"""Harpurhey municipal streetlight family: build, texture, export and night-test.

Four fresh assets (geometry in streetlightGeometry.py), each exported as its own
GLB with three LODs and a `LightEmitter` empty at the real light source:

  public/assets/models/streetlight-warm-old-01.glb
  public/assets/models/streetlight-led-modern-01.glb
  public/assets/models/streetlight-curved-01.glb
  public/assets/models/streetlight-weathered-01.glb

The fixture is the physical object only.  No light cones or pools are modelled;
the game attaches its own light at `LightEmitter`.

Run from the repository root:

  /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \\
    --python blender/scripts/createStreetlights.py -- --stage clay|build|renders|all

  clay     untextured LOD0 line-up against a grey sky (proportion check)
  build    bake + author textures, save a .blend per asset, export the GLBs
  renders  night and grey-sky test renders from the saved .blend files
"""

import sys
from math import radians
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import streetlightGeometry as geo  # noqa: E402
from surfaceWeathering import (  # noqa: E402
    F,
    Layers,
    Texels,
    bake_buffers,
    fbm2,
    fbm3,
    gltf_output_group,
    height_to_normal,
    micro_scratches,
    noise2,
    noise3,
    save_rgba,
    smoothstep,
    srgb_encode,
    streaks,
    unwrap_atlas,
)

PROJECT_ROOT = SCRIPT_DIR.parents[1]
MODEL_DIR = PROJECT_ROOT / "public" / "assets" / "models"
SOURCE_DIR = PROJECT_ROOT / "blender" / "source" / "streetlights"
TEXTURE_DIR = SOURCE_DIR / "textures"
RENDER_DIR = PROJECT_ROOT / "renders" / "streetlights"

ATLAS = {0: 1024, 1: 256}

# Light colours (sRGB) and strengths.  GLB values are what three.js reads;
# render values are physical-ish for Cycles.  The game recolours per lamp.
LAMP = {
    "sox": dict(color=(1.0, 0.47, 0.06), kelvin=1800),
    "son_small": dict(color=(1.0, 0.60, 0.25), kelvin=2100),
    "son_bowl": dict(color=(1.0, 0.57, 0.22), kelvin=2000),
    "led": dict(color=(1.0, 0.90, 0.80), kelvin=4000),
}
GLB_STRENGTH = dict(emitter=6.0, glass=0.9, reflector=0.35, spill=1.0)
RENDER_STRENGTH = dict(emitter=60.0, glass=0.0, reflector=0.0, spill=0.0)


def srgb_to_linear(c):
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


