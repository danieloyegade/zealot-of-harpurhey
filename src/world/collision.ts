import { MathUtils, Vector3 } from 'three';

const SEPARATION_EPSILON = 0.000001;

// Movement is advanced in slices no longer than this fraction of the mover's
// radius, so even thin interior walls cannot be stepped over in one update.
const MAXIMUM_STEP_FRACTION = 0.5;
const CONTACT_ITERATIONS = 4;

interface ObstacleVolume {
  readonly name: string;
  /**
   * Top of the solid volume in metres. Omitted means unbounded, which suits
   * building shells taller than any camera position.
   */
  readonly height?: number;
  /**
   * Whether the third-person camera is pulled in front of this obstacle.
   * Omitted means true. Thin street furniture opts out so poles and bollards
   * passing behind the player do not make the camera pump.
   */
  readonly blocksCamera?: boolean;
}

/** Axis-aligned box. Shape is optional so existing footprint literals stay valid. */
export interface BoxObstacle extends ObstacleVolume {
  readonly shape?: 'box';
  readonly minX: number;
  readonly maxX: number;
  readonly minZ: number;
  readonly maxZ: number;
}

export interface CircleObstacle extends ObstacleVolume {
  readonly shape: 'circle';
  readonly x: number;
  readonly z: number;
  readonly radius: number;
}

/** Box of `halfWidth` along local X and `halfDepth` along local Z, yawed like Object3D.rotation.y. */
export interface OrientedBoxObstacle extends ObstacleVolume {
  readonly shape: 'oriented-box';
  readonly x: number;
  readonly z: number;
  readonly halfWidth: number;
  readonly halfDepth: number;
  readonly rotationY: number;
}

export type CollisionObstacle = BoxObstacle | CircleObstacle | OrientedBoxObstacle;

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

/** Solid prop footprint for round street furniture. */
export function circleObstacle(
  name: string,
  x: number,
  z: number,
  radius: number,
  height: number,
): CircleObstacle {
  return { name, shape: 'circle', x, z, radius, height, blocksCamera: false };
}

/** Solid prop footprint for rectangular street furniture of full `width` × `depth`. */
export function orientedBoxObstacle(
  name: string,
  x: number,
  z: number,
  width: number,
  depth: number,
  rotationY: number,
  height: number,
): OrientedBoxObstacle {
  return {
    name,
    shape: 'oriented-box',
    x,
    z,
    halfWidth: width / 2,
    halfDepth: depth / 2,
    rotationY,
    height,
    blocksCamera: false,
  };
}

interface Contact {
  normalX: number;
  normalZ: number;
  depth: number;
}

const contact: Contact = { normalX: 0, normalZ: 0, depth: 0 };

interface BoxFrame {
  centreX: number;
  centreZ: number;
  halfWidth: number;
  halfDepth: number;
  cos: number;
  sin: number;
}

interface ObstacleBounds {
  readonly minX: number;
  readonly maxX: number;
  readonly minZ: number;
  readonly maxZ: number;
}

const obstacleBoundsCache = new WeakMap<CollisionObstacle, ObstacleBounds>();
const boxFrameCache = new WeakMap<BoxObstacle | OrientedBoxObstacle, BoxFrame>();

function loadObstacleBounds(obstacle: CollisionObstacle): ObstacleBounds {
  const cached = obstacleBoundsCache.get(obstacle);
  if (cached) return cached;

  let bounds: ObstacleBounds;
  if (obstacle.shape === 'circle') {
    bounds = {
      minX: obstacle.x - obstacle.radius,
      maxX: obstacle.x + obstacle.radius,
      minZ: obstacle.z - obstacle.radius,
      maxZ: obstacle.z + obstacle.radius,
    };
  } else if (obstacle.shape === 'oriented-box') {
    const frame = loadBoxFrame(obstacle);
    const extentX = Math.abs(frame.cos) * obstacle.halfWidth
      + Math.abs(frame.sin) * obstacle.halfDepth;
    const extentZ = Math.abs(frame.sin) * obstacle.halfWidth
      + Math.abs(frame.cos) * obstacle.halfDepth;
    bounds = {
      minX: obstacle.x - extentX,
      maxX: obstacle.x + extentX,
      minZ: obstacle.z - extentZ,
      maxZ: obstacle.z + extentZ,
    };
  } else {
    bounds = obstacle;
  }

  obstacleBoundsCache.set(obstacle, bounds);
  return bounds;
}

function loadBoxFrame(obstacle: BoxObstacle | OrientedBoxObstacle): BoxFrame {
  const cached = boxFrameCache.get(obstacle);
  if (cached) return cached;

  let frame: BoxFrame;
  if (obstacle.shape === 'oriented-box') {
    frame = {
      centreX: obstacle.x,
      centreZ: obstacle.z,
      halfWidth: obstacle.halfWidth,
      halfDepth: obstacle.halfDepth,
      cos: Math.cos(obstacle.rotationY),
      sin: Math.sin(obstacle.rotationY),
    };
  } else {
    frame = {
      centreX: (obstacle.minX + obstacle.maxX) / 2,
      centreZ: (obstacle.minZ + obstacle.maxZ) / 2,
      halfWidth: (obstacle.maxX - obstacle.minX) / 2,
      halfDepth: (obstacle.maxZ - obstacle.minZ) / 2,
      cos: 1,
      sin: 0,
    };
  }
  boxFrameCache.set(obstacle, frame);
  return frame;
}

