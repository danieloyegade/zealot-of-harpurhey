# Technical Direction

## Current decisions

- **Renderer:** Three.js
- **Language:** TypeScript
- **Build tool and development server:** Vite
- **3D asset creation:** Blender
- **Editable 3D masters:** `.blend`
- **Primary runtime 3D asset format:** `.glb` (binary glTF)
- **Version control:** Git and GitHub
- **Deployment:** static browser build
- **Target public path:** `/zealot-of-harperhey/`
- **Initial hosting:** GitHub Pages, through the existing website
- **Possible later asset hosting:** Cloudflare R2, if asset volume or delivery requirements justify it
- **Initial platform:** desktop browser MVP
- **Architecture:** lightweight, with no unnecessary frameworks

Development-only references, source photography, `.blend` masters, and renders live outside `public/` so Vite does not copy them into the production build. Only runtime-ready files belong in `public/assets/`.

## Playable prototype architecture

- `main.ts` owns renderer and scene initialisation, raw render timing, and the fixed-step game loop.
- `FixedStepClock` advances gameplay at 60 Hz with bounded catch-up and explicit extreme-gap resets.
- `InputController` tracks keyboard movement, running, and click-drag camera input.
- `AmbientAudio` layers the local street recording beneath the current ambient music track. Browser autoplay rules mean audio begins on the first key press or pointer interaction; `M` toggles music without muting the street layer.
- `PlayerController` owns the primitive player representation, velocity, facing direction, movement state, and collision movement.
- `ThirdPersonCamera` owns orbit angles, camera-relative movement direction, and smoothed following.
- `createWorld` builds the canonical city layout, visual blockouts and its collision description.
- `collision.ts` isolates the lightweight collision routines from player and world rendering code.
- `visualStyle.ts` centralises LOW/MEDIUM/HIGH quality profiles, render scale, DPR policy, texture policy, palette, lighting and post-processing values.
- `worldMaterials.ts` loads the small world texture pack and applies the photographic or graphic filtering profile.
- `worldGraphics.ts` creates low-resolution weathered sign and graffiti materials at runtime.
- `createPostProcessing.ts` owns restrained bloom, display conversion, colour adjustment, quantisation, dithering, film grain and vignette.

### Controls and temporary movement values

- Move forward: `W` or `Arrow Up`
- Move backward: `S` or `Arrow Down`
- Move left: `A` or `Arrow Left`
- Move right: `D` or `Arrow Right`
- Run: hold `Shift` or `Space` while moving
- Orbit camera: click and drag with the primary mouse button
- Hide/show development labels and debug panel: `H`
- Production walking speed: **2.4 metres per second**
- Production running speed: **4.5 metres per second**
- Development walking speed: **3.12 metres per second** (30% faster)
- Development running speed: **7.65 metres per second** (70% faster)

Movement is calculated relative to the camera's horizontal facing direction. Velocity accelerates and decelerates smoothly to give the placeholder movement some weight. There is no jumping.

## Performance and simulation policy

Rendering performance must never change simulation speed.

Gameplay advances through `FixedStepClock` at **1/60 second** per step. Real animation-frame time is accumulated rather than truncated, with at most 16 catch-up steps per rendered frame. A gap above 250 ms is treated as an extreme pause rather than an ordinary slow frame. The accumulator is also reset on document visibility changes, so returning from a background tab never attempts to simulate the entire hidden period.

The camera remains a render-time concern and uses the uncapped real frame delta during ordinary visible frames. This preserves its exponential smoothing without applying pointer orbit input once per gameplay substep.

Development FPS is derived from raw frame time. The development overlay also reports frame milliseconds, draw calls, triangles, active point and spot lights, drawing-buffer size, effective pixel ratio, render scale, resident textures and geometries, shader programs, and the selected quality profile.

