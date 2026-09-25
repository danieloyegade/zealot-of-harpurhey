// Road widening: the one place that knows how the city changed when its roads
// grew from 7.5 m to double-decker width (10 m; Quay Street 15 m; Lower Byrom
// Street 9 m).
//
// Every coordinate in the world's authoring tables and hand-placed props was
// written against the original 7.5 m roads, and those numbers are kept as
// written. `wideX`, `wideZ`, `widePoint` and `wideRect` carry an authored
// coordinate into the widened city:
//
//   - The park, its paths and pavements, and the player start do not move.
//   - Each road grows away from the park, so the blocks between roads keep
//     their shape and their distance from the kerb they front and are simply
//     pushed outward, rigidly, by the total growth of the roads between them
//     and the park. Nothing inside a block is stretched.
//   - A coordinate that lies on a road is stretched in proportion across the
//     road's new width, so kerb lines, crossings and centre lines stay put
//     relative to the carriageway.
//   - The ring roads' side streets (X = +-29.5) only exist for |Z| <= 33, so
//     the north and south blocks (which sit beyond the ring's ends) are not
//     pushed sideways by them, only the outer streets move.
//
// Positions produced here are the ones the game uses; authoring coordinates
// are only ever passed in, never read back.

export const OLD_ROAD_WIDTH = 7.5;
/** Ring and outer streets: two double-deckers pass with room for a kerbside stop. */
export const ROAD_WIDTH = 10;
/** Quay Street (the Outer North Road, the ABC Building's frontage). */
export const QUAY_STREET_WIDTH = 15;
/** Lower Byrom Street: a side street north of Quay Street. */
export const LOWER_BYROM_WIDTH = 9;

interface AuthoredRoad {
  /** Authored centre line. */
  readonly centre: number;
  /** New carriageway width. */
  readonly width: number;
  /** Only present for rows/columns inside the ring, |other axis| <= RING_HALF_EXTENT. */
  readonly ringOnly?: boolean;
}

interface Stretch {
  readonly lo: number;
  readonly hi: number;
  readonly newLo: number;
  readonly newHi: number;
  readonly ringOnly: boolean;
}

// The ring's side streets end at Z = +-33 (their authored half-length).
const RING_HALF_EXTENT = 33;
const OLD_HALF = OLD_ROAD_WIDTH / 2;

// Roads on one side of the park, nearest first. `sign` is the direction away
// from the park. The near (park-side) edge shifts by the growth already
// accumulated by the roads inside it; the far edge is one new width beyond.
function outwardStretches(roads: readonly AuthoredRoad[], sign: 1 | -1): Stretch[] {
  const stretches: Stretch[] = [];
  let growth = 0;
  for (const road of roads) {
    const near = road.centre - sign * OLD_HALF;
    const far = road.centre + sign * OLD_HALF;
    const newNear = near + sign * growth;
    const newFar = newNear + sign * road.width;
    stretches.push({
      lo: Math.min(near, far),
      hi: Math.max(near, far),
      newLo: Math.min(newNear, newFar),
      newHi: Math.max(newNear, newFar),
      ringOnly: road.ringOnly === true,
    });
    growth += road.width - OLD_ROAD_WIDTH;
  }
  return stretches;
}

// Streets running east-west (they set Z). Nearest the park first.
const Z_SOUTH = outwardStretches(
  [{ centre: 25.5, width: ROAD_WIDTH }, { centre: 59.5, width: ROAD_WIDTH }],
  1,
);
const Z_NORTH = outwardStretches(
  [{ centre: -25.5, width: ROAD_WIDTH }, { centre: -54.2, width: QUAY_STREET_WIDTH }],
  -1,
);
// Streets running north-south (they set X). The two inner ones exist only for
// |Z| <= 33; the outer streets run the whole depth of the map.
const X_EAST = outwardStretches(
  [{ centre: 29.5, width: ROAD_WIDTH, ringOnly: true }, { centre: 57, width: ROAD_WIDTH }],
  1,
);
const X_WEST = outwardStretches(
  [{ centre: -29.5, width: ROAD_WIDTH, ringOnly: true }, { centre: -48, width: ROAD_WIDTH }],
  -1,
);

