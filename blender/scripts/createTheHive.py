"""Build, render and export the detailed geometry-only model of The Hive."""

import importlib.util
from pathlib import Path

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLOCKOUT_SCRIPT = Path(__file__).with_name("createTheHiveBlockout.py")
BLEND_PATH = PROJECT_ROOT / "blender" / "source" / "the_hive.blend"
GLB_PATH = PROJECT_ROOT / "public" / "assets" / "models" / "the_hive.glb"
RENDER_DIR = PROJECT_ROOT / "renders" / "the-hive"

spec = importlib.util.spec_from_file_location("hive_blockout", BLOCKOUT_SCRIPT)
blockout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(blockout)


def get_collection(name):
    collection = bpy.data.collections.get(name)
    if collection is None:
        raise RuntimeError(f"Required collection missing: {name}")
    return collection


def get_material(name):
    material = bpy.data.materials.get(name)
    if material is None:
        raise RuntimeError(f"Required material missing: {name}")
    return material


def delete_prefix(prefix):
    for obj in list(bpy.data.objects):
        if obj.name.startswith(prefix):
            bpy.data.objects.remove(obj, do_unlink=True)


def front_window(name, x, y, z, width, height, collection, glass, frame, mullions=True):
    """Efficient facade window with a dark recess, recessed glass and real frame depth."""
    blockout.box(f"{name}_Recess", (width + 0.18, 0.15, height + 0.18), (x, y, z), frame, collection)
    blockout.box(f"{name}_Glass", (width, 0.065, height), (x, y - 0.09, z), glass, collection)
    border = 0.085
    for suffix, dx in (("Left", -width / 2), ("Right", width / 2)):
        blockout.box(f"{name}_Frame_{suffix}", (border, 0.20, height + 0.17), (x + dx, y - 0.13, z), frame, collection)
    for suffix, dz in (("Head", height / 2), ("Sill", -height / 2)):
        blockout.box(f"{name}_Frame_{suffix}", (width + 0.17, 0.20, border), (x, y - 0.13, z + dz), frame, collection)
    if mullions:
        blockout.box(f"{name}_Mullion", (0.07, 0.21, height), (x, y - 0.14, z), frame, collection)
        blockout.box(f"{name}_Transom", (width, 0.21, 0.07), (x, y - 0.14, z + height * 0.15), frame, collection)


def side_window(name, x, y, z, width, height, collection, glass, frame):
    blockout.box(f"{name}_Recess", (0.15, width + 0.18, height + 0.18), (x, y, z), frame, collection)
    blockout.box(f"{name}_Glass", (0.065, width, height), (x + 0.09, y, z), glass, collection)
    border = 0.085
    for suffix, dy in (("Near", -width / 2), ("Far", width / 2)):
        blockout.box(f"{name}_Frame_{suffix}", (0.20, border, height + 0.17), (x + 0.13, y + dy, z), frame, collection)
    for suffix, dz in (("Head", height / 2), ("Sill", -height / 2)):
        blockout.box(f"{name}_Frame_{suffix}", (0.20, width + 0.17, border), (x + 0.13, y, z + dz), frame, collection)
    blockout.box(f"{name}_Mullion", (0.21, 0.07, height), (x + 0.14, y, z), frame, collection)


def framed_door(name, x, y, z, width, height, collection, glass, frame):
    door = blockout.box(name, (width, 0.07, height), (x, y, z), glass, collection)
    border = 0.09
    for suffix, dx in (("Left", -width / 2), ("Right", width / 2)):
        component = blockout.box(f"{name}_Frame_{suffix}", (border, 0.16, height + border), (x + dx, y - 0.04, z), frame, collection)
        world_matrix = component.matrix_world.copy()
        component.parent = door
        component.matrix_world = world_matrix
    for suffix, dz in (("Head", height / 2), ("Bottom", -height / 2)):
        component = blockout.box(f"{name}_Frame_{suffix}", (width + border, 0.16, border), (x, y - 0.04, z + dz), frame, collection)
        world_matrix = component.matrix_world.copy()
        component.parent = door
        component.matrix_world = world_matrix
    component = blockout.box(f"{name}_Midrail", (width, 0.17, 0.075), (x, y - 0.05, z + 0.05), frame, collection)
    world_matrix = component.matrix_world.copy()
    component.parent = door
    component.matrix_world = world_matrix
    return door


