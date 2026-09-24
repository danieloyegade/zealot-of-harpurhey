import { createHash } from 'node:crypto';
import { existsSync } from 'node:fs';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { Document, Logger, NodeIO, PropertyType } from '@gltf-transform/core';
import {
  ALL_EXTENSIONS, EXTMeshoptCompression, EXTTextureWebP, KHRTextureBasisu,
} from '@gltf-transform/extensions';
import { dequantize, quantize, reorder } from '@gltf-transform/functions';
import { MeshoptDecoder, MeshoptEncoder } from 'meshoptimizer';
import sharp from 'sharp';

/** Bump when a change here alters GLB output, to invalidate cached results. */
export const OPTIMIZER_REVISION = 4;

export const DEFAULT_OPTIONS = {
  // Screen pixels are about 2-4 mm at the distances this game is played from
  // (the internal buffer is under one megapixel), so texels finer than this
  // are never seen. Many authored maps carry 0.3-1 mm.
  targetTexelsPerMetre: 400,
  minTextureSize: 128,
  maxTextureSize: 2048,
  // Relief at this scale is invisible at the render resolution, and UASTC
  // normals are expensive: 2048 px is 3.9 MB where 1024 px is 0.9 MB.
  maxNormalSize: 1024,
  // Used when a texture's UV density cannot be measured.
  unmeasuredMaxSize: 1024,
  // Round a wanted size up to the next power of two only beyond this factor.
  powerOfTwoBias: 1.35,
  // Roughness/AO vary slowly; one size step lower is invisible.
  linearSizeScale: 0.5,
  // Normal maps whose 99th-percentile slope (tan of deviation) stays below
  // this are dead flat: relief the eye cannot see.
  flatNormalSlope: 0.06,
  // ORM maps whose channels all vary less than this are constants.
  constantOrmDeviation: 0.02,
  // Geometry is Meshopt-compressed losslessly (byte-identical after decode).
  // Files opted in via config/asset-optimization.json are also quantised:
  // positions to this many bits per mesh bounding box (14 bits is about
  // 0.6 mm on a 10 m mesh) and normals through Meshopt's octahedral filter.
  // UVs always stay 32-bit float, because the tiled metric UVs run far outside
  // 0-1. Quantising moves each mesh node's origin to its bounding-box centre
  // (and adds child nodes under meshes that have children), so it is only for
  // static buildings whose nodes the game never rotates or looks up by name.
  positionBits: 14,
  // false leaves geometry untouched, for a model that must stay exactly as authored.
  compressGeometry: true,
  // World-space bounds of every mesh must survive the round trip within this.
  boundsToleranceMetres: 0.004,
};

/** Optimizer options that change output; part of the cache key. */
export function optionsFingerprint(options) {
  return createHash('sha1').update(JSON.stringify(options)).update(String(OPTIMIZER_REVISION)).digest('hex');
}

// ---------------------------------------------------------------- sizing

const roundToMultipleOfFour = (value) => Math.max(4, Math.round(value / 4) * 4);

export function roundPowerOfTwo(value, bias) {
  const lower = 2 ** Math.floor(Math.log2(Math.max(value, 1)));
  return value > lower * bias ? lower * 2 : lower;
}

/**
 * Pick output dimensions for a texture. `texelsPerMetre` is the texture's
 * current density on the surfaces that use it (null when unmeasured).
 */
export function chooseTextureSize({ width, height, texelsPerMetre, role }, options = DEFAULT_OPTIONS) {
  const longest = Math.max(width, height);
  let wanted;
  if (texelsPerMetre && Number.isFinite(texelsPerMetre) && texelsPerMetre > 0) {
    wanted = longest * (options.targetTexelsPerMetre / texelsPerMetre);
  } else {
    wanted = Math.min(longest, options.unmeasuredMaxSize);
  }
  if (role === 'linear') wanted *= options.linearSizeScale;
  wanted = Math.min(wanted, longest, options.maxTextureSize);
  if (role === 'normal') wanted = Math.min(wanted, options.maxNormalSize);
  wanted = Math.max(wanted, Math.min(options.minTextureSize, longest));
  let target = Math.min(roundPowerOfTwo(wanted, options.powerOfTwoBias), longest);
  target = Math.max(target, Math.min(options.minTextureSize, longest));
  const ratio = target / longest;
  if (ratio >= 1) return { width, height, changed: false };
  return {
    width: roundToMultipleOfFour(width * ratio),
    height: roundToMultipleOfFour(height * ratio),
    changed: true,
  };
}

