"""Export the approved Vinyl Exchange blockout for the game runtime.

The source scene deliberately keeps pavement, road, scale figures, cameras and
lights beside the authored building. Only ``VINYL_EXCHANGE_MASTER`` and its
descendants belong in the GLB; the world's existing systems own all context.

The source ``.blend`` remains the geometry-review master and therefore keeps
its legible placeholder palette.  This exporter performs the runtime material
pass in memory: it binds the generated Vinyl Exchange PBR sets, gives every
textured mesh metric box-projected UVs, then embeds the maps in the GLB.  That
keeps texture ownership in Blender without making the temporary blockout UVs a
dependency of the later facade-detail pass.
"""

import json
from pathlib import Path
import struct
import sys

import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLEND_PATH = PROJECT_ROOT / "blender" / "source" / "vinyl_exchange_blockout.blend"
GLB_PATH = PROJECT_ROOT / "public" / "assets" / "models" / "vinyl-exchange-blockout.glb"
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "vinyl-exchange"
MASTER_COLLECTION = "VINYL_EXCHANGE_MASTER"

sys.path.append(str(PROJECT_ROOT / "blender" / "scripts"))
from surfaceWeathering import build_pbr_material, load_image  # noqa: E402


# Metric coverage and normal strength come from the authored validation file.
# v_origin anchors bounded vertical materials to their real element bottoms;
# repeating materials use the same origin simply to keep courses aligned across
# separate objects and around the corner.
SURFACES = {
    "stone-painted-ashlar": {"coverage": (2.40, 2.40), "normal": 1.0, "v_origin": 4.30},
    "fascia-grey-panel": {"coverage": (1.35, 1.35), "normal": 1.0, "v_origin": 2.95},
    "logo-red-acrylic": {"coverage": (0.60, 0.60), "normal": 0.6, "v_origin": 0.0},
    "sign-black-panel": {"coverage": (1.00, 1.00), "normal": 0.7, "v_origin": 0.0},
    "frame-blue-paint": {"coverage": (0.30, 0.30), "normal": 1.0, "v_origin": 0.0},
    "shopfront-ribbed-alu": {"coverage": (0.64, 0.64), "normal": 1.0, "v_origin": 0.0},
    "tile-white-glazed": {"coverage": (1.20, 1.20), "normal": 1.0, "v_origin": 0.0},
    "door-green-paint": {"coverage": (1.15, 2.30), "normal": 1.0, "v_origin": 0.02},
    "grille-dark-steel": {"coverage": (0.50, 0.50), "normal": 1.0, "v_origin": 0.0},
}

PLACEHOLDER_SURFACES = {
    "MAT_VE_UpperStone_PLACEHOLDER": "stone-painted-ashlar",
    "MAT_VE_WindowFrames_PLACEHOLDER": "frame-blue-paint",
    "MAT_VE_GreyFascia_PLACEHOLDER": "fascia-grey-panel",
    "MAT_VE_RedLogo_PLACEHOLDER": "logo-red-acrylic",
    "MAT_VE_BlackSign_PLACEHOLDER": "sign-black-panel",
    "MAT_VE_TaglineStrip_PLACEHOLDER": "sign-black-panel",
    "MAT_VE_GreenPanel_PLACEHOLDER": "door-green-paint",
    "MAT_VE_WhiteTile_PLACEHOLDER": "tile-white-glazed",
    "MAT_VE_VentRecess_PLACEHOLDER": "grille-dark-steel",
}

DARK_STEEL_OBJECTS = {
    "VE_CornerSecurityGate",
    "VE_Vent_Dale_Frame",
    "VE_Vent_Oldham_Frame",
}


def surface_for_slot(obj, material):
    """Resolve a placeholder slot to one of the authored material sets."""
    if material is None:
        return None
    if material.name == "MAT_VE_Metal_PLACEHOLDER":
        # The blockout used one grey material for every metal. Split it now:
        # dark painted steel owns the gate and vent framing; the aluminium set
        # owns the shopfront piers, door/window frames and recess liners.
        return "grille-dark-steel" if obj.name in DARK_STEEL_OBJECTS else "shopfront-ribbed-alu"
    return PLACEHOLDER_SURFACES.get(material.name)


def build_runtime_materials():
    materials = {}
    for slug, spec in SURFACES.items():
        images = {
            kind: load_image(
                TEXTURE_DIR / f"{slug}-{kind}.png",
                non_color=kind != "basecolor",
            )
            for kind in ("basecolor", "orm", "normal")
        }
        material = bpy.data.materials.new(f"MAT_VE_Surface_{slug}")
        build_pbr_material(
            material,
            images["basecolor"],
            images["orm"],
            images["normal"],
            normal_strength=spec["normal"],
        )
        materials[slug] = material

    # The tagline is the same coated panel as the corner sign, but keeps a
    # separate runtime material so Three.js can apply its measured darker tint
    # without changing the corner sign box.
    tagline = materials["sign-black-panel"].copy()
    tagline.name = "MAT_VE_Surface_sign-black-panel-tagline"
    materials["sign-black-panel-tagline"] = tagline
    return materials


