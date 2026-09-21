"""Build the bougainvillea fence scene as four independent GLB assets.

Brief: references/architecture/infrastructure:objects/plants/bougainvillea/17_Bougainvillea_Fence_Scene_Assets.txt
Photo: references/architecture/infrastructure:objects/plants/bougainvillea/IMG_8966.jpg

    A  BGV_signpost_no_entry      grey column, tapered base, No Entry sign, sign lamp
    B  BGV_fence_bougainvillea    3.6 m hero closeboard fence with the climbing plant
       BGV_fence_extension        1.8 m plainer section that tiles beside it
    C  BGV_background_tree        dark canopy that stands behind the gap
    D  BGV_ground_strip_optional  kerb, tarmac, soil margin, weeds, fallen bracts

Everything is generated from seeds, so a rebuild is identical.  Surfaces come
from bougainvilleaTextures.py.  The flowers and leaves are built from a small
library of cluster and sprig variants placed many times with their own
transform and tone; each asset is then joined into one mesh per material,
which is what the game's static batching wants anyway.

Rebuild from the repository root:

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python blender/scripts/createBougainvilleaFence.py -- [--stage build|renders|validate]
"""

import json
import struct
import sys
import time
from math import cos, pi, radians, sin
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import bougainvilleaTextures as tx  # noqa: E402
from surfaceWeathering import build_pbr_material, load_image, save_rgba  # noqa: E402

PROJECT_ROOT = SCRIPT_DIR.parents[1]
SOURCE_DIR = PROJECT_ROOT / "blender" / "source" / "bougainvillea"
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "bougainvillea"
MODEL_DIR = PROJECT_ROOT / "public" / "assets" / "models" / "bougainvillea"
RENDER_DIR = PROJECT_ROOT / "renders" / "bougainvillea"
BLEND = SOURCE_DIR / "bgv_fence_scene.blend"

# Fence: origin at ground level on the fence's centre line, where the backs
# of the boards meet the rails.  Boards occupy -Y (the street side).
HERO_WIDTH = 3.6
EXTENSION_WIDTH = 1.8
FENCE_TOP = 1.8
BOARD_T = 0.019
FRONT_Y = -BOARD_T
SUN_DIR = np.array((-0.5, -0.6, 0.62)) / np.linalg.norm((-0.5, -0.6, 0.62))

# Where each asset stands in the assembled validation scene (Blender XY).
SCENE_LAYOUT = {
    "BGV_SIGNPOST_ROOT": (-1.35, -1.05, 0.0),
    "BGV_FENCE_FLOWERS_ROOT": (0.0, 0.0, 0.0),
    "BGV_FENCE_EXTENSION_ROOT": (-2.7, 0.0, 0.0),
    "BGV_TREE_ROOT": (-0.3, 1.9, 0.0),
    "BGV_GROUND_ROOT": (0.0, 0.0, 0.0),
}
EXPORTS = {
    "BGV_SIGNPOST_ROOT": "BGV_signpost_no_entry",
    "BGV_FENCE_FLOWERS_ROOT": "BGV_fence_bougainvillea",
    "BGV_FENCE_EXTENSION_ROOT": "BGV_fence_extension",
    "BGV_TREE_ROOT": "BGV_background_tree",
    "BGV_GROUND_ROOT": "BGV_ground_strip_optional",
}


def log(message):
    print(f"[bougainvillea] {message}", flush=True)


def unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.maximum(n, 1e-9)


def srgb_to_linear(c):
    c = np.asarray(c, float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


# ------------------------------------------------------------------ meshing

class Builder:
    """Accumulates vertices, faces, per-vertex UVs and material slots."""

    def __init__(self):
        self.verts, self.uvs, self.faces, self.mats, self.smooth = [], [], [], [], []
        self.count = 0

    def add(self, verts, faces, uvs, mat=0, smooth=False):
        verts = np.asarray(verts, float).reshape(-1, 3)
        uvs = np.asarray(uvs, float).reshape(-1, 2)
        assert len(verts) == len(uvs), (len(verts), len(uvs))
        self.verts.append(verts)
        self.uvs.append(uvs)
        for face in faces:
            self.faces.append(tuple(int(i) + self.count for i in face))
            self.mats.append(mat)
            self.smooth.append(smooth)
        self.count += len(verts)

    def add_batch(self, verts, faces, uvs, mat=0, smooth=False):
        """Many copies of one template: verts (N, V, 3), uvs (N, V, 2), faces for one copy."""
        n, v = verts.shape[:2]
        template = np.asarray(faces, int)
        offsets = (np.arange(n) * v + self.count)[:, None, None]
        all_faces = (template[None] + offsets).reshape(-1, template.shape[1])
        self.verts.append(verts.reshape(-1, 3))
        self.uvs.append(uvs.reshape(-1, 2))
        self.faces.extend(map(tuple, all_faces.tolist()))
        self.mats.extend([mat] * len(all_faces))
        self.smooth.extend([smooth] * len(all_faces))
        self.count += n * v

    def triangles(self):
        return sum(len(f) - 2 for f in self.faces)

    def build(self, name, materials, collection, parent=None):
        verts = np.concatenate(self.verts)
        uvs = np.concatenate(self.uvs)
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(verts.tolist(), [], self.faces)
        layer = mesh.uv_layers.new(name="UVMap")
        loop_verts = np.empty(len(mesh.loops), np.int32)
        mesh.loops.foreach_get("vertex_index", loop_verts)
        layer.data.foreach_set("uv", uvs[loop_verts].astype(np.float32).ravel())
        mesh.polygons.foreach_set("material_index", self.mats)
        mesh.polygons.foreach_set("use_smooth", self.smooth)
        for material in materials:
            mesh.materials.append(material)
        mesh.validate()
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        obj.parent = parent
        return obj


def transform(matrix, points):
    points = np.asarray(points, float)
    return points @ matrix[:3, :3].T + matrix[:3, 3]


def frame(z_axis, x_hint):
    """4x4 matrix whose Z column is z_axis and X column lies toward x_hint."""
    z = unit(z_axis)
    x = np.asarray(x_hint, float) - z * np.dot(x_hint, z)
    if np.linalg.norm(x) < 1e-6:
        x = np.cross(z, (1.0, 0.0, 0.0) if abs(z[0]) < 0.9 else (0.0, 1.0, 0.0))
    x = unit(x)
    m = np.eye(4)
    m[:3, 0], m[:3, 1], m[:3, 2] = x, np.cross(z, x), z
    return m


def translate(p):
    m = np.eye(4)
    m[:3, 3] = p
    return m


def scale(s):
    m = np.eye(4)
    m[0, 0] = m[1, 1] = m[2, 2] = s
    return m


def rot_z(a):
    m = np.eye(4)
    m[0, 0], m[0, 1], m[1, 0], m[1, 1] = cos(a), -sin(a), sin(a), cos(a)
    return m


def rot_x(a):
    m = np.eye(4)
    m[1, 1], m[1, 2], m[2, 1], m[2, 2] = cos(a), -sin(a), sin(a), cos(a)
    return m


def arclength(points):
    return np.concatenate(([0.0], np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))))


def tangents(points):
    return unit(np.gradient(points, axis=0))


def tube(builder, points, radii, sides, mat=0, v_per_m=1.0, cap=True):
    """Tube along a polyline with parallel-transported frames; u around, v along."""
    points = np.asarray(points, float)
    radii = np.broadcast_to(np.asarray(radii, float), (len(points),))
    t = tangents(points)
    ref = np.array((0.0, 0.0, 1.0)) if abs(t[0, 2]) < 0.9 else np.array((1.0, 0.0, 0.0))
    normals = [unit(np.cross(t[0], ref))]
    for i in range(1, len(points)):
        n = normals[-1] - t[i] * np.dot(normals[-1], t[i])
        normals.append(unit(n) if np.linalg.norm(n) > 1e-6 else normals[-1])
    n = np.array(normals)
    b = np.cross(t, n)
    ang = np.linspace(0, 2 * pi, sides + 1)
    ring = points[:, None, :] + radii[:, None, None] * (np.cos(ang)[None, :, None] * n[:, None, :]
                                                       + np.sin(ang)[None, :, None] * b[:, None, :])
    s = arclength(points)
    uv = np.dstack(np.broadcast_arrays(ang[None, :] / (2 * pi), s[:, None] * v_per_m)).reshape(-1, 2)
    verts = ring.reshape(-1, 3)
    width = sides + 1
    faces = [(i * width + j, i * width + j + 1, (i + 1) * width + j + 1, (i + 1) * width + j)
             for i in range(len(points) - 1) for j in range(sides)]
    if cap:
        tip = len(verts)
        verts = np.vstack((verts, points[-1] + t[-1] * radii[-1]))
        uv = np.vstack((uv, (0.5, s[-1] * v_per_m + 0.01)))
        last = (len(points) - 1) * width
        faces += [(last + j, last + j + 1, tip) for j in range(sides)]
    builder.add(verts, faces, uv, mat, smooth=True)


