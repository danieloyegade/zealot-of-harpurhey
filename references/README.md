# Reference library

This directory contains development-only source material. Nothing here is
served by the game build.

## Layout

- `architecture/<asset-slug>/` — immutable building and prop source images
- `screenshots/V<n>/` — captured game review sets, grouped by review version
- `world/` — city maps and global visual-direction references

New directory names use lowercase kebab-case without spaces. Keep original
camera filenames when they carry useful shoot ordering or metadata. Describe an
asset's reference roles and historical caveats in `docs/assets/<asset-slug>.md`.

Do not overwrite source photography with crops or retouched versions. Store
derived texture inputs beneath `blender/source/textures/<asset-slug>/` and ship
only runtime-required derivatives beneath `public/assets/`.
