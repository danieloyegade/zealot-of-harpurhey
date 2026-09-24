# Greek Gyros, Deansgate

A metric reconstruction of the Greek Gyros / Greek Grill House
food kiosk on Deansgate, inferred from the photographs in
`references/architecture/infrastructure:objects/gyros/` (daytime
three-quarter, night frontage, and
`IMG_8918.HEIC`) and the brief in
`references/architecture/infrastructure:objects/gyros/15_Greek_Gyros.txt`.

It is a small environmental prop rather than a hero building, but it is
modelled to the real stand, not to a generic kiosk. Its five principal PBR
surface families are now authored; signage artwork, food imagery, social
icons, menu lettering, prices, stickers and the diamond-plate relief remain
separate artwork/detail passes.

## Status: second pass complete, surface-textured

The blockout was approved (6.40 m width confirmed) on 2026-09-12, and the §30
second pass followed: vent/panel divisions, structural framing, sign mounting
details, the side service door, interior counters and equipment, the register
area, menu boards and lighting fixtures. The 2026-09-23 surface pass binds
measured enamel and metal sets to the shipped GLB while preserving every node
name, interaction anchor and light anchor.

## Deliverables

- Approval blockout: `blender/source/greek_gyros_blockout.blend`
- Editable geometry source: `blender/source/greek_gyros.blend`
- Blockout rebuild script: `blender/scripts/createGreekGyrosBlockout.py`
- Second-pass rebuild script: `blender/scripts/createGreekGyros.py`
  (imports the blockout script as a module and builds on its approved layout,
  the same way `createTheHive.py` builds on `createTheHiveBlockout.py`)
- Three.js runtime model: `public/assets/models/greek_gyros.glb`
- Preserved untextured runtime source:
  `blender/source/runtime-untextured/greek_gyros.glb`
- Surface authoring script: `blender/scripts/greekGyrosTextures.py`
- PBR maps and palette: `blender/source/textures/greek-gyros/`
- Surface review frames: `renders/greek-gyros-textures/`
- Blockout-stage GLB (kept for comparison): `public/assets/models/greek-gyros-blockout.glb`
- Blockout renders: `renders/greek-gyros-blockout/`
- Second-pass renders: `renders/greek-gyros/`

Regenerate the second pass (which rebuilds the blockout internally, then adds
detail) from the project root with:

```sh
/Applications/Blender.app/Contents/MacOS/Blender \
  --background \
  --python blender/scripts/createGreekGyros.py
```

Regenerate only the blockout with:

```sh
/Applications/Blender.app/Contents/MacOS/Blender \
  --background \
  --python blender/scripts/createGreekGyrosBlockout.py
```

## Scale and orientation

Inferred envelope: **6.40 m wide × 2.60 m deep × 3.40 m** to the top of the
sign cap. The sign box and canopy overhang to 6.84 m across and project 0.48 m
forward of the front plane; the side service step adds 0.56 m past the
right-hand wall, so the exported GLB measures 7.18 m across overall.

- One Blender unit is one metre, Z is vertical, ground is Z = 0.
- The serving frontage faces **-Y**, matching the other street assets here.
- Origin is at ground level at the geometric centre of the kiosk footprint, so
  it snaps straight onto pavement geometry (§25).
- 133 exported mesh objects, roughly 1,880 triangles.

Key heights: chassis skirt to 0.26 m, blue lower front panel 0.26–0.94 m,
metal-clad apron 0.94–1.22 m, stainless worktop at 1.28 m, serving opening
1.28–2.30 m, secondary menu strip 2.38–2.68 m, `GREEK GYROS` fascia
2.68–3.32 m, cap to 3.40 m. Interior floor 0.32 m, ceiling 2.32 m.

These are estimated from the references — customers at the counter, the
project's 1.78 m player height, and standard kiosk counter/fascia heights —
**not surveyed**. The two 1.78 m blocked figures in the renders are review-only
scale checks and are excluded from both GLBs, along with the pavement plane.

## Structure

Objects are grouped under `GREEK_GYROS_MASTER` following the brief's §3
hierarchy: `GG_KioskShell`, `GG_Frontage`, `GG_RoofCanopy`,
`GG_SignageSurfaces`, `GG_InteriorShell`, `GG_LightingFixtures`,
`GG_InteractionAnchors`, plus review-only camera/light/ground collections that
the GLB export excludes.

