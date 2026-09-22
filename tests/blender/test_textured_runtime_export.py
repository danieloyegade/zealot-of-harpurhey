"""Run:
    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python-exit-code 1 --python tests/blender/test_textured_runtime_export.py
"""
import json
import sys
import tempfile
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "blender" / "scripts"))

from commonSurfaces import plaster  # noqa: E402
from texturedRuntimeExport import read_glb_json, texture_glb  # noqa: E402
from vinylExchangeTextures import write_surface  # noqa: E402

PLACEHOLDERS = {"MAT_T_A_PLACEHOLDER": "t-a", "MAT_T_B_PLACEHOLDER": "t-b"}


def write_textures(directory):
    records = [write_surface(plaster(slug, "t", "#CCCCCC", seed=i, tile=tile, px=32),
                             texture_dir=directory)
               for i, (slug, tile) in enumerate((("t-a", 1.0), ("t-b", 0.5)))]
    (directory / "validation.json").write_text(json.dumps({"materials": records}))


def write_untextured_glb(path):
    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.mesh.primitive_cube_add(size=2.0)
    cube = bpy.context.active_object
    cube.name = "T_Cube"
    for name in (*PLACEHOLDERS, "MAT_T_Glass_PLACEHOLDER"):
        cube.data.materials.append(bpy.data.materials.new(name))
    for polygon in cube.data.polygons:
        polygon.material_index = polygon.index % 3
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=False)


def uv_span(obj, polygon):
    uv = obj.data.uv_layers[0].data
    us = [uv[i].uv[0] for i in polygon.loop_indices]
    vs = [uv[i].uv[1] for i in polygon.loop_indices]
    return max(max(us) - min(us), max(vs) - min(vs))


def run(public, textures, stash):
    return texture_glb(public, prefix="MAT_T_Surface_", texture_dir=textures,
                       placeholder_map=PLACEHOLDERS, expected_surfaces=2, stash_dir=stash)


def main():
    work = Path(tempfile.mkdtemp())
    textures, stash, public = work / "tex", work / "stash", work / "public" / "t.glb"
    textures.mkdir()
    public.parent.mkdir()
    write_textures(textures)
    write_untextured_glb(public)

    counts = run(public, textures, stash)
    assert counts == {"t-a": 1, "t-b": 1}, counts
    assert (stash / "t.glb").exists(), "untextured source was not stashed"

    cube = bpy.data.objects["T_Cube"]
    expected_span = {0: 2.0, 1: 4.0}          # 2 m face / 1.0 m tile, / 0.5 m tile
    for polygon in cube.data.polygons:
        want = expected_span.get(polygon.material_index)
        if want is not None:
            assert abs(uv_span(cube, polygon) - want) < 1e-4, (polygon.index, uv_span(cube, polygon))

    names = [m["name"] for m in read_glb_json(public)["materials"]]
    assert "MAT_T_Glass_PLACEHOLDER" in names and "MAT_T_Surface_t-a" in names, names

    # Idempotent: a second run reads the stash, not the textured output.
    assert run(public, textures, stash) == {"t-a": 1, "t-b": 1}

    # With the stash gone and the output already textured, it must refuse.
    (stash / "t.glb").unlink()
    try:
        run(public, textures, stash)
        raise AssertionError("re-texturing a textured GLB without a stash was allowed")
    except RuntimeError:
        pass
    print("texturedRuntimeExport: stash, per-slot UVs, export and guards are correct")


main()
