"""Build, texture, export and validate the two worn shipping pallets.

Brief: references/architecture/infrastructure:objects/pallet/pallet.txt

Geometry comes from palletGeometry.py, surface authoring from
palletWeathering.py, and the unwrap/bake/material plumbing from
surfaceWeathering.py (shared with the bus shelter texture pass).

Rebuild from the repository root:

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python blender/scripts/createPallets.py -- [--stage textures|renders|validate] \
        [--only brown|blue] [--bake-cache DIR]

--bake-cache reuses baked position/normal/AO buffers while iterating on
weathering; it is valid only while geometry and UVs are unchanged.
"""

import json
import sys
import time
from math import radians
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import palletGeometry as geometry  # noqa: E402
import palletWeathering as weathering  # noqa: E402
from surfaceWeathering import (Texels, bake_buffers, build_pbr_material, height_to_normal, save_rgba,  # noqa: E402
                               srgb_encode, unwrap_atlas)

PROJECT_ROOT = SCRIPT_DIR.parents[1]
SOURCE_DIR = PROJECT_ROOT / "blender" / "source" / "pallets"
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "pallets"
MODEL_DIR = PROJECT_ROOT / "public" / "assets" / "models" / "pallets"
RENDER_DIR = PROJECT_ROOT / "renders" / "pallets"

ATLAS = 2048
# Sub-millimetre relief is flatter than one 8-bit normal step at ~1.3 mm per texel.
NORMAL_STRENGTH = 3.0
VARIANTS = {
    "brown": (geometry.BROWN, weathering.weather_brown, "MAT_Pallet_WornBrown"),
    "blue": (geometry.BLUE, weathering.weather_blue, "MAT_Pallet_WornBlue"),
}
BAKE_CACHE = None


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    units = bpy.context.scene.unit_settings
    units.system = "METRIC"
    units.scale_length = 1.0


def new_collection(name):
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def part_meta(pallet):
    return {
        part.obj.name: {
            "kind": part.kind,
            "matrix": [list(row) for row in part.obj.matrix_world],
            "size": part.size,
            "seed": pallet.layout.seed * 100 + i,
            "replacement": part.params.get("replacement", False),
        }
        for i, part in enumerate(pallet.parts)
    }


def cached_bake(stem, objects):
    path = Path(BAKE_CACHE) / f"{stem}-{ATLAS}.npz" if BAKE_CACHE else None
    if path and path.exists():
        data = np.load(path, allow_pickle=True)
        return data["position"], data["normal"], data["extra"], data["names"].item()
    ground = bpy.data.objects.new("TEMP_ground", bpy.data.meshes.new("TEMP_ground"))
    ground.data.from_pydata([(-3, -3, 0), (3, -3, 0), (3, 3, 0), (-3, 3, 0)], [], [(0, 1, 2, 3)])
    bpy.context.scene.collection.objects.link(ground)
    result = bake_buffers(objects, ATLAS, ATLAS, ao_distance=0.2, convex_distance=0.008)
    bpy.data.objects.remove(ground, do_unlink=True)
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(path, position=result[0], normal=result[1], extra=result[2], names=np.array(result[3], dtype=object))
    return result


def write_maps(L, stem):
    tex = L.tex
    albedo = srgb_encode(L.albedo)
    base = tex.grid(np.column_stack((albedo, np.ones(tex.M, np.float32))), fill=(*albedo.mean(axis=0), 1.0))
    orm = tex.grid(np.column_stack((L.ao_channel, L.rough, L.metal)), fill=(1.0, float(L.rough.mean()), 0.0))
    normal = height_to_normal(tex.grid(L.height, fill=0.0), tex.texel_m, NORMAL_STRENGTH)
    images = {
        "base": save_rgba(TEXTURE_DIR / f"{stem}-basecolor.png", base),
        "orm": save_rgba(TEXTURE_DIR / f"{stem}-orm.png", orm),
        "normal": save_rgba(TEXTURE_DIR / f"{stem}-normal.png", normal),
    }
    images["orm"].colorspace_settings.name = "Non-Color"
    images["normal"].colorspace_settings.name = "Non-Color"
    wood = ~np.isin(tex.ids, [i for i, n in tex.names.items() if n.endswith("-nails")])
    print(f"[pallets] {stem}: texels={tex.M} texel_mm={tex.texel_m * 1000:.2f} "
          f"rough p5/p50/p95={np.percentile(L.rough[wood], [5, 50, 95]).round(3).tolist()}", flush=True)
    return images


