"""Material and texture pass for the approved North Road, Preston bus shelter.

Geometry comes unchanged from createBusShelter.py.  This pass adds only what
the textures need to read correctly -- a thin acrylic cover over the timetable
and a ground-contact decal -- then:

  * gives every material a unique, density-consistent UV atlas;
  * bakes world position, normal, object id, AO and convexity into each atlas;
  * authors weathering from physical causes: rain runs down, road spray rises,
    hands touch predictable heights, dirt settles in recesses, sun and water
    act on exposed faces, and cleaning leaves arcs;
  * reconstructs the timetable, No Smoking sign, stop number and advert from
    references/architecture/bus-stop/Hires2.jpg;
  * writes a reusable urban decal library and a wetness mask (base-colour alpha
    of opaque materials) for the runtime wet-weather shader;
  * exports textured GLBs and the twelve-view validation render set.

Run from the repository root:

  /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \\
    --python blender/scripts/createBusShelterTextured.py [-- --stage textures|renders]
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

import busShelterArtwork as artwork  # noqa: E402
import createBusShelter as shelter_geometry  # noqa: E402
from surfaceWeathering import (  # noqa: E402
    F,
    Layers,
    Texels,
    apply_decal,
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
    palm_print,
    plane_axes,
    polyline_coverage,
    save_rgba,
    segment_coverage,
    smoothstep,
    srgb_decode,
    srgb_encode,
    streaks,
    unwrap_atlas,
)

PROJECT_ROOT = SCRIPT_DIR.parents[1]
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "bus-shelter" / "texture-pass"
ARTWORK_DIR = TEXTURE_DIR / "artwork"
DECAL_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "urban-decals"
TEXTURED_BLEND = PROJECT_ROOT / "blender" / "source" / "bus-shelter" / "preston-busstop-textured.blend"
SHELTER_GLB = shelter_geometry.MODEL_DIR / "preston-bus-shelter-textured.glb"
REFERENCE_GLB = shelter_geometry.MODEL_DIR / "preston-busstop-textured.glb"
RENDER_DIR = PROJECT_ROOT / "renders" / "bus-shelter-texture-pass"
WORLD_TEXTURES = PROJECT_ROOT / "public" / "assets" / "textures" / "world-prototype"

# Shelter layout from createBusShelter.build_shelter (metres, open front +X,
# road beyond +X).
ROOF_HALF_X = 0.86
ROOF_HALF_Y = 2.59
ROOF_UNDERSIDE_Z = 2.25
REAR_X = -0.70
REAR_GLASS_X = -0.694
POST_YS = (-2.37, -0.79, 0.79, 2.37)
ADVERT_PLINTH_CENTRE = (0.01, 2.47)
ADVERT_PLINTH_HALF = (0.61, 0.09)

# Linear albedo.
POWDER_COAT = (0.058, 0.068, 0.062)
POWDER_COAT_WARM = (0.07, 0.066, 0.055)
SUN_BLEACHED = (0.1, 0.106, 0.1)
GRIME_DARK = (0.016, 0.015, 0.012)
STREAK_DIRT = (0.028, 0.026, 0.02)
ROAD_MUD = (0.08, 0.066, 0.048)
AGGREGATE = (0.2, 0.19, 0.17)
SALT_DUST = (0.19, 0.185, 0.17)
PRIMER = (0.18, 0.18, 0.17)
BARE_METAL = (0.52, 0.52, 0.5)
SCRATCH_LIGHT = (0.14, 0.15, 0.14)
RUST = (0.15, 0.055, 0.018)
ROOF_PAINT = (0.075, 0.09, 0.078)
ATMOSPHERIC_DIRT = (0.036, 0.034, 0.027)
ALGAE = (0.026, 0.045, 0.014)
RAIL_RED = (0.46, 0.038, 0.015)
RAIL_BLEACHED = (0.54, 0.11, 0.065)
RAIL_WORN = (0.22, 0.032, 0.016)
GALVANISED = (0.33, 0.33, 0.32)
GLASS_FILM = (0.19, 0.18, 0.15)
GLASS_GRIME = (0.065, 0.055, 0.04)
MINERAL = (0.5, 0.49, 0.45)

ATLAS_SIZES = {
    # name: (bake w, bake h, normal size)
    "frame": (2048, 2048, 2048),
    "glass": (2048, 2048, 1024),
    "roof": (1024, 1024, 1024),
    "rail": (1024, 1024, 1024),
    "ground": (1024, 2048, None),
}

# Opaque materials store rain exposure in base-colour alpha as
# WET_FLOOR + (1 - WET_FLOOR) * wet.  The floor keeps every texel partly opaque:
# WebP discards the colour of fully transparent pixels.
WET_FLOOR = 0.2

SIGN_ATLAS = 2048
TIMETABLE_RECT = (0, 12, 1100, 2024)
NO_SMOKING_RECT = (1150, 1500, 440, 520)
NUMBER_RECT = (1130, 1180, 900, 256)
PAINT_RECT = (1130, 40, 256, 256)
ADVERT_SIZE = (1024, 1432)
LIGHT_SIZE = 512


# ------------------------------------------------------------------ geometry

def add_texture_pass_geometry(shelter, mats):
    """The only geometry this pass adds: a timetable cover and ground contact."""
    signage = bpy.data.objects["BUSSTOP_Signage"]
    shelter_geometry.add_plane_yz(
        "BUSSTOP_Timetable_Cover", -0.556, (-1.80, -1.14), (0.88, 2.06), mats["glass"], signage)
    ground_mat = bpy.data.materials.new("MAT_BusStop_GroundContact")
    ground = shelter_geometry.add_plane_xz(
        "BUSSTOP_GroundContact_Decal", 0.0, (0, 1), (0, 1), ground_mat, shelter)
    mesh = ground.data
    mesh.clear_geometry()
    mesh.from_pydata([(-1.25, -2.95, 0.004), (1.35, -2.95, 0.004), (1.35, 2.95, 0.004), (-1.25, 2.95, 0.004)], [], [(0, 1, 2, 3)])
    mesh.materials.append(ground_mat)
    mesh.update()
    mats["ground"] = ground_mat


def meshes_with(root, mat):
    return [obj for obj in shelter_geometry.descendants(root)
            if obj.type == "MESH" and obj.data.materials and obj.data.materials[0] == mat]


def planar_uv(obj, rect, atlas_size, u_axis, v_axis, face_filter=None, fallback=None):
    """Map an object's faces onto an atlas rectangle by planar projection."""
    mesh = obj.data
    uv = mesh.uv_layers.get("UVMap") or mesh.uv_layers.new(name="UVMap")
    coords = np.array([v.co[:] for v in mesh.vertices], F)
    lo = coords.min(axis=0)
    span = np.maximum(coords.max(axis=0) - lo, 1e-6)
    atlas_w, atlas_h = atlas_size
    for poly in mesh.polygons:
        x, y, w, h = rect if (face_filter is None or face_filter(poly)) else fallback
        for loop_index in poly.loop_indices:
            co = mesh.vertices[mesh.loops[loop_index].vertex_index].co
            fu = (co[u_axis] - lo[u_axis]) / span[u_axis]
            fv = (co[v_axis] - lo[v_axis]) / span[v_axis]
            uv.data[loop_index].uv = ((x + fu * w) / atlas_w, (y + fv * h) / atlas_h)


def add_temporary_ground():
    bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 0, 0))
    plane = bpy.context.object
    plane.name = "TEMP_Bake_Ground"
    return plane


# ------------------------------------------------------- exposure & contact

def roof_cover(P):
    outside = np.maximum(np.abs(P[:, 0]) - ROOF_HALF_X, np.abs(P[:, 1]) - ROOF_HALF_Y)
    return smoothstep(0.02, -0.14, outside) * (P[:, 2] < ROOF_UNDERSIDE_Z)


def windward(tex):
    P, N = tex.P, tex.N
    w = (np.clip(-N[:, 0], 0, 1) * (P[:, 0] < -0.6)
         + np.clip(N[:, 0], 0, 1) * (P[:, 0] > 0.6)
         + np.clip(N[:, 1] * np.sign(P[:, 1]), 0, 1) * (np.abs(P[:, 1]) > 2.25))
    return np.clip(w, 0, 1).astype(F)


def rain_exposure(tex):
    sky = 1 - roof_cover(tex.P)
    driven = windward(tex) * smoothstep(2.3, 0.9, tex.P[:, 2]) * 0.75
    return np.maximum(sky, driven).astype(F)


