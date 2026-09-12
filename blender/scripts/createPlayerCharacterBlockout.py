"""Zealot of Harperhey — player character, geometry/silhouette blockout pass.

Builds the hero playable character described in the player-character asset brief:
a young Black British man in an oversized dark indigo denim jacket and enormous
indigo jeans, cornrowed, carrying a black patchwork-leather delivery bag, wearing
metallic silver Y2K football trainers, with historical steel greaves over his
shins and articulated gauntlets on his hands and forearms.

This is the FIRST pass and deliberately stops at geometry, silhouette and
placeholder material response — no textures, no normal maps, no armature.
It follows the same blockout-then-promote pattern the architecture assets use
(createRealCameraBlockout.py -> createRealCamera.py).

Object hierarchy keeps the four pivot empties that src/player/PlayerController.ts
already drives by name, so the asset can drop into the running game unchanged.

Run headless:
    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --python blender/scripts/createPlayerCharacterBlockout.py
"""

from pathlib import Path
import math

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
BLEND_PATH = ROOT / "blender" / "source" / "player-character-blockout.blend"
GLB_PATH = ROOT / "public" / "assets" / "models" / "player-character-blockout.glb"
RENDER_DIR = ROOT / "renders" / "player-character-blockout"

# ---------------------------------------------------------------------------
# Skeleton of measurements (metres, Z up, character faces +Y, sole plane z=0).
# Slim-athletic, 1.78 m. Deliberately NOT heroic proportions: the clothing
# silhouette carries the character, not the musculature.
# ---------------------------------------------------------------------------
Z_SOLE = 0.0
Z_ANKLE = 0.085
Z_CALF = 0.30
Z_KNEE = 0.455
Z_CROTCH = 0.845
Z_HIP = 0.965
Z_WAIST = 1.075
Z_CHEST = 1.31
Z_SHOULDER = 1.425
Z_NECK_TOP = 1.545
Z_CHIN = 1.545
Z_HEAD_CENTRE = 1.672
Z_CROWN = 1.780

X_LEG = 0.088          # hip pivot lateral offset
X_SHOULDER = 0.208     # anatomical shoulder joint
X_JACKET_SHOULDER = 0.288  # dropped shoulder of the oversized jacket

COLLECTIONS = (
    "ZOH_BODY",
    "ZOH_HEAD",
    "ZOH_HAIR_CORNROWS",
    "ZOH_JACKET_DENIM",
    "ZOH_JEANS_OVERSIZED",
    "ZOH_GREAVES",
    "ZOH_GAUNTLETS",
    "ZOH_SHOES",
    "ZOH_DELIVERY_BAG",
    "ZOH_REVIEW",
)

_active_collection = {"name": "ZOH_BODY"}


# ---------------------------------------------------------------------------
# Scene / collection plumbing
# ---------------------------------------------------------------------------

def reset_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def make_collections():
    for name in COLLECTIONS:
        if name not in bpy.data.collections:
            collection = bpy.data.collections.new(name)
            bpy.context.scene.collection.children.link(collection)


def part(name):
    """Route every object created after this call into the named collection."""
    _active_collection["name"] = name


def adopt(obj):
    """Move a freshly created object into the currently selected collection."""
    target = bpy.data.collections[_active_collection["name"]]
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    target.objects.link(obj)
    return obj


# ---------------------------------------------------------------------------
# Materials — the brief's material hierarchy, as placeholder PBR response only.
# ---------------------------------------------------------------------------

def material(name, colour, roughness=0.75, metallic=0.0, **extra):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*colour, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*colour, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    for key, value in extra.items():
        socket = bsdf.inputs.get(key)
        if socket is not None:
            socket.default_value = value
    return mat


def build_materials():
    """One controlled hierarchy: skin / hair / denim / leather / armour / shoe."""
    m = {}
    m["skin"] = material("PC_Skin_DeepBrown", (0.073, 0.033, 0.020), 0.58,
                         **{"Subsurface Weight": 0.10, "Specular IOR Level": 0.42})
    m["skin_warm"] = material("PC_Skin_WarmPlane", (0.098, 0.046, 0.027), 0.52,
                              **{"Subsurface Weight": 0.12})
    m["skin_lip"] = material("PC_Skin_Lip", (0.086, 0.037, 0.031), 0.42)
    m["scalp"] = material("PC_Scalp_Stubble", (0.036, 0.019, 0.013), 0.86)
    m["hair"] = material("PC_Hair_Cornrow", (0.0135, 0.0110, 0.0098), 0.36,
                         **{"Specular IOR Level": 0.55})
    m["eye_white"] = material("PC_Eye_Sclera", (0.34, 0.31, 0.27), 0.28)
    m["eye_iris"] = material("PC_Eye_Iris", (0.020, 0.012, 0.008), 0.22)

    # Near-black raw indigo. The reference photographs read almost black under
    # subdued light — never bright blue.
    m["denim"] = material("PC_Denim_RawIndigo", (0.0180, 0.0215, 0.0345), 0.88)
    m["denim_deep"] = material("PC_Denim_RawIndigo_Shadowed", (0.0128, 0.0152, 0.0250), 0.90)
    m["denim_seam"] = material("PC_Denim_SeamThread", (0.0295, 0.0268, 0.0205), 0.84)
    m["denim_hardware"] = material("PC_Denim_Hardware", (0.40, 0.40, 0.395), 0.34, 1.0)

    # Black patchwork leather: alternating matte / semi / worn-gloss panels.
    # Black leather really is black: it separates from the denim by its
    # specular response, not by being several stops lighter.
    m["leather_matte"] = material("PC_Leather_MattePebble", (0.0122, 0.0122, 0.0128), 0.90,
                                  **{"Specular IOR Level": 0.36})
    m["leather_semi"] = material("PC_Leather_SemiSmooth", (0.0134, 0.0132, 0.0139), 0.76,
                                 **{"Specular IOR Level": 0.44})
    m["leather_gloss"] = material("PC_Leather_WornGloss", (0.0148, 0.0146, 0.0154), 0.58,
                                  **{"Specular IOR Level": 0.54})
    m["leather_strap"] = material("PC_Leather_Harness", (0.0110, 0.0110, 0.0117), 0.80)
    m["leather_hw"] = material("PC_Leather_Hardware", (0.145, 0.145, 0.148), 0.42, 1.0)

    # Historical armour: aged, irregular, tarnished. Distinctly NOT the shoes.
    m["armour"] = material("PC_Armour_AgedSteel", (0.112, 0.114, 0.118), 0.72, 1.0)
    m["armour_worn"] = material("PC_Armour_PolishedWear", (0.182, 0.183, 0.186), 0.52, 1.0)
    m["armour_dark"] = material("PC_Armour_Oxidised", (0.070, 0.067, 0.058), 0.80, 1.0)
    m["rivet"] = material("PC_Armour_Rivet", (0.245, 0.241, 0.232), 0.46, 1.0)

    # Manufactured Y2K silver: smoother, brighter, cleaner than the armour.
    m["shoe"] = material("PC_Shoe_MetallicSilver", (0.660, 0.668, 0.682), 0.155, 1.0)
    m["shoe_line"] = material("PC_Shoe_PanelLine", (0.085, 0.087, 0.092), 0.35, 0.6)
    m["shoe_sole"] = material("PC_Shoe_Outsole", (0.0165, 0.0168, 0.0175), 0.62)

    m["sock"] = material("PC_Sock_Dark", (0.030, 0.031, 0.034), 0.90)
    return m


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def finish(obj, mat, smooth=False, bevel=0.0, segments=2):
    if obj.data is not None and hasattr(obj.data, "materials"):
        obj.data.materials.append(mat)
    if smooth and obj.type == "MESH":
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    if bevel:
        modifier = obj.modifiers.new("soft-edges", "BEVEL")
        modifier.width = bevel
        modifier.segments = segments
        modifier.limit_method = "ANGLE"
        modifier.angle_limit = math.radians(38)
    return obj


def parent_keep_transform(obj, parent):
    """Parent without moving the child.

    Assigning matrix_world after setting .parent is not safe here: the pivot
    empties are created moments earlier and their evaluated matrix_world is
    still stale, which silently offsets every child by the pivot's own height.
    Setting matrix_parent_inverse explicitly is the reliable form.
    """
    bpy.context.view_layer.update()
    obj.parent = parent
    obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj


