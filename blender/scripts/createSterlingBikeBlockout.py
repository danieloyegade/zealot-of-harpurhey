"""Build the Sterling Bikes reusable geometry and eight review renders.

Second geometry pass, rebuilt against IMG_8911-8917: swept step-through frame,
D-shaped rear clamshell with outboard stays, moulded basket tub, raked steering
axis and the slim J-profile side-post dock. Textures, decals, dirt and lighting
behaviour are still deferred; runtime export is exportSterlingBikeBlockout.py.

Run from the repository root:
  /Applications/Blender.app/Contents/MacOS/Blender --background \
    --python blender/scripts/createSterlingBikeBlockout.py
"""

from __future__ import annotations

import math
from pathlib import Path

import bmesh
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
# Head-tube steering axis: a point on it and its rake from vertical (radians).
HEAD_ANGLE = 0.30
HEAD_AXIS_POINT = (0.49, 0.93)
CHAIN_Y = -0.066
SEAT_TUBE_BASE = (-0.135, 0, 0.30)
SEAT_TUBE_TOP = (-0.205, 0, 0.90)
# Rear enclosure D shape: arc centre X, flat base Z, and arc radii.
COVER_CX = -0.595
COVER_BASE_Z = 0.40
COVER_RX = 0.425
COVER_RZ = 0.42
# Superellipse power: squarer shoulders than a circle, as in IMG_8911.
COVER_POWER = 2.4
# Dock side post: centre offset beside the front wheel, and its thickness.
DOCK_SLAB_Y = 0.13
DOCK_SLAB_T = 0.09


def head_axis(t):
    """Point on the steering axis, `t` metres along it from HEAD_AXIS_POINT."""
    return Vector((HEAD_AXIS_POINT[0] - math.sin(HEAD_ANGLE) * t, 0.0,
                   HEAD_AXIS_POINT[1] + math.cos(HEAD_ANGLE) * t))


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
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
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


def smooth(obj, angle=40):
    """Smooth-shade a mesh but keep hard edges above `angle` degrees."""
    if obj.type == "MESH":
        obj.data.shade_smooth()
        obj.data.set_sharp_from_angle(angle=math.radians(angle))
    return obj


def mesh_object(name, vertices, faces, mat, col, parent=None, smooth_angle=40):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata([tuple(v) for v in vertices], [], faces)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    obj.data.materials.append(mat)
    smooth(obj, smooth_angle)
    if parent:
        parent_keep(obj, parent)
    return obj


def loft(name, rings, mat, col, parent=None, cap_start=True, cap_end=True,
         smooth_angle=40):
    """Skin equal-length vertex rings into a closed solid."""
    count = len(rings[0])
    vertices = [v for ring in rings for v in ring]
    faces = []
    for ring_index in range(len(rings) - 1):
        a, b = ring_index * count, (ring_index + 1) * count
        for j in range(count):
            k = (j + 1) % count
            faces.append((a + j, a + k, b + k, b + j))
    if cap_start:
        faces.append(tuple(range(count - 1, -1, -1)))
    if cap_end:
        last = (len(rings) - 1) * count
        faces.append(tuple(range(last, last + count)))
    return mesh_object(name, vertices, faces, mat, col, parent, smooth_angle)


def rounded_rect(half_u, half_v, radius, segments=3):
    """Closed rounded-rectangle profile, counter-clockwise, fixed point count."""
    radius = min(radius, half_u, half_v)
    points = []
    corners = ((half_u - radius, half_v - radius, 0.0),
               (-half_u + radius, half_v - radius, 90.0),
               (-half_u + radius, -half_v + radius, 180.0),
               (half_u - radius, -half_v + radius, 270.0))
    for cu, cv, start in corners:
        for step in range(segments + 1):
            angle = math.radians(start + 90.0 * step / segments)
            points.append((cu + math.cos(angle) * radius, cv + math.sin(angle) * radius))
    return points


def ellipse_profile(half_u, half_v, count=12):
    return [(math.cos(2 * math.pi * i / count) * half_u,
             math.sin(2 * math.pi * i / count) * half_v) for i in range(count)]


def sweep(name, path, profile, mat, col, parent=None, ref=(0, 1, 0), scales=None,
          smooth_angle=50):
    """Sweep a closed 2D profile along a polyline.

    Profile U follows `ref` projected off the tangent; V is tangent x U. Per-point
    `scales` are (u, v) multipliers, so tubes can taper or swell.
    """
    path = [Vector(p) for p in path]
    rings = []
    for index, point in enumerate(path):
        if index == 0:
            tangent = path[1] - path[0]
        elif index == len(path) - 1:
            tangent = path[-1] - path[-2]
        else:
            tangent = ((path[index + 1] - point).normalized()
                       + (point - path[index - 1]).normalized())
        tangent.normalize()
        reference = Vector(ref)
        u_axis = reference - tangent * reference.dot(tangent)
        if u_axis.length < 1e-6:
            u_axis = Vector((0, 0, 1)) - tangent * tangent.z
        u_axis.normalize()
        v_axis = tangent.cross(u_axis)
        su, sv = scales[index] if scales else (1.0, 1.0)
        rings.append([point + u_axis * (u * su) + v_axis * (v * sv) for u, v in profile])
    return loft(name, rings, mat, col, parent, smooth_angle=smooth_angle)