def road_splash(tex, seed):
    """Spray thrown up from the carriageway: stronger toward the road and ground."""
    P, N = tex.P, tex.N
    flat = np.stack((P[:, 0] * 1.6, P[:, 1] * 1.6, np.zeros(tex.M, F)), axis=1)
    limit = 0.3 + 0.2 * fbm3(flat, 3, seed)
    zone = smoothstep(limit, limit * 0.1, P[:, 2])
    roadward = 0.45 + 0.35 * np.clip(N[:, 0], 0, 1) + 0.2 * smoothstep(-0.8, 0.8, P[:, 0])
    return np.clip(zone * roadward, 0, 1).astype(F)


def splash_specks(tex, splash, seed):
    live = splash > 0.02
    dark = smoothstep(0.86 - 0.22 * splash, 0.92 - 0.22 * splash, noise3(tex.P * 240, seed)) * live
    light = smoothstep(0.9, 0.95, noise3(tex.P * 260, seed + 1)) * splash
    return dark.astype(F), light.astype(F)


def hand_contact(tex, table):
    """Contact likelihood from object name -> (weight, height centre, height spread)."""
    contact = np.zeros(tex.M, F)
    for object_id, name in tex.names.items():
        for fragment, (weight, centre, spread) in table.items():
            if fragment in name:
                sel = tex.ids == object_id
                contact[sel] = weight * np.exp(-((tex.P[sel, 2] - centre) / spread) ** 2)
    return contact


def wet_mask(tex, exposure, splash):
    up = np.clip(tex.N[:, 2], 0, 1)
    return np.clip(exposure * (0.65 + 0.35 * up) + splash * 0.6, 0, 1).astype(F)


def add_bolts(L, bolts, rng):
    tex = L.tex
    for center, normal, radius in bolts:
        idx, u, v = tex.stamp(center, normal, radius * 2.4, depth=0.012)
        if not len(idx):
            continue
        d = np.hypot(u, v)
        head = smoothstep(radius, radius * 0.8, d)
        washer = smoothstep(radius * 1.5, radius * 1.35, d) * (1 - head)
        ring = np.exp(-((d - radius * 1.5) / (radius * 0.2)) ** 2)
        dome = np.sqrt(np.clip(1 - (d / radius) ** 2, 0, 1))
        angle = rng.uniform(0, pi)
        slot = (np.abs(u * np.cos(angle) + v * np.sin(angle)) < radius * 0.15) & (d < radius * 0.8)
        rust_amount = rng.uniform(0, 0.75) ** 2
        rust = rust_amount * smoothstep(0.35, 0.7, noise3(tex.P[idx] * 900, int(rng.integers(1e6)))) * np.clip(head + washer + ring, 0, 1)
        steel = head + washer
        L.tint(np.array((0.3, 0.3, 0.29), F) * rng.uniform(0.8, 1.15), steel, idx)
        L.metal[idx] = np.maximum(L.metal[idx], 0.85 * steel * (1 - rust))
        L.mix_rough(rng.uniform(0.36, 0.6), steel, idx)
        L.height[idx] += 0.0028 * dome * head + 0.0007 * washer - 0.0012 * slot * head
        L.tint(GRIME_DARK, 0.45 * ring, idx)
        L.rough[idx] += 0.2 * ring
        L.tint(RUST, rust, idx)
        L.mix_rough(0.85, rust, idx)
        if rust_amount > 0.18:
            run_idx, ru, rv = tex.stamp(center, normal, 0.12, depth=0.012)
            run = np.exp(-(ru / (radius * 0.6)) ** 2) * smoothstep(-radius, -radius * 2, rv) * np.exp(rv / 0.05)
            L.tint(RUST, 0.55 * run * rust_amount, run_idx)


def add_prints(L, spots, rng, rough_shift, alpha_shift=0.0, darken=0.05):
    """Clusters of fingertip marks around world-space touch points."""
    tex = L.tex
    for center, normal, count, spread in spots:
        _, u_axis, v_axis = plane_axes(normal)
        for _ in range(count):
            c = np.asarray(center, F) + u_axis * rng.normal(0, spread[0]) + v_axis * rng.normal(0, spread[1])
            idx, u, v = tex.stamp(c, normal, 0.03, depth=0.012)
            if not len(idx):
                continue
            angle = rng.uniform(-0.5, 0.5)
            ru = u * np.cos(angle) + v * np.sin(angle)
            rv = -u * np.sin(angle) + v * np.cos(angle)
            p = fingerprint(ru, rv, rng.uniform(0.013, 0.019), int(rng.integers(1e6)))
            L.rough[idx] += rough_shift * p
            L.alpha[idx] += alpha_shift * p
            L.albedo[idx] *= (1 - darken * p)[:, None]


# -------------------------------------------------------------- frame metal

FRAME_CONTACT = {
    "LeftFrontUpright": (1.0, 1.2, 0.3),
    "RightFrontUpright": (1.0, 1.2, 0.3),
    "RearUpright_01": (0.55, 1.15, 0.35),
    "RearUpright_04": (0.55, 1.15, 0.35),
    "RearUpright_02": (0.35, 1.1, 0.35),
    "RearUpright_03": (0.35, 1.1, 0.35),
    "RearRail_103": (0.6, 1.03, 0.1),
    "Bench_Perch": (1.0, 0.72, 0.06),
    "Timetable_Backplate": (0.25, 1.45, 0.4),
    "AdvertHousing": (0.4, 1.1, 0.5),
}


def frame_bolts():
    bolts = []
    for y in POST_YS:
        for z in (0.28, 1.03, 2.25):
            bolts.append(((REAR_X + 0.0425, y, z), (1, 0, 0), 0.009))
    for y in (-2.37, 2.37):
        for z in (0.28, 2.24):
            bolts.append(((0.7425, y, z), (1, 0, 0), 0.009))
    for y in (-1.80, -1.14):
        for z in (0.875, 2.065):
            bolts.append(((-0.5725, y, z), (1, 0, 0), 0.006))
    for y in (-2.175, -1.925):
        for z in (1.805, 2.135):
            bolts.append(((-0.5725, y, z), (1, 0, 0), 0.005))
    return bolts


