# Hero Street Visual Production Pass

Date: 10 September 2026

## Outcome

The 30–50 metre Dreams / North Road / Central Park edge / Bus Stop A area now provides the first production-oriented environment slice. Dreams retains its approved low, wide gabled architecture and uses low-resolution derivatives from the repository-owned Dreams photograph for the gable, shutters and right-hand brick return. The surrounding street has authored repairs, ironwork, imperfect kerbs, litter, commercial bins, utility hardware and broken coloured wetness. Bus Stop A is unchanged as an asset and receives only contextual dressing.

The pass adds no gameplay systems, bike implementation, phone, NPC AI, quest or map redesign. It adds no real-time lights and retains the fixed-timestep and quality-profile architecture.

## 1–2. Files

Created:

- `src/world/createEnvironmentKit.ts`
- `public/assets/textures/world-prototype/dreams-cladding-hero.png`
- `public/assets/textures/world-prototype/dreams-shutter-hero.png`
- `public/assets/textures/world-prototype/dreams-brick-hero.png`
- `public/assets/textures/world-prototype/street-detail-atlas.png`
- `public/assets/textures/world-prototype/soil-litter-hero.png`
- `renders/hero-street-pass/01-player-start-toward-dreams.png`
- `renders/hero-street-pass/02-dreams-frontal.png`
- `renders/hero-street-pass/03-dreams-45-degrees.png`
- `renders/hero-street-pass/04-bus-shelter-player-distance.png`
- `renders/hero-street-pass/05-north-road-shopfront.png`
- `renders/hero-street-pass/06-park-edge-to-dreams.png`
- `renders/hero-street-pass/07-close-street-detail.png`
- `renders/hero-street-pass/08-performance-overlay.png`
- `docs/HERO_STREET_VISUAL_PRODUCTION_REPORT.md`

Modified:

- `scripts/generateWorldTextures.mjs`
- `src/camera/ThirdPersonCamera.ts`
- `src/main.ts`
- `src/rendering/worldGraphics.ts`
- `src/rendering/worldMaterials.ts`
- `src/ui/DebugOverlay.ts`
- `src/world/createDreamsBuilding.ts`
- `src/world/createWorld.ts`

## 3. Dreams changes

- Preserved the low 18 metre-wide mass, deep gable, pitched roof, shutter bays, right-side return, raised plinth, accessibility ramp, railings, alarm and CCTV.
- Added photo-derived gable, shutter and brick-return materials while retaining economical construction.
- Added a dirty handwritten CCTV/no-dumping notice, sticker cluster, drainpipe, rainwater hopper, wall cable and cheap vent.
- Added a Dreams-side commercial-bin, trolley, rubbish and wet-cardboard cluster, utility cabinet, drains, manholes, road repairs and chipped kerb stones.
- Batched the complete railing assembly into one instanced draw and batched upper tubes, lower tubes and brackets by type.

## 4. Environment kit

The reusable kit currently contains:

- commercial-bin body, lid and opening components;
- battered bollards;
- wet drain/utility covers and round manholes;
- asphalt repair/wet-patch treatments;
- imperfect kerb stones;
- tied rubbish bags, paper and wet-cardboard clusters;
- four-component tree construction with approximately six silhouette combinations;
- low shrub variants, bare-soil treatments and a two-part bench system;
- Dreams railing, drainpipe, hopper, vent, cable, shutter and façade-detail patterns suitable for extracting into later architecture modules.

Repeated pieces use shared primitive geometry/materials and `InstancedMesh`. Placement is authored in clusters at Dreams, the bus shelter and selected existing city locations rather than uniformly scattered.

## 5–6. Textures and decals

New on-disk textures:

| Texture | Resolution | Source/use |
| --- | ---: | --- |
| Dreams cladding | 512 × 128 | photographic derivative for gable character |
| Dreams shutters | 512 × 256 | photographic derivative for shutter dirt/exposure |
| Dreams brick | 256 × 256 | photographic derivative for right-hand return |
| Street detail atlas | 256 × 256 | procedural iron, slot, rust and repair information |
| Soil/litter | 256 × 256 | procedural soil, leaf, foil and wet-paper information |

New runtime decals are a 256 × 256 distressed handwritten notice and a 256 × 256 sticker cluster. Existing poster, graffiti and broken-reflection materials remain shared.

## 7–9. Lighting, wetness and park edge

