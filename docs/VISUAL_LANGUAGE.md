# Visual language — photographic world pass

## Central principle

Zealot of Harpurhey's visual target is **uncanny realism suspended between the photographic and the obviously constructed** (`ART_DIRECTION.md`), not nostalgia for a console era. The style comes first from photographic reference, deliberate geometry and authored embedded lighting; post-processing is a restrained finishing layer, not the source of any retro character.

Until 24 September 2026 this document (and the render settings it described) targeted a look explicitly modelled on "an ambitious late-1990s or early-2000s console game" — flat per-facet shading, 32-level colour posterisation, and nearest-neighbour-filtered signage. `docs/REALISM_PASS_PLAN.md` Stage 1 removed those specific settings as the first step of a longer realism pass (`docs/VISUAL_REALISM_ROADMAP.md`); this section is reconciled to the current direction. Sections below this point that still describe deliberately economical geometry, embedded/baked-feeling lighting and restrained photographic texture resolution remain current: that discipline is not retro styling, it's the working method for staying performant in a browser, and later realism-pass stages (baked lightmaps, an environment map, higher-resolution PBR sets) build on it rather than replacing it.

The finished bus shelter remains a benchmark for recognisable photographic surfaces coexisting with legible, deliberately simple geometry.

## Central configuration

Global values live in `src/rendering/visualStyle.ts`. It controls internal render scale, filtering profiles, anisotropy, sky and fog, ambient and artificial-light colours, exposure, saturation, contrast, quantisation, dithering, faceted shading, shadows, draw distance and bloom.

Current rendering values:

- Internal 3D render scale: **0.72** of display pixel resolution
- Tone mapping: **AgX**, linear exposure **1.70** (`?tonemap=off` restores the uncurved image at display-referred exposure 1.34)
- Saturation: **1.12**
- Contrast: **1.05**
- Colour quantisation: **255 levels per channel** (a no-op at 8-bit output; retained as a uniform rather than removed, in case a future deliberate posterise effect wants it). Until 24 September 2026 this was 32 levels, which visibly banded dark gradients (the night sky, light pools) — a retro-console signature, not a photographic one. Removed in Stage 1 of the realism pass.
- Ordered-dither strength: **1/255** (down from 0.003; still just enough to break up 8-bit banding, no longer a visible dither pattern)
- Shadow-weighted film grain: **0.042**
- Edge vignette strength: **0.20**
- Faceted (flat per-facet) shading: **off** (was on; this was the single strongest "low-poly toy" signal — see `docs/VISUAL_REALISM_ROADMAP.md` §1). Off means every world material now shades per-vertex/per-pixel off smooth normals.
- Post-process antialiasing: **SMAA**, on at MEDIUM and HIGH (`quality.smaaEnabled`). EffectComposer's render-target chain does not receive the canvas's own MSAA, so this is the real edge antialiasing for the composed frame.
- Shadows: disabled (real-time; static lighting is heading toward Blender-baked lightmaps per the realism pass, not a real-time shadow map, though a player/bike shadow is planned)
- Fog: desaturated cobalt `#081327`, near **46 m**, far **106 m**
- Bloom: strength **0.34**, radius **0.32**, threshold **0.88**

The canvas retains full CSS window dimensions. Only its internal 3D backing resolution is scaled; HTML development UI remains at display resolution.

## Texture profiles

`PHOTO_ENVIRONMENT` uses linear magnification, trilinear minification and anisotropy 2. It is used for photographic façades, brick, roads, pavement, foliage and finished GLB photography. This retains image recognisability while allowing the deliberately small source resolution to remain visible.

`RETRO_GRAPHIC` is used for signs, road annotations and other canvas-drawn graphics. Until 24 September 2026 it forced nearest magnification and nearest mip selection, giving these signs hard, pixellated edges — a deliberate retro-console look. Stage 1 of the realism pass switched it to the same linear magnification and trilinear minification as `PHOTO_ENVIRONMENT`; it keeps its own (lower) anisotropy. These are canvas-drawn signage, not pixel art, so there is no longer a reason to force nearest-neighbour filtering on them.

