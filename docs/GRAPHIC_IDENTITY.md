# Graphic identity

Zealot of Harpurhey has two graphic personalities at once:

- **"This is a record"**: coordinates, money, distance, time, deliveries, maps, catalogue numbers, bus routes.
- **"This is a romance"**: calligraphy, horses, swords, flowers, stars, ornament, myth, poetry, the Promised Land.

The player lives between the two. Every composition should oscillate between the sublime and the administrative, and let each puncture the other. A huge romantic phrase mythologises a place; the tiny delivery data beneath it (£3.70, 0.05 KM, 23:47) brings the mythology back down.

The language draws on romantic calligraphy, medieval and heraldic ornament, fashion-editorial design, print and album artwork, municipal information, gig-economy data and night photography. It should read as culturally specific and authored, not as a videogame UI.

Reveal it gradually. The vocabulary unfolds through play the way the city does, so no screen shows everything.

## The record and the romance in type

| Voice | Belongs to | Face | Treatment |
| --- | --- | --- | --- |
| Municipal / archival | The record | EB Garamond capitals (`.z-caps`) | Small and tracked 0.2–0.26em. Opacity carries the hierarchy: primary is read when looked for, secondary through attention, tertiary is almost forensic. |
| Mythic / literary | The title | EB Garamond at display size | Monumental spaced capitals: ZEALOT of HARPURHEY. |
| The hand | The romance | Herr Von Muellerhoff (`--z-hand`), provisional | Often one of the largest objects on screen: 40–80% of the viewport width, crossing other type, running off the edges, read as shape before language. |

### The hand

- **What it should be:** long ascenders and descenders, large sweeping capitals, dramatic swashes, uneven ink, slightly distressed contours, strong horizontal movement, real handwriting character. Somewhere between a book's marginalia, album artwork, fashion typography, a love letter, an old title card, and graffiti by someone with beautiful handwriting.
- **What to avoid:** wedding-invitation calligraphy, generic luxury branding, perfect vector script, Disney-style fantasy lettering, tattoo-shop clichés.
- **Current face:** Herr Von Muellerhoff (Google Fonts) is a placeholder chosen from a specimen against the Lorde and textured-script references, with Mrs Saint Delafield as the heavier alternative. The strongest long-term options are Daniel's own lettering, scanned to SVG, or a licensed face such as Noir Ink Script or Quiet Attempt.
- **Numerals:** the face turns a Roman capital I into something like a 9. Write numerals in lower case in the hand ("night no. i"); in capitals they belong to the serif ("NIGHT I").
- **Motion:** never a corporate draw-on. The hand develops like a photograph: exposure spreading unevenly (an animated radial mask), blur resolving, the second print pass arriving later.

### Place and idea

**HARPURHEY is a place**: serif capitals, coordinates, municipal type. **The Promised Land is an idea**: always in the hand, romantic and unstable. The distinction holds wherever the two meet: the bus destination, the ticket, the title card.

## Two palettes

| World | Colours | Used for |
| --- | --- | --- |
| Night (`.z-world--night`) | Cobalt `#071c5a`, near-black `#020817`, ivory `#efe6d2`, amber `#ffa326` | Play, the title card, menus over the city |
| Print (`.z-world--print`) | Oxblood `#5e1320`, aged cream `#ebdfc6`, ink `#1c1414`, faded pink `#d9a1a6` | Bus tickets, delivery receipts, chapter cards, archive documents, menus, posters, printed maps, character cards |

- **The accent:** one saturated red, `#e5132b`, used for a small star at most. Never a colour code.
- **Tone without ground:** `.z-tone--night` and `.z-tone--print` apply a world's type and ink colours without its background.

## Texture belongs to a medium

Never lay a generic grunge texture over everything. Each medium ages in its own way:

| Medium | Texture | Where it lives |
| --- | --- | --- |
| Handwriting on the night screen | Edge wobble and ink breakup | `#intro-ink` / `#z-ink` |
| Printed type | Ink spread and a wandering edge | `#z-ink-print` |
| Documents | Paper fibre and speckle | `.z-world--print` background |
| Two-colour print | Misregistration: a faint second pass offset from the first | `.z-printed__ghost` |
| Photographic imagery | Film grain | The title card's grain layer, over the city |
| Posters (still to be built) | Screen-print breakup, halftone | — |

## Symbols

Symbols are drafts awaiting approval, per the asset-first rule in `AGENTS.md`.

