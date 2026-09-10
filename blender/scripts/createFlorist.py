"""Build the photographic low-poly Harperhay florist architecture asset."""

from mathutils import Vector
from pathlib import Path
import subprocess
import tempfile

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_PATH = (
    PROJECT_ROOT
    / "references"
    / "architecture"
    / "florist"
    / "florist-front-reference"
    / "IMG_8712.PNG"
)
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "florist"
FACADE_TEXTURE_PATH = TEXTURE_DIR / "harperhay-florist-facade.jpg"
SHOPFRONT_TEXTURE_PATH = TEXTURE_DIR / "harperhay-florist-shopfront.jpg"
BLEND_PATH = PROJECT_ROOT / "blender" / "source" / "harperhay-florist.blend"
GLB_PATH = PROJECT_ROOT / "public" / "assets" / "models" / "harperhay-florist.glb"
PREVIEW_PATH = PROJECT_ROOT / "renders" / "harperhay-florist-preview.png"
OBLIQUE_PREVIEW_PATH = PROJECT_ROOT / "renders" / "harperhay-florist-preview-oblique.png"


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
    """Crop with top-left coordinates, then resize in a separate pass."""
    crop_x, crop_y, crop_width, crop_height = crop
    output_width, output_height = resolution
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="harperhay-florist-texture-") as temp_directory:
        temporary_crop = Path(temp_directory) / "crop.png"
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
    if not REFERENCE_PATH.exists():
        raise FileNotFoundError(f"Missing florist reference: {REFERENCE_PATH}")

    # Isolate the florist from the social-media UI and adjacent mural as far as
    # the single oblique source permits. The shopfront receives its own crop so
    # signage and window contents remain legible at pedestrian distance.
    create_texture_crop(
        FACADE_TEXTURE_PATH,
        crop=(210, 350, 320, 820),
        resolution=(512, 768),
    )
    create_texture_crop(
        SHOPFRONT_TEXTURE_PATH,
        crop=(100, 1050, 520, 520),
        resolution=(512, 384),
    )


def create_material(name, base_color, roughness=0.9, metallic=0.0):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*base_color, 1.0)
    material.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (
        *base_color,
        1.0,
    )
    material.node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value = roughness
    material.node_tree.nodes.get("Principled BSDF").inputs["Metallic"].default_value = metallic
    return material


def create_textured_material(name, image_path, roughness=0.8):
    material = bpy.data.materials.new(name)
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    principled = nodes.get("Principled BSDF")
    principled.inputs["Roughness"].default_value = roughness

    image = bpy.data.images.load(str(image_path), check_existing=False)
    image.colorspace_settings.name = "sRGB"
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = image
    links.new(texture.outputs["Color"], principled.inputs["Base Color"])
    return material


def add_box(name, dimensions, location, material, objects):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}-mesh"
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    objects.append(obj)
    return obj


def add_plane_yz(name, x, y_range, z_range, material, objects):
    y_min, y_max = y_range
    z_min, z_max = z_range
    vertices = [
        (x, y_min, z_min),
        (x, y_max, z_min),
        (x, y_max, z_max),
        (x, y_min, z_max),
    ]
    mesh = bpy.data.meshes.new(f"{name}-mesh")
    mesh.from_pydata(vertices, [], [(0, 1, 2, 3)])
    mesh.materials.append(material)
    uv_layer = mesh.uv_layers.new(name="UVMap")
    # Viewed from the building front (-X), screen-right is local -Y.
    for loop, uv in zip(mesh.polygons[0].loop_indices, ((1, 0), (0, 0), (0, 1), (1, 1))):
        uv_layer.data[loop].uv = uv
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    objects.append(obj)
    return obj