// ---------------------------------------------------------------- analysis

const COLOR_SLOTS = new Set(['baseColor', 'emissive']);

/**
 * Which slots each texture serves. A texture also referenced by an extension
 * (clearcoat, sheen, ...) is left alone: its colour space is not known here.
 */
export function classifyTextures(document) {
  const roles = new Map();
  const add = (texture, slot) => {
    if (!texture) return;
    if (!roles.has(texture)) roles.set(texture, new Set());
    roles.get(texture).add(slot);
  };
  for (const material of document.getRoot().listMaterials()) {
    add(material.getBaseColorTexture(), 'baseColor');
    add(material.getEmissiveTexture(), 'emissive');
    add(material.getNormalTexture(), 'normal');
    add(material.getMetallicRoughnessTexture(), 'orm');
    add(material.getOcclusionTexture(), 'orm');
  }
  const result = new Map();
  for (const texture of document.getRoot().listTextures()) {
    const slots = roles.get(texture);
    const extensionParent = texture.listParents().some(
      (parent) => parent.propertyType !== PropertyType.MATERIAL
        && parent.propertyType !== PropertyType.ROOT
        && parent.propertyType !== PropertyType.TEXTURE_INFO,
    );
    if (!slots || extensionParent) {
      result.set(texture, { role: 'unknown', slots: new Set() });
    } else if (slots.has('normal') && slots.size === 1) {
      result.set(texture, { role: 'normal', slots });
    } else if ([...slots].every((slot) => COLOR_SLOTS.has(slot))) {
      result.set(texture, { role: 'color', slots });
    } else if ([...slots].every((slot) => slot === 'orm')) {
      result.set(texture, { role: 'linear', slots });
    } else {
      result.set(texture, { role: 'unknown', slots });
    }
  }
  return result;
}

function textureInfosFor(material, texture) {
  const infos = [];
  const check = (candidate, info) => { if (candidate === texture && info) infos.push(info); };
  check(material.getBaseColorTexture(), material.getBaseColorTextureInfo());
  check(material.getEmissiveTexture(), material.getEmissiveTextureInfo());
  check(material.getNormalTexture(), material.getNormalTextureInfo());
  check(material.getMetallicRoughnessTexture(), material.getMetallicRoughnessTextureInfo());
  check(material.getOcclusionTexture(), material.getOcclusionTextureInfo());
  return infos;
}

/**
 * UV units per metre of surface, per texture, area-weighted over every
 * triangle that samples it. Node scale is applied; runtime rescaling of a
 * whole model (for example the bus shelter) is not, and only makes it denser.
 */
