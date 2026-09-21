"""Geometry for the Harperhey municipal streetlight family.

Four related columns, built from scratch at real-world dimensions:

  Streetlight_Warm_Old_01   8 m galvanised column, short cast bracket and a
                            side-entry low-pressure sodium (SOX) lantern with a
                            prismatic bowl and a visible U-tube.
  Streetlight_LED_Modern_01 8 m stepped galvanised column with an integral
                            bent bracket and a slim flat LED luminaire.
  Streetlight_Curved_01     7 m painted residential column bending over into
                            a slightly irregular swan neck, small SON lantern.
  Streetlight_Weathered_01  8 m older galvanised column, raked single-arm
                            bracket with a strut and a deeper SON bowl lantern.

Axes (Blender): Z up, the lantern overhangs the carriageway along +X, the
maintenance door faces the footway along -X.  Every asset origin is the centre
of the column where it is planted in the pavement.  After glTF's Y-up
conversion the overhang is three.js +X.

Every asset is built three times (LOD0/1/2) from the same dimensions with fewer
segments and fewer small parts, so silhouettes match between levels.  Tiny
details (bolts, weld beads, lock screw, lens array) exist only in LOD0.

Local frame for lantern parts: x along the lantern from its spigot entry to the
nose, y across it, z up.  Each lantern is placed by a 4x4 matrix so its
installed pitch and any roll are baked into the vertices.
"""

from dataclasses import dataclass, field
from math import atan2, cos, pi, radians, sin

import bmesh
import bpy
from mathutils import Matrix, Vector

MM = 0.001

# Per-level resolution.  Pole and tube segments, lantern section points, and
# which small parts to keep.
LODS = {
    0: dict(pole=24, tube=16, section=36, loft=1.0, small=True, lenses=True),
    1: dict(pole=14, tube=10, section=24, loft=0.75, small=False, lenses=False),
    2: dict(pole=8, tube=6, section=12, loft=0.4, small=False, lenses=False),
}

# Material slot names shared by every asset.  The texture pass replaces BODY
# with a per-asset baked atlas; the rest are small shared materials.
BODY = "Body"
REFLECTOR = "Reflector"
GLASS = "Glass"
EMITTER = "Emitter"
LED_BOARD = "LEDBoard"


# ------------------------------------------------------------------ builder

class Builder:
    """Accumulates one mesh with named material slots."""

    def __init__(self):
        self.bm = bmesh.new()
        self.slots = []

    def slot(self, name):
        if name not in self.slots:
            self.slots.append(name)
        return self.slots.index(name)

    def loop(self, points):
        return [self.bm.verts.new(Vector(p)) for p in points]

    def bridge(self, a, b, material, closed=True, flip=False):
        index = self.slot(material)
        count = len(a)
        faces = []
        for i in range(count if closed else count - 1):
            j = (i + 1) % count
            quad = (a[i], a[j], b[j], b[i]) if not flip else (a[i], b[i], b[j], a[j])
            face = self.bm.faces.new(quad)
            face.material_index = index
            faces.append(face)
        return faces

    def cap(self, loop, material, flip=False, fan=True):
        """Close a loop.  Fans to a centre vertex so caps stay convex quads/tris."""
        index = self.slot(material)
        if fan:
            centre = self.bm.verts.new(sum((v.co for v in loop), Vector()) / len(loop))
            for i in range(len(loop)):
                j = (i + 1) % len(loop)
                tri = (loop[i], loop[j], centre) if not flip else (loop[j], loop[i], centre)
                self.bm.faces.new(tri).material_index = index
            return centre
        face = self.bm.faces.new(loop if not flip else list(reversed(loop)))
        face.material_index = index
        return face

    def loft(self, sections, material, closed=True, cap_start=False, cap_end=False):
        loops = [self.loop(s) for s in sections]
        for a, b in zip(loops, loops[1:]):
            self.bridge(a, b, material, closed)
        if cap_start:
            self.cap(loops[0], material, flip=True)
        if cap_end:
            self.cap(loops[-1], material)
        return loops

    def finish(self, name, materials, origin=(0, 0, 0), smooth_angle=38.0, collection=None):
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.00005)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        mesh.transform(Matrix.Translation(-Vector(origin)))
        for slot_name in self.slots:
            mesh.materials.append(materials[slot_name])
        mesh.shade_smooth()
        mesh.set_sharp_from_angle(angle=radians(smooth_angle))
        obj = bpy.data.objects.new(name, mesh)
        obj.location = origin
        (collection or bpy.context.scene.collection).objects.link(obj)
        return obj


# --------------------------------------------------------------- primitives

def circle(centre, radius, segments, normal=(0, 0, 1), phase=0.0, squash=1.0, ref=None):
    """Points on a circle around `normal`.  `ref` fixes the start direction."""
    n = Vector(normal).normalized()
    u = Vector(ref) if ref is not None else (Vector((1, 0, 0)) if abs(n.x) < 0.9 else Vector((0, 1, 0)))
    u = (u - n * u.dot(n)).normalized()
    v = n.cross(u)
    c = Vector(centre)
    return [c + (u * cos(a) * radius + v * sin(a) * radius * squash)
            for a in (phase + 2 * pi * i / segments for i in range(segments))]


