"""Create Advanced Photo's first-pass geometry blockout and four clay renders.

This script stops at the review hold requested by
references/architecture/advanced-photo/03_Advanced_Photo.txt section 23.
It establishes the compact corner footprint, two perpendicular glazed shop
fronts, usable entrance, shallow display volumes, circulation, counter and
major cabinets. Fine mouldings, decorative lower panels, detailed cabinet
frames, door furniture, interaction/light anchors and all graphic surfaces are
reserved for the approved second geometry pass.

One Blender unit is one metre, Z is up, and the main arcade frontage faces -Y.
Dimensions are inferred from the supplied photographs rather than surveyed.
"""

from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
BLEND_PATH = ROOT / "blender" / "source" / "advanced_photo_blockout.blend"
GLB_PATH = ROOT / "public" / "assets" / "models" / "advanced-photo-blockout.glb"
RENDER_DIR = ROOT / "renders" / "advanced-photo-blockout"

# Compact rectangular shop body with public glazing on the south and east.
SHOP_W = 5.80
SHOP_D = 6.20
FRONT_Y = -SHOP_D / 2
BACK_Y = SHOP_D / 2
LEFT_X = -SHOP_W / 2
RIGHT_X = SHOP_W / 2
SHOP_H = 3.55
FASCIA_BOTTOM = 2.78
FASCIA_TOP = 3.48
PLINTH_TOP = 0.58

# Main elevation rhythm, inferred using a 1.05 m commercial door.
ENTRANCE_LEFT = -2.72
ENTRANCE_RIGHT = -1.62
DISPLAY_LEFT = -1.48
DISPLAY_RIGHT = 2.76
SIDE_DISPLAY_FRONT = -2.94
SIDE_DISPLAY_BACK = 0.82


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


def material(name, color, roughness=0.85, metallic=0.0, alpha=1.0):
    result = bpy.data.materials.new(name)
    result.diffuse_color = (*color, alpha)
    result.use_nodes = True
    bsdf = result.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, alpha)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        transmission = bsdf.inputs.get("Transmission Weight") or bsdf.inputs.get("Transmission")
        if transmission:
            transmission.default_value = 0.06
        if hasattr(result, "surface_render_method"):
            result.surface_render_method = "DITHERED"
        else:
            result.blend_method = "BLEND"
    return result


