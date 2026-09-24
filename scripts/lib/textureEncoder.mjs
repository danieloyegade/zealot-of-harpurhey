import { execFile } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync } from 'node:fs';
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { cpus, tmpdir } from 'node:os';
import { join } from 'node:path';
import { promisify } from 'node:util';
import sharp from 'sharp';

const run = promisify(execFile);

/** Bump when a change here alters encoder output, to invalidate cached files. */
export const ENCODER_REVISION = 1;

/**
 * basisu presets per texture role. Colour maps take ETC1S (about 4 bits per
 * pixel on the GPU, a tenth of the download of the source PNG); normal maps
 * take UASTC, because ETC1S smears the low-amplitude gradients that lighting
 * reads as relief; colour with real alpha takes UASTC for clean cutout edges.
 */
export const BASISU_PRESETS = {
  color: ['-mipmap', '-quality', '85', '-effort', '4'],
  linear: ['-linear', '-mipmap', '-quality', '75', '-effort', '4'],
  normal: [
    '-uastc', '-uastc_level', '1', '-uastc_rdo_l', '1.5',
    '-normal_map', '-linear', '-mipmap', '-mip_renorm',
  ],
  colorAlpha: ['-uastc', '-uastc_level', '1', '-uastc_rdo_l', '1', '-mipmap'],
  linearAlpha: ['-uastc', '-uastc_level', '1', '-uastc_rdo_l', '1', '-linear', '-mipmap'],
};

export function findBasisu(env = process.env) {
  if (env.BASISU_PATH) {
    return existsSync(env.BASISU_PATH) ? env.BASISU_PATH : null;
  }
  for (const directory of (env.PATH ?? '').split(':')) {
    const candidate = join(directory, 'basisu');
    if (directory && existsSync(candidate)) return candidate;
  }
  return null;
}

/** Unit-length normals: filtering shortens them, which flattens lighting. */
export function renormalizeNormals(pixels, channels) {
  for (let index = 0; index < pixels.length; index += channels) {
    const x = pixels[index] / 127.5 - 1;
    const y = pixels[index + 1] / 127.5 - 1;
    const z = pixels[index + 2] / 127.5 - 1;
    const length = Math.hypot(x, y, z) || 1;
    pixels[index] = Math.round(((x / length) * 0.5 + 0.5) * 255);
    pixels[index + 1] = Math.round(((y / length) * 0.5 + 0.5) * 255);
    pixels[index + 2] = Math.round(((z / length) * 0.5 + 0.5) * 255);
  }
  return pixels;
}

/** Resize to the target and return an 8-bit PNG basisu (or WebP) can consume. */
export async function prepareSource({ image, width, height, role, alpha }) {
  let pipeline = sharp(image, { limitInputPixels: false })
    .resize(width, height, { fit: 'fill', kernel: 'lanczos3' });
  pipeline = alpha ? pipeline.ensureAlpha() : pipeline.removeAlpha();
  const { data, info } = await pipeline.raw().toBuffer({ resolveWithObject: true });
  if (role === 'normal') renormalizeNormals(data, info.channels);
  return sharp(data, { raw: { width: info.width, height: info.height, channels: info.channels } });
}

function presetFor(role, alpha) {
  if (role === 'normal') return 'normal';
  if (role === 'linear') return alpha ? 'linearAlpha' : 'linear';
  return alpha ? 'colorAlpha' : 'color';
}

export function createTextureEncoder({
  cacheDirectory,
  basisu = findBasisu(),
  concurrency = Math.max(1, Math.min(4, Math.floor(cpus().length / 2))),
  threadsPerJob = 2,
} = {}) {
  let basisuVersion = 'none';
  const versionReady = basisu
    ? run(basisu, ['-version']).then(({ stdout }) => {
      basisuVersion = stdout.split('\n')[0].trim();
    }).catch(() => { basisuVersion = 'unknown'; })
    : Promise.resolve();

  let active = 0;
  const waiting = [];
  const acquire = () => new Promise((resolve) => {
    if (active < concurrency) { active += 1; resolve(); } else waiting.push(resolve);
  });
  const release = () => {
    const next = waiting.shift();
    if (next) next(); else active -= 1;
  };

  const stats = { encoded: 0, cached: 0 };

  async function encode({ image, width, height, role, alpha }) {
    await versionReady;
    const preset = presetFor(role, alpha);
    const format = basisu ? 'ktx2' : 'webp';
    const key = createHash('sha1')
      .update(image)
      .update(JSON.stringify({ width, height, preset, format, basisuVersion, ENCODER_REVISION }))
      .digest('hex');
    const cachePath = cacheDirectory ? join(cacheDirectory, `${key}.${format}`) : null;
    if (cachePath && existsSync(cachePath)) {
      stats.cached += 1;
      return { data: new Uint8Array(await readFile(cachePath)), format, cached: true };
    }

    await acquire();
    try {
      const source = await prepareSource({ image, width, height, role, alpha });
      let data;
      if (basisu) {
        const directory = await mkdtemp(join(tmpdir(), 'zealot-basisu-'));
        try {
          const input = join(directory, 'input.png');
          const output = join(directory, 'output.ktx2');
          await source.png({ compressionLevel: 1 }).toFile(input);
          await run(basisu, [
            '-ktx2', ...BASISU_PRESETS[preset], '-max_threads', String(threadsPerJob),
            '-no_status_output', '-output_file', output, input,
          ], { maxBuffer: 64 * 1024 * 1024 });
          data = new Uint8Array(await readFile(output));
        } finally {
          await rm(directory, { recursive: true, force: true });
        }
      } else {
        // No basisu on this machine: a resized WebP still cuts decoded size a
        // lot, but it is not GPU-compressed. The caller reports the fallback.
        data = new Uint8Array(await (role === 'normal'
          ? source.webp({ lossless: true, effort: 4 })
          : source.webp({ quality: 88, alphaQuality: 90, effort: 4 })).toBuffer());
      }
      if (cachePath) {
        await mkdir(cacheDirectory, { recursive: true });
        await writeFile(cachePath, data);
      }
      stats.encoded += 1;
      return { data, format, cached: false };
    } finally {
      release();
    }
  }

  return { encode, stats, get compressed() { return Boolean(basisu); } };
}
