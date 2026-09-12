"""Create the Village Books geometry-only blockout and five clay renders.

This file implements the first-pass review hold requested by
references/architecture/village-books/10_Village_Books.txt section 27.  It
models only the documented storefront rhythm, 131A door, basic shop interior
shell and a conservative inferred upper mass.  Fine frames, door furniture,
display furniture, decal surfaces and interaction anchors belong to the
post-approval geometry pass.

One Blender unit is one metre, Z is up, and the Oldham Street frontage faces
-Y.  Dimensions are photographic estimates rather than survey measurements.
"""

from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
BLEND_PATH = ROOT / "blender" / "source" / "village_books_blockout.blend"
GLB_PATH = ROOT / "public" / "assets" / "models" / "village-books-blockout.glb"
RENDER_DIR = ROOT / "renders" / "village-books-blockout"

# Inferred real-world envelope (metres).  The photographed ground floor is the
# authoritative part; upper-storey values are intentionally restrained.
BUILDING_W = 7.80
BUILDING_D = 8.00
FRONT_Y = -4.00
BACK_Y = 4.00
GROUND_H = 3.90
UPPER_1_H = 2.95
UPPER_2_H = 2.95
PARAPET_H = 0.40
TOTAL_H = GROUND_H + UPPER_1_H + UPPER_2_H + PARAPET_H

SIDE_DOOR_LEFT = -3.72
SIDE_DOOR_RIGHT = -2.38
SHOP_LEFT = -2.26
SHOP_RIGHT = 3.72
FASCIA_BOTTOM = 3.18
FASCIA_TOP = 3.84
TRANSOM_BOTTOM = 2.72
TRANSOM_TOP = 3.12
PLINTH_TOP = 0.18


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
            transmission.default_value = 0.08
        if hasattr(result, "surface_render_method"):
            result.surface_render_method = "DITHERED"
        else:
            result.blend_method = "BLEND"
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
    data.clip_end = 160
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


def upper_window(name, x, z_bottom, width, height, mats, groups):
    """A conservative recessed rectangular opening in the inferred facade."""
    recess_y = FRONT_Y + 0.10
    box(
        f"{name}_Glass",
        (width, 0.05, height),
        (x, recess_y, z_bottom + height / 2),
        mats["glass"],
        groups["glass"],
    )
    frame_t = 0.10
    for suffix, frame_x in (("Left", x - width / 2), ("Right", x + width / 2)):
        box(
            f"{name}_Frame_{suffix}",
            (frame_t, 0.15, height + frame_t),
            (frame_x, FRONT_Y + 0.025, z_bottom + height / 2),
            mats["frame"],
            groups["upper"],
        )
    for suffix, frame_z in (("Top", z_bottom + height), ("Bottom", z_bottom)):
        box(
            f"{name}_Frame_{suffix}",
            (width + frame_t, 0.15, frame_t),
            (x, FRONT_Y + 0.025, frame_z),
            mats["frame"],
            groups["upper"],
        )
    box(
        f"{name}_CentreMullion",
        (0.08, 0.15, height),
        (x, FRONT_Y + 0.025, z_bottom + height / 2),
        mats["frame"],
        groups["upper"],
    )
    box(
        f"{name}_Sill",
        (width + 0.20, 0.24, 0.09),
        (x, FRONT_Y - 0.04, z_bottom - 0.05),
        mats["upper"],
        groups["upper"],
    )