def add_ground_floor(groups, mats):
    glazing = blockout.make_collection("HIVE_GroundGlazing", bpy.data.collections["HIVE_MASTER"])
    columns = blockout.make_collection("HIVE_ConcreteColumns", bpy.data.collections["HIVE_MASTER"])
    # Hide the broad blockout piers in favour of properly separated structural columns.
    delete_prefix("HIVE_GroundFloor_BlockoutPier_")
    front_y = -1.30
    bay_edges = (-21.4, -17.6, -13.8, -10.0, -6.2, -2.4, 1.4, 5.2, 9.0, 12.8, 16.6, 21.4)
    for index, x in enumerate(bay_edges):
        blockout.box(f"HIVE_ConcreteColumn_{index + 1:02d}", (0.58, 1.05, 3.62), (x, -0.76, 1.81), mats["concrete"], columns, 0.025)
    for index in range(len(bay_edges) - 1):
        left, right = bay_edges[index], bay_edges[index + 1]
        x = (left + right) / 2
        width = right - left - 0.34
        if -9.0 < x < -0.5:  # entrance frontage is built separately
            continue
        blockout.box(f"HIVE_GroundGlazing_Bay_{index + 1:02d}", (width, 0.06, 3.06), (x, front_y, 1.60), mats["glass"], glazing)
        blockout.box(f"HIVE_GroundGlazing_Head_{index + 1:02d}", (width, 0.14, 0.10), (x, front_y - 0.05, 3.10), mats["metal"], glazing)
        blockout.box(f"HIVE_GroundGlazing_Mullion_{index + 1:02d}", (0.075, 0.14, 3.02), (x, front_y - 0.05, 1.60), mats["metal"], glazing)


def add_dark_facade_windows(groups, mats):
    windows = blockout.make_collection("HIVE_Windows", bpy.data.collections["HIVE_MASTER"])
    # West and east projecting black-brick wings, visible at pedestrian range.
    for floor, z in enumerate((5.65, 8.55, 11.0)):
        for index, x in enumerate((-20.0, -17.5, -15.0, -12.5)):
            front_window(f"Hive_Window_DarkFacade_W_F{floor + 1}_{index + 1}", x, -2.02, z, 1.05, 2.05, windows, mats["glass"], mats["metal"])
        for index, x in enumerate((14.1, 16.6, 19.1, 21.0)):
            front_window(f"Hive_Window_DarkFacade_E_F{floor + 1}_{index + 1}", x, -2.38, z, 1.0, 2.05, windows, mats["glass"], mats["metal"])
    # Windows behind the screen: these provide readable wall -> glass -> air -> screen layering.
    for floor, z in enumerate((5.45, 8.35, 10.8)):
        for index, x in enumerate((-8.7, -5.4, -2.1, 1.2, 4.5, 7.8, 11.1)):
            front_window(f"Hive_Window_BehindScreen_F{floor + 1}_{index + 1}", x, -1.06, z, 1.15, 2.0, windows, mats["glass"], mats["metal"])
    # East street corner return.
    for floor, z in enumerate((5.6, 8.6)):
        for index, y in enumerate((0.1, 3.0, 5.9, 8.8, 11.7, 14.6)):
            side_window(f"Hive_Window_DarkCorner_Side_F{floor + 1}_{index + 1}", 22.04, y, z, 1.05, 2.05, windows, mats["glass"], mats["metal"])


