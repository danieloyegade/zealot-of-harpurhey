import { DefaultLoadingManager } from 'three';
import { describeAsset, isAnonymousAsset, UNIDENTIFIED_OBJECT } from './title/assetCatalogue';
import { mountTitleContent } from './title/marginalia';
import { recordEntry } from './title/riderRecord';

// The title card is authored in index.html and styled by ./intro.css so it
// paints before the game bundle has parsed. This class feeds it the world's
// asset loading, plays the beats between loading and entry, and runs the entry
// into the city.

// A finished loading wave only counts as "loaded" if no new wave starts within
// this window: several hero locations begin a second fetch after their first.
const LOAD_SETTLE_MS = 300;
// From the title being typeset until anything may replace the loading line.
const TITLE_SETTLED_MS = 2200;
// "City assembled", the star at the end of the line, a breath.
const ASSEMBLED_HOLD_MS = 1400;
// Dense, then sparse: the horse and rider alone, then the first delivery.
const RIDER_BEAT_MS = 2600;
const DELIVERY_BEAT_MS = 4600;
// Each catalogue entry stays at least this long, so the list can be read in passing.
const CATALOGUE_ENTRY_MS = 110;
// Embedded textures have no name. Every so often one is admitted as such.
const UNIDENTIFIED_EVERY = 9;
const CONTROLS_VISIBLE_MS = 9000;

// Entry, in order: marginalia and loading line fade, the lamp swells and the
// city is heard, then the title dissolves into the world beneath it.
const CITY_HEARD_AT_MS = 900;
const REVEAL_AT_MS = 2800;
const REMOVE_AFTER_REVEAL_MS = 2800;

export interface IntroScreenOptions {
  /** Remove the card as soon as the world is ready, without waiting for input. */
  readonly enterAutomatically: boolean;
}

type IntroState = 'loading' | 'assembled' | 'sequence' | 'ready' | 'entering' | 'gone';

export class IntroScreen {
  /** Whether the card will hold the camera, resolution and sound until the player enters. */
  readonly holdsWorld: boolean;

  private readonly element = document.querySelector<HTMLElement>('[data-intro]');
  private readonly rule = this.find('[data-intro-rule]');
  private readonly labelElement = this.find('[data-intro-label]');
  private readonly countElement = this.find('[data-intro-count]');
  private readonly itemElement = this.find('[data-intro-item]');
  private readonly prompt = this.find<HTMLButtonElement>('[data-intro-prompt]');
  private readonly promptKey = this.find('[data-intro-key]');
  private readonly touchOnly = window.matchMedia('(hover: none) and (pointer: coarse)').matches;
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
  private anonymousAssets = 0;
  private pendingEntry: string | null = null;
  private entryTimer: number | undefined;

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
    if (this.holdsWorld && this.element) {
      mountTitleContent(this.element);
    } else {
      // No title: take the card down now rather than leaving it over the loading world.
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
    DefaultLoadingManager.onProgress = (url, loaded, total) => {
      this.reportProgress(url, loaded, total);
    };
    DefaultLoadingManager.onLoad = () => {
      window.clearTimeout(this.settleTimer);
      this.settleTimer = window.setTimeout(this.resolveAssetsLoaded, LOAD_SETTLE_MS);
    };

    if (this.touchOnly && this.promptKey) this.promptKey.textContent = '[ Touch ]';
  }

  /** Resolves once the world's initial models and textures have finished loading. */
  waitForAssets(): Promise<void> {
    if (!this.loadingStarted) this.resolveAssetsLoaded();
    return this.assetsLoaded;
  }

  /** Resolves when the player chooses to enter and the city should begin to be heard. */
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

    await waitForClass(element, 'is-typeset');
    const typesetAt = Number(element.dataset.typesetAt) || performance.now();
    await delay(typesetAt + TITLE_SETTLED_MS - performance.now());

    this.state = 'assembled';
    this.rule?.style.setProperty('--intro-progress', '1');
    if (this.labelElement) this.labelElement.textContent = 'City assembled';
    element.classList.add('is-assembled');
    await delay(ASSEMBLED_HOLD_MS);

