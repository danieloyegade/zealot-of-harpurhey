// What the title card knows of this rider's Harperhey.
//
// Nothing in the game writes most of this yet. Missing fields fall back to a
// first night, so delivery, photography and transport systems can later record
// into the same stored object and the title card will simply start showing it.

export const RIDER_RECORD_STORAGE_KEY = 'zealot-of-harperhey:rider-record';

export interface RiderRecord {
  /** Times the player has entered the city from the title card. */
  readonly entries: number;
  readonly night: number;
  readonly deliveriesCompleted: number;
  readonly deliveriesAssigned: number;
  readonly balancePence: number;
  readonly filmExposed: number;
  readonly filmCapacity: number;
  readonly busServiceActive: boolean;
  readonly swordAcquired: boolean;
}

export const FIRST_NIGHT: RiderRecord = {
  entries: 0,
  night: 1,
  deliveriesCompleted: 0,
  deliveriesAssigned: 3,
  balancePence: 482,
  filmExposed: 0,
  filmCapacity: 36,
  busServiceActive: false,
  swordAcquired: false,
};

// Worn by the rider, as a collection record (docs/ART_DIRECTION.md, "Player
// Character Fashion"). The delivery bag is listed with carried objects instead.
export const RIDER_GARMENTS: readonly (readonly [garment: string, quality: string])[] = [
  ['Denim jacket', 'Oversized'],
  ['Denim jeans', 'Oversized'],
  ['Trainers', 'Silver'],
  ['Greaves', 'Steel'],
];

export function readRiderRecord(): RiderRecord {
  const stored = readStoredRecord();
  const record: Record<string, unknown> = { ...FIRST_NIGHT };
  for (const key of Object.keys(FIRST_NIGHT) as (keyof RiderRecord)[]) {
    if (typeof stored[key] === typeof FIRST_NIGHT[key]) record[key] = stored[key];
  }
  return record as unknown as RiderRecord;
}

/** Counts one entry into the city, leaving every other stored field as it was. */
export function recordEntry(): void {
  const stored = readStoredRecord();
  const entries = typeof stored.entries === 'number' ? stored.entries : 0;
  try {
    localStorage.setItem(RIDER_RECORD_STORAGE_KEY, JSON.stringify({ ...stored, entries: entries + 1 }));
  } catch {
    // Storage unavailable (private window, blocked site data): this entry goes unrecorded.
  }
}

function readStoredRecord(): Record<string, unknown> {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(RIDER_RECORD_STORAGE_KEY) ?? 'null');
    return value && typeof value === 'object' && !Array.isArray(value)
      ? (value as Record<string, unknown>)
      : {};
  } catch {
    return {};
  }
}
