"""Surface materials for Gulliver's: the green-tiled J.W. Lees pub on Oldham Street.

Palette measured from references/architecture/buildings/gullivers/ into
palette.json (measurePatch.py).  DSC06338/DSC06339 are the witnesses: their
cream tiles measure neutral.  gullivers-manchester.jpg has a strong magenta/
blue cast (its green fascia reads grey-blue), so it is used only for the side
door, which the DSC frames do not show; it agrees with the DSC doorway green.
Builders from commonSurfaces.py.

What the references show:

- `gul-tile-green`: square bottle-green glazed tiles, stack-bonded with a
  pale grout, each tile a visibly different firing.  The glaze body is very dark (#092317); the brighter greens in
  the photographs are sky reflections, which the low roughness reproduces.
- `gul-tile-cream`: the cream inlay strips on the pilasters and bands under
  the windows, the same square module.
- `gul-tile-plinth`: the near-black plinth course.
- `gul-brick`: muted red-brown Victorian brick above the pub front, in
  shade.  Its mortar is the 95th luminance percentile of a distant patch, so
  partly the lighter bricks: a pinkish estimate.
- `gul-joinery-cream`, `gul-paint-green-trim`, `gul-paint-green-dark`,
  `gul-door`: cream cornice and frames, grey-green fascia, dark green doorway
  surrounds and the green panelled doors.
- `gul-metal-black`: vents and brackets.

The lettering, J.W. Lees plaques and cornice shadow stay as placeholders.

Run:

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python-exit-code 1 --python blender/scripts/gulliversTextures.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from commonSurfaces import (  # noqa: E402
    brick, glazed_tile, load_palette, painted_metal, painted_timber, run_texture_pass,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "gullivers"
RENDER_DIR = PROJECT_ROOT / "renders" / "gullivers-textures"
PALETTE_PATH = TEXTURE_DIR / "palette.json"
P = load_palette(PALETTE_PATH, (
    "green tile glaze", "cream tile glaze", "plinth tile glaze", "tile grout", "brick face",
    "brick mortar", "cream joinery", "green trim", "dark green", "door paint", "black metal",
))

SQUARE = (0.152, 0.152)

BUILDERS = (
    lambda: glazed_tile("gul-tile-green", "Bottle-green glazed tiles, 6 in square",
                        P["green tile glaze"], P["tile grout"], seed=6301, tile_size=SQUARE,
                        spread=0.35),
    lambda: glazed_tile("gul-tile-cream", "Cream inlay tiles, 6 in square",
                        P["cream tile glaze"], P["tile grout"], seed=6311, tile_size=SQUARE,
                        spread=0.12, px=512),
    lambda: glazed_tile("gul-tile-plinth", "Near-black plinth tiles, 9x6 in",
                        P["plinth tile glaze"], P["tile grout"], seed=6321,
                        tile_size=(0.228, 0.152), px=512),
    lambda: brick("gul-brick", "Victorian brick above the pub front",
                  P["brick face"], P["brick mortar"], P["plinth tile glaze"], seed=6331),
    lambda: painted_timber("gul-joinery-cream", "Cream cornice, consoles and window frames",
                           P["cream joinery"], seed=6341, px=512),
    lambda: painted_timber("gul-paint-green-trim", "Grey-green painted fascia",
                           P["green trim"], seed=6351, px=512),
    lambda: painted_timber("gul-paint-green-dark", "Dark green doorway surrounds",
                           P["dark green"], seed=6361, px=512),
    lambda: painted_timber("gul-door", "Green panelled doors", P["door paint"], seed=6371,
                           chips=24, px=512),
    lambda: painted_metal("gul-metal-black", "Vents and brackets", P["black metal"],
                          seed=6381, px=512),
)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    run_texture_pass("gullivers", TEXTURE_DIR, RENDER_DIR, PALETTE_PATH, BUILDERS, argv)
