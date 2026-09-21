"""Surface materials for Nice Things and the Central Buildings frontage.

The blockout (`createNiceThingsBlockout.py`) carries flat placeholder
materials.  This script authors the asset's first real surfaces as tiling PBR
sets at metric scale, in the same glTF convention and with the same `Surface`
toolkit as `vinylExchangeTextures.py` (sRGB base colour, ORM, OpenGL normal),
under `blender/source/textures/nice-things/`.

The same reasoning applies as for Vinyl Exchange: the geometry is still the
approved blockout, so an atlas baked on its UVs would be discarded with it.
These sets describe what each material is, so they survive the second
geometry pass.  Weathering that depends on where it sits on the building (the
soot under one cornice, the graffiti on the Central Buildings pier, the scuffs
at the shop door) is left for a later atlas bake.

What the references show, and what each set is for:

- `pink-limewash`: the shopfront is not flat pink paint.  It is a trowelled
  or brushed limewash finish with visible swirling strokes, lighter salmon on
  darker rose, over boarded panels with faint butt joints.  This is the
  asset's identity, so it gets the finest texel density.
- `pink-satin-joinery`: the door and window frames are the same pink in a
  denser, smoother satin paint that reads darker in shade.
- `sandstone-ashlar`: the buff Victorian sandstone of the upper facade and the
  Central Buildings piers, in coursed ashlar with soot washing down the faces.
- `sandstone-sooted`: the same stone where it projects (string courses,
  cornice, balcony slab, lintels) and where it is black at pavement level.
- `white-painted-frame`: the upper sashes are white-painted, with the grey
  dirt film that city frames carry.
- `interior-plaster-warm`, `floor-sealed-concrete`, `birch-ply` and
  `dark-painted-steel`: the interior shell, the display furniture, and the
  shutter box and door furniture.

The palette is measured, not invented: every colour is anchored on a patch
median sampled from the photographs in
`references/architecture/buildings/florist/` (see MEASURED), then de-lit by
hand.  No pixels from the references reach the output.

Run:

    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --factory-startup --python blender/scripts/niceThingsTextures.py

Add `-- --no-render` to write the maps without the review renders.
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.append(str(Path(__file__).resolve().parent))

from surfaceWeathering import F, smoothstep  # noqa: E402
from vinylExchangeTextures import (  # noqa: E402
    Surface,
    contact_sheet,
    lin,
    review_render,
    write_surface,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "nice-things"
RENDER_DIR = PROJECT_ROOT / "renders" / "nice-things-textures"

MCRFINEST = "nice-things-jun-2023-mcrfinest-2-scaled.jpg"
INSTAGRAM = "nice.things.plant_.shop_271673900_403213688227475_1875144679113432539_n.jpg"

# Patch medians from the reference photographs, as sRGB hex.  The overcast
# mcrfinest frame is the more neutral witness; the Instagram frame is warm
# low sun and pushes the pink towards coral, so it bounds the hue and does not
# set it.
MEASURED = {
    "pink fascia, overcast":         (MCRFINEST, "#E6B5A7"),
    "pink fascia band, overcast":    (MCRFINEST, "#D69C8F"),
    "pink plinth, overcast":         (MCRFINEST, "#D49687"),
    "pink fascia, low sun":          (INSTAGRAM, "#ED9B83"),
    "pink plinth, low sun":          (INSTAGRAM, "#F39E85"),
    "pink door frame, shaded":       (MCRFINEST, "#BA7360"),
    "sandstone upper wall":          (MCRFINEST, "#BBA48A"),
    "sandstone upper pilaster":      (MCRFINEST, "#9E8A73"),
    "sandstone pier, Central Bldgs": (MCRFINEST, "#AB967F"),
    "sandstone pier base, sooted":   (MCRFINEST, "#6C5B4F"),
    "upper sash (frame + glass)":    (MCRFINEST, "#748888"),
}


# ----------------------------------------------------------------- helpers

def brush_strokes(s, count, seed, length, width, angles, curl=0.25, dark_bias=0.5):
    """Soft, streaked limewash strokes as (field, sign) pairs.

    Each stroke is a curved, tapered ellipse with bristle striations running
    along its length.  Strokes are returned as a lighter field and a darker
    field, because limewash is laid wet over wet: some passes lift pigment
    and some deposit it.
    """
    rng = np.random.default_rng(seed)
    light = np.zeros(s.shape, F)
    dark = np.zeros(s.shape, F)
    for _ in range(count):
        cx, cy = rng.uniform(0, s.width), rng.uniform(0, s.height)
        half_l = rng.uniform(*length) * 0.5
        half_w = rng.uniform(*width) * 0.5
        angle = rng.uniform(*angles) + (np.pi if rng.random() < 0.5 else 0.0)
        bend = rng.uniform(-curl, curl) / max(half_l, 1e-3)
        strength = rng.uniform(0.35, 1.0)
        target = dark if rng.random() < dark_bias else light

        reach = half_l + half_w
        ix0 = int(np.floor((cx - reach) / s.texel_x))
        ix1 = int(np.ceil((cx + reach) / s.texel_x))
        iy0 = int(np.floor((cy - reach) / s.texel_y))
        iy1 = int(np.ceil((cy + reach) / s.texel_y))
        xs = np.arange(ix0, ix1 + 1)
        ys = np.arange(iy0, iy1 + 1)
        if not s.tile_u:
            xs = xs[(xs >= 0) & (xs < s.w_px)]
        if not s.tile_v:
            ys = ys[(ys >= 0) & (ys < s.h_px)]
        if not len(xs) or not len(ys):
            continue
        dx = ((xs + 0.5) * s.texel_x - cx)[None, :]
        dy = ((ys + 0.5) * s.texel_y - cy)[:, None]
        ca, sa = np.cos(angle), np.sin(angle)
        u = dx * ca + dy * sa
        v = -dx * sa + dy * ca
        v = v - bend * u * u  # the wrist's arc
        along = np.clip(np.abs(u) / half_l, 0.0, 1.5)
        # Loaded at the start, dry at the tail.
        load = np.where(u < 0, 1.0 - 0.25 * along, 1.0 - 0.75 * along ** 1.5)
        body = smoothstep(1.0, 0.55, along) * smoothstep(1.0, 0.35, np.abs(v) / half_w)
        phase = rng.uniform(0, 2 * np.pi, 3)
        bristle = (0.72 + 0.16 * np.sin(v / half_w * 7.0 + phase[0])
                   + 0.12 * np.sin(v / half_w * 19.0 + phase[1]))
        mark = np.clip(body * load * bristle * strength, 0.0, 1.0).astype(F)
        xi = np.mod(xs, s.w_px) if s.tile_u else xs
        yi = np.mod(ys, s.h_px) if s.tile_v else ys
        window = np.ix_(yi, xi)
        target[window] = np.maximum(target[window], mark)
    return light, dark


# ----------------------------------------------------------------- materials

def pink_limewash():
    """The Nice Things shopfront: brushed limewash over boarded panels.

    Read from both photographs: a salmon ground, clouded paler where the wash
    is thin, and swept by short diagonal-to-curving strokes of darker rose
    and lighter blush roughly a hand-span long.  The boarding shows only as
    faint vertical butt joints; the finish itself is matte and chalky.
    """
    s = Surface("pink-limewash",
                "Shopfront limewash: salmon ground, rose and blush brush strokes, board joints",
                2.40, 2.40, 2048, 2048, normal_strength=0.8)
    ground, rose, blush = lin("#E9AD98"), lin("#CC7F6B"), lin("#F3C8B6")
    grime = lin("#8C6F66")

    s.fill(ground, 0.88)

    # Clouding: the wash dries unevenly over the board.
    cloud = s.noise(0.9, 1101, 4)
    s.tint(smoothstep(0.50, 0.85, cloud), blush, 0.40)
    s.tint(smoothstep(0.45, 0.15, cloud), rose, 0.25)

    # Broad smudges first, then swipes on top.  Directions are free: the
    # photographs show swirls, not a hatched grain.  Darker passes outnumber
    # lighter ones, which is what reads as rose marks on a salmon ground.
    for count, seed, length, width, opacity, curl, dark_bias in (
        (70, 1103, (0.30, 0.75), (0.12, 0.30), 0.55, 0.9, 0.55),
        (110, 1105, (0.14, 0.42), (0.035, 0.10), 0.62, 0.45, 0.65),
    ):
        light, dark = brush_strokes(s, count, seed, length, width,
                                    angles=(0.0, np.pi), curl=curl, dark_bias=dark_bias)
        s.tint(light, blush, opacity)
        s.tint(dark, rose, opacity)
        # Burnished where the brush dragged; bristle ridges at the edges.
        s.roughen(np.maximum(light, dark), 0.76, 0.35)
        s.relief += (light - dark) * 0.00012

    # Chalky limewash grain, and the board's slight undulation.
    s.base *= (0.975 + 0.05 * s.noise(0.006, 1107, 2))[..., None]
    s.relief += (s.noise(0.003, 1109) - 0.5) * 0.00012
    s.relief += (s.noise(0.35, 1111, 2) - 0.5) * 0.00045

    # Butt joints at 1.2 m board centres: filled and painted over, so they
    # read as the faintest shadow line, not a panel seam.
    joint = smoothstep(0.0022, 0.0006, s.repeat(s.x, 1.20))
    s.shade(joint, 0.86)
    s.relief -= joint * 0.0006
    s.occlude(joint, 0.8)

    # Street film: a little dust settles in the brush texture, never a stain.
    film = smoothstep(0.55, 0.95, s.noise((0.08, 0.40), 1113, 3))
    s.tint(film, grime, 0.06)
    return s


def pink_satin_joinery():
    """Door and window frames: the same pink in a harder satin paint."""
    s = Surface("pink-satin-joinery",
                "Shopfront joinery: satin pink paint on timber, brush marks, knocks at hand height",
                0.60, 0.60, 1024, 1024)
    pink, deep, primer = lin("#D08B7A"), lin("#B06E5F"), lin("#E8DCCB")

    s.fill(pink, 0.46)
    # Vertical brush-out and the timber grain telegraphing through the paint.
    s.base *= (0.965 + 0.07 * s.noise((0.003, 0.12), 1201, 2))[..., None]
    s.relief += (s.noise((0.0025, 0.16), 1203, 2) - 0.5) * 0.00016
    s.tint(smoothstep(0.55, 0.9, s.noise(0.18, 1205, 3)), deep, 0.25)

    knocks = np.zeros(s.shape, F)
    rng = np.random.default_rng(1207)
    for _ in range(18):
        s.stamp(knocks, rng.uniform(0, s.width), rng.uniform(0, s.height),
                rng.uniform(0.0012, 0.004), value=rng.uniform(0.5, 1.0), core=0.7,
                elongate=rng.uniform(0.7, 2.2))
    s.tint(knocks, primer, 0.7)
    s.roughen(knocks, 0.8)
    s.relief -= knocks * 0.00018
    return s


def sandstone(slug, description, soot_amount, seed):
    """Coursed buff sandstone ashlar, with soot washing down the faces.

    Courses of 0.38 m and 0.76 m stones, matching the upper facade's block
    size against its 1.7 m windows.  The stone is a medium-grained
    Millstone-Grit type: fine speckle, faint bedding lines, iron-rich bands,
    and blocks cut from different beds sitting a shade apart.
    """
    s = Surface(slug, description, 2.28, 2.28, 2048 if soot_amount < 0.5 else 1024,
                2048 if soot_amount < 0.5 else 1024)
    course, perpend = 0.38, 0.76
    buff, iron, soot, wash = lin("#C9AD86"), lin("#A9855E"), lin("#4A4037"), lin("#D3C3AA")

    s.fill(buff, 0.86)
    # Projecting and low stone is darker all over, not only in its streaks.
    s.base *= 1.0 - 0.32 * soot_amount

    # Per-course random offset for the perpends.  The pitch divides the tile,
    # so every course still wraps.
    rng = np.random.default_rng(seed)
    offsets = rng.uniform(0, perpend, int(round(s.height / course)))
    row = np.clip(np.floor(s.y / course).astype(int), 0, len(offsets) - 1)
    shift = offsets[row].astype(F)
    block_cx = (np.floor((s.x + shift) / perpend) + 0.5) * perpend - shift
    block_cy = (np.floor(s.y / course) + 0.5) * course
    block = s.noise((perpend, course), seed + 1, warp=(block_cx - s.x, block_cy - s.y))
    s.base *= (0.93 + 0.13 * block)[..., None]

    # Bedding: faint horizontal laminations, broken by the block joints.
    bedding = s.noise((0.9, 0.012), seed + 3, 2)
    s.tint(smoothstep(0.66, 0.92, bedding), iron, 0.16)
    s.base *= (0.97 + 0.06 * s.noise(0.0035, seed + 5))[..., None]

    # Soot: streak-led, heavier towards the top of each block where water
    # tracks off the joint above, and overall by `soot_amount`.
    columns = s.noise((0.14, 1.6), seed + 7, 3)
    patchy = smoothstep(0.2, 0.8, s.noise((0.6, 0.9), seed + 9, 2))
    below = smoothstep(0.26, 0.02, course - np.mod(s.y, course))
    dirt = np.clip(columns ** 1.6 * (0.35 + 0.9 * patchy) * (0.6 + 0.6 * below), 0, 1)
    s.tint(dirt, soot, 0.28 + 0.55 * soot_amount)
    s.roughen(dirt, 0.92, 0.5)
    if soot_amount > 0:
        # A general crust, deepest in the runs rather than in patches.
        crust = smoothstep(0.2, 0.9, s.noise((0.35, 0.9), seed + 11, 3))
        s.tint(crust, soot, 0.32 * soot_amount)
        s.relief += crust * 0.0004 * soot_amount

    # Rain-washed pale faces where soot has been cleaned off by run-off.
    pale = smoothstep(0.72, 0.94, s.noise((0.05, 2.0), seed + 13, 2))
    s.tint(pale, wash, 0.25 * (1.0 - soot_amount))

    # Pitting and erosion of the softer beds.
    pits = smoothstep(0.80, 0.97, s.noise(0.004, seed + 15, 2))
    s.shade(pits, 0.8, 0.7)
    s.relief -= pits * 0.00045
    s.relief += (s.noise(0.02, seed + 17, 3) - 0.5) * 0.0006

    # Joints: 6 mm lime mortar, slightly recessed and dirt-filled.
    joint = np.maximum(smoothstep(0.004, 0.0015, s.repeat(s.y, course)),
                       smoothstep(0.004, 0.0015, s.repeat(s.x + shift, perpend)))
    s.tint(joint, soot, 0.45)
    s.roughen(joint, 0.95, 0.8)
    s.relief -= joint * 0.0025
    s.occlude(joint, 0.5)
    # A blunt arris either side of every joint.
    arris = smoothstep(0.018, 0.004, np.minimum(s.repeat(s.y, course),
                                                  s.repeat(s.x + shift, perpend)))
    s.relief -= arris * 0.0008
    return s


def sandstone_ashlar():
    return sandstone("sandstone-ashlar",
                     "Buff sandstone ashlar: bedding, iron bands, soot run-down, pitting",
                     0.15, 1301)


def sandstone_sooted():
    return sandstone("sandstone-sooted",
                     "Projecting and low sandstone: the same stone under a black soot crust",
                     0.75, 1351)


def white_painted_frame():
    """Upper sashes: white paint under the city's grey film."""
    s = Surface("white-painted-frame",
                "Upper window frames and fanlight bars: white gloss gone to satin, dirt film",
                0.40, 0.40, 512, 512)
    white, film, flake = lin("#E6E4DE"), lin("#9A9890"), lin("#8C8175")

    s.fill(white, 0.38)
    s.base *= (0.97 + 0.06 * s.noise((0.003, 0.10), 1401, 2))[..., None]
    s.relief += (s.noise((0.003, 0.10), 1403, 2) - 0.5) * 0.00010
    dirt = smoothstep(0.4, 0.9, s.noise(0.10, 1405, 3))
    s.tint(dirt, film, 0.28)
    s.roughen(dirt, 0.6, 0.8)
    chips = np.zeros(s.shape, F)
    rng = np.random.default_rng(1407)
    for _ in range(10):
        s.stamp(chips, rng.uniform(0, s.width), rng.uniform(0, s.height),
                rng.uniform(0.001, 0.003), core=0.7, elongate=rng.uniform(0.6, 1.8))
    s.tint(chips, flake, 0.8)
    s.relief -= chips * 0.00015
    return s


