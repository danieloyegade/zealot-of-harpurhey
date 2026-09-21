import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import test from 'node:test';
import { isSafeAssetPath, validateEntries } from '../scripts/prepareRuntimeAssets.mjs';

const root = resolve(new URL('..', import.meta.url).pathname);

test('runtime asset entries are safe, present and unique', async () => {
  const manifest = JSON.parse(await readFile(resolve(root, 'config/runtime-assets.json'), 'utf8'));
  const entries = [...manifest.production, ...manifest.developmentOnly];

  assert.equal(entries.every(isSafeAssetPath), true);
  assert.deepEqual(await validateEntries(entries), []);
  assert.equal(new Set(manifest.production).size, manifest.production.length);
  assert.equal(new Set(manifest.developmentOnly).size, manifest.developmentOnly.length);
});

test('unapproved audio cannot cross the production boundary', async () => {
  const manifest = JSON.parse(await readFile(resolve(root, 'config/runtime-assets.json'), 'utf8'));
  const rights = JSON.parse(await readFile(resolve(root, 'config/asset-rights.json'), 'utf8'));
  const approved = new Set(
    rights.assets.filter((asset) => asset.productionApproved).map((asset) => asset.path),
  );
  const productionAudio = manifest.production.filter((path) => path.startsWith('assets/audio'));

  assert.deepEqual(productionAudio.filter((path) => !approved.has(path)), []);
});

test('the first delivery references real world locations', async () => {
  const world = await readFile(resolve(root, 'src/world/worldLayout.ts'), 'utf8');
  const delivery = await readFile(resolve(root, 'src/delivery/firstDelivery.ts'), 'utf8');
  const ids = new Set([...world.matchAll(/\bid:\s*'([^']+)'/g)].map((match) => match[1]));
  const pickup = delivery.match(/pickupId:\s*'([^']+)'/)?.[1];
  const destination = delivery.match(/destinationId:\s*'([^']+)'/)?.[1];

  assert.ok(pickup && ids.has(pickup), `Unknown pickup location: ${pickup}`);
  assert.ok(destination && ids.has(destination), `Unknown destination: ${destination}`);
});
