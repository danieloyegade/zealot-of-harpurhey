"""Build Cass Art with reference-derived surfaces and traced raised lettering."""

import os
import json
import struct
from math import radians
from pathlib import Path

import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLOCKOUT_PATH = PROJECT_ROOT / "blender" / "source" / "cass_art_blockout.blend"
BLEND_PATH = PROJECT_ROOT / "blender" / "source" / "cass_art.blend"
GLB_PATH = PROJECT_ROOT / "public" / "assets" / "models" / "cass_art.glb"
BLOCKOUT_RENDER_DIR = PROJECT_ROOT / "renders" / "cass-art-blockout"
FINAL_RENDER_DIR = PROJECT_ROOT / "renders" / "cass-art"
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "cass-art"

WIDTH = 18.0
DEPTH = 11.8
FACADE_HEIGHT = 4.62
BALCONY_SLAB_Z = 4.72
RAIL_TOP_Z = 6.12
FRONT_Y = 0.0


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


def material(name, color, roughness=0.78, metallic=0.0, alpha=1.0):
    result = bpy.data.materials.new(name)
    result.use_nodes = True
    result.diffuse_color = (*color, alpha)
    bsdf = result.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, alpha)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        bsdf.inputs["Transmission Weight"].default_value = 0.12
        result.surface_render_method = "DITHERED"
    return result


def image_texture(nodes, path, color_space="sRGB"):
    image = bpy.data.images.load(str(path), check_existing=True)
    image.colorspace_settings.name = color_space
    node = nodes.new("ShaderNodeTexImage")
    node.image = image
    node.interpolation = "Linear"
    return node


def textured_material(name, albedo, roughness, normal, base_roughness=0.72):
    result = material(name, (1.0, 1.0, 1.0), base_roughness)
    nodes = result.node_tree.nodes
    links = result.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    albedo_node = image_texture(nodes, TEXTURE_DIR / albedo)
    links.new(albedo_node.outputs["Color"], bsdf.inputs["Base Color"])
    if roughness:
        roughness_node = image_texture(nodes, TEXTURE_DIR / roughness, "Non-Color")
        links.new(roughness_node.outputs["Color"], bsdf.inputs["Roughness"])
    if normal:
        normal_tex = image_texture(nodes, TEXTURE_DIR / normal, "Non-Color")
        normal_node = nodes.new("ShaderNodeNormalMap")
        normal_node.inputs["Strength"].default_value = 0.34
        links.new(normal_tex.outputs["Color"], normal_node.inputs["Color"])
        links.new(normal_node.outputs["Normal"], bsdf.inputs["Normal"])
    return result


