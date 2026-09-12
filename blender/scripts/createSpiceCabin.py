"""Build the reference-led Spice Cabin shopfront as a reusable Three.js GLB.

The supplied photographs and 16_Spice_Cabin.txt are the visual authority.  One
Blender unit is one metre, Z is up, ground is Z=0, and the frontage faces -Y.
The script generates its small PBR texture set reproducibly, builds the editable
master, exports the asset without review furniture, and renders the six views
required by the brief.
"""

from math import cos, pi, radians, sin
from pathlib import Path
import random
import subprocess
import tempfile

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "references" / "architecture" / "spice-cabin" / "spice-cabin-manchester.jpg"
TEXTURES = ROOT / "blender" / "source" / "textures" / "spice-cabin"
BLEND = ROOT / "blender" / "source" / "spice-cabin.blend"
GLB = ROOT / "public" / "assets" / "models" / "spice-cabin.glb"
RENDERS = ROOT / "renders" / "spice-cabin"

W = 6.80
D = 1.10
H = 4.25
FRONT_Y = -D / 2
SIGN_BOTTOM = 2.74
SIGN_TOP = 3.64
BLUE_BOTTOM = 2.46
OPENING_BOTTOM = 1.08

ASSET_COLLECTIONS = (
    "SPICE_structure", "SPICE_brick_wall", "SPICE_cream_pier", "SPICE_sign",
    "SPICE_blue_fascia", "SPICE_window_frames", "SPICE_glass", "SPICE_door",
    "SPICE_log_cladding", "SPICE_bollards", "SPICE_security_wire",
    "SPICE_pipework", "SPICE_alarm_fixtures", "SPICE_interior_cards",
    "SPICE_anchors",
)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                       bpy.data.images, bpy.data.cameras, bpy.data.lights):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def ppm(path, width, height, pixel_fn):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="ascii") as handle:
        handle.write(f"P3\n{width} {height}\n255\n")
        for y in range(height):
            row = []
            for x in range(width):
                row.extend(str(max(0, min(255, int(v)))) for v in pixel_fn(x, y))
            handle.write(" ".join(row) + "\n")


def sips(*arguments):
    subprocess.run(["/usr/bin/sips", *map(str, arguments)], check=True,
                   capture_output=True, text=True)


def convert_ppm(source, target):
    sips("-s", "format", "png", source, "-o", target)
    source.unlink()


