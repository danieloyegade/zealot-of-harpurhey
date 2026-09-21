"""Surface and signage textures for MCR1.

MCR1 is shown in its *illuminated* state: the wrapped yellow honeycomb fascia,
the two MCR_1 wordmarks, the white roundel and the neon blade sign from
`references/architecture/buildings/mcr1/new-stevenson-square-addition-...webp`.
In the city the owner was asked to take those lights down as tacky; in the game
they stay up, and the shopkeeper talks about the people who keep asking him to
remove them.  The daylight photographs (DSC06325-7) remain the source for the
building fabric: pressed salmon-red brick in stretcher bond with fine pale
joints, buff sandstone dressings, dark grey-green sash frames with net
curtains, and the honeycomb LED ceiling inside the shop.

Two kinds of map are written to `blender/source/textures/mcr1/`:

* Tiling metric PBR sets (glTF convention: sRGB base colour, ORM, OpenGL
  normal) built with the Vinyl Exchange `Surface` class: brick, sandstone,
  the honeycomb pier wrap and the LED ceiling.
* Bounded artwork atlases laid out in metres against the geometry in
  `createMCR1.py` (ATLAS constants below are shared with it): the fascia
  signage, the window vinyls, the upper-floor glazing and the shop shelving.
  Lettering is set as vector type through the bus-shelter `PrintCanvas`, so it
  stays crisp; everything else is numpy.

No pixels from the reference photographs reach the output.  Colours are
authored by eye against the photographs: the Sony originals carry a wide-gamut
profile, so raw patch medians read far too grey to be used as numbers.

Run on its own to write the maps (createMCR1.py also calls `build_all`):

    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --factory-startup --python blender/scripts/mcr1Textures.py
"""

import json
import sys
from math import cos, pi, radians, sin, sqrt
from pathlib import Path

import bpy
import numpy as np

sys.path.append(str(Path(__file__).resolve().parent))

import busShelterArtwork  # noqa: E402
from busShelterArtwork import PrintCanvas  # noqa: E402
from surfaceWeathering import F, save_rgba, smoothstep, srgb_decode, srgb_encode  # noqa: E402
from vinylExchangeTextures import Surface, lin  # noqa: E402

busShelterArtwork.FONT_FILES.setdefault("din_bold", "DIN Alternate Bold.ttf")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "mcr1"
WORK_DIR = TEXTURE_DIR / "_work"

# ------------------------------------------------------------ shared layouts
# Every atlas is described in metres so createMCR1.py can project UVs straight
# from the geometry.  Regions are (x_px, y_px_from_top, width_m, height_m).

SIGN_PPM = 476.0                       # px per metre on the fascia faces
SIGN_SIZE = (4096, 768)
SIGN_REGIONS = {
    "Front": (0, 0, 8.60, 0.62),
    "Side": (0, 300, 2.85, 0.62),
    "Corner": (1400, 300, 1.27, 0.62),
    "Blade": (2060, 300, 0.58, 0.92),
}
SIGN_BLACK_UV = ((4000 + 40) / 4096, 1.0 - (700 + 30) / 768)   # plain housing black

# Window vinyl strip: every shopfront pane in one row.  v runs from the pane
# bottom (z 0.12) over VINYL_SPAN_M; the top rows are clear glass, and the
# sampler clamps so the rest of each pane stays clear.
VINYL_SIZE = (4096, 640)
VINYL_Z0 = 0.12
VINYL_SPAN_M = 1.25
VINYL_PRINT_M = 1.00
VINYL_PPM_X = 350.0
VINYL_GAP_PX = 16
VINYL_PANES = (                         # (glass object prefix, width m, style)
    ("MCR1_Front_Display", 5.88, "front"),
    ("MCR1_Front_EndPane", 0.64, "end"),
    ("MCR1_Side_Display", 2.45, "side"),
    ("MCR1_Corner_Display", 1.05, "corner"),
    ("MCR1_Door", 1.42, "door"),
)


def vinyl_pane_x():
    """Left pixel of each pane's column in the vinyl strip."""
    x, out = 0, {}
    for prefix, width, _ in VINYL_PANES:
        out[prefix] = x
        x += int(round(width * VINYL_PPM_X)) + VINYL_GAP_PX
    assert x <= VINYL_SIZE[0], "vinyl strip overflows its atlas"
    return out


VINYL_CLEAR_UV_V = 0.995                # a clear-glass texel for pane edges

UPPER_WINDOW_CELLS = 4                  # 1024 x 512, four 256 px variants
SHELF_CELLS = 2                         # 2048 x 1024, two 1024 px variants

# Honeycomb perforation: pointy-top hexagons, R = circumradius.
HEX_R = 0.036
HEX_WEB = 0.013


# ------------------------------------------------------------------- helpers

