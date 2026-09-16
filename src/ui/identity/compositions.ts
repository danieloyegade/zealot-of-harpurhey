import { deliveryDestination, distanceFromStartMetres, FIRST_DELIVERY } from '../../delivery/firstDelivery';
import { createCalligraphicRoute } from './calligraphicRoute';
import { createCartouche } from './cartouche';
import { createHorseEmblem, createRoseEmblem } from './emblems';
import './identity.css';

// Compositions built from the identity's parts. Each sets the record (small
// municipal capitals: coordinates, money, distance, time) against the romance
// (calligraphy, the horse, the rose, ornament). See docs/GRAPHIC_IDENTITY.md.

export type World = 'night' | 'print';
export type Emblem = 'horse' | 'rose' | 'none';

const COORDINATES = '53°31′ N  2°13′ W';

/** SVG filters for printed and handwritten type. Safe to call repeatedly. */
export function ensureIdentityDefs(): void {
  if (document.getElementById('z-identity-defs')) return;
  const holder = document.createElement('div');
  holder.innerHTML = `
    <svg id="z-identity-defs" width="0" height="0" style="position:absolute" aria-hidden="true">
      <filter id="z-ink" x="-5%" y="-15%" width="110%" height="130%">
        <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="2" seed="7" result="grain" />
        <feDisplacementMap in="SourceGraphic" in2="grain" scale="2" xChannelSelector="R" yChannelSelector="G" result="wobble" />
        <feTurbulence type="fractalNoise" baseFrequency="1.1" numOctaves="1" seed="3" result="speckle" />
        <feComponentTransfer in="speckle" result="breakup">
          <feFuncA type="discrete" tableValues="1 1 1 1 1 1 1 1 0.4 1" />
        </feComponentTransfer>
        <feComposite in="wobble" in2="breakup" operator="in" />
      </filter>
      <filter id="z-ink-print" x="-5%" y="-15%" width="110%" height="130%">
        <feMorphology operator="dilate" radius="0.3" result="spread" />
        <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="5" result="grain" />
        <feDisplacementMap in="spread" in2="grain" scale="1.3" xChannelSelector="R" yChannelSelector="G" />
      </filter>
    </svg>`;
  const defs = holder.firstElementChild;
  if (defs) document.body.append(defs);
}

/** Handwriting set in two passes, the second faint and out of register. */
export function createPrintedScript(text: string, className: string): HTMLElement {
  const script = element('p', `z-script z-printed ${className}`);
  script.setAttribute('aria-label', text);
  const ghost = element('span', 'z-printed__ghost', text);
  const ink = element('span', 'z-printed__ink', text);
  ghost.setAttribute('aria-hidden', 'true');
  ink.setAttribute('aria-hidden', 'true');
  script.append(ghost, ink);
  return script;
}

export function createEmblem(kind: Emblem, className: string): SVGSVGElement | null {
  if (kind === 'horse') return createHorseEmblem(`z-emblem ${className}`);
  if (kind === 'rose') return createRoseEmblem(`z-emblem ${className}`);
  return null;
}

export interface ChapterCardOptions {
  readonly world: World;
  readonly numeral: string;
  /** Institutional title in classical capitals; line breaks are kept. */
  readonly serifTitle?: string;
  /** Romantic title in the hand. */
  readonly scriptTitle?: string;
  readonly emblem: Emblem;
  /** Set the emblem inside the cartouche. */
  readonly framed?: boolean;
}

export function createChapterCard(options: ChapterCardOptions): HTMLElement {
  const card = element('section', `z-chapter z-world--${options.world}`);
  const head = element('div', 'z-chapter__head');

  const emblem = createEmblem(options.emblem, `z-chapter__emblem z-chapter__emblem--${options.emblem}`);
  if (emblem && options.framed) {
    const frame = element('div', 'z-chapter__frame');
    frame.append(createCartouche(150, 104, 'z-cartouche', { lace: true, medallion: false }), emblem);
    head.append(frame);
  } else if (emblem) {
    head.append(emblem);
  }
  head.append(element('p', 'z-caps z-caps--1 z-chapter__night', `Night ${options.numeral}`));
  card.append(head);

  if (options.serifTitle) card.append(element('h2', 'z-caps z-chapter__serif', options.serifTitle));
  if (options.scriptTitle) card.append(createPrintedScript(options.scriptTitle, 'z-chapter__script'));

  card.append(footer('z-chapter__meta', ['Harperhey / Greater Manchester', '23:47', COORDINATES]));
  return card;
}

