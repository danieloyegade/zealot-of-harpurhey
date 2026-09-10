export type LocationKind = 'building' | 'park' | 'car-park';
export type LocationStatus = 'finished' | 'placeholder';

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
  readonly color: number;
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
  maxZ: 62,
} as const;

// Three.js coordinates: +X east, -X west, -Z north, +Z south.
export const PLAYER_START = { x: 0, z: 21 } as const;
export const PARK = { x: 0, z: 0, width: 44, depth: 34 } as const;
export const ROAD_WIDTH = 7.5;
export const PAVEMENT_WIDTH = 2.5;

export const WORLD_LOCATIONS: readonly WorldLocation[] = [
  { id: 'florist', name: 'Florist', kind: 'building', status: 'finished', front: 'south', x: -16, z: -36, width: 6, depth: 7.5, height: 10.4, color: 0x6f594c },
  { id: 'dreams', name: 'Dreams', kind: 'building', status: 'finished', front: 'south', x: 0, z: -36, width: 18, depth: 8.5, height: 8.3, color: 0x4c4b55 },
  { id: 'renae', name: 'Renae', kind: 'building', status: 'placeholder', front: 'south', x: 17, z: -36, width: 13, depth: 8, height: 8, color: 0x51464c },

  { id: 'come-through-lab', name: 'Come Through Lab', kind: 'building', status: 'placeholder', front: 'east', x: -39, z: -15, width: 10, depth: 10, height: 8, color: 0x414954 },
  { id: 'village-books', name: 'Village Books', kind: 'building', status: 'placeholder', front: 'east', x: -39, z: -3.5, width: 10, depth: 9, height: 7, color: 0x4d4541 },
  { id: 'm1', name: 'M1', kind: 'building', status: 'placeholder', front: 'east', x: -39, z: 7, width: 10, depth: 9, height: 6.5, color: 0x4b5052 },
  { id: 'coral', name: 'Coral', kind: 'building', status: 'placeholder', front: 'east', x: -39, z: 17, width: 10, depth: 8, height: 6.8, color: 0x51434d },
  { id: 'eastern-bloc', name: 'Eastern Bloc', kind: 'building', status: 'placeholder', front: 'east', x: -39, z: 27.5, width: 10, depth: 10, height: 7.8, color: 0x454b50 },

  { id: 'gullivers', name: "Gulliver's Pub", kind: 'building', status: 'placeholder', front: 'west', x: 38, z: -15, width: 9, depth: 11, height: 8.2, color: 0x50433d },
  { id: 'terrace', name: 'Terrace', kind: 'building', status: 'placeholder', front: 'west', x: 48, z: -15, width: 9, depth: 11, height: 8.8, color: 0x413f4e },
  { id: 'car-park', name: 'Car Park', kind: 'car-park', status: 'placeholder', x: 43, z: 0, width: 20, depth: 14, height: 0, color: 0x292c31 },
  { id: 'advanced-photo', name: 'Advanced Photo', kind: 'building', status: 'placeholder', front: 'west', x: 37.5, z: 17, width: 9, depth: 10, height: 7, color: 0x3e4b53 },
  { id: 'arts-council', name: 'Arts Council', kind: 'building', status: 'placeholder', front: 'west', x: 48, z: 22.5, width: 9, depth: 15, height: 8.5, color: 0x4c4548 },

  { id: 'vinyl-exchange', name: 'Vinyl Exchange', kind: 'building', status: 'placeholder', front: 'north', x: -19, z: 39, width: 12, depth: 10, height: 8.2, color: 0x4b4541 },
  { id: 'real-camera', name: 'Real Camera', kind: 'building', status: 'placeholder', front: 'north', x: -5, z: 39, width: 14, depth: 10, height: 7.2, color: 0x414a52 },
  { id: 'spice-cabin', name: 'Spice Cabin', kind: 'building', status: 'placeholder', front: 'north', x: 10, z: 39, width: 11, depth: 10, height: 6.8, color: 0x54493f },
  { id: 'off-licence', name: 'Off-Licence', kind: 'building', status: 'placeholder', front: 'north', x: 23, z: 39, width: 11, depth: 10, height: 7.6, color: 0x4e4247 },

  { id: 'central-park', name: 'Central Park', kind: 'park', status: 'placeholder', x: PARK.x, z: PARK.z, width: PARK.width, depth: PARK.depth, height: 0, color: 0x263d2b },
] as const;

export const BUS_STOPS: readonly WorldMarker[] = [
  { id: 'bus-stop-a', name: 'Bus Stop A', x: -9, z: 20.4 },
  { id: 'bus-stop-b', name: 'Bus Stop B', x: 0, z: -49 },
] as const;

export const STERLING_BIKE_DOCKS: readonly WorldMarker[] = [
  { id: 'sterling-bikes-east', name: 'Sterling Bikes East', x: 27, z: 4 },
  { id: 'sterling-bikes-south', name: 'Sterling Bikes South', x: -24, z: 26 },
] as const;

export const FUTURE_EXITS: readonly WorldMarker[] = [
  { id: 'north-road', name: 'North Road', x: 0, z: -59 },
  { id: 'south-road', name: 'South Road', x: 0, z: 59 },
  { id: 'west-exit', name: 'West', x: -61, z: 25.5 },
  { id: 'east-exit', name: 'East', x: 61, z: 0 },
] as const;
