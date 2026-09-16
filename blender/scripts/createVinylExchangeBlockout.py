"""Create the Vinyl Exchange architectural blockout and five clay review renders.

First-pass massing model per the brief in
references/architecture/buildings/vinyl-exchange/14_Vinyl_Exchange.txt
(section 45). It contains the full Oldham Street / Dale Street corner massing,
the chamfered corner, three storeys of real arched upper openings with
reveals, plain pier and archivolt massing, the grey fascia, both shopfronts,
the corner recess, the Dale Street security-gate recess, glazing, a simple
interior shell, and placement proxies for the logo, tagline, side sign and
both street-name plaques.

Deliberately NOT here yet (second pass, brief section 47): half-round
colonnettes, carved capitals, moulded arch profiles, relief bands, vent
louvres, rib grooves, the accordion lattice, cables and detailed frames.

One Blender unit equals one metre. Ground (pavement top) = Z 0.
Plan convention: the Oldham Street building line is Y 0 and faces -Y; the
Dale Street building line is X 0 and faces +X; the two are joined by a 45
degree chamfer of CHAMFER_LEN. Standing on Oldham Street facing the shop,
Dale Street recedes to the right, matching the reference photographs.

All dimensions are inferred from people, doors, pier rhythm and fascia
proportions in the references, not surveyed -- consistent with every other
hero-location blockout in this project. The upper two storeys are inferred
from the one night photograph that shows them; no reference shows the roof.
"""

import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLEND_PATH = PROJECT_ROOT / "blender" / "source" / "vinyl_exchange_blockout.blend"
RENDER_DIR = PROJECT_ROOT / "renders" / "vinyl-exchange-blockout"
# Heavy condensed grotesque closest to the fascia lettering that ships with
# macOS. Falls back to Blender's built-in font elsewhere (proxy only).
LOGO_FONT = Path("/System/Library/Fonts/Supplemental/Arial Narrow Bold.ttf")

SQRT2 = math.sqrt(2.0)

# Plan (estimated from pier rhythm: 1.85 m bays in every elevation photo).
CHAMFER_LEN = 1.60
C = CHAMFER_LEN / SQRT2
OLDHAM_UPPER_LEN = 6.31  # arris -> party pier edge above fig + sparrow
OLDHAM_SHOP_LEN = 5.35   # arris -> Vinyl Exchange left ribbed pier
DALE_LEN = 10.01         # arris -> end of the Vinyl Exchange unit

BAY = 1.85
PIER_W = 0.70
CORNER_PIER_SPAN = 0.76  # arris pier width measured along each street face
CHAMFER_PIER_SPAN = 0.30
WINDOW_HW = 0.50
CHAMFER_WINDOW_HW = 0.40
OLDHAM_WINDOWS = tuple(1.335 + BAY * k for k in range(3))
DALE_WINDOWS = tuple(1.335 + BAY * k for k in range(5))
OLDHAM_PIERS = tuple(0.41 + BAY * k for k in range(1, 4))
DALE_PIERS = tuple(0.41 + BAY * k for k in range(1, 6))

# Heights.
PLINTH_TOP = 0.25
GLAZING_TOP = 2.35
VENT_BOTTOM, VENT_TOP = 2.40, 2.90
FASCIA_BOTTOM, FASCIA_TOP = 2.95, 4.30
FASCIA_FRONT_W = -0.32
UPPER_WALL_DEPTH = 0.45
CORNICE_BOTTOM, CORNICE_TOP = 13.35, 13.75
PARAPET_TOP = 14.45

FLOORS = (
    {"name": "F1", "sill": 4.40, "spring": 6.20, "impost": (6.00, 6.35), "arch_r": (0.60, 0.85),
     "pier_bottom": FASCIA_TOP, "pier_proj": 0.22, "arch_proj": 0.12, "band": (7.30, 7.65), "band_proj": 0.10, "sill_ledge": False},
    {"name": "F2", "sill": 7.95, "spring": 9.45, "impost": (9.25, 9.55), "arch_r": (0.58, 0.80),
     "pier_bottom": 7.65, "pier_proj": 0.18, "arch_proj": 0.10, "band": (10.50, 10.80), "band_proj": 0.08, "sill_ledge": True},
    {"name": "F3", "sill": 11.05, "spring": 12.35, "impost": (12.15, 12.40), "arch_r": (0.56, 0.76),
     "pier_bottom": 10.80, "pier_proj": 0.15, "arch_proj": 0.08, "band": None, "band_proj": 0.0, "sill_ledge": True},
)
CHAMFER_ARCH_R = (0.48, 0.62)


# ---------------------------------------------------------------------------
# Facade frames: (u along the face away from its start, w inward from the
# building line, z up). Every street element is authored in one of these.
# ---------------------------------------------------------------------------

class Frame:
    def __init__(self, origin, tangent, inward):
        self.origin, self.tangent, self.inward = origin, tangent, inward

    def xy(self, u, w):
        return (
            self.origin[0] + u * self.tangent[0] + w * self.inward[0],
            self.origin[1] + u * self.tangent[1] + w * self.inward[1],
        )

    def point(self, u, w, z):
        return (*self.xy(u, w), z)


OLDHAM = Frame((-C, 0.0), (-1.0, 0.0), (0.0, 1.0))
CHAMFER = Frame((-C, 0.0), (1 / SQRT2, 1 / SQRT2), (-1 / SQRT2, 1 / SQRT2))
DALE = Frame((0.0, C), (0.0, 1.0), (-1.0, 0.0))


def street_polyline(w, oldham_end, dale_end):
    """The Oldham -> chamfer -> Dale building line offset inward by w."""
    k = SQRT2 - 1
    return [(-C - oldham_end, w), (-C - w * k, w), (-w, C + w * k), (-w, C + dale_end)]


