/*
 * The single seam between asset paths as game code writes them and the URLs
 * they are actually fetched from. Every runtime fetch out of `public/assets`
 * goes through here — models, textures, audio.
 *
 * By default assets resolve against the site itself via Vite's BASE_URL, which
 * is what `npm run dev` and any same-origin deploy want. Setting
 * VITE_ASSET_BASE_URL at build time points them at a separate origin instead —
 * an object store or CDN — without touching a single call site.
 */

const configuredBase = import.meta.env.VITE_ASSET_BASE_URL?.trim();

function withTrailingSlash(base: string): string {
  return base.endsWith('/') ? base : `${base}/`;
}

// An env var that is defined but empty means "unset", not "serve from the root".
const ASSET_BASE_URL = new URL(
  withTrailingSlash(configuredBase ? configuredBase : import.meta.env.BASE_URL),
  window.location.href,
);

/*
 * Percent-encode each path segment, leaving any `?v=...` cache-busting suffix
 * intact. Encoding the whole string would fold the query into the filename and
 * 404 every versioned model; not encoding at all breaks the audio filenames
 * that contain spaces.
 */
function encodeAssetPath(path: string): string {
  const suffixStart = path.search(/[?#]/);
  const filePath = suffixStart === -1 ? path : path.slice(0, suffixStart);
  const suffix = suffixStart === -1 ? '' : path.slice(suffixStart);

  return `${filePath.split('/').map(encodeURIComponent).join('/')}${suffix}`;
}

/**
 * Resolve a path relative to the asset root (e.g. `assets/models/foo.glb`) to
 * an absolute URL. Accepts an optional `?v=` cache-busting suffix.
 */
export function assetUrl(relativePath: string): string {
  const cleanedPath = relativePath.replace(/^\/+/, '');

  return new URL(encodeAssetPath(cleanedPath), ASSET_BASE_URL).href;
}
