"""Read-only validation report for The Hive Blender scene."""

from mathutils import Vector

import bpy


required = (
    "ACE_FrontEntrance",
    "ACE_FrontDoor_Left",
    "ACE_FrontDoor_Right",
    "ACE_EntranceCanopy",
    "ACE_EntranceGlass",
    "ACE_EntranceTriggerAnchor",
)
meshes = [
    obj
    for obj in bpy.context.scene.objects
    if obj.type == "MESH" and not obj.name.startswith("HIVE_Context_")
]
corners = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
minimum = Vector(
    (
        min(point.x for point in corners),
        min(point.y for point in corners),
        min(point.z for point in corners),
    )
)
maximum = Vector(
    (
        max(point.x for point in corners),
        max(point.y for point in corners),
        max(point.z for point in corners),
    )
)
unapplied = [
    obj.name
    for obj in meshes
    if any(abs(value - 1.0) > 1e-6 for value in obj.scale)
    or any(abs(value) > 1e-6 for value in obj.rotation_euler)
]
texture_nodes = []
for material in bpy.data.materials:
    if material.use_nodes:
        texture_nodes.extend(
            f"{material.name}:{node.name}"
            for node in material.node_tree.nodes
            if node.type == "TEX_IMAGE"
        )

print("VALIDATION required_missing=", [name for name in required if bpy.data.objects.get(name) is None])
print("VALIDATION mesh_count=", len(meshes))
print("VALIDATION triangles=", sum(len(poly.vertices) - 2 for obj in meshes for poly in obj.data.polygons))
print("VALIDATION bounds_m=", tuple(round(v, 3) for v in minimum), tuple(round(v, 3) for v in maximum))
print("VALIDATION unapplied_transforms=", len(unapplied))
print("VALIDATION image_textures=", texture_nodes)
print("VALIDATION unit_system=", bpy.context.scene.unit_settings.system)
print("VALIDATION scale_length=", bpy.context.scene.unit_settings.scale_length)
print("VALIDATION cameras_in_blend=", len(bpy.data.cameras))
print("VALIDATION lights_in_blend=", len(bpy.data.lights))
