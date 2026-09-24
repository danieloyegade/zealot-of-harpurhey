import {
  AdditiveBlending,
  BufferAttribute,
  BufferGeometry,
  CanvasTexture,
  Color,
  DoubleSide,
  InstancedMesh,
  Matrix4,
  MeshBasicMaterial,
  Quaternion,
  Vector3,
} from 'three';
import { PUDDLE_MASK_WORLD_METRES } from '../rendering/wetSurface';
import { loadSurfaceTexture } from './surfaceDecals';

// Stage 4c of the realism pass (docs/REALISM_PASS_PLAN.md): the cheap trick
// that sells wet ground — one stretched, additive, puddle-masked streak per
// nearby emissive source (a streetlight, Dreams' tubes), lying flat on the
// ground and stretching away from its light along the direction supplied by
// the caller. Deliberately not a real reflection (no per-source render): it
// reads correctly once there's an actual puddle underneath it (the shared
// puddle mask decides that) and fades to nothing where the ground is dry.
//
// All sources share ONE InstancedMesh (one draw call), per the plan's
// "Use one InstancedMesh for all streaks" — this file owns the geometry,
// material and instancing; `createWorld.ts` supplies the actual source list
// (it already knows every streetlight's position/colour/yaw and Dreams'
// tube colour), rather than this module trying to rediscover "every
// emissive thing in the scene" itself.

export interface WetReflectionSource {
  readonly x: number;
  readonly z: number;
  /**
   * World yaw (radians) the streak stretches toward, in
   * `yawTowardNearestRoad`'s convention: local +X maps to world
   * `(cos(yaw), -sin(yaw))`. For a streetlight this is the same yaw that
   * already turns its lantern's outreach toward the road it lights, so the
   * streak naturally lies along the carriageway the lamp actually
   * illuminates.
   */
  readonly yaw: number;
  readonly color: number;
  /** Metres the streak stretches from the light's base. */
  readonly length?: number;
  /** Metres wide at the near end. */
  readonly width?: number;
  /** Peak opacity, before the puddle mask scales it down further. */
  readonly opacity?: number;
}

const DEFAULT_LENGTH = 6.5;
const DEFAULT_WIDTH = 0.9;
const DEFAULT_OPACITY = 0.55;
// Slightly above the road/pavement surface so it never z-fights with it.
const GROUND_OFFSET = 0.015;

let sharedGeometry: BufferGeometry | undefined;
let sharedGradientTexture: CanvasTexture | undefined;

/**
 * A trapezoid lying flat in XZ, local +X the stretch direction: full width
 * at x=0 (the light's base) tapering toward x=1 (scaled to `length` per
 * instance), matching how a real light's reflection narrows with distance.
 * UV.x runs 0→1 along the same axis, for the gradient alpha fade below.
 */
function getStreakGeometry(): BufferGeometry {
  if (sharedGeometry) {
    return sharedGeometry;
  }
  const positions = new Float32Array([
    0, GROUND_OFFSET, -0.5,
    0, GROUND_OFFSET, 0.5,
    1, GROUND_OFFSET, -0.12,
    1, GROUND_OFFSET, 0.12,
  ]);
  const uvs = new Float32Array([0, 0, 0, 1, 1, 0, 1, 1]);
  const geometry = new BufferGeometry();
  geometry.setAttribute('position', new BufferAttribute(positions, 3));
  geometry.setAttribute('uv', new BufferAttribute(uvs, 2));
  geometry.setIndex([0, 2, 1, 1, 2, 3]);
  sharedGeometry = geometry;
  return geometry;
}

/** White, opaque at u=0 fading to transparent at u=1 — the along-length fade. */
function getGradientTexture(): CanvasTexture {
  if (sharedGradientTexture) {
    return sharedGradientTexture;
  }
  const canvas = document.createElement('canvas');
  canvas.width = 64;
  canvas.height = 4;
  const context = canvas.getContext('2d');
  if (!context) {
    throw new Error('Could not draw the wet-reflection streak gradient.');
  }
  const gradient = context.createLinearGradient(0, 0, canvas.width, 0);
  gradient.addColorStop(0, 'rgba(255, 255, 255, 1)');
  gradient.addColorStop(0.6, 'rgba(255, 255, 255, 0.35)');
  gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');
  context.fillStyle = gradient;
  context.fillRect(0, 0, canvas.width, canvas.height);
  const texture = new CanvasTexture(canvas);
  sharedGradientTexture = texture;
  return texture;
}

