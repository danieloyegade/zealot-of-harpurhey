"""Geometry for the Spice Cabin end unit (reference-led, see docs/assets/spice-cabin.md).

Dimensions are photographic estimates from references/architecture/buildings/spice-cabin/,
scaled from the ~2.0 m door opening and 75 mm UK brick courses.  One Blender
unit is one metre, Z is up, ground is Z = 0, the origin is the centre of the
footprint and the shopfront faces -Y.  The gable (photographed with the newer
sign and phone number) faces -X.

Everything is built from explicit vertices so no hidden faces are exported:
party-wall and wall-top faces that are always covered are simply never made.
Placeholder materials are keyed by atlas; createSpiceCabin.py rebuilds them.
"""

from math import cos, pi, radians, sin

import bmesh
import bpy
import numpy as np
from mathutils import Vector

# ----------------------------------------------------------------- layout

FRONT_Y = -3.50        # pier face / building line
BRICK_FRONT_Y = -3.30  # parapet brick face above the cream band
BOARD_FACE_Y = -3.28   # dark boarding behind the front sign
GLASS_Y = -3.20        # glazing and loglap backing plane
SIDE_X = -3.05         # gable brick face
PIER_X = (-3.10, -2.55)
RIGHT_X = 3.10         # party line with the neighbouring unit
BACK_Y = 3.50

PLINTH_TOP = 0.10
BOARD_TOP = 1.12
GLASS_TOP = 1.95
HEAD_TOP = 2.02
FASCIA_TOP = 2.48
SIGN_FRONT = (2.52, 3.56)
BAND = (3.62, 4.02)
PARAPET_TOP = 4.76
ROOF_Z = 4.55
BRICK_CHANGE_Z = 3.35  # brown ground-storey brick below, buff above (gable)

BLUE_POSTS = ((-2.55, -2.45), (-0.62, -0.50), (2.86, 2.98))
DOOR_JAMBS = ((-0.50, -0.43), (0.43, 0.53))
MULLIONS = ((-1.57, -1.50), (1.91, 1.98))
BAYS = (("LeftA", -2.45, -1.57), ("LeftB", -1.50, -0.62), ("RightA", 0.53, 1.91), ("RightB", 1.98, 2.86))
BOARD_COURSES = 13

FRONT_SIGN_PLATE = (-2.44, 2.30)
SIDE_SIGN_PLATE = (-2.00, 2.60)       # along Y on the gable
SIDE_SIGN_Z = (2.62, 3.62)
DISC_OVERHANG = 0.14                  # sawn log-end cut-outs beyond each plate end
DISC_VERTICAL = 0.09

BOLLARDS = ((-3.28, -4.50), (-2.38, -4.42), (-1.90, -4.58), (0.55, -4.46))

GROUP_NAMES = (
    "SPICE_structure", "SPICE_brick_wall", "SPICE_cream_pier", "SPICE_sign",
    "SPICE_blue_fascia", "SPICE_window_frames", "SPICE_glass", "SPICE_door",
    "SPICE_log_cladding", "SPICE_bollards", "SPICE_security_wire",
    "SPICE_pipework", "SPICE_alarm_fixtures", "SPICE_interior_cards",
    "SPICE_ground_contact", "SPICE_anchors",
)

MATERIAL_KEYS = {
    "brick": "MAT_brick_aged_tan",
    "paint": "MAT_cream_painted_concrete",
    "blue": "MAT_blue_painted_frame",
    "timber": "MAT_log_cladding_weathered",
    "metal": "MAT_dark_metal",
    "sign": "MAT_sign_printed_wood",
    "glass": "MAT_glass_shopfront",
    "interior": "MAT_interior_dark",
    "emissive": "MAT_emissive_signage",
    "ground": "MAT_ground_contact",
    "felt": "MAT_roof_felt",
}


# ------------------------------------------------------------- utilities

def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def create_materials():
    mats = {}
    for key, name in MATERIAL_KEYS.items():
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        mats[key] = mat
    felt = mats["felt"].node_tree.nodes["Principled BSDF"]
    felt.inputs["Base Color"].default_value = (0.035, 0.034, 0.032, 1)
    felt.inputs["Roughness"].default_value = 0.95
    return mats


