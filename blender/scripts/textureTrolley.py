"""Bake restrained trolley PBR maps without changing the approved geometry.

Run in Blender with -- --stage bake|integrate|renders (default: bake).
Reuses surfaceWeathering for the atlas, world-space buffers and glTF material.
"""
import hashlib
import json
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import createBusShelter as geo
import createBusShelterTextured as shelter
from surfaceWeathering import (F, Texels, unwrap_atlas, bake_buffers, noise3,
                               fbm3, smoothstep, srgb_encode, save_rgba,
                               load_image, build_pbr_material)

SOURCE = geo.SOURCE_DIR / "preston-shopping-trolley.blend"
TEXTURES = geo.PROJECT_ROOT / "blender/source/textures/bus-shelter/trolley"
RENDERS = geo.PROJECT_ROOT / "renders/trolley-materials"
MATERIALS = ("MAT_Trolley_GalvanisedSteel", "MAT_Trolley_WornBracket", "MAT_Trolley_Tyre")


def meshes(root=None):
    root = root or bpy.data.objects['PRESTON_SHOPPING_TROLLEY']
    return sorted((o for o in geo.descendants(root)
                   if o.type == 'MESH'), key=lambda o: o.name)


def geometry_signature(objects):
    result = {}
    for obj in objects:
        coords = np.empty(len(obj.data.vertices)*3, F)
        obj.data.vertices.foreach_get('co', coords)
        loops = np.empty(len(obj.data.loops), np.int32)
        obj.data.loops.foreach_get('vertex_index', loops)
        result[obj.name] = hashlib.sha256(coords.tobytes()+loops.tobytes()).hexdigest()
    return result


def maps():
    base = load_image(TEXTURES / 'trolley-basecolor.png')
    orm = load_image(TEXTURES / 'trolley-orm.png', non_color=True)
    return base, orm


def apply_materials(base, orm):
    for name in MATERIALS:
        mat = bpy.data.materials.get(name)
        if mat:
            build_pbr_material(mat, base, orm)


def bake():
    TEXTURES.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    objects = meshes()
    before = geometry_signature(objects)
    unwrap_atlas(objects, margin=0.002)
    # Bake-only copies grouped by surface: do not rebuild the Cycles scene
    # once per fine wire. The editable/exported meshes remain separate.
    grouped = []
    for material_name, label in zip(MATERIALS, ('Metal', 'Bracket', 'Tyre')):
        copies = []
        for obj in objects:
            if obj.data.materials[0].name != material_name:
                continue
            clone = obj.copy()
            clone.data = obj.data.copy()
            clone.parent = None
            clone.matrix_world = obj.matrix_world.copy()
            bpy.context.collection.objects.link(clone)
            copies.append(clone)
        bpy.ops.object.select_all(action='DESELECT')
        for clone in copies:
            clone.select_set(True)
        bpy.context.view_layer.objects.active = copies[0]
        bpy.ops.object.join()
        merged = bpy.context.object
        merged.name = 'TEMP_TROLLEY_' + label
        grouped.append(merged)
    for obj in objects:
        obj.hide_render = True
    buffers = bake_buffers(grouped, 1024, 1024, ao_distance=0.04,
                           convex_distance=0.003, samples=2, margin=2, true_normal_ao=True)
    for obj in grouped:
        bpy.data.objects.remove(obj, do_unlink=True)
    for obj in objects:
        obj.hide_render = False
    tex = Texels(*buffers)
    p, n = tex.P, tex.N
    coarse = fbm3(p*22, octaves=3, seed=91)
    zinc = noise3(p*270, seed=19)
    grain = noise3(p*840, seed=54)
    lower = 1-smoothstep(0.07, 0.34, p[:,2])
    contact = (1-tex.ao)*0.20
    deposits = np.clip(lower*(0.08+0.18*coarse)+contact, 0, 0.35)
    bracket = tex.name_mask('_Bracket')
    rubber = tex.name_mask('_Tyre')
    handle = ((p[:,2] > 1.035) & (p[:,1] < -0.39))
    base = np.tile(np.array((0.47,0.49,0.48), F), (tex.M,1))
    base *= (0.96+0.08*zinc+0.035*(coarse-0.5))[:,None]
    rough = 0.34+0.10*coarse+0.05*(zinc-0.5)+0.015*(grain-0.5)
    metal = np.full(tex.M, 0.92, F)
    # Handling polishes the grip very slightly; no invented chips or heavy rust.
    rough[handle] -= 0.06
    base[bracket] = np.array((0.095,0.10,0.102),F)*(0.92+0.16*coarse[bracket,None])
    rough[bracket] = 0.48+0.12*coarse[bracket]
    metal[bracket] = 0.68
    base[rubber] = np.array((0.016,0.018,0.019),F)*(0.85+0.3*grain[rubber,None])
    rough[rubber] = 0.80+0.10*coarse[rubber]
    metal[rubber] = 0
    dust = np.array((0.075,0.067,0.050),F)
    base = base*(1-deposits[:,None])+dust*deposits[:,None]
    rough = np.clip(rough+deposits*0.28,0,1)
    metal *= 1-deposits
    # All geometry stays opaque; no displacement/normal noise on fine wires.
    rgba = tex.grid(np.column_stack((srgb_encode(base), np.ones(tex.M,F))), fill=(0.70,0.72,0.71,1))
    orm = tex.grid(np.column_stack((0.85+0.15*tex.ao,rough,metal)), fill=(1,0.45,0.9))
    save_rgba(TEXTURES/'trolley-basecolor.png', rgba)
    save_rgba(TEXTURES/'trolley-orm.png', orm)
    apply_materials(*maps())
    assert before == geometry_signature(objects), 'Approved geometry changed during UV/bake'
    uv = {}
    for obj in objects:
        a = np.empty(len(obj.data.loops)*2,F)
        obj.data.uv_layers.active.data.foreach_get('uv',a)
        uv[obj.name] = a.tolist()
    (TEXTURES/'uv-layout.json').write_text(json.dumps(uv,separators=(',',':')))
    (TEXTURES/'validation.json').write_text(json.dumps({
        'geometry_sha256': before, 'mesh_count':len(objects), 'atlas_size':[1024,1024],
        'valid_texels':tex.M, 'roughness_range':[float(rough.min()),float(rough.max())],
        'source':'Deterministic world-space weathering; existing surfaceWeathering CPU bake',
        'geometry_unchanged':True, 'maps':['trolley-basecolor.png','trolley-orm.png']
    },indent=2)+'\n')
    for image in bpy.data.images:
        if image.filepath:
            image.filepath=bpy.path.relpath(image.filepath,start=str(SOURCE.parent))
    geo.save(SOURCE)
    print('Trolley maps baked; approved mesh signatures unchanged.',flush=True)


