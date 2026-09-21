"""Surface materials for the Vinyl Exchange detail pass.

The blockout (`createVinylExchangeBlockout.py`) carries flat placeholder
materials.  This script authors the first batch of real materials for the
corner: tiling PBR sets at metric scale, written as glTF-convention maps
(sRGB base colour, ORM, OpenGL tangent-space normal) under
`blender/source/textures/vinyl-exchange/`.

Why tiling material sets rather than a baked atlas.  The geometry is still on
a detail-pass hold (brief section 47 adds pilasters, capitals, moulded arches,
vent slats, the accordion gate and the lettering), so an atlas baked on the
blockout UVs would be thrown away with the geometry it was baked for.  These
surfaces are resolution- and geometry-independent: they describe what each
material *is* -- coursing, panel joints, glaze, ribs, paint, rust -- and survive
the detail pass.  Weathering that depends on where a texel sits in the world --
the drip below one sill, the spray line at the kerb, the hand height on one
door -- belongs to the later `surfaceWeathering` atlas bake on the finished
geometry, and is deliberately not baked in here.  Two surfaces are bounded
elements whose vertical extent is already known, so they are authored with a
real top and bottom and tile only horizontally: the fascia band and the door.

The palette is measured, not invented.  Every colour below is anchored on a
patch median sampled from the photographs in
`references/architecture/buildings/vinyl-exchange/` (see MEASURED), then
de-lit by hand: the photographs carry hard August sun and deep shade, so the
sampled value is treated as evidence of hue and relative value, and the
authored figure is the albedo that would produce it.  Nothing is copied out of
a photograph -- no pixels from the references reach the output.

Run:

    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --factory-startup --python blender/scripts/vinylExchangeTextures.py

Add `-- --no-render` to write the maps without the review renders.
"""

import json
import sys
from math import radians
from pathlib import Path

import numpy as np

sys.path.append(str(Path(__file__).resolve().parent))

from surfaceWeathering import (  # noqa: E402
    F,
    fbm2_tile,
    height_to_normal,
    noise2_tile,
    smoothstep,
    srgb_decode,
    srgb_encode,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "vinyl-exchange"
RENDER_DIR = PROJECT_ROOT / "renders" / "vinyl-exchange-textures"

# A lattice period this large never wraps inside one tile, so tiling and
# non-tiling axes share one noise path.
NO_TILE = 1 << 20


# Patch medians from the reference photographs, as sRGB hex.  Each is the
# median of a rectangle sampled from the named file; the photograph's own
# lighting is still in these numbers, which is why the authored albedos in the
# material functions sit above the shaded samples and below the sunlit ones.
MEASURED = {
    "stone shaded":        ("DSC06349.JPG", "#A9A0A1"),
    "stone sunlit":        ("DSC06349.JPG", "#FFFEFD (clipped)"),
    "fascia grey sunlit":  ("DSC06347.JPG", "#9AA1B1"),
    "fascia grey shaded":  ("DSC06354.JPG", "#D1CFD0"),
    "fascia dirt bloom":   ("DSC06349.JPG", "#828C9D"),
    "logo red face":       ("DSC06349.JPG", "#5C091D"),
    "logo red lower":      ("DSC06349.JPG", "#570216"),
    "tagline strip":       ("DSC06349.JPG", "#303239"),
    "corner sign black":   ("DSC06349.JPG", "#41495B"),
    "window frame blue":   ("DSC06349.JPG", "#546A8D (with glass)"),
    "ribbed pier shaded":  ("DSC06354.JPG", "#4C413D"),
    "ribbed pier lit":     ("DSC06347.JPG", "#4D4F52"),
    "tile band":           ("DSC06354.JPG", "#BEAEA3"),
    "corner door green":   ("DSC06347.JPG", "#584B30"),
    "grille / louvre":     ("DSC06349.JPG", "#17171B"),
}


def lin(hex_colour):
    """Linear RGB triple from an sRGB hex string."""
    h = hex_colour.lstrip("#")
    return srgb_decode(np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], F) / 255.0)


# ------------------------------------------------------------------- surface

