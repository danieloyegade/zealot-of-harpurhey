import { MathUtils, Vector3 } from 'three';

const SEPARATION_EPSILON = 0.000001;

export interface CollisionObstacle {
  readonly name: string;
  readonly minX: number;
  readonly maxX: number;
  readonly minZ: number;
  readonly maxZ: number;
  readonly height: number;
  /**
   * Whether the camera should pull in front of this obstacle. Street furniture
   * blocks movement but is too thin to hide the player, and yanking the camera
   * in for every passing lamppost reads as a glitch. Defaults to true.
   */
  readonly occludesCamera?: boolean;
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

  // Apply the full movement, then let the shared overlap resolver push the
  // circle back out. This resolves to exact contact rather than stopping a
  // frame short, and slides along corners instead of cancelling a whole axis.
  position.x = MathUtils.clamp(position.x + movement.x, minX, maxX);
  position.z = MathUtils.clamp(position.z + movement.z, minZ, maxZ);

  resolveCircleOverlaps(position, radius, world);
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
    if (obstacle.occludesCamera === false) {
      continue;
    }

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