def apply_saved(root=None):
    """Restore baked UVs/maps when the shared geometry builder is rerun."""
    if not (TEXTURES/'validation.json').exists():
        return
    uv = json.loads((TEXTURES/'uv-layout.json').read_text())
    expected = json.loads((TEXTURES/'validation.json').read_text())['geometry_sha256']
    objects = meshes(root)
    if geometry_signature(objects) != expected:
        raise RuntimeError('Trolley geometry changed: rebuild its material atlas before exporting')
    for obj in objects:
        layer = obj.data.uv_layers.active or obj.data.uv_layers.new(name='UVMap')
        layer.data.foreach_set('uv', uv[obj.name])
    apply_materials(*maps())


def integrate():
    uv = json.loads((TEXTURES/'uv-layout.json').read_text())
    expected = json.loads((TEXTURES/'validation.json').read_text())['geometry_sha256']
    # The structural blockout remains deliberately untextured. Update all
    # detailed sources, including the source used by the actual game exporter.
    for source in (SOURCE,geo.DETAIL_BLEND,geo.REFERENCE_BLEND,shelter.TEXTURED_BLEND):
        bpy.ops.wm.open_mainfile(filepath=str(source))
        objects=meshes()
        assert geometry_signature(objects)==expected, f'Geometry drift: {source}'
        for obj in objects:
            layer=obj.data.uv_layers.active or obj.data.uv_layers.new(name='UVMap')
            layer.data.foreach_set('uv',uv[obj.name])
        apply_materials(*maps())
        for image in bpy.data.images:
            if image.filepath:
                image.filepath=bpy.path.relpath(image.filepath,start=str(source.parent))
        geo.save(source)
        trolley=bpy.data.objects['PRESTON_SHOPPING_TROLLEY']
        if source==SOURCE:
            shelter.export_glb(geo.TROLLEY_GLB,trolley)
        elif source==geo.REFERENCE_BLEND:
            shelter.export_glb(geo.REFERENCE_GLB,bpy.data.objects['PRESTON_BUS_SHELTER'],trolley)
        elif source==shelter.TEXTURED_BLEND:
            shelter.export_glb(shelter.REFERENCE_GLB,bpy.data.objects['PRESTON_BUS_SHELTER'],trolley)
    print('Trolley texture maps integrated; detailed source geometry preserved.',flush=True)


def renders():
    RENDERS.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    geo.configure_scene()
    scene=bpy.context.scene
    scene.render.resolution_x=1200
    scene.render.resolution_y=1000
    scene.view_settings.view_transform='AgX'
    scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(0.35,0.35,0.35,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=0.65
    geo.add_review_stage()
    cam=scene.camera
    target=Vector((0,0.0,0.53))
    cam.location=target+Vector((4,-1.7,1.0))
    cam.data.type='ORTHO'
    cam.data.ortho_scale=1.6
    geo.point_at(cam,target)
    scene.render.filepath=str(RENDERS/'01-trolley-materials.png')
    bpy.ops.render.render(write_still=True)
    cam.data.ortho_scale=0.60
    target=Vector((0.2,-0.04,0.67))
    cam.location=target+Vector((4,-1.7,0.8))
    geo.point_at(cam,target)
    scene.render.filepath=str(RENDERS/'02-steel-closeup.png')
    bpy.ops.render.render(write_still=True)


if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    stage=args[args.index('--stage')+1] if '--stage' in args else 'bake'
    {'bake':bake,'integrate':integrate,'renders':renders}[stage]()
