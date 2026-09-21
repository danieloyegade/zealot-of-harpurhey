# MCR1 corner shop

MCR1 is a metric reconstruction of the corner shop at Hilton Street and
Stevenson Square, textured and shown with its illuminated signage.

## Signage state (canonical for the game)

The game shows the old, very bright configuration from the night photograph:
yellow honeycomb lightboxes wrapping the corner, two MCR_1 wordmarks, the
white roundel and the neon CONVENIENCE STORE blade. In the real city the
owner was asked to take it down because some people found it tacky. In the
game it stays up, and that is a mechanic: the shopkeeper tells the player
that people keep asking him to take it down. The later black-and-gold fascia
in the daylight set is not modelled.

## Reconstruction rule

The source set records two historical states and they must remain distinct:

- The three daylight photographs are the architectural source for dimensions,
  proportions, glazing, entrance, structural framing, corner geometry, interior
  volume, and the relationship to the historic building above.
- The night photograph is the source for the older illuminated frontage: the
  wrapped fascia, repeated branding zones, circular sign, and projecting vape
  sign. Its graphics are not yet modelled.

The modern black-and-gold fascia visible in the daylight set is not the target
sign design.

## Immutable reference images

All source images are stored together in `references/architecture/mcr1/`:

| File | Role | Dimensions |
| --- | --- | --- |
| `DSC06325.JPG` | Daylight side/corner construction | 6000 × 4000 |
| `DSC06326.JPG` | Daylight main frontage and entrance | 6000 × 4000 |
| `DSC06327.JPG` | Daylight wider architectural elevation | 6000 × 4000 |
| `new-stevenson-square-addition-v0-lte1ozn2fpkg1.jpeg.webp` | Historical night signage configuration | 1080 × 810 |

Reference files are development sources. Do not resize, overwrite, or move them
into `public/`. Any later crops, masks, or processed textures should be written
to an asset-specific directory beneath `blender/source/textures/mcr1/`.

## Geometry-stage outputs

- Rebuild script: `blender/scripts/createMCR1.py`
- Editable master: `blender/source/harperhey-mcr1-geometry.blend`
- Runtime GLB: `public/assets/models/harperhey-mcr1-geometry.glb`
- Review renders: `renders/mcr1/`

The master uses one Blender unit per metre, ground level at Z 0, applied mesh
rotation and scale transforms, named collections, a simplified enterable
interior shell, and separate physical sign housings for the historic frontage.

Rebuild from the repository root with:

```sh
/Applications/Blender.app/Contents/MacOS/Blender \
  --background --factory-startup \
  --python blender/scripts/createMCR1.py
```

The script regenerates the Blender master, GLB, and all four QC views.

## Game integration

`src/world/createWorld.ts` loads the geometry-stage GLB in place of the former
procedural building that was incorrectly labelled M1. The canonical location ID
and display name are now `mcr1` and `MCR1`. The model remains at its authored
metric scale and uses its neutral clay material IDs; no runtime facade textures
or emissive signage are applied yet. Its 12 × 7 metre collision plot sits
immediately west of the Florist.

## QC render manifest

Views 05 and 06 are night renders with the QC lights off, for comparison with the night photograph.

| File | Required view |
| --- | --- |
| `mcr1_01_straight_shopfront.png` | Straight-on shopfront |
| `mcr1_02_daylight_corner_three_quarter.png` | Daylight-reference corner view |
| `mcr1_03_opposite_corner.png` | Opposite corner |
| `mcr1_04_elevated_connection.png` | Elevated historic-building connection |

These are review artifacts, not runtime textures, and therefore remain under
`renders/mcr1/` rather than `public/`.

## Texture pass (2026-09-21)

`blender/scripts/mcr1Textures.py` writes every map to
`blender/source/textures/mcr1/` (see `manifest.json`). `createMCR1.py` calls it,
projects the UVs from the geometry and embeds the maps in the GLB as JPEG/PNG
(about 4.8 MB). Pass `-- --reuse-textures` to rebuild the model without
regenerating the maps, which takes about 4 minutes.

| Material | Source | Notes |
| --- | --- | --- |
| `MCR1_Brick` | procedural, 1.35 m tile | Pressed salmon-red stretcher bond with 8 mm pale joints (DSC06327) |
| `MCR1_Sandstone` | procedural, 1.8 m tile | Buff ashlar, sooted lower beds, washed patches |
| `MCR1_Signage` | atlas 4096 × 768 at 476 px/m | Fascia faces, roundel disc, blade sign |
| `MCR1_Honeycomb_Lightbox` | procedural tile | Corner piers wrapped in the lit perforated skin |
| `MCR1_Window_Vinyl` / `MCR1_Riser_Vinyl` | strip 4096 × 640 | Printed lower 1 m of each pane plus its stall riser; clear glass above |
| `MCR1_Upper_Glazing` | four sash variants | Net curtains, a lit office with blinds, dark glass |
| `MCR1_Shelving`, `MCR1_LED_Ceiling` | artwork / tile | Stocked gondolas and the honeycomb LED tube ceiling (DSC06326) |

At runtime `applyMcr1ModelPolicy` in `createWorld.ts` reuses the base colour as
the emissive map for the lit materials. The yellow lightboxes get a saturated
emissive tint so the tone mapper does not bleach them to cream. A pooled group
of three local lights (two yellow fascia washes and one cold interior spill)
and two reflection patches put the colour onto the street. Dev views:
`?view=mcr1` and `?view=mcr1-corner`.

The sign faces originally sat 7 cm inside their light boxes and were invisible.
They, the roundel disc and the ring now sit on the box fronts. The bar-light
housings on the interior ceiling were removed in favour of the LED texture.

## Deferred work

Location-specific grime (sill drips, kerb splash), the fly-posters and
stickers on the left pier, 3D products and counter detail, the shopkeeper NPC
and his complaint dialogue, and street furniture belong to later passes.
