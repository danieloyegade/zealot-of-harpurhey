import {
  bikeSoundLevels,
  SILENT_BIKE,
  type BikeSoundInput,
  type BikeSoundLevels,
} from './bikeSoundModel';

const FOOTSTEP_CLIPS = [0, 1, 2, 3, 4].map(
  (index) => `${import.meta.env.BASE_URL}assets/audio/footsteps/footstep-concrete-00${index}.wav`,
);

const MASTER_GAIN = 0.9;
const WALK_STEP_GAIN = 0.3;
const RUN_STEP_GAIN = 0.46;
// The heavy jeans and boots: each step also plays a slowed, low-passed copy
// underneath, so it lands with weight rather than as a click.
const THUD_RATE = 0.58;
const THUD_CUTOFF_HZ = 320;
const THUD_GAIN = 0.85;
// Smoothing for bike layer changes, seconds. Short enough to follow the
// throttle, long enough not to zipper.
const BIKE_SMOOTHING = 0.07;

interface BikeVoice {
  readonly tyreFilter: BiquadFilterNode;
  readonly tyreGain: GainNode;
  readonly windFilter: BiquadFilterNode;
  readonly windGain: GainNode;
  readonly ratchet: OscillatorNode;
  readonly ratchetGain: GainNode;
  readonly chainGain: GainNode;
  readonly motor: OscillatorNode;
  readonly motorGain: GainNode;
  readonly squealGain: GainNode;
}

/**
 * Footsteps from recorded clips, and the ridden bike synthesised live from its
 * speed, pedalling and braking. Browsers only let audio start after a gesture,
 * so nothing is built until the first key press or click.
 */
export class MovementAudio {
  private context: AudioContext | null = null;
  private master: GainNode | null = null;
  private analyser: AnalyserNode | null = null;
  private steps: AudioBuffer[] = [];
  private lastStep = -1;
  private bike: BikeVoice | null = null;
  private bikeState: BikeSoundLevels = SILENT_BIKE;
  private noise: AudioBuffer | null = null;

  constructor() {
    window.addEventListener('keydown', this.unlock);
    window.addEventListener('pointerdown', this.unlock);
    document.addEventListener('visibilitychange', this.handleVisibility);
  }

  /** A foot has landed. Called from the player's walk cycle. */
  footfall(running: boolean): void {
    const context = this.context;
    const master = this.master;
    if (!context || !master || context.state !== 'running' || this.steps.length === 0) return;

    let index = Math.floor(Math.random() * this.steps.length);
    if (index === this.lastStep) index = (index + 1) % this.steps.length;
    this.lastStep = index;

    const buffer = this.steps[index];
    const level = (running ? RUN_STEP_GAIN : WALK_STEP_GAIN) * (0.85 + Math.random() * 0.3);
    const rate = (running ? 1.04 : 0.97) * (0.94 + Math.random() * 0.12);
    const now = context.currentTime;

    const strike = context.createBufferSource();
    strike.buffer = buffer;
    strike.playbackRate.value = rate;
    const strikeGain = context.createGain();
    strikeGain.gain.value = level;
    strike.connect(strikeGain).connect(master);
    strike.start(now);

    const thud = context.createBufferSource();
    thud.buffer = buffer;
    thud.playbackRate.value = THUD_RATE * (0.95 + Math.random() * 0.1);
    const thudFilter = context.createBiquadFilter();
    thudFilter.type = 'lowpass';
    thudFilter.frequency.value = THUD_CUTOFF_HZ;
    const thudGain = context.createGain();
    thudGain.gain.value = level * THUD_GAIN;
    thud.connect(thudFilter).connect(thudGain).connect(master);
    thud.start(now);
  }

  /** Once a frame: the bike being ridden, or null when on foot. */
  updateBike(bike: BikeSoundInput | null): void {
    const context = this.context;
    if (!context || context.state !== 'running') return;
    if (bike && !this.bike) this.bike = this.buildBikeVoice(context);
    const voice = this.bike;
    if (!voice) return;

    const levels = bike ? bikeSoundLevels(bike) : SILENT_BIKE;
    this.bikeState = levels;
    const now = context.currentTime;
    const ease = (parameter: AudioParam, value: number): void => {
      parameter.setTargetAtTime(value, now, BIKE_SMOOTHING);
    };
    ease(voice.tyreGain.gain, levels.tyreGain);
    ease(voice.tyreFilter.frequency, levels.tyreCentreHz);
    ease(voice.windGain.gain, levels.windGain);
    ease(voice.windFilter.frequency, levels.windCutoffHz);
    ease(voice.ratchetGain.gain, levels.ratchetGain);
    ease(voice.ratchet.frequency, levels.ratchetRateHz);
    ease(voice.chainGain.gain, levels.chainGain);
    ease(voice.motorGain.gain, levels.motorGain);
    ease(voice.motor.frequency, levels.motorHz);
    ease(voice.squealGain.gain, levels.squealGain);
  }

  /** The bike layer targets last applied; for inspection and tests. */
  get bikeLevels(): BikeSoundLevels {
    return this.bikeState;
  }

