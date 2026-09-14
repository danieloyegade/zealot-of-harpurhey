import {
  BufferAttribute,
  BufferGeometry,
  Mesh,
  MeshStandardMaterial,
  Vector2,
  type Group,
} from 'three';
import atlas from '../rendering/pavementDecalAtlas.json';
import { VISUAL_STYLE } from '../rendering/visualStyle';
import type { RoadIronworkPlacement } from './createEnvironmentKit';
import type { RoadSpan } from './createRoadSurfaces';
import {
  buildDecalGeometry,
  createDecalMaterial,
  createRandom,
  edgeInwardAngle,
  hashString,
  loadSurfaceTexture,
  subtractIntervals,
  type DecalQuad,
  type GroundPoint,
  type Interval,
} from './surfaceDecals';

/*
 * Layered pavements, on the same model as the roads:
 *
 *   merged pavement planes ── 600 mm concrete flags in half bond, rows counted
 *                             from the kerb; per-flag tone and roughness from
 *                             the flag grid, plus world-space drift
 *   one decal mesh ────────── tarmac reinstatements → cracked flags
 *                             → kerb stones, tactile paving → gum and stains
 *                             → wall-base grime, verge edges, moss
 *                             → leaves, parking scuffs → damp
 *   ironwork ──────────────── small utility covers (returned to the caller)
 *
 * Crack and sunken-flag decals snap to the same flag grid the shader uses, so
 * they sit exactly on whole flags.
 */

type PavementDecalCell = keyof typeof atlas.cells;
type Decal = DecalQuad<PavementDecalCell>;

export interface PavementSpan {
  readonly name: string;
  readonly x: number;
  readonly z: number;
  readonly width: number;
  readonly depth: number;
  /** What the pavement's non-kerb edge meets. */
  readonly back: 'wall' | 'verge';
  /** Damper pavements collect more water and cracked, sunken flags. */
  readonly damp?: boolean;
}

export interface PavementSurfaceLayout {
  readonly pavements: readonly PavementSpan[];
  readonly roads: readonly RoadSpan[];
  readonly crossings: readonly GroundPoint[];
  readonly streetlights: readonly GroundPoint[];
  /** Bus stops and shop entrances, where gum and spills concentrate. */
  readonly hotspots: readonly GroundPoint[];
}

interface Rect {
  readonly minX: number;
  readonly maxX: number;
  readonly minZ: number;
  readonly maxZ: number;
}

interface PavementFrame extends Rect {
  readonly span: PavementSpan;
  readonly axis: 'x' | 'z';
  readonly along0: number;
  readonly along1: number;
  readonly across: number;
  readonly halfWidth: number;
  readonly top: number;
  /** Side whose edge meets a carriageway; flag rows count from this edge. */
  readonly kerbSide: -1 | 1;
  readonly kerbIntervals: readonly Interval[];
  /** Along-axis stretches where the pavement plane lies over a road. */
  readonly roadCuts: readonly Interval[];
}

const FLAG = 0.6;
const PAVEMENT_TILE_METRES = 2.4;
// Above road decals (0.008) and below the player's contact shadow (0.025).
const PAVEMENT_TOP = 0.012;
// Overlapping pavements at corners get distinct heights instead of z-fighting.
const PAVEMENT_STAGGER = 0.0005;
const DECAL_LIFT = 0.004;
const KERB_TOLERANCE = 0.3;

function rectOf(span: { x: number; z: number; width: number; depth: number }): Rect {
  return {
    minX: span.x - span.width / 2,
    maxX: span.x + span.width / 2,
    minZ: span.z - span.depth / 2,
    maxZ: span.z + span.depth / 2,
  };
}

