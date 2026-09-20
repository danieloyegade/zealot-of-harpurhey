"""Sign and emissive artwork for the Spice Cabin texture pass.

The gable sign is laid out from a perspective-rectified measurement of
references/architecture/buildings/spice-cabin/7cf7a339-...jpg (photo 1): letter
centres, baselines and heights are plate fractions read from that rectification.
The front sign carries the same identity in the older arrangement photographed
from the street (food line under the right half, no phone number) and is aged
harder, as its reds have faded towards pink in those photographs.

Lettering is set in Marker Felt Wide (the closest system face) through the bus
shelter's PrintCanvas, which renders flat vector type in an orthographic scene.
Outlines, drop shadows, the chilli, the flame, the printed log background and
the sawn log-end cut-outs are drawn in numpy.  Nothing is copied from the
photographs.

The LED window sign reproduces its photographed fault: dead LEDs make "FRIED"
read "ΓPIED" in both front photographs.  Menu boards and fridge contents are
illegible by design, so no copy is invented.
"""

import struct
from math import pi, radians
from pathlib import Path

import numpy as np

import spiceCabinGeometry as geo
from busShelterArtwork import FONT_FILES, PrintCanvas
from surfaceWeathering import F, fbm2, noise2, smoothstep, srgb_decode, srgb_encode

SIGN_SIZE = (4096, 2048)
SIGN_FRONT_RECT = (0, 1040, 4096, 995)   # bottom-up pixels (x, y, w, h)
SIGN_SIDE_RECT = (0, 20, 4096, 990)
SIGN_TEXEL_M = (geo.FRONT_SIGN_PLATE[1] - geo.FRONT_SIGN_PLATE[0] + 2 * geo.DISC_OVERHANG) / 4096

EMISSIVE_SIZE = (1024, 1024)
EMISSIVE_CELLS = {
    "led": (0, 0, 720, 320),
    "fridge": (740, 0, 284, 896),
    "menu1": (0, 340, 236, 206),
    "menu2": (246, 340, 236, 206),
    "menu3": (492, 340, 236, 206),
    "ceiling": (0, 560, 180, 180),
    "tube_front": (0, 760, 720, 24),
    "tube_side": (0, 800, 720, 24),
}

GROUND_FRONT_RECT = (0, 0, 2048, 584)
GROUND_SIDE_RECT = (0, 640, 400, 1400)

MARKER_FELT = Path("/System/Library/Fonts/MarkerFelt.ttc")
CAP_RATIO = 0.70     # Marker Felt Wide cap height / font size (calibrated against the render)
XHEIGHT_RATIO = 0.50
TITLE_SCALE = 1.24   # measured letters are larger and wider than the face's proportions
TITLE_STRETCH = 1.14
# The printed letters are a far heavier brush face than Marker Felt Wide:
# embolden the rendered coverage by this fraction of the plate height.
TITLE_WEIGHT = 0.010
CHILLI_SHIFT = -0.014   # plate-fraction x offset: the chilli sits tight between P and c
FLAME_SHIFT = -0.030    # the flame dots the i of CaBiN

# Title glyphs: (glyph, centre x, baseline y, cap height, lowercase?, colour group, rotation deg).
# Plate fractions measured on the rectified photograph.
TITLE = (
    ("s", 0.112, 0.650, 0.43, True, "red", -2.0),
    ("P", 0.196, 0.650, 0.45, False, "red", 1.5),
    ("c", 0.338, 0.650, 0.43, True, "red", -1.0),
    ("e", 0.428, 0.650, 0.43, True, "red", 2.0),
    ("C", 0.556, 0.645, 0.43, False, "green", -2.5),
    ("a", 0.638, 0.655, 0.40, True, "green", 1.0),
    ("B", 0.720, 0.640, 0.44, False, "green", -1.0),
    ("I", 0.788, 0.640, 0.33, False, "green", 0.0),
    ("N", 0.869, 0.600, 0.42, False, "green", 3.0),
)
SIDE_FOOD = (("Pizza", 0.086), ("Kebabs", 0.227), ("Fried Chicken", 0.430), ("Burgers", 0.634))
SIDE_STARS = (0.148, 0.304, 0.556)
FRONT_FOOD = (("Pizza", 0.335), ("Kebabs", 0.452), ("Fried Chicken", 0.625), ("Burgers", 0.815))
FRONT_STARS = (0.388, 0.525, 0.735)

