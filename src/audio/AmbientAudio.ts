const MUSIC_VOLUME = 0.07;
const STREET_SOUNDS_VOLUME = 0.38;

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

export class AmbientAudio {
  private readonly music = createLoopingTrack(
    'Ambient music/Y2Mate.is - Popcorn.mp3',
    MUSIC_VOLUME,
  );

  private readonly streetSounds = createLoopingTrack(
    'Foley/Street Sounds/manny-final.wav',
    STREET_SOUNDS_VOLUME,
  );

  private musicEnabled = true;

  constructor() {
    window.addEventListener('keydown', this.handleKeyDown);
    window.addEventListener('pointerdown', this.handlePointerDown);
  }

  private readonly handleKeyDown = (event: KeyboardEvent): void => {
    if (event.code === 'KeyM' && !event.repeat) {
      this.musicEnabled = !this.musicEnabled;
      if (this.musicEnabled) {
        this.tryPlay(this.music);
      } else {
        this.music.pause();
      }
    }

    this.startEnabledTracks();
  };

  private readonly handlePointerDown = (): void => {
    this.startEnabledTracks();
  };

  private startEnabledTracks(): void {
    this.tryPlay(this.streetSounds);
    if (this.musicEnabled) {
      this.tryPlay(this.music);
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
