import type { Vector3 } from 'three';
import type { InputController } from '../input/InputController';
import type { InteractionPromptView } from '../interaction/InteractionPromptView';
import {
  FIRST_DELIVERY,
  deliveryDestination,
  deliveryPickup,
  type DeliveryAssignment,
} from './firstDelivery';
import { advanceDeliveryPhase, type DeliveryPhase } from './deliveryState';

const INTERACTION_REACH = 2.35;

export interface DeliveryView {
  readonly assignment: DeliveryAssignment;
  readonly phase: DeliveryPhase;
  readonly placeName: string;
  readonly detail: string;
}

/**
 * One complete, deliberately plain delivery loop. It shares the existing E
 * queue with bikes: it consumes the press only while the courier is on foot
 * and standing at the active address, so unrelated interactions still work.
 */
export class DeliveryInteraction {
  private phase: DeliveryPhase;
  private nearby = false;
  private riding = false;

  constructor(
    readonly assignment: DeliveryAssignment = FIRST_DELIVERY,
    initialPhase: DeliveryPhase = 'awaiting-pickup',
  ) {
    this.phase = initialPhase;
    if (!deliveryPickup(assignment) || !deliveryDestination(assignment)) {
      throw new Error(`Delivery ${assignment.number} references an unknown world location.`);
    }
  }

  update(input: InputController, playerPosition: Vector3, riding: boolean): void {
    this.riding = riding;
    const location = this.activeLocation;
    if (!location || riding) {
      this.nearby = false;
      return;
    }

    const stop = this.phase === 'awaiting-pickup'
      ? { x: location.x, z: location.z + location.depth / 2 + 1.15 }
      : { x: location.x, z: location.z + location.depth / 2 + 1.35 };
    this.nearby = Math.hypot(playerPosition.x - stop.x, playerPosition.z - stop.z) <= INTERACTION_REACH;

    if (this.nearby && input.consumeInteract()) {
      this.phase = advanceDeliveryPhase(this.phase);
      this.nearby = false;
    }
  }

  get prompt(): InteractionPromptView | null {
    if (!this.nearby || this.riding || this.phase === 'complete') return null;
    return {
      key: 'E',
      label: this.phase === 'awaiting-pickup' ? 'Collect flowers' : 'Leave flowers',
    };
  }

  get view(): DeliveryView {
    const location = this.activeLocation;
    return {
      assignment: this.assignment,
      phase: this.phase,
      placeName: location?.name ?? '',
      detail: this.phase === 'awaiting-pickup'
        ? this.assignment.pickupDetail
        : this.phase === 'in-transit'
          ? this.assignment.destinationDetail
          : 'Received',
    };
  }

  private get activeLocation() {
    if (this.phase === 'awaiting-pickup') return deliveryPickup(this.assignment);
    if (this.phase === 'in-transit') return deliveryDestination(this.assignment);
    return undefined;
  }
}
