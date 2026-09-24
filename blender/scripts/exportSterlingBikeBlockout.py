"""Export the Sterling Bikes blockout masters as two separate runtime GLBs.

Opens the reviewed `sterling_bike_blockout.blend` produced by
`createSterlingBikeBlockout.py` and exports STERLING_BIKE_MASTER and
STERLING_DOCK_MASTER on their own, so a bike is never baked into a dock and
game code controls station occupancy (brief sections 36-37 and 51). The review
ground, lights, cameras and the STERLING_STATION_REFERENCE instances are not
exported. Hierarchy, pivots and anchor empties are kept as glTF nodes.

Run from the repository root:
  /Applications/Blender.app/Contents/MacOS/Blender --background \
    blender/source/sterling-bike/sterling_bike_blockout.blend \
    --python blender/scripts/exportSterlingBikeBlockout.py
"""

from __future__ import annotations

from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "public" / "assets" / "models" / "sterling-bike"
TEXTURE_DIR = ROOT / "blender" / "source" / "textures" / "sterling-bike"
EXPORTS = {
    "STERLING_BIKE_MASTER": OUTPUT_DIR / "sterling-bike-blockout.glb",
    "STERLING_DOCK_MASTER": OUTPUT_DIR / "sterling-dock-blockout.glb",
}


def bake_procedural_materials() -> None:
    """Bake the reviewed Blender finishes to UV maps that glTF can carry.

    glTF exports Principled constants and a few extensions, but not Blender's
    Noise/Map Range/Bump node trees. Bake in memory so the authored .blend and
    its review renders retain their original procedural materials.
    """
    TEXTURE_DIR.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    # Direct procedural channels are deterministic; extra path samples only
    # multiply bake time without improving these maps.
    scene.cycles.samples = 1
    scene.cycles.device = "CPU"
    scene.render.bake.margin = 4
    meshes = sorted({obj for name in EXPORTS
                     for obj in bpy.data.collections[name].all_objects
                     if obj.type == "MESH"}, key=lambda obj: obj.name)
    materials = {mat for obj in meshes for mat in obj.data.materials if mat}

    for mat in sorted(materials, key=lambda value: value.name):
        users = [obj for obj in meshes if mat.name in obj.data.materials]
        bsdf = next(node for node in mat.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
        channels = [
            ("color", "DIFFUSE", bsdf.inputs["Base Color"], 1024),
            ("roughness", "ROUGHNESS", bsdf.inputs["Roughness"], 512),
            ("normal", "NORMAL", bsdf.inputs["Normal"], 1024),
        ]
        channels = [item for item in channels if item[2].is_linked]
        # Eighty-two tiny spokes, bolts and tubes share the metal finish. A
        # 1024 px atlas gives each too few texels to retain its 0.04-strength
        # bump and makes Cycles bake 82 full images. Keep its authored brushed
        # anisotropy and roughness map, but omit that imperceptible normal map.
        if len(users) > 40:
            channels = [item for item in channels if item[0] != "normal"]
        if not channels:
            continue

        # A single UV atlas per shared material keeps every bike/dock instance
        # on the same material and preserves the articulation hierarchy.
        if bpy.context.object and bpy.context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        for obj in users:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = users[0]
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(island_margin=0.012)
        bpy.ops.object.mode_set(mode="OBJECT")

        texture_nodes = {}
        for suffix, bake_type, socket, size in channels:
            image = bpy.data.images.new(f"{mat.name}_{suffix}", width=size, height=size, alpha=False)
            if suffix != "color":
                image.colorspace_settings.name = "Non-Color"
            node = mat.node_tree.nodes.new("ShaderNodeTexImage")
            node.image = image
            mat.node_tree.nodes.active = node
            texture_nodes[suffix] = node
            if suffix == "color":
                scene.render.bake.use_pass_direct = False
                scene.render.bake.use_pass_indirect = False
                scene.render.bake.use_pass_color = True
            bpy.ops.object.bake(type=bake_type)
            image.filepath_raw = str(TEXTURE_DIR / f"{mat.name}_{suffix}.png")
            image.file_format = "PNG"
            image.save()
            print(f"Baked {mat.name} {suffix} ({len(users)} meshes)")

        links = mat.node_tree.links
        if "color" in texture_nodes:
            links.new(texture_nodes["color"].outputs["Color"], bsdf.inputs["Base Color"])
        if "roughness" in texture_nodes:
            links.new(texture_nodes["roughness"].outputs["Color"], bsdf.inputs["Roughness"])
        if "normal" in texture_nodes:
            normal_map = mat.node_tree.nodes.new("ShaderNodeNormalMap")
            links.new(texture_nodes["normal"].outputs["Color"], normal_map.inputs["Color"])
            links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])


def export_master(collection_name: str, path: Path) -> None:
    source = bpy.data.collections[collection_name]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in source.all_objects:
        # View A-D hid the co-located dock master for rendering; the export
        # must not inherit that render state, only the selection.
        obj.hide_set(False)
        obj.select_set(True)
    bpy.context.view_layer.objects.active = bpy.data.objects[collection_name]
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_extras=True,
        export_cameras=False,
        export_lights=False,
    )
    print(f"Exported {collection_name} -> {path}")


def rename_pivot_notes() -> None:
    # The blockout labels its articulated empties with a descriptive "pivot"
    # string ("rear axle"). glTF extras become three.js userData, and the r185
    # GLTFLoader reads `userData.pivot` as a GLTFExporter pivot container: the
    # string becomes a NaN Object3D.pivot and the node's whole subtree
    # disappears. Rename it in memory only; this script never saves the .blend.
    for obj in bpy.data.objects:
        if "pivot" in obj:
            obj["pivot_note"] = obj["pivot"]
            del obj["pivot"]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rename_pivot_notes()
    bake_procedural_materials()
    for collection_name, path in EXPORTS.items():
        export_master(collection_name, path)


if __name__ == "__main__":
    main()
