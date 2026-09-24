import {
  BufferGeometry,
  Group,
  type Material,
  Matrix4,
  Mesh,
  MeshPhysicalMaterial,
  Object3D,
} from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { flipTriangleWinding, geometrySignature } from './mergeStaticModelMeshes.ts';

/** Batch within articulated pivots without deleting shader-required attributes. */
export function mergeSterlingStaticParts(model: Group, articulatedNodes: ReadonlySet<string>): void {
  model.updateMatrixWorld(true);
  const meshes: Mesh<BufferGeometry, Material>[] = [];
  model.traverse((child) => {
    if (child instanceof Mesh && !Array.isArray(child.material) && geometrySignature(child.geometry)) {
      meshes.push(child as Mesh<BufferGeometry, Material>);
    }
  });

  const batches = new Map<Object3D, Map<Material, Map<string, BufferGeometry[]>>>();
  const isotropicMaterials = new Map<MeshPhysicalMaterial, MeshPhysicalMaterial>();
  const toOwner = new Matrix4();
  for (const mesh of meshes) {
    let owner: Object3D = model;
    for (let ancestor = mesh.parent; ancestor && ancestor !== model; ancestor = ancestor.parent) {
      if (articulatedNodes.has(ancestor.name)) {
        owner = ancestor;
        break;
      }
    }
    const geometry = mesh.geometry.index
      ? mesh.geometry.toNonIndexed()
      : mesh.geometry.clone();
    if (!geometry.getAttribute('normal')) geometry.computeVertexNormals();
    toOwner.copy(owner.matrixWorld).invert().multiply(mesh.matrixWorld);
    geometry.applyMatrix4(toOwner);
    if (toOwner.determinant() < 0) {
      flipTriangleWinding(geometry);
      const tangent = geometry.getAttribute('tangent');
      if (tangent) {
        for (let vertex = 0; vertex < tangent.count; vertex += 1) {
          tangent.setW(vertex, -tangent.getW(vertex));
        }
      }
    }

    let material = mesh.material;
    if (material instanceof MeshPhysicalMaterial && material.anisotropy > 0
      && !geometry.getAttribute('uv') && !geometry.getAttribute('tangent')) {
      // A few exported bike parts have no tangent frame even before batching.
      // Keep the original shared material on valid parts; only these use the
      // otherwise identical isotropic finish. A zero UV frame produces NaNs.
      let fallback = isotropicMaterials.get(material);
      if (!fallback) {
        fallback = material.clone();
        fallback.anisotropy = 0;
        fallback.anisotropyMap = null;
        isotropicMaterials.set(material, fallback);
      }
      material = fallback;
    }

    const byMaterial = batches.get(owner) ?? new Map<Material, Map<string, BufferGeometry[]>>();
    batches.set(owner, byMaterial);
    const byLayout = byMaterial.get(material) ?? new Map<string, BufferGeometry[]>();
    byMaterial.set(material, byLayout);
    const signature = geometrySignature(geometry)!;
    const geometries = byLayout.get(signature) ?? [];
    byLayout.set(signature, geometries);
    geometries.push(geometry);
  }

  for (const mesh of meshes) {
    for (const child of [...mesh.children]) mesh.parent?.attach(child);
    mesh.removeFromParent();
  }

  for (const [owner, byMaterial] of batches) {
    for (const [material, byLayout] of byMaterial) {
      for (const geometries of byLayout.values()) {
        const merged = mergeGeometries(geometries);
        for (const geometry of merged ? [merged] : geometries) {
          const mesh = new Mesh(geometry, material);
          mesh.name = `${owner.name} ${material.name}`;
          mesh.castShadow = true;
          mesh.receiveShadow = true;
          owner.add(mesh);
        }
        if (merged) geometries.forEach(geometry => geometry.dispose());
      }
    }
  }
  model.updateMatrixWorld(true);
}
