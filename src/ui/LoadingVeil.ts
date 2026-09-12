/**
 * Holds the opening frame black until the hero GLBs have resolved, then fades
 * away. Without it the player spawns into procedural fallbacks and watches
 * buildings swap themselves out one by one.
 *
 * A held black frame is not a compromise here: it is the same opening gesture
 * as the rest of the work.
 */
export class LoadingVeil {
  private readonly element = document.createElement('div');
  private dismissed = false;

  constructor() {
    this.element.className = 'loading-veil';
    document.body.appendChild(this.element);
  }

  /**
   * Fades the veil out and removes it from the document once the CSS
   * transition has finished. Safe to call more than once.
   */
  dismiss(): void {
    if (this.dismissed) {
      return;
    }
    this.dismissed = true;

    this.element.classList.add('is-dismissed');
    this.element.addEventListener(
      'transitionend',
      () => {
        this.element.remove();
      },
      { once: true },
    );
  }
}