def hex_field(x, y, r=HEX_R):
    """(distance to hexagon centre in hex-norm units, cell id) for metric x, y.

    The hex norm is 1 on the flat sides; a hole of half-width a is `d < a`.
    """
    w = sqrt(3.0) * r
    h = 3.0 * r
    best_d = np.full(x.shape, 1e9, F)
    best_id = np.zeros(x.shape, np.int64)
    for ox, oy, parity in ((0.0, 0.0, 0), (w / 2, 1.5 * r, 1)):
        ci = np.round((x - ox) / w)
        cj = np.round((y - oy) / h)
        dx = np.abs(x - (ci * w + ox))
        dy = np.abs(y - (cj * h + oy))
        d = np.maximum(dx, dx * 0.5 + dy * (sqrt(3.0) / 2.0))
        better = d < best_d
        best_d = np.where(better, d, best_d)
        best_id = np.where(better, (ci.astype(np.int64) * 7919 + cj.astype(np.int64) * 104729) * 2 + parity,
                           best_id)
    return best_d.astype(F), best_id


def hash01(ids, seed):
    v = (ids * 2654435761 + seed * 97531) & 0xFFFFFFFF
    v = (v ^ (v >> 15)) * 2246822519 & 0xFFFFFFFF
    v = v ^ (v >> 13)
    return (v & 0xFFFF).astype(F) / 65535.0


def blur(img, radius, passes=3):
    """Separable box blur (≈ Gaussian after three passes) on an HxW(xC) array."""
    out = img.astype(F)
    r = max(1, int(radius))
    for _ in range(passes):
        for axis in (0, 1):
            c = np.cumsum(np.pad(out, [(r + 1, r) if a == axis else (0, 0) for a in range(out.ndim)],
                                 mode="edge"), axis=axis)
            hi = np.take(c, np.arange(2 * r + 1, c.shape[axis]), axis=axis)
            lo = np.take(c, np.arange(0, c.shape[axis] - 2 * r - 1), axis=axis)
            out = (hi - lo) / F(2 * r + 1)
    return out


def resize(img, h, w):
    """Bilinear resample of an HxW(xC) array."""
    H, W = img.shape[:2]
    ys = np.clip((np.arange(h) + 0.5) * H / h - 0.5, 0, H - 1)
    xs = np.clip((np.arange(w) + 0.5) * W / w - 0.5, 0, W - 1)
    y0, x0 = np.floor(ys).astype(int), np.floor(xs).astype(int)
    y1, x1 = np.minimum(y0 + 1, H - 1), np.minimum(x0 + 1, W - 1)
    fy, fx = (ys - y0)[:, None], (xs - x0)[None, :]
    if img.ndim == 3:
        fy, fx = fy[..., None], fx[..., None]
    a = img[y0][:, x0] * (1 - fx) + img[y0][:, x1] * fx
    b = img[y1][:, x0] * (1 - fx) + img[y1][:, x1] * fx
    return (a * (1 - fy) + b * fy).astype(F)


def type_mask(body, font, scale_x=1.0):
    """Tight alpha mask of a line of type, top-down, rendered at 400 px size."""
    c = PrintCanvas("type", 5200, 600)
    c.text(body, 60, 470, 400, (1, 1, 1), font, scale_x=scale_x)
    rgba = c.render(WORK_DIR / "type.png")[::-1]            # to top-down
    a = rgba[..., 3]
    ys, xs = np.nonzero(a > 0.02)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(F)


def paste(canvas_mask, mask, x, y, w, h):
    """Max-blend `mask` resized to w x h pixels at top-left (x, y)."""
    x, y, w, h = int(round(x)), int(round(y)), max(1, int(round(w))), max(1, int(round(h)))
    m = resize(mask, h, w)
    H, W = canvas_mask.shape
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    region = canvas_mask[y0:y1, x0:x1]
    np.maximum(region, m[y0 - y:y1 - y, x0 - x:x1 - x], out=region)


def to_linear(hex_or_rgb):
    if isinstance(hex_or_rgb, str):
        return lin(hex_or_rgb)
    return srgb_decode(np.asarray(hex_or_rgb, F))


def write_rgba(name, top_down_srgb_rgba):
    """Write a top-down sRGB RGBA float grid as PNG."""
    path = TEXTURE_DIR / name
    save_rgba(path, np.ascontiguousarray(top_down_srgb_rgba[::-1]), path.stem)
    return path


def write_surface(surface, slug=None):
    base, orm, normal = surface.maps()
    slug = slug or surface.slug
    files = {}
    for kind, grid in (("basecolor", base), ("orm", orm), ("normal", normal)):
        path = TEXTURE_DIR / f"{slug}-{kind}.png"
        save_rgba(path, grid, path.stem)
        files[kind] = path.name
    record = surface.record()
    record["files"] = files
    return record


# ------------------------------------------------------------- PBR surfaces

