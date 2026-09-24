# Visual Realism Roadmap — from "Lego" to the Dreams night reference

Date: 24 September 2026 · Author: Claude (consultation session for Daniel)

Target image: `renders/visual-gap-2026-09-24/00-target-reference-dreams-night.webp`
Current game, same place: `renders/visual-gap-2026-09-24/01-current-dreams-target.png` and `02-current-park-to-dreams.png` (captured this session with `?view=dreams-target` / `?view=park-to-dreams&quality=high`. The browser was software-rendered (SwiftShader), so colour and shading are right but frame rate means nothing.) See also `references/screenshots/V3/05-dreams-photographic-facade.jpg`.

---

## 0. What the reference actually is

The reference is an AI paint-over of the game's own V3 screenshot. The composition matches `references/screenshots/V3/05-dreams-photographic-facade.jpg` exactly: the placeholder capsule player, the `N_025.3` label, the debug overlay (with the old "Harperhay" spelling), the Dreams gable, the ramp and railings, the towers behind. This is good news:

- **The layout, scale, camera and composition are already right.** Nothing needs to be rebuilt at the level of the world plan.
- The gap is entirely **surface, light and density**: how materials respond to light, how light falls off and reflects, how much small detail there is, and the post-process.
- The reference also carries AI artefacts you shouldn't chase literally: the blocky "mosaic" pixellation across the ground and walls, text that is too perfect, and reflections that are physically inconsistent. Decide consciously whether you *want* the mosaic grain as a stylistic layer (it could be a nice "compressed photograph" signature). Don't copy it by accident.

A realistic expectation: a Three.js browser game at 60 fps on a laptop can get to **roughly 70–80 % of this image**, and closer in authored hero spots like Dreams. The missing last 20 % is what offline/path-traced rendering gives. It can be faked in specific places, but not everywhere.

---

## 1. Why it looks like Lego right now: the diagnosis

These are ordered by how much each contributes to the "toy" read. Items 1–4 are **configuration left over from the old Dreamcast/PS2 art direction**. `AGENTS.md` says that direction was abandoned, but the code still enforces it.

| # | Cause | Where | Effect |
|---|---|---|---|
| 1 | **Flat shading is on globally.** `facetedLighting: true` feeds `flatShading` on every world material | `src/rendering/visualStyle.ts:137`, `worldMaterials.ts:128`, road/pavement/park/decal/graffiti surfaces | Every surface is lit per-triangle. This is the single biggest "low-poly toy" signal. |
| 2 | **No environment map / image-based lighting.** `scene.environment` is never set anywhere | whole repo | Standard materials have nothing to reflect. Metal, glass, wet asphalt and painted cladding all read as matte plastic. Wet roads *cannot* look wet without it. |
| 3 | **Shadows are completely off.** `shadowsEnabled: false`, `renderer.shadowMap` is never enabled, so the ~15 `castShadow = true` calls do nothing | `visualStyle.ts:138`, `createWorld.ts` | Nothing is grounded. Objects float, and there's no contact darkness under bins, railings, bollards or the player. |
| 4 | **Colour posterisation.** The grade quantises to 32 levels per channel, with ordered dither | `visualStyle.ts:80`, `createPostProcessing.ts` | Banding in dark gradients (the whole night sky, every light pool) gives a retro, digital look. Photographs have smooth falloff. |
| 5 | **Tiny textures.** World textures are 128–512 px; few materials have normal or roughness maps; some graphics use `NearestFilter` (`RETRO_GRAPHIC`) | `public/assets/textures/world-prototype/`, `visualStyle.ts:applyTextureProfile` | Surfaces go soft and smeared up close, with no micro-surface (brick relief, shutter ribs, cracked concrete). |
| 6 | **Geometry built from boxes in code.** `createWorld.ts` is 4,175 lines, much of it hand-placed boxes and cylinders; background towers are dark boxes | `src/world/createWorld.ts` | No bevels, trims, soffits, gutters, window reveals or roofline clutter. Real buildings catch light on their *edges*; boxes don't have any. |
| 7 | **No ambient occlusion** (baked or screen-space) | — | Corners, junctions and the base of walls don't darken, so everything looks assembled rather than built. |
| 8 | **Light doesn't *land*.** Emissive tubes glow but barely light the fascia and shutters. Streetlight pools are painted additive decals. Reflections are additive `reflection-broken-overhaul` sprites | `createWorld.ts:~3748`, `LIGHTING_AUDIT.md` | The reference's strongest feature is light *on* surfaces: the gradient down the Dreams panel, the sodium spill on the wall, streaks on the wet road. |
| 9 | **Low internal resolution.** MEDIUM renders at 0.72 × a DPR capped at 1.25 | `QUALITY_PROFILES` | Edges soften and thin details (railings, cables) shimmer. This is fine for performance, but it needs a better AA/upscale. |
| 10 | **Player built from primitives, animated procedurally.** The GLB is boxes and rounded blocks from `blender/scripts/createPlayerCharacter.py`, and `PlayerController.ts` swings bones with sine waves | see §5 | Robotic motion plus a toy body. The art-direction doc already calls it a placeholder. |