# ---------------------------------------------------------------- scenes

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def new_collection(name):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def principled(name, color=(0.5, 0.5, 0.5), rough=0.5, metal=0.0, alpha=1.0, emission=None, strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    shader.inputs["Base Color"].default_value = (*srgb_to_linear(color), 1.0)
    shader.inputs["Roughness"].default_value = rough
    shader.inputs["Metallic"].default_value = metal
    if alpha < 1.0:
        shader.inputs["Alpha"].default_value = alpha
        mat.surface_render_method = "BLENDED"
    if emission is not None:
        shader.inputs["Emission Color"].default_value = (*srgb_to_linear(emission), 1.0)
        shader.inputs["Emission Strength"].default_value = strength
    return mat


def shared_materials(spec, strengths):
    """The small untextured materials.  Names are stable across all four GLBs so
    the game can share one instance of each."""
    lamp = LAMP[spec.kind]
    sodium = spec.kind != "led"
    mats = {
        geo.REFLECTOR: principled("SL_Reflector", (0.72, 0.72, 0.70), 0.28, 1.0,
                                  emission=lamp["color"], strength=strengths["reflector"]),
        geo.GLASS: (principled("SL_Glass_Prismatic", (0.86, 0.84, 0.78), 0.32, 0.0, alpha=0.42,
                               emission=lamp["color"], strength=strengths["glass"])
                    if sodium else
                    principled("SL_Glass_Clear", (0.80, 0.82, 0.84), 0.08, 0.0, alpha=0.14)),
        geo.EMITTER: principled({"sox": "SL_Emitter_SOX", "son_small": "SL_Emitter_SON",
                                 "son_bowl": "SL_Emitter_SON", "led": "SL_Emitter_LED"}[spec.kind],
                                lamp["color"], 0.3, 0.0, emission=lamp["color"], strength=strengths["emitter"]),
        geo.LED_BOARD: principled("SL_LED_Board", (0.035, 0.036, 0.038), 0.55, 0.3),
    }
    return mats


def clay_body(spec):
    finish = BODY_FINISH[spec.slug]
    return principled(f"SL_{finish['label']}_Body", finish["clay"], finish["rough"], finish["metal"])


def build_asset(spec, body_materials, strengths, lods=(0, 1, 2)):
    """One asset under a root empty; LOD groups; the LightEmitter empty."""
    shared = shared_materials(spec, strengths)
    root = bpy.data.objects.new(spec.name, None)
    root.empty_display_size = 0.5
    bpy.context.scene.collection.objects.link(root)
    col = new_collection(spec.name)
    parts = {}
    emitter_at = None
    for lod in lods:
        mats = dict(shared)
        mats[geo.BODY] = body_materials[lod]
        group = bpy.data.objects.new(f"LOD{lod}", None)
        group.parent = root
        col.objects.link(group)
        objs, emitter, _frame = geo.build_asset(spec, lod, mats, col)
        for obj in objs.values():
            obj.parent = group
        parts[lod] = objs
        emitter_at = emitter_at or emitter
    light = bpy.data.objects.new("LightEmitter", None)
    light.empty_display_type = "SINGLE_ARROW"
    light.empty_display_size = 0.4
    light.location = emitter_at
    # Pointing straight down (-Z Blender / -Y three.js).
    light.rotation_euler = (radians(180), 0, 0)
    light.parent = root
    col.objects.link(light)
    lamp = LAMP[spec.kind]
    light["colorTemperatureK"] = lamp["kelvin"]
    light["colorSRGB"] = list(lamp["color"])
    light["beamAngleDeg"] = spec.beam_deg
    # Real distributions throw their peak a little ahead of the column, toward
    # the carriageway, and are darkest behind it.
    light["aimForwardM"] = 1.4
    root["assetHeightM"] = round(max(v.co.z for v in parts[lods[0]]["Arm"].data.vertices)
                                 + parts[lods[0]]["Arm"].location.z, 3)
    root["lodDistancesM"] = [0.0, 26.0, 60.0]
    root["family"] = "harpurhey-municipal-streetlight"
    return root, parts, light


# ------------------------------------------------------------------ finishes

BODY_FINISH = {
    "streetlight-warm-old-01": dict(label="WarmOld", clay=(0.42, 0.43, 0.42), rough=0.62, metal=0.7,
                                    pole="galvanised", age=0.55, housing=(0.40, 0.41, 0.40), seed=11),
    "streetlight-led-modern-01": dict(label="LEDModern", clay=(0.50, 0.51, 0.51), rough=0.5, metal=0.8,
                                      pole="galvanised", age=0.2, housing=(0.16, 0.165, 0.17), seed=23),
    "streetlight-curved-01": dict(label="Curved", clay=(0.06, 0.06, 0.065), rough=0.6, metal=0.0,
                                  pole="painted", age=0.45, housing=(0.30, 0.31, 0.31), seed=37),
    "streetlight-weathered-01": dict(label="Weathered", clay=(0.38, 0.38, 0.36), rough=0.7, metal=0.6,
                                     pole="galvanised", age=1.0, housing=(0.36, 0.36, 0.34), seed=53),
}


# ------------------------------------------------------------------- clay

def setup_camera(name, location, target, lens=50.0, ortho=None):
    cam_data = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = location
    direction = Vector(target) - Vector(location)
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    if ortho:
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = ortho
    else:
        cam_data.lens = lens
    cam_data.clip_end = 400
    return cam


def figure(location):
    """1.75 m scale figure: plain capsule body and head."""
    mat = principled("Scale_Figure", (0.18, 0.18, 0.2), 0.8)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.19, depth=1.45, location=(location[0], location[1], 0.725))
    body = bpy.context.object
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.115, location=(location[0], location[1], 1.635))
    head = bpy.context.object
    for obj in (body, head):
        obj.data.materials.append(mat)


def set_engine(scene, engine="CYCLES", samples=64):
    try:
        scene.render.engine = engine
    except TypeError:
        scene.render.engine = "CYCLES"
    if scene.render.engine == "CYCLES":
        scene.cycles.device = "CPU"
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True


def world_color(color, strength=1.0):
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (*color, 1.0)
    bg.inputs["Strength"].default_value = strength
    return world


def ground(size=60, color=(0.10, 0.10, 0.10), rough=0.85):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, 0))
    plane = bpy.context.object
    plane.name = "Ground"
    plane.data.materials.append(principled("Ground", color, rough))
    return plane


def stage_clay():
    reset()
    scene = bpy.context.scene
    set_engine(scene, samples=48)
    world_color((0.55, 0.57, 0.60), 1.0)
    ground(80, (0.25, 0.25, 0.25))
    for i, spec in enumerate(geo.SPECS):
        root, _parts, _light = build_asset(spec, {0: clay_body(spec)}, RENDER_STRENGTH, lods=(0,))
        root.location.x = i * 3.2
        root.location.y = 0
    figure((-1.6, 0.4))
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 2.5
    sun.rotation_euler = (radians(50), radians(10), radians(-30))
    scene.collection.objects.link(sun)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1100
    views = {
        "clay-lineup-elevation": setup_camera("Elev", (5.2, -40, 4.3), (5.2, 0, 4.3), ortho=14.0),
        "clay-lineup-eye-level": setup_camera("Eye", (2.0, -11.0, 1.6), (4.8, 0, 4.6), lens=24),
    }
    for label, cam in views.items():
        scene.camera = cam
        scene.render.filepath = str(RENDER_DIR / f"{label}.png")
        bpy.ops.render.render(write_still=True)
    # Lamp-head close-ups, one per asset.
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 800
    for i, spec in enumerate(geo.SPECS):
        root = bpy.data.objects[spec.name]
        emitter = root.location + bpy.data.objects[f"LightEmitter" if i == 0 else f"LightEmitter.{i:03d}"].location
        cam = setup_camera(f"Head{i}", emitter + Vector((0.25, -1.9, -0.55)), emitter + Vector((-0.1, 0, 0.02)), lens=50)
        scene.camera = cam
        scene.render.filepath = str(RENDER_DIR / f"clay-head-{spec.slug}.png")
        bpy.ops.render.render(write_still=True)
    for i, spec in enumerate(geo.SPECS):
        objs = [o for o in bpy.data.collections[spec.name].objects if o.type == "MESH"]
        print(f"{spec.name}: LOD0 {geo.triangle_count(objs)} triangles")




