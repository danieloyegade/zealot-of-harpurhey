# Engine Stabilisation Report — Performance Phase 1

Date: 10 September 2026

## Outcome

Phase 1 meets its primary objective. Simulation speed is now independent of ordinary rendering frame rate, the overlay reports real frame timing, local dynamic lighting is within a strict 2–5 light profile budget, and the same Apple M1 test system improved from 15.10 FPS to 60 FPS at the comparable 1280 × 720/DPR-1 condition.

## 1–8. Baseline

The baseline used Chrome 152, WebGL 2 through ANGLE Metal on Apple M1, a 1280 × 720 CSS viewport, DPR 1, and the former 0.72 internal scale.

1. Baseline FPS: **15.10**.
2. Baseline median frame time: **66.6 ms**.
3. Baseline 95th-percentile frame time: **100.0 ms**.
4. Baseline walking distance in a real four-second test: **7.82 m**. The configured full-speed expectation after acceleration is approximately 9.3 m; lost frame time caused the shortfall.
5. Baseline PointLight count: **29 active**.
6. Baseline SpotLight count: **16 active**.
7. Baseline draw calls: **468** at the player-start view. Instrumented WebGL triangle submissions were approximately **6,574**.
8. Baseline drawing buffer: **921 × 518**.

Additional baseline counters were 103 resident textures, 398 resident geometries, and 27 shader programs. Live scene inspection found 685 meshes, 685 distinct scene geometry instances, and 253 materials.

The earlier Retina-style baseline at 1440 × 900/DPR 2 used a 2073 × 1296 buffer and measured 4.43 FPS, with approximately 233 ms median/p95 frames. Its debug overlay incorrectly said 20 FPS, and a five-second walk covered only 2.40 m.

## 9–13. Time architecture and telemetry

9. New timestep architecture: raw animation-frame delta enters a `FixedStepClock` accumulator. Player movement/collision and world animation update in fixed steps; rendering occurs once afterward. Camera smoothing consumes one ordinary raw frame delta per render.
10. Fixed timestep: **1/60 second**.
11. Catch-up strategy: **maximum 16 substeps**, enough to preserve all ordinary elapsed time up to the 250 ms extreme-gap threshold, including a small carried accumulator remainder.
12. Background-tab handling: Three.js `Timer` remains connected to document visibility, and the fixed-step accumulator explicitly resets on every visibility transition. Any individual delta above 250 ms is classified as an extreme gap and is not replayed.
13. FPS telemetry: FPS and frame milliseconds use uncapped real frame time. Renderer statistics are reset before the complete composer frame and read afterward. The overlay correctly displayed 14 FPS, 9 FPS, and 5 FPS in deliberate low-rate tests.

## 14–17. Lighting

14. Final PointLight count: **5 total**, with **4 active on the default MEDIUM profile**.
15. Final SpotLight count: **0**.
16. Maximum simultaneously enabled local dynamic lights: **2 LOW / 4 MEDIUM / 5 HIGH**. Five is the absolute scene maximum.
17. Lights converted to fake/emissive treatment: 16 streetlight spotlights; routine storefront point lights; six Dreams fixture lights and its panel light; three lights per bus shelter; the florist standalone light; and the development pickup light. Streetlight pools/cones/reflections, storefront emissive identity, Dreams tubes/sign/cladding, bus-shelter photographic glow, the pickup halo/pool, and coloured façade emission remain.

## 18–23. Quality configuration

18. Default render scale: **0.72**.
19. Default DPR cap: **1.25**.
20. Default bloom: **enabled**, strength 0.30.
21. LOW: scale 0.65, DPR cap 1.0, bloom off, two active local lights.
22. MEDIUM: scale 0.72, DPR cap 1.25, bloom on at 0.30, four active local lights.
23. HIGH: scale 0.80, DPR cap 1.5, bloom on at 0.34, five active local lights.

At a 1280 × 720 CSS viewport and DPR 2, measured profile results were:

| Profile | Drawing buffer | Measured FPS | Median / p95 | Draw calls | Active lights |
| --- | ---: | ---: | ---: | ---: | ---: |
| LOW | 832 × 468 | 60.00 | 16.7 / 16.7 ms | 455 | 2 |
| MEDIUM | 1152 × 647 | 60.00 | 16.7 / 16.8 ms | 468 | 4 |
| HIGH | 1536 × 864 | 59.75 | 16.7 / 16.7 ms | 468 | 5 |

LOW looked intentionally softer and lost bloom, but remained readable and visually coherent. HIGH remained within the 60 FPS target on the test hardware.

