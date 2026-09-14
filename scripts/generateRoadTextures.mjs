// Generates the layered road material set under public/assets/textures/road/:
//
//   road-asphalt-{albedo,roughness,normal}.png  tiled 4 m base asphalt
//   road-variation.png                          low-frequency tone/roughness drift
//   road-decal-{albedo,roughness,normal}.png    1024 px decal atlas
//
// The atlas layout is shared with the runtime through
// src/rendering/roadDecalAtlas.json. Every cell here is a procedural stand-in
// for a photograph in the Zealot Road Atlas (docs/ROAD_ATLAS.md): replace a
// cell's painter with a photographic derivative without moving the cell and
// the placement code keeps working.
//
// Kept separate from generateWorldTextures.mjs so regenerating roads does not
// re-encode the unrelated world texture pack.
import { mkdirSync, readFileSync } from 'node:fs';
import {
  aggregate,
  blobDistance,
  byte,
  clamp01,
  crackPoints,
  endFade,
  fbm,
  grey,
  hash,
  heightToNormal,
  mix,
  mulberry32,
  sample,
  smoothstep,
  strokeMask,
  writeDecalAtlas,
  writePng,
} from './lib/textureTools.mjs';

const atlas = JSON.parse(
  readFileSync(new URL('../src/rendering/roadDecalAtlas.json', import.meta.url), 'utf8'),
);
const outputDirectory = new URL('../public/assets/textures/road/', import.meta.url);
mkdirSync(outputDirectory, { recursive: true });

/** Worn thermoplastic paint shared by dashes, bars and yellow lines. */
function paintSample(px, py, u, v, options) {
  const {
    seed, color, wear, halfWidth, endRagged = true, trackPositions = [], crackSpacing = 0,
  } = options;
  const edgeNoise = (fbm(u * 60, v, seed, 2) - 0.5) * 0.14;
  const across = Math.abs(v - 0.5) - (halfWidth + edgeNoise);
  const endNoise = endRagged ? fbm(v * 4, u * 2, seed + 1, 2) * 0.012 : 0;
  const alongEdge = Math.min(u, 1 - u) - (0.008 + endNoise);
  const body = smoothstep(0.03, -0.03, across) * smoothstep(-0.002, 0.004, alongEdge);
  let erosion = fbm(u * 26, v * 2.4, seed + 2, 4);
  let tyre = 0;
  for (const track of trackPositions) {
    tyre = Math.max(tyre, Math.exp(-(((u - track) / 0.045) ** 2)));
  }
  erosion += tyre * 0.32;
  const remaining = smoothstep(wear + 0.06, wear - 0.04, erosion);
  const voids = hash(px, py, seed + 3) < 0.05 ? 0.6 : 1;
  let crack = 0;
  if (crackSpacing > 0) {
    const phase = (u + (fbm(v * 3, u * 5, seed + 4, 2) - 0.5) * 0.01) / crackSpacing;
    crack = smoothstep(0.035, 0.0, Math.abs(phase - Math.round(phase)) * crackSpacing * 40)
      * (hash(Math.round(phase), 0, seed + 5) > 0.35 ? 1 : 0);
  }
  const dirt = fbm(u * 18, v * 3, seed + 6, 3);
  const coverage = body * remaining * voids * (1 - crack * 0.5);
  const darken = 1 - (dirt - 0.35) * 0.42 - tyre * 0.3;
  return sample(
    coverage * 0.94,
    color.map((channel) => channel * darken),
    mix(0.62, 0.72, dirt),
    coverage * 0.9 - crack * 0.6,
  );
}

// ---------------------------------------------------------------------------
// Cell painters. Each returns (px, py, u, v) => sample. For strips, u runs
// along the length and v across it; for kerb-side cells v = 0 is the kerb.

