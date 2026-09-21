"""Create the ABC Building (Clints + Side Street) review blockout.

Implements only the first review gate (§47) of
references/architecture/buildings/clints/12_ABC_Building_Clints_Side_Street.txt:
tower mass and window grid, glazed core, podium, long retail canopy, ground
columns, the Clints hero storefront (real hinged door + interior-ready shell),
the Side Street corner frontage, the other retail bays, the Lower Byrom Street
side elevation and seven clay review renders. Geometry only: no textures,
logos, stock, foliage, final lighting or GLB export until the massing is
approved.

Run headless:
  /Applications/Blender.app/Contents/MacOS/Blender --background \
    --python blender/scripts/createABCBuildingBlockout.py

Frame of reference (1 unit = 1 m, Z up). Origin = ground-level corner of
Quay Street and Lower Byrom Street. The Quay Street elevation faces -Y and
runs along -X from the corner; the Lower Byrom Street elevation faces +X.
Viewed from Quay Street, the corner and tower are at the right-hand end.
"""

from math import radians
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
BLEND_PATH = ROOT / "blender" / "source" / "abc_building_blockout.blend"
RENDER_DIR = ROOT / "renders" / "abc-building-blockout"

# --- Inferred dimensions (photographic estimates, not survey data) ---------
BAY = 7.5                 # structural bay along Quay Street (column centres)
CORNER_X = -4.9           # west edge of the blank corner wall on Quay Street
COLUMN_W = 0.6
SHOPFRONT_Y = 0.32        # storefront glass line, just behind column faces
CANOPY_UNDERSIDE = 3.55
CANOPY_TOP = 4.95
CANOPY_DEPTH = 3.2
FIRST_FLOOR_WIN = (5.25, 8.85)
PODIUM_TOP = 9.6
PODIUM_DEPTH = 21.95
FLOOR_H = 3.35
TOWER_BAY_W = 1.95
TOWER_FLOORS = 14
TOWER_TOP = PODIUM_TOP + TOWER_FLOORS * FLOOR_H      # 56.5 m
TOWER_X0 = -26.4          # east end of tower (blank side wall)
CORE_X = (-26.4, -22.45)  # glazed vertical core at the tower's east end
GRID_PROUD = 0.55         # tower frame projects this far from the wall plane
LB_GRID_START = PODIUM_TOP + FLOOR_H                  # Lower Byrom grid begins above the glass box
LB_BLANK_Y = 4.4          # blank white corner return on Lower Byrom Street
REAR_WING = (-18.0, 46.0, PODIUM_TOP + 5 * FLOOR_H)  # x extent, y extent, height

# Quay Street bays, east to west ending at the corner wall.
BAYS = [
    ("Bay06_ABC_East", -49.9, -42.4),
    ("Bay05_Dome", -42.4, -34.9),
    ("Bay04_Tartuffe_SideStreetQuay", -34.9, -27.4),
    ("Bay03_CLINTS", -27.4, -19.9),
    ("Bay02_ABC", -19.9, -12.4),
    ("Bay01_ABC_Corner", -12.4, CORNER_X),
]
END_BLOCK = (-61.9, -49.9)  # Every Man / Smolensky block with the ABC blade sign
CANOPY_X = (-49.9, CORNER_X)

# Clints bay (column faces at -27.1 and -20.2 → 6.9 m clear).
CL_X = (-27.1, -20.2)
CL_LEFT_GLASS = (-27.1, -24.75)
CL_DOORS = (-24.75, -22.55)
CL_FIXED_LEAF = (-24.75, -23.65)
CL_DOOR_LEAF = (-23.65, -22.55)       # hinged on its right-hand (west) jamb
CL_RIGHT_GLASS = (-22.55, -20.2)
CL_HEAD = 3.42
CL_DOOR_TOP = 3.02
CL_DEPTH = 14.3


# --- Scene / collection utilities ------------------------------------------

def clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                       bpy.data.cameras, bpy.data.lights, bpy.data.texts):
        for block in list(datablocks):
            datablocks.remove(block)
    for col in list(bpy.data.collections):
        if col.name != "Collection":
            bpy.data.collections.remove(col)
    master = bpy.data.collections.get("Collection")
    if master is None:
        master = bpy.data.collections.new("Collection")
        bpy.context.scene.collection.children.link(master)
    master.name = "ABC_BUILDING_MASTER"
    return master


def child_collection(name, parent):
    col = bpy.data.collections.new(name)
    parent.children.link(col)
    return col


def material(name, colour, roughness=0.8, metallic=0.0, alpha=1.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*colour, alpha)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*colour, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        for attr, value in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
            try:
                setattr(mat, attr, value)
            except (AttributeError, TypeError):
                pass
    return mat


def create_materials():
    # Region identifiers for review only - deliberately restrained clay values.
    return {
        "concrete": material("MAT_ABC_Concrete_PLACEHOLDER", (0.50, 0.50, 0.48)),
        "white": material("MAT_ABC_WhiteFacade_PLACEHOLDER", (0.74, 0.74, 0.71)),
        "metal": material("MAT_ABC_DarkMetal_PLACEHOLDER", (0.05, 0.05, 0.055), 0.4, 0.5),
        "glass": material("MAT_ABC_Glass_PLACEHOLDER", (0.10, 0.14, 0.17), 0.12, 0.0, 0.35),
        "canopy": material("MAT_ABC_Canopy_PLACEHOLDER", (0.86, 0.84, 0.78), 0.5),
        "clints": material("MAT_CLINTS_PLACEHOLDER", (0.55, 0.46, 0.35)),
        "sidestreet": material("MAT_SIDE_STREET_PLACEHOLDER", (0.40, 0.44, 0.38)),
        "interior": material("MAT_ABC_InteriorDark_PLACEHOLDER", (0.035, 0.036, 0.038)),
        "brick": material("MAT_ABC_EndBlock_PLACEHOLDER", (0.36, 0.28, 0.24)),
        "planter": material("MAT_ABC_Planter_PLACEHOLDER", (0.06, 0.06, 0.06)),
        "letter": material("MAT_ABC_SignLetter_PLACEHOLDER", (0.03, 0.03, 0.03)),
        "ground": material("MAT_ABC_ReviewGround_NONEXPORT", (0.20, 0.20, 0.20)),
    }


# --- Geometry builders (data API, so hundreds of objects stay fast) --------

BOX_FACES = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]


def _box_verts(x0, x1, y0, y1, z0, z1, origin):
    ox, oy, oz = origin
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    z0, z1 = sorted((z0, z1))
    return [(x - ox, y - oy, z - oz) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]


def multi_box_mesh(name, boxes, mats, origin=(0.0, 0.0, 0.0)):
    """boxes: [(x0, x1, y0, y1, z0, z1, material_index)] in world/local coords."""
    verts, faces, face_mats = [], [], []
    for x0, x1, y0, y1, z0, z1, mi in boxes:
        base = len(verts)
        verts += _box_verts(x0, x1, y0, y1, z0, z1, origin)
        faces += [tuple(base + i for i in f) for f in BOX_FACES]
        face_mats += [mi] * 6
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(verts, [], faces)
    for mat in mats:
        mesh.materials.append(mat)
    for poly, mi in zip(mesh.polygons, face_mats):
        poly.material_index = mi
    mesh.update()
    return mesh


def obj_from_mesh(name, mesh, col, location=(0.0, 0.0, 0.0), rot_z=0.0):
    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    obj.rotation_euler = (0.0, 0.0, rot_z)
    col.objects.link(obj)
    return obj


