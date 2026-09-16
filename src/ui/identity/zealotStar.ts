// The Zealot star: the first symbol of the game's graphic identity.
//
// A four-point star, elongated and slightly unequal: the lower arm is longest,
// so it reads at once as a streetlight flare, a camera glint, a navigation
// marker, a heraldic mullet and, if you look for it, a sword or a cross.
// Deliberately never a collectible icon. See docs/GRAPHIC_IDENTITY.md.

const SVG_NS = 'http://www.w3.org/2000/svg';

// Arm lengths in star units, from the centre.
const ARM = { top: 0.86, bottom: 1.14, side: 0.4 } as const;
// How far the concave waist is pulled towards the centre (0 = straight sides).
const WAIST = 0.07;

/** Outline of the star, centred on the origin, in star units. */
export const ZEALOT_STAR_PATH = [
  `M 0 ${-ARM.top}`,
  `Q ${WAIST} ${-WAIST} ${ARM.side} 0`,
  `Q ${WAIST} ${WAIST} 0 ${ARM.bottom}`,
  `Q ${-WAIST} ${WAIST} ${-ARM.side} 0`,
  `Q ${-WAIST} ${-WAIST} 0 ${-ARM.top}`,
  'Z',
].join(' ');

export const ZEALOT_STAR_VIEWBOX = `${-ARM.side} ${-ARM.top} ${ARM.side * 2} ${ARM.top + ARM.bottom}`;

/** A filled star that takes its colour from CSS `color`. */
export function createZealotStar(className: string): SVGSVGElement {
  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('class', className);
  svg.setAttribute('viewBox', ZEALOT_STAR_VIEWBOX);
  svg.setAttribute('aria-hidden', 'true');
  const path = document.createElementNS(SVG_NS, 'path');
  path.setAttribute('d', ZEALOT_STAR_PATH);
  path.setAttribute('fill', 'currentColor');
  svg.append(path);
  return svg;
}

/**
 * The same star as if drawn by hand with a pen: an open, slightly wandering
 * outline, overshooting where it closes. `seed` keeps one drawing stable.
 */
export function handDrawnStarPoints(seed: number, scale: number): string {
  const random = seededRandom(seed);
  const corners: readonly (readonly [number, number])[] = [
    [0, -ARM.top],
    [ARM.side * 0.9, 0],
    [0, ARM.bottom],
    [-ARM.side * 0.9, 0],
    [0, -ARM.top],
    [ARM.side * 0.35, -0.3],
  ];
  const points: string[] = [];
  for (let index = 0; index < corners.length - 1; index += 1) {
    const [x1, y1] = corners[index]!;
    const [x2, y2] = corners[index + 1]!;
    for (let step = 0; step < 6; step += 1) {
      const t = step / 6;
      // Pinch towards the centre mid-edge, as the drawn star's sides curve in.
      const pinch = Math.sin(t * Math.PI) * 0.28;
      const x = (x1 + (x2 - x1) * t) * (1 - pinch) + (random() - 0.5) * 0.05;
      const y = (y1 + (y2 - y1) * t) * (1 - pinch) + (random() - 0.5) * 0.05;
      points.push(`${(x * scale).toFixed(1)},${(y * scale).toFixed(1)}`);
    }
  }
  const [lastX, lastY] = corners[corners.length - 1]!;
  points.push(`${(lastX * scale).toFixed(1)},${(lastY * scale).toFixed(1)}`);
  return points.join(' ');
}

export function seededRandom(seed: number): () => number {
  let state = Math.floor(seed * 2_147_483_647) || 1;
  return () => {
    state = (state * 16_807) % 2_147_483_647;
    return (state - 1) / 2_147_483_646;
  };
}
