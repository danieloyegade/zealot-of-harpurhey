# North Road Preston bus shelter

## Asset status

The game uses the texture pass of the North Road, Preston shelter
(`preston-busstop-textured.glb`): the approved geometry, unchanged, carrying
baked PBR weathering, reconstructed signage and an emissive advert. The
shopping trolley was rebuilt from traced landmarks in Daniel’s supplied
photograph (see "Trolley geometry and materials" below) and
now carries its own restrained steel/rubber material atlas.

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
wire basket, tubular A-frame undercarriage, handle, four independent caster
roots, and a short chain.

The texture pass replaced the shelter's placeholder material IDs with
`MAT_BusStop_DarkMetal`, `_Roof`, `_Glass`, `_RedRail`, `_Signage`, `_Advert`,
`_Light` and `_GroundContact`. The trolley has its own geometry-preserving
material pass described below.

## Trolley geometry and materials

The 2026-09-23 photo-traced reconstruction supersedes the earlier written-brief
tray and near-vertical supports. The photograph is authoritative again. Its
supplied copy is preserved in `renders/trolley-geometry/reference.jpg` (1818 ×
1456); `trace-landmarks.json` records the measured near-side basket corners,
frame bends, wheel centres and handle position. `TROLLEY_TRACE` in
`createBusShelter.py` drives the geometry from those pixel positions.

- Each side has one continuous bent tube, rising from the rear caster to a
  short saddle under the rear of the basket, then sweeping diagonally down
  toward the front caster. The centre remains open, with no horizontal axle
  bars or crossed braces. Frame radius is 12.5 mm; wire radius is 2.2 mm.
- Wheel-centre spacing is 308 photo pixels (0.948 m at the inferred scale).
  Their positions follow the photo rather than the basket corners. Small
  casters have paired open forks and touch the ground at Z=0.
- The basket has 27 thin ribs on each long side, 12 at each end, two horizontal
  wire bands, structural edge rails and an actual crossed-wire floor. The rear
  wall is substantially deeper than the previous tray. The handle is at -Y
  (left in the validation side view), and the nose is at +Y.
- Relative side-profile measurements follow the photograph, including its
  descending rim and almost upright nose. Approximate ratios/ASCII drawings
  in the written brief are not substituted for those visible edges. Absolute
  scale and the partially hidden width remain inferred from one photograph.
- Existing trolley materials, shelter textures and scene lighting are retained.

Validation is deliberately separate from integration:

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python blender/scripts/reviewTrolleyGeometry.py -- --stage validate
# Inspect the structural/photo overlay and black-on-white side silhouette.
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python blender/scripts/reviewTrolleyGeometry.py -- --stage integrate
```

The validation script saves a standalone editable
`blender/source/bus-shelter/preston-shopping-trolley.blend`, a structural
silhouette, structural and wire overlays on the photograph, and completely
black side/three-quarter renders against white under `renders/trolley-geometry/`.
Integration replaces only the trolley hierarchy in the four existing shelter
source scenes and exports the standalone, combined and textured combined GLBs.
It preserves the shelter's existing UVs/materials/maps without rebaking them.
Earlier whole-shelter review PNGs predate this geometry correction; the trolley
review directory is the current geometry evidence.

Daniel approved the traced wireframe in this task. The material pass keeps all
176 mesh vertex/topology signatures fixed and adds one shared 1024² base-colour
atlas and one 1024² ORM atlas (occlusion, roughness, metallic):

- `MAT_Trolley_GalvanisedSteel`: cool-neutral galvanised metal, subtle zinc
  mottling in colour/roughness, slightly smoother handled grip, and light dirt
  near ground level and contacts.
- `MAT_Trolley_WornBracket`: darker metal on the caster forks/swivels, with
  restrained accumulated dirt.
- `MAT_Trolley_Tyre`: matte charcoal rubber with fine tonal variation and dust.

No geometry displacement, artificial opacity, heavy rust or new scene lights.
Fine wire remains actual opaque geometry with open gaps. The existing runtime
bus-shelter material policy already supplies photographic filtering and the
night environment to these materials; no new shader or light is introduced.

`blender/scripts/textureTrolley.py` reuses `surfaceWeathering.py` to unwrap a
unique atlas, bake world position/normal/contact buffers on CPU, author physical
weathering and build glTF-compatible image materials. Maps, UV layout and mesh
hashes are under `blender/source/textures/bus-shelter/trolley/`. Material review
renders are in `renders/trolley-materials/`.

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python blender/scripts/textureTrolley.py -- --stage bake
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python blender/scripts/textureTrolley.py -- --stage renders
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python blender/scripts/textureTrolley.py -- --stage integrate
```

Integration changes only UVs/materials in detailed sources; the structural
blockout stays untextured. The shared geometry builder restores the saved atlas
on subsequent rebuilds and rejects mismatched geometry rather than silently
using stale UVs. If geometry is deliberately revised, regenerate the standalone
source without the saved atlas, rebake it, then integrate the revised result.

The old photographic prototype is retained beneath
`blender/source/bus-shelter/legacy/` for comparison only. Its cropped working
textures remain under `blender/source/textures/bus-shelter/` and are not used by
the current runtime GLB.