class Surface:
    """One material tile: metric coordinates in, glTF map set out.

    `x` runs across the tile and `y` runs up it, both in metres, with the
    bottom row first so the arrays are already in Blender's bottom-up image
    order.  A tiling axis wraps every noise lattice, stamp and joint line, so
    the written maps repeat seamlessly on that axis.
    """

    def __init__(self, slug, description, width, height, px_w, px_h,
                 tile_u=True, tile_v=True, normal_strength=1.0):
        self.slug = slug
        self.description = description
        self.width, self.height = float(width), float(height)
        self.w_px, self.h_px = int(px_w), int(px_h)
        self.tile_u, self.tile_v = bool(tile_u), bool(tile_v)
        self.normal_strength = normal_strength
        self.texel_x = self.width / self.w_px
        self.texel_y = self.height / self.h_px
        self.shape = (self.h_px, self.w_px)

        # Texel centres, so a wrapped stamp lands the same on both seams.
        xs = (np.arange(self.w_px, dtype=F) + 0.5) * self.texel_x
        ys = (np.arange(self.h_px, dtype=F) + 0.5) * self.texel_y
        self.x, self.y = np.meshgrid(xs, ys)

        self.base = np.zeros((self.h_px, self.w_px, 3), F)
        self.rough = np.full(self.shape, 0.5, F)
        self.metal = np.zeros(self.shape, F)
        self.ao = np.ones(self.shape, F)
        self.relief = np.zeros(self.shape, F)   # metres, positive outward

    # ------------------------------------------------------------- sampling

    def _periods(self, feature):
        """Lattice cell counts across and up the tile for a feature size."""
        fu, fv = (feature, feature) if np.isscalar(feature) else feature
        cells_x = max(1, int(round(self.width / fu)))
        cells_y = max(1, int(round(self.height / fv)))
        return cells_x, cells_y

    def noise(self, feature, seed, octaves=1, gain=0.5, warp=None):
        """Value noise (or fbm) in [0, 1], wrapping on the tiling axes.

        `feature` is the metric size of one lattice cell, either a scalar or
        (across, up) to stretch the field -- how the run-down streaks and the
        brushed metal are made.  `warp` is an optional (dx, dy) pair of metric
        offset fields; because a warp field is itself periodic, warping does
        not break the tile.
        """
        cells_x, cells_y = self._periods(feature)
        x, y = (self.x, self.y) if warp is None else (self.x + warp[0], self.y + warp[1])
        q = np.stack(((x / self.width * cells_x).ravel(),
                      (y / self.height * cells_y).ravel()), axis=1)
        period = (cells_x if self.tile_u else NO_TILE,
                  cells_y if self.tile_v else NO_TILE)
        if octaves == 1:
            value = noise2_tile(q, period, seed)
        else:
            value = fbm2_tile(q, period, octaves, seed, gain)
        return value.reshape(self.shape)

    def ridges(self, feature, seed, width=0.08, octaves=2, warp=None):
        """Thin branching crack lines: the ridge of a warped noise field."""
        n = self.noise(feature, seed, octaves, warp=warp)
        return smoothstep(1.0 - width, 1.0, 1.0 - np.abs(n * 2.0 - 1.0))

    def repeat(self, coord, pitch, offset=0.0):
        """Signed distance in metres to the nearest line of a periodic set."""
        phase = np.mod(coord + offset, pitch)
        return np.minimum(phase, pitch - phase)

    def stamp(self, field, cx, cy, radius, value=1.0, core=0.35, elongate=1.0):
        """Maximum-blend one soft round mark into a field, wrapping the tile."""
        rx = radius * elongate
        half_x = int(np.ceil(rx / self.texel_x)) + 2
        half_y = int(np.ceil(radius / self.texel_y)) + 2
        ix, iy = int(cx / self.texel_x), int(cy / self.texel_y)
        xs = np.arange(ix - half_x, ix + half_x + 1)
        ys = np.arange(iy - half_y, iy + half_y + 1)
        dx = (xs + 0.5) * self.texel_x - cx
        dy = (ys + 0.5) * self.texel_y - cy
        if self.tile_u:
            xi = np.mod(xs, self.w_px)
        else:
            keep = (xs >= 0) & (xs < self.w_px)
            xs, dx, xi = xs[keep], dx[keep], xs[keep]
        if self.tile_v:
            yi = np.mod(ys, self.h_px)
        else:
            keep = (ys >= 0) & (ys < self.h_px)
            ys, dy, yi = ys[keep], dy[keep], ys[keep]
        if not len(xi) or not len(yi):
            return
        d = np.sqrt((dy[:, None] / radius) ** 2 + (dx[None, :] / rx) ** 2)
        mark = smoothstep(1.0, core, d) * value
        window = np.ix_(yi, xi)
        field[window] = np.maximum(field[window], mark)

    def runs(self, count, seed, y_top, length, width, taper=0.55):
        """Run-down stains: narrow vertical tracks starting at one height."""
        rng = np.random.default_rng(seed)
        field = np.zeros(self.shape, F)
        for _ in range(count):
            cx = rng.uniform(0.0, self.width)
            run = rng.uniform(*length)
            half = rng.uniform(*width) * 0.5
            strength = rng.uniform(0.35, 1.0)
            start = y_top - rng.uniform(0.0, 0.02)
            dx = self.repeat(self.x - cx, self.width) if self.tile_u else np.abs(self.x - cx)
            across = smoothstep(half, half * taper, dx)
            below = smoothstep(start, start - 0.02, self.y)
            fade = smoothstep(start - run, start - run * 0.35, self.y)
            field = np.maximum(field, across * below * fade * strength)
        # Wobble: a run follows the surface, it does not draw a ruled line.
        return field * (0.55 + 0.45 * self.noise((0.05, 0.35), seed + 7, 2))

    # -------------------------------------------------------------- layering

    def fill(self, colour, rough, metal=0.0):
        self.base[:] = colour
        self.rough[:] = rough
        self.metal[:] = metal

    def tint(self, mask, colour, strength=1.0):
        a = np.clip(mask * strength, 0.0, 1.0)[..., None]
        self.base = self.base * (1.0 - a) + np.asarray(colour, F) * a

    def shade(self, mask, factor, strength=1.0):
        """Scale base colour without changing its hue (soot, wash, wear)."""
        a = np.clip(mask * strength, 0.0, 1.0)[..., None]
        self.base = self.base * (1.0 - a + a * F(factor))

    def roughen(self, mask, value, strength=1.0):
        a = np.clip(mask * strength, 0.0, 1.0)
        self.rough = self.rough * (1.0 - a) + F(value) * a

    def metalise(self, mask, value, strength=1.0):
        a = np.clip(mask * strength, 0.0, 1.0)
        self.metal = self.metal * (1.0 - a) + F(value) * a

    def occlude(self, mask, value, strength=1.0):
        a = np.clip(mask * strength, 0.0, 1.0)
        self.ao = np.minimum(self.ao, 1.0 - a * (1.0 - F(value)))

    # ----------------------------------------------------------------- write

    def maps(self):
        """(base colour RGBA, ORM RGBA, normal RGBA) as bottom-up float grids."""
        one = np.ones(self.shape, F)
        base = np.dstack((srgb_encode(np.clip(self.base, 0.0, 1.0)), one))
        orm = np.dstack((np.clip(self.ao, 0, 1),
                         np.clip(self.rough, 0.02, 1.0),
                         np.clip(self.metal, 0, 1), one))
        # Relief is authored in metres; the gradient uses the across-tile texel
        # size, so an anisotropic tile keeps its slopes honest in x.
        normal = np.dstack((height_to_normal(self.relief, self.texel_x,
                                             self.normal_strength), one))
        return base, orm, normal

    def record(self):
        return {
            "slug": self.slug,
            "description": self.description,
            "coverage_m": [round(self.width, 4), round(self.height, 4)],
            "pixels": [self.w_px, self.h_px],
            "mm_per_texel": [round(self.texel_x * 1000, 4), round(self.texel_y * 1000, 4)],
            "tiles": {"u": self.tile_u, "v": self.tile_v},
            "normal_strength": self.normal_strength,
            "roughness_range": [round(float(self.rough.min()), 3), round(float(self.rough.max()), 3)],
            "metallic_range": [round(float(self.metal.min()), 3), round(float(self.metal.max()), 3)],
            "relief_mm": [round(float(self.relief.min()) * 1000, 3), round(float(self.relief.max()) * 1000, 3)],
            "base_srgb_mean": [int(round(float(v) * 255)) for v in
                               srgb_encode(np.clip(self.base, 0, 1)).reshape(-1, 3).mean(axis=0)],
        }


