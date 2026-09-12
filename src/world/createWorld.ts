import {
  BackSide,
  Box3,
  BoxGeometry,
  CanvasTexture,
  CircleGeometry,
  Color,
  ConeGeometry,
  CylinderGeometry,
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
  addHeroStreetEnvironmentKit,
  addParkEdgeEnvironmentKit,
} from './createEnvironmentKit';
import {
  BUS_STOPS,
  FOOD_STANDS,
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
const standardColorMaterialCache = new Map<number, MeshStandardMaterial>();
const basicColorMaterialCache = new Map<number, MeshBasicMaterial>();
const BUS_SHELTER_SCALE = 1.3;

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
  });
}

function addReneeInteriorCollision(
  obstacles: CollisionObstacle[],
  location: WorldLocation,
): void {
  const addLocalObstacle = (
    name: string,
    minX: number,
    maxX: number,
    minZ: number,
    maxZ: number,
  ): void => {
    obstacles.push({
      name: `Renee ${name}`,
      minX: location.x + minX,
      maxX: location.x + maxX,
      minZ: location.z + minZ,
      maxZ: location.z + maxZ,
    });
  };

  // The authored Blender frontage faces -Y, which imports as local +Z.
  // Split the front wall around a generous 1.8 m entrance gap so the
  // player's 0.38 m collision circle can cross without catching the jambs.
  addLocalObstacle('left wall', -6.90, -6.62, -6.60, 6.60);
  addLocalObstacle('right wall', 6.62, 6.90, -6.60, 6.60);
  addLocalObstacle('rear wall', -6.90, 6.90, -6.60, -6.32);
  addLocalObstacle('shopfront left', -6.90, -2.62, 6.20, 6.62);
  addLocalObstacle('shopfront right', -0.82, 6.90, 6.20, 6.62);

  // Hero fixtures and fixed seating remain solid once the player is inside.
  addLocalObstacle('main bar', -5.64, 0.54, -4.22, -3.22);
  addLocalObstacle('front column', -0.56, -0.14, 1.06, 1.54);
  addLocalObstacle('middle column', -0.56, -0.14, -2.59, -2.11);
  addLocalObstacle('right column', 4.64, 5.06, -1.09, -0.61);
  addLocalObstacle('right banquette', 5.98, 6.70, -3.23, 3.93);
  addLocalObstacle('front-left banquette', -6.10, -3.00, 5.58, 6.28);
  addLocalObstacle('toilets volume', -6.63, -4.81, -6.46, -5.30);
}

function addCassArtInteriorCollision(
  obstacles: CollisionObstacle[],
  location: WorldLocation,
): void {
  const halfWidth = location.width / 2;
  const halfDepth = location.depth / 2;
  const wall = 0.22;
  const frontZ = location.z - halfDepth;
  const rearZ = location.z + halfDepth;
  const scale = location.width / 18;
  // The authored door is at local X +2.15. The north-facing placement rotates
  // the asset 180 degrees, moving the entrance west of the plot centre.
  const entranceX = location.x - 2.15 * scale;
  const entranceHalfWidth = 0.82 * scale;

  obstacles.push(
    {
      name: 'Cass Art west wall',
      minX: location.x - halfWidth,
      maxX: location.x - halfWidth + wall,
      minZ: frontZ,
      maxZ: rearZ,
    },
    {
      name: 'Cass Art east wall',
      minX: location.x + halfWidth - wall,
      maxX: location.x + halfWidth,
      minZ: frontZ,
      maxZ: rearZ,
    },
    {
      name: 'Cass Art rear wall',
      minX: location.x - halfWidth,
      maxX: location.x + halfWidth,
      minZ: rearZ - wall,
      maxZ: rearZ,
    },
    {
      name: 'Cass Art shopfront west',
      minX: location.x - halfWidth,
      maxX: entranceX - entranceHalfWidth,
      minZ: frontZ,
      maxZ: frontZ + 0.28,
    },
    {
      name: 'Cass Art shopfront east',
      minX: entranceX + entranceHalfWidth,
      maxX: location.x + halfWidth,
      minZ: frontZ,
      maxZ: frontZ + 0.28,
    },
  );
}