def transport_frames(points):
    """Tangents and parallel-transported reference vectors along a polyline."""
    pts = [Vector(p) for p in points]
    tangents = []
    for i in range(len(pts)):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        tangents.append((b - a).normalized())
    ref = Vector((1, 0, 0)) if abs(tangents[0].x) < 0.9 else Vector((0, 1, 0))
    ref = (ref - tangents[0] * ref.dot(tangents[0])).normalized()
    refs = [ref]
    for t0, t1 in zip(tangents, tangents[1:]):
        axis = t0.cross(t1)
        if axis.length > 1e-8:
            angle = t0.angle(t1)
            ref = Matrix.Rotation(angle, 3, axis.normalized()) @ ref
        ref = (ref - t1 * ref.dot(t1)).normalized()
        refs.append(ref)
    return pts, tangents, refs


def tube(b, points, radii, segments, material, cap_start=False, cap_end=False, ovality=0.0):
    """Sweep a circle along a polyline.  `radii` is one value per point."""
    pts, tangents, refs = transport_frames(points)
    if not isinstance(radii, (list, tuple)):
        radii = [radii] * len(pts)
    sections = []
    for p, t, r, rad in zip(pts, tangents, refs, radii):
        sections.append(circle(p, rad, segments, t, ref=r, squash=1.0 - ovality))
    return b.loft(sections, material, closed=True, cap_start=cap_start, cap_end=cap_end)


def lathe(b, profile, segments, material, cap_top=True, cap_bottom=False, ovality=0.0,
          axis_offset=lambda z: (0.0, 0.0)):
    """Column of revolution from (z, radius) pairs.  `axis_offset(z)` bends the axis
    slightly (lean, sweep) for manufacturing irregularity."""
    sections = []
    for z, r in profile:
        ox, oy = axis_offset(z)
        sections.append(circle((ox, oy, z), r, segments, (0, 0, 1), ref=(1, 0, 0), squash=1.0 - ovality))
    return b.loft(sections, material, closed=True, cap_start=cap_bottom, cap_end=cap_top)


def ring_bead(b, centre, radius, bead, segments, material, normal=(0, 0, 1)):
    """Closed weld bead / collar ring (torus) around an axis."""
    path = circle(centre, radius, segments, normal, ref=(1, 0, 0))
    loops = []
    for i, p in enumerate(path):
        tangent = (path[(i + 1) % segments] - path[i - 1]).normalized()
        radial = (p - Vector(centre)).normalized()
        loops.append(b.loop(circle(p, bead, 5, tangent, ref=radial)))
    for i in range(segments):
        b.bridge(loops[i], loops[(i + 1) % segments], material)


def superellipse(half_w, top_h, bot_h, count, exponent=4.0):
    """(y, z) points of a rounded-rectangle section, counter-clockwise from +y."""
    out = []
    for i in range(count):
        a = 2 * pi * i / count
        c, s = cos(a), sin(a)
        y = half_w * (abs(c) ** (2 / exponent)) * (1 if c >= 0 else -1)
        h = top_h if s >= 0 else bot_h
        z = h * (abs(s) ** (2 / exponent)) * (1 if s >= 0 else -1)
        out.append((y, z))
    return out


def lower_arc(half_w, depth, count, exponent=3.0):
    """Open underside (bowl) section from +y round the bottom to -y."""
    out = []
    for i in range(count + 1):
        a = -pi * i / count  # 0 .. -pi
        c, s = cos(a), sin(a)
        y = half_w * (abs(c) ** (2 / exponent)) * (1 if c >= 0 else -1)
        z = -depth * (abs(s) ** (2 / exponent))
        out.append((y, z))
    return out


# Asset-space positions of every LOD0 bolt, for the texture pass's rust stamps.
BOLT_SITES = []


def hex_bolt(b, base, direction, material, across=0.013, height=0.008):
    d = Vector(direction).normalized()
    p0 = Vector(base)
    BOLT_SITES.append(p0.copy())
    tube(b, [p0 - d * 0.001, p0 + d * height * 0.25], across * 0.62, 12, material, cap_end=True)
    tube(b, [p0 + d * height * 0.25, p0 + d * height], across * 0.5, 6, material, cap_end=True)


def box(b, centre, size, material, matrix=None):
    m = matrix or Matrix.Identity(4)
    hx, hy, hz = (s / 2 for s in size)
    c = Vector(centre)
    corners = [m @ (c + Vector((sx * hx, sy * hy, sz * hz)))
               for sz in (-1, 1) for sy in (-1, 1) for sx in (-1, 1)]
    v = [b.bm.verts.new(p) for p in corners]
    index = b.slot(material)
    for quad in ((0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)):
        b.bm.faces.new([v[i] for i in quad]).material_index = index


# ------------------------------------------------------------- asset specs

