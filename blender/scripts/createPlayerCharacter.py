"""Build the provisional player-character asset, review renders, and runtime GLB."""

from pathlib import Path
import math

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
BLEND_PATH = ROOT / "blender" / "source" / "player-character.blend"
GLB_PATH = ROOT / "public" / "assets" / "models" / "player-character.glb"
RENDER_DIR = ROOT / "renders" / "player-character"


def reset_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def material(name, colour, roughness=0.75, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*colour, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*colour, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def finish(obj, mat, smooth=False, bevel=0.0):
    obj.data.materials.append(mat)
    if smooth:
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    if bevel:
        modifier = obj.modifiers.new("soft-edges", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
    return obj


def parent_keep_transform(obj, parent):
    matrix = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = matrix


def cube(name, location, scale, mat, bevel=0.0, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    finish(obj, mat, bevel=bevel)
    if parent:
        parent_keep_transform(obj, parent)
    return obj


def tapered_box(name, z_bottom, z_top, bottom_width, top_width, bottom_depth, top_depth, mat, parent=None):
    vertices = []
    for z, width, depth in ((z_bottom, bottom_width, bottom_depth), (z_top, top_width, top_depth)):
        vertices.extend((
            (-width / 2, -depth / 2, z), (width / 2, -depth / 2, z),
            (width / 2, depth / 2, z), (-width / 2, depth / 2, z),
        ))
    faces = ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (4, 0, 3, 7))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    finish(obj, mat, bevel=0.025)
    if parent:
        parent_keep_transform(obj, parent)
    return obj


def sphere(name, location, scale, mat, segments=24, rings=16, parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    finish(obj, mat, smooth=True)
    if parent:
        parent_keep_transform(obj, parent)
    return obj


def cylinder_between(name, start, end, radius, mat, vertices=16, parent=None, radius_end=None):
    start = Vector(start)
    end = Vector(end)
    midpoint = (start + end) * 0.5
    direction = end - start
    if radius_end is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=direction.length, location=midpoint)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius_end, radius2=radius, depth=direction.length, location=midpoint)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
    obj.rotation_mode = "XYZ"
    finish(obj, mat, smooth=True, bevel=0.008)
    if parent:
        parent_keep_transform(obj, parent)
    return obj


def curve(name, points, bevel_depth, mat, parent=None):
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 2
    data.bevel_resolution = 2
    data.bevel_depth = bevel_depth
    spline = data.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for point, co in zip(spline.bezier_points, points):
        point.co = co
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    data.materials.append(mat)
    if parent:
        parent_keep_transform(obj, parent)
    return obj


def empty(name, location):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = 0.08
    obj.location = location
    bpy.context.collection.objects.link(obj)
    return obj


def build_character():
    skin = material("skin-rich-brown", (0.205, 0.092, 0.045), 0.72)
    skin_highlight = material("skin-warm-highlight", (0.31, 0.145, 0.072), 0.68)
    hair = material("hair-near-black", (0.009, 0.007, 0.006), 0.92)
    hoodie = material("hoodie-charcoal", (0.035, 0.043, 0.052), 0.96)
    hoodie_edge = material("hoodie-ribbing", (0.018, 0.023, 0.029), 0.96)
    denim = material("denim-washed-indigo", (0.035, 0.075, 0.12), 0.92)
    denim_edge = material("denim-seams", (0.17, 0.20, 0.19), 0.88)
    trainer = material("trainer-off-white", (0.66, 0.64, 0.57), 0.84)
    trainer_dark = material("trainer-rubber", (0.035, 0.037, 0.038), 0.9)
    bag = material("courier-bag-black", (0.012, 0.016, 0.018), 0.9)
    bag_panel = material("courier-bag-ochre", (0.52, 0.23, 0.035), 0.82)
    reflective = material("reflective-trim", (0.7, 0.73, 0.62), 0.38, 0.05)
    eye_white = material("eye-white", (0.55, 0.49, 0.40), 0.72)
    eye_dark = material("eye-dark", (0.008, 0.006, 0.004), 0.5)

    root = empty("player-character-root", (0, 0, 0))

    left_leg = empty("player-left-leg-pivot", (-0.145, 0, 0.91))
    right_leg = empty("player-right-leg-pivot", (0.145, 0, 0.91))
    left_leg.parent = root
    right_leg.parent = root
    for side, x, pivot in (("left", -0.145, left_leg), ("right", 0.145, right_leg)):
        cylinder_between(f"player-{side}-jean-leg", (x, 0, 0.91), (x, 0.005, 0.25), 0.125, denim, 16, pivot, 0.105)
        seam_x = x + (-0.116 if side == "left" else 0.116)
        cylinder_between(f"player-{side}-outer-seam", (seam_x, -0.005, 0.84), (x + (-0.098 if side == "left" else 0.098), 0, 0.29), 0.007, denim_edge, 8, pivot)
        foot = cube(f"player-{side}-trainer", (x, 0.05, 0.105), (0.22, 0.34, 0.16), trainer, 0.035, pivot)
        foot.rotation_euler.x = math.radians(-2)
        cube(f"player-{side}-trainer-sole", (x, 0.05, 0.035), (0.235, 0.35, 0.055), trainer_dark, 0.02, pivot)
        cube(f"player-{side}-trainer-panel", (x, 0.225, 0.115), (0.14, 0.015, 0.045), reflective, 0.006, pivot)

    tapered_box("player-hoodie-body", 0.9, 1.49, 0.54, 0.66, 0.29, 0.34, hoodie, root)
    cube("player-hoodie-hem", (0, 0, 0.91), (0.53, 0.30, 0.07), hoodie_edge, 0.018, root)
    pocket = cube("player-hoodie-pocket", (0, 0.165, 1.08), (0.35, 0.04, 0.15), hoodie_edge, 0.018, root)
    pocket.rotation_euler.x = math.radians(-5)
    sphere("player-hood", (0, -0.07, 1.49), (0.25, 0.18, 0.235), hoodie, 24, 16, root)
    sphere("player-hood-opening", (0, 0.075, 1.50), (0.17, 0.07, 0.17), hoodie_edge, 20, 12, root)
    cylinder_between("player-drawstring-left", (-0.075, 0.19, 1.46), (-0.085, 0.205, 1.25), 0.008, reflective, 8, root)
    cylinder_between("player-drawstring-right", (0.075, 0.19, 1.46), (0.085, 0.205, 1.25), 0.008, reflective, 8, root)

    left_arm = empty("player-left-arm-pivot", (-0.34, 0, 1.43))
    right_arm = empty("player-right-arm-pivot", (0.34, 0, 1.43))
    left_arm.parent = root
    right_arm.parent = root
    for side, sign, pivot in (("left", -1, left_arm), ("right", 1, right_arm)):
        shoulder = (0.34 * sign, 0, 1.43)
        elbow = (0.40 * sign, 0.02, 1.15)
        wrist = (0.37 * sign, 0.055, 0.92)
        cylinder_between(f"player-{side}-hoodie-upper-sleeve", shoulder, elbow, 0.105, hoodie, 16, pivot, 0.09)
        cylinder_between(f"player-{side}-hoodie-forearm", elbow, wrist, 0.09, hoodie, 16, pivot, 0.068)
        cylinder_between(f"player-{side}-cuff", (0.375 * sign, 0.05, 0.975), wrist, 0.072, hoodie_edge, 12, pivot, 0.065)
        sphere(f"player-{side}-hand", (0.365 * sign, 0.062, 0.85), (0.065, 0.058, 0.09), skin, 16, 12, pivot)

    cylinder_between("player-neck", (0, 0, 1.44), (0, 0, 1.54), 0.115, skin, 16, root)
    sphere("player-head", (0, 0.01, 1.68), (0.18, 0.155, 0.235), skin, 28, 20, root)
    sphere("player-left-ear", (-0.18, 0.01, 1.69), (0.027, 0.02, 0.05), skin_highlight, 14, 10, root)
    sphere("player-right-ear", (0.18, 0.01, 1.69), (0.027, 0.02, 0.05), skin_highlight, 14, 10, root)
    sphere("player-nose", (0, 0.158, 1.675), (0.03, 0.028, 0.05), skin_highlight, 14, 10, root)
    for side, x in (("left", -0.061), ("right", 0.061)):
        sphere(f"player-{side}-eye", (x, 0.155, 1.735), (0.027, 0.008, 0.012), eye_white, 14, 8, root)
        sphere(f"player-{side}-iris", (x, 0.163, 1.735), (0.011, 0.005, 0.011), eye_dark, 12, 8, root)
        curve(f"player-{side}-brow", [(x - 0.034, 0.164, 1.77), (x, 0.169, 1.775), (x + 0.034, 0.164, 1.77)], 0.005, hair, root)
    curve("player-mouth", [(-0.042, 0.164, 1.625), (0, 0.168, 1.62), (0.042, 0.164, 1.625)], 0.005, hair, root)
    curve("player-beard-line", [(-0.115, 0.12, 1.625), (-0.075, 0.143, 1.58), (0, 0.15, 1.56), (0.075, 0.143, 1.58), (0.115, 0.12, 1.625)], 0.007, hair, root)

    sphere("player-hair-cap", (0, -0.01, 1.815), (0.17, 0.15, 0.115), hair, 24, 14, root)
    for index, x in enumerate((-0.13, -0.093, -0.056, -0.019, 0.019, 0.056, 0.093, 0.13)):
        arch = 0.065 * (1.0 - min(abs(x) / 0.19, 1.0) ** 2)
        points = [
            (x, 0.145, 1.82 - abs(x) * 0.15),
            (x * 1.02, 0.055, 1.885 + arch * 0.65),
            (x * 0.98, -0.06, 1.885 + arch * 0.65),
            (x * 0.82, -0.15, 1.81),
            (x * 0.62, -0.16, 1.73),
        ]
        curve(f"player-cornrow-{index + 1:02d}", points, 0.011, hair, root)
        for knot_index, point_index in enumerate((1, 2, 3)):
            sphere(f"player-cornrow-{index + 1:02d}-knot-{knot_index + 1}", points[point_index], (0.014, 0.014, 0.014), hair, 10, 6, root)

    bag_body = cube("player-courier-bag", (0, -0.25, 1.265), (0.48, 0.26, 0.61), bag, 0.05, root)
    bag_body.rotation_euler.x = math.radians(-3)
    cube("player-courier-bag-front-panel", (0, -0.392, 1.275), (0.38, 0.035, 0.39), bag_panel, 0.02, root)
    cube("player-courier-bag-reflective-strip", (0, -0.412, 1.13), (0.35, 0.014, 0.03), reflective, 0.006, root)
    cube("player-courier-bag-lid", (0, -0.26, 1.59), (0.48, 0.29, 0.085), bag, 0.025, root)
    for side, x in (("left", -0.245), ("right", 0.245)):
        curve(f"player-bag-strap-{side}", [(x, -0.08, 1.52), (x * 0.9, 0.08, 1.35), (x * 0.78, 0.08, 1.05)], 0.025, bag, root)

    root.scale = (0.92, 0.92, 0.92)
    root["asset_stage"] = "improved-placeholder"
    root["height_metres"] = 1.78
    root["forward_axis"] = "Blender +Y / glTF -Z"
    return root


def setup_scene():
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 720
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (0.008, 0.011, 0.017)
    scene.view_settings.look = "AgX - Medium High Contrast"


def add_review_stage():
    stage_mat = material("review-ground", (0.025, 0.03, 0.038), 0.96)
    cube("review-ground", (0, 0, -0.035), (5.5, 5.5, 0.06), stage_mat)
    for name, location, energy, size, colour in (
        ("review-key", (-2.4, 2.2, 3.4), 620, 2.0, (1.0, 0.56, 0.31)),
        ("review-rim", (2.2, -1.8, 2.7), 760, 1.7, (0.22, 0.38, 1.0)),
        ("review-fill", (0, 1.4, 4.2), 330, 2.5, (0.8, 0.88, 1.0)),
    ):
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        light.data.color = colour
        light.rotation_euler = (Vector((0, 0, 1.0)) - light.location).to_track_quat("-Z", "Y").to_euler()


def aim_camera(camera, target):
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()


def render_reviews():
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "review-camera"
    bpy.context.scene.camera = camera
    views = [
        ("view-a-front.png", (0, 4.6, 1.55), (0, 0, 1.0)),
        ("view-b-three-quarter.png", (3.35, 3.65, 1.75), (0, 0, 1.02)),
        ("view-c-back-courier-silhouette.png", (-2.8, -4.2, 1.8), (0, 0, 1.1)),
        ("view-d-head-and-cornrows.png", (0.75, 2.0, 1.82), (0, 0.02, 1.72)),
    ]
    for filename, location, target in views:
        camera.location = location
        camera.data.lens = 78 if "head" in filename else 68
        aim_camera(camera, target)
        bpy.context.scene.render.filepath = str(RENDER_DIR / filename)
        bpy.ops.render.render(write_still=True)


def export_asset(root):
    GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    for child in root.children_recursive:
        child.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.gltf(filepath=str(GLB_PATH), export_format="GLB", use_selection=True, export_yup=True)


def main():
    reset_scene()
    setup_scene()
    root = build_character()
    export_asset(root)
    add_review_stage()
    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    render_reviews()
    print(f"Saved Blender master: {BLEND_PATH}")
    print(f"Exported runtime GLB: {GLB_PATH}")
    print(f"Rendered reviews: {RENDER_DIR}")


if __name__ == "__main__":
    main()