# ----------------------------------------------------------------- materials

def stone_painted_ashlar():
    """Upper facade: painted ashlar render over the Victorian carcass.

    Rain washes the open faces and leaves soot in the joints and in the band
    under every course line, which is what gives the facade its horizontal
    grain in the low-angle photographs.
    """
    s = Surface("stone-painted-ashlar",
                "Upper facade painted ashlar: sooted joints, washed faces, crazed paint",
                2.40, 2.40, 2048, 2048)
    course, perpend = 0.60, 1.20
    cream, soot, wash = lin("#D5CDBC"), lin("#6C6759"), lin("#E2DED2")

    s.fill(cream, 0.78)

    # Per-block variation: sample the noise at each block's centre so one
    # block is one flat tone, as separately painted stones read.
    stagger = np.where(np.mod(np.floor(s.y / course), 2) > 0.5, perpend * 0.5, 0.0).astype(F)
    block_cx = (np.floor((s.x + stagger) / perpend) + 0.5) * perpend - stagger
    block_cy = (np.floor(s.y / course) + 0.5) * course
    block = s.noise((perpend, course), 401, warp=(block_cx - s.x, block_cy - s.y))
    s.base *= (0.972 + 0.055 * block)[..., None]

    # Paint patchiness and the fine crazing that follows it.
    patch = s.noise(0.9, 403, 3)
    s.base *= (0.95 + 0.10 * patch)[..., None]
    s.roughen(smoothstep(0.55, 0.85, patch), 0.66)
    warp = (0.012 * (s.noise(0.20, 405) - 0.5), 0.012 * (s.noise(0.20, 406) - 0.5))
    craze = s.ridges(0.085, 407, width=0.055, warp=warp)
    s.shade(craze, 0.88, 0.6)
    s.roughen(craze, 0.88, 0.5)
    s.relief -= craze * 0.00035

    # Soot: held in the joints, and in a decaying band below each course line.
    below = smoothstep(0.34, 0.03, course - np.mod(s.y, course))
    columns = s.noise((0.16, 1.8), 409, 3)
    # Lateral variation, or every course reads as one ruled gradient band.
    patchy = smoothstep(0.25, 0.75, s.noise((0.55, 0.9), 410, 2))
    # Streak-led: the wall's grain is the run-down, and the course line only
    # concentrates it.  Weighting it the other way reads as dirty brickwork.
    dirt = np.clip(columns ** 2 * (0.45 + 0.9 * patchy) * (0.55 + 0.75 * below), 0, 1)
    s.tint(dirt, soot, 0.30)
    s.roughen(dirt, 0.9, 0.5)

    # Rain-washed pale runs on the exposed faces.
    pale = smoothstep(0.70, 0.93, s.noise((0.05, 2.2), 411, 2))
    s.tint(pale, wash, 0.22)

    # Joints: 12 mm wide, recessed, sooted and occluded.
    # Painted over, so the joints read as fine shadow lines, not brick perpends.
    joint = np.maximum(smoothstep(0.0045, 0.0018, s.repeat(s.y, course)),
                       smoothstep(0.0045, 0.0018, s.repeat(s.x + stagger, perpend)))
    s.tint(joint, soot, 0.38)
    s.roughen(joint, 0.9, 0.8)
    s.relief -= joint * 0.0020
    s.occlude(joint, 0.45)

    # Render grain, plus the slight bow of each block face.
    s.relief += (s.noise(0.004, 413) - 0.5) * 0.00018
    s.relief += (s.noise(0.05, 415, 2) - 0.5) * 0.00022
    return s


