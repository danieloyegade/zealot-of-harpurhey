# Gameplay Sluggishness Diagnosis

Date: 10 September 2026

## Executive conclusion

The game feels extremely slow because two defects reinforce each other:

1. The current scene is GPU-bound, primarily because it sends **45 local dynamic lights** through Three.js's forward renderer while drawing hundreds of separate objects. Bloom and the high Retina drawing-buffer resolution add further GPU cost.
2. Whenever rendering drops below 20 FPS, the game loop deliberately discards elapsed time by capping `deltaTime` at 50 ms. Movement, acceleration, camera follow, pickup animation, and the FPS counter all receive this shortened time. The result is not merely choppy rendering: **the simulation literally runs in slow motion**.

On the Apple M1 test system at a 1440 × 900 CSS viewport and device-pixel ratio 2, the game rendered at 4.43 FPS but reported 20 FPS. A five-second walk covered only 2.40 metres, an effective speed of 0.48 m/s instead of the configured 2.4 m/s.

The dominant causal chain is therefore:

> Too many dynamic lights and expensive pixel processing → low frame rate → elapsed-time cap → slow-motion gameplay → misleading FPS display hides the extent of the problem.

The movement and collision code itself is inexpensive. Tuning the walking-speed constant alone would conceal the symptom on one machine and leave both the rendering problem and frame-rate-dependent gameplay intact.

## Scope and method

This diagnosis covers the current working tree and is diagnostic only; no implementation code was changed.

The investigation used:

- static inspection of the game loop, player controller, camera controller, world construction, material policy, and post-processing pipeline;
- a successful production build (`npm run build`);
- live Chrome instrumentation of animation-frame intervals, WebGL draw calls, scene contents, and controlled feature-removal tests;
- timed keyboard-input tests that compared real elapsed time with player displacement.

Test environment: Chrome 152, WebGL 2 via ANGLE Metal on Apple M1. The browser was headless, so the absolute frame-rate numbers should not be treated as a cross-device benchmark. The controlled comparisons use the same browser, scene, camera, and viewport, and are strong evidence about relative cost and causality.

## Measured results

### Rendering experiments

All feature-removal comparisons below used a 1280 × 720 CSS viewport, DPR 1, and the normal 0.72 internal render scale (approximately a 922 × 518 drawing buffer). Measurements were taken after warm-up.

| Configuration | Measured FPS | Median frame | 95th-percentile frame | Change from baseline |
| --- | ---: | ---: | ---: | ---: |
| Normal scene | 15.87 | 66.6 ms | 83.4 ms | — |
| Bloom disabled | 19.41 | 50.0 ms | 66.7 ms | +22% FPS |
| All 29 point lights and 16 spotlights hidden | 60.00 | 16.7 ms | 16.8 ms | +278% FPS |

Removing local lights restored a locked 60 FPS even while the rest of the world and post-processing remained enabled. This identifies local dynamic lighting as the principal sustained bottleneck. Bloom is a meaningful secondary cost.

### Resolution and simulation-speed experiments

| CSS viewport / DPR | Drawing buffer | Observed result | Timed walking result |
| --- | ---: | --- | --- |
| 640 × 360 / 1 | 461 × 259 | Debug display 26–30 FPS | 9.23 m in 4 s (2.31 m/s) |
| 1280 × 720 / 1 | 922 × 518 | Debug display stuck at 20 FPS under load | 4.68 m in 4 s (1.17 m/s) |
| 1440 × 900 / 2 | 2073 × 1296 | 4.43 measured FPS; debug display said 20 FPS | 2.40 m in 5 s (0.48 m/s) |

The low-resolution result is close to the intended walking rate after allowing for acceleration. Increasing render load lowers distance travelled per real second, proving that gameplay speed currently depends on rendering performance.

### Scene complexity at the measured start view

Live scene inspection found:

- 834 total scene objects;
- 685 meshes;
- 685 distinct geometry instances;
- 253 distinct materials;
- 103 textures resident according to the renderer (114 texture objects referenced by scene materials);
- 47 lights in total: 29 point, 16 spot, one hemisphere, and one directional;
- 90 transparent mesh/material uses, plus 26 development-label sprites;
- approximately 468 WebGL draw calls per displayed frame at the start view;
- 27 compiled WebGL programs.

The runtime asset directory is only about 5.5 MB compressed on disk, so download size is not the cause of sustained sluggishness. Texture upload and shader compilation can contribute to startup hitches, but the repeatable steady-state tests identify rendering and time handling as the main problem.

## Findings

### P0 — The frame delta cap turns low FPS into slow-motion gameplay

`main.ts` computes:

```ts
const deltaTime = Math.min(timer.getDelta(), 0.05);
```

Every gameplay system then receives that capped value. At 60 FPS the cap is inactive. Below 20 FPS, each rendered frame advances the simulation by no more than 50 ms, regardless of how much real time passed.

The effective simulation rate below 20 FPS is approximately:

```text
simulation seconds per real second = actual FPS × 0.05
```

Examples:

- 15 FPS advances at 75% speed;
- 10 FPS advances at 50% speed;
- 4.43 FPS advances at about 22% speed.

This exactly matches the observed high-DPR walking result. The cap was probably intended to prevent a large single collision step after a stall, but applying it to the entire simulation silently throws time away.

The debug overlay has the same defect. It derives FPS from the capped `deltaTime`, so it cannot reliably report less than 20 FPS. A machine rendering at 4 FPS can therefore be shown as running at 20 FPS.

### P0 — Forty-five local dynamic lights overwhelm forward shading