def weather_frame(tex, library, rng):
    P, N = tex.P, tex.N
    z = P[:, 2]
    L = Layers(tex, POWDER_COAT, 0.5)
    exposure = rain_exposure(tex)
    splash = road_splash(tex, 20)
    contact = hand_contact(tex, FRAME_CONTACT)
    perch_top = tex.name_mask("Bench_Perch") & (N[:, 2] > 0.5)
    contact = np.where(perch_top, np.maximum(contact, 0.9), contact)

    # Macro: tonal drift, a slightly warmer respray batch, sun on outward faces.
    L.albedo *= (0.84 + 0.32 * fbm3(P * 1.3, 4, 11))[:, None]
    L.tint(POWDER_COAT_WARM, 0.4 * fbm3(P * 0.45, 3, 12))
    bleach = windward(tex) * (1 - roof_cover(P) * 0.5)
    L.tint(SUN_BLEACHED, 0.3 * bleach)
    L.rough += 0.08 * bleach

    # Micro: orange-peel powder coat and roughness grain.
    L.height += 0.00006 * (noise3(P * 260, 21) - 0.5)
    L.rough += 0.06 * (noise3(P * 140, 22) - 0.5)
    # Meso: patchy coat thickness and cleaning history, readable within one 85 mm upright.
    L.albedo *= (0.96 + 0.08 * fbm3(P * 18, 3, 33))[:, None]
    L.rough += 0.16 * (fbm3(P * 2.2, 3, 32) - 0.5) + 0.08 * (fbm3(P * 22, 2, 34) - 0.5)

    # Meso: grime settled in recesses and joints.
    cavity = np.clip((1 - tex.ao) * 1.8 - 0.1, 0, 1) ** 1.2
    grime = cavity * (0.55 + 0.45 * fbm3(P * 9, 3, 23))
    L.tint(GRIME_DARK, 0.65 * grime)
    L.rough += 0.18 * grime
    L.height += 0.00006 * grime

    # Rain runs down exposed vertical faces.
    vertical = 1 - np.abs(N[:, 2])
    runs = streaks(tex, 0.005, 0.28, 24) * exposure * vertical
    L.tint(STREAK_DIRT, 0.5 * runs)
    L.rough += 0.2 * runs

    # Road spray: broken-up band, aggregate specks, salt bloom at the foot.
    L.tint(ROAD_MUD, 0.75 * splash * (0.55 + 0.45 * fbm3(P * 6, 3, 25)))
    L.rough += 0.25 * splash
    dark, light = splash_specks(tex, splash, 26)
    L.tint(GRIME_DARK, 0.8 * dark)
    L.tint(AGGREGATE, 0.7 * light)
    L.height += 0.00012 * (dark + light)
    dust = smoothstep(0.14, 0.0, z) * (0.5 + 0.5 * fbm3(P * 20, 2, 27))
    L.tint(SALT_DUST, 0.45 * dust)
    L.rough += 0.2 * dust

    # Hands and bodies: skin oil polishes, smudges slightly darken.
    polish = contact * (0.5 + 0.5 * fbm3(P * 14, 3, 28))
    L.rough -= 0.3 * polish
    L.albedo *= (1 - 0.08 * polish)[:, None]

    # Edge wear only where something physically wears the edge.
    drive = tex.convex ** 1.3 * np.clip(0.12 + contact * 1.1 + splash * 0.7 + exposure * 0.15, 0, 1.6)
    wear = drive * 0.55 + fbm3(P * 70, 3, 29) * 0.6
    chip = smoothstep(0.66, 0.72, wear)
    primer = smoothstep(0.6, 0.66, wear) - chip
    L.tint(PRIMER, 0.8 * primer)
    L.tint(BARE_METAL, chip)
    L.metal = np.maximum(L.metal, 0.9 * chip)
    L.mix_rough(0.42, chip)
    L.height -= 0.00008 * (chip + 0.5 * primer)

    scratches = micro_scratches(tex, 30) * np.clip(contact * 1.2 + splash * 0.8 + 0.12, 0, 1)
    L.tint(SCRATCH_LIGHT, 0.35 * scratches)
    L.rough += 0.12 * scratches
    L.height -= 0.00003 * scratches

    rust = np.clip(chip * smoothstep(0.5, 0.05, z) + primer * smoothstep(0.2, 0.0, z) * 0.5, 0, 1)
    rust *= smoothstep(0.35, 0.6, noise3(P * 120, 31))
    L.tint(RUST, 0.85 * rust)
    L.metal *= 1 - rust
    L.mix_rough(0.85, rust)

    add_bolts(L, frame_bolts(), rng)
    add_prints(L, [
        ((0.7425, -2.37, 1.25), (1, 0, 0), 6, (0.015, 0.14)),
        ((0.70, -2.3275, 1.18), (0, 1, 0), 5, (0.015, 0.14)),
        ((0.70, 2.3275, 1.22), (0, -1, 0), 5, (0.015, 0.14)),
        ((0.7425, 2.37, 1.3), (1, 0, 0), 6, (0.015, 0.14)),
        ((REAR_X + 0.0425, -0.79, 1.1), (1, 0, 0), 3, (0.015, 0.12)),
        ((REAR_X + 0.0425, 0.79, 1.15), (1, 0, 0), 3, (0.015, 0.12)),
    ], rng, rough_shift=-0.22)

    apply_decal(L, library, "shipping_label", (0.70, 2.3275, 1.42), (0, -1, 0), (0.07, 0.05), 0.12)
    apply_decal(L, library, "torn_paper", (0.7425, -2.37, 1.56), (1, 0, 0), (0.06, 0.08), -0.08)
    apply_decal(L, library, "round_sticker_remnant", (0.795, 2.47, 1.05), (1, 0, 0), (0.075, 0.075))
    apply_decal(L, library, "marker_tag", (REAR_X + 0.0425, 0.2, 1.03), (1, 0, 0), (0.12, 0.06), 0.05)

    L.wet = wet_mask(tex, exposure, splash)
    L.ao_channel = 0.3 + 0.7 * tex.ao
    return L.finish()


# ---------------------------------------------------------------------- roof

def weather_roof(tex, rng):
    P, N = tex.P, tex.N
    L = Layers(tex, ROOF_PAINT, 0.55)
    up = smoothstep(0.35, 0.85, N[:, 2])
    down = smoothstep(0.35, 0.85, -N[:, 2])
    side = np.clip(1 - up - down, 0, 1)

    L.albedo *= (0.85 + 0.3 * fbm3(P * 1.1, 4, 101))[:, None]
    L.height += 0.00005 * (noise3(P * 230, 102) - 0.5)
    L.rough += 0.05 * (noise3(P * 120, 103) - 0.5)

    # Upward faces collect what the air carries.
    deposit = up * (0.5 + 0.5 * fbm3(P * 2.5, 4, 104))
    L.tint(ATMOSPHERIC_DIRT, 0.75 * deposit)
    L.rough += 0.28 * deposit

    # Water drains toward the front and rear edges in shallow channels.
    channels = up * smoothstep(0.56, 0.8, fbm2(np.stack((P[:, 1] / 0.03, P[:, 0] / 0.6), axis=1), 3, 105))
    channels *= smoothstep(0.0, 0.5, np.abs(P[:, 0]))
    L.tint(STREAK_DIRT, 0.55 * channels)
    L.rough -= 0.1 * channels

    edge_distance = np.minimum(ROOF_HALF_X - np.abs(P[:, 0]), ROOF_HALF_Y - np.abs(P[:, 1]))
    damp = up * smoothstep(0.22, 0.0, edge_distance)
    algae = damp * smoothstep(0.5, 0.72, fbm3(P * 6, 4, 106))
    L.tint(ALGAE, 0.75 * algae)
    L.rough += 0.2 * algae
    L.height += 0.0004 * algae * noise3(P * 400, 107)

    for cx, cy in rng.uniform((-0.55, -2.2), (0.55, 2.2), (3, 2)):
        idx, u, v = tex.stamp((cx, cy, 2.52), (0, 0, 1), 0.06, depth=0.03)
        if not len(idx):
            continue
        r = np.hypot(u, v) / rng.uniform(0.012, 0.022) + 0.5 * (noise2(np.stack((u, v), axis=1) / 0.004, int(rng.integers(1e6))) - 0.5)
        splat = smoothstep(1.0, 0.55, r)
        L.tint((0.5, 0.49, 0.45), 0.85 * splat, idx)
        L.mix_rough(0.9, splat, idx)
        L.height[idx] += 0.0005 * splat

    drips = streaks(tex, 0.006, 0.08, 108) * side * np.exp(-(2.52 - P[:, 2]) / 0.14)
    L.tint(STREAK_DIRT, 0.6 * drips)
    L.rough += 0.12 * drips
    lip = side * np.exp(-((P[:, 2] - 2.3) / 0.02) ** 2) * (0.5 + 0.5 * noise3(P * 30, 109))
    L.tint(GRIME_DARK, 0.5 * lip)

    insects = down * smoothstep(0.975, 0.99, noise3(P * 350, 110))
    L.tint((0.01, 0.01, 0.01), 0.9 * insects)
    L.tint(STREAK_DIRT, 0.25 * down * smoothstep(0.55, 0.8, fbm3(P * 3, 3, 111)))

    cavity = np.clip((1 - tex.ao) * 1.5, 0, 1)
    L.tint(GRIME_DARK, 0.5 * cavity)
    L.rough += 0.15 * cavity
    edge_wear = tex.convex ** 1.5 * smoothstep(0.62, 0.76, fbm3(P * 50, 3, 112))
    L.tint(PRIMER, 0.45 * edge_wear)

    L.wet = np.clip(up + side * 0.75, 0, 1).astype(F)
    L.ao_channel = 0.35 + 0.65 * tex.ao
    return L.finish()


# --------------------------------------------------------------------- glass