def fascia_grey_panel():
    """The 1.35 m fascia band: one bounded panel bay, tiling sideways only.

    Authored with a real top and bottom because its height is fixed by the
    building: the grime that gathers along the capping and runs down from it
    is the fascia's strongest read in every photograph.
    """
    s = Surface("fascia-grey-panel",
                "Fascia band: coated panel, butt joints, fixings, top grime and run-down",
                1.35, 1.35, 2048, 2048, tile_v=False)
    grey, dirt, rust, tar = lin("#B9BABC"), lin("#8A8578"), lin("#7C5232"), lin("#1B1917")

    s.fill(grey, 0.42)

    # Coated sheet: orange peel plus a faint horizontal roller direction.
    s.relief += (s.noise(0.014, 501, 2) - 0.5) * 0.00010
    s.base *= (0.975 + 0.05 * s.noise((0.5, 0.004), 503))[..., None]
    s.base *= (0.96 + 0.08 * s.noise(0.45, 505, 2))[..., None]

    # Chalked, sun-bleached patches: lighter and much less shiny.
    chalk = smoothstep(0.55, 0.88, s.noise(0.55, 507, 3))
    s.shade(chalk, 1.06, 0.8)
    s.roughen(chalk, 0.72, 0.8)

    # Vertical butt joint on the tile seam, so panels read at 1.35 m centres.
    joint = smoothstep(0.0035, 0.0015, s.repeat(s.x, s.width))
    s.shade(joint, 0.45)
    s.roughen(joint, 0.7)
    s.relief -= joint * 0.0022
    s.occlude(joint, 0.45)

    # Capping and sill edges.
    cap = smoothstep(1.318, 1.336, s.y)
    s.shade(cap, 0.55)
    s.relief += cap * 0.0016
    s.occlude(smoothstep(1.318, 1.300, s.y), 0.6, 0.7)
    s.occlude(smoothstep(0.012, 0.0, s.y), 0.55)

    # Grime along the capping, heavier where the cable run sits.
    top = smoothstep(0.92, 1.33, s.y) * (0.45 + 0.75 * s.noise((0.35, 0.18), 509, 3))
    s.tint(np.clip(top, 0, 1), dirt, 0.5)
    s.roughen(np.clip(top, 0, 1), 0.8, 0.7)

    # Run-down from the capping, and rust tears from the upper fixings.
    drips = s.runs(30, 511, y_top=1.325, length=(0.06, 1.15), width=(0.008, 0.055))
    s.tint(drips, dirt, 0.62)
    s.roughen(drips, 0.82, 0.8)

    fixings = np.zeros(s.shape, F)
    rusty = np.zeros(s.shape, F)
    rng = np.random.default_rng(513)
    for k in range(4):
        cx = (k + 0.5) * (s.width / 4)
        for cy in (0.062, 1.286):
            s.stamp(fixings, cx, cy, 0.0062, core=0.55)
            if rng.random() < 0.45:
                s.stamp(rusty, cx, cy - 0.05, 0.05, value=0.8, core=0.0, elongate=0.22)
    s.shade(fixings, 0.72)
    s.roughen(fixings, 0.62)
    s.relief -= fixings * 0.00055
    s.occlude(fixings, 0.6)
    rusty *= smoothstep(0.35, 0.9, s.noise((0.04, 0.25), 515, 2))
    s.tint(rusty, rust, 0.5)
    s.roughen(rusty, 0.85, 0.7)

    # Road splatter: tar and grit thrown up onto the panel, in loose clusters.
    splatter = np.zeros(s.shape, F)
    for _ in range(14):
        ox, oy = rng.uniform(0, s.width), rng.uniform(0.15, 1.15)
        for _ in range(rng.integers(4, 14)):
            s.stamp(splatter,
                    ox + rng.normal(0, 0.05), oy + rng.normal(0, 0.07),
                    rng.uniform(0.0012, 0.0085), value=rng.uniform(0.5, 1.0), core=0.5)
    s.tint(splatter, tar, 0.85)
    s.roughen(splatter, 0.86)
    s.relief += splatter * 0.00012
    return s


def logo_red_acrylic():
    """Face material for the projecting logo letters: moulded acrylic.

    The letters are geometry (brief section 48); this is only their surface --
    a deep crimson that has dulled unevenly, with dust settled into the mould
    texture.
    """
    s = Surface("logo-red-acrylic",
                "Projecting logo letters: moulded crimson acrylic, dust film, fine scratches",
                0.60, 0.60, 1024, 1024, normal_strength=0.6)
    red, faded, dust = lin("#B21326"), lin("#C0384A"), lin("#C7B2A8")

    s.fill(red, 0.24)
    s.base *= (0.975 + 0.05 * s.noise(0.22, 601, 2))[..., None]

    # Mould texture: a shallow orange peel that catches the streetlights.
    s.relief += (s.noise(0.007, 603, 2) - 0.5) * 0.00006

    # Acrylic fades, but evenly: the variation is in the sheen long before it
    # is in the colour, so the tints stay light and the roughness carries it.
    sun = smoothstep(0.55, 0.95, s.noise(0.35, 605, 2))
    s.tint(sun, faded, 0.14)
    s.roughen(sun, 0.33, 0.8)

    film = smoothstep(0.45, 0.95, s.noise(0.09, 607, 3))
    s.tint(film, dust, 0.07)
    s.roughen(film, 0.40, 0.9)

    for k, seed in enumerate((609, 611, 613)):
        feature = ((0.0009, 0.09), (0.05, 0.0012), (0.0016, 0.05))[k]
        scratch = smoothstep(0.86, 0.99, s.noise(feature, seed, 2))
        scratch *= smoothstep(0.5, 0.8, s.noise(0.2, seed + 1))
        s.shade(scratch, 1.25, 0.5)
        s.roughen(scratch, 0.4, 0.6)
        s.relief -= scratch * 0.00002
    return s


