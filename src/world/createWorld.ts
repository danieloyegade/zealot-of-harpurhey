import {
  BoxGeometry,
  CanvasTexture,
  Color,
  CylinderGeometry,
  DirectionalLight,
  Group,
  HemisphereLight,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  PointLight,
  Scene,
  SphereGeometry,
  SRGBColorSpace,
} from 'three';
import type { CollisionObstacle, CollisionWorld } from './collision';
import { loadModel } from './loadModel';

export interface World {
  readonly root: Group;
  readonly collision: CollisionWorld;
}

const BUILDING_DEPTH = 9.6;
const BUILDING_WIDTH = 7.5;

function createBox(
  width: number,
  height: number,
  depth: number,
  color: number,
): Mesh {
  return new Mesh(
    new BoxGeometry(width, height, depth),
    new MeshStandardMaterial({ color, roughness: 1 }),
  );
}

function createFloristSign(): Mesh {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 128;

  const context = canvas.getContext('2d');
  if (!context) {
    throw new Error('Could not create the florist sign canvas.');
  }

  context.fillStyle = '#d8c15a';
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = '#321d23';
  context.font = 'bold 64px Georgia, serif';
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  context.fillText('FLORIST', canvas.width / 2, canvas.height / 2);

  const texture = new CanvasTexture(canvas);
  texture.colorSpace = SRGBColorSpace;

  return new Mesh(
    new BoxGeometry(0.08, 0.8, 3.6),
    new MeshBasicMaterial({ map: texture }),
  );
}

function addBuilding(
  root: Group,
  obstacles: CollisionObstacle[],
  x: number,
  z: number,
  height: number,
  isFlorist: boolean,
): void {
  const building = createBox(
    BUILDING_WIDTH,
    height,
    BUILDING_DEPTH,
    isFlorist ? 0x6f3941 : 0x454851,
  );
  building.position.set(x, height / 2, z);
  building.name = isFlorist ? 'Florist' : 'Building';
  root.add(building);

  obstacles.push({
    name: building.name,
    minX: x - BUILDING_WIDTH / 2,
    maxX: x + BUILDING_WIDTH / 2,
    minZ: z - BUILDING_DEPTH / 2,
    maxZ: z + BUILDING_DEPTH / 2,
  });

  if (isFlorist) {
    const sign = createFloristSign();
    sign.position.set(x - BUILDING_WIDTH / 2 - 0.05, 2.7, z);
    root.add(sign);
  }
}

function createBusShelterFallback(): Group {
  const shelter = new Group();
  shelter.name = 'Bus shelter loading placeholder';
  shelter.position.set(-5.7, 0, 5);

  const shelterMaterial = new MeshStandardMaterial({
    color: 0x467b83,
    roughness: 0.85,
  });
  const back = new Mesh(new BoxGeometry(0.12, 2.1, 3.6), shelterMaterial);
  back.position.set(-0.75, 1.05, 0);
  shelter.add(back);

  const roof = new Mesh(new BoxGeometry(1.65, 0.14, 3.8), shelterMaterial);
  roof.position.set(0, 2.2, 0);
  shelter.add(roof);

  const bench = new Mesh(new BoxGeometry(0.55, 0.12, 2.4), shelterMaterial);
  bench.position.set(-0.35, 0.55, 0);
  shelter.add(bench);

  return shelter;
}

function markShelterLoadFailure(fallback: Group): void {
  fallback.name = 'Bus shelter load error';
  fallback.traverse((child) => {
    if (child instanceof Mesh && child.material instanceof MeshStandardMaterial) {
      child.material.color.set(0xff00c8);
      child.material.emissive.set(0x550033);
    }
  });
}

