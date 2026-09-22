# Cass Art, Northern Quarter

This asset is a metric, textured reconstruction of the Cass Art frontage at
55–57 Oldham Street, inferred from the photographs in
`references/architecture/buildings/cass-art/`. It is intended as an enterable
Three.js location. The texture pass reproduces the charcoal cladding, exact
orange slogan and address, projecting logo sign, pale timber shop floor and
the cassette / eight-ball / popcorn window installation visible in the 2026
field photographs. Individual products and loose shop props remain a later
interior-dressing pass.

## Deliverables

- Approval blockout: `blender/source/cass_art_blockout.blend`
- Editable geometry source: `blender/source/cass_art.blend`
- Deterministic rebuild script: `blender/scripts/createCassArt.py`
- Deterministic texture generator: `blender/scripts/cassArtTextures.py`
- Texture sources and generated maps: `blender/source/textures/cass-art/`
- Three.js runtime model: `public/assets/models/cass_art.glb`
- Blockout renders: `renders/cass-art-blockout/`
- Exported textured-GLB review renders: `renders/cass-art-textures/`
- Photographic letter-outline tracer: `blender/scripts/traceCassArtLettering.py`

Regenerate the texture maps and asset from the project root with:

```sh
python3 blender/scripts/cassArtTextures.py
/Applications/Blender.app/Contents/MacOS/Blender \
  --background --factory-startup \
  --python blender/scripts/createCassArt.py
```

Set `CASS_SKIP_RENDERS=1` to rebuild and validate the Blender/GLB assets without
re-rendering existing review images.

## Architecture and scale

The estimated envelope is **18.0 m wide × 11.8 m deep**, with the shopfront
fascia reaching approximately **4.6 m** and the upper railing reaching
approximately **6.1 m**. One Blender unit equals one metre; Z is vertical and
the finished floor is at Z 0.

Recognition-critical geometry includes:

- the long, low, dark-panelled facade and its stepped physical depths;
- four separately modelled glazing regions and a recessed glazed entrance;
- blank surfaces for the long slogan, address, and projecting Cass Art sign;
- the metal-grid balcony/railing immediately above the storefront;
- an enterable interior shell with wall shelving, central gondolas, paper
  racks, counter, circulation aisles, and ceiling tracks.

`CASS_Slogan_DecalSurface` retains its historical name but is now **raised mesh
lettering**, traced from the orange pixels in `DSC06343.JPG`. The exact photographed
phrase is **LETS FILL THIS TOWN WITH ARTISTS** (no apostrophe). All 27 letter
outlines and three counters are retained, with the photographed spacing and
aspect ratio, a 24 mm total extrusion and a slender mounting rail. It is not a
substitute font or a generated text image. `CASS_LogoSign_DecalSurface`
and `CASS_Address_DecalSurface` carry the projecting logo and 55–57 address.
The main and right window graphics use transparent layers outside the glass,
with their original aspect ratios maintained. The left logo/poster, entrance
popcorn display, kick vents, alarm label, stickered pier and white chalk tag use
UV-selected regions of the original photograph. The passage remains open.

## Texture provenance and material treatment

The source photographs are `DSC06340.JPG`, `DSC06343.JPG`,
`CASS-Arts-623x438.jpg` and the supplied clean logo reference. The facade base
source, `cass-facade-source.png`, was generated with the built-in image tool
from those photographs as a neutral, seamless cladding study. The checked-in
generator then creates the darker albedo, restrained normal and roughness maps
used by the game on the returns. The fascia front samples a clean cladding strip
from the photograph. Main and right window graphics are built-in ImageGen
reconstructions with alpha, retained as `cass-window-display-reference.png` and
`cass-right-display-reference.png`; they approximate the hand-painted display,
whereas the fascia lettering uses the actual photographed outlines. The original
schematic PNG previews are not used by the runtime.

The facade deliberately avoids heavy generic grunge. Recognition comes from
the panel depth, rain-softened charcoal surface, orange slogan, black aluminium
frames and the graphic window layer. Floor grain and interior materials remain
quiet so that the shop still reads through the glass at night.

## Gameplay anchors

The GLB exports the following transform nodes for game integration:

- `CASS_EntranceTriggerAnchor`
- `CASS_StaffAnchor`
- `CASS_CustomerInteractionAnchor`
- `CASS_Light_Window`
- `CASS_LightTrackAnchor_01` through `CASS_LightTrackAnchor_04`

## Game integration

Cass Art is loaded by `src/world/createWorld.ts` into the former Real Camera
area at world centre `(-16.6, 39)`. The authored facade is rotated to face
north and rendered at approximately 101% of authored scale, making this pass
about 30% larger than the first 14 m integration. Dreams shifts east so the two
buildings meet cleanly without Cass Art entering the West perimeter road.
Collision is split into side, rear, and shopfront segments so the recessed
entrance remains open to the player.

The ceiling fixtures use the dedicated `MAT_CASS_LightFixture`
material. Runtime policy turns those fixtures warm and emissive and adds a low
warm response to the interior shell. Three warm point lights at the exported
window and central track anchors illuminate the front glazing, shelves and
floor. They participate in the same nearest-light budget as the exterior hero
lights, so the active-light ceiling does not increase.

Real Camera has moved to `(-11.5, 69.75)`, opposite Vinyl Exchange and west of
Advanced Photo. The slight westward offset leaves the South Road outward
connection unobstructed.

## Runtime validation

The GLB consolidates components by material while preserving all UV loops and
**8 empty/anchor nodes**. The former exporter discarded UVs during consolidation;
this is now fixed and covered by `tests/cass-art-asset.test.mjs`, including a
non-collapsed-coordinate check. Maps are embedded as WebP, with a 5 MB asset
budget. `renderCassArtTextures.py` imports the actual exported GLB for review,
including a dedicated lettering close-up. The raised sign has a restrained
runtime emissive lift so its orange colour remains readable at night without
introducing another dynamic light.

Individual products, modular art-supply props, NPCs, and gameplay logic remain
separate future passes.
