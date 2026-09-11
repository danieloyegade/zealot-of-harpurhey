"""Create the geometry-first Dreams approval model.

This asset intentionally contains no photographic or image textures.  It is a
modular, bevelled greybox used to approve proportions and construction before
the UV and material pass begins.
"""

from math import atan2, hypot, radians
from pathlib import Path

import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLEND_PATH = PROJECT_ROOT / "blender" / "source" / "harperhey-dreams-greybox.blend"
GLB_PATH = PROJECT_ROOT / "public" / "assets" / "models" / "harperhey-dreams-greybox.glb"
RENDER_ROOT = PROJECT_ROOT / "renders" / "dreams-greybox"
FRONT_RENDER = RENDER_ROOT / "dreams-greybox-front.png"
THREE_QUARTER_RENDER = RENDER_ROOT / "dreams-greybox-three-quarter.png"
WIREFRAME_RENDER = RENDER_ROOT / "dreams-greybox-wireframe.png"

WIDTH = 18.0
DEPTH = 8.5
EAVE_HEIGHT = 5.62
PEAK_HEIGHT = 8.18
FRONT_Y = -DEPTH / 2
ASSET_COLLECTION = "Dreams_Greybox_Architecture"


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for col in list(bpy.data.collections):
        if col.name != "Collection":
            bpy.data.collections.remove(col)
    root = bpy.data.collections.get("Collection")
    if root:
        root.name = ASSET_COLLECTION
    return root


def move_to(obj, col):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    col.objects.link(obj)
    return obj


def material(name, color, roughness=0.78, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1.0)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def add_edge_treatment(obj, width):
    if width <= 0:
        return obj
    bevel = obj.modifiers.new("Approval_Bevel", "BEVEL")
    bevel.width = width
    bevel.segments = 1
    try:
        weighted = obj.modifiers.new("Approval_Weighted_Normals", "WEIGHTED_NORMAL")
        weighted.keep_sharp = True
    except (RuntimeError, TypeError):
        pass
    return obj


