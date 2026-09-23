import { Vector2 } from 'three';

const MOVEMENT_KEYS = new Set([
  'KeyW',
  'KeyA',
  'KeyS',
  'KeyD',
  'ArrowUp',
  'ArrowDown',
  'ArrowLeft',
  'ArrowRight',
  'Space',
]);

/**
 * Some hardware keyboards and automation report an empty `code`, iPadOS ones
 * among them, which would leave every binding dead. Rebuild the code from the
 * key when that happens.
 */
function resolveCode(event: KeyboardEvent): string {
  if (event.code) {
    return event.code;
  }
  const key = event.key;
  if (key.length === 1) {
    const upper = key.toUpperCase();
    if (upper >= 'A' && upper <= 'Z') {
      return `Key${upper}`;
    }
    if (key === ' ') {
      return 'Space';
    }
  }
  if (key.startsWith('Arrow')) {
    return key;
  }
  if (key === 'Shift') {
    return 'ShiftLeft';
  }
  if (key === 'Meta') {
    return 'MetaLeft';
  }
  return '';
}

export class InputController {
  readonly orbitDelta = new Vector2();

  private readonly element: HTMLCanvasElement;
  private readonly pressedKeys = new Set<string>();
  private readonly pendingOrbitDelta = new Vector2();
  private readonly lastPointerPosition = new Vector2();
  private isDragging = false;
  private activePointerId: number | null = null;
  private overlayToggleQueued = false;
  private interactQueued = false;
  private recenterQueued = false;

  constructor(element: HTMLCanvasElement) {
    this.element = element;
    window.addEventListener('keydown', this.handleKeyDown);
    window.addEventListener('keyup', this.handleKeyUp);
    window.addEventListener('blur', this.handleBlur);
    document.addEventListener('visibilitychange', this.handleVisibilityChange);
    element.addEventListener('pointerdown', this.handlePointerDown);
    element.addEventListener('pointermove', this.handlePointerMove);
    element.addEventListener('pointerup', this.handlePointerUp);
    element.addEventListener('pointercancel', this.handlePointerUp);
  }

  update(): void {
    this.orbitDelta.copy(this.pendingOrbitDelta);
    this.pendingOrbitDelta.set(0, 0);
  }

  getMovementAxes(target: Vector2): Vector2 {
    const left = this.isPressed('KeyA', 'ArrowLeft') ? 1 : 0;
    const right = this.isPressed('KeyD', 'ArrowRight') ? 1 : 0;
    const forward = this.isPressed('KeyW', 'ArrowUp') ? 1 : 0;
    const backward = this.isPressed('KeyS', 'ArrowDown') ? 1 : 0;

    return target.set(right - left, forward - backward);
  }

  /** Shift or Space: run while the player is on foot. */
  get isRunning(): boolean {
    return (
      this.pressedKeys.has('ShiftLeft') ||
      this.pressedKeys.has('ShiftRight') ||
      this.pressedKeys.has('Space')
    );
  }

  /** Shift alone: e-assist on a bike. */
  get isAssisting(): boolean {
    return this.pressedKeys.has('ShiftLeft') || this.pressedKeys.has('ShiftRight');
  }

  /** Space: boost on a bike. */
  get isBoosting(): boolean {
    return this.pressedKeys.has('Space');
  }

  consumeOverlayToggle(): boolean {
    const queued = this.overlayToggleQueued;
    this.overlayToggleQueued = false;
    return queued;
  }

  /** True once per E press; stays queued until a simulation step reads it. */
  consumeInteract(): boolean {
    const queued = this.interactQueued;
    this.interactQueued = false;
    return queued;
  }

  /** True once per C press: swing the camera behind the player. */
  consumeRecenter(): boolean {
    const queued = this.recenterQueued;
    this.recenterQueued = false;
    return queued;
  }

  private isPressed(primary: string, alternate: string): boolean {
    return this.pressedKeys.has(primary) || this.pressedKeys.has(alternate);
  }

  private readonly handleKeyDown = (event: KeyboardEvent): void => {
    const code = resolveCode(event);

    if (MOVEMENT_KEYS.has(code)) {
      event.preventDefault();
    }

    // A Cmd chord hands the keystroke to the system, and on iPadOS the matching
    // keyup never arrives, so every held key would stay down. Let go of them.
    if (event.metaKey || code === 'MetaLeft' || code === 'MetaRight') {
      this.pressedKeys.clear();
      return;
    }

    if (code === 'KeyH' && !event.repeat) {
      this.overlayToggleQueued = true;
    }

    if (code === 'KeyE' && !event.repeat) {
      this.interactQueued = true;
    }

    if (code === 'KeyC' && !event.repeat) {
      this.recenterQueued = true;
    }

    this.pressedKeys.add(code);
  };

  private readonly handleKeyUp = (event: KeyboardEvent): void => {
    const code = resolveCode(event);

    if (MOVEMENT_KEYS.has(code)) {
      event.preventDefault();
    }

    this.pressedKeys.delete(code);
  };

  private readonly handleVisibilityChange = (): void => {
    if (document.hidden) {
      this.resetTransientInput();
    }
  };

  private readonly handleBlur = (): void => {
    this.resetTransientInput();
  };

  /**
   * Focus loss is a boundary between input sessions. Discard both held state
   * and one-shot work so a queued interaction or pointer movement cannot fire
   * after the player returns to the tab.
   */
  private resetTransientInput(): void {
    this.pressedKeys.clear();
    this.pendingOrbitDelta.set(0, 0);
    this.orbitDelta.set(0, 0);
    this.overlayToggleQueued = false;
    this.interactQueued = false;
    this.recenterQueued = false;
    this.endDrag();
  }

  private readonly handlePointerDown = (event: PointerEvent): void => {
    if (event.button !== 0) {
      return;
    }

    // Embedded on danieloye.com, a click on the canvas does not reliably hand
    // keyboard focus to this frame (observed: document.activeElement on the
    // parent stays <body> after the click, so WASD never arrives here even
    // though the click itself lands correctly). Claiming focus explicitly
    // from within our own frame sidesteps whatever the host page is doing,
    // rather than depending on it.
    window.focus();

    this.isDragging = true;
    this.activePointerId = event.pointerId;
    this.lastPointerPosition.set(event.clientX, event.clientY);
    this.element.setPointerCapture(event.pointerId);
    this.element.classList.add('is-dragging');
    event.preventDefault();
  };

  private readonly handlePointerMove = (event: PointerEvent): void => {
    if (!this.isDragging || event.pointerId !== this.activePointerId) {
      return;
    }

    this.pendingOrbitDelta.x += event.clientX - this.lastPointerPosition.x;
    this.pendingOrbitDelta.y += event.clientY - this.lastPointerPosition.y;
    this.lastPointerPosition.set(event.clientX, event.clientY);
  };

  private readonly handlePointerUp = (event: PointerEvent): void => {
    if (event.pointerId !== this.activePointerId) {
      return;
    }

    if (this.element.hasPointerCapture(event.pointerId)) {
      this.element.releasePointerCapture(event.pointerId);
    }

    this.endDrag();
  };

  private endDrag(): void {
    this.isDragging = false;
    this.activePointerId = null;
    this.element.classList.remove('is-dragging');
  }
}