// Snaps a coordinate that sits on a road's edge (a kerb, a pavement edge) to
// that edge rather than the block beside it.
const EDGE_TOLERANCE = 0.02;

function mapAxis(
  value: number,
  towardPositive: readonly Stretch[],
  towardNegative: readonly Stretch[],
  includeRingOnly: boolean,
): number {
  const positive = value >= 0;
  let shift = 0;
  for (const stretch of positive ? towardPositive : towardNegative) {
    if (stretch.ringOnly && !includeRingOnly) {
      continue;
    }
    // Still on the park side of this road: the block beside it.
    if (positive ? value < stretch.lo - EDGE_TOLERANCE : value > stretch.hi + EDGE_TOLERANCE) {
      return value + shift;
    }
    // On the road: stretch across its new width.
    if (value >= stretch.lo - EDGE_TOLERANCE && value <= stretch.hi + EDGE_TOLERANCE) {
      const t = (value - stretch.lo) / (stretch.hi - stretch.lo);
      return stretch.newLo + t * (stretch.newHi - stretch.newLo);
    }
    // Past this road: everything beyond moves out by its growth so far.
    shift = positive ? stretch.newHi - stretch.hi : stretch.newLo - stretch.lo;
  }
  return value + shift;
}

/** Widened Z for an authored Z. */
export function wideZ(z: number): number {
  return mapAxis(z, Z_SOUTH, Z_NORTH, true);
}

/**
 * Widened X for an authored X. `authoredZ` selects the row: inside the ring
 * (|Z| <= 33) the inner side streets push the blocks beside them outward;
 * beyond it only the outer streets do.
 */
export function wideX(x: number, authoredZ: number): number {
  return mapAxis(x, X_EAST, X_WEST, Math.abs(authoredZ) <= RING_HALF_EXTENT);
}

export function widePoint(x: number, z: number): { x: number; z: number } {
  return { x: wideX(x, z), z: wideZ(z) };
}

export interface Rect {
  readonly x: number;
  readonly z: number;
  readonly width: number;
  readonly depth: number;
}

/**
 * Widened rectangle for a span (a road, a pavement, a ground plane): its edges
 * move independently, so a span that runs between two roads grows to meet
 * them. Use `widePoint` on a centre instead for buildings and props, which keep
 * their size.
 */
export function wideRect(rect: Rect): Rect {
  const west = wideX(rect.x - rect.width / 2, rect.z);
  const east = wideX(rect.x + rect.width / 2, rect.z);
  const north = wideZ(rect.z - rect.depth / 2);
  const south = wideZ(rect.z + rect.depth / 2);
  return {
    x: (west + east) / 2,
    z: (north + south) / 2,
    width: east - west,
    depth: south - north,
  };
}

/**
 * Widened rectangle whose cross-axis (the direction across the carriageway) is
 * set explicitly instead of by the grid above; for the side and outward roads
 * that are not part of it. `anchor` keeps the road's low edge, high edge or
 * centre where the grid puts it.
 */
export function wideSideRoad(
  rect: Rect,
  across: 'x' | 'z',
  newWidth: number,
  anchor: 'centre' | 'low' | 'high' = 'centre',
): Rect {
  const moved = wideRect(rect);
  const low = across === 'x' ? moved.x - moved.width / 2 : moved.z - moved.depth / 2;
  const high = across === 'x' ? moved.x + moved.width / 2 : moved.z + moved.depth / 2;
  const centre = anchor === 'low' ? low + newWidth / 2 : anchor === 'high' ? high - newWidth / 2 : (low + high) / 2;
  return across === 'x'
    ? { ...moved, x: centre, width: newWidth }
    : { ...moved, z: centre, depth: newWidth };
}
