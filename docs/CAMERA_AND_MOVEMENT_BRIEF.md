# Camera and Movement Brief

**Status:** Direction agreed with Daniel on 2026-09-16. Implementation is partly done in the working tree; the rest is below.
**Applies to:** `src/camera/ThirdPersonCamera.ts`, `src/player/PlayerController.ts`, `src/input/InputController.ts`, `src/interaction/BikeInteraction.ts`, the camera wiring in `src/main.ts`, and camera-facing flags in `src/world/collision.ts`.
**Read with:** `docs/creative-constitution.md` §20–24 (photographic origin, medium format, photographer before game designer, frontal framing) and `docs/TECHNICAL.md` § Camera.

This brief pulls together everything Daniel has said about how the game should move and look through the lens. It also plans how to bring in the camera and movement fixes that were built on side branches but never merged into `main`. When a later change conflicts with this brief, the brief wins unless Daniel says otherwise.

---

## 1. What Daniel said

These are Daniel's own reports and directions from the 2026-09-16 session, in order.

1. **Regression report.** "In another iteration … the camera issues were fixed: you could see the top of buildings, you didn't go into buildings or behind trees as you navigated, and the navigation wasn't disorientating. Now it's gone back to that." In particular:
   - the camera zooms in and out unexpectedly;
   - navigation is generally very disorientating.
2. **Reference frame.** He sent a screenshot of the look he wants "most of the time":
   - eye-level view, standing on the park path beside the bus shelter, looking along the pavement towards Coral;
   - horizon level and roughly through the figure's head;
   - Coral's facade upright and square-on enough to read its windows and fascia;
   - the shelter framing the left edge, trees and a second building on the right;
   - the figure small and central, seen from behind, about five metres ahead of the lens.
3. **Guiding principle, quoted.**
   > The game is largely photographic. I want to be able to see the front facades of buildings. The game is largely about architecture and the urban landscape — the nocturnal urban landscape — so you need to be able to see it clearly. The game is in part a photo walk, so you need to be able to see bus stops, buildings, framed almost as if they were photographs.
4. **Feel reference.** Movement should feel as consistent as Grand Theft Auto played on an iPad with a keyboard. The world should feel like a place you can walk around in and observe.
5. **Merge intent.** The fixes on the side branches will be merged to solve the camera and movement issues.

---

## 2. Why it regressed

The fixes Daniel remembers were made on two branches that never reached `main`:

| Branch | Tip | What it holds |
|---|---|---|
| `origin/claude/engineer-communication-workflow-uex7id` | `9d60c9d` (on top of `9e2d778`) | The movement and camera feel pass. Details in §7.1. |
| `origin/claude/game-improvement-ideas-vkan3h` (also inside `origin/codex/tone-mapping`) | `625474d` | Camera occlusion, wheel zoom, facing the input direction, plus unrelated image, payload and interaction work. Details in §7.2. |

Meanwhile `main` rewrote the camera separately (`ea8f343`, `f93ac7a`) and brought back the continuous auto-follow that `9d60c9d` had removed as a bug.

The 2026-09-16 working tree has partly fixed this; see §6. Neither branch has been merged. Both branches are older than `ea8f343` and `f93ac7a`, which rebuilt most of `createWorld.ts`.

---

## 3. Principles

These rules are ranked. When two conflict, the one higher in the list wins.

### P1. The lens is a photographer's eye
- **Resting view:** at eye level with a level lens.
  - Building verticals stay upright.
  - Facades read as architecture, not as surfaces seen from above.
  - Think of a medium-format camera on a tripod.
- **Figure:** small against the city, sitting in the middle of the frame. The frame is about the street, the light and the buildings, not about the character.
- **No high chase view:** never trade this framing for a high or top-down angle as a default, or as a way around collisions.
- **Deviations are glances:** looking up at a roofline or down at a road marking is temporary, and the camera settles back to eye level on its own.

