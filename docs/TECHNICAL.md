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
- **Target public path:** `/zealot-of-harperhay/`
- **Initial hosting:** GitHub Pages, through the existing website
- **Possible later asset hosting:** Cloudflare R2, if asset volume or delivery requirements justify it
- **Initial platform:** desktop browser MVP
- **Architecture:** lightweight, with no unnecessary frameworks

Development-only references, source photography, `.blend` masters, and renders live outside `public/` so Vite does not copy them into the production build. Only runtime-ready files belong in `public/assets/`.

## Playable prototype architecture

- `main.ts` owns renderer and scene initialisation plus the delta-time game loop.
- `InputController` tracks keyboard movement, running, and click-drag camera input.
- `PlayerController` owns the primitive player representation, velocity, facing direction, movement state, and collision movement.
- `ThirdPersonCamera` owns orbit angles, camera-relative movement direction, and smoothed following.
- `createWorld` builds the primitive Street A blockout and supplies its collision description.
- `collision.ts` isolates the lightweight collision routines from player and world rendering code.

### Controls and temporary movement values

- Move forward: `W` or `Arrow Up`
- Move backward: `S` or `Arrow Down`
- Move left: `A` or `Arrow Left`
- Move right: `D` or `Arrow Right`
- Run: hold `Shift` while moving
- Orbit camera: click and drag with the primary mouse button
- Temporary walking speed: **2.4 metres per second**
- Temporary running speed: **4.5 metres per second**

Movement is calculated relative to the camera's horizontal facing direction. Velocity accelerates and decelerates smoothly to give the placeholder movement some weight. There is no jumping.

### Camera

The prototype uses a 50-degree perspective camera placed 6.8 metres from the player. Horizontal mouse orbit is unrestricted, while vertical pitch is clamped to a modest elevated range. Camera position follows the player using frame-rate-independent exponential smoothing. Pointer lock is not used.

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

- Use lowercase `kebab-case` filenames, for example `harperhay-bus-stop.glb`.
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

- Editable master: `blender/source/harperhay-bus-shelter.blend`
- Runtime model: `public/assets/models/harperhay-bus-shelter.glb`
- Development preview: `renders/harperhay-bus-shelter-preview.png`

### Scale, coordinates, and export

- One Blender unit represents one metre, with Blender's metric unit scale set to `1.0`.
- Models are built around the world origin, stand on the ground at `Z = 0`, and have transforms applied before export.
- Blender source scenes use Blender's native Z-up coordinates. The glTF exporter converts them to the Y-up convention used by Three.js.
- Environment models should have a clearly documented forward/open direction. The bus shelter's open front faces positive local X.
- Object names are descriptive lowercase kebab-case. Asset filenames use the project-wide lowercase kebab-case convention.
- Runtime exports use binary glTF (`.glb`) with selected asset objects only and Y-up conversion enabled.

Three.js loads runtime models with `GLTFLoader`. Model URLs are built from `import.meta.env.BASE_URL`, followed by the path beneath `public/`; this preserves both Vite development and deployment beneath `/zealot-of-harperhay/`.

`.blend` source files belong under `blender/source/` and are not copied into production builds. Runtime-ready GLBs belong under `public/assets/models/` and are copied into the static build. Preview renders remain under `renders/` and are development-only.
