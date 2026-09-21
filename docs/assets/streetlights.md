# Municipal streetlight family

## Asset status

Four new council streetlights replace the procedural six-sided poles and the
Coral streetlamp in the game. They were built from scratch, not derived from
the old geometry. They should be boring by day. At night only the lamp is
theatrical; the column stays ordinary metal that mostly disappears into
the dark.

| GLB | Root node | Column | Lantern | Light |
| --- | --- | --- | --- | --- |
| `streetlight-warm-old-01.glb` | `Streetlight_Warm_Old_01` | 7.8 m galvanised, 193 mm base compartment tapering to 108 mm, cast top sleeve, short raked stub arm | 870 mm side-entry cast lantern, prismatic trough bowl, visible SOX U-tube | low-pressure sodium, ~1800 K |
| `streetlight-led-modern-01.glb` | `Streetlight_LED_Modern_01` | 7.8 m stepped galvanised (168 → 139 → 114 mm), integral bent bracket | 680 mm flat dark-grey LED luminaire, recessed 4 × 10 lens board, NEMA sensor cap | LED, ~4000 K |
| `streetlight-curved-01.glb` | `Streetlight_Curved_01` | 6.7 m painted charcoal, 144 mm base, swan neck with an opening bend radius and a small sideways drift | compact SON lantern, shallow bowl | high-pressure sodium, ~2100 K |
| `streetlight-weathered-01.glb` | `Streetlight_Weathered_01` | 7.7 m older galvanised column, slight lean, clamp collar, raked single arm with strut | older SON cobra head, deep bowl | high-pressure sodium, ~2000 K |

References: Daniel's streetlight photo board (2026-09-21), especially the
orange lamp over terraced houses, the BBC LED and Milton images, and the
Hailsham and Belfast bent columns.

## Hierarchy

```
Streetlight_*            root, origin = column centre at pavement level
├── LOD0                 Pole, AccessPanel, Arm, LampHousing, (LEDBoard), LampGlass, LampEmitter
├── LOD1                 same parts, fewer segments, no bolts/welds/lenses
├── LOD2                 Pole, Arm, LampHousing, LampGlass, LampEmitter
└── LightEmitter         empty at the real light source, pointing down
```

The lantern overhangs the carriageway along +X. The maintenance door faces
the footway (−X). `LightEmitter` carries glTF extras: `colorTemperatureK`,
`colorSRGB`, `beamAngleDeg`, `aimForwardM` (the peak of a real distribution
falls a little ahead of the column, toward the road). The root carries
`assetHeightM`, `lodDistancesM` (0 / 26 / 60 m) and `family`.

Triangle counts: LOD0 ≈ 4.4–5.4k, LOD1 ≈ 1.0–1.3k, LOD2 ≈ 0.4–0.5k. Each GLB
is about 0.4 MB (WebP textures). These counts are below the brief's upper
targets on purpose: the lamps repeat along every street.

## Materials

Names are shared across all four GLBs so the game can recolour one instance:

- `SL_<Model>_Body` (+ `_LOD1`, `_LOD2`): the baked atlas for the column, door,
  arm and housing. 1024² for LOD0, 256² for LOD1, flat colour for LOD2. Base
  colour, ORM (AO, roughness, metallic), normal, plus an **emissive spill mask**
  covering only housing and arm surfaces that face the lamp. It is greyscale:
  the game sets the colour.
- `SL_Emitter_SOX` / `SL_Emitter_SON` / `SL_Emitter_LED`: the lamp itself. This
  is the only strongly emissive surface.
- `SL_Glass_Prismatic` (sodium bowls, faint emission to scatter the lamp),
  `SL_Glass_Clear` (LED cover, no emission).
- `SL_Reflector`: the housing underside above the bowl, faintly emissive.
- `SL_LED_Board`: dark board between the LED lenses.

Weathering is authored in asset space (`author_body` in the script) and
scales with each model's `age`: galvanised spangle and zinc bloom, rain
streaks, grime under every joint and weld, road spray and a dark ground-contact
band on the road side, key scratches and hand polish around the door, a
column number plate (yellow, seven-segment digits), a small maintenance
sticker (or torn sticker residue on the weathered column), rust weeping from
bolts, dirt where the lantern meets its spigot, bird staining on lantern tops.
The painted column fades to chalk where sun and rain reach it and is chipped
to galvanising low down.

## Runtime

`src/world/createStreetlights.ts` loads each GLB once and builds a `THREE.LOD`
per lamp. Opaque parts are merged per material, so each visible lamp costs
about four draw calls. Materials are cloned once per (model, light colour).
The emitter, bowl, reflector and spill mask take the lamp's colour; nothing
else glows.

`STREETLIGHT_MODELS` mirrors each `LightEmitter` position so pools and the
light proxy can be placed before the GLB arrives. If a rebuilt GLB moves its
emitter, the loader logs a warning naming the new position.

Placement is in `createWorld.ts` (`STREETLIGHTS`): each entry names its
fixture. Models are assigned street by street, like council batches. Every
lantern is turned toward the nearest road's centre line. The painted pool and
the single managed light proxy sit under and at the lantern, not at the
column.

## Regenerating

```
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
  --python blender/scripts/createStreetlights.py -- --stage all
```

Stages: `clay` (untextured line-up and head close-ups), `build` (bake, author
textures, save `blender/source/streetlights/<slug>.blend`, export GLBs),
`renders` (night and overcast test renders to `renders/streetlights/`). Add
`--only <slug>[,<slug>]` to limit the run. A full run takes about 25 minutes
on CPU, mostly the test renders.

After a rebuild, check the console for the `LightEmitter` warning and update
`STREETLIGHT_MODELS` if it appears.
