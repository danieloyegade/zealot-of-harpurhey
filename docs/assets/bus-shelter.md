# Harperhay bus shelter benchmark

## Reference

The benchmark uses Daniel Oyegade's original photograph at `references/architecture/bus stop/Hires2.jpg` (1818 × 1456). The original is treated as immutable source material. Derived working crops are generated separately by `blender/scripts/createBusShelter.py`.

## Photographic analysis

The photograph is organised around a long, shallow shelter viewed almost frontally. A rounded dark roof caps a green-black metal frame. Four rear uprights divide large glass areas containing baked reflections of trees, houses, parked cars, grass, and warm street illumination. The left bay holds a Lancashire bus timetable. A chunky illuminated advertising housing closes the right end and produces a strong pink cast. A red horizontal perch rail cuts across the lower glazing. The central abandoned shopping trolley is the strongest foreground interruption and an essential part of the composition.

Major colour regions are deep green-black metal, green/cyan glass, warm amber reflected architecture, bright pink advert light, the red rail, and silver-grey trolley metal. Apparent illumination comes from warm light above/front, green ambient light around the glass and grass, and the advert's pink lightbox.

## Geometry versus photography

Geometry carries silhouette, parallax, and the objects that must read from changing viewpoints:

- Rounded/chunky roof
- Sparse structural posts and horizontal frame rails
- Rear and side glass planes
- Timetable and advert housings
- Red U-shaped rail and narrow perch
- Economical trolley basket rim, implied basket bars, handle, lower frame, and four wheels

Photographic textures carry specific surface information that would be wasteful or sterile to remodel:

- Rear-glass reflections, local architecture, trees, cars, grain, and green colour cast
- Original timetable typography and printed information
- Original advert typography, pink halation, fading, and photographic imperfections

The trolley basket uses a small number of low-sided rods rather than an alpha wire mask. At gameplay distance this preserves a dimensional silhouette and reads more reliably from oblique angles, while intentionally avoiding a literal model of every wire.

## Working derivatives

- `harperhay-bus-shelter-glass.jpg` — 512 × 256
- `harperhay-bus-shelter-timetable.jpg` — 256 × 384
- `harperhay-bus-shelter-advert.jpg` — 256 × 512

These intentionally modest JPEGs live under `blender/source/textures/` and retain photographic grain, colour casts, baked reflections, and halation. Blender embeds them in the exported GLB, so duplicate loose copies are not shipped from `public/`. The source photograph also remains outside `public/`.
