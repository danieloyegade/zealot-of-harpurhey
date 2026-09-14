"""Build, texture, export and validate the reference-led Spice Cabin end unit.

The photographs and brief in references/architecture/buildings/spice-cabin/ are the visual
authority.  Geometry comes from spiceCabinGeometry.py and sign/emissive artwork
from spiceCabinArtwork.py.  This script:

  * gives every material group a unique, density-consistent UV atlas, so brick
    and timber never visibly tile;
  * bakes world position, normal, object id, AO and convexity per atlas
    (surfaceWeathering.bake_buffers) and authors the surfaces in world space:
    per-brick colour, recessed mortar, pores and chipped arrises; loglap grain,
    knots and checks; weathering that follows rain, splash, sun, hands and feet;
  * writes glTF base colour / ORM / normal maps, rebuilds glTF-compatible
    materials and exports the runtime GLB with WebP textures;
  * renders the validation views the brief requires.

Run from the repository root (about 15 minutes; --bake-cache reuses bakes while
geometry and UVs are unchanged):

  /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \\
    --python blender/scripts/createSpiceCabin.py [-- --stage textures|renders] [--bake-cache DIR]
"""

import sys
import time
from math import pi, radians
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import spiceCabinArtwork as artwork  # noqa: E402
import spiceCabinGeometry as geo  # noqa: E402
from surfaceWeathering import (  # noqa: E402
    F,
    Layers,
    Texels,
    _hash,
    bake_buffers,
    build_pbr_material,
    fbm2,
    fbm3,
    fingerprint,
    height_to_normal,
    load_image,
    micro_scratches,
    noise2,
    noise3,
    polyline_coverage,
    save_rgba,
    smoothstep,
    srgb_decode,
    srgb_encode,
    streaks,
    unwrap_atlas,
)

PROJECT_ROOT = SCRIPT_DIR.parents[1]
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "spice-cabin"
ARTWORK_DIR = TEXTURE_DIR / "artwork"
BLEND = PROJECT_ROOT / "blender" / "source" / "spice-cabin.blend"
GLB = PROJECT_ROOT / "public" / "assets" / "models" / "spice-cabin.glb"
RENDER_DIR = PROJECT_ROOT / "renders" / "spice-cabin"
PAVEMENT_DIR = PROJECT_ROOT / "public" / "assets" / "textures" / "pavement"

BAKE_CACHE = None

# key: (bake size, upsample factor, normal size, ORM size, normal strength, UV importance)
ATLASES = {
    "brick": (2048, 2, 2048, 1024, 2.5, {"Brick_Back": 0.3}),
    "paint": (2048, 1, 1024, 1024, 3.0, {"Coping_Back": 0.3, "Sign_Front_Board": 0.35, "Sign_Side_Board": 0.35,
                                         "TubeStandoffPlate": 0.5}),
    "blue": (1024, 2, 1024, 1024, 3.0, {}),
    "timber": (2048, 1, 2048, 1024, 5.0, {"LogBacking": 0.2, "DoorLeaf": 0.35}),
    "metal": (2048, 1, 1024, 1024, 3.0, {"AntiClimb_Front": 0.3, "AntiClimb_Gable": 0.25, "AntiClimb_Hopper": 0.3,
                                         "AntiClimb_Brackets": 0.5, "CounterTop": 0.25, "LEDSign_Case": 0.4}),
    "glass": (1024, 1, None, 256, 1.0, {"Glass_DoorLeaf": 0.5}),
    "interior": (1024, 1, None, 512, 1.0, {}),
}

COURSE = 0.075
BRICK_LEN = 0.225


def srgb(*rgb):
    return srgb_decode(np.array(rgb, F) / 255.0)


def lerp_rows(a, b, t):
    t = np.clip(np.asarray(t, F), 0, 1)
    if t.ndim:
        t = t[:, None]
    return a * (1 - t) + b * t


# ------------------------------------------------------------------- brick

BUFF = np.stack([srgb(182, 152, 108), srgb(196, 172, 130), srgb(162, 128, 90), srgb(150, 134, 108), srgb(126, 94, 66)])
BUFF_CUM = np.array((0.46, 0.68, 0.88, 0.965, 1.0), F)
BROWN = np.stack([srgb(116, 72, 47), srgb(134, 88, 58), srgb(98, 60, 40), srgb(124, 92, 70), srgb(82, 50, 34)])
BROWN_CUM = np.array((0.42, 0.66, 0.86, 0.95, 1.0), F)
MORTAR_BUFF = srgb(152, 144, 128)
MORTAR_BROWN = srgb(124, 114, 102)
RUST = srgb(92, 46, 22)
ALGAE = srgb(44, 58, 30)
GRIME = srgb(38, 34, 28)