No dynamic light was added. The hero selector remains at 2 LOW / 4 MEDIUM / 5 HIGH, with zero spotlights. Dreams continues to use one selected hero point light; its façade tubes, sign, photographic exposure and shutter wash remain emissive/fake treatments.

Wetness continues to use moderately rough asphalt rather than a mirror plane. The Dreams road now combines the existing cool-white/cyan broken reflection strips with separately authored darker repair shapes, iron covers, manholes and uneven kerb edges. Existing amber, magenta and bus-shelter spill remains unchanged.

The park edge now uses instanced tree construction with varied crown offsets, scale and rotation; separate dark and amber-caught foliage; an extra bench; low shrubs; and six bare-soil/litter treatments. The existing damp grass and worn path network remain inexpensive shared surfaces.

## 10–16. Performance results

Measurements use the same 1280 × 720 CSS viewport and Apple M1 class test system as the stabilization milestone, after asset/shader warm-up. The immediate pre-pass values come from the approved performance-phase start view and report.

| Metric | Before | After |
| --- | ---: | ---: |
| Start-view draw calls, MEDIUM | 468 | 400 |
| Start-view triangles | 7,893 | 9,541 |
| Resident geometries | 199 | 197 |
| Resident textures | 103 | 113 |
| Distinct scene materials | 253 diagnostic baseline | 196 current MEDIUM census |
| Active local lights, MEDIUM | 4 | 4 |
| Active spotlights | 0 | 0 |

Draw calls fell by 68 (14.5%) while visible triangles rose by 1,648 for the new low-cost detail. Geometry residency also fell by two because tree, furniture and Dreams railing instances replaced many independent meshes. The texture increase includes five new disk textures, two runtime decal canvases and profile/model residency differences.

| Profile | FPS | Median / p95 frame time | Draw calls | Triangles | Active lights | Buffer |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| LOW | 60 | 16.7 / 17.6 ms | 387 | 9,528 | 2 | 832 × 468 |
| MEDIUM | 60 | 16.7 / 17.7 ms | 400 | 9,541 | 4 | 921 × 518 |
| HIGH | 58 | 16.7 / 33.4 ms | 400 | 9,541 | 5 | 1024 × 576 |

The in-app browser throttled when hidden, so reported steady-state measurements were taken with its test surface foregrounded. HIGH remains above the documented 30 FPS minimum, although its p95 frame pacing has less headroom than MEDIUM. The fixed-step files and player movement implementation were not modified; simulation slowdown protection is unchanged.

## 17–18. Build and browser result

`npm run build` passes with TypeScript and Vite. Vite retains its non-blocking warning that the main minified chunk exceeds 500 kB.

The scene was exercised in-browser in LOW, MEDIUM and HIGH, including every fixed capture view. No console errors, warnings or unexpected asset 404s were recorded. The photographic bus shelter GLB loaded successfully and was not replaced or modified.

## 19. Screenshot paths

1. `renders/hero-street-pass/01-player-start-toward-dreams.png`
2. `renders/hero-street-pass/02-dreams-frontal.png`
3. `renders/hero-street-pass/03-dreams-45-degrees.png`
4. `renders/hero-street-pass/04-bus-shelter-player-distance.png`
5. `renders/hero-street-pass/05-north-road-shopfront.png`
6. `renders/hero-street-pass/06-park-edge-to-dreams.png`
7. `renders/hero-street-pass/07-close-street-detail.png`
8. `renders/hero-street-pass/08-performance-overlay.png`

## 20. Remaining visual weaknesses

- Dreams is deliberately a hybrid reconstruction: its most characteristic surfaces are photographic, but the full façade is not yet one calibrated photographic unwrap.
- The adjacent Renae mass and distant estate towers remain visibly below the Dreams/shelter benchmark and reduce continuity in wide shots.
- Park grass still reveals its small repeating tile in broad foreground compositions; shrubs and soil break it up locally but do not remove the repetition.
- Close props are intentionally economical and will benefit from a shared UV atlas with more object-specific photographic wear.
- HIGH has acceptable average performance but a 33.4 ms p95 in this browser test, so later city propagation should preserve or improve the current batching ratio.

## 21–22. Git state and suggested commit

The approved stabilization milestone was committed and pushed to synchronized `main` as `85c91e5` with the exact message `perf: stabilise simulation timing and reduce dynamic lighting`.

The hero visual pass remains uncommitted for visual review. Suggested commit message:

`feat: establish Dreams hero street environment kit`
