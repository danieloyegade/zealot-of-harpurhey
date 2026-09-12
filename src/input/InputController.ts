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

const ZOOM_METRES_PER_NOTCH = 0.0045;

export class InputController {
  // Orbit travel expressed in screen heights, so sensitivity is independent
  // of display size.
  readonly orbitDelta = new Vector2();

  zoomDelta = 0;

  private readonly pressedKeys = new Set<string>();
  private readonly pendingOrbitDelta = new Vector2();
  private readonly lastPointerPosition = new Vector2();
  private pendingZoomDelta = 0;
  private isDragging = false;
  private isPointerLocked = false;
  private activePointerId: number | null = null;
  private overlayToggleQueued = false;
  private recenterQueued = false;

  constructor(private readonly element: HTMLCanvasElement) {
    window.addEventListener('keydown', this.handleKeyDown);
    window.addEventListener('keyup', this.handleKeyUp);
    window.addEventListener('blur', this.handleBlur);
    document.addEventListener('pointerlockchange', this.handlePointerLockChange);
    element.addEventListener('pointerdown', this.handlePointerDown);
    element.addEventListener('pointermove', this.handlePointerMove);
    element.addEventListener('pointerup', this.handlePointerUp);
    element.addEventListener('pointercancel', this.handlePointerUp);
    element.addEventListener('wheel', this.handleWheel, { passive: false });
  }

  update(): void {
    const screenHeight = this.element.clientHeight || window.innerHeight || 1;
    this.orbitDelta.copy(this.pendingOrbitDelta).divideScalar(screenHeight);
    this.pendingOrbitDelta.set(0, 0);
    this.zoomDelta = this.pendingZoomDelta;
    this.pendingZoomDelta = 0;
  }

  getMovementAxes(target: Vector2): Vector2 {
    const left = this.isPressed('KeyA', 'ArrowLeft') ? 1 : 0;
    const right = this.isPressed('KeyD', 'ArrowRight') ? 1 : 0;
    const forward = this.isPressed('KeyW', 'ArrowUp') ? 1 : 0;
    const backward = this.isPressed('KeyS', 'ArrowDown') ? 1 : 0;

    return target.set(right - left, forward - backward);
  }

  getKeyboardOrbitYaw(): number {
    const left = this.pressedKeys.has('KeyQ') ? 1 : 0;
    const right = this.pressedKeys.has('KeyE') ? 1 : 0;

    return right - left;
  }

  getKeyboardOrbitPitch(): number {
    const up = this.pressedKeys.has('KeyR') ? 1 : 0;
    const down = this.pressedKeys.has('KeyF') ? 1 : 0;

    return down - up;
  }

  get isWalking(): boolean {
    return (
      this.pressedKeys.has('ShiftLeft') || this.pressedKeys.has('ShiftRight')
    );
  }

  consumeOverlayToggle(): boolean {
    const queued = this.overlayToggleQueued;
    this.overlayToggleQueued = false;
    return queued;
  }

  consumeRecenterRequest(): boolean {
    const queued = this.recenterQueued;
    this.recenterQueued = false;
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

    if (event.code === 'KeyC' && !event.repeat) {
      this.recenterQueued = true;
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
    this.pendingOrbitDelta.set(0, 0);
    this.endDrag();
  };

  private readonly handlePointerDown = (event: PointerEvent): void => {
    if (event.button !== 0 || this.isPointerLocked) {
      return;
    }

    // Drag-to-orbit stays live as the fallback for the frames before the lock
    // engages, and for browsers that refuse the request outright.
    this.isDragging = true;
    this.activePointerId = event.pointerId;
    this.lastPointerPosition.set(event.clientX, event.clientY);
    this.element.setPointerCapture(event.pointerId);
    this.element.classList.add('is-dragging');
    event.preventDefault();

    void Promise.resolve(this.element.requestPointerLock()).catch(() => {
      // Locking is a convenience; dragging already covers this case.
    });
  };

  private readonly handlePointerMove = (event: PointerEvent): void => {
    if (this.isPointerLocked) {
      this.pendingOrbitDelta.x += event.movementX;
      this.pendingOrbitDelta.y += event.movementY;
      return;
    }

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

  private readonly handlePointerLockChange = (): void => {
    this.isPointerLocked = document.pointerLockElement === this.element;

    if (this.isPointerLocked) {
      this.endDrag();
    }
  };

  private readonly handleWheel = (event: WheelEvent): void => {
    event.preventDefault();
    this.pendingZoomDelta += event.deltaY * ZOOM_METRES_PER_NOTCH;
  };

  private endDrag(): void {
    this.isDragging = false;
    this.activePointerId = null;
    this.element.classList.remove('is-dragging');
  }
}
