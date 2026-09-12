import type { ProximityTarget } from '../interaction/LocationAwareness';

/**
 * The on-screen acknowledgement that the player is standing somewhere.
 *
 * Deliberately just the authored name — the deadpan museum caption, not a
 * quest prompt. No verbs, no key hints, no distance readout: nothing is
 * advertised that the game cannot yet do.
 */
export class LocationLabel {
  private readonly element = document.createElement('div');
  private readonly nameElement = document.createElement('span');

  constructor() {
    this.element.className = 'location-label';
    this.element.setAttribute('aria-live', 'polite');
    this.nameElement.className = 'location-label__name';
    this.element.appendChild(this.nameElement);
    this.element.hidden = true;
    document.body.appendChild(this.element);
  }

  show(target: ProximityTarget): void {
    this.nameElement.textContent = target.name;
    this.element.hidden = false;
    // Restart the fade-in even when moving straight from one location to the
    // next without an intervening hidden frame.
    this.element.classList.remove('is-visible');
    void this.element.offsetWidth;
    this.element.classList.add('is-visible');
  }

  hide(): void {
    this.element.classList.remove('is-visible');
  }

  render(target: ProximityTarget | null): void {
    if (target === null) {
      this.hide();
      return;
    }
    this.show(target);
  }
}
