"""Timber, paint and wear authoring for the worn pallets.

Operates on surfaceWeathering.Texels baked from palletGeometry parts.  Every
texel is mapped back into its own board's local frame, so grain runs along each
board, growth rings wrap round its end grain, and no pattern crosses from one
piece of timber into the next.  Wear is then placed from causes: stacked loads
bearing over the blocks, forks along the lower edges, knocks at corners, sun and
rain on the deck, ground contact underneath, iron staining round nails.

Colours are sRGB values read from the pallet reference photographs, decoded to
linear albedo.
"""

import numpy as np

from surfaceWeathering import F, Layers, fbm2, fbm3, micro_scratches, noise2, noise3, smoothstep, srgb_decode


def c255(r, g, b):
    return srgb_decode(np.array((r, g, b), F) / 255.0)


EARLY = c255(186, 158, 118)
LATE = c255(150, 118, 82)
KNOT = c255(96, 64, 40)
GREY_EARLY = c255(138, 132, 120)
GREY_LATE = c255(98, 92, 82)
FRESH = c255(206, 184, 146)
EXPOSED = c255(182, 164, 136)
DIRT = c255(50, 44, 36)
MUD = c255(92, 80, 64)
STAIN = c255(108, 86, 60)
IRON = c255(46, 44, 46)
RUST = c255(118, 64, 32)
ALGAE = c255(92, 106, 70)
MOULD = c255(28, 28, 28)
STEEL = c255(118, 118, 120)
PAINT_DEEP = c255(18, 80, 162)
PAINT_FADED = c255(60, 114, 168)
PAINT_CHALK = c255(112, 142, 170)


def lerp3(a, b, t):
    t = np.clip(np.asarray(t, F), 0, 1)
    return a * (1 - t)[:, None] + b * t[:, None] if np.ndim(t) else a * (1 - t) + b * t


def full(color, like):
    return np.broadcast_to(np.asarray(color, F), like.shape)


# ------------------------------------------------------------------ frames

class Frames:
    """Each texel expressed in the local frame of the part it belongs to."""

    def __init__(self, tex, parts):
        n = max(tex.names) + 1
        R = np.zeros((n, 3, 3), F)
        origin = np.zeros((n, 3), F)
        size = np.zeros((n, 3), F)
        kinds = np.full(n, "", object)
        for oid, name in tex.names.items():
            meta = parts[name]
            matrix = np.array(meta["matrix"], F)
            R[oid], origin[oid], size[oid], kinds[oid] = matrix[:3, :3], matrix[:3, 3], meta["size"], meta["kind"]
        Rt = R[tex.ids]
        self.local = np.einsum("mij,mi->mj", Rt, tex.P - origin[tex.ids])
        self.nl = np.einsum("mij,mi->mj", Rt, tex.N)
        self.axis = Rt[:, :, 0]
        self.size = size[tex.ids]
        texel_kinds = kinds[tex.ids]
        self.kind = {k: texel_kinds == k for k in ("top", "cross", "bottom", "block", "nails")}
        self.wood = ~self.kind["nails"]

        half = self.size / 2
        da, db, dc = (np.clip(half[:, i] - np.abs(self.local[:, i]), 0, None) for i in range(3))
        dominant = np.argmax(np.abs(self.nl), axis=1)
        self.end_face = (dominant == 0) & self.wood
        self.edge_dist = np.where(dominant == 2, np.minimum(db, da), np.where(dominant == 1, np.minimum(dc, da), np.minimum(db, dc)))
        self.da = da
        # Blocks are short, so "near an end" covers most of them; knock them less.
        self.corner = (np.exp(-da / 0.035) * np.exp(-np.minimum(db, dc) / 0.01) * self.wood
                       * np.where(self.kind["block"], 0.45, 1.0)).astype(F)


# ------------------------------------------------------------------ timber

