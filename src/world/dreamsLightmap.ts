import {
  AdditiveBlending,
  BufferAttribute,
  BufferGeometry,
  DoubleSide,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  TextureLoader,
  type Texture,
  type Group,
} from 'three';
import { HDRLoader } from 'three/addons/loaders/HDRLoader.js';

// Stage 5 of the realism pass (docs/REALISM_PASS_PLAN.md): Dreams' baked
// lighting, produced for real by `blender/scripts/bakeLightmap.py` — see
// `public/assets/textures/lightmaps/dreams_lightmap.json`, the source of
// truth for every number below (keep the two in sync if Dreams is re-baked).
//
// These are loose files, not embedded in the GLB, so none of this goes
// through GLTFLoader — every texture needs the treatment GLTFLoader would
// otherwise give it automatically for free.

// Documented convention (dreams_lightmap.json "convention"): the bake stores
// scene-linear radiance of a white diffuse surface, and three.js's own
// lightMap shading divides by PI, so lightMapIntensity = PI reproduces the
// bake's exposure exactly rather than needing a guessed multiplier.
const LIGHTMAP_INTENSITY = Math.PI;
const AO_MAP_INTENSITY = 1;
// TEXCOORD_1 / the "Lightmap" UV set (threeChannel in the JSON). Every
// Texture defaults to channel 0; this is what makes lightMap/aoMap sample
// UV1 instead of the tiling-texture UV0 the rest of each material still uses.
const LIGHTMAP_UV_CHANNEL = 1;

// Ground patch: local frame (inside the Dreams Group, before its own
// position/rotation) extent and UV convention, from dreams_lightmap.json's
// "ground" block. Its modelFrameExtent.y is Blender Y (pre-glTF-conversion
// axis naming) — the standard Blender-Z-up -> three.js-Y-up conversion is
// three(x, y, z) = blender(x, z, -y), so local Z = -(blender Y):
// blender Y -20.25..-4.25 -> local Z 4.25 (at the wall) .. 20.25 (street side).
const GROUND_LOCAL_X: readonly [number, number] = [-16, 16];
const GROUND_LOCAL_Z: readonly [number, number] = [4.25, 20.25]; // [near the wall, far into the street]

const LIGHTMAP_BASE = `${import.meta.env.BASE_URL}assets/textures/lightmaps/`;

/**
 * The bake pipeline documents its output as already glTF-convention
 * oriented ("a loader must not flip them again" — matching how TEXCOORD_1
 * itself was written) — correct, but only GLTFLoader turns Three's own
 * `flipY` default (true) off automatically; these are loose files loaded
 * with plain loaders, so it needs doing by hand here.
 */
function configureBakedTexture(texture: Texture): Texture {
  texture.flipY = false;
  texture.channel = LIGHTMAP_UV_CHANNEL;
  texture.needsUpdate = true;
  return texture;
}

interface DreamsLightmap {
  readonly lightMap: Texture;
  readonly aoMap: Texture;
}

let cachedLightmap: Promise<DreamsLightmap> | undefined;

function loadDreamsLightmap(): Promise<DreamsLightmap> {
  cachedLightmap ??= Promise.all([
    new HDRLoader().loadAsync(`${LIGHTMAP_BASE}dreams_lightmap.hdr`),
    new TextureLoader().loadAsync(`${LIGHTMAP_BASE}dreams_ao.png`),
  ]).then(([lightMap, aoMap]) => ({
    lightMap: configureBakedTexture(lightMap),
    aoMap: configureBakedTexture(aoMap),
  }));
  return cachedLightmap;
}

/** `?lightmaps=off` disables Dreams' baked lighting for A/B comparison, the
 * same way `?env=off` (environment.ts) and `?quality=`/`?tonemap=`
 * (visualStyle.ts) already resolve — any other value, or its absence,
 * leaves it on. */
export function resolveLightmapsEnabled(search: string): boolean {
  return new URLSearchParams(search).get('lightmaps') !== 'off';
}

/**
 * Applies the baked lightmap/AO to every standard material already on
 * Dreams' model. Call before `mergeStaticModelMeshes` merges its meshes, so
 * each material is finalised the same way the rest of `applyDreamsModelPolicy`
 * already finalises materials at that point.
 */
export async function applyDreamsLightmap(model: Group): Promise<void> {
  const { lightMap, aoMap } = await loadDreamsLightmap();
  model.traverse((child) => {
    if (!(child instanceof Mesh)) {
      return;
    }
    const materials = Array.isArray(child.material) ? child.material : [child.material];
    for (const material of materials) {
      if (!(material instanceof MeshStandardMaterial)) {
        continue;
      }
      material.lightMap = lightMap;
      material.lightMapIntensity = LIGHTMAP_INTENSITY;
      material.aoMap = aoMap;
      material.aoMapIntensity = AO_MAP_INTENSITY;
      material.needsUpdate = true;
    }
  });
}

/**
 * A flat, additively blended ground patch carrying the separately baked
 * street-level pool of light in front of Dreams
 * (`dreams_ground_lightmap.hdr`) — a lightmap only, with no corresponding
 * mesh baked alongside it, so this builds one. Local to the Dreams Group:
 * the caller should add it as a *child of that Group* (not of `root`
 * directly), so it inherits Dreams' own position/rotation rather than
 * needing its own copy of that transform.
 */
export async function createDreamsGroundPatch(): Promise<Mesh> {
  const texture = configureBakedTexture(
    await new HDRLoader().loadAsync(`${LIGHTMAP_BASE}dreams_ground_lightmap.hdr`),
  );

  const [minX, maxX] = GROUND_LOCAL_X;
  const [minZ, maxZ] = GROUND_LOCAL_Z;
  const positions = new Float32Array([
    minX, 0.02, maxZ,
    maxX, 0.02, maxZ,
    minX, 0.02, minZ,
    maxX, 0.02, minZ,
  ]);
  // dreams_lightmap.json "ground.uv": v runs along Blender +Y from
  // extent.y[0] (the far/street end); local Z = -(Blender Y), so v = 0 sits
  // at the far/street edge (maxZ) and v = 1 at the near/wall edge (minZ).
  const uvs = new Float32Array([0, 0, 1, 0, 0, 1, 1, 1]);
  const geometry = new BufferGeometry();
  geometry.setAttribute('position', new BufferAttribute(positions, 3));
  geometry.setAttribute('uv', new BufferAttribute(uvs, 2));
  geometry.setIndex([0, 2, 1, 1, 2, 3]);

  const material = new MeshBasicMaterial({
    map: texture,
    transparent: true,
    blending: AdditiveBlending,
    depthWrite: false,
    // Winding intentionally not relied on for a flat, camera-agnostic glow
    // decal — matches other ground-pool materials in this world
    // (createHaloMaterial) that use DoubleSide for the same reason.
    side: DoubleSide,
    // Deliberately NOT toneMapped: false, unlike this world's other additive
    // glow materials. Those are hand-authored flat LDR colours; this is real
    // HDR bake radiance (dreams_lightmap.json groundP99 ~0.69, well above a
    // display-referred 1.0 in places) and needs the scene's normal AgX curve
    // to compress those highlights the same way it does everywhere else, or
    // mid-tones read as a garishly oversaturated, wrongly-hued flat block
    // instead of a soft gradient -- confirmed by testing both.
  });
  const mesh = new Mesh(geometry, material);
  mesh.name = 'Dreams baked ground-light patch';
  return mesh;
}
