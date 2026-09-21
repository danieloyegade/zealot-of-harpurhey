# Lighting Hierarchy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the night more selective by spending light on the rider, the public pools and the current destination. Keep the black intervals, and keep the renderer's per-frame lighting cost where it is or lower it.

**Architecture:** Every change works inside the existing systems: `LocalLightRegistry` (fixed pool of 2/4/5 point-light slots), the painted streetlight graphics, the player's material policy, and the display-grade pass. Nothing adds a light slot. The rider gets a lamp response through a shader term on their own materials instead of another slot. Global changes (display grade, moon angle) ship as dev-only controls with the current values as defaults, and Daniel picks the final values from side-by-side captures.

**Tech Stack:** Three.js 0.185, TypeScript, Vite 8, Vitest (added in Task 1, dev-only), Playwright MCP for captures.

**Spec:** `docs/LIGHTING_AUDIT.md` (13 Sept audit and 14 Sept follow-up). Also read `docs/PERFORMANCE.md`, `docs/TECHNICAL.md` and `docs/creative-constitution.md` before starting.

## Global Constraints

- The active local-light ceiling stays at LOW 2 / MEDIUM 4 / HIGH 5 (`QUALITY_PROFILES` in `src/rendering/visualStyle.ts`). No task raises it.
- Do not raise global exposure, hemisphere intensity or moon intensity as a fix. Task 9 may change the moon's **angle**, but only with Daniel's approval.
- Do not add shadow maps. `VISUAL_STYLE.geometry.shadowsEnabled` stays `false`.
- Do not give streetlights real lights. The single moving proxy stays the only public-light slot.
- The player's clothing must read as near-black and must never turn visibly blue.
- Do not spread magenta to new locations.
- Rendering performance must never change simulation speed (`docs/PERFORMANCE.md`).
- Preserve-first (`AGENTS.md`): extend the existing systems and never build a parallel one.
- Asset-first (`AGENTS.md`): no new major visual asset built in engine code. Streetlight poles already exist as a world component, so adding more is allowed. New luminaires for CTL and Greek Gyros come from Blender (out of scope here).
- The working tree is shared with other sessions. Stage files by explicit path, never `git add -A` or `git add .`. Check `git status` before every commit.
- Commit subjects follow the repo's style: a plain imperative sentence (e.g. "Pool local point lights and drop glass transmission to stop lag"), no `feat:` prefix. End every commit message with the attribution line from the session's system instructions.

---

## What the game looks like now (21 Sept 2026 capture pass)

These are observations from MEDIUM captures at 1280 × 720 of `?view=` dev views (AgX, overlays off). Each item states what was seen, not what was intended.

1. **The global night is bluer and flatter than the audit says.** The hemisphere (0.72) and moon (1.28) light every façade evenly. On pale blockout buildings, such as the grey building beside MCR1 in `park-florist` and `public-light-pool`, and the Hive in `greek-gyros` and `north-road`, the brightest surfaces in the frame are unlit walls, not practical lights. The gaps between lit areas read as navy blue, not black.
2. **The rider reads as navy blue outside the pools** (`west-street`, `park-florist`, `public-light-pool`). The player-lift multiplies the rider's ambient (indirect) light by 1.55, and that ambient light is mostly the blue hemisphere sky (`0x304e9b`). So the lift makes the rider bluer, which the audit forbids.
3. **Inside a pool the rider goes darker, not brighter, from the default camera** (`south-road`, `dreams-angle`). The proxy lights the side of the rider facing the lamp, and the chase camera usually sees the other side. The rider becomes a black silhouette against lit paving. That can be photographically right, but the pool is not "selecting the figure" in the way the constitution describes.
4. **The painted pools read as scattered orange confetti, not pools of light.** They reuse the `reflection-broken-overhaul` texture on a 2.45 m disc (`addStreetlight`, `src/world/createWorld.ts:3454`). This is the most visible lighting artefact in the build.
5. **Location lights are chosen without regard to camera direction.** At `come-through-lab`, three of the four MEDIUM slots go to MCR1 and Florist lights about 16 m away, off to one side of the view. The CTL cue gets the fourth slot at intensity 3.2. Location-relevance mode checks only horizontal distance from the player.
6. **The streetlights cost roughly 100 draw calls.** 20 poles × (pole + head + pool + two reflection strips), none of them merged.
7. **Greek Gyros now works.** The counter practical from the GLB anchor produces a readable white commercial island. **The CTL door cue works** but is weak and temporary. **Bus Stop A's spill is already re-anchored** to the marker (audit item E1 is done).
8. **The `spice-cabin` dev view is stale.** Collision recovery pushes the player from (12.35, 57.6) to (18.9, 62.1), into the Eastern Bloc frontage. The fixed-view comparison needs this fixed first.

### Performance facts that shape the plan

- `LocalLightRegistry` keeps `maximumActiveLocalLights` point-light slots **always visible**; spare slots sit at intensity 0 (`src/world/localLighting.ts:60-78`). Every lit material therefore pays for the full budget on every pixel, all the time. Turning a light off changes nothing on the GPU, and adding a slot costs everywhere. **Improvements must come from better selection, emissive and painted light, and shader terms, never from more slots.**
- A shader term on the player's materials only runs on the rider's few thousand pixels, so it is effectively free.
- The grade pass has constant cost. Changing its parameters costs nothing.
- Merging the streetlight meshes cuts about 80 draw calls. The measured bottleneck is the CPU (Spice Cabin: 22 FPS, `docs/PERFORMANCE.md`), so this is a real saving.

---

## File Structure

| File | Status | Responsibility |
| --- | --- | --- |
| `package.json` | Modify | Add `vitest` dev dependency and `test` script. |
| `src/debug/lightingProbe.ts` | Create | Pure frame-statistics function (player separation, black share) plus projection of the player's screen rectangle. |
| `src/debug/lightingProbe.test.ts` | Create | Tests for the statistics. |
| `scripts/lighting-captures.playwright.js` | Create | Playwright MCP capture routine for the fixed views. Screenshots plus probe metrics. |
| `src/main.ts` | Modify | Dev views (fix `spice-cabin`, add `start`, `public-light-pool-front`, `hive-entrance`, `car-park`). Dev hooks `zealot.lighting` / `zealot.grade`. Pass the camera to `world.update`. Feed the player the character lamp. |
| `src/world/localLighting.ts` | Modify | View-aware location relevance. |
| `src/world/localLighting.test.ts` | Create | Registry selection tests. |
| `src/world/publicIllumination.ts` | Create | Nearest-streetlight lookup, pool falloff, character-lamp state. |
| `src/world/publicIllumination.test.ts` | Create | Tests for the above. |
| `src/world/createWorld.ts` | Modify | Use `publicIllumination.ts`. Drop the proxy on LOW. Merge streetlights. Car-park lamps. Hive entrance cue. Expose global lights and character lamp. |
| `src/player/PlayerController.ts` | Modify | Replace the 1.55 ambient gain with a neutral floor plus a lamp wrap/rim term. |
| `src/rendering/lightPoolTexture.ts` | Create | Soft radial `DataTexture` for painted pools. |
| `src/rendering/lightPoolTexture.test.ts` | Create | Falloff tests. |
| `src/rendering/createPostProcessing.ts` | Modify | Protected-toe contrast, grain-order switch, live grade parameters. Defaults unchanged. |
| `docs/LIGHTING_AUDIT.md`, `docs/PERFORMANCE.md`, `docs/TECHNICAL.md`, `docs/VISUAL_LANGUAGE.md`, `SYNC.md` | Modify | Task 10. |

---

### Task 1: Test runner and lighting probe

**Files:**
- Modify: `package.json`
- Create: `src/debug/lightingProbe.ts`
- Test: `src/debug/lightingProbe.test.ts`

**Interfaces:**
- Produces: `summariseFrame(pixels: Uint8Array, width: number, height: number, rect: PixelRect): FrameSummary`, `projectToPixelRect(box: Box3, camera: Camera, width: number, height: number): PixelRect | null`, and the types `PixelRect { x: number; y: number; width: number; height: number }` (bottom-left origin, drawing-buffer pixels) and `FrameSummary { playerLuminance: number; surroundLuminance: number; separation: number; blackShare: number }`.

- [ ] **Step 1: Add Vitest**

Run: `npm install --save-dev vitest`

Then add the script in `package.json`:

```json
"scripts": {
  "dev": "vite",
  "build": "tsc && vite build",
  "preview": "vite preview",
  "test": "vitest run"
}
```

- [ ] **Step 2: Write the failing test**

