"""Zealot of Harpurhey — player character, rigging pass.

Imports the reviewed blockout geometry (`createPlayerCharacterBlockout.py`) and
adds the production humanoid armature the asset brief asks for: full spine,
neck and head, clavicles, arms, legs, feet, per-finger articulation on both
hands (required because of the gauntlets), a dedicated delivery-bag bone, and
helper bones for the jacket hem, sleeve hems, wide trouser hems and bag straps.

Rigid parts (armour plates, shoes, hardware, head features) are bone-parented.
Everything that has to deform — torso, jacket body and sleeves, jeans seat and
legs, limbs, neck — is skinned with procedurally generated vertex weights
computed from distance to the bone segments, with a soft falloff on the
garments so the enormous jeans move as heavy cloth rather than as leggings.

Same promote-pattern as createTheHive.py over createTheHiveBlockout.py. The
blockout's own .blend / .glb / renders are left untouched.

Run headless:
    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --python blender/scripts/createPlayerCharacterRig.py
"""

import importlib.util
import math
import re
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLOCKOUT_SCRIPT = Path(__file__).with_name("createPlayerCharacterBlockout.py")
BLEND_PATH = PROJECT_ROOT / "blender" / "source" / "player-character-rigged.blend"
GLB_PATH = PROJECT_ROOT / "public" / "assets" / "models" / "player-character-rigged.glb"
RENDER_DIR = PROJECT_ROOT / "renders" / "player-character-rig"

spec = importlib.util.spec_from_file_location("pc_blockout", BLOCKOUT_SCRIPT)
blockout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(blockout)


# ---------------------------------------------------------------------------
# Skeleton. Positions match the blockout's own measurement skeleton exactly.
# ---------------------------------------------------------------------------

FINGER_OFFSETS = (-0.030, -0.010, 0.010, 0.030)
FINGER_LENGTHS = (0.072, 0.082, 0.078, 0.064)


def skeleton():
    """(name, head, tail, parent, connected) in world space."""
    bones = [
        ("root", (0, 0, 0), (0, 0, 0.14), None, False),
        ("hips", (0, 0.004, 0.965), (0, 0.004, 1.080), "root", False),
        ("spine", (0, 0.004, 1.080), (0, 0.004, 1.205), "hips", True),
        ("chest", (0, 0.004, 1.205), (0, 0.002, 1.400), "spine", True),
        ("neck", (0, 0.006, 1.400), (0, 0.010, 1.525), "chest", True),
        ("head", (0, 0.010, 1.525), (0, -0.004, 1.706), "neck", True),
        ("bag", (0, -0.120, 1.290), (0, -0.300, 1.290), "chest", False),
        ("helper_jacket_hem", (0, 0.060, 1.100), (0, 0.180, 1.086), "chest", False),
    ]
    for tag, sign in (("L", -1), ("R", 1)):
        bones += [
            (f"clavicle_{tag}", (sign * 0.030, 0.004, 1.395),
             (sign * 0.208, 0.000, 1.418), "chest", False),
            (f"upperarm_{tag}", (sign * 0.208, 0.000, 1.418),
             (sign * 0.232, 0.026, 1.145), f"clavicle_{tag}", True),
            (f"forearm_{tag}", (sign * 0.232, 0.026, 1.145),
             (sign * 0.240, 0.062, 0.882), f"upperarm_{tag}", True),
            (f"hand_{tag}", (sign * 0.240, 0.062, 0.882),
             (sign * 0.242, 0.076, 0.796), f"forearm_{tag}", True),
            (f"thumb_{tag}_1", (sign * 0.224, 0.082, 0.856),
             (sign * 0.218, 0.090, 0.830), f"hand_{tag}", False),
            (f"thumb_{tag}_2", (sign * 0.218, 0.090, 0.830),
             (sign * 0.212, 0.098, 0.806), f"thumb_{tag}_1", True),
            (f"thigh_{tag}", (sign * 0.088, 0.004, 0.960),
             (sign * 0.0898, 0.014, 0.455), "hips", False),
            (f"shin_{tag}", (sign * 0.0898, 0.014, 0.455),
             (sign * 0.0915, 0.020, 0.105), f"thigh_{tag}", True),
            (f"foot_{tag}", (sign * 0.0915, 0.020, 0.105),
             (sign * 0.098, 0.140, 0.026), f"shin_{tag}", True),
            # Helper bones for clothing secondary motion (brief section 18).
            (f"helper_sleeve_hem_{tag}", (sign * 0.254, 0.056, 0.976),
             (sign * 0.252, 0.060, 0.938), f"forearm_{tag}", False),
            (f"helper_trouser_hem_{tag}", (sign * 0.120, 0.014, 0.170),
             (sign * 0.126, -0.020, 0.062), f"shin_{tag}", False),
            (f"helper_bag_strap_{tag}", (sign * 0.146, -0.140, 1.516),
             (sign * 0.112, 0.184, 1.104), "chest", False),
        ]
        for index, offset in enumerate(FINGER_OFFSETS):
            x = sign * 0.242 + offset * sign
            length = FINGER_LENGTHS[index]
            bones += [
                (f"finger_{index + 1}_{tag}_1", (x, 0.078, 0.790),
                 (x, 0.080, 0.790 - length * 0.58), f"hand_{tag}", False),
                (f"finger_{index + 1}_{tag}_2", (x, 0.080, 0.790 - length * 0.58),
                 (x, 0.081, 0.790 - length), f"finger_{index + 1}_{tag}_1", True),
            ]
    return bones


