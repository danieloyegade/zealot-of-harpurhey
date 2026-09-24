# Zealot of Harpurhey

Zealot of Harpurhey is a desktop-first, browser-based Three.js exploration game and artwork. Its fictional-collage Manchester is shaped by Daniel Oyegade's photography and filmmaking, especially *The Spectres Are All Around Us*: municipal architecture, streetlight pools, surveillance distance and deadpan attention to ordinary objects. The current visual target is uncanny realism suspended between the photographic and the obviously constructed.

## Status

The project is a substantial playable prototype. It currently includes:

- third-person walking, running, camera orbit/recentring and collision
- rideable Sterling bikes with docking, assist and boost
- quality profiles, fixed-step simulation, authored night lighting and development diagnostics
- an explorable city of finished hero locations, geometry passes and explicit placeholders
- a complete first delivery: collect flowers at Nice Things, carry them to Vinyl Exchange and receive the £3.70 fee

World production remains ahead of gameplay breadth. NPC and photography systems are still future work, and many named locations remain geometry-first rather than finished assets. See `docs/WORLD_LAYOUT.md`, `docs/GAMEPLAY.md` and `SYNC.md` for the live state.

## Prerequisites

- Node.js 20.19 or later (Node.js 22.12 or later is also supported)
- npm 10 or later

## Development

Install dependencies:

```sh
npm install
```

Start the local development server:

```sh
npm run dev
```

Vite will print the local URL to open in a desktop browser.

Core controls are WASD/arrow keys to move, Shift or Space to run on foot, pointer drag to orbit, C to recenter the camera, and E for the current contextual action. On a bike, W pedals, Shift assists, Space boosts, A/D steer and S brakes.

## Production build

Create a production build:

```sh
npm run build
```

The static production files are written to `dist/`. The build is rooted at `/` and deploys to its own Cloudflare Worker (`zealot-of-harpurhey`), embedded on danieloye.com via an iframe rather than being served as a literal subpath of that site. Before Vite runs, `config/runtime-assets.json` generates a clean production-only public directory; workshop assets and uncleared audio are not copied. That copy is also optimised (textures right-sized and GPU-compressed, geometry compressed); see `docs/ASSET_PIPELINE.md`. Deploy from a machine with `basisu` installed (`brew install basis_universal`), and note the first build on a fresh clone takes 20-25 minutes to encode textures (`ZEALOT_OPTIMIZE_ASSETS=0` skips it).

To inspect a production build locally:

```sh
npm run preview
```

Run the full local/CI safety net with:

```sh
npm run check
```

This runs the state/contract tests, validates the runtime asset boundary and rights register, type-checks the application, and produces a production build.

## Project assets

Runtime candidates belong in `public/assets/`. Editable Blender masters belong in `blender/source/`, references in `references/`, and development renders in `renders/`. A file being under `public/` no longer means it ships: production inclusion is explicit in `config/runtime-assets.json`. Audio also needs approval in `config/asset-rights.json`; the current recordings are development-only until their rights are confirmed.

Asset-specific files use a stable lowercase slug such as `mcr1`:

- Immutable source photography: `references/architecture/<asset-slug>/`
- Reproducible Blender builders: `blender/scripts/create<Name>.py`
- Editable masters: `blender/source/harpurhey-<asset-slug>[-stage].blend`
- Review renders: `renders/<asset-slug>/`
- Runtime exports: `public/assets/models/harpurhey-<asset-slug>[-stage].glb`
- Source and output manifests: `docs/assets/<asset-slug>.md`

Keep reference photography and review renders outside `public/`; only files required by the shipped application belong there. Avoid spaces and case-only distinctions in new asset directory names so paths remain portable across macOS, Linux, CI and web hosting.

See `docs/ASSET_RIGHTS.md` before adding music, field recordings, photography, fonts or third-party models.
