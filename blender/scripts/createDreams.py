"""Build the photo-matched Dreams building and export a game-ready GLB.

The source photograph is used directly rather than baked into a low-resolution
atlas.  Each visible architectural component has its own calibrated UV crop,
which keeps the logo, shutter wear, brickwork, and wall staining sharp while
allowing the silhouette and façade depth to remain real geometry.
"""

from math import atan2, hypot
from mathutils import Vector
from pathlib import Path
from shutil import which
from subprocess import run

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_PHOTO = PROJECT_ROOT / "references" / "architecture" / "dreams" / "Dreams.jpg"
TEXTURE_ROOT = PROJECT_ROOT / "public" / "assets" / "textures" / "world-prototype"
FACADE_TEXTURE = TEXTURE_ROOT / "dreams-facade-hires.jpg"
SHUTTER_TEXTURE = TEXTURE_ROOT / "dreams-shutters-hires.jpg"
BRICK_TEXTURE = TEXTURE_ROOT / "brick-soot-overhaul.png"
BLEND_PATH = PROJECT_ROOT / "blender" / "source" / "harpurhey-dreams.blend"
GLB_PATH = PROJECT_ROOT / "public" / "assets" / "models" / "harpurhey-dreams.glb"
PREVIEW_PATH = PROJECT_ROOT / "renders" / "dreams" / "harpurhey-dreams-preview.png"

PHOTO_WIDTH = 3035.0
PHOTO_HEIGHT = 2432.0
WIDTH = 18.0
DEPTH = 8.5
EAVE_HEIGHT = 5.62
PEAK_HEIGHT = 8.18
FRONT_Y = -DEPTH / 2


