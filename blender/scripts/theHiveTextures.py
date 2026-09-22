"""Surface materials for The Hive (Arts Council England, Lever Street).

Palette measured from references/architecture/buildings/arts-council/ into
palette.json (measurePatch.py).  Builders from commonSurfaces.py.

What the references show:

- `hive-brick-black`: the lower floors are charcoal engineering brick, crisp
  and even, with recessed joints that read darker than the faces.
- `hive-brick-pale`: the upper towers are buff brick with a fine joint a
  shade lighter than the brick -- too fine to box, so the mortar is the 85th
  luminance percentile of a brick-and-joint patch.
- `hive-concrete`: the chunky in-situ ground-floor columns, pale and
  water-stained.
- `hive-metal-dark`: bronze-brown powder coat on the entrance portal, canopy
  and window frames.
- `hive-render-white`: the set-back white render level between the brick
  volumes.
- `hive-timber-interior`: the pale oak window and display frames seen
  through the glazing.

The perforated bird-motif screens (`MAT_MetalScreen_PLACEHOLDER`) keep their
runtime translucency and are left for a later pass.

Run:

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python-exit-code 1 --python blender/scripts/theHiveTextures.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from commonSurfaces import (  # noqa: E402
    brick, concrete, load_palette, painted_metal, painted_render, run_texture_pass, timber,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "the-hive"
RENDER_DIR = PROJECT_ROOT / "renders" / "the-hive-textures"
PALETTE_PATH = TEXTURE_DIR / "palette.json"
P = load_palette(PALETTE_PATH, (
    "black brick face", "black brick mortar", "pale brick face", "pale brick mortar",
    "concrete", "dark metal", "white wall", "timber light", "timber dark",
))

BUILDERS = (
    lambda: brick("hive-brick-black", "Charcoal engineering brick, recessed dark joints",
                  P["black brick face"], P["black brick mortar"], P["black brick mortar"],
                  seed=6201, face_spread=0.10, soot_amount=0.10, overburnt=0.0),
    lambda: brick("hive-brick-pale", "Buff brick upper towers, fine pale joint",
                  P["pale brick face"], P["pale brick mortar"], P["concrete"],
                  seed=6211, face_spread=0.12, soot_amount=0.12, overburnt=0.0),
    lambda: concrete("hive-concrete", "In-situ concrete columns", P["concrete"], seed=6221,
                     stain_amount=0.12),
    lambda: painted_metal("hive-metal-dark", "Bronze-brown powder-coated portal and frames",
                          P["dark metal"], seed=6231, rust_amount=0.1, roughness=0.45,
                          px=512),
    lambda: painted_render("hive-render-white", "White render set-back level",
                           P["white wall"], P["concrete"], seed=6241, dirt_amount=0.15),
    lambda: timber("hive-timber-interior", "Pale oak frames seen through the glazing",
                   P["timber light"], P["timber dark"], seed=6251),
)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    run_texture_pass("the-hive", TEXTURE_DIR, RENDER_DIR, PALETTE_PATH, BUILDERS, argv)
