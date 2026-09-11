"""Create The Hive architectural blockout and four clay review renders.

This is deliberately the first-pass massing model requested by the brief. It
contains no detailed window modules, screen perforations, signage, or interior.
One Blender unit equals one metre; the Lever Street elevation faces -Y.
"""

from math import radians
from pathlib import Path

import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLEND_PATH = PROJECT_ROOT / "blender" / "source" / "the_hive_blockout.blend"
RENDER_DIR = PROJECT_ROOT / "renders" / "the-hive-blockout"


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


def make_collection(name, parent=None):
    result = bpy.data.collections.new(name)
    (parent.children if parent else bpy.context.scene.collection.children).link(result)
    return result


def make_material(name, color, roughness=0.82, metallic=0.0, alpha=1.0):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, alpha)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, alpha)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        material.surface_render_method = "DITHERED"
    return material


def relink(obj, target_collection):
    for source in list(obj.users_collection):
        source.objects.unlink(obj)
    target_collection.objects.link(obj)


def box(name, dimensions, location, material, target_collection, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material:
        obj.data.materials.append(material)
    if bevel:
        modifier = obj.modifiers.new("BlockoutEdge", "BEVEL")
        modifier.width = bevel
        modifier.segments = 1
    relink(obj, target_collection)
    return obj


def empty(name, location, target_collection, display="PLAIN_AXES", size=0.6):
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    obj.empty_display_type = display
    obj.empty_display_size = size
    target_collection.objects.link(obj)
    return obj


def camera(name, location, target, lens, target_collection):
    data = bpy.data.cameras.new(f"{name}_Data")
    data.lens = lens
    data.sensor_width = 36
    data.clip_start = 0.1
    data.clip_end = 350
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    target_collection.objects.link(obj)
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return obj


def area_light(name, location, energy, size, target, target_collection):
    data = bpy.data.lights.new(name=f"{name}_Data", type="AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name=name, object_data=data)
    obj.location = location
    target_collection.objects.link(obj)
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return obj


def build_blockout():
    clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"

    master = make_collection("HIVE_MASTER")
    groups = {
        "ground": make_collection("HIVE_GroundFloor", master),
        "dark": make_collection("HIVE_DarkBrickVolume", master),
        "tower_a": make_collection("HIVE_UpperTower_A", master),
        "tower_b": make_collection("HIVE_UpperTower_B", master),
        "recessed": make_collection("HIVE_RecessedFloor", master),
        "screen": make_collection("HIVE_ScreenFacade", master),
        "entrance": make_collection("HIVE_Entrance", master),
        "context": make_collection("HIVE_BlockoutContext", master),
        "cameras": make_collection("HIVE_BlockoutCameras", master),
        "lights": make_collection("HIVE_BlockoutLights", master),
    }

    mats = {
        "dark": make_material("MAT_DarkBrick_PLACEHOLDER", (0.18, 0.19, 0.20)),
        "pale": make_material("MAT_PaleBrick_PLACEHOLDER", (0.62, 0.59, 0.52)),
        "concrete": make_material("MAT_Concrete_PLACEHOLDER", (0.50, 0.51, 0.49)),
        "screen": make_material("MAT_MetalScreen_PLACEHOLDER", (0.46, 0.49, 0.50), 0.48, 0.28),
        "metal": make_material("MAT_DarkMetal_PLACEHOLDER", (0.12, 0.13, 0.14), 0.52, 0.12),
        "glass": make_material("MAT_Glass_PLACEHOLDER", (0.20, 0.27, 0.29), 0.32),
        "white": make_material("MAT_WhiteWall_PLACEHOLDER", (0.76, 0.76, 0.73)),
        "interior": make_material("MAT_Interior_PLACEHOLDER", (0.38, 0.37, 0.35)),
        "ground": make_material("MAT_BlockoutGround", (0.30, 0.305, 0.30)),
    }

    # Reference-derived envelope: approximately 45 m frontage, 19 m deep,
    # 33 m at the tallest parapet. Lever Street is along Y=-1.4.
    # Transparent/recessed street base.
    box("HIVE_GroundFloor_Base", (44.0, 16.0, 3.7), (0.0, 8.25, 1.85), mats["glass"], groups["ground"])
    box("HIVE_GroundFloor_Soffit", (44.0, 18.0, 0.38), (0.0, 7.6, 3.62), mats["concrete"], groups["ground"])

    # A few broad structural piers belong to the blockout because they define
    # the open-base rhythm; detailed bay/mullion work is intentionally deferred.
    for index, x in enumerate((-21.2, -15.0, -8.8, -2.6, 3.6, 9.8, 16.0, 21.2)):
        box(
            f"HIVE_GroundFloor_BlockoutPier_{index + 1:02d}",
            (0.72, 1.2, 3.7),
            (x, -0.85, 1.85),
            mats["concrete"],
            groups["ground"],
        )

    # Interlocking black-brick lower masses. The east/corner wing projects
    # forward and turns the facade, as the three-quarter references show.
    box("HIVE_DarkBrick_MainBar", (44.0, 17.6, 7.5), (0.0, 7.8, 7.45), mats["dark"], groups["dark"])
    box("HIVE_DarkBrick_WestWing", (11.4, 18.6, 9.1), (-16.3, 7.35, 8.25), mats["dark"], groups["dark"])
    box("HIVE_DarkBrick_EastCorner", (9.6, 19.0, 10.4), (17.2, 7.2, 8.9), mats["dark"], groups["dark"])

    # Screen envelope: six separate, shallow panels with a real 0.75 m air gap.
    # Major frames and perforation pattern are intentionally reserved for pass 2.
    screen_left = -10.8
    panel_width = 4.38
    for index in range(6):
        x = screen_left + panel_width * 0.5 + index * panel_width
        box(
            f"HIVE_ScreenEnvelope_{index + 1:02d}",
            (panel_width - 0.10, 0.11, 8.45),
            (x, -1.51, 8.15),
            mats["screen"],
            groups["screen"],
        )

    # Light recessed floor separates screen/dark podium from the upper towers.
    box("HIVE_RecessedFloor_Main", (31.4, 16.6, 3.0), (1.0, 8.25, 13.15), mats["white"], groups["recessed"])
    box("HIVE_RecessedFloor_West", (10.4, 16.0, 2.6), (-16.1, 8.5, 12.95), mats["white"], groups["recessed"])

    # Placeholder masses for the large projecting shading banks seen above the
    # screens. These establish silhouette only, not the detailed louvre blades.
    for index, x in enumerate((-12.8, -5.8, 1.2, 8.2, 15.2)):
        box(
            f"HIVE_RecessedFloor_LouvreEnvelope_{index + 1:02d}",
            (2.0, 1.05, 2.1),
            (x, -0.62, 14.0),
            mats["metal"],
            groups["recessed"],
        )

    # Two pale upper blocks. Both project beyond their supporting recessed floor;
    # Tower A is the dominant central/east volume and Tower B steps back west.
    box("HIVE_UpperTower_A_Core", (16.6, 17.8, 17.5), (8.5, 7.65, 23.95), mats["pale"], groups["tower_a"])
    box("HIVE_UpperTower_A_Cantilever", (18.2, 18.9, 3.4), (8.2, 7.15, 16.9), mats["pale"], groups["tower_a"])
    box("HIVE_UpperTower_A_DarkFaceEnvelope", (7.3, 0.20, 13.7), (5.7, -1.31, 25.0), mats["metal"], groups["tower_a"])

    box("HIVE_UpperTower_B_Core", (13.2, 16.4, 15.2), (-13.8, 8.8, 22.25), mats["pale"], groups["tower_b"])
    box("HIVE_UpperTower_B_Cantilever", (14.7, 17.6, 3.2), (-13.5, 8.2, 16.25), mats["pale"], groups["tower_b"])
    box("HIVE_UpperTower_B_DarkFaceEnvelope", (5.4, 0.20, 11.8), (-11.4, -0.09, 23.0), mats["metal"], groups["tower_b"])

    # Parapet caps make the two rectangular roof heights explicit.
    box("HIVE_UpperTower_A_Parapet", (16.9, 18.1, 0.42), (8.5, 7.65, 32.91), mats["pale"], groups["tower_a"])
    box("HIVE_UpperTower_B_Parapet", (13.5, 16.7, 0.42), (-13.8, 8.8, 30.06), mats["pale"], groups["tower_b"])

    # Entrance location and depth study only. Door leaves are separate and named
    # so the gameplay intent survives into the detailed pass.
    entrance_x = -4.7
    empty("ACE_FrontEntrance", (entrance_x, -1.02, 0.0), groups["entrance"], "CUBE", 1.0)
    box("ACE_EntranceCanopy", (8.6, 2.4, 0.44), (entrance_x, -2.05, 3.38), mats["metal"], groups["entrance"])
    box("ACE_EntranceCanopySupport_Left", (0.48, 2.25, 3.18), (entrance_x - 4.04, -2.02, 1.59), mats["metal"], groups["entrance"])
    box("ACE_EntranceCanopySupport_Right", (0.48, 2.25, 3.18), (entrance_x + 4.04, -2.02, 1.59), mats["metal"], groups["entrance"])
    box("ACE_EntranceGlass", (6.9, 0.10, 2.72), (entrance_x, -0.78, 1.46), mats["glass"], groups["entrance"])
    box("ACE_FrontDoor_Left", (1.40, 0.14, 2.55), (entrance_x - 0.78, -1.23, 1.31), mats["metal"], groups["entrance"])
    box("ACE_FrontDoor_Right", (1.40, 0.14, 2.55), (entrance_x + 0.78, -1.23, 1.31), mats["metal"], groups["entrance"])
    empty("ACE_EntranceTriggerAnchor", (entrance_x, -3.5, 1.0), groups["entrance"], "ARROWS", 0.7)

    # Minimal pavement/context strip only; no road furniture or adjacent buildings.
    box("HIVE_Context_Pavement", (55.0, 8.0, 0.16), (0.0, -5.3, -0.08), mats["concrete"], groups["context"])
    box("HIVE_Context_Ground", (72.0, 58.0, 0.20), (0.0, 19.0, -0.20), mats["ground"], groups["context"])

    # Four named review cameras matching the brief.
    cameras = [
        camera("CAMERA_A_WideStreetThreeQuarter", (-35.0, -43.0, 18.0), (0.0, 6.0, 15.5), 47, groups["cameras"]),
        camera("CAMERA_B_OppositeThreeQuarter", (36.0, -38.0, 16.5), (1.0, 6.5, 15.0), 47, groups["cameras"]),
        camera("CAMERA_C_FrontLeverStreet", (0.0, -58.0, 15.5), (0.0, 5.0, 15.5), 52, groups["cameras"]),
        camera("CAMERA_D_ACEEntrancePedestrian", (-4.7, -16.5, 1.65), (-4.7, -0.9, 1.65), 42, groups["cameras"]),
    ]

    area_light("HIVE_Key", (-28.0, -24.0, 48.0), 5000, 18.0, (0.0, 6.0, 13.0), groups["lights"])
    area_light("HIVE_Fill", (29.0, -18.0, 28.0), 3000, 17.0, (0.0, 5.0, 13.0), groups["lights"])
    area_light("HIVE_Rim", (0.0, 31.0, 38.0), 4000, 15.0, (0.0, 8.0, 17.0), groups["lights"])
    area_light("HIVE_EntranceFill", (-4.7, -11.0, 8.0), 2500, 9.0, (-4.7, -0.8, 1.8), groups["lights"])

    world = scene.world or bpy.data.worlds.new("HIVE_BlockoutWorld")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.12, 0.14, 0.16, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.45

    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = str(RENDER_DIR / "preview.png")
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.10
    scene.camera = cameras[0]

    # A short internal note keeps the inference/phase boundary with the file.
    note = bpy.data.texts.new("HIVE_BLOCKOUT_NOTES")
    note.write(
        "FIRST PASS / REVIEW HOLD\n"
        "Approximate envelope: 44 m frontage x 19 m depth x 33 m max height.\n"
        "Lever Street faces -Y. Ground level Z=0. One unit=one metre.\n"
        "Screen planes have a real air gap; perforations and frames are deferred.\n"
        "Windows, glazing bays, detailed entrance, louvres and lobby are pass 2.\n"
    )
    return cameras


def render_reviews(cameras):
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    names = (
        "01-wide-street-three-quarter.png",
        "02-opposite-three-quarter.png",
        "03-front-lever-street.png",
        "04-ace-entrance-pedestrian.png",
    )
    scene = bpy.context.scene
    for camera_obj, filename in zip(cameras, names):
        scene.camera = camera_obj
        if filename.startswith("04-"):
            scene.render.resolution_x = 1200
            scene.render.resolution_y = 800
        else:
            scene.render.resolution_x = 1200
            scene.render.resolution_y = 900
        scene.render.filepath = str(RENDER_DIR / filename)
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    cameras = build_blockout()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    render_reviews(cameras)
    # Save again with Camera A active and the final render path no longer relevant.
    bpy.context.scene.camera = cameras[0]
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    print(f"Saved {BLEND_PATH}")
    print(f"Rendered review images to {RENDER_DIR}")
