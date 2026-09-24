// Generates the world-space puddle mask used by Stage 4b of the realism
// pass (docs/REALISM_PASS_PLAN.md): white = standing water, grey = damp,
// black = dry. Shared between the road and pavement materials
// (createRoadSurfaces.ts, createPavementSurfaces.ts), each sampling it at
// their own world-space scale/strength — puddles naturally span a kerb, so
// one mask keeps the two surfaces' wetness aligned rather than inventing two
// unrelated patterns.
//
// Kept separate from generateRoadTextures.mjs/generatePavementTextures.mjs:
// this isn't a road-specific or pavement-specific asset, and regenerating it
// should not force either of those to re-encode.
import { mkdirSync } from 'node:fs';
import { byte, clamp01, fbm, smoothstep, writePng } from './lib/textureTools.mjs';

const SIZE = 512;
const outputDirectory = new URL('../public/assets/textures/wet/', import.meta.url);
mkdirSync(outputDirectory, { recursive: true });

// Arbitrary but fixed, so regenerating this without changing the algorithm
// reproduces the same mask.
const SEED = 2609;
// Both layers are sampled in a [0, SCALE) coordinate space that exactly
// spans the image, with a matching `period` passed to `fbm` so the noise
// lattice wraps at the same point the image repeats — required for
// RepeatWrapping to tile seamlessly in-engine.
const BROAD_SCALE = 5;
const FINE_SCALE = 17;

/**
 * A broad layer lays out where puddles sit (the low points a street's camber
 * and gutters would actually collect water); a finer layer breaks each
 * puddle's edge into an irregular shape rather than a round blob, echoing
 * how real standing water follows cracks and surface unevenness. A puddle's
 * core reads fully wet; a softer damp halo fades out around it; everything
 * else stays dry.
 */
function puddleMaskValue(u, v) {
  const broad = fbm(u * BROAD_SCALE, v * BROAD_SCALE, SEED, 3, BROAD_SCALE);
  const fine = fbm(
    u * FINE_SCALE + 11,
    v * FINE_SCALE - 6,
    SEED + 41,
    3,
    FINE_SCALE,
  );
  const field = broad * 0.72 + fine * 0.28;
  // Thresholds chosen against the field's actual distribution (median
  // ~0.52, p95 ~0.69) so puddle cores cover roughly the top 4-5% of the
  // tile and the damp halo roughly a quarter — sparse, scattered puddles
  // rather than a uniformly damp street.
  const core = smoothstep(0.64, 0.75, field);
  const damp = smoothstep(0.58, 0.66, field);
  return clamp01(core + damp * 0.4 * (1 - core));
}

const pixels = Buffer.alloc(SIZE * SIZE * 3);
for (let y = 0; y < SIZE; y += 1) {
  for (let x = 0; x < SIZE; x += 1) {
    const value = byte(puddleMaskValue(x / SIZE, y / SIZE) * 255);
    const index = (y * SIZE + x) * 3;
    pixels[index] = value;
    pixels[index + 1] = value;
    pixels[index + 2] = value;
  }
}

writePng(outputDirectory, 'puddle-mask', SIZE, SIZE, 3, pixels);
console.log(`Wrote ${SIZE}x${SIZE} puddle-mask.png to ${outputDirectory.pathname}`);
