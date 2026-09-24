import assert from 'node:assert/strict';
import test from 'node:test';
import { Document } from '@gltf-transform/core';
import sharp from 'sharp';
import {
  DEFAULT_OPTIONS,
  canCompressGeometry,
  canQuantizeGeometry,
  chooseTextureSize,
  classifyTextures,
  createIo,
  maxBoundsDifference,
  measureNormalSlope,
  meshWorldBounds,
  measureOrm,
  measureUvDensity,
  optimizeGlbBytes,
  roundPowerOfTwo,
} from '../scripts/lib/glbOptimizer.mjs';
import { recompressImage } from '../scripts/lib/imageRecompress.mjs';
import { createTextureEncoder, renormalizeNormals } from '../scripts/lib/textureEncoder.mjs';

// No basisu: the encoder falls back to resized WebP, which keeps these tests
// fast and independent of the machine. Sizing and removal logic is the same.
const encoder = () => createTextureEncoder({ basisu: null });

const noise = async (size) => {
  const pixels = Buffer.alloc(size * size * 3);
  for (let index = 0; index < pixels.length; index += 1) pixels[index] = (index * 2654435761) >>> 24;
  return sharp(pixels, { raw: { width: size, height: size, channels: 3 } }).png().toBuffer();
};

const solid = async (size, [r, g, b]) => sharp({
  create: { width: size, height: size, channels: 3, background: { r, g, b } },
}).png().toBuffer();

/** A ramped tangent-space normal map with real relief. */
const reliefNormal = async (size) => {
  const pixels = Buffer.alloc(size * size * 3);
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const slope = (((x >> 3) & 1) ? 0.6 : -0.6);
      const length = Math.hypot(slope, 1);
      const index = (y * size + x) * 3;
      pixels[index] = Math.round(((slope / length) * 0.5 + 0.5) * 255);
      pixels[index + 1] = 128;
      pixels[index + 2] = Math.round(((1 / length) * 0.5 + 0.5) * 255);
    }
  }
  return sharp(pixels, { raw: { width: size, height: size, channels: 3 } }).png().toBuffer();
};

/** One quad of `side` metres, UV 0..1, carrying the given maps. */
async function buildDocument({ side, base, normal, orm }) {
  const document = new Document();
  const buffer = document.createBuffer();
  const texture = (name, image) => document.createTexture(name).setImage(new Uint8Array(image)).setMimeType('image/png');
  const material = document.createMaterial('MAT_TEST')
    .setBaseColorTexture(texture('base', base))
    .setNormalTexture(texture('normal', normal))
    .setMetallicRoughnessTexture(texture('orm', orm))
    .setOcclusionTexture(document.getRoot().listTextures().find((t) => t.getName() === 'orm'))
    .setRoughnessFactor(1)
    .setMetallicFactor(1);
  const accessor = (type, array) => document.createAccessor().setType(type).setArray(array).setBuffer(buffer);
  const primitive = document.createPrimitive()
    .setMaterial(material)
    .setAttribute('POSITION', accessor('VEC3', new Float32Array([0, 0, 0, side, 0, 0, side, side, 0, 0, side, 0])))
    .setAttribute('TEXCOORD_0', accessor('VEC2', new Float32Array([0, 0, 1, 0, 1, 1, 0, 1])))
    .setIndices(accessor('SCALAR', new Uint16Array([0, 1, 2, 0, 2, 3])));
  const mesh = document.createMesh('quad').addPrimitive(primitive);
  const node = document.createNode('QUAD_ANCHOR_TARGET').setMesh(mesh);
  const anchor = document.createNode('ENTRANCE_ANCHOR').setTranslation([1, 2, 3]);
  document.createScene('scene').addChild(node).addChild(anchor);
  return document;
}

test('powers of two round up only past the bias', () => {
  assert.equal(roundPowerOfTwo(512, 1.35), 512);
  assert.equal(roundPowerOfTwo(690, 1.35), 512);
  assert.equal(roundPowerOfTwo(700, 1.35), 1024);
});

