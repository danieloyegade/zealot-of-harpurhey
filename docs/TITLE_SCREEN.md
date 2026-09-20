# Title card

The first screen: **ZEALOT of HARPERHEY** over the live city. It reads as a photographic title card before it reads as a game menu, and it introduces only a little of the graphic identity (`docs/GRAPHIC_IDENTITY.md`):

- the classical serif
- archival microtype in the corners
- one calligraphic intervention: *The Promised Land*, developing behind HARPERHEY
- one small symbol: the red Zealot star riding the loading line

Between loading and entry there are two sparse beats, the horse and rider and then the first delivery, so the screen moves from dense to sparse. Everything else in the identity (map, bus, ledgers, sword, chapter cards) is withheld for play.

## Files

| Concern | File |
| --- | --- |
| Markup: title, corners, loading line, beats, prompt | `index.html` |
| Typography, layout, beats, motion, responsive rules | `src/ui/intro.css`. Linked from `index.html` so it paints before the bundle parses. |
| Orchestration: loading progress, sequence, entry timeline | `src/ui/IntroScreen.ts` |
| Beat contents, loading star, controls line | `src/ui/title/marginalia.ts` |
| Asset filename → catalogue entry ("pallet / timber / worn brown") | `src/ui/title/assetCatalogue.ts` |
| Rider record: persisted state with first-night defaults | `src/ui/title/riderRecord.ts` |
| First delivery data | `src/delivery/firstDelivery.ts` |
| Identity parts and compositions (star, horse, rose, cartouche, delivery card) | `src/ui/identity/` |
| Static camera and glide into the chase camera | `src/camera/TitleCamera.ts` |
| Muffled street, ballast hum, unveiling | `src/audio/AmbientAudio.ts` |
| Wiring: title render scale, focus pull, input hold, `?identity` board | `src/main.ts` |

## Sequence

1. **Paint (before JS).** Scrim, lamp, title and corners. An inline script adds `is-typeset` once EB Garamond and the script face have loaded, so neither appears in a fallback face.
2. **Loading.** `IntroScreen` listens to three's `DefaultLoadingManager`. The hairline fills, the red star rides its head, and the count and a catalogue entry per named asset update as files load. *The Promised Land* develops behind HARPERHEY at about 10% opacity: exposure spreads unevenly, the blur resolves, and the amber second pass arrives later.
3. **Assembled.** The wave settles and shaders are prewarmed. The label becomes "City assembled" and the star reaches the end of the line, held for 1.4 s. From here Return enters the city immediately, so the beats never block entry.
4. **Rider beat** (2.6 s). The title card steps back entirely, leaving a small horse, RIDER 01, and the coordinates far below.
5. **Delivery beat** (4.6 s). An enormous handwritten *Flowers* develops across the frame, with DELIVERY 001 / VINYL EXCHANGE / UPPER FLOOR / 0.05 KM / £3.70 in the cartouche under the rose. The event is announced by typography alone, with no "quest started".
6. **Ready.** The title card returns with *The Promised Land* behind it, "Enter Harperhey / [ Return ]" appears, and the controls line shows for 9 s.
7. **Entering.** Marginalia and the loading line fade, the lamp swells, and the street opens up. Entering from a beat brings the title back first.
8. **Revealing (2.8 s).** Title and script dissolve, the render returns to full resolution under a focus pull, and the camera glides into the chase camera.
9. **Gone (5.6 s).** The overlay is removed.

## The city behind the card

The world renders from the start, from a fixed shot (`TitleCamera`: eye height at the park's south edge). It renders at `TITLE_RENDER_SCALE` (0.14) of normal resolution: the browser's upscale does the defocusing, and the title screen costs less than gameplay. No lights or render passes are added for the menu. Fog drift, the passing headlights, exposure breathing and grain are CSS `transform`/`opacity` animations. The two "develop" reveals animate a registered CSS property (`--intro-develop`) through a radial mask for a few seconds each.

In development, `?titleshot=x,y,z,lookX,lookY,lookZ` recomposes the shot.

## Feeding it real state later

The title card deliberately shows no ledger. The record (night, money, film, bus) belongs to the pause menu, which is laid out as `createNightSoFar` in `src/ui/identity/compositions.ts`. Game systems should write fields into `localStorage['zealot-of-harperhey:rider-record']` using the `RiderRecord` field names. Only `entries` is written today, incremented on each entry. Add controls to `CONTROLS` in `marginalia.ts` when interact or map keys exist.

## URL parameters

- `?intro=off`: no title card. The world renders at normal resolution immediately.
- `?view=…` (dev): the card is removed as soon as the world loads.
- `?titleshot=…` (dev): see above.
- `?identity` (dev): the graphic identity board (marks, chapter cards, bus destination and ticket, pause menu, delivery beat) instead of the title card.

## Known limits

- Browsers keep audio silent until the first key press or click, so the title is silent until the player presses a key or clicks.
- The only street recording is `ambience/manny-streets.mp3` (192 kbps MP3; the 97 MB WAV master was dropped).
- EB Garamond, Herr Von Muellerhoff and Mrs Saint Delafield load from Google Fonts. The script face is a placeholder; see `docs/GRAPHIC_IDENTITY.md`.