function framePavement(span: PavementSpan, index: number, roads: readonly Rect[]): PavementFrame {
  const rect = rectOf(span);
  const axis = span.width >= span.depth ? 'x' : 'z';
  const along0 = axis === 'x' ? rect.minX : rect.minZ;
  const along1 = axis === 'x' ? rect.maxX : rect.maxZ;
  const across = axis === 'x' ? span.z : span.x;
  const halfWidth = (axis === 'x' ? span.depth : span.width) / 2;

  const roadCuts: Interval[] = [];
  const kerbs: Record<-1 | 1, Interval[]> = { [-1]: [], [1]: [] };
  for (const road of roads) {
    const [roadAcross0, roadAcross1] = axis === 'x' ? [road.minZ, road.maxZ] : [road.minX, road.maxX];
    const [roadAlong0, roadAlong1] = axis === 'x' ? [road.minX, road.maxX] : [road.minZ, road.maxZ];
    const overlap0 = Math.max(roadAlong0, along0);
    const overlap1 = Math.min(roadAlong1, along1);
    if (overlap1 <= overlap0) continue;
    if (roadAcross0 < across && roadAcross1 > across) {
      roadCuts.push([overlap0, overlap1]);
      continue;
    }
    for (const side of [-1, 1] as const) {
      const edge = across + side * halfWidth;
      const roadEdge = side < 0 ? roadAcross1 : roadAcross0;
      if (Math.abs(roadEdge - edge) <= KERB_TOLERANCE) {
        kerbs[side].push([overlap0, overlap1]);
      }
    }
  }
  const coverage = (intervals: readonly Interval[]) =>
    intervals.reduce((total, [start, end]) => total + end - start, 0);
  const kerbSide: -1 | 1 = coverage(kerbs[1]) > coverage(kerbs[-1]) ? 1 : -1;
  const kerbIntervals = kerbs[kerbSide].flatMap((interval) => subtractIntervals(interval, roadCuts));

  return {
    ...rect,
    span,
    axis,
    along0,
    along1,
    across,
    halfWidth,
    top: PAVEMENT_TOP + index * PAVEMENT_STAGGER,
    kerbSide,
    kerbIntervals,
    roadCuts,
  };
}

function toWorld(frame: PavementFrame, along: number, acrossOffset: number): GroundPoint {
  return frame.axis === 'x'
    ? { x: along, z: frame.across + acrossOffset }
    : { x: frame.across + acrossOffset, z: along };
}

/** Across offset of a point `distance` metres in from the kerb edge. */
function fromKerb(frame: PavementFrame, distance: number): number {
  return frame.kerbSide * (frame.halfWidth - distance);
}

function containsPoint(rect: Rect, point: GroundPoint, margin = 0): boolean {
  return point.x >= rect.minX - margin && point.x <= rect.maxX + margin
    && point.z >= rect.minZ - margin && point.z <= rect.maxZ + margin;
}

