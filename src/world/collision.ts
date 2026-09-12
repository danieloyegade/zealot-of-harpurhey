import { MathUtils, Vector3 } from 'three';

export interface CollisionObstacle {
  readonly name: string;
  readonly minX: number;
  readonly maxX: number;
  readonly minZ: number;
  readonly maxZ: number;
  /**
   * Height in metres above the ground plane. Player movement is purely
   * horizontal and ignores this value; it exists so the camera can fly over
   * low obstacles such as bus shelters instead of treating every footprint as
   * an infinitely tall column. Omit it for buildings, which are always taller
   * than the camera can climb.
   */
  readonly height?: number;
}

export interface PlayableBounds {
  readonly minX: number;
  readonly maxX: number;
  readonly minZ: number;
  readonly maxZ: number;
}

export interface CollisionWorld {
  readonly bounds: PlayableBounds;
  readonly obstacles: readonly CollisionObstacle[];
}

function intersectsObstacle(
  x: number,
  z: number,
  radius: number,
  obstacles: readonly CollisionObstacle[],
): boolean {
  return obstacles.some((obstacle) => {
    const closestX = MathUtils.clamp(x, obstacle.minX, obstacle.maxX);
    const closestZ = MathUtils.clamp(z, obstacle.minZ, obstacle.maxZ);
    const offsetX = x - closestX;
    const offsetZ = z - closestZ;

    return offsetX * offsetX + offsetZ * offsetZ < radius * radius;
  });
}

export function moveCircleWithCollisions(
  position: Vector3,
  movement: Vector3,
  radius: number,
  world: CollisionWorld,
): void {
  const minX = world.bounds.minX + radius;
  const maxX = world.bounds.maxX - radius;
  const minZ = world.bounds.minZ + radius;
  const maxZ = world.bounds.maxZ - radius;

  const nextX = MathUtils.clamp(position.x + movement.x, minX, maxX);
  if (!intersectsObstacle(nextX, position.z, radius, world.obstacles)) {
    position.x = nextX;
  }

  const nextZ = MathUtils.clamp(position.z + movement.z, minZ, maxZ);
  if (!intersectsObstacle(position.x, nextZ, radius, world.obstacles)) {
    position.z = nextZ;
  }
}

const RAY_PARALLEL_EPSILON = 1e-6;

/**
 * Slab-method ray/box entry distance. Returns null when the ray misses, and
 * also when the origin already sits inside the box: a camera probe starting
 * inside geometry should ignore that geometry rather than collapse onto the
 * player.
 */
function rayBoxEntryDistance(
  origin: Vector3,
  direction: Vector3,
  maximumDistance: number,
  minX: number,
  maxX: number,
  minY: number,
  maxY: number,
  minZ: number,
  maxZ: number,
): number | null {
  if (
    origin.x > minX && origin.x < maxX
    && origin.y > minY && origin.y < maxY
    && origin.z > minZ && origin.z < maxZ
  ) {
    return null;
  }

  let entryDistance = 0;
  let exitDistance = maximumDistance;

  const axes: readonly [number, number, number, number][] = [
    [origin.x, direction.x, minX, maxX],
    [origin.y, direction.y, minY, maxY],
    [origin.z, direction.z, minZ, maxZ],
  ];

  for (const [componentOrigin, componentDirection, minimum, maximum] of axes) {
    if (Math.abs(componentDirection) < RAY_PARALLEL_EPSILON) {
      if (componentOrigin < minimum || componentOrigin > maximum) {
        return null;
      }
      continue;
    }

    const firstCrossing = (minimum - componentOrigin) / componentDirection;
    const secondCrossing = (maximum - componentOrigin) / componentDirection;
    const nearCrossing = Math.min(firstCrossing, secondCrossing);
    const farCrossing = Math.max(firstCrossing, secondCrossing);

    entryDistance = Math.max(entryDistance, nearCrossing);
    exitDistance = Math.min(exitDistance, farCrossing);

    if (entryDistance > exitDistance) {
      return null;
    }
  }

  return entryDistance;
}

/**
 * Distance the camera may travel from `origin` along `direction` before it
 * would enter world geometry. Obstacles are padded by `padding` so the near
 * plane never grazes a wall. Returns `maximumDistance` when nothing blocks.
 */
export function castAgainstObstacles(
  origin: Vector3,
  direction: Vector3,
  maximumDistance: number,
  padding: number,
  world: CollisionWorld,
): number {
  let nearest = maximumDistance;

  for (const obstacle of world.obstacles) {
    const height = obstacle.height ?? Number.POSITIVE_INFINITY;
    const hit = rayBoxEntryDistance(
      origin,
      direction,
      nearest,
      obstacle.minX - padding,
      obstacle.maxX + padding,
      -padding,
      height + padding,
      obstacle.minZ - padding,
      obstacle.maxZ + padding,
    );

    if (hit !== null && hit < nearest) {
      nearest = hit;
    }
  }

  return nearest;
}
