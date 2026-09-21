import type { DeliveryView } from '../delivery/DeliveryInteraction';

function pounds(pence: number): string {
  return `£${(pence / 100).toFixed(2)}`;
}

/** A restrained job docket: an address, not a waypoint or progress bar. */
export class DeliveryDocket {
  private readonly element = document.createElement('aside');
  private readonly heading = document.createElement('div');
  private readonly instruction = document.createElement('strong');
  private readonly place = document.createElement('span');
  private readonly detail = document.createElement('small');
  private shownPhase = '';

  constructor() {
    this.element.className = 'delivery-docket';
    this.element.setAttribute('aria-live', 'polite');
    this.heading.className = 'delivery-docket__heading';
    this.element.append(this.heading, this.instruction, this.place, this.detail);
    document.body.append(this.element);
  }

  update(view: DeliveryView, hidden: boolean): void {
    this.element.classList.toggle('is-visible', !hidden);
    if (view.phase === this.shownPhase) return;
    this.shownPhase = view.phase;

    const number = String(view.assignment.number).padStart(3, '0');
    this.heading.textContent = `DELIVERY ${number}`;
    if (view.phase === 'complete') {
      this.instruction.textContent = 'RECEIVED';
      this.place.textContent = pounds(view.assignment.feePence);
      this.detail.textContent = view.assignment.item;
      return;
    }
    this.instruction.textContent = view.phase === 'awaiting-pickup' ? 'COLLECT' : 'DELIVER';
    this.place.textContent = view.placeName;
    this.detail.textContent = `${view.assignment.item} · ${view.detail}`;
  }
}