def add_screen_frames(groups, mats):
    frames = blockout.make_collection("HIVE_ScreenFrames", bpy.data.collections["HIVE_MASTER"])
    screen_mat = mats["screen"]
    screen_mat.diffuse_color = (0.42, 0.45, 0.46, 0.48)
    bsdf = screen_mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Alpha"].default_value = 0.48
    screen_mat.surface_render_method = "DITHERED"
    for panel_index in range(6):
        panel = bpy.data.objects.get(f"HIVE_ScreenEnvelope_{panel_index + 1:02d}")
        x = panel.location.x
        width = panel.dimensions.x
        y = -1.62
        for suffix, dx in (("L", -width / 2), ("R", width / 2)):
            blockout.box(f"HIVE_ScreenFrame_{panel_index + 1:02d}_{suffix}", (0.12, 0.19, 8.62), (x + dx, y, 8.15), mats["metal"], frames)
        for suffix, z in (("Top", 12.42), ("Mid", 8.15), ("Bottom", 3.88)):
            blockout.box(f"HIVE_ScreenFrame_{panel_index + 1:02d}_{suffix}", (width, 0.19, 0.12), (x, y, z), mats["metal"], frames)
        # Brackets make the screen's offset legible in oblique views.
        for suffix, dx in (("L", -width / 2 + 0.15), ("R", width / 2 - 0.15)):
            for level, z in enumerate((4.3, 8.15, 12.0)):
                blockout.box(f"HIVE_ScreenBracket_{panel_index + 1:02d}_{suffix}_{level + 1}", (0.10, 0.72, 0.10), (x + dx, -1.28, z), mats["metal"], frames)


def add_recessed_floor(groups, mats):
    windows = get_collection("HIVE_Windows")
    louvres = blockout.make_collection("HIVE_Louvres", bpy.data.collections["HIVE_MASTER"])
    delete_prefix("HIVE_RecessedFloor_LouvreEnvelope_")
    for index, x in enumerate((-12.8, -5.8, 1.2, 8.2, 15.2)):
        front_window(f"Hive_Window_RecessedFloor_{index + 1}", x, -0.16, 13.18, 1.35, 1.75, windows, mats["glass"], mats["metal"], False)
        # Six deep horizontal blades form each projecting shading bank.
        for blade in range(6):
            z = 13.08 + blade * 0.34
            blockout.box(f"HIVE_Louvre_{index + 1:02d}_{blade + 1:02d}", (2.1, 1.0, 0.095), (x, -0.64, z), mats["metal"], louvres)
        blockout.box(f"HIVE_Louvre_SideL_{index + 1:02d}", (0.10, 1.0, 2.0), (x - 1.0, -0.64, 13.85), mats["metal"], louvres)
        blockout.box(f"HIVE_Louvre_SideR_{index + 1:02d}", (0.10, 1.0, 2.0), (x + 1.0, -0.64, 13.85), mats["metal"], louvres)


def add_upper_windows(groups, mats):
    windows = get_collection("HIVE_Windows")
    # Tower A front: tall narrow pale-brick openings beside the major dark strip.
    for floor, z in enumerate((18.7, 22.1, 25.5, 28.9)):
        for index, x in enumerate((11.0, 12.9, 14.8, 16.2)):
            front_window(f"Hive_Window_UpperNarrow_A_F{floor + 1}_{index + 1}", x, -1.38, z, 0.68, 2.25, windows, mats["glass"], mats["metal"], False)
    # Tower B sits farther back, so its front plane is intentionally recessed.
    for floor, z in enumerate((18.2, 21.6, 25.0, 28.35)):
        for index, x in enumerate((-19.1, -17.2, -15.3)):
            front_window(f"Hive_Window_UpperNarrow_B_F{floor + 1}_{index + 1}", x, 0.48, z, 0.68, 2.20, windows, mats["glass"], mats["metal"], False)
    # Important upper corner rhythm on Tower A's east return.
    for floor, z in enumerate((18.7, 22.1, 25.5, 28.9)):
        for index, y in enumerate((0.1, 2.6, 5.1, 7.6, 10.1, 12.6)):
            side_window(f"Hive_Window_Corner_A_F{floor + 1}_{index + 1}", 16.84, y, z, 0.72, 2.25, windows, mats["glass"], mats["metal"])