@dataclass
class Column:
    """Planted column: (z, radius) profile plus door, plate and weld heights."""
    profile: list
    door_z: tuple            # bottom, top of the maintenance door
    door_width: float        # chord width of the door
    plate_z: float
    welds: list = field(default_factory=list)
    lean: tuple = (0.0, 0.0)  # metres of top offset from vertical (x, y)
    ovality: float = 0.002


@dataclass
class Spec:
    name: str
    slug: str
    column: Column
    kind: str                 # sox | led | son_small | son_bowl
    lantern: Matrix = None    # lantern frame in asset space
    emitter_kelvin: int = 1800
    beam_deg: float = 130.0


def taper(z0, r0, z1, r1, steps):
    return [(z0 + (z1 - z0) * i / steps, r0 + (r1 - r0) * i / steps) for i in range(steps + 1)]


def column_axis(column, z):
    top = column.profile[-1][0]
    t = max(0.0, z) / top
    return column.lean[0] * t * t, column.lean[1] * t * t


def build_column(b, column, lod):
    seg = LODS[lod]["pole"]
    lathe(b, column.profile, seg, BODY, cap_top=False, ovality=column.ovality,
          axis_offset=lambda z: column_axis(column, z))
    if LODS[lod]["small"]:
        for z in column.welds:
            r = radius_at(column, z)
            ox, oy = column_axis(column, z)
            ring_bead(b, (ox, oy, z), r, 0.0035, 28, BODY)


def radius_at(column, z):
    prof = column.profile
    for (z0, r0), (z1, r1) in zip(prof, prof[1:]):
        if z0 <= z <= z1:
            t = 0 if z1 == z0 else (z - z0) / (z1 - z0)
            return r0 + (r1 - r0) * t
    return prof[-1][1]


def build_access_panel(b, column, lod):
    """Door in the base compartment facing the footway (-X), proud by 2 mm."""
    z0, z1 = column.door_z
    r = radius_at(column, (z0 + z1) / 2)
    half = column.door_width / (2 * r)
    cols = 7 if lod == 0 else 3
    rows = [z0, z1]
    front = []
    back = []
    for z in rows:
        ox, oy = column_axis(column, z)
        rz = radius_at(column, z)
        front.append([Vector((ox + (rz + 0.0022) * cos(pi + a), oy + (rz + 0.0022) * sin(pi + a), z))
                      for a in (-half + 2 * half * i / (cols - 1) for i in range(cols))])
        back.append([Vector((ox + (rz - 0.0004) * cos(pi + a), oy + (rz - 0.0004) * sin(pi + a), z))
                     for a in (-half + 2 * half * i / (cols - 1) for i in range(cols))])
    fl = [b.loop(row) for row in front]
    bl = [b.loop(row) for row in back]
    b.bridge(fl[0], fl[1], BODY, closed=False, flip=True)
    # Side walls give the door edge its shadow line.
    b.bridge(bl[0], fl[0], BODY, closed=False, flip=True)
    b.bridge(fl[1], bl[1], BODY, closed=False, flip=True)
    for side in (0, -1):
        quad = (bl[0][side], bl[1][side], fl[1][side], fl[0][side])
        if side == -1:
            quad = tuple(reversed(quad))
        b.bm.faces.new(quad).material_index = b.slot(BODY)
    if LODS[lod]["small"]:
        # Triangular-key lock screw near the top of the door, and hinge pins.
        zt = z1 - 0.06
        rz = radius_at(column, zt)
        ox, oy = column_axis(column, zt)
        tube(b, [(ox - rz - 0.001, oy, zt), (ox - rz - 0.007, oy, zt)], 0.0065, 10, BODY, cap_end=True)
        zb = z0 + 0.06
        rz = radius_at(column, zb)
        ox, oy = column_axis(column, zb)
        tube(b, [(ox - rz - 0.001, oy, zb), (ox - rz - 0.005, oy, zb)], 0.0055, 10, BODY, cap_end=True)


def build_plate(b, column, lod, facing_deg=35.0):
    """Column number plate: a thin 75 x 100 mm tab strapped to the shaft."""
    z = column.plate_z
    r = radius_at(column, z)
    ox, oy = column_axis(column, z)
    a = radians(facing_deg)
    m = Matrix.Translation((ox + (r + 0.002) * cos(a), oy + (r + 0.002) * sin(a), z)) @ Matrix.Rotation(a, 4, "Z")
    box(b, (0, 0, 0), (0.003, 0.075, 0.10), BODY, m)


def superellipse_loft(b, frame, stations, count, material, exponent=4.0, cap_start=True, cap_end=True):
    """Lantern body: stations are (x, half_w, top_h, bot_h, z_offset)."""
    sections = []
    for x, hw, th, bh, dz in stations:
        sections.append([frame @ Vector((x, y, z + dz)) for y, z in superellipse(hw, th, bh, count, exponent)])
    return b.loft(sections, material, closed=True, cap_start=cap_start, cap_end=cap_end)