def footprint(w):
    return street_polyline(w, OLDHAM_UPPER_LEN, DALE_LEN) + [(-C - OLDHAM_UPPER_LEN, C + DALE_LEN)]


def ribbon(w_out, w_in, oldham_end, dale_end):
    return street_polyline(w_out, oldham_end, dale_end) + list(reversed(street_polyline(w_in, oldham_end, dale_end)))


def arc_points(uc, zc, r, a0, a1, segments):
    return [
        (uc + r * math.cos(math.radians(a0 + (a1 - a0) * i / segments)), zc + r * math.sin(math.radians(a0 + (a1 - a0) * i / segments)))
        for i in range(segments + 1)
    ]


def arched_poly(uc, hw, z0, spring, segments=12):
    return [(uc - hw, z0), (uc + hw, z0)] + arc_points(uc, spring, hw, 0, 180, segments)


def arch_band_poly(uc, zc, r_in, r_out, segments=14):
    return arc_points(uc, zc, r_out, 0, 180, segments) + arc_points(uc, zc, r_in, 180, 0, segments)


# ---------------------------------------------------------------------------
# Scene / collection / material helpers (pattern shared with the other
# blockout scripts in this project, e.g. createComeThroughLabBlockout.py).
# ---------------------------------------------------------------------------

def clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for datablocks in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights, bpy.data.curves, bpy.data.texts):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)


def make_collection(name, parent=None):
    result = bpy.data.collections.new(name)
    (parent.children if parent else bpy.context.scene.collection.children).link(result)
    return result


def make_material(name, color, roughness=0.85, metallic=0.0, alpha=1.0):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, alpha)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, alpha)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        material.surface_render_method = "DITHERED"
    return material


class MeshBuilder:
    """Accumulates closed prisms into one mesh object (few objects, no bpy.ops)."""

    def __init__(self):
        self.bm = bmesh.new()

    def prism(self, bottom, top):
        b = [self.bm.verts.new(p) for p in bottom]
        t = [self.bm.verts.new(p) for p in top]
        self.bm.faces.new(b)
        self.bm.faces.new(t)
        for i in range(len(b)):
            j = (i + 1) % len(b)
            self.bm.faces.new((b[i], b[j], t[j], t[i]))

    def frame_poly(self, frame, poly_uz, w0, w1):
        self.prism([frame.point(u, w0, z) for u, z in poly_uz], [frame.point(u, w1, z) for u, z in poly_uz])

    def frame_box(self, frame, u0, u1, w0, w1, z0, z1):
        self.frame_poly(frame, [(u0, z0), (u1, z0), (u1, z1), (u0, z1)], w0, w1)

    def plan_poly(self, pts, z0, z1):
        self.prism([(x, y, z0) for x, y in pts], [(x, y, z1) for x, y in pts])

    def finish(self, name, material, collection, origin=(0.0, 0.0, 0.0)):
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces[:])
        if any(origin):
            bmesh.ops.translate(self.bm, verts=self.bm.verts[:], vec=Vector(origin) * -1)
        mesh = bpy.data.meshes.new(f"{name}_Mesh")
        self.bm.to_mesh(mesh)
        self.bm.free()
        mesh.materials.append(material)
        obj = bpy.data.objects.new(name, mesh)
        obj.location = origin
        collection.objects.link(obj)
        return obj


def single_box(name, frame, u0, u1, w0, w1, z0, z1, material, collection):
    mb = MeshBuilder()
    mb.frame_box(frame, u0, u1, w0, w1, z0, z1)
    return mb.finish(name, material, collection)


def empty(name, location, collection, display="PLAIN_AXES", size=0.5):
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    obj.empty_display_type = display
    obj.empty_display_size = size
    collection.objects.link(obj)
    return obj


def parent_keep(child, parent_obj, parent_world_location):
    child.parent = parent_obj
    child.matrix_parent_inverse = Matrix.Translation(parent_world_location).inverted()


def camera(name, location, target, lens, collection, shift_y=0.0):
    data = bpy.data.cameras.new(f"{name}_Data")
    data.lens = lens
    data.sensor_width = 36
    data.sensor_fit = "AUTO"
    data.shift_y = shift_y
    data.clip_start = 0.05
    data.clip_end = 300
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    collection.objects.link(obj)
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    return obj


# ---------------------------------------------------------------------------
# Upper facade -- real arched openings with reveals (brief sections 5-6).
# ---------------------------------------------------------------------------

def add_wall_with_openings(mb, frame, u0, u1, z0, z1, columns, w0, w1, segments=12):
    """Punch stacked semicircular-headed openings through a wall slab.

    columns: [(uc, hw, [(sill, spring), ...]), ...] sorted by uc. The slab is
    split into plain strips between columns and, within a column, sill-height
    rectangles plus two arch-shouldered halves per opening, so every piece is
    a simple polygon and extruding it through the wall produces the reveal.
    """
    half = segments // 2
    cursor = u0
    for uc, hw, openings in columns:
        ul, ur = uc - hw, uc + hw
        if ul - cursor > 1e-4:
            mb.frame_box(frame, cursor, ul, w0, w1, z0, z1)
        z = z0
        ordered = sorted(openings)
        for index, (sill, spring) in enumerate(ordered):
            if sill - z > 1e-4:
                mb.frame_box(frame, ul, ur, w0, w1, z, sill)
            top = ordered[index + 1][0] if index + 1 < len(ordered) else z1
            mb.frame_poly(frame, [(ul, top), (uc, top)] + arc_points(uc, spring, hw, 90, 180, half), w0, w1)
            mb.frame_poly(frame, [(uc, top), (ur, top)] + arc_points(uc, spring, hw, 0, 90, half), w0, w1)
            z = top
        cursor = ur
    if u1 - cursor > 1e-4:
        mb.frame_box(frame, cursor, u1, w0, w1, z0, z1)


