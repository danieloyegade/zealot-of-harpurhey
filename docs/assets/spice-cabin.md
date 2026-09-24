# Spice Cabin

A reference-led reconstruction of the Spice Cabin takeaway end unit, built from
the photographs and production brief in
`references/architecture/buildings/spice-cabin/` (moved from
`references/architecture/spice-cabin/` on 2026-09-14).

Rebuilt on 2026-09-14 (Claude). The first pass (2026-09-12) had a skewed photo
crop as its sign, flat untiled-looking brick with no normal map, and striped
cylinders for the cladding; it failed the brief's own revision triggers.

## Reading the references

- **Photo 1** (`7cf7a339-….jpg`) is the **gable**, not the front: tan brick
  above, dragfaced brown brick below, the cream pier's return at its right edge,
  a newer sign with the phone number and a pale tube on stand-offs above it.
- **Photos 2 and 4** show the shopfront with the older sign: no phone number,
  reds faded towards pink.
- The LED window sign reads "ΓPIED CHICKEN" in both front photographs because of
  dead LEDs. The asset keeps the fault.

## Deliverables

- Build script: `blender/scripts/createSpiceCabin.py`
- Geometry: `blender/scripts/spiceCabinGeometry.py`
- Sign, LED and interior artwork: `blender/scripts/spiceCabinArtwork.py`
- Editable master: `blender/source/spice-cabin.blend`
- Generated maps: `blender/source/textures/spice-cabin/`
- Runtime model: `public/assets/models/spice-cabin.glb`
- Validation renders: `renders/spice-cabin/01`–`11`

