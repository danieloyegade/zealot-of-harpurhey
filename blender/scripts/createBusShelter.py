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


def add_wheel(name, location, mat, parent, steering=0.0, radius=0.09):
    # Small utilitarian casters, not full-size supermarket wheels: everything
    # scales off the one radius so the fork stays proportional.
    scale = radius / 0.09
    wheel_root = add_empty(name, parent, location)
    wheel_root.rotation_euler[2] = steering
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=12,
        radius=radius,
        depth=0.052 * scale,
        location=(0, 0, 0),
        rotation=(0, pi / 2, 0),
    )
    wheel = bpy.context.object
    wheel.name = f"{name}_Tyre"
    wheel.data.materials.append(mat[0])
    parent_to(wheel, wheel_root)
    add_box(f"{name}_Fork", (0.075 * scale, 0.045 * scale, 0.15 * scale), (0, 0, 0.095 * scale), mat[1], wheel_root, bevel=0.012 * scale)
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
        # Aged galvanised/chromed steel: the whole structure (basket, frame,
        # handle) -- moderate, irregular roughness rather than a mirror-polish
        # chrome, so it reads as an outdoor, abandoned object.
        "trolley": material("MAT_Trolley_GalvanisedSteel", (0.50, 0.52, 0.50), 0.50, 0.78),
        # Darker, less metallic worn bracket/fork metal -- the one deliberate
        # material break, at the wheel mounts, for a hint of "old and
        # utilitarian" without needing a baked weathering pass.
        "plastic": material("MAT_Trolley_WornBracket", (0.10, 0.10, 0.11), 0.62, 0.55),
        "wheel": material("MAT_Trolley_Tyre", (0.03, 0.032, 0.034), 0.88),
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


# Pixel landmarks measured on the supplied 1818 x 1456 photograph. +Y is
# screen-right/nose, +X is the near side, Z is up. Absolute scale is inferred;
# relative Y/Z positions are traced, not generic trolley dimensions.
TROLLEY_TRACE = {
    "rear_top": (732, 817), "front_top": (1027, 843),
    "rear_bottom": (769, 925), "front_bottom": (1024, 915),
    "rear_foot": (692, 1091), "rear_bend": (757, 938),
    "front_bend": (834, 934), "front_foot": (980, 1091),
    "rear_wheel": (682, 1124), "front_wheel": (990, 1124),
    "handle": (697, 797),
}
TROLLEY_PIXELS_PER_METRE = 325.0
TROLLEY_IMAGE_ORIGIN = (835, 1143)


def trolley_point(pixel, x=0.0):
    u, v = pixel
    return Vector((x, (u - TROLLEY_IMAGE_ORIGIN[0]) / TROLLEY_PIXELS_PER_METRE,
                   (TROLLEY_IMAGE_ORIGIN[1] - v) / TROLLEY_PIXELS_PER_METRE))


