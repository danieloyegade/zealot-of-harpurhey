import { MathUtils, PerspectiveCamera, Vector2, Vector3 } from 'three';
import type { InputController } from '../input/InputController';

export class ThirdPersonCamera {
  readonly distance = 6.8;
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

  constructor(
    private readonly camera: PerspectiveCamera,
    private readonly lookTargetHeight = 1.05,
  ) {
    camera.fov = this.fieldOfView;
    camera.updateProjectionMatrix();
  }

  getPlanarForward(target: Vector3): Vector3 {
    return target.set(-Math.sin(this.yaw), 0, -Math.cos(this.yaw));
  }

  snapTo(playerPosition: Vector3): void {
    this.calculateDesiredPosition(playerPosition);
    this.camera.position.copy(this.desiredPosition);
    this.updateLookTarget(playerPosition);
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

    this.calculateDesiredPosition(playerPosition);
    const followBlend = 1 - Math.exp(-this.followResponsiveness * deltaTime);
    this.camera.position.lerp(this.desiredPosition, followBlend);

    this.updateLookTarget(playerPosition);
    this.camera.lookAt(this.lookTarget);
  }

  private calculateDesiredPosition(playerPosition: Vector3): void {
    const horizontalDistance = Math.cos(this.pitch) * this.distance;
    const verticalDistance = Math.sin(this.pitch) * this.distance;

    this.desiredPosition.set(
      playerPosition.x + Math.sin(this.yaw) * horizontalDistance,
      playerPosition.y + 1.15 + verticalDistance,
      playerPosition.z + Math.cos(this.yaw) * horizontalDistance,
    );
  }

  private updateLookTarget(playerPosition: Vector3): void {
    this.lookTarget.copy(playerPosition);
    this.lookTarget.y += this.lookTargetHeight;
  }
}
