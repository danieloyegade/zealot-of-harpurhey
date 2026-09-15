/// <reference types="vite/client" />

interface ImportMetaEnv {
  /*
   * Origin that runtime assets (models, textures, audio) are served from.
   * Unset means "same origin as the site", resolved via BASE_URL. Set it to a
   * bucket or CDN origin to serve assets from somewhere other than the app.
   */
  readonly VITE_ASSET_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