def sign_black_panel():
    """The corner sign box and the tagline strip: satin black sheet.

    The tagline strip is the same coating a few shades lighter; the runtime
    material for it lifts the base colour rather than carrying its own maps.
    """
    s = Surface("sign-black-panel",
                "Corner sign box and tagline strip: satin black panel, dust bloom, wipe marks",
                1.00, 1.00, 1024, 1024, normal_strength=0.7)
    black, dust = lin("#17181A"), lin("#4C4D50")

    s.fill(black, 0.38)
    s.relief += (s.noise(0.012, 701, 2) - 0.5) * 0.00008

    bloom = smoothstep(0.5, 0.95, s.noise(0.11, 703, 4))
    s.tint(bloom, dust, 0.09)
    s.roughen(bloom, 0.5, 0.9)

    # Wiped-over dust: vertical bands where rain or a cloth has cleared it.
    wipe = smoothstep(0.6, 0.9, s.noise((0.04, 0.7), 705, 2))
    s.shade(wipe, 0.95, 0.5)
    s.roughen(wipe, 0.34, 0.6)

    scuff = smoothstep(0.88, 0.99, s.noise((0.0018, 0.07), 707, 2))
    s.shade(scuff, 2.1, 0.45)
    s.roughen(scuff, 0.5, 0.6)
    return s


def frame_blue_paint():
    """Upper-window frames: dark petrol-blue paint, chalked and micro-cracked."""
    s = Surface("frame-blue-paint",
                "Upper window frames: aged petrol-blue paint, chalking, chips to primer",
                0.30, 0.30, 1024, 1024)
    blue, chalked, primer = lin("#1E2B42"), lin("#4A5670"), lin("#6E4C33")

    s.fill(blue, 0.44)

    # Brush direction along the member, and the paint's own slight ropiness.
    s.base *= (0.95 + 0.10 * s.noise((0.0022, 0.08), 801, 2))[..., None]
    s.relief += (s.noise((0.0025, 0.09), 803, 2) - 0.5) * 0.00012

    # Chalking is a bloom on the surface, not a repaint: it lifts the sheen
    # much further than it lifts the colour.
    chalk = smoothstep(0.62, 0.96, s.noise(0.09, 805, 3))
    s.tint(chalk, chalked, 0.24)
    s.roughen(chalk, 0.82, 0.95)

    crack = s.ridges(0.018, 807, width=0.05,
                     warp=(0.003 * (s.noise(0.05, 809) - 0.5), 0.003 * (s.noise(0.05, 811) - 0.5)))
    s.shade(crack, 0.7, 0.8)
    s.roughen(crack, 0.85, 0.7)
    s.relief -= crack * 0.00012

    chips = np.zeros(s.shape, F)
    rng = np.random.default_rng(813)
    for _ in range(34):
        s.stamp(chips, rng.uniform(0, s.width), rng.uniform(0, s.height),
                rng.uniform(0.0009, 0.0045), value=rng.uniform(0.6, 1.0), core=0.75,
                elongate=rng.uniform(0.6, 1.7))
    s.tint(chips, primer, 0.85)
    s.roughen(chips, 0.88)
    s.relief -= chips * 0.00022
    s.occlude(chips, 0.7)
    return s


def shopfront_ribbed_alu():
    """Shopfront piers and reveals: vertically ribbed mill-finish aluminium."""
    s = Surface("shopfront-ribbed-alu",
                "Shopfront piers: vertically ribbed mill-finish aluminium, brushed, grimy grooves",
                0.64, 0.64, 1024, 1024, normal_strength=1.0)
    pitch = 0.032
    alu, grime = lin("#8E9194"), lin("#4A463F")

    s.fill(alu, 0.34, metal=1.0)

    # Rib profile: a shallow flute with a sharp groove at every rib edge.
    phase = np.mod(s.x, pitch) / pitch
    s.relief += 0.0022 * np.power(0.5 - 0.5 * np.cos(2 * np.pi * phase), 0.75).astype(F)
    groove = smoothstep(0.0018, 0.0006, s.repeat(s.x, pitch))
    s.relief -= groove * 0.0011
    s.occlude(groove, 0.5)

    # Per-rib mill variation, then the vertical brushing over everything.
    rib_cx = (np.floor(s.x / pitch) + 0.5) * pitch
    rib = s.noise(pitch, 901, warp=(rib_cx - s.x, -s.y))
    s.base *= (0.94 + 0.12 * rib)[..., None]
    brush = s.noise((0.0007, 0.09), 903, 2)
    s.rough = np.clip(s.rough + (brush - 0.5) * 0.16, 0.08, 1.0)
    s.base *= (0.97 + 0.06 * brush)[..., None]

    # Grime: collects in the grooves, which also kills the metal there.
    dirt = np.clip(groove * (0.35 + 0.8 * s.noise((0.05, 0.45), 905, 3))
                   + 0.30 * smoothstep(0.6, 0.95, s.noise(0.18, 907, 3)), 0, 1)
    s.tint(dirt, grime, 0.55)
    s.roughen(dirt, 0.72, 0.8)
    s.metalise(dirt, 0.0, 0.55)

    # Trolley and bag knocks: shallow dents that break the rib reflections.
    dents = np.zeros(s.shape, F)
    rng = np.random.default_rng(909)
    for _ in range(18):
        s.stamp(dents, rng.uniform(0, s.width), rng.uniform(0, s.height),
                rng.uniform(0.006, 0.026), value=rng.uniform(0.4, 1.0), core=0.0,
                elongate=rng.uniform(0.5, 1.4))
    s.relief -= dents * 0.00035
    s.rough = np.clip(s.rough + dents * 0.06, 0.08, 1.0)
    return s