def box(name, x0, x1, y0, y1, z0, z1, mat, col, origin=None):
    if origin is None:
        origin = ((x0 + x1) / 2, (y0 + y1) / 2, min(z0, z1))
    mesh = multi_box_mesh(name, [(x0, x1, y0, y1, z0, z1, 0)], [mat], origin)
    return obj_from_mesh(name, mesh, col, origin)


def boxes(name, parts, mat, col, origin=None):
    """One object from many same-material boxes [(x0,x1,y0,y1,z0,z1)]."""
    if origin is None:
        origin = (sum(p[0] + p[1] for p in parts) / (2 * len(parts)),
                  sum(p[2] + p[3] for p in parts) / (2 * len(parts)),
                  min(min(p[4], p[5]) for p in parts))
    mesh = multi_box_mesh(name, [(*p, 0) for p in parts], [mat], origin)
    return obj_from_mesh(name, mesh, col, origin)


def xy(axis, u0, u1, p0, p1):
    """Map facade (u along wall, p through wall) to x/y ranges.
    axis 'y': wall faces ±Y, u = x.  axis 'x': wall faces ±X, u = y."""
    return (u0, u1, p0, p1) if axis == "y" else (p0, p1, u0, u1)


def wall_with_openings(name, axis, p0, p1, u0, u1, z0, z1, openings, mat, col):
    """Solid wall slab minus rectangular openings [(u0, u1, z0, z1)]."""
    zs = sorted({z0, z1, *[o[2] for o in openings], *[o[3] for o in openings]})
    zs = [z for z in zs if z0 <= z <= z1]
    solids = []
    for za, zb in zip(zs, zs[1:]):
        blocked = sorted((o[0], o[1]) for o in openings if o[2] <= za and o[3] >= zb)
        cursor = u0
        for bu0, bu1 in blocked + [(u1, u1)]:
            if bu0 - cursor > 1e-4:
                solids.append((*xy(axis, cursor, bu0, p0, p1), za, zb))
            cursor = max(cursor, bu1)
    return boxes(name, solids, mat, col)


def frame_rect(name, axis, p0, p1, u0, u1, z0, z1, mat, col, bar=0.08,
               mullions=(), transoms=(), mullion_w=0.07):
    """Perimeter frame + mullions (u positions) + transoms (z positions)."""
    parts = [
        (u0, u0 + bar, z0, z1), (u1 - bar, u1, z0, z1),
        (u0 + bar, u1 - bar, z0, z0 + bar), (u0 + bar, u1 - bar, z1 - bar, z1),
    ]
    parts += [(m - mullion_w / 2, m + mullion_w / 2, z0 + bar, z1 - bar) for m in mullions]
    parts += [(u0 + bar, u1 - bar, t - mullion_w / 2, t + mullion_w / 2) for t in transoms]
    return boxes(name, [(*xy(axis, a, b, p0, p1), za, zb) for a, b, za, zb in parts], mat, col)


def glass(name, axis, plane, u0, u1, z0, z1, mat, col, thickness=0.02):
    x0, x1, y0, y1 = xy(axis, u0, u1, plane - thickness / 2, plane + thickness / 2)
    return box(name, x0, x1, y0, y1, z0, z1, mat, col)


def empty(name, location, col, display="PLAIN_AXES", size=0.4):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = display
    obj.empty_display_size = size
    obj.location = location
    col.objects.link(obj)
    return obj