def weather_glass(tex, library, rng):
    P = tex.P
    M = tex.M
    L = Layers(tex, GLASS_FILM, 0.035, alpha=0.026)
    s0, s1, t0, t1 = tex.panel_bounds()
    d_bottom = tex.t - t0
    d_top = t1 - tex.t
    d_side = np.minimum(tex.s - s0, s1 - tex.s)
    panels = {oid: name for oid, name in tex.names.items() if "Glass_" in name}

    L.alpha += 0.025 * (0.5 + 0.5 * fbm3(P * 0.8, 3, 201))

    # Build-up where glass meets the frame, heaviest along the bottom rail.
    bottom = np.exp(-d_bottom / 0.08) * (0.55 + 0.45 * fbm2(np.stack((tex.s * 12, tex.t * 40), axis=1), 3, 202))
    framed = np.exp(-np.minimum(d_side, d_top) / 0.025) * (0.6 + 0.4 * noise3(P * 25, 203))
    L.alpha += 0.3 * bottom + 0.09 * framed
    L.tint(GLASS_GRIME, np.clip(bottom * 1.3 + framed * 0.5, 0, 1))
    L.rough += 0.4 * bottom + 0.15 * framed

    splash = road_splash(tex, 204)
    dark, light = splash_specks(tex, splash, 205)
    L.alpha += 0.1 * splash + 0.25 * dark + 0.1 * light
    L.tint(GLASS_GRIME, np.clip(0.6 * splash + dark, 0, 1))
    L.rough += 0.35 * splash

    exposure = rain_exposure(tex)
    # Runs gather in patches where water sheets off the frame, not evenly across the pane.
    patches = smoothstep(0.4, 0.7, fbm2(np.stack((tex.s * 3.0, tex.t * 0.8), axis=1), 3, 207))
    runs = streaks(tex, 0.006, 0.35, 206) * exposure * patches * (0.35 + 0.65 * np.exp(-d_top / 0.5))
    L.alpha += 0.045 * runs
    L.rough += 0.22 * runs
    L.tint(MINERAL, 0.35 * runs)

    # People clean the reachable middle; the wipe leaves arcs at its edge.
    centre = smoothstep(0.1, 0.35, d_side) * smoothstep(0.35, 0.7, d_bottom) * smoothstep(0.08, 0.3, d_top)
    wiped = np.zeros(M, F)
    arcs = np.zeros(M, F)
    for oid in panels:
        sel = np.flatnonzero(tex.ids == oid)
        s_mid = 0.5 * (s0[sel[0]] + s1[sel[0]])
        t_centre = t0[sel[0]] + rng.uniform(0.8, 1.1)
        dist = np.hypot(tex.s[sel] - s_mid, tex.t[sel] - t_centre)
        reach = rng.uniform(0.45, 0.62)
        wiped[sel] = smoothstep(reach, reach - 0.12, dist)
        q = np.stack((tex.s[sel], tex.t[sel]), axis=1) * 6
        for k in range(5):
            radius = reach * rng.uniform(0.55, 1.0)
            band = np.exp(-((dist - radius) / max(0.0035, tex.texel_m * 0.8)) ** 2)
            arcs[sel] = np.maximum(arcs[sel], band * smoothstep(0.35, 0.6, noise2(q, 210 + k)))
    L.alpha *= 1 - 0.45 * wiped
    L.rough -= 0.12 * wiped * centre
    L.alpha += 0.02 * arcs
    L.rough += 0.18 * arcs

    wipe_scratches = micro_scratches(tex, 220, directions=5) * (0.35 + 0.65 * centre)
    L.rough += 0.3 * wipe_scratches
    L.alpha += 0.012 * wipe_scratches
    L.height -= 0.00002 * wipe_scratches

    for oid in panels:
        sel = np.flatnonzero(tex.ids == oid)
        for _ in range(int(rng.integers(2, 6))):
            a = np.array((rng.uniform(s0[sel[0]] + 0.05, s1[sel[0]] - 0.05), rng.uniform(t0[sel[0]] + 0.2, t1[sel[0]] - 0.2)), F)
            angle = rng.uniform(0, pi)
            b = a + rng.uniform(0.05, 0.3) * np.array((np.cos(angle), np.sin(angle)), F)
            cov = segment_coverage(tex.s[sel], tex.t[sel], a, b, rng.uniform(0.0007, 0.0014), tex.texel_m)
            L.rough[sel] += 0.4 * cov
            L.alpha[sel] += 0.07 * cov
            L.tint(MINERAL, 0.4 * cov, sel)
            L.height[sel] -= 0.00005 * cov

    # Dried drops leave mineral rings, gathered toward the lower middle.
    panel_ids = list(panels)
    for _ in range(160):
        oid = panel_ids[int(rng.integers(len(panel_ids)))]
        sel = np.flatnonzero(tex.ids == oid)
        sc = rng.uniform(s0[sel[0]] + 0.03, s1[sel[0]] - 0.03)
        tc = t0[sel[0]] + 0.05 + rng.beta(1.4, 2.6) * (t1[sel[0]] - t0[sel[0]] - 0.1)
        radius = rng.uniform(0.0015, 0.0045)
        near = sel[(np.abs(tex.s[sel] - sc) < 0.012) & (np.abs(tex.t[sel] - tc) < 0.012)]
        d = np.hypot(tex.s[near] - sc, tex.t[near] - tc)
        width = max(0.0006, tex.texel_m * 0.6)
        ring = np.exp(-((d - radius) / width) ** 2) * min(1.0, 0.0006 / width + 0.4) + 0.3 * smoothstep(radius, radius * 0.5, d)
        L.alpha[near] += 0.05 * ring
        L.rough[near] += 0.3 * ring
        L.tint(MINERAL, 0.5 * ring, near)

    plus_x = (1, 0, 0)
    minus_y = (0, -1, 0)
    for name, center, normal, count, spread in (
        ("Glass_Rear01", (REAR_GLASS_X, -1.0, 1.35), plus_x, 9, (0.12, 0.16)),
        ("Glass_Left", (0.45, -2.37, 1.25), minus_y, 11, (0.1, 0.18)),
        ("Glass_Right", (0.35, 2.37, 1.3), minus_y, 8, (0.1, 0.16)),
        ("Glass_Rear02", (REAR_GLASS_X, -0.55, 1.2), plus_x, 6, (0.1, 0.14)),
        ("Glass_Rear03", (REAR_GLASS_X, 2.1, 1.4), plus_x, 5, (0.08, 0.12)),
        ("Timetable_Cover", (-0.556, -1.47, 1.5), plus_x, 12, (0.12, 0.2)),
    ):
        add_prints(L, [(center, normal, count, spread)], rng, rough_shift=0.2, alpha_shift=0.03, darken=0.0)

    for center, normal, scale, drag in (
        ((0.25, -2.37, 1.35), minus_y, 1.0, 0.4),
        ((REAR_GLASS_X, -0.2, 1.25), plus_x, 1.0, 0.0),
        ((0.1, 2.37, 0.86), minus_y, 0.7, 0.2),
        ((REAR_GLASS_X, 1.95, 1.3), plus_x, 1.0, 0.8),
    ):
        idx, u, v = tex.stamp(center, normal, 0.16, depth=0.012)
        p = palm_print(u, v, scale, int(rng.integers(1e6)), drag)
        L.alpha[idx] += 0.022 * p
        L.rough[idx] += 0.12 * p

    # A removed notice left a cleaner rectangle, tape corners and a torn scrap.
    notice = tex.name_mask("Glass_Rear03") & (np.abs(P[:, 1] - 1.485) < 0.235) & (np.abs(P[:, 2] - 1.275) < 0.225)
    L.alpha[notice] *= 0.45
    L.rough[notice] -= 0.02
    apply_decal(L, library, "tape_residue", (REAR_GLASS_X, 1.27, 1.49), plus_x, (0.06, 0.022), 0.6)
    apply_decal(L, library, "tape_residue", (REAR_GLASS_X, 1.70, 1.49), plus_x, (0.06, 0.022), -0.6)
    apply_decal(L, library, "torn_paper", (REAR_GLASS_X, 1.28, 1.07), plus_x, (0.045, 0.035), 0.3)
    apply_decal(L, library, "adhesive_residue", (-0.2, -2.37, 1.48), minus_y, (0.09, 0.055), 0.04)
    apply_decal(L, library, "marker_tag", (0.35, 2.37, 0.62), minus_y, (0.14, 0.09), -0.1)
    apply_decal(L, library, "scratched_initials", (REAR_GLASS_X, 0.15, 1.05), plus_x, (0.12, 0.12), 0.08)

    # The photographed cover carries a pale scratched scribble over the red panel.
    cover = np.flatnonzero(tex.name_mask("Timetable_Cover"))
    scribble = np.zeros(len(cover), F)
    for _ in range(28):
        start = np.array((rng.normal(-1.40, 0.06), rng.normal(1.45, 0.12)), F)
        points = [start]
        for _ in range(int(rng.integers(2, 5))):
            points.append(points[-1] + rng.normal(0, 0.03, 2).astype(F))
        scribble = np.maximum(scribble, polyline_coverage(P[cover, 1], P[cover, 2], points, 0.0012, tex.texel_m))
    L.rough[cover] += 0.45 * scribble
    L.alpha[cover] += 0.16 * scribble
    L.tint((0.8, 0.8, 0.78), 0.6 * scribble, cover)

    L.alpha = np.clip(L.alpha, 0.0, 0.9)
    L.rough = np.clip(L.rough, 0.03, 0.9)
    L.ao_channel = np.ones(M, F)
    return L.finish()


# ---------------------------------------------------------------------- rail

