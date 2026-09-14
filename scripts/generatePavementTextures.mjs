// Generates the layered pavement material set under public/assets/textures/pavement/:
//
//   pavement-{albedo,roughness,normal}.png        2.4 m tile of 600 mm flags
//   pavement-decal-{albedo,roughness,normal}.png  1024 px decal atlas
//
// Tone drift reuses the road set's road-variation.png. The atlas layout is
// shared with the runtime through src/rendering/pavementDecalAtlas.json. As
// with the roads, every cell is a procedural stand-in for a photograph; see
// docs/ROAD_ATLAS.md.
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
  readFileSync(new URL('../src/rendering/pavementDecalAtlas.json', import.meta.url), 'utf8'),
);
const outputDirectory = new URL('../public/assets/textures/pavement/', import.meta.url);
mkdirSync(outputDirectory, { recursive: true });

// ---------------------------------------------------------------------------
// Base flags: 512 px = 2.4 m = 4 × 4 flags of 600 mm in half bond.
//
// Rows are counted from the bottom of the image, which is texture v = 0 and the
// kerb edge at runtime. The pavement shader and flag-aligned decals use the same
// grid: row = floor(v / 0.6 m), and odd rows shift 300 mm along u.

const BASE = 512;
const FLAG = 128;
{
  const albedo = Buffer.alloc(BASE * BASE * 3);
  const roughness = Buffer.alloc(BASE * BASE * 3);
  const heights = new Float32Array(BASE * BASE);
  for (let y = 0; y < BASE; y += 1) {
    for (let x = 0; x < BASE; x += 1) {
      const row = 3 - Math.floor(y / FLAG);
      const offset = (row % 2) * (FLAG / 2);
      const shifted = (x + offset) % BASE;
      const column = Math.floor(shifted / FLAG);
      const localX = shifted % FLAG;
      const localY = y % FLAG;
      const edge = Math.min(localX, FLAG - 1 - localX, localY, FLAG - 1 - localY);
      const flag = hash(column, row, 401);
      const fine = fbm(x / 16, y / 16, 403, 3, 32);
      const grit = hash(x, y, 405);
      const wear = fbm(x / 32, y / 32, 407, 3, 16);

      let value = 116 + (fine - 0.5) * 16 + (grit - 0.5) * 12 + (wear - 0.5) * 14 + (flag - 0.5) * 8;
      let height = (fine - 0.5) * 0.5 + (grit - 0.5) * 0.2;
      let rough = 0.82 + (fine - 0.5) * 0.08;
      let moss = 0;
      if (grit > 0.965) {
        value -= 20;
        height -= 0.6;
      } else if (grit < 0.02) {
        value += 14;
      }
      // Worn arrises collect dirt.
      if (edge < 5) {
        const t = 1 - edge / 5;
        value -= 16 * t;
        height -= 1.1 * t;
        rough += 0.06 * t;
      }
      // Chipped corners on some flags.
      if (flag > 0.78 && localX + localY < 12 + hash(column, row, 409) * 10) {
        value -= 24;
        height -= 1.2;
      }
      // Sand joints with dirt and a trace of moss.
      if (edge < 1.6) {
        moss = smoothstep(0.55, 0.7, fbm(x / 8, y / 8, 411, 2, 64));
        value = 46 + moss * 6;
        height = -1.8;
        rough = 0.95;
      }
      const color = moss > 0
        ? [value * 0.82, value, value * 0.74]
        : [value, value * 0.985, value * 0.95];
      const offsetRgb = (y * BASE + x) * 3;
      albedo[offsetRgb] = byte(color[0]);
      albedo[offsetRgb + 1] = byte(color[1]);
      albedo[offsetRgb + 2] = byte(color[2]);
      roughness.fill(byte(clamp01(rough) * 255), offsetRgb, offsetRgb + 3);
      heights[y * BASE + x] = height;
    }
  }
  writePng(outputDirectory, 'pavement-albedo', BASE, BASE, 3, albedo);
  writePng(outputDirectory, 'pavement-roughness', BASE, BASE, 3, roughness);
  writePng(outputDirectory, 'pavement-normal', BASE, BASE, 3, heightToNormal(heights, BASE, BASE, 0.5, true));
}

// ---------------------------------------------------------------------------
// Cell painters. Strip cells: u along the edge, v = 0 on the edge itself.

function leafSample(lx, ly, leaf, alpha) {
  const inside = (lx / leaf.size) ** 2 + (ly / (leaf.size * 0.48)) ** 2;
  if (inside >= 1) return null;
  const vein = Math.abs(ly) < 0.6 ? 0.8 : 1;
  const colour = mix(mix([130, 84, 34], [150, 120, 48], leaf.tone), [70, 52, 34], leaf.tone > 0.7 ? 0.6 : 0);
  return sample(alpha, colour.map((channel) => channel * vein), 0.8, 0.7);
}