def build_upper_window(label, frame, uc, hw, sill, spring, mats, groups):
    fw, w0, w1 = 0.07, 0.20, 0.28
    ul, ur = uc - hw, uc + hw
    lower = sill + 0.42 * (spring - sill)
    mb = MeshBuilder()
    mb.frame_box(frame, ul, ul + fw, w0, w1, sill, spring)
    mb.frame_box(frame, ur - fw, ur, w0, w1, sill, spring)
    mb.frame_box(frame, ul, ur, w0, w1, sill, sill + fw)
    mb.frame_poly(frame, arch_band_poly(uc, spring, hw - fw, hw, 12), w0, w1)
    mb.frame_box(frame, uc - 0.03, uc + 0.03, w0, w1, sill + fw, spring + hw - fw)
    mb.frame_box(frame, ul + fw, ur - fw, w0, w1, spring - 0.035, spring + 0.035)
    mb.frame_box(frame, ul + fw, ur - fw, w0, w1, lower - 0.03, lower + 0.03)
    mb.finish(f"VE_Window_{label}", mats["frames"], groups["windows"])

    glass = MeshBuilder()
    glass.frame_poly(frame, arched_poly(uc, hw - 0.02, sill + 0.02, spring, 12), 0.24, 0.25)
    glass.finish(f"VE_Glass_Upper_{label}", mats["glass"], groups["glass"])


def arris_polygon_oldham(p, face_span, chamfer_span):
    k = SQRT2 - 1
    return [OLDHAM.xy(face_span, 0), OLDHAM.xy(face_span, -p), (-C + p * k, -p), CHAMFER.xy(chamfer_span, -p), CHAMFER.xy(chamfer_span, 0), (-C, 0.0)]


def arris_polygon_dale(p, face_span, chamfer_span):
    k = SQRT2 - 1
    return [CHAMFER.xy(CHAMFER_LEN - chamfer_span, 0), CHAMFER.xy(CHAMFER_LEN - chamfer_span, -p), (p, C - p * k), DALE.xy(face_span, -p), DALE.xy(face_span, 0), (0.0, C)]


def build_upper_facade(mats, groups):
    faces = (
        ("Oldham", OLDHAM, OLDHAM_UPPER_LEN, OLDHAM_WINDOWS, WINDOW_HW, OLDHAM_PIERS, (0.60, 0.85)),
        ("Corner", CHAMFER, CHAMFER_LEN, (CHAMFER_LEN / 2,), CHAMFER_WINDOW_HW, (), CHAMFER_ARCH_R),
        ("Dale", DALE, DALE_LEN, DALE_WINDOWS, WINDOW_HW, DALE_PIERS, (0.60, 0.85)),
    )

    for face_name, frame, length, windows, hw, piers, _ in faces:
        wall = MeshBuilder()
        columns = [(uc, hw, [(floor["sill"], floor["spring"]) for floor in FLOORS]) for uc in windows]
        add_wall_with_openings(wall, frame, 0.0, length, FASCIA_TOP, CORNICE_BOTTOM, columns, 0.0, UPPER_WALL_DEPTH)
        wall.finish(f"VE_UpperFacade_Wall_{face_name}", mats["stone"], groups["upper"])

        for floor in FLOORS:
            arch_r = CHAMFER_ARCH_R if face_name == "Corner" else floor["arch_r"]
            ornament = MeshBuilder()
            for uc in windows:
                ornament.frame_poly(frame, arch_band_poly(uc, floor["impost"][1], arch_r[0], arch_r[1]), -floor["arch_proj"], 0.02)
                if floor["sill_ledge"]:
                    ornament.frame_box(frame, uc - hw - 0.06, uc + hw + 0.06, -0.10, 0.05, floor["sill"] - 0.08, floor["sill"])
            ornament.finish(f"VE_ArchSurrounds_{face_name}_{floor['name']}", mats["stone"], groups["ornament"])

            if not piers:
                continue
            pier_mb = MeshBuilder()
            for pc in piers:
                phw = PIER_W / 2
                pier_mb.frame_box(frame, pc - phw, pc + phw, -floor["pier_proj"], 0.02, floor["pier_bottom"], floor["impost"][0])
                pier_mb.frame_box(frame, pc - phw - 0.06, pc + phw + 0.06, -(floor["pier_proj"] + 0.08), 0.02, *floor["impost"])
                if floor["name"] == "F1":
                    pier_mb.frame_box(frame, pc - phw - 0.05, pc + phw + 0.05, -0.28, 0.02, FASCIA_TOP, 4.75)
            pier_mb.finish(f"VE_Piers_{face_name}_{floor['name']}", mats["stone"], groups["upper"])

        for index, uc in enumerate(windows, start=1):
            for floor in FLOORS:
                label = f"Corner_{floor['name']}" if face_name == "Corner" else f"{face_name}_{floor['name']}_{index:02d}"
                build_upper_window(label, frame, uc, hw, floor["sill"], floor["spring"], mats, groups)

    # Arris piers straddle each end of the chamfer (brief sections 11, 41).
    for floor in FLOORS:
        corner = MeshBuilder()
        p = floor["pier_proj"]
        for polygon in (arris_polygon_oldham, arris_polygon_dale):
            corner.plan_poly(polygon(p, CORNER_PIER_SPAN, CHAMFER_PIER_SPAN), floor["pier_bottom"], floor["impost"][0])
            corner.plan_poly(polygon(p + 0.08, CORNER_PIER_SPAN + 0.06, CHAMFER_PIER_SPAN + 0.06), *floor["impost"])
            if floor["name"] == "F1":
                corner.plan_poly(polygon(0.28, CORNER_PIER_SPAN + 0.05, CHAMFER_PIER_SPAN + 0.05), FASCIA_TOP, 4.75)
        corner.finish(f"VE_Piers_CornerArris_{floor['name']}", mats["stone"], groups["corner"])

    bands = MeshBuilder()
    for floor in FLOORS:
        if floor["band"]:
            bands.plan_poly(ribbon(-floor["band_proj"], 0.05, OLDHAM_UPPER_LEN, DALE_LEN), *floor["band"])
    bands.finish("VE_StringCourses", mats["stone"], groups["ornament"])

    cornice = MeshBuilder()
    cornice.plan_poly(ribbon(-0.40, UPPER_WALL_DEPTH, OLDHAM_UPPER_LEN, DALE_LEN), CORNICE_BOTTOM, CORNICE_TOP)
    cornice.plan_poly(ribbon(0.0, 0.40, OLDHAM_UPPER_LEN, DALE_LEN), CORNICE_TOP, PARAPET_TOP)
    cornice.finish("VE_Cornice_Parapet_INFERRED", mats["stone"], groups["ornament"])


