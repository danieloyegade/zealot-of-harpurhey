# Spice Cabin

A reference-led, textured reconstruction of the Spice Cabin takeaway end unit,
built from the photographs and production brief in
`references/architecture/spice-cabin/`. It preserves the observed tan commercial
brick, rounded faux-log lower cladding, photographed sign identity, blue framing,
cream end pier, recessed glazing/door, black bollards, upper conduit and simplified
anti-climb silhouette rather than generalising the location into a generic takeaway.

## Deliverables

- Rebuild script: `blender/scripts/createSpiceCabin.py`
- Editable master: `blender/source/spice-cabin.blend`
- Generated texture sources: `blender/source/textures/spice-cabin/`
- Three.js runtime model: `public/assets/models/spice-cabin.glb`
- Six validation renders: `renders/spice-cabin/`

Regenerate everything from the repository root with:

```sh
/Applications/Blender.app/Contents/MacOS/Blender \
  --background \
  --python blender/scripts/createSpiceCabin.py
```

The script creates deterministic brick and timber albedo/roughness textures and a
sign derivative cropped from the supplied `spice-cabin-manchester.jpg`. Reference
photographs are read-only inputs. Runtime textures are embedded in the GLB.

## Scale and orientation

- Nominal facade: **6.80 m wide × 1.10 m deep × 4.25 m high**, with the security
  silhouette extending above the masonry.
- One Blender unit is one metre; ground is `Z = 0`.
- The frontage faces local **-Y**, consistent with the current food-stand and hero
  frontage authoring convention.
- The asset is a modular building-edge facade, not an invented parade or street.
- Dimensions are inferred from photography and standard door/bollard sizes, not a
  survey.

## Runtime structure

The master separates the logical groups requested by the brief:
`SPICE_structure`, `SPICE_brick_wall`, `SPICE_cream_pier`, `SPICE_sign`,
`SPICE_blue_fascia`, `SPICE_window_frames`, `SPICE_glass`, `SPICE_door`,
`SPICE_log_cladding`, `SPICE_bollards`, `SPICE_security_wire`, `SPICE_pipework`,
`SPICE_alarm_fixtures`, `SPICE_interior_cards`, and `SPICE_anchors`.

The rounded timber is genuine low-segment relief with a continuous backing layer,
not a striped flat panel. Brick relief remains texture-led for runtime efficiency.
The anti-climb assembly uses sparse curve geometry to preserve the roof silhouette
without modelling dense concertina wire.

Review pavement, railing and the 1.78 m scale witness live in
`SPICE_review_only` and are excluded from the GLB, as are all validation cameras
and lights.

## Materials and lighting

The concise glTF-compatible material set includes aged tan brick, weathered log
cladding, the photographed sign, weathered blue framing, cream concrete, dark
pipe/bollard metal, security metal, shopfront glass, interior cards, warm interior
suggestion and a restrained red window-sign treatment. The two authored surface
sets use separate albedo and roughness maps.

The GLB contains no real-time lights. Three authored light anchors allow the game
to join the existing nearest-hero-light policy later:

- `SPICE_LightAnchor_Window`
- `SPICE_LightAnchor_Door`
- `SPICE_LightAnchor_Sign`

Two interaction anchors are also exported: `SPICE_EntranceAnchor` and
`SPICE_DeliveryAnchor`.

## Validation and placement status

The build script checks the identifying meshes and anchors, applies transforms,
and reports approximately **2,820 triangles** across **66 runtime mesh objects**.
The six required renders cover neutral daylight, grazing daylight, restrained night
lighting, brick close-up, rounded timber close-up and a straight-on elevation.

The asset has not been placed in `worldLayout.ts` and has no runtime collision box
yet. Placement should be decided against actual neighbouring GLB bounds rather than
nominal plot centres; a single facade-envelope box will be sufficient unless the
bollards are made separately collidable.
