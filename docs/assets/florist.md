# Florist photographic architecture asset

## Available references

- `references/architecture/florist/florist-front-reference/IMG_8712.PNG` — 1284 × 2778 screenshot containing the clearest view of the florist shopfront and the building above it.
- `references/architecture/florist/florist-front-reference/IMG_8714.PNG` — 1284 × 2778 wider Manchester night scene. It is useful as broad atmospheric context but does not show the florist.

`IMG_8712.PNG` is the strongest frontal/main reference currently available. It is an oblique screenshot rather than a clean architectural photograph and contains interface overlays and neighbouring imagery.

## Visible structure and proportions

The florist occupies the ground floor of a narrow, approximately rectangular building with a flat roof and shallow parapet. The building has three visible storeys in total: the shop at street level and two upper storeys. Its street-facing elevation appears roughly half as wide as it is tall. The pale stone or concrete façade is heavily stained and divided by strong vertical piers and shallow horizontal bands.

The shopfront has a full-width white fascia with distressed dark lettering and red accents. Below it are two glazed display areas separated by painted framing, plus a narrow entrance door at the right. A smaller dark sign sits above the right-hand display/entrance area. Posters, stickers and printed material cover parts of the lower surround.

The upper façade uses recessed, dark window openings with projecting lintel or hood details. The first upper floor appears to contain two broad windows and a narrower right-hand opening. The top floor has a less regular sequence of smaller recessed openings. The roof terminates in a plain parapet rather than a pitched silhouette.

## Geometry versus photography

Geometry should provide:

- The simple three-storey rectangular mass and flat parapet silhouette
- Shallow overall building depth
- Recessed shop doorway
- Selective depth for the two display windows
- Fascia and secondary sign projection
- Major façade piers, bands, window recesses and projecting lintels
- A minimal pavement contact edge where needed

Photography should provide:

- Pale stone/concrete surface, staining and grime
- Fascia lettering and secondary signage
- Shop-window contents, reflections and darkness
- Posters, stickers, wear and lower-wall clutter
- Upper-window appearance and most frame detail
- Colour casts, uneven exposure and other photographic imperfections

The intended pipeline is photograph → texture extraction → shallow low-poly building geometry → selective 3D depth → GLB → Three.js. The bus shelter remains the quality and restraint benchmark; small façade detail should not be rebuilt simply because it could be modelled.

## Missing photographic coverage

The current references do not establish the building's right or left elevations, rear, roof surface, exact depth, measured scale, doorway interior, or shopfront at a clean straight-on angle. The right side is substantially obscured by neighbouring mural imagery. Fine signage text is also difficult to resolve. Those areas would require restrained approximation unless better source photographs are supplied and approved.

## Estimated production scale

The first exterior benchmark uses an estimated **7.5 m depth × 6.0 m frontage × 10.4 m height**. These are not surveyed dimensions. They are inferred from a typical roughly 2.0 m shop door, the three visible storeys, common UK shopfront proportions, and comparison with the 1.78 m player.

Generated working derivatives remain outside the runtime build:

- `blender/source/textures/florist/harperhey-florist-facade.jpg` — 512 × 768
- `blender/source/textures/florist/harperhey-florist-shopfront.jpg` — 512 × 384

Both are embedded in `public/assets/models/harperhey-florist.glb` during export. The primary crop isolates the central façade; the secondary crop preserves more shopfront signage and window content at pedestrian distance.

Regenerate the complete asset from the project root with:

```sh
/Applications/Blender.app/Contents/MacOS/Blender \
  --background \
  --python blender/scripts/createFlorist.py
```

This produces the editable `.blend`, self-contained runtime GLB, primary comparison preview and oblique diagnostic preview without modifying either approved reference image.