export function measureUvDensity(document) {
  const totals = new Map();
  const point = [0, 0, 0];
  const coordinates = [0, 0];

  for (const node of document.getRoot().listNodes()) {
    const mesh = node.getMesh();
    if (!mesh) continue;
    const world = node.getWorldMatrix();
    const scaleX = Math.hypot(world[0], world[1], world[2]);
    const scaleY = Math.hypot(world[4], world[5], world[6]);
    const scaleZ = Math.hypot(world[8], world[9], world[10]);
    for (const primitive of mesh.listPrimitives()) {
      const material = primitive.getMaterial();
      const position = primitive.getAttribute('POSITION');
      if (!material || !position) continue;
      const indices = primitive.getIndices();
      const count = indices ? indices.getCount() : position.getCount();

      // One pass over the triangles per (UV set, transform scale), shared by
      // every texture of this material that samples that set.
      const passes = new Map();
      for (const texture of new Set([
        material.getBaseColorTexture(), material.getEmissiveTexture(), material.getNormalTexture(),
        material.getMetallicRoughnessTexture(), material.getOcclusionTexture(),
      ].filter(Boolean))) {
        for (const info of textureInfosFor(material, texture)) {
          const transform = info.getExtension('KHR_texture_transform');
          const scale = transform ? Math.abs(transform.getScale()[0] * transform.getScale()[1]) || 1 : 1;
          const key = `${info.getTexCoord()}:${scale}`;
          if (!passes.has(key)) passes.set(key, { texCoord: info.getTexCoord(), scale, textures: new Set() });
          passes.get(key).textures.add(texture);
        }
      }

      for (const { texCoord, scale, textures } of passes.values()) {
        const uv = primitive.getAttribute(`TEXCOORD_${texCoord}`);
        if (!uv) continue;
        let area = 0;
        let uvArea = 0;
        const p0 = [0, 0, 0]; const p1 = [0, 0, 0]; const p2 = [0, 0, 0];
        const uv0 = [0, 0]; const uv1 = [0, 0]; const uv2 = [0, 0];
        const corner = (index, out, uvOut) => {
          const vertex = indices ? indices.getScalar(index) : index;
          position.getElement(vertex, point);
          out[0] = point[0] * scaleX; out[1] = point[1] * scaleY; out[2] = point[2] * scaleZ;
          uv.getElement(vertex, coordinates);
          uvOut[0] = coordinates[0]; uvOut[1] = coordinates[1];
        };
        for (let index = 0; index + 2 < count; index += 3) {
          corner(index, p0, uv0); corner(index + 1, p1, uv1); corner(index + 2, p2, uv2);
          const e1x = p1[0] - p0[0]; const e1y = p1[1] - p0[1]; const e1z = p1[2] - p0[2];
          const e2x = p2[0] - p0[0]; const e2y = p2[1] - p0[1]; const e2z = p2[2] - p0[2];
          area += 0.5 * Math.hypot(
            e1y * e2z - e1z * e2y, e1z * e2x - e1x * e2z, e1x * e2y - e1y * e2x,
          );
          uvArea += 0.5 * Math.abs(
            (uv1[0] - uv0[0]) * (uv2[1] - uv0[1]) - (uv2[0] - uv0[0]) * (uv1[1] - uv0[1]),
          ) * scale;
        }
        if (area <= 0 || uvArea <= 0) continue;
        for (const texture of textures) {
          const total = totals.get(texture) ?? { area: 0, uvArea: 0 };
          total.area += area; total.uvArea += uvArea;
          totals.set(texture, total);
        }
      }
    }
  }
  const density = new Map();
  for (const [texture, { area, uvArea }] of totals) {
    density.set(texture, Math.sqrt(uvArea / area));
  }
  return density;
}

/** 99th-percentile slope (tan of the angle from flat) of a tangent-space normal map. */
export async function measureNormalSlope(image) {
  const { data } = await sharp(image, { limitInputPixels: false })
    .resize(128, 128, { fit: 'fill' }).removeAlpha().raw().toBuffer({ resolveWithObject: true });
  const slopes = [];
  for (let index = 0; index < data.length; index += 3) {
    const x = data[index] / 127.5 - 1;
    const y = data[index + 1] / 127.5 - 1;
    const z = Math.max(data[index + 2] / 127.5 - 1, 0.05);
    slopes.push(Math.hypot(x, y) / z);
  }
  slopes.sort((a, b) => a - b);
  return slopes[Math.floor(slopes.length * 0.99)];
}

/** Per-channel mean and standard deviation (0-1) of an ORM map. */
export async function measureOrm(image) {
  const { data } = await sharp(image, { limitInputPixels: false })
    .resize(128, 128, { fit: 'fill' }).removeAlpha().raw().toBuffer({ resolveWithObject: true });
  const pixels = data.length / 3;
  const sum = [0, 0, 0]; const squares = [0, 0, 0];
  for (let index = 0; index < data.length; index += 3) {
    for (let channel = 0; channel < 3; channel += 1) {
      const value = data[index + channel] / 255;
      sum[channel] += value; squares[channel] += value * value;
    }
  }
  const mean = sum.map((value) => value / pixels);
  const deviation = squares.map((value, channel) => Math.sqrt(Math.max(value / pixels - mean[channel] ** 2, 0)));
  return { mean, deviation };
}

