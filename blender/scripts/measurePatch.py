"""Measure the median colour of a rectangle in a reference photograph.

The building texture passes anchor every albedo on a patch median sampled from
the photographs in `references/` (see MEASURED in vinylExchangeTextures.py).
This records those samples in the building's `palette.json` and derives the
authored albedo with one explicit de-lighting rule: a sunlit sample is scaled
by 0.85, a shaded one by 1.15, an overcast one is taken as-is, and the albedo
is the mean of all samples for that key.  Only the median colour is stored;
no pixels from the photograph reach any output.

Coordinates are pixels from the photograph's top-left, as an image viewer
shows them.  Blender cannot read HEIC or AVIF; convert those first with
`sips -s format jpeg <in> --out <scratch>.jpg`.  Blender ignores EXIF
rotation, so check the photo's orientation in the printed size.

Run:

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python blender/scripts/measurePatch.py -- \
        <palette.json> "<key>" <photo> <x0> <y0> <x1> <y1> <sunlit|shaded|overcast>
"""

import json
import sys
from pathlib import Path

import bpy
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LIGHT_SCALE = {"overcast": 1.0, "sunlit": 0.85, "shaded": 1.15}


def to_hex(rgb):
    return "#" + "".join(f"{int(round(float(v) * 255)):02X}" for v in np.clip(rgb, 0, 1))


def from_hex(value):
    value = value.lstrip("#")
    return np.array([int(value[i:i + 2], 16) for i in (0, 2, 4)], float) / 255.0


def patch_median(photo, box):
    """Median sRGB (0-1) of box = (x0, y0, x1, y1), y from the top."""
    image = bpy.data.images.load(str(photo), check_existing=False)
    width, height = image.size
    x0, y0, x1, y1 = box
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise SystemExit(f"box {box} lies outside {Path(photo).name} ({width}x{height})")
    pixels = np.empty(width * height * 4, np.float32)
    image.pixels.foreach_get(pixels)
    bpy.data.images.remove(image)
    grid = pixels.reshape(height, width, 4)[::-1]  # top row first
    return np.median(grid[y0:y1, x0:x1, :3].reshape(-1, 3), axis=0)


def record_sample(palette_path, key, photo, box, light):
    if light not in LIGHT_SCALE:
        raise SystemExit(f"light must be one of {', '.join(LIGHT_SCALE)}")
    palette_path, photo = Path(palette_path), Path(photo)
    data = json.loads(palette_path.read_text()) if palette_path.exists() else {}
    srgb = patch_median(photo, box)
    try:
        shown = str(photo.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        shown = photo.name
    entry = data.setdefault(key, {"samples": []})
    entry["samples"].append({"photo": shown, "box": list(box), "light": light,
                             "srgb": to_hex(srgb)})
    corrected = [np.clip(from_hex(s["srgb"]) * LIGHT_SCALE[s["light"]], 0, 1)
                 for s in entry["samples"]]
    entry["albedo"] = to_hex(np.mean(corrected, axis=0))
    palette_path.parent.mkdir(parents=True, exist_ok=True)
    palette_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return entry["albedo"]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(argv) != 8:
        raise SystemExit(__doc__)
    palette, key, photo = argv[0], argv[1], argv[2]
    box = tuple(int(v) for v in argv[3:7])
    albedo = record_sample(palette, key, photo, box, argv[7])
    print(f"{key}: albedo {albedo}", flush=True)


if __name__ == "__main__":
    main()