def superellipse(angle, power):
    """Unit superellipse point; power 2 is a circle, higher squares the shoulders."""
    c, s = math.cos(angle), math.sin(angle)
    return (math.copysign(abs(c) ** (2 / power), c), math.copysign(abs(s) ** (2 / power), s))


def arc_points(cx, cz, rx, rz, start_deg, end_deg, count, y=0.0, power=2.0):
    points = []
    for i in range(count):
        u, v = superellipse(math.radians(start_deg + (end_deg - start_deg) * i / (count - 1)),
                            power)
        points.append((cx + u * rx, y, cz + v * rz))
    return points


def mudguard_profile(half_width, crown, thickness, count=7):
    """Crescent section: V is toward the wheel centre, so the crown bulges out."""
    outer = [(u, -crown * (1 - (u / half_width) ** 2))
             for u in (-half_width + 2 * half_width * i / (count - 1) for i in range(count))]
    inner = [(u, v + thickness) for u, v in reversed(outer)]
    return outer + inner


def tub(name, center, top_half, bottom_half, height, corner, wall, lip, mat, col,
        parent=None):
    """Open-topped moulded tub with wall thickness and a rolled lip."""
    cx, cy, z0 = center
    z1 = z0 + height

    def ring(half, radius, z):
        return [Vector((cx + u, cy + v, z))
                for u, v in rounded_rect(half[0], half[1], radius, 3)]

    top_corner = corner
    bottom_corner = corner * 0.8
    rings = [
        ring(bottom_half, bottom_corner, z0),
        ring(top_half, top_corner, z1 - 0.022),
        ring((top_half[0] + lip, top_half[1] + lip), top_corner + lip, z1 - 0.022),
        ring((top_half[0] + lip, top_half[1] + lip), top_corner + lip, z1),
        ring((top_half[0] - wall, top_half[1] - wall), top_corner - wall, z1),
        ring((bottom_half[0] - wall, bottom_half[1] - wall), bottom_corner - wall,
             z0 + wall),
    ]
    return loft(name, rings, mat, col, parent, smooth_angle=35)


def d_outline(cx, base_z, rx, rz, samples=26, min_z=None, power=COVER_POWER):
    """X/Z outline of a D shape lying on its flat side (arc over a flat base)."""
    points = []
    for i in range(samples):
        u, v = superellipse(math.pi * i / (samples - 1), power)
        x, z = cx + u * rx, base_z + v * rz
        if min_z is None or z >= min_z:
            points.append((x, z))
    return points


