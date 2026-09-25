import {
  LOWER_BYROM_WIDTH,
  OLD_ROAD_WIDTH,
  ROAD_WIDTH as WIDENED_ROAD_WIDTH,
  widePoint,
  wideX,
  wideZ,
} from './roadWidening.ts';

export type LocationKind = 'building' | 'park' | 'car-park';
export type LocationStatus = 'finished' | 'geometry-wip' | 'placeholder';

export interface WorldLocation {
  readonly id: string;
  readonly name: string;
  readonly kind: LocationKind;
  readonly status: LocationStatus;
  readonly front?: 'north' | 'south' | 'east' | 'west';
  readonly x: number;
  readonly z: number;
  readonly width: number;
  readonly depth: number;
  readonly height: number;
  readonly color?: number;
}

export interface WorldMarker {
  readonly id: string;
  readonly name: string;
  readonly x: number;
  readonly z: number;
}

// Coordinates in this file, and in the hand-placed props elsewhere, are
// authored against the original 7.5 m roads and carried into the widened city
// by `roadWidening.ts`; see its header. The exports here are the widened ones.
export const WORLD_BOUNDS = {
  minX: wideX(-64, 0),
  maxX: wideX(64, 0),
  // Extended north for the ABC Building block on the far side of the Outer
  // North Road: its tower, rear wing and Lower Byrom Street reach Z ≈ -110
  // (authored), before the roads were widened.
  minZ: wideZ(-116),
  maxZ: wideZ(78),
} as const;

// Three.js coordinates: +X east, -X west, -Z north, +Z south.
export const PLAYER_START = { x: 0, z: 3.5 } as const;
export const PARK = { x: 0, z: 0, width: 44, depth: 34 } as const;
export const ROAD_WIDTH = WIDENED_ROAD_WIDTH;
export const PAVEMENT_WIDTH = 2.5;

// ABC Building GLB origin: its ground-level Quay Street / Lower Byrom Street
// corner. The Quay Street frontage (Blender -Y) imports facing +Z, so it faces
// south across the Outer North Road, 6 m of pavement back from the kerb
// (Z = -57.95). The 61.9 m frontage runs west from here to X = -42.25, 2 m
// short of the outer west street; Lower Byrom Street runs north past the
// corner's east side, 3 m of pavement away.
const AUTHORED_ABC_BUILDING_CORNER = { x: 19.65, z: -63.95 } as const;
export const ABC_BUILDING_CORNER = widePoint(
  AUTHORED_ABC_BUILDING_CORNER.x,
  AUTHORED_ABC_BUILDING_CORNER.z,
);

