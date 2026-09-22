import type { MeshStandardMaterial } from 'three';
import { applyTextureProfile } from '../rendering/visualStyle';

/**
 * Building GLBs textured by blender/scripts/exportTexturedBuilding.py carry
 * Blender-authored base colour, ORM and normal maps. Runtime keeps every map
 * and applies the shared photographic filtering profile to each of them.
 */
export function profileAuthoredMaps(material: MeshStandardMaterial): void {
  for (const texture of [
    material.map,
    material.roughnessMap,
    material.metalnessMap,
    material.aoMap,
    material.normalMap,
  ]) {
    if (texture) {
      applyTextureProfile(texture, 'PHOTO_ENVIRONMENT');
    }
  }
}