INK_BLACK = srgb_decode(np.array((20, 15, 12), F) / 255)
WHITE = srgb_decode(np.array((245, 245, 240), F) / 255)


def srgb(*rgb):
    return srgb_decode(np.array(rgb, F) / 255.0)


def marker_felt(work_dir):
    """Extract Marker Felt Wide (face 1) from the system collection for Blender."""
    target = Path(work_dir) / "fonts" / "MarkerFelt-Wide.ttf"
    if target.exists():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    data = MARKER_FELT.read_bytes()
    offset = struct.unpack(">I", data[16:20])[0]
    num_tables = struct.unpack(">H", data[offset + 4:offset + 6])[0]
    directory, body = bytearray(), bytearray()
    start = 12 + 16 * num_tables
    for t in range(num_tables):
        e = offset + 12 + 16 * t
        tag, checksum, table_offset, length = struct.unpack(">4sIII", data[e:e + 16])
        directory += struct.pack(">4sIII", tag, checksum, start + len(body), length)
        body += data[table_offset:table_offset + length]
        body += b"\0" * ((4 - len(body) % 4) % 4)
    target.write_bytes(bytes(data[offset:offset + 12] + directory + body))
    return target


# ------------------------------------------------------------- raster tools

def dilate(mask, radius):
    """Octagonal grey-scale dilation by alternating 4- and 8-neighbourhood maxima."""
    out = mask.astype(F)
    for i in range(int(round(radius))):
        m = out
        n = m.copy()
        np.maximum(n[1:], m[:-1], out=n[1:])
        np.maximum(n[:-1], m[1:], out=n[:-1])
        np.maximum(n[:, 1:], m[:, :-1], out=n[:, 1:])
        np.maximum(n[:, :-1], m[:, 1:], out=n[:, :-1])
        if i % 2:
            np.maximum(n[1:, 1:], m[:-1, :-1], out=n[1:, 1:])
            np.maximum(n[:-1, :-1], m[1:, 1:], out=n[:-1, :-1])
            np.maximum(n[1:, :-1], m[:-1, 1:], out=n[1:, :-1])
            np.maximum(n[:-1, 1:], m[1:, :-1], out=n[:-1, 1:])
        out = n
    return out


def shift(mask, dx, dy):
    out = np.zeros_like(mask)
    h, w = mask.shape
    out[max(dy, 0):h + min(dy, 0), max(dx, 0):w + min(dx, 0)] = mask[max(-dy, 0):h + min(-dy, 0), max(-dx, 0):w + min(-dx, 0)]
    return out


def over(image, colour, coverage):
    a = np.clip(coverage, 0, 1)[..., None]
    return image * (1 - a) + np.asarray(colour, F) * a


def tube_shape(shape, centre_points, half_widths, pad=4):
    """Coverage and shading coordinates of a tapered stroke along a sampled centreline."""
    h, w = shape
    pts = np.asarray(centre_points, F)
    hw = np.asarray(half_widths, F)
    x0 = int(max(pts[:, 0].min() - hw.max() - pad, 0))
    x1 = int(min(pts[:, 0].max() + hw.max() + pad, w))
    y0 = int(max(pts[:, 1].min() - hw.max() - pad, 0))
    y1 = int(min(pts[:, 1].max() + hw.max() + pad, h))
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(F)
    best = np.full(xx.shape, 1e9, F)
    across = np.zeros(xx.shape, F)
    along = np.zeros(xx.shape, F)
    for i in range(len(pts)):
        dx, dy = xx - pts[i, 0], yy - pts[i, 1]
        d = np.hypot(dx, dy) - hw[i]
        closer = d < best
        best = np.where(closer, d, best)
        j = min(i + 1, len(pts) - 1)
        k = max(i - 1, 0)
        tx, ty = pts[j] - pts[k]
        norm = max(float(np.hypot(tx, ty)), 1e-6)
        side = (dx * ty - dy * tx) / norm / max(float(hw[i]), 1.0)
        across = np.where(closer, side, across)
        along = np.where(closer, i / (len(pts) - 1), along)
    coverage = np.zeros(shape, F)
    a = np.zeros(shape, F)
    t = np.zeros(shape, F)
    coverage[y0:y1, x0:x1] = smoothstep(1.2, -1.2, best)
    a[y0:y1, x0:x1] = across
    t[y0:y1, x0:x1] = along
    return coverage, a, t


