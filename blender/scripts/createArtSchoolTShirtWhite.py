"""Build the white Art School T-shirt as a standalone game-ready wearable.

The supplied reference is an oversized heavyweight white fashion blank with a
small two-line red copperplate-style chest print. This script constructs
connected front/back/sleeve pattern surfaces around a temporary adult male
A-pose fitting body, settles them with Blender Cloth under gravity and body
collision, adds fabric thickness only after simulation, bakes the cotton and
print into runtime textures, exports only the garment, renders the review set,
and reimports the GLB into an empty scene for validation.

Run from the repository root:

    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --python blender/scripts/createArtSchoolTShirtWhite.py

The fitting body, studio, cameras, working typography and lights are never
exported.  One Blender unit is one metre; the character faces +Y in Blender.
"""

from __future__ import annotations

from pathlib import Path
import json
import math
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.geometry import tessellate_polygon


ROOT = Path(__file__).resolve().parents[2]
BLEND_PATH = ROOT / "blender" / "source" / "characters" / "clothing" / "art_school_tshirt_white.blend"
GLB_PATH = ROOT / "public" / "assets" / "models" / "characters" / "clothing" / "art_school_tshirt_white.glb"
TEXTURE_DIR = ROOT / "blender" / "source" / "textures" / "characters" / "clothing" / "art-school-tshirt-white"
RENDER_DIR = ROOT / "renders" / "art-school-tshirt-white"
VALIDATION_PATH = RENDER_DIR / "validation.json"

COTTON_DIR = ROOT / "blender" / "source" / "textures" / "cc0" / "cotton-jersey"
COTTON_ALBEDO = COTTON_DIR / "cotton-jersey-albedo.jpg"
COTTON_NORMAL = COTTON_DIR / "cotton-jersey-normal.jpg"
COTTON_ROUGHNESS = COTTON_DIR / "cotton-jersey-roughness.jpg"

PRINT_WORKING_PATH = TEXTURE_DIR / "art-school-tshirt-white-print-working-4k.png"
BASECOLOR_PATH = TEXTURE_DIR / "art-school-tshirt-white-basecolor.png"
ROUGHNESS_PATH = TEXTURE_DIR / "art-school-tshirt-white-roughness.png"
NORMAL_PATH = TEXTURE_DIR / "art-school-tshirt-white-normal.png"

FONT_CANDIDATES = (
    Path.home() / "Library" / "Fonts" / "GreatVibes-Regular.ttf",
    Path.home() / "Library" / "Fonts" / "Burgues Script Regular.otf",
    Path("/System/Library/Fonts/Supplemental/SnellRoundhand.ttc"),
)

GARMENT_NAME = "ARTSCHOOL_TSHIRT_WHITE"
MATERIAL_NAME = "MAT_ArtSchool_White"
TEXTURE_SIZE = 2048


def ensure_directories() -> None:
    for path in (BLEND_PATH.parent, GLB_PATH.parent, TEXTURE_DIR, RENDER_DIR):
        path.mkdir(parents=True, exist_ok=True)


def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"


def collection(name: str) -> bpy.types.Collection:
    found = bpy.data.collections.get(name)
    if found is not None:
        return found
    found = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(found)
    return found


def move_to_collection(obj: bpy.types.Object, target: bpy.types.Collection) -> None:
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    target.objects.link(obj)


def material(name: str, colour: tuple[float, float, float], roughness: float = 0.8) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*colour, 1.0)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*colour, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = 0.0
    specular = bsdf.inputs.get("Specular IOR Level")
    if specular is not None:
        specular.default_value = 0.28
    return mat


def add_cube(name: str, location, dimensions, mat, target, bevel=0.0) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(obj, target)
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new("soft-edge", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    return obj


def add_uv_sphere(name: str, location, scale, mat, target, segments=24, rings=12) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(obj, target)
    obj.data.materials.append(mat)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def cylinder_between(name: str, start, end, radius, mat, target, vertices=18) -> bpy.types.Object:
    start_v = Vector(start)
    end_v = Vector(end)
    axis = end_v - start_v
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=axis.length,
                                        location=(start_v + end_v) * 0.5)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = axis.to_track_quat("Z", "Y")
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(obj, target)
    obj.data.materials.append(mat)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def build_fitting_body() -> bpy.types.Collection:
    """Temporary 1.80 m adult male fitting body in a relaxed 22 degree A-pose."""
    target = collection("FITTING_BODY_DO_NOT_EXPORT")
    grey = material("MAT_FittingBody_Grey", (0.105, 0.115, 0.125), 0.72)
    skin = material("MAT_FittingBody_Skin", (0.165, 0.105, 0.075), 0.66)

    add_uv_sphere("FIT_Torso", (0, -0.005, 1.175), (0.245, 0.145, 0.295), grey, target)
    add_uv_sphere("FIT_Pelvis", (0, -0.005, 0.875), (0.205, 0.135, 0.205), grey, target)
    add_uv_sphere("FIT_Neck", (0, 0.0, 1.525), (0.074, 0.067, 0.105), skin, target, 20, 10)
    add_uv_sphere("FIT_Head", (0, 0.0, 1.690), (0.104, 0.094, 0.135), skin, target)

    shoulder_z = 1.425
    upper_end_z = 1.17
    hand_z = 0.875
    for side, sign in (("L", -1), ("R", 1)):
        shoulder = (0.205 * sign, 0.0, shoulder_z)
        elbow = (0.515 * sign, 0.0, upper_end_z)
        wrist = (0.685 * sign, 0.005, hand_z)
        add_uv_sphere(f"FIT_Shoulder_{side}", (0.235 * sign, 0.0, 1.400),
                      (0.090, 0.110, 0.075), skin, target, 22, 11)
        cylinder_between(f"FIT_UpperArm_{side}", shoulder, elbow, 0.070, skin, target)
        cylinder_between(f"FIT_Forearm_{side}", elbow, wrist, 0.057, skin, target)
        add_uv_sphere(f"FIT_Hand_{side}", (0.715 * sign, 0.01, 0.825), (0.055, 0.036, 0.105), skin, target, 18, 9)

    for side, sign in (("L", -1), ("R", 1)):
        cylinder_between(f"FIT_Thigh_{side}", (0.10 * sign, 0, 0.86), (0.10 * sign, 0, 0.48), 0.092, grey, target)
        cylinder_between(f"FIT_Shin_{side}", (0.10 * sign, 0, 0.48), (0.10 * sign, 0, 0.10), 0.073, grey, target)

    target["purpose"] = "Temporary adult male A-pose fitting body; excluded from GLB export"
    return target


