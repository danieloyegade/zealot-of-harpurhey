import { ZEALOT_STAR_PATH } from './zealotStar';

// The Zealot cartouche: an original ornamental frame and a recurring
// signature. Concave corners holding small lace-like ornaments, a double rule
// threaded with pinholes, a medallion that breaks the top edge and a bead on
// the bottom. It must survive as a single thin line, so every element is a
// hairline or a dot. See docs/GRAPHIC_IDENTITY.md.

const SVG_NS = 'http://www.w3.org/2000/svg';

// Space around the frame for the medallion and corner ornaments.
const MARGIN = 16;
const CORNER_RADIUS = 13;
const RULE_GAP = 5;
const LACE_SPACING = 7;

export interface CartoucheOptions {
  /** Pinholes between the two rules. Omit for very small frames. */
  readonly lace?: boolean;
  /** Star medallion breaking the top edge. */
  readonly medallion?: boolean;
}

/** A frame sized in CSS pixels; its interior is left empty for content laid over it. */
export function createCartouche(
  width: number,
  height: number,
  className: string,
  { lace = true, medallion = true }: CartoucheOptions = {},
): SVGSVGElement {
  const svg = svgElement('svg', {
    class: className,
    width,
    height,
    viewBox: `0 0 ${width} ${height}`,
    'aria-hidden': 'true',
  });

  const left = MARGIN;
  const top = MARGIN;
  const right = width - MARGIN;
  const bottom = height - MARGIN;
  const centreX = width / 2;
  const medallionGap = medallion ? 17 : 0;

  const rules = svgElement('g', { class: 'z-cartouche__rule' });
  rules.append(
    svgElement('path', {
      d: concaveFrame(left, top, right, bottom, CORNER_RADIUS, medallionGap, 7),
    }),
    svgElement('path', {
      d: concaveFrame(
        left + RULE_GAP,
        top + RULE_GAP,
        right - RULE_GAP,
        bottom - RULE_GAP,
        CORNER_RADIUS,
        medallionGap,
        7,
      ),
    }),
  );
  svg.append(rules);

  if (lace) svg.append(pinholes(left, top, right, bottom, centreX, medallionGap));

  const ornament = svgElement('g', { class: 'z-cartouche__ornament' });
  for (const [x, y, dx, dy] of [
    [left, top, 1, 1],
    [right, top, -1, 1],
    [right, bottom, -1, -1],
    [left, bottom, 1, -1],
  ] as const) {
    ornament.append(cornerOrnament(x, y, dx, dy));
  }

  // The bead at the foot.
  ornament.append(
    svgElement('path', {
      d: `M ${centreX} ${bottom - 4} L ${centreX + 4} ${bottom} L ${centreX} ${bottom + 4} L ${centreX - 4} ${bottom} Z`,
    }),
  );

  if (medallion) {
    ornament.append(
      svgElement('ellipse', { cx: centreX, cy: top + RULE_GAP / 2, rx: 9, ry: 11, fill: 'none' }),
      svgElement('path', {
        class: 'z-cartouche__star',
        d: ZEALOT_STAR_PATH,
        transform: `translate(${centreX} ${top + RULE_GAP / 2 - 1}) scale(7)`,
      }),
      svgElement('path', { d: flourish(centreX - 10, top + RULE_GAP / 2, -1), fill: 'none' }),
      svgElement('path', { d: flourish(centreX + 10, top + RULE_GAP / 2, 1), fill: 'none' }),
    );
  }
  svg.append(ornament);
  return svg;
}

/**
 * A rectangle whose corners are cut inwards by quarter circles centred on the
 * corner points, with gaps left in the top and bottom edges for ornaments.
 */
