import {
  BoxGeometry,
  BufferGeometry,
  CylinderGeometry,
  Float32BufferAttribute,
  Group,
  InstancedMesh,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  Object3D,
  Quaternion,
  Vector3,
  type Material,
} from 'three';
import {
  createDreamsSignMaterial,
  createGraffitiMaterial,
  createNoticeMaterial,
  createStickerClusterMaterial,
} from '../rendering/worldGraphics';
import { createWorldMaterial } from '../rendering/worldMaterials';
import type { WorldLocation } from './worldLayout';

const FRONT_Z = 4.32;
const RAIL_RADIUS = 0.035;
const UP = new Vector3(0, 1, 0);
const boxGeometryCache = new Map<string, BoxGeometry>();
const unitRailGeometry = new CylinderGeometry(RAIL_RADIUS, RAIL_RADIUS, 1, 6);

function getBoxGeometry(width: number, height: number, depth: number): BoxGeometry {
  const key = `${width}:${height}:${depth}`;
  let geometry = boxGeometryCache.get(key);
  if (!geometry) {
    geometry = new BoxGeometry(width, height, depth);
    boxGeometryCache.set(key, geometry);
  }
  return geometry;
}

function box(
  width: number,
  height: number,
  depth: number,
  material: Material | Material[],
): Mesh {
  return new Mesh(getBoxGeometry(width, height, depth), material);
}

function addPart(
  root: Group,
  name: string,
  mesh: Mesh,
  x: number,
  y: number,
  z: number,
): Mesh {
  mesh.name = `Dreams ${name}`;
  mesh.position.set(x, y, z);
  root.add(mesh);
  return mesh;
}