def brick_pressed_red():
    """Pressed salmon-red brick, stretcher bond, fine flush pale joints.

    Victorian machine-pressed brick: crisp arrises, very even size, the colour
    varying brick to brick between salmon, rose and a few darker flashed
    headers.  Joints are thin (8 mm) and weathered buff-grey, almost flush.
    """
    course, stretcher = 0.075, 0.225
    s = Surface("brick-pressed-red", "Pressed salmon-red brick, stretcher bond, 8 mm pale joints",
                1.35, 1.35, 1024, 1024, normal_strength=1.0)
    brick_a, brick_b, flashed = lin("#B8604F"), lin("#C27564"), lin("#8C4439")
    mortar = lin("#B9AA9C")

    row = np.floor(s.y / course)
    stagger = np.where(np.mod(row, 2) > 0.5, stretcher * 0.5, 0.0).astype(F)
    col = np.floor((s.x + stagger) / stretcher)
    # Per-brick identity that wraps with the tile (6 bricks x 18 courses).
    ids = (np.mod(col, 6).astype(np.int64) * 131 + np.mod(row, 18).astype(np.int64) * 977)
    tone = hash01(ids, 11)
    hue = hash01(ids, 23)
    flash = (hash01(ids, 37) > 0.9).astype(F)

    s.base = (brick_a * (1 - hue[..., None]) + brick_b * hue[..., None]).astype(F)
    s.base *= (0.84 + 0.30 * tone)[..., None]
    s.tint(flash, flashed, 0.75)
    s.rough[:] = 0.84

    # Face: fine sand grain, firing clouds, a slightly lighter weathered crust.
    grain = s.noise(0.003, 51)
    cloud = s.noise(0.06, 53, 3)
    s.base *= (0.93 + 0.10 * cloud + 0.05 * (grain - 0.5))[..., None]
    crust = smoothstep(0.62, 0.9, s.noise((0.12, 0.05), 55, 3))
    s.tint(crust, lin("#C9A091"), 0.22)
    s.relief += (grain - 0.5) * 0.00025 + (cloud - 0.5) * 0.0004

    # Joints and arrises.  Distance inside the brick, in metres.
    ex = s.repeat(s.x + stagger, stretcher)
    ey = s.repeat(s.y, course)
    edge = np.minimum(ex, ey)
    jitter = (s.noise(0.01, 57) - 0.5) * 0.0015
    joint = smoothstep(0.0048, 0.0032, edge + jitter)
    s.tint(joint, mortar, 1.0)
    s.base *= (1.0 - 0.10 * joint * s.noise(0.02, 59))[..., None]
    s.rough = s.rough * (1 - joint) + 0.93 * joint
    s.relief -= joint * 0.0022 + smoothstep(0.009, 0.004, edge) * 0.0006
    s.occlude(joint, 0.62)
    # Chipped arrises catch a lighter tone.
    chip = smoothstep(0.75, 0.95, s.noise(0.008, 61)) * smoothstep(0.01, 0.005, edge) * (1 - joint)
    s.tint(chip, lin("#D59A88"), 0.5)
    s.relief -= chip * 0.0015

    # City soot settles into the bed joints and the lower lip of each course.
    soot = s.noise((0.35, 0.8), 63, 3)
    s.shade(smoothstep(0.012, 0.0, np.mod(s.y, course)) * soot, 0.8, 0.5)
    return s


def sandstone_dressed():
    """Buff sandstone dressings: courses, sills, lintels, pilasters, cornice.

    Tooled face, soft bedding lines, rain-washed pale patches and grey soot in
    the lower half of each block.  Joints at 0.45 m courses and 0.9 m perpends.
    """
    course, perpend = 0.45, 0.90
    s = Surface("sandstone-dressed", "Buff sandstone ashlar dressings, sooted and washed",
                1.80, 1.80, 1024, 1024, normal_strength=1.0)
    buff, soot, wash = lin("#BDA58A"), lin("#6E665E"), lin("#D4C4AC")
    s.fill(buff, 0.86)
    stagger = np.where(np.mod(np.floor(s.y / course), 2) > 0.5, perpend * 0.5, 0.0).astype(F)
    bx = np.floor((s.x + stagger) / perpend)
    by = np.floor(s.y / course)
    ids = np.mod(bx, 2).astype(np.int64) * 31 + np.mod(by, 4).astype(np.int64) * 173
    s.base *= (0.9 + 0.16 * hash01(ids, 71))[..., None]

    bedding = s.noise((0.9, 0.012), 73, 2)
    s.base *= (0.95 + 0.08 * bedding)[..., None]
    tool = s.noise((0.004, 0.02), 75)
    s.relief += (tool - 0.5) * 0.0005 + (s.noise(0.08, 77, 3) - 0.5) * 0.0008

    lower = smoothstep(0.30, 0.0, np.mod(s.y, course)) * s.noise((0.2, 0.5), 79, 3)
    s.tint(lower, soot, 0.45)
    blotch = smoothstep(0.55, 0.85, s.noise(0.3, 81, 3))
    s.tint(blotch, soot, 0.25)
    pale = smoothstep(0.7, 0.92, s.noise((0.08, 0.9), 83, 2))
    s.tint(pale, wash, 0.35)

    joint = np.maximum(smoothstep(0.004, 0.002, s.repeat(s.y, course)),
                       smoothstep(0.004, 0.002, s.repeat(s.x + stagger, perpend)))
    s.tint(joint, lin("#857766"), 0.8)
    s.relief -= joint * 0.0025
    s.occlude(joint, 0.55)
    s.roughen(joint, 0.95)
    return s