function concaveFrame(
  left: number,
  top: number,
  right: number,
  bottom: number,
  radius: number,
  topGap: number,
  bottomGap: number,
): string {
  const centreX = (left + right) / 2;
  const arc = (x: number, y: number): string => `A ${radius} ${radius} 0 0 0 ${round(x)} ${round(y)}`;
  return [
    `M ${round(centreX + topGap)} ${round(top)}`,
    `H ${round(right - radius)}`,
    arc(right, top + radius),
    `V ${round(bottom - radius)}`,
    arc(right - radius, bottom),
    `H ${round(centreX + bottomGap)}`,
    `M ${round(centreX - bottomGap)} ${round(bottom)}`,
    `H ${round(left + radius)}`,
    arc(left, bottom - radius),
    `V ${round(top + radius)}`,
    arc(left + radius, top),
    `H ${round(centreX - topGap)}`,
  ].join(' ');
}

// In each cut-away corner: a smaller concentric arc, a pinhole, and a short
// tendril running out along the diagonal.
function cornerOrnament(x: number, y: number, dx: number, dy: number): SVGGElement {
  const group = svgElement('g', {});
  const inner = CORNER_RADIUS - 5;
  const sweep = dx * dy > 0 ? 0 : 1;
  group.append(
    svgElement('path', {
      d: `M ${round(x + dx * inner)} ${round(y)} A ${inner} ${inner} 0 0 ${sweep} ${round(x)} ${round(y + dy * inner)}`,
      fill: 'none',
    }),
    svgElement('circle', { cx: round(x + dx * 2.6), cy: round(y + dy * 2.6), r: 1.6 }),
    svgElement('path', {
      d: `M ${round(x - dx * 2)} ${round(y - dy * 2)} C ${round(x - dx * 8)} ${round(y - dy * 3)}, ${round(x - dx * 9)} ${round(y - dy * 10)}, ${round(x - dx * 4)} ${round(y - dy * 11)}`,
      fill: 'none',
    }),
  );
  return group;
}

// An S-scroll running along the top edge away from the medallion, ending in a curl.
function flourish(startX: number, y: number, direction: 1 | -1): string {
  const x = (offset: number): number => round(startX + direction * offset);
  return [
    `M ${x(0)} ${round(y)}`,
    `C ${x(10)} ${round(y - 9)}, ${x(20)} ${round(y + 8)}, ${x(34)} ${round(y)}`,
    `C ${x(40)} ${round(y - 4)}, ${x(44)} ${round(y - 1)}, ${x(42)} ${round(y + 3)}`,
    `C ${x(40)} ${round(y + 6)}, ${x(36)} ${round(y + 3)}, ${x(38)} ${round(y)}`,
  ].join(' ');
}

function pinholes(
  left: number,
  top: number,
  right: number,
  bottom: number,
  centreX: number,
  medallionGap: number,
): SVGGElement {
  const group = svgElement('g', { class: 'z-cartouche__lace' });
  const inset = RULE_GAP / 2;
  const clear = CORNER_RADIUS + 4;

  const horizontal = (y: number, gap: number): void => {
    for (let x = left + clear; x <= right - clear; x += LACE_SPACING) {
      if (Math.abs(x - centreX) < gap + 6) continue;
      group.append(svgElement('circle', { cx: round(x), cy: round(y), r: 0.8 }));
    }
  };
  const vertical = (x: number): void => {
    for (let y = top + clear; y <= bottom - clear; y += LACE_SPACING) {
      group.append(svgElement('circle', { cx: round(x), cy: round(y), r: 0.8 }));
    }
  };

  horizontal(top + inset, medallionGap + 34);
  horizontal(bottom - inset, 8);
  vertical(left + inset);
  vertical(right - inset);
  return group;
}

function svgElement<K extends keyof SVGElementTagNameMap>(
  tag: K,
  attributes: Record<string, string | number>,
): SVGElementTagNameMap[K] {
  const element = document.createElementNS(SVG_NS, tag);
  for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, String(value));
  return element;
}

function round(value: number): number {
  return Math.round(value * 10) / 10;
}
