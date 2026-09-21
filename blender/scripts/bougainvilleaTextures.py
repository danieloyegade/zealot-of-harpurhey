"""Procedural surfaces for the bougainvillea fence scene.

Brief: references/architecture/infrastructure:objects/plants/bougainvillea/17_Bougainvillea_Fence_Scene_Assets.txt

Every function returns bottom-up float grids (row 0 is v = 0) in display
(sRGB) values for colour and linear values for ORM/height, ready for
surfaceWeathering.save_rgba.  Nothing here touches bpy.

No lighting is painted in.  The reference photograph is overexposed and full
of leaf shadow; the brief forbids baking either, so these are albedo,
roughness and relief only, and the shadows come from geometry at runtime.
"""

import numpy as np

from surfaceWeathering import F, fbm2, height_to_normal, smoothstep


def rgb(r, g, b):
    return np.array((r, g, b), F) / F(255)


def grid(w, h):
    u = (np.arange(w, dtype=F) + F(0.5)) / F(w)
    v = (np.arange(h, dtype=F) + F(0.5)) / F(h)
    return np.meshgrid(u, v)


def fbm(x, y, octaves=4, seed=0, gain=0.5):
    q = np.column_stack((np.ravel(x), np.ravel(y))).astype(F)
    return fbm2(q, octaves, seed, gain=gain).reshape(np.shape(x))


def mix(a, b, t):
    t = np.clip(np.asarray(t, F), 0.0, 1.0)[..., None]
    return a + (b - a) * t


def orm(ao, rough, metal=0.0):
    return np.dstack((np.broadcast_to(ao, rough.shape), rough, np.broadcast_to(F(metal), rough.shape))).astype(F)


# --------------------------------------------------------------------- timber

TIMBER_COLUMNS = 8
BOARD_WIDTH_M = 0.1
BOARD_LENGTH_M = 2.0