def build_scene():
    clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"

    master = collection("VILLAGE_BOOKS_MASTER")
    groups = {
        "shell": collection("VB_BuildingShell", master),
        "upper": collection("VB_UpperFacade", master),
        "shopfront": collection("VB_Shopfront", master),
        "glass": collection("VB_MainGlass", master),
        "entrance": collection("VB_Entrance", master),
        "side_door": collection("VB_131A_Door", master),
        "interior": collection("VB_InteriorShell", master),
        "review": collection("VB_BlockoutReviewOnly", master),
        "cameras": collection("VB_BlockoutCameras", master),
        "lights": collection("VB_BlockoutLights", master),
    }

    mats = {
        "dark": material("MAT_VB_DarkFacade_PLACEHOLDER", (0.055, 0.060, 0.070), 0.58),
        "glass": material("MAT_VB_Glass_PLACEHOLDER", (0.10, 0.14, 0.16), 0.20, alpha=0.24),
        "upper": material("MAT_VB_UpperWall_PLACEHOLDER", (0.70, 0.69, 0.65), 0.94),
        "frame": material("MAT_VB_WindowFrame_PLACEHOLDER", (0.075, 0.080, 0.090), 0.50, 0.18),
        "interior": material("MAT_VB_InteriorWall_PLACEHOLDER", (0.64, 0.63, 0.59), 0.90),
        "floor": material("MAT_VB_Floor_PLACEHOLDER", (0.19, 0.19, 0.19), 0.76),
        "wood": material("MAT_VB_Wood_PLACEHOLDER", (0.39, 0.27, 0.17), 0.82),
        "opaque_glass": material("MAT_VB_131A_Glass_PLACEHOLDER", (0.47, 0.50, 0.51), 0.52),
        "review_ground": material("MAT_VB_ReviewGround", (0.28, 0.285, 0.28), 0.95),
        "review_context": material("MAT_VB_ReviewCityContext", (0.20, 0.20, 0.21), 0.86),
    }

    # Shell: close the asset at its rear and sides but leave the shopfront and
    # upper windows as real openings rather than placing trim over a solid box.
    box("VB_BackWall", (BUILDING_W, 0.20, TOTAL_H), (0.0, BACK_Y - 0.10, TOTAL_H / 2), mats["upper"], groups["shell"])
    box("VB_LeftReturn", (0.18, BUILDING_D, TOTAL_H), (-BUILDING_W / 2 + 0.09, 0.0, TOTAL_H / 2), mats["upper"], groups["shell"])
    box("VB_RightPartyWall", (0.18, BUILDING_D, TOTAL_H), (BUILDING_W / 2 - 0.09, 0.0, TOTAL_H / 2), mats["upper"], groups["shell"])
    box("VB_Roof", (BUILDING_W, BUILDING_D, 0.18), (0.0, 0.0, TOTAL_H - 0.09), mats["upper"], groups["shell"])

    # Ground-floor backing above the shopfront, plus the left and right wall
    # strips needed to make a clean party-wall boundary.
    box("VB_GroundHeadWall", (BUILDING_W - 0.18, 0.22, GROUND_H - FASCIA_TOP), (0.0, FRONT_Y + 0.11, (FASCIA_TOP + GROUND_H) / 2), mats["upper"], groups["shell"])
    box("VB_GroundLeftEdge", (0.18, 0.24, FASCIA_TOP), (-BUILDING_W / 2 + 0.09, FRONT_Y + 0.12, FASCIA_TOP / 2), mats["upper"], groups["shell"])
    box("VB_GroundRightEdge", (0.18, 0.24, FASCIA_TOP), (BUILDING_W / 2 - 0.09, FRONT_Y + 0.12, FASCIA_TOP / 2), mats["dark"], groups["shopfront"])

    # Restrained two-storey upper facade.  The broad surrounding wall planes
    # carry the mass; the six simple windows repeat the visible street rhythm.
    upper_start = GROUND_H
    floor_1_top = upper_start + UPPER_1_H
    floor_2_top = floor_1_top + UPPER_2_H
    box("VB_UpperSpandrel_00", (BUILDING_W - 0.18, 0.24, 0.46), (0.0, FRONT_Y + 0.12, upper_start + 0.23), mats["upper"], groups["upper"])
    box("VB_UpperSpandrel_01", (BUILDING_W - 0.18, 0.24, 0.84), (0.0, FRONT_Y + 0.12, floor_1_top - 0.42), mats["upper"], groups["upper"])
    box("VB_UpperSpandrel_02", (BUILDING_W - 0.18, 0.24, 0.84), (0.0, FRONT_Y + 0.12, floor_2_top - 0.42), mats["upper"], groups["upper"])
    box("VB_Parapet", (BUILDING_W + 0.08, 0.34, PARAPET_H), (0.0, FRONT_Y + 0.17, TOTAL_H - PARAPET_H / 2), mats["upper"], groups["upper"])

    window_centres = (-1.95, 1.95)
    window_w = 1.75
    window_h = 1.72
    # Piers close the facade around two broad window bays.  Two openings per
    # floor are the least elaborate continuation supported by the wider
    # photograph; adding a third would overstate the uncertain upper evidence.
    pier_spans = ((-3.81, -2.825), (-1.075, 1.075), (2.825, 3.81))
    for floor_index, z_bottom in enumerate((upper_start + 0.50, floor_1_top + 0.50), start=1):
        window_top = z_bottom + window_h
        for pier_index, (left, right) in enumerate(pier_spans, start=1):
            box(
                f"VB_Upper_{floor_index}_Pier_{pier_index}",
                (right - left, 0.24, window_top - z_bottom),
                ((left + right) / 2, FRONT_Y + 0.12, (z_bottom + window_top) / 2),
                mats["upper"],
                groups["upper"],
            )
        for bay_index, x in enumerate(window_centres, start=1):
            upper_window(f"VB_UpperWindow_{floor_index}_{bay_index}", x, z_bottom, window_w, window_h, mats, groups)

    # Broad projected fascia, with blank inset planes where the Village and
    # address lettering will be applied only after blockout approval.
    fascia_depth = 0.24
    box("VB_Fascia", (BUILDING_W - 0.18, fascia_depth, FASCIA_TOP - FASCIA_BOTTOM), (0.0, FRONT_Y - fascia_depth / 2, (FASCIA_BOTTOM + FASCIA_TOP) / 2), mats["dark"], groups["shopfront"])
    box("VB_Fascia_LeftReturn", (0.16, 0.30, FASCIA_TOP - FASCIA_BOTTOM), (-BUILDING_W / 2 + 0.17, FRONT_Y, (FASCIA_BOTTOM + FASCIA_TOP) / 2), mats["dark"], groups["shopfront"])
    box("VB_Fascia_RightReturn", (0.16, 0.30, FASCIA_TOP - FASCIA_BOTTOM), (BUILDING_W / 2 - 0.17, FRONT_Y, (FASCIA_BOTTOM + FASCIA_TOP) / 2), mats["dark"], groups["shopfront"])

    # 131A side door: distinct from the shop entrance and intentionally plain
    # at blockout stage.  Detailed handle/letterbox geometry is deferred.
    side_centre = (SIDE_DOOR_LEFT + SIDE_DOOR_RIGHT) / 2
    side_w = SIDE_DOOR_RIGHT - SIDE_DOOR_LEFT
    box("VB_131A_LeftJamb", (0.14, 0.28, FASCIA_BOTTOM), (SIDE_DOOR_LEFT, FRONT_Y + 0.14, FASCIA_BOTTOM / 2), mats["dark"], groups["side_door"])
    box("VB_131A_RightJamb", (0.14, 0.28, FASCIA_BOTTOM), (SIDE_DOOR_RIGHT, FRONT_Y + 0.14, FASCIA_BOTTOM / 2), mats["dark"], groups["side_door"])
    box("VB_131A_Head", (side_w + 0.14, 0.28, 0.14), (side_centre, FRONT_Y + 0.14, 2.82), mats["dark"], groups["side_door"])
    box("VB_131A_Door", (side_w - 0.14, 0.07, 2.62), (side_centre, FRONT_Y + 0.19, 1.31), mats["frame"], groups["side_door"])
    box("VB_131A_Glass", (side_w - 0.32, 0.035, 2.18), (side_centre, FRONT_Y + 0.145, 1.45), mats["opaque_glass"], groups["side_door"])
    box("VB_131A_Threshold", (side_w + 0.08, 0.34, 0.06), (side_centre, FRONT_Y + 0.17, 0.03), mats["dark"], groups["side_door"])

    # Shopfront frame and real panes.  The entrance is slightly right of
    # centre, as in the direct photograph, between unequal display windows.
    left_display_right = -0.18
    entrance_right = 1.10
    frame_t = 0.13
    for name, x in (
        ("VB_ShopfrontPost_Left", SHOP_LEFT),
        ("VB_ShopfrontPost_LeftDisplay", left_display_right),
        ("VB_ShopfrontPost_EntranceRight", entrance_right),
        ("VB_ShopfrontPost_Right", SHOP_RIGHT),
    ):
        box(name, (frame_t, 0.26, FASCIA_BOTTOM), (x, FRONT_Y + 0.13, FASCIA_BOTTOM / 2), mats["frame"], groups["shopfront"])
    box("VB_ShopfrontHead", (SHOP_RIGHT - SHOP_LEFT, 0.26, 0.13), ((SHOP_RIGHT + SHOP_LEFT) / 2, FRONT_Y + 0.13, FASCIA_BOTTOM - 0.065), mats["frame"], groups["shopfront"])
    box("VB_ShopfrontPlinth", (SHOP_RIGHT - SHOP_LEFT, 0.24, PLINTH_TOP), ((SHOP_RIGHT + SHOP_LEFT) / 2, FRONT_Y + 0.12, PLINTH_TOP / 2), mats["dark"], groups["shopfront"])
    box("VB_TransomRail", (SHOP_RIGHT - SHOP_LEFT, 0.24, 0.10), ((SHOP_RIGHT + SHOP_LEFT) / 2, FRONT_Y + 0.12, TRANSOM_BOTTOM), mats["frame"], groups["shopfront"])

    glass_y = FRONT_Y + 0.18
    lower_glass_h = TRANSOM_BOTTOM - PLINTH_TOP - 0.10
    lower_glass_z = PLINTH_TOP + 0.05 + lower_glass_h / 2
    left_glass_w = left_display_right - SHOP_LEFT - frame_t
    right_glass_w = SHOP_RIGHT - entrance_right - frame_t
    box("VB_Glass_Left", (left_glass_w, 0.035, lower_glass_h), ((SHOP_LEFT + left_display_right) / 2, glass_y, lower_glass_z), mats["glass"], groups["glass"])
    box("VB_Glass_Right", (right_glass_w, 0.035, lower_glass_h), ((entrance_right + SHOP_RIGHT) / 2, glass_y, lower_glass_z), mats["glass"], groups["glass"])

    transom_h = TRANSOM_TOP - TRANSOM_BOTTOM
    for index, (left, right) in enumerate(((SHOP_LEFT, left_display_right), (left_display_right, entrance_right), (entrance_right, SHOP_RIGHT)), start=1):
        box(
            f"VB_Glass_Transom_{index}",
            (right - left - frame_t, 0.035, transom_h - 0.08),
            ((left + right) / 2, glass_y, (TRANSOM_BOTTOM + TRANSOM_TOP) / 2),
            mats["glass"],
            groups["glass"],
        )

    entrance_centre = (left_display_right + entrance_right) / 2
    entrance_w = entrance_right - left_display_right - 0.12
    door_bottom = PLINTH_TOP
    door_top = TRANSOM_BOTTOM - 0.05
    door_frame_t = 0.10
    box("VB_EntranceDoor", (entrance_w, 0.065, door_frame_t), (entrance_centre, FRONT_Y + 0.11, door_bottom + door_frame_t / 2), mats["frame"], groups["entrance"])
    box("VB_EntranceDoor_Top", (entrance_w, 0.065, door_frame_t), (entrance_centre, FRONT_Y + 0.11, door_top - door_frame_t / 2), mats["frame"], groups["entrance"])
    box("VB_EntranceDoor_Left", (door_frame_t, 0.065, door_top - door_bottom), (entrance_centre - entrance_w / 2 + door_frame_t / 2, FRONT_Y + 0.11, (door_bottom + door_top) / 2), mats["frame"], groups["entrance"])
    box("VB_EntranceDoor_Right", (door_frame_t, 0.065, door_top - door_bottom), (entrance_centre + entrance_w / 2 - door_frame_t / 2, FRONT_Y + 0.11, (door_bottom + door_top) / 2), mats["frame"], groups["entrance"])
    box("VB_Glass_Entrance", (entrance_w - 0.18, 0.035, TRANSOM_BOTTOM - PLINTH_TOP - 0.28), (entrance_centre, FRONT_Y + 0.07, (PLINTH_TOP + TRANSOM_BOTTOM + 0.02) / 2), mats["glass"], groups["entrance"])
    box("VB_EntranceThreshold", (entrance_w + 0.04, 0.42, 0.055), (entrance_centre, FRONT_Y + 0.20, 0.0275), mats["dark"], groups["entrance"])

    # Simplified, genuinely visible interior shell.  Furniture is reserved for
    # the approved second pass, leaving a clear player circulation route.
    interior_left = SHOP_LEFT + 0.16
    interior_right = SHOP_RIGHT - 0.16
    interior_w = interior_right - interior_left
    interior_centre = (interior_left + interior_right) / 2
    interior_front = FRONT_Y + 0.30
    interior_back = BACK_Y - 0.36
    interior_depth = interior_back - interior_front
    box("VB_InteriorFloor", (interior_w, interior_depth, 0.08), (interior_centre, (interior_front + interior_back) / 2, 0.04), mats["floor"], groups["interior"])
    box("VB_InteriorCeiling", (interior_w, interior_depth, 0.10), (interior_centre, (interior_front + interior_back) / 2, 3.03), mats["interior"], groups["interior"])
    box("VB_InteriorLeftWall", (0.10, interior_depth, 3.00), (interior_left + 0.05, (interior_front + interior_back) / 2, 1.50), mats["interior"], groups["interior"])
    box("VB_InteriorRightWall", (0.10, interior_depth, 3.00), (interior_right - 0.05, (interior_front + interior_back) / 2, 1.50), mats["interior"], groups["interior"])
    box("VB_InteriorRearWall", (interior_w, 0.10, 3.00), (interior_centre, interior_back - 0.05, 1.50), mats["interior"], groups["interior"])

    # Review-only ground and a deliberately crude adjoining City mass.  The
    # latter communicates street line, party wall and relative height without
    # inventing or exporting the pub's ornament.
    review = groups["review"]
    box("VB_Review_Ground", (30.0, 25.0, 0.10), (2.0, 1.5, -0.05), mats["review_ground"], review)
    city_w = 5.70
    city_h = 11.35
    box("VB_Review_CityContextMass", (city_w, BUILDING_D, city_h), (BUILDING_W / 2 + city_w / 2 + 0.05, 0.0, city_h / 2), mats["review_context"], review)

    cameras = (
        camera("CAMERA_A_StraightOnShop", (0.0, -13.8, 2.25), (0.0, FRONT_Y, 2.15), 48, groups["cameras"]),
        camera("CAMERA_B_LeftThreeQuarter", (-10.5, -11.0, 3.25), (-0.15, FRONT_Y + 0.25, 2.40), 44, groups["cameras"]),
        camera("CAMERA_C_RightThreeQuarter_CityBoundary", (7.5, -20.0, 3.35), (1.70, FRONT_Y + 0.15, 3.35), 52, groups["cameras"]),
        camera("CAMERA_D_WideFullBuilding", (-13.5, -22.0, 5.45), (0.90, FRONT_Y + 0.45, 5.05), 42, groups["cameras"]),
        camera("CAMERA_E_PlayerHeightThroughWindow", (-1.35, -7.15, 1.68), (0.35, 0.55, 1.45), 35, groups["cameras"]),
    )

    area_light("VB_Review_Key", (-8.0, -11.0, 13.0), (0.0, FRONT_Y, 4.4), 1850, 7.0, groups["lights"])
    area_light("VB_Review_Fill", (10.0, -7.0, 8.0), (0.8, FRONT_Y, 3.2), 1050, 6.0, groups["lights"])
    area_light("VB_Review_InteriorFill", (0.4, -0.4, 2.75), (0.2, 1.2, 1.25), 120, 2.4, groups["lights"])

    world = scene.world or bpy.data.worlds.new("VB_BlockoutWorld")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.055, 0.062, 0.070, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.48

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

    note = bpy.data.texts.new("VILLAGE_BOOKS_BLOCKOUT_NOTES")
    note.write(
        "FIRST PASS / REVIEW HOLD - GEOMETRY ONLY (see 10_Village_Books.txt section 27)\n"
        f"Inferred envelope: {BUILDING_W:.2f} m wide x {BUILDING_D:.2f} m deep x {TOTAL_H:.2f} m to parapet.\n"
        "Oldham Street frontage faces -Y; ground is Z=0; one unit equals one metre.\n"
        "Ground floor follows the direct frontal and oblique photographs: distinct 131A door,\n"
        "projected fascia, unequal display panes and a slightly right-of-centre shop entrance.\n"
        "Upper two storeys are conservative inference: plain wall planes and rectangular windows only.\n"
        "The simple adjoining City mass and ground plane are review-only and excluded from export.\n"
        "Deferred until approval: fine metal frames, door furniture, display plinths, shelves,\n"
        "counter, signage/decal surfaces, A-frame prop, fixtures and interaction anchors.\n"
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
        "VB_Fascia",
        "VB_Glass_Left",
        "VB_Glass_Entrance",
        "VB_Glass_Right",
        "VB_Glass_Transom_1",
        "VB_EntranceDoor",
        "VB_131A_Door",
        "VB_InteriorFloor",
        "VB_UpperWindow_1_1_Glass",
        "VB_Parapet",
    )
    missing = [name for name in required if bpy.data.objects.get(name) is None]
    if missing:
        raise RuntimeError(f"Missing Village Books blockout objects: {missing}")
    unnamed = [obj.name for obj in bpy.data.objects if obj.name.startswith(("Cube", "Cylinder"))]
    if unnamed:
        raise RuntimeError(f"Unnamed primitives left in scene: {unnamed}")
    bad_scale = [obj.name for obj in bpy.data.objects if obj.type == "MESH" and any(abs(value - 1.0) > 1e-5 for value in obj.scale)]
    if bad_scale:
        raise RuntimeError(f"Unapplied mesh scales: {bad_scale}")
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    triangles = sum(sum(max(0, len(poly.vertices) - 2) for poly in obj.data.polygons) for obj in meshes)
    print(f"Validation: {len(meshes)} mesh objects, approximately {triangles} triangles")
    print(f"Validation: envelope {BUILDING_W:.2f} x {BUILDING_D:.2f} x {TOTAL_H:.2f} m, frontage faces -Y")


def export_runtime_glb():
    """Export blockout architecture only; omit all review staging."""
    GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
    excluded_collections = {
        "VB_BlockoutReviewOnly",
        "VB_BlockoutCameras",
        "VB_BlockoutLights",
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
        "view-a-straight-on-shop.png",
        "view-b-left-three-quarter.png",
        "view-c-right-three-quarter-city-boundary.png",
        "view-d-wide-full-building.png",
        "view-e-player-height-through-window.png",
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
