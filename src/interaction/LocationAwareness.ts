import { MathUtils, type Vector3 } from 'three';
import {
  BUS_STOPS,
  STERLING_BIKE_DOCKS,
  WORLD_LOCATIONS,
  type LocationStatus,
} from '../world/worldLayout';

export interface ProximityTarget {
  readonly id: string;
  readonly name: string;
  readonly status: LocationStatus;
  /** Footprint the player is measured against, not a centre point. */
  readonly minX: number;
  readonly maxX: number;
  readonly minZ: number;
  readonly maxZ: number;
}

/**
 * Distance from the footprint edge at which a location acknowledges the
 * player. Deliberately close: the world should not announce itself from across
 * the street.
 */
const ACKNOWLEDGE_RANGE = 2.6;

/**
 * Extra distance the player must travel before an acknowledged location is
 * released again, so a label does not flicker while standing on the boundary.
 */
const RELEASE_HYSTERESIS = 0.9;

/** Markers have no footprint, so they get a small nominal one. */
const MARKER_HALF_EXTENT = 1.1;

function distanceToFootprint(
  target: ProximityTarget,
  x: number,
  z: number,
): number {
  const closestX = MathUtils.clamp(x, target.minX, target.maxX);
  const closestZ = MathUtils.clamp(z, target.minZ, target.maxZ);
  const offsetX = x - closestX;
  const offsetZ = z - closestZ;

  return Math.sqrt(offsetX * offsetX + offsetZ * offsetZ);
}

export function createProximityTargets(): ProximityTarget[] {
  // Only kinds the player approaches from outside. The park and car park are
  // walked *through* — their footprints enclose the player (the spawn point
  // sits inside the park), so edge distance is meaningless for them. They need
  // a region-entry rule rather than a proximity one, which is a separate job.
  const targets: ProximityTarget[] = WORLD_LOCATIONS.filter(
    (location) => location.kind === 'building',
  ).map((location) => ({
    id: location.id,
    name: location.name,
    status: location.status,
    minX: location.x - location.width / 2,
    maxX: location.x + location.width / 2,
    minZ: location.z - location.depth / 2,
    maxZ: location.z + location.depth / 2,
  }));

  for (const marker of [...BUS_STOPS, ...STERLING_BIKE_DOCKS]) {
    targets.push({
      id: marker.id,
      name: marker.name,
      status: 'placeholder',
      minX: marker.x - MARKER_HALF_EXTENT,
      maxX: marker.x + MARKER_HALF_EXTENT,
      minZ: marker.z - MARKER_HALF_EXTENT,
      maxZ: marker.z + MARKER_HALF_EXTENT,
    });
  }

  return targets;
}

/**
 * Tracks which authored location the player is currently standing at.
 *
 * This is the seam the delivery loop attaches to: it answers "where am I" from
 * the existing `worldLayout` data without owning any behaviour of its own.
 * Nothing here invents content — it surfaces names that are already authored.
 */
export class LocationAwareness {
  private readonly targets: readonly ProximityTarget[];
  private current: ProximityTarget | null = null;

  constructor(targets: readonly ProximityTarget[] = createProximityTargets()) {
    this.targets = targets;
  }

  get activeTarget(): ProximityTarget | null {
    return this.current;
  }

  /**
   * Returns true when the acknowledged location changed this step, so callers
   * can react to arrival and departure rather than polling.
   */
  update(playerPosition: Vector3): boolean {
    const previous = this.current;

    // An already-acknowledged location keeps priority while the player stays
    // inside its release range, so walking along a shopfront does not strobe
    // between neighbouring footprints.
    if (previous !== null) {
      const heldDistance = distanceToFootprint(
        previous,
        playerPosition.x,
        playerPosition.z,
      );
      if (heldDistance <= ACKNOWLEDGE_RANGE + RELEASE_HYSTERESIS) {
        return false;
      }
    }

    let nearest: ProximityTarget | null = null;
    let nearestDistance = ACKNOWLEDGE_RANGE;

    for (const target of this.targets) {
      const distance = distanceToFootprint(
        target,
        playerPosition.x,
        playerPosition.z,
      );
      if (distance <= nearestDistance) {
        nearest = target;
        nearestDistance = distance;
      }
    }

    this.current = nearest;
    return this.current !== previous;
  }
}