const AUTHORED_LOCATIONS: readonly WorldLocation[] = [
  { id: 'florist', name: 'Nice Things', kind: 'building', status: 'geometry-wip', front: 'south', x: -16.9, z: -32, width: 6, depth: 7.5, height: 14.55, color: 0xb56f72 },
  { id: 'dreams', name: 'Dreams', kind: 'building', status: 'finished', front: 'north', x: 1.5, z: 39, width: 18, depth: 8.5, height: 8.3, color: 0x4c4b55 },
  { id: 'renae', name: 'Renee', kind: 'building', status: 'geometry-wip', front: 'south', x: 17, z: -38.6, width: 13.8, depth: 13.2, height: 10.65, color: 0x51464c },

  // width is the east-west extent and depth the north-south one for every
  // location, independent of `front`. Come Through Lab is authored 6.0 m deep
  // with a 9.7 m frontage, and x places its east face on the -34 building line
  // shared with Village Books and Coral rather than 2 m behind it.
  { id: 'come-through-lab', name: 'Come Through Lab', kind: 'building', status: 'geometry-wip', front: 'east', x: -37, z: -15, width: 6.0, depth: 9.7, height: 7.15, color: 0x414954 },
  // The rotated GLB measures 8.24 m east-west (including the projecting
  // fascia) by 7.88 m north-south. Its east shopfront stays on X = -34,
  // continuing the west-side building line shared with Come Through Lab.
  { id: 'village-books', name: 'Village Books', kind: 'building', status: 'geometry-wip', front: 'east', x: -38.12, z: -3.5, width: 8.24, depth: 7.88, height: 10.2, color: 0x4d4541 },
  { id: 'mcr1', name: 'MCR1', kind: 'building', status: 'finished', front: 'south', x: -29, z: -36, width: 12, depth: 7, height: 9.8, color: 0x4b5052 },
  { id: 'coral', name: 'Coral', kind: 'building', status: 'finished', front: 'east', x: -39, z: 17, width: 10, depth: 23, height: 13.7, color: 0x51434d },
  { id: 'cass-art', name: 'Cass Art', kind: 'building', status: 'finished', front: 'north', x: -16.6, z: 39, width: 18.2, depth: 11.93, height: 6.19, color: 0x303538 },

  { id: 'gullivers', name: "Gulliver's Pub", kind: 'building', status: 'geometry-wip', front: 'south', x: 27.9, z: -40, width: 8, depth: 16.6, height: 12.2 },
  // Authored body footprint: the Oldham Street frontage faces south on Z = 54,
  // while the perpendicular Dale Street return faces east into the open gap.
  // Fascia, piers and cornice project by up to about 0.5 m beyond this envelope.
  { id: 'vinyl-exchange', name: 'Vinyl Exchange', kind: 'building', status: 'geometry-wip', front: 'south', x: -7, z: 48.43, width: 7.44, depth: 11.14, height: 14.45, color: 0x4b4541 },
  { id: 'car-park', name: 'Car Park', kind: 'car-park', status: 'placeholder', x: 43, z: 0, width: 20, depth: 14, height: 0, color: 0x292c31 },
  { id: 'arts-council', name: 'Arts Council', kind: 'building', status: 'geometry-wip', front: 'west', x: 47, z: 20, width: 20.4, depth: 44.3, height: 33.12, color: 0x4c4548 },

  { id: 'eastern-bloc', name: 'Eastern Bloc', kind: 'building', status: 'placeholder', front: 'north', x: 20, z: 69.75, width: 10, depth: 10, height: 7.8, color: 0x454b50 },
  // The 6.2 × 7.0 × 5.1 m GLB at SPICE_CABIN_SCALE (1.5), depth stretched to
  // 10 m. Its east party wall (which has no exterior face) is closed by a brick
  // skin at X = 17 (addSpiceCabinPartyWall), and its shopfront stays on the
  // Z = 54 building line.
  { id: 'spice-cabin', name: 'Spice Cabin', kind: 'building', status: 'finished', front: 'south', x: 12.35, z: 49, width: 9.3, depth: 10, height: 7.65, color: 0x54493f },
  { id: 'real-camera', name: 'Real Camera', kind: 'building', status: 'geometry-wip', front: 'north', x: -11.5, z: 69.75, width: 15.93, depth: 11.36, height: 14.76, color: 0x414a52 },
  // The authored shop body is 5.8 × 6.2 m. Its centre preserves the old
  // placeholder's north frontage plane at Z = 64.75, while its east wall
  // remains attached to Eastern Bloc at X = 15. The GLB's surrounding arcade
  // connector extends outside this collision footprint toward the west.
  { id: 'advanced-photo', name: 'Advanced Photo', kind: 'building', status: 'geometry-wip', front: 'north', x: 12.1, z: 67.85, width: 5.8, depth: 6.2, height: 3.55, color: 0x3e4b53 },

  // Footprint of the podium and tower (61.9 m x 22 m, 60 m to the core top).
  // The rear wing continues 24 m further north along Lower Byrom Street.
  { id: 'abc-building', name: 'ABC Building (Clints, Side Street)', kind: 'building', status: 'geometry-wip', front: 'south', x: AUTHORED_ABC_BUILDING_CORNER.x - 30.95 + 0.275, z: AUTHORED_ABC_BUILDING_CORNER.z - 10.975, width: 62.45, depth: 21.95, height: 60, color: 0xb9b8b2 },

  { id: 'central-park', name: 'Central Park', kind: 'park', status: 'placeholder', x: PARK.x, z: PARK.z, width: PARK.width, depth: PARK.depth, height: 0, color: 0x263d2b },
] as const;

export const WORLD_LOCATIONS: readonly WorldLocation[] = AUTHORED_LOCATIONS.map((location) => ({
  ...location,
  ...widePoint(location.x, location.z),
}));