def add_entrance_and_lobby(groups, mats):
    entrance = groups["entrance"]
    for name in ("ACE_FrontDoor_Left", "ACE_FrontDoor_Right", "ACE_EntranceGlass"):
        obj = bpy.data.objects.get(name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)
    # Recessed glazed wall and individually framed door leaves.
    blockout.box("ACE_EntranceGlass", (7.0, 0.065, 2.76), (-4.7, -0.76, 1.48), mats["glass"], entrance)
    framed_door("ACE_FrontDoor_Left", -5.47, -1.34, 1.34, 1.40, 2.58, entrance, mats["glass"], mats["metal"])
    framed_door("ACE_FrontDoor_Right", -3.93, -1.34, 1.34, 1.40, 2.58, entrance, mats["glass"], mats["metal"])
    blockout.box("ACE_EntranceThreshold", (3.12, 1.05, 0.09), (-4.7, -0.95, 0.045), mats["concrete"], entrance)
    blockout.box("ACE_Entrance_Reveal_Left", (0.32, 0.78, 2.95), (-8.18, -0.93, 1.48), mats["metal"], entrance)
    blockout.box("ACE_Entrance_Reveal_Right", (0.32, 0.78, 2.95), (-1.22, -0.93, 1.48), mats["metal"], entrance)

    lobby = blockout.make_collection("HIVE_InteriorLobby", bpy.data.collections["HIVE_MASTER"])
    blockout.box("HIVE_Lobby_Floor", (8.0, 8.5, 0.10), (-4.7, 3.55, 0.04), mats["concrete"], lobby)
    blockout.box("HIVE_Lobby_BackWall", (8.0, 0.20, 3.55), (-4.7, 7.75, 1.78), mats["white"], lobby)
    blockout.box("HIVE_Lobby_LeftWall", (0.20, 8.3, 3.55), (-8.60, 3.65, 1.78), mats["white"], lobby)
    blockout.box("HIVE_Lobby_RightWall", (0.20, 8.3, 3.55), (-0.80, 3.65, 1.78), mats["white"], lobby)
    blockout.box("HIVE_Lobby_ReceptionDesk", (3.4, 1.0, 1.18), (-2.95, 4.8, 0.59), mats["metal"], lobby)
    blockout.box("HIVE_Lobby_CorridorOpening", (2.0, 0.12, 2.65), (-6.7, 7.61, 1.33), mats["interior"], lobby)
    for index, x in enumerate((-7.8, -6.25, -4.7, -3.15, -1.6)):
        blockout.box(f"HIVE_Lobby_CeilingBaffle_{index + 1:02d}", (0.13, 8.0, 0.28), (x, 3.55, 3.25), mats["metal"], lobby)
    # Two simple timber-toned reveal volumes without textures or detailed joinery.
    timber = blockout.make_material("MAT_InteriorTimber_PLACEHOLDER", (0.38, 0.28, 0.17))
    for index, x in enumerate((-6.65, -3.6)):
        blockout.box(f"HIVE_Lobby_TimberOpening_{index + 1:02d}", (1.35, 0.18, 2.25), (x, 7.48, 1.50), timber, lobby)


def apply_transforms_and_validate():
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in meshes:
        obj.select_set(True)
    if meshes:
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    for obj in meshes:
        if not obj.data.validate(verbose=False, clean_customdata=False):
            obj.data.update()


