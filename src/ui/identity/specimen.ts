import { createCalligraphicRoute } from './calligraphicRoute';
import { createCartouche } from './cartouche';
import {
  createBusDestination,
  createBusTicket,
  createChapterCard,
  createDeliveryCard,
  createNightSoFar,
  createPrintedScript,
  ensureIdentityDefs,
  type World,
} from './compositions';
import { createHorseEmblem, createRoseEmblem } from './emblems';
import { createZealotStar } from './zealotStar';

// Development board (?identity): the identity's parts and compositions on one
// scrolling page, for review before they are used in play.

export function mountIdentitySpecimen(): void {
  ensureIdentityDefs();
  const board = element('main', 'z-board');

  board.append(
    section('Marks — night world / print world', [marksSheet('night'), marksSheet('print')]),
    section('Title sequence beat — first delivery', [deliveryBeat()]),
    section('Chapter cards', [
      createChapterCard({ world: 'print', numeral: 'I', scriptTitle: 'Flowers for a Stranger', emblem: 'rose' }),
      createChapterCard({
        world: 'night',
        numeral: 'II',
        serifTitle: 'Figures Isolated Within\nMunicipal Architecture',
        emblem: 'horse',
      }),
      createChapterCard({ world: 'print', numeral: 'III', scriptTitle: 'Before the Night Is Spent', emblem: 'horse', framed: true }),
    ]),
    section('Bus destination / ticket', [createBusDestination('01', '23:52'), ticketSheet()]),
    section('Pause menu — the night so far (example values after several nights)', [
      createNightSoFar({
        deliveries: 7,
        earnedPence: 1940,
        filmExposed: 21,
        filmCapacity: 36,
        time: '01:14',
        lastService: '01:32',
      }),
    ]),
  );

  document.body.append(board);
}

function marksSheet(world: World): HTMLElement {
  const sheet = element('div', `z-sheet z-marks z-world--${world}`);
  const cartouche = element('figure', 'z-marks__item');
  cartouche.append(createCartouche(220, 150, 'z-cartouche'), caption('Cartouche'));
  const horse = element('figure', 'z-marks__item');
  horse.append(createHorseEmblem('z-emblem z-marks__horse'), caption('Horse'));
  const horseMark = element('figure', 'z-marks__item');
  horseMark.append(createHorseEmblem('z-emblem z-marks__horse-mark', 'mark'), caption('Horse, small'));
  const rose = element('figure', 'z-marks__item');
  rose.append(createRoseEmblem('z-emblem z-marks__rose'), caption('Rose'));
  const star = element('figure', 'z-marks__item');
  star.append(createZealotStar('z-marks__star'), caption('Star'));
  const route = element('figure', 'z-marks__item z-marks__item--wide');
  route.append(createCalligraphicRoute(300, 60, 'z-route', 0.4), caption('Route'));
  const script = element('figure', 'z-marks__item z-marks__item--wide');
  script.append(createPrintedScript('night no. i', 'z-marks__script'), caption('Hand'));
  sheet.append(cartouche, horse, horseMark, rose, star, route, script);
  return sheet;
}

function deliveryBeat(): HTMLElement {
  const sheet = element('div', 'z-sheet z-beat z-world--night');
  sheet.append(createPrintedScript('Flowers', 'z-beat__script'), createDeliveryCard('night'));
  return sheet;
}

function ticketSheet(): HTMLElement {
  const sheet = element('div', 'z-sheet z-world--print z-sheet--centred');
  sheet.append(createBusTicket('01', '23:52'));
  return sheet;
}

function section(label: string, children: readonly HTMLElement[]): HTMLElement {
  const wrapper = element('section', 'z-board__section');
  const row = element('div', 'z-board__row');
  row.append(...children);
  wrapper.append(element('h2', 'z-board__label', label), row);
  return wrapper;
}

function caption(text: string): HTMLElement {
  return element('figcaption', 'z-caps z-caps--3', text);
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
