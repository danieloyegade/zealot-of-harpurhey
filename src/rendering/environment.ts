import { PMREMGenerator, Vector3, type Scene, type WebGLRenderer } from 'three';
import { VISUAL_STYLE } from './visualStyle';

// Stage 4a of the realism pass (docs/REALISM_PASS_PLAN.md) calls for a
// panoramic HDR photographed/rendered near Dreams in Blender, with a CC0
// stopgap HDRI in the meantime. Neither is available from here — no
// Blender, no network fetch of a licensed third-party asset — so this
// captures the game's *own* already-built scene once, through a
// `PMREMGenerator`, and uses that as `scene.environment` instead. It has a
// real advantage over a generic HDRI: the reflections/ambient tint it
// produces are this location's actual colours (the cold fluorescent Dreams
// tubes, the sodium lamp, this sky), not a stand-in. A real Blender-rendered
// or licensed equirectangular HDR can replace this later by swapping the
// `fromScene` call below for `PMREMGenerator.fromEquirectangular` — every
// downstream material stays the same, since they all read `scene.environment`
// the same way regardless of how it was produced.
//
// A fixed point on the pavement in front of Dreams (`worldLayout.ts`'s
// `dreams` entry, front north at x 1.5 / z 39), a few metres south of the
// frontage so the building itself is in frame rather than intersected,
// at roughly head height. One capture serves the whole map: this is
// deliberately a single global ambient/reflection source, not a
// per-location one — good enough for a soft tint and faint reflections,
// which is all Stage 4a asks for.
const CAPTURE_POSITION = new Vector3(0, 1.7, 33);

/**
 * Render the current scene once from a fixed point near Dreams, prefilter it
 * with PMREMGenerator, and install the result as `scene.environment`. Call
 * this once, after the scene has loaded and settled (its own render pass
 * needs real geometry/materials/lighting in place) — see `main.ts`, where it
 * runs immediately after `prepareScene`'s GPU warm-up, inside the same
 * loading-screen hold, so this one-shot cost never appears as a mid-game
 * stall.
 *
 * Idempotent to call more than once (a later call replaces `scene.environment`
 * with a fresh capture), but there is no reason to during a normal session —
 * the scene it captures is largely static, and a captured cube always excludes
 * the moment's HUD/UI, which never entered the Three.js scene in the first place.
 */
export function captureSceneEnvironment(renderer: WebGLRenderer, scene: Scene): void {
  const { intensity, captureSize, captureSigma, captureNear, captureFar } =
    VISUAL_STYLE.environment;
  const pmrem = new PMREMGenerator(renderer);
  const renderTarget = pmrem.fromScene(scene, captureSigma, captureNear, captureFar, {
    size: captureSize,
    position: CAPTURE_POSITION,
  });
  // `dispose()` only frees the generator's own scratch resources (blur/GGX
  // materials, its ping-pong render target); the output `renderTarget` and
  // its `.texture` — what we keep as `scene.environment` — are ours to keep.
  pmrem.dispose();
  scene.environment = renderTarget.texture;
  scene.environmentIntensity = intensity;
}

/** `?env=off` disables the environment map for A/B comparison. Any other
 * value, or its absence, leaves it on — matching how `?quality=`/`?tonemap=`
 * already resolve in `visualStyle.ts`. */
export function resolveEnvironmentMapEnabled(search: string): boolean {
  return new URLSearchParams(search).get('env') !== 'off';
}