function createStreakMaterial(): MeshBasicMaterial {
  const puddleMask = loadSurfaceTexture('wet/puddle-mask', { repeat: true });
  const material = new MeshBasicMaterial({
    map: getGradientTexture(),
    transparent: true,
    blending: AdditiveBlending,
    depthWrite: false,
    side: DoubleSide,
    // A raw glow, not a lit/graded surface colour — matches how the sky and
    // other emissive-only materials in this world are treated.
    toneMapped: false,
  });
  material.onBeforeCompile = (shader) => {
    shader.uniforms.puddleMask = { value: puddleMask };
    shader.uniforms.puddleMaskMetres = { value: PUDDLE_MASK_WORLD_METRES };
    // `worldpos_vertex`'s own `worldPosition` only exists under
    // USE_ENVMAP/shadows/transmission, none of which this material has, and
    // in any case never applies `instanceMatrix` to it for InstancedMesh —
    // `project_vertex` applies instancing to the local `mvPosition` only.
    // So this computes its own per-instance world position explicitly.
    shader.vertexShader = shader.vertexShader
      .replace(
        '#include <common>',
        '#include <common>\nvarying vec2 vStreakWorld;\nvarying vec3 vStreakColor;',
      )
      .replace(
        '#include <worldpos_vertex>',
        `#include <worldpos_vertex>
	vStreakWorld = ( modelMatrix * instanceMatrix * vec4( transformed, 1.0 ) ).xz;
	vStreakColor = instanceColor;`,
      );
    shader.fragmentShader = shader.fragmentShader
      .replace(
        '#include <common>',
        '#include <common>\nuniform sampler2D puddleMask;\nuniform float puddleMaskMetres;\nvarying vec2 vStreakWorld;\nvarying vec3 vStreakColor;',
      )
      .replace(
        '#include <color_fragment>',
        `#include <color_fragment>
	diffuseColor.rgb *= vStreakColor;
	// Bypasses the built-in USE_COLOR/vColor path deliberately: that path
	// requires material.vertexColors plus a geometry "color" attribute this
	// mesh does not have, where instanceColor alone is already enough here.
	float streakWet = texture2D( puddleMask, vStreakWorld / puddleMaskMetres ).r;
	diffuseColor.a *= streakWet;`,
      );
  };
  material.customProgramCacheKey = () => 'zealot-wet-reflection-streak';
  return material;
}

/**
 * One InstancedMesh covering every supplied source, or `null` if the list is
 * empty (nothing to add — callers can `root.add` the result unconditionally
 * either way, since `Group.add(null)`-shaped call sites are avoided by
 * checking first).
 */
export function createWetReflectionStreaks(
  sources: readonly WetReflectionSource[],
): InstancedMesh | null {
  if (sources.length === 0) {
    return null;
  }
  const mesh = new InstancedMesh(getStreakGeometry(), createStreakMaterial(), sources.length);
  mesh.name = 'Wet-ground light-streak reflections';

  const matrix = new Matrix4();
  const rotation = new Quaternion();
  const yAxis = new Vector3(0, 1, 0);
  const scale = new Vector3();
  const translation = new Vector3();
  sources.forEach((source, index) => {
    const length = source.length ?? DEFAULT_LENGTH;
    const width = source.width ?? DEFAULT_WIDTH;
    const opacity = source.opacity ?? DEFAULT_OPACITY;
    translation.set(source.x, 0, source.z);
    rotation.setFromAxisAngle(yAxis, source.yaw);
    scale.set(length, 1, width);
    matrix.compose(translation, rotation, scale);
    mesh.setMatrixAt(index, matrix);
    // instanceColor has no alpha channel, and material.opacity is one value
    // shared by every instance, so a source's own opacity is folded into its
    // colour's magnitude instead — under AdditiveBlending a dimmer colour and
    // a lower alpha read the same way, since both just scale how much this
    // streak adds to the frame.
    mesh.setColorAt(index, new Color(source.color).multiplyScalar(opacity));
  });
  mesh.instanceMatrix.needsUpdate = true;
  if (mesh.instanceColor) {
    mesh.instanceColor.needsUpdate = true;
  }

  return mesh;
}
