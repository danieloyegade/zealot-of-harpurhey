import { MathUtils, Vector3 } from 'three';

const SEPARATION_EPSILON = 0.000001;

export interface CollisionObstacle {
  readonly name: string;
  readonly minX: number;
  readonly maxX: number;
  readonly minZ: number;
  readonly maxZ: number;
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

function separateCircleFromObstacle(
  position: Vector3,
  radius: number,
  obstacle: CollisionObstacle,
): boolean {
  const closestX = MathUtils.clamp(position.x, obstacle.minX, obstacle.maxX);
  const closestZ = MathUtils.clamp(position.z, obstacle.minZ, obstacle.maxZ);
  const offsetX = position.x - closestX;
  const offsetZ = position.z - closestZ;
  const distanceSquared = offsetX * offsetX + offsetZ * offsetZ;

  if (distanceSquared >= radius * radius) {
    return false;
  }

  const centreIsInside = position.x >= obstacle.minX
    && position.x <= obstacle.maxX
    && position.z >= obstacle.minZ
    && position.z <= obstacle.maxZ;

  if (centreIsInside) {
    const candidates = [
      { axis: 'x', displacement: obstacle.minX - radius - SEPARATION_EPSILON - position.x },
      { axis: 'x', displacement: obstacle.maxX + radius + SEPARATION_EPSILON - position.x },
      { axis: 'z', displacement: obstacle.minZ - radius - SEPARATION_EPSILON - position.z },
      { axis: 'z', displacement: obstacle.maxZ + radius + SEPARATION_EPSILON - position.z },
    ] as const;
    const nearestExit = candidates.reduce((nearest, candidate) => (
      Math.abs(candidate.displacement) < Math.abs(nearest.displacement)
        ? candidate
        : nearest
    ));
    position[nearestExit.axis] += nearestExit.displacement;
    return true;
  }

  const distance = Math.sqrt(distanceSquared);
  const separation = (radius - distance + SEPARATION_EPSILON) / distance;
  position.x += offsetX * separation;
  position.z += offsetZ * separation;
  return true;
}

export function resolveCircleOverlaps(
  position: Vector3,
  radius: number,
  world: CollisionWorld,
): void {
  const minX = world.bounds.minX + radius;
  const maxX = world.bounds.maxX - radius;
  const minZ = world.bounds.minZ + radius;
  const maxZ = world.bounds.maxZ - radius;
  const maximumPasses = Math.max(1, world.obstacles.length * 2);

  position.x = MathUtils.clamp(position.x, minX, maxX);
  position.z = MathUtils.clamp(position.z, minZ, maxZ);

  for (let pass = 0; pass < maximumPasses; pass += 1) {
    let foundOverlap = false;
    for (const obstacle of world.obstacles) {
      if (separateCircleFromObstacle(position, radius, obstacle)) {
        position.x = MathUtils.clamp(position.x, minX, maxX);
        position.z = MathUtils.clamp(position.z, minZ, maxZ);
        foundOverlap = true;
      }
    }
    if (!foundOverlap) {
      return;
    }
  }
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

  // A level edit or teleport can place the player inside an obstacle. Recover
  // before testing incremental movement so the player cannot become trapped.
  resolveCircleOverlaps(position, radius, world);

  const nextX = MathUtils.clamp(position.x + movement.x, minX, maxX);
  if (!intersectsObstacle(nextX, position.z, radius, world.obstacles)) {
    position.x = nextX;
  }

  const nextZ = MathUtils.clamp(position.z + movement.z, minZ, maxZ);
  if (!intersectsObstacle(position.x, nextZ, radius, world.obstacles)) {
    position.z = nextZ;
  }
}