def weather_brick(tex, rng, seed=11):
    P, N = tex.P, tex.N
    z = P[:, 2].astype(np.float64)
    s = tex.s.astype(np.float64)
    wall = np.where(np.abs(N[:, 0]) > 0.7, 1, np.where(N[:, 1] > 0.7, 2, 0)).astype(np.int64)
    zeros = np.zeros(tex.M, np.int64)

    course = np.floor(z / COURSE).astype(np.int64)
    v = z - course * COURSE
    shift = (course % 2) * (BRICK_LEN / 2) + (_hash(course, wall, zeros, seed) - 0.5) * 0.012 + wall * 0.37
    sx = s + shift
    ix = np.floor(sx / BRICK_LEN).astype(np.int64)
    u = sx - ix * BRICK_LEN
    h1 = _hash(ix, course, wall, seed + 1)
    h2 = _hash(ix, course, wall, seed + 2)
    h3 = _hash(ix, course, wall, seed + 3)
    head_w = 0.008 + 0.005 * h2
    bed_w = 0.0085 + 0.003 * noise2(np.stack((s / 0.5, course.astype(F)), axis=1), seed + 4)
    d = np.minimum(np.minimum(u, BRICK_LEN - u) - head_w / 2, np.minimum(v, COURSE - v) - bed_w / 2).astype(F)
    face = smoothstep(-0.0006, 0.0010, d)

    brown = (wall > 0) & (course < int(geo.BRICK_CHANGE_Z / COURSE))
    pick_buff = np.searchsorted(BUFF_CUM, h1)
    pick_brown = np.searchsorted(BROWN_CUM, h1)
    col = np.where(brown[:, None], BROWN[np.clip(pick_brown, 0, 4)], BUFF[np.clip(pick_buff, 0, 4)])
    col = col * (0.9 + 0.2 * h3)[:, None]
    # Kiln flashing: soft value drift across a brick and between neighbours.
    mott = fbm2(np.stack((s / 0.06, z / 0.035), axis=1), 3, seed + 5)
    col *= (0.86 + 0.28 * mott)[:, None]
    fine = noise3(P * 820, seed + 6)
    dark_speck = np.where(brown, smoothstep(0.70, 0.80, fine), smoothstep(0.84, 0.91, fine))
    col = lerp_rows(col, col * 0.35, dark_speck * 0.85)
    light_speck = smoothstep(0.86, 0.92, noise3(P * 640, seed + 7))
    col = lerp_rows(col, col * 1.45, light_speck * 0.5)
    # Dragfaced texture on the ground-storey bricks, as in photo 1.
    drag = smoothstep(0.60, 0.80, noise2(np.stack((s / 0.0016, z / 0.02), axis=1), seed + 8)) * brown
    col *= (1 - 0.22 * drag)[:, None]

    mortar = np.where(brown[:, None], MORTAR_BROWN, MORTAR_BUFF)
    mortar = mortar * (0.85 + 0.3 * fbm3(P * 45, 3, seed + 9))[:, None]
    L = Layers(tex, (0.3, 0.3, 0.3), 0.9)
    L.albedo = lerp_rows(mortar, col, face)

    tilt = (u - BRICK_LEN / 2) * (h2 - 0.5) * 0.008 + (v - COURSE / 2) * (h3 - 0.5) * 0.012
    pores = smoothstep(0.78, 0.9, noise3(P * 480, seed + 10))
    arris = 1 - smoothstep(0.0, 0.007, d)
    chips = smoothstep(0.58, 0.7, noise3(P * 120, seed + 11)) * smoothstep(0.014, 0.0, d)
    brick_h = tilt - 0.0011 * pores - 0.0012 * arris - 0.003 * chips - 0.0005 * drag + 0.0004 * mott
    mortar_h = -0.0065 + 0.0012 * fbm3(P * 300, 2, seed + 12)
    L.height = (face * brick_h + (1 - face) * mortar_h).astype(F)
    L.rough = (face * (0.84 + 0.1 * mott) + (1 - face) * 0.95).astype(F)
    L.albedo = lerp_rows(L.albedo, L.albedo * 0.72, chips * 0.6)

    # Rain off the coping: streaks down from the parapet top.
    top_fall = smoothstep(geo.PARAPET_TOP - 1.4, geo.PARAPET_TOP - 0.02, z) ** 1.6
    L.tint(GRIME, streaks(tex, 0.035, 0.9, seed + 20) * top_fall * 0.55)
    L.tint(GRIME, top_fall * 0.12)
    # Rust bleeding from the anti-climb bracket fixings.
    rust = np.zeros(tex.M, F)
    fixings = [(0, x) for x in np.arange(-2.85, geo.RIGHT_X, 0.95)] + [(1, -y) for y in np.arange(-2.60, geo.BACK_Y, 0.95)]
    for wall_id, sb in fixings:
        below = np.clip(4.42 - z, 0, None)
        width = 0.006 + 0.03 * below
        sel = (wall == wall_id) & (z < 4.44) & (z > 3.6)
        rust[sel] = np.maximum(rust[sel], np.exp(-((s[sel] - sb) / width[sel]) ** 2) * smoothstep(3.6, 4.4, z[sel]))
    for y in (-1.55, 0.18, 1.90):
        sel = (wall == 1) & (z < 3.97) & (z > 3.62)
        rust[sel] = np.maximum(rust[sel], 0.6 * np.exp(-((s[sel] + y) / (0.01 + 0.05 * (3.97 - z[sel]))) ** 2) * smoothstep(3.62, 3.96, z[sel]))
    rust *= 0.55 + 0.45 * noise2(np.stack((s / 0.01, z / 0.05), axis=1), seed + 21)
    L.tint(RUST, rust * 0.5)
    # Run-off from the gable sign's bottom edge.
    y0, y1 = geo.SIDE_SIGN_PLATE
    under_sign = (wall == 1) * smoothstep(y0 - 0.1, y0 + 0.2, -s) * smoothstep(y1 + 0.1, y1 - 0.2, -s)
    under_sign = under_sign * smoothstep(1.7, geo.SIDE_SIGN_Z[0], z) * (z < geo.SIDE_SIGN_Z[0])
    L.tint(GRIME, streaks(tex, 0.025, 0.55, seed + 22) * under_sign * 0.5 + under_sign * 0.08)
    # Splash zone, algae and salts at the foot of the walls.
    splash = smoothstep(0.55 + 0.25 * fbm3(P * 1.5, 3, seed + 23), 0.0, z)
    L.tint(GRIME, splash * 0.35)
    algae = splash * smoothstep(0.45, 0.65, fbm3(P * 4.0, 3, seed + 24)) * (wall > 0)
    L.tint(ALGAE, algae * 0.4)
    L.rough = np.clip(L.rough + algae * 0.05, 0, 1)
    salts = smoothstep(0.68, 0.8, fbm3(P * 3.0, 3, seed + 25)) * smoothstep(0.08, 0.3, z) * smoothstep(0.9, 0.45, z) * (wall == 1)
    L.tint(srgb(170, 166, 152), salts * 0.12 * (1 - 0.6 * face) + salts * 0.08)
    # Faded white marker tags on the lower gable near the pier (photo 2).
    tags = np.zeros(tex.M, F)
    for centre_s, centre_z, size in ((2.55, 1.05, 0.34), (1.70, 0.72, 0.22)):
        pts = [(centre_s + size * (np.sin(k * 0.9 + centre_s) * 0.5 + k / 14 - 0.5), centre_z + size * 0.35 * np.sin(k * 1.7 + 1.3 * centre_z))
               for k in range(15)]
        near = (wall == 1) & (np.abs(s - centre_s) < size) & (np.abs(z - centre_z) < size)
        idx = np.flatnonzero(near)
        tags[idx] = polyline_coverage(s[idx].astype(F), z[idx].astype(F), pts, 0.012, tex.texel_m)
    L.tint(srgb(214, 212, 204), tags * (0.3 + 0.35 * face))
    # Atmospheric variation and ambient occlusion.
    L.albedo *= (0.9 + 0.2 * fbm3(P * 0.7, 3, seed + 26))[:, None]
    L.albedo *= (0.6 + 0.4 * tex.ao)[:, None]
    L.ao_channel = 0.5 + 0.5 * tex.ao
    return L.finish()


# ------------------------------------------------------------------- paint

CREAM = srgb(214, 206, 184)
RENDER_GREY = srgb(120, 118, 110)
COPING_GREEN = srgb(58, 104, 78)
BLACK_PAINT = srgb(38, 38, 36)
CONCRETE = srgb(132, 130, 122)
PLASTIC_WHITE = srgb(228, 226, 216)