def bowl_loft(b, frame, stations, count, material, exponent=3.0):
    """Open-top diffuser: stations are (x, half_w, depth, z_top).  End arcs capped."""
    sections = []
    for x, hw, depth, zt in stations:
        sections.append([frame @ Vector((x, y, zt + z)) for y, z in lower_arc(hw, depth, count, exponent)])
    loops = b.loft(sections, material, closed=False)
    b.cap(loops[0], material, flip=False)
    b.cap(loops[-1], material, flip=True)
    return loops


def smooth(stations, steps):
    """Catmull-Rom subdivision of a station list: `steps` samples per span."""
    if steps <= 1:
        return stations
    out = []
    count = len(stations)
    for i in range(count - 1):
        p0 = stations[max(i - 1, 0)]
        p1, p2 = stations[i], stations[i + 1]
        p3 = stations[min(i + 2, count - 1)]
        for k in range(steps):
            t = k / steps
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2
                                    + (-a + 3 * b - 3 * c + d) * t3)
                             for a, b, c, d in zip(p0, p1, p2, p3)))
    out.append(stations[-1])
    return out


def resample(stations, factor):
    """Smooth for LOD0, thin for lower LODs, always keeping the ends."""
    if factor >= 1.0:
        return smooth(stations, 3)
    keep = max(3, int(round(len(stations) * factor)))
    idx = sorted({round(i * (len(stations) - 1) / (keep - 1)) for i in range(keep)})
    return [stations[i] for i in idx]


def mark_reflector(obj, frame, x0, x1, half_w, reflector):
    """Faces on the lantern underside above the bowl become the reflector."""
    inv = (Matrix.Translation(obj.location).inverted() @ frame).inverted()
    index = list(obj.data.materials).index(reflector)
    for poly in obj.data.polygons:
        c = inv @ poly.center
        n = inv.to_3x3() @ poly.normal
        if n.z < -0.55 and x0 <= c.x <= x1 and abs(c.y) <= half_w:
            poly.material_index = index


# ------------------------------------------------------------- the lanterns