class Builder:
    """Creates named mesh objects under group empties of one asset root."""

    def __init__(self, collection_name="SPICE_CABIN", root_name="SPICE_CABIN"):
        self.collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(self.collection)
        self.root = self.empty(root_name, (0, 0, 0), None)
        self.groups = {}

    def group(self, name):
        if name not in self.groups:
            self.groups[name] = self.empty(name, (0, 0, 0), self.root)
        return self.groups[name]

    def empty(self, name, location, parent, size=0.2):
        obj = bpy.data.objects.new(name, None)
        obj.empty_display_type = "PLAIN_AXES"
        obj.empty_display_size = size
        obj.location = location
        self.collection.objects.link(obj)
        if parent is not None:
            obj.parent = parent
        return obj

    def mesh(self, name, verts, faces, group, mat, smooth=False, sharp_angle=35, recalc=True):
        mesh = bpy.data.meshes.new(f"{name}_mesh")
        mesh.from_pydata([tuple(map(float, v)) for v in verts], [], faces)
        mesh.validate(clean_customdata=False)
        if recalc:
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
            bm.to_mesh(mesh)
            bm.free()
        mesh.materials.append(mat)
        if smooth:
            mesh.shade_smooth()
            mesh.set_sharp_from_angle(angle=radians(sharp_angle))
        obj = bpy.data.objects.new(name, mesh)
        self.collection.objects.link(obj)
        obj.parent = self.group(group)
        return obj


def bevel_mesh(obj, offset, segments=2):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.bevel(bm, geom=bm.verts[:] + bm.edges[:], offset=offset, segments=segments,
                    affect="EDGES", clamp_overlap=True, profile=0.5)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.shade_smooth()
    obj.data.set_sharp_from_angle(angle=radians(40))


BOX_FACES = {
    "-x": (0, 4, 7, 3), "+x": (1, 2, 6, 5), "-y": (0, 1, 5, 4),
    "+y": (3, 7, 6, 2), "-z": (0, 3, 2, 1), "+z": (4, 5, 6, 7),
}