# ------------------------------------------------------------ texture pass
#
# Weathering is described in asset space: rain runs down the column, spray
# rises from the road (+X) and dirties the base, grime gathers under every
# joint, hands and keys wear the door, bolts weep rust, birds use the lantern.
# Amounts scale with each finish's `age`; none of it should read from
# gameplay distance as anything other than "an ordinary old lamp post".

SEVEN_SEG = {
    "0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd",
    "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcfgd",
}
PLATE_NUMBERS = {
    "streetlight-warm-old-01": "12", "streetlight-led-modern-01": "47",
    "streetlight-curved-01": "8", "streetlight-weathered-01": "103",
}


def seven_segment(u, v, text, cell_w, cell_h, stroke):
    """Coverage of a row of seven-segment digits centred on (0, 0)."""
    out = np.zeros_like(u)
    count = len(text)
    gap = cell_w * 0.35
    total = count * cell_w + (count - 1) * gap
    for k, ch in enumerate(text):
        cx = -total / 2 + cell_w / 2 + k * (cell_w + gap)
        du = u - cx
        hw, hh = cell_w / 2, cell_h / 2
        segs = {
            "a": (0, hh, hw, stroke), "g": (0, 0, hw, stroke), "d": (0, -hh, hw, stroke),
            "f": (-hw, hh / 2, stroke, hh / 2), "b": (hw, hh / 2, stroke, hh / 2),
            "e": (-hw, -hh / 2, stroke, hh / 2), "c": (hw, -hh / 2, stroke, hh / 2),
        }
        for name in SEVEN_SEG[ch]:
            sx, sy, ex, ey = segs[name]
            inside = (np.abs(du - sx) < ex + stroke / 2) & (np.abs(v - sy) < ey + stroke / 2)
            out = np.maximum(out, inside.astype(F))
    return out


def vertical_streaks(P, width, length, seed, threshold=0.55, sharp=2.0):
    """Seamless run-down streak field: 3-D noise stretched along Z."""
    q = P * np.array((1 / width, 1 / width, 1 / length), F)
    field = fbm3(q, 3, seed)
    return np.clip((field - threshold) * 3.2, 0, 1) ** sharp


