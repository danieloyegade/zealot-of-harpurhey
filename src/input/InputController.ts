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
 * Wheel deltas arrive in wildly different units across browsers and devices
 * (pixels, lines, pages). Normalising to notches keeps zoom speed consistent.
 */
const WHEEL_PIXELS_PER_NOTCH = 100;
const WHEEL_LINES_PER_NOTCH = 3;

export class InputController {
  readonly orbitDelta = new Vector2();

  private readonly pressedKeys = new Set<string>();
  private readonly pendingOrbitDelta = new Vector2();
  private readonly lastPointerPosition = new Vector2();
  private isDragging = false;
  private activePointerId: number | null = null;
  private overlayToggleQueued = false;
  private pendingZoomNotches = 0;
  private interactionQueued = false;

  constructor(private readonly element: HTMLCanvasElement) {
    window.addEventListener('keydown', this.handleKeyDown);
    window.addEventListener('keyup', this.handleKeyUp);
    window.addEventListener('blur', this.handleBlur);
    element.addEventListener('pointerdown', this.handlePointerDown);
    element.addEventListener('pointermove', this.handlePointerMove);
    element.addEventListener('pointerup', this.handlePointerUp);
    element.addEventListener('pointercancel', this.handlePointerUp);
    element.addEventListener('wheel', this.handleWheel, { passive: false });
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

  get isRunning(): boolean {
    return (
      this.pressedKeys.has('ShiftLeft') ||
      this.pressedKeys.has('ShiftRight') ||
      this.pressedKeys.has('Space')
    );
  }

  consumeOverlayToggle(): boolean {
    const queued = this.overlayToggleQueued;
    this.overlayToggleQueued = false;
    return queued;
  }

  /** Positive notches pull the camera back, negative push it in. */
  consumeZoomDelta(): number {
    const pending = this.pendingZoomNotches;
    this.pendingZoomNotches = 0;
    return pending;
  }

  /**
   * Seam for the delivery/interaction loop, which does not exist yet. Nothing
   * consumes this so far, and no on-screen prompt advertises the key: the
   * plumbing is here so the first interaction does not have to re-thread
   * input, not because `E` currently does anything.
   */
  consumeInteraction(): boolean {
    const queued = this.interactionQueued;
    this.interactionQueued = false;
    return queued;
  }

  private isPressed(primary: string, alternate: string): boolean {
    return this.pressedKeys.has(primary) || this.pressedKeys.has(alternate);
  }

  private readonly handleKeyDown = (event: KeyboardEvent): void => {
    if (MOVEMENT_KEYS.has(event.code)) {
      event.preventDefault();
    }

    if (event.code === 'KeyH' && !event.repeat) {
      this.overlayToggleQueued = true;
    }

    if (event.code === 'KeyE' && !event.repeat) {
      this.interactionQueued = true;
    }

    this.pressedKeys.add(event.code);
  };

  private readonly handleKeyUp = (event: KeyboardEvent): void => {
    if (MOVEMENT_KEYS.has(event.code)) {
      event.preventDefault();
    }

    this.pressedKeys.delete(event.code);
  };

  private readonly handleBlur = (): void => {
    this.pressedKeys.clear();
    this.pendingZoomNotches = 0;
    this.endDrag();
  };

  private readonly handleWheel = (event: WheelEvent): void => {
    event.preventDefault();

    const scale = event.deltaMode === WheelEvent.DOM_DELTA_LINE
      ? WHEEL_LINES_PER_NOTCH
      : event.deltaMode === WheelEvent.DOM_DELTA_PAGE
        ? 1
        : WHEEL_PIXELS_PER_NOTCH;

    this.pendingZoomNotches += event.deltaY / scale;
  };

  private readonly handlePointerDown = (event: PointerEvent): void => {
    if (event.button !== 0) {
      return;
    }

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
