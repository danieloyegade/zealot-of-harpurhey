# Title card

The first screen is a scanned print object held over the live city. It reads as an encountered artefact before it reads as a game menu. Its static plate collapses the project's delivery-worker/knight structure into one image: an engraved knight on horseback and a courier on a Starling hire bike, running at each other with couched lances, under the title in silver calligraphy on oxblood.

**It is one screen.** The plate is never stepped away from: the card loads, assembles and becomes interactive without the frame ever changing. The two sparse interstitial beats that used to play between loading and entry — the horse and rider, then *Flowers* and the first delivery — were removed on 2026-09-20, because they read as two further screens rather than as one object being looked at. Their contents survive intact in `src/ui/identity/` and are still on the `?identity` board; if they are ever wanted again, they belong somewhere that is not the threshold.

The plate is `public/ui/title/zealot-title-card.jpg` (1672 × 940). It owns the title, the joust, the border, the silver scrollwork and every piece of marginalia — *The Spectres Are All Around Us*, the coordinates, `Manchester MMXXVI`, `A game by Daniel Oyegade` — **and the menu: `ENTER`, `SETTINGS`, `QUIT`**. None of that is rebuilt from browser primitives. Live HTML carries only assembly, the menu's behaviour, and the accessible title.

## The printed menu

Because the menu is printed, it cannot light up on its own. Three transparent `<button>`s are laid over the printed words, positioned in per-cent of the plate, and pointing at one brings the card's single lamp onto that line: a feathered pool of light (`mix-blend-mode: screen`, so it lifts the silver out of the oxblood rather than laying a film over both) and a rule struck underneath. Once the city is ready, `Enter` is the line already under the lamp, breathing.

- **Enter** goes into the city, as Return always has.
- **Settings** and **Quit** are `aria-disabled` rather than `disabled`: they are meant to be chosen, and to answer for themselves. Choosing one gutters the lamp and writes `Settings — not yet` on the line above the printed rule. Neither is implemented.

Keyboard: Return enters; once the menu is live, `ArrowUp`/`ArrowDown` walk the three lines and a focused line is activated by Return or Space in the usual way. On a coarse pointer a tap anywhere on the card enters, and a tap on one of the three lines is that line only.

The hit areas are measured off the artwork, so the plate's box is locked to its own aspect (`aspect-ratio: 1672 / 940`) and contained in the window. At 16 : 9 it fills the frame; at any other ratio the night shows above and below it, which is the card's premise. `container-type: inline-size` makes `1cqw` one per-cent of the plate, so the live type scales with the print rather than with the window. **If the plate is ever re-exported at different proportions or with the menu moved, the per-cent figures in `intro.css` (`.intro__choice--*`, `.intro__rule`, `.intro__caption`) must be re-measured.**

## Files

| Concern | File |
| --- | --- |
| Markup: plate, accessible title, printed menu, assembly, beats | `index.html` |
| Plate box, menu hit areas and lamp, assembly, beats, motion | `src/ui/intro.css`. Linked from `index.html` so it paints before the bundle parses. |
| Printed title-card plate | `public/ui/title/zealot-title-card.jpg` (source: `references/title_screen/renders/ZEALOT2.png`) |
| Orchestration: loading progress, menu, sequence, entry timeline | `src/ui/IntroScreen.ts` |
| Loading star and controls line | `src/ui/title/marginalia.ts` |
| Asset filename → catalogue entry ("pallet / timber / worn brown") | `src/ui/title/assetCatalogue.ts` |
| Rider record: persisted state with first-night defaults | `src/ui/title/riderRecord.ts` |
| First delivery data | `src/delivery/firstDelivery.ts` |
| Identity parts and compositions (star, horse, rose, cartouche, delivery card) | `src/ui/identity/` |
| Static camera and glide into the chase camera | `src/camera/TitleCamera.ts` |
| Muffled street, ballast hum, unveiling | `src/audio/AmbientAudio.ts` |
| Wiring: title render scale, focus pull, input hold, `?identity` board | `src/main.ts` |

