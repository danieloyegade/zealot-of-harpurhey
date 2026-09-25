"""Bake a building's light into a lightmap and export its GLB with a second UV set.

Stage 5a of docs/REALISM_PASS_PLAN.md.  One command rebuilds everything:

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python-exit-code 1 --python blender/scripts/bakeLightmap.py -- dreams

Options after `--`:  --samples N  --ao-samples N  --size N  --device cpu|gpu
                     --no-export  --out-dir DIR   (the last two are for test runs:
                     nothing under public/ or blender/source/ is touched)

What it does, from config/lightmap-bakes.json:

1. Builds the same textured scene texture_glb() ships: the untextured stash GLB
   (blender/source/runtime-untextured/, an export of the greybox .blend) with
   the building's PBR surfaces applied.  Baking from the runtime geometry rather
   than the .blend keeps node names and transforms identical to the game's.
2. Adds a second UV map, `Lightmap`, to every mesh: one Smart-UV atlas across the
   whole building.  UV0 (the tiling metric UVs) is untouched.
3. Places the game's actual lights (cold-white fascia tubes, the sodium lamps in
   front of the shop, the dim sky fill) plus a ground patch and the neighbouring
   buildings as stand-ins, all in the game's own colours and units.
4. Bakes Cycles DIFFUSE (direct + indirect, colour off = light only) and AO into
   2K images, and the ground patch into a 2048x1024 image, then denoises them
   (Cycles ignores its denoise flag when baking, so the compositor's
   OpenImageDenoise does it).
5. Writes <prefix>_lightmap.hdr, <prefix>_ao.png, <prefix>_ground_lightmap.hdr and
   <prefix>_lightmap.json to public/assets/textures/lightmaps/, saves the bake
   scene to blender/source/bake/, writes review images, and re-exports the GLB
   with TEXCOORD_1 on every primitive.
"""

import datetime
import json
import shutil
import struct
import sys
import tempfile
import time
from math import radians
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.append(str(Path(__file__).resolve().parent))

from lightmapConfig import (  # noqa: E402
    PROJECT_ROOT, candela_to_watts, emission_strength, hex_to_linear, load_config,
    sky_strength, world_rect_to_model_box, world_to_model,
)
from texturedRuntimeExport import (  # noqa: E402
    STASH_DIR, apply_surfaces, has_surfaces, inspect_glb, read_glb_json,
)

UV_LAYER = "Lightmap"
TARGET_NODE = "BAKE_TARGET"


def log(message):
    print(message, flush=True)


# --------------------------------------------------------------------------- args

def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not argv:
        raise SystemExit("usage: bakeLightmap.py -- <asset> [--samples N] [--ao-samples N] "
                         "[--size N] [--device cpu|gpu] [--no-export] [--out-dir DIR]")
    options = {"asset": argv[0], "samples": None, "ao_samples": None, "size": None,
               "device": "gpu", "export": True, "out_dir": None}
    rest = iter(argv[1:])
    for flag in rest:
        if flag == "--samples":
            options["samples"] = int(next(rest))
        elif flag == "--ao-samples":
            options["ao_samples"] = int(next(rest))
        elif flag == "--size":
            options["size"] = int(next(rest))
        elif flag == "--device":
            options["device"] = next(rest)
        elif flag == "--no-export":
            options["export"] = False
        elif flag == "--out-dir":
            options["out_dir"] = Path(next(rest)).resolve()
        else:
            raise SystemExit(f"Unknown option {flag}")
    return options


# ----------------------------------------------------------------- building scene

def building_contract(asset_config):
    contract = json.loads((PROJECT_ROOT / "config" / "building-textures.json").read_text())
    entries = [e for e in contract["buildings"] if e["building"] == asset_config["contract"]]
    if len(entries) != 1:
        raise SystemExit(f"Expected one building-textures.json entry for {asset_config['contract']}")
    return entries[0]


