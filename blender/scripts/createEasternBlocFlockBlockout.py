"""Create the Eastern Bloc + Flok connected-corner review blockout.

This script implements only the first review gate in
references/architecture/buildings/eastern-bloc:flok/07_Eastern_Bloc_Flock.txt.
It establishes the shared building envelope, lower facade, corner turn,
Eastern Bloc entrance/window/awning, Flok arched portal/canopy, side windows,
and upper brick floors. Fine mouldings, props, final typography, graphics,
textures, weathering, interaction anchors and game integration are deferred.
"""

from math import atan2, cos, pi, radians, sin
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
BLEND_PATH = ROOT / "blender" / "source" / "eastern-bloc-flock-blockout.blend"
RENDER_DIR = ROOT / "renders" / "eastern-bloc-flock-blockout"

# Inferred from doorway, window and table scale across all supplied photos.
# The public Eastern Bloc elevation faces -Y. Flok occupies the clipped corner
# and wraps onto the +X elevation.
FRONT = ((-8.0, -4.0), (2.2, -4.0))
CORNER = ((2.2, -4.0), (4.2, -2.0))
SIDE = ((4.2, -2.0), (4.2, 5.5))
FOOTPRINT = [(-8.0, -4.0), (2.2, -4.0), (4.2, -2.0), (4.2, 5.5), (-8.0, 5.5)]

GROUND_FLOOR_TOP = 4.05
FASCIA_BOTTOM = 4.05
FASCIA_TOP = 5.20
UPPER_TOP = 10.80


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
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)
    for col in list(bpy.data.collections):
        if col.name != "Collection":
            bpy.data.collections.remove(col)
    bpy.data.collections["Collection"].name = "EASTERN_BLOC_FLOCK_MASTER"


def child_collection(name, parent=None):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(col)
    return col


def relink(obj, collection):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)
    return obj


def material(name, colour, roughness=0.78, metallic=0.0, alpha=1.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*colour, alpha)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*colour, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        mat.blend_method = "BLEND"
        mat.use_screen_refraction = True
        mat.show_transparent_back = False
    return mat


def create_materials():
    # Colour differences identify future material regions; they are intentionally
    # restrained review clay, not final surfacing.
    return {
        "upper": material("MAT_EBF_UpperBrick_PLACEHOLDER", (0.43, 0.30, 0.25)),
        "lower": material("MAT_EBF_LowerFacade_PLACEHOLDER", (0.58, 0.59, 0.56)),
        "fascia": material("MAT_EBF_BlueFascia_PLACEHOLDER", (0.20, 0.26, 0.31)),
        "sign": material("MAT_EB_DarkSignBand_PLACEHOLDER", (0.12, 0.13, 0.14)),
        "awning": material("MAT_EB_Awning_PLACEHOLDER", (0.24, 0.25, 0.24)),
        "yellow": material("MAT_FL_Yellow_PLACEHOLDER", (0.72, 0.54, 0.10)),
        "glass": material("MAT_EBF_Glass_PLACEHOLDER", (0.12, 0.16, 0.18), 0.20, 0.05, 0.40),
        "metal": material("MAT_EBF_Metal_PLACEHOLDER", (0.10, 0.11, 0.11), 0.38, 0.42),
        "interior": material("MAT_EBF_InteriorClay_PLACEHOLDER", (0.075, 0.078, 0.075)),
        "letter": material("MAT_EB_LetteringClay_PLACEHOLDER", (0.64, 0.51, 0.32)),
        "ground": material("MAT_EBF_ReviewGround_NONEXPORT", (0.17, 0.18, 0.18)),
    }


