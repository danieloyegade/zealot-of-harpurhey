"""Surface materials for the Greek Gyros kiosk.

Palette measured from references/architecture/infrastructure:objects/gyros/
into palette.json (measurePatch.py). Builders from commonSurfaces.py.

The blue panel set also carries a very restrained luminance-only wear layer
from ``source/blue-enamel-imagegen.png``.  The generated image is never used
as colour evidence: it is mirrored into a periodic field, reduced to five per
cent contrast, and applied over the measured blue.  This keeps the asset
reproducible while avoiding the large, directional scratches of a raw image.

Run:

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python-exit-code 1 --python blender/scripts/greekGyrosTextures.py
"""

import json
import sys
from pathlib import Path

import bpy
import numpy as np

sys.path.append(str(Path(__file__).resolve().parent))

from commonSurfaces import load_palette, painted_metal, run_texture_pass  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "greek-gyros"
RENDER_DIR = PROJECT_ROOT / "renders" / "greek-gyros-textures"
PALETTE_PATH = TEXTURE_DIR / "palette.json"
GENERATED_BLUE_SOURCE = TEXTURE_DIR / "source" / "blue-enamel-imagegen.png"
P = load_palette(
    PALETTE_PATH,
    ("white panel", "blue panel", "deep blue panel", "dark metal", "steel"),
)


def add_generated_blue_wear(surface):
    """Add low-contrast periodic wear from the retained generated source."""
    image = bpy.data.images.load(str(GENERATED_BLUE_SOURCE), check_existing=False)
    width, height = image.size
    pixels = np.empty(width * height * 4, np.float32)
    image.pixels.foreach_get(pixels)
    bpy.data.images.remove(image)

    rgb = pixels.reshape(height, width, 4)[..., :3]
    luminance = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    yi = np.linspace(0, height - 1, surface.h_px).astype(np.int32)
    xi = np.linspace(0, width - 1, surface.w_px).astype(np.int32)
    wear = luminance[np.ix_(yi, xi)]
    # Mirroring opposite sides makes both axes periodic by construction.
    wear = (wear + wear[::-1, :] + wear[:, ::-1] + wear[::-1, ::-1]) * 0.25
    wear = (wear - wear.mean()) / max(float(wear.std()), 1e-6)
    wear = np.clip(wear, -1.5, 1.5)
    surface.base *= (1.0 + wear[..., None] * 0.035).astype(np.float32)
    surface.roughen(np.clip(0.5 - wear * 0.25, 0.0, 1.0), 0.56, 0.18)
    return surface


def blue_panel():
    surface = painted_metal(
        "gg-panel-blue",
        "Blue enamelled kiosk panels with restrained generated wear",
        P["blue panel"],
        seed=6611,
        rust_amount=0.08,
        chips=8,
        roughness=0.42,
    )
    return add_generated_blue_wear(surface)


BUILDERS = (
    lambda: painted_metal(
        "gg-panel-white",
        "Warm white enamelled kiosk panels",
        P["white panel"],
        seed=6601,
        rust_amount=0.08,
        chips=6,
        roughness=0.40,
    ),
    blue_panel,
    lambda: painted_metal(
        "gg-panel-deep-blue",
        "Deep blue secondary fascia band",
        P["deep blue panel"],
        seed=6621,
        rust_amount=0.08,
        chips=6,
        roughness=0.42,
    ),
    lambda: painted_metal(
        "gg-metal-dark",
        "Dark metal frame and roof edge",
        P["dark metal"],
        seed=6631,
        rust_amount=0.12,
        px=512,
    ),
    lambda: painted_metal(
        "gg-metal-steel",
        "Stainless counter, cladding and fittings",
        P["steel"],
        seed=6641,
        rust_amount=0.03,
        chips=0,
        roughness=0.35,
        metallic=0.9,
        px=512,
    ),
)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    run_texture_pass("greek-gyros", TEXTURE_DIR, RENDER_DIR, PALETTE_PATH, BUILDERS, argv)
    validation_path = TEXTURE_DIR / "validation.json"
    validation = json.loads(validation_path.read_text())
    validation["generated_sources"] = [
        {
            "path": str(GENERATED_BLUE_SOURCE.relative_to(PROJECT_ROOT)),
            "role": "luminance-only micro-wear for gg-panel-blue; measured palette remains authoritative",
            "tool": "built-in ImageGen",
            "prompt": (
                "Seamless square texture of the blue enamelled metal panel surface visible on the "
                "Greek Gyros kiosk references; muted cobalt-blue paint, subtle age, restrained "
                "chalking and fine scratches; flat diffuse material capture; no lighting gradient, "
                "text, logos, flags, food, people, borders or watermark."
            ),
        }
    ]
    validation_path.write_text(json.dumps(validation, indent=2) + "\n")
