# Vinyl Exchange, Oldham Street / Dale Street

This asset is a metric, geometry-only reconstruction of the Vinyl Exchange
corner at Oldham Street and Dale Street, Manchester, inferred from the
photographs in `references/architecture/buildings/vinyl-exchange/` per the brief
`14_Vinyl_Exchange.txt`.

**Status: blockout integrated in game — DETAIL-PASS REVIEW HOLD.** Daniel's
instruction to put the existing blockout in the game approves runtime use at
this stage. It does not resolve the architectural questions below or start the
second detail pass (brief section 47).

## Deliverables so far

- Approval blockout: `blender/source/vinyl_exchange_blockout.blend`
- Deterministic rebuild script: `blender/scripts/createVinylExchangeBlockout.py`
- Runtime-export script: `blender/scripts/exportVinylExchangeBlockout.py`
- Runtime blockout: `public/assets/models/vinyl-exchange-blockout.glb`
- Blockout renders: `renders/vinyl-exchange-blockout/` (views A–E)
- Surface materials, first batch: `blender/scripts/vinylExchangeTextures.py`,
  maps in `blender/source/textures/vinyl-exchange/`, review frames in
  `renders/vinyl-exchange-textures/` (see "Surface materials" below)

Regenerate from the project root with:

```sh
/Applications/Blender.app/Contents/MacOS/Blender \
  --background --python blender/scripts/createVinylExchangeBlockout.py
```

Export the current approved blockout without rebuilding or rerendering it with:

```sh
/Applications/Blender.app/Contents/MacOS/Blender \
  --background --factory-startup \
  --python blender/scripts/exportVinylExchangeBlockout.py
```

The exporter includes only `VINYL_EXCHANGE_MASTER` and its descendants. The
review pavement, road, figures, cameras and light are not shipped. The GLB is
1.2 MB and contains 125 objects, 121 meshes and 27,744 triangles.

Not yet produced: the detailed `vinyl_exchange.blend` and final
`vinyl_exchange.glb` named in the brief.

## In the game

- `worldLayout.ts` now records the authored 7.44 × 11.14 × 14.45 m body as a
  `geometry-wip` location centred at `(-7, 48.43)`. Its Oldham Street frontage
  remains on the existing South Road building line at Z = 54.
- The asset remains at 1:1 authored scale. Blender -Y imports as world +Z, so
  the main frontage faces south without rotation; the perpendicular Dale
  Street return faces east into the open gap toward Spice Cabin.
- The loader aligns the authored street-line corner to the plot's south-east
  corner and stands pavement Z = 0 on the sampled game pavement. Review-only
  context is supplied by the world's existing road and pavement systems.
- Runtime material policy preserves the blockout palette, disables accidental
  emissive treatment and configures the shared glass material for Three.js.
- The old procedural mass remains only as a hidden loading/error fallback. The
  measured body footprint is solid for player and camera collision because the
  door interaction system does not exist yet.
- Development view: `?view=vinyl-exchange`.

## Plan convention

One Blender unit equals one metre; Z is vertical, and the pavement top is Z 0.
The Oldham Street building line is Y 0 and faces -Y. The Dale Street building
line is X 0 and faces +X. The two lines meet at a 45° chamfer 1.60 m wide,
so the world origin is the notional intersection of the two street lines.
Standing on Oldham Street facing the shop, Dale Street recedes to the right.
Every street element is authored in a per-face (u along face, w inward, z)
frame, so the second pass can reuse the same bay and height constants.

## Blockout checks (brief section 46)

| # | Check | Blockout value | Source |
|---|---|---|---|
| 1 | Shop width | Oldham 5.35 m (arris → left ribbed pier); Dale 10.01 m | door leaves, pier rhythm, people |
| 2 | Corner width | 1.60 m chamfer at 45° | chamfer window ≈ one opening; black sign box width |
| 3 | Fascia height | 1.35 m (Z 2.95–4.30), front 0.32 m proud of building line | fascia : vent : glazing ratios in both straight-on photos |
| 4 | Entrance width | 1.55 m double glazed doors (two 0.715 m leaves), 2.30 m high | door vs display windows |
| 5 | Side-window proportions | Dale glazing 2.41 m and 3.72 m wide, Z 0.25–2.35 | Dale Street straight-on photo |
| 6 | Upper-floor height | F1 3.35 m, F2 3.15 m, F3 2.95 m; parapet top 14.45 m | F1 measured; F2 partly visible; **F3/roof inferred** |
| 7 | Arch spacing | 1.85 m bays; 1.00 m openings; 0.70 m piers; springing Z 6.20 | pier centres identical in Oldham and Dale photos |
| 8 | Corner bay depth | no projecting bay; arris piers project 0.22 m; 0.45 m reveals | low-angle corner photos |
| 9 | Building depth | 7.44 m along Oldham × 11.14 m along Dale | **inferred** — no rear reference |
| 10 | Oldham/Dale relationship | 90° street angle with chamfer; three Oldham bays, one chamfer bay, five Dale bays | **angle inferred** |