def weather_paint(tex, rng, seed=31):
    P, N = tex.P, tex.N
    z = P[:, 2]
    up = smoothstep(0.5, 0.8, N[:, 2])
    down = smoothstep(-0.5, -0.8, N[:, 2])
    masks = {k: tex.name_mask(*v) for k, v in {
        "pier": ("CreamPier",), "band": ("CreamBand",), "coping": ("Coping",), "board": ("Boarding", "Sign_Front_Board", "Sign_Side_Board"),
        "plinth": ("Plinth",), "alarm": ("AlarmSounder",), "cctv": ("CCTV",), "tube": ("Tube_Front", "Tube_Side"),
        "standoff": ("TubeStandoff",)}.items()}
    L = Layers(tex, CREAM, 0.86)
    for key, colour, rough in (("coping", COPING_GREEN, 0.58), ("board", BLACK_PAINT, 0.72), ("plinth", CONCRETE, 0.95),
                               ("alarm", PLASTIC_WHITE, 0.42), ("cctv", PLASTIC_WHITE, 0.45), ("tube", srgb(206, 204, 194), 0.5),
                               ("standoff", srgb(210, 208, 200), 0.6)):
        L.albedo[masks[key]] = colour
        L.rough[masks[key]] = rough
    patch = fbm3(P * 2.2, 4, seed)
    L.albedo *= (0.93 + 0.14 * patch)[:, None]

    # General dust on upward faces and grime in recesses.
    L.tint(srgb(88, 80, 66), up * (0.25 + 0.3 * patch))
    # Pier: splash, shoe scuffs, flaking to render, a repaint patch, a crack, tags.
    pier = masks["pier"]
    low = smoothstep(1.1, 0.0, z + 0.25 * fbm3(P * 3, 3, seed + 1)) * pier
    L.tint(srgb(96, 90, 76), low * 0.4)
    scuff = smoothstep(0.62, 0.8, fbm2(np.stack((tex.s / 0.05, z / 0.012), axis=1), 3, seed + 2)) * smoothstep(0.42, 0.25, z) * pier
    L.tint(srgb(30, 30, 30), scuff * 0.25)
    flake = smoothstep(0.64, 0.7, fbm3(P * 6.0, 4, seed + 3)) * (0.35 + 0.65 * smoothstep(1.3, 0.0, z) + 0.8 * tex.convex) * (pier | masks["band"])
    flake = np.clip(flake, 0, 1)
    L.tint(RENDER_GREY, flake * 0.85)
    L.rough = np.clip(L.rough + flake * 0.08, 0, 1)
    L.height -= flake * 0.0008
    repaint = pier * (N[:, 1] < -0.9) * smoothstep(-3.04, -2.98, P[:, 0]) * smoothstep(-2.60, -2.66, P[:, 0])
    repaint = repaint * smoothstep(0.22, 0.30, z) * smoothstep(1.2, 1.1, z + 0.04 * noise2(P[:, (0, 2)] * 30, seed + 4))
    L.tint(srgb(232, 228, 214), repaint * 0.5)
    L.height += repaint * 0.0002
    crack_pts = [(-2.74, 0.12), (-2.73, 0.45), (-2.76, 0.8), (-2.72, 1.2), (-2.74, 1.62)]
    sel = np.flatnonzero(pier & (N[:, 1] < -0.9) & (z < 1.7))
    crack = np.zeros(tex.M, F)
    crack[sel] = polyline_coverage(P[sel, 0], z[sel], crack_pts, 0.0015, tex.texel_m)
    L.tint(srgb(60, 56, 48), crack * 0.8)
    L.height -= crack * 0.001
    sel = np.flatnonzero(pier & (N[:, 1] < -0.9) & (z > 0.9) & (z < 1.5))
    tag = np.zeros(tex.M, F)
    pts = [(-3.0 + 0.03 * k + 0.05 * np.sin(k * 1.3), 1.2 + 0.08 * np.sin(k * 2.1)) for k in range(12)]
    tag[sel] = polyline_coverage(P[sel, 0], z[sel], pts, 0.008, tex.texel_m)
    L.tint(srgb(40, 40, 48), tag * 0.55)
    base_green = smoothstep(0.18, 0.0, z) * (pier | masks["plinth"])
    L.tint(ALGAE, base_green * 0.4)

    # Band: streaks from the top edge, algae on top, dusty soffit, knocked arrises.
    band = masks["band"]
    front = band & (N[:, 1] < -0.9)
    L.tint(GRIME, streaks(tex, 0.03, 0.35, seed + 5) * smoothstep(geo.BAND[0], geo.BAND[1], z) * front * 0.45)
    L.tint(srgb(40, 46, 32), up * band * (0.35 + 0.35 * fbm3(P * 5, 3, seed + 6)))
    L.tint(srgb(110, 104, 92), down * band * 0.3)
    chips = smoothstep(0.62, 0.72, noise3(P * 70, seed + 7)) * smoothstep(0.15, 0.5, tex.convex) * (band | pier | masks["plinth"])
    L.tint(RENDER_GREY, chips * 0.8)
    L.height -= chips * 0.002

    # Coping: sun-chalked top, dirty drip lips, joints every three metres.
    coping = masks["coping"]
    L.tint(srgb(120, 140, 124), up * coping * 0.35)
    L.tint(GRIME, coping * down * 0.5 + coping * smoothstep(-0.2, -0.7, N[:, 2]) * 0.3)
    joint = coping * (np.abs(((tex.s + 1.5) % 3.0) - 1.5) < 0.012)
    L.tint(srgb(20, 24, 20), joint * 0.7)
    L.height -= joint * 0.001

    # Black boarding: vertical board grooves, fade and dust.
    board = masks["board"]
    boarding = tex.name_mask("Boarding")
    groove = boarding * (np.abs(((tex.s + 0.0625) % 0.125) - 0.0625) < 0.004)
    L.height -= groove * 0.002
    L.tint(srgb(18, 18, 18), groove * 0.6)
    L.tint(srgb(78, 78, 74), board * smoothstep(3.0, 3.6, z) * 0.25 * (0.5 + fbm3(P * 3, 3, seed + 8)))
    L.tint(srgb(90, 84, 70), board * up * 0.4)

    # Plinth: grit, gum, chipped nosing.
    plinth = masks["plinth"]
    aggregate = smoothstep(0.7, 0.8, noise3(P * 350, seed + 9)) * plinth
    L.tint(srgb(90, 88, 82), aggregate * 0.6)
    L.tint(srgb(60, 56, 48), plinth * up * 0.45)
    gum = smoothstep(0.93, 0.96, noise3(P * 60, seed + 10)) * plinth * up
    L.tint(srgb(160, 158, 150), gum * 0.8)
    L.height += gum * 0.0015

    # Fittings: yellowed plastic, dirty tops, tube grime.
    for key in ("alarm", "cctv"):
        L.tint(srgb(200, 190, 150), masks[key] * 0.2)
        L.tint(GRIME, masks[key] * up * 0.4)
    alarm_front = masks["alarm"] & (N[:, 1] < -0.9)
    ring = np.abs(np.hypot(P[:, 0] - 2.725, z - 3.08) - 0.05) < 0.004
    L.height += (alarm_front & ring) * 0.0008
    lens_dir = np.array((-0.06, -0.16, -0.06), F)
    lens_dir /= np.linalg.norm(lens_dir)
    lens = masks["cctv"] & (N @ lens_dir > 0.9)
    L.albedo[lens] = srgb(8, 10, 12)
    L.rough[lens] = 0.1
    tube = masks["tube"] | masks["standoff"]
    L.tint(srgb(60, 58, 48), tube * smoothstep(0.1, 0.6, N[:, 2]) * (0.4 + 0.4 * noise3(P * 40, seed + 11)))
    L.tint(srgb(46, 60, 34), tube * smoothstep(0.5, 0.9, N[:, 2]) * smoothstep(0.55, 0.7, fbm3(P * 8, 3, seed + 12)) * 0.5)

    L.albedo *= (0.55 + 0.45 * tex.ao)[:, None]
    L.height += (fbm3(P * 600, 2, seed + 13) - 0.5) * 0.00015
    L.ao_channel = 0.45 + 0.55 * tex.ao
    return L.finish()


# ------------------------------------------------------------------- blue

BLUE = srgb(32, 86, 168)


def weather_blue(tex, rng, seed=51):
    P, N = tex.P, tex.N
    z = P[:, 2]
    L = Layers(tex, BLUE, 0.55)
    up = smoothstep(0.5, 0.8, N[:, 2])
    down = smoothstep(-0.5, -0.8, N[:, 2])
    patch = fbm3(P * 2.5, 4, seed)
    L.tint(srgb(96, 128, 176), up * 0.45 + 0.12 * patch)
    L.mix_rough(0.8, up * 0.6 + 0.2 * patch)
    L.tint(srgb(70, 72, 70), down * 0.35)
    fascia = tex.name_mask("Blue_Fascia")
    posts = tex.name_mask("Blue_Post")
    L.tint(GRIME, streaks(tex, 0.02, 0.3, seed + 1) * smoothstep(geo.HEAD_TOP, geo.FASCIA_TOP, z) * fascia * (N[:, 1] < -0.9) * 0.35)
    # Chips stay broader than a few texels: sub-texel noise aliases into blocky dither.
    chips = smoothstep(0.62, 0.72, fbm3(P * 40, 3, seed + 2)) * smoothstep(0.12, 0.45, tex.convex)
    knocks = posts * smoothstep(0.7, 0.8, fbm3(P * 30, 3, seed + 3)) * smoothstep(1.3, 0.2, z) * 0.6
    chips = np.clip(chips + knocks, 0, 1)
    L.tint(srgb(150, 150, 144), chips * 0.8)
    L.mix_rough(0.9, chips)
    L.height -= chips * 0.0006
    rubbed = posts * smoothstep(0.2, 0.5, z) * smoothstep(1.6, 1.1, z) * smoothstep(0.5, 0.75, fbm3(P * 8, 3, seed + 4))
    L.tint(srgb(110, 140, 186), rubbed * 0.3)
    L.mix_rough(0.75, rubbed)
    base = smoothstep(0.42, 0.0, z + 0.1 * fbm3(P * 4, 3, seed + 5)) * posts
    L.tint(GRIME, base * 0.5)
    grease = tex.name_mask("Blue_Post_02") * smoothstep(0.85, 1.05, z) * smoothstep(1.55, 1.35, z) * (N[:, 0] > 0.5)
    L.tint(srgb(20, 40, 80), grease * 0.3)
    L.mix_rough(0.3, grease * 0.6)
    # Small silver installer plate on the fascia's right end (services crop).
    label = fascia & (N[:, 1] < -0.9) & (P[:, 0] > 2.64) & (P[:, 0] < 2.80) & (z > 2.36) & (z < 2.44)
    L.albedo[label] = srgb(170, 170, 166)
    L.metal[label] = 0.7
    L.rough[label] = 0.45
    L.height[label] += 0.0006
    print_bars = label & (np.abs(((z - 2.37) % 0.016) - 0.008) < 0.002) & (P[:, 0] > 2.66) & (P[:, 0] < 2.78)
    L.albedo[print_bars] = srgb(40, 40, 40)
    L.metal[print_bars] = 0.0
    L.albedo *= (0.55 + 0.45 * tex.ao)[:, None]
    L.ao_channel = 0.45 + 0.55 * tex.ao
    return L.finish()


# ------------------------------------------------------------------- timber

HONEY = srgb(204, 152, 88)
SILVER = srgb(150, 140, 124)