async function replaceBusShelterFallback(
  root: Group,
  fallback: Group,
): Promise<void> {
  try {
    const shelter = await loadModel(
      'assets/models/harperhay-bus-shelter.glb',
    );
    shelter.name = 'Harperhay bus shelter';
    shelter.position.copy(fallback.position);
    root.add(shelter);
    root.remove(fallback);
  } catch (error) {
    markShelterLoadFailure(fallback);
    console.error(
      '[Street A] Failed to load harperhay-bus-shelter.glb. Showing the magenta fallback.',
      error,
    );
  }
}

function addBusShelter(root: Group, obstacles: CollisionObstacle[]): void {
  const fallback = createBusShelterFallback();
  root.add(fallback);
  void replaceBusShelterFallback(root, fallback);

  const shelterLights = new Group();
  shelterLights.name = 'Bus shelter local lights';

  const warmOverhead = new PointLight(0xffc878, 11, 8, 2);
  warmOverhead.position.set(-5.45, 2.55, 5);
  shelterLights.add(warmOverhead);

  const greenGlassLight = new PointLight(0x55c58a, 7, 6.5, 2);
  greenGlassLight.position.set(-5.35, 1.25, 5.15);
  shelterLights.add(greenGlassLight);

  const advertSpill = new PointLight(0xff3d91, 8, 5.5, 2);
  advertSpill.position.set(-5.25, 1.35, 2.8);
  shelterLights.add(advertSpill);

  root.add(shelterLights);

  obstacles.push({
    name: 'Bus shelter',
    minX: -6.6,
    maxX: -4.8,
    minZ: 2.5,
    maxZ: 7.5,
  });
}

function addLamppost(root: Group): void {
  const lamppost = new Group();
  lamppost.name = 'Lamppost';
  lamppost.position.set(5.7, 0, -4);

  const darkMetal = new MeshStandardMaterial({
    color: 0x25262b,
    roughness: 1,
  });
  const pole = new Mesh(new CylinderGeometry(0.08, 0.1, 4.8, 8), darkMetal);
  pole.position.y = 2.4;
  lamppost.add(pole);

  const lamp = new Mesh(
    new SphereGeometry(0.24, 8, 6),
    new MeshBasicMaterial({ color: 0xe0b56a }),
  );
  lamp.position.y = 4.75;
  lamppost.add(lamp);

  const light = new PointLight(0xffc674, 18, 12, 2);
  light.position.y = 4.6;
  lamppost.add(light);
  root.add(lamppost);
}

export function createWorld(scene: Scene): World {
  scene.background = new Color(0x080b14);

  const root = new Group();
  root.name = 'Street A blockout';
  scene.add(root);

  const road = createBox(9, 0.1, 60, 0x202229);
  road.position.set(0, -0.05, 0);
  road.name = 'Road';
  root.add(road);

  for (const x of [-5.75, 5.75]) {
    const pavement = createBox(2.5, 0.12, 60, 0x686867);
    pavement.position.set(x, -0.06, 0);
    pavement.name = 'Pavement';
    root.add(pavement);
  }

  const parkOpening = createBox(14, 0.08, 4.2, 0x344a36);
  parkOpening.position.set(0, -0.04, -27.6);
  parkOpening.name = 'Future central park opening';
  root.add(parkOpening);

  const obstacles: CollisionObstacle[] = [];
  const buildingPositions = [-20, -10, 0, 10, 20];

  for (const z of buildingPositions) {
    const heightOffset = (Math.abs(z) / 10) % 3;
    addBuilding(root, obstacles, -10.75, z, 5.8 + heightOffset, false);
    addBuilding(root, obstacles, 10.75, z, 6.3 + heightOffset, z === 10);
  }

  addBusShelter(root, obstacles);
  addLamppost(root);

  scene.add(new HemisphereLight(0x617092, 0x17130f, 1.35));
  const moonlight = new DirectionalLight(0x9aa9c8, 1.35);
  moonlight.position.set(-8, 14, 10);
  scene.add(moonlight);

  return {
    root,
    collision: {
      bounds: {
        minX: -15,
        maxX: 15,
        minZ: -29.5,
        maxZ: 29.5,
      },
      obstacles,
    },
  };
}