def timber_atlas(w=1024, h=2048, seed=17):
    """Eight board variants side by side, each 100 mm wide and 2 m long.

    Each fence board samples one column, so neighbouring boards never share
    grain, knots or weathering.  v runs up the board, so ground-level
    staining and the bleached upper ends line up with the world.
    """
    rng = np.random.default_rng(seed)
    U, V = grid(w, h)
    col = np.minimum((U * TIMBER_COLUMNS).astype(np.int32), TIMBER_COLUMNS - 1)
    colf = col.astype(F)
    lu = U * TIMBER_COLUMNS - colf
    x = lu * F(BOARD_WIDTH_M)
    z = V * F(BOARD_LENGTH_M)

    weather = rng.uniform(0.35, 0.9, TIMBER_COLUMNS).astype(F)[col]
    warmth = rng.uniform(0.0, 1.0, TIMBER_COLUMNS).astype(F)[col]
    tone = rng.uniform(0.9, 1.07, TIMBER_COLUMNS).astype(F)[col]

    # Knots: grain lines bow around them, a dark core with a few rings.
    xs = x.copy()
    knot = np.zeros_like(x)
    ring = np.zeros_like(x)
    for c in range(TIMBER_COLUMNS):
        for _ in range(int(rng.integers(0, 3))):
            cx, cz, r = rng.uniform(0.018, 0.082), rng.uniform(0.25, 1.85), rng.uniform(0.005, 0.012)
            m = col == c
            ddx, ddz = x - cx, (z - cz) * F(0.4)
            d2 = ddx * ddx + ddz * ddz
            xs -= np.where(m, F(0.9) * ddx * np.exp(-d2 / F(9 * r * r)), 0).astype(F)
            knot = np.maximum(knot, np.where(m, np.exp(-d2 / F(r * r)), 0).astype(F))
            rings = F(0.5) + F(0.5) * np.sin(np.sqrt(d2) / F(r) * F(9))
            ring = np.maximum(ring, np.where(m, rings * np.exp(-d2 / F(5 * r * r)), 0).astype(F))

    streak = fbm(xs * 90 + colf * 13.1, z * 1.4 + colf * 7.3, 5, seed)
    fibre = fbm(xs * 750 + colf * 3.3, z * 7 + colf * 1.7, 3, seed + 5)
    blotch = fbm(x * 9 + colf * 2.1, z * 0.9, 3, seed + 9)

    warm = mix(rgb(128, 102, 78), rgb(116, 96, 80), warmth)
    silver = rgb(156, 150, 139)
    exposure = weather + (blotch - 0.5) * 0.35 + smoothstep(0.9, 1.95, z) * 0.15
    base = mix(np.broadcast_to(warm, (h, w, 3)), silver, exposure)
    base = base * (F(0.84) + F(0.3) * streak)[..., None]
    base = mix(base, rgb(80, 68, 58), smoothstep(0.6, 0.78, fibre) * 0.4)

    base = mix(base, rgb(62, 47, 36), knot * 0.85)
    base = mix(base, rgb(90, 72, 58), ring * 0.35)

    # Rain runs down the face from the top: faint darker drip lines.
    drips = smoothstep(0.58, 0.72, fbm(xs * 260 + colf, z * 0.35, 3, seed + 21)) * smoothstep(0.9, 1.8, z)
    base = mix(base, rgb(96, 88, 80), drips * 0.3)

    # Ground contact: green algae and soil splash up the bottom of every board.
    algae = smoothstep(0.5, 0.02, z) * (F(0.35) + F(0.9) * fbm(x * 60 + colf, z * 12, 4, seed + 31))
    base = mix(base, rgb(70, 86, 50), algae * 0.75)
    splash = smoothstep(0.16, 0.0, z) * fbm(x * 300, z * 300, 3, seed + 33)
    base = mix(base, rgb(52, 45, 37), splash * 0.9)

    # Board edges sit in shadowed joints and hold dirt.
    edge = smoothstep(0.0, 0.07, np.minimum(lu, 1 - lu))
    base = base * (F(0.78) + F(0.22) * edge)[..., None]

    # Surface checking, used sparingly.
    checks = np.zeros_like(x)
    for c in range(TIMBER_COLUMNS):
        for _ in range(int(rng.integers(0, 3))):
            cx, z0 = rng.uniform(0.01, 0.09), rng.uniform(0.1, 1.6)
            z1 = z0 + rng.uniform(0.12, 0.45)
            wiggle = (fbm(z * 40, colf, 2, seed + c) - 0.5) * F(0.002)
            line = np.exp(-(((x + wiggle) - cx) / F(0.00045)) ** 2) * smoothstep(z0, z0 + 0.03, z) * smoothstep(z1, z1 - 0.03, z)
            checks = np.maximum(checks, np.where(col == c, line, 0).astype(F))
    base = mix(base, rgb(48, 40, 34), checks * 0.9)
    base = np.clip(base * tone[..., None], 0, 1)

    height = ((streak - 0.5) * 0.00035 + (fibre - 0.5) * 0.00022 - checks * 0.0011
              + knot * 0.00025 - (1 - edge) * 0.0006).astype(F)
    rough = np.clip(F(0.9) + (fibre - 0.5) * F(0.08) - knot * F(0.06) + checks * F(0.05), 0.78, 0.97).astype(F)
    ao = (F(0.82) + F(0.18) * edge) * (F(1) - checks * F(0.4))
    texel = BOARD_WIDTH_M / (w / TIMBER_COLUMNS)
    return {"base": base.astype(F), "orm": orm(ao, rough), "normal": height_to_normal(height, texel, 1.0)}


# ----------------------------------------------------------------- road sign

SIGN_W, SIGN_H = 0.75, 0.9
SIGN_CORNER = 0.06


def _rounded_rect_distance(X, Y, w, h, r):
    """Signed distance to a centred rounded rectangle (negative inside)."""
    qx = np.abs(X) - (w / 2 - r)
    qy = np.abs(Y) - (h / 2 - r)
    outside = np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2)
    return (outside + np.minimum(np.maximum(qx, qy), 0) - r).astype(F)