def build_armature():
    armature_data = bpy.data.armatures.new("ZOH_PlayerArmature")
    armature = bpy.data.objects.new("ZOH_PlayerRig", armature_data)
    bpy.context.scene.collection.objects.link(armature)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="EDIT")
    created = {}
    for name, head, tail, parent, connected in skeleton():
        bone = armature_data.edit_bones.new(name)
        bone.head = Vector(head)
        bone.tail = Vector(tail)
        bone.use_deform = name != "root"
        created[name] = bone
    for name, head, tail, parent, connected in skeleton():
        if parent:
            created[name].parent = created[parent]
            created[name].use_connect = connected
    bpy.ops.object.mode_set(mode="OBJECT")
    armature.show_in_front = True
    return armature


# ---------------------------------------------------------------------------
# Mesh -> bone routing.
#
# Ordered: the first entry whose key matches the object name wins, so more
# specific prefixes must come before the general ones.
# ---------------------------------------------------------------------------

def routing_rules():
    """(pattern, mode, bone templates), first match wins.

    Patterns are side-aware regexes rather than plain prefixes. A prefix like
    "PC_Greave_" is side-agnostic — matching it against a per-side rule list
    binds every right-leg plate to the left leg's bones, which is exactly the
    kind of silent mirror bug that only shows up once the rig is posed.
    Templates take {S} (side) and {i} (finger index) from the match.
    """
    rules = [
        # --- head, face and hair: rigid on the head bone --------------------
        (r"^PC_(Head|Brow_|Ear_|EyeBall_|Iris_|LidUpper_|LidLower_|Nose|"
         r"Philtrum|Lip_|Chin|Jaw_|ScalpCap|Cornrow_|Edge_|Nape)",
         "rigid", ("head",)),

        # --- delivery bag ---------------------------------------------------
        (r"^PC_Bag_(Strap_[LR]|SternumStrap|StrapAnchor_[LR])$", "blend",
         ("bag", "chest", "helper_bag_strap_L", "helper_bag_strap_R")),
        (r"^PC_Bag_", "rigid", ("bag",)),

        # --- fingers: most specific patterns first ---------------------------
        (r"^PC_Gauntlet_Finger_(?P<i>\d)_1_(?P<S>[LR])$", "rigid",
         ("finger_{i}_{S}_1",)),
        (r"^PC_Gauntlet_Finger_(?P<i>\d)_2_(?P<S>[LR])$", "rigid",
         ("finger_{i}_{S}_2",)),
        (r"^PC_Gauntlet_FingerTip_(?P<i>\d)_(?P<S>[LR])$", "rigid",
         ("finger_{i}_{S}_2",)),
        (r"^PC_Finger_(?P<S>[LR])_(?P<i>\d)$", "blend",
         ("finger_{i}_{S}_1", "finger_{i}_{S}_2")),
        (r"^PC_(Gauntlet_)?Thumb_.*(?P<S>[LR])(_\d)?$", "blend",
         ("thumb_{S}_1", "thumb_{S}_2", "hand_{S}")),

        # --- hand ------------------------------------------------------------
        (r"^PC_Gauntlet_(HandPlate|HandRidge|Knuckle_\d|FingerBase)_(?P<S>[LR])$",
         "rigid", ("hand_{S}",)),
        (r"^PC_PalmBlock_(?P<S>[LR])$", "rigid", ("hand_{S}",)),
        (r"^PC_Palm_(?P<S>[LR])$", "blend", ("hand_{S}", "forearm_{S}")),

        # --- forearm: vambrace, gauntlet cuff, denim cuff ---------------------
        (r"^PC_Gauntlet_(Vambrace|Cuff|CuffLip)_(?P<S>[LR])$", "rigid",
         ("forearm_{S}",)),
        (r"^PC_Gauntlet_WristLame_\d_(?P<S>[LR])$", "rigid", ("forearm_{S}",)),
        (r"^PC_Gauntlet_Rivet_(?P<S>[LR])_\d$", "rigid", ("forearm_{S}",)),
        (r"^PC_Jacket_Cuff_(?P<S>[LR])$", "blend",
         ("forearm_{S}", "helper_sleeve_hem_{S}")),
        (r"^PC_Jacket_ElbowSeam_(?P<S>[LR])$", "rigid", ("forearm_{S}",)),

        # --- arms and sleeves -------------------------------------------------
        (r"^PC_Jacket_SleeveLower_(?P<S>[LR])$", "cloth",
         ("upperarm_{S}", "forearm_{S}", "helper_sleeve_hem_{S}")),
        (r"^PC_Jacket_SleeveUpper_(?P<S>[LR])$", "cloth",
         ("chest", "clavicle_{S}", "upperarm_{S}", "forearm_{S}")),
        (r"^PC_UpperArm_(?P<S>[LR])$", "blend",
         ("clavicle_{S}", "upperarm_{S}", "forearm_{S}")),
        (r"^PC_Forearm_(?P<S>[LR])$", "blend",
         ("upperarm_{S}", "forearm_{S}", "hand_{S}")),

        # --- legs --------------------------------------------------------------
        (r"^PC_Greave_\w*?(?P<S>[LR])(_\d)?$", "rigid", ("shin_{S}",)),
        (r"^PC_Shoe_\w*?(?P<S>[LR])$", "rigid", ("foot_{S}",)),
        (r"^PC_Sock_(?P<S>[LR])$", "blend", ("shin_{S}", "foot_{S}")),
        (r"^PC_Thigh_(?P<S>[LR])$", "blend", ("hips", "thigh_{S}", "shin_{S}")),
        (r"^PC_Shin_(?P<S>[LR])$", "blend",
         ("thigh_{S}", "shin_{S}", "foot_{S}")),
        (r"^PC_Jeans_(Leg|Outseam|Inseam|Hem)_(?P<S>[LR])$", "cloth",
         ("hips", "thigh_{S}", "shin_{S}", "helper_trouser_hem_{S}", "foot_{S}")),

        # --- jacket body and torso ---------------------------------------------
        (r"^PC_Jacket_(Body|HemBand)$", "cloth",
         ("hips", "spine", "chest", "helper_jacket_hem")),
        (r"^PC_Jacket_(Collar|Placket|Button_|Pocket|YokeSeam|PanelSeam|BackSeam)",
         "rigid", ("chest",)),
        (r"^PC_Torso$", "blend", ("hips", "spine", "chest", "neck")),
        (r"^PC_Neck$", "blend", ("chest", "neck", "head")),
        # Weighted to the pelvis only. With the thighs in the candidate set the
        # seat got dragged up with the knees under hip flexion, exposing the
        # body underneath.
        (r"^PC_Jeans_(Seat|Waistband)$", "blend", ("hips", "spine")),
        (r"^PC_Jeans_(BeltLoop|Fly|FrontPocket|BackPocket)", "rigid", ("hips",)),
    ]
    return [(re.compile(pattern), mode, bones) for pattern, mode, bones in rules]


