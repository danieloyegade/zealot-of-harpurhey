"""Generate the Harperhay bus shelter master, GLB, and preview render."""

from mathutils import Vector
from pathlib import Path

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLEND_PATH = PROJECT_ROOT / "blender" / "source" / "harperhay-bus-shelter.blend"
GLB_PATH = PROJECT_ROOT / "public" / "assets" / "models" / "harperhay-bus-shelter.glb"
PREVIEW_PATH = PROJECT_ROOT / "renders" / "harperhay-bus-shelter-preview.png"


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def create_material(name, color, roughness=0.8, alpha=1.0):
    material = bpy.data.materials.new(name=name)
    material.use_nodes = True

    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (*color, 1.0)
    principled.inputs["Roughness"].default_value = roughness
    principled.inputs["Alpha"].default_value = alpha

    if alpha < 1.0:
        material.blend_method = "BLEND"
        material.use_screen_refraction = True
        material.show_transparent_back = True

    return material


def add_box(name, dimensions, location, material, asset_objects):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.name = f"{name}-mesh"
    obj.data.materials.append(material)
    asset_objects.append(obj)
    return obj


def build_shelter():
    frame = create_material("mat-frame", (0.12, 0.18, 0.19), roughness=0.72)
    panel = create_material(
        "mat-panel", (0.18, 0.42, 0.45), roughness=0.45, alpha=0.52
    )
    bench = create_material("mat-bench", (0.34, 0.16, 0.09), roughness=0.9)
    roof = create_material("mat-roof", (0.22, 0.27, 0.27), roughness=0.85)

    objects = []

    # Blender uses Z-up. The shelter is 1.5 m deep on X, 3.7 m long on Y,
    # and 2.38 m high. Its open front faces positive X.
    add_box("shelter-roof", (1.58, 3.86, 0.14), (0.0, 0.0, 2.31), roof, objects)

    for x in (-0.70, 0.70):
        for y in (-1.73, 1.73):
            post_name = "rear" if x < 0 else "front"
            side_name = "south" if y < 0 else "north"
            add_box(
                f"shelter-post-{post_name}-{side_name}",
                (0.10, 0.10, 2.28),
                (x, y, 1.14),
                frame,
                objects,
            )

    add_box(
        "shelter-rear-panel",
        (0.07, 3.30, 1.72),
        (-0.68, 0.0, 1.20),
        panel,
        objects,
    )
    add_box(
        "shelter-side-panel-south",
        (1.30, 0.07, 1.72),
        (0.0, -1.70, 1.20),
        panel,
        objects,
    )
    add_box(
        "shelter-side-panel-north",
        (1.30, 0.07, 1.72),
        (0.0, 1.70, 1.20),
        panel,
        objects,
    )

    add_box("bench-seat", (0.55, 2.48, 0.12), (-0.29, 0.0, 0.58), bench, objects)
    add_box("bench-back", (0.10, 2.48, 0.58), (-0.55, 0.0, 0.89), bench, objects)
    add_box("bench-leg-south", (0.12, 0.16, 0.52), (-0.29, -0.90, 0.29), frame, objects)
    add_box("bench-leg-north", (0.12, 0.16, 0.52), (-0.29, 0.90, 0.29), frame, objects)

    return objects


def save_master():
    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), check_existing=False)


def export_glb(asset_objects):
    GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in asset_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = asset_objects[0]

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
    ground_material = create_material("preview-ground", (0.035, 0.045, 0.06), 1.0)
    bpy.ops.mesh.primitive_plane_add(size=14.0, location=(0.0, 0.0, 0.0))
    ground = bpy.context.object
    ground.name = "preview-ground"
    ground.data.materials.append(ground_material)

    bpy.ops.object.camera_add(location=(5.4, -5.8, 3.5))
    camera = bpy.context.object
    camera.name = "preview-camera"
    camera.data.lens = 52
    point_at(camera, (0.0, 0.0, 1.15))
    bpy.context.scene.camera = camera

    bpy.ops.object.light_add(type="AREA", location=(2.5, -2.5, 5.0))
    key = bpy.context.object
    key.name = "preview-key"
    key.data.energy = 550
    key.data.size = 4.0
    key.data.color = (1.0, 0.72, 0.45)
    point_at(key, (0.0, 0.0, 1.0))

    bpy.ops.object.light_add(type="AREA", location=(-3.0, 3.0, 3.2))
    fill = bpy.context.object
    fill.name = "preview-fill"
    fill.data.energy = 350
    fill.data.size = 5.0
    fill.data.color = (0.42, 0.55, 1.0)
    point_at(fill, (0.0, 0.0, 1.0))


def render_preview():
    PREVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.render.resolution_x = 640
    scene.render.resolution_y = 480
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(PREVIEW_PATH)
    scene.render.film_transparent = False
    scene.world.color = (0.008, 0.012, 0.025)
    bpy.ops.render.render(write_still=True)


def main():
    clear_scene()

    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0

    shelter_objects = build_shelter()
    save_master()
    export_glb(shelter_objects)
    add_preview_setup()
    render_preview()

    print(f"Saved Blender master: {BLEND_PATH}")
    print(f"Exported GLB: {GLB_PATH}")
    print(f"Rendered preview: {PREVIEW_PATH}")


if __name__ == "__main__":
    main()
