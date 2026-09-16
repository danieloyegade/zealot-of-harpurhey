import { ZEALOT_STAR_PATH } from './zealotStar';

// A journey drawn as a pen stroke rather than a GPS line: an entry loop, a
// long swash that swells in the middle, and a flick where it arrives. The
// Zealot star marks where the rider is along it.

const SVG_NS = 'http://www.w3.org/2000/svg';
let instance = 0;

/** `progress` (0–1) places the rider star along the main swash. */
export function createCalligraphicRoute(
  width: number,
  height: number,
  className: string,
  progress: number,
): SVGSVGElement {
  instance += 1;
  const gradientId = `z-route-pressure-${instance}`;
  const maskId = `z-route-mask-${instance}`;
  const svg = svgElement('svg', {
    class: className,
    width,
    height,
    viewBox: `0 0 ${width} ${height}`,
    'aria-hidden': 'true',
  });

  const middle = height * 0.58;
  // The main swash, as one cubic segment and one smooth continuation.
  const start: Point = [14, middle];
  const control1: Point = [width * 0.2, middle - height * 0.42];
  const control2: Point = [width * 0.36, middle + height * 0.36];
  const end: Point = [width * 0.52, middle - height * 0.05];
  const d = [
    `M 8 ${round(middle)}`,
    `C 3 ${round(middle - 12)}, 17 ${round(middle - 17)}, 19 ${round(middle - 6)}`,
    `C 20 ${round(middle + 3)}, 11 ${round(middle + 5)}, ${start[0]} ${start[1]}`,
    `C ${round(control1[0])} ${round(control1[1])}, ${round(control2[0])} ${round(control2[1])}, ${round(end[0])} ${round(end[1])}`,
    `S ${round(width * 0.8)} ${round(middle - height * 0.5)}, ${round(width * 0.9)} ${round(middle - height * 0.12)}`,
    `C ${round(width * 0.95)} ${round(middle + 2)}, ${round(width - 6)} ${round(middle)}, ${round(width - 3)} ${round(middle - height * 0.3)}`,
  ].join(' ');

  // A second, offset pass that fades in only through the middle of the stroke,
  // as a pen swells under pressure.
  const defs = svgElement('defs', {});
  const gradient = svgElement('linearGradient', { id: gradientId, x1: 0, x2: 1, y1: 0, y2: 0 });
  for (const [offset, opacity] of [[0, 0], [0.3, 1], [0.7, 1], [1, 0]] as const) {
    gradient.append(svgElement('stop', { offset, 'stop-color': 'white', 'stop-opacity': opacity }));
  }
  const mask = svgElement('mask', { id: maskId, maskUnits: 'userSpaceOnUse', x: 0, y: 0, width, height });
  mask.append(svgElement('rect', { x: 0, y: 0, width, height, fill: `url(#${gradientId})` }));
  defs.append(gradient, mask);

  const [riderX, riderY] = cubicPoint(start, control1, control2, end, Math.min(1, Math.max(0, progress)));
  svg.append(
    defs,
    svgElement('path', { class: 'z-route__stroke', d }),
    svgElement('path', { class: 'z-route__stroke z-route__stroke--pressure', d, transform: 'translate(0 0.9)', mask: `url(#${maskId})` }),
    svgElement('path', {
      class: 'z-route__rider',
      d: ZEALOT_STAR_PATH,
      transform: `translate(${round(riderX)} ${round(riderY)}) scale(7)`,
    }),
  );
  return svg;
}

type Point = readonly [number, number];

function cubicPoint(p0: Point, p1: Point, p2: Point, p3: Point, t: number): Point {
  const u = 1 - t;
  const a = u * u * u;
  const b = 3 * u * u * t;
  const c = 3 * u * t * t;
  const e = t * t * t;
  return [a * p0[0] + b * p1[0] + c * p2[0] + e * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + e * p3[1]];
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
