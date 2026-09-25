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
- **Target public path:** `/zealot-of-harpurhey/`
- **Initial hosting:** GitHub Pages, through the existing website
- **Possible later asset hosting:** Cloudflare R2, if asset volume or delivery requirements justify it
- **Initial platform:** desktop browser MVP
- **Architecture:** lightweight, with no unnecessary frameworks

Development-only references, source photography, `.blend` masters, and renders live outside `public/` so Vite does not copy them into the production build. Only runtime-ready files belong in `public/assets/`.

## Playable prototype architecture

- `main.ts` owns renderer and scene initialisation, raw render timing, and the fixed-step game loop.
- `FixedStepClock` advances gameplay at 60 Hz with bounded catch-up and explicit extreme-gap resets.
- `InputController` tracks keyboard movement, running, and click-drag camera input.
- `AmbientAudio` layers the Manny streets recording beneath the Popcorn music track; both are shipped to production (see `docs/ASSET_RIGHTS.md`). Browser autoplay rules mean audio begins on the first key press or pointer interaction; `M` toggles music without muting the street layer.
- `MovementAudio` (`src/audio/`) plays footsteps and the ridden bike. Footsteps are five recorded concrete clips (Kenney Impact Sounds, CC0; `docs/assets/kenney-impact-sounds-LICENSE.txt`), fired from `PlayerController.onFootfall` each time the walk cycle's thigh swing reaches an extreme (`src/player/footfall.ts`), only while the player is actually moving. Each step is the clip at a randomised pitch and level plus a slowed, low-passed copy underneath for weight; running is louder and faster. The bike is synthesised live, no recordings: `bikeSoundLevels` (`bikeSoundModel.ts`, unit-tested) maps speed, pedalling, e-assist and braking to tyre hiss, wind, a freewheel ratchet while coasting, chain whirr while pedalling, a motor whine and a brake squeal. `SterlingBike` exposes `motorAssist` and `braking` for it. Audio starts on the first key press or click; the context is suspended while the tab is hidden. `tests/browser/movement-audio.html` is the real-Web-Audio regression (click the page to start it).
- `PlayerController` owns the primitive player representation, velocity, facing direction, movement state, and collision movement. While riding it is seated by `updateRiding`: planar two-bone IK puts the feet on the pedals and the hands on the grips.
- `BikeInteraction` (`src/interaction/`) is the on-foot / riding state machine. It runs the player on foot, or the ridden Sterling bike and its rider, inside the fixed step, and supplies the camera target and the E prompt (`src/ui/InteractionPrompt.ts`).
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
- Use (hire / ride / get off / return to dock): `E`
- Production walking speed: **2.4 metres per second**
- Production running speed: **4.5 metres per second**
- Development walking speed: **3.12 metres per second** (30% faster)
- Development running speed: **7.65 metres per second** (70% faster)

Movement is calculated relative to the camera's horizontal facing direction. Velocity accelerates and decelerates smoothly to give the placeholder movement some weight. There is no jumping.

### Riding a Sterling bike

