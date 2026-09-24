import { MathUtils, Object3D, Quaternion, Vector2, Vector3 } from 'three';
import type { MovementState, RiderPose } from '../player/PlayerController';
import {
  moveCircleWithCollisions,
  resolveCircleOverlaps,
  type CollisionWorld,
  type OrientedBoxObstacle,
} from '../world/collision';

// Geometry measured from blender/scripts/createSterlingBikeBlockout.py, in the
// bike's own sagittal plane: x forward from the bike origin, y up.
const WHEEL_RADIUS = 0.355;
const WHEELBASE = 1.31;
const CRANK_CENTRE = new Vector2(-0.02, 0.30);
const CRANK_LENGTH = 0.17;
// Authored crank angles at rest: the drive (right, +Z) arm points forward-down.
const RIGHT_CRANK_REST = MathUtils.degToRad(-15);
const LEFT_CRANK_REST = RIGHT_CRANK_REST + Math.PI;
const RIDER_HIP = new Vector2(-0.235, 1.16);
const RIDER_GRIP = new Vector2(0.215, 1.255);

// E-assist fleet bikes are capped near 15.5 mph (6.9 m/s).
const CRUISE_SPEED = 4.6;
const ASSISTED_SPEED = 6.9;
const PEDAL_ACCELERATION = 2.1;
const ASSISTED_ACCELERATION = 3.0;
const BRAKE_DECELERATION = 5.5;
// Harder braking above assist speed, so a boosting bike stops within a street.
const HIGH_SPEED_BRAKE_DECELERATION = 12;
// Space boost: well past any real e-bike, a game-feel sprint. ~4.3x pedalling,
// ~45 mph. Faster than this the bike crosses the ~100 m city in seconds and
// can no longer turn into its streets.
const BOOST_SPEED = 20;
const BOOST_ACCELERATION = 9;
// Letting go of boost bleeds speed back down rather than stopping dead.
const OVER_SPEED_DECELERATION = 5;
const REVERSE_SPEED = 0.9;
const ROLLING_DRAG = 0.22;
const AIR_DRAG = 0.011;
const MAXIMUM_STEER_SLOW = 0.62;
const MAXIMUM_STEER_FAST = 0.13;
// Above assist speed, steering lock is limited by sideways grip instead, so a
// boosting bike carves wide arcs rather than snapping round.
const MAXIMUM_LATERAL_ACCELERATION = 16;
const STEER_RESPONSIVENESS = 7;
const MAXIMUM_LEAN = 0.5;
const LEAN_RESPONSIVENESS = 6;
const GRAVITY = 9.81;
// Crank turns once for ~2.2 wheel turns in the fleet's hub gear.
const GEAR_RATIO = 2.2;
// Legs spin out here (~2 revolutions a second) however fast the bike goes.
const MAXIMUM_CRANK_RATE = 12.5;
// Longest single collision sub-step; keeps the narrow wheel probes from
// passing through lampposts at boost speed.
const MAXIMUM_COLLISION_STEP = 0.1;

// Collision: a swept body circle plus front and rear wheel probes. Wheel probes
// are narrow so a bike can roll out past its own dock's side post.
const BODY_RADIUS = 0.27;
const WHEEL_PROBE_RADIUS = 0.08;
const FRONT_PROBE = 0.74;
const REAR_PROBE = -0.70;
/** Parked footprint: rear cover at -1.03 m to front mudguard at +1.08 m. */
const PARKED_HALF_LENGTH = 1.06;
const PARKED_CENTRE_OFFSET = 0.02;
const PARKED_HALF_WIDTH = 0.24;

export type SterlingBikeState = 'docked' | 'parked' | 'ridden' | 'docking' | 'undocking';

export interface BikeControls {
  /** -1 (brake / back up) to 1 (pedal). */
  readonly throttle: number;
  /** -1 (right) to 1 (left). */
  readonly steer: number;
  readonly assisted: boolean;
  /** Space: sprint far past the assisted limit. */
  readonly boost: boolean;
}

export const STERLING_ASSISTED_SPEED = ASSISTED_SPEED;
export const STERLING_BOOST_SPEED = BOOST_SPEED;

interface ArticulatedNode {
  readonly node: Object3D;
  readonly rest: Quaternion;
}

