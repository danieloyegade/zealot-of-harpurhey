import {
  BoxGeometry,
  CircleGeometry,
  ConeGeometry,
  CylinderGeometry,
  Group,
  MathUtils,
  Matrix4,
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
import { crossedFootfall } from './footfall';
import {
  moveCircleWithCollisions,
  resolveCircleOverlaps,
  type CollisionWorld,
} from '../world/collision';
import { PLAYER_START } from '../world/worldLayout';

export type MovementState = 'Idle' | 'Walking' | 'Running' | 'Riding';

/**
 * What the player needs from a vehicle to sit on it. Sagittal points are in
 * the vehicle's own plane: x forward, y up, metres from its ground origin.
 */
export interface RiderPose {
  /** World frame the rider sits in; its -Z is the vehicle's forward. */
  readonly mount: Object3D;
  readonly hip: Vector2;
  readonly grip: Vector2;
  readonly leftPedal: Vector2;
  readonly rightPedal: Vector2;
  /** 0 when coasting, 1 when driving the pedals. */
  readonly pedalling: number;
}

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
  'spine',
  'neck',
] as const;

// Rest-pose rig measurements (player-character-rigged.glb), metres.
const RIG_HIP_HEIGHT = 0.965;
const RIG_SPINE_PIVOT_ABOVE_HIP = 0.115;
const RIG_SHOULDER_ABOVE_SPINE = 0.338;
const RIG_THIGH = 0.505;
const RIG_SHIN_TO_ANKLE = 0.35;
const RIG_UPPER_ARM = 0.275;
const RIG_FOREARM_TO_GRIP = 0.33;
// The ball of the foot, not the ankle, sits on the pedal.
const ANKLE_ABOVE_PEDAL = 0.085;
const ANKLE_BEHIND_PEDAL = 0.045;
const RIDING_TORSO_LEAN = 0.34;
const MOUNT_SECONDS = 0.38;

const WALKING_SPEED = 2.4;
// Slower than this the figure is shuffling against something, not stepping.
const FOOTFALL_MINIMUM_SPEED = 0.8;
const RUNNING_SPEED = 4.5;

// Dev builds used to walk and run faster than the real game, which meant every
// tuning session judged a pace players never feel. The multipliers now only
// apply behind ?fast=on.
const FAST_WALKING_SPEED_MULTIPLIER = 1.3;
const FAST_RUNNING_SPEED_MULTIPLIER = 1.7;

function fastTraversalRequested(): boolean {
  if (!import.meta.env.DEV || typeof window === 'undefined') {
    return false;
  }
  return new URLSearchParams(window.location.search).get('fast') === 'on';
}

const SPEED_MULTIPLIER_APPLIES = fastTraversalRequested();