# ---------------------------------------------------------------------------
# Ground floor -- shopfronts, corner recess, gate recess, fascia.
# ---------------------------------------------------------------------------

def add_shopfront_window(frames_mb, frame, u0, u1, glass_name, mats, groups):
    frames_mb.frame_box(frame, u0, u1, 0.0, 0.35, 0.0, PLINTH_TOP)
    frames_mb.frame_box(frame, u0, u1, -0.02, 0.16, PLINTH_TOP, PLINTH_TOP + 0.07)
    frames_mb.frame_box(frame, u0, u0 + 0.05, -0.02, 0.16, PLINTH_TOP, GLAZING_TOP)
    frames_mb.frame_box(frame, u1 - 0.05, u1, -0.02, 0.16, PLINTH_TOP, GLAZING_TOP)
    frames_mb.frame_box(frame, u0, u1, -0.02, 0.16, GLAZING_TOP - 0.05, VENT_BOTTOM)
    single_box(glass_name, frame, u0 + 0.05, u1 - 0.05, 0.11, 0.13, PLINTH_TOP + 0.07, GLAZING_TOP - 0.05, mats["glass"], groups["glass"])


def add_vents(frame, segments, label, mats, groups):
    rails, louvres = MeshBuilder(), MeshBuilder()
    for a, b in segments:
        rails.frame_box(frame, a, b, -0.02, 0.08, VENT_BOTTOM, VENT_BOTTOM + 0.04)
        rails.frame_box(frame, a, b, -0.02, 0.08, VENT_TOP - 0.04, FASCIA_BOTTOM)
        rails.frame_box(frame, a, a + 0.04, -0.02, 0.08, VENT_BOTTOM, VENT_TOP)
        rails.frame_box(frame, b - 0.04, b, -0.02, 0.08, VENT_BOTTOM, VENT_TOP)
        louvres.frame_box(frame, a, b, 0.08, 0.14, VENT_BOTTOM, VENT_TOP)
    rails.finish(f"VE_Vent_{label}_Frame", mats["metal"], groups["vents"])
    louvres.finish(f"VE_Vent_{label}_LouvreZone", mats["vent"], groups["vents"])


def build_door_leaf(name, u_hinge, u_free, door_empty, mats, groups):
    ua, ub = sorted((u_hinge, u_free))
    handle_u = u_free + (0.13 if u_free < u_hinge else -0.13)
    hinge = OLDHAM.point(u_hinge, 0.11, 0.0)

    leaf = MeshBuilder()
    leaf.frame_box(OLDHAM, ua, ua + 0.09, 0.08, 0.14, 0.02, 2.30)
    leaf.frame_box(OLDHAM, ub - 0.09, ub, 0.08, 0.14, 0.02, 2.30)
    leaf.frame_box(OLDHAM, ua, ub, 0.08, 0.14, 0.02, 0.22)
    leaf.frame_box(OLDHAM, ua, ub, 0.08, 0.14, 2.21, 2.30)
    leaf.frame_box(OLDHAM, handle_u - 0.02, handle_u + 0.02, 0.02, 0.08, 0.75, 1.55)
    leaf_obj = leaf.finish(name, mats["metal"], groups["oldham"], origin=hinge)
    parent_keep(leaf_obj, door_empty, door_empty.location)

    glass = MeshBuilder()
    glass.frame_box(OLDHAM, ua + 0.09, ub - 0.09, 0.105, 0.115, 0.22, 2.21)
    glass_obj = glass.finish(name.replace("VE_MainDoor", "VE_MainDoorGlass"), mats["glass"], groups["glass"], origin=hinge)
    parent_keep(glass_obj, leaf_obj, Vector(hinge))


