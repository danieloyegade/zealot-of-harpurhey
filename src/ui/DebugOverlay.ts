import type { Vector3 } from 'three';
import type { MovementState } from '../player/PlayerController';
import type { QualityLevel } from '../rendering/visualStyle';

export interface RenderDiagnostics {
  readonly drawCalls: number;
  readonly triangles: number;
  readonly activePointLights: number;
  readonly activeSpotLights: number;
  readonly registeredPointLights: number;
  readonly maximumActiveLocalLights: number;
  readonly activeLocalLightGroups: readonly string[];
  readonly drawingBufferWidth: number;
  readonly drawingBufferHeight: number;
  readonly pixelRatio: number;
  readonly renderScale: number;
  readonly textures: number;
  readonly geometries: number;
  readonly materials: number;
  readonly programs: number;
  readonly qualityLevel: QualityLevel;
}

export class DebugOverlay {
  private readonly element = document.createElement('pre');
  private elapsedTime = 0;
  private frameCount = 0;
  private framesPerSecond = 0;
  private frameTimeMilliseconds = 0;
  private medianFrameTimeMilliseconds = 0;
  private p95FrameTimeMilliseconds = 0;
  private readonly recentFrameTimes: number[] = [];

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
    if (realFrameDelta > 0 && realFrameDelta < 0.25) {
      this.recentFrameTimes.push(this.frameTimeMilliseconds);
      if (this.recentFrameTimes.length > 360) this.recentFrameTimes.shift();
    }

    if (this.elapsedTime >= 0.5) {
      this.framesPerSecond = Math.round(this.frameCount / this.elapsedTime);
      const sortedFrameTimes = [...this.recentFrameTimes].sort((a, b) => a - b);
      const sampleAt = (proportion: number): number => sortedFrameTimes[
        Math.min(sortedFrameTimes.length - 1, Math.floor(sortedFrameTimes.length * proportion))
      ] ?? 0;
      this.medianFrameTimeMilliseconds = sampleAt(0.5);
      this.p95FrameTimeMilliseconds = sampleAt(0.95);
      this.elapsedTime = 0;
      this.frameCount = 0;
    }

    this.element.textContent = [
      'ZEALOT OF HARPERHEY — DEVELOPMENT BUILD',
      '',
      `FPS: ${this.framesPerSecond}`,
      `Frame: ${this.frameTimeMilliseconds.toFixed(1)} ms`,
      `Median / p95: ${this.medianFrameTimeMilliseconds.toFixed(1)} / ${this.p95FrameTimeMilliseconds.toFixed(1)} ms`,
      `Draw calls: ${diagnostics.drawCalls}`,
      `Triangles: ${diagnostics.triangles.toLocaleString()}`,
      `Lights: ${diagnostics.activePointLights} / ${diagnostics.maximumActiveLocalLights} local point (${diagnostics.registeredPointLights} registered) + ${diagnostics.activeSpotLights} spot`,
      `Active light groups: ${diagnostics.activeLocalLightGroups.join(', ') || 'none'}`,
      `Buffer: ${diagnostics.drawingBufferWidth} × ${diagnostics.drawingBufferHeight}`,
      `Pixel ratio: ${diagnostics.pixelRatio.toFixed(2)} (scale ${diagnostics.renderScale.toFixed(2)})`,
      `Textures / geometries: ${diagnostics.textures} / ${diagnostics.geometries}`,
      `Scene materials: ${diagnostics.materials}`,
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