def bezier(points, samples):
    p = np.asarray(points, F)
    t = np.linspace(0, 1, samples, dtype=F)[:, None]
    if len(p) == 3:
        return (1 - t) ** 2 * p[0] + 2 * (1 - t) * t * p[1] + t ** 2 * p[2]
    return (1 - t) ** 3 * p[0] + 3 * (1 - t) ** 2 * t * p[1] + 3 * (1 - t) * t ** 2 * p[2] + t ** 3 * p[3]


# ---------------------------------------------------------------- the sign

class Plate:
    def __init__(self, plate_w, plate_h, cell_w, cell_h):
        self.ppm = cell_w / (plate_w + 2 * geo.DISC_OVERHANG)
        self.w, self.h = cell_w, cell_h
        self.x0 = geo.DISC_OVERHANG * self.ppm
        self.x1 = self.x0 + plate_w * self.ppm
        self.y0 = geo.DISC_VERTICAL * self.ppm
        self.y1 = self.y0 + plate_h * self.ppm
        self.ph = self.y1 - self.y0

    def X(self, fx):
        return self.x0 + fx * (self.x1 - self.x0)

    def Y(self, fy):
        return self.y0 + fy * self.ph


def printed_logs(plate, seed):
    """The sign's printed log-wall background (distinct from the real loglap below)."""
    h, w = plate.h, plate.w
    yy, xx = np.mgrid[0:h, 0:w].astype(F)
    band_h = plate.ph / 9.0
    v = (yy - plate.y0) / band_h
    band = np.floor(v)
    f = v - band
    # Printed round logs: a bright ridge along each log, dark rolled edges and seams.
    roundness = np.sin(np.clip(f, 0, 1) * pi)
    # Lit from above: bright shoulder high on each log, rolled-under shadow below.
    shade = 0.26 + 0.80 * roundness ** 0.7 + 0.34 * np.exp(-((f - 0.34) / 0.11) ** 2) - 0.16 * smoothstep(0.62, 0.95, f)
    seam = np.exp(-(f / 0.05) ** 2) + np.exp(-((1 - f) / 0.07) ** 2)
    q = np.stack((xx.ravel() / (0.35 * plate.ppm) + band.ravel() * 7.3, yy.ravel() / (0.006 * plate.ppm)), axis=1)
    grain = fbm2(q, 4, seed).reshape(h, w)
    streak = smoothstep(0.52, 0.7, grain)
    light = smoothstep(0.38, 0.22, grain)
    tone = fbm2(np.stack((xx.ravel() / (0.9 * plate.ppm) + band.ravel() * 3.1, band.ravel()), axis=1), 3, seed + 1).reshape(h, w)
    base = srgb(186, 100, 52) * (0.85 + 0.3 * tone)[..., None]
    img = base * shade[..., None]
    img = over(img, srgb(226, 146, 90), light * 0.35 * shade)
    img = over(img, srgb(104, 48, 24), streak * 0.35)
    img = over(img, srgb(40, 16, 8), np.clip(seam, 0, 1) * 0.95)
    knots = smoothstep(0.93, 0.97, noise2(np.stack((xx.ravel() / (0.05 * plate.ppm), yy.ravel() / (0.025 * plate.ppm)), axis=1), seed + 2)).reshape(h, w)
    return over(img, srgb(70, 32, 16), knots * 0.8)


def render_type(plate, work_dir, name, glyphs, words, word_y, word_cap, shear, phone=None):
    font = marker_felt(work_dir)
    FONT_FILES["marker"] = str(font)
    canvas = PrintCanvas(f"spice_{name}", plate.w, plate.h)
    for glyph, fx, fy, cap, lower, group, rotation in glyphs:
        cap_px = cap * plate.ph * TITLE_SCALE
        size = cap_px / (XHEIGHT_RATIO if lower else CAP_RATIO)
        colour = (1, 0, 0) if group == "red" else (0, 1, 0)
        stretch = 1.55 if glyph == "I" else TITLE_STRETCH
        obj = canvas.text(glyph, plate.X(fx), plate.Y(fy), size, colour, "marker", align="CENTER", scale_x=stretch)
        obj.rotation_euler.z = radians(-rotation)
    for word, fx in words:
        obj = canvas.text(word, plate.X(fx), plate.Y(word_y), word_cap * plate.ph / CAP_RATIO, (0, 0, 1), "marker", align="CENTER")
        obj.data.shear = shear
    if phone:
        text, fx, fy, cap = phone
        obj = canvas.text(text, plate.X(fx), plate.Y(fy), cap * plate.ph / CAP_RATIO, (1, 1, 0), "marker", align="CENTER")
        obj.data.shear = shear
    art = canvas.render(Path(work_dir) / f"{name}-type.png")[::-1]
    a = art[..., 3]
    weight = TITLE_WEIGHT * plate.ph
    red = dilate(np.clip(art[..., 0] - art[..., 1], 0, 1) * a, weight)
    green = dilate(np.clip(art[..., 1] - art[..., 0], 0, 1) * a, weight)
    food = art[..., 2] * a
    phone_cov = np.minimum(art[..., 0], art[..., 1]) * a
    return red, green, food, phone_cov


