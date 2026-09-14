"""Build the geometry-first North Road, Preston bus shelter hero asset.

The shelter and trolley are authored as independent hierarchies.  The combined
runtime GLB places them as in the reference photograph; the individual GLBs
retain useful local origins and can be loaded or removed independently.
"""

from math import pi
from mathutils import Vector
from pathlib import Path

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = PROJECT_ROOT / "blender" / "source" / "bus-shelter"
MODEL_DIR = PROJECT_ROOT / "public" / "assets" / "models" / "bus-shelter"
RENDER_DIR = PROJECT_ROOT / "renders" / "bus-shelter"

BLOCKOUT_BLEND = SOURCE_DIR / "preston-busstop-blockout.blend"
DETAIL_BLEND = SOURCE_DIR / "preston-busstop.blend"
REFERENCE_BLEND = SOURCE_DIR / "preston-busstop-reference.blend"
SHELTER_GLB = MODEL_DIR / "preston-bus-shelter.glb"
TROLLEY_GLB = MODEL_DIR / "preston-shopping-trolley.glb"
REFERENCE_GLB = MODEL_DIR / "preston-busstop-reference.glb"


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
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def material(name, color, roughness=0.72, metallic=0.0, alpha=1.0, emission=None):
    mat = bpy.data.materials.new(name=name)
    mat.diffuse_color = (*color, alpha)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1.0)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Alpha"].default_value = alpha
    if alpha < 1.0:
        mat.surface_render_method = "BLENDED"
        mat.use_transparency_overlap = False
    if emission is not None:
        emission_color, strength = emission
        shader.inputs["Emission Color"].default_value = (*emission_color, 1.0)
        shader.inputs["Emission Strength"].default_value = strength
    return mat


def parent_to(obj, parent):
    obj.parent = parent
    return obj


def add_empty(name, parent=None, location=(0, 0, 0)):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    if parent:
        parent_to(obj, parent)
    return obj


def add_box(name, dimensions, location, mat, parent, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.name = f"{name}_Mesh"
    obj.data.materials.append(mat)
    if bevel:
        modifier = obj.modifiers.new(name="Small_Edge_Bevel", type="BEVEL")
        modifier.width = bevel
        modifier.segments = 2
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    return parent_to(obj, parent)


def add_plane_yz(name, x, y_range, z_range, mat, parent):
    y0, y1 = y_range
    z0, z1 = z_range
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata([(x, y0, z0), (x, y1, z0), (x, y1, z1), (x, y0, z1)], [], [(0, 1, 2, 3)])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(mat)
    return parent_to(obj, parent)


def add_plane_xz(name, y, x_range, z_range, mat, parent):
    x0, x1 = x_range
    z0, z1 = z_range
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata([(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)], [], [(0, 1, 2, 3)])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(mat)
    return parent_to(obj, parent)


def add_cylinder_between(name, start, end, radius, mat, parent, vertices=8):
    start = Vector(start)
    end = Vector(end)
    direction = end - start
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=direction.length,
        location=(start + end) * 0.5,
    )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    obj.data.name = f"{name}_Mesh"
    obj.data.materials.append(mat)
    return parent_to(obj, parent)


def add_wheel(name, location, mat, parent, steering=0.0):
    wheel_root = add_empty(name, parent, location)
    wheel_root.rotation_euler[2] = steering
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=12,
        radius=0.09,
        depth=0.052,
        location=(0, 0, 0),
        rotation=(0, pi / 2, 0),
    )
    wheel = bpy.context.object
    wheel.name = f"{name}_Tyre"
    wheel.data.materials.append(mat[0])
    parent_to(wheel, wheel_root)
    add_box(f"{name}_Fork", (0.075, 0.045, 0.15), (0, 0, 0.095), mat[1], wheel_root, bevel=0.012)
    return wheel_root


