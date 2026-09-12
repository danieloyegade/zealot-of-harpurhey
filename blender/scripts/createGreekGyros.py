"""Second-pass geometry for the Greek Gyros kiosk, built on the approved blockout.

This is the §30 pass from references/architecture/gyros/15_Greek_Gyros.txt,
run after Daniel approved the blockout's 6.40 m width on 2026-09-12. It imports
createGreekGyrosBlockout.py, rebuilds that reviewed layout, and adds the
detailing the brief holds back until approval: vent/panel divisions, structural
framing, the side service door (§13), interior counters and equipment (§§14-15),
the register area (§16), menu boards (§17), lighting fixtures (§18) and signage
mounting details.

Still deliberately absent: all artwork and texture-stage work - the GREEK GYROS
wordmark, Greek flags, the CHICKEN/PORK/HALLOUMI strip, social icons, food
imagery, prices, the diamond-plate pattern, dirt and stickers (§§9, 20, 21) -
and any baked emissive night lighting, which §19 requires to come from materials
and game lighting rather than from geometry.

One Blender unit is one metre, Z is up, and the serving frontage faces -Y.
"""

import importlib.util
from math import radians
from pathlib import Path

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLOCKOUT_SCRIPT = Path(__file__).with_name("createGreekGyrosBlockout.py")
BLEND_PATH = PROJECT_ROOT / "blender" / "source" / "greek_gyros.blend"
GLB_PATH = PROJECT_ROOT / "public" / "assets" / "models" / "greek_gyros.glb"
RENDER_DIR = PROJECT_ROOT / "renders" / "greek-gyros"

spec = importlib.util.spec_from_file_location("greek_gyros_blockout", BLOCKOUT_SCRIPT)
blockout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(blockout)

B = blockout  # dimensions live on the blockout module so they are never re-derived


def glass_material(name, color=(0.72, 0.79, 0.82), alpha=0.22):
    result = bpy.data.materials.new(name)
    result.diffuse_color = (*color, alpha)
    result.use_nodes = True
    bsdf = result.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, alpha)
    bsdf.inputs["Roughness"].default_value = 0.08
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Alpha"].default_value = alpha
    bsdf.inputs["Transmission Weight"].default_value = 0.10
    result.surface_render_method = "DITHERED"
    return result


def tilted_box(name, dimensions, location, mat, target, rotation_x=0.0):
    obj = B.box(name, dimensions, location, mat, target)
    if rotation_x:
        obj.rotation_euler[0] = rotation_x
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        bpy.ops.object.select_all(action="DESELECT")
    return obj


# --- §30 panel divisions and structural framing ---------------------------

