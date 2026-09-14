import {
  BoxGeometry,
  CircleGeometry,
  ConeGeometry,
  CylinderGeometry,
  Group,
  Mesh,
  MeshStandardMaterial,
  Object3D,
  MeshBasicMaterial,
  Quaternion,
  SphereGeometry,
  Vector2,
  Vector3,
} from 'three';
import type { InputController } from '../input/InputController';
import { loadModel } from '../world/loadModel';
import {
  moveCircleWithCollisions,
  resolveCircleOverlaps,
  type CollisionWorld,
} from '../world/collision';
import { PLAYER_START } from '../world/worldLayout';

export type MovementState = 'Idle' | 'Walking' | 'Running';

type AnimatedBone = {
  bone: Object3D;
  /** Rest-pose local rotation, which every frame's swing is applied on top of. */
  rest: Quaternion;
  /**
   * The character's own +X axis, expressed in this bone's rest-local frame.
   *
   * Bone local axes depend on rest orientation and roll, so a raw euler means
   * nothing you can reason about — the sign that swings a thigh forward tips
   * the spine backward. Resolving the axis once at load lets the walk cycle be
   * written in plain "degrees forward" terms. Positive rotation about it swings
   * a downward-pointing limb forward (the model faces -Z).
   */
  axis: Vector3;
};

const UP = new Vector3(0, 1, 0);
const ANIMATED_BONES = [
  'thigh_L',
  'thigh_R',
  'shin_L',
  'shin_R',
  'upperarm_L',
  'upperarm_R',
  'forearm_L',
  'forearm_R',
  'helper_trouser_hem_L',
  'helper_trouser_hem_R',
  'helper_jacket_hem',
] as const;

const WALKING_SPEED = 2.4;
const RUNNING_SPEED = 4.5;
const DEVELOPMENT_WALKING_SPEED_MULTIPLIER = 1.3;
const DEVELOPMENT_RUNNING_SPEED_MULTIPLIER = 1.7;
const PLAYER_INDIRECT_VISIBILITY_GAIN = 1.55;
const PLAYER_VISIBILITY_SHADER_KEY = 'player-indirect-visibility-v1';

function needsPlayerVisibilityLift(material: MeshStandardMaterial): boolean {
  const name = material.name;
  return (
    (name.startsWith('PC_Denim_') && name !== 'PC_Denim_Hardware') ||
    (name.startsWith('PC_Leather_') && name !== 'PC_Leather_Hardware') ||
    name === 'PC_Hair_Cornrow'
  );
}

/**
 * Preserve the authored near-black clothing while lifting only its indirect
 * response. Direct sodium/fluorescent/cold light remains untouched, so public
 * pools still change the character rather than a self-lit emissive floor doing
 * the work everywhere.
 */