Rebuild from the repository root (about 10 minutes cold; `--bake-cache` reuses
bakes while geometry and UVs are unchanged, `--stage textures|renders` runs one
half, `--only 04,05` re-renders selected views):

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python blender/scripts/createSpiceCabin.py -- --bake-cache /tmp/spice-cabin-bake
```

## Scale, orientation and dimensions

- One Blender unit is one metre, Z up, ground at Z = 0.
- Origin at the centre of a 6.2 × 7.0 m footprint.
- Shopfront faces **-Y**, gable faces **-X**. The +X side is the party wall with the
  neighbouring unit and has no exterior face.
- Heights are photographic estimates scaled from the ~2.0 m door opening and
  75 mm brick courses:

| Element | Z (m) |
| --- | --- |
| Concrete upstand | 0–0.10 |
| Loglap cladding (13 boards) | 0.10–1.12 |
| Glazing | 1.12–1.95 |
| Timber head | 1.95–2.02 |
| Blue fascia (boxed, 0.22 m proud of the pier) | 2.02–2.48 |
| Front sign | 2.52–3.56 |
| Cream band | 3.62–4.02 |
| Parapet brick | 4.02–4.76 |
| Green coping | 4.76–4.84 |
| Rotary anti-climb bar | 5.00 |

- Gable sign: 4.60 × 1.00 m at Z 2.62–3.62.
- Gable brick changes from brown to buff at the course nearest 3.35 m.

## Runtime structure

Hierarchy: `SPICE_CABIN` → group empties → meshes. The groups are:

- `SPICE_structure`
- `SPICE_brick_wall`
- `SPICE_cream_pier`
- `SPICE_sign`
- `SPICE_blue_fascia`
- `SPICE_window_frames`
- `SPICE_glass`
- `SPICE_door`
- `SPICE_log_cladding`
- `SPICE_bollards`
- `SPICE_security_wire`
- `SPICE_pipework`
- `SPICE_alarm_fixtures`
- `SPICE_interior_cards`
- `SPICE_ground_contact`
- `SPICE_anchors`

Notes on geometry:

- **Loglap boards** have a genuine convex, lipped profile. Brick relief is
  texture-led.
- **Anti-climb:** each rotor is three offset five-vane stars of closed
  tetrahedra, merged per run. Rotors reach up to 0.16 m with broad vanes so the
  run reads as the heavy black silhouette photographed.
- **Downpipe:** 100 mm pipe under a 0.36 m hopper head.
- **Door:** stands open inward, as photographed.
- **No hidden faces:** wall tops under the coping and the party wall are never
  built.

Anchors (no lights are exported):

- `SPICE_EntranceAnchor`
- `SPICE_DeliveryAnchor`
- `SPICE_LightAnchor_Window`
- `SPICE_LightAnchor_Door`
- `SPICE_LightAnchor_Sign`
- `SPICE_LightAnchor_SideSign`
- `SPICE_LightAnchor_LEDSign`

The review stage is excluded from the GLB. It contains pavement, kerb, road,
grass, the galvanised railing, a white concrete bollard, the neighbour's edge
and a 1.78 m scale figure.

## Texture pass

Every textured material gets a unique, density-consistent UV atlas, so brick
and timber cannot tile. The pass then:

1. Bakes world position, normal, object id, AO and convexity
   (`surfaceWeathering.bake_buffers`). The brick and blue bakes are upsampled
   2×, which is exact on their planar faces.
2. Authors each surface in world space:
   - **Brick:** stretcher bond on real 225 × 75 mm modules. Per-brick colour
     comes from buff and brown palettes, with kiln flashing, speckle and
     dragface. Joint widths vary, mortar is recessed 6.5 mm, and faces carry
     pores, tilt and chipped arrises.
   - **Loglap timber:** grain follows each piece (vertical on mullions, jambs
     and the door), with per-board colour, knots and checks.
3. Adds weathering from causes rather than grunge:
   - coping run-off and rust bleed from bracket fixings;
   - drip lines under the gable sign;
   - splash zone, algae and salts at the wall foot;
   - flaking and scuffs on the pier;
   - sun-chalked coping and band top;
   - chips and hand wear on the blue posts;
   - sun-silvered sills and board tops;
   - a white bumper-paint smear on one bollard;
   - galvanising bloom;
   - glass film, squeegee arcs, palm prints and sticker residue by the door;
   - stickers on three bollards;
   - an analytic ground-contact decal: wall-base grime, bollard rust rings,
     damp at the downpipe shoe, glossy puddles, gum, cigarette ends and
     takeaway litter (wrappers, receipts, napkins, crushed cans).
4. Sets the signs in Marker Felt Wide through the bus shelter's `PrintCanvas`,
   at letter positions measured on a perspective-rectified copy of photo 1.
   The printed face is far heavier than Marker Felt, so the rendered coverage
   is emboldened (`TITLE_WEIGHT`), the chilli is pulled in tight between P and c,
   and the flame dots the i of CaBiN.
   Outlines, drop shadows, the chilli, the flame, the printed round-log
   background and the sawn log-end cut-outs are drawn in numpy. Nothing is
   copied from the photographs. The front sign is aged harder, but its reds and greens stay
   saturated, as in photo 4.
5. Draws dot-matrix LEDs for the window sign, including its dead LEDs.
   Menu boards and fridge contents are illegible by design, so no copy is
   invented.

Materials (glTF, WebP textures, single-sided):

| Material | Contents |
| --- | --- |
| `MAT_brick_aged_tan` | Base 4096, normal 2048, ORM 1024 (≈1.7 mm/texel) |
| `MAT_cream_painted_concrete` | Pier, band, coping, boarding, plinth, tubes, alarm, CCTV |
| `MAT_blue_painted_frame` | Fascia and posts |
| `MAT_log_cladding_weathered` | Boards, sills, head, mullions, jambs, door leaf |
| `MAT_dark_metal` | Bollards, downpipe, hopper, anti-climb, galvanised brackets and clips, threshold, counter top, LED case (merges the brief's black-bollard, dark-pipe and security-metal materials) |
| `MAT_sign_printed_wood` | alphaMode MASK for the log-end cut-outs |
| `MAT_glass_shopfront` | alphaMode BLEND, dark film |
| `MAT_interior_dark` | Interior surfaces |
| `MAT_emissive_signage` | LED sign, fridge front, menu boards, ceiling panels, tube diffusers |
| `MAT_ground_contact` | alphaMode BLEND |
| `MAT_roof_felt` | Untextured |

ORM packing is glTF standard. Opaque base-colour alpha is 1; no wetness mask is
stored, unlike the bus shelter.

## Validation

The build checks the identifying meshes, anchors and UVs.

Measured on 2026-09-16:

- 98 meshes, 11,788 triangles, 11 materials.
- GLB ≈7.6 MB, of which images are 6.7 MB and brick is ≈4.1 MB.
- Materials are single-sided.

**Texture budget:** this exceeds `docs/VISUAL_LANGUAGE.md`'s budget (512 px
landmark façades, 1024 maximum when justified). The brief's top priorities are
brick and timber at close player range, so the atlases were sized for that.

To export a budget-compliant variant, lower the base/normal/ORM sizes in
`ATLASES` and `sign_maps`; the authored surfaces are resolution-independent.
Which variant the game uses is an open question for Daniel.

Renders:

1. neutral overcast
2. grazing daylight along the shopfront
3. night with interior, sign-tube and LED practicals
4. brick close-up at the gable sign (raked)
5. loglap close-up (raked)
6. straight-on elevation
7. gable sign in sun (photo 1 match)
8. photo 4 viewpoint match
9. gameplay-camera distance at night
10. roof edge and services
11. shopfront junctions

Renders 1, 7 and 8 are the comparisons to make against the photographs.

## In the game

`createWorld.ts` `addSpiceCabinModel` loads the full textured GLB into the
`spice-cabin` plot.

**Scale:** in the game it is enlarged by `SPICE_CABIN_SCALE` = 1.5 in width and
height, so it sits with the other South Road buildings, as the bus shelter runs
at 1.3. Depth uses `SPICE_CABIN_DEPTH_SCALE` = 10/7 to reach 10 m (it was
matched to the Off-Licence placeholder, since removed); the 5% horizontal
squeeze on the gable is not visible.

The GLB itself stays at real-world scale. The plot is `finished` at the scaled
9.3 × 10 × 7.65 m envelope, centred on (12.35, 49).

If either factor changes, update the `worldLayout.ts` envelope to match. Bollard
collision, light offsets, light ranges and activation radii follow the
constants. Light intensity follows the square of the main scale.

The ground-contact decal's outer edge now reaches about 1 m past the kerb onto
the carriageway.

Placement and collision:

- **Orientation:** the asset's -Y shopfront already faces the plot's south
  frontage after glTF conversion, so there is no rotation.
- **Building line:** the shopfront sits on the Z = 54 South Road line.
- **Party wall:** the east side has no exterior face. The Off-Licence
  placeholder that hid it was removed on 2026-09-24, so `addSpiceCabinPartyWall`
  closes it with a 0.3 m sooty brick skin at X = 17 (full depth and height, with
  collision). Anything built there later can replace that skin.
- **Height:** the model stands at `pavementTopAt` height, so the ground-contact
  decal clears the pavement flags.
- **Collision:** one solid footprint (interiors are not walkable yet) plus four
  16 cm bollard boxes.

Materials and light:

- `applySpiceCabinTexturePolicy` in `busShelterMaterials.ts` shares the bus
  shelter's texture-pass runtime policy. It applies photographic texture
  filtering and the painted night-street environment map. Shop glass gets the
  premultiplied glass shader, and the ground decal gets polygon-offset blending.
- Glass: Spice Cabin passes stronger environment reflection (4.2) and a
  grazing-angle sheen to the shared glass shader, over a darker baked film
  (alpha 0.74) and a darkened interior, so the windows read as tinted glazing.
- Emissives: the shared `MAT_emissive_signage` is held to 0.25 ×
  `emissiveMultiplier`, so the menu boxes, fridge and ceiling panels glow
  without blooming out behind the glass. The LED window sign and the tube
  diffusers get a full-strength clone.
- Lights: the world is moonlit blue, so without practical light the brick,
  cream band and printed signs read grey-blue. The blue-grey in-game look
  matches a Blender render under the game's hemisphere and moon. Two
  `location-relevance` installations hang off the GLB's anchors:
  - **Shopfront** (radius 14): the sodium interior spill at
    `SPICE_LightAnchor_Window`, plus a warm tube wash in front of
    `SPICE_LightAnchor_Sign`.
  - **Gable sign** (radius 12): a warm tube wash at `SPICE_LightAnchor_SideSign`.

  The shopfront installation uses two point lights of the per-quality budget,
  and the gable sign one.

Development views: `?view=spice-cabin` (front) and `?view=spice-cabin-gable`.