### P2. The camera never moves without a cause the player can feel
Every camera change must be caused by one of these three things:
1. the player's own look input;
2. the player's own movement, meaning positional follow only;
3. a collision it can't avoid, handled as gently as possible (P5).

That rules out several things:
- **Speed:** no zoom or boom change linked to speed on foot.
- **Running:** no FOV swell when running.
- **Bobbing:** no camera bob.
- **Self-rotation:** no rotation the player didn't ask for while walking.

### P3. Directions mean the same thing from one moment to the next
This is the GTA-with-a-keyboard quality.
- **Held direction:** holding a direction key keeps you walking in a straight line across the screen until you change the input or turn the camera yourself.
- **Diagonals:** holding W+D for ten seconds traces a straight line, not an arc.
- **Starting and stopping:** getting up to speed is quick and predictable, and so is stopping. You never slide on, drift or overshoot.
- **Every device:** speeds and responsiveness are the same at 30, 60 and 120 Hz, on a laptop and on an iPad.

### P4. The walk is the point
- **Pace:** the default pace is an observing walk. Running is a deliberate choice.
- **Stopping:** stopping is a good thing. When the player stands still, the city should compose itself into a better picture (§5.4), not sit there waiting for input.

### P5. Collisions are handled in the gentlest order that works
When something stands between the figure and the lens, try these in order:
1. **Ignore it** if it can't block the view in a way that matters: poles, bollards, benches, bins, bike docks, tree trunks (`blocksCamera: false`).
2. **Fade it** if it's a canopy or small overhead mass near the lens. Future work, see §5.5.
3. **Rise slightly**, keeping the boom length, within a small cap so P1 still holds.
4. **Shorten the boom**, pulling in immediately and easing back out slowly after a hold, so rows of buildings don't make it pump.
5. **Hide the figure** if the lens ends up so close that the figure would fill the frame.

The lens must never end up inside a building.

### P6. Riding is a different mode
- **Steering:** the bike steers relative to itself, so following behind it is correct and safe.
- **Boom and lens:** the boom stays a fixed length; boost may widen the lens by no more than 5°.
- **Eye level:** the camera stays at eye level on the bike too.

---

## 4. Consistent movement: what "GTA on an iPad with a keyboard" means here

The target is a feel, not a copy. Concretely:

| Quality | Specification |
|---|---|
| Movement basis | Relative to the camera. W moves away from the lens and A/D move across the screen. |
| **Basis latch** (new) | While any movement key stays held, the yaw that defines "forward" is latched from the moment input started. It is re-captured only when the set of held keys changes, the player moves the camera, or C recentres. So nothing that moves the camera without direct input (a collision lift, and any future follow) can bend a walk. This is the structural fix for the circling bug, which the branch fixed by removal only. |
| Acceleration | Full speed in about 0.1 s and a stop in about 0.08 s. The branch's responsiveness of 16 moving and 20 stopping, plus a zero-snap below 5 cm/s, achieves this. `main` is still at 8/11 (floaty). |
| Speeds | Walk 2.4 m/s by default, run 4.5 m/s with Shift. **The same in dev and prod builds.** The dev multipliers (×1.3 walk, ×1.7 run) make every tuning session feel different from the real game; remove them, or put them behind an explicit `?fast=on` flag. |
| Facing | The figure faces the *input* direction, turning quickly but smoothly (from `625474d`), not its post-collision slide. Sliding along a wall doesn't swing the figure round to face along it. |
| Walls | Collision slides along surfaces. Velocity is reconciled with actual displacement every step, so nothing stale carries over (`9d60c9d`). An overlap is always resolvable, so the player can never be trapped. |
| Camera follow | Positional follow only, from one smoothed anchor that drives both the lens and the look target. This stops the figure swimming around the frame when it speeds up (`9d60c9d`). There is no rotational follow on foot. |
| Recentre | C swings the camera behind the figure over about a quarter of a second. It eases rather than cuts, so the new view stays readable. |
| Frame-rate independence | All smoothing is exponential with `1 - exp(-k·dt)`. The simulation runs on the fixed step. The camera runs on the render delta, which is zeroed after long gaps (already in place). |