def ensure_stash(public_glb, prefix):
    """Same rule as texture_glb(): the untextured source lives in runtime-untextured/."""
    stash = STASH_DIR / public_glb.name
    if not has_surfaces(public_glb, prefix):
        stash.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(public_glb, stash)
        log(f"Stashed untextured source {stash.name}")
    elif not stash.exists():
        raise SystemExit(f"{public_glb.name} is already textured and has no untextured stash in "
                         f"{STASH_DIR}; re-run its create script first")
    return stash


def load_textured_building(stash, entry):
    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(stash))
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    apply_surfaces(meshes, prefix=entry["surfacePrefix"],
                   texture_dir=PROJECT_ROOT / entry["textureDir"],
                   placeholder_map=entry["placeholders"])
    return meshes


def is_excluded(obj, excluded_materials):
    materials = [m.name for m in obj.data.materials if m]
    return bool(materials) and all(name in excluded_materials for name in materials)


# ------------------------------------------------------------------- lightmap UVs

def ensure_uv0(obj):
    """The Lightmap map must be the SECOND layer so it exports as TEXCOORD_1."""
    if not obj.data.uv_layers:
        obj.data.uv_layers.new(name="UVMap")


def add_lightmap_layer(obj):
    layer = obj.data.uv_layers.new(name=UV_LAYER)
    obj.data.uv_layers.active = layer
    layer.active_render = True
    return layer


def select_only(objects):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]


def unwrap_atlas(objects, margin):
    """One Smart-UV atlas across every object, at a uniform texel density."""
    select_only(objects)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=radians(66.0), margin_method="FRACTION",
                             island_margin=margin, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    # Smart UV's own packer leaves ~80% of the square empty; a concave re-pack that
    # may rescale the whole layout buys about 15% more texel density.
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=True, margin_method="FRACTION", margin=margin,
                            shape_method="CONCAVE", scale=True)
    bpy.ops.object.mode_set(mode="OBJECT")


def read_uv(obj, layer_name=UV_LAYER):
    layer = obj.data.uv_layers[layer_name]
    values = np.empty(len(obj.data.loops) * 2, dtype=np.float32)
    layer.data.foreach_get("uv", values)
    return values


def atlas_report(objects, size):
    """Coverage and texel-density spread of the packed atlas, in the log."""
    density, covered = [], 0.0
    low, high = np.array([9.0, 9.0]), np.array([-9.0, -9.0])
    for obj in objects:
        uv = read_uv(obj).reshape(-1, 2)
        low, high = np.minimum(low, uv.min(0)), np.maximum(high, uv.max(0))
        world = obj.matrix_world
        for polygon in obj.data.polygons:
            loops = np.array(list(polygon.loop_indices))
            p = uv[loops]
            x, y = p[:, 0], p[:, 1]
            uv_area = 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
            world_area = polygon.area * abs(world.determinant()) ** (2.0 / 3.0)
            covered += uv_area
            if uv_area > 0 and world_area > 1e-9:
                density.append(size * (uv_area / world_area) ** 0.5)
    density = np.array(density)
    log(f"  atlas: UV bounds {low.round(4)} .. {high.round(4)}, {covered * 100:.1f}% of the "
        f"square covered by faces")
    log(f"  texel density (texels/m): min {density.min():.0f}  p10 {np.percentile(density, 10):.0f}  "
        f"median {np.median(density):.0f}  p90 {np.percentile(density, 90):.0f}  "
        f"max {density.max():.0f}  ->  {100.0 / np.median(density):.2f} cm per texel")
    if low.min() < -1e-4 or high.max() > 1.0 + 1e-4:
        raise RuntimeError("Lightmap atlas leaves the 0-1 square")


# --------------------------------------------------------------- scene for baking