The Oldham plaque sits on the base of the first Oldham pier, just above the
right edge of the door. The Dale plaque sits on the Dale face of the arris
pier. Both are separate named objects that are not merged with the fascia.

## What the blockout contains

- Opening-aware upper walls: three storeys of semicircular-headed openings are
  punched through a 0.45 m wall, so each reveal is real geometry and not an
  overlay.
- Plain pier, impost, archivolt, string-course and cornice massing, with dark
  frames, mullions and transoms. The frames and mullions sit under the
  separate `VE_Glass` objects.
- The grey fascia wraps the corner, with a projecting black corner sign box.
- Placement proxies for the `vinyl` / `exchange` letters on both fascias. These
  are extruded Arial Narrow Bold (a macOS system font), not the real typeface.
- Tagline surfaces on both fascias, plus `VE_SideLogoSurface`.
- The Oldham shopfront: display windows, `VE_Display_Left`/`Right`, and double
  doors. Each leaf is pivoted at its hinge under `VE_MainDoor`, with glass
  parented to the leaf.
- The corner recess with the pale green door, and the white tiled columns.
- The Dale Street gate recess with AC units and a picket proxy of
  `VE_CornerSecurityGate`.
- Vents shown as recessed zones.
- A simple interior shell: floor, ceiling, and side and rear walls. It stretches
  about 10 m back from Oldham Street and 6 m back from Dale Street.
- `VE_EntranceAnchor` and `VE_InteriorSpawnAnchor`.

Context objects are the pavement, road, a neighbour ground stub under the
Oldham party bay, and two 1.75 m scale figures. They live outside
`VINYL_EXCHANGE_MASTER`, alongside the cameras and the sun.

## Surface materials (first batch)

The blockout carries flat `*_PLACEHOLDER` materials. The first batch of real
surfaces is authored by `blender/scripts/vinylExchangeTextures.py` and written
to `blender/source/textures/vinyl-exchange/` as glTF-convention map sets:

```
<slug>-basecolor.png   sRGB
<slug>-orm.png         R occlusion, G roughness, B metallic
<slug>-normal.png      OpenGL tangent space (+Y up)
```

Regenerate from the project root with:

```sh
/Applications/Blender.app/Contents/MacOS/Blender \
  --background --factory-startup \
  --python blender/scripts/vinylExchangeTextures.py
```

Add `-- --no-render` to write the maps without the review frames.

### Why tiling sets rather than a baked atlas

The geometry is still on the detail-pass hold, and section 47 will add
pilasters, capitals, moulded arches, vent slats, the accordion gate and the
lettering. An atlas baked on the blockout UVs would be discarded with the
geometry it was baked for. These surfaces are geometry-independent: they say
what each material *is*, and survive the detail pass.

The division of labour is deliberate. **Material identity** — coursing, panel
joints, glaze, ribs, paint, rust — lives in these tiles. **Position-dependent
weathering** — the drip below one particular sill, the spray line at the kerb,
the hand height on one door — belongs to a later `surfaceWeathering` atlas bake
on the finished geometry, exactly as the Spice Cabin and the pallets were done,
and is deliberately not baked in here. Two surfaces are exceptions, because
their vertical extent is already fixed by the building: the fascia band and the
corner door are authored with a real top and bottom and tile only sideways.

### The set

