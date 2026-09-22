"""Review the shipped Cass Art GLB, including its exported UVs."""
import sys
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'blender/scripts'))
import createCassArt as cass

cass.clear_scene()
bpy.ops.import_scene.gltf(filepath=str(cass.GLB_PATH))
helpers, camera = cass.add_render_helpers()
cass.render_views(camera, ROOT / 'renders/cass-art-textures')
scene = bpy.context.scene
camera.location = (-1.55, -16, 3.58)
cass.point_at(camera, (-1.55, 0, 3.58))
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 11.1
scene.render.resolution_x = 1800
scene.render.resolution_y = 400
scene.render.filepath = str(ROOT / 'renders/cass-art-textures/lettering-closeup.png')
bpy.ops.render.render(write_still=True)