const painters = {
  'patch-rect-a': () => (px, py, u, v) => {
    const ex = (fbm(v * 5, 0.5, 31, 3) - 0.5) * 0.05;
    const ey = (fbm(u * 5, 1.5, 32, 3) - 0.5) * 0.05;
    const d = Math.max(Math.abs(u - 0.5) - (0.41 + ex), Math.abs(v - 0.5) - (0.37 + ey));
    if (d > 0.02) {
      const halo = smoothstep(0.07, 0.02, d) * (hash(px, py, 43) > 0.72 ? 0.5 : 0.1);
      return sample(halo, [74, 70, 62], 0.95, 0.3 * halo);
    }
    const agg = aggregate(px, py, 41, 33, 0.7);
    const seamBreak = fbm(u * 7, v * 7, 45, 3) > 0.7 ? 0.3 : 1;
    const seam = smoothstep(0.02, 0.006, Math.abs(d + 0.004)) * seamBreak;
    const inside = smoothstep(0.004, -0.004, d);
    return sample(
      Math.max(inside * 0.93, seam * 0.95),
      grey(mix(agg.value, 12, seam)),
      mix(0.74 + agg.rough, 0.34, seam),
      mix(agg.height - 0.35, 0.5, seam),
    );
  },

  'patch-rect-b': () => {
    const rng = mulberry32(51);
    const cracks = strokeMask(256, 256, [
      { points: crackPoints(rng, 40, 60, 0.5, 14, 9, 0.9), radius: 1.3 },
      { points: crackPoints(rng, 210, 190, 3.5, 10, 8, 1.1), radius: 1.1 },
    ]);
    return (px, py, u, v) => {
      const ex = (fbm(v * 7, 2.5, 53, 3) - 0.5) * 0.08;
      const ey = (fbm(u * 7, 3.5, 54, 3) - 0.5) * 0.08;
      const d = Math.max(Math.abs(u - 0.5) - (0.39 + ex), Math.abs(v - 0.5) - (0.4 + ey));
      const inside = smoothstep(0.01, -0.01, d);
      const crumbled = fbm(u * 11, v * 11, 55, 3) > 0.52 ? 1 : 0.15;
      const seam = smoothstep(0.022, 0.006, Math.abs(d)) * crumbled;
      const agg = aggregate(px, py, 57, 52, 1.1);
      const crack = cracks[py * 256 + px] * inside;
      const faded = fbm(u * 3, v * 3, 58, 3);
      return sample(
        Math.max(inside * mix(0.62, 0.86, faded), seam * 0.8),
        grey(mix(mix(agg.value, 20, seam * 0.8), 16, crack), 3),
        mix(0.9 + agg.rough, 0.5, seam * 0.6),
        agg.height - crack * 1.2 + seam * 0.3,
      );
    };
  },

  'patch-irregular-a': () => (px, py, u, v) => {
    const d = blobDistance(u, v, 61, 0.36, 0.3, 1, 0.78);
    if (d > 0.14) return sample(0, [60, 58, 54], 0.9);
    const agg = aggregate(px, py, 63, 30, 0.35);
    if (d > 0) {
      const grit = hash(px, py, 65) > 0.55 ? 1 : 0.2;
      const ravel = smoothstep(0.14, 0.0, d) * grit;
      return sample(ravel * 0.62, [96, 88, 74], 0.96, ravel * 0.6);
    }
    return sample(0.9, grey(agg.value), 0.58 + agg.rough, agg.height - 0.1);
  },

  'patch-irregular-b': () => (px, py, u, v) => {
    const d = blobDistance(u, v, 71, 0.4, 0.28, 1.05, 0.85);
    const inside = smoothstep(0.05, -0.08, d);
    const agg = aggregate(px, py, 73, 49, 0.9);
    const fade = fbm(u * 4, v * 4, 75, 3);
    return sample(
      inside * mix(0.45, 0.8, fade),
      grey(agg.value, 2),
      0.88 + agg.rough,
      agg.height,
    );
  },

  'pothole-fill-a': () => (px, py, u, v) => {
    const d = blobDistance(u, v, 81, 0.3, 0.34, 1, 0.82);
    if (d > 0.35) return sample(0, [50, 48, 44], 0.9);
    if (d > 0.04) {
      const stones = hash(px >> 1, py >> 1, 83) > 0.8 ? 1 : 0;
      const loose = smoothstep(0.35, 0.05, d) * stones;
      return sample(loose * 0.9, grey(70 + hash(px, py, 84) * 30), 0.9, loose * 1.4);
    }
    const agg = aggregate(px, py, 85, 28, 0.5);
    const lip = smoothstep(-0.18, 0.02, d);
    return sample(0.97, grey(agg.value + lip * 6), 0.52 + agg.rough, mix(-0.9, 0.7, lip) + agg.height);
  },

  'pothole-fill-b': () => (px, py, u, v) => {
    const d = blobDistance(u, v, 91, 0.28, 0.4, 1, 0.74);
    const inside = smoothstep(0.08, -0.05, d);
    const agg = aggregate(px, py, 93, 29, 2);
    const depth = smoothstep(0.02, -0.6, d);
    return sample(
      inside * 0.95,
      grey(agg.value - depth * 8, -2),
      mix(0.8, 0.46, depth) + agg.rough,
      -depth * 1.6 + agg.height,
    );
  },

  'crack-web': () => {
    const rng = mulberry32(101);
    const strokes = [];
    for (let index = 0; index < 7; index += 1) {
      strokes.push({
        points: crackPoints(rng, 48 + rng() * 160, 48 + rng() * 160, rng() * Math.PI * 2, 12 + Math.floor(rng() * 10), 8, 1.2),
        radius: 1 + rng() * 1.4,
      });
    }
    const mask = strokeMask(256, 256, strokes);
    return (px, py, u, v) => {
      const crack = mask[py * 256 + px] * endFade(u, 0.12) * endFade(v, 0.12);
      return sample(crack * 0.88, [12, 12, 13], 0.92, -crack * 1.5);
    };
  },

  'oil-stain': () => {
    const rng = mulberry32(111);
    const drops = Array.from({ length: 9 }, () => ({
      x: 0.3 + rng() * 0.4,
      y: 0.25 + rng() * 0.5,
      r: 0.05 + rng() * 0.12,
    }));
    return (px, py, u, v) => {
      let density = 0;
      for (const drop of drops) {
        density += Math.exp(-(((u - drop.x) ** 2 + (v - drop.y) ** 2) / (drop.r * drop.r)));
      }
      const breakup = fbm(u * 9, v * 9, 113, 3);
      const alpha = clamp01(density * 0.6) * mix(0.5, 1, breakup) * 0.6;
      return sample(alpha, [16, 15, 16], 0.4, 0);
    };
  },

  'wet-patch-a': () => (px, py, u, v) => {
    const d = blobDistance(u, v, 121, 0.34, 0.32, 1, 0.8);
    const wet = smoothstep(0.25, -0.35, d);
    const breakup = fbm(u * 6, v * 6, 123, 3);
    return sample(
      wet * mix(0.3, 0.48, breakup),
      [16, 17, 19],
      mix(0.52, 0.18, wet),
      0,
    );
  },

  'wet-patch-b': () => (px, py, u, v) => {
    const falloff = smoothstep(0.5, 0.18, Math.hypot((u - 0.5) * 0.9, (v - 0.5) * 1.4));
    const islands = smoothstep(0.42, 0.56, fbm(u * 7, v * 7, 131, 4) * falloff + falloff * 0.35);
    return sample(islands * 0.5, [14, 15, 17], mix(0.5, 0.14, islands), -islands * 0.2);
  },

  'zebra-stripe-a': () => (px, py, u, v) => paintSample(px, py, u, v, {
    seed: 141,
    color: [214, 210, 196],
    wear: 0.8,
    halfWidth: 0.38,
    trackPositions: [0.2, 0.39, 0.61, 0.8],
    crackSpacing: 0.11,
  }),

  'zebra-stripe-b': () => (px, py, u, v) => paintSample(px, py, u, v, {
    seed: 151,
    color: [196, 192, 180],
    wear: 0.68,
    halfWidth: 0.37,
    trackPositions: [0.18, 0.36, 0.63, 0.82],
    crackSpacing: 0.08,
  }),

  'gutter-litter': () => {
    const rng = mulberry32(161);
    const items = Array.from({ length: 70 }, () => {
      const kind = rng();
      return {
        x: rng() * 512,
        y: Math.pow(rng(), 1.8) * 70,
        angle: rng() * Math.PI,
        kind: kind < 0.62 ? 'leaf' : kind < 0.84 ? 'stone' : 'butt',
        size: kind < 0.62 ? 4 + rng() * 6 : 1.5 + rng() * 2.5,
        tone: rng(),
      };
    });
    return (px, py, u, v) => {
      const silt = smoothstep(0.7, 0.0, v) * smoothstep(0.4, 0.7, fbm(u * 20, v * 4, 163, 3));
      let best = sample(silt * 0.55 * endFade(u), [44, 40, 32], 0.72, silt * 0.3);
      for (const item of items) {
        const dx = px - item.x;
        const dy = py - item.y;
        if (Math.abs(dx) > 12 || Math.abs(dy) > 12) continue;
        const ca = Math.cos(item.angle);
        const sa = Math.sin(item.angle);
        const lx = dx * ca + dy * sa;
        const ly = -dx * sa + dy * ca;
        if (item.kind === 'leaf') {
          const inside = (lx / item.size) ** 2 + (ly / (item.size * 0.45)) ** 2;
          if (inside < 1) {
            const vein = Math.abs(ly) < 0.6 ? 0.8 : 1;
            best = sample(0.9 * endFade(u), mix([118, 76, 32], [84, 70, 38], item.tone).map((c) => c * vein), 0.78, 0.6);
          }
        } else if (item.kind === 'stone') {
          if (Math.hypot(lx, ly) < item.size) {
            best = sample(0.95 * endFade(u), grey(66 + item.tone * 40), 0.86, 1.2);
          }
        } else if (Math.abs(lx) < 4.5 && Math.abs(ly) < 1.2) {
          best = sample(0.95 * endFade(u), lx > 2.5 ? [168, 112, 60] : [206, 198, 180], 0.8, 0.8);
        }
      }
      return best;
    };
  },

  'crack-long': () => {
    const rng = mulberry32(171);
    // A free random walk leaves an 80 px strip within a few steps, so the
    // main crack meanders about the strip's centre instead.
    const main = [];
    for (let x = 8; x <= 504; x += 6) {
      main.push([x, 40 + (fbm(x / 90, 0.5, 175, 3) - 0.5) * 44 + (rng() - 0.5) * 3]);
    }
    const strokes = [{ points: main, radius: 1.8, taper: 0.3 }];
    for (let index = 0; index < 6; index += 1) {
      const origin = main[6 + Math.floor(rng() * (main.length - 12))];
      strokes.push({
        points: crackPoints(rng, origin[0], origin[1], (rng() < 0.5 ? -1 : 1) * (0.9 + rng() * 0.7), 4 + Math.floor(rng() * 4), 6, 1),
        radius: 1.1,
      });
    }
    const crack = strokeMask(512, 80, strokes);
    const band = strokeMask(512, 80, [{ points: main, radius: 7, taper: 0 }]);
    return (px, py, u) => {
      const offset = py * 512 + px;
      const tar = band[offset] * (fbm(u * 14, 0.5, 173, 3) > 0.46 ? 1 : 0) * endFade(u, 0.03);
      const split = crack[offset] * endFade(u, 0.02);
      return sample(
        Math.max(tar * 0.88, split * 0.9),
        grey(tar > split ? 9 : 13),
        tar > split ? 0.3 : 0.92,
        tar * 0.5 - split * 1.4,
      );
    };
  },

  trench: () => (px, py, u, v) => {
    const edgeWobble = (fbm(u * 40, 0.5, 181, 2) - 0.5) * 0.04;
    const across = Math.abs(v - 0.5) - (0.4 + edgeWobble);
    const along = Math.min(u, 1 - u) - 0.006;
    const d = Math.max(across, -along * 18);
    const inside = smoothstep(0.02, -0.02, d);
    const seam = smoothstep(0.08, 0.02, Math.abs(d)) * (fbm(u * 30, v, 183, 2) > 0.34 ? 1 : 0.2);
    const agg = aggregate(px, py, 185, 46, 0.95);
    const settle = smoothstep(0.4, 0.0, Math.abs(v - 0.5));
    return sample(
      Math.max(inside * 0.9, seam * 0.92),
      grey(mix(agg.value - settle * 5, 11, seam), 2),
      mix(0.86 + agg.rough, 0.34, seam),
      agg.height - settle * 0.3 + seam * 0.4,
    );
  },

  'gutter-grime-a': () => (px, py, u, v) => {
    const clumps = fbm(u * 60, v * 3, 191, 4);
    const density = Math.pow(smoothstep(1, 0, v), 1.5) * mix(0.45, 1, clumps);
    const moss = smoothstep(0.58, 0.72, fbm(u * 24, v * 2, 193, 3)) * smoothstep(0.45, 0, v);
    const silt = smoothstep(0.66, 0.78, fbm(u * 38, v * 5, 195, 3));
    const speck = hash(px, py, 197) > 0.985 ? 1 : 0;
    let color = mix([24, 23, 20], [34, 46, 27], moss);
    color = mix(color, [92, 82, 64], silt * 0.7);
    if (speck) color = [110, 84, 48];
    return sample(
      clamp01(density * 0.9 + speck * 0.4) * endFade(u),
      color,
      mix(0.46, 0.9, v + silt * 0.3),
      silt * 0.4 + speck * 0.6,
    );
  },

  'gutter-grime-b': () => (px, py, u, v) => {
    const drift = fbm(u * 40, v * 4, 201, 4);
    const density = Math.pow(smoothstep(1, 0, v), 1.2) * mix(0.35, 1, drift);
    const stone = hash(px >> 1, py >> 1, 203) > 0.93 ? 1 : 0;
    const stoneTone = hash(px >> 1, py >> 1, 205);
    const color = stone ? grey(64 + stoneTone * 42) : mix([62, 56, 44], [104, 94, 74], drift);
    return sample(
      clamp01(density * 0.78 + stone * density) * endFade(u),
      color,
      0.95,
      stone * 1.3 + density * 0.2,
    );
  },

  'tyre-stain': () => (px, py, u, v) => {
    const centre = 0.5 + (fbm(u * 3, 0.5, 211, 2) - 0.5) * 0.18;
    const band = Math.exp(-(((v - centre) / 0.26) ** 2));
    const streaks = fbm(u * 2.5, v * 28, 213, 3);
    return sample(
      band * mix(0.18, 0.6, streaks) * endFade(u, 0.12),
      [14, 14, 15],
      0.66,
      0,
    );
  },

  'tar-seam': () => (px, py, u, v) => {
    const centre = 0.5 + (fbm(u * 10, 0.5, 221, 3) - 0.5) * 0.35;
    const halfWidth = 0.26 + (fbm(u * 30, 1.5, 223, 2) - 0.5) * 0.12;
    const line = smoothstep(halfWidth + 0.08, halfWidth - 0.04, Math.abs(v - centre));
    const broken = fbm(u * 18, 2.5, 225, 2) > 0.74 ? 0.35 : 1;
    return sample(line * broken * 0.95 * endFade(u, 0.02), [8, 8, 9], 0.3, line * 0.5);
  },

  'line-white-a': () => (px, py, u, v) => paintSample(px, py, u, v, {
    seed: 231,
    color: [216, 212, 200],
    wear: 0.8,
    halfWidth: 0.36,
    crackSpacing: 0.045,
  }),

  'line-white-b': () => (px, py, u, v) => paintSample(px, py, u, v, {
    seed: 241,
    color: [192, 188, 176],
    wear: 0.62,
    halfWidth: 0.34,
    trackPositions: [0.3, 0.72],
    crackSpacing: 0.03,
  }),

  'line-yellow': () => (px, py, u, v) => paintSample(px, py, u, v, {
    seed: 251,
    color: [198, 152, 40],
    wear: 0.72,
    halfWidth: 0.36,
    endRagged: false,
    crackSpacing: 0.02,
  }),
};

