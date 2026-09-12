import {
  BoxGeometry,
  CircleGeometry,
  ConeGeometry,
  CylinderGeometry,
  Group,
  Mesh,
  MeshStandardMaterial,
  MeshBasicMaterial,
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
import { PLAYER_START } from '../world/worldLayout';

export type MovementState = 'Idle' | 'Walking' | 'Running';

const UP = new Vector3(0, 1, 0);
const WALKING_SPEED = 2.4;
const RUNNING_SPEED = 4.5;
const DEVELOPMENT_WALKING_SPEED_MULTIPLIER = 1.3;
const DEVELOPMENT_RUNNING_SPEED_MULTIPLIER = 1.7;

export class PlayerController {
  readonly object = new Group();
  readonly facingDirection = new Vector3(0, 0, -1);
  readonly walkingSpeed = WALKING_SPEED * (
    import.meta.env.DEV ? DEVELOPMENT_WALKING_SPEED_MULTIPLIER : 1
  );
  readonly runningSpeed = RUNNING_SPEED * (
    import.meta.env.DEV ? DEVELOPMENT_RUNNING_SPEED_MULTIPLIER : 1
  );
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
    this.object.position.set(PLAYER_START.x, 0, PLAYER_START.z);
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

    // Face where the player is steering, not where collision let them go.
    // Deriving facing from the resolved movement made the figure turn to run
    // along a wall it was pushed against, instead of facing into it.
    if (isMoving) {
      this.facingDirection.copy(this.movementDirection);
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
      color: 0x303644,
      roughness: 1,
    });
    const headMaterial = new MeshStandardMaterial({
      color: 0x686a70,
      roughness: 1,
    });
    const facingMaterial = new MeshStandardMaterial({
      color: 0x192038,
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

    // The player is the one figure the eye tracks, so it casts into the
    // moonlight shadow map. The fake contact shadow below stays: it is the
    // only grounding cue on quality profiles where shadows are disabled.
    for (const part of [body, shoulders, head, facingMarker]) {
      part.castShadow = true;
      part.receiveShadow = true;
    }

    const contactShadow = new Mesh(
      new CircleGeometry(0.48, 12),
      new MeshBasicMaterial({
        color: 0x030407,
        transparent: true,
        opacity: 0.5,
        depthWrite: false,
      }),
    );
    contactShadow.name = 'Player grounding shadow';
    contactShadow.rotation.x = -Math.PI / 2;
    contactShadow.position.y = 0.025;
    this.object.add(contactShadow);
  }
}