def honeycomb_pier():
    """The yellow perforated lightbox skin wrapped round the corner piers."""
    r = HEX_R
    w, h = sqrt(3.0) * r, 3.0 * r
    s = Surface("honeycomb-lightbox", "Backlit yellow honeycomb perforated panel",
                w * 6, h * 4, 512, 512, normal_strength=1.5)
    d, _ = hex_field(s.x, s.y, r)
    a = w / 2 - HEX_WEB / 2
    hole = smoothstep(a + 0.0012, a - 0.0012, d)
    lattice = to_linear((0.98, 0.86, 0.05))
    dark = to_linear((0.05, 0.045, 0.02))
    s.fill(lattice, 0.42)
    s.base *= (0.95 + 0.07 * s.noise(0.05, 91, 2))[..., None]
    s.tint(hole, dark, 1.0)
    s.relief -= hole * 0.004
    s.occlude(hole, 0.3)
    s.roughen(hole, 0.8)
    return s


def led_ceiling():
    """Honeycomb LED tube ceiling over a dark grey soffit (DSC06326)."""
    R = 0.38
    w, h = sqrt(3.0) * R, 3.0 * R
    s = Surface("led-hex-ceiling", "Honeycomb LED tube grid on a dark soffit",
                w * 3, h * 2, 1024, 1024, normal_strength=1.0)
    d, _ = hex_field(s.x, s.y, R)
    edge = np.abs(d - w / 2)
    tube = smoothstep(0.022, 0.012, edge)
    halo = smoothstep(0.09, 0.0, edge) * 0.12
    s.fill(lin("#1E1F22"), 0.7)
    s.tint(np.clip(tube + halo, 0, 1), lin("#F4F8FF"), 1.0)
    s.relief += tube * 0.01
    s.roughen(tube, 0.3)
    return s


# ---------------------------------------------------------------- signage

def wordmark_mask(width_px, height_px):
    """MCR___1: wide geometric capitals, the R's leg running out as an
    underline into the numeral."""
    mcr = type_mask("MCR", "din_bold", scale_x=1.18)
    one = type_mask("1", "black", scale_x=1.25)
    cap = height_px
    mcr_w = mcr.shape[1] * cap / mcr.shape[0]
    one_w = one.shape[1] * cap / one.shape[0]
    out = np.zeros((height_px, width_px), F)
    paste(out, mcr, 0, 0, mcr_w, cap)
    paste(out, one, width_px - one_w, 0, one_w, cap)
    bar = cap * 0.15
    x0 = mcr_w - cap * 0.22
    out[int(cap - bar):cap, int(x0):int(width_px - one_w * 0.35)] = 1.0
    return out


def roundel_text_mask(width_px, height_px):
    m = type_mask("MCR1", "din_bold", scale_x=1.12)
    out = np.zeros((height_px, width_px), F)
    w = m.shape[1] * height_px / m.shape[0]
    paste(out, m, (width_px - w) / 2, 0, w, height_px)
    return out


def lightbox(width_m, height_m, ppm, seed):
    """Top-down sRGB RGB of a lit honeycomb panel `width_m` x `height_m`."""
    w, h = int(round(width_m * ppm)), int(round(height_m * ppm))
    xs = (np.arange(w, dtype=F) + 0.5) / ppm
    ys = height_m - (np.arange(h, dtype=F) + 0.5) / ppm
    x, y = np.meshgrid(xs, ys)
    d, ids = hex_field(x + seed * 0.011, y)
    a = sqrt(3.0) * HEX_R / 2 - HEX_WEB / 2
    hole = smoothstep(a + 1.2 / ppm, a - 1.2 / ppm, d)
    lattice = np.array((0.80, 0.66, 0.03), F)
    # LED lightbox: brighter centre band, soft falloff to the frame, faint
    # module seams every 0.6 m.
    across = smoothstep(0.0, 0.10, x) * smoothstep(width_m, width_m - 0.10, x)
    up = 1.0 - 0.25 * ((y / height_m - 0.5) * 2) ** 2
    seam = 1.0 - 0.06 * smoothstep(0.012, 0.0, np.abs(np.mod(x, 0.6) - 0.3))
    glow = (0.82 + 0.18 * across * up) * seam
    rgb = lattice[None, None, :] * glow[..., None]
    hole_rgb = np.array((0.07, 0.06, 0.02), F) + 0.05 * hash01(ids, seed)[..., None] * np.array((1, 0.8, 0.1), F)
    rgb = rgb * (1 - hole[..., None]) + hole_rgb * hole[..., None]
    return rgb.astype(F)


