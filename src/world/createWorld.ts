import {
  BackSide,
  BoxGeometry,
  CanvasTexture,
  CircleGeometry,
  Color,
  ConeGeometry,
  CylinderGeometry,
  DodecahedronGeometry,
  DirectionalLight,
  Group,
  HemisphereLight,
  type Material,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  OctahedronGeometry,
  PointLight,
  Points,
  PointsMaterial,
  Scene,
  ShaderMaterial,
  SphereGeometry,
  Sprite,
  SpriteMaterial,
  SRGBColorSpace,
  TorusGeometry,
  Vector3,
} from 'three';
import { BufferAttribute, BufferGeometry, Fog } from 'three';
import { applyTextureProfile, VISUAL_STYLE } from '../rendering/visualStyle';
import {
  createGraffitiMaterial,
  createWeatheredSignMaterial,
} from '../rendering/worldGraphics';
import {
  createAdditiveWorldMaterial,
  createHaloMaterial,
  createWorldMaterial,
  type WorldTextureName,
} from '../rendering/worldMaterials';
import type { CollisionObstacle, CollisionWorld } from './collision';
import { loadModel } from './loadModel';
import { createDreamsBuilding } from './createDreamsBuilding';
import {
  BUS_STOPS,
  FUTURE_EXITS,
  PARK,
  PAVEMENT_WIDTH,
  ROAD_WIDTH,
  STERLING_BIKE_DOCKS,
  WORLD_BOUNDS,
  WORLD_LOCATIONS,
  type WorldLocation,
  type WorldMarker,
} from './worldLayout';

export interface World {
  readonly root: Group;
  readonly collision: CollisionWorld;
  readonly update: (deltaTime: number, playerPosition: Vector3) => void;
  readonly getLightingStats: () => LightingStats;
  readonly setDevelopmentOverlaysVisible: (visible: boolean) => void;
}

export interface LightingStats {
  readonly activePointLights: number;
  readonly activeSpotLights: number;
  readonly maximumActiveLocalLights: number;
}

const boxGeometryCache = new Map<string, BoxGeometry>();
const cylinderGeometryCache = new Map<string, CylinderGeometry>();
const circleGeometryCache = new Map<string, CircleGeometry>();
const coneGeometryCache = new Map<string, ConeGeometry>();
const dodecahedronGeometryCache = new Map<string, DodecahedronGeometry>();
const standardColorMaterialCache = new Map<number, MeshStandardMaterial>();
const basicColorMaterialCache = new Map<number, MeshBasicMaterial>();

function getBoxGeometry(
  width: number,
  height: number,
  depth: number,
  widthSegments = 1,
  heightSegments = 1,
  depthSegments = 1,
): BoxGeometry {
  const key = [width, height, depth, widthSegments, heightSegments, depthSegments].join(':');
  let geometry = boxGeometryCache.get(key);
  if (!geometry) {
    geometry = new BoxGeometry(
      width,
      height,
      depth,
      widthSegments,
      heightSegments,
      depthSegments,
    );
    boxGeometryCache.set(key, geometry);
  }
  return geometry;
}

function getCylinderGeometry(
  radiusTop: number,
  radiusBottom: number,
  height: number,
  radialSegments: number,
): CylinderGeometry {
  const key = [radiusTop, radiusBottom, height, radialSegments].join(':');
  let geometry = cylinderGeometryCache.get(key);
  if (!geometry) {
    geometry = new CylinderGeometry(radiusTop, radiusBottom, height, radialSegments);
    cylinderGeometryCache.set(key, geometry);
  }
  return geometry;
}

function getCircleGeometry(radius: number, segments: number): CircleGeometry {
  const key = `${radius}:${segments}`;
  let geometry = circleGeometryCache.get(key);
  if (!geometry) {
    geometry = new CircleGeometry(radius, segments);
    circleGeometryCache.set(key, geometry);
  }
  return geometry;
}

function getConeGeometry(
  radius: number,
  height: number,
  radialSegments: number,
  heightSegments = 1,
  openEnded = false,
): ConeGeometry {
  const key = [radius, height, radialSegments, heightSegments, openEnded].join(':');
  let geometry = coneGeometryCache.get(key);
  if (!geometry) {
    geometry = new ConeGeometry(
      radius,
      height,
      radialSegments,
      heightSegments,
      openEnded,
    );
    coneGeometryCache.set(key, geometry);
  }
  return geometry;
}

function getDodecahedronGeometry(radius: number): DodecahedronGeometry {
  let geometry = dodecahedronGeometryCache.get(`${radius}`);
  if (!geometry) {
    geometry = new DodecahedronGeometry(radius, 0);
    dodecahedronGeometryCache.set(`${radius}`, geometry);
  }
  return geometry;
}

function getStandardColorMaterial(color: number): MeshStandardMaterial {
  let material = standardColorMaterialCache.get(color);
  if (!material) {
    material = new MeshStandardMaterial({ color, roughness: 1 });
    standardColorMaterialCache.set(color, material);
  }
  return material;
}

function getBasicColorMaterial(color: number): MeshBasicMaterial {
  let material = basicColorMaterialCache.get(color);
  if (!material) {
    material = new MeshBasicMaterial({ color });
    basicColorMaterialCache.set(color, material);
  }
  return material;
}

function createBox(
  width: number,
  height: number,
  depth: number,
  colorOrMaterial: number | Material,
): Mesh {
  return new Mesh(
    getBoxGeometry(width, height, depth),
    typeof colorOrMaterial === 'number'
      ? getStandardColorMaterial(colorOrMaterial)
      : colorOrMaterial,
  );
}

function addSurface(
  root: Group,
  name: string,
  x: number,
  z: number,
  width: number,
  depth: number,
  color: number,
  y = -0.05,
  material?: Material,
): Mesh {
  const surface = createBox(width, 0.1, depth, material ?? color);
  surface.name = name;
  surface.position.set(x, y, z);
  root.add(surface);
  return surface;
}

function addEnvironmentSurface(
  root: Group,
  name: string,
  x: number,
  z: number,
  width: number,
  depth: number,
  textureName: WorldTextureName,
  y = -0.05,
  tileSize = 4,
): Mesh {
  const isWet = textureName === 'asphalt-wet-overhaul'
    || textureName === 'pavement-wet-overhaul';
  const material = createWorldMaterial(textureName, {
    repeatX: Math.max(1, Math.round(width / tileSize)),
    repeatY: Math.max(1, Math.round(depth / tileSize)),
    roughness: isWet ? 0.54 : 0.9,
    metalness: textureName === 'asphalt-wet-overhaul' ? 0.12 : 0,
  });
  return addSurface(root, name, x, z, width, depth, 0xffffff, y, material);
}

function addReflectionPatch(
  root: Group,
  name: string,
  x: number,
  z: number,
  width: number,
  depth: number,
  color: number,
  opacity: number,
  rotation = 0,
): Mesh {
  const patch = createBox(
    width,
    0.018,
    depth,
    createAdditiveWorldMaterial(
      'reflection-broken-overhaul',
      color,
      opacity,
    ),
  );
  patch.name = name;
  patch.position.set(x, 0.035, z);
  patch.rotation.y = rotation;
  root.add(patch);
  return patch;
}

