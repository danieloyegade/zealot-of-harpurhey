import {
  BufferGeometry,
  Float32BufferAttribute,
  Group,
  LineBasicMaterial,
  LineSegments,
} from 'three';
import type { CollisionObstacle } from './collision';

const OUTLINE_HEIGHT = 0.08;
const CIRCLE_SEGMENTS = 16;

type Point = readonly [number, number];

function obstacleOutline(obstacle: CollisionObstacle): Point[] {
  if (obstacle.shape === 'circle') {
    return Array.from({ length: CIRCLE_SEGMENTS }, (_, index) => {
      const angle = (index / CIRCLE_SEGMENTS) * Math.PI * 2;
      return [
        obstacle.x + Math.cos(angle) * obstacle.radius,
        obstacle.z + Math.sin(angle) * obstacle.radius,
      ] as const;
    });
  }
  if (obstacle.shape === 'oriented-box') {
    const cos = Math.cos(obstacle.rotationY);
    const sin = Math.sin(obstacle.rotationY);
    return [
      [-obstacle.halfWidth, -obstacle.halfDepth],
      [obstacle.halfWidth, -obstacle.halfDepth],
      [obstacle.halfWidth, obstacle.halfDepth],
      [-obstacle.halfWidth, obstacle.halfDepth],
    ].map(([localX, localZ]) => [
      obstacle.x + localX * cos + localZ * sin,
      obstacle.z - localX * sin + localZ * cos,
    ] as const);
  }
  return [
    [obstacle.minX, obstacle.minZ],
    [obstacle.maxX, obstacle.minZ],
    [obstacle.maxX, obstacle.maxZ],
    [obstacle.minX, obstacle.maxZ],
  ];
}

function createOutlines(
  name: string,
  obstacles: readonly CollisionObstacle[],
  color: number,
): LineSegments {
  const vertices: number[] = [];
  for (const obstacle of obstacles) {
    const outline = obstacleOutline(obstacle);
    outline.forEach(([x, z], index) => {
      const [nextX, nextZ] = outline[(index + 1) % outline.length];
      vertices.push(x, OUTLINE_HEIGHT, z, nextX, OUTLINE_HEIGHT, nextZ);
    });
  }
  const geometry = new BufferGeometry();
  geometry.setAttribute('position', new Float32BufferAttribute(vertices, 3));
  const lines = new LineSegments(
    geometry,
    new LineBasicMaterial({ color, depthTest: false, transparent: true }),
  );
  lines.name = name;
  lines.renderOrder = 1000;
  lines.frustumCulled = false;
  return lines;
}

/**
 * Development overlay tracing every collision footprint on the ground, drawn
 * through geometry so misaligned footprints are visible. Magenta outlines also
 * stop the camera; cyan ones only stop the player.
 */
export function createCollisionDebugOutlines(
  obstacles: readonly CollisionObstacle[],
): Group {
  const group = new Group();
  group.name = 'Development collision outlines';
  group.userData.developmentOverlay = true;
  group.add(
    createOutlines(
      'Camera-blocking collision outlines',
      obstacles.filter((obstacle) => obstacle.blocksCamera !== false),
      0xff3df2,
    ),
    createOutlines(
      'Player-only collision outlines',
      obstacles.filter((obstacle) => obstacle.blocksCamera === false),
      0x3de8ff,
    ),
  );
  return group;
}
