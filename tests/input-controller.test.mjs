import assert from 'node:assert/strict';
import test from 'node:test';
import { InputController } from '../src/input/InputController.ts';

class FakeCanvas extends EventTarget {
  classList = { add() {}, remove() {} };
  setPointerCapture() {}
  releasePointerCapture() {}
  hasPointerCapture() { return false; }
}

function keyEvent(code) {
  return {
    code,
    key: code === 'KeyE' ? 'e' : '',
    metaKey: false,
    repeat: false,
    preventDefault() {},
  };
}

test('focus loss discards queued actions and pointer movement', () => {
  const previousWindow = globalThis.window;
  const previousDocument = globalThis.document;
  const fakeWindow = new EventTarget();
  const fakeDocument = new EventTarget();
  Object.defineProperty(fakeDocument, 'hidden', { value: false, writable: true });
  globalThis.window = fakeWindow;
  globalThis.document = fakeDocument;

  try {
    const input = new InputController(new FakeCanvas());
    input.handleKeyDown(keyEvent('KeyE'));
    input.handleKeyDown(keyEvent('KeyC'));
    input.handleKeyDown(keyEvent('KeyH'));
    input.pendingOrbitDelta.set(18, -7);

    input.handleBlur();
    input.update();

    assert.equal(input.consumeInteract(), false);
    assert.equal(input.consumeRecenter(), false);
    assert.equal(input.consumeOverlayToggle(), false);
    assert.deepEqual(input.orbitDelta.toArray(), [0, 0]);
  } finally {
    globalThis.window = previousWindow;
    globalThis.document = previousDocument;
  }
});
