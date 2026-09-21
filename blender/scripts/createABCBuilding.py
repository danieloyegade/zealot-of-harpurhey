"""ABC Building (Clints + Side Street) - second geometry pass (brief §49).

Builds on the approved blockout layout in createABCBuildingBlockout.py (imported
as a module, the same promotion pattern as createRealCamera.py) and swaps in
refined builders for: tower window recesses (split-detail: detailed modules on
the first three floors, the lighter blockout module above), glazed-core
mullions and spandrels, podium sills/cornice, column plinths and bearing plates,
the canopy panel grid and per-tenant sign surfaces, the Clints entrance, glazing
and door hardware, Side Street glazing/doorways/louvres, and the patterned
service grille. Still geometry only: placeholder materials, no textures,
emissives, stock, foliage or detailed Clints interior.

Run headless:
  /Applications/Blender.app/Contents/MacOS/Blender --background \
    --python blender/scripts/createABCBuilding.py

Outputs: blender/source/abc_building.blend, public/assets/models/abc_building.glb,
renders/abc-building/*.png.
"""

import importlib.util
from math import radians
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("abc_blockout", HERE / "createABCBuildingBlockout.py")
bo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bo)

ROOT = bo.ROOT
BLEND_PATH = ROOT / "blender" / "source" / "abc_building.blend"
GLB_PATH = ROOT / "public" / "assets" / "models" / "abc_building.glb"
RENDER_DIR = ROOT / "renders" / "abc-building"

box, boxes, glass, empty = bo.box, bo.boxes, bo.glass, bo.empty
multi_box_mesh, obj_from_mesh, parent_keep = bo.multi_box_mesh, bo.obj_from_mesh, bo.parent_keep
child_collection = bo.child_collection

DETAIL_TOWER_FLOORS = 3   # mid-range geometry (§44); floors above use the light module
NON_EXPORT_COLLECTIONS = {"ABC_ReviewHelpers_NONEXPORT", "ABC_BlockoutCameras", "ABC_BlockoutLights"}


def beads(axis, plane, u0, u1, z0, z1, w=0.022, gap=0.012, depth=0.018):
    """Glazing beads either side of a glass plane, as box tuples."""
    out = []
    for p0, p1 in ((plane - gap - depth, plane - gap), (plane + gap, plane + gap + depth)):
        for a, b, za, zb in ((u0, u0 + w, z0, z1), (u1 - w, u1, z0, z1),
                             (u0 + w, u1 - w, z0, z0 + w), (u0 + w, u1 - w, z1 - w, z1)):
            out.append((*bo.xy(axis, a, b, p0, p1), za, zb))
    return out


# --- Tower -----------------------------------------------------------------

def tower_bay_detail_mesh(mats):
    w, h, t, d = bo.TOWER_BAY_W, bo.FLOOR_H, 0.16, bo.GRID_PROUD
    il, ir = -w / 2 + t, w / 2 - t
    zb, zt = 0.24, h - 0.2
    return multi_box_mesh("ABC_TowerBay_Module_Detail", [
        (-w / 2, il, -d, 0, 0, h, 0),
        (ir, w / 2, -d, 0, 0, h, 0),
        (il, ir, -d, 0, 0, zb, 0),
        (il, ir, -d, 0, zt, h, 0),
        (il, ir, -0.36, -0.14, zb, zb + 0.05, 0),          # sill ledge inside the recess
        (il, ir, -d, -d + 0.04, zt - 0.03, zt, 0),         # head drip at the frame front
        (il, il + 0.05, -0.14, -0.08, zb, zt, 1),          # window sub-frame
        (ir - 0.05, ir, -0.14, -0.08, zb, zt, 1),
        (il, ir, -0.14, -0.08, zb, zb + 0.05, 1),
        (il, ir, -0.14, -0.08, zt - 0.05, zt, 1),
        (-0.025, 0.025, -0.14, -0.08, zb + 0.05, zt - 0.05, 1),   # central mullion
        (il, ir, -0.17, -0.11, 0.98, 1.05, 1),             # horizontal band
        (il, ir, -0.03, 0, zb, zt, 2),                     # dark backing
    ], [mats["white"], mats["metal"], mats["interior"]])


