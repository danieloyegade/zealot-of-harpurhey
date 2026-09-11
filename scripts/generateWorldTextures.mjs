import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { mkdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const outputDirectory = new URL(
  '../public/assets/textures/world-prototype/',
  import.meta.url,
);
await mkdir(outputDirectory, { recursive: true });

const temporaryDirectory = mkdtempSync(join(tmpdir(), 'zealot-world-textures-'));
const clamp = (value) => Math.max(0, Math.min(255, Math.round(value)));
const noise = (x, y, seed = 0) => {
  let value = Math.imul(x + seed * 101, 374761393);
  value = Math.imul(value ^ Math.imul(y + seed * 37, 668265263), 1274126177);
  return ((value ^ (value >>> 13)) >>> 0) / 4294967295;
};

function writeTexture(name, width, height, pixel) {
  const header = Buffer.from(`P6\n${width} ${height}\n255\n`);
  const pixels = Buffer.alloc(width * height * 3);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const color = pixel(x, y, noise(x, y));
      const offset = (y * width + x) * 3;
      pixels[offset] = clamp(color[0]);
      pixels[offset + 1] = clamp(color[1]);
      pixels[offset + 2] = clamp(color[2]);
    }
  }

  const sourcePath = join(temporaryDirectory, `${name}.ppm`);
  const outputPath = new URL(`${name}.png`, outputDirectory);
  writeFileSync(sourcePath, Buffer.concat([header, pixels]));
  const result = spawnSync(
    '/usr/bin/sips',
    [sourcePath, '-s', 'format', 'png', '-o', outputPath.pathname],
    { encoding: 'utf8' },
  );
  if (result.status !== 0) {
    throw new Error(result.stderr || `Could not generate ${name}.png`);
  }
  console.log(`${name}.png ${width}x${height}`);
}

function derivePhotoTexture(name, sourceRelativePath, videoFilter) {
  const sourcePath = fileURLToPath(new URL(sourceRelativePath, import.meta.url));
  const outputPath = fileURLToPath(new URL(`${name}.png`, outputDirectory));
  const result = spawnSync(
    'ffmpeg',
    [
      '-loglevel',
      'error',
      '-y',
      '-i',
      sourcePath,
      '-vf',
      videoFilter,
      outputPath,
    ],
    { encoding: 'utf8' },
  );
  if (result.status !== 0) {
    throw new Error(result.stderr || `Could not derive ${name}.png`);
  }
  console.log(`${name}.png photographic derivative`);
}

const grain = (base, n, amount) => base + (n - 0.5) * amount;
const stain = (x, y, seed) => {
  const broad = noise(Math.floor(x / 13), Math.floor(y / 17), seed);
  return broad > 0.72 ? (broad - 0.72) * 85 : 0;
};

writeTexture('asphalt-dark-temporary', 256, 256, (x, y, n) => {
  const patch = noise(Math.floor(x / 32), Math.floor(y / 28), 4) * 15;
  const crack = Math.abs((x + y * 0.37 + noise(y, 3, 8) * 18) % 83 - 41) < 0.7;
  const value = grain(35 + patch, n, 34) - (crack ? 22 : 0);
  return [value * 0.9, value * 0.96, value];
});

writeTexture('pavement-worn-temporary', 256, 256, (x, y, n) => {
  const joint = x % 64 < 3 || y % 48 < 3;
  const grime = stain(x, y, 7);
  const value = grain(joint ? 48 : 105, n, 30) - grime;
  return [value, value * 0.98, value * 0.9];
});

writeTexture('pavement-damp-temporary', 256, 256, (x, y, n) => {
  const joint = x % 64 < 3 || y % 48 < 3;
  const wet = noise(Math.floor(x / 18), Math.floor(y / 15), 14);
  const value = grain(joint ? 35 : 72 + wet * 30, n, 22);
  return [value * 0.75, value * 0.86, value];
});

function brickPixel(base, mortar, seed) {
  return (x, y, n) => {
    const row = Math.floor(y / 12);
    const shiftedX = x + (row % 2) * 18;
    const isMortar = y % 12 < 2 || shiftedX % 36 < 2;
    const grime = stain(x, y, seed);
    const source = isMortar ? mortar : base;
    return source.map((channel) => grain(channel, n, 30) - grime);
  };
}

