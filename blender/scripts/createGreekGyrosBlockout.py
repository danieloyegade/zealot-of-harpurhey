"""Create the Greek Gyros kiosk's geometry-only blockout and four clay renders.

This file stops at the review hold requested by
references/architecture/gyros/15_Greek_Gyros.txt §29: main kiosk volume,
canopy, fascia, serving opening, counter, lower front panel and side depth,
plus the shallow interior shell §14 asks for so the open frontage is real
space rather than a black void. Vent divisions, menu boards, register,
lighting fixtures and structural detailing are deliberately deferred to the
second pass (§30), and no signage artwork, diamond-plate pattern or food is
textured (§§9, 20, 21).

One Blender unit is one metre, Z is up, and the serving frontage faces -Y.
Inferred, not surveyed: proportions are estimated from the supplied Deansgate
photography (customers at the counter, the 1.78 m player height, and standard
kiosk counter/fascia heights), the same caveat as every other hero asset here.
"""

from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
BLEND_PATH = ROOT / "blender" / "source" / "greek_gyros_blockout.blend"
GLB_PATH = ROOT / "public" / "assets" / "models" / "greek-gyros-blockout.glb"
RENDER_DIR = ROOT / "renders" / "greek-gyros-blockout"

# --- Inferred envelope (metres) ------------------------------------------
BODY_W = 6.40           # kiosk body width
BODY_D = 2.60           # kiosk body depth
FRONT_Y = -1.30         # customer-facing front plane
BACK_Y = 1.30
SKIRT_H = 0.26          # dark chassis/base skirt
PANEL_TOP = 0.94        # top of the blue lower front panel
APRON_TOP = 1.22        # top of the metal-clad apron band
COUNTER_TOP = 1.28      # stainless worktop surface
COUNTER_FRONT_Y = -1.46
COUNTER_BACK_Y = -0.84
OPENING_TOP = 2.30      # underside of the front header / canopy soffit
BODY_TOP = 2.42         # top of walls, header and interior ceiling
ROOF_TOP = 2.56
SIGN_BOT = 2.38         # bottom of the projecting sign box
STRIP_TOP = 2.68        # top of the secondary menu strip
SIGN_TOP = 3.32         # top of the main GREEK GYROS fascia
CAP_TOP = 3.40          # thin cap over the sign box
SIGN_W = 6.72           # sign box width (overhangs the body slightly)
SIGN_FRONT_Y = -1.68    # sign box front plane
SIGN_FACE_Y = -1.73     # proud signage surfaces
JAMB_W = 0.22


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


def material(name, color, roughness=0.85, metallic=0.0):
    result = bpy.data.materials.new(name)
    result.diffuse_color = (*color, 1.0)
    result.use_nodes = True
    bsdf = result.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
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


def cylinder(name, radius, depth, location, mat, target, vertices=16):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=depth, location=location, vertices=vertices
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    if mat:
        obj.data.materials.append(mat)
    relink(obj, target)
    return obj


def empty(name, location, target, display="ARROWS", size=0.4):
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


def scale_figure(name, location, mat, target):
    """Review-only 1.78 m blocked figure, matching the player's authored height."""
    x, y = location
    box(f"{name}_Legs", (0.34, 0.24, 0.86), (x, y, 0.43), mat, target)
    box(f"{name}_Torso", (0.44, 0.26, 0.62), (x, y, 1.17), mat, target)
    box(f"{name}_Head", (0.20, 0.21, 0.26), (x, y, 1.63), mat, target)