def build_oldham_front(mats, groups):
    g = groups["oldham"]
    ribs = MeshBuilder()
    ribs.frame_box(OLDHAM, 0.0, 0.55, -0.08, 0.35, 0.0, FASCIA_BOTTOM)
    ribs.frame_box(OLDHAM, 4.85, OLDHAM_SHOP_LEN, -0.08, 0.35, 0.0, FASCIA_BOTTOM)
    ribs.finish("VE_RibbedPanel_Oldham", mats["metal"], g)

    side = MeshBuilder()
    side.frame_box(OLDHAM, 0.55, 1.00, 0.15, 0.35, 0.0, GLAZING_TOP)
    side.finish("VE_OldhamFront_SidePanel", mats["green"], g)

    frames = MeshBuilder()
    add_shopfront_window(frames, OLDHAM, 1.00, 2.25, "VE_Glass_MainShop_Right", mats, groups)
    add_shopfront_window(frames, OLDHAM, 3.80, 4.85, "VE_Glass_MainShop_Left", mats, groups)
    frames.finish("VE_OldhamFront_WindowFrames", mats["metal"], g)

    door_u0, door_u1 = 2.25, 3.80
    door_frame = MeshBuilder()
    door_frame.frame_box(OLDHAM, door_u0, door_u0 + 0.06, -0.02, 0.16, 0.0, VENT_BOTTOM)
    door_frame.frame_box(OLDHAM, door_u1 - 0.06, door_u1, -0.02, 0.16, 0.0, VENT_BOTTOM)
    door_frame.frame_box(OLDHAM, door_u0, door_u1, -0.02, 0.16, 2.30, VENT_BOTTOM)
    door_frame.frame_box(OLDHAM, door_u0, door_u1, -0.05, 0.35, 0.0, 0.02)
    door_frame.finish("VE_MainDoorFrame", mats["metal"], g)

    door_mid = (door_u0 + door_u1) / 2
    entrance = empty("VE_MainEntrance", OLDHAM.point(door_mid, 0.11, 1.15), g, "CUBE", 1.0)
    entrance.scale = ((door_u1 - door_u0) / 2, 0.15, 1.15)
    door_empty = empty("VE_MainDoor", OLDHAM.point(door_mid, 0.11, 0.0), g, "PLAIN_AXES", 0.4)
    build_door_leaf("VE_MainDoor_LeafLeft", door_u1 - 0.06, door_mid, door_empty, mats, groups)
    build_door_leaf("VE_MainDoor_LeafRight", door_u0 + 0.06, door_mid, door_empty, mats, groups)

    single_box("VE_Display_Right", OLDHAM, 1.10, 2.15, 0.40, 0.42, 0.35, 2.25, mats["display"], g)
    single_box("VE_Display_Left", OLDHAM, 3.90, 4.75, 0.40, 0.42, 0.35, 2.25, mats["display"], g)

    add_vents(OLDHAM, ((0.55, door_u0), (door_u0, door_u1), (door_u1, 4.85)), "Oldham", mats, groups)

    empty("VE_EntranceAnchor", OLDHAM.point(door_mid, -1.2, 1.0), groups["anchors"], "ARROWS", 0.5)
    empty("VE_InteriorSpawnAnchor", OLDHAM.point(door_mid, 2.5, 0.0), groups["anchors"], "ARROWS", 0.5)


def build_corner(mats, groups):
    g = groups["corner"]
    recess = MeshBuilder()
    recess.frame_box(CHAMFER, -0.30, 0.0, 0.0, 0.95, 0.0, GLAZING_TOP)
    recess.frame_box(CHAMFER, 0.0, 1.20, 0.0, 0.95, 0.0, 0.03)
    recess.finish("VE_CornerRecess_Shell", mats["metal"], g)

    single_box("VE_CornerRecess_GreenDoor", CHAMFER, 0.02, 1.18, 0.85, 0.92, 0.02, GLAZING_TOP - 0.02, mats["green"], g)

    tiles = MeshBuilder()
    tiles.frame_box(CHAMFER, 1.20, CHAMFER_LEN, -0.05, 0.95, 0.0, FASCIA_BOTTOM)
    tiles.frame_box(DALE, 0.0, 0.20, -0.05, 0.95, 0.0, FASCIA_BOTTOM)
    tiles.frame_box(DALE, 9.68, DALE_LEN, -0.02, 0.35, 0.0, FASCIA_BOTTOM)
    tiles.finish("VE_Corner_TiledColumns", mats["tile"], g)

    single_box("VE_CornerShutter_Housing", CHAMFER, 0.0, 1.20, 0.0, 0.12, VENT_BOTTOM, VENT_TOP, mats["vent"], groups["shutters"])

    gate_u0, gate_u1 = 0.43, 1.95
    gate_recess = MeshBuilder()
    gate_recess.frame_box(DALE, 0.20, gate_u0, -0.05, 0.95, 0.0, FASCIA_BOTTOM)
    gate_recess.frame_box(DALE, gate_u0, gate_u1, 0.90, 1.00, 0.0, GLAZING_TOP)
    gate_recess.frame_box(DALE, gate_u0, gate_u1, 0.0, 0.95, 0.0, 0.03)
    gate_recess.finish("VE_DaleFront_GateRecess", mats["metal"], g)

    ac = MeshBuilder()
    ac.frame_box(DALE, 0.62, 1.38, 0.45, 0.88, 0.10, 0.95)
    ac.frame_box(DALE, 0.62, 1.38, 0.45, 0.88, 1.00, 1.85)
    ac.finish("VE_CornerRecess_ACUnits", mats["vent"], g)

    gate = MeshBuilder()
    gate.frame_box(DALE, gate_u0, gate_u0 + 0.06, -0.04, 0.04, 0.0, GLAZING_TOP)
    gate.frame_box(DALE, gate_u1 - 0.06, gate_u1, -0.04, 0.04, 0.0, GLAZING_TOP)
    gate.frame_box(DALE, gate_u0, gate_u1, -0.04, 0.04, GLAZING_TOP - 0.07, GLAZING_TOP)
    gate.frame_box(DALE, gate_u0, gate_u1, -0.03, 0.03, 0.0, 0.04)
    pickets = 9
    for i in range(1, pickets + 1):
        u = gate_u0 + (gate_u1 - gate_u0) * i / (pickets + 1)
        gate.frame_box(DALE, u - 0.015, u + 0.015, -0.02, 0.02, 0.04, GLAZING_TOP - 0.07)
    gate.finish("VE_CornerSecurityGate", mats["metal"], groups["grilles"])