function createDevelopmentLabel(text: string): Sprite {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 128;
  const context = canvas.getContext('2d');
  if (!context) {
    throw new Error('Could not create a world development label.');
  }

  context.fillStyle = 'rgba(8, 10, 15, 0.82)';
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.strokeStyle = '#d6bd67';
  context.lineWidth = 5;
  context.strokeRect(3, 3, canvas.width - 6, canvas.height - 6);
  context.fillStyle = '#f2e5b8';
  context.font = 'bold 44px Georgia, serif';
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  context.fillText(text.toUpperCase(), canvas.width / 2, canvas.height / 2);

  const texture = new CanvasTexture(canvas);
  texture.colorSpace = SRGBColorSpace;
  const label = new Sprite(
    new SpriteMaterial({ map: texture, transparent: true, depthWrite: false }),
  );
  label.name = `Development label: ${text}`;
  label.scale.set(5.4, 1.35, 1);
  return label;
}

function addDevelopmentLabel(
  root: Group,
  name: string,
  x: number,
  y: number,
  z: number,
): void {
  if (!import.meta.env.DEV) {
    return;
  }
  const label = createDevelopmentLabel(name);
  label.userData.developmentOverlay = true;
  label.position.set(x, y, z);
  root.add(label);
}

function addCollisionFootprint(
  obstacles: CollisionObstacle[],
  location: WorldLocation,
): void {
  obstacles.push({
    name: location.name,
    minX: location.x - location.width / 2,
    maxX: location.x + location.width / 2,
    minZ: location.z - location.depth / 2,
    maxZ: location.z + location.depth / 2,
    height: location.height,
  });
}

function markLoadFailure(fallback: Mesh, assetName: string): void {
  fallback.name = `${assetName} load error`;
  if (fallback.material instanceof MeshStandardMaterial) {
    fallback.material.color.set(0xff00c8);
    fallback.material.emissive.set(0x550033);
  }
}

function applyPhotographicModelPolicy(model: Group): void {
  model.traverse((child) => {
    if (!(child instanceof Mesh)) {
      return;
    }
    const materials = Array.isArray(child.material)
      ? child.material
      : [child.material];
    for (const material of materials) {
      if (!(material instanceof MeshStandardMaterial)) {
        continue;
      }
      for (const texture of [
        material.map,
        material.emissiveMap,
        material.alphaMap,
      ]) {
        if (texture) {
          applyTextureProfile(texture, 'PHOTO_ENVIRONMENT');
        }
      }
      material.emissiveIntensity *= VISUAL_STYLE.lighting.emissiveMultiplier;
    }
  });
}

async function replaceFloristFallback(
  root: Group,
  fallback: Mesh,
  location: WorldLocation,
): Promise<void> {
  try {
    const florist = await loadModel('assets/models/harperhay-florist.glb');
    applyPhotographicModelPolicy(florist);
    florist.name = 'Harperhay florist';
    florist.position.set(location.x, 0, location.z);
    florist.rotation.y = Math.PI / 2;
    root.add(florist);
    root.remove(fallback);
  } catch (error) {
    markLoadFailure(fallback, 'Florist');
    console.error(
      '[World] Failed to load harperhay-florist.glb. Showing the magenta fallback.',
      error,
    );
  }
}

function addFacadePanel(
  root: Group,
  location: WorldLocation,
  name: string,
  acrossScale: number,
  height: number,
  y: number,
  material: Material,
  acrossOffset = 0,
): Mesh {
  const front = location.front ?? 'south';
  const northOrSouth = front === 'north' || front === 'south';
  const panel = createBox(
    northOrSouth ? location.width * acrossScale : 0.12,
    height,
    northOrSouth ? 0.12 : location.depth * acrossScale,
    material,
  );
  panel.name = `${location.name} ${name}`;
  panel.position.set(location.x, y, location.z);

  if (front === 'south') {
    panel.position.x += acrossOffset * location.width;
    panel.position.z += location.depth / 2 + 0.07;
  } else if (front === 'north') {
    panel.position.x += acrossOffset * location.width;
    panel.position.z -= location.depth / 2 + 0.07;
  } else if (front === 'east') {
    panel.position.x += location.width / 2 + 0.07;
    panel.position.z += acrossOffset * location.depth;
  } else {
    panel.position.x -= location.width / 2 + 0.07;
    panel.position.z += acrossOffset * location.depth;
  }
  root.add(panel);
  return panel;
}

function addFacadeProjection(
  root: Group,
  location: WorldLocation,
  name: string,
  acrossScale: number,
  height: number,
  projection: number,
  y: number,
  material: Material,
  acrossOffset = 0,
): Mesh {
  const front = location.front ?? 'south';
  const northOrSouth = front === 'north' || front === 'south';
  const feature = createBox(
    northOrSouth ? location.width * acrossScale : projection,
    height,
    northOrSouth ? projection : location.depth * acrossScale,
    material,
  );
  feature.name = `${location.name} ${name}`;
  feature.position.set(location.x, y, location.z);
  if (front === 'south') {
    feature.position.x += acrossOffset * location.width;
    feature.position.z += location.depth / 2 + projection / 2;
  } else if (front === 'north') {
    feature.position.x += acrossOffset * location.width;
    feature.position.z -= location.depth / 2 + projection / 2;
  } else if (front === 'east') {
    feature.position.x += location.width / 2 + projection / 2;
    feature.position.z += acrossOffset * location.depth;
  } else {
    feature.position.x -= location.width / 2 + projection / 2;
    feature.position.z += acrossOffset * location.depth;
  }
  root.add(feature);
  return feature;
}

function createBlockoutBuildingMass(location: WorldLocation): Mesh {
  const frontTexture = location.id === 'dreams' || location.id === 'renae'
    ? 'brick-painted-overhaul'
    : location.id === 'arts-council' || location.id === 'come-through-lab'
      ? 'concrete-cracked-overhaul'
      : 'brick-soot-overhaul';
  const frontTint = location.id === 'dreams'
    ? 0x8c3349
    : location.id === 'renae'
      ? 0x7c2847
      : 0xffffff;
  const frontEmissive = ['renae', 'terrace'].includes(location.id)
    ? VISUAL_STYLE.lighting.magenta
    : location.id === 'come-through-lab'
      ? VISUAL_STYLE.lighting.fluorescent
      : ['coral', 'advanced-photo', 'arts-council'].includes(location.id)
        ? VISUAL_STYLE.lighting.coldWhite
        : VISUAL_STYLE.lighting.sodium;
  const frontMaterial = createWorldMaterial(frontTexture, {
    repeatX: Math.max(2, Math.round(location.width / 4)),
    repeatY: Math.max(2, Math.round(location.height / 2)),
    tint: frontTint,
    emissive: frontEmissive,
    emissiveIntensity: ['renae', 'coral', 'come-through-lab'].includes(location.id)
      ? 0.16
      : 0.1,
    roughness: 0.94,
  });
  const sideMaterial = createWorldMaterial('brick-soot-overhaul', {
    repeatX: Math.max(2, Math.round(location.depth / 4)),
    repeatY: Math.max(2, Math.round(location.height / 2)),
    tint: 0x81716b,
    emissive: 0x070b18,
    emissiveIntensity: 0.06,
    roughness: 0.97,
  });
  const concreteRoof = createWorldMaterial('concrete-cracked-overhaul', {
    repeatX: 2,
    repeatY: 2,
    tint: 0x777779,
  });
  const materials: Material[] = [
    sideMaterial,
    sideMaterial,
    concreteRoof,
    sideMaterial,
    sideMaterial,
    sideMaterial,
    sideMaterial,
  ];
  const frontIndex = {
    east: 0,
    west: 1,
    south: 4,
    north: 5,
  }[location.front ?? 'south'];
  materials[frontIndex] = frontMaterial;

  return new Mesh(
    getBoxGeometry(location.width, location.height, location.depth),
    materials,
  );
}

