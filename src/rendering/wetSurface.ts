import type { Texture } from 'three';

// Stage 4b of the realism pass (docs/REALISM_PASS_PLAN.md): shared GLSL
// snippets for sampling the puddle mask (`scripts/generatePuddleMask.mjs`)
// and driving wetness from it. Used by both `createRoadSurfaces.ts` and
// `createPavementSurfaces.ts`'s own `onBeforeCompile` hooks — one mask keeps
// a puddle visually continuous across a kerb, rather than each surface
// inventing its own unrelated pattern.
//
// These are plain string builders, not chunk-searching `.replace()` calls:
// each caller already owns a single, ordered `.replace()` per shader chunk
// (`map_fragment`, `roughnessmap_fragment`, `normal_fragment_maps`) for its
// own surface-specific texturing, and appends the matching snippet below
// directly inside that same call. Composing this by independently
// re-`.replace()`-ing the same chunk anchor a second time from outside would
// insert *before* each material's existing custom block (since the anchor
// text still appears at the start of the previously-inserted content) — fine
// for a commutative multiply, wrong in general, so this stays explicit.
//
// All three snippets read one local `float wetMask` computed by
// `wetSurfaceMaskSample`, which callers place in their `map_fragment`
// insertion (first in fragment-shader chunk order: map_fragment →
// roughnessmap_fragment → normal_fragment_begin → normal_fragment_maps), so
// it is already in scope by the time the other two snippets run.

// The middle of the realism plan's stated 6-10 m puddle scale. Shared so a
// puddle's ground wetness and its light-streak reflection (wetReflections.ts)
// agree on where puddles actually are.
export const PUDDLE_MASK_WORLD_METRES = 7;

export interface WetSurfaceUniformValues {
  readonly maskMap: Texture;
  /** World metres one puddle-mask tile spans. */
  readonly maskMetres: number;
  /** Albedo multiplier at full wetness (lower = darker, water absorbs light). */
  readonly darken: number;
  /** Roughness at full wetness — near 0 reads as a near-mirror puddle surface. */
  readonly wetRoughness: number;
  /** How much the perturbed normal flattens toward the flat surface normal at full wetness (0-1; water has no relief). */
  readonly normalFlatten: number;
}

export function wetSurfaceUniforms(
  values: WetSurfaceUniformValues,
): Record<string, { value: unknown }> {
  return {
    puddleMask: { value: values.maskMap },
    puddleMaskMetres: { value: values.maskMetres },
    puddleDarken: { value: values.darken },
    puddleWetRoughness: { value: values.wetRoughness },
    puddleNormalFlatten: { value: values.normalFlatten },
  };
}

export const wetSurfaceUniformDeclarations =
  'uniform sampler2D puddleMask;\nuniform float puddleMaskMetres;\nuniform float puddleDarken;\nuniform float puddleWetRoughness;\nuniform float puddleNormalFlatten;';

/**
 * Samples the mask and darkens albedo. Declares `wetMask` (used by the two
 * snippets below) — place this in the `map_fragment` insertion, after any
 * existing albedo computation, so it multiplies the surface's own colour
 * rather than replacing it.
 */
export function wetSurfaceMaskSampleAndAlbedo(worldPositionVarying: string): string {
  return `\tfloat wetMask = texture2D( puddleMask, ${worldPositionVarying} / puddleMaskMetres ).r;
	diffuseColor.rgb *= mix( 1.0, puddleDarken, wetMask );`;
}

/** Place in the `roughnessmap_fragment` insertion, after any existing roughness computation. */
export const wetSurfaceRoughness =
  '\troughnessFactor = mix( roughnessFactor, puddleWetRoughness, wetMask );';

/**
 * Place at the end of the `normal_fragment_maps` insertion, after any
 * existing normal-map perturbation. `nonPerturbedNormal` is the flat,
 * unperturbed view-space normal Three.js's own `normal_fragment_begin`
 * chunk sets before any normal map is applied — mixing the final normal
 * toward it is what "flattens" the surface: standing water has no relief.
 */
export const wetSurfaceNormalFlatten =
  '\tnormal = normalize( mix( normal, nonPerturbedNormal, wetMask * puddleNormalFlatten ) );';