  /** RMS of everything this class is currently playing, 0..1. */
  outputLevel(): number {
    const analyser = this.analyser;
    if (!analyser) return 0;
    const samples = new Float32Array(analyser.fftSize);
    analyser.getFloatTimeDomainData(samples);
    let sum = 0;
    for (const sample of samples) sum += sample * sample;
    return Math.sqrt(sum / samples.length);
  }

  private readonly unlock = (): void => {
    if (this.context) {
      void this.context.resume();
      return;
    }
    try {
      const context = new AudioContext();
      const master = context.createGain();
      master.gain.value = MASTER_GAIN;
      const analyser = context.createAnalyser();
      master.connect(analyser);
      master.connect(context.destination);
      this.context = context;
      this.master = master;
      this.analyser = analyser;
      this.noise = createNoise(context);
      void context.resume();
      void this.loadSteps(context);
    } catch {
      // Web Audio unavailable: the game is simply quiet underfoot.
    }
  };

  private readonly handleVisibility = (): void => {
    const context = this.context;
    if (!context) return;
    // Frames stop in a hidden tab, so the bike voice would hold its last level.
    if (document.hidden) void context.suspend();
    else void context.resume();
  };

  private async loadSteps(context: AudioContext): Promise<void> {
    const decoded = await Promise.all(
      FOOTSTEP_CLIPS.map(async (url) => {
        try {
          const response = await fetch(url);
          if (!response.ok) return null;
          return await context.decodeAudioData(await response.arrayBuffer());
        } catch {
          return null;
        }
      }),
    );
    this.steps = decoded.filter((buffer): buffer is AudioBuffer => buffer !== null);
  }

  private buildBikeVoice(context: AudioContext): BikeVoice | null {
    const master = this.master;
    const noise = this.noise;
    if (!master || !noise) return null;

    const noiseSource = (): AudioBufferSourceNode => {
      const source = context.createBufferSource();
      source.buffer = noise;
      source.loop = true;
      // Each layer reads the shared noise from a different point.
      source.start(0, Math.random() * noise.duration);
      return source;
    };
    const gainAt = (value: number): GainNode => {
      const gain = context.createGain();
      gain.gain.value = value;
      return gain;
    };
    const filter = (type: BiquadFilterType, hz: number, q: number): BiquadFilterNode => {
      const node = context.createBiquadFilter();
      node.type = type;
      node.frequency.value = hz;
      node.Q.value = q;
      return node;
    };

    // Tyre on tarmac: band-limited hiss that rises in pitch with speed.
    const tyreFilter = filter('bandpass', 500, 0.7);
    const tyreGain = gainAt(0);
    noiseSource().connect(tyreFilter).connect(tyreGain).connect(master);

    // Wind past the ears, only really there when boosting.
    const windFilter = filter('lowpass', 800, 0.4);
    const windGain = gainAt(0);
    noiseSource().connect(windFilter).connect(windGain).connect(master);

    // Freewheel ratchet: a narrow pulse train at the pawl rate, kept to the
    // bright band where the clicks live.
    const ratchet = context.createOscillator();
    ratchet.setPeriodicWave(pulseWave(context));
    ratchet.frequency.value = 20;
    const ratchetGain = gainAt(0);
    ratchet.connect(filter('bandpass', 3000, 1.2)).connect(ratchetGain).connect(master);
    ratchet.start();

    // Chain and sprockets under load.
    const chainGain = gainAt(0);
    noiseSource().connect(filter('bandpass', 2300, 4)).connect(chainGain).connect(master);

    // E-assist motor whine.
    const motor = context.createOscillator();
    motor.type = 'triangle';
    motor.frequency.value = 300;
    const motorGain = gainAt(0);
    motor.connect(filter('lowpass', 2600, 0.5)).connect(motorGain).connect(master);
    motor.start();

    // Rim brake squeal.
    const squealGain = gainAt(0);
    noiseSource().connect(filter('bandpass', 3400, 14)).connect(squealGain).connect(master);

    return {
      tyreFilter, tyreGain, windFilter, windGain, ratchet, ratchetGain,
      chainGain, motor, motorGain, squealGain,
    };
  }
}

function createNoise(context: AudioContext): AudioBuffer {
  const length = context.sampleRate * 2;
  const buffer = context.createBuffer(1, length, context.sampleRate);
  const data = buffer.getChannelData(0);
  for (let index = 0; index < length; index += 1) data[index] = Math.random() * 2 - 1;
  return buffer;
}

// A pulse with about a tenth of the cycle high: rich in harmonics, so the
// band-pass finds plenty to click with at any pawl rate.
function pulseWave(context: AudioContext): PeriodicWave {
  const harmonics = 64;
  const real = new Float32Array(harmonics);
  const imaginary = new Float32Array(harmonics);
  const duty = 0.1;
  for (let n = 1; n < harmonics; n += 1) {
    imaginary[n] = (2 / (n * Math.PI)) * Math.sin(n * Math.PI * duty) * Math.sin(n * Math.PI * duty);
    real[n] = (2 / (n * Math.PI)) * Math.sin(n * Math.PI * duty) * Math.cos(n * Math.PI * duty);
  }
  return context.createPeriodicWave(real, imaginary);
}