def triangles(obj):
    return sum(len(poly.vertices) - 2 for poly in obj.data.polygons)


def texture_stage(key):
    layout, weather, material_name = VARIANTS[key]
    started = time.time()
    reset()
    rng = np.random.default_rng(layout.seed + 1)
    components = new_collection(f"{layout.slug}-components")
    export = new_collection(f"{layout.slug}-export")
    pallet = geometry.build_pallet(layout, components)
    if key == "brown":
        # One top board has been replaced: paler, barely weathered, a clean saw cut.
        [p for p in pallet.parts if p.kind == "top"][3].params["replacement"] = True

    material = bpy.data.materials.new(material_name)
    objects = [part.obj for part in pallet.parts]
    for obj in objects:
        obj.data.materials.append(material)
    unwrap_atlas(objects, importance={"top-board": 1.15, "cross-board": 0.95, "bottom-board": 0.85, "block": 0.9})

    position, normal, extra, names = cached_bake(layout.slug, objects)
    print(f"[pallets] {key}: baked in {time.time() - started:.0f}s", flush=True)
    tex = Texels(position, normal, extra, names)
    fr = weathering.Frames(tex, part_meta(pallet))
    ctx = {
        "parts": part_meta(pallet), "cross_x": pallet.cross_x, "row_y": pallet.row_y,
        "cross_w": layout.cross_width, "bottom_widths": layout.bottom_widths, "top_z": pallet.top_z,
        "nails": pallet.nails, "holes": pallet.holes,
    }
    maps = write_maps(weather(tex, fr, ctx, rng), layout.slug)
    print(f"[pallets] {key}: weathered in {time.time() - started:.0f}s", flush=True)
    build_pbr_material(material, maps["base"], maps["orm"], maps["normal"], normal_strength=1.0)

    joined = geometry.join_for_export(pallet, export)
    bpy.context.view_layer.layer_collection.children[components.name].exclude = True
    for image in bpy.data.images:
        if image.filepath:
            image.filepath = bpy.path.relpath(image.filepath, start=str(SOURCE_DIR))
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    blend = SOURCE_DIR / f"{layout.name}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    glb = MODEL_DIR / f"{layout.name}.glb"
    bpy.ops.object.select_all(action="DESELECT")
    joined.select_set(True)
    bpy.context.view_layer.objects.active = joined
    bpy.ops.export_scene.gltf(filepath=str(glb), export_format="GLB", use_selection=True, export_apply=True,
                              export_yup=True, export_cameras=False, export_lights=False,
                              export_image_format="WEBP", export_image_quality=90)
    print(f"[pallets] {key}: {triangles(joined)} tris, nails={len(pallet.nails)}, holes={len(pallet.holes)}, "
          f"{glb.stat().st_size / 1e6:.2f} MB -> {glb.relative_to(PROJECT_ROOT)} ({time.time() - started:.0f}s)", flush=True)


# ------------------------------------------------------------------ renders

def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def render_stage(key):
    layout, _, _ = VARIANTS[key]
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE_DIR / f"{layout.name}.blend"))
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.use_raytracing = True
    scene.eevee.use_shadows = True
    scene.eevee.taa_render_samples = 64
    scene.render.resolution_x, scene.render.resolution_y = 1280, 960
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "None"

    # Neutral grey studio: soft overcast dome plus a low-contrast key that rakes
    # the deck enough to show roughness, grain relief and paint edges.
    world = bpy.data.worlds.new("Neutral")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.5, 0.5, 0.5, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.9
    scene.world = world
    sun = bpy.data.objects.new("Key", bpy.data.lights.new("Key", "SUN"))
    sun.data.energy = 2.6
    sun.data.angle = radians(6)
    sun.location = (-2, -3, 4)
    point_at(sun, (0, 0, 0))
    scene.collection.objects.link(sun)
    ground_mat = bpy.data.materials.new("Stage_Ground")
    ground_mat.use_nodes = True
    shader = ground_mat.node_tree.nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value = (0.16, 0.16, 0.155, 1)
    shader.inputs["Roughness"].default_value = 0.85
    ground = bpy.data.objects.new("Stage_Ground", bpy.data.meshes.new("Stage_Ground"))
    ground.data.from_pydata([(-8, -8, 0), (8, -8, 0), (8, 8, 0), (-8, 8, 0)], [], [(0, 1, 2, 3)])
    ground.data.materials.append(ground_mat)
    scene.collection.objects.link(ground)

    camera = bpy.data.objects.new("Review_Camera", bpy.data.cameras.new("Review_Camera"))
    camera.data.clip_start = 0.01
    scene.collection.objects.link(camera)
    scene.camera = camera
    lx, wy = layout.length / 2, layout.width / 2
    views = (
        ("01-upper-three-quarter", (lx + 1.1, -wy - 1.5, 1.25), (0, 0, 0.06), 38),
        ("02-lower-three-quarter", (lx + 1.0, -wy - 1.3, 0.09), (0, 0, 0.085), 38),
        ("03-closeup-corner", (lx + 0.28, -wy - 0.34, 0.33), (lx - 0.1, -wy + 0.1, 0.12), 50),
    )
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    for name, location, target, lens in views:
        camera.location = location
        camera.data.lens = lens
        point_at(camera, target)
        scene.render.filepath = str(RENDER_DIR / f"{key}-{name}.png")
        bpy.ops.render.render(write_still=True)
    print(f"[pallets] {key}: renders -> {RENDER_DIR.relative_to(PROJECT_ROOT)}", flush=True)