const UP = new Vector3(0, 1, 0);
const FORWARD_AXIS = new Vector3(1, 0, 0);
const AXLE_AXIS = new Vector3(0, 0, 1);
const scratchQuaternion = new Quaternion();
const scratchRoll = new Quaternion();
const probe = new Vector3();
const probeStart = new Vector3();
const previousPosition = new Vector3();

function findNode(root: Object3D, name: string): ArticulatedNode | undefined {
  const node = root.getObjectByName(name);
  return node ? { node, rest: node.quaternion.clone() } : undefined;
}

/**
 * One Sterling fleet bike: its pose, bicycle-model riding physics and the
 * articulated wheels, steering, crank and pedals authored in the GLB.
 */
export class SterlingBike implements RiderPose {
  readonly forward = new Vector3(1, 0, 0);
  /** Rider sits in this frame; its -Z is the bike's forward. */
  readonly mount = new Object3D();
  readonly hip = RIDER_HIP;
  readonly grip = RIDER_GRIP;
  readonly leftPedal = new Vector2();
  readonly rightPedal = new Vector2();

  state: SterlingBikeState = 'parked';
  speed = 0;
  obstacle: OrientedBoxObstacle | null = null;
  pedalling = 0;
  /** 0..1, smoothed: the e-assist motor is driving. Read by the ride audio. */
  motorAssist = 0;
  /** True while the rider is braking a moving bike. */
  braking = false;

  private yaw = 0;
  private steerAngle = 0;
  private lean = 0;
  private wheelAngle = 0;
  private crankAngle = 0;
  private readonly frontWheel?: ArticulatedNode;
  private readonly rearWheel?: ArticulatedNode;
  private readonly steering?: ArticulatedNode;
  private readonly crank?: ArticulatedNode;
  private readonly pedals: ArticulatedNode[];

  constructor(readonly object: Object3D) {
    this.frontWheel = findNode(object, 'SB_FrontWheel');
    this.rearWheel = findNode(object, 'SB_RearWheel');
    this.steering = findNode(object, 'SB_SteeringRoot');
    this.crank = findNode(object, 'SB_CrankRoot');
    this.pedals = ['SB_Pedal_Left', 'SB_Pedal_Right']
      .map((name) => findNode(object, name))
      .filter((entry): entry is ArticulatedNode => entry !== undefined);
    this.mount.name = 'Sterling bike rider mount';
    this.mount.rotation.y = -Math.PI / 2;
    object.add(this.mount);
    this.updatePedalPositions();
  }

  get position(): Vector3 {
    return this.object.position;
  }

  get heading(): number {
    return this.yaw;
  }

  get movementState(): MovementState {
    return Math.abs(this.speed) > 0.35 ? 'Riding' : 'Idle';
  }

  get facingDirection(): Vector3 {
    return this.forward;
  }

  setPose(x: number, y: number, z: number, yaw: number): void {
    this.object.position.set(x, y, z);
    this.yaw = yaw;
    this.forward.set(Math.cos(yaw), 0, -Math.sin(yaw));
    this.applyTransform();
  }

  /** Planar distance from `point` to the bike's centreline, rear cover to front wheel. */
  distanceToCentreline(point: Vector3): number {
    const dx = point.x - this.position.x;
    const dz = point.z - this.position.z;
    const along = MathUtils.clamp(dx * this.forward.x + dz * this.forward.z, -1.0, 1.05);
    return Math.hypot(dx - this.forward.x * along, dz - this.forward.z * along);
  }

  /** Collision footprint used while the bike stands docked or parked. */
  createParkedObstacle(name: string): OrientedBoxObstacle {
    return {
      name,
      shape: 'oriented-box',
      x: this.position.x + this.forward.x * PARKED_CENTRE_OFFSET,
      z: this.position.z + this.forward.z * PARKED_CENTRE_OFFSET,
      halfWidth: PARKED_HALF_LENGTH,
      halfDepth: PARKED_HALF_WIDTH,
      rotationY: this.yaw,
      height: 1.3,
      blocksCamera: false,
    };
  }