def add_framing_and_panels(groups, mats):
    shell = groups["shell"]
    frontage = groups["frontage"]
    wall_h = B.BODY_TOP - B.SKIRT_H
    wall_z = B.SKIRT_H + wall_h / 2

    # Corner posts read the kiosk as a built frame rather than a solid block.
    for name, x, y in (
        ("FrontLeft", -(B.BODY_W / 2 - 0.05), B.FRONT_Y + 0.05),
        ("FrontRight", B.BODY_W / 2 - 0.05, B.FRONT_Y + 0.05),
        ("RearLeft", -(B.BODY_W / 2 - 0.05), B.BACK_Y - 0.05),
        ("RearRight", B.BODY_W / 2 - 0.05, B.BACK_Y - 0.05),
    ):
        B.box(f"GG_CornerPost_{name}", (0.11, 0.11, wall_h + 0.06),
              (x, y, wall_z + 0.03), mats["dark"], shell)

    # Panel seams: geometry only for the major divisions, never the pattern (§9).
    for side, x in (("Left", -(B.BODY_W / 2 + 0.015)), ("Right", B.BODY_W / 2 + 0.015)):
        for index, y in enumerate((-0.62, 0.02, 0.66), start=1):
            B.box(f"GG_SidePanelSeam_{side}_{index:02d}", (0.05, 0.05, wall_h - 0.10),
                  (x, y, wall_z), mats["dark"], shell)
    for index, x in enumerate((-2.24, -0.78, 0.66, 2.12), start=1):
        B.box(f"GG_ApronSeam_{index:02d}", (0.05, 0.04, B.APRON_TOP - B.PANEL_TOP - 0.02),
              (x, B.FRONT_Y - 0.115, (B.PANEL_TOP + B.APRON_TOP) / 2), mats["dark"], frontage)
    for index, x in enumerate((-2.05, 0.0, 2.05), start=1):
        B.box(f"GG_RearPanelSeam_{index:02d}", (0.05, 0.05, wall_h - 0.10),
              (x, B.BACK_Y + 0.015, wall_z), mats["dark"], shell)
    B.box("GG_LowerPanelRail_Top", (B.BODY_W - 0.10, 0.05, 0.05),
          (0.0, B.FRONT_Y - 0.055, B.PANEL_TOP - 0.02), mats["dark"], frontage)
    B.box("GG_LowerPanelRail_Bottom", (B.BODY_W - 0.10, 0.05, 0.05),
          (0.0, B.FRONT_Y - 0.055, B.SKIRT_H + 0.03), mats["dark"], frontage)

    # Opening framing (§11): sill rail, intermediate uprights, header stiffener.
    B.box("GG_OpeningSillRail", (B.BODY_W - 0.46, 0.09, 0.07),
          (0.0, B.FRONT_Y + 0.06, B.COUNTER_TOP + 0.05), mats["metal"], frontage)
    B.box("GG_HeaderStiffener", (B.BODY_W - 0.46, 0.10, 0.08),
          (0.0, B.FRONT_Y + 0.20, B.OPENING_TOP - 0.05), mats["metal"], frontage)
    for index, x in enumerate((-1.62,), start=1):
        B.box(f"GG_FrontMullion_{index:02d}", (0.08, 0.15, B.OPENING_TOP - B.COUNTER_TOP),
              (x, B.FRONT_Y + 0.08, (B.COUNTER_TOP + B.OPENING_TOP) / 2), mats["metal"], frontage)


def add_sign_mounting(groups, mats):
    """§30 signage mounting details for the projecting sign box."""
    canopy = groups["canopy"]
    soffit_mid_y = (B.SIGN_FACE_Y + B.FRONT_Y) / 2
    B.box("GG_SignMountRail", (B.BODY_W - 0.30, 0.09, 0.11),
          (0.0, B.FRONT_Y - 0.06, B.SIGN_BOT + 0.10), mats["dark"], canopy)
    B.box("GG_SignTopRail", (B.SIGN_W - 0.20, 0.10, 0.07),
          (0.0, B.FRONT_Y - 0.10, B.SIGN_TOP - 0.06), mats["dark"], canopy)
    for side, x in (("Left", -2.98), ("Right", 2.98)):
        B.box(f"GG_SignStay_{side}", (0.07, 0.30, 0.07),
              (x, B.FRONT_Y - 0.16, B.SIGN_TOP - 0.10), mats["dark"], canopy)
        B.box(f"GG_SignBracket_Outer_{side}", (0.08, B.FRONT_Y - B.SIGN_FACE_Y - 0.08, 0.14),
              (x, soffit_mid_y + 0.02, B.OPENING_TOP - 0.07), mats["dark"], canopy)
    for index, x in enumerate((-1.05, 1.05), start=1):
        B.box(f"GG_SignBracket_Inner_{index:02d}", (0.08, B.FRONT_Y - B.SIGN_FACE_Y - 0.10, 0.13),
              (x, soffit_mid_y + 0.03, B.OPENING_TOP - 0.07), mats["dark"], canopy)