test('sizing targets a texel density and never upscales', () => {
  // 2048 px at 1000 texels/m: 819 px would match 400 texels/m, rounds up to 1024.
  assert.deepEqual(
    chooseTextureSize({ width: 2048, height: 2048, texelsPerMetre: 1000, role: 'color' }),
    { width: 1024, height: 1024, changed: true },
  );
  // Already below the target density: leave it alone.
  assert.equal(
    chooseTextureSize({ width: 1024, height: 1024, texelsPerMetre: 250, role: 'color' }).changed,
    false,
  );
  // Absurdly dense maps stop at the floor, not 1 px.
  assert.equal(
    chooseTextureSize({ width: 1024, height: 1024, texelsPerMetre: 900000, role: 'color' }).width,
    DEFAULT_OPTIONS.minTextureSize,
  );
});

test('roughness/AO maps drop one size step and aspect ratio survives', () => {
  const colour = chooseTextureSize({ width: 1024, height: 2048, texelsPerMetre: 800, role: 'color' });
  const linear = chooseTextureSize({ width: 1024, height: 2048, texelsPerMetre: 800, role: 'linear' });
  assert.equal(colour.height / colour.width, 2);
  assert.equal(linear.height / linear.width, 2);
  assert.ok(linear.width < colour.width);
});

test('unmeasured textures are capped rather than left at 4096', () => {
  const size = chooseTextureSize({ width: 4096, height: 4096, texelsPerMetre: null, role: 'color' });
  assert.equal(size.width, DEFAULT_OPTIONS.unmeasuredMaxSize);
});

test('a flat normal map has no measurable slope; a ramped one does', async () => {
  assert.ok(await measureNormalSlope(await solid(64, [128, 128, 255])) < DEFAULT_OPTIONS.flatNormalSlope);
  assert.ok(await measureNormalSlope(await reliefNormal(64)) > 0.3);
});

test('constant ORM is detected, varying ORM is not', async () => {
  const constant = await measureOrm(await solid(64, [255, 230, 0]));
  assert.ok(constant.deviation.every((value) => value < DEFAULT_OPTIONS.constantOrmDeviation));
  assert.ok(Math.abs(constant.mean[1] - 230 / 255) < 0.01);
  const varying = await measureOrm(await noise(64));
  assert.ok(varying.deviation.some((value) => value > 0.1));
});

test('resizing re-normalises normal maps to unit length', () => {
  const pixels = Buffer.from([160, 128, 140, 100, 128, 150]);
  renormalizeNormals(pixels, 3);
  for (let index = 0; index < pixels.length; index += 3) {
    const length = Math.hypot(
      pixels[index] / 127.5 - 1, pixels[index + 1] / 127.5 - 1, pixels[index + 2] / 127.5 - 1,
    );
    assert.ok(Math.abs(length - 1) < 0.02, `length ${length}`);
  }
});

test('UV density and roles are read from the material slots', async () => {
  const document = await buildDocument({
    side: 0.5, base: await noise(64), normal: await solid(64, [128, 128, 255]), orm: await solid(64, [255, 230, 0]),
  });
  const density = measureUvDensity(document);
  const roles = classifyTextures(document);
  const byName = (name) => document.getRoot().listTextures().find((t) => t.getName() === name);
  assert.ok(Math.abs(density.get(byName('base')) - 2) < 1e-6, 'a 0.5 m quad spans 2 UV units per metre');
  assert.equal(roles.get(byName('base')).role, 'color');
  assert.equal(roles.get(byName('normal')).role, 'normal');
  assert.equal(roles.get(byName('orm')).role, 'linear');
});