/**
 * Writes the push-out normal and depth for a circle overlapping `obstacle`
 * into `contact`, returning false when they do not overlap.
 */
function findContact(
  x: number,
  z: number,
  radius: number,
  obstacle: CollisionObstacle,
): boolean {
  // Most world obstacles are nowhere near a given player/bike probe. Reject
  // those before any square roots or local-space transforms. Bounds and box
  // trigonometry are cached because obstacle objects are immutable; moving
  // parked-bike footprints are replaced rather than mutated.
  const bounds = loadObstacleBounds(obstacle);
  if (
    x + radius <= bounds.minX
    || x - radius >= bounds.maxX
    || z + radius <= bounds.minZ
    || z - radius >= bounds.maxZ
  ) {
    return false;
  }

  if (obstacle.shape === 'circle') {
    const offsetX = x - obstacle.x;
    const offsetZ = z - obstacle.z;
    const reach = radius + obstacle.radius;
    const distanceSquared = offsetX * offsetX + offsetZ * offsetZ;
    if (distanceSquared >= reach * reach) {
      return false;
    }
    const distance = Math.sqrt(distanceSquared);
    if (distance < SEPARATION_EPSILON) {
      contact.normalX = 1;
      contact.normalZ = 0;
    } else {
      contact.normalX = offsetX / distance;
      contact.normalZ = offsetZ / distance;
    }
    contact.depth = reach - distance;
    return true;
  }

  const frame = loadBoxFrame(obstacle);
  // World offset into the box's local frame (inverse yaw).
  const worldOffsetX = x - frame.centreX;
  const worldOffsetZ = z - frame.centreZ;
  const localX = worldOffsetX * frame.cos - worldOffsetZ * frame.sin;
  const localZ = worldOffsetX * frame.sin + worldOffsetZ * frame.cos;

  const closestX = MathUtils.clamp(localX, -frame.halfWidth, frame.halfWidth);
  const closestZ = MathUtils.clamp(localZ, -frame.halfDepth, frame.halfDepth);
  let normalX: number;
  let normalZ: number;

  if (closestX !== localX || closestZ !== localZ) {
    const offsetX = localX - closestX;
    const offsetZ = localZ - closestZ;
    const distanceSquared = offsetX * offsetX + offsetZ * offsetZ;
    if (distanceSquared >= radius * radius) {
      return false;
    }
    const distance = Math.sqrt(distanceSquared);
    normalX = offsetX / distance;
    normalZ = offsetZ / distance;
    contact.depth = radius - distance;
  } else {
    // The centre is inside the box: leave through the nearest face.
    const exitX = frame.halfWidth - Math.abs(localX);
    const exitZ = frame.halfDepth - Math.abs(localZ);
    if (exitX <= exitZ) {
      normalX = localX < 0 ? -1 : 1;
      normalZ = 0;
      contact.depth = exitX + radius;
    } else {
      normalX = 0;
      normalZ = localZ < 0 ? -1 : 1;
      contact.depth = exitZ + radius;
    }
  }

  // Local normal back to world space (forward yaw).
  contact.normalX = normalX * frame.cos + normalZ * frame.sin;
  contact.normalZ = -normalX * frame.sin + normalZ * frame.cos;
  return true;
}

function clampToBounds(position: Vector3, radius: number, bounds: PlayableBounds): void {
  position.x = MathUtils.clamp(position.x, bounds.minX + radius, bounds.maxX - radius);
  position.z = MathUtils.clamp(position.z, bounds.minZ + radius, bounds.maxZ - radius);
}

/** Pushes the circle out of every obstacle it overlaps. Returns true if it is left clear. */
function pushOutOfObstacles(
  position: Vector3,
  radius: number,
  world: CollisionWorld,
  maximumPasses: number,
): boolean {
  for (let pass = 0; pass < maximumPasses; pass += 1) {
    let foundOverlap = false;
    for (const obstacle of world.obstacles) {
      if (!findContact(position.x, position.z, radius, obstacle)) {
        continue;
      }
      const push = contact.depth + SEPARATION_EPSILON;
      position.x += contact.normalX * push;
      position.z += contact.normalZ * push;
      clampToBounds(position, radius, world.bounds);
      foundOverlap = true;
    }
    if (!foundOverlap) {
      return true;
    }
  }
  return !world.obstacles.some((obstacle) =>
    findContact(position.x, position.z, radius, obstacle));
}

export function resolveCircleOverlaps(
  position: Vector3,
  radius: number,
  world: CollisionWorld,
): void {
  clampToBounds(position, radius, world.bounds);
  pushOutOfObstacles(
    position,
    radius,
    world,
    Math.max(1, world.obstacles.length * 2),
  );
}

