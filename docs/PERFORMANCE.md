# Performance Policy

## Non-negotiable principle

**Rendering performance must never change simulation speed.**

The renderer and gameplay clock are separate. Raw animation-frame time is used for measurement and camera smoothing. Gameplay systems advance at a fixed 60 Hz through a bounded accumulator.

## Simulation timing

- Fixed timestep: `1 / 60` second.
- Maximum substeps per rendered frame: `16`.
- Ordinary frame deltas up to 250 ms are accumulated and simulated rather than discarded.
- A delta above 250 ms is treated as an extreme gap and resets the accumulator.
- Any document visibility transition resets the accumulator. Three.js's connected `Timer` resets its timestamp on visibility restoration as an additional guard.
- Player movement, collision, facing, and world animation update inside fixed steps.
- Camera smoothing updates once per rendered frame from the real visible-frame delta. Pointer orbit input is therefore consumed once, not multiplied by catch-up substeps.

## Lighting budget and philosophy

Most environmental illumination in Zealot of Harpurhey is intentionally represented using emissive materials, photographic/baked illumination, geometric light cones and fake light pools rather than large numbers of real-time dynamic lights.

The old streetlight spotlights and routine always-on storefront lights are removed. Those locations retain their identity through emissive signs and textures, painted reflection geometry, visible additive cones, fake pools, and photographic illumination.

All runtime local point lights now pass through `LocalLightRegistry`. The registry owns both static hero lights and asset-loaded lights, including Coral's pair after the Coral GLBs load. It chooses atomic lighting installations rather than individual loose lights, so LOW cannot select only half of a deliberately balanced pair. The selector ranks by either real point-light reach at the player or explicit location relevance for thresholds and lit facades, with short fades to avoid visible switching.

Public streetlights remain mostly graphic objects. A single managed public-light proxy moves to the nearest streetlight pool and only contributes when the player is inside that pool, so the rider responds to streetlight islands without turning every pole into a real-time light.

The normal active point-light ceiling is still the selected profile's 2/4/5 budget, including Coral, public-light proxy use, and lights fading out. No local spotlights remain.

## Quality profiles

MEDIUM is the default desktop profile. It prioritises a stable 60 FPS on a typical Apple Silicon laptop over Retina-native pixel density.

| Profile | Render scale | DPR cap | Maximum effective pixel ratio | Bloom | Active local-light budget |
| --- | ---: | ---: | ---: | --- | ---: |
| LOW | 0.65 | 1.00 | 0.65 | Off | 2 |
| MEDIUM | 0.72 | 1.25 | 0.90 | On, strength 0.30 | 4 |
| HIGH | 0.80 | 1.50 | 1.20 | On, strength 0.34 | 5 |

Select a profile with `?quality=low`, `?quality=medium`, or `?quality=high`. An absent or invalid value resolves to MEDIUM.

Bloom remains available where it materially supports emissive photographic highlights. LOW disables it. MEDIUM slightly reduces its strength. HIGH retains the previous strength while still respecting the five-light ceiling.

## Geometry and material reuse

Phase 1 caches identical box, cylinder, circle, cone, dodecahedron, and Dreams railing geometries. Repeated flat-colour standard/basic materials are shared where mutation is not required. This reduced resident geometry at the start view from 398 to 199 without merging objects or changing their independent transforms.

Static hero GLBs are also batched after their material policy and authored-anchor lookups have run. Opaque, non-animated meshes with the same material and compatible vertex layout are transformed into model-local space and merged. Transparent meshes remain separate so object-level sorting is unchanged; skinned, instanced, morph-target, multi-material, and articulated Sterling parts are excluded.

The 2026-09-20 browser pass at 1280 × 720, DPR 1 and MEDIUM measured these complete-composer draw-call changes after assets settled:

| Development view | Before | After | Reduction |
| --- | ---: | ---: | ---: |
| Start | 1,737 | 589 | 66% |
| Sterling South | 2,594 | 676 | 74% |
| East Shops | 1,996 | 842 | 58% |
| Spice Cabin | 5,319 | 1,705 | 68% |

At Spice Cabin, the previously worst measured view, observed frame rate increased from approximately 14 to 22 FPS in the same in-app browser test surface. The scene is still CPU-limited there and remains the priority for a later visibility/LOD pass. Static batching intentionally accepts a modest increase in submitted triangles where a whole material batch intersects the frustum; the reduced submission count is the larger win on the current target hardware.

Future work may instance repeated streetlight parts, tower windows, trees, benches, bollards, and road markings. That work should be measured and kept within the existing world architecture rather than becoming a renderer rewrite.

## Development diagnostics

The development-only overlay is toggled with `H` and reports:

- real FPS and current raw frame milliseconds;
- renderer draw calls and triangles;
- active point and spot lights, registered local point lights, and active local-light group names;
- drawing-buffer dimensions;
- effective renderer pixel ratio and profile render scale;
- resident textures and geometries;
- compiled shader programs;
- current quality profile and player state.

Renderer statistics span the complete composer frame. `renderer.info.autoReset` is disabled and explicitly reset immediately before each render, preventing the overlay from reporting only the final fullscreen pass.

## Targets

- Default desktop target: stable 60 FPS on Apple Silicon at common laptop viewport sizes.
- High-quality fallback floor: documented 30 FPS without any simulation slowdown.
- Four-second walking-distance variance: no more than 5% across 30, 60, and a useful lower test rate.
- Normal active local-light count: no more than the selected profile's 2/4/5 budget.
- Profile and art-direction changes must be compared using repeatable development views.
