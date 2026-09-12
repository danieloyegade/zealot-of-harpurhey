"""Build the geometry-first Gulliver's, Manchester architectural reconstruction.

The asset intentionally uses only flat placeholder materials.  Architectural
depth, window rhythm, arches, fascia, corbels, parapet and the wrapped corner
frontage are geometry so the building reads correctly in a neutral clay pass.
"""

from math import cos, pi, radians, sin
from pathlib import Path

import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLEND_PATH = PROJECT_ROOT / "blender" / "source" / "harperhey-gullivers.blend"
GLB_PATH = PROJECT_ROOT / "public" / "assets" / "models" / "harperhey-gullivers.glb"
RENDER_ROOT = PROJECT_ROOT / "renders" / "gullivers-greybox"

WIDTH = 7.40
DEPTH = 16.00
HEIGHT = 11.45
FRONT_Y = -DEPTH / 2
SIDE_X = WIDTH / 2


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    root = bpy.data.collections.new("Gullivers_Architecture")
    bpy.context.scene.collection.children.link(root)
    return root


def collection(root, name):
    col = bpy.data.collections.new(name)
    root.children.link(col)
    return col


def material(name, color, roughness=0.82, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1.0)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def move_to(obj, col):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    col.objects.link(obj)
    return obj


def bevel(obj, width=0.012, segments=1):
    if width > 0:
        mod = obj.modifiers.new("Architectural_Edge", "BEVEL")
        mod.width = width
        mod.segments = segments
    return obj


def box(name, dims, loc, mat, col, edge=0.0, rotation=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    bevel(obj, edge)
    return move_to(obj, col)


def prism(name, footprint, height, z0, mat, col):
    vertices = [(x, y, z0) for x, y in footprint] + [(x, y, z0 + height) for x, y in footprint]
    n = len(footprint)
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, n * 2))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(mat)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    bevel(obj, 0.018)
    return obj


def rail_between(name, start, end, radius, mat, col, vertices=10):
    a, b = Vector(start), Vector(end)
    direction = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=direction.length, location=(a + b) * 0.5)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    obj.data.materials.append(mat)
    return move_to(obj, col)


def front_box(name, width, depth, height, x, z, mat, col, edge=0.0, y=None):
    return box(name, (width, depth, height), (x, FRONT_Y - depth * 0.5 if y is None else y, z), mat, col, edge)


def side_box(name, depth, width, height, y, z, mat, col, edge=0.0, x=None):
    return box(name, (width, depth, height), (SIDE_X + width * 0.5 if x is None else x, y, z), mat, col, edge)


def arch_shape_points(center, width, bottom, spring, segments=12):
    radius = width * 0.5
    points = [(center - radius, bottom), (center + radius, bottom), (center + radius, spring)]
    for i in range(segments + 1):
        angle = i * pi / segments
        points.append((center + radius * cos(angle), spring + radius * sin(angle)))
    points.append((center - radius, spring))
    return points


def extruded_face(name, points, axis_value, thickness, orientation, mat, col):
    # points are (horizontal, z); front extrudes along Y, side along X.
    vertices = []
    for offset in (-thickness * 0.5, thickness * 0.5):
        for horizontal, z in points:
            if orientation == "front":
                vertices.append((horizontal, axis_value + offset, z))
            else:
                vertices.append((axis_value + offset, horizontal, z))
    n = len(points)
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, n * 2))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(mat)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    return obj


def arch_band(name, center, width, spring, band, axis_value, thickness, orientation, mat, col, segments=14):
    outer_r = width * 0.5 + band
    inner_r = width * 0.5
    profile = []
    for i in range(segments + 1):
        a = i * pi / segments
        profile.append((center + outer_r * cos(a), spring + outer_r * sin(a)))
    for i in range(segments, -1, -1):
        a = i * pi / segments
        profile.append((center + inner_r * cos(a), spring + inner_r * sin(a)))
    return extruded_face(name, profile, axis_value, thickness, orientation, mat, col)