def box(name, dimensions, location, mat, col, bevel=0.0, rotation=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    add_edge_treatment(obj, bevel)
    return move_to(obj, col)


def mesh_object(name, vertices, faces, mat, col, bevel=0.0):
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(mat)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    add_edge_treatment(obj, bevel)
    return obj


def cylinder(name, radius, depth, location, mat, col, vertices=12, rotation=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    obj.data.materials.append(mat)
    return move_to(obj, col)


def rail_between(name, start, end, radius, mat, col, vertices=12):
    a = Vector(start)
    b = Vector(end)
    direction = b - a
    obj = cylinder(name, radius, direction.length, (a + b) * 0.5, mat, col, vertices)
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    return obj


def text_object(name, body, location, size, mat, col):
    bpy.ops.object.text_add(location=location, rotation=(radians(90), 0.0, 0.0))
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Curve"
    obj.data.body = body
    obj.data.align_x = "CENTER"
    obj.data.align_y = "CENTER"
    obj.data.size = size
    obj.data.resolution_u = 1
    obj.data.extrude = 0.012
    obj.data.bevel_depth = 0.0
    obj.data.bevel_resolution = 0
    font_path = Path("/System/Library/Fonts/Supplemental/Georgia.ttf")
    if font_path.exists():
        obj.data.font = bpy.data.fonts.load(str(font_path), check_existing=True)
    obj.data.materials.append(mat)
    return move_to(obj, col)


def curve_stroke(name, points, radius, mat, col):
    curve = bpy.data.curves.new(f"{name}_Curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = radius
    curve.bevel_resolution = 2
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for point, coordinate in zip(spline.bezier_points, points):
        point.co = coordinate
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    curve.materials.append(mat)
    obj = bpy.data.objects.new(name, curve)
    col.objects.link(obj)
    return obj


def build_shell(materials, col):
    # Main rectangular volume and a true triangular-prism gable.
    box(
        "Dreams_Main_Shell",
        (WIDTH, DEPTH, EAVE_HEIGHT),
        (0.0, 0.0, EAVE_HEIGHT * 0.5),
        materials["wall"], col, 0.035,
    )
    half_w = WIDTH * 0.5
    half_d = DEPTH * 0.5
    vertices = [
        (-half_w, -half_d, EAVE_HEIGHT),
        (half_w, -half_d, EAVE_HEIGHT),
        (0.0, -half_d, PEAK_HEIGHT),
        (-half_w, half_d, EAVE_HEIGHT),
        (half_w, half_d, EAVE_HEIGHT),
        (0.0, half_d, PEAK_HEIGHT),
    ]
    faces = [(0, 2, 1), (3, 4, 5), (0, 1, 4, 3), (0, 3, 5, 2), (2, 5, 4, 1)]
    mesh_object("Dreams_Gable_Volume", vertices, faces, materials["cladding"], col, 0.02)

    # Front upper wall is layered rather than drawn onto one plane.
    box("Dreams_Left_Cladding_Wing", (3.18, 0.22, 2.18), (-7.41, FRONT_Y - 0.08, 4.52), materials["cladding"], col, 0.018)
    box("Dreams_Central_Signboard", (11.14, 0.34, 2.16), (-0.25, FRONT_Y - 0.17, 4.51), materials["signboard"], col, 0.035)
    box("Dreams_Right_Cladding_Wing", (3.55, 0.22, 2.18), (7.22, FRONT_Y - 0.08, 4.52), materials["cladding"], col, 0.018)
    box("Dreams_Signboard_Shadow_Reveal", (11.34, 0.12, 2.32), (-0.25, FRONT_Y - 0.035, 4.51), materials["recess"], col, 0.01)

    # Horizontal cladding joints and the pronounced central gable seam.
    for index, z in enumerate((4.16, 4.88, 5.57)):
        box(f"Dreams_Cladding_Joint_Left_{index}", (3.10, 0.025, 0.025), (-7.41, FRONT_Y - 0.205, z), materials["joint"], col)
        box(f"Dreams_Cladding_Joint_Right_{index}", (3.48, 0.025, 0.025), (7.22, FRONT_Y - 0.205, z), materials["joint"], col)
    box("Dreams_Gable_Centre_Seam", (0.035, 0.035, 2.48), (0.0, FRONT_Y - 0.14, 6.84), materials["joint"], col)
    box("Dreams_Gable_Horizontal_Seam", (12.0, 0.035, 0.035), (0.0, FRONT_Y - 0.14, 6.43), materials["joint"], col)

    # Dimensional logo for proportion approval; it receives a decal/material later.
    logo = text_object("Dreams_Sign_Letters", "Dreams", (-0.25, FRONT_Y - 0.38, 4.63), 1.22, materials["lettering"], col)
    logo.scale.x = 1.15
    curve_stroke(
        "Dreams_Sign_Swoosh",
        [(-2.88, FRONT_Y - 0.40, 4.12), (-1.45, FRONT_Y - 0.40, 4.19), (0.15, FRONT_Y - 0.40, 4.05), (1.60, FRONT_Y - 0.40, 4.02), (2.72, FRONT_Y - 0.40, 4.16)],
        0.018, materials["lettering"], col,
    )


def build_roof(materials, col):
    rise = PEAK_HEIGHT - EAVE_HEIGHT
    angle = atan2(rise, WIDTH * 0.5)
    length = hypot(WIDTH * 0.5 + 0.34, rise)
    box("Dreams_Left_Roof_Plane", (length, DEPTH + 0.72, 0.22), (-4.60, 0.0, 6.94), materials["roof"], col, 0.025, rotation=(0.0, -angle, 0.0))
    box("Dreams_Right_Roof_Plane", (length, DEPTH + 0.72, 0.22), (4.60, 0.0, 6.94), materials["roof"], col, 0.025, rotation=(0.0, angle, 0.0))
    box("Dreams_Ridge_Cap", (0.22, DEPTH + 0.96, 0.18), (0.0, 0.0, PEAK_HEIGHT + 0.06), materials["roof_trim"], col, 0.025)

    for side, y in (("Front", FRONT_Y - 0.25), ("Rear", -FRONT_Y + 0.25)):
        rail_between(f"Dreams_{side}_Left_Raking_Fascia", (-9.18, y, 5.62), (0.0, y, 8.23), 0.07, materials["roof_trim"], col, 8)
        rail_between(f"Dreams_{side}_Right_Raking_Fascia", (0.0, y, 8.23), (9.18, y, 5.62), 0.07, materials["roof_trim"], col, 8)
        rail_between(f"Dreams_{side}_Gutter", (-9.16, y, 5.52), (9.16, y, 5.52), 0.085, materials["gutter"], col, 12)
    rail_between("Dreams_Right_Downpipe", (8.62, FRONT_Y - 0.27, 0.35), (8.62, FRONT_Y - 0.27, 5.50), 0.065, materials["gutter"], col, 12)
    cylinder("Dreams_Right_Downpipe_Hopper", 0.13, 0.24, (8.62, FRONT_Y - 0.27, 5.40), materials["gutter"], col, 10)


def build_shutter(name, x0, x1, materials, col):
    width = x1 - x0
    centre = (x0 + x1) * 0.5
    bottom = 0.55
    top = 3.26
    height = top - bottom
    # Dark opening, inset curtain, projecting guides and hood.
    box(f"{name}_Opening", (width + 0.22, 0.20, height + 0.22), (centre, FRONT_Y - 0.015, bottom + height * 0.5), materials["recess"], col, 0.018)
    box(f"{name}_Curtain", (width - 0.15, 0.10, height - 0.12), (centre, FRONT_Y - 0.11, bottom + height * 0.5), materials["shutter"], col, 0.012)
    box(f"{name}_Left_Guide", (0.16, 0.20, height + 0.12), (x0, FRONT_Y - 0.24, bottom + height * 0.5), materials["shutter_frame"], col, 0.018)
    box(f"{name}_Right_Guide", (0.16, 0.20, height + 0.12), (x1, FRONT_Y - 0.24, bottom + height * 0.5), materials["shutter_frame"], col, 0.018)
    box(f"{name}_Head_Box", (width + 0.18, 0.25, 0.25), (centre, FRONT_Y - 0.25, top + 0.09), materials["shutter_frame"], col, 0.025)
    box(f"{name}_Bottom_Rail", (width - 0.05, 0.18, 0.13), (centre, FRONT_Y - 0.23, bottom + 0.03), materials["shutter_frame"], col, 0.018)

    # Actual corrugation catches light from oblique angles and can later be
    # simplified into a normal map for lower LODs.
    slat_count = 34
    usable_height = height - 0.20
    step = usable_height / slat_count
    for index in range(slat_count):
        z = bottom + 0.13 + index * step
        box(
            f"{name}_Corrugation_{index:02d}",
            (width - 0.30, 0.075, step * 0.34),
            (centre, FRONT_Y - 0.205, z),
            materials["shutter_highlight"], col, 0.008,
        )


def build_ground_frontage(materials, col):
    build_shutter("Dreams_Left_Shutter", -8.43, -2.32, materials, col)
    build_shutter("Dreams_Centre_Shutter", -2.18, -0.08, materials, col)
    build_shutter("Dreams_Right_Shutter", 0.08, 5.28, materials, col)
    box("Dreams_Continuous_Fascia", (13.95, 0.38, 0.26), (-1.55, FRONT_Y - 0.22, 3.40), materials["shutter_frame"], col, 0.028)
    box("Dreams_Shutter_Brick_Plith", (13.88, 0.54, 0.47), (-1.55, FRONT_Y - 0.02, 0.235), materials["brick"], col, 0.025)

    # Separate brick return with a recessed noticeboard.
    box("Dreams_Right_Brick_Return", (3.55, 0.42, 3.44), (7.10, FRONT_Y - 0.10, 1.72), materials["brick"], col, 0.025)
    # Mortar-course relief is geometry in this approval pass so the brick scale
    # can be judged before the final normal/roughness texture is authored.
    for row in range(16):
        z = 0.20 + row * 0.205
        box(f"Dreams_Brick_Course_{row:02d}", (3.47, 0.025, 0.018), (7.10, FRONT_Y - 0.325, z), materials["mortar"], col)
        offset = 0.22 if row % 2 else 0.0
        for column in range(5):
            x = 5.55 + offset + column * 0.68
            if x < 8.73:
                box(f"Dreams_Brick_Joint_{row:02d}_{column:02d}", (0.018, 0.025, 0.19), (x, FRONT_Y - 0.325, z + 0.10), materials["mortar"], col)

    box("Dreams_Notice_Recess", (1.56, 0.10, 1.84), (6.91, FRONT_Y - 0.36, 1.94), materials["recess"], col, 0.025)
    box("Dreams_Notice_Back", (1.36, 0.05, 1.62), (6.91, FRONT_Y - 0.425, 1.94), materials["notice"], col, 0.018)
    for name, dims, loc in (
        ("Top", (1.62, 0.13, 0.09), (6.91, FRONT_Y - 0.46, 2.84)),
        ("Bottom", (1.62, 0.13, 0.09), (6.91, FRONT_Y - 0.46, 1.04)),
        ("Left", (0.09, 0.13, 1.88), (6.15, FRONT_Y - 0.46, 1.94)),
        ("Right", (0.09, 0.13, 1.88), (7.67, FRONT_Y - 0.46, 1.94)),
    ):
        box(f"Dreams_Notice_Frame_{name}", dims, loc, materials["shutter_frame"], col, 0.018)
    box("Dreams_Notice_Yellow_Band", (1.34, 0.035, 0.40), (6.91, FRONT_Y - 0.50, 1.48), materials["accent"], col, 0.01)


def ramp_mesh(name, x0, x1, y0, y1, top0, top1, thickness, mat, col):
    vertices = [
        (x0, y0, top0), (x1, y0, top1), (x1, y1, top1), (x0, y1, top0),
        (x0, y0, top0 - thickness), (x1, y0, max(0.0, top1 - thickness)),
        (x1, y1, max(0.0, top1 - thickness)), (x0, y1, top0 - thickness),
    ]
    faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    return mesh_object(name, vertices, faces, mat, col, 0.025)


def build_accessibility(materials, col):
    platform_x0, platform_x1 = -3.20, 3.55
    rear_y, front_y = FRONT_Y - 0.20, FRONT_Y - 1.52
    platform_top = 0.62
    box("Dreams_Platform_Brick_Base", (platform_x1 - platform_x0, 1.46, 0.52), ((platform_x0 + platform_x1) * 0.5, (rear_y + front_y) * 0.5, 0.26), materials["brick"], col, 0.025)
    box("Dreams_Platform_Concrete_Landing", (platform_x1 - platform_x0, 1.50, 0.16), ((platform_x0 + platform_x1) * 0.5, (rear_y + front_y) * 0.5, platform_top - 0.08), materials["concrete"], col, 0.025)

    ramp_x0, ramp_x1 = 3.55, 7.00
    ramp_mesh("Dreams_Access_Ramp", ramp_x0, ramp_x1, front_y, rear_y, platform_top, 0.14, 0.16, materials["concrete"], col)
    box("Dreams_Ramp_Lower_Landing", (0.90, 1.50, 0.14), (7.45, (rear_y + front_y) * 0.5, 0.07), materials["concrete"], col, 0.02)

    rail_top = 1.58
    rail_mid = 1.12
    for side_index, y in enumerate((rear_y - 0.02, front_y + 0.02)):
        platform_posts = (platform_x0, -1.55, 0.15, 1.85, platform_x1)
        for post_index, x in enumerate(platform_posts):
            rail_between(f"Dreams_Platform_Rail_Post_{side_index}_{post_index}", (x, y, platform_top), (x, y, rail_top), 0.035, materials["rail"], col, 12)
        rail_between(f"Dreams_Platform_Rail_Top_{side_index}", (platform_x0, y, rail_top), (platform_x1, y, rail_top), 0.045, materials["rail"], col, 12)
        rail_between(f"Dreams_Platform_Rail_Mid_{side_index}", (platform_x0, y, rail_mid), (platform_x1, y, rail_mid), 0.035, materials["rail"], col, 12)

        def ramp_surface(x):
            t = (x - ramp_x0) / (ramp_x1 - ramp_x0)
            return platform_top + (0.14 - platform_top) * t

        for post_index, x in enumerate((ramp_x0, 4.75, 5.90, ramp_x1)):
            surface = ramp_surface(x)
            top = surface + 0.96
            rail_between(f"Dreams_Ramp_Rail_Post_{side_index}_{post_index}", (x, y, surface), (x, y, top), 0.035, materials["rail"], col, 12)
        rail_between(f"Dreams_Ramp_Rail_Top_{side_index}", (ramp_x0, y, platform_top + 0.96), (ramp_x1, y, 1.10), 0.045, materials["rail"], col, 12)
        rail_between(f"Dreams_Ramp_Rail_Mid_{side_index}", (ramp_x0, y, platform_top + 0.50), (ramp_x1, y, 0.64), 0.035, materials["rail"], col, 12)

    # End returns tie the two rail runs together as in the reference.
    rail_between("Dreams_Rail_Left_Return_Top", (platform_x0, rear_y, rail_top), (platform_x0, front_y, rail_top), 0.045, materials["rail"], col, 12)
    rail_between("Dreams_Rail_Ramp_Return_Top", (ramp_x1, rear_y, 1.10), (ramp_x1, front_y, 1.10), 0.045, materials["rail"], col, 12)


def build_fixtures(materials, col):
    # Four upper and four lower fluorescent housings, without emissive materials.
    for row, (z, depth) in enumerate(((5.73, 0.26), (3.30, 0.34))):
        for index, x in enumerate((-4.55, -1.52, 1.52, 4.55)):
            box(f"Dreams_Light_Housing_{row}_{index}", (2.70, 0.16, 0.12), (x, FRONT_Y - depth, z), materials["fixture"], col, 0.025)
            box(f"Dreams_Light_Tube_{row}_{index}", (2.48, 0.075, 0.045), (x, FRONT_Y - depth - 0.09, z - 0.025), materials["tube"], col, 0.018)

    # Hexagonal alarm with a recessed face.
    cylinder("Dreams_Alarm_Body", 0.18, 0.16, (-7.44, FRONT_Y - 0.25, 4.56), materials["alarm"], col, 6, rotation=(radians(90), 0.0, 0.0))
    cylinder("Dreams_Alarm_Face", 0.10, 0.025, (-7.44, FRONT_Y - 0.35, 4.56), materials["recess"], col, 12, rotation=(radians(90), 0.0, 0.0))

    box("Dreams_CCTV_Wall_Plate", (0.15, 0.08, 0.22), (-6.84, FRONT_Y - 0.22, 3.74), materials["fixture"], col, 0.018)
    rail_between("Dreams_CCTV_Arm", (-6.84, FRONT_Y - 0.28, 3.73), (-6.78, FRONT_Y - 0.48, 3.68), 0.025, materials["fixture"], col, 10)
    box("Dreams_CCTV_Camera", (0.23, 0.30, 0.14), (-6.76, FRONT_Y - 0.57, 3.68), materials["fixture"], col, 0.025, rotation=(radians(8), 0.0, radians(-5)))
    cylinder("Dreams_CCTV_Lens", 0.045, 0.025, (-6.76, FRONT_Y - 0.73, 3.66), materials["recess"], col, 12, rotation=(radians(90), 0.0, 0.0))


def build_model(materials, col):
    build_shell(materials, col)
    build_roof(materials, col)
    build_ground_frontage(materials, col)
    build_accessibility(materials, col)
    build_fixtures(materials, col)
    return list(col.objects)


def materials():
    # Flat identifiers only: no image textures or final surface authoring.
    return {
        "wall": material("Dreams_Greybox_Wall", (0.33, 0.35, 0.36), 0.90),
        "cladding": material("Dreams_Greybox_Cladding", (0.48, 0.50, 0.49), 0.82),
        "signboard": material("Dreams_Greybox_Signboard", (0.66, 0.67, 0.64), 0.80),
        "lettering": material("Dreams_Greybox_Lettering", (0.24, 0.28, 0.30), 0.72),
        "joint": material("Dreams_Greybox_Cladding_Joint", (0.22, 0.24, 0.25), 0.88),
        "recess": material("Dreams_Greybox_Recess", (0.055, 0.065, 0.07), 0.92),
        "roof": material("Dreams_Greybox_Roof", (0.10, 0.12, 0.14), 0.84),
        "roof_trim": material("Dreams_Greybox_Roof_Trim", (0.16, 0.19, 0.21), 0.72, 0.16),
        "gutter": material("Dreams_Greybox_Gutter", (0.11, 0.13, 0.14), 0.60, 0.42),
        "shutter": material("Dreams_Greybox_Shutter", (0.37, 0.40, 0.41), 0.68, 0.24),
        "shutter_highlight": material("Dreams_Greybox_Shutter_Corrugation", (0.48, 0.51, 0.52), 0.60, 0.30),
        "shutter_frame": material("Dreams_Greybox_Shutter_Frame", (0.29, 0.32, 0.33), 0.58, 0.36),
        "brick": material("Dreams_Greybox_Brick", (0.28, 0.24, 0.22), 0.94),
        "mortar": material("Dreams_Greybox_Mortar", (0.13, 0.13, 0.13), 0.96),
        "notice": material("Dreams_Greybox_Noticeboard", (0.58, 0.59, 0.56), 0.80),
        "accent": material("Dreams_Greybox_Notice_Accent", (0.48, 0.45, 0.20), 0.82),
        "concrete": material("Dreams_Greybox_Concrete", (0.38, 0.38, 0.36), 0.96),
        "rail": material("Dreams_Greybox_Rail", (0.49, 0.51, 0.51), 0.44, 0.58),
        "fixture": material("Dreams_Greybox_Fixture", (0.24, 0.27, 0.28), 0.58, 0.32),
        "tube": material("Dreams_Greybox_Light_Tube", (0.72, 0.73, 0.68), 0.54),
        "alarm": material("Dreams_Greybox_Alarm", (0.50, 0.44, 0.16), 0.76),
    }


def select_asset(objects):
    bpy.ops.object.select_all(action="DESELECT")
    selected = []
    for obj in objects:
        if obj.type in {"MESH", "CURVE", "FONT"}:
            obj.select_set(True)
            selected.append(obj)
    if selected:
        bpy.context.view_layer.objects.active = selected[0]
    return selected


def save_and_export(objects):
    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), check_existing=False)
    select_asset(objects)
    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_image_format="AUTO",
    )