writeTexture('brick-red-temporary', 256, 256, brickPixel([103, 43, 34], [77, 68, 60], 17));
writeTexture('brick-brown-temporary', 256, 256, brickPixel([72, 52, 37], [65, 62, 55], 19));
writeTexture('masonry-alley-temporary', 256, 256, (x, y, n) => {
  const block = x % 52 < 2 || y % 32 < 2;
  const drip = noise(Math.floor(x / 9), 0, 23) > 0.76 ? y / 18 : 0;
  const value = grain(block ? 42 : 70, n, 28) - drip - stain(x, y, 24);
  return [value * 0.92, value * 0.9, value];
});

writeTexture('concrete-stained-temporary', 256, 256, (x, y, n) => {
  const run = noise(Math.floor(x / 14), 2, 31) > 0.78 ? y / 20 : 0;
  const value = grain(102, n, 26) - stain(x, y, 29) - run;
  return [value * 0.93, value * 0.95, value];
});

writeTexture('painted-metal-temporary', 256, 256, (x, y, n) => {
  const seam = x % 48 < 2;
  const scratch = noise(x, Math.floor(y / 7), 37) > 0.994;
  return [grain(seam ? 40 : 60, n, 18) + (scratch ? 45 : 0), grain(70, n, 16), grain(76, n, 20)];
});

writeTexture('shop-shutter-temporary', 256, 256, (x, y, n) => {
  const ridge = y % 10 < 3;
  const rust = noise(Math.floor(x / 11), Math.floor(y / 19), 41) > 0.8 ? 26 : 0;
  return [grain(ridge ? 62 : 91, n, 22) + rust, grain(ridge ? 65 : 94, n, 18) - rust * 0.4, grain(ridge ? 68 : 96, n, 18) - rust * 0.6];
});

writeTexture('window-dark-temporary', 256, 256, (x, y, n) => {
  const frame = x % 64 < 4 || y % 80 < 4;
  const reflected = (x + y) % 97 < 8 ? 16 : 0;
  return frame ? [36, 43, 47] : [grain(12, n, 8), grain(24 + reflected, n, 10), grain(34 + reflected, n, 12)];
});

writeTexture('window-lit-temporary', 256, 256, (x, y, n) => {
  const frame = x % 64 < 4 || y % 80 < 4;
  const greenCast = Math.floor(x / 64) % 3 === 1;
  if (frame) return [42, 39, 34];
  return greenCast
    ? [grain(75, n, 16), grain(139, n, 22), grain(86, n, 16)]
    : [grain(186, n, 28), grain(128, n, 20), grain(57, n, 15)];
});

writeTexture('grass-cheap-temporary', 256, 256, (x, y, n) => {
  const tuft = noise(Math.floor(x / 5), Math.floor(y / 7), 53);
  return [grain(25 + tuft * 12, n, 18), grain(54 + tuft * 28, n, 26), grain(31 + tuft * 10, n, 16)];
});

writeTexture('foliage-rough-temporary', 128, 128, (x, y, n) => {
  const clump = noise(Math.floor(x / 8), Math.floor(y / 8), 61);
  return [grain(15 + clump * 12, n, 18), grain(42 + clump * 45, n, 30), grain(23 + clump * 14, n, 18)];
});

writeTexture('tree-bark-temporary', 128, 128, (x, y, n) => {
  const groove = x % 11 < 3 ? -18 : 0;
  return [grain(66 + groove, n, 22), grain(46 + groove * 0.6, n, 18), grain(31 + groove * 0.4, n, 14)];
});