- Walk within about 1 m of a docked or parked bike: **E** hires it (docked) or takes it (parked). A docked bike first rolls 1.15 m straight back out of its dock, as at a real dock. Riding forward would run the front wheel through the side post.
- Riding controls are bike-relative, not camera-relative: `W` pedal, `Shift` e-assist, `Space` boost (drives forward on its own, no `W` needed), `A`/`D` steer, `S` brake (then walk the bike backwards).
- Pedalling tops out at **4.6 m/s**; e-assist at **6.9 m/s** (the ~15.5 mph fleet cap); Space boost at **20 m/s** (~45 mph, ~4.3x pedalling). Boost is a game-feel sprint, not realism. It was set below 5x because the city is ~100 m across and faster bikes can't turn into its streets. It reaches ~19 m/s in 4 s and bleeds off at 5 m/s² when released. Above assist speed braking is 12 m/s² (20 m/s to a stop in ~2.3 s / ~19 m). No development speed multiplier is applied.
- **E** within 1 m of an empty dock's bike position (at up to 3.2 m/s) rolls the bike in and locks it. Anywhere else, **E** brakes to a stop, leaves the bike parked, and steps off. Press E again while braking to keep riding.
- Steering is a kinematic bicycle model (yaw rate = speed × tan(steer) / 1.31 m wheelbase). Steering lock narrows with speed and is further capped by 16 m/s² of sideways grip, giving a ~25 m turning radius at full boost. The bike and rider lean into turns (up to 0.5 rad). Crank speed caps at ~2 rev/s.
- Collision: a swept 0.27 m body circle plus two narrow wheel probes, sub-stepped every 0.1 m so boost speed cannot pass through lampposts. Anything a wall absorbs is taken off the speed. Docked and parked bikes are solid footprints that `SterlingFleet` adds to and removes from the shared obstacle list. A ridden bike has no footprint. Dock side posts are fixed obstacles.
- The chase camera eases its boom from 6.8 m to 7.9 m while mounted, and above assist speed up to +2.6 m boom and +11° field of view at full boost.

## Performance and simulation policy

Rendering performance must never change simulation speed.

Gameplay advances through `FixedStepClock` at **1/60 second** per step. Real animation-frame time is accumulated rather than truncated, with at most 16 catch-up steps per rendered frame. A gap above 250 ms is treated as an extreme pause rather than an ordinary slow frame. The accumulator is also reset on document visibility changes, so returning from a background tab never attempts to simulate the entire hidden period.

The camera remains a render-time concern and uses the uncapped real frame delta during ordinary visible frames. This preserves its exponential smoothing without applying pointer orbit input once per gameplay substep.

Development FPS is derived from raw frame time. The development overlay also reports frame milliseconds, draw calls, triangles, active point and spot lights, drawing-buffer size, effective pixel ratio, render scale, resident textures and geometries, shader programs, and the selected quality profile.

The default desktop quality is **MEDIUM**. Use `?quality=low`, `?quality=medium`, or `?quality=high` during development and profiling. Full policy and measured Phase 1 results are documented in `PERFORMANCE.md` and `ENGINE_STABILISATION_REPORT.md`.

Tone mapping defaults to **AgX**, applied by `OutputPass` in linear HDR after bloom and before the display grade. Use `?tonemap=agx`, `?tonemap=neutral`, `?tonemap=aces`, or `?tonemap=off` to compare curves; `off` reproduces the earlier uncurved image. Each curve has its own exposure in `VISUAL_STYLE.render.exposure`, calibrated so midtone brightness matches `off`, so a comparison shows highlight rolloff and colour rather than a brightness change. When a curve is active the grade pass's own exposure is 1, so exposure is never applied twice. Combine with `?view=<name>&quality=high&overlays=off` for repeatable comparisons.

Most environmental illumination in Zealot of Harpurhey is intentionally represented using emissive materials, photographic/baked illumination, geometric light cones and fake light pools rather than large numbers of real-time dynamic lights. The normal local-light budget is four on MEDIUM, with five available on HIGH and two on LOW. `LocalLightRegistry` owns the real-time local point lights, keeps multi-light fixtures atomic, includes asset-loaded shop lights in the same budget, and uses one moving public-light proxy for the current streetlight pool. Streetlights do not use real-time spotlights.

### Camera

The agreed direction, the merge plan for the unmerged camera branches and the acceptance tests live in `docs/CAMERA_AND_MOVEMENT_BRIEF.md`. Read it before changing the camera, movement or input.

**Guiding principle (Daniel, 2026-09-16):** the game is in part a photo walk through a nocturnal city of architecture. Most of the time the camera sits at eye level with a near-level lens, so building facades, bus stops and the street read clearly and are framed almost like photographs. Don't trade this for a high or top-down chase view. See also the medium-format framing notes in `docs/creative-constitution.md`.

