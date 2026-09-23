"""Create the modular Coral betting-shop environment kit from coral2.png.

The asset is deliberately geometry/material based so the editable master and all
runtime GLBs are self-contained and do not depend on external texture files.
"""

from math import radians
from pathlib import Path

import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = PROJECT_ROOT / "blender" / "source"
MODEL_ROOT = PROJECT_ROOT / "public" / "assets" / "models"
RENDER_ROOT = PROJECT_ROOT / "renders" / "coral-shop"
BLEND_PATH = SOURCE_ROOT / "harpurhey-coral-shop.blend"
PREVIEW_PATH = RENDER_ROOT / "harpurhey-coral-shop-preview.png"

FRONT_Y = -3.35
ASSET_COLLECTIONS = {
    "shopfront": "Coral_Shopfront",
    "upper-block": "Coral_Upper_Block",
    "window-module": "Coral_Window_Module",
    "bin": "Coral_Bin",
    "streetlight": "Coral_Streetlight",
    "bollard": "Coral_Bollard",
}


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        if collection.name != "Collection":
            bpy.data.collections.remove(collection)
    root = bpy.data.collections.get("Collection")
    if root:
        root.name = "Coral_Architecture_Kit"


def collection(name):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def move_to(obj, col):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    col.objects.link(obj)
    return obj