def build_tower(mats, cols):
    tower, glass_col = cols["tower"], cols["tower_glass"]
    light_bay, win = bo.tower_modules(mats, glass_col)
    detail_bay = tower_bay_detail_mesh(mats)
    frames = child_collection("ABC_TowerGrid_Instances", tower)
    W, H = bo.TOWER_BAY_W, bo.FLOOR_H

    def place(label, loc, rot, floor_index):
        bay = detail_bay if floor_index < DETAIL_TOWER_FLOORS else light_bay
        obj_from_mesh(f"ABC_TowerBay_{label}", bay, frames, loc, rot)
        obj_from_mesh(f"ABC_TowerWindow_{label}", win, glass_col, loc, rot)

    box("ABC_Tower_Mass", bo.TOWER_X0, 0.0, 0.0, bo.PODIUM_DEPTH, bo.PODIUM_TOP, bo.TOWER_TOP,
        mats["white"], tower)
    for f in range(bo.TOWER_FLOORS):
        z = bo.PODIUM_TOP + f * H
        for i in range(9):
            place(f"Quay_F{f + 1:02d}_B{i + 1:02d}", (bo.CORNER_X - W * (i + 0.5), 0.0, z), 0.0, f)
    bo.wall_with_openings("ABC_Tower_CornerBlankWall_Quay", "y", -bo.GRID_PROUD, 0.0, bo.CORNER_X, 0.0,
                          0.0, bo.TOWER_TOP, [(*bo.SS_QUAY_DOOR, 0.0, 3.2), (*bo.SS_QUAY_PANEL, 0.3, 3.2)],
                          mats["white"], tower)

    lb_floors = int(round((bo.TOWER_TOP - bo.LB_GRID_START) / H))
    for f in range(lb_floors):
        z = bo.LB_GRID_START + f * H
        for i in range(9):
            place(f"LowerByrom_F{f + 2:02d}_B{i + 1:02d}", (0.0, bo.LB_BLANK_Y + W * (i + 0.5), z),
                  radians(90), f)
    box("ABC_Tower_CornerBlankWall_LowerByrom", 0.0, bo.GRID_PROUD, -bo.GRID_PROUD, bo.LB_BLANK_Y,
        bo.LB_GRID_START, bo.TOWER_TOP, mats["white"], tower)

    count = int(abs(bo.TOWER_X0) / W)
    margin = (abs(bo.TOWER_X0) - count * W) / 2
    for f in range(bo.TOWER_FLOORS):
        z = bo.PODIUM_TOP + f * H
        for i in range(count):
            x = -margin - W * (i + 0.5)
            if z < bo.REAR_WING[2] and x > bo.REAR_WING[0] - W / 2:
                continue
            # Rear is low-priority (§2): always the light module.
            place(f"Rear_F{f + 1:02d}_B{i + 1:02d}", (x, bo.PODIUM_DEPTH, z), radians(180), 99)

    # Roof: projecting cornice slab + parapet upstand (no invented plant, §9).
    x0, x1 = bo.TOWER_X0 - 0.35, bo.GRID_PROUD + 0.25
    y0, y1 = -bo.GRID_PROUD - 0.4, bo.PODIUM_DEPTH + bo.GRID_PROUD + 0.25
    top = bo.TOWER_TOP
    box("ABC_Tower_RoofCornice", x0, x1, y0, y1, top, top + 0.8, mats["white"], tower)
    boxes("ABC_Tower_RoofCornice_Soffit", [(x0, x1, y0, y1, top - 0.06, top)], mats["concrete"], tower)
    boxes("ABC_Tower_Parapet", [
        (x0, x1, y0, y0 + 0.25, top + 0.8, top + 1.5), (x0, x1, y1 - 0.25, y1, top + 0.8, top + 1.5),
        (x0, x0 + 0.25, y0, y1, top + 0.8, top + 1.5), (x1 - 0.25, x1, y0, y1, top + 0.8, top + 1.5),
    ], mats["white"], tower)

    # Glazed core: fins, cap with coping, curtain wall, mullions, spandrels.
    cx0, cx1 = bo.CORE_X
    front = -0.95
    core_top = top + 3.6
    gx0, gx1 = cx0 + 0.4, cx1 - 0.4
    boxes("ABC_TowerCore_Frame", [
        (cx0, cx0 + 0.4, front, 0.0, bo.PODIUM_TOP, core_top),
        (cx1 - 0.4, cx1, front, 0.0, bo.PODIUM_TOP, core_top),
        (cx0, cx1, front - 0.1, 0.0, core_top - 0.6, core_top),
        (cx0 - 0.08, cx1 + 0.08, front - 0.18, 0.08, core_top, core_top + 0.12),
        (cx0, cx1, front - 0.06, 0.0, bo.PODIUM_TOP - 0.3, bo.PODIUM_TOP),   # base plinth on podium roof
    ], mats["white"], tower)
    glass("ABC_TowerCore_CurtainGlass", "y", front + 0.2, gx0, gx1, bo.PODIUM_TOP, core_top - 0.6,
          mats["glass"], glass_col)
    boxes("ABC_TowerCore_Backing", [(gx0, gx1, -0.2, 0.0, bo.PODIUM_TOP, core_top - 0.6)],
          mats["interior"], tower)
    span = gx1 - gx0
    levels = [bo.PODIUM_TOP + k * H for k in range(1, bo.TOWER_FLOORS + 1)]
    mull = [(gx0 + span * k / 3 - 0.04, gx0 + span * k / 3 + 0.04, front + 0.05, front + 0.19,
             bo.PODIUM_TOP, core_top - 0.6) for k in (1, 2)]
    mull += [(gx0, gx1, front + 0.05, front + 0.19, z - 0.06, z + 0.06) for z in levels]
    mull += [(gx0, gx1, front + 0.1, front + 0.19, z - 2.2, z - 2.17) for z in levels]   # light transom
    mull += [(gx0, gx0 + 0.06, front + 0.05, front + 0.19, bo.PODIUM_TOP, core_top - 0.6),
             (gx1 - 0.06, gx1, front + 0.05, front + 0.19, bo.PODIUM_TOP, core_top - 0.6)]
    boxes("ABC_TowerCore_Mullions", mull, mats["metal"], tower)
    boxes("ABC_TowerCore_Spandrels", [(gx0, gx1, front + 0.24, front + 0.3, z - 0.45, z + 0.3) for z in levels],
          mats["metal"], tower)


