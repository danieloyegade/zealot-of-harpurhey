"""Surface materials for Real Camera (Sevendale House, Dale Street).

Palette measured from references/architecture/buildings/real-camera/EXT/rc.jpg
into palette.json (measurePatch.py). Builders from commonSurfaces.py.

The brief (13_Real_Camera.txt) centres the ornate red sandstone/terracotta
architecture. What the reference shows:

- `rc-sandstone-light`: the upper-floor facade, a pale salmon-pink sandstone
  in daylight.
- `rc-sandstone-dark`: the ground-floor piers and reveals, the same stone in
  shadow -- noticeably darker and more red-brown.
- `rc-sandstone-red`: the moulded string course and dressings, a warmer,
  more saturated red between the two.
- `rc-frame-paint`: near-black painted upper-window frames.
- `rc-trim-green` (MAT_RC_ShopTrimGreen): the entrance doors measure a muted
  sage-grey rather than a vivid green; kept as measured.
- `rc-shopfront-black`: the dark timber shopfront joinery around the display
  windows.
- `rc-shutter`: the pale grey aluminium roller shutter.
- `rc-metal`, `rc-display-wood`, `rc-interior-wall`: no clean isolated
  sample exists in the references (railings too thin, interior mostly out
  of frame); these keep the approved blockout's own colours, recorded as
  such in palette.json.

The maroon awning ("the Real Camera Co") carries lettering and stays a flat
placeholder, along with the other signage and glazing.

Run:

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python-exit-code 1 --python blender/scripts/realCameraTextures.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from commonSurfaces import (  # noqa: E402
    ashlar, load_palette, painted_metal, painted_timber, plaster, run_texture_pass, timber,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "real-camera"
RENDER_DIR = PROJECT_ROOT / "renders" / "real-camera-textures"
PALETTE_PATH = TEXTURE_DIR / "palette.json"
P = load_palette(PALETTE_PATH, (
    "light sandstone", "dark sandstone", "red sandstone", "frame paint", "trim door",
    "shopfront black", "shutter", "metal", "display wood", "interior wall",
))

BUILDERS = (
    lambda: ashlar("rc-sandstone-light", "Upper facade: pale salmon sandstone",
                   P["light sandstone"], P["dark sandstone"], P["dark sandstone"],
                   seed=6501, soot_amount=0.1),
    lambda: ashlar("rc-sandstone-dark", "Ground-floor piers and reveals, in shadow",
                   P["dark sandstone"], P["dark sandstone"], P["dark sandstone"],
                   seed=6511, soot_amount=0.3),
    lambda: ashlar("rc-sandstone-red", "Moulded string course and dressings",
                   P["red sandstone"], P["dark sandstone"], P["dark sandstone"], seed=6521),
    lambda: painted_timber("rc-frame-paint", "Painted upper-window frames", P["frame paint"],
                           seed=6531, tile=0.30, px=512),
    lambda: painted_timber("rc-trim-green", "Entrance doors: measured sage-grey",
                           P["trim door"], seed=6541, px=512),
    lambda: painted_timber("rc-shopfront-black", "Dark shopfront joinery", P["shopfront black"],
                           seed=6551),
    lambda: painted_metal("rc-shutter", "Pale grey aluminium roller shutter", P["shutter"],
                          seed=6561, rust_amount=0.1, roughness=0.35),
    lambda: painted_metal("rc-metal", "Ironwork and window security bars", P["metal"],
                          seed=6571, rust_amount=0.35, px=512),
    lambda: timber("rc-display-wood", "Counter and display woodwork", P["display wood"],
                   P["display wood"], seed=6581, finish=0.6),
    lambda: plaster("rc-interior-wall", "Interior walls seen through the glazing",
                    P["interior wall"], seed=6591),
)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    run_texture_pass("real-camera", TEXTURE_DIR, RENDER_DIR, PALETTE_PATH, BUILDERS, argv)