def lathe(builder, profile, segments, mat=0, matrix=None, v_of=None, u_range=(0.0, 1.0), cap_top=False):
    """Surface of revolution about local Z from (radius, z) pairs listed bottom to top."""
    profile = np.asarray(profile, float)
    a0, a1 = u_range
    ang = np.linspace(a0 * 2 * pi, a1 * 2 * pi, segments + 1)
    r, z = profile[:, 0], profile[:, 1]
    verts = np.stack((r[:, None] * np.cos(ang)[None], r[:, None] * np.sin(ang)[None],
                      np.broadcast_to(z[:, None], (len(z), len(ang)))), axis=-1).reshape(-1, 3)
    v = v_of(z) if v_of else arclength(np.column_stack((r, z)))
    uv = np.dstack(np.broadcast_arrays(ang[None, :] / (2 * pi), v[:, None])).reshape(-1, 2)
    width = segments + 1
    faces = [(i * width + j, i * width + j + 1, (i + 1) * width + j + 1, (i + 1) * width + j)
             for i in range(len(profile) - 1) for j in range(segments)]
    if cap_top:
        centre = len(verts)
        verts = np.vstack((verts, (0, 0, z[-1])))
        uv = np.vstack((uv, (0.5, v[-1])))
        last = (len(profile) - 1) * width
        faces += [(last + j, last + j + 1, centre) for j in range(segments)]
    if matrix is not None:
        verts = transform(matrix, verts)
    builder.add(verts, faces, uv, mat, smooth=True)


def box(builder, lo, hi, mat=0, uv_fn=None):
    """Axis-aligned box with its own vertices per face.  uv_fn(point, axis_i, axis_j) -> (u, v)."""
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    for k in range(3):
        i, j = (k + 1) % 3, (k + 2) % 3
        for sign in (-1, 1):
            corners = []
            for a, b in ((0, 0), (1, 0), (1, 1), (0, 1)):
                p = np.empty(3)
                p[k] = hi[k] if sign > 0 else lo[k]
                p[i] = hi[i] if a else lo[i]
                p[j] = hi[j] if b else lo[j]
                corners.append(p)
            if sign < 0:
                corners.reverse()
            uvs = [uv_fn(p, i, j) if uv_fn else (p[i], p[j]) for p in corners]
            builder.add(corners, [(0, 1, 2, 3)], uvs, mat)