def mesh_from(name, vertices, faces, mat, smooth=False, bevel=0.0, parent=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.validate()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    adopt(obj)
    finish(obj, mat, smooth=smooth, bevel=bevel)
    if parent:
        parent_keep_transform(obj, parent)
    return obj


def cube(name, location, size, mat, bevel=0.0, parent=None, rotation=None, smooth=False):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if rotation:
        obj.rotation_euler = [math.radians(a) for a in rotation]
    adopt(obj)
    finish(obj, mat, bevel=bevel, smooth=smooth)
    if parent:
        parent_keep_transform(obj, parent)
    return obj


def sphere(name, location, radii, mat, segments=20, rings=12, parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings,
                                         radius=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = radii
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    adopt(obj)
    finish(obj, mat, smooth=True)
    if parent:
        parent_keep_transform(obj, parent)
    return obj


def tube(name, start, end, radius_start, radius_end, mat, sides=14, parent=None,
         smooth=True, bevel=0.0):
    """A tapered tube between two world points."""
    start = Vector(start)
    end = Vector(end)
    axis = end - start
    length = axis.length
    quat = axis.to_track_quat("Z", "Y")
    vertices = []
    for index, (offset, radius) in enumerate(((0.0, radius_start), (length, radius_end))):
        for s in range(sides):
            angle = 2 * math.pi * s / sides
            local = Vector((math.cos(angle) * radius, math.sin(angle) * radius, offset))
            vertices.append(start + quat @ local)
    faces = []
    for s in range(sides):
        n = (s + 1) % sides
        faces.append((s, n, sides + n, sides + s))
    faces.append(tuple(range(sides - 1, -1, -1)))
    faces.append(tuple(range(sides, sides * 2)))
    return mesh_from(name, vertices, faces, mat, smooth=smooth, bevel=bevel, parent=parent)


def loft(name, rings, mat, sides=20, power=1.0, smooth=True, bevel=0.0,
         parent=None, cap_bottom=True, cap_top=True):
    """Loft a stack of super-elliptical cross sections.

    rings: sequence of (z, cx, cy, rx, ry). `power` < 1 squares the section off,
    which is what makes denim volumes read as fabric rather than as pipes.
    """
    vertices = []
    for z, cx, cy, rx, ry in rings:
        for s in range(sides):
            angle = 2 * math.pi * s / sides
            c, sn = math.cos(angle), math.sin(angle)
            x = math.copysign(abs(c) ** power, c) * rx
            y = math.copysign(abs(sn) ** power, sn) * ry
            vertices.append((cx + x, cy + y, z))
    faces = []
    for r in range(len(rings) - 1):
        base = r * sides
        for s in range(sides):
            n = (s + 1) % sides
            faces.append((base + s, base + n, base + sides + n, base + sides + s))
    if cap_bottom:
        faces.append(tuple(range(sides - 1, -1, -1)))
    if cap_top:
        top = (len(rings) - 1) * sides
        faces.append(tuple(range(top, top + sides)))
    return mesh_from(name, vertices, faces, mat, smooth=smooth, bevel=bevel, parent=parent)


def shell(name, rings, angle_from, angle_to, thickness, mat, steps=12,
          parent=None, smooth=True, bevel=0.0, wobble=0.0):
    """A curved armour plate: an arc swept up a stack of (z, cx, cy, rx, ry) rings.

    Produces a closed solid with an inner and outer surface, which is how a real
    greave or gauntlet cuff behaves — a wrapped sheet, not a tube.
    """
    a0 = math.radians(angle_from)
    a1 = math.radians(angle_to)
    outer, inner = [], []
    seed = abs(hash(name)) % 9973
    for row, (z, cx, cy, rx, ry) in enumerate(rings):
        for s in range(steps + 1):
            angle = a0 + (a1 - a0) * s / steps
            c, sn = math.cos(angle), math.sin(angle)
            # Hammered, handmade irregularity: real armour is not a lathe part.
            bump = jitter(seed + row * 31 + s * 7, wobble) if wobble else 0.0
            outer.append((cx + c * (rx + bump), cy + sn * (ry + bump), z))
            inner.append((cx + c * (rx - thickness), cy + sn * (ry - thickness), z))
    vertices = outer + inner
    offset = len(outer)
    cols = steps + 1
    faces = []
    for r in range(len(rings) - 1):
        for s in range(steps):
            a = r * cols + s
            b = a + 1
            c = a + cols
            d = c + 1
            faces.append((a, b, d, c))                                  # outer
            faces.append((offset + a, offset + c, offset + d, offset + b))  # inner
        # side returns
        a = r * cols
        faces.append((a, a + cols, offset + a + cols, offset + a))
        b = r * cols + steps
        faces.append((b, offset + b, offset + b + cols, b + cols))
    bottom = [(s, s + 1, offset + s + 1, offset + s) for s in range(steps)]
    top_base = (len(rings) - 1) * cols
    top = [(top_base + s, offset + top_base + s, offset + top_base + s + 1, top_base + s + 1)
           for s in range(steps)]
    faces.extend(bottom)
    faces.extend(top)
    return mesh_from(name, vertices, faces, mat, smooth=smooth, bevel=bevel, parent=parent)


def braid(name, points, radius, mat, parent=None, knots=True, knot_scale=1.32):
    """A cornrow: a swept path whose radius pulses so it reads as an interlock.

    The pulse is real geometry, not a normal map — the brief requires the braids
    to be readable forms in the silhouette.
    """
    samples = _frames(_resample(points, max(10, int(len(points) * 7))))
    sides = 7
    vertices = []
    for index, (position, side, normal) in enumerate(samples):
        pulse = 1.0
        lateral = 0.0
        if knots:
            phase = index * 0.78
            pulse = 1.0 + (knot_scale - 1.0) * (0.5 + 0.5 * math.sin(phase))
            lateral = math.sin(phase * 0.5) * radius * 0.30
        # taper the last few samples so the braid ends rather than stopping flat
        tail = min(1.0, (len(samples) - index) / 5.0)
        r = radius * pulse * (0.35 + 0.65 * tail)
        centre = position + side * lateral
        for s in range(sides):
            angle = 2 * math.pi * s / sides
            vertices.append(centre + side * (math.cos(angle) * r) + normal * (math.sin(angle) * r))
    faces = []
    for seg in range(len(samples) - 1):
        base = seg * sides
        for s in range(sides):
            n = (s + 1) % sides
            faces.append((base + s, base + n, base + sides + n, base + sides + s))
    faces.append(tuple(range(sides - 1, -1, -1)))
    last = (len(samples) - 1) * sides
    faces.append(tuple(range(last, last + sides)))
    return mesh_from(name, vertices, faces, mat, smooth=True, parent=parent)


def _frames(path):
    """Parallel-transport a reference normal along a path, so a swept ribbon
    never flips. Choosing `up` per sample twists wherever the path is vertical."""
    tangent0 = path[0][1]
    seed = Vector((0, 0, 1))
    if abs(tangent0.dot(seed)) > 0.9:
        seed = Vector((0, 1, 0))
    normal = (seed - tangent0 * seed.dot(tangent0)).normalized()
    frames = []
    for position, tangent in path:
        normal = (normal - tangent * normal.dot(tangent))
        if normal.length < 1e-6:
            fallback = Vector((0, 1, 0)) if abs(tangent.z) > 0.9 else Vector((0, 0, 1))
            normal = (fallback - tangent * fallback.dot(tangent))
        normal = normal.normalized()
        side = tangent.cross(normal).normalized()
        frames.append((position, side, normal))
    return frames


def _resample(points, count):
    """Catmull-Rom resample of a polyline, returning (position, unit tangent)."""
    pts = [Vector(p) for p in points]
    padded = [pts[0] + (pts[0] - pts[1])] + pts + [pts[-1] + (pts[-1] - pts[-2])]
    out = []
    spans = len(pts) - 1
    for index in range(count):
        u = index / (count - 1) * spans
        i = min(int(u), spans - 1)
        t = u - i
        p0, p1, p2, p3 = padded[i], padded[i + 1], padded[i + 2], padded[i + 3]
        t2, t3 = t * t, t * t * t
        position = 0.5 * ((2 * p1) + (-p0 + p2) * t +
                          (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
                          (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
        tangent = 0.5 * ((-p0 + p2) + (2 * p0 - 5 * p1 + 4 * p2 - p3) * 2 * t +
                         (-p0 + 3 * p1 - 3 * p2 + p3) * 3 * t2)
        if tangent.length < 1e-6:
            tangent = (p2 - p1)
        out.append((position, tangent.normalized()))
    return out


def empty(name, location, parent=None, size=0.06):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = size
    obj.location = location
    bpy.context.collection.objects.link(obj)
    adopt(obj)
    if parent:
        obj.parent = parent
    return obj


def jitter(seed, spread):
    """Deterministic pseudo-random offset so reruns of the script are identical."""
    value = math.sin(seed * 12.9898) * 43758.5453
    return (value - math.floor(value) - 0.5) * 2.0 * spread


def loft_y(name, rings, mat, sides=18, power=1.0, smooth=True, bevel=0.0, parent=None):
    """Loft along +Y instead of +Z. rings: (y, cx, cz, rx, rz)."""
    vertices = []
    for y, cx, cz, rx, rz in rings:
        for s in range(sides):
            angle = 2 * math.pi * s / sides
            c, sn = math.cos(angle), math.sin(angle)
            x = math.copysign(abs(c) ** power, c) * rx
            z = math.copysign(abs(sn) ** power, sn) * rz
            vertices.append((cx + x, y, cz + z))
    faces = []
    for r in range(len(rings) - 1):
        base = r * sides
        for s in range(sides):
            n = (s + 1) % sides
            faces.append((base + s, base + sides + s, base + sides + n, base + n))
    faces.append(tuple(range(sides)))
    last = (len(rings) - 1) * sides
    faces.append(tuple(range(last + sides - 1, last - 1, -1)))
    return mesh_from(name, vertices, faces, mat, smooth=smooth, bevel=bevel, parent=parent)


# ---------------------------------------------------------------------------
# Body
# ---------------------------------------------------------------------------

def build_body(m, root, arms, legs):
    part("ZOH_BODY")

    loft("PC_Torso", [
        (0.840, 0.0, 0.004, 0.146, 0.104),
        (0.965, 0.0, 0.004, 0.151, 0.108),
        (1.075, 0.0, 0.002, 0.138, 0.097),
        (1.200, 0.0, 0.004, 0.152, 0.101),
        (1.310, 0.0, 0.006, 0.172, 0.108),
        (1.395, 0.0, 0.004, 0.180, 0.105),
        (1.440, 0.0, 0.002, 0.160, 0.096),
    ], m["skin"], sides=22, power=0.82)

    tube("PC_Neck", (0, 0.004, 1.375), (0, 0.012, 1.558), 0.058, 0.050, m["skin"], sides=16)

    for side, sign, pivot in (("L", -1, legs["L"]), ("R", 1, legs["R"])):
        hip = (sign * X_LEG, 0.004, 0.960)
        knee = (sign * X_LEG * 1.02, 0.014, Z_KNEE)
        ankle = (sign * X_LEG * 1.04, 0.020, 0.105)
        tube(f"PC_Thigh_{side}", hip, knee, 0.090, 0.058, m["skin"], sides=14, parent=pivot)
        tube(f"PC_Shin_{side}", knee, ankle, 0.058, 0.036, m["skin"], sides=14, parent=pivot)
        tube(f"PC_Sock_{side}", (sign * X_LEG * 1.04, 0.020, 0.145),
             (sign * X_LEG * 1.06, 0.022, 0.048), 0.042, 0.040, m["sock"], sides=12, parent=pivot)

    for side, sign, pivot in (("L", -1, arms["L"]), ("R", 1, arms["R"])):
        shoulder = (sign * X_SHOULDER, 0.000, 1.418)
        elbow = (sign * 0.232, 0.026, 1.145)
        wrist = (sign * 0.240, 0.062, 0.882)
        tube(f"PC_UpperArm_{side}", shoulder, elbow, 0.054, 0.041, m["skin"], sides=14, parent=pivot)
        tube(f"PC_Forearm_{side}", elbow, wrist, 0.041, 0.030, m["skin"], sides=14, parent=pivot)
        build_hand(m, side, sign, pivot)


def build_hand(m, side, sign, pivot):
    """Underlying hand. Mostly hidden by the gauntlet, but present and articulable —
    the rigging stage needs real fingers to drive the gauntlet lames."""
    palm_top = (sign * 0.240, 0.064, 0.880)
    palm_low = (sign * 0.242, 0.074, 0.800)
    tube(f"PC_Palm_{side}", palm_top, palm_low, 0.031, 0.034, m["skin"], sides=12, parent=pivot)
    cube(f"PC_PalmBlock_{side}", (sign * 0.242, 0.072, 0.828), (0.076, 0.038, 0.088),
         m["skin"], bevel=0.012, parent=pivot)
    for index, offset in enumerate((-0.0285, -0.0095, 0.0095, 0.0285)):
        x = sign * (0.242 + offset * sign)
        length = (0.072, 0.082, 0.078, 0.064)[index]
        tube(f"PC_Finger_{side}_{index + 1}", (x, 0.076, 0.790), (x, 0.081, 0.790 - length),
             0.0092, 0.0078, m["skin"], sides=8, parent=pivot)
    tube(f"PC_Thumb_{side}", (sign * 0.224, 0.082, 0.856), (sign * 0.212, 0.098, 0.806),
         0.0135, 0.0110, m["skin"], sides=8, parent=pivot)


# ---------------------------------------------------------------------------
# Head — believable, grounded, deliberately not a hyper-masculine game face.
# The hairstyle reference supplies grooming and presentation only; this is not
# a likeness of the person photographed.
# ---------------------------------------------------------------------------

HEAD_C = (0.0, -0.004, 1.676)
HEAD_R = (0.0795, 0.0885, 0.1045)


def build_head(m, root):
    part("ZOH_HEAD")

    loft("PC_Head", [
        (1.542, 0.0, 0.030, 0.030, 0.040),
        (1.562, 0.0, 0.022, 0.050, 0.060),
        (1.588, 0.0, 0.012, 0.066, 0.074),
        (1.616, 0.0, 0.005, 0.0745, 0.0825),
        (1.646, 0.0, 0.000, 0.0790, 0.0872),
        (1.676, 0.0, -0.004, 0.0795, 0.0885),
        (1.706, 0.0, -0.006, 0.0785, 0.0875),
        (1.736, 0.0, -0.009, 0.0745, 0.0825),
        (1.762, 0.0, -0.013, 0.0645, 0.0715),
        (1.776, 0.0, -0.016, 0.0455, 0.0505),
        (1.783, 0.0, -0.018, 0.0200, 0.0225),
    ], m["skin"], sides=26, power=1.0, parent=root)

    # Face. Deliberately restrained: the brief puts the geometry budget into
    # silhouette and material, not into a face the gameplay camera rarely sees.
    # The eye sits marginally proud of the skull and is framed by lid forms —
    # primitive assembly cannot cut a real socket, and a buried eyeball reads
    # as nothing at all while an unframed one reads as a bulge.
    for sign in (-1, 1):
        tag = "L" if sign < 0 else "R"
        sphere(f"PC_Brow_{tag}", (sign * 0.033, 0.0640, 1.7025),
               (0.032, 0.012, 0.0062), m["skin_warm"], 14, 8, parent=root)
        ear = sphere(f"PC_Ear_{tag}", (sign * 0.0755, -0.014, 1.6680),
                     (0.0060, 0.014, 0.024), m["skin_warm"], 14, 10, parent=root)
        ear.rotation_euler.z = math.radians(sign * 14)
        # Flattened into the eye socket plane: a full ball reads as a bulge on
        # a head built from primitives, and the socket cannot be cut.
        sphere(f"PC_EyeBall_{tag}", (sign * 0.0315, 0.0700, 1.6802),
               (0.0128, 0.0088, 0.0072), m["eye_white"], 16, 12, parent=root)
        sphere(f"PC_Iris_{tag}", (sign * 0.0315, 0.0770, 1.6802),
               (0.0048, 0.0026, 0.0046), m["eye_iris"], 12, 8, parent=root)
        lid_u = cube(f"PC_LidUpper_{tag}", (sign * 0.0315, 0.0700, 1.6872),
                     (0.034, 0.024, 0.0060), m["skin"], bevel=0.0028, parent=root)
        lid_u.rotation_euler.x = math.radians(-22)
        lid_l = cube(f"PC_LidLower_{tag}", (sign * 0.0315, 0.0706, 1.6738),
                     (0.032, 0.022, 0.0048), m["skin"], bevel=0.0022, parent=root)
        lid_l.rotation_euler.x = math.radians(16)

    loft("PC_Nose", [
        (1.6330, 0.0, 0.0660, 0.0128, 0.0120),
        (1.6430, 0.0, 0.0755, 0.0120, 0.0098),
        (1.6560, 0.0, 0.0782, 0.0098, 0.0090),
        (1.6760, 0.0, 0.0748, 0.0074, 0.0082),
        (1.6980, 0.0, 0.0700, 0.0068, 0.0078),
        (1.7120, 0.0, 0.0655, 0.0086, 0.0078),
    ], m["skin_warm"], sides=12, power=0.85, parent=root)

    cube("PC_Philtrum", (0, 0.0700, 1.6235), (0.015, 0.012, 0.015),
         m["skin_warm"], bevel=0.005, parent=root)
    cube("PC_Lip_Upper", (0, 0.0700, 1.6128), (0.040, 0.014, 0.0072), m["skin_lip"],
         bevel=0.0032, parent=root)
    cube("PC_Lip_Lower", (0, 0.0706, 1.6035), (0.036, 0.015, 0.0090), m["skin_lip"],
         bevel=0.004, parent=root)
    cube("PC_Chin", (0, 0.0580, 1.5735), (0.044, 0.028, 0.028), m["skin_warm"],
         bevel=0.013, parent=root)
    # Jaw line — carried by the head loft itself. Slab cubes here read as
    # rectangles stuck on the cheeks.
    for sign in (-1, 1):
        jaw = sphere(f"PC_Jaw_{'L' if sign < 0 else 'R'}", (sign * 0.047, 0.028, 1.5885),
                     (0.019, 0.040, 0.024), m["skin"], 14, 10, parent=root)
        jaw.rotation_euler.z = math.radians(sign * -12)


# ---------------------------------------------------------------------------
# Cornrows — the single most identity-bearing element. Real swept braid geometry
# with readable partings, following curved paths across the scalp.
# ---------------------------------------------------------------------------

def scalp_point(lat_deg, phi_deg, lift=0.0):
    """Point on (or just above) the cranium.

    lat_deg  lateral angle from the sagittal plane, +ve to the character's right
    phi_deg  0 = forward, 90 = crown, 180 = back of the head
    """
    lat = math.radians(lat_deg)
    phi = math.radians(phi_deg)
    n = (math.sin(lat), math.cos(lat) * math.cos(phi), math.cos(lat) * math.sin(phi))
    return (
        HEAD_C[0] + n[0] * (HEAD_R[0] + lift),
        HEAD_C[1] + n[1] * (HEAD_R[1] + lift),
        HEAD_C[2] + n[2] * (HEAD_R[2] + lift),
    )


def build_hair(m, root):
    part("ZOH_HAIR_CORNROWS")

    # Scalp cap in a stubble material so the partings read as scalp, not as a
    # gap down to bare face skin.
    loft("PC_ScalpCap", [
        (1.648, 0.0, -0.004, 0.0800, 0.0890),
        (1.690, 0.0, -0.006, 0.0792, 0.0882),
        (1.726, 0.0, -0.010, 0.0760, 0.0842),
        (1.758, 0.0, -0.014, 0.0672, 0.0744),
        (1.776, 0.0, -0.017, 0.0470, 0.0522),
        (1.786, 0.0, -0.019, 0.0180, 0.0205),
    ], m["scalp"], sides=26, power=1.0, parent=root, cap_bottom=False)

    # Nine braids. Outer braids curve inward toward the nape, which is what makes
    # the partings read as curves rather than as straight stripes.
    laterals = (-48, -36, -24, -12, 0, 12, 24, 36, 48)
    for index, lat in enumerate(laterals):
        drop = abs(lat) / 48.0
        start_phi = 26 + drop * 12          # hairline sits lower at the temples
        points = []
        for step in range(9):
            v = step / 8.0
            phi = start_phi + (196 - start_phi) * v
            # braids converge slightly toward the back, and sweep as they go
            lat_eff = lat * (1.0 - 0.24 * v) + math.sin(v * math.pi) * (-3.5 if lat else 0.0)
            lift = 0.0105 + 0.0025 * math.sin(v * math.pi)
            points.append(scalp_point(lat_eff, phi, lift))
        # short braided ends hanging clear of the skull at the nape
        tail_lat = lat * 0.72
        points.append(scalp_point(tail_lat, 204, 0.004))
        tail = scalp_point(tail_lat, 210, -0.004)
        points.append((tail[0], tail[1] - 0.008, tail[2] - 0.030))
        braid(f"PC_Cornrow_{index + 1:02d}", points, 0.0088, m["hair"], parent=root)

    # Tight-textured edge / hairline and nape, kept short and clean.
    for sign in (-1, 1):
        sphere(f"PC_Edge_Temple_{'L' if sign < 0 else 'R'}",
               (sign * 0.070, 0.048, 1.700), (0.014, 0.022, 0.024),
               m["scalp"], 14, 10, parent=root)
        sphere(f"PC_Edge_Sideburn_{'L' if sign < 0 else 'R'}",
               (sign * 0.072, 0.026, 1.654), (0.011, 0.016, 0.026),
               m["scalp"], 12, 10, parent=root)
    loft("PC_Nape", [
        (1.596, 0.0, -0.062, 0.052, 0.030),
        (1.624, 0.0, -0.068, 0.060, 0.034),
        (1.650, 0.0, -0.072, 0.064, 0.036),
    ], m["scalp"], sides=16, power=0.9, parent=root)


# ---------------------------------------------------------------------------
# Denim jacket — oversized, boxy, cropped relative to its width, dropped
# shoulders, heavy raw indigo that reads near-black under subdued light.
# ---------------------------------------------------------------------------

def build_jacket(m, root, arms):
    part("ZOH_JACKET_DENIM")

    # Cropped at the natural waist and narrower through the body, so the arms
    # separate from the torso and the jeans read as a distinct garment below.
    loft("PC_Jacket_Body", [
        (1.088, 0.0, 0.004, 0.226, 0.148),
        (1.128, 0.0, 0.004, 0.222, 0.145),
        (1.196, 0.0, 0.004, 0.230, 0.151),
        (1.272, 0.0, 0.005, 0.238, 0.156),
        (1.348, 0.0, 0.004, 0.246, 0.159),
        (1.412, 0.0, 0.002, 0.258, 0.156),
        (1.442, 0.0, 0.000, 0.242, 0.144),
        (1.468, 0.0, -0.002, 0.180, 0.114),
    ], m["denim"], sides=26, power=0.72, parent=root)

    # Waistband / hem band — the structural band a denim jacket sits on.
    loft("PC_Jacket_HemBand", [
        (1.076, 0.0, 0.004, 0.229, 0.151),
        (1.104, 0.0, 0.004, 0.233, 0.154),
        (1.132, 0.0, 0.004, 0.227, 0.148),
    ], m["denim_deep"], sides=26, power=0.72, parent=root)

    # Collar: a stand plus a folded-down leaf, classic trucker collar.
    shell("PC_Jacket_CollarStand", [
        (1.462, 0.0, -0.004, 0.118, 0.104),
        (1.500, 0.0, -0.006, 0.122, 0.108),
    ], -168, 168, 0.012, m["denim"], steps=20, parent=root, smooth=False, bevel=0.004)
    shell("PC_Jacket_CollarLeaf", [
        (1.478, 0.0, -0.006, 0.140, 0.126),
        (1.508, 0.0, -0.008, 0.131, 0.117),
    ], -160, 160, 0.014, m["denim_deep"], steps=20, parent=root, smooth=False, bevel=0.005)

    # Front placket, buttons and the panel seams that give denim its structure.
    cube("PC_Jacket_Placket", (0, 0.160, 1.276), (0.058, 0.016, 0.352),
         m["denim_deep"], bevel=0.006, parent=root)
    for index in range(4):
        z = 1.146 + index * 0.084
        cube(f"PC_Jacket_Button_{index + 1}", (0.0, 0.172, z), (0.018, 0.010, 0.018),
             m["denim_hardware"], bevel=0.004, parent=root)

    for sign in (-1, 1):
        tag = "L" if sign < 0 else "R"
        # chest pocket with a buttoned flap
        cube(f"PC_Jacket_Pocket_{tag}", (sign * 0.112, 0.158, 1.276),
             (0.104, 0.012, 0.094), m["denim_deep"], bevel=0.006, parent=root)
        cube(f"PC_Jacket_PocketFlap_{tag}", (sign * 0.112, 0.164, 1.322),
             (0.114, 0.016, 0.038), m["denim"], bevel=0.006, parent=root)
        cube(f"PC_Jacket_PocketButton_{tag}", (sign * 0.112, 0.172, 1.304),
             (0.013, 0.008, 0.013), m["denim_hardware"], bevel=0.003, parent=root)
        # yoke seam and the vertical front panel seams
        cube(f"PC_Jacket_YokeSeam_{tag}", (sign * 0.132, 0.156, 1.356),
             (0.200, 0.010, 0.009), m["denim_seam"], bevel=0.002, parent=root)
        cube(f"PC_Jacket_PanelSeam_{tag}", (sign * 0.180, 0.148, 1.234),
             (0.008, 0.010, 0.270), m["denim_seam"], bevel=0.002, parent=root)
        cube(f"PC_Jacket_BackSeam_{tag}", (sign * 0.138, -0.152, 1.256),
             (0.008, 0.010, 0.310), m["denim_seam"], bevel=0.002, parent=root)

    build_sleeves(m, arms)


def build_sleeves(m, arms):
    for side, sign, pivot in (("L", -1, arms["L"]), ("R", 1, arms["R"])):
        shoulder = (sign * 0.248, 0.002, 1.420)
        elbow = (sign * 0.266, 0.032, 1.136)
        cuff_top = (sign * 0.254, 0.056, 0.976)
        wrist = (sign * 0.252, 0.060, 0.944)
        # Roomy but not puffed: the reference jacket is oversized through the
        # body with a sleeve that hangs, not a balloon.
        tube(f"PC_Jacket_SleeveUpper_{side}", shoulder, elbow, 0.104, 0.092,
             m["denim"], sides=16, parent=pivot, bevel=0.006)
        tube(f"PC_Jacket_SleeveLower_{side}", elbow, cuff_top, 0.090, 0.072,
             m["denim"], sides=16, parent=pivot, bevel=0.006)
        tube(f"PC_Jacket_Cuff_{side}", cuff_top, wrist, 0.070, 0.062,
             m["denim_deep"], sides=16, parent=pivot, bevel=0.005)
        tube(f"PC_Jacket_ElbowSeam_{side}", (sign * 0.266, 0.030, 1.148),
             (sign * 0.266, 0.034, 1.126), 0.0935, 0.0915, m["denim_seam"],
             sides=16, parent=pivot)


# ---------------------------------------------------------------------------
# Jeans — extremely wide, near-black indigo, long enough to stack heavily over
# the shoes. The shin is locally gathered where the greave straps compress it.
# ---------------------------------------------------------------------------

def build_jeans(m, root, legs):
    part("ZOH_JEANS_OVERSIZED")

    loft("PC_Jeans_Seat", [
        (0.792, 0.0, 0.004, 0.202, 0.146),
        (0.880, 0.0, 0.004, 0.210, 0.150),
        (0.960, 0.0, 0.004, 0.206, 0.145),
        (1.018, 0.0, 0.002, 0.194, 0.136),
        (1.048, 0.0, 0.002, 0.188, 0.131),
        (1.088, 0.0, 0.002, 0.182, 0.126),
    ], m["denim"], sides=24, power=0.80, parent=root)

    # Runs up past the jacket hem band. At rest the 14 mm of torso between the
    # two garments is hidden, but any real hip flexion opened it into a strip
    # of bare skin — the overlap has to be built in, not assumed.
    loft("PC_Jeans_Waistband", [
        (1.014, 0.0, 0.002, 0.192, 0.135),
        (1.062, 0.0, 0.002, 0.190, 0.133),
        (1.090, 0.0, 0.002, 0.184, 0.128),
    ], m["denim_deep"], sides=24, power=0.80, parent=root)

    for index, x in enumerate((-0.150, -0.062, 0.062, 0.150)):
        cube(f"PC_Jeans_BeltLoop_F{index + 1}", (x, 0.126, 1.040),
             (0.020, 0.016, 0.058), m["denim_deep"], bevel=0.004, parent=root)
    for index, x in enumerate((-0.120, 0.0, 0.120)):
        cube(f"PC_Jeans_BeltLoop_B{index + 1}", (x, -0.124, 1.040),
             (0.020, 0.016, 0.058), m["denim_deep"], bevel=0.004, parent=root)

    cube("PC_Jeans_Fly", (0, 0.138, 0.968), (0.030, 0.012, 0.094),
         m["denim_seam"], bevel=0.003, parent=root)
    for sign in (-1, 1):
        tag = "L" if sign < 0 else "R"
        front = (34, 62) if sign > 0 else (118, 146)
        shell(f"PC_Jeans_FrontPocket_{tag}", [
            (0.930, 0.0, 0.004, 0.208, 0.147),
            (1.014, 0.0, 0.002, 0.198, 0.139),
        ], front[0], front[1], 0.006, m["denim_deep"], steps=10, parent=root,
            smooth=False, bevel=0.004)
        back = (-64, -20) if sign > 0 else (200, 244)
        shell(f"PC_Jeans_BackPocket_{tag}", [
            (0.890, 0.0, 0.004, 0.212, 0.152),
            (1.010, 0.0, 0.002, 0.200, 0.141),
        ], back[0], back[1], 0.007, m["denim_deep"], steps=10, parent=root,
            smooth=False, bevel=0.005)

    for side, sign, pivot in (("L", -1, legs["L"]), ("R", 1, legs["R"])):
        build_jeans_leg(m, side, sign, pivot)


def build_jeans_leg(m, side, sign, pivot):
    # cx drifts outward with height loss so the columns splay very slightly.
    # The column stays centred close to the actual leg, so the extra width
    # falls both outboard and inboard — which is how jeans this wide really
    # hang, and what makes the two legs read as one mass of denim.
    profile = [
        (0.890, 0.106, 0.126, 0.134),
        (0.760, 0.108, 0.134, 0.144),
        (0.620, 0.111, 0.145, 0.157),
        (0.510, 0.114, 0.156, 0.168),
        (0.470, 0.115, 0.160, 0.172),   # widest — enormous above the greave
        (0.438, 0.116, 0.146, 0.156),   # gathered by the upper greave strap
        (0.404, 0.116, 0.104, 0.110),   # compressed under the strap
        (0.300, 0.116, 0.098, 0.104),   # compressed beneath the greave itself
        (0.208, 0.116, 0.103, 0.109),   # compressed under the lower strap
        (0.170, 0.117, 0.152, 0.158),   # fabric escapes below the armour
        (0.128, 0.120, 0.170, 0.168),   # stacks on the shoe
        (0.098, 0.122, 0.172, 0.166),   # break / fold
        (0.076, 0.123, 0.164, 0.150),   # hem rolling under
        (0.062, 0.124, 0.150, 0.128),
    ]
    # The hem is pulled back as well as up, so the toe of the shoe clears the
    # denim: the brief wants the silver to flash beneath the trouser hems.
    rings = [(z, sign * cx, 0.014 - max(0.0, (0.17 - z)) * 0.34, rx, ry)
             for z, cx, rx, ry in profile]
    loft(f"PC_Jeans_Leg_{side}", rings, m["denim"], sides=24, power=0.80,
         parent=pivot, bevel=0.004)

    # Outseam swept along the real outer edge of the profile, so it stays on the
    # cloth instead of hanging in the air beside it.
    outseam = [(sign * (cx + rx * 0.995), 0.014, z) for z, cx, rx, ry in profile]
    sweep(f"PC_Jeans_Outseam_{side}", outseam, 0.010, 0.0034, m["denim_seam"],
          parent=pivot)
    inseam = [(sign * (cx - rx * 0.995), 0.014, z) for z, cx, rx, ry in profile[:-2]]
    sweep(f"PC_Jeans_Inseam_{side}", inseam, 0.009, 0.0030, m["denim_seam"],
          parent=pivot)
    loft(f"PC_Jeans_Hem_{side}", [
        (0.062, sign * 0.124, -0.0298, 0.152, 0.130),
        (0.096, sign * 0.122, -0.0198, 0.174, 0.168),
    ], m["denim_deep"], sides=24, power=0.80, parent=pivot)


# ---------------------------------------------------------------------------
# Greaves — museum-metal, articulated, strapped ON OVER the denim so the fabric
# is compressed rather than replaced. Not a fantasy armour tube.
# ---------------------------------------------------------------------------

def build_greaves(m, legs):
    part("ZOH_GREAVES")
    for side, sign, pivot in (("L", -1, legs["L"]), ("R", 1, legs["R"])):
        # Sized to the leg, not to the denim column: a shin plate strapped over
        # compressed cloth, never an armour tube worn outside the trousers.
        cx = sign * 0.108
        lames = (
            ("Upper", [
                (0.394, 0.102, 0.108),
                (0.420, 0.106, 0.113),
                (0.440, 0.098, 0.104),
            ]),
            ("Main", [
                (0.214, 0.101, 0.107),
                (0.266, 0.108, 0.115),
                (0.328, 0.107, 0.114),
                (0.382, 0.103, 0.109),
            ]),
            ("Ankle", [
                (0.130, 0.092, 0.097),
                (0.168, 0.099, 0.105),
                (0.206, 0.102, 0.108),
            ]),
        )
        for name, rows in lames:
            rings = [(z, cx, 0.014, rx, ry) for z, rx, ry in rows]
            plate = shell(f"PC_Greave_{name}_{side}", rings, 22, 158, 0.009,
                          m["armour"], steps=16, parent=pivot, smooth=False,
                          bevel=0.004, wobble=0.0022)
            # irregular, handmade: each lame sits at its own slight angle
            plate.rotation_euler.y = math.radians(jitter(hash((name, side)) % 97, 1.4))

        # Polished wear along the shin crest, where a greave actually rubs.
        sweep(f"PC_Greave_Crest_{side}", [
            (cx, 0.128, 0.146), (cx, 0.136, 0.300), (cx, 0.128, 0.432),
        ], 0.020, 0.005, m["armour_worn"], parent=pivot)
        # Oxidised interior lip at the top opening.
        shell(f"PC_Greave_TopLip_{side}", [
            (0.440, cx, 0.014, 0.097, 0.103),
            (0.452, cx, 0.014, 0.103, 0.110),
        ], 20, 160, 0.010, m["armour_dark"], steps=16, parent=pivot,
            smooth=False, bevel=0.003)

        # Two leather straps wrapping behind the calf, through the denim.
        for index, z in ((1, 0.198), (2, 0.406)):
            shell(f"PC_Greave_Strap_{index}_{side}", [
                (z - 0.015, cx, 0.014, 0.106, 0.113),
                (z + 0.015, cx, 0.014, 0.106, 0.113),
            ], -186, 186, 0.007, m["leather_strap"], steps=22, parent=pivot,
                smooth=False, bevel=0.002)
            cube(f"PC_Greave_Buckle_{index}_{side}", (cx + sign * 0.100, 0.012, z),
                 (0.014, 0.024, 0.024), m["leather_hw"], bevel=0.004, parent=pivot)

        for index in range(6):
            angle = math.radians(34 + index * 18.4)
            z = 0.238 + (index % 3) * 0.058
            rx, ry = 0.107, 0.114
            sphere(f"PC_Greave_Rivet_{side}_{index + 1}",
                   (cx + math.cos(angle) * rx, 0.014 + math.sin(angle) * ry, z),
                   (0.0046, 0.0046, 0.0046), m["rivet"], 8, 6, parent=pivot)


# ---------------------------------------------------------------------------
# Gauntlets — articulated, riveted, closer to museum armour than videogame
# armour. Flared cuff sits over the oversized denim sleeve.
# ---------------------------------------------------------------------------

def build_gauntlets(m, arms):
    part("ZOH_GAUNTLETS")
    for side, sign, pivot in (("L", -1, arms["L"]), ("R", 1, arms["R"])):
        cx = sign * 0.244
        # Cuff flares just enough to swallow the denim sleeve cuff. A wide bell
        # here reads as a trumpet, not as armour.
        # Barely flared. The denim sleeve inside is slim, so a wide bell here
        # reads as a traffic cone rather than as armour.
        shell(f"PC_Gauntlet_Vambrace_{side}", [
            (0.848, cx, 0.066, 0.048, 0.050),
            (0.886, cx, 0.065, 0.052, 0.054),
            (0.920, cx, 0.064, 0.055, 0.058),
        ], -178, 178, 0.007, m["armour"], steps=22, parent=pivot,
            smooth=False, bevel=0.004, wobble=0.0016)
        # Short bell, only at the top, overlapping the denim sleeve cuff.
        shell(f"PC_Gauntlet_Cuff_{side}", [
            (0.916, cx, 0.064, 0.056, 0.059),
            (0.942, cx, 0.063, 0.062, 0.065),
            (0.964, cx, 0.062, 0.067, 0.070),
        ], -178, 178, 0.008, m["armour"], steps=22, parent=pivot,
            smooth=False, bevel=0.004, wobble=0.0014)
        shell(f"PC_Gauntlet_CuffLip_{side}", [
            (0.962, cx, 0.062, 0.066, 0.069),
            (0.976, cx, 0.062, 0.070, 0.073),
        ], -178, 178, 0.010, m["armour_worn"], steps=22, parent=pivot,
            smooth=False, bevel=0.003, wobble=0.0012)

        # Wrist articulation: three narrow overlapping lames.
        for index, z in enumerate((0.840,)):
            shell(f"PC_Gauntlet_WristLame_{index + 1}_{side}", [
                (z - 0.012, cx, 0.066, 0.047, 0.046),
                (z + 0.012, cx, 0.066, 0.050, 0.044),
            ], -150, 150, 0.006, m["armour"], steps=18, parent=pivot,
                smooth=False, bevel=0.002, wobble=0.0010)

        # Back-of-hand plate (the metacarpal plate) with a raised central ridge.
        shell(f"PC_Gauntlet_HandPlate_{side}", [
            (0.786, cx, 0.072, 0.054, 0.030),
            (0.818, cx, 0.072, 0.059, 0.032),
            (0.850, cx, 0.070, 0.055, 0.034),
        ], -70, 150, 0.007, m["armour"], steps=16, parent=pivot,
            smooth=False, bevel=0.003, wobble=0.0012)
        sweep(f"PC_Gauntlet_HandRidge_{side}", [
            (cx, 0.100, 0.790), (cx, 0.104, 0.818), (cx, 0.100, 0.846),
        ], 0.018, 0.005, m["armour_worn"], parent=pivot)

        # Knuckle lames spanning all four fingers.
        for index, z in enumerate((0.786, 0.772)):
            shell(f"PC_Gauntlet_Knuckle_{index + 1}_{side}", [
                (z - 0.008, cx, 0.073, 0.056, 0.029),
                (z + 0.010, cx, 0.073, 0.059, 0.031),
            ], -50, 145, 0.006, m["armour"], steps=14, parent=pivot,
                smooth=False, bevel=0.002, wobble=0.0010)

        # Per-finger lames — three plates each, the articulation the brief wants.
        # A lame spanning all four fingers at the base, then per-finger plates.
        # Twelve separate tubes read as a chain of beads at gameplay distance.
        shell(f"PC_Gauntlet_FingerBase_{side}", [
            (0.742, cx, 0.073, 0.055, 0.028),
            (0.762, cx, 0.073, 0.058, 0.030),
        ], -50, 145, 0.006, m["armour"], steps=14, parent=pivot,
            smooth=False, bevel=0.002, wobble=0.0010)
        for finger, offset in enumerate((-0.0300, -0.0100, 0.0100, 0.0300)):
            x = cx + offset * sign
            length = (0.068, 0.078, 0.074, 0.060)[finger]
            for lame in range(2):
                t = lame / 2.0
                z = 0.748 - t * length
                radius = 0.0128 - lame * 0.0008
                shell(f"PC_Gauntlet_Finger_{finger + 1}_{lame + 1}_{side}", [
                    (z - length * 0.560, x, 0.074, radius, radius),
                    (z + length * 0.040, x, 0.074, radius + 0.0012, radius + 0.0012),
                ], -40, 220, 0.0045, m["armour"], steps=12, parent=pivot,
                    smooth=False, bevel=0.0012)
            sphere(f"PC_Gauntlet_FingerTip_{finger + 1}_{side}",
                   (x, 0.0755, 0.752 - length), (0.0118, 0.0126, 0.0128),
                   m["armour_worn"], 10, 8, parent=pivot)

        # Thumb lames.
        for lame in range(3):
            t = lame / 3.0
            sphere(f"PC_Gauntlet_Thumb_{lame + 1}_{side}",
                   (sign * (0.226 - t * 0.022), 0.086 + t * 0.014, 0.856 - t * 0.026),
                   (0.0180, 0.0188, 0.0150), m["armour"], 12, 8, parent=pivot)

        for index in range(5):
            angle = math.radians(-40 + index * 62)
            z = (0.862, 0.886, 0.908, 0.886, 0.862)[index]
            sphere(f"PC_Gauntlet_Rivet_{side}_{index + 1}",
                   (cx + math.cos(angle) * 0.051, 0.065 + math.sin(angle) * 0.054, z),
                   (0.0048, 0.0048, 0.0048), m["rivet"], 8, 6, parent=pivot)


def sweep(name, points, width, thickness, mat, parent=None, samples=None, bevel=0.0):
    """Sweep a flat rectangular band along a path — straps, panel lines, trim."""
    path = _frames(_resample(points, samples or max(8, len(points) * 6)))
    vertices = []
    for position, side, normal in path:
        for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            vertices.append(position + side * (sx * width * 0.5) + normal * (sz * thickness * 0.5))
    faces = []
    for seg in range(len(path) - 1):
        base = seg * 4
        for s in range(4):
            n = (s + 1) % 4
            faces.append((base + s, base + n, base + 4 + n, base + 4 + s))
    faces.append((3, 2, 1, 0))
    last = (len(path) - 1) * 4
    faces.append((last, last + 1, last + 2, last + 3))
    return mesh_from(name, vertices, faces, mat, smooth=False, bevel=bevel, parent=parent)


# ---------------------------------------------------------------------------
# Shoes — metallic silver, early-2000s football/training last. Manufactured,
# smooth and bright: deliberately a different metal from the historical armour.
# ---------------------------------------------------------------------------

def build_shoes(m, legs):
    part("ZOH_SHOES")
    for side, sign, pivot in (("L", -1, legs["L"]), ("R", 1, legs["R"])):
        cx = sign * 0.098
        upper = [
            (-0.086, cx, 0.038, 0.030, 0.030),
            (-0.068, cx, 0.044, 0.041, 0.044),
            (-0.044, cx, 0.042, 0.046, 0.043),
            (-0.014, cx, 0.038, 0.048, 0.039),
            (0.020, cx, 0.034, 0.048, 0.035),
            (0.058, cx, 0.030, 0.047, 0.031),
            (0.096, cx, 0.026, 0.043, 0.026),
            (0.126, cx, 0.022, 0.034, 0.020),
            (0.148, cx, 0.018, 0.018, 0.011),
        ]
        loft_y(f"PC_Shoe_Upper_{side}", upper, m["shoe"], sides=18, power=0.74,
               parent=pivot, bevel=0.004)

        sole = [
            (-0.086, cx, 0.008, 0.030, 0.008),
            (-0.060, cx, 0.007, 0.043, 0.007),
            (-0.014, cx, 0.006, 0.050, 0.006),
            (0.058, cx, 0.006, 0.049, 0.006),
            (0.112, cx, 0.007, 0.040, 0.007),
            (0.150, cx, 0.009, 0.019, 0.006),
        ]
        loft_y(f"PC_Shoe_Sole_{side}", sole, m["shoe_sole"], sides=16, power=0.55,
               parent=pivot, bevel=0.002)

        # Flowing embossed panel lines — the +F50-era swept graphic.
        for index, (y0, z0, y1, z1, y2, z2) in enumerate((
            (-0.052, 0.062, 0.020, 0.048, 0.108, 0.030),
            (-0.044, 0.048, 0.026, 0.036, 0.116, 0.024),
            (-0.034, 0.034, 0.032, 0.026, 0.120, 0.018),
        )):
            outer = sign * 0.001
            sweep(f"PC_Shoe_PanelLine_{index + 1}_{side}", [
                (cx + sign * 0.044 + outer, y0, z0),
                (cx + sign * 0.049 + outer, y1, z1),
                (cx + sign * 0.036 + outer, y2, z2),
            ], 0.0075, 0.0026, m["shoe_line"], parent=pivot)

        # Minimal fastening: a single elasticated tongue strap, no visible laces.
        cube(f"PC_Shoe_Strap_{side}", (cx, 0.004, 0.058), (0.086, 0.046, 0.016),
             m["shoe"], bevel=0.006, parent=pivot, rotation=(-16, 0, 0))
        cube(f"PC_Shoe_HeelTab_{side}", (cx, -0.082, 0.062), (0.030, 0.012, 0.026),
             m["shoe_line"], bevel=0.005, parent=pivot)


# ---------------------------------------------------------------------------
# Delivery bag — black patchwork leather. A handmade luxury-leather artefact
# that still reads as delivery equipment. No branding, no bright colours.
# ---------------------------------------------------------------------------

BAG_CY = -0.272


def build_bag(m, root):
    part("ZOH_DELIVERY_BAG")

    # power 0.74 keeps it a bag rather than a filing cabinet: the corners are
    # soft because the thing is made of leather and carries weight.
    body = loft("PC_Bag_Body", [
        (1.020, 0.0, BAG_CY, 0.170, 0.082),
        (1.060, 0.0, BAG_CY, 0.200, 0.098),
        (1.180, 0.0, BAG_CY, 0.216, 0.106),
        (1.330, 0.0, BAG_CY, 0.218, 0.107),
        (1.444, 0.0, BAG_CY, 0.210, 0.102),
        (1.506, 0.0, BAG_CY, 0.190, 0.090),
        (1.538, 0.0, BAG_CY, 0.156, 0.072),
    ], m["leather_matte"], sides=24, power=0.82, parent=root, bevel=0.016)
    body.rotation_euler.x = math.radians(-2.5)

    # Patchwork: panels of subtly different black leathers, each at its own
    # slight depth and gloss. Deliberately IRREGULAR — an even grid of equal
    # squares reads as a Rubik's cube, not as something handmade from offcuts.
    leathers = (m["leather_matte"], m["leather_semi"], m["leather_gloss"])
    rows = (
        (1.052, 0.104, (0.30, 0.24, 0.46)),
        (1.156, 0.088, (0.22, 0.41, 0.37)),
        (1.244, 0.112, (0.44, 0.31, 0.25)),
        (1.356, 0.094, (0.27, 0.20, 0.29, 0.24)),
        (1.450, 0.082, (0.38, 0.35, 0.27)),
    )
    span = 0.408
    for row_index, (z0, height, widths) in enumerate(rows):
        cursor = -span * 0.5
        for col_index, fraction in enumerate(widths):
            width = span * fraction
            seed = row_index * 11 + col_index * 7
            mat = leathers[(row_index * 2 + col_index + row_index // 2) % 3]
            depth = 0.006 + jitter(seed, 0.0014)
            cube(f"PC_Bag_Patch_B{row_index + 1}{col_index + 1}",
                 (cursor + width * 0.5 + jitter(seed + 1, 0.0010),
                  BAG_CY - 0.1055 - depth * 0.5 + 0.005,
                  z0 + height * 0.5 + jitter(seed + 2, 0.0010)),
                 (width - 0.004, depth, height - 0.004),
                 mat, bevel=0.005, parent=root)
            if col_index < len(widths) - 1:
                sweep(f"PC_Bag_SeamV_{row_index + 1}{col_index + 1}", [
                    (cursor + width, BAG_CY - 0.106, z0 + 0.004),
                    (cursor + width, BAG_CY - 0.108, z0 + height - 0.004),
                ], 0.0040, 0.0024, m["leather_strap"], parent=root)
            cursor += width
        if row_index < len(rows) - 1:
            sweep(f"PC_Bag_SeamH_{row_index + 1}", [
                (-span * 0.49, BAG_CY - 0.106, z0 + height),
                (0.0, BAG_CY - 0.109, z0 + height),
                (span * 0.49, BAG_CY - 0.106, z0 + height),
            ], 0.0040, 0.0024, m["leather_strap"], parent=root)

    # The gusset is a single wrapped piece of leather with a welt seam, not more
    # panels — flat side slabs made the whole bag read as a filing cabinet.
    for side_sign in (-1, 1):
        sweep(f"PC_Bag_Welt_{'L' if side_sign < 0 else 'R'}", [
            (side_sign * 0.196, BAG_CY - 0.096, 1.052),
            (side_sign * 0.214, BAG_CY - 0.088, 1.200),
            (side_sign * 0.216, BAG_CY - 0.086, 1.360),
            (side_sign * 0.202, BAG_CY - 0.090, 1.486),
        ], 0.016, 0.006, m["leather_gloss"], parent=root)

    # Closure: top flap, tongue and a dark turn-lock. Delivery function stays legible.
    loft("PC_Bag_Flap", [
        (1.496, 0.0, BAG_CY - 0.004, 0.196, 0.098),
        (1.526, 0.0, BAG_CY - 0.006, 0.202, 0.100),
        (1.548, 0.0, BAG_CY - 0.010, 0.186, 0.088),
        (1.562, 0.0, BAG_CY - 0.016, 0.152, 0.068),
    ], m["leather_semi"], sides=24, power=0.82, parent=root, bevel=0.012)
    # The closing tongue hangs down over the patchwork, so the flap reads as
    # leather folded over a volume rather than a lid resting on a box.
    cube("PC_Bag_FlapSkirt", (0, BAG_CY - 0.102, 1.470), (0.386, 0.020, 0.092),
         m["leather_semi"], bevel=0.010, parent=root)
    cube("PC_Bag_FlapTongue", (0, BAG_CY - 0.114, 1.416), (0.112, 0.022, 0.088),
         m["leather_gloss"], bevel=0.010, parent=root)
    cube("PC_Bag_TurnLock", (0, BAG_CY - 0.128, 1.392), (0.038, 0.016, 0.024),
         m["leather_hw"], bevel=0.005, parent=root)

    # Rolled top handle, as on the reference bag.
    sweep("PC_Bag_Handle", [
        (-0.076, BAG_CY - 0.010, 1.534),
        (-0.056, BAG_CY - 0.012, 1.584),
        (0.0, BAG_CY - 0.012, 1.598),
        (0.056, BAG_CY - 0.012, 1.584),
        (0.076, BAG_CY - 0.010, 1.534),
    ], 0.028, 0.024, m["leather_strap"], parent=root, bevel=0.008)

    # Harness: shoulder straps over the top of the jacket and down the chest.
    for sign in (-1, 1):
        tag = "L" if sign < 0 else "R"
        sweep(f"PC_Bag_Strap_{tag}", [
            (sign * 0.144, BAG_CY - 0.014, 1.514),
            (sign * 0.150, -0.146, 1.544),
            (sign * 0.152, -0.020, 1.506),
            (sign * 0.144, 0.126, 1.432),
            (sign * 0.126, 0.182, 1.284),
            (sign * 0.112, 0.184, 1.104),
        ], 0.056, 0.014, m["leather_strap"], parent=root, bevel=0.005)
        cube(f"PC_Bag_StrapAnchor_{tag}", (sign * 0.110, 0.186, 1.086),
             (0.070, 0.026, 0.036), m["leather_hw"], bevel=0.006, parent=root)
    sweep("PC_Bag_SternumStrap", [
        (-0.118, 0.186, 1.248),
        (0.0, 0.198, 1.244),
        (0.118, 0.186, 1.248),
    ], 0.026, 0.012, m["leather_strap"], parent=root)

    # Structural reinforcement along the base — it carries weight.
    loft("PC_Bag_BasePlate", [
        (1.010, 0.0, BAG_CY, 0.154, 0.072),
        (1.034, 0.0, BAG_CY, 0.178, 0.086),
    ], m["leather_gloss"], sides=20, power=0.82, parent=root, bevel=0.008)


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def build_character():
    materials = build_materials()

    part("ZOH_BODY")
    root = empty("player-character-root", (0, 0, 0), size=0.16)

    # These four names are the contract with src/player/PlayerController.ts,
    # which finds them by name and drives the stride/arm swing. Do not rename.
    arms = {
        "L": empty("player-left-arm-pivot", (-X_SHOULDER, 0.0, 1.418), parent=root),
        "R": empty("player-right-arm-pivot", (X_SHOULDER, 0.0, 1.418), parent=root),
    }
    legs = {
        "L": empty("player-left-leg-pivot", (-X_LEG, 0.004, 0.960), parent=root),
        "R": empty("player-right-leg-pivot", (X_LEG, 0.004, 0.960), parent=root),
    }

    build_body(materials, root, arms, legs)
    build_head(materials, root)
    build_hair(materials, root)
    build_jacket(materials, root, arms)
    build_jeans(materials, root, legs)
    build_greaves(materials, legs)
    build_gauntlets(materials, arms)
    build_shoes(materials, legs)
    build_bag(materials, root)

    # Re-home the body meshes that were created before their pivots existed.
    for obj in bpy.data.objects:
        if obj.parent is None and obj.name.startswith("PC_"):
            parent_keep_transform(obj, root)

    root["asset"] = "zoh-player-character"
    root["asset_stage"] = "blockout-geometry-pass"
    root["height_metres"] = 1.78
    root["forward_axis"] = "Blender +Y / glTF -Z"
    root["brief"] = "docs/assets/player-character.md"
    return root, materials


# ---------------------------------------------------------------------------
# Review scene: studio rig for form, sodium/LED rig for the actual game night.
# ---------------------------------------------------------------------------

def setup_scene():
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    try:
        scene.render.engine = "BLENDER_EEVEE"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    eevee = scene.eevee
    if hasattr(eevee, "taa_render_samples"):
        eevee.taa_render_samples = 64
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.006, 0.008, 0.013)
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass


def area_light(name, location, target, energy, size, colour):
    bpy.ops.object.light_add(type="AREA", location=location)
    light = bpy.context.object
    light.name = name
    light.data.energy = energy
    light.data.shape = "DISK"
    light.data.size = size
    light.data.color = colour
    light.rotation_euler = (Vector(target) - light.location).to_track_quat("-Z", "Y").to_euler()
    adopt(light)
    return light


def spot_light(name, location, target, energy, angle, blend, colour, radius=0.08):
    bpy.ops.object.light_add(type="SPOT", location=location)
    light = bpy.context.object
    light.name = name
    light.data.energy = energy
    light.data.spot_size = math.radians(angle)
    light.data.spot_blend = blend
    light.data.color = colour
    light.data.shadow_soft_size = radius
    light.rotation_euler = (Vector(target) - light.location).to_track_quat("-Z", "Y").to_euler()
    adopt(light)
    return light


def build_lighting(m):
    part("ZOH_REVIEW")
    ground = cube("review-ground", (0, 0, -0.012), (9.0, 9.0, 0.024),
                  material("PC_Review_Ground", (0.022, 0.024, 0.028), 0.72))

    studio = [
        area_light("studio-key", (-2.5, 2.6, 3.1), (0, 0, 1.15), 200, 2.2, (0.86, 0.90, 1.0)),
        area_light("studio-rim", (2.7, -2.4, 2.6), (0, 0, 1.25), 300, 1.6, (0.62, 0.72, 1.0)),
        area_light("studio-fill", (0.8, 3.4, 1.5), (0, 0, 1.10), 100, 3.0, (1.0, 0.88, 0.74)),
        area_light("studio-floor-bounce", (0, 0.8, 0.25), (0, 0, 0.9), 45, 2.4, (0.7, 0.75, 0.88)),
    ]

    # The world this character actually lives in: hard sodium pools in darkness.
    night = [
        spot_light("night-sodium-lamp", (-1.35, 2.2, 4.4), (0.1, 0.15, 0.6),
                   1400, 62, 0.36, (1.0, 0.56, 0.20), 0.22),
        spot_light("night-led-spill", (2.6, -2.0, 3.2), (0, -0.1, 1.4),
                   620, 74, 0.52, (0.60, 0.74, 1.0), 0.30),
        area_light("night-shopfront", (2.9, 1.7, 1.2), (0, 0.1, 1.1), 95, 1.6,
                   (1.0, 0.80, 0.52)),
    ]
    return {"ground": ground, "studio": studio, "night": night}


def set_lighting(rig, mode):
    for light in rig["studio"]:
        light.hide_render = mode != "studio"
    for light in rig["night"]:
        light.hide_render = mode != "night"
    bpy.context.scene.world.color = (0.006, 0.008, 0.013) if mode == "night" else (0.012, 0.014, 0.019)


VIEWS = (
    # filename, camera, target, lens, width, height, lighting
    ("view-a-front.png", (0.0, 4.40, 1.10), (0, 0, 1.00), 85, 900, 1200, "studio"),
    ("view-b-rear.png", (0.0, -4.40, 1.12), (0, 0, 1.02), 85, 900, 1200, "studio"),
    ("view-c-left-profile.png", (-4.40, 0.0, 1.08), (0, 0, 1.00), 85, 900, 1200, "studio"),
    ("view-d-right-profile.png", (4.40, 0.0, 1.08), (0, 0, 1.00), 85, 900, 1200, "studio"),
    ("view-e-three-quarter-front.png", (2.95, 3.30, 1.35), (0, 0, 1.02), 80, 900, 1200, "studio"),
    ("view-f-three-quarter-rear.png", (-2.70, -3.45, 1.48), (0, 0, 1.05), 80, 900, 1200, "studio"),
    ("view-g-head-cornrows.png", (0.62, 0.98, 1.80), (0, 0.01, 1.695), 105, 1000, 1000, "studio"),
    ("view-h-denim-jacket.png", (0.78, 1.34, 1.30), (0, 0.10, 1.23), 100, 1000, 1000, "studio"),
    ("view-i-delivery-bag.png", (-0.72, -1.30, 1.46), (0, -0.30, 1.32), 100, 1000, 1000, "studio"),
    ("view-j-gauntlet.png", (0.80, 0.62, 0.90), (0.244, 0.070, 0.845), 100, 1000, 1000, "studio"),
    ("view-k-greave.png", (0.66, 0.96, 0.44), (0.136, 0.020, 0.295), 100, 1000, 1000, "studio"),
    ("view-l-silver-shoe.png", (0.56, 0.78, 0.26), (0.152, 0.020, 0.055), 100, 1000, 1000, "studio"),
    ("view-m-night-streetlight.png", (2.60, 3.05, 1.42), (0, 0, 1.05), 80, 900, 1200, "night"),
    ("view-n-gameplay-camera.png", (0.0, -6.475, 3.123), (0, 0, 1.05), 38.6, 1280, 720, "night"),
)


def render_views(rig):
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    part("ZOH_REVIEW")
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "review-camera"
    camera.data.sensor_width = 36.0
    adopt(camera)
    bpy.context.scene.camera = camera
    for filename, location, target, lens, width, height, mode in VIEWS:
        set_lighting(rig, mode)
        camera.location = location
        camera.data.lens = lens
        camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
        bpy.context.scene.render.resolution_x = width
        bpy.context.scene.render.resolution_y = height
        bpy.context.scene.render.filepath = str(RENDER_DIR / filename)
        bpy.ops.render.render(write_still=True)
        print(f"  rendered {filename}")
    set_lighting(rig, "studio")


def blockout_notes():
    text = bpy.data.texts.new("PC_BLOCKOUT_NOTES")
    text.write(
        "Zealot of Harperhey - player character, blockout geometry pass.\n"
        "\n"
        "Delivered: silhouette, proportion, garment/armour relationship, material\n"
        "hierarchy, modular collection split, review renders.\n"
        "\n"
        "NOT delivered in this pass (deliberately, pending review):\n"
        "  - armature / rigging and finger drivers (brief 17-19)\n"
        "  - LOD0/1/2 chain (brief 22)\n"
        "  - textures, normal maps, packed ORM (brief 21)\n"
        "  - walking and bicycle poses (brief 23 O-P) - need the rig first\n"
        "\n"
        "Contract with the engine: the four pivot empties\n"
        "player-{left,right}-{arm,leg}-pivot are read by name in\n"
        "src/player/PlayerController.ts. Do not rename them.\n"
    )
    return text


def export_asset(root):
    GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    for child in root.children_recursive:
        child.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH),
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_apply=True,
    )


def report(root):
    meshes = [o for o in root.children_recursive if o.type == "MESH"]
    triangles = sum(len(o.data.loop_triangles) for o in meshes if o.data.loop_triangles
                    or o.data.calc_loop_triangles() is None)
    print("\n--- player character blockout ---")
    print(f"  mesh objects : {len(meshes)}")
    print(f"  triangles    : {triangles}")
    for name in COLLECTIONS:
        count = len(bpy.data.collections[name].objects)
        print(f"  {name:<22} {count:>4} objects")


def main():
    reset_scene()
    make_collections()
    setup_scene()
    root, materials = build_character()
    export_asset(root)
    rig = build_lighting(materials)
    blockout_notes()
    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    render_views(rig)
    report(root)
    print(f"Saved Blender master: {BLEND_PATH}")
    print(f"Exported blockout GLB: {GLB_PATH}")
    print(f"Rendered reviews: {RENDER_DIR}")


if __name__ == "__main__":
    main()
