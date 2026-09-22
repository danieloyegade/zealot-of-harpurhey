"""Parameterised tiling surfaces shared by the building texture passes.

Vinyl Exchange and Nice Things each wrote their surfaces by hand.  The
buildings that follow share most of their materials -- clay brick, sandstone
ashlar, painted steel, painted joinery, concrete -- and differ mainly in
palette.  Each builder here takes the measured palette and returns a
`vinylExchangeTextures.Surface` in the same glTF convention (sRGB base colour,
ORM, OpenGL normal) at metric scale, so a building's texture script is a
palette plus a list of calls.

Every repeating feature (brick pitch, course height, tile module) must divide
the tile exactly, or the maps would not wrap; `_check_tiles` enforces that.
Weathering that depends on where a texel sits on the building belongs to a
later `surfaceWeathering` atlas bake, not here.
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.append(str(Path(__file__).resolve().parent))

from surfaceWeathering import F, smoothstep  # noqa: E402
from vinylExchangeTextures import Surface, lin  # noqa: E402


# ------------------------------------------------------------------ helpers

def _check_tiles(tile, *pitches):
    for pitch in pitches:
        count = tile / pitch
        if abs(count - round(count)) > 1e-6:
            raise ValueError(f"tile {tile} m is not a whole number of {pitch} m pitches")


def _check_even_courses(tile, course):
    if round(tile / course) % 2:
        raise ValueError(f"a {tile} m tile holds an odd number of {course} m courses; "
                         "a half-bond stagger would not wrap")


def _chips(s, count, seed, size=(0.0010, 0.0038)):
    field = np.zeros(s.shape, F)
    rng = np.random.default_rng(seed)
    for _ in range(count):
        s.stamp(field, rng.uniform(0, s.width), rng.uniform(0, s.height),
                rng.uniform(*size), value=rng.uniform(0.5, 1.0), core=0.7,
                elongate=rng.uniform(0.6, 1.8))
    return field


def _bond(s, pitch, course):
    """Stretcher-bond layout: bond coordinates and the per-row stagger.

    The bond is shifted a quarter unit across and half a course up, so no joint
    lies on a tile edge.  A groove centred on the wrap is seamless but mirrors
    its slope, which reads as a seam to `seam_report`'s edge comparison.
    """
    gx, gy = s.x + pitch * 0.25, s.y + course * 0.5
    row = np.floor(gy / course)
    stagger = np.where(np.mod(row, 2) > 0.5, pitch * 0.5, 0.0).astype(F)
    return gx, gy, stagger


def _unit_random(s, gx, gy, pitch, course, stagger, seed):
    """One independent value in [0, 1) per brick or block, wrapped to the tile.

    Lattice noise sampled at unit centres correlates neighbours (they share
    lattice corners), which strings accent bricks into diagonal chains.  A
    hash of the unit's integer index does not.
    """
    columns = int(round(s.width / pitch))
    rows = int(round(s.height / course))
    ix = np.mod(np.floor((gx + stagger) / pitch), columns)
    iy = np.mod(np.floor(gy / course), rows)
    h = np.sin(ix * 12.9898 + iy * 78.233 + seed * 37.719) * 43758.5453
    return (h - np.floor(h)).astype(F)


def _joints(s, gx, gy, pitch, course, stagger, joint):
    half = joint * 0.5
    soft = min(0.0015, half * 0.5)
    return np.maximum(smoothstep(half, half - soft, s.repeat(gy, course)),
                      smoothstep(half, half - soft, s.repeat(gx + stagger, pitch)))


def _soot(s, seed, colour, amount):
    """Run-down soot: streak-led, concentrated in patches, never a ruled band."""
    streaks = s.noise((0.12, 1.2), seed, 3) ** 2
    patchy = smoothstep(0.3, 0.8, s.noise((0.6, 0.9), seed + 1, 2))
    dirt = np.clip(streaks * (0.4 + 0.9 * patchy), 0.0, 1.0)
    s.tint(dirt, colour, amount)
    s.roughen(dirt, 0.92, 0.4)


# ----------------------------------------------------------------- masonry

def brick(slug, description, face, mortar, soot, *, seed, soot_amount=0.30,
          tile=1.80, px=1024, pitch=0.225, course=0.075, joint=0.010, face_spread=0.14,
          accent=None, accent_share=0.5, overburnt=0.08):
    """Stretcher-bond clay brick.  Pitches include the joint: 1.80 m = 8 x 24.

    `accent` is an optional second brick colour given to about `accent_share`
    of the bricks, chosen per brick: polychrome work such as the alternating
    red and blue-grey arches of the Victorian Northern Quarter.  `overburnt`
    is the share of clamp-fired bricks darkened by the kiln; modern
    machine-made brick is even, so pass 0.
    """
    _check_tiles(tile, pitch, course)
    _check_even_courses(tile, course)
    s = Surface(slug, description, tile, tile, px, px)
    s.fill(lin(face), 0.84)

    gx, gy, stagger = _bond(s, pitch, course)
    if accent is not None:
        pick = _unit_random(s, gx, gy, pitch, course, stagger, seed + 6)
        s.tint((pick < accent_share).astype(F), lin(accent))
    tone = _unit_random(s, gx, gy, pitch, course, stagger, seed)
    s.base *= (1.0 - face_spread * 0.5 + face_spread * tone)[..., None]
    # Firing varies across one brick too: a soft cloud, not a flat fill.
    s.base *= (0.95 + 0.10 * s.noise(0.08, seed + 7, 2))[..., None]
    burnt = (_unit_random(s, gx, gy, pitch, course, stagger, seed + 1) > 1.0 - overburnt).astype(F)
    s.shade(burnt, 0.72)

    pits = smoothstep(0.78, 0.95, s.noise(0.006, seed + 2, 2))
    s.shade(pits, 0.80, 0.7)
    s.relief -= pits * 0.0006
    s.relief += (s.noise(0.03, seed + 3, 2) - 0.5) * 0.0005

    mask = _joints(s, gx, gy, pitch, course, stagger, joint)
    s.tint(mask, lin(mortar))
    s.roughen(mask, 0.95)
    s.relief -= mask * 0.004
    s.occlude(mask, 0.55)

    _soot(s, seed + 4, lin(soot), soot_amount)
    return s


def ashlar(slug, description, stone, joint_colour, soot, *, seed, soot_amount=0.25,
           tile=2.40, px=1024, course=0.30, block=0.60, joint=0.008):
    """Coursed sandstone ashlar: per-block tone, bedding planes, pores, fine joints."""
    _check_tiles(tile, course, block)
    _check_even_courses(tile, course)
    s = Surface(slug, description, tile, tile, px, px)
    s.fill(lin(stone), 0.86)

    gx, gy, stagger = _bond(s, block, course)
    tone = _unit_random(s, gx, gy, block, course, stagger, seed)
    s.base *= (0.93 + 0.14 * tone)[..., None]
    # Sedimentary bedding runs along each block.
    beds = s.noise((0.9, 0.012), seed + 1, 3)
    s.base *= (0.965 + 0.07 * beds)[..., None]
    s.relief += (beds - 0.5) * 0.0002

    pores = smoothstep(0.80, 0.95, s.noise(0.004, seed + 2, 2))
    s.shade(pores, 0.85, 0.7)
    s.relief -= pores * 0.0003
    s.relief += (s.noise(0.05, seed + 3, 2) - 0.5) * 0.0004

    mask = _joints(s, gx, gy, block, course, stagger, joint)
    s.tint(mask, lin(joint_colour), 0.8)
    s.roughen(mask, 0.92, 0.8)
    s.relief -= mask * 0.002
    s.occlude(mask, 0.5)

    _soot(s, seed + 4, lin(soot), soot_amount)
    return s


# -------------------------------------------------------------- paint films

def painted_metal(slug, description, paint, *, seed, rust="#5E3620", bare="#6B6C6E",
                  rust_amount=0.55, chips=20, tile=0.50, px=1024, roughness=0.55, metallic=0.0):
    """Painted or coated steel: rust bloom with its bleed, chips to bare metal, dust."""
    s = Surface(slug, description, tile, tile, px, px)
    s.fill(lin(paint), roughness, metallic)
    s.relief += (s.noise(0.010, seed, 2) - 0.5) * 0.00020
    s.base *= (0.94 + 0.12 * s.noise(0.16, seed + 1, 3))[..., None]

    bloom = smoothstep(0.66, 0.95, s.noise(0.055, seed + 2, 4))
    lifted = (np.zeros_like(s.x), np.full_like(s.y, 0.05))
    above = smoothstep(0.66, 0.95, s.noise(0.055, seed + 2, 4, warp=lifted))
    bleed = above * smoothstep(0.30, 0.80, s.noise((0.035, 0.30), seed + 3, 2))
    rusted = np.clip(bloom + 0.6 * bleed, 0, 1)
    s.tint(rusted, lin(rust), rust_amount)
    s.roughen(rusted, 0.92, 0.9 * min(1.0, rust_amount / 0.55))
    s.relief += bloom * 0.00022 * rust_amount

    chipped = _chips(s, chips, seed + 4) * (1.0 - bloom)
    s.tint(chipped, lin(bare), 0.7)
    s.metalise(chipped, 1.0, 0.6)
    s.roughen(chipped, 0.45, 0.8)
    s.relief -= chipped * 0.00018

    dust = smoothstep(0.5, 0.95, s.noise(0.05, seed + 5, 3))
    s.shade(dust, 1.06, 0.5)
    s.roughen(dust, 0.75, 0.5)
    return s


def painted_timber(slug, description, paint, *, seed, primer="#8A7A62", tile=0.60,
                   px=1024, gloss=0.42, chips=14):
    """Painted joinery: grain telegraphing through the film, brush marks, chipped arrises."""
    s = Surface(slug, description, tile, tile, px, px)
    s.fill(lin(paint), gloss)
    grain = s.noise((0.004, 0.30), seed, 3)
    s.relief += (grain - 0.5) * 0.00025
    s.base *= (0.97 + 0.06 * grain)[..., None]

    brush = s.noise((0.002, 0.08), seed + 1, 2)
    s.roughen(smoothstep(0.4, 0.9, brush), gloss + 0.12, 0.6)
    s.relief += (brush - 0.5) * 0.00008

    dull = smoothstep(0.45, 0.85, s.noise(0.25, seed + 2, 3))
    s.roughen(dull, min(gloss + 0.25, 0.95), 0.7)
    s.shade(dull, 0.94, 0.6)

    chipped = _chips(s, chips, seed + 3)
    s.tint(chipped, lin(primer), 0.8)
    s.roughen(chipped, 0.85, 0.8)
    s.relief -= chipped * 0.00015
    return s


def painted_render(slug, description, colour, dirt, *, seed, dirt_amount=0.30,
                   tile=2.40, px=512, roughness=0.80):
    """Painted smooth render: float marks, fresher repair patches, run-down dirt.

    512 px by default for the same reason as `concrete`: float grain is
    incompressible and reads only as smoothness at street distance.
    """
    s = Surface(slug, description, tile, tile, px, px)
    s.fill(lin(colour), roughness)
    s.base *= (0.95 + 0.10 * s.noise(0.8, seed, 3))[..., None]
    s.relief += (s.noise(0.003, seed + 1, 2) - 0.5) * 0.0003
    s.relief += (s.noise(0.12, seed + 2, 2) - 0.5) * 0.0006

    patches = smoothstep(0.72, 0.90, s.noise(0.5, seed + 3, 2))
    s.shade(patches, 1.05, 0.8)
    s.roughen(patches, max(roughness - 0.10, 0.3), 0.8)

    _soot(s, seed + 4, lin(dirt), dirt_amount)
    return s


# ------------------------------------------------------------------ others

def timber(slug, description, light, dark, *, seed, tile=(0.60, 1.20), px=(512, 1024),
           finish=0.55):
    """Sealed or oiled timber, grain running up the tile."""
    s = Surface(slug, description, tile[0], tile[1], px[0], px[1])
    s.fill(lin(light), finish)
    wobble = (0.02 * (s.noise(0.3, seed) - 0.5), np.zeros_like(s.y))
    figure = s.noise((0.012, 0.9), seed + 1, 3, warp=wobble)
    rings = (0.5 + 0.5 * np.sin(figure * 40.0)).astype(F)
    s.tint(rings, lin(dark), 0.55)
    s.relief += (rings - 0.5) * 0.00012

    pores = smoothstep(0.75, 0.95, s.noise((0.0015, 0.02), seed + 2, 2))
    s.shade(pores, 0.85, 0.6)
    s.relief -= pores * 0.0001
    return s


def concrete(slug, description, colour, *, seed, stain="#4A4A46", stain_amount=0.25,
             tile=2.00, px=512, roughness=0.88):
    """Cast concrete: aggregate mottle, blowholes, water staining.

    512 px (3.9 mm/texel on the 2 m tile) by default: the fine aggregate grain
    is noise PNG cannot compress, and at 1024 the normal map alone runs to
    1.5 MB for detail that is invisible from the street.
    """
    s = Surface(slug, description, tile, tile, px, px)
    s.fill(lin(colour), roughness)
    s.base *= (0.90 + 0.20 * s.noise(0.35, seed, 4))[..., None]
    fine = s.noise(0.01, seed + 1, 2)
    s.base *= (0.96 + 0.08 * fine)[..., None]
    s.relief += (fine - 0.5) * 0.0004

    blowholes = smoothstep(0.82, 0.96, s.noise(0.005, seed + 2))
    s.shade(blowholes, 0.6, 0.8)
    s.relief -= blowholes * 0.0008
    s.occlude(blowholes, 0.7)

    stains = smoothstep(0.55, 0.90, s.noise((0.2, 0.8), seed + 3, 3))
    s.tint(stains, lin(stain), stain_amount)
    s.roughen(stains, 0.95, 0.4)
    return s


def plaster(slug, description, colour, *, seed, tile=2.00, px=512, roughness=0.90):
    """Interior plaster/emulsion: soft trowel variation only."""
    s = Surface(slug, description, tile, tile, px, px)
    s.fill(lin(colour), roughness)
    s.base *= (0.96 + 0.08 * s.noise(0.4, seed, 3))[..., None]
    s.relief += (s.noise(0.02, seed + 1, 2) - 0.5) * 0.0002
    return s


def glazed_tile(slug, description, glaze, grout, *, seed, tile_size=(0.152, 0.076),
                tile=0.912, px=1024, spread=0.10, craze=True):
    """Glazed ceramic tile: per-tile tone, pillowed faces, recessed grout, crazing."""
    tile_w, tile_h = tile_size
    _check_tiles(tile, tile_w, tile_h)
    s = Surface(slug, description, tile, tile, px, px)
    s.fill(lin(glaze), 0.12)

    # Grout lines are offset half a module from the tile edges: the normal is a
    # gradient of relief, and a grout groove straddling the wrap reads as a seam.
    gx, gy = s.x + tile_w * 0.5, s.y + tile_h * 0.5
    centre_x = (np.floor(gx / tile_w) + 0.5) * tile_w - tile_w * 0.5
    centre_y = (np.floor(gy / tile_h) + 0.5) * tile_h - tile_h * 0.5
    tone = s.noise(tile_size, seed, warp=(centre_x - s.x, centre_y - s.y))
    s.base *= (1.0 - spread * 0.5 + spread * tone)[..., None]

    # 0 at the grout line, 1 at the tile centre.
    inset = np.minimum(s.repeat(gx, tile_w) / (tile_w * 0.5),
                       s.repeat(gy, tile_h) / (tile_h * 0.5))
    s.relief += smoothstep(0.0, 0.25, inset) * 0.0015
    s.shade(1.0 - smoothstep(0.0, 0.2, inset), 1.10, 0.5)  # thin glaze on the roll
    s.roughen(smoothstep(0.5, 0.9, s.noise(0.02, seed + 1, 2)), 0.20, 0.5)

    lines = smoothstep(0.004, 0.002, np.minimum(s.repeat(gx, tile_w), s.repeat(gy, tile_h)))
    s.tint(lines, lin(grout))
    s.roughen(lines, 0.95)
    s.relief -= lines * 0.002
    s.occlude(lines, 0.6)

    if craze:
        cracks = s.ridges(0.03, seed + 2, width=0.03)
        s.shade(cracks, 0.85, 0.5)
    return s


# ------------------------------------------------------------ palette + run

def load_palette(path, required):
    """Albedo hex per key from a building's palette.json (see measurePatch.py)."""
    path = Path(path)
    data = json.loads(path.read_text()) if path.exists() else {}
    missing = [key for key in required if key not in data]
    if missing:
        raise SystemExit(f"{path} is missing measured keys: {', '.join(missing)}")
    return {key: entry["albedo"] for key, entry in data.items()}