def arch_window(name, center, width, bottom, spring, axis_value, orientation, mats, cols, upper=False):
    glass_depth = 0.055
    points = arch_shape_points(center, width, bottom, spring, 14)
    glass = extruded_face(f"{name}_Recessed_Glass", points, axis_value, glass_depth, orientation, mats["glass"], cols["windows"])
    # Frame follows the arch and vertical opening edges.
    arch_band(f"{name}_Arch_Trim", center, width, spring, 0.075 if upper else 0.105, axis_value - 0.08 if orientation == "front" else axis_value + 0.08, 0.10, orientation, mats["green"], cols["trim"])
    r = width * 0.5
    if orientation == "front":
        y = axis_value - 0.08
        for side in (-1, 1):
            box(f"{name}_Vertical_Frame_{side}", (0.085, 0.10, spring - bottom), (center + side * r, y, (bottom + spring) * 0.5), mats["green"], cols["windows"], 0.008)
        box(f"{name}_Sill", (width + 0.24, 0.20, 0.13), (center, y - 0.035, bottom - 0.04), mats["green"], cols["trim"], 0.012)
        box(f"{name}_Mullion_H", (width - 0.12, 0.075, 0.07), (center, y - 0.035, bottom + (spring - bottom) * 0.49), mats["green"], cols["windows"], 0.006)
    else:
        x = axis_value + 0.08
        for side in (-1, 1):
            box(f"{name}_Vertical_Frame_{side}", (0.10, 0.085, spring - bottom), (x, center + side * r, (bottom + spring) * 0.5), mats["green"], cols["windows"], 0.008)
        box(f"{name}_Sill", (0.20, width + 0.24, 0.13), (x + 0.035, center, bottom - 0.04), mats["green"], cols["trim"], 0.012)
        box(f"{name}_Mullion_H", (0.075, width - 0.12, 0.07), (x + 0.035, center, bottom + (spring - bottom) * 0.49), mats["green"], cols["windows"], 0.006)
    # Simplified perforated spandrel rhythm in the first-floor arch heads.
    if not upper:
        for i in range(-2, 3):
            offset = i * width * 0.12
            top = spring + max(0.12, r * (1.0 - abs(offset) / max(r, 0.01)) * 0.48)
            if orientation == "front":
                rail_between(f"{name}_Spandrel_{i}", (center + offset, axis_value - 0.145, spring + 0.05), (center + offset, axis_value - 0.145, top), 0.023, mats["brick_dark"], cols["trim"], 6)
            else:
                rail_between(f"{name}_Spandrel_{i}", (axis_value + 0.145, center + offset, spring + 0.05), (axis_value + 0.145, center + offset, top), 0.023, mats["brick_dark"], cols["trim"], 6)
    return glass


def rectangular_window(name, center, width, bottom, height, axis_value, orientation, mats, cols, segmental=True):
    # A shallow segmental crown preserves the characteristic late-Victorian openings.
    if segmental:
        points = [(center - width / 2, bottom), (center + width / 2, bottom), (center + width / 2, bottom + height - 0.14)]
        for i in range(9):
            t = i / 8
            x = center + width / 2 - width * t
            z = bottom + height - 0.14 + 0.14 * sin(pi * t)
            points.append((x, z))
        points.append((center - width / 2, bottom + height - 0.14))
    else:
        points = [(center - width / 2, bottom), (center + width / 2, bottom), (center + width / 2, bottom + height), (center - width / 2, bottom + height)]
    extruded_face(f"{name}_Recessed_Glass", points, axis_value, 0.055, orientation, mats["glass"], cols["windows"])
    if orientation == "front":
        y = axis_value - 0.08
        for sx in (-1, 1):
            box(f"{name}_Frame_V_{sx}", (0.075, 0.09, height), (center + sx * width / 2, y, bottom + height / 2), mats["green"], cols["windows"], 0.006)
        box(f"{name}_Frame_H", (width, 0.09, 0.07), (center, y, bottom + height * 0.48), mats["green"], cols["windows"], 0.006)
        box(f"{name}_Sill", (width + 0.20, 0.18, 0.12), (center, y - 0.03, bottom - 0.04), mats["green"], cols["trim"], 0.01)
    else:
        x = axis_value + 0.08
        for sy in (-1, 1):
            box(f"{name}_Frame_V_{sy}", (0.09, 0.075, height), (x, center + sy * width / 2, bottom + height / 2), mats["green"], cols["windows"], 0.006)
        box(f"{name}_Frame_H", (0.09, width, 0.07), (x, center, bottom + height * 0.48), mats["green"], cols["windows"], 0.006)
        box(f"{name}_Sill", (0.18, width + 0.20, 0.12), (x + 0.03, center, bottom - 0.04), mats["green"], cols["trim"], 0.01)