def stamp_letters(rgb, mask, colour=(1.0, 0.93, 0.08), outline_px=8):
    """Solid lit letters with a thin dark keyline, over a lightbox."""
    keyline = np.clip(blur(mask, outline_px / 2, 2) * 3.0, 0, 1)
    rgb = rgb * (1 - keyline[..., None]) + np.array((0.12, 0.09, 0.01), F) * keyline[..., None]
    col = np.array(colour, F)
    return rgb * (1 - mask[..., None]) + col * mask[..., None]


def blade_art(ppm):
    """Projecting blade: black box, neon arrow, CONVENIENCE / STORE / VAPE."""
    wm, hm = SIGN_REGIONS["Blade"][2:]
    W, H = int(round(wm * ppm)), int(round(hm * ppm))
    c = PrintCanvas("blade", W, H)
    c.rect(0, 0, W, H, (0.02, 0.02, 0.025))
    green, red, blue, pink = (0.25, 1.0, 0.45), (1.0, 0.18, 0.22), (0.3, 0.55, 1.0), (1.0, 0.35, 0.8)
    t = 9
    # Bent arrow pointing down-left to the door, as in the night photograph.
    pts = [(W * 0.78, H * 0.05), (W * 0.93, H * 0.05), (W * 0.93, H * 0.80), (W * 0.40, H * 0.80),
           (W * 0.40, H * 0.93), (W * 0.07, H * 0.72), (W * 0.40, H * 0.51), (W * 0.40, H * 0.64),
           (W * 0.78, H * 0.64)]
    for a, b in zip(pts, pts[1:] + pts[:1]):
        c.line(*a, *b, t, green)
    c.text("STORE", W * 0.50, H * 0.745, 44, red, "black", align="CENTER", scale_x=0.9)
    c.text("24/7", W * 0.62, H * 0.60, 40, pink, "black", align="CENTER")
    # Vape bottle icon.
    c.rect(W * 0.20, H * 0.14, W * 0.16, H * 0.30, blue)
    c.rect(W * 0.235, H * 0.08, W * 0.09, H * 0.07, (0.95, 0.95, 1.0))
    c.rect(W * 0.225, H * 0.20, W * 0.11, H * 0.12, (0.95, 0.95, 1.0))
    rgba = c.render(WORK_DIR / "blade.png")
    rgb = rgba[..., :3][::-1].copy()
    # Vertical CONVENIENCE along the arrow shaft.
    conv = type_mask("CONVENIENCE", "black")
    conv = np.rot90(conv, -1)
    tall = np.zeros((H, W), F)
    cw = W * 0.09
    paste(tall, conv, W * 0.815, H * 0.10, cw, cw * conv.shape[0] / conv.shape[1])
    rgb = rgb * (1 - tall[..., None]) + np.array(pink, F) * tall[..., None]
    # Neon bloom: tubes spill a soft halo onto the black face.
    bright = np.clip(rgb - 0.25, 0, 1)
    rgb = np.clip(rgb + blur(bright, 7) * 0.9, 0, 1)
    return rgb


def signage_atlas():
    W, H = SIGN_SIZE
    atlas = np.zeros((H, W, 3), F)
    atlas[:] = (0.02, 0.02, 0.022)
    ppm = SIGN_PPM

    def region(name):
        x, y, wm, hm = SIGN_REGIONS[name]
        return x, y, int(round(wm * ppm)), int(round(hm * ppm))

    # Front: roundel text near the corner, wordmark across the main bay.
    x, y, w, h = region("Front")
    panel = lightbox(8.60, 0.62, ppm, 1)
    m = np.zeros((h, w), F)
    # Roundel centre sits 1.48 m along the carrier (createMCR1 ring_u - 0.07).
    # Kept inside the 0.365 m inner radius of the white ring.
    rw = int(0.62 * ppm)
    paste(m, roundel_text_mask(rw, int(0.17 * ppm)), 1.48 * ppm - rw / 2, (0.31 - 0.085) * ppm, rw, 0.17 * ppm)
    panel = stamp_letters(panel, m)
    # Roundel disc face behind the text is darker so the white ring reads.
    xx, yy = np.meshgrid(np.arange(w) + 0.5, np.arange(h) + 0.5)
    disc = smoothstep(0.35 * ppm, 0.33 * ppm, np.hypot(xx - 1.48 * ppm, yy - 0.31 * ppm))
    panel = panel * (1 - 0.35 * disc[..., None] * (1 - m[..., None]))
    wm = np.zeros((h, w), F)
    paste(wm, wordmark_mask(int(4.9 * ppm), int(0.40 * ppm)), 3.2 * ppm, 0.11 * ppm, 4.9 * ppm, 0.40 * ppm)
    atlas[y:y + h, x:x + w] = stamp_letters(panel, wm)

    x, y, w, h = region("Side")
    panel = lightbox(2.85, 0.62, ppm, 2)
    wm = np.zeros((h, w), F)
    paste(wm, wordmark_mask(int(2.35 * ppm), int(0.34 * ppm)), 0.25 * ppm, 0.14 * ppm, 2.35 * ppm, 0.34 * ppm)
    atlas[y:y + h, x:x + w] = stamp_letters(panel, wm)

    x, y, w, h = region("Corner")
    atlas[y:y + h, x:x + w] = lightbox(1.27, 0.62, ppm, 3)

    x, y, w, h = region("Blade")
    atlas[y:y + h, x:x + w] = blade_art(ppm)

    rgba = np.dstack((atlas, np.ones((H, W), F)))
    return write_rgba("signage-atlas-basecolor.png", rgba)


