import { MathUtils, Vector3 } from 'three';

export interface CollisionObstacle {
  readonly name: string;
  readonly minX: number;
  readonly maxX: number;
  readonly minZ: number;
  readonly maxZ: number;
  readonly height: number;
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

// Pushes the circle clear of any obstacle it currently overlaps, along the
// shortest exit. Doubles as the recovery path: a player who somehow starts
// inside geometry walks back out instead of being trapped there forever.
function resolveObstaclePenetration(
  position: Vector3,
  radius: number,
  obstacles: readonly CollisionObstacle[],
): void {
  for (const obstacle of obstacles) {
    const closestX = MathUtils.clamp(position.x, obstacle.minX, obstacle.maxX);
    const closestZ = MathUtils.clamp(position.z, obstacle.minZ, obstacle.maxZ);
    const offsetX = position.x - closestX;
    const offsetZ = position.z - closestZ;
    const distanceSquared = offsetX * offsetX + offsetZ * offsetZ;

    if (distanceSquared >= radius * radius) {
      continue;
    }

    if (distanceSquared > 1e-8) {
      const distance = Math.sqrt(distanceSquared);
      position.x = closestX + (offsetX / distance) * radius;
      position.z = closestZ + (offsetZ / distance) * radius;
      continue;
    }

    const exitWest = position.x - obstacle.minX;
    const exitEast = obstacle.maxX - position.x;
    const exitNorth = position.z - obstacle.minZ;
    const exitSouth = obstacle.maxZ - position.z;
    const shortestExit = Math.min(exitWest, exitEast, exitNorth, exitSouth);

    if (shortestExit === exitWest) {
      position.x = obstacle.minX - radius;
    } else if (shortestExit === exitEast) {
      position.x = obstacle.maxX + radius;
    } else if (shortestExit === exitNorth) {
      position.z = obstacle.minZ - radius;
    } else {
      position.z = obstacle.maxZ + radius;
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

  position.x = MathUtils.clamp(position.x + movement.x, minX, maxX);
  position.z = MathUtils.clamp(position.z + movement.z, minZ, maxZ);

  resolveObstaclePenetration(position, radius, world.obstacles);

  position.x = MathUtils.clamp(position.x, minX, maxX);
  position.z = MathUtils.clamp(position.z, minZ, maxZ);
}

// Fraction along origin->target at which the segment first enters an
// obstacle, or 1 when the segment is clear. Used to pull the camera in
// front of anything it would otherwise sit inside.
export function findSegmentObstruction(
  origin: Vector3,
  target: Vector3,
  padding: number,
  world: CollisionWorld,
): number {
  const directionX = target.x - origin.x;
  const directionY = target.y - origin.y;
  const directionZ = target.z - origin.z;
  let nearest = 1;

  for (const obstacle of world.obstacles) {
    const entry = findSegmentBoxEntry(
      origin,
      directionX,
      directionY,
      directionZ,
      obstacle,
      padding,
    );

    if (entry !== null && entry < nearest) {
      nearest = entry;
    }
  }

  return nearest;
}

function findSegmentBoxEntry(
  origin: Vector3,
  directionX: number,
  directionY: number,
  directionZ: number,
  obstacle: CollisionObstacle,
  padding: number,
): number | null {
  let entry = 0;
  let exit = 1;

  const axes: readonly [number, number, number, number][] = [
    [origin.x, directionX, obstacle.minX - padding, obstacle.maxX + padding],
    [origin.y, directionY, -padding, obstacle.height + padding],
    [origin.z, directionZ, obstacle.minZ - padding, obstacle.maxZ + padding],
  ];

  for (const [start, direction, minimum, maximum] of axes) {
    if (Math.abs(direction) < 1e-8) {
      if (start < minimum || start > maximum) {
        return null;
      }
      continue;
    }

    const firstCrossing = (minimum - start) / direction;
    const secondCrossing = (maximum - start) / direction;
    entry = Math.max(entry, Math.min(firstCrossing, secondCrossing));
    exit = Math.min(exit, Math.max(firstCrossing, secondCrossing));

    if (entry > exit) {
      return null;
    }
  }

  return entry;
}
