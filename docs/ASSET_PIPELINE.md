# Runtime asset pipeline

Authored files under `public/` are the **source of truth** and are never
modified by the build. When `npm run assets:prepare` (or `predev`, or
`prebuild`) copies the manifest's files into `.runtime-public/`, it then
optimises the copies. Blender exports, the Blender scripts and every other
session's files keep working exactly as before; only what the player downloads
and what the GPU holds changes.

```
public/  (authored, untouched)  ──▶  .runtime-public/  (optimised, gitignored)  ──▶  dist/  ──▶  Cloudflare
```

## Why this exists

Measured on 2026-09-24 against the production manifest:

| | Before | After |
| --- | --- | --- |
| Shipped files | 128.8 MB | 51.7 MB |
| Models (33 GLBs) | 98.4 MB | 40.4 MB |
| Loose textures | 19.6 MB | 10.0 MB |
| Title art | 10.8 MB | 0.75 MB |
| **Texture memory once decoded** | **about 2,040 MB** in models, plus 183 MB loose | **about 120 MB** in models, plus 183 MB loose |

The decoded figure is the one that hurts. Roughly 100 maps were 2048² RGBA
(22 MB each once decoded and mip-mapped), and three.js uploads a mesh's
textures the first time it renders, so walking somewhere new stalled the frame.
Forcing every off-screen mesh to render once took **21 s** in one browser
before optimisation. See `docs/PERFORMANCE.md` for how the loading screen now
prepares the scene; this pipeline is what makes that preparation cheap.

## What the optimiser does to a GLB

Code: `scripts/optimizeRuntimeAssets.mjs`, `scripts/lib/glbOptimizer.mjs`,
`scripts/lib/textureEncoder.mjs`. Tests: `tests/asset-optimizer.test.mjs`.

1. **Right-sizes each texture from measured density.** For every texture it
   computes how many texels land on each metre of the surfaces that sample it
   (UV area against world area, per triangle, node scale included) and shrinks
   it to about **400 texels per metre (2.5 mm)**. The game renders into a buffer
   under one megapixel, so a pixel is 2–4 mm at play distances; the authored
   0.3–1 mm was invisible. It never upscales, never goes below 128 px, rounds to
   a power of two, and gives roughness/AO maps one size step less and normal
   maps a 1024 px ceiling.
2. **Drops maps that carry no information.** 63 of 106 normal maps were
   perfectly flat (99th-percentile slope 0.006, pure quantisation noise) and 25
   of 115 ORM maps were constant. Flat normals are removed; constant ORM values
   move into `roughnessFactor` / `metallicFactor`. Each removal is one less
   texture to download, upload and sample per material. (Compiled shader
   programs did not change measurably: 77 before, 80 after.)
3. **Re-encodes what remains as KTX2** through `basisu`: ETC1S for colour and
   ORM, UASTC for normal maps and anything with real alpha. The browser
   transcodes to the GPU's own compressed format (ASTC, BC7, ETC2...), so a 1024²
   colour map costs about 0.7 MB of GPU memory instead of 5.6 MB and needs no
   image decode. Normals are re-normalised after resizing.
4. **Compresses geometry with Meshopt, losslessly** (byte-identical floats after
   decode). Skinned meshes are included; morph targets are left alone.
5. **Optionally quantises positions to 14 bits**, only for the files listed in
   `config/asset-optimization.json` (currently Real Camera and the Coral shop;
   measured on Real Camera, 14-bit quantising takes 10.6 MB down to 5.7 MB
   beyond what lossless compression already gives). Quantising moves each mesh node's origin to
   its bounding-box centre and adds child nodes under meshes that have children,
   so it is opt-in for static buildings that nothing rotates or looks up by name.
   UVs always stay float; the tiled metric UVs run far outside 0-1.