def weather_timber(tex, rng, seed=71):
    P, N = tex.P, tex.N
    z = P[:, 2]
    vertical = tex.name_mask("Mullion", "DoorJamb", "DoorLeaf")
    boards = tex.name_mask("LogBoards")
    along = np.where(vertical, z, tex.s).astype(F)
    across = np.where(vertical, tex.s, tex.t).astype(F)
    pitch = (geo.BOARD_TOP - geo.PLINTH_TOP) / geo.BOARD_COURSES
    course = np.floor((z - geo.PLINTH_TOP) / pitch).astype(np.int64)
    piece = np.where(boards, course * 31 + tex.ids * 7, tex.ids * 131).astype(np.int64)
    zeros = np.zeros(tex.M, np.int64)
    hp = _hash(piece, zeros, zeros, seed)
    hq = _hash(piece, zeros + 1, zeros, seed)

    L = Layers(tex, HONEY, 0.7)
    L.albedo = L.albedo * (0.84 + 0.3 * hp)[:, None] * np.stack((1.0 + 0.06 * (hq - 0.5), np.ones(tex.M, F), 1.0 - 0.12 * (hq - 0.5)), axis=1)
    offset = (hp * 37.0).astype(F)
    g = fbm2(np.stack((along / 0.7 + offset, across / 0.0045), axis=1), 4, seed + 1)
    lines = smoothstep(0.5, 0.72, g)
    rings = 0.5 + 0.5 * np.sin((across + 0.012 * fbm2(np.stack((along / 0.35 + offset, across / 0.02), axis=1), 2, seed + 2)) / 0.0024 * 2 * pi)
    bands = fbm2(np.stack((along / 0.9 + offset, across / 0.03), axis=1), 3, seed + 3)
    L.albedo *= ((1 - 0.3 * lines) * (0.93 + 0.07 * rings) * (0.88 + 0.24 * bands))[:, None]
    L.height += (-0.00035 * lines + 0.0001 * rings).astype(F)

    # Knots on the boards, one cell per 0.45 m.
    cell = np.floor(along / 0.45).astype(np.int64)
    hk = _hash(piece, cell, zeros + 2, seed)
    hk2 = _hash(piece, cell, zeros + 3, seed)
    centre = (cell + 0.2 + 0.6 * hk2) * 0.45
    board_mid = geo.PLINTH_TOP + (course + 0.45) * pitch
    r = np.hypot((along - centre) / 0.02, (z - board_mid) / 0.011)
    knot = boards * (hk < 0.28) * smoothstep(1.0, 0.6, r)
    halo = boards * (hk < 0.28) * smoothstep(2.4, 1.0, r) * (1 - knot)
    L.tint(srgb(92, 52, 26), knot * 0.85)
    L.tint(srgb(150, 96, 52), halo * 0.35)
    L.height += knot * 0.0003
    checks = smoothstep(0.955, 0.985, noise2(np.stack((along / 0.22 + offset, across / 0.0009), axis=1), seed + 4))
    L.tint(srgb(52, 34, 20), checks * 0.7)
    L.height -= checks * 0.0012

    # Weather: sun-silvered upper faces, splash, scuffs by the door, seams.
    exposure = np.clip(N[:, 2], 0, 1) * (0.6 + 0.4 * fbm3(P * 3, 3, seed + 5))
    sills = tex.name_mask("Sill")
    L.tint(SILVER, exposure * (0.16 + 0.3 * sills))
    L.tint(SILVER, 0.03 + 0.05 * fbm3(P * 1.5, 3, seed + 6))
    L.mix_rough(0.86, exposure * 0.7)
    splash = smoothstep(0.4, 0.1, z + 0.08 * fbm3(P * 6, 3, seed + 7))
    L.tint(srgb(70, 58, 44), splash * 0.5)
    specks = smoothstep(0.86, 0.92, noise3(P * 260, seed + 8)) * splash
    L.tint(srgb(40, 34, 28), specks * 0.8)
    scuff = smoothstep(0.66, 0.82, noise2(np.stack((P[:, 0] / 0.07, z / 0.006), axis=1), seed + 9))
    scuff = scuff * smoothstep(1.1, 0.6, np.abs(P[:, 0])) * smoothstep(0.32, 0.12, z) * boards
    L.tint(srgb(28, 26, 24), scuff * 0.55)
    backing = tex.name_mask("LogBacking")
    L.albedo[backing] *= 0.35
    L.albedo *= (0.42 + 0.58 * tex.ao)[:, None]
    L.mix_rough(0.8, 1 - tex.ao)
    L.ao_channel = 0.35 + 0.65 * tex.ao
    return L.finish()


# ------------------------------------------------------------------- metal

def weather_metal(tex, rng, seed=91):
    P, N = tex.P, tex.N
    z = P[:, 2]
    up = smoothstep(0.4, 0.8, N[:, 2])
    L = Layers(tex, srgb(26, 26, 26), 0.5)
    m = lambda *names: tex.name_mask(*names)  # noqa: E731
    bollard, pipe, spikes = m("Bollard"), m("Downpipe", "Hopper"), m("AntiClimb_Front", "AntiClimb_Gable", "AntiClimb_Hopper")
    galv, alu, steel, plastic = m("AntiClimb_Brackets", "TubeClip", "DownpipeClip"), m("Threshold"), m("CounterTop"), m("LEDSign_Case")
    for mask, colour, rough, metal in ((pipe, srgb(20, 20, 20), 0.42, 0.0), (spikes, srgb(30, 30, 28), 0.62, 0.0),
                                       (galv, srgb(150, 152, 150), 0.5, 1.0), (alu, srgb(165, 165, 160), 0.45, 1.0),
                                       (steel, srgb(160, 162, 162), 0.3, 1.0), (plastic, srgb(10, 10, 10), 0.4, 0.0)):
        L.albedo[mask] = colour
        L.rough[mask] = rough
        L.metal[mask] = metal
    noise = fbm3(P * 6, 3, seed)
    L.tint(srgb(86, 84, 78), up * (bollard | pipe | spikes) * (0.25 + 0.3 * noise))
    # Bollards: scuffs, a white bumper-paint transfer, rust rings at the pavement.
    L.tint(srgb(90, 90, 88), micro_scratches(tex, seed + 1) * bollard * 0.6)
    # One bollard carries the white smear photographed in front of the door.
    transfer = m("Bollard_04") * smoothstep(0.38, 0.46, z) * smoothstep(0.72, 0.6, z) * (N[:, 1] < -0.3)
    transfer = transfer * smoothstep(0.55, 0.7, fbm2(np.stack((P[:, 0] / 0.02, z / 0.09), axis=1), 3, seed + 2))
    L.tint(srgb(206, 206, 200), transfer * 0.6)
    L.mix_rough(0.7, transfer)
    rust_ring = bollard * smoothstep(0.14, 0.0, z + 0.04 * noise3(P * 30, seed + 3))
    L.tint(RUST, rust_ring * 0.6)
    L.mix_rough(0.9, rust_ring)
    chips = bollard * smoothstep(0.7, 0.8, fbm3(P * 50, 3, seed + 4)) * (0.3 + tex.convex)
    L.tint(srgb(90, 88, 84), np.clip(chips, 0, 1) * 0.6)
    # Downpipe: algae and damp at the shoe, a fleck of white paint.
    L.tint(ALGAE, pipe * smoothstep(0.35, 0.0, z) * 0.55)
    L.tint(srgb(200, 200, 196), pipe * smoothstep(0.9, 0.95, noise3(P * 90, seed + 5)) * 0.8)
    # Galvanising: white rust bloom and orange spots.
    bloom = galv * smoothstep(0.5, 0.7, fbm3(P * 25, 3, seed + 6))
    L.tint(srgb(196, 196, 188), bloom * 0.7)
    L.metal = np.where(bloom > 0.4, L.metal * (1 - bloom), L.metal)
    L.mix_rough(0.9, bloom)
    spots = galv * smoothstep(0.78, 0.86, noise3(P * 80, seed + 7))
    L.tint(RUST, spots)
    L.metal *= 1 - spots
    dirt = (alu | galv) * up * 0.5
    L.tint(GRIME, dirt)
    L.metal *= 1 - dirt * 0.6
    L.albedo *= (0.55 + 0.45 * tex.ao)[:, None]
    L.ao_channel = 0.45 + 0.55 * tex.ao
    return L.finish()


# ------------------------------------------------------------------- glass

