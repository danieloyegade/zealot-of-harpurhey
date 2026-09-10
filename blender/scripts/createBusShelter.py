"""Build the photographic low-poly Harperhay bus shelter benchmark asset."""

from mathutils import Vector
from pathlib import Path
import subprocess
import tempfile

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_PATH = PROJECT_ROOT / "references" / "architecture" / "bus stop" / "Hires2.jpg"
BLEND_PATH = PROJECT_ROOT / "blender" / "source" / "harperhay-bus-shelter.blend"
GLB_PATH = PROJECT_ROOT / "public" / "assets" / "models" / "harperhay-bus-shelter.glb"
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures"
PREVIEW_PATH = PROJECT_ROOT / "renders" / "harperhay-bus-shelter-preview.png"

GLASS_TEXTURE_PATH = TEXTURE_DIR / "harperhay-bus-shelter-glass.jpg"
TIMETABLE_TEXTURE_PATH = TEXTURE_DIR / "harperhay-bus-shelter-timetable.jpg"
ADVERT_TEXTURE_PATH = TEXTURE_DIR / "harperhay-bus-shelter-advert.jpg"


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.images,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def run_sips(arguments):
    result = subprocess.run(
        ["/usr/bin/sips", *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    if result.stderr.strip():
        print(result.stderr.strip())


def create_texture_crop(output_path, crop, resolution):
    """Crop using top-left pixel coordinates, then resize in a second pass."""
    crop_x, crop_y, crop_width, crop_height = crop
    output_width, output_height = resolution
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="harperhay-texture-") as temp_directory:
        temporary_crop = Path(temp_directory) / "crop.jpg"
        run_sips(
            [
                "-c",
                str(crop_height),
                str(crop_width),
                "--cropOffset",
                str(crop_y),
                str(crop_x),
                str(REFERENCE_PATH),
                "-o",
                str(temporary_crop),
            ]
        )
        run_sips(
            [
                "-z",
                str(output_height),
                str(output_width),
                str(temporary_crop),
                "-s",
                "format",
                "jpeg",
                "-s",
                "formatOptions",
                "88",
                "-o",
                str(output_path),
            ]
        )


def generate_texture_derivatives():
    if not REFERENCE_PATH.is_file():
        raise FileNotFoundError(f"Bus shelter reference not found: {REFERENCE_PATH}")

    # The crops intentionally retain grain, reflections, colour casts, and halation.
    create_texture_crop(
        GLASS_TEXTURE_PATH,
        crop=(550, 350, 900, 450),
        resolution=(512, 256),
    )
    create_texture_crop(
        TIMETABLE_TEXTURE_PATH,
        crop=(325, 390, 240, 360),
        resolution=(256, 384),
    )
    create_texture_crop(
        ADVERT_TEXTURE_PATH,
        crop=(1470, 380, 220, 600),
        resolution=(256, 512),
    )


def get_principled(material):
    principled = material.node_tree.nodes.get("Principled BSDF")
    if principled is None:
        raise RuntimeError(f"Principled BSDF missing from {material.name}")
    return principled


def create_material(name, color, roughness=0.8, metallic=0.0, alpha=1.0):
    material = bpy.data.materials.new(name=name)
    principled = get_principled(material)
    principled.inputs["Base Color"].default_value = (*color, 1.0)
    principled.inputs["Roughness"].default_value = roughness
    principled.inputs["Metallic"].default_value = metallic
    principled.inputs["Alpha"].default_value = alpha

    if alpha < 1.0:
        material.surface_render_method = "BLENDED"
        material.use_transparency_overlap = False

    return material


def create_textured_material(
    name,
    texture_path,
    roughness=0.75,
    alpha=1.0,
    emission_strength=0.0,
):
    material = create_material(name, (1.0, 1.0, 1.0), roughness, alpha=alpha)
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    principled = get_principled(material)

    image = bpy.data.images.load(str(texture_path), check_existing=True)
    image.name = f"{name}-image"
    image.filepath = bpy.path.relpath(str(texture_path), start=str(BLEND_PATH.parent))

    texture_node = nodes.new("ShaderNodeTexImage")
    texture_node.name = f"{name}-texture"
    texture_node.label = texture_path.name
    texture_node.image = image
    links.new(texture_node.outputs["Color"], principled.inputs["Base Color"])

    if emission_strength > 0.0:
        emission_input = principled.inputs.get("Emission Color")
        emission_strength_input = principled.inputs.get("Emission Strength")
        if emission_input is not None and emission_strength_input is not None:
            links.new(texture_node.outputs["Color"], emission_input)
            emission_strength_input.default_value = emission_strength

    return material


def add_box(name, dimensions, location, material, asset_objects, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.name = f"{name}-mesh"
    obj.data.materials.append(material)

    if bevel > 0.0:
        modifier = obj.modifiers.new(name="chunky-edge", type="BEVEL")
        modifier.width = bevel
        modifier.segments = 2
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)

    asset_objects.append(obj)
    return obj


def add_plane_yz(name, x, y_range, z_range, material, asset_objects):
    y_min, y_max = y_range
    z_min, z_max = z_range
    mesh = bpy.data.meshes.new(f"{name}-mesh")
    mesh.from_pydata(
        [
            (x, y_min, z_min),
            (x, y_max, z_min),
            (x, y_max, z_max),
            (x, y_min, z_max),
        ],
        [],
        [(0, 1, 2, 3)],
    )
    mesh.update()
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for loop, uv in zip(mesh.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        uv_layer.data[loop.index].uv = uv

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(material)
    asset_objects.append(obj)
    return obj


def add_plane_xz(name, y, x_range, z_range, material, asset_objects):
    x_min, x_max = x_range
    z_min, z_max = z_range
    mesh = bpy.data.meshes.new(f"{name}-mesh")
    mesh.from_pydata(
        [
            (x_min, y, z_min),
            (x_max, y, z_min),
            (x_max, y, z_max),
            (x_min, y, z_max),
        ],
        [],
        [(0, 1, 2, 3)],
    )
    mesh.update()
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for loop, uv in zip(mesh.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        uv_layer.data[loop.index].uv = uv

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(material)
    asset_objects.append(obj)
    return obj


def add_cylinder_between(
    name,
    start,
    end,
    radius,
    material,
    asset_objects,
    vertices=8,
):
    start_vector = Vector(start)
    end_vector = Vector(end)
    direction = end_vector - start_vector
    midpoint = (start_vector + end_vector) * 0.5

    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=direction.length,
        location=midpoint,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}-mesh"
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    obj.data.materials.append(material)
    asset_objects.append(obj)
    return obj


def add_wheel(name, location, wheel_material, asset_objects):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=8,
        radius=0.095,
        depth=0.055,
        location=location,
        rotation=(0.0, 1.5707963268, 0.0),
    )
    wheel = bpy.context.object
    wheel.name = name
    wheel.data.name = f"{name}-mesh"
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    wheel.data.materials.append(wheel_material)
    asset_objects.append(wheel)
    return wheel


def build_trolley(materials, asset_objects):
    root = bpy.data.objects.new("trolley", None)
    bpy.context.collection.objects.link(root)
    asset_objects.append(root)
    trolley_parts = []

    metal = materials["trolley-metal"]
    dark_metal = materials["trolley-dark"]
    wheels = materials["trolley-wheel"]

    top = {"x0": -0.34, "x1": 0.34, "y0": -0.62, "y1": 0.72, "z": 1.18}
    bottom = {"x0": -0.25, "x1": 0.25, "y0": -0.48, "y1": 0.58, "z": 0.72}

    basket_edges = [
        ((top["x0"], top["y0"], top["z"]), (top["x1"], top["y0"], top["z"])),
        ((top["x0"], top["y1"], top["z"]), (top["x1"], top["y1"], top["z"])),
        ((top["x0"], top["y0"], top["z"]), (top["x0"], top["y1"], top["z"])),
        ((top["x1"], top["y0"], top["z"]), (top["x1"], top["y1"], top["z"])),
        ((bottom["x0"], bottom["y0"], bottom["z"]), (bottom["x1"], bottom["y0"], bottom["z"])),
        ((bottom["x0"], bottom["y1"], bottom["z"]), (bottom["x1"], bottom["y1"], bottom["z"])),
        ((bottom["x0"], bottom["y0"], bottom["z"]), (bottom["x0"], bottom["y1"], bottom["z"])),
        ((bottom["x1"], bottom["y0"], bottom["z"]), (bottom["x1"], bottom["y1"], bottom["z"])),
    ]
    for index, (start, end) in enumerate(basket_edges):
        trolley_parts.append(
            add_cylinder_between(
                f"trolley-basket-rim-{index:02d}",
                start,
                end,
                0.022,
                metal,
                asset_objects,
                vertices=6,
            )
        )

    for x_sign in (-1, 1):
        for y_sign in (-1, 1):
            trolley_parts.append(
                add_cylinder_between(
                    f"trolley-basket-corner-{x_sign}-{y_sign}",
                    (
                        top["x1"] if x_sign > 0 else top["x0"],
                        top["y1"] if y_sign > 0 else top["y0"],
                        top["z"],
                    ),
                    (
                        bottom["x1"] if x_sign > 0 else bottom["x0"],
                        bottom["y1"] if y_sign > 0 else bottom["y0"],
                        bottom["z"],
                    ),
                    0.018,
                    metal,
                    asset_objects,
                    vertices=6,
                )
            )

    # Five conspicuous bars imply the basket grid without modelling every wire.
    for side_x in (-0.34, 0.34):
        for index, y in enumerate((-0.38, -0.14, 0.10, 0.34, 0.58)):
            trolley_parts.append(
                add_cylinder_between(
                    f"trolley-basket-bar-{side_x:+.2f}-{index}",
                    (side_x, y, 1.15),
                    (side_x * 0.74, y, 0.75),
                    0.012,
                    metal,
                    asset_objects,
                    vertices=6,
                )
            )

    add_cylinder_between(
        "trolley-handle",
        (-0.39, -0.94, 1.16),
        (0.39, -0.94, 1.16),
        0.035,
        dark_metal,
        asset_objects,
        vertices=8,
    )
    add_cylinder_between(
        "trolley-handle-stem-left",
        (-0.32, -0.91, 1.14),
        (-0.25, -0.50, 0.68),
        0.024,
        metal,
        asset_objects,
        vertices=6,
    )
    add_cylinder_between(
        "trolley-handle-stem-right",
        (0.32, -0.91, 1.14),
        (0.25, -0.50, 0.68),
        0.024,
        metal,
        asset_objects,
        vertices=6,
    )

    for side_x in (-0.25, 0.25):
        add_cylinder_between(
            f"trolley-lower-frame-{side_x:+.2f}",
            (side_x, -0.47, 0.70),
            (side_x, 0.53, 0.20),
            0.025,
            metal,
            asset_objects,
            vertices=6,
        )

    for x in (-0.28, 0.28):
        for y in (-0.56, 0.56):
            add_wheel(
                f"trolley-wheel-{'left' if x < 0 else 'right'}-{'rear' if y < 0 else 'front'}",
                (x, y, 0.12),
                wheels,
                asset_objects,
            )

    for part in asset_objects:
        if part is not root and part.name.startswith("trolley-"):
            part.parent = root

    root.location = (0.10, 0.18, 0.0)
    root.rotation_euler[2] = -0.10
    return root


def build_shelter():
    materials = {
        "frame": create_material("mat-frame", (0.055, 0.095, 0.085), 0.8, metallic=0.45),
        "roof": create_material("mat-roof", (0.10, 0.14, 0.12), 0.9),
        "rail": create_material("mat-red-rail", (0.62, 0.025, 0.018), 0.72),
        "trolley-metal": create_material("mat-trolley-metal", (0.48, 0.52, 0.49), 0.42, metallic=0.8),
        "trolley-dark": create_material("mat-trolley-handle", (0.12, 0.14, 0.13), 0.78),
        "trolley-wheel": create_material("mat-trolley-wheel", (0.025, 0.03, 0.028), 0.95),
        "glass": create_textured_material(
            "mat-photographic-glass",
            GLASS_TEXTURE_PATH,
            roughness=0.5,
            alpha=0.64,
        ),
        "timetable": create_textured_material(
            "mat-photographic-timetable",
            TIMETABLE_TEXTURE_PATH,
            roughness=0.78,
        ),
        "advert": create_textured_material(
            "mat-photographic-advert",
            ADVERT_TEXTURE_PATH,
            roughness=0.45,
            emission_strength=2.2,
        ),
    }

    objects = []

    add_box(
        "shelter-rounded-roof",
        (1.58, 4.90, 0.26),
        (0.0, 0.0, 2.37),
        materials["roof"],
        objects,
        bevel=0.11,
    )

    # Large rear photographic glass plane, divided economically by frame geometry.
    add_plane_yz(
        "shelter-rear-photographic-glass",
        -0.70,
        (-2.23, 2.23),
        (0.34, 2.19),
        materials["glass"],
        objects,
    )
    for index, y in enumerate((-2.24, -0.76, 0.76, 2.24)):
        add_box(
            f"shelter-rear-post-{index}",
            (0.09, 0.09, 2.25),
            (-0.68, y, 1.13),
            materials["frame"],
            objects,
        )

    add_box("shelter-rear-top-rail", (0.10, 4.56, 0.10), (-0.68, 0.0, 2.19), materials["frame"], objects)
    add_box("shelter-rear-mid-rail", (0.10, 4.56, 0.10), (-0.66, 0.0, 1.02), materials["frame"], objects)
    add_box("shelter-rear-bottom-rail", (0.10, 4.56, 0.13), (-0.68, 0.0, 0.32), materials["frame"], objects)

    # One shallow side panel at the photograph's left end; the front stays open.
    add_plane_xz(
        "shelter-side-photographic-glass",
        -2.23,
        (-0.68, 0.66),
        (0.34, 2.18),
        materials["glass"],
        objects,
    )
    add_box("shelter-front-post-south", (0.10, 0.10, 2.24), (0.68, -2.24, 1.12), materials["frame"], objects)
    add_box("shelter-side-bottom-rail", (1.39, 0.10, 0.12), (0.0, -2.24, 0.33), materials["frame"], objects)

    # Timetable board remains a textured plane in a simple chunky housing.
    add_box("shelter-timetable-housing", (0.11, 0.78, 1.34), (-0.625, -1.38, 1.46), materials["frame"], objects, bevel=0.025)
    add_plane_yz(
        "shelter-timetable-display",
        -0.56,
        (-1.72, -1.04),
        (0.84, 2.08),
        materials["timetable"],
        objects,
    )

    # The advert uses one emissive photographic plane and a heavy dark housing.
    add_box("shelter-advert-housing", (1.52, 0.24, 2.12), (0.0, 2.34, 1.29), materials["frame"], objects, bevel=0.07)
    add_plane_xz(
        "shelter-illuminated-advert",
        2.205,
        (-0.63, 0.63),
        (0.35, 2.23),
        materials["advert"],
        objects,
    )

    # Red U-shaped perch rail and a narrow dark leaning strip.
    add_cylinder_between("shelter-red-rail-horizontal", (0.30, -1.25, 0.79), (0.30, 0.88, 0.79), 0.045, materials["rail"], objects)
    add_cylinder_between("shelter-red-rail-leg-south", (0.30, -1.25, 0.12), (0.30, -1.25, 0.79), 0.045, materials["rail"], objects)
    add_cylinder_between("shelter-red-rail-leg-north", (0.30, 0.88, 0.12), (0.30, 0.88, 0.79), 0.045, materials["rail"], objects)
    add_box("shelter-perch", (0.24, 2.08, 0.09), (-0.48, -0.14, 0.70), materials["frame"], objects)

    build_trolley(materials, objects)
    return objects


def triangle_count(objects):
    return sum(
        sum(max(0, len(polygon.vertices) - 2) for polygon in obj.data.polygons)
        for obj in objects
        if obj.type == "MESH"
    )


def save_master():
    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), check_existing=False)


