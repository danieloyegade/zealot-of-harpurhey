# North Road Preston bus shelter

## Asset status

The game uses the geometry-first North Road, Preston shelter and shopping
trolley. This is the review-approved clay/material-ID pass: proportions,
silhouette, hierarchy and transparent glazing are present; final decals, PBR
materials and local light emission are deliberately deferred.

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

The game loads `preston-busstop-reference.glb`, which contains the independently
parented trolley in the photographed position. `preston-bus-shelter.glb` and
`preston-shopping-trolley.glb` are available for later independent placement.

## Geometry and material boundaries

The asset includes slender rear and side framing, a shallow rounded roof,
separate rear/left/right glass panels, the minimal orange-red resting rail,
timetable and No Smoking backplates, blank decal surfaces, under-roof fixture
geometry, and the projecting right-hand advert housing. The trolley has an open
wire basket, tubular frame, handle, four independent caster roots, and a short
chain.

Placeholder material IDs are deliberately stable so the later pass can add:

- dark aged painted metal;
- transmissive, slightly dirty glass;
- exact timetable, No Smoking and `3309 00 83` decals;
- emissive advert artwork and physically derived reflections;
- trolley metal, plastic, wear and grime.

The old photographic prototype is retained beneath
`blender/source/bus-shelter/legacy/` for comparison only. Its cropped working
textures remain under `blender/source/textures/bus-shelter/` and are not used by
the current runtime GLB.
