import { MathUtils, PerspectiveCamera, Vector2, Vector3 } from 'three';
import type { InputController } from '../input/InputController';
import { castAgainstObstacles, type CollisionWorld } from '../world/collision';

const DEFAULT_DISTANCE = 6.8;
const MINIMUM_DISTANCE = 2.5;
const MAXIMUM_DISTANCE = 12;
const ZOOM_METRES_PER_NOTCH = 0.9;

/**
 * Height of the point the camera orbits around. Kept separate from the look
 * target height so the existing framing is preserved: the orbit pivot is a
 * fixed property of the camera rig, while the look target is per-view.
 */
const ORBIT_PIVOT_HEIGHT = 1.15;

/**
 * Padding applied to every obstacle when probing for occlusion. Slightly wider
 * than the camera near plane so walls never clip through the frame edge.
 */
const OCCLUSION_PADDING = 0.34;

/**
 * The camera snaps inward the instant geometry intrudes, then eases back out.
 * Easing outward stops doorways and railings from flicking the camera around.
 */
const RECOVERY_RESPONSIVENESS = 4;

export class ThirdPersonCamera {
  readonly fieldOfView = 50;

  private yaw = 0;
  private pitch = 0.31;
  private readonly minPitch = 0.12;
  private readonly maxPitch = 0.62;
  private readonly orbitSensitivity = 0.004;
  private readonly followResponsiveness = 7;
  private readonly orbitInput = new Vector2();
  private readonly desiredPosition = new Vector3();
  private readonly lookTarget = new Vector3();
  private readonly orbitPivot = new Vector3();
  private readonly probeDirection = new Vector3();

  /** Distance the player has asked for with the scroll wheel. */
  private requestedDistance = DEFAULT_DISTANCE;
  /** Distance actually in use once occlusion has been resolved. */
  private currentDistance = DEFAULT_DISTANCE;

  constructor(
    private readonly camera: PerspectiveCamera,
    private readonly collisionWorld: CollisionWorld,
    private readonly lookTargetHeight = 1.05,
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
    this.updateTargets(playerPosition);
    this.currentDistance = this.resolveUnoccludedDistance(this.requestedDistance);
    this.calculateDesiredPosition(this.currentDistance);
    this.camera.position.copy(this.desiredPosition);
    this.camera.lookAt(this.lookTarget);
  }

  update(
    deltaTime: number,
    input: InputController,
    playerPosition: Vector3,
  ): void {
    this.orbitInput.copy(input.orbitDelta);
    this.yaw -= this.orbitInput.x * this.orbitSensitivity;
    this.pitch = MathUtils.clamp(
      this.pitch - this.orbitInput.y * this.orbitSensitivity,
      this.minPitch,
      this.maxPitch,
    );

    const zoomNotches = input.consumeZoomDelta();
    if (zoomNotches !== 0) {
      this.requestedDistance = MathUtils.clamp(
        this.requestedDistance + zoomNotches * ZOOM_METRES_PER_NOTCH,
        MINIMUM_DISTANCE,
        MAXIMUM_DISTANCE,
      );
    }

    this.updateTargets(playerPosition);

    const allowedDistance = this.resolveUnoccludedDistance(this.requestedDistance);
    if (allowedDistance < this.currentDistance) {
      this.currentDistance = allowedDistance;
    } else {
      this.currentDistance = MathUtils.lerp(
        this.currentDistance,
        allowedDistance,
        1 - Math.exp(-RECOVERY_RESPONSIVENESS * deltaTime),
      );
    }

    this.calculateDesiredPosition(this.currentDistance);
    const followBlend = 1 - Math.exp(-this.followResponsiveness * deltaTime);
    this.camera.position.lerp(this.desiredPosition, followBlend);

    this.camera.lookAt(this.lookTarget);
  }

  /**
   * Probes from the orbit pivot toward where the camera wants to sit and
   * returns the distance it may actually occupy. `orbitPivot` must be current.
   */
  private resolveUnoccludedDistance(requestedDistance: number): number {
    const travelled = castAgainstObstacles(
      this.orbitPivot,
      this.probeDirection,
      requestedDistance,
      OCCLUSION_PADDING,
      this.collisionWorld,
    );

    return Math.max(MINIMUM_DISTANCE * 0.6, travelled);
  }

  /**
   * Placed along the probe ray so the position the camera moves to is exactly
   * the position that was tested for occlusion.
   */
  private calculateDesiredPosition(distance: number): void {
    this.desiredPosition
      .copy(this.orbitPivot)
      .addScaledVector(this.probeDirection, distance);
  }

  /**
   * Refreshes the orbit pivot, look target and probe direction for the current
   * player position and orbit angles. Must run before the occlusion probe and
   * before the desired position is derived.
   */
  private updateTargets(playerPosition: Vector3): void {
    this.lookTarget.copy(playerPosition);
    this.lookTarget.y += this.lookTargetHeight;

    this.orbitPivot.copy(playerPosition);
    this.orbitPivot.y += ORBIT_PIVOT_HEIGHT;

    // Already unit length: cos(pitch)^2 + sin(pitch)^2 = 1.
    const horizontal = Math.cos(this.pitch);
    this.probeDirection.set(
      Math.sin(this.yaw) * horizontal,
      Math.sin(this.pitch),
      Math.cos(this.yaw) * horizontal,
    );
  }
}