def add_metric_uvs(obj, coverage, v_origin):
    """Box-project UVs in metres, using world Z as up on vertical faces."""
    mesh = obj.data
    uv = mesh.uv_layers.get("UVMap") or mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.active = uv
    normal_matrix = obj.matrix_world.to_3x3().inverted().transposed()
    width, height = coverage

    for polygon in mesh.polygons:
        normal = (normal_matrix @ polygon.normal).normalized()
        horizontal = abs(normal.z) < 0.707
        if horizontal:
            tangent = Vector((normal.y, -normal.x, 0.0)).normalized()
        for loop_index in polygon.loop_indices:
            vertex = mesh.vertices[mesh.loops[loop_index].vertex_index]
            point = obj.matrix_world @ vertex.co
            if horizontal:
                u = (point.x * tangent.x + point.y * tangent.y) / width
                v = (point.z - v_origin) / height
            else:
                u = point.x / width
                v = point.y / height
            uv.data[loop_index].uv = (u, v)

    mesh.update()


def apply_runtime_surfaces(meshes):
    runtime_materials = build_runtime_materials()
    assignments = {slug: 0 for slug in SURFACES}

    for obj in meshes:
        textured_slugs = []
        for index, material in enumerate(obj.data.materials):
            slug = surface_for_slot(obj, material)
            if slug is None:
                continue
            target = slug
            if material.name == "MAT_VE_TaglineStrip_PLACEHOLDER":
                target = "sign-black-panel-tagline"
            obj.data.materials[index] = runtime_materials[target]
            textured_slugs.append(slug)
            assignments[slug] += 1

        if textured_slugs:
            if len(set(textured_slugs)) != 1:
                raise RuntimeError(f"{obj.name} requires more than one metric UV scale")
            spec = SURFACES[textured_slugs[0]]
            add_metric_uvs(obj, spec["coverage"], spec["v_origin"])

    missing = [slug for slug, count in assignments.items() if count == 0]
    if missing:
        raise RuntimeError(f"No runtime geometry assigned to: {', '.join(missing)}")
    print(
        "Runtime surface assignments: "
        + ", ".join(f"{slug}={count}" for slug, count in assignments.items()),
        flush=True,
    )


def inspect_glb():
    """Fail the export if maps or texture coordinates were dropped by glTF."""
    with GLB_PATH.open("rb") as handle:
        magic, version, _ = struct.unpack("<4sII", handle.read(12))
        if magic != b"glTF" or version != 2:
            raise RuntimeError("Runtime export is not a glTF 2 GLB")
        json_length, json_type = struct.unpack("<II", handle.read(8))
        if json_type != 0x4E4F534A:
            raise RuntimeError("Runtime GLB has no JSON chunk")
        data = json.loads(handle.read(json_length))

    textured = [
        material for material in data.get("materials", [])
        if material.get("name", "").startswith("MAT_VE_Surface_")
    ]
    primitives = [primitive for mesh in data.get("meshes", []) for primitive in mesh.get("primitives", [])]
    missing_uvs = [
        primitive for primitive in primitives
        if primitive.get("material") is not None
        and data["materials"][primitive["material"]].get("name", "").startswith("MAT_VE_Surface_")
        and "TEXCOORD_0" not in primitive.get("attributes", {})
    ]
    if len(textured) != 10 or len(data.get("images", [])) != 27 or missing_uvs:
        raise RuntimeError(
            "Incomplete runtime material export: "
            f"materials={len(textured)}, images={len(data.get('images', []))}, "
            f"textured primitives without UVs={len(missing_uvs)}"
        )
    print(
        f"Runtime GLB validation: {len(textured)} surface materials, "
        f"{len(data['images'])} embedded maps, all textured primitives have UV0",
        flush=True,
    )


def export_runtime_glb():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH))
    master = bpy.data.collections.get(MASTER_COLLECTION)
    if master is None:
        raise RuntimeError(f"Missing runtime collection: {MASTER_COLLECTION}")

    export_objects = list(master.all_objects)
    meshes = [obj for obj in export_objects if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError(f"{MASTER_COLLECTION} contains no mesh objects")

    apply_runtime_surfaces(meshes)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in export_objects:
        obj.hide_set(False)
        obj.hide_render = False
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]

    GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_cameras=False,
        export_lights=False,
    )
    inspect_glb()

    points = [
        obj.matrix_world @ Vector(corner)
        for obj in meshes
        for corner in obj.bound_box
    ]
    triangles = 0
    for obj in meshes:
        obj.data.calc_loop_triangles()
        triangles += len(obj.data.loop_triangles)

    print(f"Exported {GLB_PATH}", flush=True)
    print(
        "Runtime source bounds: "
        f"X {min(point.x for point in points):.3f}..{max(point.x for point in points):.3f}, "
        f"Y {min(point.y for point in points):.3f}..{max(point.y for point in points):.3f}, "
        f"Z {min(point.z for point in points):.3f}..{max(point.z for point in points):.3f}",
        flush=True,
    )
    print(
        f"Runtime collection: {len(export_objects)} objects, {len(meshes)} meshes, "
        f"{triangles} triangles",
        flush=True,
    )


if __name__ == "__main__":
    export_runtime_glb()