## Sequence

1. **Paint (before JS).** The plate arrives through a short focus settle over the low-resolution live city. An inline script adds `is-typeset` once EB Garamond is ready, which is what the live marginalia waits for.
2. **Loading.** `IntroScreen` listens to three's `DefaultLoadingManager`. The assembly line **rides the plate's own printed bottom rule**: a silver fill grows along it with the red star at its head, `Assembling the city` and the count sit below it in the plate's lower margin, and a catalogue entry per named asset runs above it.
3. **Assembled.** The wave settles and shaders are prewarmed. The label becomes "City assembled" and the star reaches the end of the line, held for 1.4 s.
4. **Ready.** The assembly line fades, the printed menu becomes live with the lamp on `ENTER`, and the controls line shows for 9 s on the line above the rule. Nothing about the frame has changed since the first paint.
5. **Entering.** The menu and the live marginalia fade, the lamp swells, and the street opens up.
6. **Revealing (2.8 s).** The plate dissolves, the render returns to full resolution under a focus pull, and the camera glides into the chase camera.
7. **Gone (5.6 s).** The overlay is removed.

## The city behind the card

The world renders from the start, from a fixed shot (`TitleCamera`: eye height at the park's south edge). It renders at `TITLE_RENDER_SCALE` (0.14) of normal resolution: the browser's upscale does the defocusing, and the title screen costs less than gameplay. No lights or render passes are added for the menu. Fog drift, the passing headlights, exposure breathing and grain are CSS `transform`/`opacity` animations, and they sit *behind* the plate — on a 16 : 9 window they are only felt in the letterbox of other ratios and in the entry.

In development, `?titleshot=x,y,z,lookX,lookY,lookZ` recomposes the shot.

## Feeding it real state later

The title card deliberately shows no ledger. The record (night, money, film, bus) belongs to the pause menu, which is laid out as `createNightSoFar` in `src/ui/identity/compositions.ts`. Game systems should write fields into `localStorage['zealot-of-harperhey:rider-record']` using the `RiderRecord` field names. Only `entries` is written today, incremented on each entry. Add controls to `CONTROLS` in `marginalia.ts` when interact or map keys exist.

When Settings and Quit are built, they replace the `refuse()` branch in `IntroScreen.handleChoice` — the hit areas, focus order, lamp and keyboard walk are already in place.

## URL parameters

- `?intro=off`: no title card. The world renders at normal resolution immediately.
- `?view=…` (dev): the card is removed as soon as the world loads.
- `?titleshot=…` (dev): see above.
- `?identity` (dev): the graphic identity board (marks, chapter cards, bus destination and ticket, pause menu, delivery beat) instead of the title card.

## Known limits

- **Spelling.** The plate is lettered *Harpurhey*; the codebase, the page `<title>` and the `localStorage` key are *Harperhey*, the deliberate fictional spelling `AGENTS.md` settled on. The accessible `<h1>` restates what the plate actually says, so it reads *Harpurhey* and disagrees with the page title. One of the two needs to give — unresolved.
- **Phones.** The plate is a landscape object, so on a phone it is contained and the printed menu is a few pixels tall. Tapping anywhere enters; the assembly readout and controls line are dropped below 760 px. A portrait crop of the plate, or a separate legible menu below it, is still an open design question.
- Browsers keep audio silent until the first key press or click, so the title is silent until the player presses a key or clicks.
- The only street recording is `ambience/manny-streets.mp3` (192 kbps MP3; the 97 MB WAV master was dropped).
- The plate is a quality-90 JPEG (759 KB) re-encoded from the 2.9 MB PNG render, since it is the first paint asset. Re-encode from the PNG in `references/` rather than from the JPEG.
- EB Garamond, Herr Von Muellerhoff and Mrs Saint Delafield load from Google Fonts. The card itself now only needs EB Garamond; the script faces are still loaded for `src/ui/identity/`. See `docs/GRAPHIC_IDENTITY.md`.