def add_bent_tube(name, points, radius, mat, parent, rounding=0.04):
    """One connected tube, with short quadratic bends between straight runs."""
    points = [Vector(p) for p in points]
    sampled = [points[0]]
    for previous, corner, following in zip(points, points[1:], points[2:]):
        distance = min(rounding, (previous-corner).length/3, (following-corner).length/3)
        a = corner + (previous-corner).normalized()*distance
        b = corner + (following-corner).normalized()*distance
        sampled.append(a)
        for i in range(1, 9):
            t = i/8
            sampled.append((1-t)**2*a + 2*(1-t)*t*corner + t*t*b)
    sampled.append(points[-1])
    curve = bpy.data.curves.new(name + "_Curve", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = 3
    curve.use_fill_caps = True
    spline = curve.splines.new("POLY")
    spline.points.add(len(sampled)-1)
    for p, co in zip(spline.points, sampled):
        p.co = (*co, 1)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    curve.materials.append(mat)
    parent_to(obj, parent)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def build_trolley(mats, detailed=True):
    """Reconstruct the photographed profile; retain genuinely open 3D wirework."""
    root = add_empty("PRESTON_SHOPPING_TROLLEY")
    basket = add_empty("TROLLEY_Basket", root)
    frame = add_empty("TROLLEY_Frame", root)
    handle = add_empty("TROLLEY_Handle", root)
    metal = mats["trolley"]
    # Width is inferred from the visible return edges in the photograph.
    # The near-side Y/Z silhouette is the traced constraint on both sides.
    corners = {}
    for side, label in ((1, "R"), (-1, "L")):
        rt = trolley_point(TROLLEY_TRACE["rear_top"], side*0.265)
        ft = trolley_point(TROLLEY_TRACE["front_top"], side*0.225)
        rb = trolley_point(TROLLEY_TRACE["rear_bottom"], side*0.205)
        fb = trolley_point(TROLLEY_TRACE["front_bottom"], side*0.185)
        corners[label] = (rt, ft, rb, fb)
        for part, a, b in (("Top", rt, ft), ("Bottom", rb, fb),
                            ("Rear", rt, rb), ("Front", ft, fb)):
            add_cylinder_between(f"TROLLEY_Basket_{part}_{label}", a, b, 0.006, metal, basket, 8)
        if detailed:
            # 27 side ribs per wall, compared with 12 in the previous tray.
            for i in range(1, 28):
                t = i/28
                add_cylinder_between(f"TROLLEY_Basket_SideWire_{label}_{i:02d}",
                                     rt.lerp(ft, t), rb.lerp(fb, t), 0.0022, metal, basket, 6)
            for i, t in enumerate((0.18, 0.84)):
                add_cylinder_between(f"TROLLEY_Basket_SideRail_{label}_{i}",
                                     rt.lerp(rb, t), ft.lerp(fb, t), 0.0025, metal, basket, 6)

    left, right = corners["L"], corners["R"]
    for i in range(4):
        add_cylinder_between(f"TROLLEY_Basket_CrossRail_{i}", left[i], right[i], 0.006, metal, basket, 8)
    if detailed:
        for end, top_index, bottom_index in (("Rear", 0, 2), ("Front", 1, 3)):
            for i in range(1, 13):
                t = i/13
                add_cylinder_between(f"TROLLEY_Basket_{end}Wire_{i:02d}",
                                     left[top_index].lerp(right[top_index], t),
                                     left[bottom_index].lerp(right[bottom_index], t), 0.0022, metal, basket, 6)
            for i, t in enumerate((0.18, 0.84)):
                add_cylinder_between(f"TROLLEY_Basket_{end}Rail_{i}",
                                     left[top_index].lerp(left[bottom_index], t),
                                     right[top_index].lerp(right[bottom_index], t), 0.0025, metal, basket, 6)
        # An actual wire floor; the previous model had an empty hole underneath.
        for i in range(1, 28):
            t = i/28
            add_cylinder_between(f"TROLLEY_Basket_FloorCross_{i:02d}",
                                 left[2].lerp(left[3], t), right[2].lerp(right[3], t), 0.0022, metal, basket, 6)
        for i in range(1, 11):
            t = i/11
            add_cylinder_between(f"TROLLEY_Basket_FloorLong_{i:02d}",
                                 left[2].lerp(right[2], t), left[3].lerp(right[3], t), 0.0022, metal, basket, 6)

    for side, label in ((1, "R"), (-1, "L")):
        # Both legs meet a short, rounded saddle beneath the REAR of the
        # basket. They do not descend from opposite basket corners.
        path = [trolley_point(TROLLEY_TRACE[key], side*0.215)
                for key in ("rear_foot", "rear_bend", "front_bend", "front_foot")]
        add_bent_tube(f"TROLLEY_Frame_Continuous_{label}", path, 0.0125, metal, frame, 0.09)
        rt, ft, rb, fb = corners[label]
        for i, t in enumerate((0.0, 0.24)):
            upper = rb.lerp(fb, t)
            lower = Vector((side*0.215, upper.y, trolley_point((800, 936)).z))
            add_cylinder_between(f"TROLLEY_Frame_BasketMount_{label}_{i}", lower, upper, 0.009, metal, frame, 8)
        grip = trolley_point(TROLLEY_TRACE["handle"], side*0.265)
        add_bent_tube(f"TROLLEY_Handle_Return_{label}",
                      [rb, rt, grip], 0.010, metal, handle, 0.025)

        for end, key, foot_key in (("R", "rear_wheel", "rear_foot"), ("F", "front_wheel", "front_foot")):
            centre = trolley_point(TROLLEY_TRACE[key], side*0.215)
            foot = trolley_point(TROLLEY_TRACE[foot_key], side*0.215)
            wheel_root = add_empty(f"TROLLEY_Wheel_{end}{label}", root)
            radius = centre.z  # Tangency at Z=0, no floating tyres.
            bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=radius, depth=0.028,
                                               location=centre, rotation=(0, pi/2, 0))
            wheel = bpy.context.object
            wheel.name = f"TROLLEY_Wheel_{end}{label}_Tyre"
            wheel.data.materials.append(mats["wheel"])
            parent_to(wheel, wheel_root)
            for offset in (-0.023, 0.023):
                axle = centre + Vector((offset, 0, 0))
                crown = foot + Vector((offset, 0, -0.025))
                add_cylinder_between(f"TROLLEY_Wheel_{end}{label}_Fork_{offset}",
                                     axle, crown, 0.009, mats["plastic"], wheel_root, 8)
            add_cylinder_between(f"TROLLEY_Wheel_{end}{label}_Swivel", foot,
                                 foot-Vector((0, 0, 0.034)), 0.022, mats["plastic"], wheel_root, 12)
            add_cylinder_between(f"TROLLEY_Wheel_{end}{label}_Axle",
                                 centre-Vector((0.031, 0, 0)), centre+Vector((0.031, 0, 0)), 0.010, metal, wheel_root, 10)

    add_cylinder_between("TROLLEY_Handle_Bar", trolley_point(TROLLEY_TRACE["handle"], -0.265),
                         trolley_point(TROLLEY_TRACE["handle"], 0.265), 0.014, metal, handle, 12)
    if detailed:
        chain = add_empty("TROLLEY_Chain", root)
        for i in range(12):
            p = trolley_point((697, 802+i*4), 0.265)
            bpy.ops.mesh.primitive_torus_add(major_radius=0.007, minor_radius=0.0018,
                                            major_segments=10, minor_segments=5, location=p,
                                            rotation=(0, pi/2, i*pi/2))
            link = bpy.context.object
            link.name = f"TROLLEY_Chain_Link_{i:02d}"
            link.data.materials.append(metal)
            parent_to(link, chain)
    if detailed:
        # Reuse the approved material atlas on rebuild; no geometry mutation.
        from textureTrolley import apply_saved
        apply_saved(root)
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
