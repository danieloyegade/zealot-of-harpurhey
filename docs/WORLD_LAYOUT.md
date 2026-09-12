# Canonical world layout — Map v0.3

`references/world/zealot-city-map-v0.3.jpg` is the canonical visual reference for world topology as of Map v0.3.

The image is authoritative for topology, relative placement, building order, road relationships, park position and outward connections. Coordinates below are an adjustable compact-pedestrian interpretation, not surveyed measurements. The broader fictional-collage and art-direction principles in `WORLD.md` and `ART_DIRECTION.md` remain unchanged.

The canonical map image defines topology and relative spatial relationships; in-game dimensions may be tuned for traversal and composition.

## Orientation and scale

- Map top / negative Z: north
- Map bottom / positive Z: south
- Negative X: west
- Positive X: east
- One world unit: one metre
- Playable bounds: X -64 to 64; Z -62 to 78
- Main road width: 7.5 m
- Typical pavement width: 2.5 m, widened near building rows where useful
- Central Park: 44 m east-west × 34 m north-south, centred at (0, 0)

At the production 2.4 m/s walking speed, a direct full-district crossing is roughly 45 seconds. Development builds raise walking speed to 3.12 m/s and running speed to 7.65 m/s for quicker visual inspection. Routes around buildings and across the park make important deliveries meaningful while keeping the district compact.

## Named locations

Coordinates are plot centres. Footprints are X width × Z depth.

| Location | Centre (X, Z) | Footprint | Status / relationship |
| --- | ---: | ---: | --- |
| Florist | (-16.9, -32) | 6 × 7.5 m | Finished photographic asset aligned beside MCR1's integrated stone doorway |
| Dreams | (1.5, 39) | 18 × 8.5 m | North-facing photographic hero asset shifted east to accommodate the enlarged Cass Art frontage |
| Renee | (17, -38.6) | 13.8 × 13.2 m | Geometry-first Renee blockout; final textures and interior-detail pass pending |
| Come Through Lab | (-37, -15) | 6 × 9.7 m | Geometry-complete east-facing GLB hero asset, shopfront flush to the plot's east edge (shared -34 building line with Village Books/Coral); drop box and supply holder load as independent props at the entrance; final textures pending |
| Village Books | (-38.12, -3.5) | 8.24 × 7.88 m | East-facing geometry blockout replacing the old box shop; fascia aligned to the shared X = -34 building line; detail pass and textures pending |
| MCR1 | (-29, -36) | 12 × 7 m | Geometry-first corner-shop asset west of Florist with a clear gap between their authored envelopes; final textures pending |
| Coral | (-39, 17) | 10 × 23 m | Full-scale east-facing Blender hero asset occupying the expanded west plot |
| Cass Art | (-16.6, 39) | 18.2 × 11.93 m | Enlarged enterable geometry-first GLB in the former Real Camera area, with illuminated interior fixtures |
| Gulliver's Pub | (27.9, -40) | 8 × 16.6 m | South-facing geometry-first asset directly east of Renee, with aligned front planes and a 0.1 m envelope gap; final textures pending |
| Vinyl Exchange | (-7, 49) | 12 × 10 m | South-facing unit directly behind Eastern Bloc; the two rear walls touch |
| Car Park | (43, 0) | 20 × 14 m | Open surface between upper and lower east plots |
| Arts Council / The Hive | (47, 20) | 20.4 × 44.3 m | Geometry asset centred on the east-side plot with its Lever Street frontage facing west |
| Eastern Bloc | (20, 69.75) | 10 × 10 m | North-facing unit touching the east side of Advanced Photo across South Road |
| Spice Cabin | (10.5, 49) | 11 × 10 m | South-facing takeaway on the recessed South Road frontage |
| Off-Licence | (22.5, 49) | 11 × 10 m | South-facing South Road atmospheric/interior location |
| Real Camera | (-11.5, 69.75) | 14 × 10 m | North-facing unit opposite Vinyl Exchange and west of Advanced Photo; offset to keep the South Road exit open |
| Advanced Photo | (10.5, 69.75) | 9 × 10 m | North-facing unit across South Road, directly opposite Spice Cabin |
| Central Park | (0, 0) | 44 × 34 m | Geographic anchor and cross-district shortcut |