def prepare_photo_textures():
    """Create compact, colour-matched 2K derivatives used by the GLB."""
    ffmpeg = which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to prepare the Dreams photo textures")
    TEXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    variants = (
        (
            FACADE_TEXTURE,
            "scale=2048:-2:flags=lanczos,eq=contrast=1.18:saturation=0.72:brightness=-0.10:gamma=0.92",
        ),
        (
            SHUTTER_TEXTURE,
            "scale=2048:-2:flags=lanczos,eq=contrast=1.16:saturation=0.52:brightness=-0.19:gamma=0.90",
        ),
    )
    for target, video_filter in variants:
        if target.exists() and target.stat().st_mtime >= SOURCE_PHOTO.stat().st_mtime:
            continue
        run(
            [
                ffmpeg, "-loglevel", "error", "-y", "-i", str(SOURCE_PHOTO),
                "-vf", video_filter, "-q:v", "3", str(target),
            ],
            check=True,
        )


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.images,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def create_material(name, color, roughness=0.9, metallic=0.0, emission=None, emission_strength=0.0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (*color, 1.0)
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (*color, 1.0)
    principled.inputs["Roughness"].default_value = roughness
    principled.inputs["Metallic"].default_value = metallic
    if emission and "Emission Color" in principled.inputs:
        principled.inputs["Emission Color"].default_value = (*emission, 1.0)
        principled.inputs["Emission Strength"].default_value = emission_strength
    return material


def create_textured_material(name, image_path, roughness=0.9):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    principled = nodes.get("Principled BSDF")
    principled.inputs["Roughness"].default_value = roughness
    image = bpy.data.images.load(str(image_path), check_existing=True)
    image.colorspace_settings.name = "sRGB"
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = image
    texture.interpolation = "Linear"
    links.new(texture.outputs["Color"], principled.inputs["Base Color"])
    return material


def add_box(name, dimensions, location, material, objects, rotation=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}-mesh"
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    objects.append(obj)
    return obj


def add_mesh(name, vertices, faces, material, objects, uvs=None):
    mesh = bpy.data.meshes.new(f"{name}-mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    if uvs:
        uv_layer = mesh.uv_layers.new(name="UVMap")
        for polygon_index, polygon_uvs in enumerate(uvs):
            polygon = mesh.polygons[polygon_index]
            for loop_index, uv in zip(polygon.loop_indices, polygon_uvs):
                uv_layer.data[loop_index].uv = uv
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    objects.append(obj)
    return obj


def photo_uv(pixel_x, pixel_y):
    return (pixel_x / PHOTO_WIDTH, 1.0 - pixel_y / PHOTO_HEIGHT)


def add_photo_panel(name, x0, x1, z0, z1, source_rect, material, objects, y):
    source_x0, source_y0, source_x1, source_y1 = source_rect
    return add_mesh(
        name,
        [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)],
        [(0, 3, 2, 1)],
        material,
        objects,
        [[
            photo_uv(source_x0, source_y1),
            photo_uv(source_x0, source_y0),
            photo_uv(source_x1, source_y0),
            photo_uv(source_x1, source_y1),
        ]],
    )


def add_photo_gable(material, objects):
    y = FRONT_Y - 0.012
    return add_mesh(
        "dreams-photo-gable",
        [(-9.0, y, EAVE_HEIGHT), (0.0, y, PEAK_HEIGHT), (9.0, y, EAVE_HEIGHT)],
        [(0, 1, 2)],
        material,
        objects,
        [[
            photo_uv(150, 1010),
            photo_uv(1360, 445),
            photo_uv(2620, 1015),
        ]],
    )


def add_architectural_facade(materials, objects):
    photo = materials["photo"]
    shutter_photo = materials["shutter_photo"]
    wall_y = FRONT_Y - 0.018
    shutter_y = FRONT_Y - 0.055

    # These crops are measured against Dreams.jpg.  The physical divisions are
    # matched to the target image: broad left shutter, narrow central doorway,
    # medium right shutter, then the exposed brick return.
    add_photo_gable(photo, objects)
    add_photo_panel(
        "dreams-left-upper-cladding",
        -9.0, -5.82, 3.43, EAVE_HEIGHT,
        (150, 850, 585, 1280), photo, objects, wall_y,
    )
    add_photo_panel(
        "dreams-logo-cladding-panel",
        -5.82, 5.32, 3.43, EAVE_HEIGHT,
        (585, 850, 2110, 1280), photo, objects, wall_y - 0.012,
    )
    add_photo_panel(
        "dreams-right-upper-cladding",
        5.32, 9.0, 3.43, EAVE_HEIGHT,
        (2110, 1000, 2620, 1280), photo, objects, wall_y,
    )

    add_photo_panel(
        "dreams-left-shutter",
        -8.45, -2.30, 0.57, 3.28,
        (275, 1315, 1170, 1805), shutter_photo, objects, shutter_y,
    )
    add_photo_panel(
        "dreams-centre-shutter",
        -2.23, -0.12, 0.57, 3.28,
        (1170, 1315, 1470, 1805), shutter_photo, objects, shutter_y,
    )
    add_photo_panel(
        "dreams-right-shutter",
        -0.05, 5.28, 0.57, 3.28,
        (1470, 1315, 2110, 1805), shutter_photo, objects, shutter_y,
    )
    add_photo_panel(
        "dreams-photo-brick-return",
        5.32, 8.88, 0.42, 3.43,
        (2110, 1280, 2600, 1825), photo, objects, wall_y,
    )

    # Real depth at every major façade break.
    add_box("dreams-deep-lower-fascia", (17.76, 0.34, 0.24), (-0.06, FRONT_Y - 0.17, 3.39), materials["metal"], objects)
    for index, x in enumerate((-8.48, -2.265, -0.085, 5.30)):
        add_box(
            f"dreams-shutter-frame-{index}",
            (0.13, 0.14, 2.79),
            (x, FRONT_Y - 0.13, 1.91),
            materials["metal"], objects,
        )
    add_box("dreams-shutter-bottom-sill", (13.84, 0.18, 0.13), (-1.55, FRONT_Y - 0.13, 0.52), materials["metal"], objects)

    # The notice-board is present in the photo texture; a thin raised frame
    # keeps its silhouette legible under non-photographic game lighting.
    for name, dimensions, location in (
        ("dreams-notice-frame-top", (1.54, 0.10, 0.07), (6.91, FRONT_Y - 0.115, 2.83)),
        ("dreams-notice-frame-bottom", (1.54, 0.10, 0.07), (6.91, FRONT_Y - 0.115, 1.12)),
        ("dreams-notice-frame-left", (0.07, 0.10, 1.78), (6.17, FRONT_Y - 0.115, 1.97)),
        ("dreams-notice-frame-right", (0.07, 0.10, 1.78), (7.65, FRONT_Y - 0.115, 1.97)),
    ):
        add_box(name, dimensions, location, materials["metal"], objects)

    # Cladding joints visible in both supplied references.
    add_box("dreams-gable-centre-seam", (0.035, 0.035, 2.43), (0.0, FRONT_Y - 0.055, 6.86), materials["seam"], objects)
    add_box("dreams-gable-horizontal-seam", (12.0, 0.035, 0.035), (0.0, FRONT_Y - 0.055, 6.45), materials["seam"], objects)


def add_gable_volume(material, objects):
    half_width = WIDTH / 2
    half_depth = DEPTH / 2
    vertices = [
        (-half_width, -half_depth, EAVE_HEIGHT),
        (half_width, -half_depth, EAVE_HEIGHT),
        (0.0, -half_depth, PEAK_HEIGHT),
        (-half_width, half_depth, EAVE_HEIGHT),
        (half_width, half_depth, EAVE_HEIGHT),
        (0.0, half_depth, PEAK_HEIGHT),
    ]
    faces = [(0, 2, 1), (3, 4, 5), (0, 1, 4, 3), (0, 3, 5, 2), (2, 5, 4, 1)]
    return add_mesh("dreams-gabled-volume", vertices, faces, material, objects)


def add_rail_between(name, start, end, material, objects, radius=0.035, vertices=8):
    start_vector = Vector(start)
    end_vector = Vector(end)
    direction = end_vector - start_vector
    midpoint = (start_vector + end_vector) * 0.5
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=direction.length, location=midpoint)
    rail = bpy.context.object
    rail.name = name
    rail.data.name = f"{name}-mesh"
    rail.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    rail.data.materials.append(material)
    objects.append(rail)
    return rail