function addBlockoutFacade(root: Group, location: WorldLocation): void {
  const variant = location.id.length % 4;
  const isWarm = ['dreams', 'renae', 'gullivers', 'vinyl-exchange'].includes(location.id);
  const windowMaterial = createWorldMaterial('window-row-overhaul', {
    repeatX: Math.max(1, Math.round(location.width / 5)),
    repeatY: 1,
    emissive: isWarm ? VISUAL_STYLE.lighting.sodium : 0x102044,
    emissiveIntensity: isWarm ? 0.32 : 0.08,
    roughness: 0.7,
  });
  const shutterMaterial = createWorldMaterial('shutter-grimy-overhaul', {
    repeatX: 2,
    repeatY: 1,
    roughness: 0.86,
  });
  const locationStyle: Record<string, readonly [string, string, number]> = {
    dreams: ['#72283b', '#e7d4c6', VISUAL_STYLE.lighting.magenta],
    renae: ['#7e2348', '#f1ccd7', VISUAL_STYLE.lighting.magenta],
    m1: ['#cdb33f', '#391e19', VISUAL_STYLE.lighting.sodium],
    'advanced-photo': ['#214b86', '#e2e9e0', VISUAL_STYLE.lighting.coldWhite],
    coral: ['#183b74', '#eee6d5', VISUAL_STYLE.lighting.coldWhite],
    'eastern-bloc': ['#856b31', '#10151c', VISUAL_STYLE.lighting.sodium],
    'village-books': ['#d5c8a7', '#7c231d', VISUAL_STYLE.lighting.sodium],
    'come-through-lab': ['#1d2938', '#b6d6c9', VISUAL_STYLE.lighting.fluorescent],
    gullivers: ['#403025', '#e9d3a2', VISUAL_STYLE.lighting.sodium],
    terrace: ['#392547', '#d3cbe4', VISUAL_STYLE.lighting.magenta],
    'vinyl-exchange': ['#d3c6a0', '#a12f28', VISUAL_STYLE.lighting.sodium],
    'real-camera': ['#ddd1ae', '#8c2a22', VISUAL_STYLE.lighting.sodium],
    'spice-cabin': ['#8d2d29', '#f0d28c', VISUAL_STYLE.lighting.sodium],
    'off-licence': ['#302a25', '#ead7ac', VISUAL_STYLE.lighting.sodium],
    'arts-council': ['#d4c79d', '#191816', VISUAL_STYLE.lighting.coldWhite],
  };
  const fallbackStyles: readonly (readonly [string, string, number])[] = [
    ['#614538', '#e3d4a8', VISUAL_STYLE.lighting.sodium],
    ['#254937', '#ddd6a7', VISUAL_STYLE.lighting.fluorescent],
    ['#632b4d', '#f0d0dd', VISUAL_STYLE.lighting.magenta],
    ['#3d4e67', '#e1e6e8', VISUAL_STYLE.lighting.coldWhite],
  ];
  const fallbackStyle = fallbackStyles[variant] ?? fallbackStyles[0];
  const [signBackground, signForeground, signColor] = locationStyle[location.id] ?? fallbackStyle;
  const signMaterial = createWeatheredSignMaterial(
    location.name,
    signBackground,
    signForeground,
    ['dreams', 'renae', 'm1', 'arts-council'].includes(location.id) ? 0.24 : 0.11,
  );

  addFacadePanel(
    root,
    location,
    'uneven upper windows',
    0.84,
    Math.min(2.1, location.height * 0.27),
    location.height * 0.69,
    windowMaterial,
  );
  if (location.id === 'dreams' || location.id === 'coral') {
    addFacadePanel(
      root,
      location,
      'photographic shopfront derivative',
      0.9,
      Math.min(2.75, location.height * 0.36),
      Math.min(1.4, location.height * 0.2),
      createWorldMaterial(
        location.id === 'dreams' ? 'dreams-photo-overhaul' : 'coral-photo-overhaul',
        {
          clamp: true,
          roughness: 0.68,
          emissive: location.id === 'dreams' ? 0xd7e3ee : 0x5c7890,
          emissiveIntensity: location.id === 'dreams' ? 0.16 : 0.08,
        },
      ),
    );
  } else {
    addFacadePanel(
      root,
      location,
      'grimy recessed shop shutter',
      0.64,
      Math.min(2.45, location.height * 0.35),
      Math.min(1.25, location.height * 0.2),
      shutterMaterial,
      -0.08,
    );
  }
  addFacadePanel(
    root,
    location,
    'weathered identity sign',
    0.72,
    0.66,
    Math.min(3.05, location.height * 0.43),
    signMaterial,
    0.03,
  );
  if (location.id === 'dreams' || location.id === 'renae') {
    addFacadePanel(
      root,
      location,
      'oversized painted name wall',
      0.82,
      1.42,
      location.height * 0.68,
      createWeatheredSignMaterial(
        location.name,
        location.id === 'dreams' ? '#72263d' : '#7f244a',
        '#ead5d2',
        0.18,
      ),
    );
  }

  const doorwayMaterial = createWorldMaterial('window-dark-temporary', {
    tint: 0x171923,
    emissive: 0x20120b,
    emissiveIntensity: isWarm ? 0.18 : 0.02,
    roughness: 0.58,
  });
  addFacadePanel(
    root,
    location,
    'recessed doorway',
    0.16,
    Math.min(2.7, location.height * 0.38),
    Math.min(1.35, location.height * 0.2),
    doorwayMaterial,
    0.36,
  );
  addFacadeProjection(
    root,
    location,
    'shop canopy projection',
    0.76,
    0.12,
    0.65 + variant * 0.08,
    Math.min(2.75, location.height * 0.4),
    createWorldMaterial('metal-oxidised-overhaul', {
      tint: signColor,
      roughness: 0.82,
      metalness: 0.18,
    }),
  );
  addFacadePanel(
    root,
    location,
    'drainpipe',
    0.026,
    location.height * 0.82,
    location.height * 0.46,
    createWorldMaterial('metal-oxidised-overhaul', {
      repeatY: 4,
      tint: 0x555454,
      roughness: 0.8,
      metalness: 0.2,
    }),
    variant % 2 === 0 ? -0.44 : 0.44,
  );

  if (location.id !== 'dreams' && location.id !== 'coral') {
    addFacadePanel(
      root,
      location,
      'flyposter strip',
      0.17,
      1.7,
      1.02,
      createWorldMaterial('poster-wall-overhaul', {
        clamp: true,
        roughness: 0.94,
      }),
      variant % 2 === 0 ? 0.31 : -0.31,
    );
  }
  if (['dreams', 'come-through-lab', 'eastern-bloc', 'arts-council'].includes(location.id)) {
    addFacadePanel(
      root,
      location,
      'painted graffiti',
      0.38,
      1.4,
      1.04,
      createGraffitiMaterial(location.id === 'dreams' ? 'NO SLEEP' : 'ZOH'),
      -0.2,
    );
  }

  const roofHeight = 0.55 + variant * 0.12;
  const roofFeature = createBox(
    location.width * 0.34,
    roofHeight,
    location.depth * 0.28,
    createWorldMaterial('concrete-cracked-overhaul', {
      repeatX: 1,
      repeatY: 1,
    }),
  );
  roofFeature.name = `${location.name} economical roof silhouette`;
  roofFeature.position.set(
    location.x + (variant % 2 === 0 ? -0.18 : 0.2) * location.width,
    location.height + roofHeight / 2,
    location.z,
  );
  root.add(roofFeature);
}