def box(b, name, x, y, z, group, mat, faces="all", bevel=0.0):
    (x0, x1), (y0, y1), (z0, z1) = x, y, z
    verts = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
             (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    keys = BOX_FACES.keys() if faces == "all" else faces
    used = [BOX_FACES[k] for k in keys]
    obj = b.mesh(name, verts, used, group, mat, recalc=(faces == "all"))
    if faces != "all":
        _orient_box_faces(obj, keys)
    if bevel and faces == "all":
        bevel_mesh(obj, bevel)
    return obj


def _orient_box_faces(obj, keys):
    wanted = {"-x": (-1, 0, 0), "+x": (1, 0, 0), "-y": (0, -1, 0), "+y": (0, 1, 0), "-z": (0, 0, -1), "+z": (0, 0, 1)}
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    for face, key in zip(bm.faces, keys):
        face.normal_update()
        if face.normal.dot(Vector(wanted[key])) < 0:
            face.normal_flip()
    bm.to_mesh(mesh)
    bm.free()


def quad(b, name, corners, group, mat, normal):
    obj = b.mesh(name, corners, [(0, 1, 2, 3)], group, mat, recalc=False)
    if obj.data.polygons[0].normal.dot(Vector(normal)) < 0:
        obj.data.flip_normals()
    return obj


def sweep_arrays(points, profile, closed_profile=True, caps=False, up=(0, 0, 1)):
    """Rings of a 2D profile swept along a polyline with transported frames."""
    P = [Vector(p) for p in points]
    n = len(P)
    tangents = []
    for i in range(n):
        a = P[max(i - 1, 0)]
        c = P[min(i + 1, n - 1)]
        tangents.append((c - a).normalized())
    side = tangents[0].cross(Vector(up))
    if side.length < 1e-4:
        side = tangents[0].cross(Vector((1, 0, 0)))
    side.normalize()
    verts, faces = [], []
    m = len(profile)
    for i in range(n):
        t = tangents[i]
        side = (side - t * side.dot(t)).normalized()
        upv = side.cross(t)
        verts.extend(P[i] + side * px + upv * py for px, py in profile)
    count = m if closed_profile else m - 1
    for i in range(n - 1):
        for j in range(count):
            a, bb = i * m + j, i * m + (j + 1) % m
            faces.append((a, bb, bb + m, a + m))
    if caps:
        faces.append(tuple(range(m))[::-1])
        faces.append(tuple((n - 1) * m + j for j in range(m)))
    return verts, faces


def circle(radius, segments, phase=0.0):
    return [(radius * cos(2 * pi * k / segments + phase), radius * sin(2 * pi * k / segments + phase)) for k in range(segments)]


def pipe(b, name, points, radius, group, mat, segments=12, caps=True):
    verts, faces = sweep_arrays(points, circle(radius, segments), caps=caps)
    return b.mesh(name, verts, faces, group, mat, smooth=True, sharp_angle=50)


def flat_bar(b, name, points, width, thickness, group, mat, up=(0, 0, 1)):
    hw, ht = width / 2, thickness / 2
    verts, faces = sweep_arrays(points, [(-hw, -ht), (hw, -ht), (hw, ht), (-hw, ht)], caps=True, up=up)
    return b.mesh(name, verts, faces, group, mat)


def merge_parts(b, name, parts, group, mat, smooth=False):
    verts, faces = [], []
    for part_verts, part_faces in parts:
        offset = len(verts)
        verts.extend(part_verts)
        faces.extend(tuple(i + offset for i in face) for face in part_faces)
    return b.mesh(name, verts, faces, group, mat, smooth=smooth)


# ------------------------------------------------------------- the building

def build_masonry(b, m):
    g = "SPICE_brick_wall"
    # Parapet brick above the cream band, full frontage width.
    quad(b, "SPICE_Brick_FrontParapet",
         [(SIDE_X - 0.05, BRICK_FRONT_Y, BAND[1]), (RIGHT_X, BRICK_FRONT_Y, BAND[1]),
          (RIGHT_X, BRICK_FRONT_Y, PARAPET_TOP), (SIDE_X - 0.05, BRICK_FRONT_Y, PARAPET_TOP)], g, m["brick"], (0, -1, 0))
    # Gable: two faces, the strip beside the band and the full wall behind the pier.
    gx = SIDE_X
    b.mesh("SPICE_Brick_Gable", [
        (gx, -2.95, 0.0), (gx, BACK_Y, 0.0), (gx, BACK_Y, PARAPET_TOP), (gx, -2.95, PARAPET_TOP),
        (gx - 0.05, BRICK_FRONT_Y, BAND[1]), (gx - 0.05, -2.95, BAND[1]), (gx - 0.05, -2.95, PARAPET_TOP), (gx - 0.05, BRICK_FRONT_Y, PARAPET_TOP),
    ], [(0, 3, 2, 1), (4, 7, 6, 5)], g, m["brick"], recalc=False)
    _flip_to(b, "SPICE_Brick_Gable", (-1, 0, 0))
    quad(b, "SPICE_Brick_Back",
         [(gx, BACK_Y, 0.0), (RIGHT_X, BACK_Y, 0.0), (RIGHT_X, BACK_Y, PARAPET_TOP), (gx, BACK_Y, PARAPET_TOP)], g, m["brick"], (0, 1, 0))

    g = "SPICE_structure"
    # Roof deck and parapet inner faces are only visible from above.
    quad(b, "SPICE_Roof_Deck", [(gx + 0.30, -3.00, ROOF_Z), (RIGHT_X, -3.00, ROOF_Z), (RIGHT_X, BACK_Y - 0.30, ROOF_Z), (gx + 0.30, BACK_Y - 0.30, ROOF_Z)],
         g, m["felt"], (0, 0, 1))
    b.mesh("SPICE_Parapet_Inner", [
        (gx + 0.30, -3.00, ROOF_Z), (RIGHT_X, -3.00, ROOF_Z), (RIGHT_X, -3.00, PARAPET_TOP), (gx + 0.30, -3.00, PARAPET_TOP),
        (gx + 0.30, BACK_Y - 0.30, ROOF_Z), (gx + 0.30, BACK_Y - 0.30, PARAPET_TOP),
        (RIGHT_X, BACK_Y - 0.30, ROOF_Z), (RIGHT_X, BACK_Y - 0.30, PARAPET_TOP),
    ], [(0, 3, 2, 1), (4, 5, 3, 0), (4, 6, 7, 5)], g, m["felt"])

    # Concrete upstand the shopfront stands on.
    box(b, "SPICE_Plinth_Shopfront", (PIER_X[1], 2.98), (-3.44, -3.16), (0.0, PLINTH_TOP), g, m["paint"], bevel=0.01)

    g = "SPICE_cream_pier"
    box(b, "SPICE_CreamPier", PIER_X, (FRONT_Y, -2.95), (0.0, BAND[0]), g, m["paint"], bevel=0.012)
    box(b, "SPICE_CreamBand", (-3.14, 2.92), (-3.62, -3.20), BAND, g, m["paint"], bevel=0.015)
    # Green PVC coping with drip lips over both faces of each parapet.
    lip = [(-0.20, -0.05), (-0.20, 0.055), (0.20, 0.07), (0.20, -0.05), (0.188, -0.05), (0.188, 0.0), (-0.188, 0.0), (-0.188, -0.05)]
    for name, points in (("Front", [(-3.14, -3.15, PARAPET_TOP), (RIGHT_X, -3.15, PARAPET_TOP)]),
                         ("Gable", [(-2.90, -3.34, PARAPET_TOP), (-2.90, BACK_Y + 0.04, PARAPET_TOP)]),
                         ("Back", [(-3.14, BACK_Y - 0.15, PARAPET_TOP), (RIGHT_X, BACK_Y - 0.15, PARAPET_TOP)])):
        verts, faces = sweep_arrays(points, lip, caps=True)
        b.mesh(f"SPICE_Coping_{name}", verts, faces, g, m["paint"])


def _flip_to(b, name, normal):
    obj = bpy.data.objects[name]
    for poly in obj.data.polygons:
        if poly.normal.dot(Vector(normal)) < 0:
            poly.flip()


def build_shopfront(b, m):
    g = "SPICE_blue_fascia"
    box(b, "SPICE_Blue_Fascia", (PIER_X[1], 2.92), (FRONT_Y, -3.20), (HEAD_TOP, FASCIA_TOP), g, m["blue"], bevel=0.012)

    g = "SPICE_window_frames"
    for i, (x0, x1) in enumerate(BLUE_POSTS, 1):
        box(b, f"SPICE_Blue_Post_{i:02d}", (x0, x1), (-3.32, -3.14), (PLINTH_TOP, HEAD_TOP), g, m["blue"], bevel=0.008)
    box(b, "SPICE_Timber_Head", (-2.45, 2.86), (-3.30, -3.14), (GLASS_TOP, HEAD_TOP), g, m["timber"], bevel=0.006)
    for i, (x0, x1) in enumerate(MULLIONS, 1):
        box(b, f"SPICE_Timber_Mullion_{i:02d}", (x0, x1), (-3.29, -3.15), (PLINTH_TOP, GLASS_TOP), g, m["timber"], bevel=0.006)
    for name, x0, x1 in BAYS:
        box(b, f"SPICE_Timber_Sill_{name}", (x0, x1), (-3.33, -3.15), (BOARD_TOP, BOARD_TOP + 0.045), g, m["timber"], bevel=0.006)
        box(b, f"SPICE_Timber_Bead_{name}", (x0, x1), (-3.235, -3.19), (GLASS_TOP - 0.03, GLASS_TOP), g, m["timber"])

    g = "SPICE_glass"
    for name, x0, x1 in BAYS:
        quad(b, f"SPICE_Glass_{name}", [(x0, GLASS_Y, BOARD_TOP + 0.045), (x1, GLASS_Y, BOARD_TOP + 0.045),
                                         (x1, GLASS_Y, GLASS_TOP - 0.03), (x0, GLASS_Y, GLASS_TOP - 0.03)], g, m["glass"], (0, -1, 0))

    g = "SPICE_door"
    for i, (x0, x1) in enumerate(DOOR_JAMBS, 1):
        box(b, f"SPICE_Timber_DoorJamb_{i:02d}", (x0, x1), (-3.31, -3.12), (PLINTH_TOP, GLASS_TOP), g, m["timber"], bevel=0.006)
    box(b, "SPICE_Door_Threshold", (-0.43, 0.43), (-3.30, -3.10), (PLINTH_TOP, PLINTH_TOP + 0.018), g, m["metal"])
    # The door stands open inward in both front photographs.
    hinge_x = -0.43
    box(b, "SPICE_Timber_DoorLeaf", (hinge_x + 0.005, hinge_x + 0.05), (-3.10, -2.28), (PLINTH_TOP + 0.01, GLASS_TOP - 0.02), g, m["timber"], bevel=0.006)

    g = "SPICE_log_cladding"
    rng = np.random.default_rng(1601)
    pitch = (BOARD_TOP - PLINTH_TOP) / BOARD_COURSES
    for name, x0, x1 in BAYS:
        quad(b, f"SPICE_LogBacking_{name}", [(x0, GLASS_Y, PLINTH_TOP), (x1, GLASS_Y, PLINTH_TOP),
                                              (x1, GLASS_Y, BOARD_TOP), (x0, GLASS_Y, BOARD_TOP)], g, m["timber"], (0, -1, 0))
        parts = []
        for course in range(BOARD_COURSES):
            zb = PLINTH_TOP + course * pitch + rng.normal(0, 0.0012)
            bulge = 0.021 + rng.normal(0, 0.0015)
            h = pitch
            # Loglap profile: lipped bottom edge, convex face, tucked top edge.
            profile_yz = [(0.0, 0.0), (-0.005, 0.0), (-0.013, 0.004), (-bulge * 0.92, 0.018), (-bulge, 0.036),
                          (-bulge * 0.86, 0.054), (-bulge * 0.5, 0.068), (-0.002, h)]
            wobble = rng.normal(0, 0.0008, 2)
            ring0 = [(x0 + 0.002, GLASS_Y + y + wobble[0], zb + z) for y, z in profile_yz]
            ring1 = [(x1 - 0.002, GLASS_Y + y + wobble[1], zb + z + rng.normal(0, 0.0006)) for y, z in profile_yz]
            verts = ring0 + ring1
            k = len(profile_yz)
            faces = [(j, j + 1, k + j + 1, k + j) for j in range(k - 1)]
            parts.append((verts, faces))
        obj = merge_parts(b, f"SPICE_LogBoards_{name}", parts, g, m["timber"], smooth=True)
        for poly in obj.data.polygons:
            if poly.normal.y > 0.05:
                poly.flip()


def build_signs(b, m):
    g = "SPICE_sign"
    box(b, "SPICE_Boarding_Front", (PIER_X[1], 2.98), (BOARD_FACE_Y, -3.20), (FASCIA_TOP, BAND[0]), g, m["paint"], faces=("-y", "-x", "-z"))
    x0, x1 = FRONT_SIGN_PLATE
    z0, z1 = SIGN_FRONT
    box(b, "SPICE_Sign_Front_Board", (x0, x1), (-3.36, BOARD_FACE_Y), (z0, z1), g, m["paint"], faces=("-y", "-x", "+x", "-z", "+z"))
    quad(b, "SPICE_Sign_Front_Face", [(x0 - DISC_OVERHANG, -3.362, z0 - DISC_VERTICAL), (x1 + DISC_OVERHANG, -3.362, z0 - DISC_VERTICAL),
                                      (x1 + DISC_OVERHANG, -3.362, z1 + DISC_VERTICAL), (x0 - DISC_OVERHANG, -3.362, z1 + DISC_VERTICAL)],
         g, m["sign"], (0, -1, 0))
    y0, y1 = SIDE_SIGN_PLATE
    z0, z1 = SIDE_SIGN_Z
    box(b, "SPICE_Sign_Side_Board", (SIDE_X - 0.08, SIDE_X), (y0, y1), (z0, z1), g, m["paint"], faces=("-x", "-y", "+y", "-z", "+z"))
    quad(b, "SPICE_Sign_Side_Face", [(SIDE_X - 0.082, y1 + DISC_OVERHANG, z0 - DISC_VERTICAL), (SIDE_X - 0.082, y0 - DISC_OVERHANG, z0 - DISC_VERTICAL),
                                     (SIDE_X - 0.082, y0 - DISC_OVERHANG, z1 + DISC_VERTICAL), (SIDE_X - 0.082, y1 + DISC_OVERHANG, z1 + DISC_VERTICAL)],
         g, m["sign"], (-1, 0, 0))


def build_services(b, m):
    g = "SPICE_pipework"
    # Pale tube fittings: under the band on the front, on stand-offs above the gable sign.
    pipe(b, "SPICE_Tube_Front", [(-2.95, -3.665, 3.575), (2.20, -3.665, 3.575)], 0.034, g, m["paint"], segments=12)
    quad(b, "SPICE_TubeDiffuser_Front", [(-2.85, -3.68, 3.537), (2.10, -3.68, 3.537), (2.10, -3.65, 3.537), (-2.85, -3.65, 3.537)],
         g, m["emissive"], (0, 0, -1))
    for i, x in enumerate((-2.60, -0.95, 0.70, 1.95), 1):
        flat_bar(b, f"SPICE_TubeClip_Front_{i:02d}", [(x, -3.62, 3.625), (x, -3.665, 3.61)], 0.03, 0.004, g, m["metal"], up=(1, 0, 0))
    tube_x = SIDE_X - 0.19
    pipe(b, "SPICE_Tube_Side", [(tube_x, -1.95, 4.10), (tube_x, 2.30, 4.10)], 0.034, g, m["paint"], segments=12)
    quad(b, "SPICE_TubeDiffuser_Side", [(tube_x - 0.015, -1.85, 4.063), (tube_x + 0.015, -1.85, 4.063),
                                         (tube_x + 0.015, 2.20, 4.063), (tube_x - 0.015, 2.20, 4.063)], g, m["emissive"], (0, 0, -1))
    for i, y in enumerate((-1.55, 0.18, 1.90), 1):
        flat_bar(b, f"SPICE_TubeStandoff_Side_{i:02d}",
                 [(SIDE_X, y, 4.00), (SIDE_X - 0.08, y, 4.03), (tube_x, y, 4.10)], 0.035, 0.008, g, m["paint"], up=(0, 1, 0))
        box(b, f"SPICE_TubeStandoffPlate_Side_{i:02d}", (SIDE_X - 0.012, SIDE_X), (y - 0.035, y + 0.035), (3.96, 4.05), g, m["paint"])

    # Hopper head on the band end, swan neck past it, downpipe to a kicked shoe.
    hopper = [(2.67, -3.62, 4.28), (2.93, -3.62, 4.28), (2.93, -3.34, 4.28), (2.67, -3.34, 4.28),
              (2.73, -3.56, 4.06), (2.87, -3.56, 4.06), (2.87, -3.40, 4.06), (2.73, -3.40, 4.06)]
    b.mesh("SPICE_Hopper", hopper, [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7)], g, m["metal"])
    pipe(b, "SPICE_Downpipe", [(2.80, -3.48, 4.08), (2.86, -3.48, 4.02), (2.96, -3.47, 3.95), (3.00, -3.465, 3.84),
                               (3.00, -3.465, 0.24), (3.00, -3.50, 0.12), (3.00, -3.60, 0.075)], 0.034, g, m["metal"], segments=12)
    pipe(b, "SPICE_Downpipe_Collar", [(3.00, -3.465, 1.82), (3.00, -3.465, 1.90)], 0.041, g, m["metal"], segments=12)
    for i, z in enumerate((0.9, 2.4, 3.5), 1):
        flat_bar(b, f"SPICE_DownpipeClip_{i:02d}", [(3.00, -3.40, z), (3.00, -3.505, z)], 0.03, 0.01, g, m["metal"], up=(0, 0, 1))

    g = "SPICE_alarm_fixtures"
    box(b, "SPICE_AlarmSounder", (2.60, 2.85), (-3.37, BOARD_FACE_Y), (2.93, 3.23), g, m["paint"], bevel=0.035)
    # CCTV bullet camera on the pier, under the band.
    pipe(b, "SPICE_CCTV_Body", [(-2.84, -3.60, 3.39), (-2.90, -3.76, 3.33)], 0.034, g, m["paint"], segments=10)
    box(b, "SPICE_CCTV_Hood", (-2.93, -2.81), (-3.80, -3.56), (3.365, 3.385), g, m["paint"])
    flat_bar(b, "SPICE_CCTV_Bracket", [(-2.84, -3.50, 3.44), (-2.84, -3.58, 3.40)], 0.03, 0.02, g, m["paint"])
    # Red LED window sign hung inside the right window.
    box(b, "SPICE_LEDSign_Case", (1.08, 1.80), (-3.155, -3.13), (1.56, 1.89), g, m["metal"])
    quad(b, "SPICE_LEDSign_Face", [(1.09, -3.157, 1.57), (1.79, -3.157, 1.57), (1.79, -3.157, 1.88), (1.09, -3.157, 1.88)],
         g, m["emissive"], (0, -1, 0))