def timber(tex, fr, parts):
    """Growth rings, knots, fibre, pores and band-saw marks, per board."""
    M = tex.M
    out = {k: np.zeros(M, F) for k in ("late", "knot", "pores", "saw")}
    for k in ("fibre", "mottle", "streak", "fade", "rub"):
        out[k] = np.full(M, 0.5, F)
    out["tone"] = np.ones((M, 3), F)
    out["weather"] = np.ones(M, F)
    for oid, name in tex.names.items():
        meta = parts[name]
        if meta["kind"] == "nails":
            continue
        sel = np.flatnonzero(tex.ids == oid)
        rs = np.random.default_rng(meta["seed"])
        s = int(meta["seed"]) % 9973
        a, b, c = fr.local[sel].T
        half_l, half_w, _ = np.asarray(meta["size"]) / 2

        # Pith runs well outside the plank and nearly parallel to it: long,
        # quiet cathedral figure on the faces, shallow arcs on the end grain.
        pb, pc = rs.uniform(-0.8, 0.8) * half_w, rs.choice((-1, 1)) * rs.uniform(0.08, 0.35)
        sb, sc = rs.normal(0, 0.012, 2)
        rho = rs.uniform(110, 190)
        warp = (fbm3(np.stack((a * 0.8, b * 6, c * 6), axis=1) + s, 3, s) - 0.5) * 0.004
        phase = (np.hypot(b - (pb + sb * a), c - (pc + sc * a)) + warp) * rho
        knot = np.zeros(len(sel), F)
        for _ in range(int(rs.integers(0, 3 if meta["kind"] in ("top", "bottom") else 2))):
            ak, bk, rk = rs.uniform(-half_l + 0.04, half_l - 0.04), rs.uniform(-half_w, half_w), rs.uniform(0.005, 0.013)
            d = np.hypot((a - ak) / 1.6, b - bk) / rk
            phase += 1.2 * np.exp(-(d / 3.0) ** 2)
            knot = np.maximum(knot, smoothstep(1.1, 0.75, d))
        f = phase - np.floor(phase)
        out["late"][sel] = smoothstep(0.5, 0.78, f) * (1 - smoothstep(0.9, 1.0, f))
        out["knot"][sel] = knot
        across = b + c
        out["fibre"][sel] = fbm2(np.stack((a / 0.05, across / 0.0016), axis=1) + s, 2, s + 3)
        out["pores"][sel] = smoothstep(0.72, 0.95, noise2(np.stack((a / 0.007, across / 0.0008), axis=1) + s, s + 5))
        out["mottle"][sel] = fbm2(np.stack((a / 0.25, across / 0.04), axis=1) + s, 3, s + 9)
        out["streak"][sel] = noise2(np.stack((a / 0.08, across / 0.0009), axis=1) + s, s + 11)
        spacing = rs.uniform(0.003, 0.007)
        marks = 0.5 + 0.5 * np.sin(2 * np.pi * (a + 0.002 * np.sin(across * 31 + s)) / spacing)
        patch = smoothstep(0.35, 0.7, noise2(np.stack((a / 0.12, across / 0.05), axis=1) + s, s + 7))
        out["saw"][sel] = marks * patch * rs.uniform(0.3, 1.0)
        warm = rs.normal(0, 0.035)
        out["tone"][sel] = rs.uniform(0.84, 1.08) * np.array((1 + warm, 1, 1 - warm), F)
        out["weather"][sel] = 0.3 if meta.get("replacement") else rs.uniform(0.55, 1.0)
        out["fade"][sel] = rs.uniform(0, 1)
        out["rub"][sel] = rs.uniform(0.2, 0.9)
    return out


def timber_albedo(W, fr):
    # Flat-sawn edges show straight, low-contrast grain; the faces carry the figure.
    late = W["late"] * (0.55 + 0.45 * np.abs(fr.nl[:, 2]))
    albedo = lerp3(full(EARLY, W["tone"]), full(LATE, W["tone"]), late) * W["tone"]
    albedo = lerp3(albedo, full(KNOT, albedo), W["knot"] * 0.9)
    shade = (0.92 + 0.16 * W["fibre"]) * (1 - 0.18 * W["pores"]) * (1 - 0.04 * W["saw"]) * (0.9 + 0.2 * W["mottle"])
    return albedo * shade[:, None]


# ------------------------------------------------------------------ causes

