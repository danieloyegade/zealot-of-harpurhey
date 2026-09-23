import { defineConfig } from 'vite';

// No @types/node in this project; declare just what this config needs.
declare const process: { env: Record<string, string | undefined> };

const requestedPort = process.env.PORT ? Number(process.env.PORT) : undefined;

export default defineConfig({
  // Served from its own Worker origin and embedded on danieloye.com via
  // iframe, so it's rooted at '/' rather than a subpath of the host site.
  base: '/',
  // Generated from config/runtime-assets.json by the npm lifecycle scripts.
  // Development receives the full workshop; production receives only runtime
  // dependencies that have passed the release boundary.
  publicDir: '.runtime-public',
  server: {
    port: requestedPort ?? 5173,
    strictPort: requestedPort !== undefined,
  },
});
