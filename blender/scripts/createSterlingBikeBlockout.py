"""Build the Sterling Bikes reusable geometry blockout and seven review renders.

Reference-led first pass only. This intentionally stops before detailed geometry,
textures, decals, dirt, lighting behaviour, and runtime GLB export.

Run from the repository root:
  /Applications/Blender.app/Contents/MacOS/Blender --background \
    --python blender/scripts/createSterlingBikeBlockout.py
"""

from __future__ import annotations

import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "blender" / "source" / "sterling-bike"
RENDER_DIR = ROOT / "renders" / "sterling-bike-blockout"
BLEND_PATH = SOURCE_DIR / "sterling_bike_blockout.blend"

REAR_X = -0.62
FRONT_X = 0.69
AXLE_Z = 0.355
WHEEL_R = 0.355
TYRE_R = 0.030
STATION_X = 6.0
DOCK_SPACING = 0.94


def reset_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                       bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)


def collection(name, parent=None):
    col = bpy.data.collections.new(name)
    if parent:
        parent.children.link(col)
    else:
        bpy.context.scene.collection.children.link(col)
    return col


def move_to_collection(obj, col):
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    col.objects.link(obj)


def material(name, color, metallic=0.0, roughness=0.72):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def parent_keep(obj, parent):
    world = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = world


def empty(name, location, col, parent=None, display="PLAIN_AXES", size=0.14):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = display
    obj.empty_display_size = size
    col.objects.link(obj)
    if parent:
        # New datablock objects can expose a stale identity matrix until the
        # dependency graph updates. Build the desired world matrix explicitly.
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
        obj.matrix_world = Matrix.Translation(Vector(location))
    else:
        obj.location = location
    return obj


