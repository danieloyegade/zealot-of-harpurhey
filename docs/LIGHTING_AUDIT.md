# Lighting Evaluation — Zealot of Harperhey

Date: 13 September 2026

Scope: current `main` working tree at `4562e6d`, including the uncommitted AgX, layered-road, pavement, Greek Gyros relocation, Advanced Photo, bus-shelter texture, and camera work present during the audit.

## Implementation follow-up — 14 September 2026

The first lighting pass has now implemented the audit's safest recommendations without changing global exposure, fog, moonlight, hemisphere light or the display grade:

- added `LocalLightRegistry` so every runtime local point light shares the 2/4/5 quality budget, including Coral's asset-loaded pair;
- grouped multi-light fixtures atomically, with short fade in/out windows and development diagnostics that list active light groups;
- replaced the dead public-streetlight values with one budgeted moving proxy that only contributes when the player is inside a pool;
- added a restrained player material visibility floor by lifting indirect diffuse response only on the dark denim/leather/hair materials;
- added a Greek Gyros counter light from the authored GLB anchor and a placeholder emissive treatment for fixture lenses;
- added a temporary Come Through Lab threshold cue for the entrance/drop-box ensemble, pending a final authored luminaire in the asset;
- preserved the nocturnal negative space by leaving unlit intervals and the global grade untouched.

Still open after this pass: final post-grade/quantisation review, authored Hive and car-park threshold lighting, final Greek/CTL material-light integration, and repeatable capture comparison once those asset passes land.

## Executive answer

Some important areas are too dark, but the game as a whole is **not** too dark.

The darkness between lights is one of the strongest and most specific parts of the work. It gives the streets negative space, lets ordinary objects become isolated images, and supports the intended nocturnal Manchester rather than a uniformly legible videogame night. Raising global exposure, hemisphere intensity, or moonlight would weaken that. It would flatten the city into a blue wash, reduce the authority of the practical lights, and make the night feel decorative rather than structural.

The problem is **where the available visibility is assigned**. The current scene often makes roads, pale blockout walls, labels, or additive ground graphics easier to read than the delivery rider, a doorway, or a delivery object. In several places an apparent pool of light does not illuminate the player or nearby geometry at all. The game therefore has enough overall light, but not always enough authored hierarchy.

The clearest priorities are:

1. Keep the player a readable near-black figure everywhere, without turning him blue or adding a visible game-like halo.
2. Make the streetlight pools affect the figure and immediately adjacent materials, while retaining black intervals between them.
3. Light functional thresholds—especially the Come Through Lab door/drop box and Greek Gyros serving front—rather than broad façades.
4. Replace the current nearest-light selection with a range-aware, grouped, stable selector.
5. Bring Coral's two permanent point lights inside the shared budget and diagnostics.
6. Reassess the shadow-crushing part of the display grade only after the local hierarchy is fixed.

The guiding sentence is: **do not brighten the night; make the night more selective.**

## Evidence and confidence

This evaluation combines:

- the current renderer, material, light-selection, world-layout, and asset-integration source;
- the current asset briefs and the [creative constitution](./creative-constitution.md);
- checked-in visual comparisons under `renders/art-direction/`, `renders/hero-street-pass/`, `renders/performance-phase-1/`, and `references/screenshots/V3/`;
- runtime inspection of the current player asset and representative world views during the audit;
- the same-day AgX calibration results recorded in `SYNC.md`.

The worktree changed during the audit: AgX tone mapping, layered roads and pavements, the Greek Gyros move, Advanced Photo integration, and a new bus-shelter material pass arrived after the first runtime captures. System and spatial conclusions below use the latest source. Exact appearance of those same-day additions should receive one clean, repeatable screenshot pass before lighting values are committed. Confidence is high on light coverage, budget, material response, and the identified spatial faults; it is moderate on fine final colour judgement for the newest assets.

Many buildings are explicitly geometry-stage assets. Their flatness or darkness is not a modelling failure. It does mean the present playable build cannot yet rely on their final textures to supply the missing lighting information.

## The correct standard for darkness

The creative constitution does not ask for generic moodiness. It describes municipal light as theatre: a lamp turns a waiting person into a performer; night removes explanatory detail; and the figure should be discovered inside a pool of artificial light. It also explicitly says not to fear blackness. The useful distinction is therefore not bright versus dark, but **intentional concealment versus accidental loss of meaning**.