def add_roof_and_trim(materials, objects):
    roof_angle = atan2(PEAK_HEIGHT - EAVE_HEIGHT, WIDTH / 2)
    roof_length = hypot(WIDTH / 2 + 0.30, PEAK_HEIGHT - EAVE_HEIGHT)
    add_box(
        "dreams-left-pitched-roof", (roof_length, DEPTH + 0.62, 0.20),
        (-4.58, 0.0, 6.94), materials["roof"], objects,
        rotation=(0.0, -roof_angle, 0.0),
    )
    add_box(
        "dreams-right-pitched-roof", (roof_length, DEPTH + 0.62, 0.20),
        (4.58, 0.0, 6.94), materials["roof"], objects,
        rotation=(0.0, roof_angle, 0.0),
    )
    trim_y = FRONT_Y - 0.18
    add_rail_between("dreams-left-blue-roof-trim", (-9.08, trim_y, 5.63), (0.0, trim_y, 8.22), materials["blue_trim"], objects, 0.045, 6)
    add_rail_between("dreams-right-blue-roof-trim", (0.0, trim_y, 8.22), (9.08, trim_y, 5.63), materials["blue_trim"], objects, 0.045, 6)
    add_box("dreams-eaves-blue-trim", (18.10, 0.13, 0.09), (0.0, trim_y, 5.64), materials["blue_trim"], objects)
    add_box("dreams-ridge-cap", (0.16, DEPTH + 0.82, 0.13), (0.0, 0.0, 8.24), materials["roof"], objects)


def add_lights_and_security(materials, objects):
    for index, x in enumerate((-4.55, -1.50, 1.55, 4.60)):
        add_box(f"dreams-upper-light-housing-{index}", (2.78, 0.16, 0.12), (x, FRONT_Y - 0.225, 5.72), materials["metal"], objects)
        add_box(f"dreams-upper-light-tube-{index}", (2.60, 0.075, 0.055), (x, FRONT_Y - 0.315, 5.70), materials["light"], objects)
    for index, x in enumerate((-4.35, -1.39, 1.57, 4.53)):
        add_box(f"dreams-lower-light-tube-{index}", (2.70, 0.065, 0.045), (x, FRONT_Y - 0.365, 3.29), materials["lower_light"], objects)

    # The small props sit directly over their photographic counterparts, adding
    # parallax without producing a visible duplicate from the hero angle.
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.17, depth=0.15, location=(-6.86, FRONT_Y - 0.18, 4.55), rotation=(1.5708, 0.0, 0.0))
    alarm = bpy.context.object
    alarm.name = "dreams-yellow-security-alarm"
    alarm.data.materials.append(materials["yellow"])
    objects.append(alarm)
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.092, depth=0.018, location=(-6.86, FRONT_Y - 0.27, 4.55), rotation=(1.5708, 0.0, 0.0))
    alarm_face = bpy.context.object
    alarm_face.name = "dreams-blue-alarm-face"
    alarm_face.data.materials.append(materials["alarm_blue"])
    objects.append(alarm_face)

    add_box("dreams-cctv-mount", (0.05, 0.08, 0.23), (-6.31, FRONT_Y - 0.18, 3.65), materials["dark_metal"], objects)
    add_box("dreams-cctv-camera", (0.18, 0.23, 0.11), (-6.26, FRONT_Y - 0.27, 3.70), materials["dark_metal"], objects, rotation=(0.12, 0.0, -0.10))