// Carries an authored marker into the widened city.
function widen<T extends { readonly x: number; readonly z: number }>(marker: T): T {
  return { ...marker, ...widePoint(marker.x, marker.z) };
}

const AUTHORED_BUS_STOPS: readonly WorldMarker[] = [
  // Centred on the 3.6 m park south pavement: the whole footprint stays on the
  // flags and the roof's front edge is 0.63 m back from the kerb.
  { id: 'bus-stop-a', name: 'Bus Stop A', x: 0, z: 20.0 },
  // On the ABC Building's Quay Street pavement, centred on the Every Man block
  // at its west end: about 2.5 m clear of the building's west end and of the
  // ABC blade sign, with the trolley at the kerb line and ~3.5 m of pavement behind.
  { id: 'bus-stop-b', name: 'Bus Stop B', x: -36.5, z: -59.8 },
] as const;

export const BUS_STOPS: readonly WorldMarker[] = AUTHORED_BUS_STOPS.map(widen);

export interface FoodStandMarker extends WorldMarker {
  /** Yaw applied to the authored +Z serving frontage. */
  readonly rotationY: number;
}

// Street-food stands: placeable props rather than plots. Greek Gyros sits just
// inside the park's east edge, across Lever Street from the Arts Council
// entrance (world Z ≈ 15.3). Its back is flush with the park edge at X = 22 and
// its serving frontage faces west into the park, over the east path. The
// footprint stops short of the south path at Z = 14.45.
const AUTHORED_FOOD_STANDS: readonly FoodStandMarker[] = [
  { id: 'greek-gyros', name: 'Greek Gyros', x: 20.6, z: 10.5, rotationY: -Math.PI / 2 },
] as const;

export const FOOD_STANDS: readonly FoodStandMarker[] = AUTHORED_FOOD_STANDS.map(widen);

export interface SterlingStationMarker extends WorldMarker {
  /** Yaw applied to the authored +X bike-forward axis; docks line up along local Z. */
  readonly rotationY: number;
  /** One entry per dock, in order along local Z. `false` leaves that dock empty. */
  readonly occupancy: readonly boolean[];
}

// Sterling Bikes docking stations. Each marker is the centre of the dock line.
// The earlier markers (27, 4) and (-24, 26) stood in the East and South
// perimeter carriageways. South now sits on the 3.6 m park south pavement:
// the dock baseplates stop 0.14 m short of the kerb, the bikes point south into
// them, and about 1.35 m of footway stays clear along the park verge. East
// sits in the car park's northern bay, the only open part of it (the Arts
// Council footprint covers Z >= -2.15). Docks line up east-west at Z = -6.3,
// bikes point north into them, rear wheels stopping 0.35 m short of the bay
// marker at Z = -4.2, with one dock left empty.
const AUTHORED_STERLING_BIKE_DOCKS: readonly SterlingStationMarker[] = [
  { id: 'sterling-bikes-east', name: 'Sterling Bikes East', x: 38.5, z: -6.3, rotationY: Math.PI / 2, occupancy: [true, true, false] },
  { id: 'sterling-bikes-south', name: 'Sterling Bikes South', x: -20.5, z: 21.2, rotationY: -Math.PI / 2, occupancy: [true, true, true] },
] as const;

export const STERLING_BIKE_DOCKS: readonly SterlingStationMarker[] = AUTHORED_STERLING_BIKE_DOCKS.map(widen);

export interface PalletStackMarker extends WorldMarker {
  /** Yaw applied to both pallets; the brown pallet keeps its small relative twist. */
  readonly rotationY: number;
}

// Matching blue-under-brown stacks used as ordinary service-area dressing.
// They stay off pavements and entrances: beside the Florist, in the gap north
// of Coral, and along the Arts Council edge of the open car-park bay.
const AUTHORED_PALLET_STACKS: readonly PalletStackMarker[] = [
  { id: 'florist-side-pallets', name: 'Florist east-side pallet stack', x: -12.8, z: -35, rotationY: Math.PI / 2 },
  { id: 'coral-north-pallets', name: 'Coral north pallet stack', x: -38.5, z: 4.35, rotationY: 0 },
  { id: 'arts-council-pallets', name: 'Arts Council car-park pallet stack', x: 48, z: -3.4, rotationY: 0 },
] as const;