def interior_plaster_warm():
    """Shop interior walls and ceiling: warm peach emulsion on plaster."""
    s = Surface("interior-plaster-warm",
                "Interior walls and ceiling: warm peach matt emulsion, roller texture",
                2.00, 2.00, 1024, 1024, normal_strength=0.6)
    peach, shade = lin("#E9C3A6"), lin("#D7A98A")
    s.fill(peach, 0.9)
    # Roller stipple and the laps between roller passes.
    s.relief += (s.noise(0.004, 1501, 2) - 0.5) * 0.00012
    laps = s.noise((0.5, 2.0), 1503, 2)
    s.tint(smoothstep(0.55, 0.85, laps), shade, 0.18)
    return s


def floor_sealed_concrete():
    """Shop floor: sealed concrete, worn along the walking line."""
    s = Surface("floor-sealed-concrete",
                "Interior floor: sealed warm-grey concrete, trowel marks, scuffs",
                2.00, 2.00, 1024, 1024, normal_strength=0.6)
    grey, dark, dust = lin("#A89684"), lin("#7E6F61"), lin("#C2B3A2")
    s.fill(grey, 0.42)
    s.tint(smoothstep(0.45, 0.85, s.noise(0.45, 1601, 4)), dark, 0.35)
    # Power-float swirls.
    swirl = s.ridges(0.3, 1603, width=0.06,
                     warp=(0.1 * (s.noise(0.5, 1605) - 0.5), 0.1 * (s.noise(0.5, 1607) - 0.5)))
    s.tint(swirl, dust, 0.18)
    s.roughen(swirl, 0.3, 0.4)
    scuffs = smoothstep(0.85, 0.98, s.noise((0.12, 0.012), 1609, 2))
    s.tint(scuffs, dark, 0.45)
    s.relief += (s.noise(0.003, 1611) - 0.5) * 0.00008
    return s