def create_materials():
    return {
        "dark": material("MAT_BusStop_DarkMetal_PLACEHOLDER", (0.19, 0.22, 0.21), 0.64, 0.55),
        "roof": material("MAT_BusStop_Roof_PLACEHOLDER", (0.24, 0.26, 0.25), 0.68, 0.42),
        "glass": material("MAT_BusStop_Glass_PLACEHOLDER", (0.54, 0.68, 0.69), 0.12, 0.05, 0.24),
        "rail": material("MAT_BusStop_RedRail_PLACEHOLDER", (0.74, 0.12, 0.055), 0.58, 0.18),
        "sign": material("MAT_BusStop_Signage_PLACEHOLDER", (0.79, 0.79, 0.75), 0.82),
        "advert": material("MAT_BusStop_Advert_PLACEHOLDER", (0.84, 0.81, 0.79), 0.62),
        "light": material("MAT_BusStop_Light_PLACEHOLDER", (0.9, 0.89, 0.81), 0.4),
        "trolley": material("MAT_Trolley_Metal_PLACEHOLDER", (0.43, 0.47, 0.46), 0.38, 0.78),
        "plastic": material("MAT_Trolley_Plastic_PLACEHOLDER", (0.16, 0.18, 0.17), 0.72),
        "wheel": material("MAT_Trolley_Wheel_PLACEHOLDER", (0.045, 0.05, 0.048), 0.92),
    }


def build_shelter(mats):
    root = add_empty("PRESTON_BUS_SHELTER")
    frame = add_empty("BUSSTOP_Frame", root)
    roof = add_empty("BUSSTOP_Roof", root)
    glass_rear = add_empty("BUSSTOP_GlassRear", root)
    glass_left = add_empty("BUSSTOP_GlassLeft", root)
    glass_right = add_empty("BUSSTOP_GlassRight", root)
    bench = add_empty("BUSSTOP_Bench", root)
    advert = add_empty("BUSSTOP_AdvertHousing", root)
    signage = add_empty("BUSSTOP_Signage", root)
    lighting = add_empty("BUSSTOP_Lighting", root)

    # 5.10 m wide, 2.52 m tall, 1.55 m deep. Open front faces +X.
    add_box("BUSSTOP_Roof_Shell", (1.72, 5.18, 0.24), (0, 0, 2.40), mats["roof"], roof, bevel=0.105)
    add_box("BUSSTOP_Roof_Underside", (1.45, 4.92, 0.055), (-0.02, 0, 2.275), mats["dark"], roof, bevel=0.018)
    add_box("BUSSTOP_Number_DecalSurface", (0.018, 0.56, 0.16), (0.866, -2.05, 2.40), mats["sign"], signage, bevel=0.008)

    rear_x = -0.70
    post_ys = (-2.37, -0.79, 0.79, 2.37)
    # Uprights run 30 mm below ground so they read as set into the pavement.
    for index, y in enumerate(post_ys, 1):
        add_box(f"BUSSTOP_Frame_RearUpright_{index:02d}", (0.085, 0.085, 2.33), (rear_x, y, 1.135), mats["dark"], frame, bevel=0.008)
    for z, height in ((2.25, 0.085), (1.03, 0.075), (0.28, 0.12)):
        add_box(f"BUSSTOP_Frame_RearRail_{int(z * 100):03d}", (0.085, 4.82, height), (rear_x, 0, z), mats["dark"], frame, bevel=0.006)

    rear_bays = ((-2.32, -0.84), (-0.74, 0.74), (0.84, 2.32))
    for index, y_range in enumerate(rear_bays, 1):
        add_plane_yz(f"BUSSTOP_Glass_Rear{index:02d}", rear_x + 0.006, y_range, (0.34, 2.20), mats["glass"], glass_rear)

    # Narrow left return, with its own front upright and rails.
    add_box("BUSSTOP_Frame_LeftFrontUpright", (0.085, 0.085, 2.33), (0.70, -2.37, 1.135), mats["dark"], frame, bevel=0.008)
    add_box("BUSSTOP_Frame_LeftBottomRail", (1.42, 0.085, 0.11), (0, -2.37, 0.28), mats["dark"], frame)
    add_box("BUSSTOP_Frame_LeftTopRail", (1.42, 0.085, 0.08), (0, -2.37, 2.24), mats["dark"], frame)
    add_plane_xz("BUSSTOP_Glass_Left", -2.37, (-0.65, 0.65), (0.34, 2.20), mats["glass"], glass_left)

    # Right return glazing remains distinct behind the projecting lightbox.
    add_box("BUSSTOP_Frame_RightFrontUpright", (0.085, 0.085, 2.33), (0.70, 2.37, 1.135), mats["dark"], frame, bevel=0.008)
    add_plane_xz("BUSSTOP_Glass_Right", 2.37, (-0.65, 0.65), (0.34, 2.20), mats["glass"], glass_right)

    # The photograph has a resting rail, not a conventional seat.
    add_cylinder_between("BUSSTOP_BenchRail_Horizontal", (0.34, -1.62, 0.76), (0.34, 0.70, 0.76), 0.041, mats["rail"], bench, 10)
    # The legs are set into the pavement, as in the photograph.
    add_cylinder_between("BUSSTOP_BenchRail_LeftLeg", (0.34, -1.62, -0.03), (0.34, -1.62, 0.76), 0.041, mats["rail"], bench, 10)
    add_cylinder_between("BUSSTOP_BenchRail_RightLeg", (0.34, 0.70, -0.03), (0.34, 0.70, 0.76), 0.041, mats["rail"], bench, 10)
    add_box("BUSSTOP_Bench_Perch", (0.22, 2.12, 0.075), (-0.46, -0.42, 0.68), mats["dark"], bench, bevel=0.018)

    # Separate physical signage backplates and future decal surfaces.
    add_box("BUSSTOP_Timetable_Backplate", (0.075, 0.70, 1.23), (-0.61, -1.47, 1.47), mats["dark"], signage, bevel=0.022)
    add_plane_yz("BUSSTOP_Timetable_DecalSurface", -0.567, (-1.78, -1.16), (0.90, 2.04), mats["sign"], signage)
    add_box("BUSSTOP_NoSmoking_Backplate", (0.055, 0.29, 0.36), (-0.60, -2.05, 1.97), mats["dark"], signage, bevel=0.012)
    add_plane_yz("BUSSTOP_NoSmoking_DecalSurface", -0.568, (-2.16, -1.94), (1.84, 2.10), mats["sign"], signage)

    add_box("BUSSTOP_AdvertHousing_Outer", (1.55, 0.28, 2.12), (0.02, 2.47, 1.28), mats["dark"], advert, bevel=0.065)
    # The photographed unit stands on a narrower steel plinth set into the pavement.
    add_box("BUSSTOP_AdvertHousing_Plinth", (1.22, 0.18, 0.28), (0.01, 2.47, 0.11), mats["dark"], advert, bevel=0.012)
    add_box("BUSSTOP_AdvertGlass", (1.37, 0.035, 1.88), (0.06, 2.315, 1.30), mats["glass"], advert, bevel=0.025)
    add_plane_xz("BUSSTOP_Advert_DecalSurface", 2.293, (-0.57, 0.66), (0.44, 2.16), mats["advert"], advert)
    add_empty("BUSSTOP_AdvertLightAnchor", advert, (0.04, 2.24, 1.30))

    for label, y in (("Left", -1.58), ("Centre", 0), ("Right", 1.58)):
        add_box(f"BUSSTOP_RoofLightFixture_{label}", (0.40, 0.52, 0.035), (0.02, y, 2.235), mats["light"], lighting, bevel=0.018)
        add_empty(f"BUSSTOP_RoofLight_{label}", lighting, (0.02, y, 2.18))
    return root


