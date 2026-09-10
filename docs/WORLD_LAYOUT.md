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
- Playable bounds: X -64 to 64; Z -62 to 62
- Main road width: 7.5 m
- Typical pavement width: 2.5 m, widened near building rows where useful
- Central Park: 44 m east-west × 34 m north-south, centred at (0, 0)

At the existing 2.4 m/s walking speed, a direct full-district crossing is roughly 45 seconds. Routes around buildings and across the park make important deliveries meaningful while keeping the district compact.

## Named locations

Coordinates are plot centres. Footprints are X width × Z depth.

| Location | Centre (X, Z) | Footprint | Status / relationship |
| --- | ---: | ---: | --- |
| Florist | (-16, -36) | 6 × 7.5 m | Finished photographic asset; north-west of Dreams |
| Dreams | (0, -36) | 14 × 8 m | North Road landmark placeholder |
| Renae | (17, -36) | 13 × 8 m | North-east row placeholder |
| Come Through Lab | (-39, -15) | 10 × 10 m | Northernmost west-side shop |
| Village Books | (-39, -3.5) | 10 × 9 m | West side, south of Come Through Lab |
| M1 | (-39, 7) | 10 × 9 m | West-side convenience shop |
| Coral | (-39, 17) | 10 × 8 m | West side, south of M1 |
| Eastern Bloc | (-39, 27.5) | 10 × 10 m | Southernmost west-side location |
| Gulliver's Pub | (38, -15) | 9 × 11 m | Upper east side |
| Terrace | (48, -15) | 9 × 11 m | Club east of Gulliver's; not a bicycle shop |
| Car Park | (43, 0) | 20 × 14 m | Open surface between upper and lower east plots |
| Advanced Photo | (37.5, 17) | 9 × 10 m | East-side photo lab; not a bus stop |
| Arts Council | (48, 22.5) | 9 × 15 m | South-east, beside the car-park/service route |
| Vinyl Exchange | (-19, 39) | 12 × 10 m | South Road; first-delivery recipient lives above |
| Real Camera | (-5, 39) | 14 × 10 m | South-side photography shop; distinct from Dreams |
| Spice Cabin | (10, 39) | 11 × 10 m | South-side takeaway |
| Off-Licence | (23, 39) | 11 × 10 m | South-east atmospheric/interior location |
| Central Park | (0, 0) | 44 × 34 m | Geographic anchor and cross-district shortcut |

## Roads, routes and exits

Inner north and south roads run east-west at Z -25.5 and Z 25.5. Inner west and east roads run north-south at X -29.5 and X 29.5. Named building rows sit between this park-facing ring and outer boundary streets at north Z -44.2, south Z 48, west X -48 and east X 57. This prevents outward connections from crossing building plots. The park has perimeter paths and two diagonal crossings so it is a usable pedestrian shortcut rather than an inaccessible island. Cheap primitive trees and benches establish scale without becoming final scenery, and a marked 8 × 6 m area at (12.5, 3) reserves space for the future playground.

Outward future-area markers are:

- North Road: (0, -59)
- South Road: (0, 59)
- West: (-61, 25.5)
- East: (61, 0)

The Arts Council remains directly south-east of the car park. The blockout deliberately leaves public pavement and open car-park space between them, preserving a future route from the formal frontage around to the service/rear area where the sword sequence can occur.

## Player and transport infrastructure

- Player start: (0, 21), on the southern edge of Central Park
- Bus Stop A: (-9, 20.4), close to player start
- Bus Stop B: (0, -49), across outer North Road from Dreams
- Sterling Bikes South dock: (-24, 26)
- Sterling Bikes East dock: (27, 4), near the car park

Both bus stops instance the completed photographic shelter benchmark. The bike docks are development blockout markers only; no bicycle gameplay is implemented.

## Implementation boundaries

Named plots are data-driven in `src/world/worldLayout.ts`. Finished landmark assets can replace their corresponding blockout without changing district topology. For Map v0.3, only the florist and reusable bus shelter are finished assets. All other named buildings, the park landscape, car park, roads, crossings, paths, bike docks, exits and street furniture remain intentionally economical blockouts.

Development labels are created only when `import.meta.env.DEV` is true and are removed from production builds. Building and shelter collision remains two-dimensional axis-aligned bounding boxes. The park, roads, paths, car park and future exits remain walkable.
