# Worn shipping pallets

## Asset status

Two production props, textured and exported, built from Daniel's pallet brief
(2026-09-14).

## In the game

Daniel asked for the pair "one stacked on the other, blue one on the ground,
outside Spice Cabin". `createWorld.ts` builds the stack in
`addSpiceCabinPallets`, and `addSpiceCabinPalletCollision` gives it one oriented
box collider (2.4 × 2.0 m, 0.6 m tall at the 2× scale, not blocking the camera). It is called
from the `spice-cabin` branch, anchored to that plot's layout so it moves with
the building.

- **Placement:** against the west gable, on the bare ground of the gap toward
  Vinyl Exchange, 0.15 m off the wall and 0.35 m behind the South Road building
  line. The long side runs along the wall.
- **Stacking:** the blue pallet stands on the ground. The brown sits on the
  blue deck at +0.146 m × scale, pushed toward the wall and turned 0.06 rad, so
  one end overhangs.
- **Ground height:** off the pavement, the world ground's top is at y −0.07,
  not 0. Placing the stack at 0 floated it 7 cm.
- **Draw order:** Spice Cabin stands at pavement height, so its transparent
  ground-contact decal spans the gap as a plane at y 0.022, 9 cm above that
  ground. It would composite floor grime over the stack's lower boards. The
  pallet meshes are therefore drawn as fully opaque transparent-queue draws
  (`transparent`, `depthWrite`, render order 2), after the decal's order 1, so
  they overwrite it.
- **Scale:** Daniel asked for the pallets 4× bigger, then half that
  (`PALLET_STACK_SCALE` = 2), applied at runtime; the GLBs stay at real-world
  scale. Each pallet is 2.4 m long and 0.3 m tall, the stack 0.6 m, spanning
  about X 5.55–7.55 and Z 51.25–53.65. The wall gap and setback stay absolute.
- **Materials:** `applyPalletTexturePolicy` in `busShelterMaterials.ts` gives
  them the shared photographic texture filtering and night-street environment.
- **Shadows:** the game's moonlight casts no shadows, so the viewer's
  shadow-bias note doesn't apply yet.
- **Dev view:** `?view=spice-cabin-pallets`.

Three more identical blue-under-brown stacks are distributed around the map:

- against the Florist's east service wall at (-12.8, -35), on bare ground;
- in the gap north of Coral at (-38.5, 4.35), on bare service ground;
- along the Arts Council edge of the car park at (48, -3.4), on the asphalt slab.

They are declared in `PALLET_STACKS` in `worldLayout.ts`, reuse one loaded pair
of GLB templates so geometry and textures stay shared, and each receives the
same 2.4 × 2.0 × 0.6 m collision footprint. Review them with
`?view=pallets-north`, `?view=pallets-west`, and `?view=pallets-east`.

| Runtime GLB | Footprint | Top boards | Material |
| --- | --- | --- | --- |
| `public/assets/models/pallets/pallet_worn_brown.glb` | 1200 × 800 mm (EUR-style) | 5 | `MAT_Pallet_WornBrown` |
| `public/assets/models/pallets/pallet_worn_blue.glb` | 1200 × 1000 mm (block pallet) | 7 | `MAT_Pallet_WornBlue` |

The blue pallet is 7,838 triangles and the brown 6,026, inside the brief's
3,000–8,000 target. The nail heads account for about 1,000 of each.

The brief suggested 1200 × 800 mm as a starting point but made the references
authoritative. The blue photographs show 1200 × 1000 block pallets with seven
top boards, so the blue pallet follows them. The brown pallet keeps the brief's
footprint. Both pallets stand about 150 mm tall.

Filenames use the brief's underscore spelling rather than the kebab-case in
`TECHNICAL.md`. Other assets already do this (`cass_art.glb`, `real_camera.glb`).

## Source

- Brief: `references/architecture/infrastructure:objects/pallet/pallet.txt`
- Photographs: the five images in the same folder. `createPallets.py` does not
  read them. Paint and timber colours were sampled from them once by luminance
  quartile, and those sRGB values are recorded as constants in
  `palletWeathering.py`.