The default desktop quality is **MEDIUM**. Use `?quality=low`, `?quality=medium`, or `?quality=high` during development and profiling. Full policy and measured Phase 1 results are documented in `PERFORMANCE.md` and `ENGINE_STABILISATION_REPORT.md`.

Tone mapping defaults to **AgX**, applied by `OutputPass` in linear HDR after bloom and before the display grade. Use `?tonemap=agx`, `?tonemap=neutral`, `?tonemap=aces`, or `?tonemap=off` to compare curves; `off` reproduces the earlier uncurved image. Each curve has its own exposure in `VISUAL_STYLE.render.exposure`, calibrated so midtone brightness matches `off`, so a comparison shows highlight rolloff and colour rather than a brightness change. When a curve is active the grade pass's own exposure is 1, so exposure is never applied twice. Combine with `?view=<name>&quality=high&overlays=off` for repeatable comparisons.

Most environmental illumination in Zealot of Harperhey is intentionally represented using emissive materials, photographic/baked illumination, geometric light cones and fake light pools rather than large numbers of real-time dynamic lights. The normal local-light budget is four on MEDIUM, with five available on HIGH and two on LOW. `LocalLightRegistry` owns the real-time local point lights, keeps multi-light fixtures atomic, includes asset-loaded shop lights in the same budget, and uses one moving public-light proxy for the current streetlight pool. Streetlights do not use real-time spotlights.

### Camera

The prototype uses a 50-degree perspective camera placed 6.8 metres from the player. Horizontal mouse orbit is unrestricted, while vertical pitch is clamped to a modest elevated range. Camera position follows the player using frame-rate-independent exponential smoothing. Pointer lock is not used.