def add_roof_services(groups, mats):
    """Extraction and vents: the kitchen has to breathe somewhere (§30)."""
    shell = groups["shell"]
    B.box("GG_RoofEdgeTrim_Front", (B.BODY_W + 0.20, 0.07, 0.09),
          (0.0, -(B.BODY_D / 2 + 0.04), B.ROOF_TOP + 0.04), mats["dark"], shell)
    B.box("GG_RoofEdgeTrim_Rear", (B.BODY_W + 0.20, 0.07, 0.09),
          (0.0, B.BODY_D / 2 + 0.04, B.ROOF_TOP + 0.04), mats["dark"], shell)
    B.box("GG_ExtractionPlenum", (1.30, 0.72, 0.26),
          (1.45, 0.42, B.ROOF_TOP + 0.13), mats["metal"], shell)
    B.cylinder("GG_ExtractionDuct", 0.24, 0.42, (1.45, 0.42, B.ROOF_TOP + 0.47),
               mats["metal"], shell, vertices=14)
    B.box("GG_ExtractionCowl", (0.76, 0.70, 0.16),
          (1.45, 0.42, B.ROOF_TOP + 0.72), mats["dark"], shell)
    for index, x in enumerate((-2.35, -1.45), start=1):
        B.box(f"GG_RoofVent_{index:02d}", (0.46, 0.46, 0.14),
              (x, 0.62, B.ROOF_TOP + 0.07), mats["dark"], shell)
    B.box("GG_RearLouvre", (1.05, 0.06, 0.42),
          (-2.05, B.BACK_Y + 0.02, 1.70), mats["dark"], shell)
    for index, z in enumerate((1.56, 1.70, 1.84), start=1):
        B.box(f"GG_RearLouvreBlade_{index:02d}", (0.98, 0.05, 0.04),
              (-2.05, B.BACK_Y + 0.05, z), mats["metal"], shell)


def add_side_service(groups, mats):
    """§13: the side access door visible at the kiosk's right-hand end."""
    shell = groups["shell"]
    signage = groups["signage"]
    x_face = B.BODY_W / 2
    door_z0, door_z1 = B.SKIRT_H + 0.04, 2.22
    door_mid_z = (door_z0 + door_z1) / 2
    B.box("GG_SideDoor_Recess", (0.10, 0.98, door_z1 - door_z0),
          (x_face - 0.02, 0.42, door_mid_z), mats["dark"], shell)
    B.box("GG_SideDoor_Panel", (0.06, 0.88, door_z1 - door_z0 - 0.08),
          (x_face + 0.04, 0.42, door_mid_z), mats["metal"], shell)
    for suffix, dy in (("Fore", -0.49), ("Aft", 0.49)):
        B.box(f"GG_SideDoor_Jamb_{suffix}", (0.09, 0.07, door_z1 - door_z0 + 0.06),
              (x_face + 0.02, 0.42 + dy, door_mid_z), mats["dark"], shell)
    B.box("GG_SideDoor_Head", (0.09, 1.04, 0.07),
          (x_face + 0.02, 0.42, door_z1 + 0.02), mats["dark"], shell)
    B.cylinder("GG_SideDoor_Handle", 0.025, 0.22, (x_face + 0.09, 0.05, 1.12),
               mats["dark"], shell, vertices=10)
    B.box("GG_SideStep", (0.52, 0.74, B.SKIRT_H),
          (x_face + 0.30, 0.42, B.SKIRT_H / 2), mats["dark"], shell)
    # Reserved side artwork area (§20) - no graphic applied at this stage.
    B.box("GG_SideSignSurface", (0.04, 1.20, 0.58),
          (-(x_face + 0.03), -0.30, 1.66), mats["white"], signage)


# --- §§14-17 interior ------------------------------------------------------

def delete_objects(names):
    """Blockout stand-ins the second pass replaces with authored units."""
    for name in names:
        obj = bpy.data.objects.get(name)
        if obj is not None:
            bpy.data.objects.remove(obj, do_unlink=True)