def weather_glass(tex, rng, seed=111):
    P = tex.P
    z = P[:, 2]
    # Dark from outside, as photographed: reflections dominate and the interior only glows through.
    L = Layers(tex, (0.008, 0.010, 0.012), 0.05, alpha=0.62)
    s0, s1, t0, t1 = tex.panel_bounds()
    edge = np.minimum(np.minimum(tex.s - s0, s1 - tex.s), np.minimum(tex.t - t0, t1 - tex.t))
    film = smoothstep(0.06, 0.0, edge) * (0.6 + 0.4 * noise2(np.stack((tex.s / 0.03, tex.t / 0.03), axis=1), seed))
    low = smoothstep(0.22, 0.0, tex.t - t0 + 0.04 * fbm2(np.stack((tex.s / 0.1, tex.t / 0.1), axis=1), 3, seed + 1))
    dirt = np.clip(film * 0.6 + low * 0.8, 0, 1)
    L.tint(srgb(74, 66, 50), dirt)
    L.alpha += dirt * 0.4
    L.mix_rough(0.6, dirt)
    # Squeegee arcs and palm prints by the door.
    arcs = np.zeros(tex.M, F)
    for _ in range(9):
        cx, cz, radius = rng.uniform(-2.5, 2.9), rng.uniform(1.0, 2.2), rng.uniform(0.25, 0.6)
        arcs = np.maximum(arcs, smoothstep(0.015, 0.0, np.abs(np.hypot(P[:, 0] - cx, z - cz) - radius)) * 0.5)
    L.alpha += arcs * 0.08
    L.mix_rough(0.35, arcs)
    prints = np.zeros(tex.M, F)
    for _ in range(14):
        cx = rng.choice((-0.75, 0.72)) + rng.normal(0, 0.1)
        cz = rng.uniform(1.2, 1.6)
        near = (np.abs(P[:, 0] - cx) < 0.06) & (np.abs(z - cz) < 0.06)
        idx = np.flatnonzero(near)
        prints[idx] = np.maximum(prints[idx], fingerprint(P[idx, 0] - cx, z[idx] - cz, rng.uniform(0.012, 0.02), seed + 2))
    L.tint(srgb(60, 56, 46), prints * 0.6)
    L.alpha += prints * 0.2
    L.mix_rough(0.5, prints)
    residue = (P[:, 0] > 0.62) & (P[:, 0] < 0.78) & (z > 1.26) & (z < 1.40)
    torn = residue * smoothstep(0.35, 0.55, noise2(np.stack((P[:, 0] / 0.02, z / 0.02), axis=1), seed + 3))
    L.tint(srgb(150, 144, 128), torn * 0.8)
    L.alpha = np.maximum(L.alpha, torn * 0.7)
    L.mix_rough(0.8, torn)
    L.ao_channel = np.ones(tex.M, F)
    return L.finish()


# ------------------------------------------------------------------- interior

def weather_interior(tex, rng, seed=131):
    P, N = tex.P, tex.N
    z = P[:, 2]
    L = Layers(tex, srgb(146, 136, 118), 0.8)
    m = tex.name_mask
    floor, ceiling = m("Floor"), m("Ceiling")
    walls = m("BackWall", "LeftWall", "RightWall")
    tile = floor & ((np.abs(((P[:, 0] + 0.15) % 0.3) - 0.15) < 0.004) | (np.abs(((P[:, 1] + 0.15) % 0.3) - 0.15) < 0.004))
    L.albedo[floor] = srgb(76, 54, 42)
    L.albedo[tile] = srgb(40, 34, 30)
    L.tint(srgb(40, 34, 28), floor * smoothstep(-2.3, -3.1, P[:, 1]) * 0.5)
    L.rough[floor] = 0.45
    lower = walls & (z < 1.25)
    L.albedo[lower] = srgb(126, 82, 46)
    groove = lower & (np.abs(((z + 0.05) % 0.1) - 0.05) < 0.004)
    L.albedo[groove] = srgb(60, 38, 20)
    L.albedo[ceiling] = srgb(150, 148, 140)
    L.albedo[m("Counter")] = srgb(58, 34, 22)
    L.albedo[m("Fridge")] = srgb(170, 24, 24)
    L.rough[m("Fridge")] = 0.35
    L.albedo[m("WindowLedge")] = srgb(186, 182, 170)
    L.albedo *= (0.85 + 0.3 * fbm3(P * 3, 3, seed))[:, None]
    L.albedo *= (0.35 + 0.65 * tex.ao)[:, None]
    L.ao_channel = 0.3 + 0.7 * tex.ao
    return L.finish()


WEATHER = {
    "brick": weather_brick, "paint": weather_paint, "blue": weather_blue, "timber": weather_timber,
    "metal": weather_metal, "glass": weather_glass, "interior": weather_interior,
}


# ------------------------------------------------------------- map writing

