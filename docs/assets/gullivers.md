# Gulliver's architectural reconstruction

## Deliverables

- Editable source: `blender/source/harperhey-gullivers.blend`
- Deterministic build script: `blender/scripts/createGullivers.py`
- Three.js runtime asset: `public/assets/models/harperhey-gullivers.glb`
- Review renders: `renders/gullivers-greybox/`

Regenerate all deliverables from the project root with:

```sh
/Applications/Blender.app/Contents/MacOS/Blender \
  --background --factory-startup \
  --python blender/scripts/createGullivers.py
```

## Reconstruction scope

The asset is a geometry-first reconstruction derived from all photographs in
`references/architecture/gullivers/`. It models the complete visible corner
building: the Oldham Street front, the Whittle Street side return, a restrained
rear wall, flat roof, parapet and chimney. Adjacent buildings, street furniture
and the pub interior are outside this pass.

The estimated architectural envelope is approximately **7.4 m wide × 16.0 m
deep × 11.45 m to the parapet**, with the chimney reaching 12.18 m. These are
photogrammetric estimates based on doorway and storey-scale cues rather than a
survey.

Recognition-critical geometry includes:

- the three-storey narrow corner silhouette and chamfered street corner;
- the wrapped green pub frontage with projecting tiled piers and cream inlays;
- recessed ground-floor glazing, clerestories and panelled doors;
- the deep fascia, layered cornice, dentils and simplified corbels;
- three Oldham Street first-floor arches and five Whittle Street arches;
- recessed upper glazing, mullions, sills, arch trim and pierced head details;
- upper horizontal courses, parapet/coping, chimney and hanging sign structure.

No image textures, procedural surface textures, normal maps or baked lighting
are used. Flat placeholder materials identify brick, green trim, tiled frontage,
cream joinery, glass, doors, roof and metal so later PBR materials can be
assigned cleanly.

## Game integration status

The geometry-first GLB is loaded directly by `src/world/createWorld.ts`. The old
procedural Gulliver's building, fallback generation and façade styling data have
been removed completely. It is positioned at the east-side plot and rotated so
the Oldham Street frontage faces west. The model remains explicitly labelled as
a geometry WIP in development builds: **final textures have not yet been
produced or applied**. Its authored dimensions are used for placement and
collision. Vinyl Exchange now occupies the north-row plot beside Renae,
leaving the complete Whittle Street return clear.

## Runtime optimisation

The editable Blender file retains 373 clearly named component meshes grouped in
eight architectural collections. Export builds eight consolidated,
multi-material runtime meshes. The validated GLB contains **15,264 triangles**,
18 material definitions and an approximately **7.99 × 16.59 × 12.18 m** total
bounding box including cornice, hanging sign and chimney projections.

The GLB was round-trip imported into Blender 5.2.1 after export to verify that
all eight runtime meshes, material regions, ground contact and dimensions
survive serialization.