def build_scene():
    clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0

    master = collection("GREEK_GYROS_MASTER")
    groups = {
        "shell": collection("GG_KioskShell", master),
        "frontage": collection("GG_Frontage", master),
        "canopy": collection("GG_RoofCanopy", master),
        "signage": collection("GG_SignageSurfaces", master),
        "interior": collection("GG_InteriorShell", master),
        "anchors": collection("GG_InteractionAnchors", master),
        "review": collection("GG_BlockoutReviewOnly", master),
        "cameras": collection("GG_BlockoutCameras", master),
        "lights": collection("GG_BlockoutLights", master),
    }

    mats = {
        "blue": material("MAT_GG_Blue_PLACEHOLDER", (0.055, 0.105, 0.30), 0.55),
        "navy": material("MAT_GG_DeepBlue_PLACEHOLDER", (0.022, 0.045, 0.145), 0.55),
        "white": material("MAT_GG_White_PLACEHOLDER", (0.78, 0.78, 0.76), 0.70),
        "metal": material("MAT_GG_Metal_PLACEHOLDER", (0.60, 0.61, 0.63), 0.42, 0.30),
        "dark": material("MAT_GG_DarkMetal_PLACEHOLDER", (0.115, 0.125, 0.135), 0.55, 0.25),
        "ground_review": material("MAT_GG_ReviewGround", (0.27, 0.275, 0.27)),
        "figure_review": material("MAT_GG_ReviewFigure", (0.42, 0.40, 0.38)),
    }

    shell = groups["shell"]
    frontage = groups["frontage"]
    canopy = groups["canopy"]
    signage = groups["signage"]
    interior = groups["interior"]

    # --- Chassis / base skirt (§2, §10). -------------------------------------
    box("GG_BaseSkirt", (BODY_W - 0.14, BODY_D - 0.14, SKIRT_H),
        (0.0, 0.0, SKIRT_H / 2), mats["dark"], shell)
    for side, x in (("Left", -(BODY_W / 2 - 0.30)), ("Right", BODY_W / 2 - 0.30)):
        cylinder(f"GG_Leveller_{side}_Front", 0.05, SKIRT_H,
                 (x, FRONT_Y + 0.45, SKIRT_H / 2), mats["dark"], shell)
        cylinder(f"GG_Leveller_{side}_Rear", 0.05, SKIRT_H,
                 (x, BACK_Y - 0.45, SKIRT_H / 2), mats["dark"], shell)

    wall_h = BODY_TOP - SKIRT_H
    wall_z = SKIRT_H + wall_h / 2

    # --- Side walls, rear return and roof (§6, §12). -------------------------
    for side, x in (("Left", -(BODY_W / 2 - 0.06)), ("Right", BODY_W / 2 - 0.06)):
        box(f"GG_SideWall_{side}", (0.12, BODY_D, wall_h), (x, 0.0, wall_z),
            mats["metal"], shell)
        box(f"GG_SideTrim_{side}", (0.06, BODY_D + 0.04, 0.10),
            (x + (0.08 if side == "Right" else -0.08), 0.0, BODY_TOP - 0.12),
            mats["dark"], shell)
    box("GG_RearWall", (BODY_W, 0.12, wall_h), (0.0, BACK_Y - 0.06, wall_z),
        mats["metal"], shell)
    box("GG_RoofSlab", (BODY_W + 0.16, BODY_D + 0.16, ROOF_TOP - BODY_TOP),
        (0.0, 0.0, (BODY_TOP + ROOF_TOP) / 2), mats["dark"], shell)

    # --- Front frame around the serving opening (§11). -----------------------
    for side, x in (("Left", -(BODY_W / 2 - JAMB_W / 2)), ("Right", BODY_W / 2 - JAMB_W / 2)):
        box(f"GG_FrontJamb_{side}", (JAMB_W, 0.20, wall_h), (x, FRONT_Y + 0.10, wall_z),
            mats["metal"], frontage)
    box("GG_FrontHeader", (BODY_W, 0.20, BODY_TOP - OPENING_TOP),
        (0.0, FRONT_Y + 0.10, (OPENING_TOP + BODY_TOP) / 2), mats["metal"], frontage)
    box("GG_FrontMullion", (0.09, 0.16, OPENING_TOP - COUNTER_TOP),
        (1.58, FRONT_Y + 0.08, (COUNTER_TOP + OPENING_TOP) / 2), mats["metal"], frontage)

    # --- Front stack below the counter (§8, §9, §10). ------------------------
    box("GG_LowerFrontPanel", (BODY_W - 0.12, 0.06, PANEL_TOP - SKIRT_H),
        (0.0, FRONT_Y - 0.03, (SKIRT_H + PANEL_TOP) / 2), mats["blue"], frontage)
    box("GG_MetalCladding_Apron", (BODY_W - 0.06, 0.11, APRON_TOP - PANEL_TOP),
        (0.0, FRONT_Y - 0.055, (PANEL_TOP + APRON_TOP) / 2), mats["metal"], frontage)

    for side, x in (("Left", -(BODY_W / 2 + 0.03)), ("Right", BODY_W / 2 + 0.03)):
        box(f"GG_LowerSidePanel_{side}", (0.06, 1.00, PANEL_TOP - SKIRT_H),
            (x, FRONT_Y + 0.55, (SKIRT_H + PANEL_TOP) / 2), mats["blue"], frontage)

    # --- Service counter (§8). ----------------------------------------------
    counter_depth = COUNTER_BACK_Y - COUNTER_FRONT_Y
    counter_mid_y = (COUNTER_FRONT_Y + COUNTER_BACK_Y) / 2
    box("GG_ServiceCounter_Top", (BODY_W - 0.04, counter_depth, 0.06),
        (0.0, counter_mid_y, COUNTER_TOP - 0.03), mats["metal"], frontage)
    box("GG_ServiceCounter_FrontLip", (BODY_W - 0.04, 0.05, 0.12),
        (0.0, COUNTER_FRONT_Y + 0.025, COUNTER_TOP - 0.12), mats["metal"], frontage)
    box("GG_ServiceCounter_Support", (BODY_W - 0.30, 0.46, APRON_TOP - 0.32 - SKIRT_H + 0.06),
        (0.0, COUNTER_BACK_Y - 0.20, (SKIRT_H + APRON_TOP - 0.26) / 2), mats["metal"], frontage)

    # --- Projecting canopy / sign box (§4, §5, §6). --------------------------
    soffit_depth = FRONT_Y - SIGN_FACE_Y
    soffit_mid_y = (SIGN_FACE_Y + FRONT_Y) / 2
    box("GG_CanopySoffit", (SIGN_W, soffit_depth, SIGN_BOT - OPENING_TOP),
        (0.0, soffit_mid_y, (OPENING_TOP + SIGN_BOT) / 2), mats["white"], canopy)
    box("GG_SignBoxBody", (SIGN_W, FRONT_Y - SIGN_FRONT_Y, SIGN_TOP - SIGN_BOT),
        (0.0, (SIGN_FRONT_Y + FRONT_Y) / 2, (SIGN_BOT + SIGN_TOP) / 2), mats["blue"], canopy)
    box("GG_CanopyTopCap", (SIGN_W + 0.12, soffit_depth + 0.10, CAP_TOP - SIGN_TOP),
        (0.0, soffit_mid_y, (SIGN_TOP + CAP_TOP) / 2), mats["dark"], canopy)
    for side, x in (("Left", -2.55), ("Right", 2.55)):
        box(f"GG_SignBracket_{side}", (0.08, soffit_depth - 0.06, 0.16),
            (x, soffit_mid_y + 0.03, OPENING_TOP - 0.08), mats["dark"], canopy)

    # --- Reserved signage surfaces, no artwork yet (§20, §21). ---------------
    box("GG_MainSignSurface", (SIGN_W - 0.04, 0.05, SIGN_TOP - STRIP_TOP),
        (0.0, SIGN_FACE_Y + 0.025, (STRIP_TOP + SIGN_TOP) / 2), mats["blue"], signage)
    box("GG_MenuStripSurface", (SIGN_W - 0.04, 0.04, STRIP_TOP - SIGN_BOT - 0.02),
        (0.0, SIGN_FACE_Y + 0.03, (SIGN_BOT + STRIP_TOP) / 2), mats["navy"], signage)
    flag_w = 0.56
    flag_h = (SIGN_TOP - STRIP_TOP) - 0.14
    for side, x in (("Left", -(SIGN_W / 2 - 0.16 - flag_w / 2)), ("Right", SIGN_W / 2 - 0.16 - flag_w / 2)):
        box(f"GG_FlagPanel_{side}", (flag_w, 0.03, flag_h),
            (x, SIGN_FACE_Y + 0.005, (STRIP_TOP + SIGN_TOP) / 2), mats["white"], signage)
    box("GG_LowerFrontSignSurface", (BODY_W - 0.60, 0.03, PANEL_TOP - SKIRT_H - 0.16),
        (0.0, FRONT_Y - 0.07, (SKIRT_H + PANEL_TOP) / 2), mats["blue"], signage)

    # --- Interior shell: real depth behind the counter (§14). ----------------
    box("GG_InteriorFloor", (BODY_W - 0.24, BODY_D - 0.24, 0.06),
        (0.0, 0.0, SKIRT_H + 0.03), mats["metal"], interior)
    box("GG_InteriorCeiling", (BODY_W - 0.24, BODY_D - 0.24, 0.10),
        (0.0, 0.0, BODY_TOP - 0.05), mats["white"], interior)
    box("GG_InteriorRearLining", (BODY_W - 0.24, 0.05, BODY_TOP - SKIRT_H - 0.10),
        (0.0, BACK_Y - 0.145, SKIRT_H + (BODY_TOP - SKIRT_H - 0.10) / 2), mats["metal"], interior)
    box("GG_PrepCounter", (BODY_W - 1.30, 0.52, 0.90),
        (-0.20, BACK_Y - 0.46, SKIRT_H + 0.51), mats["metal"], interior)
    box("GG_GrillUnit", (0.80, 0.46, 1.05),
        (2.10, BACK_Y - 0.44, SKIRT_H + 0.58), mats["metal"], interior)

    # --- Interaction anchors, empties only (§22). ----------------------------
    anchors = groups["anchors"]
    empty("GG_OrderAnchor", (1.55, FRONT_Y - 0.95, 0.0), anchors, "SPHERE", 0.28)
    empty("GG_VendorAnchor", (1.55, 0.25, SKIRT_H), anchors, "SPHERE", 0.28)
    for index, (x, y) in enumerate(((0.45, -2.55), (-0.45, -2.70), (-1.35, -2.85)), start=1):
        empty(f"GG_QueueAnchor_{index:02d}", (x, y, 0.0), anchors, "PLAIN_AXES", 0.26)

    # --- Review-only pavement and 1.78 m scale figures. ----------------------
    review = groups["review"]
    box("GG_Review_Ground", (26.0, 22.0, 0.12), (0.0, 2.0, -0.06), mats["ground_review"], review)
    scale_figure("GG_Review_ScaleFigure_Customer", (-2.80, -2.10), mats["figure_review"], review)
    scale_figure("GG_Review_ScaleFigure_Passerby", (4.55, -3.10), mats["figure_review"], review)

    # --- Review cameras (§29 VIEW A-D). --------------------------------------
    cameras = (
        camera("CAMERA_A_StraightOnFront", (0.0, -10.5, 1.95), (0.0, FRONT_Y, 1.80), 42, groups["cameras"]),
        camera("CAMERA_B_ThreeQuarterFront", (7.4, -8.2, 2.70), (-0.3, -0.30, 1.70), 40, groups["cameras"]),
        camera("CAMERA_C_SideProfile", (13.5, -1.10, 2.10), (-0.4, -0.20, 1.70), 50, groups["cameras"]),
        camera("CAMERA_D_CounterEyeLevel", (0.80, -5.60, 1.62), (0.20, 0.20, 1.72), 28, groups["cameras"]),
    )

    area_light("GG_Review_Key", (-7.0, -9.0, 9.0), (0.0, FRONT_Y, 2.1), 1800, 6.0, groups["lights"])
    area_light("GG_Review_Fill", (8.5, -6.0, 6.5), (0.0, FRONT_Y, 1.8), 1100, 5.0, groups["lights"])
    area_light("GG_Review_Interior", (0.0, -0.30, 2.24), (0.0, 1.0, 1.1), 42, 1.8, groups["lights"])

    world = scene.world or bpy.data.worlds.new("GG_BlockoutWorld")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.055, 0.065, 0.075, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.45

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

    note = bpy.data.texts.new("GREEK_GYROS_BLOCKOUT_NOTES")
    note.write(
        "FIRST PASS / REVIEW HOLD - GEOMETRY ONLY (see 15_Greek_Gyros.txt SS29-30)\n"
        f"Inferred envelope: {BODY_W:.2f} m wide x {BODY_D:.2f} m deep x {CAP_TOP:.2f} m "
        "to the top of the sign cap.\n"
        "Serving frontage faces -Y; ground is Z=0; one unit equals one metre.\n"
        f"Counter worktop {COUNTER_TOP:.2f} m; serving opening {COUNTER_TOP:.2f}-{OPENING_TOP:.2f} m;\n"
        f"menu strip {SIGN_BOT:.2f}-{STRIP_TOP:.2f} m; GREEK GYROS fascia {STRIP_TOP:.2f}-{SIGN_TOP:.2f} m.\n"
        "Deferred to the second pass: vent/panel divisions, menu boards, register,\n"
        "lighting fixtures, side service opening, detailed framing and sign mounts.\n"
        "Deferred to texturing: GREEK GYROS wordmark, Greek flags, CHICKEN/PORK/HALLOUMI\n"
        "strip, social icons, food imagery, diamond-plate pattern, stainless wear.\n"
        "Review-only ground plane and 1.78 m scale figures are excluded from the GLB.\n"
    )

    layout = {
        "groups": groups,
        "mats": mats,
        "body_w": BODY_W,
        "body_d": BODY_D,
        "front_y": FRONT_Y,
        "back_y": BACK_Y,
        "skirt_h": SKIRT_H,
        "panel_top": PANEL_TOP,
        "apron_top": APRON_TOP,
        "counter_top": COUNTER_TOP,
        "counter_front_y": COUNTER_FRONT_Y,
        "counter_back_y": COUNTER_BACK_Y,
        "opening_top": OPENING_TOP,
        "body_top": BODY_TOP,
        "roof_top": ROOF_TOP,
        "sign_bot": SIGN_BOT,
        "strip_top": STRIP_TOP,
        "sign_top": SIGN_TOP,
        "cap_top": CAP_TOP,
        "sign_w": SIGN_W,
        "sign_front_y": SIGN_FRONT_Y,
        "sign_face_y": SIGN_FACE_Y,
    }
    return cameras, layout


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
        "GG_BaseSkirt", "GG_RoofSlab", "GG_FrontHeader", "GG_LowerFrontPanel",
        "GG_ServiceCounter_Top", "GG_CanopySoffit", "GG_SignBoxBody",
        "GG_MainSignSurface", "GG_MenuStripSurface", "GG_FlagPanel_Left",
        "GG_InteriorFloor", "GG_OrderAnchor", "GG_QueueAnchor_03",
    )
    missing = [name for name in required if bpy.data.objects.get(name) is None]
    if missing:
        raise RuntimeError(f"Missing blockout objects: {missing}")
    unnamed = [obj.name for obj in bpy.data.objects if obj.name.startswith(("Cube", "Cylinder"))]
    if unnamed:
        raise RuntimeError(f"Unnamed primitives left in scene: {unnamed}")
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    triangles = sum(sum(max(0, len(poly.vertices) - 2) for poly in obj.data.polygons) for obj in meshes)
    print(f"Validation: {len(meshes)} mesh objects, approximately {triangles} triangles")
    print(f"Validation: envelope {BODY_W:.2f} x {BODY_D:.2f} x {CAP_TOP:.2f} m, frontage faces -Y")


def export_runtime_glb():
    """Export the kiosk and its anchors only - no pavement, figures or context (§24)."""
    GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
    excluded_collections = {
        "GG_BlockoutReviewOnly",
        "GG_BlockoutCameras",
        "GG_BlockoutLights",
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
        "view-a-straight-on-front.png",
        "view-b-three-quarter-front.png",
        "view-c-side-profile.png",
        "view-d-counter-eye-level.png",
    )
    scene = bpy.context.scene
    for camera_obj, filename in zip(cameras, names):
        scene.camera = camera_obj
        scene.render.resolution_x = 1200
        scene.render.resolution_y = 900
        scene.render.filepath = str(RENDER_DIR / filename)
        bpy.ops.render.render(write_still=True)
        print(f"Rendered {scene.render.filepath}")


def main():
    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    cameras, _layout = build_scene()
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