### 4.1 iPad with a keyboard: practical requirements
- **Keys:** read every binding by `event.code`, falling back to `event.key` when `code` is empty. Some iPadOS hardware keyboards and input methods report an empty `code`, which is why `E` already has this fallback.
- **Stuck keys:** clear all held keys on `blur`, on `visibilitychange`, and on any `Meta` keydown. On iPad, Cmd shortcuts and the app switcher swallow keyups, which leaves movement keys stuck down.
- **Reserved shortcuts:** don't bind anything that needs Cmd, Ctrl or the Globe key. iPadOS takes those for itself.
- **Look input:** trackpad and mouse drag to orbit must always work. Pointer lock (from `9d60c9d`) is an extra when supported. **Check it on a real iPad** before relying on it, and keep drag as the fallback that's guaranteed to work.
- **Keyboard-only look:** a player with no pointing device must still be able to turn the camera (§4.2).
- **Scrolling:** trackpads send continuous, high-frequency wheel events, so free wheel zoom is easy to trigger by accident and would bring back "zooms unexpectedly". See §4.3.
- **Touch-only play** (no keyboard) is out of scope for this brief; see open questions.

### 4.2 Key map (proposed)

| Key | On foot | Riding |
|---|---|---|
| W A S D | Move (camera-relative, latched) | W pedal, A/D steer, S brake |
| Shift | Run | E-assist |
| Space | *(unbound, reserved)* | Boost |
| E | Interact / mount | Interact / dock / dismount |
| C | Recentre camera behind figure | Recentre |
| ← → | Turn camera (yaw) | Turn camera (yaw; auto-follow resumes after 1.2 s) |
| ↑ ↓ | Look up/down (a glance; eases back to eye level) | Same |
| V | Cycle framing preset (§4.3) | Cycle framing preset |
| H | Dev overlays (dev builds only) | Same |

**Conflicts with the branch, resolved above.**
- `9d60c9d` binds Q/E to keyboard yaw and R/F to pitch. `main` now uses **E for interact**, so Q/E yaw can't be merged as it is. Arrow keys are the proposal instead: they currently only duplicate WASD, and "arrows turn the view" is a familiar convention.
- `9d60c9d` also makes running the default, with Shift to walk. That goes against P4, and Shift is now e-assist on the bike, so it isn't adopted. Walking stays the default.
- Space is currently a second run key on foot (`InputController.isRunning`). Unbind it on foot, so it can later become the shutter or photo key without retraining players.

### 4.3 Zoom: presets, not a free wheel
Both branches add free wheel zoom (`9d60c9d`: 3.4–10.5 m; `625474d`: 2.5–12 m). Don't port it as is. Use a small set of **framing presets**, cycled with V and eased between over about 0.6 s, each keeping P1's eye-level lens:

| Preset | Boom | Pivot/look height | FOV | Use |
|---|---|---|---|---|
| **Standard** (default) | 5.6 m | 1.6 m | 56° | Daniel's reference frame |
| Close | 3.4 m | 1.6 m | 52° | Tight streets, interiors |
| Wide | 8.5 m | 1.7 m | 60° | Taking in a whole facade or square |

Wheel input can be mapped to the same presets as discrete steps, with a threshold and a cooldown, so a trackpad swipe changes at most one preset. Mounting the bike switches to a riding boom of 7 m and restores the preset on dismount.

---

## 5. Photographic framing

### 5.1 Resting frame (built, see §6)
- **Lens:** about 1.8 m up, 5.6 m behind the figure, FOV 56°.
- **Tilt:** the look target is the orbit pivot (1.6 m), so at rest the lens tilt equals the boom pitch of 0.04 rad (about 2°).
- **Pitch limits:** −0.12 to 0.9 rad. Manual pitch eases back to rest after 2.5 s.

