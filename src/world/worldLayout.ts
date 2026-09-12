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

export const WORLD_BOUNDS = {
  minX: -64,
  maxX: 64,
  minZ: -62,
  maxZ: 78,
} as const;

// Three.js coordinates: +X east, -X west, -Z north, +Z south.
export const PLAYER_START = { x: 0, z: 3.5 } as const;
export const PARK = { x: 0, z: 0, width: 44, depth: 34 } as const;
export const ROAD_WIDTH = 7.5;
export const PAVEMENT_WIDTH = 2.5;

export const WORLD_LOCATIONS: readonly WorldLocation[] = [
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
  { id: 'mcr1', name: 'MCR1', kind: 'building', status: 'geometry-wip', front: 'south', x: -29, z: -36, width: 12, depth: 7, height: 9.8, color: 0x4b5052 },
  { id: 'coral', name: 'Coral', kind: 'building', status: 'finished', front: 'east', x: -39, z: 17, width: 10, depth: 23, height: 13.7, color: 0x51434d },
  { id: 'cass-art', name: 'Cass Art', kind: 'building', status: 'geometry-wip', front: 'north', x: -16.6, z: 39, width: 18.2, depth: 11.93, height: 6.19, color: 0x303538 },

  { id: 'gullivers', name: "Gulliver's Pub", kind: 'building', status: 'geometry-wip', front: 'south', x: 27.9, z: -40, width: 8, depth: 16.6, height: 12.2 },
  { id: 'vinyl-exchange', name: 'Vinyl Exchange', kind: 'building', status: 'placeholder', front: 'south', x: -7, z: 49, width: 12, depth: 10, height: 8.2, color: 0x4b4541 },
  { id: 'car-park', name: 'Car Park', kind: 'car-park', status: 'placeholder', x: 43, z: 0, width: 20, depth: 14, height: 0, color: 0x292c31 },
  { id: 'arts-council', name: 'Arts Council', kind: 'building', status: 'geometry-wip', front: 'west', x: 47, z: 20, width: 20.4, depth: 44.3, height: 33.12, color: 0x4c4548 },

  { id: 'eastern-bloc', name: 'Eastern Bloc', kind: 'building', status: 'placeholder', front: 'north', x: 20, z: 69.75, width: 10, depth: 10, height: 7.8, color: 0x454b50 },
  { id: 'spice-cabin', name: 'Spice Cabin', kind: 'building', status: 'placeholder', front: 'south', x: 10.5, z: 49, width: 11, depth: 10, height: 6.8, color: 0x54493f },
  { id: 'off-licence', name: 'Off-Licence', kind: 'building', status: 'placeholder', front: 'south', x: 22.5, z: 49, width: 11, depth: 10, height: 7.6, color: 0x4e4247 },
  { id: 'real-camera', name: 'Real Camera', kind: 'building', status: 'geometry-wip', front: 'north', x: -11.5, z: 69.75, width: 15.93, depth: 11.36, height: 14.76, color: 0x414a52 },
  { id: 'advanced-photo', name: 'Advanced Photo', kind: 'building', status: 'placeholder', front: 'north', x: 10.5, z: 69.75, width: 9, depth: 10, height: 7, color: 0x3e4b53 },

  { id: 'central-park', name: 'Central Park', kind: 'park', status: 'placeholder', x: PARK.x, z: PARK.z, width: PARK.width, depth: PARK.depth, height: 0, color: 0x263d2b },
] as const;

export const BUS_STOPS: readonly WorldMarker[] = [
  { id: 'bus-stop-a', name: 'Bus Stop A', x: 0, z: 20.4 },
  { id: 'bus-stop-b', name: 'Bus Stop B', x: 0, z: -49 },
] as const;

// Street-food stands: placeable props rather than plots. Greek Gyros sits on
// the park's north pavement directly opposite Renee, backing onto North Road
// with its serving frontage and queue facing into the park. It is set west of
// the existing bollard pair and streetlight at x = 18.5-20.
export const FOOD_STANDS: readonly WorldMarker[] = [
  { id: 'greek-gyros', name: 'Greek Gyros', x: 14, z: -19.35 },
] as const;

export const STERLING_BIKE_DOCKS: readonly WorldMarker[] = [
  { id: 'sterling-bikes-east', name: 'Sterling Bikes East', x: 27, z: 4 },
  { id: 'sterling-bikes-south', name: 'Sterling Bikes South', x: -24, z: 26 },
] as const;

export const FUTURE_EXITS: readonly WorldMarker[] = [
  { id: 'north-road', name: 'North Road', x: 0, z: -59 },
  { id: 'south-road', name: 'South Road', x: 0, z: 75 },
  { id: 'west-exit', name: 'West', x: -61, z: 25.5 },
  { id: 'east-exit', name: 'East', x: 61, z: 0 },
] as const;
