import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';

async function glbJson(name) {
  const bytes = await readFile(new URL(`../public/assets/models/sterling-bike/${name}`, import.meta.url));
  assert.equal(bytes.toString('ascii', 0, 4), 'glTF');
  assert.equal(bytes.toString('ascii', 16, 20), 'JSON');
  return JSON.parse(bytes.toString('utf8', 20, 20 + bytes.readUInt32LE(12)));
}

test('Sterling runtime GLBs carry the authored paint maps and UVs', async () => {
  for (const [name, keyMaterials, keyNodes] of [
    ['sterling-bike-blockout.glb',
      ['MAT_SB_Frame', 'MAT_SB_RearPanel', 'MAT_SB_Basket', 'MAT_SB_Rubber'],
      ['SB_FrontWheel', 'SB_RearWheel', 'SB_SteeringRoot', 'SB_CrankRoot', 'SB_Basket', 'SB_DockAnchor']],
    ['sterling-dock-blockout.glb',
      ['MAT_SD_Dock', 'MAT_SD_DockYellow'],
      ['SD_BikeDockAnchor', 'SD_InteractionAnchor']],
  ]) {
    const gltf = await glbJson(name);
    assert.ok(gltf.images?.length > 0, `${name} has no embedded texture images`);
    const nodes = new Set(gltf.nodes.map(({ name: nodeName }) => nodeName));
    for (const nodeName of keyNodes) {
      assert.ok(nodes.has(nodeName), `${name} lost articulated node ${nodeName}`);
    }
    for (const materialName of keyMaterials) {
      const material = gltf.materials.find(({ name: candidate }) => candidate === materialName);
      assert.ok(material?.pbrMetallicRoughness?.baseColorTexture,
        `${name}: ${materialName} lost its baked color map`);
    }
    for (const mesh of gltf.meshes) {
      for (const primitive of mesh.primitives) {
        const material = gltf.materials[primitive.material];
        if (material?.pbrMetallicRoughness?.baseColorTexture) {
          assert.ok('TEXCOORD_0' in primitive.attributes,
            `${name}: ${material.name} has a color map but no UVs`);
        }
      }
    }
  }
});