# --- Podium refinements ----------------------------------------------------

def column_xs():
    return [xa for _n, xa, _xb in bo.BAYS] + [bo.CORNER_X]


def build_podium(mats, cols):
    bo_build_podium(mats, cols)
    podium, retail = cols["podium"], cols["retail"]
    plinths, gaps = [], []
    for x in column_xs():
        x0 = x - bo.COLUMN_W / 2
        x1 = x + bo.COLUMN_W / 2 if x != bo.CORNER_X else x
        plinths.append((x0 - 0.03, x1 + (0.03 if x != bo.CORNER_X else 0.0), -0.13, 0.53, 0.0, 0.12))
        gaps.append((x0 + 0.02, x1 - 0.02, -0.08, 0.48, bo.CANOPY_UNDERSIDE - 0.1, bo.CANOPY_UNDERSIDE))
    boxes("ABC_Column_Plinths", plinths, mats["metal"], retail)
    boxes("ABC_Column_HeadShadowGaps", gaps, mats["metal"], retail)
    sills, heads = [], []
    for _name, xa, xb in bo.BAYS:
        u0 = xa + bo.COLUMN_W / 2
        u1 = xb - (bo.COLUMN_W / 2 if xb != bo.CORNER_X else 0.0)
        z0, z1 = bo.FIRST_FLOOR_WIN
        sills.append((u0, u1, -0.09, 0.42, z0 - 0.1, z0 + 0.02))
        heads.append((u0, u1, 0.0, 0.4, z1 - 0.04, z1))
    boxes("ABC_Podium_UpperWindow_Sills", sills, mats["white"], podium)
    boxes("ABC_Podium_UpperWindow_HeadShadow", heads, mats["concrete"], podium)
    x_east, x_west = bo.CANOPY_X
    boxes("ABC_Podium_Cornice", [
        (x_east, x_west, -0.24, 0.2, bo.PODIUM_TOP - 0.14, bo.PODIUM_TOP),
        (x_east, x_west, -0.14, -0.11, bo.FIRST_FLOOR_WIN[1] + 0.2, bo.FIRST_FLOOR_WIN[1] + 0.26),
    ], mats["white"], podium)
    boxes("ABC_Podium_ParapetCoping", [
        (x_east - 0.34, bo.TOWER_X0, -0.18, 0.36, bo.PODIUM_TOP + 0.7, bo.PODIUM_TOP + 0.78),
    ], mats["concrete"], podium)


# --- Canopy ----------------------------------------------------------------