def catmull(ctrl, step):
    p = np.asarray(ctrl, float)
    p = np.vstack((2 * p[0] - p[1], p, 2 * p[-1] - p[-2]))
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1:i + 3]
        n = max(2, int(np.linalg.norm(p2 - p1) / step))
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append(0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(p[-2])
    return np.array(out)


# ---------------------------------------------------------------- materials

def flat_material(name, srgb, rough, metal=0.0, emission=None, double_sided=False):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value = (*srgb_to_linear(srgb), 1.0)
    shader.inputs["Roughness"].default_value = rough
    shader.inputs["Metallic"].default_value = metal
    if emission is not None:
        shader.inputs["Emission Color"].default_value = (*srgb_to_linear(emission[0]), 1.0)
        shader.inputs["Emission Strength"].default_value = emission[1]
    mat.use_backface_culling = not double_sided
    return mat


REUSE_TEXTURES = False


def textured_material(name, stem, make_maps, *, double_sided=False, alpha_clip=False, roughness=0.5):
    """make_maps() authors the maps; with --reuse-textures, maps already on disk are loaded instead."""
    mat = bpy.data.materials.new(name)
    paths = {kind: TEXTURE_DIR / f"{stem}-{label}.png"
             for kind, label in (("base", "basecolor"), ("orm", "orm"), ("normal", "normal"))}
    if REUSE_TEXTURES and paths["base"].exists():
        images = {kind: load_image(path) for kind, path in paths.items() if path.exists()}
    else:
        maps = make_maps()
        images = {kind: save_rgba(paths[kind], maps[kind]) for kind in paths if kind in maps}
    base, orm, normal = images["base"], images.get("orm"), images.get("normal")
    for image in (orm, normal):
        if image is not None:
            image.colorspace_settings.name = "Non-Color"
    build_pbr_material(mat, base, orm, normal, roughness=roughness)
    if alpha_clip:
        # Base alpha -> Round -> BSDF alpha is the pattern the glTF exporter
        # writes as alphaMode MASK with a 0.5 cutoff.
        nt = mat.node_tree
        shader = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        clip = nt.nodes.new("ShaderNodeMath")
        clip.operation = "ROUND"
        nt.links.new(nt.nodes["Base Color"].outputs["Alpha"], clip.inputs[0])
        nt.links.new(clip.outputs[0], shader.inputs["Alpha"])
    mat.use_backface_culling = not double_sided
    return mat


def build_materials():
    started = time.time()
    m = {
        "sign": textured_material("MAT_sign_reflective_weathered", "bgv-sign-face", tx.sign_face),
        "sign_back": flat_material("MAT_sign_metal_back", (150, 152, 150), 0.48, metal=0.7),
        "pole": textured_material("MAT_pole_grey_metal", "bgv-pole", tx.pole_paint),
        "lamp": flat_material("MAT_lamp_housing", (196, 196, 186), 0.5),
        "lens": flat_material("MAT_lamp_lens", (232, 228, 214), 0.18, emission=((255, 226, 178), 0.8)),
        "timber": textured_material("MAT_fence_aged_timber", "bgv-fence-timber", tx.timber_atlas),
        "branch": flat_material("MAT_branch_dark_wood", (74, 60, 44), 0.8),
        "leaf": textured_material("MAT_bougainvillea_leaf", "bgv-bougainvillea-leaf", tx.leaf_atlas,
                                  double_sided=True, roughness=0.55),
        "flower": textured_material("MAT_bougainvillea_flower", "bgv-bougainvillea-bract", tx.bract_atlas,
                                    double_sided=True, alpha_clip=True, roughness=0.6),
        "tree_leaf": textured_material("MAT_tree_leaf", "bgv-tree-sprigs", tx.tree_sprig_atlas,
                                       double_sided=True, alpha_clip=True, roughness=0.6),
        "bark": textured_material("MAT_tree_bark", "bgv-tree-bark", tx.bark),
    }
    log(f"textures authored in {time.time() - started:.0f}s")
    return m


# ----------------------------------------------------------------- signpost

POLE_R = 0.038
BASE_R = 0.062
POLE_TOP = 3.2
SIGN_BOTTOM = 2.17
SIGN_CENTRE_Z = SIGN_BOTTOM + tx.SIGN_H / 2
PLATE_FRONT_Y = -0.078
PLATE_BACK_Y = -0.075


def pole_v(z):
    return np.asarray(z, float) / tx.POLE_HEIGHT_M


def rounded_rect(w, h, r, arc=6):
    pts = []
    for cx, cz, a0 in ((w / 2 - r, -h / 2 + r, -90), (w / 2 - r, h / 2 - r, 0),
                       (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180)):
        for k in range(arc + 1):
            a = radians(a0 + 90 * k / arc)
            pts.append((cx + r * cos(a), cz + r * sin(a)))
    return np.array(pts)


def build_signpost(collection, mats):
    root = bpy.data.objects.new("BGV_SIGNPOST_ROOT", None)
    collection.objects.link(root)

    shaft = Builder()
    lathe(shaft, [(POLE_R, 0.93), (POLE_R, POLE_TOP - 0.02), (POLE_R * 0.8, POLE_TOP), (0.0, POLE_TOP + 0.012)],
          20, v_of=pole_v)
    shaft.build("BGV_pole", [mats["pole"]], collection, root)

    base = Builder()
    profile = [(0.067, 0.0), (0.065, 0.018), (BASE_R, 0.04), (BASE_R, 0.244), (0.0598, 0.25), (0.0598, 0.258),
               (BASE_R, 0.264), (BASE_R, 0.78), (0.052, 0.85), (0.043, 0.905), (0.0445, 0.912), (0.0445, 0.945),
               (POLE_R, 0.955)]
    lathe(base, profile, 24, v_of=pole_v)
    # Access door on the street face: a proud curved panel with thin returns.
    for profile in ([(BASE_R + 0.0018, 0.34), (BASE_R + 0.0018, 0.66)],
                    [(BASE_R, 0.34), (BASE_R + 0.0018, 0.34)],
                    [(BASE_R + 0.0018, 0.66), (BASE_R, 0.66)]):
        lathe(base, profile, 6, v_of=pole_v, u_range=(0.70, 0.80))
    base.build("BGV_pole_base", [mats["pole"]], collection, root)

    plate = Builder()
    outline = rounded_rect(tx.SIGN_W, tx.SIGN_H, tx.SIGN_CORNER)
    n = len(outline)
    front = [(x, PLATE_FRONT_Y, z + SIGN_CENTRE_Z) for x, z in outline]
    back = [(x, PLATE_BACK_Y, z + SIGN_CENTRE_Z) for x, z in outline]
    face_uv = [((x + tx.SIGN_W / 2) / tx.SIGN_W, (z + tx.SIGN_H / 2) / tx.SIGN_H) for x, z in outline]
    plate.add(front, [tuple(range(n))], face_uv, mat=0)
    plate.add(back, [tuple(reversed(range(n)))], face_uv, mat=1)
    for k in range(n):
        k1 = (k + 1) % n
        plate.add([front[k], back[k], back[k1], front[k1]], [(0, 1, 2, 3)],
                  [(0, 0), (0, 0.01), (0.01, 0.01), (0.01, 0)], mat=1)
    plate.build("BGV_sign_plate", [mats["sign"], mats["sign_back"]], collection, root)

    mounts = Builder()
    for z in (SIGN_BOTTOM + 0.19, SIGN_BOTTOM + 0.71):
        # Extruded channel across the back of the plate, a bracket, and a band clip.
        box(mounts, (-0.34, PLATE_BACK_Y, z - 0.016), (0.34, PLATE_BACK_Y + 0.012, z + 0.016))
        box(mounts, (-0.016, PLATE_BACK_Y + 0.012, z - 0.014), (0.016, -POLE_R - 0.003, z + 0.014))
        lathe(mounts, [(POLE_R + 0.004, z - 0.016), (POLE_R + 0.004, z + 0.016)], 20, matrix=translate((0, 0, 0)))
        lathe(mounts, [(POLE_R + 0.004, z + 0.016), (POLE_R, z + 0.016)], 20)
        lathe(mounts, [(POLE_R, z - 0.016), (POLE_R + 0.004, z - 0.016)], 20)
        for side in (-1, 1):
            box(mounts, (side * 0.004 - 0.003, -POLE_R - 0.012, z - 0.01), (side * 0.004 + 0.003, -POLE_R - 0.003, z + 0.01))
    mounts.build("BGV_sign_mounts", [mats["sign_back"]], collection, root)

    lamp = Builder()
    tilt = rot_x(radians(-9))
    # The housing sits on the column head and overhangs the sign face,
    # tilted a few degrees so its lens looks down and forward onto it.
    centre = translate((0.0, -0.125, POLE_TOP + 0.05)) @ tilt
    housing = [(0.148, 0.0), (0.158, 0.01), (0.163, 0.026), (0.156, 0.042), (0.13, 0.056), (0.08, 0.066), (0.0, 0.07)]
    lathe(lamp, housing, 28, mat=0, matrix=centre)
    lathe(lamp, [(0.132, -0.006), (0.148, 0.0)], 28, mat=0, matrix=centre)
    lathe(lamp, [(0.0, -0.012), (0.07, -0.011), (0.132, -0.006)], 28, mat=1, matrix=centre)
    stub = catmull([(0.0, 0.0, POLE_TOP - 0.01), (0.0, 0.006, POLE_TOP + 0.02), (0.0, 0.012, POLE_TOP + 0.05)], 0.01)
    tube(lamp, stub, 0.016, 8, mat=0)
    lamp.build("BGV_lamp", [mats["lamp"], mats["lens"]], collection, root)
    return root


# -------------------------------------------------------------------- fence

def timber_u(col, local, flip=False):
    local = 1 - local if flip else local
    return (col + 0.03 + 0.94 * np.clip(local, 0, 1)) / tx.TIMBER_COLUMNS


def build_boards(builder, width, rng):
    """Closeboard: individually cut, slightly leaning, bowed and offset boards."""
    x = -width / 2
    index = 0
    while x < width / 2 - 0.01:
        w = min(rng.uniform(0.094, 0.106), width / 2 - x)
        col = int(rng.integers(tx.TIMBER_COLUMNS))
        flip = bool(rng.random() < 0.5)
        v_off = rng.uniform(0.0, 0.07)
        lean = rng.normal(0, 0.0035)
        bow = rng.normal(0, 0.0018)
        cup = rng.normal(0, 0.0012)
        dy = rng.normal(0, 0.0015)
        top_l = FENCE_TOP + rng.uniform(-0.016, 0.008)
        top_r = top_l + rng.normal(0, 0.005)
        c = 0.0022
        prof = [(0, 0), (0, -BOARD_T + c), (c, -BOARD_T), (w - c, -BOARD_T), (w, -BOARD_T + c), (w, 0)]
        rows = (0.02, 0.6, 1.2, None)

        def point(px, py, row):
            z = row if row is not None else top_l + (top_r - top_l) * px / w
            shift = lean * z + bow * sin(pi * z / FENCE_TOP)
            return (x + px + shift, py + dy + cup * sin(pi * px / w), z)

        for e in range(len(prof)):
            (ax, ay), (bx, by) = prof[e], prof[(e + 1) % len(prof)]
            verts, uvs = [], []
            for row in rows:
                for px, py in ((ax, ay), (bx, by)):
                    p = point(px, py, row)
                    if ax == bx:  # board side: runs into the joint, so sample the dark edge
                        local = abs(py) / 0.1 if ax == 0 else 1 - abs(py) / 0.1
                    else:
                        local = px / w
                    verts.append(p)
                    uvs.append((timber_u(col, local, flip), (p[2] + v_off) / tx.BOARD_LENGTH_M))
            faces = [(2 * r, 2 * r + 1, 2 * r + 3, 2 * r + 2) for r in range(len(rows) - 1)]
            builder.add(verts, faces, uvs)
        top = [point(px, py, None) for px, py in prof]
        builder.add(top, [tuple(range(len(prof)))],
                    [(timber_u(col, px / w, flip), 0.985 + 0.01 * (py / BOARD_T)) for px, py in prof])
        x += w + rng.choice((0.0, 0.0, 0.001, 0.002, 0.003, 0.006))
        index += 1
    return index


def build_fence_structure(builder, width, rng):
    """Posts and three horizontal rails behind the boards, spaced so modules tile."""

    def uv_fn(long_axis, col):
        def fn(p, i, j):
            axes = (i, j)
            if long_axis in axes:
                across = j if i == long_axis else i
                return timber_u(col, (p[across] % 0.1) / 0.1), p[long_axis] / tx.BOARD_LENGTH_M
            return timber_u(col, (p[i] % 0.1) / 0.1), 0.99 + (p[j] % 0.01)
        return fn

    for z in (0.3, 0.95, 1.6):
        box(builder, (-width / 2, 0.001, z - 0.045), (width / 2, 0.046, z + 0.045),
            uv_fn=uv_fn(0, int(rng.integers(tx.TIMBER_COLUMNS))))
    for px in np.arange(-width / 2 + 0.9, width / 2, 1.8):
        box(builder, (px - 0.05, 0.046, 0.0), (px + 0.05, 0.146, FENCE_TOP - 0.05),
            uv_fn=uv_fn(2, int(rng.integers(tx.TIMBER_COLUMNS))))


# ------------------------------------------------------------- the climber

HERO_CANES = [
    # The main arched mass, upper-left of centre, spilling over the top.
    [(-1.0, 0.3, 1.5), (-0.95, 0.06, 1.9), (-0.75, -0.18, 2.3), (-0.35, -0.32, 2.28), (0.0, -0.3, 1.98), (0.2, -0.22, 1.6)],
    [(-0.7, 0.3, 1.55), (-0.62, 0.05, 1.95), (-0.5, -0.12, 2.55), (-0.2, -0.2, 2.7), (0.1, -0.15, 2.55)],
    [(-0.4, 0.3, 1.55), (-0.42, 0.04, 1.9), (-0.55, -0.3, 1.75), (-0.72, -0.4, 1.4), (-0.68, -0.36, 1.05), (-0.6, -0.3, 0.85)],
    [(-1.3, 0.3, 1.55), (-1.25, 0.05, 1.92), (-1.1, -0.2, 2.25), (-0.8, -0.25, 2.42)],
    [(-0.9, 0.3, 1.5), (-0.95, 0.05, 1.9), (-1.15, -0.25, 1.8), (-1.3, -0.3, 1.45), (-1.25, -0.28, 1.1), (-1.1, -0.25, 0.9)],
    [(-0.55, 0.3, 1.55), (-0.5, 0.05, 1.92), (-0.4, -0.3, 2.1), (-0.15, -0.45, 1.95), (0.05, -0.42, 1.7)],
    [(-0.85, 0.3, 1.6), (-0.8, 0.05, 1.95), (-0.65, -0.35, 2.05), (-0.45, -0.5, 1.85), (-0.35, -0.45, 1.55)],
    [(-0.25, 0.3, 1.6), (-0.3, 0.06, 1.98), (-0.35, -0.2, 2.35), (-0.6, -0.35, 2.45), (-0.95, -0.3, 2.2)],
    # Long canes reaching right along the fence and dropping.
    [(-0.2, 0.3, 1.5), (-0.15, 0.04, 1.9), (0.35, -0.1, 1.9), (0.9, -0.12, 1.62), (1.35, -0.1, 1.3), (1.65, -0.12, 0.95), (1.78, -0.15, 0.7)],
    [(0.2, 0.3, 1.5), (0.25, 0.04, 1.88), (0.6, -0.06, 1.55), (0.95, -0.05, 1.1), (1.3, -0.06, 0.7), (1.55, -0.1, 0.4)],
    [(0.5, 0.3, 1.55), (0.55, 0.04, 1.9), (0.95, -0.06, 2.05), (1.4, -0.05, 1.95), (1.75, -0.04, 1.7)],
    [(0.0, 0.3, 1.5), (0.02, 0.04, 1.9), (0.1, -0.22, 1.6), (0.12, -0.28, 1.25), (0.05, -0.25, 1.0)],
    # Stems traced flat across the timber.
    [(0.75, 0.2, 1.55), (0.78, 0.03, 1.86), (0.85, -0.03, 1.5), (1.05, -0.03, 1.05), (1.2, -0.04, 0.6), (1.4, -0.05, 0.3)],
    [(-0.3, 0.2, 1.55), (-0.28, 0.03, 1.86), (-0.25, -0.03, 1.5), (-0.35, -0.035, 1.2)],
    # Whips reaching up past the fence line.
    [(-0.2, 0.35, 1.6), (-0.15, 0.1, 2.1), (-0.1, -0.02, 2.6), (0.15, -0.06, 2.85)],
    [(1.0, 0.3, 1.6), (1.05, 0.08, 2.0), (1.3, 0.0, 2.25)],
]

EXTENSION_CANES = [
    [(0.3, 0.3, 1.55), (0.28, 0.04, 1.88), (0.1, -0.05, 1.7), (-0.2, -0.05, 1.35), (-0.45, -0.07, 1.1)],
    [(-0.5, 0.3, 1.6), (-0.52, 0.05, 1.9), (-0.7, -0.08, 2.05)],
    [(0.6, 0.3, 1.6), (0.62, 0.04, 1.88), (0.8, -0.04, 1.6)],
]


def hero_density(p):
    x, z = p[0], p[2]
    main = np.exp(-((x + 0.45) / 0.7) ** 2 - ((z - 2.05) / 0.42) ** 2)
    right = 0.55 * np.exp(-((x - 1.15) / 0.55) ** 2 - ((z - 1.25) / 0.55) ** 2)
    low = 0.35 * np.exp(-((x + 0.3) / 0.45) ** 2 - ((z - 1.1) / 0.3) ** 2)
    return float(np.clip(main + right + low + 0.08, 0, 1))


def extension_density(p):
    return 0.18


def hidden(p):
    return p[1] > 0.02 and p[2] < FENCE_TOP + 0.02


def clear_fence(points, radius, half_width):
    """Keep stems in front of the boards wherever they are not clearly behind them."""
    points = points.copy()
    limit = FRONT_Y - radius - 0.004
    m = (points[:, 2] < FENCE_TOP + 0.035) & (points[:, 1] < 0.06) & (np.abs(points[:, 0]) < half_width + 0.05)
    points[m, 1] = np.minimum(points[m, 1], limit)
    points[:, 2] = np.maximum(points[:, 2], 0.03)
    return points


def wobble(points, rng, amp):
    s = arclength(points)
    off = np.zeros_like(points)
    for axis in range(3):
        for _ in range(2):
            off[:, axis] += amp * rng.uniform(0.4, 1.0) * np.sin(2 * pi * s / rng.uniform(0.12, 0.4) + rng.uniform(0, 2 * pi))
    return points + off


def tone_index(rng, sunlit):
    weights = np.array((1.3 * sunlit, 1.0, 0.75 * (1 - sunlit) + 0.2, 0.45 * (1 - sunlit) + 0.05))
    return int(rng.choice(4, p=weights / weights.sum()))


def sunlit_at(p, facing):
    return float(np.clip(0.45 + 0.35 * np.dot(facing, SUN_DIR) + 0.25 * (p[2] - 1.6) - 1.2 * (p[1] + 0.1), 0, 1))


# Leaflet (length 1 along +X, blade in XY, facing +Z) and bract (same frame).
LEAFLET_2D = np.array([(0, 0), (0.3, 0.24), (0.65, 0.2), (1, 0), (0.65, -0.2), (0.3, -0.24)])
LEAFLET_FACES = [(0, 1, 5), (1, 4, 5), (1, 2, 4), (2, 3, 4)]
# Bract card: a coarse envelope around the alpha-cut rounded bract, with a
# centre spine so it can cup.  Card width is BRACT_WIDTH x its length.
BRACT_WIDTH = 0.85
BRACT_2D = np.array([(0, -0.15), (0, 0.15), (0.4, -0.5), (0.4, 0), (0.4, 0.5), (1, -0.5), (1, 0), (1, 0.5)]) * (1, BRACT_WIDTH)
BRACT_FACES = [(0, 1, 3), (0, 3, 2), (1, 4, 3), (2, 3, 6), (2, 6, 5), (3, 4, 7), (3, 7, 6)]


def orient(points2d, faces):
    out = []
    for a, b, c in faces:
        ab, ac = points2d[b] - points2d[a], points2d[c] - points2d[a]
        out.append((a, b, c) if ab[0] * ac[1] - ab[1] * ac[0] > 0 else (a, c, b))
    return out


LEAFLET_FACES = orient(LEAFLET_2D, LEAFLET_FACES)
BRACT_FACES = orient(BRACT_2D, BRACT_FACES)


def leaflet_template():
    x, y = LEAFLET_2D[:, 0], LEAFLET_2D[:, 1]
    z = 0.28 * np.abs(y) - 0.1 * x * x  # folded along the midrib, tip drooping
    return np.column_stack((x, y, z)), np.column_stack((0.5 + y / 0.5, x))


def bract_template():
    x, y = BRACT_2D[:, 0], BRACT_2D[:, 1]
    z = 0.22 * (y / (0.5 * BRACT_WIDTH)) ** 2 * (0.3 + x) + 0.1 * x * x  # papery cup, rim turned in
    return np.column_stack((x, y, z)), np.column_stack((0.5 + y / BRACT_WIDTH, x))


LEAFLET_VERTS, LEAFLET_UV = leaflet_template()
BRACT_VERTS, BRACT_UV = bract_template()

# Sprig variants: (position along the petiole, angle in degrees, relative length).
SPRIGS = (
    ((0.0, 0, 1.0),),
    ((0.45, 0, 0.9), (0.2, 55, 0.7), (0.2, -55, 0.7)),
    ((0.85, 0, 0.85), (0.3, 60, 0.62), (0.3, -60, 0.62), (0.6, 48, 0.74), (0.6, -48, 0.74)),
    ((0.0, 38, 0.9), (0.0, -42, 0.8)),
)
SPRIG_WEIGHTS = np.array((0.3, 0.3, 0.2, 0.2))


def make_cluster_variants(rng):
    """Eight flower-cluster shapes: (flower position, axis, size) in cluster space (+Z out)."""
    specs = ((5, 0.045, 0.4), (7, 0.055, 0.45), (9, 0.065, 0.5), (12, 0.075, 0.5),
             (15, 0.09, 0.45), (18, 0.1, 0.4), (10, 0.08, 0.25), (6, 0.05, 0.6))
    variants = []
    for count, radius, height in specs:
        points, tries = [], 0
        spacing = 1.3 * radius / np.sqrt(count)
        while len(points) < count and tries < 800:
            tries += 1
            q = rng.uniform(-radius, radius, 2)
            q[1] *= rng.uniform(0.6, 1.0)  # most clusters are longer than wide
            if np.hypot(*q) <= radius and all(np.hypot(*(q - o)) > spacing for o in points):
                points.append(q)
        flowers = []
        for q in points:
            r = np.hypot(*q) / radius
            pos = np.array((q[0], q[1], height * radius * (1 - r * r)))
            axis = unit((q[0] / radius * 0.9, q[1] / radius * 0.9, 1.0))
            flowers.append((pos, axis, rng.uniform(0.85, 1.15), rng.uniform(0, 2 * pi)))
        variants.append(flowers)
    return variants


class Climber:
    """Stems, sprigs and flower clusters for one fence module."""

    def __init__(self, width, canes, density, seed):
        self.width, self.half = width, width / 2
        self.density = density
        self.rng = np.random.default_rng(seed)
        self.variants = make_cluster_variants(np.random.default_rng(seed + 1))
        self.primary, self.secondary = [], []
        self.leaflets, self.leaf_tones = [], []
        self.bracts, self.bract_tones = [], []
        self.cluster_centres = []
        self.grow(canes)

    # -- stems
    def grow(self, canes):
        rng = self.rng
        for ctrl in canes:
            pts = wobble(catmull(ctrl, 0.03), rng, 0.008)
            radii = np.linspace(0.0085, 0.0028, len(pts)) * rng.uniform(0.85, 1.15)
            self.primary.append((clear_fence(pts, radii[0], self.half), radii))
        for pts, radii in list(self.primary):
            s = arclength(pts)
            t = tangents(pts)
            next_s = rng.uniform(0.05, 0.15)
            for i in range(len(pts)):
                if s[i] < next_s or hidden(pts[i]):
                    continue
                next_s = s[i] + rng.uniform(0.09, 0.2)
                d = self.density(pts[i])
                self.branch(pts[i], t[i], min(radii[i] * 0.6, 0.0045), rng.uniform(0.06, 0.2) + 0.22 * d * rng.random(), 1)

    def branch(self, start, tangent, radius, length, depth):
        rng = self.rng
        direction = unit(tangent * 0.35 + np.array((0, -1.0, 0)) * rng.uniform(0.3, 0.8) + rng.normal(0, 0.45, 3))
        steps = max(3, int(length / 0.025))
        pts = [start]
        for _ in range(steps):
            direction = unit(direction + np.array((0, 0, -0.08)) + rng.normal(0, 0.12, 3))
            pts.append(pts[-1] + direction * length / steps)
        pts = clear_fence(np.array(pts), radius, self.half)
        radii = np.linspace(radius, 0.0014, len(pts))
        self.secondary.append((pts, radii))
        if depth == 1 and rng.random() < 0.35:
            k = len(pts) // 2
            self.branch(pts[k], tangents(pts)[k], radius * 0.7, length * rng.uniform(0.35, 0.6), 2)

    # -- leaves
    def add_sprig(self, p, direction, normal_hint, size):
        rng = self.rng
        m = frame(normal_hint, direction)
        m[:3, 3] = p
        variant = SPRIGS[rng.choice(len(SPRIGS), p=SPRIG_WEIGHTS)]
        tone = tone_index(rng, sunlit_at(p, m[:3, 2]))
        for along, angle, length in variant:
            leaf = (m @ scale(size) @ translate((along, 0, 0)) @ rot_z(radians(angle + rng.normal(0, 8)))
                    @ rot_x(rng.normal(0, 0.25)) @ scale(length * rng.uniform(0.9, 1.1)))
            self.leaflets.append(leaf)
            self.leaf_tones.append(tone if rng.random() < 0.8 else tone_index(rng, 0.5))

    def leaf_along(self, pts, bare):
        rng = self.rng
        s = arclength(pts)
        t = tangents(pts)
        next_s = rng.uniform(0.01, 0.05)
        side = 1
        for i in range(len(pts)):
            if s[i] < next_s:
                continue
            next_s = s[i] + rng.uniform(0.025, 0.05)
            p = pts[i]
            if hidden(p) or any(a <= s[i] <= b for a, b in bare):
                continue
            if rng.random() > 0.5 + 0.4 * self.density(p):
                continue
            side = -side
            lateral = unit(np.cross(t[i], (0, -1.0, 0)) + 1e-6)
            direction = unit(lateral * side * 0.8 + t[i] * 0.5 + rng.normal(0, 0.35, 3))
            normal = unit((0, -0.7, 0.7) + rng.normal(0, 0.6, 3))
            self.add_sprig(p, direction, normal, rng.uniform(0.045, 0.066))

    # -- flowers
    def add_cluster(self, p, tangent, d):
        rng = self.rng
        axis = unit(np.array((0, -1.0, 0.45)) + rng.normal(0, 0.45, 3) + tangent * 0.2)
        if p[2] < FENCE_TOP and axis[1] > -0.25:
            axis[1] = -0.25
            axis = unit(axis)
        centre = p + axis * 0.012
        cluster = frame(axis, rng.normal(0, 1, 3))
        cluster[:3, 3] = centre
        size = rng.uniform(0.75, 1.2) * (0.8 + 0.4 * d)
        cluster = cluster @ scale(size)
        sun = sunlit_at(centre, axis)
        for pos, f_axis, f_size, twist in self.variants[rng.integers(len(self.variants))]:
            flower = cluster @ translate(pos) @ frame(f_axis, (1, 0, 0)) @ rot_z(twist)
            tone = tone_index(rng, sun)
            length = 0.03 * f_size
            for k in range(3):
                phi = k * 2 * pi / 3 + rng.normal(0, 0.2)
                theta = radians(rng.uniform(52, 68))
                out = np.array((sin(theta) * cos(phi), sin(theta) * sin(phi), cos(theta)))
                tang = np.array((-sin(phi), cos(phi), 0.0))
                b = np.eye(4)
                b[:3, 0], b[:3, 1], b[:3, 2] = out, tang, np.cross(out, tang)
                self.bracts.append(flower @ b @ scale(length))
                self.bract_tones.append(tone if rng.random() < 0.85 else min(tone + 1, 3))
        for _ in range(int(rng.integers(1, 4))):
            direction = unit(rng.normal(0, 1, 3) + axis * 0.2)
            self.add_sprig(centre - axis * 0.02, direction, unit(axis + rng.normal(0, 0.5, 3)), rng.uniform(0.045, 0.06))
        self.cluster_centres.append(centre)

    def place_flowers(self):
        rng = self.rng
        candidates = []
        for pts, _ in self.secondary:
            candidates.append((pts[-1], tangents(pts)[-1], True))
            if len(pts) > 4:
                candidates.append((pts[len(pts) // 2], tangents(pts)[len(pts) // 2], False))
        for pts, _ in self.primary:
            t = tangents(pts)
            s = arclength(pts)
            next_s = 0.0
            for i in range(len(pts)):
                if s[i] >= next_s:
                    next_s = s[i] + 0.07
                    candidates.append((pts[i], t[i], False))
        order = rng.permutation(len(candidates))
        for index in order:
            p, t, tip = candidates[index]
            if hidden(p):
                continue
            d = self.density(p)
            chance = (0.25 + 0.9 * d) if tip else 0.9 * d
            if rng.random() > chance:
                continue
            if self.cluster_centres and np.min(np.linalg.norm(np.array(self.cluster_centres) - p, axis=1)) < 0.045 + 0.065 * (1 - d):
                continue
            self.add_cluster(p, t, d)

    def populate(self):
        rng = self.rng
        for pts, _ in self.primary:
            s = arclength(pts)
            bare = []
            for _ in range(int(rng.integers(1, 3))):
                a = rng.uniform(0.2, max(0.3, s[-1] - 0.3))
                bare.append((a, a + rng.uniform(0.12, 0.3)))
            self.leaf_along(pts, bare)
        for pts, _ in self.secondary:
            self.leaf_along(pts, [])
        self.place_flowers()

    # -- meshing
    def press_to_fence(self, verts):
        """Leaves and bracts lying against the boards flatten onto them instead of passing through."""
        v = verts.reshape(-1, 3)
        m = (v[:, 2] < FENCE_TOP + 0.01) & (np.abs(v[:, 0]) < self.half + 0.02) & (v[:, 1] > FRONT_Y - 0.004) & (v[:, 1] < 0.08)
        v[m, 1] = FRONT_Y - 0.004
        return v.reshape(verts.shape)

    def instanced(self, matrices, tones, template, template_uv):
        mats = np.array(matrices)
        verts = np.einsum("nij,vj->nvi", mats[:, :3, :3], template) + mats[:, None, :3, 3]
        uv = np.empty((len(mats), len(template), 2))
        for tone in range(4):
            sel = np.array(tones) == tone
            u, v = tx.tile_uv(tone, template_uv[:, 0], template_uv[:, 1])
            uv[sel] = np.column_stack((u, v))
        return self.press_to_fence(verts), uv

    def build(self, prefix, collection, parent, mats):
        counts = {}
        primary = Builder()
        for pts, radii in self.primary:
            tube(primary, pts[::2] if len(pts) > 8 else pts, radii[::2] if len(pts) > 8 else radii, 5, v_per_m=4.0)
        secondary = Builder()
        for pts, radii in self.secondary:
            keep = np.unique(np.append(np.arange(0, len(pts), 2), len(pts) - 1))
            tube(secondary, pts[keep], radii[keep], 4, v_per_m=4.0)
        leaves = Builder()
        if self.leaflets:
            verts, uv = self.instanced(self.leaflets, self.leaf_tones, LEAFLET_VERTS, LEAFLET_UV)
            leaves.add_batch(verts, LEAFLET_FACES, uv, smooth=True)
        flowers = Builder()
        if self.bracts:
            verts, uv = self.instanced(self.bracts, self.bract_tones, BRACT_VERTS, BRACT_UV)
            flowers.add_batch(verts, BRACT_FACES, uv, smooth=True)
        for name, builder, material in (("primary_stems", primary, "branch"), ("secondary_stems", secondary, "branch"),
                                        ("leaves", leaves, "leaf"), ("flowers", flowers, "flower")):
            if not builder.faces:
                continue
            builder.build(f"{prefix}_{name}", [mats[material]], collection, parent)
            counts[name] = builder.triangles()
        counts["clusters"] = len(self.cluster_centres)
        counts["leaflets"] = len(self.leaflets)
        counts["bracts"] = len(self.bracts)
        return counts


def build_fence(collection, mats, root_name, width, canes, density, seed):
    root = bpy.data.objects.new(root_name, None)
    collection.objects.link(root)
    rng = np.random.default_rng(seed)
    prefix = "BGV" if root_name == "BGV_FENCE_FLOWERS_ROOT" else "BGV_ext"
    boards = Builder()
    n = build_boards(boards, width, rng)
    boards.build(f"{prefix}_fence_boards", [mats["timber"]], collection, root)
    structure = Builder()
    build_fence_structure(structure, width, rng)
    structure.build(f"{prefix}_fence_structure", [mats["timber"]], collection, root)
    climber = Climber(width, canes, density, seed + 7)
    climber.populate()
    stem_prefix = f"{prefix}_bougainvillea"
    counts = climber.build(stem_prefix, collection, root, mats)
    counts.update(boards=n, board_tris=boards.triangles(), structure_tris=structure.triangles())
    log(f"{root_name}: {counts}")
    return root, climber


# --------------------------------------------------------------------- tree

TREE_BRANCHES = (
    ((0.05, 0.0, 2.2), (-2.6, -0.5, 4.3)),
    ((0.05, 0.0, 2.3), (-1.4, -0.9, 5.6)),
    ((0.1, 0.0, 2.4), (0.4, -0.6, 6.1)),
    ((0.1, 0.0, 2.2), (1.9, -0.7, 5.0)),
    ((0.05, 0.0, 1.9), (2.8, -0.4, 3.4)),
    ((0.0, 0.0, 1.6), (-2.9, -0.9, 2.6)),
    ((0.1, 0.0, 2.0), (0.9, 0.8, 4.8)),
    ((0.0, 0.0, 1.4), (-1.3, -1.1, 2.2)),
    ((0.1, 0.0, 1.5), (1.3, -1.1, 2.1)),
)
CANOPY_CENTRE = np.array((0.0, -0.2, 4.0))
CANOPY_RADII = np.array((3.0, 1.5, 2.3))
CARD_2D = np.array([(-0.5, 0, 0), (0, 0, 0.12), (0.5, 0, 0), (-0.5, 1, 0), (0, 1, 0.12), (0.5, 1, 0)], float)
CARD_FACES = [(0, 1, 4, 3), (1, 2, 5, 4)]


def build_tree(collection, mats, seed=91):
    rng = np.random.default_rng(seed)
    root = bpy.data.objects.new("BGV_TREE_ROOT", None)
    collection.objects.link(root)

    trunk = Builder()
    trunk_pts = wobble(catmull([(0, 0, 0), (0.04, 0.02, 1.2), (0.1, 0.0, 2.5)], 0.1), rng, 0.02)
    trunk_pts[0] = (0, 0, -0.05)
    tube(trunk, trunk_pts, np.linspace(0.16, 0.1, len(trunk_pts)), 12, v_per_m=1.0, cap=False)
    # A flared root collar so the trunk meets the ground.
    lathe(trunk, [(0.26, -0.05), (0.2, 0.04), (0.165, 0.18)], 12, v_of=lambda z: z)
    trunk.build("BGV_tree_trunk", [mats["bark"]], collection, root)

    branches = Builder()
    clumps = []
    for start, end in TREE_BRANCHES:
        start, end = np.array(start), np.array(end)
        mid = start + (end - start) * 0.5 + np.array((0, 0, 0.45)) + rng.normal(0, 0.15, 3)
        pts = wobble(catmull([start, mid, end], 0.12), rng, 0.04)
        tube(branches, pts, np.linspace(0.085, 0.025, len(pts)), 7, v_per_m=1.0)
        t = tangents(pts)
        for f in (0.55, 0.78, 0.97):
            clumps.append((pts[int(f * (len(pts) - 1))] + rng.normal(0, 0.2, 3), rng.uniform(0.6, 0.95)))
        for _ in range(2):
            k = int(rng.uniform(0.4, 0.8) * (len(pts) - 1))
            direction = unit(t[k] + rng.normal(0, 0.7, 3) + (0, 0, 0.3))
            length = rng.uniform(0.8, 1.3)
            twig = wobble(np.array([pts[k] + direction * length * f for f in np.linspace(0, 1, 6)]), rng, 0.03)
            tube(branches, twig, np.linspace(0.03, 0.01, len(twig)), 5, v_per_m=1.0)
            clumps.append((twig[-1] + rng.normal(0, 0.15, 3), rng.uniform(0.55, 0.85)))
    branches.build("BGV_tree_branches", [mats["bark"]], collection, root)

    cards, tones = [], []
    for centre, radius in clumps:
        for _ in range(int(rng.integers(14, 21))):
            offset = unit(rng.normal(0, 1, 3)) * radius * rng.uniform(0.2, 1.0) ** 0.5
            p = centre + offset * np.array((1.0, 0.8, 0.75))
            outward = unit((p - CANOPY_CENTRE) / CANOPY_RADII)
            normal = unit(outward * 0.7 + unit(offset) * 0.4 + rng.normal(0, 0.6, 3))
            up = np.array((0, 0, 1.0)) * 0.5 + outward * 0.5 + rng.normal(0, 0.5, 3)
            m = frame(normal, up)
            m[:, [0, 1]] = m[:, [1, 0]]  # card X across, Y up the sprig
            m[:3, 0] *= -1
            size = rng.uniform(0.7, 1.05)
            m = translate(p) @ m @ scale(size) @ translate((0, -0.5, 0))
            depth = np.linalg.norm((p - CANOPY_CENTRE) / CANOPY_RADII)
            exposure = 0.75 * depth + 0.4 * np.dot(outward, SUN_DIR) + 0.35 * np.linalg.norm(offset) / radius
            tones.append(0 if exposure > 1.2 else 1 if exposure > 0.95 else 2 if exposure > 0.7 else 3)
            cards.append(m)
    mats_arr = np.array(cards)
    verts = np.einsum("nij,vj->nvi", mats_arr[:, :3, :3], CARD_2D) + mats_arr[:, None, :3, 3]
    uv = np.empty((len(cards), len(CARD_2D), 2))
    for tone in range(4):
        sel = np.array(tones) == tone
        u, v = tx.tile_uv(tone, CARD_2D[:, 0] + 0.5, CARD_2D[:, 1])
        uv[sel] = np.column_stack((u, v))
    foliage = Builder()
    foliage.add_batch(verts, CARD_FACES, uv)
    foliage.build("BGV_tree_foliage", [mats["tree_leaf"]], collection, root)
    log(f"tree: trunk {trunk.triangles()} tris, branches {branches.triangles()} tris, {len(cards)} foliage cards "
        f"({foliage.triangles()} tris), tones {np.bincount(tones, minlength=4).tolist()}")
    return root


# ------------------------------------------------------------------- ground

GROUND_PROFILE = [(-1.62, -0.11), (-1.34, -0.11), (-1.327, -0.03), (-1.32, -0.006), (-1.305, 0.0), (-1.18, 0.0),
                  (-0.98, 0.0), (-0.78, 0.0), (-0.58, 0.0), (-0.38, 0.0), (-0.34, 0.006), (-0.28, 0.0),
                  (-0.22, 0.0), (-0.16, 0.0), (-0.1, 0.0), (-0.05, 0.0), (0.0, 0.0), (0.06, 0.0)]
SOIL_Y = -0.36


def ground_height(x, y):
    """Soil banks up toward the fence and is lumpy; everything else is the profile."""
    ys, zs = np.array(GROUND_PROFILE).T
    base = np.interp(y, ys, zs)
    soil = np.clip((np.asarray(y) - SOIL_Y) / 0.26, 0, 1)
    lumps = (0.006 * np.sin(x * 23.0 + np.sin(y * 17.0)) + 0.005 * np.sin(x * 51.0 + y * 37.0)
             + 0.004 * np.cos(x * 9.0 - y * 29.0))
    return base + soil * (0.014 + lumps)


def build_ground(collection, mats, seed=101):
    rng = np.random.default_rng(seed)
    root = bpy.data.objects.new("BGV_GROUND_ROOT", None)
    collection.objects.link(root)
    prof = np.array(GROUND_PROFILE)
    s = arclength(prof)
    depth = s[-1]
    bands = (s[1], s[5], float(np.interp(SOIL_Y, prof[:, 0], s)))
    mats["ground"] = textured_material("MAT_ground_rough_optional", "bgv-ground-strip",
                                       lambda: tx.ground_strip(bands, HERO_WIDTH, depth))

    xs = np.linspace(-HERO_WIDTH / 2, HERO_WIDTH / 2, 73)
    verts, uvs = [], []
    for y, z0, sv in zip(prof[:, 0], prof[:, 1], s):
        for x in xs:
            z = ground_height(x, y) if y > SOIL_Y else z0
            verts.append((x, y, z))
            uvs.append(((x + HERO_WIDTH / 2) / HERO_WIDTH, sv / depth))
    nx = len(xs)
    faces = [(j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i)
             for j in range(len(prof) - 1) for i in range(nx - 1)]
    ground = Builder()
    ground.add(verts, faces, uvs, smooth=True)
    ground.build("BGV_ground", [mats["ground"]], collection, root)

    weeds = Builder()
    blade = np.array([(-0.004, 0, 0), (0.004, 0, 0), (-0.003, 0.01, 0.5), (0.003, 0.012, 0.5), (0, 0.04, 1.0)])
    blade_uv = np.array([(0.45, 0), (0.55, 0), (0.46, 0.5), (0.54, 0.5), (0.5, 1.0)])
    blade_faces = [(0, 1, 3), (0, 3, 2), (2, 3, 4)]
    tuft_sites = ([(rng.uniform(-1.75, 1.75), rng.uniform(-0.2, -0.03)) for _ in range(34)]
                  + [(rng.uniform(-1.7, 1.7), rng.uniform(-1.2, -1.16)) for _ in range(9)]
                  + [(rng.uniform(-1.6, 1.6), rng.uniform(-1.0, -0.5)) for _ in range(4)])
    blade_mats, blade_tones = [], []
    for x, y in tuft_sites:
        base = np.array((x, y, float(ground_height(x, y)) - 0.004))
        height = rng.uniform(0.07, 0.24) * (1.0 if y > SOIL_Y else 0.7)
        for _ in range(int(rng.integers(5, 11))):
            m = translate(base + np.append(rng.normal(0, 0.012, 2), 0)) @ rot_z(rng.uniform(0, 2 * pi)) @ rot_x(rng.uniform(-0.45, 0.05))
            m = m @ np.diag((1.0, height * rng.uniform(0.6, 1.2), height * rng.uniform(0.6, 1.1), 1.0))
            blade_mats.append(m)
            blade_tones.append(int(rng.choice((1, 2, 2, 3))))
    for x, y in [(rng.uniform(-1.7, 1.7), rng.uniform(-0.3, -0.05)) for _ in range(10)]:
        # Low broad-leaved rosettes: leaflets laid almost flat.
        base = np.array((x, y, float(ground_height(x, y)) + 0.003))
        for k in range(int(rng.integers(5, 8))):
            m = translate(base) @ rot_z(k * 2 * pi / 6 + rng.normal(0, 0.2)) @ rot_x(rng.uniform(-0.05, 0.2))
            blade_mats.append(m @ scale(rng.uniform(0.05, 0.08)) @ np.diag((1, 1, 1, 1.0)))
            blade_tones.append(-1 - int(rng.choice((1, 2))))
    blades = [(m, t) for m, t in zip(blade_mats, blade_tones) if t >= 0]
    rosettes = [(m, -1 - t) for m, t in zip(blade_mats, blade_tones) if t < 0]
    for items, template, template_uv, faces in ((blades, blade, blade_uv, blade_faces),
                                                (rosettes, LEAFLET_VERTS, LEAFLET_UV, LEAFLET_FACES)):
        arr = np.array([m for m, _ in items])
        verts = np.einsum("nij,vj->nvi", arr[:, :3, :3], template) + arr[:, None, :3, 3]
        uv = np.empty((len(items), len(template), 2))
        for i, (_, tone) in enumerate(items):
            u, v = tx.tile_uv(tone, template_uv[:, 0], template_uv[:, 1])
            uv[i] = np.column_stack((u, v))
        weeds.add_batch(verts, faces, uv)
    weeds.build("BGV_weeds", [mats["leaf"]], collection, root)

    debris = Builder()
    petals = []
    for _ in range(140):
        # Fallen bracts collect under the heaviest flowering, and blow a little way out.
        x = float(np.clip(rng.normal(-0.4, 0.7) if rng.random() < 0.7 else rng.normal(1.2, 0.4), -1.75, 1.75))
        y = -abs(rng.normal(0.05, 0.22)) - 0.025
        z = float(ground_height(x, y)) + 0.003
        m = translate((x, y, z)) @ rot_z(rng.uniform(0, 2 * pi)) @ rot_x(rng.normal(pi if rng.random() < 0.5 else 0, 0.2))
        petals.append((m @ scale(rng.uniform(0.018, 0.026)), int(rng.choice((1, 2, 2, 3)))))
    arr = np.array([m for m, _ in petals])
    verts = np.einsum("nij,vj->nvi", arr[:, :3, :3], BRACT_VERTS * (1, 1, 0.3)) + arr[:, None, :3, 3]
    uv = np.array([np.column_stack(tx.tile_uv(t, BRACT_UV[:, 0], BRACT_UV[:, 1])) for _, t in petals])
    debris.add_batch(verts, BRACT_FACES, uv)
    debris.build("BGV_debris_optional", [mats["flower"]], collection, root)
    log(f"ground: {ground.triangles()} tris, weeds {weeds.triangles()} tris, fallen bracts {debris.triangles()} tris")
    return root


# ------------------------------------------------------------------- export

def descendants(obj):
    out = [obj]
    for child in obj.children:
        out += descendants(child)
    return out


def export_root(root, stem):
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    saved = root.location.copy()
    root.location = (0, 0, 0)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    for obj in descendants(root):
        obj.select_set(True)
    bpy.context.view_layer.objects.active = root
    path = MODEL_DIR / f"{stem}.glb"
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_apply=True,
                              export_yup=True, export_cameras=False, export_lights=False,
                              export_image_format="WEBP", export_image_quality=90)
    root.location = saved
    log(f"exported {path.relative_to(PROJECT_ROOT)} ({path.stat().st_size / 1e6:.2f} MB)")


def build_stage():
    started = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    mats = build_materials()
    collections = {}
    for name in ("BGV_signpost", "BGV_fence", "BGV_fence_extension", "BGV_tree", "BGV_ground"):
        collections[name] = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collections[name])
    roots = [
        build_signpost(collections["BGV_signpost"], mats),
        build_fence(collections["BGV_fence"], mats, "BGV_FENCE_FLOWERS_ROOT", HERO_WIDTH, HERO_CANES, hero_density, 2026)[0],
        build_fence(collections["BGV_fence_extension"], mats, "BGV_FENCE_EXTENSION_ROOT", EXTENSION_WIDTH,
                    EXTENSION_CANES, extension_density, 3031)[0],
        build_tree(collections["BGV_tree"], mats),
        build_ground(collections["BGV_ground"], mats),
    ]
    for root in roots:
        export_root(root, EXPORTS[root.name])
        root.location = SCENE_LAYOUT[root.name]
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    for image in bpy.data.images:
        if image.filepath:
            image.filepath = bpy.path.relpath(image.filepath, start=str(SOURCE_DIR))
    add_validation_rig()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    log(f"saved {BLEND.relative_to(PROJECT_ROOT)} ({time.time() - started:.0f}s)")


# ------------------------------------------------------ validation lighting

def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def add_validation_rig():
    """Lights, cameras and stage ground for review only; never exported."""
    rig = bpy.data.collections.new("BGV_validation")
    bpy.context.scene.collection.children.link(rig)

    def link(obj):
        rig.objects.link(obj)
        return obj

    sun = link(bpy.data.objects.new("VAL_sun", bpy.data.lights.new("VAL_sun", "SUN")))
    sun.data.energy = 5.5
    sun.data.angle = radians(0.8)
    sun.location = (-3.0, -3.6, 4.4)
    point_at(sun, (0, 0, 1.0))
    street = link(bpy.data.objects.new("VAL_streetlight", bpy.data.lights.new("VAL_streetlight", "SPOT")))
    # One street lamp off to the right: a pool that catches the flowers and
    # fades out across the sign, leaving the canopy mostly in darkness.
    street.data.energy = 650
    street.data.spot_size = radians(95)
    street.data.spot_blend = 0.5
    street.data.shadow_soft_size = 0.08
    street.data.color = (1.0, 0.84, 0.62)
    street.location = (1.1, -1.7, 4.8)
    point_at(street, (0.3, 0.0, 0.6))

    stage = bpy.data.materials.new("VAL_stage_ground")
    stage.use_nodes = True
    stage.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*srgb_to_linear((48, 46, 42)), 1)
    stage.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.95
    for name, (y0, y1, z) in {"VAL_road": (-9, -1.3, -0.112), "VAL_pavement": (-1.35, 12, -0.003)}.items():
        obj = link(bpy.data.objects.new(name, bpy.data.meshes.new(name)))
        obj.data.from_pydata([(-12, y0, z), (12, y0, z), (12, y1, z), (-12, y1, z)], [], [(0, 1, 2, 3)])
        obj.data.materials.append(stage)
    camera = link(bpy.data.objects.new("VAL_camera", bpy.data.cameras.new("VAL_camera")))
    camera.data.clip_start = 0.02
    bpy.context.scene.camera = camera


def set_world(scene, colour, strength):
    world = scene.world or bpy.data.worlds.new("VAL_world")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes["Background"]
    background.inputs["Color"].default_value = (*colour, 1)
    background.inputs["Strength"].default_value = strength


def show_only(names):
    for root_name in SCENE_LAYOUT:
        root = bpy.data.objects[root_name]
        for obj in descendants(root):
            obj.hide_render = root_name not in names


def render_stage():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.use_shadows = True
    scene.eevee.use_raytracing = True
    scene.eevee.taa_render_samples = 64
    scene.view_settings.view_transform = "AgX"
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        scene.view_settings.look = "None"
    sun = bpy.data.objects["VAL_sun"]
    street = bpy.data.objects["VAL_streetlight"]
    camera = bpy.data.objects["VAL_camera"]
    lens = bpy.data.materials["MAT_lamp_lens"].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    everything = set(SCENE_LAYOUT)
    dusk_green = (0.018, 0.026, 0.018)

    def shot(name, *, loc, target, lens_mm=35, res=(1080, 1334), ortho=None, show=everything,
             day=True, world=dusk_green, world_strength=1.0, sun_loc=None):
        show_only(show)
        for obj_name in ("VAL_road", "VAL_pavement"):
            bpy.data.objects[obj_name].hide_render = "BGV_GROUND_ROOT" not in show
        sun.hide_render = not day
        street.hide_render = day
        sun.location = sun_loc or (-2.4, -2.9, 6.4)
        point_at(sun, (0, 0, 1.0))
        lens.default_value = 0.0 if day else 0.8
        set_world(scene, world if day else (0.0015, 0.002, 0.004), world_strength)
        camera.location = loc
        point_at(camera, target)
        camera.data.type = "ORTHO" if ortho else "PERSP"
        if ortho:
            camera.data.ortho_scale = ortho
        camera.data.lens = lens_mm
        scene.render.resolution_x, scene.render.resolution_y = res
        scene.render.filepath = str(RENDER_DIR / f"{name}.png")
        started = time.time()
        bpy.ops.render.render(write_still=True)
        log(f"render {name} ({time.time() - started:.0f}s)")

    shot("A-assembled-daylight", loc=(0.95, -4.7, 1.5), target=(-0.35, 0.0, 1.6), lens_mm=30)
    shot("B-fence-straight-on", loc=(-0.9, -8, 1.3), target=(-0.9, 0, 1.3), res=(1800, 760), ortho=5.9,
         show={"BGV_FENCE_FLOWERS_ROOT", "BGV_FENCE_EXTENSION_ROOT", "BGV_GROUND_ROOT", "BGV_TREE_ROOT"})
    shot("C-closeup-timber-stems", loc=(1.0, -0.8, 1.05), target=(1.2, 0.0, 0.95), lens_mm=45, res=(1200, 1200))
    shot("D-closeup-flower-clusters", loc=(-0.2, -1.05, 2.3), target=(-0.45, -0.2, 2.05), lens_mm=45, res=(1400, 1050))
    shot("E-closeup-signpost", loc=(-0.55, -2.9, 2.55), target=(-1.35, -1.05, 2.7), lens_mm=40, res=(1000, 1250),
         show={"BGV_SIGNPOST_ROOT", "BGV_FENCE_FLOWERS_ROOT", "BGV_TREE_ROOT", "BGV_FENCE_EXTENSION_ROOT"})
    shot("F-foliage-shadow-test", loc=(0.2, -3.4, 1.4), target=(0.2, 0.0, 1.35), lens_mm=35, res=(1600, 1100),
         show={"BGV_FENCE_FLOWERS_ROOT", "BGV_GROUND_ROOT"}, world=(0.03, 0.03, 0.032), sun_loc=(-4.5, -3.0, 3.6))
    shot("G-tree-silhouette", loc=(-0.3, -14, 3.4), target=(-0.3, 1.9, 3.4), res=(1400, 1100), ortho=8.4,
         show={"BGV_TREE_ROOT"}, world=(0.78, 0.8, 0.82), world_strength=1.0)
    shot("H-night-streetlight", loc=(0.95, -4.7, 1.5), target=(-0.35, 0.0, 1.6), lens_mm=30, day=False)

    # Exploded view: pull the assets apart to show they are independent.
    exploded = {"BGV_SIGNPOST_ROOT": (-3.6, -2.4, 0.0), "BGV_FENCE_FLOWERS_ROOT": (0.0, 0.0, 0.0),
                "BGV_FENCE_EXTENSION_ROOT": (-3.6, 0.9, 0.0), "BGV_TREE_ROOT": (0.6, 4.4, 0.0),
                "BGV_GROUND_ROOT": (0.3, -2.9, 0.012)}
    for name, location in exploded.items():
        bpy.data.objects[name].location = location
    shot("I-exploded-assets", loc=(7.5, -10.5, 6.0), target=(-0.4, 0.8, 1.6), lens_mm=30, res=(1600, 1100),
         world=(0.35, 0.37, 0.38))


# ------------------------------------------------------------- validation

def glb_json(path):
    data = path.read_bytes()
    length = struct.unpack_from("<I", data, 12)[0]
    return json.loads(data[20:20 + length])


def validate_stage():
    """Reimport every GLB into an empty scene and record what survived export."""
    report = {}
    for root_name, stem in EXPORTS.items():
        path = MODEL_DIR / f"{stem}.glb"
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(path))
        objects = list(bpy.context.scene.objects)
        meshes = [o for o in objects if o.type == "MESH"]
        corners = np.array([o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box])
        doc = glb_json(path)
        report[stem] = {
            "size_mb": round(path.stat().st_size / 1e6, 2),
            "nodes": sorted(o.name for o in objects),
            "cameras_or_lights": [o.name for o in objects if o.type in ("CAMERA", "LIGHT")],
            "triangles": {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in meshes},
            "bounds_min": [round(float(v), 3) for v in corners.min(0)],
            "bounds_max": [round(float(v), 3) for v in corners.max(0)],
            "root_transform_identity": all(
                (o.location.length < 1e-6 and max(abs(r) for r in o.rotation_euler) < 1e-6 and
                 max(abs(s - 1) for s in o.scale) < 1e-6) for o in objects),
            "materials": {m["name"]: {"alphaMode": m.get("alphaMode", "OPAQUE"), "doubleSided": m.get("doubleSided", False),
                                      "textures": sorted(k for k, v in m.get("pbrMetallicRoughness", {}).items() if isinstance(v, dict) and "index" in v)
                                      + sorted(k for k in ("normalTexture", "occlusionTexture", "emissiveTexture") if k in m)}
                          for m in doc.get("materials", [])},
            "images": [(img.get("mimeType"), img.get("name")) for img in doc.get("images", [])],
            "extensions": doc.get("extensionsUsed", []),
        }
        report[stem]["triangles_total"] = sum(report[stem]["triangles"].values())
        log(f"validated {stem}: {report[stem]['triangles_total']} tris, bounds {report[stem]['bounds_min']} -> {report[stem]['bounds_max']}")
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    (RENDER_DIR / "validation.json").write_text(json.dumps(report, indent=2))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    stage = argv[argv.index("--stage") + 1] if "--stage" in argv else "all"
    global REUSE_TEXTURES
    REUSE_TEXTURES = "--reuse-textures" in argv
    if stage in ("all", "build"):
        build_stage()
    if stage in ("all", "validate"):
        validate_stage()
    if stage in ("all", "renders"):
        render_stage()


if __name__ == "__main__":
    main()
