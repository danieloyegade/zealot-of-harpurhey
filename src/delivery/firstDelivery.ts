import { PLAYER_START, WORLD_LOCATIONS, type WorldLocation } from '../world/worldLayout';

export interface DeliveryAssignment {
  readonly number: number;
  readonly item: string;
  /** A `WORLD_LOCATIONS` id. */
  readonly pickupId: string;
  readonly pickupDetail: string;
  /** A `WORLD_LOCATIONS` id. */
  readonly destinationId: string;
  readonly destinationDetail: string;
  readonly feePence: number;
}

// The first assignment of a night. The mundanity is intentional: the courier
// structure is established before the night asks anything stranger of it.
export const FIRST_DELIVERY: DeliveryAssignment = {
  number: 1,
  item: 'Flowers',
  pickupId: 'florist',
  pickupDetail: 'Collect at shutter',
  destinationId: 'vinyl-exchange',
  destinationDetail: 'Upper floor',
  feePence: 370,
};

export function deliveryPickup(assignment: DeliveryAssignment): WorldLocation | undefined {
  return WORLD_LOCATIONS.find((location) => location.id === assignment.pickupId);
}

export function deliveryDestination(assignment: DeliveryAssignment): WorldLocation | undefined {
  return WORLD_LOCATIONS.find((location) => location.id === assignment.destinationId);
}

/** Straight-line distance from where a night begins to the destination. */
export function distanceFromStartMetres(assignment: DeliveryAssignment): number {
  const destination = deliveryDestination(assignment);
  if (!destination) return 0;
  return Math.hypot(destination.x - PLAYER_START.x, destination.z - PLAYER_START.z);
}
