import { MathUtils, PerspectiveCamera, Vector2, Vector3 } from 'three';
import type { InputController } from '../input/InputController';
import type { MovementState } from '../player/PlayerController';
import {
  castSphereThroughObstacles,
  type CollisionWorld,
} from '../world/collision';

export interface CameraTarget {
  readonly position: Vector3;
  readonly facingDirection: Vector3;
  readonly movementState: MovementState;
}

const AUTO_FOLLOW_RESPONSIVENESS = 2.4;

// How long manual orbiting suppresses auto-follow, so the camera does not
// fight a player who is deliberately looking somewhere else.
const MANUAL_ORBIT_HOLD_SECONDS = 1.2;

// Height above the player's feet that the orbit boom swings around.
const ORBIT_PIVOT_HEIGHT = 1.15;

// Clearance kept between the lens and walls; comfortably wider than the
// 0.1 m near plane, so no wall face is ever sliced open on screen.
const CAMERA_COLLISION_RADIUS = 0.3;

// How quickly the boom extends again once an obstruction clears. Pulling in
// is instant, since easing it would let a wall pass between camera and player.
const OCCLUSION_RECOVERY_RESPONSIVENESS = 5;

export class ThirdPersonCamera {
  readonly distance = 6.8;
  readonly fieldOfView = 50;

  private yaw = 0;
  private pitch = 0.31;
  private readonly minPitch = 0.12;
  private readonly maxPitch = 0.62;
  private readonly orbitSensitivity = 0.004;
  private readonly followResponsiveness = 7;
  private manualOrbitHold = 0;
  private boomFraction = 1;
  private readonly orbitInput = new Vector2();
  private readonly desiredPosition = new Vector3();
  private readonly followPosition = new Vector3();
  private readonly pivot = new Vector3();
  private readonly lookTarget = new Vector3();

  constructor(
    private readonly camera: PerspectiveCamera,
    private readonly lookTargetHeight = 1.05,
    private readonly collisionWorld?: CollisionWorld,
  ) {
    camera.fov = this.fieldOfView;
    camera.updateProjectionMatrix();
  }

  setOrbit(yaw: number, pitch = 0.31): void {
    this.yaw = yaw;
    this.pitch = MathUtils.clamp(pitch, this.minPitch, this.maxPitch);
  }

  getPlanarForward(target: Vector3): Vector3 {
    return target.set(-Math.sin(this.yaw), 0, -Math.cos(this.yaw));
  }

  snapTo(playerPosition: Vector3): void {
    this.calculateDesiredPosition(playerPosition);
    this.followPosition.copy(this.desiredPosition);
    this.placeClearOfObstacles(0, playerPosition, true);
    this.updateLookTarget(playerPosition);
    this.camera.lookAt(this.lookTarget);
  }

  update(
    deltaTime: number,
    input: InputController,
    target: CameraTarget,
  ): void {
    this.orbitInput.copy(input.orbitDelta);
    this.yaw -= this.orbitInput.x * this.orbitSensitivity;
    this.pitch = MathUtils.clamp(
      this.pitch - this.orbitInput.y * this.orbitSensitivity,
      this.minPitch,
      this.maxPitch,
    );

    if (this.orbitInput.lengthSq() > 0) {
      this.manualOrbitHold = MANUAL_ORBIT_HOLD_SECONDS;
    } else {
      this.manualOrbitHold = Math.max(0, this.manualOrbitHold - deltaTime);
    }
    this.applyAutoFollow(deltaTime, target);

    this.calculateDesiredPosition(target.position);
    const followBlend = 1 - Math.exp(-this.followResponsiveness * deltaTime);
    this.followPosition.lerp(this.desiredPosition, followBlend);
    this.placeClearOfObstacles(deltaTime, target.position, false);

    this.updateLookTarget(target.position);
    this.camera.lookAt(this.lookTarget);
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

    // Movement is camera-relative, so chasing sideways or backwards travel
    // would make holding A run in a circle and S flip the controls. Only
    // travel heading away from the camera pulls it round.
    const forwardness = Math.max(0, Math.cos(shortestTurn));

    this.yaw += shortestTurn
      * forwardness
      * (1 - Math.exp(-AUTO_FOLLOW_RESPONSIVENESS * deltaTime));
  }

  /**
   * Keeps the smoothed follow position, but shortens the boom from the pivot
   * whenever a wall stands between it and the player, so orbiting beside a
   * building never puts the lens inside it.
   */
  private placeClearOfObstacles(
    deltaTime: number,
    playerPosition: Vector3,
    snap: boolean,
  ): void {
    this.pivot.set(
      playerPosition.x,
      playerPosition.y + ORBIT_PIVOT_HEIGHT,
      playerPosition.z,
    );
    const clearFraction = this.collisionWorld
      ? castSphereThroughObstacles(
          this.pivot,
          this.followPosition,
          CAMERA_COLLISION_RADIUS,
          this.collisionWorld,
        )
      : 1;

    if (snap || clearFraction < this.boomFraction) {
      this.boomFraction = clearFraction;
    } else {
      this.boomFraction += (clearFraction - this.boomFraction)
        * (1 - Math.exp(-OCCLUSION_RECOVERY_RESPONSIVENESS * deltaTime));
    }
    this.camera.position.lerpVectors(
      this.pivot,
      this.followPosition,
      this.boomFraction,
    );
  }

  private calculateDesiredPosition(playerPosition: Vector3): void {
    const horizontalDistance = Math.cos(this.pitch) * this.distance;
    const verticalDistance = Math.sin(this.pitch) * this.distance;

    this.desiredPosition.set(
      playerPosition.x + Math.sin(this.yaw) * horizontalDistance,
      playerPosition.y + ORBIT_PIVOT_HEIGHT + verticalDistance,
      playerPosition.z + Math.cos(this.yaw) * horizontalDistance,
    );
  }

  private updateLookTarget(playerPosition: Vector3): void {
    this.lookTarget.copy(playerPosition);
    this.lookTarget.y += this.lookTargetHeight;
  }
}