def text_mesh(name, body, size, depth, location, rotation, mat, col):
    """Low-depth placeholder lettering, converted to a mesh (no font datablock)."""
    curve = bpy.data.curves.new(f"{name}_Curve", "FONT")
    curve.body = body
    curve.size = size
    curve.extrude = depth / 2
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    tmp = bpy.data.objects.new(f"{name}_TMP", curve)
    bpy.context.scene.collection.objects.link(tmp)
    bpy.context.view_layer.update()
    mesh = bpy.data.meshes.new_from_object(tmp.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(tmp, do_unlink=True)
    bpy.data.curves.remove(curve)
    mesh.name = f"{name}_Mesh"
    mesh.materials.clear()
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    obj.rotation_euler = rotation
    col.objects.link(obj)
    return obj


FACING_NEG_Y = (radians(90), 0.0, 0.0)
FACING_POS_X = (radians(90), 0.0, radians(90))
FACING_NEG_X = (radians(90), 0.0, radians(-90))


def parent_keep(child, parent):
    bpy.context.view_layer.update()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()


# --- Tower -----------------------------------------------------------------

def tower_modules(mats, glass_col):
    """ABC_TowerBay_Module (frame, band, dark backing) + ABC_TowerWindow_Module
    (glass), authored for a -Y-facing wall with origin at bay bottom-centre."""
    w, h, t, d = TOWER_BAY_W, FLOOR_H, 0.16, GRID_PROUD
    il, ir = -w / 2 + t, w / 2 - t
    bay = multi_box_mesh("ABC_TowerBay_Module", [
        (-w / 2, il, -d, 0, 0, h, 0),
        (ir, w / 2, -d, 0, 0, h, 0),
        (il, ir, -d, 0, 0, 0.24, 0),
        (il, ir, -d, 0, h - 0.2, h, 0),
        (il, ir, -0.17, -0.11, 0.98, 1.05, 1),   # horizontal band within the window
        (il, ir, -0.03, 0, 0.24, h - 0.2, 2),     # dark backing so windows read as voids
    ], [mats["white"], mats["metal"], mats["interior"]])
    window = multi_box_mesh("ABC_TowerWindow_Module",
                            [(il, ir, -0.11, -0.09, 0.24, h - 0.2, 0)], [mats["glass"]])
    return bay, window


def place_tower_bay(label, bay_mesh, win_mesh, location, rot_z, frame_col, glass_col):
    obj_from_mesh(f"ABC_TowerBay_{label}", bay_mesh, frame_col, location, rot_z)
    obj_from_mesh(f"ABC_TowerWindow_{label}", win_mesh, glass_col, location, rot_z)


def build_tower(mats, cols):
    tower, glass_col = cols["tower"], cols["tower_glass"]
    bay_mesh, win_mesh = tower_modules(mats, glass_col)
    frames = child_collection("ABC_TowerGrid_Instances", tower)

    box("ABC_Tower_Mass", TOWER_X0, 0.0, 0.0, PODIUM_DEPTH, PODIUM_TOP, TOWER_TOP,
        mats["white"], tower)

    # Quay Street elevation: blank corner wall, 9-bay grid, glazed core.
    grid_x0 = CORNER_X
    for floor in range(TOWER_FLOORS):
        z = PODIUM_TOP + floor * FLOOR_H
        for i in range(9):
            x = grid_x0 - TOWER_BAY_W * (i + 0.5)
            place_tower_bay(f"Quay_F{floor + 1:02d}_B{i + 1:02d}", bay_mesh, win_mesh,
                            (x, 0.0, z), 0.0, frames, glass_col)
    box("ABC_Tower_CornerBlankWall_Quay", CORNER_X, 0.0, -GRID_PROUD, 0.0, 0.0, TOWER_TOP,
        mats["white"], tower)

    # Lower Byrom elevation: blank corner return, then grid above the glass box.
    lb_floors = int(round((TOWER_TOP - LB_GRID_START) / FLOOR_H))
    for floor in range(lb_floors):
        z = LB_GRID_START + floor * FLOOR_H
        for i in range(9):
            y = LB_BLANK_Y + TOWER_BAY_W * (i + 0.5)
            place_tower_bay(f"LowerByrom_F{floor + 2:02d}_B{i + 1:02d}", bay_mesh, win_mesh,
                            (0.0, y, z), radians(90), frames, glass_col)
    box("ABC_Tower_CornerBlankWall_LowerByrom", 0.0, GRID_PROUD, -GRID_PROUD, LB_BLANK_Y,
        LB_GRID_START, TOWER_TOP, mats["white"], tower)

    # Rear (south) elevation: simplified, above the rear wing where they meet.
    count = int(abs(TOWER_X0) / TOWER_BAY_W)
    margin = (abs(TOWER_X0) - count * TOWER_BAY_W) / 2
    for floor in range(TOWER_FLOORS):
        z = PODIUM_TOP + floor * FLOOR_H
        for i in range(count):
            x = -margin - TOWER_BAY_W * (i + 0.5)
            if z < REAR_WING[2] and x > REAR_WING[0] - TOWER_BAY_W / 2:
                continue
            place_tower_bay(f"Rear_F{floor + 1:02d}_B{i + 1:02d}", bay_mesh, win_mesh,
                            (x, PODIUM_DEPTH, z), radians(180), frames, glass_col)
    # East elevation is the large uninterrupted side wall (the tower mass face).

    # Roof slab / projecting cornice over the grid.
    box("ABC_Tower_RoofCornice", TOWER_X0 - 0.35, GRID_PROUD + 0.25, -GRID_PROUD - 0.4,
        PODIUM_DEPTH + GRID_PROUD + 0.25, TOWER_TOP, TOWER_TOP + 0.8, mats["white"], tower)
    box("ABC_Tower_RoofPlant_Upstand", -20.0, -6.0, 6.0, 16.0, TOWER_TOP + 0.8, TOWER_TOP + 3.0,
        mats["white"], tower)

    # Vertical glazed core: fins, curtain wall, mullions, floor divisions, top.
    cx0, cx1 = CORE_X
    front = -0.95
    core_top = TOWER_TOP + 3.6
    boxes("ABC_TowerCore_Frame", [
        (cx0, cx0 + 0.4, front, 0.0, PODIUM_TOP, core_top),
        (cx1 - 0.4, cx1, front, 0.0, PODIUM_TOP, core_top),
        (cx0, cx1, front - 0.1, 0.0, core_top - 0.6, core_top),
    ], mats["white"], tower)
    glass("ABC_TowerCore_CurtainGlass", "y", front + 0.2, cx0 + 0.4, cx1 - 0.4,
          PODIUM_TOP, core_top - 0.6, mats["glass"], glass_col)
    boxes("ABC_TowerCore_Backing", [(cx0 + 0.4, cx1 - 0.4, -0.2, 0.0, PODIUM_TOP, core_top - 0.6)],
          mats["interior"], tower)
    span = (cx1 - 0.4) - (cx0 + 0.4)
    mullions = [(cx0 + 0.4 + span * k / 3 - 0.04, cx0 + 0.4 + span * k / 3 + 0.04,
                 front + 0.05, front + 0.18, PODIUM_TOP, core_top - 0.6) for k in (1, 2)]
    floors = [(cx0 + 0.4, cx1 - 0.4, front + 0.05, front + 0.18, z - 0.06, z + 0.06)
              for z in [PODIUM_TOP + k * FLOOR_H for k in range(1, TOWER_FLOORS + 1)]]
    boxes("ABC_TowerCore_Mullions", mullions + floors, mats["metal"], tower)


# --- Podium, canopy, bays --------------------------------------------------

def column_positions():
    return [xb for _n, _xa, xb in BAYS[:-1]] + [BAYS[0][1]]


def build_podium(mats, cols):
    podium, retail, glass_col = cols["podium"], cols["retail"], cols["podium_glass"]
    x_east, x_west = CANOPY_X

    # Ground-floor slab zone (shop ceilings at 3.42), rear service mass, upper floor.
    box("ABC_Podium_FirstFloorSlab", x_east, x_west, SHOPFRONT_Y, PODIUM_DEPTH, CL_HEAD, CANOPY_TOP,
        mats["concrete"], podium)
    box("ABC_Podium_RearServiceMass", x_east, x_west, CL_DEPTH + 0.2, PODIUM_DEPTH, 0.0, CL_HEAD,
        mats["concrete"], podium)
    box("ABC_Podium_UpperFloorMass", x_east, x_west, 0.75, PODIUM_DEPTH, CANOPY_TOP, PODIUM_TOP,
        mats["interior"], podium)
    box("ABC_Podium_Roof", x_east, TOWER_X0, 0.0, PODIUM_DEPTH, PODIUM_TOP, PODIUM_TOP + 0.15,
        mats["concrete"], podium)
    boxes("ABC_Podium_Parapet", [
        (x_east, TOWER_X0, -0.12, 0.3, PODIUM_TOP, PODIUM_TOP + 0.7),
        (x_east - 0.3, x_east, 0.0, PODIUM_DEPTH, PODIUM_TOP, PODIUM_TOP + 0.7),
    ], mats["white"], podium)

    # Structural columns at pedestrian level + first-floor piers above the canopy.
    col_x = [xa for _n, xa, _xb in BAYS] + [CORNER_X]
    for i, x in enumerate(col_x):
        x0 = x - COLUMN_W / 2 if x != CORNER_X else x - COLUMN_W / 2
        x1 = x + COLUMN_W / 2 if x != CORNER_X else x
        box(f"ABC_Column_{i + 1:02d}", x0, x1, -0.1, 0.5, 0.0, CANOPY_UNDERSIDE, mats["white"], retail)
        box(f"ABC_FirstFloorPier_{i + 1:02d}", x0, x1, 0.0, 0.75, FIRST_FLOOR_WIN[0], FIRST_FLOOR_WIN[1],
            mats["white"], podium)
    box("ABC_Podium_Spandrel", x_east, x_west, 0.0, 0.75, CL_HEAD, FIRST_FLOOR_WIN[0],
        mats["white"], podium)
    box("ABC_Podium_HeadBand", x_east, x_west, -0.12, 0.75, FIRST_FLOOR_WIN[1], PODIUM_TOP,
        mats["white"], podium)

    # Large first-floor glazed bays: recessed frame, 3 lights + upper transom row.
    for name, xa, xb in BAYS:
        u0 = xa + COLUMN_W / 2
        u1 = xb - (COLUMN_W / 2 if xb != CORNER_X else 0.0)
        z0, z1 = FIRST_FLOOR_WIN
        third = (u1 - u0) / 3
        frame_rect(f"ABC_{name}_UpperWindow_Frame", "y", 0.40, 0.52, u0, u1, z0, z1, mats["metal"],
                   podium, bar=0.12, mullions=(u0 + third, u0 + 2 * third), transoms=(z1 - 0.8,),
                   mullion_w=0.09)
        glass(f"ABC_PodiumGlass_{name}_Upper", "y", 0.47, u0, u1, z0, z1, mats["glass"], glass_col)

    # Partitions between shop units (column lines), dark interior material.
    for i, x in enumerate([xa for _n, xa, _xb in BAYS[1:]]):
        box(f"ABC_ShopPartition_{i + 1:02d}", x - 0.1, x + 0.1, 0.5, CL_DEPTH + 0.2, 0.0, CL_HEAD,
            mats["interior"], podium)


def build_canopy(mats, cols):
    col = cols["canopy"]
    x0, x1 = CANOPY_X
    front = -CANOPY_DEPTH
    u, t = CANOPY_UNDERSIDE, CANOPY_TOP
    box("ABC_Canopy_Deck", x0, x1, front, 0.0, t - 0.28, t - 0.08, mats["concrete"], col)
    boxes("ABC_Canopy_Frame", [
        (x0, x1, front - 0.06, front + 0.08, t - 0.32, t),             # dark upper fascia
        (x0, x1, front - 0.06, front + 0.14, u - 0.06, u + 0.06),      # dark lower lip
        (x0 - 0.06, x0 + 0.06, front - 0.06, 0.0, u - 0.06, t),        # east end cap
        (x1 - 0.06, x1 + 0.06, front - 0.06, 0.0, u - 0.06, t),        # west end cap
    ], mats["metal"], col)
    box("ABC_Canopy_SignBand", x0 + 0.06, x1 - 0.06, front - 0.04, front + 0.1, u + 0.06, t - 0.32,
        mats["canopy"], col)
    # Thin horizontal marquee lines + vertical dividers at column lines.
    lines = [(x0, x1, front - 0.075, front - 0.04, z - 0.018, z + 0.018)
             for z in (u + 0.42, u + 0.72, u + 1.02)]
    lines += [(x - 0.02, x + 0.02, front - 0.075, front - 0.04, u + 0.06, t - 0.32)
              for x in [xa for _n, xa, _xb in BAYS[1:]]]
    boxes("ABC_Canopy_SignLines", lines, mats["metal"], col)
    # Underside: a real grid of rectangular panels with thin dark framing.
    box("ABC_Canopy_Panels", x0, x1, front + 0.08, 0.0, u + 0.02, u + 0.05, mats["canopy"], col)
    rows = 4
    grid = [(x0, x1, front + (k * CANOPY_DEPTH / rows) - 0.025, front + (k * CANOPY_DEPTH / rows) + 0.025,
             u - 0.03, u + 0.02) for k in range(1, rows + 1)]
    n = int(round((x1 - x0) / 1.25))
    grid += [(x0 + k * (x1 - x0) / n - 0.025, x0 + k * (x1 - x0) / n + 0.025, front, 0.0,
              u - 0.03, u + 0.02) for k in range(1, n)]
    boxes("ABC_Canopy_UndersideGrid", grid, mats["metal"], col)


def shopfront(prefix, xa, xb, segments, mats, frame_col, glass_col, interior_col, depth=6.0):
    """Non-hero shopfront. segments: [(kind, width)] with kind glass|door|panel."""
    y0, y1 = SHOPFRONT_Y - 0.06, SHOPFRONT_Y + 0.06
    head = CL_HEAD
    bars = [(xa, xb, y0, y1, head - 0.14, head), (xa, xb, y0, y1, 0.0, 0.08)]
    cursor = xa
    for idx, (kind, width) in enumerate(segments):
        s0, s1 = cursor, cursor + width
        bars.append((s0, s0 + 0.07, y0, y1, 0.0, head))
        if kind == "glass":
            glass(f"{prefix}_Glass_{idx + 1}", "y", SHOPFRONT_Y, s0 + 0.07, s1, 0.08, head - 0.14,
                  mats["glass"], glass_col)
        elif kind == "door":
            door_top = 2.6
            bars.append((s0, s1, y0, y1, door_top, door_top + 0.08))
            frame_rect(f"{prefix}_Door_Placeholder", "y", SHOPFRONT_Y - 0.03, SHOPFRONT_Y + 0.03,
                       s0 + 0.09, s1 - 0.02, 0.02, door_top - 0.02, mats["metal"], frame_col, bar=0.09)
            glass(f"{prefix}_Glass_Door", "y", SHOPFRONT_Y, s0 + 0.18, s1 - 0.11, 0.11, door_top - 0.11,
                  mats["glass"], glass_col)
            glass(f"{prefix}_Glass_Transom", "y", SHOPFRONT_Y, s0 + 0.07, s1, door_top + 0.08, head - 0.14,
                  mats["glass"], glass_col)
        else:
            box(f"{prefix}_SolidPanel", s0 + 0.07, s1, y0 - 0.02, y1, 0.08, head - 0.14,
                mats["planter"], frame_col)
        cursor = s1
    bars.append((xb - 0.07, xb, y0, y1, 0.0, head))
    boxes(f"{prefix}_Frame", bars, mats["metal"], frame_col)
    # Simple interior darkness/depth.
    box(f"{prefix}_Interior_BackWall", xa, xb, depth, depth + 0.1, 0.0, head, mats["interior"], interior_col)
    box(f"{prefix}_Interior_Floor", xa, xb, SHOPFRONT_Y + 0.06, depth, 0.0, 0.02, mats["interior"], interior_col)


def build_other_bays(mats, cols):
    other, glass_col, interiors = cols["other"], cols["podium_glass"], cols["interiors"]
    layouts = {
        "Bay06_ABC_East": [("door", 1.3), ("glass", 2.8), ("glass", 2.8)],
        "Bay05_Dome": [("glass", 2.85), ("door", 1.2), ("glass", 2.85)],
        "Bay02_ABC": [("glass", 2.85), ("door", 1.2), ("glass", 2.85)],
        "Bay01_ABC_Corner": [("glass", 3.2), ("door", 1.2), ("glass", 2.8)],
    }
    for name, xa, xb in BAYS:
        u0 = xa + COLUMN_W / 2
        u1 = xb - (COLUMN_W / 2 if xb != CORNER_X else 0.0)
        if name in layouts:
            segs = layouts[name]
            scale = (u1 - u0) / sum(w for _k, w in segs)
            shopfront(f"ABC_{name}", u0, u1, [(k, w * scale) for k, w in segs], mats, other,
                      glass_col, interiors)
        elif name.startswith("Bay04"):
            # Night photo: Side Street's black Quay Street panel beside a glazed
            # door section, directly east of the Clints column. TARTUFFE above.
            segs = [("panel", 4.3), ("glass", 1.15), ("door", 1.45)]
            scale = (u1 - u0) / sum(w for _k, w in segs)
            shopfront("SS_QuayStreet", u0, u1, [(k, w * scale) for k, w in segs], mats,
                      cols["sidestreet"], cols["ss_glass"], interiors)


def build_end_block(mats, cols):
    col, glass_col = cols["podium"], cols["podium_glass"]
    x0, x1 = END_BLOCK
    box("ABC_EndBlock_Mass", x0, x1, 1.0, PODIUM_DEPTH, 0.0, PODIUM_TOP + 0.5, mats["brick"], col)
    boxes("ABC_EndBlock_Frame", [
        (x0, x0 + 0.5, -0.1, 1.0, 0.0, PODIUM_TOP + 0.5),
        (x1 - 0.3, x1, -0.1, 1.0, 0.0, PODIUM_TOP + 0.5),
        (x0, x1, -0.1, 1.0, 3.6, 4.3),                          # Smolensky sign band
        (x0, x1, -0.1, 1.0, PODIUM_TOP - 0.4, PODIUM_TOP + 0.5),
    ], mats["brick"], col)
    frame_rect("ABC_EndBlock_GroundFrame", "y", 0.5, 0.62, x0 + 0.5, x1 - 0.3, 0.0, 3.6, mats["metal"], col,
               mullions=[x0 + 0.5 + k * (x1 - x0 - 0.8) / 4 for k in (1, 2, 3)], transoms=(2.7,))
    glass("ABC_PodiumGlass_EndBlock_Ground", "y", 0.56, x0 + 0.5, x1 - 0.3, 0.0, 3.6, mats["glass"], glass_col)
    frame_rect("ABC_EndBlock_UpperFrame", "y", 0.5, 0.62, x0 + 0.5, x1 - 0.3, 4.3, PODIUM_TOP - 0.4,
               mats["metal"], col, mullions=[x0 + 0.5 + k * (x1 - x0 - 0.8) / 4 for k in (1, 2, 3)],
               transoms=(6.9,))
    glass("ABC_PodiumGlass_EndBlock_Upper", "y", 0.56, x0 + 0.5, x1 - 0.3, 4.3, PODIUM_TOP - 0.4,
          mats["glass"], glass_col)
    # ABC blade fin carrying the vertical podium letters (§31).
    box("ABC_PodiumLetters_BladeFin", x1 - 0.32, x1 - 0.02, -1.7, 0.2, 0.9, PODIUM_TOP - 0.2,
        mats["white"], col)


def build_rear_wing(mats, cols):
    col = cols["podium"]
    wx, wy, wz = REAR_WING
    box("ABC_RearWing_Mass", wx, 0.0, PODIUM_DEPTH, wy, 0.0, wz, mats["white"], col)
    box("ABC_RearWing_Parapet", wx, 0.3, PODIUM_DEPTH, wy + 0.3, wz, wz + 0.6, mats["white"], col)
    # Lower Byrom face: vertical fins + recessed horizontal window strips.
    fins = [(0.0, 0.35, y - 0.12, y + 0.12, 3.2, wz)
            for y in [PODIUM_DEPTH + k * TOWER_BAY_W for k in range(1, int((wy - PODIUM_DEPTH) / TOWER_BAY_W) + 1)]]
    boxes("ABC_RearWing_Fins", fins, mats["white"], col)
    for k in range(1, int(wz / FLOOR_H)):
        z = k * FLOOR_H
        glass(f"ABC_PodiumGlass_RearWing_F{k:02d}", "x", 0.02, PODIUM_DEPTH + 0.3, wy - 0.3,
              z + 0.9, z + 2.6, mats["glass"], cols["podium_glass"])
    # Service-level patterned grille (§33): low-poly repeated module instances.
    grille = multi_box_mesh("ABC_ServiceGrille_Module", [
        (0.0, 0.12, -0.9, 0.9, 0.0, 0.1, 0), (0.0, 0.12, -0.9, 0.9, 1.1, 1.2, 0),
        (0.0, 0.12, -0.9, -0.8, 0.0, 1.2, 0), (0.0, 0.12, 0.8, 0.9, 0.0, 1.2, 0),
        *[(0.02, 0.1, -0.8 + j * 0.2, -0.72 + j * 0.2, 0.1, 1.1, 0) for j in range(1, 8)],
        (-0.2, -0.15, -0.8, 0.8, 0.1, 1.1, 1),
    ], [mats["concrete"], mats["interior"]])
    box("ABC_RearWing_BaseBand", 0.0, 0.2, PODIUM_DEPTH, wy, 0.0, 3.2, mats["concrete"], col)
    for k in range(int((wy - PODIUM_DEPTH) / TOWER_BAY_W)):
        obj_from_mesh(f"ABC_ServiceGrille_{k + 1:02d}", grille, col,
                      (0.2, PODIUM_DEPTH + TOWER_BAY_W * (k + 0.5), 0.35))


# --- Lower Byrom Street elevation + Side Street -----------------------------

def build_lower_byrom_and_side_street(mats, cols):
    ss, ss_glass, tower = cols["sidestreet"], cols["ss_glass"], cols["tower"]
    wall_p = (0.0, GRID_PROUD)
    tall = (0.4, 4.0, 0.7, 5.6)
    door = (4.6, 6.0, 0.0, 3.2)
    windows = [(6.6 + i * 3.8, 6.6 + i * 3.8 + 3.3, 0.8, 4.4) for i in range(4)]
    vent = (4.6, 21.3, 5.75, 6.15)
    wall_with_openings("ABC_LowerByrom_BaseWall", "x", *wall_p, -GRID_PROUD, PODIUM_DEPTH, 0.0,
                       LB_GRID_START, [tall, door, *windows, vent], mats["white"], tower)
    box("ABC_LowerByrom_VentLouvre", 0.12, 0.3, vent[0], vent[1], vent[2], vent[3], mats["metal"], tower)
    box("ABC_CornerBase_Mass", CORNER_X, 0.0, 0.0, PODIUM_DEPTH, 6.0, PODIUM_TOP, mats["concrete"], tower)

    # Side Street: tall double-height window with clerestory transom.
    frame_rect("SS_Window_Frame", "x", 0.14, 0.26, tall[0], tall[1], tall[2], tall[3], mats["metal"], ss,
               bar=0.1, mullions=((tall[0] + tall[1]) / 2,), transoms=(4.75,))
    glass("SS_Glass_Main", "x", 0.2, tall[0], tall[1], tall[2], tall[3], mats["glass"], ss_glass)
    # Entrance: real usable doorway geometry.
    entrance = empty("SS_Entrance", (0.2, (door[0] + door[1]) / 2, 0.0), ss, "ARROWS", 0.5)
    frame_rect("SS_DoorFrame", "x", 0.14, 0.26, door[0], door[1], 0.0, door[3], mats["metal"], ss,
               bar=0.09, transoms=(2.7,))
    leaf = boxes("SS_Door", [
        (0.17, 0.23, door[0] + 0.09, door[0] + 0.19, 0.02, 2.66),
        (0.17, 0.23, door[1] - 0.19, door[1] - 0.09, 0.02, 2.66),
        (0.17, 0.23, door[0] + 0.19, door[1] - 0.19, 0.02, 0.2),
        (0.17, 0.23, door[0] + 0.19, door[1] - 0.19, 2.54, 2.66),
    ], mats["metal"], ss, origin=(0.2, door[0] + 0.09, 0.0))
    ss_door_glass = glass("SS_Glass_Door", "x", 0.2, door[0] + 0.19, door[1] - 0.19, 0.2, 2.54,
                          mats["glass"], ss_glass)
    glass("SS_Glass_Transom", "x", 0.2, door[0] + 0.09, door[1] - 0.09, 2.74, door[3] - 0.09,
          mats["glass"], ss_glass)
    parent_keep(leaf, entrance)
    parent_keep(ss_door_glass, leaf)
    for i, (u0, u1, z0, z1) in enumerate(windows):
        frame_rect(f"SS_RowWindow_{i + 1:02d}_Frame", "x", 0.14, 0.26, u0, u1, z0, z1, mats["metal"], ss,
                   mullions=((u0 + u1) / 2,))
        glass(f"SS_Glass_Row_{i + 1:02d}", "x", 0.2, u0, u1, z0, z1, mats["glass"], ss_glass)

    # Interior-ready shell: tall, shallow visible depth, no fit-out.
    shell = child_collection("SS_InteriorShell_TEMP", ss)
    box("SS_Interior_Floor", -4.6, 0.0, 0.0, PODIUM_DEPTH - 0.4, 0.0, 0.02, mats["sidestreet"], shell)
    box("SS_Interior_Ceiling", -4.6, 0.0, 0.0, PODIUM_DEPTH - 0.4, 5.9, 6.0, mats["sidestreet"], shell)
    box("SS_Interior_BackWall", -4.8, -4.6, 0.0, PODIUM_DEPTH - 0.4, 0.0, 5.9, mats["sidestreet"], shell)
    box("SS_Interior_EndWall", -4.6, 0.0, PODIUM_DEPTH - 0.6, PODIUM_DEPTH - 0.4, 0.0, 5.9,
        mats["sidestreet"], shell)

    # Projecting glazed volume on the Lower Byrom elevation (§34).
    gx0, gx1, gy0, gy1, gz0, gz1 = GRID_PROUD, 2.95, 5.5, PODIUM_DEPTH, 8.2, 12.2
    boxes("ABC_ProjectingGlassVolume_Frame", [
        (gx0, gx1, gy0, gy1, gz0, gz0 + 0.35),
        (gx0, gx1, gy0, gy1, gz1 - 0.35, gz1),
        (gx1 - 0.12, gx1, gy0, gy0 + 0.12, gz0, gz1),
        (gx1 - 0.12, gx1, gy1 - 0.12, gy1, gz0, gz1),
        *[(gx1 - 0.1, gx1, y - 0.05, y + 0.05, gz0, gz1)
          for y in [gy0 + k * (gy1 - gy0) / 3 for k in (1, 2)]],
    ], mats["white"], tower)
    glass("ABC_TowerGlass_ProjectingVolume_Front", "x", gx1 - 0.05, gy0, gy1, gz0 + 0.35, gz1 - 0.35,
          mats["glass"], cols["tower_glass"])
    for label, y in (("North", gy0 + 0.02), ("South", gy1 - 0.02)):
        glass(f"ABC_TowerGlass_ProjectingVolume_{label}Return", "y", y, gx0, gx1 - 0.1, gz0 + 0.35,
              gz1 - 0.35, mats["glass"], cols["tower_glass"])
    box("ABC_ProjectingGlassVolume_Interior", gx0, gx1 - 0.4, gy0 + 0.3, gy1 - 0.3, gz0 + 0.35, gz0 + 0.4,
        mats["interior"], tower)


# --- Clints hero storefront ------------------------------------------------

def build_clints(mats, cols):
    cl, cl_glass = cols["clints"], cols["cl_glass"]
    y = SHOPFRONT_Y
    y0, y1 = y - 0.07, y + 0.07
    lx0, lx1 = CL_LEFT_GLASS
    rx0, rx1 = CL_RIGHT_GLASS
    dx0, dx1 = CL_DOORS

    # Storefront frame: sill, head, jambs, door mullions, low rails, door transom.
    boxes("CL_Storefront_Frame", [
        (CL_X[0], CL_X[1], y0, y1, 0.0, 0.07),
        (CL_X[0], CL_X[1], y0, y1, CL_HEAD - 0.14, CL_HEAD),
        (CL_X[0], CL_X[0] + 0.09, y0, y1, 0.0, CL_HEAD),
        (CL_X[1] - 0.09, CL_X[1], y0, y1, 0.0, CL_HEAD),
        (dx0 - 0.05, dx0 + 0.05, y0, y1, 0.0, CL_HEAD),
        (dx1 - 0.05, dx1 + 0.05, y0, y1, 0.0, CL_HEAD),
        (lx0 + 0.09, dx0 - 0.05, y0, y1, 0.82, 0.9),     # low rail seen in daytime photo
        (dx1 + 0.05, rx1 - 0.09, y0, y1, 0.82, 0.9),
    ], mats["metal"], cl)
    glass("CL_Glass_Left", "y", y, lx0 + 0.09, dx0 - 0.05, 0.07, CL_HEAD - 0.14, mats["glass"], cl_glass)
    glass("CL_Glass_Right", "y", y, dx1 + 0.05, rx1 - 0.09, 0.07, CL_HEAD - 0.14, mats["glass"], cl_glass)

    # Entrance hierarchy: CL_Entrance > CL_DoorFrame, fixed leaf, CL_Door (hinged).
    entrance = empty("CL_Entrance", ((dx0 + dx1) / 2, y, 0.0), cl, "ARROWS", 0.6)
    frame = boxes("CL_DoorFrame", [
        (dx0 + 0.05, dx1 - 0.05, y0, y1, CL_DOOR_TOP, CL_DOOR_TOP + 0.08),   # door transom bar
        (CL_FIXED_LEAF[1] - 0.03, CL_FIXED_LEAF[1] + 0.03, y0, y1, 0.07, CL_DOOR_TOP),
    ], mats["metal"], cl)
    fixed = frame_rect("CL_DoorFixedLeaf", "y", y - 0.03, y + 0.03, CL_FIXED_LEAF[0] + 0.05,
                       CL_FIXED_LEAF[1] - 0.03, 0.07, CL_DOOR_TOP, mats["metal"], cl, bar=0.1)
    fixed_glass = glass("CL_Glass_DoorFixed", "y", y, CL_FIXED_LEAF[0] + 0.15, CL_FIXED_LEAF[1] - 0.13,
                        0.25, CL_DOOR_TOP - 0.1, mats["glass"], cl_glass)
    glass("CL_Glass_Transom", "y", y, dx0 + 0.05, dx1 - 0.05, CL_DOOR_TOP + 0.08, CL_HEAD - 0.14,
          mats["glass"], cl_glass)

    hinge = (CL_DOOR_LEAF[1] - 0.05, y, 0.0)
    lx, rx = CL_DOOR_LEAF[0] + 0.03, CL_DOOR_LEAF[1] - 0.05
    door = boxes("CL_Door", [
        (lx, lx + 0.1, y - 0.03, y + 0.03, 0.07, CL_DOOR_TOP - 0.01),
        (rx - 0.1, rx, y - 0.03, y + 0.03, 0.07, CL_DOOR_TOP - 0.01),
        (lx + 0.1, rx - 0.1, y - 0.03, y + 0.03, 0.07, 0.25),
        (lx + 0.1, rx - 0.1, y - 0.03, y + 0.03, CL_DOOR_TOP - 0.11, CL_DOOR_TOP - 0.01),
    ], mats["metal"], cl, origin=hinge)
    door["hinge"] = "vertical axis at the west (right-hand, street view) jamb"
    door["open_rotation_z_deg"] = "positive swings the leaf outward onto the pavement (-Y)"
    door_glass = glass("CL_Glass_Door", "y", y, lx + 0.1, rx - 0.1, 0.25, CL_DOOR_TOP - 0.11,
                       mats["glass"], cl_glass)
    handle = boxes("CL_Door_Handle", [
        (lx + 0.12, lx + 0.16, y - 0.11, y - 0.07, 0.6, 2.2),
        (lx + 0.12, lx + 0.16, y - 0.07, y - 0.03, 0.6, 0.66),
        (lx + 0.12, lx + 0.16, y - 0.07, y - 0.03, 2.14, 2.2),
    ], mats["metal"], cl)
    box("CL_Threshold", dx0, dx1, y - 0.3, y + 0.25, 0.0, 0.02, mats["metal"], cl)
    for child in (frame, fixed, door):
        parent_keep(child, entrance)
    parent_keep(fixed_glass, fixed)
    parent_keep(door_glass, door)
    parent_keep(handle, door)

    # Interior-ready shell: real depth, ceiling continuing inward, vestibule.
    shell = child_collection("CL_InteriorShell_TEMP", cl)
    ix0, ix1 = CL_X
    box("CL_Interior_Floor", ix0, ix1, y + 0.07, CL_DEPTH, 0.0, 0.02, mats["clints"], shell)
    box("CL_Interior_Ceiling", ix0, ix1, y + 0.07, CL_DEPTH, CL_HEAD - 0.02, CL_HEAD, mats["white"], shell)
    box("CL_Interior_WallLeft", ix0, ix0 + 0.12, y + 0.07, CL_DEPTH, 0.0, CL_HEAD, mats["clints"], shell)
    box("CL_Interior_WallRight", ix1 - 0.12, ix1, y + 0.07, CL_DEPTH, 0.0, CL_HEAD, mats["clints"], shell)
    box("CL_Interior_RearWall", ix0, ix1, CL_DEPTH, CL_DEPTH + 0.12, 0.0, CL_HEAD, mats["clints"], shell)
    box("CL_Interior_Vestibule_FloorMat", dx0 + 0.1, dx1 - 0.1, y + 0.1, y + 1.7, 0.02, 0.035,
        mats["metal"], shell)
    box("CL_Interior_CirculationVolume_GUIDE", ix0 + 1.5, ix1 - 1.5, y + 1.8, CL_DEPTH - 1.5, 0.02, 0.025,
        mats["clints"], shell)

    return door


def build_signage(mats, cols):
    sig = cols["signage"]
    band_y = -CANOPY_DEPTH - 0.08
    band_z = CANOPY_UNDERSIDE + 0.57
    names = {"Bay06_ABC_East": "ABC", "Bay05_Dome": "THE DOME",
             "Bay04_Tartuffe_SideStreetQuay": "TARTUFFE", "Bay03_CLINTS": "CLINTS",
             "Bay02_ABC": "ABC", "Bay01_ABC_Corner": "ABC"}
    for name, xa, xb in BAYS:
        cx = (xa + xb) / 2
        text_mesh(f"ABC_CanopySign_{name}_PLACEHOLDER", names[name], 0.5, 0.02,
                  (cx, band_y, band_z), FACING_NEG_Y, mats["letter"], sig)
    empty("CL_SignAnchor_Canopy", (-23.65, band_y, band_z), sig, "SINGLE_ARROW", 0.6)
    empty("SS_SignAnchor", (-32.3, SHOPFRONT_Y - 0.12, 1.9), sig, "SINGLE_ARROW", 0.6)
    empty("SS_LogoAnchor", (0.3, 2.2, 2.2), sig, "SINGLE_ARROW", 0.6)
    empty("ABC_EndBlock_SignAnchor_Smolensky", (-55.9, -0.15, 3.95), sig, "SINGLE_ARROW", 0.6)
    empty("ABC_EndBlock_SignAnchor_EveryMan", (-55.9, 0.4, 7.0), sig, "SINGLE_ARROW", 0.6)
    # Vertical ABC lettering: podium blade fin (both faces) and tower core.
    fx = END_BLOCK[1] - 0.17
    for i, letter in enumerate("ABC"):
        z = PODIUM_TOP - 1.6 - i * 2.6
        text_mesh(f"ABC_PodiumLetter_{letter}_East_PLACEHOLDER", letter, 2.2, 0.06,
                  (fx - 0.19, -0.75, z), FACING_NEG_X, mats["letter"], sig)
        text_mesh(f"ABC_PodiumLetter_{letter}_West_PLACEHOLDER", letter, 2.2, 0.06,
                  (fx + 0.19, -0.75, z), FACING_POS_X, mats["letter"], sig)
        text_mesh(f"ABC_TowerLetter_{letter}_PLACEHOLDER", letter, 2.4, 0.06,
                  ((CORE_X[0] + CORE_X[1]) / 2, -1.05, TOWER_TOP - 2.0 - i * 2.9),
                  FACING_NEG_Y, mats["letter"], sig)
    empty("ABC_TowerLogoAnchor", ((CORE_X[0] + CORE_X[1]) / 2, -1.05, TOWER_TOP - 4.9), sig,
          "SINGLE_ARROW", 1.5)


def build_anchors(cols):
    a = cols["anchors"]
    door_x = (CL_DOOR_LEAF[0] + CL_DOOR_LEAF[1]) / 2
    empty("CL_EntranceTriggerAnchor", (door_x, -1.0, 0.0), a, "CUBE", 0.6)
    empty("CL_InteriorSpawnAnchor", (door_x, 2.6, 0.0), a, "ARROWS", 0.6)
    empty("CL_ExitAnchor", (door_x, -1.9, 0.0), a, "ARROWS", 0.6)
    empty("CL_Neon_LeftAnchor", (-25.9, 0.7, 2.25), a, "CUBE", 0.5)
    empty("CL_Neon_RightAnchor", (-21.4, 0.7, 2.45), a, "CUBE", 0.5)
    empty("CL_LogoInteriorAnchor", (-23.65, CL_DEPTH - 0.1, 2.0), a, "CUBE", 0.6)
    empty("SS_EntranceAnchor", (1.2, 5.3, 0.0), a, "CUBE", 0.6)


def build_props(mats, cols):
    props = cols["props"]
    planter = multi_box_mesh("ABC_Planter_Module", [
        (-0.55, 0.55, -0.4, 0.4, 0.0, 0.72, 0),
        (-0.48, 0.48, -0.33, 0.33, 0.72, 0.74, 1),
    ], [mats["planter"], mats["interior"]])
    for i, (x, y) in enumerate(((-33.3, -2.6), (-32.4, -1.4), (-29.2, -2.2), (-19.3, -2.3))):
        obj_from_mesh(f"ABC_Planter_{i + 1:02d}", planter, props, (x, y, 0.0))


# --- Review scene ----------------------------------------------------------

def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def camera(name, location, target, lens, col):
    data = bpy.data.cameras.new(f"{name}_Data")
    data.lens = lens
    data.clip_end = 1000.0
    cam = bpy.data.objects.new(name, data)
    cam.location = location
    col.objects.link(cam)
    point_at(cam, target)
    return cam


def setup_review_scene(mats, master):
    review = child_collection("ABC_ReviewHelpers_NONEXPORT", master)
    box("ABC_Review_Ground_NONEXPORT", -140.0, 80.0, -80.0, 120.0, -0.1, 0.0, mats["ground"], review)
    box("ABC_Review_Road_NONEXPORT", -140.0, 80.0, -16.0, -5.5, -0.09, 0.005, mats["planter"], review)
    box("ABC_Review_RoadLowerByrom_NONEXPORT", 6.5, 16.0, -16.0, 120.0, -0.09, 0.005, mats["planter"], review)
    for i, (x, y) in enumerate(((-25.6, -1.4), (-15.5, -2.4), (1.4, 2.8))):
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.2, depth=1.75, location=(x, y, 0.875))
        human = bpy.context.object
        human.name = f"ABC_Review_HumanScale_{i + 1}_NONEXPORT"
        human.data.name = f"{human.name}_Mesh"
        human.data.materials.append(mats["white"])
        for c in list(human.users_collection):
            c.objects.unlink(human)
        review.objects.link(human)

    cams_col = child_collection("ABC_BlockoutCameras", master)
    cams = [
        camera("CAMERA_A_WideStreet", (-24.0, -78.0, 4.0), (-26.0, 0.0, 22.0), 20, cams_col),
        camera("CAMERA_B_LowAngleTower", (-40.0, -9.0, 1.6), (-16.0, 6.0, 30.0), 16, cams_col),
        camera("CAMERA_C_ClintsStraightOn", (-23.65, -13.5, 2.3), (-23.65, 0.0, 2.9), 32, cams_col),
        camera("CAMERA_D_ClintsThreeQuarter", (-14.2, -9.6, 1.7), (-24.4, 0.0, 2.9), 26, cams_col),
        camera("CAMERA_E_SideStreetStraightOn", (15.0, 3.2, 3.2), (0.0, 3.2, 5.0), 24, cams_col),
        camera("CAMERA_F_LowerByromElevation", (52.0, 28.0, 14.0), (0.0, 20.0, 20.0), 22, cams_col),
        camera("CAMERA_G_DistantSilhouette", (-95.0, -190.0, 18.0), (-24.0, 8.0, 26.0), 40, cams_col),
    ]

    lights = child_collection("ABC_BlockoutLights", master)
    sun_data = bpy.data.lights.new("ABC_Review_Sun_Data", "SUN")
    sun_data.energy = 3.2
    sun_data.angle = radians(3.0)
    sun = bpy.data.objects.new("ABC_Review_Sun", sun_data)
    lights.objects.link(sun)
    sun.rotation_euler = Vector((-0.55, 0.75, -0.62)).to_track_quat("-Z", "Y").to_euler()

    scene = bpy.context.scene
    scene.world = scene.world or bpy.data.worlds.new("ABC_BlockoutWorld")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.42, 0.45, 0.50, 1.0)
    bg.inputs["Strength"].default_value = 0.9
    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 850
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = 24
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    scene.camera = cams[0]
    return cams