def ground_window_front(name, center, width, mats, cols):
    y_glass = FRONT_Y - 0.23
    front_box(f"{name}_Recessed_Glass", width, 0.055, 1.72, center, 1.45, mats["glass"], cols["windows"], y=y_glass)
    front_box(f"{name}_Clerestory_Glass", width, 0.055, 0.42, center, 2.62, mats["glass_light"], cols["windows"], y=y_glass)
    for sx in (-1, 1):
        front_box(f"{name}_Frame_V_{sx}", 0.075, 0.10, 2.35, center + sx * width / 2, 1.58, mats["cream"], cols["windows"], 0.006)
    for z in (0.57, 2.30, 2.88):
        front_box(f"{name}_Frame_H_{z}", width + 0.06, 0.10, 0.075, center, z, mats["cream"], cols["windows"], 0.006)
    front_box(f"{name}_Sill", width + 0.18, 0.22, 0.12, center, 0.55, mats["cream"], cols["trim"], 0.012)
    for i in range(1, max(2, round(width / 0.55))):
        x = center - width / 2 + width * i / max(2, round(width / 0.55))
        front_box(f"{name}_Clerestory_Mullion_{i}", 0.045, 0.08, 0.48, x, 2.62, mats["cream"], cols["windows"])


def ground_window_side(name, center, width, mats, cols):
    x_glass = SIDE_X + 0.23
    side_box(f"{name}_Recessed_Glass", width, 0.055, 1.72, center, 1.45, mats["glass"], cols["windows"], x=x_glass)
    side_box(f"{name}_Clerestory_Glass", width, 0.055, 0.42, center, 2.62, mats["glass_light"], cols["windows"], x=x_glass)
    for sy in (-1, 1):
        side_box(f"{name}_Frame_V_{sy}", 0.10, 0.075, 2.35, center + sy * width / 2, 1.58, mats["cream"], cols["windows"], 0.006)
    for z in (0.57, 2.30, 2.88):
        side_box(f"{name}_Frame_H_{z}", width + 0.06, 0.10, 0.075, center, z, mats["cream"], cols["windows"], 0.006)
    side_box(f"{name}_Sill", width + 0.18, 0.22, 0.12, center, 0.55, mats["cream"], cols["trim"], 0.012)


def tiled_pier_front(name, center, width, mats, cols, white_panel=False):
    front_box(name, width, 0.24, 3.02, center, 1.51, mats["tile"], cols["ground"], 0.012)
    if white_panel:
        front_box(f"{name}_Cream_Inset", width * 0.44, 0.035, 1.20, center, 1.35, mats["tile_cream"], cols["ground"], 0.006, y=FRONT_Y - 0.145)


def tiled_pier_side(name, center, width, mats, cols, white_panel=False):
    side_box(name, width, 0.24, 3.02, center, 1.51, mats["tile"], cols["ground"], 0.012)
    if white_panel:
        side_box(f"{name}_Cream_Inset", width * 0.44, 0.035, 1.20, center, 1.35, mats["tile_cream"], cols["ground"], 0.006, x=SIDE_X + 0.145)


def build_shell(mats, cols):
    footprint = [(-WIDTH / 2, FRONT_Y), (WIDTH / 2 - 0.55, FRONT_Y), (WIDTH / 2, FRONT_Y + 0.55), (WIDTH / 2, DEPTH / 2), (-WIDTH / 2, DEPTH / 2)]
    prism("Gullivers_Shell", footprint, 10.82, 0.0, mats["brick"], cols["shell"])
    # A dark inner volume gives all glazing believable depth without an interior build.
    box("Gullivers_Dark_Interior", (WIDTH - 0.45, DEPTH - 0.45, 9.9), (0, 0, 4.95), mats["interior"], cols["shell"])
    box("Gullivers_Flat_Roof", (WIDTH - 0.35, DEPTH - 0.35, 0.20), (0, 0, 10.78), mats["roof"], cols["roof"], 0.015)


