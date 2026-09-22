import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

test('Cass Art consolidation preserves usable UVs and raised lettering', async () => {
  const bytes = await readFile(new URL('../public/assets/models/cass_art.glb', import.meta.url));
  const jsonLength = bytes.readUInt32LE(12);
  const gltf = JSON.parse(bytes.toString('utf8', 20, 20 + jsonLength));
  const binaryStart = 28 + jsonLength;
  let textured = 0;
  for (const mesh of gltf.meshes) {
    for (const primitive of mesh.primitives) {
      const material = gltf.materials[primitive.material];
      if (!material.pbrMetallicRoughness?.baseColorTexture) continue;
      textured++;
      const accessor = gltf.accessors[primitive.attributes.TEXCOORD_0];
      assert.ok(accessor, `${material.name} lost its UVs during consolidation`);
      assert.equal(accessor.componentType, 5126);
      const view = gltf.bufferViews[accessor.bufferView];
      const start = binaryStart + (view.byteOffset ?? 0) + (accessor.byteOffset ?? 0);
      const coordinates = new Set();
      for (let i = 0; i < accessor.count; i++) {
        const offset = start + i * (view.byteStride ?? 8);
        coordinates.add(`${bytes.readFloatLE(offset)},${bytes.readFloatLE(offset + 4)}`);
      }
      assert.ok(coordinates.size >= 4, `${material.name} has collapsed UVs`);
    }
  }
  assert.ok(textured >= 8, 'Missing Cass Art facade/display maps');
  const slogan = gltf.materials.find(m => m.name === 'MAT_CASS_Slogan');
  assert.ok(slogan);
  assert.equal(slogan.alphaMode ?? 'OPAQUE', 'OPAQUE', 'Raised letters must write depth');
  for (const name of ['CASS_EntranceTriggerAnchor', 'CASS_StaffAnchor', 'CASS_CustomerInteractionAnchor']) {
    assert.ok(gltf.nodes.some(n => n.name.startsWith(name)), `Lost ${name}`);
  }
  assert.ok(bytes.length < 5_000_000, 'Cass Art exceeds its 5 MB runtime budget');
});
