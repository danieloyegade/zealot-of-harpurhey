// Shared helpers for the procedural surface generators
// (generateRoadTextures.mjs, generatePavementTextures.mjs).
import { writeFileSync } from 'node:fs';
import { deflateSync } from 'node:zlib';

// ---------------------------------------------------------------------------
// PNG encoding (RGB or RGBA; the world generator's sips path drops alpha).

export const CRC_TABLE = new Uint32Array(256).map((_, index) => {
  let value = index;
  for (let bit = 0; bit < 8; bit += 1) {
    value = value & 1 ? 0xedb88320 ^ (value >>> 1) : value >>> 1;
  }
  return value >>> 0;
});

export function crc32(buffer) {
  let value = 0xffffffff;
  for (const byte of buffer) {
    value = CRC_TABLE[(value ^ byte) & 0xff] ^ (value >>> 8);
  }
  return (value ^ 0xffffffff) >>> 0;
}

export function pngChunk(type, data) {
  const length = Buffer.alloc(4);
  length.writeUInt32BE(data.length);
  const body = Buffer.concat([Buffer.from(type, 'ascii'), data]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(body));
  return Buffer.concat([length, body, crc]);
}

export function writePng(outputDirectory, name, width, height, channels, pixels) {
  const header = Buffer.alloc(13);
  header.writeUInt32BE(width, 0);
  header.writeUInt32BE(height, 4);
  header[8] = 8;
  header[9] = channels === 4 ? 6 : 2;
  const stride = width * channels;
  const raw = Buffer.alloc((stride + 1) * height);
  for (let y = 0; y < height; y += 1) {
    pixels.copy(raw, y * (stride + 1) + 1, y * stride, (y + 1) * stride);
  }
  writeFileSync(
    new URL(`${name}.png`, outputDirectory),
    Buffer.concat([
      Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
      pngChunk('IHDR', header),
      pngChunk('IDAT', deflateSync(raw, { level: 9 })),
      pngChunk('IEND', Buffer.alloc(0)),
    ]),
  );
  console.log(`${name}.png ${width}x${height}`);
}

// ---------------------------------------------------------------------------
// Noise and shaping.

export const byte = (value) => Math.max(0, Math.min(255, Math.round(value)));
export const clamp01 = (value) => Math.max(0, Math.min(1, value));
/** Linear interpolation of numbers or equal-length colour arrays. */
export const mix = (a, b, t) => (Array.isArray(a)
  ? a.map((channel, index) => channel + (b[index] - channel) * t)
  : a + (b - a) * t);
export const smoothstep = (edge0, edge1, value) => {
  const t = clamp01((value - edge0) / (edge1 - edge0));
  return t * t * (3 - 2 * t);
};

export function hash(x, y, seed) {
  let value = Math.imul((x | 0) + Math.imul(seed, 101), 374761393);
  value = Math.imul(value ^ Math.imul((y | 0) + Math.imul(seed, 37), 668265263), 1274126177);
  return ((value ^ (value >>> 13)) >>> 0) / 4294967296;
}

export function valueNoise(x, y, seed, period = 0) {
  const x0 = Math.floor(x);
  const y0 = Math.floor(y);
  const fx = x - x0;
  const fy = y - y0;
  const sx = fx * fx * (3 - 2 * fx);
  const sy = fy * fy * (3 - 2 * fy);
  const wrap = (value) => (period > 0 ? ((value % period) + period) % period : value);
  const a = hash(wrap(x0), wrap(y0), seed);
  const b = hash(wrap(x0 + 1), wrap(y0), seed);
  const c = hash(wrap(x0), wrap(y0 + 1), seed);
  const d = hash(wrap(x0 + 1), wrap(y0 + 1), seed);
  return mix(mix(a, b, sx), mix(c, d, sx), sy);
}

/** Fractal value noise in roughly [0, 1]. A period makes it tile. */
export function fbm(x, y, seed, octaves = 4, period = 0) {
  let sum = 0;
  let amplitude = 0.5;
  let total = 0;
  let frequency = 1;
  for (let octave = 0; octave < octaves; octave += 1) {
    sum += valueNoise(
      x * frequency,
      y * frequency,
      seed + octave * 17,
      period > 0 ? period * frequency : 0,
    ) * amplitude;
    total += amplitude;
    amplitude *= 0.5;
    frequency *= 2;
  }
  return sum / total;
}

