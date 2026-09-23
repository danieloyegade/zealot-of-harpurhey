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

// The game is in part a photo walk: most of the time the camera stands at a
// photographer's eye height with an almost level lens, so facades keep their
// verticals upright and read as architecture, the way a medium-format
// camera on a tripod would frame them (docs/creative-constitution.md).
export const DEFAULT_CAMERA_PITCH = 0.04;

// Height above the player's feet that the orbit boom swings around, and that
// the lens looks at. Looking at the pivot keeps the lens tilt equal to the
// boom pitch, so at rest the horizon sits level through the player's head.
export const ORBIT_PIVOT_HEIGHT = 1.6;

// A bike pulls the camera round behind its direction of travel immediately:
// it steers relative to itself, so following it can never bend the ride.
const RIDING_FOLLOW_RESPONSIVENESS = 2.4;

// Walking pulls the camera round too, but only once the walk has settled.
// Walking is camera-relative, so a camera that turned while the player was
// still steering would redefine "forward" under their hands. Two things make
// this safe: PlayerController latches the movement basis while a direction is
// held, so a camera turning on its own cannot bend the path into a circle
// (the old bug); and the short wait below means a tap or a quick correction
// is over before the lens moves. Hold a direction and the city comes round
// behind you almost at once.
// Kept short: at 1 s the lag read as the camera failing to keep up.
const WALK_FOLLOW_DELAY_SECONDS = 0.2;
// Brisk enough that the camera keeps pace with the walk rather than trailing
// it. Measured on a 45-degree diagonal: halfway round 0.6 s after the key goes
// down, 90% round by 1.7 s (the boom's own positional smoothing adds a little).
const WALK_FOLLOW_RESPONSIVENESS = 3;
// Any real change of direction is the player steering, and restarts the wait.
// Loose enough to ignore the jitter of a diagonal held against a kerb.
const WALK_FOLLOW_STEER_TOLERANCE = 0.05;

// How long manual orbiting suppresses auto-follow, so the camera does not
// fight a player who is deliberately looking somewhere else.
const MANUAL_ORBIT_HOLD_SECONDS = 1.2;

// After manual orbiting, the pitch drifts slowly back to the rest angle, so
// looking up at a roofline or down at a road marking is a glance, not a new
// default.
const PITCH_RETURN_DELAY_SECONDS = 2.5;
const PITCH_RETURN_RESPONSIVENESS = 0.9;

// Pressing C swings the camera behind the player over a fraction of a second,
// rather than cutting, so the new view stays legible.
const RECENTER_RESPONSIVENESS = 10;

// Clearance kept between the lens and walls; comfortably wider than the
// 0.1 m near plane, so no wall face is ever sliced open on screen.
const CAMERA_COLLISION_RADIUS = 0.3;

// The boom is otherwise allowed to shorten all the way onto the pivot when an
// obstruction is right at the player, but the pivot and the look target sit
// at the same point (both anchor + ORBIT_PIVOT_HEIGHT). A camera placed
// exactly there looks at its own position: lookAt() has nothing to aim at,
// the view matrix degenerates, and the screen goes black until the player
// turns away from the wall. Keeping the lens at least this far from the
// pivot guarantees a real look direction always exists.
const MINIMUM_BOOM_DISTANCE = 0.6;

// When a building stands between the player and the camera, the boom first
// rises a little, keeping its length, and is only cut short if that does not
// clear. Shortening the boom reads as an unasked-for zoom. The lift is capped
// so the eye-level framing is never traded for a view from above.
const OCCLUSION_LIFT_STEP = 0.05;
const OCCLUSION_LIFT_MAXIMUM = 0.35;
const OCCLUSION_LIFT_RISE_RESPONSIVENESS = 6;
const OCCLUSION_LIFT_FALL_RESPONSIVENESS = 1.2;
// Keeps the lift raised briefly after the obstruction clears, so walking past
// a row of buildings does not bob the camera at every gap between them.
const OCCLUSION_LIFT_HOLD_SECONDS = 0.8;

// How quickly the boom extends again once an obstruction clears. Pulling in
// is instant, since easing it would let a wall pass between camera and player.
const OCCLUSION_RECOVERY_RESPONSIVENESS = 2.5;

// Both the lens and the look target are driven from one smoothed anchor that
// chases the player. Driving them from different points makes the figure slide
// around the frame whenever it accelerates.
const ANCHOR_RESPONSIVENESS = 14;

// How quickly the boom eases to a new length, e.g. when mounting a bike.
const BOOM_LENGTH_RESPONSIVENESS = 1.5;

export class ThirdPersonCamera {
  readonly baseDistance = 5.6;
  private distance = this.baseDistance;
  private targetDistance = this.baseDistance;
  readonly fieldOfView = 56;
  private targetFieldOfView = this.fieldOfView;