def pattern_boundary(front: bool) -> list[tuple[float, float]]:
    """Clockwise oversized cut; the assembled result remains a cloth surface."""
    neck_centre = 1.424 if front else 1.466
    neck_mid = 1.428 if front else 1.469
    return [
        (-0.112, 1.495),
        (-0.300, 1.458),
        (-0.492, 1.340),
        (-0.610, 1.200),
        (-0.574, 1.102),
        (-0.478, 1.090),
        (-0.342, 1.218),
        (-0.342, 0.744),
        (-0.330, 0.690),
        (0.330, 0.690),
        (0.342, 0.744),
        (0.342, 1.218),
        (0.478, 1.090),
        (0.574, 1.102),
        (0.610, 1.200),
        (0.492, 1.340),
        (0.300, 1.458),
        (0.112, 1.495),
        (0.106, 1.486 if front else 1.489),
        (0.091, 1.463 if front else 1.479),
        (0.067, 1.442 if front else 1.472),
        (0.035, neck_mid),
        (0.000, neck_centre),
        (-0.035, neck_mid),
        (-0.067, 1.442 if front else 1.472),
        (-0.091, 1.463 if front else 1.479),
        (-0.106, 1.486 if front else 1.489),
    ]


def panel_depth(x: float, z: float, front: bool) -> float:
    """Wrap a panel over the torso/arm instead of extruding a flat outline."""
    ax = abs(x)
    torso_half = 0.350
    torso_profile = math.sqrt(max(0.0, 1.0 - (ax / torso_half) ** 2)) if ax < torso_half else 0.0
    torso_depth = 0.166 * torso_profile
    if front:
        torso_depth += 0.013 * torso_profile * math.exp(-((z - 1.31) / 0.20) ** 2)

    sleeve_depth = 0.0
    if ax > 0.285:
        t = max(0.0, min(1.0, (ax - 0.285) / 0.325))
        centre_z = 1.365 - 0.205 * t
        vertical_radius = 0.140 - 0.030 * t
        vertical = (z - centre_z) / vertical_radius
        if abs(vertical) < 1.0:
            sleeve_depth = (0.137 - 0.022 * t) * math.sqrt(1.0 - vertical * vertical)
    return max(torso_depth, sleeve_depth)


def base_panel_y(x: float, z: float, front: bool) -> float:
    sign = 1.0 if front else -1.0
    return sign * panel_depth(x, z, front)


def boundary_open_segments(boundary_count: int) -> set[int]:
    # Cuff ends, bottom hem, and all neckline edges remain open.
    return {3, 8, 13, *range(17, boundary_count)}


def build_outer_shirt_surface(mat: bpy.types.Material) -> bpy.types.Object:
    target = collection("GARMENT")
    front_2d = pattern_boundary(True)
    back_2d = pattern_boundary(False)
    count = len(front_2d)
    vertices = []
    # Keep the panels distinct through subdivision so they develop independent
    # front/back cloth topology. Their outer sewing boundaries are welded only
    # after the dense pattern surfaces exist.
    for x, z in front_2d:
        vertices.append((x, base_panel_y(x, z, True), z))
    for x, z in back_2d:
        vertices.append((x, base_panel_y(x, z, False), z))

    lookup_front = {(round(x, 6), round(z, 6)): i for i, (x, z) in enumerate(front_2d)}
    lookup_back = {(round(x, 6), round(z, 6)): count + i for i, (x, z) in enumerate(back_2d)}
    faces = []
    front_poly = [Vector((x, z, 0)) for x, z in front_2d]
    back_poly = [Vector((x, z, 0)) for x, z in back_2d]
    for tri in tessellate_polygon([front_poly]):
        indices = [
            int(v) if isinstance(v, int) else lookup_front[(round(v.x, 6), round(v.y, 6))]
            for v in tri
        ]
        faces.append(tuple(reversed(indices)))  # +Y outer normal
    for tri in tessellate_polygon([back_poly]):
        indices = [
            count + int(v) if isinstance(v, int) else lookup_back[(round(v.x, 6), round(v.y, 6))]
            for v in tri
        ]
        faces.append(tuple(indices))  # -Y outer normal

    mesh = bpy.data.meshes.new("ARTSCHOOL_TSHIRT_WHITE_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.validate(verbose=True)
    mesh.update()
    shirt = bpy.data.objects.new(GARMENT_NAME, mesh)
    target.objects.link(shirt)
    shirt.data.materials.append(mat)

    subdiv = shirt.modifiers.new("garment-retopology-density", "SUBSURF")
    subdiv.subdivision_type = "SIMPLE"
    subdiv.levels = 3
    subdiv.render_levels = 3
    bpy.context.view_layer.objects.active = shirt
    shirt.select_set(True)
    bpy.ops.object.modifier_apply(modifier=subdiv.name)

    # Wrap the panel interiors over the body. Sewn boundaries stay at y=0;
    # Blender Cloth supplies all primary local folds in the next stage.
    for vertex in shirt.data.vertices:
        x, y, z = vertex.co
        if abs(y) > 0.00001:
            front = y > 0
            vertex.co.y = base_panel_y(x, z, front)

    # Sew corresponding front/back boundary vertices. Neck, cuff and hem
    # segments remain separate openings; endpoints still meet the adjacent
    # construction seam exactly as they do in a stitched garment.
    bm = bmesh.new()
    bm.from_mesh(shirt.data)
    bm.verts.ensure_lookup_table()
    boundary_verts = {vert for edge in bm.edges if edge.is_boundary for vert in edge.verts}

    def point_on_segment(px, pz, a, b, tolerance=0.00005):
        ax, az = a
        bx, bz = b
        dx, dz = bx - ax, bz - az
        length_sq = dx * dx + dz * dz
        if length_sq == 0:
            return math.hypot(px - ax, pz - az) <= tolerance
        t = max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / length_sq))
        return math.hypot(px - (ax + t * dx), pz - (az + t * dz)) <= tolerance

    sewn = []
    for vert in boundary_verts:
        px, _py, pz = vert.co
        lies_on_sewn_edge = False
        for boundary in (front_2d, back_2d):
            for index in range(len(boundary)):
                if index in boundary_open_segments(len(boundary)):
                    continue
                if point_on_segment(px, pz, boundary[index], boundary[(index + 1) % len(boundary)]):
                    lies_on_sewn_edge = True
                    break
            if lies_on_sewn_edge:
                break
        if lies_on_sewn_edge:
            vert.co.y = 0.0
            sewn.append(vert)
    bmesh.ops.remove_doubles(bm, verts=sewn, dist=0.000001)
    bm.to_mesh(shirt.data)
    bm.free()

    for polygon in shirt.data.polygons:
        polygon.use_smooth = True
    return shirt