What already works and should be kept: the darkness between the light pools, the cold-fluorescent vs sodium contrast, AgX tone mapping, the fog, the planimetric camera, the lighting-budget system (`LocalLightRegistry`), and fixed-step simulation. The reference *keeps* all of this and adds realism on top.

---

## 2. What makes the reference read as "real": a breakdown

1. **Wet ground doing most of the work.** Roughly 40 % of the frame is reflective asphalt and paving. Reflections of every light source are stretched vertically (anisotropic wet-road streaks), broken up by puddle masks and micro-normal noise.
2. **Light with gradients.** The Dreams panel is brighter at the top under the tubes and falls off downward. The sodium lamp has a soft cone plus a warm spill on the wall and tree. Nothing is uniformly lit.
3. **Grounding.** Contact shadows and AO under the bins, bollards, ramp, kerbs and railings, with a dark line where the wall meets the ground.
4. **Material specificity.** Painted steel cladding with panel seams, roller shutters with ribs and dirt streaks, brick with mortar relief, paving slabs with worn edges, glossy bollards with reflective bands.
5. **Density of small true things.** Graffiti tag, alarm box, CCTV, poster frame, handrail brackets, drainage, a bin with stickers, fence panels, a tree canopy silhouette, lit windows in the towers, and signage bleeding in from the next shop.
6. **Photographic post.** Slight bloom halos on the tubes, a gentle vignette, fine grain, no banding, a slightly lifted black floor, and a cool/warm split between tubes and sodium.

---

## 3. The plan: ordered, with performance cost

Principle: **bake what doesn't move, fake what you can, compute in real time only what must react to the player.** The game is already CPU/draw-call bound (589–1,705 draw calls per frame, about 43–55 fps measured on the 24 September runs), so realism has to come mostly from *better pixels in the same draw calls*, not from more real-time lights or passes.

### Phase A — Undo the retro settings (1–2 days, ~free performance)

- `facetedLighting: false`. Make sure GLBs export smooth normals, with auto-smooth/weighted normals in Blender.
- Remove colour quantisation. Keep dither only as ~1/255 anti-banding noise, not as a stylistic 32-level posterise. Keep grain.
- Switch `RETRO_GRAPHIC` signage to linear filtering and mipmaps unless it's deliberately pixel art.
- Add SMAA or FXAA after the grade so the 0.72 render scale looks cleaner. SMAA costs ~0.5 ms.
- **Expected:** an immediate step away from "Lego", with no new assets needed.

### Phase B — Image-based lighting and a real wet road (3–5 days, low cost)

- Author one or two **night HDR environment maps**: render a 360° panorama of the street from Blender at Dreams, or use a Poly Haven CC0 night HDRI as a stopgap. Prefilter it with `PMREMGenerator` once at load and set `scene.environment` with a low `environmentIntensity` (~0.15–0.3) so darkness survives. This is a **one-time cost**: no per-frame work.
- Rebuild the wet asphalt/paving material: 1–2K PBR set (albedo, normal, roughness), with a **puddle mask** that drives roughness from ~0.05 in puddles to ~0.7 on dry patches. A small normal-map "ripple" scroll is optional.
- **Reflection strategy, cheapest first:**
  1. **Light-streak billboards** (the classic racing-game trick): for each emissive source near the camera, a vertically stretched, additive, puddle-masked quad mirrored under the ground. It's nearly free and gets 70 % of the reference's road. It replaces the current generic `reflection-broken-overhaul` sprites with per-light, view-facing ones.
  2. **Box-projected cube-map** at hero spots (Dreams frontage), baked once from Blender or captured once at runtime with `CubeCamera`. That gives correct-ish reflections of the façade in puddles at zero per-frame cost.
  3. **HIGH only:** a ¼-resolution planar reflection of just the emissive/bright layer, blurred and masked by roughness. That's one extra cheap render. Measure it before committing.
  - Avoid full screen-space reflections on WebGL. They cost too much for the target hardware.

### Phase C — Baked lighting and ambient occlusion in Blender (1–3 weeks, the big one)