def add_interior(groups, mats):
    interior = groups["interior"]
    signage = groups["signage"]
    floor_z = B.SKIRT_H + 0.06          # 0.32: top of the interior floor
    ceiling_z = B.BODY_TOP - 0.10       # 2.32: underside of the interior ceiling
    rear_face_y = B.BACK_Y - 0.17       # 1.13: inner face of the rear lining
    run_y = rear_face_y - 0.30
    run_h = 0.90
    run_z = floor_z + run_h / 2

    # The blockout's two placeholder blocks become a continuous rear run.
    delete_objects(("GG_PrepCounter", "GG_GrillUnit"))
    for name, x, width in (
        ("GG_RefrigeratedCounter", -2.25, 1.60),
        ("GG_PrepCounter", -0.45, 2.00),
        ("GG_RotisserieCounter", 1.05, 1.00),
        ("GG_GrillUnit", 2.30, 1.50),
    ):
        B.box(name, (width, 0.55, run_h), (x, run_y, run_z), mats["metal"], interior)
        B.box(f"{name}_Kickboard", (width - 0.06, 0.05, 0.12),
              (x, run_y - 0.30, floor_z + 0.06), mats["dark"], interior)
    B.box("GG_RefrigeratedCounter_Door", (1.42, 0.05, 0.70),
          (-2.25, run_y - 0.30, run_z + 0.02), mats["dark"], interior)
    B.box("GG_CondimentArea", (0.92, 0.42, 0.26),
          (-0.55, run_y - 0.02, floor_z + run_h + 0.13), mats["metal"], interior)
    B.box("GG_GrillUnit_Hotplate", (1.34, 0.50, 0.09),
          (2.30, run_y - 0.02, floor_z + run_h + 0.05), mats["dark"], interior)
    B.box("GG_GrillUnit_Backsplash", (1.44, 0.06, 0.42),
          (2.30, rear_face_y - 0.05, floor_z + run_h + 0.21), mats["metal"], interior)

    # Vertical rotisserie: equipment only, no meat cone (§27).
    B.box("GG_Rotisserie_Base", (0.46, 0.44, 0.14),
          (1.05, run_y - 0.02, floor_z + run_h + 0.07), mats["metal"], interior)
    B.box("GG_Rotisserie_Heater", (0.34, 0.10, 0.63),
          (1.05, run_y + 0.16, 1.685), mats["dark"], interior)
    B.cylinder("GG_Rotisserie_Spit", 0.035, 0.60, (1.05, run_y - 0.06, 1.68),
               mats["metal"], interior, vertices=10)
    B.box("GG_Rotisserie_Guard", (0.54, 0.04, 0.58),
          (1.05, run_y - 0.24, 1.68), mats["metal"], interior)

    # Extraction hood over the hot line, ducted up to the roof cowl.
    B.box("GG_ExtractionHood", (2.40, 0.78, 0.26),
          (1.62, run_y - 0.06, 2.15), mats["metal"], interior)
    B.box("GG_ExtractionHood_Riser", (0.62, 0.56, 0.08),
          (1.45, run_y - 0.02, ceiling_z - 0.04), mats["metal"], interior)

    # Wall shelving above the prep run.
    for index, z in enumerate((1.62, 1.94), start=1):
        B.box(f"GG_Shelf_{index:02d}", (2.05, 0.30, 0.05),
              (-2.30, rear_face_y - 0.15, z), mats["metal"], interior)
        B.box(f"GG_Shelf_Bracket_{index:02d}", (2.05, 0.05, 0.07),
              (-2.30, rear_face_y - 0.03, z - 0.05), mats["dark"], interior)

    # Menu boards: flat panels only, no prices or food photographs yet (§17).
    for name, x in (("A", -0.10), ("B", 0.78), ("C", 1.66)):
        B.box(f"GG_MenuBoard_{name}", (0.78, 0.05, 0.92),
              (x, rear_face_y - 0.02, 1.80), mats["white"], signage)
        B.box(f"GG_MenuBoard_{name}_Frame", (0.84, 0.04, 0.98),
              (x, rear_face_y + 0.02, 1.80), mats["dark"], signage)