function addBuildingLocation(
  root: Group,
  obstacles: CollisionObstacle[],
  location: WorldLocation,
): void {
  if (location.id === 'dreams') {
    root.add(createDreamsBuilding(location));
    addCollisionFootprint(obstacles, location);
    return;
  }

  const building =
    location.status === 'finished'
      ? createBox(
          location.width,
          location.height,
          location.depth,
          location.color,
        )
      : createBlockoutBuildingMass(location);
  building.position.set(location.x, location.height / 2, location.z);
  building.name =
    location.status === 'finished'
      ? `${location.name} loading placeholder`
      : `${location.name} blockout`;
  root.add(building);
  addCollisionFootprint(obstacles, location);

  if (location.id === 'florist') {
    void replaceFloristFallback(root, building, location);
  } else {
    addBlockoutFacade(root, location);
  }

  addDevelopmentLabel(
    root,
    location.name,
    location.x,
    location.height + 1.1,
    location.z,
  );
}

function createBusShelterFallback(): Group {
  const shelter = new Group();
  shelter.name = 'Bus shelter loading placeholder';
  const material = new MeshStandardMaterial({
    color: 0x467b83,
    roughness: 0.85,
  });

  const back = new Mesh(getBoxGeometry(0.12, 2.1, 3.6), material);
  back.position.set(-0.75, 1.05, 0);
  shelter.add(back);
  const roof = new Mesh(getBoxGeometry(1.65, 0.14, 3.8), material);
  roof.position.set(0, 2.2, 0);
  shelter.add(roof);
  const bench = new Mesh(getBoxGeometry(0.55, 0.12, 2.4), material);
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
    applyPhotographicModelPolicy(shelter);
    shelter.name = fallback.name.replace(' loading placeholder', '');
    shelter.position.copy(fallback.position);
    shelter.rotation.copy(fallback.rotation);
    root.add(shelter);
    root.remove(fallback);
  } catch (error) {
    markShelterLoadFailure(fallback);
    console.error(
      '[World] Failed to load harperhay-bus-shelter.glb. Showing the magenta fallback.',
      error,
    );
  }
}

function addBusShelter(
  root: Group,
  obstacles: CollisionObstacle[],
  marker: WorldMarker,
  rotation: number,
): void {
  const fallback = createBusShelterFallback();
  fallback.name = `${marker.name} loading placeholder`;
  fallback.position.set(marker.x, 0, marker.z);
  fallback.rotation.y = rotation;
  root.add(fallback);
  void replaceBusShelterFallback(root, fallback);

  obstacles.push({
    name: marker.name,
    minX: marker.x - 2.55,
    maxX: marker.x + 2.55,
    minZ: marker.z - 0.9,
    maxZ: marker.z + 0.9,
    height: 2.6,
  });
  addDevelopmentLabel(root, marker.name, marker.x, 3.4, marker.z);
}

function addPathBetween(
  root: Group,
  name: string,
  startX: number,
  startZ: number,
  endX: number,
  endZ: number,
  width: number,
): void {
  const deltaX = endX - startX;
  const deltaZ = endZ - startZ;
  const length = Math.hypot(deltaX, deltaZ);
  const path = addEnvironmentSurface(
    root,
    name,
    (startX + endX) / 2,
    (startZ + endZ) / 2,
    width,
    length,
    'pavement-weathered-overhaul',
    0.01,
    3,
  );
  path.rotation.y = Math.atan2(deltaX, deltaZ);
}

function addCentralPark(root: Group): void {
  addEnvironmentSurface(
    root,
    'Central Park grass blockout',
    PARK.x,
    PARK.z,
    PARK.width,
    PARK.depth,
    'grass-damp-overhaul',
    -0.03,
    5,
  );

  addEnvironmentSurface(root, 'Park path north', 0, -15.2, 42, 1.5, 'pavement-weathered-overhaul', 0.01, 3);
  addEnvironmentSurface(root, 'Park path south', 0, 15.2, 42, 1.5, 'pavement-wet-overhaul', 0.01, 3);
  addEnvironmentSurface(root, 'Park path west', -20.2, 0, 1.5, 30, 'pavement-wet-overhaul', 0.01, 3);
  addEnvironmentSurface(root, 'Park path east', 20.2, 0, 1.5, 30, 'pavement-weathered-overhaul', 0.01, 3);
  addPathBetween(root, 'Park diagonal NW-SE', -20, -15, 20, 15, 1.8);
  addPathBetween(root, 'Park diagonal NE-SW', 20, -15, -20, 15, 1.8);

  const centre = new Mesh(
    getCylinderGeometry(2.4, 2.4, 0.18, 16),
    new MeshStandardMaterial({ color: 0x555d5b, roughness: 1 }),
  );
  centre.name = 'Provisional central park feature';
  centre.position.y = 0.08;
  root.add(centre);

  const fountainBasin = new Mesh(
    getCylinderGeometry(1.75, 1.9, 0.34, 12),
    createWorldMaterial('concrete-cracked-overhaul', {
      repeatX: 2,
      repeatY: 1,
      tint: 0x777d78,
      roughness: 0.78,
    }),
  );
  fountainBasin.name = 'Weathered park fountain basin';
  fountainBasin.position.y = 0.31;
  root.add(fountainBasin);
  const fountainWater = new Mesh(
    getCircleGeometry(1.48, 12),
    new MeshStandardMaterial({
      color: 0x102447,
      roughness: 0.3,
      metalness: 0.22,
    }),
  );
  fountainWater.name = 'Dark still fountain water';
  fountainWater.rotation.x = -Math.PI / 2;
  fountainWater.position.y = 0.49;
  root.add(fountainWater);
  const fountainColumn = new Mesh(
    getCylinderGeometry(0.22, 0.38, 1.25, 8),
    createWorldMaterial('concrete-cracked-overhaul', { tint: 0x606765 }),
  );
  fountainColumn.name = 'Fountain centre column';
  fountainColumn.position.y = 1.02;
  root.add(fountainColumn);

  const treeMaterial = createWorldMaterial('foliage-dark-overhaul', {
    repeatX: 2,
    repeatY: 2,
    tint: 0x446a43,
    roughness: 1,
  });
  const treeAmberMaterial = createWorldMaterial('foliage-dark-overhaul', {
    repeatX: 2,
    repeatY: 2,
    tint: 0x6f7138,
    emissive: 0x5a300b,
    emissiveIntensity: 0.16,
    roughness: 1,
  });
  const trunkMaterial = createWorldMaterial('tree-bark-temporary', {
    repeatX: 2,
    repeatY: 2,
  });
  for (const [index, [x, z]] of [
    [-15, -10], [-8, -11], [9, -11], [15, -8],
    [-17, -3], [17, -2], [-15, 9], [-8, 11],
    [9, 10], [15, 8], [-4, -6], [5, 6],
  ].entries()) {
    const tree = new Group();
    tree.name = 'Retro park tree';
    tree.position.set(x, 0, z);
    const trunk = new Mesh(getCylinderGeometry(0.14, 0.18, 1.6, 5), trunkMaterial);
    trunk.position.y = 0.8;
    tree.add(trunk);
    const crownMaterial = index % 4 === 0 ? treeAmberMaterial : treeMaterial;
    const crown = new Mesh(getDodecahedronGeometry(1.15), crownMaterial);
    crown.position.set(index % 2 === 0 ? -0.18 : 0.16, 2.05, 0);
    crown.scale.set(1.05, 1.25 + (index % 3) * 0.08, 0.92);
    crown.rotation.y = index * 0.73;
    tree.add(crown);
    const upperCrown = new Mesh(getDodecahedronGeometry(0.78), crownMaterial);
    upperCrown.position.set(index % 2 === 0 ? 0.28 : -0.25, 2.75, 0.08);
    upperCrown.scale.set(1.1, 0.85, 0.9);
    upperCrown.rotation.y = index * 0.41;
    tree.add(upperCrown);
    const sideCrown = new Mesh(getDodecahedronGeometry(0.68), crownMaterial);
    sideCrown.position.set(index % 3 === 0 ? 0.78 : -0.68, 1.92, 0.16);
    sideCrown.scale.set(1.18, 0.82, 1.02);
    sideCrown.rotation.set(index * 0.13, index * 0.59, index * 0.07);
    tree.add(sideCrown);
    root.add(tree);
  }

  for (const [x, z, rotation] of [
    [-12, -14, 0], [12, 14, Math.PI], [-19, 7, Math.PI / 2],
  ] as const) {
    const bench = new Group();
    bench.name = 'Weathered park bench';
    bench.position.set(x, 0, z);
    bench.rotation.y = rotation;
    const timber = createWorldMaterial('metal-oxidised-overhaul', {
      tint: 0x754b30,
      roughness: 0.96,
    });
    for (const offsetZ of [-0.16, 0.02, 0.2]) {
      const slat = createBox(2.1, 0.11, 0.14, timber);
      slat.position.set(0, 0.57, offsetZ);
      bench.add(slat);
    }
    for (const offsetX of [-0.78, 0.78]) {
      const leg = createBox(0.12, 0.56, 0.36, 0x24282a);
      leg.position.set(offsetX, 0.28, 0.04);
      bench.add(leg);
    }
    root.add(bench);
  }

  const playgroundReserve = addSurface(
    root,
    'Future playground reserved area',
    12.5,
    3,
    8,
    6,
    0x38543b,
    0.02,
  );
  playgroundReserve.material = new MeshStandardMaterial({
    color: 0x38543b,
    roughness: 1,
    wireframe: true,
  });
  addDevelopmentLabel(root, 'Future Playground', 12.5, 1.2, 3);
  addDevelopmentLabel(root, 'Central Park', 0, 2.2, 0);
}