def sign_face(w=1024, h=1024, seed=3):
    """Yellow backing board carrying the red No Entry roundel.

    The photo's lime wash is overexposure; these are the sign's own colours
    so it can go that bright under a real sun and still read at night.
    """
    U, V = grid(w, h)
    X, Z = (U - 0.5) * F(SIGN_W), (V - 0.5) * F(SIGN_H)
    px = F(SIGN_W / w)
    d = np.sqrt(X * X + Z * Z)

    base = np.broadcast_to(rgb(206, 214, 64), (h, w, 3)).copy()
    base = mix(base, rgb(236, 236, 228), smoothstep(0.318 + px, 0.318 - px, d))
    base = mix(base, rgb(184, 26, 38), smoothstep(0.300 + px, 0.300 - px, d))
    bar = np.minimum(smoothstep(0.232 + px, 0.232 - px, np.abs(X)), smoothstep(0.06 + px, 0.06 - px, np.abs(Z)))
    base = mix(base, rgb(236, 236, 228), bar)

    # Sheeting fades unevenly; grime gathers along the lower edge and the rim.
    fade = fbm(U * 2.5, V * 3, 4, seed)
    base = mix(base, rgb(226, 224, 208), smoothstep(0.5, 0.85, fade) * 0.08)
    edge = -_rounded_rect_distance(X, Z, SIGN_W, SIGN_H, SIGN_CORNER)
    grime = (smoothstep(0.03, 0.0, edge) * 0.5 + smoothstep(0.22, 0.0, Z + SIGN_H / 2) * 0.35)
    grime = grime * (F(0.4) + fbm(U * 30, V * 30, 3, seed + 4))
    streaks = smoothstep(0.62, 0.78, fbm(U * 90, V * 3, 3, seed + 7)) * smoothstep(0.1, -0.4, Z) * 0.3
    specks = smoothstep(0.83, 0.9, fbm(U * 300, V * 300, 2, seed + 9)) * 0.6
    dirt = np.clip(grime + streaks + specks, 0, 1)
    base = mix(base, rgb(88, 84, 62), dirt * 0.55)

    rough = np.clip(F(0.3) + dirt * F(0.35) + (fade - 0.5) * F(0.1), 0.22, 0.8).astype(F)
    return {"base": np.clip(base, 0, 1).astype(F), "orm": orm(F(1), rough)}


# ---------------------------------------------------------------------- pole

POLE_HEIGHT_M = 3.3
FRONT_U = 0.75  # the -Y (street-facing) side of a cylinder unwrapped from +X anticlockwise


def pole_paint(w=256, h=2048, seed=11):
    """Grey municipal paint for the column and its base, unwrapped around the
    shaft (u) and up it (v = z / 3.3 m).  Carries the small yellow asset tag
    and the torn remains of a taped notice seen in the photograph."""
    U, V = grid(w, h)
    z = V * F(POLE_HEIGHT_M)
    base = np.broadcast_to(rgb(124, 129, 127), (h, w, 3)).copy()
    mottle = fbm(U * 8, z * 4, 4, seed)
    base = base * (F(0.9) + F(0.2) * mottle)[..., None]
    rain = smoothstep(0.6, 0.78, fbm(U * 45, z * 0.8, 3, seed + 3)) * 0.3
    base = mix(base, rgb(92, 94, 90), rain)
    splash = smoothstep(0.45, 0.0, z) * (F(0.4) + F(0.8) * fbm(U * 60, z * 40, 3, seed + 5))
    base = mix(base, rgb(74, 68, 58), splash * 0.7)
    chips = smoothstep(0.86, 0.92, fbm(U * 120, z * 70, 2, seed + 8)) * smoothstep(1.4, 0.2, z)
    base = mix(base, rgb(170, 172, 168), chips * 0.8)

    def patch(u0, z0, du, dz):
        return (np.abs(U - u0) < du / 2) & (np.abs(z - z0) < dz / 2)

    # Asset tag: yellow, with a dark stencilled number block.
    tag = patch(FRONT_U, 1.62, 0.12, 0.05)
    base[tag] = rgb(222, 190, 44)
    base[patch(FRONT_U, 1.625, 0.05, 0.018)] = rgb(40, 38, 30)
    # Torn paper and tape: ragged edge from thresholded noise.
    torn = fbm(U * 30, z * 60, 3, seed + 12)
    paper = (np.abs(U - FRONT_U) < 0.17) & (np.abs(z - 1.33) < 0.075 + (torn - 0.5) * 0.05)
    base[paper] = (rgb(196, 196, 186) * (F(0.85) + F(0.3) * torn[paper])[:, None])
    tape = paper & (np.abs(z - 1.39) < 0.012)
    base[tape] = rgb(170, 166, 150)

    rough = np.clip(F(0.62) + splash * F(0.25) + chips * F(-0.15) + (mottle - 0.5) * F(0.1), 0.35, 0.92).astype(F)
    rough[paper] = 0.88
    metal = np.where(chips > 0.5, F(0.6), F(0.0)).astype(F)
    return {"base": np.clip(base, 0, 1).astype(F), "orm": np.dstack((np.ones_like(rough), rough, metal)).astype(F)}