Create `src/debug/lightingProbe.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { summariseFrame, type PixelRect } from './lightingProbe';

function frame(width: number, height: number, value: (x: number, y: number) => number): Uint8Array {
  const pixels = new Uint8Array(width * height * 4);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const index = (y * width + x) * 4;
      const v = value(x, y);
      pixels[index] = v;
      pixels[index + 1] = v;
      pixels[index + 2] = v;
      pixels[index + 3] = 255;
    }
  }
  return pixels;
}

describe('summariseFrame', () => {
  const rect: PixelRect = { x: 40, y: 40, width: 20, height: 20 };

  it('reports no separation when the player matches the surround', () => {
    const summary = summariseFrame(frame(100, 100, () => 60), 100, 100, rect);
    expect(summary.separation).toBeCloseTo(0, 5);
  });

  it('reports strong separation for a dark figure on a lit surround', () => {
    const inside = (x: number, y: number) =>
      x >= 40 && x < 60 && y >= 40 && y < 60;
    const summary = summariseFrame(
      frame(100, 100, (x, y) => (inside(x, y) ? 4 : 120)),
      100,
      100,
      rect,
    );
    expect(summary.playerLuminance).toBeLessThan(summary.surroundLuminance);
    expect(summary.separation).toBeGreaterThan(0.9);
  });

  it('measures the share of near-black pixels across the whole frame', () => {
    const summary = summariseFrame(
      frame(100, 100, (x) => (x < 25 ? 5 : 200)),
      100,
      100,
      rect,
    );
    expect(summary.blackShare).toBeCloseTo(0.25, 2);
  });

  it('clips the surround ring to the frame edges', () => {
    const edgeRect: PixelRect = { x: 0, y: 0, width: 10, height: 10 };
    const summary = summariseFrame(frame(20, 20, () => 80), 20, 20, edgeRect);
    expect(Number.isFinite(summary.surroundLuminance)).toBe(true);
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `npx vitest run src/debug/lightingProbe.test.ts`
Expected: FAIL with "Failed to resolve import './lightingProbe'".

- [ ] **Step 4: Write the implementation**

Create `src/debug/lightingProbe.ts`:

```ts
import { Box3, Vector3, type Camera } from 'three';

/** Drawing-buffer pixels, bottom-left origin (the `readPixels` convention). */
export interface PixelRect {
  readonly x: number;
  readonly y: number;
  readonly width: number;
  readonly height: number;
}

export interface FrameSummary {
  /** Mean relative luminance (linear, 0–1) inside the player's screen box. */
  readonly playerLuminance: number;
  /** Mean relative luminance of the ring around that box. */
  readonly surroundLuminance: number;
  /** |player − surround| / max(player, surround): 0 = merged, 1 = fully separated. */
  readonly separation: number;
  /** Share of all frame pixels whose brightest channel is below 10/255. */
  readonly blackShare: number;
}

const NEAR_BLACK_CHANNEL = 10;
// The surround ring extends this fraction of the box size beyond each side.
const SURROUND_MARGIN = 0.5;

function channelToLinear(value: number): number {
  const c = value / 255;
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}

function luminanceAt(pixels: Uint8Array, index: number): number {
  return (
    0.2126 * channelToLinear(pixels[index]) +
    0.7152 * channelToLinear(pixels[index + 1]) +
    0.0722 * channelToLinear(pixels[index + 2])
  );
}

/**
 * Summarises one rendered frame for lighting comparisons. The player box is a
 * projected bounding box, so it includes some background around the figure;
 * compare values between captures of the same view, not across views.
 */
export function summariseFrame(
  pixels: Uint8Array,
  width: number,
  height: number,
  rect: PixelRect,
): FrameSummary {
  const marginX = Math.round(rect.width * SURROUND_MARGIN);
  const marginY = Math.round(rect.height * SURROUND_MARGIN);
  const outerLeft = Math.max(0, rect.x - marginX);
  const outerRight = Math.min(width, rect.x + rect.width + marginX);
  const outerBottom = Math.max(0, rect.y - marginY);
  const outerTop = Math.min(height, rect.y + rect.height + marginY);

  let playerTotal = 0;
  let playerCount = 0;
  let surroundTotal = 0;
  let surroundCount = 0;
  let blackCount = 0;

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const index = (y * width + x) * 4;
      if (
        Math.max(pixels[index], pixels[index + 1], pixels[index + 2]) <
        NEAR_BLACK_CHANNEL
      ) {
        blackCount += 1;
      }
      const insidePlayer =
        x >= rect.x && x < rect.x + rect.width &&
        y >= rect.y && y < rect.y + rect.height;
      const insideOuter =
        x >= outerLeft && x < outerRight && y >= outerBottom && y < outerTop;
      if (insidePlayer) {
        playerTotal += luminanceAt(pixels, index);
        playerCount += 1;
      } else if (insideOuter) {
        surroundTotal += luminanceAt(pixels, index);
        surroundCount += 1;
      }
    }
  }

  const playerLuminance = playerCount > 0 ? playerTotal / playerCount : 0;
  const surroundLuminance = surroundCount > 0 ? surroundTotal / surroundCount : 0;
  const brighter = Math.max(playerLuminance, surroundLuminance, 1e-4);
  return {
    playerLuminance,
    surroundLuminance,
    separation: Math.abs(playerLuminance - surroundLuminance) / brighter,
    blackShare: blackCount / (width * height),
  };
}