  /** One fixed simulation step of riding. */
  ride(deltaTime: number, controls: BikeControls, collision: CollisionWorld): void {
    this.updateSpeed(deltaTime, controls);

    const speedFraction = MathUtils.clamp(Math.abs(this.speed) / ASSISTED_SPEED, 0, 1);
    const gripLimitedSteer = Math.atan(
      (WHEELBASE * MAXIMUM_LATERAL_ACCELERATION) / Math.max(this.speed * this.speed, 0.0001),
    );
    const maximumSteer = Math.min(
      MathUtils.lerp(MAXIMUM_STEER_SLOW, MAXIMUM_STEER_FAST, speedFraction),
      gripLimitedSteer,
    );
    const steerRate = controls.steer === 0 ? STEER_RESPONSIVENESS * 1.3 : STEER_RESPONSIVENESS;
    this.steerAngle = MathUtils.lerp(
      this.steerAngle,
      controls.steer * maximumSteer,
      1 - Math.exp(-steerRate * deltaTime),
    );

    // Kinematic bicycle: yaw rate from speed and steer over the wheelbase.
    const yawRate = (this.speed * Math.tan(this.steerAngle)) / WHEELBASE;
    this.yaw += yawRate * deltaTime;
    this.forward.set(Math.cos(this.yaw), 0, -Math.sin(this.yaw));

    const targetLean = MathUtils.clamp(
      Math.atan((this.speed * yawRate) / GRAVITY),
      -MAXIMUM_LEAN,
      MAXIMUM_LEAN,
    );
    this.lean = MathUtils.lerp(this.lean, targetLean, 1 - Math.exp(-LEAN_RESPONSIVENESS * deltaTime));

    this.moveWithCollisions(deltaTime, collision);

    this.pedalling = MathUtils.lerp(
      this.pedalling,
      controls.throttle > 0 ? 1 : 0,
      1 - Math.exp(-8 * deltaTime),
    );
    this.motorAssist = MathUtils.lerp(
      this.motorAssist,
      controls.throttle > 0 && (controls.assisted || controls.boost) ? 1 : 0,
      1 - Math.exp(-5 * deltaTime),
    );
    this.braking = controls.throttle < 0 && this.speed > 0.05;
    if (controls.throttle > 0) {
      const crankRate = Math.min(
        Math.max(Math.abs(this.speed), 1.2) / WHEEL_RADIUS / GEAR_RATIO,
        MAXIMUM_CRANK_RATE,
      );
      this.crankAngle -= crankRate * deltaTime;
    }
    this.applyTransform();
  }

  /** Settles a standing or docking bike: no drive, lean returns upright. */
  settle(deltaTime: number, moving = false): void {
    this.speed = 0;
    this.pedalling = 0;
    this.motorAssist = 0;
    this.braking = false;
    if (!moving && Math.abs(this.lean) < 0.0005) return;
    this.lean = MathUtils.lerp(this.lean, 0, 1 - Math.exp(-LEAN_RESPONSIVENESS * deltaTime));
    this.applyTransform();
  }

  /** Rolls the bike to a pose (used while snapping into a dock). */
  rollTo(x: number, z: number, yaw: number): void {
    const distance = (x - this.position.x) * this.forward.x + (z - this.position.z) * this.forward.z;
    this.wheelAngle -= distance / WHEEL_RADIUS;
    this.steerAngle *= 0.85;
    this.object.position.x = x;
    this.object.position.z = z;
    this.yaw = yaw;
    this.forward.set(Math.cos(yaw), 0, -Math.sin(yaw));
  }