def causes(tex, fr, ctx, seed):
    x, y, z = tex.P.T
    up = tex.N[:, 2]
    top_face = up > 0.7
    warp = (fbm2(np.stack((x / 0.05, y / 0.05), axis=1), 3, seed + 1) - 0.5) * 0.05
    dx = np.min([np.abs(x - cx) for cx in ctx["cross_x"]], axis=0) - ctx["cross_w"] / 2
    dy = np.min([np.abs(y - ry) - w / 2 for ry, w in zip(ctx["row_y"], ctx["bottom_widths"])], axis=0)
    deck = top_face & fr.kind["top"] & (z > ctx["top_z"] - 0.012)
    # Pallets stacked on this one bear on the deck directly over its blocks.
    stack = deck * smoothstep(0.035, -0.025, dx + warp) * (0.5 + 0.5 * smoothstep(0.06, -0.01, dy + warp))
    edge = np.maximum(np.exp(-fr.edge_dist / 0.0035), np.clip(tex.convex * 1.5, 0, 1)) * fr.wood

    a = fr.local[:, 0]
    across = fr.local[:, 1] + fr.local[:, 2]
    outward = (tex.N[:, 0] * np.sign(x) + tex.N[:, 1] * np.sign(y)) > 0.5
    fork = (fr.kind["block"] | fr.kind["bottom"] | fr.kind["cross"]) & ~fr.end_face & (z < ctx["top_z"] - 0.02)
    fork = fork * np.where(outward, 1.0, 0.45)
    line = smoothstep(0.93, 0.985, noise2(np.stack((across / 0.0012, a / 0.09), axis=1), seed + 2))
    gouge = line * smoothstep(0.5, 0.78, noise2(np.stack((a / 0.15, across / 0.15), axis=1), seed + 3)) * fork

    scratch = micro_scratches(tex, seed + 4, directions=5, length=0.09) * top_face * fr.wood
    chips = smoothstep(0.7, 0.82, noise3(tex.P / 0.009, seed + 5)) * smoothstep(0.5, 0.72, noise3(tex.P / 0.06, seed + 6))
    dents = smoothstep(0.86, 0.97, noise3(tex.P / 0.012, seed + 7)) * (top_face | (edge > 0.3)) * fr.wood
    low = smoothstep(0.1, 0.0, z) * (0.5 + 0.5 * noise3(tex.P / 0.03, seed + 8))
    damp = np.clip(low + np.exp(-fr.da / 0.03) * 0.6 * fr.wood + (1 - tex.ao) * 0.5, 0, 1)
    expo = smoothstep(-0.2, 0.9, up) * tex.ao ** 0.6
    broad = smoothstep(0.45, 0.8, fbm2(np.stack((x / 0.3, y / 0.1), axis=1), 4, seed + 9))
    dirt = smoothstep(0.35, 0.75, fbm3(tex.P / 0.15, 4, seed + 10))
    return dict(up=up, top_face=top_face, deck=deck, stack=stack, edge=edge, corner=fr.corner, gouge=gouge,
                scratch=scratch, chips=chips, dents=dents, low=low, damp=damp, expo=expo, broad=broad, dirt=dirt, z=z)


# ----------------------------------------------------------------- shared

def relief(W, C, fr, tex, fresh):
    """Height in metres: weathered grain, saw marks, fibres, dents, gouges."""
    h = (W["late"] - 0.5) * 0.0003 * (0.35 + C["expo"])
    h += W["saw"] * 0.00015 * (1 - fresh) + (W["fibre"] - 0.5) * 0.00008 - W["pores"] * 0.00006
    h -= C["dents"] * 0.0005 + C["gouge"] * 0.0003 + C["scratch"] * 0.00008
    h += np.where(fr.end_face, (noise3(tex.P / 0.0015, 91) - 0.5) * 0.0004, 0)
    return h * fr.wood


def nail_marks(L, tex, fr, ctx, rng):
    """Iron-tannin staining, rust halos and hammer dents round each nail; open holes."""
    order = np.argsort(tex.P[:, 0])
    xs = tex.P[order, 0]
    stain = np.zeros(tex.M, F)
    rust = np.zeros(tex.M, F)
    hole = np.zeros(tex.M, F)

    for record in ctx["nails"] + ctx["holes"]:
        center = np.array(record["position"], F)
        normal = np.array(record["normal"], F)
        lo, hi = np.searchsorted(xs, (center[0] - 0.035, center[0] + 0.035))
        idx = order[lo:hi]
        d = tex.P[idx] - center
        keep = (np.abs(d[:, 1]) < 0.035) & (np.abs(d[:, 2]) < 0.035) & fr.wood[idx] & (tex.N[idx] @ normal > 0.5)
        idx, d = idx[keep], d[keep]
        dist = np.linalg.norm(d, axis=1)
        along = np.abs(np.sum(d * fr.axis[idx], axis=1))
        # Tannin staining bleeds along the fibres, not across them.
        aniso = np.hypot(along / 2.4, np.sqrt(np.clip(dist ** 2 - along ** 2, 0, None)))
        r = record["radius"]
        strength = rng.uniform(0.4, 0.9)
        stain[idx] = np.maximum(stain[idx], strength * np.exp(-(aniso / rng.uniform(0.008, 0.016)) ** 2))
        rust[idx] = np.maximum(rust[idx], 0.5 * np.exp(-((dist - r * 1.5) / 0.002) ** 2))
        L.height[idx] -= 0.00035 * np.exp(-((dist - r * 1.15) / 0.0025) ** 2)
        if "state" not in record:
            hole[idx] = np.maximum(hole[idx], smoothstep(r, r * 0.6, dist))
    L.tint(IRON, stain * 0.95)
    L.tint(RUST, rust * 0.45)
    L.tint(MOULD, hole * 0.9)
    L.height -= hole * 0.001
    L.mix_rough(0.95, np.maximum(hole, stain * 0.4))


