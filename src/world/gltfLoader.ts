import type { WebGLRenderer } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';

/**
 * Runtime models are optimised at build time (scripts/optimizeRuntimeAssets.mjs):
 * textures become GPU-compressed KTX2 and are transcoded to whatever format
 * this device's GPU samples natively, instead of being decoded to RGBA and
 * uploaded at four bytes a pixel.
 *
 * KTX2Loader normally asks the renderer what the GPU supports, but models
 * start loading before anything needs a renderer, so ask a throwaway context.
 */
function createKtx2Loader(): KTX2Loader {
  const loader = new KTX2Loader();
  const baseUrl = new URL(import.meta.env.BASE_URL, window.location.origin);
  loader.setTranscoderPath(new URL('basis/', baseUrl).href);

  const canvas = document.createElement('canvas');
  const gl = canvas.getContext('webgl2');
  if (gl) {
    // Only the two members detectSupport() reads.
    const probe = {
      isWebGPURenderer: false,
      extensions: {
        has: (name: string) => gl.getExtension(name) !== null,
        get: (name: string) => gl.getExtension(name),
      },
    };
    loader.detectSupport(probe as unknown as WebGLRenderer);
    gl.getExtension('WEBGL_lose_context')?.loseContext();
  } else {
    // No WebGL2 at all: transcode to plain RGBA so loading still completes.
    loader.workerConfig = {
      astcSupported: false,
      astcHDRSupported: false,
      etc1Supported: false,
      etc2Supported: false,
      dxtSupported: false,
      bptcSupported: false,
      pvrtcSupported: false,
    };
  }
  return loader;
}

let sharedLoader: GLTFLoader | null = null;

/** The one glTF loader for the game: KTX2 textures and Meshopt geometry. */
export function getGltfLoader(): GLTFLoader {
  if (sharedLoader === null) {
    sharedLoader = new GLTFLoader();
    sharedLoader.setKTX2Loader(createKtx2Loader());
    sharedLoader.setMeshoptDecoder(MeshoptDecoder);
  }
  return sharedLoader;
}
