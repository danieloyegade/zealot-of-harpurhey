# Real Camera, Sevendale House

This asset is a metric, geometry-only reconstruction of Real Camera at
Sevendale House (the Dale Street / Lever Street corner), inferred from the
photographs and Street View captures in
`references/architecture/real-camera/EXT/` and the brief in
`references/architecture/real-camera/13_Real_Camera.txt`. It is a hero
architectural asset — ornate red sandstone/terracotta facade, not a flat
shopfront — and still contains no final textures, stone colour/porosity,
typography, weathering, graffiti, window reflections, or shop stock.

## Deliverables

- Approval blockout: `blender/source/real_camera_blockout.blend`
- Editable geometry source: `blender/source/real_camera.blend`
- Blockout rebuild script: `blender/scripts/createRealCameraBlockout.py`
- Detailed/ornament rebuild script: `blender/scripts/createRealCamera.py`
  (imports the blockout script as a module and builds on its reviewed layout,
  the same way `createTheHive.py` builds on `createTheHiveBlockout.py`)
- Three.js runtime model: `public/assets/models/real_camera.glb`
- Blockout-stage GLB (kept for comparison): `public/assets/models/real-camera-blockout.glb`
- Blockout renders: `renders/real-camera-blockout/`
- Final geometry renders: `renders/real-camera/`

Regenerate the ornament pass (which regenerates the blockout internally, then
adds detail) from the project root with:

```sh
/Applications/Blender.app/Contents/MacOS/Blender \
  --background \
  --python blender/scripts/createRealCamera.py
```

Regenerate only the blockout with:

```sh
/Applications/Blender.app/Contents/MacOS/Blender \
  --background \
  --python blender/scripts/createRealCameraBlockout.py
```

## Architecture and scale

The estimated envelope is **15.15 m Dale Street frontage × 10.0 m depth ×
14.2 m to the parapet** (ground floor 4.2 m, three upper storeys, cornice),
with a rounded corner mass wrapping onto a short Lever Street return wing.
One Blender unit equals one metre; Z is vertical, ground is Z = 0, and the
Dale Street frontage faces -Y. These are inferred, not surveyed, dimensions —
estimated from shopfront/door proportions and storey counts in the
photography, the same caveat as every other hero-location asset in this
project.

Ground-floor rhythm (west to east): rounded corner mass carrying the
projecting corner clock, a narrow plain secondary door, a stone pier, the
Real Camera Shopping Centre & Gallery entrance (real stepped stairs, double
glazed doors, architrave), a second pier, the Real Camera shop itself — its
red awning holds the genuine customer entrance: two glass doors with a
rolled-up shutter housing above them, not an opaque shutter panel — a third
pier, and an adjacent shuttered unit. Two downpipes run the full facade
height (by the shop's east pier and by the corner). All three upper floors
carry plain rectangular recessed windows, separated by stepped string
courses, with a dentilled cornice at the roofline.

Corrected after Daniel's photo-by-photo review of the first ornament pass:
the main shop's ground-floor opening was originally modelled as a single
opaque shutter panel, when the street photography actually shows the shutter
raised during opening hours to reveal a genuine two-door entrance — fixed.
The secondary door between the corner and the Gallery, and the downpipes
running the facade, were both missing entirely from the first pass — both
added. The building's frontage widened by 1.5 m (west side) to make honest
room for the secondary door bay rather than compressing it. Floor 1 windows
were originally modelled with round-arch heads; a second review round
caught that no floor of this building actually has arched openings in the
reference photography (a generic brief allowance, not something this
specific building shows) and that the arch geometry's own keystone ornament
was rendering as an unexplained "circle with a square in it" artifact —
floor 1 is now plain rectangular, matching floors 2-3.

Ornament added in the detailed pass (`createRealCamera.py`) beyond the
blockout: pilaster plinths/necking/abaci, the cornice dentil course, arch
keystones, window console brackets and lintel lips, ground-floor rustication
bands, the Gallery entrance architrave and keyblock, and decorative brackets
on the hanging sign and corner clock. Fine carving, stone joints, and surface
weathering remain deferred to a later texture/normal-map pass, per the
brief's own restraint rule (§5, §46).

## Gameplay anchors

The GLB exports the following transform nodes for game integration:

- `RC_EntranceAnchor`
- `RC_InteriorSpawnAnchor`
- `RC_ExitAnchor`

## Game integration

Not yet wired into `src/world/createWorld.ts`. A placeholder `'real-camera'`
colour scheme already exists there (`#ddd1ae` stone, `#8c2a22` awning red) at
world position `(-11.5, 69.75)` per `docs/assets/cass-art.md`, but no GLB load
call references this asset yet — that's the next integration step once this
geometry pass is approved.

## Runtime validation

The detailed source contains **269 mesh objects** totalling approximately
**3,836 triangles** before Blender-only bevel modifiers. It has been
round-trip built and rendered in Blender 5.2.1 LTS to verify the geometry
survives export.

Final PBR materials, red sandstone colour/porosity, typography (the red
awning brand surface, the Gallery sign, the hanging sign face, the corner
clock face), weathering, graffiti, window reflections, shop stock, and the
Three.js integration above remain separate future passes.
