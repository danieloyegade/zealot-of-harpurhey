# Cass Art, Northern Quarter

This asset is a metric, geometry-only reconstruction of the Cass Art frontage
at 55–57 Oldham Street, inferred from the photographs in
`references/architecture/cass-art/`. It is intended as an enterable Three.js
location and contains no final textures, logos, product packaging, posters,
graffiti, or window illustrations.

## Deliverables

- Approval blockout: `blender/source/cass_art_blockout.blend`
- Editable geometry source: `blender/source/cass_art.blend`
- Deterministic rebuild script: `blender/scripts/createCassArt.py`
- Three.js runtime model: `public/assets/models/cass_art.glb`
- Blockout renders: `renders/cass-art-blockout/`
- Final geometry renders: `renders/cass-art/`

Regenerate everything from the project root with:

```sh
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

The blank `CASS_Slogan_DecalSurface` must later receive the exact phrase
**LET’S FILL THIS TOWN WITH ARTISTS**. It must not be replaced by an oversized
generic Cass Art logo. `CASS_LogoSign_DecalSurface` and
`CASS_Address_DecalSurface` are reserved for the smaller projecting logo and
55–57 address treatment.

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

The ceiling fixtures use the dedicated `MAT_CASS_LightFixture_PLACEHOLDER`
material. Runtime policy turns those fixtures warm and emissive and adds a low
warm response to the interior shell. Three warm point lights at the exported
window and central track anchors illuminate the front glazing, shelves and
floor. They participate in the same nearest-light budget as the exterior hero
lights, so the active-light ceiling does not increase.

Real Camera has moved to `(-11.5, 69.75)`, opposite Vinyl Exchange and west of
Advanced Photo. The slight westward offset leaves the South Road outward
connection unobstructed.

## Runtime validation

The editable source retains **363 named component meshes** grouped into
architectural collections and totals approximately **4,356 triangles** before
small Blender-only bevel modifiers. The GLB consolidates these components into
**10 material-grouped runtime meshes** while preserving **8 empty/anchor nodes**.
It has been round-trip imported in Blender 5.2.1 to verify that the meshes and
anchors survive serialization.

Final PBR materials, facade wear, slogan/logo artwork, display graphics,
individual products, modular art-supply props, NPCs, and gameplay logic remain
separate future passes.
