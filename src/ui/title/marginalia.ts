import { createDeliveryCard, createPrintedScript, ensureIdentityDefs } from '../identity/compositions';
import { createHorseEmblem } from '../identity/emblems';
import { createZealotStar } from '../identity/zealotStar';

// What the title card shows besides the title itself: the star on the loading
// line, the two sparse beats between the city assembling and the invitation to
// enter, and the controls line. The rest of the graphic vocabulary is withheld
// for play. Layout lives in index.html (`data-intro-slot`) and intro.css.

// Controls that exist today. Add E / Interact and a map key when those systems do.
const CONTROLS = [
  ['WASD', 'Move'],
  ['Shift', 'Run'],
  ['Drag', 'Look'],
  ['M', 'Music'],
] as const;

export function mountTitleContent(root: HTMLElement): void {
  ensureIdentityDefs();

  // The one small symbol on the card: a red star riding the loading line.
  root.querySelector('[data-intro-rule]')?.append(createZealotStar('intro__rule-star'));

  // Sparse: a small horse, the rider's number, and far below, where.
  slot(root, 'rider-beat')?.replaceChildren(
    createHorseEmblem('z-emblem intro__beat-horse'),
    line('Rider 01', 'intro__line intro__line--primary intro__beat-rider'),
    line('53°31′ N / 2°13′ W', 'intro__line intro__line--tertiary intro__beat-coordinates'),
  );

  // The first delivery, announced by typography alone: the romance in the
  // hand, the record in the cartouche.
  slot(root, 'delivery-beat')?.replaceChildren(
    createPrintedScript('Flowers', 'z-beat__script intro__beat-script'),
    createDeliveryCard('night'),
  );

  slot(root, 'controls')?.replaceChildren(
    ...CONTROLS.map(([key, action]) => line(`${key} / ${action}`, '', 'span')),
  );
}

function slot(root: HTMLElement, name: string): HTMLElement | null {
  return root.querySelector<HTMLElement>(`[data-intro-slot="${name}"]`);
}

function line(text: string, className: string, tag: 'p' | 'span' = 'p'): HTMLElement {
  const element = document.createElement(tag);
  if (className) element.className = className;
  element.textContent = text;
  return element;
}