def configure_body_collisions(fitting: bpy.types.Collection) -> None:
    for obj in fitting.objects:
        if obj.type != "MESH":
            continue
        obj.modifiers.new("fitting-body-collision", "COLLISION")
        obj.collision.thickness_outer = 0.007
        obj.collision.damping = 0.30
        obj.collision.cloth_friction = 8.0


def simulate_cloth_drape(shirt: bpy.types.Object, fitting: bpy.types.Collection) -> None:
    """Settle the sewn surface under gravity; no decorative folds are authored."""
    configure_body_collisions(fitting)
    pin_name = "CLOTH_Neckline_Anchor"
    pin = shirt.vertex_groups.new(name=pin_name)
    neckline = []
    shoulder_support = []
    for vertex in shirt.data.vertices:
        x, _y, z = vertex.co
        if z > 1.415 and abs(x) < 0.125:
            neckline.append(vertex.index)
        elif z > 1.435 and abs(x) < 0.325:
            shoulder_support.append(vertex.index)
    if neckline:
        pin.add(neckline, 1.0, "REPLACE")
    if shoulder_support:
        pin.add(shoulder_support, 1.0, "REPLACE")

    bpy.ops.object.select_all(action="DESELECT")
    shirt.select_set(True)
    bpy.context.view_layer.objects.active = shirt
    cloth = shirt.modifiers.new("cotton-gravity-drape", "CLOTH")
    settings = cloth.settings
    settings.quality = 8
    settings.mass = 0.34
    settings.air_damping = 3.5
    settings.tension_stiffness = 18.0
    settings.compression_stiffness = 12.0
    settings.shear_stiffness = 8.0
    settings.bending_stiffness = 0.28
    settings.tension_damping = 8.0
    settings.compression_damping = 8.0
    settings.shear_damping = 6.0
    settings.bending_damping = 0.7
    settings.pin_stiffness = 12.0
    settings.vertex_group_mass = pin.name
    settings.time_scale = 0.55
    collision = cloth.collision_settings
    collision.use_collision = True
    collision.collision_quality = 6
    collision.distance_min = 0.004
    collision.friction = 5.0
    collision.use_self_collision = False
    collision.self_distance_min = 0.003
    collision.self_friction = 5.0
    cloth.point_cache.frame_start = 1
    cloth.point_cache.frame_end = 72

    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = 72
    scene.gravity = (0.0, 0.0, -9.81)
    for frame in range(1, 73):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
    bpy.ops.object.modifier_apply(modifier=cloth.name)
    scene.frame_set(1)
    remaining_pin = shirt.vertex_groups.get(pin_name)
    if remaining_pin is not None:
        shirt.vertex_groups.remove(remaining_pin)


def finish_simulated_cloth(shirt: bpy.types.Object) -> None:
    """Add physical thickness only after the cloth result is frozen."""
    bpy.ops.object.select_all(action="DESELECT")
    shirt.select_set(True)
    bpy.context.view_layer.objects.active = shirt

    smooth = shirt.modifiers.new("cloth-relax-after-simulation", "SMOOTH")
    smooth.factor = 0.12
    smooth.iterations = 2
    bpy.ops.object.modifier_apply(modifier=smooth.name)

    solid = shirt.modifiers.new("heavyweight-cotton-thickness", "SOLIDIFY")
    solid.thickness = 0.0026
    solid.offset = 0.0
    solid.use_rim = True
    solid.use_rim_only = False
    bpy.ops.object.modifier_apply(modifier=solid.name)

    for polygon in shirt.data.polygons:
        polygon.use_smooth = True