The camera is a 56-degree perspective lens 5.6 m behind the player. The orbit pivot, which is also the look target (`ORBIT_PIVOT_HEIGHT`), is 1.6 m above the feet, and the rest pitch (`DEFAULT_CAMERA_PITCH`) is 0.04 rad. That puts the lens about 1.8 m up with verticals upright and the horizon running through the player's head. Horizontal mouse orbit is unrestricted, and vertical pitch is clamped between -0.12 and 0.9 rad. After manual orbiting, pitch waits 2.5 s, then drifts back to the rest angle, so looking up at a roofline is a glance and not a new default. Both the lens and the look target are driven from a single anchor that chases the player with frame-rate-independent exponential smoothing, so the figure keeps its place in the frame under acceleration. Pointer lock is not used.

On foot the camera never turns by itself. Walking is camera-relative, so easing yaw toward the direction of travel rotates the movement basis, and a diagonal or strafing walker gets carried round in a circle. C swings the camera behind the player over a fraction of a second. Only a bike, which steers relative to itself, pulls the camera round behind its direction of travel, and manual orbiting holds that off for 1.2 s. The riding boom is a fixed 7 m. Boost widens the lens by up to 5° but does not change the boom, because a speed-linked boom made the camera zoom in and out with every change of pace.

The camera collides with the same obstacle set as the player. When an obstacle stands between the orbit pivot and the camera, the boom first rises a little and keeps its length. Each frame it sweeps extra pitch in 0.05 rad steps, capped at 0.35 rad so the eye-level framing is never swapped for a view from above, and uses the first angle whose 0.3 m sphere cast clears. The lift rises quickly, holds for 0.8 s after the obstruction clears so rows of buildings do not make it bob, then eases back down. When the capped lift can't clear, the boom is shortened. It is also shortened as a hard constraint while the lift is still catching up. Pulling in is immediate, and extending back out eases. Obstacles are extruded from the ground to their `height`, so the camera can look over anything lower than it. Thin street furniture sets `blocksCamera: false`, so poles and bollards passing behind the player do not make the camera pump.

The collision fraction is a hard upper bound: no minimum boom distance may push the camera back through a wall. When the lens and look target coincide, orientation uses the intended orbit direction. At close range the character visual hides below 1.7 m and returns above 1.95 m, while its ground shadow remains; this avoids the lens looking through the character's head or clothes.

### Movement

Movement is camera-relative, but the basis is **latched**: while a direction key is held, "forward" stays the yaw captured when the input started. It is re-captured only when the held keys change or the player orbits the camera themselves, so a camera that moves for any other reason — easing past a building, following a bike — cannot bend a walk into a curve. This is what makes a held direction trace a straight line.

Walking is 2.4 m/s and running (Shift or Space) is 4.5 m/s, the same in dev and production; `?fast=on` restores the old dev multipliers. Velocity reaches 90% of pace in about 0.12 s and settles to a stop in the same time, gliding under 7 cm after the key is released, with a snap below 0.12 m/s so idle never drifts. Space is contextual: it runs on foot and boosts while riding.

The figure faces the **input** direction, not its post-collision movement, so brushing a wall no longer swings it round to run along the wall.

Key handling is written for hardware keyboards on iPads as well as desktops: bindings resolve `event.code`, falling back to a code rebuilt from `event.key` when the code is empty, and every held key is released on blur, on a hidden document, and on any Cmd chord, whose keyup iPadOS swallows.

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

- Use lowercase `kebab-case` filenames, for example `harpurhey-bus-stop.glb`.
- Use ASCII letters, numbers, and hyphens only; do not use spaces.
- Add a meaningful variant suffix where needed, for example `brick-wall-wet-albedo.jpg`.
- Use conventional texture suffixes: `-albedo`, `-normal`, `-roughness`, `-metalness`, `-emissive`, and `-ao`.
- Include resolution only when multiple runtime resolutions exist, for example `shop-sign-albedo-1k.jpg`.
- Keep names stable after an asset is referenced by code.
- Mirror a runtime asset's base name in its Blender master where practical.