def build_security(b, m, rng):
    g = "SPICE_security_wire"
    runs = (
        ("Front", Vector((-3.14, -3.12, 4.965)), Vector((RIGHT_X, -3.12, 4.965))),
        ("Gable", Vector((-3.00, -3.12, 4.965)), Vector((-3.00, BACK_Y - 0.05, 4.965))),
        ("Hopper", Vector((2.42, -3.50, 4.40)), Vector((RIGHT_X, -3.50, 4.40))),
    )
    for name, p0, p1 in runs:
        axis = (p1 - p0)
        length = axis.length
        axis.normalize()
        perp1 = axis.cross(Vector((0, 0, 1))).normalized()
        perp2 = perp1.cross(axis)
        parts = [sweep_arrays([p0, p1], circle(0.013, 6))]
        pitch = 0.10
        count = int(length / pitch)
        for i in range(count):
            c = p0 + axis * (pitch * (i + 0.5) + rng.normal(0, 0.006))
            phase = rng.uniform(0, 2 * pi)
            # Three offset vane stars per rotor give the bushy, leaf-like cluster
            # photographed rather than a regular row of stars.
            for star in (-1, 0, 1):
                cs = c + axis * (star * 0.018)
                for k in range(5):
                    a = phase + k * 2 * pi / 5 + star * 0.42 + rng.normal(0, 0.16)
                    d = perp1 * cos(a) + perp2 * sin(a)
                    tangent = perp1 * -sin(a) + perp2 * cos(a)
                    reach = rng.uniform(0.06, 0.11) if star else rng.uniform(0.04, 0.07)
                    b0 = cs + d * 0.011 + axis * 0.006
                    b1 = cs + d * 0.011 - axis * 0.006
                    b2 = cs + d * 0.011 + tangent * 0.012
                    tip = cs + d * reach + tangent * rng.uniform(-0.004, 0.024) + axis * rng.normal(0, 0.006)
                    parts.append(([b0, b1, b2, tip], [(0, 2, 1), (0, 1, 3), (1, 2, 3), (2, 0, 3)]))
        b.mesh(f"SPICE_AntiClimb_{name}", *_merged(parts), g, m["metal"])

    brackets = []
    for x in np.arange(-2.85, RIGHT_X, 0.95):
        brackets.append(sweep_arrays([(x, BRICK_FRONT_Y - 0.004, 4.40), (x, BRICK_FRONT_Y - 0.004, 4.70), (x, -3.37, 4.75),
                                      (x, -3.37, 4.86), (x, -3.14, 4.965)], [(-0.02, -0.003), (0.02, -0.003), (0.02, 0.003), (-0.02, 0.003)],
                                     caps=True, up=(1, 0, 0)))
    for y in np.arange(-2.60, BACK_Y, 0.95):
        brackets.append(sweep_arrays([(SIDE_X - 0.004, y, 4.40), (SIDE_X - 0.004, y, 4.70), (SIDE_X - 0.07, y, 4.75),
                                      (SIDE_X - 0.07, y, 4.86), (-3.01, y, 4.965)], [(-0.02, -0.003), (0.02, -0.003), (0.02, 0.003), (-0.02, 0.003)],
                                     caps=True, up=(0, 1, 0)))
    for x in (2.55, 3.02):
        brackets.append(sweep_arrays([(x, -3.40, BAND[1]), (x, -3.45, 4.25), (x, -3.50, 4.40)],
                                     [(-0.02, -0.003), (0.02, -0.003), (0.02, 0.003), (-0.02, 0.003)], caps=True, up=(1, 0, 0)))
    b.mesh("SPICE_AntiClimb_Brackets", *_merged(brackets), g, m["metal"])


