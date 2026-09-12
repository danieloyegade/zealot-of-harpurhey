"""Rebuild Real Camera / Sevendale House with a walkable shop interior.

The model is reconstructed from the supplied exterior and interior photographs.
It deliberately replaces the earlier generic flat facade: the Dale Street elevation
now has projecting bays, tall mullioned windows, arched top-storey openings, a
faceted corner bay, the photographed shop-window/shutter arrangement, and the
Gallery stair entrance.  Behind that entrance is a navigable camera shop with a
clear aisle, display cases, shelving, camera silhouettes, tripods, softboxes and a
suspended fluorescent ceiling.

One Blender unit is one metre.  Z is up.  Dale Street faces local -Y.
"""

from math import atan2, cos, pi, radians, sin, sqrt
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
BLEND_PATH = ROOT / "blender" / "source" / "real_camera.blend"
GLB_PATH = ROOT / "public" / "assets" / "models" / "real_camera.glb"
RENDER_DIR = ROOT / "renders" / "real-camera"

FRONT_Y = -5.0
WEST_X = -8.0
BACK_Y = 5.4
GROUND_H = 4.25
FLOOR_1_Z = 4.45
FLOOR_2_Z = 7.52
FLOOR_3_Z = 10.58
PARAPET_Z = 13.55
TOTAL_H = 14.75


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
        bpy.data.curves,
    ):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def collection(name, parent=None):
    result = bpy.data.collections.new(name)
    (parent.children if parent else bpy.context.scene.collection.children).link(result)
    return result


def relink(obj, target):
    for source in list(obj.users_collection):
        source.objects.unlink(obj)
    target.objects.link(obj)


def material(name, color, roughness=0.75, metallic=0.0, alpha=1.0, emission=None, emission_strength=0.0):
    result = bpy.data.materials.new(name)
    result.diffuse_color = (*color, alpha)
    result.use_nodes = True
    bsdf = result.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, alpha)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        bsdf.inputs["Transmission Weight"].default_value = 0.04
        result.surface_render_method = "DITHERED"
    if emission is not None:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    return result