## Blender asset pipeline

The production asset path is **Blender → GLB → Three.js**. Assets that can be generated procedurally should have a repeatable Python script under `blender/scripts/` so their editable master and runtime export can be rebuilt without a manual GUI process.

### Installed Blender

- Detected version: **Blender 5.2 LTS** (upgraded from 3.0.0, 2026-09-25, Stage 0.1 of `docs/REALISM_PASS_PLAN.md`)
- Executable: `/Applications/Blender.app/Contents/MacOS/Blender` (unverified against the new install — confirm this path still resolves before the next `blender --background --python ...` run, and update it here if the new version installed elsewhere rather than in place over the old one)

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

Three.js loads runtime models with `GLTFLoader`. Model URLs are built from `import.meta.env.BASE_URL`, followed by the path beneath `public/`; this preserves both Vite development and deployment beneath `/zealot-of-harpurhey/`.

`.blend` source files belong under `blender/source/` and are not copied into production builds. Runtime-ready GLBs belong under `public/assets/models/` and are copied into the static build. Preview renders remain under `renders/` and are development-only.

## Prototype world textures

Regenerate the temporary low-resolution world texture pack with:

```sh
node scripts/generateWorldTextures.mjs
```

The script produces 128–512 pixel PNG runtime textures under `public/assets/textures/world-prototype/`. Most are procedural; the Dreams and Coral façade derivatives are reproducibly cropped and graded from the corresponding repository reference photographs. The originals are read-only inputs outside `public/` and are never modified. The filtering and resolution policies are documented in `VISUAL_LANGUAGE.md`.

Generation currently expects macOS `sips` for procedural PPM-to-PNG conversion and `ffmpeg` on `PATH` for the two photographic crops. No npm package is required for either step.

## Texture standard

Stage 3a of the realism pass (`docs/REALISM_PASS_PLAN.md`). Applies to new/replaced texture sets going forward; it does not retroactively resize what is already shipping.

| Surface | Resolution | Maps | Source |
| --- | --- | --- | --- |
| Hero façade materials (cladding, shutters, brick, render) | 1K–2K | albedo, normal, **ORM** (AO/roughness/metal packed in R/G/B) | Poly Haven / ambientCG CC0 scans, or Daniel's own photographs for signage |
| Ground (asphalt, paving, kerbs) | 2K tiling + world-space variation (already the pattern for roads/pavement, see "Layered road textures" below) | albedo, normal, roughness, a puddle mask (Stage 4) | Poly Haven asphalt (already in use), a paving scan |
| Props (bins, bollards, rails) | 512–1K, shared trim sheet | albedo, normal, ORM | CC0 scans + Blender |
| Signs and posters | as needed | albedo + emissive | Daniel's photographs |

