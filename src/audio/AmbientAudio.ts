const MUSIC_VOLUME = 0.07;
const STREET_SOUNDS_VOLUME = 0.38;

// Behind the title card the street is heard as if through a wall: low-passed,
// quieter, under the hum of the lamp. Entering the city opens it up.
const VEILED_CUTOFF_HZ = 420;
const OPEN_CUTOFF_HZ = 18_000;
const VEILED_STREET_GAIN = 0.5;
// Sodium lamp ballasts hum at twice the 50 Hz UK mains frequency.
const BALLAST_HUM_HZ = 100;
const BALLAST_HUM_GAIN = 0.012;
const BALLAST_HUM_FADE_IN_SECONDS = 4;

function runtimeAssetUrl(path: string): string {
  const encodedPath = path.split('/').map(encodeURIComponent).join('/');
  return `${import.meta.env.BASE_URL}assets/audio/${encodedPath}`;
}

function createLoopingTrack(path: string, volume: number): HTMLAudioElement {
  const track = new Audio(runtimeAssetUrl(path));
  track.loop = true;
  track.preload = 'metadata';
  track.volume = volume;
  return track;
}

export interface AmbientAudioOptions {
  /** Start muffled behind the title card until `unveil()` is called. */
  readonly veiled: boolean;
}

interface Veil {
  readonly context: AudioContext;
  readonly filter: BiquadFilterNode;
  readonly streetGain: GainNode;
  readonly hum: OscillatorNode;
  readonly humGain: GainNode;
}

export class AmbientAudio {
  private readonly music = createLoopingTrack(
    'Ambient music/Popcorn.mp3',
    MUSIC_VOLUME,
  );

  private readonly streetSounds = createLoopingTrack(
    'ambience/manny-streets.mp3',
    STREET_SOUNDS_VOLUME,
  );

  private musicEnabled = true;
  private veiled: boolean;
  // Music belongs to the city, not the title card.
  private musicHeld: boolean;
  private veil: Veil | null = null;

  constructor(options: AmbientAudioOptions = { veiled: false }) {
    this.veiled = options.veiled;
    this.musicHeld = options.veiled;
    window.addEventListener('keydown', this.handleKeyDown);
    window.addEventListener('pointerdown', this.handlePointerDown);
  }

  /** Opens the street to full presence over the given time, then lets music start. */
  unveil(durationSeconds: number): void {
    if (!this.veiled) return;
    this.veiled = false;

    const veil = this.veil;
    if (veil) {
      const now = veil.context.currentTime;
      const end = now + durationSeconds;
      rampFrom(veil.filter.frequency, now).exponentialRampToValueAtTime(OPEN_CUTOFF_HZ, end);
      rampFrom(veil.streetGain.gain, now).linearRampToValueAtTime(1, end);
      rampFrom(veil.humGain.gain, now).linearRampToValueAtTime(0, end);
      veil.hum.stop(end + 0.1);
    }

    window.setTimeout(() => {
      this.musicHeld = false;
      this.startEnabledTracks();
    }, durationSeconds * 1000);
  }

  private readonly handleKeyDown = (event: KeyboardEvent): void => {
    if (event.code === 'KeyM' && !event.repeat) {
      this.musicEnabled = !this.musicEnabled;
      if (!this.musicEnabled) {
        this.music.pause();
      }
    }

    this.startEnabledTracks();
  };

  private readonly handlePointerDown = (): void => {
    this.startEnabledTracks();
  };

  private startEnabledTracks(): void {
    if (this.veiled) {
      this.ensureVeil();
    }
    this.tryPlay(this.streetSounds);
    if (this.musicEnabled && !this.musicHeld) {
      this.tryPlay(this.music);
    }
  }

  // Built on the first gesture: browsers only let an AudioContext run after one.
  private ensureVeil(): void {
    if (this.veil) {
      void this.veil.context.resume();
      return;
    }

    try {
      const context = new AudioContext();
      const filter = context.createBiquadFilter();
      filter.type = 'lowpass';
      filter.frequency.value = VEILED_CUTOFF_HZ;
      filter.Q.value = 0.5;
      const streetGain = context.createGain();
      streetGain.gain.value = VEILED_STREET_GAIN;
      context
        .createMediaElementSource(this.streetSounds)
        .connect(filter)
        .connect(streetGain)
        .connect(context.destination);

      const hum = context.createOscillator();
      hum.type = 'triangle';
      hum.frequency.value = BALLAST_HUM_HZ;
      const humGain = context.createGain();
      humGain.gain.setValueAtTime(0, context.currentTime);
      humGain.gain.linearRampToValueAtTime(
        BALLAST_HUM_GAIN,
        context.currentTime + BALLAST_HUM_FADE_IN_SECONDS,
      );
      hum.connect(humGain).connect(context.destination);
      hum.start();

      void context.resume();
      this.veil = { context, filter, streetGain, hum, humGain };
    } catch {
      // Web Audio unavailable: the street simply plays unfiltered.
    }
  }

  private tryPlay(track: HTMLAudioElement): void {
    if (!track.paused) {
      return;
    }

    void track.play().catch(() => {
      // A later user gesture will retry if the browser has not unlocked audio yet.
    });
  }
}

function rampFrom(parameter: AudioParam, now: number): AudioParam {
  parameter.cancelScheduledValues(now);
  parameter.setValueAtTime(parameter.value, now);
  return parameter;
}