export function mulberry32(seed) {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Encodes a height field as an OpenGL (green-up) tangent-space normal map.
 * Image rows grow downward while texture V grows upward, hence the sign on Y.
 */
export function heightToNormal(heights, width, height, strength, wrap) {
  const pixels = Buffer.alloc(width * height * 3);
  const at = (x, y) => {
    const sx = wrap ? (x + width) % width : Math.max(0, Math.min(width - 1, x));
    const sy = wrap ? (y + height) % height : Math.max(0, Math.min(height - 1, y));
    return heights[sy * width + sx];
  };
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const dx = (at(x + 1, y) - at(x - 1, y)) * strength;
      const dy = (at(x, y + 1) - at(x, y - 1)) * strength;
      const nx = -dx;
      const ny = dy;
      const length = Math.hypot(nx, ny, 1);
      const offset = (y * width + x) * 3;
      pixels[offset] = byte((nx / length * 0.5 + 0.5) * 255);
      pixels[offset + 1] = byte((ny / length * 0.5 + 0.5) * 255);
      pixels[offset + 2] = byte((1 / length * 0.5 + 0.5) * 255);
    }
  }
  return pixels;
}

/** Non-tiling bound aggregate used inside decals so repairs keep a texture. */
export function aggregate(px, py, seed, tone, contrast) {
  const fine = fbm(px / 7, py / 7, seed, 3);
  const grit = hash(px, py, seed + 3);
  const chip = hash(px >> 1, py >> 1, seed + 5);
  let value = tone + (fine - 0.5) * 14 * contrast + (grit - 0.5) * 9 * contrast;
  let height = (fine - 0.5) * 0.6 * contrast;
  let rough = 0;
  if (chip > 1 - 0.1 * contrast) {
    value += 18 * contrast;
    height += 0.8 * contrast;
    rough -= 0.12;
  } else if (grit < 0.05 * contrast) {
    value -= 12;
    height -= 0.8;
    rough += 0.06;
  }
  return { value, height, rough };
}

/** Rasterises tapered polylines into a coverage mask. */
export function strokeMask(width, height, strokes) {
  const mask = new Float32Array(width * height);
  for (const { points, radius, taper = 0.6 } of strokes) {
    let travelled = 0;
    let total = 0;
    for (let index = 1; index < points.length; index += 1) {
      total += Math.hypot(
        points[index][0] - points[index - 1][0],
        points[index][1] - points[index - 1][1],
      );
    }
    for (let index = 1; index < points.length; index += 1) {
      const [ax, ay] = points[index - 1];
      const [bx, by] = points[index];
      const length = Math.hypot(bx - ax, by - ay);
      const steps = Math.max(1, Math.ceil(length * 2));
      for (let step = 0; step <= steps; step += 1) {
        const t = step / steps;
        const cx = mix(ax, bx, t);
        const cy = mix(ay, by, t);
        const r = radius * (1 - taper * ((travelled + length * t) / Math.max(total, 1)));
        const minX = Math.max(0, Math.floor(cx - r - 1));
        const maxX = Math.min(width - 1, Math.ceil(cx + r + 1));
        const minY = Math.max(0, Math.floor(cy - r - 1));
        const maxY = Math.min(height - 1, Math.ceil(cy + r + 1));
        for (let y = minY; y <= maxY; y += 1) {
          for (let x = minX; x <= maxX; x += 1) {
            const coverage = clamp01(r + 0.5 - Math.hypot(x - cx, y - cy));
            const offset = y * width + x;
            if (coverage > mask[offset]) mask[offset] = coverage;
          }
        }
      }
      travelled += length;
    }
  }
  return mask;
}

export function crackPoints(rng, x, y, angle, steps, stepLength, wobble) {
  const points = [[x, y]];
  let heading = angle;
  for (let step = 0; step < steps; step += 1) {
    heading += (rng() - 0.5) * wobble;
    x += Math.cos(heading) * stepLength * (0.6 + rng() * 0.8);
    y += Math.sin(heading) * stepLength * (0.6 + rng() * 0.8);
    points.push([x, y]);
  }
  return points;
}

