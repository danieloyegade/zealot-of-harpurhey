import {
  BufferGeometry,
  Group,
  InstancedMesh,
  InterleavedBufferAttribute,
  type Material,
  Matrix4,
  Mesh,
  SkinnedMesh,
} from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

export interface StaticModelMergeStats {
  readonly sourceMeshes: number;
  readonly mergedMeshes: number;
  readonly removedMeshes: number;
}

interface MergeBatch {
  readonly material: Material;
  readonly geometries: BufferGeometry[];
  readonly meshes: Mesh[];
  readonly castShadow: boolean;
  readonly receiveShadow: boolean;
  readonly renderOrder: number;
  readonly layersMask: number;
  readonly frustumCulled: boolean;
}

export function geometrySignature(geometry: BufferGeometry): string | undefined {
  if (Object.keys(geometry.morphAttributes).length > 0) {
    return undefined;
  }

  const attributes: string[] = [];
  for (const name of Object.keys(geometry.attributes).sort()) {
    const attribute = geometry.getAttribute(name);
    if (attribute instanceof InterleavedBufferAttribute) {
      return undefined;
    }
    attributes.push(
      `${name}:${attribute.array.constructor.name}:${attribute.itemSize}:${Number(attribute.normalized)}`,
    );
  }

  return `${geometry.index ? 'indexed' : 'unindexed'}|${attributes.join('|')}`;
}

export function flipTriangleWinding(geometry: BufferGeometry): void {
  if (geometry.index) {
    for (let index = 0; index + 2 < geometry.index.count; index += 3) {
      const second = geometry.index.getX(index + 1);
      geometry.index.setX(index + 1, geometry.index.getX(index + 2));
      geometry.index.setX(index + 2, second);
    }
    geometry.index.needsUpdate = true;
    return;
  }

  for (const attribute of Object.values(geometry.attributes)) {
    if (attribute instanceof InterleavedBufferAttribute) {
      continue;
    }
    for (let vertex = 0; vertex + 2 < attribute.count; vertex += 3) {
      for (let component = 0; component < attribute.itemSize; component += 1) {
        const second = attribute.getComponent(vertex + 1, component);
        attribute.setComponent(
          vertex + 1,
          component,
          attribute.getComponent(vertex + 2, component),
        );
        attribute.setComponent(vertex + 2, component, second);
      }
    }
    attribute.needsUpdate = true;
  }
}

/**
 * Collapse a static GLB's opaque meshes into one mesh per compatible material.
 *
 * Artist-authored exports often contain hundreds of tiny objects. Keeping that
 * hierarchy at runtime makes the CPU submit hundreds of draw calls even when
 * the whole building is static. Transparent surfaces are deliberately left
 * alone because merging them would change Three.js's object-level sort order.
 * Animated, instanced, morph-target and multi-material meshes are also kept.
 */
export function mergeStaticModelMeshes(model: Group): StaticModelMergeStats {
  model.updateMatrixWorld(true);
  const rootInverse = new Matrix4().copy(model.matrixWorld).invert();
  const meshes: Mesh[] = [];

  model.traverse((child) => {
    if (
      child instanceof Mesh &&
      !(child instanceof SkinnedMesh) &&
      !(child instanceof InstancedMesh) &&
      !Array.isArray(child.material) &&
      child.visible &&
      !child.material.transparent &&
      geometrySignature(child.geometry)
    ) {
      meshes.push(child);
    }
  });

  const batches = new Map<Material, Map<string, MergeBatch>>();
  const toRoot = new Matrix4();

  for (const mesh of meshes) {
    const signature = geometrySignature(mesh.geometry);
    if (!signature || Array.isArray(mesh.material)) {
      continue;
    }

    const key = [
      signature,
      Number(mesh.castShadow),
      Number(mesh.receiveShadow),
      mesh.renderOrder,
      mesh.layers.mask,
      Number(mesh.frustumCulled),
    ].join('|');
    const bySignature = batches.get(mesh.material) ?? new Map<string, MergeBatch>();
    batches.set(mesh.material, bySignature);
    let batch = bySignature.get(key);
    if (!batch) {
      batch = {
        material: mesh.material,
        geometries: [],
        meshes: [],
        castShadow: mesh.castShadow,
        receiveShadow: mesh.receiveShadow,
        renderOrder: mesh.renderOrder,
        layersMask: mesh.layers.mask,
        frustumCulled: mesh.frustumCulled,
      };
      bySignature.set(key, batch);
    }

    const geometry = mesh.geometry.clone();
    toRoot.copy(rootInverse).multiply(mesh.matrixWorld);
    geometry.applyMatrix4(toRoot);
    if (toRoot.determinant() < 0) {
      flipTriangleWinding(geometry);
    }
    batch.geometries.push(geometry);
    batch.meshes.push(mesh);
  }

  let mergedMeshes = 0;
  let removedMeshes = 0;
  for (const bySignature of batches.values()) {
    for (const batch of bySignature.values()) {
      if (batch.meshes.length < 2) {
        batch.geometries[0]?.dispose();
        continue;
      }

      const geometry = mergeGeometries(batch.geometries);
      for (const sourceGeometry of batch.geometries) {
        sourceGeometry.dispose();
      }
      if (!geometry) {
        continue;
      }

      for (const sourceMesh of batch.meshes) {
        for (const child of [...sourceMesh.children]) {
          model.attach(child);
        }
        sourceMesh.removeFromParent();
      }

      geometry.computeBoundingBox();
      geometry.computeBoundingSphere();
      const merged = new Mesh(geometry, batch.material);
      merged.name = `${model.name || 'Static model'} — ${batch.material.name || 'material'} batch`;
      merged.castShadow = batch.castShadow;
      merged.receiveShadow = batch.receiveShadow;
      merged.renderOrder = batch.renderOrder;
      merged.layers.mask = batch.layersMask;
      merged.frustumCulled = batch.frustumCulled;
      merged.userData.performanceBatch = true;
      model.add(merged);
      mergedMeshes += 1;
      removedMeshes += batch.meshes.length;
    }
  }

  model.updateMatrixWorld(true);
  return {
    sourceMeshes: meshes.length,
    mergedMeshes,
    removedMeshes,
  };
}