Darkness is working when it:

- removes irrelevant upper-floor and background detail;
- makes the sky, silhouette, window, sign, shelter, tree, or waiting figure feel isolated;
- creates uncertain distance while preserving the broad route;
- separates one practical-light island from the next;
- makes wet fragments and reflective objects appear briefly rather than continuously;
- allows closed or inactive buildings to remain genuinely closed and inactive.

Darkness is failing when it:

- hides the player's outline against the surface immediately behind him;
- obscures a kerb, path direction, obstacle, or turn inside normal reaction distance;
- makes a delivery door, drop box, serving counter, or entrance unreadable without UI annotation;
- removes the one recognition feature that distinguishes a destination;
- presents a visible lamp pool but leaves the person standing in it unchanged;
- makes a geometry-stage asset look accidentally unfinished rather than deliberately unilluminated;
- causes light sources to pop on and off as the player crosses an invisible selection boundary.

The intended result should retain substantial true or near-black space in most frames. The player, traversal plane, and current destination do not all need full detail, but each needs a deliberate readable cue.

## Current lighting system

| Layer | Current implementation | Assessment |
| --- | --- | --- |
| Sky and distance | Cobalt sky `#071c5a`; near-black blue horizon; fog `#07133b` from 44 m to 108 m | Strong identity. The fog makes distance dissolve into the night and should remain. |
| Global surface light | Hemisphere light at 0.72 plus cool directional moon at 1.28 | Already generous enough for broad massing. Increasing either would flatten local contrast. |
| Tone mapping | AgX at linear exposure 1.70 by default; calibrated against the earlier uncurved midtones | Sensible current baseline. Do not use exposure to solve local lighting faults. |
| Display grade | Saturation 1.12, contrast 1.05, 32-step RGB quantisation, shadow-weighted grain 0.042, vignette 0.20 | Visually assertive. The toe treatment can destroy the last small differences in dark materials. Review after local fixes. |
| Streetlights | 20 poles with bright basic-material heads, additive cones, painted pools, and reflection strips | They create convincing graphic light *images*, but cast no light on player or standard materials. |
| Hero-light selector | 15 point-light candidates; nearest 2/4/5 enabled on LOW/MEDIUM/HIGH | Budgeted, but raw distance is not the same as useful contribution. It frequently enables lights that are out of range. |
| Coral | Two additional permanent point lights created when the GLBs load | Visually useful, but outside the selector and omitted from the overlay. Actual point-light count exceeds the stated budget. |
| Shadows | Disabled globally; GLBs still set `castShadow` and `receiveShadow` | Appropriate for current performance, but depth must come from baked AO, contact treatment, texture, and directed light rather than shadow maps. |
| Emissive lighting | Strong at Dreams, Coral, bus shelters, Cass Art, Real Camera and Advanced Photo; absent on several geometry assets | This is the right performance strategy. Coverage and hierarchy need completing per location. |

There are also unused `streetLightIntensity` and `streetLightDistance` values in `visualStyle.ts`. They should not be revived as 20 simultaneous real lights. They are evidence of a partially removed system and should either be repurposed for a tightly budgeted public-light proxy or removed to avoid misleading future work.

## Principal findings

### 1. The player is the most important underlit object

The current rigged player is intentionally difficult material: raw-indigo denim uses base colour around `(0.018, 0.0215, 0.0345)`, shadow denim around `(0.0128, 0.0152, 0.025)`, and most black leather around `0.011–0.015`. That is artistically correct—the clothing should read near-black, never bright blue—but it leaves almost no display-level separation under global light alone.

At the default start `(0, 3.5)`, the four closest medium-profile hero candidates are approximately:

| Candidate | 3D distance from player | Light range | Useful contribution |
| --- | ---: | ---: | --- |
| Bus Stop A | 17.1 m | 8 m | None |
| Dreams | 30.2 m | 10 m | None |
| Cass Art window | 34.7 m | 7 m | None |
| Florist | 35.0 m | 9 m | None |

The selector still enables all four. The player is therefore lit only by the cool global pair even though the debug overlay reports a full four-light budget. Against dark grass, road, jacket, bag, and hair, much of the character collapses into one shape. The silver shoes and metal armour can catch highlights, but the torso, head, bag, and leg separation are unreliable.