/** Projects a world-space box to a drawing-buffer rectangle, or null if off-screen. */
export function projectToPixelRect(
  box: Box3,
  camera: Camera,
  width: number,
  height: number,
): PixelRect | null {
  const corner = new Vector3();
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (let i = 0; i < 8; i += 1) {
    corner.set(
      i & 1 ? box.max.x : box.min.x,
      i & 2 ? box.max.y : box.min.y,
      i & 4 ? box.max.z : box.min.z,
    ).project(camera);
    minX = Math.min(minX, corner.x);
    minY = Math.min(minY, corner.y);
    maxX = Math.max(maxX, corner.x);
    maxY = Math.max(maxY, corner.y);
  }
  const left = Math.max(0, Math.floor(((minX + 1) / 2) * width));
  const right = Math.min(width, Math.ceil(((maxX + 1) / 2) * width));
  const bottom = Math.max(0, Math.floor(((minY + 1) / 2) * height));
  const top = Math.min(height, Math.ceil(((maxY + 1) / 2) * height));
  if (right <= left || top <= bottom) {
    return null;
  }
  return { x: left, y: bottom, width: right - left, height: top - bottom };
}
```

- [ ] **Step 5: Run the tests**

Run: `npx vitest run src/debug/lightingProbe.test.ts`
Expected: 4 passed.

- [ ] **Step 6: Wire the dev probe into `src/main.ts`**

Add `Box3` to the existing `three` import in `src/main.ts`, and add this import:

```ts
import { projectToPixelRect, summariseFrame } from './debug/lightingProbe';
```

Inside the existing `if (import.meta.env.DEV) { (window as ...).zealot = { ... } }` block, add a `lighting` entry to the object literal:

```ts
    lighting: {
      /**
       * Renders one frame and reads it back immediately, before the browser
       * can clear the drawing buffer. Dev-only: readPixels stalls the GPU.
       */
      probe: () => {
        renderer.info.reset();
        postProcessing.render(elapsedSeconds);
        const gl = renderer.getContext();
        const width = gl.drawingBufferWidth;
        const height = gl.drawingBufferHeight;
        const pixels = new Uint8Array(width * height * 4);
        gl.readPixels(0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
        const rect = projectToPixelRect(
          new Box3().setFromObject(player.object),
          camera,
          width,
          height,
        );
        const stats = world.getLightingStats();
        return {
          ...(rect ? summariseFrame(pixels, width, height, rect) : {}),
          drawCalls: renderer.info.render.calls,
          activeLocalLightGroups: stats.activeLocalLightGroups,
        };
      },
    },
```

`elapsedSeconds` is declared with `let` further down the file. The probe runs only when called from the console, after module evaluation, so the reference is safe.

- [ ] **Step 7: Verify in the browser**

Run: `npm run build` (expected: passes), then start the `zealot-dev` preview, open `/zealot-of-harperhey/?view=west-street&overlays=off`, wait for the world to load, and evaluate `window.zealot.lighting.probe()`.
Expected: an object with finite `playerLuminance`, `surroundLuminance`, `separation`, `blackShare` and a `drawCalls` number.

- [ ] **Step 8: Commit**

```bash
git add package.json package-lock.json src/debug/lightingProbe.ts src/debug/lightingProbe.test.ts src/main.ts
git commit -m "Add a dev lighting probe and Vitest for lighting logic"
```

---

### Task 2: Fixed capture views and the baseline

**Files:**
- Modify: `src/main.ts` (the `developmentViews` table)
- Create: `scripts/lighting-captures.playwright.js`
- Create: `renders/lighting-captures/2026-09-21-baseline/` (PNG captures) and `renders/lighting-captures/2026-09-21-baseline/metrics.json`

**Interfaces:**
- Consumes: `window.zealot.lighting.probe()` from Task 1.
- Produces: views `start`, `public-light-pool-front`, `hive-entrance`, `car-park`, and a corrected `spice-cabin`. The baseline metrics file is what later tasks' acceptance checks compare against.

- [ ] **Step 1: Fix and add dev views**

In `src/main.ts`'s `developmentViews`, add:

```ts
    start: [0, 3.5],
    // The same pool as `public-light-pool`, seen from the lamp's side so the
    // lit face of the rider is towards the camera.
    'public-light-pool-front': [-20, -19.8, Math.PI, 0.18],
    'hive-entrance': [33.5, 20, -Math.PI / 2, 0.14],
    'car-park': [36, -8, -Math.PI / 2 - 0.5, 0.2],
```

Then fix `spice-cabin`. Load `?view=spice-cabin&overlays=on`, find the collision outline the player is being pushed out of, and move the view's x/z to the nearest point on South Road pavement where `window.zealot.player.position` after load equals the tuple (within 0.05 m). Keep the yaw and pitch. Check `spice-cabin-close` the same way.

Yaw is in the camera's orbit convention. If `public-light-pool-front` or `hive-entrance` does not frame its subject, adjust yaw in steps of π/8 until it does, and record the final value.

- [ ] **Step 2: Write the capture routine**

Create `scripts/lighting-captures.playwright.js`:

```js
// Run through the Playwright MCP tool `browser_run_code_unsafe` with
// `filename: "scripts/lighting-captures.playwright.js"`, after navigating the
// Playwright page to the running dev server (any path). Screenshots go to
// renders/lighting-captures/latest/; the metrics JSON is the return value —
// save it next to the screenshots as metrics.json, then rename `latest` to
// `<date>-<label>`.
async (page) => {
  const origin = new URL(page.url()).origin;
  const out = 'renders/lighting-captures/latest';
  const medium = [
    'start', 'public-light-pool', 'public-light-pool-front',
    'between-light-pools', 'bus-shelter', 'dreams-angle', 'come-through-lab',
    'village-books', 'greek-gyros', 'hive-entrance', 'car-park', 'west-street',
    'south-road', 'real-camera', 'advanced-photo', 'spice-cabin', 'north-road',
    'park-florist',
  ];
  const critical = [
    'public-light-pool', 'between-light-pools', 'come-through-lab',
    'greek-gyros', 'south-road',
  ];
  const runs = [
    ...medium.map((view) => ({ view, quality: 'medium' })),
    ...critical.map((view) => ({ view, quality: 'low' })),
    ...critical.map((view) => ({ view, quality: 'high' })),
  ];
  await page.setViewportSize({ width: 1280, height: 720 });
  const metrics = {};
  for (const { view, quality } of runs) {
    await page.goto(
      `${origin}/zealot-of-harperhey/?view=${view}&quality=${quality}&overlays=off`,
    );
    await page.waitForFunction(() => Boolean(window.zealot), null, { timeout: 60000 });
    // Assets stream in after zealot exists; lights fade over ~0.25 s.
    await page.waitForTimeout(9000);
    await page.screenshot({ path: `${out}/${view}-${quality}.png` });
    metrics[`${view}-${quality}`] = await page.evaluate(() => window.zealot.lighting.probe());
  }
  return JSON.stringify(metrics, null, 2);
};
```

- [ ] **Step 3: Capture the baseline**

With the `zealot-dev` preview running, point the Playwright page at it (`browser_navigate` to `http://localhost:<port>/zealot-of-harperhey/`) and run the script through `browser_run_code_unsafe` with the `filename` above. Save the returned JSON as `renders/lighting-captures/latest/metrics.json`, then run:

```bash
mv renders/lighting-captures/latest renders/lighting-captures/2026-09-21-baseline
```

Expected: 28 PNGs and a metrics file with 28 entries. Open `public-light-pool-front-medium.png` and confirm the rider's lamp side faces the camera.

- [ ] **Step 4: Commit**

```bash
git add src/main.ts scripts/lighting-captures.playwright.js renders/lighting-captures/2026-09-21-baseline
git commit -m "Add fixed lighting capture views and record the lighting baseline"
```

---

### Task 3: View-aware location lights

**Files:**
- Modify: `src/world/localLighting.ts`
- Modify: `src/world/createWorld.ts` (`World.update` signature and the call into `localLights.update`)
- Modify: `src/main.ts` (pass the camera pose)
- Test: `src/world/localLighting.test.ts`

**Interfaces:**
- Produces: `export interface LocalLightViewer { readonly position: Vector3; readonly forward: Vector3 }`, `LocalLightRegistry.update(deltaTime: number, playerPosition: Vector3, viewer?: LocalLightViewer): void`, and `World.update(deltaTime: number, playerPosition: Vector3, viewer?: LocalLightViewer): void`.

**Rule:** a `location-relevance` installation qualifies only if it is inside its activation radius **and** either (a) its lit sphere overlaps the camera's view cone, or (b) it reaches the player's torso (contribution ratio within range). A shop light behind the camera still lights the rider and the pavement they stand on, so (b) keeps it. A light that is behind the camera and too far to reach the rider is wasted, so it no longer takes a slot.

- [ ] **Step 1: Write the failing tests**

Create `src/world/localLighting.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { Group, PointLight, Vector3 } from 'three';
import { LocalLightRegistry, type LocalLightViewer } from './localLighting';

function pointLight(name: string, x: number, y: number, z: number, distance = 8): PointLight {
  const light = new PointLight(0xffffff, 5, distance, 2);
  light.name = name;
  light.position.set(x, y, z);
  return light;
}

// Camera 5.6 m behind a player at the origin, looking towards -Z.
const player = new Vector3(0, 0, 0);
const viewer: LocalLightViewer = {
  position: new Vector3(0, 1.8, 5.6),
  forward: new Vector3(0, 0, -1),
};

function registryWith(budget: number, ...installs: [string, PointLight[]][]) {
  const registry = new LocalLightRegistry(new Group(), budget);
  for (const [name, lights] of installs) {
    registry.register({
      name,
      lights,
      selectionMode: 'location-relevance',
      activationRadius: 20,
    });
  }
  return registry;
}

describe('LocalLightRegistry view-aware selection', () => {
  it('selects an in-view location light that cannot reach the player', () => {
    const registry = registryWith(4, ['Ahead', [pointLight('ahead', 0, 3, -14)]]);
    registry.update(0.016, player, viewer);
    expect(registry.getStats().activeLocalLightGroups).toEqual(['Ahead']);
  });

  it('skips a location light behind the camera that cannot reach the player', () => {
    const registry = registryWith(4, ['Behind', [pointLight('behind', 0, 3, 18)]]);
    registry.update(0.016, player, viewer);
    expect(registry.getStats().activeLocalLightGroups).toEqual([]);
  });

  it('keeps a light behind the camera when it reaches the player', () => {
    const registry = registryWith(4, ['Behind but close', [pointLight('close', 0, 3, 4, 9)]]);
    registry.update(0.016, player, viewer);
    expect(registry.getStats().activeLocalLightGroups).toEqual(['Behind but close']);
  });

  // The camera turns 66° (1.15 rad). The light's range sphere then sits about
  // 55° off-axis: past the 0.85 rad entry angle, inside the 1.05 rad exit angle.
  const turned: LocalLightViewer = {
    position: viewer.position,
    forward: new Vector3(Math.sin(1.15), 0, -Math.cos(1.15)),
  };

  it('keeps a selected light until it is well outside the view cone', () => {
    const registry = registryWith(4, ['Edge', [pointLight('edge', 0, 3, -16, 4)]]);
    registry.update(0.016, player, viewer);
    registry.update(0.016, player, turned);
    expect(registry.getStats().activeLocalLightGroups).toEqual(['Edge']);
  });

  it('does not newly select a light at that same angle', () => {
    const registry = registryWith(4, ['Edge', [pointLight('edge', 0, 3, -16, 4)]]);
    registry.update(0.016, player, turned);
    expect(registry.getStats().activeLocalLightGroups).toEqual([]);
  });

  it('never lights half of an atomic pair', () => {
    const registry = registryWith(1, [
      'Pair',
      [pointLight('left', -1, 3, -10), pointLight('right', 1, 3, -10)],
    ]);
    registry.update(0.016, player, viewer);
    expect(registry.getStats().activePointLights).toBe(0);
  });

  it('keeps distance-only behaviour when no viewer is supplied', () => {
    const registry = registryWith(4, ['Behind', [pointLight('behind', 0, 3, 18)]]);
    registry.update(0.016, player);
    expect(registry.getStats().activeLocalLightGroups).toEqual(['Behind']);
  });
});
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `npx vitest run src/world/localLighting.test.ts`
Expected: "skips a location light behind the camera" and "does not newly select a light at that same angle" FAIL (both lights are still selected). The other four pass already.

- [ ] **Step 3: Implement view relevance**

In `src/world/localLighting.ts`, add below `LocalLightRegistryStats`:

```ts
/** The camera pose used to skip location lights that light nothing in view. */
export interface LocalLightViewer {
  readonly position: Vector3;
  /** World-space view direction; only its horizontal part is used. */
  readonly forward: Vector3;
}
```

Add below the existing constants:

```ts
// Half-angle of the horizontal view cone a light's range sphere must touch.
// The 56° lens at 16:9 spans about ±43°; the margins let lights fade in just
// before their pool enters the frame and fade out after it has left.
const VIEW_ENTER_HALF_ANGLE = 0.85;
const VIEW_EXIT_HALF_ANGLE = 1.05;
```

Change the `update` signature and the filter:

```ts
  update(
    deltaTime: number,
    playerPosition: Vector3,
    viewer?: LocalLightViewer,
  ): void {
    const ranked = this.installations
      .filter((installation) => {
        this.measureContribution(installation, playerPosition);
        const exitMultiplier = installation.desired
          ? EXIT_CONTRIBUTION_RATIO
          : ENTER_CONTRIBUTION_RATIO;
        installation.selectionRatio =
          installation.selectionMode === 'location-relevance'
            ? installation.horizontalDistance /
              (installation.activationRadius ?? 1)
            : installation.contributionRatio;
        const withinPrimaryRange =
          installation.selectionRatio <= exitMultiplier;
        const withinOptionalActivationCap =
          installation.selectionMode === 'location-relevance' ||
          installation.activationRadius === undefined ||
          installation.horizontalDistance <=
            installation.activationRadius * exitMultiplier;
        // A location light earns a slot by lighting something in view, or by
        // reaching the rider, whose lit side may face away from the camera.
        const usefulToView =
          installation.selectionMode !== 'location-relevance' ||
          viewer === undefined ||
          installation.contributionRatio <= exitMultiplier ||
          this.touchesView(installation, viewer);
        return withinPrimaryRange && withinOptionalActivationCap && usefulToView;
      })
```

The rest of `update` is unchanged. Add this private method next to `measureContribution`:

```ts
  private touchesView(
    installation: RuntimeInstallation,
    viewer: LocalLightViewer,
  ): boolean {
    const forwardLength = Math.hypot(viewer.forward.x, viewer.forward.z);
    if (forwardLength < 1e-6) {
      return true;
    }
    const forwardX = viewer.forward.x / forwardLength;
    const forwardZ = viewer.forward.z / forwardLength;
    const halfAngle = installation.desired
      ? VIEW_EXIT_HALF_ANGLE
      : VIEW_ENTER_HALF_ANGLE;

    for (const { light } of installation.lights) {
      const deltaX = light.position.x - viewer.position.x;
      const deltaZ = light.position.z - viewer.position.z;
      const distance = Math.hypot(deltaX, deltaZ);
      if (distance <= light.distance) {
        return true;
      }
      const cosine = (deltaX * forwardX + deltaZ * forwardZ) / distance;
      const offAxis = Math.acos(Math.min(1, Math.max(-1, cosine)));
      const angularRadius = Math.asin(light.distance / distance);
      if (offAxis - angularRadius <= halfAngle) {
        return true;
      }
    }
    return false;
  }
```

- [ ] **Step 4: Run the tests**

Run: `npx vitest run src/world/localLighting.test.ts`
Expected: 7 passed.

- [ ] **Step 5: Pass the viewer through the world**

In `src/world/createWorld.ts`, add `type LocalLightViewer` to the `./localLighting` import, and change `World.update`:

```ts
  readonly update: (
    deltaTime: number,
    playerPosition: Vector3,
    viewer?: LocalLightViewer,
  ) => void;
```

In the returned object:

```ts
    update: (deltaTime, playerPosition, viewer) => {
      atmosphere.update(deltaTime);
      updatePickup(deltaTime);
      updatePublicIllumination(playerPosition);
      localLights.update(deltaTime, playerPosition, viewer);
    },
```

In `src/main.ts`, above `function frame`:

```ts
const lightingViewer = { position: new Vector3(), forward: new Vector3() };
```

In `frame`, immediately before `simulationClock.advance(...)`:

```ts
  // Last frame's camera pose is close enough for choosing which lights matter.
  camera.getWorldPosition(lightingViewer.position);
  camera.getWorldDirection(lightingViewer.forward);
```

and change the call inside the step callback to `world.update(fixedDelta, player.position, lightingViewer);`.

- [ ] **Step 6: Verify in the browser**

Run `npm run build` (expected: passes). Load `?view=come-through-lab&overlays=off` and evaluate `window.zealot.lighting.probe().activeLocalLightGroups`.
Expected: includes `Come Through Lab threshold`, and no longer contains both MCR1 groups plus Florist. With overlays on (H), walk slowly past Cass Art while orbiting the camera 360°. No light should visibly pop; they fade.

- [ ] **Step 7: Commit**

```bash
git add src/world/localLighting.ts src/world/localLighting.test.ts src/world/createWorld.ts src/main.ts
git commit -m "Skip location lights that neither reach the rider nor touch the view"
```

---

### Task 4: Public illumination module, character-lamp state, LOW slot

**Files:**
- Create: `src/world/publicIllumination.ts`
- Test: `src/world/publicIllumination.test.ts`
- Modify: `src/world/createWorld.ts` (`addPublicIlluminationResponse`, `createWorld`, `World`)

**Interfaces:**
- Produces: `POOL_FADE_START = 2.55`, `POOL_FADE_END = 4`, `poolResponse(distance: number): number`, `findNearestStreetlight(lights: readonly StreetlightDefinition[], x: number, z: number): { index: number; distance: number }`, `type StreetlightDefinition = readonly [x: number, z: number, color: number]`, `interface CharacterLampState { readonly position: Vector3; readonly color: Color; strength: number }`, and `World.characterLamp: CharacterLampState`.

- [ ] **Step 1: Write the failing tests**

Create `src/world/publicIllumination.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import {
  POOL_FADE_END,
  POOL_FADE_START,
  findNearestStreetlight,
  poolResponse,
} from './publicIllumination';

describe('poolResponse', () => {
  it('is full across the painted pool', () => {
    expect(poolResponse(0)).toBe(1);
    expect(poolResponse(POOL_FADE_START)).toBe(1);
  });

  it('is zero at and beyond the fade end', () => {
    expect(poolResponse(POOL_FADE_END)).toBe(0);
    expect(poolResponse(9)).toBe(0);
  });

  it('is a smooth half-way at the midpoint', () => {
    expect(poolResponse((POOL_FADE_START + POOL_FADE_END) / 2)).toBeCloseTo(0.5, 5);
  });

  it('never increases with distance', () => {
    let previous = 1;
    for (let d = 0; d <= 5; d += 0.05) {
      const value = poolResponse(d);
      expect(value).toBeLessThanOrEqual(previous + 1e-9);
      previous = value;
    }
  });
});

describe('findNearestStreetlight', () => {
  const lights = [
    [0, 0, 0xffffff],
    [8, 0, 0xff0000],
    [0, 10, 0x00ff00],
  ] as const;

  it('returns the nearest lamp and its horizontal distance', () => {
    expect(findNearestStreetlight(lights, 6, 1)).toEqual({
      index: 1,
      distance: Math.hypot(2, 1),
    });
  });

  it('keeps the first lamp on an exact tie', () => {
    expect(findNearestStreetlight(lights, 4, 0).index).toBe(0);
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `npx vitest run src/world/publicIllumination.test.ts`
Expected: FAIL, "Failed to resolve import './publicIllumination'".

- [ ] **Step 3: Implement the module**

Create `src/world/publicIllumination.ts`:

```ts
import { Color, Vector3 } from 'three';

export type StreetlightDefinition = readonly [x: number, z: number, color: number];

/** Response is full across the 2.45 m painted pool and gone before the darkness. */
export const POOL_FADE_START = 2.55;
export const POOL_FADE_END = 4;

export function poolResponse(distance: number): number {
  const t = Math.max(
    0,
    Math.min(1, (POOL_FADE_END - distance) / (POOL_FADE_END - POOL_FADE_START)),
  );
  return t * t * (3 - 2 * t);
}

export function findNearestStreetlight(
  lights: readonly StreetlightDefinition[],
  x: number,
  z: number,
): { index: number; distance: number } {
  let index = 0;
  let nearestSquared = Number.POSITIVE_INFINITY;
  lights.forEach(([lightX, lightZ], candidate) => {
    const squared = (lightX - x) ** 2 + (lightZ - z) ** 2;
    if (squared < nearestSquared) {
      nearestSquared = squared;
      index = candidate;
    }
  });
  return { index, distance: Math.sqrt(nearestSquared) };
}

/**
 * The nearest public lamp as the rider's own materials see it. It drives a
 * shader term on the player only, so it never occupies a local-light slot.
 */
export interface CharacterLampState {
  readonly position: Vector3;
  readonly color: Color;
  /** 0 outside every pool, 1 inside the painted pool. */
  strength: number;
}
```

- [ ] **Step 4: Run the tests**

Run: `npx vitest run src/world/publicIllumination.test.ts`
Expected: 6 passed.

- [ ] **Step 5: Rewrite `addPublicIlluminationResponse`**

In `src/world/createWorld.ts`, add `Color` to the `three` import and add:

```ts
import {
  findNearestStreetlight,
  poolResponse,
  type CharacterLampState,
} from './publicIllumination';
```

Replace the whole `addPublicIlluminationResponse` function with:

```ts
const STREETLIGHT_HEAD_HEIGHT = 3.85;

function addPublicIlluminationResponse(
  localLights: LocalLightRegistry,
  registerProxy: boolean,
): { characterLamp: CharacterLampState; update: (playerPosition: Vector3) => void } {
  const characterLamp: CharacterLampState = {
    position: new Vector3(STREETLIGHTS[0][0], STREETLIGHT_HEAD_HEIGHT, STREETLIGHTS[0][1]),
    color: new Color(STREETLIGHTS[0][2]),
    strength: 0,
  };

  // LOW has two slots. The character term already makes the rider answer the
  // pool there, so the proxy's slot goes to the location instead.
  const light = registerProxy
    ? createManagedPointLight(
        'Nearest public streetlight response',
        characterLamp.position.x,
        characterLamp.position.y,
        characterLamp.position.z,
        STREETLIGHTS[0][2],
        VISUAL_STYLE.lighting.streetLightIntensity,
        VISUAL_STYLE.lighting.streetLightDistance,
      )
    : null;
  if (light) {
    localLights.register({
      name: 'Public illumination pool',
      lights: [light],
      priority: 1.7,
      activationRadius: 4,
      intensityScale: () => characterLamp.strength,
    });
  }

  return {
    characterLamp,
    update: (playerPosition: Vector3): void => {
      const nearest = findNearestStreetlight(
        STREETLIGHTS,
        playerPosition.x,
        playerPosition.z,
      );
      const [x, z, color] = STREETLIGHTS[nearest.index];
      characterLamp.position.set(x, STREETLIGHT_HEAD_HEIGHT, z);
      characterLamp.color.setHex(color);
      characterLamp.strength = poolResponse(nearest.distance);
      if (light) {
        light.position.copy(characterLamp.position);
        light.color.setHex(color);
      }
    },
  };
}
```

In `createWorld`, replace `const updatePublicIllumination = addPublicIlluminationResponse(localLights);` with:

```ts
  const publicIllumination = addPublicIlluminationResponse(
    localLights,
    maximumActiveLocalLights > 2,
  );
```

In the returned `update`, change `updatePublicIllumination(playerPosition);` to `publicIllumination.update(playerPosition);`. Add `characterLamp: publicIllumination.characterLamp,` to the returned object and `readonly characterLamp: CharacterLampState;` to `interface World`.

Check the streetlight spacing: the closest pair of lamps is (8, 19) and (16, 19), 8 m apart. `POOL_FADE_END` (4 m) × 2 = 8 m, so the proxy only jumps between lamps while its strength is 0. If a later layout puts two lamps closer than 8 m, the proxy will pop. Add this comment above `STREETLIGHTS`:

```ts
// Keep lamps at least 2 × POOL_FADE_END (8 m) apart: the public proxy and the
// rider's lamp response move to the nearest lamp, and only do so invisibly
// while both pools are out of reach.
```

- [ ] **Step 6: Verify**

Run: `npx vitest run && npm run build`. Expected: all tests pass and the build passes. Load `?view=public-light-pool&overlays=off` and run `zealot.lighting.probe().activeLocalLightGroups`. Expected: it includes `Public illumination pool`. Repeat with `&quality=low`. Expected: it does not. The rider's response to the lamp strength is checked visually in Task 5 Step 4.

- [ ] **Step 7: Commit**

```bash
git add src/world/publicIllumination.ts src/world/publicIllumination.test.ts src/world/createWorld.ts
git commit -m "Track the nearest public lamp for the rider and free the proxy slot on LOW"
```

---

### Task 5: Rider lamp response instead of the blue ambient gain

**Files:**
- Modify: `src/player/PlayerController.ts:115-175` (`PLAYER_INDIRECT_VISIBILITY_GAIN`, `applyPlayerVisibilityPolicy`) and add a public method.
- Modify: `src/main.ts` (feed the lamp each frame, dev tuning hook)

**Interfaces:**
- Consumes: `CharacterLampState` from Task 4 (`world.characterLamp`).
- Produces: `PlayerController.setCharacterLamp(lamp: CharacterLampState, camera: Camera): void` and the exported tunables `CHARACTER_LIGHT: { floor: number; lampWrap: number; lampRim: number }`.

**Shader note:** in Three 0.185, `lights_fragment_begin` declares `geometryPosition` (view space), `geometryNormal` and `geometryViewDir` in `main()`. Before editing, confirm with:
`grep -n "geometryViewDir\|geometryPosition" node_modules/three/src/renderers/shaders/ShaderChunk/lights_fragment_begin.glsl.js`
If the names differ, use the ones printed.

- [ ] **Step 1: Replace the gain with uniforms**

In `src/player/PlayerController.ts`, add `Color`, `Vector3` and `type Camera` to the `three` import (keep the existing names), add `import type { CharacterLampState } from '../world/publicIllumination';`, and replace everything from `const PLAYER_INDIRECT_VISIBILITY_GAIN` to the end of `applyPlayerVisibilityPolicy` with:

```ts
/**
 * Start values; Daniel tunes them live with `zealot.characterLight`.
 * `floor` is a neutral, albedo-weighted lift: grey, where the old 1.55×
 * ambient gain amplified the blue hemisphere sky. `lampWrap` lets the nearest
 * public pool colour the side of the rider facing it; `lampRim` adds a faint
 * pool-coloured edge so the figure separates even when the lamp is behind them.
 */
export const CHARACTER_LIGHT = {
  floor: 0.03,
  lampWrap: 0.9,
  lampRim: 0.05,
};

const PLAYER_CHARACTER_LIGHT_SHADER_KEY = 'player-character-light-v2';

const characterLightUniforms = {
  uCharacterFloor: { value: CHARACTER_LIGHT.floor },
  uCharacterLampViewPosition: { value: new Vector3() },
  uCharacterLampColor: { value: new Color() },
  uCharacterLampStrength: { value: 0 },
  uCharacterLampWrap: { value: CHARACTER_LIGHT.lampWrap },
  uCharacterLampRim: { value: CHARACTER_LIGHT.lampRim },
};

const CHARACTER_LIGHT_DECLARATIONS = `
uniform float uCharacterFloor;
uniform vec3 uCharacterLampViewPosition;
uniform vec3 uCharacterLampColor;
uniform float uCharacterLampStrength;
uniform float uCharacterLampWrap;
uniform float uCharacterLampRim;
`;

const CHARACTER_LIGHT_TERM = `
{
  reflectedLight.indirectDiffuse += material.diffuseColor * uCharacterFloor;
  vec3 characterLampDirection = normalize(uCharacterLampViewPosition - geometryPosition);
  float characterLampWrap = clamp((dot(geometryNormal, characterLampDirection) + 0.35) / 1.35, 0.0, 1.0);
  float characterRim = pow(1.0 - clamp(dot(geometryNormal, geometryViewDir), 0.0, 1.0), 3.0);
  vec3 characterLamp = uCharacterLampColor * uCharacterLampStrength;
  reflectedLight.indirectDiffuse += material.diffuseColor * characterLamp * characterLampWrap * uCharacterLampWrap;
  reflectedLight.indirectDiffuse += characterLamp * characterRim * uCharacterLampRim;
}
`;

function needsCharacterLight(material: MeshStandardMaterial): boolean {
  const name = material.name;
  return (
    (name.startsWith('PC_Denim_') && name !== 'PC_Denim_Hardware') ||
    (name.startsWith('PC_Leather_') && name !== 'PC_Leather_Hardware') ||
    name === 'PC_Hair_Cornrow'
  );
}

/**
 * Keep the authored near-black clothing. Direct sodium, fluorescent and cold
 * light is untouched; this adds a neutral floor plus a response to the nearest
 * public pool, so the rider answers the streetlight without a light slot.
 */
function applyCharacterLightPolicy(character: Group): void {
  const configured = new Set<MeshStandardMaterial>();

  character.traverse((child) => {
    if (!(child instanceof Mesh)) {
      return;
    }
    const materials = Array.isArray(child.material)
      ? child.material
      : [child.material];

    for (const material of materials) {
      if (
        !(material instanceof MeshStandardMaterial) ||
        configured.has(material) ||
        !needsCharacterLight(material)
      ) {
        continue;
      }

      configured.add(material);
      const previousOnBeforeCompile = material.onBeforeCompile;
      const previousProgramCacheKey = material.customProgramCacheKey();
      material.onBeforeCompile = (shader, renderer) => {
        previousOnBeforeCompile.call(material, shader, renderer);
        const anchor = '#include <lights_fragment_end>';
        if (!shader.fragmentShader.includes(anchor)) {
          return;
        }
        Object.assign(shader.uniforms, characterLightUniforms);
        shader.fragmentShader = shader.fragmentShader
          .replace('#include <common>', `#include <common>\n${CHARACTER_LIGHT_DECLARATIONS}`)
          .replace(anchor, `${anchor}\n${CHARACTER_LIGHT_TERM}`);
      };
      material.customProgramCacheKey = () =>
        `${previousProgramCacheKey}|${PLAYER_CHARACTER_LIGHT_SHADER_KEY}`;
      material.needsUpdate = true;
    }
  });
}
```

Rename the call site at the old line 481 from `applyPlayerVisibilityPolicy(character);` to `applyCharacterLightPolicy(character);`.

Add this method to `PlayerController` (next to `get position()`):

```ts
  /** Called once per rendered frame, after the camera has moved. */
  setCharacterLamp(lamp: CharacterLampState, camera: Camera): void {
    characterLightUniforms.uCharacterLampViewPosition.value
      .copy(lamp.position)
      .applyMatrix4(camera.matrixWorldInverse);
    characterLightUniforms.uCharacterLampColor.value.copy(lamp.color);
    characterLightUniforms.uCharacterLampStrength.value = lamp.strength;
    characterLightUniforms.uCharacterFloor.value = CHARACTER_LIGHT.floor;
    characterLightUniforms.uCharacterLampWrap.value = CHARACTER_LIGHT.lampWrap;
    characterLightUniforms.uCharacterLampRim.value = CHARACTER_LIGHT.lampRim;
  }
```

- [ ] **Step 2: Feed it each frame and add the dev hook**

In `src/main.ts`, import `CHARACTER_LIGHT` next to `PlayerController`. In `frame`, after `titleCamera.apply(cameraDelta);` and before `renderer.info.reset();`, add:

```ts
  camera.updateMatrixWorld();
  player.setCharacterLamp(world.characterLamp, camera);
```

Add `characterLight: CHARACTER_LIGHT,` to the dev `zealot` object, so the values can be tuned live with `zealot.characterLight.floor = 0.05`.

- [ ] **Step 3: Calibrate the floor against the baseline**

Run: `npm run build` (expected: passes). Load `?view=west-street&overlays=off` and run `zealot.lighting.probe()`. Adjust `zealot.characterLight.floor` until `playerLuminance` is within ±10% of `west-street-medium.playerLuminance` in the baseline metrics. That keeps the old lift's brightness but in grey instead of blue. Write the calibrated value into `CHARACTER_LIGHT.floor`.

- [ ] **Step 4: Check the pool response**

Load `public-light-pool-front` and `public-light-pool`. Take a screenshot of each at `lampRim` 0, 0.05 and 0.1 (set live).
Expected: in `-front` the rider's chest and face take the sodium colour. In the back view the silhouette edge picks up a thin warm edge, but with no outline or halo visible at 1280 × 720. Pick the largest `lampRim` that shows no visible outline, and write it into `CHARACTER_LIGHT.lampRim`. At `between-light-pools`, lamp strength is 0 and the rider reads near-black neutral, not navy.

- [ ] **Step 5: Commit**

```bash
git add src/player/PlayerController.ts src/main.ts
git commit -m "Replace the rider's blue ambient gain with a neutral floor and a pool response"
```

---

### Task 6: Soft painted pools and merged streetlights

**Files:**
- Create: `src/rendering/lightPoolTexture.ts`
- Test: `src/rendering/lightPoolTexture.test.ts`
- Modify: `src/world/createWorld.ts` (replace per-lamp `addStreetlight` with a batched builder)

**Interfaces:**
- Produces: `lightPoolFalloff(radius: number): number` (0–1 input, 1 at centre, 0 at the rim) and `getLightPoolTexture(): DataTexture`.

- [ ] **Step 1: Write the failing test**

Create `src/rendering/lightPoolTexture.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { getLightPoolTexture, lightPoolFalloff } from './lightPoolTexture';

describe('lightPoolFalloff', () => {
  it('is brightest at the centre and zero at the rim', () => {
    expect(lightPoolFalloff(0)).toBe(1);
    expect(lightPoolFalloff(1)).toBe(0);
    expect(lightPoolFalloff(1.4)).toBe(0);
  });

  it('falls off monotonically', () => {
    let previous = 1;
    for (let r = 0; r <= 1; r += 0.02) {
      expect(lightPoolFalloff(r)).toBeLessThanOrEqual(previous + 1e-9);
      previous = lightPoolFalloff(r);
    }
  });
});

describe('getLightPoolTexture', () => {
  it('is cached and has a dark border', () => {
    const texture = getLightPoolTexture();
    expect(getLightPoolTexture()).toBe(texture);
    const { data, width } = texture.image as { data: Uint8Array; width: number };
    expect(data[0]).toBe(0);
    const centre = ((width / 2) * width + width / 2) * 4;
    expect(data[centre]).toBeGreaterThan(200);
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `npx vitest run src/rendering/lightPoolTexture.test.ts`
Expected: FAIL, unresolved import.

- [ ] **Step 3: Implement**

Create `src/rendering/lightPoolTexture.ts`:

```ts
import { DataTexture, LinearFilter, RGBAFormat } from 'three';

const SIZE = 64;
let cached: DataTexture | null = null;

/** Light on the ground under a lamp: a broad core that thins towards the rim. */
export function lightPoolFalloff(radius: number): number {
  if (radius >= 1) {
    return 0;
  }
  return (1 - radius * radius) ** 2.2;
}

function unevenness(x: number, y: number): number {
  const n = Math.sin(x * 12.9898 + y * 78.233) * 43758.5453;
  return n - Math.floor(n);
}

/**
 * Greyscale mask for the painted streetlight pools. The slight deterministic
 * unevenness keeps the pool reading as light on a worn surface rather than a
 * vector disc, without the broken-reflection confetti it replaces.
 */
export function getLightPoolTexture(): DataTexture {
  if (cached) {
    return cached;
  }
  const data = new Uint8Array(SIZE * SIZE * 4);
  for (let y = 0; y < SIZE; y += 1) {
    for (let x = 0; x < SIZE; x += 1) {
      const u = ((x + 0.5) / SIZE) * 2 - 1;
      const v = ((y + 0.5) / SIZE) * 2 - 1;
      const falloff = lightPoolFalloff(Math.hypot(u, v));
      const value = Math.round(255 * falloff * (0.9 + 0.1 * unevenness(x, y)));
      const index = (y * SIZE + x) * 4;
      data[index] = value;
      data[index + 1] = value;
      data[index + 2] = value;
      data[index + 3] = 255;
    }
  }
  cached = new DataTexture(data, SIZE, SIZE, RGBAFormat);
  cached.magFilter = LinearFilter;
  cached.minFilter = LinearFilter;
  cached.needsUpdate = true;
  return cached;
}
```

- [ ] **Step 4: Run the tests**

Run: `npx vitest run src/rendering/lightPoolTexture.test.ts`
Expected: 3 passed.

- [ ] **Step 5: Record the draw-call baseline for this view**

Read `drawCalls` for `public-light-pool-medium` and `south-road-medium` from `renders/lighting-captures/2026-09-21-baseline/metrics.json`, and write them down for Step 8.

- [ ] **Step 6: Replace `addStreetlight` with a batched builder**

The names `Public illumination streetlight`, `Streetlight painted pool` and `Broken streetlight reflection` are referenced only where they are set (checked 21 Sept: `grep -rn "painted pool\|Public illumination streetlight\|Broken streetlight" src`). Re-run that grep before editing. If anything else now reads them, keep those names on the merged meshes.

In `src/world/createWorld.ts`, add `AdditiveBlending`, `DoubleSide`, `Euler`, `Matrix4` and `Quaternion` to the `three` import if missing, and add `import { getLightPoolTexture } from '../rendering/lightPoolTexture';`. Replace the whole `addStreetlight` function with:

```ts
/**
 * Builds every public streetlight as a handful of merged meshes: one for all
 * poles and, per lamp colour, one each for heads, painted pools and the two
 * broken reflections. Twenty separate lamps cost about 100 draw calls.
 */
function addStreetlights(root: Group, streetlights: typeof STREETLIGHTS): void {
  const placed = (
    geometry: BufferGeometry,
    x: number,
    y: number,
    z: number,
    rotationX = 0,
    rotationY = 0,
  ): BufferGeometry =>
    geometry.clone().applyMatrix4(
      new Matrix4().compose(
        new Vector3(x, y, z),
        new Quaternion().setFromEuler(new Euler(rotationX, rotationY, 0)),
        new Vector3(1, 1, 1),
      ),
    );

  type ColourParts = {
    heads: BufferGeometry[];
    pools: BufferGeometry[];
    longReflections: BufferGeometry[];
    sideReflections: BufferGeometry[];
  };
  const poles: BufferGeometry[] = [];
  const byColour = new Map<number, ColourParts>();

  for (const [x, z, color] of streetlights) {
    poles.push(placed(getCylinderGeometry(0.075, 0.105, 4.2, 6), x, 2.1, z));
    let parts = byColour.get(color);
    if (!parts) {
      parts = { heads: [], pools: [], longReflections: [], sideReflections: [] };
      byColour.set(color, parts);
    }
    parts.heads.push(placed(getBoxGeometry(0.52, 0.16, 0.38), x, 4.18, z));
    parts.pools.push(placed(getCircleGeometry(2.45, 12), x, 0.035, z, -Math.PI / 2));
    parts.longReflections.push(
      placed(getBoxGeometry(0.7, 0.018, 4.9), x + 0.35, 0.04, z + 2.1, 0, 0.08),
    );
    parts.sideReflections.push(
      placed(getBoxGeometry(0.42, 0.018, 2.6), x - 0.72, 0.042, z + 1.25, 0, -0.2),
    );
  }

  const addMerged = (name: string, geometries: BufferGeometry[], material: Material) => {
    const merged = mergeGeometries(geometries, false);
    geometries.forEach((geometry) => geometry.dispose());
    if (!merged) {
      console.error(`[World] Could not merge ${name}.`);
      return;
    }
    const mesh = new Mesh(merged, material);
    mesh.name = name;
    root.add(mesh);
  };

  addMerged(
    'Public illumination streetlight poles',
    poles,
    createWorldMaterial('metal-oxidised-overhaul', { repeatX: 1, repeatY: 3, tint: 0x5c6063 }),
  );
  for (const [color, parts] of byColour) {
    addMerged('Public illumination streetlight heads', parts.heads, getBasicColorMaterial(color));
    addMerged(
      'Streetlight painted pool',
      parts.pools,
      new MeshBasicMaterial({
        color,
        map: getLightPoolTexture(),
        transparent: true,
        opacity: 0.3,
        blending: AdditiveBlending,
        depthWrite: false,
        side: DoubleSide,
      }),
    );
    addMerged(
      'Broken streetlight reflection',
      parts.longReflections,
      createAdditiveWorldMaterial('reflection-broken-overhaul', color, 0.25),
    );
    addMerged(
      'Secondary broken streetlight reflection',
      parts.sideReflections,
      createAdditiveWorldMaterial('reflection-broken-overhaul', color, 0.15),
    );
  }
}
```

If `getBoxGeometry`'s default segment arguments differ from what `createBox` used, pass the same arguments `createBox` passes (read `createBox` at `src/world/createWorld.ts:203`).

In `createWorld`, replace:

```ts
  for (const [x, z, color] of STREETLIGHTS) {
    addStreetlight(root, x, z, color);
    obstacles.push(circleObstacle('Streetlight pole', x, z, 0.12, 4.3));
  }
```

with:

```ts
  addStreetlights(root, STREETLIGHTS);
  for (const [x, z] of STREETLIGHTS) {
    obstacles.push(circleObstacle('Streetlight pole', x, z, 0.12, 4.3));
  }
```

- [ ] **Step 7: Build and check the look**

Run: `npx vitest run && npm run build`. Expected: pass. Load `public-light-pool`, `south-road` and `dreams-angle` and take screenshots.
Expected: each pool reads as a soft warm pool that fades into the paving and grass, with no scattered dashes. The broken reflection strips remain. Tune `opacity` (0.22–0.4) until the pool centre on grey paving is about as bright as the baseline pool's brightest dashes, then write the value in.

- [ ] **Step 8: Measure draw calls**

Run `zealot.lighting.probe().drawCalls` at `public-light-pool` and `south-road` on MEDIUM.
Expected: each is at least 60 lower than the Step 5 baseline number. If it isn't, check the scene for leftover per-lamp meshes: `zealot.scene.getObjectsByProperty('name', 'Public illumination streetlight')` should return `[]`.

- [ ] **Step 9: Commit**

```bash
git add src/rendering/lightPoolTexture.ts src/rendering/lightPoolTexture.test.ts src/world/createWorld.ts
git commit -m "Soften the painted streetlight pools and merge all streetlights into a few meshes"
```

---

### Task 7: Hive entrance cue and car-park pools

**Files:**
- Modify: `src/world/createWorld.ts` (`addTheHiveModel`, its caller at about line 2488, `STREETLIGHTS`)

**Interfaces:**
- Consumes: the `ACE_EntranceTriggerAnchor` node in `public/assets/models/the_hive.glb` (confirmed present 21 Sept), `LocalLightRegistry.register`, `createManagedPointLight`.

- [ ] **Step 1: Hive entrance cue from the authored anchor**

Change the signature to `async function addTheHiveModel(root: Group, location: WorldLocation, localLights: LocalLightRegistry): Promise<void>` and its call to `void addTheHiveModel(root, location, localLights);`.

Inside, **move `mergeStaticModelMeshes(hive);` to after the anchor lookup** (merging can remove empties, and the performance doc says anchors are read before batching). After `root.add(hive);`, add:

```ts
    hive.updateWorldMatrix(true, true);
    const entrance = hive.getObjectByName('ACE_EntranceTriggerAnchor');
    if (entrance) {
      const position = entrance.getWorldPosition(new Vector3());
      // A precise cold municipal cue at the west door, set just proud of the
      // frontage towards the street; the building above stays moonlit.
      position.x -= 1.2;
      position.y = 3;
      localLights.register({
        name: 'The Hive entrance',
        lights: [
          createManagedPointLight(
            'The Hive entrance cue',
            position.x,
            position.y,
            position.z,
            VISUAL_STYLE.lighting.coldWhite,
            4,
            6,
          ),
        ],
        priority: 1.2,
        selectionMode: 'location-relevance',
        activationRadius: 14,
      });
    } else {
      console.warn('[World] The Hive entrance anchor is missing.');
    }
    mergeStaticModelMeshes(hive);
```

Load `?view=hive-entrance&overlays=on`. The Hive faces west, so the cue should sit on the street side of the doors. If it lands inside the building, flip the sign of the x offset and note why in the comment.

- [ ] **Step 2: Two isolated car-park pools**

Add two entries to the end of `STREETLIGHTS`:

```ts
  // Car park: two hard security pools with a wide dark gap between them.
  [38, -3, VISUAL_STYLE.lighting.coldWhite],
  [49, 4.5, VISUAL_STYLE.lighting.coldWhite],
```

These get a pole, collision, a painted pool, the public proxy and the rider response automatically. They are 13 m apart and more than 8 m from every other lamp and from the Arts Council pallet stack at (48, −3.4).

- [ ] **Step 3: Verify**

Run `npm run build` (expected: passes). Capture `hive-entrance`, `car-park` and `pallets-east` on MEDIUM and LOW, and run `zealot.lighting.probe()` at each.
Expected: at `hive-entrance`, `activeLocalLightGroups` includes `The Hive entrance` and the door plane is readable while the upper building stays moonlit. At `car-park` there are two separate pools with near-black asphalt between them. `blackShare` at `car-park` should fall by no more than 0.05 from its Task 2 baseline. Walking into either car-park pool colours the rider.

- [ ] **Step 4: Commit**

```bash
git add src/world/createWorld.ts
git commit -m "Light The Hive entrance from its anchor and add two isolated car-park pools"
```

---

### Task 8: Display-grade controls and A/B (defaults unchanged)

**Files:**
- Modify: `src/rendering/createPostProcessing.ts`
- Modify: `src/rendering/visualStyle.ts` (`VISUAL_STYLE.render`)
- Modify: `src/main.ts` (dev hook)

**Interfaces:**
- Produces: `PostProcessingPipeline.grade: { get(): GradeParameters; set(values: Partial<GradeParameters>): void }` and `GradeParameters { contrast: number; toeProtection: number; quantizationLevels: number; grainStrength: number; grainAfterQuantization: boolean }`.

**Why now, not last:** the audit put the grade review after every location pass. But the grade removes detail below about 0.03, and every later light gets judged through it. Tuning the grade after Tasks 3–7 (hierarchy fixed) and **before** the Blender-side CTL and Greek Gyros lighting passes avoids tuning those lights twice.

- [ ] **Step 1: Add the style values (current look preserved)**

In `VISUAL_STYLE.render` add:

```ts
    // 0 keeps the linear contrast that pulls near-blacks down by 0.025;
    // 1 fades contrast out below luminance 0.1 so it cannot crush them.
    toeProtection: 0,
    // false adds grain before quantisation (current); true adds it after, at
    // 60% strength, so grain cannot flip dark values between steps.
    grainAfterQuantization: false,
```

- [ ] **Step 2: Update the shader and expose parameters**

In `createPostProcessing.ts`, add the two uniforms to the `ShaderMaterial`:

```ts
        toeProtection: { value: VISUAL_STYLE.render.toeProtection },
        grainAfterQuantization: {
          value: VISUAL_STYLE.render.grainAfterQuantization ? 1 : 0,
        },
```

declare them in the fragment shader (`uniform float toeProtection; uniform float grainAfterQuantization;`), and replace the body of `main()` from `color = (color - 0.5) * contrast + 0.5;` to the end with:

```glsl
          vec3 contrasted = (color - 0.5) * contrast + 0.5;
          float toe = smoothstep(0.0, 0.1, luminance);
          color = mix(contrasted, mix(color, contrasted, toe), toeProtection);
          float shadowWeight = 0.4 + (1.0 - clamp(luminance, 0.0, 1.0)) * 0.6;
          float grain = hash(gl_FragCoord.xy + elapsedSeconds * vec2(17.0, 9.0)) - 0.5;
          color += grain * grainStrength * shadowWeight * (1.0 - grainAfterQuantization);
          float distanceFromCentre = distance(vUv, vec2(0.5));
          float vignette = smoothstep(
            0.48 - vignetteSoftness * 0.25,
            0.72 + vignetteSoftness * 0.25,
            distanceFromCentre
          );
          color *= 1.0 - vignette * vignetteStrength;
          float dither = (orderedDither(gl_FragCoord.xy) / 15.0 - 0.5)
            * ditherStrength;
          color = floor(clamp(color + dither, 0.0, 1.0)
            * quantizationLevels) / quantizationLevels;
          color += grain * grainStrength * 0.6 * shadowWeight * grainAfterQuantization;
          gl_FragColor = vec4(clamp(color, 0.0, 1.0), source.a);
```

Add to the interface and the returned object:

```ts
export interface GradeParameters {
  contrast: number;
  toeProtection: number;
  quantizationLevels: number;
  grainStrength: number;
  grainAfterQuantization: boolean;
}

export interface PostProcessingPipeline {
  readonly render: (elapsedSeconds?: number) => void;
  readonly resize: (width: number, height: number) => void;
  readonly grade: {
    readonly get: () => GradeParameters;
    readonly set: (values: Partial<GradeParameters>) => void;
  };
}
```

```ts
    grade: {
      get: () => ({
        contrast: grade.uniforms.contrast.value,
        toeProtection: grade.uniforms.toeProtection.value,
        quantizationLevels: grade.uniforms.quantizationLevels.value,
        grainStrength: grade.uniforms.grainStrength.value,
        grainAfterQuantization: grade.uniforms.grainAfterQuantization.value > 0.5,
      }),
      set: (values) => {
        if (values.contrast !== undefined) grade.uniforms.contrast.value = values.contrast;
        if (values.toeProtection !== undefined) grade.uniforms.toeProtection.value = values.toeProtection;
        if (values.quantizationLevels !== undefined) grade.uniforms.quantizationLevels.value = values.quantizationLevels;
        if (values.grainStrength !== undefined) grade.uniforms.grainStrength.value = values.grainStrength;
        if (values.grainAfterQuantization !== undefined) {
          grade.uniforms.grainAfterQuantization.value = values.grainAfterQuantization ? 1 : 0;
        }
      },
    },
```

In `main.ts` add `grade: postProcessing.grade,` to the dev `zealot` object. `createPostProcessing(...)` already runs before that object is built, so no reordering is needed.

- [ ] **Step 3: Confirm the default is pixel-identical**

Run `npm run build`. At `between-light-pools`, compare `zealot.lighting.probe()` before this task (Task 7's commit) and after, with a fixed `elapsedSeconds`. Grain is time-seeded, so compare `blackShare` and `playerLuminance` within ±0.002 rather than exact pixels.

- [ ] **Step 4: Capture the A/B set for Daniel**

At `between-light-pools`, `come-through-lab`, `park-florist`, `bus-shelter` and `dreams-angle` (MEDIUM), screenshot and probe each variant, set live with `zealot.grade.set(...)`:

| Variant | Values |
| --- | --- |
| A current | `{ toeProtection: 0, quantizationLevels: 32, grainAfterQuantization: false }` |
| B protected toe | `{ toeProtection: 1 }` |
| C toe + 64 steps | `{ toeProtection: 1, quantizationLevels: 64 }` |
| D toe + grain after | `{ toeProtection: 1, grainAfterQuantization: true }` |
| E toe + 64 + grain after | `{ toeProtection: 1, quantizationLevels: 64, grainAfterQuantization: true }` |

Save them to `renders/lighting-captures/2026-09-21-grade-ab/<view>-<variant>.png` with a `metrics.json`.

- [ ] **Step 5: Commit the controls and captures (defaults unchanged)**

```bash
git add src/rendering/createPostProcessing.ts src/rendering/visualStyle.ts src/main.ts renders/lighting-captures/2026-09-21-grade-ab
git commit -m "Add protected-toe and grain-order grade controls with A/B captures"
```

- [ ] **Step 6: Daniel decides**

Show Daniel the A–E sheet for each view. The bus shelter is the colour benchmark (the audit's rule). Write his choice into `VISUAL_STYLE.render`, rerun Step 3's probe to confirm, and commit as "Adopt grade variant <X> after the A/B review". If he keeps A, record that in Task 10's audit follow-up and change nothing.

---

### Task 9: Moon angle experiment (defaults unchanged)

**Files:**
- Modify: `src/world/createWorld.ts` (expose global lights)
- Modify: `src/main.ts` (dev hook)

**Interfaces:**
- Produces: `World.globalLights: { readonly hemisphere: HemisphereLight; readonly moon: DirectionalLight }` and the dev hook `zealot.lighting.setMoonElevation(degrees: number, azimuthDegrees?: number)`.

**Hypothesis:** the moon sits at about 45° elevation, from `(-8, 14, 10)`. That fully lights every façade facing south-west, so unlit pale walls outshine practicals (observation 1). A steeper moon keeps the ground and roofs lit, so the route stays legible, while walls fall back and practicals win the verticals. Intensities stay the same. This costs nothing at runtime.

- [ ] **Step 1: Expose the lights**

In `createWorld`, keep a reference to the `HemisphereLight` (`const hemisphere = new HemisphereLight(...)`; `scene.add(hemisphere)`), add `globalLights: { hemisphere, moon: moonlight },` to the returned object, and add to `World`:

```ts
  readonly globalLights: {
    readonly hemisphere: HemisphereLight;
    readonly moon: DirectionalLight;
  };
```

- [ ] **Step 2: Dev hook**

In `main.ts`, add to the dev `zealot.lighting` object:

```ts
      setMoonElevation: (degrees: number, azimuthDegrees = 321.3) => {
        // Default azimuth reproduces the authored (-8, 14, 10) direction.
        const elevation = (degrees * Math.PI) / 180;
        const azimuth = (azimuthDegrees * Math.PI) / 180;
        const radius = Math.hypot(-8, 14, 10);
        world.globalLights.moon.position.set(
          Math.sin(azimuth) * Math.cos(elevation) * radius,
          Math.sin(elevation) * radius,
          Math.cos(azimuth) * Math.cos(elevation) * radius,
        );
      },
```

Check it: `setMoonElevation(47.9)` should put the moon back at about `(-8, 14, 10)`. Correct the default azimuth if it doesn't (atan2(−8, 10) = −38.7° = 321.3°).

- [ ] **Step 3: Capture for Daniel**

At `park-florist`, `public-light-pool`, `north-road`, `greek-gyros`, `start` and `bus-shelter` (MEDIUM), capture elevation 48° (current), 65° and 80°, with probes. Save to `renders/lighting-captures/2026-09-21-moon-ab/`.
Expected: at 65°/80° the pale blockout walls drop in value relative to MCR1, Dreams and the shelter. Paving and grass stay about as bright as before (`surroundLuminance` for ground-heavy frames within about 15%). `blackShare` rises.

- [ ] **Step 4: Commit and decide**

```bash
git add src/world/createWorld.ts src/main.ts renders/lighting-captures/2026-09-21-moon-ab
git commit -m "Expose global lights and add a dev moon-elevation experiment with captures"
```

If Daniel picks a new elevation, change `moonlight.position.set(-8, 14, 10)` to the chosen vector (with a comment naming the elevation), and commit as "Raise the moon to <N>° so façades fall back behind practicals". If a steeper moon works but only some pale blockouts still dominate, the fallback is to lower those blockouts' material tint during their texture pass. Record that as follow-up work, not part of this plan.

---

### Task 10: After captures, performance on target hardware, documentation

**Files:**
- Create: `renders/lighting-captures/<date>-after/`
- Modify: `docs/LIGHTING_AUDIT.md`, `docs/PERFORMANCE.md`, `docs/TECHNICAL.md`, `docs/VISUAL_LANGUAGE.md`, `SYNC.md`

- [ ] **Step 1: Re-run the capture script**

Run the capture routine exactly as in Task 2 Step 3 and rename the folder to `<date>-after`.

- [ ] **Step 2: Check the acceptance criteria against the baseline**

For each view in `metrics.json`, compare with `2026-09-21-baseline/metrics.json`:

| Check | Pass condition |
| --- | --- |
| Darkness kept | `blackShare` drops by no more than 0.03 in any view except `hive-entrance` and `car-park` (≤ 0.05). |
| Rider stays near-black | Out of pools (`between-light-pools`, `west-street`, `park-florist`), `playerLuminance` is at most 1.2 × baseline. |
| Rider separates | `separation` is at least the baseline in every view. In `public-light-pool-front` it is higher than baseline. |
| Rider not blue | Visual check in `west-street` and `park-florist`: the clothing reads neutral near-black. |
| Budget honest | No `activeLocalLightGroups` list is longer than 2/4/5 lights by profile. LOW never lists `Public illumination pool`. |
| Draw calls | `drawCalls` in `public-light-pool-medium` and `south-road-medium` are at least 60 lower than baseline. |
| No popping | Manual: walk from `public-light-pool` to `between-light-pools` and orbit 360° at Cass Art. No visible switching. |

Any failure: fix it in the task that owns it, re-capture, and re-check.

- [ ] **Step 3: Real frame-rate measurement (Daniel's Mac, not headless)**

Headless and hidden-pane browsers do not give representative GPU timings. In a normal browser window on the target Apple Silicon laptop at 1280 × 720, at baseline commit `29801c1` and at the final commit, record the overlay's FPS and frame milliseconds (H) at `start`, `south-road`, `spice-cabin` and `east-shops` on MEDIUM and LOW. Stand still for 10 s at each and note the typical value. Expected: no view is slower after the change, and `spice-cabin` is equal or faster from the draw-call cut.

- [ ] **Step 4: Update the docs**

- `docs/LIGHTING_AUDIT.md`: add an "Implementation follow-up — <date>" section under the 14 Sept one. List the ten tasks' outcomes, the grade and moon decisions, a link to the before/after capture folders, and correct the 14 Sept wording: the old "visibility floor" was a 1.55× gain on ambient light, not a floor.
- `docs/PERFORMANCE.md`: the fixed-slot cost model (slots always present), view-aware selection, the LOW proxy change, the rider shader term costing no slot, the streetlight merge draw-call numbers, and the Step 3 FPS table.
- `docs/TECHNICAL.md`: `npm test` (Vitest), the `zealot.lighting` / `zealot.grade` / `zealot.characterLight` dev hooks, and the capture routine.
- `docs/VISUAL_LANGUAGE.md`: public illumination is now a soft painted pool plus broken reflections plus one proxy plus the rider's lamp response. Note the lamp-spacing rule (≥ 8 m).

- [ ] **Step 5: SYNC entry and commit**

Append a `SYNC.md` entry using its template (HEAD at start, what changed, captures, decisions, open questions below).

```bash
git add renders/lighting-captures docs/LIGHTING_AUDIT.md docs/PERFORMANCE.md docs/TECHNICAL.md docs/VISUAL_LANGUAGE.md SYNC.md
git commit -m "Record the lighting hierarchy pass: captures, performance and docs"
```

---

## Out of scope (separate asset-first plans)

- **Come Through Lab final luminaire.** It needs a Blender pass that adds a real fixture and an anchor (for example `CTL_Luminaire_Entrance`). The runtime then swaps the temporary cue's position for that anchor. Task 3 already keeps the cue from being starved of a slot.
- **Greek Gyros final material and light pass.** Emissive fixture faces and three more anchors, again authored in Blender first.
- **View-dependent wet reflections.** The broken reflection strips always point towards +Z, so from some angles they point away from the camera. Fixing that is a separate reflection task.

## Open questions for Daniel

1. Four public streetlights are magenta (`STREETLIGHTS` at (8, 19), (16, 19), (12, −29), (16.5, 55)). The audit says to keep magenta specific to Renee. Should they be sodium or cold white?
2. Car-park pools: cold white (security) as planned, or one sodium and one cold white for a mixed-light scene?
3. Task 8 and Task 9 decisions (grade variant, moon elevation) are yours by design. Nothing global changes without them.