def build_ground_floor(mats, cols):
    # Oldham Street: tiled pier → window → pier → entrance → pier → window → corner pier.
    for args in [
        ("Gullivers_Front_Left_End_Pier", -3.48, 0.34, False),
        ("Gullivers_Front_Left_Window_Pier", -1.76, 0.48, True),
        ("Gullivers_Front_Door_Left_Pier", -0.69, 0.42, True),
        ("Gullivers_Front_Door_Right_Pier", 0.82, 0.44, True),
        ("Gullivers_Front_Right_Window_Pier", 2.17, 0.45, True),
        ("Gullivers_Front_Corner_Pier", 3.42, 0.42, False),
    ]:
        tiled_pier_front(args[0], args[1], args[2], mats, cols, args[3])
    ground_window_front("Gullivers_Front_Left_Pub_Window", -2.58, 1.16, mats, cols)
    ground_window_front("Gullivers_Front_Right_Pub_Window", 1.49, 0.92, mats, cols)
    ground_window_front("Gullivers_Front_Corner_Pub_Window", 2.84, 0.86, mats, cols)

    # Recessed double entrance and its framed overlight.
    front_box("Gullivers_Main_Entrance_Recess", 1.18, 0.06, 2.38, 0.06, 1.20, mats["interior"], cols["doors"], y=FRONT_Y - 0.12)
    for sx in (-1, 1):
        front_box(f"Gullivers_Main_Door_{sx}", 0.53, 0.08, 2.12, 0.06 + sx * 0.285, 1.08, mats["door"], cols["doors"], 0.012, y=FRONT_Y - 0.21)
        for z in (0.60, 1.36):
            front_box(f"Gullivers_Main_Door_{sx}_Panel_{z}", 0.34, 0.025, 0.48, 0.06 + sx * 0.285, z, mats["door_panel"], cols["doors"], 0.018, y=FRONT_Y - 0.265)
    front_box("Gullivers_Main_Door_Overlight", 1.18, 0.055, 0.43, 0.06, 2.66, mats["glass_light"], cols["windows"], y=FRONT_Y - 0.23)
    for x in (-0.53, 0.06, 0.65):
        front_box(f"Gullivers_Main_Door_Overlight_Mullion_{x}", 0.045, 0.08, 0.43, x, 2.66, mats["cream"], cols["windows"], y=FRONT_Y - 0.27)

    # Whittle Street return, five principal pub windows and rear service door.
    pier_positions = [-7.42, -5.74, -3.70, -1.64, 0.42, 2.48, 4.54, 6.20]
    for i, y in enumerate(pier_positions):
        tiled_pier_side(f"Gullivers_Side_Tiled_Pier_{i}", y, 0.42 if i else 0.55, mats, cols, i in (1, 2, 3, 4, 5))
    window_centres = [-6.58, -4.72, -2.67, -0.61, 1.45, 3.51, 5.37]
    window_widths = [1.04, 1.54, 1.55, 1.55, 1.55, 1.55, 1.08]
    for i, (y, width) in enumerate(zip(window_centres, window_widths)):
        if i == len(window_centres) - 1:
            side_box("Gullivers_Side_Service_Door", width, 0.08, 2.28, y, 1.15, mats["door"], cols["doors"], 0.012, x=SIDE_X + 0.21)
            side_box("Gullivers_Side_Service_Door_Panel", width * 0.65, 0.025, 0.62, y, 0.72, mats["door_panel"], cols["doors"], 0.015, x=SIDE_X + 0.265)
            side_box("Gullivers_Side_Service_Overlight", width, 0.055, 0.42, y, 2.62, mats["glass_light"], cols["windows"], x=SIDE_X + 0.23)
        else:
            ground_window_side(f"Gullivers_Side_Pub_Window_{i}", y, width, mats, cols)

    # Continuous dark tile plinth and cream inset rails wrap both elevations.
    front_box("Gullivers_Front_Tile_Plinth", WIDTH, 0.27, 0.34, 0, 0.17, mats["tile_dark"], cols["ground"], 0.008)
    side_box("Gullivers_Side_Tile_Plinth", DEPTH - 0.55, 0.27, 0.34, 0.26, 0.17, mats["tile_dark"], cols["ground"], 0.008)
    front_box("Gullivers_Front_Cream_Tile_Rail", WIDTH - 0.35, 0.035, 0.18, 0, 0.72, mats["tile_cream"], cols["ground"], y=FRONT_Y - 0.145)
    side_box("Gullivers_Side_Cream_Tile_Rail", DEPTH - 0.90, 0.035, 0.18, 0.30, 0.72, mats["tile_cream"], cols["ground"], x=SIDE_X + 0.145)

    # Deep sign fascia and layered cornice wrap the corner.
    for name, z, height, depth, mat in [
        ("Fascia", 3.25, 0.58, 0.30, mats["green"]),
        ("Lower_Moulding", 2.98, 0.13, 0.42, mats["cream"]),
        ("Upper_Cornice", 3.62, 0.20, 0.48, mats["cream"]),
        ("Dentil_Band", 3.46, 0.11, 0.39, mats["cream_dark"]),
    ]:
        front_box(f"Gullivers_Front_{name}", WIDTH + (0.22 if name != "Fascia" else 0), depth, height, 0, z, mat, cols["cornice"], 0.012)
        side_box(f"Gullivers_Side_{name}", DEPTH + (0.22 if name != "Fascia" else 0), depth, height, 0, z, mat, cols["cornice"], 0.012)
    # Dentil blocks and sculptural corbel approximations.
    for i in range(24):
        x = -3.45 + i * 6.9 / 23
        front_box(f"Gullivers_Front_Dentil_{i:02d}", 0.13, 0.46, 0.12, x, 3.49, mats["cream_dark"], cols["cornice"], 0.006)
    for i in range(42):
        y = -7.65 + i * 15.3 / 41
        side_box(f"Gullivers_Side_Dentil_{i:02d}", 0.13, 0.46, 0.12, y, 3.49, mats["cream_dark"], cols["cornice"], 0.006)
    for i, x in enumerate((-3.08, -0.72, 2.38, 3.38)):
        front_box(f"Gullivers_Front_Corbel_{i}_Top", 0.30, 0.42, 0.54, x, 3.30, mats["cream"], cols["cornice"], 0.045)
        front_box(f"Gullivers_Front_Corbel_{i}_Drop", 0.20, 0.48, 0.30, x, 3.02, mats["cream"], cols["cornice"], 0.035)
    for i, y in enumerate((-6.85, -3.8, -0.75, 2.3, 5.35)):
        side_box(f"Gullivers_Side_Corbel_{i}_Top", 0.30, 0.42, 0.54, y, 3.30, mats["cream"], cols["cornice"], 0.045)
        side_box(f"Gullivers_Side_Corbel_{i}_Drop", 0.20, 0.48, 0.30, y, 3.02, mats["cream"], cols["cornice"], 0.035)


