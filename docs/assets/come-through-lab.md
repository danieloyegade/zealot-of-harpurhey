# Come Through Lab, 84 Silk Street

This asset is a metric, geometry-only reconstruction of the Come Through Lab
frontage at 84 Silk Street, Manchester, inferred from the photographs in
`references/architecture/come-through-lab/`. It contains no final textures,
CTL branding, the green instruction panel, QR code, graffiti, or wood grain.

## Deliverables

- Approval blockout: `blender/source/come_through_lab_blockout.blend`
- Editable geometry source: `blender/source/come_through_lab.blend`
- Deterministic rebuild script: `blender/scripts/createComeThroughLab.py`
- Three.js runtime models:
  - `public/assets/models/come_through_lab.glb` — building only
  - `public/assets/models/ctl_dropbox.glb` — drop box, independently placeable
  - `public/assets/models/ctl_dropoff_props.glb` — supply holder + envelope + pencil
- Blockout renders: `renders/come-through-lab-blockout/`
- Final geometry renders: `renders/come-through-lab/`

Regenerate everything from the project root with:

```sh
/Applications/Blender.app/Contents/MacOS/Blender \
  --background --python blender/scripts/createComeThroughLab.py
```

## Architecture and scale

The estimated envelope is **9.7 m wide × 6.0 m deep**, reaching **7.15 m** to
the parapet cap (ground floor 3.50 m, upper floor 3.40 m, parapet 0.25 m). One
Blender unit equals one metre; Z is vertical, ground is Z 0, and the street
elevation faces -Y.

The original frontage bay (door, two ground windows, three upper windows)
sits at the west end of the model. Per review, the model extends east past the
second ground window by the same span as the whole original bay, ending in a
projecting glazed balcony bay rather than blank wall, matching the wider
reference photography. Recognition-critical geometry includes opening-aware
masonry (the wall is punched for real openings, not a solid box with fixtures
laid over it), the arched timber entrance with a heavy stone surround, dense
security grilles over both ground windows, raised `84` address lettering,
sash-framed upper windows, and downpipes/service runs on the facade.

The drop box and supply holder (envelope + pencil) are exported as separate
GLBs and must never be fused into the building mesh — the brief's 24-hour
drop-off requirement means both need to stay independently placeable/usable.

## Gameplay anchors

The GLB exports the following transform nodes for game integration:

- `CTL_EntranceTriggerAnchor` (building GLB)
- `CTL_DropBox_InteractAnchor` (drop box GLB)

No runtime code reads these yet — placement in `src/world/createWorld.ts` uses
a fixed rotation + bounding-box-derived offset instead (see below). Wiring
delivery/interaction logic to these anchors is future work for
`src/interaction/`/`src/delivery/`, both currently empty stubs.

## Game integration

Come Through Lab is loaded by `src/world/createWorld.ts`'s
`addComeThroughLabModel`, dispatched from `addBuildingLocation` for
`location.id === 'come-through-lab'`. All three GLBs load in parallel via
`Promise.all`. The building's Blender -Y frontage imports facing +Z, so it is
rotated 90° to face east; its world position is then derived from its actual
post-rotation bounding box so the shopfront face sits flush with the plot's
east edge (`location.x + location.width / 2`, since `width` is always the
east-west extent in `worldLayout.ts` regardless of `front`), not just the
plot centre. The
drop box and supply holder share the exact same rotation and the exact same
computed position delta as the building (rather than their own bounding
boxes), since all three were authored in one shared Blender scene and only
split into separate GLBs at export time — copying the building's final
`position` after matching rotation reproduces their authored placement next to
the entrance without needing to hand-tune offsets per prop.

`worldLayout.ts`'s plot entry was corrected from the original placeholder box
(10 × 10 × 8 m, `status: 'placeholder'`) to the asset's real footprint —
`width: 6.0` (east-west), `depth: 9.7` (north-south), `height: 7.15`,
`status: 'geometry-wip'` — at `x: -37` so the shopfront sits on the same -34
building line as Village Books and Coral. The placeholder cosmetic
facade/style lookups in `createWorld.ts` (blockout brick texture, sign-colour
map, graffiti-panel list) had their now-unreachable `'come-through-lab'`
entries removed, since the dedicated GLB branch returns before any of that
code runs.

## Runtime validation

Verified by GLB reimport after each Blender regeneration: required hero
collections/anchors present, model bounds non-degenerate, and a clean
`npm run build`.

Final PBR materials, weathering, CTL branding, the green instruction panel,
QR code, graffiti, and gameplay/delivery logic remain separate future passes.
