"""Run:
    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python-exit-code 1 --python tests/blender/test_common_surfaces.py
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "blender" / "scripts"))

from commonSurfaces import (  # noqa: E402
    ashlar, brick, concrete, glazed_tile, painted_metal, painted_render,
    painted_timber, plaster, timber,
)
from vinylExchangeTextures import seam_report  # noqa: E402


def cases():
    small = {"px": 128}
    return [
        (brick("t-brick", "t", "#8A4A3A", "#9A958C", "#3A3632", seed=1, **small), "#8A4A3A"),
        (ashlar("t-ashlar", "t", "#BBA48A", "#6C5B4F", "#3A332C", seed=2, **small), "#BBA48A"),
        (painted_metal("t-metal", "t", "#2A3F6A", seed=3, **small), "#2A3F6A"),
        (painted_timber("t-paint", "t", "#1E3A2A", seed=4, **small), "#1E3A2A"),
        (timber("t-timber", "t", "#B08A60", "#6A4A30", seed=5, px=(64, 128)), "#8E6C48"),
        (concrete("t-concrete", "t", "#8C8A84", seed=6, **small), "#8C8A84"),
        (plaster("t-plaster", "t", "#E8E0D2", seed=7, **small), "#E8E0D2"),
        (painted_render("t-render", "t", "#EDEBE4", "#5A5850", seed=8, **small), "#EDEBE4"),
        (glazed_tile("t-tile", "t", "#1F5A3A", "#CFC8B8", seed=9, **small), "#1F5A3A"),
        # Production size: joints on the tile edge only showed up as a seam at 1024.
        (ashlar("t-ashlar-full", "t", "#BBA48A", "#6C5B4F", "#3A332C", seed=2), "#BBA48A"),
        (brick("t-brick-full", "t", "#8A4A3A", "#9A958C", "#3A3632", seed=1), "#8A4A3A"),
        (brick("t-brick-accent", "t", "#8A4A3A", "#9A958C", "#3A3632", seed=1, px=256,
               accent="#8A4A3A"), "#8A4A3A"),
    ]


def hex_rgb(value):
    value = value.lstrip("#")
    return np.array([int(value[i:i + 2], 16) for i in (0, 2, 4)], float)


def main():
    failures = []
    for surface, dominant in cases():
        base, orm, normal = surface.maps()
        for name, grid in (("base", base), ("orm", orm), ("normal", normal)):
            if not np.isfinite(grid).all() or grid.min() < 0 or grid.max() > 1:
                failures.append(f"{surface.slug}: {name} map out of range")
        for axis, step in seam_report(surface, {"basecolor": base, "orm": orm, "normal": normal}).items():
            if step["wrap"] > max(3.0, step["typical"] * 3.0):
                failures.append(f"{surface.slug}: seam on {axis} ({step})")
        mean = np.array(surface.record()["base_srgb_mean"], float)
        if np.abs(mean - hex_rgb(dominant)).max() > 40:
            failures.append(f"{surface.slug}: mean {mean} drifted from {dominant}")

    try:
        brick("t-bad", "t", "#8A4A3A", "#9A958C", "#3A3632", seed=1, tile=1.0, px=64)
        failures.append("brick accepted a tile that is not a whole number of bricks")
    except ValueError:
        pass

    if failures:
        raise AssertionError("\n".join(failures))
    print("commonSurfaces: all builders tile, stay in range and hold their palette")


main()