def build_florist():
    materials = {
        "wall": create_material("mat-florist-side-wall", (0.19, 0.17, 0.14), 0.96),
        "trim": create_material("mat-florist-stone-trim", (0.22, 0.19, 0.15), 0.94),
        "dark": create_material("mat-florist-door-dark", (0.015, 0.018, 0.018), 0.82),
        "facade": create_textured_material(
            "mat-florist-photographic-facade", FACADE_TEXTURE_PATH, 0.86
        ),
        "shopfront": create_textured_material(
            "mat-florist-photographic-shopfront", SHOPFRONT_TEXTURE_PATH, 0.58
        ),
    }
    objects = []

    # Estimated from a common UK shopfront/door scale, not surveyed dimensions:
    # 7.5 m deep, 6.0 m wide and 10.4 m to the flat parapet.
    add_box("florist-building-shell", (7.50, 6.00, 10.40), (0.0, 0.0, 5.20), materials["wall"], objects)
    add_plane_yz(
        "florist-photographic-facade",
        -3.756,
        (-3.0, 3.0),
        (3.25, 10.4),
        materials["facade"],
        objects,
    )
    add_plane_yz(
        "florist-photographic-shopfront",
        -3.772,
        (-2.86, 2.86),
        (0.10, 3.25),
        materials["shopfront"],
        objects,
    )

    # Sparse projections preserve the photograph's shallow theatrical flatness.
    add_box("florist-parapet-cap", (0.30, 6.12, 0.30), (-3.82, 0.0, 10.25), materials["trim"], objects)
    for index, z in enumerate((3.30, 6.62)):
        add_box(
            f"florist-facade-band-{index}",
            (0.20, 5.92, 0.16),
            (-3.84, 0.0, z),
            materials["trim"],
            objects,
        )

    for index, y in enumerate((-2.72, 0.0, 2.72)):
        add_box(
            f"florist-facade-pier-{index}",
            (0.18, 0.22, 6.65),
            (-3.84, y, 6.95),
            materials["trim"],
            objects,
        )

    for floor_index, z in enumerate((6.28, 9.25)):
        for window_index, y in enumerate((-1.48, 1.45)):
            add_box(
                f"florist-window-hood-{floor_index}-{window_index}",
                (0.26, 2.12, 0.16),
                (-3.90, y, z),
                materials["trim"],
                objects,
            )

    # The entrance remains dark and simple, ready for a later interior transition.
    add_plane_yz(
        "florist-future-doorway",
        -3.79,
        (-2.77, -2.05),
        (0.10, 2.55),
        materials["dark"],
        objects,
    )
    add_box("florist-door-jamb-inner", (0.24, 0.14, 2.62), (-3.91, -2.01, 1.36), materials["trim"], objects)
    add_box("florist-door-jamb-outer", (0.24, 0.14, 2.62), (-3.91, -2.82, 1.36), materials["trim"], objects)
    add_box("florist-door-lintel", (0.24, 0.95, 0.15), (-3.91, -2.42, 2.62), materials["trim"], objects)
    add_box("florist-roof-slab", (7.62, 6.12, 0.18), (0.0, 0.0, 10.49), materials["wall"], objects)

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


def export_glb(objects):
    GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
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
    )


def point_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_preview_environment():
    ground = add_box(
        "preview-ground",
        (18.0, 18.0, 0.08),
        (0.0, 0.0, -0.05),
        create_material("preview-ground-material", (0.025, 0.028, 0.034), 1.0),
        [],
    )
    ground.hide_render = False

    bpy.ops.object.light_add(type="AREA", location=(-9.0, -3.0, 9.0))
    key = bpy.context.object
    key.name = "preview-warm-key"
    key.data.energy = 1050
    key.data.color = (1.0, 0.66, 0.38)
    key.data.shape = "RECTANGLE"
    key.data.size = 7.0
    point_at(key, (-3.75, 0.0, 5.0))

    bpy.ops.object.light_add(type="AREA", location=(-4.5, 5.0, 4.2))
    fill = bpy.context.object
    fill.name = "preview-cool-fill"
    fill.data.energy = 650
    fill.data.color = (0.25, 0.40, 0.70)
    fill.data.size = 5.0
    point_at(fill, (-3.0, 0.0, 4.2))


def render_preview(path, camera_location):
    scene = bpy.context.scene
    camera = bpy.data.objects.get("preview-camera")
    if camera is None:
        bpy.ops.object.camera_add(location=camera_location)
        camera = bpy.context.object
        camera.name = "preview-camera"
        camera.data.lens = 56
        scene.camera = camera
    camera.location = camera_location
    point_at(camera, (-2.8, 0.0, 5.0))

    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 800
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(path)
    scene.render.film_transparent = False
    scene.world.color = (0.006, 0.008, 0.014)
    scene.render.image_settings.color_mode = "RGBA"
    bpy.ops.render.render(write_still=True)


def main():
    generate_texture_derivatives()
    clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0

    objects = build_florist()
    triangles = triangle_count(objects)
    save_master()
    export_glb(objects)

    add_preview_environment()
    PREVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    render_preview(PREVIEW_PATH, (-17.5, -4.8, 7.4))
    render_preview(OBLIQUE_PREVIEW_PATH, (-14.0, -12.0, 7.8))

    print(f"Reference preserved: {REFERENCE_PATH}")
    print("Estimated dimensions: 7.50 m deep x 6.00 m wide x 10.40 m high")
    print(f"Florist triangles: {triangles}")
    print(f"Saved Blender master: {BLEND_PATH}")
    print(f"Exported GLB: {GLB_PATH}")
    print(f"Rendered preview: {PREVIEW_PATH}")
    print(f"Rendered oblique preview: {OBLIQUE_PREVIEW_PATH}")


if __name__ == "__main__":
    main()
