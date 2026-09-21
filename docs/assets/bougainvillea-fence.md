# Bougainvillea fence scene

## Asset status

A set of production assets built from Daniel's brief and photograph on
2026-09-21, exported, validated and placed in the world.

## In the game

Daniel asked for the plant, fence, lamp and sign to stand between Coral and
Village Books. `src/world/bougainvilleaFence.ts` loads them, and
`createWorld.ts` calls it next to the pallet stacks. The positions are in
`BOUGAINVILLEA_FENCE_SCENE` in `worldLayout.ts`.

- **The gap:** measured from the loaded meshes, the ground is clear from
  Village Books' south wall (Z = 0.44) to Coral's north brick (Z = 5.75).
  Coral's concrete, which reaches Z = 3.9, is cornice above 6.3 m.
- **Scale:** Daniel asked for the fence, flowers and signpost 30% larger, so
  all three load at a runtime scale of 1.3 (`scale` in the layout constant).
  The GLBs stay at real-world size. In the game the fence is 2.34 m tall and
  the sign lamp stands 4.3 m up.
- **Fence:** it stands behind the Coral north pallet stack, which covers
  X −39.7 to −37.3, at X = −40.3. That is 6.3 m back from the X = −34
  building line. It is turned a quarter turn to face east toward the street.
  - The 4.68 m hero section starts at Village Books (centre Z = 2.78).
  - The extension follows it (centre Z = 6.29). Only 0.63 m of it shows
    before it runs into Coral's wall.
  - The flower mass is at the Village Books end.
- **Signpost:** at (−38.94, 2.3), 1.37 m in front of the fence, which is the
  scaled offset from the Blender scene. It moved north of the pallets, because
  the photo's position, south of the flower mass, falls inside the stack. The
  sign faces the street.
- **Sign lamp:** `addBougainvilleaSignLamp` registers a warm point light just
  under the lamp lens:
  - colour `0xffd6a0`, intensity 16, range 10 m;
  - location-relevance selection within 18 m, priority 1.1.

  It lights the flowers and fence from the front, and spills onto Village
  Books' side wall. The lens emission is raised 3× through
  `applyBougainvilleaTexturePolicy`, so the lamp reads as the source.
- **Ground height:** both use `palletGroundAt`. In the gap that is world ground
  (−0.07), the same as the pallets.
- **Materials:** `applyBougainvilleaTexturePolicy` in `busShelterMaterials.ts`
  gives them the shared photographic filtering and night-street environment,
  and treats the lamp lens as emissive.
- **Collision:** there are two solids, and neither blocks the camera:
  - a strip covering the fence and its dense growth across the whole gap
    (X −40.53 to −39.81, 2.6 m tall);
  - a circle of about 0.1 m for the signpost.
- **Not placed:** the background tree is 8 m wide and would cut through both
  buildings in the 5.3 m gap. The ground strip carries its own kerb and road,
  which would double the world's.
- **Viewing it:** there is no dedicated dev view yet. `?view=village-books`
  looks at the neighbouring shopfront, and the scene is at the left of that
  frame.

- Brief: `references/architecture/infrastructure:objects/plants/bougainvillea/17_Bougainvillea_Fence_Scene_Assets.txt`
- Photograph: `IMG_8966.jpg` in the same folder

| Runtime GLB | What it is | Triangles | Draws |
| --- | --- | --- | --- |
| `public/assets/models/bougainvillea/BGV_signpost_no_entry.glb` | Grey column with tapered base, No Entry sign on a yellow backing board, sign lamp | 1,784 | 7 |
| `public/assets/models/bougainvillea/BGV_fence_bougainvillea.glb` | 3.6 m hero closeboard fence with the climber | 80,862 | 6 |
| `public/assets/models/bougainvillea/BGV_fence_extension.glb` | 1.8 m plainer section that tiles beside it | 4,419 | 6 |
| `public/assets/models/bougainvillea/BGV_background_tree.glb` | Dark canopy that stands behind the gap | 7,861 | 3 |
| `public/assets/models/bougainvillea/BGV_ground_strip_optional.glb` | Kerb, tarmac, soil margin, weeds, fallen bracts | 4,721 | 3 |

The extension section was not in the brief's export list. The brief allowed
"one simpler extension section if useful", and it is what lets the fence run
past 3.6 m without repeating the hero.

## Rebuild