function createPavementMaterial(): MeshStandardMaterial {
  const variation = loadSurfaceTexture('road/road-variation', { repeat: true });
  const photo = { repeat: true, extension: 'jpg' } as const;
  const concrete = loadSurfaceTexture('photo/concrete-floor-worn-albedo', { ...photo, color: true });
  const concreteRoughness = loadSurfaceTexture('photo/concrete-floor-worn-roughness', photo);
  const concreteNormal = loadSurfaceTexture('photo/concrete-floor-worn-normal', photo);
  const material = new MeshStandardMaterial({
    name: 'Layered pavement flag material',
    map: loadSurfaceTexture('pavement/pavement-albedo', { color: true, repeat: true }),
    roughnessMap: loadSurfaceTexture('pavement/pavement-roughness', { repeat: true }),
    normalMap: loadSurfaceTexture('pavement/pavement-normal', { repeat: true }),
    normalScale: new Vector2(0.7, 0.7),
    roughness: 1,
    metalness: 0,
    flatShading: VISUAL_STYLE.geometry.facetedLighting,
  });
  // UVs are metres along the pavement and in from the kerb, divided by the
  // tile. Rebuilding the flag grid here gives every flag its own tone,
  // occasional newer replacements, and roughness, so a 2.4 m tile never
  // visibly repeats.
  // Each flag face then reads its own offset into a photo-scanned concrete
  // (Poly Haven concrete_floor_worn_001, 3 m, CC0), as every flag is a separate
  // casting. The generated tile keeps the joints, arrises and chips, and now
  // only modulates the scan.
  material.onBeforeCompile = (shader) => {
    shader.uniforms.roadVariationMap = { value: variation };
    shader.uniforms.concreteMap = { value: concrete };
    shader.uniforms.concreteRoughnessMap = { value: concreteRoughness };
    shader.uniforms.concreteNormalMap = { value: concreteNormal };
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec2 vPavementWorld;')
      .replace(
        '#include <worldpos_vertex>',
        '#include <worldpos_vertex>\n\tvPavementWorld = ( modelMatrix * vec4( transformed, 1.0 ) ).xz;',
      );
    shader.fragmentShader = shader.fragmentShader
      .replace(
        '#include <common>',
        '#include <common>\nuniform sampler2D roadVariationMap;\nuniform sampler2D concreteMap;\nuniform sampler2D concreteRoughnessMap;\nuniform sampler2D concreteNormalMap;\nvarying vec2 vPavementWorld;',
      )
      .replace(
        '#include <map_fragment>',
        `#include <map_fragment>
	vec2 flagMetres = vMapUv * ${PAVEMENT_TILE_METRES.toFixed(1)};
	float flagRow = floor( flagMetres.y / ${FLAG.toFixed(1)} );
	float flagColumn = floor( ( flagMetres.x + mod( flagRow, 2.0 ) * ${(FLAG / 2).toFixed(1)} ) / ${FLAG.toFixed(1)} );
	float flagHash = fract( sin( dot( vec2( flagColumn, flagRow ), vec2( 12.9898, 78.233 ) ) ) * 43758.5453 );
	float flagHash2 = fract( flagHash * 91.7 );
	// The per-flag offset jumps at every joint, so mip levels are chosen from
	// the continuous flag metres instead.
	vec2 concreteUv = ( flagMetres + vec2( flagHash, flagHash2 ) * 2.3 ) / 3.0;
	vec2 concreteDx = dFdx( flagMetres ) / 3.0;
	vec2 concreteDy = dFdy( flagMetres ) / 3.0;
	// 0.175 is the generated face's linear albedo and 0.093 the scan's: faces
	// keep their old brightness, joints and chips stay dark but softer.
	vec3 flagRelief = mix( vec3( 1.0 ), sampledDiffuseColor.rgb / 0.175, 0.75 );
	diffuseColor.rgb = diffuse * textureGrad( concreteMap, concreteUv, concreteDx, concreteDy ).rgb * flagRelief * 1.9;
	vec3 pavementBroad = texture2D( roadVariationMap, vPavementWorld / 53.0 ).rgb;
	float flagTone = 0.9 + flagHash * 0.14 + ( pavementBroad.r - 0.5 ) * 0.3;
	flagTone += step( 0.94, flagHash2 ) * 0.1;
	diffuseColor.rgb *= flagTone * mix( vec3( 0.97, 0.99, 1.03 ), vec3( 1.04, 1.0, 0.95 ), pavementBroad.b );`,
      )
      .replace(
        '#include <roughnessmap_fragment>',
        `#include <roughnessmap_fragment>
	float concreteRough = textureGrad( concreteRoughnessMap, concreteUv, concreteDx, concreteDy ).g;
	roughnessFactor = clamp( roughnessFactor + ( concreteRough - 0.54 ) * 0.7 + ( flagHash - 0.5 ) * 0.1 + ( pavementBroad.g - 0.5 ) * 0.1, 0.05, 1.0 );`,
      )
      .replace(
        '#include <normal_fragment_maps>',
        `#include <normal_fragment_maps>
	vec3 concreteNormal = textureGrad( concreteNormalMap, concreteUv, concreteDx, concreteDy ).xyz * 2.0 - 1.0;
	normal = normalize( normal + tbn * vec3( concreteNormal.xy * 0.6, 0.0 ) );`,
      );
  };
  material.customProgramCacheKey = () => 'zealot-layered-pavement-flags';
  return material;
}

