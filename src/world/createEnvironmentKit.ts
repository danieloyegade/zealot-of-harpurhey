import {
  BoxGeometry,
  CircleGeometry,
  CylinderGeometry,
  DodecahedronGeometry,
  Group,
  InstancedMesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  Object3D,
  type BufferGeometry,
  type Material,
} from 'three';
import { createWorldMaterial } from '../rendering/worldMaterials';

interface InstanceTransform {
  readonly x: number;
  readonly y: number;
  readonly z: number;
  readonly rotationX?: number;
  readonly rotationY?: number;
  readonly rotationZ?: number;
  readonly scaleX?: number;
  readonly scaleY?: number;
  readonly scaleZ?: number;
}

const unitBox = new BoxGeometry(1, 1, 1);
const unitCylinder = new CylinderGeometry(1, 1, 1, 7);
const unitCircle = new CircleGeometry(1, 12);
const unitCrown = new DodecahedronGeometry(1, 0);
const instanceDummy = new Object3D();

function addInstances(
  root: Group,
  name: string,
  geometry: BufferGeometry,
  material: Material,
  transforms: readonly InstanceTransform[],
): InstancedMesh {
  const mesh = new InstancedMesh(geometry, material, transforms.length);
  mesh.name = name;
  mesh.frustumCulled = true;
  transforms.forEach((transform, index) => {
    instanceDummy.position.set(transform.x, transform.y, transform.z);
    instanceDummy.rotation.set(
      transform.rotationX ?? 0,
      transform.rotationY ?? 0,
      transform.rotationZ ?? 0,
    );
    instanceDummy.scale.set(
      transform.scaleX ?? 1,
      transform.scaleY ?? 1,
      transform.scaleZ ?? 1,
    );
    instanceDummy.updateMatrix();
    mesh.setMatrixAt(index, instanceDummy.matrix);
  });
  mesh.instanceMatrix.needsUpdate = true;
  root.add(mesh);
  return mesh;
}

const treePositions = [
  [-15, -10], [-8, -11], [9, -11], [15, -8],
  [-17, -3], [17, -2], [-15, 9], [-8, 11],
  [9, 10], [15, 8], [-4, -6], [5, 6],
] as const;