def build_canopy(mats, cols):
    col, sig = cols["canopy"], cols["signage"]
    x0, x1 = bo.CANOPY_X
    front = -bo.CANOPY_DEPTH
    u, t = bo.CANOPY_UNDERSIDE, bo.CANOPY_TOP
    box("ABC_Canopy_Deck", x0, x1, front, 0.0, t - 0.28, t - 0.08, mats["concrete"], col)
    boxes("ABC_Canopy_Frame", [
        (x0 - 0.05, x1 + 0.05, front - 0.1, front + 0.12, t, t + 0.05),        # coping
        (x0, x1, front - 0.06, front + 0.08, t - 0.32, t),                     # dark upper fascia
        (x0, x1, front - 0.08, front + 0.14, u - 0.06, u + 0.06),              # lower lip
        (x0, x1, front - 0.07, front - 0.04, u + 0.06, u + 0.09),              # sign band bottom trim
        (x0, x1, front - 0.07, front - 0.04, t - 0.35, t - 0.32),              # sign band top trim
        (x0 - 0.06, x0 + 0.06, front - 0.08, 0.0, u - 0.06, t + 0.05),         # east end cap
        (x1 - 0.06, x1 + 0.06, front - 0.08, 0.0, u - 0.06, t + 0.05),         # west end cap
        (x0, x1, -0.1, 0.0, u, t - 0.28),                                      # back fixing channel
    ], mats["metal"], col)
    # Individual sign surfaces per tenant (§15, §39) + returns on the end caps.
    for name, xa, xb in bo.BAYS:
        sa, sb = max(xa, x0) + 0.06, min(xb, x1) - 0.06
        box(f"ABC_SignSurface_{name}", sa, sb, front - 0.04, front + 0.1, u + 0.09, t - 0.35,
            mats["canopy"], sig)
    box("ABC_SignSurface_EndEast", x0 - 0.08, x0 - 0.06, front + 0.1, -0.3, u + 0.09, t - 0.35,
        mats["canopy"], sig)
    box("ABC_SignSurface_EndWest", x1 + 0.06, x1 + 0.08, front + 0.1, -0.3, u + 0.09, t - 0.35,
        mats["canopy"], sig)
    lines = [(x0, x1, front - 0.075, front - 0.045, z - 0.015, z + 0.015)
             for z in (u + 0.42, u + 0.72, u + 1.02)]
    lines += [(x - 0.02, x + 0.02, front - 0.075, front - 0.045, u + 0.06, t - 0.32)
              for x in [xa for _n, xa, _xb in bo.BAYS[1:]]]
    boxes("ABC_Canopy_SignLines", lines, mats["metal"], col)

    # Underside: inset rectangular panels between T-bar framing (emissive-ready).
    rows = 4
    n = int(round((x1 - x0) / 1.25))
    cw, rd = (x1 - x0) / n, (bo.CANOPY_DEPTH - 0.14 - 0.1) / rows
    ystart = front + 0.14
    panels, tbars = [], []
    for i in range(n):
        for j in range(rows):
            cx0, cy0 = x0 + i * cw, ystart + j * rd
            panels.append((cx0 + 0.03, cx0 + cw - 0.03, cy0 + 0.03, cy0 + rd - 0.03, u + 0.012, u + 0.03))
    for j in range(rows + 1):
        yy = ystart + j * rd
        tbars.append((x0, x1, yy - 0.03, yy + 0.03, u - 0.018, u + 0.012))
    for i in range(n + 1):
        xx = x0 + i * cw
        tbars.append((xx - 0.03, xx + 0.03, ystart, ystart + rows * rd, u - 0.018, u + 0.012))
    tbars.append((x0, x1, front, ystart, u - 0.03, u + 0.012))       # front perimeter trim
    tbars.append((x0, x1, -0.1, 0.0, u - 0.03, u + 0.012))          # back perimeter trim
    boxes("ABC_Canopy_Panels", panels, mats["canopy"], col)
    boxes("ABC_Canopy_UndersideGrid", tbars, mats["metal"], col)
    # Bearing plates where the canopy meets each column (§13 supporting relationship).
    boxes("ABC_Canopy_ColumnBearingPlates", [
        (x - 0.36, (x + 0.36) if x != bo.CORNER_X else x, -0.16, 0.56, u - 0.05, u)
        for x in column_xs()], mats["metal"], col)
    # Kept name for the blockout's validation list.
    box("ABC_Canopy_SignBand", x0 + 0.06, x1 - 0.06, front + 0.1, front + 0.12, u + 0.09, t - 0.35,
        mats["metal"], col)


# --- Clints hero storefront ------------------------------------------------