Do not globally force photographic imagery to nearest-neighbour filtering. The photographic source must remain legible.

## Texture budget

- Small props and vegetation: 128 × 128 or 256 × 256
- Signs and posters: 256 × 256 or 256 × 512
- Ordinary façade sections: 256 × 512 or 512 × 512
- Major photographic landmark façades: 512 × 512; 1024 maximum only when justified
- Ground tiles: 256 × 256 or 512 × 512

Source photographs are never automatically upscaled. Grain, softness, colour casts, uneven exposure and stains should survive extraction.

## World-overhaul texture pack

The current pack is reproducibly generated by `scripts/generateWorldTextures.mjs`. Runtime derivatives live under `public/assets/textures/world-prototype/`. The generator creates procedural low-resolution materials and extracts deliberately small façade derivatives from repository-owned Dreams and Coral reference photographs. Those original photographs remain outside `public/`.

The overhaul set includes 512-pixel wet asphalt, weathered and damp pavement, soot-stained and painted brick, cracked concrete, grimy shutters, damp grass, poster sheets, uneven window rows, broken-reflection masks and low-resolution Dreams/Coral shopfront crops. Foliage, oxidised metal and light masks use 128- or 256-pixel sources. Earlier `*-temporary` textures remain available during migration but are no longer the primary road, park or blockout-building surfaces.

Wetness is represented with locally reduced roughness (road wet decals, damp pavement variants) plus sparse additive colour fragments. It deliberately does not use a continuous mirror plane: practical lights, shopfronts, the shelter and the pickup create broken streaks separated by dark asphalt.

Physical façade identity is now carried by shallow shopfront recesses, canopies, drainpipes, window depth and weathered signs. Photography supplies recognisable storefront information where an approved repository reference exists. Procedural surfaces supply the surrounding grime and ageing; they are not treated as final landmark photography.

### Legacy prototype set

Textures at 256 × 256:

- dark asphalt
- worn pavement
- damp pavement
- dark red brick
- dirty brown brick
- stained alley masonry
- stained concrete
- painted metal
- dirty shop shutter
- dark window sheet
- illuminated window sheet
- cheap grass

Textures at 128 × 128:

- rough foliage
- tree bark

These legacy procedural images were a prototype systems test, not a replacement for approved photographic derivatives. Their limited resolution, grain, stains and coarse tonal blocks are intentional.

## Architecture and ground

Unnamed/unfinished buildings use a reusable 2.5D construction: rectangular mass, distinct roof material, layered upper windows, recessed shutter or photographic shopfront, narrow doorway, projecting canopy, drainpipe, weathered identity sign, posters/graffiti and an uneven roof silhouette. The topology and collision footprints do not change. Finished landmarks can later replace the mass without changing layout data.

Roads are layered rather than uniform. A photo-scanned asphalt (a CC0 stand-in until the road atlas is photographed) tiles every 2.1 m with roughness and normal maps, and world-space tone drift and a second rotated sample hide the repeat. Over it sit decals for repairs, trenches, potholes, cracks, tar seams, worn paint, tyre staining, gutter grime and local wetness. The markings are never pristine. Gutter edges carry the most information. Dry asphalt stays rough; only local wet decals are glossy. Pavements are layered the same way: 600 mm concrete flags with per-flag tone, kerb stones on carriageway edges, tarmac reinstatements, cracked and sunken flags, gum concentrated at bus stops and shop entrances, wall-base grime, verge creep, moss, leaves and red tactile paving at crossings. See `ROAD_ATLAS.md`. Pavement flag faces read a photo-scanned concrete, offset per flag. Park grass is a photo scan too, worn to mud in bald patches and along trodden path margins, and park paths are scanned tarmac. Only the car park still uses a repeated low-resolution colour texture with high roughness and no normal map. Damp pavement variants break uniform repetition. Sparse coordinate-like road annotations introduce the measured/catalogued language of *The Spectres Are All Around Us*.