def build_upper_facades(mats, cols):
    # Strong horizontal courses separating ground, first and second storeys.
    for name, z, h, d in (("First_Sill_Course", 4.08, 0.22, 0.25), ("First_Upper_Course", 7.43, 0.26, 0.28), ("Second_Sill_Course", 7.78, 0.15, 0.22)):
        front_box(f"Gullivers_Front_{name}", WIDTH, d, h, 0, z, mats["green"], cols["trim"], 0.01)
        side_box(f"Gullivers_Side_{name}", DEPTH, d, h, 0, z, mats["green"], cols["trim"], 0.01)

    # Oldham Street: unmistakable triple arch over tall first-floor windows.
    for i, x in enumerate((-2.38, 0.0, 2.38)):
        arch_window(f"Gullivers_Front_First_Window_{i}", x, 1.38, 4.38, 6.30, FRONT_Y - 0.145, "front", mats, cols)
        rectangular_window(f"Gullivers_Front_Second_Window_{i}", x, 1.28, 8.05, 2.20, FRONT_Y - 0.145, "front", mats, cols, True)
        # Painted skewback blocks above the upper windows.
        front_box(f"Gullivers_Front_Second_Keystone_{i}", 0.32, 0.14, 0.37, x, 10.22, mats["green"], cols["trim"], 0.01)
    # Green-linked arch spring course and central decorative drops.
    front_box("Gullivers_Front_Arch_Spring_Course", 6.72, 0.20, 0.22, 0, 6.30, mats["green"], cols["trim"], 0.012)
    for i, x in enumerate((-1.19, 1.19)):
        front_box(f"Gullivers_Front_Arch_Decorative_Drop_{i}", 0.24, 0.26, 0.50, x, 6.58, mats["green"], cols["trim"], 0.025)

    # Whittle Street continuation: five bays, matching arch cadence and upper windows.
    side_bays = (-6.25, -3.55, -0.85, 1.85, 4.55)
    for i, y in enumerate(side_bays):
        arch_window(f"Gullivers_Side_First_Window_{i}", y, 1.32, 4.38, 6.28, SIDE_X + 0.145, "side", mats, cols)
        rectangular_window(f"Gullivers_Side_Second_Window_{i}", y, 1.20, 8.05, 2.18, SIDE_X + 0.145, "side", mats, cols, True)
        side_box(f"Gullivers_Side_Second_Keystone_{i}", 0.32, 0.14, 0.37, y, 10.20, mats["green"], cols["trim"], 0.01)
    side_box("Gullivers_Side_Arch_Spring_Course", 13.65, 0.20, 0.22, -0.85, 6.28, mats["green"], cols["trim"], 0.012)
    for i, y in enumerate((-4.90, -2.20, 0.50, 3.20)):
        side_box(f"Gullivers_Side_Arch_Decorative_Drop_{i}", 0.24, 0.26, 0.50, y, 6.56, mats["green"], cols["trim"], 0.025)


