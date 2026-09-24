import { createHash } from 'node:crypto';
import { existsSync } from 'node:fs';
import { mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
import { extname, join, relative, resolve } from 'node:path';
import sharp from 'sharp';

/** Bump when a change here alters output, to invalidate cached files. */
export const RECOMPRESS_REVISION = 1;

// Full chroma: these are mostly normal and roughness maps, where 4:2:0
// subsampling smears the very channels the shader reads as data.
const JPEG_OPTIONS = { quality: 88, mozjpeg: true, chromaSubsampling: '4:4:4' };
const PNG_OPTIONS = { compressionLevel: 9, effort: 10, adaptiveFiltering: true };

/**
 * Re-encode an image in its own format, never returning something larger.
 * PNG is lossless (identical pixels) and skipped when it carries alpha; JPEG is
 * re-encoded once at high quality.
 * Paths and extensions stay put, so no loader needs to change.
 */
export async function recompressImage(buffer, extension) {
  const type = extension.toLowerCase();
  let encoded;
  if (type === '.png') {
    // Re-encoding zeroes the colour under fully transparent pixels, which
    // bleeds into the edges when the texture is filtered (dark halos around
    // decals and graffiti). PNGs with real transparency are left exactly as authored.
    const image = sharp(buffer, { limitInputPixels: false });
    let pipeline = image;
    if ((await image.metadata()).hasAlpha) {
      // An alpha channel that is 255 everywhere is dead weight; drop it exactly.
      if (!(await sharp(buffer, { limitInputPixels: false }).stats()).isOpaque) return buffer;
      pipeline = sharp(buffer, { limitInputPixels: false }).removeAlpha();
    }
    encoded = await pipeline.png(PNG_OPTIONS).toBuffer();
  }
  else if (type === '.jpg' || type === '.jpeg') encoded = await sharp(buffer, { limitInputPixels: false }).jpeg(JPEG_OPTIONS).toBuffer();
  else return buffer;
  return encoded.length < buffer.length ? encoded : buffer;
}

async function findImages(directory) {
  const found = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) found.push(...await findImages(path));
    else if (/\.(png|jpe?g)$/i.test(entry.name)) found.push(path);
  }
  return found;
}

/** Recompress every PNG/JPEG under `directories` (relative to outputRoot) from its source. */
export async function recompressLooseImages({
  sourceRoot, outputRoot, directories = ['assets/textures'], cacheDirectory, log = () => {},
}) {
  const totals = { files: 0, before: 0, after: 0 };
  for (const directory of directories) {
    const root = resolve(outputRoot, directory);
    if (!existsSync(root)) continue;
    for (const destination of (await findImages(root)).sort()) {
      const source = resolve(sourceRoot, relative(outputRoot, destination));
      const original = await readFile(source);
      const key = createHash('sha1').update(original).update(String(RECOMPRESS_REVISION)).digest('hex');
      const cachePath = cacheDirectory ? join(cacheDirectory, 'loose', `${key}${extname(source)}`) : null;
      let result;
      if (cachePath && existsSync(cachePath)) {
        result = await readFile(cachePath);
      } else {
        result = await recompressImage(original, extname(source));
        if (cachePath) {
          await mkdir(join(cacheDirectory, 'loose'), { recursive: true });
          await writeFile(cachePath, result);
        }
      }
      await writeFile(destination, result);
      totals.files += 1; totals.before += original.length; totals.after += result.length;
    }
  }
  log(`Recompressed ${totals.files} loose images: ${(totals.before / 1048576).toFixed(1)} -> ${(totals.after / 1048576).toFixed(1)} MB.`);
  return totals;
}