function createGableGeometry(width: number, depth: number): BufferGeometry {
  const halfWidth = width / 2;
  const halfDepth = depth / 2;
  const eave = 5.62;
  const peak = 8.18;
  const positions = [
    -halfWidth, eave, halfDepth,
    halfWidth, eave, halfDepth,
    0, peak, halfDepth,
    -halfWidth, eave, -halfDepth,
    halfWidth, eave, -halfDepth,
    0, peak, -halfDepth,
  ];
  const indices = [
    0, 1, 2,
    5, 4, 3,
    0, 3, 4, 0, 4, 1,
    0, 2, 5, 0, 5, 3,
    2, 1, 4, 2, 4, 5,
  ];
  const geometry = new BufferGeometry();
  geometry.setAttribute('position', new Float32BufferAttribute(positions, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

function createRailMaterial(): MeshStandardMaterial {
  return new MeshStandardMaterial({
    color: 0x9ba5a4,
    roughness: 0.48,
    metalness: 0.58,
  });
}

interface RailSegment {
  readonly start: Vector3;
  readonly end: Vector3;
}

function addRailBetween(
  segments: RailSegment[],
  start: Vector3,
  end: Vector3,
): void {
  segments.push({ start, end });
}

function addRampAndRailings(root: Group, brick: Material, rail: Material): void {
  addPart(root, 'raised brick plinth', box(9.2, 0.52, 1.64, brick), -0.3, 0.26, 5.02);
  addPart(
    root,
    'raised concrete platform',
    box(8.4, 0.16, 1.48, createWorldMaterial('concrete-stained-temporary', {
      repeatX: 3,
      tint: 0xc8cbc5,
      roughness: 0.94,
    })),
    -0.7,
    0.6,
    5.08,
  );

  const ramp = addPart(
    root,
    'accessibility ramp',
    box(4.9, 0.18, 1.48, createWorldMaterial('concrete-stained-temporary', {
      repeatX: 2,
      tint: 0xc2c6c0,
      roughness: 0.95,
    })),
    5.42,
    0.34,
    5.08,
  );
  ramp.rotation.z = -0.105;

  const segments: RailSegment[] = [];
  for (const z of [4.42, 5.74]) {
    for (const x of [-4.75, -2.4, 0, 2.35, 3.55]) {
      addRailBetween(
        segments,
        new Vector3(x, 0.61, z),
        new Vector3(x, 1.46, z),
      );
    }
    addRailBetween(
      segments,
      new Vector3(-4.75, 1.46, z),
      new Vector3(3.55, 1.46, z),
    );
    addRailBetween(
      segments,
      new Vector3(-4.75, 1.02, z),
      new Vector3(3.55, 1.02, z),
    );

    const rampStart = new Vector3(3.55, 1.46, z);
    const rampEnd = new Vector3(7.82, 1.02, z);
    addRailBetween(segments, rampStart, rampEnd);
    addRailBetween(
      segments,
      new Vector3(3.55, 1.02, z),
      new Vector3(7.82, 0.58, z),
    );
    for (const [x, low, high] of [
      [5.65, 0.39, 1.24],
      [7.82, 0.17, 1.02],
    ] as const) {
      addRailBetween(
        segments,
        new Vector3(x, low, z),
        new Vector3(x, high, z),
      );
    }
  }

  const railing = new InstancedMesh(unitRailGeometry, rail, segments.length);
  railing.name = 'Dreams instanced ramp and platform railings';
  const dummy = new Object3D();
  segments.forEach(({ start, end }, index) => {
    const direction = new Vector3().subVectors(end, start);
    dummy.position.copy(start).add(end).multiplyScalar(0.5);
    dummy.quaternion.copy(new Quaternion().setFromUnitVectors(UP, direction.clone().normalize()));
    dummy.scale.set(1, direction.length(), 1);
    dummy.updateMatrix();
    railing.setMatrixAt(index, dummy.matrix);
  });
  railing.instanceMatrix.needsUpdate = true;
  root.add(railing);
}

function addShutterBay(
  root: Group,
  name: string,
  x: number,
  width: number,
  shutter: Material,
  frame: Material,
): void {
  addPart(root, `${name} shutter`, box(width, 2.48, 0.13, shutter), x, 1.83, FRONT_Z + 0.08);
  addPart(root, `${name} left channel`, box(0.12, 2.62, 0.2, frame), x - width / 2, 1.86, FRONT_Z + 0.16);
  addPart(root, `${name} right channel`, box(0.12, 2.62, 0.2, frame), x + width / 2, 1.86, FRONT_Z + 0.16);
}

function addSignLights(root: Group): void {
  const tubeMaterial = new MeshBasicMaterial({ color: 0xe5fff7 });
  const bracketMaterial = new MeshStandardMaterial({
    color: 0x656d68,
    roughness: 0.72,
    metalness: 0.35,
  });
  const dummy = new Object3D();
  const upper = new InstancedMesh(getBoxGeometry(2.7, 0.075, 0.08), tubeMaterial, 4);
  upper.name = 'Dreams instanced cold fascia tubes';
  [-4.55, -1.5, 1.55, 4.6].forEach((x, index) => {
    dummy.position.set(x, 5.86, FRONT_Z + 0.46);
    dummy.rotation.set(0, 0, 0);
    dummy.scale.set(1, 1, 1);
    dummy.updateMatrix();
    upper.setMatrixAt(index, dummy.matrix);
  });
  upper.instanceMatrix.needsUpdate = true;
  root.add(upper);

  const brackets = new InstancedMesh(getBoxGeometry(0.08, 0.22, 0.22), bracketMaterial, 8);
  brackets.name = 'Dreams instanced fluorescent brackets';
  [-5.6, -3.5, -2.55, -0.45, 0.5, 2.6, 3.55, 5.65].forEach((x, index) => {
    dummy.position.set(x, 5.78, FRONT_Z + 0.34);
    dummy.rotation.set(-0.3, 0, 0);
    dummy.updateMatrix();
    brackets.setMatrixAt(index, dummy.matrix);
  });
  brackets.instanceMatrix.needsUpdate = true;
  root.add(brackets);

  const lowerTube = new MeshBasicMaterial({ color: 0xbde9ef });
  const lower = new InstancedMesh(getBoxGeometry(2.65, 0.055, 0.06), lowerTube, 4);
  lower.name = 'Dreams instanced cool shutter wash tubes';
  [-4.3, -1.35, 1.6, 4.55].forEach((x, index) => {
    dummy.position.set(x, 3.31, FRONT_Z + 0.5);
    dummy.rotation.set(0, 0, 0);
    dummy.updateMatrix();
    lower.setMatrixAt(index, dummy.matrix);
  });
  lower.instanceMatrix.needsUpdate = true;
  root.add(lower);
}

export function createDreamsBuilding(location: WorldLocation): Group {
  const root = new Group();
  root.name = 'Dreams photographic low-poly reconstruction';
  root.position.set(location.x, 0, location.z);

  const brick = createWorldMaterial('brick-soot-overhaul', {
    repeatX: 5,
    repeatY: 3,
    tint: 0xb06f59,
    roughness: 0.96,
  });
  const stainedCladding = createWorldMaterial('concrete-cracked-overhaul', {
    repeatX: 4,
    repeatY: 2,
    tint: 0xd7d3c7,
    emissive: 0xa9bdbe,
    emissiveIntensity: 0.42,
    roughness: 0.93,
  });
  const photographicGable = createWorldMaterial('dreams-cladding-hero', {
    clamp: true,
    tint: 0xd8d4c8,
    emissive: 0xa9bdbe,
    emissiveIntensity: 0.18,
    roughness: 0.94,
  });
  const darkRoof = createWorldMaterial('metal-oxidised-overhaul', {
    repeatX: 5,
    repeatY: 2,
    tint: 0x24252b,
    roughness: 0.92,
    metalness: 0.12,
  });
  const shutter = createWorldMaterial('dreams-shutter-hero', {
    repeatX: 1,
    repeatY: 1,
    tint: 0xffffff,
    emissive: 0x75868b,
    emissiveIntensity: 0.22,
    roughness: 0.82,
    metalness: 0.16,
  });
  const frame = createWorldMaterial('metal-oxidised-overhaul', {
    repeatY: 3,
    tint: 0xa8b2af,
    roughness: 0.7,
    metalness: 0.34,
  });

  addPart(root, 'brick shell', box(18, 5.62, 8.5, brick), 0, 2.81, 0);
  const gable = new Mesh(createGableGeometry(18, 8.5), photographicGable);
  addPart(root, 'deep gabled volume', gable, 0, 0, 0);

  const roofAngle = Math.atan2(2.82, 9);
  const roofLength = Math.hypot(9.25, 2.82);
  const leftRoof = addPart(root, 'left pitched roof', box(roofLength, 0.2, 9.05, darkRoof), -4.55, 6.94, 0);
  leftRoof.rotation.z = roofAngle;
  const rightRoof = addPart(root, 'right pitched roof', box(roofLength, 0.2, 9.05, darkRoof), 4.55, 6.94, 0);
  rightRoof.rotation.z = -roofAngle;
  addPart(root, 'blue eaves trim', box(18.35, 0.11, 0.18, new MeshStandardMaterial({ color: 0x315d78, roughness: 0.76 })), 0, 5.6, FRONT_Z + 0.08);

  addPart(root, 'upper illuminated frontage', box(17.2, 2.18, 0.2, stainedCladding), -0.15, 4.55, FRONT_Z + 0.05);
  addPart(root, 'central identity panel', box(10.5, 1.9, 0.13, createDreamsSignMaterial()), -0.3, 4.66, FRONT_Z + 0.19);
  addPart(root, 'lower aluminium fascia', box(17.5, 0.28, 0.52, frame), -0.05, 3.38, FRONT_Z + 0.2);

  addPart(root, 'shutter recess', box(14.3, 2.75, 0.18, new MeshStandardMaterial({ color: 0x121619, roughness: 1 })), -1.75, 1.82, FRONT_Z - 0.01);
  addShutterBay(root, 'wide left', -5.7, 5.55, shutter, frame);
  addShutterBay(root, 'central entrance', -1.52, 2.62, shutter, frame);
  addShutterBay(root, 'right', 2.15, 4.55, shutter, frame);

  const rightBrick = createWorldMaterial('dreams-brick-hero', {
    clamp: true,
    tint: 0xc5a99b,
    roughness: 0.94,
  });
  addPart(root, 'right brick return', box(3.35, 3.28, 0.22, rightBrick), 7.22, 1.68, FRONT_Z + 0.07);
  addPart(root, 'right wall panel frame', box(1.35, 2.12, 0.2, frame), 7.15, 1.84, FRONT_Z + 0.23);
  addPart(root, 'right wall panel face', box(1.08, 1.82, 0.08, new MeshStandardMaterial({ color: 0xc7c3b5, roughness: 0.94 })), 7.15, 1.88, FRONT_Z + 0.37);
  addPart(root, 'right panel faded yellow stripe', box(1.08, 0.35, 0.035, new MeshStandardMaterial({ color: 0xa7a014, roughness: 0.9 })), 7.15, 1.62, FRONT_Z + 0.43);

  const alarm = addPart(root, 'yellow alarm box', box(0.38, 0.42, 0.22, new MeshStandardMaterial({ color: 0xe1c91b, roughness: 0.72 })), -7.45, 4.55, FRONT_Z + 0.3);
  alarm.rotation.z = Math.PI / 4;
  addPart(root, 'alarm dark centre', box(0.17, 0.17, 0.05, new MeshBasicMaterial({ color: 0x133867 })), -7.45, 4.55, FRONT_Z + 0.44);
  const camera = addPart(root, 'small CCTV camera', box(0.28, 0.16, 0.22, frame), -6.78, 3.63, FRONT_Z + 0.35);
  camera.rotation.x = -0.28;

  const graffiti = addPart(root, 'restrained shutter tagging', box(2.2, 1.15, 0.025, createGraffitiMaterial('MCR', '#29252b')), -5.65, 1.62, FRONT_Z + 0.24);
  graffiti.rotation.z = -0.08;

  addPart(
    root,
    'handwritten no dumping notice',
    box(0.72, 0.78, 0.025, createNoticeMaterial('NO DUMPING', 'CCTV IN USE\nKEEP CLEAR', '#d2b731')),
    7.15,
    2.25,
    FRONT_Z + 0.46,
  );
  const stickers = addPart(
    root,
    'sticker cluster decal',
    box(0.68, 0.8, 0.02, createStickerClusterMaterial()),
    8.18,
    1.12,
    FRONT_Z + 0.22,
  );
  stickers.rotation.z = -0.045;
  addPart(root, 'right drainpipe', box(0.14, 5.35, 0.16, frame), 8.58, 2.68, FRONT_Z + 0.22);
  addPart(root, 'rainwater hopper', box(0.34, 0.38, 0.3, frame), 8.58, 5.18, FRONT_Z + 0.22);
  addPart(root, 'wall cable', box(5.8, 0.045, 0.045, frame), 5.55, 3.18, FRONT_Z + 0.39).rotation.z = -0.025;
  addPart(root, 'cheap wall vent', box(0.58, 0.42, 0.08, frame), 5.72, 0.62, FRONT_Z + 0.42);

  addRampAndRailings(root, brick, createRailMaterial());
  addSignLights(root);

  return root;
}