def author_body(spec, tex, emitter, spigot, bolts):
    fin = BODY_FINISH[spec.slug]
    age = fin["age"]
    seed = fin["seed"]
    col = spec.column
    P, N = tex.P, tex.N
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    M = tex.M
    top = col.profile[-1][0]

    column = tex.name_mask("Pole") | tex.name_mask("AccessPanel")
    door = tex.name_mask("AccessPanel")
    arm = tex.name_mask("Arm")
    housing = tex.name_mask("LampHousing")
    structure = column | arm

    # Column-local cylindrical coordinates (theta 0 at the footway door).
    t = np.clip(z / top, 0, 1)
    dx = x - col.lean[0] * t * t
    dy = y - col.lean[1] * t * t
    rad = np.hypot(dx, dy)
    theta = np.arctan2(dy, -dx)
    u = theta * rad
    r_nominal = np.interp(z, [p[0] for p in col.profile], [p[1] for p in col.profile]).astype(F)

    L = Layers(tex, (0.3, 0.3, 0.3), 0.6, 0.0)
    height = np.zeros(M, F)
    sideways = np.clip(1 - np.abs(N[:, 2]) * 1.6, 0, 1)

    # --- base finishes -------------------------------------------------
    spangle = fbm3(P * 45.0, 3, seed) - 0.5
    blotch = fbm3(P * np.array((3.0, 3.0, 1.1), F), 3, seed + 1)
    mottle = fbm3(P * np.array((9.0, 9.0, 4.0), F), 3, seed + 2) - 0.5
    if fin["pole"] == "galvanised":
        g = 0.30 + spangle * 0.05 + mottle * 0.05
        L.albedo[structure] = np.stack((g, g, g * 0.975), axis=1)[structure]
        L.metal[structure] = (0.60 - 0.18 * age + mottle * 0.2)[structure]
        L.rough[structure] = (0.50 + 0.14 * age + spangle * 0.12 + mottle * 0.1)[structure]
        # Dull white zinc bloom patches.
        bloom = smoothstep(0.55, 0.78, blotch) * (0.35 + 0.65 * age)
        sel = structure
        L.tint((0.40, 0.40, 0.385), (bloom * 0.8)[sel], sel)
        L.rough[sel] += (bloom * 0.14)[sel]
        L.metal[sel] -= (bloom * 0.3)[sel]
        # Darker weathered patina.
        dark = smoothstep(0.45, 0.8, fbm3(P * np.array((5, 5, 1.6), F), 3, seed + 3)) * age
        L.tint((0.19, 0.19, 0.18), (dark * 0.45)[sel], sel)
        height += spangle * 0.00004
    else:
        # Near-black charcoal paint, chalky where sun and rain reach.
        L.albedo[structure] = np.array((0.020, 0.021, 0.023), F)
        L.rough[structure] = (0.50 + mottle * 0.08)[structure]
        L.metal[structure] = 0.0
        sun = np.clip(N @ np.array((0.35, -0.8, 0.45), F), 0, 1)
        chalk = (sun * 0.7 + 0.3) * smoothstep(0.35, 0.75, blotch) * age
        L.tint((0.050, 0.050, 0.052), (chalk * 0.85)[structure], structure)
        L.rough[structure] += (chalk * 0.25)[structure]
        # Chips down to galvanising, mostly low down and on edges.
        exposure = np.clip((1.3 - z) / 1.3, 0, 1) * 0.8 + tex.convex * 0.8 + (door * 0.4)
        chips = smoothstep(0.80, 0.86, fbm3(P * 60.0, 3, seed + 4) + exposure * 0.08 * age) * structure
        L.tint((0.28, 0.28, 0.27), chips)
        L.metal = np.maximum(L.metal, chips * 0.55)
        L.rough = L.rough * (1 - chips) + 0.45 * chips
        height -= chips * 0.00006

    hcol = np.array(fin["housing"], F)
    L.albedo[housing] = hcol * (1.0 + (mottle * 0.12)[housing, None])
    L.rough[housing] = (0.58 + mottle * 0.1)[housing]
    L.metal[housing] = 0.0
    if age > 0.3:
        # Old cast housings: chalky tops.
        up = np.clip(N[:, 2], 0, 1)
        L.tint(hcol * 1.25, (up * 0.5 * age)[housing], housing)
        L.rough[housing] += (up * 0.15 * age)[housing]

    # --- column number plate ----------------------------------------------
    a = radians(35.0)
    plate = column & (np.abs(z - col.plate_z) < 0.052) & (rad > r_nominal + 0.0011) & (np.abs(theta - (pi_f - a)) < 0.7)
    if plate.any():
        tangent = np.array((-np.sin(a), np.cos(a), 0.0), F)
        pu = (P[:, :2] - np.array((np.cos(a), np.sin(a)), F) * 0.0) @ tangent[:2]
        pv = z - col.plate_z
        yellow = np.array((0.62, 0.40, 0.02), F) * (1.0 - 0.25 * age)
        L.albedo[plate] = yellow
        glyph = seven_segment(pu, pv, PLATE_NUMBERS[spec.slug], 0.016, 0.042, 0.0055)
        L.tint((0.015, 0.015, 0.015), glyph[plate] * 0.95, plate)
        L.rough[plate] = 0.5
        L.metal[plate] = 0.0
        height += glyph * plate * 0.0002

    # --- rain streaks and run-off --------------------------------------
    rain = vertical_streaks(P, 0.010, 0.8, seed + 5) * sideways
    rain *= 0.45 + 0.55 * (1 - t)
    L.tint((0.11, 0.105, 0.09), rain * (0.25 + 0.45 * age))
    L.rough += rain * 0.08
    if fin["pole"] == "galvanised":
        zinc_runs = vertical_streaks(P, 0.006, 1.4, seed + 6, 0.6) * sideways * structure
        L.tint((0.42, 0.42, 0.40), zinc_runs * 0.35 * age)

    joints = list(col.welds) + [col.door_z[1] + 0.003, col.plate_z - 0.052]
    if spec.kind == "sox":
        joints.append(top - 0.24)
    if spec.kind == "son_bowl":
        joints.append(top - 0.36)
    drip_field = vertical_streaks(P, 0.006, 0.35, seed + 7, 0.45, 1.5)
    for zj in joints:
        below = np.clip(zj - z, 0, None)
        drip = (below > 0.001) * np.exp(-below / 0.28) * drip_field * sideways * column
        L.tint((0.07, 0.065, 0.055), drip * (0.35 + 0.45 * age))

    # --- road spray and ground contact ---------------------------------
    edge = 0.45 + 0.3 * fbm2(np.stack((u * 6, z * 2), axis=1), 3, seed + 8)
    spray = (1 - smoothstep(0.03, edge, z)) * (0.55 + 0.45 * np.clip(N[:, 0], 0, 1)) * column
    L.tint((0.085, 0.078, 0.065), spray * (0.45 + 0.4 * age))
    L.rough += spray * 0.12
    L.metal *= 1 - spray * 0.5
    contact = (1 - smoothstep(0.0, 0.06, z)) * column
    L.tint((0.035, 0.032, 0.028), contact * 0.85)

    # Crevice dirt everywhere, heavier with age.
    L.tint((0.06, 0.056, 0.05), (1 - tex.ao) * (0.35 + 0.4 * age))

    # --- door: key scratches, hand polish -------------------------------
    z0, z1 = col.door_z
    near_door = column & (np.abs(theta) < 0.95) & (z > z0 - 0.15) & (z < z1 + 0.15)
    patch = smoothstep(0.35, 0.7, noise2(np.stack((u / 0.05, z / 0.05), axis=1), seed + 9))
    rng = np.random.default_rng(seed)
    scratch = np.zeros(M, F)
    for k in range(5):
        ang = rng.uniform(0, np.pi)
        c, sn = np.cos(ang), np.sin(ang)
        across = u * c + z * sn
        along = -u * sn + z * c
        line = noise2(np.stack((across / 0.0011, along / 0.03), axis=1), seed + 20 + k)
        scratch = np.maximum(scratch, smoothstep(0.955, 0.99, line))
    scratch *= patch * near_door * (0.4 + 0.8 * age)
    lock = np.linalg.norm(P - np.array((-radius_at_z(col, z1 - 0.06), 0, z1 - 0.06), F), axis=1)
    scratch = np.maximum(scratch, (lock < 0.028) * smoothstep(0.9, 0.97, noise2(
        np.stack((np.arctan2(z - (z1 - 0.06), y) * 8, lock / 0.002), axis=1), seed + 30)) * (0.5 + age * 0.5))
    bright = (0.46, 0.46, 0.44) if fin["pole"] == "galvanised" else (0.26, 0.26, 0.25)
    L.tint(bright, scratch * 0.85)
    L.rough -= scratch * 0.2
    L.metal = np.maximum(L.metal, scratch * 0.7)
    height -= scratch * 0.00004
    polish = door * (1 - smoothstep(0.02, 0.06, np.abs(z - (z1 - 0.06)))) * 0.5
    L.rough -= polish * 0.12

    # --- stickers ----------------------------------------------------------
    paper = np.zeros(M, F)
    if spec.slug == "streetlight-weathered-01":
        rect = column & (np.abs(u - 0.0) < 0.055) & (np.abs(z - 1.49) < 0.09)
        torn = smoothstep(0.42, 0.5, fbm2(np.stack((u / 0.018, z / 0.018), axis=1), 4, seed + 11))
        glue = rect * (1 - torn)
        paper = rect * torn * 0.9
        L.tint((0.15, 0.14, 0.11), glue * 0.7)
        L.rough -= glue * 0.18
        L.tint((0.52, 0.50, 0.42), paper)
        rect2 = column & (np.abs(u + 0.02) < 0.035) & (np.abs(z - 1.12) < 0.03)
        L.tint((0.16, 0.15, 0.12), rect2 * smoothstep(0.4, 0.6, fbm2(np.stack((u / 0.01, z / 0.01), axis=1), 3, seed + 12)) * 0.6)
    else:
        rect = column & (np.abs(u - 0.055) < 0.022) & (np.abs(z - 1.56) < 0.032)
        paper = rect.astype(F)
        yellowed = np.array((0.66, 0.66, 0.62), F) * (1 - 0.3 * age) + np.array((0.0, 0.0, -0.08), F) * age
        L.tint(yellowed, paper)
        lines = ((np.abs(((z - 1.56) / 0.007) % 1.0 - 0.5) < 0.18) & (np.abs(u - 0.055) < 0.017)
                 & (z < 1.583)) * smoothstep(0.35, 0.55, noise2(np.stack((u / 0.003, z / 0.007), axis=1), seed + 13))
        L.tint((0.10, 0.10, 0.12), lines * paper * 0.8)
        L.tint((0.55, 0.12, 0.05), paper * (np.abs(z - 1.584) < 0.004) * 0.9)
    L.rough = L.rough * (1 - paper) + 0.7 * paper
    L.metal *= 1 - paper
    height += paper * 0.00008

    # --- bolts weep rust ---------------------------------------------------
    rust_amount = 0.2 + 0.8 * age
    for b in bolts:
        b = np.array(b, F)
        d = np.linalg.norm(P - b, axis=1)
        halo = (1 - smoothstep(0.004, 0.02 + 0.012 * age, d)) * smoothstep(0.3, 0.6, noise3(P * 180.0, seed + 14))
        dz = b[2] - z
        run = ((dz > 0) & (dz < 0.22) & (np.linalg.norm((P - b)[:, :2], axis=1) < 0.012)) * (1 - dz / 0.22)
        run *= vertical_streaks(P, 0.003, 0.08, seed + 15, 0.4, 1.0)
        L.tint((0.19, 0.08, 0.025), np.clip(halo + run * 0.6, 0, 1) * rust_amount * 0.85)
        L.rough += halo * 0.2

    # --- housing: dirt at the spigot, tops, birds ------------------------------
    d_sp = np.linalg.norm(P - np.array(spigot, F), axis=1)
    L.tint((0.06, 0.055, 0.05), (1 - smoothstep(0.02, 0.16, d_sp)) * (housing | arm) * (0.35 + 0.5 * age))
    top_face = np.clip((N[:, 2] - 0.4) / 0.6, 0, 1) * (housing | arm)
    L.tint((0.10, 0.10, 0.085), top_face * (0.15 + 0.4 * age))
    if age > 0.5:
        L.tint((0.07, 0.085, 0.05), top_face * smoothstep(0.5, 0.8, fbm3(P * 20, 3, seed + 16)) * 0.45 * age)
    birds = (0.1 + 0.9 * age) * smoothstep(0.62, 0.75, noise3(P * 5.0, seed + 17))
    splat = top_face * birds * smoothstep(0.7, 0.8, noise3(P * 60.0, seed + 18))
    runs = (housing | arm) * sideways * birds * vertical_streaks(P, 0.004, 0.06, seed + 19, 0.62, 1.4)
    L.tint((0.60, 0.60, 0.56), np.clip(splat + runs * 0.4, 0, 1) * 0.9)
    L.rough += splat * 0.2
    L.metal *= 1 - splat

    # --- lamp spill on the housing underside --------------------------------
    to_lamp = np.array(emitter, F) - P
    dist = np.linalg.norm(to_lamp, axis=1)
    facing = np.clip(np.sum(N * to_lamp, axis=1) / np.maximum(dist, 1e-4), 0, 1)
    spill = (housing | arm) * facing * np.exp(-dist / 0.14) * (N[:, 2] < 0.2)
    spill = np.clip(spill / max(float(spill.max()), 1e-4), 0, 1) ** 1.2

    L.height = height
    L.finish()
    return L, spill