def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def add_preview_environment(materials):
    preview = bpy.data.collections.new("Dreams_Greybox_Preview_Only")
    bpy.context.scene.collection.children.link(preview)
    ground = material("Dreams_Preview_Ground", (0.035, 0.042, 0.050), 0.78)
    box("Dreams_Preview_Ground", (30.0, 30.0, 0.10), (0.0, 0.0, -0.08), ground, preview, 0.02)

    bpy.ops.object.light_add(type="AREA", location=(-5.5, -12.0, 10.5))
    key = bpy.context.object
    key.name = "Dreams_Preview_Key"
    key.data.energy = 1050
    key.data.color = (0.70, 0.82, 1.0)
    key.data.shape = "RECTANGLE"
    key.data.size = 10.0
    point_at(key, (0.0, FRONT_Y, 3.8))
    move_to(key, preview)

    bpy.ops.object.light_add(type="AREA", location=(10.0, -8.0, 5.0))
    rim = bpy.context.object
    rim.name = "Dreams_Preview_Warm_Rim"
    rim.data.energy = 700
    rim.data.color = (1.0, 0.42, 0.12)
    rim.data.size = 5.0
    point_at(rim, (5.5, FRONT_Y, 2.8))
    move_to(rim, preview)
    return preview


def make_camera(name, location, target, preview, orthographic=False, ortho_scale=13.0):
    bpy.ops.object.camera_add(location=location)
    camera = bpy.context.object
    camera.name = name
    if orthographic:
        camera.data.type = "ORTHO"
        camera.data.ortho_scale = ortho_scale
    else:
        camera.data.lens = 53
    point_at(camera, target)
    move_to(camera, preview)
    return camera


