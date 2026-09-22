"""Runtime material pass for building GLBs, applied to the GLB that ships.

Vinyl Exchange and Nice Things each re-open their source .blend and re-select
their export set; every create script selects differently (runtime duplicate
collections, NON_EXPORT filters, per-asset collections).  This pass works on
the shipped GLB instead, so the geometry, node names and extras are exactly
what the game loads today:

1. If the public GLB has no `<prefix>` materials it is the fresh untextured
   export, and is copied to `blender/source/runtime-untextured/`.  Otherwise
   the stash must already exist (re-run the building's create script to
   refresh it after a geometry change).
2. The stash is imported into an empty scene; placeholder slots named in the
   contract are swapped for textured materials built from the maps and
   `validation.json` of the building's texture pass.
3. Faces are box-projected in metres per material slot, so one mesh may carry
   several surfaces at different tile sizes (the Vinyl Exchange exporter could
   not).
4. The result is exported over the public GLB and inspected: exact surface
   count, UV0 on every textured primitive, and unchanged node names.
"""

import json
import shutil
import struct
import sys
from pathlib import Path

import bpy
from mathutils import Vector

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STASH_DIR = PROJECT_ROOT / "blender" / "source" / "runtime-untextured"

sys.path.append(str(PROJECT_ROOT / "blender" / "scripts"))
from surfaceWeathering import build_pbr_material, load_image  # noqa: E402


def read_glb_json(path):
    with Path(path).open("rb") as handle:
        magic, version, _ = struct.unpack("<4sII", handle.read(12))
        if magic != b"glTF" or version != 2:
            raise RuntimeError(f"{path} is not a glTF 2 GLB")
        length, kind = struct.unpack("<II", handle.read(8))
        if kind != 0x4E4F534A:
            raise RuntimeError(f"{path} has no JSON chunk")
        return json.loads(handle.read(length))


def has_surfaces(path, prefix):
    return any(m.get("name", "").startswith(prefix)
               for m in read_glb_json(path).get("materials", []))


def load_surface_specs(texture_dir):
    data = json.loads((Path(texture_dir) / "validation.json").read_text())
    return {m["slug"]: {"coverage": tuple(m["coverage_m"]), "normal": m["normal_strength"]}
            for m in data["materials"]}


def runtime_material(prefix, slug, texture_dir, spec):
    name = f"{prefix}{slug}"
    material = bpy.data.materials.get(name)
    if material is not None:
        return material
    images = {kind: load_image(Path(texture_dir) / f"{slug}-{kind}.png",
                               non_color=kind != "basecolor")
              for kind in ("basecolor", "orm", "normal")}
    material = bpy.data.materials.new(name)
    build_pbr_material(material, images["basecolor"], images["orm"], images["normal"],
                       normal_strength=spec["normal"])
    return material


def metric_uv(point, normal, coverage):
    """World-metre box projection; world Z is up on vertical faces."""
    width, height = coverage
    if abs(normal.z) < 0.707:
        tangent = Vector((normal.y, -normal.x, 0.0)).normalized()
        return ((point.x * tangent.x + point.y * tangent.y) / width, point.z / height)
    return (point.x / width, point.y / height)


def add_metric_uvs_per_slot(obj, slot_coverage):
    """UV-map only the faces whose material slot has a surface; others keep theirs."""
    mesh = obj.data
    uv = mesh.uv_layers[0] if mesh.uv_layers else mesh.uv_layers.new(name="UVMap")
    normal_matrix = obj.matrix_world.to_3x3().inverted().transposed()
    for polygon in mesh.polygons:
        coverage = slot_coverage.get(polygon.material_index)
        if coverage is None:
            continue
        normal = (normal_matrix @ polygon.normal).normalized()
        for loop_index in polygon.loop_indices:
            point = obj.matrix_world @ mesh.vertices[mesh.loops[loop_index].vertex_index].co
            uv.data[loop_index].uv = metric_uv(point, normal, coverage)
    mesh.update()


def apply_surfaces(meshes, *, prefix, texture_dir, placeholder_map):
    specs = load_surface_specs(texture_dir)
    unknown = sorted(set(placeholder_map.values()) - specs.keys())
    if unknown:
        raise RuntimeError(f"No authored maps in {texture_dir} for: {', '.join(unknown)}")
    counts = {}
    for obj in meshes:
        if obj.data.users > 1:
            obj.data = obj.data.copy()  # UVs are world-space; instances need their own
        slot_coverage = {}
        for index, material in enumerate(obj.data.materials):
            slug = placeholder_map.get(material.name) if material else None
            if slug is None:
                continue
            obj.data.materials[index] = runtime_material(prefix, slug, texture_dir, specs[slug])
            slot_coverage[index] = specs[slug]["coverage"]
            counts[slug] = counts.get(slug, 0) + 1
        if slot_coverage:
            add_metric_uvs_per_slot(obj, slot_coverage)
    return counts


def inspect_glb(path, prefix, expected_surfaces, reference=None):
    data = read_glb_json(path)
    names = [m.get("name", "") for m in data.get("materials", [])]
    surfaces = {i for i, name in enumerate(names) if name.startswith(prefix)}
    no_uv = [p for mesh in data.get("meshes", []) for p in mesh["primitives"]
             if p.get("material") in surfaces and "TEXCOORD_0" not in p["attributes"]]
    if len(surfaces) != expected_surfaces or no_uv:
        raise RuntimeError(f"{Path(path).name}: {len(surfaces)} surfaces "
                           f"(expected {expected_surfaces}), {len(no_uv)} textured primitives without UV0")
    if reference is not None:
        before = sorted(n.get("name", "") for n in read_glb_json(reference).get("nodes", []))
        after = sorted(n.get("name", "") for n in data.get("nodes", []))
        if before != after:
            raise RuntimeError(f"{Path(path).name}: node names changed; lost "
                               f"{sorted(set(before) - set(after))[:10]}, gained "
                               f"{sorted(set(after) - set(before))[:10]}")
    print(f"{Path(path).name}: {len(surfaces)} surface materials, "
          f"{len(data.get('images', []))} maps, {Path(path).stat().st_size / 1e6:.2f} MB", flush=True)


def texture_glb(public_glb, *, prefix, texture_dir, placeholder_map, expected_surfaces,
                stash_dir=STASH_DIR):
    public_glb = Path(public_glb)
    stash = Path(stash_dir) / public_glb.name
    if not has_surfaces(public_glb, prefix):
        stash.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(public_glb, stash)
        print(f"Stashed untextured source {stash.name}", flush=True)
    elif not stash.exists():
        raise RuntimeError(f"{public_glb.name} is already textured and has no untextured "
                           f"stash in {stash_dir}; re-run its create script first")

    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(stash))
    objects = list(bpy.context.scene.objects)
    meshes = [obj for obj in objects if obj.type == "MESH"]
    counts = apply_surfaces(meshes, prefix=prefix, texture_dir=texture_dir,
                            placeholder_map=placeholder_map)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(public_glb), export_format="GLB",
                              use_selection=True, export_apply=True, export_yup=True,
                              export_cameras=False, export_lights=False, export_extras=True)
    inspect_glb(public_glb, prefix, expected_surfaces, reference=stash)
    return counts