def build_trolley(mats, detailed=True):
    root = add_empty("PRESTON_SHOPPING_TROLLEY")
    basket = add_empty("TROLLEY_Basket", root)
    frame = add_empty("TROLLEY_Frame", root)
    handle = add_empty("TROLLEY_Handle", root)

    top = (-0.38, 0.38, -0.63, 0.68, 1.19)
    lower = (-0.28, 0.28, -0.48, 0.54, 0.72)
    tx0, tx1, ty0, ty1, tz = top
    bx0, bx1, by0, by1, bz = lower
    edges = [
        ((tx0, ty0, tz), (tx1, ty0, tz)), ((tx0, ty1, tz), (tx1, ty1, tz)),
        ((tx0, ty0, tz), (tx0, ty1, tz)), ((tx1, ty0, tz), (tx1, ty1, tz)),
        ((bx0, by0, bz), (bx1, by0, bz)), ((bx0, by1, bz), (bx1, by1, bz)),
        ((bx0, by0, bz), (bx0, by1, bz)), ((bx1, by0, bz), (bx1, by1, bz)),
    ]
    for index, edge in enumerate(edges):
        add_cylinder_between(f"TROLLEY_Basket_Rim_{index:02d}", *edge, 0.018, mats["trolley"], basket, 6)
    for sx, sy in ((tx0, ty0), (tx0, ty1), (tx1, ty0), (tx1, ty1)):
        ex = bx0 if sx < 0 else bx1
        ey = by0 if sy < 0 else by1
        add_cylinder_between(f"TROLLEY_Basket_Corner_{sx:+.2f}_{sy:+.2f}", (sx, sy, tz), (ex, ey, bz), 0.014, mats["trolley"], basket, 6)

    if detailed:
        # Open basket: enough low-sided wire geometry to read from gameplay distance.
        for side_x in (tx0, tx1):
            for index in range(10):
                t = index / 9
                y_top = ty0 + (ty1 - ty0) * t
                y_bottom = by0 + (by1 - by0) * t
                add_cylinder_between(f"TROLLEY_Basket_SideWire_{'L' if side_x < 0 else 'R'}_{index:02d}", (side_x, y_top, tz - 0.02), ((bx0 if side_x < 0 else bx1), y_bottom, bz + 0.02), 0.007, mats["trolley"], basket, 5)
        for index in range(8):
            t = index / 7
            x_top = tx0 + (tx1 - tx0) * t
            x_bottom = bx0 + (bx1 - bx0) * t
            add_cylinder_between(f"TROLLEY_Basket_FrontWire_{index:02d}", (x_top, ty1, tz - 0.02), (x_bottom, by1, bz + 0.02), 0.007, mats["trolley"], basket, 5)
        for level in (0.81, 0.93, 1.05):
            t = (level - bz) / (tz - bz)
            x = bx0 + (tx0 - bx0) * t
            add_cylinder_between(f"TROLLEY_Basket_Horizontal_L_{int(level*100)}", (x, by0, level), (x, by1, level), 0.006, mats["trolley"], basket, 5)
            add_cylinder_between(f"TROLLEY_Basket_Horizontal_R_{int(level*100)}", (-x, by0, level), (-x, by1, level), 0.006, mats["trolley"], basket, 5)

    add_cylinder_between("TROLLEY_Handle_Bar", (-0.43, -0.94, 1.18), (0.43, -0.94, 1.18), 0.032, mats["plastic"], handle, 10)
    add_cylinder_between("TROLLEY_Handle_Stem_L", (-0.34, -0.91, 1.16), (-0.26, -0.46, 0.69), 0.022, mats["trolley"], handle, 7)
    add_cylinder_between("TROLLEY_Handle_Stem_R", (0.34, -0.91, 1.16), (0.26, -0.46, 0.69), 0.022, mats["trolley"], handle, 7)
    for side in (-1, 1):
        x = 0.27 * side
        add_cylinder_between(f"TROLLEY_Frame_Lower_{'L' if side < 0 else 'R'}", (x, -0.48, 0.70), (x, 0.56, 0.23), 0.023, mats["trolley"], frame, 7)
        add_cylinder_between(f"TROLLEY_Frame_RearLeg_{'L' if side < 0 else 'R'}", (x, -0.48, 0.70), (x, -0.56, 0.22), 0.023, mats["trolley"], frame, 7)
    add_cylinder_between("TROLLEY_Frame_FrontAxle", (-0.30, 0.56, 0.23), (0.30, 0.56, 0.23), 0.021, mats["trolley"], frame, 7)
    add_cylinder_between("TROLLEY_Frame_RearAxle", (-0.30, -0.56, 0.22), (0.30, -0.56, 0.22), 0.021, mats["trolley"], frame, 7)

    wheel_pair = (mats["wheel"], mats["trolley"])
    add_wheel("TROLLEY_Wheel_FL", (-0.30, 0.58, 0.09), wheel_pair, root, 0.14)
    add_wheel("TROLLEY_Wheel_FR", (0.30, 0.58, 0.09), wheel_pair, root, -0.10)
    add_wheel("TROLLEY_Wheel_RL", (-0.30, -0.58, 0.09), wheel_pair, root, -0.18)
    add_wheel("TROLLEY_Wheel_RR", (0.30, -0.58, 0.09), wheel_pair, root, 0.08)

    if detailed:
        chain = add_empty("TROLLEY_Chain", root)
        for index in range(7):
            bpy.ops.mesh.primitive_torus_add(
                major_radius=0.025,
                minor_radius=0.006,
                major_segments=8,
                minor_segments=4,
                location=(-0.39, -0.91 + index * 0.034, 1.12 - index * 0.045),
                rotation=(pi / 2, 0, index * pi / 2),
            )
            link = bpy.context.object
            link.name = f"TROLLEY_Chain_Link_{index:02d}"
            link.data.materials.append(mats["trolley"])
            parent_to(link, chain)
    return root