// Art-direction overhaul surfaces. These intentionally contain local repairs,
// exposure shifts and dirt rather than uniform material noise.
writeTexture('asphalt-wet-overhaul', 512, 512, (x, y, n) => {
  const broad = noise(Math.floor(x / 48), Math.floor(y / 43), 71);
  const aggregate = noise(x * 3, y * 5, 73);
  const utilityCut = x > 292 && x < 366 && y > 42 && y < 430;
  const repaired = x > 44 && x < 206 && y > 310 && y < 404;
  const crackA = Math.abs((x * 0.84 + y * 0.27 + noise(y, 4, 75) * 24) % 137 - 68) < 1.1;
  const crackB = Math.abs((x * 0.18 - y + noise(x, 5, 76) * 17) % 181 - 90) < 0.8;
  const wetBand = noise(Math.floor(x / 17), Math.floor(y / 61), 77) > 0.63;
  let value = 39 + broad * 24 + (aggregate - 0.5) * 30;
  if (utilityCut) value -= 8;
  if (repaired) value += 7;
  if (crackA || crackB) value -= 22;
  if (wetBand) value -= 4;
  return [value * 0.78, value * 0.9, value * 1.05];
});

function weatheredSlab(wet) {
  return (x, y, n) => {
    const row = Math.floor(y / 64);
    const shiftedX = x + (row % 2) * 48;
    const joint = shiftedX % 96 < 4 || y % 64 < 4;
    const tile = noise(Math.floor(shiftedX / 96), Math.floor(y / 64), wet ? 83 : 81);
    const gum = noise(Math.floor(x / 5), Math.floor(y / 5), 87) > 0.992;
    const repair = x > 310 && x < 455 && y > 205 && y < 305;
    const run = noise(Math.floor(x / 16), 0, 89) > 0.8 ? y / 54 : 0;
    let value = joint ? 34 : 76 + tile * 43 + (n - 0.5) * 21 - run;
    if (repair) value -= 14;
    if (gum) value += wet ? 38 : 23;
    const blue = wet ? 0.98 : 0.96;
    return [value * (wet ? 0.8 : 0.93), value * 0.9, value * blue];
  };
}

writeTexture('pavement-weathered-overhaul', 512, 512, weatheredSlab(false));
writeTexture('pavement-wet-overhaul', 512, 512, weatheredSlab(true));

writeTexture('brick-soot-overhaul', 512, 512, (x, y, n) => {
  const row = Math.floor(y / 15);
  const shiftedX = x + (row % 2) * 22;
  const mortar = y % 15 < 2 || shiftedX % 44 < 3;
  const brickAge = noise(Math.floor(shiftedX / 38), row, 97);
  const soot = Math.max(0, 1 - y / 350) * 34;
  const damp = noise(Math.floor(x / 29), Math.floor(y / 37), 101) > 0.7 ? 22 : 0;
  const value = mortar ? 54 : 76 + brickAge * 36 + (n - 0.5) * 24;
  return [value - soot - damp, value * 0.54 - soot, value * 0.42 - damp];
});

writeTexture('brick-painted-overhaul', 512, 512, (x, y, n) => {
  const row = Math.floor(y / 16);
  const shiftedX = x + (row % 2) * 34;
  const mortar = y % 16 < 2 || shiftedX % 68 < 3;
  const peel = noise(Math.floor(x / 8), Math.floor(y / 7), 109) > 0.86;
  const drip = noise(Math.floor(x / 15), 0, 111) > 0.78 ? y / 24 : 0;
  if (mortar) return [48, 43, 41];
  if (peel) return [grain(73, n, 18), grain(38, n, 15), grain(31, n, 12)];
  return [grain(116 - drip, n, 22), grain(42 - drip * 0.4, n, 14), grain(45, n, 15)];
});

writeTexture('concrete-cracked-overhaul', 512, 512, (x, y, n) => {
  const panel = x % 171 < 3 || y % 128 < 3;
  const crack = Math.abs((x * 0.41 + y + noise(x, 1, 121) * 22) % 163 - 81) < 1;
  const water = noise(Math.floor(x / 23), 2, 123) > 0.76 ? y / 26 : 0;
  const patch = x > 55 && x < 212 && y > 92 && y < 238;
  let value = 93 + (n - 0.5) * 28 - water;
  if (panel) value -= 24;
  if (crack) value -= 38;
  if (patch) value += 10;
  return [value * 0.91, value * 0.94, value];
});