def collar_mesh(mat: bpy.types.Material) -> bpy.types.Object:
    """Substantial rib band following the garment's actual crew-neck edge."""
    target = bpy.data.collections["GARMENT"]
    front = pattern_boundary(True)
    back = pattern_boundary(False)
    path = []
    # Right-to-left across the front neckline, then left-to-right across back.
    for index in [*range(17, len(front)), 0]:
        x, z = front[index]
        path.append(Vector((x, base_panel_y(x, z, True) + 0.0015, z)))
    for index in [0, *range(len(back) - 1, 16, -1)]:
        x, z = back[index]
        path.append(Vector((x, base_panel_y(x, z, False) - 0.0015, z)))

    segments = len(path)
    verts = []
    faces = []
    centre = Vector((0, 0, 1.525))
    # Four loops: outer-top, inner-top, outer-bottom, inner-bottom. The inner
    # loop moves toward the neck, creating a visible 20 mm rib band rather
    # than an edge-on horizontal torus.
    for loop in range(4):
        inner = loop in (1, 3)
        bottom = loop >= 2
        for point in path:
            inward = Vector((centre.x - point.x, 0.0, centre.z - point.z)).normalized()
            position = point + inward * (0.021 if inner else 0.0)
            position.y += 0.0025 if point.y >= 0 else -0.0025
            if bottom:
                position.z -= 0.0045
            verts.append(tuple(position))

    ot, it, ob, ib = (0, segments, 2 * segments, 3 * segments)
    for index in range(segments):
        nxt = (index + 1) % segments
        faces.extend([
            (ot + index, ot + nxt, it + nxt, it + index),
            (ob + index, ib + index, ib + nxt, ob + nxt),
            (ot + index, ob + index, ob + nxt, ot + nxt),
            (it + index, it + nxt, ib + nxt, ib + index),
        ])
    mesh = bpy.data.meshes.new("ARTSCHOOL_COLLAR_MESH")
    mesh.from_pydata(verts, [], faces)
    mesh.validate(verbose=True)
    mesh.update()
    obj = bpy.data.objects.new("ARTSCHOOL_Collar_Rib", mesh)
    target.objects.link(obj)
    obj.data.materials.append(mat)
    bevel = obj.modifiers.new("collar-soft-edge", "BEVEL")
    bevel.width = 0.0015
    bevel.segments = 2
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def curve_tube(name: str, points: list[tuple[float, float, float]], radius: float,
               mat: bpy.types.Material, cyclic=False) -> bpy.types.Object:
    """Create a capped low-sided tube; unlike converted curves this is manifold."""
    samples = [Vector(point) for point in points]
    sides = 8
    verts = []
    faces = []
    rings = len(samples)
    for index, point in enumerate(samples):
        if index == 0:
            tangent = (samples[1] - point).normalized()
        elif index == rings - 1:
            tangent = (point - samples[index - 1]).normalized()
        else:
            tangent = (samples[index + 1] - samples[index - 1]).normalized()
        axis_a = Vector((0, 1, 0))
        if abs(tangent.dot(axis_a)) > 0.92:
            axis_a = Vector((1, 0, 0))
        axis_a = (axis_a - tangent * axis_a.dot(tangent)).normalized()
        axis_b = tangent.cross(axis_a).normalized()
        for side in range(sides):
            angle = 2 * math.pi * side / sides
            offset = radius * (math.cos(angle) * axis_a + math.sin(angle) * axis_b)
            verts.append(tuple(point + offset))
    for ring in range(rings - 1):
        for side in range(sides):
            nxt = (side + 1) % sides
            a = ring * sides + side
            b = ring * sides + nxt
            c = (ring + 1) * sides + nxt
            d = (ring + 1) * sides + side
            faces.append((a, b, c, d))
    if cyclic:
        for side in range(sides):
            nxt = (side + 1) % sides
            faces.append(((rings - 1) * sides + side, (rings - 1) * sides + nxt, nxt, side))
    else:
        start_centre = len(verts)
        verts.append(tuple(samples[0]))
        end_centre = len(verts)
        verts.append(tuple(samples[-1]))
        for side in range(sides):
            nxt = (side + 1) % sides
            faces.append((start_centre, nxt, side))
            faces.append((end_centre, (rings - 1) * sides + side, (rings - 1) * sides + nxt))
    mesh = bpy.data.meshes.new(name + "_MESH")
    mesh.from_pydata(verts, [], faces)
    mesh.validate(verbose=True)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.data.collections["GARMENT"].objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def add_construction_seams(mat: bpy.types.Material) -> list[bpy.types.Object]:
    seams = []
    # Shoulder and sleeve top seams, following the integrated pattern edge.
    for front in (True, False):
        sign = 1 if front else -1
        boundary = pattern_boundary(front)
        y_offset = 0.0017 * sign
        for start, end, label in ((0, 3, "L"), (14, 17, "R")):
            pts = []
            route = range(start, end + 1) if start < end else range(start, end - 1, -1)
            for idx in route:
                x, z = boundary[idx]
                pts.append((x, base_panel_y(x, z, front) + y_offset, z))
            seams.append(curve_tube(f"ARTSCHOOL_ShoulderSleeveSeam_{label}_{'F' if front else 'B'}", pts,
                                    0.00125, mat))

    return seams


