import {
  Float32BufferAttribute,
  InterleavedBufferAttribute,
  Mesh,
  type BufferGeometry,
  type Object3D,
} from 'three';

// Attributes the world code reads or rewrites as floats. Skin indices and
// weights are left in their own integer types.
const FLOAT_ATTRIBUTES = ['position', 'normal', 'tangent', 'uv', 'uv1', 'uv2', 'uv3', 'color'];

/**
 * Models opted in to quantisation (config/asset-optimization.json) store
 * positions as 16-bit integers with the dequantising scale on the node. That
 * renders fine, but mergeStaticModelMeshes() bakes each mesh's world matrix
 * into its vertices, and writing metres into an integer array truncates them.
 * Turn such attributes back into floats; the node transform stays as
 * authored, so every vertex lands exactly where it did.
 *
 * Meshopt also pads quantised attributes out to 4-byte strides, which three.js
 * loads as InterleavedBufferAttribute, and mergeStaticModelMeshes() refuses
 * to merge those. Both cases become plain Float32 attributes here.
 *
 * Models that were not quantised already hold tightly packed Float32 arrays
 * and are skipped.
 */
export function dequantizeModelGeometry(model: Object3D): void {
  const seen = new Set<BufferGeometry>();
  model.traverse((child) => {
    if (!(child instanceof Mesh) || seen.has(child.geometry)) {
      return;
    }
    seen.add(child.geometry);

    let changed = false;
    for (const name of FLOAT_ATTRIBUTES) {
      const attribute = child.geometry.getAttribute(name);
      if (!attribute) {
        continue;
      }
      const interleaved = attribute instanceof InterleavedBufferAttribute;
      const plainFloats = !interleaved && attribute.array instanceof Float32Array;
      if (plainFloats) {
        continue;
      }
      const { count, itemSize } = attribute;
      const floats = new Float32Array(count * itemSize);
      for (let vertex = 0; vertex < count; vertex += 1) {
        for (let component = 0; component < itemSize; component += 1) {
          // getComponent() applies normalisation, so normals and UVs come back in range.
          floats[vertex * itemSize + component] = attribute.getComponent(vertex, component);
        }
      }
      child.geometry.setAttribute(name, new Float32BufferAttribute(floats, itemSize));
      changed = true;
    }
    if (changed) {
      // Bounds were derived from the integer positions; recompute lazily.
      child.geometry.boundingBox = null;
      child.geometry.boundingSphere = null;
    }
  });
}