const stepStart = new Vector3();

/**
 * Moves a ground-plane circle by `movement`, sliding along whatever it meets.
 *
 * Each slice moves freely and is then pushed back out along the contact
 * normals, which removes only the part of the motion driving into a surface
 * and so slides along walls and round obstacles alike. A slice that cannot be
 * resolved (a pinch narrower than the circle) is undone instead of letting the
 * mover squeeze through.
 */
export function moveCircleWithCollisions(
  position: Vector3,
  movement: Vector3,
  radius: number,
  world: CollisionWorld,
): void {
  // A level edit or teleport can place the player inside an obstacle. Recover
  // before testing incremental movement so the player cannot become trapped.
  resolveCircleOverlaps(position, radius, world);

  const distance = Math.hypot(movement.x, movement.z);
  if (distance === 0) {
    return;
  }
  const slices = Math.ceil(distance / (radius * MAXIMUM_STEP_FRACTION));
  const sliceX = movement.x / slices;
  const sliceZ = movement.z / slices;

  for (let slice = 0; slice < slices; slice += 1) {
    stepStart.copy(position);
    position.x += sliceX;
    position.z += sliceZ;
    clampToBounds(position, radius, world.bounds);
    if (!pushOutOfObstacles(position, radius, world, CONTACT_ITERATIONS)) {
      position.copy(stepStart);
      return;
    }
  }
}

/**
 * Fraction (0–1) of the way from `start` to `end` at which a sphere of
 * `radius` first touches an obstacle volume, or 1 when the path is clear.
 * Obstacles are extruded from the ground to their height; ones that already
 * contain `start` are ignored so a pivot tucked against a wall is not pinned.
 */
export function castSphereThroughObstacles(
  start: Vector3,
  end: Vector3,
  radius: number,
  world: CollisionWorld,
): number {
  const deltaX = end.x - start.x;
  const deltaY = end.y - start.y;
  const deltaZ = end.z - start.z;
  let nearest = 1;

  for (const obstacle of world.obstacles) {
    if (obstacle.blocksCamera === false) {
      continue;
    }
    const top = (obstacle.height ?? Number.POSITIVE_INFINITY) + radius;

    let enter: number;
    let exit: number;
    let startInside: boolean;

    if (obstacle.shape === 'circle') {
      const offsetX = start.x - obstacle.x;
      const offsetZ = start.z - obstacle.z;
      const reach = obstacle.radius + radius;
      const a = deltaX * deltaX + deltaZ * deltaZ;
      const b = 2 * (offsetX * deltaX + offsetZ * deltaZ);
      const c = offsetX * offsetX + offsetZ * offsetZ - reach * reach;
      startInside = c <= 0 && start.y <= top;
      if (a < SEPARATION_EPSILON) {
        continue;
      }
      const discriminant = b * b - 4 * a * c;
      if (discriminant < 0) {
        continue;
      }
      const root = Math.sqrt(discriminant);
      enter = (-b - root) / (2 * a);
      exit = (-b + root) / (2 * a);
    } else {
      const frame = loadBoxFrame(obstacle);
      const offsetX = start.x - frame.centreX;
      const offsetZ = start.z - frame.centreZ;
      const localStartX = offsetX * frame.cos - offsetZ * frame.sin;
      const localStartZ = offsetX * frame.sin + offsetZ * frame.cos;
      const localDeltaX = deltaX * frame.cos - deltaZ * frame.sin;
      const localDeltaZ = deltaX * frame.sin + deltaZ * frame.cos;
      const reachX = frame.halfWidth + radius;
      const reachZ = frame.halfDepth + radius;
      startInside = Math.abs(localStartX) <= reachX
        && Math.abs(localStartZ) <= reachZ
        && start.y <= top;

      enter = Number.NEGATIVE_INFINITY;
      exit = Number.POSITIVE_INFINITY;
      for (const [origin, direction, reach] of [
        [localStartX, localDeltaX, reachX],
        [localStartZ, localDeltaZ, reachZ],
      ] as const) {
        if (Math.abs(direction) < SEPARATION_EPSILON) {
          if (Math.abs(origin) > reach) {
            enter = Number.POSITIVE_INFINITY;
          }
          continue;
        }
        const first = (-reach - origin) / direction;
        const second = (reach - origin) / direction;
        enter = Math.max(enter, Math.min(first, second));
        exit = Math.min(exit, Math.max(first, second));
      }
    }

    if (startInside) {
      continue;
    }

    // Clip against the extruded height (the volume runs down through the ground).
    if (Number.isFinite(top)) {
      if (Math.abs(deltaY) < SEPARATION_EPSILON) {
        if (start.y > top) {
          continue;
        }
      } else {
        const crossing = (top - start.y) / deltaY;
        if (deltaY > 0) {
          exit = Math.min(exit, crossing);
        } else {
          enter = Math.max(enter, crossing);
        }
      }
    }

    if (enter <= exit && enter >= 0 && enter < nearest) {
      nearest = enter;
    }
  }

  return nearest;
}