async function hasRealAlpha(image) {
  const metadata = await sharp(image, { limitInputPixels: false }).metadata();
  if (!metadata.hasAlpha) return false;
  return !(await sharp(image, { limitInputPixels: false }).stats()).isOpaque;
}

/** Bytes of GPU memory for a decoded RGBA8 texture with mip chain. */
export const decodedGpuBytes = (width, height) => Math.round(width * height * 4 * (4 / 3));

/** GPU bytes once transcoded: ETC1S -> BC1/ETC2 (0.5 B/px), UASTC -> BC7/ASTC (1 B/px). */
export const compressedGpuBytes = (width, height, uastc) => Math.round(width * height * (uastc ? 1 : 0.5) * (4 / 3));

// ------------------------------------------------------------- optimizing

export function createIo() {
  return new NodeIO()
    .setLogger(new Logger(Logger.Verbosity.WARN))
    .registerExtensions(ALL_EXTENSIONS)
    .registerDependencies({ 'meshopt.encoder': MeshoptEncoder, 'meshopt.decoder': MeshoptDecoder });
}

const meshoptReady = Promise.all([MeshoptEncoder.ready, MeshoptDecoder.ready]);

// ---------------------------------------------------------------- geometry

const hasMorphTargets = (document) => document.getRoot().listMeshes()
  .some((mesh) => mesh.listPrimitives().some((primitive) => primitive.listTargets().length > 0));

/** Lossless Meshopt is safe for skinned meshes; morph targets are left alone. */
export function canCompressGeometry(document) {
  return !hasMorphTargets(document);
}

/** Quantising a skinned mesh would need its skeleton rebuilt, so it never is. */
export function canQuantizeGeometry(document) {
  return canCompressGeometry(document) && document.getRoot().listSkins().length === 0;
}

/** World-space bounds of every mesh node, in node order. */
export function meshWorldBounds(document) {
  const bounds = [];
  for (const node of document.getRoot().listNodes()) {
    const mesh = node.getMesh();
    if (!mesh) { bounds.push(null); continue; }
    const m = node.getWorldMatrix();
    const min = [Infinity, Infinity, Infinity];
    const max = [-Infinity, -Infinity, -Infinity];
    for (const primitive of mesh.listPrimitives()) {
      const position = primitive.getAttribute('POSITION');
      if (!position) continue;
      const low = position.getMin([0, 0, 0]);
      const high = position.getMax([0, 0, 0]);
      for (let corner = 0; corner < 8; corner += 1) {
        const x = corner & 1 ? high[0] : low[0];
        const y = corner & 2 ? high[1] : low[1];
        const z = corner & 4 ? high[2] : low[2];
        const world = [
          m[0] * x + m[4] * y + m[8] * z + m[12],
          m[1] * x + m[5] * y + m[9] * z + m[13],
          m[2] * x + m[6] * y + m[10] * z + m[14],
        ];
        for (let axis = 0; axis < 3; axis += 1) {
          min[axis] = Math.min(min[axis], world[axis]);
          max[axis] = Math.max(max[axis], world[axis]);
        }
      }
    }
    bounds.push({ min, max });
  }
  return bounds;
}

/**
 * How far apart two sets of mesh bounds are, in metres: for every box, the
 * distance to its nearest counterpart in the other set, worst case over both
 * directions. Independent of node order, because quantising can add nodes.
 */
export function maxBoundsDifference(before, after) {
  const boxes = (list) => list.filter(Boolean);
  const a = boxes(before);
  const b = boxes(after);
  if (a.length !== b.length) return Infinity;
  const distance = (first, second) => {
    let worst = 0;
    for (let axis = 0; axis < 3; axis += 1) {
      worst = Math.max(worst, Math.abs(first.min[axis] - second.min[axis]), Math.abs(first.max[axis] - second.max[axis]));
    }
    return worst;
  };
  const nearest = (from, to) => {
    let worst = 0;
    for (const box of from) {
      let best = Infinity;
      for (const candidate of to) {
        const d = distance(box, candidate);
        if (d < best) best = d;
        if (best === 0) break;
      }
      worst = Math.max(worst, best);
    }
    return worst;
  };
  return Math.max(nearest(a, b), nearest(b, a));
}

