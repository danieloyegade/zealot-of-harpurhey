import assert from 'node:assert/strict';
import test from 'node:test';
import {
  QUAY_STREET_WIDTH,
  ROAD_WIDTH,
  wideRect,
  wideSideRoad,
  widePoint,
  wideX,
  wideZ,
} from '../src/world/roadWidening.ts';

const near = (actual, expected, message) =>
  assert.ok(Math.abs(actual - expected) < 1e-9, `${message}: ${actual} != ${expected}`);

test('the park, its pavements and the player start do not move', () => {
  for (const [x, z] of [[0, 0], [0, 3.5], [0, 19.95], [-24.4, 0], [24.4, 0], [0, -19.95]]) {
    const point = widePoint(x, z);
    near(point.x, x, `x of (${x}, ${z})`);
    near(point.z, z, `z of (${x}, ${z})`);
  }
});

test('each main road grows to its new width away from the park', () => {
  const ringNorth = wideRect({ x: 0, z: -25.5, width: 72, depth: 7.5 });
  near(ringNorth.depth, ROAD_WIDTH, 'ring north width');
  near(ringNorth.z + ringNorth.depth / 2, -21.75, 'ring north keeps its park-side edge');

  const quay = wideRect({ x: 0, z: -54.2, width: 114, depth: 7.5 });
  near(quay.depth, QUAY_STREET_WIDTH, 'Quay Street width');

  const outerWest = wideRect({ x: -48, z: -4.975, width: 7.5, depth: 105.95 });
  near(outerWest.width, ROAD_WIDTH, 'outer west width');
});

test('a block between two roads keeps its distance from the kerb it fronts', () => {
  // Renee's south frontage (Z = -32) sat 3.25 m from the ring's north kerb.
  const kerb = wideZ(-29.25);
  near(wideZ(-32) - kerb, -32 - -29.25, 'north block setback from the ring kerb');
  // Everything in the north block moves by the same amount.
  near(wideZ(-40) - -40, wideZ(-32) - -32, 'north block moves rigidly');
  // ...and Quay Street's south pavement keeps its distance from that block.
  near(wideZ(-49.45) - wideZ(-40), -49.45 - -40, 'rear pavement keeps its distance');
});

test('south and outer-south blocks move by the growth of the roads inside them', () => {
  near(wideZ(39) - 39, 2.5, 'south block');
  near(wideZ(69.75) - 69.75, 5, 'beyond the outer south road');
  near(wideZ(-70) - -70, -10, 'north of Quay Street');
});

test('the ring side streets push only the columns beside them', () => {
  near(wideX(-38, 0) - -38, -2.5, 'west column inside the ring');
  near(wideX(47, 20) - 47, 2.5, 'east column inside the ring');
  near(wideX(-29, -36), -29, 'north block is not pushed sideways');
  near(wideX(17, -38.6), 17, 'Renee stays put in X');
});

test('mapping is monotonic along both axes', () => {
  let previous = -Infinity;
  for (let z = -130; z <= 90; z += 0.25) {
    const mapped = wideZ(z);
    assert.ok(mapped > previous, `wideZ not increasing at ${z}`);
    previous = mapped;
  }
  for (const row of [0, -40, 45]) {
    previous = -Infinity;
    for (let x = -70; x <= 70; x += 0.25) {
      const mapped = wideX(x, row);
      assert.ok(mapped > previous - 1e-9, `wideX not increasing at ${x} (row ${row})`);
      previous = mapped;
    }
  }
});

test('Lower Byrom Street keeps the ABC Building side and takes its own width', () => {
  const lowerByrom = wideSideRoad({ x: 26.4, z: -86.975, width: 7.5, depth: 58.05 }, 'x', 9, 'low');
  near(lowerByrom.width, 9, 'width');
  near(lowerByrom.x - lowerByrom.width / 2, 26.4 - 3.75, 'west edge stays beside the ABC Building');
  near(lowerByrom.z - lowerByrom.depth / 2, -116 - 10, 'north end moves out with the block');
});