export interface NightSoFarValues {
  readonly deliveries: number;
  readonly earnedPence: number;
  readonly filmExposed: number;
  readonly filmCapacity: number;
  readonly time: string;
  readonly lastService: string;
}

// The pause menu as a record of the night: statistics set as an artwork.
export function createNightSoFar(values: NightSoFarValues): HTMLElement {
  const sheet = element('section', 'z-pause z-world--night');
  sheet.append(
    element('p', 'z-caps z-pause__mast', 'Zealot'),
    createPrintedScript('The Night So Far', 'z-pause__script'),
  );

  const ledger = element('dl', 'z-pause__ledger');
  for (const [label, value] of [
    ['Deliveries', String(values.deliveries).padStart(2, '0')],
    ['Earned', formatMoney(values.earnedPence)],
    ['Film', `${values.filmExposed} / ${values.filmCapacity}`],
    ['Time', values.time],
    ['Bus', `Last service ${values.lastService}`],
  ] as const) {
    ledger.append(element('dt', 'z-caps', label), element('dd', 'z-caps', value));
  }

  const horse = createHorseEmblem('z-emblem z-pause__horse', 'mark');
  sheet.append(ledger, horse, footer('z-pause__foot', ['Harperhey', 'MMXXVI']));
  return sheet;
}

// Harperhey is a place, set in the institution's capitals; the Promised Land
// is an idea, set in the hand. The route between them is a pen stroke.
export function createBusDestination(service: string, departs: string): HTMLElement {
  const sheet = element('section', 'z-destination z-world--night');
  sheet.append(
    element('p', 'z-caps z-caps--2 z-destination__service', `Service ${service}`),
    element('p', 'z-caps z-destination__from', 'Harperhey'),
    createCalligraphicRoute(520, 80, 'z-route z-destination__route', 0.34),
    createPrintedScript('The Promised Land', 'z-destination__to'),
    element('p', 'z-caps z-caps--3 z-destination__time', `Departs ${departs}`),
  );
  return sheet;
}

export function createBusTicket(service: string, departs: string): HTMLElement {
  const ticket = element('section', 'z-ticket z-world--print');
  ticket.append(
    createCartouche(360, 220, 'z-cartouche', { lace: true, medallion: true }),
    element('p', 'z-caps z-caps--3 z-ticket__service', `Service ${service} · Adult single`),
    element('p', 'z-caps z-ticket__from', 'Harperhey'),
    createPrintedScript('The Promised Land', 'z-ticket__to'),
    footer('z-ticket__foot', [departs, '£ 2.00']),
  );
  return ticket;
}

/** DELIVERY 001 inside the cartouche, with the rose standing for the flowers. */
export function createDeliveryCard(world: World): HTMLElement {
  const card = element('div', `z-delivery z-tone--${world}`);
  const destination = deliveryDestination(FIRST_DELIVERY);
  card.append(
    createCartouche(300, 214, 'z-cartouche', { lace: true, medallion: true }),
    createRoseEmblem('z-emblem z-delivery__rose'),
    element('p', 'z-caps z-caps--1', `Delivery ${String(FIRST_DELIVERY.number).padStart(3, '0')}`),
    element('p', 'z-caps z-caps--2', `${destination?.name ?? FIRST_DELIVERY.destinationId} / ${FIRST_DELIVERY.destinationDetail}`),
    element('p', 'z-caps z-caps--3', `${(distanceFromStartMetres(FIRST_DELIVERY) / 1000).toFixed(2)} km`),
    element('p', 'z-caps z-caps--2', formatMoney(FIRST_DELIVERY.feePence)),
  );
  return card;
}

function footer(className: string, items: readonly string[]): HTMLElement {
  const row = element('div', className);
  row.append(...items.map((text) => element('span', 'z-caps z-caps--3', text)));
  return row;
}

function element<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className: string,
  text?: string,
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function formatMoney(pence: number): string {
  return `£ ${(pence / 100).toFixed(2)}`;
}