From the repository root:

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python blender/scripts/createBougainvilleaFence.py
```

- `-- --stage build`, `validate` or `renders` runs one stage.
- `--reuse-textures` loads maps already in `blender/source/textures/bougainvillea/`
  instead of authoring them again. Authoring takes about five minutes, mostly
  for the timber. Delete a map's PNGs to make it regenerate.

The scripts are:

- `blender/scripts/createBougainvilleaFence.py`: geometry, plant growth,
  materials, export, validation and renders.
- `blender/scripts/bougainvilleaTextures.py`: procedural albedo, ORM and
  height maps, all numpy. It reuses the noise helpers in `surfaceWeathering.py`.

Everything is seeded, so a rebuild comes out identical.

## Outputs

- **Blender source:** `blender/source/bougainvillea/bgv_fence_scene.blend` holds
  the assembled scene: all five roots in their own collections, plus a
  `BGV_validation` collection with the sun, streetlight, camera and stage
  ground. That collection is never exported.
- **Textures:** `blender/source/textures/bougainvillea/`.
- **Renders:** `renders/bougainvillea/`, views A to I from brief §23:
  1. A: assembled daylight
  2. B: straight-on fence
  3. C: timber and stems
  4. D: flower clusters
  5. E: signpost
  6. F: foliage shadow test
  7. G: tree silhouette
  8. H: night streetlight
  9. I: exploded assets
- **Reimport report:** `renders/bougainvillea/validation.json`.

## Origins and orientation

Units are metres. Blender is Z-up and the GLBs are Y-up. Each GLB has one
named root node (`BGV_*_ROOT`) with an identity transform, and its meshes are
children of that root.

- **Signpost:** the origin is at the ground centre of the column. The sign
  faces glTF +Z, which is the street.
- **Fence and extension:** the origin is at ground level on the fence centre
  line, the plane where the backs of the boards meet the rails. Boards face
  +Z. Rails and posts sit behind them. Posts stand 0.9 m in from each end of
  the hero and at the centre of the extension, so sections laid end to end
  keep a 1.8 m post rhythm with no doubled posts. Some leaves and flowers
  overhang the ends by a few centimetres. That overhang is deliberate,
  because the brief wants the plant to spill over neighbouring building
  edges.
- **Tree:** the origin is at the trunk base. The canopy reaches about 2.25 m
  toward +Z, so stand the tree at least 1.9 m behind the fence line. The
  validation scene uses 1.9 m, which keeps foliage clear of the boards below
  the fence top.
- **Ground strip:** the origin is on the fence line at pavement level, so the
  strip sits directly under a fence placed at the same origin. It runs 1.62 m
  toward the street. The road edge is at −0.11 m and the kerb is 150 mm wide.

In the assembled scene the signpost stands at (−1.35, 1.05) in glTF XZ, which
puts it on the pavement near the kerb, as in the photograph.

## How the climber is built

- **Stems:** 16 hand-placed primary canes come over the top of the fence from
  behind. The main arched mass sits upper-left of centre. Long canes run right
  and droop, and a few stems are traced flat against the timber. Side shoots
  branch from the canes every 9–20 cm, biased outward and pulled down by
  gravity. Stems are tubes with parallel-transported frames. Wherever they
  are not clearly behind the fence, they are kept in front of the boards.
- **Flowers:** there are eight cluster variants, with 5 to 18 flowers on a
  dome. Each flower is three cupped bracts. A bract is a 7-triangle card; its
  rounded outline comes from an alpha-cut texture (alphaTest 0.5), and each
  card is bent across its spine. There are 268 clusters. Placement follows a
  density field: dense upper-left, thinner to the right, a few low drips.
  Each flower picks one of four tones (sunlit pale pink, mid pink, deep
  magenta, crimson), weighted by how exposed its cluster is.
- **Leaves:** four sprig variants: single, trifoliate, five-leaflet and
  opposite pair. Each leaflet is folded and has four triangles. Sprigs grow
  along stems, skipping one or two bare stretches per cane, and gather around
  clusters.
- **Pressing:** any leaf or bract vertex that would pass through the boards is
  pressed flat onto their face instead.
- **Batching:** every variant is instanced at build time with its own
  transform and tone, then each fence module is joined into one mesh per
  material. The game's `mergeStaticModelMeshes` would batch it this way
  anyway, so a fence module costs six draws.

All leaf and flower shadows come from geometry. Nothing is baked into the
timber.

## Materials

The asset set uses the brief's material list, with one addition:
`MAT_lamp_lens` carries a small warm emission, so the sign lamp reads as lit
at night.

- **Timber:** a 1024 × 2048 atlas of eight 100 mm board variants. Each has
  grain that bows around its knots, some surface checking, rain drips, algae
  and soil splash at the foot, bleaching toward the top, and dark edges.
  Boards pick a column, flip and height offset at random. Roughness is
  0.78–0.97, with a normal map.
- **Sign face:** the sign's own colours, not the photo's overexposed wash.
  The white bar and border sit on a red roundel on a yellow backing board,
  with light edge grime. Roughness is 0.22–0.8.
- **Pole:** grey paint unwrapped around the shaft. It carries the small
  yellow asset tag and the torn, taped paper remnant from the photograph.
- **Tree foliage:** alpha-cut sprig cards in four tones, from sunlit to near
  black. Cards deep inside the canopy take the darkest tile, which gives the
  photo's dark recesses without any baked lighting.

## Known limitations

- **Budget:** the hero fence is about 81k triangles, 56k of them bracts. It is
  priced as a hero piece, but it is heavy next to the rest of the world; a
  Spice Cabin view is ~730k triangles in total.
- **No LODs:** the brief's LOD1 and LOD2 were not built, because the engine
  has no distance/LOD switching yet (see `docs/PERFORMANCE.md`). If the fence
  is ever placed where it is seen from far away, a LOD1 that halves the
  clusters is the first thing to add.
- **Leaf translucency:** there is none. Leaves are double-sided opaque, which
  keeps rendering stable.
- **No nails:** no nail or screw heads on the boards. At gameplay distance
  they would not read.
- **Bract self-shadow:** in close-ups, cupped bracts shadow their own centres,
  which can read as a dark stain.
- **Tree cards:** from directly side-on, a few edge cards show as flat
  sheets.
- **Rail UVs:** the rails' v coordinate runs past 1, so they repeat the
  board columns. They are hidden behind the boards.
