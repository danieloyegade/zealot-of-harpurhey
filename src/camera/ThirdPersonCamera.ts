import { MathUtils, PerspectiveCamera, Vector2, Vector3 } from 'three';
import type { InputController } from '../input/InputController';
import type { MovementState } from '../player/PlayerController';
import { findSegmentObstruction, type CollisionWorld } from '../world/collision';

export interface CameraTarget {
  readonly position: Vector3;
  readonly facingDirection: Vector3;
  readonly movementState: MovementState;
}

const WALKING_FIELD_OF_VIEW = 58;
const RUNNING_FIELD_OF_VIEW = 64;

// Radians of rotation per full screen height of pointer travel, so the same
// gesture turns the same amount regardless of display size.
const ORBIT_RADIANS_PER_SCREEN = 3.2;
const KEYBOARD_ORBIT_SPEED = 2.2;

// How long manual orbiting suppresses auto-follow, so the camera does not
// fight a player who is deliberately looking somewhere else.
const MANUAL_ORBIT_HOLD_SECONDS = 1.2;

const OCCLUSION_PADDING = 0.18;

// Only guards against the camera landing exactly on the look target; it must
// never exceed the cleared distance, or the camera is pushed back into the
// wall the occlusion test just moved it out of.
const MIN_OCCLUDED_DISTANCE = 0.12;

// Backing into a wall and orbiting into it pulls the camera inside the player
// figure, which would otherwise fill the screen. Hide the figure instead, with
// hysteresis so it cannot flicker at the threshold.
const HIDE_TARGET_BELOW = 1.7;
const SHOW_TARGET_ABOVE = 1.95;

export class ThirdPersonCamera {
  invertPitch = false;
  orbitSensitivity = 1;

  private distance = 6.8;
  private readonly minDistance = 3.4;
  private readonly maxDistance = 10.5;
  private yaw = 0;
  private pitch = 0.31;
  private readonly minPitch = 0.04;
  private readonly maxPitch = 1.02;
  private readonly followResponsiveness = 9;
  private readonly anchorResponsiveness = 14;
  private readonly autoFollowResponsiveness = 2.4;
  private manualOrbitHold = 0;
  private targetHidden = false;
  private fieldOfView = WALKING_FIELD_OF_VIEW;
  private readonly anchor = new Vector3();
  private readonly orbitInput = new Vector2();
  private readonly desiredPosition = new Vector3();
  private readonly occlusionOrigin = new Vector3();
  private readonly lookTarget = new Vector3();

  constructor(
    private readonly camera: PerspectiveCamera,
    private readonly collisionWorld: CollisionWorld,
    private readonly lookTargetHeight = 1.05,
  ) {
    camera.fov = this.fieldOfView;
    camera.updateProjectionMatrix();
  }

  getPlanarForward(target: Vector3): Vector3 {
    return target.set(-Math.sin(this.yaw), 0, -Math.cos(this.yaw));
  }

  // True when the camera has been pulled so close that the follow target would
  // obscure the view and should not be drawn.
  get isTargetObscuringView(): boolean {
    return this.targetHidden;
  }

  snapTo(target: CameraTarget): void {
    this.anchor.copy(target.position);
    this.calculateDesiredPosition();
    this.camera.position.copy(this.desiredPosition);
    this.updateLookTarget();
    this.camera.lookAt(this.lookTarget);
  }

  update(deltaTime: number, input: InputController, target: CameraTarget): void {
    this.applyOrbitInput(deltaTime, input);
    this.applyAutoFollow(deltaTime, target);

    this.distance = MathUtils.clamp(
      this.distance + input.zoomDelta,
      this.minDistance,
      this.maxDistance,
    );

    // Both the camera position and the look target derive from this single
    // smoothed anchor; driving them from different points makes the player
    // slide around the frame whenever they accelerate.
    this.anchor.lerp(
      target.position,
      1 - Math.exp(-this.anchorResponsiveness * deltaTime),
    );

    this.calculateDesiredPosition();
    const followBlend = 1 - Math.exp(-this.followResponsiveness * deltaTime);
    this.camera.position.lerp(this.desiredPosition, followBlend);

    this.updateLookTarget();
    this.camera.lookAt(this.lookTarget);
    this.updateTargetVisibility();
    this.updateFieldOfView(deltaTime, target.movementState);
  }