pi_f = float(np.pi)


def radius_at_z(column, z):
    return geo.radius_at(column, z)


def save_body_textures(spec, lod, tex, layers, spill):
    stem = f"{spec.slug}_lod{lod}"
    out = TEXTURE_DIR / spec.slug
    ao = 1 - (1 - tex.ao) * 0.75
    base = tex.grid(np.concatenate((srgb_encode(layers.albedo), np.ones((tex.M, 1), F)), axis=1), (0.2, 0.2, 0.2, 1))
    orm = tex.grid(np.stack((ao, layers.rough, layers.metal, np.ones(tex.M, F)), axis=1), (1, 0.7, 0.3, 1))
    height = tex.grid(layers.height, 0.0)
    normal = height_to_normal(height, tex.texel_m, 1.0)
    glow = tex.grid(np.stack((spill, spill, spill, np.ones(tex.M, F)), axis=1), (0, 0, 0, 1))
    images = dict(
        base=save_rgba(out / f"{stem}_basecolor.png", base),
        orm=save_rgba(out / f"{stem}_orm.png", orm),
        normal=save_rgba(out / f"{stem}_normal.png", normal),
        glow=save_rgba(out / f"{stem}_emissive.png", glow),
    )
    for key in ("orm", "normal", "glow"):
        images[key].colorspace_settings.name = "Non-Color" if key != "glow" else "sRGB"
    return images


