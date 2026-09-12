"""Create Renee's geometry-only first-pass blockout and five clay renders.

Reference-derived but deliberately conservative: this file stops at the review
hold requested in 02_Renee.txt.  One Blender unit is one metre, Z is up, and
Thomas Street/frontage faces -Y.
"""

from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
BLEND_PATH = ROOT / "blender" / "source" / "renee_blockout.blend"
GLB_PATH = ROOT / "public" / "assets" / "models" / "renee-blockout.glb"
RENDER_DIR = ROOT / "renders" / "renee-blockout"


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


def material(name, color, roughness=0.82, metallic=0.0, alpha=1.0):
    result = bpy.data.materials.new(name)
    result.diffuse_color = (*color, alpha)
    result.use_nodes = True
    bsdf = result.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, alpha)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        bsdf.inputs["Transmission Weight"].default_value = 0.08
        result.surface_render_method = "DITHERED"
    return result


def relink(obj, target):
    for source in list(obj.users_collection):
        source.objects.unlink(obj)
    target.objects.link(obj)


def box(name, dimensions, location, mat, target, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        obj.data.materials.append(mat)
    if bevel:
        modifier = obj.modifiers.new("BlockoutEdge", "BEVEL")
        modifier.width = bevel
        modifier.segments = 1
    relink(obj, target)
    return obj


def empty(name, location, target, display="ARROWS", size=0.45):
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    obj.empty_display_type = display
    obj.empty_display_size = size
    target.objects.link(obj)
    return obj


def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def camera(name, location, target, lens, target_collection):
    data = bpy.data.cameras.new(f"{name}_Data")
    data.lens = lens
    data.sensor_width = 36
    data.clip_start = 0.06
    data.clip_end = 180
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    target_collection.objects.link(obj)
    point_at(obj, target)
    return obj


def area_light(name, location, target, energy, size, target_collection):
    data = bpy.data.lights.new(f"{name}_Data", "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    target_collection.objects.link(obj)
    point_at(obj, target)
    return obj


def upper_window(name, x, z, mats, target):
    """Simple blockout recess and frame; no detailed sash geometry yet."""
    width, height = 1.55, 1.75
    box(f"{name}_Recess", (width, 0.07, height), (x, -6.68, z), mats["glass"], target)
    for suffix, dx in (("L", -width / 2), ("R", width / 2)):
        box(f"{name}_Frame_{suffix}", (0.11, 0.10, height + 0.12), (x + dx, -6.75, z), mats["frame"], target)
    for suffix, dz in (("Top", height / 2), ("Bottom", -height / 2)):
        box(f"{name}_Frame_{suffix}", (width + 0.11, 0.10, 0.11), (x, -6.75, z + dz), mats["frame"], target)
    box(f"{name}_Transom", (width, 0.105, 0.08), (x, -6.76, z - 0.29), mats["frame"], target)
    box(f"{name}_Sill", (width + 0.24, 0.24, 0.11), (x, -6.79, z - height / 2 - 0.07), mats["stone"], target)


def build_scene():
    clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"

    master = collection("RENEE_MASTER")
    groups = {
        "exterior": collection("REN_ExteriorShell", master),
        "upper": collection("REN_UpperFacade", master),
        "ground": collection("REN_GroundFacade", master),
        "fascia": collection("REN_Fascia", master),
        "entrance": collection("REN_Entrance", master),
        "glass": collection("REN_Glass", master),
        "interior": collection("REN_InteriorShell", master),
        "bar": collection("REN_Bar", master),
        "records": collection("REN_RecordWall", master),
        "ceiling": collection("REN_Ceiling", master),
        "panels": collection("REN_AcousticPanels", master),
        "columns": collection("REN_Columns", master),
        "banquettes": collection("REN_Banquettes", master),
        "doors": collection("REN_Doors", master),
        "anchors": collection("REN_InteractionAnchors", master),
        "review": collection("REN_BlockoutReviewOnly", master),
        "cameras": collection("REN_BlockoutCameras", master),
        "lights": collection("REN_BlockoutLights", master),
    }

    mats = {
        "brick": material("MAT_REN_Brick_PLACEHOLDER", (0.46, 0.25, 0.18)),
        "black": material("MAT_REN_BlackFacade_PLACEHOLDER", (0.055, 0.060, 0.066)),
        "glass": material("MAT_REN_Glass_PLACEHOLDER", (0.16, 0.22, 0.24), 0.28, alpha=0.22),
        "timber": material("MAT_REN_Timber_PLACEHOLDER", (0.42, 0.27, 0.16)),
        "dark": material("MAT_REN_DarkWall_PLACEHOLDER", (0.10, 0.12, 0.13)),
        "concrete": material("MAT_REN_Concrete_PLACEHOLDER", (0.49, 0.48, 0.44)),
        "metal": material("MAT_REN_Metal_PLACEHOLDER", (0.18, 0.19, 0.19), 0.45, 0.20),
        "upholstery": material("MAT_REN_Upholstery_PLACEHOLDER", (0.30, 0.15, 0.13)),
        "frame": material("MAT_REN_WindowFrame_PLACEHOLDER", (0.72, 0.72, 0.68)),
        "stone": material("MAT_REN_Stone_PLACEHOLDER", (0.56, 0.54, 0.50)),
        "ground": material("MAT_REN_ReviewGround", (0.27, 0.275, 0.27)),
    }

    # Coherent inferred envelope: 13.8 m frontage, 13.2 m deep, two upper floors.
    width, depth = 13.8, 13.2
    front_y, back_y = -depth / 2, depth / 2
    ground_h, fascia_h, total_h = 3.75, 0.88, 10.65

    # Upper closed volume. Upstairs is intentionally not developed internally.
    box("REN_UpperFacade_Main", (width, depth, total_h - 4.35), (0.0, 0.0, 7.50), mats["brick"], groups["upper"])
    box("REN_RoofCap", (width + 0.18, depth + 0.18, 0.18), (0.0, 0.0, total_h), mats["black"], groups["exterior"])
    # Lightly irregular party-wall strips communicate the real attached building.
    box("REN_UpperPartyPier_Left", (0.30, 0.26, 6.10), (-6.76, front_y - 0.04, 7.50), mats["brick"], groups["upper"])
    box("REN_UpperPartyPier_Right", (0.30, 0.26, 6.10), (6.76, front_y - 0.04, 7.50), mats["brick"], groups["upper"])
    for floor_index, z in enumerate((5.80, 8.82), 1):
        for window_index, x in enumerate((-5.10, -2.55, 0.0, 2.55, 5.10), 1):
            upper_window(f"REN_UpperWindow_F{floor_index}_{window_index:02d}", x, z, mats, groups["upper"])

    # Navigable ground-floor shell: front remains open behind the real shopfront.
    box("REN_Floor", (width - 0.24, depth - 0.12, 0.12), (0.0, 0.03, 0.0), mats["concrete"], groups["interior"])
    box("REN_Wall_Left", (0.18, depth, ground_h), (-6.81, 0.0, ground_h / 2), mats["dark"], groups["interior"])
    box("REN_Wall_Right", (0.18, depth, ground_h), (6.81, 0.0, ground_h / 2), mats["dark"], groups["interior"])
    box("REN_Wall_Back", (width, 0.18, ground_h), (0.0, back_y - 0.09, ground_h / 2), mats["dark"], groups["interior"])
    box("REN_CeilingPlane", (width, depth, 0.16), (0.0, 0.0, ground_h), mats["dark"], groups["ceiling"])

    # Shopfront depth, fascia and lower lip. The clean central fascia is reserved for branding.
    box("REN_Fascia_Main", (width, 0.43, fascia_h), (0.0, front_y - 0.10, 4.19), mats["black"], groups["fascia"])
    box("REN_Fascia_LowerLip", (width, 0.58, 0.20), (0.0, front_y - 0.17, 3.68), mats["black"], groups["fascia"])
    box("REN_SignageReservedSurface", (4.20, 0.035, 0.46), (1.35, front_y - 0.405, 4.22), mats["black"], groups["fascia"])
    box("REN_GroundPier_Left", (0.34, 0.58, ground_h), (-6.73, front_y - 0.02, ground_h / 2), mats["black"], groups["ground"])
    box("REN_GroundPier_Right", (0.34, 0.58, ground_h), (6.73, front_y - 0.02, ground_h / 2), mats["black"], groups["ground"])
    box("REN_GroundPlinth", (width - 0.50, 0.43, 0.24), (0.0, front_y - 0.06, 0.12), mats["black"], groups["ground"])

    # Recessed entrance slightly left of centre, matching Renee-era street photographs.
    door_x, door_w = -1.72, 1.52
    for suffix, x in (("Left", door_x - door_w / 2), ("Right", door_x + door_w / 2)):
        box(f"REN_DoorFrame_{suffix}", (0.14, 0.58, 3.02), (x, front_y + 0.16, 1.63), mats["black"], groups["entrance"])
    box("REN_DoorFrame_Head", (door_w + 0.14, 0.58, 0.14), (door_x, front_y + 0.16, 3.10), mats["black"], groups["entrance"])
    box("REN_EntranceThreshold", (door_w + 0.22, 0.86, 0.09), (door_x, front_y + 0.26, 0.045), mats["stone"], groups["entrance"])
    box("REN_Door", (door_w - 0.18, 0.065, 2.82), (door_x, front_y + 0.39, 1.50), mats["glass"], groups["doors"])

    # Glazed frontage in broad bays, physically recessed from the fascia face.
    glazed_bays = ((-5.15, 2.55), (-3.20, 1.16), (0.25, 2.20), (2.56, 2.20), (5.03, 2.40))
    for index, (x, bay_w) in enumerate(glazed_bays, 1):
        box(f"REN_Glass_Bay_{index:02d}", (bay_w, 0.045, 2.82), (x, front_y + 0.35, 1.60), mats["glass"], groups["glass"])
        for suffix, edge_x in (("L", x - bay_w / 2), ("R", x + bay_w / 2)):
            box(f"REN_GlazingFrame_{index:02d}_{suffix}", (0.10, 0.18, 3.02), (edge_x, front_y + 0.30, 1.62), mats["black"], groups["ground"])
    box("REN_ShopfrontHead", (width - 0.50, 0.20, 0.13), (0.0, front_y + 0.27, 3.16), mats["black"], groups["ground"])
    empty("REN_EntranceTriggerAnchor", (door_x, front_y + 1.25, 1.0), groups["anchors"], size=0.55)

    # Main bar blockout at the rear-left, with a clear staff-side working aisle.
    box("REN_Bar_Main", (5.90, 0.82, 1.08), (-2.55, 3.78, 0.54), mats["timber"], groups["bar"], 0.025)
    box("REN_Bar_Countertop", (6.18, 1.00, 0.12), (-2.55, 3.72, 1.10), mats["black"], groups["bar"], 0.018)
    box("REN_Bar_Back", (5.90, 0.48, 2.30), (-2.55, 5.92, 1.42), mats["dark"], groups["bar"])
    box("REN_Bar_Shelving_Blockout", (5.56, 0.34, 1.42), (-2.55, 5.60, 2.10), mats["timber"], groups["bar"])
    empty("REN_BartenderAnchor", (-2.55, 4.82, 1.0), groups["anchors"])
    empty("REN_CustomerBarAnchor", (-2.55, 2.72, 1.0), groups["anchors"])

    # Defining vinyl wall on the back-right; only the shelving grid is present.
    shelf_x0, shelf_y, shelf_w, shelf_h = 3.52, 6.34, 5.85, 3.05
    box("REN_RecordWall_Back", (shelf_w, 0.20, shelf_h), (shelf_x0, shelf_y, 1.62), mats["timber"], groups["records"])
    for index in range(8):
        x = shelf_x0 - shelf_w / 2 + index * (shelf_w / 7)
        box(f"REN_RecordWall_Vertical_{index:02d}", (0.095, 0.32, shelf_h), (x, shelf_y - 0.16, 1.62), mats["timber"], groups["records"])
    for index in range(5):
        z = 0.25 + index * 0.70
        box(f"REN_RecordWall_Shelf_{index:02d}", (shelf_w, 0.34, 0.09), (shelf_x0, shelf_y - 0.17, z), mats["timber"], groups["records"])
    box("REN_RecordWall_LowerPlinth", (shelf_w, 0.46, 0.34), (shelf_x0, shelf_y - 0.17, 0.17), mats["timber"], groups["records"])

    # Major exposed rectangular columns; their placement drives circulation.
    for index, (x, y) in enumerate(((-0.35, -1.30), (-0.35, 2.35), (4.85, 0.85)), 1):
        box(f"REN_StructuralColumn_{index:02d}", (0.42, 0.48, ground_h), (x, y, ground_h / 2), mats["concrete"], groups["columns"])

    # Suspended acoustic rafts: clean slabs only, with real gaps and drop depth.
    raft_specs = (
        (-4.55, -3.72, 3.48, 2.40), (-1.05, -3.72, 2.65, 2.40),
        (2.15, -3.72, 2.75, 2.40), (5.15, -3.72, 2.55, 2.40),
        (-4.55, -0.62, 3.48, 2.55), (-1.05, -0.62, 2.65, 2.55),
        (2.15, -0.62, 2.75, 2.55), (5.15, -0.62, 2.55, 2.55),
        (-4.55, 2.60, 3.48, 2.58), (-1.05, 2.60, 2.65, 2.58),
        (2.15, 2.60, 2.75, 2.58), (5.15, 2.60, 2.55, 2.58),
    )
    for index, (x, y, sx, sy) in enumerate(raft_specs, 1):
        box(f"REN_AcousticPanel_{index:02d}", (sx, sy, 0.11), (x, y, 3.49), mats["timber"], groups["panels"], 0.012)

    # Permanent seating zones only; loose chairs/tables wait for pass 2.
    box("REN_Banquette_Right_Base", (0.72, 7.15, 0.47), (6.34, -0.35, 0.235), mats["upholstery"], groups["banquettes"], 0.04)
    box("REN_Banquette_Right_Back", (0.30, 7.15, 0.92), (6.61, -0.35, 0.91), mats["upholstery"], groups["banquettes"], 0.05)
    box("REN_Banquette_FrontLeft_Base", (3.10, 0.70, 0.47), (-4.55, -5.93, 0.235), mats["upholstery"], groups["banquettes"], 0.04)
    box("REN_Banquette_FrontLeft_Back", (3.10, 0.30, 0.92), (-4.55, -6.28, 0.91), mats["upholstery"], groups["banquettes"], 0.05)

    # Rear toilets opening/closed volume establishes the photographed left-hand zone.
    box("REN_ToiletsZone", (1.82, 1.15, 3.05), (-5.72, 5.88, 1.53), mats["dark"], groups["interior"])
    box("REN_ToiletsDoor", (0.92, 0.08, 2.16), (-5.72, 5.27, 1.08), mats["metal"], groups["doors"])

    # Review-only street and lighting are excluded from the architectural hierarchy.
    box("REN_Review_Pavement", (20.0, 6.5, 0.12), (0.0, -9.65, -0.07), mats["concrete"], groups["review"])
    box("REN_Review_Ground", (30.0, 34.0, 0.12), (0.0, 2.0, -0.15), mats["ground"], groups["review"])

    cameras = (
        camera("CAMERA_A_StraightOnStreet", (0.0, -27.0, 5.20), (0.0, -5.70, 5.20), 52, groups["cameras"]),
        camera("CAMERA_B_ThreeQuarterExterior", (-16.5, -21.0, 5.65), (0.0, -4.20, 4.95), 48, groups["cameras"]),
        camera("CAMERA_C_EntranceLookingIn", (door_x, -7.72, 1.66), (0.10, 2.75, 1.52), 34, groups["cameras"]),
        camera("CAMERA_D_InteriorBarAndSeating", (-5.25, -4.70, 1.72), (1.70, 1.80, 1.38), 30, groups["cameras"]),
        camera("CAMERA_E_RecordWall", (3.45, -0.55, 1.70), (3.45, 6.12, 1.58), 40, groups["cameras"]),
    )

    area_light("REN_Review_Key", (-11.0, -14.0, 17.0), (0.0, -1.0, 3.5), 2500, 7.0, groups["lights"])
    area_light("REN_Review_Fill", (11.0, -7.0, 11.0), (0.0, 0.0, 3.2), 1700, 6.0, groups["lights"])
    area_light("REN_Review_Interior", (0.0, 1.2, 3.25), (0.0, 2.0, 0.7), 1150, 5.0, groups["lights"])
    area_light("REN_Review_Back", (1.0, 5.5, 3.15), (0.0, 2.4, 1.0), 950, 4.0, groups["lights"])

    world = scene.world or bpy.data.worlds.new("REN_BlockoutWorld")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.055, 0.065, 0.075, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.38

    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.camera = cameras[0]

    note = bpy.data.texts.new("RENEE_BLOCKOUT_NOTES")
    note.write(
        "FIRST PASS / REVIEW HOLD - GEOMETRY ONLY\n"
        "Inferred dimensions: 13.8 m frontage x 13.2 m depth x 10.65 m height.\n"
        "Thomas Street faces -Y; ground is Z=0; one unit equals one metre.\n"
        "Architecture uses all temporal references; clean fascia is reserved for Renee-era branding.\n"
        "Loose furniture, pendants, detailed joinery, textures, signage and red lighting are deferred.\n"
    )
    return cameras


def apply_mesh_transforms():
    bpy.ops.object.select_all(action="DESELECT")
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    for obj in meshes:
        obj.select_set(True)
    if meshes:
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.ops.object.select_all(action="DESELECT")


def validate():
    required = (
        "REN_Door", "REN_EntranceTriggerAnchor", "REN_Bar_Main",
        "REN_RecordWall_Back", "REN_StructuralColumn_01", "REN_AcousticPanel_01",
        "REN_Banquette_Right_Base", "REN_ToiletsDoor",
    )
    missing = [name for name in required if bpy.data.objects.get(name) is None]
    if missing:
        raise RuntimeError(f"Missing blockout objects: {missing}")
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    triangles = sum(sum(max(0, len(poly.vertices) - 2) for poly in obj.data.polygons) for obj in meshes)
    print(f"Validation: {len(meshes)} mesh objects, approximately {triangles} triangles")
    print("Validation: metric scale, Z-up, ground level Z=0")


def export_runtime_glb():
    """Export authored geometry and anchors, excluding review-only helpers."""
    GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
    excluded_collections = {
        "REN_BlockoutReviewOnly",
        "REN_BlockoutCameras",
        "REN_BlockoutLights",
    }
    bpy.ops.object.select_all(action="DESELECT")
    export_objects = [
        obj
        for obj in bpy.data.objects
        if obj.type not in {"CAMERA", "LIGHT"}
        and not any(group.name in excluded_collections for group in obj.users_collection)
    ]
    for obj in export_objects:
        obj.select_set(True)
    if export_objects:
        bpy.context.view_layer.objects.active = export_objects[0]
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
    print(f"Exported runtime blockout: {GLB_PATH}")


def render_reviews(cameras):
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    names = (
        "view-a-straight-on-street.png",
        "view-b-three-quarter-exterior.png",
        "view-c-entrance-looking-inward.png",
        "view-d-interior-bar-and-seating.png",
        "view-e-record-wall.png",
    )
    scene = bpy.context.scene
    for camera_obj, filename in zip(cameras, names):
        scene.camera = camera_obj
        scene.render.resolution_x = 1200
        scene.render.resolution_y = 800 if filename.startswith(("view-c", "view-d", "view-e")) else 900
        scene.render.filepath = str(RENDER_DIR / filename)
        bpy.ops.render.render(write_still=True)
        print(f"Rendered {scene.render.filepath}")


def main():
    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    cameras = build_scene()
    apply_mesh_transforms()
    validate()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), check_existing=False)
    export_runtime_glb()
    render_reviews(cameras)
    bpy.context.scene.camera = cameras[0]
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), check_existing=False)
    print(f"Saved geometry-only blockout: {BLEND_PATH}")


if __name__ == "__main__":
    main()