// ---------------------------------------------------------------------------
// Base asphalt: 512 px = 4 m, tiles seamlessly.

const BASE = 512;
{
  const albedo = Buffer.alloc(BASE * BASE * 3);
  const roughness = Buffer.alloc(BASE * BASE * 3);
  const heights = new Float32Array(BASE * BASE);
  for (let y = 0; y < BASE; y += 1) {
    for (let x = 0; x < BASE; x += 1) {
      const broad = fbm(x / 64, y / 64, 11, 3, 8);
      const fine = fbm(x / 8, y / 8, 13, 3, 64);
      const grit = hash(x, y, 17);
      const chip = hash(x >> 1, y >> 1, 19);
      const chipTone = hash(x >> 1, y >> 1, 23);
      let value = 38 + (broad - 0.5) * 10 + (fine - 0.5) * 16 + (grit - 0.5) * 10;
      let height = (fine - 0.5) * 0.8 + (grit - 0.5) * 0.3;
      let rough = 0.86 + (fine - 0.5) * 0.08;
      let warmth = 0;
      if (chip > 0.88) {
        value += 16 + chipTone * 22;
        height += 0.9;
        rough -= 0.18;
        warmth = chipTone > 0.7 ? 7 : 0;
      } else if (grit < 0.07) {
        value -= 14;
        height -= 1;
        rough += 0.08;
      }
      const offset = (y * BASE + x) * 3;
      const color = grey(value, warmth);
      albedo[offset] = byte(color[0]);
      albedo[offset + 1] = byte(color[1]);
      albedo[offset + 2] = byte(color[2]);
      roughness.fill(byte(clamp01(rough) * 255), offset, offset + 3);
      heights[y * BASE + x] = height;
    }
  }
  writePng(outputDirectory, 'road-asphalt-albedo', BASE, BASE, 3, albedo);
  writePng(outputDirectory, 'road-asphalt-roughness', BASE, BASE, 3, roughness);
  writePng(outputDirectory, 'road-asphalt-normal', BASE, BASE, 3, heightToNormal(heights, BASE, BASE, 0.5, true));
}