function discs(seed, count, minRadius, maxRadius, margin = 12) {
  const rng = mulberry32(seed);
  return Array.from({ length: count }, () => ({
    x: margin + rng() * (256 - margin * 2),
    y: margin + rng() * (256 - margin * 2),
    r: minRadius + rng() * (maxRadius - minRadius),
    tone: rng(),
  }));
}

const painters = {
  'tarmac-patch-a': () => (px, py, u, v) => {
    const ex = (fbm(v * 6, 0.5, 421, 3) - 0.5) * 0.03;
    const ey = (fbm(u * 6, 1.5, 422, 3) - 0.5) * 0.03;
    const d = Math.max(Math.abs(u - 0.5) - (0.47 + ex), Math.abs(v - 0.5) - (0.47 + ey));
    const agg = aggregate(px, py, 423, 36, 0.8);
    const inside = smoothstep(0.006, -0.006, d);
    const smear = smoothstep(0.03, 0, d) * (fbm(u * 14, v * 14, 424, 2) > 0.55 ? 0.35 : 0);
    return sample(Math.max(inside * 0.95, smear), grey(agg.value, 1), 0.7 + agg.rough, agg.height - 0.2 * inside);
  },

  'tarmac-patch-b': () => (px, py, u, v) => {
    const d = blobDistance(u, v, 431, 0.38, 0.3, 1, 0.85);
    if (d > 0) {
      const ravel = smoothstep(0.12, 0, d) * (hash(px, py, 433) > 0.6 ? 0.6 : 0.1);
      return sample(ravel, grey(54), 0.9, ravel * 0.4);
    }
    const agg = aggregate(px, py, 435, 38, 0.7);
    return sample(0.95, grey(agg.value), 0.72 + agg.rough, agg.height);
  },

  'cracked-flag-a': () => {
    const rng = mulberry32(441);
    const brokenEdge = [];
    for (let step = 0; step <= 12; step += 1) {
      const t = step / 12;
      brokenEdge.push([mix(118, 255, t) + (rng() - 0.5) * 6, mix(255, 118, t) + (rng() - 0.5) * 6]);
    }
    const mask = strokeMask(256, 256, [
      { points: crackPoints(rng, 0, 96, 0.3, 14, 20, 0.6), radius: 1.3, taper: 0.2 },
      { points: brokenEdge, radius: 1.5, taper: 0 },
    ]);
    return (px, py, u, v) => {
      const crack = mask[py * 256 + px];
      const piece = u + v > 1.46 + (fbm(u * 8, v * 8, 443, 2) - 0.5) * 0.03 ? 1 : 0;
      return sample(
        Math.max(crack * 0.9, piece * 0.3),
        crack > 0.2 ? [28, 28, 26] : [70, 68, 64],
        crack > 0.2 ? 0.95 : 0.88,
        -crack * 1.4 - piece * 0.8,
      );
    };
  },

  'cracked-flag-b': () => {
    const rng = mulberry32(451);
    const strokes = [];
    for (let index = 0; index < 6; index += 1) {
      strokes.push({
        points: crackPoints(rng, 120, 136, (index / 6) * Math.PI * 2 + rng() * 0.5, 9, 20, 0.5),
        radius: 1.4,
        taper: 0.3,
      });
    }
    const mask = strokeMask(256, 256, strokes);
    return (px, py, u, v) => {
      const crack = mask[py * 256 + px];
      const sector = Math.floor(((Math.atan2(v - 0.53, u - 0.47) + Math.PI) / (Math.PI * 2)) * 6);
      const shade = (sector % 2 === 0 ? 0.12 : 0.04) * smoothstep(0.62, 0.3, Math.hypot(u - 0.47, v - 0.53));
      return sample(
        Math.max(crack * 0.9, shade),
        crack > 0.2 ? [26, 26, 24] : [62, 60, 56],
        0.92,
        -crack * 1.5 - (sector % 2) * 0.5,
      );
    };
  },

  'sunken-flag-wet': () => (px, py, u, v) => {
    const edge = Math.min(u, 1 - u, v, 1 - v);
    const pool = smoothstep(0.02, 0.22, edge) * mix(0.75, 1, fbm(u * 5, v * 5, 461, 3));
    return sample(pool * 0.55, [34, 36, 40], mix(0.55, 0.1, pool), -pool * 0.3);
  },

  'damp-patch': () => (px, py, u, v) => {
    const d = blobDistance(u, v, 471, 0.34, 0.34, 1, 0.8);
    const wet = smoothstep(0.3, -0.4, d);
    return sample(
      wet * mix(0.25, 0.42, fbm(u * 6, v * 6, 473, 3)),
      [44, 46, 50],
      mix(0.62, 0.25, wet),
      0,
    );
  },

  'gum-scatter': () => {
    const blobs = discs(481, 70, 1.6, 5);
    return (px, py) => {
      for (const blob of blobs) {
        const d = Math.hypot(px - blob.x, py - blob.y) / blob.r;
        if (d < 1) return sample(0.95, grey(mix(118, 168, blob.tone)), 0.62, 0.5);
        if (d < 1.3) return sample(0.3, grey(60), 0.8, 0);
      }
      return sample(0, grey(140), 0.8);
    };
  },

  'gum-old': () => {
    const blobs = discs(491, 110, 1.2, 3);
    return (px, py) => {
      for (const blob of blobs) {
        if (Math.hypot(px - blob.x, py - blob.y) < blob.r) {
          return sample(0.92, grey(blob.tone > 0.85 ? 132 : mix(38, 70, blob.tone)), 0.7, 0.4);
        }
      }
      return sample(0, grey(60), 0.8);
    };
  },

  'stain-spill': () => {
    const rng = mulberry32(501);
    const drops = Array.from({ length: 26 }, () => ({
      x: 0.5 + (rng() - 0.5) * 0.7,
      y: 0.5 + (rng() - 0.5) * 0.7,
      r: 0.01 + rng() ** 3 * 0.05,
    }));
    return (px, py, u, v) => {
      const d = blobDistance(u, v, 503, 0.26, 0.36, 1, 0.8);
      let alpha = smoothstep(0.1, -0.2, d) * mix(0.3, 0.5, fbm(u * 8, v * 8, 505, 3));
      for (const drop of drops) {
        if (Math.hypot(u - drop.x, v - drop.y) < drop.r) alpha = Math.max(alpha, 0.5);
      }
      return sample(alpha * endFade(u, 0.05) * endFade(v, 0.05), [42, 37, 30], 0.5, 0);
    };
  },

  'bin-stain': () => (px, py, u, v) => {
    const r = Math.hypot(u - 0.5, (v - 0.45) * 1.1);
    const ring = Math.exp(-(((r - 0.24) / 0.035) ** 2));
    const fill = smoothstep(0.26, 0.1, r) * 0.35;
    const runCentre = 0.5 + (fbm(v * 4, 0.5, 511, 2) - 0.5) * 0.15;
    const run = smoothstep(0.08, 0, Math.abs(u - runCentre)) * smoothstep(0.45, 0.95, v) * (1 - smoothstep(0.8, 1, v));
    const alpha = clamp01(Math.max(ring * 0.55, fill, run * 0.45)) * mix(0.6, 1, fbm(u * 9, v * 9, 513, 3));
    return sample(alpha, [50, 42, 32], 0.58, 0);
  },

  'moss-lichen': () => {
    const lichens = discs(521, 22, 3, 10, 20);
    return (px, py, u, v) => {
      for (const lichen of lichens) {
        const d = Math.hypot(px - lichen.x, py - lichen.y) / lichen.r;
        if (d < 1) return sample(0.75, d > 0.7 ? [168, 172, 150] : [140, 146, 122], 0.9, 0.3);
      }
      const falloff = smoothstep(0.5, 0.2, Math.hypot(u - 0.5, v - 0.5));
      const moss = smoothstep(0.5, 0.62, fbm(u * 9, v * 9, 523, 4) * 0.6 + falloff * 0.5);
      return sample(moss * 0.85, mix([28, 40, 24], [46, 62, 32], fbm(u * 30, v * 30, 525, 2)), 0.96, moss * 0.7);
    };
  },

  'tactile-red': () => (px, py) => {
    const unit = 256 / 3;
    const localX = px % unit;
    const localY = py % unit;
    const edge = Math.min(localX, unit - localX, localY, unit - localY);
    if (edge < 1.5) return sample(0.97, [58, 48, 44], 0.95, -1.2);
    const pitch = unit / 6;
    const dome = clamp01(1 - Math.hypot((localX % pitch) - pitch / 2, (localY % pitch) - pitch / 2) / 5.2);
    const base = mix([132, 60, 50], [112, 64, 56], fbm(px / 12, py / 12, 531, 3));
    const top = mix(base, [168, 110, 94], fbm(px / 40, py / 40, 533, 2) * 0.8);
    const colour = dome > 0 ? mix(base, top, dome) : base.map((channel) => channel * 0.9);
    const grit = (hash(px, py, 535) - 0.5) * 10;
    return sample(0.97, colour.map((channel) => channel - grit), 0.8 - dome * 0.1, dome * 1.6);
  },

  'kerb-stone': () => (px, py, u, v) => {
    // About 915 mm units when a strip spans 6 m.
    const unitLength = 156;
    const localX = px % unitLength;
    const joint = Math.min(localX, unitLength - localX) < 1.5 || v > 0.95;
    const unitTone = hash(Math.floor(px / unitLength), 0, 541);
    const agg = aggregate(px, py, 543, 122 + unitTone * 16, 0.8);
    const arris = smoothstep(0.22, 0, v);
    const chip = v < 0.3 && fbm(u * 80, v * 4, 545, 2) > 0.7 ? 1 : 0;
    const value = joint ? 50 : agg.value - arris * 28 - chip * 30;
    return sample(
      0.97 * endFade(u, 0.004),
      grey(value, 2),
      joint ? 0.95 : 0.84 + agg.rough,
      joint ? -1.5 : agg.height - arris * 1.2 - chip,
    );
  },

  'wall-base': () => (px, py, u, v) => {
    const density = smoothstep(1, 0, v) ** 2.2 * mix(0.5, 1, fbm(u * 50, v * 3, 551, 3));
    const algae = smoothstep(0.55, 0.7, fbm(u * 20, v * 2, 553, 3)) * smoothstep(0.5, 0, v);
    const tuft = v < 0.28 && fbm(u * 140, v * 6, 555, 2) > 0.74 && hash(px, py, 557) > 0.35;
    if (tuft) {
      return sample(0.92 * endFade(u), mix([44, 70, 34], [76, 96, 44], hash(px >> 1, py >> 1, 559)), 0.9, 1.2);
    }
    return sample(
      clamp01(density * 0.85) * endFade(u),
      mix([30, 30, 28], [34, 44, 28], algae),
      mix(0.55, 0.9, v),
      density * 0.2,
    );
  },

  'verge-edge': () => (px, py, u, v) => {
    const edgeLine = 0.18 + (fbm(u * 24, 0.5, 561, 3) - 0.5) * 0.3;
    const soil = smoothstep(edgeLine + 0.08, edgeLine - 0.05, v);
    const blade = v < edgeLine + 0.1 && hash(px, py, 563) > 0.8 && fbm(u * 90, v * 5, 565, 2) > 0.45;
    if (blade) {
      return sample(0.9 * endFade(u), mix([40, 64, 32], [70, 90, 44], hash(px, py, 567)), 0.95, 1);
    }
    const crumbs = soil < 0.5 && v < edgeLine + 0.35 && hash(px >> 1, py >> 1, 569) > 0.9 ? 0.7 : 0;
    return sample(
      Math.max(soil * 0.9, crumbs) * endFade(u),
      mix([54, 44, 34], [70, 58, 42], fbm(u * 40, v * 6, 571, 2)),
      0.96,
      soil * 0.5 + crumbs * 0.6,
    );
  },

  'tyre-scuff': () => (px, py, u, v) => {
    const band = Math.exp(-(((v - 0.5) / 0.3) ** 2));
    const streak = fbm(u * 6, v * 20, 581, 3);
    return sample(band * mix(0.12, 0.42, streak) * endFade(u, 0.18), [26, 26, 28], 0.7, 0);
  },

  'leaf-litter': () => {
    const rng = mulberry32(591);
    const leaves = Array.from({ length: 150 }, () => ({
      x: rng() * 512,
      y: 6 + rng() * 84,
      angle: rng() * Math.PI,
      size: 4 + rng() * 7,
      tone: rng(),
    }));
    return (px, py, u, v) => {
      const fade = endFade(u, 0.06) * endFade(v, 0.1);
      let found = null;
      for (const leaf of leaves) {
        const dx = px - leaf.x;
        const dy = py - leaf.y;
        if (Math.abs(dx) > 12 || Math.abs(dy) > 12) continue;
        const cos = Math.cos(leaf.angle);
        const sin = Math.sin(leaf.angle);
        found = leafSample(dx * cos + dy * sin, -dx * sin + dy * cos, leaf, 0.92 * fade) ?? found;
      }
      if (found) return found;
      const mulch = smoothstep(0.55, 0.68, fbm(u * 18, v * 4, 593, 3));
      return sample(mulch * 0.5 * fade, [52, 42, 30], 0.85, mulch * 0.3);
    };
  },
};

writeDecalAtlas(outputDirectory, 'pavement-decal', atlas, painters);
