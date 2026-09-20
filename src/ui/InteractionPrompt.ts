import type { InteractionPromptView } from '../interaction/BikeInteraction';

const RIDING_HINT_SECONDS = 7;

/** The single contextual key prompt at the foot of the screen. */
export class InteractionPrompt {
  private readonly element = document.createElement('div');
  private readonly key = document.createElement('kbd');
  private readonly label = document.createElement('span');
  private readonly hint = document.createElement('div');
  private shownKey = '';
  private shownLabel = '';
  private hintRemaining = 0;
  private wasRiding = false;

  constructor() {
    this.element.className = 'interaction-prompt';
    this.element.setAttribute('aria-live', 'polite');
    this.element.append(this.key, this.label);
    this.hint.className = 'interaction-hint';
    this.hint.textContent = 'W pedal · Shift assist · Space boost · A D steer · S brake';
    document.body.append(this.element, this.hint);
  }

  update(deltaTime: number, prompt: InteractionPromptView | null, riding: boolean): void {
    if (prompt && (prompt.key !== this.shownKey || prompt.label !== this.shownLabel)) {
      this.key.textContent = prompt.key;
      this.label.textContent = prompt.label;
      this.shownKey = prompt.key;
      this.shownLabel = prompt.label;
    }
    this.element.classList.toggle('is-visible', prompt !== null);

    if (riding && !this.wasRiding) this.hintRemaining = RIDING_HINT_SECONDS;
    this.wasRiding = riding;
    this.hintRemaining = riding ? Math.max(0, this.hintRemaining - deltaTime) : 0;
    this.hint.classList.toggle('is-visible', this.hintRemaining > 0);
  }
}
