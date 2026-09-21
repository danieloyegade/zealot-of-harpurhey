import { ensureIdentityDefs } from '../identity/compositions';
import { createZealotStar } from '../identity/zealotStar';

// What the title card shows besides the printed plate: the star riding the
// assembly line, and the controls line. Everything else in the graphic
// vocabulary is either printed on the plate or withheld for play. Layout lives
// in index.html (`data-intro-slot`) and intro.css.

// Controls that exist today. Add E / Interact and a map key when those systems do.
const CONTROLS = [
  ['WASD', 'Move'],
  ['Shift / Space', 'Run'],
  ['E', 'Use'],
  ['Drag', 'Look'],
  ['M', 'Music'],
] as const;

export function mountTitleContent(root: HTMLElement): void {
  ensureIdentityDefs();

  // The one live symbol on the card: a star riding the plate's printed rule.
  root.querySelector('[data-intro-rule]')?.append(createZealotStar('intro__rule-star'));

  slot(root, 'controls')?.replaceChildren(
    ...CONTROLS.map(([key, action]) => span(`${key} / ${action}`)),
  );
}

function slot(root: HTMLElement, name: string): HTMLElement | null {
  return root.querySelector<HTMLElement>(`[data-intro-slot="${name}"]`);
}

function span(text: string): HTMLElement {
  const element = document.createElement('span');
  element.textContent = text;
  return element;
}