def relink(obj, target):
    for source in list(obj.users_collection):
        source.objects.unlink(obj)
    target.objects.link(obj)


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
        modifier = obj.modifiers.new("BlockoutEdge", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
    relink(obj, target)
    return obj


def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def camera(name, location, target, lens, target_collection):
    data = bpy.data.cameras.new(f"{name}_Data")
    data.lens = lens
    data.sensor_fit = "HORIZONTAL"
    data.sensor_width = 36
    data.clip_start = 0.05
    data.clip_end = 120
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


def cabinet_front(name, centre_x, centre_y, width, depth, height, mats, groups):
    """Economical front-facing glass cabinet with real shelf depth."""
    base_h = 0.32
    top_t = 0.07
    frame_t = 0.055
    box(f"{name}_Base", (width, depth, base_h), (centre_x, centre_y, base_h / 2), mats["counter"], groups["cabinets"], 0.015)
    box(f"{name}_Top", (width, depth, top_t), (centre_x, centre_y, height - top_t / 2), mats["metal"], groups["cabinets"])
    for suffix, x in (("Left", centre_x - width / 2), ("Right", centre_x + width / 2)):
        box(f"{name}_Frame_{suffix}", (frame_t, depth, height - base_h), (x, centre_y, base_h + (height - base_h) / 2), mats["metal"], groups["cabinets"])
    for index, z in enumerate((0.78, 1.20, 1.62), start=1):
        if z < height - 0.10:
            box(f"{name}_Shelf_{index:02d}", (width - 0.08, depth - 0.05, 0.025), (centre_x, centre_y, z), mats["glass"], groups["cabinets"])
    box(f"{name}_GlassFront", (width - 0.08, 0.025, height - base_h - top_t), (centre_x, centre_y - depth / 2, base_h + (height - base_h - top_t) / 2), mats["glass"], groups["glass"])


def cabinet_side(name, centre_x, centre_y, width, depth, height, mats, groups):
    """Cabinet running along the glazed east return, with glass facing +X."""
    base_h = 0.32
    top_t = 0.07
    frame_t = 0.055
    box(f"{name}_Base", (depth, width, base_h), (centre_x, centre_y, base_h / 2), mats["counter"], groups["cabinets"], 0.015)
    box(f"{name}_Top", (depth, width, top_t), (centre_x, centre_y, height - top_t / 2), mats["metal"], groups["cabinets"])
    for suffix, y in (("Front", centre_y - width / 2), ("Back", centre_y + width / 2)):
        box(f"{name}_Frame_{suffix}", (depth, frame_t, height - base_h), (centre_x, y, base_h + (height - base_h) / 2), mats["metal"], groups["cabinets"])
    for index, z in enumerate((0.78, 1.20, 1.62), start=1):
        if z < height - 0.10:
            box(f"{name}_Shelf_{index:02d}", (depth - 0.05, width - 0.08, 0.025), (centre_x, centre_y, z), mats["glass"], groups["cabinets"])
    box(f"{name}_GlassSide", (0.025, width - 0.08, height - base_h - top_t), (centre_x + depth / 2, centre_y, base_h + (height - base_h - top_t) / 2), mats["glass"], groups["glass"])


def build_scene():
    clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"

    master = collection("ADVANCED_PHOTO_MASTER")
    groups = {
        "shell": collection("AP_ShopShell", master),
        "shopfront": collection("AP_Shopfront", master),
        "fascia": collection("AP_Fascia", master),
        "entrance": collection("AP_Entrance", master),
        "glass": collection("AP_Glass", master),
        "display": collection("AP_MainDisplay", master),
        "cabinets": collection("AP_DisplayCabinets", master),
        "interior": collection("AP_Interior", master),
        "counter": collection("AP_Counter", master),
        "wall_shelving": collection("AP_WallShelving", master),
        "arcade": collection("AP_ArcadeContext", master),
        "review": collection("AP_BlockoutReviewOnly", master),
        "cameras": collection("AP_BlockoutCameras", master),
        "lights": collection("AP_BlockoutLights", master),
    }

    mats = {
        "black": material("MAT_AP_BlackWood_PLACEHOLDER", (0.025, 0.028, 0.032), 0.54),
        "glass": material("MAT_AP_Glass_PLACEHOLDER", (0.22, 0.34, 0.38), 0.18, alpha=0.22),
        "metal": material("MAT_AP_Metal_PLACEHOLDER", (0.32, 0.34, 0.36), 0.38, 0.45),
        "wall": material("MAT_AP_InteriorWall_PLACEHOLDER", (0.79, 0.77, 0.71), 0.91),
        "floor": material("MAT_AP_Floor_PLACEHOLDER", (0.69, 0.68, 0.64), 0.72),
        "counter": material("MAT_AP_Counter_PLACEHOLDER", (0.52, 0.38, 0.19), 0.78),
        "arcade_floor": material("MAT_AP_ArcadeFloor_PLACEHOLDER", (0.76, 0.75, 0.72), 0.64),
        "arcade_wall": material("MAT_AP_ArcadeWall_PLACEHOLDER", (0.72, 0.70, 0.66), 0.90),
        "review_ground": material("MAT_AP_ReviewGround", (0.20, 0.205, 0.21), 0.92),
        "review_light": material("MAT_AP_ReviewRing", (0.92, 0.78, 0.49), 0.42),
    }

    # Interior shell. The south and east faces remain open where the real
    # shopfront wraps the arcade corner; solid strips close only non-glazed
    # boundaries and keep the blockout physically coherent.
    box("AP_InteriorFloor", (SHOP_W - 0.18, SHOP_D - 0.18, 0.08), (0.0, 0.0, 0.04), mats["floor"], groups["interior"])
    box("AP_InteriorCeiling", (SHOP_W - 0.18, SHOP_D - 0.18, 0.10), (0.0, 0.0, SHOP_H - 0.12), mats["wall"], groups["interior"])
    box("AP_BackWall", (SHOP_W, 0.18, SHOP_H), (0.0, BACK_Y - 0.09, SHOP_H / 2), mats["wall"], groups["shell"])
    box("AP_LeftWall", (0.18, SHOP_D, SHOP_H), (LEFT_X + 0.09, 0.0, SHOP_H / 2), mats["wall"], groups["shell"])
    side_wall_depth = BACK_Y - SIDE_DISPLAY_BACK
    box("AP_RightRearWall", (0.18, side_wall_depth, SHOP_H), (RIGHT_X - 0.09, SIDE_DISPLAY_BACK + side_wall_depth / 2, SHOP_H / 2), mats["wall"], groups["shell"])
    box("AP_FrontHeadWall", (SHOP_W, 0.20, SHOP_H - FASCIA_TOP), (0.0, FRONT_Y + 0.10, FASCIA_TOP + (SHOP_H - FASCIA_TOP) / 2), mats["wall"], groups["shell"])

    # Broad black fascia on both public elevations. Its stepped mouldings and
    # recessed sign fields are intentionally deferred to the approved pass.
    fascia_h = FASCIA_TOP - FASCIA_BOTTOM
    box("AP_Fascia_Main", (SHOP_W, 0.30, fascia_h), (0.0, FRONT_Y - 0.06, FASCIA_BOTTOM + fascia_h / 2), mats["black"], groups["fascia"], 0.025)
    side_fascia_depth = SIDE_DISPLAY_BACK - FRONT_Y
    box("AP_Fascia_Return", (0.30, side_fascia_depth, fascia_h), (RIGHT_X - 0.06, FRONT_Y + side_fascia_depth / 2, FASCIA_BOTTOM + fascia_h / 2), mats["black"], groups["fascia"], 0.025)

    # Main facade: narrow open entrance at left, hero display across the rest.
    frame_t = 0.12
    frame_depth = 0.25
    for name, x in (
        ("AP_MainPost_Left", LEFT_X + 0.06),
        ("AP_EntrancePost_Left", ENTRANCE_LEFT),
        ("AP_EntrancePost_Right", ENTRANCE_RIGHT),
        ("AP_DisplayPost_Left", DISPLAY_LEFT),
        ("AP_CornerPost", DISPLAY_RIGHT),
    ):
        box(name, (frame_t, frame_depth, FASCIA_BOTTOM), (x, FRONT_Y + 0.05, FASCIA_BOTTOM / 2), mats["black"], groups["shopfront"], 0.012)
    box("AP_MainHeadRail", (SHOP_W - 0.10, frame_depth, 0.14), (0.0, FRONT_Y + 0.05, FASCIA_BOTTOM - 0.07), mats["black"], groups["shopfront"])
    box("AP_MainDisplayPlinth", (DISPLAY_RIGHT - DISPLAY_LEFT, 0.34, PLINTH_TOP), ((DISPLAY_LEFT + DISPLAY_RIGHT) / 2, FRONT_Y + 0.11, PLINTH_TOP / 2), mats["black"], groups["display"], 0.018)
    main_glass_w = DISPLAY_RIGHT - DISPLAY_LEFT - frame_t
    box("AP_ExteriorGlass_Main", (main_glass_w, 0.028, FASCIA_BOTTOM - PLINTH_TOP - 0.12), ((DISPLAY_LEFT + DISPLAY_RIGHT) / 2, FRONT_Y - 0.01, PLINTH_TOP + (FASCIA_BOTTOM - PLINTH_TOP) / 2), mats["glass"], groups["glass"])

    # Door is held open in the photographed state, keeping the 1.10 m opening
    # genuinely navigable. The leaf is separate for the later hinge setup.
    entrance_centre = (ENTRANCE_LEFT + ENTRANCE_RIGHT) / 2
    box("AP_DoorFrame_Head", (ENTRANCE_RIGHT - ENTRANCE_LEFT, frame_depth, 0.12), (entrance_centre, FRONT_Y + 0.05, 2.52), mats["black"], groups["entrance"])
    box("AP_EntranceThreshold", (ENTRANCE_RIGHT - ENTRANCE_LEFT, 0.42, 0.045), (entrance_centre, FRONT_Y + 0.16, 0.0225), mats["metal"], groups["entrance"])
    door_x = ENTRANCE_LEFT + 0.08
    door_y = FRONT_Y - 0.38
    door_h = 2.32
    door_w = 1.02
    door_rail = 0.11
    box("AP_Door_FrameHinge", (0.065, door_rail, door_h), (door_x, door_y - door_w / 2 + door_rail / 2, door_h / 2), mats["black"], groups["entrance"], 0.008)
    box("AP_Door_FrameLatch", (0.065, door_rail, door_h), (door_x, door_y + door_w / 2 - door_rail / 2, door_h / 2), mats["black"], groups["entrance"], 0.008)
    box("AP_Door_FrameBottom", (0.065, door_w - 2 * door_rail, door_rail), (door_x, door_y, door_rail / 2), mats["black"], groups["entrance"], 0.008)
    box("AP_Door_FrameTop", (0.065, door_w - 2 * door_rail, door_rail), (door_x, door_y, door_h - door_rail / 2), mats["black"], groups["entrance"], 0.008)
    box("AP_DoorGlass", (0.035, door_w - 2 * door_rail, door_h - 2 * door_rail), (door_x, door_y, door_h / 2), mats["glass"], groups["glass"])

    # East return display and its clean transition into the solid rear wall.
    for name, y in (
        ("AP_ReturnPost_Front", SIDE_DISPLAY_FRONT),
        ("AP_ReturnPost_Back", SIDE_DISPLAY_BACK),
    ):
        box(name, (frame_depth, frame_t, FASCIA_BOTTOM), (RIGHT_X - 0.05, y, FASCIA_BOTTOM / 2), mats["black"], groups["shopfront"], 0.012)
    box("AP_ReturnHeadRail", (frame_depth, SIDE_DISPLAY_BACK - SIDE_DISPLAY_FRONT, 0.14), (RIGHT_X - 0.05, (SIDE_DISPLAY_FRONT + SIDE_DISPLAY_BACK) / 2, FASCIA_BOTTOM - 0.07), mats["black"], groups["shopfront"])
    box("AP_ReturnDisplayPlinth", (0.34, SIDE_DISPLAY_BACK - SIDE_DISPLAY_FRONT, PLINTH_TOP), (RIGHT_X - 0.11, (SIDE_DISPLAY_FRONT + SIDE_DISPLAY_BACK) / 2, PLINTH_TOP / 2), mats["black"], groups["display"], 0.018)
    box("AP_ExteriorGlass_Return", (0.028, SIDE_DISPLAY_BACK - SIDE_DISPLAY_FRONT - frame_t, FASCIA_BOTTOM - PLINTH_TOP - 0.12), (RIGHT_X + 0.01, (SIDE_DISPLAY_FRONT + SIDE_DISPLAY_BACK) / 2, PLINTH_TOP + (FASCIA_BOTTOM - PLINTH_TOP) / 2), mats["glass"], groups["glass"])

    # Deep hero display volumes, not products pasted behind one pane.
    cabinet_front("AP_DisplayCabinet_Front", 0.58, FRONT_Y + 0.52, 3.65, 0.72, 2.18, mats, groups)
    cabinet_side("AP_DisplayCabinet_Return", RIGHT_X - 0.52, -1.05, 2.70, 0.72, 2.18, mats, groups)
    cabinet_front("AP_DisplayCabinet_Interior01", -1.72, 0.35, 1.55, 0.50, 1.95, mats, groups)

    # Permanent interior furniture only: a customer counter, left/rear wall
    # shelving and a low service-area partition. A clear 1.15 m route runs
    # from the entrance to the counter.
    box("AP_Counter", (2.45, 0.78, 0.96), (0.65, 1.72, 0.48), mats["counter"], groups["counter"], 0.035)
    box("AP_CounterTop", (2.55, 0.86, 0.075), (0.65, 1.72, 0.997), mats["metal"], groups["counter"], 0.018)
    box("AP_RearServicePartition", (2.35, 0.12, 2.42), (1.62, 2.68, 1.21), mats["wall"], groups["interior"])
    box("AP_WallCabinet_Left", (0.42, 2.40, 2.22), (LEFT_X + 0.34, 1.25, 1.11), mats["counter"], groups["wall_shelving"], 0.018)
    for index, z in enumerate((0.48, 0.95, 1.42, 1.89), start=1):
        box(f"AP_WallShelf_Left_{index:02d}", (0.54, 2.30, 0.035), (LEFT_X + 0.29, 1.25, z), mats["metal"], groups["wall_shelving"])
    box("AP_WallCabinet_Rear", (1.75, 0.40, 2.10), (-1.55, BACK_Y - 0.31, 1.05), mats["counter"], groups["wall_shelving"], 0.018)

    # A short L-shaped slice of St Ann's Arcade: tiled floor, ceiling and the
    # immediate opposite boundary. The ring fixture is a blockout cue for the
    # oblique source photograph, not a final light implementation.
    box("AP_ArcadeFloor_Front", (10.8, 3.6, 0.08), (1.25, FRONT_Y - 1.78, -0.04), mats["arcade_floor"], groups["arcade"])
    box("AP_ArcadeFloor_Return", (3.4, 8.0, 0.08), (RIGHT_X + 1.65, 0.10, -0.04), mats["arcade_floor"], groups["arcade"])
    box("AP_ArcadeCeiling_Front", (10.8, 3.6, 0.12), (1.25, FRONT_Y - 1.78, 3.58), mats["arcade_wall"], groups["arcade"])
    box("AP_ArcadeCeiling_Return", (3.4, 8.0, 0.12), (RIGHT_X + 1.65, 0.10, 3.58), mats["arcade_wall"], groups["arcade"])
    box("AP_ArcadeOppositeBoundary", (0.16, 7.8, 3.58), (RIGHT_X + 3.30, 0.10, 1.79), mats["arcade_wall"], groups["arcade"])
    bpy.ops.mesh.primitive_torus_add(major_radius=0.72, minor_radius=0.035, major_segments=32, minor_segments=8, location=(0.55, FRONT_Y - 1.78, 3.49))
    ring = bpy.context.object
    ring.name = "AP_ArcadeRingLight_Blockout"
    ring.data.name = f"{ring.name}_Mesh"
    ring.data.materials.append(mats["review_light"])
    relink(ring, groups["arcade"])

    # Review staging is excluded from GLB.
    box("AP_Review_Ground", (22.0, 20.0, 0.08), (1.0, 0.0, -0.09), mats["review_ground"], groups["review"])

    cameras = (
        camera("CAMERA_A_StraightOnMainWindow", (0.0, -11.8, 2.05), (0.0, FRONT_Y + 0.15, 1.68), 50, groups["cameras"]),
        camera("CAMERA_B_ObliqueArcadeRing", (7.8, -10.0, 2.55), (1.05, FRONT_Y + 0.20, 1.85), 43, groups["cameras"]),
        camera("CAMERA_C_ThroughEntrance", (-2.18, -5.25, 1.68), (-0.15, 1.35, 1.25), 36, groups["cameras"]),
        camera("CAMERA_D_InteriorBackToShopfront", (0.20, 2.25, 1.68), (-0.35, FRONT_Y - 0.35, 1.52), 38, groups["cameras"]),
    )

    area_light("AP_Review_Key", (-6.5, -8.5, 9.0), (0.0, FRONT_Y, 1.8), 1450, 5.5, groups["lights"])
    area_light("AP_Review_ArcadeFill", (7.0, -4.5, 6.0), (RIGHT_X, -0.5, 1.6), 950, 5.0, groups["lights"])
    area_light("AP_Review_InteriorFill", (-0.4, 0.1, 3.15), (0.0, 1.2, 1.1), 620, 3.5, groups["lights"])
    area_light("AP_Review_RearFill", (0.0, 2.75, 2.65), (-0.4, -1.0, 1.1), 360, 2.8, groups["lights"])

    world = scene.world or bpy.data.worlds.new("AP_BlockoutWorld")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.045, 0.050, 0.058, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.55

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

    note = bpy.data.texts.new("ADVANCED_PHOTO_BLOCKOUT_NOTES")
    note.write(
        "FIRST PASS / REVIEW HOLD - GEOMETRY ONLY (03_Advanced_Photo.txt section 23)\n"
        f"Inferred envelope: {SHOP_W:.2f} m wide x {SHOP_D:.2f} m deep x {SHOP_H:.2f} m high.\n"
        "Main arcade frontage faces -Y; public return glazing faces +X; floor is Z=0.\n"
        "References establish a corner unit: entrance and hero display on the main face,\n"
        "secondary display down the arcade return, with a genuinely deep glazed display volume.\n"
        "The interior preserves a compact entrance-to-counter route and logical staff zone.\n"
        "Arcade floor/ceiling/opposite boundary are short connector context, not a full arcade.\n"
        "Deferred until approval: layered mouldings, lower decorative panels, fine cabinet\n"
        "frames, door furniture, ceiling detail, all anchors, signs, products and textures.\n"
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
        "AP_Fascia_Main",
        "AP_Fascia_Return",
        "AP_Door_FrameHinge",
        "AP_ExteriorGlass_Main",
        "AP_ExteriorGlass_Return",
        "AP_DisplayCabinet_Front_Base",
        "AP_DisplayCabinet_Return_Base",
        "AP_Counter",
        "AP_InteriorFloor",
        "AP_ArcadeRingLight_Blockout",
    )
    missing = [name for name in required if bpy.data.objects.get(name) is None]
    if missing:
        raise RuntimeError(f"Missing Advanced Photo blockout objects: {missing}")
    unnamed = [obj.name for obj in bpy.data.objects if obj.name.startswith(("Cube", "Cylinder", "Torus"))]
    if unnamed:
        raise RuntimeError(f"Unnamed primitives left in scene: {unnamed}")
    bad_scale = [
        obj.name
        for obj in bpy.data.objects
        if obj.type == "MESH" and any(abs(value - 1.0) > 1e-5 for value in obj.scale)
    ]
    if bad_scale:
        raise RuntimeError(f"Unapplied mesh scales: {bad_scale}")
    if ENTRANCE_RIGHT - ENTRANCE_LEFT < 1.0:
        raise RuntimeError("Advanced Photo entrance is narrower than the one-metre gameplay minimum")
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    triangles = sum(sum(max(0, len(poly.vertices) - 2) for poly in obj.data.polygons) for obj in meshes)
    print(f"Validation: {len(meshes)} mesh objects, approximately {triangles} triangles")
    print(f"Validation: shop envelope {SHOP_W:.2f} x {SHOP_D:.2f} x {SHOP_H:.2f} m, main frontage faces -Y")
    print(f"Validation: clear entrance width {ENTRANCE_RIGHT - ENTRANCE_LEFT:.2f} m")


def export_runtime_glb():
    """Export blockout architecture; omit cameras, lights and review staging."""
    GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
    excluded_collections = {
        "AP_BlockoutReviewOnly",
        "AP_BlockoutCameras",
        "AP_BlockoutLights",
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
        "view-a-straight-on-main-window.png",
        "view-b-oblique-arcade-ring.png",
        "view-c-through-entrance.png",
        "view-d-interior-looking-out.png",
    )
    scene = bpy.context.scene
    for camera_obj, filename in zip(cameras, names):
        scene.camera = camera_obj
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
