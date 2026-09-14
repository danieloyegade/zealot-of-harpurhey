import {
  BufferAttribute,
  BufferGeometry,
  Mesh,
  MeshStandardMaterial,
  Vector2,
  type Group,
} from 'three';
import atlas from '../rendering/roadDecalAtlas.json';
import { VISUAL_STYLE } from '../rendering/visualStyle';
import type { RoadIronworkPlacement } from './createEnvironmentKit';
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
  type Random,
} from './surfaceDecals';

/*
 * Layered roads. Realism comes from surface information rather than geometry:
 *
 *   merged road planes ── tiled asphalt (albedo / roughness / normal)
 *                      └─ world-space low-frequency tone and roughness drift
 *   one decal mesh ────── repairs → potholes → cracks, seams, stains
 *                         → worn paint → tyre staining → gutter grime → wetness
 *   ironwork ──────────── gully grates and utility covers (returned to the caller)
 *
 * Placement is seeded from road names, so the same streets keep the same
 * history between sessions. Pavements follow the same model in
 * createPavementSurfaces.ts.
 */

type RoadDecalCell = keyof typeof atlas.cells;
type Decal = DecalQuad<RoadDecalCell>;

export type { GroundPoint } from './surfaceDecals';

export interface RoadSpan {
  readonly name: string;
  readonly x: number;
  readonly z: number;
  readonly width: number;
  readonly depth: number;
  /** Dashed white centre line. Defaults to true. */
  readonly centreLine?: boolean;
}

export interface RoadCrossing {
  readonly name: string;
  readonly x: number;
  readonly z: number;
  readonly rotation?: number;
}

export interface KerbLine {
  readonly name: string;
  readonly x: number;
  readonly z: number;
  readonly length: number;
  readonly axis: 'x' | 'z';
}

/** A stretch that has been dug up far more often than the rest. */
export interface RepairCluster {
  readonly x: number;
  readonly z: number;
  readonly radius: number;
  readonly count: number;
}

export interface RoadSurfaceLayout {
  readonly roads: readonly RoadSpan[];
  readonly crossings: readonly RoadCrossing[];
  readonly kerbLines: readonly KerbLine[];
  readonly repairClusters: readonly RepairCluster[];
  readonly streetlights: readonly GroundPoint[];
  readonly drains: readonly GroundPoint[];
}

interface RoadFrame {
  readonly road: RoadSpan;
  readonly axis: 'x' | 'z';
  readonly along0: number;
  readonly along1: number;
  readonly across: number;
  readonly halfWidth: number;
  readonly minX: number;
  readonly maxX: number;
  readonly minZ: number;
  readonly maxZ: number;
}

// The clean_asphalt scan covers 2.1 m.
const ROAD_TILE_METRES = 2.1;
const DECAL_HEIGHT = 0.008;
const GUTTER_INSET = 0.3;
const UK_DASH_MARK = 4;
const UK_DASH_GAP = 5;

function frameOf(road: RoadSpan): RoadFrame {
  const axis = road.width >= road.depth ? 'x' : 'z';
  const minX = road.x - road.width / 2;
  const maxX = road.x + road.width / 2;
  const minZ = road.z - road.depth / 2;
  const maxZ = road.z + road.depth / 2;
  return axis === 'x'
    ? { road, axis, along0: minX, along1: maxX, across: road.z, halfWidth: road.depth / 2, minX, maxX, minZ, maxZ }
    : { road, axis, along0: minZ, along1: maxZ, across: road.x, halfWidth: road.width / 2, minX, maxX, minZ, maxZ };
}

function toWorld(frame: RoadFrame, along: number, acrossOffset: number): GroundPoint {
  return frame.axis === 'x'
    ? { x: along, z: frame.across + acrossOffset }
    : { x: frame.across + acrossOffset, z: along };
}

function alongOf(frame: RoadFrame, point: GroundPoint): number {
  return frame.axis === 'x' ? point.x : point.z;
}

function acrossOffsetOf(frame: RoadFrame, point: GroundPoint): number {
  return (frame.axis === 'x' ? point.z : point.x) - frame.across;
}

function contains(frame: RoadFrame, point: GroundPoint, margin = 0): boolean {
  return point.x >= frame.minX - margin && point.x <= frame.maxX + margin
    && point.z >= frame.minZ - margin && point.z <= frame.maxZ + margin;
}

/**
 * Along-axis intervals of `frame` where a line at absolute across coordinate
 * `line` runs into another carriageway, so kerbs and markings stop at junctions.
 */