Every GLB is also **verified after encoding**: the output is decoded again and
each mesh's world-space bounds must match the original within 4 mm, otherwise
the build fails rather than shipping a moved mesh. (Extreme vertices land
exactly on the quantiser's grid, so this guards structure and transforms, not
interior precision, which the bit depth bounds by construction.)

Names are never touched: node names, material names and every extension the
runtime reads survive, and no materials are merged (the runtime keys behaviour
on material names such as `MAT_NT_Glass_PLACEHOLDER`).

**Loose images** under `assets/textures/` are recompressed in their own format
(same paths and extensions, so no loader changes): PNG losslessly, JPEG once at
quality 88 with full chroma. PNGs with real transparency are left alone,
because re-encoding zeroes the colour under transparent pixels and filtering
then bleeds dark halos into decal edges.

**Title art** ships as `zealot-loading-screen.webp` (749 KB) instead of the
3.3 MB PNG, which stays in the repo as the source. Only the used file is in the
manifest; the other title PNGs were dead weight.

## Running it

`basisu` is needed for the full effect:

```sh
brew install basis_universal      # or set BASISU_PATH=/path/to/basisu
```

Without it the optimiser still runs, but stores resized WebP instead of KTX2 and
says so in the log. That is what CI does (`npm ci` cannot install `basisu`), so
**deploy from a machine that has it**: `npm run build`, then `wrangler deploy`.
If the build log opens with `! basisu not found`, the output is WebP, not KTX2.

| Command / variable | Effect |
| --- | --- |
| `npm run assets:prepare` | Production manifest, optimised (used by `npm run build`) |
| `npm run assets:prepare:dev` | Development manifest, optimised (used by `npm run dev`) |
| `ZEALOT_OPTIMIZE_ASSETS=0` | Copy the authored files unchanged, for quick iteration or an A/B baseline |
| `ZEALOT_RUNTIME_OUTPUT=.runtime-public-x` | Build into another directory; `vite` reads the same variable, so a second asset set can be served beside the default without touching it |
| `node scripts/optimizeRuntimeAssets.mjs <srcRoot> <outRoot>` | Optimise the `.glb` files under `<outRoot>` from `<srcRoot>` |

Results are cached by content hash in `.cache/asset-optimizer/` (gitignored).
The **first run on a fresh clone encodes every texture and takes 20-25 minutes**;
after that only files that changed are redone, and an unchanged tree takes about
20 seconds. Set `ZEALOT_OPTIMIZE_ASSETS=0` if you only need the game running.

Tuning lives in `DEFAULT_OPTIONS` in `scripts/lib/glbOptimizer.mjs`. If a
surface looks soft up close, raise `targetTexelsPerMetre` (each doubling
quadruples that texture's memory). Bump `OPTIMIZER_REVISION` in the same file
when you change behaviour so cached results are rebuilt.

## Runtime side

- `src/world/gltfLoader.ts` is the one `GLTFLoader` for the game, with the KTX2
  and Meshopt decoders. KTX2 needs to know which formats the GPU supports before
  a renderer exists, so it asks a throwaway WebGL2 context (three.js's own
  `detectSupport` logic, including its Linux driver workaround). The transcoder
  is served from `/basis/`, copied by the optimiser.
- `src/world/dequantizeGeometry.ts` turns quantised or interleaved attributes
  back into plain Float32 after load. `mergeStaticModelMeshes` bakes each mesh's
  world matrix into its vertices, which truncates integer arrays, and skips
  interleaved attributes entirely (which is why an early version left 590 meshes
  unmerged). Models that were not quantised are untouched by this.
- `public/_headers` gives Cloudflare sensible cache headers. Without it every
  visit made about 140 revalidation round trips (`max-age=0, must-revalidate`).

## Adding a model

Nothing special: export it, add it to `config/runtime-assets.json`, and the next
prepare optimises it. Author to the density above and don't bother with
2048² maps for tiled surfaces; they are shrunk anyway. Do not add a file to
`quantizePositions` unless its nodes are static and nothing in `src/` looks up
its mesh nodes by name or rotates them.