def route(name, rules):
    for pattern, mode, templates in rules:
        match = pattern.match(name)
        if match:
            fields = {k: v for k, v in (match.groupdict() or {}).items()
                      if v is not None}
            return mode, tuple(t.format(**fields) for t in templates)
    return None


# ---------------------------------------------------------------------------
# Procedural skinning
# ---------------------------------------------------------------------------

def point_segment_distance(point, head, tail):
    axis = tail - head
    length_squared = axis.length_squared
    if length_squared < 1e-12:
        return (point - head).length
    t = max(0.0, min(1.0, (point - head).dot(axis) / length_squared))
    return (point - (head + axis * t)).length


def skin_mesh(obj, armature, bone_names, falloff, max_influences=4):
    """Weight every vertex by inverse distance to the candidate bone segments.

    `falloff` controls how tightly the mesh follows one bone: a high value
    snaps to the nearest bone, a low value spreads the influence. Garments use
    a low value on purpose — jeans this wide have to move as heavy cloth, not
    as a second skin (brief section 18).
    """
    segments = []
    for name in bone_names:
        bone = armature.data.bones.get(name)
        if bone is None:
            raise RuntimeError(f"{obj.name}: unknown bone {name}")
        segments.append((name, bone.head_local.copy(), bone.tail_local.copy()))

    groups = {name: obj.vertex_groups.new(name=name) for name, _, _ in segments}
    matrix = obj.matrix_world
    for vertex in obj.data.vertices:
        position = matrix @ vertex.co
        scored = []
        for name, head, tail in segments:
            distance = point_segment_distance(position, head, tail)
            scored.append((1.0 / ((distance + 0.012) ** falloff), name))
        scored.sort(reverse=True)
        chosen = scored[:max_influences]
        # Discard negligible influences, or a distant bone drags the whole
        # garment back toward the rest pose when the limb swings.
        cutoff = chosen[0][0] * 0.04
        chosen = [entry for entry in chosen if entry[0] >= cutoff]
        total = sum(weight for weight, _ in chosen)
        for weight, name in chosen:
            groups[name].add([vertex.index], weight / total, "REPLACE")

    modifier = obj.modifiers.new("armature", "ARMATURE")
    modifier.object = armature
    modifier.use_vertex_groups = True