def build_roof_and_sign(mats, cols):
    # Layered parapet/coping defines the flat-roof silhouette.
    front_box("Gullivers_Front_Parapet_Band", WIDTH, 0.24, 0.42, 0, 10.80, mats["green"], cols["roof"], 0.01)
    side_box("Gullivers_Side_Parapet_Band", DEPTH, 0.24, 0.42, 0, 10.80, mats["green"], cols["roof"], 0.01)
    front_box("Gullivers_Front_Parapet_Coping", WIDTH + 0.18, 0.38, 0.18, 0, 11.10, mats["green_dark"], cols["roof"], 0.018)
    side_box("Gullivers_Side_Parapet_Coping", DEPTH + 0.18, 0.38, 0.18, 0, 11.10, mats["green_dark"], cols["roof"], 0.018)
    box("Gullivers_Rear_Chimney", (0.72, 0.72, 1.55), (-2.25, 5.85, 11.30), mats["brick"], cols["roof"], 0.012)
    box("Gullivers_Rear_Chimney_Cap", (0.88, 0.88, 0.16), (-2.25, 5.85, 12.10), mats["green_dark"], cols["roof"], 0.012)

    # Simplified projecting hanging pub sign and bracket on the corner elevation.
    sign_x = 3.98
    sign_y = -5.90
    box("Gullivers_Hanging_Sign_Board", (0.12, 0.92, 1.18), (sign_x, sign_y, 6.55), mats["green_dark"], cols["signs"], 0.035)
    box("Gullivers_Hanging_Sign_Inset", (0.025, 0.72, 0.91), (sign_x + 0.071, sign_y, 6.55), mats["cream"] , cols["signs"], 0.02)
    rail_between("Gullivers_Hanging_Sign_Arm", (SIDE_X + 0.08, sign_y, 7.35), (sign_x, sign_y, 7.35), 0.045, mats["metal"], cols["signs"], 10)
    rail_between("Gullivers_Hanging_Sign_Diagonal", (SIDE_X + 0.08, sign_y, 7.35), (sign_x, sign_y, 7.04), 0.028, mats["metal"], cols["signs"], 8)
    for y in (sign_y - 0.34, sign_y + 0.34):
        rail_between(f"Gullivers_Hanging_Sign_Hanger_{y}", (sign_x, y, 7.35), (sign_x, y, 7.15), 0.018, mats["metal"], cols["signs"], 6)


def add_camera(name, location, target, lens, col):
    bpy.ops.object.camera_add(location=location)
    camera = bpy.context.object
    camera.name = name
    camera.data.name = f"{name}_Data"
    camera.data.lens = lens
    camera.data.sensor_width = 36
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    return move_to(camera, col)