This is not an argument for changing the character palette. The costume's darkness is conceptually important. It is an argument for a controlled **character visibility floor**: a restrained rim, soft key, or material response that preserves black while separating the figure from whatever surface happens to sit behind him.

### 2. Streetlights depict illumination without performing it

Every public streetlight has a luminous head, visible cone, circular pool, and two broken reflection strips. Those meshes are basic/additive graphics. They do not illuminate the rider, building, kerb, trolley, tree, or the new low-roughness road decals.

This is the most important conceptual mismatch in the current lighting. The creative constitution says the streetlight selects the figure. At present the graphic on the ground is selected, but the figure is not. A player can cross an amber or cold-white pool and remain almost exactly the same cool global silhouette.

The fix is not to restore 20 spotlights. A single nearby public-light candidate, or a character-only lamp response, can make the nearest pool physically consequential while preserving the 2/4/5 budget and the darkness between pools.

### 3. Light is aimed at architecture when gameplay needs it at thresholds

Come Through Lab has two cold point-light candidates at its parapet corners, each at about `y = 6.9 m` with a 7 m range. The south light is roughly 6.9 m from the ground-level entrance and about 7.0 m from the independent drop box. The door is consequently at the extreme attenuation tail and the drop box is at or just outside the cutoff. Even when the correct light wins the selector, almost all useful energy is spent above the action plane.

This is a precise example of the wrong hierarchy: the upper corner receives an architectural wash while the 24-hour delivery mechanism—the thing the player must understand—remains obscure. Keep one graphic upper accent if the façade needs it, but move the real contribution down to the entrance/drop-box ensemble and derive it from the authored anchors.

### 4. Greek Gyros is not ready for its intended night role

The kiosk's own brief calls for a bright white interior, illuminated signage, strong spill through the open front, and a reflective metal counter. Four light anchors and fixture meshes already exist in the GLB. The runtime currently clears every emissive material and does not read those anchors.

At its new park-east position `(20.6, 10.5)`, the serving front has no hero light within range. A fake cold streetlight sits nearby, but cannot illuminate the kiosk or the player. The pale shell may remain geometrically visible under moonlight; the significant information—the open counter, interior depth, service ritual, and fascia—is what stays dark. This is definitively underlit relative to the asset's authored intent.

The kiosk should become a compact white/cool commercial island, not a broad orange flood and not cyberpunk neon. One real counter/interior light, emissive fixture faces, and a restrained spill card or pool are enough.

### 5. The nearest-light selector spends budget on lights that cannot help

The selector sorts all candidate positions by raw 3D distance and enables the first N. It does not test the light's attenuation range, compare distance as a fraction of range, reserve roles, group lights by location, or add hysteresis.

Consequences:

- At the player start, all four enabled medium lights are out of range.
- At Greek Gyros, all four are out of range.
- At Village Books, all four are out of range.
- At The Hive entrance and the car park, all four are out of range.
- At the centre of South Road `(0, 59.5)`, the four closest candidates are roughly 12–15 m away but have only 6–10 m ranges; all are out of range.
- Cass Art, Real Camera, and Advanced Photo can consume most of the budget with several lights belonging to one asset.
- LOW can light only two members of a three-light shop group, producing unintended left/right asymmetry.
- Candidate visibility changes instantly when rankings cross, creating a risk of visible popping.
- High-mounted lights are penalised by vertical distance when chosen, yet their short ranges can still leave the ground they are meant to light at the cutoff.

This is both an artistic and performance problem. Invisible contribution still expands the active light array used by standard-material shaders. A range-aware selector can often enable fewer lights while making the scene *more* readable.

### 6. Coral bypasses the stated light ceiling

The selector currently owns 15 candidates. Separately, successful Coral loading adds two always-visible point lights directly to the root. They are not returned by `addHeroLocalLights`, not switched by quality, and not included by `getLightingStats()`.

After Coral loads, the effective visible point-light totals can therefore be:

| Profile | Overlay/selector reports | Effective visible total |
| --- | ---: | ---: |
| LOW | 2 | 4 |
| MEDIUM | 4 | 6 |
| HIGH | 5 | 7 |

The renderer pays for those Coral lights throughout the scene, even where distance attenuation makes their visible contribution zero. `docs/PERFORMANCE.md`, `docs/ENGINE_STABILISATION_REPORT.md`, and the debug overlay consequently describe an older lighting architecture. Coral's appearance should be preserved, but its lights must join the same registry or be converted to emissive/fake spill.