def downsample(grid, factor):
    if factor <= 1:
        return grid
    h, w = grid.shape[:2]
    rest = grid.shape[2:]
    return grid.reshape(h // factor, factor, w // factor, factor, *rest).mean(axis=(1, 3))


def upsample(grid, factor):
    """Bilinear upsampling of bake buffers; exact on the planar faces that dominate."""
    if factor == 1:
        return grid
    h, w = grid.shape[:2]

    def axis(n):
        coords = (np.arange(n * factor) + 0.5) / factor - 0.5
        i0 = np.clip(np.floor(coords).astype(np.int64), 0, n - 1)
        i1 = np.clip(i0 + 1, 0, n - 1)
        return i0, i1, np.clip(coords - i0, 0, 1).astype(F)

    y0, y1, fy = axis(h)
    x0, x1, fx = axis(w)
    rows = grid[y0] * (1 - fy)[:, None, None] + grid[y1] * fy[:, None, None]
    return (rows[:, x0] * (1 - fx)[None, :, None] + rows[:, x1] * fx[None, :, None]).astype(F)


def write_maps(L, stem, normal_size, orm_size, normal_strength, alpha=False):
    tex = L.tex
    albedo = srgb_encode(L.albedo)
    fourth = L.alpha if alpha else np.ones(tex.M, F)
    size = tex.shape[1]
    base = tex.grid(np.column_stack((albedo, fourth)), fill=(*albedo.mean(axis=0), float(fourth.mean())))
    orm = tex.grid(np.column_stack((L.ao_channel, L.rough, L.metal)), fill=(1.0, float(L.rough.mean()), 0.0))
    images = {
        "base": save_rgba(TEXTURE_DIR / f"{stem}-basecolor.png", base),
        "orm": save_rgba(TEXTURE_DIR / f"{stem}-orm.png", downsample(orm, size // orm_size)),
    }
    images["orm"].colorspace_settings.name = "Non-Color"
    if normal_size:
        factor = size // normal_size
        height = downsample(tex.grid(L.height, fill=0.0), factor)
        images["normal"] = save_rgba(TEXTURE_DIR / f"{stem}-normal.png", height_to_normal(height, tex.texel_m * factor, normal_strength))
        images["normal"].colorspace_settings.name = "Non-Color"
    print(f"[spice-cabin] {stem}: {tex.M} texels at {tex.texel_m * 1000:.2f} mm, rough {L.rough.mean():.2f}", flush=True)
    return images


def cached_bake(stem, objects, size, ao_distance):
    path = Path(BAKE_CACHE) / f"{stem}-{size}.npz" if BAKE_CACHE else None
    if path and path.exists():
        data = np.load(path, allow_pickle=True)
        return data["position"], data["normal"], data["extra"], data["names"].item()
    position, normal, extra, names = bake_buffers(objects, size, size, ao_distance=ao_distance)
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(path, position=position, normal=normal, extra=extra, names=np.array(names, dtype=object))
    return position, normal, extra, names


def rect_uv(obj, rects, atlas, rotate=False):
    """Map quads by vertex index onto atlas rectangles (bottom-up pixels).

    Assigning by vertex index keeps the mapping valid after normals are flipped.
    """
    mesh = obj.data
    uv = mesh.uv_layers.get("UVMap") or mesh.uv_layers.new(name="UVMap")
    corner = ((0, 0), (1, 0), (1, 1), (0, 1)) if not rotate else ((0, 0), (0, 1), (1, 1), (1, 0))
    aw, ah = atlas
    for poly in mesh.polygons:
        x, y, w, h = rects[poly.index]
        for loop_index in poly.loop_indices:
            vi = mesh.loops[loop_index].vertex_index
            fu, fv = corner[vi % 4]
            uv.data[loop_index].uv = ((x + fu * w) / aw, (y + fv * h) / ah)


# ----------------------------------------------------------- ground contact

def ground_contact_maps():
    """Analytic contact decal: grime against the walls, bollard rings, damp at the shoe."""
    size = 2048
    rgba = np.zeros((size, size, 4), F)
    rough = np.full((size, size), 0.9, F)
    rng = np.random.default_rng(1733)
    for (xr, yr), rect in ((geo.GROUND_FRONT, artwork.GROUND_FRONT_RECT), (geo.GROUND_SIDE, artwork.GROUND_SIDE_RECT)):
        rx, ry, rw, rh = rect
        yy, xx = np.mgrid[0:rh, 0:rw].astype(F)
        X = xr[0] + (xx + 0.5) / rw * (xr[1] - xr[0])
        Y = yr[0] + (yy + 0.5) / rh * (yr[1] - yr[0])
        flat = np.stack((X.ravel(), Y.ravel()), axis=1)
        D = np.full(X.shape, 9.0, F)

        def seg(ax, ay, bx, by):
            px, py = X - ax, Y - ay
            vx, vy = bx - ax, by - ay
            t = np.clip((px * vx + py * vy) / (vx * vx + vy * vy), 0, 1)
            return np.hypot(px - t * vx, py - t * vy)

        for a in ((geo.PIER_X[1], -3.44, 2.98, -3.44), (geo.PIER_X[0], geo.FRONT_Y, geo.PIER_X[1], geo.FRONT_Y),
                  (geo.PIER_X[0], geo.FRONT_Y, geo.PIER_X[0], -2.95), (geo.SIDE_X, -2.95, geo.SIDE_X, geo.BACK_Y),
                  (geo.PIER_X[1], geo.FRONT_Y, geo.PIER_X[1], -3.44)):
            D = np.minimum(D, seg(*a))
        n = fbm2(flat * 3.0, 4, 5).reshape(X.shape)
        fine = noise2(flat * 60.0, 6).reshape(X.shape)
        grime = np.exp(-D / (0.07 + 0.05 * n)) * 0.8 + np.exp(-D / 0.35) * 0.25 * n
        corner = np.exp(-(np.hypot(X - geo.PIER_X[1], Y + 3.47) / 0.12) ** 2) + np.exp(-(np.hypot(X - geo.PIER_X[0], Y + 2.95) / 0.15) ** 2)
        grime = np.clip(grime + corner * 0.6, 0, 1) * (0.75 + 0.25 * fine)
        colour = np.broadcast_to(srgb(34, 31, 26), X.shape + (3,)).copy()
        alpha = grime * 0.85
        for bx, by in geo.BOLLARDS:
            r = np.hypot(X - bx, Y - by)
            ring = np.exp(-((r - 0.075) / 0.03) ** 2)
            rust = smoothstep(0.16, 0.08, r) * (0.5 + 0.5 * fine)
            colour = colour * (1 - rust[..., None] * 0.6) + srgb(80, 42, 20) * rust[..., None] * 0.6
            alpha = np.maximum(alpha, ring * 0.75 + rust * 0.35)
        damp = np.exp(-(((X - 3.0) / 0.28) ** 2 + ((Y + 3.85) / 0.45) ** 2)) * (0.7 + 0.3 * n)
        colour = colour * (1 - damp[..., None] * 0.3) + ALGAE * damp[..., None] * 0.3 * smoothstep(0.3, 0.6, n)[..., None]
        alpha = np.maximum(alpha, damp * 0.65)
        rough_rect = 0.9 - 0.65 * damp
        # Sparse gum spots and cigarette ends; never modelled litter.
        for _ in range(int(40 * rw * rh / (size * size))):
            gx, gy = rng.uniform(xr[0], xr[1]), rng.uniform(yr[0], yr[1])
            r = np.hypot(X - gx, Y - gy)
            spot = smoothstep(rng.uniform(0.008, 0.016), 0.004, r)
            colour = colour * (1 - spot[..., None]) + srgb(150, 148, 140) * spot[..., None]
            alpha = np.maximum(alpha, spot * 0.9)
        for _ in range(int(12 * rw * rh / (size * size))):
            gx, gy = rng.uniform(xr[0], xr[1]), rng.uniform(max(yr[0], -4.4), min(yr[1], -3.3) if yr[1] > -3.3 else yr[1])
            angle = rng.uniform(0, pi)
            du = (X - gx) * np.cos(angle) + (Y - gy) * np.sin(angle)
            dv = -(X - gx) * np.sin(angle) + (Y - gy) * np.cos(angle)
            butt = (np.abs(du) < 0.013) & (np.abs(dv) < 0.004)
            tip = butt & (du > 0.004)
            colour[butt] = srgb(225, 220, 205)
            colour[tip] = srgb(196, 120, 60)
            alpha[butt] = 1.0
        rgba[ry:ry + rh, rx:rx + rw, :3] = srgb_encode(colour.reshape(-1, 3)).reshape(colour.shape)
        rgba[ry:ry + rh, rx:rx + rw, 3] = np.clip(alpha, 0, 1)
        rough[ry:ry + rh, rx:rx + rw] = rough_rect
    base = save_rgba(TEXTURE_DIR / "ground-contact-basecolor.png", rgba)
    orm = np.dstack((np.ones((size, size), F), rough, np.zeros((size, size), F)))
    orm_image = save_rgba(TEXTURE_DIR / "ground-contact-orm.png", downsample(orm, 4))
    orm_image.colorspace_settings.name = "Non-Color"
    return {"base": base, "orm": orm_image}


def sign_maps():
    rgba, rough, height = artwork.sign_atlas(ARTWORK_DIR)
    base = save_rgba(TEXTURE_DIR / "sign-basecolor.png", rgba)
    h, w = rough.shape
    orm = np.dstack((np.ones((h, w), F), rough, np.zeros((h, w), F)))
    orm_image = save_rgba(TEXTURE_DIR / "sign-orm.png", downsample(orm, 4))
    orm_image.colorspace_settings.name = "Non-Color"
    normal = height_to_normal(downsample(height, 4), artwork.SIGN_TEXEL_M * 4, 2.0)
    normal_image = save_rgba(TEXTURE_DIR / "sign-normal.png", normal)
    normal_image.colorspace_settings.name = "Non-Color"
    return {"base": base, "orm": orm_image, "normal": normal_image}


def emissive_maps():
    rgb, rough = artwork.emissive_atlas(ARTWORK_DIR)
    h, w = rough.shape
    base = save_rgba(TEXTURE_DIR / "emissive-basecolor.png", np.dstack((rgb, np.ones((h, w), F))))
    orm = np.dstack((np.ones((h, w), F), rough, np.zeros((h, w), F)))
    orm_image = save_rgba(TEXTURE_DIR / "emissive-orm.png", downsample(orm, 4))
    orm_image.colorspace_settings.name = "Non-Color"
    return {"base": base, "orm": orm_image}


def alpha_clip(mat):
    """Sawn log-end cut-outs: glTF alphaMode MASK via the exporter's Round-node convention."""
    nt = mat.node_tree
    shader = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    base = nt.nodes["Base Color"]
    clip = nt.nodes.new("ShaderNodeMath")
    clip.operation = "ROUND"
    nt.links.new(base.outputs["Alpha"], clip.inputs[0])
    nt.links.new(clip.outputs[0], shader.inputs["Alpha"])
    mat.surface_render_method = "DITHERED"
    base.image.alpha_mode = "STRAIGHT"


# -------------------------------------------------------------------- stage

EMISSIVE_OBJECTS = (
    ("LEDSign_Face", "led", False), ("FridgeFront", "fridge", False), ("MenuBoard_01", "menu1", False),
    ("MenuBoard_02", "menu2", False), ("MenuBoard_03", "menu3", False), ("CeilingPanel", "ceiling", False),
    ("TubeDiffuser_Front", "tube_front", False), ("TubeDiffuser_Side", "tube_side", True),
)


def texture_stage():
    TEXTURE_DIR.mkdir(parents=True, exist_ok=True)
    for stale in TEXTURE_DIR.glob("*.png"):
        stale.unlink()
    rng = np.random.default_rng(16_0161)
    geo.clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    mats = geo.create_materials()
    builder = geo.build_asset(mats)
    groups = {key: geo.meshes_with(builder, mats[key]) for key in list(ATLASES) + ["sign", "emissive", "ground"]}

    for key, (_, _, _, _, _, importance) in ATLASES.items():
        unwrap_atlas(groups[key], importance=importance)
    for obj in groups["sign"]:
        rect_uv(obj, [artwork.SIGN_FRONT_RECT if "Front" in obj.name else artwork.SIGN_SIDE_RECT], artwork.SIGN_SIZE)
    for obj in groups["emissive"]:
        for fragment, cell, rotate in EMISSIVE_OBJECTS:
            if fragment in obj.name:
                rect_uv(obj, [artwork.EMISSIVE_CELLS[cell]] * len(obj.data.polygons), artwork.EMISSIVE_SIZE, rotate)
    rect_uv(groups["ground"][0], [artwork.GROUND_FRONT_RECT, artwork.GROUND_SIDE_RECT], (2048, 2048))

    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, -0.002))
    temp_ground = bpy.context.object
    temp_ground.name = "TEMP_Bake_Ground"
    maps = {}
    for key, (size, factor, normal_size, orm_size, strength, _) in ATLASES.items():
        started = time.time()
        position, normal, extra, names = cached_bake(key, groups[key], size, 0.3 if key != "interior" else 0.6)
        print(f"[spice-cabin] {key}: baked in {time.time() - started:.0f}s", flush=True)
        tex = Texels(upsample(position, factor), upsample(normal, factor), upsample(extra, factor), names)
        layers = WEATHER[key](tex, rng)
        maps[key] = write_maps(layers, key, normal_size, orm_size, strength, alpha=(key == "glass"))
        print(f"[spice-cabin] {key}: done in {time.time() - started:.0f}s", flush=True)
        del tex, layers, position, normal, extra
    bpy.data.objects.remove(temp_ground, do_unlink=True)
    maps["sign"] = sign_maps()
    maps["emissive"] = emissive_maps()
    maps["ground"] = ground_contact_maps()

    for key, options in (("brick", {}), ("paint", {}), ("blue", {}), ("timber", {}), ("metal", {}),
                         ("glass", {"blend_alpha": True}), ("interior", {}), ("sign", {}),
                         ("emissive", {"emission_strength": 2.5}), ("ground", {"blend_alpha": True})):
        m = maps[key]
        build_pbr_material(mats[key], m["base"], m.get("orm"), m.get("normal"), **options)
    alpha_clip(mats["sign"])
    # Every face is modelled facing outward, so single-sided glTF materials avoid needless overdraw.
    for mat in mats.values():
        mat.use_backface_culling = True

    for image in bpy.data.images:
        if image.filepath:
            image.filepath = bpy.path.relpath(image.filepath, start=str(BLEND.parent))
    validate(builder)
    note = bpy.data.texts.new("SPICE_CABIN_NOTES")
    note.write("Reference-led Spice Cabin end unit. Frontage -Y, gable -X, origin at footprint centre.\n"
               "Rebuild with blender/scripts/createSpiceCabin.py; see docs/assets/spice-cabin.md.\n")
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    export_glb(builder)


def validate(builder):
    required = ("SPICE_Sign_Front_Face", "SPICE_Sign_Side_Face", "SPICE_CreamPier", "SPICE_LogBoards_LeftA",
                "SPICE_Brick_Gable", "SPICE_Tube_Side", "SPICE_AntiClimb_Front", "SPICE_Downpipe",
                "SPICE_EntranceAnchor", "SPICE_LightAnchor_Sign")
    missing = [name for name in required if bpy.data.objects.get(name) is None]
    if missing:
        raise RuntimeError(f"Missing required Spice Cabin objects: {missing}")
    meshes = geo.asset_meshes(builder)
    # Roof felt is a flat untextured colour, only visible from above.
    unmapped = [o.name for o in meshes if not o.data.uv_layers and o.data.materials[0].name != geo.MATERIAL_KEYS["felt"]]
    if unmapped:
        raise RuntimeError(f"Meshes without UVs: {unmapped}")
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in meshes)
    print(f"[spice-cabin] validation: {len(meshes)} meshes, {tris} triangles, "
          f"{len({o.data.materials[0].name for o in meshes})} materials")