def add_counter_and_register(groups, mats):
    """§§8, 16: the hot display, its glass screen, and the ordering end."""
    frontage = groups["frontage"]
    signage = groups["signage"]
    guard_mat = mats["glass"]

    # Hot-food display wells set into the counter's left two thirds.
    B.box("GG_HotWell_Body", (3.05, 0.54, 0.20),
          (-1.32, B.COUNTER_FRONT_Y + 0.34, B.COUNTER_TOP + 0.10), mats["metal"], frontage)
    for index, x in enumerate((-2.52, -1.72, -0.92, -0.12), start=1):
        B.box(f"GG_HotWell_Divider_{index:02d}", (0.05, 0.50, 0.16),
              (x, B.COUNTER_FRONT_Y + 0.34, B.COUNTER_TOP + 0.12), mats["dark"], frontage)

    # Serving screen over the hot display.
    for side, x in (("Left", -2.86), ("Right", 0.22)):
        B.box(f"GG_CounterGuard_Post_{side}", (0.05, 0.05, 0.46),
              (x, B.COUNTER_FRONT_Y + 0.14, B.COUNTER_TOP + 0.23), mats["metal"], frontage)
    B.box("GG_CounterGuard_Glass", (3.10, 0.03, 0.42),
          (-1.32, B.COUNTER_FRONT_Y + 0.14, B.COUNTER_TOP + 0.24), guard_mat, frontage)
    B.box("GG_CounterGuard_Rail", (3.14, 0.05, 0.05),
          (-1.32, B.COUNTER_FRONT_Y + 0.14, B.COUNTER_TOP + 0.47), mats["metal"], frontage)

    # Ordering / payment end (§16).
    B.box("GG_RegisterCounter", (1.30, 0.52, 0.10),
          (2.30, B.COUNTER_FRONT_Y + 0.33, B.COUNTER_TOP + 0.05), mats["metal"], frontage)
    B.box("GG_Register_Base", (0.34, 0.26, 0.12),
          (2.36, B.COUNTER_FRONT_Y + 0.40, B.COUNTER_TOP + 0.16), mats["dark"], frontage)
    tilted_box("GG_Register_Screen", (0.32, 0.05, 0.26),
               (2.36, B.COUNTER_FRONT_Y + 0.42, B.COUNTER_TOP + 0.35), mats["dark"], frontage,
               rotation_x=radians(-14))
    B.box("GG_CardReader", (0.10, 0.08, 0.16),
          (1.82, B.COUNTER_FRONT_Y + 0.20, B.COUNTER_TOP + 0.08), mats["dark"], frontage)

    # Reserved ORDER HERE / PICK UP HERE panels - lettering is texture stage (§20).
    B.box("GG_OrderHereSurface", (0.50, 0.03, 0.26),
          (2.72, B.FRONT_Y - 0.03, 2.06), mats["white"], signage)
    B.box("GG_PickUpHereSurface", (0.50, 0.03, 0.26),
          (-2.72, B.FRONT_Y - 0.03, 2.06), mats["white"], signage)


def add_lighting_fixtures(groups, mats):
    """§18: visible hardware only. No emission is baked in - §19 keeps that for
    materials and game lighting, so these stay plain meshes plus anchors."""
    fixtures = blockout.collection("GG_LightingFixtures", bpy.data.collections["GREEK_GYROS_MASTER"])
    anchors = groups["anchors"]
    lens = mats["lens"]

    B.box("GG_LightFixture_A_CounterStrip", (5.70, 0.13, 0.07),
          (0.0, B.FRONT_Y - 0.24, B.OPENING_TOP - 0.05), mats["dark"], fixtures)
    B.box("GG_LightFixture_A_CounterLens", (5.56, 0.10, 0.03),
          (0.0, B.FRONT_Y - 0.24, B.OPENING_TOP - 0.09), lens, fixtures)
    for index, y in enumerate((-0.30, 0.62), start=1):
        B.box(f"GG_LightFixture_B_Ceiling_{index:02d}", (4.70, 0.17, 0.08),
              (-0.30, y, B.BODY_TOP - 0.14), mats["dark"], fixtures)
        B.box(f"GG_LightFixture_B_CeilingLens_{index:02d}", (4.56, 0.13, 0.03),
              (-0.30, y, B.BODY_TOP - 0.19), lens, fixtures)

    # Authored light anchors, the same pattern the Cass Art interior uses.
    blockout.empty("GG_LightAnchor_Counter", (0.0, B.FRONT_Y - 0.30, B.OPENING_TOP - 0.14),
                   anchors, "SPHERE", 0.22)
    blockout.empty("GG_LightAnchor_Interior_A", (-1.60, 0.20, B.BODY_TOP - 0.28),
                   anchors, "SPHERE", 0.22)
    blockout.empty("GG_LightAnchor_Interior_B", (1.60, 0.20, B.BODY_TOP - 0.28),
                   anchors, "SPHERE", 0.22)
    blockout.empty("GG_LightAnchor_Fascia", (0.0, B.SIGN_FACE_Y - 0.20, (B.STRIP_TOP + B.SIGN_TOP) / 2),
                   anchors, "SPHERE", 0.22)
    return fixtures