def textured_body(mat, images, spill_strength):
    """Principled material fed by the baked atlas; emissive map is a lamp-spill mask."""
    from surfaceWeathering import build_pbr_material

    build_pbr_material(mat, images["base"], images["orm"], images["normal"])
    nt = mat.node_tree
    shader = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    glow = nt.nodes.new("ShaderNodeTexImage")
    glow.name = glow.label = "Emissive"
    glow.image = images["glow"]
    glow.location = (-500, -650)
    nt.links.new(glow.outputs["Color"], shader.inputs["Emission Color"])
    shader.inputs["Emission Strength"].default_value = spill_strength
    return mat


def cylinder_uvs(obj, column, chunk=1.6, lower_boost=1.4):
    """Exact column unwrap in metres: u around the shaft, v up it.  The seam
    runs up the +Y side (neither road nor footway face); the shaft is cut into
    `chunk`-high islands so it packs into a square atlas, and the lowest two
    metres (door, stickers, spray) get extra texel density."""
    mesh = obj.data
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="UVMap")
    uv = mesh.uv_layers.active.data
    top = column.profile[-1][0]
    origin = obj.location
    for poly in mesh.polygons:
        pts = [origin + mesh.vertices[mesh.loops[li].vertex_index].co for li in poly.loop_indices]
        coords = []
        for p in pts:
            t = min(max(p.z / top, 0.0), 1.0)
            dx = p.x - column.lean[0] * t * t
            dy = p.y - column.lean[1] * t * t
            coords.append((np.arctan2(dx, -dy), float(np.hypot(dx, dy)), p.z))
        angles = [c[0] for c in coords]
        if max(angles) - min(angles) > np.pi:
            angles = [a + 2 * np.pi if a < 0 else a for a in angles]
        cz = sum(c[2] for c in coords) / len(coords)
        k = int(cz // chunk)
        boost = lower_boost if cz < 2.2 else 1.0
        for li, a, (_, r, z) in zip(poly.loop_indices, angles, coords):
            uv[li].uv = (a * 0.08 * boost + k * 10.0, (z - k * chunk) * boost)


def smart_uvs_in_metres(obj, boost=1.0):
    """Smart-project one object, then scale its islands to metres (x boost)."""
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    if not obj.data.uv_layers:
        obj.data.uv_layers.new(name="UVMap")
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=radians(50), island_margin=0.0, scale_to_bounds=False)
    bpy.ops.uv.average_islands_scale()
    bpy.ops.object.mode_set(mode="OBJECT")
    mesh = obj.data
    uv = mesh.uv_layers.active.data
    area3d = sum(p.area for p in mesh.polygons)
    area_uv = 0.0
    for poly in mesh.polygons:
        pts = [uv[li].uv for li in poly.loop_indices]
        for i in range(1, len(pts) - 1):
            a, b, c = pts[0], pts[i], pts[i + 1]
            area_uv += abs((b.x - a.x) * (c.y - a.y) - (c.x - a.x) * (b.y - a.y)) / 2
    factor = (area3d / max(area_uv, 1e-12)) ** 0.5 * boost
    for loop_uv in uv:
        loop_uv.uv = loop_uv.uv * factor + Vector((0, 40.0 + obj.name.__hash__() % 7))