The camera collides with the same obstacle set as the player. Each frame a 0.3-metre sphere is cast from the orbit pivot (1.15 metres above the player's feet) to the smoothed follow position, and the boom is shortened to the first hit, so orbiting beside or inside a building never puts the lens inside a wall. Pulling in is immediate; extending back out eases over roughly half a second. Obstacles are extruded from the ground to their `height`, so the camera can look over anything lower than it. Thin street furniture sets `blocksCamera: false`, so poles and bollards passing behind the player do not make the camera pump.

### Collision

The player is represented on the ground plane by a circle with a temporary radius of 0.38 metres. There is no vertical movement, so anything the player cannot walk under is a two-dimensional footprint in `src/world/collision.ts`:

- **Axis-aligned boxes:** building plots and hand-authored interior walls.
- **Oriented boxes:** benches, bins, utility cabinets and trolleys.
- **Circles:** the fountain basin, tree trunks, shrubs, bollards and streetlight poles.

Props register their footprint where they are placed (`createEnvironmentKit.ts` and `createWorld.ts`), from the same placement data as their meshes, so the two cannot drift apart.

Movement is advanced in slices no longer than half the player's radius. After each slice the circle is pushed back out along the contact normals, which removes only the part of the motion driving into a surface: the player slides along walls and around round obstacles, and cannot step through thin walls. A slice that cannot be resolved, such as a gap narrower than the player, is undone. When a wall absorbs part of a step, the player's velocity is reduced to match, so no stale momentum remains. Movement is clamped to the playable bounds. Before movement, any overlap caused by a changed level layout or development teleport is resolved toward the nearest valid edge, so the player cannot remain trapped inside moved geometry.

Building footprints come from `worldLayout.ts` plots. Where a GLB's solid body-height geometry (0.25–1.7 metres, which excludes canopies the player can walk under) differs from its plot, `createWorld.ts` adds or replaces footprints with measured values. Current cases are Nice Things, the Dreams entrance landing and ramp, the MCR1 shopfront and the Advanced Photo arcade wall. Re-measure when an asset or its placement changes. In development builds, H (or `?overlays=on`) draws every footprint through the scene: magenta outlines also stop the camera, and cyan ones stop only the player.

## Naming conventions

### TypeScript and source files

- Use `camelCase.ts` for modules and utilities, for example `cameraController.ts`.
- Use `PascalCase.ts` only for modules whose primary export is a class or component with the same name.
- Use descriptive English names; avoid unexplained abbreviations.
- Name tests after the source module, using `.test.ts` when tests are introduced.
- Keep directories lowercase and organise them by game domain rather than technical file type.

### Assets

- Use lowercase `kebab-case` filenames, for example `harperhey-bus-stop.glb`.
- Use ASCII letters, numbers, and hyphens only; do not use spaces.
- Add a meaningful variant suffix where needed, for example `brick-wall-wet-albedo.jpg`.
- Use conventional texture suffixes: `-albedo`, `-normal`, `-roughness`, `-metalness`, `-emissive`, and `-ao`.
- Include resolution only when multiple runtime resolutions exist, for example `shop-sign-albedo-1k.jpg`.
- Keep names stable after an asset is referenced by code.
- Mirror a runtime asset's base name in its Blender master where practical.

## Blender asset pipeline

The production asset path is **Blender → GLB → Three.js**. Assets that can be generated procedurally should have a repeatable Python script under `blender/scripts/` so their editable master and runtime export can be rebuilt without a manual GUI process.

### Installed Blender

- Detected version: **Blender 3.0.0**
- Executable: `/Applications/Blender.app/Contents/MacOS/Blender`

From the project root, generate the bus shelter with:

```sh
/Applications/Blender.app/Contents/MacOS/Blender \
  --background \
  --python blender/scripts/createBusShelter.py
```

The script derives the project root from its own location and creates parent directories when necessary. It produces:

- Blockout master: `blender/source/bus-shelter/preston-busstop-blockout.blend`
- Detailed geometry master: `blender/source/bus-shelter/preston-busstop.blend`
- Composed review scene: `blender/source/bus-shelter/preston-busstop-reference.blend`
- Shelter-only runtime model: `public/assets/models/bus-shelter/preston-bus-shelter.glb`
- Trolley-only runtime model: `public/assets/models/bus-shelter/preston-shopping-trolley.glb`
- Composed game model: `public/assets/models/bus-shelter/preston-busstop-reference.glb`
- Development reviews: `renders/bus-shelter/01-...png` through `04-...png`

The game loads the texture pass instead, built on the same geometry by `blender/scripts/createBusShelterTextured.py`: `public/assets/models/bus-shelter/preston-busstop-textured.glb`, configured at runtime by `src/world/busShelterMaterials.ts`. The pipeline, map conventions and rebuild command are in `docs/assets/bus-shelter.md`.

### Scale, coordinates, and export

- One Blender unit represents one metre, with Blender's metric unit scale set to `1.0`.
- Models are built around the world origin, stand on the ground at `Z = 0`, and have transforms applied before export.
- Blender source scenes use Blender's native Z-up coordinates. The glTF exporter converts them to the Y-up convention used by Three.js.
- Environment models should have a clearly documented forward/open direction. The bus shelter's open front faces positive local X.
- Object names are descriptive lowercase kebab-case. Asset filenames use the project-wide lowercase kebab-case convention.
- Runtime exports use binary glTF (`.glb`) with selected asset objects only and Y-up conversion enabled.

Three.js loads runtime models with `GLTFLoader`. Model URLs are built from `import.meta.env.BASE_URL`, followed by the path beneath `public/`; this preserves both Vite development and deployment beneath `/zealot-of-harperhey/`.

`.blend` source files belong under `blender/source/` and are not copied into production builds. Runtime-ready GLBs belong under `public/assets/models/` and are copied into the static build. Preview renders remain under `renders/` and are development-only.

## Prototype world textures

Regenerate the temporary low-resolution world texture pack with:

```sh
node scripts/generateWorldTextures.mjs
```

The script produces 128–512 pixel PNG runtime textures under `public/assets/textures/world-prototype/`. Most are procedural; the Dreams and Coral façade derivatives are reproducibly cropped and graded from the corresponding repository reference photographs. The originals are read-only inputs outside `public/` and are never modified. The filtering and resolution policies are documented in `VISUAL_LANGUAGE.md`.

Generation currently expects macOS `sips` for procedural PPM-to-PNG conversion and `ffmpeg` on `PATH` for the two photographic crops. No npm package is required for either step.

## Layered road textures

Roads are built by `src/world/createRoadSurfaces.ts` from tiled asphalt, a world-space variation texture, a decal atlas and instanced ironwork. That comes to three draw calls for the entire network. Regenerate their textures separately from the world pack:

```sh
node scripts/generateRoadTextures.mjs
```

It writes PNGs directly (Node's `zlib`, no `sips` or `ffmpeg`) to `public/assets/textures/road/`. It reads the cell layout from `src/rendering/roadDecalAtlas.json`, the same file the runtime imports, so the two cannot drift apart. Pavements follow the same model in `src/world/createPavementSurfaces.ts`, with textures from `node scripts/generatePavementTextures.mjs`, written to `public/assets/textures/pavement/` from `src/rendering/pavementDecalAtlas.json`. Both generators share `scripts/lib/textureTools.mjs`, and both runtimes share `src/world/surfaceDecals.ts`. Road and pavement ironwork share one instanced mesh, so both networks together cost five draw calls. The layer model, placement rules and the photograph shot list for replacing procedural cells are in `ROAD_ATLAS.md`.

## Character and garment pipeline

Art-direction intent is in `ART_DIRECTION.md` under "Fashion as a Core Art-Direction Pillar".

Three.js is the renderer, not the primary garment-authoring environment. Garment fidelity is established upstream in Blender:

```
reference photography
→ character/body proportions
→ garment modelling
→ optional Blender cloth simulation
→ baked/rest-state drape
→ retopology
→ skinning
→ PBR material creation
→ GLB export
→ Three.js
```

Avoid real-time cloth simulation for standard NPC garments during the current production phase.

Priorities, in order:

1. silhouette
2. proportions
3. drape
4. skinning
5. material response
6. texture resolution

Use LODs/lower-detail variants for background NPCs where necessary. Characters follow the same scale and export conventions as other assets ("Scale, coordinates, and export" above). The current player is a primitive placeholder owned by `PlayerController`, and `src/npc/` is still an empty stub.

## Vehicle architecture

Design intent is in `ART_DIRECTION.md` under "Transport and Movement".

Build vehicle systems in `src/vehicles/` (currently an empty stub) around reusable vehicle controllers. Initial priorities:

- `BicycleController`
- `BusRoute`
- `BusController`
- `BusStop`

Buses initially use deterministic spline/node routes rather than general traffic AI. The initial network is **Harperhey ⇄ The Promised Land**: two buses circulate between two stops.

Existing pieces to extend rather than duplicate:

- `BUS_STOPS` in `src/world/worldLayout.ts` already defines Bus Stop A and Bus Stop B. Both are inside the current map, and neither is yet assigned to Harperhey or The Promised Land.
- The Sterling hire bikes (`docs/assets/sterling-bike.md`) already expose articulated wheel, steering, crank and pedal nodes and a future `SD_InteractionAnchor`. A `BicycleController` should be able to drive that rig as well as the player's own bike.
- Vehicles should advance on `FixedStepClock` like the player, so rendering performance never changes their speed.

## Photographic lighting

Photography/video lights can exist as normal world assets and, later, interactive lighting objects.

Performance rule: **do not recreate the earlier problem of large numbers of independent dynamic lights.** The local-light budget in "Performance and simulation policy" above still applies. Where possible:

- bake/static-light environmental tableaux
- limit shadow-casting lights
- use emissive geometry where illumination is not required
- activate expensive lights contextually
- use distance-based disabling/LOD
- reuse light/stand assets

Visible lighting apparatus is an art-direction feature, not justification for unrestricted dynamic lighting.