def nail_heads(L, tex, fr, C, paint=None):
    idx = np.flatnonzero(fr.kind["nails"])
    if not len(idx):
        return
    P = tex.P[idx]
    rust = np.clip(smoothstep(0.45, 0.75, noise3(P / 0.002, 101)) + C["damp"][idx] * 0.4, 0, 1)
    L.albedo[idx] = STEEL * (0.55 + 0.3 * noise3(P / 0.0008, 102))[:, None]
    L.metal[idx] = 0.85
    L.rough[idx] = 0.48
    L.tint(RUST, rust, idx)
    L.metal[idx] *= 1 - rust * 0.85
    L.rough[idx] = L.rough[idx] * (1 - rust) + 0.85 * rust
    if paint is not None:
        p = paint[idx]
        L.tint(PAINT_FADED, p, idx)
        L.metal[idx] *= 1 - p
        L.rough[idx] = L.rough[idx] * (1 - p) + 0.72 * p


def grime(L, tex, fr, C, ctx, rng, rain_washed=0.0):
    wood = fr.wood
    # Handling and yard dirt: patchy everywhere, heavier where rain never rinses.
    handling = (C["dirt"] * 0.3 + (1 - C["expo"]) * 0.12) * (1 - rain_washed * 0.5) * wood
    L.tint(DIRT, handling)
    L.mix_rough(0.92, C["dirt"] * 0.2)
    recess = (1 - tex.ao) ** 1.6 * (1 - rain_washed * C["expo"])
    L.tint(DIRT, recess * 0.75)
    L.mix_rough(0.93, recess * 0.5)
    L.tint(MUD, C["low"] * 0.55)
    underside = (C["up"] < -0.7) & (C["z"] < 0.004)
    L.tint(MUD, underside * (0.45 + 0.35 * noise3(tex.P / 0.05, 111)))
    L.mix_rough(0.95, underside * 0.8)
    speck = smoothstep(0.8, 0.92, noise3(tex.P / 0.0022, 112)) * smoothstep(0.45, 0.7, noise3(tex.P / 0.08, 113))
    L.tint(MOULD, speck * C["damp"] * 0.7 * wood)
    nail_marks(L, tex, fr, ctx, rng)


def water_stains(L, tex, C, seed, strength):
    s = fbm2(tex.P[:, :2] / 0.2, 4, seed)
    face = smoothstep(0.2, 0.8, C["up"])
    inside = smoothstep(0.52, 0.6, s) * face
    tide = np.exp(-((s - 0.56) / 0.008) ** 2) * face
    L.tint(STAIN, (inside * 0.15 + tide * 0.35) * strength)
    L.mix_rough(0.85, inside * 0.3 * strength)


def finish_ao(L, tex):
    L.ao_channel = (0.25 + 0.75 * tex.ao).astype(F)
    return L.finish()


# ------------------------------------------------------------------- brown

def weather_brown(tex, fr, ctx, rng):
    W = timber(tex, fr, ctx["parts"])
    C = causes(tex, fr, ctx, 200)
    L = Layers(tex, (0, 0, 0), 0.9)
    L.albedo = timber_albedo(W, fr)
    L.rough = (0.9 + 0.05 * (W["fibre"] - 0.5) - 0.16 * W["knot"]).astype(F)

    # Years outdoors grey every face a little and silver the exposed deck.
    grey = np.clip(0.22 + C["expo"] * W["weather"] * (0.45 + 0.5 * C["broad"]), 0, 0.9) * fr.wood
    L.tint(lerp3(full(GREY_EARLY, L.albedo), full(GREY_LATE, L.albedo), W["late"]), grey)
    L.mix_rough(0.94, grey * 0.4)

    # End grain wicks water and dirt.
    L.albedo[fr.end_face] *= 0.62
    L.rough[fr.end_face] = 0.96
    soak = np.exp(-fr.da / 0.045) * (0.4 + 0.6 * noise3(tex.P / 0.02, 201)) * fr.wood * ~fr.end_face
    L.tint(STAIN, soak * 0.45)
    water_stains(L, tex, C, 202, 1.0)

    # Recent knocks reveal raw timber under the grey.
    fresh = np.clip(C["corner"] * 0.8 + C["edge"] * 0.3 * smoothstep(0.55, 0.8, noise3(tex.P / 0.015, 203))
                    + C["stack"] * 0.35 * C["broad"] + C["gouge"] * 0.9 + C["chips"] * C["edge"] * 0.6
                    + C["scratch"] * 0.4, 0, 1) * fr.wood
    fresh_colour = lerp3(full(FRESH, L.albedo), full(LATE, L.albedo), W["late"] * 0.5) * W["tone"]
    L.tint(fresh_colour, fresh * 0.7)
    L.mix_rough(0.8, C["stack"] * 0.6)
    L.height = relief(W, C, fr, tex, fresh)

    grime(L, tex, fr, C, ctx, rng)
    nail_heads(L, tex, fr, C)
    return finish_ao(L, tex)