async function compressGeometry(document, options, quantizePositions) {
  await meshoptReady;
  const transforms = [reorder({ encoder: MeshoptEncoder, target: 'size' })];
  if (quantizePositions) {
    transforms.push(quantize({ pattern: /^POSITION$/, quantizePosition: options.positionBits }));
  }
  await document.transform(...transforms);
  // FILTER (octahedral normals) is only valid on quantised data; the plain
  // QUANTIZE method leaves every attribute exactly as it was.
  document.createExtension(EXTMeshoptCompression).setRequired(true).setEncoderOptions({
    method: quantizePositions
      ? EXTMeshoptCompression.EncoderMethod.FILTER
      : EXTMeshoptCompression.EncoderMethod.QUANTIZE,
  });
}

/** Decode what was actually written and confirm the meshes are where they were. */
async function verifyGeometry(before, output, options, name) {
  const decoded = await createIo().readBinary(output);
  await decoded.transform(dequantize());
  const difference = maxBoundsDifference(before, meshWorldBounds(decoded));
  if (!(difference <= options.boundsToleranceMetres)) {
    throw new Error(`${name}: geometry compression moved a mesh by ${difference} m (limit ${options.boundsToleranceMetres} m)`);
  }
  return difference;
}

/**
 * Optimise one GLB. Only textures change: geometry, node names, material
 * names and every extension the runtime reads are left exactly as authored.
 */