def mat(name, color, roughness=0.75, metallic=0.0, emission=None, strength=0.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.diffuse_color = (*color, alpha)
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emission:
        emission_input = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
        if emission_input:
            emission_input.default_value = (*emission, 1.0)
        strength_input = bsdf.inputs.get("Emission Strength")
        if strength_input:
            strength_input.default_value = strength
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        m.surface_render_method = "DITHERED"
    return m


def brick_mat(name, base):
    m = mat(name, base, 0.94)
    nodes = m.node_tree.nodes
    links = m.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    tex = nodes.new("ShaderNodeTexBrick")
    tex.inputs["Color1"].default_value = (*base, 1.0)
    tex.inputs["Color2"].default_value = (base[0] * 0.5, base[1] * 0.48, base[2] * 0.43, 1.0)
    tex.inputs["Mortar"].default_value = (0.08, 0.07, 0.065, 1.0)
    tex.inputs["Scale"].default_value = 7.5
    tex.inputs["Mortar Size"].default_value = 0.025
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.22
    bump.inputs["Distance"].default_value = 0.08
    links.new(tex.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    return m


def concrete_mat(name, base):
    m = mat(name, base, 0.96)
    nodes = m.node_tree.nodes
    links = m.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 8.0
    noise.inputs["Detail"].default_value = 4.0
    noise.inputs["Roughness"].default_value = 0.78
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (base[0] * 0.58, base[1] * 0.58, base[2] * 0.58, 1)
    ramp.color_ramp.elements[1].color = (*base, 1)
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.18
    bump.inputs["Distance"].default_value = 0.05
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def box(name, dims, loc, material, col, bevel=0.0, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material:
        obj.data.materials.append(material)
    if bevel:
        mod = obj.modifiers.new("Edge_Soften", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    move_to(obj, col)
    return obj


def cylinder(name, radius, depth, loc, material, col, vertices=16, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    if material:
        obj.data.materials.append(material)
    move_to(obj, col)
    return obj


def text_obj(name, body, loc, size, material, col, extrude=0.035, align="CENTER"):
    bpy.ops.object.text_add(location=loc, rotation=(radians(90), 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Curve"
    obj.data.body = body
    obj.data.align_x = align
    obj.data.align_y = "CENTER"
    obj.data.size = size
    obj.data.extrude = extrude
    obj.data.bevel_depth = 0.008
    obj.data.materials.append(material)
    move_to(obj, col)
    return obj


def rail_between(name, start, end, radius, material, col, vertices=10):
    a, b = Vector(start), Vector(end)
    direction = b - a
    obj = cylinder(name, radius, direction.length, (a + b) / 2, material, col, vertices)
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    return obj


def quad(name, coords, material, col):
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(coords, [], [(0, 1, 2, 3)])
    mesh.materials.append(material)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    return obj


def build_store_window(col, materials, x, width, name, hero=False):
    y = FRONT_Y - 0.18
    z0, height = 0.55, 2.35
    box(f"{name}_Glass", (width, 0.055, height), (x, y, z0 + height / 2), materials["glass"], col)
    frame = materials["aluminium"]
    for sx in (-1, 1):
        box(f"{name}_FrameV_{sx}", (0.075, 0.09, height + 0.12), (x + sx * width / 2, y - 0.025, z0 + height / 2), frame, col, 0.01)
    # The reference has closely spaced aluminium mullions rather than broad,
    # uninterrupted panes. Keep each clear pane close to a metre wide.
    subdivisions = max(1, round(width / 1.05))
    for division in range(1, subdivisions):
        mx = x - width / 2 + width * division / subdivisions
        box(f"{name}_Mullion_{division}", (0.055, 0.10, height), (mx, y - 0.035, z0 + height / 2), frame, col, 0.008)
    for z in (z0, z0 + height, z0 + height - 0.52):
        box(f"{name}_FrameH_{z:.2f}", (width + 0.07, 0.09, 0.075), (x, y - 0.025, z), frame, col, 0.01)
    # Characteristic Coral blue/green printed privacy band.
    box(f"{name}_PrintedBlue", (width - 0.12, 0.035, 1.0), (x, y - 0.075, 1.22), materials["print_blue"], col)
    box(f"{name}_PrintedGreen", (width - 0.12, 0.038, 0.24), (x, y - 0.085, 0.66), materials["print_green"], col)
    count = max(3, int(width / 0.48))
    palette = [materials["print_white"], materials["print_tan"], materials["print_blue_light"]]
    for i in range(count):
        px = x - width / 2 + 0.22 + i * ((width - 0.44) / max(1, count - 1))
        pz = 1.18 + (0.18 if i % 3 == 0 else -0.04 if i % 3 == 1 else 0.11)
        box(f"{name}_CoralMotif_{i}", (0.22 + 0.08 * (i % 2), 0.026, 0.3 + 0.07 * (i % 3)), (px, y - 0.105, pz), palette[i % len(palette)], col, 0.08, rotation=(0, 0, radians((i % 3 - 1) * 18)))
    for i in range(max(1, int(width / 1.65))):
        tx = x - width / 2 + 0.7 + i * 1.65
        text_obj(f"{name}_MiniLogo_{i}", "CORAL", (tx, y - 0.13, 0.76), 0.13, materials["white"], col, 0.006)
    if hero:
        # Paper notice and simple interior silhouettes visible through the glass.
        box(f"{name}_Notice", (0.42, 0.025, 0.58), (x + width * 0.34, y - 0.11, 1.72), materials["paper"], col, 0.01)
        for j in range(4):
            box(f"{name}_NoticeLine_{j}", (0.3, 0.015, 0.018), (x + width * 0.34, y - 0.13, 1.88 - j * 0.09), materials["ink"], col)
    return box(f"{name}_Origin", (0.01, 0.01, 0.01), (x, y, z0), materials["black"], col)


def build_shop_interior(materials, col):
    """Layer a readable betting-shop interior behind the transparent glazing."""
    # Replace the old solid façade backing with a shallow but real room.
    box("Coral_Interior_Floor", (16.0, 6.0, 0.12), (0, -0.05, 0.12), materials["interior_floor"], col)
    box("Coral_Interior_Ceiling", (16.0, 6.0, 0.12), (0, -0.05, 2.86), materials["interior_ceiling"], col)
    box("Coral_Interior_Back_Wall", (16.0, 0.18, 2.75), (0, 2.92, 1.48), materials["interior_blue"], col)
    for x in (-7.82, 7.82):
        box(f"Coral_Interior_Side_Wall_{x}", (0.22, 6.0, 2.82), (x, -0.05, 1.47), materials["dark_wall"], col)

    # Repeating illuminated information panels and dark vertical separators
    # reproduce the layered poster/terminal rhythm seen through the windows.
    for i in range(10):
        x = -6.95 + i * 1.54
        panel_mat = materials["interior_screen"] if i % 3 else materials["interior_poster"]
        box(f"Coral_Interior_Back_Panel_{i}", (1.08, 0.075, 1.42), (x, 2.78, 1.43), panel_mat, col, 0.025)
        box(f"Coral_Interior_Back_Panel_Header_{i}", (0.86, 0.025, 0.10), (x, 2.72, 1.94), materials["fluorescent"], col, 0.018)
        for line in range(4):
            box(f"Coral_Interior_Back_Panel_Line_{i}_{line}", (0.72 - line * 0.06, 0.018, 0.035), (x, 2.70, 1.72 - line * 0.16), materials["paper"], col, 0.008)

    # Customer counters and angled terminal screens provide parallax through
    # the glass instead of reading as a flat printed wall.
    for i, x in enumerate((-6.2, -3.7, 0.25, 2.75, 5.35)):
        box(f"Coral_Interior_Counter_{i}", (1.55, 0.68, 0.72), (x, 0.32, 0.48), materials["counter_blue"], col, 0.055)
        box(f"Coral_Interior_Counter_Top_{i}", (1.68, 0.78, 0.08), (x, 0.28, 0.87), materials["counter_top"], col, 0.025)
        box(f"Coral_Interior_Terminal_{i}", (0.72, 0.12, 0.52), (x, -0.02, 1.22), materials["screen_dark"], col, 0.035, rotation=(radians(-9), 0, 0))
        box(f"Coral_Interior_Terminal_Glow_{i}", (0.60, 0.018, 0.38), (x, -0.09, 1.23), materials["screen_glow"], col, 0.018, rotation=(radians(-9), 0, 0))

    # Ceiling light banks visible in the clear clerestory strip.
    for row, y in enumerate((-1.65, 0.2, 1.75)):
        for i, x in enumerate((-5.8, -2.9, 0.0, 2.9, 5.8)):
            box(f"Coral_Interior_Ceiling_Light_{row}_{i}", (1.55, 0.16, 0.055), (x, y, 2.76), materials["fluorescent"], col, 0.035)

    # A few suspended signs break up the otherwise regular shop interior.
    for i, (x, y) in enumerate(((-4.9, 1.15), (1.25, 1.25), (4.45, 1.0))):
        box(f"Coral_Interior_Hanging_Sign_{i}", (0.78, 0.08, 0.52), (x, y, 2.08), materials["interior_poster"], col, 0.025)
        rail_between(f"Coral_Interior_Sign_Wire_{i}", (x, y, 2.34), (x, y, 2.72), 0.012, materials["metal_dark"], col, 6)


def build_shopfront(materials):
    col = collection(ASSET_COLLECTIONS["shopfront"])
    brick = materials["brick"]
    # Ground-floor structure. The room is genuinely open behind the windows;
    # only the rear, sides, floor and header are solid.
    build_shop_interior(materials, col)
    box("Coral_Ground_Rear_Shell", (17.4, 0.32, 4.25), (0, 3.19, 2.125), materials["dark_wall"], col)
    box("Coral_Ground_Left_Return", (0.45, 6.7, 4.25), (-8.48, 0, 2.125), brick, col)
    box("Coral_Ground_Right_Return", (0.45, 6.7, 4.25), (8.48, 0, 2.125), brick, col)
    box("Coral_Ground_Header", (17.4, 6.7, 0.34), (0, 0, 4.08), materials["dark_wall"], col)
    box("Coral_Left_Brick_Pier", (1.05, 0.52, 4.18), (-8.18, FRONT_Y + 0.05, 2.09), brick, col, 0.025)
    box("Coral_Right_Brick_Pier", (1.15, 0.52, 4.18), (8.13, FRONT_Y + 0.05, 2.09), brick, col, 0.025)
    box("Coral_Central_Stone_Pier", (0.42, 0.48, 3.02), (-2.38, FRONT_Y - 0.03, 1.52), materials["concrete"], col, 0.025)
    box("Coral_Fascia", (15.95, 0.42, 1.02), (0, FRONT_Y - 0.06, 3.45), materials["coral_blue"], col, 0.035)
    box("Coral_Fascia_Top_Trim", (16.15, 0.5, 0.12), (0, FRONT_Y - 0.08, 4.0), materials["navy"], col, 0.018)
    box("Coral_Fascia_Bottom_Trim", (16.15, 0.5, 0.10), (0, FRONT_Y - 0.08, 2.94), materials["navy"], col, 0.018)
    text_obj("Coral_Main_Sign", "CORAL", (-0.15, FRONT_Y - 0.31, 3.48), 0.78, materials["sign_white"], col, 0.045)
    # Three-color wave logo at right of wordmark.
    ly = FRONT_Y - 0.34
    quad("Coral_Logo_Green", [(2.95, ly, 3.70), (3.65, ly, 3.78), (3.53, ly, 3.55), (2.86, ly, 3.50)], materials["logo_green"], col)
    quad("Coral_Logo_Yellow", [(2.88, ly - 0.01, 3.50), (3.53, ly - 0.01, 3.55), (3.40, ly - 0.01, 3.32), (2.80, ly - 0.01, 3.28)], materials["logo_yellow"], col)
    quad("Coral_Logo_Red", [(2.80, ly - 0.02, 3.28), (3.40, ly - 0.02, 3.32), (3.27, ly - 0.02, 3.10), (2.72, ly - 0.02, 3.07)], materials["logo_red"], col)
    # Store glazing mirrors the reference: 3 bays, narrow glazed door, 5 bays.
    build_store_window(col, materials, -6.32, 2.85, "Coral_Left_Window_A")
    build_store_window(col, materials, -3.95, 1.82, "Coral_Left_Window_B")
    build_store_window(col, materials, -1.55, 1.18, "Coral_Door_Glass", hero=True)
    build_store_window(col, materials, 0.55, 2.70, "Coral_Right_Window_A")
    build_store_window(col, materials, 3.48, 2.95, "Coral_Right_Window_B")
    build_store_window(col, materials, 6.45, 2.85, "Coral_Right_Window_C", hero=True)
    # Door hardware and entry details.
    door_x = -1.55
    for sx in (-1, 1):
        box(f"Coral_Door_Frame_V_{sx}", (0.075, 0.12, 2.72), (door_x + sx * 0.64, FRONT_Y - 0.18, 1.45), materials["aluminium"], col, 0.012)
    for z in (0.10, 2.80):
        box(f"Coral_Door_Frame_H_{z}", (1.35, 0.12, 0.075), (door_x, FRONT_Y - 0.18, z), materials["aluminium"], col, 0.012)
    box("Coral_Door_Glass_Inset", (1.15, 0.055, 2.38), (door_x, FRONT_Y - 0.21, 1.46), materials["glass"], col)
    box("Coral_Door_Kickplate", (1.05, 0.04, 0.28), (door_x, FRONT_Y - 0.255, 0.30), materials["metal_dark"], col)
    box("Coral_Door_Handle", (0.035, 0.14, 0.58), (door_x + 0.42, FRONT_Y - 0.31, 1.42), materials["metal"], col, 0.012)
    box("Coral_Letterbox", (0.38, 0.06, 0.11), (door_x, FRONT_Y - 0.30, 1.25), materials["brass"], col, 0.015)
    # Continuous fluorescent strip above glazing and blue tiled plinth.
    for i, x in enumerate((-6.35, -4.05, -1.55, 0.65, 3.45, 6.4)):
        box(f"Coral_Fluorescent_{i}", (2.0 if i not in (2, 5) else 1.25, 0.09, 0.07), (x, FRONT_Y - 0.33, 2.84), materials["fluorescent"], col, 0.025)
    for i in range(32):
        x = -7.75 + i * 0.5
        box(f"Coral_Blue_Plith_Tile_{i}", (0.48, 0.18, 0.28), (x, FRONT_Y - 0.11, 0.25), materials["tile_blue"], col, 0.018)
    # Small wall keypad, alarm and side entrance stair.
    box("Coral_Entry_Keypad", (0.18, 0.08, 0.34), (-0.72, FRONT_Y - 0.31, 1.86), materials["cream"], col, 0.025)
    box("Coral_Alarm_Box", (0.23, 0.11, 0.30), (-8.02, FRONT_Y - 0.31, 3.72), materials["cream"], col, 0.035)
    cylinder("Coral_Downpipe", 0.055, 3.55, (7.92, FRONT_Y - 0.30, 1.82), materials["black_metal"], col, 10)
    box("Coral_Right_Service_Door", (1.26, 0.14, 2.35), (8.92, FRONT_Y + 2.55, 1.55), materials["black"], col, 0.025)
    box("Coral_Right_Service_Light", (0.52, 0.28, 0.16), (8.92, FRONT_Y + 2.32, 2.92), materials["lamp_glow"], col, 0.035)
    for step in range(8):
        box(f"Coral_Right_Stair_{step}", (1.5, 0.42, 0.18), (8.95, FRONT_Y + 0.25 + step * 0.36, 0.09 + step * 0.17), materials["stair"] , col, 0.025)
    box("Coral_Right_Stair_Wall", (0.28, 3.8, 2.35), (9.77, FRONT_Y + 1.4, 1.18), brick, col, 0.02)
    box("Coral_Right_Stair_Door", (1.12, 0.12, 2.12), (8.95, -0.28, 2.19), materials["black_metal"], col, 0.025)
    box("Coral_Right_Stair_Door_Light", (0.62, 0.06, 0.12), (8.95, -0.36, 3.34), materials["lamp_glow"], col, 0.025)
    for side in (-0.68, 0.68):
        rail_between(
            f"Coral_Right_Stair_Handrail_{side}",
            (8.95 + side, FRONT_Y + 0.16, 0.85),
            (8.95 + side, -0.45, 2.25),
            0.035,
            materials["black_metal"],
            col,
            10,
        )
        for i in range(4):
            y = FRONT_Y + 0.35 + i * 0.72
            z = 0.70 + i * 0.34
            rail_between(f"Coral_Right_Stair_Rail_Post_{side}_{i}", (8.95 + side, y, z - 0.55), (8.95 + side, y, z + 0.25), 0.028, materials["black_metal"], col, 8)
    return col


def build_upper_window(materials, parent_col, x, z, width=1.15, lit=False, prefix="Upper"):
    glass = materials["window_lit"] if lit else materials["window_dark"]
    box(f"{prefix}_Glass_{x:.2f}_{z:.2f}", (width, 0.055, 0.98), (x, FRONT_Y - 0.07, z), glass, parent_col)
    for sx in (-1, 1):
        box(f"{prefix}_VFrame_{sx}_{x:.2f}_{z:.2f}", (0.065, 0.10, 1.08), (x + sx * width / 2, FRONT_Y - 0.105, z), materials["window_frame"], parent_col, 0.008)
    for sz in (-1, 1):
        box(f"{prefix}_HFrame_{sz}_{x:.2f}_{z:.2f}", (width + 0.07, 0.10, 0.065), (x, FRONT_Y - 0.105, z + sz * 0.50), materials["window_frame"], parent_col, 0.008)
    box(f"{prefix}_Mullion_{x:.2f}_{z:.2f}", (0.055, 0.11, 1.0), (x + width * 0.20, FRONT_Y - 0.12, z), materials["window_frame"], parent_col)
    if lit:
        box(f"{prefix}_Curtain_{x:.2f}_{z:.2f}", (width * 0.34, 0.025, 0.82), (x - width * 0.27, FRONT_Y - 0.11, z), materials["curtain"], parent_col)


def build_window_module(materials):
    col = collection(ASSET_COLLECTIONS["window-module"])
    box("Coral_Window_Module_Wall", (1.55, 0.34, 1.42), (0, 0, 0.71), materials["brick"], col)
    # Front at local y=-0.2 for independent export.
    old_front = FRONT_Y
    glass = box("Coral_Window_Module_Glass", (1.15, 0.05, 0.98), (0, -0.2, 0.73), materials["window_dark"], col)
    for x in (-0.575, 0.575, 0.2):
        box(f"Coral_Window_Module_V_{x}", (0.065, 0.08, 1.06), (x, -0.24, 0.73), materials["window_frame"], col)
    for z in (0.2, 1.26):
        box(f"Coral_Window_Module_H_{z}", (1.22, 0.08, 0.065), (0, -0.24, z), materials["window_frame"], col)
    return col


def build_upper_block(materials):
    col = collection(ASSET_COLLECTIONS["upper-block"])
    box("Coral_Upper_Block_Shell", (22.5, 6.7, 9.0), (0, 0, 8.75), materials["upper_brick"], col)
    # Concrete overhang directly above the shop.
    box("Coral_Concrete_Canopy", (18.6, 1.18, 0.62), (0, FRONT_Y - 0.08, 4.55), materials["concrete"], col, 0.025)
    box("Coral_Canopy_Weather_Line", (18.2, 0.045, 0.10), (0, FRONT_Y - 0.69, 4.34), materials["soot"], col, 0.02)
    for i in range(9):
        x = -7.8 + i * 1.95
        cylinder(f"Coral_Canopy_Drain_{i}", 0.055, 0.5, (x, FRONT_Y - 0.62, 4.18), materials["metal_dark"], col, 10)
        rail_between(
            f"Coral_Canopy_Hook_{i}",
            (x, FRONT_Y - 0.62, 4.22),
            (x, FRONT_Y - 0.84, 4.43),
            0.035,
            materials["metal_dark"],
            col,
            8,
        )
    # Long horizontal residential window bands over three floors.
    xs = [-9.4, -8.0, -6.6, -5.2, -3.8, -2.4, -1.0, 0.4, 1.8, 3.2, 4.6, 6.0, 7.4, 8.8]
    lit_sets = ({2, 8, 11}, {1, 5, 9, 12}, {3, 7, 13})
    for floor, z in enumerate((6.35, 8.55, 10.75)):
        box(f"Coral_Window_Band_Recess_{floor}", (20.4, 0.18, 1.45), (0, FRONT_Y + 0.06, z), materials["recess"], col)
        for idx, x in enumerate(xs):
            build_upper_window(materials, col, x, z, 1.16, idx in lit_sets[floor], f"Coral_F{floor+1}")
    # Raised walkway/parapet with weathered timber rails and mesh infill.
    box("Coral_Deck_Slab", (19.6, 2.35, 0.32), (0, FRONT_Y - 0.42, 5.08), materials["concrete"], col, 0.02)
    for index, z in enumerate((5.62, 6.12, 6.60)):
        # Small alternating offsets keep the boards from looking factory-perfect.
        box(f"Coral_Timber_Rail_{z}", (19.1 - index * 0.10, 0.24, 0.20), ((index - 1) * 0.045, FRONT_Y - 1.45, z), materials["timber"], col, 0.045, rotation=(0, radians((index - 1) * 0.18), radians((1 - index) * 0.12)))
    box("Coral_Railing_Mesh", (19.0, 0.035, 1.34), (0, FRONT_Y - 1.39, 6.03), materials["mesh_dark"], col)
    for x in range(-9, 10, 1):
        box(f"Coral_Railing_Post_{x}", (0.09, 0.18, 1.62), (x, FRONT_Y - 1.43, 5.96), materials["metal_dark"], col, 0.02)
    box("Coral_Railing_Top_Pipe", (19.4, 0.10, 0.10), (0, FRONT_Y - 1.44, 6.94), materials["metal_dark"], col, 0.04)
    # Utility pipe and clipped cable run along the wall behind the walkway.
    rail_between("Coral_Walkway_Utility_Pipe", (-9.3, FRONT_Y - 0.34, 5.43), (9.25, FRONT_Y - 0.34, 5.43), 0.045, materials["black_metal"], col, 10)
    for x in (-8.2, -5.0, -1.8, 1.4, 4.6, 7.8):
        box(f"Coral_Utility_Pipe_Clip_{x}", (0.08, 0.10, 0.18), (x, FRONT_Y - 0.34, 5.43), materials["metal_dark"], col, 0.015)
    # Patch panels, vents and water stains break the monolithic façade.
    for i, (x, z, w) in enumerate(((-7.8, 7.52, 1.6), (-4.2, 9.68, 1.1), (5.9, 7.52, 1.4), (8.1, 11.85, 1.2))):
        box(f"Coral_Upper_Repair_Patch_{i}", (w, 0.035, 0.34), (x, FRONT_Y - 0.12, z), materials["repair_patch"], col, 0.012)
    for i, x in enumerate((-10.2, 9.95)):
        box(f"Coral_Upper_Vent_{i}", (0.48, 0.10, 0.68), (x, FRONT_Y - 0.15, 7.45), materials["metal_dark"], col, 0.03)
        for slat in range(4):
            box(f"Coral_Upper_Vent_Slat_{i}_{slat}", (0.36, 0.04, 0.035), (x, FRONT_Y - 0.22, 7.65 - slat * 0.14), materials["window_frame"], col)
    # Roofline and a stepped right-hand service volume.
    box("Coral_Upper_Parapet", (22.7, 6.9, 0.48), (0, 0, 13.48), materials["concrete_dark"], col, 0.025)
    box("Coral_Right_Service_Block", (4.2, 5.9, 5.25), (11.0, 0.1, 9.0), materials["concrete_dark"], col, 0.035)
    return col


def build_bin(materials):
    col = collection(ASSET_COLLECTIONS["bin"])
    # Local reusable asset, origin at pavement level.
    box("Coral_Bin_Body", (0.78, 0.72, 1.18), (0, 0, 0.61), materials["bin_green"], col, 0.08)
    box("Coral_Bin_Front_Panel", (0.60, 0.08, 0.82), (0, -0.39, 0.58), materials["bin_green_dark"], col, 0.05)
    box("Coral_Bin_Lid", (0.92, 0.82, 0.16), (0, -0.01, 1.25), materials["bin_dark"], col, 0.07)
    cylinder("Coral_Bin_Domed_Top", 0.44, 0.18, (0, -0.01, 1.39), materials["bin_dark"], col, 16)
    box("Coral_Bin_Slot", (0.46, 0.06, 0.16), (0, -0.47, 1.29), materials["black"], col, 0.055)
    for x in (-0.32, 0.32):
        cylinder(f"Coral_Bin_Wheel_{x}", 0.11, 0.09, (x, 0.31, 0.13), materials["black"], col, 12, rotation=(0, radians(90), 0))
    # Stylised flower/graffiti marks seen on the reference bin.
    for i, (x, z) in enumerate(((-0.2, 0.62), (0.08, 0.47), (0.22, 0.78))):
        for p in range(5):
            angle = radians(p * 72)
            bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=4, radius=0.055, location=(x + 0.07 * __import__('math').cos(angle), -0.445, z + 0.07 * __import__('math').sin(angle)))
            petal = bpy.context.object
            petal.name = f"Coral_Bin_Graffiti_{i}_{p}"
            petal.scale = (1.0, 0.22, 1.45)
            petal.data.materials.append(materials["graffiti_pink"] if i != 1 else materials["graffiti_cream"])
            move_to(petal, col)
    return col


def build_streetlight(materials):
    col = collection(ASSET_COLLECTIONS["streetlight"])
    cylinder("Coral_Lamp_Post", 0.105, 5.9, (0, 0, 2.95), materials["black_metal"], col, 16)
    cylinder("Coral_Lamp_Base", 0.22, 0.22, (0, 0, 0.11), materials["black_metal"], col, 16)
    cylinder("Coral_Lamp_Collar", 0.15, 0.16, (0, 0, 5.75), materials["metal_dark"], col, 16)
    rail_between("Coral_Lamp_Arm", (0, 0, 5.72), (0.72, 0, 5.72), 0.075, materials["black_metal"], col, 12)
    bpy.ops.mesh.primitive_cone_add(vertices=20, radius1=0.56, radius2=0.30, depth=0.22, location=(0.76, 0, 5.58))
    hood = bpy.context.object
    hood.name = "Coral_Lamp_Hood"
    hood.data.materials.append(materials["black_metal"])
    move_to(hood, col)
    cylinder("Coral_Lamp_Lens", 0.31, 0.035, (0.76, 0, 5.44), materials["lamp_glow"], col, 20)
    return col


def build_bollard(materials):
    col = collection(ASSET_COLLECTIONS["bollard"])
    cylinder("Coral_Bollard_Body", 0.18, 1.0, (0, 0, 0.5), materials["black_metal"], col, 8)
    cylinder("Coral_Bollard_Base", 0.24, 0.10, (0, 0, 0.05), materials["black_metal"], col, 8)
    cylinder("Coral_Bollard_Reflector", 0.19, 0.13, (0, 0, 0.77), materials["reflector"], col, 8)
    bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=0.20, radius2=0.12, depth=0.18, location=(0, 0, 1.09))
    cap = bpy.context.object
    cap.name = "Coral_Bollard_Cap"
    cap.data.materials.append(materials["black_metal"])
    move_to(cap, col)
    return col


def duplicate_collection_objects(source_col, target_col, prefix, offset):
    for obj in source_col.objects:
        dup = obj.copy()
        if obj.data:
            dup.data = obj.data.copy()
        dup.name = f"{prefix}_{obj.name}"
        dup.location = obj.location + Vector(offset)
        target_col.objects.link(dup)


def build_scene_context(materials, assets):
    col = collection("Coral_Scene_Context")
    # Pavement, curb and wet road are scene context but excluded from the building GLB.
    box("Coral_Pavement", (24, 4.2, 0.20), (0, -5.45, 0.0), materials["pavement"], col, 0.02)
    box("Coral_Curb", (24, 0.32, 0.32), (0, -7.55, 0.04), materials["curb"], col, 0.025)
    box("Coral_Road", (28, 13, 0.10), (0, -14.1, -0.12), materials["wet_road"], col)
    # Double yellow curb markings.
    for y in (-7.85, -8.13):
        box(f"Coral_Yellow_Line_{y}", (23.5, 0.10, 0.025), (0, y, -0.045), materials["road_yellow"], col, 0.025)
    duplicate_collection_objects(assets["bin"], col, "Placed", (-8.4, -5.05, 0.1))
    duplicate_collection_objects(assets["streetlight"], col, "Placed", (-9.7, -6.2, 0.1))
    for i, x in enumerate((-6.7, 7.3, 10.2)):
        duplicate_collection_objects(assets["bollard"], col, f"Placed_{i}", (x, -7.15, 0.1))
    return col


def materials():
    return {
        "brick": brick_mat("Coral_Brick", (0.25, 0.085, 0.045)),
        "upper_brick": brick_mat("Coral_Upper_Brick", (0.12, 0.075, 0.06)),
        "concrete": concrete_mat("Coral_Concrete", (0.38, 0.37, 0.33)),
        "concrete_dark": concrete_mat("Coral_Dark_Concrete", (0.22, 0.22, 0.21)),
        "pavement": concrete_mat("Coral_Wet_Pavement", (0.28, 0.27, 0.24)),
        "curb": concrete_mat("Coral_Curb_Material", (0.38, 0.37, 0.34)),
        "stair": concrete_mat("Coral_Stair_Material", (0.33, 0.31, 0.27)),
        "dark_wall": mat("Coral_Dark_Wall", (0.035, 0.04, 0.045), 0.95),
        "soot": mat("Coral_Soot_Stain", (0.025, 0.022, 0.019), 0.98, alpha=0.76),
        "repair_patch": concrete_mat("Coral_Repair_Patch", (0.29, 0.28, 0.25)),
        "recess": mat("Coral_Window_Recess", (0.025, 0.03, 0.04), 0.92),
        "coral_blue": mat("Coral_Sign_Blue", (0.015, 0.12, 0.31), 0.66),
        "navy": mat("Coral_Navy_Trim", (0.01, 0.035, 0.075), 0.70),
        "tile_blue": mat("Coral_Blue_Tile", (0.015, 0.11, 0.28), 0.45),
        "sign_white": mat("Coral_Sign_Letters", (0.79, 0.78, 0.72), 0.55),
        "white": mat("Coral_White_Print", (0.74, 0.78, 0.76), 0.75),
        "logo_green": mat("Coral_Logo_Green", (0.16, 0.48, 0.16), 0.55),
        "logo_yellow": mat("Coral_Logo_Yellow", (0.95, 0.66, 0.04), 0.55),
        "logo_red": mat("Coral_Logo_Red", (0.78, 0.12, 0.08), 0.55),
        "glass": mat("Coral_Store_Glass", (0.08, 0.21, 0.28), 0.16, 0.05, alpha=0.46),
        "window_dark": mat("Coral_Upper_Window_Dark", (0.015, 0.035, 0.07), 0.25, 0.05),
        "window_lit": mat("Coral_Upper_Window_Lit", (0.85, 0.32, 0.045), 0.38, emission=(1.0, 0.24, 0.025), strength=2.5),
        "curtain": mat("Coral_Curtain", (0.8, 0.56, 0.25), 0.92),
        "window_frame": mat("Coral_Window_Frame", (0.34, 0.36, 0.35), 0.52, 0.3),
        "aluminium": mat("Coral_Aluminium", (0.48, 0.53, 0.54), 0.38, 0.58),
        "metal": mat("Coral_Metal", (0.42, 0.45, 0.44), 0.34, 0.7),
        "metal_dark": mat("Coral_Dark_Metal", (0.045, 0.05, 0.052), 0.48, 0.62),
        "black_metal": mat("Coral_Black_Metal", (0.012, 0.014, 0.016), 0.42, 0.72),
        "brass": mat("Coral_Brass", (0.48, 0.28, 0.07), 0.38, 0.66),
        "fluorescent": mat("Coral_Fluorescent", (0.7, 0.95, 1.0), 0.2, emission=(0.65, 0.9, 1.0), strength=4.0),
        "interior_floor": mat("Coral_Interior_Floor", (0.12, 0.14, 0.15), 0.54),
        "interior_ceiling": mat("Coral_Interior_Ceiling", (0.56, 0.59, 0.57), 0.84),
        "interior_blue": mat("Coral_Interior_Blue", (0.025, 0.085, 0.15), 0.88),
        "interior_screen": mat("Coral_Interior_Screen", (0.10, 0.22, 0.29), 0.38, emission=(0.05, 0.22, 0.32), strength=0.55),
        "interior_poster": mat("Coral_Interior_Poster", (0.46, 0.52, 0.48), 0.72),
        "counter_blue": mat("Coral_Counter_Blue", (0.018, 0.075, 0.135), 0.76),
        "counter_top": mat("Coral_Counter_Top", (0.22, 0.24, 0.23), 0.46),
        "screen_dark": mat("Coral_Terminal_Dark", (0.012, 0.018, 0.024), 0.32, 0.22),
        "screen_glow": mat("Coral_Terminal_Glow", (0.18, 0.36, 0.42), 0.27, emission=(0.12, 0.48, 0.62), strength=1.4),
        "print_blue": mat("Coral_Printed_Blue", (0.025, 0.16, 0.27), 0.83),
        "print_green": mat("Coral_Printed_Green", (0.15, 0.35, 0.11), 0.83),
        "print_white": mat("Coral_Printed_White", (0.68, 0.7, 0.66), 0.88),
        "print_tan": mat("Coral_Printed_Tan", (0.56, 0.44, 0.30), 0.88),
        "print_blue_light": mat("Coral_Printed_Light_Blue", (0.22, 0.40, 0.48), 0.88),
        "paper": mat("Coral_Paper", (0.72, 0.72, 0.66), 0.95),
        "ink": mat("Coral_Ink", (0.08, 0.12, 0.14), 0.9),
        "cream": mat("Coral_Cream_Plastic", (0.60, 0.58, 0.48), 0.75),
        "timber": mat("Coral_Weathered_Timber", (0.31, 0.19, 0.095), 0.92),
        "mesh_dark": mat("Coral_Railing_Mesh", (0.02, 0.025, 0.027), 0.74, 0.35, alpha=0.62),
        "bin_green": mat("Coral_Bin_Green", (0.025, 0.19, 0.15), 0.84),
        "bin_green_dark": mat("Coral_Bin_Green_Dark", (0.018, 0.10, 0.085), 0.86),
        "bin_dark": mat("Coral_Bin_Lid", (0.025, 0.045, 0.042), 0.80),
        "graffiti_pink": mat("Coral_Graffiti_Pink", (0.55, 0.20, 0.29), 0.78),
        "graffiti_cream": mat("Coral_Graffiti_Cream", (0.67, 0.51, 0.34), 0.78),
        "black": mat("Coral_Black", (0.005, 0.006, 0.007), 0.82),
        "lamp_glow": mat("Coral_Lamp_Glow", (1.0, 0.45, 0.05), 0.2, emission=(1.0, 0.18, 0.01), strength=8.0),
        "reflector": mat("Coral_Bollard_Reflector", (0.54, 0.52, 0.46), 0.32, 0.68),
        "wet_road": mat("Coral_Wet_Road", (0.018, 0.024, 0.03), 0.22, 0.12),
        "road_yellow": mat("Coral_Road_Yellow", (0.85, 0.46, 0.025), 0.64),
    }


def recursive_objects(col):
    result = list(col.objects)
    for child in col.children:
        result.extend(recursive_objects(child))
    return result


def select_objects(objects):
    bpy.ops.object.select_all(action="DESELECT")
    mesh_like = []
    for obj in objects:
        if obj.type in {"MESH", "CURVE", "FONT"}:
            obj.select_set(True)
            mesh_like.append(obj)
    if mesh_like:
        bpy.context.view_layer.objects.active = mesh_like[0]
    return mesh_like


def export_objects(path, objects):
    selected = select_objects(objects)
    bpy.ops.export_scene.gltf(
        filepath=str(path), export_format="GLB", use_selection=True,
        export_apply=True, export_yup=True, export_image_format="AUTO",
    )
    return selected


def export_assets(assets):
    MODEL_ROOT.mkdir(parents=True, exist_ok=True)
    # Individual modular kits.
    for slug, col_name in ASSET_COLLECTIONS.items():
        export_objects(MODEL_ROOT / f"harpurhey-coral-{slug}.glb", recursive_objects(assets[slug]))
    # Complete architecture excludes loose scene context but includes all building pieces.
    complete = recursive_objects(assets["shopfront"]) + recursive_objects(assets["upper-block"])
    export_objects(MODEL_ROOT / "harpurhey-coral-shop.glb", complete)
    # Full set includes placed props and ground context for rapid scene dressing.
    full = complete + recursive_objects(assets["scene"])
    export_objects(MODEL_ROOT / "harpurhey-coral-street-set.glb", full)


def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def render_preview(materials):
    scene = bpy.context.scene
    engine_ids = {item.identifier for item in scene.bl_rna.properties["render"].fixed_type.properties["engine"].enum_items} if False else set()
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 820
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.filepath = str(PREVIEW_PATH)
    scene.world.color = (0.002, 0.004, 0.012)
    # Cool shop wash.
    bpy.ops.object.light_add(type="AREA", location=(0, -9.5, 6.2))
    cool = bpy.context.object
    cool.name = "Preview_Cool_Shop_Wash"
    cool.data.energy = 1100
    cool.data.color = (0.42, 0.68, 1.0)
    cool.data.shape = "RECTANGLE"
    cool.data.size = 12
    point_at(cool, (0, FRONT_Y, 3.5))
    # Sodium streetlamp pool.
    bpy.ops.object.light_add(type="AREA", location=(-8.9, -6.2, 5.35))
    warm = bpy.context.object
    warm.name = "Preview_Sodium_Light"
    warm.data.energy = 1250
    warm.data.color = (1.0, 0.24, 0.015)
    warm.data.shape = "DISK"
    warm.data.size = 4.2
    point_at(warm, (-6.0, -8.0, 0))
    bpy.ops.object.light_add(type="AREA", location=(8.0, -6.0, 5.0))
    warm2 = bpy.context.object
    warm2.data.energy = 450
    warm2.data.color = (1.0, 0.34, 0.05)
    warm2.data.size = 3
    point_at(warm2, (7, FRONT_Y, 1.5))
    # Pull back far enough to review the complete architecture and all placed
    # street furniture in one image (the reference itself uses a wide street view).
    bpy.ops.object.camera_add(location=(0.0, -40.5, 6.35))
    camera = bpy.context.object
    camera.name = "Coral_Preview_Camera"
    camera.data.lens = 52
    point_at(camera, (0, FRONT_Y, 6.15))
    scene.camera = camera
    RENDER_ROOT.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)


def triangle_count(objects):
    total = 0
    for obj in objects:
        if obj.type == "MESH":
            total += sum(max(0, len(poly.vertices) - 2) for poly in obj.data.polygons)
    return total


def main():
    clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    mats = materials()
    assets = {
        "shopfront": build_shopfront(mats),
        "upper-block": build_upper_block(mats),
        "window-module": build_window_module(mats),
        "bin": build_bin(mats),
        "streetlight": build_streetlight(mats),
        "bollard": build_bollard(mats),
    }
    assets["scene"] = build_scene_context(mats, assets)
    SOURCE_ROOT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), check_existing=False)
    export_assets(assets)
    render_preview(mats)
    all_objects = [obj for col in assets.values() for obj in recursive_objects(col)]
    print(f"Coral kit objects: {len(all_objects)}")
    print(f"Coral kit triangles: {triangle_count(all_objects)}")
    print(f"Saved: {BLEND_PATH}")
    print(f"Preview: {PREVIEW_PATH}")


if __name__ == "__main__":
    main()