# -------------------------------------------------------------------- blue

def weather_blue(tex, fr, ctx, rng):
    W = timber(tex, fr, ctx["parts"])
    C = causes(tex, fr, ctx, 300)
    wood = timber_albedo(W, fr)
    top = C["top_face"]

    # Timber under the paint: greyed by exposure, with blue soaked into the earlywood.
    exposed = lerp3(wood, full(EXPOSED, wood) * W["tone"], 0.5)
    exposed = lerp3(exposed, full(GREY_EARLY, wood), 0.2 + 0.35 * C["expo"])
    exposed = lerp3(exposed, full(PAINT_FADED * 0.8, wood), 0.28 * (1 - W["late"]))
    exposed[fr.end_face] *= 0.6

    top_boards = fr.kind["top"] & top
    rub = top_boards * C["broad"] * W["rub"]
    ground = (C["up"] < -0.7) & (C["z"] < 0.004)
    # Blocks were painted all over; only board ends take real end-grain wear.
    end_wear = fr.end_face * np.where(fr.kind["block"], 0.12, 0.5)
    wear = (0.95 * C["stack"] + 0.9 * C["corner"] + 0.5 * C["edge"] * smoothstep(0.4, 0.75, noise3(tex.P / 0.012, 301))
            + 0.55 * rub + C["chips"] * (0.25 + 0.7 * C["edge"]) + 0.6 * C["gouge"] + 0.45 * C["scratch"]
            + 0.12 * top_boards + 0.35 * ground + end_wear)
    # On the deck, paint lets go along latewood ridges and raised fibres, leaving
    # blue caught in streaks along the grain; protected faces break up less by grain.
    grain_w = np.where(top, 0.35, 0.12)
    streak_w = np.where(top, 0.35, 0.08)
    t = wear + (W["late"] - 0.5) * grain_w + (W["fibre"] - 0.5) * 0.25 + (W["streak"] - 0.5) * streak_w
    paint = 1 - smoothstep(0.38, 0.62, t)
    thin = smoothstep(0.1, 0.4, t) * paint

    fade = np.clip(C["expo"] * (0.35 + 0.45 * W["fade"]), 0, 1)
    coat = lerp3(full(PAINT_DEEP, wood), full(PAINT_FADED, wood), fade)
    chalk = fade * 0.45 * smoothstep(0.3, 0.8, noise3(tex.P / 0.05, 302))
    coat = lerp3(coat, full(PAINT_CHALK, wood), chalk)
    coat *= ((0.88 + 0.24 * W["fade"]) * (1 - 0.08 * W["late"]) * (1 - 0.05 * W["saw"]))[:, None]
    coat = lerp3(coat, exposed * 0.9, thin * 0.45)

    L = Layers(tex, (0, 0, 0), 0.9)
    L.albedo = lerp3(exposed, coat, paint)
    wood_rough = 0.9 + 0.05 * (W["fibre"] - 0.5)
    paint_rough = 0.72 + 0.12 * fade - 0.1 * thin * C["stack"]
    L.rough = (wood_rough * (1 - paint) + paint_rough * paint).astype(F)
    L.rough[fr.end_face] = np.maximum(L.rough[fr.end_face], 0.9)

    water_stains(L, tex, C, 303, 0.6)
    L.height = relief(W, C, fr, tex, 1 - paint) + paint * 0.00012 * fr.wood
    # Green-grey growth where the pallet stays damp.
    algae = smoothstep(0.62, 0.8, fbm3(tex.P / 0.12, 3, 304)) * C["damp"] * (C["up"] > -0.2) * fr.wood
    L.tint(ALGAE, algae * 0.35)

    grime(L, tex, fr, C, ctx, rng, rain_washed=0.4)
    nail_paint = (1 - smoothstep(0.3, 0.5, C["stack"] + noise3(tex.P / 0.003, 305) * 0.6)) * 0.8
    nail_heads(L, tex, fr, C, nail_paint)
    return finish_ao(L, tex)
