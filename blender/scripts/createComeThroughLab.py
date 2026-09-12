"""Second geometry pass for Come Through Lab (84 Silk Street, Manchester).

Refines the approved blockout (createComeThroughLabBlockout.py) per brief
section 31: detailed entrance surround, plank-rhythm door, raised address-84
digits, segmented brick-arch voussoirs, refined window framing/hoods, a
mounting-bracket grille read, drop-box lock/hinge detail, and a rounded
supply holder -- still geometry only, no textures/decals/QR code/wood grain
per section 31's own "do not texture yet."

Object naming, collection hierarchy, dimensions and camera placement are
kept identical to the blockout wherever the brief doesn't call for a shape
change, so the two stages stay directly comparable (brief section 32: compare
against every reference and against the prior pass).

Exports three separate GLBs, matching section 13's requirement that the drop
box (and the supply holder) never be permanently fused into the building
mesh:

- public/assets/models/come_through_lab.glb   -- building only
- public/assets/models/ctl_dropbox.glb         -- drop box, independently placeable
- public/assets/models/ctl_dropoff_props.glb   -- supply holder + envelope + pencil
"""

import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLEND_PATH = PROJECT_ROOT / "blender" / "source" / "come_through_lab.blend"
MODELS_DIR = PROJECT_ROOT / "public" / "assets" / "models"
BUILDING_GLB = MODELS_DIR / "come_through_lab.glb"
DROPBOX_GLB = MODELS_DIR / "ctl_dropbox.glb"
PROPS_GLB = MODELS_DIR / "ctl_dropoff_props.glb"
RENDER_DIR = PROJECT_ROOT / "renders" / "come-through-lab"

# Building envelope inferred from the full reference set.  The immediate CTL
# frontage is retained at the left; the first projecting balcony bay visible
# in the wider photographs occupies the extension to the right.
WALL_THICKNESS = 0.40
SHELL_DEPTH = 6.0
SHELL_X_MIN = -3.20
# Extended right-hand bay per review: the brief's frontage bay ended flush
# with the second ground window; Daniel asked for it to continue past that
# window by the same span as the whole original bay (left edge to the second
# window, 4.85 m), leaving blank brick wide enough for the graffiti visible
# in the reference photo to sit later as a decal/texture.
WINDOW_G2_X = 1.65
SHELL_X_MAX = WINDOW_G2_X + (WINDOW_G2_X - SHELL_X_MIN)
GROUND_HEIGHT = 3.50
UPPER_HEIGHT = 3.40
PARAPET_HEIGHT = 0.25
TOTAL_HEIGHT = GROUND_HEIGHT + UPPER_HEIGHT + PARAPET_HEIGHT

DOOR_X = -2.55
DROPBOX_X = -1.65
SUPPLY_HOLDER_X = -1.98
# Leaflet holder rides on the drop box's left edge in the reference photo,
# within the box's own height rather than above it.
SUPPLY_HOLDER_Z = 1.28
WINDOW_G1_X = -0.25
UPPER_WINDOW_XS = (DOOR_X, -0.25, 1.65)
BALCONY_WINDOW_XS = (3.65, 5.35)


# ---------------------------------------------------------------------------
# Scene / collection / material / primitive helpers.
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