The second pass adds corner posts and side/rear/apron panel seams, opening sill
and header framing, sign mounting rails, stays and brackets, roof extraction
(plenum, duct, cowl), roof vents and a rear louvre, the right-hand side service
door with jambs, handle and step (§13), a continuous interior rear run
(refrigerated counter, prep counter, rotisserie counter, grill with hotplate
and backsplash), an extraction hood, condiment area, two wall shelves, three
menu boards, hot-food display wells with a glass serving screen, and the
register end with POS block and card reader (§16).

Signage surfaces are kept as separate meshes so artwork can be applied without
touching structure (§20): `GG_MainSignSurface` (the `GREEK GYROS` fascia),
`GG_MenuStripSurface` (`CHICKEN • PORK • HALLOUMI • ON WRAPS OR BOXES`),
`GG_LowerFrontSignSurface`, `GG_SideSignSurface`, `GG_OrderHereSurface`,
`GG_PickUpHereSurface`, `GG_MenuBoard_A`–`_C`, and `GG_FlagPanel_Left` /
`GG_FlagPanel_Right`, which are reserved rectangles for the Greek flag motifs
rather than modelled stripes (§21).

The runtime export replaces the five opaque placeholders with
`MAT_GG_Surface_*` PBR materials: measured warm-white enamel, measured blue
enamel, the darker secondary fascia blue, dark coated frame metal and
stainless steel. Glass and fixture-lens placeholders remain deliberately
untextured because their transparency and emission are set by the runtime.
The blue panel's fine wear uses a retained ImageGen source only as a
low-contrast luminance field; colour still comes from the photographic
palette. Exact provenance and the prompt are recorded in `validation.json`.

## Interaction, lighting and collision

Nine empties ship in the GLB. Five are the §22 vendor interaction anchors:
`GG_OrderAnchor` in front of the counter on the register side,
`GG_VendorAnchor` behind it, and `GG_QueueAnchor_01`–`_03` along the frontage.
Four are authored light positions for the night look described in §§18–19 —
`GG_LightAnchor_Counter`, `GG_LightAnchor_Interior_A`/`_B` and
`GG_LightAnchor_Fascia`. `createWorld.ts` currently reads the counter anchor
as a restrained warm-white local light through `LocalLightRegistry`; the
interior and fascia anchors are reserved for the final night-material pass.
The fixture meshes
(`GG_LightFixture_A_CounterStrip`, `GG_LightFixture_B_Ceiling_01`/`_02` and
their lens plates) are plain geometry so the emissive treatment can be chosen
at texture stage rather than baked now.

Collision should stay simple (§23): a single 6.40 × 2.60 m footprint box is
enough. The serving opening is not a walkable gap — the counter closes it — so
no cut-outs are needed. The 0.52 × 0.74 m side step at the right-hand end sits
outside that footprint; either widen the box by ~0.6 m on that side or let the
player walk over it.

## In the world

The kiosk is placed at **(20.6, 10.5)** on the park's east edge, declared in
`FOOD_STANDS` in `src/world/worldLayout.ts` and loaded by `addGreekGyros` in
`src/world/createWorld.ts`. Blender's -Y frontage imports facing +Z; runtime
rotation turns the serving front west toward the park. Collision is a single
box, 6.4 × 2.6 m extended 0.56 m to enclose the side service step. Inspect it
in a development build with `?view=greek-gyros`.

## Not yet done

- Signage artwork: the `GREEK GYROS` wordmark, Greek flags, menu strip, social
  icons, food imagery and menu-board content. Signage remains deferred by the
  building-texture plan.
- A dedicated diamond-plate relief set. The current apron shares the authored
  stainless-steel surface with counters and fittings, so adding tread relief
  without a material split would incorrectly texture all stainless parts.
- Final night materials and signage lighting (§§18–19). The runtime now gives
  the fixture lenses a placeholder emissive and uses the counter anchor for a
  preliminary local light, but the fascia, menu boards, bright white interior
  and final spill still belong to the texture/material pass.
