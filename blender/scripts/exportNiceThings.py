"""Export the approved Nice Things blockout for the game runtime, textured.

The source ``.blend`` written by ``createNiceThingsBlockout.py`` remains the
geometry-review master and keeps its legible placeholder palette.  This
exporter performs the runtime material pass in memory, the same way
``exportVinylExchangeBlockout.py`` does for Vinyl Exchange: it binds the PBR
sets written by ``niceThingsTextures.py``, gives every textured mesh metric
box-projected UVs, and embeds the maps in the GLB.

Run after ``createNiceThingsBlockout.py`` (which writes an untextured GLB to
the same path) and after ``niceThingsTextures.py``:

    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --factory-startup --python blender/scripts/exportNiceThings.py
"""

import json
from pathlib import Path
import struct
import sys

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLEND_PATH = PROJECT_ROOT / "blender" / "source" / "nice_things_blockout.blend"
GLB_PATH = PROJECT_ROOT / "public" / "assets" / "models" / "nice-things-blockout.glb"
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "nice-things"
MASTER_COLLECTION = "NICE_THINGS_MASTER"
REVIEW_ONLY = {"NT_Pavement_ReviewOnly"}

sys.path.append(str(PROJECT_ROOT / "blender" / "scripts"))
from exportVinylExchangeBlockout import add_metric_uvs  # noqa: E402
from surfaceWeathering import build_pbr_material, load_image  # noqa: E402


# Metric coverage matches each set's tile in niceThingsTextures.py.
SURFACES = {
    "pink-limewash": {"coverage": (2.40, 2.40), "normal": 0.8, "v_origin": 0.0},
    "pink-satin-joinery": {"coverage": (0.60, 0.60), "normal": 1.0, "v_origin": 0.0},
    "sandstone-ashlar": {"coverage": (2.28, 2.28), "normal": 1.0, "v_origin": 0.0},
    "sandstone-sooted": {"coverage": (2.28, 2.28), "normal": 1.0, "v_origin": 0.0},
    "white-painted-frame": {"coverage": (0.40, 0.40), "normal": 1.0, "v_origin": 0.0},
    "interior-plaster-warm": {"coverage": (2.00, 2.00), "normal": 0.6, "v_origin": 0.0},
    "floor-sealed-concrete": {"coverage": (2.00, 2.00), "normal": 0.6, "v_origin": 0.0},
    "birch-ply": {"coverage": (1.20, 1.20), "normal": 0.5, "v_origin": 0.0},
    "dark-painted-steel": {"coverage": (0.40, 0.40), "normal": 1.0, "v_origin": 0.0},
}

PLACEHOLDER_SURFACES = {
    "MAT_NT_Stone_PLACEHOLDER": "sandstone-ashlar",
    "MAT_NT_StoneShadow_PLACEHOLDER": "sandstone-sooted",
    "MAT_NT_PinkFacade_PLACEHOLDER": "pink-limewash",
    "MAT_NT_InteriorWall_PLACEHOLDER": "interior-plaster-warm",
    "MAT_NT_Floor_PLACEHOLDER": "floor-sealed-concrete",
    "MAT_NT_Furniture_PLACEHOLDER": "birch-ply",
    "MAT_NT_Metal_PLACEHOLDER": "dark-painted-steel",
}

# The blockout used one frame material everywhere.  The references split it:
# the shop's door and window frames are painted the shopfront pink, the bar
# over the display window is the dark roller-shutter box, and the upper sashes
# and the Central Buildings fanlight bars are white.
PINK_JOINERY_PREFIXES = ("NT_DoorFrame_", "NT_MainWindow_Frame_")
SHUTTER_BOX_OBJECTS = {"NT_WindowHead"}


def surface_for_slot(obj, material):
    """Resolve a placeholder slot to one of the authored material sets."""
    if material is None:
        return None
    if material.name == "MAT_NT_WindowFrames_PLACEHOLDER":
        if obj.name.startswith(PINK_JOINERY_PREFIXES):
            return "pink-satin-joinery"
        if obj.name in SHUTTER_BOX_OBJECTS:
            return "dark-painted-steel"
        return "white-painted-frame"
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
        material = bpy.data.materials.new(f"MAT_NT_Surface_{slug}")
        build_pbr_material(
            material,
            images["basecolor"],
            images["orm"],
            images["normal"],
            normal_strength=spec["normal"],
        )
        materials[slug] = material
    return materials


def apply_runtime_surfaces(meshes):
    runtime_materials = build_runtime_materials()
    assignments = {slug: 0 for slug in SURFACES}

    for obj in meshes:
        textured_slugs = []
        for index, material in enumerate(obj.data.materials):
            slug = surface_for_slot(obj, material)
            if slug is None:
                continue
            obj.data.materials[index] = runtime_materials[slug]
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

    def textured(index):
        return data["materials"][index].get("name", "").startswith("MAT_NT_Surface_")

    surfaces = [m for m in data.get("materials", []) if m.get("name", "").startswith("MAT_NT_Surface_")]
    primitives = [p for mesh in data.get("meshes", []) for p in mesh.get("primitives", [])]
    missing_uvs = [
        p for p in primitives
        if p.get("material") is not None and textured(p["material"])
        and "TEXCOORD_0" not in p.get("attributes", {})
    ]
    expected = len(SURFACES)
    if len(surfaces) != expected or len(data.get("images", [])) != expected * 3 or missing_uvs:
        raise RuntimeError(
            "Incomplete runtime material export: "
            f"materials={len(surfaces)}, images={len(data.get('images', []))}, "
            f"textured primitives without UVs={len(missing_uvs)}"
        )
    print(
        f"Runtime GLB validation: {len(surfaces)} surface materials, "
        f"{len(data['images'])} embedded maps, all textured primitives have UV0",
        flush=True,
    )


def export_runtime_glb():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH))
    master = bpy.data.collections.get(MASTER_COLLECTION)
    if master is None:
        raise RuntimeError(f"Missing runtime collection: {MASTER_COLLECTION}")

    export_objects = [obj for obj in master.all_objects if obj.name not in REVIEW_ONLY]
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
        # WebP, as the bus shelter and pallets use: PNG embedding came to
        # 22 MB for these nine sets.
        export_image_format="WEBP",
        export_image_quality=88,
    )
    inspect_glb()
    print(f"Exported {GLB_PATH} ({GLB_PATH.stat().st_size / 1e6:.1f} MB)", flush=True)


if __name__ == "__main__":
    export_runtime_glb()