def _merged(parts):
    verts, faces = [], []
    for part_verts, part_faces in parts:
        offset = len(verts)
        verts.extend(part_verts)
        faces.extend(tuple(i + offset for i in face) for face in part_faces)
    return verts, faces


def build_bollards(b, m, rng):
    g = "SPICE_bollards"
    for i, (x, y) in enumerate(BOLLARDS, 1):
        lean = Vector((rng.normal(0, 0.012), rng.normal(0, 0.012), 1.0)).normalized()
        base = Vector((x, y, -0.06))
        top = base + lean * 0.99
        profile = circle(0.07, 16)
        verts, faces = sweep_arrays([base, top - lean * 0.015, top], profile, caps=False)
        # Shallow domed cap.
        ring_start = 2 * 16
        cap_ring = [top + lean * 0.012 + Vector((px * 0.72, py * 0.72, 0)) for px, py in profile]
        verts.extend(cap_ring)
        verts.append(top + lean * 0.02)
        for k in range(16):
            a, c = ring_start + k, ring_start + (k + 1) % 16
            faces.append((a, c, c + 16, a + 16))
            faces.append((a + 16, c + 16, len(verts) - 1))
        b.mesh(f"SPICE_Bollard_{i:02d}", verts, faces, g, m["metal"], smooth=True, sharp_angle=60)


