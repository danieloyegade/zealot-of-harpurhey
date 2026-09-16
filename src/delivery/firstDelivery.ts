import { PLAYER_START, WORLD_LOCATIONS, type WorldLocation } from '../world/worldLayout';

export interface DeliveryAssignment {
  readonly number: number;
  readonly item: string;
  /** A `WORLD_LOCATIONS` id. */
  readonly destinationId: string;
  readonly destinationDetail: string;
  readonly feePence: number;
}

// The first assignment of a night. No delivery system exists yet: this is the
// data it will start from, and what the title card already reads.
export const FIRST_DELIVERY: DeliveryAssignment = {
  number: 1,
  item: 'Flowers',
  destinationId: 'vinyl-exchange',
  destinationDetail: 'Upper floor',
  feePence: 370,
};

export function deliveryDestination(assignment: DeliveryAssignment): WorldLocation | undefined {
  return WORLD_LOCATIONS.find((location) => location.id === assignment.destinationId);
}

/** Straight-line distance from where a night begins to the destination. */
export function distanceFromStartMetres(assignment: DeliveryAssignment): number {
  const destination = deliveryDestination(assignment);
  if (!destination) return 0;
  return Math.hypot(destination.x - PLAYER_START.x, destination.z - PLAYER_START.z);
}
