import { Matrix4, Object3D, Quaternion, Vector3, type PerspectiveCamera } from 'three';

// The tripod the title card is laid over: eye height at the south edge of the
// park, frontal down its axis, with the rider small at the centre of frame.
// On entry the lens travels from here into the chase camera.
const TITLE_POSITION = new Vector3(0, 1.65, 18.5);
const TITLE_LOOK_AT = new Vector3(0, 2, -12);
const GLIDE_SECONDS = 3.6;

// Small enough to read as a hand resting on the tripod, not as a camera move.
const DRIFT_METRES = 0.035;

type TitleCameraState = 'holding' | 'gliding' | 'released';

export class TitleCamera {
  private state: TitleCameraState;
  private elapsedSeconds = 0;
  private glideProgress = 0;
  private readonly titlePosition = new Vector3();
  private readonly titleQuaternion = new Quaternion();
  private readonly glideFrom = new Vector3();
  private readonly chasePosition = new Vector3();
  private readonly chaseQuaternion = new Quaternion();

  constructor(
    private readonly camera: PerspectiveCamera,
    holding: boolean,
  ) {
    this.state = holding ? 'holding' : 'released';
    const [position, lookAt] = resolveTitleShot();
    this.titlePosition.copy(position);
    this.titleQuaternion.setFromRotationMatrix(
      new Matrix4().lookAt(position, lookAt, Object3D.DEFAULT_UP),
    );
    this.glideFrom.copy(position);
  }

  /** True while the title holds the frame; the rider should not move. */
  get holdsPlayer(): boolean {
    return this.state === 'holding';
  }

  release(): void {
    if (this.state === 'holding') this.state = 'gliding';
  }

  /** Call after the chase camera has placed itself for this frame. */
  apply(deltaTime: number): void {
    if (this.state === 'released') return;

    if (this.state === 'holding') {
      this.elapsedSeconds += deltaTime;
      this.camera.position.copy(this.titlePosition);
      this.camera.position.x += Math.sin(this.elapsedSeconds * 0.23) * DRIFT_METRES;
      this.camera.position.y += Math.sin(this.elapsedSeconds * 0.17 + 1.3) * DRIFT_METRES * 0.5;
      this.camera.quaternion.copy(this.titleQuaternion);
      this.glideFrom.copy(this.camera.position);
      return;
    }

    this.glideProgress = Math.min(1, this.glideProgress + deltaTime / GLIDE_SECONDS);
    const blend = smootherstep(this.glideProgress);
    this.chasePosition.copy(this.camera.position);
    this.chaseQuaternion.copy(this.camera.quaternion);
    this.camera.position.lerpVectors(this.glideFrom, this.chasePosition, blend);
    this.camera.quaternion.slerpQuaternions(this.titleQuaternion, this.chaseQuaternion, blend);
    if (this.glideProgress >= 1) this.state = 'released';
  }
}

function resolveTitleShot(): readonly [Vector3, Vector3] {
  if (import.meta.env.DEV) {
    // ?titleshot=x,y,z,lookX,lookY,lookZ composes the shot in the browser.
    const values = new URLSearchParams(window.location.search)
      .get('titleshot')
      ?.split(',')
      .map(Number);
    if (values?.length === 6 && values.every(Number.isFinite)) {
      const [x, y, z, lookX, lookY, lookZ] = values as [number, number, number, number, number, number];
      return [new Vector3(x, y, z), new Vector3(lookX, lookY, lookZ)];
    }
  }
  return [TITLE_POSITION, TITLE_LOOK_AT];
}

function smootherstep(value: number): number {
  return value * value * value * (value * (value * 6 - 15) + 10);
}
