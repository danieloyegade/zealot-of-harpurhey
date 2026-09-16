"""Geometry for the worn timber shipping pallets.

Both pallets share one block-pallet construction: top deck boards run along the
pallet's length (X), three cross boards run across it (Y) over nine blocks, and
three bottom boards run along X beneath the block rows.  Fork openings exist on
all four sides.

Every board is its own mesh with a chamfered ten-vertex profile, so edges catch
highlights, and each is deformed individually from a seeded generator: bow,
sweep, twist, cup, skewed saw cuts, edge chips, crushed corners and, on a few
top boards, a splintered end.  Blocks keep the faces the boards cover: their
chipped and crushed corners would otherwise open onto a hollow interior.  Nail
heads are placed by ray casting onto the deformed boards, so none float.

Local axes of every part: X runs along its length, Y across its width, Z through
its thickness.  createPallets.py reads these to align wood grain per board.
"""

from dataclasses import dataclass, field
from math import cos, pi, radians, sin

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

MM = 0.001


@dataclass
class Layout:
    name: str
    length: float
    width: float
    top_widths: tuple
    gap_jitter: float
    seed: int
    cross_width: float = 0.145
    bottom_widths: tuple = (0.100, 0.145, 0.100)
    board_t: float = 0.022
    block_h: float = 0.078
    broken_ends: int = 1
    chips: tuple = (1, 4)

    @property
    def slug(self):
        return self.name.replace("_", "-")


# EUR-style 1200 x 800: the brief's starting footprint.
BROWN = Layout("pallet_worn_brown", 1.200, 0.800, (0.145, 0.100, 0.145, 0.100, 0.145), 0.006, seed=1207)
# The blue references are 1200 x 1000 block pallets with seven top boards.
BLUE = Layout("pallet_worn_blue", 1.200, 1.000, (0.145, 0.100, 0.100, 0.145, 0.100, 0.100, 0.145), 0.008,
              seed=4412, broken_ends=2, chips=(2, 5))


@dataclass
class Part:
    obj: object
    kind: str  # top | cross | bottom | block | nails
    size: tuple  # local (length, width, thickness)
    params: dict = field(default_factory=dict)


@dataclass
class Pallet:
    layout: Layout
    parts: list
    nails: list
    holes: list
    cross_x: list
    row_y: list
    top_y: list
    top_z: float


# ------------------------------------------------------------------ profile

# Ten vertices around a chamfered rectangle: right side, top face (split in
# three so the top can be jagged at broken ends), left side, bottom.
CORNERS = {"br": (0, 1), "tr": (2, 3), "tl": (6, 7), "bl": (8, 9)}
CORNER_SIGN = {"br": (1, -1), "tr": (1, 1), "tl": (-1, 1), "bl": (-1, -1)}


def profile(w, t, chamfer):
    br, tr, tl, bl = chamfer
    return [(w - br, -t), (w, -t + br), (w, t - tr), (w - tr, t), (w / 3, t), (-w / 3, t),
            (-w + tl, t), (-w, t - tl), (-w, -t + bl), (-w + bl, -t)]


def random_chips(rng, half_length, count, corners, depth=(2.5, 8.0), length=(0.015, 0.06)):
    chips = []
    for _ in range(count):
        chips.append({
            "corner": corners[rng.integers(len(corners))],
            "a": float(rng.uniform(-half_length + 0.03, half_length - 0.03)),
            "len": float(rng.uniform(*length)),
            "depth": float(rng.uniform(*depth)) * MM,
        })
    return chips