**Acceptance:** from `?view=east-shops` with default pitch, the frame matches the composition of Daniel's reference: level horizon, facades upright, figure central and small.

### 5.2 Developer views
The `developmentViews` table in `main.ts` passes explicit pitches (0.16–0.24) that were tuned for the old, higher camera, so they now look down more than normal play does. Re-tune them to the resting frame, or remove the pitch argument, so dev screenshots show what players see.

### 5.3 Figure visibility
- **Close to the lens:** port the hysteresis hide from `9d60c9d`, which hides the figure below 1.7 m and shows it again above 1.95 m. It's needed when backing into a wall pulls the boom right in.
- **Contact shadow:** stays visible, so the player still knows where they are.

### 5.4 Standing still: the tripod (future phase, needs Daniel's sign-off)
The creative constitution asks: "What happens if the person stands still?" Proposal:
1. **Trigger:** after about 4 s with no movement or look input, and when a location facade is within about 25 m and roughly ahead, the camera very slowly (over 3–5 s) settles into a **frontal composition** of that facade.
2. **Composition:**
   - yaw perpendicular to the frontage (`front` in `worldLayout.ts` already gives the side);
   - lens level;
   - figure moved off-centre towards a third.
3. **Cancelling:** any input cancels it immediately. Movement then continues on the *latched* basis captured at the moment input started, so it can't be disorientating.
4. **Hook:** `LocationAwareness` from `625474d` already tracks which location the player is standing at. It's the natural place to connect this.

### 5.5 Trees and overhead masses (future phase)
- **Current behaviour:** tree canopies don't block the camera, so foliage can sit in front of the lens. Pulling the camera in for foliage would break P2.
- **Proposal:** fade or dither canopy materials that fall inside a cone between the lens and the figure (screen-door or alpha, eased).
- **Awnings and shelter roofs:** the same treatment. Daniel's reference frame puts the bus shelter right against the lens, and that's desirable, so fade only when the mass actually covers the figure.

### 5.6 Photo mode (future, a seam only)
A deliberate photo mode is the natural next step for a photo walk:
- a free lens within a few metres of the figure;
- a level-horizon lock;
- lens choices based on medium-format equivalents;
- an optional grid;
- a shutter bound to Space or a mouse button.

Don't build it yet. Keep the camera code structured (presets, latch, pitch return) so a photo mode can take over the `PerspectiveCamera` and hand it back cleanly, the way `TitleCamera` already does.

---

## 6. Current state of the working tree (2026-09-16, uncommitted)

**Done:**
- **Auto-follow:** removed on foot, kept only while riding (`RIDING_FOLLOW_RESPONSIVENESS` 2.4, suspended for 1.2 s after manual orbit).
- **Recentre:** C swings the camera behind the figure (`InputController.consumeRecenter`).
- **Resting frame:** eye-level, as in §5.1, with pitch return.
- **Occlusion:** rise-before-retract, with the lift capped at 0.35 rad, rising quickly, held for 0.8 s and falling slowly. The sphere-cast boom clamp is the hard backstop, pulling in immediately and recovering at a rate of 2.5.
- **Riding:** boom fixed at 7 m; the boost-linked boom is gone and the boost FOV bump is +5°.

**Measured** in the dev page against a stepped copy of the camera, on scripted 8–10 s walks:
- unasked camera rotation on foot dropped from 300–600° per walk to 0°;
- the camera held steady at 1.82 m;
- 0 frames with the view blocked.

**Not done:**
- basis latch;
- movement responsiveness, zero-snap and speeds;
- facing the input direction;
- single smoothed anchor;
- figure hide;
- arrow-key look;
- framing presets;
- normalised orbit sensitivity (the camera still uses raw pixels × 0.004);
- iPad key hygiene;
- dev view pitches;
- tripod, canopy fade and photo mode.

**Not verified:** live keyboard play. The Browser pane was hidden, which throttles `requestAnimationFrame`.