### 7. The display grade can erase exactly the detail the night needs

The grade's contrast operation is `(colour - 0.5) × 1.05 + 0.5`, which subtracts 0.025 from values near black. It then quantises each RGB channel in steps of `1/32`, approximately 0.03125. Dark values below the first surviving step become black. Shadow-weighted grain can vary by as much as about ±0.021 before that quantisation, so tiny material differences may turn into temporal bin changes rather than stable form.

This matters because the player's dominant albedos, closed windows, dark foliage, and soot materials all live in that bottom region. AgX has improved highlight rolloff and was calibrated to retain midtone brightness, but it cannot protect detail removed afterward by the display grade.

Do not immediately remove the grade: it contributes to the existing look. First fix local light hierarchy. Then compare:

- current 32-step RGB quantisation;
- 64 steps;
- no quantisation;
- luminance-aware quantisation that preserves a smoother toe;
- grain after quantisation at a lower amplitude, rather than before it;
- a contrast curve with a protected black toe rather than a linear negative offset.

The project's current direction has moved away from the old Dreamcast/PS2 target toward uncanny photographic construction. The remaining 32-step per-channel treatment should therefore have to justify itself visually; it should not be protected merely because it is already present.

### 8. The global night, fog, and best hero locations are working

Several elements should be protected:

- The cobalt-to-black sky and blue fog produce a distinct, authored night rather than neutral darkness.
- Dreams successfully combines photographic information, restrained façade emission, tube lights, one cool hero point, and broken road reflection.
- The bus shelter remains the clearest benchmark: luminous imagery, dirty reflective glass, recognisable construction, and a real local point make an ordinary municipal object theatrical.
- Coral has a strong hierarchy of cool shop light, warmer windows, terminals, sign, and road spill; its problem is budget ownership, not lack of visual direction.
- Cass Art, Real Camera, and Advanced Photo use the correct broad strategy: practical fixtures and interior materials carry most of the image, with a small number of candidate lights supplying local response.
- The fog and unlit upper masses preserve scale and uncertainty. They should not be filled merely to display modelling work.

### 9. Lighting documentation and diagnostics have drifted

The current performance policy says there are eight selector candidates and a five-light absolute maximum. The current working tree has 15 selector candidates plus Coral's two unmanaged points. The public-illumination section of `docs/VISUAL_LANGUAGE.md` still says each streetlight includes a spotlight, although none exists. The Greek Gyros asset note first says its anchors are read by `createWorld.ts`, then correctly says later that nothing reads them; current source confirms the latter.

This is more than editorial housekeeping. Incorrect documentation can lead a future lighting pass to budget against the wrong scene, assume a painted pool affects geometry, or duplicate a supposedly integrated anchor system. Update those documents and make the debug overlay derive its count from the central registry after the architecture is corrected.

## Area-by-area assessment