## Scripts

- `blender/scripts/palletGeometry.py` builds the construction, the damage and
  the nails.
- `blender/scripts/palletWeathering.py` authors timber, paint, wear and grime
  from the baked buffers.
- `blender/scripts/createPallets.py` handles the unwrap, bake, maps, material,
  `.blend` save, GLB export, reimport validation and review renders.
- `blender/scripts/surfaceWeathering.py` is the shared toolkit, reused
  unchanged from the bus shelter texture pass.

Rebuild both from the repository root. A cold bake takes about five minutes per
pallet, and weathering takes two to five more:

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python blender/scripts/createPallets.py
```

The script also takes these arguments:

- `-- --only blue` or `-- --only brown` builds one variant.
- `--stage textures`, `--stage validate` or `--stage renders` runs one stage.
- `--bake-cache DIR` reuses baked buffers while you iterate on weathering. The
  cache is valid only while geometry and UVs are unchanged, so delete it after
  any change to `palletGeometry.py`.

## Outputs

- Editable masters:
  - `blender/source/pallets/pallet_worn_brown.blend`
  - `blender/source/pallets/pallet_worn_blue.blend`

  Each contains the joined export mesh plus an excluded `-components`
  collection that keeps every board, block and the nail mesh as separate
  objects.
- Texture sources: `blender/source/textures/pallets/pallet-worn-{brown,blue}-{basecolor,orm,normal}.png`,
  all 2048².
- Review renders:
  - `renders/pallets/{brown,blue}-01-upper-three-quarter.png`
  - `renders/pallets/{brown,blue}-02-lower-three-quarter.png`
  - `renders/pallets/{brown,blue}-03-closeup-corner.png`
- Reimport reports: `renders/pallets/{brown,blue}-validation.json`

## Construction

The geometry follows real pallet construction, with separate parts:

- **Top boards:** 22 mm thick, running along X.
- **Cross boards:** three boards, 145 mm wide, running along Y over the block
  lines.
- **Blocks:** nine blocks, 78 mm tall.
- **Bottom boards:** three boards running along X, 100/145/100 mm wide.

Fork openings are on all four sides.

Every part has its own seeded variation:

- a ten-vertex chamfered profile with 0.8–2.6 mm worn arrises;
- bow, sweep, twist and cup of a millimetre or two;
- a skewed saw cut at each end;
- crushed corners and inserted edge chips.

Some top boards also have a splintered, jagged end: one on the brown pallet,
two on the blue. The blocks carry fork chips on their lower edges.

Blocks keep the faces the boards cover. With those faces deleted, a chipped or
crushed block corner opened onto the hollow inside of the block, which showed up
in the first review renders.

Nail heads are hexagonal and cost 18 triangles each. They are ray-cast onto the
deformed boards, so none float:

- two or three nails per top board over each cross board;
- nails driven up through the bottom boards;
- about 4% work proud and tilted (deck nails only);
- about 5% have fallen out, leaving an open hole in the texture.

Every edge sharper than 35° is split.

## Material pipeline

1. `unwrap_atlas` gives every part one non-overlapping, density-consistent
   atlas. Top boards get 15% more texel density, bottom boards 15% less.
   Texel density is about 1.1–1.3 mm.
2. `bake_buffers` bakes world position, world normal, part ID, AO and
   convexity, with a temporary ground plane for contact occlusion.
3. Each texel is transformed back into its own part's local frame. Wood grain
   is therefore computed per board, so it follows each board's length no
   matter how the UV islands were rotated, and never crosses from one piece of
   timber into another. The grain includes:
   - growth rings around a pith line outside the plank, with arcs showing on
     the end grain;
   - knots;
   - fibre, pores and patches of band-saw marks.

   Each part has its own seed and tone.
4. Wear is placed by cause:
   - **Stacking:** abrasion on the deck directly over the blocks, where the
     next pallet in a stack bears down. This produces the pale bands across
     the boards seen in the garden and driveway photographs.
   - **Knocks:** collisions at corners, and chips concentrated on edges.
   - **Forks:** gouges along the outward lower faces.
   - **Weather:** sun and rain exposure on the deck, water stains and tide
     marks.
   - **Grime:** handling dirt, recess grime from AO, splash rising from the
     ground, mud on the ground-contact faces, black mould specks where the
     pallet stays damp.
   - **Nails:** iron-tannin staining around each nail, spreading along the
     grain.
5. The output is glTF ORM (occlusion, roughness, metallic), a sRGB base colour
   and an OpenGL tangent-space normal map from the height channel. They are
   exported as WebP inside the GLB (`EXT_texture_webp`), matching the bus
   shelter. There is one material and one mesh per pallet, so each pallet is
   one draw call.

**Brown timber** is greyed by exposure and silvered on the deck. It keeps
warmer brown on protected faces and darkens at the end grain, with a
water-wicking soak near board ends. Paler raw timber shows at recent knocks.
One top board is a replacement: paler and barely weathered.

**Blue paint** follows the brief's order: paint, then abrasion, then exposed
wood, then dirt.

- Deep blue survives on protected and lower faces.
- The deck fades to a chalky blue.
- On the deck, paint breaks along latewood ridges and fibre streaks, leaving
  blue caught along the grain.
- Exposed timber carries blue soaked into the earlywood.
- Thin paint lets the timber tone through.
- Painted nail heads lose their paint where stacking has rubbed them.

**Roughness:**

- Brown timber is mostly 0.86–0.95, with compressed stacking areas nearer 0.8
  and end grain at 0.96.
- Blue paint is 0.72–0.84, rubbed paint is smoother, and bare wood is about
  0.9.
- Nail heads run from 0.48 (bare steel, metallic) to 0.85 (rust).

There is no broad sheen.

## Transforms and orientation

- Units are metres. Blender is Z-up, and the GLB is converted to Y-up.
- The origin is at ground level, centred on the footprint, and the lowest
  vertex is exactly at Z = 0.
- Transforms are applied. The exported node has zero location, zero rotation
  and scale 1.
- The long side runs along Blender X (glTF X). The front long face, with its
  two fork openings, faces Blender −Y, which is glTF +Z.

## Validation

`--stage validate` reimports each GLB into an empty scene and writes the
`*-validation.json` reports. It checks:

- object list (a single mesh; no cameras or lights);
- dimensions, minimum Z and XY centre;
- transforms and triangle count;
- UV layers;
- loose vertices, degenerate faces and zero normals;
- material name;
- embedded 2048² base colour, ORM and normal maps;
- textured roughness and metallic;
- normal strength.

The GLBs were also loaded with Three.js r185 `GLTFLoader` in a throwaway
browser page:

- Each loads as one mesh with one `MeshStandardMaterial`.
- Base colour, roughness, metalness, AO and normal maps are all present at
  2048², with the glTF-standard normal scale `[1, -1]`.
- WebP arrives through `EXT_texture_webp`.
- Sizes are correct in Y-up, and each pallet rests at Y = 0.
- There are no cameras or lights, and no console errors.

A directional shadow without bias drew acne moiré across the thin deck boards
at grazing light. `shadow.bias = -0.0004` with `normalBias = 0.01` cleared it,
so apply similar bias to any light that shadows these pallets in the game.

## Known limitations

- A few fork chips on block lower edges are stepped rather than ragged. The
  profile has only ten vertices, so a deep chip reads as a notch at close
  range.
- The brown pallet's growth-ring figure is procedural. At extreme close range
  a knot's swirl can still look slightly drawn.
- No stencil marks, barcodes or pool-operator branding. The blue references
  carry trade marks, which are deliberately left out.

## Texture memory

Each pallet carries three 2048² maps, about 64 MB of GPU memory with
mipmaps if uploaded uncompressed. Two pallet types cost about 128 MB, shared
by every instance that clones the same loaded model.

If pallets become common set dressing, the options are:

- ship a 1024² runtime derivative under the LOW/MEDIUM quality profiles;
- move to KTX2 textures.

Either choice belongs in `visualStyle.ts`'s texture policy rather than in these
masters.