def make_wheel(prefix, x, root, col, mats, driven=False):
    tyre = torus(prefix + "_Tyre", (x, 0, AXLE_Z), WHEEL_R - TYRE_R, TYRE_R,
                 mats["rubber"], col, root, 40, 10)
    smooth(tyre, 60)
    tyre["sterling_role"] = "rotating-wheel"
    # Reflective sidewall stripe, visible on both wheels in IMG_8911/8915.
    for side, y in (("L", -0.028), ("R", 0.028)):
        stripe = torus(f"{prefix}_SidewallStripe_{side}", (x, y, AXLE_Z),
                       WHEEL_R - 0.036, 0.0032, mats["reflector"], col, root, 40, 4)
        smooth(stripe, 80)
    smooth(torus(prefix + "_Rim", (x, 0, AXLE_Z), WHEEL_R - 0.058, 0.011,
                 mats["rim"], col, root, 40, 6), 80)
    hub_r, hub_depth = (0.052, 0.10) if driven else (0.046, 0.085)
    smooth(cylinder(prefix + ("_MotorHub" if driven else "_Hub"), (x, 0, AXLE_Z), hub_r,
                    hub_depth, mats["hub"], col, rotation=(math.pi / 2, 0, 0),
                    parent=root, vertices=20))
    for side_index, y in enumerate((-0.035, 0.035)):
        for index in range(14):
            angle = 2 * math.pi * index / 14 + side_index * math.pi / 14
            rim_point = (x + math.cos(angle) * (WHEEL_R - 0.068), y * 0.25,
                         AXLE_Z + math.sin(angle) * (WHEEL_R - 0.068))
            beam(f"{prefix}_Spoke_{side_index}_{index:02d}", (x, y, AXLE_Z), rim_point,
                 0.0018, mats["metal"], col, root, 4)
    if driven:
        smooth(cylinder(prefix + "_Sprocket", (x, CHAIN_Y, AXLE_Z), 0.040, 0.004,
                        mats["dark_metal"], col, rotation=(math.pi / 2, 0, 0),
                        parent=root, vertices=20))
    # Spoke reflectors lie along a spoke at mid radius, not as floating plates.
    for side, y, angle in (("L", -0.038, -1.95), ("R", 0.038, 1.2)):
        refl = cube(f"{prefix}_Reflector_{side}",
                    (x + math.cos(angle) * 0.19, y, AXLE_Z + math.sin(angle) * 0.19),
                    (0.095, 0.008, 0.024), mats["reflector"], col, root, 0.004)
        refl.rotation_euler.y = -angle


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

    # Steering root sits on the real head-tube axis and is tilted to match it, so
    # rotating its local Z steers about the correct raked axis.
    steering = empty("SB_SteeringRoot", head_axis(-0.13), bike_col, root,
                     display="ARROWS", size=0.20)
    steering.rotation_euler.y = -HEAD_ANGLE
    steering["pivot"] = "head-tube steering axis (local Z)"
    bpy.context.view_layer.update()
    front_root = empty("SB_FrontWheel", (FRONT_X, 0, AXLE_Z), bike_col, steering,
                       display="CIRCLE", size=WHEEL_R)
    front_root["pivot"] = "front axle"
    make_wheel("SB_FrontWheel", FRONT_X, front_root, bike_col, mats, driven=False)

    # --- Frame -----------------------------------------------------------------
    # One continuous swept step-through tube, flattened and swelling into the
    # battery housing toward the crank (IMG_8913/8914), rather than stepped slabs.
    down_path = [(0.52, 0, 0.81), (0.42, 0, 0.70), (0.30, 0, 0.55), (0.18, 0, 0.38),
                 (0.05, 0, 0.28), (-0.08, 0, 0.27), (-0.15, 0, 0.33)]
    down_scales = [(0.85, 1.0), (0.95, 1.0), (1.0, 1.15), (1.05, 1.5),
                   (1.1, 1.7), (1.05, 1.45), (1.0, 1.0)]
    sweep("SB_Frame_BatteryShell", down_path, rounded_rect(0.042, 0.045, 0.030, 3),
          mats["frame"], bike_col, root, scales=down_scales)
    # Access-panel seam: a slightly proud plate on the lower battery section.
    sweep("SB_Frame_BatteryAccessPanel", down_path[2:5],
          [(-0.045, -0.030), (-0.041, -0.030), (-0.041, 0.030), (-0.045, 0.030)],
          mats["frame_light"], bike_col, root,
          scales=[(1.0, 1.1), (1.05, 1.35), (1.1, 1.5)], smooth_angle=30)
    smooth(cylinder("SB_MotorHousing", (-0.02, 0, 0.30), 0.068, 0.108, mats["frame"],
                    bike_col, rotation=(math.pi / 2, 0, 0), parent=root, vertices=24))
    head_centre = head_axis(0.01)
    smooth(cylinder("SB_HeadTube", head_centre, 0.034, 0.28, mats["frame"], bike_col,
                    rotation=(0, -HEAD_ANGLE, 0), parent=root, vertices=20))
    # Welded gusset between head tube and down tube (IMG_8916).
    extruded_xz("SB_HeadTubeGusset", [(0.53, 0.80), (0.47, 0.96), (0.44, 0.90),
                                      (0.47, 0.78)],
                0.05, mats["frame"], bike_col, root, 0.01)
    beam("SB_SeatTube", SEAT_TUBE_BASE, SEAT_TUBE_TOP, 0.024, mats["frame"], bike_col,
         root, 16)
    for side, s in (("Left", -1), ("Right", 1)):
        # Seat stays sit OUTBOARD of the rear cover and cross its panel (IMG_8912).
        sweep(f"SB_RearStay_{side}",
              [(REAR_X + 0.005, s * 0.112, 0.37), (-0.24, s * 0.112, 0.760),
               (-0.197, s * 0.030, 0.810)],
              rounded_rect(0.011, 0.019, 0.009, 2), mats["frame"], bike_col, root)
        sweep(f"SB_RearStay_ReflectiveStrip_{side}",
              [(-0.54, s * 0.112, 0.448), (-0.334, s * 0.112, 0.662)],
              [(s * 0.0108, -0.006), (s * 0.0138, -0.006), (s * 0.0138, 0.006),
               (s * 0.0108, 0.006)], mats["reflector"], bike_col, root, smooth_angle=20)
        # Flattened chainstays below the cover band, carrying the fleet number.
        sweep(f"SB_Chainstay_{side}",
              [(-0.07, s * 0.040, 0.285), (-0.35, s * 0.080, 0.32),
               (REAR_X + 0.005, s * 0.100, 0.355)],
              rounded_rect(0.011, 0.020, 0.008, 2), mats["frame"], bike_col, root)
        cube(f"SB_Dropout_{side}", (REAR_X, s * 0.106, 0.362), (0.065, 0.012, 0.070),
             mats["frame"], bike_col, root, 0.008)
    cylinder("SB_RearAxleBolts", (REAR_X, 0, AXLE_Z), 0.011, 0.25, mats["metal"],
             bike_col, rotation=(math.pi / 2, 0, 0), parent=root, vertices=10)
    plate = cube("SB_FleetNumber_Surface", (-0.36, -0.094, 0.321), (0.13, 0.004, 0.032),
                 mats["reflector"], bike_col, root, 0.008)
    plate.rotation_euler.y = 0.12

    # --- Rear enclosure ----------------------------------------------------------
    # D shape on its flat side: smooth arc over the wheel, flat base just above the
    # axle so the lower wheel and spokes stay exposed (IMG_8911/8912).
    cover = d_outline(COVER_CX, COVER_BASE_Z, COVER_RX, COVER_RZ, 30)
    panel = d_outline(COVER_CX, COVER_BASE_Z, COVER_RX - 0.036, COVER_RZ - 0.036, 30,
                      min_z=COVER_BASE_Z + 0.075)
    panel = [(x, max(z, COVER_BASE_Z + 0.075)) for x, z in panel]
    for side, s in (("Left", -1), ("Right", 1)):
        outer = extruded_xz(f"SB_RearWheelCover_{side}", cover, 0.028,
                            mats["basket"], bike_col, root, 0.010)
        outer.location.y = s * 0.070
        smooth(outer, 35)
        brand = extruded_xz(f"SB_Branding_RearCover_{side}", panel, 0.008,
                            mats["rear_panel"], bike_col, root, 0.004)
        brand.location.y = s * 0.089
        smooth(brand, 35)
    # Crown closes the arc so it reads as one clamshell, not two loose plates.
    sweep("SB_RearWheelCover_Crown",
          arc_points(COVER_CX, COVER_BASE_Z, COVER_RX - 0.010, COVER_RZ - 0.010,
                     22, 150, 18, power=COVER_POWER),
          rounded_rect(0.084, 0.011, 0.008, 2), mats["basket"], bike_col, root,
          smooth_angle=60)
    # Wide channel mudguard tail below the crown, carrying the rear light.
    sweep("SB_RearMudguard",
          arc_points(REAR_X, AXLE_Z, 0.392, 0.392, 118, 188, 10),
          mudguard_profile(0.048, 0.014, 0.006), mats["basket"], bike_col, root)
    light_angle = math.radians(150)
    light_normal = (math.cos(light_angle), math.sin(light_angle))
    housing = cube("SB_RearLightHousing",
                   (REAR_X + light_normal[0] * 0.416, 0, AXLE_Z + light_normal[1] * 0.416),
                   (0.028, 0.072, 0.175), mats["basket"], bike_col, root, 0.012)
    housing.rotation_euler.y = math.radians(210)
    # Tall capsule lens recessed into the tail (IMG_8917).
    lens = uv_sphere("SB_RearLightLens",
                     (REAR_X + light_normal[0] * 0.430, 0, AXLE_Z + light_normal[1] * 0.430),
                     (0.012, 0.030, 0.072), mats["red_lens"], bike_col, root, 20, 10)
    lens.rotation_euler.y = math.radians(210)
    smooth(lens, 80)
    empty("SB_RearLightAnchor",
          (REAR_X + light_normal[0] * 0.45, 0, AXLE_Z + light_normal[1] * 0.45),
          bike_col, root, "SPHERE", 0.06)

    # --- Drivetrain ----------------------------------------------------------------
    crank_root = empty("SB_CrankRoot", (-0.02, 0, 0.30), bike_col, root,
                       display="CIRCLE", size=0.16)
    crank_root["pivot"] = "crank spindle"
    smooth(cylinder("SB_Chainring", (-0.02, CHAIN_Y, 0.30), 0.094, 0.004,
                    mats["dark_metal"], bike_col, rotation=(math.pi / 2, 0, 0),
                    parent=crank_root, vertices=28))
    # Full black ring guard around the chainring (IMG_8913/8914).
    guard = torus("SB_ChainringGuard", (-0.02, CHAIN_Y - 0.006, 0.30), 0.100, 0.013,
                  mats["basket"], bike_col, crank_root, 32, 8)
    guard.scale.y = 1.2
    smooth(guard, 80)
    for index in range(5):
        angle = 2 * math.pi * index / 5 + 0.3
        beam(f"SB_CrankSpider_{index}", (-0.02, CHAIN_Y - 0.008, 0.30),
             (-0.02 + math.cos(angle) * 0.078, CHAIN_Y - 0.008,
              0.30 + math.sin(angle) * 0.078),
             0.007, mats["metal"], bike_col, crank_root, 6)
    for side, y, angle in (("Left", -0.100, math.radians(-15)),
                           ("Right", 0.100, math.radians(165))):
        end = (-0.02 + math.cos(angle) * 0.17, y, 0.30 + math.sin(angle) * 0.17)
        arm = sweep(f"SB_Crank_{side}", [(-0.02, y, 0.30), end],
                    rounded_rect(0.008, 0.016, 0.006, 2), mats["metal"], bike_col,
                    crank_root, scales=[(1.0, 1.1), (0.9, 0.75)])
        pedal_root = empty(f"SB_Pedal_{side}", end, bike_col, crank_root,
                           display="CUBE", size=0.08)
        pedal_y = y + (-0.058 if y < 0 else 0.058)
        cylinder(f"SB_PedalSpindle_{side}", (end[0], (y + pedal_y) / 2, end[2]), 0.006,
                 abs(pedal_y - y), mats["metal"], bike_col,
                 rotation=(math.pi / 2, 0, 0), parent=pedal_root, vertices=8)
        # Black platform pedal: frame plus two grip bars.
        for bar, dx in (("Front", 0.045), ("Rear", -0.045)):
            cube(f"SB_PedalBody_{side}_{bar}", (end[0] + dx, pedal_y, end[2]),
                 (0.016, 0.100, 0.024), mats["basket"], bike_col, pedal_root, 0.005)
        for bar, dy in (("Outer", 0.046), ("Inner", -0.046)):
            cube(f"SB_PedalBody_{side}_{bar}", (end[0], pedal_y + dy, end[2]),
                 (0.100, 0.012, 0.020), mats["basket"], bike_col, pedal_root, 0.004)
    curve_tube("SB_ChainPath",
               [(-0.02, CHAIN_Y, 0.396), (REAR_X, CHAIN_Y, 0.396),
                (REAR_X - 0.042, CHAIN_Y, AXLE_Z), (REAR_X, CHAIN_Y, 0.314),
                (-0.30, CHAIN_Y, 0.232), (-0.02, CHAIN_Y, 0.205),
                (0.075, CHAIN_Y, 0.30), (-0.02, CHAIN_Y, 0.396)],
               0.005, mats["dark_metal"], bike_col, root)
    # Chain tensioner roller in the lower run (IMG_8914).
    cylinder("SB_ChainTensioner", (-0.30, CHAIN_Y, 0.254), 0.018, 0.016,
             mats["dark_metal"], bike_col, rotation=(math.pi / 2, 0, 0), parent=root,
             vertices=14)
    # Chain guard continues the cover's dark lower band forward to the ring guard.
    guard_band = extruded_xz("SB_ChainGuard",
                             [(REAR_X, 0.398), (REAR_X, 0.470), (-0.16, 0.470),
                              (-0.03, 0.448), (0.06, 0.418), (0.085, 0.390),
                              (0.05, 0.372), (-0.14, 0.382)],
                             0.012, mats["basket"], bike_col, root, 0.005)
    guard_band.location.y = -0.080
    smooth(guard_band, 35)

    # --- Seat ------------------------------------------------------------------------
    post_top = (SEAT_TUBE_TOP[0] - 0.021, 0, 1.075)
    beam("SB_SeatPost", (SEAT_TUBE_TOP[0] + 0.004, 0, 0.86), post_top, 0.0165,
         mats["metal"], bike_col, root, 14)
    cylinder("SB_SeatClamp", SEAT_TUBE_TOP, 0.030, 0.035, mats["dark_metal"], bike_col,
             rotation=(0, -0.116, 0), parent=root, vertices=14)
    cube("SB_SeatPostReflector", (post_top[0] - 0.022, 0, 1.00), (0.008, 0.050, 0.035),
         mats["red_lens"], bike_col, root, 0.003)
    saddle = uv_sphere("SB_Saddle", (post_top[0] - 0.005, 0, 1.105), (0.145, 0.105, 0.042),
                       mats["basket"], bike_col, root, 28, 12)
    # Pear plan: broad rear, narrow nose, flat underside.
    for vertex in saddle.data.vertices:
        t = min(max((vertex.co.x + 0.04) / 0.18, 0.0), 1.0)
        vertex.co.y *= 1.0 - 0.62 * t * t * (3 - 2 * t)
        if vertex.co.z < 0:
            vertex.co.z *= 0.45
        vertex.co.z += 0.010 * max(-vertex.co.x, 0.0) / 0.145
    saddle.rotation_euler.y = -0.05
    smooth(saddle, 80)

    # --- Cockpit (steering) ------------------------------------------------------------
    for side, s in (("Left", -1), ("Right", 1)):
        sweep(f"SB_Fork_{side}",
              [head_axis(-0.17) + Vector((0, s * 0.058, -0.01)),
               (FRONT_X, s * 0.058, AXLE_Z)],
              ellipse_profile(0.011, 0.018, 12), mats["fork"], bike_col, steering,
              scales=[(1.15, 1.15), (0.75, 0.65)])
    crown = cube("SB_ForkCrown", head_axis(-0.17), (0.075, 0.150, 0.040), mats["fork"],
                 bike_col, steering, 0.012)
    crown.rotation_euler.y = -HEAD_ANGLE
    stem = cylinder("SB_Stem", head_axis(0.225), 0.022, 0.15, mats["metal"], bike_col,
                    rotation=(0, -HEAD_ANGLE, 0), parent=steering, vertices=18)
    smooth(stem)
    for name, t, radius, depth, mat in (("SB_HeadsetCollar", 0.150, 0.036, 0.020, "fork"),
                                        ("SB_StemCollar", 0.172, 0.025, 0.012, "collar")):
        smooth(cylinder(name, head_axis(t), radius, depth, mats[mat], bike_col,
                        rotation=(0, -HEAD_ANGLE, 0), parent=steering, vertices=18))
    for index, t in enumerate((0.21, 0.25)):
        bolt = head_axis(t) + Vector((-0.02, 0, 0))
        cylinder(f"SB_StemBolt_{index}", bolt, 0.006, 0.012, mats["dark_metal"], bike_col,
                 rotation=(0, math.pi / 2 - HEAD_ANGLE, 0), parent=steering, vertices=8)
    stem_top = head_axis(0.30)
    cylinder("SB_HandlebarClamp", stem_top, 0.024, 0.075, mats["metal"], bike_col,
             rotation=(math.pi / 2, 0, 0), parent=steering, vertices=16)
    # Swept-back cruiser bar: rises from the clamp, then sweeps toward the rider.
    half_bar = [(stem_top.x, 0.0, stem_top.z), (stem_top.x - 0.004, 0.07, stem_top.z + 0.004),
                (stem_top.x - 0.02, 0.15, stem_top.z + 0.020),
                (stem_top.x - 0.06, 0.23, stem_top.z + 0.030),
                (stem_top.x - 0.12, 0.29, stem_top.z + 0.030),
                (stem_top.x - 0.20, 0.34, stem_top.z + 0.026)]
    bar_path = [(x, -y, z) for x, y, z in reversed(half_bar[1:])] + half_bar
    sweep("SB_Handlebar", bar_path, ellipse_profile(0.011, 0.011, 10), mats["metal"],
          bike_col, steering, ref=(0, 0, 1))
    for side, s in (("Left", -1), ("Right", 1)):
        a, b = Vector(half_bar[-2]), Vector(half_bar[-1])
        grip_start = a + (b - a) * 0.15
        grip_end = b + (b - a) * 0.10
        sweep(f"SB_Grip_{side}",
              [(grip_start.x, s * grip_start.y, grip_start.z),
               (grip_end.x, s * grip_end.y, grip_end.z)],
              ellipse_profile(0.017, 0.017, 12), mats["basket"], bike_col, steering,
              ref=(0, 0, 1))
        lever_start = a + Vector((0.035, 0, -0.008))
        lever_end = b + Vector((0.030, 0.01, -0.020))
        beam(f"SB_BrakeLever_{side}", (lever_start.x, s * lever_start.y, lever_start.z),
             (lever_end.x, s * lever_end.y, lever_end.z), 0.0065, mats["dark_metal"],
             bike_col, steering, 8)
        curve_tube(f"SB_Cable_{side}",
                   [(a.x + 0.01, s * a.y, a.z), (0.39, s * 0.14, 1.16),
                    (0.43, s * 0.055, 1.00), (0.555, s * 0.050, 0.77)],
                   0.0035, mats["basket"], bike_col, steering)
        cube(f"SB_BrakeLeverMount_{side}", (a.x, s * a.y, a.z), (0.03, 0.022, 0.03),
             mats["dark_metal"], bike_col, steering, 0.006)

    # Wide channel front mudguard, running low in front of the tyre (IMG_8915).
    sweep("SB_FrontMudguard", arc_points(FRONT_X, AXLE_Z, 0.388, 0.388, -30, 118, 18),
          mudguard_profile(0.038, 0.013, 0.006), mats["basket"], bike_col, steering)
    for side, s in (("Left", -1), ("Right", 1)):
        tip = (FRONT_X + math.cos(math.radians(-18)) * 0.39, s * 0.038,
               AXLE_Z + math.sin(math.radians(-18)) * 0.39)
        beam(f"SB_FrontMudguardStay_{side}", tip, (FRONT_X, s * 0.064, AXLE_Z), 0.0025,
             mats["metal"], bike_col, steering, 5)

    # --- Basket (frame-mounted, IMG_8916) ------------------------------------------------
    basket_root = empty("SB_Basket", (0.705, 0, 0.87), bike_col, root,
                        display="CUBE", size=0.14)
    basket_root["mount"] = "frame (head tube bracket); does not steer"
    tub("SB_BasketTub", (0.705, 0, 0.87), (0.165, 0.215), (0.135, 0.180), 0.215, 0.060,
        0.007, 0.010, mats["basket"], bike_col, basket_root)
    for side, s in (("Left", -1), ("Right", 1)):
        beam(f"SB_BasketMount_{side}", (0.565, s * 0.075, 0.90), (0.50, s * 0.028, 0.86),
             0.012, mats["dark_metal"], bike_col, basket_root, 10)
    # Lock tongue under the basket that engages the dock's top plate.
    cube("SB_DockLockTongue", (0.70, DOCK_SLAB_Y, 0.828), (0.055, 0.026, 0.045),
         mats["dark_metal"], bike_col, basket_root, 0.008)
    cube("SB_DockLockTongueArm", (0.70, DOCK_SLAB_Y * 0.62, 0.862), (0.050, 0.10, 0.018),
         mats["dark_metal"], bike_col, basket_root, 0.005)
    # White head unit panel standing between head tube and basket (IMG_8916).
    head_unit = cube("SB_HeadUnitPanel", (0.520, 0, 1.055), (0.014, 0.150, 0.210),
                     mats["white_plastic"], bike_col, root, 0.012)
    head_unit.rotation_euler.y = -HEAD_ANGLE * 0.6
    cube("SB_HeadUnitMount", (0.505, 0, 0.965), (0.030, 0.060, 0.070), mats["basket"],
         bike_col, root, 0.010)
    smooth(cube("SB_FrontLightHousing", (0.866, 0, 0.935), (0.030, 0.100, 0.050),
                mats["basket"], bike_col, basket_root, 0.014), 60)
    cube("SB_FrontLightLens", (0.882, 0, 0.935), (0.006, 0.080, 0.030), mats["lens"],
         bike_col, basket_root, 0.004)
    empty("SB_FrontLightAnchor", (0.90, 0, 0.935), bike_col, basket_root, "SPHERE", 0.06)

    # Decal-ready surfaces.
    pill = cube("SB_Branding_DownTube", (0.365, -0.046, 0.631), (0.20, 0.004, 0.040),
                mats["rear_panel"], bike_col, root, 0.018)
    pill.rotation_euler.y = -0.90
    decal = cube("SB_Branding_SeatTube", (-0.180, -0.024, 0.62), (0.034, 0.004, 0.20),
                 mats["frame_light"], bike_col, root, 0.014)
    decal.rotation_euler.y = -0.116

    dock_anchor = empty("SB_DockAnchor", (0, 0, 0), bike_col, root, "ARROWS", 0.12)
    dock_anchor["snap_role"] = "bike-to-dock"
    for obj in bike_col.objects:
        if obj.type == "MESH" and not obj.data.polygons[0].use_smooth:
            smooth(obj, 35)
    return bike_col, root


