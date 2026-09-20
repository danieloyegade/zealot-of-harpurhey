// Generates spray-painted specter graffiti under public/assets/textures/graffiti/:
//
//   specter-haze-pair.png    two soft white figures, dark dot eyes, pink/blue scale bar
//   specter-drip-trio.png    three black figures with white dot eyes and paint runs
//   specter-outline.png      white outlined figure over a pink/teal scale bar
//
// The specters are Daniel Oyegade's recurring painting motif: long upright
// figures with two small eyes, often measured against a hand-drawn scale bar
// carrying a pink and a blue mark. These are procedural spray renditions of
// that motif, not scans. Every texture is straight-alpha RGBA, figure feet at
// the bottom edge, so a decal quad can sit on the pavement line of a wall.
import { mkdirSync } from 'node:fs';
import {
  byte,
  clamp01,
  fbm,
  hash,
  mulberry32,
  smoothstep,
  writePng,
} from './lib/textureTools.mjs';

const outputDirectory = new URL('../public/assets/textures/graffiti/', import.meta.url);
mkdirSync(outputDirectory, { recursive: true });

const WHITE = [236, 234, 228];
const BLACK = [18, 18, 20];
const PINK = [214, 58, 132];
const BLUE = [44, 78, 168];
const ROSE = [170, 72, 92];
const TEAL = [58, 112, 116];

/**
 * A layer is a function (u, v) -> coverage in [0, 1] with u, v in texture
 * space (0..1, v growing downward). Layers are composited in order, each with
 * its own colour, so later paint covers earlier paint the way sprayed coats do.
 */
function renderTexture(name, width, height, seed, layers) {
  const pixels = Buffer.alloc(width * height * 4);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const u = (x + 0.5) / width;
      const v = (y + 0.5) / height;
      let r = 0;
      let g = 0;
      let b = 0;
      let a = 0;
      for (const [index, layer] of layers.entries()) {
        const coverage = clamp01(layer.coverage(u, v, x, y, seed + index * 131));
        if (coverage <= 0) {
          continue;
        }
        // Over-composite in premultiplied space.
        r = layer.color[0] * coverage + r * (1 - coverage);
        g = layer.color[1] * coverage + g * (1 - coverage);
        b = layer.color[2] * coverage + b * (1 - coverage);
        a = coverage + a * (1 - coverage);
      }
      const offset = (y * width + x) * 4;
      pixels[offset] = a > 0 ? byte(r / a) : 0;
      pixels[offset + 1] = a > 0 ? byte(g / a) : 0;
      pixels[offset + 2] = a > 0 ? byte(b / a) : 0;
      pixels[offset + 3] = byte(a * 255);
    }
  }
  writePng(outputDirectory, name, width, height, 4, pixels);
}

/**
 * Turns a signed distance (negative inside, in texture-width units) into can
 * coverage: a dense core, a soft halo, and grainy overspray dots that thin out
 * with distance. `halo` is the width of the soft falloff.
 */
function spray(distance, x, y, seed, { halo, density = 0.94, grain = 0.5 }) {
  const core = 1 - smoothstep(-halo * 0.35, halo, distance);
  const speckleReach = 1 - smoothstep(0, halo * 3.2, distance);
  const dot = hash(x, y, seed) < speckleReach * speckleReach * 0.22 ? 0.55 + 0.4 * hash(y, x, seed + 7) : 0;
  const mottling = 1 - grain * 0.35 * fbm(x / 23, y / 23, seed + 3, 3);
  return Math.max(core * density * mottling, dot);
}

/**
 * Distance to a leaning, slightly wobbling capsule body. `top`/`bottom` are v
 * extents, `center` the u of the spine at the bottom, `lean` the u offset at
 * the top, `radius` the half width (in u), `swell` widens the lower body.
 */
function specterBody({ center, top, bottom, lean, radius, swell = 0, wobbleSeed }, aspect) {
  return (u, v) => {
    const t = clamp01((v - top) / (bottom - top));
    const spine = center + lean * (1 - t) * (1 - t)
      + (fbm(t * 3.1, 0.5, wobbleSeed, 2) - 0.5) * radius * 0.9;
    const halfWidth = radius * (1 + swell * Math.sin(t * Math.PI * 0.85))
      * (0.9 + 0.2 * fbm(t * 5, 1.5, wobbleSeed + 9, 2));
    // Squash the capsule ends so they round off like a single sweep of the can.
    const endRadius = halfWidth * aspect;
    const dv = v < top + endRadius
      ? (top + endRadius - v) / aspect
      : v > bottom - endRadius
        ? (v - (bottom - endRadius)) / aspect
        : 0;
    const du = Math.abs(u - spine);
    return dv > 0 ? Math.hypot(du, dv) - halfWidth : du - halfWidth;
  };
}