writeTexture('shutter-grimy-overhaul', 512, 512, (x, y, n) => {
  const ridge = y % 12 < 4;
  const rust = noise(Math.floor(x / 14), Math.floor(y / 21), 131) > 0.78;
  const sticker = (x > 72 && x < 132 && y > 277 && y < 342)
    || (x > 358 && x < 423 && y > 109 && y < 178);
  const scratch = noise(x, Math.floor(y / 5), 133) > 0.993;
  if (sticker) return [grain(174, n, 22), grain(151, n, 24), grain(76, n, 18)];
  return [grain(ridge ? 50 : 75, n, 18) + (rust ? 43 : 0) + (scratch ? 35 : 0), grain(ridge ? 53 : 72, n, 16) - (rust ? 18 : 0), grain(ridge ? 56 : 67, n, 16) - (rust ? 22 : 0)];
});

writeTexture('metal-oxidised-overhaul', 256, 256, (x, y, n) => {
  const seam = x % 64 < 3;
  const chip = noise(Math.floor(x / 6), Math.floor(y / 5), 139) > 0.9;
  const rust = noise(Math.floor(x / 17), Math.floor(y / 19), 141) > 0.75;
  if (chip) return [96, 92, 79];
  return [grain(seam ? 31 : 47, n, 17) + (rust ? 39 : 0), grain(seam ? 48 : 64, n, 19) + (rust ? 4 : 0), grain(seam ? 50 : 61, n, 15) - (rust ? 17 : 0)];
});

writeTexture('grass-damp-overhaul', 512, 512, (x, y, n) => {
  const clump = noise(Math.floor(x / 9), Math.floor(y / 11), 149);
  const bare = noise(Math.floor(x / 37), Math.floor(y / 33), 151) > 0.79;
  const leaf = noise(Math.floor(x / 4), Math.floor(y / 4), 153) > 0.965;
  if (bare) return [grain(39, n, 14), grain(34, n, 12), grain(25, n, 10)];
  return [grain(18 + clump * 18 + (leaf ? 24 : 0), n, 17), grain(43 + clump * 38 + (leaf ? 19 : 0), n, 24), grain(25 + clump * 17, n, 14)];
});

writeTexture('foliage-dark-overhaul', 256, 256, (x, y, n) => {
  const mass = noise(Math.floor(x / 13), Math.floor(y / 12), 157);
  const leaf = noise(Math.floor(x / 3), Math.floor(y / 4), 159);
  const amberCatch = x < 72 && y > 88 && leaf > 0.82;
  return [grain(10 + mass * 18 + (amberCatch ? 57 : 0), n, 14), grain(27 + mass * 46 + (amberCatch ? 36 : 0), n, 25), grain(18 + mass * 18, n, 15)];
});

writeTexture('reflection-broken-overhaul', 256, 256, (x, y, n) => {
  const streak = Math.abs((x + noise(Math.floor(y / 9), 1, 163) * 33) % 57 - 28) < 4;
  const fragment = noise(Math.floor(x / 7), Math.floor(y / 13), 167) > 0.48;
  const fade = Math.max(0, 1 - Math.abs(x - 128) / 128);
  const value = streak && fragment ? (78 + n * 132) * fade : n * 5;
  return [value, value, value];
});

writeTexture('light-cone-noise-overhaul', 128, 256, (x, y, n) => {
  const edge = Math.max(0, 1 - Math.abs(x - 64) / 64);
  const broken = noise(Math.floor(x / 7), Math.floor(y / 13), 173);
  const verticalFade = 0.3 + (y / 256) * 0.7;
  const value = (15 + broken * 80) * edge * verticalFade + n * 6;
  return [value, value, value];
});

