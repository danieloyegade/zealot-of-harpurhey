# Initial loading screen

The game opens on a single reproduced textile-and-silver plate: `public/ui/title/zealot-loading-screen.png` (1672 × 941), shipped as the 749 KB `zealot-loading-screen.webp` made from it (the PNG stays as the source; regenerate with `sharp(...).webp({ quality: 92, effort: 6, smartSubsample: true })` if the artwork changes). It owns the title, the knight/courier joust, the border, the TSAU mark and the authorship credit. Browser UI does not reconstruct or add to that composition.

The only live element is the fill inside the empty progress-bar frame printed near the bottom of the artwork. `IntroScreen` observes Three.js's `DefaultLoadingManager`, advances the bar with model and texture loading, holds the last six per cent for loading-wave settlement and shader compilation, and fills it to 100% only when the city is ready to render. After a 650 ms full-bar hold, the plate dissolves directly into play; there is no intervening menu or input gate.

## Files

| Concern | File |
| --- | --- |
| Markup, accessible title and progress element | `index.html` |
| Full-frame plate and measured bar placement | `src/ui/intro.css` |
| Artwork used in game (WebP of the PNG source) | `public/ui/title/zealot-loading-screen.webp` |
| Loading progress and automatic reveal | `src/ui/IntroScreen.ts` |
| Static loading camera and glide into chase camera | `src/camera/TitleCamera.ts` |
| Wiring, reduced title render scale and focus pull | `src/main.ts` |

## Sequence

1. **First paint.** The artwork appears before the main TypeScript bundle has finished parsing. It is contained at its native 1672:941 ratio against a near-black navy ground.
2. **Loading.** GLTF and texture requests report through `DefaultLoadingManager`. The bar never retreats and is capped at 94%, preventing a completed intermediate loading wave from falsely presenting as finished.
3. **Ready.** After the last loading wave settles, the renderer compiles the loaded world's shaders. The bar then reaches 100% and holds for 650 ms.
4. **Reveal.** The plate fades and softens over 1.1 seconds while the game render returns from its reduced loading resolution to the selected quality profile. The overlay is removed after 1.2 seconds.

## Runtime details

- `?intro=off` removes the loading plate.
- Development `?view=…` routes omit the loading plate and enter their requested view after loading.
- The artwork is intentionally the complete visual source. If it is re-exported at different dimensions or the printed bar moves, re-measure `.intro__progress` in `src/ui/intro.css`.
- The accessible title restates the lettering in the plate as *Zealot of Harpurhey*. The page title and codebase retain the fictional spelling *Harpurhey*; that pre-existing naming discrepancy remains unresolved.
- Audio still requires a user gesture under browser autoplay policy. Automatic visual entry does not bypass that policy; the existing global key/pointer listeners start enabled tracks on the player's first input.