| Area | Is it too dark? | What is working | What should change |
| --- | --- | --- | --- |
| Player start / central park | **Player: yes. World: mostly no.** | Paths, fountain mass, skyline, and distant light islands establish the night. | Give the player a visibility floor. Reserve a real response for a nearby public lamp. Do not raise park-wide ambient. |
| Park interior | **Selective risk.** | Dark grass and trees provide valuable negative space. Wet paths can catch global highlights. | Verify path turns, fountain edge, trees across paths, and future playground at LOW. Add tiny reflected or baked cues only where traversal fails. |
| Greek Gyros / east park edge | **Yes at the functional front.** | Strong silhouette and a useful future contrast with The Hive. | Read the four GLB light anchors; make fixture faces emissive; use one real white/cool counter light and restrained spill. Recheck after its relocation. |
| Bus Stop A | **No, but spatially wrong.** | It is the game's best public-illumination tableau and already has a local point. | The magenta and green legacy spill patches remain near old x positions around `-8` to `-10`, while the shelter is now at `x = 0`. Re-anchor or remove them; derive all shelter spill from the marker transform. |
| Bus Stop B / north exit | **Probably acceptable; verify LOW.** | The isolated shelter and estate-window backdrop can form a strong lonely endpoint. | Confirm the player remains legible at the edge of the 8 m light. Do not duplicate every Bus Stop A colour patch automatically; asymmetry can be valuable. |
| Dreams approach | **No.** | Cool photographic façade, tubes, modest point light, and broken wet-road spill produce a clear destination without broad floodlighting. | Use as the benchmark for a finished commercial façade. Recheck practical colour after AgX; avoid global saturation changes. |
| Cass Art | **No near the frontage; system is over-provisioned.** | Warm interior against the cool street is effective and distinct. | Reduce its three real candidates to one key plus at most one fill, with fixtures/interior emission carrying the rest. Group them so LOW does not make arbitrary asymmetry. |
| Come Through Lab | **Yes at the door and drop box.** | Dark masonry and a cold upper silhouette suit the building. | Move the useful real light to the authored entrance/drop-box anchors at roughly head/door height. Keep upper-corner treatment emissive or fake. Do not extend a broad range across the whole façade. |
| Village Books | **Potentially, depending on activity.** | It can validly be one closed, dark frontage in the west sequence. | Keep it dark if inactive, but give glass, sign, or metal enough stable response to identify the shop. If it becomes a destination, add a small threshold cue only while relevant. |
| Coral / west street | **No visually; yes technically.** | Best-developed combination of cool retail, warm windows, terminals, sign and wet spill. | Preserve the image while registering or baking out the two unmanaged point lights. Review the older additive patches against the new layered road so they do not read as confetti. |
| Florist and Renee | **Generally functional near their hero points.** | Their sodium and magenta anchors punctuate the north frontage. | Finish source-led practical/emissive identity with texture passes. Keep magenta specific to Renee rather than spreading it as generic nightlife colour. |
| MCR1 and Gulliver's | **Under-authored rather than globally too dark.** | Their massing can remain subdued between stronger anchors. | MCR1's historical night frontage calls for emissive signage in its texture stage. Gulliver's needs one modest pub threshold/window/sign cue, not a fully glowing façade. |
| The Hive entrance | **Yes at the action plane; upper building no.** | The large dark institutional mass is effective and should stay dominant. | Give the west entrance or screen a precise cold municipal cue. Let Greek Gyros provide the smaller human/commercial counterpoint across the road. |
| Car park | **Likely too undifferentiated.** | It is an ideal Public Illumination Studies subject and benefits from large black areas. | Author one or two hard pools with broad darkness between them. Light the player and wet asphalt only inside the chosen pool; avoid uniform security lighting. |
| South Road centre | **Player: yes. Route: source-dependent.** | The chain of fake lamp pools and wet road detail can lead the eye between shops. | Stop spending all four candidate slots on out-of-range shop lights. Let the nearest public lamp affect the rider and road locally. |
| Real Camera | **No near the shop.** | Sodium exterior versus cool fluorescent interior is a useful mixed-light situation. | Cap its three candidates as a group; use one exterior key and one interior response on MEDIUM, with fixture emission doing the rest. |
| Advanced Photo | **No near the shop; verify new integration.** | Pale interior and circular arcade fixture already have restrained emission and two candidates. | Prefer one active real candidate at a time unless both demonstrably add form. Keep the arcade ring warm and the interior cooler. |
| Far boundaries and estate backdrop | **No.** | Fog, isolated lit windows, and uncertain exits provide depth without explaining everything. | Guide exits with one repeatable landmark or practical, not brighter fog or a raised black level. |

## Recommended lighting architecture

### A. Add a restrained character visibility floor

The player needs a solution that is independent of nearby hero-light accidents.

Preferred approach:

- Give the player materials a restrained character-specific lighting response: a low diffuse floor plus a soft world- or view-space rim, implemented in the material shader rather than as a visible outline.
- Use a cool-neutral bias from above/behind the camera, just strong enough to split head, shoulders, bag, and legs from the local background.
- Keep the denim's average read near-black. Do not lift its base colour to obvious blue.
- Let metal greaves, gauntlets, hardware, and silver shoes respond more strongly, preserving the costume's existing hierarchy.
- Blend the character-light colour toward a nearby practical source when the player enters a real/fake lamp pool.
- Avoid a uniform outline shader, halo, flashlight cone, or exposure that follows the player visibly.

A simpler fallback is a very low emissive floor on the darkest player materials. It is cheaper but easier to make artificial, and it will not produce the important colour transition under sodium, fluorescent, and cold public light. A separate character render pass with its own light is another option; ordinary Three.js `Layers` alone do not provide per-object selective lighting in the main pass.

