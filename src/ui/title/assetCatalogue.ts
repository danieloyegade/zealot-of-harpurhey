// Asset loads described as catalogue entries: the city listed object by object
// as it is reconstructed. Known files are authored; anything else is derived
// from its filename once the pipeline words are removed.

export const UNIDENTIFIED_OBJECT = 'spectre / unidentified';

// Matched against the lowercased filename, without extension or `harpurhey-`.
const CATALOGUE: readonly (readonly [RegExp, string])[] = [
  [/^coral-shop/, 'coral / illuminated fascia'],
  [/^coral-bin/, 'litter bin / coral'],
  [/^streetlight-warm-old/, 'street lamp / low-pressure sodium'],
  [/^streetlight-led-modern/, 'street lamp / led / 4000 k'],
  [/^streetlight-curved/, 'street lamp / swan neck'],
  [/^streetlight-weathered/, 'street lamp / galvanised / weathered'],
  [/^coral-bollard/, 'bollard / municipal'],
  [/^coral-photo/, 'coral / photograph'],
  [/^nice-things/, 'nice things / florist'],
  [/^dreams-greybox/, 'dreams / shopfront'],
  [/^dreams-photo/, 'dreams / photograph'],
  [/^gullivers/, "gulliver's / public house"],
  [/^mcr1/, 'mcr1 / frontage'],
  [/^cass[-_]art/, 'cass art / aerosol cabinet'],
  [/^renee/, 'renee / shopfront'],
  [/^the[-_]hive/, 'arts council / the hive'],
  [/^come[-_]through[-_]lab/, 'come through lab / 84 silk street'],
  [/^ctl[-_]dropbox/, 'come through lab / drop box'],
  [/^ctl[-_]dropoff[-_]props/, 'film envelope / pencil'],
  [/^village-books/, 'village books / shopfront'],
  [/^advanced-photo/, 'advanced photo / kiosk'],
  [/^spice-cabin/, 'spice cabin / timber'],
  [/^pallet[-_]worn[-_]blue/, 'pallet / timber / worn blue'],
  [/^pallet[-_]worn[-_]brown/, 'pallet / timber / worn brown'],
  [/^real[-_]camera/, 'real camera / sevendale house'],
  [/^vinyl-exchange/, 'vinyl exchange / upper floor'],
  [/^preston-bus/, 'bus shelter / scratched glass'],
  [/^greek[-_]gyros/, 'greek gyros / fluorescent interior'],
  [/^sterling-bike/, 'bicycle / sterling'],
  [/^sterling-dock/, 'bicycle dock / sterling'],
  [/^player-character/, 'rider 01 / denim / oversized'],
  [/^road-decal/, 'road marking / worn paint'],
  [/^road-asphalt/, 'carriageway / asphalt'],
  [/^pavement-decal/, 'pavement / chewing gum'],
  [/^pavement-(albedo|normal|roughness)$/, 'pavement / concrete flags'],
  [/^poster-wall/, 'poster / wet paste'],
  [/^light-cone-noise/, 'light / sodium haze'],
  [/^reflection-broken/, 'reflection / broken'],
  [/^window-row/, 'windows / upper floors'],
  [/^street-detail-atlas/, 'drain cover / kerb / litter'],
];

const PIPELINE_WORDS = new Set([
  'albedo',
  'atlas',
  'basecolor',
  'blockout',
  'geometry',
  'greybox',
  'hero',
  'hires',
  'module',
  'normal',
  'orm',
  'overhaul',
  'reference',
  'roughness',
  'set',
  'temporary',
  'textured',
]);

/** Textures embedded in GLBs arrive as blob or data URLs, with no name to read. */
export function isAnonymousAsset(url: string): boolean {
  return url.startsWith('blob:') || url.startsWith('data:');
}

// 'assets/models/pallets/pallet_worn_brown.glb?v=…' → 'pallet / timber / worn brown'
export function describeAsset(url: string): string | null {
  if (isAnonymousAsset(url)) return null;

  const name = assetName(url);
  for (const [pattern, description] of CATALOGUE) {
    if (pattern.test(name)) return description;
  }

  const words = name.split(/[-_\s]+/).filter((word) => word && !PIPELINE_WORDS.has(word));
  if (words.length === 0) return null;
  return words.length === 1 ? words[0]! : `${words[0]} / ${words.slice(1).join(' ')}`;
}

function assetName(url: string): string {
  const file = url.split(/[?#]/)[0]?.split('/').pop() ?? '';
  let name = file;
  try {
    name = decodeURIComponent(file);
  } catch {
    // Keep the raw segment if it is not valid percent-encoding.
  }
  return name
    .toLowerCase()
    .replace(/\.[a-z0-9]+$/, '')
    .replace(/^harpurhey[-_]/, '');
}