def rigid_skin(obj, armature, bone_name):
    """Bind every vertex to one bone at full weight.

    Motion is identical to bone-parenting, but the mesh stays a normal skinned
    mesh, so it can be merged with its neighbours instead of costing its own
    draw call.
    """
    if bone_name not in armature.data.bones:
        raise RuntimeError(f"{obj.name}: unknown bone {bone_name}")
    group = obj.vertex_groups.new(name=bone_name)
    group.add([v.index for v in obj.data.vertices], 1.0, "REPLACE")
    modifier = obj.modifiers.new("armature", "ARMATURE")
    modifier.object = armature
    modifier.use_vertex_groups = True


def reparent_to_armature(obj, armature):
    bpy.context.view_layer.update()
    world = obj.matrix_world.copy()
    obj.parent = armature
    obj.parent_type = "OBJECT"
    obj.matrix_parent_inverse = armature.matrix_world.inverted()
    obj.matrix_world = world


FALLOFF = {"blend": 4.0, "cloth": 3.0}


def apply_modifiers(obj):
    """Bake the blockout's bevel modifiers into the mesh.

    Skinned meshes must export with export_apply=False (applying modifiers at
    export time would discard the armature binding), so the bevels have to be
    real geometry before binding. Without this the rigged GLB ships hard-edged
    while the blockout GLB — which does apply at export — does not.
    """
    if not obj.modifiers:
        return
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    for modifier in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=modifier.name)