function addCrossing(
  root: Group,
  name: string,
  x: number,
  z: number,
  rotation = 0,
): void {
  const crossing = new Group();
  crossing.name = name;
  crossing.position.set(x, 0.015, z);
  crossing.rotation.y = rotation;
  for (let index = -2; index <= 2; index += 1) {
    const stripe = createBox(0.45, 0.03, 4.8, 0xd3d0c4);
    stripe.position.x = index * 0.9;
    crossing.add(stripe);
  }
  root.add(crossing);
}

function addRoadAnnotation(
  root: Group,
  text: string,
  x: number,
  z: number,
  rotation = 0,
): void {
  const canvas = document.createElement('canvas');
  canvas.width = 256;
  canvas.height = 64;
  const context = canvas.getContext('2d');
  if (!context) {
    return;
  }
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = '#d9d2b2';
  context.font = 'bold 31px ui-monospace, monospace';
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  context.fillText(text, canvas.width / 2, canvas.height / 2);
  const texture = applyTextureProfile(
    new CanvasTexture(canvas),
    'RETRO_GRAPHIC',
  );
  texture.colorSpace = SRGBColorSpace;
  const marking = createBox(
    3.4,
    0.025,
    0.8,
    new MeshBasicMaterial({
      map: texture,
      transparent: true,
      depthWrite: false,
    }),
  );
  marking.name = `Survey road marking ${text}`;
  marking.position.set(x, 0.035, z);
  marking.rotation.y = rotation;
  root.add(marking);
}

function addRoadAndPavementLayout(root: Group): void {
  const road = (
    name: string,
    x: number,
    z: number,
    width: number,
    depth: number,
  ): void => {
    addEnvironmentSurface(
      root,
      name,
      x,
      z,
      width,
      depth,
      'asphalt-wet-overhaul',
      -0.05,
      4,
    );
  };
  const pavement = (
    name: string,
    x: number,
    z: number,
    width: number,
    depth: number,
    damp = false,
  ): void => {
    addEnvironmentSurface(
      root,
      name,
      x,
      z,
      width,
      depth,
      damp ? 'pavement-wet-overhaul' : 'pavement-weathered-overhaul',
      -0.045,
      3,
    );
  };

  road('North perimeter road', 0, -25.5, 72, ROAD_WIDTH);
  road('South perimeter road', 0, 25.5, 72, ROAD_WIDTH);
  road('West perimeter road', -29.5, 0, ROAD_WIDTH, 66);
  road('East perimeter road', 29.5, 0, ROAD_WIDTH, 66);
  road('Outer North Road', 0, -44.2, 114, ROAD_WIDTH);
  road('Outer South Road', 0, 48, 114, ROAD_WIDTH);
  road('Outer west street', -48, 0, ROAD_WIDTH, 96);
  road('Outer east street', 57, 0, ROAD_WIDTH, 96);
  road('North Road outward connection', 0, -55, ROAD_WIDTH, 16);
  road('South Road outward connection', 0, 57, ROAD_WIDTH, 14);
  road('West outward connection', -58, 25.5, 16, ROAD_WIDTH);
  road('East outward connection', 61, 0, 8, ROAD_WIDTH);

  pavement('Park north pavement', 0, -19.4, 49, PAVEMENT_WIDTH, true);
  pavement('Park south pavement', 0, 19.4, 49, PAVEMENT_WIDTH);
  pavement('Park west pavement', -24.4, 0, PAVEMENT_WIDTH, 39, true);
  pavement('Park east pavement', 24.4, 0, PAVEMENT_WIDTH, 39);
  pavement('North building pavement', 0, -31.1, 72, 3.6, true);
  pavement('South building pavement', 0, 31.1, 72, 3.6);
  pavement('West building pavement', -34.2, 0, 2, 66, true);
  pavement('East building pavement', 34.2, 0, 2, 66);

  const northKerbMarkingMaterial = new MeshStandardMaterial({
    color: 0xb58a18,
    emissive: 0x2e1c02,
    emissiveIntensity: 0.12,
    roughness: 0.86,
  });
  for (const z of [-29.02, -28.76]) {
    const line = createBox(18, 0.025, 0.08, northKerbMarkingMaterial);
    line.name = 'Dreams worn double yellow kerb marking';
    line.position.set(0, 0.028, z);
    root.add(line);
  }
  addCrossing(root, 'South park crossing', 0, 25.5);
  addCrossing(root, 'West park crossing', -29.5, 0, Math.PI / 2);
  addCrossing(root, 'East park crossing', 29.5, 0, Math.PI / 2);

  addRoadAnnotation(root, 'N-025.5', -9, -25.5);
  addRoadAnnotation(root, 'X 29.5', 29.5, 8, Math.PI / 2);
  addRoadAnnotation(root, 'Z +48', 17, 48);
}

function addCarPark(root: Group, location: WorldLocation): void {
  addEnvironmentSurface(
    root,
    'Car Park blockout surface',
    location.x,
    location.z,
    location.width,
    location.depth,
    'asphalt-wet-overhaul',
    -0.02,
    4,
  );
  for (const offsetZ of [-4.2, 0, 4.2]) {
    addSurface(
      root,
      'Car Park bay marker',
      location.x,
      location.z + offsetZ,
      location.width - 2,
      0.12,
      0xb5ad83,
      0.04,
    );
  }
  addDevelopmentLabel(root, location.name, location.x, 1.8, location.z);
}

function addBikeDock(root: Group, marker: WorldMarker): void {
  const dock = new Group();
  dock.name = marker.name;
  dock.position.set(marker.x, 0, marker.z);
  for (let index = 0; index < 5; index += 1) {
    const stand = createBox(0.18, 0.7, 0.55, 0xd2ad26);
    stand.position.set((index - 2) * 0.55, 0.35, 0);
    dock.add(stand);
  }
  root.add(dock);
  addDevelopmentLabel(root, marker.name, marker.x, 1.8, marker.z);
}