def validate():
    required = (
        "ABC_Tower_Mass", "ABC_TowerCore_CurtainGlass", "ABC_Tower_RoofCornice",
        "ABC_Canopy_Frame", "ABC_Canopy_Panels", "ABC_Canopy_SignBand", "ABC_Canopy_UndersideGrid",
        "CL_Entrance", "CL_Door", "CL_DoorFrame", "CL_Glass_Door", "CL_Glass_Left", "CL_Glass_Right",
        "CL_Glass_Transom", "CL_EntranceTriggerAnchor", "CL_InteriorSpawnAnchor", "CL_ExitAnchor",
        "CL_Neon_LeftAnchor", "CL_Neon_RightAnchor", "CL_LogoInteriorAnchor", "CL_SignAnchor_Canopy",
        "SS_Glass_Main", "SS_Door", "SS_Entrance", "SS_EntranceAnchor", "SS_LogoAnchor", "SS_SignAnchor",
        "ABC_TowerLogoAnchor", "ABC_ProjectingGlassVolume_Frame", "ABC_Planter_01",
    )
    missing = [n for n in required if bpy.data.objects.get(n) is None]
    if missing:
        raise RuntimeError(f"Missing ABC blockout objects: {missing}")
    unnamed = [o.name for o in bpy.data.objects if o.name.startswith(("Cube", "Cylinder", "Text", "Camera"))]
    if unnamed:
        raise RuntimeError(f"Unnamed primitives left in scene: {unnamed}")
    bad_scale = [o.name for o in bpy.data.objects if o.type == "MESH"
                 and any(abs(v - 1.0) > 1e-5 for v in o.scale)]
    if bad_scale:
        raise RuntimeError(f"Unapplied mesh scales: {bad_scale}")
    door = bpy.data.objects["CL_Door"]
    hinge = door.matrix_world.translation
    if abs(hinge.x - (CL_DOOR_LEAF[1] - 0.05)) > 1e-4:
        raise RuntimeError(f"CL_Door pivot is not on the hinge: {tuple(hinge)}")
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and "NONEXPORT" not in o.name]
    unique = {o.data.name for o in meshes}
    tris = sum(sum(max(0, len(p.vertices) - 2) for p in o.data.polygons) for o in meshes)
    print(f"Validation: {len(meshes)} asset mesh objects ({len(unique)} unique meshes), ~{tris} triangles")
    print(f"Validation: Quay St frontage {abs(END_BLOCK[0]):.1f} m; tower {abs(TOWER_X0):.1f} x "
          f"{PODIUM_DEPTH:.2f} m, top {TOWER_TOP:.1f} m (+core); podium {PODIUM_TOP:.1f} m; "
          f"canopy {CANOPY_DEPTH:.1f} m deep, underside {CANOPY_UNDERSIDE:.2f} m")
    print(f"Validation: Clints clear width {CL_X[1] - CL_X[0]:.2f} m, door leaf "
          f"{CL_DOOR_LEAF[1] - CL_DOOR_LEAF[0]:.2f} x {CL_DOOR_TOP:.2f} m, interior depth {CL_DEPTH:.1f} m")