function eyes(body, { top, eyeSize, gap, drop }, aspect) {
  return (u, v) => {
    const eyeV = top + drop;
    const spineAtEyes = body.spineAt ? body.spineAt(eyeV) : 0;
    let nearest = Infinity;
    for (const side of [-1, 1]) {
      const du = u - (spineAtEyes + side * gap);
      const dv = (v - eyeV) / aspect;
      nearest = Math.min(nearest, Math.hypot(du, dv * 0.8) - eyeSize);
    }
    return nearest;
  };
}

/** Runs of paint below a figure: thin vertical drips that bead at the end. */
function drips(rng, count, uMin, uMax, vStart, maxLength, thickness, aspect) {
  const runs = Array.from({ length: count }, () => ({
    u: uMin + rng() * (uMax - uMin),
    v0: vStart - rng() * 0.05,
    length: maxLength * (0.35 + 0.65 * rng()),
    width: thickness * (0.6 + 0.6 * rng()),
  }));
  return (u, v) => {
    let nearest = Infinity;
    for (const run of runs) {
      const t = (v - run.v0) / run.length;
      if (t < -0.02 || t > 1.02) {
        continue;
      }
      const taper = run.width * (1 - 0.55 * clamp01(t));
      const bead = run.width * 1.25;
      const dv = (v - (run.v0 + run.length)) / aspect;
      const beadDistance = Math.hypot(u - run.u, dv * 1.4) - bead;
      const stem = Math.abs(u - run.u) - taper * smoothstep(0, 0.12, t) * (1 - smoothstep(0.9, 1, t));
      nearest = Math.min(nearest, stem, beadDistance);
    }
    return nearest;
  };
}

/** A hand-drawn scale bar: line, end ticks, and two coloured marks near the left end. */
function scaleBar({ u0, u1, v, tick, stroke, marks }, aspect) {
  const lineDistance = (u, pv) => {
    const wave = Math.sin(u * 40) * stroke * 0.25;
    const along = Math.max(u0 - u, u - u1, 0);
    return Math.hypot(along, (pv - v - wave) / aspect) - stroke;
  };
  const tickDistance = (u, pv, at) => Math.hypot(
    u - at,
    Math.max(Math.abs(pv - v) - tick, 0) / aspect,
  ) - stroke * 1.4;
  const line = (u, pv) => Math.min(lineDistance(u, pv), tickDistance(u, pv, u0), tickDistance(u, pv, u1));
  const markLayers = marks.map(({ at, color }) => ({
    color,
    distance: (u, pv) => Math.hypot(
      u - at - (pv - v) * 0.12,
      Math.max(Math.abs(pv - v) - tick * 0.72, 0) / aspect,
    ) - stroke * 2.2,
  }));
  return { line, markLayers };
}

function specterLayers(seed, figures, aspect, color, eyeColor, halo) {
  const layers = [];
  for (const [index, figure] of figures.entries()) {
    const body = specterBody({ ...figure, wobbleSeed: seed + index * 17 }, aspect);
    const t0 = figure.top + figure.radius * 1.2 * aspect;
    // Spine lookup for eye placement, matching specterBody's centre line.
    const spineAt = (v) => {
      const t = clamp01((v - figure.top) / (figure.bottom - figure.top));
      return figure.center + figure.lean * (1 - t) * (1 - t)
        + (fbm(t * 3.1, 0.5, seed + index * 17, 2) - 0.5) * figure.radius * 0.9;
    };
    layers.push({
      color,
      coverage: (u, v, x, y, layerSeed) => spray(body(u, v), x, y, layerSeed, { halo: halo * figure.radius }),
    });
    const eyeDistance = eyes({ spineAt }, {
      top: figure.top,
      radius: figure.radius,
      eyeSize: figure.radius * 0.13,
      gap: figure.radius * 0.3,
      drop: t0 - figure.top + figure.radius * 0.35 * aspect,
    }, aspect);
    layers.push({
      color: eyeColor,
      coverage: (u, v, x, y, layerSeed) => spray(eyeDistance(u, v), x, y, layerSeed, {
        halo: figure.radius * 0.05,
        density: 1,
        grain: 0.1,
      }),
    });
  }
  return layers;
}