function buildPavementGeometry(frames: readonly PavementFrame[]): BufferGeometry {
  const positions = new Float32Array(frames.length * 12);
  const normals = new Float32Array(frames.length * 12);
  const uvs = new Float32Array(frames.length * 8);
  const indices: number[] = [];
  frames.forEach((frame, index) => {
    const corners = [
      [frame.minX, frame.minZ],
      [frame.minX, frame.maxZ],
      [frame.maxX, frame.maxZ],
      [frame.maxX, frame.minZ],
    ] as const;
    corners.forEach(([x, z], corner) => {
      const vertex = index * 4 + corner;
      const along = frame.axis === 'x' ? x : z;
      const acrossOffset = (frame.axis === 'x' ? z : x) - frame.across;
      const distanceFromKerb = frame.halfWidth - frame.kerbSide * acrossOffset;
      positions.set([x, frame.top, z], vertex * 3);
      normals.set([0, 1, 0], vertex * 3);
      uvs.set([along / PAVEMENT_TILE_METRES, distanceFromKerb / PAVEMENT_TILE_METRES], vertex * 2);
    });
    const base = index * 4;
    indices.push(base, base + 1, base + 2, base, base + 2, base + 3);
  });
  const geometry = new BufferGeometry();
  geometry.setAttribute('position', new BufferAttribute(positions, 3));
  geometry.setAttribute('normal', new BufferAttribute(normals, 3));
  geometry.setAttribute('uv', new BufferAttribute(uvs, 2));
  geometry.setIndex(indices);
  geometry.computeBoundingSphere();
  return geometry;
}