def box(name, dims, location, mat, col, bevel=0.0, rotation=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        obj.data.materials.append(mat)
    if bevel > 0.0:
        modifier = obj.modifiers.new("Blockout edge bevel", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
    return relink(obj, col)


def cylinder(name, radius, depth, location, mat, col, vertices=24, rotation=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    if mat:
        obj.data.materials.append(mat)
    return relink(obj, col)


def polygon_prism(name, points, z0, z1, mat, col):
    verts = [(x, y, z0) for x, y in points] + [(x, y, z1) for x, y in points]
    count = len(points)
    faces = [tuple(range(count - 1, -1, -1)), tuple(range(count, count * 2))]
    faces += [(i, (i + 1) % count, (i + 1) % count + count, i + count) for i in range(count)]
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(mat)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    return obj


def segment_frame(segment):
    start, end = Vector(segment[0]), Vector(segment[1])
    tangent = (end - start).normalized()
    outward = Vector((tangent.y, -tangent.x))
    return start, end, tangent, outward


def segment_box(name, segment, u0, width, depth, height, z, mat, col, offset=0.0, bevel=0.0):
    start, _end, tangent, outward = segment_frame(segment)
    centre = start + tangent * (u0 + width / 2.0) + outward * (offset + depth / 2.0)
    return box(
        name,
        (width, depth, height),
        (centre.x, centre.y, z),
        mat,
        col,
        bevel,
        rotation=(0.0, 0.0, atan2(tangent.y, tangent.x)),
    )


def local_to_world(segment, u, depth, z):
    start, _end, tangent, outward = segment_frame(segment)
    point = start + tangent * u + outward * depth
    return Vector((point.x, point.y, z))


def arch_ring(name, segment, centre_u, centre_z, inner_radius, outer_radius, depth, mat, col, segments=18):
    """Extruded upper semicircular ring in a facade's local plane."""
    start, _end, tangent, outward = segment_frame(segment)
    verts = []
    for d in (0.0, depth):
        for radius in (outer_radius, inner_radius):
            for index in range(segments + 1):
                angle = pi * index / segments
                u = centre_u + radius * cos(angle)
                z = centre_z + radius * sin(angle)
                point = start + tangent * u + outward * d
                verts.append((point.x, point.y, z))

    stride = segments + 1
    outer_back = 0
    inner_back = stride
    outer_front = stride * 2
    inner_front = stride * 3
    faces = []
    for index in range(segments):
        nxt = index + 1
        faces.append((outer_back + index, outer_back + nxt, inner_back + nxt, inner_back + index))
        faces.append((outer_front + index, inner_front + index, inner_front + nxt, outer_front + nxt))
        faces.append((outer_back + index, outer_front + index, outer_front + nxt, outer_back + nxt))
        faces.append((inner_back + index, inner_back + nxt, inner_front + nxt, inner_front + index))
    faces += [
        (outer_back, inner_back, inner_front, outer_front),
        (outer_back + segments, outer_front + segments, inner_front + segments, inner_back + segments),
    ]
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(mat)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    return obj


def beam_between(name, start, end, width, depth, mat, col):
    midpoint = (start + end) * 0.5
    direction = end - start
    length = direction.length
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=midpoint)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    obj.dimensions = (width, depth, length)
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    return relink(obj, col)


def add_window(prefix, segment, u0, width, bottom, height, mats, wall_col, frame_col, divisions=2):
    segment_box(f"{prefix}_Recess", segment, u0, width, 0.08, height, bottom + height / 2.0,
                mats["interior"], wall_col, offset=0.13)
    segment_box(f"{prefix}_Glass", segment, u0 + 0.05, width - 0.10, 0.025, height - 0.10,
                bottom + height / 2.0, mats["glass"], frame_col, offset=0.23)
    frame_width = 0.075
    for index in range(divisions + 1):
        u = u0 + width * index / divisions
        segment_box(f"{prefix}_Mullion_{index:02d}", segment, u - frame_width / 2.0, frame_width,
                    0.10, height + 0.10, bottom + height / 2.0, mats["metal"], frame_col, offset=0.22)
    for index, z in enumerate((bottom, bottom + height * 0.66, bottom + height)):
        segment_box(f"{prefix}_Rail_{index:02d}", segment, u0, width, 0.10, 0.075,
                    z, mats["metal"], frame_col, offset=0.22)
    segment_box(f"{prefix}_Sill", segment, u0 - 0.08, width + 0.16, 0.30, 0.12,
                bottom - 0.05, mats["lower"], wall_col, offset=0.15, bevel=0.012)


def add_arch_portal(prefix, segment, centre_u, opening_width, spring_z, opening_bottom, mats,
                    facade_col, door_col, fanlight_col, yellow=False):
    inner_radius = opening_width / 2.0
    outer_radius = inner_radius + 0.29
    jamb_width = 0.29
    opening_height = spring_z - opening_bottom
    portal_mat = mats["lower"]
    accent = mats["yellow"] if yellow else mats["metal"]

    # Dark opening has no wall behind it, preserving a future usable entrance.
    segment_box(f"{prefix}_EntryVoid", segment, centre_u - inner_radius, opening_width, 0.10,
                opening_height, opening_bottom + opening_height / 2.0, mats["interior"], facade_col, offset=0.10)
    segment_box(f"{prefix}_Jamb_Left", segment, centre_u - outer_radius, jamb_width, 0.34,
                opening_height, opening_bottom + opening_height / 2.0, portal_mat, facade_col, offset=0.02, bevel=0.018)
    segment_box(f"{prefix}_Jamb_Right", segment, centre_u + inner_radius, jamb_width, 0.34,
                opening_height, opening_bottom + opening_height / 2.0, portal_mat, facade_col, offset=0.02, bevel=0.018)
    arch_ring(f"{prefix}_ArchSurround", segment, centre_u, spring_z, inner_radius, outer_radius,
              0.34, portal_mat, facade_col)

    # Recessed fanlight and an economical radial pattern; this is silhouette
    # evidence only, not the second-pass decorative metalwork.
    arch_ring(f"{prefix}_FanlightOuterFrame", segment, centre_u, spring_z,
              inner_radius - 0.07, inner_radius, 0.08, mats["metal"], fanlight_col, 18)
    for index, angle in enumerate((22, 45, 68, 90, 112, 135, 158)):
        theta = radians(angle)
        start = local_to_world(segment, centre_u, 0.28, spring_z)
        end = local_to_world(
            segment,
            centre_u + (inner_radius - 0.11) * cos(theta),
            0.28,
            spring_z + (inner_radius - 0.11) * sin(theta),
        )
        beam_between(f"{prefix}_FanlightSpoke_{index:02d}", start, end, 0.035, 0.045,
                     mats["metal"], fanlight_col)

    if yellow:
        door_width = opening_width - 0.18
        leaf_width = door_width / 2.0
        for index, offset in enumerate((-leaf_width / 2.0, leaf_width / 2.0), start=1):
            centre = centre_u + offset
            segment_box(f"{prefix}_Door_{index:02d}_Frame", segment, centre - leaf_width / 2.0,
                        leaf_width, 0.11, 2.05, opening_bottom + 1.025, accent, door_col, offset=0.25)
            segment_box(f"{prefix}_Door_{index:02d}_Glass", segment, centre - leaf_width / 2.0 + 0.12,
                        leaf_width - 0.24, 0.025, 1.40, opening_bottom + 1.25, mats["glass"],
                        door_col, offset=0.32)
        segment_box(f"{prefix}_Threshold", segment, centre_u - inner_radius, opening_width, 0.48,
                    0.06, opening_bottom + 0.03, mats["metal"], door_col, offset=0.08)


def add_upper_window(prefix, segment, u0, width, bottom, height, mats, wall_col, frame_col):
    segment_box(f"{prefix}_Recess", segment, u0, width, 0.08, height, bottom + height / 2.0,
                mats["interior"], wall_col, offset=0.12)
    segment_box(f"{prefix}_Glass", segment, u0 + 0.08, width - 0.16, 0.025, height - 0.16,
                bottom + height / 2.0, mats["glass"], frame_col, offset=0.22)
    for frac in (0.0, 0.5, 1.0):
        segment_box(f"{prefix}_FrameV_{frac}", segment, u0 + width * frac - 0.035, 0.07,
                    0.10, height, bottom + height / 2.0, mats["metal"], frame_col, offset=0.21)
    for frac in (0.0, 0.58, 1.0):
        segment_box(f"{prefix}_FrameH_{frac}", segment, u0, width, 0.10, 0.07,
                    bottom + height * frac, mats["metal"], frame_col, offset=0.21)
    segment_box(f"{prefix}_Sill", segment, u0 - 0.10, width + 0.20, 0.30, 0.12,
                bottom - 0.05, mats["lower"], wall_col, offset=0.13, bevel=0.012)


def add_placeholder_text(body, name, location, target_width, mat, col):
    bpy.ops.object.text_add(location=location, rotation=(radians(90), 0.0, 0.0))
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Curve"
    obj.data.body = body
    obj.data.align_x = "CENTER"
    obj.data.align_y = "CENTER"
    obj.data.size = 0.64
    obj.data.extrude = 0.035
    obj.data.bevel_depth = 0.006
    obj.data.materials.append(mat)
    bpy.context.view_layer.update()
    if obj.dimensions.x > 0.0:
        scale = target_width / obj.dimensions.x
        obj.scale = (scale, scale, scale)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return relink(obj, col)


def build_blockout(mats):
    master = bpy.data.collections["EASTERN_BLOC_FLOCK_MASTER"]
    shell = child_collection("EBF_BuildingShell", master)
    upper = child_collection("EBF_UpperBuilding", master)
    eastern = child_collection("EB_EasternBloc", master)
    eb_awning = child_collection("EB_Awning", eastern)
    eb_openings = child_collection("EB_EntrancesAndWindows", eastern)
    flock = child_collection("FL_Flock", master)
    fl_portal = child_collection("FL_ArchEntrance", flock)
    fl_windows = child_collection("FL_SideWindows", flock)
    glass = child_collection("EBF_Glass", master)
    interior = child_collection("EBF_InteriorShells", master)
    review = child_collection("EBF_BlockoutReviewOnly")

    # Connected shell and enough internal depth that the public openings do not
    # read as a stage-flat facade.
    polygon_prism("EBF_InteriorFloor", FOOTPRINT, 0.0, 0.14, mats["interior"], interior)
    polygon_prism("EBF_GroundFloorCeiling", FOOTPRINT, 3.88, 4.05, mats["interior"], shell)
    polygon_prism("EBF_UpperBrickMass", FOOTPRINT, FASCIA_TOP, UPPER_TOP, mats["upper"], upper)
    box("EBF_RearWall", (12.2, 0.24, GROUND_FLOOR_TOP), (-1.9, 5.38, 2.025), mats["lower"], shell)
    box("EBF_WestPartyWall", (0.24, 9.25, GROUND_FLOOR_TOP), (-7.88, 0.62, 2.025), mats["lower"], shell)

    # Lower Eastern Bloc frontage, with a real opening at the entrance and a
    # broad recessed display window rather than a single pasted glass plane.
    for index, (u0, width) in enumerate(((0.0, 0.55), (2.25, 0.82), (8.33, 1.87))):
        segment_box(f"EB_LowerFacadePier_{index:02d}", FRONT, u0, width, 0.30, 3.72, 1.86,
                    mats["lower"], eastern, offset=-0.02, bevel=0.015)
    segment_box("EB_LowerFacadeHeader", FRONT, 0.0, 10.2, 0.30, 0.40, 3.52,
                mats["lower"], eastern, offset=-0.02, bevel=0.012)
    segment_box("EB_DisplayPlinth", FRONT, 3.07, 5.26, 0.36, 0.76, 0.38,
                mats["lower"], eastern, offset=0.02, bevel=0.015)
    add_window("EB_MainWindow", FRONT, 3.07, 5.26, 0.76, 2.66, mats, eastern, glass, divisions=3)
    add_arch_portal("EB_Entrance", FRONT, 1.40, 1.65, 2.50, 0.10, mats,
                    eastern, eb_openings, glass, yellow=False)

    # Continuous sign band and shallow physical placeholder lettering.
    segment_box("EB_Sign_Backplate", FRONT, 0.18, 8.45, 0.18, 0.78, 4.60,
                mats["sign"], eastern, offset=0.10, bevel=0.012)
    add_placeholder_text("EASTERN BLOC", "EB_Sign_Lettering_Blockout",
                         (-3.58, -4.305, 4.60), 6.15, mats["letter"], eastern)

    # Hero awning: nearly three metres of projection, deep enough to define the
    # sheltered pavement room visible in the references.
    box("EB_Awning_Fabric_Blockout", (8.05, 2.90, 0.11), (-3.58, -5.55, 3.20),
        mats["awning"], eb_awning, bevel=0.025, rotation=(radians(14), 0.0, 0.0))
    box("EB_Awning_Valance_Blockout", (8.05, 0.10, 0.38), (-3.58, -6.96, 2.73),
        mats["awning"], eb_awning, bevel=0.018)
    box("EB_Awning_WallMount", (8.10, 0.16, 0.18), (-3.58, -4.18, 3.57),
        mats["metal"], eb_awning, bevel=0.012)
    for index, x in enumerate((-7.25, 0.08)):
        beam_between(f"EB_Awning_FrameArm_{index:02d}", Vector((x, -4.17, 3.51)),
                     Vector((x, -6.90, 2.78)), 0.055, 0.055, mats["metal"], eb_awning)

    # Fascia/cornice wraps continuously around the clipped corner and side.
    for label, segment, length in (
        ("Front", FRONT, 10.2),
        ("Corner", CORNER, 2.828),
        ("Side", SIDE, 7.5),
    ):
        segment_box(f"EBF_BlueFascia_{label}", segment, 0.0, length, 0.28,
                    FASCIA_TOP - FASCIA_BOTTOM, (FASCIA_BOTTOM + FASCIA_TOP) / 2.0,
                    mats["fascia"], shell, offset=-0.02, bevel=0.012)
        segment_box(f"EBF_FasciaUpperCourse_{label}", segment, 0.0, length, 0.36,
                    0.18, FASCIA_TOP + 0.09, mats["lower"], shell, offset=-0.03, bevel=0.015)
        segment_box(f"EBF_FasciaLowerCourse_{label}", segment, 0.0, length, 0.38,
                    0.22, FASCIA_BOTTOM - 0.11, mats["lower"], shell, offset=-0.03, bevel=0.015)

    # Flok's clipped-corner portal remains the second unmistakable silhouette.
    corner_length = (Vector(CORNER[1]) - Vector(CORNER[0])).length
    portal_centre = corner_length / 2.0
    add_arch_portal("FL_Entrance", CORNER, portal_centre, 1.58, 2.40, 0.10, mats,
                    fl_portal, fl_portal, glass, yellow=True)
    segment_box("FL_YellowCanopy", CORNER, portal_centre - 0.98, 1.96, 0.72, 0.30,
                2.08, mats["yellow"], fl_portal, offset=0.27, bevel=0.025)
    segment_box("FL_CanopySignSurface", CORNER, portal_centre - 0.88, 1.76, 0.035, 0.22,
                2.08, mats["yellow"], fl_portal, offset=1.005)

    # Side elevation: three generous bays with masonry piers and a base course.
    side_length = 7.5
    segment_box("FL_SideFacadeHeader", SIDE, 0.0, side_length, 0.30, 0.42, 3.50,
                mats["lower"], flock, offset=-0.02, bevel=0.012)
    for index, (u0, width) in enumerate(((0.30, 1.85), (2.55, 1.85), (4.85, 1.85)), start=1):
        add_window(f"FL_SideWindow_{index:02d}", SIDE, u0, width, 0.72, 2.58,
                   mats, flock, fl_windows, divisions=2)
    for index, (u0, width) in enumerate(((0.0, 0.30), (2.15, 0.40), (4.40, 0.45), (6.70, 0.80))):
        segment_box(f"FL_SideFacadePier_{index:02d}", SIDE, u0, width, 0.30, 3.72, 1.86,
                    mats["lower"], flock, offset=-0.02, bevel=0.015)
    segment_box("FL_SideBaseCourse", SIDE, 0.0, side_length, 0.38, 0.58, 0.29,
                mats["metal"], flock, offset=-0.03, bevel=0.015)

    # Upper-floor window rhythm: two rows on both public elevations and one on
    # the clipped corner. Brick remains a material region, not modelled units.
    for row, bottom in enumerate((6.05, 8.45), start=1):
        for index, u0 in enumerate((0.60, 2.70, 4.80, 6.90, 8.65), start=1):
            add_upper_window(f"EBF_FrontUpper_R{row}_W{index}", FRONT, u0, 1.25,
                             bottom, 1.55, mats, upper, glass)
        for index, u0 in enumerate((0.48, 2.48, 4.48), start=1):
            add_upper_window(f"EBF_SideUpper_R{row}_W{index}", SIDE, u0, 1.20,
                             bottom, 1.55, mats, upper, glass)
        add_upper_window(f"EBF_CornerUpper_R{row}", CORNER, 0.80, 1.22,
                         bottom, 1.55, mats, upper, glass)

    # Strong upper/lower separation and a simple parapet silhouette.
    for label, segment, length in (
        ("Front", FRONT, 10.2), ("Corner", CORNER, 2.828), ("Side", SIDE, 7.5)
    ):
        segment_box(f"EBF_UpperBelt_{label}", segment, 0.0, length, 0.30, 0.22,
                    5.42, mats["lower"], upper, offset=-0.01, bevel=0.012)
        segment_box(f"EBF_ParapetCap_{label}", segment, 0.0, length, 0.34, 0.20,
                    UPPER_TOP + 0.10, mats["lower"], upper, offset=-0.02, bevel=0.012)

    # Review-only ground and scale proxy (1.75 m), deliberately not exported or
    # treated as authored architecture.
    box("EBF_Review_Ground_NONEXPORT", (28.0, 26.0, 0.10), (-1.5, -2.0, -0.08),
        mats["ground"], review)
    cylinder("EBF_Review_HumanScale_NONEXPORT", 0.18, 1.75, (-1.0, -8.0, 0.875),
             mats["lower"], review, vertices=16)

    return review


def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def camera(name, location, target, lens, col):
    bpy.ops.object.camera_add(location=location)
    cam = bpy.context.object
    cam.name = name
    cam.data.name = f"{name}_Data"
    cam.data.lens = lens
    point_at(cam, target)
    return relink(cam, col)


def area_light(name, location, target, energy, size, col):
    bpy.ops.object.light_add(type="AREA", location=location)
    light = bpy.context.object
    light.name = name
    light.data.name = f"{name}_Data"
    light.data.energy = energy
    light.data.shape = "DISK"
    light.data.size = size
    point_at(light, target)
    return relink(light, col)


def setup_review_scene():
    cameras = child_collection("EBF_BlockoutCameras")
    lights = child_collection("EBF_BlockoutLights")
    cams = (
        camera("CAMERA_A_WideConnectedCorner", (15.0, -25.0, 8.2), (-1.0, -0.6, 4.8), 56, cameras),
        camera("CAMERA_B_EasternBlocStraightOn", (-3.15, -29.0, 5.6), (-3.15, -3.85, 4.9), 58, cameras),
        camera("CAMERA_C_FlokEntranceClose", (10.8, -14.6, 2.8), (3.15, -3.0, 1.85), 60, cameras),
        camera("CAMERA_D_FlokSideCorner", (20.5, -10.5, 7.2), (1.6, 0.6, 4.5), 55, cameras),
        camera("CAMERA_E_ElevatedWrap", (19.0, -21.0, 17.0), (-0.4, 0.2, 5.4), 55, cameras),
    )
    area_light("EBF_Review_Key", (-9.0, -13.0, 15.0), (-1.0, -1.0, 4.5), 1700, 7.0, lights)
    area_light("EBF_Review_Fill", (12.0, -6.0, 10.0), (2.5, -1.0, 4.0), 1050, 6.0, lights)
    area_light("EBF_Review_Rim", (-1.0, 10.0, 14.0), (-0.5, 1.0, 5.0), 1350, 7.5, lights)

    scene = bpy.context.scene
    scene.world = scene.world or bpy.data.worlds.new("EBF_BlockoutWorld")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.055, 0.060, 0.066, 1.0)
    background.inputs["Strength"].default_value = 0.62
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 850
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = 24
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.camera = cams[0]
    return cams


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
        "EBF_UpperBrickMass",
        "EB_Sign_Backplate",
        "EB_Awning_Fabric_Blockout",
        "EB_MainWindow_Glass",
        "FL_Entrance_ArchSurround",
        "FL_YellowCanopy",
        "FL_Entrance_Door_01_Frame",
        "FL_SideWindow_01_Glass",
    )
    missing = [name for name in required if bpy.data.objects.get(name) is None]
    if missing:
        raise RuntimeError(f"Missing Eastern Bloc + Flok blockout objects: {missing}")
    unnamed = [
        obj.name for obj in bpy.data.objects
        if obj.name.startswith(("Cube", "Cylinder", "Text", "Camera", "Area"))
    ]
    if unnamed:
        raise RuntimeError(f"Unnamed primitives left in scene: {unnamed}")
    bad_scale = [
        obj.name for obj in bpy.data.objects
        if obj.type == "MESH" and any(abs(value - 1.0) > 1e-5 for value in obj.scale)
    ]
    if bad_scale:
        raise RuntimeError(f"Unapplied mesh scales: {bad_scale}")
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH" and "NONEXPORT" not in obj.name]
    triangles = sum(
        sum(max(0, len(poly.vertices) - 2) for poly in obj.data.polygons)
        for obj in meshes
    )
    print(f"Validation: {len(meshes)} asset mesh objects, approximately {triangles} triangles")
    print("Validation: footprint 12.2 m wide x 9.5 m deep; upper parapet 10.9 m")
    print("Validation: Eastern Bloc front faces -Y; Flok wraps the clipped south-east corner")


