# Zealot Road Atlas

Roads get their realism from surface information, not geometry. The target is not "high-resolution asphalt" but *this particular road has been dug up by the council six times in twenty years*: accumulated patches, paint, drainage, grime, repairs and weather.

## Layers

```text
ROAD PLANES (merged, world-space UVs)            src/world/createRoadSurfaces.ts
│
├── tiled asphalt scan, 2.1 m tile              photo/clean-asphalt-{albedo,roughness,normal}.jpg
├── large-scale colour variation                road-variation.png, sampled in world space
│
DECAL MESH (merged, drawn in layer order)
├── 0 repairs         patch-rect-a/b, patch-irregular-a/b, trench
├── 1 depressions     pothole-fill-a/b
├── 2 cracks, seams   crack-web, crack-long, tar-seam, oil-stain
├── 3 paint           line-white-a/b, line-yellow, zebra-stripe-a/b
├── 4 tyre            tyre-stain
├── 5 gutter          gutter-grime-a/b, gutter-litter
└── 6 wet             wet-patch-a/b
│
IRONWORK (instanced)  gully grates at the kerb, utility covers in the lanes
```

The whole network is three draw calls: road planes, decals and ironwork. The decals share one 1024 px atlas made of albedo+alpha, roughness (G) and a tangent-space normal map. They sit 8 mm above the asphalt, with polygon offset and no depth write.

## What goes where

Placement is deterministic, seeded from each road's name. Inputs live in `addRoadAndPavementLayout` in `src/world/createWorld.ts`:

- **Roads** (`ROADS`): each rectangle gets repairs at roughly one per 9 m, an optional tar-sealed centre joint, and one or two utility covers on roads over 40 m. It also gets wheel-path staining on four tracks and gutter grime and litter along both kerbs. Gully grates go every 20–28 m, each with its own staining and often standing water. Connections are marked `centreLine: false`.
- **Junctions:** kerb grime, gullies and centre lines stop where another carriageway crosses.
- **Centre lines:** 4 m dashes with 5 m gaps. About 7% are missing. Dashes are cut short by junctions, crossings and full-width trenches, which were reinstated without repainting.
- **Crossings:** the authored five-bar layout, drawn as worn paint.
- **Kerb lines:** authored double-yellow runs (Dreams, South Road frontage).
- **Repair clusters:** stretches dug up far more often than the rest. There are currently three: North Road outside the detail view, the Dreams frontage, and South Road.
- **Wetness is local, never a global "wet road" mode.** It collects in gutters, at gullies and drains, in potholes and patch edges, and near streetlights. Dry asphalt roughness is about 0.7–0.9 and wet decals about 0.15–0.5. None of it is a mirror.

## Pavements

Pavements use the same model in `src/world/createPavementSurfaces.ts`. Shared machinery (texture loading, seeded placement, interval clipping, merged decal meshes) lives in `src/world/surfaceDecals.ts`.

```text
PAVEMENT PLANES (merged)   600 mm concrete flags in half bond      pavement-{albedo,roughness,normal}.png
│                          rows count from the kerb; the shader rebuilds the flag grid to give every
│                          flag its own tone and roughness, and ~6% read as newer replacement flags
DECAL MESH
├── 0 repairs        tarmac-patch-a (lifted flags, footway service trench), tarmac-patch-b (infill, lamp collars)
├── 1 flags          cracked-flag-a/b, snapped to whole flags
├── 2 paving units   kerb-stone along carriageway edges, tactile-red at controlled crossings
├── 3 stains         gum-scatter, gum-old, stain-spill, bin-stain
├── 4 edges          wall-base on building lines, verge-edge on park sides, moss-lichen
├── 5 litter         leaf-litter, tyre-scuff (cars parked half on the kerb)
└── 6 wet            sunken-flag-wet (whole flags), damp-patch
IRONWORK             stopcock and BT covers set into flags, batched with the road gullies
```

Inputs are `PAVEMENTS` in `createWorld.ts`:

- **Kerb edge:** detected automatically wherever a pavement edge lies within 0.3 m of a road. Flag rows and kerb stones run from that edge.
- **`back`:** what the other edge meets. `wall` gets wall-base grime, bins, parking scuffs, covers and dense gum. `verge` gets soil creep, more moss and leaves.
- **`damp`:** raises the rate of cracked and sunken flags and damp patches.
- **Hotspots:** bus stops and every building entrance from `WORLD_LOCATIONS` gather gum and spills. Lamp posts sit in tarmac collars with damp around them.
- **Tactile paving:** red blister paving sits at both ends of each zebra crossing.

