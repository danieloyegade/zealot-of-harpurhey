import {
  CanvasTexture,
  type Group,
  LinearMipmapLinearFilter,
  Mesh,
  MeshBasicMaterial,
  PlaneGeometry,
  SRGBColorSpace,
} from 'three';

// Lettering for the ABC Building, drawn at runtime onto the GLB's own sign
// surfaces. Reference: references/architecture/buildings/clints/EXT/IMG_8908
// and the Quay Street Street View captures. Each tenant's name is dark,
// condensed, all-caps type printed on a translucent, evenly lit white
// lightbox band. The GLB's sign surfaces (all 7.38 m x 0.96 m, front face
// toward +Z) carry no UVs, so each name is a thin plane just proud of its
// surface rather than a change to the authored geometry.
//
// Not covered yet: the window neon (Clints' red CLI/NTS, the blue hand), Side
// Street's bubble-lettering wall sign, and the vertical ABC on the tower core.
// Those have anchors in the GLB (CL_Neon_*, SS_LogoAnchor, ABC_TowerLogoAnchor).

const BAND_WIDTH = 7.38;
const BAND_HEIGHT = 0.96;
const CANVAS_WIDTH = 2048;
const PIXELS_PER_METRE = CANVAS_WIDTH / BAND_WIDTH;
const CANVAS_HEIGHT = Math.round(BAND_HEIGHT * PIXELS_PER_METRE);

// The plane sits 2 mm proud of the sign surface's front face (local z = +0.07).
const PLANE_Z = 0.072;

const LIGHTBOX = '#f7ecd6';
const INK = '#2a2c2f';

interface BaySign {
  readonly surface: string;
  readonly text: string | null;
  /** Cap height in metres. The reference lettering is about a third of the band. */
  readonly capHeight: number;
  /** Horizontal squash of the base face; smaller is more condensed. */
  readonly squash: number;
  /** Extra space between letters, in metres. */
  readonly tracking: number;
  /** Horizontal centre of the text as a fraction of the band's width. */
  readonly anchorX: number;
}

const BAY_SIGNS: readonly BaySign[] = [
  { surface: 'ABC_SignSurface_Bay01_ABC_Corner', text: 'ABC', capHeight: 0.42, squash: 0.58, tracking: 0.05, anchorX: 0.5 },
  { surface: 'ABC_SignSurface_Bay02_ABC', text: 'ABC', capHeight: 0.42, squash: 0.58, tracking: 0.05, anchorX: 0.5 },
  { surface: 'ABC_SignSurface_Bay03_CLINTS', text: 'CLINTS', capHeight: 0.46, squash: 0.56, tracking: 0.035, anchorX: 0.5 },
  { surface: 'ABC_SignSurface_Bay04_Tartuffe', text: 'TARTUFFE', capHeight: 0.42, squash: 0.54, tracking: 0.03, anchorX: 0.5 },
  { surface: 'ABC_SignSurface_Bay05_Dome', text: 'THE DOME', capHeight: 0.42, squash: 0.56, tracking: 0.04, anchorX: 0.5 },
  { surface: 'ABC_SignSurface_Bay06_ABC_East', text: 'ABC', capHeight: 0.42, squash: 0.58, tracking: 0.05, anchorX: 0.5 },
];

// Side returns of the band: lit, blank.
const BLANK_RETURNS = [
  { surface: 'ABC_SignSurface_EndWest', yaw: Math.PI / 2 },
  { surface: 'ABC_SignSurface_EndEast', yaw: -Math.PI / 2 },
] as const;

function createTexture(canvas: HTMLCanvasElement): CanvasTexture {
  const texture = new CanvasTexture(canvas);
  texture.colorSpace = SRGBColorSpace;
  texture.minFilter = LinearMipmapLinearFilter;
  texture.anisotropy = 8;
  return texture;
}

function get2d(canvas: HTMLCanvasElement): CanvasRenderingContext2D {
  const context = canvas.getContext('2d');
  if (!context) {
    throw new Error('Could not create an ABC signage canvas.');
  }
  return context;
}

function paintLightbox(context: CanvasRenderingContext2D, width: number, height: number): void {
  context.fillStyle = LIGHTBOX;
  context.fillRect(0, 0, width, height);
  // The diffuser is faintly ribbed, and a touch dimmer toward the edges.
  context.fillStyle = 'rgba(120, 100, 70, 0.05)';
  for (let y = 4; y < height; y += 7) {
    context.fillRect(0, y, width, 2);
  }
  const falloff = context.createLinearGradient(0, 0, 0, height);
  falloff.addColorStop(0, 'rgba(90, 70, 40, 0.10)');
  falloff.addColorStop(0.25, 'rgba(90, 70, 40, 0)');
  falloff.addColorStop(0.75, 'rgba(90, 70, 40, 0)');
  falloff.addColorStop(1, 'rgba(90, 70, 40, 0.10)');
  context.fillStyle = falloff;
  context.fillRect(0, 0, width, height);
}

interface CapsLayout {
  readonly capHeight: number;
  readonly squash: number;
  readonly tracking: number;
  readonly anchorX: number;
}

