import { readdir, readFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const root = resolve(new URL('..', import.meta.url).pathname);
const runtime = JSON.parse(await readFile(resolve(root, 'config/runtime-assets.json'), 'utf8'));
const register = JSON.parse(await readFile(resolve(root, 'config/asset-rights.json'), 'utf8'));
const registered = new Map(register.assets.map((asset) => [asset.path, asset]));

async function audioFiles(directory, prefix = '') {
  const result = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (entry.name === '.DS_Store' || entry.name === '.gitkeep') continue;
    const relative = prefix ? `${prefix}/${entry.name}` : entry.name;
    if (entry.isDirectory()) result.push(...await audioFiles(resolve(directory, entry.name), relative));
    else result.push(`assets/audio/${relative}`);
  }
  return result;
}

const files = await audioFiles(resolve(root, 'public/assets/audio'));
const missing = files.filter((file) => !registered.has(file));
const productionAudio = runtime.production.filter((entry) => entry.startsWith('assets/audio'));
const uncleared = productionAudio.filter((file) => !registered.get(file)?.productionApproved);

if (missing.length || uncleared.length) {
  const messages = [];
  if (missing.length) messages.push(`Unregistered audio:\n${missing.join('\n')}`);
  if (uncleared.length) messages.push(`Production audio without clearance:\n${uncleared.join('\n')}`);
  throw new Error(messages.join('\n\n'));
}

console.log(`Rights register covers ${files.length} audio files; ${productionAudio.length} are cleared for production.`);