---

## 7. Merge plan for the side branches

### 7.0 Strategy
**Don't `git merge` either branch.**
- **World code:** both branches are older than `ea8f343` and `f93ac7a`, which rebuilt `createWorld.ts` (about 1,800 lines of difference) and added the title screen, bikes and surfaces. A merge would put conflicts through the world code that have nothing to do with the camera.
- **Camera:** `main`'s camera has also diverged on purpose (sphere cast, lift, bike API, eye-level framing).

**Port by feature instead**, onto a fresh branch taken from `main`:
1. Commit the current camera work on `main` first, as its own commit separate from the large pre-existing dirty tree, so the port starts from a known base.
2. `git switch -c camera-movement-consolidation`.
3. For each item below, read the branch version with `git show <sha>:<path>` and hand-port the behaviour into `main`'s structure.
4. Tick off each item in `SYNC.md` as it lands.
5. Keep commits one feature each, so any of them can be reverted on its own.

### 7.1 From `9d60c9d` / `9e2d778` (`claude/engineer-communication-workflow-uex7id`)

| Item | Decision | Notes |
|---|---|---|
| Continuous auto-follow removed | **Already done** | Riding-only follow kept (P6). |
| C recentre | **Already done** | `main` eases the swing; the branch snapped. Keep the ease. |
| Occlusion as a hard constraint on the final position | **Already done differently** | `main`'s sphere cast plus lift covers this. Keep `main`'s. |
| Street furniture solid but not camera-blocking | **Already on `main`** | `main` uses `blocksCamera: false`; the branch named it `occludesCamera`. Keep `main`'s name. |
| Movement responsiveness 16/20 + zero-snap | **Port** | P3. |
| Velocity reconciled with displacement every step, clamped to speed | **Port** | `main` reconciles only when blocked. |
| Single smoothed anchor (responsiveness 14) for lens and look target | **Port** | Must keep `main`'s pivot/look-height design and the `dreams-target` look-height override. |
| Orbit sensitivity normalised to screen height (3.2 rad per screen) | **Port** | Consistent across iPad and desktop. |
| `invertPitch`, `orbitSensitivity` settings | **Port** | Needed for any future options menu. |
| Pointer lock with drag fallback | **Port, check on iPad** | §4.1. Esc must always release it. Clicking the canvas to lock mustn't swallow the first interaction on the title screen. |
| Hide the figure when the lens is close (1.7/1.95 m hysteresis) | **Port** | §5.3. |
| Keyboard orbit Q/E, R/F | **Port, rebound** | Use arrow keys; E is interact (§4.2). |
| Wheel zoom 3.4–10.5 m | **Port as presets** | §4.3. |
| FOV 58 walking / 64 running | **Reject** | Breaks P2. Use preset FOVs only. |
| Pitch range up to 1.02 | **Reject** | Breaks P1. Keep −0.12 to 0.9 with pitch return. |
| Run by default, Shift to walk | **Reject** | Breaks P4, and Shift is bike assist. |
| `docs/STATUS.md`, `docs/AGENT_WORKFLOW.md` | **Ignore** | Already deleted on the branch in favour of `SYNC.md`. |

### 7.2 From `625474d` (`claude/game-improvement-ideas-vkan3h`)

| Item | Decision | Notes |
|---|---|---|
| Camera occlusion probe | **Superseded** | `main`'s sphere cast is more complete. |
| Obstacle heights | **Already on `main`** | |
| Wheel zoom with `deltaMode` normalisation | **Port the normalisation only** | Feed it into the preset stepping in §4.3. |
| Figure faces the input direction, not the post-collision slide | **Port** | §4. |
| 4× MSAA composer target, colour quantisation off, directional moon shadow | **Separate brief** | Rendering, not camera or movement. Check against `main`'s current `createPostProcessing.ts` and lighting first; `main` may already cover some of it. |
| Unreferenced GLBs moved out of `public/` | **Separate task** | Re-audit, since many GLBs have been added since. |
| `LoadingVeil` | **Probably superseded** | `main` has `IntroScreen` with `SHOW_TITLE_SCREEN`. Compare before porting. |
| `LocationAwareness` + `LocationLabel` | **Port later** | Hook for the tripod (§5.4) and the delivery loop. It isn't needed for this brief's first phase. |
| Typecheck/build CI workflow | **Separate task** | |