def build_dale_front(mats, groups):
    g = groups["dale"]
    ribs = MeshBuilder()
    for a, b in ((1.95, 2.16), (4.57, 5.46), (9.18, 9.68)):
        ribs.frame_box(DALE, a, b, -0.08, 0.35, 0.0, FASCIA_BOTTOM)
    ribs.finish("VE_RibbedPanel_Dale", mats["metal"], g)

    frames = MeshBuilder()
    add_shopfront_window(frames, DALE, 2.16, 4.57, "VE_Glass_DaleStreet_01", mats, groups)
    add_shopfront_window(frames, DALE, 5.46, 9.18, "VE_Glass_DaleStreet_02", mats, groups)
    frames.finish("VE_DaleFront_WindowFrames", mats["metal"], g)

    single_box("VE_SideWindowGraphicSurface", DALE, 5.60, 9.05, 0.095, 0.105, 0.30, 1.45, mats["display"], g)
    add_vents(DALE, ((0.43, 1.95), (2.16, 4.57), (5.46, 9.18)), "Dale", mats, groups)


def build_shells(mats, groups):
    upper = MeshBuilder()
    upper.plan_poly(footprint(UPPER_WALL_DEPTH), FASCIA_TOP, CORNICE_BOTTOM)
    upper.finish("VE_BuildingShell_Upper", mats["stone"], groups["shell"])

    fascia_zone = MeshBuilder()
    fascia_zone.plan_poly(footprint(0.10), GLAZING_TOP, FASCIA_TOP)
    fascia_zone.finish("VE_BuildingShell_FasciaZone", mats["interior"], groups["shell"])

    fascia = MeshBuilder()
    fascia.plan_poly(ribbon(FASCIA_FRONT_W, 0.10, OLDHAM_SHOP_LEN, DALE_LEN), FASCIA_BOTTOM, FASCIA_TOP)
    fascia.finish("VE_Fascia_Main", mats["fascia"], groups["fascia"])

    interior_end_oldham, interior_end_dale = 5.05, 9.68
    floor_poly = street_polyline(0.30, interior_end_oldham, interior_end_dale) + [(-C - interior_end_oldham, C + interior_end_dale)]
    shell = MeshBuilder()
    shell.plan_poly(floor_poly, -0.10, 0.0)
    shell.finish("VE_InteriorShell_Floor", mats["interior"], groups["interior"])
    ceiling = MeshBuilder()
    ceiling.plan_poly(floor_poly, GLAZING_TOP - 0.05, GLAZING_TOP)
    ceiling.finish("VE_InteriorShell_Ceiling", mats["interior"], groups["interior"])
    walls = MeshBuilder()
    walls.frame_box(OLDHAM, interior_end_oldham, OLDHAM_SHOP_LEN, 0.35, C + DALE_LEN, 0.0, GLAZING_TOP)
    walls.frame_box(DALE, interior_end_dale, DALE_LEN, 0.35, C + OLDHAM_SHOP_LEN, 0.0, GLAZING_TOP)
    walls.finish("VE_InteriorShell_SideAndRearWalls", mats["interior"], groups["interior"])


# ---------------------------------------------------------------------------
# Signage and plaques -- placement proxies for review (sections 13-18).
# ---------------------------------------------------------------------------