def save_notes():
    note = bpy.data.texts.new("EASTERN_BLOC_FLOCK_BLOCKOUT_NOTES")
    note.write(
        "FIRST PASS / REVIEW HOLD - GEOMETRY ONLY\n"
        "Source: references/architecture/buildings/eastern-bloc:flok/07_Eastern_Bloc_Flock.txt\n"
        "Inferred connected footprint: 12.2 m wide x 9.5 m deep, clipped SE corner.\n"
        "Eastern Bloc public frontage faces -Y; Flok portal occupies the clipped corner and wraps +X.\n"
        "Hero checks: the Eastern Bloc awning projects 2.9 m; Flok has an arched portal, radial fanlight,\n"
        "paired doors and projecting canopy; upper brick mass and fascia are continuous across the turn.\n"
        "Placeholder lettering is dimensional evidence only, not approved typography.\n"
        "Deferred: detailed moulding divisions, final fanlight metalwork, door furniture, vents, barrel,\n"
        "A-frame, terrace furniture, interaction anchors, textures, graphics, weathering and integration.\n"
    )


def render_reviews(cameras):
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    names = (
        "view-a-wide-connected-corner.png",
        "view-b-eastern-bloc-straight-on.png",
        "view-c-flok-entrance-close.png",
        "view-d-flok-side-corner.png",
        "view-e-elevated-wrap.png",
    )
    scene = bpy.context.scene
    for cam, filename in zip(cameras, names):
        scene.camera = cam
        scene.render.filepath = str(RENDER_DIR / filename)
        bpy.ops.render.render(write_still=True)
        print(f"Rendered {scene.render.filepath}")


def main():
    clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene.unit_settings.scale_length = 1.0
    mats = create_materials()
    build_blockout(mats)
    cameras = setup_review_scene()
    apply_mesh_transforms()
    validate()
    save_notes()
    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), check_existing=False)
    render_reviews(cameras)
    scene.camera = cameras[0]
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), check_existing=False)
    print(f"Saved geometry-only review blockout: {BLEND_PATH}")
    print(f"Review renders: {RENDER_DIR}")


if __name__ == "__main__":
    main()