    // From here Return goes straight into the city; the beats are not a gate.
    this.state = 'sequence';
    window.addEventListener('keydown', this.handleKeyDown);
    if (this.touchOnly) element.addEventListener('pointerdown', this.enter);

    element.classList.add('is-beat-rider');
    await delay(RIDER_BEAT_MS);
    if (this.state !== 'sequence') return;

    element.classList.replace('is-beat-rider', 'is-beat-delivery');
    await delay(DELIVERY_BEAT_MS);
    if (this.state !== 'sequence') return;

    element.classList.remove('is-beat-delivery');
    this.state = 'ready';
    element.classList.add('is-ready', 'is-showing-controls');
    window.setTimeout(() => element.classList.remove('is-showing-controls'), CONTROLS_VISIBLE_MS);
    if (this.prompt) {
      this.prompt.disabled = false;
      this.prompt.addEventListener('click', this.enter);
    }
  }

  private reportProgress(url: string, loaded: number, total: number): void {
    if (this.state !== 'loading') return;

    // Later waves raise the total, so never let the line retreat.
    this.displayedProgress = Math.max(this.displayedProgress, total > 0 ? loaded / total : 0);
    this.rule?.style.setProperty('--intro-progress', this.displayedProgress.toFixed(3));
    if (this.countElement) this.countElement.textContent = `${loaded} / ${total}`;

    if (isAnonymousAsset(url)) {
      this.anonymousAssets += 1;
      if (this.anonymousAssets % UNIDENTIFIED_EVERY === 0) this.catalogue(UNIDENTIFIED_OBJECT);
      return;
    }
    const description = describeAsset(url);
    if (description) this.catalogue(description);
  }

  private catalogue(description: string): void {
    this.pendingEntry = description;
    if (this.entryTimer === undefined) this.showPendingEntry();
  }

  private showPendingEntry(): void {
    if (this.pendingEntry === null || !this.itemElement || this.state !== 'loading') return;

    this.itemElement.textContent = this.pendingEntry;
    this.pendingEntry = null;
    this.entryTimer = window.setTimeout(() => {
      this.entryTimer = undefined;
      this.showPendingEntry();
    }, CATALOGUE_ENTRY_MS);
  }

  private readonly handleKeyDown = (event: KeyboardEvent): void => {
    // `key` covers Return and the numpad's Enter alike, whatever the layout.
    if (event.key !== 'Enter') return;
    if (event.repeat || event.metaKey || event.ctrlKey || event.altKey) return;
    event.preventDefault();
    this.enter();
  };

  private readonly enter = (): void => {
    const element = this.element;
    if (!element || (this.state !== 'sequence' && this.state !== 'ready')) return;

    this.state = 'entering';
    window.removeEventListener('keydown', this.handleKeyDown);
    element.removeEventListener('pointerdown', this.enter);
    if (this.prompt) {
      this.prompt.blur();
      this.prompt.disabled = true;
    }
    recordEntry();
    // Entering from a beat brings the title back to dissolve into the city.
    element.classList.remove('is-beat-rider', 'is-beat-delivery');
    element.classList.add('is-entering');

    window.setTimeout(this.resolveEntering, CITY_HEARD_AT_MS);
    window.setTimeout(() => {
      element.classList.add('is-revealing');
      this.resolveRevealing();
    }, REVEAL_AT_MS);
    window.setTimeout(() => {
      this.state = 'gone';
      element.remove();
    }, REVEAL_AT_MS + REMOVE_AFTER_REVEAL_MS);
  };

  private find<T extends HTMLElement = HTMLElement>(selector: string): T | null {
    return this.element?.querySelector<T>(selector) ?? null;
  }
}

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, Math.max(0, milliseconds)));
}

function waitForClass(element: HTMLElement, className: string): Promise<void> {
  if (element.classList.contains(className)) return Promise.resolve();

  return new Promise((resolve) => {
    const observer = new MutationObserver(() => {
      if (!element.classList.contains(className)) return;
      observer.disconnect();
      resolve();
    });
    observer.observe(element, { attributes: true, attributeFilter: ['class'] });
  });
}
