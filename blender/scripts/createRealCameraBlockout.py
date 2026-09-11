"""Create Real Camera's geometry-only first-pass blockout and five clay renders.

Reference-derived but deliberately conservative: this file stops at the review
hold requested by references/architecture/real-camera/13_Real_Camera.txt §42.
One Blender unit is one metre, Z is up, and the Dale Street frontage faces -Y.
Inferred, not surveyed: proportions are estimated from the supplied street
photography (shopfront widths, storey counts, a ~2.0 m entrance door, and the
1.78 m player), the same way the Renee and Nice Things blockouts were built.
"""

from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
BLEND_PATH = ROOT / "blender" / "source" / "real_camera_blockout.blend"
GLB_PATH = ROOT / "public" / "assets" / "models" / "real-camera-blockout.glb"
RENDER_DIR = ROOT / "renders" / "real-camera-blockout"


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
        bsdf.inputs["Transmission Weight"].default_value = 0.08
        result.surface_render_method = "DITHERED"
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
    if rotation_z:
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


def cylinder(name, radius, depth, location, mat, target, rotation=(0.0, 0.0, 0.0), vertices=20):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=depth, location=location, vertices=vertices
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    obj.rotation_euler = rotation
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    if mat:
        obj.data.materials.append(mat)
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
    data.clip_end = 200
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


def arched_window(name, x, z_base, width, height, front_y, mats, target):
    """Recessed rectangular pane with a genuine rounded arch head (§25)."""
    depth = 0.30
    box(f"{name}_Recess", (width, depth, height), (x, front_y - depth / 2, z_base + height / 2), mats["glass"], target)
    box(f"{name}_Reveal_L", (0.12, depth + 0.06, height), (x - width / 2, front_y - depth / 2, z_base + height / 2), mats["frame"], target)
    box(f"{name}_Reveal_R", (0.12, depth + 0.06, height), (x + width / 2, front_y - depth / 2, z_base + height / 2), mats["frame"], target)
    cylinder(
        f"{name}_ArchHead",
        radius=width / 2,
        depth=depth + 0.06,
        location=(x, front_y - depth / 2, z_base + height),
        mat=mats["frame"],
        target=target,
        rotation=(1.5708, 0.0, 0.0),
        vertices=16,
    )
    box(f"{name}_Sill", (width + 0.24, 0.24, 0.10), (x, front_y + 0.10, z_base - 0.05), mats["stone"], target)


def rect_window(name, x, z_base, width, height, front_y, mats, target):
    depth = 0.26
    box(f"{name}_Recess", (width, depth, height), (x, front_y - depth / 2, z_base + height / 2), mats["glass"], target)
    for suffix, dx in (("L", -width / 2), ("R", width / 2)):
        box(f"{name}_Frame_{suffix}", (0.11, depth + 0.06, height + 0.10), (x + dx, front_y - depth / 2, z_base + height / 2), mats["frame"], target)
    for suffix, dz in (("Top", height / 2), ("Bottom", -height / 2)):
        box(f"{name}_Frame_{suffix}", (width + 0.11, depth + 0.06, 0.11), (x, front_y - depth / 2, z_base + height / 2 + dz), mats["frame"], target)
    box(f"{name}_Sill", (width + 0.26, 0.24, 0.10), (x, front_y + 0.10, z_base - 0.05), mats["stone"], target)


def pilaster(name, x, z_base, height, front_y, mats, target):
    box(f"{name}_Shaft", (0.62, 0.34, height), (x, front_y - 0.17, z_base + height / 2), mats["stone"], target)
    box(f"{name}_Base", (0.78, 0.42, 0.30), (x, front_y - 0.21, z_base + 0.15), mats["stone"], target)
    box(f"{name}_Capital", (0.78, 0.42, 0.26), (x, front_y - 0.21, z_base + height - 0.13), mats["stone"], target)


def string_course(name, z, front_y, width, mats, target):
    box(f"{name}_Band", (width, 0.34, 0.24), (0.0, front_y - 0.17, z), mats["stone"], target)
    box(f"{name}_Step", (width, 0.22, 0.10), (0.0, front_y - 0.11, z + 0.17), mats["stone"], target)


