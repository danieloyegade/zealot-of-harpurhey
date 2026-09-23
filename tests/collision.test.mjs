import assert from 'node:assert/strict';
import test from 'node:test';
import { Vector3 } from 'three';
import {
  castSphereThroughObstacles,
  moveCircleWithCollisions,
} from '../src/world/collision.ts';

const world = {
  bounds: { minX: -20, maxX: 20, minZ: -20, maxZ: 20 },
  obstacles: [
    {
      name: 'yawed bench',
      shape: 'oriented-box',
      x: 0,
      z: 0,
      halfWidth: 2,
      halfDepth: 0.25,
      rotationY: Math.PI / 4,
      height: 1,
    },
  ],
};

test('cached collision bounds preserve movement against oriented boxes', () => {
  const position = new Vector3(-3, 0, 0);
  moveCircleWithCollisions(position, new Vector3(6, 0, 0), 0.38, world);

  // The mover reaches and slides around the yawed footprint, but never tunnels
  // straight through to the requested endpoint.
  assert.ok(position.x < 3);
  assert.ok(Math.abs(position.z) > 0.1);
});

test('camera casts still hit oriented boxes after broad-phase rejection', () => {
  const fraction = castSphereThroughObstacles(
    new Vector3(-3, 0.8, 0),
    new Vector3(3, 0.8, 0),
    0.3,
    world,
  );

  assert.ok(fraction > 0 && fraction < 1);
});
