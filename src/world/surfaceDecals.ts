import {
  BufferAttribute,
  BufferGeometry,
  ClampToEdgeWrapping,
  MeshStandardMaterial,
  NoColorSpace,
  RepeatWrapping,
  SRGBColorSpace,
  TextureLoader,
  Vector2,
  type Texture,
} from 'three';
import { applyTextureProfile, VISUAL_STYLE } from '../rendering/visualStyle';

/*
 * Shared machinery for layered ground surfaces (roads, pavements): texture
 * loading, seeded placement, interval clipping and merged decal meshes drawn
 * from a cell atlas described by a JSON layout.
 */

export type Interval = readonly [number, number];

export interface GroundPoint {
  readonly x: number;
  readonly z: number;
}

export interface DecalAtlasCell {
  readonly x: number;
  readonly y: number;
  readonly w: number;
  readonly h: number;
  readonly layer: number;
}

export interface DecalAtlas<Cell extends string> {
  readonly size: number;
  readonly cells: Readonly<Record<Cell, DecalAtlasCell>>;
}

export interface DecalQuad<Cell extends string> {
  readonly cell: Cell;
  readonly x: number;
  readonly z: number;
  /** Height of the quad; defaults to the mesh's surface height. */
  readonly y?: number;
  /** Extent along the cell's u axis. */
  readonly length: number;
  /** Extent along the cell's v axis. */
  readonly breadth: number;
  /** Direction of the cell's u axis in the XZ plane, radians from +X toward +Z. */
  readonly angle: number;
  readonly flipU?: boolean;
  readonly flipV?: boolean;
  /** Sub-range of the cell along u, for pieces cut short by a junction. */
  readonly u0?: number;
  readonly u1?: number;
  readonly tint?: number;
  readonly alpha?: number;
}

const loader = new TextureLoader();
const textureCache = new Map<string, Texture>();

/** Loads `assets/textures/<path>.<extension>`, sharing one texture per path and mode. */
export function loadSurfaceTexture(
  path: string,
  {
    color = false,
    repeat = false,
    extension = 'png',
  }: { color?: boolean; repeat?: boolean; extension?: 'png' | 'jpg' } = {},
): Texture {
  const key = `${path}.${extension}:${color}:${repeat}`;
  const cached = textureCache.get(key);
  if (cached) {
    return cached;
  }
  const texture = loader.load(`${import.meta.env.BASE_URL}assets/textures/${path}.${extension}`);
  texture.name = path;
  texture.colorSpace = color ? SRGBColorSpace : NoColorSpace;
  texture.wrapS = repeat ? RepeatWrapping : ClampToEdgeWrapping;
  texture.wrapT = texture.wrapS;
  applyTextureProfile(texture, 'PHOTO_ENVIRONMENT');
  textureCache.set(key, texture);
  return texture;
}

export function hashString(text: string): number {
  let hash = 2166136261;
  for (let index = 0; index < text.length; index += 1) {
    hash = Math.imul(hash ^ text.charCodeAt(index), 16777619);
  }
  return hash >>> 0;
}

