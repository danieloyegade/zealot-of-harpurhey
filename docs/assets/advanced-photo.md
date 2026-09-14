# Advanced Photo, St Ann's Arcade

This is the first-pass, geometry-only reconstruction of Advanced Photo from
the six photographs and production brief in
`references/architecture/advanced-photo/`. It is intentionally stopped at the
review hold in `03_Advanced_Photo.txt` section 23. No signage, logos, posters,
packaging, products, photographic textures, decals, weathering, or final PBR
materials are present.

## Current deliverables

- Rebuild script: `blender/scripts/createAdvancedPhotoBlockout.py`
- Approval source: `blender/source/advanced_photo_blockout.blend`
- Runtime comparison export: `public/assets/models/advanced-photo-blockout.glb`
- Four required clay views: `renders/advanced-photo-blockout/`

Regenerate the blockout from the project root with:

```sh
/Applications/Blender.app/Contents/MacOS/Blender \
  --background \
  --python blender/scripts/createAdvancedPhotoBlockout.py
```

## Inferred architecture and scale

The estimated shop envelope is **5.80 m wide × 6.20 m deep × 3.55 m high**.
One Blender unit is one metre, Z is vertical, floor level is Z = 0, and the
main shopfront faces local -Y. These dimensions are photographic estimates,
not survey measurements.

The references establish a compact corner shop rather than a flat glass wall.
The narrow customer entrance and hero display occupy the main elevation; a
second display runs perpendicular to it along the arcade return on local +X.
The external panes sit in front of real shallow display volumes containing
cabinet frames and shelves. The door is held open in the photographed state
and built as an actual glazed frame, preserving a 1.10 m clear entrance.

Inside, the blockout provides a compact circulation route from the entrance to
the customer counter, a plausible staff zone behind it, one freestanding
interior cabinet, wall storage, and a simplified rear service partition. A
short L-shaped slice of arcade floor and ceiling, the immediate opposite wall,
and the circular ceiling fixture establish how the asset connects to St Ann's
Arcade without attempting to reconstruct the full passage.

## Review hold

The four renders correspond to the brief:

- View A: straight-on main display elevation
- View B: oblique arcade view with the circular ceiling fixture
- View C: player-eye view through the entrance toward the counter
- View D: interior/player-eye view back toward the shopfront

The approval questions are the overall 5.80 × 6.20 m footprint, entrance and
main-window rhythm, length of the side return, display-case depth, and the
counter/circulation arrangement.

Only after approval should the detailed geometry pass add layered black
mouldings, lower decorative panels, refined cabinet frames, entrance hardware,
ceiling structure, wall-display rails, and the specified gameplay and lighting
anchors. The final `advanced_photo.blend` and `advanced_photo.glb` do not yet
exist because the brief explicitly forbids proceeding automatically beyond
this review stage.

## Runtime notes

The comparison GLB contains the blockout architecture and arcade connector
context, including the ring fixture, but excludes review ground, cameras, and
lights. It replaces the old Advanced Photo box in `src/world/createWorld.ts`
at world shop-body centre `(12.1, 67.85)`, rotated 180 degrees so the authored
main frontage faces north. This keeps the old placeholder's north facade plane
at Z = 64.75 and keeps the shop's east wall attached to Eastern Bloc without
scaling the measured asset.

Runtime collision is split around the shell, fixed display cabinets, customer
counter and rear service partition. The open 1.10 m entrance and the route to
the counter remain traversable. The glass receives transparent runtime
treatment; the pale interior and circular arcade fixture receive restrained
emissive treatment plus two candidates in the existing nearest-hero-light
budget. The asset remains a geometry blockout and is not presented as final.