function placePavementDecals(
  layout: PavementSurfaceLayout,
  frames: readonly PavementFrame[],
): { decals: Decal[]; ironwork: RoadIronworkPlacement[] } {
  const decals: Decal[] = [];
  const ironwork: RoadIronworkPlacement[] = [];

  for (const frame of frames) {
    const { span, halfWidth, kerbSide } = frame;
    const random = createRandom(hashString(`${span.name} pavement`));
    const push = (decal: Omit<Decal, 'y'>) => decals.push({ ...decal, y: frame.top + DECAL_LIFT });
    const alongAngle = frame.axis === 'x' ? 0 : Math.PI / 2;
    const length = frame.along1 - frame.along0;
    const width = halfWidth * 2;
    const rows = Math.floor(width / FLAG + 1e-6);
    const isFrontage = span.back === 'wall';
    const hasKerb = frame.kerbIntervals.length > 0;
    const free = subtractIntervals([frame.along0, frame.along1], frame.roadCuts);
    const freeLength = free.reduce((total, [start, end]) => total + end - start, 0);
    const inFree = (start: number, end: number) =>
      free.some(([free0, free1]) => start >= free0 && end <= free1);
    const randomAlong = (extent: number): number => {
      let target = random.next() * freeLength;
      for (const [free0, free1] of free) {
        if (target <= free1 - free0) {
          return Math.min(free1 - extent, Math.max(free0 + extent, free0 + target));
        }
        target -= free1 - free0;
      }
      return (frame.along0 + frame.along1) / 2;
    };
    const randomAcross = (extent: number) => {
      const limit = Math.max(0, halfWidth - extent);
      return random.range(-limit, limit);
    };

    const strip = (
      intervals: readonly Interval[],
      side: -1 | 1,
      cell: PavementDecalCell,
      minBreadth: number,
      maxBreadth: number,
      overlap: number,
    ) => {
      for (const [interval0, interval1] of intervals) {
        for (let at = interval0; at < interval1 - 0.3;) {
          const pieceLength = Math.min(random.range(5, 7), interval1 - at);
          const breadth = random.range(minBreadth, maxBreadth);
          push({
            cell, length: pieceLength, breadth,
            angle: edgeInwardAngle(frame.axis, side),
            flipU: random.chance(0.5),
            ...toWorld(frame, at + pieceLength / 2, side * (halfWidth - breadth / 2)),
          });
          // A short final piece reaches the end; stepping back by the overlap
          // from there would never advance.
          if (at + pieceLength >= interval1) break;
          at += pieceLength - overlap;
        }
      }
    };

    // Edges: kerb stones against the carriageway, grime or verge on the rest.
    if (hasKerb) {
      strip(frame.kerbIntervals, kerbSide, 'kerb-stone', 0.16, 0.16, 0);
    }
    for (const side of hasKerb ? [(-kerbSide) as -1 | 1] : [-1, 1] as const) {
      if (isFrontage) {
        strip(free, side, 'wall-base', 0.5, 0.7, 0.4);
      } else {
        strip(free, side, 'verge-edge', 0.45, 0.7, 0.4);
      }
    }

    // Tarmac reinstatements: lifted flags, service trenches, infill.
    const repairs = Math.max(1, Math.round((length * width) / 30));
    for (let index = 0; index < repairs; index += 1) {
      const roll = random.next();
      if (roll < 0.45 && rows > 0) {
        const row0 = Math.floor(random.next() * rows);
        const rowCount = Math.min(rows - row0, 1 + Math.floor(random.next() * 3));
        const columns = 2 + Math.floor(random.next() * 4);
        const offset = (row0 % 2) * (FLAG / 2);
        const start = Math.floor((randomAlong(columns * FLAG) + offset) / FLAG) * FLAG - offset;
        const end = start + columns * FLAG;
        if (!inFree(start, end)) continue;
        push({
          cell: 'tarmac-patch-a',
          length: end - start, breadth: rowCount * FLAG, angle: alongAngle,
          flipU: random.chance(0.5), flipV: random.chance(0.5),
          ...toWorld(frame, (start + end) / 2, fromKerb(frame, (row0 + rowCount / 2) * FLAG)),
        });
      } else if (roll < 0.75) {
        // A service connection trench from kerb to building line.
        const trenchWidth = random.range(0.55, 0.9);
        push({
          cell: 'tarmac-patch-a', length: trenchWidth, breadth: width, angle: alongAngle,
          flipU: random.chance(0.5),
          ...toWorld(frame, randomAlong(trenchWidth), 0),
        });
      } else {
        const size = Math.min(width * 0.9, random.range(0.8, 1.8));
        push({
          cell: 'tarmac-patch-b', length: size, breadth: size * random.range(0.7, 1),
          angle: random.range(0, Math.PI * 2),
          ...toWorld(frame, randomAlong(size), randomAcross(size / 2)),
        });
      }
    }

    // Individual flags: cracked by overrun, or sunk and holding water.
    const crackChance = span.damp ? 0.05 : 0.035;
    const sunkChance = span.damp ? 0.025 : 0.012;
    for (let row = 0; row < rows; row += 1) {
      const offset = (row % 2) * (FLAG / 2);
      for (let column = Math.ceil((frame.along0 + offset) / FLAG); (column + 1) * FLAG - offset <= frame.along1; column += 1) {
        const start = column * FLAG - offset;
        if (!inFree(start, start + FLAG)) continue;
        const roll = random.next();
        let cell: PavementDecalCell;
        if (roll < crackChance) {
          cell = random.chance(0.6) ? 'cracked-flag-a' : 'cracked-flag-b';
        } else if (roll < crackChance + sunkChance) {
          cell = 'sunken-flag-wet';
        } else {
          continue;
        }
        push({
          cell, length: FLAG, breadth: FLAG, angle: alongAngle,
          flipU: random.chance(0.5), flipV: random.chance(0.5),
          ...toWorld(frame, start + FLAG / 2, fromKerb(frame, (row + 0.5) * FLAG)),
        });
      }
    }

    // Gum, spills and bin stains, far denser on shop frontages.
    const gum = Math.round((length * width) / (isFrontage ? 14 : 40));
    for (let index = 0; index < gum; index += 1) {
      const size = random.range(1.2, 2.6);
      push({
        cell: random.chance(0.55) ? 'gum-old' : 'gum-scatter',
        length: size, breadth: size * random.range(0.7, 1),
        angle: random.range(0, Math.PI * 2),
        alpha: random.range(0.6, 1),
        ...toWorld(frame, randomAlong(size / 2), randomAcross(size / 2)),
      });
    }
    for (let index = 0; index < Math.round((length * width) / 60); index += 1) {
      const size = random.range(0.8, 1.6);
      push({
        cell: 'stain-spill', length: size, breadth: size, angle: random.range(0, Math.PI * 2),
        ...toWorld(frame, randomAlong(size / 2), randomAcross(size / 2)),
      });
    }
    if (isFrontage) {
      for (let index = 0; index < Math.round(length / 30); index += 1) {
        const size = random.range(0.8, 1.2);
        const backDistance = Math.min(width - size / 2, random.range(0.4, 0.9));
        push({
          cell: 'bin-stain', length: size, breadth: size, angle: random.range(0, Math.PI * 2),
          ...toWorld(frame, randomAlong(size / 2), -kerbSide * (halfWidth - backDistance)),
        });
      }
    }

    // Moss and lichen where the pavement meets walls and verges.
    const mossSides = hasKerb ? [(-kerbSide) as -1 | 1] : [-1, 1] as const;
    for (const side of mossSides) {
      for (let index = 0; index < Math.round(length / (isFrontage ? 14 : 9)); index += 1) {
        const size = Math.min(width, random.range(0.7, 1.5));
        push({
          cell: 'moss-lichen', length: size, breadth: size, angle: random.range(0, Math.PI * 2),
          alpha: random.range(0.6, 1),
          ...toWorld(frame, randomAlong(size / 2), side * Math.max(0, halfWidth - random.range(0.25, 0.7))),
        });
      }
    }

    // Leaves drift along verges; a few blow onto frontages.
    for (let index = 0; index < Math.round(length / (isFrontage ? 40 : 7)); index += 1) {
      const leafLength = random.range(1.5, 3.5);
      const breadth = Math.min(width, random.range(0.4, 0.8));
      push({
        cell: 'leaf-litter', length: leafLength, breadth,
        angle: alongAngle + random.range(-0.3, 0.3),
        flipU: random.chance(0.5),
        ...toWorld(frame, randomAlong(leafLength / 2), randomAcross(breadth / 2)),
      });
    }

    // Cars parked half on the kerb.
    if (isFrontage && hasKerb) {
      for (let index = 0; index < Math.round(length / 20); index += 1) {
        if (!random.chance(0.55)) continue;
        const at = randomAlong(3);
        const offset = fromKerb(frame, random.range(0.4, 0.6));
        for (const wheel of [-1.35, 1.35]) {
          push({
            cell: 'tyre-scuff', length: random.range(1.2, 2.2), breadth: 0.3, angle: alongAngle,
            flipU: random.chance(0.5),
            ...toWorld(frame, at + wheel, offset),
          });
        }
      }
    }

    // Damp: runoff along the building line and wherever the surface dips.
    for (let index = 0; index < Math.round(length / (span.damp ? 9 : 22)); index += 1) {
      const size = Math.min(width, random.range(1, 2.4));
      const againstBack = isFrontage && random.chance(0.5);
      push({
        cell: 'damp-patch', length: size, breadth: size * random.range(0.6, 1),
        angle: random.range(0, Math.PI * 2),
        ...toWorld(
          frame,
          randomAlong(size / 2),
          againstBack ? -kerbSide * (halfWidth - size / 3) : randomAcross(size / 2),
        ),
      });
    }

    // Small utility covers set into whole flags.
    if (isFrontage && rows > 0) {
      for (let index = 0; index < Math.round(length / 16); index += 1) {
        if (!random.chance(0.7)) continue;
        const row = Math.floor(random.next() * rows);
        const offset = (row % 2) * (FLAG / 2);
        const start = Math.floor((randomAlong(FLAG) + offset) / FLAG) * FLAG - offset;
        if (!inFree(start, start + FLAG)) continue;
        const stopcock = random.chance(0.5);
        ironwork.push({
          ...toWorld(frame, start + FLAG / 2, fromKerb(frame, (row + 0.5) * FLAG)),
          rotationY: alongAngle,
          width: stopcock ? 0.24 : 0.58,
          depth: stopcock ? 0.24 : 0.42,
        });
      }
    }
  }

  const pointRandom = createRandom(hashString('pavement points'));

  // Tarmac collars and damp around lamp posts.
  for (const light of layout.streetlights) {
    const frame = frames.find((candidate) => containsPoint(candidate, light, 0.2));
    if (!frame) continue;
    const y = frame.top + DECAL_LIFT;
    const size = pointRandom.range(0.8, 1.1);
    decals.push({ cell: 'tarmac-patch-b', x: light.x, z: light.z, y, length: size, breadth: size, angle: pointRandom.range(0, Math.PI) });
    if (pointRandom.chance(0.6)) {
      const damp = pointRandom.range(1.2, 2);
      decals.push({ cell: 'damp-patch', x: light.x, z: light.z, y, length: damp, breadth: damp * 0.8, angle: pointRandom.range(0, Math.PI) });
    }
  }

  // Where people wait and queue, gum and spills pile up.
  for (const hotspot of layout.hotspots) {
    const frame = frames.find((candidate) => containsPoint(candidate, hotspot, 2.5));
    if (!frame) continue;
    const y = frame.top + DECAL_LIFT;
    const along = Math.min(frame.along1 - 1, Math.max(frame.along0 + 1, frame.axis === 'x' ? hotspot.x : hotspot.z));
    const nearAcross = Math.max(-frame.halfWidth + 0.5, Math.min(frame.halfWidth - 0.5, (frame.axis === 'x' ? hotspot.z : hotspot.x) - frame.across));
    for (let index = 0; index < 3; index += 1) {
      const size = pointRandom.range(1.2, 2.2);
      decals.push({
        cell: index === 0 ? 'gum-scatter' : 'gum-old',
        ...toWorld(frame, along + pointRandom.range(-1.5, 1.5), nearAcross * pointRandom.range(0.2, 1)),
        y, length: size, breadth: size, angle: pointRandom.range(0, Math.PI * 2),
      });
    }
    if (pointRandom.chance(0.5)) {
      decals.push({
        cell: 'stain-spill',
        ...toWorld(frame, along + pointRandom.range(-1, 1), nearAcross * 0.6),
        y, length: 1.2, breadth: 1.2, angle: pointRandom.range(0, Math.PI * 2),
      });
    }
  }

  // Red blister paving at each end of the controlled crossings.
  for (const crossing of layout.crossings) {
    for (const frame of frames) {
      const along = frame.axis === 'x' ? crossing.x : crossing.z;
      const crossingAcross = frame.axis === 'x' ? crossing.z : crossing.x;
      if (along < frame.along0 + 1.2 || along > frame.along1 - 1.2) continue;
      const side: -1 | 1 = crossingAcross > frame.across ? 1 : -1;
      if (Math.abs(crossingAcross - (frame.across + side * frame.halfWidth)) > 5.5) continue;
      for (const offset of [-0.6, 0.6]) {
        decals.push({
          cell: 'tactile-red',
          ...toWorld(frame, along + offset, side * (frame.halfWidth - 0.6)),
          y: frame.top + DECAL_LIFT,
          length: 1.2, breadth: 1.2, angle: alongAngle(frame),
        });
      }
    }
  }

  return { decals, ironwork };
}