## 24–32. Final performance and movement

24. Final default FPS at 1280 × 720/DPR 1: **60.00**.
25. Final median frame time: **16.7 ms**.
26. Final 95th-percentile frame time: **16.8 ms**.
27. Final four-second walking distance: **9.36 m** at the comparable default test. A 1440 × 900/DPR-2 default test covered 9.32 m.
28. Walking-distance variance in deliberate rate tests: 9.52 m at 60 FPS, 9.60 m near 30 FPS, 9.60 m at 14–15 FPS, 9.40 m at 9–10 FPS, and 9.60 m at 5 FPS. The full range is **2.1%**, within the required 5%.
29. Final draw calls: **468** at the unchanged player-start view; the count is unchanged because Phase 1 shared resources but did not merge independently transformed scene objects.
30. Final resident texture count: **103** at the player-start view.
31. Final resident geometry count: **199**, down from 398. Scene-wide distinct geometry references fell from 685 to 338.
32. Final drawing buffer at 1280 × 720/DPR 1: **921 × 518**. At the representative 1440 × 900/DPR-2 default condition it is **1295 × 809**, down from 2073 × 1296.

The representative 1440 × 900/DPR-2 default test also held 60 FPS with 16.7 ms median and 16.8 ms p95 frames. No console errors or warnings were recorded during the final two-condition benchmark.

## 33–35. Visual comparison and remaining work

33. Before/after comparisons were captured for player start, Dreams, bus shelter, west street, and a streetlight-pool view under `renders/performance-phase-1/`. The cobalt sky, deep dark intervals, Dreams' cool identity, Renae magenta, bus-shelter green/white/pink imagery, amber pools, reflection patches, and visible cones remain.
34. Art-direction compromises: real lights no longer spread soft illumination from every shop and lamp onto nearby standard materials. West street is slightly darker and more graphic. Dreams uses stronger emissive frontage plus one restrained hero light rather than seven overlapping point lights. This is a visible but modest shift toward the intended Dreamcast-like fake-light language.
35. Remaining bottlenecks: approximately 468 start-view draw calls, transparent/additive overdraw, more than 100 resident textures, and the multi-pass bloom/grade pipeline. Repeated streetlight parts, tower windows, trees, benches, bollards, and markings remain candidates for later measured instancing. The production JavaScript chunk also remains approximately 673 kB minified and triggers Vite's size advisory.

## 36–42. Verification and handoff

36. Build result: **pass** (`npm run build`). TypeScript and Vite complete successfully; Vite reports only its existing chunk-size advisory.
37. Browser-console result: **pass**, with no captured errors or warnings in the final default-quality DPR-1 and Retina-style tests.
38. Files created: `src/core/FixedStepClock.ts`, `docs/PERFORMANCE.md`, this report, and before/after performance screenshots (including the new streetlight-pool comparison).
39. Files modified by Phase 1: `src/main.ts`, `src/rendering/createPostProcessing.ts`, `src/rendering/visualStyle.ts`, `src/rendering/worldGraphics.ts`, `src/ui/DebugOverlay.ts`, `src/world/createDreamsBuilding.ts`, `src/world/createWorld.ts`, and `docs/TECHNICAL.md`.
40. Git status: the repository was already dirty before Phase 1. No commit or push was performed. The final working-tree status is recorded in the task handoff.
41. Suggested commit message: `perf: stabilise simulation timing and reduce dynamic lighting`.
42. Recommended next task: a tightly scoped draw-call pass that instances repeated streetlight and tower-window geometry, with the same five-view visual comparison and renderer counters. Do not begin new gameplay or environment content until that measured pass is accepted.

## Required answers

**A. Is simulation speed now independent of rendering FPS?** Yes, for ordinary visible-frame deltas through the tested 9–60 FPS range; measured walking variance is 2.1%.

**B. Does the FPS display now report real rendering performance?** Yes. It uses raw frame time and successfully reported values below 20 FPS.

**C. Has the local dynamic-light count been reduced from 45 to a safe budget?** Yes. There are five candidates total, with 2/4/5 enabled by LOW/MEDIUM/HIGH and no spotlights.

**D. Is the game substantially faster on the same hardware?** Yes. The comparable default test improved from 15.10 to 60 FPS, and the Retina-style default test improved from 4.43 to 60 FPS while using a much smaller buffer.

**E. Does the game still visually feel like Zealot of Harperhey?** Yes. The core palette, photographic/emissive landmarks, pools, cones, reflections, deep darkness, and night-sky treatment remain. The principal difference is slightly more graphic and localised illumination where broad real-time spill was removed.