def build_board(name, size, rng, collection, *, chips=(), broken_end=0, deform=1.0):
    """Mesh one timber part centred on its origin; returns the object and its damage record."""
    length, width, thick = size
    L, w, t = length / 2, width / 2, thick / 2
    # Sawn pallet timber is nearly square-edged; the arris is worn, not machined.
    base = profile(w, t, rng.uniform(0.8, 2.6, 4) * MM)

    stations = list(np.linspace(-L, L, max(2, int(round(length / 0.15))) + 1))
    for chip in chips:
        stations += [chip["a"] + chip["len"] * f for f in (-0.5, 0.0, 0.5)]
    stations += [-L + 0.02, L - 0.02]
    if broken_end:
        stations.append(broken_end * (L - 0.07))
    stations = sorted(s for s in stations if -L <= s <= L)
    merged = [stations[0]]
    for s in stations[1:]:
        if s - merged[-1] > 3 * MM:
            merged.append(s)
    merged[-1] = L
    merged[0] = -L

    bow = rng.normal(0, 1.2) * MM * deform
    sweep = rng.normal(0, 1.2) * MM * deform
    twist = radians(rng.normal(0, 0.35)) * deform
    cup = rng.normal(0, 0.5) * MM * deform
    w_scale = 1 + rng.normal(0, 0.008)
    t_scale = 1 + rng.normal(0, 0.02)
    skew = rng.normal(0, 1.2, 2) * MM
    crush = {end: {c: rng.uniform(0, 6) * MM if rng.random() < 0.55 else 0.0 for c in CORNERS} for end in (-1, 1)}
    jag = rng.uniform(4, 28, 10) * MM

    bm = bmesh.new()
    rings = []
    for a in merged:
        u = a / L
        end = 1 if a >= L - 1e-6 else -1 if a <= -L + 1e-6 else 0
        ring = []
        for k, (y0, z0) in enumerate(base):
            y, z, x = y0 * w_scale, z0 * t_scale, a
            for chip in chips:
                s = 1 - ((a - chip["a"]) / (chip["len"] / 2)) ** 2
                if s > 0 and k in CORNERS[chip["corner"]]:
                    sy, sz = CORNER_SIGN[chip["corner"]]
                    y -= sy * chip["depth"] * s ** 0.7 * 0.75
                    z -= sz * chip["depth"] * s ** 0.7 * 0.75
            near_end = 1 if a > 0 else -1
            ramp = max(0.0, 1 - (L - abs(a)) / 0.02)
            for corner, amount in crush[near_end].items():
                if k in CORNERS[corner] and amount:
                    sy, sz = CORNER_SIGN[corner]
                    y -= sy * amount * ramp * 0.7
                    z -= sz * amount * ramp * 0.7
            if end:
                x += skew[0 if end < 0 else 1] * (y0 / w)
                if broken_end == end and 2 <= k <= 7:
                    x -= end * jag[k]
            z += bow * (1 - u * u) + cup * (y0 / w) ** 2
            y += sweep * (1 - u * u)
            angle = twist * u
            y, z = y * cos(angle) - z * sin(angle), y * sin(angle) + z * cos(angle)
            ring.append(bm.verts.new((x, y, z)))
        rings.append(ring)

    n = len(base)
    for i in range(len(rings) - 1):
        for k in range(n):
            bm.faces.new((rings[i][k], rings[i][(k + 1) % n], rings[i + 1][(k + 1) % n], rings[i + 1][k]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.shade_smooth()
    mesh.set_sharp_from_angle(angle=radians(35))
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj, {"chips": list(chips), "broken_end": broken_end, "crush": crush}


# -------------------------------------------------------------------- nails

def world_bvh(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)
    tree = BVHTree.FromBMesh(bm)
    bm.free()
    return tree


def add_nail_head(bm, position, normal, radius, proud, sink, rotation, tilt_axis=None, tilt=0.0):
    frame = Vector(normal).to_track_quat("Z", "X").to_matrix()
    if tilt:
        frame = Matrix.Rotation(tilt, 3, tilt_axis) @ frame
    frame = frame @ Matrix.Rotation(rotation, 3, "Z")
    p = Vector(position)
    top, bottom = [], []
    for i in range(6):
        angle = i * pi / 3
        r = Vector((radius * cos(angle), radius * sin(angle), 0))
        top.append(bm.verts.new(p + frame @ (r + Vector((0, 0, proud)))))
        bottom.append(bm.verts.new(p + frame @ (r + Vector((0, 0, -sink)))))
    centre = bm.verts.new(p + frame @ Vector((0, 0, proud + 0.35 * MM)))
    for i in range(6):
        j = (i + 1) % 6
        bm.faces.new((top[i], top[j], centre))
        bm.faces.new((bottom[i], bottom[j], top[j], top[i]))


def place_nails(pallet, rng, collection):
    layout = pallet.layout
    boards = {p.obj.name: p for p in pallet.parts}
    tops = [p for p in pallet.parts if p.kind == "top"]
    bottoms = [p for p in pallet.parts if p.kind == "bottom"]
    bm = bmesh.new()

    def drive(part, x, y, from_above):
        tree = world_bvh(part.obj)
        z0, direction = (1.0, Vector((0, 0, -1))) if from_above else (-1.0, Vector((0, 0, 1)))
        hit, normal, _, _ = tree.ray_cast(Vector((x, y, z0)), direction, 3.0)
        if hit is None:
            return
        roll = rng.random()
        radius = rng.uniform(3.2, 4.2) * MM
        if roll < 0.05:
            pallet.holes.append({"position": tuple(hit), "normal": tuple(normal), "radius": 2.4 * MM, "part": part.obj.name})
            return
        proud, tilt = rng.uniform(0.2, 0.6) * MM, 0.0
        state = "flush"
        # Only deck nails work proud; one under a bottom board would lift the pallet off the ground.
        if from_above and roll > 0.96:
            proud, tilt, state = rng.uniform(1.5, 3.0) * MM, radians(rng.uniform(5, 12)), "proud"
        axis = Vector((rng.normal(), rng.normal(), 0)).normalized()
        add_nail_head(bm, hit, normal, radius, proud, 2.0 * MM, rng.uniform(0, pi), axis, tilt)
        pallet.nails.append({"position": tuple(hit), "normal": tuple(normal), "radius": radius,
                             "part": part.obj.name, "state": state})

    for top in tops:
        y, width = top.params["y"], top.size[1]
        fractions = (-0.32, 0.0, 0.32) if width >= 0.12 else (-0.25, 0.25)
        for x in pallet.cross_x:
            for i, f in enumerate(fractions):
                offset = (-0.035, 0.035, -0.03)[i] + rng.normal(0, 4) * MM
                drive(top, x + offset, y + f * width + rng.normal(0, 4) * MM, True)
    for bottom in bottoms:
        y, width = bottom.params["y"], bottom.size[1]
        fractions = (-0.3, 0.0, 0.3) if width >= 0.12 else (-0.22, 0.22)
        for x in pallet.cross_x:
            for i, f in enumerate(fractions):
                offset = (0.04, -0.04, 0.035)[i] + rng.normal(0, 4) * MM
                drive(bottom, x + offset, y + f * width + rng.normal(0, 4) * MM, False)

    mesh = bpy.data.meshes.new(f"{layout.slug}-nails")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(mesh.name, mesh)
    collection.objects.link(obj)
    pallet.parts.append(Part(obj, "nails", (0, 0, 0)))


# ----------------------------------------------------------------- assembly

def build_pallet(layout, collection):
    rng = np.random.default_rng(layout.seed)
    t, h = layout.board_t, layout.block_h
    L, W = layout.length, layout.width
    parts = []

    widths = layout.top_widths
    gap = (W - sum(widths)) / (len(widths) - 1)
    top_y, cursor = [], -W / 2
    for i, width in enumerate(widths):
        jitter = 0.0 if i in (0, len(widths) - 1) else rng.uniform(-0.5, 0.5) * layout.gap_jitter
        top_y.append(cursor + width / 2 + jitter)
        cursor += width + gap

    cross_x = [-L / 2 + layout.cross_width / 2, 0.0, L / 2 - layout.cross_width / 2]
    bw = layout.bottom_widths
    row_y = [-W / 2 + bw[0] / 2, 0.0, W / 2 - bw[2] / 2]
    z_bottom, z_block, z_cross, z_top = t / 2, t + h / 2, t + h + t / 2, t + h + t + t / 2

    broken = set(rng.choice(len(widths), layout.broken_ends, replace=False).tolist())
    for i, (y, width) in enumerate(zip(top_y, widths)):
        size = (L + rng.normal(0, 2) * MM, width, t)
        count = int(rng.integers(layout.chips[0], layout.chips[1] + 1))
        chips = random_chips(rng, size[0] / 2, count, ("tr", "tr", "tl", "tl", "br", "bl"))
        end = int(rng.choice((-1, 1))) if i in broken else 0
        name = f"{layout.slug}-top-board-{i + 1:02d}"
        obj, damage = build_board(name, size, rng, collection, chips=chips, broken_end=end)
        obj.location = (rng.normal(0, 3) * MM, y, z_top)
        parts.append(Part(obj, "top", size, {"y": y, **damage}))

    for i, x in enumerate(cross_x):
        size = (W, layout.cross_width, t)
        chips = random_chips(rng, W / 2, int(rng.integers(0, 3)), ("br", "bl", "tr", "tl"), depth=(2, 5))
        obj, damage = build_board(f"{layout.slug}-cross-board-{i + 1:02d}", size, rng, collection, chips=chips, deform=0.6)
        obj.location = (x, 0, z_cross)
        obj.rotation_euler = (0, 0, pi / 2)
        parts.append(Part(obj, "cross", size, {"x": x, **damage}))

    for r, (y, width) in enumerate(zip(row_y, bw)):
        for i, x in enumerate(cross_x):
            size = (layout.cross_width - 3 * MM, width - 3 * MM, h)
            # Forks strike the lower edges of the blocks.
            chips = random_chips(rng, size[0] / 2, int(rng.integers(1, 4)), ("br", "bl", "br", "bl", "tr"),
                                 depth=(2, 6), length=(0.015, 0.05))
            obj, damage = build_board(f"{layout.slug}-block-{r * 3 + i + 1:02d}", size, rng, collection,
                                      chips=chips, deform=0.3)
            obj.location = (x + rng.normal(0, 1.5) * MM, y + rng.normal(0, 1.5) * MM, z_block)
            parts.append(Part(obj, "block", size, {"x": x, "y": y, **damage}))

    for r, (y, width) in enumerate(zip(row_y, bw)):
        size = (L, width, t)
        chips = random_chips(rng, L / 2, int(rng.integers(2, 5)), ("tr", "tl", "br", "bl"), depth=(3, 9))
        obj, damage = build_board(f"{layout.slug}-bottom-board-{r + 1:02d}", size, rng, collection, chips=chips, deform=0.7)
        obj.location = (rng.normal(0, 2) * MM, y, z_bottom)
        parts.append(Part(obj, "bottom", size, {"y": y, **damage}))

    pallet = Pallet(layout, parts, [], [], cross_x, row_y, top_y, t + h + t + t)
    bpy.context.view_layer.update()
    place_nails(pallet, rng, collection)
    ground_pallet(pallet)
    return pallet


def ground_pallet(pallet):
    """Shift every part so the lowest vertex rests exactly on Z = 0."""
    bpy.context.view_layer.update()
    lowest = min((p.obj.matrix_world @ v.co).z for p in pallet.parts for v in p.obj.data.vertices)
    for part in pallet.parts:
        part.obj.location.z -= lowest
    for record in pallet.nails + pallet.holes:
        x, y, z = record["position"]
        record["position"] = (x, y, z - lowest)
    pallet.top_z -= lowest
    bpy.context.view_layer.update()


def join_for_export(pallet, collection):
    """One mesh object at the world origin, transforms applied, for the runtime GLB."""
    copies = []
    for part in pallet.parts:
        copy = part.obj.copy()
        copy.data = part.obj.data.copy()
        collection.objects.link(copy)
        copies.append(copy)
    bpy.ops.object.select_all(action="DESELECT")
    for copy in copies:
        copy.select_set(True)
    bpy.context.view_layer.objects.active = copies[0]
    bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    joined.name = pallet.layout.slug
    joined.data.name = pallet.layout.slug
    return joined