  private updateSpeed(deltaTime: number, controls: BikeControls): void {
    const drag = (ROLLING_DRAG + AIR_DRAG * this.speed * this.speed) * deltaTime;
    if (controls.throttle > 0) {
      const target = controls.boost
        ? BOOST_SPEED
        : controls.assisted ? ASSISTED_SPEED : CRUISE_SPEED;
      const acceleration = controls.boost
        ? BOOST_ACCELERATION
        : controls.assisted ? ASSISTED_ACCELERATION : PEDAL_ACCELERATION;
      if (this.speed < 0) {
        this.speed = Math.min(0, this.speed + BRAKE_DECELERATION * deltaTime);
      } else if (this.speed < target) {
        // Assist tapers as the bike approaches its limit.
        const taper = 1 - (this.speed / target) ** 2;
        this.speed = Math.min(target, this.speed + acceleration * Math.max(taper, 0.15) * deltaTime);
      } else {
        this.speed = Math.max(target, this.speed - drag - OVER_SPEED_DECELERATION * deltaTime);
      }
    } else if (controls.throttle < 0) {
      if (this.speed > 0.05) {
        const braking = this.speed > ASSISTED_SPEED ? HIGH_SPEED_BRAKE_DECELERATION : BRAKE_DECELERATION;
        this.speed = Math.max(0, this.speed - braking * deltaTime);
      } else {
        // Stopped: walk the bike backwards with the feet down.
        this.speed = Math.max(-REVERSE_SPEED, this.speed - 1.6 * deltaTime);
      }
    } else if (this.speed > 0) {
      this.speed = Math.max(0, this.speed - drag);
    } else {
      this.speed = Math.min(0, this.speed + drag * 6);
    }
  }

  private moveWithCollisions(deltaTime: number, collision: CollisionWorld): void {
    const intended = this.speed * deltaTime;
    previousPosition.copy(this.position);
    const steps = Math.max(1, Math.ceil(Math.abs(intended) / MAXIMUM_COLLISION_STEP));
    for (let step = 0; step < steps; step += 1) {
      probe.copy(this.forward).multiplyScalar(intended / steps);
      moveCircleWithCollisions(this.position, probe, BODY_RADIUS, collision);

      for (const offset of [FRONT_PROBE, REAR_PROBE]) {
        probe.copy(this.position).addScaledVector(this.forward, offset);
        probeStart.copy(probe);
        resolveCircleOverlaps(probe, WHEEL_PROBE_RADIUS, collision);
        this.position.x += probe.x - probeStart.x;
        this.position.z += probe.z - probeStart.z;
      }
    }

    const travelled = (this.position.x - previousPosition.x) * this.forward.x
      + (this.position.z - previousPosition.z) * this.forward.z;
    // Whatever a wall or kerb furniture absorbed is lost from the speed.
    if (deltaTime > 0 && Math.abs(travelled) < Math.abs(intended) * 0.98) {
      this.speed = travelled / deltaTime;
    }
    this.wheelAngle -= travelled / WHEEL_RADIUS;
  }

  private applyTransform(): void {
    scratchQuaternion.setFromAxisAngle(UP, this.yaw);
    // Leaning into a left turn tips the top toward -Z, a negative roll about +X.
    scratchRoll.setFromAxisAngle(FORWARD_AXIS, -this.lean);
    this.object.quaternion.copy(scratchQuaternion).multiply(scratchRoll);

    if (this.frontWheel) this.spin(this.frontWheel, this.wheelAngle);
    if (this.rearWheel) this.spin(this.rearWheel, this.wheelAngle);
    if (this.crank) this.spin(this.crank, this.crankAngle);
    for (const pedal of this.pedals) {
      // Counter-rotate so the platforms stay level through the stroke.
      this.spin(pedal, -this.crankAngle);
    }
    if (this.steering) {
      // Blender local Z (the raked head-tube axis) imports as local +Y.
      scratchQuaternion.setFromAxisAngle(UP, this.steerAngle);
      this.steering.node.quaternion.copy(this.steering.rest).multiply(scratchQuaternion);
    }
    this.updatePedalPositions();
    this.object.updateMatrixWorld(true);
  }

  private spin(entry: ArticulatedNode, angle: number): void {
    scratchQuaternion.setFromAxisAngle(AXLE_AXIS, angle);
    entry.node.quaternion.copy(entry.rest).multiply(scratchQuaternion);
  }

  private updatePedalPositions(): void {
    const right = RIGHT_CRANK_REST + this.crankAngle;
    const left = LEFT_CRANK_REST + this.crankAngle;
    this.rightPedal.set(
      CRANK_CENTRE.x + Math.cos(right) * CRANK_LENGTH,
      CRANK_CENTRE.y + Math.sin(right) * CRANK_LENGTH,
    );
    this.leftPedal.set(
      CRANK_CENTRE.x + Math.cos(left) * CRANK_LENGTH,
      CRANK_CENTRE.y + Math.sin(left) * CRANK_LENGTH,
    );
  }
}
