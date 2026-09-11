# Zealot of Harperhay

Zealot of Harperhay is a desktop-first, browser-based 3D artwork and exploration game. It is set across a fictional city block informed by North-West England and uses a deliberately early-3D, Dreamcast-era visual language.

## Status

The project is at the environment-bootstrap stage. The current application contains only a minimal Three.js scene used to verify the rendering and build toolchain; gameplay has not been implemented.

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

## Production build

Create a production build:

```sh
npm run build
```

The static production files are written to `dist/`. The build uses `/zealot-of-harperhay/` as its public base path so it can be deployed beneath that path on the existing website.

To inspect a production build locally:

```sh
npm run preview
```

## Project assets

Runtime-ready assets belong in `public/assets/`. Editable Blender masters belong in `blender/source/`, references in `references/`, and development renders in `renders/`. The latter three directories are not copied into the production build.

Asset-specific files use a stable lowercase slug such as `mcr1`:

- Immutable source photography: `references/architecture/<asset-slug>/`
- Reproducible Blender builders: `blender/scripts/create<Name>.py`
- Editable masters: `blender/source/harperhay-<asset-slug>[-stage].blend`
- Review renders: `renders/<asset-slug>/`
- Runtime exports: `public/assets/models/harperhay-<asset-slug>[-stage].glb`
- Source and output manifests: `docs/assets/<asset-slug>.md`

Keep reference photography and review renders outside `public/`; only files required by the shipped application belong there. Avoid spaces and case-only distinctions in new asset directory names so paths remain portable across macOS, Linux, CI and web hosting.
