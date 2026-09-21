import assert from 'node:assert/strict';
import test from 'node:test';
import { advanceDeliveryPhase } from '../src/delivery/deliveryState.ts';

test('the first delivery advances through pickup, transit and completion', () => {
  const carrying = advanceDeliveryPhase('awaiting-pickup');
  const delivered = advanceDeliveryPhase(carrying);

  assert.equal(carrying, 'in-transit');
  assert.equal(delivered, 'complete');
  assert.equal(advanceDeliveryPhase(delivered), 'complete');
});