def build_clints(mats, cols):
    cl, cl_glass = cols["clints"], cols["cl_glass"]
    y = bo.SHOPFRONT_Y
    y0, y1 = y - 0.08, y + 0.08
    lx0, _ = bo.CL_LEFT_GLASS
    _, rx1 = bo.CL_RIGHT_GLASS
    dx0, dx1 = bo.CL_DOORS
    head, dtop = bo.CL_HEAD, bo.CL_DOOR_TOP
    X0, X1 = bo.CL_X

    boxes("CL_Storefront_Frame", [
        (X0, X1, y0, y1, 0.0, 0.07),                        # sill
        (X0, X1, y0 - 0.06, y0, 0.0, 0.1),                  # outer sill kerb / drip
        (X0, X1, y0, y1, head - 0.14, head),                # head
        (X0, X1, y0 - 0.04, y1, head - 0.02, head + 0.04),  # head cover flashing
        (X0, X0 + 0.09, y0, y1, 0.0, head),                 # jambs
        (X1 - 0.09, X1, y0, y1, 0.0, head),
        (dx0 - 0.05, dx0 + 0.05, y0, y1, 0.0, head),        # door-side mullions
        (dx1 - 0.05, dx1 + 0.05, y0, y1, 0.0, head),
        (dx0 - 0.03, dx0 + 0.03, y0 - 0.03, y0, 0.07, head - 0.14),   # mullion cover caps
        (dx1 - 0.03, dx1 + 0.03, y0 - 0.03, y0, 0.07, head - 0.14),
        (lx0 + 0.09, dx0 - 0.05, y0, y1, 0.82, 0.9),        # low rails (daytime photo)
        (dx1 + 0.05, rx1 - 0.09, y0, y1, 0.82, 0.9),
    ], mats["metal"], cl)
    glass("CL_Glass_Left", "y", y, lx0 + 0.09, dx0 - 0.05, 0.07, head - 0.14, mats["glass"], cl_glass)
    glass("CL_Glass_Right", "y", y, dx1 + 0.05, rx1 - 0.09, 0.07, head - 0.14, mats["glass"], cl_glass)
    bead_parts = []
    for a, b in ((lx0 + 0.09, dx0 - 0.05), (dx1 + 0.05, rx1 - 0.09)):
        bead_parts += beads("y", y, a, b, 0.07, 0.82) + beads("y", y, a, b, 0.9, head - 0.14)
    bead_parts += beads("y", y, dx0 + 0.05, dx1 - 0.05, dtop + 0.08, head - 0.14)
    boxes("CL_Storefront_GlazingBeads", bead_parts, mats["metal"], cl)

    entrance = empty("CL_Entrance", ((dx0 + dx1) / 2, y, 0.0), cl, "ARROWS", 0.6)
    fl0, fl1 = bo.CL_FIXED_LEAF
    frame = boxes("CL_DoorFrame", [
        (dx0 + 0.05, dx1 - 0.05, y0, y1, dtop, dtop + 0.08),              # door transom
        (fl1 - 0.03, fl1 + 0.03, y0, y1, 0.07, dtop),                      # meeting mullion
        (dx0 + 0.05, dx1 - 0.05, y + 0.04, y + 0.07, dtop - 0.02, dtop),  # head stop
        (dx1 - 0.08, dx1 - 0.05, y + 0.04, y + 0.07, 0.07, dtop),         # hinge-side stop
    ], mats["metal"], cl)
    glass("CL_Glass_Transom", "y", y, dx0 + 0.05, dx1 - 0.05, dtop + 0.08, head - 0.14,
          mats["glass"], cl_glass)

    def leaf_parts(a, b):
        return [(a, a + 0.1, y - 0.03, y + 0.03, 0.07, dtop - 0.01),
                (b - 0.1, b, y - 0.03, y + 0.03, 0.07, dtop - 0.01),
                (a + 0.1, b - 0.1, y - 0.03, y + 0.03, 0.07, 0.29),          # kick rail
                (a + 0.1, b - 0.1, y - 0.03, y + 0.03, dtop - 0.13, dtop - 0.01)]

    fixed = boxes("CL_DoorFixedLeaf", leaf_parts(fl0 + 0.05, fl1 - 0.03)
                  + beads("y", y, fl0 + 0.15, fl1 - 0.13, 0.29, dtop - 0.13)
                  + [(fl1 - 0.2, fl1 - 0.16, y + 0.03, y + 0.05, 0.07, 0.3)],  # flush bolt
                  mats["metal"], cl)
    fixed_glass = glass("CL_Glass_DoorFixed", "y", y, fl0 + 0.15, fl1 - 0.13, 0.29, dtop - 0.13,
                        mats["glass"], cl_glass)

    lx, rx = bo.CL_DOOR_LEAF[0] + 0.03, bo.CL_DOOR_LEAF[1] - 0.05
    hinge = (rx, y, 0.0)
    door = boxes("CL_Door", leaf_parts(lx, rx) + beads("y", y, lx + 0.1, rx - 0.1, 0.29, dtop - 0.13),
                 mats["metal"], cl, origin=hinge)
    door["hinge"] = "vertical axis at the west (right-hand, street view) jamb"
    door["open_rotation_z_deg"] = "positive swings the leaf outward onto the pavement (-Y)"
    door_glass = glass("CL_Glass_Door", "y", y, lx + 0.1, rx - 0.1, 0.29, dtop - 0.13, mats["glass"], cl_glass)
    hx = lx + 0.14
    handle = boxes("CL_Door_Handle", [
        (hx - 0.02, hx + 0.02, y - 0.12, y - 0.08, 0.45, 2.25),     # long street-side pull
        (hx - 0.015, hx + 0.015, y - 0.08, y - 0.03, 0.55, 0.6),
        (hx - 0.015, hx + 0.015, y - 0.08, y - 0.03, 2.1, 2.15),
        (hx - 0.02, hx + 0.02, y + 0.08, y + 0.12, 0.8, 1.6),       # interior pull
        (hx - 0.015, hx + 0.015, y + 0.03, y + 0.08, 0.85, 0.9),
        (hx - 0.015, hx + 0.015, y + 0.03, y + 0.08, 1.5, 1.55),
    ], mats["metal"], cl)
    hinges = boxes("CL_Door_Hinges", [(rx - 0.01, rx + 0.03, y - 0.045, y + 0.045, z, z + 0.14)
                                      for z in (0.3, 1.45, 2.6)], mats["metal"], cl)
    lock = boxes("CL_Door_Lock", [(lx + 0.02, lx + 0.08, y - 0.045, y + 0.045, 1.0, 1.12)], mats["metal"], cl)
    closer = boxes("CL_Door_Closer", [(rx - 0.55, rx - 0.12, y + 0.03, y + 0.1, dtop - 0.12, dtop - 0.04)],
                   mats["metal"], cl)
    boxes("CL_Threshold", [(dx0, dx1, y - 0.3, y + 0.25, 0.0, 0.02),
                           (dx0, dx1, y - 0.5, y - 0.38, 0.0, 0.012)], mats["metal"], cl)
    for child in (frame, fixed, door):
        parent_keep(child, entrance)
    parent_keep(fixed_glass, fixed)
    for child in (door_glass, handle, hinges, lock, closer):
        parent_keep(child, door)

    # Interior-ready shell (unchanged scope: no fit-out, §21).
    shell = child_collection("CL_InteriorShell_TEMP", cl)
    box("CL_Interior_Floor", X0, X1, y + 0.08, bo.CL_DEPTH, 0.0, 0.02, mats["clints"], shell)
    box("CL_Interior_Ceiling", X0, X1, y + 0.08, bo.CL_DEPTH, head - 0.02, head, mats["white"], shell)
    box("CL_Interior_WallLeft", X0, X0 + 0.12, y + 0.08, bo.CL_DEPTH, 0.0, head, mats["clints"], shell)
    box("CL_Interior_WallRight", X1 - 0.12, X1, y + 0.08, bo.CL_DEPTH, 0.0, head, mats["clints"], shell)
    box("CL_Interior_RearWall", X0, X1, bo.CL_DEPTH, bo.CL_DEPTH + 0.12, 0.0, head, mats["clints"], shell)
    boxes("CL_Interior_Skirting", [(X0 + 0.12, X0 + 0.14, y + 0.3, bo.CL_DEPTH, 0.0, 0.1),
                                   (X1 - 0.14, X1 - 0.12, y + 0.3, bo.CL_DEPTH, 0.0, 0.1),
                                   (X0, X1, bo.CL_DEPTH - 0.02, bo.CL_DEPTH, 0.0, 0.1)],
          mats["metal"], shell)
    box("CL_Interior_ShopfrontBulkhead", X0, X1, y + 0.08, y + 0.5, head - 0.25, head, mats["white"], shell)
    box("CL_Interior_Vestibule_FloorMat", dx0 + 0.1, dx1 - 0.1, y + 0.1, y + 1.7, 0.0, 0.03,
        mats["metal"], shell)
    box("CL_Interior_CirculationVolume_GUIDE", X0 + 1.5, X1 - 1.5, y + 1.8, bo.CL_DEPTH - 1.5, 0.02, 0.025,
        mats["clints"], shell)
    return door