def export_glb(asset_objects):
    GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in asset_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = next(obj for obj in asset_objects if obj.type == "MESH")

    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
    )


def point_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_preview_setup():
    ground_material = create_material("preview-ground", (0.022, 0.030, 0.027), 1.0)
    bpy.ops.mesh.primitive_plane_add(size=16.0, location=(0.0, 0.0, 0.0))
    ground = bpy.context.object
    ground.name = "preview-ground"
    ground.data.materials.append(ground_material)

    bpy.ops.object.camera_add(location=(7.8, -2.3, 3.25))
    camera = bpy.context.object
    camera.name = "preview-camera"
    camera.data.lens = 58
    point_at(camera, (0.0, 0.0, 1.25))
    bpy.context.scene.camera = camera

    bpy.ops.object.light_add(type="AREA", location=(1.2, 0.0, 5.0))
    overhead = bpy.context.object
    overhead.name = "preview-warm-overhead"
    overhead.data.energy = 650
    overhead.data.shape = "RECTANGLE"
    overhead.data.size = 5.0
    overhead.data.size_y = 2.0
    overhead.data.color = (1.0, 0.68, 0.36)
    point_at(overhead, (0.0, 0.0, 1.0))

    bpy.ops.object.light_add(type="AREA", location=(2.2, -1.0, 2.3))
    green_fill = bpy.context.object
    green_fill.name = "preview-green-fill"
    green_fill.data.energy = 420
    green_fill.data.size = 4.0
    green_fill.data.color = (0.20, 0.82, 0.48)
    point_at(green_fill, (-0.3, 0.0, 1.0))

    bpy.ops.object.light_add(type="AREA", location=(1.4, 2.9, 1.55))
    advert_spill = bpy.context.object
    advert_spill.name = "preview-advert-spill"
    advert_spill.data.energy = 300
    advert_spill.data.size = 2.2
    advert_spill.data.color = (1.0, 0.12, 0.46)
    point_at(advert_spill, (0.0, 1.6, 1.2))


def render_preview():
    PREVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 800
    scene.render.resolution_y = 600
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(PREVIEW_PATH)
    scene.render.film_transparent = False
    scene.world.color = (0.003, 0.006, 0.009)
    bpy.ops.render.render(write_still=True)


def main():
    clear_scene()
    generate_texture_derivatives()

    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0

    shelter_objects = build_shelter()
    total_triangles = triangle_count(shelter_objects)
    trolley_triangles = triangle_count(
        [obj for obj in shelter_objects if obj.name.startswith("trolley-")]
    )

    save_master()
    export_glb(shelter_objects)
    add_preview_setup()
    render_preview()

    print(f"Reference preserved: {REFERENCE_PATH}")
    print(f"Shelter triangles: {total_triangles}")
    print(f"Trolley triangles: {trolley_triangles}")
    print(f"Saved Blender master: {BLEND_PATH}")
    print(f"Exported GLB: {GLB_PATH}")
    print(f"Rendered preview: {PREVIEW_PATH}")


if __name__ == "__main__":
    main()