def chilli(plate):
    Y = plate.Y

    def X(fx):
        return plate.X(fx + CHILLI_SHIFT)

    body = bezier([(X(0.293), Y(0.17)), (X(0.262), Y(0.36)), (X(0.300), Y(0.58)), (X(0.297), Y(0.79))], 90)
    t = np.linspace(0, 1, 90, dtype=F)
    widths = plate.ph * 0.085 * np.sqrt(np.clip(t / 0.1, 0, 1)) * (1 - t) ** 0.85 + 1.0
    cov, across, along = tube_shape((plate.h, plate.w), body, widths)
    stem_pts = bezier([(X(0.292), Y(0.19)), (X(0.296), Y(0.10)), (X(0.312), Y(0.05))], 30)
    stem, _, _ = tube_shape((plate.h, plate.w), stem_pts, np.linspace(plate.ph * 0.014, plate.ph * 0.008, 30))
    calyx_pts = bezier([(X(0.280), Y(0.20)), (X(0.293), Y(0.165)), (X(0.306), Y(0.20))], 20)
    calyx, _, _ = tube_shape((plate.h, plate.w), calyx_pts, np.full(20, plate.ph * 0.02, F))
    return cov, across, along, np.clip(stem + calyx, 0, 1)


def flame(plate):
    Y = plate.Y

    def X(fx):
        return plate.X(fx + FLAME_SHIFT)

    shapes = []
    for colour, pts, width in (
        (srgb(40, 140, 50), [(X(0.818), Y(0.27)), (X(0.804), Y(0.20)), (X(0.812), Y(0.11))], 0.020),
        (srgb(250, 210, 30), [(X(0.826), Y(0.27)), (X(0.840), Y(0.21)), (X(0.836), Y(0.15))], 0.022),
        (srgb(220, 30, 30), [(X(0.822), Y(0.27)), (X(0.816), Y(0.14)), (X(0.823), Y(0.045))], 0.020),
    ):
        centre = bezier(pts, 40)
        t = np.linspace(0, 1, 40, dtype=F)
        profile = np.clip(np.sin(np.clip(t * 0.9 + 0.1, 0, 1) * pi), 0, None)
        widths = plate.ph * width * 1.7 * profile ** 0.6 * (1 - t * 0.7) + 0.8
        cov, across, _ = tube_shape((plate.h, plate.w), centre, widths)
        shapes.append((colour, cov, across))
    return shapes


def star(plate, fx, fy, radius_frac):
    cx, cy = plate.X(fx), plate.Y(fy)
    r = radius_frac * plate.ph
    y0, y1 = int(cy - r - 4), int(cy + r + 4)
    x0, x1 = int(cx - r - 4), int(cx + r + 4)
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(F)
    dist = np.hypot(xx - cx, yy - cy)
    theta = np.arctan2(yy - cy, xx - cx)
    limit = r * (0.42 + 0.58 * np.abs(np.cos(2 * theta)) ** 2.2)
    out = np.zeros((plate.h, plate.w), F)
    out[y0:y1, x0:x1] = smoothstep(1.0, -1.0, dist - limit)
    return out