  private yaw = 0;
  private pitch = DEFAULT_CAMERA_PITCH;
  private restPitch = DEFAULT_CAMERA_PITCH;
  private readonly minPitch = -0.12;
  private readonly maxPitch = 0.9;
  private readonly orbitSensitivity = 0.004;
  private readonly followResponsiveness = 7;
  private manualOrbitHold = 0;
  private pitchReturnDelay = 0;
  private recenterYaw: number | null = null;
  private steadyWalkSeconds = 0;
  private previousFacingYaw: number | null = null;
  private occlusionLift = 0;
  private occlusionLiftHold = 0;
  private boomFraction = 1;
  private readonly anchor = new Vector3();
  private readonly orbitInput = new Vector2();
  private readonly desiredPosition = new Vector3();
  private readonly followPosition = new Vector3();
  private readonly pivot = new Vector3();
  private readonly probe = new Vector3();
  private readonly lookTarget = new Vector3();

  constructor(
    private readonly camera: PerspectiveCamera,
    private readonly lookTargetHeight = ORBIT_PIVOT_HEIGHT,
    private readonly collisionWorld?: CollisionWorld,
  ) {
    camera.fov = this.fieldOfView;
    camera.updateProjectionMatrix();
  }

  /** Eases the boom to `metres`; faster travel wants more street ahead in frame. */
  setBoomLength(metres: number): void {
    this.targetDistance = metres;
  }

  /** Eases the lens to `degrees`; a wider view sells speed. */
  setFieldOfView(degrees: number): void {
    this.targetFieldOfView = degrees;
  }

  setOrbit(yaw: number, pitch = DEFAULT_CAMERA_PITCH): void {
    this.yaw = yaw;
    this.pitch = MathUtils.clamp(pitch, this.minPitch, this.maxPitch);
    this.restPitch = this.pitch;
  }

  getPlanarForward(target: Vector3): Vector3 {
    return target.set(-Math.sin(this.yaw), 0, -Math.cos(this.yaw));
  }

  snapTo(playerPosition: Vector3): void {
    this.anchor.copy(playerPosition);
    this.setPivot(this.anchor);
    this.occlusionLift = this.findOcclusionLift();
    this.calculateDesiredPosition(this.pitch + this.occlusionLift);
    this.followPosition.copy(this.desiredPosition);
    this.placeClearOfObstacles(0, true);
    this.updateLookTarget();
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
      this.pitchReturnDelay = PITCH_RETURN_DELAY_SECONDS;
      this.recenterYaw = null;
    } else {
      this.manualOrbitHold = Math.max(0, this.manualOrbitHold - deltaTime);
      this.applyPitchReturn(deltaTime);
    }

    if (input.consumeRecenter()) {
      this.recenterYaw = yawBehind(target.facingDirection);
    }
    this.applyRecenter(deltaTime);
    this.applyRidingFollow(deltaTime, target);
    this.applyWalkingFollow(deltaTime, target);

    const boomBlend = 1 - Math.exp(-BOOM_LENGTH_RESPONSIVENESS * deltaTime);
    this.distance += (this.targetDistance - this.distance) * boomBlend;
    if (Math.abs(this.targetFieldOfView - this.camera.fov) > 0.01) {
      this.camera.fov += (this.targetFieldOfView - this.camera.fov) * boomBlend;
      this.camera.updateProjectionMatrix();
    }

    this.anchor.lerp(
      target.position,
      1 - Math.exp(-ANCHOR_RESPONSIVENESS * deltaTime),
    );
    this.setPivot(this.anchor);
    this.updateOcclusionLift(deltaTime);
    this.calculateDesiredPosition(this.pitch + this.occlusionLift);
    const followBlend = 1 - Math.exp(-this.followResponsiveness * deltaTime);
    this.followPosition.lerp(this.desiredPosition, followBlend);
    this.placeClearOfObstacles(deltaTime, false);