# ------------------------------------------------------------- flower bracts

BRACT_TONES = (
    rgb(246, 156, 190),  # sunlit pale pink
    rgb(232, 74, 132),   # saturated mid pink
    rgb(198, 30, 104),   # deep magenta
    rgb(160, 20, 66),    # shadowed crimson
)
LEAF_TONES = (
    rgb(122, 160, 64),
    rgb(78, 124, 48),
    rgb(50, 94, 40),
    rgb(36, 70, 38),
)


def tile_uv(index, u, v):
    """Map a (0..1, 0..1) coordinate into tile `index` of a 2 x 2 atlas."""
    tu, tv = index % 2, index // 2
    pad = 0.02
    return ((tu + pad + u * (1 - 2 * pad)) / 2, (tv + pad + v * (1 - 2 * pad)) / 2)


def _atlas(size, tones, painter, seed):
    half = size // 2
    out = np.zeros((size, size, 3), F)
    for index, tone in enumerate(tones):
        U, V = grid(half, half)
        tu, tv = index % 2, index // 2
        out[tv * half:(tv + 1) * half, tu * half:(tu + 1) * half] = painter(U, V, tone, seed + index * 13)
    return np.clip(out, 0, 1)


def _bract(U, V, tone, seed):
    """A papery bract: pale at its base, veined, darker toward the rim."""
    across = np.abs(U - 0.5) * 2
    colour = mix(np.broadcast_to(tone, U.shape + (3,)), np.minimum(tone * F(1.25) + F(0.12), 1), smoothstep(0.3, 0.0, V) * 0.7)
    colour = mix(colour, rgb(236, 226, 186), smoothstep(0.1, 0.0, V) * 0.6)
    angle = np.arctan2(U - 0.5, V + 0.05)
    veins = (F(0.5) + F(0.5) * np.cos(angle * F(38))) * smoothstep(0.05, 0.4, V)
    colour = colour * (F(1) - veins * F(0.09))[..., None]
    colour = colour * (F(1) - smoothstep(0.55, 1.0, across) * F(0.18))[..., None]
    colour = colour * (F(0.93) + F(0.14) * fbm(U * 14, V * 14, 3, seed))[..., None]
    return colour


def _leaf(U, V, tone, seed):
    """Leaf blade with a paler midrib and lateral veins."""
    across = np.abs(U - 0.5) * 2
    colour = np.broadcast_to(tone, U.shape + (3,)).copy()
    midrib = smoothstep(0.05, 0.0, across)
    lateral = (F(0.5) + F(0.5) * np.cos((V * F(9) - across * F(3.2)) * F(2 * np.pi))) * smoothstep(0.05, 0.2, across)
    colour = mix(colour, np.minimum(tone * F(1.35) + F(0.06), 1), midrib * 0.8)
    colour = mix(colour, np.minimum(tone * F(1.15), 1), lateral * 0.25)
    colour = colour * (F(1) - smoothstep(0.7, 1.0, across) * F(0.15))[..., None]
    colour = colour * (F(0.92) + F(0.16) * fbm(U * 10, V * 10, 3, seed))[..., None]
    return colour


def bract_silhouette(U, V):
    """Rounded, broad-shouldered bract outline in card space (v along, u across)."""
    half = F(0.47) * np.power(np.sin(np.pi * np.clip(V, 0, 1)), F(0.7)) * (F(1) - F(0.15) * V)
    return (np.abs(U - 0.5) < half) & (V > 0.01) & (V < 0.99)


def bract_atlas(size=512, seed=41):
    """Alpha-cut bracts: the card geometry is a coarse envelope and the
    rounded outline comes from alpha.  Roughness is a material constant."""
    base = _atlas(size, BRACT_TONES, _bract, seed)
    half = size // 2
    U, V = grid(half, half)
    mask = bract_silhouette(U, V).astype(F)
    alpha = np.tile(mask, (2, 2))
    for index, tone in enumerate(BRACT_TONES):
        tu, tv = index % 2, index // 2
        tile = base[tv * half:(tv + 1) * half, tu * half:(tu + 1) * half]
        tile[mask == 0] = tile[mask > 0].mean(axis=0)
    return {"base": np.dstack((base, alpha)).astype(F)}