def add_graffiti(materials, objects):
    """Add the dark hand-style tag visible on the target's left shutter."""
    y = FRONT_Y - 0.135
    strokes = (
        ((-7.43, y, 1.48), (-7.25, y, 2.18), (-7.08, y, 1.62), (-6.90, y, 2.24)),
        ((-6.78, y, 1.55), (-6.58, y, 2.14), (-6.42, y, 1.58), (-6.20, y, 2.05)),
        ((-7.55, y, 1.78), (-6.10, y, 1.84)),
        ((-7.28, y, 1.38), (-6.32, y, 1.31)),
        ((-6.05, y, 1.51), (-5.69, y, 1.35), (-5.86, y, 1.82)),
    )
    for stroke_index, stroke in enumerate(strokes):
        for segment_index, (start, end) in enumerate(zip(stroke, stroke[1:])):
            add_rail_between(
                f"dreams-graffiti-{stroke_index}-{segment_index}",
                start, end, materials["graffiti"], objects, radius=0.014, vertices=5,
            )


def add_ramp_and_rails(materials, objects):
    add_box("dreams-raised-brick-plinth", (9.20, 1.64, 0.52), (-0.30, FRONT_Y - 0.77, 0.26), materials["brick"], objects)
    add_box("dreams-concrete-platform", (8.40, 1.48, 0.16), (-0.70, FRONT_Y - 0.83, 0.60), materials["concrete"], objects)
    ramp_angle = atan2(0.44, 4.27)
    add_box(
        "dreams-accessibility-ramp", (4.90, 1.48, 0.18),
        (5.42, FRONT_Y - 0.83, 0.34), materials["concrete"], objects,
        rotation=(0.0, ramp_angle, 0.0),
    )

    for side_index, y in enumerate((FRONT_Y - 0.19, FRONT_Y - 1.48)):
        for post_index, x in enumerate((-4.75, -2.40, 0.00, 2.35, 3.55)):
            add_rail_between(f"dreams-platform-post-{side_index}-{post_index}", (x, y, 0.61), (x, y, 1.84), materials["rail"], objects)
        for rail_index, height in enumerate((1.34, 1.84)):
            add_rail_between(f"dreams-platform-rail-{side_index}-{rail_index}", (-4.75, y, height), (3.55, y, height), materials["rail"], objects)
        add_rail_between(f"dreams-ramp-upper-rail-{side_index}", (3.55, y, 1.84), (7.82, y, 1.40), materials["rail"], objects)
        add_rail_between(f"dreams-ramp-lower-rail-{side_index}", (3.55, y, 1.34), (7.82, y, 0.90), materials["rail"], objects)
        for post_index, (x, low, high) in enumerate(((5.65, 0.39, 1.62), (7.82, 0.17, 1.40))):
            add_rail_between(f"dreams-ramp-post-{side_index}-{post_index}", (x, y, low), (x, y, high), materials["rail"], objects)

    add_rail_between("dreams-right-drainpipe", (8.55, FRONT_Y - 0.17, 0.42), (8.55, FRONT_Y - 0.17, 3.43), materials["dark_metal"], objects, 0.055, 8)
    add_box("dreams-white-wall-vent", (0.12, 0.12, 0.25), (8.10, FRONT_Y - 0.16, 0.48), materials["metal"], objects)