def bind(armature):
    rules = routing_rules()
    meshes = [o for o in bpy.data.objects
              if o.type == "MESH" and o.name.startswith("PC_")]
    for obj in meshes:
        apply_modifiers(obj)
    unrouted = []
    rigid, skinned = 0, 0
    for obj in meshes:
        result = route(obj.name, rules)
        if result is None:
            unrouted.append(obj.name)
            continue
        mode, bones = result
        reparent_to_armature(obj, armature)
        if mode == "rigid":
            rigid_skin(obj, armature, bones[0])
            rigid += 1
        else:
            skin_mesh(obj, armature, bones, FALLOFF[mode])
            skinned += 1
    if unrouted:
        raise RuntimeError("Unrouted meshes: " + ", ".join(sorted(unrouted)[:12]))
    return rigid, skinned


def add_attachment_points(armature):
    """Named empties gameplay code can attach objects to."""
    points = (
        ("attach-hand-L", "hand_L"),
        ("attach-hand-R", "hand_R"),
        ("attach-bag", "bag"),
        ("attach-head", "head"),
    )
    created = []
    for name, bone_name in points:
        bone = armature.data.bones[bone_name]
        empty = bpy.data.objects.new(name, None)
        empty.empty_display_type = "ARROWS"
        empty.empty_display_size = 0.06
        bpy.context.scene.collection.objects.link(empty)
        empty.location = bone.tail_local
        bpy.ops.object.select_all(action="DESELECT")
        empty.select_set(True)
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode="POSE")
        armature.data.bones.active = armature.data.bones[bone_name]
        bpy.ops.object.parent_set(type="BONE", keep_transform=True)
        bpy.ops.object.mode_set(mode="OBJECT")
        created.append(empty)
    return created


# ---------------------------------------------------------------------------
# Validation poses (brief section 23, views O and P)
# ---------------------------------------------------------------------------

# Poses are authored as world-space rotations, not as raw bone eulers.
#
# A bone's local euler axes depend on its rest orientation and roll, so raw
# values mean nothing you can reason about — the sign that leans the spine
# forward swings the thigh backward. Here every entry is (pitch, yaw) in
# degrees about the world X and Z axes, converted into each bone's own rest
# frame. Positive pitch rotates about world X such that an upward-pointing
# bone (spine, neck) leans FORWARD and a downward-pointing bone (thigh, upper
# arm) swings its tail BACKWARD; rotations compound down the chain, so a value
# is always relative to the parent.

WALK_POSE = {
    "chest": (4, 0),
    "neck": (-2, 0),
    # Leading leg: thigh 24 deg forward, ankle 6 deg forward of vertical.
    "thigh_L": (-24, 0), "shin_L": (18, 0), "foot_L": (-12, 0),
    # Trailing leg: thigh 18 deg back, ankle 34 deg back, toeing off.
    "thigh_R": (18, 0), "shin_R": (16, 0), "foot_R": (26, 0),
    "upperarm_L": (16, 0), "forearm_L": (10, 0),
    "upperarm_R": (-20, 0), "forearm_R": (14, 0),
    "helper_trouser_hem_L": (-10, 0),
    "helper_trouser_hem_R": (12, 0),
    "helper_jacket_hem": (6, 0),
}