def generate_textures():
    """Small authored texture set: variation is deterministic and non-uniform."""
    TEXTURES.mkdir(parents=True, exist_ok=True)
    rng = random.Random(16061995)
    brick_variation = [[rng.uniform(-22, 20) for _ in range(16)] for _ in range(16)]

    def brick_pixel(x, y):
        bw, bh, mortar = 64, 27, 4
        row = y // bh
        shifted = x + (bw // 2 if row % 2 else 0)
        bx, by = shifted % bw, y % bh
        if bx < mortar or by < mortar:
            grit = ((x * 13 + y * 7) % 11) - 5
            return 111 + grit, 105 + grit, 91 + grit
        variation = brick_variation[row % 16][(shifted // bw) % 16]
        pore = -16 if ((x * 31 + y * 17) % 137) < 5 else 0
        grain = 7 * sin(x * .37) + 4 * sin(y * .81)
        stain = -10 * max(0.0, sin((x + y * .45) * .018))
        return 151 + variation + grain + pore + stain, 124 + variation * .72 + grain + pore, 87 + variation * .48 + pore

    def brick_rough(x, y):
        value = 214 + int(20 * sin(x * .19) * sin(y * .31))
        return value, value, value

    def wood_pixel(x, y):
        wave = 13 * sin(x * .055 + sin(y * .08)) + 7 * sin(x * .013 + y * .14)
        grain = 9 * sin(x * .31 + y * .035)
        knots = -28 if ((x - 177) ** 2 + (y - 89) ** 2) < 180 else 0
        dirt = -14 * (y / 255.0) + (-8 if (x + y * 3) % 193 < 4 else 0)
        return 154 + wave + grain + knots + dirt, 102 + wave * .55 + grain * .3 + knots + dirt, 55 + wave * .25 + knots * .5 + dirt

    def wood_rough(x, y):
        value = 196 + int(27 * abs(sin(x * .097 + y * .03)))
        return value, value, value

    for name, size, fn in (
        ("brick-aged-tan-albedo.png", (512, 512), brick_pixel),
        ("brick-aged-tan-roughness.png", (512, 512), brick_rough),
        ("log-cladding-weathered-albedo.png", (1024, 256), wood_pixel),
        ("log-cladding-weathered-roughness.png", (1024, 256), wood_rough),
    ):
        target = TEXTURES / name
        source = target.with_suffix(".ppm")
        ppm(source, *size, fn)
        convert_ppm(source, target)

    # The clearest near-frontal historical photograph supplies the real identity
    # rather than a guessed logo. Crop includes only the sign face and is resized
    # to the 4:1 sign ratio; source references are never modified.
    sign = TEXTURES / "spice-cabin-sign-albedo.png"
    with tempfile.TemporaryDirectory(prefix="spice-cabin-sign-") as temp:
        crop = Path(temp) / "sign-crop.png"
        sips("-c", 250, 450, "--cropOffset", 245, 380, REFERENCE, "-o", crop)
        sips("-z", 512, 2048, crop, "-s", "format", "png", "-o", sign)


def collection(name):
    result = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(result)
    return result


def move_to(obj, target):
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    target.objects.link(obj)
    return obj


def material(name, color, roughness=.8, metallic=0.0, emission=None, strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1)
        bsdf.inputs["Emission Strength"].default_value = strength
    return mat


def textured_material(name, albedo, roughness_image=None, roughness=.85):
    mat = material(name, (.5, .5, .5), roughness)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    image = bpy.data.images.load(str(TEXTURES / albedo), check_existing=False)
    image.colorspace_settings.name = "sRGB"
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.interpolation = "Linear"
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if roughness_image:
        rough_image = bpy.data.images.load(str(TEXTURES / roughness_image), check_existing=False)
        rough_image.colorspace_settings.name = "Non-Color"
        rough_tex = nodes.new("ShaderNodeTexImage")
        rough_tex.image = rough_image
        links.new(rough_tex.outputs["Color"], bsdf.inputs["Roughness"])
    return mat


def glass_material():
    mat = material("MAT_glass_shopfront", (.045, .065, .07), .22)
    mat.diffuse_color = (.045, .065, .07, .42)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Alpha"].default_value = .42
    bsdf.inputs["Transmission Weight"].default_value = .12
    mat.surface_render_method = "DITHERED"
    return mat


def box(name, dimensions, location, mat, target, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_mesh"
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        modifier = obj.modifiers.new("edge-softness", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.data.materials.append(mat)
    return move_to(obj, target)


def cylinder(name, radius, depth, location, mat, target, vertices=16, rotate_y=False):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location,
                                       rotation=(0, radians(90), 0) if rotate_y else (0, 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_mesh"
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    obj.data.materials.append(mat)
    return move_to(obj, target)


def curve(name, points, radius, mat, target):
    data = bpy.data.curves.new(f"{name}_curve", "CURVE")
    data.dimensions = "3D"
    data.bevel_depth = radius
    data.bevel_resolution = 0
    data.resolution_u = 1
    spline = data.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, coordinate in zip(spline.points, points):
        point.co = (*coordinate, 1)
    obj = bpy.data.objects.new(name, data)
    target.objects.link(obj)
    return obj


def facade_plane(name, width, height, location, mat, target, u_repeat=1.0, v_repeat=1.0):
    """A dedicated -Y-facing decal plane with predictable full-face UVs."""
    x, y, z = location
    vertices = [
        (x - width / 2, y, z - height / 2),
        (x + width / 2, y, z - height / 2),
        (x + width / 2, y, z + height / 2),
        (x - width / 2, y, z + height / 2),
    ]
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], [(0, 1, 2, 3)])
    mesh.materials.append(mat)
    uv_layer = mesh.uv_layers.new(name="UVMap")
    uvs = ((0, 0), (u_repeat, 0), (u_repeat, v_repeat), (0, v_repeat))
    for loop, uv in zip(mesh.polygons[0].loop_indices, uvs):
        uv_layer.data[loop].uv = uv
    obj = bpy.data.objects.new(name, mesh)
    target.objects.link(obj)
    return obj


def empty(name, location, target):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = .18
    obj.location = location
    target.objects.link(obj)
    return obj


def build_materials():
    return {
        "brick": textured_material("MAT_brick_aged_tan", "brick-aged-tan-albedo.png", "brick-aged-tan-roughness.png"),
        "log": textured_material("MAT_log_cladding_weathered", "log-cladding-weathered-albedo.png", "log-cladding-weathered-roughness.png"),
        "sign": textured_material("MAT_sign_printed_wood", "spice-cabin-sign-albedo.png", roughness=.69),
        "blue": material("MAT_blue_painted_frame", (.018, .105, .28), .66),
        "cream": material("MAT_cream_painted_concrete", (.67, .64, .55), .92),
        "dark": material("MAT_dark_pipe", (.018, .021, .022), .78, .15),
        "security": material("MAT_security_metal", (.035, .038, .04), .69, .58),
        "glass": glass_material(),
        "interior": material("MAT_interior_dark", (.012, .009, .008), .94),
        "wood": material("MAT_door_wood", (.24, .13, .055), .78),
        "pavement": material("MAT_pavement_worn", (.105, .11, .108), .97),
        "red_emissive": material("MAT_emissive_signage", (.34, .008, .006), .38, emission=(1.0, .018, .008), strength=4.0),
        "warm": material("MAT_interior_warm", (.34, .18, .075), .55, emission=(1.0, .48, .18), strength=1.2),
    }


def build_shop(groups, mats):
    # A shallow modular building edge, not an invented street.
    box("SPICE_Structure_Back", (W, .18, H), (0, D / 2 - .09, H / 2), mats["interior"], groups["structure"])
    brick_w = W - .78
    brick_h = H - SIGN_TOP
    box("SPICE_Brick_Upper", (brick_w, .34, brick_h), (.18, FRONT_Y + .10, (H + SIGN_TOP) / 2), mats["brick"], groups["brick_wall"])
    facade_plane("SPICE_Brick_Upper_Face", brick_w, brick_h, (.18, FRONT_Y - .075, (H + SIGN_TOP) / 2),
                 mats["brick"], groups["brick_wall"], u_repeat=5.0, v_repeat=1.0)
    box("SPICE_Brick_LeftReturn", (.48, D, H), (-W / 2 + .24, 0, H / 2), mats["brick"], groups["brick_wall"])
    box("SPICE_CreamPier_Left", (.54, .56, 3.88), (-W / 2 + .38, FRONT_Y - .02, 1.94), mats["cream"], groups["cream_pier"], .025)
    box("SPICE_CreamPier_Top", (W - .25, .46, .18), (.12, FRONT_Y - .015, 3.73), mats["cream"], groups["cream_pier"], .025)

    # Sign and blue shopfront anatomy.
    box("SPICE_Sign_Casing", (5.90, .22, 1.02), (.24, FRONT_Y - .20, 3.18), mats["dark"], groups["sign"], .025)
    facade_plane("SPICE_Sign_Face", 5.76, .90, (.24, FRONT_Y - .322, 3.19), mats["sign"], groups["sign"])
    box("SPICE_Blue_Fascia", (5.94, .32, BLUE_BOTTOM - 2.14), (.24, FRONT_Y - .11, (BLUE_BOTTOM + 2.14) / 2), mats["blue"], groups["blue_fascia"], .018)
    box("SPICE_Blue_LeftJamb", (.14, .22, 2.32), (-2.69, FRONT_Y - .12, 1.28), mats["blue"], groups["window_frames"], .012)
    box("SPICE_Blue_RightJamb", (.14, .22, 2.32), (3.18, FRONT_Y - .12, 1.28), mats["blue"], groups["window_frames"], .012)

    # Recessed broad display, narrow entrance, and right-hand pane.
    panes = (("Left", -1.42, 2.28), ("Right", 2.25, 1.66))
    for label, x, width in panes:
        box(f"SPICE_Glass_{label}", (width, .035, 1.29), (x, FRONT_Y - .025, 1.75), mats["glass"], groups["glass"])
        for side in (-1, 1):
            box(f"SPICE_Frame_{label}_{side:+d}", (.065, .12, 1.38), (x + side * width / 2, FRONT_Y - .075, 1.72), mats["blue"], groups["window_frames"])
        box(f"SPICE_Frame_{label}_Top", (width + .08, .12, .07), (x, FRONT_Y - .075, 2.42), mats["blue"], groups["window_frames"])

    door_x = .56
    box("SPICE_Door_Recess", (.93, .16, 2.24), (door_x, FRONT_Y + .035, 1.12), mats["interior"], groups["door"])
    box("SPICE_Door_Frame_Left", (.09, .24, 2.30), (door_x - .50, FRONT_Y - .09, 1.15), mats["blue"], groups["door"])
    box("SPICE_Door_Frame_Right", (.09, .24, 2.30), (door_x + .50, FRONT_Y - .09, 1.15), mats["blue"], groups["door"])
    box("SPICE_Door_Frame_Top", (1.08, .24, .09), (door_x, FRONT_Y - .09, 2.29), mats["blue"], groups["door"])
    box("SPICE_Door", (.80, .07, 2.09), (door_x, FRONT_Y + .025, 1.09), mats["wood"], groups["door"], .012)
    box("SPICE_Door_Glass", (.63, .025, 1.04), (door_x, FRONT_Y - .018, 1.55), mats["glass"], groups["door"])
    cylinder("SPICE_Door_Handle", .025, .24, (door_x + .27, FRONT_Y - .075, 1.10), mats["security"], groups["door"], 12)

    # Genuine rounded horizontal log relief, split cleanly around the entrance.
    log_h = .155
    box("SPICE_Log_Backing_Left", (2.32, .06, 1.04), (-1.42, FRONT_Y - .045, .57), mats["log"], groups["log_cladding"])
    box("SPICE_Log_Backing_Right", (1.70, .06, 1.04), (2.25, FRONT_Y - .045, .57), mats["log"], groups["log_cladding"])
    for course in range(7):
        z = .11 + course * log_h
        for label, x, length in (("Left", -1.42, 2.30), ("Right", 2.25, 1.68)):
            cylinder(f"SPICE_Log_{label}_{course + 1:02d}", log_h * .55, length,
                     (x, FRONT_Y - .105, z), mats["log"], groups["log_cladding"], 12, rotate_y=True)
    box("SPICE_Log_Sill_Left", (2.38, .15, .07), (-1.42, FRONT_Y - .10, 1.10), mats["wood"], groups["log_cladding"], .012)
    box("SPICE_Log_Sill_Right", (1.76, .15, .07), (2.25, FRONT_Y - .10, 1.10), mats["wood"], groups["log_cladding"], .012)

    # Economical interior: depth and warm silhouettes behind dark glass.
    box("SPICE_Interior_Back", (5.55, .08, 2.12), (.22, .30, 1.12), mats["interior"], groups["interior_cards"])
    box("SPICE_Interior_Counter", (3.55, .42, .82), (-.65, -.05, .48), mats["wood"], groups["interior_cards"], .02)
    box("SPICE_Interior_WarmCard", (3.9, .025, 1.24), (-.50, .245, 1.60), mats["warm"], groups["interior_cards"])
    box("SPICE_FriedChicken_Sign", (.70, .035, .27), (1.88, FRONT_Y - .06, 1.75), mats["red_emissive"], groups["interior_cards"], .018)
    for i in range(3):
        box(f"SPICE_FriedChicken_LetterBar_{i + 1}", (.48 - i * .08, .012, .025),
            (1.88, FRONT_Y - .086, 1.82 - i * .07), mats["warm"], groups["interior_cards"])

    # Upper services and the long pale conduit are prominent in the photographs.
    pipe_y = FRONT_Y - .27
    curve("SPICE_HighConduit", [(-2.55, pipe_y, 3.84), (2.82, pipe_y, 3.84)], .035, mats["cream"], groups["pipework"])
    for x in (-2.35, -1.20, 0.0, 1.28, 2.58):
        box(f"SPICE_ConduitBracket_{x:+.2f}", (.05, .12, .22), (x, FRONT_Y - .18, 3.80), mats["security"], groups["pipework"])
    curve("SPICE_Downpipe_Right", [(3.03, FRONT_Y - .06, 3.68), (3.03, FRONT_Y - .06, .12)], .065, mats["dark"], groups["pipework"])
    box("SPICE_AlarmBox_Left", (.23, .10, .29), (-2.58, FRONT_Y - .24, 2.68), mats["cream"], groups["alarm_fixtures"], .025)
    box("SPICE_AlarmBox_Right", (.22, .11, .27), (2.82, FRONT_Y - .24, 2.67), mats["dark"], groups["alarm_fixtures"], .025)

    # Bollards are part of the observed shop threshold, not generic decoration.
    for index, x in enumerate((-2.22, -.62, 1.30, 2.78), 1):
        cylinder(f"SPICE_Bollard_{index:02d}", .105, .93, (x, FRONT_Y - .76, .465), mats["dark"], groups["bollards"], 14)
        cylinder(f"SPICE_BollardCap_{index:02d}", .112, .045, (x, FRONT_Y - .76, .945), mats["dark"], groups["bollards"], 14)

    # Simplified anti-climb silhouette: rails, stanchions and sparse paired spikes.
    top_z = H + .18
    for x in (-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0):
        curve(f"SPICE_SecurityStanchion_{x:+.1f}", [(x, -.27, H), (x, -.33, top_z + .12)], .018, mats["security"], groups["security_wire"])
    curve("SPICE_SecurityRail_Lower", [(-3.1, -.31, top_z), (3.1, -.31, top_z)], .018, mats["security"], groups["security_wire"])
    curve("SPICE_SecurityRail_Upper", [(-3.1, -.32, top_z + .11), (3.1, -.32, top_z + .11)], .014, mats["security"], groups["security_wire"])
    for index in range(19):
        x = -3.0 + index / 3.0
        for dy in (-.02, .02):
            curve(f"SPICE_AntiClimbSpike_{index:02d}_{dy:+.2f}",
                  [(x, -.32 + dy, top_z + .04), (x + .09, -.32 + dy, top_z + .25)],
                  .011, mats["security"], groups["security_wire"])

    # Runtime hooks: the game can illuminate and interact without guessing.
    empty("SPICE_EntranceAnchor", (door_x, FRONT_Y - 1.05, 0), groups["anchors"])
    empty("SPICE_DeliveryAnchor", (1.68, FRONT_Y - 1.05, 0), groups["anchors"])
    empty("SPICE_LightAnchor_Window", (-1.12, FRONT_Y - .28, 2.05), groups["anchors"])
    empty("SPICE_LightAnchor_Door", (door_x, FRONT_Y - .20, 2.02), groups["anchors"])
    empty("SPICE_LightAnchor_Sign", (.24, FRONT_Y - .42, 3.20), groups["anchors"])


def add_review_scene(mats):
    review = collection("SPICE_review_only")
    box("SPICE_Review_Pavement", (11.5, 6.0, .10), (0, -2.55, -.05), mats["pavement"], review)
    # Ordinary railing at the end-unit edge and a 1.78 m scale witness.
    for x in (-3.15, -2.55, -1.95):
        cylinder(f"SPICE_Review_RailingPost_{x}", .025, .98, (x, -1.45, .49), mats["security"], review, 10)
    curve("SPICE_Review_RailingTop", [(-3.15, -1.45, .92), (-1.95, -1.45, .92)], .026, mats["security"], review)
    cylinder("SPICE_Review_ScaleFigure", .16, 1.40, (3.75, -1.85, .70), mats["dark"], review, 16)
    cylinder("SPICE_Review_ScaleHead", .19, .32, (3.75, -1.85, 1.59), mats["dark"], review, 16)
    return review


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def camera(name, location, target, lens=48):
    data = bpy.data.cameras.new(f"{name}_data")
    data.lens = lens
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    look_at(obj, target)
    return obj


def configure_scene():
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.world.color = (.025, .03, .04)
    scene.view_settings.look = "AgX - Medium High Contrast"
    return scene


def add_lighting():
    sun_data = bpy.data.lights.new("SPICE_Review_Sun_data", "SUN")
    sun_data.energy = 2.0
    sun_data.angle = radians(8)
    sun = bpy.data.objects.new("SPICE_Review_Sun", sun_data)
    bpy.context.scene.collection.objects.link(sun)
    sun.rotation_euler = (radians(38), radians(-18), radians(-28))
    area_data = bpy.data.lights.new("SPICE_Review_Softbox_data", "AREA")
    area_data.energy = 760
    area_data.shape = "RECTANGLE"
    area_data.size = 8
    area_data.size_y = 5
    area = bpy.data.objects.new("SPICE_Review_Softbox", area_data)
    bpy.context.scene.collection.objects.link(area)
    area.location = (-2.5, -5.5, 7.8)
    look_at(area, (0, 0, 2.0))
    warm_data = bpy.data.lights.new("SPICE_Review_InteriorLight_data", "AREA")
    warm_data.energy = 310
    warm_data.color = (1.0, .42, .16)
    warm_data.size = 4.3
    warm = bpy.data.objects.new("SPICE_Review_InteriorLight", warm_data)
    bpy.context.scene.collection.objects.link(warm)
    warm.location = (-.45, -.18, 2.05)
    warm.rotation_euler = (radians(90), 0, 0)
    warm.hide_render = True
    sign_data = bpy.data.lights.new("SPICE_Review_SignLight_data", "AREA")
    sign_data.energy = 240
    sign_data.color = (1.0, .63, .34)
    sign_data.shape = "RECTANGLE"
    sign_data.size = 5.4
    sign_data.size_y = .28
    sign_light = bpy.data.objects.new("SPICE_Review_SignLight", sign_data)
    bpy.context.scene.collection.objects.link(sign_light)
    sign_light.location = (.24, -1.02, 3.83)
    look_at(sign_light, (.24, FRONT_Y - .31, 3.18))
    sign_light.hide_render = True
    return sun, area, warm, sign_light


def apply_and_validate(groups):
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj.name.startswith("SPICE_"):
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            obj.select_set(False)
    required = ("SPICE_Sign_Face", "SPICE_CreamPier_Left", "SPICE_Door", "SPICE_Log_Left_01",
                "SPICE_Brick_Upper", "SPICE_HighConduit", "SPICE_SecurityRail_Upper",
                "SPICE_EntranceAnchor", "SPICE_LightAnchor_Sign")
    missing = [name for name in required if bpy.data.objects.get(name) is None]
    if missing:
        raise RuntimeError(f"Missing required Spice Cabin objects: {missing}")
    stray = [o.name for o in bpy.data.objects if o.name.startswith(("Cube", "Cylinder"))]
    if stray:
        raise RuntimeError(f"Unnamed primitives remain: {stray}")
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("SPICE_Review_")]
    triangles = sum(sum(max(0, len(p.vertices) - 2) for p in o.data.polygons) for o in meshes)
    print(f"Validation: {len(meshes)} runtime meshes, approximately {triangles} triangles")
    print(f"Validation: nominal facade {W:.2f}m wide x {H:.2f}m high; frontage faces -Y")


def export_glb(groups):
    GLB.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    objects = []
    for key, group in groups.items():
        for obj in group.objects:
            if obj.type not in {"LIGHT", "CAMERA"}:
                obj.select_set(True)
                objects.append(obj)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(filepath=str(GLB), export_format="GLB", use_selection=True,
                              export_apply=True, export_yup=True, export_cameras=False,
                              export_lights=False)
    bpy.ops.object.select_all(action="DESELECT")
    print(f"Exported {GLB}")


def render_reviews(scene, lights):
    RENDERS.mkdir(parents=True, exist_ok=True)
    cameras = (
        camera("SPICE_Camera_A_Overcast", (0, -10.7, 3.05), (0, 0, 2.05), 58),
        camera("SPICE_Camera_B_Grazing", (-7.4, -8.0, 3.35), (-.25, 0, 2.15), 52),
        camera("SPICE_Camera_C_Night", (6.9, -8.3, 3.15), (.10, 0, 2.10), 52),
        camera("SPICE_Camera_D_Brick", (-1.05, -3.0, 4.02), (-.85, -.15, 4.0), 68),
        camera("SPICE_Camera_E_Timber", (-1.55, -3.15, .69), (-1.42, -.18, .64), 66),
        camera("SPICE_Camera_F_Front", (0, -9.4, 2.30), (0, 0, 2.25), 62),
    )
    filenames = (
        "01-neutral-overcast-daylight.png", "02-oblique-grazing-daylight.png",
        "03-night-practical-light.png", "04-brick-close-up.png",
        "05-rounded-timber-close-up.png", "06-straight-on-facade.png",
    )
    sun, area, warm, sign_light = lights
    for index, (cam, filename) in enumerate(zip(cameras, filenames)):
        is_night = index == 2
        sun.hide_render = is_night
        area.hide_render = is_night
        warm.hide_render = not is_night
        sign_light.hide_render = not is_night
        scene.world.color = (.002, .004, .009) if is_night else (.055, .065, .078)
        scene.camera = cam
        scene.render.resolution_x = 1280 if index < 3 or index == 5 else 1024
        scene.render.resolution_y = 900 if index < 3 or index == 5 else 1024
        scene.render.filepath = str(RENDERS / filename)
        bpy.ops.render.render(write_still=True)
        print(f"Rendered {scene.render.filepath}")


def main():
    clear_scene()
    generate_textures()
    scene = configure_scene()
    groups = {name.removeprefix("SPICE_"): collection(name) for name in ASSET_COLLECTIONS}
    mats = build_materials()
    build_shop(groups, mats)
    add_review_scene(mats)
    lights = add_lighting()
    apply_and_validate(groups)
    render_reviews(scene, lights)
    export_glb(groups)
    note = bpy.data.texts.new("SPICE_CABIN_NOTES")
    note.write("Reference-led Spice Cabin facade; frontage -Y; review-only pavement excluded from GLB.\n")
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    print(f"Saved {BLEND}")


if __name__ == "__main__":
    main()