def build_dreams():
    materials = {
        "photo": create_textured_material("mat-dreams-photographic-front-hires", FACADE_TEXTURE, 0.88),
        "shutter_photo": create_textured_material("mat-dreams-photographic-shutters-hires", SHUTTER_TEXTURE, 0.94),
        "brick": create_textured_material("mat-dreams-photographic-brick", BRICK_TEXTURE, 0.96),
        "side": create_material("mat-dreams-dark-side", (0.105, 0.060, 0.047), 0.98),
        "gable": create_material("mat-dreams-gable-backing", (0.42, 0.40, 0.35), 0.97),
        "roof": create_material("mat-dreams-weathered-roof", (0.032, 0.035, 0.041), 0.92, 0.08),
        "metal": create_material("mat-dreams-painted-metal", (0.47, 0.51, 0.51), 0.70, 0.22),
        "dark_metal": create_material("mat-dreams-dark-metal", (0.035, 0.045, 0.048), 0.76, 0.34),
        "seam": create_material("mat-dreams-cladding-seam", (0.29, 0.31, 0.29), 0.94),
        "rail": create_material("mat-dreams-handrail", (0.54, 0.58, 0.57), 0.46, 0.55),
        "concrete": create_material("mat-dreams-ramp-concrete", (0.25, 0.25, 0.23), 0.97),
        "graffiti": create_material("mat-dreams-graffiti", (0.055, 0.038, 0.070), 0.86),
        "yellow": create_material("mat-dreams-alarm-yellow", (0.76, 0.63, 0.025), 0.82),
        "alarm_blue": create_material("mat-dreams-alarm-blue", (0.018, 0.085, 0.22), 0.72),
        "blue_trim": create_material("mat-dreams-blue-roof-trim", (0.025, 0.13, 0.22), 0.64, 0.34),
        "light": create_material("mat-dreams-tube-light", (0.74, 0.90, 0.88), 0.28, emission=(0.58, 0.86, 0.88), emission_strength=2.4),
        "lower_light": create_material("mat-dreams-lower-tube-light", (0.43, 0.61, 0.63), 0.48, emission=(0.27, 0.54, 0.58), emission_strength=1.2),
    }
    objects = []
    add_box("dreams-building-shell", (WIDTH, DEPTH, EAVE_HEIGHT), (0.0, 0.0, EAVE_HEIGHT / 2), materials["side"], objects)
    add_gable_volume(materials["gable"], objects)
    add_roof_and_trim(materials, objects)
    add_architectural_facade(materials, objects)
    add_lights_and_security(materials, objects)
    add_graffiti(materials, objects)
    add_ramp_and_rails(materials, objects)
    return objects


def triangle_count(objects):
    return sum(
        sum(max(0, len(polygon.vertices) - 2) for polygon in obj.data.polygons)
        for obj in objects if obj.type == "MESH"
    )


def save_and_export(objects):
    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Keep the editable master portable: the photo-derived maps travel inside
    # the .blend, while the GLB embeds its own copies for the game runtime.
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), check_existing=False)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_image_format="AUTO",
    )


def point_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def render_preview():
    add_box(
        "preview-ground", (30.0, 28.0, 0.08), (0.0, 0.0, -0.05),
        create_material("preview-wet-ground", (0.014, 0.021, 0.030), 0.48, 0.16), [],
    )
    bpy.ops.object.light_add(type="AREA", location=(0.0, -9.0, 7.2))
    cool = bpy.context.object
    cool.data.energy = 340
    cool.data.color = (0.55, 0.76, 1.0)
    cool.data.shape = "RECTANGLE"
    cool.data.size = 13.0
    point_at(cool, (0.0, FRONT_Y, 3.7))
    bpy.ops.object.light_add(type="AREA", location=(-10.0, -8.0, 6.5))
    warm = bpy.context.object
    warm.data.energy = 260
    warm.data.color = (1.0, 0.43, 0.10)
    warm.data.size = 4.0
    point_at(warm, (-6.5, FRONT_Y, 2.8))
    bpy.ops.object.camera_add(location=(0.0, -28.8, 5.25))
    camera = bpy.context.object
    camera.data.lens = 50
    point_at(camera, (0.0, FRONT_Y, 3.75))
    scene = bpy.context.scene
    scene.camera = camera
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1536
    scene.render.resolution_y = 1024
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(PREVIEW_PATH)
    scene.render.film_transparent = False
    scene.world.color = (0.002, 0.004, 0.012)
    scene.view_settings.look = "AgX - Medium High Contrast"
    PREVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)


def main():
    for source in (SOURCE_PHOTO, BRICK_TEXTURE):
        if not source.exists():
            raise FileNotFoundError(f"Missing Dreams texture: {source}")
    prepare_photo_textures()
    clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    objects = build_dreams()
    triangles = triangle_count(objects)
    save_and_export(objects)
    render_preview()
    print(f"Dreams triangles: {triangles}")
    print(f"Saved Blender master: {BLEND_PATH}")
    print(f"Exported GLB: {GLB_PATH}")
    print(f"Rendered preview: {PREVIEW_PATH}")


if __name__ == "__main__":
    main()
