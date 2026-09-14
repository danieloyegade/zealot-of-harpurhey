# CC0 texture library

Staging library of free photo-scanned materials, downloaded 2026-09-14. Everything here is **CC0** (public domain, no attribution required; authors credited anyway). Nothing here is wired into the game yet.

It lives outside `public/` on purpose: Vite copies all of `public/` into the build, so unused textures would ship. When a texture is used:

- **Runtime surface:** downscale to the `docs/VISUAL_LANGUAGE.md` budget (256–512 px) into `public/assets/textures/photo/`, and add it to the credit table in `docs/ROAD_ATLAS.md` or the relevant asset doc.
- **Blender asset** (garments, shutters, props): reference it from the `.blend`, and bake or downscale into the GLB.

All maps are 1k JPG. Normals are OpenGL convention (+Y), which matches Three.js and Blender. Filenames follow the `-albedo/-normal/-roughness/-ao` convention in `docs/TECHNICAL.md`, plus `-opacity` for decals.

## Façades and street surfaces

| Folder | Source asset | Authors | Scan covers | Intended use |
| --- | --- | --- | --- | --- |
| `brick-sooty-dark-weathered` | Poly Haven `brick_wall_10` | Dimitrios Savva | 1.9 m | Victorian terraces, soot-darkened backstreets |
| `brick-red-common` | Poly Haven `red_bricks_04` | Rob Tuytel | 2.5 m | Generic red-brick blockout buildings |
| `brick-mixed-patched` | Poly Haven `mixed_brick_wall` | Dimitrios Savva | 1.7 m | Repaired/reclaimed walls, alleys, side returns |
| `brick-painted-black-worn` | ambientCG `PaintedBricks005` | ambientCG | — | Painted shopfront bases and stall risers |
| `render-grey-rough` | Poly Haven `rough_plaster_brick_04` | Rob Tuytel | 2 m | Grey render, upper storeys, gable ends |
| `shutter-rusted-blue` | Poly Haven `rusted_shutter` | Dimitrios Savva | 1.8 m | Roller shutters (replaces `shutter-grimy-overhaul`) |
| `shutter-painted-grey` | Poly Haven `painted_metal_shutter` | Dario Barresi, Rico Cilliers, Charlotte Baglioni | 2 m | Roller shutters, cleaner variant |
| `corrugated-iron-galvanised` | Poly Haven `corrugated_iron_02` | Jenelle van Heerden, Sergej Majboroda | 2.7 m | Hoardings, sheds, fences, bus-depot backs |
| `metal-painted-rusty` | Poly Haven `rusty_metal_02` | Rob Tuytel | 1 m | Bins, bollards, utility boxes, signage backs |
| `asphalt-cracked` | Poly Haven `asphalt_02` | Rob Tuytel | 3 m | Car park (the last low-res ground tile) |
| `bark-plane-tree` | Poly Haven `bark_platanus` | Dimitrios Savva | 1.5 m | London plane street and park trees |
| `decal-leak-streaks-wide` | ambientCG `Leaking004` | ambientCG | — | Streaking under sills, gutters and parapets |
| `decal-leak-streak-narrow` | ambientCG `Leaking006` | ambientCG | — | Single drainpipe/overflow stain |

## Garment fabrics (fashion pipeline)

Fabric scans cover about 0.26 m, so tile them densely on garment UVs.

| Folder | Source asset | Authors | Intended use |
| --- | --- | --- | --- |
| `denim-mid-blue` | ambientCG `Fabric069` | ambientCG | Player's oversized denim jacket |
| `denim-dark-worn` | Poly Haven `denim_fabric_06` | Greg Zaal, Rico Cilliers | Player's oversized jeans, NPC denim |
| `leather-black-scratched` | ambientCG `Leather032` | ambientCG | Player's black leather delivery bag |
| `wool-herringbone-grey` | Poly Haven `poly_wool_herringbone` | colormass, Rico Cilliers | Long coats, tailoring |
| `cotton-jersey` | Poly Haven `cotton_jersey` | colormass, Rico Cilliers | T-shirts, hoodies (tint albedo) |
| `knit-fleece-olive` | Poly Haven `knitted_fleece` | colormass, Rico Cilliers | Knits, jumpers |
| `corduroy-ribbed` | Poly Haven `ribbed_corduroy` | colormass, Rico Cilliers | Art-school trousers and jackets |

## Lighting

| File | Source asset | Authors | Intended use |
| --- | --- | --- | --- |
| `hdri-street-night/hdri-street-night-1k.hdr` | Poly Haven `cobblestone_street_night` | Greg Zaal, Jenelle van Heerden | Reflection-only environment map (PMREM) for PBR metals, leather, glass. Never the visible sky, which stays the cobalt dome. |