test('optimising drops dead maps, shrinks the rest and leaves names alone', async () => {
  const document = await buildDocument({
    side: 0.25, base: await noise(1024), normal: await solid(1024, [128, 128, 255]), orm: await solid(1024, [255, 230, 0]),
  });
  const input = await createIo().writeBinary(document);

  const { output, report } = await optimizeGlbBytes(input, { encoder: encoder() });
  const result = await createIo().readBinary(output);
  const root = result.getRoot();

  assert.equal(report.droppedNormals, 1);
  assert.equal(report.constantOrms, 1);
  assert.equal(root.listTextures().length, 1, 'only the base colour map survives');
  const [texture] = root.listTextures();
  assert.ok(texture.getSize()[0] <= 256, `shrunk to ${texture.getSize()[0]}`);
  assert.ok(output.byteLength < input.byteLength / 2);

  const material = root.listMaterials()[0];
  assert.equal(material.getName(), 'MAT_TEST');
  assert.equal(material.getNormalTexture(), null);
  assert.equal(material.getMetallicRoughnessTexture(), null);
  assert.equal(material.getOcclusionTexture(), null);
  assert.ok(Math.abs(material.getRoughnessFactor() - 230 / 255) < 0.01, 'constant roughness moved into the factor');
  assert.equal(material.getMetallicFactor(), 0);

  const names = root.listNodes().map((node) => node.getName()).sort();
  assert.deepEqual(names, ['ENTRANCE_ANCHOR', 'QUAD_ANCHOR_TARGET']);
  assert.deepEqual(
    root.listNodes().find((node) => node.getName() === 'ENTRANCE_ANCHOR').getTranslation(),
    [1, 2, 3],
  );
});

test('a normal map with real relief is kept', async () => {
  const document = await buildDocument({
    side: 0.25, base: await noise(512), normal: await reliefNormal(512), orm: await noise(512),
  });
  const input = await createIo().writeBinary(document);
  const { output, report } = await optimizeGlbBytes(input, { encoder: encoder() });
  const material = (await createIo().readBinary(output)).getRoot().listMaterials()[0];
  assert.equal(report.droppedNormals, 0);
  assert.equal(report.constantOrms, 0);
  assert.ok(material.getNormalTexture());
  assert.ok(material.getMetallicRoughnessTexture());
});

test('normal maps are capped below colour maps', () => {
  const normal = chooseTextureSize({ width: 2048, height: 2048, texelsPerMetre: 500, role: 'normal' });
  const colour = chooseTextureSize({ width: 2048, height: 2048, texelsPerMetre: 500, role: 'color' });
  assert.equal(normal.width, DEFAULT_OPTIONS.maxNormalSize);
  assert.ok(colour.width > normal.width);
});

const richScene = async () => buildDocument({
  side: 3, base: await noise(256), normal: await reliefNormal(256), orm: await noise(256),
});

test('geometry is compressed losslessly by default and stays where it was', async () => {
  const document = await richScene();
  // Put the quad away from the origin under a rotated, scaled parent.
  document.getRoot().listNodes().find((n) => n.getName() === 'QUAD_ANCHOR_TARGET')
    .setTranslation([10, 2, -4]).setScale([2, 2, 2]).setRotation([0, 0.3826834, 0, 0.9238795]);
  const input = await createIo().writeBinary(document);
  const before = meshWorldBounds(await createIo().readBinary(input));

  const { output, report } = await optimizeGlbBytes(input, { encoder: encoder() });
  assert.equal(report.geometry, 'meshopt');
  assert.equal(report.boundsError, 0, 'lossless geometry is bit-exact');

  const result = await createIo().readBinary(output);
  assert.equal(maxBoundsDifference(before, meshWorldBounds(result)), 0);
  assert.equal(result.getRoot().listExtensionsUsed().some((e) => e.extensionName === 'KHR_mesh_quantization'), false);
});

test('opted-in quantisation stays within the bounds tolerance', async () => {
  const document = await richScene();
  document.getRoot().listNodes().find((n) => n.getName() === 'QUAD_ANCHOR_TARGET').setTranslation([10, 2, -4]);
  const input = await createIo().writeBinary(document);
  const before = meshWorldBounds(await createIo().readBinary(input));

  const { output, report } = await optimizeGlbBytes(input, { encoder: encoder(), quantizePositions: true });
  assert.equal(report.geometry, 'meshopt+quantized');
  // A mesh's extreme vertices land exactly on the quantisation grid, so this
  // guards structure and transforms (a lost, added or displaced mesh), not
  // interior precision, which the bit depth bounds by construction.
  assert.ok(report.boundsError <= DEFAULT_OPTIONS.boundsToleranceMetres);
  // The unquantised original is still what an unquantised read of the input sees.
  assert.equal(maxBoundsDifference(before, meshWorldBounds(await createIo().readBinary(input))), 0);
  assert.ok(output.byteLength > 0);
});