def box(name, dimensions, location, material, target_collection, rotation=None, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    obj.dimensions = dimensions
    if rotation:
        obj.rotation_euler = rotation
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material:
        obj.data.materials.append(material)
    if bevel:
        modifier = obj.modifiers.new("DetailBevel", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
        modifier.limit_method = "ANGLE"
    relink(obj, target_collection)
    return obj


def add_cylinder(name, radius, depth, location, material, target_collection, rotation=None, vertices=16):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, vertices=vertices, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    if rotation:
        obj.rotation_euler = rotation
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material:
        obj.data.materials.append(material)
    relink(obj, target_collection)
    return obj


def add_cone(name, radius, depth, location, material, target_collection, rotation=None, vertices=6):
    bpy.ops.mesh.primitive_cone_add(radius1=radius, depth=depth, vertices=vertices, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    if rotation:
        obj.rotation_euler = rotation
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material:
        obj.data.materials.append(material)
    relink(obj, target_collection)
    return obj


def add_text(name, body, location, size, depth, material, target_collection):
    """Raised facade lettering converted to mesh for reliable GLB export."""
    bpy.ops.object.text_add(location=location, rotation=(math.radians(90), 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Curve"
    obj.data.body = body
    obj.data.align_x = "CENTER"
    obj.data.align_y = "CENTER"
    obj.data.size = size
    obj.data.extrude = depth
    obj.data.bevel_depth = 0.008
    obj.data.bevel_resolution = 1
    font_path = Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")
    if font_path.exists():
        obj.data.font = bpy.data.fonts.load(str(font_path), check_existing=True)
    obj.data.materials.append(material)
    relink(obj, target_collection)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    obj.data.name = f"{name}_Mesh"
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


def collect_objects(collection):
    objects = list(collection.objects)
    for child in collection.children:
        objects.extend(collect_objects(child))
    return objects


# ---------------------------------------------------------------------------
# Arch geometry.
# ---------------------------------------------------------------------------

def add_arch_solid(name, x_center, y_front, depth, half_width, base_z, top_z, rise, segments, material, target_collection):
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


def add_arch_voussoir_joints(name_prefix, x_center, y_front, half_width, spring_z, rise, thickness, count, material, target_collection):
    """Small radial ticks across the arch band suggesting individual voussoir
    blocks -- a geometry-level nod to the brief's alternating-brick arch
    rhythm (section 4/24) without modelling individual bricks."""
    for i in range(1, count):
        t = i / count
        x = x_center - half_width + 2 * half_width * t
        z = spring_z + rise * math.sin(math.pi * t)
        slope = rise * math.pi / (2 * half_width) * math.cos(math.pi * t)
        angle = math.atan(slope)
        box(
            f"{name_prefix}_Joint_{i:02d}",
            (0.018, 0.02, thickness * 1.05),
            (x, y_front - 0.006, z + thickness / 2),
            material,
            target_collection,
            rotation=(0, angle, 0),
        )


def add_grille(name, x_center, y_front, half_width, bottom_z, top_z, material, target_collection, v_bars=17, h_bars=10, bar=0.012):
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
    # Standoff brackets at the four corners -- the mounting relationship to
    # the facade called out in brief section 10.
    for corner_x in (x_center - half_width, x_center + half_width):
        for corner_z in (bottom_z, top_z):
            box(f"{name}_Bracket_{corner_x:.2f}_{corner_z:.2f}", (0.045, 0.10, 0.045), (corner_x, y_front + 0.05, corner_z), material, target_collection)


# ---------------------------------------------------------------------------
# Building assembly.
# ---------------------------------------------------------------------------

def build_facade_shell(mats, groups):
    """Build a deep shell plus a thin, opening-aware street facade.

    The previous model used one solid box at the street plane, which occluded
    every recessed door and pane.  These panels leave genuine apertures while
    the deeper rear shell supplies wall thickness and interior darkness.
    """
    width = SHELL_X_MAX - SHELL_X_MIN
    center_x = (SHELL_X_MIN + SHELL_X_MAX) / 2
    rear_front = 0.34
    box(
        "CTL_BuildingShell_Rear",
        (width, SHELL_DEPTH - rear_front, TOTAL_HEIGHT - PARAPET_HEIGHT),
        (center_x, rear_front + (SHELL_DEPTH - rear_front) / 2, (TOTAL_HEIGHT - PARAPET_HEIGHT) / 2),
        mats["brick"],
        groups["shell"],
    )

    def band(name, bottom, top, openings):
        intervals = sorted((max(SHELL_X_MIN, left), min(SHELL_X_MAX, right)) for left, right in openings)
        cursor = SHELL_X_MIN
        part = 1
        for left, right in intervals:
            if left > cursor:
                box(f"{name}_{part:02d}", (left - cursor, rear_front, top - bottom), ((cursor + left) / 2, rear_front / 2, (bottom + top) / 2), mats["brick"], groups["shell"])
                part += 1
            cursor = max(cursor, right)
        if cursor < SHELL_X_MAX:
            box(f"{name}_{part:02d}", (SHELL_X_MAX - cursor, rear_front, top - bottom), ((cursor + SHELL_X_MAX) / 2, rear_front / 2, (bottom + top) / 2), mats["brick"], groups["shell"])

    door_opening = (DOOR_X - 0.62, DOOR_X + 0.62)
    ground_openings = [(x - 0.82, x + 0.82) for x in (WINDOW_G1_X, WINDOW_G2_X, *BALCONY_WINDOW_XS)]
    upper_openings = [(x - 0.63, x + 0.63) for x in (*UPPER_WINDOW_XS, *BALCONY_WINDOW_XS)]

    band("CTL_Facade_Base", 0.0, 0.82, [door_opening])
    band("CTL_Facade_GroundOpenings", 0.82, 2.88, [door_opening, *ground_openings])
    band("CTL_Facade_GroundHead", 2.88, GROUND_HEIGHT, [])
    band("CTL_Facade_UpperApron", GROUND_HEIGHT, 3.82, [])
    band("CTL_Facade_UpperOpenings", 3.82, 5.62, upper_openings)
    band("CTL_Facade_UpperHead", 5.62, TOTAL_HEIGHT - PARAPET_HEIGHT, [])

    box("CTL_HorizontalBand_FloorDivide", (width + 0.05, 0.10, 0.12), (center_x, -0.03, GROUND_HEIGHT), mats["arch_brick"], groups["shell"])
    box("CTL_Parapet_Cap", (width + 0.10, SHELL_DEPTH + 0.10, PARAPET_HEIGHT), (center_x, SHELL_DEPTH / 2, TOTAL_HEIGHT - PARAPET_HEIGHT / 2), mats["stone"], groups["shell"], bevel=0.02)

def build_ground_window(index, x, mats, groups):
    half_w, sill_z, spring_z, rise, depth = 0.75, 0.90, 2.55, 0.30, WALL_THICKNESS
    name = f"CTL_Window_Ground{index:02d}"
    box(f"{name}_JambLeft", (0.16, 0.16, spring_z - sill_z), (x - half_w, 0.08, (sill_z + spring_z) / 2), mats["brick"], groups["windows"])
    box(f"{name}_JambRight", (0.16, 0.16, spring_z - sill_z), (x + half_w, 0.08, (sill_z + spring_z) / 2), mats["brick"], groups["windows"])
    glass = add_arch_solid(
        f"CTL_WindowGlass_Ground{index:02d}", x, 0.16, 0.05, half_w - 0.06, sill_z, spring_z, rise * 0.9, 14, mats["glass"], groups["windows"]
    )
    add_arch_band(f"{name}_ArchVoussoirs", x, -0.02, 0.30, half_w + 0.12, spring_z, rise, 0.24, 14, mats["arch_brick"], groups["windows"])
    add_arch_voussoir_joints(f"{name}_ArchVoussoirs", x, -0.02, half_w + 0.12, spring_z, rise, 0.24, 7, mats["brick"], groups["windows"])

    # Impost course at the springline -- a real stone band the arch actually
    # rests on, rather than voussoirs sitting straight on the brick jambs.
    box(f"{name}_Impost", (half_w * 2 + 0.16, 0.08, 0.055), (x, -0.05, spring_z), mats["frame"], groups["windows"])

    # Interior sash bars visible behind the grille, so the window reads as a
    # real multi-pane sash rather than a flat dark void (brief section 9/11:
    # the window itself, not just its surround, is part of the facade rhythm).
    sash_bottom, sash_top = sill_z + 0.05, spring_z - 0.05
    sash_mid = (sash_bottom + sash_top) / 2
    box(f"{name}_SashTransom", (half_w * 2 - 0.10, 0.03, 0.04), (x, 0.155, sash_mid), mats["frame"], groups["windows"])
    for i in (1, 2, 3):
        sx = x - half_w + (half_w * 2) * i / 4
        box(f"{name}_SashMullion_{i:02d}", (0.035, 0.03, sash_top - sash_bottom), (sx, 0.155, sash_mid), mats["frame"], groups["windows"])

    box(f"{name}_Sill", (half_w * 2 + 0.30, 0.22, 0.12), (x, -0.11, sill_z - 0.06), mats["stone"], groups["windows"], bevel=0.012)
    box(f"{name}_SillLip", (half_w * 2 + 0.34, 0.05, 0.03), (x, -0.19, sill_z - 0.10), mats["stone"], groups["windows"])
    add_grille(f"CTL_Grille_Ground{index:02d}", x, -0.10, half_w - 0.02, sill_z + 0.02, spring_z - 0.02, mats["metal"], groups["grilles"])
    return glass


def build_upper_window(index, x, mats, groups):
    half_w, sill_z, height = 0.55, 3.85, 1.55
    top_z = sill_z + height
    name = f"CTL_Window_Upper_TypeA_{index:02d}"
    width = half_w * 2
    box(f"{name}_Glass", (width, 0.05, height), (x, 0.22, sill_z + height / 2), mats["glass"], groups["windows"])
    for side, frame_x in (("Left", x - half_w), ("Right", x + half_w)):
        box(f"{name}_Frame{side}", (0.075, 0.08, height + 0.10), (frame_x, 0.14, sill_z + height / 2), mats["frame"], groups["windows"], bevel=0.006)
    box(f"{name}_FrameTop", (width + 0.075, 0.08, 0.075), (x, 0.14, top_z), mats["frame"], groups["windows"])
    box(f"{name}_FrameBottom", (width + 0.075, 0.08, 0.075), (x, 0.14, sill_z), mats["frame"], groups["windows"])
    box(f"{name}_MuntinV", (0.05, 0.07, height), (x, 0.10, sill_z + height / 2), mats["frame"], groups["windows"])
    box(f"{name}_MuntinH", (width, 0.07, 0.06), (x, 0.10, sill_z + height * 0.53), mats["frame"], groups["windows"])
    box(f"{name}_Sill", (width + 0.22, 0.18, 0.10), (x, -0.09, sill_z - 0.05), mats["stone"], groups["windows"], bevel=0.010)
    add_arch_band(f"{name}_BrickArch", x, -0.015, 0.18, half_w + 0.10, top_z + 0.03, 0.12, 0.16, 12, mats["arch_brick"], groups["windows"])
    add_arch_voussoir_joints(f"{name}_BrickArch", x, -0.02, half_w + 0.10, top_z + 0.03, 0.12, 0.16, 7, mats["brick"], groups["windows"])


def build_entrance(mats, groups):
    half_w, sill_z, spring_z, rise = 0.55, 0.0, 1.95, 0.35
    door_top = sill_z + spring_z + rise

    box("CTL_DoorFrame_JambLeft", (0.22, 0.20, spring_z), (DOOR_X - half_w, 0.10, spring_z / 2), mats["brick"], groups["entrance"])
    box("CTL_DoorFrame_JambRight", (0.22, 0.20, spring_z), (DOOR_X + half_w, 0.10, spring_z / 2), mats["brick"], groups["entrance"])
    add_arch_band("CTL_DoorFrame_Arch", DOOR_X, 0.02, 0.18, half_w, spring_z, rise, 0.16, 14, mats["frame"], groups["entrance"])

    door = add_arch_solid(
        "CTL_Door", DOOR_X, 0.10, 0.07, half_w - 0.06, sill_z + 0.02, spring_z, rise * 0.92, 12, mats["wood"], groups["entrance"]
    )
    # Vertical plank rhythm as real proud geometry (brief section 7), not a texture.
    plank_count = 5
    plank_span = (half_w - 0.06) * 2 * 0.92
    for i in range(1, plank_count):
        px = DOOR_X - plank_span / 2 + plank_span * i / plank_count
        box(f"CTL_Door_PlankSeam_{i:02d}", (0.015, 0.02, spring_z - 0.10), (px, 0.065, (sill_z + spring_z) / 2), mats["wood_dark"], groups["entrance"])

    # Heavy Victorian stone entablature and ribbed capitals visible in the
    # close reference, with a broad central header rather than a thin lintel.
    box("CTL_StoneSurround_Header", (1.62, 0.30, 0.42), (DOOR_X, -0.13, door_top + 0.26), mats["stone"], groups["entrance"], bevel=0.014)
    box("CTL_StoneSurround_Cornice", (1.82, 0.38, 0.14), (DOOR_X, -0.17, door_top + 0.55), mats["stone"], groups["entrance"], bevel=0.012)
    box("CTL_StoneSurround_Cap", (1.72, 0.34, 0.10), (DOOR_X, -0.15, door_top + 0.67), mats["stone"], groups["entrance"])
    for side, capital_x in (("Left", DOOR_X - half_w - 0.10), ("Right", DOOR_X + half_w + 0.10)):
        box(f"CTL_StoneSurround_Capital{side}", (0.30, 0.32, 0.34), (capital_x, -0.12, door_top - 0.02), mats["stone"], groups["entrance"])
        for flute in (-0.07, 0.0, 0.07):
            box(f"CTL_StoneSurround_Capital{side}_Flute_{flute:+.2f}", (0.035, 0.035, 0.20), (capital_x + flute, -0.30, door_top - 0.04), mats["arch_brick"], groups["entrance"])

    box("CTL_DoorHandle", (0.05, 0.05, 0.55), (DOOR_X + half_w * 0.35, 0.06, 1.05), mats["metal"], groups["entrance"], bevel=0.01)
    box("CTL_LetterSlot", (0.28, 0.03, 0.06), (DOOR_X, 0.04, 1.35), mats["metal"], groups["entrance"])
    box("CTL_LetterSlot_Flap", (0.24, 0.015, 0.045), (DOOR_X, 0.02, 1.335), mats["metal"], groups["entrance"])
    box("CTL_KickPlate", (half_w * 2 - 0.12, 0.025, 0.28), (DOOR_X, 0.045, 0.16), mats["metal"], groups["entrance"])

    empty("CTL_EntranceTriggerAnchor", (DOOR_X, -1.2, 1.0), groups["anchors"], "ARROWS", 0.5)
    return door


def build_address_84(mats, groups):
    add_text("CTL_Address84", "84", (-1.38, -0.08, 2.92), 0.42, 0.035, mats["metal"], groups["entrance"])


def build_dropbox(mats, groups):
    # Size corrected against the straight-on reference photograph
    # (references/architecture/come-through-lab/unnamed.jpg).  Measured there,
    # the door leaf is 174 px wide and the box body 70-73 px, so the box is
    # 0.40-0.42x the leaf width and reads about 1.45 taller than wide.  Against
    # the authored 0.98 m leaf that gives 0.39 m wide by 0.57 m tall; the
    # previous 0.50 x 0.78 m body was half again too wide and dominated the
    # entrance bay.  Horizontal ratios are used because box and door sit side
    # by side at the same height and so share a scale -- vertical ratios taken
    # across the facade do not survive the photograph's perspective.  The
    # mounting height is unchanged: the bottom edge stays at 0.96 m, so only
    # the size is corrected.
    body_w, body_h, body_d = 0.39, 0.57, 0.20
    bottom_z = 0.96
    center_z = bottom_z + body_h / 2
    y_face = -0.06

    box("CTL_DropBox_Body", (body_w, body_d, body_h), (DROPBOX_X, y_face, center_z), mats["dropbox"], groups["dropbox"], bevel=0.006)
    box("CTL_DropBox_Lid", (body_w + 0.037, body_d + 0.037, 0.05), (DROPBOX_X, y_face - 0.008, center_z + body_h / 2 + 0.015), mats["dropbox"], groups["dropbox"], bevel=0.005)
    box("CTL_DropBox_Door", (body_w - 0.044, 0.03, body_h - 0.215), (DROPBOX_X, y_face - body_d / 2 - 0.015, center_z - 0.036), mats["dropbox"], groups["dropbox"])
    box("CTL_DropBox_HingeLine", (0.011, 0.02, body_h - 0.215), (DROPBOX_X - (body_w - 0.044) / 2, y_face - body_d / 2 - 0.02, center_z - 0.036), mats["metal"], groups["dropbox"])
    add_cylinder("CTL_DropBox_Lock", 0.016, 0.03, (DROPBOX_X - 0.111, y_face - body_d / 2 - 0.03, center_z - 0.036), mats["metal"], groups["dropbox"], rotation=(math.radians(90), 0, 0))

    box("CTL_DropBox_LogoSurface", (body_w - 0.074, 0.01, 0.072), (DROPBOX_X, y_face - body_d / 2 - 0.02, center_z + 0.158), mats["metal"], groups["dropbox"])
    box("CTL_DropBox_InstructionsSurface", (body_w - 0.074, 0.01, 0.201), (DROPBOX_X, y_face - body_d / 2 - 0.02, center_z + 0.014), mats["metal"], groups["dropbox"])
    box("CTL_DropBox_InstructionsBorder", (body_w - 0.059, 0.014, 0.215), (DROPBOX_X, y_face - body_d / 2 - 0.021, center_z + 0.014), mats["metal"], groups["dropbox"])
    box("CTL_DropBox_TextSurface", (body_w - 0.074, 0.01, 0.086), (DROPBOX_X, y_face - body_d / 2 - 0.02, center_z - 0.158), mats["metal"], groups["dropbox"])

    empty("CTL_DropBox_InteractAnchor", (DROPBOX_X, y_face - 0.9, 1.05), groups["anchors"], "ARROWS", 0.4)



def build_supply_holder(mats, groups):
    x, center_z = SUPPLY_HOLDER_X, SUPPLY_HOLDER_Z
    box("CTL_SupplyHolder_Backplate", (0.24, 0.03, 0.38), (x, -0.02, center_z), mats["metal"], groups["supply"])
    box("CTL_SupplyHolder_Body", (0.22, 0.11, 0.34), (x, -0.09, center_z - 0.01), mats["glass"], groups["supply"], bevel=0.012)
    box("CTL_SupplyHolder_Divider", (0.20, 0.10, 0.015), (x, -0.09, center_z + 0.02), mats["metal"], groups["supply"])
    for screw_z in (center_z + 0.16, center_z - 0.16):
        add_cylinder(f"CTL_SupplyHolder_Screw_{screw_z:.2f}", 0.010, 0.02, (x, -0.005, screw_z), mats["metal"], groups["supply"], rotation=(0, math.radians(90), 0))


def build_props(mats, groups):
    box("CTL_FilmEnvelope", (0.16, 0.008, 0.11), (SUPPLY_HOLDER_X, -0.14, SUPPLY_HOLDER_Z + 0.07), mats["paper"], groups["props"])
    box("CTL_FilmEnvelope_Flap", (0.13, 0.008, 0.03), (SUPPLY_HOLDER_X, -0.145, SUPPLY_HOLDER_Z + 0.135), mats["paper"], groups["props"], rotation=(0, math.radians(20), 0))
    add_cylinder("CTL_Pencil_Body", 0.006, 0.16, (SUPPLY_HOLDER_X + 0.06, -0.16, SUPPLY_HOLDER_Z - 0.03), mats["wood"], groups["props"], vertices=6)
    add_cone("CTL_Pencil_Tip", 0.006, 0.035, (SUPPLY_HOLDER_X + 0.06, -0.16, SUPPLY_HOLDER_Z + 0.0675), mats["wood_dark"], groups["props"], vertices=6)
    add_cylinder("CTL_Pencil_Eraser", 0.007, 0.018, (SUPPLY_HOLDER_X + 0.06, -0.16, SUPPLY_HOLDER_Z - 0.119), mats["frame"], groups["props"], vertices=6)


def build_ground_floor_extras(mats, groups):
    """Facade projections and the restrained cable/downpipe layer."""

    box("CTL_EndPier_Left", (0.18, 0.07, TOTAL_HEIGHT - 0.30), (SHELL_X_MIN + 0.10, -0.035, (TOTAL_HEIGHT - 0.30) / 2 + 0.15), mats["brick"], groups["shell"])
    box("CTL_EndPier_Right", (0.20, 0.08, TOTAL_HEIGHT - 0.30), (SHELL_X_MAX - 0.12, -0.04, (TOTAL_HEIGHT - 0.30) / 2 + 0.15), mats["brick"], groups["shell"])

    shell_width = SHELL_X_MAX - SHELL_X_MIN
    shell_center_x = (SHELL_X_MIN + SHELL_X_MAX) / 2
    box("CTL_Parapet_DripLip", (shell_width + 0.20, SHELL_DEPTH + 0.20, 0.05), (shell_center_x, SHELL_DEPTH / 2, TOTAL_HEIGHT - PARAPET_HEIGHT - 0.03), mats["stone"], groups["shell"])

    downpipe_x = SHELL_X_MAX - 0.55
    add_cylinder("CTL_Downpipe_Body", 0.045, TOTAL_HEIGHT - 0.55, (downpipe_x, -0.05, (TOTAL_HEIGHT - 0.55) / 2 + 0.25), mats["metal"], groups["fixtures"])
    box("CTL_Downpipe_Hopper", (0.16, 0.11, 0.18), (downpipe_x, -0.06, TOTAL_HEIGHT - 0.55), mats["metal"], groups["fixtures"])
    box("CTL_Downpipe_Shoe", (0.10, 0.09, 0.16), (downpipe_x, -0.045, 0.10), mats["metal"], groups["fixtures"])
    for index, bracket_z in enumerate((1.2, 3.6, 5.8)):
        box(f"CTL_Downpipe_Bracket_{index:02d}", (0.10, 0.06, 0.05), (downpipe_x, -0.075, bracket_z), mats["metal"], groups["fixtures"])

    def cable(name, x1, z1, x2, z2, y_front, radius):
        dx, dz = x2 - x1, z2 - z1
        length = math.hypot(dx, dz)
        angle = math.atan2(dx, dz)
        add_cylinder(name, radius, length, ((x1 + x2) / 2, y_front, (z1 + z2) / 2), mats["metal"], groups["fixtures"], rotation=(0, angle, 0), vertices=8)

    # The references show untidy but primarily orthogonal service runs.
    cable("CTL_WallFixture_Cable_Horizontal", -1.25, 3.08, 2.55, 3.08, -0.055, 0.010)
    cable("CTL_WallFixture_Cable_Vertical", 2.55, 3.08, 2.55, 4.10, -0.055, 0.010)


def build_balcony_section(mats, groups):
    """First projecting balcony/walkway bay visible immediately to the right."""
    center_x = sum(BALCONY_WINDOW_XS) / 2
    width = 3.65
    slab_z = 3.68
    box("CTL_Balcony_Slab", (width, 0.72, 0.16), (center_x, -0.25, slab_z), mats["stone"], groups["shell"])
    box("CTL_Balcony_Fascia", (width, 0.10, 0.26), (center_x, -0.63, slab_z - 0.02), mats["metal"], groups["shell"])

    for index, x in enumerate(BALCONY_WINDOW_XS, start=1):
        build_ground_window(index + 2, x, mats, groups)
        # Tall upper door/window modules behind the guarding.
        sill_z, height, half_w = 3.82, 1.72, 0.58
        box(f"CTL_BalconyDoor_{index:02d}_Glass", (half_w * 2, 0.05, height), (x, 0.22, sill_z + height / 2), mats["glass"], groups["windows"])
        for side, frame_x in (("Left", x - half_w), ("Right", x + half_w)):
            box(f"CTL_BalconyDoor_{index:02d}_Frame{side}", (0.07, 0.08, height), (frame_x, 0.14, sill_z + height / 2), mats["frame"], groups["windows"])
        box(f"CTL_BalconyDoor_{index:02d}_FrameTop", (half_w * 2, 0.08, 0.07), (x, 0.14, sill_z + height), mats["frame"], groups["windows"])
        box(f"CTL_BalconyDoor_{index:02d}_FrameBottom", (half_w * 2, 0.08, 0.07), (x, 0.14, sill_z), mats["frame"], groups["windows"])

    rail_z = 4.18
    for index, post_x in enumerate((center_x - width / 2, center_x, center_x + width / 2)):
        box(f"CTL_Balcony_Post_{index:02d}", (0.055, 0.055, 0.95), (post_x, -0.64, rail_z), mats["metal"], groups["shell"])
    box("CTL_Balcony_TopRail", (width, 0.07, 0.07), (center_x, -0.64, rail_z + 0.48), mats["metal"], groups["shell"])
    for index, panel_x in enumerate((center_x - width / 4, center_x + width / 4)):
        box(f"CTL_Balcony_GuardGlass_{index:02d}", (width / 2 - 0.10, 0.025, 0.78), (panel_x, -0.62, rail_z), mats["glass"], groups["shell"])

    for index, support_x in enumerate((center_x - width / 2 + 0.25, center_x + width / 2 - 0.25)):
        box(f"CTL_Balcony_Support_{index:02d}", (0.32, 0.42, 0.52), (support_x, -0.12, slab_z - 0.32), mats["stone"], groups["shell"], bevel=0.015)


def build_detail_pass():
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
        "cameras": make_collection("CTL_ReviewCameras", master),
        "lights": make_collection("CTL_ReviewLights", master),
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
        "wood_dark": make_material("MAT_CTL_WoodDark_PLACEHOLDER", (0.17, 0.10, 0.06), 0.85),
        "metal": make_material("MAT_CTL_Metal_PLACEHOLDER", (0.05, 0.05, 0.06), 0.55, 0.35),
        "frame": make_material("MAT_CTL_WindowFrame_PLACEHOLDER", (0.33, 0.38, 0.40), 0.65, 0.10),
        "glass": make_material("MAT_CTL_Glass_PLACEHOLDER", (0.10, 0.14, 0.17), 0.25, 0.05, alpha=0.55),
        "dropbox": make_material("MAT_CTL_DropBox_PLACEHOLDER", (0.03, 0.03, 0.035), 0.45, 0.25),
        "paper": make_material("MAT_CTL_Paper_PLACEHOLDER", (0.85, 0.82, 0.72), 0.95),
        "infill": make_material("MAT_CTL_InfillPanel_PLACEHOLDER", (0.34, 0.14, 0.11), 0.90),
        "ground": make_material("MAT_CTL_Ground_PLACEHOLDER", (0.11, 0.11, 0.115), 1.0),
    }

    shell_width = SHELL_X_MAX - SHELL_X_MIN
    shell_center_x = (SHELL_X_MIN + SHELL_X_MAX) / 2
    build_facade_shell(mats, groups)

    build_entrance(mats, groups)
    build_address_84(mats, groups)

    build_ground_window(1, WINDOW_G1_X, mats, groups)
    build_ground_window(2, WINDOW_G2_X, mats, groups)
    for index, x in enumerate(UPPER_WINDOW_XS, start=1):
        build_upper_window(index, x, mats, groups)
    build_balcony_section(mats, groups)

    build_dropbox(mats, groups)
    build_supply_holder(mats, groups)
    build_props(mats, groups)

    box("CTL_WallFixture_AlarmBox", (0.06, 0.16, 0.16), (-2.05, -0.03, 2.75), mats["frame"], groups["fixtures"])
    box("CTL_WallFixture_Conduit", (0.05, 0.05, TOTAL_HEIGHT - 0.3), (0.55, -0.03, TOTAL_HEIGHT / 2), mats["metal"], groups["fixtures"])

    build_ground_floor_extras(mats, groups)

    box("CTL_Context_Pavement", (SHELL_X_MAX - SHELL_X_MIN + 6.0, 3.0, 0.12), (shell_center_x, -1.5, -0.06), mats["ground"], groups["context"])
    box("CTL_Context_Ground", (30.0, 24.0, 0.15), (shell_center_x, 6.0, -0.15), mats["ground"], groups["context"])

    # Same five camera placements as the approved blockout, for a direct
    # before/after comparison per brief section 32 -- except Camera B, backed
    # off and re-aimed to take in the newly extended right-hand bay.
    cameras = [
        camera("CAMERA_A_StraightOnEntrance", (-0.55, -10.5, 3.25), (-0.55, 0.0, 3.25), 42, groups["cameras"]),
        camera("CAMERA_B_WiderThreeQuarterStreet", (-5.0, -15.5, 4.8), (1.4, 1.2, 3.3), 34, groups["cameras"]),
        camera("CAMERA_C_LowAngleUpperFloors", (-1.0, -4.2, 1.0), (-0.2, 1.5, 6.8), 30, groups["cameras"]),
        camera("CAMERA_D_DoorDropboxWindows", (-0.7, -5.8, 1.55), (-0.7, 0.0, 1.55), 38, groups["cameras"]),
        camera("CAMERA_E_DropboxIndependent", (-1.65, -1.6, 1.35), (-1.65, 0.0, 1.35), 45, groups["cameras"]),
    ]

    area_light("CTL_Key", (-9.0, -9.0, 9.0), 3600, 8.0, (0.0, 1.0, 3.0), groups["lights"])
    area_light("CTL_Fill", (7.0, -6.0, 6.0), 1800, 7.0, (0.0, 1.0, 3.0), groups["lights"])
    area_light("CTL_Rim", (0.0, 8.0, 8.0), 1600, 6.0, (0.0, 2.0, 4.5), groups["lights"])

    world = scene.world or bpy.data.worlds.new("CTL_ReviewWorld")
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

    note = bpy.data.texts.new("CTL_DETAIL_NOTES")
    note.write(
        "REFERENCE-CORRECTION PASS -- geometry only; no textures, decals, QR\n"
        "code, graffiti, brick maps or wood grain. The street facade is now\n"
        "built around genuine recessed apertures instead of a solid wall that\n"
        "occluded the door and glazing. Width/depth axes are corrected on all\n"
        "frames, sills, drop-box panels and supply props. The entrance follows\n"
        "the photographed arched timber door and heavy stone entablature; 84\n"
        "uses raised numeral geometry; security grilles use the dense reference\n"
        "rhythm. The extension now contains the first projecting balcony bay\n"
        "visible in the wider references rather than unsupported blank wall.\n"
    )

    return groups, cameras


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


def export_glb(objects, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
    )


def triangle_count(objects):
    return sum(
        sum(max(0, len(polygon.vertices) - 2) for polygon in obj.data.polygons)
        for obj in objects
        if obj.type == "MESH"
    )


if __name__ == "__main__":
    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    groups, cameras = build_detail_pass()

    building_objects = (
        collect_objects(groups["shell"])
        + collect_objects(groups["entrance"])
        + collect_objects(groups["windows"])
        + collect_objects(groups["grilles"])
        + collect_objects(groups["fixtures"])
        + [bpy.data.objects["CTL_EntranceTriggerAnchor"]]
    )
    dropbox_objects = collect_objects(groups["dropbox"]) + [bpy.data.objects["CTL_DropBox_InteractAnchor"]]
    props_objects = collect_objects(groups["supply"])

    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    render_reviews(cameras)

    export_glb(building_objects, BUILDING_GLB)
    export_glb(dropbox_objects, DROPBOX_GLB)
    export_glb(props_objects, PROPS_GLB)

    bpy.context.scene.camera = cameras[0]
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

    print(f"Building triangles: {triangle_count(building_objects)}")
    print(f"Drop-box triangles: {triangle_count(dropbox_objects)}")
    print(f"Props triangles: {triangle_count(props_objects)}")
    print(f"Saved {BLEND_PATH}")
    print(f"Exported {BUILDING_GLB}")
    print(f"Exported {DROPBOX_GLB}")
    print(f"Exported {PROPS_GLB}")
    print(f"Rendered review images to {RENDER_DIR}")