// Reaching speed and stopping both want to feel immediate: about 0.1 s to full
// pace and 0.08 s to a stop, with a snap that kills the last crawl so releasing
// a key never leaves the figure drifting.
const ACCELERATION_RESPONSIVENESS = 20;
const DECELERATION_RESPONSIVENESS = 26;
const RESIDUAL_SPEED_SNAP = 0.12;
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
    SPEED_MULTIPLIER_APPLIES ? FAST_WALKING_SPEED_MULTIPLIER : 1
  );
  readonly runningSpeed = RUNNING_SPEED * (
    SPEED_MULTIPLIER_APPLIES ? FAST_RUNNING_SPEED_MULTIPLIER : 1
  );
  readonly collisionRadius = 0.38;

  movementState: MovementState = 'Idle';
  /** Called each time a foot lands while the player is actually moving. */
  onFootfall: ((running: boolean) => void) | null = null;

  private readonly movementAxes = new Vector2();
  private readonly latchedAxes = new Vector2();
  private readonly latchedForward = new Vector3(0, 0, -1);
  private hasLatchedBasis = false;
  private readonly movementDirection = new Vector3();
  private readonly cameraRight = new Vector3();
  private readonly targetVelocity = new Vector3();
  private readonly velocity = new Vector3();
  private readonly frameMovement = new Vector3();
  private readonly previousPosition = new Vector3();
  private readonly targetRotation = new Quaternion();
  private characterVisible = true;
  private characterVisual?: Group;
  private fallbackFigure?: Group;
  private readonly bones = new Map<string, AnimatedBone>();
  private readonly swingQuaternion = new Quaternion();
  private animationTime = 0;
  private stridePhase = 0;
  private strideBlend = 0;
  private contactShadow?: Mesh;
  private riding = false;
  private mountBlend = 0;
  private readonly mountStartPosition = new Vector3();
  private readonly mountStartRotation = new Quaternion();
  private readonly mountMatrix = new Matrix4();
  private readonly mountPosition = new Vector3();
  private readonly mountRotation = new Quaternion();
  private readonly mountScale = new Vector3();
  private readonly limbDelta = new Vector2();
  private readonly limbJoint = new Vector2();

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

  /** Keep the lens out of the figure when a wall retracts the camera boom. */
  updateCameraVisibility(cameraPosition: Vector3): void {
    const distance = Math.hypot(
      cameraPosition.x - this.position.x,
      cameraPosition.y - (this.position.y + 1.6),
      cameraPosition.z - this.position.z,
    );
    // Hysteresis avoids flicker at the boundary; the grounding shadow stays.
    this.characterVisible = distance >= (this.characterVisible ? 1.7 : 1.95);
    if (this.characterVisual) this.characterVisual.visible = this.characterVisible;
    if (this.fallbackFigure) this.fallbackFigure.visible = this.characterVisible;
  }

  recoverFromCollisionOverlap(): void {
    resolveCircleOverlaps(
      this.position,
      this.collisionRadius,
      this.collisionWorld,
    );
  }

  get isRiding(): boolean {
    return this.riding;
  }

  /** Hands the player to a vehicle; `updateRiding` drives them from now on. */
  beginRiding(): void {
    this.riding = true;
    this.mountBlend = 0;
    this.velocity.set(0, 0, 0);
    this.movementState = 'Riding';
    this.mountStartPosition.copy(this.position);
    this.mountStartRotation.copy(this.object.quaternion);
    if (this.contactShadow) this.contactShadow.visible = false;
  }

  /** Puts the player back on foot at `position`, facing `facing`. */
  endRiding(position: Vector3, facing: Vector3): void {
    this.riding = false;
    this.movementState = 'Idle';
    this.position.set(position.x, 0, position.z);
    this.recoverFromCollisionOverlap();
    this.facingDirection.set(facing.x, 0, facing.z).normalize();
    this.object.quaternion.setFromAxisAngle(
      UP,
      Math.atan2(-this.facingDirection.x, -this.facingDirection.z),
    );
    if (this.contactShadow) this.contactShadow.visible = true;
    if (this.characterVisual) this.characterVisual.position.set(0, 0, 0);
    this.strideBlend = 0;
    for (const name of ANIMATED_BONES) this.setBoneSwing(name, 0);
  }

  /** Seats the player in `pose.mount` and poses legs on the pedals, hands on the grips. */
  updateRiding(deltaTime: number, pose: RiderPose, facing: Vector3): void {
    this.mountBlend = Math.min(1, this.mountBlend + deltaTime / MOUNT_SECONDS);
    const blend = MathUtils.smoothstep(this.mountBlend, 0, 1);

    this.mountMatrix.copy(pose.mount.matrixWorld);
    this.mountMatrix.decompose(this.mountPosition, this.mountRotation, this.mountScale);
    this.position.lerpVectors(this.mountStartPosition, this.mountPosition, blend);
    this.object.quaternion.slerpQuaternions(this.mountStartRotation, this.mountRotation, blend);
    this.facingDirection.copy(facing);
    this.animationTime += deltaTime;

    if (!this.characterVisual) return;
    // Mount frame: forward is -Z, so the hip's sagittal x maps to -z.
    this.characterVisual.position.set(
      0,
      (pose.hip.y - RIG_HIP_HEIGHT) * blend,
      -pose.hip.x * blend,
    );

    const lean = RIDING_TORSO_LEAN * (0.85 + 0.15 * pose.pedalling);
    this.setBoneSwing('spine', -lean * blend);
    this.setBoneSwing('neck', lean * 0.75 * blend);

    this.solveLeg('thigh_L', 'shin_L', pose.hip, pose.leftPedal, blend);
    this.solveLeg('thigh_R', 'shin_R', pose.hip, pose.rightPedal, blend);

    // Shoulder position once the torso has leaned forward about the spine.
    const pivotX = pose.hip.x;
    const pivotY = pose.hip.y + RIG_SPINE_PIVOT_ABOVE_HIP;
    const shoulderX = pivotX + Math.sin(lean) * RIG_SHOULDER_ABOVE_SPINE;
    const shoulderY = pivotY + Math.cos(lean) * RIG_SHOULDER_ABOVE_SPINE;
    this.solveTwoBone(shoulderX, shoulderY, pose.grip.x, pose.grip.y, RIG_UPPER_ARM, RIG_FOREARM_TO_GRIP);
    // A leaned chest swings a hanging arm backwards by the same angle.
    const upperArm = (this.limbJoint.x + lean) * blend;
    const forearm = this.limbJoint.y * blend;
    this.setBoneSwing('upperarm_L', upperArm);
    this.setBoneSwing('upperarm_R', upperArm);
    this.setBoneSwing('forearm_L', forearm);
    this.setBoneSwing('forearm_R', forearm);

    this.setBoneSwing('helper_trouser_hem_L', 0);
    this.setBoneSwing('helper_trouser_hem_R', 0);
    this.setBoneSwing('helper_jacket_hem', 0.35 * blend);
  }

  private solveLeg(
    thigh: string,
    shin: string,
    hip: Vector2,
    pedal: Vector2,
    blend: number,
  ): void {
    this.solveTwoBone(
      hip.x,
      hip.y,
      pedal.x - ANKLE_BEHIND_PEDAL,
      pedal.y + ANKLE_ABOVE_PEDAL,
      RIG_THIGH,
      RIG_SHIN_TO_ANKLE,
      true,
    );
    this.setBoneSwing(thigh, this.limbJoint.x * blend);
    this.setBoneSwing(shin, this.limbJoint.y * blend);
  }

  /**
   * Planar two-bone IK from a joint to a target, both in (forward, up).
   * Writes into `limbJoint`: x is the first bone's forward swing from hanging
   * straight down, y is the second bone's swing relative to the first.
   * Knees bend forward (second bone swings back); elbows bend back.
   */
  private solveTwoBone(
    rootX: number,
    rootY: number,
    targetX: number,
    targetY: number,
    upper: number,
    lower: number,
    kneeForward = false,
  ): void {
    this.limbDelta.set(targetX - rootX, targetY - rootY);
    const reach = MathUtils.clamp(this.limbDelta.length(), Math.abs(upper - lower) + 0.01, upper + lower - 0.005);
    const towardTarget = Math.atan2(this.limbDelta.x, -this.limbDelta.y);
    const rootBend = Math.acos(
      MathUtils.clamp((upper * upper + reach * reach - lower * lower) / (2 * upper * reach), -1, 1),
    );
    const jointInterior = Math.acos(
      MathUtils.clamp((upper * upper + lower * lower - reach * reach) / (2 * upper * lower), -1, 1),
    );
    const jointBend = Math.PI - jointInterior;
    if (kneeForward) {
      this.limbJoint.set(towardTarget + rootBend, -jointBend);
    } else {
      this.limbJoint.set(towardTarget - rootBend, jointBend);
    }
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

    this.updateLatchedBasis(input, cameraForward);
    this.cameraRight.set(-this.latchedForward.z, 0, this.latchedForward.x);
    this.movementDirection
      .copy(this.latchedForward)
      .multiplyScalar(this.movementAxes.y)
      .addScaledVector(this.cameraRight, this.movementAxes.x);

    if (this.movementDirection.lengthSq() > 0) {
      this.movementDirection.normalize();
    }

    const isMoving = this.movementDirection.lengthSq() > 0;
    const speed = input.isRunning ? this.runningSpeed : this.walkingSpeed;
    this.targetVelocity.copy(this.movementDirection).multiplyScalar(speed);

    const responsiveness = isMoving
      ? ACCELERATION_RESPONSIVENESS
      : DECELERATION_RESPONSIVENESS;
    const velocityBlend = 1 - Math.exp(-responsiveness * deltaTime);
    this.velocity.lerp(this.targetVelocity, velocityBlend);

    if (!isMoving && this.velocity.lengthSq() < RESIDUAL_SPEED_SNAP ** 2) {
      this.velocity.set(0, 0, 0);
    }

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
    // The figure faces where the player steered, not where a wall pushed it:
    // brushing a wall used to swing it round to run along the wall.
    if (isMoving) {
      this.facingDirection.copy(this.movementDirection);
      this.faceAlongFacingDirection(deltaTime);
    }
    // Discard the velocity a wall absorbed, so pressing into one and turning
    // away does not carry stale momentum back into the slide.
    if (deltaTime > 0 && this.frameMovement.lengthSq() < intendedDistanceSquared) {
      this.velocity.copy(this.frameMovement).divideScalar(deltaTime);
    }

    this.movementState = isMoving
      ? input.isRunning
        ? 'Running'
        : 'Walking'
      : 'Idle';

    this.updateCharacterAnimation(deltaTime);
  }

  /**
   * Holds the movement basis still while a direction is held down.
   *
   * Movement is camera-relative, so a camera that turns on its own would keep
   * redefining "forward" under a held key and bend a straight walk into a
   * curve. The basis is therefore captured when input starts and re-captured
   * only when the player changes it themselves: a different set of keys, or
   * their own orbiting. A camera moving for any other reason, such as easing
   * past a building, cannot steer the player.
   */
  private updateLatchedBasis(input: InputController, cameraForward: Vector3): void {
    if (this.movementAxes.lengthSq() === 0) {
      this.hasLatchedBasis = false;
      this.latchedAxes.set(0, 0);
      return;
    }

    const playerTurnedCamera = input.orbitDelta.lengthSq() > 0;
    const axesChanged = !this.movementAxes.equals(this.latchedAxes);

    if (!this.hasLatchedBasis || axesChanged || playerTurnedCamera) {
      this.latchedForward.copy(cameraForward);
      this.latchedAxes.copy(this.movementAxes);
      this.hasLatchedBasis = true;
    }
  }

  private faceAlongFacingDirection(deltaTime: number): void {
    this.targetRotation.setFromAxisAngle(
      UP,
      Math.atan2(-this.facingDirection.x, -this.facingDirection.z),
    );
    this.object.quaternion.slerp(
      this.targetRotation,
      1 - Math.exp(-12 * deltaTime),
    );
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
      const previousPhase = this.stridePhase;
      this.stridePhase += deltaTime * (isRunning ? 11.5 : 7.5);
      // Pressing into a wall keeps the legs going but not the feet landing.
      if (
        crossedFootfall(previousPhase, this.stridePhase)
        && this.velocity.lengthSq() > FOOTFALL_MINIMUM_SPEED ** 2
      ) {
        this.onFootfall?.(isRunning);
      }
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
    this.contactShadow = contactShadow;
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
