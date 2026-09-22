"""Surface materials for Renee (45-47 Thomas Street).

Palette measured from references/architecture/buildings/renae/ into
palette.json (measurePatch.py).  Builders from commonSurfaces.py.

Exterior colour comes from IMG_8039, the same frontage in flat overcast
light; renae-NQ is a sunny frame whose shaded facade takes a strong blue sky
cast (its brick measures a neutral mauve-grey), so it is not used.  The white
uPVC frames and sills sample near clipping.  Interior colour comes from
IMG_0932 and IMG_4910.  The brief (02_Renee.txt) says brick is to be carried
by PBR materials, not modelled.

What each set is for:

- `ren-brick`: warm red-brown brick of the upper floors.
- `ren-facade-black`: the matte black fascia, shutter box and shopfront frame.
- `ren-frame-paint`, `ren-stone`: white uPVC windows and white-painted sills.
- `ren-timber`: pale oak acoustic slats, perforated ceiling panels, shelving.
- `ren-wall-dark`: navy-painted interior walls.
- `ren-concrete`: polished concrete floor.
- `ren-metal`: dark metal fixtures.

Run:

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python-exit-code 1 --python blender/scripts/reneeTextures.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from commonSurfaces import (  # noqa: E402
    brick, concrete, load_palette, painted_metal, painted_render, painted_timber, plaster,
    run_texture_pass, timber,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "renee"
RENDER_DIR = PROJECT_ROOT / "renders" / "renee-textures"
PALETTE_PATH = TEXTURE_DIR / "palette.json"
P = load_palette(PALETTE_PATH, (
    "brick face", "brick mortar", "black facade", "window frame", "stone", "concrete",
    "timber light", "timber dark", "dark wall", "metal",
))

BUILDERS = (
    lambda: brick("ren-brick", "Red-brown brick upper floors",
                  P["brick face"], P["brick mortar"], P["black facade"], seed=6401,
                  face_spread=0.16, soot_amount=0.15),
    lambda: painted_render("ren-facade-black", "Matte black fascia, shutter box and shopfront",
                           P["black facade"], P["metal"], seed=6411, dirt_amount=0.12,
                           roughness=0.7),
    lambda: painted_render("ren-stone", "White-painted sills", P["stone"], P["concrete"],
                           seed=6421, dirt_amount=0.2, tile=1.20),
    lambda: concrete("ren-concrete", "Polished concrete floor", P["concrete"], seed=6431,
                     stain_amount=0.12, roughness=0.55),
    lambda: painted_metal("ren-metal", "Dark metal fixtures", P["metal"], seed=6441,
                          rust_amount=0.1, px=512),
    lambda: painted_timber("ren-frame-paint", "White uPVC window frames", P["window frame"],
                           seed=6451, tile=0.30, px=512, chips=0, gloss=0.35),
    lambda: timber("ren-timber", "Pale oak slats, ceiling panels and shelving",
                   P["timber light"], P["timber dark"], seed=6461),
    lambda: plaster("ren-wall-dark", "Navy-painted interior walls", P["dark wall"], seed=6471),
)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    run_texture_pass("renee", TEXTURE_DIR, RENDER_DIR, PALETTE_PATH, BUILDERS, argv)
