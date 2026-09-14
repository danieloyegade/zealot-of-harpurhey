import {
  BoxGeometry,
  Color,
  Mesh,
  MeshStandardMaterial,
  Vector2,
  Vector4,
  type Group,
} from 'three';
import { VISUAL_STYLE } from '../rendering/visualStyle';
import { loadSurfaceTexture } from './surfaceDecals';

/*
 * Park ground from photo-scanned surfaces:
 *
 *   grass ─── leafy_grass scan, plus a second rotated sample so its 2 m repeat
 *         │   never lines up
 *         ├── bald patches from the sparse_grass scan, placed by world drift
 *         └── trodden, muddy margins along every path
 *   paths ─── clean_asphalt scan, the same tarmac as the roads
 *
 * The scans are Poly Haven CC0 stand-ins (public/assets/textures/photo/) until
 * Daniel's own surface photographs exist. UVs are projected from world metres,
 * so every box shares one texel density whatever its size or rotation.
 */

export interface ParkPath {
  readonly name: string;
  readonly startX: number;
  readonly startZ: number;
  readonly endX: number;
  readonly endZ: number;
  readonly width: number;
}

export interface ParkGround {
  readonly x: number;
  readonly z: number;
  readonly width: number;
  readonly depth: number;
  readonly paths: readonly ParkPath[];
}

type CompiledShader = Parameters<MeshStandardMaterial['onBeforeCompile']>[0];

const SLAB_THICKNESS = 0.1;
// Tops match the blockout boxes these replace: grass 8 mm above the pavement
// flags, paths 4 cm above the grass.
const GRASS_TOP = 0.02;
const PATH_TOP = 0.06;
const GRASS_TILE_METRES = 2;
const ASPHALT_TILE_METRES = 2.1;
const MAX_PATHS = 8;

const PHOTO = { repeat: true, extension: 'jpg' } as const;

/** Replaces the mesh UVs with world XZ metres divided by `tileMetres`. */
function projectWorldUvs(shader: CompiledShader, tileMetres: number): void {
  shader.vertexShader = shader.vertexShader
    .replace('#include <common>', '#include <common>\nvarying vec2 vParkWorld;')
    .replace(
      '#include <uv_vertex>',
      `#include <uv_vertex>
	vParkWorld = ( modelMatrix * vec4( position, 1.0 ) ).xz;
	vMapUv = vParkWorld / ${tileMetres.toFixed(2)};
	vRoughnessMapUv = vMapUv;
	vNormalMapUv = vMapUv;`,
    );
  shader.fragmentShader = shader.fragmentShader.replace(
    '#include <common>',
    '#include <common>\nvarying vec2 vParkWorld;',
  );
}