export async function optimizeGlbBytes(input, {
  encoder, options = DEFAULT_OPTIONS, name = 'model.glb', quantizePositions = false,
}) {
  await meshoptReady;
  const io = createIo();
  const document = await io.readBinary(new Uint8Array(input));
  const root = document.getRoot();
  const boundsBefore = meshWorldBounds(document);
  const report = {
    name, bytesBefore: input.byteLength, bytesAfter: 0,
    texturesBefore: root.listTextures().length, texturesAfter: 0,
    resized: 0, droppedNormals: 0, constantOrms: 0, encoded: 0, kept: 0,
    gpuBefore: 0, gpuAfter: 0, format: encoder.compressed ? 'ktx2' : 'webp',
    geometry: 'untouched', boundsError: 0,
  };

  const density = measureUvDensity(document);
  const roles = classifyTextures(document);
  const materials = root.listMaterials();

  // Pass 1: remove maps that carry no information.
  for (const [texture, { role }] of roles) {
    const image = texture.getImage();
    if (!image) continue;
    if (role === 'normal') {
      if ((await measureNormalSlope(image)) < options.flatNormalSlope) {
        for (const material of materials) {
          if (material.getNormalTexture() === texture) material.setNormalTexture(null);
        }
        report.droppedNormals += 1;
        roles.set(texture, { role: 'dropped', slots: new Set() });
      }
    } else if (role === 'linear') {
      const { mean, deviation } = await measureOrm(image);
      const constant = deviation.every((value) => value < options.constantOrmDeviation);
      const usedBy = materials.filter((material) => material.getMetallicRoughnessTexture() === texture
        || material.getOcclusionTexture() === texture);
      const occlusionOnlyIfWhite = usedBy.every(
        (material) => material.getOcclusionTexture() !== texture || mean[0] >= 0.97,
      );
      if (constant && occlusionOnlyIfWhite) {
        for (const material of usedBy) {
          if (material.getMetallicRoughnessTexture() === texture) {
            material.setRoughnessFactor(material.getRoughnessFactor() * mean[1]);
            material.setMetallicFactor(material.getMetallicFactor() * mean[2]);
            material.setMetallicRoughnessTexture(null);
          }
          if (material.getOcclusionTexture() === texture) material.setOcclusionTexture(null);
        }
        report.constantOrms += 1;
        roles.set(texture, { role: 'dropped', slots: new Set() });
      }
    }
  }
  for (const texture of root.listTextures()) {
    const [width, height] = texture.getSize() ?? [0, 0];
    report.gpuBefore += decodedGpuBytes(width, height);
    if (roles.get(texture)?.role === 'dropped') texture.dispose();
  }

  // Pass 2: right-size and re-encode what remains.
  const jobs = [];
  for (const [texture, { role }] of roles) {
    if (role === 'dropped' || texture.isDisposed?.()) continue;
    const image = texture.getImage();
    if (!image || texture.getMimeType() === 'image/ktx2') { report.kept += 1; continue; }
    if (role === 'unknown') { report.kept += 1; continue; }
    jobs.push((async () => {
      const [width, height] = texture.getSize();
      const perMetre = density.get(texture);
      const size = chooseTextureSize({
        width, height, role, texelsPerMetre: perMetre ? perMetre * Math.sqrt(width * height) : null,
      }, options);
      const alpha = role !== 'normal' && await hasRealAlpha(image);
      const result = await encoder.encode({ image, width: size.width, height: size.height, role, alpha });
      texture.setImage(result.data);
      texture.setMimeType(result.format === 'ktx2' ? 'image/ktx2' : 'image/webp');
      if (size.changed) report.resized += 1;
      report.encoded += 1;
      report.gpuAfter += result.format === 'ktx2'
        ? compressedGpuBytes(size.width, size.height, role === 'normal' || alpha)
        : decodedGpuBytes(size.width, size.height);
    })());
  }
  await Promise.all(jobs);

  const formats = new Set(root.listTextures().map((texture) => texture.getMimeType()));
  const hasExtension = (extension) => root.listExtensionsUsed().some((used) => used.extensionName === extension.EXTENSION_NAME);
  if (formats.has('image/ktx2') && !hasExtension(KHRTextureBasisu)) {
    document.createExtension(KHRTextureBasisu).setRequired(true);
  }
  if (formats.has('image/webp') && !hasExtension(EXTTextureWebP)) {
    document.createExtension(EXTTextureWebP).setRequired(false);
  }

  const compressed = options.compressGeometry && canCompressGeometry(document);
  const quantized = compressed && quantizePositions && canQuantizeGeometry(document);
  if (compressed) await compressGeometry(document, options, quantized);

  const output = await io.writeBinary(document);
  if (compressed) {
    report.boundsError = await verifyGeometry(boundsBefore, output, options, name);
    report.geometry = quantized ? 'meshopt+quantized' : 'meshopt';
  }
  report.texturesAfter = root.listTextures().length;
  report.bytesAfter = output.byteLength;
  return { output, report };
}

/** Cached wrapper: identical input, options and encoder reuse the previous output. */
export async function optimizeGlbFile(sourcePath, destinationPath, { cacheDirectory, ...rest }) {
  const input = await readFile(sourcePath);
  const key = createHash('sha1')
    .update(input)
    .update(optionsFingerprint(rest.options ?? DEFAULT_OPTIONS))
    .update(rest.encoder.compressed ? 'ktx2' : 'webp')
    .update(rest.quantizePositions ? 'quantized' : 'lossless')
    .digest('hex');
  const cachePath = cacheDirectory ? join(cacheDirectory, `${key}.glb`) : null;
  const reportPath = cachePath ? `${cachePath}.json` : null;
  if (cachePath && existsSync(cachePath) && existsSync(reportPath)) {
    await writeFile(destinationPath, await readFile(cachePath));
    return { ...JSON.parse(await readFile(reportPath, 'utf8')), cached: true };
  }
  const { output, report } = await optimizeGlbBytes(input, { ...rest, name: sourcePath });
  await writeFile(destinationPath, output);
  if (cachePath) {
    await mkdir(cacheDirectory, { recursive: true });
    await writeFile(cachePath, output);
    await writeFile(reportPath, JSON.stringify(report));
  }
  return { ...report, cached: false };
}

export { Document };