def build_dock(mats):
    dock_col = collection("STERLING_DOCK_MASTER")
    root = empty("STERLING_DOCK_MASTER", (0, 0, 0), dock_col, display="CUBE", size=0.18)
    root["asset_type"] = "sterling-dock-blockout"
    # Thin rounded baseplate, bolted to the flags (IMG_8915).
    baseplate = loft("SD_Baseplate",
                     [[Vector((0.0 + u - 0.02, 0.07 + v, z)) for u, v in
                       rounded_rect(0.40, 0.165, 0.05, 3)] for z in (0.0, 0.022)],
                     mats["dock"], dock_col, root, smooth_angle=30)
    for index, (x, y) in enumerate(((-0.37, -0.06), (-0.37, 0.20),
                                    (0.33, -0.06), (0.33, 0.20))):
        cylinder(f"SD_BaseBolt_{index + 1:02d}", (x, y, 0.028), 0.014, 0.012,
                 mats["metal"], dock_col, parent=root, vertices=10)

    # Slim J-profile side post beside the front wheel, not a cabinet: tall front
    # edge, raked top, and a concave notch cradling the tyre with a low rear foot.
    notch = [(-0.12 + math.cos(math.radians(a)) * 0.19,
              0.34 + math.sin(math.radians(a)) * 0.19) for a in range(60, -61, -15)]
    outline = ([(-0.36, 0.022), (0.30, 0.022), (0.312, 0.12), (0.285, 0.60),
                (0.245, 0.700), (-0.030, 0.795), (-0.075, 0.765), (-0.055, 0.60)]
               + notch + [(-0.20, 0.175), (-0.36, 0.165)])
    body = extruded_xz("SD_UprightHousing", outline, DOCK_SLAB_T, mats["dock"],
                       dock_col, root, 0.012)
    body.location.y = DOCK_SLAB_Y
    smooth(body, 35)
    # Yellow bolted top lock plate wrapping the raked top edge.
    top_plate = extruded_xz("SD_TopLockPlate",
                            [(0.292, 0.555), (0.252, 0.712), (-0.032, 0.806),
                             (-0.086, 0.772), (-0.066, 0.62)],
                            DOCK_SLAB_T + 0.012, mats["dock_yellow"], dock_col, root, 0.008)
    top_plate.location.y = DOCK_SLAB_Y
    smooth(top_plate, 35)
    face_y = DOCK_SLAB_Y - (DOCK_SLAB_T + 0.012) / 2 - 0.003
    strip = cube("SD_ReflectiveStrip", (0.10, face_y, 0.655), (0.22, 0.006, 0.038),
                 mats["reflector"], dock_col, root, 0.016)
    strip.rotation_euler.y = -0.17
    for index, (x, z) in enumerate(((0.00, 0.72), (0.12, 0.70), (0.22, 0.67),
                                    (-0.02, 0.63), (0.10, 0.60), (0.22, 0.58))):
        cylinder(f"SD_TopPlateBolt_{index + 1:02d}", (x, face_y - 0.002, z), 0.009, 0.006,
                 mats["metal"], dock_col, rotation=(math.pi / 2, 0, 0), parent=root,
                 vertices=10)
    cube("SD_LockSlot", (0.0, DOCK_SLAB_Y, 0.797), (0.085, 0.040, 0.012),
         mats["dark_metal"], dock_col, root, 0.003).rotation_euler.y = 0.33
    # Tall yellow "Bike Hire" panel with the teal band down its rear edge.
    face_y = DOCK_SLAB_Y - DOCK_SLAB_T / 2 - 0.003
    sticker = extruded_xz("SD_BrandingSurface",
                          [(0.115, 0.13), (0.290, 0.13), (0.268, 0.54), (0.093, 0.54)],
                          0.004, mats["dock_yellow"], dock_col, root)
    sticker.location.y = face_y
    band = extruded_xz("SD_BrandingBand",
                       [(0.093, 0.13), (0.140, 0.13), (0.118, 0.54), (0.071, 0.54)],
                       0.005, mats["rear_panel"], dock_col, root)
    band.location.y = face_y - 0.001
    # Wheel cradle: dark tread plates in a shallow V under the tyre, with
    # hazard slats (IMG_8915). Kept below the tyre's circle.
    for name, start, end in (("Rear", (-0.23, 0.060), (-0.035, 0.024)),
                             ("Front", (0.035, 0.024), (0.23, 0.066))):
        length = math.dist(start, end)
        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        mid = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
        tread = cube(f"SD_WheelTread_{name}", (mid[0], 0.02, mid[1] - 0.008),
                     (length, 0.13, 0.014), mats["dark_metal"], dock_col, root, 0.004)
        tread.rotation_euler.y = -angle
        for slat in range(4):
            f = (slat + 0.5) / 4
            x = start[0] + (end[0] - start[0]) * f
            z = start[1] + (end[1] - start[1]) * f
            stripe = cube(f"SD_WheelTreadStripe_{name}_{slat}", (x, 0.02, z - 0.0005),
                          (0.022, 0.12, 0.004), mats["dock_yellow"], dock_col, root)
            stripe.rotation_euler = (0, -angle, 0.5)
    for side, y in (("Left", -0.055), ("Right", 0.075)):
        cube(f"SD_WheelGuide_{side}", (0.0, y, 0.045), (0.30, 0.012, 0.05), mats["dock"],
             dock_col, root, 0.004)

    anchor = empty("SD_BikeDockAnchor", (-FRONT_X, 0, 0), dock_col, root,
                   "ARROWS", 0.14)
    anchor["snap_role"] = "dock-to-bike"
    empty("SD_InteractionAnchor", (-0.25, -0.85, 0), dock_col, root,
          "PLAIN_AXES", 0.20)
    for obj in dock_col.objects:
        if obj.type == "MESH" and not obj.data.polygons[0].use_smooth:
            smooth(obj, 35)
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
        # Linear base colours sampled by eye from IMG_8911-8917, pushed slightly
        # past the sodium-lit photos toward daylight fleet colours.
        "frame": material("MAT_SB_Frame_PLACEHOLDER", (0.74, 0.70, 0.012), 0.05, 0.42),
        "frame_light": material("MAT_SB_FrameLight_PLACEHOLDER", (0.80, 0.76, 0.050), 0.02, 0.48),
        "metal": material("MAT_SB_Metal_PLACEHOLDER", (0.56, 0.57, 0.59), 0.85, 0.32),
        "rim": material("MAT_SB_Rim_PLACEHOLDER", (0.34, 0.35, 0.36), 0.70, 0.45),
        "hub": material("MAT_SB_Hub_PLACEHOLDER", (0.16, 0.16, 0.17), 0.55, 0.50),
        "fork": material("MAT_SB_ForkPaint_PLACEHOLDER", (0.25, 0.24, 0.30), 0.30, 0.45),
        "collar": material("MAT_SB_StemCollar_PLACEHOLDER", (0.015, 0.11, 0.08), 0.20, 0.50),
        "dark_metal": material("MAT_SB_DarkMetal_PLACEHOLDER", (0.05, 0.055, 0.06), 0.45, 0.48),
        "rubber": material("MAT_SB_Rubber_PLACEHOLDER", (0.018, 0.019, 0.021), 0.0, 0.90),
        "rear_panel": material("MAT_SB_RearPanel_PLACEHOLDER", (0.12, 0.58, 0.60), 0.0, 0.50),
        "basket": material("MAT_SB_Basket_PLACEHOLDER", (0.020, 0.023, 0.026), 0.0, 0.70),
        "white_plastic": material("MAT_SB_HeadUnit_PLACEHOLDER", (0.66, 0.67, 0.66), 0.0, 0.50),
        "lens": material("MAT_SB_LightLens_PLACEHOLDER", (0.75, 0.82, 0.76), 0.0, 0.24),
        "red_lens": material("MAT_SB_RearLightLens_PLACEHOLDER", (0.42, 0.015, 0.015), 0.0, 0.28),
        "reflector": material("MAT_SB_Reflector_PLACEHOLDER", (0.72, 0.72, 0.70), 0.0, 0.35),
        "dock": material("MAT_SD_Dock_PLACEHOLDER", (0.30, 0.30, 0.34), 0.35, 0.50),
        "dock_yellow": material("MAT_SD_DockYellow_PLACEHOLDER", (0.80, 0.52, 0.010), 0.0, 0.50),
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
    # H: close-up of the empty middle dock's side post, tread cradle and top plate.
    render_view("H-empty-dock-detail.png", (STATION_X + 1.35, -1.25, 0.95),
                (STATION_X + 0.02, 0.08, 0.36), 50)
    bikes[1].hide_render = False
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    print(f"Saved {BLEND_PATH}")


if __name__ == "__main__":
    main()
