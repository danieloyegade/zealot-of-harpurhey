import type { Vector3 } from 'three';
import type { MovementState } from '../player/PlayerController';

export class DebugOverlay {
  private readonly element = document.createElement('pre');
  private elapsedTime = 0;
  private frameCount = 0;
  private framesPerSecond = 0;

  constructor() {
    this.element.className = 'debug-overlay';
    document.body.appendChild(this.element);
  }

  update(
    deltaTime: number,
    position: Vector3,
    movementState: MovementState,
  ): void {
    this.elapsedTime += deltaTime;
    this.frameCount += 1;

    if (this.elapsedTime >= 0.25) {
      this.framesPerSecond = Math.round(this.frameCount / this.elapsedTime);
      this.elapsedTime = 0;
      this.frameCount = 0;
    }

    this.element.textContent = [
      'ZEALOT OF HARPERHAY — DEVELOPMENT BUILD',
      '',
      `FPS: ${this.framesPerSecond}`,
      `Player X: ${position.x.toFixed(2)}`,
      `Player Z: ${position.z.toFixed(2)}`,
      `Walking / Running: ${movementState}`,
    ].join('\n');
  }
}