def diffuse_material(name, linear_rgb, albedo=1.0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    shader = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    shader.inputs["Base Color"].default_value = (*[c * albedo for c in linear_rgb], 1.0)
    shader.inputs["Roughness"].default_value = 1.0
    shader.inputs["Metallic"].default_value = 0.0
    return material


def emission_material(name, linear_rgb, strength):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    emit = tree.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (*linear_rgb, 1.0)
    emit.inputs["Strength"].default_value = strength
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return material


def link_new(obj, collection):
    collection.objects.link(obj)
    return obj


def box_object(name, low, high, material, collection):
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    obj.scale = tuple(h - l for l, h in zip(low, high))
    obj.location = tuple((l + h) / 2 for l, h in zip(low, high))
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)
    return obj


def plane_object(name, x_range, y_range, z, material, collection):
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    x0, x1 = x_range
    y0, y1 = y_range
    mesh.from_pydata([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], [], [(0, 1, 2, 3)])
    layer = mesh.uv_layers.new(name="UVMap")
    for loop, uv in zip(mesh.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        layer.data[loop.index].uv = uv
    mesh.materials.append(material)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def add_world(scene, sky):
    world = bpy.data.worlds.new("DreamsBakeSky")
    world.use_nodes = True
    background = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    background.inputs["Color"].default_value = (*hex_to_linear(sky["colorHex"]), 1.0)
    background.inputs["Strength"].default_value = sky_strength(sky["intensity"])
    scene.world = world
    return world


def add_lamps(scene, lights, placement):
    for lamp in lights["lamps"]:
        data = bpy.data.lights.new(lamp["name"], "SPOT")
        data.energy = candela_to_watts(lamp["candela"])
        data.color = hex_to_linear(lamp["colorHex"])
        data.spot_size = radians(lights["lampSpotDegrees"])
        data.spot_blend = lights["lampSpotBlend"]
        data.shadow_soft_size = lights["lampRadius"]
        obj = bpy.data.objects.new(lamp["name"], data)
        obj.location = Vector(world_to_model(lamp["world"], placement))
        obj.rotation_euler = (0.0, 0.0, 0.0)  # a spot points down -Z
        scene.collection.objects.link(obj)


def light_tubes(meshes, tubes):
    """Turn each fascia tube into a mesh light whose head-on intensity is `candelaEach`."""
    colour = hex_to_linear(tubes["colorHex"])
    lit = []
    for obj in meshes:
        if not any(m and m.name == tubes["material"] for m in obj.data.materials):
            continue
        front_area = obj.dimensions.x * obj.dimensions.z
        strength = emission_strength(tubes["candelaEach"], front_area)
        material = emission_material(f"BAKE_{obj.name}_Emission", colour, strength)
        for index, slot in enumerate(obj.data.materials):
            if slot and slot.name == tubes["material"]:
                obj.data.materials[index] = material
        lit.append(obj.name)
    if not lit:
        raise RuntimeError(f"No meshes use {tubes['material']}; the tubes would not light anything")
    return lit


def neutralise_for_light_only(objects):
    """Bounce light should carry the real albedo, but not metal or transmission.

    A metal has no diffuse, so it would bake black, and the runtime multiplies the
    lightmap by albedo * (1 - metalness) again.
    """
    seen = set()
    for obj in objects:
        for material in obj.data.materials:
            if material is None or material.name in seen or not material.use_nodes:
                continue
            seen.add(material.name)
            for node in material.node_tree.nodes:
                if node.type != "BSDF_PRINCIPLED":
                    continue
                for name in ("Metallic", "Transmission Weight", "Coat Weight", "Sheen Weight"):
                    socket = node.inputs.get(name)
                    if socket is None:
                        continue
                    for link in list(socket.links):
                        material.node_tree.links.remove(link)
                    socket.default_value = 0.0


def join_for_bake(objects, name):
    """One object bakes in seconds; 300 separate ones re-sync the scene 300 times.

    Only the bake scene is joined: the export re-imports a clean scene and takes
    the per-object UVs captured before this.
    """
    select_only(objects)
    bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = name
    joined.data.name = f"{name}_Mesh"
    return joined


def configure_cycles(scene, samples, device):
    scene.render.engine = "CYCLES"
    cycles = scene.cycles
    cycles.samples = samples
    cycles.use_adaptive_sampling = False
    cycles.max_bounces = 8
    cycles.diffuse_bounces = 6
    cycles.sample_clamp_indirect = 10.0
    cycles.caustics_reflective = False
    cycles.caustics_refractive = False
    cycles.device = "CPU"
    if device == "gpu":
        try:
            prefs = bpy.context.preferences.addons["cycles"].preferences
            prefs.compute_device_type = "METAL"
            prefs.refresh_devices()
            gpus = [d for d in prefs.devices if d.type == "METAL"]
            for d in prefs.devices:
                d.use = d.type == "METAL"
            if gpus:
                cycles.device = "GPU"
                log(f"  Cycles device: {gpus[0].name}")
        except (TypeError, RuntimeError, AttributeError) as error:
            log(f"  GPU unavailable ({error}); baking on CPU")
    if cycles.device == "CPU":
        log("  Cycles device: CPU")
    scene.view_settings.view_transform = "Standard"


# ------------------------------------------------------------------------- baking

def new_float_image(name, width, height):
    image = bpy.data.images.new(name, width, height, alpha=False, float_buffer=True, is_data=True)
    return image


def set_bake_target(objects, image):
    for obj in objects:
        for material in obj.data.materials:
            if material is None or not material.use_nodes:
                continue
            nodes = material.node_tree.nodes
            node = nodes.get(TARGET_NODE) or nodes.new("ShaderNodeTexImage")
            node.name = TARGET_NODE
            node.image = image
            node.select = True
            nodes.active = node


def bake(kind, objects, image, *, samples, margin_px, uv_name):
    scene = bpy.context.scene
    scene.cycles.samples = samples
    for obj in objects:
        layer = obj.data.uv_layers[uv_name]
        obj.data.uv_layers.active = layer
        layer.active_render = True
    set_bake_target(objects, image)
    select_only(objects)
    started = time.time()
    if kind == "DIFFUSE":
        bpy.ops.object.bake(type="DIFFUSE", pass_filter={"DIRECT", "INDIRECT"},
                            margin=margin_px, margin_type="EXTEND", use_clear=True)
    else:
        bpy.ops.object.bake(type=kind, margin=margin_px, margin_type="EXTEND", use_clear=True)
    log(f"  baked {kind} -> {image.name} {image.size[0]}x{image.size[1]} "
        f"at {samples} samples in {time.time() - started:.0f} s")


def image_array(image):
    values = np.empty(image.size[0] * image.size[1] * 4, dtype=np.float32)
    image.pixels.foreach_get(values)
    return values.reshape(image.size[1], image.size[0], 4)


def denoise(image, work_dir):
    """OpenImageDenoise through the compositor; returns the denoised (h, w, 3) array."""
    width, height = image.size
    noisy_path = work_dir / f"{image.name}_noisy.exr"
    clean_path = work_dir / f"{image.name}_clean.exr"

    scene = bpy.data.scenes.new(f"denoise_{image.name}")
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 1
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_depth = "32"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "Standard"
    camera_data = bpy.data.cameras.new("denoise_camera")
    camera = bpy.data.objects.new("denoise_camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    image.save_render(str(noisy_path), scene=scene)
    source = bpy.data.images.load(str(noisy_path))
    source.colorspace_settings.name = "Non-Color"

    tree = bpy.data.node_groups.new(f"denoise_{image.name}", "CompositorNodeTree")
    scene.compositing_node_group = tree
    tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    read = tree.nodes.new("CompositorNodeImage")
    read.image = source
    node = tree.nodes.new("CompositorNodeDenoise")
    out = tree.nodes.new("NodeGroupOutput")
    tree.links.new(read.outputs["Image"], node.inputs["Image"])
    tree.links.new(node.outputs["Image"], out.inputs[0])

    scene.render.filepath = str(clean_path)
    bpy.ops.render.render(scene=scene.name, write_still=True)
    clean = bpy.data.images.load(str(clean_path))
    clean.colorspace_settings.name = "Non-Color"

    before = image_array(image)[..., :3]
    after = image_array(clean)[..., :3]
    baked = before.max(axis=2) > 0.0  # texels the bake wrote; the rest of the atlas is empty
    drift = abs(after[baked].mean() - before[baked].mean()) / max(before[baked].mean(), 1e-9)
    log(f"  denoised {image.name}: mean over {baked.mean() * 100:.0f}% baked texels "
        f"{before[baked].mean():.4f} -> {after[baked].mean():.4f} ({drift * 100:.2f}% drift)")
    if drift > 0.05:
        raise RuntimeError(f"Denoising shifted {image.name}'s mean by {drift * 100:.1f}%")
    return after.copy()


def write_hdr(array, path, name):
    """Scene-linear radiance as a Radiance .hdr (RGBE)."""
    height, width = array.shape[:2]
    image = bpy.data.images.new(name, width, height, alpha=False, float_buffer=True, is_data=True)
    rgba = np.ones((height, width, 4), dtype=np.float32)
    rgba[..., :3] = array
    image.pixels.foreach_set(rgba.ravel())
    image.filepath_raw = str(path)
    image.file_format = "HDR"
    image.save()
    return image


def write_png(rgb, path, name, *, colour):
    """8-bit PNG. `colour` True encodes sRGB (review images); False stores raw data (AO)."""
    height, width = rgb.shape[:2]
    if colour:
        rgb = np.where(rgb <= 0.0031308, rgb * 12.92,
                       1.055 * np.power(np.clip(rgb, 1e-9, None), 1 / 2.4) - 0.055)
    rgba = np.ones((height, width, 4), dtype=np.float32)
    rgba[..., :3] = np.clip(rgb, 0.0, 1.0)
    image = bpy.data.images.new(name, width, height, alpha=False, float_buffer=False, is_data=True)
    image.pixels.foreach_set(rgba.ravel())
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()


def tonemap_review(array, exposure):
    """Simple soft-clip so an HDR lightmap can be looked at in a PNG."""
    scaled = array * exposure
    return scaled / (1.0 + scaled)


# ------------------------------------------------------------------ review render

def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def render_preview(cfg, placement, path, samples):
    preview = cfg["preview"]
    scene = bpy.context.scene
    camera_data = bpy.data.cameras.new("PreviewCamera")
    camera_data.lens = preview["lensMm"]
    camera = bpy.data.objects.new("PreviewCamera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = Vector(world_to_model(preview["cameraWorld"], placement))
    look_at(camera, world_to_model(preview["targetWorld"], placement))
    scene.camera = camera
    scene.render.resolution_x, scene.render.resolution_y = preview["size"]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.view_settings.view_transform = "AgX"
    scene.render.filepath = str(path)
    started = time.time()
    bpy.ops.render.render(write_still=True)
    scene.view_settings.view_transform = "Standard"
    log(f"  review render (real lights, AgX) -> {path.name} in {time.time() - started:.0f} s")


# ------------------------------------------------------------------------- export

def export_with_lightmap_uvs(entry, stash, uv_by_name, public_glb):
    """Fresh copy of the shipped scene (so the bake's material edits do not leak),
    plus the baked `Lightmap` map as its second UV layer."""
    meshes = load_textured_building(stash, entry)
    for obj in meshes:
        ensure_uv0(obj)
        values = uv_by_name.get(obj.name)
        if values is None or values.size != len(obj.data.loops) * 2:
            raise RuntimeError(f"{obj.name}: baked UVs do not match the re-imported mesh")
        layer = obj.data.uv_layers.new(name=UV_LAYER)
        layer.data.foreach_set("uv", values)
        obj.data.uv_layers.active_index = 0
        obj.data.uv_layers[0].active_render = True
    everything = list(bpy.context.scene.objects)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in everything:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(public_glb), export_format="GLB",
                              use_selection=True, export_apply=True, export_yup=True,
                              export_cameras=False, export_lights=False, export_extras=True)
    inspect_glb(public_glb, entry["surfacePrefix"], entry["expectedSurfaces"], reference=stash)
    check_second_uv(public_glb)


def read_glb_binary(path):
    """The BIN chunk of a GLB (chunk 2), for reading accessor data directly."""
    with Path(path).open("rb") as handle:
        handle.seek(12)
        while True:
            header = handle.read(8)
            if len(header) < 8:
                raise RuntimeError(f"{path} has no BIN chunk")
            length, kind = struct.unpack("<II", header)
            body = handle.read(length)
            if kind == 0x004E4942:
                return body


def read_vec2_accessor(data, binary, index):
    accessor = data["accessors"][index]
    if accessor["componentType"] != 5126 or accessor["type"] != "VEC2":
        raise RuntimeError(f"accessor {index} is not a float VEC2")
    view = data["bufferViews"][accessor["bufferView"]]
    stride = view.get("byteStride", 8)
    start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    raw = np.frombuffer(binary, dtype=np.uint8, count=stride * (accessor["count"] - 1) + 8,
                        offset=start)
    rows = np.lib.stride_tricks.as_strided(raw, shape=(accessor["count"], 8), strides=(stride, 1))
    return np.ascontiguousarray(rows).view("<f4").reshape(-1, 2)


def check_second_uv(path):
    """Every primitive carries TEXCOORD_1, inside 0-1 (glTF stores no min/max for UVs)."""
    data = read_glb_json(path)
    binary = read_glb_binary(path)
    primitives = [p for mesh in data["meshes"] for p in mesh["primitives"]]
    missing = [p for p in primitives if "TEXCOORD_1" not in p["attributes"]]
    if missing:
        raise RuntimeError(f"{Path(path).name}: {len(missing)} of {len(primitives)} primitives "
                           f"have no TEXCOORD_1")
    uv = np.concatenate([read_vec2_accessor(data, binary, p["attributes"]["TEXCOORD_1"])
                         for p in primitives])
    low, high = uv.min(axis=0), uv.max(axis=0)
    if low.min() < -1e-4 or high.max() > 1.0 + 1e-4:
        raise RuntimeError(f"TEXCOORD_1 leaves 0-1: {low} .. {high}")
    log(f"  {Path(path).name}: TEXCOORD_1 on all {len(primitives)} primitives, "
        f"range {low.round(4)} .. {high.round(4)}")


# --------------------------------------------------------------------------- main

def main():
    options = parse_args()
    cfg = load_config(options["asset"])
    entry = building_contract(cfg)
    placement = cfg["placement"]
    building_cfg, ground_cfg, light_cfg = cfg["building"], cfg["ground"], cfg["lights"]

    size = options["size"] or building_cfg["size"]
    ground_size = (size, size // 2) if options["size"] else tuple(ground_cfg["size"])
    samples = options["samples"] or building_cfg["samples"]
    ground_samples = options["samples"] or ground_cfg["samples"]
    ao_samples = options["ao_samples"] or building_cfg["aoSamples"]

    live = options["out_dir"] is None
    out_dir = PROJECT_ROOT / cfg["outputDir"] if live else options["out_dir"]
    preview_dir = PROJECT_ROOT / cfg["previewDir"] if live else options["out_dir"]
    work_dir = Path(tempfile.mkdtemp(prefix=f"lightmap-{cfg['prefix']}-"))
    for directory in (out_dir, preview_dir):
        directory.mkdir(parents=True, exist_ok=True)
    prefix = cfg["prefix"]
    started = time.time()

    public_glb = PROJECT_ROOT / "public" / entry["glb"]
    stash = ensure_stash(public_glb, entry["surfacePrefix"])
    log(f"[1/6] Building the textured scene from {stash.name}")
    meshes = load_textured_building(stash, entry)
    building = [m for m in meshes if not is_excluded(m, building_cfg["excludeMaterials"])]
    excluded = [m for m in meshes if m not in building]
    log(f"  {len(meshes)} meshes: {len(building)} baked, {len(excluded)} excluded "
        f"({', '.join(building_cfg['excludeMaterials'])})")

    log(f"[2/6] Lightmap UV atlas ({size} px, margin {building_cfg['uvMargin']})")
    for obj in meshes:
        ensure_uv0(obj)
        add_lightmap_layer(obj)
    unwrap_atlas(building, building_cfg["uvMargin"])
    for obj in excluded:
        zeros = np.zeros(len(obj.data.loops) * 2, dtype=np.float32)
        obj.data.uv_layers[UV_LAYER].data.foreach_set("uv", zeros)
        obj.hide_render = True
    atlas_report(building, size)
    uv_by_name = {obj.name: read_uv(obj) for obj in meshes}

    log("[3/6] Placing the game's lights, the ground patch and the neighbouring buildings")
    scene = bpy.context.scene
    configure_cycles(scene, samples, options["device"])
    add_world(scene, light_cfg["sky"])
    add_lamps(scene, light_cfg, placement)
    lit_tubes = light_tubes(meshes, light_cfg["tubes"])
    neutralise_for_light_only(building)
    joined = join_for_bake(building, f"{cfg['prefix'].title()}_Bake_Joined")

    ground_material = diffuse_material("BAKE_Ground", (1.0, 1.0, 1.0), ground_cfg["albedo"])
    extent = ground_cfg["extent"]
    ground = plane_object("Dreams_Ground_Patch", extent["x"], extent["y"], 0.0,
                          ground_material, scene.collection)
    plane_object("Far_Ground", (-300.0, 300.0), (-300.0, 300.0), -0.02, ground_material,
                 scene.collection)
    for stand_in in cfg["standIns"]:
        low, high = world_rect_to_model_box(stand_in["worldX"], stand_in["worldZ"],
                                            stand_in["height"], placement)
        box_object(f"StandIn_{stand_in['name'].replace(' ', '_')}", low, high,
                   diffuse_material(f"BAKE_{stand_in['name']}", hex_to_linear(stand_in["colorHex"])),
                   scene.collection)
    log(f"  sky {light_cfg['sky']['colorHex']} x {sky_strength(light_cfg['sky']['intensity']):.3f}, "
        f"{len(light_cfg['lamps'])} sodium lamps at {light_cfg['lamps'][0]['candela']} cd, "
        f"{len(lit_tubes)} tubes at {light_cfg['tubes']['candelaEach']} cd (cold white)")

    log("[4/6] Baking")
    bpy.context.scene.world.light_settings.distance = building_cfg["aoDistance"]
    light_image = new_float_image(f"{prefix}_lightmap", size, size)
    ao_image = new_float_image(f"{prefix}_ao", size, size)
    ground_image = new_float_image(f"{prefix}_ground_lightmap", *ground_size)
    bake("DIFFUSE", [joined], light_image, samples=samples,
         margin_px=building_cfg["bakeMarginPx"], uv_name=UV_LAYER)
    bake("AO", [joined], ao_image, samples=ao_samples,
         margin_px=building_cfg["bakeMarginPx"], uv_name=UV_LAYER)
    bake("DIFFUSE", [ground], ground_image, samples=ground_samples,
         margin_px=ground_cfg["bakeMarginPx"], uv_name="UVMap")

    log("[5/6] Denoising and saving")
    light = denoise(light_image, work_dir)
    ao = denoise(ao_image, work_dir)
    ground_light = denoise(ground_image, work_dir)
    write_hdr(light, out_dir / f"{prefix}_lightmap.hdr", f"{prefix}_lightmap_out")
    write_hdr(ground_light, out_dir / f"{prefix}_ground_lightmap.hdr", f"{prefix}_ground_out")
    write_png(ao, out_dir / f"{prefix}_ao.png", f"{prefix}_ao_out", colour=False)
    write_png(tonemap_review(light, 3.0), preview_dir / f"{prefix}-lightmap-building.png",
              "review_light", colour=True)
    write_png(tonemap_review(ground_light, 3.0), preview_dir / f"{prefix}-lightmap-ground.png",
              "review_ground", colour=True)
    write_png(ao, preview_dir / f"{prefix}-ao-building.png", "review_ao", colour=False)
    log(f"  lightmap radiance: mean {light[..., :3].mean():.4f}, p99 "
        f"{np.percentile(light[..., :3], 99):.3f}, max {light[..., :3].max():.2f}; "
        f"ground p99 {np.percentile(ground_light[..., :3], 99):.3f}, max "
        f"{ground_light[..., :3].max():.2f}")

    metadata = {
        "asset": options["asset"],
        "generatedBy": "blender/scripts/bakeLightmap.py",
        "blender": bpy.app.version_string,
        "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "convention": "scene-linear radiance of a white diffuse surface, light only; "
                      "three.js lightMapIntensity = pi reproduces the bake's exposure",
        "uvLayer": {"name": UV_LAYER, "gltfAttribute": "TEXCOORD_1", "threeChannel": 1,
                    "orientation": "glTF convention (v = 1 - v_blender), so the image rows run "
                                   "top-down and a loader must not flip them again"},
        "lightmap": {"file": f"{prefix}_lightmap.hdr", "size": [size, size], "samples": samples},
        "ao": {"file": f"{prefix}_ao.png", "size": [size, size], "samples": ao_samples,
               "distanceMetres": building_cfg["aoDistance"]},
        "ground": {
            "file": f"{prefix}_ground_lightmap.hdr", "size": list(ground_size),
            "samples": ground_samples, "modelFrameExtent": extent,
            "uv": "u runs along model +X from extent.x[0]; v runs along model +Y from extent.y[0]",
            "placement": placement,
        },
        "lights": light_cfg,
        "denoise": "compositor OpenImageDenoise, HDR, accurate prefilter",
        "glb": entry["glb"],
        "stats": {
            "bakedMeshes": len(building), "excludedMeshes": len(excluded),
            "lightmapMean": float(light[..., :3].mean()),
            "lightmapP99": float(np.percentile(light[..., :3], 99)),
            "groundP99": float(np.percentile(ground_light[..., :3], 99)),
        },
    }
    (out_dir / f"{prefix}_lightmap.json").write_text(json.dumps(metadata, indent=2) + "\n")

    if live:
        blend_path = PROJECT_ROOT / cfg["bakeSceneBlend"]
    else:
        blend_path = out_dir / f"{prefix}-bake.blend"
    blend_path.parent.mkdir(parents=True, exist_ok=True)
    render_preview(cfg, placement, preview_dir / f"{prefix}-bake-scene-real-lights.png",
                   cfg["preview"]["samples"])
    # The baked maps live in the files above; keep the .blend to the scene itself.
    for material in bpy.data.materials:
        if material.use_nodes and material.node_tree.nodes.get(TARGET_NODE):
            material.node_tree.nodes.remove(material.node_tree.nodes[TARGET_NODE])
    for image in (light_image, ao_image, ground_image):
        bpy.data.images.remove(image)
    bpy.ops.file.make_paths_relative()
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), compress=True)
    log(f"  bake scene -> {blend_path}")

    log("[6/6] Exporting the GLB with TEXCOORD_1")
    if options["export"]:
        export_with_lightmap_uvs(entry, stash, uv_by_name, public_glb if live else out_dir / public_glb.name)
    else:
        log("  --no-export: GLB not written")
    shutil.rmtree(work_dir, ignore_errors=True)
    log(f"Done in {time.time() - started:.0f} s")


if __name__ == "__main__":
    main()