Naming: `<asset>_<surface>_{albedo,normal,orm}.ktx2`, compressed with albedo on ETC1S and normal/ORM on UASTC (ETC1S's chroma subsampling visibly damages normal and ORM data). Every new texture set is recorded in `config/asset-rights.json`; `npm run rights:check` (part of `npm run check`) enforces this.

**Building GLBs textured through the real Blender pipeline** (`exportTexturedBuilding.py` and similar) already carry albedo/normal/ORM natively via glTF — `src/world/buildingMaterials.ts`'s `profileAuthoredMaps` is the runtime side of that, and every hero building already runs it. This standard mainly matters for **new** hero-building texture passes (a Stage 3c/Stage 9 re-texture) and for `docs/assets/*.md` texture briefs.

**The procedural `world-prototype` system** (`src/rendering/worldMaterials.ts`'s `createWorldMaterial`) generates its own low-resolution albedo-only textures in code (see "Prototype world textures" above) and, as of Stage 3, also accepts an optional `normalMap` and a packed `ormMap` (glTF R=AO/G=roughness/B=metalness convention) as companion textures alongside any `WorldTextureName`. No procedural texture currently ships a companion map — this is plumbing, not yet content — but a future `scripts/generateWorldTextures.mjs` pass, or a hand-authored replacement following the table above, can now wire one in without a further code change.

## Baked lighting (lightmaps)

Stage 5a of the realism pass. One command bakes a building's light in Blender and re-exports its GLB with a second UV set:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
  --python-exit-code 1 --python blender/scripts/bakeLightmap.py -- dreams
```

Settings, light positions and colours live in `config/lightmap-bakes.json` (world coordinates, converted into the model's frame by `blender/scripts/lightmapConfig.py`; `python3 tests/blender/test_lightmap_config.py` checks the maths). About five minutes on an M1, of which the bakes are four. Options: `--samples N --ao-samples N --size N --device cpu|gpu`; `--no-export --out-dir DIR` runs it without touching `public/` or `blender/source/`.

- **Geometry** comes from the untextured stash GLB (`blender/source/runtime-untextured/`), with the building's PBR surfaces applied exactly as `texture_glb()` does, so node names and transforms match the game. The `.blend` greybox is not opened.
- **UVs:** every mesh gets a second UV map named `Lightmap` (exported as `TEXCOORD_1`, three.js `channel = 1`), one Smart-UV atlas across the building at about 4.7 cm per texel at 2048. UV0, the tiling metric UVs, is untouched. Excluded meshes (Dreams' hidden mortar strips) get a zeroed second UV so every primitive has the same vertex layout, which the runtime mesh merger requires. The UVs are in glTF convention (v flipped), so a loader must not flip the image again.
- **Lights** use the game's own colours and units: the cold-white fascia tubes (`coldWhite`), the two sodium lamps in front of the shop (`sodium`, 95 cd = `streetLightIntensity`, at the `streetlightEmitterWorld` positions), and the sky as `ambientSky x ambientIntensity / pi` world colour. A Cycles point light of P watts is P / (4 pi) candela in the game's terms (measured). The tube brightness (9 cd each) is the bake's own choice. A ground patch and the neighbouring buildings (Cass Art, Spice Cabin) are stand-ins that bounce and shadow.
- **Outputs** in `public/assets/textures/lightmaps/`: `<asset>_lightmap.hdr` (scene-linear radiance a white diffuse surface would show, light only), `<asset>_ao.png` (8-bit, R = AO), `<asset>_ground_lightmap.hdr` (2048x1024) and `<asset>_lightmap.json` (every setting used). Three.js divides irradiance by pi when it applies albedo, so `lightMapIntensity = pi` reproduces the bake's exposure. The bake scene is saved to `blender/source/bake/<asset>-bake.blend` and review images to `renders/realism-pass/05-baked-lighting/`.
- **Denoise:** Cycles ignores its denoise flag when baking (verified in 5.2), so the script denoises both maps afterwards with the compositor's OpenImageDenoise node and fails if the denoise moves the mean by more than 5%.
- **Adding a building:** add an entry to `config/lightmap-bakes.json` and to `config/building-textures.json`; the script does the rest.

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

Build vehicle systems in `src/vehicles/` around reusable vehicle controllers. Initial priorities:

- `BicycleController`: first version exists as `SterlingBike` (physics, collision and rig animation for one fleet bike) plus `SterlingFleet` (docks, parked bikes, dock roll-in/out). Generalise it when the player's own bike arrives.
- `BusRoute`
- `BusController`
- `BusStop`

Buses initially use deterministic spline/node routes rather than general traffic AI. The initial network is **Harpurhey ⇄ The Promised Land**: two buses circulate between two stops.

Existing pieces to extend rather than duplicate:

- `BUS_STOPS` in `src/world/worldLayout.ts` already defines Bus Stop A and Bus Stop B. Both are inside the current map, and neither is yet assigned to Harpurhey or The Promised Land.
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