# --------------------------------------------------------------- validation

def validate_stage(key):
    """Reimport the GLB into an empty scene and record what actually survived export."""
    import bmesh

    layout, _, material_name = VARIANTS[key]
    glb = MODEL_DIR / f"{layout.name}.glb"
    reset()
    bpy.ops.import_scene.gltf(filepath=str(glb))
    objects = list(bpy.context.scene.objects)
    meshes = [o for o in objects if o.type == "MESH"]
    report = {"glb": str(glb.relative_to(PROJECT_ROOT)), "size_mb": round(glb.stat().st_size / 1e6, 2),
              "objects": [(o.name, o.type) for o in objects], "meshes": []}
    for obj in meshes:
        mesh = obj.data
        corners = np.array([obj.matrix_world @ Vector(c) for c in obj.bound_box])
        bm = bmesh.new()
        bm.from_mesh(mesh)
        normals = np.array([f.normal for f in bm.faces])
        entry = {
            "name": obj.name,
            "location": list(obj.location), "rotation": list(obj.rotation_euler), "scale": list(obj.scale),
            "dimensions_m": [round(float(v), 4) for v in corners.max(0) - corners.min(0)],
            "min_z": round(float(corners[:, 2].min()), 5),
            "centre_xy": [round(float(v), 4) for v in (corners.max(0) + corners.min(0))[:2] / 2],
            "triangles": triangles(obj),
            "uv_layers": [uv.name for uv in mesh.uv_layers],
            "loose_verts": sum(1 for v in bm.verts if not v.link_faces),
            "degenerate_faces": int(sum(1 for f in bm.faces if f.calc_area() < 1e-10)),
            "zero_normals": int((np.linalg.norm(normals, axis=1) < 0.5).sum()),
            "materials": [],
        }
        bm.free()
        for slot in obj.material_slots:
            mat = slot.material
            nodes = mat.node_tree.nodes
            shader = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
            images = [(n.image.name, list(n.image.size), bool(n.image.packed_file)) for n in nodes if n.type == "TEX_IMAGE"]
            normal_map = next((n for n in nodes if n.type == "NORMAL_MAP"), None)
            entry["materials"].append({
                "name": mat.name, "expected": material_name,
                "images": images,
                "roughness_textured": shader.inputs["Roughness"].is_linked,
                "metallic_textured": shader.inputs["Metallic"].is_linked,
                "base_textured": shader.inputs["Base Color"].is_linked,
                "normal_strength": normal_map.inputs["Strength"].default_value if normal_map else None,
            })
        report["meshes"].append(entry)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    (RENDER_DIR / f"{key}-validation.json").write_text(json.dumps(report, indent=2))
    print(f"[pallets] {key} validation: {json.dumps(report)}", flush=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    stage = argv[argv.index("--stage") + 1] if "--stage" in argv else "all"
    only = argv[argv.index("--only") + 1] if "--only" in argv else None
    global BAKE_CACHE
    BAKE_CACHE = argv[argv.index("--bake-cache") + 1] if "--bake-cache" in argv else None
    for key in VARIANTS:
        if only and key != only:
            continue
        if stage in ("all", "textures"):
            texture_stage(key)
        if stage in ("all", "validate"):
            validate_stage(key)
        if stage in ("all", "renders"):
            render_stage(key)


if __name__ == "__main__":
    main()
