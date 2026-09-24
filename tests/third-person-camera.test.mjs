import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { stripTypeScriptTypes } from 'node:module';
import { PerspectiveCamera, Vector2, Vector3 } from 'three';

// The camera uses constructor parameter properties, beyond Node's strip-only mode.
const source = await readFile(new URL('../src/camera/ThirdPersonCamera.ts', import.meta.url), 'utf8');
const compiled = stripTypeScriptTypes(source, { mode: 'transform' })
  .replace("from 'three'", `from '${import.meta.resolve('three')}'`)
  .replace("from '../world/collision'", `from '${new URL('../src/world/collision.ts', import.meta.url)}'`);
const { ThirdPersonCamera } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);

const wall = { name: 'shop wall', minX: -10, maxX: 10, minZ: 0, maxZ: 5, height: 10 };
const world = { bounds: { minX: -20, maxX: 20, minZ: -20, maxZ: 20 }, obstacles: [wall] };
const input = { orbitDelta: new Vector2(), consumeRecenter: () => false };

test('a wall closer than 0.6 m remains a hard camera constraint through an orbit', () => {
  const camera = new PerspectiveCamera(56, 16 / 9, 0.1, 120);
  const controller = new ThirdPersonCamera(camera, 1.6, world);
  const position = new Vector3(0, 0, -0.38);
  controller.snapTo(position);
  assert.ok(camera.position.z <= -0.3 + 1e-6, `lens crossed wall clearance: ${camera.position.z}`);
  const target = { position, facingDirection: new Vector3(0, 0, -1), movementState: 'Idle' };
  for (let i = 0; i < 720; i++) {
    input.orbitDelta.set(5, 0);
    controller.update(1 / 60, input, target);
    assert.ok(camera.position.z <= -0.3 + 1e-6, `lens crossed wall on frame ${i}: ${camera.position.z}`);
    assert.ok(camera.quaternion.toArray().every(Number.isFinite));
  }
  input.orbitDelta.set(0, 0);
});

test('a fully collapsed boom keeps a finite view pointed along the orbit', () => {
  const camera = new PerspectiveCamera();
  const controller = new ThirdPersonCamera(camera, 1.6, world);
  controller.setOrbit(0, 0);
  controller.snapTo(new Vector3(0, 0, -0.300000001));
  assert.ok(camera.position.z <= -0.3 + 1e-6);
  assert.ok(camera.quaternion.toArray().every(Number.isFinite));
  assert.ok(camera.getWorldDirection(new Vector3()).z < -0.99);
});