def build_interior(b, m):
    g = "SPICE_interior_cards"
    x0, x1 = -2.45, 2.86
    yf, yb = -3.12, -0.35
    ceiling = 2.55
    quad(b, "SPICE_Interior_Floor", [(x0, yf, PLINTH_TOP), (x1, yf, PLINTH_TOP), (x1, yb, PLINTH_TOP), (x0, yb, PLINTH_TOP)], g, m["interior"], (0, 0, 1))
    quad(b, "SPICE_Interior_Ceiling", [(x0, yf, ceiling), (x1, yf, ceiling), (x1, yb, ceiling), (x0, yb, ceiling)], g, m["interior"], (0, 0, -1))
    quad(b, "SPICE_Interior_BackWall", [(x0, yb, PLINTH_TOP), (x1, yb, PLINTH_TOP), (x1, yb, ceiling), (x0, yb, ceiling)], g, m["interior"], (0, -1, 0))
    quad(b, "SPICE_Interior_LeftWall", [(x0, yf, PLINTH_TOP), (x0, yb, PLINTH_TOP), (x0, yb, ceiling), (x0, yf, ceiling)], g, m["interior"], (1, 0, 0))
    quad(b, "SPICE_Interior_RightWall", [(x1, yf, PLINTH_TOP), (x1, yb, PLINTH_TOP), (x1, yb, ceiling), (x1, yf, ceiling)], g, m["interior"], (-1, 0, 0))
    box(b, "SPICE_Interior_Counter", (-2.40, -0.10), (-1.55, -1.02), (PLINTH_TOP, 1.04), g, m["interior"], faces=("-y", "+z", "+x"))
    box(b, "SPICE_Interior_CounterTop", (-2.42, -0.06), (-1.60, -0.98), (1.04, 1.075), g, m["metal"], faces=("-y", "+z", "+x", "-z"))
    box(b, "SPICE_Interior_Fridge", (0.62, 1.24), (-1.02, -0.40), (PLINTH_TOP, 2.02), g, m["interior"], faces=("-x", "+x", "+z", "-y"))
    quad(b, "SPICE_Interior_FridgeFront", [(0.67, -1.025, 0.22), (1.19, -1.025, 0.22), (1.19, -1.025, 1.86), (0.67, -1.025, 1.86)],
         g, m["emissive"], (0, -1, 0))
    box(b, "SPICE_Interior_WindowLedge", (0.66, 2.78), (-3.10, -2.84), (BOARD_TOP + 0.04, BOARD_TOP + 0.08), g, m["interior"], faces=("-y", "+z", "-z", "+y"))
    for i, xc in enumerate((-1.95, -1.25, -0.55), 1):
        quad(b, f"SPICE_Interior_MenuBoard_{i:02d}", [(xc - 0.31, yb - 0.02, 1.72), (xc + 0.31, yb - 0.02, 1.72),
                                                       (xc + 0.31, yb - 0.02, 2.26), (xc - 0.31, yb - 0.02, 2.26)], g, m["emissive"], (0, -1, 0))
    for i, (xc, yc) in enumerate(((-1.25, -2.30), (1.55, -2.30), (-1.25, -1.10)), 1):
        quad(b, f"SPICE_Interior_CeilingPanel_{i:02d}", [(xc - 0.3, yc - 0.3, ceiling - 0.005), (xc + 0.3, yc - 0.3, ceiling - 0.005),
                                                          (xc + 0.3, yc + 0.3, ceiling - 0.005), (xc - 0.3, yc + 0.3, ceiling - 0.005)],
             g, m["emissive"], (0, 0, -1))