def weather_rail(tex, rng):
    P, N = tex.P, tex.N
    L = Layers(tex, RAIL_RED, 0.44)
    horizontal = tex.name_mask("Horizontal")
    legs = (~horizontal).astype(F)
    horizontal_f = horizontal.astype(F)

    L.albedo *= (0.88 + 0.24 * fbm3(P * 2.0, 4, 301))[:, None]
    top = smoothstep(0.1, 0.8, N[:, 2])
    L.tint(RAIL_BLEACHED, 0.3 * top * (0.6 + 0.4 * fbm3(P * 3, 3, 302)))
    L.height += 0.00004 * (noise3(P * 260, 303) - 0.5)

    # People perch on the bar: polished, thinned paint, the odd bright spot.
    seat = horizontal_f * top * smoothstep(-1.62, -1.25, P[:, 1]) * smoothstep(0.70, 0.45, P[:, 1])
    polish = seat * (0.55 + 0.45 * fbm3(P * 8, 3, 304))
    L.mix_rough(0.2, 0.7 * polish)
    L.tint(RAIL_WORN, 0.8 * polish * smoothstep(0.55, 0.8, fbm3(P * 30, 3, 305)))
    bare = polish * smoothstep(0.8, 0.9, fbm3(P * 60, 3, 306))
    L.tint(BARE_METAL, bare)
    L.metal = np.maximum(L.metal, bare)
    L.mix_rough(0.35, bare)
    L.height -= 0.00008 * bare

    arc = np.arctan2(P[:, 2] - 0.76, P[:, 0] - 0.34) * 0.041
    lines = smoothstep(0.88, 0.97, noise2(np.stack((P[:, 1] / 0.09, arc / 0.0012), axis=1), 307))
    lines *= horizontal_f * (0.3 + 0.7 * seat)
    L.rough += 0.2 * lines
    L.tint(RAIL_WORN, 0.4 * lines)
    L.height -= 0.00003 * lines

    under = smoothstep(0.2, 0.8, -N[:, 2]) * horizontal_f
    L.tint(STREAK_DIRT, 0.35 * under)
    L.rough += 0.2 * under

    # Leg feet are unpainted galvanised sleeves, as in the photograph.
    sleeve = legs * smoothstep(0.195, 0.185, P[:, 2])
    L.tint(GALVANISED, sleeve)
    L.metal = np.maximum(L.metal, 0.8 * sleeve)
    L.mix_rough(0.5, sleeve)
    bloom = sleeve * smoothstep(0.6, 0.8, fbm3(P * 40, 3, 308))
    L.tint((0.48, 0.48, 0.45), 0.5 * bloom)
    L.rough += 0.3 * bloom
    L.metal -= 0.5 * bloom
    paint_edge = legs * np.exp(-((P[:, 2] - 0.19) / 0.012) ** 2) * (0.4 + 0.6 * noise3(P * 90, 309))
    L.tint(RUST, 0.6 * paint_edge)
    bleed = legs * smoothstep(0.19, 0.08, P[:, 2]) * streaks(tex, 0.004, 0.05, 310) * 0.6
    L.tint(RUST, bleed)

    kick = legs * smoothstep(0.12, 0.25, P[:, 2]) * smoothstep(0.55, 0.35, P[:, 2])
    scuffs = kick * smoothstep(0.62, 0.8, fbm2(np.stack((tex.s / 0.02, tex.t / 0.006), axis=1), 3, 311))
    L.tint((0.03, 0.03, 0.03), 0.7 * scuffs)
    L.mix_rough(0.6, scuffs)
    chips = kick * smoothstep(0.8, 0.86, fbm3(P * 80, 3, 312))
    L.tint(PRIMER, chips)
    L.height -= 0.00008 * chips

    splash = road_splash(tex, 313)
    L.tint(ROAD_MUD, 0.6 * splash * (0.5 + 0.5 * fbm3(P * 7, 3, 314)))
    L.rough += 0.25 * splash
    cavity = np.clip((1 - tex.ao) * 1.6, 0, 1)
    L.tint(GRIME_DARK, 0.5 * cavity)

    L.wet = wet_mask(tex, rain_exposure(tex), splash)
    L.ao_channel = 0.35 + 0.65 * tex.ao
    return L.finish()


# ---------------------------------------------------------- ground contact

def weather_ground(tex, library, rng):
    P = tex.P
    x, y = P[:, 0], P[:, 1]
    L = Layers(tex, (0.03, 0.028, 0.024), 0.85, alpha=0.0)

    # The sheltered footprint stays dry: a pale dust film that rain never rinses.
    under_roof = np.maximum(np.abs(x) - ROOF_HALF_X, np.abs(y) - ROOF_HALF_Y)
    sheltered = smoothstep(0.02, -0.12, under_roof) * (0.5 + 0.5 * fbm3(P * 2.5, 4, 408))
    L.tint((0.16, 0.15, 0.13), sheltered)
    L.alpha += 0.12 * sheltered
    L.mix_rough(0.95, sheltered)

    occlusion = np.clip(1 - tex.ao, 0, 1) ** 1.2
    L.tint((0.02, 0.018, 0.015), occlusion)
    L.alpha += 0.9 * occlusion

    # Drip lines under the roof edges, with splash scatter outward.
    for edge in (ROOF_HALF_X, -ROOF_HALF_X):
        wobble = 0.04 * (noise2(np.stack((y * 3, np.zeros(tex.M, F)), axis=1), 401) - 0.5)
        line = np.exp(-((x - edge - 0.03 * np.sign(edge) - wobble) / 0.05) ** 2) * smoothstep(2.75, 2.5, np.abs(y))
        damp = line * (0.55 + 0.45 * fbm3(P * 4, 3, 402))
        scatter = smoothstep(0.14, 0.0, np.abs(x - edge) - 0.02) * smoothstep(0.8, 0.9, noise3(P * 140, 403))
        L.alpha += 0.35 * damp + 0.3 * scatter
        L.mix_rough(0.3, damp)
        L.tint((0.018, 0.02, 0.016), damp)

    # Leaves, grit and litter blow in and collect against the rear panel.
    debris = np.exp(-((x - REAR_X - 0.04) / 0.09) ** 2) * (np.abs(y) < 2.4) * (0.45 + 0.55 * fbm3(P * 8, 3, 404))
    L.tint((0.02, 0.018, 0.013), debris)
    L.alpha += 0.55 * debris
    L.mix_rough(0.95, debris)

    for side in (-1, 1):
        r = np.hypot(x + 0.78, y - 2.42 * side)
        moss = smoothstep(0.22, 0.05, r) * smoothstep(0.45, 0.65, fbm3(P * 10, 4, 405 + side))
        L.tint(ALGAE, moss)
        L.alpha += 0.55 * moss

    feet = [(REAR_X, py) for py in POST_YS] + [(0.70, -2.37), (0.70, 2.37), (0.34, -1.62), (0.34, 0.70)]
    for fx, fy in feet:
        r = np.hypot(x - fx, y - fy)
        # Dirt and damp trapped against each foot, then rust run-off from the fixing.
        trapped = smoothstep(0.22, 0.03, r) * (0.55 + 0.45 * fbm3(P * 30, 3, 406))
        L.tint((0.012, 0.011, 0.009), trapped)
        L.alpha += 0.8 * trapped
        L.mix_rough(0.7, trapped)
        halo = smoothstep(0.07, 0.012, r) * smoothstep(0.35, 0.75, fbm3(P * 45, 3, 407))
        L.tint(RUST, 0.6 * halo)
        L.alpha += 0.25 * halo

    # The advert plinth, as photographed: the ground around it stays damp, and grit
    # heaps against its road-facing end and spills onto the pavement.
    px, py = ADVERT_PLINTH_CENTRE
    plinth = np.maximum(np.abs(x - px) - ADVERT_PLINTH_HALF[0], np.abs(y - py) - ADVERT_PLINTH_HALF[1])
    damp_band = smoothstep(0.35, 0.0, plinth) * (0.5 + 0.5 * fbm3(P * 6, 3, 409))
    L.tint((0.015, 0.014, 0.011), damp_band)
    L.alpha += 0.55 * damp_band
    L.mix_rough(0.45, damp_band)
    heap = smoothstep(0.3, 0.0, np.hypot(np.maximum(x - px - ADVERT_PLINTH_HALF[0], 0) / 0.8, plinth))
    heap *= smoothstep(px, px + 0.5, x)
    grit = heap * smoothstep(0.35, 0.65, noise3(P * 180, 410))
    L.tint((0.3, 0.28, 0.24), grit)
    L.alpha += 0.8 * grit
    L.mix_rough(1.0, grit)

    for _ in range(7):
        gx, gy = rng.uniform(0.0, 1.2), rng.uniform(-2.2, 2.2)
        size = rng.uniform(0.02, 0.03)
        apply_decal(L, library, "chewing_gum", (gx, gy, 0.004), (0, 0, 1), (size, size), rng.uniform(0, pi), depth=0.02)

    border = np.minimum.reduce((x + 1.25, 1.35 - x, y + 2.95, 2.95 - y))
    L.alpha *= smoothstep(0.0, 0.18, border)
    L.alpha = np.clip(L.alpha, 0, 0.8)
    L.ao_channel = np.ones(tex.M, F)
    return L.finish()


# ------------------------------------------------------------- map writing