  private updateTargetVisibility(): void {
    const distance = this.camera.position.distanceTo(this.lookTarget);

    if (this.targetHidden && distance > SHOW_TARGET_ABOVE) {
      this.targetHidden = false;
    } else if (!this.targetHidden && distance < HIDE_TARGET_BELOW) {
      this.targetHidden = true;
    }
  }

  private applyOrbitInput(deltaTime: number, input: InputController): void {
    this.orbitInput.copy(input.orbitDelta);
    const keyboardYaw = input.getKeyboardOrbitYaw();
    const keyboardPitch = input.getKeyboardOrbitPitch();
    const pitchSign = this.invertPitch ? -1 : 1;
    const sensitivity = ORBIT_RADIANS_PER_SCREEN * this.orbitSensitivity;

    const yawChange =
      this.orbitInput.x * sensitivity
      + keyboardYaw * KEYBOARD_ORBIT_SPEED * deltaTime;
    const pitchChange =
      (this.orbitInput.y * sensitivity
        + keyboardPitch * KEYBOARD_ORBIT_SPEED * deltaTime)
      * pitchSign;

    this.yaw -= yawChange;
    this.pitch = MathUtils.clamp(
      this.pitch - pitchChange,
      this.minPitch,
      this.maxPitch,
    );

    if (yawChange !== 0 || pitchChange !== 0) {
      this.manualOrbitHold = MANUAL_ORBIT_HOLD_SECONDS;
    } else {
      this.manualOrbitHold = Math.max(0, this.manualOrbitHold - deltaTime);
    }
  }

  private applyAutoFollow(deltaTime: number, target: CameraTarget): void {
    if (this.manualOrbitHold > 0 || target.movementState === 'Idle') {
      return;
    }

    const desiredYaw = Math.atan2(
      -target.facingDirection.x,
      -target.facingDirection.z,
    );
    const shortestTurn = MathUtils.euclideanModulo(
      desiredYaw - this.yaw + Math.PI,
      Math.PI * 2,
    ) - Math.PI;

    this.yaw += shortestTurn
      * (1 - Math.exp(-this.autoFollowResponsiveness * deltaTime));
  }

  private calculateDesiredPosition(): void {
    const horizontalDistance = Math.cos(this.pitch) * this.distance;
    const verticalDistance = Math.sin(this.pitch) * this.distance;

    this.occlusionOrigin.set(
      this.anchor.x,
      this.anchor.y + this.lookTargetHeight,
      this.anchor.z,
    );
    this.desiredPosition.set(
      this.anchor.x + Math.sin(this.yaw) * horizontalDistance,
      this.anchor.y + 1.15 + verticalDistance,
      this.anchor.z + Math.cos(this.yaw) * horizontalDistance,
    );

    const clearFraction = findSegmentObstruction(
      this.occlusionOrigin,
      this.desiredPosition,
      OCCLUSION_PADDING,
      this.collisionWorld,
    );

    if (clearFraction >= 1) {
      return;
    }

    const fullDistance = this.occlusionOrigin.distanceTo(this.desiredPosition);
    const clearedDistance = Math.min(
      Math.max(fullDistance * clearFraction, MIN_OCCLUDED_DISTANCE),
      fullDistance,
    );

    this.desiredPosition.lerpVectors(
      this.occlusionOrigin,
      this.desiredPosition,
      fullDistance > 0 ? clearedDistance / fullDistance : 1,
    );
  }

  private updateLookTarget(): void {
    this.lookTarget.copy(this.anchor);
    this.lookTarget.y += this.lookTargetHeight;
  }

  private updateFieldOfView(
    deltaTime: number,
    movementState: MovementState,
  ): void {
    const desired =
      movementState === 'Running'
        ? RUNNING_FIELD_OF_VIEW
        : WALKING_FIELD_OF_VIEW;

    this.fieldOfView = MathUtils.lerp(
      this.fieldOfView,
      desired,
      1 - Math.exp(-3 * deltaTime),
    );

    if (Math.abs(this.camera.fov - this.fieldOfView) > 0.01) {
      this.camera.fov = this.fieldOfView;
      this.camera.updateProjectionMatrix();
    }
  }
}