// Condensed caps built from a bold system grotesque squashed horizontally, so
// the weight and proportion match on every machine without shipping a font.
function paintCaps(
  context: CanvasRenderingContext2D,
  text: string,
  layout: CapsLayout,
  ink: string,
  canvasWidth: number,
  canvasHeight: number,
  pixelsPerMetre: number,
): void {
  const capPixels = layout.capHeight * pixelsPerMetre;
  const fontPixels = capPixels / 0.716;
  context.font = `800 ${fontPixels}px "Helvetica Neue", Helvetica, Arial, sans-serif`;
  context.textBaseline = 'alphabetic';
  context.textAlign = 'left';
  context.fillStyle = ink;
  context.strokeStyle = ink;
  context.lineJoin = 'miter';
  // The system face at 800 is not always heavy enough; a stroke evens it out.
  context.lineWidth = capPixels * 0.07;

  const glyphs = [...text];
  const tracking = layout.tracking * pixelsPerMetre;
  const widths = glyphs.map((glyph) => context.measureText(glyph).width * layout.squash);
  const total = widths.reduce((sum, width) => sum + width, 0) + tracking * (glyphs.length - 1);

  let cursor = canvasWidth * layout.anchorX - total / 2;
  const baseline = canvasHeight / 2 + capPixels / 2;
  for (let index = 0; index < glyphs.length; index += 1) {
    context.save();
    context.translate(cursor, baseline);
    context.scale(layout.squash, 1);
    context.strokeText(glyphs[index], 0, 0);
    context.fillText(glyphs[index], 0, 0);
    context.restore();
    cursor += widths[index] + tracking;
  }
}

function createBandMaterial(text: BaySign | null): MeshBasicMaterial {
  const canvas = document.createElement('canvas');
  canvas.width = CANVAS_WIDTH;
  canvas.height = CANVAS_HEIGHT;
  const context = get2d(canvas);
  paintLightbox(context, CANVAS_WIDTH, CANVAS_HEIGHT);
  if (text?.text) {
    paintCaps(context, text.text, text, INK, CANVAS_WIDTH, CANVAS_HEIGHT, PIXELS_PER_METRE);
  }
  return new MeshBasicMaterial({
    name: text?.text ? `ABC sign: ${text.text}` : 'ABC sign: blank return',
    map: createTexture(canvas),
    polygonOffset: true,
    polygonOffsetFactor: -1,
    polygonOffsetUnits: -1,
  });
}

function addBandPlane(
  model: Group,
  surfaceName: string,
  material: MeshBasicMaterial,
  yaw: number,
  width: number,
): void {
  const surface = model.getObjectByName(surfaceName);
  if (!surface) {
    console.warn(`[ABC signage] ${surfaceName} not found in the model.`);
    return;
  }
  const plane = new Mesh(new PlaneGeometry(width, BAND_HEIGHT), material);
  plane.name = `${surfaceName} lettering`;
  // The surface's own origin sits on its bottom edge, centred along its width.
  plane.position.set(0, BAND_HEIGHT / 2, yaw === 0 ? PLANE_Z : 0);
  if (yaw !== 0) {
    plane.position.x = Math.sign(yaw) * PLANE_Z;
    plane.rotation.y = yaw;
  }
  plane.castShadow = false;
  plane.receiveShadow = false;
  surface.add(plane);
}

// The Every Man / Smolensky end block is dark brick with a glazed upper storey.
// Its two signs are unlit-looking cream lettering with no lightbox behind:
// Smolensky on the brick band over the ground-floor glazing, Every Man across
// the upper glass. Anchors mark where each goes; the block's front face is at
// local z = +0.10, so the letters stand 2.5 cm proud of it.
interface EndBlockSign {
  readonly anchor: string;
  readonly text: string;
  readonly width: number;
  readonly height: number;
  readonly layout: CapsLayout;
}

const END_BLOCK_SIGNS: readonly EndBlockSign[] = [
  {
    anchor: 'ABC_EndBlock_SignAnchor_Smolensky',
    text: 'SMOLENSKY',
    width: 6,
    height: 0.6,
    layout: { capHeight: 0.36, squash: 0.8, tracking: 0.11, anchorX: 0.5 },
  },
  {
    anchor: 'ABC_EndBlock_SignAnchor_EveryMan',
    text: 'EVERYMAN',
    width: 7,
    height: 1,
    layout: { capHeight: 0.68, squash: 0.9, tracking: 0.14, anchorX: 0.5 },
  },
];

const END_BLOCK_FRONT_Z = 0.125;
const END_BLOCK_INK = '#eee4cf';

function addEndBlockSigns(model: Group): void {
  for (const sign of END_BLOCK_SIGNS) {
    const anchor = model.getObjectByName(sign.anchor);
    if (!anchor?.parent) {
      console.warn(`[ABC signage] ${sign.anchor} not found in the model.`);
      continue;
    }
    const canvas = document.createElement('canvas');
    canvas.width = CANVAS_WIDTH;
    canvas.height = Math.round((CANVAS_WIDTH * sign.height) / sign.width);
    const context = get2d(canvas);
    paintCaps(
      context,
      sign.text,
      sign.layout,
      END_BLOCK_INK,
      canvas.width,
      canvas.height,
      CANVAS_WIDTH / sign.width,
    );
    const plane = new Mesh(
      new PlaneGeometry(sign.width, sign.height),
      new MeshBasicMaterial({
        name: `ABC sign: ${sign.text}`,
        map: createTexture(canvas),
        alphaTest: 0.4,
      }),
    );
    plane.name = `${sign.anchor} lettering`;
    plane.position.set(anchor.position.x, anchor.position.y, END_BLOCK_FRONT_Z);
    plane.castShadow = false;
    plane.receiveShadow = false;
    anchor.parent.add(plane);
  }
}

export function addAbcSignage(model: Group): void {
  addEndBlockSigns(model);
  for (const sign of BAY_SIGNS) {
    addBandPlane(model, sign.surface, createBandMaterial(sign), 0, BAND_WIDTH);
  }
  for (const { surface, yaw } of BLANK_RETURNS) {
    // Returns are 2.8 m deep, so their plane is that wide, not the bay's.
    addBandPlane(model, surface, createBandMaterial(null), yaw, 2.8);
  }
}