def join_garment_parts(parts: list[bpy.types.Object]) -> bpy.types.Object:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    shirt = bpy.context.object
    shirt.name = GARMENT_NAME
    shirt.data.name = "ARTSCHOOL_TSHIRT_WHITE_MESH"
    # One material slot only.
    for polygon in shirt.data.polygons:
        polygon.material_index = 0
        # Keep the thin open bottom rim flat-shaded so its front/back normals
        # do not average into dark scribble-like artifacts.
        polygon.use_smooth = abs(polygon.normal.z) < 0.78
    while len(shirt.data.materials) > 1:
        shirt.data.materials.pop(index=len(shirt.data.materials) - 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    triangulate = shirt.modifiers.new("runtime-triangulation", "TRIANGULATE")
    triangulate.keep_custom_normals = True
    bpy.ops.object.modifier_apply(modifier=triangulate.name)
    shirt.data.validate(verbose=True, clean_customdata=False)
    shirt["asset"] = "Zealot of Harperhey — Art School T-shirt, white"
    shirt["fit"] = "oversized heavyweight contemporary blank"
    shirt["rigging"] = "standalone rest-state garment; skin to compatible humanoid armature"
    shirt["front"] = "+Y in Blender / -Z after glTF Y-up conversion"
    return shirt


def render_typography_source() -> bpy.types.Image:
    """Render high-resolution red script artwork; geometry is immediately discarded."""
    scene = bpy.context.scene
    temp = collection("WORKING_TYPOGRAPHY_DO_NOT_EXPORT")
    for obj in bpy.context.scene.objects:
        obj.hide_render = True

    red = material("MAT_Working_Print_Red", (0.62, 0.012, 0.020), 0.72)
    nodes = red.node_tree.nodes
    links = red.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    output = nodes.get("Material Output")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (0.62, 0.012, 0.020, 1.0)
    emission.inputs["Strength"].default_value = 1.0
    links.remove(bsdf.outputs["BSDF"].links[0])
    links.new(emission.outputs["Emission"], output.inputs["Surface"])

    font_path = next((path for path in FONT_CANDIDATES if path.exists()), None)
    if font_path is None:
        raise FileNotFoundError("No suitable copperplate-style font was found")
    font = bpy.data.fonts.load(str(font_path))

    text_specs = (
        ("I went to art school and", 0.17),
        ("all I got was this lousy T-shirt.", -0.17),
    )
    texts = []
    for index, (body, y) in enumerate(text_specs):
        curve = bpy.data.curves.new(f"WORKING_Print_Line_{index + 1}", "FONT")
        curve.body = body
        curve.font = font
        curve.align_x = "CENTER"
        curve.align_y = "CENTER"
        curve.size = 0.44
        curve.offset = 0.010
        curve.resolution_u = 24
        curve.space_character = 1.0
        obj = bpy.data.objects.new(curve.name, curve)
        temp.objects.link(obj)
        obj.location = (0.0, y, 0.0)
        obj.data.materials.append(red)
        texts.append(obj)
    bpy.context.view_layer.update()
    max_width = max(obj.dimensions.x for obj in texts)
    if max_width > 3.35:
        scale = 3.35 / max_width
        for obj in texts:
            obj.scale *= scale

    bpy.ops.object.camera_add(location=(0, 0, 10))
    camera = bpy.context.object
    camera.name = "WORKING_Print_Camera"
    move_to_collection(camera, temp)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 4.0
    camera.rotation_euler = (0, 0, 0)
    # Cameras look down local -Z; no rotation is required.
    scene.camera = camera
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 4096
    scene.render.resolution_y = 4096
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = str(PRINT_WORKING_PATH)
    scene.view_settings.look = "AgX - Medium High Contrast"
    bpy.ops.render.render(write_still=True)

    for obj in list(temp.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(temp)
    for obj in bpy.context.scene.objects:
        obj.hide_render = False
    image = bpy.data.images.load(str(PRINT_WORKING_PATH), check_existing=False)
    image.name = "ArtSchool_Print_Working_4K"
    return image


def smart_unwrap_and_aux_uvs(shirt: bpy.types.Object) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    shirt.select_set(True)
    bpy.context.view_layer.objects.active = shirt
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.008,
                             area_weight=0.35, correct_aspect=True, scale_to_bounds=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    target_uv = shirt.data.uv_layers.active
    target_uv.name = "UVMap"
    target_uv.active_render = True

    print_uv = shirt.data.uv_layers.new(name="PrintUV")
    fabric_uv = shirt.data.uv_layers.new(name="FabricUV")
    for loop in shirt.data.loops:
        co = shirt.data.vertices[loop.vertex_index].co
        # Flip U so the front-facing +Y view reads left-to-right after the
        # projection-to-atlas bake. Keep the intentionally small print below
        # the collar with generous negative space.
        print_uv.data[loop.index].uv = (0.5 - co.x / 0.55, (co.z - 1.135) / 0.33)
        # Roughly 55 mm repeat: only the weave, not the source image's colour, should read.
        fabric_uv.data[loop.index].uv = (co.x * 18.0 + co.y * 3.0, co.z * 18.0)
    shirt.data.uv_layers.active = target_uv


def new_bake_image(name: str, path: Path, colorspace: str) -> bpy.types.Image:
    image = bpy.data.images.new(name, width=TEXTURE_SIZE, height=TEXTURE_SIZE, alpha=False,
                                float_buffer=False, is_data=(colorspace != "sRGB"))
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.colorspace_settings.name = colorspace
    return image


def clear_nodes(mat: bpy.types.Material):
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (900, 0)
    return nodes, mat.node_tree.links, output


def image_node(nodes, image, uv_node, location):
    node = nodes.new("ShaderNodeTexImage")
    node.image = image
    node.interpolation = "Linear"
    node.extension = "REPEAT"
    node.location = location
    return node


def front_facing_mask(nodes, links):
    geometry = nodes.new("ShaderNodeNewGeometry")
    geometry.location = (-850, -470)
    separate = nodes.new("ShaderNodeSeparateXYZ")
    separate.location = (-650, -470)
    # Position is more robust than interpolated normals while baking across
    # the garment's thin inner/outer shell and many UV seams.
    links.new(geometry.outputs["Position"], separate.inputs["Vector"])
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (-450, -470)
    ramp.color_ramp.elements[0].position = 0.05
    ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    ramp.color_ramp.elements[1].position = 0.12
    ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    links.new(separate.outputs["Y"], ramp.inputs["Fac"])
    return ramp.outputs["Color"]


def prepare_source_nodes(mat: bpy.types.Material, print_image: bpy.types.Image, mode: str):
    nodes, links, output = clear_nodes(mat)
    print_uv = nodes.new("ShaderNodeUVMap")
    print_uv.uv_map = "PrintUV"
    print_uv.location = (-1050, 180)
    fabric_uv = nodes.new("ShaderNodeUVMap")
    fabric_uv.uv_map = "FabricUV"
    fabric_uv.location = (-1050, -140)
    print_tex = image_node(nodes, print_image, print_uv, (-820, 180))
    print_tex.extension = "CLIP"
    links.new(print_uv.outputs["UV"], print_tex.inputs["Vector"])
    facing = front_facing_mask(nodes, links)
    alpha = nodes.new("ShaderNodeMath")
    alpha.operation = "MULTIPLY"
    alpha.location = (-180, 80)
    links.new(print_tex.outputs["Alpha"], alpha.inputs[0])
    links.new(facing, alpha.inputs[1])

    if mode == "basecolor":
        cotton = bpy.data.images.load(str(COTTON_ALBEDO), check_existing=True)
        cotton.colorspace_settings.name = "sRGB"
        cotton_tex = image_node(nodes, cotton, fabric_uv, (-820, -160))
        links.new(fabric_uv.outputs["UV"], cotton_tex.inputs["Vector"])
        grey = nodes.new("ShaderNodeRGBToBW")
        grey.location = (-590, -160)
        links.new(cotton_tex.outputs["Color"], grey.inputs["Color"])
        map_range = nodes.new("ShaderNodeMapRange")
        map_range.location = (-360, -180)
        map_range.inputs["From Min"].default_value = 0.20
        map_range.inputs["From Max"].default_value = 0.80
        map_range.inputs["To Min"].default_value = 0.94
        map_range.inputs["To Max"].default_value = 1.02
        map_range.clamp = True
        links.new(grey.outputs["Val"], map_range.inputs["Value"])
        warm = nodes.new("ShaderNodeRGB")
        warm.outputs[0].default_value = (0.825, 0.795, 0.745, 1.0)
        multiply = nodes.new("ShaderNodeMixRGB")
        multiply.blend_type = "MULTIPLY"
        multiply.inputs[0].default_value = 1.0
        links.new(warm.outputs["Color"], multiply.inputs[1])
        links.new(map_range.outputs["Result"], multiply.inputs[2])
        red = nodes.new("ShaderNodeRGB")
        red.outputs[0].default_value = (0.34, 0.006, 0.010, 1.0)
        mix = nodes.new("ShaderNodeMixRGB")
        mix.blend_type = "MIX"
        mix.location = (220, 50)
        links.new(alpha.outputs[0], mix.inputs[0])
        links.new(multiply.outputs["Color"], mix.inputs[1])
        links.new(red.outputs["Color"], mix.inputs[2])
        emission = nodes.new("ShaderNodeEmission")
        emission.location = (520, 40)
        links.new(mix.outputs["Color"], emission.inputs["Color"])
        links.new(emission.outputs["Emission"], output.inputs["Surface"])
    elif mode == "roughness":
        rough = bpy.data.images.load(str(COTTON_ROUGHNESS), check_existing=True)
        rough.colorspace_settings.name = "Non-Color"
        rough_tex = image_node(nodes, rough, fabric_uv, (-820, -160))
        links.new(fabric_uv.outputs["UV"], rough_tex.inputs["Vector"])
        map_range = nodes.new("ShaderNodeMapRange")
        map_range.inputs["From Min"].default_value = 0.05
        map_range.inputs["From Max"].default_value = 0.95
        map_range.inputs["To Min"].default_value = 0.78
        map_range.inputs["To Max"].default_value = 0.90
        map_range.clamp = True
        links.new(rough_tex.outputs["Color"], map_range.inputs["Value"])
        print_delta = nodes.new("ShaderNodeMath")
        print_delta.operation = "MULTIPLY_ADD"
        print_delta.inputs[1].default_value = -0.025
        links.new(alpha.outputs[0], print_delta.inputs[0])
        links.new(map_range.outputs["Result"], print_delta.inputs[2])
        emission = nodes.new("ShaderNodeEmission")
        links.new(print_delta.outputs[0], emission.inputs["Color"])
        links.new(emission.outputs["Emission"], output.inputs["Surface"])
    elif mode == "normal":
        normal_image = bpy.data.images.load(str(COTTON_NORMAL), check_existing=True)
        normal_image.colorspace_settings.name = "Non-Color"
        normal_tex = image_node(nodes, normal_image, fabric_uv, (-650, -120))
        links.new(fabric_uv.outputs["UV"], normal_tex.inputs["Vector"])
        normal_map = nodes.new("ShaderNodeNormalMap")
        normal_map.uv_map = "FabricUV"
        normal_map.inputs["Strength"].default_value = 0.18
        links.new(normal_tex.outputs["Color"], normal_map.inputs["Color"])
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.inputs["Base Color"].default_value = (0.82, 0.79, 0.74, 1)
        bsdf.inputs["Roughness"].default_value = 0.84
        links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
        links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    else:
        raise ValueError(mode)
    return nodes


def bake_to_image(shirt: bpy.types.Object, mat: bpy.types.Material, print_image: bpy.types.Image,
                  mode: str, image: bpy.types.Image) -> None:
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 1
    scene.cycles.use_denoising = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.bake.margin = 12
    scene.render.bake.use_clear = True
    nodes = prepare_source_nodes(mat, print_image, mode)
    target = nodes.new("ShaderNodeTexImage")
    target.image = image
    target.name = "BAKE_TARGET"
    nodes.active = target
    bpy.ops.object.select_all(action="DESELECT")
    shirt.select_set(True)
    bpy.context.view_layer.objects.active = shirt
    if mode == "normal":
        bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT")
    else:
        bpy.ops.object.bake(type="EMIT")
    image.save()


def build_runtime_material(mat: bpy.types.Material, base: bpy.types.Image,
                           rough: bpy.types.Image, normal: bpy.types.Image) -> None:
    nodes, links, output = clear_nodes(mat)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (420, 0)
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Roughness"].default_value = 0.84
    specular = bsdf.inputs.get("Specular IOR Level")
    if specular is not None:
        specular.default_value = 0.28
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    base_node = nodes.new("ShaderNodeTexImage")
    base_node.name = "ArtSchool_BaseColor_2K"
    base_node.image = base
    base_node.location = (-420, 160)
    links.new(base_node.outputs["Color"], bsdf.inputs["Base Color"])

    rough_node = nodes.new("ShaderNodeTexImage")
    rough_node.name = "ArtSchool_Roughness_2K"
    rough_node.image = rough
    rough_node.location = (-420, -40)
    links.new(rough_node.outputs["Color"], bsdf.inputs["Roughness"])

    normal_node = nodes.new("ShaderNodeTexImage")
    normal_node.name = "ArtSchool_Normal_2K"
    normal_node.image = normal
    normal_node.location = (-420, -250)
    map_node = nodes.new("ShaderNodeNormalMap")
    map_node.location = (0, -240)
    map_node.inputs["Strength"].default_value = 0.22
    links.new(normal_node.outputs["Color"], map_node.inputs["Color"])
    links.new(map_node.outputs["Normal"], bsdf.inputs["Normal"])


def write_subtle_weave_normal(image: bpy.types.Image) -> None:
    """Write a seamless micro-weave normal without UV-island bake seams."""
    size = int(image.size[0])
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    # Fine warp/weft with a weak diagonal interlock. At ordinary gameplay
    # distance this averages away; it becomes legible only in the close-up.
    nx = (
        0.020 * np.sin(2.0 * math.pi * x / 11.0)
        + 0.008 * np.sin(2.0 * math.pi * (x + y) / 23.0)
    )
    ny = (
        0.020 * np.sin(2.0 * math.pi * y / 13.0)
        + 0.008 * np.sin(2.0 * math.pi * (x - y) / 19.0)
    )
    nz = np.sqrt(np.maximum(0.0, 1.0 - nx * nx - ny * ny))
    pixels = np.empty((size, size, 4), dtype=np.float32)
    pixels[..., 0] = nx * 0.5 + 0.5
    pixels[..., 1] = ny * 0.5 + 0.5
    pixels[..., 2] = nz * 0.5 + 0.5
    pixels[..., 3] = 1.0
    image.pixels.foreach_set(pixels.ravel())
    image.save()


def bake_runtime_textures(shirt: bpy.types.Object, mat: bpy.types.Material,
                          print_image: bpy.types.Image) -> tuple[bpy.types.Image, bpy.types.Image, bpy.types.Image]:
    base = new_bake_image("ArtSchool_White_BaseColor_2K", BASECOLOR_PATH, "sRGB")
    rough = new_bake_image("ArtSchool_White_Roughness_2K", ROUGHNESS_PATH, "Non-Color")
    normal = new_bake_image("ArtSchool_White_Normal_2K", NORMAL_PATH, "Non-Color")
    bake_to_image(shirt, mat, print_image, "basecolor", base)
    bake_to_image(shirt, mat, print_image, "roughness", rough)
    write_subtle_weave_normal(normal)
    build_runtime_material(mat, base, rough, normal)
    # Projection-only UVs have served their purpose. The source master and GLB
    # keep one clean packed runtime atlas with no repeating/overlapping helper
    # coordinates.
    for name in ("PrintUV", "FabricUV"):
        layer = shirt.data.uv_layers.get(name)
        if layer is not None:
            shirt.data.uv_layers.remove(layer)
    shirt.data.uv_layers.active = shirt.data.uv_layers.get("UVMap")
    return base, rough, normal


def look_at(obj: bpy.types.Object, target) -> None:
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def make_review_scene(fitting: bpy.types.Collection):
    review = collection("REVIEW_DO_NOT_EXPORT")
    # The body exists to generate the fit, not to disguise the garment's
    # silhouette in presentation renders.
    for obj in fitting.objects:
        obj.hide_render = True
    studio_mat = material("MAT_Studio_Grey", (0.055, 0.061, 0.070), 0.82)
    add_cube("REVIEW_Ground", (0, 0, -0.035), (5.0, 5.0, 0.06), studio_mat, review, 0.03)

    bpy.ops.object.camera_add(location=(0, 3.65, 1.18))
    camera = bpy.context.object
    camera.name = "REVIEW_Camera"
    move_to_collection(camera, review)
    camera.data.lens = 68
    look_at(camera, (0, 0, 1.10))
    bpy.context.scene.camera = camera

    lights = []
    for name, location, energy, size, colour in (
        ("REVIEW_Key", (-2.0, 2.4, 3.2), 380, 2.0, (1.0, 0.91, 0.82)),
        ("REVIEW_Fill", (2.1, 1.5, 2.2), 210, 2.4, (0.78, 0.87, 1.0)),
        ("REVIEW_Rim", (0.5, -2.0, 2.8), 320, 1.6, (1.0, 0.83, 0.70)),
    ):
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        light.data.color = colour
        move_to_collection(light, review)
        look_at(light, (0, 0, 1.2))
        lights.append(light)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("ArtSchool_Studio_World")
    scene.world.color = (0.025, 0.030, 0.040)
    scene.view_settings.look = "AgX - Medium High Contrast"
    return camera, lights


def render_review_set(camera: bpy.types.Object, lights: list[bpy.types.Object]) -> None:
    scene = bpy.context.scene
    views = (
        ("01-front.png", (0, 3.55, 1.20), (0, 0, 1.14), 68),
        ("02-back.png", (0, -3.55, 1.20), (0, 0, 1.14), 68),
        ("03-left-three-quarter.png", (-2.45, 2.75, 1.30), (0, 0, 1.15), 72),
        ("04-right-three-quarter.png", (2.45, 2.75, 1.30), (0, 0, 1.15), 72),
        ("05-side.png", (3.60, 0, 1.25), (0, 0, 1.16), 72),
        ("06-chest-typography-closeup.png", (0, 2.10, 1.39), (0, 0.135, 1.36), 86),
    )
    for filename, position, target, lens in views:
        camera.location = position
        camera.data.lens = lens
        look_at(camera, target)
        if filename.startswith("06-"):
            scene.render.resolution_x = 1200
            scene.render.resolution_y = 900
        else:
            scene.render.resolution_x = 900
            scene.render.resolution_y = 900
        scene.render.filepath = str(RENDER_DIR / filename)
        bpy.ops.render.render(write_still=True)

    # Hard directional construction check: small source, grazing across white cotton.
    for light in lights:
        light.hide_render = True
    bpy.ops.object.light_add(type="AREA", location=(-1.4, 1.8, 2.75))
    hard = bpy.context.object
    hard.name = "REVIEW_HardDirectional"
    hard.data.energy = 600
    hard.data.size = 0.18
    move_to_collection(hard, bpy.data.collections["REVIEW_DO_NOT_EXPORT"])
    look_at(hard, (0.10, 0.05, 1.18))
    camera.location = (2.1, 2.85, 1.42)
    camera.data.lens = 72
    look_at(camera, (0, 0, 1.15))
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 900
    scene.render.filepath = str(RENDER_DIR / "07-hard-light-construction.png")
    bpy.ops.render.render(write_still=True)
    hard.hide_render = True
    for light in lights:
        light.hide_render = False


def count_triangles(obj: bpy.types.Object) -> int:
    return sum(len(poly.vertices) - 2 for poly in obj.data.polygons)


def non_manifold_edges(obj: bpy.types.Object, weld_import_splits: bool = False) -> int:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    if weld_import_splits:
        # glTF correctly duplicates vertices at UV/tangent seams. Re-weld
        # coincident positions before judging whether the underlying surface
        # topology survived the round trip.
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.000001)
    count = sum(1 for edge in bm.edges if not edge.is_manifold)
    bm.free()
    return count


def describe_non_manifold_edges(obj: bpy.types.Object, limit: int = 24) -> list[dict]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    records = []
    for edge in bm.edges:
        if edge.is_manifold:
            continue
        records.append({
            "faces": len(edge.link_faces),
            "a": [round(value, 4) for value in edge.verts[0].co],
            "b": [round(value, 4) for value in edge.verts[1].co],
        })
        if len(records) >= limit:
            break
    bm.free()
    return records


def object_bounds(obj: bpy.types.Object):
    world = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    mins = Vector((min(v.x for v in world), min(v.y for v in world), min(v.z for v in world)))
    maxs = Vector((max(v.x for v in world), max(v.y for v in world), max(v.z for v in world)))
    return mins, maxs


def export_glb(shirt: bpy.types.Object) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    shirt.select_set(True)
    bpy.context.view_layer.objects.active = shirt
    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
        export_extras=True,
    )