`origin/codex/tone-mapping` is `625474d` plus a tone-mapping comparison switch (`17e3b34`), which is rendering and out of scope here.

---

## 8. Phases

1. **Phase 1: consistency.** This fixes what Daniel reported.
   - Basis latch.
   - Movement responsiveness, zero-snap, reconciliation, facing the input direction, and equal dev and prod speeds.
   - Single smoothed anchor.
   - Normalised orbit sensitivity.
   - iPad key hygiene.
   - Figure hide.
   - Space unbound on foot.
   - Re-tuned dev views.
2. **Phase 2: look controls.**
   - Arrow-key look.
   - Pointer lock (checked on iPad).
   - V framing presets, with wheel stepping.
   - Invert and sensitivity settings plumbed through, even without a menu yet.
3. **Phase 3: photographic behaviour** (each item needs Daniel's go-ahead).
   - Canopy fade.
   - Tripod settle when standing still.
   - `LocationAwareness` port.
4. **Phase 4: photo mode.** A design brief of its own.

---

## 9. Acceptance tests

Build these as a dev-only harness, reusing the approach from 2026-09-16:
- step a separate `ThirdPersonCamera` and the collision functions in the dev page through `window.zealot`, at a fixed 1/60 s;
- make it callable from a URL such as `?feeltest=on`, logging a table.

It runs even when the Browser pane is hidden. **Every threshold must pass before merging any phase.**

| # | Scenario | Pass condition |
|---|---|---|
| T1 | Hold W+D for 10 s in the park | Unasked camera yaw is 0°; the path deviates from a straight line by less than 1° |
| T2 | Strafe D for 8 s along the west shops | Unasked yaw 0°, boom change 0 m |
| T3 | Run past the east shops with the camera angled towards the buildings, 8 s | 0 frames blocked; at most 10 frames with a boom change above 4 cm |
| T4 | Zig-zag the south road for 10 s | 0 frames blocked; at most 10 sudden-boom frames; camera height stays within 0.4 m of rest |
| T5 | Back straight into a tall wall | Lens never inside geometry; figure hidden while the boom is under 1.7 m and shown again above 1.95 m |
| T6 | Tap W from rest, then release | 90% of speed within 0.12 s; stopped within 0.1 s; no drift afterwards |
| T7 | Same scripted input at 30, 60 and 120 Hz render rates | End positions within 5 cm; camera yaw within 0.5° |
| T8 | Resting frame at `?view=east-shops` | Lens height 1.7–1.9 m; tilt at most 3°; screenshot matches the reference composition |
| T9 | Ride and boost for 10 s | Boom constant at 7 m ±0.05 m; FOV change at most 5° |
| T10 | Hold W, press Cmd+Tab away and back (iPad and macOS) | No stuck movement on return |

Also play it live on a desktop browser and on an iPad with a keyboard before calling a phase done. The Browser pane isn't enough on its own.

---

## 10. Open questions for Daniel

1. **Arrow keys for camera look** instead of the branch's Q/E and R/F, which clash with E for interact. OK?
2. **Walking by default**, with Shift to run and Space freed for a future shutter. OK?
3. **Framing presets on V**, rather than a free scroll-wheel zoom. OK? Are the three presets in §4.3 right?
4. **Tripod settle** when standing still (§5.4): wanted, and how assertive should it be?
5. **Touch-only iPad play** (no keyboard): in scope at some point, or keyboard only for now?
6. **Rendering items from `625474d`** (MSAA, moon shadows, quantisation off): take them in a separate pass?