test('skinned meshes are compressed losslessly but never quantised', async () => {
  const document = await richScene();
  const root = document.getRoot();
  assert.equal(canQuantizeGeometry(document), true);
  const joint = document.createNode('bone');
  root.listScenes()[0].addChild(joint);
  document.createSkin('rig').addJoint(joint);
  assert.equal(canCompressGeometry(document), true);
  assert.equal(canQuantizeGeometry(document), false);

  const input = await createIo().writeBinary(document);
  const { report } = await optimizeGlbBytes(input, { encoder: encoder(), quantizePositions: true });
  assert.equal(report.geometry, 'meshopt', 'the quantise request is refused, lossless still applies');
});

test('morph targets keep their geometry untouched', async () => {
  const document = await richScene();
  const mesh = document.getRoot().listMeshes()[0];
  const primitive = mesh.listPrimitives()[0];
  const target = document.createPrimitiveTarget().setAttribute('POSITION', primitive.getAttribute('POSITION'));
  primitive.addTarget(target);
  assert.equal(canCompressGeometry(document), false);
});

test('bounds comparison notices a moved mesh', () => {
  const box = (x) => ({ min: [x, 0, 0], max: [x + 1, 1, 1] });
  assert.equal(maxBoundsDifference([box(0), box(5)], [box(5), box(0)]), 0, 'node order does not matter');
  assert.ok(maxBoundsDifference([box(0)], [box(0.5)]) >= 0.5);
  assert.equal(maxBoundsDifference([box(0)], [box(0), box(1)]), Infinity, 'a lost or added mesh is an error');
});

test('PNG recompression is lossless and never grows the file', async () => {
  // A wasteful encoding (no compression, RGBA) of low-entropy content.
  const source = await sharp({ create: { width: 64, height: 64, channels: 4, background: { r: 30, g: 60, b: 90, alpha: 1 } } })
    .png({ compressionLevel: 0 }).toBuffer();
  const result = await recompressImage(source, '.png');
  assert.ok(result.length < source.length);
  const pixels = async (buffer) => (await sharp(buffer).ensureAlpha().raw().toBuffer()).toString('hex');
  assert.equal(await pixels(result), await pixels(source));
  // Something already tight comes back untouched.
  assert.equal(await recompressImage(result, '.png'), result);
});

test('JPEG recompression keeps dimensions and unknown types pass through', async () => {
  const source = await sharp(await noise(128)).jpeg({ quality: 100, chromaSubsampling: '4:4:4' }).toBuffer();
  const result = await recompressImage(source, '.jpg');
  assert.ok(result.length <= source.length);
  const meta = await sharp(result).metadata();
  assert.equal(meta.width, 128);
  assert.equal(meta.chromaSubsampling, '4:4:4');
  const other = Buffer.from('not an image');
  assert.equal(await recompressImage(other, '.bin'), other);
});

test('PNGs with an alpha channel are left byte-for-byte alone', async () => {
  // Fully transparent pixels carry colour that filtering bleeds into edges.
  const pixels = Buffer.alloc(32 * 32 * 4);
  for (let index = 0; index < pixels.length; index += 4) {
    const pixel = index / 4;
    pixels[index] = pixel & 255; pixels[index + 1] = 90; pixels[index + 2] = 200;
    pixels[index + 3] = pixel % 3 === 0 ? 0 : 255;
  }
  const source = await sharp(pixels, { raw: { width: 32, height: 32, channels: 4 } }).png({ compressionLevel: 0 }).toBuffer();
  assert.equal(await recompressImage(source, '.png'), source);
});
