# Cass Art reference texture pass — 22 September 2026

## Sources and limits

Daniel's two supplied images match the existing `DSC06340.JPG` and
`DSC06343.JPG` reference photographs. They remain unmodified. The latter is
sampled directly by Blender UVs for cladding, stickers, chalk tag, alarm,
logo/poster, door popcorn and kick vents. Blender embeds a 3072 × 2048 copy in
the material; the GLB uses WebP.

The fascia letters are **geometry derived from the photograph**, not generated
lettering. `traceCassArtLettering.py` analyses the orange sign region, traces
oriented contours and simplifies to subpixel tolerance. The Blender script
extrudes those outlines and preserves the word spacing. The sign reads
`LETS FILL THIS TOWN WITH ARTISTS`, exactly as photographed.

The transparent window paintings are **generated reconstructions**, not exact
photo extractions. Built-in ImageGen was used, with the prompts below. Their
alpha channels are retained. The main graphic's generated logo is excluded by
UV geometry in favour of the original photographed logo/poster. The artwork
keeps its aspect ratio inside the existing wider model bay; model proportions
and detailed interior stock are not a surveyed reconstruction.

## Saved generated assets

- `blender/source/textures/cass-art/cass-window-display-reference.png`
- `blender/source/textures/cass-art/cass-right-display-reference.png`

## Main display prompt

Use case: background-extraction. Create an actual transparent PNG game texture of ONLY the hand-painted window graphics and stickers from this Cass Art photograph. Closely reproduce the actual marks and positioning. Landscape canvas 3:2 corresponding exactly to the main display glass rectangle from x=215 to 1234, y=350 to 957 in the supplied 1920x1280 rendition. Include upper left white CASS ART EST.1984 logo, blue MUSIC walkman left below, angled red SCHOOL'S OUT cassette at upper middle, green FOR SUMMER cassette at lower middle, swooping pink and yellow thin cables, purple musical notes, black record with white 8 centre and colorful scribbled highlights at right, ESSENTIALS VOL 1 yellow label along bottom of artwork, a few popcorn kernels and the narrow red white popcorn partial strip on right edge. Keep the photograph's handmade paint pen quality, detailed imperfect edges and exact angled orientations, not clean generic icons. Remove ALL shop interior, reflections, people, window frame, wall and background: actual transparent alpha everywhere between painted marks. The bottom approximately 20% should be entirely transparent just as the source has no graphics there. Do not include fascia slogan or architecture. No new content. This asset will be layered onto transparent 3D glass.

## Right display prompt

Background-extraction for a transparent PNG game decal. Reconstruct ONLY the painted window artwork visible in the RIGHT HAND shop window, right of the large plain grey pier, from this reference photograph. Output square canvas on actual transparent alpha. Keep the hand-painted texture and photographed design: three overlapping slightly rotated pale blue-white Polaroid photo outlines in the middle-left, small colorful summer landscapes within two, a thin blue headphone cable winding around them, pink/purple cassette at upper right with yellow label 'DANCE CLASSICS MIX TAPE', a few scattered creamy white popcorn kernels outlined ochre at top left and bottom left, large pale blue/white headphone earpiece and loosely coiled wire toward bottom right. Reconstruct artwork currently occluded by the man. Remove the man entirely; also remove every bit of architecture, shop interior, shelving, glass reflections, mullions and background. Preserve handmade white paint marker irregular edges, detail, and natural imperfect outlines. Transparent gaps between all painted objects. No fascia lettering, no CASS logo, no black record, no extra objects, no people, no background.
