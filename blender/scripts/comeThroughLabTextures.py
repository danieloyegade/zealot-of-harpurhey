"""Surface materials for Come Through Lab (84 Silk Street), its drop box and drop-off props.

Palette measured from references/architecture/buildings/come-through-lab/ into
palette.json (measurePatch.py), sampled from single brick interiors and
voussoirs rather than wall-sized boxes, which let the pale lime mortar wash the
brick out.  Builders from commonSurfaces.py.

What the references show:

- `ctl-brick`: orange-red common brick in stretcher bond with pale lime
  mortar, weathered and streaked with street grime; about one brick in five
  is a darker purple-brown, and the rest vary widely in tone.
- `ctl-arch-brick`: the brief's polychrome arches (and the floor-divide band
  that uses the same material) alternate brighter orange bricks with slate
  blue-grey headers.
- `ctl-stone`: buff sandstone door surround, cornice and sills, greened by
  grime in the joints.
- `ctl-frame-paint`: grey-green painted joinery (fanlight panel, frames).
- `ctl-metal-paint`: the pale blue-grey window grilles and door furniture.
- `ctl-door-timber` / `ctl-door-timber-dark`: the honey-to-brown oak plank
  door and its darker seams.
- `ctl-dropbox-paint`: the black powder-coated drop box and holder.

Run:

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python-exit-code 1 --python blender/scripts/comeThroughLabTextures.py

Add `-- --no-render` to write the maps without the review renders.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from commonSurfaces import (  # noqa: E402
    ashlar, brick, load_palette, painted_metal, painted_timber, run_texture_pass, timber,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "come-through-lab"
RENDER_DIR = PROJECT_ROOT / "renders" / "come-through-lab-textures"
PALETTE_PATH = TEXTURE_DIR / "palette.json"
P = load_palette(PALETTE_PATH, (
    "brick face", "dark brick", "brick mortar", "blue brick", "arch brick face", "grime", "stone",
    "frame paint", "metal paint", "door timber light", "door timber dark", "dropbox paint",
))

BUILDERS = (
    lambda: brick("ctl-brick", "Historic frontage: orange-red stretcher-bond brick, lime mortar",
                  P["brick face"], P["brick mortar"], P["grime"], seed=6101,
                  face_spread=0.30, accent=P["dark brick"], accent_share=0.2),
    lambda: brick("ctl-arch-brick", "Polychrome arches and band: orange and blue-grey brick",
                  P["arch brick face"], P["brick mortar"], P["grime"], seed=6111,
                  soot_amount=0.2, tile=0.90, accent=P["blue brick"], accent_share=0.5),
    lambda: ashlar("ctl-stone", "Buff sandstone surround, cornice and sills",
                   P["stone"], P["grime"], P["grime"], seed=6121, tile=1.20),
    lambda: painted_timber("ctl-frame-paint", "Grey-green painted frames and fanlight panel",
                           P["frame paint"], seed=6131, tile=0.30, px=512),
    lambda: timber("ctl-door-timber", "Oak plank entrance door",
                   P["door timber light"], P["door timber dark"], seed=6141),
    lambda: timber("ctl-door-timber-dark", "Door plank seams and shadowed timber",
                   P["door timber dark"], P["door timber dark"], seed=6151, px=(256, 512)),
    lambda: painted_metal("ctl-metal-paint", "Pale blue-grey grilles and door furniture",
                          P["metal paint"], seed=6161, rust_amount=0.3, px=512),
    lambda: painted_metal("ctl-dropbox-paint", "Black powder-coated drop box and holder",
                          P["dropbox paint"], seed=6171, rust_amount=0.15, roughness=0.5),
)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    run_texture_pass("come-through-lab", TEXTURE_DIR, RENDER_DIR, PALETTE_PATH, BUILDERS, argv)