def sox_lantern(frame, lod):
    """Side-entry cast lantern, 780 mm, with prismatic bowl and SOX U-tube."""
    res = LODS[lod]
    n = res["section"]
    housing = Builder()
    stations = [
        # x,    half_w, top_h, bot_h, dz
        (-0.035, 0.048, 0.048, 0.044, 0.000),
        (0.000, 0.058, 0.056, 0.048, 0.000),
        (0.060, 0.100, 0.074, 0.048, 0.004),
        (0.130, 0.122, 0.084, 0.044, 0.006),
        (0.250, 0.130, 0.088, 0.038, 0.006),
        (0.420, 0.131, 0.086, 0.035, 0.003),
        (0.600, 0.128, 0.080, 0.033, -0.002),
        (0.740, 0.120, 0.068, 0.031, -0.007),
        (0.820, 0.100, 0.052, 0.029, -0.010),
        (0.858, 0.064, 0.036, 0.024, -0.012),
        (0.868, 0.026, 0.020, 0.016, -0.012),
    ]
    superellipse_loft(housing, frame, resample(stations, res["loft"]), n, BODY, exponent=4.5)
    housing.slot(REFLECTOR)
    # Spigot entry collar with two clamp bolts underneath.
    tube(housing, [frame @ Vector((-0.10, 0, 0)), frame @ Vector((-0.03, 0, 0))], 0.046, res["tube"], BODY,
         cap_start=True)
    if res["small"]:
        ring_bead(housing, frame @ Vector((0.0, 0, 0)), 0.058, 0.004, 24, BODY, normal=frame.to_3x3() @ Vector((1, 0, 0)))
        for x in (0.02, 0.07):
            hex_bolt(housing, frame @ Vector((x, 0.0, -0.051)), frame.to_3x3() @ Vector((0, 0, -1)), BODY)
        # Hinge knuckle at the nose and the bowl catch at the rear.
        tube(housing, [frame @ Vector((0.845, -0.045, -0.03)), frame @ Vector((0.845, 0.045, -0.03))], 0.008, 8, BODY,
             cap_start=True, cap_end=True)
        box(housing, (0.125, 0, -0.052), (0.018, 0.05, 0.012), BODY, frame)
    glass = Builder()
    bowl = [
        (0.130, 0.098, 0.030, -0.040),
        (0.170, 0.108, 0.068, -0.038),
        (0.280, 0.112, 0.080, -0.036),
        (0.500, 0.111, 0.080, -0.034),
        (0.690, 0.106, 0.074, -0.032),
        (0.770, 0.094, 0.052, -0.030),
        (0.805, 0.078, 0.022, -0.029),
    ]
    bowl_loft(glass, frame, resample(bowl, max(res["loft"], 0.5)), max(8, n // 2), GLASS, exponent=5.0)
    emitter = Builder()
    tseg = 10 if lod == 0 else 6
    if lod < 2:
        # 35 W SOX: two limbs 26 mm apart, 20 mm glass, joined in a U at the far end.
        z = -0.070
        limb = []
        for sign in (1, -1):
            limb.append([frame @ Vector((x, 0.024 * sign, z)) for x in (0.22, 0.34, 0.46, 0.58)])
        bend = [frame @ Vector((0.58 + 0.024 * sin(a), 0.024 * cos(a), z)) for a in
                (pi * i / (6 if lod == 0 else 3) for i in range(1, (6 if lod == 0 else 3)))]
        path = limb[0] + bend + list(reversed(limb[1]))
        tube(emitter, path, 0.0105, tseg, EMITTER, cap_start=True, cap_end=True)
        # Bayonet cap and holder, dark.
        tube(housing, [frame @ Vector((0.175, 0, -0.046)), frame @ Vector((0.225, 0, -0.068))], 0.020, tseg, REFLECTOR,
             cap_start=True, cap_end=True)
    else:
        box(emitter, (0.41, 0, -0.068), (0.38, 0.07, 0.022), EMITTER, frame)
    return housing, glass, emitter, dict(reflector=(0.12, 0.80, 0.112), emitter=frame @ Vector((0.41, 0, -0.07)))


def led_lantern(frame, lod):
    """Slim flat LED luminaire, 680 mm, dark grey, recessed lens board."""
    res = LODS[lod]
    n = res["section"]
    housing = Builder()
    stations = [
        (-0.020, 0.045, 0.045, 0.040, 0.000),
        (0.000, 0.055, 0.052, 0.040, 0.000),
        (0.040, 0.110, 0.060, 0.030, 0.000),
        (0.100, 0.140, 0.058, 0.022, 0.000),
        (0.200, 0.150, 0.050, 0.018, 0.000),
        (0.340, 0.152, 0.044, 0.016, -0.002),
        (0.480, 0.148, 0.038, 0.015, -0.005),
        (0.580, 0.136, 0.032, 0.014, -0.008),
        (0.640, 0.112, 0.026, 0.013, -0.010),
        (0.668, 0.074, 0.020, 0.012, -0.011),
        (0.678, 0.030, 0.012, 0.009, -0.011),
    ]
    superellipse_loft(housing, frame, resample(stations, res["loft"]), n, BODY, exponent=5.0)
    # Side-entry clamp with an adjustable-tilt knuckle and bolts.
    tube(housing, [frame @ Vector((-0.09, 0, 0)), frame @ Vector((-0.02, 0, 0))], 0.040, res["tube"], BODY,
         cap_start=True)
    # Zhaga/NEMA sensor socket on top, towards the rear.
    sensor_base = frame @ Vector((0.13, 0, 0.056))
    tube(housing, [sensor_base, frame @ Vector((0.13, 0, 0.072))], 0.034, res["tube"], BODY, cap_end=True)
    if res["small"]:
        for y in (-0.03, 0.03):
            hex_bolt(housing, frame @ Vector((0.03, y, 0.058)), frame.to_3x3() @ Vector((0, 0, 1)), BODY, across=0.011)
        ring_bead(housing, frame @ Vector((0.0, 0, 0)), 0.050, 0.004, 20, BODY, normal=frame.to_3x3() @ Vector((1, 0, 0)))
        tube(housing, [frame @ Vector((0.13, 0, 0.072)), frame @ Vector((0.13, 0, 0.082))], 0.028, 12, BODY, cap_end=True)
    # Recess: a bezel 9 mm deep around the board.
    bx0, bx1, bw = 0.160, 0.600, 0.100
    zb = -0.016
    board = Builder()
    if lod < 2:
        t = 0.006
        for cx, cy, sx, sy in (((bx0 + bx1) / 2, bw + t / 2, bx1 - bx0 + 2 * t, t),
                               ((bx0 + bx1) / 2, -bw - t / 2, bx1 - bx0 + 2 * t, t),
                               (bx0 - t / 2, 0, t, 2 * bw), (bx1 + t / 2, 0, t, 2 * bw)):
            box(housing, (cx, cy, zb - 0.0045), (sx, sy, 0.009), BODY, frame)
    box(board, ((bx0 + bx1) / 2, 0, zb - 0.001), (bx1 - bx0, 2 * bw, 0.002), LED_BOARD, frame)
    emitter = Builder()
    if res["lenses"]:
        rows, cols = 4, 10
        for r in range(rows):
            for c in range(cols):
                x = bx0 + 0.022 + (bx1 - bx0 - 0.044) * c / (cols - 1)
                y = -bw + 0.028 + (2 * bw - 0.056) * r / (rows - 1)
                p0 = frame @ Vector((x, y, zb - 0.002))
                p1 = frame @ Vector((x, y, zb - 0.0045))
                tube(emitter, [p0, p1], 0.0068, 8, EMITTER, cap_end=True)
    else:
        box(emitter, ((bx0 + bx1) / 2, 0, zb - 0.003), (bx1 - bx0 - 0.02, 2 * bw - 0.03, 0.002), EMITTER, frame)
    glass = Builder()
    box(glass, ((bx0 + bx1) / 2, 0, zb - 0.0085), (bx1 - bx0, 2 * bw, 0.001), GLASS, frame)
    return housing, glass, emitter, dict(board=board, emitter=frame @ Vector(((bx0 + bx1) / 2, 0, zb - 0.01)))


def son_lantern(frame, lod, deep=False):
    """Compact cobra-head SON lantern.  `deep` is the older, deeper-bowl model."""
    res = LODS[lod]
    n = res["section"]
    L = 0.70 if deep else 0.58
    housing = Builder()
    stations = [
        (-0.030, 0.042, 0.044, 0.040, 0.000),
        (0.000, 0.052, 0.052, 0.042, 0.000),
        (0.050, 0.100, 0.070, 0.040, 0.004),
        (0.120, 0.124, 0.082, 0.036, 0.006),
        (0.250 * L / 0.58, 0.132, 0.084, 0.030, 0.004),
        (0.400 * L / 0.58, 0.124, 0.074, 0.028, -0.002),
        (0.500 * L / 0.58, 0.104, 0.058, 0.026, -0.008),
        (L - 0.035, 0.074, 0.040, 0.022, -0.012),
        (L - 0.010, 0.036, 0.024, 0.016, -0.013),
    ]
    if deep:
        # The older model: taller canopy, fuller shoulders.
        stations = [(x, hw * 1.04, th * 1.3, bh, dz) for x, hw, th, bh, dz in stations]
    superellipse_loft(housing, frame, resample(stations, res["loft"]), n, BODY, exponent=3.6 if deep else 5.0)
    housing.slot(REFLECTOR)
    tube(housing, [frame @ Vector((-0.08, 0, 0)), frame @ Vector((-0.025, 0, 0))], 0.040, res["tube"], BODY,
         cap_start=True)
    if res["small"]:
        ring_bead(housing, frame @ Vector((0.0, 0, 0)), 0.051, 0.0035, 20, BODY, normal=frame.to_3x3() @ Vector((1, 0, 0)))
        hex_bolt(housing, frame @ Vector((0.03, 0, -0.043)), frame.to_3x3() @ Vector((0, 0, -1)), BODY)
        box(housing, (0.09, 0, -0.045), (0.016, 0.044, 0.010), BODY, frame)
    glass = Builder()
    depth = 0.135 if deep else 0.058
    bowl = [
        (0.095, 0.100, depth * 0.40, -0.032),
        (0.130, 0.112, depth * 0.85, -0.030),
        (0.240 * L / 0.58, 0.116, depth, -0.028),
        (0.380 * L / 0.58, 0.110, depth * 0.95, -0.026),
        (0.470 * L / 0.58, 0.094, depth * 0.72, -0.024),
        (L - 0.055, 0.066, depth * 0.35, -0.022),
    ]
    bowl_loft(glass, frame, resample(bowl, max(res["loft"], 0.5)), max(8, n // 2), GLASS, exponent=2.1 if deep else 3.6)
    emitter = Builder()
    ex = 0.27 * L / 0.58
    if lod < 2:
        # SON-E ovoid (deep) or SON-T tube, lying along the lantern.
        seg = 10 if lod == 0 else 6
        if deep:
            prof = [(0.00, 0.010), (0.03, 0.028), (0.08, 0.036), (0.13, 0.030), (0.16, 0.014), (0.168, 0.004)]
            path = [frame @ Vector((ex - 0.08 + x, 0, -0.050)) for x, _ in prof]
            tube(emitter, path, [r for _, r in prof], seg, EMITTER, cap_start=True, cap_end=True)
        else:
            path = [frame @ Vector((ex - 0.075 + 0.15 * i / 4, 0, -0.045)) for i in range(5)]
            tube(emitter, path, 0.0125, seg, EMITTER, cap_start=True, cap_end=True)
        tube(housing, [frame @ Vector((ex - 0.12, 0, -0.034)), frame @ Vector((ex - 0.08, 0, -0.048))], 0.018, seg,
             REFLECTOR, cap_start=True, cap_end=True)
    else:
        box(emitter, (ex, 0, -0.045), (0.15, 0.04, 0.02), EMITTER, frame)
    return housing, glass, emitter, dict(reflector=(0.09, L - 0.05, 0.11),
                                         emitter=frame @ Vector((ex, 0, -0.05 if deep else -0.045)))


# ------------------------------------------------------------ the four assets

def lantern_frame(origin, pitch_deg, roll_deg=0.0, yaw_deg=0.0):
    """Lantern frame: +x along the lantern, pitched up (positive) about -y."""
    return (Matrix.Translation(origin) @ Matrix.Rotation(radians(yaw_deg), 4, "Z")
            @ Matrix.Rotation(radians(-pitch_deg), 4, "Y") @ Matrix.Rotation(radians(roll_deg), 4, "X"))


WARM_OLD = Spec(
    name="Streetlight_Warm_Old_01",
    slug="streetlight-warm-old-01",
    column=Column(
        profile=[(-0.02, 0.0965), (1.30, 0.0965), (1.33, 0.0935), (1.46, 0.0700)]
        + taper(1.46, 0.0700, 7.70, 0.0540, 8)[1:],
        door_z=(0.52, 1.02), door_width=0.105, plate_z=2.55, welds=[1.31, 1.46], lean=(0.012, -0.006),
    ),
    kind="sox",
    emitter_kelvin=1800,
    beam_deg=140.0,
)

LED_MODERN = Spec(
    name="Streetlight_LED_Modern_01",
    slug="streetlight-led-modern-01",
    column=Column(
        profile=[(-0.02, 0.0840), (1.95, 0.0840), (2.02, 0.0700), (2.06, 0.0695)]
        + taper(2.06, 0.0695, 5.10, 0.0620, 3)[1:]
        + [(5.14, 0.0575), (7.40, 0.0572)],
        door_z=(0.62, 1.12), door_width=0.090, plate_z=2.75, welds=[2.02, 5.12], ovality=0.0015,
    ),
    kind="led",
    emitter_kelvin=4000,
    beam_deg=120.0,
)

CURVED = Spec(
    name="Streetlight_Curved_01",
    slug="streetlight-curved-01",
    column=Column(
        profile=[(-0.02, 0.0720), (1.20, 0.0720), (1.26, 0.0600)]
        + taper(1.26, 0.0600, 6.10, 0.0470, 6)[1:],
        door_z=(0.40, 0.86), door_width=0.080, plate_z=2.40, welds=[1.23], lean=(-0.010, 0.014), ovality=0.004,
    ),
    kind="son_small",
    emitter_kelvin=2100,
    beam_deg=130.0,
)

WEATHERED = Spec(
    name="Streetlight_Weathered_01",
    slug="streetlight-weathered-01",
    column=Column(
        profile=[(-0.02, 0.0965), (1.38, 0.0965), (1.41, 0.0930), (1.54, 0.0695)]
        + taper(1.54, 0.0695, 7.55, 0.0560, 7)[1:],
        door_z=(0.55, 1.05), door_width=0.105, plate_z=2.35, welds=[1.39, 1.54], lean=(-0.030, 0.020),
        ovality=0.003,
    ),
    kind="son_bowl",
    emitter_kelvin=2000,
    beam_deg=135.0,
)

SPECS = [WARM_OLD, LED_MODERN, CURVED, WEATHERED]


def build_bracket(spec, b, lod):
    """Arm geometry from the column top to the lantern spigot.  Returns the lantern frame."""
    res = LODS[lod]
    col = spec.column
    top = col.profile[-1][0]
    ox, oy = column_axis(col, top)
    seg = res["tube"]
    if spec.kind == "sox":
        # Cast sleeve over the column top with a domed cap; short raked stub arm.
        sleeve = [(top - 0.24, 0.0600), (top - 0.23, 0.0625), (top + 0.02, 0.0625), (top + 0.05, 0.0560),
                  (top + 0.07, 0.0380), (top + 0.08, 0.0100)]
        lathe(b, sleeve, res["pole"], BODY, cap_top=True, axis_offset=lambda z: (ox, oy))
        z = top - 0.08
        start = Vector((ox + 0.05, oy, z))
        end = start + Vector((cos(radians(5)), 0, sin(radians(5)))) * 0.44
        tube(b, [start, (start + end) / 2, end], [0.031, 0.030, 0.030], seg, BODY, cap_end=False)
        if res["small"]:
            for a in (0, 120, 240):
                hex_bolt(b, (ox + 0.0625 * cos(radians(a + 60)), oy + 0.0625 * sin(radians(a + 60)), top - 0.18),
                         (cos(radians(a + 60)), sin(radians(a + 60)), 0), BODY, across=0.012)
        return lantern_frame(end + Vector((0.10, 0, 0.0)), 5.0, roll_deg=0.6)
    if spec.kind == "led":
        # Integral bracket: the 76 mm top section bends over through ~85 degrees.
        r_bend = 0.34
        steps = 10 if lod == 0 else (5 if lod == 1 else 3)
        pts = [Vector((ox, oy, top - 0.30)), Vector((ox, oy, top))]
        for i in range(1, steps + 1):
            a = radians(85) * i / steps
            pts.append(Vector((ox + r_bend * (1 - cos(a)), oy, top + r_bend * sin(a))))
        d = (pts[-1] - pts[-2]).normalized()
        end = pts[-1] + d * 0.22
        pts.append(end)
        radii = [0.0572] + [0.0572 - (0.0572 - 0.038) * min(1.0, i / (len(pts) - 2)) for i in range(1, len(pts))]
        tube(b, pts, radii, seg, BODY)
        if res["small"]:
            ring_bead(b, end - d * 0.02, 0.040, 0.0035, 20, BODY, normal=d)
        return lantern_frame(end + d * 0.09, 5.0)
    if spec.kind == "son_small":
        # Swan neck: bend radius opens from 0.52 to 0.64 m, and wanders 18 mm sideways.
        steps = 16 if lod == 0 else (8 if lod == 1 else 4)
        pts = [Vector((ox, oy, top - 0.20)), Vector((ox, oy, top))]
        total = radians(98)
        a = 0.0
        p = Vector((ox, oy, top))
        for i in range(1, steps + 1):
            da = total / steps
            r = 0.52 + 0.12 * (i / steps) ** 1.4
            a_mid = a + da / 2
            p = p + Vector((sin(a_mid), 0.0, cos(a_mid))) * r * da
            p.y = oy + 0.018 * (i / steps) ** 2
            a += da
            pts.append(p.copy())
        d = Vector((sin(total), 0, cos(total))).normalized()
        end = p + d * 0.16
        pts.append(end)
        radii = [0.047] + [0.047 - 0.017 * min(1.0, i / (len(pts) - 2)) for i in range(1, len(pts))]
        tube(b, pts, radii, seg, BODY, ovality=0.03)
        if res["small"]:
            ring_bead(b, end - d * 0.03, 0.0305, 0.003, 18, BODY, normal=d)
        pitch = -8.0 + 11.0  # arm ends 8 deg down; lantern rides 3 deg nose-up on its spigot
        return lantern_frame(end + d * 0.08 + Vector((0, 0, 0.004)), pitch, roll_deg=1.6, yaw_deg=1.1)
    # son_bowl: raked single arm with a curved strut, clamped to the column top.
    clamp = [(top - 0.36, 0.0690), (top - 0.35, 0.0715), (top - 0.04, 0.0715), (top - 0.03, 0.0690),
             (top - 0.01, 0.0600), (top, 0.0200)]
    lathe(b, clamp, res["pole"], BODY, cap_top=True, axis_offset=lambda z: column_axis(col, top))
    rake = radians(12)
    start = Vector((ox + 0.065, oy, top - 0.10))
    end = start + Vector((cos(rake), 0, sin(rake))) * 0.98
    tube(b, [start, start + (end - start) * 0.5, end], [0.031, 0.030, 0.029], seg, BODY)
    strut_steps = 6 if lod == 0 else 3
    strut = []
    for i in range(strut_steps + 1):
        t = i / strut_steps
        base = Vector((ox + 0.065, oy, top - 0.33))
        tip = start + (end - start) * 0.46
        mid = Vector((base.x + 0.12, oy, base.z + 0.02))
        strut.append(base * (1 - t) ** 2 + mid * 2 * t * (1 - t) + tip * t * t)
    tube(b, strut, 0.013, max(6, seg // 2), BODY)
    if res["small"]:
        for z in (top - 0.30, top - 0.12):
            hex_bolt(b, (ox - 0.0715, oy, z), (-1, 0, 0), BODY, across=0.014)
    return lantern_frame(end + Vector((cos(rake), 0, sin(rake))) * 0.085, 8.0, roll_deg=-1.2)


def build_asset(spec, lod, materials, collection):
    """Build one LOD of one asset.  Returns the created objects by part name."""
    suffix = f"_LOD{lod}"
    pole = Builder()
    build_column(pole, spec.column, lod)
    if LODS[lod]["small"]:
        build_plate(pole, spec.column, lod)
    arm = Builder()
    frame = build_bracket(spec, arm, lod)
    if spec.kind == "sox":
        housing, glass, emitter, info = sox_lantern(frame, lod)
    elif spec.kind == "led":
        housing, glass, emitter, info = led_lantern(frame, lod)
    else:
        housing, glass, emitter, info = son_lantern(frame, lod, deep=spec.kind == "son_bowl")

    objs = {}
    objs["Pole"] = pole.finish("Pole" + suffix, materials, (0, 0, 0), collection=collection)
    if lod < 2:
        door = Builder()
        build_access_panel(door, spec.column, lod)
        z0, z1 = spec.column.door_z
        objs["AccessPanel"] = door.finish("AccessPanel" + suffix, materials,
                                          (-radius_at(spec.column, z0), 0, z0), smooth_angle=30, collection=collection)
    spigot = frame.to_translation()
    col_top = spec.column.profile[-1][0]
    ox, oy = column_axis(spec.column, col_top)
    objs["Arm"] = arm.finish("Arm" + suffix, materials, (ox, oy, col_top), collection=collection)
    objs["LampHousing"] = housing.finish("LampHousing" + suffix, materials, spigot, smooth_angle=40, collection=collection)
    if "board" in info:
        objs["LEDBoard"] = info["board"].finish("LEDBoard" + suffix, materials, spigot, collection=collection)
    objs["LampGlass"] = glass.finish("LampGlass" + suffix, materials, spigot, smooth_angle=60, collection=collection)
    objs["LampEmitter"] = emitter.finish("LampEmitter" + suffix, materials, info["emitter"], smooth_angle=60,
                                         collection=collection)
    if "reflector" in info:
        x0, x1, hw = info["reflector"]
        mark_reflector(objs["LampHousing"], frame, x0, x1, hw, materials[REFLECTOR])
    return objs, info["emitter"], frame


def triangle_count(objects):
    total = 0
    for obj in objects:
        for poly in obj.data.polygons:
            total += len(poly.vertices) - 2
    return total