def unwrap_streetlight(objs, spec):
    for obj in objs:
        base = obj.name.split("_LOD")[0]
        if base in ("Pole", "AccessPanel"):
            cylinder_uvs(obj, spec.column)
        else:
            smart_uvs_in_metres(obj, boost={"LampHousing": 1.8, "Arm": 1.3}.get(base, 1.0))
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(margin=0.004, rotate=True, scale=True)
    bpy.ops.object.mode_set(mode="OBJECT")


def body_objects(parts):
    return [parts[k] for k in ("Pole", "AccessPanel", "Arm", "LampHousing") if k in parts]


def stage_build(specs=None):
    TEXTURE_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    report = []
    for spec in specs or geo.SPECS:
        reset()
        geo.BOLT_SITES.clear()
        fin = BODY_FINISH[spec.slug]
        bodies = {lod: bpy.data.materials.new(f"SL_{fin['label']}_Body" + ("" if lod == 0 else f"_LOD{lod}"))
                  for lod in (0, 1, 2)}
        root, parts, light = build_asset(spec, bodies, GLB_STRENGTH)
        bolts = [tuple(b) for b in geo.BOLT_SITES]
        bpy.context.view_layer.update()
        emitter = tuple(light.location)
        report.append(f"EMITTER {spec.slug} x={emitter[0]:.3f} y={emitter[1]:.3f} z={emitter[2]:.3f} "
                      f"height={root['assetHeightM']:.2f}")
        spigot = tuple(parts[0]["LampHousing"].location)
        mean = None
        for lod in (0, 1):
            objs = body_objects(parts[lod])
            unwrap_streetlight(objs, spec)
            size = ATLAS[lod]
            position, normal, extra, names = bake_buffers(objs, size, size, ao_distance=0.2, samples=4 if lod else 8,
                                                           true_normal_ao=True)
            tex = Texels(position, normal, extra, names)
            layers, spill = author_body(spec, tex, emitter, spigot, bolts if lod == 0 else [])
            images = save_body_textures(spec, lod, tex, layers, spill)
            textured_body(bodies[lod], images, GLB_STRENGTH["spill"])
            if lod == 0:
                column = tex.name_mask("Pole")
                mean = srgb_encode(layers.albedo[column].mean(axis=0))
                rough = float(layers.rough[column].mean())
                metal = float(layers.metal[column].mean())
        flat = bodies[2]
        flat.use_nodes = True
        shader = next(n for n in flat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        shader.inputs["Base Color"].default_value = (*srgb_to_linear(tuple(float(c) for c in mean)), 1.0)
        shader.inputs["Roughness"].default_value = rough
        shader.inputs["Metallic"].default_value = metal

        for lod in (0, 1, 2):
            objs = [o for o in parts[lod].values()]
            report.append(f"{spec.name} LOD{lod}: {geo.triangle_count(objs)} triangles, {len(objs)} meshes")
        bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE_DIR / f"{spec.slug}.blend"))
        export_glb(root, MODEL_DIR / f"{spec.slug}.glb")
    print("\n".join(report))


def export_glb(root, path):
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    for child in root.children_recursive:
        child.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_extras=True,
        export_image_format="WEBP",
        export_image_quality=86,
        export_lights=False,
        export_cameras=False,
    )


# ------------------------------------------------------------- test renders

def set_strength(prefix, value):
    for mat in bpy.data.materials:
        if mat.name.startswith(prefix) and mat.node_tree:
            shader = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if shader:
                shader.inputs["Emission Strength"].default_value = value


