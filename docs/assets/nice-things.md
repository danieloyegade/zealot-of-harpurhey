# Nice Things, Oldham Street

Florist in the ground floor of Central Buildings, with the Central Buildings
entrance arch beside it. It is reconstructed from the photographs in
`references/architecture/buildings/florist/` per the brief
`08_Nice_Things_Florist.txt`. This is the collection point for Delivery 001.

**Status: approved geometry blockout + first surface-material pass.** The
second geometry pass (brief §35) has not started. Signage, the `nice things.`
lettering, the vents, the plants and the window graphics are still to come.

## Deliverables

- Blockout script: `blender/scripts/createNiceThingsBlockout.py` writes
  `blender/source/nice_things_blockout.blend`, an untextured GLB and the
  review renders in `renders/nice-things-blockout/`.
- Surface materials: `blender/scripts/niceThingsTextures.py` writes the PBR
  sets to `blender/source/textures/nice-things/`, with `validation.json` and
  review frames in `renders/nice-things-textures/`.
- Runtime exporter: `blender/scripts/exportNiceThings.py` binds the sets in
  memory, adds metric box-projected UVs, and writes
  `public/assets/models/nice-things-blockout.glb` with WebP-embedded maps
  (about 1.5 MB).

Regenerate in this order. The blockout script overwrites the GLB with an
untextured one, so the exporter must always run last:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --python blender/scripts/createNiceThingsBlockout.py
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python blender/scripts/niceThingsTextures.py
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python blender/scripts/exportNiceThings.py
```

## Surface materials

These are tiling metric sets, not an atlas, for the same reason as Vinyl
Exchange: the geometry still has a detail pass to go. Colours are patch
medians sampled from the reference photographs and then de-lit (see
`MEASURED` in the script).

| Set | Covers | Read from the references |
| --- | --- | --- |
| `pink-limewash` | fascia, jambs, plinth, sill, reveal, logo mount | Salmon limewash with rose and blush swirled brush strokes, plus faint board joints at 1.2 m |
| `pink-satin-joinery` | door frame, display-window mullions | The same pink in a harder satin paint on timber |
| `sandstone-ashlar` | upper facade, pilasters, sills, lintels, Central Buildings piers, arch, balusters | Buff coursed ashlar (0.38 m courses) with soot run-down and pitting |
| `sandstone-sooted` | string courses, cornice, balcony slab, entrance lintel, threshold, roof | The same stone under a soot crust |
| `white-painted-frame` | upper sashes, fanlight bars | White paint under a grey dirt film |
| `interior-plaster-warm` | interior walls, ceiling | Warm peach emulsion |
| `floor-sealed-concrete` | interior floor | Sealed warm-grey concrete |
| `birch-ply` | counter, shelving, display plinth | Lacquered birch ply |
| `dark-painted-steel` | roller-shutter box, door handle | Dark grey powder coat |

The glass stays `MAT_NT_Glass_PLACEHOLDER`, which runtime makes transparent.
Location-specific weathering is left for a later atlas bake on the finished
geometry: graffiti on the Central Buildings pier, soot under the cornice,
scuffs at the door.