This is **the one structural change worth making now**, because it changes the asset pipeline for every building you make from here on.

- For each hero building (start with Dreams), add a second UV channel (lightmap UVs) in its `blender/scripts/create*.py` script.
- In Blender Cycles, light the scene with the real practical lights (tubes, sodium lamps, shop signs) and **bake AO plus indirect/diffuse lighting into a lightmap** (1K–2K per hero building, KTX2-compressed).
- In Three.js, assign `material.lightMap` / `aoMap` (uv1), and keep the emissive tubes visible. The façade gradient, the spill on the brick return and the contact darkness at the base all come "for free" at runtime.
- Keep `LocalLightRegistry` real-time lights **only** for what must react to the player: the character in light pools and the bike.
- Bake a **ground lightmap/decal** for each streetlight pool (a soft sodium ellipse with falloff) instead of the flat additive pool, and bake contact shadows under static props into the ground texture.
- Performance: lightmaps add texture memory, not draw calls or shader cost. This is how *every* realistic mobile/web game gets its look.

### Phase D — Real-time shadows only for the player and bike (1–2 days, small cost)

- Enable `renderer.shadowMap` (PCFSoft), with **one** shadow-casting light: the managed public-light proxy or a single sodium lamp near the player. Use a 1024 shadow map, cast only from player and bike, and receive on ground and nearby walls.
- Or cheaper: a **blob/contact shadow** decal under the player (a soft dark ellipse projected down) plus a very short, soft directional shadow. Already partly there ("contact shadow retained" in the camera fix).

### Phase E — Materials and textures (ongoing, per asset)

- Move to **1K–2K PBR texture sets** for hero surfaces, from scanned CC0 sources (Poly Haven, ambientCG) for generic materials: brick, asphalt, concrete, paving, painted metal, roller shutter. Keep Daniel's own photographs for signage and specific façades (the TSAU photographic identity).
- Every texture ships as **KTX2 (Basis UASTC for normals, ETC1S for albedo)** so GPU memory stays low. SYNC notes a KTX2/Meshopt pipeline was being written on Daniel's machine but isn't committed in this checkout yet. Land it first.
- Add **trim sheets** and **decals** (grime streaks under sills, rust runs, sticker clusters, graffiti tags) as a cheap layer that makes clean surfaces look lived-in.

### Phase F — Geometry detail on hero buildings (per asset, in Blender)