def export_glb():
    """Export a draw-call-conscious runtime GLB while preserving hero nodes."""
    def semantic_bucket(name):
        if name.startswith("HIVE_Screen"):
            return "ScreenFacade"
        if name.startswith("HIVE_UpperTower_A") or "UpperNarrow_A" in name or "Corner_A" in name:
            return "UpperTower_A"
        if name.startswith("HIVE_UpperTower_B") or "UpperNarrow_B" in name:
            return "UpperTower_B"
        if name.startswith("HIVE_DarkBrick") or "DarkFacade" in name or "BehindScreen" in name:
            return "DarkBrickVolume"
        if name.startswith("HIVE_Ground") or name.startswith("HIVE_Concrete"):
            return "GroundFloor"
        if name.startswith("HIVE_Recessed") or "RecessedFloor" in name:
            return "RecessedFloor"
        if name.startswith("HIVE_Louvre"):
            return "Louvres"
        if name.startswith("HIVE_Lobby"):
            return "InteriorLobby"
        return "BuildingShell"

    runtime_collection = bpy.data.collections.new("HIVE_RUNTIME_EXPORT_TEMP")
    bpy.context.scene.collection.children.link(runtime_collection)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    grouped = {}
    originals = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH"
        and not obj.name.startswith("HIVE_Context_")
        and not obj.name.startswith("ACE_")
    ]
    for obj in originals:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = bpy.data.meshes.new_from_object(evaluated, depsgraph=depsgraph)
        duplicate = bpy.data.objects.new(f"RUNTIME_{obj.name}", mesh)
        duplicate.matrix_world = obj.matrix_world.copy()
        runtime_collection.objects.link(duplicate)
        material_name = mesh.materials[0].name if mesh.materials else "NoMaterial"
        grouped.setdefault((semantic_bucket(obj.name), material_name), []).append(duplicate)

    joined_runtime = []
    for (bucket, material_name), objects in grouped.items():
        bpy.ops.object.select_all(action="DESELECT")
        for obj in objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]
        bpy.ops.object.join()
        joined = bpy.context.view_layer.objects.active
        safe_material = "".join(char if char.isalnum() else "_" for char in material_name)
        joined.name = f"HIVE_{bucket}_{safe_material}"
        joined_runtime.append(joined)

    bpy.ops.object.select_all(action="DESELECT")
    selected = list(joined_runtime)
    for obj in joined_runtime:
        obj.select_set(True)
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and obj.name.startswith("ACE_"):
            obj.select_set(True)
            selected.append(obj)
        elif obj.type == "EMPTY" and obj.name in {"ACE_FrontEntrance", "ACE_EntranceTriggerAnchor"}:
            obj.select_set(True)
            selected.append(obj)
    bpy.context.view_layer.objects.active = next(obj for obj in selected if obj.type == "MESH")
    GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
    )
    for obj in list(runtime_collection.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(runtime_collection)


def render_final(cameras):
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    outputs = (
        "01-final-wide-street-three-quarter.png",
        "02-final-opposite-three-quarter.png",
        "03-final-front-lever-street.png",
        "04-final-ace-entrance-pedestrian.png",
    )
    for camera_obj, filename in zip(cameras, outputs):
        scene.camera = camera_obj
        scene.render.resolution_x = 1200
        scene.render.resolution_y = 800 if filename.startswith("04-") else 900
        scene.render.filepath = str(RENDER_DIR / filename)
        bpy.ops.render.render(write_still=True)


def main():
    cameras = blockout.build_blockout()
    master = bpy.data.collections["HIVE_MASTER"]
    groups = {
        "ground": get_collection("HIVE_GroundFloor"),
        "dark": get_collection("HIVE_DarkBrickVolume"),
        "tower_a": get_collection("HIVE_UpperTower_A"),
        "tower_b": get_collection("HIVE_UpperTower_B"),
        "recessed": get_collection("HIVE_RecessedFloor"),
        "screen": get_collection("HIVE_ScreenFacade"),
        "entrance": get_collection("HIVE_Entrance"),
    }
    mats = {
        "dark": get_material("MAT_DarkBrick_PLACEHOLDER"),
        "pale": get_material("MAT_PaleBrick_PLACEHOLDER"),
        "concrete": get_material("MAT_Concrete_PLACEHOLDER"),
        "screen": get_material("MAT_MetalScreen_PLACEHOLDER"),
        "metal": get_material("MAT_DarkMetal_PLACEHOLDER"),
        "glass": get_material("MAT_Glass_PLACEHOLDER"),
        "white": get_material("MAT_WhiteWall_PLACEHOLDER"),
        "interior": get_material("MAT_Interior_PLACEHOLDER"),
    }
    add_ground_floor(groups, mats)
    add_dark_facade_windows(groups, mats)
    add_screen_frames(groups, mats)
    add_recessed_floor(groups, mats)
    add_upper_windows(groups, mats)
    add_entrance_and_lobby(groups, mats)
    apply_transforms_and_validate()
    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.camera = cameras[0]
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), check_existing=False)
    export_glb()
    render_final(cameras)
    bpy.context.scene.camera = cameras[0]
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), check_existing=False)
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and not obj.name.startswith("HIVE_Context_")]
    tris = sum(sum(max(0, len(poly.vertices) - 2) for poly in obj.data.polygons) for obj in meshes)
    print(f"Detailed geometry objects: {len(meshes)}")
    print(f"Detailed geometry triangles: {tris}")
    print(f"Saved blend: {BLEND_PATH}")
    print(f"Exported GLB: {GLB_PATH}")
    print(f"Final clay renders: {RENDER_DIR}")


if __name__ == "__main__":
    main()
