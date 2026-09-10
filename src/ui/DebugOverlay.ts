import type { Vector3 } from 'three';
import type { MovementState } from '../player/PlayerController';
import type { QualityLevel } from '../rendering/visualStyle';

export interface RenderDiagnostics {
  readonly drawCalls: number;
  readonly triangles: number;
  readonly activePointLights: number;
  readonly activeSpotLights: number;
  readonly drawingBufferWidth: number;
  readonly drawingBufferHeight: number;
  readonly pixelRatio: number;
  readonly renderScale: number;
  readonly textures: number;
  readonly geometries: number;
  readonly programs: number;
  readonly qualityLevel: QualityLevel;
}

export class DebugOverlay {
  private readonly element = document.createElement('pre');
  private elapsedTime = 0;
  private frameCount = 0;
  private framesPerSecond = 0;
  private frameTimeMilliseconds = 0;

  constructor() {
    this.element.className = 'debug-overlay';
    document.body.appendChild(this.element);
  }

  setVisible(visible: boolean): void {
    this.element.hidden = !visible;
  }

  update(
    realFrameDelta: number,
    position: Vector3,
    movementState: MovementState,
    diagnostics: RenderDiagnostics,
  ): void {
    this.elapsedTime += realFrameDelta;
    this.frameCount += 1;
    this.frameTimeMilliseconds = realFrameDelta * 1000;

    if (this.elapsedTime >= 0.5) {
      this.framesPerSecond = Math.round(this.frameCount / this.elapsedTime);
      this.elapsedTime = 0;
      this.frameCount = 0;
    }

    this.element.textContent = [
      'ZEALOT OF HARPERHAY — DEVELOPMENT BUILD',
      '',
      `FPS: ${this.framesPerSecond}`,
      `Frame: ${this.frameTimeMilliseconds.toFixed(1)} ms`,
      `Draw calls: ${diagnostics.drawCalls}`,
      `Triangles: ${diagnostics.triangles.toLocaleString()}`,
      `Lights: ${diagnostics.activePointLights} point + ${diagnostics.activeSpotLights} spot`,
      `Buffer: ${diagnostics.drawingBufferWidth} × ${diagnostics.drawingBufferHeight}`,
      `Pixel ratio: ${diagnostics.pixelRatio.toFixed(2)} (scale ${diagnostics.renderScale.toFixed(2)})`,
      `Textures / geometries: ${diagnostics.textures} / ${diagnostics.geometries}`,
      `Programs: ${diagnostics.programs}`,
      `Quality: ${diagnostics.qualityLevel.toUpperCase()}`,
      '',
      `Player X: ${position.x.toFixed(2)}`,
      `Player Z: ${position.z.toFixed(2)}`,
      `Walking / Running: ${movementState}`,
      '',
      'H: hide development overlays',
    ].join('\n');
  }
}