function junctionCuts(
  frame: RoadFrame,
  frames: readonly RoadFrame[],
  line: number,
  acrossMargin: number,
  alongMargin: number,
): Interval[] {
  const cuts: Interval[] = [];
  for (const other of frames) {
    if (other === frame) continue;
    const [across0, across1] = frame.axis === 'x'
      ? [other.minZ, other.maxZ]
      : [other.minX, other.maxX];
    if (line < across0 - acrossMargin || line > across1 + acrossMargin) continue;
    const [along0, along1] = frame.axis === 'x'
      ? [other.minX, other.maxX]
      : [other.minZ, other.maxZ];
    if (along1 < frame.along0 || along0 > frame.along1) continue;
    cuts.push([along0 - alongMargin, along1 + alongMargin]);
  }
  return cuts;
}

function createRoadMaterial(): MeshStandardMaterial {
  const variation = loadSurfaceTexture('road/road-variation', { repeat: true });
  const photo = { repeat: true, extension: 'jpg' } as const;
  const material = new MeshStandardMaterial({
    name: 'Layered road asphalt material',
    // Photo-scanned stand-in (Poly Haven clean_asphalt, CC0) until the Zealot
    // road atlas is photographed; see docs/ROAD_ATLAS.md.
    map: loadSurfaceTexture('photo/clean-asphalt-albedo', { ...photo, color: true }),
    roughnessMap: loadSurfaceTexture('photo/clean-asphalt-roughness', photo),
    normalMap: loadSurfaceTexture('photo/clean-asphalt-normal', photo),
    normalScale: new Vector2(0.8, 0.8),
    // 0.55 linear: the scan is lighter than the asphalt the decals were tuned on.
    color: 0xc4c4c4,
    roughness: 1,
    metalness: 0,
    flatShading: VISUAL_STYLE.geometry.facetedLighting,
  });
  // Two world-space samples of a small drift texture break the tile: one over
  // ~67 m for broad light/dark and warm/cool patches, one over ~19 m for
  // patchier tone and roughness. The mid drift also fades in a second, rotated
  // sample of the scan, so its 2.1 m repeat never lines up.
  material.onBeforeCompile = (shader) => {
    shader.uniforms.roadVariationMap = { value: variation };
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec2 vRoadWorld;')
      .replace(
        '#include <worldpos_vertex>',
        '#include <worldpos_vertex>\n\tvRoadWorld = ( modelMatrix * vec4( transformed, 1.0 ) ).xz;',
      );
    shader.fragmentShader = shader.fragmentShader
      .replace(
        '#include <common>',
        '#include <common>\nuniform sampler2D roadVariationMap;\nvarying vec2 vRoadWorld;',
      )
      .replace(
        '#include <map_fragment>',
        `#include <map_fragment>
	vec3 roadBroad = texture2D( roadVariationMap, vRoadWorld / 67.0 ).rgb;
	vec3 roadMid = texture2D( roadVariationMap, vRoadWorld / 19.0 + vec2( 0.37, 0.61 ) ).rgb;
	vec2 roadAltUv = mat2( 0.8, -0.6, 0.6, 0.8 ) * vMapUv * 0.73 + vec2( 0.31, 0.17 );
	diffuseColor.rgb = mix( diffuseColor.rgb, diffuse * texture2D( map, roadAltUv ).rgb, smoothstep( 0.35, 0.65, roadMid.b ) );
	float roadTone = 0.74 + roadBroad.r * 0.42 + ( roadMid.r - 0.5 ) * 0.2;
	diffuseColor.rgb *= roadTone * mix( vec3( 0.95, 0.99, 1.06 ), vec3( 1.06, 1.0, 0.93 ), roadBroad.b );`,
      )
      .replace(
        '#include <roughnessmap_fragment>',
        `#include <roughnessmap_fragment>
	// The scan averages 0.66; dry road should sit around 0.7-0.9.
	roughnessFactor = clamp( 0.25 + roughnessFactor * 0.85 + ( roadMid.g - 0.5 ) * 0.14 - ( 1.0 - roadBroad.g ) * 0.05, 0.05, 1.0 );`,
      );
  };
  material.customProgramCacheKey = () => 'zealot-layered-road-asphalt';
  return material;
}