/** Low-cost tree and bench variants shared by the park and later city blocks. */
export function addParkEdgeEnvironmentKit(root: Group): void {
  const trunkMaterial = createWorldMaterial('tree-bark-temporary', {
    repeatX: 2,
    repeatY: 2,
  });
  const foliage = createWorldMaterial('foliage-dark-overhaul', {
    repeatX: 2,
    repeatY: 2,
    tint: 0x3d6740,
    roughness: 1,
  });
  const foliageLit = createWorldMaterial('foliage-dark-overhaul', {
    repeatX: 2,
    repeatY: 2,
    tint: 0x70763a,
    emissive: 0x5a300b,
    emissiveIntensity: 0.13,
    roughness: 1,
  });

  addInstances(root, 'Environment kit — instanced tree trunks', unitCylinder, trunkMaterial,
    treePositions.map(([x, z], index) => ({
      x, y: 0.78 + (index % 3) * 0.05, z,
      scaleX: 0.14 + (index % 4) * 0.012,
      scaleY: 1.55 + (index % 3) * 0.1,
      scaleZ: 0.16 + (index % 2) * 0.018,
      rotationY: index * 0.47,
    })),
  );

  const crowns = treePositions.map(([x, z], index) => ({
    x: x + (index % 2 === 0 ? -0.18 : 0.16),
    y: 2.12 + (index % 4) * 0.08,
    z,
    scaleX: 1.02 + (index % 3) * 0.09,
    scaleY: 1.18 + (index % 4) * 0.1,
    scaleZ: 0.86 + (index % 3) * 0.06,
    rotationX: (index % 3) * 0.11,
    rotationY: index * 0.73,
    rotationZ: (index % 2) * 0.08,
  }));
  addInstances(root, 'Environment kit — instanced dark tree crowns', unitCrown, foliage,
    crowns.filter((_, index) => index % 4 !== 0));
  addInstances(root, 'Environment kit — instanced amber tree crowns', unitCrown, foliageLit,
    crowns.filter((_, index) => index % 4 === 0));

  const upperCrowns = treePositions.flatMap(([x, z], index) => [
    {
      x: x + (index % 2 === 0 ? 0.28 : -0.25), y: 2.82, z: z + 0.08,
      scaleX: 0.86, scaleY: 0.67 + (index % 3) * 0.08, scaleZ: 0.7,
      rotationY: index * 0.41,
    },
    {
      x: x + (index % 3 === 0 ? 0.78 : -0.68), y: 1.94, z: z + 0.16,
      scaleX: 0.8, scaleY: 0.56 + (index % 2) * 0.08, scaleZ: 0.69,
      rotationX: index * 0.13, rotationY: index * 0.59, rotationZ: index * 0.07,
    },
  ]);
  addInstances(root, 'Environment kit — instanced tree crown clusters', unitCrown, foliage, upperCrowns);

  const benchPlacements = [
    [-12, -14, 0], [12, 14, Math.PI], [-19, 7, Math.PI / 2],
    [-5.8, -14, 0.05],
  ] as const;
  const timber = createWorldMaterial('metal-oxidised-overhaul', {
    tint: 0x754b30,
    roughness: 0.96,
  });
  const slats: InstanceTransform[] = [];
  const legs: InstanceTransform[] = [];
  for (const [x, z, rotationY] of benchPlacements) {
    for (const localZ of [-0.18, 0, 0.18]) {
      const offsetX = Math.sin(rotationY) * localZ;
      const offsetZ = Math.cos(rotationY) * localZ;
      slats.push({ x: x + offsetX, y: 0.57, z: z + offsetZ, rotationY, scaleX: 2.1, scaleY: 0.11, scaleZ: 0.14 });
    }
    for (const localX of [-0.78, 0.78]) {
      legs.push({
        x: x + Math.cos(rotationY) * localX,
        y: 0.28,
        z: z - Math.sin(rotationY) * localX,
        rotationY,
        scaleX: 0.12,
        scaleY: 0.56,
        scaleZ: 0.36,
      });
    }
  }
  addInstances(root, 'Environment kit — instanced bench slats', unitBox, timber, slats);
  addInstances(root, 'Environment kit — instanced bench frames', unitBox,
    new MeshStandardMaterial({ color: 0x24282a, roughness: 0.92 }), legs);

  const soil = createWorldMaterial('soil-litter-hero', { roughness: 1 });
  addInstances(root, 'Environment kit — park bare-soil treatments', unitBox, soil, [
    { x: -14.7, y: 0.018, z: -9.8, rotationY: 0.2, scaleX: 2.6, scaleY: 0.025, scaleZ: 1.7 },
    { x: -7.9, y: 0.019, z: -11.1, rotationY: -0.3, scaleX: 2.1, scaleY: 0.025, scaleZ: 1.25 },
    { x: 8.8, y: 0.019, z: -11, rotationY: 0.42, scaleX: 2.4, scaleY: 0.025, scaleZ: 1.45 },
    { x: -5.1, y: 0.02, z: 3.1, rotationY: -0.18, scaleX: 2.8, scaleY: 0.026, scaleZ: 1.25 },
    { x: 4.8, y: 0.02, z: 1.8, rotationY: 0.36, scaleX: 2.2, scaleY: 0.026, scaleZ: 1.05 },
    { x: 1.7, y: 0.021, z: 8.2, rotationY: -0.42, scaleX: 1.75, scaleY: 0.027, scaleZ: 0.82 },
  ]);

  addInstances(root, 'Environment kit — park-edge shrub variants', unitCrown, foliage, [
    { x: -10.8, y: 0.48, z: 1.5, rotationY: 0.4, scaleX: 0.92, scaleY: 0.48, scaleZ: 0.68 },
    { x: 11.5, y: 0.42, z: -4.2, rotationY: -0.6, scaleX: 0.78, scaleY: 0.42, scaleZ: 0.86 },
    { x: -13.4, y: 0.37, z: -7.2, rotationY: 0.9, scaleX: 0.7, scaleY: 0.37, scaleZ: 0.62 },
  ]);
}