function createGrassMaterial(paths: readonly ParkPath[]): MeshStandardMaterial {
  if (paths.length > MAX_PATHS) {
    throw new Error(`Park grass supports at most ${MAX_PATHS} paths, got ${paths.length}.`);
  }
  const variation = loadSurfaceTexture('road/road-variation', { repeat: true });
  const worn = loadSurfaceTexture('photo/sparse-grass-albedo', { ...PHOTO, color: true });
  const wornRoughness = loadSurfaceTexture('photo/sparse-grass-roughness', PHOTO);
  const segments = Array.from({ length: MAX_PATHS }, (_, index) => {
    const path = paths[index];
    return path ? new Vector4(path.startX, path.startZ, path.endX, path.endZ) : new Vector4();
  });
  const halfWidths = Array.from({ length: MAX_PATHS }, (_, index) => (paths[index]?.width ?? 0) / 2);

  const material = new MeshStandardMaterial({
    name: 'Park grass photo material',
    map: loadSurfaceTexture('photo/leafy-grass-albedo', { ...PHOTO, color: true }),
    roughnessMap: loadSurfaceTexture('photo/leafy-grass-roughness', PHOTO),
    normalMap: loadSurfaceTexture('photo/leafy-grass-normal', PHOTO),
    normalScale: new Vector2(0.9, 0.9),
    // The scan is a sunlit autumn lawn; this pulls it toward damp, dark green.
    color: new Color(0.2, 0.34, 0.33),
    roughness: 1,
    metalness: 0,
    flatShading: VISUAL_STYLE.geometry.facetedLighting,
  });
  material.onBeforeCompile = (shader) => {
    projectWorldUvs(shader, GRASS_TILE_METRES);
    Object.assign(shader.uniforms, {
      parkVariationMap: { value: variation },
      grassWornMap: { value: worn },
      grassWornRoughnessMap: { value: wornRoughness },
      grassWornTint: { value: new Color(0.7, 0.8, 1.5) },
      parkPaths: { value: segments },
      parkPathHalfWidths: { value: halfWidths },
      parkPathCount: { value: paths.length },
    });
    shader.fragmentShader = shader.fragmentShader
      .replace(
        '#include <common>',
        `#include <common>
uniform sampler2D parkVariationMap;
uniform sampler2D grassWornMap;
uniform sampler2D grassWornRoughnessMap;
uniform vec3 grassWornTint;
uniform vec4 parkPaths[ ${MAX_PATHS} ];
uniform float parkPathHalfWidths[ ${MAX_PATHS} ];
uniform int parkPathCount;
float parkPathDistance( vec2 point ) {
	float nearest = 1e4;
	for ( int i = 0; i < ${MAX_PATHS}; i ++ ) {
		if ( i >= parkPathCount ) break;
		vec2 start = parkPaths[ i ].xy;
		vec2 along = parkPaths[ i ].zw - start;
		float t = clamp( dot( point - start, along ) / dot( along, along ), 0.0, 1.0 );
		nearest = min( nearest, length( point - start - along * t ) - parkPathHalfWidths[ i ] );
	}
	return nearest;
}`,
      )
      .replace(
        '#include <map_fragment>',
        `#include <map_fragment>
	vec3 parkBroad = texture2D( parkVariationMap, vParkWorld / 37.0 ).rgb;
	vec3 parkMid = texture2D( parkVariationMap, vParkWorld / 11.0 + vec2( 0.53, 0.21 ) ).rgb;
	vec2 grassAltUv = mat2( 0.8, -0.6, 0.6, 0.8 ) * vMapUv * 0.71 + vec2( 0.43, 0.11 );
	diffuseColor.rgb = mix( diffuseColor.rgb, diffuse * texture2D( map, grassAltUv ).rgb, smoothstep( 0.4, 0.6, parkMid.b ) );
	// People step off paths to pass and cut the corners, so the grass beside
	// them wears to mud over a ragged half metre or so.
	float trodden = 1.0 - smoothstep( 0.0, 0.2 + parkMid.g * 0.6, parkPathDistance( vParkWorld ) );
	float bald = smoothstep( 0.62, 0.8, parkBroad.r * 0.55 + parkMid.r * 0.45 );
	float grassWear = max( trodden, bald );
	vec2 wornUv = mat2( 0.6, 0.8, -0.8, 0.6 ) * vMapUv * 0.83 + vec2( 0.21, 0.67 );
	diffuseColor.rgb = mix( diffuseColor.rgb, grassWornTint * texture2D( grassWornMap, wornUv ).rgb, grassWear );
	diffuseColor.rgb *= 0.86 + parkBroad.g * 0.28;`,
      )
      .replace(
        '#include <roughnessmap_fragment>',
        `#include <roughnessmap_fragment>
	roughnessFactor = mix( 0.35 + roughnessFactor * 0.75, texture2D( grassWornRoughnessMap, wornUv ).g, grassWear );`,
      );
  };
  material.customProgramCacheKey = () => 'zealot-park-grass-photo';
  return material;
}

function createPathMaterial(): MeshStandardMaterial {
  const material = new MeshStandardMaterial({
    name: 'Park path tarmac photo material',
    map: loadSurfaceTexture('photo/clean-asphalt-albedo', { ...PHOTO, color: true }),
    roughnessMap: loadSurfaceTexture('photo/clean-asphalt-roughness', PHOTO),
    normalMap: loadSurfaceTexture('photo/clean-asphalt-normal', PHOTO),
    normalScale: new Vector2(0.8, 0.8),
    // Footpath tarmac reads a little lighter and drier than the carriageway.
    color: 0xd4d4d4,
    roughness: 1,
    metalness: 0,
    flatShading: VISUAL_STYLE.geometry.facetedLighting,
  });
  material.onBeforeCompile = (shader) => {
    projectWorldUvs(shader, ASPHALT_TILE_METRES);
    shader.fragmentShader = shader.fragmentShader.replace(
      '#include <roughnessmap_fragment>',
      `#include <roughnessmap_fragment>
	roughnessFactor = clamp( 0.3 + roughnessFactor * 0.8, 0.05, 1.0 );`,
    );
  };
  material.customProgramCacheKey = () => 'zealot-park-path-photo';
  return material;
}

/** Adds the park's grass and its tarmac paths. */
export function addParkGround(root: Group, ground: ParkGround): void {
  const grass = new Mesh(
    new BoxGeometry(ground.width, SLAB_THICKNESS, ground.depth),
    createGrassMaterial(ground.paths),
  );
  grass.name = 'Central Park grass — photo scan with trodden path margins';
  grass.position.set(ground.x, GRASS_TOP - SLAB_THICKNESS / 2, ground.z);
  grass.receiveShadow = true;
  root.add(grass);

  const pathMaterial = createPathMaterial();
  for (const path of ground.paths) {
    const deltaX = path.endX - path.startX;
    const deltaZ = path.endZ - path.startZ;
    const mesh = new Mesh(
      new BoxGeometry(path.width, SLAB_THICKNESS, Math.hypot(deltaX, deltaZ)),
      pathMaterial,
    );
    mesh.name = path.name;
    mesh.position.set(
      (path.startX + path.endX) / 2,
      PATH_TOP - SLAB_THICKNESS / 2,
      (path.startZ + path.endZ) / 2,
    );
    mesh.rotation.y = Math.atan2(deltaX, deltaZ);
    mesh.receiveShadow = true;
    root.add(mesh);
  }
}