function mulberry32(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

export function createRandom(seed: number) {
  const next = mulberry32(seed);
  return {
    next,
    range: (min: number, max: number) => min + next() * (max - min),
    chance: (probability: number) => next() < probability,
    pick: <T>(items: readonly T[]): T => items[Math.floor(next() * items.length)],
    sign: (): -1 | 1 => (next() < 0.5 ? -1 : 1),
  };
}

export type Random = ReturnType<typeof createRandom>;

export function subtractIntervals(base: Interval, cuts: readonly Interval[]): Interval[] {
  let pieces: Interval[] = [base];
  for (const [cut0, cut1] of cuts) {
    pieces = pieces.flatMap(([piece0, piece1]): Interval[] => {
      if (cut1 <= piece0 || cut0 >= piece1) {
        return [[piece0, piece1]];
      }
      const kept: Interval[] = [];
      if (cut0 > piece0) kept.push([piece0, cut0]);
      if (cut1 < piece1) kept.push([cut1, piece1]);
      return kept;
    });
  }
  return pieces;
}

/**
 * Angle for a strip along an axis-aligned edge at `side` of its surface whose
 * cell v = 0 lies on that edge and whose v axis points back into the surface.
 */
export function edgeInwardAngle(axis: 'x' | 'z', side: -1 | 1): number {
  if (axis === 'x') {
    return side < 0 ? 0 : Math.PI;
  }
  return side < 0 ? -Math.PI / 2 : Math.PI / 2;
}

export function createDecalMaterial(name: string, texturePrefix: string): MeshStandardMaterial {
  return new MeshStandardMaterial({
    name,
    map: loadSurfaceTexture(`${texturePrefix}-albedo`, { color: true }),
    roughnessMap: loadSurfaceTexture(`${texturePrefix}-roughness`),
    normalMap: loadSurfaceTexture(`${texturePrefix}-normal`),
    normalScale: new Vector2(0.8, 0.8),
    roughness: 1,
    metalness: 0,
    vertexColors: true,
    transparent: true,
    depthWrite: false,
    polygonOffset: true,
    polygonOffsetFactor: -2,
    polygonOffsetUnits: -2,
    flatShading: VISUAL_STYLE.geometry.facetedLighting,
  });
}

export function buildDecalGeometry<Cell extends string>(
  decals: readonly DecalQuad<Cell>[],
  atlas: DecalAtlas<Cell>,
  surfaceHeight: number,
): BufferGeometry {
  // One mesh draws in index order, so sorting by layer is the stacking order.
  const sorted = [...decals].sort(
    (a, b) => atlas.cells[a.cell].layer - atlas.cells[b.cell].layer,
  );
  const positions = new Float32Array(sorted.length * 12);
  const normals = new Float32Array(sorted.length * 12);
  const uvs = new Float32Array(sorted.length * 8);
  const colors = new Float32Array(sorted.length * 16);
  const indices: number[] = [];
  sorted.forEach((decal, index) => {
    const cell = atlas.cells[decal.cell];
    const ux = Math.cos(decal.angle);
    const uz = Math.sin(decal.angle);
    const vx = -uz;
    const vz = ux;
    const u0 = decal.u0 ?? 0;
    const u1 = decal.u1 ?? 1;
    const tint = decal.tint ?? 1;
    const alpha = decal.alpha ?? 1;
    const height = decal.y ?? surfaceHeight;
    const corners = [[0, 0], [1, 0], [1, 1], [0, 1]] as const;
    corners.forEach(([s, t], corner) => {
      const vertex = index * 4 + corner;
      positions.set([
        decal.x + ux * (s - 0.5) * decal.length + vx * (t - 0.5) * decal.breadth,
        height,
        decal.z + uz * (s - 0.5) * decal.length + vz * (t - 0.5) * decal.breadth,
      ], vertex * 3);
      normals.set([0, 1, 0], vertex * 3);
      const cellU = u0 + (u1 - u0) * (decal.flipU ? 1 - s : s);
      const cellV = decal.flipV ? 1 - t : t;
      // Atlas image rows grow downward; texture V grows upward.
      uvs.set([
        (cell.x + cellU * cell.w) / atlas.size,
        1 - (cell.y + cellV * cell.h) / atlas.size,
      ], vertex * 2);
      colors.set([tint, tint, tint, alpha], vertex * 4);
    });
    // Keep every quad facing up regardless of angle.
    const edgeAx = ux * decal.length;
    const edgeAz = uz * decal.length;
    const edgeBx = edgeAx + vx * decal.breadth;
    const edgeBz = edgeAz + vz * decal.breadth;
    const base = index * 4;
    if (edgeAz * edgeBx - edgeAx * edgeBz > 0) {
      indices.push(base, base + 1, base + 2, base, base + 2, base + 3);
    } else {
      indices.push(base, base + 2, base + 1, base, base + 3, base + 2);
    }
  });
  const geometry = new BufferGeometry();
  geometry.setAttribute('position', new BufferAttribute(positions, 3));
  geometry.setAttribute('normal', new BufferAttribute(normals, 3));
  geometry.setAttribute('uv', new BufferAttribute(uvs, 2));
  geometry.setAttribute('color', new BufferAttribute(colors, 4));
  geometry.setIndex(indices);
  geometry.computeBoundingSphere();
  return geometry;
}
