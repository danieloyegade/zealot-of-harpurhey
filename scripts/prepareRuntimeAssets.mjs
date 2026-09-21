import { cp, mkdir, readFile, rm, stat } from 'node:fs/promises';
import { dirname, resolve, sep } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const sourceRoot = resolve(projectRoot, 'public');
const outputRoot = resolve(projectRoot, '.runtime-public');
const manifestPath = resolve(projectRoot, 'config/runtime-assets.json');

export function isSafeAssetPath(relativePath) {
  return typeof relativePath === 'string'
    && relativePath.length > 0
    && !relativePath.startsWith('/')
    && !relativePath.split(/[\\/]/).includes('..');
}

function within(root, candidate) {
  return candidate === root || candidate.startsWith(`${root}${sep}`);
}

async function readManifest() {
  return JSON.parse(await readFile(manifestPath, 'utf8'));
}

async function byteSize(path) {
  const details = await stat(path);
  if (details.isFile()) return details.size;
  const { readdir } = await import('node:fs/promises');
  const children = await readdir(path, { withFileTypes: true });
  let total = 0;
  for (const child of children) {
    if (child.name === '.DS_Store') continue;
    total += await byteSize(resolve(path, child.name));
  }
  return total;
}

export async function validateEntries(entries) {
  const failures = [];
  for (const entry of entries) {
    if (!isSafeAssetPath(entry)) {
      failures.push(`${entry}: unsafe path`);
      continue;
    }
    const source = resolve(sourceRoot, entry);
    if (!within(sourceRoot, source)) {
      failures.push(`${entry}: resolves outside public/`);
      continue;
    }
    try {
      await stat(source);
    } catch {
      failures.push(`${entry}: missing from public/`);
    }
  }
  return failures;
}

export async function prepareRuntimeAssets(mode = 'production') {
  const manifest = await readManifest();
  const entries = mode === 'development'
    ? [...manifest.production, ...manifest.developmentOnly]
    : manifest.production;
  const failures = await validateEntries(entries);
  if (failures.length > 0) {
    throw new Error(`Runtime asset manifest is invalid:\n${failures.join('\n')}`);
  }

  await rm(outputRoot, { recursive: true, force: true });
  await mkdir(outputRoot, { recursive: true });

  const copied = new Set();
  let total = 0;
  for (const entry of entries) {
    if (copied.has(entry)) continue;
    copied.add(entry);
    const source = resolve(sourceRoot, entry);
    const destination = resolve(outputRoot, entry);
    await mkdir(dirname(destination), { recursive: true });
    await cp(source, destination, {
      recursive: true,
      filter: (candidate) => !candidate.endsWith(`${sep}.DS_Store`),
    });
    total += await byteSize(source);
  }
  return { mode, entries: copied.size, bytes: total };
}

async function main() {
  const checkOnly = process.argv.includes('--check');
  const development = process.argv.includes('--development');
  const manifest = await readManifest();
  const entries = [...manifest.production, ...manifest.developmentOnly];
  const failures = await validateEntries(entries);
  if (failures.length > 0) throw new Error(failures.join('\n'));
  if (checkOnly) {
    console.log(`Validated ${entries.length} runtime asset entries.`);
    return;
  }
  const result = await prepareRuntimeAssets(development ? 'development' : 'production');
  console.log(`Prepared ${result.entries} ${result.mode} asset entries (${(result.bytes / 1024 / 1024).toFixed(1)} MB).`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await main();
}