def birch_ply():
    """Counter and display furniture: clear-lacquered birch plywood."""
    s = Surface("birch-ply",
                "Counter and shelving: lacquered birch ply, soft grain, warm yellowed lacquer",
                1.20, 1.20, 1024, 1024, normal_strength=0.5)
    birch, grain, amber = lin("#D9B48A"), lin("#B98D62"), lin("#C79A63")
    s.fill(birch, 0.5)
    # Rotary-cut birch: long, low-contrast figure along X.
    figure = s.noise((0.30, 0.012), 1701, 3,
                     warp=(0.0, 0.02 * (s.noise(0.2, 1703) - 0.5)))
    s.tint(smoothstep(0.5, 0.9, figure), grain, 0.45)
    s.tint(smoothstep(0.3, 0.8, s.noise(0.5, 1705, 2)), amber, 0.2)
    s.relief += (figure - 0.5) * 0.00006
    return s


def dark_painted_steel():
    """Roller-shutter box, door furniture: dark grey powder coat."""
    s = Surface("dark-painted-steel",
                "Shutter box and door furniture: dark grey powder coat, dust and knocks",
                0.40, 0.40, 512, 512)
    coat, dust = lin("#34322F"), lin("#6E6860")
    s.fill(coat, 0.5, metal=0.0)
    s.relief += (s.noise(0.006, 1801, 2) - 0.5) * 0.00008
    s.tint(smoothstep(0.5, 0.95, s.noise(0.08, 1803, 3)), dust, 0.25)
    return s


