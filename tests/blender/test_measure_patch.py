"""Run:
    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python-exit-code 1 --python tests/blender/test_measure_patch.py
"""
import json
import sys
import tempfile
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "blender" / "scripts"))

from measurePatch import patch_median, record_sample  # noqa: E402


def solid_png(path, top, bottom, size=(40, 20)):
    """Top half one colour, bottom half another, as an 8-bit PNG."""
    width, height = size
    image = bpy.data.images.new("t", width, height, alpha=True)
    grid = np.ones((height, width, 4), np.float32)
    grid[: height // 2, :, :3] = np.array(bottom) / 255.0   # Blender rows are bottom-up
    grid[height // 2:, :, :3] = np.array(top) / 255.0
    image.pixels.foreach_set(grid.ravel())
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()


def main():
    work = Path(tempfile.mkdtemp())
    photo = work / "p.png"
    solid_png(photo, top=(128, 64, 32), bottom=(10, 20, 30))

    top = np.round(patch_median(photo, (0, 0, 40, 10)) * 255)
    assert top.tolist() == [128, 64, 32], top          # y counts from the top
    bottom = np.round(patch_median(photo, (0, 10, 40, 20)) * 255)
    assert bottom.tolist() == [10, 20, 30], bottom

    # A box straddling both halves: the median lands on one half, the 85th
    # luminance percentile isolates the brighter (top) half, as for pale mortar.
    bright = np.round(patch_median(photo, (0, 4, 40, 20), percentile=85) * 255)
    assert bright.tolist() == [128, 64, 32], bright

    palette = work / "palette.json"
    assert record_sample(palette, "brick face", photo, (0, 0, 40, 10), "overcast") == "#804020"
    # A sunlit sample is scaled by 0.85, and the albedo is the mean of both samples:
    # (128+108.8)/2=118.4 -> 0x76, (64+54.4)/2=59.2 -> 0x3B, (32+27.2)/2=29.6 -> 0x1E.
    albedo = record_sample(palette, "brick face", photo, (0, 0, 40, 10), "sunlit")
    assert albedo == "#763B1E", albedo
    data = json.loads(palette.read_text())
    assert len(data["brick face"]["samples"]) == 2
    print("measurePatch: medians, orientation and albedo averaging are correct")


main()