def export_glb(builder):
    GLB.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in builder.collection.objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = builder.root
    bpy.ops.export_scene.gltf(filepath=str(GLB), export_format="GLB", use_selection=True, export_apply=True,
                              export_yup=True, export_cameras=False, export_lights=False, export_extras=False,
                              export_image_format="WEBP", export_image_quality=86)
    print(f"[spice-cabin] exported {GLB} ({GLB.stat().st_size / 1e6:.1f} MB)")


# ------------------------------------------------------------------ renders

def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def flat_material(name, colour, roughness=0.8, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value = (*colour, 1)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    return mat


def pavement_material():
    mat = bpy.data.materials.new("REVIEW_Pavement")
    mat.use_nodes = True
    nt = mat.node_tree
    shader = nt.nodes["Principled BSDF"]
    coords = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (1 / 1.8, 1 / 1.8, 1)
    nt.links.new(coords.outputs["Object"], mapping.inputs["Vector"])
    for name, socket, non_color in (("pavement-albedo.png", "Base Color", False), ("pavement-roughness.png", "Roughness", True)):
        image = nt.nodes.new("ShaderNodeTexImage")
        image.image = load_image(PAVEMENT_DIR / name, non_color)
        nt.links.new(mapping.outputs["Vector"], image.inputs["Vector"])
        nt.links.new(image.outputs["Color"], shader.inputs[socket])
    normal = nt.nodes.new("ShaderNodeTexImage")
    normal.image = load_image(PAVEMENT_DIR / "pavement-normal.png", True)
    nt.links.new(mapping.outputs["Vector"], normal.inputs["Vector"])
    normal_map = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(normal.outputs["Color"], normal_map.inputs["Color"])
    nt.links.new(normal_map.outputs["Normal"], shader.inputs["Normal"])
    return mat


def build_review_stage():
    """Review-only context: pavement, kerb and road, the railing, the neighbour's edge, a scale figure."""
    b = geo.Builder("SPICE_review_only", "SPICE_REVIEW")
    pavement = pavement_material()
    road = flat_material("REVIEW_Road", (0.03, 0.03, 0.032), 0.75)
    grass = flat_material("REVIEW_Grass", (0.05, 0.09, 0.025), 0.95)
    galv = flat_material("REVIEW_Galvanised", (0.45, 0.45, 0.44), 0.45, 1.0)
    blue = flat_material("REVIEW_NeighbourBlue", (0.02, 0.1, 0.4), 0.55)
    cream = flat_material("REVIEW_NeighbourCream", (0.6, 0.57, 0.48), 0.85)
    shutter = flat_material("REVIEW_Shutter", (0.03, 0.08, 0.25), 0.5, 0.4)
    figure = flat_material("REVIEW_ScaleFigure", (0.06, 0.06, 0.065), 0.7)
    concrete = flat_material("REVIEW_WhiteBollard", (0.6, 0.6, 0.58), 0.8)
    geo.quad(b, "REVIEW_Pavement", [(-14, -10.5, 0), (9, -10.5, 0), (9, 5, 0), (-14, 5, 0)], "REVIEW", pavement, (0, 0, 1))
    geo.box(b, "REVIEW_Kerb", (-14, 9), (-10.65, -10.5), (-0.12, 0.0), "REVIEW", pavement)
    geo.quad(b, "REVIEW_Road", [(-14, -20, -0.12), (9, -20, -0.12), (9, -10.65, -0.12), (-14, -10.65, -0.12)], "REVIEW", road, (0, 0, 1))
    geo.quad(b, "REVIEW_Grass", [(-14, -4.2, 0.01), (-6.2, -4.2, 0.01), (-6.2, 5, 0.01), (-14, 5, 0.01)], "REVIEW", grass, (0, 0, 1))
    for x in np.arange(-9.0, -3.8, 2.0):
        geo.pipe(b, f"REVIEW_RailPost_{x:+.1f}", [(x, -5.3, 0), (x, -5.3, 1.05)], 0.025, "REVIEW", galv, 8)
    for z in (0.15, 1.0):
        geo.pipe(b, f"REVIEW_RailTop_{z}", [(-9.0, -5.3, z), (-3.9, -5.3, z)], 0.02, "REVIEW", galv, 8)
    for x in np.arange(-8.9, -3.9, 0.13):
        geo.pipe(b, f"REVIEW_RailBar_{x:+.2f}", [(x, -5.3, 0.15), (x, -5.3, 1.0)], 0.008, "REVIEW", galv, 6, caps=False)
    geo.pipe(b, "REVIEW_WhiteBollard", [(-5.2, -6.2, 0), (-5.2, -6.2, 0.95)], 0.09, "REVIEW", concrete, 12)
    geo.box(b, "REVIEW_Neighbour_Post", (3.10, 3.24), (-3.40, -3.10), (0, 2.6), "REVIEW", blue)
    geo.box(b, "REVIEW_Neighbour_Box", (3.10, 5.6), (-3.48, -3.10), (2.02, 2.62), "REVIEW", blue)
    geo.box(b, "REVIEW_Neighbour_Shutter", (3.24, 5.6), (-3.22, -3.10), (0.1, 2.02), "REVIEW", shutter)
    geo.box(b, "REVIEW_Neighbour_Band", (2.92, 5.6), (-3.62, -3.20), geo.BAND, "REVIEW", cream)
    parapet = flat_material("REVIEW_NeighbourBrick", (0.32, 0.22, 0.13), 0.9)
    geo.box(b, "REVIEW_Neighbour_Parapet", (3.10, 5.6), (-3.30, -3.00), (geo.BAND[1], geo.PARAPET_TOP), "REVIEW", parapet)
    geo.pipe(b, "REVIEW_ScaleFigure", [(2.3, -5.3, 0.25), (2.3, -5.3, 1.52)], 0.21, "REVIEW", figure, 16)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(2.3, -5.3, 1.66))
    head = bpy.context.object
    head.name = "REVIEW_ScaleHead"
    head.data.materials.append(figure)
    return b