function addStreetBin(root: Group, x: number, z: number, rotation = 0): void {
  const bin = new Group();
  bin.name = 'Weathered street bin';
  bin.position.set(x, 0, z);
  bin.rotation.y = rotation;
  const body = createBox(
    0.66,
    1.04,
    0.58,
    createWorldMaterial('metal-oxidised-overhaul', {
      tint: 0x344944,
      roughness: 0.9,
      metalness: 0.08,
    }),
  );
  body.position.y = 0.52;
  bin.add(body);
  const opening = createBox(0.46, 0.17, 0.05, 0x080a0b);
  opening.position.set(0, 0.72, 0.315);
  bin.add(opening);
  const lid = createBox(0.74, 0.11, 0.66, 0x20292a);
  lid.position.y = 1.08;
  bin.add(lid);
  root.add(bin);
}

function addBollard(root: Group, x: number, z: number, tint = 0x23282b): void {
  const bollard = new Mesh(
    getCylinderGeometry(0.12, 0.15, 0.82, 7),
    createWorldMaterial('metal-oxidised-overhaul', {
      tint,
      roughness: 0.86,
      metalness: 0.14,
    }),
  );
  bollard.name = 'Battered pavement bollard';
  bollard.position.set(x, 0.41, z);
  root.add(bollard);
}

function addRubbishBag(root: Group, x: number, z: number, scale = 1): void {
  const bag = new Mesh(
    getDodecahedronGeometry(0.38 * scale),
    new MeshStandardMaterial({
      color: 0x0b0c11,
      roughness: 0.44,
      metalness: 0.06,
    }),
  );
  bag.name = 'Discarded rubbish bag';
  bag.scale.set(1, 1.35, 0.8);
  bag.position.set(x, 0.39 * scale, z);
  bag.rotation.set(0.08, x * 0.31, -0.1);
  root.add(bag);
}

function addDrainCover(root: Group, x: number, z: number, rotation = 0): void {
  const cover = createBox(
    0.52,
    0.025,
    1.05,
    createWorldMaterial('metal-oxidised-overhaul', {
      repeatX: 1,
      repeatY: 2,
      tint: 0x3e4546,
      roughness: 0.52,
      metalness: 0.32,
    }),
  );
  cover.name = 'Wet iron drain cover';
  cover.position.set(x, 0.045, z);
  cover.rotation.y = rotation;
  root.add(cover);
}

function addUtilityBox(root: Group, x: number, z: number, rotation = 0): void {
  const box = new Group();
  box.name = 'Stickered utility cabinet';
  box.position.set(x, 0, z);
  box.rotation.y = rotation;
  const cabinet = createBox(
    1.08,
    1.42,
    0.42,
    createWorldMaterial('metal-oxidised-overhaul', {
      tint: 0x435355,
      roughness: 0.84,
      metalness: 0.16,
    }),
  );
  cabinet.position.y = 0.71;
  box.add(cabinet);
  const posters = createBox(
    0.7,
    0.82,
    0.025,
    createWorldMaterial('poster-wall-overhaul', {
      clamp: true,
      roughness: 0.95,
    }),
  );
  posters.position.set(0, 0.75, 0.225);
  box.add(posters);
  root.add(box);
}

function addPaperLitter(root: Group, x: number, z: number, rotation = 0): void {
  const paper = createBox(
    0.34,
    0.012,
    0.24,
    new MeshStandardMaterial({ color: 0xbab39c, roughness: 1 }),
  );
  paper.name = 'Discarded paper litter';
  paper.position.set(x, 0.055, z);
  paper.rotation.y = rotation;
  root.add(paper);
}

function addShoppingTrolley(root: Group, x: number, z: number, rotation = 0): void {
  const trolley = new Group();
  trolley.name = 'Abandoned shopping trolley';
  trolley.position.set(x, 0, z);
  trolley.rotation.y = rotation;
  const wire = new MeshStandardMaterial({
    color: 0x7b6c66,
    roughness: 0.48,
    metalness: 0.62,
    wireframe: true,
  });
  const basket = new Mesh(getBoxGeometry(1.15, 0.62, 0.72, 4, 3, 3), wire);
  basket.name = 'Trolley wire basket';
  basket.position.set(0, 0.83, 0);
  basket.rotation.z = -0.08;
  trolley.add(basket);
  const frame = createBox(0.11, 0.72, 1.12, 0x5f5a58);
  frame.position.set(-0.48, 0.43, 0);
  frame.rotation.z = -0.22;
  trolley.add(frame);
  const handle = createBox(0.12, 0.12, 1.12, 0xc03f45);
  handle.position.set(-0.61, 1.24, 0);
  trolley.add(handle);
  for (const [wheelX, wheelZ] of [[-0.42, -0.34], [-0.42, 0.34], [0.4, -0.34], [0.4, 0.34]] as const) {
    const wheel = new Mesh(
      getCylinderGeometry(0.1, 0.1, 0.08, 7),
      getStandardColorMaterial(0x111214),
    );
    wheel.position.set(wheelX, 0.12, wheelZ);
    wheel.rotation.x = Math.PI / 2;
    trolley.add(wheel);
  }
  root.add(trolley);
}

function addStreetDressing(root: Group): void {
  for (const [x, z, rotation] of [
    [-11.9, 20.1, -0.08], [22.7, -19.8, 0.12], [-34.9, 8.8, Math.PI / 2],
    [34.8, 21, -Math.PI / 2], [17.5, 31.1, Math.PI],
  ] as const) {
    addStreetBin(root, x, z, rotation);
  }
  for (const [x, z] of [
    [-16.7, -19.7], [-14.9, -19.7], [18.5, -19.6], [20.2, -19.6],
    [-34.6, -4], [-34.6, -1.9], [34.5, 13.2], [34.5, 15.1],
    [-11.5, 31.2], [-9.7, 31.2], [21.8, 31.1],
  ] as const) {
    addBollard(root, x, z);
  }
  for (const [x, z, scale] of [
    [-12.6, 20.4, 0.85], [-33.9, 18.8, 1], [35.1, 16.8, 0.9], [28.1, 31.1, 1.05],
  ] as const) {
    addRubbishBag(root, x, z, scale);
  }
  for (const [x, z, rotation] of [
    [-5.7, 23.9, 0], [13.4, -23.1, 0], [-27.1, 10.5, Math.PI / 2],
    [27, -7, Math.PI / 2], [6.8, 28.9, 0],
  ] as const) {
    addDrainCover(root, x, z, rotation);
  }
  addShoppingTrolley(root, -5.8, 20.2, 0.16);
  addShoppingTrolley(root, 31.9, 20.9, -0.74);
  addUtilityBox(root, -34.7, -11.7, Math.PI / 2);
  addUtilityBox(root, 34.5, 6.4, -Math.PI / 2);
  addUtilityBox(root, 25.6, 31.2, Math.PI);
  for (const [x, z, rotation] of [
    [-6.4, 20.8, 0.4], [-7.2, 21.7, -0.9], [-15.3, -19.1, 0.2],
    [-31.4, 6.2, -0.5], [-29.1, 17.8, 1.2], [30.1, 19.5, -0.7],
    [4.8, 29.1, 0.5], [12.1, 30.6, -0.2],
  ] as const) {
    addPaperLitter(root, x, z, rotation);
  }

  addReflectionPatch(root, 'Bus shelter magenta spill', -8.2, 22.2, 1.1, 4.8, VISUAL_STYLE.lighting.magenta, 0.3, -0.12);
  addReflectionPatch(root, 'Bus shelter green spill', -10.2, 21.4, 0.8, 3.1, VISUAL_STYLE.lighting.fluorescent, 0.2, 0.15);
  addReflectionPatch(root, 'Dreams cool fascia spill', 0.2, -25.4, 2.1, 5.8, VISUAL_STYLE.lighting.coldWhite, 0.25, 0.03);
  addReflectionPatch(root, 'Dreams broken secondary spill', -3.1, -26.3, 1.15, 4.3, 0x8fd8e6, 0.13, -0.07);
  addReflectionPatch(root, 'Dreams broken east spill', 3.7, -25.8, 1.35, 4.8, 0xb9e2e8, 0.12, 0.08);
  addReflectionPatch(root, 'Renae fascia spill', 16.5, -25.8, 1.2, 4.4, VISUAL_STYLE.lighting.magenta, 0.2, -0.1);
  addReflectionPatch(root, 'M1 fascia spill', -30.3, 7, 4.8, 0.75, VISUAL_STYLE.lighting.sodium, 0.2, -0.04);
  addReflectionPatch(root, 'Coral fascia spill', -30.1, 17.1, 4.4, 0.72, VISUAL_STYLE.lighting.coldWhite, 0.16, 0.06);
  addReflectionPatch(root, 'Advanced Photo fascia spill', 30.3, 17.2, 4.6, 0.68, VISUAL_STYLE.lighting.coldWhite, 0.14, -0.04);
  addReflectionPatch(root, 'Arts Council fascia spill', 30.2, 22.6, 4.1, 0.62, VISUAL_STYLE.lighting.sodium, 0.17, 0.08);
  addReflectionPatch(root, 'Vinyl Exchange fascia spill', -18.7, 26.1, 0.75, 4.7, VISUAL_STYLE.lighting.sodium, 0.2, 0.04);
  addReflectionPatch(root, 'Spice Cabin fascia spill', 10.3, 26.2, 0.82, 4.2, VISUAL_STYLE.lighting.magenta, 0.18, -0.08);
}