def tile_white_glazed():
    """Shopfront base and corner columns: small white glazed tiles."""
    s = Surface("tile-white-glazed",
                "Shopfront base and corner columns: 100 mm white glazed tiles, dirty grout, chips",
                1.20, 1.20, 2048, 2048)
    pitch = 0.10
    glaze, grout, biscuit, soil = lin("#D3D0C7"), lin("#A19C91"), lin("#C6BEB0"), lin("#6A6256")

    s.fill(grout, 0.85)

    joint = np.maximum(smoothstep(0.0022, 0.0042, s.repeat(s.x, pitch)),
                       smoothstep(0.0022, 0.0042, s.repeat(s.y, pitch)))
    face = np.minimum(smoothstep(0.0022, 0.0042, s.repeat(s.x, pitch)),
                      smoothstep(0.0022, 0.0042, s.repeat(s.y, pitch)))
    s.tint(face, glaze)
    s.roughen(face, 0.11)

    # Per-tile tone, and the slight pillowing of a pressed tile.
    cx = (np.floor(s.x / pitch) + 0.5) * pitch
    cy = (np.floor(s.y / pitch) + 0.5) * pitch
    tone = s.noise(pitch, 1001, warp=(cx - s.x, cy - s.y))
    s.base *= np.where(face > 0.5, 0.95 + 0.10 * tone, 1.0)[..., None]
    px = np.clip((s.x - cx) / (pitch * 0.5), -1, 1)
    py = np.clip((s.y - cy) / (pitch * 0.5), -1, 1)
    s.relief += face * (1 - px ** 2) * (1 - py ** 2) * 0.00035
    s.relief -= (1 - face) * 0.0016
    s.occlude(1 - face, 0.42)

    # Grime lives in the grout, not on the glaze.
    dirty = (1 - face) * (0.45 + 0.9 * s.noise(0.09, 1003, 3))
    s.tint(np.clip(dirty, 0, 1), soil, 0.72)

    # Crazing in the glaze, and chips at tile corners down to the biscuit.
    craze = s.ridges(0.05, 1005, width=0.04) * face
    s.shade(craze, 0.93, 0.7)
    s.roughen(craze, 0.25, 0.6)

    chips = np.zeros(s.shape, F)
    rng = np.random.default_rng(1007)
    for _ in range(26):
        corner_x = (rng.integers(0, int(s.width / pitch)) + rng.integers(0, 2)) * pitch
        corner_y = (rng.integers(0, int(s.height / pitch)) + rng.integers(0, 2)) * pitch
        s.stamp(chips, corner_x, corner_y, rng.uniform(0.003, 0.011),
                value=rng.uniform(0.6, 1.0), core=0.6, elongate=rng.uniform(0.6, 1.6))
    s.tint(chips, biscuit, 0.9)
    s.roughen(chips, 0.8, 0.9)
    s.relief -= chips * 0.00055
    s.occlude(chips, 0.65)
    return s


def door_green_paint():
    """The corner door: a boarded door in faded sage-green paint.

    Bounded vertically, so the wear is where a door actually wears -- kicked
    at the bottom, handled at 1.05 m, sun-bleached and rain-run at the top.
    """
    s = Surface("door-green-paint",
                "Corner recess door: boarded sage-green paint, kick scuffs, hand grime, tape residue",
                1.15, 2.30, 1024, 2048, tile_v=False)
    pitch = s.width / 6
    green, bleached, primer, grime = lin("#6E7359"), lin("#878B72"), lin("#7A6E55"), lin("#4A4534")

    s.fill(green, 0.48)
    s.base *= (0.93 + 0.14 * s.noise((0.004, 0.22), 1101, 2))[..., None]

    # Boarded face: a V-groove on every board joint.
    groove = smoothstep(0.0055, 0.0018, s.repeat(s.x, pitch))
    s.relief -= groove * 0.0032
    s.shade(groove, 0.7)
    s.occlude(groove, 0.4)
    board_cx = (np.floor(s.x / pitch) + 0.5) * pitch
    board = s.noise(pitch, 1103, warp=(board_cx - s.x, -s.y))
    s.base *= (0.95 + 0.10 * board)[..., None]

    # Sun bleaches the upper half; rain runs down from the head.
    sun = smoothstep(1.05, 2.25, s.y) * (0.5 + 0.6 * s.noise(0.35, 1105, 2))
    s.tint(np.clip(sun, 0, 1), bleached, 0.55)
    s.roughen(np.clip(sun, 0, 1), 0.72, 0.8)
    drips = s.runs(16, 1107, y_top=2.27, length=(0.10, 1.5), width=(0.010, 0.05))
    s.tint(drips, grime, 0.4)
    s.roughen(drips, 0.75, 0.7)

    # Hand zone: polished, darker, less rough than the paint around it.
    hand = smoothstep(0.72, 1.05, s.y) * smoothstep(1.48, 1.10, s.y)
    hand *= smoothstep(0.25, 0.85, s.noise((0.22, 0.30), 1109, 3))
    s.tint(np.clip(hand, 0, 1), grime, 0.22)
    s.roughen(np.clip(hand, 0, 1), 0.33, 0.6)

    # Kick zone: scrapes to the primer, and a dirt line at the threshold.
    kick = smoothstep(0.42, 0.04, s.y)
    s.tint(kick * (0.25 + 0.85 * s.noise((0.2, 0.12), 1111, 3)), grime, 0.38)
    scrapes = np.zeros(s.shape, F)
    rng = np.random.default_rng(1113)
    for _ in range(40):
        s.stamp(scrapes, rng.uniform(0, s.width), abs(rng.normal(0.06, 0.16)),
                rng.uniform(0.004, 0.022), value=rng.uniform(0.5, 1.0), core=0.5,
                elongate=rng.uniform(1.4, 3.2))
    s.tint(scrapes, primer, 0.8)
    s.roughen(scrapes, 0.85, 0.9)
    s.relief -= scrapes * 0.00025

    # Fly-posting residue: torn paper and its tape, at poster height.
    residue = np.zeros(s.shape, F)
    for _ in range(3):
        ox, oy = rng.uniform(0.1, s.width - 0.1), rng.uniform(1.45, 1.85)
        for _ in range(rng.integers(8, 18)):
            s.stamp(residue, ox + rng.normal(0, 0.035), oy + rng.normal(0, 0.045),
                    rng.uniform(0.004, 0.017), value=rng.uniform(0.5, 1.0), core=0.7,
                    elongate=rng.uniform(0.7, 2.0))
    residue *= smoothstep(0.35, 0.75, s.noise(0.02, 1115, 2))
    s.tint(residue, lin("#C9C4B4"), 0.75)
    s.roughen(residue, 0.92, 0.9)
    s.relief += residue * 0.00016
    return s


