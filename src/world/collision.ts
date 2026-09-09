import { MathUtils, Vector3 } from 'three';

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
