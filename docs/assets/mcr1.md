# MCR1 corner shop

MCR1 is a metric, geometry-stage reconstruction of the corner shop at Hilton
Street and Stevenson Square. The current asset deliberately contains neutral
clay materials rather than final photographic textures.

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
- Editable master: `blender/source/harperhay-mcr1-geometry.blend`
- Runtime GLB: `public/assets/models/harperhay-mcr1-geometry.glb`
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

| File | Required view |
| --- | --- |
| `mcr1_01_straight_shopfront.png` | Straight-on shopfront |
| `mcr1_02_daylight_corner_three_quarter.png` | Daylight-reference corner view |
| `mcr1_03_opposite_corner.png` | Opposite corner |
| `mcr1_04_elevated_connection.png` | Elevated historic-building connection |

These are review artifacts, not runtime textures, and therefore remain under
`renders/mcr1/` rather than `public/`.

## Deferred work

Final MCR1 lettering, perforated fascia graphics, emissive surfaces, brick and
stone textures, grime, posters, stickers, products, shelves, counter detail,
NPC placement, and street furniture belong to later material, interior-prop,
and environment passes.
