import { cp, mkdir, readFile, readdir } from 'node:fs/promises';
import { dirname, relative, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { DEFAULT_OPTIONS, optimizeGlbFile } from './lib/glbOptimizer.mjs';
import { recompressLooseImages } from './lib/imageRecompress.mjs';
import { createTextureEncoder } from './lib/textureEncoder.mjs';

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const defaultCacheDirectory = resolve(projectRoot, '.cache', 'asset-optimizer');
const transcoderSource = resolve(projectRoot, 'node_modules/three/examples/jsm/libs/basis');
const configPath = resolve(projectRoot, 'config/asset-optimization.json');

/** Files (relative to the assets root) whose positions may be quantised. */
async function readQuantizeList() {
  const config = JSON.parse(await readFile(configPath, 'utf8'));
  return new Set(Object.keys(config.quantizePositions ?? {}));
}

const megabytes = (bytes) => (bytes / 1048576).toFixed(1);

async function findGlbs(directory) {
  const found = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) found.push(...await findGlbs(path));
    else if (entry.name.endsWith('.glb')) found.push(path);
  }
  return found;
}

/** The KTX2 loader fetches its WASM transcoder from `<base>/basis/` at runtime. */
export async function installTranscoder(outputRoot) {
  const destination = resolve(outputRoot, 'basis');
  await mkdir(destination, { recursive: true });
  for (const file of ['basis_transcoder.js', 'basis_transcoder.wasm']) {
    await cp(resolve(transcoderSource, file), resolve(destination, file));
  }
}

/**
 * Replace every `.glb` under `outputRoot` with an optimised build of its
 * pristine source under `sourceRoot`. Sources are never modified, so the
 * authored files stay the single source of truth for the Blender pipeline.
 */
export async function optimizeRuntimeAssets({
  sourceRoot,
  outputRoot,
  cacheDirectory = defaultCacheDirectory,
  options = DEFAULT_OPTIONS,
  encoder = createTextureEncoder({ cacheDirectory }),
  log = console.log,
}) {
  const files = (await findGlbs(outputRoot)).sort();
  const quantizeList = await readQuantizeList();
  const totals = { before: 0, after: 0, gpuBefore: 0, gpuAfter: 0, cached: 0, files: 0 };
  if (!encoder.compressed) {
    log('  ! basisu not found: textures are resized and stored as WebP, not GPU-compressed KTX2.');
    log('    Install it (brew install basis_universal) or set BASISU_PATH for the full effect.');
  }
  for (const destination of files) {
    const relativePath = relative(outputRoot, destination);
    const report = await optimizeGlbFile(resolve(sourceRoot, relativePath), destination, {
      cacheDirectory, encoder, options, quantizePositions: quantizeList.has(relativePath.split('\\').join('/')),
    });
    totals.before += report.bytesBefore; totals.after += report.bytesAfter;
    totals.gpuBefore += report.gpuBefore; totals.gpuAfter += report.gpuAfter;
    totals.cached += report.cached ? 1 : 0; totals.files += 1;
    log(`  ${relativePath.padEnd(50)} ${megabytes(report.bytesBefore).padStart(6)} -> ${megabytes(report.bytesAfter).padStart(5)} MB`
      + `  tex ${String(report.texturesBefore).padStart(2)}->${String(report.texturesAfter).padEnd(2)}`
      + `  GPU ${String(Math.round(report.gpuBefore / 1048576)).padStart(4)}->${String(Math.round(report.gpuAfter / 1048576)).padEnd(3)} MB`
      + `  (-${report.droppedNormals} normal, -${report.constantOrms} orm, ${report.geometry}${report.cached ? ', cached' : ''})`);
  }
  if (encoder.compressed || files.length > 0) await installTranscoder(outputRoot);
  log(`Optimised ${totals.files} models: ${megabytes(totals.before)} -> ${megabytes(totals.after)} MB download, `
    + `estimated texture memory ${Math.round(totals.gpuBefore / 1048576)} -> ${Math.round(totals.gpuAfter / 1048576)} MB `
    + `(${totals.cached} from cache).`);
  totals.images = await recompressLooseImages({ sourceRoot, outputRoot, cacheDirectory, log });
  return totals;
}

async function main() {
  const [sourceRoot, outputRoot] = process.argv.slice(2);
  if (!sourceRoot || !outputRoot) {
    console.error('usage: node scripts/optimizeRuntimeAssets.mjs <sourceRoot> <outputRoot>');
    console.error('  Replaces the .glb files under <outputRoot> with optimised builds of the same');
    console.error('  paths under <sourceRoot>. Normally run for you by scripts/prepareRuntimeAssets.mjs.');
    process.exit(2);
  }
  await optimizeRuntimeAssets({ sourceRoot: resolve(sourceRoot), outputRoot: resolve(outputRoot) });
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await main();
}
