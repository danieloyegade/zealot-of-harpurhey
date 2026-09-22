"""Surface materials for the approved Dreams greybox.

The only photograph of the building itself in references/architecture/
buildings/dreams/ is `Dreams.jpg`, a floodlit night frame; the other files are
a game render, a video still and a textile piece, and are not colour
witnesses.  Floodlit surfaces are measured from it (the brick from its two
best-lit patches, beside the shutter and along the plinth, as `shaded`; the
sodium-yellowed left shutter is skipped for the neutral centre one).  Surfaces the photograph leaves unlit or out of frame -- roof
planes, fascia, gutters, the ramp concrete -- keep the approved greybox's own
colours, recorded as such in palette.json.  The brick joints are blurred into
the brick, so the mortar is the 99.5th luminance percentile of the return: a
lower bound on how pale it really is.

What each set is for:

- `drm-cladding`: off-white profiled cladding of the gable, wings and upper wall.
- `drm-signboard`: the white signboard behind the lettering.
- `drm-shutter` / `drm-shutter-frame`: cream roller shutters in white guides
  and fascia; the corrugation is geometry, so the set is a plain coated steel.
- `drm-brick`: red brick plinth, return and platform base.  The greybox's
  per-joint mortar strips are hidden at runtime now that the brick carries
  its own joints.
- `drm-roof`, `drm-roof-trim`: roof sheet, fascia and gutters.
- `drm-rail`, `drm-concrete`: the access-ramp handrails and landing.

Run:

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python-exit-code 1 --python blender/scripts/dreamsGreyboxTextures.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from commonSurfaces import (  # noqa: E402
    brick, concrete, load_palette, painted_metal, run_texture_pass,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "dreams-greybox"
RENDER_DIR = PROJECT_ROOT / "renders" / "dreams-greybox-textures"
PALETTE_PATH = TEXTURE_DIR / "palette.json"
P = load_palette(PALETTE_PATH, (
    "cladding", "signboard", "shutter", "shutter frame", "rail", "brick face", "brick mortar",
    "roof", "roof trim", "concrete",
))

BUILDERS = (
    lambda: painted_metal("drm-cladding", "Off-white profiled cladding: gable, wings, upper wall",
                          P["cladding"], seed=7001, rust_amount=0.12, roughness=0.5, px=512),
    lambda: painted_metal("drm-signboard", "White signboard backing",
                          P["signboard"], seed=7011, rust_amount=0.05, chips=6,
                          roughness=0.4, px=512),
    lambda: painted_metal("drm-shutter", "Cream coated-steel roller shutters",
                          P["shutter"], seed=7021, rust_amount=0.2, px=512),
    lambda: painted_metal("drm-shutter-frame", "White shutter guides, head boxes and fascia",
                          P["shutter frame"], seed=7031, rust_amount=0.15, px=512),
    lambda: brick("drm-brick", "Red brick plinth, return and platform base",
                  P["brick face"], P["brick mortar"], P["roof"], seed=7041,
                  face_spread=0.16, soot_amount=0.15),
    lambda: painted_metal("drm-roof", "Dark roof sheet", P["roof"], seed=7051,
                          rust_amount=0.35, px=512),
    lambda: painted_metal("drm-roof-trim", "Fascia, ridge cap and gutters",
                          P["roof trim"], seed=7061, rust_amount=0.2, px=512),
    lambda: painted_metal("drm-rail", "Pale grey painted handrails", P["rail"], seed=7071,
                          rust_amount=0.25, px=512),
    lambda: concrete("drm-concrete", "Ramp and landing concrete", P["concrete"], seed=7081,
                     stain_amount=0.12),
)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    run_texture_pass("dreams-greybox", TEXTURE_DIR, RENDER_DIR, PALETTE_PATH, BUILDERS, argv)
