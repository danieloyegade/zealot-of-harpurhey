"""Create the Come Through Lab architectural blockout and five clay review renders.

Deliberately a first-pass massing model per the brief in
references/architecture/come-through-lab/06_Come_Through_Lab.txt. It contains
the building envelope, brick-arch shapes, entrance, ground/upper window
rhythm, grilles, the CTL drop box, and the envelope/pencil supply holder as
distinct objects/collections -- no final textures, decals, QR code, signage
graphics, or brick coursing.

One Blender unit equals one metre. Ground = Z 0. The street elevation faces
-Y; the door sits toward -X, the two grilled ground windows step toward +X,
matching the reference photographs (84 Silk Street, Manchester).

All dimensions are inferred from the door, drop-box and window proportions
visible in the references, not surveyed -- consistent with every other
hero-location blockout in this project.
"""

import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLEND_PATH = PROJECT_ROOT / "blender" / "source" / "come_through_lab_blockout.blend"
RENDER_DIR = PROJECT_ROOT / "renders" / "come-through-lab-blockout"

# Building envelope (estimated from door/window/drop-box proportions).
WALL_THICKNESS = 0.40
SHELL_DEPTH = 6.0
SHELL_X_MIN = -3.20
SHELL_X_MAX = 2.80
GROUND_HEIGHT = 3.50
UPPER_HEIGHT = 3.40
PARAPET_HEIGHT = 0.25
TOTAL_HEIGHT = GROUND_HEIGHT + UPPER_HEIGHT + PARAPET_HEIGHT

DOOR_X = -2.55
DROPBOX_X = -1.65
SUPPLY_HOLDER_X = -1.98
WINDOW_G1_X = -0.25
WINDOW_G2_X = 1.65
UPPER_WINDOW_XS = (-2.15, -0.25, 1.65)


# ---------------------------------------------------------------------------
# Scene / collection / material helpers (pattern shared with the other
# blockout scripts in this project, e.g. createTheHiveBlockout.py).
# ---------------------------------------------------------------------------

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
        bpy.data.texts,
    ):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def make_collection(name, parent=None):
    result = bpy.data.collections.new(name)
    (parent.children if parent else bpy.context.scene.collection.children).link(result)
    return result


def make_material(name, color, roughness=0.85, metallic=0.0, alpha=1.0):
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


def box(name, dimensions, location, material, target_collection):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material:
        obj.data.materials.append(material)
    relink(obj, target_collection)
    return obj


def empty(name, location, target_collection, display="PLAIN_AXES", size=0.5):
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
    data.clip_start = 0.05
    data.clip_end = 200
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


# ---------------------------------------------------------------------------
# Arch geometry -- real curved brick-arch/door shapes rather than rectangles
# with a texture faked on top (brief section 5).
# ---------------------------------------------------------------------------