### B. Make one nearby public lamp real at a time

Do not restore every streetlight spotlight. Instead:

- Treat the 20 lamp positions as candidates.
- Reserve one local-light slot for the nearest lamp only when the player is within its designed pool radius.
- Use a short-range point or modest cone response that reaches the player, nearby kerb, and wet road without lighting a whole block.
- Keep the existing graphic cone, pool, and reflection geometry as the photographic/compositional layer.
- Score and switch with hysteresis; fade between sources over roughly a few tenths of a second so colour does not pop.
- When no lamp is in range, disable that slot rather than selecting an irrelevant distant light.

A useful budget split to test is:

| Profile | Reserved public-lamp response | Location lights | Total ceiling |
| --- | ---: | ---: | ---: |
| LOW | 1 | 1 | 2 |
| MEDIUM | 1 | up to 3 | 4 |
| HIGH | 1 | up to 4 | 5 |

The preferred character shader/material response does not consume one of these point-light slots. If a separate render pass and actual character light are used instead, that light must be included honestly in diagnostics and performance testing.

### C. Give every functional location a lighting contract

Each active destination should define four possible components, not necessarily four real lights:

1. **Identity** — sign, window, recognisable fixture, or lit architectural fragment visible on approach.
2. **Threshold** — door, counter, gate, or drop-off object visible at player height.
3. **Response** — one real light, when needed, so player and nearby materials share the source.
4. **Trace** — a broken reflection, damp patch, glass response, or adjacent object catching the source.

Inactive locations may intentionally omit threshold and response. This prevents every shop from glowing while ensuring the current destination never disappears into arbitrary black.

### D. Replace raw nearest-N selection with contribution-aware groups

The selector should:

- reject candidates whose target surface/player is outside the attenuation range;
- score normalised distance (`distance / range`) rather than raw distance alone;
- consider horizontal approach and the intended target plane for high-mounted lights;
- group candidates by location and cap the number enabled per group;
- reserve roles, so a public/character source cannot be displaced by three fixtures inside one shop;
- use hysteresis and a short intensity fade to prevent switching pop;
- enable a light only when its source asset has loaded successfully;
- expose active light names, ranges, groups, and actual scene totals in a lighting-debug mode.

This change should improve both performance and appearance. At the start and South Road, the correct environmental count may be zero or one rather than four ineffective shop lights.

### E. Correct the immediate location faults

1. Re-anchor Bus Stop A's magenta and green spill to the current `(0, 20.4)` marker and shelter rotation, or remove those patches if the textured shelter's own ground-contact treatment now replaces them.
2. Move Come Through Lab's meaningful point response from parapet height to the entrance/drop-box ensemble. Use the exported anchors; do not add another hard-coded world coordinate.
3. Wire Greek Gyros' four authored anchors. Start with one real counter/interior light; make the other fixtures emissive or baked unless a second light clearly adds something.
4. Move Coral's two cool points into the central registry, group them as one location, and test whether one real point plus the existing emissive materials and fake spills can reproduce the current look.
5. Cap Cass Art and Real Camera at one key plus one fill on MEDIUM. Let their emissive practicals do most of the work.
6. Add one precise cold entrance cue to The Hive and one or two isolated public pools to the car park during their proper asset/lighting pass.

### F. Recalibrate the post stack after local lighting is correct

Keep AgX as the working baseline for now. Its midtones were calibrated against the old output, and its highlight rolloff solves a real clipping problem. The bus shelter is the deciding colour benchmark because its green/white/pink image is central to the visual identity and AgX currently makes its brightest core paler.

After the local pass, compare post variants at identical camera positions:

- current grade;
- protected-toe contrast;
- 64-level quantisation;
- quantisation off;
- lower grain in the deepest 0–10% of luminance;
- grain after, rather than before, quantisation.

Choose the least destructive treatment that still makes the image feel constructed. Do not compensate for pale highlights with global saturation until the individual emissive colours have been tested.

## Suggested starting values, not final art direction

These ranges are deliberately conservative and use the existing scene's point-light scale:

| Use | Starting range | Starting intensity | Notes |
| --- | ---: | ---: | --- |
| Nearby public-lamp response | 5–7 m | 4–7 | One active near player; decay 2; match the visible pool colour. |
| Come Through Lab threshold | 4–6 m | 4–6 | Around `y = 2–2.5 m`; target door/drop box, not upper wall. |
| Greek Gyros counter/interior | 6–8 m | 5–7 | Bright white/cool interior; fixture emission supplies apparent brightness. |
| Hive entrance | 5–7 m | 3–5 | Cold and institutional; keep the upper building almost entirely global-lit. |
| Car-park pool | 6–8 m | 4–6 | Hard local island with a large unlit interval. |

These are test values only. Perceptual result under AgX matters more than the number. A point light should be removed if emission, texture, and a character response can create the same image.

## What should not be changed

- Do not raise global exposure as the first response.
- Do not raise hemisphere or moon intensity across the whole map.
- Do not reduce or push back the fog merely to expose remote assets.
- Do not give every streetlight a permanent point or spotlight.
- Do not turn every shop window on.
- Do not make the player denim visibly blue or add a conspicuous rim outline.
- Do not spread magenta across unrelated locations; that would drift toward the cyberpunk shorthand the constitution rejects.
- Do not enable scene-wide dynamic shadows to solve grounding. Use the existing contact shadow, baked AO, authored dark planes, decals, and selective material response.
- Do not light geometry-stage assets broadly just to show their detail. Finish their source-led material and practical-light passes.
- Do not eliminate black intervals. The city should remain a sequence of illuminated islands, not a uniformly exposed level.

## Validation plan

Capture the following fixed development views with overlays off:

1. Player start.
2. Player standing inside a fake streetlight pool and halfway between pools.
3. Bus Stop A, including its ground spill.
4. Dreams and Cass Art approaches.
5. Come Through Lab door/drop box.
6. Village Books frontage.
7. Greek Gyros service counter from the park path.
8. The Hive entrance and car park.
9. Coral west street.
10. South Road midpoint, Real Camera, and Advanced Photo.
11. Bus Stop B / north exit.

For each critical view, compare LOW, MEDIUM, and HIGH. Use AgX for the main judgement; use `?tonemap=off` and `?tonemap=neutral` only for controlled comparison. Capture both idle and walking frames because armour, shoe, bag, and trouser separation changes with motion.

Acceptance criteria:

- The player's head, shoulders, delivery bag, and leg masses remain distinguishable against grass, asphalt, pavement, and a dark façade.
- The player visibly changes colour/value when entering a public-light pool.
- A normal walking route is legible several metres ahead without turning the night grey.
- A functional door/counter/drop box is identifiable from approach distance without relying on a development label.
- Closed, non-functional buildings may remain dark.
- No shop group creates left/right asymmetry solely because LOW selected an arbitrary subset.
- No candidate light switches visibly during a slow walk across a boundary.
- The overlay reports every enabled point/spot light, including Coral and any character/public source.
- The same visual hierarchy survives bloom-off LOW: sources lose glow, but not meaning.
- Bus-shelter and Dreams highlights retain their characteristic hue under AgX without clipping.
- Large parts of every night frame can still be genuinely black or near-black.

## Implementation order

1. Correct diagnostics and selection: central registry, contribution/range test, grouping, hysteresis, truthful counts, Coral ownership.
2. Correct the moved Bus Stop A spill and remove redundant legacy patches against the new road treatment.
3. Add the character visibility floor and one nearby public-lamp response within the existing ceiling.
4. Fix Come Through Lab and Greek Gyros using their authored anchors.
5. Add precise Hive/car-park cues and complete source-led practical lighting as geometry assets receive material passes.
6. Run the fixed-view LOW/MEDIUM/HIGH comparison.
7. Only then tune quantisation, grain, contrast toe, bloom, and individual emissive colour under AgX.

## Final judgement

Zealot of Harperhey needs **more consequential light, not more light everywhere**.

Its darkness is already doing valuable work. The cobalt atmosphere, black intervals, isolated signs, bus shelter, Dreams frontage, wet fragments, and distant windows form a convincing nocturnal grammar. The weak point is that the grammar is sometimes only painted onto the ground: it does not consistently classify the rider, reveal the action, or make the chosen destination legible.

If the player becomes readable as a near-black body, public pools begin to affect him, and functional thresholds receive precise authored light, the game can become darker in the right places while feeling clearer, more photographic, and more faithful to *Public Illumination Studies*. That is the direction to pursue.