def log_ends(plate, rng):
    """Sawn log-end cut-outs: rings, cracks, bark and a white serrated contour."""
    rgb = np.zeros((plate.h, plate.w, 3), F)
    cov = np.zeros((plate.h, plate.w), F)
    span_top = plate.y0 - 0.075 * plate.ppm
    span = plate.ph + 0.15 * plate.ppm
    d = span / 5
    radius = d * 0.5
    for column, cx0 in ((0, plate.x0 + 0.03 * plate.ppm), (1, plate.x1 - 0.03 * plate.ppm)):
        for k in range(5):
            cx = cx0 + (0.012 if k % 2 else -0.008) * plate.ppm * (1 if column else -1) + rng.normal(0, 2)
            cy = span_top + (k + 0.5) * d
            x0, x1 = int(max(cx - radius * 1.1, 0)), int(min(cx + radius * 1.1, plate.w))
            y0, y1 = int(max(cy - radius * 1.1, 0)), int(min(cy + radius * 1.1, plate.h))
            yy, xx = np.mgrid[y0:y1, x0:x1].astype(F)
            dx, dy = xx - cx, yy - cy
            r = np.hypot(dx, dy) / radius
            theta = np.arctan2(dy, dx)
            serration = 1.0 + 0.018 * np.abs(((theta * 44 / pi + rng.uniform()) % 2) - 1)
            edge = smoothstep(1.0 * serration + 0.006, 1.0 * serration - 0.006, r)
            ecc = np.hypot(dx - radius * 0.06 * rng.normal(), dy - radius * 0.06 * rng.normal()) / radius
            wobble = noise2(np.stack(((np.cos(theta) * 3 + k * 5.1).ravel(), (np.sin(theta) * 3 + column).ravel()), axis=1), 7 + k).reshape(r.shape)
            q = ecc * (1 + 0.05 * wobble) * 12
            rings = 0.5 + 0.5 * np.cos(q * 2 * pi)
            ring_line = smoothstep(0.85, 0.97, rings)
            wood = over(srgb(240, 150, 64) * (0.86 + 0.14 * rings)[..., None], srgb(186, 88, 30), ring_line)
            wood = over(wood, srgb(252, 196, 120), smoothstep(0.4, 0.1, ecc) * 0.35)
            for _ in range(rng.integers(3, 5)):
                angle = rng.uniform(-pi, pi)
                dtheta = np.abs(np.angle(np.exp(1j * (theta - angle))))
                crack = smoothstep(0.018, 0.004, dtheta * np.maximum(r, 0.05)) * smoothstep(0.82, 0.55, r) * smoothstep(0.02, 0.12, r)
                wood = over(wood, srgb(120, 58, 26), crack * 0.9)
            wood = over(wood, srgb(110, 52, 22), smoothstep(0.035, 0.015, r))
            wood = over(wood, srgb(245, 196, 120), smoothstep(0.80, 0.83, r) * smoothstep(0.87, 0.84, r))
            wood = over(wood, srgb(84, 42, 20), smoothstep(0.85, 0.88, r))
            wood = over(wood, WHITE, smoothstep(0.915, 0.93, r / serration))
            wood = over(wood, INK_BLACK, smoothstep(0.975, 0.99, r / serration))
            region = rgb[y0:y1, x0:x1]
            rgb[y0:y1, x0:x1] = region * (1 - edge[..., None]) + wood * edge[..., None]
            cov[y0:y1, x0:x1] = np.maximum(cov[y0:y1, x0:x1], edge)
    return rgb, cov


