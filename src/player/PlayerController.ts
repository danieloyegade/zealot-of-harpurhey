import {
  BoxGeometry,
  ConeGeometry,
  CylinderGeometry,
  Group,
  Mesh,
  MeshStandardMaterial,
  Quaternion,
  SphereGeometry,
  Vector2,
  Vector3,
} from 'three';
import type { InputController } from '../input/InputController';
import {
  moveCircleWithCollisions,
  type CollisionWorld,
} from '../world/collision';

export type MovementState = 'Idle' | 'Walking' | 'Running';

const UP = new Vector3(0, 1, 0);

export class PlayerController {
  readonly object = new Group();
  readonly facingDirection = new Vector3(0, 0, -1);
  readonly walkingSpeed = 2.4;
  readonly runningSpeed = 4.5;
  readonly collisionRadius = 0.38;

  movementState: MovementState = 'Idle';

  private readonly movementAxes = new Vector2();
  private readonly movementDirection = new Vector3();
  private readonly cameraRight = new Vector3();
  private readonly targetVelocity = new Vector3();
  private readonly velocity = new Vector3();
  private readonly frameMovement = new Vector3();
  private readonly previousPosition = new Vector3();
  private readonly targetRotation = new Quaternion();

  constructor(private readonly collisionWorld: CollisionWorld) {
    this.object.name = 'Player';
    this.object.position.set(0, 0, 18);
    this.createPlaceholderFigure();
  }

  get position(): Vector3 {
    return this.object.position;
  }

  update(
    deltaTime: number,
    input: InputController,
    cameraForward: Vector3,
  ): void {
    input.getMovementAxes(this.movementAxes);

    if (this.movementAxes.lengthSq() > 1) {
      this.movementAxes.normalize();
    }

    this.cameraRight.set(-cameraForward.z, 0, cameraForward.x);
    this.movementDirection
      .copy(cameraForward)
      .multiplyScalar(this.movementAxes.y)
      .addScaledVector(this.cameraRight, this.movementAxes.x);

    if (this.movementDirection.lengthSq() > 0) {
      this.movementDirection.normalize();
    }

    const isMoving = this.movementDirection.lengthSq() > 0;
    const speed = input.isRunning ? this.runningSpeed : this.walkingSpeed;
    this.targetVelocity.copy(this.movementDirection).multiplyScalar(speed);

    const responsiveness = isMoving ? 8 : 11;
    const velocityBlend = 1 - Math.exp(-responsiveness * deltaTime);
    this.velocity.lerp(this.targetVelocity, velocityBlend);

    this.previousPosition.copy(this.position);
    this.frameMovement.copy(this.velocity).multiplyScalar(deltaTime);
    moveCircleWithCollisions(
      this.position,
      this.frameMovement,
      this.collisionRadius,
      this.collisionWorld,
    );
    this.position.y = 0;

    this.frameMovement.subVectors(this.position, this.previousPosition);
    if (this.frameMovement.lengthSq() > 0.000001) {
      this.facingDirection.copy(this.frameMovement).normalize();
      const facingAngle = Math.atan2(
        -this.facingDirection.x,
        -this.facingDirection.z,
      );
      this.targetRotation.setFromAxisAngle(UP, facingAngle);
      this.object.quaternion.slerp(
        this.targetRotation,
        1 - Math.exp(-12 * deltaTime),
      );
    }

    this.movementState = isMoving
      ? input.isRunning
        ? 'Running'
        : 'Walking'
      : 'Idle';
  }

  private createPlaceholderFigure(): void {
    const bodyMaterial = new MeshStandardMaterial({
      color: 0xd69b35,
      roughness: 1,
    });
    const headMaterial = new MeshStandardMaterial({
      color: 0xe2b06a,
      roughness: 1,
    });
    const facingMaterial = new MeshStandardMaterial({
      color: 0x371d16,
      roughness: 1,
    });

    const body = new Mesh(
      new CylinderGeometry(0.3, 0.36, 1.1, 8),
      bodyMaterial,
    );
    body.position.y = 0.75;
    this.object.add(body);

    const shoulders = new Mesh(
      new BoxGeometry(0.8, 0.22, 0.3),
      bodyMaterial,
    );
    shoulders.position.y = 1.22;
    this.object.add(shoulders);

    const head = new Mesh(new SphereGeometry(0.27, 8, 6), headMaterial);
    head.position.y = 1.51;
    this.object.add(head);

    const facingMarker = new Mesh(
      new ConeGeometry(0.12, 0.36, 4),
      facingMaterial,
    );
    facingMarker.position.set(0, 1.08, -0.34);
    facingMarker.rotation.x = -Math.PI / 2;
    this.object.add(facingMarker);
  }
}