// Low-frequency drift sampled at two world scales by the road shader:
// R broad tone, G roughness drift, B warm/cool balance.
{
  const SIZE = 256;
  // Lattice periods divide 256 so every channel tiles.
  const channels = [
    (x, y) => fbm(x / 64, y / 64, 301, 3, 4),
    (x, y) => fbm(x / 32, y / 32, 311, 3, 8),
    (x, y) => fbm(x / 64, y / 64, 321, 2, 4),
  ];
  const raw = channels.map((channel) => {
    const values = new Float32Array(SIZE * SIZE);
    for (let y = 0; y < SIZE; y += 1) {
      for (let x = 0; x < SIZE; x += 1) values[y * SIZE + x] = channel(x, y);
    }
    let min = Infinity;
    let max = -Infinity;
    for (const value of values) {
      min = Math.min(min, value);
      max = Math.max(max, value);
    }
    return values.map((value) => (value - min) / (max - min));
  });
  const pixels = Buffer.alloc(SIZE * SIZE * 3);
  for (let index = 0; index < SIZE * SIZE; index += 1) {
    pixels[index * 3] = byte(raw[0][index] * 255);
    pixels[index * 3 + 1] = byte(raw[1][index] * 255);
    pixels[index * 3 + 2] = byte(raw[2][index] * 255);
  }
  writePng(outputDirectory, 'road-variation', SIZE, SIZE, 3, pixels);
}

// ---------------------------------------------------------------------------
// Decal atlas.

writeDecalAtlas(outputDirectory, 'road-decal', atlas, painters);
