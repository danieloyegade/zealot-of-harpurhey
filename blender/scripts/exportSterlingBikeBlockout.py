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
EXPORTS = {
    "STERLING_BIKE_MASTER": OUTPUT_DIR / "sterling-bike-blockout.glb",
    "STERLING_DOCK_MASTER": OUTPUT_DIR / "sterling-dock-blockout.glb",
}


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
    for collection_name, path in EXPORTS.items():
        export_master(collection_name, path)


if __name__ == "__main__":
    main()