def leaf_atlas(size=512, seed=51):
    return {"base": _atlas(size, LEAF_TONES, _leaf, seed)}


# ------------------------------------------------------------- tree foliage

TREE_TONES = (
    rgb(90, 124, 50),   # sun-caught outer leaves
    rgb(54, 92, 38),
    rgb(32, 62, 28),
    rgb(16, 36, 18),    # deep interior, near black under the canopy
)


def _stamp_segment(rgba, a, b, width, colour):
    h, w = rgba.shape[:2]
    lo = np.floor(np.minimum(a, b) - width - 1).astype(int)
    hi = np.ceil(np.maximum(a, b) + width + 1).astype(int)
    x0, y0 = max(lo[0], 0), max(lo[1], 0)
    x1, y1 = min(hi[0], w), min(hi[1], h)
    if x1 <= x0 or y1 <= y0:
        return
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(F)
    ab = b - a
    t = np.clip(((xs - a[0]) * ab[0] + (ys - a[1]) * ab[1]) / max(float(ab @ ab), 1e-6), 0, 1)
    d = np.hypot(xs - (a[0] + t * ab[0]), ys - (a[1] + t * ab[1]))
    m = d < width
    region = rgba[y0:y1, x0:x1]
    region[m, :3] = colour
    region[m, 3] = 1


def _stamp_leaf(rgba, base, angle, length, width, colour, rng):
    h, w = rgba.shape[:2]
    reach = length + 2
    x0, y0 = int(max(base[0] - reach, 0)), int(max(base[1] - reach, 0))
    x1, y1 = int(min(base[0] + reach, w)), int(min(base[1] + reach, h))
    if x1 <= x0 or y1 <= y0:
        return
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(F)
    dx, dy = xs - base[0], ys - base[1]
    ca, sa = np.cos(angle), np.sin(angle)
    s = (dx * ca + dy * sa) / length
    t = (-dx * sa + dy * ca) / length
    profile = width * np.power(np.clip(np.sin(np.pi * np.clip(s, 0, 1)), 0, 1), 0.75) * (1 - 0.35 * s)
    m = (s > 0) & (s < 1) & (np.abs(t) < profile)
    if not m.any():
        return
    side = np.where(t > 0, F(1.08), F(0.9))
    shade = side * (F(0.8) + F(0.3) * np.clip(s, 0, 1))
    midrib = np.abs(t) < 0.035 * width / 0.4
    col = colour[None, None, :] * shade[..., None]
    col = np.where(midrib[..., None], np.minimum(colour * F(1.3), 1), col)
    region = rgba[y0:y1, x0:x1]
    region[m, :3] = np.clip(col[m], 0, 1)
    region[m, 3] = 1


def tree_sprig_atlas(size=1024, seed=61):
    """Four alpha-cut foliage sprigs, one per tone, for the background canopy.

    Each is a twig carrying some fifty leaves.  Transparent texels carry the
    tile's mean leaf colour so mipmaps do not bleed dark halos.
    """
    rng = np.random.default_rng(seed)
    half = size // 2
    out = np.zeros((size, size, 4), F)
    for index, tone in enumerate(TREE_TONES):
        tile = np.zeros((half, half, 4), F)
        stem = rgb(58, 48, 38) * (F(0.5) + F(0.25) * index)
        start = np.array((half * 0.5, half * 0.03), F)
        end = np.array((half * rng.uniform(0.35, 0.65), half * 0.96), F)
        twigs = []
        for k in range(12):
            t = 0.1 + 0.85 * k / 11
            p = start + (end - start) * t
            side = -1 if k % 2 else 1
            tip = p + np.array((side * half * rng.uniform(0.22, 0.44), half * rng.uniform(0.04, 0.2)), F)
            twigs.append((p, tip))
        _stamp_segment(tile, start, end, 2.6, stem)
        for p, tip in twigs:
            _stamp_segment(tile, p, tip, 1.3, stem)
        leaves = []
        for p, tip in twigs + [(start + (end - start) * 0.6, end)]:
            for k in range(11):
                t = rng.uniform(0.1, 1.0)
                q = p + (tip - p) * t
                direction = np.arctan2(*(tip - p)[::-1])
                leaves.append((q, direction + rng.choice((-1, 1)) * rng.uniform(0.4, 1.1)))
        rng.shuffle(leaves)
        for q, angle in leaves:
            c = tone * F(rng.uniform(0.75, 1.2))
            _stamp_leaf(tile, q, angle, half * rng.uniform(0.07, 0.105), rng.uniform(0.32, 0.44), c, rng)
        filled = tile[..., 3] > 0
        tile[~filled, :3] = tile[filled, :3].mean(axis=0)
        tu, tv = index % 2, index // 2
        out[tv * half:(tv + 1) * half, tu * half:(tu + 1) * half] = tile
    return {"base": out}