- Bevel every visible edge (a 1–2 cm bevel with weighted normals catches light like the reference's cladding and shutter frames).
- Add soffit, gutters, downpipes, fascia depth, window reveals, shutter boxes, roofline clutter (vents, aerials), and kerb chamfers.
- Background towers: a proper low-poly block with a **window-grid emissive texture** where a random 10–20 % of windows are lit warm. It's one draw call per tower and makes a big difference to the skyline in the reference.
- Keep moving procedural boxes *out* of `createWorld.ts` and into Blender GLBs (already the stated asset-first policy).

### Phase G — Atmosphere and post (2–4 days, small cost)

- **Rain:** one GPU-instanced streak particle system around the camera (a few thousand quads, ~1 draw call), plus screen-space rain-drop ripples on puddles via the normal map. Optional, but it sells "wet".
- **Light halos:** soft camera-facing glow sprites on each lamp and tube (not real volumetrics). Tune bloom threshold and strength after Phases A–C, since bloom looks different once highlights are real.
- **Grade:** lift the blacks slightly (the reference's shadows sit around 5–8 % luminance, not 0), and use a gentle teal/amber split rather than global saturation 1.12. Keep grain, keep vignette, add a whisper of chromatic aberration only if it serves the "photograph" read.
- **Ambient occlusion:** baked (Phase C) is the main answer. A half-resolution screen-space AO (Three.js `GTAOPass`) is an option on HIGH only. Measure it: it costs 2–4 ms.

### Phase H — Performance work that pays for all of the above

- Land the KTX2 + Meshopt compression.
- Instance repeated props (bollards, streetlight parts, bins, railings, windows): `PERFORMANCE.md` already lists this as future work.
- **Distance culling/LOD**: hide small props beyond ~40 m, and swap background buildings to simple versions.
- Fix the first-visit stutter (lazy GPU uploads, see SYNC 24 September) with a staged pre-warm or area streaming. Realistic textures make this worse if it isn't solved.
- Keep the LOW/MEDIUM/HIGH profile idea: LOW = lightmaps + IBL + billboards only. MEDIUM = + bloom + SMAA + player shadow. HIGH = + planar reflection + GTAO.

---

## 4. Do you need to change engine or architecture?

**No engine change.** Stay on Three.js and the browser. The target look is achievable with WebGL2 plus baked lighting, and the project's identity is a browser artwork embedded on danieloye.com. Unreal/Unity would reach the reference faster, but you'd lose the web embed (Unity WebGL is heavy, and Unreal has no current web export) and throw away a large, working codebase.

**Structural changes worth making now, before more assets are built:**

1. **Lightmap/AO bake step in the Blender pipeline** (second UV set plus a bake script shared by all `create*.py` builders). Every building made without it will need revisiting.
2. **Retire the retro rendering flags** (flat shading, quantisation, nearest filtering) and reconcile `docs/ART_DIRECTION.md`'s stale sections, so future sessions stop re-applying the old look.
3. **A texture standard**: 1–2K PBR plus KTX2, and a naming convention for albedo/normal/ORM maps.
4. **Character pipeline switch** from primitives plus procedural bone swinging to a proper human mesh plus animation clips (§5).

**Worth knowing about, but not now:** Three.js's `WebGPURenderer` (with TSL node materials) has built-in SSR, GTAO and temporal AA passes. It could give real reflections on HIGH later. But it would mean porting the post stack and the `onBeforeCompile` shader patches (player visibility lift, finite-colour guard), and WebGPU support on Safari/older machines is still uneven. Revisit when the art is locked.

---

## 5. Characters: from blocky to realistic

**Current state:** `player-character-rigged.glb` (5 MB) is assembled from primitives (boxy hoodie, cylinder limbs, block trainers) by `blender/scripts/createPlayerCharacter.py`. `PlayerController.ts` animates the bones procedurally with sine-wave stride and two-bone IK. Both halves need replacing to read as realistic. Motion matters as much as the mesh: a realistic body moving on sine waves looks worse than a toy.

**Recommended pipeline (beginner-friendly, web-budgeted):**

1. **Base body:** generate a realistic, correctly proportioned male base mesh with **MPFB2 (MakeHuman for Blender, free, CC0 outputs)**. **Character Creator 4** (paid, needs its game-export licence) is higher quality and faster, and handles skin, hair and clothing well. MetaHuman is very realistic, but too heavy for the web without major reduction work. Check its current licence terms before using it outside Unreal. Avoid Ready Player Me (the service has shut down).
2. **Clothing:** model the oversized denim jacket and jeans in **Marvelous Designer** (or Blender cloth sim, free but slower to learn), simulate the drape once, then **retopologise** to game density and bake the high-detail folds into a normal map. `ART_DIRECTION.md` already describes this flow.
3. **Materials:** denim twill normal map, stitching and fading in the albedo, leather bag with roughness variation, silver trainers with a metallic/roughness map, skin with a subtle subsurface approximation (`MeshPhysicalMaterial` sheen/`thickness`, or a warm wrap-lighting tweak). Cornrows as a sculpted scalp mesh with a normal map plus a few hair-card strips.
4. **Rig and animation:** auto-rig in **Mixamo** (free) or Blender's Rigify. Pull walk, idle, run, turn, bike-mount and pedal clips from Mixamo, or record your own mocap cheaply with a phone app (Move One, Rokoko Video). Play them in Three.js with `AnimationMixer` and cross-fade blending. Keep procedural IK only as a layer on top (feet on kerbs, hands on handlebars).
5. **Budget:** player 20–35k triangles, one or two 2K texture sets (body, garments) in KTX2, and ≤ 4 skinned draw calls. NPCs: 8–15k triangles, 1K textures, with a LOD at ~15 m.
6. **Silhouette first:** from the third-person camera you mostly see the back and shoulders. The bag, oversized denim shape, greaves and cornrows carry the character, not the face. Spend detail there.

AI 3D generators (Hunyuan3D, Rodin, both reachable through the Blender MCP) are useful for **props** and as a sculpting starting point. Their topology and rigs aren't good enough for a hero character yet.

---

## 6. Suggested order of work

1. Phase A (retro flags off) plus SMAA. Take before/after screenshots at the V3 views.
2. Land KTX2/Meshopt (Phase H) so heavier textures don't hurt.
3. Phase B (IBL plus wet road plus light-streak reflections) at the Dreams frontage only.
4. Phase C (baked lightmap/AO) on Dreams only: a **vertical slice**. Compare against the reference side by side.
5. If the slice is convincing, write the bake step into the shared Blender helpers and roll it out building by building.
6. Character: base mesh plus Mixamo walk in parallel with steps 3–5 (it's an independent track).
7. Phases D, F and G as polish, measuring fps at every step with the `H` overlay on the repeatable dev views.