def night_world():
    world = bpy.data.worlds.new("Night")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(coord.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    ramp.color_ramp.elements[0].position = 0.5
    ramp.color_ramp.elements[0].color = (0.012, 0.013, 0.022, 1)
    ramp.color_ramp.elements[1].position = 0.85
    ramp.color_ramp.elements[1].color = (0.004, 0.014, 0.065, 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0


def street_set():
    """Pavement, kerb, road and near-black terraces either side."""
    asphalt = principled("Set_Asphalt", (0.06, 0.06, 0.062), 0.5)
    slabs = principled("Set_Pavement", (0.20, 0.20, 0.19), 0.8)
    brick = principled("Set_Terrace", (0.05, 0.035, 0.03), 0.9)
    window = principled("Set_Window", (0.02, 0.02, 0.02), 0.2, emission=(1.0, 0.72, 0.42), strength=0.6)
    dark_window = principled("Set_DarkWindow", (0.01, 0.012, 0.015), 0.15)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(8, 0, 0))
    road = bpy.context.object
    road.scale = (16, 80, 1)
    road.data.materials.append(asphalt)
    for loc, dims, mat in (((-1.9, 0, 0.06), (3.6, 80, 0.12), slabs), ((0.2, 0, 0.065), (0.15, 80, 0.13), slabs)):
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        o = bpy.context.object
        o.scale = dims
        o.data.materials.append(mat)
    rng = np.random.default_rng(3)
    for side, x0 in ((-1, -3.7), (1, 16.5)):
        for i in range(-8, 9):
            y = i * 5.2
            bpy.ops.mesh.primitive_cube_add(size=1, location=(x0 + side * 4.5, y, 4.6))
            o = bpy.context.object
            o.scale = (9.0, 5.1, 9.2)
            o.data.materials.append(brick)
            for fz in (1.6, 4.4):
                bpy.ops.mesh.primitive_cube_add(size=1, location=(x0 - side * 0.02, y + 1.0, fz))
                w = bpy.context.object
                w.scale = (0.05, 1.1, 1.3)
                w.data.materials.append(window if rng.random() < 0.08 else dark_window)


def compositor_bloom(scene, strength=0.18):
    ng = bpy.data.node_groups.new("StreetlightComp", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    scene.compositing_node_group = ng
    rl = ng.nodes.new("CompositorNodeRLayers")
    glare = ng.nodes.new("CompositorNodeGlare")
    glare.inputs["Type"].default_value = "Bloom"
    glare.inputs["Threshold"].default_value = 4.0
    glare.inputs["Strength"].default_value = strength
    glare.inputs["Size"].default_value = 0.12
    out = ng.nodes.new("NodeGroupOutput")
    ng.links.new(rl.outputs["Image"], glare.inputs["Image"])
    ng.links.new(glare.outputs[0], out.inputs[0])


def stage_renders(specs=None):
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    for spec in specs or geo.SPECS:
        bpy.ops.wm.open_mainfile(filepath=str(SOURCE_DIR / f"{spec.slug}.blend"))
        scene = bpy.context.scene
        for obj in bpy.data.objects:
            if obj.parent and obj.parent.name in ("LOD1", "LOD2"):
                obj.hide_render = True
        set_engine(scene, samples=96)
        scene.render.resolution_x = 960
        scene.render.resolution_y = 1200
        scene.view_settings.view_transform = "AgX"
        street_set()
        light_obj = bpy.data.objects["LightEmitter"]
        emitter = light_obj.matrix_world.translation
        lamp = LAMP[spec.kind]
        # A downward distribution: bright under and a little ahead of the
        # lantern, nothing above it, falling to darkness between columns.
        point = bpy.data.lights.new("Lamp", "SPOT")
        point.color = srgb_to_linear(lamp["color"])
        point.energy = 5200 if spec.kind != "led" else 4200
        point.spot_size = radians(spec.beam_deg)
        point.spot_blend = 0.85
        point.shadow_soft_size = 0.04
        lamp_obj = bpy.data.objects.new("Lamp", point)
        lamp_obj.location = emitter + Vector((0, 0, -0.02))
        lamp_obj.rotation_euler = (0, radians(-12), 0)
        scene.collection.objects.link(lamp_obj)
        # The bowl's own glow on the housing it hangs from.
        spill = bpy.data.lights.new("LampSpill", "POINT")
        spill.color = srgb_to_linear(lamp["color"])
        spill.energy = 6.0
        spill.shadow_soft_size = 0.05
        spill_obj = bpy.data.objects.new("LampSpill", spill)
        spill_obj.location = emitter + Vector((0, 0, -0.05))
        scene.collection.objects.link(spill_obj)

        # Night.
        night_world()
        set_strength("SL_Emitter", 30.0)
        set_strength("SL_Glass", 0.25)
        set_strength("SL_Reflector", 0.0)
        set_strength(f"SL_{BODY_FINISH[spec.slug]['label']}_Body", 0.0)
        scene.view_settings.exposure = 0.6
        compositor_bloom(scene)
        head = emitter
        cams = {
            "night-street": setup_camera("NightStreet", (5.5, -10.5, 1.6), (0.9, 0, 3.9), lens=26),
            "night-head": setup_camera("NightHead", head + Vector((1.6, -2.6, -1.9)), head + Vector((-0.15, 0, 0.02)), lens=70),
        }
        for label, cam in cams.items():
            scene.camera = cam
            scene.render.filepath = str(RENDER_DIR / f"{spec.slug}-{label}.png")
            bpy.ops.render.render(write_still=True)

        # Overcast day, lamp off: the final "would I believe it?" test.
        point.energy = 0
        spill.energy = 0
        set_strength("SL_Emitter", 0.0)
        set_strength("SL_Glass", 0.0)
        scene.compositing_node_group = None
        world_color((0.62, 0.64, 0.67), 1.0)
        scene.view_settings.exposure = 0.0
        cams = {
            "day-grey-sky": setup_camera("DayGrey", (5.5, -9.5, 1.6), (0.4, 0, 5.4), lens=30),
            "day-base": setup_camera("DayBase", (-1.25, -1.0, 1.25), (-0.05, 0, 0.95), lens=40),
        }
        for label, cam in cams.items():
            scene.camera = cam
            scene.render.filepath = str(RENDER_DIR / f"{spec.slug}-{label}.png")
            bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    stage = argv[argv.index("--stage") + 1] if "--stage" in argv else "all"
    only = argv[argv.index("--only") + 1].split(",") if "--only" in argv else None
    specs = [s for s in geo.SPECS if only is None or s.slug in only]
    if stage == "clay":
        stage_clay()
    if stage in ("build", "all"):
        stage_build(specs)
    if stage in ("renders", "all"):
        stage_renders(specs)