def configure_scene(mats, cols):
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.world.color = (0.035, 0.045, 0.06)

    box("Gullivers_Render_Ground", (30, 34, 0.12), (0, 0, -0.07), mats["ground"], cols["render"])
    bpy.ops.object.light_add(type="AREA", location=(-7.5, -10.5, 15.0))
    key = bpy.context.object
    key.name = "Gullivers_Render_Key"
    key.data.energy = 1700
    key.data.shape = "DISK"
    key.data.size = 8.0
    key.rotation_euler = (Vector((0, 0, 5.2)) - key.location).to_track_quat("-Z", "Y").to_euler()
    move_to(key, cols["render"])
    bpy.ops.object.light_add(type="AREA", location=(9.0, -1.5, 9.0))
    fill = bpy.context.object
    fill.name = "Gullivers_Render_Fill"
    fill.data.energy = 950
    fill.data.size = 7.0
    fill.rotation_euler = (Vector((0, 0, 5.0)) - fill.location).to_track_quat("-Z", "Y").to_euler()
    move_to(fill, cols["render"])
    bpy.ops.object.light_add(type="AREA", location=(-4.0, 8.0, 11.0))
    rim = bpy.context.object
    rim.name = "Gullivers_Render_Rim"
    rim.data.energy = 1150
    rim.data.size = 6.0
    rim.rotation_euler = (Vector((0, 0, 6.0)) - rim.location).to_track_quat("-Z", "Y").to_euler()
    move_to(rim, cols["render"])

    return {
        "front": add_camera("Gullivers_Camera_Front", (0, -38.0, 5.9), (0, -1.4, 5.55), 58, cols["render"]),
        "corner": add_camera("Gullivers_Camera_Corner", (15.5, -23.0, 8.2), (0.3, -1.0, 5.1), 52, cols["render"]),
        "side": add_camera("Gullivers_Camera_Whittle_Street", (30.0, 0.2, 6.0), (1.8, 0.0, 5.25), 54, cols["render"]),
        "elevated": add_camera("Gullivers_Camera_Elevated", (16.5, -22.0, 14.5), (0.0, -0.3, 5.5), 55, cols["render"]),
    }


def render_views(cameras):
    RENDER_ROOT.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for key, filename in (
        ("front", "gullivers-clay-front.png"),
        ("corner", "gullivers-clay-three-quarter.png"),
        ("side", "gullivers-clay-whittle-street.png"),
        ("elevated", "gullivers-clay-elevated.png"),
    ):
        scene.camera = cameras[key]
        scene.render.filepath = str(RENDER_ROOT / filename)
        bpy.ops.render.render(write_still=True)


def apply_export_transforms(root):
    export_objects = []
    for col in root.children:
        if col.name == "Gullivers_Render_Setup":
            continue
        for obj in col.objects:
            if obj.type in {"MESH", "CURVE"}:
                export_objects.append(obj)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in export_objects:
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return export_objects


def build_runtime_meshes(root):
    """Duplicate and consolidate editable parts by architectural collection.

    The .blend keeps every named component separate.  The GLB uses one
    multi-material mesh per major component collection to keep Three.js draw
    traversal practical while preserving logical runtime nodes.
    """
    runtime_col = bpy.data.collections.new("Gullivers_Runtime_Export")
    bpy.context.scene.collection.children.link(runtime_col)
    runtime_objects = []
    for source_col in root.children:
        if source_col.name == "Gullivers_Render_Setup":
            continue
        duplicates = []
        for source in source_col.objects:
            if source.type not in {"MESH", "CURVE"}:
                continue
            duplicate = source.copy()
            duplicate.data = source.data.copy()
            runtime_col.objects.link(duplicate)
            bpy.ops.object.select_all(action="DESELECT")
            duplicate.select_set(True)
            bpy.context.view_layer.objects.active = duplicate
            if duplicate.type != "MESH" or duplicate.modifiers:
                bpy.ops.object.convert(target="MESH")
                duplicate = bpy.context.object
            duplicates.append(duplicate)
        if not duplicates:
            continue
        bpy.ops.object.select_all(action="DESELECT")
        for duplicate in duplicates:
            duplicate.select_set(True)
        bpy.context.view_layer.objects.active = duplicates[0]
        if len(duplicates) > 1:
            bpy.ops.object.join()
        runtime = bpy.context.object
        runtime.name = f"Gullivers_Runtime_{source_col.name.removeprefix('Gullivers_')}"
        runtime.data.name = f"{runtime.name}_Mesh"
        runtime_objects.append(runtime)
    return runtime_objects