def save_notes():
    note = bpy.data.texts.new("ABC_BUILDING_BLOCKOUT_NOTES")
    note.write(
        "FIRST PASS / REVIEW HOLD - GEOMETRY ONLY (brief §47)\n"
        "Source: references/architecture/buildings/clints/12_ABC_Building_Clints_Side_Street.txt\n"
        "Origin: ground-level Quay St / Lower Byrom St corner. Quay St faces -Y, Lower Byrom faces +X.\n"
        "Quay St sequence (east->west): Every Man/Smolensky end block + ABC blade, ABC, THE DOME,\n"
        "TARTUFFE (Side Street's black Quay panel + door), CLINTS, ABC, ABC, blank corner wall.\n"
        "Side Street main frontage: double-height window + door on Lower Byrom under the blank corner.\n"
        "Tower: 14 floors of 3.35 m over a 9.6 m podium, 1.95 m grid bays, glazed core at the east end,\n"
        "blank east side wall. Grid built from linked ABC_TowerBay_Module / ABC_TowerWindow_Module.\n"
        "All dimensions are photographic estimates. Placeholder lettering is composition evidence only.\n"
        "Deferred: second geometry pass (§49), textures, emissives, props detail, GLB export.\n"
    )


def render_reviews(cameras, clints_door):
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    names = (
        "view-a-wide-street.png",
        "view-b-low-angle-tower.png",
        "view-c-clints-straight-on.png",
        "view-d-clints-three-quarter.png",
        "view-e-side-street-straight-on.png",
        "view-f-lower-byrom-elevation.png",
        "view-g-distant-silhouette.png",
    )
    scene = bpy.context.scene
    for cam, filename in zip(cameras, names):
        # View D shows the door swung open as in the daytime reference photo.
        clints_door.rotation_euler.z = radians(72) if "view-d" in filename else 0.0
        scene.camera = cam
        scene.render.filepath = str(RENDER_DIR / filename)
        bpy.ops.render.render(write_still=True)
        print(f"Rendered {scene.render.filepath}")
    clints_door.rotation_euler.z = 0.0