def validate_reimport(expected_triangles: int) -> dict:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(GLB_PATH))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    all_objects = list(bpy.context.scene.objects)
    if len(meshes) != 1:
        raise RuntimeError(f"Expected one exported mesh, got {len(meshes)}")
    shirt = meshes[0]
    materials = sorted({slot.material.name for slot in shirt.material_slots if slot.material})
    triangles = count_triangles(shirt)
    mins, maxs = object_bounds(shirt)
    fitting_leaks = [obj.name for obj in all_objects if obj.name.startswith("FIT_")]
    if fitting_leaks:
        raise RuntimeError(f"Fitting body leaked into export: {fitting_leaks}")
    if GARMENT_NAME not in shirt.name:
        raise RuntimeError(f"Unexpected exported object name: {shirt.name}")
    if MATERIAL_NAME not in materials:
        raise RuntimeError(f"Missing runtime material {MATERIAL_NAME}: {materials}")
    if not (5000 <= triangles <= 12000):
        raise RuntimeError(f"Triangle budget violated: {triangles}")
    if abs(triangles - expected_triangles) > 8:
        raise RuntimeError(f"Triangle count changed on export: {expected_triangles} -> {triangles}")
    imported_split_edges = non_manifold_edges(shirt)
    welded_non_manifold = non_manifold_edges(shirt, weld_import_splits=True)
    if welded_non_manifold != 0:
        raise RuntimeError("Reimported garment contains non-manifold edges")
    if len(shirt.data.uv_layers) < 1:
        raise RuntimeError("Reimported garment has no UV set")

    image_records = []
    for image in bpy.data.images:
        if image.source == "FILE" and image.size[0] > 0:
            image_records.append({"name": image.name, "size": [int(image.size[0]), int(image.size[1])]})
    report = {
        "asset": "Art School T-shirt — white",
        "glb": str(GLB_PATH.relative_to(ROOT)),
        "object": shirt.name,
        "mesh_objects": len(meshes),
        "materials": materials,
        "vertices": len(shirt.data.vertices),
        "triangles": triangles,
        "triangle_budget": [5000, 12000],
        "non_manifold_edges_after_welding_import_splits": welded_non_manifold,
        "raw_import_boundary_edges_from_uv_normal_splits": imported_split_edges,
        "uv_sets": [layer.name for layer in shirt.data.uv_layers],
        "bounds_m": {
            "min": [round(value, 4) for value in mins],
            "max": [round(value, 4) for value in maxs],
            "dimensions": [round(value, 4) for value in (maxs - mins)],
        },
        "object_scale": [round(value, 6) for value in shirt.scale],
        "textures": image_records,
        "fitting_body_exported": False,
        "cameras_exported": any(obj.type == "CAMERA" for obj in all_objects),
        "lights_exported": any(obj.type == "LIGHT" for obj in all_objects),
        "status": "PASS",
    }
    VALIDATION_PATH.write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    ensure_directories()
    reset_scene()
    fitting = build_fitting_body()
    garment_mat = material(MATERIAL_NAME, (0.825, 0.795, 0.745), 0.84)
    outer = build_outer_shirt_surface(garment_mat)
    print(f"[art-school-tshirt] cloth surface before simulation: {count_triangles(outer)} tris, "
          f"{non_manifold_edges(outer)} open-boundary edges")
    simulate_cloth_drape(outer, fitting)
    finish_simulated_cloth(outer)
    collar = collar_mesh(garment_mat)
    for part in (outer, collar):
        print(f"[art-school-tshirt] prejoin {part.name}: {count_triangles(part)} tris, "
              f"{non_manifold_edges(part)} non-manifold edges")
    shirt = join_garment_parts([outer, collar])
    triangles = count_triangles(shirt)
    print(f"[art-school-tshirt] joined: {triangles} tris, {non_manifold_edges(shirt)} non-manifold edges")
    if not (5000 <= triangles <= 12000):
        raise RuntimeError(f"Source garment triangle budget violated: {triangles}")
    if non_manifold_edges(shirt) != 0:
        print(json.dumps(describe_non_manifold_edges(shirt), indent=2))
        raise RuntimeError("Source garment contains non-manifold edges")

    smart_unwrap_and_aux_uvs(shirt)
    print_image = render_typography_source()
    bake_runtime_textures(shirt, garment_mat, print_image)

    camera, lights = make_review_scene(fitting)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), compress=True)
    export_glb(shirt)
    render_review_set(camera, lights)
    report = validate_reimport(triangles)
    print(json.dumps(report, indent=2))
    print(f"[art-school-tshirt] BLEND: {BLEND_PATH}")
    print(f"[art-school-tshirt] GLB:   {GLB_PATH}")
    print(f"[art-school-tshirt] RENDERS: {RENDER_DIR}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[art-school-tshirt] ERROR: {exc}", file=sys.stderr)
        raise
