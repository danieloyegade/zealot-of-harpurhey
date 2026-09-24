import { Group, Mesh, MeshPhysicalMaterial } from 'three';
import { dequantizeModelGeometry } from './dequantizeGeometry';
import { getGltfLoader } from './gltfLoader';

// Glass exported with KHR_materials_transmission makes three.js render the
// whole opaque scene a second time, into a transmission target, every frame
// any of it is on screen. Night glazing reads just as well alpha-blended, so
// transmission becomes plain transparency here; the per-model material
// policies that run after loading still set their own glass opacity.
const TRANSMISSION_GLASS_MAXIMUM_OPACITY = 0.35;

function replaceTransmissionWithTransparency(material: unknown): void {
  if (!(material instanceof MeshPhysicalMaterial) || material.transmission <= 0) {
    return;
  }
  const opacity = Math.min(
    material.transparent ? material.opacity : 1,
    1 - material.transmission * (1 - TRANSMISSION_GLASS_MAXIMUM_OPACITY),
  );
  material.transmission = 0;
  material.transmissionMap = null;
  material.thicknessMap = null;
  material.transparent = true;
  material.opacity = opacity;
  material.depthWrite = false;
  material.needsUpdate = true;
}

function resolveAssetUrl(relativePath: string): string {
  const baseUrl = new URL(import.meta.env.BASE_URL, window.location.origin);
  return new URL(relativePath.replace(/^\/+/, ''), baseUrl).href;
}

export async function loadModel(relativePath: string): Promise<Group> {
  const assetUrl = resolveAssetUrl(relativePath);
  const gltf = await getGltfLoader().loadAsync(assetUrl);
  dequantizeModelGeometry(gltf.scene);

  gltf.scene.traverse((child) => {
    if (child instanceof Mesh) {
      child.castShadow = true;
      child.receiveShadow = true;
      const materials = Array.isArray(child.material) ? child.material : [child.material];
      materials.forEach(replaceTransmissionWithTransparency);
    }
  });

  return gltf.scene;
}