GROUND_FRONT = ((-3.70, 3.30), (-5.40, -3.44))
GROUND_SIDE = ((-4.40, -3.10), (-3.44, BACK_Y))


def build_ground_contact(b, m):
    (fx0, fx1), (fy0, fy1) = GROUND_FRONT
    (sx0, sx1), (sy0, sy1) = GROUND_SIDE
    z = 0.004
    obj = b.mesh("SPICE_GroundContact_Decal", [
        (fx0, fy0, z), (fx1, fy0, z), (fx1, fy1, z), (fx0, fy1, z),
        (sx0, sy0, z), (sx1, sy0, z), (sx1, sy1, z), (sx0, sy1, z),
    ], [(0, 1, 2, 3), (4, 5, 6, 7)], "SPICE_ground_contact", m["ground"], recalc=False)
    for poly in obj.data.polygons:
        if poly.normal.z < 0:
            poly.flip()
    return obj


def build_anchors(b):
    g = b.group("SPICE_anchors")
    for name, location in (
        ("SPICE_EntranceAnchor", (0.0, -4.20, 0.0)),
        ("SPICE_DeliveryAnchor", (-1.00, -4.05, 0.0)),
        ("SPICE_LightAnchor_Window", (1.40, -2.90, 2.25)),
        ("SPICE_LightAnchor_Door", (0.0, -2.95, 2.30)),
        ("SPICE_LightAnchor_Sign", (-0.07, -3.95, 3.50)),
        ("SPICE_LightAnchor_SideSign", (-3.70, 0.30, 4.00)),
        ("SPICE_LightAnchor_LEDSign", (1.44, -3.30, 1.72)),
    ):
        b.empty(name, location, g, 0.12)


def build_asset(mats, seed=1601):
    rng = np.random.default_rng(seed)
    b = Builder()
    for name in GROUP_NAMES:
        b.group(name)
    build_masonry(b, mats)
    build_shopfront(b, mats)
    build_signs(b, mats)
    build_services(b, mats)
    build_security(b, mats, rng)
    build_bollards(b, mats, rng)
    build_interior(b, mats)
    build_ground_contact(b, mats)
    build_anchors(b)
    return b


def asset_meshes(builder):
    return [obj for obj in builder.collection.objects if obj.type == "MESH"]


def meshes_with(builder, mat):
    return [obj for obj in asset_meshes(builder) if obj.data.materials and obj.data.materials[0] == mat]
