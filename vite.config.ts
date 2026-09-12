import { defineConfig } from 'vite';

// No @types/node in this project; declare just what this config needs.
declare const process: { env: Record<string, string | undefined> };

const requestedPort = process.env.PORT ? Number(process.env.PORT) : undefined;

export default defineConfig({
  base: '/zealot-of-harperhey/',
  server: {
    port: requestedPort ?? 5173,
    strictPort: requestedPort !== undefined,
  },
});