| Slug | Surface | Tile | Pixels | mm/texel |
| --- | --- | --- | --- | --- |
| `stone-painted-ashlar` | Upper facade painted ashlar, sooted joints, washed faces | 2.40 × 2.40 m, both axes | 2048² | 1.17 |
| `fascia-grey-panel` | Fascia band: coated panel, butt joint, fixings, top grime, run-down | 1.35 × 1.35 m, sideways only | 2048² | 0.66 |
| `logo-red-acrylic` | Projecting logo letters: moulded crimson acrylic | 0.60 × 0.60 m, both axes | 1024² | 0.59 |
| `sign-black-panel` | Corner sign box and tagline strip: satin black panel | 1.00 × 1.00 m, both axes | 1024² | 0.98 |
| `frame-blue-paint` | Upper window frames: aged petrol-blue paint, chalking, chips | 0.30 × 0.30 m, both axes | 1024² | 0.29 |
| `shopfront-ribbed-alu` | Shopfront piers: ribbed mill-finish aluminium, 32 mm pitch | 0.64 × 0.64 m, both axes | 1024² | 0.63 |
| `tile-white-glazed` | Shopfront base and corner columns: 100 mm glazed tiles | 1.20 × 1.20 m, both axes | 2048² | 0.59 |
| `door-green-paint` | Corner door: boarded sage paint, kick scuffs, hand grime, tape | 1.15 × 2.30 m, sideways only | 1024 × 2048 | 1.12 |
| `grille-dark-steel` | Security gate, vents, shutter framing: dark painted steel | 0.50 × 0.50 m, both axes | 1024² | 0.49 |

`coverage_m` in `validation.json` is what one tile spans in the world, so UV
scale follows from it directly: a 1.35 m fascia band takes one tile up its
height, and a 10 m run of it repeats 7.4 times across.

The tagline strip uses `sign-black-panel` with its base colour lifted at
runtime rather than carrying its own maps — it is the same coating a few
shades lighter (measured `#303239` against the corner box's `#41495B`).

### Palette provenance

Every colour is anchored on a patch median sampled from the photographs in
`references/architecture/buildings/vinyl-exchange/`; the patches and their
source files are listed under `measured_reference_patches` in
`validation.json`. Those samples carry the photographs' own hard August sun and
deep shade, so each is treated as evidence of hue and relative value, and the
authored albedo is the one that would produce it. **No pixels from the
references reach the output** — everything is generated.

### Validation

`blender/source/textures/vinyl-exchange/validation.json` records per material:
coverage, pixels, mm/texel, which axes tile, roughness/metallic ranges, relief
in millimetres, mean base colour, file sizes, and a seam measurement.

The seam measurement reports, in 8-bit levels, the step across each wrapping
edge next to the tile's typical adjacent-pixel step. Two entries are large by
design and were confirmed by eye in the review frames: the stone's course line
and the aluminium's rib groove each fall exactly on a tile edge, so the step
there is the feature itself, not a seam.

Review frames are in `renders/vinyl-exchange-textures/`: one 2 × 2 tiled panel
per material (tiled so any seam shows as a ruled line across the panel), plus
`00-contact-sheet.png`. They are rendered flat-on under a raking key with the
`Standard` view transform, not AgX — this is a material check, so the frames
should report the albedo that was authored rather than the game's grade.

### Not in this batch

Glass, the street plaques (both need their lettering, and the plaques are
enamel over a different substrate), the display-window stock, the interior,
the pavement and road at this corner (the world's own road and pavement systems
already own those), and all lettering geometry and typography, which stay with
section 48.

## Deferred to the second pass

Half-round colonnettes and collars, clustered floral capitals, moulded arch
profiles, relief bands and spandrel panels, vent louvres, rib grooves, the
folding accordion lattice, the cable bundle, detailed aluminium frames, and
final lettering geometry validated against the logo (section 48).

## Open questions before the second pass

- The brief mentions a "projecting corner bay". The photos read to me as a
  chamfer with piers at both arrises and one window on the chamfer, so that is
  what the blockout models. Confirm or correct.
- The number of storeys above first floor and the roofline are not visible in
  any reference.
- The fictional map does not reproduce the real Oldham/Dale road junction. The
  blockout therefore uses the existing South Road building line for Oldham
  Street and lets the Dale Street return face the open inter-building gap. A
  later map pass can decide whether that gap becomes a named side street.
- At ground level, the Oldham party bay (u 5.35–6.31 m, under the fig + sparrow
  fascia) is only a context stub. Decide whether the export includes a plain
  neighbour bay or trims the upper facade.