def descendants(root):
    result = [root]
    for child in root.children:
        result.extend(descendants(child))
    return result


def select_roots(*roots):
    bpy.ops.object.select_all(action="DESELECT")
    for root in roots:
        for obj in descendants(root):
            obj.select_set(True)
    bpy.context.view_layer.objects.active = roots[0]


def export_glb(path, *roots):
    path.parent.mkdir(parents=True, exist_ok=True)
    select_roots(*roots)
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
    )


def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def render_view(name, camera_location, target, focal_length=52):
    bpy.ops.object.camera_add(location=camera_location)
    camera = bpy.context.object
    camera.name = f"Review_Camera_{name}"
    camera.data.lens = focal_length
    point_at(camera, target)
    bpy.context.scene.camera = camera
    scene = bpy.context.scene
    scene.render.filepath = str(RENDER_DIR / f"{name}.png")
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera, do_unlink=True)


def add_review_stage():
    ground = material("MAT_Review_Ground", (0.13, 0.14, 0.14), 0.92)
    bpy.ops.mesh.primitive_plane_add(size=16, location=(0, 0, -0.015))
    plane = bpy.context.object
    plane.name = "TEMP_Review_Ground"
    plane.data.materials.append(ground)
    for name, location, energy, size in (
        ("Key", (5.0, -4.0, 6.5), 850, 5.0),
        ("Fill", (2.5, 5.0, 4.0), 500, 4.0),
        ("Rear", (-4.0, 0.0, 3.5), 420, 3.0),
    ):
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = f"TEMP_Review_{name}"
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        point_at(light, (0, 0, 1.1))