def bevel(obj, width=0.015, segments=2):
    mod = obj.modifiers.new("Blockout edge softness", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    return obj


def cube(name, location, scale, mat, col, parent=None, bevel_width=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(obj, col)
    obj.data.materials.append(mat)
    if bevel_width:
        bevel(obj, bevel_width)
    if parent:
        parent_keep(obj, parent)
    return obj


def uv_sphere(name, location, scale, mat, col, parent=None, segments=24, rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(obj, col)
    obj.data.materials.append(mat)
    if parent:
        parent_keep(obj, parent)
    return obj


def cylinder(name, location, radius, depth, mat, col, rotation=(0, 0, 0),
             parent=None, vertices=16, bevel_width=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth,
                                       location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    move_to_collection(obj, col)
    obj.data.materials.append(mat)
    if bevel_width:
        bevel(obj, bevel_width)
    if parent:
        parent_keep(obj, parent)
    return obj


def beam(name, start, end, radius, mat, col, parent=None, vertices=12):
    start, end = Vector(start), Vector(end)
    delta = end - start
    obj = cylinder(name, (start + end) * 0.5, radius, delta.length, mat, col,
                   parent=parent, vertices=vertices)
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(delta.normalized())
    return obj


def curve_tube(name, points, radius, mat, col, parent=None, resolution=1):
    data = bpy.data.curves.new(name + "_Curve", "CURVE")
    data.dimensions = "3D"
    data.resolution_u = resolution
    data.bevel_depth = radius
    data.bevel_resolution = 1
    spline = data.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, co in zip(spline.points, points):
        point.co = (*co, 1.0)
    obj = bpy.data.objects.new(name, data)
    col.objects.link(obj)
    obj.data.materials.append(mat)
    if parent:
        parent_keep(obj, parent)
    return obj


def extruded_xz(name, outline, depth, mat, col, parent=None, bevel_width=0.0):
    """Create a closed prism from an X/Z outline, extruded along Y."""
    half = depth * 0.5
    vertices = [(x, -half, z) for x, z in outline] + [(x, half, z) for x, z in outline]
    count = len(outline)
    faces = [tuple(range(count - 1, -1, -1)), tuple(range(count, count * 2))]
    for index in range(count):
        nxt = (index + 1) % count
        faces.append((index, nxt, count + nxt, count + index))
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    obj.data.materials.append(mat)
    if bevel_width:
        bevel(obj, bevel_width)
    if parent:
        parent_keep(obj, parent)
    return obj


def torus(name, location, major_radius, minor_radius, mat, col, parent=None,
          major_segments=32, minor_segments=8):
    bpy.ops.mesh.primitive_torus_add(major_segments=major_segments,
                                    minor_segments=minor_segments,
                                    major_radius=major_radius,
                                    minor_radius=minor_radius,
                                    location=location,
                                    rotation=(math.pi / 2, 0, 0))
    obj = bpy.context.object
    obj.name = name
    move_to_collection(obj, col)
    obj.data.materials.append(mat)
    if parent:
        parent_keep(obj, parent)
    return obj


def make_wheel(prefix, x, root, col, mats, driven=False):
    tyre = torus(prefix + "_Tyre", (x, 0, AXLE_Z), WHEEL_R - TYRE_R, TYRE_R,
                 mats["rubber"], col, root)
    tyre["sterling_role"] = "rotating-wheel"
    torus(prefix + "_Rim", (x, 0, AXLE_Z), WHEEL_R - 0.060, 0.010,
          mats["metal"], col, root, 28, 6)
    hub_r = 0.055 if driven else 0.035
    cylinder(prefix + ("_MotorHub" if driven else "_Hub"), (x, 0, AXLE_Z), hub_r,
             0.115 if driven else 0.09, mats["dark_metal"], col,
             rotation=(math.pi / 2, 0, 0), parent=root, vertices=20)
    for side_index, y in enumerate((-0.035, 0.035)):
        for index in range(10):
            angle = 2 * math.pi * index / 10 + side_index * 0.12
            rim_point = (x + math.cos(angle) * (WHEEL_R - 0.075), y,
                         AXLE_Z + math.sin(angle) * (WHEEL_R - 0.075))
            beam(f"{prefix}_Spoke_{side_index}_{index:02d}", (x, y, AXLE_Z), rim_point,
                 0.0022, mats["metal"], col, root, 6)
    # Two physically raised reflector blocks; final reflective treatment is deferred.
    for side, y in (("L", -0.044), ("R", 0.044)):
        refl = cube(f"{prefix}_Reflector_{side}", (x - 0.02, y, AXLE_Z - 0.235),
                    (0.15, 0.012, 0.035), mats["reflector"], col, root, 0.006)
        refl.rotation_euler.y = -0.08


def build_bike(mats):
    bike_col = collection("STERLING_BIKE_MASTER")
    root = empty("STERLING_BIKE_MASTER", (0, 0, 0), bike_col, display="CUBE", size=0.18)
    root["asset_type"] = "sterling-bike-blockout"
    root["forward_axis"] = "+X"
    root["units"] = "metres"

    rear_root = empty("SB_RearWheel", (REAR_X, 0, AXLE_Z), bike_col, root,
                      display="CIRCLE", size=WHEEL_R)
    rear_root["pivot"] = "rear axle"
    make_wheel("SB_RearWheel", REAR_X, rear_root, bike_col, mats, driven=True)

    steering = empty("SB_SteeringRoot", (0.48, 0, 0.79), bike_col, root,
                     display="ARROWS", size=0.20)
    steering["pivot"] = "head-tube steering axis"
    front_root = empty("SB_FrontWheel", (FRONT_X, 0, AXLE_Z), bike_col, steering,
                       display="CIRCLE", size=WHEEL_R)
    front_root["pivot"] = "front axle"
    make_wheel("SB_FrontWheel", FRONT_X, front_root, bike_col, mats, driven=False)

    # Main flattened fleet-specific e-bike frame shell and low step-through structure.
    extruded_xz("SB_Frame_BatteryShell",
                [(-0.08, 0.30), (0.17, 0.31), (0.53, 0.79), (0.43, 0.84),
                 (0.08, 0.47), (-0.18, 0.43)],
                0.105, mats["frame"], bike_col, root, 0.025)
    extruded_xz("SB_Frame_BatteryAccessPanel",
                [(0.10, 0.36), (0.20, 0.37), (0.44, 0.72), (0.40, 0.76),
                 (0.18, 0.49), (0.04, 0.45)],
                0.112, mats["frame_light"], bike_col, root, 0.008)
    beam("SB_SeatTube", (-0.16, 0, 0.34), (-0.20, 0, 0.89), 0.050,
         mats["frame"], bike_col, root, 16)
    beam("SB_RearStay_Left", (-0.18, -0.052, 0.43), (REAR_X, -0.052, AXLE_Z),
         0.025, mats["frame"], bike_col, root)
    beam("SB_RearStay_Right", (-0.18, 0.052, 0.43), (REAR_X, 0.052, AXLE_Z),
         0.025, mats["frame"], bike_col, root)
    beam("SB_Chainstay_Left", (-0.05, -0.052, 0.30), (REAR_X, -0.052, AXLE_Z),
         0.026, mats["frame"], bike_col, root)
    beam("SB_Chainstay_Right", (-0.05, 0.052, 0.30), (REAR_X, 0.052, AXLE_Z),
         0.026, mats["frame"], bike_col, root)
    cylinder("SB_HeadTube", (0.49, 0, 0.78), 0.064, 0.24, mats["frame"], bike_col,
             rotation=(0, -0.13, 0), parent=root, vertices=16, bevel_width=0.012)

    # Rear enclosure: two outer housings and separate inset branding surfaces.
    cover_outline = [(-0.96, 0.33), (-0.93, 0.61), (-0.78, 0.78), (-0.54, 0.82),
                     (-0.28, 0.74), (-0.18, 0.53), (-0.22, 0.30), (-0.44, 0.27),
                     (-0.77, 0.25)]
    inset_outline = [(-0.89, 0.39), (-0.86, 0.59), (-0.73, 0.72), (-0.53, 0.76),
                     (-0.33, 0.68), (-0.25, 0.52), (-0.28, 0.36), (-0.48, 0.32),
                     (-0.75, 0.31)]
    for side, y in (("Left", -0.075), ("Right", 0.075)):
        outer = extruded_xz(f"SB_RearWheelCover_{side}", cover_outline, 0.028,
                            mats["basket"], bike_col, root, 0.018)
        outer.location.y = y
        panel = extruded_xz(f"SB_Branding_RearCover_{side}", inset_outline, 0.010,
                            mats["rear_panel"], bike_col, root, 0.012)
        panel.location.y = y + (-0.020 if side == "Left" else 0.020)
    # Separate rear mudguard retains a visible air gap from tyre and enclosure.
    mud_points = []
    for index in range(19):
        angle = math.radians(18 + index * 8.0)
        mud_points.append((REAR_X + math.cos(angle) * 0.392, 0,
                           AXLE_Z + math.sin(angle) * 0.392))
    curve_tube("SB_RearMudguard", mud_points, 0.020, mats["basket"], bike_col, root)

    # Rear light integrated at the shroud's back edge.
    housing = cube("SB_RearLightHousing", (-0.945, 0, 0.585), (0.035, 0.130, 0.165),
                   mats["basket"], bike_col, root, 0.012)
    lens = cube("SB_RearLightLens", (-0.967, 0, 0.595), (0.014, 0.102, 0.120),
                mats["red_lens"], bike_col, root, 0.010)
    empty("SB_RearLightAnchor", (-0.98, 0, 0.595), bike_col, root, "SPHERE", 0.06)

    # Drivetrain and separately pivoted crank/pedals.
    crank_root = empty("SB_CrankRoot", (-0.02, 0, 0.30), bike_col, root,
                       display="CIRCLE", size=0.16)
    crank_root["pivot"] = "crank spindle"
    cylinder("SB_CrankHousing", (-0.02, 0, 0.30), 0.090, 0.115, mats["basket"], bike_col,
             rotation=(math.pi / 2, 0, 0), parent=crank_root, vertices=20)
    torus("SB_ChainringGuard", (-0.02, -0.070, 0.30), 0.115, 0.018,
          mats["basket"], bike_col, crank_root, 24, 6)
    for side, y, phase in (("Left", -0.095, 1), ("Right", 0.095, -1)):
        start = (-0.02, y, 0.30)
        end = (-0.02 + 0.16 * phase, y, 0.26)
        beam(f"SB_Crank_{side}", start, end, 0.014, mats["metal"], bike_col,
             crank_root, 10)
        pedal_root = empty(f"SB_Pedal_{side}", end, bike_col, crank_root,
                           display="CUBE", size=0.08)
        cube(f"SB_PedalBody_{side}", end, (0.12, 0.075, 0.025), mats["basket"],
             bike_col, pedal_root, 0.008)
    curve_tube("SB_ChainPath", [(-0.04, -0.075, 0.395), (-0.58, -0.075, 0.405),
                                (-0.62, -0.075, 0.315), (-0.06, -0.075, 0.205)],
               0.006, mats["dark_metal"], bike_col, root)
    extruded_xz("SB_ChainGuard", [(-0.68, 0.27), (-0.66, 0.40), (0.02, 0.43),
                                  (0.13, 0.35), (0.06, 0.22), (-0.56, 0.21)],
                0.035, mats["basket"], bike_col, root, 0.015).location.y = -0.090

    # Seat and adjustable post.
    cylinder("SB_SeatPost", (-0.20, 0, 0.94), 0.025, 0.34, mats["metal"], bike_col,
             rotation=(0, -0.05, 0), parent=root, vertices=14)
    saddle = uv_sphere("SB_Saddle", (-0.22, 0, 1.105), (0.155, 0.095, 0.045),
                       mats["basket"], bike_col, root, 24, 10)
    saddle.rotation_euler.y = -0.08

    # Front fork, steering stem, upright swept handlebar and controls.
    for side, y in (("Left", -0.060), ("Right", 0.060)):
        beam(f"SB_Fork_{side}", (0.51, y, 0.75), (FRONT_X, y, AXLE_Z), 0.025,
             mats["metal"], bike_col, steering, 12)
    cylinder("SB_Stem", (0.47, 0, 1.015), 0.038, 0.46, mats["metal"], bike_col,
             rotation=(0, -0.10, 0), parent=steering, vertices=16)
    curve_tube("SB_Handlebar", [(0.45, -0.30, 1.22), (0.46, -0.18, 1.27),
                                (0.47, 0, 1.24), (0.46, 0.18, 1.27),
                                (0.45, 0.30, 1.22)],
               0.020, mats["metal"], bike_col, steering)
    for side, y in (("Left", -0.32), ("Right", 0.32)):
        cylinder(f"SB_Grip_{side}", (0.45, y, 1.22), 0.027, 0.13, mats["basket"],
                 bike_col, rotation=(math.pi / 2, 0, 0), parent=steering, vertices=14)
        lever_y = y * 0.78
        beam(f"SB_BrakeLever_{side}", (0.46, lever_y, 1.25),
             (0.50, lever_y, 1.17), 0.007, mats["dark_metal"], bike_col, steering, 8)
    curve_tube("SB_Cable_Left", [(0.47, -0.20, 1.24), (0.54, -0.13, 1.04),
                                 (0.58, -0.08, 0.77)], 0.004,
               mats["basket"], bike_col, steering)
    curve_tube("SB_Cable_Right", [(0.47, 0.20, 1.24), (0.55, 0.13, 1.01),
                                  (0.59, 0.08, 0.72)], 0.004,
               mats["basket"], bike_col, steering)

    # Long front mudguard.
    front_mud = []
    for index in range(22):
        angle = math.radians(8 + index * 7.2)
        front_mud.append((FRONT_X + math.cos(angle) * 0.395, 0,
                          AXLE_Z + math.sin(angle) * 0.395))
    curve_tube("SB_FrontMudguard", front_mud, 0.021, mats["basket"], bike_col, steering)

    # Open tapered basket: bottom, front/back rails and spaced side slats.
    basket_root = empty("SB_Basket", (0.72, 0, 0.93), bike_col, steering,
                        display="CUBE", size=0.14)
    cube("SB_BasketBottom", (0.70, 0, 0.87), (0.43, 0.43, 0.025), mats["basket"],
         bike_col, basket_root, 0.008)
    for x in (0.49, 0.91):
        cube(f"SB_BasketWall_{'Rear' if x < .7 else 'Front'}", (x, 0, 1.01),
             (0.025, 0.48, 0.28), mats["basket"], bike_col, basket_root, 0.018)
    for side, y in (("Left", -0.235), ("Right", 0.235)):
        for index, x in enumerate((0.53, 0.62, 0.71, 0.80, 0.89)):
            beam(f"SB_Basket_{side}_Slat_{index:02d}", (x, y * 0.90, 0.88),
                 (x, y, 1.15), 0.010, mats["basket"], bike_col, basket_root, 8)
        beam(f"SB_Basket_{side}_TopRail", (0.48, y, 1.15), (0.93, y, 1.15),
             0.015, mats["basket"], bike_col, basket_root, 10)
    beam("SB_BasketMount_Left", (0.53, -0.12, 0.88), (0.49, -0.08, 0.73),
         0.014, mats["dark_metal"], bike_col, steering)
    beam("SB_BasketMount_Right", (0.53, 0.12, 0.88), (0.49, 0.08, 0.73),
         0.014, mats["dark_metal"], bike_col, steering)

    # Light housings and decal-ready surfaces.
    cube("SB_FrontLightHousing", (0.47, 0, 1.02), (0.10, 0.15, 0.13),
         mats["basket"], bike_col, steering, 0.018)
    cube("SB_FrontLightLens", (0.525, 0, 1.02), (0.014, 0.115, 0.085),
         mats["lens"], bike_col, steering, 0.010)
    empty("SB_FrontLightAnchor", (0.55, 0, 1.02), bike_col, steering, "SPHERE", 0.06)
    cube("SB_Branding_DownTube", (0.285, -0.061, 0.575), (0.31, 0.008, 0.055),
         mats["rear_panel"], bike_col, root, 0.006).rotation_euler.y = -0.67
    cube("SB_FleetNumber_Surface", (-0.36, -0.068, 0.31), (0.19, 0.008, 0.045),
         mats["reflector"], bike_col, root, 0.006)

    dock_anchor = empty("SB_DockAnchor", (0, 0, 0), bike_col, root, "ARROWS", 0.12)
    dock_anchor["snap_role"] = "bike-to-dock"
    return bike_col, root


def build_dock(mats):
    dock_col = collection("STERLING_DOCK_MASTER")
    root = empty("STERLING_DOCK_MASTER", (0, 0, 0), dock_col, display="CUBE", size=0.18)
    root["asset_type"] = "sterling-dock-blockout"
    cube("SD_Baseplate", (0.05, 0, 0.025), (0.72, 0.42, 0.05), mats["dock"],
         dock_col, root, 0.025)
    # Reference dock has a substantial tall tapered side body, not a flat sign.
    body = extruded_xz("SD_UprightHousing",
                       [(-0.06, 0.04), (0.28, 0.04), (0.34, 0.18), (0.30, 0.91),
                        (0.18, 1.05), (0.04, 1.00), (-0.10, 0.73)],
                       0.32, mats["dock"], dock_col, root, 0.025)
    cube("SD_BrandingSurface", (0.255, -0.168, 0.55), (0.17, 0.014, 0.52),
         mats["frame"], dock_col, root, 0.015)
    cube("SD_ReflectiveStrip", (0.245, -0.173, 0.89), (0.18, 0.012, 0.065),
         mats["reflector"], dock_col, root, 0.012)
    # Open U-shaped channel grips the front tyre while leaving the bike complete.
    cube("SD_WheelChannelBase", (-0.12, 0, 0.075), (0.56, 0.13, 0.08),
         mats["dark_metal"], dock_col, root, 0.015)
    for side, y in (("Left", -0.105), ("Right", 0.105)):
        cube(f"SD_WheelGuide_{side}", (-0.12, y, 0.16), (0.58, 0.055, 0.19),
             mats["dock"], dock_col, root, 0.018)
    cube("SD_UpperLockInterface", (0.08, 0, 0.63), (0.18, 0.24, 0.16),
         mats["dark_metal"], dock_col, root, 0.025)
    cube("SD_LockJaw_Left", (-0.025, -0.105, 0.57), (0.22, 0.050, 0.22),
         mats["dark_metal"], dock_col, root, 0.015)
    cube("SD_LockJaw_Right", (-0.025, 0.105, 0.57), (0.22, 0.050, 0.22),
         mats["dark_metal"], dock_col, root, 0.015)
    for index, (x, y) in enumerate(((-0.25, -0.14), (-0.25, 0.14),
                                    (0.29, -0.14), (0.29, 0.14))):
        cylinder(f"SD_BaseBolt_{index + 1:02d}", (x, y, 0.057), 0.018, 0.012,
                 mats["metal"], dock_col, parent=root, vertices=10)
    anchor = empty("SD_BikeDockAnchor", (-FRONT_X, 0, 0), dock_col, root,
                   "ARROWS", 0.14)
    anchor["snap_role"] = "dock-to-bike"
    empty("SD_InteractionAnchor", (-0.25, -0.85, 0), dock_col, root,
          "PLAIN_AXES", 0.20)
    return dock_col, root


def instance_collection(name, source, location, col, parent=None):
    obj = bpy.data.objects.new(name, None)
    obj.instance_type = "COLLECTION"
    obj.instance_collection = source
    if parent:
        obj.parent = parent
    obj.location = location
    col.objects.link(obj)
    return obj


def build_station(bike_col, dock_col):
    station = collection("STERLING_STATION_REFERENCE")
    root = empty("STERLING_STATION_REFERENCE", (STATION_X, 0, 0), station,
                 display="CUBE", size=0.24)
    root["occupancy"] = "reference-only; game-controlled later"
    docks, bikes = [], []
    for index, y in enumerate((-DOCK_SPACING, 0, DOCK_SPACING), 1):
        dock = instance_collection(f"Dock_{index:02d}", dock_col, (0, y, 0), station, root)
        bike = instance_collection(f"Bike_{index:02d}", bike_col,
                                   (-FRONT_X, y, 0), station, root)
        dock["module_index"] = index
        bike["fleet_number_placeholder"] = f"STERLING_{index:04d}"
        docks.append(dock)
        bikes.append(bike)
    return station, root, docks, bikes


def setup_scene(mats):
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.engine = "BLENDER_EEVEE_NEXT" if hasattr(bpy.types, "SceneEEVEE") is False else "BLENDER_EEVEE"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.world.color = (0.025, 0.030, 0.040)

    review = collection("REVIEW_ONLY")
    ground = cube("Review_Ground", (3.0, 0, -0.045), (12.5, 7.5, 0.08),
                  mats["ground"], review, bevel_width=0.01)
    ground["export_exclude"] = True
    bpy.ops.object.light_add(type="AREA", location=(1.8, -3.0, 5.4))
    key = bpy.context.object
    key.name = "Review_Key"
    key.data.energy = 1050
    key.data.shape = "DISK"
    key.data.size = 4.0
    move_to_collection(key, review)
    point_camera(key, (2.0, 0, 0.65))
    bpy.ops.object.light_add(type="AREA", location=(-3.0, 3.8, 2.6))
    fill = bpy.context.object
    fill.name = "Review_Fill"
    fill.data.energy = 700
    fill.data.size = 3.5
    move_to_collection(fill, review)
    point_camera(fill, (0.0, 0, 0.65))
    bpy.ops.object.light_add(type="AREA", location=(7.5, 1.0, 4.2))
    station_light = bpy.context.object
    station_light.name = "Review_StationFill"
    station_light.data.energy = 950
    station_light.data.size = 4.0
    move_to_collection(station_light, review)
    point_camera(station_light, (STATION_X - 0.2, 0, 0.6))
    return review


def point_camera(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def render_view(filename, camera_location, target, focal_length=58):
    scene = bpy.context.scene
    if not scene.camera:
        bpy.ops.object.camera_add()
        scene.camera = bpy.context.object
        scene.camera.name = "Review_Camera"
    camera = scene.camera
    camera.location = camera_location
    camera.data.lens = focal_length
    point_camera(camera, target)
    scene.render.filepath = str(RENDER_DIR / filename)
    bpy.ops.render.render(write_still=True)
    print(f"Rendered {scene.render.filepath}")


def set_collection_geometry_hidden(col, hidden):
    """Hide source geometry for isolated master renders; empties do not render."""
    for obj in col.objects:
        if obj.type != "EMPTY":
            obj.hide_render = hidden


def validate(bike_root, dock_root, bikes, docks):
    bpy.context.view_layer.update()
    assert tuple(round(v, 4) for v in bike_root.location) == (0.0, 0.0, 0.0)
    assert tuple(round(v, 4) for v in dock_root.location) == (0.0, 0.0, 0.0)
    required = {
        "SB_FrontWheel", "SB_RearWheel", "SB_SteeringRoot", "SB_CrankRoot",
        "SB_Pedal_Left", "SB_Pedal_Right", "SB_Basket", "SB_DockAnchor",
        "SB_FrontLightAnchor", "SB_RearLightAnchor", "SD_BikeDockAnchor",
        "SD_InteractionAnchor", "SD_BrandingSurface",
    }
    missing = sorted(name for name in required if name not in bpy.data.objects)
    assert not missing, f"Missing required objects: {missing}"
    assert all(obj.instance_collection is not None for obj in bikes + docks)
    assert all(obj.parent and obj.parent.name == "STERLING_STATION_REFERENCE"
               for obj in bikes + docks)
    assert len({id(obj.instance_collection) for obj in bikes}) == 1
    assert len({id(obj.instance_collection) for obj in docks}) == 1
    bike_anchor = bpy.data.objects["SB_DockAnchor"]
    dock_anchor = bpy.data.objects["SD_BikeDockAnchor"]
    assert bike_anchor.matrix_world.translation.length < 1e-6
    assert abs(dock_anchor.matrix_world.translation.x + FRONT_X) < 1e-6, (
        f"Dock anchor world X is {dock_anchor.matrix_world.translation.x:.6f}"
    )
    print("Validation passed: reusable masters, pivots, anchors and linked station instances.")


def main():
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    reset_scene()
    mats = {
        "frame": material("MAT_SB_Frame_PLACEHOLDER", (0.83, 0.67, 0.08), 0.05, 0.60),
        "frame_light": material("MAT_SB_FrameLight_PLACEHOLDER", (0.95, 0.80, 0.16), 0.02, 0.62),
        "metal": material("MAT_SB_Metal_PLACEHOLDER", (0.42, 0.46, 0.48), 0.60, 0.36),
        "dark_metal": material("MAT_SB_DarkMetal_PLACEHOLDER", (0.10, 0.12, 0.13), 0.45, 0.48),
        "rubber": material("MAT_SB_Rubber_PLACEHOLDER", (0.018, 0.022, 0.024), 0.0, 0.92),
        "rear_panel": material("MAT_SB_RearPanel_PLACEHOLDER", (0.53, 0.78, 0.74), 0.0, 0.72),
        "basket": material("MAT_SB_Basket_PLACEHOLDER", (0.035, 0.045, 0.050), 0.0, 0.82),
        "lens": material("MAT_SB_LightLens_PLACEHOLDER", (0.75, 0.82, 0.76), 0.0, 0.24),
        "red_lens": material("MAT_SB_RearLightLens_PLACEHOLDER", (0.42, 0.015, 0.015), 0.0, 0.28),
        "reflector": material("MAT_SB_Reflector_PLACEHOLDER", (0.78, 0.76, 0.62), 0.0, 0.35),
        "dock": material("MAT_SD_Dock_PLACEHOLDER", (0.16, 0.18, 0.19), 0.35, 0.62),
        "ground": material("MAT_ReviewGround", (0.16, 0.17, 0.18), 0.0, 0.92),
    }
    bike_col, bike_root = build_bike(mats)
    dock_col, dock_root = build_dock(mats)
    station, station_root, docks, bikes = build_station(bike_col, dock_col)
    setup_scene(mats)
    validate(bike_root, dock_root, bikes, docks)

    # Keep the middle bike addressable and prove the empty dock in View G.
    bikes[1]["review_middle_bike"] = True
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

    # A-D: isolate the reusable bike master from the co-located dock master.
    set_collection_geometry_hidden(dock_col, True)
    for obj in docks + bikes:
        obj.hide_render = True
    render_view("A-bike-left-side.png", (0.0, -4.8, 0.95), (0.0, 0, 0.61), 66)
    render_view("B-bike-right-side.png", (0.0, 4.8, 0.95), (0.0, 0, 0.61), 66)
    render_view("C-front-three-quarter-basket.png", (3.05, -3.45, 1.75),
                (0.18, 0, 0.72), 58)
    render_view("D-rear-three-quarter-enclosure.png", (-3.15, 3.25, 1.55),
                (-0.10, 0, 0.63), 58)

    # E: show exactly one linked dock/bike module.
    set_collection_geometry_hidden(dock_col, False)
    docks[0].hide_render = False
    bikes[0].hide_render = False
    render_view("E-bike-docked.png", (8.65, -3.65, 1.55),
                (STATION_X - 0.20, -DOCK_SPACING, 0.56), 62)
    for obj in docks + bikes:
        obj.hide_render = False
    render_view("F-three-bike-station.png", (8.85, -5.55, 2.15),
                (STATION_X - 0.15, 0, 0.58), 55)

    # G: remove only the station's middle bike instance, leaving the dock untouched.
    bikes[1].hide_render = True
    render_view("G-station-middle-bike-removed.png", (8.85, -5.55, 2.15),
                (STATION_X - 0.15, 0, 0.58), 55)
    bikes[1].hide_render = False
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    print(f"Saved {BLEND_PATH}")


if __name__ == "__main__":
    main()