# ---------------------------------------------------------------- vinyls

PRODUCT_COLOURS = [(0.85, 0.1, 0.12), (0.1, 0.35, 0.85), (0.1, 0.6, 0.25), (0.5, 0.15, 0.6),
                   (0.95, 0.45, 0.05), (0.1, 0.1, 0.12), (0.9, 0.9, 0.92), (0.75, 0.05, 0.4),
                   (0.2, 0.7, 0.85), (0.55, 0.3, 0.12)]


def draw_products(c, rng, x0, x1, y0, y1, ppm, density=1.0):
    """Scatter crisp packets, bottles, cans and bars over a print area."""
    area = (x1 - x0) * (y1 - y0) / (ppm * ppm)
    ppm = ppm * 1.7                     # products are printed larger than life
    for _ in range(int(area * 9 * density)):
        kind = rng.choice(["packet", "bottle", "can", "bar", "tub"], p=[0.3, 0.25, 0.2, 0.15, 0.1])
        col = PRODUCT_COLOURS[rng.integers(len(PRODUCT_COLOURS))]
        cx, cy = rng.uniform(x0, x1), rng.uniform(y0, y1)
        if kind == "packet":
            w, h = 0.16 * ppm, 0.22 * ppm
            c.poly([(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2 + 4), (cx + w / 2 + 3, cy + h / 2),
                    (cx - w / 2 - 2, cy + h / 2 - 3)], col)
            c.rect(cx - w / 2, cy - h * 0.1, w, h * 0.18, (0.97, 0.9, 0.2))
            c.circle(cx, cy + h * 0.22, w * 0.22, (0.95, 0.8, 0.45))
        elif kind == "bottle":
            w, h = 0.065 * ppm, 0.24 * ppm
            c.rect(cx - w / 2, cy - h * 0.25, w, h * 0.75, col)
            c.rect(cx - w * 0.2, cy - h / 2, w * 0.4, h * 0.26, col)
            c.rect(cx - w * 0.22, cy - h / 2 - 6, w * 0.44, 7, (0.95, 0.95, 0.95))
            c.rect(cx - w / 2, cy, w, h * 0.15, (0.96, 0.96, 0.9))
        elif kind == "can":
            w, h = 0.06 * ppm, 0.12 * ppm
            c.rect(cx - w / 2, cy - h / 2, w, h, col)
            c.rect(cx - w / 2, cy - h / 2, w, 5, (0.8, 0.8, 0.82))
        elif kind == "bar":
            w, h = 0.20 * ppm, 0.05 * ppm
            c.rect(cx - w / 2, cy - h / 2, w, h, col)
            c.rect(cx - w * 0.3, cy - h * 0.3, w * 0.6, h * 0.6, (0.95, 0.95, 0.9))
        else:
            c.circle(cx, cy, 0.05 * ppm, col)
            c.ring(cx, cy, 0.05 * ppm, 0.035 * ppm, (0.95, 0.95, 0.95))