The world creates a point light for nearly every storefront, additional point lights across the Dreams building and pickup, and 16 spotlights for streetlights. The code already models much of this lighting with emissive materials, painted pools, translucent cones, and reflection patches, but also layers real dynamic lights on top.

Three.js's normal forward material path evaluates the active light arrays while shading the affected surfaces. Light distance limits do not provide the same benefit as selecting a small per-object light list: a large global light count still increases shader work and shader complexity. This becomes especially expensive across the many `MeshStandardMaterial` objects and millions of Retina-resolution pixels.

The controlled result—15.87 FPS normally versus 60 FPS with the 45 local lights hidden—shows that this is the largest rendering issue by a wide margin.

### P1 — Retina resolution and full-screen effects amplify the lighting cost

The drawing-buffer pixel ratio is:

```text
min(devicePixelRatio, 2) × 0.72
```

On a DPR-2 display, this is 1.44 physical pixels per CSS pixel. A 1440 × 900 window therefore renders approximately 2073 × 1296, or 2.69 million pixels, before the composer performs its additional full-screen work.

The pipeline includes a scene render, multi-level Unreal bloom, an output pass, and a final custom grading pass containing exposure, saturation, contrast, animated grain, vignette, ordered dithering, and quantisation. Disabling bloom alone improved the controlled result by 22%, so it is material but not the root cause.

### P1 — The world is fragmented into too many independent render resources

The scene uses a separate geometry instance for every mesh and produces about 468 visible draw calls at the initial camera position. Many boxes, lamps, windows, benches, façade details, reflections, and street props could share geometry or be instanced. There are also 253 material instances and more than 100 texture objects, partly because material variants use differing repeat values and other options.

This fragmentation adds CPU submission overhead, material switches, shader variants, memory use, and transparent overdraw. It is secondary to the light count in the current measurements, but it reduces headroom and makes every additional visual feature more expensive.

### P2 — Intentional smoothing and traversal speed add perceived latency

With rendering healthy, the configured movement still has a deliberately weighty feel:

- walking speed is 2.4 m/s and running speed is 4.5 m/s;
- movement responsiveness 8 reaches roughly 90% of target velocity in 0.29 seconds;
- camera follow responsiveness 7 closes roughly 90% of its positional error in 0.33 seconds;
- the playable bounds span 128 × 124 metres, so walking across the full map would take more than 50 seconds even at uninterrupted full speed.

Player acceleration and camera lag stack visually, especially when starting or changing direction. These values can make the game feel heavy, but they do not explain the extreme slowdown: the low-resolution input test reached the configured speed, while the same code ran far slower under GPU load.

## Recommended remediation order

### 1. Restore simulation correctness and honest telemetry

- Keep an uncapped real-frame delta for telemetry.
- Use a fixed-timestep accumulator for gameplay, with bounded catch-up work, or substep movement/collision while preserving the full elapsed time.
- Treat very large resume/background gaps separately instead of truncating every slow frame.
- Calculate FPS from raw `requestAnimationFrame` timestamps or an uncapped real delta.

This will stop low rendering performance from changing world speed. It will not make 4 FPS feel responsive, so rendering work remains equally urgent.

### 2. Establish a strict dynamic-light budget

- Remove real point lights from routine storefronts and retain their existing emissive/fake-pool treatment.
- Remove real spotlights from most or all streetlights; their cones, pools, and reflection meshes already convey the intended look.
- Keep only a very small set of hero lights, or select the nearest few lights dynamically if genuine illumination is essential.
- Start with a target of no more than roughly 4–8 simultaneously active local lights, then profile rather than choosing the final budget by eye.

For this stylised prototype, reducing real lights is a much smaller and safer intervention than adopting a deferred or clustered renderer.

### 3. Add quality and resolution controls

- Provide explicit low/medium/high profiles for render scale, DPR ceiling, bloom, and local-light count.
- Consider a default DPR ceiling of 1–1.5 on the current content, subject to visual review.
- Optionally adapt internal scale using sustained frame-time measurements with hysteresis.
- Re-profile bloom after the light reduction; disable or simplify it on lower profiles.

### 4. Reduce draw submissions and transparent overdraw

- Share primitive geometries instead of constructing one geometry per box or prop.
- Instance repeated streetlights, tower windows, trees, benches, bike stands, road markings, and similar props.
- Merge static meshes where material and culling boundaries make that sensible.
- Consolidate material/texture variants and avoid duplicate texture objects for the same image where possible.
- Review the 90 transparent surfaces, especially overlapping additive cones and reflection patches.

### 5. Tune feel only after performance is stable

Once movement is invariant across frame rates, playtest somewhat faster walking, stronger acceleration response, and faster camera follow. Also make the run control visible outside the development documentation. Do not compensate for slow simulation by multiplying the current speed constants.

## Suggested acceptance criteria

- A timed four-second walk covers the same distance within 5% at 30, 60, and 120 FPS and across supported resolutions.
- The FPS overlay matches raw animation-frame measurements and can display values below 20.
- The Apple M1 test scene sustains 60 FPS at the agreed default desktop quality, or a documented minimum of 30 FPS at high quality, without simulation slowdown.
- Median and 95th-percentile frame times are recorded separately; brief loading/compilation hitches do not contaminate steady-state results.
- A renderer diagnostic displays draw calls, triangles, active local lights, drawing-buffer size, and texture/geometry counts so regressions are visible during development.

## Bottom line

The report confirms a real technical defect, not merely subjective pacing. The world is expensive to shade, particularly on a Retina buffer, and the game loop converts that rendering cost directly into slow-motion movement. Fixing time handling and drastically reducing simultaneously active dynamic lights should produce the largest immediate improvement; resource batching, quality scaling, and feel tuning should follow.