# --- Scene, export, renders ------------------------------------------------

def add_detail_cameras(groups):
    cams = groups["cameras"]
    return (
        blockout.camera("CAMERA_01_FrontElevation", (0.0, -10.5, 1.95), (0.0, B.FRONT_Y, 1.80), 42, cams),
        blockout.camera("CAMERA_02_ThreeQuarterStreet", (7.4, -8.2, 2.70), (-0.3, -0.30, 1.70), 40, cams),
        blockout.camera("CAMERA_03_SideAndServiceDoor", (11.0, -3.40, 2.30), (1.2, 0.30, 1.55), 44, cams),
        blockout.camera("CAMERA_04_CounterEyeLevel", (0.80, -5.60, 1.62), (0.20, 0.20, 1.72), 28, cams),
        blockout.camera("CAMERA_05_InteriorOverCounter", (-0.90, -4.60, 1.88), (0.05, 0.95, 1.58), 38, cams),
    )


def light_the_review(groups):
    """Extra review fill so the deepened interior reads in the clay renders."""
    blockout.area_light("GG_Review_InteriorRear", (0.0, -0.60, 2.22), (0.0, 1.15, 1.55),
                        26, 2.2, groups["lights"])
    blockout.area_light("GG_Review_CounterFill", (0.0, -4.20, 2.30), (0.0, -0.40, 1.45),
                        70, 3.0, groups["lights"])


def apply_transforms_and_normals():
    """§31: applied transforms and outward normals before export."""
    bpy.ops.object.select_all(action="DESELECT")
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    for obj in meshes:
        obj.select_set(True)
    if meshes:
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")


def purge_unused_materials():
    """§31: no unused materials travel with the asset."""
    removed = []
    for mat in list(bpy.data.materials):
        if mat.users == 0:
            removed.append(mat.name)
            bpy.data.materials.remove(mat)
    if removed:
        print(f"Removed unused materials: {removed}")


def validate():
    required = (
        "GG_SideDoor_Panel", "GG_ExtractionCowl", "GG_MenuBoard_A", "GG_MenuBoard_C",
        "GG_RegisterCounter", "GG_Register_Screen", "GG_CounterGuard_Glass",
        "GG_LightFixture_A_CounterStrip", "GG_LightFixture_B_Ceiling_01",
        "GG_Rotisserie_Spit", "GG_SignMountRail", "GG_CornerPost_FrontLeft",
        "GG_OrderAnchor", "GG_LightAnchor_Fascia",
    )
    missing = [name for name in required if bpy.data.objects.get(name) is None]
    if missing:
        raise RuntimeError(f"Missing second-pass objects: {missing}")
    stray = [obj.name for obj in bpy.data.objects if obj.name.startswith(("Cube", "Cylinder", "Cone"))]
    if stray:
        raise RuntimeError(f"Unnamed primitives left in scene: {stray}")
    for mat in bpy.data.materials:
        if not mat.name.startswith("MAT_GG_"):
            raise RuntimeError(f"Unexpected material name: {mat.name}")
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    exported = [obj for obj in meshes if not obj.name.startswith("GG_Review_")]
    triangles = sum(
        sum(max(0, len(poly.vertices) - 2) for poly in obj.data.polygons) for obj in exported
    )
    print(f"Validation: {len(exported)} exported mesh objects, approximately {triangles} triangles")
    print(f"Validation: envelope {B.BODY_W:.2f} x {B.BODY_D:.2f} x {B.CAP_TOP:.2f} m, frontage faces -Y")