BICYCLE_POSE = {
    "hips": (40, 0), "spine": (8, 0), "chest": (6, 0),
    # Head comes back up out of the pitched torso to look along the road.
    "neck": (-22, 0), "head": (-22, 0),
    # Left leg at the top of the stroke, right leg extended.
    "thigh_L": (-110, 0), "shin_L": (55, 0), "foot_L": (20, 0),
    "thigh_R": (-62, 0), "shin_R": (12, 0), "foot_R": (8, 0),
    # Reaching forward and down to the bars, out of an already pitched torso.
    "clavicle_L": (0, -6), "clavicle_R": (0, 6),
    "upperarm_L": (-94, 0), "upperarm_R": (-94, 0),
    "forearm_L": (-10, 0), "forearm_R": (-10, 0),
    "hand_L": (-10, 0), "hand_R": (-10, 0),
    "helper_trouser_hem_L": (-18, 0),
    "helper_trouser_hem_R": (-12, 0),
    "helper_jacket_hem": (14, 0),
}
for _side in ("L", "R"):
    for _finger in range(1, 5):
        BICYCLE_POSE[f"finger_{_finger}_{_side}_1"] = (-55, 0)
        BICYCLE_POSE[f"finger_{_finger}_{_side}_2"] = (-60, 0)
    BICYCLE_POSE[f"thumb_{_side}_1"] = (-30, 0)


def world_rotation(armature, bone_name, pitch_degrees, yaw_degrees=0.0):
    """Convert a world-space (pitch, yaw) into the bone's own rest frame."""
    rest = armature.data.bones[bone_name].matrix_local.to_3x3()
    world = (Matrix.Rotation(math.radians(yaw_degrees), 3, "Z")
             @ Matrix.Rotation(math.radians(-pitch_degrees), 3, "X"))
    return (rest.inverted() @ world @ rest).to_euler("XYZ")


def apply_pose(armature, pose):
    clear_pose(armature)
    for name, (pitch, yaw) in pose.items():
        bone = armature.pose.bones.get(name)
        if bone is None:
            raise RuntimeError(f"Pose references unknown bone: {name}")
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = world_rotation(armature, name, pitch, yaw)
    bpy.context.view_layer.update()


def clear_pose(armature):
    for bone in armature.pose.bones:
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = (0.0, 0.0, 0.0)
        bone.location = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

RIG_VIEWS = (
    ("view-o-walking-pose.png", WALK_POSE, (2.60, 3.35, 1.42), (0, 0, 1.02),
     80, 900, 1200, "studio"),
    ("view-p-bicycle-pose.png", BICYCLE_POSE, (2.75, 2.95, 1.28), (0, 0.05, 1.00),
     78, 900, 1200, "studio"),
    ("view-q-walking-rear-gameplay.png", WALK_POSE, (0.0, -6.475, 3.123),
     (0, 0, 1.05), 38.6, 1280, 720, "night"),
    ("view-r-rig-rest-front.png", None, (0.0, 4.40, 1.10), (0, 0, 1.00),
     85, 900, 1200, "studio"),
)