function addStreetlight(
  root: Group,
  x: number,
  z: number,
  color: number = VISUAL_STYLE.lighting.sodium,
): void {
  const lamp = new Group();
  lamp.name = 'Public illumination streetlight';
  lamp.position.set(x, 0, z);
  const pole = new Mesh(
    getCylinderGeometry(0.075, 0.105, 4.2, 6),
    createWorldMaterial('metal-oxidised-overhaul', {
      repeatX: 1,
      repeatY: 3,
      tint: 0x5c6063,
    }),
  );
  pole.position.y = 2.1;
  lamp.add(pole);
  const head = createBox(
    0.52,
    0.16,
    0.38,
    getBasicColorMaterial(color),
  );
  head.position.y = 4.18;
  lamp.add(head);

  const pool = new Mesh(
    getCircleGeometry(2.45, 12),
    createAdditiveWorldMaterial('reflection-broken-overhaul', color, 0.23),
  );
  pool.name = 'Streetlight painted pool';
  pool.rotation.x = -Math.PI / 2;
  pool.position.y = 0.035;
  lamp.add(pool);

  const cone = new Mesh(
    getConeGeometry(2.4, 4.05, 8, 1, true),
    createAdditiveWorldMaterial('light-cone-noise-overhaul', color, 0.095),
  );
  cone.name = 'Visible sodium light cone';
  cone.position.y = 2.1;
  lamp.add(cone);

  const longReflection = createBox(
    0.7,
    0.018,
    4.9,
    createAdditiveWorldMaterial('reflection-broken-overhaul', color, 0.25),
  );
  longReflection.name = 'Broken streetlight reflection';
  longReflection.position.set(0.35, 0.04, 2.1);
  longReflection.rotation.y = 0.08;
  lamp.add(longReflection);
  const sideReflection = createBox(
    0.42,
    0.018,
    2.6,
    createAdditiveWorldMaterial('reflection-broken-overhaul', color, 0.15),
  );
  sideReflection.name = 'Secondary broken streetlight reflection';
  sideReflection.position.set(-0.72, 0.042, 1.25);
  sideReflection.rotation.y = -0.2;
  lamp.add(sideReflection);

  root.add(lamp);
}

function addStylizedSky(root: Group): void {
  const skyDome = new Mesh(
    new SphereGeometry(104, 16, 8),
    new ShaderMaterial({
      uniforms: {
        horizonColor: { value: new Color(VISUAL_STYLE.sky.horizonColor) },
        zenithColor: { value: new Color(VISUAL_STYLE.sky.color) },
      },
      vertexShader: `
        varying vec3 vPosition;
        void main() {
          vPosition = position;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform vec3 horizonColor;
        uniform vec3 zenithColor;
        varying vec3 vPosition;
        void main() {
          float elevation = smoothstep(-0.08, 0.72, normalize(vPosition).y);
          gl_FragColor = vec4(mix(horizonColor, zenithColor, elevation), 1.0);
        }
      `,
      side: BackSide,
      depthWrite: false,
      fog: false,
    }),
  );
  skyDome.name = 'Cobalt gradient sky dome';
  skyDome.renderOrder = -10;
  root.add(skyDome);

  const geometry = new BufferGeometry();
  const positions = new Float32Array(VISUAL_STYLE.sky.starCount * 3);
  let seed = 9137;
  const random = (): number => {
    seed = (seed * 16807) % 2147483647;
    return (seed - 1) / 2147483646;
  };

  for (let index = 0; index < VISUAL_STYLE.sky.starCount; index += 1) {
    const angle = random() * Math.PI * 2;
    const radius = 50 + random() * 38;
    positions[index * 3] = Math.cos(angle) * radius;
    positions[index * 3 + 1] = 9 + random() * 30;
    positions[index * 3 + 2] = Math.sin(angle) * radius;
  }

  geometry.setAttribute('position', new BufferAttribute(positions, 3));
  const stars = new Points(
    geometry,
    new PointsMaterial({
      color: VISUAL_STYLE.sky.starColor,
      size: 0.42,
      sizeAttenuation: true,
      fog: false,
    }),
  );
  stars.name = 'Stylized star field';
  root.add(stars);

  const brightGeometry = new BufferGeometry();
  brightGeometry.setAttribute(
    'position',
    new BufferAttribute(positions.slice(0, 42 * 3), 3),
  );
  const brightStars = new Points(
    brightGeometry,
    new PointsMaterial({
      color: 0xffd9c3,
      size: 0.94,
      sizeAttenuation: true,
      fog: false,
    }),
  );
  brightStars.name = 'Sparse warm bright stars';
  root.add(brightStars);
}

function addNorthEstateBackdrop(root: Group): void {
  const towerMaterial = createWorldMaterial('brick-soot-overhaul', {
    repeatX: 4,
    repeatY: 8,
    tint: 0x514443,
    emissive: 0x050812,
    emissiveIntensity: 0.05,
    roughness: 0.98,
  });
  const darkWindow = createWorldMaterial('window-dark-temporary', {
    clamp: true,
    tint: 0x11182a,
    emissive: 0x071126,
    emissiveIntensity: 0.08,
    roughness: 0.8,
  });
  const litWindow = createWorldMaterial('window-lit-temporary', {
    clamp: true,
    emissive: VISUAL_STYLE.lighting.sodium,
    emissiveIntensity: 0.62,
    roughness: 0.68,
  });

  for (const [side, x, z, width, height] of [
    ['west', -13.5, -48.5, 10.5, 16.5],
    ['east', 14.5, -49, 11.5, 18.5],
  ] as const) {
    const tower = createBox(width, height, 6, towerMaterial);
    tower.name = `North road ${side} estate tower`;
    tower.position.set(x, height / 2, z);
    root.add(tower);

    for (let floor = 0; floor < 7; floor += 1) {
      for (let column = 0; column < 4; column += 1) {
        const isLit = (floor * 5 + column * 3 + (side === 'west' ? 1 : 2)) % 7 === 0;
        const window = createBox(0.72, 0.85, 0.06, isLit ? litWindow : darkWindow);
        window.name = `North road ${side} tower ${isLit ? 'lit' : 'dark'} window`;
        window.position.set(
          x - width * 0.34 + column * (width * 0.225),
          2.05 + floor * 1.9,
          z + 3.04,
        );
        root.add(window);
      }
    }
  }
}

