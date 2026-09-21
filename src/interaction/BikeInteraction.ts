import { Vector2, Vector3 } from 'three';
import type { CameraTarget } from '../camera/ThirdPersonCamera';
import type { InputController } from '../input/InputController';
import type { InteractionPromptView } from './InteractionPromptView';
import type { PlayerController } from '../player/PlayerController';
import type { SterlingBike } from '../vehicles/SterlingBike';
import type { SterlingFleet } from '../vehicles/SterlingFleet';
import { resolveCircleOverlaps, type CollisionWorld } from '../world/collision';

// Reach from the player to a standing bike's centreline.
const MOUNT_REACH = 1.05;
// Getting off happens once braking has brought the bike this slow.
const DISMOUNT_SPEED = 0.6;
const DOCKING_MAXIMUM_SPEED = 3.2;
// Where the rider steps off, in (forward, right) metres from the bike origin:
// right side first (the dock post is on the left), then left, then behind,
// which is the only clear spot between neighbours in a full station.
const DISMOUNT_SPOTS: readonly (readonly [number, number])[] = [
  [-0.15, 0.78],
  [-0.15, -0.78],
  [-1.5, 0],
];
const DISMOUNT_CLEARANCE = 0.12;

type RideState =
  | { readonly kind: 'on-foot' }
  | { readonly kind: 'riding'; readonly bike: SterlingBike; dismountRequested: boolean }
  | { readonly kind: 'docking'; readonly bike: SterlingBike }
  | { readonly kind: 'undocking'; readonly bike: SterlingBike };

const movementAxes = new Vector2();
const standPosition = new Vector3();
const clearedPosition = new Vector3();

/**
 * Walk up to a Sterling bike and press E to take it; ride it anywhere; press
 * E near an empty dock to return it, or anywhere else to get off and leave it
 * standing. Bike-relative controls: W pedal, Shift e-assist, Space boost, S
 * brake and back up, A/D steer.
 */
export class BikeInteraction {
  private state: RideState = { kind: 'on-foot' };
  private nearbyBike: SterlingBike | null = null;

  constructor(
    private readonly fleet: SterlingFleet,
    private readonly player: PlayerController,
    private readonly collision: CollisionWorld,
  ) {}

  get isRiding(): boolean {
    return this.state.kind !== 'on-foot';
  }

  get bike(): SterlingBike | null {
    return this.state.kind === 'on-foot' ? null : this.state.bike;
  }

  /** What the camera should follow: the bike while mounted, else the player. */
  get cameraTarget(): CameraTarget {
    return this.state.kind === 'on-foot' ? this.player : this.state.bike;
  }

  /** Fixed-step update: moves the player on foot, or the bike and its rider. */
  update(deltaTime: number, input: InputController, cameraForward: Vector3): void {
    const interact = input.consumeInteract();
    const state = this.state;

    if (state.kind === 'on-foot') {
      this.player.update(deltaTime, input, cameraForward);
      this.nearbyBike = this.fleet.nearestMountable(this.player.position, MOUNT_REACH);
      if (interact && this.nearbyBike) {
        const bike = this.nearbyBike;
        this.fleet.takeOut(bike);
        this.player.beginRiding();
        this.state = this.fleet.isInMotion(bike)
          ? { kind: 'undocking', bike }
          : { kind: 'riding', bike, dismountRequested: false };
        this.nearbyBike = null;
      }
      this.fleet.update(deltaTime);
      return;
    }

    if (state.kind === 'docking' || state.kind === 'undocking') {
      this.fleet.update(deltaTime);
      this.player.updateRiding(deltaTime, state.bike, state.bike.forward);
      if (!this.fleet.isInMotion(state.bike)) {
        if (state.kind === 'docking') {
          this.stepOff(state.bike);
        } else {
          this.state = { kind: 'riding', bike: state.bike, dismountRequested: false };
        }
      }
      return;
    }

    const { bike } = state;
    if (interact) {
      const dock = this.fleet.nearestFreeDock(bike);
      if (dock && Math.abs(bike.speed) <= DOCKING_MAXIMUM_SPEED) {
        this.fleet.beginDocking(bike, dock);
        this.state = { kind: 'docking', bike };
        this.fleet.update(deltaTime);
        this.player.updateRiding(deltaTime, bike, bike.forward);
        return;
      }
      state.dismountRequested = !state.dismountRequested;
    }

    input.getMovementAxes(movementAxes);
    const braking = state.dismountRequested;
    // Space boosts on its own, without W, unless the rider is braking with S.
    const boosting = input.isBoosting && movementAxes.y >= 0 && !braking;
    bike.ride(
      deltaTime,
      {
        throttle: braking ? -1 : boosting ? 1 : movementAxes.y,
        steer: -movementAxes.x,
        assisted: input.isAssisting,
        boost: boosting,
      },
      this.collision,
    );
    this.fleet.update(deltaTime);
    this.player.updateRiding(deltaTime, bike, bike.forward);

    if (braking && Math.abs(bike.speed) <= DISMOUNT_SPEED) {
      bike.speed = 0;
      this.fleet.park(bike);
      this.stepOff(bike);
    }
  }

  /** The prompt to show this frame, or null. */
  get prompt(): InteractionPromptView | null {
    switch (this.state.kind) {
      case 'on-foot':
        if (!this.nearbyBike) return null;
        return {
          key: 'E',
          label: this.nearbyBike.state === 'docked' ? 'Hire Sterling bike' : 'Ride bike',
        };
      case 'docking':
      case 'undocking':
        return null;
      case 'riding': {
        const { bike } = this.state;
        if (this.state.dismountRequested) return { key: 'E', label: 'Keep riding' };
        const dock = this.fleet.nearestFreeDock(bike);
        if (dock && Math.abs(bike.speed) <= DOCKING_MAXIMUM_SPEED) {
          return { key: 'E', label: 'Return to dock' };
        }
        return { key: 'E', label: 'Get off' };
      }
    }
  }

  private stepOff(bike: SterlingBike): void {
    const right = new Vector3(-bike.forward.z, 0, bike.forward.x);
    // First spot nothing stands in; otherwise whichever needed the least push.
    let best: Vector3 | null = null;
    let bestPush = Number.POSITIVE_INFINITY;
    for (const [forward, side] of DISMOUNT_SPOTS) {
      standPosition
        .copy(bike.position)
        .addScaledVector(right, side)
        .addScaledVector(bike.forward, forward);
      standPosition.y = 0;
      clearedPosition.copy(standPosition);
      resolveCircleOverlaps(clearedPosition, this.player.collisionRadius, this.collision);
      const push = clearedPosition.distanceTo(standPosition);
      if (push < bestPush) {
        best = clearedPosition.clone();
        bestPush = push;
      }
      if (push <= DISMOUNT_CLEARANCE) break;
    }
    this.player.endRiding(best ?? bike.position, bike.forward);
    this.state = { kind: 'on-foot' };
  }
}