def set_world(colour, strength):
    world = bpy.context.scene.world or bpy.data.worlds.new("REVIEW_World")
    bpy.context.scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes["Background"]
    background.inputs["Color"].default_value = (*colour, 1.0)
    background.inputs["Strength"].default_value = strength


def add_light(kind, location, target, energy, colour, size=0.1, spot=radians(60), angle=2.0):
    data = bpy.data.lights.new(f"TEMP_{kind}", kind)
    data.energy = energy
    data.color = colour
    if kind == "AREA":
        data.size = size
    else:
        data.shadow_soft_size = size
    if kind == "SPOT":
        data.spot_size = spot
        data.spot_blend = 0.4
    if kind == "SUN":
        data.angle = radians(angle)
    obj = bpy.data.objects.new(f"TEMP_{kind}", data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    point_at(obj, target)
    return obj


def set_emission(strength):
    mat = bpy.data.materials["MAT_emissive_signage"]
    shader = next(n for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    shader.inputs["Emission Strength"].default_value = strength


def rig(name):
    if name == "overcast":
        set_world((0.55, 0.57, 0.6), 1.5)
        add_light("SUN", (0, 0, 10), (0.4, 0.6, 0), 0.8, (1.0, 0.98, 0.95), angle=25)
        set_emission(1.2)
    elif name == "sun":
        set_world((0.35, 0.5, 0.85), 0.8)
        add_light("SUN", (-6, -4, 8), (0, 0, 0), 4.0, (1.0, 0.95, 0.86))
        set_emission(1.2)
    elif name == "grazing":
        # Low sun raking along the shopfront from the gable side.
        set_world((0.4, 0.46, 0.56), 0.5)
        add_light("SUN", (-10, -4.4, 2.2), (0, -3.2, 0.6), 4.5, (1.0, 0.86, 0.7), angle=1.0)
        set_emission(1.0)
    elif name == "gable_rake":
        set_world((0.4, 0.46, 0.56), 0.45)
        add_light("SUN", (-3.3, -10, 3.0), (-3.05, 0.5, 2.2), 4.5, (1.0, 0.88, 0.74), angle=1.0)
        set_emission(1.0)
    elif name == "night":
        set_world((0.002, 0.003, 0.007), 1.0)
        set_emission(4.0)
        add_light("AREA", (0.2, -1.9, 2.45), (0.2, -1.9, 0), 220, (1.0, 0.82, 0.62), size=3.0)
        add_light("POINT", (-7.5, -9.5, 6.0), (0, -3, 0), 1400, (1.0, 0.55, 0.22), size=0.2)
        add_light("AREA", (-0.2, -3.9, 3.5), (-0.2, -3.36, 3.0), 45, (1.0, 0.9, 0.78), size=4.5)
        add_light("AREA", (-3.35, 0.2, 4.0), (-3.13, 0.3, 3.2), 40, (1.0, 0.9, 0.78), size=4.0)
        add_light("POINT", (1.44, -3.35, 1.72), (1.44, -4, 1.0), 6, (1.0, 0.05, 0.02), size=0.3)


def validation_glass():
    """Validation-only glass matching a premultiplied runtime glass: film blends, reflection adds."""
    mat = bpy.data.materials["MAT_glass_shopfront"]
    nt = mat.node_tree
    grime = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    output = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeOutputMaterial")
    base = nt.nodes["Base Color"]
    for link in list(grime.inputs["Alpha"].links):
        nt.links.remove(link)
    grime.inputs["Specular IOR Level"].default_value = 0.0
    reflection = nt.nodes.new("ShaderNodeBsdfPrincipled")
    reflection.inputs["Base Color"].default_value = (0, 0, 0, 1)
    reflection.inputs["IOR"].default_value = 1.52
    nt.links.new(nt.nodes["ORM Split"].outputs["Green"], reflection.inputs["Roughness"])
    clear = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(base.outputs["Alpha"], mix.inputs["Fac"])
    nt.links.new(clear.outputs[0], mix.inputs[1])
    nt.links.new(grime.outputs[0], mix.inputs[2])
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(mix.outputs[0], add.inputs[0])
    nt.links.new(reflection.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], output.inputs["Surface"])


VIEWS = (
    ("01-neutral-overcast-daylight", (-6.8, -13.0, 1.7), (0.0, -3.3, 2.4), 30, "overcast", (1280, 960)),
    ("02-oblique-grazing-daylight", (7.2, -11.5, 1.7), (-0.6, -3.3, 2.2), 32, "grazing", (1280, 960)),
    ("03-night-practical-light", (-5.2, -11.8, 1.65), (0.0, -3.3, 2.3), 30, "night", (1280, 960)),
    ("04-brick-close-up", (-4.25, -1.55, 3.25), (-3.05, -2.05, 3.30), 40, "gable_rake", (1024, 1024)),
    ("05-rounded-timber-close-up", (-0.95, -4.30, 0.75), (-1.95, -3.22, 0.58), 38, "grazing", (1024, 1024)),
    ("06-straight-on-facade", (0.0, -24.0, 2.45), (0.0, -3.3, 2.45), 80, "overcast", (1400, 1000)),
    ("07-gable-sign-daylight", (-9.8, 2.2, 1.6), (-3.05, 0.2, 3.3), 30, "sun", (1280, 960)),
    ("08-reference-match-photo-4", (-4.4, -10.2, 1.6), (0.35, -3.3, 2.25), 27, "overcast", (1200, 1200)),
    ("09-gameplay-camera-distance", None, None, None, "night", (1280, 720)),
    ("10-roof-edge-and-services", (1.2, -6.2, 4.3), (2.4, -3.3, 4.2), 35, "overcast", (1280, 960)),
    ("11-shopfront-junctions", (-0.15, -4.9, 1.3), (-0.9, -3.25, 1.2), 30, "overcast", (1280, 960)),
)


def render_stage(only=None):
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.use_raytracing = True
    scene.eevee.taa_render_samples = 64
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "None"
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    validation_glass()
    # Validation only: EEVEE drops a thin blended decal over the opaque stage, so dither it.
    bpy.data.materials["MAT_ground_contact"].surface_render_method = "DITHERED"
    build_review_stage()
    for name, location, target, lens, rig_name, (width, height) in VIEWS:
        if only and not any(key in name for key in only):
            continue
        for obj in list(bpy.data.objects):
            if obj.name.startswith("TEMP_") or obj.name.startswith("VALIDATION_Camera"):
                bpy.data.objects.remove(obj, do_unlink=True)
        rig(rig_name)
        data = bpy.data.cameras.new("VALIDATION_Camera")
        cam = bpy.data.objects.new("VALIDATION_Camera", data)
        scene.collection.objects.link(cam)
        if location is None:
            # Game camera: 6.8 m behind the player at 0.31 rad pitch, 50 degree vertical FOV.
            player = Vector((-0.8, -7.4, 1.5))
            cam.location = player + Vector((0, -6.8 * np.cos(0.31), 6.8 * np.sin(0.31)))
            data.sensor_fit = "VERTICAL"
            data.angle_y = radians(50)
            point_at(cam, player + Vector((0, 3, 0.4)))
        else:
            cam.location = location
            data.lens = lens
            point_at(cam, target)
        data.clip_start = 0.02
        scene.camera = cam
        scene.render.resolution_x, scene.render.resolution_y = width, height
        scene.render.filepath = str(RENDER_DIR / f"{name}.png")
        started = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"[spice-cabin] rendered {name} in {time.time() - started:.0f}s", flush=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    stage = argv[argv.index("--stage") + 1] if "--stage" in argv else "all"
    only = argv[argv.index("--only") + 1].split(",") if "--only" in argv else None
    global BAKE_CACHE
    BAKE_CACHE = argv[argv.index("--bake-cache") + 1] if "--bake-cache" in argv else None
    if stage in ("all", "textures"):
        texture_stage()
    if stage in ("all", "renders"):
        for stale in RENDER_DIR.glob("*.png") if not only else ():
            stale.unlink()
        render_stage(only)


if __name__ == "__main__":
    main()
