import assert from 'node:assert/strict';
import test from 'node:test';
import { crossedFootfall } from '../src/player/footfall.ts';
import { bikeSoundLevels, SILENT_BIKE } from '../src/audio/bikeSoundModel.ts';

test('a foot lands twice per stride cycle, at the thigh-swing extremes', () => {
  let landings = 0;
  let phase = 0;
  const step = 0.125; // one 60 Hz tick of a walk
  for (let tick = 0; tick < Math.ceil((Math.PI * 2 * 10) / step); tick += 1) {
    const next = phase + step;
    if (crossedFootfall(phase, next)) landings += 1;
    phase = next;
  }
  // Ten full cycles: twenty landings, give or take the partial last step.
  assert.ok(landings >= 19 && landings <= 21, `landings: ${landings}`);
  assert.equal(crossedFootfall(0, Math.PI / 2 - 0.01), false);
  assert.equal(crossedFootfall(Math.PI / 2 - 0.01, Math.PI / 2 + 0.01), true);
  assert.equal(crossedFootfall(Math.PI / 2 + 0.01, Math.PI / 2 + 0.3), false);
  assert.equal(crossedFootfall(1.5 * Math.PI - 0.01, 1.5 * Math.PI + 0.01), true);
});

const rolling = { speed: 4.6, pedalling: 0, motorAssist: 0, braking: false };

test('a bike at rest, or being walked, is silent', () => {
  assert.deepEqual(bikeSoundLevels({ ...rolling, speed: 0 }), SILENT_BIKE);
  assert.deepEqual(bikeSoundLevels({ ...rolling, speed: -0.9 }), SILENT_BIKE);
});

test('tyre and wind build with speed, wind only really at boost', () => {
  const slow = bikeSoundLevels({ ...rolling, speed: 2 });
  const cruise = bikeSoundLevels(rolling);
  const boost = bikeSoundLevels({ ...rolling, speed: 20 });
  assert.ok(slow.tyreGain < cruise.tyreGain && cruise.tyreGain < boost.tyreGain);
  assert.ok(slow.tyreCentreHz < boost.tyreCentreHz);
  assert.ok(cruise.windGain < 0.02, `wind at cruise: ${cruise.windGain}`);
  assert.ok(boost.windGain > 0.1, `wind at boost: ${boost.windGain}`);
});

test('the freewheel ratchets while coasting and gives way to chain whirr while pedalling', () => {
  const coasting = bikeSoundLevels(rolling);
  const pedalling = bikeSoundLevels({ ...rolling, pedalling: 1 });
  assert.ok(coasting.ratchetGain > 0 && coasting.chainGain === 0);
  assert.ok(pedalling.ratchetGain === 0 && pedalling.chainGain > 0);
  // Pawl rate follows wheel speed.
  assert.ok(bikeSoundLevels({ ...rolling, speed: 6 }).ratchetRateHz > coasting.ratchetRateHz);
});

test('the motor whine follows assist, and the squeal follows braking at speed', () => {
  assert.equal(bikeSoundLevels(rolling).motorGain, 0);
  assert.ok(bikeSoundLevels({ ...rolling, pedalling: 1, motorAssist: 1 }).motorGain > 0);
  assert.equal(bikeSoundLevels(rolling).squealGain, 0);
  assert.ok(bikeSoundLevels({ ...rolling, speed: 6, braking: true }).squealGain > 0);
  assert.equal(bikeSoundLevels({ ...rolling, speed: 1, braking: true }).squealGain, 0);
});