def main():
    master = clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene.unit_settings.scale_length = 1.0
    mats = create_materials()

    cols = {}
    cols["tower"] = child_collection("ABC_Tower", master)
    cols["podium"] = child_collection("ABC_Podium", master)
    cols["retail"] = child_collection("ABC_RetailFacade", master)
    cols["canopy"] = child_collection("ABC_Canopy", cols["retail"])
    cols["clints"] = child_collection("ABC_CLINTS", master)
    cols["sidestreet"] = child_collection("ABC_SIDE_STREET", master)
    cols["other"] = child_collection("ABC_OtherRetailBays", master)
    glass_root = child_collection("ABC_Glass", master)
    cols["tower_glass"] = child_collection("ABC_TowerGlass", glass_root)
    cols["podium_glass"] = child_collection("ABC_PodiumGlass", glass_root)
    cols["cl_glass"] = child_collection("CL_Glass", cols["clints"])
    cols["ss_glass"] = child_collection("SS_Glass", cols["sidestreet"])
    cols["interiors"] = child_collection("ABC_InteriorShells", master)
    cols["signage"] = child_collection("ABC_SignageSurfaces", master)
    cols["anchors"] = child_collection("ABC_InteractionAnchors", master)
    cols["props"] = child_collection("ABC_Props_Independent", master)

    build_tower(mats, cols)
    build_podium(mats, cols)
    build_canopy(mats, cols)
    build_other_bays(mats, cols)
    door = build_clints(mats, cols)
    build_end_block(mats, cols)
    build_rear_wing(mats, cols)
    build_lower_byrom_and_side_street(mats, cols)
    build_signage(mats, cols)
    build_anchors(cols)
    build_props(mats, cols)
    cameras = setup_review_scene(mats, master)
    bpy.context.view_layer.update()
    validate()
    save_notes()

    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    render_reviews(cameras, door)
    scene.camera = cameras[0]
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), check_existing=False)
    print(f"Saved geometry-only review blockout: {BLEND_PATH}")
    print(f"Review renders: {RENDER_DIR}")


if __name__ == "__main__":
    main()