function addDevelopmentPickup(root: Group): (deltaTime: number) => void {
  if (!import.meta.env.DEV) {
    return () => undefined;
  }

  const pickup = new Group();
  pickup.name = 'Dreamcast-style pickup prototype';
  pickup.position.set(5, 1, 10.5);

  const halo = new Mesh(
    new SphereGeometry(1.15, 10, 6),
    createHaloMaterial(VISUAL_STYLE.lighting.magenta, 0.19),
  );
  halo.name = 'Pickup translucent halo';
  pickup.add(halo);

  const core = new Mesh(
    new OctahedronGeometry(0.42, 0),
    new MeshBasicMaterial({ color: 0xffd146 }),
  );
  core.name = 'Pickup faceted core';
  pickup.add(core);

  const ring = new Mesh(
    new TorusGeometry(0.62, 0.075, 5, 10),
    new MeshBasicMaterial({ color: VISUAL_STYLE.lighting.fluorescent }),
  );
  ring.name = 'Pickup graphic ring';
  ring.rotation.x = Math.PI / 2;
  pickup.add(ring);

  root.add(pickup);

  const pool = new Mesh(
    getCircleGeometry(1.6, 12),
    createHaloMaterial(VISUAL_STYLE.lighting.magenta, 0.24),
  );
  pool.name = 'Pickup fake coloured pool';
  pool.position.set(5, 0.04, 10.5);
  pool.rotation.x = -Math.PI / 2;
  root.add(pool);

  let elapsedTime = 0;
  return (deltaTime: number): void => {
    elapsedTime += deltaTime;
    pickup.rotation.y += deltaTime * 1.15;
    ring.rotation.z -= deltaTime * 0.72;
    pickup.position.y = 1 + Math.sin(elapsedTime * 1.8) * 0.14;
  };
}

function addHeroLocalLights(root: Group): PointLight[] {
  const definitions = [
    ['Bus Stop A hero light', -9, 2.35, 20.4, 0xb9ffe7, 8, 8],
    ['Dreams hero light', 0, 4.5, -30.8, VISUAL_STYLE.lighting.coldWhite, 3, 10],
    ['Renae hero light', 17, 2.5, -30.8, VISUAL_STYLE.lighting.magenta, 7, 9],
    ['Florist hero light', -16, 2.7, -31, VISUAL_STYLE.lighting.sodium, 7.5, 9],
    ['Bus Stop B hero light', 0, 2.35, -49, 0xb9ffe7, 8, 8],
  ] as const;

  return definitions.map(([name, x, y, z, color, intensity, distance]) => {
    const light = new PointLight(color, intensity, distance, 2);
    light.name = name;
    light.position.set(x, y, z);
    light.visible = false;
    root.add(light);
    return light;
  });
}

export function createWorld(scene: Scene, maximumActiveLocalLights: number): World {
  scene.background = new Color(VISUAL_STYLE.sky.color);
  scene.fog = new Fog(
    VISUAL_STYLE.fog.color,
    VISUAL_STYLE.fog.near,
    VISUAL_STYLE.fog.far,
  );
  const root = new Group();
  root.name = 'Canonical city layout Map v0.3';
  scene.add(root);
  addStylizedSky(root);

  addEnvironmentSurface(
    root,
    'World ground',
    0,
    0,
    128,
    124,
    'concrete-cracked-overhaul',
    -0.12,
    5,
  );
  addRoadAndPavementLayout(root);
  addCentralPark(root);
  addNorthEstateBackdrop(root);
  const updatePickup = addDevelopmentPickup(root);

  const obstacles: CollisionObstacle[] = [];
  for (const location of WORLD_LOCATIONS) {
    if (location.kind === 'building') {
      addBuildingLocation(root, obstacles, location);
    } else if (location.kind === 'car-park') {
      addCarPark(root, location);
    }
  }

  addBusShelter(root, obstacles, BUS_STOPS[0], -Math.PI / 2);
  addBusShelter(root, obstacles, BUS_STOPS[1], -Math.PI / 2);
  addStreetDressing(root);
  for (const marker of STERLING_BIKE_DOCKS) {
    addBikeDock(root, marker);
  }
  for (const marker of FUTURE_EXITS) {
    addDevelopmentLabel(root, `${marker.name} →`, marker.x, 2.2, marker.z);
  }

  for (const [x, z, color] of [
    [-20, -19, VISUAL_STYLE.lighting.sodium],
    [20, -19, VISUAL_STYLE.lighting.sodium],
    [-18, 19, VISUAL_STYLE.lighting.sodium],
    [-9, 19, VISUAL_STYLE.lighting.sodium],
    [8, 19, VISUAL_STYLE.lighting.magenta],
    [16, 19, VISUAL_STYLE.lighting.magenta],
    [-25, -10, VISUAL_STYLE.lighting.coldWhite],
    [-25, 10, VISUAL_STYLE.lighting.sodium],
    [25, -10, VISUAL_STYLE.lighting.fluorescent],
    [25, 10, VISUAL_STYLE.lighting.coldWhite],
    [-12, -29, VISUAL_STYLE.lighting.sodium],
    [12, -29, VISUAL_STYLE.lighting.magenta],
    [-12, 29, VISUAL_STYLE.lighting.sodium],
    [12, 29, VISUAL_STYLE.lighting.sodium],
    [-34, 7, VISUAL_STYLE.lighting.sodium],
    [34, 17, VISUAL_STYLE.lighting.coldWhite],
  ] as const) {
    addStreetlight(root, x, z, color);
  }

  const heroLocalLights = addHeroLocalLights(root);
  const nearestLightDistances = heroLocalLights.map((light) => ({
    light,
    distanceSquared: 0,
  }));

  const updateHeroLocalLights = (playerPosition: Vector3): void => {
    for (const candidate of nearestLightDistances) {
      candidate.distanceSquared = candidate.light.position.distanceToSquared(playerPosition);
    }
    nearestLightDistances.sort((a, b) => a.distanceSquared - b.distanceSquared);
    for (let index = 0; index < nearestLightDistances.length; index += 1) {
      nearestLightDistances[index].light.visible = index < maximumActiveLocalLights;
    }
  };

  scene.add(
    new HemisphereLight(
      VISUAL_STYLE.lighting.ambientSky,
      VISUAL_STYLE.lighting.ambientGround,
      VISUAL_STYLE.lighting.ambientIntensity,
    ),
  );
  const moonlight = new DirectionalLight(
    VISUAL_STYLE.lighting.moonColor,
    VISUAL_STYLE.lighting.moonIntensity,
  );
  moonlight.position.set(-8, 14, 10);
  scene.add(moonlight);

  return {
    root,
    collision: {
      bounds: WORLD_BOUNDS,
      obstacles,
    },
    update: (deltaTime, playerPosition) => {
      updatePickup(deltaTime);
      updateHeroLocalLights(playerPosition);
    },
    getLightingStats: () => ({
      activePointLights: heroLocalLights.filter((light) => light.visible).length,
      activeSpotLights: 0,
      maximumActiveLocalLights,
    }),
    setDevelopmentOverlaysVisible: (visible: boolean) => {
      root.traverse((child) => {
        if (child.userData.developmentOverlay === true) {
          child.visible = visible;
        }
      });
    },
  };
}