## Roads, routes and exits

Inner north and south roads run east-west at Z -25.5 and Z 25.5. Inner west and east roads run north-south at X -29.5 and X 29.5. Most named building rows sit between this park-facing ring and the outer boundary streets at north Z -44.2, south Z 59.5, west X -48 and east X 57. Cass Art is approximately 30 percent larger than its first integration and nearly matches the Blender asset's authored scale. Its west edge clears the West perimeter road and its east edge meets Dreams cleanly; Dreams has shifted east to preserve that boundary. Vinyl Exchange remains on the south-facing frontage behind Dreams. Real Camera faces Vinyl Exchange from the opposite side of South Road. Advanced Photo remains opposite Spice Cabin, with Eastern Bloc directly beside and touching its east wall. South Road has pavement on both shopfront sides and the north frontage has its own streetlights. The park has perimeter paths and two diagonal crossings so it is a usable pedestrian shortcut rather than an inaccessible island. Cheap primitive trees and benches establish scale without becoming final scenery, and a marked 8 × 6 m area at (12.5, 3) reserves space for the future playground.

Outward future-area markers are:

- North Road: (0, -59)
- South Road: (0, 75)
- West: (-61, 25.5)
- East: (61, 0)

The Arts Council remains directly south-east of the car park. The former procedural blockout has been removed and replaced by the metric The Hive GLB. Its Lever Street entrance faces west, while the collision footprint follows the full 20.4 × 44.3 m architectural envelope.

Advanced Photo is now active as a compact South Road shop opposite Spice Cabin. Real Camera sits west of the South Road exit and opposite Vinyl Exchange, while Advanced Photo sits east of the exit, forming a small photographic-retail cluster without closing the future route.

## Player and transport infrastructure

- Player start: (0, 3.5), just south of and facing the Central Park fountain
- Bus Stop A: (0, 20.4), centred on the South park zebra crossing
- Bus Stop B: (0, -49), on outer North Road
- Sterling Bikes South dock: (-24, 26)
- Sterling Bikes East dock: (27, 4), near the car park
- Greek Gyros food stand: (14, -19.35), on the park's north pavement opposite Renee

Both bus stops instance the geometry-first North Road, Preston shelter and its independently parented shopping trolley. The glass is truly transparent and contains no baked background photography. The bike docks are development blockout markers only; no bicycle gameplay is implemented.

The Greek Gyros kiosk is a standalone placeable prop rather than a named plot, declared in `FOOD_STANDS` alongside the other markers. It backs onto North Road with its authored serving frontage facing +Z into the park, so the queue forms on the park side and the stand reads across the road from Renee's frontage. It sits west of the existing bollard pair and streetlight at x = 18.5-20. Its collision box is 6.4 m wide by 2.6 m deep, extended 0.56 m east to enclose the side service step, and stops the player at the counter lip while leaving the projecting canopy overhead clear. The asset is untextured geometry: the fascia carries no wordmark or flags and nothing glows yet, though the GLB ships four light anchors for that pass.

## Implementation boundaries

Named plots are data-driven in `src/world/worldLayout.ts`. Finished landmark assets replace their corresponding loading blockouts without changing the surrounding road topology. The Florist, Dreams, full-scale Coral complex and reusable bus shelter are finished assets. Cass Art, Renee, Gulliver's and MCR1 now use their geometry-first Blender reconstructions in game, but remain works in progress because their final textures have not been produced. The remaining named buildings, park landscape, car park, roads, crossings, paths, bike docks, exits and general street furniture remain intentionally economical blockouts.

Development labels are created only when `import.meta.env.DEV` is true and are removed from production builds. Building and shelter collision remains two-dimensional axis-aligned bounding boxes. Renee, Cass Art, and Coral use multiple boxes for their walls and fixed frontage sections instead of solid footprints, leaving their entrances and interior circulation open to the player. The park, roads, paths, car park and future exits remain walkable.