# --- Side Street + Lower Byrom refinements ---------------------------------

def build_lower_byrom_and_side_street(mats, cols):
    bo_build_lower_byrom(mats, cols)
    ss, tower = cols["sidestreet"], cols["tower"]
    tall = (0.4, 4.0, 0.7, 5.6)
    door = (4.6, 6.0)
    windows = [(6.6 + i * 3.8, 6.6 + i * 3.8 + 3.3, 0.8, 4.4) for i in range(4)]
    sills = [(0.14, 0.72, tall[0] - 0.05, tall[1] + 0.05, tall[2] - 0.1, tall[2])]
    sills += [(0.14, 0.72, a - 0.05, b + 0.05, z0 - 0.08, z0) for a, b, z0, _z1 in windows]
    boxes("SS_WindowSills", sills, mats["white"], ss)
    parts = beads("x", 0.2, tall[0] + 0.1, tall[1] - 0.1, tall[2] + 0.1, tall[3] - 0.1)
    for a, b, z0, z1 in windows:
        parts += beads("x", 0.2, a + 0.08, b - 0.08, z0 + 0.08, z1 - 0.08)
    boxes("SS_GlazingBeads", parts, mats["metal"], ss)
    # Door hardware (children of the hinged leaf) + threshold.
    leaf = bpy.data.objects["SS_Door"]
    hy = door[1] - 0.26
    handle = boxes("SS_Door_Handle", [(0.26, 0.3, hy - 0.02, hy + 0.02, 0.7, 1.9),
                                      (0.23, 0.26, hy - 0.015, hy + 0.015, 0.78, 0.82),
                                      (0.23, 0.26, hy - 0.015, hy + 0.015, 1.78, 1.82)], mats["metal"], ss)
    hinges = boxes("SS_Door_Hinges", [(0.155, 0.245, door[0] + 0.07, door[0] + 0.11, z, z + 0.12)
                                      for z in (0.3, 1.3, 2.3)], mats["metal"], ss)
    parent_keep(handle, leaf)
    parent_keep(hinges, leaf)
    box("SS_Threshold", 0.1, 0.75, door[0], door[1], 0.0, 0.02, mats["metal"], ss)
    # Quay St door hardware + black panel trim.
    qleaf = bpy.data.objects["SS_QuayDoor"]
    d0, d1 = bo.SS_QUAY_DOOR
    split = d1 - 0.6
    qx = split - 0.3
    qhandle = boxes("SS_QuayDoor_Handle", [(qx - 0.02, qx + 0.02, -0.34, -0.3, 0.7, 1.9),
                                           (qx - 0.015, qx + 0.015, -0.3, -0.23, 0.78, 0.82),
                                           (qx - 0.015, qx + 0.015, -0.3, -0.23, 1.78, 1.82)],
                    mats["metal"], ss)
    parent_keep(qhandle, qleaf)
    p0, p1 = bo.SS_QUAY_PANEL
    boxes("SS_QuayPanel_Trim", [(p0, p1, -0.2, -0.14, 0.3, 0.36), (p0, p1, -0.2, -0.14, 3.14, 3.2),
                                (p0, p0 + 0.06, -0.2, -0.14, 0.3, 3.2), (p1 - 0.06, p1, -0.2, -0.14, 0.3, 3.2)],
          mats["metal"], ss)
    box("SS_QuayThreshold", d0, d1, -0.7, -0.1, 0.0, 0.02, mats["metal"], ss)
    # Ventilation strip: individual louvre blades.
    boxes("ABC_LowerByrom_VentBlades", [(0.3, 0.5, 4.6, 21.3, z, z + 0.03) for z in (5.8, 5.9, 6.0, 6.1)],
          mats["metal"], tower)