def downsample_height(height, factor):
    if factor == 1:
        return height
    h, w = height.shape
    return height.reshape(h // factor, factor, w // factor, factor).mean(axis=(1, 3))


def write_maps(L, stem, normal_size, alpha_source, normal_strength=1.0):
    tex = L.tex
    albedo = srgb_encode(L.albedo)
    fourth = L.alpha if alpha_source == "alpha" else WET_FLOOR + (1 - WET_FLOOR) * L.wet
    base = tex.grid(np.column_stack((albedo, fourth)), fill=(*albedo.mean(axis=0), float(fourth.mean())))
    orm = tex.grid(np.column_stack((L.ao_channel, L.rough, L.metal)), fill=(1.0, float(L.rough.mean()), 0.0))
    images = {
        "base": save_rgba(TEXTURE_DIR / f"{stem}-basecolor.png", base),
        "orm": save_rgba(TEXTURE_DIR / f"{stem}-orm.png", orm),
    }
    images["orm"].colorspace_settings.name = "Non-Color"
    if normal_size:
        height = tex.grid(L.height, fill=0.0)
        factor = tex.shape[1] // normal_size
        normal = height_to_normal(downsample_height(height, factor), tex.texel_m * factor, normal_strength)
        images["normal"] = save_rgba(TEXTURE_DIR / f"{stem}-normal.png", normal)
        images["normal"].colorspace_settings.name = "Non-Color"
    coverage = {
        "texels": tex.M,
        "texel_mm": round(tex.texel_m * 1000, 2),
        "rough_mean": round(float(L.rough.mean()), 3),
        "metal_gt_half": round(float((L.metal > 0.5).mean()) * 100, 2),
    }
    print(f"[texture-pass] {stem}: {coverage}")
    return images


def build_sign_atlas():
    size = SIGN_ATLAS
    paint = srgb_decode(np.array((0.2, 0.235, 0.21), F))
    base = np.tile(paint, (size, size, 1)).astype(F)
    rough = np.full((size, size), 0.62, F)
    height = np.zeros((size, size), F)

    def place(rect, rgb, r, h):
        x, y, w, hgt = rect
        base[y:y + hgt, x:x + w] = rgb
        rough[y:y + hgt, x:x + w] = r
        height[y:y + hgt, x:x + w] = h

    timetable, _ = artwork.timetable_artwork(ARTWORK_DIR)
    place(TIMETABLE_RECT, *artwork.age_timetable(timetable))
    no_smoking, _ = artwork.no_smoking_artwork(ARTWORK_DIR)
    place(NO_SMOKING_RECT, *artwork.age_no_smoking(no_smoking))
    live, ghost, _ = artwork.stop_number_artwork(ARTWORK_DIR)
    place(NUMBER_RECT, *artwork.age_stop_number(live, ghost))

    rgba = np.dstack((srgb_encode(base), np.full((size, size), WET_FLOOR, F)))
    orm = np.dstack((np.ones((size, size), F), np.clip(rough, 0, 1), np.zeros((size, size), F)))
    normal = height_to_normal(downsample_height(height, 4), 0.00056 * 4, 2.0)
    return {
        "base": save_rgba(TEXTURE_DIR / "signage-basecolor.png", rgba),
        "orm": save_rgba(TEXTURE_DIR / "signage-orm.png", downsample_orm(orm, 4)),
        "normal": save_rgba(TEXTURE_DIR / "signage-normal.png", normal),
    }


def downsample_orm(orm, factor):
    h, w = orm.shape[:2]
    return orm.reshape(h // factor, factor, w // factor, factor, 3).mean(axis=(1, 3))


def build_advert_maps():
    art, _ = artwork.advert_artwork(ARTWORK_DIR)
    lin = artwork.age_advert(art)
    w, h = ADVERT_SIZE
    rgba = np.dstack((srgb_encode(lin), np.full((h, w), WET_FLOOR, F)))
    base = save_rgba(TEXTURE_DIR / "advert-basecolor.png", rgba)
    orm = save_rgba(TEXTURE_DIR / "advert-orm.png", np.dstack((np.ones((64, 64), F), np.full((64, 64), 0.3, F), np.zeros((64, 64), F))))
    orm.colorspace_settings.name = "Non-Color"
    return {"base": base, "orm": orm}


def build_light_maps():
    lin, rough = artwork.light_diffuser(LIGHT_SIZE)
    rgba = np.dstack((srgb_encode(lin), np.full((LIGHT_SIZE, LIGHT_SIZE), WET_FLOOR, F)))
    base = save_rgba(TEXTURE_DIR / "light-basecolor.png", rgba)
    orm = np.dstack((np.ones_like(rough), rough, np.zeros_like(rough)))
    orm_image = save_rgba(TEXTURE_DIR / "light-orm.png", downsample_orm(orm, 2))
    orm_image.colorspace_settings.name = "Non-Color"
    return {"base": base, "orm": orm_image}


def load_decal_library():
    atlas, meta = artwork.build_urban_decal_library(
        DECAL_DIR / "urban-decal-library.png", DECAL_DIR / "urban-decal-library.json")
    return atlas, meta


# -------------------------------------------------------------------- export

def export_glb(path, *roots):
    path.parent.mkdir(parents=True, exist_ok=True)
    shelter_geometry.select_roots(*roots)
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_image_format="WEBP",
        export_image_quality=88,
    )


BAKE_CACHE = None


def cached_bake(stem, objects, width, height, ao_distance):
    """Bake buffers, reusing a cache from --bake-cache when iterating on weathering.

    The cache is only valid while geometry and unwrapping are unchanged.
    """
    path = Path(BAKE_CACHE) / f"{stem}-{width}x{height}.npz" if BAKE_CACHE else None
    if path and path.exists():
        data = np.load(path, allow_pickle=True)
        return data["position"], data["normal"], data["extra"], data["names"].item()
    position, normal, extra, names = bake_buffers(objects, width, height, ao_distance=ao_distance)
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(path, position=position, normal=normal, extra=extra, names=np.array(names, dtype=object))
    return position, normal, extra, names


def texture_stage():
    TEXTURE_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(3309_0083)
    shelter_geometry.clear_scene()
    shelter_geometry.configure_scene()
    mats = shelter_geometry.create_materials()
    shelter = shelter_geometry.build_shelter(mats)
    trolley = shelter_geometry.build_trolley(mats, detailed=True)
    trolley.location = (1.25, 0.10, 0)
    trolley.rotation_euler[2] = -0.08
    add_texture_pass_geometry(shelter, mats)

    groups = {key: meshes_with(shelter, mats[key]) for key in ("dark", "roof", "glass", "rail", "sign", "advert", "light", "ground")}

    unwrap_atlas(groups["dark"], importance={"Roof_Underside": 0.45, "AdvertHousing_Outer": 0.6})
    unwrap_atlas(groups["roof"])
    unwrap_atlas(groups["glass"], importance={"AdvertGlass": 0.55})
    unwrap_atlas(groups["rail"])
    atlas = (SIGN_ATLAS, SIGN_ATLAS)
    for obj in groups["sign"]:
        if "Timetable" in obj.name:
            planar_uv(obj, TIMETABLE_RECT, atlas, 1, 2)
        elif "NoSmoking" in obj.name:
            planar_uv(obj, NO_SMOKING_RECT, atlas, 1, 2)
        else:
            planar_uv(obj, NUMBER_RECT, atlas, 1, 2, lambda poly: poly.normal.x > 0.7, PAINT_RECT)
    for obj in groups["advert"]:
        planar_uv(obj, (0, 0, *ADVERT_SIZE), ADVERT_SIZE, 0, 1)
    for obj in groups["light"]:
        planar_uv(obj, (10, 10, 492, 360), (LIGHT_SIZE, LIGHT_SIZE), 0, 1,
                  lambda poly: poly.normal.z < -0.5, (10, 400, 492, 100))
    planar_uv(groups["ground"][0], (0, 0, 1024, 2048), (1024, 2048), 0, 1)

    library = load_decal_library()
    temp_ground = add_temporary_ground()
    weathered = {}
    # Normal strength compensates for texel size: physically scaled sub-millimetre
    # relief is otherwise flatter than one 8-bit normal step at 2-5 mm per texel.
    for key, stem, weather, alpha_source, strength in (
        ("dark", "frame", lambda t: weather_frame(t, library, rng), "wet", 4.0),
        ("roof", "roof", lambda t: weather_roof(t, rng), "wet", 5.0),
        ("glass", "glass", lambda t: weather_glass(t, library, rng), "alpha", 20.0),
        ("rail", "rail", lambda t: weather_rail(t, rng), "wet", 5.0),
        ("ground", "ground", lambda t: weather_ground(t, library, rng), "alpha", 1.0),
    ):
        width, height, normal_size = ATLAS_SIZES[stem]
        distance = 0.35 if stem == "ground" else 0.25
        started = time.time()
        position, normal, extra, names = cached_bake(stem, groups[key], width, height, distance)
        print(f"[texture-pass] {stem}: baked buffers in {time.time() - started:.0f}s", flush=True)
        tex = Texels(position, normal, extra, names)
        weathered[key] = write_maps(weather(tex), stem, normal_size, alpha_source, strength)
        print(f"[texture-pass] {stem}: weathered in {time.time() - started:.0f}s total", flush=True)
    bpy.data.objects.remove(temp_ground, do_unlink=True)

    weathered["sign"] = build_sign_atlas()
    weathered["advert"] = build_advert_maps()
    weathered["light"] = build_light_maps()

    finals = {
        "dark": ("MAT_BusStop_DarkMetal", {}),
        "roof": ("MAT_BusStop_Roof", {}),
        "glass": ("MAT_BusStop_Glass", {"blend_alpha": True}),
        "rail": ("MAT_BusStop_RedRail", {}),
        "sign": ("MAT_BusStop_Signage", {}),
        "advert": ("MAT_BusStop_Advert", {"emission_strength": 3.0}),
        "light": ("MAT_BusStop_Light", {"emission_strength": 2.0}),
        "ground": ("MAT_BusStop_GroundContact", {"blend_alpha": True}),
    }
    for key, (name, options) in finals.items():
        maps = weathered[key]
        mat = mats[key]
        mat.name = name
        build_pbr_material(mat, maps["base"], maps.get("orm"), maps.get("normal"), **options)

    for image in bpy.data.images:
        if image.filepath:
            image.filepath = bpy.path.relpath(image.filepath, start=str(TEXTURED_BLEND.parent))
    shelter_geometry.save(TEXTURED_BLEND)
    export_glb(SHELTER_GLB, shelter)
    export_glb(REFERENCE_GLB, shelter, trolley)
    print(f"Textured blend: {TEXTURED_BLEND}")
    print(f"Shelter GLB: {SHELTER_GLB} ({SHELTER_GLB.stat().st_size / 1e6:.1f} MB)")
    print(f"Combined game GLB: {REFERENCE_GLB} ({REFERENCE_GLB.stat().st_size / 1e6:.1f} MB)")


# ------------------------------------------------------------------ renders

def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def stage_material(name, texture, scale, roughness, tint=(1, 1, 1)):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    shader = nt.nodes["Principled BSDF"]
    coords = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (scale, scale, scale)
    image = nt.nodes.new("ShaderNodeTexImage")
    image.image = load_image(WORLD_TEXTURES / texture)
    multiply = nt.nodes.new("ShaderNodeMix")
    multiply.data_type = "RGBA"
    multiply.blend_type = "MULTIPLY"
    multiply.inputs["Factor"].default_value = 1.0
    multiply.inputs["B"].default_value = (*tint, 1.0)
    nt.links.new(coords.outputs["Object"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], image.inputs["Vector"])
    nt.links.new(image.outputs["Color"], multiply.inputs["A"])
    nt.links.new(multiply.outputs["Result"], shader.inputs["Base Color"])
    shader.inputs["Roughness"].default_value = roughness
    return mat


def build_render_stage():
    stage = []
    pavement = stage_material("STAGE_Pavement", "pavement-weathered-overhaul.png", 0.6, 0.85)
    road = stage_material("STAGE_Road", "asphalt-wet-overhaul.png", 0.35, 0.8)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(-2.2, 0, 0))
    plane = bpy.context.object
    plane.scale = (9.8, 16, 1)
    plane.data.materials.append(pavement)
    stage.append(plane)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(2.8, 0, -0.06))
    kerb = bpy.context.object
    kerb.scale = (0.16, 16, 0.12)
    kerb.data.materials.append(pavement)
    stage.append(kerb)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(8.9, 0, -0.12))
    carriageway = bpy.context.object
    carriageway.scale = (12, 16, 1)
    carriageway.data.materials.append(road)
    stage.append(carriageway)
    return stage, pavement, road