writeTexture('poster-wall-overhaul', 256, 512, (x, y, n) => {
  const column = Math.floor(x / 64);
  const row = Math.floor(y / 96);
  const localX = x % 64;
  const localY = y % 96;
  const border = localX < 4 || localY < 5 || localX > 59 || localY > 90;
  const torn = noise(Math.floor(x / 5), Math.floor(y / 4), 179) > 0.94;
  const ink = localY > 18 && localY < 77 && (localY % 13 < 5 || localX % 23 < 4);
  const palettes = [
    [147, 45, 36],
    [192, 139, 45],
    [56, 104, 82],
    [78, 64, 118],
  ];
  const color = palettes[(column + row) % palettes.length];
  if (border || torn) return [grain(41, n, 16), grain(37, n, 14), grain(31, n, 13)];
  if (ink) return color.map((channel) => grain(channel * 0.35, n, 15));
  return color.map((channel) => grain(channel, n, 27));
});

writeTexture('window-row-overhaul', 512, 256, (x, y, n) => {
  const frame = x % 86 < 7 || y % 118 < 7 || y > 232;
  const pane = Math.floor(x / 86);
  const warm = pane % 5 === 1 || pane % 7 === 4;
  const curtain = (x + pane * 13) % 71 < 16;
  if (frame) return [45, 43, 39];
  if (warm) return [grain(157, n, 24), grain(103, n, 22), grain(44, n, 13)];
  return curtain
    ? [grain(27, n, 9), grain(30, n, 10), grain(36, n, 11)]
    : [grain(11, n, 7), grain(21, n, 10), grain(32, n, 12)];
});

writeTexture('street-detail-atlas', 256, 256, (x, y, n) => {
  const border = x < 8 || y < 8 || x > 247 || y > 247;
  const slot = x % 32 < 4 || y % 28 < 3;
  const rust = noise(Math.floor(x / 11), Math.floor(y / 13), 191) > 0.79;
  const tar = Math.abs((x * 0.63 + y + noise(y, 7, 193) * 18) % 91 - 45) < 2;
  let value = 48 + (n - 0.5) * 32;
  if (border) value -= 20;
  if (slot) value -= 13;
  if (tar) value += 14;
  return [value + (rust ? 36 : 0), value + (rust ? 7 : 0), value - (rust ? 8 : 0)];
});

writeTexture('soil-litter-hero', 256, 256, (x, y, n) => {
  const clod = noise(Math.floor(x / 14), Math.floor(y / 12), 197);
  const foil = noise(Math.floor(x / 5), Math.floor(y / 4), 199) > 0.975;
  const paper = x > 74 && x < 154 && y > 132 && y < 202;
  const leaf = Math.abs((x * 0.7 - y + noise(x, 8, 201) * 20) % 67 - 33) < 2;
  if (foil) return [132, 139, 142];
  if (paper) return [grain(112, n, 24), grain(96, n, 22), grain(69, n, 18)];
  const value = 39 + clod * 24 + (leaf ? 22 : 0);
  return [grain(value, n, 18), grain(value * 0.82, n, 15), grain(value * 0.58, n, 12)];
});

derivePhotoTexture(
  'dreams-photo-overhaul',
  '../references/architecture/dreams/Dreams.jpg',
  'crop=2900:1450:60:450,scale=512:256:flags=lanczos,eq=contrast=1.12:saturation=0.8:brightness=-0.08',
);
derivePhotoTexture(
  'dreams-cladding-hero',
  '../references/architecture/dreams/Dreams.jpg',
  'crop=1700:350:165:500,scale=512:128:flags=lanczos,eq=contrast=1.08:saturation=0.72:brightness=-0.05',
);
derivePhotoTexture(
  'dreams-shutter-hero',
  '../references/architecture/dreams/Dreams.jpg',
  'crop=1950:600:280:1200,scale=512:256:flags=lanczos,eq=contrast=1.12:saturation=0.68:brightness=-0.1',
);
derivePhotoTexture(
  'dreams-brick-hero',
  '../references/architecture/dreams/Dreams.jpg',
  'crop=500:700:2100:1050,scale=256:256:flags=lanczos,eq=contrast=1.1:saturation=0.9:brightness=-0.08',
);
derivePhotoTexture(
  'coral-photo-overhaul',
  '../references/architecture/coral/coral.jpg',
  'crop=2800:1000:120:1300,scale=512:256:flags=lanczos,eq=contrast=1.08:saturation=0.9:brightness=-0.05',
);

rmSync(temporaryDirectory, { recursive: true, force: true });