**Heights:** pavements sit at 12 mm, above road decals, with 0.5 mm steps so overlapping corners don't z-fight. Pavement decals are 4 mm higher again. Everything stays below the player's contact shadow at 25 mm.

## Photo-scanned stand-ins

The base surfaces now use photo scans from [Poly Haven](https://polyhaven.com) (CC0, no attribution required; authors credited here anyway). They stand in until Daniel's own surface photographs exist. They are 1k JPGs (colour, roughness, OpenGL normal) in `public/assets/textures/photo/`, downloaded unmodified.

| Surface | Scan | Authors | Covers | Used by |
| --- | --- | --- | --- | --- |
| Road asphalt, park paths | `clean_asphalt` | Dimitrios Savva | 2.1 m | `createRoadSurfaces.ts`, `createParkSurfaces.ts` |
| Pavement flag faces | `concrete_floor_worn_001` | Dimitrios Savva, Rico Cilliers | 3 m | `createPavementSurfaces.ts` |
| Park grass | `leafy_grass` | Charlotte Baglioni | 2 m | `createParkSurfaces.ts` |
| Worn grass, trodden path margins | `sparse_grass` | Amal Kumar | 2 m | `createParkSurfaces.ts` |

How each one is fitted into the existing layers:

- **Asphalt:** the scan replaces `road-asphalt-*.png`, now a 2.1 m tile. It is darkened to 0.55 linear to match the value the decals were tuned against. Roughness is lifted from the scan's 0.66 to about 0.8. A second, rotated sample fades in over the mid-scale drift, so the tile never lines up.
- **Pavement:** the flags keep the generated 600 mm grid, joints, arrises and chips, because decals snap to it. Each flag face reads its own offset into the concrete scan, because every flag is a separate casting. The generated tile only modulates the scan, and the per-flag tone contrast is softened.
- **Grass:** `createParkSurfaces.ts` replaces the blocky `grass-damp-overhaul` tile with world-projected UVs.
  - The scan gets a second rotated sample and is tinted from sunlit autumn lawn toward damp green.
  - `sparse_grass` shows through as bald patches from the world drift, and as a ragged, trodden margin up to about 0.8 m beside every path.
  - The grass now reaches the park pavements, closing the old bare-ground strip.

The generated `road-asphalt-*.png` files and `generateRoadTextures.mjs` are left in place, so reverting a surface is a one-line path change. When Daniel's photographs replace a scan, keep the tile size constant, the tone gain and the roughness remap next to the loader, and recalibrate them.

## Replacing procedural cells with photographs

Every texture is currently a procedural stand-in produced by `scripts/generateRoadTextures.mjs`. The atlas layout in `src/rendering/roadDecalAtlas.json` is the contract between the generator and the runtime. A cell can be redrawn from a photograph without touching placement code, provided it keeps its rectangle and orientation:

- square cells are free to rotate;
- in strip cells, **u runs along the length**;
- in kerb-side strips (`gutter-*`), **v = 0 is the kerb edge**;
- transparent texels should carry the cell's average colour, which avoids dark mip fringes on paint.

There is no automated photo-to-atlas step yet. For now, either replace a cell's painter in the generator so it samples a prepared image, or paint the photograph straight into the atlas PNGs at the cell rectangle and stop regenerating that cell. The base tile needs a flat, seamless 512 px photographic crop covering about 4 × 4 m.

## Shot list

Photograph boring roads. Point the camera straight down and shoot flat, evenly exposed frames, ideally overcast or in open shade. A phone is more useful here than the Mamiya. Include something for scale.

- **Asphalt:** fresh, old, coarse, smooth, faded
- **Repairs:** rectangular patch, trench, crack, pothole, tar line
- **Markings:** white line, yellow line, arrows, disabled bays, bus markings, faded paint
- **Infrastructure:** manholes, drains, utility and inspection covers
- **Dirt:** oil, tyre marks, chewing gum, leaves, mud, gutter grime
- **Wet:** small puddles, damp patches, reflections

Keep originals outside `public/`, as with the other reference photography, and commit only the derived runtime atlas.

Pavement shots worth adding: flags (clean, stained, cracked), tarmac reinstatements in flags, kerb tops, tactile paving, gum, bin stains, wall bases, moss and lichen, leaf drifts.

## Regenerate

```bash
node scripts/generateRoadTextures.mjs
```

```bash
node scripts/generatePavementTextures.mjs
```

Both use the shared helpers in `scripts/lib/textureTools.mjs`. Road output was byte-identical before and after that extraction.