def wireframe_material():
    mat = bpy.data.materials.new("Dreams_Approval_Wireframe")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    mix = nodes.new("ShaderNodeMixShader")
    dark = nodes.new("ShaderNodeBsdfPrincipled")
    dark.inputs["Base Color"].default_value = (0.012, 0.018, 0.025, 1.0)
    dark.inputs["Roughness"].default_value = 0.92
    edges = nodes.new("ShaderNodeEmission")
    edges.inputs["Color"].default_value = (0.56, 0.88, 1.0, 1.0)
    edges.inputs["Strength"].default_value = 1.6
    wire = nodes.new("ShaderNodeWireframe")
    wire.inputs["Size"].default_value = 0.018
    links.new(wire.outputs["Fac"], mix.inputs[0])
    links.new(dark.outputs[0], mix.inputs[1])
    links.new(edges.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], output.inputs[0])
    return mat


def render_approvals(materials):
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1536
    scene.render.resolution_y = 1024
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.006, 0.009, 0.016)
    scene.view_settings.look = "AgX - Medium High Contrast"
    RENDER_ROOT.mkdir(parents=True, exist_ok=True)

    preview = add_preview_environment(materials)
    front = make_camera("Dreams_Approval_Front_Camera", (0.0, -35.0, 4.20), (0.0, FRONT_Y, 4.20), preview, True, 15.5)
    three_quarter = make_camera("Dreams_Approval_Three_Quarter_Camera", (19.5, -28.5, 10.8), (0.0, -0.35, 3.75), preview)

    scene.camera = front
    scene.render.filepath = str(FRONT_RENDER)
    bpy.ops.render.render(write_still=True)

    scene.camera = three_quarter
    scene.render.filepath = str(THREE_QUARTER_RENDER)
    bpy.ops.render.render(write_still=True)

    scene.view_layers[0].material_override = wireframe_material()
    preview_ground = bpy.data.objects.get("Dreams_Preview_Ground")
    if preview_ground:
        preview_ground.hide_render = True
    scene.camera = three_quarter
    scene.render.filepath = str(WIREFRAME_RENDER)
    bpy.ops.render.render(write_still=True)
    if preview_ground:
        preview_ground.hide_render = False
    scene.view_layers[0].material_override = None


def triangle_count(objects):
    return sum(
        sum(max(0, len(poly.vertices) - 2) for poly in obj.data.polygons)
        for obj in objects if obj.type == "MESH"
    )


def main():
    col = clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    mats = materials()
    objects = build_model(mats, col)
    source_triangles = triangle_count(objects)
    save_and_export(objects)
    render_approvals(mats)
    print(f"Dreams greybox objects: {len(objects)}")
    print(f"Dreams greybox source triangles: {source_triangles}")
    print(f"Saved Blender master: {BLEND_PATH}")
    print(f"Exported GLB: {GLB_PATH}")
    print(f"Front render: {FRONT_RENDER}")
    print(f"Three-quarter render: {THREE_QUARTER_RENDER}")
    print(f"Wireframe render: {WIREFRAME_RENDER}")


if __name__ == "__main__":
    main()