def vinyl_strip():
    W, H = VINYL_SIZE
    ppm_y = H / VINYL_SPAN_M
    print_top = H - VINYL_PRINT_M * ppm_y                  # canvas y of the print's top edge
    xs = vinyl_pane_x()
    rng = np.random.default_rng(7)
    c = PrintCanvas("vinyl", W, H)
    yellow = (0.99, 0.84, 0.06)
    ink = (0.06, 0.05, 0.05)
    for prefix, width, style in VINYL_PANES:
        x0 = xs[prefix]
        x1 = x0 + width * VINYL_PPM_X
        if style == "door":
            # Door glass stays clear: an opening-hours sticker and a push plate.
            c.rect(x0 + 0.22 * VINYL_PPM_X, H - 1.02 * ppm_y, 0.30 * VINYL_PPM_X, 0.12 * ppm_y, (0.8, 0.08, 0.1))
            c.text("OPEN 24 HOURS", x0 + 0.37 * VINYL_PPM_X, H - 0.935 * ppm_y, 22, (1, 1, 1), "black",
                   align="CENTER", scale_x=0.8)
            c.circle(x0 + 1.05 * VINYL_PPM_X, H - 0.98 * ppm_y, 0.07 * VINYL_PPM_X, yellow)
            c.text("MCR1", x0 + 1.05 * VINYL_PPM_X, H - 0.965 * ppm_y, 17, ink, "black", align="CENTER")
            continue
        c.rect(x0, print_top, x1 - x0, H - print_top, yellow)
        if style == "front":
            # The vape panel nearest the corner: violet night-sky gradient.
            vx1 = x0 + 2.2 * VINYL_PPM_X
            for i in range(12):
                t = i / 11
                col = (0.25 + 0.4 * t, 0.08 + 0.05 * t, 0.55 - 0.2 * t)
                c.rect(x0, print_top + (H - print_top) * i / 12, vx1 - x0, (H - print_top) / 12 + 1, col)
            for k in range(7):
                bx = x0 + (0.25 + k * 0.27) * VINYL_PPM_X
                bh = rng.uniform(0.35, 0.6) * ppm_y
                c.rect(bx, H - bh - 0.06 * ppm_y, 0.07 * VINYL_PPM_X, bh, PRODUCT_COLOURS[k % 10])
                c.rect(bx, H - bh - 0.06 * ppm_y, 0.07 * VINYL_PPM_X, 10, (0.95, 0.95, 0.95))
            c.text("VAPE", x0 + 1.1 * VINYL_PPM_X, print_top + 0.34 * ppm_y, 150, (1.0, 0.62, 0.1), "black",
                   align="CENTER")
            draw_products(c, rng, vx1 + 40, x1 - 40, print_top + 0.34 * ppm_y, H - 50, VINYL_PPM_X)
            c.text("SNACKS · DRINKS · GROCERIES", (vx1 + x1) / 2, print_top + 0.12 * ppm_y, 54, ink, "black",
                   align="CENTER", scale_x=0.85)
        else:
            draw_products(c, rng, x0 + 40, x1 - 40, print_top + (0.34 if style == "side" else 0.14) * ppm_y,
                          H - 50, VINYL_PPM_X,
                          density=1.2 if style == "side" else 0.9)
            if style == "side":
                c.text("OPEN 24 HOURS", (x0 + x1) / 2, print_top + 0.12 * ppm_y, 54, ink, "black",
                       align="CENTER", scale_x=0.85)
    rgba = c.render(WORK_DIR / "vinyl.png")[::-1].copy()    # top-down sRGB
    alpha = rgba[..., 3]

    # Faint honeycomb printed into the yellow ground, as on the lightboxes.
    yy, xx = np.mgrid[0:H, 0:W].astype(F)
    d, _ = hex_field(xx / VINYL_PPM_X, yy / ppm_y, 0.06)
    lines = smoothstep(0.004, 0.0015, np.abs(d - sqrt(3.0) * 0.06 / 2))
    is_yellow = np.all(np.abs(rgba[..., :3] - np.array(yellow, F)) < 0.05, axis=-1).astype(F)
    rgba[..., :3] *= (1 - 0.18 * lines * is_yellow)[..., None]

    # Clear glass everywhere the print is not: faint cool tint, low alpha.
    glass = np.array((0.30, 0.38, 0.40), F)
    rgba[..., :3] = rgba[..., :3] * alpha[..., None] + glass * (1 - alpha[..., None])
    rgba[..., 3] = np.maximum(alpha, 0.16)
    return write_rgba("window-vinyl-basecolor.png", rgba)


# ------------------------------------------------------- upper-floor glazing