def add_arch_solid(name, x_center, y_front, depth, half_width, base_z, top_z, rise, segments, material, target_collection):
    """A solid slab with a segmental-arched top: door leaves, arch-filled voids."""
    bm = bmesh.new()
    verts = [
        bm.verts.new((x_center - half_width, y_front, base_z)),
        bm.verts.new((x_center + half_width, y_front, base_z)),
        bm.verts.new((x_center + half_width, y_front, top_z)),
    ]
    for i in range(1, segments):
        t = i / segments
        x = (x_center + half_width) - (2 * half_width) * t
        z = top_z + rise * math.sin(math.pi * t)
        verts.append(bm.verts.new((x, y_front, z)))
    verts.append(bm.verts.new((x_center - half_width, y_front, top_z)))

    face = bm.faces.new(verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ret = bmesh.ops.extrude_face_region(bm, geom=[face])
    new_verts = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=new_verts, vec=(0, depth, 0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    bm.to_mesh(mesh)
    bm.free()
    if material:
        mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    target_collection.objects.link(obj)
    return obj


def add_arch_band(name, x_center, y_front, depth, half_width, spring_z, rise, thickness, segments, material, target_collection):
    """A shallow curved voussoir band -- the visible brick arch above a window."""
    bm = bmesh.new()
    inner, outer = [], []
    for i in range(segments + 1):
        t = i / segments
        x = x_center - half_width + 2 * half_width * t
        rise_t = rise * math.sin(math.pi * t)
        inner.append(bm.verts.new((x, y_front, spring_z + rise_t)))
        outer.append(bm.verts.new((x, y_front, spring_z + rise_t + thickness)))

    faces = [bm.faces.new((inner[i], inner[i + 1], outer[i + 1], outer[i])) for i in range(segments)]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ret = bmesh.ops.extrude_face_region(bm, geom=faces)
    new_verts = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=new_verts, vec=(0, depth, 0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    bm.to_mesh(mesh)
    bm.free()
    if material:
        mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    target_collection.objects.link(obj)
    return obj


def add_grille(name, x_center, y_front, half_width, bottom_z, top_z, material, target_collection, v_bars=4, h_bars=3, bar=0.035):
    """A restrained repeated grid rather than a densely subdivided wire mesh."""
    width = half_width * 2
    height = top_z - bottom_z
    box(f"{name}_FrameTop", (width, bar, bar), (x_center, y_front, top_z), material, target_collection)
    box(f"{name}_FrameBottom", (width, bar, bar), (x_center, y_front, bottom_z), material, target_collection)
    box(f"{name}_FrameLeft", (bar, bar, height), (x_center - half_width, y_front, (top_z + bottom_z) / 2), material, target_collection)
    box(f"{name}_FrameRight", (bar, bar, height), (x_center + half_width, y_front, (top_z + bottom_z) / 2), material, target_collection)
    for i in range(1, v_bars + 1):
        x = x_center - half_width + width * i / (v_bars + 1)
        box(f"{name}_VBar_{i:02d}", (bar, bar, height), (x, y_front, (top_z + bottom_z) / 2), material, target_collection)
    for i in range(1, h_bars + 1):
        z = bottom_z + height * i / (h_bars + 1)
        box(f"{name}_HBar_{i:02d}", (width, bar, bar), (x_center, y_front, z), material, target_collection)


# ---------------------------------------------------------------------------
# Building assembly
# ---------------------------------------------------------------------------

def build_ground_window(index, x, mats, groups):
    half_w, sill_z, spring_z, rise, depth = 0.75, 0.90, 2.55, 0.30, WALL_THICKNESS
    name = f"CTL_Window_Ground{index:02d}"
    box(f"{name}_JambLeft", (0.16, 0.16, spring_z - sill_z), (x - half_w, 0.08, (sill_z + spring_z) / 2), mats["stone"], groups["windows"])
    box(f"{name}_JambRight", (0.16, 0.16, spring_z - sill_z), (x + half_w, 0.08, (sill_z + spring_z) / 2), mats["stone"], groups["windows"])
    glass = add_arch_solid(
        f"CTL_WindowGlass_Ground{index:02d}", x, 0.16, 0.05, half_w - 0.06, sill_z, spring_z, rise * 0.9, 10, mats["glass"], groups["windows"]
    )
    add_arch_band(f"{name}_ArchVoussoirs", x, -0.02, 0.30, half_w + 0.12, spring_z, rise, 0.24, 9, mats["arch_brick"], groups["windows"])
    box(f"{name}_Sill", (0.22, half_w * 2 + 0.30, 0.12), (x, -0.11, sill_z - 0.06), mats["stone"], groups["windows"])
    add_grille(f"CTL_Grille_Ground{index:02d}", x, -0.10, half_w - 0.02, sill_z + 0.02, spring_z - 0.02, mats["metal"], groups["grilles"])
    return glass


def build_upper_window(index, x, mats, groups):
    half_w, sill_z, height = 0.55, 3.85, 1.55
    top_z = sill_z + height
    name = f"CTL_Window_Upper_TypeA_{index:02d}"
    box(f"{name}_Frame", (0.14, half_w * 2 + 0.16, height + 0.14), (x, 0.05, sill_z + height / 2), mats["frame"], groups["windows"])
    box(f"{name}_Glass", (0.06, half_w * 2, height), (x, 0.12, sill_z + height / 2), mats["glass"], groups["windows"])
    box(f"{name}_MuntinV", (0.05, 0.05, height), (x, 0.10, sill_z + height / 2), mats["frame"], groups["windows"])
    box(f"{name}_MuntinH", (0.05, half_w * 2, 0.05), (x, 0.10, sill_z + height / 2), mats["frame"], groups["windows"])
    box(f"{name}_Sill", (0.18, half_w * 2 + 0.22, 0.10), (x, -0.09, sill_z - 0.05), mats["stone"], groups["windows"])


def build_entrance(mats, groups):
    half_w, sill_z, spring_z, rise = 0.55, 0.0, 1.95, 0.35
    door_top = sill_z + spring_z + rise

    box("CTL_DoorFrame_JambLeft", (0.22, 0.16, spring_z), (DOOR_X - half_w, 0.08, spring_z / 2), mats["stone"], groups["entrance"])
    box("CTL_DoorFrame_JambRight", (0.22, 0.16, spring_z), (DOOR_X + half_w, 0.08, spring_z / 2), mats["stone"], groups["entrance"])
    add_arch_band("CTL_DoorFrame_Arch", DOOR_X, -0.02, 0.30, half_w + 0.10, spring_z, rise, 0.20, 9, mats["arch_brick"], groups["entrance"])

    door = add_arch_solid(
        "CTL_Door", DOOR_X, 0.10, 0.07, half_w - 0.06, sill_z + 0.02, spring_z, rise * 0.92, 10, mats["wood"], groups["entrance"]
    )

    # Heavy projecting stone lintel + decorative corbel blocks (brief section 6).
    box("CTL_StoneSurround_Lintel", (0.28, half_w * 2 + 0.55, 0.30), (DOOR_X, -0.12, door_top + 0.18), mats["stone"], groups["entrance"])
    box("CTL_StoneSurround_CorbelLeft", (0.24, 0.30, 0.22), (DOOR_X - half_w - 0.10, -0.10, door_top + 0.05), mats["stone"], groups["entrance"])
    box("CTL_StoneSurround_CorbelRight", (0.24, 0.30, 0.22), (DOOR_X + half_w + 0.10, -0.10, door_top + 0.05), mats["stone"], groups["entrance"])

    box("CTL_DoorHandle", (0.05, 0.05, 0.55), (DOOR_X + half_w * 0.35, 0.06, 1.05), mats["metal"], groups["entrance"])
    box("CTL_LetterSlot", (0.03, 0.28, 0.05), (DOOR_X, 0.06, 1.35), mats["metal"], groups["entrance"])
    box("CTL_KickPlate", (0.02, half_w * 2 - 0.12, 0.28), (DOOR_X, 0.135, 0.16), mats["metal"], groups["entrance"])

    empty("CTL_EntranceTriggerAnchor", (DOOR_X, -1.2, 1.0), groups["anchors"], "ARROWS", 0.5)
    return door


def build_dropbox(mats, groups):
    body_w, body_h, body_d = 0.50, 0.78, 0.26
    center_z = 1.35
    y_face = -0.06

    box("CTL_DropBox_Body", (body_d, body_w, body_h), (DROPBOX_X, y_face, center_z), mats["dropbox"], groups["dropbox"])
    box("CTL_DropBox_Lid", (body_d + 0.05, body_w + 0.05, 0.07), (DROPBOX_X, y_face - 0.01, center_z + body_h / 2 + 0.02), mats["dropbox"], groups["dropbox"])
    box("CTL_DropBox_Door", (0.03, body_w - 0.06, body_h - 0.30), (DROPBOX_X, y_face - body_d / 2 - 0.015, center_z - 0.05), mats["dropbox"], groups["dropbox"])
    box("CTL_DropBox_Lock", (0.02, 0.05, 0.05), (DROPBOX_X - 0.15, y_face - body_d / 2 - 0.03, center_z - 0.05), mats["metal"], groups["dropbox"])

    # Dedicated flat surfaces for future logo/instructions/text decals -- no
    # geometry for the QR code or lettering itself (brief section 15).
    box("CTL_DropBox_LogoSurface", (0.01, body_w - 0.10, 0.10), (DROPBOX_X, y_face - body_d / 2 - 0.02, center_z + 0.22), mats["metal"], groups["dropbox"])
    box("CTL_DropBox_InstructionsSurface", (0.01, body_w - 0.10, 0.28), (DROPBOX_X, y_face - body_d / 2 - 0.02, center_z + 0.02), mats["metal"], groups["dropbox"])
    box("CTL_DropBox_TextSurface", (0.01, body_w - 0.10, 0.12), (DROPBOX_X, y_face - body_d / 2 - 0.02, center_z - 0.22), mats["metal"], groups["dropbox"])

    empty("CTL_DropBox_InteractAnchor", (DROPBOX_X, y_face - 0.9, 1.05), groups["anchors"], "ARROWS", 0.4)


def build_supply_holder(mats, groups):
    x, center_z = SUPPLY_HOLDER_X, 1.55
    box("CTL_SupplyHolder_Backplate", (0.03, 0.24, 0.38), (x, -0.02, center_z), mats["metal"], groups["supply"])
    box("CTL_SupplyHolder_Body", (0.11, 0.22, 0.34), (x, -0.09, center_z - 0.01), mats["glass"], groups["supply"])
    box("CTL_SupplyHolder_Divider", (0.10, 0.20, 0.015), (x, -0.09, center_z + 0.02), mats["metal"], groups["supply"])


def build_props(mats, groups):
    box("CTL_FilmEnvelope", (0.008, 0.16, 0.11), (SUPPLY_HOLDER_X, -0.06, 1.62), mats["paper"], groups["props"])
    box("CTL_Pencil", (0.008, 0.008, 0.19), (SUPPLY_HOLDER_X + 0.03, -0.04, 1.47), mats["wood"], groups["props"])


def build_blockout():
    clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"

    master = make_collection("CTL_BUILDING_MASTER")
    groups = {
        "shell": make_collection("CTL_ExteriorShell", master),
        "entrance": make_collection("CTL_Entrance", master),
        "windows": make_collection("CTL_Windows", master),
        "grilles": make_collection("CTL_Grilles", master),
        "fixtures": make_collection("CTL_WallFixtures", master),
        "anchors": make_collection("CTL_InteractionAnchors", master),
        "context": make_collection("CTL_BlockoutContext", master),
        "cameras": make_collection("CTL_BlockoutCameras", master),
        "lights": make_collection("CTL_BlockoutLights", master),
    }
    dropbox_collection = make_collection("CTL_DROPBOX_MASTER")
    supply_collection = make_collection("CTL_SUPPLY_HOLDER_MASTER")
    props_collection = make_collection("CTL_DropoffProps", supply_collection)
    groups["dropbox"] = dropbox_collection
    groups["supply"] = supply_collection
    groups["props"] = props_collection

    mats = {
        "brick": make_material("MAT_CTL_Brick_PLACEHOLDER", (0.40, 0.16, 0.12), 0.92),
        "arch_brick": make_material("MAT_CTL_ArchBrick_PLACEHOLDER", (0.22, 0.10, 0.09), 0.90),
        "stone": make_material("MAT_CTL_Stone_PLACEHOLDER", (0.62, 0.57, 0.46), 0.85),
        "wood": make_material("MAT_CTL_Wood_PLACEHOLDER", (0.28, 0.18, 0.10), 0.80),
        "metal": make_material("MAT_CTL_Metal_PLACEHOLDER", (0.05, 0.05, 0.06), 0.55, 0.35),
        "frame": make_material("MAT_CTL_WindowFrame_PLACEHOLDER", (0.33, 0.38, 0.40), 0.65, 0.10),
        "glass": make_material("MAT_CTL_Glass_PLACEHOLDER", (0.10, 0.14, 0.17), 0.25, 0.05, alpha=0.55),
        "dropbox": make_material("MAT_CTL_DropBox_PLACEHOLDER", (0.03, 0.03, 0.035), 0.45, 0.25),
        "paper": make_material("MAT_CTL_Paper_PLACEHOLDER", (0.85, 0.82, 0.72), 0.95),
        "ground": make_material("MAT_CTL_Ground_PLACEHOLDER", (0.11, 0.11, 0.115), 1.0),
    }

    shell_width = SHELL_X_MAX - SHELL_X_MIN
    shell_center_x = (SHELL_X_MIN + SHELL_X_MAX) / 2

    box("CTL_BuildingShell_Ground", (shell_width, SHELL_DEPTH, GROUND_HEIGHT), (shell_center_x, SHELL_DEPTH / 2, GROUND_HEIGHT / 2), mats["brick"], groups["shell"])
    box(
        "CTL_BuildingShell_Upper",
        (shell_width, SHELL_DEPTH, UPPER_HEIGHT),
        (shell_center_x, SHELL_DEPTH / 2, GROUND_HEIGHT + UPPER_HEIGHT / 2),
        mats["brick"],
        groups["shell"],
    )
    box(
        "CTL_HorizontalBand_FloorDivide",
        (shell_width + 0.05, 0.10, 0.12),
        (shell_center_x, -0.03, GROUND_HEIGHT),
        mats["arch_brick"],
        groups["shell"],
    )
    box(
        "CTL_Parapet_Cap",
        (shell_width + 0.10, SHELL_DEPTH + 0.10, PARAPET_HEIGHT),
        (shell_center_x, SHELL_DEPTH / 2, TOTAL_HEIGHT - PARAPET_HEIGHT / 2),
        mats["stone"],
        groups["shell"],
    )

    build_entrance(mats, groups)
    box("CTL_Address84", (0.03, 0.55, 0.42), (-1.55, -0.02, 2.95), mats["metal"], groups["entrance"])

    build_ground_window(1, WINDOW_G1_X, mats, groups)
    build_ground_window(2, WINDOW_G2_X, mats, groups)
    for index, x in enumerate(UPPER_WINDOW_XS, start=1):
        build_upper_window(index, x, mats, groups)

    build_dropbox(mats, groups)
    build_supply_holder(mats, groups)
    build_props(mats, groups)

    box("CTL_WallFixture_AlarmBox", (0.06, 0.16, 0.16), (-2.05, -0.03, 2.75), mats["frame"], groups["fixtures"])
    box("CTL_WallFixture_Conduit", (0.05, 0.05, TOTAL_HEIGHT - 0.3), (0.55, -0.03, TOTAL_HEIGHT / 2), mats["metal"], groups["fixtures"])

    box("CTL_Context_Pavement", (SHELL_X_MAX - SHELL_X_MIN + 6.0, 3.0, 0.12), (shell_center_x, -1.5, -0.06), mats["ground"], groups["context"])
    box("CTL_Context_Ground", (30.0, 24.0, 0.15), (shell_center_x, 6.0, -0.15), mats["ground"], groups["context"])

    cameras = [
        camera("CAMERA_A_StraightOnEntrance", (-0.2, -9.0, 3.3), (-0.2, 0.0, 3.3), 40, groups["cameras"]),
        camera("CAMERA_B_WiderThreeQuarterStreet", (-4.0, -11.0, 4.2), (-0.2, 1.5, 3.0), 38, groups["cameras"]),
        camera("CAMERA_C_LowAngleUpperFloors", (-1.0, -4.2, 1.0), (-0.2, 1.5, 6.8), 30, groups["cameras"]),
        camera("CAMERA_D_DoorDropboxWindows", (-0.5, -4.5, 1.4), (-0.5, 0.0, 1.4), 32, groups["cameras"]),
        camera("CAMERA_E_DropboxIndependent", (-1.65, -1.6, 1.35), (-1.65, 0.0, 1.35), 45, groups["cameras"]),
    ]

    area_light("CTL_Key", (-9.0, -9.0, 9.0), 3600, 8.0, (0.0, 1.0, 3.0), groups["lights"])
    area_light("CTL_Fill", (7.0, -6.0, 6.0), 1800, 7.0, (0.0, 1.0, 3.0), groups["lights"])
    area_light("CTL_Rim", (0.0, 8.0, 8.0), 1600, 6.0, (0.0, 2.0, 4.5), groups["lights"])

    world = scene.world or bpy.data.worlds.new("CTL_BlockoutWorld")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.10, 0.11, 0.13, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.5

    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.15
    scene.camera = cameras[0]

    note = bpy.data.texts.new("CTL_BLOCKOUT_NOTES")
    note.write(
        "FIRST PASS / REVIEW HOLD\n"
        "Geometry-only blockout for 84 Silk Street (Come Through Lab), inferred\n"
        "from door/window/drop-box proportions, not surveyed dimensions.\n"
        "Frontage bay only -- door + 2 ground windows + 3 upper windows -- per\n"
        "brief section 3 (do not fuse adjacent buildings or the full street).\n"
        "No balcony massing added: not visible in the immediate CTL frontage\n"
        "references: those appear further down the same building on Silk St.\n"
        "One unit = one metre. Street faces -Y. Ground level Z=0.\n"
        "Individual bricks, mortar, QR code, logos, wood grain and weathering\n"
        "are deferred to the second geometry/texture pass.\n"
    )
    return cameras


def render_reviews(cameras):
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    names = (
        "view-a-straight-on-entrance.png",
        "view-b-wider-three-quarter-street.png",
        "view-c-low-angle-upper-floors.png",
        "view-d-door-dropbox-windows.png",
        "view-e-dropbox-independent.png",
    )
    scene = bpy.context.scene
    for camera_obj, filename in zip(cameras, names):
        scene.camera = camera_obj
        scene.render.filepath = str(RENDER_DIR / filename)
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    cameras = build_blockout()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    render_reviews(cameras)
    bpy.context.scene.camera = cameras[0]
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    print(f"Saved {BLEND_PATH}")
    print(f"Rendered review images to {RENDER_DIR}")