export const sample = (alpha, color, rough, height = 0) => ({ alpha, color, rough, height });
export const grey = (value, warmth = 0) => [value + warmth, value + warmth * 0.35, value - warmth * 0.4];

/** Fades a strip's ends so consecutive strips chain without a visible seam. */
export const endFade = (u, width = 0.04) => smoothstep(0, width, u) * smoothstep(0, width, 1 - u);

// ---------------------------------------------------------------------------
// Shapes and atlas assembly.

export function blobDistance(u, v, seed, radius, wobble, stretchU = 1, stretchV = 1) {
  const dx = (u - 0.5) / stretchU;
  const dy = (v - 0.5) / stretchV;
  const angle = Math.atan2(dy, dx);
  const r = radius
    + (fbm(Math.cos(angle) * 1.6 + 5, Math.sin(angle) * 1.6 + 5, seed, 4) - 0.5) * wobble;
  return Math.hypot(dx, dy) / r - 1;
}

/**
 * Paints every cell of a decal atlas into `${prefix}-{albedo,roughness,normal}.png`.
 * Painters return (px, py, u, v) => sample for their cell.
 */
export function writeDecalAtlas(outputDirectory, prefix, atlas, painters) {
  const SIZE = atlas.size;
  const albedo = Buffer.alloc(SIZE * SIZE * 4);
  const roughness = Buffer.alloc(SIZE * SIZE * 3);
  const normal = Buffer.alloc(SIZE * SIZE * 3);
  for (let index = 0; index < SIZE * SIZE; index += 1) {
    albedo.set([30, 30, 30, 0], index * 4);
    roughness.fill(217, index * 3, index * 3 + 3);
    normal.set([128, 128, 255], index * 3);
  }

  for (const [name, cell] of Object.entries(atlas.cells)) {
    const painter = painters[name];
    if (!painter) throw new Error(`No painter for decal cell "${name}".`);
    const paint = painter(cell);
    const { w, h } = cell;
    const samples = new Array(w * h);
    const heights = new Float32Array(w * h);
    let red = 0;
    let green = 0;
    let blue = 0;
    let weight = 0;
    for (let py = 0; py < h; py += 1) {
      for (let px = 0; px < w; px += 1) {
        const result = paint(px, py, (px + 0.5) / w, (py + 0.5) / h);
        const alpha = clamp01(result.alpha);
        samples[py * w + px] = result;
        heights[py * w + px] = result.height * alpha;
        red += result.color[0] * alpha;
        green += result.color[1] * alpha;
        blue += result.color[2] * alpha;
        weight += alpha;
      }
    }
    // Transparent texels take the cell's mean colour so mipmapping does not
    // pull a dark fringe into pale paint.
    const fill = weight > 0 ? [red / weight, green / weight, blue / weight] : [30, 30, 30];
    const cellNormal = heightToNormal(heights, w, h, 0.45, false);
    for (let py = 0; py < h; py += 1) {
      for (let px = 0; px < w; px += 1) {
        const result = samples[py * w + px];
        const alpha = clamp01(result.alpha);
        const color = alpha > 0.02 ? result.color : fill;
        const target = (cell.y + py) * SIZE + cell.x + px;
        albedo[target * 4] = byte(color[0]);
        albedo[target * 4 + 1] = byte(color[1]);
        albedo[target * 4 + 2] = byte(color[2]);
        albedo[target * 4 + 3] = byte(alpha * 255);
        roughness.fill(byte(clamp01(result.rough) * 255), target * 3, target * 3 + 3);
        cellNormal.copy(normal, target * 3, (py * w + px) * 3, (py * w + px + 1) * 3);
      }
    }
  }

  writePng(outputDirectory, `${prefix}-albedo`, SIZE, SIZE, 4, albedo);
  writePng(outputDirectory, `${prefix}-roughness`, SIZE, SIZE, 3, roughness);
  writePng(outputDirectory, `${prefix}-normal`, SIZE, SIZE, 3, normal);
}
