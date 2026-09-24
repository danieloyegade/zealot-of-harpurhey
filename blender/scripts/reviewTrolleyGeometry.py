"""Geometry-only trolley review and promotion. Run validate before integrate.

Blender --background --python blender/scripts/reviewTrolleyGeometry.py -- --stage validate
Blender --background --python blender/scripts/reviewTrolleyGeometry.py -- --stage integrate

Integration replaces only the trolley hierarchy in existing source scenes;
all shelter geometry, materials, UVs, textures and review lights are retained.
"""
import json
import sys
from pathlib import Path
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import createBusShelter as geometry

OUT = geometry.PROJECT_ROOT / "renders/trolley-geometry"
SOURCE = geometry.SOURCE_DIR / "preston-shopping-trolley.blend"


def emission(name, colour):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    shader = nodes.new("ShaderNodeEmission")
    shader.inputs[0].default_value = (*colour, 1)
    out = nodes.new("ShaderNodeOutputMaterial")
    mat.node_tree.links.new(shader.outputs[0], out.inputs["Surface"])
    return mat


def camera():
    # Crop of the full photo: x=635..1065, y=770..1160, enlarged 2x.
    target = geometry.trolley_point((850, 965))
    bpy.ops.object.camera_add(location=target + Vector((5, 0, 0)))
    cam = bpy.context.object
    geometry.point_at(cam, target)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 430 / geometry.TROLLEY_PIXELS_PER_METRE
    bpy.context.scene.camera = cam
    return cam


def photo_plane():
    photo = bpy.data.images.load(str(OUT / "reference.jpg"), check_existing=True)
    mat = emission("Review_ReferencePhoto", (1, 1, 1))
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = photo
    shader = mat.node_tree.nodes.get("Emission")
    mat.node_tree.links.new(tex.outputs["Color"], shader.inputs[0])
    mesh = bpy.data.meshes.new("Review_PhotoPlane")
    mesh.from_pydata([geometry.trolley_point(p, -2) for p in
                     ((0, 1456), (1818, 1456), (1818, 0), (0, 0))], [], [(0, 1, 2, 3)])
    uv = mesh.uv_layers.new()
    for loop, co in zip(uv.data, ((0, 0), (1, 0), (1, 1), (0, 1))):
        loop.uv = co
    obj = bpy.data.objects.new("Review_PhotoPlane", mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(mat)
    return obj


def render(name):
    bpy.context.scene.render.filepath = str(OUT / (name + ".png"))
    bpy.ops.render.render(write_still=True)


def validate():
    OUT.mkdir(parents=True, exist_ok=True)
    for detailed in (False, True):
        geometry.clear_scene()
        geometry.configure_scene()
        scene = bpy.context.scene
        scene.render.resolution_x, scene.render.resolution_y = 860, 780
        scene.view_settings.view_transform = "Standard"
        scene.world.use_nodes = True
        scene.world.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
        scene.world.node_tree.nodes["Background"].inputs[1].default_value = 1
        trolley = geometry.build_trolley(geometry.create_materials(), detailed)
        cam = camera()
        if detailed:
            # Save the clean material-bearing source before review overrides.
            geometry.save(SOURCE)
        cyan = emission("Review_Trace", (0, 0.7, 0.9))
        black = emission("Review_Black", (0, 0, 0))
        for obj in geometry.descendants(trolley):
            if obj.type == "MESH":
                obj.data.materials.clear()
                obj.data.materials.append(cyan)
        plane = photo_plane()
        render("02-wire-photo-overlay" if detailed else "01-structural-photo-overlay")
        bpy.data.objects.remove(plane, do_unlink=True)
        for obj in geometry.descendants(trolley):
            if obj.type == "MESH":
                obj.data.materials[0] = black
        render("03-black-side-silhouette" if detailed else "00-structural-silhouette")
        if detailed:
            target = geometry.trolley_point((850, 965))
            cam.location = target + Vector((5, -2.3, 1.5))
            cam.data.ortho_scale = 1.6
            geometry.point_at(cam, target)
            render("04-black-three-quarter")
    (OUT / "trace-landmarks.json").write_text(json.dumps({
        "reference_size": [1818, 1456], "crop": [635, 770, 430, 390],
        "pixels_per_metre_inferred": geometry.TROLLEY_PIXELS_PER_METRE,
        "landmarks": geometry.TROLLEY_TRACE,
        "note": "Y/Z traced from visible near-side profile; hidden depth is inferred. Photo governs over approximate written ratios."
    }, indent=2) + "\n")


def integrate():
    # Separate invocation: only run after inspecting the saved silhouette.
    required = ("01-structural-photo-overlay.png", "03-black-side-silhouette.png", "04-black-three-quarter.png")
    if not all((OUT / name).exists() for name in required):
        raise RuntimeError("Render and inspect the silhouette before promotion")
    import createBusShelterTextured as textured
    for source in (geometry.BLOCKOUT_BLEND, geometry.DETAIL_BLEND,
                   geometry.REFERENCE_BLEND, textured.TEXTURED_BLEND):
        bpy.ops.wm.open_mainfile(filepath=str(source))
        old = bpy.data.objects["PRESTON_SHOPPING_TROLLEY"]
        location, rotation, scale = old.location.copy(), old.rotation_euler.copy(), old.scale.copy()
        mats = {key: bpy.data.materials[name] for key, name in (
            ("trolley", "MAT_Trolley_GalvanisedSteel"),
            ("plastic", "MAT_Trolley_WornBracket"), ("wheel", "MAT_Trolley_Tyre"))}
        for obj in reversed(geometry.descendants(old)):
            bpy.data.objects.remove(obj, do_unlink=True)
        trolley = geometry.build_trolley(mats, detailed=source != geometry.BLOCKOUT_BLEND)
        trolley.location, trolley.rotation_euler, trolley.scale = location, rotation, scale
        geometry.save(source)
        shelter = bpy.data.objects["PRESTON_BUS_SHELTER"]
        if source == geometry.DETAIL_BLEND:
            trolley.location = (0, 0, 0)
            trolley.rotation_euler = (0, 0, 0)
            geometry.export_glb(geometry.TROLLEY_GLB, trolley)
        elif source == geometry.REFERENCE_BLEND:
            geometry.export_glb(geometry.REFERENCE_GLB, shelter, trolley)
        elif source == textured.TEXTURED_BLEND:
            textured.export_glb(textured.REFERENCE_GLB, shelter, trolley)
    print("Replaced trolley in four source scenes and three GLBs; no texture bake.")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    stage = args[args.index("--stage")+1] if "--stage" in args else "validate"
    if stage == "validate":
        validate()
    elif stage == "integrate":
        integrate()
    else:
        raise ValueError(stage)
