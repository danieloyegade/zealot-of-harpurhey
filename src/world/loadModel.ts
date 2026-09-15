import { Group, Mesh } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { assetUrl } from '../core/assetUrl';

const gltfLoader = new GLTFLoader();

export async function loadModel(relativePath: string): Promise<Group> {
  const gltf = await gltfLoader.loadAsync(assetUrl(relativePath));

  gltf.scene.traverse((child) => {
    if (child instanceof Mesh) {
      child.castShadow = true;
      child.receiveShadow = true;
    }
  });

  return gltf.scene;
}