def grille_dark_steel():
    """Security gate, vent recesses and shutter framing: dark painted steel."""
    s = Surface("grille-dark-steel",
                "Security gate, vents and shutter framing: dark painted steel, rust bloom and bleed",
                0.50, 0.50, 1024, 1024)
    steel, rust, bare = lin("#202124"), lin("#5E3620"), lin("#6B6C6E")

    s.fill(steel, 0.55)
    s.relief += (s.noise(0.010, 1201, 2) - 0.5) * 0.00020
    s.base *= (0.94 + 0.12 * s.noise(0.16, 1203, 3))[..., None]

    bloom = smoothstep(0.66, 0.95, s.noise(0.055, 1205, 4))
    # The bleed below a bloom: the same field sampled from a little higher up.
    above = smoothstep(0.66, 0.95,
                       s.noise(0.055, 1205, 4, warp=(np.zeros_like(s.x), np.full_like(s.y, 0.05))))
    bleed = above * smoothstep(0.30, 0.80, s.noise((0.035, 0.30), 1207, 2))
    s.tint(np.clip(bloom + 0.6 * bleed, 0, 1), rust, 0.55)
    s.roughen(np.clip(bloom + 0.5 * bleed, 0, 1), 0.92, 0.9)
    s.relief += bloom * 0.00022

    chips = np.zeros(s.shape, F)
    rng = np.random.default_rng(1209)
    for _ in range(20):
        s.stamp(chips, rng.uniform(0, s.width), rng.uniform(0, s.height),
                rng.uniform(0.0010, 0.0038), value=rng.uniform(0.5, 1.0), core=0.7,
                elongate=rng.uniform(0.6, 1.8))
    chips *= 1.0 - bloom
    s.tint(chips, bare, 0.7)
    s.metalise(chips, 1.0, 0.6)
    s.roughen(chips, 0.45, 0.8)
    s.relief -= chips * 0.00018

    dust = smoothstep(0.5, 0.95, s.noise(0.05, 1211, 3))
    s.shade(dust, 1.06, 0.5)
    s.roughen(dust, 0.75, 0.5)
    return s


MATERIALS = (
    stone_painted_ashlar,
    fascia_grey_panel,
    logo_red_acrylic,
    sign_black_panel,
    frame_blue_paint,
    shopfront_ribbed_alu,
    tile_white_glazed,
    door_green_paint,
    grille_dark_steel,
)


# --------------------------------------------------------------------- write

def seam_report(surface, grids):
    """What one wrap costs, in 8-bit levels, against the tile's typical step.

    `wrap` is the mean absolute difference between the first and last column
    (or row); `typical` is the mean difference between any adjacent pair.  A
    wrap of a level or two is invisible whatever the ratio says -- a joint
    line or a rib groove may sit exactly on the tile edge, which makes the
    ratio large and the surface still seamless.  A wrap far above `typical`
    *and* above a few levels is a real seam.  Only tiling axes are reported.
    """
    report = {}
    for name, grid in grids.items():
        g = grid[..., :3].astype(np.float64) * 255.0
        if surface.tile_u:
            report[f"{name}_u"] = {
                "wrap": round(float(np.abs(g[:, 0] - g[:, -1]).mean()), 2),
                "typical": round(float(np.abs(g[:, 1:] - g[:, :-1]).mean()), 2),
            }
        if surface.tile_v:
            report[f"{name}_v"] = {
                "wrap": round(float(np.abs(g[0, :] - g[-1, :]).mean()), 2),
                "typical": round(float(np.abs(g[1:, :] - g[:-1, :]).mean()), 2),
            }
    return report


def write_surface(surface, texture_dir=None):
    """Write the three maps and return the record for validation.json.

    `texture_dir` lets another asset's texture script reuse this writer.
    """
    from surfaceWeathering import save_rgba

    texture_dir = texture_dir or TEXTURE_DIR
    texture_dir.mkdir(parents=True, exist_ok=True)
    base, orm, normal = surface.maps()
    grids = {"basecolor": base, "orm": orm, "normal": normal}
    files = {}
    for kind, grid in grids.items():
        path = texture_dir / f"{surface.slug}-{kind}.png"
        save_rgba(path, grid, f"{surface.slug}-{kind}")
        files[kind] = {"file": path.name, "bytes": path.stat().st_size}
    record = surface.record()
    record["files"] = files
    record["seam_levels"] = seam_report(surface, grids)
    return record


# ------------------------------------------------------------------- renders

def point_at(obj, target):
    from mathutils import Vector

    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def set_engine(scene):
    for identifier in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
        try:
            scene.render.engine = identifier
            return identifier
        except TypeError:
            continue
    return scene.render.engine