def configure_scene():
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 960
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.035, 0.04, 0.045)


def save(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(path), check_existing=False)


def main():
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)

    # Required first-stop blockout, intentionally without the dense trolley wires.
    clear_scene()
    configure_scene()
    mats = create_materials()
    shelter = build_shelter(mats)
    trolley = build_trolley(mats, detailed=False)
    # Place the independent trolley fully in front of the shelter opening.
    # Its nearest basket/frame point is beyond the x=0.70 front uprights, so it
    # visually overlaps the bench from the reference camera without occupying
    # the same physical space.
    trolley.location = (1.25, 0.10, 0)
    trolley.rotation_euler[2] = -0.08
    save(BLOCKOUT_BLEND)

    # Second geometry pass and the independent runtime exports.
    clear_scene()
    configure_scene()
    mats = create_materials()
    shelter = build_shelter(mats)
    trolley = build_trolley(mats, detailed=True)
    trolley.location = (1.25, 0.10, 0)
    trolley.rotation_euler[2] = -0.08
    save(DETAIL_BLEND)

    export_glb(SHELTER_GLB, shelter)
    placed_location = trolley.location.copy()
    placed_rotation = trolley.rotation_euler.copy()
    trolley.location = (0, 0, 0)
    trolley.rotation_euler = (0, 0, 0)
    export_glb(TROLLEY_GLB, trolley)
    trolley.location = placed_location
    trolley.rotation_euler = placed_rotation
    export_glb(REFERENCE_GLB, shelter, trolley)

    add_review_stage()
    render_view("01-preston-busstop-front", (9.6, -0.15, 2.85), (0, 0, 1.25), 54)
    render_view("02-preston-busstop-left-three-quarter", (6.1, -6.2, 3.3), (0, 0, 1.20), 58)
    render_view("03-preston-busstop-right-three-quarter", (6.1, 6.3, 3.3), (0, 0.2, 1.20), 58)
    render_view("04-preston-busstop-rear-separation", (-6.6, -5.2, 2.8), (0, 0, 1.15), 55)
    save(REFERENCE_BLEND)

    print(f"Blockout: {BLOCKOUT_BLEND}")
    print(f"Detailed master: {DETAIL_BLEND}")
    print(f"Reference scene: {REFERENCE_BLEND}")
    print(f"Shelter GLB: {SHELTER_GLB}")
    print(f"Trolley GLB: {TROLLEY_GLB}")
    print(f"Combined game GLB: {REFERENCE_GLB}")


if __name__ == "__main__":
    main()