def run_texture_pass(asset, texture_dir, render_dir, palette_path, builders, argv):
    """Write every surface, refuse any that does not tile, and record validation.json.

    `builders` is a sequence of no-argument callables returning a Surface.
    Pass `--no-render` in argv to skip the review renders.
    """
    from vinylExchangeTextures import contact_sheet, review_render, write_surface

    render = "--no-render" not in argv
    records, frames = [], []
    for build in builders:
        surface = build()
        record = write_surface(surface, texture_dir=texture_dir)
        seams = [f"{axis}: wrap {step['wrap']} vs typical {step['typical']}"
                 for axis, step in record["seam_levels"].items()
                 if step["wrap"] > max(3.0, step["typical"] * 3.0)]
        if seams:
            raise RuntimeError(f"{surface.slug} does not tile: " + "; ".join(seams))
        print(f"  {surface.slug:28s} {surface.w_px}x{surface.h_px}  "
              f"{record['mm_per_texel'][0]:.3f} mm/texel", flush=True)
        if render:
            frames.append(review_render(surface, texture_dir=texture_dir, render_dir=render_dir))
        records.append(record)
    if render:
        contact_sheet(frames, render_dir=render_dir)

    validation = {
        "asset": asset,
        "pass": "surface materials (commonSurfaces)",
        "convention": {
            "maps": "<slug>-{basecolor,orm,normal}.png",
            "orm": "R occlusion, G roughness, B metallic (glTF)",
            "normal": "OpenGL tangent space (+Y up)",
            "unit": "1 Blender unit = 1 m; coverage_m is what one tile spans",
        },
        "measured_reference_patches": json.loads(Path(palette_path).read_text()),
        "materials": records,
    }
    (Path(texture_dir) / "validation.json").write_text(json.dumps(validation, indent=2) + "\n")
    print(f"wrote {len(records)} materials to {texture_dir}", flush=True)
    return records