function addCoralInteriorCollision(
  obstacles: CollisionObstacle[],
  location: WorldLocation,
): void {
  const westX = location.x - location.width / 2;
  const eastX = location.x + location.width / 2;
  const northZ = location.z - location.depth / 2;
  const southZ = location.z + location.depth / 2;
  const wall = 0.26;
  // Coral's Blender frontage is 17.4 m long with the door at local X -1.55.
  // After the east-facing quarter turn, that door lies north of plot centre.
  const doorZ = location.z + 1.55;
  const doorHalfWidth = 0.82;

  obstacles.push(
    {
      name: 'Coral north wall',
      minX: westX,
      maxX: eastX,
      minZ: northZ,
      maxZ: northZ + wall,
    },
    {
      name: 'Coral south wall',
      minX: westX,
      maxX: eastX,
      minZ: southZ - wall,
      maxZ: southZ,
    },
    {
      name: 'Coral rear wall',
      minX: westX,
      maxX: westX + wall,
      minZ: northZ,
      maxZ: southZ,
    },
    {
      name: 'Coral shopfront north',
      minX: eastX - 0.34,
      maxX: eastX,
      minZ: northZ,
      maxZ: doorZ - doorHalfWidth,
    },
    {
      name: 'Coral shopfront south',
      minX: eastX - 0.34,
      maxX: eastX,
      minZ: doorZ + doorHalfWidth,
      maxZ: southZ,
    },
  );

  // Fixed betting terminals remain solid while preserving a clear route from
  // the entrance to the rear information wall.
  for (const [index, localX] of [-6.2, -3.7, 0.25, 2.75, 5.35].entries()) {
    const centreZ = location.z - localX;
    obstacles.push({
      name: `Coral counter ${index + 1}`,
      minX: location.x - 0.98,
      maxX: location.x + 0.08,
      minZ: centreZ - 0.88,
      maxZ: centreZ + 0.88,
    });
  }
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

function applyBusShelterGeometryPolicy(model: Group): void {
  const shelterRoot = model.getObjectByName('PRESTON_BUS_SHELTER');
  if (shelterRoot) {
    // The shelter root contains the frame, glazing, signage and bench. The
    // trolley is a sibling root, so it deliberately remains at authored size.
    shelterRoot.scale.multiplyScalar(BUS_SHELTER_SCALE);
  }

  model.traverse((child) => {
    if (!(child instanceof Mesh)) {
      return;
    }
    child.castShadow = true;
    child.receiveShadow = true;
    const materials = Array.isArray(child.material)
      ? child.material
      : [child.material];
    for (const material of materials) {
      if (!(material instanceof MeshStandardMaterial)) {
        continue;
      }
      const name = material.name.toLowerCase();
      if (name.includes('busstop_glass')) {
        material.transparent = true;
        material.opacity = 0.24;
        material.depthWrite = false;
        material.roughness = 0.12;
        material.metalness = 0.05;
      } else {
        // Preserve the geometry-pass material IDs and avoid accidental baked
        // photographic maps while this version is under proportion review.
        material.map = null;
        material.emissiveMap = null;
        material.roughness = Math.max(material.roughness, 0.38);
      }
    }
  });
}

function applyNiceThingsBlockoutPolicy(model: Group): void {
  applyPhotographicModelPolicy(model);
  model.traverse((child) => {
    if (!(child instanceof Mesh)) {
      return;
    }
    child.castShadow = true;
    child.receiveShadow = true;
    const materials = Array.isArray(child.material)
      ? child.material
      : [child.material];
    for (const material of materials) {
      if (!(material instanceof MeshStandardMaterial)) {
        continue;
      }
      if (material.name === 'MAT_NT_Glass_PLACEHOLDER') {
        material.transparent = true;
        material.opacity = 0.16;
        material.depthWrite = false;
        material.roughness = 0.22;
      } else {
        material.roughness = Math.max(material.roughness, 0.72);
      }
    }
  });
}

function applyVillageBooksBlockoutPolicy(model: Group): void {
  // Village Books is still at its geometry-review hold. Preserve the authored
  // placeholder palette, disable accidental emissive treatment and configure
  // only the documented shopfront/upper glazing for the runtime renderer.
  model.traverse((child) => {
    if (!(child instanceof Mesh)) {
      return;
    }
    child.castShadow = true;
    child.receiveShadow = true;
    const materials = Array.isArray(child.material)
      ? child.material
      : [child.material];
    for (const material of materials) {
      if (!(material instanceof MeshStandardMaterial)) {
        continue;
      }
      material.map = null;
      material.emissiveMap = null;
      material.emissive.set(0x000000);
      material.emissiveIntensity = 0;
      if (material.name === 'MAT_VB_Glass_PLACEHOLDER') {
        material.transparent = true;
        material.opacity = 0.2;
        material.depthWrite = false;
        material.roughness = 0.18;
        material.metalness = 0.04;
      } else {
        material.roughness = Math.max(material.roughness, 0.58);
      }
    }
  });
}

function applyDreamsModelPolicy(model: Group): void {
  applyPhotographicModelPolicy(model);
  model.traverse((child) => {
    if (!(child instanceof Mesh)) {
      return;
    }
    child.castShadow = true;
    child.receiveShadow = true;
    const materials = Array.isArray(child.material)
      ? child.material
      : [child.material];
    for (const material of materials) {
      if (!(material instanceof MeshStandardMaterial)) {
        continue;
      }
      if (material.name.includes('mat-dreams-photographic-front')) {
        material.emissive.set(0xc7dce0);
        material.emissiveMap = material.map;
        material.emissiveIntensity = 0.09 * VISUAL_STYLE.lighting.emissiveMultiplier;
        material.roughness = 0.82;
      } else if (material.name.includes('mat-dreams-photographic-shutters')) {
        material.color.set(0xb0b2ad);
        material.roughness = 0.93;
      } else if (material.name.includes('mat-dreams-tube-light')) {
        material.emissive.set(0xd9fff8);
        material.emissiveIntensity = 1.25 * VISUAL_STYLE.lighting.emissiveMultiplier;
        material.roughness = 0.24;
      } else if (material.name.includes('mat-dreams-lower-tube-light')) {
        material.emissive.set(0x96cbd0);
        material.emissiveIntensity = 0.72 * VISUAL_STYLE.lighting.emissiveMultiplier;
        material.roughness = 0.46;
      } else if (material.name.includes('mat-dreams-side-brick')) {
        material.color.set(0xc6a398);
        material.emissive.set(0x35120c);
        material.emissiveMap = material.map;
        material.emissiveIntensity = 0.1;
      } else if (material.name.includes('mat-dreams-handrail')) {
        material.color.set(0xb8c0bd);
        material.roughness = 0.4;
        material.metalness = 0.56;
      }
    }
  });
}

function applyGulliversModelPolicy(model: Group): void {
  // This is the geometry-approval asset. Preserve its deliberately simple
  // material-ID palette until the dedicated PBR texture pass is complete.
  model.traverse((child) => {
    if (!(child instanceof Mesh)) {
      return;
    }
    child.castShadow = true;
    child.receiveShadow = true;
    const materials = Array.isArray(child.material)
      ? child.material
      : [child.material];
    for (const material of materials) {
      if (!(material instanceof MeshStandardMaterial)) {
        continue;
      }
      material.roughness = Math.max(material.roughness, 0.58);
    }
  });
}

function applyMcr1ModelPolicy(model: Group): void {
  // MCR1 is intentionally still at geometry approval. Preserve the authored
  // clay material IDs and do not substitute runtime textures or emissive signs.
  model.traverse((child) => {
    if (!(child instanceof Mesh)) {
      return;
    }
    child.castShadow = true;
    child.receiveShadow = true;
    const materials = Array.isArray(child.material)
      ? child.material
      : [child.material];
    for (const material of materials) {
      if (!(material instanceof MeshStandardMaterial)) {
        continue;
      }
      material.emissive.set(0x000000);
      material.emissiveIntensity = 0;
      if (material.name.toLowerCase().includes('clay_glass')) {
        material.transparent = true;
        material.opacity = 0.34;
        material.depthWrite = false;
        material.roughness = 0.16;
      } else {
        material.roughness = Math.max(material.roughness, 0.55);
      }
    }
  });
}

function applyCassArtModelPolicy(model: Group): void {
  model.traverse((child) => {
    if (!(child instanceof Mesh)) {
      return;
    }
    child.castShadow = true;
    child.receiveShadow = true;
    const materials = Array.isArray(child.material)
      ? child.material
      : [child.material];
    for (const material of materials) {
      if (!(material instanceof MeshStandardMaterial)) {
        continue;
      }
      material.emissive.set(0x000000);
      material.emissiveIntensity = 0;
      if (material.name === 'MAT_CASS_LightFixture_PLACEHOLDER') {
        material.color.set(0xffe0a3);
        material.emissive.set(0xffc56c);
        material.emissiveIntensity = 2.2 * VISUAL_STYLE.lighting.emissiveMultiplier;
        material.roughness = 0.24;
      } else if (material.name === 'MAT_CASS_InteriorWall_PLACEHOLDER') {
        material.emissive.set(0x2c1a0d);
        material.emissiveIntensity = 0.16 * VISUAL_STYLE.lighting.emissiveMultiplier;
        material.roughness = Math.max(material.roughness, 0.68);
      } else if (material.name === 'MAT_CASS_Glass_PLACEHOLDER') {
        material.transparent = true;
        material.opacity = 0.20;
        material.depthWrite = false;
        material.roughness = 0.18;
        material.metalness = 0.05;
      } else {
        material.roughness = Math.max(material.roughness, 0.58);
      }
    }
  });
}

function applyReneeBlockoutPolicy(model: Group): void {
  // Renee is at the geometry approval gate. Preserve its authored material-ID
  // palette and prevent the clay blockout from inheriting emissive treatment.
  model.traverse((child) => {
    if (!(child instanceof Mesh)) {
      return;
    }
    child.castShadow = true;
    child.receiveShadow = true;
    const materials = Array.isArray(child.material)
      ? child.material
      : [child.material];
    for (const material of materials) {
      if (!(material instanceof MeshStandardMaterial)) {
        continue;
      }
      material.emissive.set(0x000000);
      material.emissiveIntensity = 0;
      if (material.name === 'MAT_REN_Glass_PLACEHOLDER') {
        material.transparent = true;
        material.opacity = 0.22;
        material.depthWrite = false;
        material.roughness = 0.28;
      } else {
        material.roughness = Math.max(material.roughness, 0.58);
      }
    }
  });
}

function applyTheHiveModelPolicy(model: Group): void {
  // The Hive is currently a geometry-only asset. Preserve its authored
  // material-region palette while configuring its layered transparent systems.
  model.traverse((child) => {
    if (!(child instanceof Mesh)) {
      return;
    }
    child.castShadow = true;
    child.receiveShadow = true;
    const materials = Array.isArray(child.material)
      ? child.material
      : [child.material];
    for (const material of materials) {
      if (!(material instanceof MeshStandardMaterial)) {
        continue;
      }
      material.map = null;
      material.emissiveMap = null;
      material.emissive.set(0x000000);
      material.emissiveIntensity = 0;
      const name = material.name.toLowerCase();
      if (name.includes('mat_glass_placeholder')) {
        material.transparent = true;
        material.opacity = 0.24;
        material.depthWrite = false;
        material.roughness = 0.2;
        material.metalness = 0.04;
      } else if (name.includes('mat_metalscreen_placeholder')) {
        material.transparent = true;
        material.opacity = 0.48;
        material.depthWrite = false;
        material.roughness = 0.46;
        material.metalness = 0.32;
      } else {
        material.roughness = Math.max(material.roughness, 0.58);
      }
    }
  });
}

function applyComeThroughLabModelPolicy(model: Group): void {
  // Come Through Lab is a geometry-only detail pass (no textures, decals or
  // QR code yet). Keep its authored placeholder palette and only configure
  // the glazing so the shopfront reads through the grilles.
  model.traverse((child) => {
    if (!(child instanceof Mesh)) {
      return;
    }
    child.castShadow = true;
    child.receiveShadow = true;
    const materials = Array.isArray(child.material)
      ? child.material
      : [child.material];
    for (const material of materials) {
      if (!(material instanceof MeshStandardMaterial)) {
        continue;
      }
      material.map = null;
      material.emissiveMap = null;
      material.emissive.set(0x000000);
      material.emissiveIntensity = 0;
      if (material.name.toLowerCase().includes('mat_ctl_glass_placeholder')) {
        material.transparent = true;
        material.opacity = 0.55;
        material.depthWrite = false;
        material.roughness = 0.25;
        material.metalness = 0.05;
      } else {
        material.roughness = Math.max(material.roughness, 0.55);
      }
    }
  });
}

function applyRealCameraModelPolicy(model: Group): void {
  // Real Camera authors its own sandstone/shopfront palette rather than clay
  // placeholders, so the colours are kept. Only the glazing and the interior
  // fluorescents need runtime treatment so the shop reads through the windows.
  model.traverse((child) => {
    if (!(child instanceof Mesh)) {
      return;
    }
    child.castShadow = true;
    child.receiveShadow = true;
    const materials = Array.isArray(child.material)
      ? child.material
      : [child.material];
    for (const material of materials) {
      if (!(material instanceof MeshStandardMaterial)) {
        continue;
      }
      material.emissive.set(0x000000);
      material.emissiveIntensity = 0;
      if (material.name === 'MAT_RC_Fluorescent') {
        material.color.set(0xf2f6ff);
        material.emissive.set(0xcfe2ff);
        material.emissiveIntensity = 2.1 * VISUAL_STYLE.lighting.emissiveMultiplier;
        material.roughness = 0.3;
      } else if (material.name === 'MAT_RC_ShopGlass') {
        // The shopfront glazing stays readable: the lit interior behind it is
        // the whole point of the display window.
        material.transparent = true;
        material.opacity = 0.26;
        material.depthWrite = false;
        material.roughness = 0.16;
        material.metalness = 0.05;
      } else if (material.name === 'MAT_RC_WindowGlass') {
        material.transparent = true;
        material.opacity = 0.42;
        material.depthWrite = false;
        material.roughness = 0.22;
        material.metalness = 0.05;
      } else if (material.name === 'MAT_RC_LensGlass') {
        material.roughness = 0.14;
        material.metalness = 0.35;
      } else {
        material.roughness = Math.max(material.roughness, 0.55);
      }
    }
  });
}

function applyCoralModelPolicy(model: Group): void {
  const brick = createWorldMaterial('brick-soot-overhaul', {
    repeatX: 2,
    repeatY: 2,
    tint: 0x8d6658,
    emissive: 0x080d18,
    emissiveIntensity: 0.045,
    roughness: 0.95,
  });
  brick.name = 'Coral runtime soot-stained brick';
  const concrete = createWorldMaterial('concrete-cracked-overhaul', {
    repeatX: 2,
    repeatY: 2,
    tint: 0x8f8b82,
    emissive: 0x0b111b,
    emissiveIntensity: 0.035,
    roughness: 0.94,
  });
  concrete.name = 'Coral runtime stained concrete';

  model.traverse((child) => {
    if (!(child instanceof Mesh)) {
      return;
    }
    child.castShadow = true;
    child.receiveShadow = true;
    const sourceMaterials = Array.isArray(child.material)
      ? child.material
      : [child.material];
    const runtimeMaterials = sourceMaterials.map((source) => {
      if (!(source instanceof MeshStandardMaterial)) {
        return source;
      }
      const name = source.name.toLowerCase();
      if (name.includes('upper_brick') || name.endsWith('brick')) {
        return brick;
      }
      if (
        name.includes('concrete') ||
        name.includes('repair_patch') ||
        name.includes('stair_material')
      ) {
        return concrete;
      }
      if (name.includes('store_glass') || name.includes('door_glass')) {
        source.color.set(0x8ab4c4);
        source.transparent = true;
        source.opacity = 0.43;
        source.depthWrite = false;
        source.roughness = 0.17;
        source.metalness = 0.06;
      } else if (name.includes('fluorescent')) {
        source.color.set(0xc7f4ff);
        source.emissive.set(0xa8eaff);
        source.emissiveIntensity = 2.2 * VISUAL_STYLE.lighting.emissiveMultiplier;
        source.roughness = 0.2;
      } else if (
        name.includes('lamp_glow') ||
        name.includes('upper_window_lit')
      ) {
        source.emissive.set(0xff7b1f);
        source.emissiveIntensity = 1.7 * VISUAL_STYLE.lighting.emissiveMultiplier;
      } else if (name.includes('terminal_glow')) {
        source.emissive.set(0x79d9ff);
        source.emissiveIntensity = 1.1 * VISUAL_STYLE.lighting.emissiveMultiplier;
      } else if (name.includes('sign_blue')) {
        source.color.set(0x0b3574);
        source.emissive.set(0x071b42);
        source.emissiveIntensity = 0.18 * VISUAL_STYLE.lighting.emissiveMultiplier;
        source.roughness = 0.62;
      } else if (name.includes('sign_letters')) {
        source.emissive.set(0xcfe8ff);
        source.emissiveIntensity = 0.36 * VISUAL_STYLE.lighting.emissiveMultiplier;
      } else if (name.includes('wet_road')) {
        return createWorldMaterial('asphalt-wet-overhaul', {
          repeatX: 4,
          repeatY: 3,
          roughness: 0.28,
          metalness: 0.08,
        });
      } else if (name.includes('wet_pavement')) {
        return createWorldMaterial('pavement-wet-overhaul', {
          repeatX: 4,
          repeatY: 2,
          roughness: 0.45,
        });
      }
      return source;
    });
    child.material = Array.isArray(child.material)
      ? runtimeMaterials
      : runtimeMaterials[0];
  });
}

async function replaceCoralFallback(
  root: Group,
  fallback: Mesh,
  location: WorldLocation,
): Promise<void> {
  try {
    const [shop, bin, streetlight, bollard] = await Promise.all([
      loadModel('assets/models/harperhey-coral-shop.glb'),
      loadModel('assets/models/harperhey-coral-bin.glb'),
      loadModel('assets/models/harperhey-coral-streetlight.glb'),
      loadModel('assets/models/harperhey-coral-bollard.glb'),
    ]);

    applyCoralModelPolicy(shop);
    applyCoralModelPolicy(bin);
    applyCoralModelPolicy(streetlight);
    applyCoralModelPolicy(bollard);

    shop.name = 'Harperhey Coral finished hero asset';
    shop.position.set(location.x, 0, location.z);
    // The Blender façade faces +Z after glTF axis conversion. Rotate it to the
    // east-facing west-side plot. Preserve the authored frontage and height;
    // only deepen the building to meet the existing west terrace rear line.
    shop.rotation.y = Math.PI / 2;
    shop.scale.set(1, 1, 1.42);
    root.add(shop);

    bin.name = 'Coral matching pavement bin';
    bin.position.set(location.x + 5.55, 0.04, location.z - 9.3);
    bin.rotation.y = Math.PI / 2;
    bin.scale.setScalar(0.9);
    root.add(bin);

    streetlight.name = 'Coral matching sodium streetlight';
    streetlight.position.set(location.x + 6.15, 0, location.z - 10.6);
    streetlight.rotation.y = Math.PI / 2;
    streetlight.scale.setScalar(0.82);
    root.add(streetlight);

    for (const [index, zOffset] of [-7.2, 8.8].entries()) {
      const placedBollard = index === 0 ? bollard : bollard.clone(true);
      placedBollard.name = `Coral matching pavement bollard ${index + 1}`;
      placedBollard.position.set(location.x + 5.7, 0, location.z + zOffset);
      placedBollard.scale.setScalar(0.92);
      root.add(placedBollard);
    }

    const coolShopLight = new PointLight(
      VISUAL_STYLE.lighting.coldWhite,
      2.25 * VISUAL_STYLE.lighting.emissiveMultiplier,
      10,
      2,
    );
    coolShopLight.name = 'Coral cool shopfront spill';
    coolShopLight.position.set(location.x + 6.1, 2.55, location.z - 5.5);
    root.add(coolShopLight);

    const coolShopLightSouth = coolShopLight.clone();
    coolShopLightSouth.name = 'Coral cool shopfront spill south';
    coolShopLightSouth.intensity *= 0.82;
    coolShopLightSouth.position.z = location.z + 5.5;
    root.add(coolShopLightSouth);

    root.remove(fallback);
  } catch (error) {
    markLoadFailure(fallback, 'Coral');
    console.error(
      '[World] Failed to load the Coral hero asset set. Showing the magenta fallback.',
      error,
    );
  }
}

async function replaceFloristFallback(
  root: Group,
  fallback: Mesh,
  location: WorldLocation,
): Promise<void> {
  try {
    const florist = await loadModel(
      'assets/models/nice-things-blockout.glb?v=geometry-approved-20260911',
    );
    applyNiceThingsBlockoutPolicy(florist);
    florist.name = 'Nice Things geometry blockout';
    // The authored asset includes Central Buildings to the left, while the
    // canonical florist location remains centred on the 5.9 m shopfront.
    florist.position.set(location.x - 2.8, 0, location.z);
    root.add(florist);
    root.remove(fallback);
  } catch (error) {
    markLoadFailure(fallback, 'Florist');
    console.error(
      '[World] Failed to load nice-things-blockout.glb. Showing the magenta fallback.',
      error,
    );
  }
}

async function replaceDreamsFallback(
  root: Group,
  fallback: Group,
  location: WorldLocation,
): Promise<void> {
  fallback.visible = false;
  try {
    const dreams = await loadModel(
      'assets/models/harperhey-dreams-greybox.glb?v=geometry-approved-20260911',
    );
    applyDreamsModelPolicy(dreams);
    dreams.name = 'Harperhey Dreams geometry-first hero asset';
    dreams.position.set(location.x, 0, location.z);
    dreams.rotation.y = location.front === 'north' ? Math.PI : 0;
    root.add(dreams);
    root.remove(fallback);
  } catch (error) {
    fallback.visible = true;
    fallback.name = 'Dreams procedural fallback after GLB load error';
    console.error(
      '[World] Failed to load harperhey-dreams-greybox.glb. Showing the procedural fallback.',
      error,
    );
  }
}

async function addGulliversModel(
  root: Group,
  location: WorldLocation,
): Promise<void> {
  try {
    const gullivers = await loadModel(
      'assets/models/harperhey-gullivers.glb?v=geometry-wip-20260911',
    );
    applyGulliversModelPolicy(gullivers);
    gullivers.name = 'Gullivers geometry WIP — textures pending';
    gullivers.position.set(location.x, 0, location.z);
    // Blender front (-Y) imports facing +Z, aligning the Oldham Street
    // frontage south beside Renee while retaining the full side return.
    root.add(gullivers);
  } catch (error) {
    console.error(
      '[World] Failed to load harperhey-gullivers.glb. No legacy fallback is retained.',
      error,
    );
  }
}

async function addMcr1Model(
  root: Group,
  location: WorldLocation,
): Promise<void> {
  try {
    const mcr1 = await loadModel(
      'assets/models/harperhey-mcr1-geometry.glb?v=geometry-wip-20260911',
    );
    applyMcr1ModelPolicy(mcr1);
    mcr1.name = 'MCR1 geometry WIP — textures pending';
    // The Blender asset uses the real corner as its modelling origin rather
    // than the plot centre. This offset centres its 11.7 m envelope immediately
    // west of the Florist while keeping the main frontage south-facing.
    mcr1.position.set(location.x - 1.45, 0, location.z);
    root.add(mcr1);
  } catch (error) {
    console.error(
      '[World] Failed to load harperhey-mcr1-geometry.glb. No legacy M1 fallback is retained.',
      error,
    );
  }
}

async function replaceCassArtFallback(
  root: Group,
  fallback: Mesh,
  location: WorldLocation,
): Promise<void> {
  try {
    const cassArt = await loadModel(
      'assets/models/cass_art.glb?v=geometry-wip-20260911',
    );
    applyCassArtModelPolicy(cassArt);
    cassArt.name = 'Cass Art geometry WIP — textures pending';
    const scale = location.width / 18;
    // Blender -Y imports as Three.js +Z. Rotate the facade north and align its
    // authored front plane with the north edge of the former Real Camera plot.
    cassArt.position.set(location.x, 0, location.z - location.depth / 2);
    cassArt.rotation.y = Math.PI;
    cassArt.scale.setScalar(scale);
    root.add(cassArt);
    root.remove(fallback);
  } catch (error) {
    markLoadFailure(fallback, 'Cass Art');
    console.error(
      '[World] Failed to load cass_art.glb. Showing the magenta fallback.',
      error,
    );
  }
}

async function replaceReneeFallback(
  root: Group,
  fallback: Mesh,
  location: WorldLocation,
): Promise<void> {
  try {
    const renee = await loadModel(
      'assets/models/renee-blockout.glb?v=geometry-wip-20260911',
    );
    applyReneeBlockoutPolicy(renee);
    renee.name = 'Renee geometry blockout — textures pending';
    // Blender -Y becomes Three.js +Z, matching this south-facing plot. The
    // plot centre is shifted north so the deeper model keeps the old frontage.
    renee.position.set(location.x, 0, location.z);
    root.add(renee);
    root.remove(fallback);
  } catch (error) {
    markLoadFailure(fallback, 'Renee');
    console.error(
      '[World] Failed to load renee-blockout.glb. Showing the magenta fallback.',
      error,
    );
  }
}

async function addTheHiveModel(
  root: Group,
  location: WorldLocation,
): Promise<void> {
  try {
    const hive = await loadModel(
      'assets/models/the_hive.glb?v=geometry-20260911',
    );
    applyTheHiveModelPolicy(hive);
    hive.name = 'The Hive / Arts Council geometry asset';
    // Blender's -Y frontage imports facing +Z. Rotate that frontage west and
    // centre the authored metric envelope on the canonical Arts Council plot.
    hive.rotation.y = -Math.PI / 2;
    hive.updateMatrixWorld(true);
    const bounds = new Box3().setFromObject(hive);
    const centre = bounds.getCenter(new Vector3());
    hive.position.x += location.x - centre.x;
    hive.position.y -= bounds.min.y;
    hive.position.z += location.z - centre.z;
    root.add(hive);
  } catch (error) {
    console.error(
      '[World] Failed to load the_hive.glb. No legacy Arts Council blockout is retained.',
      error,
    );
  }
}

async function addComeThroughLabModel(
  root: Group,
  location: WorldLocation,
): Promise<void> {
  try {
    const [lab, dropbox, props] = await Promise.all([
      loadModel('assets/models/come_through_lab.glb?v=geometry-20260912'),
      loadModel('assets/models/ctl_dropbox.glb?v=geometry-20260912'),
      loadModel('assets/models/ctl_dropoff_props.glb?v=geometry-20260912'),
    ]);
    applyComeThroughLabModelPolicy(lab);
    applyComeThroughLabModelPolicy(dropbox);
    applyComeThroughLabModelPolicy(props);
    lab.name = 'Come Through Lab geometry asset — textures pending';
    dropbox.name = 'Come Through Lab drop box (independent hero prop)';
    props.name = 'Come Through Lab supply holder + envelope + pencil';
    // Blender's -Y frontage imports facing +Z. Rotate that frontage east, then
    // sit the authored metric envelope on the plot with its shopfront flush to
    // the plot's east edge so the door and drop-box wall meet the pavement.
    // `width` is the east-west extent, matching addCollisionFootprint.
    lab.rotation.y = Math.PI / 2;
    lab.updateMatrixWorld(true);
    const bounds = new Box3().setFromObject(lab);
    const centre = bounds.getCenter(new Vector3());
    lab.position.x += location.x + location.width / 2 - bounds.max.x;
    lab.position.y -= bounds.min.y;
    lab.position.z += location.z - centre.z;
    root.add(lab);

    // The drop box and supply holder were authored in the same Blender scene
    // as the building and exported separately only so they stay independently
    // placeable (never fused into the building mesh, per the brief's 24-hour
    // drop-off requirement). Applying the identical rotation + position delta
    // keeps them exactly where they were authored relative to the entrance.
    for (const prop of [dropbox, props]) {
      prop.rotation.y = Math.PI / 2;
      prop.position.copy(lab.position);
      root.add(prop);
    }
  } catch (error) {
    console.error(
      '[World] Failed to load the Come Through Lab hero asset set (building, drop box, supply holder).',
      error,
    );
  }
}

async function replaceVillageBooksFallback(
  root: Group,
  fallback: Mesh,
  location: WorldLocation,
): Promise<void> {
  try {
    const villageBooks = await loadModel(
      'assets/models/village-books-blockout.glb?v=geometry-wip-20260912',
    );
    applyVillageBooksBlockoutPolicy(villageBooks);
    villageBooks.name = 'Village Books geometry blockout — detail pass pending';
    // Blender's -Y Oldham Street frontage imports facing +Z. Rotate it east,
    // then align the measured fascia projection to the canonical X = -34
    // building line and centre its north-south envelope on the plot.
    villageBooks.rotation.y = Math.PI / 2;
    villageBooks.updateMatrixWorld(true);
    const bounds = new Box3().setFromObject(villageBooks);
    const centre = bounds.getCenter(new Vector3());
    villageBooks.position.x += location.x + location.width / 2 - bounds.max.x;
    villageBooks.position.y -= bounds.min.y;
    villageBooks.position.z += location.z - centre.z;
    root.add(villageBooks);
    root.remove(fallback);
  } catch (error) {
    markLoadFailure(fallback, 'Village Books');
    console.error(
      '[World] Failed to load village-books-blockout.glb. Showing the magenta fallback.',
      error,
    );
  }
}

async function addRealCameraModel(
  root: Group,
  location: WorldLocation,
): Promise<void> {
  try {
    const realCamera = await loadModel(
      'assets/models/real_camera.glb?v=geometry-20260912',
    );
    applyRealCameraModelPolicy(realCamera);
    realCamera.name = 'Real Camera geometry asset — textures pending';
    // Blender's -Y Dale Street frontage imports facing +Z. Rotate it to face
    // north, then sit the authored metric envelope on the plot with the
    // shopfront flush to the plot's north edge so it meets the pavement.
    realCamera.rotation.y = Math.PI;
    realCamera.updateMatrixWorld(true);
    const bounds = new Box3().setFromObject(realCamera);
    const centre = bounds.getCenter(new Vector3());
    realCamera.position.x += location.x - centre.x;
    realCamera.position.y -= bounds.min.y;
    realCamera.position.z += location.z - location.depth / 2 - bounds.min.z;
    root.add(realCamera);
  } catch (error) {
    console.error(
      '[World] Failed to load real_camera.glb. No legacy Real Camera blockout is retained.',
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
    : location.id === 'arts-council'
      ? 'concrete-cracked-overhaul'
      : 'brick-soot-overhaul';
  const frontTint = location.id === 'dreams'
    ? 0x8c3349
    : location.id === 'renae'
      ? 0x7c2847
      : 0xffffff;
  const frontEmissive = location.id === 'renae'
    ? VISUAL_STYLE.lighting.magenta
    : ['coral', 'arts-council'].includes(location.id)
      ? VISUAL_STYLE.lighting.coldWhite
      : VISUAL_STYLE.lighting.sodium;
  const frontMaterial = createWorldMaterial(frontTexture, {
    repeatX: Math.max(2, Math.round(location.width / 4)),
    repeatY: Math.max(2, Math.round(location.height / 2)),
    tint: frontTint,
    emissive: frontEmissive,
    emissiveIntensity: ['renae', 'coral'].includes(location.id)
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
  const isWarm = ['dreams', 'renae', 'vinyl-exchange'].includes(location.id);
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
    coral: ['#183b74', '#eee6d5', VISUAL_STYLE.lighting.coldWhite],
    'eastern-bloc': ['#856b31', '#10151c', VISUAL_STYLE.lighting.sodium],
    'vinyl-exchange': ['#d3c6a0', '#a12f28', VISUAL_STYLE.lighting.sodium],
    'real-camera': ['#ddd1ae', '#8c2a22', VISUAL_STYLE.lighting.sodium],
    'spice-cabin': ['#8d2d29', '#f0d28c', VISUAL_STYLE.lighting.sodium],
    'off-licence': ['#302a25', '#ead7ac', VISUAL_STYLE.lighting.sodium],
    'advanced-photo': ['#d4cbb2', '#20384b', VISUAL_STYLE.lighting.coldWhite],
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
    ['dreams', 'renae', 'arts-council'].includes(location.id) ? 0.24 : 0.11,
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
  if (['dreams', 'eastern-bloc', 'arts-council'].includes(location.id)) {
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
    const fallback = createDreamsBuilding(location);
    fallback.rotation.y = location.front === 'north' ? Math.PI : 0;
    root.add(fallback);
    void replaceDreamsFallback(root, fallback, location);
    addCollisionFootprint(obstacles, location);
    return;
  }

  if (location.id === 'gullivers') {
    void addGulliversModel(root, location);
    addCollisionFootprint(obstacles, location);
    addDevelopmentLabel(
      root,
      `${location.name} · geometry WIP · textures pending`,
      location.x,
      location.height + 1.1,
      location.z,
    );
    return;
  }

  if (location.id === 'mcr1') {
    void addMcr1Model(root, location);
    addCollisionFootprint(obstacles, location);
    addDevelopmentLabel(
      root,
      `${location.name} · geometry WIP · textures pending`,
      location.x,
      location.height + 1.1,
      location.z,
    );
    return;
  }

  if (location.id === 'renae') {
    const fallback = createBlockoutBuildingMass(location);
    fallback.position.set(location.x, location.height / 2, location.z);
    fallback.name = 'Renee loading placeholder';
    root.add(fallback);
    void replaceReneeFallback(root, fallback, location);
    addReneeInteriorCollision(obstacles, location);
    addDevelopmentLabel(
      root,
      `${location.name} · geometry WIP · textures pending`,
      location.x,
      location.height + 1.1,
      location.z,
    );
    return;
  }

  if (location.id === 'village-books') {
    const fallback = createBlockoutBuildingMass(location);
    fallback.position.set(location.x, location.height / 2, location.z);
    fallback.name = 'Village Books loading placeholder';
    root.add(fallback);
    void replaceVillageBooksFallback(root, fallback, location);
    // The blockout includes a visible closed door but no door animation or
    // interaction system yet, so retain a solid measured collision footprint.
    addCollisionFootprint(obstacles, location);
    addDevelopmentLabel(
      root,
      `${location.name} · geometry blockout · detail pass pending`,
      location.x,
      location.height + 1.1,
      location.z,
    );
    return;
  }

  if (location.id === 'come-through-lab') {
    void addComeThroughLabModel(root, location);
    addCollisionFootprint(obstacles, location);
    addDevelopmentLabel(
      root,
      `${location.name} · geometry complete · textures pending`,
      location.x,
      location.height + 1.1,
      location.z,
    );
    return;
  }

  if (location.id === 'real-camera') {
    void addRealCameraModel(root, location);
    // Solid footprint rather than an interior shell: the authored shop floor
    // sits 0.82 m up a stair flight, and the player is pinned to y = 0 with
    // XZ-only collision, so the interior cannot be entered without vertical
    // support. The GLB already ships the entry/spawn anchors for when it can.
    addCollisionFootprint(obstacles, location);
    addDevelopmentLabel(
      root,
      `${location.name} · geometry WIP · textures pending`,
      location.x,
      location.height + 1.1,
      location.z,
    );
    return;
  }

  if (location.id === 'arts-council') {
    void addTheHiveModel(root, location);
    addCollisionFootprint(obstacles, location);
    addDevelopmentLabel(
      root,
      `${location.name} · geometry complete · textures pending`,
      location.x,
      location.height + 1.1,
      location.z,
    );
    return;
  }

  if (location.id === 'cass-art') {
    const fallback = createBlockoutBuildingMass(location);
    fallback.position.set(location.x, location.height / 2, location.z);
    fallback.name = 'Cass Art loading placeholder';
    root.add(fallback);
    void replaceCassArtFallback(root, fallback, location);
    addCassArtInteriorCollision(obstacles, location);
    addDevelopmentLabel(
      root,
      `${location.name} · geometry WIP · textures pending`,
      location.x,
      location.height + 1.1,
      location.z,
    );
    return;
  }

  const building =
    location.status === 'finished'
      ? createBox(
          location.width,
          location.height,
          location.depth,
          location.color ?? 0x555555,
        )
      : createBlockoutBuildingMass(location);
  building.position.set(location.x, location.height / 2, location.z);
  building.name =
    location.status === 'finished'
      ? `${location.name} loading placeholder`
      : `${location.name} blockout`;
  root.add(building);
  if (location.id === 'coral') {
    addCoralInteriorCollision(obstacles, location);
  } else {
    addCollisionFootprint(obstacles, location);
  }

  if (location.id === 'florist') {
    void replaceFloristFallback(root, building, location);
  } else if (location.id === 'coral') {
    void replaceCoralFallback(root, building, location);
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
  shelter.scale.setScalar(BUS_SHELTER_SCALE);
  return shelter;
}

function markShelterLoadFailure(fallback: Group, assetName = 'Bus shelter'): void {
  fallback.name = `${assetName} load error`;
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
      'assets/models/bus-shelter/preston-busstop-reference.glb?v=geometry-pass-20260911',
    );
    applyBusShelterGeometryPolicy(shelter);
    shelter.name = fallback.name.replace(' loading placeholder', '');
    shelter.position.copy(fallback.position);
    shelter.rotation.copy(fallback.rotation);
    root.add(shelter);
    root.remove(fallback);
  } catch (error) {
    markShelterLoadFailure(fallback);
    console.error(
      '[World] Failed to load the Preston bus-stop geometry asset. Showing the magenta fallback.',
      error,
    );
  }
}

function applyGreekGyrosPolicy(model: Group): void {
  // The kiosk is a geometry-only asset: keep its authored placeholder palette
  // and let the glass screen read as glass without inheriting emissive light.
  model.traverse((child) => {
    if (!(child instanceof Mesh)) {
      return;
    }
    child.castShadow = true;
    child.receiveShadow = true;
    const materials = Array.isArray(child.material)
      ? child.material
      : [child.material];
    for (const material of materials) {
      if (!(material instanceof MeshStandardMaterial)) {
        continue;
      }
      material.map = null;
      material.emissiveMap = null;
      material.emissive.set(0x000000);
      material.emissiveIntensity = 0;
      if (material.name === 'MAT_GG_Glass_PLACEHOLDER') {
        material.transparent = true;
        material.opacity = 0.22;
        material.depthWrite = false;
        material.roughness = 0.14;
      } else {
        material.roughness = Math.max(material.roughness, 0.42);
      }
    }
  });
}

function createGreekGyrosFallback(): Group {
  const stand = new Group();
  stand.name = 'Greek Gyros loading placeholder';
  const body = new MeshStandardMaterial({ color: 0x6a7076, roughness: 0.85 });
  const fascia = new MeshStandardMaterial({ color: 0x21386d, roughness: 0.6 });

  const shell = new Mesh(getBoxGeometry(6.4, 2.16, 2.6), body);
  shell.position.set(0, 1.34, 0);
  stand.add(shell);
  const counter = new Mesh(getBoxGeometry(6.36, 0.06, 0.62), body);
  counter.position.set(0, 1.25, 1.15);
  stand.add(counter);
  const sign = new Mesh(getBoxGeometry(6.72, 0.94, 0.38), fascia);
  sign.position.set(0, 2.85, 1.49);
  stand.add(sign);
  return stand;
}

async function replaceGreekGyrosFallback(
  root: Group,
  fallback: Group,
): Promise<void> {
  try {
    const stand = await loadModel(
      'assets/models/greek_gyros.glb?v=geometry-pass-20260912',
    );
    applyGreekGyrosPolicy(stand);
    stand.name = fallback.name.replace(' loading placeholder', '');
    stand.position.copy(fallback.position);
    stand.rotation.copy(fallback.rotation);
    root.add(stand);
    root.remove(fallback);
  } catch (error) {
    markShelterLoadFailure(fallback, 'Greek Gyros');
    console.error(
      '[World] Failed to load greek_gyros.glb. Showing the magenta fallback.',
      error,
    );
  }
}

function addGreekGyros(
  root: Group,
  obstacles: CollisionObstacle[],
  marker: WorldMarker,
): void {
  const fallback = createGreekGyrosFallback();
  fallback.name = `${marker.name} loading placeholder`;
  fallback.position.set(marker.x, 0, marker.z);
  root.add(fallback);
  void replaceGreekGyrosFallback(root, fallback);

  obstacles.push({
    name: marker.name,
    minX: marker.x - 3.2,
    // The side service step projects 0.56 m past the east wall; enclosing it
    // keeps the player from clipping through the step rather than over it.
    maxX: marker.x + 3.76,
    minZ: marker.z - 1.3,
    // The authored frontage faces +Z: stop the player at the counter lip and
    // leave the projecting canopy overhead clear.
    maxZ: marker.z + 1.5,
  });
  addDevelopmentLabel(root, marker.name, marker.x, 4.1, marker.z);
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
    minX: marker.x - 2.55 * BUS_SHELTER_SCALE,
    maxX: marker.x + 2.55 * BUS_SHELTER_SCALE,
    minZ: marker.z - 0.9 * BUS_SHELTER_SCALE,
    // Both shelters face toward +Z after their -90° world rotation. Include
    // the independently modelled trolley now positioned in front of the rail.
    maxZ: marker.z + 1.85,
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

  addParkEdgeEnvironmentKit(root);

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
  road('Outer South Road', 0, 59.5, 114, ROAD_WIDTH);
  road('Outer west street', -48, 0, ROAD_WIDTH, 96);
  road('Outer east street', 57, 0, ROAD_WIDTH, 96);
  road('North Road outward connection', 0, -55, ROAD_WIDTH, 16);
  road('South Road outward connection', 0, 69.625, ROAD_WIDTH, 12.75);
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
  pavement('South Road shop frontage pavement', 0, 54.875, 72, 1.75, true);
  pavement('South Road opposite pavement', 18.5, 64, 75, 1.5, true);

  const dreamsKerbMarkingMaterial = new MeshStandardMaterial({
    color: 0xb58a18,
    emissive: 0x2e1c02,
    emissiveIntensity: 0.12,
    roughness: 0.86,
  });
  for (const z of [29.02, 28.76]) {
    const line = createBox(18, 0.025, 0.08, dreamsKerbMarkingMaterial);
    line.name = 'Dreams worn double yellow kerb marking';
    line.position.set(-3, 0.028, z);
    root.add(line);
  }
  addCrossing(root, 'South park crossing', 0, 25.5);
  addCrossing(root, 'West park crossing', -29.5, 0, Math.PI / 2);
  addCrossing(root, 'East park crossing', 29.5, 0, Math.PI / 2);

  addRoadAnnotation(root, 'N-025.5', -9, -25.5);
  addRoadAnnotation(root, 'X 29.5', 29.5, 8, Math.PI / 2);
  addRoadAnnotation(root, 'Z +59.5', 17, 59.5);
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
  addHeroStreetEnvironmentKit(root);
  addShoppingTrolley(root, 31.9, 20.9, -0.74);
  addShoppingTrolley(root, -7.1, -30.1, 0.22);
  addUtilityBox(root, -34.7, -11.7, Math.PI / 2);
  addUtilityBox(root, 34.5, 6.4, -Math.PI / 2);
  addUtilityBox(root, 25.6, 31.2, Math.PI);
  addUtilityBox(root, 8.15, -30.25, Math.PI);

  addReflectionPatch(root, 'Bus shelter magenta spill', -8.2, 22.2, 1.1, 4.8, VISUAL_STYLE.lighting.magenta, 0.3, -0.12);
  addReflectionPatch(root, 'Bus shelter green spill', -10.2, 21.4, 0.8, 3.1, VISUAL_STYLE.lighting.fluorescent, 0.2, 0.15);
  addReflectionPatch(root, 'Dreams cool fascia spill', -2.8, 25.6, 2.65, 5.8, VISUAL_STYLE.lighting.coldWhite, 0.36, -0.03);
  addReflectionPatch(root, 'Dreams broken secondary spill', -6.1, 26.5, 1.75, 4.3, 0x8fd8e6, 0.22, 0.07);
  addReflectionPatch(root, 'Dreams broken east spill', 0.7, 26, 1.85, 4.8, 0xb9e2e8, 0.2, -0.08);
  addReflectionPatch(root, 'Dreams broad rough road wash', -2.6, 25.8, 8.2, 4.2, 0xaedbe2, 0.11, -0.02);
  addReflectionPatch(root, 'Renee fascia spill', 16.5, -25.8, 1.2, 4.4, VISUAL_STYLE.lighting.magenta, 0.2, -0.1);
  addReflectionPatch(root, 'Coral central fascia spill', -30.1, 17, 5.2, 1.05, VISUAL_STYLE.lighting.coldWhite, 0.17, 0.03);
  addReflectionPatch(root, 'Coral north fascia spill', -30.4, 10.2, 4.5, 0.82, 0x9edff2, 0.13, -0.05);
  addReflectionPatch(root, 'Coral south fascia spill', -30.4, 23.8, 4.5, 0.82, 0x9edff2, 0.13, 0.05);
  addReflectionPatch(root, 'Arts Council fascia spill', 34, 20, 5.8, 0.82, VISUAL_STYLE.lighting.sodium, 0.17, 0.08);
  addReflectionPatch(root, 'Vinyl Exchange fascia spill', -7, 57.6, 4.7, 0.75, VISUAL_STYLE.lighting.sodium, 0.2, 0.04);
  addReflectionPatch(root, 'Spice Cabin fascia spill', 10.8, 57.2, 0.82, 4.2, VISUAL_STYLE.lighting.magenta, 0.18, -0.08);
  addReflectionPatch(root, 'Off-Licence fascia spill', 22.5, 57.2, 0.82, 4.2, VISUAL_STYLE.lighting.sodium, 0.16, 0.06);
  addReflectionPatch(root, 'Advanced Photo fascia spill', 10.5, 62, 3.8, 0.7, VISUAL_STYLE.lighting.coldWhite, 0.16, -0.04);
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
  pickup.userData.developmentOverlay = true;
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
  pool.userData.developmentOverlay = true;
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
  type HeroLightDefinition = readonly [
    name: string,
    x: number,
    y: number,
    z: number,
    color: number,
    intensity: number,
    distance: number,
  ];

  const definitions: HeroLightDefinition[] = [
    ['Bus Stop A hero light', 0, 2.35, 20.4, 0xb9ffe7, 8, 8],
    ['Dreams hero light', -3, 4.5, 33.2, VISUAL_STYLE.lighting.coldWhite, 1.8, 10],
    ['Renee hero light', 17, 2.5, -30.8, VISUAL_STYLE.lighting.magenta, 7, 9],
    ['Florist hero light', -16.9, 2.7, -27, VISUAL_STYLE.lighting.sodium, 7.5, 9],
    ['Bus Stop B hero light', 0, 2.35, -49, 0xb9ffe7, 8, 8],
  ];

  const cassArt = WORLD_LOCATIONS.find((location) => location.id === 'cass-art');
  if (cassArt) {
    const scale = cassArt.width / 18;
    const modelOriginZ = cassArt.z - cassArt.depth / 2;
    const cassLightDefinitions = [
      ['Cass Art window fill', 0, 0.65, 3.68, 7, 7],
      ['Cass Art interior track west', -2.1, 5.75, 4.02, 9, 8],
      ['Cass Art interior track east', 1.9, 5.75, 4.02, 9, 8],
    ] as const;

    // The model is rotated 180 degrees at runtime: authored +X becomes world
    // -X, while authored interior depth (+Y) extends south in world +Z.
    for (const [name, localX, localDepth, localHeight, intensity, distance] of cassLightDefinitions) {
      definitions.push([
        name,
        cassArt.x - localX * scale,
        localHeight * scale,
        modelOriginZ + localDepth * scale,
        0xffcf91,
        intensity,
        distance,
      ]);
    }
  }

  const comeThroughLab = WORLD_LOCATIONS.find(
    (location) => location.id === 'come-through-lab',
  );
  if (comeThroughLab) {
    // The plot now carries the authored parapet top (7.15 m = ground 3.50 +
    // upper 3.40 + cap 0.25); sit the pair just under the cap and slightly
    // proud of the frontage so the wash reaches both upper corners instead of
    // only the flat wall. `width` is the east-west extent.
    const parapetTop = comeThroughLab.height;
    const frontPlaneX = comeThroughLab.x + comeThroughLab.width / 2;
    for (const [suffix, offsetZ] of [
      ['north', -4.6],
      ['south', 4.6],
    ] as const) {
      definitions.push([
        `Come Through Lab parapet corner ${suffix}`,
        frontPlaneX + 0.4,
        parapetTop - 0.25,
        comeThroughLab.z + offsetZ,
        VISUAL_STYLE.lighting.coldWhite,
        3.2,
        7,
      ]);
    }
  }

  const realCamera = WORLD_LOCATIONS.find(
    (location) => location.id === 'real-camera',
  );
  if (realCamera) {
    // The model is rotated 180 degrees and its frontage aligned to the plot's
    // north edge, so an authored Blender point (bx, by, bz) lands at
    // world x = -bx + (plot x - 0.275), y = bz, z = by + (front plane + 5.963).
    const worldX = (authoredX: number) => realCamera.x - 0.275 - authoredX;
    const worldZ = (authoredY: number) =>
      realCamera.z - realCamera.depth / 2 + 5.963 + authoredY;
    const realCameraLights = [
      // Sodium wash on the hero shopfront, sitting proud of the facade so the
      // awning, hanging sign and stone piers catch it rather than one flat wall.
      ['Real Camera shopfront', 0.05, -6.4, 3.7, VISUAL_STYLE.lighting.sodium, 7, 10],
      // Interior fluorescents read through the display glazing after dark.
      ['Real Camera interior west', -4.55, -1.55, 3.3, VISUAL_STYLE.lighting.fluorescent, 5, 7],
      ['Real Camera interior east', -0.2, -1.55, 3.3, VISUAL_STYLE.lighting.fluorescent, 5, 7],
    ] as const;

    for (const [name, authoredX, authoredY, height, color, intensity, distance] of realCameraLights) {
      definitions.push([
        name,
        worldX(authoredX),
        height,
        worldZ(authoredY),
        color,
        intensity,
        distance,
      ]);
    }
  }

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
    8,
    128,
    140,
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
  for (const marker of FOOD_STANDS) {
    addGreekGyros(root, obstacles, marker);
  }
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
    [-9.6, -20.5, VISUAL_STYLE.lighting.sodium],
    [12, -29, VISUAL_STYLE.lighting.magenta],
    [-12, 29, VISUAL_STYLE.lighting.sodium],
    [12, 29, VISUAL_STYLE.lighting.sodium],
    [-34, 7, VISUAL_STYLE.lighting.sodium],
    [34, 17, VISUAL_STYLE.lighting.coldWhite],
    [-15, 55, VISUAL_STYLE.lighting.sodium],
    [1, 55, VISUAL_STYLE.lighting.sodium],
    [16.5, 55, VISUAL_STYLE.lighting.magenta],
    [29, 55, VISUAL_STYLE.lighting.sodium],
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
