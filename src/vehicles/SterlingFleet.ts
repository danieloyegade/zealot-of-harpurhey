import { MathUtils, Vector3 } from 'three';
import type { CollisionObstacle } from '../world/collision';
import type { SterlingBike } from './SterlingBike';

/** Where a docked bike's origin stands, and which bike (if any) holds it. */
export interface SterlingDock {
  readonly id: string;
  readonly position: Vector3;
  readonly yaw: number;
  bike: SterlingBike | null;
}

// Riding within this distance of an empty dock's bike position offers docking.
const DOCKING_REACH = 1.0;
const DOCKING_SECONDS = 0.55;
// A hired bike is rolled straight back until its front wheel clears the dock
// post, as at a real dock; riding forward out would run through the post.
const UNDOCK_DISTANCE = 1.15;
const UNDOCK_SECONDS = 0.7;

/** A short scripted roll into or out of a dock, ignoring collision. */
interface DockMotion {
  readonly bike: SterlingBike;
  readonly from: Vector3;
  readonly fromYaw: number;
  readonly to: Vector3;
  readonly toYaw: number;
  readonly seconds: number;
  /** Dock to lock the bike into when the roll ends; null leaves it ridden. */
  readonly lockInto: SterlingDock | null;
  elapsed: number;
}

/**
 * Every Sterling bike and dock in the city. Owns the bikes' dynamic collision:
 * a docked or parked bike is a solid footprint in the shared obstacle list; a
 * ridden bike is not.
 */
export class SterlingFleet {
  readonly bikes: SterlingBike[] = [];
  readonly docks: SterlingDock[] = [];
  private readonly motions: DockMotion[] = [];
  private readonly names = new Map<SterlingBike, string>();

  constructor(private readonly obstacles: CollisionObstacle[]) {}

  addDock(id: string, position: Vector3, yaw: number): SterlingDock {
    const dock: SterlingDock = { id, position: position.clone(), yaw, bike: null };
    this.docks.push(dock);
    return dock;
  }

  /** Registers a bike, either locked into `dock` or parked where it stands. */
  addBike(bike: SterlingBike, name: string, dock?: SterlingDock): void {
    this.bikes.push(bike);
    this.names.set(bike, name);
    if (dock) {
      bike.setPose(dock.position.x, dock.position.y, dock.position.z, dock.yaw);
      this.lockInto(bike, dock);
    } else {
      bike.state = 'parked';
      this.setSolid(bike, true);
    }
  }

  /** The closest standing bike the player can reach, if any. */
  nearestMountable(position: Vector3, reach: number): SterlingBike | null {
    let nearest: SterlingBike | null = null;
    let nearestDistance = reach;
    for (const bike of this.bikes) {
      if (bike.state !== 'docked' && bike.state !== 'parked') continue;
      const distance = bike.distanceToCentreline(position);
      if (distance <= nearestDistance) {
        nearest = bike;
        nearestDistance = distance;
      }
    }
    return nearest;
  }

  /** The closest empty dock a ridden bike is near enough to roll into. */
  nearestFreeDock(bike: SterlingBike): SterlingDock | null {
    let nearest: SterlingDock | null = null;
    let nearestDistance = DOCKING_REACH;
    for (const dock of this.docks) {
      if (dock.bike) continue;
      const distance = Math.hypot(
        dock.position.x - bike.position.x,
        dock.position.z - bike.position.z,
      );
      if (distance <= nearestDistance) {
        nearest = dock;
        nearestDistance = distance;
      }
    }
    return nearest;
  }

  dockOf(bike: SterlingBike): SterlingDock | null {
    return this.docks.find((dock) => dock.bike === bike) ?? null;
  }

  /**
   * Unlocks a standing bike for riding and stops it being solid. A docked bike
   * first rolls back out of its dock; `isInMotion` is true until it has.
   */
  takeOut(bike: SterlingBike): void {
    const dock = this.dockOf(bike);
    this.setSolid(bike, false);
    if (!dock) {
      bike.state = 'ridden';
      return;
    }
    dock.bike = null;
    bike.state = 'undocking';
    this.motions.push({
      bike,
      from: bike.position.clone(),
      fromYaw: bike.heading,
      to: bike.position.clone().addScaledVector(bike.forward, -UNDOCK_DISTANCE),
      toYaw: bike.heading,
      seconds: UNDOCK_SECONDS,
      lockInto: null,
      elapsed: 0,
    });
  }

  /** Leaves a ridden bike standing where it stopped. */
  park(bike: SterlingBike): void {
    bike.state = 'parked';
    bike.speed = 0;
    this.setSolid(bike, true);
  }

  /** Rolls a ridden bike into `dock`; `isInMotion` stays true until it locks. */
  beginDocking(bike: SterlingBike, dock: SterlingDock): void {
    dock.bike = bike;
    bike.state = 'docking';
    bike.speed = 0;
    this.motions.push({
      bike,
      from: bike.position.clone(),
      fromYaw: bike.heading,
      to: dock.position,
      toYaw: dock.yaw,
      seconds: DOCKING_SECONDS,
      lockInto: dock,
      elapsed: 0,
    });
  }

  isInMotion(bike: SterlingBike): boolean {
    return this.motions.some((motion) => motion.bike === bike);
  }

  update(deltaTime: number): void {
    for (let index = this.motions.length - 1; index >= 0; index -= 1) {
      const motion = this.motions[index];
      motion.elapsed += deltaTime;
      const t = MathUtils.smoothstep(motion.elapsed / motion.seconds, 0, 1);
      const turn = MathUtils.euclideanModulo(motion.toYaw - motion.fromYaw + Math.PI, Math.PI * 2) - Math.PI;
      motion.bike.rollTo(
        MathUtils.lerp(motion.from.x, motion.to.x, t),
        MathUtils.lerp(motion.from.z, motion.to.z, t),
        motion.fromYaw + turn * t,
      );
      if (motion.elapsed < motion.seconds) continue;
      this.motions.splice(index, 1);
      const { bike, lockInto } = motion;
      if (lockInto) {
        bike.setPose(lockInto.position.x, lockInto.position.y, lockInto.position.z, lockInto.yaw);
        this.lockInto(bike, lockInto);
      } else {
        bike.state = 'ridden';
      }
    }
    for (const bike of this.bikes) {
      if (bike.state === 'ridden') continue;
      bike.settle(deltaTime, bike.state === 'docking' || bike.state === 'undocking');
    }
  }

  private lockInto(bike: SterlingBike, dock: SterlingDock): void {
    dock.bike = bike;
    bike.state = 'docked';
    bike.speed = 0;
    this.setSolid(bike, true);
  }

  private setSolid(bike: SterlingBike, solid: boolean): void {
    if (bike.obstacle) {
      const index = this.obstacles.indexOf(bike.obstacle);
      if (index >= 0) this.obstacles.splice(index, 1);
      bike.obstacle = null;
    }
    if (solid) {
      bike.obstacle = bike.createParkedObstacle(this.names.get(bike) ?? 'Sterling bike');
      this.obstacles.push(bike.obstacle);
    }
  }
}