function buildRoadGeometry(frames: readonly RoadFrame[]): BufferGeometry {
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
      positions.set([x, 0, z], vertex * 3);
      normals.set([0, 1, 0], vertex * 3);
      // World-space UVs: overlapping junctions sample identical texels, so
      // coplanar road planes cannot visibly z-fight.
      uvs.set([x / ROAD_TILE_METRES, z / ROAD_TILE_METRES], vertex * 2);
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

interface Placement {
  readonly decals: Decal[];
  readonly ironwork: RoadIronworkPlacement[];
}

/**
 * Adds one piece of road history at `along`. Returns the along-axis interval of
 * a full-width trench, which interrupts the centre line painted before it.
 */
function addRepair(
  placement: Placement,
  frame: RoadFrame,
  random: Random,
  along: number,
): Interval | null {
  const { decals } = placement;
  const halfWidth = frame.halfWidth;
  const alongAngle = frame.axis === 'x' ? 0 : Math.PI / 2;
  const clampAlong = (extent: number) => Math.min(
    frame.along1 - extent,
    Math.max(frame.along0 + extent, along),
  );
  const acrossWithin = (extent: number) =>
    random.range(-halfWidth + extent + 0.15, halfWidth - extent - 0.15);
  const push = (decal: Omit<Decal, 'x' | 'z'>, alongAt: number, acrossOffset: number) => {
    decals.push({ ...decal, ...toWorld(frame, alongAt, acrossOffset) });
  };
  const roll = random.next();

  if (roll < 0.24) {
    const length = random.range(1.2, 2.6);
    const breadth = random.range(0.8, 1.6);
    const at = clampAlong(length / 2);
    const offset = acrossWithin(breadth / 2);
    push({
      cell: random.pick(['patch-rect-a', 'patch-rect-b'] as const),
      length, breadth,
      angle: alongAngle + random.range(-0.03, 0.03),
      flipU: random.chance(0.5), flipV: random.chance(0.5),
    }, at, offset);
    if (random.chance(0.15)) {
      push({ cell: 'wet-patch-a', length: length * 0.7, breadth: breadth * 0.6, angle: random.range(0, Math.PI) }, at, offset);
    }
  } else if (roll < 0.34) {
    const length = random.range(5, Math.min(14, (frame.along1 - frame.along0) * 0.4));
    const breadth = random.range(0.5, 0.85);
    push({
      cell: 'trench', length, breadth,
      angle: alongAngle + random.range(-0.01, 0.01),
      flipU: random.chance(0.5),
      tint: random.range(0.85, 1.1),
    }, clampAlong(length / 2), acrossWithin(breadth / 2));
  } else if (roll < 0.44) {
    // A service connection cut straight across the carriageway.
    const breadth = random.range(0.55, 0.9);
    const at = clampAlong(breadth / 2 + 0.5);
    push({
      cell: 'trench', length: halfWidth * 2 - 0.1, breadth,
      angle: alongAngle + Math.PI / 2 + random.range(-0.02, 0.02),
      flipU: random.chance(0.5),
      tint: random.range(0.8, 1.12),
    }, at, 0);
    return [at - breadth / 2 - 0.15, at + breadth / 2 + 0.15];
  } else if (roll < 0.58) {
    const length = random.range(2, 4.2);
    const breadth = random.range(1.4, 2.8);
    const extent = Math.max(length, breadth) / 2;
    push({
      cell: random.pick(['patch-irregular-a', 'patch-irregular-b'] as const),
      length, breadth,
      angle: random.range(0, Math.PI * 2),
      flipV: random.chance(0.5),
    }, clampAlong(extent), acrossWithin(Math.min(extent, halfWidth - 0.4)));
  } else if (roll < 0.78) {
    // Potholes open where wheels and water work at the surface.
    const length = random.range(0.5, 1.1);
    const breadth = random.range(0.4, 0.85);
    const at = clampAlong(length);
    const offset = random.pick([
      random.sign() * (halfWidth - 0.75),
      random.sign() * (halfWidth / 2 + random.sign() * 0.8),
    ]);
    const angle = random.range(0, Math.PI * 2);
    push({ cell: random.pick(['pothole-fill-a', 'pothole-fill-b'] as const), length, breadth, angle }, at, offset);
    if (random.chance(0.4)) {
      push({ cell: 'wet-patch-a', length: length * 1.5, breadth: breadth * 1.4, angle }, at, offset);
    }
  } else if (roll < 0.9) {
    const size = random.range(1.5, 3);
    push({
      cell: 'crack-web', length: size, breadth: size * random.range(0.7, 1),
      angle: random.range(0, Math.PI * 2),
    }, clampAlong(size / 2), acrossWithin(size / 2));
  } else if (roll < 0.95) {
    const length = random.range(4, 8);
    push({
      cell: 'crack-long', length, breadth: 0.55,
      angle: alongAngle + random.range(-0.05, 0.05),
      flipU: random.chance(0.5), flipV: random.chance(0.5),
    }, clampAlong(length / 2), acrossWithin(0.3));
  } else {
    const size = random.range(0.9, 1.5);
    push({
      cell: 'oil-stain', length: size, breadth: size,
      angle: random.range(0, Math.PI * 2),
      alpha: random.range(0.6, 1),
    }, clampAlong(size), random.sign() * halfWidth / 2 + random.range(-0.3, 0.3));
  }
  return null;
}

function placeRoadDecals(layout: RoadSurfaceLayout, frames: readonly RoadFrame[]): Placement {
  const placement: Placement = { decals: [], ironwork: [] };
  const { decals, ironwork } = placement;
  const centreLineCuts = new Map<RoadFrame, Interval[]>(frames.map((frame) => [frame, []]));

  // Repairs and seams: the accumulated history of each street.
  for (const frame of frames) {
    const random = createRandom(hashString(frame.road.name));
    const length = frame.along1 - frame.along0;
    const alongAngle = frame.axis === 'x' ? 0 : Math.PI / 2;
    const cuts = centreLineCuts.get(frame)!;
    const repairCount = Math.round(length / 9);
    for (let index = 0; index < repairCount; index += 1) {
      const trench = addRepair(placement, frame, random, random.range(frame.along0, frame.along1));
      if (trench) cuts.push(trench);
    }

    if (random.chance(0.55)) {
      const offset = random.range(-0.45, 0.45);
      for (let at = frame.along0 + random.range(0, 4); at < frame.along1 - 3;) {
        const pieceLength = Math.min(random.range(6, 12), frame.along1 - at);
        if (random.chance(0.75)) {
          decals.push({
            cell: 'tar-seam', length: pieceLength, breadth: 0.1,
            angle: alongAngle, flipU: random.chance(0.5),
            ...toWorld(frame, at + pieceLength / 2, offset),
          });
        }
        at += pieceLength - 0.2;
      }
    }

    if (length > 40) {
      const covers = random.chance(0.5) ? 1 : 2;
      for (let index = 0; index < covers; index += 1) {
        const at = random.range(frame.along0 + 4, frame.along1 - 4);
        const offset = random.sign() * frame.halfWidth / 2 + random.range(-0.3, 0.3);
        const point = toWorld(frame, at, offset);
        const rotationY = frame.axis === 'x' ? 0 : Math.PI / 2;
        ironwork.push({ ...point, rotationY, width: 0.68, depth: 0.68 });
        decals.push({
          cell: random.pick(['patch-rect-a', 'patch-rect-b'] as const),
          length: 1.25, breadth: 1.25, angle: alongAngle, ...point,
        });
      }
    }
  }

  for (const cluster of layout.repairClusters) {
    const frame = frames.find((candidate) => contains(candidate, cluster));
    if (!frame) continue;
    const random = createRandom(hashString(`${cluster.x}:${cluster.z}`));
    const centre = alongOf(frame, cluster);
    for (let index = 0; index < cluster.count; index += 1) {
      const trench = addRepair(
        placement,
        frame,
        random,
        centre + random.range(-cluster.radius, cluster.radius),
      );
      if (trench) centreLineCuts.get(frame)!.push(trench);
    }
  }

  // Zebra crossings keep their authored bar layout, now as worn paint.
  const paintRandom = createRandom(hashString('road paint'));
  for (const crossing of layout.crossings) {
    const rotation = crossing.rotation ?? 0;
    for (let index = -2; index <= 2; index += 1) {
      decals.push({
        cell: paintRandom.chance(0.6) ? 'zebra-stripe-a' : 'zebra-stripe-b',
        x: crossing.x + Math.cos(rotation) * index * 0.9,
        z: crossing.z - Math.sin(rotation) * index * 0.9,
        length: 4.8,
        breadth: 0.45,
        angle: Math.atan2(Math.cos(rotation), Math.sin(rotation)),
        flipU: paintRandom.chance(0.5),
        tint: paintRandom.range(0.9, 1),
      });
    }
    for (const frame of frames) {
      if (contains(frame, crossing)) {
        const at = alongOf(frame, crossing);
        centreLineCuts.get(frame)!.push([at - 5, at + 5]);
      }
    }
  }

  // Centre lines: UK dashes, stopped short of junctions and interrupted by
  // trenches that were reinstated without repainting.
  for (const frame of frames) {
    if (frame.road.centreLine === false) continue;
    const alongAngle = frame.axis === 'x' ? 0 : Math.PI / 2;
    const cuts = [
      ...junctionCuts(frame, frames, frame.across, 0, 2.5),
      ...centreLineCuts.get(frame)!,
    ];
    for (let dash0 = frame.along0 + 2; dash0 + UK_DASH_MARK <= frame.along1; dash0 += UK_DASH_MARK + UK_DASH_GAP) {
      if (paintRandom.chance(0.07)) continue;
      const dash1 = dash0 + UK_DASH_MARK;
      const cell = paintRandom.chance(0.35) ? 'line-white-b' : 'line-white-a';
      const flipV = paintRandom.chance(0.5);
      const tint = paintRandom.range(0.82, 1);
      const alpha = paintRandom.range(0.7, 1);
      for (const [piece0, piece1] of subtractIntervals([dash0, dash1], cuts)) {
        if (piece1 - piece0 < 0.3) continue;
        decals.push({
          cell, flipV, tint, alpha,
          length: piece1 - piece0,
          breadth: 0.1,
          angle: alongAngle,
          u0: (piece0 - dash0) / UK_DASH_MARK,
          u1: (piece1 - dash0) / UK_DASH_MARK,
          ...toWorld(frame, (piece0 + piece1) / 2, 0),
        });
      }
    }
  }

  for (const line of layout.kerbLines) {
    const angle = line.axis === 'x' ? 0 : Math.PI / 2;
    const start = (line.axis === 'x' ? line.x : line.z) - line.length / 2;
    for (let at = start; at < start + line.length - 0.2;) {
      const pieceLength = Math.min(paintRandom.range(5, 7), start + line.length - at);
      const mid = at + pieceLength / 2;
      decals.push({
        cell: 'line-yellow',
        x: line.axis === 'x' ? mid : line.x,
        z: line.axis === 'x' ? line.z : mid,
        length: pieceLength + 0.02,
        breadth: 0.1,
        angle,
        flipU: paintRandom.chance(0.5),
        tint: paintRandom.range(0.78, 1),
        alpha: paintRandom.range(0.75, 1),
      });
      at += pieceLength;
    }
  }

  // Wheel paths, gutters, gullies and the water they collect.
  for (const frame of frames) {
    const random = createRandom(hashString(`${frame.road.name} wear`));
    const alongAngle = frame.axis === 'x' ? 0 : Math.PI / 2;
    const laneCentre = frame.halfWidth / 2;
    for (const offset of [-laneCentre - 0.8, -laneCentre + 0.8, laneCentre - 0.8, laneCentre + 0.8]) {
      for (let at = frame.along0 + random.range(0, 3); at < frame.along1 - 2;) {
        const pieceLength = Math.min(random.range(6, 10), frame.along1 - at);
        if (random.chance(0.72)) {
          decals.push({
            cell: 'tyre-stain', length: pieceLength, breadth: random.range(0.38, 0.55),
            angle: alongAngle, flipU: random.chance(0.5),
            alpha: random.range(0.55, 1),
            ...toWorld(frame, at + pieceLength / 2, offset + random.range(-0.08, 0.08)),
          });
        }
        at += pieceLength - 1;
      }
    }

    for (const side of [-1, 1] as const) {
      const line = frame.across + side * (frame.halfWidth - GUTTER_INSET);
      const angle = edgeInwardAngle(frame.axis, side);
      const intervals = subtractIntervals(
        [frame.along0, frame.along1],
        junctionCuts(frame, frames, line, GUTTER_INSET, 0.5),
      );
      for (const [interval0, interval1] of intervals) {
        for (let at = interval0; at < interval1 - 0.8;) {
          const pieceLength = Math.min(random.range(5, 7), interval1 - at);
          const breadth = random.range(0.55, 0.85);
          decals.push({
            cell: random.chance(0.6) ? 'gutter-grime-a' : 'gutter-grime-b',
            length: pieceLength, breadth, angle, flipU: random.chance(0.5),
            ...toWorld(frame, at + pieceLength / 2, side * (frame.halfWidth - breadth / 2)),
          });
          if (random.chance(0.35)) {
            const litterLength = Math.min(pieceLength, random.range(2.5, 5));
            decals.push({
              cell: 'gutter-litter', length: litterLength, breadth: 0.4, angle,
              flipU: random.chance(0.5),
              ...toWorld(frame, at + random.range(litterLength / 2, pieceLength - litterLength / 2), side * (frame.halfWidth - 0.2)),
            });
          }
          if (random.chance(0.22)) {
            decals.push({
              cell: 'wet-patch-b', length: random.range(1.5, 3.5), breadth: random.range(0.7, 1.2), angle,
              ...toWorld(frame, at + random.range(0.5, pieceLength - 0.5), side * (frame.halfWidth - 0.55)),
            });
          }
          at += pieceLength - 0.5;
        }

        for (let at = interval0 + random.range(4, 10); at < interval1 - 1; at += random.range(20, 28)) {
          const point = toWorld(frame, at, side * (frame.halfWidth - 0.2));
          ironwork.push({ ...point, rotationY: alongAngle, width: 0.62, depth: 0.34 });
          decals.push({
            cell: 'gutter-grime-a', length: 1.6, breadth: 0.9, angle,
            ...toWorld(frame, at, side * (frame.halfWidth - 0.45)),
          });
          if (random.chance(0.5)) {
            decals.push({
              cell: 'wet-patch-a', length: random.range(1.4, 2.2), breadth: random.range(0.9, 1.3), angle,
              ...toWorld(frame, at, side * (frame.halfWidth - 0.55)),
            });
          }
        }
      }
    }
  }

  // Damp ground under the lamps, so streetlights find something to catch.
  const wetRandom = createRandom(hashString('road wetness'));
  for (const light of layout.streetlights) {
    let best: { frame: RoadFrame; distance: number } | null = null;
    for (const frame of frames) {
      const dx = Math.max(frame.minX - light.x, 0, light.x - frame.maxX);
      const dz = Math.max(frame.minZ - light.z, 0, light.z - frame.maxZ);
      const distance = Math.hypot(dx, dz);
      if (!best || distance < best.distance) best = { frame, distance };
    }
    if (!best || best.distance > 6 || !wetRandom.chance(0.75)) continue;
    const { frame } = best;
    const along = Math.min(frame.along1 - 1.5, Math.max(frame.along0 + 1.5, alongOf(frame, light)));
    const nearest = Math.max(-frame.halfWidth, Math.min(frame.halfWidth, acrossOffsetOf(frame, light)));
    const inward = nearest - Math.sign(nearest || 1) * wetRandom.range(0.8, 1.6);
    decals.push({
      cell: wetRandom.pick(['wet-patch-a', 'wet-patch-b'] as const),
      length: wetRandom.range(1.4, 2.8), breadth: wetRandom.range(0.9, 1.8),
      angle: wetRandom.range(0, Math.PI),
      ...toWorld(frame, along, inward),
    });
    if (wetRandom.chance(0.4)) {
      decals.push({
        cell: 'wet-patch-a',
        length: wetRandom.range(0.8, 1.4), breadth: wetRandom.range(0.6, 1),
        angle: wetRandom.range(0, Math.PI),
        ...toWorld(frame, along + wetRandom.range(-2.5, 2.5), inward * 0.7),
      });
    }
  }

  for (const drain of layout.drains) {
    if (!frames.some((frame) => contains(frame, drain, 1))) continue;
    decals.push({
      cell: 'wet-patch-a', x: drain.x, z: drain.z,
      length: wetRandom.range(1.4, 2.2), breadth: wetRandom.range(1, 1.5),
      angle: wetRandom.range(0, Math.PI),
    });
  }

  return placement;
}

/** Builds the road network and returns its ironwork for batching with pavements. */
export function addRoadSurfaces(root: Group, layout: RoadSurfaceLayout): RoadIronworkPlacement[] {
  const frames = layout.roads.map(frameOf);

  const roads = new Mesh(buildRoadGeometry(frames), createRoadMaterial());
  roads.name = 'Road network — layered asphalt';
  root.add(roads);

  const { decals, ironwork } = placeRoadDecals(layout, frames);
  const decalMesh = new Mesh(
    buildDecalGeometry(decals, atlas, DECAL_HEIGHT),
    createDecalMaterial('Road decal atlas material', 'road/road-decal'),
  );
  decalMesh.name = `Road network — ${decals.length} repair, paint, grime and wetness decals`;
  // Draw before the additive light spills so those are not dimmed by decals.
  decalMesh.renderOrder = -1;
  root.add(decalMesh);

  return ironwork;
}
