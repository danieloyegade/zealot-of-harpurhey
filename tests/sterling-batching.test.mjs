import assert from 'node:assert/strict';
import test from 'node:test';
import { BoxGeometry, Group, Mesh, MeshPhysicalMaterial } from 'three';
import { mergeSterlingStaticParts } from '../src/world/mergeSterlingStaticParts.ts';

test('Sterling batching preserves UV/tangent frames and articulated ownership', () => {
  const model = new Group();
  const steering = new Group();
  steering.name = 'SB_SteeringRoot';
  steering.position.set(1, 2, 3);
  model.add(steering);
  const material = new MeshPhysicalMaterial({ anisotropy: 0.35 });
  for (let i = 0; i < 2; i++) {
    const geometry = new BoxGeometry();
    geometry.computeTangents();
    const mesh = new Mesh(geometry, material);
    mesh.position.x = i * 2;
    // A reflection must swap UVs/tangents along with the triangle's vertices.
    if (i === 1) mesh.scale.x = -1;
    steering.add(mesh);
  }
  const expectedUVs = steering.children.map(mesh => {
    const geometry = mesh.geometry.toNonIndexed();
    return [...geometry.getAttribute('uv').array];
  });
  // Reflected triangles reverse vertices 1 and 2, including their UVs.
  for (let i = 0; i < expectedUVs[1].length; i += 6) {
    [expectedUVs[1][i+2], expectedUVs[1][i+4]] = [expectedUVs[1][i+4], expectedUVs[1][i+2]];
    [expectedUVs[1][i+3], expectedUVs[1][i+5]] = [expectedUVs[1][i+5], expectedUVs[1][i+3]];
  }
  const missingUV = new BoxGeometry();
  missingUV.deleteAttribute('uv');
  model.add(new Mesh(missingUV, material));

  mergeSterlingStaticParts(model, new Set(['SB_SteeringRoot']));
  assert.equal(steering.children.length, 1);
  const merged = steering.children[0];
  assert.equal(merged.material, material);
  assert.equal(merged.material.anisotropy, 0.35);
  const tangents = merged.geometry.getAttribute('tangent');
  assert.ok(tangents);
  assert.equal(tangents.getW(0), -tangents.getW(tangents.count / 2));
  assert.deepEqual([...merged.geometry.getAttribute('uv').array], expectedUVs.flat());
  assert.deepEqual(steering.position.toArray(), [1, 2, 3]);
  const unwrappedPart = model.children.find(child => child.isMesh);
  assert.equal(unwrappedPart.material.anisotropy, 0);
  assert.notEqual(unwrappedPart.material, material);
  assert.equal(material.anisotropy, 0.35, 'fallback must not mutate shared valid materials');
});