def draw_sign(work_dir, name, plate_w, plate_h, rect, food, stars, food_y, phone, age, seed):
    _, _, cell_w, cell_h = rect
    plate = Plate(plate_w, plate_h, cell_w, cell_h)
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:cell_h, 0:cell_w].astype(F)
    plate_mask = smoothstep(plate.x0 - 1, plate.x0 + 1, xx) * smoothstep(plate.x1 + 1, plate.x1 - 1, xx)
    plate_mask *= smoothstep(plate.y0 - 1, plate.y0 + 1, yy) * smoothstep(plate.y1 + 1, plate.y1 - 1, yy)

    img = printed_logs(plate, seed)
    red, green, food_cov, phone_cov = render_type(plate, work_dir, name, TITLE, food, food_y, 0.135, 0.14, phone)
    title = np.maximum(red, green)
    ch_cov, ch_across, ch_along, stem = chilli(plate)
    flames = flame(plate)
    outline_r = 0.03 * plate.ph
    shadow_off = int(0.026 * plate.ph)
    title_shadow = shift(dilate(title, outline_r + 3), shadow_off, shadow_off)
    extras = np.clip(ch_cov + stem, 0, 1)
    img = over(img, INK_BLACK, np.maximum(title_shadow, shift(extras, shadow_off // 2, shadow_off // 2) * 0.8))
    img = over(img, WHITE, dilate(title, outline_r))
    t = np.clip((yy - plate.Y(0.22)) / (plate.Y(0.66) - plate.Y(0.22)), 0, 1)[..., None]
    gloss = smoothstep(0.30, 0.2, np.abs(t[..., 0] - 0.22)) * 0.25
    red_fill = over(srgb(214, 18, 40) * (1 - t) + srgb(128, 4, 20) * t, srgb(255, 96, 104), gloss * 0.8)
    green_fill = over(srgb(28, 150, 58) * (1 - t) + srgb(8, 84, 32) * t, srgb(110, 204, 130), gloss * 0.8)
    img = over(img, red_fill, red)
    img = over(img, green_fill, green)

    shade = np.clip(1.0 - 0.45 * np.abs(ch_across) ** 2, 0.4, 1.0)[..., None]
    chilli_rgb = srgb(214, 22, 32) * shade
    chilli_rgb = over(chilli_rgb, srgb(255, 150, 140), smoothstep(0.25, 0.0, np.abs(ch_across + 0.45)) * smoothstep(0.9, 0.2, ch_along) * 0.8)
    img = over(img, chilli_rgb, ch_cov)
    img = over(img, srgb(40, 120, 40), stem)
    for colour, cov, across in flames:
        img = over(img, colour * np.clip(1.05 - 0.35 * across ** 2, 0.6, 1.1)[..., None], cov)

    food_outline = dilate(food_cov, 0.009 * plate.ph)
    img = over(img, INK_BLACK, shift(food_outline, 3, 3))
    img = over(img, INK_BLACK, food_outline)
    img = over(img, srgb(255, 236, 40), food_cov)
    for fx in stars:
        s = star(plate, fx, food_y - 0.04, 0.03)
        img = over(img, INK_BLACK, dilate(s, 3))
        img = over(img, WHITE, s)
    if phone:
        phone_outline = dilate(phone_cov, 0.01 * plate.ph)
        img = over(img, INK_BLACK, shift(phone_outline, 3, 3))
        img = over(img, INK_BLACK, phone_outline)
        img = over(img, WHITE, phone_cov)

    # Outdoor ageing: UV fade (reds go pink first), dust, streaks from the top edge.
    luma = img @ np.array((0.2126, 0.7152, 0.0722), F)
    img = img * (1 - age * 0.22) + (luma[..., None] * 1.1 + 0.03) * age * 0.22
    img = over(img, srgb(214, 96, 110), red * age * 0.35)
    img = over(img, srgb(90, 170, 120), green * age * 0.25)
    streak_field = fbm2(np.stack((xx.ravel() / (0.03 * plate.ppm), yy.ravel() / (0.5 * plate.ppm)), axis=1), 3, seed + 5).reshape(cell_h, cell_w)
    from_top = smoothstep(plate.y0 + 0.7 * plate.ph, plate.y0, yy)
    dirt = smoothstep(0.6, 0.78, streak_field) * from_top * (0.05 + 0.28 * age)
    dirt += smoothstep(plate.y1 - 0.05 * plate.ph, plate.y1, yy) * (0.3 + 0.3 * age)
    img = over(img, srgb(70, 60, 48), dirt)
    img = over(img, srgb(150, 140, 120), 0.04 + 0.06 * age)

    ends_rgb, ends_cov = log_ends(plate, rng)
    img = over(img, INK_BLACK, shift(ends_cov, 6, 6) * plate_mask * 0.5)
    img = img * (1 - ends_cov[..., None]) + ends_rgb * (1 - age * 0.25) * ends_cov[..., None]
    alpha = np.maximum(plate_mask, ends_cov)

    height = alpha * 0.0015 + ends_cov * 0.002
    seams = (0.5,) if phone else (0.34, 0.67)
    for fx in seams:
        sx = plate.X(fx)
        line = smoothstep(2.5, 0.5, np.abs(xx - sx)) * plate_mask
        img = over(img, srgb(60, 40, 30), line * 0.6)
        height -= line * 0.001
    for fy in (0.05, 0.95):
        for mx in np.arange(0.25, plate_w, 0.55):
            cx, cy = plate.x0 + mx * plate.ppm, plate.Y(fy)
            y0, y1, x0, x1 = int(cy - 9), int(cy + 9), int(cx - 9), int(cx + 9)
            ly, lx = np.mgrid[y0:y1, x0:x1].astype(F)
            screw = smoothstep(6.5, 4.5, np.hypot(lx - cx, ly - cy))
            img[y0:y1, x0:x1] = over(img[y0:y1, x0:x1], srgb(150, 146, 136), screw)
            height[y0:y1, x0:x1] += screw * 0.0008
    rough = 0.45 + 0.35 * dirt + 0.1 * age
    rough = np.where(alpha > 0.5, rough, 0.9).astype(F)
    return np.clip(img, 0, 1), alpha, rough.astype(F), height.astype(F)


def sign_atlas(work_dir):
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    aw, ah = SIGN_SIZE
    rgba = np.zeros((ah, aw, 4), F)
    rgba[..., :3] = srgb_encode(srgb(90, 50, 30))
    rough = np.full((ah, aw), 0.9, F)
    height = np.zeros((ah, aw), F)
    x0, x1 = geo.FRONT_SIGN_PLATE
    z0, z1 = geo.SIGN_FRONT
    y0, y1 = geo.SIDE_SIGN_PLATE
    sz0, sz1 = geo.SIDE_SIGN_Z
    for rect, args in (
        (SIGN_SIDE_RECT, dict(name="side-sign", plate_w=y1 - y0, plate_h=sz1 - sz0, food=SIDE_FOOD, stars=SIDE_STARS,
                              food_y=0.915, phone=("Tel: 0161 202 0888", 0.838, 0.905, 0.14), age=0.12, seed=301)),
        (SIGN_FRONT_RECT, dict(name="front-sign", plate_w=x1 - x0, plate_h=z1 - z0, food=FRONT_FOOD, stars=FRONT_STARS,
                               food_y=0.93, phone=None, age=0.40, seed=302)),
    ):
        img, alpha, r, h = draw_sign(work_dir, rect=rect, **args)
        rx, ry, rw, rh = rect
        rgba[ry:ry + rh, rx:rx + rw, :3] = srgb_encode(img.reshape(-1, 3)).reshape(img.shape)[::-1]
        rgba[ry:ry + rh, rx:rx + rw, 3] = alpha[::-1]
        rough[ry:ry + rh, rx:rx + rw] = r[::-1]
        height[ry:ry + rh, rx:rx + rw] = h[::-1]
    return rgba, rough, height


# ------------------------------------------------------------------ emissive

LED_GLYPHS = {
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "D": ("11100", "10010", "10001", "10001", "10001", "10010", "11100"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
}
# Dead LEDs photographed in both front views: F loses its middle bar, R its leg.
LED_DEAD = {(0, "F"): {(3, 1), (3, 2), (3, 3)}, (0, "R"): {(4, 2), (5, 3), (6, 4)}}


def dots(canvas, centres, colour, radius, glow=2.2):
    h, w = canvas.shape[:2]
    for cx, cy, level in centres:
        r = int(radius * 4)
        y0, y1, x0, x1 = max(int(cy) - r, 0), min(int(cy) + r, h), max(int(cx) - r, 0), min(int(cx) + r, w)
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(F)
        d = np.hypot(xx - cx, yy - cy)
        core = smoothstep(radius, radius * 0.6, d)
        halo = np.exp(-(d / (radius * glow)) ** 2) * 0.35
        canvas[y0:y1, x0:x1] += np.asarray(colour, F) * ((core + halo) * level)[..., None]


def led_sign(w, h):
    img = np.full((h, w, 3), 0.004, F)
    pitch = 14.0
    border = []
    for x in np.arange(10, w - 5, pitch * 0.8):
        border += [(x, 9, 1.0), (x, h - 9, 1.0)]
    for y in np.arange(10, h - 5, pitch * 0.8):
        border += [(9, y, 1.0), (w - 9, y, 1.0)]
    dots(img, border, srgb(40, 90, 255) * 1.4, 3.2)
    lit = []
    for line, (word, top) in enumerate((("FRIED", 52), ("CHICKEN", 182))):
        width = len(word) * 6 * pitch - pitch
        left = (w - width) / 2
        for ci, ch in enumerate(word):
            dead = LED_DEAD.get((line, ch), set()) if ci <= 1 else set()
            for row, bits in enumerate(LED_GLYPHS[ch]):
                for col, bit in enumerate(bits):
                    if bit == "1":
                        level = 0.05 if (row, col) in dead else 1.0
                        lit.append((left + (ci * 6 + col) * pitch, top + row * pitch, level))
    dots(img, lit, srgb(255, 40, 28) * 1.6, 4.6)
    return np.clip(img, 0, 1), 0.3


def fridge_front(w, h, rng):
    yy, xx = np.mgrid[0:h, 0:w].astype(F)
    img = np.broadcast_to(srgb(230, 236, 240), (h, w, 3)).copy() * (0.8 + 0.2 * (1 - yy / h))[..., None]
    palette = [srgb(200, 20, 30), srgb(20, 60, 160), srgb(240, 170, 20), srgb(30, 140, 60), srgb(180, 180, 185), srgb(250, 110, 20)]
    shelf_h = (h - 60) / 5
    for s in range(5):
        top = 30 + s * shelf_h
        x = 22.0
        while x < w - 40:
            cw = rng.uniform(26, 38)
            ch = shelf_h * rng.uniform(0.5, 0.8)
            colour = palette[rng.integers(len(palette))]
            box = (xx > x) & (xx < x + cw) & (yy > top + shelf_h - 12 - ch) & (yy < top + shelf_h - 12)
            img[box] = colour * rng.uniform(0.7, 1.0)
            x += cw + rng.uniform(3, 8)
        img[(yy > top + shelf_h - 12) & (yy < top + shelf_h - 6)] = srgb(150, 150, 150)
    frame = (xx < 14) | (xx > w - 14) | (yy < 16) | (yy > h - 16)
    img[frame] = srgb(40, 40, 42)
    return np.clip(img * 0.9, 0, 1), 0.2


def menu_board(w, h, rng, header):
    yy, xx = np.mgrid[0:h, 0:w].astype(F)
    img = np.broadcast_to(srgb(236, 226, 196), (h, w, 3)).copy()
    img[yy < h * 0.2] = header
    for _ in range(3):
        cx, cy = rng.uniform(0.15, 0.85) * w, rng.uniform(0.35, 0.55) * h
        blob = ((xx - cx) / (w * 0.12)) ** 2 + ((yy - cy) / (h * 0.1)) ** 2 < 1
        img[blob] = [srgb(170, 100, 40), srgb(220, 170, 60), srgb(120, 60, 30)][rng.integers(3)]
    for row in range(4):
        y = h * (0.7 + row * 0.07)
        for col in range(2):
            x0 = w * (0.06 + col * 0.5)
            length = w * rng.uniform(0.25, 0.38)
            img[(yy > y) & (yy < y + 4) & (xx > x0) & (xx < x0 + length)] = srgb(60, 40, 30)
    img[(xx < 6) | (xx > w - 6) | (yy < 6) | (yy > h - 6)] = srgb(30, 30, 30)
    return img, 0.35


def emissive_atlas(work_dir):
    rng = np.random.default_rng(4471)
    aw, ah = EMISSIVE_SIZE
    atlas = np.zeros((ah, aw, 3), F)
    rough = np.full((ah, aw), 0.5, F)

    def place(cell, img, r):
        x, y, w, h = EMISSIVE_CELLS[cell]
        atlas[y:y + h, x:x + w] = srgb_encode(img.reshape(-1, 3)).reshape(img.shape)[::-1]
        rough[y:y + h, x:x + w] = r

    for cell in EMISSIVE_CELLS:
        _, _, w, h = EMISSIVE_CELLS[cell]
        if cell == "led":
            place(cell, *led_sign(w, h))
        elif cell == "fridge":
            place(cell, *fridge_front(w, h, rng))
        elif cell.startswith("menu"):
            header = (srgb(190, 24, 24), srgb(230, 170, 20), srgb(190, 24, 24))[int(cell[-1]) - 1]
            place(cell, *menu_board(w, h, rng, header))
        elif cell == "ceiling":
            yy, xx = np.mgrid[0:h, 0:w].astype(F)
            img = np.broadcast_to(srgb(246, 244, 236), (h, w, 3)).copy()
            img[(xx < 8) | (xx > w - 8) | (yy < 8) | (yy > h - 8)] = srgb(160, 160, 156)
            place(cell, img, 0.4)
        else:
            yy = np.mgrid[0:h, 0:w][0].astype(F)
            falloff = np.exp(-((yy - h / 2) / (h * 0.35)) ** 2)
            img = srgb(255, 238, 206) * (0.4 + 0.6 * falloff)[..., None] * np.ones((h, w, 1), F)
            place(cell, img, 0.3)
    return atlas, rough