export const PALLET_STACKS: readonly PalletStackMarker[] = AUTHORED_PALLET_STACKS.map(widen);

// The bougainvillea fence scene (docs/assets/bougainvillea-fence.md) closes
// the ground-level gap between Village Books' south wall (Z = 0.44) and
// Coral's north brick (Z = 5.75), set back behind the Coral north pallet
// stack (X -39.7 to -37.3, Z 3.35 to 5.35). Daniel asked for it 30% larger
// than authored, so the fence is 2.34 m tall. The 4.68 m hero section starts at
// Village Books; the extension runs on into Coral's wall, of which only 0.63 m
// shows. The signpost stands in front of the fence and north of the pallets.
// The GLBs face +Z, so a quarter turn faces them east toward the street.
const AUTHORED_BOUGAINVILLEA_FENCE_SCENE = {
  scale: 1.3,
  rotationY: Math.PI / 2,
  hero: { x: -40.3, z: 2.78 },
  extension: { x: -40.3, z: 6.29 },
  signpost: { x: -38.94, z: 2.3 },
  gap: { minZ: 0.44, maxZ: 5.75 },
} as const;

export const BOUGAINVILLEA_FENCE_SCENE = {
  ...AUTHORED_BOUGAINVILLEA_FENCE_SCENE,
  hero: widen(AUTHORED_BOUGAINVILLEA_FENCE_SCENE.hero),
  extension: widen(AUTHORED_BOUGAINVILLEA_FENCE_SCENE.extension),
  signpost: widen(AUTHORED_BOUGAINVILLEA_FENCE_SCENE.signpost),
  // Inside the ring rows, so Z is unchanged.
  gap: { minZ: wideZ(AUTHORED_BOUGAINVILLEA_FENCE_SCENE.gap.minZ), maxZ: wideZ(AUTHORED_BOUGAINVILLEA_FENCE_SCENE.gap.maxZ) },
} as const;

export type SpecterVariant = 'specter-haze-pair' | 'specter-drip-trio' | 'specter-outline';

export interface SpecterGraffitiMarker extends WorldMarker {
  readonly variant: SpecterVariant;
  /** Yaw of the painted face's outward normal; 0 faces +Z (south). */
  readonly rotationY: number;
  /** Height of the texture's bottom edge above the ground. */
  readonly y: number;
  /** Painted extent in metres; the textures are authored 2:3. */
  readonly width: number;
  readonly height: number;
}

// Spray-painted specters: Daniel's recurring painting motif of long upright
// figures with two dot eyes, scattered over walls around the city. x/z is the
// centre of the painted area on the wall surface itself; the decal is pushed
// a few millimetres off it at build time. Textures come from
// scripts/generateSpecterTextures.mjs.
const AUTHORED_SPECTER_GRAFFITI: readonly SpecterGraffitiMarker[] = [
  // Dreams' rear wall (Z = 43.25, dark grey render) where it faces the open gap
  // between Vinyl Exchange's Dale Street return (X = -3.28) and Spice Cabin
  // (X = 7.7). Visible from Oldham Street looking north up the gap.
  { id: 'specter-dreams-rear', name: 'Dreams rear wall specters', variant: 'specter-haze-pair', x: 2.2, z: 43.25, y: 0.12, rotationY: 0, width: 2.8, height: 4.2 },
] as const;

export const SPECTER_GRAFFITI: readonly SpecterGraffitiMarker[] = AUTHORED_SPECTER_GRAFFITI.map(widen);

const AUTHORED_FUTURE_EXITS: readonly WorldMarker[] = [
  { id: 'north-road', name: 'North Road', x: 26.4, z: -112 },
  { id: 'south-road', name: 'South Road', x: 0, z: 75 },
  { id: 'west-exit', name: 'West', x: -61, z: 25.5 },
  { id: 'east-exit', name: 'East', x: 61, z: 0 },
] as const;

export const FUTURE_EXITS: readonly WorldMarker[] = AUTHORED_FUTURE_EXITS.map((marker) =>
  marker.id === 'north-road'
    // Lower Byrom Street keeps its ABC-side kerb and is wider on the other.
    ? { ...widen(marker), x: marker.x + (LOWER_BYROM_WIDTH - OLD_ROAD_WIDTH) / 2 }
    : widen(marker),
);