## Sky, fog and palette

The sky is a camera-centred shader dome: almost-black charcoal navy at the
zenith, desaturated navy and blue-grey below, and a restrained dirty
mauve-grey pollution band at the horizon. Three broad procedural waves produce
barely visible large-scale density changes; they are not readable cloud forms
and move too slowly to announce themselves as animation. The shader is one draw
call and uses no textures, HDRI, particles or volumetric simulation.

The default urban sky contains **zero stars**. `createNightAtmosphere.ts` keeps
an optional 0–15 point system for testing, but those points are round,
sub-pixel-to-one-pixel, muted and below the bloom threshold. Distance fog uses
a dark desaturated member of the same blue family so remote architecture loses
detail into the atmosphere before the horizon, without lifting the black
intervals between practical lights.

In development, `window.zealot.atmosphere` exposes `getParameters()` and
`set({...})`. Tunable values include the four sky colours, brightness,
saturation, horizon glow colour/strength/height, star count/brightness/size,
cloud-noise strength/scale/speed, and fog colour/near/far. For example:

```js
zealot.atmosphere.set({ horizonGlowStrength: 0.12, fogFar: 112 })
```

Palette:

- charcoal-navy zenith `#01040b`
- desaturated lower sky `#09152a`
- dirty mauve-grey horizon `#151722`
- sodium amber `#ffa326`
- fluorescent green `#70ff9b`
- magenta `#ff3a9c`
- cold white-blue `#c4dcff`
- dirty red/brown masonry and near-black green shadows

## Public illumination

Streetlights are real-scale council fixtures (`docs/assets/streetlights.md`):
seven- and eight-metre galvanised or painted columns, deliberately mundane by
day. Only the lamp itself, its bowl and a faint spill on the housing underside
carry the light colour; columns and casings stay unlit metal. Each lamp keeps
a textured additive ground pool, centred under the lantern, and two fragmented
reflection streaks. The former open eight-sided translucent cone meshes were
removed: from distant angles their facets became enormous pyramids against the
sky. A single managed public-light proxy moves to the lantern above the
current nearby pool so the player and immediate ground respond to one pool at
a time; the columns do not each carry real-time spotlights.
Darkness between pools remains part of the composition.

Selected façades receive small coloured accents, while low emissive brick contributions imitate lighting information embedded in a photographed or baked surface. Finished bus-shelter lights retain their stronger local colour treatment.

## Vegetation

Park trees use five-sided trunks and clustered, textured, un-smoothed dodecahedron crowns. Uneven scale, rotation, three-part crown offsets and occasional amber light catches stop them reading as default spheres while retaining a very small triangle count. This is an intermediate retro vegetation language; approved photographic cut-out foliage can replace it later.

## Post-processing limits

The current composer applies restrained bloom, SMAA edge antialiasing, AgX tone mapping with display conversion, saturation/contrast adjustment, a (now effectively disabled, see "Central configuration") colour-quantisation step, subtle 4 × 4 ordered dithering, shadow-weighted film grain and a restrained vignette. Sky and optional star values remain below the bloom threshold, leaving bloom to practical artificial sources. It deliberately excludes scanlines, CRT curvature, chromatic aberration, tape damage, vertex wobble and aggressive pixelation.

## Street-level density

Reusable low-poly bins, bollards, drain covers, rubbish bags and abandoned shopping trolleys provide scale and disorder without changing traversal. Their placement is authored rather than uniformly scattered. The player-start/bus-shelter edge has the densest first pass; the same kit appears selectively on west, east and south streets.

## Pickup prototype and development UI

The development-only park pickup is an octahedral yellow core with a low-segment green ring, translucent magenta halo, fake ground pool and local magenta light. It rotates and hovers but has no gameplay behaviour.

Press `H` to hide or restore location labels and the HTML debug panel for clean visual assessment. There is currently no collision-geometry renderer; any future collision overlay should use the same development-overlay visibility flag.