def decal_material(name, texture, roughness=0.48, emission=0.0):
    result = material(name, (1.0, 1.0, 1.0), roughness, alpha=0.0)
    result.surface_render_method = "DITHERED"
    result.use_transparency_overlap = False
    nodes = result.node_tree.nodes
    links = result.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    texture_node = image_texture(nodes, TEXTURE_DIR / texture)
    links.new(texture_node.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(texture_node.outputs["Alpha"], bsdf.inputs["Alpha"])
    if emission > 0:
        links.new(texture_node.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = emission
    return result


def move_to(obj, target):
    for source in list(obj.users_collection):
        source.objects.unlink(obj)
    target.objects.link(obj)
    return obj


def edge_treatment(obj, width=0.015):
    if width <= 0:
        return obj
    bevel = obj.modifiers.new("GameReady_Bevel", "BEVEL")
    bevel.width = width
    bevel.segments = 1
    return obj


def planar_uv(obj, horizontal_axis="X", vertical_axis="Z", flip_u=False):
    """Map each face from local bounds; used by exported glTF texture surfaces."""
    axes = {"X": 0, "Y": 1, "Z": 2}
    hi = axes[horizontal_axis]
    vi = axes[vertical_axis]
    coords_h = [vertex.co[hi] for vertex in obj.data.vertices]
    coords_v = [vertex.co[vi] for vertex in obj.data.vertices]
    min_h, max_h = min(coords_h), max(coords_h)
    min_v, max_v = min(coords_v), max(coords_v)
    span_h = max(max_h - min_h, 1e-6)
    span_v = max(max_v - min_v, 1e-6)
    uv_layer = obj.data.uv_layers.active or obj.data.uv_layers.new(name="UVMap")
    for polygon in obj.data.polygons:
        for loop_index in polygon.loop_indices:
            vertex = obj.data.vertices[obj.data.loops[loop_index].vertex_index]
            u = (vertex.co[hi] - min_h) / span_h
            v = (vertex.co[vi] - min_v) / span_v
            uv_layer.data[loop_index].uv = (1.0 - u if flip_u else u, v)
    return obj


def box(name, dimensions, location, mat, target, bevel=0.0, rotation=(0.0, 0.0, 0.0), uv_axes=None, flip_u=False):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        obj.data.materials.append(mat)
    if uv_axes:
        planar_uv(obj, uv_axes[0], uv_axes[1], flip_u)
    edge_treatment(obj, bevel)
    return move_to(obj, target)


def empty(name, location, target, display="ARROWS", size=0.32):
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    obj.empty_display_type = display
    obj.empty_display_size = size
    target.objects.link(obj)
    return obj


def linked_box(source, name, location, target):
    obj = bpy.data.objects.new(name, source.data)
    obj.location = location
    obj.rotation_euler = source.rotation_euler
    target.objects.link(obj)
    return obj


def create_blockout_materials():
    return {
        "facade": material("MAT_CASS_DarkFacade_PLACEHOLDER", (0.155, 0.17, 0.18)),
        "facade_alt": material("MAT_CASS_DarkFacadePanel_PLACEHOLDER", (0.205, 0.22, 0.225)),
        "glass": material("MAT_CASS_Glass_PLACEHOLDER", (0.22, 0.34, 0.39), 0.18, alpha=0.20),
        "metal": material("MAT_CASS_Metal_PLACEHOLDER", (0.055, 0.065, 0.07), 0.34, 0.45),
        "interior": material("MAT_CASS_InteriorWall_PLACEHOLDER", (0.72, 0.70, 0.64)),
        "floor": material("MAT_CASS_Floor_PLACEHOLDER", (0.38, 0.37, 0.35)),
        "shelving": material("MAT_CASS_Shelving_PLACEHOLDER", (0.52, 0.49, 0.43)),
        "wood": material("MAT_CASS_Wood_PLACEHOLDER", (0.43, 0.32, 0.23)),
        "fixture": material("MAT_CASS_PaintedFixture_PLACEHOLDER", (0.48, 0.49, 0.47)),
        "slogan": material("MAT_CASS_SloganSurface_PLACEHOLDER", (0.48, 0.49, 0.47)),
        "logo": material("MAT_CASS_LogoSurface_PLACEHOLDER", (0.48, 0.49, 0.47)),
        "address": material("MAT_CASS_AddressSurface_PLACEHOLDER", (0.48, 0.49, 0.47)),
        "window_display": material("MAT_CASS_WindowDisplaySurface_PLACEHOLDER", (0.22, 0.34, 0.39), alpha=0.0),
        "light": material("MAT_CASS_LightFixture_PLACEHOLDER", (0.88, 0.80, 0.64), 0.28),
    }


def create_final_materials():
    return {
        "facade": textured_material("MAT_CASS_DarkFacade", "cass-facade-albedo.png", "cass-facade-roughness.png", "cass-facade-normal.png"),
        "facade_alt": textured_material("MAT_CASS_DarkFacadePanel", "cass-facade-albedo.png", "cass-facade-roughness.png", "cass-facade-normal.png"),
        "glass": material("MAT_CASS_Glass", (0.34, 0.36, 0.35), 0.12, alpha=0.12),
        "metal": material("MAT_CASS_Metal", (0.035, 0.042, 0.046), 0.32, 0.58),
        "interior": material("MAT_CASS_InteriorWall", (0.78, 0.75, 0.68), 0.80),
        "floor": textured_material("MAT_CASS_Floor", "cass-floor-albedo.png", "cass-floor-roughness.png", "cass-floor-normal.png", 0.67),
        "shelving": material("MAT_CASS_Shelving", (0.68, 0.62, 0.52), 0.66),
        "wood": material("MAT_CASS_Wood", (0.48, 0.32, 0.18), 0.62),
        "fixture": material("MAT_CASS_PaintedFixture", (0.48, 0.49, 0.47), 0.70),
        "slogan": material("MAT_CASS_Slogan", (0.88, 0.235, 0.048), 0.42),
        "logo": decal_material("MAT_CASS_LogoSign", "cass-logo-sign.png", 0.52),
        "address": decal_material("MAT_CASS_Address", "cass-address.png", 0.44, 0.12),
        "window_display": decal_material("MAT_CASS_WindowDisplay", "cass-window-display-reference.png", 0.58),
        "right_display": decal_material("MAT_CASS_RightWindowDisplay", "cass-right-display-reference.png", 0.58),
        "light": material("MAT_CASS_LightFixture", (0.88, 0.80, 0.64), 0.28),
    }


def replace_blockout_materials(blockout_mats, final_mats):
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        for slot in obj.material_slots:
            for key, old_material in blockout_mats.items():
                if slot.material == old_material:
                    slot.material = final_mats[key]
                    break


def create_hierarchy():
    master = collection("CASS_ART_MASTER")
    groups = {
        "master": master,
        "exterior": collection("CASS_ExteriorShell", master),
        "panels": collection("CASS_FacadePanels", master),
        "fascia": collection("CASS_Fascia", master),
        "slogan": collection("CASS_SloganArea", master),
        "logo": collection("CASS_LogoSign", master),
        "entrance": collection("CASS_Entrance", master),
        "glass": collection("CASS_Glass", master),
        "interior": collection("CASS_InteriorShell", master),
        "wall_shelves": collection("CASS_WallShelving", master),
        "centre_shelves": collection("CASS_CentreShelving", master),
        "paper": collection("CASS_PaperRacks", master),
        "counter": collection("CASS_Counter", master),
        "ceiling": collection("CASS_Ceiling", master),
        "balcony": collection("CASS_BalconyRail", master),
        "fixtures": collection("CASS_ExteriorFixtures", master),
        "anchors": collection("CASS_InteractionAnchors", master),
    }
    return groups


def build_blockout(mats, groups):
    # The photographed building reads as a long, low, panel-clad frontage.
    box("CASS_InteriorFloor", (WIDTH - 0.34, DEPTH, 0.12), (0, DEPTH / 2, 0.0), mats["floor"], groups["interior"], uv_axes=("X", "Y"))
    box("CASS_InteriorCeiling", (WIDTH - 0.34, DEPTH, 0.14), (0, DEPTH / 2, 4.28), mats["interior"], groups["interior"])
    box("CASS_InteriorWall_Back", (WIDTH - 0.34, 0.16, 4.28), (0, DEPTH - 0.08, 2.14), mats["interior"], groups["interior"])
    box("CASS_InteriorWall_Left", (0.18, DEPTH, 4.28), (-WIDTH / 2 + 0.09, DEPTH / 2, 2.14), mats["interior"], groups["interior"])
    box("CASS_InteriorWall_Right", (0.18, DEPTH, 4.28), (WIDTH / 2 - 0.09, DEPTH / 2, 2.14), mats["interior"], groups["interior"])

    # Fascia, end returns, plinth, and principal piers are separate depth layers.
    box("CASS_Fascia_Back", (WIDTH, 0.42, 1.20), (0, 0.17, 3.72), mats["facade"], groups["fascia"], 0.018, uv_axes=("X", "Z"))
    box("CASS_Fascia_Cap", (WIDTH + 0.12, 0.54, 0.16), (0, 0.10, 4.34), mats["metal"], groups["fascia"])
    box("CASS_LowerPlinth", (WIDTH, 0.50, 0.36), (0, 0.12, 0.18), mats["facade"], groups["exterior"], 0.012)
    pier_specs = (
        ("LeftBoundary", -8.72, 0.55),
        ("MainLeft", -7.18, 0.38),
        ("MainRight", 1.16, 0.36),
        ("DoorRight", 3.16, 0.38),
        ("RightBoundary", 8.70, 0.60),
    )
    for label, x, width in pier_specs:
        box(f"CASS_FacadePier_{label}", (width, 0.54, 3.18), (x, 0.10, 1.76), mats["facade_alt"], groups["panels"], 0.012, uv_axes=("X", "Z"))

    # Narrow left bay, dominant central display, entrance, and right display bay.
    glazing = (
        ("CASS_Glass_Main01", -7.93, 1.05),
        ("CASS_Glass_Main02", -2.99, 7.82),
        ("CASS_Glass_Entrance", 2.15, 1.48),
        ("CASS_Glass_Main03", 5.93, 4.92),
    )
    for name, x, width in glazing:
        box(name, (width, 0.035, 2.64), (x, -0.205, 1.67), mats["glass"], groups["glass"])
        box(f"{name}_Head", (width + 0.12, 0.24, 0.13), (x, -0.10, 3.04), mats["metal"], groups["exterior"])
        box(f"{name}_Sill", (width + 0.12, 0.30, 0.13), (x, -0.13, 0.34), mats["metal"], groups["exterior"])

    # The door is a separate hinged leaf inside a deeper entrance reveal.
    box("CASS_Entrance_RecessFloor", (1.58, 0.72, 0.08), (2.15, 0.24, 0.04), mats["floor"], groups["entrance"])
    box("CASS_Door", (1.30, 0.055, 2.55), (2.15, 0.04, 1.61), mats["glass"], groups["entrance"])
    box("CASS_DoorFrame_Left", (0.11, 0.34, 2.75), (1.45, 0.01, 1.68), mats["metal"], groups["entrance"])
    box("CASS_DoorFrame_Right", (0.11, 0.34, 2.75), (2.85, 0.01, 1.68), mats["metal"], groups["entrance"])
    box("CASS_DoorFrame_Head", (1.51, 0.34, 0.12), (2.15, 0.01, 3.02), mats["metal"], groups["entrance"])

    # Blank physical surfaces carry exact signage later; no words are geometry.
    box("CASS_Slogan_DecalSurface", (9.90, 0.018, 0.54), (-1.55, -0.062, 3.82), mats["slogan"], groups["slogan"], uv_axes=("X", "Z"))
    box("CASS_Address_DecalSurface", (0.78, 0.018, 0.46), (-8.12, -0.162, 3.78), mats["address"], groups["slogan"], uv_axes=("X", "Z"))

    # Balcony platform blockout and building return above the facade.
    box("CASS_Balcony_LowerBeam", (WIDTH + 0.18, 0.72, 0.24), (0, 0.20, BALCONY_SLAB_Z), mats["metal"], groups["balcony"], 0.012)
    box("CASS_UpperWall_Context", (WIDTH, 2.4, 2.0), (0, 1.45, 5.55), mats["facade_alt"], groups["exterior"])
    box("CASS_BalconyRail_Blockout", (WIDTH - 0.28, 0.12, 1.16), (0, -0.18, 5.42), mats["metal"], groups["balcony"])

    # Coarse, traversable furniture blocks establish the aisle plan.
    for index, y in enumerate((2.1, 4.2, 6.3, 8.4, 10.5)):
        box(f"CASS_WallShelf_Left_Blockout_{index:02d}", (0.58, 1.55, 2.25), (-8.48, y, 1.13), mats["shelving"], groups["wall_shelves"], 0.018)
        box(f"CASS_WallShelf_Right_Blockout_{index:02d}", (0.58, 1.55, 2.25), (8.48, y, 1.13), mats["shelving"], groups["wall_shelves"], 0.018)
    for index, (x, y) in enumerate(((-4.6, 3.0), (-1.7, 3.0), (-4.6, 6.2), (-1.7, 6.2), (1.4, 6.2), (4.5, 6.2))):
        box(f"CASS_CentreShelf_Blockout_{index:02d}", (2.05, 0.82, 1.12), (x, y, 0.56), mats["shelving"], groups["centre_shelves"], 0.025)
    box("CASS_Counter_Blockout", (3.25, 0.88, 1.02), (5.15, 9.70, 0.51), mats["wood"], groups["counter"], 0.035)
    box("CASS_PaperRack_Blockout_01", (1.20, 0.70, 1.78), (-6.25, 1.30, 0.89), mats["shelving"], groups["paper"], 0.025)
    box("CASS_PaperRack_Blockout_02", (1.20, 0.70, 1.78), (5.70, 1.30, 0.89), mats["shelving"], groups["paper"], 0.025)


def add_window_display(mats, groups):
    # Preserve the artwork's aspect ratio; the older full-pane fit flattened
    # the record into an ellipse. The logo is supplied by the real photo below.
    for index, (u0, v0, u1, v1) in enumerate(((0, 0, .22, .69), (.22, 0, 1, 1))):
        width, height = 3.96, 2.64
        mesh = bpy.data.meshes.new(f"CASS_WindowDisplay_{index}_Mesh")
        mesh.from_pydata([(-3.40+u*width, -.235, .35+v*height)
                          for u,v in ((u0,v0),(u1,v0),(u1,v1),(u0,v1))], [], [(0,1,2,3)])
        mesh.materials.append(mats["window_display"])
        uv = mesh.uv_layers.new(name="UVMap")
        for loop, coords in zip(uv.data, ((u0,v0),(u1,v0),(u1,v1),(u0,v1))):
            loop.uv = coords
        obj = bpy.data.objects.new(f"CASS_WindowDisplay_DecalSurface_{index}", mesh)
        groups["glass"].objects.link(obj)
    box("CASS_RightWindowDisplay_DecalSurface", (2.47, .008, 2.47), (5.93, -.239, 1.64), mats["right_display"], groups["glass"], uv_axes=("X", "Z"))


def add_reference_details(mats, groups):
    """Use the actual photographed outlines and surfaces, not substitute text."""
    old = bpy.data.objects.get("CASS_Slogan_DecalSurface")
    bpy.data.objects.remove(old, do_unlink=True)
    data = json.loads((TEXTURE_DIR / "cass-lettering-contours.json").read_text())
    xmin, ymin, xmax, ymax = data["bounds_px"]
    scale = 9.90 / (xmax - xmin)
    curve = bpy.data.curves.new("CASS_PhotographedLetterOutlines", "CURVE")
    curve.dimensions = "2D"
    curve.resolution_u = 1
    curve.fill_mode = "BOTH"
    curve.extrude = 0.012
    for contour in data["contours"]:
        spline = curve.splines.new("POLY")
        points = contour[:-1]
        spline.points.add(len(points) - 1)
        for vertex, (x, y) in zip(spline.points, points):
            vertex.co = ((x - xmin) * scale, (ymax - y) * scale, 0, 1)
        spline.use_cyclic_u = True
    letters = bpy.data.objects.new("CASS_Slogan_DecalSurface", curve)
    groups["slogan"].objects.link(letters)
    letters.location = (-6.5, -0.12, 3.39)
    letters.rotation_euler.x = radians(90)
    curve.materials.append(mats["slogan"])
    bpy.ops.object.select_all(action="DESELECT")
    letters.select_set(True)
    bpy.context.view_layer.objects.active = letters
    bpy.ops.object.convert(target="MESH")
    box("CASS_Slogan_MountingRail", (9.94, 0.028, 0.035), (-1.55, -0.087, 3.57), mats["metal"], groups["slogan"])

    # Shared photograph sampled with UVs: sticker pier, chalk tag and alarm.
    # No people, pavement or window reflections enter these selected regions.
    photo = bpy.data.images.load(str(PROJECT_ROOT / "references/architecture/buildings/cass-art/DSC06343.JPG"), check_existing=True)
    photo.scale(3072, 2048)
    photo.pack()
    surface = material("MAT_CASS_PhotographedDetails", (1, 1, 1), 0.78)
    node = surface.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = photo
    surface.node_tree.links.new(node.outputs["Color"], surface.node_tree.nodes.get("Principled BSDF").inputs["Base Color"])

    def photo_face(name, width, height, x, y, z, rect):
        # rect uses coordinates in the 1920 x 1280 review of the source photo.
        left, top, right, bottom = rect
        mesh = bpy.data.meshes.new(name + "_Mesh")
        mesh.from_pydata([(x-width/2,y,z-height/2), (x+width/2,y,z-height/2),
                         (x+width/2,y,z+height/2), (x-width/2,y,z+height/2)], [], [(0,1,2,3)])
        mesh.materials.append(surface)
        uv = mesh.uv_layers.new(name="UVMap")
        for item, coords in zip(uv.data, [(left/1920,1-bottom/1280), (right/1920,1-bottom/1280),
                                         (right/1920,1-top/1280), (left/1920,1-top/1280)]):
            item.uv = coords
        obj = bpy.data.objects.new(name, mesh)
        groups["panels"].objects.link(obj)
        return obj

    photo_face("CASS_FasciaWeathering_Photo", 18.0, 1.20, 0, -0.043, 3.72, (170,75,1690,231))
    photo_face("CASS_StickeredPier_Photo", 0.38, 3.12, -7.18, -0.177, 1.76, (2,323,166,1056))
    photo_face("CASS_TaggedPier_Photo", 0.38, 3.12, 3.16, -0.177, 1.76, (1587,323,1802,1056))
    photo_face("CASS_AlarmLabel_Photo", 0.39, 0.27, 7.10, -0.225, 4.06, (1749,96,1826,144))
    photo_face("CASS_LogoAndPoster_Photo", 1.18, 2.30, -5.65, -0.231, 1.73, (318,354,512,780))
    photo_face("CASS_DoorPopcorn_Photo", 1.10, 2.03, 2.10, -0.235, 1.47, (1270,498,1468,950))
    # Recessed vent/kick strip beneath the large display, sampled from the same photo.
    photo_face("CASS_KickVents_Photo", 7.82, .27, -2.99, -0.145, .16, (215,995,1234,1052))


def add_panel_divisions(mats, groups):
    for index, x in enumerate((-8.35, -6.65, -4.35, -2.05, 0.25, 3.65, 5.55, 7.45)):
        box(f"CASS_FacadePanelJoint_V_{index:02d}", (0.026, 0.025, 1.08), (x, -0.055, 3.74), mats["metal"], groups["panels"])
    # The main display is a single uninterrupted pane in the photographs.
    # High transom on entrance/right-hand glazing.
    box("CASS_Entrance_Transom", (1.49, 0.12, 0.10), (2.15, -0.24, 2.63), mats["metal"], groups["entrance"])
    box("CASS_RightWindow_Transom", (4.92, 0.12, 0.10), (5.93, -0.24, 2.63), mats["metal"], groups["exterior"])
    box("CASS_DoorHandle", (0.045, 0.14, 0.48), (2.66, -0.07, 1.24), mats["metal"], groups["entrance"], 0.012)


def add_projecting_sign_and_fixtures(mats, groups):
    box("CASS_LogoSign_Bracket", (0.16, 0.82, 0.12), (7.80, -0.43, 4.03), mats["metal"], groups["logo"])
    box("CASS_LogoSign_Housing", (0.18, 0.86, 0.68), (7.80, -0.76, 3.87), mats["metal"], groups["logo"], 0.025)
    box("CASS_LogoSign_DecalSurface", (0.185, 0.66, 0.52), (7.696, -0.80, 3.87), mats["logo"], groups["logo"], uv_axes=("Y", "Z"), flip_u=True)
    for index, x in enumerate((-5.9, -0.6, 5.3)):
        box(f"CASS_ExteriorLight_{index + 1:02d}", (0.42, 0.34, 0.16), (x, -0.19, 4.43), mats["metal"], groups["fixtures"], 0.02, rotation=(radians(-12), 0, 0))
    box("CASS_AlarmBox", (0.42, 0.16, 0.30), (7.10, -0.14, 4.06), mats["fixture"], groups["fixtures"], 0.025)


def replace_balcony_blockout(mats, groups):
    blockout = bpy.data.objects.get("CASS_BalconyRail_Blockout")
    if blockout:
        bpy.data.objects.remove(blockout, do_unlink=True)
    rail_y = -0.23
    box("CASS_BalconyRail_Bottom", (WIDTH - 0.32, 0.11, 0.11), (0, rail_y, 4.88), mats["metal"], groups["balcony"])
    box("CASS_BalconyRail_Top", (WIDTH - 0.25, 0.13, 0.13), (0, rail_y, RAIL_TOP_Z), mats["metal"], groups["balcony"])
    panel_width = 1.46
    start_x = -8.20
    for panel in range(12):
        cx = start_x + panel * panel_width
        box(f"CASS_Balcony_Post_{panel:02d}", (0.10, 0.13, 1.30), (cx - panel_width / 2, rail_y, 5.50), mats["metal"], groups["balcony"])
        box(f"CASS_Balcony_MidRail_{panel:02d}", (panel_width, 0.08, 0.07), (cx, rail_y, 5.48), mats["metal"], groups["balcony"])
        for bar in range(5):
            x = cx - panel_width * 0.40 + bar * panel_width * 0.20
            box(f"CASS_Balcony_GridV_{panel:02d}_{bar:02d}", (0.025, 0.055, 1.12), (x, rail_y, 5.50), mats["metal"], groups["balcony"])
        for bar in range(4):
            z = 5.02 + bar * 0.29
            box(f"CASS_Balcony_GridH_{panel:02d}_{bar:02d}", (panel_width - 0.10, 0.055, 0.025), (cx, rail_y, z), mats["metal"], groups["balcony"])
    box("CASS_Balcony_Post_End", (0.10, 0.13, 1.30), (8.55, rail_y, 5.50), mats["metal"], groups["balcony"])


def replace_shelf_blockouts(mats, groups):
    blockouts = [obj for obj in bpy.data.objects if "Shelf_" in obj.name and "Blockout" in obj.name]
    for obj in blockouts:
        bpy.data.objects.remove(obj, do_unlink=True)

    # Each unit has a back, sides, cap, and four shelves. Modules remain distinct.
    def wall_module(name, x, y, facing):
        depth = 0.58
        width = 1.55
        inner_x = x + facing * 0.21
        box(f"{name}_Back", (0.08, width, 2.30), (x, y, 1.15), mats["shelving"], groups["wall_shelves"])
        for side, dy in (("A", -width / 2), ("B", width / 2)):
            box(f"{name}_Side_{side}", (depth, 0.07, 2.30), (inner_x, y + dy, 1.15), mats["shelving"], groups["wall_shelves"])
        for level, z in enumerate((0.16, 0.68, 1.20, 1.72, 2.25)):
            box(f"{name}_Shelf_{level:02d}", (depth, width, 0.07), (inner_x, y, z), mats["shelving"], groups["wall_shelves"])

    for index, y in enumerate((2.1, 4.2, 6.3, 8.4, 10.5)):
        wall_module(f"CASS_Shelf_Wall_Module_L{index:02d}", -8.64, y, 1)
        wall_module(f"CASS_Shelf_Wall_Module_R{index:02d}", 8.64, y, -1)

    def centre_module(name, x, y):
        box(f"{name}_Base", (2.05, 0.82, 0.16), (x, y, 0.08), mats["shelving"], groups["centre_shelves"], 0.018)
        box(f"{name}_Spine", (1.85, 0.10, 1.08), (x, y, 0.63), mats["shelving"], groups["centre_shelves"])
        for side, dy in (("Front", -0.30), ("Back", 0.30)):
            for level, z in enumerate((0.42, 0.78, 1.10)):
                box(f"{name}_{side}_Shelf_{level:02d}", (1.95, 0.34, 0.065), (x, y + dy, z), mats["shelving"], groups["centre_shelves"])

    for index, (x, y) in enumerate(((-4.6, 3.0), (-1.7, 3.0), (-4.6, 6.2), (-1.7, 6.2), (1.4, 6.2), (4.5, 6.2))):
        centre_module(f"CASS_Shelf_Centre_Module_{index:02d}", x, y)


def refine_paper_racks_and_counter(mats, groups):
    for name in ("CASS_PaperRack_Blockout_01", "CASS_PaperRack_Blockout_02", "CASS_Counter_Blockout"):
        obj = bpy.data.objects.get(name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)
    for index, x in enumerate((-6.25, 5.70)):
        name = f"CASS_PaperRack_Module_{index + 1:02d}"
        box(f"{name}_Base", (1.30, 0.76, 0.14), (x, 1.30, 0.07), mats["shelving"], groups["paper"], 0.02)
        box(f"{name}_Back", (1.24, 0.10, 1.72), (x, 1.62, 0.92), mats["shelving"], groups["paper"])
        for slot in range(5):
            y = 1.02 + slot * 0.13
            z = 0.34 + slot * 0.27
            box(f"{name}_Tray_{slot:02d}", (1.18, 0.46, 0.055), (x, y, z), mats["shelving"], groups["paper"], rotation=(radians(10), 0, 0))
    box("CASS_Counter_Base", (3.20, 0.84, 0.92), (5.15, 9.70, 0.46), mats["wood"], groups["counter"], 0.028)
    box("CASS_Counter_ToeKick", (3.00, 0.10, 0.14), (5.15, 9.25, 0.14), mats["metal"], groups["counter"])
    box("CASS_Counter_Top", (3.38, 1.00, 0.10), (5.15, 9.70, 0.97), mats["wood"], groups["counter"], 0.025)
    box("CASS_Counter_RearShelf", (2.60, 0.46, 1.55), (5.15, 10.95, 0.78), mats["shelving"], groups["counter"], 0.018)


def add_ceiling_tracks(mats, groups):
    for index, x in enumerate((-6.1, -2.1, 1.9, 5.9)):
        box(f"CASS_LightTrack_{index + 1:02d}", (0.055, 9.9, 0.055), (x, 5.75, 4.08), mats["metal"], groups["ceiling"])
        for fixture, y in enumerate((1.5, 3.7, 5.9, 8.1, 10.3)):
            box(f"CASS_LightTrack_{index + 1:02d}_Fixture_{fixture + 1:02d}", (0.18, 0.28, 0.18), (x, y, 3.96), mats["light"], groups["ceiling"], 0.018)


def add_anchors(groups):
    empty("CASS_EntranceTriggerAnchor", (2.15, -0.82, 0.05), groups["anchors"], "CUBE", 0.45)
    empty("CASS_StaffAnchor", (5.15, 10.35, 0.05), groups["anchors"])
    empty("CASS_CustomerInteractionAnchor", (5.15, 8.85, 0.05), groups["anchors"])
    empty("CASS_Light_Window", (0.0, 0.65, 3.68), groups["anchors"], "CIRCLE", 0.32)
    for index, x in enumerate((-6.1, -2.1, 1.9, 5.9)):
        empty(f"CASS_LightTrackAnchor_{index + 1:02d}", (x, 5.75, 4.02), groups["anchors"], "CIRCLE", 0.24)


def point_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_render_helpers():
    helpers = collection("CASS_RENDER_HELPERS_REVIEW_ONLY")
    world = bpy.context.scene.world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.055, 0.06, 0.068, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.34
    lights = (
        ("CASS_Review_Key", (-8.5, -8.0, 11.0), 1650, 7.0, (1.0, 0.82, 0.68), (0, 3.0, 2.5)),
        ("CASS_Review_Fill", (9.5, -4.5, 8.5), 1200, 6.0, (0.60, 0.75, 1.0), (1.0, 2.0, 2.2)),
        ("CASS_Review_Interior", (0.0, 6.5, 4.0), 1350, 5.0, (1.0, 0.83, 0.62), (0.0, 4.0, 1.2)),
    )
    for name, location, energy, size, color, target in lights:
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.shape = "RECTANGLE"
        light.data.size = size
        light.data.color = color
        point_at(light, target)
        move_to(light, helpers)
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "CASS_Review_Camera"
    camera.data.sensor_width = 36
    move_to(camera, helpers)
    bpy.context.scene.camera = camera
    return helpers, camera


def remove_render_helpers(helpers):
    bpy.data.collections.remove(helpers, do_unlink=True)


def render_views(camera, output_dir):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1080
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.render.film_transparent = False
    output_dir.mkdir(parents=True, exist_ok=True)
    views = (
        ("view-a-straight-on.png", (0.0, -27.0, 3.25), (0.0, 2.0, 3.05), 52),
        ("view-b-oblique-street.png", (-15.8, -20.0, 4.1), (0.0, 2.8, 2.6), 46),
        ("view-c-entrance-looking-in.png", (2.15, -2.65, 1.68), (2.15, 6.6, 1.45), 35),
        ("view-d-interior-to-glazing.png", (0.0, 10.2, 1.72), (0.0, -0.35, 1.55), 38),
        ("view-e-elevated-balcony.png", (13.6, -15.8, 10.2), (0.0, 1.0, 3.7), 48),
    )
    for filename, location, target, lens in views:
        camera.location = location
        camera.data.lens = lens
        point_at(camera, target)
        scene.render.filepath = str(output_dir / filename)
        bpy.ops.render.render(write_still=True)
        print(f"Rendered {scene.render.filepath}")


def apply_mesh_transforms():
    bpy.ops.object.select_all(action="DESELECT")
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    for obj in meshes:
        obj.select_set(True)
    if meshes:
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.ops.object.select_all(action="DESELECT")


def validate_scene(stage):
    required = (
        "CASS_Slogan_DecalSurface",
        "CASS_Address_DecalSurface",
        "CASS_Glass_Main01",
        "CASS_Glass_Main02",
        "CASS_Glass_Main03",
        "CASS_Glass_Entrance",
        "CASS_Door",
        "CASS_EntranceTriggerAnchor",
        "CASS_StaffAnchor",
        "CASS_CustomerInteractionAnchor",
    )
    missing = [name for name in required if bpy.data.objects.get(name) is None]
    if missing and stage == "final":
        raise RuntimeError(f"Missing required objects: {missing}")
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH" and not obj.name.startswith("CASS_Review")]
    triangles = sum(sum(max(0, len(poly.vertices) - 2) for poly in obj.data.polygons) for obj in meshes)
    dimensions = Vector((0, 0, 0))
    print(f"Validation ({stage}): {len(meshes)} meshes, approximately {triangles} triangles")
    print(f"Validation ({stage}): metric scale, Z-up, ground plane Z=0, footprint {WIDTH:.1f} x {DEPTH:.1f} m")


def export_glb():
    GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
    runtime = collection("CASS_RUNTIME_EXPORT_TEMP")
    material_groups = {}
    # Preserve the authored component hierarchy in the .blend, but collapse the
    # runtime copy by material so shelves and balcony bars do not become hundreds
    # of Three.js draw calls.
    source_meshes = [
        obj for obj in bpy.context.scene.objects
        if obj.type == "MESH" and not obj.name.startswith("CASS_Review")
    ]
    for source in source_meshes:
        material_name = source.data.materials[0].name if source.data.materials else "Unassigned"
        material_groups.setdefault(material_name, []).append(source)

    runtime_meshes = []
    for material_name, objects in material_groups.items():
        clean_name = material_name.replace("MAT_CASS_", "").replace("_PLACEHOLDER", "")
        object_name = f"CASS_Runtime_{clean_name}"
        vertices = []
        faces = []
        texcoords = []
        for source in objects:
            vertex_offset = len(vertices)
            vertices.extend(tuple(source.matrix_world @ vertex.co) for vertex in source.data.vertices)
            faces.extend(tuple(vertex_offset + index for index in polygon.vertices) for polygon in source.data.polygons)
            source_uv = source.data.uv_layers.active
            texcoords.extend(tuple(source_uv.data[i].uv) if source_uv else (0.0, 0.0)
                             for polygon in source.data.polygons for i in polygon.loop_indices)
        mesh = bpy.data.meshes.new(f"{object_name}_Mesh")
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        uv = mesh.uv_layers.new(name="UVMap")
        for loop, coords in zip(uv.data, texcoords):
            loop.uv = coords
        mat = bpy.data.materials.get(material_name)
        if mat:
            mesh.materials.append(mat)
        joined = bpy.data.objects.new(object_name, mesh)
        runtime.objects.link(joined)
        runtime_meshes.append(joined)

    runtime_anchors = []
    source_anchors = [
        obj for obj in bpy.context.scene.objects
        if obj.type == "EMPTY" and obj.name.startswith("CASS_")
    ]
    for source in source_anchors:
        duplicate = source.copy()
        duplicate.name = source.name
        runtime.objects.link(duplicate)
        runtime_anchors.append(duplicate)

    bpy.ops.object.select_all(action="DESELECT")
    export_objects = runtime_meshes + runtime_anchors
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
        export_image_format="WEBP",
        export_image_quality=88,
    )
    bpy.ops.object.select_all(action="DESELECT")
    print(f"Exported runtime GLB: {GLB_PATH} ({len(runtime_meshes)} consolidated meshes, {len(runtime_anchors)} anchors)")
    with GLB_PATH.open("rb") as handle:
        handle.seek(12)
        length, kind = struct.unpack("<II", handle.read(8))
        gltf = json.loads(handle.read(length))
    for mesh in gltf["meshes"]:
        for primitive in mesh["primitives"]:
            mat = gltf["materials"][primitive["material"]]
            if mat.get("pbrMetallicRoughness", {}).get("baseColorTexture"):
                assert "TEXCOORD_0" in primitive["attributes"], f"Lost UVs: {mat['name']}"
    bpy.data.collections.remove(runtime, do_unlink=True)


def verify_glb_round_trip():
    before = set(bpy.data.objects.keys())
    verify_collection = collection("CASS_GLB_ROUNDTRIP_VERIFY")
    bpy.ops.import_scene.gltf(filepath=str(GLB_PATH))
    imported = [obj for obj in bpy.context.selected_objects]
    for obj in imported:
        move_to(obj, verify_collection)
    mesh_count = sum(obj.type == "MESH" for obj in imported)
    empty_names = {obj.name for obj in imported if obj.type == "EMPTY"}
    if mesh_count == 0:
        raise RuntimeError("GLB round-trip produced no meshes")
    for required in ("CASS_EntranceTriggerAnchor", "CASS_StaffAnchor", "CASS_CustomerInteractionAnchor"):
        if not any(name.startswith(required) for name in empty_names):
            raise RuntimeError(f"GLB round-trip lost anchor {required}")
    print(f"GLB round-trip: {mesh_count} mesh nodes and {len(empty_names)} empties imported successfully")
    bpy.data.collections.remove(verify_collection, do_unlink=True)
    for obj_name in set(bpy.data.objects.keys()) - before:
        obj = bpy.data.objects.get(obj_name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)


def main():
    clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"
    mats = create_blockout_materials()
    groups = create_hierarchy()

    build_blockout(mats, groups)
    BLOCKOUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLOCKOUT_PATH), check_existing=False)
    if not os.environ.get("CASS_SKIP_RENDERS"):
        helpers, camera = add_render_helpers()
        render_views(camera, BLOCKOUT_RENDER_DIR)
        remove_render_helpers(helpers)
    print(f"Saved Cass Art blockout: {BLOCKOUT_PATH}")

    final_mats = create_final_materials()
    replace_blockout_materials(mats, final_mats)
    mats = final_mats

    add_panel_divisions(mats, groups)
    add_window_display(mats, groups)
    add_projecting_sign_and_fixtures(mats, groups)
    add_reference_details(mats, groups)
    replace_balcony_blockout(mats, groups)
    replace_shelf_blockouts(mats, groups)
    refine_paper_racks_and_counter(mats, groups)
    add_ceiling_tracks(mats, groups)
    add_anchors(groups)
    apply_mesh_transforms()
    validate_scene("final")
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), check_existing=False)
    print(f"Saved Cass Art source: {BLEND_PATH}")
    export_glb()
    verify_glb_round_trip()
    if not os.environ.get("CASS_SKIP_RENDERS"):
        helpers, camera = add_render_helpers()
        render_views(camera, FINAL_RENDER_DIR)
        remove_render_helpers(helpers)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), check_existing=False)


if __name__ == "__main__":
    main()