| Symbol | File | Meaning |
| --- | --- | --- |
| Zealot star | `src/ui/identity/zealotStar.ts` | Four points, lower arm longest. It sits between streetlight flare, camera glint, navigation marker, heraldic mullet, sword and cross. The player's position; the one red accent. |
| Horse | `src/ui/identity/emblems.ts` | A horse passant, woodcut-style with carved lines, carrying an insulated delivery box charged with the star. It stands for the knight's horse, transport, the rider's bicycle, labour, pilgrimage, and the past surviving as an image. Never explained. |
| Rose | `src/ui/identity/emblems.ts` | An engraved line rose. It marks the flower delivery. |
| Cartouche | `src/ui/identity/cartouche.ts` | The recurring signature: concave corners holding lace-like ornaments, a double rule threaded with pinholes, a star medallion breaking the top edge, a bead at the foot. It survives as a single thin line. |
| Calligraphic route | `src/ui/identity/calligraphicRoute.ts` | A journey drawn as a pen stroke (entry loop, swelling swash, arrival flick), with the star marking the rider. |

**Still to be drawn:** sword, cross, arrow, coordinate mark, measurement line, registration mark, and a character-portrait version of the cartouche.

### Treat the collisions seriously

Horse with delivery bag, horse with bicycle wheel, horse with GPS route, horse with QR code, horse with sword, horse with £3.70, horse with coordinates, horse with receipt. None of these are jokey logos. The seriousness is what makes the collision work.

## Ornament that works as interface

Ornament carries information. The boundary between ornament and interface should stay unstable.

- **Star:** the player's position. On the title card it rides the loading line as its head.
- **Swash:** a route.
- **Cartouche:** an active card, a delivery, a ticket.
- **Horse:** transport and the rider.
- **Rose:** the flower delivery.
- **Sword:** a narrative state (planned).
- **Decorative initial:** used very sparingly, borrowing the manuscript hierarchy of a large initial followed by tiny forensic data. D for DELIVERY 001 followed by VINYL EXCHANGE / 0.05 KM / 23:47 / £3.70.

## Negative space and rhythm

Don't fear empty space. A tiny heraldic image in a large empty field can outweigh a crowded composition. Follow dense screens with extremely sparse ones. For example, the title sequence holds a small horse, RIDER 01 and the coordinates far below, with nothing else on screen.

## Compositions

`src/ui/identity/compositions.ts`. All can be reviewed together on the development board at `?identity`.

- **Chapter cards** (`createChapterCard`): night numeral in serif capitals, either an institutional title in capitals (FIGURES ISOLATED WITHIN MUNICIPAL ARCHITECTURE) or a romantic title in the hand (*Flowers for a Stranger*, *Before the Night Is Spent*). They carry an emblem (optionally in the cartouche), a tiny municipal footer, and large negative space. They should feel like album sleeves, fashion campaigns and art-film intertitles, in either world.
- **Delivery card** (`createDeliveryCard`): DELIVERY 001 in the cartouche with the rose. On the title card it sits under an enormous handwritten *Flowers*.
- **Bus destination and ticket** (`createBusDestination`, `createBusTicket`): SERVICE 01, HARPURHEY in serif, a calligraphic route, *The Promised Land* in the hand.
- **The night so far** (`createNightSoFar`): the pause menu as a record set as an artwork. ZEALOT, *The Night So Far* in the hand, a ledger (deliveries, earned, film, time, last bus), a tiny horse, HARPURHEY and MMXXVI. It is not wired to a pause system yet; it is laid out to receive `RiderRecord` values.

## The title card's share

The title card shows only the classical serif, archival microtype, one calligraphic intervention (*The Promised Land* behind HARPURHEY) and one small symbol (the red star on the loading line). Its two beats then introduce the horse and the rose. Map, bus route, ledgers, sword, frames and patterns are withheld for play. See `docs/TITLE_SCREEN.md`.

## Pattern library (planned)

Tartan and check (woven like pixels, matching the game's quantised rendering), leopard, repeating horses, stars, lace and doilies, heraldic motifs, ornamental relief. These are for clothing, bus upholstery, packaging, posters, magazines, Cass Art works, graffiti and chapter cards. They are authored as textures through the Blender and texture pipeline from references, not generated in engine code.

## British symbols

Never used as straightforward patriotic imagery. When they appear they are:

- reconstructed or fragmented
- misprinted or covered in leopard print
- recontextualised or commercialised

The chained unicorn and the lion of the royal arms are candidates for the same treatment as the horse (`creative-constitution.md` §161–163).