    this.updateLookTarget();
    this.camera.lookAt(this.lookTarget);
  }

  private applyPitchReturn(deltaTime: number): void {
    if (this.pitchReturnDelay > 0) {
      this.pitchReturnDelay -= deltaTime;
      return;
    }
    this.pitch += (this.restPitch - this.pitch)
      * (1 - Math.exp(-PITCH_RETURN_RESPONSIVENESS * deltaTime));
  }

  private applyRecenter(deltaTime: number): void {
    if (this.recenterYaw === null) {
      return;
    }
    const turn = shortestAngle(this.recenterYaw - this.yaw);
    if (Math.abs(turn) < 0.002) {
      this.yaw = this.recenterYaw;
      this.recenterYaw = null;
      return;
    }
    this.yaw += turn * (1 - Math.exp(-RECENTER_RESPONSIVENESS * deltaTime));
  }

  private applyRidingFollow(deltaTime: number, target: CameraTarget): void {
    if (
      target.movementState !== 'Riding'
      || this.manualOrbitHold > 0
      || this.recenterYaw !== null
    ) {
      return;
    }
    const turn = shortestAngle(yawBehind(target.facingDirection) - this.yaw);
    this.yaw += turn * (1 - Math.exp(-RIDING_FOLLOW_RESPONSIVENESS * deltaTime));
  }

  /**
   * Eases the camera round behind a walk that has held its direction for
   * `WALK_FOLLOW_DELAY_SECONDS`, so a long walk ends up looking where the
   * player is going instead of stranding them at an angle to their own path.
   *
   * Steering, orbiting or recentring all restart the wait, so the lens only
   * ever moves after the player has stopped asking it to do anything else.
   */
  private applyWalkingFollow(deltaTime: number, target: CameraTarget): void {
    const facingYaw = yawBehind(target.facingDirection);
    const steered = this.previousFacingYaw !== null
      && Math.abs(shortestAngle(facingYaw - this.previousFacingYaw))
        > WALK_FOLLOW_STEER_TOLERANCE;
    this.previousFacingYaw = facingYaw;

    const onFoot = target.movementState === 'Walking'
      || target.movementState === 'Running';

    if (
      !onFoot
      || steered
      || this.manualOrbitHold > 0
      || this.recenterYaw !== null
    ) {
      this.steadyWalkSeconds = 0;
      return;
    }

    this.steadyWalkSeconds += deltaTime;
    if (this.steadyWalkSeconds < WALK_FOLLOW_DELAY_SECONDS) {
      return;
    }

    const turn = shortestAngle(facingYaw - this.yaw);
    this.yaw += turn * (1 - Math.exp(-WALK_FOLLOW_RESPONSIVENESS * deltaTime));
  }

  private updateOcclusionLift(deltaTime: number): void {
    const required = this.findOcclusionLift();

    if (required >= this.occlusionLift - 0.001) {
      this.occlusionLiftHold = OCCLUSION_LIFT_HOLD_SECONDS;
      this.occlusionLift += (required - this.occlusionLift)
        * (1 - Math.exp(-OCCLUSION_LIFT_RISE_RESPONSIVENESS * deltaTime));
    } else if (this.occlusionLiftHold > 0) {
      this.occlusionLiftHold -= deltaTime;
    } else {
      this.occlusionLift += (required - this.occlusionLift)
        * (1 - Math.exp(-OCCLUSION_LIFT_FALL_RESPONSIVENESS * deltaTime));
    }
  }

  /**
   * The smallest extra pitch, within the lift cap, at which the full-length
   * boom clears every obstacle. If none does, the one leaving the longest
   * clear boom.
   */
  private findOcclusionLift(): number {
    if (!this.collisionWorld) {
      return 0;
    }
    const headroom = Math.min(
      OCCLUSION_LIFT_MAXIMUM,
      Math.max(0, this.maxPitch - this.pitch),
    );
    let bestLift = 0;
    let bestFraction = -1;

    for (let lift = 0; lift <= headroom + 1e-6; lift += OCCLUSION_LIFT_STEP) {
      this.calculateDesiredPosition(this.pitch + lift, this.probe);
      const fraction = castSphereThroughObstacles(
        this.pivot,
        this.probe,
        CAMERA_COLLISION_RADIUS,
        this.collisionWorld,
      );
      if (fraction >= 1) {
        return lift;
      }
      if (fraction > bestFraction + 0.02) {
        bestFraction = fraction;
        bestLift = lift;
      }
    }
    return bestLift;
  }

  /**
   * Keeps the smoothed follow position, but shortens the boom from the pivot
   * whenever a wall still stands between it and the player, so the lens is
   * never inside a building while the lift is catching up.
   */
  private placeClearOfObstacles(deltaTime: number, snap: boolean): void {
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
    // Never let the lens reach the pivot itself: see MINIMUM_BOOM_DISTANCE.
    const minimumFraction = Math.min(1, MINIMUM_BOOM_DISTANCE / this.distance);
    this.camera.position.lerpVectors(
      this.pivot,
      this.followPosition,
      Math.max(this.boomFraction, minimumFraction),
    );
  }

  private setPivot(anchor: Vector3): void {
    this.pivot.set(anchor.x, anchor.y + ORBIT_PIVOT_HEIGHT, anchor.z);
  }

  private calculateDesiredPosition(
    pitch: number,
    target = this.desiredPosition,
  ): void {
    const horizontalDistance = Math.cos(pitch) * this.distance;
    const verticalDistance = Math.sin(pitch) * this.distance;

    target.set(
      this.pivot.x + Math.sin(this.yaw) * horizontalDistance,
      this.pivot.y + verticalDistance,
      this.pivot.z + Math.cos(this.yaw) * horizontalDistance,
    );
  }

  private updateLookTarget(): void {
    this.lookTarget.copy(this.anchor);
    this.lookTarget.y += this.lookTargetHeight;
  }
}

function yawBehind(facing: Vector3): number {
  return Math.atan2(-facing.x, -facing.z);
}

function shortestAngle(radians: number): number {
  return MathUtils.euclideanModulo(radians + Math.PI, Math.PI * 2) - Math.PI;
}