def box(name, dimensions, location, mat, target, bevel=0.0, rotation_z=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    obj.dimensions = dimensions
    obj.rotation_euler[2] = rotation_z
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new("EdgeSoftening", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    relink(obj, target)
    return obj


def cylinder(name, radius, depth, location, mat, target, rotation=(0.0, 0.0, 0.0), vertices=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    obj.rotation_euler = rotation
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    if mat:
        obj.data.materials.append(mat)
    relink(obj, target)
    return obj


def empty(name, location, target, size=0.35):
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    obj.empty_display_type = "ARROWS"
    obj.empty_display_size = size
    target.objects.link(obj)
    return obj


def text_mesh(name, body, location, size, extrude, mat, target, rotation=(radians(90), 0.0, 0.0), align="CENTER"):
    curve = bpy.data.curves.new(f"{name}_Curve", "FONT")
    curve.body = body
    curve.align_x = align
    curve.align_y = "CENTER"
    curve.size = size
    curve.extrude = extrude
    curve.bevel_depth = min(0.008, extrude * 0.5)
    obj = bpy.data.objects.new(name, curve)
    obj.location = location
    obj.rotation_euler = rotation
    target.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    obj.select_set(False)
    return obj


def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def camera(name, location, target, lens, target_collection):
    data = bpy.data.cameras.new(f"{name}_Data")
    data.lens = lens
    data.sensor_fit = "HORIZONTAL"
    data.sensor_width = 36
    data.clip_start = 0.05
    data.clip_end = 250
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    target_collection.objects.link(obj)
    point_at(obj, target)
    return obj


def area_light(name, location, target, energy, size, target_collection, color=(1.0, 0.93, 0.83)):
    data = bpy.data.lights.new(f"{name}_Data", "AREA")
    data.energy = energy
    data.shape = "RECTANGLE"
    data.size = size
    data.size_y = size * 0.65
    data.color = color
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    target_collection.objects.link(obj)
    point_at(obj, target)
    return obj


def cylinder_between(name, start, end, radius, mat, target, vertices=10):
    start_v, end_v = Vector(start), Vector(end)
    delta = end_v - start_v
    obj = cylinder(name, radius, delta.length, (start_v + end_v) * 0.5, mat, target, vertices=vertices)
    obj.rotation_euler = delta.to_track_quat("Z", "Y").to_euler()
    return obj


def prism_mesh(name, points_xy, z0, z1, mat, target):
    count = len(points_xy)
    verts = [(x, y, z0) for x, y in points_xy] + [(x, y, z1) for x, y in points_xy]
    faces = [tuple(range(count - 1, -1, -1)), tuple(range(count, count * 2))]
    for i in range(count):
        j = (i + 1) % count
        faces.append((i, j, count + j, count + i))
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    target.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    return obj


def quarter_tower(name, center, radius, z0, z1, mat, target, segments=12):
    cx, cy = center
    points = [(cx, cy)]
    for i in range(segments + 1):
        angle = pi + (pi / 2) * (i / segments)
        points.append((cx + radius * cos(angle), cy + radius * sin(angle)))
    return prism_mesh(name, points, z0, z1, mat, target)


def triangular_pediment(name, center_x, y, width, height, depth, z0, mat, target):
    points = [
        (center_x - width / 2, z0),
        (center_x + width / 2, z0),
        (center_x, z0 + height),
    ]
    verts = []
    for yy in (y - depth / 2, y + depth / 2):
        verts.extend([(x, yy, z) for x, z in points])
    faces = [(0, 2, 1), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)]
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    target.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def arch_glass(name, center_x, y, z0, width, straight_h, radius, depth, mat, target, segments=14):
    spring = z0 + straight_h
    points = [(center_x - width / 2, z0), (center_x + width / 2, z0), (center_x + width / 2, spring)]
    for i in range(segments + 1):
        angle = pi * (i / segments)
        points.append((center_x + radius * cos(angle), spring + radius * sin(angle)))
    points.append((center_x - width / 2, spring))
    verts = [(x, y - depth / 2, z) for x, z in points] + [(x, y + depth / 2, z) for x, z in points]
    n = len(points)
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    target.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def create_materials():
    return {
        "redstone": material("MAT_RC_RedSandstone", (0.43, 0.16, 0.095), 0.92),
        "stone_light": material("MAT_RC_LightSandstone", (0.60, 0.29, 0.18), 0.88),
        "stone_dark": material("MAT_RC_DarkSandstone", (0.25, 0.085, 0.045), 0.96),
        "frame": material("MAT_RC_PaintedWindowFrames", (0.11, 0.12, 0.105), 0.62),
        "glass": material("MAT_RC_WindowGlass", (0.08, 0.115, 0.12), 0.18, alpha=0.32),
        "shop_glass": material("MAT_RC_ShopGlass", (0.11, 0.16, 0.15), 0.14, alpha=0.24),
        "red": material("MAT_RC_AwningRed", (0.55, 0.025, 0.028), 0.48),
        "green": material("MAT_RC_ShopTrimGreen", (0.035, 0.24, 0.13), 0.56),
        "white": material("MAT_RC_SignWhite", (0.87, 0.86, 0.79), 0.72),
        "black": material("MAT_RC_Black", (0.015, 0.018, 0.018), 0.52),
        "metal": material("MAT_RC_Metal", (0.20, 0.21, 0.20), 0.40, 0.45),
        "shutter": material("MAT_RC_Shutter", (0.44, 0.46, 0.45), 0.48, 0.25),
        "carpet": material("MAT_RC_GreyCarpet", (0.19, 0.205, 0.19), 0.98),
        "interior_wall": material("MAT_RC_InteriorWalls", (0.79, 0.78, 0.70), 0.90),
        "ceiling": material("MAT_RC_CeilingTiles", (0.76, 0.76, 0.70), 0.95),
        "fluorescent": material("MAT_RC_Fluorescent", (0.92, 0.96, 0.88), 0.30, emission=(0.92, 0.98, 0.90), emission_strength=5.0),
        "wood": material("MAT_RC_DisplayWood", (0.42, 0.17, 0.055), 0.68),
        "counter": material("MAT_RC_CounterBase", (0.67, 0.58, 0.43), 0.86),
        "red_shelf": material("MAT_RC_ShelfRed", (0.58, 0.035, 0.025), 0.55),
        "poster_blue": material("MAT_RC_PosterBlue", (0.14, 0.29, 0.47), 0.75),
        "poster_yellow": material("MAT_RC_PosterYellow", (0.72, 0.50, 0.08), 0.75),
        "lens": material("MAT_RC_LensGlass", (0.015, 0.025, 0.03), 0.10, metallic=0.18),
        "review_ground": material("MAT_RC_ReviewGround", (0.20, 0.21, 0.20), 0.96),
        "nav": material("MAT_RC_NAV_PROXY", (0.02, 0.50, 0.70), 1.0, alpha=0.0),
    }


def moulding_course(name, x0, x1, y, z, mats, target, depth=0.42):
    width = x1 - x0
    center = (x0 + x1) / 2
    box(f"{name}_Lower", (width, depth * 0.72, 0.12), (center, y - depth * 0.34, z - 0.12), mats["stone_dark"], target)
    box(f"{name}_Main", (width + 0.12, depth, 0.18), (center, y - depth / 2, z), mats["stone_light"], target)
    box(f"{name}_Lip", (width + 0.22, depth + 0.12, 0.09), (center, y - depth * 0.62, z + 0.15), mats["stone_light"], target)


def pilaster(name, x, y, z0, z1, mats, target, width=0.52, depth=0.42, fluted=False):
    box(f"{name}_Shaft", (width, depth, z1 - z0), (x, y - depth / 2, (z0 + z1) / 2), mats["stone_light"], target)
    box(f"{name}_BaseA", (width + 0.28, depth + 0.16, 0.30), (x, y - (depth + 0.16) / 2, z0 + 0.15), mats["stone_dark"], target, bevel=0.025)
    box(f"{name}_BaseB", (width + 0.16, depth + 0.10, 0.18), (x, y - (depth + 0.10) / 2, z0 + 0.38), mats["stone_light"], target)
    box(f"{name}_Capital", (width + 0.34, depth + 0.18, 0.26), (x, y - (depth + 0.18) / 2, z1 - 0.13), mats["stone_light"], target, bevel=0.025)
    box(f"{name}_Abacus", (width + 0.44, depth + 0.22, 0.12), (x, y - (depth + 0.22) / 2, z1 + 0.04), mats["stone_dark"], target)
    if fluted:
        for i, dx in enumerate((-0.14, 0.0, 0.14)):
            box(f"{name}_Flute_{i}", (0.035, depth + 0.025, min(0.75, z1 - z0 - 0.9)), (x + dx, y - depth - 0.02, z0 + 0.9), mats["stone_dark"], target)


def flat_window(name, x, z0, width, height, mats, target, small_panes=True):
    y = FRONT_Y - 0.055
    box(f"{name}_Glass", (width, 0.07, height), (x, y, z0 + height / 2), mats["glass"], target)
    for suffix, dx in (("L", -width / 2), ("R", width / 2), ("M", 0.0)):
        box(f"{name}_Frame_{suffix}", (0.09, 0.11, height + 0.10), (x + dx, y - 0.04, z0 + height / 2), mats["frame"], target)
    for suffix, dz in (("Top", height / 2), ("Bottom", -height / 2), ("Transom", height * 0.18)):
        box(f"{name}_Frame_{suffix}", (width + 0.10, 0.11, 0.09), (x, y - 0.04, z0 + height / 2 + dz), mats["frame"], target)
    if small_panes:
        pane_y = y - 0.065
        upper_start = z0 + height * 0.69
        for i in range(1, 4):
            px = x - width / 2 + width * i / 4
            box(f"{name}_LeadV_{i}", (0.025, 0.035, height * 0.30), (px, pane_y, upper_start + height * 0.15), mats["frame"], target)
        box(f"{name}_LeadH", (width, 0.035, 0.025), (x, pane_y, upper_start + height * 0.15), mats["frame"], target)
    box(f"{name}_Sill", (width + 0.28, 0.34, 0.12), (x, FRONT_Y - 0.16, z0 - 0.07), mats["stone_dark"], target)
    box(f"{name}_Lintel", (width + 0.30, 0.28, 0.14), (x, FRONT_Y - 0.13, z0 + height + 0.09), mats["stone_light"], target)


def bay_window(name, x, z0, width, height, projection, mats, target):
    front_w = width - 0.78
    side_dx = (width - front_w) / 2
    side_len = sqrt(side_dx * side_dx + projection * projection)
    angle = atan2(projection, side_dx)
    y_front = FRONT_Y - projection
    box(f"{name}_FrontGlass", (front_w, 0.07, height), (x, y_front, z0 + height / 2), mats["glass"], target)
    box(f"{name}_LeftGlass", (side_len, 0.07, height), (x - front_w / 2 - side_dx / 2, FRONT_Y - projection / 2, z0 + height / 2), mats["glass"], target, rotation_z=-angle)
    box(f"{name}_RightGlass", (side_len, 0.07, height), (x + front_w / 2 + side_dx / 2, FRONT_Y - projection / 2, z0 + height / 2), mats["glass"], target, rotation_z=angle)
    for i, fx in enumerate((x - front_w / 2, x, x + front_w / 2)):
        box(f"{name}_FrontMullion_{i}", (0.10, 0.13, height + 0.10), (fx, y_front - 0.04, z0 + height / 2), mats["frame"], target)
    for suffix, px, rot in (("L", x - width / 2, -angle), ("R", x + width / 2, angle)):
        box(f"{name}_Outer_{suffix}", (0.13, 0.15, height + 0.22), (px, FRONT_Y - 0.03, z0 + height / 2), mats["stone_light"], target, rotation_z=rot)
    for suffix, z in (("Sill", z0 - 0.08), ("Head", z0 + height + 0.08)):
        box(f"{name}_{suffix}_Front", (front_w + 0.24, 0.38, 0.15), (x, y_front - 0.12, z), mats["stone_dark"], target)
        box(f"{name}_{suffix}_Left", (side_len + 0.12, 0.30, 0.15), (x - front_w / 2 - side_dx / 2, FRONT_Y - projection / 2 - 0.07, z), mats["stone_light"], target, rotation_z=-angle)
        box(f"{name}_{suffix}_Right", (side_len + 0.12, 0.30, 0.15), (x + front_w / 2 + side_dx / 2, FRONT_Y - projection / 2 - 0.07, z), mats["stone_light"], target, rotation_z=angle)
    transom_z = z0 + height * 0.70
    box(f"{name}_FrontTransom", (front_w, 0.13, 0.09), (x, y_front - 0.04, transom_z), mats["frame"], target)
    for suffix, px, rot in (("L", x - front_w / 2 - side_dx / 2, -angle), ("R", x + front_w / 2 + side_dx / 2, angle)):
        box(f"{name}_SideTransom_{suffix}", (side_len, 0.10, 0.09), (px, FRONT_Y - projection / 2 - 0.04, transom_z), mats["frame"], target, rotation_z=rot)


def arched_window(name, x, z0, width, straight_h, radius, mats, target):
    y = FRONT_Y - 0.07
    arch_glass(f"{name}_Glass", x, y, z0, width, straight_h, radius, 0.07, mats["glass"], target)
    total_h = straight_h + radius
    for suffix, dx in (("L", -width / 2), ("R", width / 2), ("M", 0.0)):
        box(f"{name}_Mullion_{suffix}", (0.10, 0.13, straight_h + 0.10), (x + dx, y - 0.04, z0 + straight_h / 2), mats["frame"], target)
    box(f"{name}_Transom", (width + 0.08, 0.13, 0.09), (x, y - 0.04, z0 + straight_h * 0.70), mats["frame"], target)
    for i in range(11):
        angle = pi * (i / 10)
        px = x + (radius + 0.10) * cos(angle)
        pz = z0 + straight_h + (radius + 0.10) * sin(angle)
        box(f"{name}_ArchBlock_{i:02d}", (0.26, 0.30, 0.16), (px, FRONT_Y - 0.15, pz), mats["stone_light"], target, rotation_z=angle - pi / 2)
    box(f"{name}_Sill", (width + 0.32, 0.34, 0.14), (x, FRONT_Y - 0.16, z0 - 0.08), mats["stone_dark"], target)
    return total_h


def corner_windows(name, center, z0, height, mats, target):
    cx, cy = center
    radius = 2.06
    for index, angle_deg in enumerate((191.5, 214.0, 236.0, 258.5)):
        angle = radians(angle_deg)
        px, py = cx + radius * cos(angle), cy + radius * sin(angle)
        tangent = angle + pi / 2
        box(f"{name}_Glass_{index}", (0.72, 0.07, height), (px, py, z0 + height / 2), mats["glass"], target, rotation_z=tangent)
        box(f"{name}_Transom_{index}", (0.72, 0.11, 0.08), (px - 0.03 * cos(angle), py - 0.03 * sin(angle), z0 + height * 0.70), mats["frame"], target, rotation_z=tangent)
    for index, angle_deg in enumerate((180.0, 202.5, 225.0, 247.5, 270.0)):
        angle = radians(angle_deg)
        px, py = cx + 2.10 * cos(angle), cy + 2.10 * sin(angle)
        box(f"{name}_Pier_{index}", (0.14, 0.23, height + 0.20), (px, py, z0 + height / 2), mats["stone_light"], target, rotation_z=angle + pi / 2)


def create_exterior(groups, mats):
    shell, ground, upper, ornament = groups["shell"], groups["ground"], groups["upper"], groups["ornament"]
    windows, signage = groups["windows"], groups["signage"]

    # Main and return masses meet a true quarter-round corner, instead of the
    # disconnected full cylinder used by the earlier model.
    box("RC_MainBuildingMass", (13.4, BACK_Y - FRONT_Y, TOTAL_H), (0.7, (FRONT_Y + BACK_Y) / 2, TOTAL_H / 2), mats["redstone"], shell)
    box("RC_LeverStreetReturnMass", (2.0, 8.4, TOTAL_H), (-7.0, 1.2, TOTAL_H / 2), mats["redstone"], shell)
    corner_center = (-6.0, -3.0)
    quarter_tower("RC_QuarterRoundCorner", corner_center, 2.0, 0.0, TOTAL_H, mats["redstone"], shell, segments=16)

    # Deep storey bands visible across the photographic elevation.
    for index, z in enumerate((4.18, 7.30, 10.36, 13.28)):
        moulding_course(f"RC_StringCourse_{index}", -6.05, 7.42, FRONT_Y, z, mats, ornament, depth=0.46 if index < 3 else 0.56)
    for index, z in enumerate((4.18, 7.30, 10.36, 13.28)):
        for angle_deg in range(180, 271, 15):
            angle = radians(angle_deg)
            px = corner_center[0] + 2.10 * cos(angle)
            py = corner_center[1] + 2.10 * sin(angle)
            box(f"RC_CornerBand_{index}_{angle_deg}", (0.48, 0.28, 0.16), (px, py, z), mats["stone_light"], ornament, rotation_z=angle + pi / 2)

    # Ground-floor piers and rustication confined to the actual stonework.
    for index, x in enumerate((-6.05, -2.42, 2.30, 6.45)):
        pilaster(f"RC_GroundPilaster_{index}", x, FRONT_Y, 0.0, 4.15, mats, ornament, width=0.58, depth=0.55, fluted=True)
        for band_index, z in enumerate((1.02, 1.84, 2.67, 3.48)):
            box(f"RC_PilasterRustication_{index}_{band_index}", (0.74, 0.58, 0.07), (x, FRONT_Y - 0.31, z), mats["stone_dark"], ornament)

    # Secondary grey door beside the corner.
    box("RC_SecondaryDoorLeaf", (1.02, 0.08, 2.35), (-6.92, FRONT_Y - 0.04, 1.18), mats["frame"], ground)
    for suffix, dx in (("L", -0.58), ("R", 0.58)):
        box(f"RC_SecondaryDoorJamb_{suffix}", (0.18, 0.34, 2.70), (-6.92 + dx, FRONT_Y - 0.12, 1.35), mats["stone_light"], ground)
    box("RC_SecondaryDoorHead", (1.36, 0.36, 0.18), (-6.92, FRONT_Y - 0.14, 2.64), mats["stone_dark"], ground)
    for panel_index, z in enumerate((0.48, 1.18, 1.88)):
        box(f"RC_SecondaryDoorPanel_{panel_index}", (0.78, 0.05, 0.48), (-6.92, FRONT_Y - 0.10, z), mats["stone_dark"], ground, bevel=0.018)

    # Recessed Shopping Centre & Gallery entrance: the actual player route.
    gallery_x, gallery_w = -4.24, 3.08
    box("RC_GalleryRevealLeft", (0.18, 2.25, 3.76), (gallery_x - gallery_w / 2, FRONT_Y + 1.10, 1.88), mats["interior_wall"], ground)
    box("RC_GalleryRevealRight", (0.18, 2.25, 3.76), (gallery_x + gallery_w / 2, FRONT_Y + 1.10, 1.88), mats["interior_wall"], ground)
    box("RC_GalleryCeiling", (gallery_w, 2.25, 0.12), (gallery_x, FRONT_Y + 1.10, 3.78), mats["interior_wall"], ground)
    # Six actual granite steps, matching the reference flight.
    step_count, rise, total_run = 6, 0.82, 2.05
    for i in range(step_count):
        step_h = rise / step_count
        step_d = total_run / step_count
        box(f"RC_GalleryStep_{i:02d}", (gallery_w - 0.18, step_d * (i + 1), step_h * (i + 1)), (gallery_x, FRONT_Y + step_d * (i + 1) / 2, step_h * (i + 1) / 2), mats["stone_light"], ground, bevel=0.012)
    box("RC_GalleryLanding", (gallery_w - 0.18, 0.82, 0.10), (gallery_x, FRONT_Y + 2.48, rise - 0.05), mats["stone_light"], ground)
    # Open double doors preserve the photographed threshold but leave 1.6 m clear.
    door_y = FRONT_Y + 2.12
    for suffix, x, rot in (("L", gallery_x - 1.10, radians(-62)), ("R", gallery_x + 1.10, radians(62))):
        box(f"RC_GalleryDoor_{suffix}", (0.78, 0.06, 2.28), (x, door_y, rise + 1.14), mats["shop_glass"], ground, rotation_z=rot)
        box(f"RC_GalleryDoorFrame_{suffix}", (0.84, 0.08, 0.07), (x, door_y, rise + 2.27), mats["metal"], ground, rotation_z=rot)
    box("RC_GallerySignPanel", (gallery_w - 0.18, 0.10, 0.55), (gallery_x, FRONT_Y - 0.06, 3.47), mats["white"], signage)
    text_mesh("RC_GallerySignText", "THE  Real Camera Shopping Centre & Gallery", (gallery_x, FRONT_Y - 0.122, 3.53), 0.20, 0.012, mats["black"], signage)
    text_mesh("RC_GalleryTelephone", "Tel: 0161 907 3236", (gallery_x, FRONT_Y - 0.124, 3.35), 0.12, 0.008, mats["black"], signage)

    # Real Camera's photographed frontage: upper display window, green frame,
    # and a distinct lower shutter/window zone.  It is not an exterior doorway.
    shop_x, shop_w = 0.05, 3.95
    box("RC_MainShopRecess", (shop_w, 0.28, 3.72), (shop_x, FRONT_Y + 0.12, 1.86), mats["black"], ground)
    box("RC_MainDisplayGlass", (shop_w - 0.28, 0.07, 1.47), (shop_x, FRONT_Y - 0.045, 2.76), mats["shop_glass"], windows)
    for suffix, dx in (("L", -shop_w / 2), ("R", shop_w / 2)):
        box(f"RC_MainShopJamb_{suffix}", (0.22, 0.48, 3.72), (shop_x + dx, FRONT_Y - 0.22, 1.86), mats["stone_light"], ground)
    box("RC_GreenDisplaySill", (shop_w - 0.12, 0.26, 0.16), (shop_x, FRONT_Y - 0.14, 2.00), mats["green"], ground)
    box("RC_GreenDisplayHead", (shop_w - 0.12, 0.22, 0.12), (shop_x, FRONT_Y - 0.12, 3.50), mats["green"], ground)
    for i, x in enumerate((shop_x - shop_w / 2 + 0.10, shop_x, shop_x + shop_w / 2 - 0.10)):
        box(f"RC_MainDisplayMullion_{i}", (0.08, 0.12, 1.48), (x, FRONT_Y - 0.08, 2.76), mats["green"], windows)
    box("RC_LowerShutterRecess", (shop_w - 0.22, 0.12, 1.64), (shop_x, FRONT_Y - 0.01, 1.08), mats["white"], ground)
    box("RC_LowerShutter", (shop_w - 0.34, 0.08, 0.66), (shop_x + 0.84, FRONT_Y - 0.08, 0.73), mats["shutter"], ground)
    # Sparse corrugation gives the shutter its physical reading without dense folds.
    for i in range(9):
        z = 0.44 + i * 0.075
        box(f"RC_LowerShutterRib_{i:02d}", (1.85, 0.035, 0.018), (shop_x + 0.84, FRONT_Y - 0.132, z), mats["metal"], ground)
    box("RC_LowerWindowDivider", (0.09, 0.14, 1.58), (shop_x - 0.10, FRONT_Y - 0.07, 1.08), mats["metal"], ground)
    box("RC_LowerWindowSill", (shop_w - 0.18, 0.30, 0.15), (shop_x, FRONT_Y - 0.16, 0.24), mats["stone_light"], ground)

    # Curved red sign canopy and its simple typography.
    box("RC_RedAwningCore", (shop_w + 0.22, 0.78, 0.52), (shop_x, FRONT_Y - 0.18, 3.82), mats["red"], signage, bevel=0.18)
    cylinder("RC_RedAwningRolledLip", 0.28, shop_w + 0.22, (shop_x, FRONT_Y - 0.56, 3.63), mats["red"], signage, rotation=(0.0, pi / 2, 0.0), vertices=20)
    text_mesh("RC_AwningText", "the  Real  CAMERA  co.", (shop_x, FRONT_Y - 0.588, 3.88), 0.28, 0.014, mats["white"], signage)
    text_mesh("RC_AwningSubText", "0161 907 3236                       realcamera.co.uk", (shop_x, FRONT_Y - 0.590, 3.68), 0.095, 0.008, mats["white"], signage)

    # Adjacent shopfront continuation helps the hero unit feel embedded.
    adj_x, adj_w = 4.48, 3.42
    box("RC_AdjacentWindow", (adj_w - 0.25, 0.08, 2.72), (adj_x, FRONT_Y - 0.04, 1.58), mats["shop_glass"], ground)
    box("RC_AdjacentShopSill", (adj_w, 0.30, 0.18), (adj_x, FRONT_Y - 0.15, 0.22), mats["stone_light"], ground)
    for i, x in enumerate((adj_x - adj_w / 2, adj_x, adj_x + adj_w / 2)):
        box(f"RC_AdjacentMullion_{i}", (0.10, 0.12, 2.72), (x, FRONT_Y - 0.08, 1.58), mats["frame"], ground)
    box("RC_AdjacentTransom", (adj_w, 0.12, 0.10), (adj_x, FRONT_Y - 0.08, 2.30), mats["frame"], ground)

    # Upper floors: the first two alternate projecting bays and flat pairs.
    for floor_index, (z0, h, proj) in enumerate(((FLOOR_1_Z, 2.52, 0.46), (FLOOR_2_Z, 2.50, 0.52)), start=1):
        corner_windows(f"RC_Floor{floor_index}_CornerBay", corner_center, z0, h, mats, windows)
        bay_window(f"RC_Floor{floor_index}_GalleryBay", -4.18, z0, 2.85, h, proj, mats, windows)
        flat_window(f"RC_Floor{floor_index}_ShopWindow_L", -0.68, z0, 1.32, h, mats, windows)
        flat_window(f"RC_Floor{floor_index}_ShopWindow_R", 0.82, z0, 1.32, h, mats, windows)
        bay_window(f"RC_Floor{floor_index}_AdjacentBay", 4.48, z0, 2.95, h, proj, mats, windows)

    # Tall arched top-storey windows visible in the wider Street View references.
    corner_windows("RC_Floor3_CornerBay", corner_center, FLOOR_3_Z, 2.20, mats, windows)
    for index, x in enumerate((-4.18, 0.05, 4.48)):
        arched_window(f"RC_Floor3_Arch_{index}", x, FLOOR_3_Z, 2.15, 1.48, 1.075, mats, windows)

    # Strong upper piers, carved blocks and dentilled cornice.
    for index, x in enumerate((-6.05, -2.38, 2.30, 6.45)):
        pilaster(f"RC_UpperPier_{index}", x, FRONT_Y, 4.22, 13.34, mats, upper, width=0.46, depth=0.36)
        for z in (7.18, 10.24, 13.14):
            box(f"RC_UpperPierBand_{index}_{z:.2f}", (0.66, 0.44, 0.14), (x, FRONT_Y - 0.24, z), mats["stone_dark"], upper)
    box("RC_CorniceFascia", (13.72, 0.62, 0.44), (0.68, FRONT_Y - 0.31, 13.54), mats["stone_light"], ornament)
    box("RC_CorniceCap", (14.02, 0.76, 0.20), (0.68, FRONT_Y - 0.38, 13.82), mats["stone_dark"], ornament)
    for i in range(31):
        x = -6.08 + i * 0.445
        box(f"RC_CorniceDentil_{i:02d}", (0.22, 0.24, 0.20), (x, FRONT_Y - 0.46, 13.28), mats["stone_light"], ornament)

    # Raised roofline/pediment supported by the corner references.
    triangular_pediment("RC_CornerPediment", -4.18, FRONT_Y - 0.18, 3.45, 1.18, 0.38, 13.58, mats["stone_light"], ornament)
    box("RC_CornerPedimentInset", (1.90, 0.12, 0.40), (-4.18, FRONT_Y - 0.42, 14.12), mats["stone_dark"], ornament)
    text_mesh("RC_SevendaleHouseText", "SEVENDALE HOUSE", (-4.18, FRONT_Y - 0.492, 14.15), 0.18, 0.01, mats["stone_light"], signage)

    # Hanging sign and diagonal corner clock.
    box("RC_HangingSign", (0.98, 0.10, 0.88), (2.30, FRONT_Y - 0.88, 4.78), mats["white"], signage, bevel=0.035)
    text_mesh("RC_HangingSignText", "Real\nCamera", (2.30, FRONT_Y - 0.945, 4.79), 0.22, 0.012, mats["black"], signage)
    cylinder_between("RC_HangingSignArmTop", (2.30, FRONT_Y - 0.12, 5.10), (2.30, FRONT_Y - 0.82, 5.10), 0.035, mats["metal"], signage)
    cylinder_between("RC_HangingSignArmBottom", (2.30, FRONT_Y - 0.12, 4.48), (2.30, FRONT_Y - 0.82, 4.48), 0.035, mats["metal"], signage)

    clock_angle = radians(225)
    clock_center = (corner_center[0] + 2.62 * cos(clock_angle), corner_center[1] + 2.62 * sin(clock_angle), 8.05)
    box("RC_CornerClockHousing", (0.76, 0.76, 0.76), clock_center, mats["black"], signage, bevel=0.05, rotation_z=clock_angle + pi / 4)
    # Two pale faces create the recognisable projecting clock silhouette.
    cylinder("RC_CornerClockFace_Dale", 0.32, 0.06, (clock_center[0] + 0.34, clock_center[1] - 0.18, clock_center[2]), mats["white"], signage, rotation=(pi / 2, 0.0, 0.0), vertices=24)
    cylinder("RC_CornerClockFace_Lever", 0.32, 0.06, (clock_center[0] - 0.18, clock_center[1] + 0.34, clock_center[2]), mats["white"], signage, rotation=(0.0, pi / 2, 0.0), vertices=24)
    cylinder_between("RC_CornerClockBracket", (corner_center[0] + 1.48 * cos(clock_angle), corner_center[1] + 1.48 * sin(clock_angle), 7.46), (clock_center[0], clock_center[1], 7.72), 0.06, mats["metal"], signage)

    # Prominent downpipes and alarm boxes from the photos.
    for index, x in enumerate((2.32, 6.48)):
        cylinder(f"RC_Downpipe_{index}", 0.055, 12.8, (x, FRONT_Y - 0.34, 6.4), mats["metal"], ground, vertices=12)
    box("RC_AlarmBox", (0.34, 0.16, 0.30), (-2.75, FRONT_Y - 0.26, 3.06), mats["white"], ground, bevel=0.04)

    return {"gallery_x": gallery_x, "gallery_rise": rise, "shop_x": shop_x, "corner_center": corner_center}


def display_case(name, location, dimensions, mats, target, rotation_z=0.0, tall=False):
    x, y, z = location
    width, depth, height = dimensions
    base_h = 0.48 if tall else 0.54
    box(f"{name}_Base", (width, depth, base_h), (x, y, z + base_h / 2), mats["counter"], target, bevel=0.025, rotation_z=rotation_z)
    glass_h = height - base_h
    box(f"{name}_GlassVolume", (width - 0.08, depth - 0.08, glass_h), (x, y, z + base_h + glass_h / 2), mats["shop_glass"], target, rotation_z=rotation_z)
    for suffix, dz in (("Lower", z + base_h + 0.05), ("Upper", z + height - 0.05)):
        box(f"{name}_Rail_{suffix}", (width, depth, 0.07), (x, y, dz), mats["metal"], target, rotation_z=rotation_z)
    shelf_count = 3 if tall else 2
    for i in range(1, shelf_count + 1):
        shelf_z = z + base_h + glass_h * i / (shelf_count + 1)
        box(f"{name}_Shelf_{i}", (width - 0.12, depth - 0.12, 0.035), (x, y, shelf_z), mats["shop_glass"], target, rotation_z=rotation_z)


def camera_prop(name, location, scale, mats, target, rotation_z=0.0):
    x, y, z = location
    body = box(f"{name}_Body", (0.30 * scale, 0.16 * scale, 0.22 * scale), (x, y, z), mats["black"], target, bevel=0.025 * scale, rotation_z=rotation_z)
    # Lens points toward local -Y; position follows the camera's rotation.
    forward = Vector((sin(rotation_z), -cos(rotation_z), 0.0))
    lens_pos = Vector((x, y, z)) + forward * (0.12 * scale)
    lens = cylinder(f"{name}_Lens", 0.075 * scale, 0.13 * scale, lens_pos, mats["lens"], target, rotation=(pi / 2, 0.0, rotation_z), vertices=12)
    box(f"{name}_Prism", (0.13 * scale, 0.10 * scale, 0.07 * scale), (x, y, z + 0.14 * scale), mats["metal"], target, bevel=0.018 * scale, rotation_z=rotation_z)
    return body, lens


def wall_shelves(name, center_x, y, z0, width, height, mats, target):
    box(f"{name}_Back", (width, 0.12, height), (center_x, y, z0 + height / 2), mats["interior_wall"], target)
    for i in range(6):
        z = z0 + 0.32 + i * (height - 0.45) / 5
        box(f"{name}_Shelf_{i}", (width, 0.34, 0.055), (center_x, y - 0.14, z), mats["red_shelf"], target)
    for i in range(5):
        x = center_x - width / 2 + 0.32 + i * (width - 0.64) / 4
        box(f"{name}_Vertical_{i}", (0.055, 0.18, height), (x, y - 0.05, z0 + height / 2), mats["metal"], target)


def tripod(name, location, height, mats, target):
    x, y, z = location
    head_z = z + height
    cylinder_between(f"{name}_Column", (x, y, z + 0.18), (x, y, head_z), 0.025, mats["metal"], target, vertices=8)
    for i, angle in enumerate((0.0, 2 * pi / 3, 4 * pi / 3)):
        foot = (x + 0.38 * cos(angle), y + 0.38 * sin(angle), z)
        cylinder_between(f"{name}_Leg_{i}", (x, y, z + height * 0.58), foot, 0.022, mats["metal"], target, vertices=8)
    box(f"{name}_Head", (0.15, 0.12, 0.09), (x, y, head_z), mats["black"], target, bevel=0.018)


def softbox(name, location, rotation_z, mats, target):
    x, y, z = location
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=0.54, radius2=0.20, depth=0.62, location=(x, y, z), rotation=(pi / 2, 0.0, rotation_z))
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    obj.data.materials.append(mats["black"])
    relink(obj, target)
    facing = Vector((sin(rotation_z), -cos(rotation_z), 0.0))
    panel_pos = Vector((x, y, z)) + facing * 0.31
    box(f"{name}_Diffuser", (0.86, 0.045, 0.86), panel_pos, mats["white"], target, rotation_z=rotation_z)


def create_interior(groups, mats, layout):
    interior, fixtures, props, nav = groups["interior"], groups["fixtures"], groups["props"], groups["nav"]
    rise = layout["gallery_rise"]
    room_x0, room_x1 = -5.55, 2.05
    room_y0, room_y1 = -2.72, 5.02
    room_w, room_d = room_x1 - room_x0, room_y1 - room_y0
    room_cx, room_cy = (room_x0 + room_x1) / 2, (room_y0 + room_y1) / 2
    ceiling_z = rise + 2.72

    box("RC_InteriorCarpet", (room_w, room_d, 0.08), (room_cx, room_cy, rise - 0.04), mats["carpet"], interior)
    box("RC_InteriorLeftWall", (0.14, room_d, ceiling_z - rise), (room_x0, room_cy, rise + (ceiling_z - rise) / 2), mats["interior_wall"], interior)
    box("RC_InteriorRightWall", (0.14, room_d, ceiling_z - rise), (room_x1, room_cy, rise + (ceiling_z - rise) / 2), mats["interior_wall"], interior)
    box("RC_InteriorBackWall", (room_w, 0.14, ceiling_z - rise), (room_cx, room_y1, rise + (ceiling_z - rise) / 2), mats["interior_wall"], interior)
    box("RC_InteriorSuspendedCeiling", (room_w, room_d, 0.09), (room_cx, room_cy, ceiling_z), mats["ceiling"], interior)

    # Suspended ceiling grid and fluorescent panels from the interior photos.
    for i in range(1, 5):
        x = room_x0 + room_w * i / 5
        box(f"RC_CeilingGrid_Long_{i}", (0.025, room_d, 0.03), (x, room_cy, ceiling_z - 0.06), mats["metal"], fixtures)
    for i in range(1, 7):
        y = room_y0 + room_d * i / 7
        box(f"RC_CeilingGrid_Cross_{i}", (room_w, 0.025, 0.03), (room_cx, y, ceiling_z - 0.06), mats["metal"], fixtures)
    light_positions = ((-4.55, -1.55), (-2.40, -0.35), (-0.20, -1.55), (-4.55, 1.25), (-2.40, 2.45), (-0.20, 1.25), (-3.45, 4.05), (0.35, 4.05))
    for i, (x, y) in enumerate(light_positions):
        box(f"RC_FluorescentPanel_{i:02d}", (1.20, 0.56, 0.035), (x, y, ceiling_z - 0.075), mats["fluorescent"], fixtures, bevel=0.018)

    # Display furniture leaves a continuous 1.45 m+ aisle from the doors to the back.
    display_case("RC_LeftTallDisplay", (-5.06, 0.60, rise), (0.66, 4.40, 2.18), mats, fixtures, tall=True)
    display_case("RC_LeftLowDisplay", (-3.95, 1.24, rise), (1.05, 3.55, 1.12), mats, fixtures)
    display_case("RC_CentreAngledDisplay", (-2.60, 2.55, rise), (0.92, 2.25, 1.02), mats, fixtures, rotation_z=radians(-13))
    display_case("RC_BackCounter", (-1.22, 4.25, rise), (3.48, 0.82, 1.08), mats, fixtures)
    display_case("RC_RightTallDisplay", (1.58, 2.65, rise), (0.60, 2.55, 2.15), mats, fixtures, tall=True)
    wall_shelves("RC_BackWallShelves", -1.20, 4.82, rise + 0.76, 4.55, 1.66, mats, fixtures)

    # Cameras populate the cases/shelves as low-poly silhouettes rather than empty boxes.
    camera_locations = []
    for row, z in enumerate((rise + 0.72, rise + 1.15, rise + 1.60, rise + 2.03)):
        for col, y in enumerate((-0.85, 0.05, 0.95, 1.85)):
            camera_locations.append((-5.12, y, z, radians(90)))
    for row, z in enumerate((rise + 0.73, rise + 1.05)):
        for col, y in enumerate((0.10, 1.15, 2.20)):
            camera_locations.append((-3.95, y, z, 0.0))
    for row, z in enumerate((rise + 1.10, rise + 1.48, rise + 1.86, rise + 2.22)):
        for col, x in enumerate((-2.85, -2.05, -1.25, -0.45, 0.35)):
            camera_locations.append((x, 4.57, z, 0.0))
    for i, (x, y, z, rot) in enumerate(camera_locations):
        camera_prop(f"RC_DisplayCamera_{i:03d}", (x, y, z), 0.70 if i < 22 else 0.62, mats, props, rotation_z=rot)

    # Tripod and lighting cluster on the right, prominent in two references.
    for i, (x, y, h) in enumerate(((0.62, -0.25, 1.52), (1.28, 0.35, 1.72), (0.74, 1.05, 1.44), (1.28, 1.42, 1.62))):
        tripod(f"RC_Tripod_{i}", (x, y, rise), h, mats, props)
    tripod("RC_SoftboxStand_A", (1.16, 0.02, rise), 2.05, mats, props)
    softbox("RC_Softbox_A", (1.16, 0.02, rise + 2.10), radians(205), mats, props)
    tripod("RC_SoftboxStand_B", (0.55, 1.46, rise), 1.90, mats, props)
    softbox("RC_Softbox_B", (0.55, 1.46, rise + 1.95), radians(225), mats, props)

    # Entrance-side book rack/wire basket and modest wall graphics.
    box("RC_EntranceBookcase", (0.34, 1.16, 1.25), (-5.18, -1.76, rise + 0.63), mats["wood"], fixtures)
    for i in range(4):
        box(f"RC_EntranceBookShelf_{i}", (0.42, 1.16, 0.045), (-5.15, -1.76, rise + 0.18 + i * 0.30), mats["wood"], fixtures)
    box("RC_WireBasket", (0.72, 0.62, 0.76), (-4.55, -0.92, rise + 0.38), mats["metal"], fixtures)
    for i, (y, z, mat_key) in enumerate(((-1.36, rise + 1.68, "poster_blue"), (-0.42, rise + 1.63, "poster_yellow"), (0.56, rise + 1.70, "poster_blue"))):
        box(f"RC_RightWallPoster_{i}", (0.035, 0.68, 0.88), (room_x1 - 0.09, y, z), mats[mat_key], fixtures)

    # A small monitor-like screen on the back wall preserves the photographic shop's
    # layered screens-within-glass character without inventing narrative content.
    box("RC_BackWallMonitor", (0.78, 0.08, 0.50), (-3.00, room_y1 - 0.10, rise + 2.16), mats["black"], fixtures)
    box("RC_BackWallMonitorScreen", (0.66, 0.035, 0.38), (-3.00, room_y1 - 0.155, rise + 2.16), mats["poster_blue"], fixtures)

    # Navigation helpers: visible stairs remain genuine geometry; the proxy communicates
    # the traversable slope to a future 3D movement/collision implementation.
    ramp_start = (layout["gallery_x"], FRONT_Y - 0.20, 0.0)
    ramp_end = (layout["gallery_x"], FRONT_Y + 2.45, rise)
    delta = Vector(ramp_end) - Vector(ramp_start)
    ramp = box("RC_NAV_GalleryRamp", (2.34, delta.length, 0.04), (layout["gallery_x"], (ramp_start[1] + ramp_end[1]) / 2, rise / 2), mats["nav"], nav)
    ramp.rotation_euler[0] = -atan2(rise, ramp_end[1] - ramp_start[1])
    ramp.hide_render = True

    empty("RC_EntranceAnchor", (layout["gallery_x"], FRONT_Y - 0.70, 0.0), groups["anchors"])
    empty("RC_GalleryThresholdAnchor", (layout["gallery_x"], FRONT_Y + 2.45, rise), groups["anchors"])
    empty("RC_InteriorSpawnAnchor", (layout["gallery_x"], -1.72, rise), groups["anchors"])
    empty("RC_ShopCounterAnchor", (-1.20, 3.65, rise), groups["anchors"])
    empty("RC_ExitAnchor", (layout["gallery_x"], FRONT_Y + 1.92, rise), groups["anchors"])

    return {"room_center": (room_cx, room_cy, rise + 1.25), "ceiling_z": ceiling_z}


def setup_scene(groups, mats, layout, interior_layout):
    review, cameras, lights = groups["review"], groups["cameras"], groups["lights"]
    box("RC_ReviewPavement", (25.0, 7.0, 0.12), (0.0, FRONT_Y - 3.55, -0.06), mats["review_ground"], review)
    box("RC_ReviewGround", (38.0, 34.0, 0.12), (0.0, 3.5, -0.16), mats["review_ground"], review)

    camera_specs = (
        ("CAMERA_01_FrontElevation", (0.0, -29.0, 6.6), (0.0, FRONT_Y, 6.4), 46),
        ("CAMERA_02_StreetThreeQuarter", (-13.8, -18.0, 5.6), (-0.3, FRONT_Y, 5.2), 43),
        ("CAMERA_03_UpperFacade", (1.0, -16.0, 5.0), (-0.4, FRONT_Y, 10.1), 52),
        ("CAMERA_04_CornerClock", (-16.0, -13.2, 7.0), (-6.4, -4.0, 7.7), 48),
        ("CAMERA_05_Entrances", (-1.5, -14.0, 2.4), (-1.4, FRONT_Y, 2.0), 55),
        ("CAMERA_06_InteriorFromDoor", (-4.22, -1.98, 1.72), (-1.65, 3.5, 1.62), 34),
        ("CAMERA_07_InteriorDisplay", (1.25, -0.55, 1.75), (-2.65, 3.2, 1.48), 39),
        ("CAMERA_08_InteriorBackToDoor", (-0.9, 4.1, 1.70), (-3.8, -2.1, 1.55), 36),
    )
    result = [camera(name, loc, target, lens, cameras) for name, loc, target, lens in camera_specs]
    area_light("RC_ExteriorKey", (-10.0, -18.0, 18.0), (0.0, FRONT_Y, 6.5), 2100, 8.0, lights)
    area_light("RC_ExteriorFill", (12.0, -11.0, 12.0), (0.0, FRONT_Y, 5.0), 1450, 7.0, lights, color=(0.72, 0.82, 1.0))
    area_light("RC_CornerFill", (-17.0, -5.0, 12.0), (-6.4, -3.5, 7.4), 1100, 5.0, lights)
    for i, (x, y) in enumerate(((-4.4, -0.8), (-2.2, 1.4), (-0.2, 3.3))):
        area_light(f"RC_InteriorLight_{i}", (x, y, interior_layout["ceiling_z"] - 0.16), (x, y, 0.8), 320, 2.0, lights, color=(0.86, 1.0, 0.88))
    return result


def apply_transforms_and_convert():
    bpy.ops.object.select_all(action="DESELECT")
    for obj in list(bpy.data.objects):
        if obj.type == "MESH":
            obj.select_set(True)
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    if meshes:
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.ops.object.select_all(action="DESELECT")


def export_glb():
    """Export a draw-call-conscious runtime GLB.

    The authored scene is ~675 separate named component meshes, which is right
    for editing but would cost ~675 draw calls per frame in Three.js. As with
    createTheHive.py, the runtime copy merges those into one mesh per material
    while leaving the interaction anchors as their own nodes.
    """
    excluded = {"RC_ReviewOnly", "RC_ReviewCameras", "RC_ReviewLights", "RC_Navigation"}

    def exportable(obj):
        return (
            obj.type not in {"CAMERA", "LIGHT"}
            and not any(collection.name in excluded for collection in obj.users_collection)
        )

    source_meshes = [obj for obj in bpy.data.objects if obj.type == "MESH" and exportable(obj)]
    anchors = [obj for obj in bpy.data.objects if obj.type == "EMPTY" and exportable(obj)]

    runtime_collection = bpy.data.collections.new("RC_RUNTIME_EXPORT_TEMP")
    bpy.context.scene.collection.children.link(runtime_collection)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    grouped = {}
    for obj in source_meshes:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = bpy.data.meshes.new_from_object(evaluated, depsgraph=depsgraph)
        duplicate = bpy.data.objects.new(f"RUNTIME_{obj.name}", mesh)
        duplicate.matrix_world = obj.matrix_world.copy()
        runtime_collection.objects.link(duplicate)
        material_name = mesh.materials[0].name if mesh.materials else "NoMaterial"
        grouped.setdefault(material_name, []).append(duplicate)

    joined_runtime = []
    for material_name, objects in grouped.items():
        bpy.ops.object.select_all(action="DESELECT")
        for obj in objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]
        bpy.ops.object.join()
        joined = bpy.context.view_layer.objects.active
        joined.name = f"RC_Runtime_{material_name.replace('MAT_RC_', '')}"
        joined_runtime.append(joined)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in (*joined_runtime, *anchors):
        obj.select_set(True)
    bpy.context.view_layer.objects.active = joined_runtime[0]

    GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_cameras=False,
        export_lights=False,
    )
    bpy.ops.object.select_all(action="DESELECT")

    # The authored .blend is saved again after this runs, so the merged copies
    # must not survive into it.
    for obj in list(runtime_collection.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(runtime_collection)
    print(f"Runtime GLB: {len(joined_runtime)} merged meshes from {len(source_meshes)} authored meshes")


def render_reviews(cameras):
    names = (
        "01-front-elevation.png",
        "02-street-three-quarter.png",
        "03-upper-facade.png",
        "04-corner-clock.png",
        "05-shop-and-gallery-entrances.png",
        "06-interior-from-entrance.png",
        "07-interior-display-cases.png",
        "08-interior-looking-to-entrance.png",
    )
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for cam, filename in zip(cameras, names):
        scene.camera = cam
        scene.render.resolution_x = 1280
        scene.render.resolution_y = 900
        scene.render.resolution_percentage = 100
        scene.render.filepath = str(RENDER_DIR / filename)
        bpy.ops.render.render(write_still=True)
        print(f"Rendered {scene.render.filepath}")


def build_scene():
    clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"

    master = collection("REAL_CAMERA_MASTER")
    groups = {
        "shell": collection("RC_BuildingShell", master),
        "ground": collection("RC_GroundFloorArchitecture", master),
        "upper": collection("RC_UpperFacade", master),
        "ornament": collection("RC_ArchitecturalOrnament", master),
        "windows": collection("RC_Windows", master),
        "signage": collection("RC_Signage", master),
        "interior": collection("RC_InteriorShell", master),
        "fixtures": collection("RC_InteriorFixtures", master),
        "props": collection("RC_InteriorProps", master),
        "anchors": collection("RC_GameplayAnchors", master),
        "nav": collection("RC_Navigation", master),
        "review": collection("RC_ReviewOnly", master),
        "cameras": collection("RC_ReviewCameras", master),
        "lights": collection("RC_ReviewLights", master),
    }
    mats = create_materials()
    layout = create_exterior(groups, mats)
    interior_layout = create_interior(groups, mats, layout)
    cameras = setup_scene(groups, mats, layout, interior_layout)

    scene.render.engine = "BLENDER_EEVEE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.render.resolution_percentage = 100
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.world.color = (0.035, 0.04, 0.045)
    world = scene.world or bpy.data.worlds.new("RC_World")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.035, 0.045, 0.055, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.40

    note = bpy.data.texts.new("REAL_CAMERA_REBUILD_NOTES")
    note.write(
        "Reference-led rebuild, 2026-09-12. Dale Street faces -Y; Z up; metres.\n"
        "Exterior: projecting bays, faceted corner glazing, top-storey arches, deep courses,\n"
        "photographed gallery stairs, shop display window/lower shutter, signs and corner clock.\n"
        "Interior: walkable central aisle, suspended fluorescent ceiling, display cases, shelves,\n"
        "camera silhouettes, tripods and softboxes derived from INT/jh,mamed,nb,nbv.\n"
        "The real Gallery stair entrance is the player route. RC_NAV_GalleryRamp is a hidden\n"
        "authoring proxy and is deliberately excluded from the runtime GLB.\n"
    )
    return groups, mats, cameras


def main():
    groups, mats, cameras = build_scene()
    apply_transforms_and_convert()
    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.camera = cameras[0]
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), check_existing=False)
    export_glb()
    render_reviews(cameras)
    bpy.context.scene.camera = cameras[0]
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), check_existing=False)
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    triangles = sum(sum(max(0, len(poly.vertices) - 2) for poly in obj.data.polygons) for obj in meshes)
    print(f"Real Camera rebuild: {len(meshes)} mesh objects, {triangles} triangles")
    print(f"Saved {BLEND_PATH}")
    print(f"Exported {GLB_PATH}")


if __name__ == "__main__":
    main()
