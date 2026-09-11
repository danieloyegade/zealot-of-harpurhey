# Development renders

Review renders are grouped by stable asset or review-pass slug. They are
development evidence and are not copied into the Vite production build.

- Asset renders: `renders/<asset-slug>/`
- Cross-scene review passes: `renders/<review-pass>/`
- Numbered multi-view renders: `01-...`, `02-...`, and so on

Render-producing Blender scripts must create their destination directory and
write into the matching asset folder. Runtime images and textures belong in
`public/assets/`, not here.