MATERIALS = (
    pink_limewash,
    pink_satin_joinery,
    sandstone_ashlar,
    sandstone_sooted,
    white_painted_frame,
    interior_plaster_warm,
    floor_sealed_concrete,
    birch_ply,
    dark_painted_steel,
)


# ---------------------------------------------------------------------- main

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    render = "--no-render" not in argv
    only = {arg for arg in argv if not arg.startswith("--")}

    records, frames = [], []
    for build in MATERIALS:
        if only and build.__name__ not in only:
            continue
        surface = build()
        record = write_surface(surface, TEXTURE_DIR)
        print(f"  {surface.slug:26s} {surface.w_px}x{surface.h_px}  "
              f"{record['mm_per_texel'][0]:.3f} mm/texel", flush=True)
        for axis, step in record["seam_levels"].items():
            if step["wrap"] > max(3.0, step["typical"] * 3.0):
                print(f"      seam check {axis}: wrap {step['wrap']} levels "
                      f"vs typical {step['typical']}")
        if render:
            frames.append(review_render(surface, texture_dir=TEXTURE_DIR, render_dir=RENDER_DIR))
        records.append(record)

    if render and frames and not only:
        contact_sheet(frames, render_dir=RENDER_DIR)
    if only:
        return

    validation = {
        "asset": "nice-things",
        "pass": "surface materials, first batch",
        "convention": {
            "maps": "<slug>-{basecolor,orm,normal}.png",
            "orm": "R occlusion, G roughness, B metallic (glTF)",
            "normal": "OpenGL tangent space (+Y up)",
            "unit": "1 Blender unit = 1 m; coverage_m is what one tile spans",
        },
        "measured_reference_patches": {k: {"photo": v[0], "srgb": v[1]} for k, v in MEASURED.items()},
        "materials": records,
    }
    path = TEXTURE_DIR / "validation.json"
    path.write_text(json.dumps(validation, indent=2) + "\n")
    print(f"wrote {len(records)} materials to {TEXTURE_DIR.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
