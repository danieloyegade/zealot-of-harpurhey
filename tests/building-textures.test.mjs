import assert from 'node:assert/strict';
import { readFile, stat } from 'node:fs/promises';
import { resolve } from 'node:path';
import test from 'node:test';

const root = resolve(new URL('..', import.meta.url).pathname);
const contract = JSON.parse(
  await readFile(resolve(root, 'config/building-textures.json'), 'utf8'),
);

async function readGlbJson(path) {
  const bytes = await readFile(path);
  assert.equal(bytes.toString('latin1', 0, 4), 'glTF', `${path} is not a GLB`);
  assert.equal(bytes.readUInt32LE(16), 0x4e4f534a, `${path} has no JSON chunk`);
  return JSON.parse(bytes.toString('utf8', 20, 20 + bytes.readUInt32LE(12)));
}

for (const entry of contract.buildings) {
  test(`${entry.glb} carries its authored surface materials`, async () => {
    const path = resolve(root, 'public', entry.glb);
    const gltf = await readGlbJson(path);
    const materials = gltf.materials ?? [];

    const surfaces = materials
      .map((material, index) => ({ material, index }))
      .filter(({ material }) => (material.name ?? '').startsWith(entry.surfacePrefix));
    assert.equal(surfaces.length, entry.expectedSurfaces, 'surface material count');
    for (const { material } of surfaces) {
      assert.ok(material.pbrMetallicRoughness?.baseColorTexture, `${material.name}: no base colour map`);
      assert.ok(material.pbrMetallicRoughness?.metallicRoughnessTexture, `${material.name}: no ORM map`);
      assert.ok(material.normalTexture, `${material.name}: no normal map`);
    }

    const surfaceIndices = new Set(surfaces.map(({ index }) => index));
    const unmapped = (gltf.meshes ?? [])
      .flatMap((mesh) => mesh.primitives)
      .filter((primitive) => surfaceIndices.has(primitive.material))
      .filter((primitive) => !('TEXCOORD_0' in primitive.attributes));
    assert.equal(unmapped.length, 0, 'textured primitives without TEXCOORD_0');

    const allowed = new Set(entry.untexturedAllowed);
    const unaccounted = materials
      .map((material) => material.name ?? '')
      .filter((name) => !name.startsWith(entry.surfacePrefix) && !allowed.has(name));
    assert.deepEqual(unaccounted, [], 'materials neither textured nor allowlisted');

    const { size } = await stat(path);
    assert.ok(size <= entry.maxBytes, `${size} bytes exceeds budget ${entry.maxBytes}`);
  });
}