def logo_text(name, body, frame, reading_sign, u_start, width, z_edge, edge, mats, collection, depth=0.06):
    font = bpy.data.fonts.load(str(LOGO_FONT), check_existing=True) if LOGO_FONT.exists() else None
    curve = bpy.data.curves.new(f"{name}_Text", "FONT")
    curve.body = body
    curve.extrude = 0.05
    if font:
        curve.font = font
    temp = bpy.data.objects.new(f"{name}_Temp", curve)
    bpy.context.scene.collection.objects.link(temp)
    bpy.context.view_layer.update()
    mesh = bpy.data.meshes.new_from_object(temp.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(temp, do_unlink=True)
    bpy.data.curves.remove(curve)

    xs = [v.co.x for v in mesh.vertices]
    ys = [v.co.y for v in mesh.vertices]
    zs = [v.co.z for v in mesh.vertices]
    scale = width / (max(xs) - min(xs))
    height = (max(ys) - min(ys)) * scale
    z_bottom = z_edge if edge == "bottom" else z_edge - height

    base = Vector(frame.point(u_start, FASCIA_FRONT_W, z_bottom))
    read = Vector((frame.tangent[0] * reading_sign, frame.tangent[1] * reading_sign, 0.0))
    out = Vector((-frame.inward[0], -frame.inward[1], 0.0))
    up = Vector((0.0, 0.0, 1.0))
    z_span = max(zs) - min(zs) or 1.0
    for v in mesh.vertices:
        local = v.co.copy()
        v.co = base + read * ((local.x - min(xs)) * scale) + up * ((local.y - min(ys)) * scale) + out * ((local.z - min(zs)) / z_span * depth)
    mesh.update()
    mesh.name = f"{name}_Mesh"
    mesh.materials.append(mats["logo"])
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def build_signage(mats, groups):
    g = groups["signage"]
    vinyl_w, exchange_w = 0.75, 1.49
    # Oldham Street: right-aligned 0.27 m from the arris; reads along -u.
    logo_text("VE_MainLogo_vinyl", "vinyl", OLDHAM, -1, 0.27 + vinyl_w, vinyl_w, 4.12, "top", mats, g)
    logo_text("VE_MainLogo_exchange", "exchange", OLDHAM, -1, 0.27 + exchange_w, exchange_w, 3.42, "bottom", mats, g)
    single_box("VE_TaglineSurface", OLDHAM, 0.27, 2.74, FASCIA_FRONT_W - 0.015, FASCIA_FRONT_W, 3.08, 3.33, mats["tagline"], g)
    # Dale Street: left-aligned 0.25 m from the arris; reads along +u.
    logo_text("VE_DaleLogo_vinyl", "vinyl", DALE, 1, 0.25, vinyl_w, 4.12, "top", mats, g)
    logo_text("VE_DaleLogo_exchange", "exchange", DALE, 1, 0.25, exchange_w, 3.42, "bottom", mats, g)
    single_box("VE_TaglineSurface_Dale", DALE, 0.28, 4.98, FASCIA_FRONT_W - 0.015, FASCIA_FRONT_W, 3.08, 3.33, mats["tagline"], g)

    single_box("VE_SideLogo_Box", CHAMFER, -0.10, CHAMFER_LEN + 0.10, -0.62, -0.30, 2.75, 4.25, mats["black"], g)
    single_box("VE_SideLogoSurface", CHAMFER, 0.0, CHAMFER_LEN, -0.635, -0.62, 2.90, 4.10, mats["black"], g)

    p = groups["plaques"]
    single_box("VE_Plaque_OldhamStreet", OLDHAM, OLDHAM_PIERS[0] - 0.265, OLDHAM_PIERS[0] + 0.265, -0.30, -0.28, 4.41, 4.71, mats["plaque"], p)
    single_box("VE_Plaque_DaleStreet", DALE, 0.28, 0.78, -0.30, -0.28, 4.45, 4.73, mats["plaque"], p)


# ---------------------------------------------------------------------------
# Assembly, context, cameras, renders
# ---------------------------------------------------------------------------

def build_context(mats, groups):
    g = groups["context"]
    pavement = MeshBuilder()
    pavement.plan_poly(ribbon(-3.6, 0.0, OLDHAM_UPPER_LEN + 8.0, DALE_LEN + 8.0), -0.12, 0.0)
    pavement.finish("VE_Context_Pavement", mats["pavement"], g)
    road = MeshBuilder()
    road.plan_poly([(-30.0, -25.0), (25.0, -25.0), (25.0, 35.0), (-30.0, 35.0)], -0.30, -0.12)
    road.finish("VE_Context_Road", mats["road"], g)
    # Neighbouring ground-floor unit (fig + sparrow) under the Oldham party bay.
    single_box("VE_Context_NeighbourGroundStub", OLDHAM, OLDHAM_SHOP_LEN, OLDHAM_UPPER_LEN, 0.0, C + DALE_LEN, 0.0, GLAZING_TOP, mats["context"], g)
    single_box("VE_Context_ScaleFigure_1p75m_Oldham", OLDHAM, 1.40, 1.85, -1.64, -1.36, 0.0, 1.75, mats["figure"], g)
    single_box("VE_Context_ScaleFigure_1p75m_Dale", DALE, 3.20, 3.65, -2.14, -1.86, 0.0, 1.75, mats["figure"], g)


def build_blockout():
    clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"

    master = make_collection("VINYL_EXCHANGE_MASTER")
    groups = {
        "shell": make_collection("VE_BuildingShell", master),
        "upper": make_collection("VE_UpperFacade", master),
        "ornament": make_collection("VE_Ornament", master),
        "windows": make_collection("VE_Windows", master),
        "ground": make_collection("VE_GroundFloor", master),
        "fascia": make_collection("VE_Fascia", master),
    }
    groups["oldham"] = make_collection("VE_OldhamStreetFront", groups["ground"])
    groups["dale"] = make_collection("VE_DaleStreetFront", groups["ground"])
    groups["corner"] = make_collection("VE_Corner", master)
    for key, name in (
        ("vents", "VE_Vents"),
        ("shutters", "VE_Shutters"),
        ("grilles", "VE_Grilles"),
        ("signage", "VE_Signage"),
        ("glass", "VE_Glass"),
        ("interior", "VE_InteriorShell"),
        ("plaques", "VE_StreetPlaques"),
        ("anchors", "VE_InteractionAnchors"),
    ):
        groups[key] = make_collection(name, master)
    groups["context"] = make_collection("VE_BlockoutContext")
    groups["cameras"] = make_collection("VE_BlockoutCameras")
    groups["lights"] = make_collection("VE_BlockoutLights")

    mats = {
        "stone": make_material("MAT_VE_UpperStone_PLACEHOLDER", (0.78, 0.72, 0.62), 0.90),
        "frames": make_material("MAT_VE_WindowFrames_PLACEHOLDER", (0.04, 0.07, 0.16), 0.55),
        "fascia": make_material("MAT_VE_GreyFascia_PLACEHOLDER", (0.40, 0.41, 0.42), 0.55, 0.15),
        "metal": make_material("MAT_VE_Metal_PLACEHOLDER", (0.50, 0.51, 0.52), 0.45, 0.50),
        "glass": make_material("MAT_VE_Glass_PLACEHOLDER", (0.08, 0.11, 0.13), 0.10, 0.0, alpha=0.45),
        "logo": make_material("MAT_VE_RedLogo_PLACEHOLDER", (0.55, 0.03, 0.04), 0.45),
        "plaque": make_material("MAT_VE_Plaque_PLACEHOLDER", (0.86, 0.88, 0.92), 0.30),
        "tagline": make_material("MAT_VE_TaglineStrip_PLACEHOLDER", (0.18, 0.18, 0.18), 0.60),
        "black": make_material("MAT_VE_BlackSign_PLACEHOLDER", (0.02, 0.02, 0.02), 0.40),
        "green": make_material("MAT_VE_GreenPanel_PLACEHOLDER", (0.34, 0.43, 0.37), 0.60),
        "tile": make_material("MAT_VE_WhiteTile_PLACEHOLDER", (0.82, 0.82, 0.80), 0.40),
        "vent": make_material("MAT_VE_VentRecess_PLACEHOLDER", (0.10, 0.10, 0.11), 0.70, 0.30),
        "display": make_material("MAT_VE_DisplaySurface_PLACEHOLDER", (0.55, 0.52, 0.46), 0.90),
        "interior": make_material("MAT_VE_Interior_PLACEHOLDER", (0.30, 0.27, 0.23), 0.95),
        "pavement": make_material("MAT_VE_ContextPavement_PLACEHOLDER", (0.24, 0.23, 0.22), 1.0),
        "road": make_material("MAT_VE_ContextRoad_PLACEHOLDER", (0.07, 0.07, 0.08), 1.0),
        "context": make_material("MAT_VE_ContextNeighbour_PLACEHOLDER", (0.16, 0.15, 0.14), 1.0),
        "figure": make_material("MAT_VE_ScaleFigure_PLACEHOLDER", (0.85, 0.40, 0.08), 0.80),
    }

    build_shells(mats, groups)
    build_upper_facade(mats, groups)
    build_oldham_front(mats, groups)
    build_corner(mats, groups)
    build_dale_front(mats, groups)
    build_signage(mats, groups)
    build_context(mats, groups)

    corner_mid = Vector((-C / 2, C / 2, 0.0))
    views = [
        (camera("CAMERA_A_OldhamStraightOn", (-C - OLDHAM_UPPER_LEN / 2, -17.0, 1.7), (-C - OLDHAM_UPPER_LEN / 2, 0.0, 1.7), 35, groups["cameras"], 0.32),
         "01-view-a-oldham-street-straight-on.png", (1200, 1500)),
        (camera("CAMERA_B_ThreeQuarterCorner", (10.75, -10.75, 1.6), (corner_mid.x, corner_mid.y, 1.6), 24, groups["cameras"], 0.18),
         "02-view-b-three-quarter-corner.png", (1500, 1000)),
        (camera("CAMERA_C_DaleStraightOn", (17.0, C + DALE_LEN / 2, 1.7), (0.0, C + DALE_LEN / 2, 1.7), 28, groups["cameras"], 0.256),
         "03-view-c-dale-street-straight-on.png", (1600, 1200)),
        (camera("CAMERA_D_LowAngleUpperFacade", (2.8, -2.2, 1.6), (-0.8, 1.6, 8.5), 20, groups["cameras"]),
         "04-view-d-low-angle-upper-facade.png", (1200, 1500)),
        (camera("CAMERA_E_CornerTransitionClose", (5.2, -4.6, 1.65), (-0.6, 0.9, 2.9), 26, groups["cameras"]),
         "05-view-e-corner-transition-close.png", (1500, 1100)),
    ]

    sun_data = bpy.data.lights.new("VE_Sun_Data", "SUN")
    sun_data.energy = 3.5
    sun_data.angle = math.radians(1.5)
    sun = bpy.data.objects.new("VE_Sun", sun_data)
    groups["lights"].objects.link(sun)
    sun.rotation_euler = Vector((-0.50, 0.75, -0.60)).to_track_quat("-Z", "Y").to_euler()

    world = scene.world or bpy.data.worlds.new("VE_BlockoutWorld")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.62, 0.68, 0.78, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.55

    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 48
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.0
    scene.camera = views[0][0]

    note = bpy.data.texts.new("VE_BLOCKOUT_NOTES")
    note.write(
        "FIRST PASS / REVIEW HOLD (brief section 45)\n"
        "Geometry-only blockout of Vinyl Exchange, Oldham Street / Dale Street,\n"
        "inferred from people, doors, pier rhythm and fascia proportions -- not surveyed.\n"
        "Plan: Oldham building line Y=0 faces -Y; Dale building line X=0 faces +X;\n"
        f"45-degree chamfer {CHAMFER_LEN} m. Bays {BAY} m. Fascia top {FASCIA_TOP} m.\n"
        "INFERRED: storeys 2-3, cornice and parapet (no reference shows the roof);\n"
        "the 90-degree street angle; building depth behind both frontages.\n"
        "Logo text uses Arial Narrow Bold as a placement proxy only.\n"
        "Deferred to second pass: colonnettes, carved capitals, moulded arches,\n"
        "relief bands, louvres, ribs, accordion lattice, cables, detailed frames.\n"
    )
    return views


def report():
    names = [obj.name for obj in bpy.data.objects]
    duplicates = [name for name in names if "." in name]
    master = bpy.data.collections["VINYL_EXCHANGE_MASTER"]
    meshes = [obj for obj in master.all_objects if obj.type == "MESH"]
    triangles = 0
    for obj in meshes:
        obj.data.calc_loop_triangles()
        triangles += len(obj.data.loop_triangles)
    xs = [(obj.matrix_world @ Vector(corner)).x for obj in meshes for corner in obj.bound_box]
    ys = [(obj.matrix_world @ Vector(corner)).y for obj in meshes for corner in obj.bound_box]
    zs = [(obj.matrix_world @ Vector(corner)).z for obj in meshes for corner in obj.bound_box]
    print(f"VE blockout: {len(meshes)} mesh objects, {triangles} triangles")
    print(f"VE bounds X {min(xs):.2f}..{max(xs):.2f}  Y {min(ys):.2f}..{max(ys):.2f}  Z {min(zs):.2f}..{max(zs):.2f}")
    print(f"VE duplicate-suffixed names: {duplicates or 'none'}")
    for required in ("VE_Plaque_OldhamStreet", "VE_Plaque_DaleStreet", "VE_MainDoor_LeafLeft", "VE_EntranceAnchor", "VE_InteriorSpawnAnchor", "VE_CornerSecurityGate"):
        print(f"VE required {required}: {'ok' if required in bpy.data.objects else 'MISSING'}")


def render_reviews(views):
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for camera_obj, filename, (res_x, res_y) in views:
        scene.camera = camera_obj
        scene.render.resolution_x = res_x
        scene.render.resolution_y = res_y
        scene.render.filepath = str(RENDER_DIR / filename)
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    views = build_blockout()
    report()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    render_reviews(views)
    bpy.context.scene.camera = views[0][0]
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    print(f"Saved {BLEND_PATH}")
    print(f"Rendered review images to {RENDER_DIR}")