def stairs(name, x_center, y_front, y_back, z_top, width, step_count, mats, target):
    step_h = z_top / step_count
    step_d = (y_front - y_back) / step_count
    for index in range(step_count):
        z = step_h * (index + 0.5)
        y = y_front - step_d * (index + 0.5)
        depth_run = step_d * (step_count - index)
        box(
            f"{name}_Step_{index:02d}",
            (width, depth_run, step_h),
            (x_center, y, z),
            mats["stone"],
            target,
        )


def build_scene():
    clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"

    master = collection("REAL_CAMERA_MASTER")
    groups = {
        "shell": collection("RC_BuildingShell", master),
        "ground": collection("RC_GroundFloorArchitecture", master),
        "upper": collection("RC_UpperFacade", master),
        "ornament": collection("RC_Ornament", master),
        "windows": collection("RC_Windows", master),
        "mainshop": collection("RC_MainShop", master),
        "gallery": collection("RC_GalleryEntrance", master),
        "sign": collection("RC_HangingSign", master),
        "clock": collection("RC_CornerClock", master),
        "glass": collection("RC_Glass", master),
        "interior": collection("RC_InteriorShell", master),
        "anchors": collection("RC_InteractionAnchors", master),
        "review": collection("RC_BlockoutReviewOnly", master),
        "cameras": collection("RC_BlockoutCameras", master),
        "lights": collection("RC_BlockoutLights", master),
    }

    mats = {
        "redstone": material("MAT_RC_RedStone_PLACEHOLDER", (0.48, 0.22, 0.16), 0.92),
        "darktrim": material("MAT_RC_DarkPaintedTrim_PLACEHOLDER", (0.05, 0.05, 0.055), 0.55),
        "frame": material("MAT_RC_WindowFrames_PLACEHOLDER", (0.30, 0.22, 0.17), 0.75),
        "glass": material("MAT_RC_Glass_PLACEHOLDER", (0.10, 0.13, 0.15), 0.22, alpha=0.24),
        "metal": material("MAT_RC_Metalwork_PLACEHOLDER", (0.15, 0.15, 0.16), 0.40, 0.35),
        "shopfront": material("MAT_RC_Shopfront_PLACEHOLDER", (0.62, 0.06, 0.07), 0.55),
        "signage": material("MAT_RC_SignageSurfaces_PLACEHOLDER", (0.85, 0.83, 0.78), 0.60),
        "stone": material("MAT_RC_MouldedStone_PLACEHOLDER", (0.55, 0.30, 0.22), 0.88),
        "shutter": material("MAT_RC_Shutter_PLACEHOLDER", (0.62, 0.62, 0.63), 0.50, 0.30),
        "ground_review": material("MAT_RC_ReviewGround", (0.27, 0.275, 0.27)),
    }

    # Coherent inferred envelope: 14.0 m Dale Street frontage, storeys from the
    # street photography (ground shopfronts, three upper floors, cornice/parapet).
    width = 14.0
    front_y, back_y = -5.0, 5.0
    ground_h, floor1_h, floor2_h, floor3_h, cornice_h = 4.20, 3.30, 3.30, 2.60, 0.80
    z_floor1 = ground_h
    z_floor2 = z_floor1 + floor1_h
    z_floor3 = z_floor2 + floor2_h
    z_cornice = z_floor3 + floor3_h
    total_h = z_cornice + cornice_h

    corner_x = -7.0

    # --- Overall shell mass -------------------------------------------------
    box("RC_MainVolume", (width, back_y - front_y, total_h), (0.0, (front_y + back_y) / 2, total_h / 2), mats["redstone"], groups["shell"])
    box("RC_RoofCap", (width + 0.20, back_y - front_y + 0.20, 0.20), (0.0, (front_y + back_y) / 2, total_h + 0.10), mats["darktrim"], groups["shell"])

    # Rounded/chamfered corner mass wrapping onto the Lever Street return (§18).
    cylinder(
        "RC_CornerMass",
        radius=1.35,
        depth=total_h,
        location=(corner_x - 1.0, front_y - 0.4, total_h / 2),
        mat=mats["redstone"],
        target=groups["shell"],
        rotation=(0.0, 0.0, 0.0),
        vertices=24,
    )
    box(
        "RC_CornerReturnWing",
        (3.6, 7.0, total_h),
        (corner_x - 3.2, front_y + 3.1, total_h / 2),
        mats["redstone"],
        groups["shell"],
    )

    # --- Ground-floor rhythm: corner pier | Gallery entrance | pier | Real
    # Camera shop | pier | adjacent shopfront | corner pier (§7). ------------
    pier_positions = (-6.65, -2.70, 2.95, 6.65)
    for index, x in enumerate(pier_positions):
        pilaster(f"RC_Pilaster_{index:02d}", x, 0.0, ground_h, front_y, mats, groups["ornament"])

    # Ground-floor stone bases/plinth (§20).
    box("RC_GroundPlinth", (width - 0.6, 0.50, 0.30), (0.0, front_y - 0.15, 0.15), mats["stone"], groups["ground"])

    # --- Gallery entrance: recessed opening, stair flight, doors (§12,13). --
    gallery_x, gallery_w = -4.5, 3.0
    gallery_recess_y = front_y + 1.30
    box("RC_GalleryEntrance_Reveal_L", (0.20, 1.30, ground_h - 0.20), (gallery_x - gallery_w / 2, front_y + 0.65, ground_h / 2), mats["stone"], groups["gallery"])
    box("RC_GalleryEntrance_Reveal_R", (0.20, 1.30, ground_h - 0.20), (gallery_x + gallery_w / 2, front_y + 0.65, ground_h / 2), mats["stone"], groups["gallery"])
    box("RC_GalleryEntrance_Head", (gallery_w + 0.20, 1.30, 0.24), (gallery_x, front_y + 0.65, ground_h - 0.22), mats["stone"], groups["gallery"])
    box("RC_GallerySignSurface", (gallery_w - 0.30, 0.05, 0.55), (gallery_x, front_y + 0.05, ground_h - 0.55), mats["signage"], groups["gallery"])
    stairs("RC_GalleryStairs", gallery_x, front_y + 1.25, gallery_recess_y, 0.55, gallery_w - 0.6, 5, mats, groups["gallery"])
    box("RC_GalleryLanding", (gallery_w - 0.5, 0.60, 0.10), (gallery_x, gallery_recess_y - 0.20, 0.55), mats["stone"], groups["gallery"])
    box("RC_GalleryDoor_L", (gallery_w / 2 - 0.15, 0.06, 2.05), (gallery_x - gallery_w / 4, gallery_recess_y + 0.10, 1.60), mats["glass"], groups["gallery"])
    box("RC_GalleryDoor_R", (gallery_w / 2 - 0.15, 0.06, 2.05), (gallery_x + gallery_w / 4, gallery_recess_y + 0.10, 1.60), mats["glass"], groups["gallery"])
    box("RC_GalleryDoorFrame_Mid", (0.10, 0.14, 2.10), (gallery_x, gallery_recess_y + 0.06, 1.65), mats["frame"], groups["gallery"])
    box("RC_GalleryCeiling", (gallery_w, 1.30, 0.10), (gallery_x, front_y + 0.65, ground_h - 0.15), mats["stone"], groups["gallery"])

    # --- Real Camera main shop: hero shopfront (§8,9,10,11). ----------------
    shop_x, shop_w = 0.10, 5.00
    shop_recess_y = front_y + 0.55
    box("RC_MainShop_Reveal_L", (0.22, 0.55, ground_h - 0.20), (shop_x - shop_w / 2, front_y + 0.275, ground_h / 2), mats["stone"], groups["mainshop"])
    box("RC_MainShop_Reveal_R", (0.22, 0.55, ground_h - 0.20), (shop_x + shop_w / 2, front_y + 0.275, ground_h / 2), mats["stone"], groups["mainshop"])
    box("RC_MainShop_Threshold", (shop_w, 0.60, 0.10), (shop_x, front_y + 0.275, 0.05), mats["stone"], groups["mainshop"])

    # Upper display window with recessed glazing (§10, §35).
    window_h = 1.85
    box("RC_MainWindowFrame", (shop_w - 0.30, 0.10, window_h + 0.16), (shop_x, shop_recess_y, 2.55 + window_h / 2), mats["frame"], groups["mainshop"])
    box("RC_MainShopGlass", (shop_w - 0.50, 0.05, window_h), (shop_x, shop_recess_y + 0.03, 2.55 + window_h / 2), mats["glass"], groups["glass"])

    # Red curved awning: hero brand surface (§9). Bevel suggests the curved face.
    awning = box("RC_RedAwning", (shop_w + 0.60, 0.90, 0.55), (shop_x, front_y + 0.10, 4.42), mats["shopfront"], groups["mainshop"], bevel=0.14)
    box("RC_AwningBrandSurface", (shop_w + 0.30, 0.04, 0.34), (shop_x, front_y - 0.32, 4.42), mats["signage"], groups["mainshop"])
    box("RC_SignageAnchor", (shop_w + 0.60, 0.12, 0.10), (shop_x, front_y + 0.30, 4.10), mats["darktrim"], groups["mainshop"])

    # Lower shutter/glazing zone below the awning (§11, matches the open-shutter
    # references showing shop stock through the lower glazing).
    box("RC_LowerShutter_Recess", (shop_w - 0.30, 0.14, 2.40), (shop_x, front_y + 0.30, 1.20), mats["shutter"], groups["mainshop"])
    box("RC_LowerShutter_Frame", (shop_w - 0.10, 0.18, 2.55), (shop_x, front_y + 0.20, 1.20), mats["frame"], groups["mainshop"])

    # --- Adjacent shopfront continuation with roller shutter (§7, §11). -----
    adj_x, adj_w = 4.80, 3.00
    box("RC_AdjacentShopfront_Reveal_L", (0.18, 0.45, ground_h - 0.20), (adj_x - adj_w / 2, front_y + 0.225, ground_h / 2), mats["stone"], groups["ground"])
    box("RC_AdjacentShopfront_Reveal_R", (0.18, 0.45, ground_h - 0.20), (adj_x + adj_w / 2, front_y + 0.225, ground_h / 2), mats["stone"], groups["ground"])
    box("RC_AdjacentShopfront_SignBand", (adj_w, 0.10, 0.55), (adj_x, front_y + 0.10, ground_h - 0.55), mats["signage"], groups["ground"])
    box("RC_AdjacentShutter_Recess", (adj_w - 0.20, 0.14, 2.65), (adj_x, front_y + 0.25, 1.35), mats["shutter"], groups["ground"])
    box("RC_AdjacentShutter_Frame", (adj_w, 0.18, 2.80), (adj_x, front_y + 0.15, 1.35), mats["frame"], groups["ground"])

    # --- Upper facade: string courses + arched/rect windows (§22-§26). ------
    string_course("RC_StringCourse_Floor1", z_floor1, front_y, width, mats, groups["ornament"])
    string_course("RC_StringCourse_Floor2", z_floor2, front_y, width, mats, groups["ornament"])
    string_course("RC_StringCourse_Floor3", z_floor3, front_y, width, mats, groups["ornament"])

    bay_centers = (-4.5, 0.10, 4.80)
    # Floor 1: rounded arch heads directly above the shopfronts (§25).
    for bay_index, bx in enumerate(bay_centers):
        for wing_index, dx in enumerate((-0.95, 0.95)):
            arched_window(f"RC_Floor1Window_{bay_index}{wing_index}", bx + dx, z_floor1 + 0.35, 1.35, 1.90, front_y, mats, groups["windows"])
    # Floors 2-3: rectangular recessed windows (§24).
    for floor_index, (z_base, win_h) in enumerate(((z_floor2 + 0.30, 1.75), (z_floor3 + 0.28, 1.55)), start=2):
        for bay_index, bx in enumerate(bay_centers):
            for wing_index, dx in enumerate((-0.95, 0.95)):
                rect_window(f"RC_Floor{floor_index}Window_{bay_index}{wing_index}", bx + dx, z_base, 1.35, win_h, front_y, mats, groups["windows"])

    # --- Cornice / roofline (§27, §28). -------------------------------------
    box("RC_Cornice_LowerBand", (width + 0.30, 0.42, 0.24), (0.0, front_y - 0.21, z_cornice + 0.12), mats["stone"], groups["ornament"])
    box("RC_Cornice_Projection", (width + 0.50, 0.30, 0.20), (0.0, front_y - 0.15, z_cornice + 0.34), mats["stone"], groups["ornament"])
    box("RC_Cornice_TopCap", (width + 0.20, 0.36, 0.24), (0.0, front_y - 0.18, z_cornice + 0.56), mats["stone"], groups["ornament"])

    # --- Hanging Real Camera sign with brackets (§15,16). -------------------
    sign_x, sign_z = 3.05, ground_h + 0.55
    box("RC_HangingSign_Box", (1.05, 0.10, 1.05), (sign_x, front_y - 0.75, sign_z), mats["signage"], groups["sign"])
    cylinder("RC_HangingSign_Bracket_Top", 0.05, 0.55, (sign_x, front_y - 0.35, sign_z + 0.45), mats["metal"], groups["sign"], rotation=(1.5708, 0.0, 0.0))
    cylinder("RC_HangingSign_Bracket_Bottom", 0.05, 0.55, (sign_x, front_y - 0.35, sign_z - 0.40), mats["metal"], groups["sign"], rotation=(1.5708, 0.0, 0.0))
    box("RC_HangingSign_MountPlate", (0.18, 0.10, 1.30), (sign_x, front_y + 0.02, sign_z), mats["metal"], groups["sign"])

    # --- Corner clock on the rounded corner mass (§17). ---------------------
    clock_x, clock_y, clock_z = corner_x - 2.15, front_y + 0.55, z_floor1 + 0.55
    box("RC_CornerClock_Housing", (0.55, 0.55, 0.55), (clock_x, clock_y, clock_z), mats["darktrim"], groups["clock"])
    cylinder("RC_CornerClock_FaceA", 0.30, 0.06, (clock_x - 0.30, clock_y, clock_z), mats["signage"], groups["clock"], rotation=(0.0, 1.5708, 0.0))
    cylinder("RC_CornerClock_FaceB", 0.30, 0.06, (clock_x, clock_y - 0.30, clock_z), mats["signage"], groups["clock"], rotation=(1.5708, 0.0, 0.0))
    box("RC_CornerClock_Bracket", (0.14, 0.14, 0.70), (clock_x + 0.20, clock_y + 0.20, clock_z - 0.55), mats["metal"], groups["clock"])

    # --- Basic interior shells behind both openings (§34). ------------------
    box("RC_MainShop_InteriorFloor", (shop_w - 0.10, 4.0, 0.10), (shop_x, shop_recess_y + 2.1, 0.05), mats["darktrim"], groups["interior"])
    box("RC_MainShop_InteriorCeiling", (shop_w - 0.10, 4.0, 0.10), (shop_x, shop_recess_y + 2.1, ground_h - 0.30), mats["darktrim"], groups["interior"])
    box("RC_MainShop_InteriorWall_L", (0.10, 4.0, ground_h - 0.40), (shop_x - shop_w / 2 + 0.15, shop_recess_y + 2.1, (ground_h - 0.4) / 2), mats["darktrim"], groups["interior"])
    box("RC_MainShop_InteriorWall_R", (0.10, 4.0, ground_h - 0.40), (shop_x + shop_w / 2 - 0.15, shop_recess_y + 2.1, (ground_h - 0.4) / 2), mats["darktrim"], groups["interior"])
    box("RC_MainShop_InteriorWall_Back", (shop_w - 0.10, 0.10, ground_h - 0.40), (shop_x, shop_recess_y + 4.1, (ground_h - 0.4) / 2), mats["darktrim"], groups["interior"])
    box("RC_GalleryEntrance_InteriorFloor", (gallery_w - 0.10, 2.5, 0.10), (gallery_x, gallery_recess_y + 1.25, 0.60), mats["darktrim"], groups["interior"])
    box("RC_GalleryEntrance_InteriorBack", (gallery_w - 0.10, 0.10, 2.4), (gallery_x, gallery_recess_y + 2.5, 1.85), mats["darktrim"], groups["interior"])

    # --- Interaction anchors for the future Real Camera entry (§14). --------
    empty("RC_EntranceAnchor", (shop_x, front_y + 0.9, 1.0), groups["anchors"], size=0.5)
    empty("RC_InteriorSpawnAnchor", (shop_x, shop_recess_y + 1.2, 0.0), groups["anchors"], size=0.5)
    empty("RC_ExitAnchor", (shop_x, front_y + 1.4, 0.0), groups["anchors"], size=0.5)

    # --- Review-only pavement/ground plane. ---------------------------------
    box("RC_Review_Pavement", (24.0, 8.0, 0.12), (0.0, front_y - 4.5, -0.06), mats["ground_review"], groups["review"])
    box("RC_Review_Ground", (36.0, 34.0, 0.12), (0.0, 4.0, -0.16), mats["ground_review"], groups["review"])

    cameras = (
        camera("CAMERA_A_StraightOnLowerFacade", (0.0, -22.0, 3.4), (0.0, front_y, 2.6), 50, groups["cameras"]),
        camera("CAMERA_B_ThreeQuarterDepth", (-16.0, -18.0, 5.5), (0.0, front_y + 1.5, 4.5), 42, groups["cameras"]),
        camera("CAMERA_C_LowAngleUpperFacade", (2.0, -12.0, 2.0), (0.0, front_y, total_h - 2.5), 38, groups["cameras"]),
        camera("CAMERA_D_CornerWithClock", (corner_x - 10.0, front_y - 8.0, 7.5), (corner_x - 2.0, front_y, 6.0), 40, groups["cameras"]),
        camera("CAMERA_E_ShopAndGalleryClose", (0.0, -8.5, 2.4), (-1.5, front_y, 2.2), 46, groups["cameras"]),
    )

    area_light("RC_Review_Key", (-12.0, -16.0, 16.0), (0.0, front_y, 5.0), 2600, 7.0, groups["lights"])
    area_light("RC_Review_Fill", (12.0, -10.0, 12.0), (0.0, front_y, 4.5), 1600, 6.0, groups["lights"])
    area_light("RC_Review_Corner", (corner_x - 8.0, front_y - 4.0, 10.0), (corner_x - 2.0, front_y, 5.5), 1400, 5.0, groups["lights"])

    world = scene.world or bpy.data.worlds.new("RC_BlockoutWorld")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.05, 0.06, 0.07, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.42

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

    note = bpy.data.texts.new("REAL_CAMERA_BLOCKOUT_NOTES")
    note.write(
        "FIRST PASS / REVIEW HOLD - GEOMETRY ONLY (see 13_Real_Camera.txt SS42-43)\n"
        "Inferred dimensions: 14.0 m Dale St frontage x 10.0 m depth x 14.2 m to parapet.\n"
        "Dale Street faces -Y; ground is Z=0; one unit equals one metre.\n"
        "Ground rhythm (west to east): corner mass+clock, Gallery entrance, pier,\n"
        "Real Camera shop (hero, red awning), pier, adjacent shuttered unit, corner pier.\n"
        "Corner mass is a rounded cylinder wrapping toward a short Lever St return wing.\n"
        "Fine ornament (capitals, carving, stone joints, weathering, typography,\n"
        "reflections, shop stock) is deliberately deferred to the ornament/texture passes.\n"
        "Open validation items per S43: bay widths, storey heights, corner curvature\n"
        "and pilaster spacing are estimated from photography, not surveyed.\n"
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
        "RC_MainShopGlass", "RC_RedAwning", "RC_GalleryStairs_Step_00",
        "RC_HangingSign_Box", "RC_CornerClock_Housing", "RC_CornerMass",
        "RC_EntranceAnchor", "RC_Cornice_TopCap",
    )
    missing = [name for name in required if bpy.data.objects.get(name) is None]
    if missing:
        raise RuntimeError(f"Missing blockout objects: {missing}")
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    triangles = sum(sum(max(0, len(poly.vertices) - 2) for poly in obj.data.polygons) for obj in meshes)
    print(f"Validation: {len(meshes)} mesh objects, approximately {triangles} triangles")
    print("Validation: metric scale, Z-up, ground level Z=0, Dale St frontage faces -Y")


def export_runtime_glb():
    """Export authored geometry and anchors, excluding review-only helpers."""
    GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
    excluded_collections = {
        "RC_BlockoutReviewOnly",
        "RC_BlockoutCameras",
        "RC_BlockoutLights",
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
        "view-a-straight-on-lower-facade.png",
        "view-b-three-quarter-depth.png",
        "view-c-low-angle-upper-facade.png",
        "view-d-corner-with-clock.png",
        "view-e-shop-and-gallery-close.png",
    )
    scene = bpy.context.scene
    for camera_obj, filename in zip(cameras, names):
        scene.camera = camera_obj
        scene.render.resolution_x = 1200
        scene.render.resolution_y = 800 if filename.startswith(("view-e",)) else 900
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