def set_world(color, strength):
    world = bpy.context.scene.world
    world.use_nodes = True
    background = world.node_tree.nodes["Background"]
    background.inputs["Color"].default_value = (*color, 1.0)
    background.inputs["Strength"].default_value = strength


def add_light(kind, location, target, energy, color, size=0.05, spot=radians(60), blend=0.25):
    data = bpy.data.lights.new(f"TEMP_{kind}", kind)
    data.energy = energy
    data.color = color
    data.shadow_soft_size = size
    if kind == "SPOT":
        data.spot_size = spot
        data.spot_blend = blend
    if kind == "SUN":
        data.angle = radians(1.2)
    obj = bpy.data.objects.new(f"TEMP_{kind}", data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    point_at(obj, target)
    return obj


def add_night_backdrop():
    items = []
    mat_cache = {}
    for i, (y, z, color, strength) in enumerate((
        (-4.5, 1.6, (1.0, 0.55, 0.2), 6), (-1.5, 2.4, (1.0, 0.8, 0.55), 4), (1.2, 1.2, (1.0, 0.6, 0.25), 5),
        (3.8, 2.0, (0.75, 0.85, 1.0), 5), (5.5, 1.4, (1.0, 0.25, 0.55), 4), (-6.5, 2.8, (0.8, 0.9, 1.0), 3),
    )):
        key = (color, strength)
        if key not in mat_cache:
            mat = bpy.data.materials.new(f"TEMP_Backdrop_{i}")
            mat.use_nodes = True
            nt = mat.node_tree
            nt.nodes.clear()
            emission = nt.nodes.new("ShaderNodeEmission")
            emission.inputs["Color"].default_value = (*color, 1)
            emission.inputs["Strength"].default_value = strength
            out = nt.nodes.new("ShaderNodeOutputMaterial")
            nt.links.new(emission.outputs[0], out.inputs["Surface"])
            mat_cache[key] = mat
        bpy.ops.mesh.primitive_plane_add(size=1, location=(-9.0, y, z), rotation=(0, pi / 2, 0))
        panel = bpy.context.object
        panel.name = f"TEMP_Backdrop_{i}"
        panel.scale = (0.9, 0.6, 1)
        panel.data.materials.append(mat_cache[key])
        items.append(panel)
    return items


def clear_temporary():
    for obj in list(bpy.data.objects):
        if obj.name.startswith("TEMP_") or obj.name.startswith("Validation_Camera"):
            bpy.data.objects.remove(obj, do_unlink=True)


def make_wet(pavement, road):
    """Validation-only wet variant mirroring the runtime wet shader."""
    for mat in bpy.data.materials:
        if not mat.use_nodes or "Base Color" not in mat.node_tree.nodes:
            continue
        nt = mat.node_tree
        shader = nt.nodes["Principled BSDF"]
        base = nt.nodes["Base Color"]
        if mat.name == "MAT_BusStop_Glass":
            noise = nt.nodes.new("ShaderNodeTexNoise")
            coords = nt.nodes.new("ShaderNodeTexCoord")
            mapping = nt.nodes.new("ShaderNodeMapping")
            mapping.inputs["Scale"].default_value = (140, 140, 3)
            nt.links.new(coords.outputs["Object"], mapping.inputs["Vector"])
            nt.links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
            ramp = nt.nodes.new("ShaderNodeMapRange")
            ramp.inputs["From Min"].default_value = 0.55
            ramp.inputs["From Max"].default_value = 0.75
            ramp.inputs["To Min"].default_value = 1.0
            ramp.inputs["To Max"].default_value = 0.1
            nt.links.new(noise.outputs["Fac"], ramp.inputs["Value"])
            scale = nt.nodes.new("ShaderNodeMath")
            scale.operation = "MULTIPLY"
            nt.links.new(nt.nodes["ORM Split"].outputs["Green"], scale.inputs[0])
            nt.links.new(ramp.outputs["Result"], scale.inputs[1])
            nt.links.new(scale.outputs[0], shader.inputs["Roughness"])
            if "Glass Reflection" in nt.nodes:
                nt.links.new(scale.outputs[0], nt.nodes["Glass Reflection"].inputs["Roughness"])
            continue
        if "ORM Split" not in nt.nodes or mat.surface_render_method == "BLENDED":
            continue
        rough = nt.nodes["ORM Split"].outputs["Green"]
        wet = nt.nodes.new("ShaderNodeMapRange")
        wet.inputs["From Min"].default_value = WET_FLOOR
        wet.inputs["To Max"].default_value = 0.85
        nt.links.new(base.outputs["Alpha"], wet.inputs["Value"])
        rough_mix = nt.nodes.new("ShaderNodeMix")
        rough_mix.data_type = "FLOAT"
        nt.links.new(wet.outputs[0], rough_mix.inputs["Factor"])
        nt.links.new(rough, rough_mix.inputs["A"])
        rough_mix.inputs["B"].default_value = 0.07
        nt.links.new(rough_mix.outputs["Result"], shader.inputs["Roughness"])
        darken = nt.nodes.new("ShaderNodeMath")
        darken.operation = "MULTIPLY"
        nt.links.new(wet.outputs[0], darken.inputs[0])
        nt.links.new(rough, darken.inputs[1])
        color_mix = nt.nodes.new("ShaderNodeMix")
        color_mix.data_type = "RGBA"
        color_mix.blend_type = "MULTIPLY"
        nt.links.new(darken.outputs[0], color_mix.inputs["Factor"])
        nt.links.new(base.outputs["Color"], color_mix.inputs["A"])
        color_mix.inputs["B"].default_value = (0.55, 0.55, 0.55, 1)
        nt.links.new(color_mix.outputs["Result"], shader.inputs["Base Color"])
    for mat, value in ((pavement, 0.12), (road, 0.06)):
        mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = value
        mix = next(n for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeMix")
        mix.inputs["B"].default_value = (0.55, 0.55, 0.58, 1)


def validation_glass():
    """Match the runtime glass in validation renders.

    A Principled BSDF's alpha scales its reflections too, so thin baked grime
    alpha makes the glass vanish.  Rebuild it as the runtime shader behaves:
    film and grime blend by alpha, specular reflection adds at full strength.
    """
    mat = bpy.data.materials["MAT_BusStop_Glass"]
    nt = mat.node_tree
    grime = nt.nodes["Principled BSDF"]
    output = next(node for node in nt.nodes if node.bl_idname == "ShaderNodeOutputMaterial")
    base = nt.nodes["Base Color"]
    for link in list(grime.inputs["Alpha"].links):
        nt.links.remove(link)
    grime.inputs["Specular IOR Level"].default_value = 0.0
    reflection = nt.nodes.new("ShaderNodeBsdfPrincipled")
    reflection.name = "Glass Reflection"
    reflection.inputs["Base Color"].default_value = (0, 0, 0, 1)
    reflection.inputs["IOR"].default_value = 1.52
    nt.links.new(nt.nodes["ORM Split"].outputs["Green"], reflection.inputs["Roughness"])
    if grime.inputs["Normal"].links:
        nt.links.new(grime.inputs["Normal"].links[0].from_socket, reflection.inputs["Normal"])
    clear = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(base.outputs["Alpha"], mix.inputs["Fac"])
    nt.links.new(clear.outputs[0], mix.inputs[1])
    nt.links.new(grime.outputs[0], mix.inputs[2])
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(mix.outputs[0], add.inputs[0])
    nt.links.new(reflection.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], output.inputs["Surface"])


NIGHT_WORLD = ((0.0025, 0.004, 0.012), 1.0)
LED = (0.8, 0.9, 1.0)
SODIUM = (1.0, 0.56, 0.2)


def rig(name):
    scene = bpy.context.scene
    if name == "day":
        set_world((0.42, 0.52, 0.7), 0.9)
        add_light("SUN", (4, -6, 8), (0, 0, 0), 3.2, (1.0, 0.96, 0.9))
        return
    if name == "overcast":
        set_world((0.52, 0.54, 0.57), 1.6)
        return
    set_world(*NIGHT_WORLD)
    add_night_backdrop()
    if name == "night":
        add_light("POINT", (5.5, -8.0, 5.5), (0, 0, 1), 900, SODIUM, size=0.2)
    elif name in ("led", "sodium", "wet", "led_low"):
        add_light("SPOT", (2.6, -6.2, 5.8), (0, -0.6, 1.0), 4500, LED if name != "sodium" else SODIUM, size=0.04, spot=radians(75))
        if name == "led_low":
            add_light("SPOT", (3.0, -1.4, 0.6), (0.6, -2.2, 0.2), 250, (1.0, 0.8, 0.6), spot=radians(50))
        if name == "wet":
            add_light("AREA", (5.5, 3.5, 1.6), (0, 0, 1.2), 500, (1.0, 0.25, 0.6), size=1.5)
    elif name == "glass_rake":
        # Nearly parallel to the left return glass, so prints and film catch the light.
        add_light("SPOT", (1.4, -2.15, 1.9), (-0.5, -2.37, 1.1), 1500, LED, size=0.02, spot=radians(45))
    elif name == "frame_rake":
        # Rakes down the upright's road-facing face, from below the roof shell.
        add_light("SPOT", (0.86, -2.37, 2.1), (0.745, -2.37, 0.5), 900, LED, size=0.02, spot=radians(30))
    elif name == "grazing":
        # Inside the shelter, in front of the advert housing, skimming the rear glass.
        add_light("SPOT", (-0.6, 2.05, 1.35), (-0.66, -2.2, 1.2), 1600, LED, size=0.01, spot=radians(25))
    elif name == "contact_right":
        add_light("SPOT", (3.0, 1.2, 1.2), (0.3, 2.4, 0.1), 700, LED, size=0.03, spot=radians(45))
    elif name == "macro_rake":
        add_light("SPOT", (-0.62, 1.4, 0.4), (-0.66, 0.6, 0.35), 260, LED, size=0.01, spot=radians(30))


def render_stage():
    bpy.ops.wm.open_mainfile(filepath=str(TEXTURED_BLEND))
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.use_raytracing = True
    scene.eevee.taa_render_samples = 64
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 960
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "None"
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    validation_glass()
    # Validation only: EEVEE drops the thin blended ground-contact decal over the
    # opaque stage plane, so render the same coverage dithered.
    bpy.data.materials["MAT_BusStop_GroundContact"].surface_render_method = "DITHERED"
    _, pavement, road = build_render_stage()
    shelter = bpy.data.objects["PRESTON_BUS_SHELTER"]

    views = [
        ("01-neutral-daylight", (8.2, -5.6, 2.5), (0, 0, 1.15), 40, "day"),
        ("02-overcast-daylight", (8.2, -5.6, 2.5), (0, 0, 1.15), 40, "overcast"),
        ("03-clean-night", (7.4, 1.6, 1.7), (0, 0.1, 1.2), 40, "night"),
        ("04-hard-led-streetlight", (6.6, -4.2, 1.75), (0, -0.3, 1.15), 42, "led"),
        ("05-warm-streetlight", (6.6, -4.2, 1.75), (0, -0.3, 1.15), 42, "sodium"),
        ("07-closeup-glass", (0.35, -1.45, 1.35), (0.05, -2.37, 1.25), 38, "glass_rake"),
        ("08-closeup-frame", (1.35, -2.05, 1.25), (0.74, -2.37, 1.15), 50, "frame_rake"),
        ("09-closeup-lower-grime", (1.7, -1.1, 0.42), (0.55, -2.1, 0.25), 32, "led_low"),
        ("10-grazing-light-test", (1.6, 1.9, 1.75), (-0.69, -0.8, 1.2), 40, "grazing"),
        ("11-gameplay-camera-distance", None, None, None, "led"),
        ("12-extreme-closeup", (-0.45, 0.62, 0.52), (-0.66, 0.79, 0.34), 70, "macro_rake"),
        ("13-ground-contact", (2.2, 1.2, 0.55), (0.4, 2.3, 0.12), 32, "contact_right"),
        ("06-wet-night", (6.6, -4.2, 1.75), (0, -0.3, 1.15), 42, "wet"),
    ]
    for name, location, target, lens, rig_name in views:
        clear_temporary()
        if rig_name == "wet":
            make_wet(pavement, road)
        rig(rig_name)
        camera_data = bpy.data.cameras.new("Validation_Camera")
        camera = bpy.data.objects.new("Validation_Camera", camera_data)
        scene.collection.objects.link(camera)
        shelter.scale = (1, 1, 1)
        if location is None:
            # Game camera: 6.8 m behind the player, 0.31 rad pitch, 50 deg vertical FOV,
            # with the shelter at its runtime 1.3x scale.
            shelter.scale = (1.3, 1.3, 1.3)
            player = Vector((3.2, 0.8, 1.5))
            camera.location = player + Vector((6.8 * np.cos(0.31), 0, 6.8 * np.sin(0.31)))
            camera_data.sensor_fit = "VERTICAL"
            camera_data.angle_y = radians(50)
            point_at(camera, player)
        else:
            camera.location = location
            camera_data.lens = lens
            point_at(camera, target)
        camera_data.clip_start = 0.01
        scene.camera = camera
        scene.render.filepath = str(RENDER_DIR / f"{name}.png")
        bpy.ops.render.render(write_still=True)
    print(f"Validation renders: {RENDER_DIR}")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    stage = argv[argv.index("--stage") + 1] if "--stage" in argv else "all"
    global BAKE_CACHE
    BAKE_CACHE = argv[argv.index("--bake-cache") + 1] if "--bake-cache" in argv else None
    if stage in ("all", "textures"):
        texture_stage()
    if stage in ("all", "renders"):
        render_stage()


if __name__ == "__main__":
    main()