function applyPlayerVisibilityPolicy(character: Group): void {
  const configured = new Set<MeshStandardMaterial>();

  character.traverse((child) => {
    if (!(child instanceof Mesh)) {
      return;
    }
    const materials = Array.isArray(child.material)
      ? child.material
      : [child.material];

    for (const material of materials) {
      if (
        !(material instanceof MeshStandardMaterial) ||
        configured.has(material) ||
        !needsPlayerVisibilityLift(material)
      ) {
        continue;
      }

      configured.add(material);
      const previousOnBeforeCompile = material.onBeforeCompile;
      const previousProgramCacheKey = material.customProgramCacheKey();
      material.onBeforeCompile = (shader, renderer) => {
        previousOnBeforeCompile.call(material, shader, renderer);
        const anchor = '#include <lights_fragment_end>';
        if (!shader.fragmentShader.includes(anchor)) {
          return;
        }
        shader.fragmentShader = shader.fragmentShader.replace(
          anchor,
          `${anchor}\nreflectedLight.indirectDiffuse *= ${PLAYER_INDIRECT_VISIBILITY_GAIN.toFixed(2)};`,
        );
      };
      material.customProgramCacheKey = () =>
        `${previousProgramCacheKey}|${PLAYER_VISIBILITY_SHADER_KEY}`;
      material.needsUpdate = true;
    }
  });
}

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
  private characterVisual?: Group;
  private fallbackFigure?: Group;
  private readonly bones = new Map<string, AnimatedBone>();
  private readonly swingQuaternion = new Quaternion();
  private animationTime = 0;
  private stridePhase = 0;
  private strideBlend = 0;

  constructor(private readonly collisionWorld: CollisionWorld) {
    this.object.name = 'Player';
    this.object.position.set(PLAYER_START.x, 0, PLAYER_START.z);
    this.recoverFromCollisionOverlap();
    this.createGroundingShadow();
    this.fallbackFigure = this.createFallbackFigure();
    this.object.add(this.fallbackFigure);
    void this.loadCharacterAsset();
  }

  get position(): Vector3 {
    return this.object.position;
  }

  recoverFromCollisionOverlap(): void {
    resolveCircleOverlaps(
      this.position,
      this.collisionRadius,
      this.collisionWorld,
    );
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
    const intendedDistanceSquared = this.frameMovement.lengthSq();
    moveCircleWithCollisions(
      this.position,
      this.frameMovement,
      this.collisionRadius,
      this.collisionWorld,
    );
    this.position.y = 0;

    this.frameMovement.subVectors(this.position, this.previousPosition);
    // Discard the velocity a wall absorbed, so pressing into one and turning
    // away does not carry stale momentum back into the slide.
    if (deltaTime > 0 && this.frameMovement.lengthSq() < intendedDistanceSquared) {
      this.velocity.copy(this.frameMovement).divideScalar(deltaTime);
    }
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

    this.updateCharacterAnimation(deltaTime);
  }

  private async loadCharacterAsset(): Promise<void> {
    try {
      const character = await loadModel(
        'assets/models/player-character-rigged.glb',
      );
      applyPlayerVisibilityPolicy(character);
      character.name = 'Player character asset';
      this.characterVisual = character;
      this.object.add(character);
      this.object.updateWorldMatrix(true, true);
      this.captureRestPose(character);

      if (this.fallbackFigure) {
        this.object.remove(this.fallbackFigure);
        this.fallbackFigure = undefined;
      }
    } catch (error) {
      console.warn('Player character GLB failed to load; retaining fallback figure.', error);
    }
  }

  private captureRestPose(character: Group): void {
    const characterRotation = new Quaternion();
    character.getWorldQuaternion(characterRotation);
    const boneRotation = new Quaternion();

    for (const name of ANIMATED_BONES) {
      const bone = character.getObjectByName(name);
      if (!bone) {
        console.warn(`Player rig is missing the bone "${name}".`);
        continue;
      }
      bone.getWorldQuaternion(boneRotation);
      const axis = new Vector3(1, 0, 0)
        .applyQuaternion(characterRotation)
        .applyQuaternion(boneRotation.invert())
        .normalize();
      this.bones.set(name, {
        bone,
        rest: bone.quaternion.clone(),
        axis,
      });
    }
  }

  private updateCharacterAnimation(deltaTime: number): void {
    if (!this.characterVisual) {
      return;
    }

    this.animationTime += deltaTime;
    const isMoving = this.movementState !== 'Idle';
    const isRunning = this.movementState === 'Running';
    const targetBlend = isMoving ? 1 : 0;
    this.strideBlend += (targetBlend - this.strideBlend) * (1 - Math.exp(-9 * deltaTime));

    if (isMoving) {
      this.stridePhase += deltaTime * (isRunning ? 11.5 : 7.5);
    }

    const blend = this.strideBlend;
    const strideAmplitude = (isRunning ? 0.68 : 0.43) * blend;
    const stride = Math.sin(this.stridePhase) * strideAmplitude;
    // Knees only ever bend one way, so the lift is a rectified sine offset a
    // little behind the stride rather than a mirror of it.
    const kneeAmplitude = (isRunning ? 0.95 : 0.55) * blend;
    const leftKnee = Math.max(0, Math.sin(this.stridePhase - 0.9)) * kneeAmplitude;
    const rightKnee = Math.max(0, Math.sin(this.stridePhase - 0.9 + Math.PI)) * kneeAmplitude;

    this.setBoneSwing('thigh_L', stride);
    this.setBoneSwing('thigh_R', -stride);
    this.setBoneSwing('shin_L', -leftKnee);
    this.setBoneSwing('shin_R', -rightKnee);
    this.setBoneSwing('upperarm_L', -stride * 0.72);
    this.setBoneSwing('upperarm_R', stride * 0.72);
    this.setBoneSwing('forearm_L', -0.14 * blend - stride * 0.16);
    this.setBoneSwing('forearm_R', -0.14 * blend + stride * 0.16);
    // The jeans are enormous and heavy, so the hems trail the shin rather than
    // tracking it (asset brief section 18).
    this.setBoneSwing('helper_trouser_hem_L', stride * 0.22);
    this.setBoneSwing('helper_trouser_hem_R', -stride * 0.22);
    this.setBoneSwing('helper_jacket_hem', Math.sin(this.stridePhase * 2) * 0.06 * blend);

    const movingBob = Math.abs(Math.sin(this.stridePhase)) * (isRunning ? 0.045 : 0.025);
    const idleBreath = Math.sin(this.animationTime * 1.7) * 0.004;
    this.characterVisual.position.y = movingBob * blend + idleBreath * (1 - blend);
  }

  private setBoneSwing(name: string, radians: number): void {
    const entry = this.bones.get(name);
    if (!entry) {
      return;
    }
    this.swingQuaternion.setFromAxisAngle(entry.axis, radians);
    entry.bone.quaternion.copy(entry.rest).multiply(this.swingQuaternion);
  }

  private createGroundingShadow(): void {
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

  private createFallbackFigure(): Group {
    const fallback = new Group();
    fallback.name = 'Player load fallback';
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
    fallback.add(body);

    const shoulders = new Mesh(
      new BoxGeometry(0.8, 0.22, 0.3),
      bodyMaterial,
    );
    shoulders.position.y = 1.22;
    fallback.add(shoulders);

    const head = new Mesh(new SphereGeometry(0.27, 8, 6), headMaterial);
    head.position.y = 1.51;
    fallback.add(head);

    const facingMarker = new Mesh(
      new ConeGeometry(0.12, 0.36, 4),
      facingMaterial,
    );
    facingMarker.position.set(0, 1.08, -0.34);
    facingMarker.rotation.x = -Math.PI / 2;
    fallback.add(facingMarker);

    return fallback;
  }
}
