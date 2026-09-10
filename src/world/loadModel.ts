import { Group, Mesh } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const gltfLoader = new GLTFLoader();

function resolveAssetUrl(relativePath: string): string {
  const baseUrl = new URL(import.meta.env.BASE_URL, window.location.origin);
  return new URL(relativePath.replace(/^\/+/, ''), baseUrl).href;
}

export async function loadModel(relativePath: string): Promise<Group> {
  const assetUrl = resolveAssetUrl(relativePath);
  const gltf = await gltfLoader.loadAsync(assetUrl);

  gltf.scene.traverse((child) => {
    if (child instanceof Mesh) {
      child.castShadow = true;
      child.receiveShadow = true;
    }
  });

  return gltf.scene;
}