function alongAngle(frame: PavementFrame): number {
  return frame.axis === 'x' ? 0 : Math.PI / 2;
}

/**
 * Surface height of the highest pavement covering a point, or undefined off
 * the pavement network. Street furniture stands on this rather than y = 0.
 */
export function pavementTopAt(pavements: readonly PavementSpan[], x: number, z: number): number | undefined {
  let top: number | undefined;
  pavements.forEach((span, index) => {
    const rect = rectOf(span);
    if (x >= rect.minX && x <= rect.maxX && z >= rect.minZ && z <= rect.maxZ) {
      top = Math.max(top ?? -Infinity, PAVEMENT_TOP + index * PAVEMENT_STAGGER);
    }
  });
  return top;
}

/** Builds the pavement network and returns its ironwork for batching with roads. */
export function addPavementSurfaces(root: Group, layout: PavementSurfaceLayout): RoadIronworkPlacement[] {
  const roads = layout.roads.map(rectOf);
  const frames = layout.pavements.map((span, index) => framePavement(span, index, roads));

  const pavements = new Mesh(buildPavementGeometry(frames), createPavementMaterial());
  pavements.name = 'Pavement network — layered concrete flags';
  root.add(pavements);

  const { decals, ironwork } = placePavementDecals(layout, frames);
  const decalMesh = new Mesh(
    buildDecalGeometry(decals, atlas, PAVEMENT_TOP + DECAL_LIFT),
    createDecalMaterial('Pavement decal atlas material', 'pavement/pavement-decal'),
  );
  decalMesh.name = `Pavement network — ${decals.length} repair, flag, stain and edge decals`;
  decalMesh.renderOrder = -1;
  root.add(decalMesh);

  return ironwork;
}
