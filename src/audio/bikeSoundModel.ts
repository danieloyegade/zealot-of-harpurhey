/** What the ridden bike is doing, as far as the ear is concerned. */
export interface BikeSoundInput {
  /** Signed forward speed, m/s. */
  readonly speed: number;
  /** 0..1, smoothed: how much the rider is pedalling. */
  readonly pedalling: number;
  /** 0..1, smoothed: how much the e-assist motor is driving. */
  readonly motorAssist: number;
  readonly braking: boolean;
}

/** Target level and pitch of each synthesised layer for one moment of riding. */
export interface BikeSoundLevels {
  readonly tyreGain: number;
  readonly tyreCentreHz: number;
  readonly windGain: number;
  readonly windCutoffHz: number;
  readonly ratchetGain: number;
  readonly ratchetRateHz: number;
  readonly chainGain: number;
  readonly motorGain: number;
  readonly motorHz: number;
  readonly squealGain: number;
}

// Space boost speed (STERLING_BOOST_SPEED); kept local so this file stays
// free of the bike's three.js imports and can be unit-tested directly.
const TOP_SPEED = 20;
// A hub freewheel engages about 19 times a wheel turn; the wheel is ~2.1 m round.
const RATCHET_CLICKS_PER_METRE = 9;
const MINIMUM_RATCHET_HZ = 6;
// Below this the bike is walked or rolling to a stop, and the layers fade out.
const AUDIBLE_SPEED = 0.15;

const clamp01 = (value: number): number => Math.min(1, Math.max(0, value));

export const SILENT_BIKE: BikeSoundLevels = {
  tyreGain: 0,
  tyreCentreHz: 500,
  windGain: 0,
  windCutoffHz: 800,
  ratchetGain: 0,
  ratchetRateHz: MINIMUM_RATCHET_HZ,
  chainGain: 0,
  motorGain: 0,
  motorHz: 200,
  squealGain: 0,
};

/**
 * Maps riding state to the synthesised layers: tyre hiss and wind that build
 * with speed, the freewheel ratchet while coasting, chain whirr while pedalling,
 * the e-assist motor's whine, and a squeal under hard braking.
 */
export function bikeSoundLevels(input: BikeSoundInput): BikeSoundLevels {
  const speed = Math.max(0, input.speed);
  if (speed < AUDIBLE_SPEED) return SILENT_BIKE;

  const presence = clamp01(speed / 1.2);
  const speedFraction = clamp01(speed / TOP_SPEED);
  const coasting = 1 - input.pedalling;

  return {
    tyreGain: 0.09 * presence * Math.pow(clamp01(speed / 7), 0.7),
    tyreCentreHz: 380 + speed * 70,
    windGain: 0.16 * speedFraction * speedFraction,
    windCutoffHz: 600 + speedFraction * 2600,
    ratchetGain: 0.055 * presence * coasting,
    ratchetRateHz: Math.max(MINIMUM_RATCHET_HZ, speed * RATCHET_CLICKS_PER_METRE),
    chainGain: 0.028 * presence * input.pedalling,
    motorGain: 0.02 * presence * input.motorAssist,
    motorHz: 200 + speed * 55,
    squealGain: input.braking ? 0.05 * clamp01((speed - 1.2) / 5) : 0,
  };
}