// --- specter-haze-pair: after the "fig 1 / fig 2" drawing --------------------
{
  const width = 1024;
  const height = 1536;
  const aspect = width / height;
  const seed = 4101;
  const figures = [
    { center: 0.25, top: 0.1, bottom: 0.78, lean: 0.0, radius: 0.085, swell: 0.08 },
    { center: 0.58, top: 0.14, bottom: 0.76, lean: -0.1, radius: 0.08, swell: 0.12 },
  ];
  const bar = scaleBar({
    u0: 0.14,
    u1: 0.86,
    v: 0.9,
    tick: 0.028,
    stroke: 0.0045,
    marks: [{ at: 0.23, color: PINK }, { at: 0.29, color: BLUE }],
  }, aspect);
  renderTexture('specter-haze-pair', width, height, seed, [
    ...specterLayers(seed, figures, aspect, WHITE, BLACK, 0.55),
    { color: WHITE, coverage: (u, v, x, y, s) => spray(bar.line(u, v), x, y, s, { halo: 0.004, grain: 0.3 }) },
    ...bar.markLayers.map((mark) => ({
      color: mark.color,
      coverage: (u, v, x, y, s) => spray(mark.distance(u, v), x, y, s, { halo: 0.004, grain: 0.3 }),
    })),
  ]);
}

// --- specter-drip-trio: after "Home Improvement" / Aberration 14 ------------
{
  const width = 1024;
  const height = 1536;
  const aspect = width / height;
  const seed = 5209;
  const rng = mulberry32(seed);
  const figures = [
    { center: 0.22, top: 0.12, bottom: 0.84, lean: 0.02, radius: 0.075, swell: 0.1 },
    { center: 0.45, top: 0.04, bottom: 0.86, lean: -0.03, radius: 0.07, swell: 0.05 },
    { center: 0.7, top: 0.14, bottom: 0.83, lean: -0.08, radius: 0.072, swell: 0.12 },
  ];
  const run = drips(rng, 11, 0.17, 0.76, 0.8, 0.13, 0.0042, aspect);
  renderTexture('specter-drip-trio', width, height, seed, [
    { color: BLACK, coverage: (u, v, x, y, s) => spray(run(u, v), x, y, s, { halo: 0.003, grain: 0.2 }) },
    ...specterLayers(seed, figures, aspect, BLACK, WHITE, 0.28),
  ]);
}

// --- specter-outline: after the single outlined figure ------------------------
{
  const width = 1024;
  const height = 1536;
  const aspect = width / height;
  const seed = 6311;
  const figure = { center: 0.4, top: 0.08, bottom: 0.72, lean: -0.03, radius: 0.13, swell: 0.18 };
  const body = specterBody({ ...figure, wobbleSeed: seed }, aspect);
  const stroke = 0.012;
  const spineAt = (v) => {
    const t = clamp01((v - figure.top) / (figure.bottom - figure.top));
    return figure.center + figure.lean * (1 - t) * (1 - t)
      + (fbm(t * 3.1, 0.5, seed, 2) - 0.5) * figure.radius * 0.9;
  };
  const eyeDistance = eyes({ spineAt }, {
    top: figure.top,
    radius: figure.radius,
    eyeSize: figure.radius * 0.1,
    gap: figure.radius * 0.28,
    drop: figure.radius * 1.6 * aspect,
  }, aspect);
  const bar = scaleBar({
    u0: 0.3,
    u1: 0.92,
    v: 0.86,
    tick: 0.034,
    stroke: 0.006,
    marks: [{ at: 0.38, color: ROSE }, { at: 0.46, color: TEAL }],
  }, aspect);
  renderTexture('specter-outline', width, height, seed, [
    { color: WHITE, coverage: (u, v, x, y, s) => spray(Math.abs(body(u, v)) - stroke, x, y, s, { halo: 0.004, grain: 0.3 }) },
    { color: WHITE, coverage: (u, v, x, y, s) => spray(eyeDistance(u, v), x, y, s, { halo: 0.003, density: 1, grain: 0.1 }) },
    { color: WHITE, coverage: (u, v, x, y, s) => spray(bar.line(u, v), x, y, s, { halo: 0.004, grain: 0.3 }) },
    ...bar.markLayers.map((mark) => ({
      color: mark.color,
      coverage: (u, v, x, y, s) => spray(mark.distance(u, v), x, y, s, { halo: 0.004, grain: 0.3 }),
    })),
  ]);
}
