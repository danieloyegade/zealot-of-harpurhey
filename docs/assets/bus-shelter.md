# North Road Preston bus shelter

## Asset status

The game uses the texture pass of the North Road, Preston shelter
(`preston-busstop-textured.glb`): the approved geometry, unchanged, carrying
baked PBR weathering, reconstructed signage and an emissive advert. The
shopping trolley still uses its placeholder materials; it was outside the
texture brief.

The shelter and trolley are independent root hierarchies:

- `PRESTON_BUS_SHELTER`
- `PRESTON_SHOPPING_TROLLEY`

The combined game export retains the reference composition, but either root can
be moved or removed without affecting the other. Standalone GLBs are also
generated for both assets.

## Source material

- Photograph: `references/architecture/bus-stop/Hires2.jpg`
- Reconstruction brief: `references/architecture/bus-stop/04_North_Road_Preston_Bus_Shelter.txt`
- Generated concept review: `renders/bus-shelter/00-generated-concept-review.png`

The photograph is authoritative for proportions and placement only. Trees,
houses, parked cars, grass, fencing, roads and warm illuminated background are
environmental content and are not reproduced on the shelter. Rear and side
panels are physically separate transparent glass surfaces.

## Generated source and runtime assets

`blender/scripts/createBusShelter.py` produces:

- `blender/source/bus-shelter/preston-busstop-blockout.blend`
- `blender/source/bus-shelter/preston-busstop.blend`
- `blender/source/bus-shelter/preston-busstop-reference.blend`
- `public/assets/models/bus-shelter/preston-bus-shelter.glb`
- `public/assets/models/bus-shelter/preston-shopping-trolley.glb`
- `public/assets/models/bus-shelter/preston-busstop-reference.glb`
- four numbered review renders under `renders/bus-shelter/`

`preston-busstop-reference.glb` contains the independently parented trolley in
the photographed position. `preston-bus-shelter.glb` and
`preston-shopping-trolley.glb` are available for later independent placement.
The game now loads the textured equivalent described below.

## Texture pass

Brief: `references/architecture/bus-stop/05_North_Road_Preston_Bus_Shelter_Texture_Brief.txt`.

`blender/scripts/createBusShelterTextured.py` rebuilds the approved geometry from
`createBusShelter.py` and adds only two objects: `BUSSTOP_Timetable_Cover`, a
thin acrylic layer so the poster and its reflections are distinct, and
`BUSSTOP_GroundContact_Decal`, so the shelter meets the pavement.

Grounding changes to the approved geometry, so it stands in the pavement rather
than on it:

- the uprights and rail legs run 30 mm below ground (the rail legs previously
  stopped 50 mm above it);
- `BUSSTOP_AdvertHousing_Plinth`, a narrower steel plinth set into the
  pavement, supports the advert unit as photographed. The housing previously
  floated 220 mm up.

The ground-contact decal carries AO under the structure, grime trapped at each
foot, debris along the rear panel, drip lines under both roof edges, and a
damp patch with a grit heap at the plinth's road-facing end.

The pass then:

1. unwraps each material group into a unique, density-consistent atlas;
2. bakes world position, world normal, object id, AO and convexity into that
   atlas (`surfaceWeathering.bake_buffers`);
3. authors weathering in world space from physical causes: rain exposure under
   the roof, road spray rising from the carriageway side, hand-contact heights,
   recess grime, sun on outward faces, cleaning arcs on glass;
4. reconstructs the timetable, No Smoking sign, stop number and advert as
   vector artwork (`busShelterArtwork.py`), then ages them. Fine print that is
   illegible in `Hires2.jpg` is set as print bars, and the advert keeps the
   photographed headline and palette but omits the manufacturer's trade marks;
5. exports WebP-embedded GLBs and the validation renders.

Outputs:

- `blender/source/bus-shelter/preston-busstop-textured.blend`
- `blender/source/textures/bus-shelter/texture-pass/`: frame and glass 2048²,
  roof and rail 1024², ground contact 1024×2048, signage atlas 2048², advert
  1024×1432, light diffuser 512²
- `blender/source/textures/urban-decals/urban-decal-library.png` and `.json`: a
  reusable 1024² atlas of ten street-ephemera decals (torn paper, shipping
  label, removed sticker, adhesive residue, event sticker, marker tag,
  scratched initials, tape residue, sticker remnant, chewing gum)
- `public/assets/models/bus-shelter/preston-bus-shelter-textured.glb` and
  `preston-busstop-textured.glb` (about 2 MB)
- `renders/bus-shelter-texture-pass/01`–`12`, the brief's validation views,
  plus `13-ground-contact` for the plinth and foot contact

Channel conventions:

- Metallic/roughness/occlusion are packed as glTF ORM.
- Glass and ground-contact base-colour alpha is opacity.
- Opaque shelter materials store rain exposure in base-colour alpha as
  `0.2 + 0.8 × wet`. The floor stops WebP discarding colour under zero alpha.

Runtime (`src/world/busShelterMaterials.ts`):

- Glass blends premultiplied, so baked film and grime dim only the glass's own
  diffuse layer while reflections add at full strength, as real glass does.
- A small painted night-street environment gives the glass and wet surfaces
  something to reflect without a real-time reflection pass.
- `setBusShelterWetness(0–1)`, or `?wet=0.8` in the URL, drives the wet
  variant. Exposure-masked surfaces darken by porosity and lose roughness,
  while roof-sheltered faces stay dry, and rivulets and droplets form on the
  lower glass.
- Both shelters clone one loaded model, so texture memory is shared.

Rebuild from the repository root (about 15 minutes; `--bake-cache` makes later
weathering-only iterations take a few minutes, and is valid only while geometry
and UVs are unchanged):

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python blender/scripts/createBusShelterTextured.py -- --bake-cache /tmp/bus-shelter-bake
```

Pass `--stage textures` or `--stage renders` to run one half. The render stage
swaps in a validation-only glass shader that matches the runtime blending;
the exported material stays a plain glTF Principled BSDF.

## Geometry and material boundaries

The asset includes slender rear and side framing, a shallow rounded roof,
separate rear/left/right glass panels, the minimal orange-red resting rail,
timetable and No Smoking backplates, blank decal surfaces, under-roof fixture
geometry, and the projecting right-hand advert housing. The trolley has an open
wire basket, tubular frame, handle, four independent caster roots, and a short
chain.

The texture pass replaced the shelter's placeholder material IDs with
`MAT_BusStop_DarkMetal`, `_Roof`, `_Glass`, `_RedRail`, `_Signage`, `_Advert`,
`_Light` and `_GroundContact`. Trolley metal, plastic, wear and grime remain
outstanding, under the original `MAT_Trolley_*_PLACEHOLDER` IDs.

The old photographic prototype is retained beneath
`blender/source/bus-shelter/legacy/` for comparison only. Its cropped working
textures remain under `blender/source/textures/bus-shelter/` and are not used by
the current runtime GLB.
