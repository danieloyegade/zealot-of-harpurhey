import { DefaultLoadingManager } from 'three';
import { recordEntry } from './title/riderRecord';

// The loading plate is authored in index.html and styled by ./intro.css so it
// paints before the game bundle has parsed. This class feeds its printed bar
// the world's real asset progress and dissolves it once shaders are compiled.

// A finished loading wave only counts as "loaded" if no new wave starts within
// this window: several hero locations begin a second fetch after their first.
const LOAD_SETTLE_MS = 300;
// Let the full bar register before the plate gives the frame to the city.
const LOADED_HOLD_MS = 650;
const REMOVE_AFTER_REVEAL_MS = 1200;
// Asset waves can momentarily report 100% before follow-up GLBs begin. Reserve
// the final part of the bar for the settle window and shader compilation.
const ASSET_PROGRESS_CEILING = 0.94;

export interface IntroScreenOptions {
  /** Omit the loading plate entirely, as development screenshot views do. */
  readonly enterAutomatically: boolean;
}

type IntroState = 'loading' | 'entering' | 'gone';

export class IntroScreen {
  /** Whether the plate holds the camera, resolution and sound until loading completes. */
  readonly holdsWorld: boolean;

  private readonly element = document.querySelector<HTMLElement>('[data-intro]');
  private readonly progressElement = this.find('[data-intro-progress]');
  private readonly assetsLoaded: Promise<void>;
  private readonly entering: Promise<void>;
  private readonly revealing: Promise<void>;
  private resolveAssetsLoaded: () => void = () => undefined;
  private resolveEntering: () => void = () => undefined;
  private resolveRevealing: () => void = () => undefined;
  private state: IntroState = 'loading';
  private loadingStarted = false;
  private settleTimer: number | undefined;
  private displayedProgress = 0;

  constructor(private readonly options: IntroScreenOptions) {
    this.assetsLoaded = new Promise((resolve) => {
      this.resolveAssetsLoaded = resolve;
    });
    this.entering = new Promise((resolve) => {
      this.resolveEntering = resolve;
    });
    this.revealing = new Promise((resolve) => {
      this.resolveRevealing = resolve;
    });

    this.holdsWorld = this.element !== null && !options.enterAutomatically;
    if (!this.holdsWorld) {
      // Development views and ?intro=off go straight to the loaded world.
      this.element?.remove();
      this.resolveEntering();
      this.resolveRevealing();
    }

    // GLTFLoader and TextureLoader both report through the default manager, so
    // the world needs no changes to be observed. Install before createWorld().
    DefaultLoadingManager.onStart = () => {
      this.loadingStarted = true;
      window.clearTimeout(this.settleTimer);
    };
    DefaultLoadingManager.onProgress = (_url, loaded, total) => {
      this.reportProgress(loaded, total);
    };
    DefaultLoadingManager.onLoad = () => {
      window.clearTimeout(this.settleTimer);
      this.settleTimer = window.setTimeout(this.resolveAssetsLoaded, LOAD_SETTLE_MS);
    };
  }

  /** Resolves once the world's initial models and textures have finished loading. */
  waitForAssets(): Promise<void> {
    if (!this.loadingStarted) this.resolveAssetsLoaded();
    return this.assetsLoaded;
  }

  /** Resolves when loading completes and the city should begin to be heard. */
  whenEntering(): Promise<void> {
    return this.entering;
  }

  /** Resolves when the title starts to dissolve and the world should take the frame back. */
  whenRevealing(): Promise<void> {
    return this.revealing;
  }

  async setReady(): Promise<void> {
    const element = this.element;
    if (!element || this.state !== 'loading') return;

    if (this.options.enterAutomatically) {
      this.state = 'gone';
      element.remove();
      return;
    }

    this.setProgress(1);
    await delay(LOADED_HOLD_MS);
    this.beginEntry();
  }

  private reportProgress(loaded: number, total: number): void {
    if (this.state !== 'loading') return;

    const next = total > 0 ? Math.min(loaded / total, 1) * ASSET_PROGRESS_CEILING : 0;
    this.setProgress(Math.max(this.displayedProgress, next));
  }

  private setProgress(progress: number): void {
    this.displayedProgress = progress;
    this.progressElement?.style.setProperty('--intro-progress', progress.toFixed(3));
    this.progressElement?.setAttribute('aria-valuenow', String(Math.round(progress * 100)));
  }

  private beginEntry(): void {
    const element = this.element;
    if (!element || this.state !== 'loading') return;

    this.state = 'entering';
    recordEntry();
    element.classList.add('is-revealing');
    this.resolveEntering();
    this.resolveRevealing();
    window.setTimeout(() => {
      this.state = 'gone';
      element.remove();
    }, REMOVE_AFTER_REVEAL_MS);
  }

  private find<T extends HTMLElement = HTMLElement>(selector: string): T | null {
    return this.element?.querySelector<T>(selector) ?? null;
  }
}

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, Math.max(0, milliseconds)));
}