def render_views(armature, rig):
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    blockout.part("ZOH_REVIEW")
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "rig-review-camera"
    camera.data.sensor_width = 36.0
    blockout.adopt(camera)
    bpy.context.scene.camera = camera
    for filename, pose, location, target, lens, width, height, mode in RIG_VIEWS:
        apply_pose(armature, pose) if pose else clear_pose(armature)
        blockout.set_lighting(rig, mode)
        camera.location = location
        camera.data.lens = lens
        camera.rotation_euler = (
            Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene = bpy.context.scene
        scene.render.resolution_x = width
        scene.render.resolution_y = height
        scene.render.filepath = str(RENDER_DIR / filename)
        bpy.ops.render.render(write_still=True)
        print(f"  rendered {filename}")
    clear_pose(armature)
    blockout.set_lighting(rig, "studio")


MERGE_COLLECTIONS = (
    "ZOH_BODY", "ZOH_HEAD", "ZOH_HAIR_CORNROWS", "ZOH_JACKET_DENIM",
    "ZOH_JEANS_OVERSIZED", "ZOH_GREAVES", "ZOH_GAUNTLETS", "ZOH_SHOES",
    "ZOH_DELIVERY_BAG",
)


def merge_for_runtime():
    """Join each costume component into one skinned mesh.

    259 separate meshes is 259 draw calls for a single character. Everything is
    skinned to the same armature, so meshes can be joined freely and their
    materials survive as separate slots — which glTF exports as primitives.

    Merging happens PER COMPONENT rather than across the whole character, so the
    jacket, jeans, bag, armour and so on stay independently swappable (asset
    brief section 20). The editable .blend is saved before this runs.
    """
    merged = []
    for name in MERGE_COLLECTIONS:
        collection = bpy.data.collections.get(name)
        if collection is None:
            continue
        meshes = [o for o in collection.objects if o.type == "MESH"]
        if not meshes:
            continue
        bpy.ops.object.select_all(action="DESELECT")
        for obj in meshes:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        if len(meshes) > 1:
            bpy.ops.object.join()
        joined = bpy.context.view_layer.objects.active
        joined.name = name.replace("ZOH_", "PC_") + "_MERGED"
        merged.append((joined.name, len(meshes), len(joined.data.materials)))
    return merged


def export_asset(armature):
    GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    armature.select_set(True)
    for child in armature.children_recursive:
        child.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH),
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_skins=True,
        export_apply=False,
    )


def rig_notes(rigid, skinned):
    text = bpy.data.texts.new("PC_RIG_NOTES")
    text.write(
        "Zealot of Harpurhey - player character, rigging pass.\n"
        "\n"
        f"Rigid bone-parented meshes : {rigid}\n"
        f"Skinned meshes             : {skinned}\n"
        "\n"
        "Deform bones cover spine/neck/head, clavicles, arms, hands, two bones\n"
        "per finger plus thumbs, legs and feet, a delivery-bag bone, and helper\n"
        "bones for the jacket hem, sleeve hems, wide trouser hems and bag straps.\n"
        "\n"
        "Garment meshes are skinned with a deliberately soft falloff so the wide\n"
        "jeans move as heavy cloth. Armour, shoes and hardware are rigid.\n"
        "\n"
        "This file supersedes the blockout's pivot-empty animation contract.\n"
        "src/player/PlayerController.ts still drives the older\n"
        "player-character.glb by pivot name and must be switched to skeletal\n"
        "animation before this GLB is used in game.\n"
    )
    return text


def main():
    blockout.reset_scene()
    blockout.make_collections()
    blockout.setup_scene()
    root, materials = blockout.build_character()

    # The rig replaces the blockout's empty-pivot hierarchy, so unhook the
    # meshes from it before binding. The pivots stay in the file as markers.
    bpy.context.view_layer.update()
    armature = build_armature()
    rigid, skinned = bind(armature)
    add_attachment_points(armature)

    rig = blockout.build_lighting(materials)
    rig_notes(rigid, skinned)

    # Save the editable, still-modular source BEFORE merging for runtime.
    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

    merged = merge_for_runtime()
    export_asset(armature)
    render_views(armature, rig)

    print("\n--- runtime merge ---")
    for name, sources, slots in merged:
        print(f"  {name:34s} {sources:4d} meshes -> {slots} material slots")

    print("\n--- player character rig ---")
    print(f"  deform bones : {len([b for b in armature.data.bones if b.use_deform])}")
    print(f"  rigid meshes : {rigid}")
    print(f"  skinned      : {skinned}")
    print(f"Saved Blender master: {BLEND_PATH}")
    print(f"Exported rigged GLB: {GLB_PATH}")
    print(f"Rendered reviews: {RENDER_DIR}")


if __name__ == "__main__":
    main()