/** Authored North Road clusters, batched by reusable asset type. */
export function addHeroStreetEnvironmentKit(root: Group): void {
  const metal = createWorldMaterial('metal-oxidised-overhaul', {
    tint: 0x30383a,
    roughness: 0.84,
    metalness: 0.18,
  });
  addInstances(root, 'Environment kit — battered bollards', unitCylinder, metal, [
    { x: -16.7, y: 0.41, z: -19.7, scaleX: 0.12, scaleY: 0.82, scaleZ: 0.12 },
    { x: -14.9, y: 0.41, z: -19.7, rotationZ: 0.04, scaleX: 0.12, scaleY: 0.82, scaleZ: 0.12 },
    { x: -7.8, y: 0.41, z: -30.1, scaleX: 0.13, scaleY: 0.82, scaleZ: 0.13 },
    { x: 7.9, y: 0.4, z: -30, rotationZ: -0.07, scaleX: 0.13, scaleY: 0.8, scaleZ: 0.13 },
    { x: 18.5, y: 0.41, z: -19.6, scaleX: 0.12, scaleY: 0.82, scaleZ: 0.12 },
    { x: 20.2, y: 0.41, z: -19.6, scaleX: 0.12, scaleY: 0.82, scaleZ: 0.12 },
    { x: -34.6, y: 0.41, z: -4, scaleX: 0.12, scaleY: 0.82, scaleZ: 0.12 },
    { x: -34.6, y: 0.41, z: -1.9, scaleX: 0.12, scaleY: 0.82, scaleZ: 0.12 },
    { x: 34.5, y: 0.41, z: 13.2, scaleX: 0.12, scaleY: 0.82, scaleZ: 0.12 },
    { x: 34.5, y: 0.41, z: 15.1, scaleX: 0.12, scaleY: 0.82, scaleZ: 0.12 },
    { x: -11.5, y: 0.41, z: 31.2, scaleX: 0.12, scaleY: 0.82, scaleZ: 0.12 },
    { x: -9.7, y: 0.41, z: 31.2, scaleX: 0.12, scaleY: 0.82, scaleZ: 0.12 },
    { x: 21.8, y: 0.41, z: 31.1, scaleX: 0.12, scaleY: 0.82, scaleZ: 0.12 },
  ]);

  const drainMaterial = createWorldMaterial('street-detail-atlas', {
    tint: 0x596063,
    roughness: 0.56,
    metalness: 0.28,
  });
  addInstances(root, 'Environment kit — wet drain and utility covers', unitBox, drainMaterial, [
    { x: -5.7, y: 0.045, z: 23.9, scaleX: 0.52, scaleY: 0.025, scaleZ: 1.05 },
    { x: 13.4, y: 0.045, z: -23.1, scaleX: 0.52, scaleY: 0.025, scaleZ: 1.05 },
    { x: -6.5, y: 0.046, z: -28.2, rotationY: 0.04, scaleX: 0.48, scaleY: 0.026, scaleZ: 0.92 },
    { x: 6.2, y: 0.046, z: -22.4, rotationY: Math.PI / 2, scaleX: 0.52, scaleY: 0.026, scaleZ: 1.05 },
    { x: -27.1, y: 0.045, z: 10.5, rotationY: Math.PI / 2, scaleX: 0.52, scaleY: 0.025, scaleZ: 1.05 },
    { x: 27, y: 0.045, z: -7, rotationY: Math.PI / 2, scaleX: 0.52, scaleY: 0.025, scaleZ: 1.05 },
    { x: 6.8, y: 0.045, z: 28.9, scaleX: 0.52, scaleY: 0.025, scaleZ: 1.05 },
  ]);

  const patchMaterial = createWorldMaterial('street-detail-atlas', {
    tint: 0xa7abb3,
    roughness: 0.72,
    metalness: 0.05,
  });
  addInstances(root, 'Environment kit — North Road repairs and wet patches', unitBox, patchMaterial, [
    { x: -7.8, y: 0.016, z: -25.3, rotationY: -0.16, scaleX: 4.2, scaleY: 0.018, scaleZ: 1.7 },
    { x: 6.8, y: 0.017, z: -25.7, rotationY: 0.11, scaleX: 3.1, scaleY: 0.019, scaleZ: 1.35 },
    { x: 11.5, y: 0.017, z: -27.4, rotationY: -0.08, scaleX: 1.8, scaleY: 0.019, scaleZ: 0.7 },
    { x: -1.8, y: 0.018, z: -23.2, rotationY: 0.32, scaleX: 1.4, scaleY: 0.02, scaleZ: 0.58 },
  ]);

  addInstances(root, 'Environment kit — North Road iron manholes', unitCircle, drainMaterial, [
    { x: -1.8, y: 0.052, z: -26.2, rotationX: -Math.PI / 2, rotationZ: 0.2, scaleX: 0.62, scaleY: 0.62, scaleZ: 0.62 },
    { x: 9.8, y: 0.052, z: -24.1, rotationX: -Math.PI / 2, rotationZ: -0.3, scaleX: 0.54, scaleY: 0.54, scaleZ: 0.54 },
  ]);

  const kerb = createWorldMaterial('concrete-cracked-overhaul', { tint: 0x878681, roughness: 0.98 });
  addInstances(root, 'Environment kit — imperfect Dreams kerb stones', unitBox, kerb, [
    { x: -11.1, y: 0.07, z: 29.22, rotationY: -0.015, rotationZ: 0.025, scaleX: 1.4, scaleY: 0.16, scaleZ: 0.28 },
    { x: -9.55, y: 0.065, z: 29.2, rotationY: 0.02, scaleX: 1.35, scaleY: 0.15, scaleZ: 0.27 },
    { x: -7.98, y: 0.075, z: 29.21, rotationY: -0.025, rotationZ: -0.02, scaleX: 1.45, scaleY: 0.17, scaleZ: 0.28 },
    { x: 1.9, y: 0.07, z: 29.2, rotationY: 0.018, scaleX: 1.4, scaleY: 0.16, scaleZ: 0.28 },
    { x: 3.45, y: 0.065, z: 29.22, rotationY: -0.021, scaleX: 1.35, scaleY: 0.15, scaleZ: 0.27 },
    { x: 5.0, y: 0.078, z: 29.2, rotationY: 0.012, rotationZ: 0.02, scaleX: 1.43, scaleY: 0.17, scaleZ: 0.28 },
  ]);

  const rubbish = new MeshStandardMaterial({ color: 0x0b0c11, roughness: 0.5, metalness: 0.04 });
  addInstances(root, 'Environment kit — tied rubbish bags', unitCrown, rubbish, [
    { x: -12.6, y: 0.35, z: 20.4, rotationZ: -0.1, scaleX: 0.32, scaleY: 0.44, scaleZ: 0.27 },
    { x: -8.2, y: 0.38, z: -30.6, rotationY: 0.7, scaleX: 0.34, scaleY: 0.5, scaleZ: 0.29 },
    { x: 7.7, y: 0.34, z: -30.7, rotationY: -0.3, scaleX: 0.3, scaleY: 0.45, scaleZ: 0.26 },
    { x: -33.9, y: 0.39, z: 18.8, scaleX: 0.38, scaleY: 0.51, scaleZ: 0.3 },
    { x: 35.1, y: 0.36, z: 16.8, scaleX: 0.34, scaleY: 0.46, scaleZ: 0.28 },
    { x: 28.1, y: 0.41, z: 31.1, scaleX: 0.4, scaleY: 0.54, scaleZ: 0.32 },
  ]);

  const paper = createWorldMaterial('soil-litter-hero', { tint: 0xc1b79e, roughness: 1 });
  addInstances(root, 'Environment kit — litter and wet cardboard clusters', unitBox, paper, [
    { x: -6.4, y: 0.055, z: 20.8, rotationY: 0.4, scaleX: 0.34, scaleY: 0.012, scaleZ: 0.24 },
    { x: -7.2, y: 0.055, z: 21.7, rotationY: -0.9, scaleX: 0.31, scaleY: 0.012, scaleZ: 0.22 },
    { x: -15.3, y: 0.055, z: -19.1, rotationY: 0.2, scaleX: 0.34, scaleY: 0.012, scaleZ: 0.24 },
    { x: -8.9, y: 0.06, z: -29.8, rotationY: -0.5, scaleX: 0.58, scaleY: 0.018, scaleZ: 0.43 },
    { x: -7.9, y: 0.061, z: -29.5, rotationY: 0.22, scaleX: 0.3, scaleY: 0.014, scaleZ: 0.2 },
    { x: 8.6, y: 0.06, z: -30.1, rotationY: 0.8, scaleX: 0.47, scaleY: 0.016, scaleZ: 0.34 },
    { x: -31.4, y: 0.055, z: 6.2, rotationY: -0.5, scaleX: 0.34, scaleY: 0.012, scaleZ: 0.24 },
    { x: -29.1, y: 0.055, z: 17.8, rotationY: 1.2, scaleX: 0.34, scaleY: 0.012, scaleZ: 0.24 },
    { x: 30.1, y: 0.055, z: 19.5, rotationY: -0.7, scaleX: 0.34, scaleY: 0.012, scaleZ: 0.24 },
    { x: 4.8, y: 0.055, z: 29.1, rotationY: 0.5, scaleX: 0.34, scaleY: 0.012, scaleZ: 0.24 },
    { x: 12.1, y: 0.055, z: 30.6, rotationY: -0.2, scaleX: 0.34, scaleY: 0.012, scaleZ: 0.24 },
  ]);

  const binBody = createWorldMaterial('metal-oxidised-overhaul', { tint: 0x344944, roughness: 0.9, metalness: 0.08 });
  const bins = [
    [-11.9, 20.1, -0.08], [-8.55, -30.2, 0.05], [8.45, -30.3, -0.08],
    [22.7, -19.8, 0.12], [-34.9, 8.8, Math.PI / 2], [34.8, 21, -Math.PI / 2], [17.5, 31.1, Math.PI],
  ] as const;
  addInstances(root, 'Environment kit — commercial bin bodies', unitBox, binBody,
    bins.map(([x, z, rotationY]) => ({ x, y: 0.52, z, rotationY, scaleX: 0.66, scaleY: 1.04, scaleZ: 0.58 })));
  addInstances(root, 'Environment kit — commercial bin lids', unitBox,
    new MeshStandardMaterial({ color: 0x20292a, roughness: 0.88 }),
    bins.map(([x, z, rotationY]) => ({ x, y: 1.08, z, rotationY, scaleX: 0.74, scaleY: 0.11, scaleZ: 0.66 })));
  addInstances(root, 'Environment kit — commercial bin openings', unitBox,
    new MeshBasicMaterial({ color: 0x080a0b }),
    bins.map(([x, z, rotationY]) => {
      const frontX = Math.sin(rotationY) * 0.315;
      const frontZ = Math.cos(rotationY) * 0.315;
      return { x: x + frontX, y: 0.72, z: z + frontZ, rotationY, scaleX: 0.46, scaleY: 0.17, scaleZ: 0.05 };
    }));
}