# --- Rear wing with patterned service grille (§33) -------------------------

def build_rear_wing(mats, cols):
    col = cols["podium"]
    wx, wy, wz = bo.REAR_WING
    D, W = bo.PODIUM_DEPTH, bo.TOWER_BAY_W
    box("ABC_RearWing_Mass", wx, 0.0, D, wy, 0.0, wz, mats["white"], col)
    box("ABC_RearWing_Parapet", wx, 0.3, D, wy + 0.3, wz, wz + 0.6, mats["white"], col)
    boxes("ABC_RearWing_ParapetCoping", [(wx - 0.05, 0.38, D, wy + 0.38, wz + 0.6, wz + 0.68)],
          mats["concrete"], col)
    nfin = int((wy - D) / W)
    boxes("ABC_RearWing_Fins", [(0.0, 0.35, y - 0.12, y + 0.12, 3.2, wz)
                                for y in [D + k * W for k in range(1, nfin + 1)]], mats["white"], col)
    for k in range(1, int(wz / bo.FLOOR_H)):
        z = k * bo.FLOOR_H
        glass(f"ABC_PodiumGlass_RearWing_F{k:02d}", "x", 0.02, D + 0.3, wy - 0.3, z + 0.9, z + 2.6,
              mats["glass"], cols["podium_glass"])
    boxes("ABC_RearWing_StripWindowSills", [(0.0, 0.1, D + 0.3, wy - 0.3, k * bo.FLOOR_H + 0.84,
                                             k * bo.FLOOR_H + 0.9) for k in range(1, int(wz / bo.FLOOR_H))],
          mats["concrete"], col)
    # Wave-pattern screen module: alternating U / inverted-U units in two rows.
    parts = [
        (0.0, 0.12, -0.9, 0.9, 0.0, 0.1, 0), (0.0, 0.12, -0.9, 0.9, 1.1, 1.2, 0),
        (0.0, 0.12, -0.9, -0.8, 0.0, 1.2, 0), (0.0, 0.12, 0.8, 0.9, 0.0, 1.2, 0),
        (-0.2, -0.15, -0.8, 0.8, 0.1, 1.1, 1),
    ]
    unit, leg = 0.32, 0.06
    for row, (z0, z1, flip) in enumerate(((0.12, 0.58, False), (0.62, 1.08, True))):
        offset = 0.0 if row == 0 else unit / 2
        for k in range(5):
            a = -0.8 + offset + k * unit
            b = min(a + unit - 0.02, 0.8)
            if b - a < 0.15:
                continue
            base = (z1 - leg, z1) if flip else (z0, z0 + leg)
            parts += [(0.02, 0.1, a, a + leg, z0, z1, 0), (0.02, 0.1, b - leg, b, z0, z1, 0),
                      (0.02, 0.1, a, b, *base, 0)]
    grille = multi_box_mesh("ABC_ServiceGrille_Module", parts, [mats["concrete"], mats["interior"]])
    box("ABC_RearWing_BaseBand", 0.0, 0.2, D, wy, 0.0, 3.2, mats["concrete"], col)
    for k in range(nfin):
        obj_from_mesh(f"ABC_ServiceGrille_{k + 1:02d}", grille, col, (0.2, D + W * (k + 0.5), 0.35))


# --- Review, export, reimport check ---------------------------------------

def add_close_cameras(cams_col):
    return [
        bo.camera("CAMERA_H_ClintsEntranceDetail", (-21.4, -4.4, 1.55), (-23.7, 0.3, 1.6), 30, cams_col),
        bo.camera("CAMERA_I_CanopyUnderside", (-17.0, -1.6, 1.3), (-26.0, -2.0, 3.7), 18, cams_col),
        bo.camera("CAMERA_J_SideStreetCorner", (7.5, -9.5, 2.0), (-1.2, 1.8, 3.2), 24, cams_col),
        bo.camera("CAMERA_K_ServiceGrille", (4.6, 29.0, 1.2), (0.1, 34.0, 0.9), 28, cams_col),
    ]