def upper_glazing():
    """Four sash variants: net curtains, blinds, one lit office, dark glass."""
    W, H = 256 * UPPER_WINDOW_CELLS, 512
    rng = np.random.default_rng(3)
    out = np.zeros((H, W, 3), F)
    for k in range(UPPER_WINDOW_CELLS):
        yy, xx = np.mgrid[0:H, 0:256].astype(F)
        u, v = xx / 256, 1 - yy / H                      # v up
        # Night reflection: dark blue-grey glass with the street's sodium
        # glow rising from the bottom and a soft diagonal sheen.
        sky = np.array((0.05, 0.06, 0.08), F) + np.array((0.16, 0.10, 0.04), F) * (1 - v)[..., None] ** 3
        sheen = smoothstep(0.08, 0.0, np.abs(u - v * 0.6 - 0.15)) * 0.10
        cell = sky + sheen[..., None]
        if k in (0, 2):
            # Net curtains gathered at both jambs, as in DSC06327.
            fold = 0.5 + 0.5 * np.sin(u * 2 * pi * 18 + np.sin(v * 7) * 0.8)
            left = smoothstep(0.34, 0.26, u) if k == 0 else smoothstep(0.22, 0.15, u)
            right = smoothstep(0.66, 0.74, u) if k == 0 else smoothstep(0.80, 0.86, u)
            net = np.clip(left + right, 0, 1) * (0.55 + 0.25 * fold)
            cell = cell * (1 - net[..., None] * 0.8) + np.array((0.48, 0.47, 0.44), F) * net[..., None] * 0.8
        if k == 1:
            # Warm lit office, venetian blind lowered to the transom.
            room = np.array((0.95, 0.72, 0.42), F) * (0.55 + 0.45 * v)[..., None]
            blind = (np.mod(yy, 9) < 6).astype(F) * (v > 0.55)
            cell = room * (1 - blind[..., None] * 0.55)
            cell += smoothstep(0.03, 0.0, np.abs(v - 0.92))[..., None] * np.array((0.4, 0.4, 0.35), F)
        if k == 3:
            # Empty dark office, a ceiling panel faintly visible.
            cell += smoothstep(0.05, 0.0, np.abs(v - 0.88))[..., None] * np.array((0.10, 0.11, 0.12), F)
        grime = rng.uniform(0.9, 1.0)
        out[:, k * 256:(k + 1) * 256] = cell * grime
    rgba = np.dstack((np.clip(out, 0, 1), np.ones((H, W), F)))
    return write_rgba("upper-glazing-basecolor.png", rgba)


# --------------------------------------------------------------- shelving

def shelving():
    """Wall gondolas crammed with stock, under cold white LED light."""
    W, H = 1024 * SHELF_CELLS, 1024
    c = PrintCanvas("shelves", W, H)
    rng = np.random.default_rng(19)
    for k in range(SHELF_CELLS):
        x0 = k * 1024
        c.rect(x0, 0, 1024, H, (0.86, 0.87, 0.88))
        shelf_ys = [80, 250, 410, 570, 730, 890]
        for i, sy in enumerate(shelf_ys):
            top = shelf_ys[i - 1] + 26 if i else 20
            x = x0 + 12
            while x < x0 + 1010:
                kind = rng.choice(["box", "bottle", "packet", "jar"])
                col = PRODUCT_COLOURS[rng.integers(len(PRODUCT_COLOURS))]
                gap = sy - top - 4
                w = {"box": rng.uniform(40, 70), "bottle": rng.uniform(22, 30),
                     "packet": rng.uniform(45, 60), "jar": rng.uniform(30, 40)}[kind]
                h = gap * {"box": rng.uniform(0.6, 1.0), "bottle": rng.uniform(0.7, 0.95),
                           "packet": rng.uniform(0.55, 0.85), "jar": rng.uniform(0.3, 0.45)}[kind]
                w = max(8.0, min(w, x0 + 1012 - x))
                c.rect(x, sy - h, w - 2, h, col)
                c.rect(x + 3, sy - h * 0.6, w - 8, h * 0.18, (0.95, 0.95, 0.9))
                if kind == "bottle":
                    c.rect(x + w * 0.3, sy - h - 10, w * 0.35, 12, (0.9, 0.9, 0.9))
                x += w + rng.uniform(0, 4)
            # Shelf edge with yellow price strip.
            c.rect(x0, sy, 1024, 22, (0.93, 0.93, 0.94))
            c.rect(x0, sy + 8, 1024, 9, (0.98, 0.85, 0.08))
        c.rect(x0, 930, 1024, 94, (0.25, 0.25, 0.27))
        c.rect(x0, 0, 10, H, (0.7, 0.7, 0.72))
        c.rect(x0 + 1014, 0, 10, H, (0.7, 0.7, 0.72))
    rgba = c.render(WORK_DIR / "shelves.png")[::-1].copy()
    rgba[..., 3] = 1.0
    return write_rgba("shelving-basecolor.png", rgba)


# -------------------------------------------------------------------- main

def build_all():
    TEXTURE_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    records = [write_surface(build()) for build in (brick_pressed_red, sandstone_dressed, honeycomb_pier,
                                                   led_ceiling)]
    artwork = [p.name for p in (signage_atlas(), vinyl_strip(), upper_glazing(), shelving())]
    for p in WORK_DIR.glob("*"):
        p.unlink()
    WORK_DIR.rmdir()
    manifest = {
        "asset": "mcr1",
        "state": "illuminated signage (pre-removal), daylight-reference fabric",
        "convention": {"orm": "R occlusion, G roughness, B metallic", "normal": "OpenGL +Y",
                       "artwork": "sRGB base colour, also used as the emissive map at runtime"},
        "tiling_surfaces": records,
        "artwork": artwork,
    }
    (TEXTURE_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"MCR1 textures written to {TEXTURE_DIR.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    build_all()
