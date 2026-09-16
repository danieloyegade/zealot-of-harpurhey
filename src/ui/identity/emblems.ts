import { ZEALOT_STAR_PATH } from './zealotStar';

// Heraldic marks drawn as if cut in wood or engraved: the horse and the rose.
// Deliberately simple, so they survive as small marks and as thin lines.
// Drafts awaiting approval, per the asset-first rule. See docs/GRAPHIC_IDENTITY.md.

const SVG_NS = 'http://www.w3.org/2000/svg';
let instance = 0;

const HORSE_WIDTH = 200;
const HORSE_HEIGHT = 164;

// A horse passant, facing dexter (the viewer's left, as heraldic beasts do):
// long legs, an arched neck and a raised near foreleg, carrying an insulated
// delivery box charged with the Zealot star.
const HORSE_BODY = [
  'M 20 44',
  'C 24 36, 30 30, 38 24',
  'C 43 20, 46 15, 48 8',
  'L 52 2',
  'L 55 14',
  'C 58 16, 62 18, 66 21',
  'C 80 27, 90 40, 102 50',
  'C 114 54, 126 56, 138 54',
  'C 150 52, 160 52, 167 58',
  'C 173 63, 176 71, 175 81',
  'C 174 91, 171 99, 169 105',
  'C 171 116, 172 132, 170 150',
  'L 173 157',
  'L 162 157',
  'C 162 142, 161 126, 157 112',
  'C 155 104, 151 99, 145 97',
  'C 131 101, 111 103, 98 99',
  'C 95 112, 96 130, 94 150',
  'L 97 157',
  'L 86 157',
  'C 86 142, 84 124, 82 108',
  'C 76 112, 70 118, 66 128',
  'C 64 134, 62 140, 58 141',
  'L 53 137',
  'C 57 132, 60 124, 63 114',
  'C 66 104, 69 94, 69 86',
  'C 66 78, 60 68, 52 60',
  'C 46 56, 38 54, 32 55',
  'C 26 56, 18 54, 20 44',
  'Z',
].join(' ');

const HORSE_TAIL =
  'M 166 57 C 182 54, 193 67, 190 83 C 188 97, 180 108, 188 126 C 176 117, 171 103, 174 88 C 176 75, 174 65, 165 62 Z';

// Lines "carved" out of the silhouette: mane, musculature, the box strap.
const HORSE_CARVING = [
  'M 68 27 C 78 34, 86 42, 94 49',
  'M 63 35 C 71 42, 78 49, 84 56',
  'M 151 62 C 159 67, 163 75, 163 86',
  'M 73 74 C 77 80, 79 86, 79 93',
  'M 114 55 C 113 70, 111 85, 109 99',
];

export type EmblemDetail = 'full' | 'mark';

/** The Zealot horse. `mark` drops the carved detail for very small sizes. */
export function createHorseEmblem(className: string, detail: EmblemDetail = 'full'): SVGSVGElement {
  instance += 1;
  const maskId = `z-horse-carving-${instance}`;
  const svg = svgElement('svg', {
    class: className,
    viewBox: `0 0 ${HORSE_WIDTH} ${HORSE_HEIGHT}`,
    'aria-hidden': 'true',
  });

  const defs = svgElement('defs', {});
  const mask = svgElement('mask', {
    id: maskId,
    maskUnits: 'userSpaceOnUse',
    x: 0,
    y: 0,
    width: HORSE_WIDTH,
    height: HORSE_HEIGHT,
  });
  mask.append(svgElement('rect', { x: 0, y: 0, width: HORSE_WIDTH, height: HORSE_HEIGHT, fill: 'white' }));
  const carving = svgElement('g', {
    fill: 'none',
    stroke: 'black',
    'stroke-width': 2.6,
    'stroke-linecap': 'round',
  });
  if (detail === 'full') {
    for (const d of HORSE_CARVING) carving.append(svgElement('path', { d }));
  }
  // The box: a carved inner edge like stitching, and the star as its charge.
  carving.append(
    svgElement('rect', { x: 109, y: 33, width: 22, height: 17, rx: 1, 'stroke-width': detail === 'full' ? 1.8 : 3 }),
    svgElement('path', {
      d: ZEALOT_STAR_PATH,
      fill: 'black',
      stroke: 'none',
      transform: 'translate(120 41.5) scale(5.2)',
    }),
    svgElement('circle', { cx: 35, cy: 31, r: 2.2, fill: 'black', stroke: 'none' }),
  );
  mask.append(carving);
  defs.append(mask);

  const body = svgElement('g', { fill: 'currentColor', mask: `url(#${maskId})` });
  body.append(
    svgElement('path', { d: HORSE_BODY }),
    svgElement('path', { d: HORSE_TAIL }),
    svgElement('rect', { x: 105, y: 29, width: 30, height: 25, rx: 2 }),
  );

  svg.append(defs, body);
  return svg;
}

// An engraved rose on a stem: line only, so it prints in one colour at any size.
const ROSE_LINES = [
  'M 14 30 C 12 18, 22 8, 30 10 C 40 8, 48 18, 46 30 C 44 40, 36 44, 30 44 C 22 44, 16 40, 14 30 Z',
  'M 30 21 C 36 19, 38 27, 32 29 C 26 31, 24 23, 30 19 C 38 15, 44 25, 38 33',
  'M 18 34 C 24 38, 34 38, 42 32',
  'M 22 14 C 26 18, 34 18, 38 13',
  'M 17 24 L 21 26 M 16 29 L 21 31 M 18 35 L 22 36',
  'M 30 44 C 30 60, 28 76, 32 96',
  'M 30 64 C 20 58, 12 60, 8 66 C 16 70, 24 70, 30 64 Z',
  'M 12 65 C 18 64, 24 65, 29 64',
  'M 31 77 C 40 71, 48 73, 52 79 C 44 83, 36 83, 31 77 Z',
  'M 48 79 C 42 78, 36 78, 32 77',
  'M 29.5 53 L 25 51 M 30.5 87 L 35 85',
];

export function createRoseEmblem(className: string): SVGSVGElement {
  const svg = svgElement('svg', { class: className, viewBox: '0 0 60 100', 'aria-hidden': 'true' });
  const group = svgElement('g', {
    fill: 'none',
    stroke: 'currentColor',
    'stroke-width': 1.5,
    'stroke-linecap': 'round',
    'stroke-linejoin': 'round',
  });
  for (const d of ROSE_LINES) group.append(svgElement('path', { d }));
  svg.append(group);
  return svg;
}

function svgElement<K extends keyof SVGElementTagNameMap>(
  tag: K,
  attributes: Record<string, string | number>,
): SVGElementTagNameMap[K] {
  const element = document.createElementNS(SVG_NS, tag);
  for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, String(value));
  return element;
}
