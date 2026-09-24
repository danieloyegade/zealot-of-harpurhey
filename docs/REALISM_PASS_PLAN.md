# Realism Pass Plan — step by step

Date: 24 September 2026 · Companion to `docs/VISUAL_REALISM_ROADMAP.md` (the *why*). This file is the *how*: numbered steps, who does each, which files, and how we know it worked.

Target image: `renders/visual-gap-2026-09-24/00-target-reference-dreams-night.webp`

**The rule for the whole pass:** prove everything on **Dreams and ~30 m around it** first. Nothing rolls out to the rest of the map until Stage 6 passes its gate.

**Who:** 🧑 = Daniel (needs hands in Blender or a GUI tool, or an art decision) · 🤖 = an AI session (Claude/Codex) can do it in code · 🤝 = both.

Two terms that sound alike:
- **Environment map** (IBL): a 360° picture of the surroundings that shiny surfaces reflect and dull surfaces take a faint tint from. One per area; costs nothing per frame.
- **Lightmap**: a texture per building with the lighting (tubes, lamps, soft corner darkness) pre-rendered into it in Blender. That's "baked lighting".

---

## Stage 0 — Set up and take a baseline (half a day)

| # | Step | Who | Done when |
|---|---|---|---|
| 0.1 | **Upgrade Blender** from 3.0.0 to the current LTS (4.2 or later). Lightmap baking, the modern glTF exporter and MPFB2 (Stage 8) all expect it. Update the path/version in `docs/TECHNICAL.md` → "Installed Blender". | 🧑 | `blender --version` shows 4.x, and one existing script (e.g. `createDreamsGreybox.py`) still rebuilds its GLB unchanged. |
| 0.2 | **Commit or discard the KTX2/Meshopt work** SYNC says is uncommitted on Daniel's Mac (`gltfLoader.ts`, optimiser scripts). It isn't in the repo. Stage 3 depends on it. | 🧑 then 🤖 | `git status` on the Mac is clean and the optimiser tests pass in CI. |
| 0.3 | **Baseline pack.** On real hardware (Daniel's Mac, not automation), capture screenshots and the `H` overlay (fps, draw calls, textures) at these dev views: `dreams-target`, `dreams-angle`, `park-to-dreams`, `public-light-pool`, `bus-shelter`, `spice-cabin` (the worst view), `sterling-south`, at `quality=medium` and `quality=high`. Save to `renders/realism-pass/00-baseline/` with a `numbers.md`. | 🤝 | Folder exists; every later stage adds a sibling folder with the same shots and the same numbers table. |

**Performance budget for the whole pass (MEDIUM, Apple Silicon laptop):** keep the baseline fps or better at `dreams-target`, allow at most **+10 % draw calls**, and keep GPU texture memory under ~250 MB. If a step breaks the budget, it goes to HIGH only or gets cut.

---

## Stage 1 — Turn off the retro settings (1 day · 🤖) — **done 2026-09-24, `realism-pass` branch**

All in `src/rendering/visualStyle.ts` and `src/rendering/createPostProcessing.ts`.

1. **Flat shading off:** `geometry.facetedLighting: false`. This flows into every `flatShading:` use (`worldMaterials.ts`, road, pavement, park, decals, graffiti). ✅
2. **Check GLB normals:** for any building that looks lumpy after step 1, re-export from Blender with *Shade Smooth + Weighted Normal modifier* (or Auto Smooth 30°). Note which assets needed it in the stage's `numbers.md`. **Not done** — needs a real GPU browser pass on Daniel's machine to judge; the `dreams-target`/`dreams-angle` SwiftShader captures taken for this stage didn't show obvious lumpiness, but that's not a reliable signal (software rasteriser). Check on real hardware before Stage 3.
3. **Remove posterisation:** make `colorQuantizationLevels` 255, or delete the quantise line in the grade shader. Keep `ditherStrength` at ~`1/255` purely to stop banding. ✅ (kept the uniform rather than deleting the shader line, in case a deliberate posterise effect wants it later)
4. **Linear filtering for signage:** in `applyTextureProfile`, `RETRO_GRAPHIC` becomes linear plus mipmaps, unless a specific sign is meant to be pixel art. Then grep for `'RETRO_GRAPHIC'` and remove any that were only there for the old look. ✅ All 5 current uses (`worldGraphics.ts` weathered sign/graffiti/notice/sticker, `createWorld.ts` road annotation) are canvas-drawn signage, not pixel art — kept as `RETRO_GRAPHIC` (for its lower anisotropy) but now linear-filtered.
5. **Anti-aliasing:** add `SMAAPass` (from `three/examples/jsm/postprocessing/SMAAPass.js`), gated by a new `quality.smaaEnabled` (on at MEDIUM/HIGH, off at LOW). ✅ — **placement corrected from this plan's original wording**: SMAA must run *before* `OutputPass`, not after the grade — the library operates in linear-sRGB and `OutputPass` performs the tone-mapping/colour-space conversion the grade then works on. Order is now: RenderPass → Bloom → **SMAA** → OutputPass → grade.
6. **Update docs:** delete the stale Dreamcast wording in `docs/VISUAL_LANGUAGE.md` (its title still said "Dreamcast") and the matching caveat in `AGENTS.md`. ✅ — on inspection the `AGENTS.md` caveat itself was the stale part: `ART_DIRECTION.md`'s "Core principles" already states the current direction. Fixed both.

**Validation:** `npx tsc --noEmit`, `npm test` (17/17), `npm run build` all clean. Visually confirmed via SwiftShader screenshots at `dreams-target`/`dreams-angle`/`park-to-dreams` — smoother sky gradient, smoother sign edges — but SwiftShader gives no meaningful fps number, so the Stage 0/1 performance budget is **not yet confirmed on real hardware**. Do that before Stage 2.

**Done when:** before/after shots show smooth shading and no sky banding, fps is within 3 % of baseline, and the tests plus `npm run check` pass.

---

## Stage 2 — The grade (1 day · 🤖 with 🧑 approving the look) — **code done 2026-09-24, `realism-pass` branch; look not yet approved**

Only change the grade *after* Stage 1, because the image changes underneath it.

1. **Split the grade from the dither/grain** so each can be tuned alone. ✅ — implemented as a `GradeParameters` interface with every value get/settable independently (`createPostProcessing.ts`), rather than as separate GPU passes (one shader stays cheaper than several, and nothing here needs its own render target).
2. **Lift blacks slightly:** add a `blackLift` uniform so the darkest pixels land around 3–6 % luminance instead of 0 (the reference's shadows are dark blue-grey, not black). Don't raise overall exposure: `LIGHTING_AUDIT.md` is right that the darkness is the identity. ✅ — `blackLift: 0.045` (4.5%), applied as `color * (1 - blackLift) + blackLift` after contrast, before split-tone. Exposure/ambient untouched.
3. **Split-tone instead of global saturation:** drop `saturation` from 1.12 to ~1.0, and add a gentle teal push in shadows and amber push in highlights (two colour uniforms, a luminance-weighted mix). ✅ — `saturation: 1.0`; `splitTone` (shadowTint `#8fb4c9`, highlightTint `#dcb98c`, strength 0.16, blended by post-lift luminance between 0.12 and 0.72).
4. **Retune bloom** (`bloom.threshold`, strength): tubes and signs should have a tight halo, not a haze. ✅ — `radius` 0.32→0.22, `threshold` 0.88→0.92, `bloomStrength` 0.3/0.34→0.24/0.26 (medium/high). First-pass numbers, not yet judged against the reference on real hardware.
5. **Keep** AgX, grain and vignette. ✅ — unchanged, only reordered around the new steps.
6. Expose all grade values through a dev-only `?grade=` URL flag or the debug overlay, so Daniel can tune them live and paste the numbers back. ✅, via `window.zealot.grade.getParameters()`/`.set({...})` (dev only) — matching the existing `window.zealot.atmosphere` convention rather than a new URL DSL, since that pattern is already documented and used in this codebase (`docs/VISUAL_LANGUAGE.md`).

**Not done — this is the actual gate, not the code:** "Daniel signs off one grade on the `dreams-target` view, next to the reference." The values above are a reasoned first pass, not a tuned-and-approved look. Tune live with `zealot.grade.set({...})` against `renders/visual-gap-2026-09-24/00-target-reference-dreams-night.webp`, then report the numbers back so they can be baked into `VISUAL_STYLE.render`/`VISUAL_STYLE.bloom` and this stage marked fully done.

**Validation:** `npx tsc --noEmit`, `npm test` (43/43), `npm run build` all clean. Visually smoke-tested via SwiftShader screenshots (no meaningful fps signal, see Stage 1's same caveat) — lift and split-tone are visible in the shadows, bloom is visibly tighter around the Dreams tubes. No fps/GPU measurement on real hardware yet.

**Done when:** Daniel signs off one grade on the `dreams-target` view, next to the reference. The numbers are written into `VISUAL_STYLE.render` and there's no fps change.

---

## Stage 3 — Texture standard and material settings (2–4 days · 🤝) — **3a/3b done 2026-09-24, `realism-pass` branch; 3c blocked, needs Daniel + Blender**

### 3a. The texture standard (write it into `docs/TECHNICAL.md`) ✅

Written into `docs/TECHNICAL.md` under "Texture standard", verbatim per the table below, plus a note on the two texture systems it actually applies to (the real Blender/glTF pipeline most hero buildings already use, and the procedural `world-prototype` system).

| Surface | Resolution | Maps | Source |
|---|---|---|---|
| Hero façade materials (cladding, shutters, brick, render) | 1K–2K | albedo, normal, **ORM** (AO-roughness-metal packed in R-G-B) | Poly Haven / ambientCG CC0 scans, or Daniel's own photos for signage |
| Ground (asphalt, paving, kerbs) | 2K tiling + world-space variation (already exists for roads) | albedo, normal, roughness, **puddle mask** (Stage 4) | Poly Haven asphalt (already used), a paving scan |
| Props (bins, bollards, rails) | 512–1K, shared **trim sheet** | albedo, normal, ORM | CC0 scans + Blender |
| Signs and posters | as needed | albedo + emissive | Daniel's photographs |

- Naming: `<asset>_<surface>_{albedo,normal,orm}.ktx2`. Albedo uses ETC1S; normal and ORM use UASTC.
- Every new texture set is recorded in `config/asset-rights.json` (the licence check already runs in `npm run check`).

### 3b. Material settings (runtime, 🤖) — done, but narrower than first written; see the note below the list

1. **Enable the `aoMap` and `roughnessMap` slots** in `createWorldMaterial` (`src/rendering/worldMaterials.ts`), and accept ORM maps. ✅ — `normalMap`/`ormMap`/`aoMapIntensity`/`normalScale` options added; an ORM texture is wired to `aoMap`/`roughnessMap`/`metalnessMap` together (the glTF R/AO-G/rough-B/metal convention). **Plumbing only**: no procedural texture currently ships a companion map, so this has no visual effect yet — see "Flagged".
2. ~~Give every metal a real metalness (≈0.8–1) and roughness 0.3–0.6: railings, bollards, shutter frames, bins.~~ **Not done, deliberately.** Checked every `metal-oxidised-overhaul` call site first: they already carry considered, non-zero metalness (0.08–0.34) matched to a genuinely weathered/painted/oxidised finish, and the Dreams handrail is already 0.56 metalness/0.48 roughness. Blanket-raising to 0.8–1 would turn painted council street furniture into polished chrome — a regression against `ART_DIRECTION.md`'s weathered, photographic material identity, not a fix. This line in the original plan was written without inspecting the code; striking it rather than doing it anyway.
3. **Painted cladding:** roughness ~0.45, so the tubes leave a soft sheen on it. ✅ — Dreams' `mat-dreams-photographic-front` (the lit fascia panel) was 0.82, now 0.45. Confirmed visually: a soft highlight band now shows under the tubes that wasn't there before.
4. **Glass:** keep the existing alpha glass (`loadModel.ts`), but lower roughness to ~0.05 so it reflects the environment map. ✅ — clamped (never raised) to ≤0.05 after the transmission→alpha conversion, so any authored-glass material that didn't already set a low roughness in Blender is ready once Stage 4 lands; a lower authored value is left untouched.
5. Load every new texture through the KTX2 loader from step 0.2. Already true for every GLB (landed with the `main` merge before this stage); the new `ormMap`/`normalMap` options in `createWorldMaterial` use plain `TextureLoader` like every other procedural `world-prototype` texture, since KTX2 is a build-time GLB compression step, not something hand-authored PNGs go through.

**Found while implementing, not in the original plan:** the real Blender/glTF pipeline (`exportTexturedBuilding.py` and similar) already exports albedo/normal/ORM/AO natively for most hero buildings, and `buildingMaterials.ts`'s `profileAuthoredMaps` — which every hero building already calls — already keeps every one of those maps. Item 1 above is genuinely new plumbing only for the *procedural* `createWorldMaterial` system; it was already true for authored GLBs before this session. Also found: `busShelterMaterials.ts` already has a considerably more advanced glass system than either this stage or Stage 4 describes — grazing-angle Fresnel sheen, wet-glass roughness dropping to 0.015, and `envMapIntensity` already set on multiple materials (Spice Cabin's glass at 4.2) waiting for `scene.environment` to exist. None of this needed touching; noting it so Stage 4 doesn't duplicate it.

### 3c. Re-texture Dreams only (🧑 in Blender, 🤖 wiring) — **blocked, not started**

Replace the 128–512 px `dreams-*-hero` PNGs with a 2K cladding / shutter / brick set, through the existing `dreamsGreyboxTextures.py` → `harpurhey-dreams-greybox.glb` path and `applyDreamsModelPolicy` in `createWorld.ts`.

This needs Blender and, per `AGENTS.md`'s asset-first policy, real photographic reference — neither is available in this sandbox, and fabricating a "2K texture set" procedurally in code would violate that policy for no real gain (it wouldn't look more real, just higher-resolution noise). This is Daniel's half of Stage 3; the wiring side (🤖) is a small, fast follow-up once the textures exist.

**Done when:** a close-up at `dreams-angle` shows shutter ribs, panel seams and brick relief that hold up at 2 m. GPU texture memory rises by no more than ~40 MB, and fps is unchanged.

---

## Stage 4 — Environment map, wet road and puddle mask (3–5 days · 🤝) — **4a/4b/4c done 2026-09-24, `realism-pass` branch (with real deviations from the plan's exact wording — read each subsection)**

### 4a. Environment map — done, differently than planned

1. ~~In Blender... render a 1024×512 HDR... Stopgap: a CC0 Poly Haven night-street HDRI.~~ **Not done — no Blender or network download available from this sandbox.** Used a different, self-contained technique instead: `PMREMGenerator.fromScene()` captures the game's *own* already-built scene once (a real three.js API, not a hack) and prefilters that into the environment map, rather than loading any external image. This has a genuine advantage over a generic HDRI: the reflections/tint are this location's actual colours (the cold Dreams tubes, the sodium lamp, this sky), not a stand-in — and it needs no licence tracking. A real Blender-rendered or licensed HDR can still replace it later; every downstream material is unaffected either way, since they all just read `scene.environment`. See the long comment at the top of `src/rendering/environment.ts`.
2. ✅ (adjusted for the above) `src/rendering/environment.ts`: `captureSceneEnvironment()` does the capture + `PMREMGenerator` prefilter + `scene.environment`/`scene.environmentIntensity` (0.22) assignment. Called from `main.ts` inside the `sceneReady` chain, right after `prepareScene`'s GPU warm-up, so this one-shot cost sits under the same loading-screen hold rather than appearing as a mid-game stall. Capture point: a fixed spot on the pavement in front of Dreams (`x=0, z=33`), head height — see the file for why one global capture is enough for what Stage 4a asks.
3. ✅ `resolveEnvironmentMapEnabled()` — `?env=off` disables it, matching how `?quality=`/`?tonemap=` already resolve (works in prod too, not dev-gated).
   - Found and fixed while implementing: the initial `captureSigma` (0.045) exceeded `PMREMGenerator`'s internal 20-sample blur cap at `captureSize=256` and logged a console warning ("sigmaRadians... is too large and will clip"). Lowered to 0.03; confirmed clean.

### 4b. Puddle mask and wet ground — done as planned

1. ✅ `scripts/generatePuddleMask.mjs` (512×512, `public/assets/textures/wet/puddle-mask.png`), built from `textureTools.mjs`'s existing `fbm`/`smoothstep` helpers — two noise layers (a broad one for where puddles sit, a finer one for irregular edges), thresholded against the field's actual measured distribution so puddle cores cover roughly the top 4-5% of a tile and the damp halo roughly a quarter, not (as the first pass produced) half the map. A first-pass procedural placeholder, in the same "-temporary"/"-overhaul" tradition as this codebase's other procedural textures — replaceable by a hand-painted or photo-derived mask later without touching any shader code.
2. ✅ `createRoadMaterial()` (`src/world/createRoadSurfaces.ts`): roughness toward 0.04, albedo toward ×0.55, normal flattened toward the unperturbed surface normal, all driven by the mask, via a new shared module (`src/rendering/wetSurface.ts`) rather than duplicated inline — reusable because item 3 needs the identical mechanism.
3. ✅ `createPavementSurfaces.ts`: same mechanism, deliberately weaker (darken to ×0.75 not ×0.55, roughness floor 0.12 not 0.04, less normal flattening) — paving drains at the joints and holds less water than asphalt. Both sample the **same** mask file at the same world-space scale (7 m, the middle of the stated 6-10 m range), so a puddle reads continuously across a kerb rather than the two surfaces inventing unrelated patterns.
4. **Not done.** Hand-placed puddle decals at Dreams from the existing decal atlas — a small, low-risk follow-up, skipped this pass in favour of finishing 4c; the procedural mask already puts some wetness in front of Dreams some of the time (it's sparse/random, not guaranteed at every viewing angle — see the Stage 4 screenshots).

### 4c. Light-streak reflections — done, with one deliberate design change from the plan's wording

1. ✅ (design changed) `src/world/wetReflections.ts`, but as a **flat quad lying on the ground stretching toward/along the road**, not a vertical camera-facing billboard as originally written. A billboard would need a per-frame instance-matrix update to face the camera; a ground-lying streak needs no per-frame work at all (same one-shot instancing as everything else here) and is the standard technique this effect is modelled on (visible in the reference itself: the streetlight streaks lie on the road, they don't stand up). Each source supplies a `yaw`; every streetlight reuses the yaw that already turns its lantern's outreach toward the road it lights (`yawTowardNearestRoad`, already computed in `createWorld.ts`), which is also the natural direction for its reflection to stretch — no new authoring needed. Colour and puddle-mask-driven opacity are exactly as planned.
2. ✅ One `InstancedMesh` for every source (all streetlights + Dreams' tubes) — 1 draw call.
3. **Not done, on inspection — see "Flagged".** The named `addReflectionPatch` calls near "~3748" turned out, on reading the code, to cover **every hero building across the whole map** (Renee, Coral, Arts Council, Vinyl Exchange, Spice Cabin, Advanced Photo — not just Dreams), and to be a different kind of effect (a fixed, always-on fascia glow spill, independent of whether that ground is wet) rather than a wet-specific reflection. Retiring them is a real, city-wide visual change, not a small Dreams-local cleanup — left alone rather than deleting authored content across many locations without a side-by-side comparison. `addStreetlightPool()`'s own per-lamp `reflection-broken-overhaul` boxes (a different thing again — every streetlight's baseline "painted pool" graphic, on regardless of wetness) were never in scope and are also untouched.
4. **Not done.** HIGH-only box-projected cube-map at Dreams — skipped; 4a's scene-capture environment map already gives every puddle *some* reflection of its surroundings, which covers much of what this would have added on top.

**Done when:** at `dreams-target` the road shows streaks under the tubes and the lamp, and puddles read as puddles. Fps stays within 5 % of Stage 3, and draw calls rise by at most 2. — **Partially confirmed.** Puddles and streaks are both visibly present and working (clearest at `public-light-pool`, a warm streak under MCR1's shop light; puddles visible at `street-detail`) — see `renders/realism-pass/04-environment-wet-ground/`. Draw-call delta: +1 (the streak mesh) as intended. **fps not confirmed** — same SwiftShader-only limitation flagged every stage so far; needs a real-hardware pass.

---

## Stage 5 — Baked lighting on Dreams: *proving the pipeline* (1–2 weeks · 🧑 Blender, 🤖 runtime)

This is the core experiment. It proves (or disproves) that Blender-baked light gets us to the reference at no runtime cost.

### 5a. In Blender (🧑, with a script 🤖 writes)

1. **Assemble a "bake scene"** `blender/source/bake/dreams-bake.blend`. It contains the Dreams greybox, the ground plane in front of it (~30×20 m), and simple stand-ins for neighbours that throw light or shadow onto it: the right-hand shop, the lamp post, the bins.
2. **Place the real lights** as Blender lights, matching the game's colours in `VISUAL_STYLE.lighting`:
   - Dreams fascia tubes: area lights or emissive tube meshes, cold white `#c4dcff`.
   - Sodium streetlamp: spot or point light `#ffa326`.
   - Sky/moon fill: dim blue world colour.
3. **Lightmap UVs:** add a second UV map named `Lightmap` to every baked mesh (Smart UV Project, island margin 0.02, or *Lightmap Pack*). Keep UV0 untouched for the tiling textures.
4. **Bake** in Cycles: bake type *Diffuse*, contributions *Direct + Indirect*, **Color off** (bake light only, not the albedo). Use 2048×2048 for the building and 2048×1024 for the ground patch, 256–512 samples, with denoise on.
5. **Also bake AO** into a separate map (or a channel) at the same resolution.
6. Save to `public/assets/textures/lightmaps/dreams_lightmap.hdr` (or 16-bit PNG with a documented intensity scale) and `dreams_ao.png`, then compress to KTX2.
7. **Script it:** new `blender/scripts/bakeLightmap.py <asset>`. It opens the bake scene, adds UV2 if missing, bakes, saves and re-exports the GLB *with* UV2. Every future building calls the same script. **This script is the actual deliverable of Stage 5.**

### 5b. In Three.js (🤖)

1. In `applyDreamsModelPolicy` (`createWorld.ts`), load the lightmap and AO, assign `material.lightMap`, `lightMapIntensity`, `aoMap` and `aoMapIntensity`, and make sure the material samples the channel the glTF loader puts the second UV set on (`uv1`).
2. Turn the Dreams-specific real-time point lights down or off in `LocalLightRegistry` (the lightmap now carries them). That frees budget for the player.
3. Apply the ground lightmap to a **Dreams ground patch** mesh: either a separate road/pavement tile at Dreams, or a multiply-blended decal over the existing road with the pool of light and contact shadows baked in.
4. Dev flag `?lightmaps=off` for A/B comparison.

### 5c. The proof gate ✅

Compare side by side at `dreams-target`, `dreams-angle` and `park-to-dreams`: baseline → after Stage 5 → reference. **Pass** if all of these hold:

- [ ] Light falls down the Dreams panel in a gradient; the brick return picks up tube spill.
- [ ] There's visible contact darkness where walls meet ground, under the ramp, bins and railings.
- [ ] The shutters look ribbed and dirty, not flat grey.
- [ ] Fps ≥ baseline at MEDIUM; draw calls haven't risen; the extra texture memory is ≤ 40 MB.
- [ ] Rebuilding from scratch is **one command**: `blender --background --python blender/scripts/bakeLightmap.py -- dreams`.
- [ ] Daniel says "yes, this is the direction".

**If it fails:** write down which box failed in SYNC.md and fix that single thing. Don't start other buildings.

---

## Stage 6 — Shadows (2–3 days · 🤖)

Static things are already shadowed by the bake. Real-time shadows are only needed for things that **move**.

1. **Contact shadow** under the player and bike: a soft, dark, radial-gradient quad projected on the ground, scaled by height above ground. It's always on, at every quality level, and costs one draw call. (The camera fix already mentions a contact shadow; extend that rather than making a new one.)
2. **One real shadow-caster on MEDIUM/HIGH:**
   - Enable the renderer's shadow map (`renderer.shadowMap.enabled = true`, `PCFSoftShadowMap`), gated by a new `QualityProfile.playerShadow` flag (currently `geometry.shadowsEnabled` does nothing).
   - The **managed public-light proxy** (the one that already follows the player between lamp pools) gets `castShadow = true` with a 1024 map (512 on MEDIUM) and tight shadow-camera bounds (~6 m).
   - Only the player and active bike have `castShadow = true`. **Remove the blanket `castShadow = true`** in `loadModel.ts` and `createWorld.ts`. Ground and nearby walls get `receiveShadow`.
3. Fade the shadow in and out with the proxy's existing fade, so it never pops.

**Done when:** walking under a lamp at `public-light-pool`, the rider casts a soft shadow that stretches away from the lamp, and costs less than 1 ms on MEDIUM.

---

## Stage 7 — Replace the body (1–2 weeks · 🧑 Blender, 🤖 runtime)

Can run **in parallel** with Stages 3–6.

1. **Choose the base** (🧑 decision):
   - **Free:** MPFB2 (MakeHuman for Blender), with CC0-licensed outputs. Set a Black male, ~1.80 m, slim-athletic, then export the "game engine" rig.
   - **Paid, faster and better:** Character Creator 4, which requires its game-export licence.
2. **Proportions from reference:** match against the photos in `references/characters/named characters/player/`.
3. **Head and hair:** a sculpted scalp with cornrow geometry (a few tube strips) plus a normal map. The face can stay simple, since it's rarely seen close up.
4. **Skin material:** albedo + normal + roughness at 2K. In Three.js, a `MeshPhysicalMaterial` with a slight `sheen` for skin.
5. **Rig:** keep the MPFB/CC4 skeleton, or run it through **Mixamo** auto-rig. Record the bone names.
6. **Budget:** body + head + hair ≤ 12k triangles (clothes add the rest; total ≤ 35k), ≤ 4 materials.
7. **Scripted export:** `blender/scripts/exportPlayerCharacter.py` → `public/assets/models/player-character-v2.glb`. Keep `player-character-rigged.glb` as the fallback until v2 is approved.
8. **Animation — the half that actually removes "robotic":**
   - 🧑 Download from Mixamo (in-place versions): idle, walk, jog, turn-left/right, bike-mount, bike-idle, pedal. Or record your own with a phone mocap app (Move One, Rokoko Video).
   - 🤖 In `PlayerController.ts`, add an `AnimationMixer` that plays and cross-fades clips by speed/state. Keep the existing two-bone IK only as a **layer on top** (hands on handlebars, feet on pedals), remapped to the new bone names. The sine-wave stride code (`ANIMATED_BONES`, `stridePhase`) is removed once clips replace it.
   - 🤖 Keep the existing visibility lift (`applyPlayerVisibilityPolicy`) working on the new materials.

**Done when:** the rear gameplay view shows a human silhouette with natural weight shift when walking, the walk doesn't foot-slide at normal speed, fps is unchanged, and the GLB is ≤ 6 MB (KTX2).

---

## Stage 8 — Denim, bag, trainers, greaves (1–2 weeks · 🧑)

1. **Pattern the garments** in **Marvelous Designer** (paid) or Blender's Cloth modifier (free): an oversized denim jacket (dropped shoulder, boxy, hip length) and oversized jeans (wide straight leg, stacking at the ankle). Drape them on the Stage 7 body in the rest pose.
2. **Retopologise** to a clean game mesh (Blender Quad Remesher or manual): jacket ≈ 6–8k triangles, jeans ≈ 4–6k.
3. **Bake** the high-detail folds from the simulation onto the low mesh as a **normal map** (Blender *Selected to Active* bake).
4. **Denim material:** a 2K tiling **twill** normal + albedo (indigo with a white weft showing through), plus a per-garment **wear mask** for fading at the knees, seat and pocket edges and a whiter seam line. Leave the sheen off (denim is matte, roughness ~0.85).
5. **Skin the garments** to the Stage 7 skeleton (*Data Transfer* of weights from the body, then fix the shoulders and knees by hand). Delete body faces hidden under clothes to save triangles and stop them poking through.
6. **Bag:** black leather (roughness 0.35–0.5, faint creasing normal map), rigid, parented to the spine bone.
7. **Silver trainers:** metallic 0.7, roughness 0.35, with a scuff mask. Reference: `references/characters/clothing/silver nikes`.
8. **Greaves:** hard-surface shin and hand pieces, parented to the shin and hand bones, in brushed metal.
9. **Silhouette check:** render the character from behind at 10 m against the dark street. Bag, oversized denim and greaves must read instantly (`ART_DIRECTION.md` → "Player Character Fashion").

**Done when:** jeans and jacket read as denim (not generic cloth) at gameplay distance, nothing pokes through during the walk and pedal clips, and the total player is ≤ 35k triangles.

---

## Stage 9 — Roll out (ongoing, only after the Stage 5 gate passes)

For each building, in order of how often the player sees it (Dreams → Nice Things → Vinyl Exchange → Coral → bus shelter → the rest):

1. 2K texture set (Stage 3).
2. Bevel pass in its `create*.py` (1–2 cm on visible edges).
3. `bakeLightmap.py <asset>` (Stage 5).
4. Ground patch lightmap for its frontage.
5. Before/after/fps entry in `renders/realism-pass/<asset>/`.

Then the world-wide pieces: background tower window-grid textures, rain particles, lamp halo sprites, and prop instancing and LOD (`PERFORMANCE.md` future work).

---

## Order at a glance

```
Stage 0  setup + baseline            ─┐
Stage 1  retro settings off           │  week 1
Stage 2  grade                       ─┘
Stage 3  textures + materials (Dreams) ─┐
Stage 4  env map + puddles + streaks    │  weeks 2–3
Stage 5  BAKED LIGHTING — PROOF GATE  ──┘  ← stop and judge here
Stage 6  player/bike shadows              week 4
Stage 7  body + animation     ─┐  runs in parallel
Stage 8  denim + kit          ─┘  from week 2
Stage 9  roll out building by building
```

Each stage ends with: screenshots in `renders/realism-pass/<stage>/`, a line in that folder's `numbers.md` (fps / draw calls / texture MB at the Stage 0 views), and a SYNC.md entry.