def review_render(surface, repeats=2, texture_dir=None, render_dir=None):
    """Flat-on review of `repeats` x `repeats` tiles under a raking key.

    Rendering whole tiles side by side is the seam test a human can read: any
    wrap that does not line up shows as a ruled line across the panel.
    """
    import bpy

    from surfaceWeathering import load_image

    # Resetting the file frees every datablock, so the maps are reloaded from
    # disk here rather than carried in from the writing pass.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    texture_dir = texture_dir or TEXTURE_DIR
    render_dir = render_dir or RENDER_DIR
    images = {kind: load_image(texture_dir / f"{surface.slug}-{kind}.png",
                               non_color=kind != "basecolor")
              for kind in ("basecolor", "orm", "normal")}
    scene = bpy.context.scene
    set_engine(scene)
    if hasattr(scene, "eevee"):
        for attribute, value in (("use_raytracing", True), ("use_shadows", True),
                                 ("taa_render_samples", 64)):
            if hasattr(scene.eevee, attribute):
                setattr(scene.eevee, attribute, value)
    scene.render.resolution_x = scene.render.resolution_y = 1024
    # Standard, not AgX: this is a material check, so the frame should report
    # the albedo that was authored rather than the game's grade.
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"

    world = bpy.data.worlds.new("Review")
    world.use_nodes = True
    background = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    background.inputs["Color"].default_value = (0.34, 0.36, 0.40, 1.0)
    background.inputs["Strength"].default_value = 1.0
    scene.world = world

    # A bounded surface is shown once up the frame: stacking it would repeat
    # a top and bottom edge that do not repeat on the building.
    across, up = repeats, repeats if surface.tile_v else 1
    width, height = surface.width * across, surface.height * up
    mesh = bpy.data.meshes.new(surface.slug)
    mesh.from_pydata([(-width / 2, 0, -height / 2), (width / 2, 0, -height / 2),
                      (width / 2, 0, height / 2), (-width / 2, 0, height / 2)], [], [(0, 1, 2, 3)])
    uv = mesh.uv_layers.new(name="UVMap")
    for index, coordinate in enumerate(((0, 0), (across, 0), (across, up), (0, up))):
        uv.data[index].uv = coordinate
    panel = bpy.data.objects.new(surface.slug, mesh)
    scene.collection.objects.link(panel)

    from surfaceWeathering import build_pbr_material

    material = bpy.data.materials.new(f"REVIEW_{surface.slug}")
    build_pbr_material(material, images["basecolor"], images["orm"], images["normal"],
                       normal_strength=surface.normal_strength)
    mesh.materials.append(material)

    key = bpy.data.objects.new("Key", bpy.data.lights.new("Key", "SUN"))
    key.data.energy, key.data.angle = 2.4, radians(2.5)
    # High and well off to the side: a key facing the panel square on would
    # bounce its specular lobe straight back down the lens and wash out every
    # dark satin material.
    key.location = (-width * 1.7, -height * 0.55, height * 1.5)
    point_at(key, (0, 0, 0))
    scene.collection.objects.link(key)

    # Both lights are suns, so the exposure does not depend on how large the
    # panel is: an area light placed relative to the panel lit a 0.30 m tile
    # several times harder than a 2.40 m one, and the small dark materials came
    # out looking pale.
    fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill", "SUN"))
    fill.data.energy, fill.data.angle = 0.9, radians(45)
    fill.location = (width * 1.2, -height * 1.2, height * 0.35)
    point_at(fill, (0, 0, 0))
    scene.collection.objects.link(fill)

    camera = bpy.data.objects.new("Review", bpy.data.cameras.new("Review"))
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = max(width, height) * 1.02
    camera.location = (0, -max(width, height) * 2.0, 0)
    point_at(camera, (0, 0, 0))
    scene.collection.objects.link(camera)
    scene.camera = camera

    render_dir.mkdir(parents=True, exist_ok=True)
    path = render_dir / f"{surface.slug}.png"
    scene.render.filepath = str(path)
    scene.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    return path


def contact_sheet(paths, columns=3, cell=640, render_dir=None):
    """One sheet of every review frame, for a single look at the whole set."""
    import bpy

    from surfaceWeathering import save_rgba

    rows = (len(paths) + columns - 1) // columns
    sheet = np.zeros((rows * cell, columns * cell, 4), F)
    sheet[..., 3] = 1.0
    for index, path in enumerate(paths):
        image = bpy.data.images.load(str(path), check_existing=False)
        w, h = image.size
        pixels = np.empty(w * h * 4, F)
        image.pixels.foreach_get(pixels)
        frame = pixels.reshape(h, w, 4)
        yi = (np.arange(cell) * h // cell).clip(0, h - 1)
        xi = (np.arange(cell) * w // cell).clip(0, w - 1)
        row, column = divmod(index, columns)
        # Bottom-up grid, so the first frame lands on the top row.
        top = (rows - 1 - row) * cell
        sheet[top:top + cell, column * cell:(column + 1) * cell] = frame[yi][:, xi]
        bpy.data.images.remove(image)
    path = (render_dir or RENDER_DIR) / "00-contact-sheet.png"
    save_rgba(path, sheet, "contact-sheet")
    return path


# ---------------------------------------------------------------------- main

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    render = "--no-render" not in argv

    records, frames = [], []
    for build in MATERIALS:
        surface = build()
        record = write_surface(surface)
        print(f"  {surface.slug:26s} {surface.w_px}x{surface.h_px}  "
              f"{record['mm_per_texel'][0]:.3f} mm/texel")
        for axis, step in record["seam_levels"].items():
            if step["wrap"] > max(3.0, step["typical"] * 3.0):
                print(f"      seam check {axis}: wrap {step['wrap']} levels "
                      f"vs typical {step['typical']}")
        if render:
            frames.append(review_render(surface))
        records.append(record)

    if render:
        contact_sheet(frames)

    validation = {
        "asset": "vinyl-exchange",
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