def bark(w=256, h=512, seed=71):
    """Dark, fissured bark; v runs up the stem, one tile per metre."""
    U, V = grid(w, h)
    ridge = fbm(U * 14, V * 3, 5, seed)
    fissure = smoothstep(0.42, 0.3, ridge)
    base = mix(np.broadcast_to(rgb(80, 72, 62), (h, w, 3)), rgb(34, 30, 27), fissure)
    lichen = smoothstep(0.62, 0.75, fbm(U * 6, V * 6, 4, seed + 3))
    base = mix(base, rgb(112, 120, 92), lichen * 0.5)
    height = ((ridge - 0.5) * 0.004).astype(F)
    rough = np.full(ridge.shape, 0.92, F)
    return {"base": base.astype(F), "orm": orm(F(1) - fissure * F(0.3), rough),
            "normal": height_to_normal(height, 0.25 / w, 1.0)}


# -------------------------------------------------------------------- ground

def ground_strip(bands, length_m, depth_m, w=2048, h=512, seed=81):
    """Road, kerb, tarmac pavement and the dark soil/moss margin at the fence.

    `bands` gives the profile distance (metres from the road edge) where each
    surface ends: (road, kerb, pavement); soil runs from there to depth_m.
    v is profile distance / depth_m, u is x / length_m.
    """
    U, V = grid(w, h)
    x, s = U * F(length_m), V * F(depth_m)
    road_end, kerb_end, pave_end = bands
    road = s < road_end
    kerb = (s >= road_end) & (s < kerb_end)
    soil = s >= pave_end

    agg = fbm(x * 400, s * 400, 2, seed)
    agg2 = fbm(x * 900, s * 900, 1, seed + 1)
    tarmac = rgb(66, 66, 63) * (F(0.75) + F(0.5) * agg)[..., None]
    tarmac = mix(tarmac, rgb(128, 124, 116), smoothstep(0.78, 0.9, agg2) * 0.8)
    lichen = smoothstep(0.7, 0.8, fbm(x * 12, s * 12, 3, seed + 2)) * smoothstep(0.6, 0.85, fbm(x * 70, s * 70, 2, seed + 3))
    base = mix(tarmac, rgb(150, 152, 132), lichen * 0.5)
    base[road] = (rgb(48, 48, 47) * (F(0.75) + F(0.5) * agg[road])[:, None])

    concrete = rgb(122, 120, 113) *(F(0.82) + F(0.3) * fbm(x * 40, s * 40, 4, seed + 4))[..., None]
    concrete = mix(concrete, rgb(96, 94, 88), smoothstep(0.65, 0.8, fbm(x * 6, s * 30, 3, seed + 5)) * 0.6)
    base[kerb] = concrete[kerb]

    moss_n = fbm(x * 8, s * 8, 4, seed + 6)
    earth = mix(rgb(44, 36, 28) * (F(0.7) + F(0.6) * agg)[..., None], rgb(58, 76, 36), smoothstep(0.45, 0.7, moss_n))
    margin = smoothstep(pave_end - 0.06, pave_end + 0.08, s + (fbm(x * 10, s, 2, seed + 7) - 0.5) * 0.12)
    base = mix(base, earth, margin)
    base = mix(base, rgb(30, 27, 22), smoothstep(depth_m - 0.1, depth_m, s) * 0.5)

    height = (agg * 0.0015 + agg2 * 0.0008 + margin * fbm(x * 30, s * 30, 3, seed + 8) * 0.004).astype(F)
    rough = np.where(kerb, F(0.84), F(0.92)).astype(F) + margin * F(0.04)
    rough = np.clip(rough - lichen * F(0.04), 0.7, 0.98).astype(F)
    ao = np.where(soil, F(0.85), F(1)).astype(F)
    return {"base": np.clip(base, 0, 1).astype(F), "orm": orm(ao, rough),
            "normal": height_to_normal(height, length_m / w, 1.0)}