RENDER_NAMES = (
    "view-a-wide-street.png", "view-b-low-angle-tower.png", "view-c-clints-straight-on.png",
    "view-d-clints-three-quarter.png", "view-e-side-street-straight-on.png",
    "view-f-lower-byrom-elevation.png", "view-g-distant-silhouette.png",
    "view-h-clints-entrance-detail.png", "view-i-canopy-underside.png",
    "view-j-side-street-corner.png", "view-k-service-grille.png",
)


def render_all(cameras, door):
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for cam, filename in zip(cameras, RENDER_NAMES):
        door.rotation_euler.z = radians(72) if "view-d" in filename else 0.0
        scene.camera = cam
        scene.render.filepath = str(RENDER_DIR / filename)
        bpy.ops.render.render(write_still=True)
        print(f"Rendered {scene.render.filepath}")
    door.rotation_euler.z = 0.0


def exportable(obj):
    if obj.type not in {"MESH", "EMPTY"}:
        return False
    if any(c.name in NON_EXPORT_COLLECTIONS for c in obj.users_collection):
        return False
    # Placeholder lettering and review guides stay in the .blend only (§39, §53).
    return not obj.name.endswith(("_PLACEHOLDER", "_GUIDE", "_NONEXPORT"))


def export_glb():
    bpy.ops.object.select_all(action="DESELECT")
    chosen = [o for o in bpy.data.objects if exportable(o)]
    for obj in chosen:
        obj.select_set(True)
    GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(GLB_PATH), export_format="GLB", use_selection=True,
                              export_apply=True, export_yup=True, export_cameras=False,
                              export_lights=False, export_extras=True)
    print(f"Exported {len(chosen)} objects to {GLB_PATH} ({GLB_PATH.stat().st_size / 1e6:.2f} MB)")
    return len(chosen)


def reimport_check(expected):
    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(GLB_PATH))
    objs = bpy.data.objects
    door = objs.get("CL_Door")
    problems = []
    if door is None or door.parent is None or door.parent.name != "CL_Entrance":
        problems.append("CL_Door missing or not parented to CL_Entrance")
    for name in ("CL_Glass_Door", "CL_EntranceTriggerAnchor", "CL_InteriorSpawnAnchor", "CL_ExitAnchor",
                 "SS_EntranceAnchor", "ABC_Canopy_Panels", "ABC_TowerLogoAnchor"):
        if objs.get(name) is None:
            problems.append(f"{name} missing after reimport")
    if any(o.name.endswith("_PLACEHOLDER") or "NONEXPORT" in o.name for o in objs):
        problems.append("review/placeholder objects leaked into the GLB")
    meshes = [o for o in objs if o.type == "MESH"]
    print(f"Reimport: {len(objs)} objects ({len(meshes)} meshes, "
          f"{len({o.data.name for o in meshes})} unique mesh datablocks); exported {expected}")
    if problems:
        raise RuntimeError("GLB reimport check failed: " + "; ".join(problems))


def save_notes():
    note = bpy.data.texts.new("ABC_BUILDING_DETAIL_NOTES")
    note.write(
        "SECOND GEOMETRY PASS (brief §49) - placeholder materials only\n"
        "Layout: createABCBuildingBlockout.py (approved 2026-09-21, Side Street corrected to the west end).\n"
        f"Tower: floors 1-{DETAIL_TOWER_FLOORS} use ABC_TowerBay_Module_Detail; above use ABC_TowerBay_Module.\n"
        "Clints: CL_Door pivots on its west jamb; +Z rotation swings it outward. Hardware is parented to it.\n"
        "GLB excludes *_PLACEHOLDER lettering, *_GUIDE, review helpers, cameras and lights.\n"
        "Deferred: textures, emissive canopy/neon, Clints interior (CL_Interior_FINAL), LODs.\n"
    )


bo_build_podium = bo.build_podium
bo_build_lower_byrom = bo.build_lower_byrom_and_side_street


def main():
    bo.build_tower = build_tower
    bo.build_podium = build_podium
    bo.build_canopy = build_canopy
    bo.build_clints = build_clints
    bo.build_rear_wing = build_rear_wing
    bo.build_lower_byrom_and_side_street = build_lower_byrom_and_side_street

    master = bo.clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    mats = bo.create_materials()
    cols = bo.make_collections(master)
    door = bo.build_all(mats, cols)
    cameras = bo.setup_review_scene(mats, master)
    cameras += add_close_cameras(bpy.data.collections["ABC_BlockoutCameras"])
    bpy.context.view_layer.update()
    bo.validate()
    save_notes()

    render_all(cameras, door)
    scene.camera = cameras[0]
    count = export_glb()
    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), check_existing=False)
    print(f"Saved {BLEND_PATH}")
    reimport_check(count)


if __name__ == "__main__":
    main()