def export_glb():
    """§§24, 31: kiosk and its own props only - no pavement, figures or context."""
    GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
    excluded = {"GG_BlockoutReviewOnly", "GG_BlockoutCameras", "GG_BlockoutLights"}
    bpy.ops.object.select_all(action="DESELECT")
    export_objects = [
        obj
        for obj in bpy.data.objects
        if obj.type not in {"CAMERA", "LIGHT"}
        and not any(group.name in excluded for group in obj.users_collection)
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
    print(f"Exported runtime model: {GLB_PATH}")


def render_reviews(cameras):
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    names = (
        "01-front-elevation.png",
        "02-three-quarter-street.png",
        "03-side-and-service-door.png",
        "04-counter-eye-level.png",
        "05-interior-over-counter.png",
    )
    scene = bpy.context.scene
    for camera_obj, filename in zip(cameras, names):
        scene.camera = camera_obj
        scene.render.resolution_x = 1200
        scene.render.resolution_y = 900
        scene.render.filepath = str(RENDER_DIR / filename)
        bpy.ops.render.render(write_still=True)
        print(f"Rendered {scene.render.filepath}")


def remove_blockout_cameras():
    """The second pass authors its own review set, so §31 leaves no stale cameras."""
    for obj in list(bpy.data.objects):
        if obj.type == "CAMERA" and obj.name[:8] in {"CAMERA_A", "CAMERA_B", "CAMERA_C", "CAMERA_D"}:
            bpy.data.objects.remove(obj, do_unlink=True)


def main():
    _blockout_cameras, layout = blockout.build_scene()
    remove_blockout_cameras()
    groups = layout["groups"]
    mats = dict(layout["mats"])
    mats["glass"] = glass_material("MAT_GG_Glass_PLACEHOLDER")
    mats["lens"] = blockout.material("MAT_GG_FixtureLens_PLACEHOLDER", (0.88, 0.88, 0.85), 0.28)

    add_framing_and_panels(groups, mats)
    add_sign_mounting(groups, mats)
    add_roof_services(groups, mats)
    add_side_service(groups, mats)
    add_interior(groups, mats)
    add_counter_and_register(groups, mats)
    add_lighting_fixtures(groups, mats)
    light_the_review(groups)
    cameras = add_detail_cameras(groups)

    apply_transforms_and_normals()
    purge_unused_materials()
    validate()

    note = bpy.data.texts.get("GREEK_GYROS_BLOCKOUT_NOTES")
    if note is not None:
        bpy.data.texts.remove(note)
    note = bpy.data.texts.new("GREEK_GYROS_NOTES")
    note.write(
        "SECOND PASS - GEOMETRY ONLY (see 15_Greek_Gyros.txt SS30-31)\n"
        f"Envelope {B.BODY_W:.2f} m wide x {B.BODY_D:.2f} m deep x {B.CAP_TOP:.2f} m to the sign cap;\n"
        "sign box overhangs to 6.84 m and projects 0.48 m forward of the frontage.\n"
        "Frontage faces -Y; ground is Z=0; origin at the footprint centre; one unit is one metre.\n"
        "Added here: corner posts and panel seams, opening framing, sign mounting rails and\n"
        "brackets, roof extraction and vents, the right-hand side service door, interior\n"
        "counters/rotisserie/hood/shelving, three menu boards, the register end, the serving\n"
        "glass screen, and the fascia/counter/ceiling light fixtures.\n"
        "Still absent by instruction: every graphic and texture (wordmark, flags, menu strip,\n"
        "social icons, food, prices, diamond-plate pattern, dirt, stickers) and any baked\n"
        "emissive night lighting - SS18-19 keep that for materials and game lighting.\n"
        "GG_LightAnchor_* empties mark where those night lights should sit.\n"
    )

    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.camera = cameras[0]
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), check_existing=False)
    export_glb()
    render_reviews(cameras)
    bpy.context.scene.camera = cameras[0]
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), check_existing=False)
    print(f"Saved second-pass model: {BLEND_PATH}")


if __name__ == "__main__":
    main()
