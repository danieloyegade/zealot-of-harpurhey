"""Build the geometry-stage MCR1 corner shop from the supplied references.

The daylight photographs drive scale and construction; the older night view
drives the arrangement of the projecting illuminated sign housings.  The file
intentionally contains no lettering, graphics, brick geometry, products,
street furniture, or photographic textures.
"""

from math import atan2, radians, sqrt
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
BLEND = ROOT / "blender" / "source" / "harperhey-mcr1-geometry.blend"
GLB = ROOT / "public" / "assets" / "models" / "harperhey-mcr1-geometry.glb"
RENDERS = ROOT / "renders" / "mcr1"


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)
    for col in list(bpy.data.collections):
        if col.name != "Collection":
            bpy.data.collections.remove(col)
    bpy.data.collections["Collection"].name = "MCR1_Asset"


def collection(name):
    col = bpy.data.collections.get(name)
    if not col:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def material(name, colour, roughness=0.78, metallic=0.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*colour, alpha)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*colour, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if alpha < 1:
        bsdf.inputs["Alpha"].default_value = alpha
        m.surface_render_method = "DITHERED"
    return m


def move(obj, col):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    col.objects.link(obj)
    return obj


def box(name, dims, loc, mat, col, bevel=0.0, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = name + "_Mesh"
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new("Small_Edge_Bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    move(obj, col)
    return obj


def cylinder(name, radius, depth, loc, mat, col, vertices=24, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = name + "_Mesh"
    if mat:
        obj.data.materials.append(mat)
    move(obj, col)
    return obj


def segment_box(name, p1, p2, depth, height, z, mat, col, outward=True, bevel=0.0):
    """Box whose long axis follows a facade segment; p1->p2 keeps exterior on right."""
    a, b = Vector(p1), Vector(p2)
    direction = b - a
    length = direction.length
    u = direction.normalized()
    normal = Vector((u.y, -u.x))
    centre = (a + b) * 0.5 + normal * depth * (0.5 if outward else -0.5)
    return box(name, (length, depth, height), (centre.x, centre.y, z), mat, col, bevel,
               rotation=(0, 0, atan2(u.y, u.x)))


def facade_item(name, p1, p2, u0, width, depth, height, z, mat, col, offset=0.0, bevel=0.0):
    a, b = Vector(p1), Vector(p2)
    u = (b - a).normalized()
    n = Vector((u.y, -u.x))
    q1 = a + u * u0 + n * offset
    q2 = q1 + u * width
    return segment_box(name, q1, q2, depth, height, z, mat, col, True, bevel)


def polygon_prism(name, points, z0, z1, mat, col):
    verts = [(x, y, z0) for x, y in points] + [(x, y, z1) for x, y in points]
    n = len(points)
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(mat)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    return obj


def materials():
    return {
        "brick": material("MCR1_Clay_Brick", (0.36, 0.19, 0.14)),
        "stone": material("MCR1_Clay_Stone", (0.50, 0.46, 0.39)),
        "stone_dark": material("MCR1_Clay_Stone_Shadow", (0.30, 0.29, 0.27)),
        "metal": material("MCR1_Clay_Black_Frame", (0.035, 0.04, 0.045), 0.42, 0.35),
        "sign": material("MCR1_Clay_Historic_Sign_Housing", (0.22, 0.20, 0.12), 0.55, 0.15),
        "glass": material("MCR1_Clay_Glass", (0.12, 0.18, 0.20), 0.16, 0.0, 0.34),
        "interior": material("MCR1_Clay_Interior", (0.31, 0.31, 0.29)),
        "floor": material("MCR1_Clay_Floor", (0.20, 0.21, 0.20)),
        "recess": material("MCR1_Clay_Recess", (0.055, 0.06, 0.065)),
        "ground": material("MCR1_Clay_Ground", (0.18, 0.19, 0.19)),
    }


FRONT = ((-3.4, -4.0), (5.4, -4.0))
CHAMFER = ((-4.4, -3.0), (-3.4, -4.0))
SIDE = ((-4.4, 2.8), (-4.4, -3.0))


def add_frame_set(prefix, seg, u0, width, bottom, height, divisions, mats, col, door=False):
    # Glazing is set into the facade; frame members sit proud enough to cast shadows.
    facade_item(prefix + "_Glass", *seg, u0, width, 0.045, height, bottom + height / 2,
                mats["glass"], col, offset=0.10)
    frame_w, frame_d = 0.075, 0.11
    for i in range(divisions + 1):
        x = u0 + width * i / divisions
        facade_item(f"{prefix}_Mullion_{i:02d}", *seg, x - frame_w / 2, frame_w, frame_d,
                    height + 0.11, bottom + height / 2, mats["metal"], col, offset=0.13, bevel=0.008)
    for j, zz in enumerate((bottom, bottom + height, bottom + height - 0.56)):
        facade_item(f"{prefix}_Rail_{j:02d}", *seg, u0, width, frame_d, 0.075, zz,
                    mats["metal"], col, offset=0.13, bevel=0.008)
    if not door:
        facade_item(prefix + "_Stall_Riser", *seg, u0 + 0.04, width - 0.08, 0.10, 0.48,
                    bottom + 0.24, mats["metal"], col, offset=0.13, bevel=0.01)


def build_shopfront(mats):
    shell = collection("MCR1_Shell")
    shop = collection("MCR1_Shopfront")
    glass = collection("MCR1_Glass")
    doors = collection("MCR1_Doors")
    frames = collection("MCR1_WindowFrames")
    signs = collection("MCR1_HistoricSignBoxes")

    footprint = [(-4.4, 2.8), (5.4, 2.8), (5.4, -4.0), (-3.4, -4.0), (-4.4, -3.0)]
    polygon_prism("MCR1_Interior_Floor_Slab", footprint, 0.0, 0.14, mats["floor"], shell)
    polygon_prism("MCR1_Ground_Header_Slab", footprint, 3.68, 3.92, mats["stone_dark"], shell)
    # Real room shell: rear/right walls, with the two public elevations left open.
    box("MCR1_Shell_RearWall", (9.8, 0.20, 3.55), (0.5, 2.70, 1.90), mats["interior"], shell)
    box("MCR1_Shell_RightWall", (0.20, 6.7, 3.55), (5.30, -0.45, 1.90), mats["interior"], shell)

    # Front: recessed entrance, broad display, narrow return pane.
    add_frame_set("MCR1_Door", FRONT, 0.38, 1.42, 0.12, 2.82, 1, mats, doors, door=True)
    facade_item("MCR1_Door_Recess_Ceiling", *FRONT, 0.28, 1.60, 0.76, 0.12, 2.99,
                mats["recess"], doors, offset=-0.23)
    facade_item("MCR1_Door_Threshold", *FRONT, 0.38, 1.42, 0.72, 0.08, 0.08,
                mats["stone_dark"], doors, offset=-0.23)
    add_frame_set("MCR1_Front_Display", FRONT, 1.88, 5.88, 0.12, 2.82, 3, mats, frames)
    add_frame_set("MCR1_Front_EndPane", FRONT, 7.84, 0.64, 0.12, 2.82, 1, mats, frames)
    for u in (0.08, 1.80, 7.76, 8.50):
        facade_item(f"MCR1_Front_Pier_{u:.2f}", *FRONT, u, 0.20, 0.30, 3.32, 1.74,
                    mats["metal"], shop, offset=0.08, bevel=0.015)

    # The short elevation wraps around the corner and contains one large display bay.
    add_frame_set("MCR1_Side_Display", SIDE, 3.05, 2.45, 0.12, 2.82, 2, mats, frames)
    facade_item("MCR1_Side_BackPier", *SIDE, 2.83, 0.24, 0.30, 3.32, 1.74,
                mats["metal"], shop, offset=0.08, bevel=0.015)
    facade_item("MCR1_Side_CornerPier", *SIDE, 5.50, 0.22, 0.30, 3.32, 1.74,
                mats["metal"], shop, offset=0.08, bevel=0.015)
    # Lower side wall beyond the retail bay, visible in the daylight context.
    facade_item("MCR1_Side_Masonry_Return", *SIDE, 0.0, 2.80, 0.35, 3.55, 1.82,
                mats["brick"], shell, offset=-0.02)

    # Narrow corner face and its glazing make the shop read as a true corner rather than two planes.
    add_frame_set("MCR1_Corner_Display", CHAMFER, 0.18, 1.05, 0.12, 2.82, 1, mats, glass)
    for u in (0.03, 1.25):
        facade_item(f"MCR1_Corner_Pier_{u:.2f}", *CHAMFER, u, 0.16, 0.28, 3.34, 1.76,
                    mats["metal"], shop, offset=0.08, bevel=0.012)

    # Old illuminated configuration: continuous shallow boxes, perforated-face carrier,
    # centre ring and a projecting vertical blade sign. Graphics remain for a later pass.
    for label, seg, u0, width in (
        ("Front", FRONT, 0.02, 8.70), ("Corner", CHAMFER, 0.02, 1.37), ("Side", SIDE, 2.83, 2.95)
    ):
        facade_item(f"MCR1_HistoricFascia_{label}_BackBox", *seg, u0, width, 0.28, 0.78, 3.27,
                    mats["sign"], signs, offset=0.10, bevel=0.025)
        facade_item(f"MCR1_HistoricFascia_{label}_FaceCarrier", *seg, u0 + 0.05, width - 0.10,
                    0.035, 0.62, 3.28, mats["sign"], signs, offset=0.28, bevel=0.018)
    # Circular sign: torus and central shallow disc, mounted to the front fascia.
    ring_u = 1.55
    a, b = Vector(FRONT[0]), Vector(FRONT[1])
    ring_xy = a + (b - a).normalized() * ring_u
    bpy.ops.mesh.primitive_torus_add(major_radius=0.42, minor_radius=0.055, major_segments=32,
                                    minor_segments=8, location=(ring_xy.x, -4.34, 3.28),
                                    rotation=(radians(90), 0, 0))
    ring = bpy.context.object
    ring.name = "MCR1_Historic_CircularSign_Ring"
    ring.data.materials.append(mats["sign"])
    move(ring, signs)
    cylinder("MCR1_Historic_CircularSign_Backplate", 0.34, 0.055, (ring_xy.x, -4.305, 3.28),
             mats["sign"], signs, 32, rotation=(radians(90), 0, 0))
    # Projecting vape blade near the corner, represented only as blank physical housing.
    box("MCR1_Historic_VapeBlade_Box", (0.32, 0.58, 0.92), (-3.52, -4.35, 3.58),
        mats["sign"], signs, 0.06)
    box("MCR1_Historic_VapeBlade_Bracket", (0.08, 0.34, 0.08), (-3.52, -4.16, 3.83),
        mats["metal"], signs, 0.015)
    return footprint


def upper_window(prefix, seg, u0, width, bottom, height, mats, facade, frames):
    facade_item(prefix + "_Recess", *seg, u0, width, 0.12, height, bottom + height / 2,
                mats["recess"], facade, offset=0.20, bevel=0.01)
    # Blocky stone jambs/lintel/sill capture the deep Victorian reveals.
    for suffix, x in (("LeftJamb", u0 - 0.10), ("RightJamb", u0 + width)):
        facade_item(prefix + "_" + suffix, *seg, x, 0.10, 0.23, height + 0.32,
                    bottom + height / 2, mats["stone"], frames, offset=0.22, bevel=0.018)
    facade_item(prefix + "_Lintel", *seg, u0 - 0.10, width + 0.20, 0.25, 0.20,
                bottom + height + 0.10, mats["stone"], frames, offset=0.22, bevel=0.018)
    facade_item(prefix + "_Sill", *seg, u0 - 0.12, width + 0.24, 0.30, 0.16,
                bottom - 0.06, mats["stone"], frames, offset=0.23, bevel=0.018)
    for frac in (0.0, 0.5, 1.0):
        facade_item(prefix + f"_FrameV_{frac}", *seg, u0 + width * frac - 0.035, 0.07,
                    0.10, height, bottom + height / 2, mats["metal"], frames, offset=0.27)
    for frac in (0.42, 0.70):
        facade_item(prefix + f"_FrameH_{frac}", *seg, u0, width, 0.10, 0.065,
                    bottom + height * frac, mats["metal"], frames, offset=0.27)


def build_historic_facade(mats, footprint):
    facade = collection("MCR1_HistoricFacade")
    stone = collection("MCR1_Stonework")
    frames = collection("MCR1_Upper_WindowFrames")
    cornice = collection("MCR1_Cornice")
    polygon_prism("MCR1_Historic_Upper_Mass", footprint, 3.92, 9.60, mats["brick"], facade)

    # Stone belt courses wrap all three public faces.
    for idx, (z, h, d) in enumerate(((4.12, 0.22, 0.32), (6.78, 0.20, 0.25), (8.92, 0.18, 0.28))):
        for label, seg in (("Front", FRONT), ("Corner", CHAMFER), ("Side", SIDE)):
            segment_box(f"MCR1_StoneCourse_{idx}_{label}", *seg, d, h, z, mats["stone"], stone, True, 0.018)
    # Layered main cornice gives the upper crop a convincing silhouette.
    for idx, (z, h, d) in enumerate(((9.40, 0.18, 0.32), (9.57, 0.20, 0.46), (9.73, 0.14, 0.56))):
        for label, seg in (("Front", FRONT), ("Corner", CHAMFER), ("Side", SIDE)):
            segment_box(f"MCR1_Cornice_{idx}_{label}", *seg, d, h, z, mats["stone"], cornice, True, 0.025)

    # Four tall front windows with masonry piers, matching the daylight rhythm.
    for i, u in enumerate((0.55, 2.55, 4.55, 6.55)):
        upper_window(f"MCR1_Front_UpperWindow_{i+1:02d}", FRONT, u, 1.18, 4.70, 2.02,
                     mats, facade, frames)
    for i, u in enumerate((0.50, 2.18)):
        upper_window(f"MCR1_Side_UpperWindow_{i+1:02d}", SIDE, u, 1.05, 4.70, 2.02,
                     mats, facade, frames)

    # Heavy corner stone pilasters and stepped capitals.
    for label, seg, u in (("Front", FRONT, -0.18), ("Side", SIDE, 5.72)):
        facade_item(f"MCR1_CornerPilaster_{label}", *seg, u, 0.38, 0.40, 5.55, 6.68,
                    mats["stone"], stone, offset=0.16, bevel=0.025)
        for j, (zz, ww, dd) in enumerate(((4.08, 0.48, 0.45), (6.86, 0.54, 0.50), (7.13, 0.68, 0.58))):
            facade_item(f"MCR1_CornerCapital_{label}_{j}", *seg, u - (ww - 0.38) / 2, ww,
                        dd, 0.20, zz, mats["stone"], stone, offset=0.17, bevel=0.025)

    # Distinctive circular opening on the chamfered corner.
    ch_a, ch_b = Vector(CHAMFER[0]), Vector(CHAMFER[1])
    mid = (ch_a + ch_b) / 2
    u = (ch_b - ch_a).normalized()
    n = Vector((u.y, -u.x))
    centre = mid + n * 0.34
    angle = atan2(u.y, u.x)
    cylinder("MCR1_Corner_Oculus_Recess", 0.43, 0.10, (centre.x, centre.y, 5.40),
             mats["recess"], facade, 32, rotation=(radians(90), 0, angle))
    bpy.ops.mesh.primitive_torus_add(major_radius=0.49, minor_radius=0.105, major_segments=32,
                                    minor_segments=10, location=(centre.x + n.x * 0.06, centre.y + n.y * 0.06, 5.40),
                                    rotation=(radians(90), 0, angle))
    surround = bpy.context.object
    surround.name = "MCR1_Corner_Oculus_StoneSurround"
    surround.data.materials.append(mats["stone"])
    move(surround, stone)
    # Keystones and lower scroll-like blocks, kept economical for real-time use.
    for j, (dx, dz, sx, sz) in enumerate(((0, 0.61, 0.28, 0.24), (-0.47, -0.38, 0.22, 0.34), (0.47, -0.38, 0.22, 0.34))):
        pos = centre + u * dx + n * 0.08
        box(f"MCR1_Oculus_Ornament_{j}", (sx, 0.22, sz), (pos.x, pos.y, 5.40 + dz),
            mats["stone"], stone, 0.05, rotation=(0, 0, angle))

    # Integrated stone entrance immediately right of the shop.
    portal = collection("MCR1_Integrated_Neighbour_StonePortal")
    box("MCR1_Portal_Recess", (1.58, 0.24, 3.25), (6.28, -3.93, 1.74), mats["recess"], portal)
    for x in (5.48, 7.08):
        box(f"MCR1_Portal_Jamb_{x}", (0.42, 0.48, 3.55), (x, -4.10, 1.78), mats["stone"], portal, 0.025)
    box("MCR1_Portal_Lintel", (2.05, 0.50, 0.40), (6.28, -4.11, 3.34), mats["stone"], portal, 0.03)
    # Shallow broken-pediment silhouette.
    for i, (x, rot) in enumerate(((5.82, radians(-23)), (6.74, radians(23)))):
        box(f"MCR1_Portal_PedimentSlope_{i}", (1.05, 0.46, 0.18), (x, -4.12, 3.82),
            mats["stone"], portal, 0.025, rotation=(0, rot, 0))
    return facade


def build_interior(mats):
    col = collection("MCR1_InteriorShell")
    box("MCR1_Interior_Ceiling", (8.8, 6.0, 0.12), (0.7, -0.35, 3.48), mats["interior"], col)
    box("MCR1_Interior_BackWall", (8.8, 0.16, 3.20), (0.7, 2.48, 1.75), mats["interior"], col)
    box("MCR1_Interior_RightWall", (0.16, 6.1, 3.20), (5.12, -0.40, 1.75), mats["interior"], col)
    # Architectural receiving zones for later modular shelving/counter placement.
    for i, x in enumerate((-2.6, -0.7, 1.2, 3.1)):
        box(f"MCR1_Interior_WallShelf_Blockout_{i}", (1.55, 0.38, 2.05), (x, 2.22, 1.23),
            mats["recess"], col, 0.025)
    box("MCR1_Interior_Counter_Blockout", (3.05, 0.72, 0.92), (3.25, 0.55, 0.52), mats["recess"], col, 0.04)
    # Low-poly ceiling-light housings only, without emissive materials.
    for row, y in enumerate((-2.7, -1.2, 0.3, 1.8)):
        for i, x in enumerate((-2.3, 0.0, 2.3, 4.35)):
            box(f"MCR1_CeilingLight_Housing_{row}_{i}", (1.35, 0.075, 0.055), (x, y, 3.36),
                mats["stone"], col, 0.012)


def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def setup_world_and_ground(mats):
    ctx = collection("MCR1_QC_Context_NONEXPORT")
    box("MCR1_QC_Ground", (28, 24, 0.12), (1.0, -4.0, -0.08), mats["ground"], ctx)
    scene = bpy.context.scene
    scene.world.color = (0.045, 0.045, 0.045)
    for name, loc, energy, size in (
        ("MCR1_QC_Key", (-8, -12, 14), 1600, 8.0),
        ("MCR1_QC_Fill", (10, -5, 9), 900, 7.0),
        ("MCR1_QC_Rim", (-2, 8, 12), 1200, 6.0),
    ):
        bpy.ops.object.light_add(type="AREA", location=loc)
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        point_at(light, (0, -1, 4.5))
        move(light, ctx)
    return ctx


def render_views():
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"
    RENDERS.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    cam.name = "MCR1_QC_Camera"
    cam.data.lens = 48
    scene.camera = cam
    views = {
        "01_straight_shopfront": ((1.1, -29.0, 4.9), (1.1, -3.5, 4.75), 52),
        "02_daylight_corner_three_quarter": ((-20.5, -23.0, 6.0), (-0.2, -2.0, 4.7), 52),
        "03_opposite_corner": ((21.5, -21.0, 5.8), (0.0, -1.8, 4.65), 52),
        "04_elevated_connection": ((-18.5, -22.0, 16.0), (-0.1, -1.5, 4.9), 55),
    }
    for slug, (loc, target, lens) in views.items():
        cam.location = loc
        cam.data.lens = lens
        point_at(cam, target)
        scene.render.filepath = str(RENDERS / f"mcr1_{slug}.png")
        bpy.ops.render.render(write_still=True)


def export_glb():
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.context.scene.objects:
        if obj.name.startswith("MCR1_QC_") or obj.type in {"CAMERA", "LIGHT"}:
            continue
        if obj.type in {"MESH", "CURVE"}:
            obj.select_set(True)
    GLB.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(GLB), export_format="GLB", use_selection=True,
                              export_apply=True, export_yup=True)


def apply_asset_transforms():
    """Leave the editable master export-ready with unit scale and zero rotation."""
    bpy.ops.object.select_all(action="DESELECT")
    assets = []
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and not obj.name.startswith("MCR1_QC_"):
            obj.select_set(True)
            assets.append(obj)
    if assets:
        bpy.context.view_layer.objects.active = assets[0]
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)


def main():
    clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene.unit_settings.scale_length = 1.0
    mats = materials()
    footprint = build_shopfront(mats)
    build_historic_facade(mats, footprint)
    build_interior(mats)
    setup_world_and_ground(mats)
    apply_asset_transforms()
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), check_existing=False)
    export_glb()
    render_views()
    meshes = [o for o in scene.objects if o.type == "MESH" and not o.name.startswith("MCR1_QC_")]
    tris = sum(sum(max(0, len(p.vertices) - 2) for p in o.data.polygons) for o in meshes)
    print(f"MCR1 geometry objects: {len(meshes)}")
    print(f"MCR1 geometry triangles: {tris}")
    print(f"Saved blend: {BLEND}")
    print(f"Exported GLB: {GLB}")
    print(f"QC renders: {RENDERS}")


if __name__ == "__main__":
    main()
