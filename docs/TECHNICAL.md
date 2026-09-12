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
- `PlayerController` owns the primitive player representation, velocity, facing direction, movement state, and collision movement.
- `ThirdPersonCamera` owns orbit angles, camera-relative movement direction, and smoothed following.
- `createWorld` builds the canonical city layout, visual blockouts and its collision description. It exposes a `ready` promise that settles once every hero GLB has loaded or failed.
- `collision.ts` isolates the lightweight collision routines from player and world rendering code, including the ray/box cast the camera uses for occlusion.
- `interaction/LocationAwareness.ts` tracks which authored location the player is standing at, measured against location footprints from `worldLayout.ts`. It owns no behaviour — it is the seam the delivery loop attaches to.
- `ui/LocationLabel.ts` renders that acknowledgement as a restrained caption. `ui/LoadingVeil.ts` holds the opening frame until `world.ready` settles (or a 12-second timeout elapses, so a failed asset never leaves the player staring at black).
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
- Zoom camera: scroll wheel (2.5 m – 12 m, default 6.8 m)
- Hide/show development labels and debug panel: `H`
- Production walking speed: **2.4 metres per second**
- Production running speed: **4.5 metres per second**
- Development walking speed: **3.12 metres per second** (30% faster)
- Development running speed: **7.65 metres per second** (70% faster)

Movement is calculated relative to the camera's horizontal facing direction. Velocity accelerates and decelerates smoothly to give the placeholder movement some weight. There is no jumping.

The figure faces the player's **input** direction, not the movement that collision resolution allowed. Deriving facing from the resolved delta made the character turn to run along a wall it was being pushed against.

## Performance and simulation policy

Rendering performance must never change simulation speed.

Gameplay advances through `FixedStepClock` at **1/60 second** per step. Real animation-frame time is accumulated rather than truncated, with at most 16 catch-up steps per rendered frame. A gap above 250 ms is treated as an extreme pause rather than an ordinary slow frame. The accumulator is also reset on document visibility changes, so returning from a background tab never attempts to simulate the entire hidden period.

The camera remains a render-time concern and uses the uncapped real frame delta during ordinary visible frames. This preserves its exponential smoothing without applying pointer orbit input once per gameplay substep.

Development FPS is derived from raw frame time. The development overlay also reports frame milliseconds, draw calls, triangles, active point and spot lights, drawing-buffer size, effective pixel ratio, render scale, resident textures and geometries, shader programs, and the selected quality profile.

The default desktop quality is **MEDIUM**. Use `?quality=low`, `?quality=medium`, or `?quality=high` during development and profiling. Full policy and measured Phase 1 results are documented in `PERFORMANCE.md` and `ENGINE_STABILISATION_REPORT.md`.

Tone mapping defaults to the current uncurved render. Use `?tonemap=off`,
`?tonemap=aces`, `?tonemap=agx`, or `?tonemap=neutral` to compare the same
scene through Three.js's NoToneMapping, ACES Filmic, AgX, and Neutral curves.
With no `?tonemap=` parameter (or an unrecognised value), tone mapping remains
off. Development camera positions can be selected with `?view=<name>`; combine
that with `?quality=high&overlays=off` for clean, repeatable comparisons.

Most environmental illumination in Zealot of Harperhey is intentionally represented using emissive materials, photographic/baked illumination, geometric light cones and fake light pools rather than large numbers of real-time dynamic lights. The normal local-light budget is four on MEDIUM, with five available on HIGH and two on LOW. Streetlights do not use real-time spotlights.

### Camera

The prototype uses a 50-degree perspective camera placed 6.8 metres from the player by default, adjustable from 2.5 m to 12 m with the scroll wheel. Horizontal mouse orbit is unrestricted, while vertical pitch is clamped to a modest elevated range. Camera position follows the player using frame-rate-independent exponential smoothing. Pointer lock is not used.

**Occlusion:** the camera probes from its orbit pivot toward its desired position against the same axis-aligned obstacle list the player collides with, and pulls in to the first hit. It snaps inward immediately so walls never clip through the frame, and eases back out so doorways and railings do not flick it around. Obstacles may declare a `height`; those that do (the bus shelters) can be flown over, while those that omit it are treated as infinitely tall columns, which is correct for buildings since they are all taller than the camera can climb.

### Collision

The player is represented on the ground plane by a circle with a temporary radius of 0.38 metres. Buildings and the bus shelter use two-dimensional axis-aligned bounding boxes. Movement is resolved one horizontal axis at a time, allowing the player to slide along obstacles, and is clamped to the current playable blockout bounds. This intentionally small collision layer can later be replaced without changing the input or camera systems.

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

### Scale, coordinates, and export

- One Blender unit represents one metre, with Blender's metric unit scale set to `1.0`.
- Models are built around the world origin, stand on the ground at `Z = 0`, and have transforms applied before export.
- Blender source scenes use Blender's native Z-up coordinates. The glTF exporter converts them to the Y-up convention used by Three.js.
- Environment models should have a clearly documented forward/open direction. The bus shelter's open front faces positive local X.
- Object names are descriptive lowercase kebab-case. Asset filenames use the project-wide lowercase kebab-case convention.
- Runtime exports use binary glTF (`.glb`) with selected asset objects only and Y-up conversion enabled.

Three.js loads runtime models with `GLTFLoader`. Model URLs are built from `import.meta.env.BASE_URL`, followed by the path beneath `public/`; this preserves both Vite development and deployment beneath `/zealot-of-harperhey/`.

`.blend` source files belong under `blender/source/` and are not copied into production builds. Runtime-ready GLBs belong under `public/assets/models/` and are copied into the static build. Preview renders remain under `renders/` and are development-only.

**Only GLBs that code actually loads belong in `public/`.** Vite copies everything under `public/` verbatim into `dist/`, so an unreferenced export is downloaded by every player without ever being used. Superseded hero assets, component exports and not-yet-wired blockouts live in `blender/exports/unreferenced/` (see the README there) and move back in the same commit as the code that references them.

Verify with:

```sh
comm -13 <(grep -rho "assets/models/[a-zA-Z0-9_/-]*\.glb" src/ | sort -u) \
         <(cd public && find assets/models -name '*.glb' | sort)
```

Any output is an asset shipping to players for no reason.

## Prototype world textures

Regenerate the temporary low-resolution world texture pack with:

```sh
node scripts/generateWorldTextures.mjs
```

The script produces 128–512 pixel PNG runtime textures under `public/assets/textures/world-prototype/`. Most are procedural; the Dreams and Coral façade derivatives are reproducibly cropped and graded from the corresponding repository reference photographs. The originals are read-only inputs outside `public/` and are never modified. The filtering and resolution policies are documented in `VISUAL_LANGUAGE.md`.

Generation currently expects macOS `sips` for procedural PPM-to-PNG conversion and `ffmpeg` on `PATH` for the two photographic crops. No npm package is required for either step.