def main():
    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
    root = clear_scene()
    cols = {
        "shell": collection(root, "Gullivers_Shell"),
        "ground": collection(root, "Gullivers_GroundFloor"),
        "windows": collection(root, "Gullivers_Windows"),
        "doors": collection(root, "Gullivers_Doors"),
        "cornice": collection(root, "Gullivers_Cornice"),
        "trim": collection(root, "Gullivers_UpperTrim"),
        "signs": collection(root, "Gullivers_SignStructures"),
        "roof": collection(root, "Gullivers_Roof"),
        "render": collection(root, "Gullivers_Render_Setup"),
    }
    mats = {
        "brick": material("Gullivers_Placeholder_Brick", (0.43, 0.20, 0.13)),
        "brick_dark": material("Gullivers_Placeholder_Brick_Infill", (0.25, 0.105, 0.075)),
        "green": material("Gullivers_Placeholder_Green_Trim", (0.055, 0.19, 0.125)),
        "green_dark": material("Gullivers_Placeholder_Dark_Green", (0.025, 0.095, 0.065)),
        "tile": material("Gullivers_Placeholder_Green_Tile", (0.035, 0.245, 0.145), 0.62),
        "tile_dark": material("Gullivers_Placeholder_Dark_Tile_Plinth", (0.025, 0.095, 0.07), 0.68),
        "tile_cream": material("Gullivers_Placeholder_Cream_Tile_Inlay", (0.74, 0.70, 0.59), 0.70),
        "cream": material("Gullivers_Placeholder_Cream_Joinery", (0.76, 0.70, 0.59), 0.73),
        "cream_dark": material("Gullivers_Placeholder_Cornice_Shadow", (0.53, 0.48, 0.40), 0.78),
        "glass": material("Gullivers_Placeholder_Dark_Glass", (0.025, 0.045, 0.045), 0.35),
        "glass_light": material("Gullivers_Placeholder_Clerestory_Glass", (0.15, 0.22, 0.20), 0.32),
        "door": material("Gullivers_Placeholder_Door", (0.035, 0.13, 0.085), 0.74),
        "door_panel": material("Gullivers_Placeholder_Door_Panels", (0.055, 0.20, 0.125), 0.72),
        "interior": material("Gullivers_Placeholder_Interior", (0.012, 0.014, 0.014), 0.96),
        "roof": material("Gullivers_Placeholder_Roof", (0.07, 0.075, 0.075), 0.94),
        "metal": material("Gullivers_Placeholder_Black_Metal", (0.035, 0.04, 0.04), 0.55, 0.35),
        "ground": material("Gullivers_Render_Ground_Material", (0.075, 0.085, 0.09), 0.92),
    }

    build_shell(mats, cols)
    build_ground_floor(mats, cols)
    build_upper_facades(mats, cols)
    build_roof_and_sign(mats, cols)
    cameras = configure_scene(mats, cols)
    render_views(cameras)
    export_objects = apply_export_transforms(root)

    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    runtime_objects = build_runtime_meshes(root)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in runtime_objects:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
    )
    mesh_count = sum(1 for obj in export_objects if obj.type == "MESH")
    runtime_mesh_count = sum(1 for obj in runtime_objects if obj.type == "MESH")
    vertex_count = sum(len(obj.data.vertices) for obj in runtime_objects if obj.type == "MESH")
    triangle_count = sum(len(poly.vertices) - 2 for obj in runtime_objects if obj.type == "MESH" for poly in obj.data.polygons)
    print(f"GULLIVERS_BUILD_COMPLETE editable_meshes={mesh_count} runtime_meshes={runtime_mesh_count} vertices={vertex_count} triangles={triangle_count}")
    print(f"BLEND={BLEND_PATH}")
    print(f"GLB={GLB_PATH}")


if __name__ == "__main__":
    main()
