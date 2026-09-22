import {
  Box3,
  BoxGeometry,
  CanvasTexture,
  CircleGeometry,
  CylinderGeometry,
  DirectionalLight,
  Group,
  HemisphereLight,
  type Material,
  Matrix4,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  Object3D,
  OctahedronGeometry,
  PointLight,
  Scene,
  SphereGeometry,
  Sprite,
  SpriteMaterial,
  SRGBColorSpace,
  TorusGeometry,
  Vector3,
} from 'three';
import { BufferGeometry } from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import {
  createNightAtmosphere,
  type NightAtmosphere,
} from '../rendering/createNightAtmosphere';
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
import {
  circleObstacle,
  orientedBoxObstacle,
  type CollisionObstacle,
  type CollisionWorld,
} from './collision';
import { createCollisionDebugOutlines } from './collisionDebug';
import { addSpecterGraffiti } from './createSpecterGraffiti';
import {
  addBougainvilleaFenceCollision,
  addBougainvilleaFenceScene,
  addBougainvilleaSignLamp,
} from './bougainvilleaFence';
import { loadModel } from './loadModel';
import { profileAuthoredMaps } from './buildingMaterials';
import {
  addStreetlightFixtures,
  createStreetlightFixture,
  STREETLIGHT_MODELS,
  streetlightEmitterWorld,
  type StreetlightModel,
} from './createStreetlights';
import { LocalLightRegistry } from './localLighting';
import { mergeStaticModelMeshes } from './mergeStaticModelMeshes';
import { SterlingBike } from '../vehicles/SterlingBike';
import { SterlingFleet } from '../vehicles/SterlingFleet';
import {
  applyBusShelterTexturePolicy,
  applyPalletTexturePolicy,
  applySpiceCabinTexturePolicy,
} from './busShelterMaterials';
import { createDreamsBuilding } from './createDreamsBuilding';
import {
  addHeroStreetEnvironmentKit,
  addParkEdgeEnvironmentKit,
  addRoadIronwork,
  HERO_STREET_DRAIN_COVERS,
} from './createEnvironmentKit';
import { addParkGround } from './createParkSurfaces';
import { addPavementSurfaces, pavementTopAt, type PavementSpan } from './createPavementSurfaces';
import { addRoadSurfaces, type RoadCrossing, type RoadSpan } from './createRoadSurfaces';
import {
  BUS_STOPS,
  FOOD_STANDS,
  FUTURE_EXITS,
  PALLET_STACKS,
  PARK,
  PAVEMENT_WIDTH,
  ROAD_WIDTH,
  SPECTER_GRAFFITI,
  STERLING_BIKE_DOCKS,
  WORLD_BOUNDS,
  ABC_BUILDING_CORNER,
  WORLD_LOCATIONS,
  type FoodStandMarker,
  type PalletStackMarker,
  type SterlingStationMarker,
  type WorldLocation,
  type WorldMarker,
} from './worldLayout';

export interface World {
  readonly root: Group;
  readonly collision: CollisionWorld;
  readonly sterlingFleet: SterlingFleet;
  readonly atmosphere: NightAtmosphere;
  readonly update: (deltaTime: number, playerPosition: Vector3) => void;
  readonly getLightingStats: () => LightingStats;
  readonly setDevelopmentOverlaysVisible: (visible: boolean) => void;
}

export interface LightingStats {
  readonly activePointLights: number;
  readonly activeSpotLights: number;
  readonly registeredPointLights: number;
  readonly activePointLightNames: readonly string[];
  readonly activeLocalLightGroups: readonly string[];
  readonly maximumActiveLocalLights: number;
}

const boxGeometryCache = new Map<string, BoxGeometry>();
const cylinderGeometryCache = new Map<string, CylinderGeometry>();
const circleGeometryCache = new Map<string, CircleGeometry>();
const standardColorMaterialCache = new Map<number, MeshStandardMaterial>();
const BUS_SHELTER_SCALE = 1.3;

function createManagedPointLight(
  name: string,
  x: number,
  y: number,
  z: number,
  color: number,
  intensity: number,
  distance: number,
): PointLight {
  const light = new PointLight(color, intensity, distance, 2);
  light.name = name;
  light.position.set(x, y, z);
  return light;
}

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

function getStandardColorMaterial(color: number): MeshStandardMaterial {
  let material = standardColorMaterialCache.get(color);
  if (!material) {
    material = new MeshStandardMaterial({ color, roughness: 1 });
    standardColorMaterialCache.set(color, material);
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

function addAdvancedPhotoInteriorCollision(
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
      name: `Advanced Photo ${name}`,
      minX: location.x + minX,
      maxX: location.x + maxX,
      minZ: location.z + minZ,
      maxZ: location.z + maxZ,
      height: location.height,
    });
  };

  // Blender -Y imports as local +Z and the model is rotated 180 degrees to
  // face north. Authored +X therefore becomes world -X, while authored +Y
  // becomes world +Z. The fixed display volumes form the glazed boundaries;
  // the east entrance remains open for the player's collision circle.
  addLocalObstacle('east wall', 2.72, 2.90, -3.10, 3.10);
  addLocalObstacle('rear wall', -2.90, 2.90, 2.92, 3.10);
  addLocalObstacle('west rear wall', -2.90, -2.72, 0.82, 3.10);
  addLocalObstacle('main display cabinet', -2.41, 1.25, -2.94, -2.22);
  addLocalObstacle('return display cabinet', -2.74, -2.02, -2.40, 0.30);
  addLocalObstacle('interior cabinet', 0.94, 2.50, 0.10, 0.60);
  addLocalObstacle('customer counter', -1.88, 0.58, 1.33, 2.11);
  addLocalObstacle('service partition', -2.80, -0.44, 2.62, 2.74);
  // The arcade connector west of the shop stays walkable, but its far
  // boundary wall (AP_ArcadeOppositeBoundary) is solid.
  addLocalObstacle('arcade boundary wall', -6.30, -6.10, -3.80, 4.00);
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
    if (child instanceof Mesh) {
      child.castShadow = true;
      child.receiveShadow = true;
    }
  });
  applyBusShelterTexturePolicy(model);
}

function applyNiceThingsTexturePolicy(model: Group): void {
  // The GLB carries the Blender-authored metric UVs and PBR sets from
  // niceThingsTextures.py / exportNiceThings.py (pink limewash, sandstone,
  // joinery). Runtime applies the shared photographic filtering policy and
  // configures the glazing, which stays a placeholder material.
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
      material.emissiveMap = null;
      material.emissive.set(0x000000);
      material.emissiveIntensity = 0;

      for (const texture of [
        material.map,
        material.roughnessMap,
        material.metalnessMap,
        material.aoMap,
        material.normalMap,
      ]) {
        if (texture) {
          applyTextureProfile(texture, 'PHOTO_ENVIRONMENT');
        }
      }

      if (material.name === 'MAT_NT_Glass_PLACEHOLDER') {
        material.transparent = true;
        material.opacity = 0.16;
        material.depthWrite = false;
        material.roughness = 0.22;
      } else if (!material.map) {
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

function applyVinylExchangeTexturePolicy(model: Group): void {
  // The GLB carries the Blender-authored metric UVs and PBR material sets.
  // Runtime only applies the shared photographic filtering policy, preserves
  // the blockout's untextured regions, and configures transparent glazing.
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
      material.emissiveMap = null;
      material.emissive.set(0x000000);
      material.emissiveIntensity = 0;

      for (const texture of [
        material.map,
        material.roughnessMap,
        material.metalnessMap,
        material.aoMap,
        material.normalMap,
      ]) {
        if (texture) {
          applyTextureProfile(texture, 'PHOTO_ENVIRONMENT');
        }
      }

      if (material.name === 'MAT_VE_Glass_PLACEHOLDER') {
        material.transparent = true;
        material.opacity = 0.28;
        material.depthWrite = false;
        material.roughness = 0.2;
        material.metalness = 0.04;
      } else if (material.name === 'MAT_VE_Surface_sign-black-panel-tagline') {
        // Measured coating shift: #41495b sign box -> #303239 tagline strip.
        // MeshStandardMaterial.color is a linear multiplier over the map.
        material.color.setRGB(0.56, 0.48, 0.39);
      } else if (!material.map) {
        material.roughness = Math.max(material.roughness, 0.58);
      }
    }
  });
}

function applyAdvancedPhotoBlockoutPolicy(model: Group): void {
  // Preserve the geometry-review palette. Runtime intervention is limited to
  // transparent glazing, restrained emissive response for the bright
  // interior and the arcade's photographed circular fixture, and dropping the
  // arcade floor slice.
  //
  // That floor sits at y = 0 and reaches 3.6 m north of the shopfront, over
  // the South Road pavement, the carriageway and the open ground to the west.
  // It z-fought with those surfaces (white striping along the kerb) and read
  // as a pale untextured slab, so the world's own surfaces are the ground here.
  const arcadeFloors: Mesh[] = [];
  model.traverse((child) => {
    if (child instanceof Mesh && child.name.startsWith('AP_ArcadeFloor_')) {
      arcadeFloors.push(child);
    }
  });
  arcadeFloors.forEach((floor) => floor.removeFromParent());

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
      if (material.name === 'MAT_AP_Glass_PLACEHOLDER') {
        material.transparent = true;
        material.opacity = 0.19;
        material.depthWrite = false;
        material.roughness = 0.16;
        material.metalness = 0.04;
      } else if (material.name === 'MAT_AP_InteriorWall_PLACEHOLDER') {
        material.emissive.set(0x2a2419);
        material.emissiveIntensity =
          0.13 * VISUAL_STYLE.lighting.emissiveMultiplier;
        material.roughness = Math.max(material.roughness, 0.7);
      } else if (material.name === 'MAT_AP_ReviewRing') {
        material.color.set(0xffe7b7);
        material.emissive.set(0xffc96f);
        material.emissiveIntensity =
          2.1 * VISUAL_STYLE.lighting.emissiveMultiplier;
        material.roughness = 0.25;
      } else {
        material.roughness = Math.max(material.roughness, 0.55);
      }
    }
  });
}

function applyDreamsModelPolicy(model: Group): void {
  // The greybox carries the PBR sets from dreamsGreyboxTextures.py; the
  // photographic-era branches below match only the retired photographic GLB.
  applyPhotographicModelPolicy(model);
  model.traverse((child) => {
    if (!(child instanceof Mesh)) {
      return;
    }
    child.castShadow = true;
    child.receiveShadow = true;
    if (!Array.isArray(child.material) && child.material.name === 'Dreams_Greybox_Mortar') {
      // The greybox modelled each brick joint as a strip so brick scale could be
      // approved before texturing; drm-brick now carries its own joints.
      child.visible = false;
      return;
    }
    const materials = Array.isArray(child.material)
      ? child.material
      : [child.material];
    for (const material of materials) {
      if (!(material instanceof MeshStandardMaterial)) {
        continue;
      }
      profileAuthoredMaps(material);
      if (material.name === 'Dreams_Greybox_Light_Tube') {
        // The greybox's fluorescent tubes over the signboard and shutters.
        material.emissive.set(0xd9fff8);
        material.emissiveIntensity = 1.25 * VISUAL_STYLE.lighting.emissiveMultiplier;
        material.roughness = 0.24;
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
  // The approved geometry carries the measured PBR sets from gulliversTextures.py
  // (green, cream and plinth glazed tile, brick, painted joinery). Runtime keeps
  // the maps; lettering, plaques and glazing stay placeholders.
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
      profileAuthoredMaps(material);
      if (!material.map) {
        material.roughness = Math.max(material.roughness, 0.58);
      }
    }
  });
}

// Runtime glow per MCR1 material. The GLB carries the Blender-authored
// artwork as base colour; the lit surfaces reuse it as their emissive map so
// the honeycomb holes and the black sign housings stay dark.
// The yellow lightboxes carry a saturated emissive tint: at this brightness
// the tone mapper otherwise bleaches the lettering to cream.
const MCR1_EMISSIVE: Readonly<Record<string, readonly [number, number]>> = {
  MCR1_Signage: [2.6, 0xffc400],
  MCR1_Honeycomb_Lightbox: [2.2, 0xffc400],
  MCR1_Sign_Ring_White: [3, 0xffffff],
  MCR1_Window_Vinyl: [0.75, 0xffffff],
  MCR1_Riser_Vinyl: [0.75, 0xffffff],
  MCR1_Shelving: [0.7, 0xffffff],
  MCR1_LED_Ceiling: [1.5, 0xffffff],
  MCR1_Upper_Glazing: [0.55, 0xffffff],
};

function applyMcr1ModelPolicy(model: Group): void {
  // MCR1 keeps its illuminated fascia. In the game the owner has been asked
  // to take it down; he has not.
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
      for (const texture of [
        material.map,
        material.roughnessMap,
        material.metalnessMap,
        material.aoMap,
        material.normalMap,
      ]) {
        if (texture) {
          applyTextureProfile(texture, 'PHOTO_ENVIRONMENT');
        }
      }
      const glow = MCR1_EMISSIVE[material.name];
      if (glow !== undefined) {
        const [intensity, tint] = glow;
        material.emissive.set(tint);
        material.emissiveMap = material.map;
        material.emissiveIntensity =
          intensity * VISUAL_STYLE.lighting.emissiveMultiplier;
      } else {
        material.emissiveMap = null;
        material.emissive.set(0x000000);
        material.emissiveIntensity = 0;
      }
      if (material.name === 'MCR1_Window_Vinyl') {
        // Opaque print over clear glass: the alpha lives in the base map.
        material.transparent = true;
        material.depthWrite = false;
        material.roughness = 0.08;
      } else if (material.name === 'MCR1_Upper_Glazing') {
        material.roughness = 0.08;
        material.metalness = 0.25;
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
      for (const texture of [
        material.map,
        material.roughnessMap,
        material.metalnessMap,
        material.aoMap,
        material.normalMap,
        material.emissiveMap,
      ]) {
        if (texture) {
          applyTextureProfile(texture, 'PHOTO_ENVIRONMENT');
        }
      }
      material.emissive.set(0x000000);
      material.emissiveIntensity = 0;
      if (material.name === 'MAT_CASS_LightFixture') {
        material.color.set(0xffe0a3);
        material.emissive.set(0xffc56c);
        material.emissiveIntensity = 2.2 * VISUAL_STYLE.lighting.emissiveMultiplier;
        material.roughness = 0.24;
      } else if (material.name === 'MAT_CASS_InteriorWall') {
        material.emissive.set(0x2c1a0d);
        material.emissiveIntensity = 0.16 * VISUAL_STYLE.lighting.emissiveMultiplier;
        material.roughness = Math.max(material.roughness, 0.68);
      } else if (material.name === 'MAT_CASS_Glass') {
        material.transparent = true;
        material.opacity = 0.18;
        material.depthWrite = false;
        material.roughness = 0.12;
        material.metalness = 0.05;
      } else if (material.name === 'MAT_CASS_Slogan') {
        // Opaque raised letter outlines traced from Daniel's reference photo.
        material.transparent = false;
        material.depthWrite = true;
        material.roughness = 0.42;
        material.emissive.set(0xf47c35);
        material.emissiveIntensity = 0.24 * VISUAL_STYLE.lighting.emissiveMultiplier;
      } else if (material.name === 'MAT_CASS_Address') {
        material.transparent = true;
        material.depthWrite = false;
        material.emissive.set(0xf05b23);
        material.emissiveMap = material.map;
        material.emissiveIntensity = 0.16 * VISUAL_STYLE.lighting.emissiveMultiplier;
        material.roughness = 0.42;
      } else if (material.name === 'MAT_CASS_WindowDisplay' || material.name === 'MAT_CASS_RightWindowDisplay') {
        material.transparent = true;
        material.depthWrite = false;
        material.emissive.set(0xffffff);
        material.emissiveMap = material.map;
        material.emissiveIntensity = 0.12 * VISUAL_STYLE.lighting.emissiveMultiplier;
        material.roughness = 0.34;
      } else {
        material.roughness = Math.max(material.roughness, 0.58);
      }
    }
  });
}

function applyReneeBlockoutPolicy(model: Group): void {
  // Renee carries the measured PBR sets from reneeTextures.py (brick, black
  // fascia, white frames and sills, oak, navy walls, concrete). Runtime keeps the
  // maps, prevents stray emissive treatment and configures the glazing.
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
      profileAuthoredMaps(material);
      material.emissive.set(0x000000);
      material.emissiveIntensity = 0;
      if (material.name === 'MAT_REN_Glass_PLACEHOLDER') {
        material.transparent = true;
        material.opacity = 0.22;
        material.depthWrite = false;
        material.roughness = 0.28;
      } else if (!material.map) {
        material.roughness = Math.max(material.roughness, 0.58);
      }
    }
  });
}

function applyTheHiveModelPolicy(model: Group): void {
  // The Hive carries the measured PBR sets from theHiveTextures.py (black and
  // buff brick, concrete, bronze metal, white render, interior oak). Runtime
  // keeps the maps and configures its layered transparent systems; the
  // perforated screens stay a placeholder.
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
      profileAuthoredMaps(material);
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
  // Come Through Lab carries the measured PBR sets from
  // comeThroughLabTextures.py (brick, polychrome arches, sandstone, oak,
  // painted metal). Decals, lettering and the QR code are still pending.
  // Runtime keeps the maps and configures the glazing so the shopfront reads
  // through the grilles.
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
      profileAuthoredMaps(material);
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
  localLights: LocalLightRegistry,
): Promise<void> {
  try {
    const streetlightX = location.x + 6.15;
    const streetlightZ = location.z - 10.6;
    const [shop, bin, streetlight, bollard] = await Promise.all([
      loadModel('assets/models/harperhey-coral-shop.glb'),
      loadModel('assets/models/harperhey-coral-bin.glb'),
      createStreetlightFixture({
        name: 'Coral matching sodium streetlight',
        x: streetlightX,
        z: streetlightZ,
        yaw: yawTowardNearestRoad(streetlightX, streetlightZ),
        model: 'warm-old',
        color: VISUAL_STYLE.lighting.sodium,
      }),
      loadModel('assets/models/harperhey-coral-bollard.glb'),
    ]);

    applyCoralModelPolicy(shop);
    applyCoralModelPolicy(bin);
    applyCoralModelPolicy(bollard);

    for (const model of [shop, bin, bollard]) {
      mergeStaticModelMeshes(model);
    }

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

    root.add(streetlight);

    for (const [index, zOffset] of [-7.2, 8.8].entries()) {
      const placedBollard = index === 0 ? bollard : bollard.clone(true);
      placedBollard.name = `Coral matching pavement bollard ${index + 1}`;
      placedBollard.position.set(location.x + 5.7, 0, location.z + zOffset);
      placedBollard.scale.setScalar(0.92);
      root.add(placedBollard);
    }

    const coolShopLight = createManagedPointLight(
      'Coral cool shopfront spill north',
      location.x + 6.1,
      2.55,
      location.z - 5.5,
      VISUAL_STYLE.lighting.coldWhite,
      2.25 * VISUAL_STYLE.lighting.emissiveMultiplier,
      10,
    );
    const coolShopLightSouth = createManagedPointLight(
      'Coral cool shopfront spill south',
      location.x + 6.1,
      2.55,
      location.z + 5.5,
      VISUAL_STYLE.lighting.coldWhite,
      2.25 * 0.82 * VISUAL_STYLE.lighting.emissiveMultiplier,
      10,
    );
    localLights.register({
      name: 'Coral shopfront pair',
      lights: [coolShopLight, coolShopLightSouth],
      priority: 1.05,
    });

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
      'assets/models/nice-things-blockout.glb?v=surface-pass-20260921',
    );
    applyNiceThingsTexturePolicy(florist);
    mergeStaticModelMeshes(florist);
    florist.name = 'Nice Things textured blockout';
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
      'assets/models/harperhey-dreams-greybox.glb?v=textured-20260922',
    );
    applyDreamsModelPolicy(dreams);
    mergeStaticModelMeshes(dreams);
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
      'assets/models/harperhey-gullivers.glb?v=textured-20260922',
    );
    applyGulliversModelPolicy(gullivers);
    mergeStaticModelMeshes(gullivers);
    gullivers.name = 'Gullivers textured asset';
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
  localLights: LocalLightRegistry,
): Promise<void> {
  try {
    const mcr1 = await loadModel(
      'assets/models/harperhey-mcr1-geometry.glb?v=illuminated-20260921',
    );
    applyMcr1ModelPolicy(mcr1);
    mergeStaticModelMeshes(mcr1);
    mcr1.name = 'MCR1 illuminated corner shop';
    // The Blender asset uses the real corner as its modelling origin rather
    // than the plot centre. This offset centres its 11.7 m envelope immediately
    // west of the Florist while keeping the main frontage south-facing.
    const originX = location.x - 1.45;
    mcr1.position.set(originX, 0, location.z);
    root.add(mcr1);

    // Blender Y maps to world -Z after glTF conversion: the frontage at
    // Blender Y -4.0 sits at world z + 4.0, the side (Blender X -4.4) at x - 4.4.
    const frontZ = location.z + 4.0;
    const sideX = originX - 4.4;
    const intensityScale = VISUAL_STYLE.lighting.emissiveMultiplier;
    localLights.register({
      name: 'MCR1 fascia',
      lights: [
        createManagedPointLight(
          'MCR1 yellow fascia wash front',
          originX + 2.2,
          3.0,
          frontZ + 1.4,
          0xffd21a,
          10 * intensityScale,
          9,
        ),
        createManagedPointLight(
          'MCR1 yellow fascia wash corner',
          sideX - 0.9,
          3.0,
          frontZ + 0.6,
          0xffd21a,
          8 * intensityScale,
          8,
        ),
        createManagedPointLight(
          'MCR1 cold interior spill',
          originX + 1.6,
          1.6,
          frontZ + 0.9,
          VISUAL_STYLE.lighting.coldWhite,
          3.2 * intensityScale,
          7,
        ),
      ],
      priority: 1.25,
      selectionMode: 'location-relevance',
      activationRadius: 18,
    });
    addReflectionPatch(root, 'MCR1 fascia reflection front', originX + 1.8, frontZ + 2.6, 8.4, 1.4, 0xffd21a, 0.34);
    addReflectionPatch(root, 'MCR1 fascia reflection side', sideX - 2.2, location.z + 1.6, 1.3, 3.0, 0xffd21a, 0.28);
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
      'assets/models/cass_art.glb?v=reference-lettering-20260922',
    );
    applyCassArtModelPolicy(cassArt);
    mergeStaticModelMeshes(cassArt);
    cassArt.name = 'Cass Art textured building';
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
      'assets/models/renee-blockout.glb?v=textured-20260922',
    );
    applyReneeBlockoutPolicy(renee);
    mergeStaticModelMeshes(renee);
    renee.name = 'Renee textured asset';
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
      'assets/models/the_hive.glb?v=textured-20260922',
    );
    applyTheHiveModelPolicy(hive);
    mergeStaticModelMeshes(hive);
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
  localLights: LocalLightRegistry,
): Promise<void> {
  try {
    const [lab, dropbox, props] = await Promise.all([
      loadModel('assets/models/come_through_lab.glb?v=textured-20260922'),
      loadModel('assets/models/ctl_dropbox.glb?v=textured-20260922'),
      loadModel('assets/models/ctl_dropoff_props.glb?v=textured-20260922'),
    ]);
    applyComeThroughLabModelPolicy(lab);
    applyComeThroughLabModelPolicy(dropbox);
    applyComeThroughLabModelPolicy(props);
    lab.name = 'Come Through Lab textured asset';
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

    lab.updateWorldMatrix(true, true);
    const wallFixture = lab.getObjectByName('CTL_WallFixture_AlarmBox');
    const entranceAnchor = lab.getObjectByName('CTL_EntranceTriggerAnchor');
    const dropBoxAnchor = dropbox.getObjectByName('CTL_DropBox_InteractAnchor');
    let thresholdPosition = wallFixture?.getWorldPosition(new Vector3());

    if (thresholdPosition) {
      // The geometry pass has no authored luminaire. This restrained temporary
      // cue sits just proud of the real wall fixture and classifies the door +
      // 24-hour drop box; a final fixture must come from the asset pass.
      thresholdPosition.x += 0.82;
    } else if (entranceAnchor && dropBoxAnchor) {
      thresholdPosition = entranceAnchor
        .getWorldPosition(new Vector3())
        .lerp(dropBoxAnchor.getWorldPosition(new Vector3()), 0.5);
      thresholdPosition.y = 2.45;
    }

    if (thresholdPosition) {
      localLights.register({
        name: 'Come Through Lab threshold',
        lights: [
          createManagedPointLight(
            'Come Through Lab entrance and drop-box cue',
            thresholdPosition.x,
            thresholdPosition.y,
            thresholdPosition.z,
            VISUAL_STYLE.lighting.coldWhite,
            3.2,
            6,
          ),
        ],
        priority: 1.25,
        selectionMode: 'location-relevance',
        activationRadius: 13,
      });
    } else {
      console.warn(
        '[World] Come Through Lab has no usable threshold or wall-fixture anchor.',
      );
    }
    mergeStaticModelMeshes(lab);
    mergeStaticModelMeshes(dropbox);
    mergeStaticModelMeshes(props);
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
    mergeStaticModelMeshes(villageBooks);
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

async function replaceAdvancedPhotoFallback(
  root: Group,
  fallback: Mesh,
  location: WorldLocation,
): Promise<void> {
  try {
    const advancedPhoto = await loadModel(
      'assets/models/advanced-photo-blockout.glb?v=geometry-wip-20260913',
    );
    applyAdvancedPhotoBlockoutPolicy(advancedPhoto);
    mergeStaticModelMeshes(advancedPhoto);
    advancedPhoto.name =
      'Advanced Photo geometry blockout — detail pass pending';
    // Blender's main -Y frontage imports facing +Z. Rotate it north and place
    // the authored shop-body origin at the canonical location. Its short
    // arcade connector deliberately extends west of the collision footprint.
    advancedPhoto.rotation.y = Math.PI;
    advancedPhoto.position.set(location.x, 0, location.z);
    root.add(advancedPhoto);
    root.remove(fallback);
  } catch (error) {
    markLoadFailure(fallback, 'Advanced Photo');
    console.error(
      '[World] Failed to load advanced-photo-blockout.glb. Showing the magenta fallback.',
      error,
    );
  }
}

// The GLB is authored at real-world scale. The game's South Road placeholders
// are larger (the Off-Licence is 11 × 10 × 7.6 m), so Spice Cabin is enlarged
// to sit with its neighbour, as the bus shelter is at 1.3. Depth is matched
// exactly to the Off-Licence's 10 m, because the asset's east party wall has no
// exterior face and must stay covered; the 5% difference is not visible. Keep
// worldLayout.ts's spice-cabin envelope equal to 6.2 × 7.0 × 5.1 m times these.
const SPICE_CABIN_SCALE = 1.5;
const SPICE_CABIN_DEPTH_SCALE = 10 / 7;

// Bollards authored in spice-cabin.glb, as unscaled plot-local (x, z) after glTF
// axis conversion. They stand on the pavement just off the building line.
const SPICE_CABIN_BOLLARDS: readonly (readonly [number, number])[] = [
  [-3.28, 4.5],
  [-2.38, 4.42],
  [-1.9, 4.58],
  [0.55, 4.46],
];

function addSpiceCabinBollardCollision(
  obstacles: CollisionObstacle[],
  location: WorldLocation,
): void {
  const half = 0.08 * SPICE_CABIN_SCALE;
  for (const [x, z] of SPICE_CABIN_BOLLARDS) {
    const bollardX = location.x + x * SPICE_CABIN_SCALE;
    const bollardZ = location.z + z * SPICE_CABIN_DEPTH_SCALE;
    obstacles.push({
      name: 'Spice Cabin bollard',
      minX: bollardX - half,
      maxX: bollardX + half,
      minZ: bollardZ - half,
      maxZ: bollardZ + half,
      height: 0.9,
      blocksCamera: false,
    });
  }
}

async function addSpiceCabinModel(
  root: Group,
  location: WorldLocation,
  localLights: LocalLightRegistry,
): Promise<void> {
  try {
    const spiceCabin = await loadModel('assets/models/spice-cabin.glb?v=textured-20260916');
    applySpiceCabinTexturePolicy(spiceCabin);
    spiceCabin.name = 'Spice Cabin finished hero asset';
    // Blender's -Y shopfront imports facing +Z, which is this plot's South Road
    // frontage, so no rotation. The authored origin is the footprint centre.
    // Stand it at pavement height so its ground-contact decal clears the flags.
    const s = SPICE_CABIN_SCALE;
    const sd = SPICE_CABIN_DEPTH_SCALE;
    const frontZ = location.z + location.depth / 2;
    spiceCabin.scale.set(s, s, sd);
    spiceCabin.position.set(
      location.x,
      pavementTopAt(PAVEMENTS, location.x, frontZ + 0.5) ?? 0,
      location.z,
    );
    root.add(spiceCabin);

    // The asset's colour only reads under its own practical light: the world is
    // moonlit blue, and without the tube fittings and shop glow the brick,
    // cream band and printed signs turn grey-blue. Lights hang off the GLB's
    // authored anchors; sign washes stand clear of the wall to avoid hotspots.
    // Offsets and ranges follow the model scale, and intensity follows its
    // square so the inverse-square falloff lands the same light on the façade.
    spiceCabin.updateMatrixWorld(true);
    const anchorAt = (name: string, fallback: Vector3): Vector3 =>
      spiceCabin.getObjectByName(name)?.getWorldPosition(new Vector3()) ?? fallback;
    const warmTube = 0xffd9a0;
    const intensityScale = VISUAL_STYLE.lighting.emissiveMultiplier * s * s;
    const shopWindow = anchorAt('SPICE_LightAnchor_Window', new Vector3(location.x + 1.4 * s, 2.25 * s, frontZ - 0.6 * sd));
    const frontSign = anchorAt('SPICE_LightAnchor_Sign', new Vector3(location.x, 3.5 * s, frontZ + 0.45 * sd));
    const sideSign = anchorAt('SPICE_LightAnchor_SideSign', new Vector3(location.x - 3.7 * s, 4.0 * s, location.z - 0.3 * sd));
    localLights.register({
      name: 'Spice Cabin shopfront',
      lights: [
        createManagedPointLight(
          'Spice Cabin warm interior spill',
          shopWindow.x,
          shopWindow.y,
          shopWindow.z,
          VISUAL_STYLE.lighting.sodium,
          7 * intensityScale,
          6 * s,
        ),
        createManagedPointLight(
          'Spice Cabin front sign tube wash',
          frontSign.x,
          frontSign.y + 0.15 * s,
          frontSign.z + 0.35 * sd,
          warmTube,
          6 * intensityScale,
          5 * s,
        ),
      ],
      priority: 1.2,
      selectionMode: 'location-relevance',
      activationRadius: 14 * s,
    });
    localLights.register({
      name: 'Spice Cabin gable sign',
      lights: [
        createManagedPointLight(
          'Spice Cabin gable sign tube wash',
          sideSign.x - 0.2 * s,
          sideSign.y - 0.2 * s,
          sideSign.z,
          warmTube,
          6.5 * intensityScale,
          5 * s,
        ),
      ],
      priority: 1.1,
      selectionMode: 'location-relevance',
      activationRadius: 12 * s,
    });
    mergeStaticModelMeshes(spiceCabin);
  } catch (error) {
    console.error(
      '[World] Failed to load spice-cabin.glb. Only its collision footprint remains.',
      error,
    );
  }
}

// Worn pallets (docs/assets/pallets.md) stacked against Spice Cabin's west gable,
// just back from the South Road building line, on the bare ground of the gap:
// the blue 1200 × 1000 on the ground, the brown 1200 × 800 dropped on it
// slightly askew. Both GLBs are authored at real-world scale standing on Y = 0,
// long side on local X; the yaw runs that along the wall with the fork-opening
// face (local +Z) looking west into the gap. Daniel asked for them 4× bigger,
// then half that, so every pallet-derived size below is multiplied by
// PALLET_STACK_SCALE; the wall gap and setback stay absolute so the stack still
// hugs the gable.
const PALLET_STACK_SCALE = 2;
const SPICE_CABIN_PALLET_STACK_YAW = -Math.PI / 2;
const SPICE_CABIN_PALLET_WALL_GAP = 0.15;
const SPICE_CABIN_PALLET_SETBACK = 0.35;
// Top of the blue deck boards. The brown pallet's lowest nail heads sink a
// millimetre or two into them, which is hidden.
const PALLET_BLUE_DECK_TOP = 0.146;
// Top face of the 'World ground' surface (laid at y -0.12), measured by ray cast.
// The gap beside the gable is bare ground, 7 cm below 0, not pavement.
const WORLD_GROUND_TOP = -0.07;
// Top of the car-park slab (0.1 m thick, centred at y = -0.02).
const CAR_PARK_SURFACE_TOP = 0.03;

function spiceCabinPalletStackPlacement(location: WorldLocation): PalletStackMarker {
  return {
    id: 'spice-cabin-pallets',
    name: 'Spice Cabin pallet stack',
    // The blue pallet is 1.0 m deep across the wall and 1.2 m long along it, before scaling.
    x: location.x - location.width / 2 - SPICE_CABIN_PALLET_WALL_GAP - 0.5 * PALLET_STACK_SCALE,
    z: location.z + location.depth / 2 - SPICE_CABIN_PALLET_SETBACK - 0.6 * PALLET_STACK_SCALE,
    rotationY: SPICE_CABIN_PALLET_STACK_YAW,
  };
}

function addPalletStackCollision(
  obstacles: CollisionObstacle[],
  marker: PalletStackMarker,
): void {
  obstacles.push(
    orientedBoxObstacle(
      marker.name,
      marker.x,
      marker.z,
      1.2 * PALLET_STACK_SCALE,
      1.0 * PALLET_STACK_SCALE,
      marker.rotationY,
      0.3 * PALLET_STACK_SCALE,
    ),
  );
}

let palletTemplates: Promise<{ blue: Group; brown: Group }> | undefined;

function loadPalletTemplates(): Promise<{ blue: Group; brown: Group }> {
  palletTemplates ??= Promise.all([
    loadModel('assets/models/pallets/pallet_worn_blue.glb?v=texture-pass-20260914'),
    loadModel('assets/models/pallets/pallet_worn_brown.glb?v=texture-pass-20260914'),
  ]).then(([blue, brown]) => {
    applyPalletTexturePolicy(blue);
    applyPalletTexturePolicy(brown);
    mergeStaticModelMeshes(blue);
    mergeStaticModelMeshes(brown);
    // Spice Cabin's ground-contact decal crosses its pallet stack. Queue every
    // instance after such decals so all four stacks share the exact same policy.
    for (const pallet of [blue, brown]) {
      pallet.traverse((child) => {
        if (child instanceof Mesh && child.material instanceof MeshStandardMaterial) {
          child.material.transparent = true;
          child.material.depthWrite = true;
          child.renderOrder = 2;
        }
      });
    }
    return { blue, brown };
  });
  return palletTemplates;
}

function palletGroundAt(x: number, z: number): number {
  const pavement = pavementTopAt(PAVEMENTS, x, z);
  if (pavement !== undefined) {
    return pavement;
  }
  const carPark = WORLD_LOCATIONS.find((location) => location.kind === 'car-park');
  if (
    carPark &&
    Math.abs(x - carPark.x) <= carPark.width / 2 &&
    Math.abs(z - carPark.z) <= carPark.depth / 2
  ) {
    return CAR_PARK_SURFACE_TOP;
  }
  return WORLD_GROUND_TOP;
}

async function addPalletStack(root: Group, marker: PalletStackMarker): Promise<void> {
  const ground = palletGroundAt(marker.x, marker.z);
  try {
    const templates = await loadPalletTemplates();
    const blue = templates.blue.clone(true);
    const brown = templates.brown.clone(true);
    const s = PALLET_STACK_SCALE;
    blue.name = `${marker.name} worn blue pallet`;
    blue.scale.setScalar(s);
    blue.position.set(marker.x, ground, marker.z);
    blue.rotation.y = marker.rotationY;
    // Pushed toward the wall inside the blue deck's slack (0.1 m each side before
    // scaling), and turned a little so one end overhangs, as a dropped pallet lands.
    // Rotate that local offset with each stack. Both GLB origins are at their
    // base, so the deck height scales with them.
    const localOffsetX = -0.04 * s;
    const localOffsetZ = -0.05 * s;
    const cos = Math.cos(marker.rotationY);
    const sin = Math.sin(marker.rotationY);
    const brownOffsetX = localOffsetX * cos + localOffsetZ * sin;
    const brownOffsetZ = -localOffsetX * sin + localOffsetZ * cos;
    brown.name = `${marker.name} worn brown pallet`;
    brown.scale.setScalar(s);
    brown.position.set(
      marker.x + brownOffsetX,
      ground + PALLET_BLUE_DECK_TOP * s,
      marker.z + brownOffsetZ,
    );
    brown.rotation.y = marker.rotationY + 0.06;
    root.add(blue, brown);
  } catch (error) {
    console.error(
      `[World] Failed to load ${marker.name}. Only its collision remains.`,
      error,
    );
  }
}

// Stable pseudo-random pick so the same tower windows stay lit every load.
function nameHash(name: string): number {
  let hash = 2166136261;
  for (let index = 0; index < name.length; index += 1) {
    hash = Math.imul(hash ^ name.charCodeAt(index), 16777619);
  }
  return hash >>> 0;
}

function applyAbcBuildingModelPolicy(model: Group): void {
  // Geometry pass with placeholder clay. The ~400 tower-window panes are
  // opaque here so they merge into two draw calls instead of sorting as
  // hundreds of transparent meshes; a few are lit for the northern skyline.
  // Shopfront glass stays transparent so the Clints and Side Street shells read.
  const darkWindow = new MeshStandardMaterial({
    name: 'ABC tower window dark (runtime)',
    color: 0x0c121b,
    roughness: 0.32,
    metalness: 0.1,
    emissive: 0x050a14,
    emissiveIntensity: 0.4,
  });
  const litWindow = new MeshStandardMaterial({
    name: 'ABC tower window lit (runtime)',
    color: 0x2a2418,
    roughness: 0.6,
    emissive: VISUAL_STYLE.lighting.sodium,
    emissiveIntensity: 0.55,
  });
  model.traverse((child) => {
    if (!(child instanceof Mesh)) {
      return;
    }
    child.castShadow = true;
    child.receiveShadow = true;
    if (/^ABC_(TowerWindow_|TowerCore_CurtainGlass|PodiumGlass_RearWing)/.test(child.name)) {
      child.material = nameHash(child.name) % 9 === 0 ? litWindow : darkWindow;
      return;
    }
    const materials = Array.isArray(child.material) ? child.material : [child.material];
    for (const material of materials) {
      if (!(material instanceof MeshStandardMaterial)) {
        continue;
      }
      if (material.name === 'MAT_ABC_Canopy_PLACEHOLDER') {
        // The marquee's underside panels and sign bands are lit at night.
        material.emissive.set(0xfff1d8);
        material.emissiveIntensity = 0.35;
      } else {
        material.emissive.set(0x000000);
        material.emissiveIntensity = 0;
      }
      if (material.name === 'MAT_ABC_Glass_PLACEHOLDER') {
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

async function addAbcBuildingModel(root: Group): Promise<void> {
  try {
    const abc = await loadModel('assets/models/abc_building.glb?v=geometry-20260921');
    applyAbcBuildingModelPolicy(abc);
    // Keep the hinged Clints entrance (CL_Door pivots on its jamb) out of the
    // static merge so it can swing once interactions exist.
    const entrance = abc.getObjectByName('CL_Entrance');
    entrance?.removeFromParent();
    mergeStaticModelMeshes(abc);
    if (entrance) {
      abc.add(entrance);
    }
    abc.name = 'ABC Building (Clints, Side Street) geometry — textures pending';
    // Authored origin is the Quay Street / Lower Byrom Street corner; the
    // Quay Street frontage already faces +Z, so no rotation is needed.
    abc.position.set(ABC_BUILDING_CORNER.x, 0, ABC_BUILDING_CORNER.z);
    root.add(abc);
  } catch (error) {
    console.error('[World] Failed to load abc_building.glb.', error);
  }
}

function addAbcBuildingCollision(obstacles: CollisionObstacle[]): void {
  // Boxes in the GLB's own frame: mx along the frontage (west is negative),
  // my back from the Quay Street face (north is positive).
  const { x, z } = ABC_BUILDING_CORNER;
  const add = (name: string, mx0: number, mx1: number, my0: number, my1: number, height: number) => {
    obstacles.push({
      name: `ABC Building ${name}`,
      minX: x + mx0,
      maxX: x + mx1,
      minZ: z - my1,
      maxZ: z - my0,
      height,
    });
  };
  // Shopfronts sit 0.32 m behind the column faces; the Clints and Side Street
  // doors are closed until interiors can be entered.
  add('tower', -26.4, 0.55, 0.3, 21.95, 60);
  add('podium', -61.9, -26.4, 0.3, 21.95, 10.3);
  add('Side Street corner wall', -4.9, 0.55, -0.55, 0.3, 56.5);
  add('rear wing', -18, 0.55, 21.95, 46, 26.95);
  for (const mx of [-12.4, -19.9, -27.4, -34.9, -42.4, -49.9]) {
    add('column', mx - 0.33, mx + 0.33, -0.13, 0.3, 3.55);
  }
  add('ABC blade sign', -50.25, -49.92, -1.7, 0.3, 9.4);
  for (const [mx, my] of [[-33.3, -2.6], [-32.4, -1.4], [-29.2, -2.2], [-19.3, -2.3]] as const) {
    add('planter', mx - 0.55, mx + 0.55, my - 0.4, my + 0.4, 0.74);
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
    mergeStaticModelMeshes(realCamera);
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

async function replaceVinylExchangeFallback(
  root: Group,
  fallback: Mesh,
  location: WorldLocation,
): Promise<void> {
  fallback.visible = false;
  try {
    const vinylExchange = await loadModel(
      'assets/models/vinyl-exchange-blockout.glb?v=surface-pass-20260916',
    );
    applyVinylExchangeTexturePolicy(vinylExchange);
    mergeStaticModelMeshes(vinylExchange);
    vinylExchange.name = 'Vinyl Exchange textured geometry blockout — facade detail pending';

    // The Blender origin is the notional Oldham/Dale street-line corner. On
    // import, Blender -Y faces world +Z, so the Oldham frontage already faces
    // South Road and the Dale return already faces east. Put the authored
    // X = 0 side wall on the plot's east edge and Y = 0 frontage on Z = 54.
    const frontZ = location.z + location.depth / 2;
    vinylExchange.position.set(
      location.x + location.width / 2,
      pavementTopAt(PAVEMENTS, location.x, frontZ + 0.5) ?? 0,
      frontZ,
    );
    root.add(vinylExchange);
    root.remove(fallback);
  } catch (error) {
    fallback.visible = true;
    markLoadFailure(fallback, 'Vinyl Exchange');
    console.error(
      '[World] Failed to load vinyl-exchange-blockout.glb. Showing the magenta fallback.',
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
  localLights: LocalLightRegistry,
): void {
  if (location.id === 'dreams') {
    const fallback = createDreamsBuilding(location);
    fallback.rotation.y = location.front === 'north' ? Math.PI : 0;
    root.add(fallback);
    void replaceDreamsFallback(root, fallback, location);
    addCollisionFootprint(obstacles, location);
    // The raised entrance landing, its access ramp and their railings stand
    // 1.6 m proud of the façade (measured from the GLB at body height). The
    // player has no vertical movement, so they are solid rather than climbable.
    const frontZ = location.z - location.depth / 2;
    obstacles.push({
      name: 'Dreams entrance landing and ramp',
      minX: location.x - 7.1,
      maxX: location.x + 3.3,
      minZ: frontZ - 1.65,
      maxZ: frontZ,
      height: 1.65,
      blocksCamera: false,
    });
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
    void addMcr1Model(root, location, localLights);
    addCollisionFootprint(obstacles, location);
    // Stall risers, piers and portal jambs stand 0.9 m proud of the plot's
    // south edge (measured from the GLB at body height).
    obstacles.push({
      name: 'MCR1 shopfront',
      minX: location.x - location.width / 2,
      maxX: location.x + location.width / 2,
      minZ: location.z + location.depth / 2,
      maxZ: location.z + location.depth / 2 + 0.9,
      height: location.height,
    });
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
    void addComeThroughLabModel(root, location, localLights);
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

  if (location.id === 'spice-cabin') {
    void addSpiceCabinModel(root, location, localLights);
    // The door stands open as photographed, but interiors are not yet walkable,
    // so the measured envelope stays solid.
    addCollisionFootprint(obstacles, location);
    addSpiceCabinBollardCollision(obstacles, location);
    const palletStack = spiceCabinPalletStackPlacement(location);
    void addPalletStack(root, palletStack);
    addPalletStackCollision(obstacles, palletStack);
    addDevelopmentLabel(root, location.name, location.x, location.height + 1.1, location.z);
    return;
  }

  if (location.id === 'vinyl-exchange') {
    const fallback = createBlockoutBuildingMass(location);
    fallback.position.set(location.x, location.height / 2, location.z);
    fallback.name = 'Vinyl Exchange loading placeholder';
    root.add(fallback);
    void replaceVinylExchangeFallback(root, fallback, location);
    // The doors are articulated in the GLB for a future interaction pass, but
    // no interaction system exists yet, so the authored body remains solid.
    addCollisionFootprint(obstacles, location);
    addDevelopmentLabel(
      root,
      `${location.name} · geometry blockout · detail and textures pending`,
      location.x,
      location.height + 1.1,
      location.z,
    );
    return;
  }

  if (location.id === 'abc-building') {
    void addAbcBuildingModel(root);
    addAbcBuildingCollision(obstacles);
    addDevelopmentLabel(
      root,
      `${location.name} · geometry · textures pending`,
      location.x,
      11.5,
      location.z + location.depth / 2,
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

  if (location.id === 'advanced-photo') {
    const fallback = createBlockoutBuildingMass(location);
    fallback.position.set(location.x, location.height / 2, location.z);
    fallback.name = 'Advanced Photo loading placeholder';
    root.add(fallback);
    void replaceAdvancedPhotoFallback(root, fallback, location);
    addAdvancedPhotoInteriorCollision(obstacles, location);
    addDevelopmentLabel(
      root,
      `${location.name} · geometry blockout · detail pass pending`,
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
  } else if (location.id === 'florist') {
    // The GLB sits 2.8 m west of the plot centre and includes the Central
    // Buildings entry beside the shop, so the plot rectangle missed the model's
    // west 3 m and ran 3.2 m past its façade over the pavement. This is the
    // model's measured body-height extent instead.
    obstacles.push({
      name: location.name,
      minX: location.x - 6.2,
      maxX: location.x + 2.95,
      minZ: location.z - 6.9,
      maxZ: location.z + 0.52,
      height: location.height,
    });
  } else {
    addCollisionFootprint(obstacles, location);
  }

  if (location.id === 'florist') {
    void replaceFloristFallback(root, building, location);
  } else if (location.id === 'coral') {
    void replaceCoralFallback(root, building, location, localLights);
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

let busShelterTemplate: Promise<Group> | undefined;

// Both shelters clone one loaded model so the texture-pass maps are uploaded
// to the GPU once rather than per shelter.
function loadBusShelterTemplate(): Promise<Group> {
  busShelterTemplate ??= loadModel(
    'assets/models/bus-shelter/preston-busstop-textured.glb?v=texture-pass-20260913',
  ).then((model) => {
    applyBusShelterGeometryPolicy(model);
    mergeStaticModelMeshes(model);
    return model;
  });
  return busShelterTemplate;
}

async function replaceBusShelterFallback(
  root: Group,
  fallback: Group,
): Promise<void> {
  try {
    const shelter = (await loadBusShelterTemplate()).clone(true);
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
      } else if (material.name === 'MAT_GG_FixtureLens_PLACEHOLDER') {
        // The fixture geometry is authored even though the kiosk is awaiting
        // its final texture pass. A restrained practical keeps the source of
        // the counter light visible without making the whole shell emissive.
        material.emissive.set(0xfff1d6);
        material.emissiveIntensity =
          1.15 * VISUAL_STYLE.lighting.emissiveMultiplier;
        material.roughness = 0.28;
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
  localLights: LocalLightRegistry,
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
    stand.updateWorldMatrix(true, true);

    const counterAnchor = stand.getObjectByName('GG_LightAnchor_Counter');
    if (counterAnchor) {
      const position = counterAnchor.getWorldPosition(new Vector3());
      localLights.register({
        name: 'Greek Gyros counter practical',
        lights: [
          createManagedPointLight(
            'Greek Gyros counter spill',
            position.x,
            position.y,
            position.z,
            0xfff1d6,
            6,
            7,
          ),
        ],
        priority: 1.3,
        selectionMode: 'location-relevance',
        activationRadius: 13,
      });
    } else {
      console.warn('[World] Greek Gyros counter light anchor is missing.');
    }
    mergeStaticModelMeshes(stand);
    root.remove(fallback);
  } catch (error) {
    markShelterLoadFailure(fallback, 'Greek Gyros');
    console.error(
      '[World] Failed to load greek_gyros.glb. Showing the magenta fallback.',
      error,
    );
  }
}

/** Axis-aligned obstacle enclosing a local footprint after yaw `rotationY`. */
function rotatedObstacle(
  name: string,
  x: number,
  z: number,
  rotationY: number,
  minLocalX: number,
  maxLocalX: number,
  minLocalZ: number,
  maxLocalZ: number,
): CollisionObstacle {
  const cos = Math.cos(rotationY);
  const sin = Math.sin(rotationY);
  const corners = [
    [minLocalX, minLocalZ],
    [maxLocalX, minLocalZ],
    [minLocalX, maxLocalZ],
    [maxLocalX, maxLocalZ],
  ].map(([localX, localZ]) => [
    x + localX * cos + localZ * sin,
    z - localX * sin + localZ * cos,
  ]);
  const worldX = corners.map(([cornerX]) => cornerX);
  const worldZ = corners.map(([, cornerZ]) => cornerZ);
  return {
    name,
    minX: Math.min(...worldX),
    maxX: Math.max(...worldX),
    minZ: Math.min(...worldZ),
    maxZ: Math.max(...worldZ),
  };
}

function addGreekGyros(
  root: Group,
  obstacles: CollisionObstacle[],
  marker: FoodStandMarker,
  localLights: LocalLightRegistry,
): void {
  const fallback = createGreekGyrosFallback();
  fallback.name = `${marker.name} loading placeholder`;
  fallback.position.set(marker.x, 0, marker.z);
  fallback.rotation.y = marker.rotationY;
  root.add(fallback);
  void replaceGreekGyrosFallback(root, fallback, localLights);

  // Local footprint: the side service step projects 0.56 m past the +X wall,
  // so enclosing it keeps the player from clipping through the step. The
  // authored frontage faces +Z; stopping at the counter lip leaves the
  // projecting canopy overhead clear. Rotate the corners into world space.
  obstacles.push(
    {
      ...rotatedObstacle(marker.name, marker.x, marker.z, marker.rotationY, -3.2, 3.76, -1.3, 1.5),
      height: 3.4,
    },
  );
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
  // Stand on the flags: the uprights, rail legs and advert plinth are modelled
  // 30 mm below their base, and the ground-contact decal sits just above it.
  fallback.position.set(marker.x, pavementTopAt(PAVEMENTS, marker.x, marker.z) ?? 0, marker.z);
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
    height: 3.3,
  });
  addDevelopmentLabel(root, marker.name, marker.x, 3.4, marker.z);
}

function addCentralPark(root: Group, obstacles: CollisionObstacle[]): void {
  // The grass runs to the inner edges of the park pavements (x ±23.15,
  // z ±18.15), closing the strip of bare world ground that showed between.
  addParkGround(root, {
    x: PARK.x,
    z: PARK.z,
    width: 46.3,
    depth: 36.3,
    paths: [
      { name: 'Park path north', startX: -21, startZ: -15.2, endX: 21, endZ: -15.2, width: 1.5 },
      { name: 'Park path south', startX: -21, startZ: 15.2, endX: 21, endZ: 15.2, width: 1.5 },
      { name: 'Park path west', startX: -20.2, startZ: -15, endX: -20.2, endZ: 15, width: 1.5 },
      { name: 'Park path east', startX: 20.2, startZ: -15, endX: 20.2, endZ: 15, width: 1.5 },
      { name: 'Park diagonal NW-SE', startX: -20, startZ: -15, endX: 20, endZ: 15, width: 1.8 },
      { name: 'Park diagonal NE-SW', startX: 20, startZ: -15, endX: -20, endZ: 15, width: 1.8 },
    ],
  });

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
  // The basin rim is the solid edge. The 18 cm plinth around it stays
  // walkable, like the similarly raised pavements.
  obstacles.push(circleObstacle('Park fountain basin', 0, 0, 1.9, 1.65));

  addParkEdgeEnvironmentKit(root, obstacles);

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

const ROADS: readonly RoadSpan[] = [
  { name: 'North perimeter road', x: 0, z: -25.5, width: 72, depth: ROAD_WIDTH },
  { name: 'South perimeter road', x: 0, z: 25.5, width: 72, depth: ROAD_WIDTH },
  { name: 'West perimeter road', x: -29.5, z: 0, width: ROAD_WIDTH, depth: 66 },
  { name: 'East perimeter road', x: 29.5, z: 0, width: ROAD_WIDTH, depth: 66 },
  // Moved 10 m north (from Z = -44.2) so the north block is deep enough for
  // Renee (back at Z = -45.2) and Gulliver's (Z = -48.1) to sit off the road.
  { name: 'Outer North Road', x: 0, z: -54.2, width: 114, depth: ROAD_WIDTH },
  { name: 'Outer South Road', x: 0, z: 59.5, width: 114, depth: ROAD_WIDTH },
  // North ends extended to meet the moved Outer North Road (Z = -57.95).
  { name: 'Outer west street', x: -48, z: -4.975, width: ROAD_WIDTH, depth: 105.95 },
  { name: 'Outer east street', x: 57, z: -4.975, width: ROAD_WIDTH, depth: 105.95 },
  // Lower Byrom Street: the north outward connection, moved from X = 0 to run
  // past the ABC Building's east corner (Side Street wraps onto it).
  { name: 'Lower Byrom Street', x: 26.4, z: -86.975, width: ROAD_WIDTH, depth: 58.05 },
  { name: 'South Road outward connection', x: 0, z: 69.625, width: ROAD_WIDTH, depth: 12.75, centreLine: false },
  { name: 'West outward connection', x: -58, z: 25.5, width: 16, depth: ROAD_WIDTH, centreLine: false },
  { name: 'East outward connection', x: 61, z: 0, width: 8, depth: ROAD_WIDTH, centreLine: false },
];

// Public streetlights: [x, z, light colour, fixture]. Fixtures change in
// batches, street by street, the way a council replaces them: the park's north
// edge and South Road keep the old sodium lanterns, half of the park's south
// edge has been retrofitted with LED, the building pavements have painted
// swan necks. The colours are the game's photographic casts, not the lamps'.
const STREETLIGHTS = [
  [-20, -19, VISUAL_STYLE.lighting.sodium, 'warm-old'],
  [20, -19, VISUAL_STYLE.lighting.sodium, 'warm-old'],
  [-18, 19, VISUAL_STYLE.lighting.sodium, 'weathered'],
  [-9, 19, VISUAL_STYLE.lighting.sodium, 'weathered'],
  [8, 19, VISUAL_STYLE.lighting.magenta, 'led-modern'],
  [16, 19, VISUAL_STYLE.lighting.magenta, 'led-modern'],
  [-25, -10, VISUAL_STYLE.lighting.coldWhite, 'led-modern'],
  [-25, 10, VISUAL_STYLE.lighting.sodium, 'weathered'],
  [25, -10, VISUAL_STYLE.lighting.fluorescent, 'led-modern'],
  [25, 10, VISUAL_STYLE.lighting.coldWhite, 'led-modern'],
  [-9.6, -20.5, VISUAL_STYLE.lighting.sodium, 'warm-old'],
  [12, -29, VISUAL_STYLE.lighting.magenta, 'curved'],
  [-12, 29, VISUAL_STYLE.lighting.sodium, 'curved'],
  [12, 29, VISUAL_STYLE.lighting.sodium, 'curved'],
  [-34, 7, VISUAL_STYLE.lighting.sodium, 'curved'],
  [34, 17, VISUAL_STYLE.lighting.coldWhite, 'led-modern'],
  [-15, 55, VISUAL_STYLE.lighting.sodium, 'warm-old'],
  [1, 55, VISUAL_STYLE.lighting.sodium, 'warm-old'],
  [16.5, 55, VISUAL_STYLE.lighting.magenta, 'led-modern'],
  [29, 55, VISUAL_STYLE.lighting.sodium, 'weathered'],
  // ABC Building frontage and Lower Byrom Street: modern LED heads.
  [-30, -58.5, VISUAL_STYLE.lighting.coldWhite, 'led-modern'],
  [-12, -58.5, VISUAL_STYLE.lighting.coldWhite, 'led-modern'],
  [15, -58.5, VISUAL_STYLE.lighting.coldWhite, 'led-modern'],
  [22.2, -82, VISUAL_STYLE.lighting.coldWhite, 'led-modern'],
  [22.2, -102, VISUAL_STYLE.lighting.sodium, 'weathered'],
] as const satisfies readonly (readonly [number, number, number, StreetlightModel])[];

// Painted pool radius under an eight-metre lantern.
const STREETLIGHT_POOL_RADIUS = 2.9;

// Lanterns overhang the nearest carriageway: yaw turns the model's +X
// outreach toward that road's centre line.
function yawTowardNearestRoad(x: number, z: number): number {
  let best = Number.POSITIVE_INFINITY;
  let yaw = 0;
  for (const road of ROADS) {
    const alongX = road.width >= road.depth;
    const halfLength = (alongX ? road.width : road.depth) / 2 + 2;
    const along = alongX ? x - road.x : z - road.z;
    if (Math.abs(along) > halfLength) {
      continue;
    }
    const across = alongX ? road.z - z : road.x - x;
    if (Math.abs(across) < best) {
      best = Math.abs(across);
      // Rotation about Y maps +X to (cos, -sin).
      yaw = alongX ? (across > 0 ? -Math.PI / 2 : Math.PI / 2) : across > 0 ? 0 : Math.PI;
    }
  }
  return yaw;
}

const PUBLIC_LIGHTS = STREETLIGHTS.map(([x, z, color, model], index) => {
  const yaw = yawTowardNearestRoad(x, z);
  return {
    name: `Public streetlight ${index + 1} (${model})`,
    x,
    z,
    yaw,
    model,
    color,
    emitter: streetlightEmitterWorld({ x, z, yaw, model }),
  };
});

const CROSSINGS: readonly RoadCrossing[] = [
  { name: 'South park crossing', x: 0, z: 25.5 },
  { name: 'West park crossing', x: -29.5, z: 0, rotation: Math.PI / 2 },
  { name: 'East park crossing', x: 29.5, z: 0, rotation: Math.PI / 2 },
];

// `back` is what the non-kerb edge meets; kerbs are found from ROADS.
const PAVEMENTS: readonly PavementSpan[] = [
  // The park north and south pavements run to the carriageway edge (z ±21.75).
  // At 2.5 m deep they stopped 1.1 m short, so no kerb was detected and a strip
  // of bare world ground, 8 cm lower, ran between pavement and road.
  { name: 'Park north pavement', x: 0, z: -19.95, width: 49, depth: 3.6, back: 'verge', damp: true },
  { name: 'Park south pavement', x: 0, z: 19.95, width: 49, depth: 3.6, back: 'verge' },
  { name: 'Park west pavement', x: -24.4, z: 0, width: PAVEMENT_WIDTH, depth: 39, back: 'verge', damp: true },
  { name: 'Park east pavement', x: 24.4, z: 0, width: PAVEMENT_WIDTH, depth: 39, back: 'verge' },
  { name: 'North building pavement', x: 0, z: -31.1, width: 72, depth: 3.6, back: 'wall', damp: true },
  { name: 'South building pavement', x: 0, z: 31.1, width: 72, depth: 3.6, back: 'wall' },
  { name: 'West building pavement', x: -34.2, z: 0, width: 2, depth: 66, back: 'wall', damp: true },
  { name: 'East building pavement', x: 34.2, z: 0, width: 2, depth: 66, back: 'wall' },
  { name: 'South Road shop frontage pavement', x: 0, z: 54.875, width: 72, depth: 1.75, back: 'wall', damp: true },
  { name: 'South Road opposite pavement', x: 18.5, z: 64, width: 75, depth: 1.5, back: 'wall', damp: true },
  // ABC Building: a wide Quay Street pavement under the canopy, and the
  // Lower Byrom Street footway along its east side.
  { name: 'ABC Quay Street pavement', x: -10.8, z: -60.95, width: 66.9, depth: 6, back: 'wall' },
  { name: 'ABC Lower Byrom Street pavement', x: 21.15, z: -89.975, width: 3, depth: 52.05, back: 'wall', damp: true },
  // Behind the north block (Renee, Gulliver's, MCR1, Nice Things), along the
  // Outer North Road's south kerb, between the outer west and east streets.
  { name: 'North block rear pavement', x: 4.5, z: -49.45, width: 97.5, depth: 2, back: 'wall', damp: true },
];

function addRoadAndPavementLayout(root: Group): void {
  // Damp ground and worn paving gather under the lamp heads, not the columns.
  const streetlights = PUBLIC_LIGHTS.map(({ emitter }) => ({ x: emitter.x, z: emitter.z }));
  const shopEntrances = WORLD_LOCATIONS
    .filter((location) => location.kind === 'building' && location.front)
    .map((location) => {
      switch (location.front) {
        case 'south': return { x: location.x, z: location.z + location.depth / 2 };
        case 'north': return { x: location.x, z: location.z - location.depth / 2 };
        case 'east': return { x: location.x + location.width / 2, z: location.z };
        default: return { x: location.x - location.width / 2, z: location.z };
      }
    });

  const roadIronwork = addRoadSurfaces(root, {
    roads: ROADS,
    crossings: CROSSINGS,
    kerbLines: [
      { name: 'Dreams worn double yellow kerb marking', x: -3, z: 29.02, length: 18, axis: 'x' },
      { name: 'Dreams worn double yellow kerb marking', x: -3, z: 28.76, length: 18, axis: 'x' },
      { name: 'South Road frontage double yellow', x: -13, z: 55.98, length: 22, axis: 'x' },
      { name: 'South Road frontage double yellow', x: -13, z: 56.24, length: 22, axis: 'x' },
    ],
    // Stretches dug up far more often than the rest: the North Road detail
    // view, the Dreams frontage and South Road.
    repairClusters: [
      { x: 2, z: -25.5, radius: 10, count: 8 },
      { x: -4, z: 25.8, radius: 9, count: 8 },
      { x: -3, z: 59.5, radius: 11, count: 7 },
    ],
    streetlights,
    drains: HERO_STREET_DRAIN_COVERS,
  });

  const pavementIronwork = addPavementSurfaces(root, {
    pavements: PAVEMENTS,
    roads: ROADS,
    crossings: CROSSINGS,
    streetlights,
    hotspots: [...BUS_STOPS, ...shopEntrances],
  });

  // Gullies, lane covers and footway covers share one instanced mesh.
  addRoadIronwork(root, [...roadIronwork, ...pavementIronwork]);

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

// Sterling bike nodes that must stay independently transformable for the later
// riding state (wheels spin, front wheel steers, crank and pedals turn).
const STERLING_ARTICULATED_NODES = new Set([
  'SB_FrontWheel',
  'SB_RearWheel',
  'SB_SteeringRoot',
  'SB_CrankRoot',
  'SB_Pedal_Left',
  'SB_Pedal_Right',
  'SB_Basket',
]);
// Must match DOCK_SPACING in blender/scripts/createSterlingBikeBlockout.py.
const STERLING_DOCK_SPACING = 0.94;
let sterlingTemplates: Promise<{ bike: Group; dock: Group }> | undefined;

function applySterlingBlockoutPolicy(model: Group): void {
  // Geometry-review blockout: keep the authored placeholder palette, but stop
  // lens and reflector placeholders reading as lit before the lighting pass.
  model.traverse((child) => {
    if (!(child instanceof Mesh)) {
      return;
    }
    const materials = Array.isArray(child.material)
      ? child.material
      : [child.material];
    for (const material of materials) {
      if (material instanceof MeshStandardMaterial) {
        material.emissive.set(0x000000);
        material.emissiveIntensity = 0;
        material.roughness = Math.max(material.roughness, 0.4);
      }
    }
  });
}

function flipTriangleWinding(geometry: BufferGeometry): void {
  for (const attribute of [geometry.getAttribute('position'), geometry.getAttribute('normal')]) {
    for (let vertex = 0; vertex + 2 < attribute.count; vertex += 3) {
      for (let component = 0; component < attribute.itemSize; component += 1) {
        const second = attribute.getComponent(vertex + 1, component);
        attribute.setComponent(vertex + 1, component, attribute.getComponent(vertex + 2, component));
        attribute.setComponent(vertex + 2, component, second);
      }
    }
  }
}

function mergeSterlingStaticParts(model: Group): void {
  // The blockout exports ~107 meshes per bike. Merge the meshes under each
  // articulated node (or the root) by material so a bike costs a couple of
  // dozen draw calls while its moving parts keep their authored pivots.
  model.updateMatrixWorld(true);
  const meshes: Mesh[] = [];
  model.traverse((child) => {
    if (child instanceof Mesh && !Array.isArray(child.material)) {
      meshes.push(child);
    }
  });

  const batches = new Map<Object3D, Map<Material, BufferGeometry[]>>();
  const toOwner = new Matrix4();
  for (const mesh of meshes) {
    let owner: Object3D = model;
    for (let ancestor = mesh.parent; ancestor && ancestor !== model; ancestor = ancestor.parent) {
      if (STERLING_ARTICULATED_NODES.has(ancestor.name)) {
        owner = ancestor;
        break;
      }
    }
    const geometry = mesh.geometry.index
      ? mesh.geometry.toNonIndexed()
      : mesh.geometry.clone();
    // Untextured placeholders: position and normal are all that must agree
    // for the geometries to merge.
    for (const name of Object.keys(geometry.attributes)) {
      if (name !== 'position' && name !== 'normal') {
        geometry.deleteAttribute(name);
      }
    }
    if (!geometry.getAttribute('normal')) {
      geometry.computeVertexNormals();
    }
    toOwner.copy(owner.matrixWorld).invert().multiply(mesh.matrixWorld);
    geometry.applyMatrix4(toOwner);
    if (toOwner.determinant() < 0) {
      flipTriangleWinding(geometry);
    }
    // Multi-material meshes were filtered out above.
    const material = mesh.material as Material;
    const byMaterial = batches.get(owner) ?? new Map<Material, BufferGeometry[]>();
    batches.set(owner, byMaterial);
    const geometries = byMaterial.get(material) ?? [];
    byMaterial.set(material, geometries);
    geometries.push(geometry);
  }

  for (const mesh of meshes) {
    for (const child of [...mesh.children]) {
      mesh.parent?.attach(child);
    }
    mesh.removeFromParent();
  }

  for (const [owner, byMaterial] of batches) {
    for (const [material, geometries] of byMaterial) {
      const merged = mergeGeometries(geometries);
      for (const geometry of merged ? [merged] : geometries) {
        const mesh = new Mesh(geometry, material);
        mesh.name = `${owner.name} ${material.name}`;
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        owner.add(mesh);
      }
    }
  }
  model.updateMatrixWorld(true);
}

function loadSterlingTemplates(): Promise<{ bike: Group; dock: Group }> {
  sterlingTemplates ??= Promise.all([
    loadModel('assets/models/sterling-bike/sterling-bike-blockout.glb?v=geometry-pass2-20260916'),
    loadModel('assets/models/sterling-bike/sterling-dock-blockout.glb?v=geometry-pass2-20260916'),
  ]).then(([bike, dock]) => {
    for (const model of [bike, dock]) {
      applySterlingBlockoutPolicy(model);
      mergeSterlingStaticParts(model);
    }
    return { bike, dock };
  });
  return sterlingTemplates;
}

/** Position of a named anchor in an unparented template's own coordinates. */
function sterlingAnchorPosition(template: Group, name: string): Vector3 {
  const anchor = template.getObjectByName(name);
  if (!anchor) {
    throw new Error(`Sterling Bikes asset is missing ${name}`);
  }
  return template.worldToLocal(anchor.getWorldPosition(new Vector3()));
}

function sterlingDockOffset(index: number, count: number): number {
  return (index - (count - 1) / 2) * STERLING_DOCK_SPACING;
}

function createSterlingStationFallback(marker: SterlingStationMarker): Group {
  const station = new Group();
  station.name = `${marker.name} loading placeholder`;
  marker.occupancy.forEach((_, index) => {
    const stand = createBox(0.32, 1.0, 0.3, 0xd2ad26);
    stand.position.set(0.15, 0.5, sterlingDockOffset(index, marker.occupancy.length));
    station.add(stand);
  });
  return station;
}

// Dock side post footprint in dock-local metres (Blender +Y imports as -Z).
const STERLING_DOCK_POST = { minX: -0.36, maxX: 0.31, minZ: -0.175, maxZ: -0.085, height: 0.82 };

async function replaceSterlingStationFallback(
  root: Group,
  fallback: Group,
  marker: SterlingStationMarker,
  fleet: SterlingFleet,
): Promise<void> {
  try {
    const { bike, dock } = await loadSterlingTemplates();
    // Snap with the authored anchors rather than an eyeballed offset: the
    // bike's SB_DockAnchor lands on the dock's SD_BikeDockAnchor, which puts
    // the front tyre in the wheel channel.
    const bikeOffset = sterlingAnchorPosition(dock, 'SD_BikeDockAnchor')
      .sub(sterlingAnchorPosition(bike, 'SB_DockAnchor'));
    const station = new Group();
    station.name = `${marker.name} Sterling Bikes geometry blockout`;
    station.position.copy(fallback.position);
    station.rotation.copy(fallback.rotation);
    marker.occupancy.forEach((occupied, index) => {
      // Docks and bikes are separate clones so game code can take a bike out
      // and leave a complete empty dock behind.
      const dockInstance = dock.clone(true);
      dockInstance.name = `${marker.name} dock ${index + 1}`;
      dockInstance.position.set(0, 0, sterlingDockOffset(index, marker.occupancy.length));
      station.add(dockInstance);
      if (!occupied) {
        return;
      }
      const bikeInstance = bike.clone(true);
      bikeInstance.name = `${marker.name} bike ${index + 1}`;
      bikeInstance.position.copy(dockInstance.position).add(bikeOffset);
      bikeInstance.userData.sterlingDockIndex = index;
      station.add(bikeInstance);
    });
    root.add(station);
    root.remove(fallback);
    station.updateMatrixWorld(true);

    // Bikes live in world space so they can be ridden away; docks stay put.
    marker.occupancy.forEach((occupied, index) => {
      const dockPosition = station.localToWorld(
        new Vector3(0, 0, sterlingDockOffset(index, marker.occupancy.length)).add(bikeOffset),
      );
      const dock = fleet.addDock(`${marker.id}-${index + 1}`, dockPosition, marker.rotationY);
      const bikeInstance = station.getObjectByName(`${marker.name} bike ${index + 1}`);
      if (!occupied || !bikeInstance) return;
      root.attach(bikeInstance);
      fleet.addBike(new SterlingBike(bikeInstance), bikeInstance.name, dock);
    });
  } catch (error) {
    markShelterLoadFailure(fallback, 'Sterling Bikes');
    console.error(
      '[World] Failed to load the Sterling Bikes blockout GLBs. Showing the magenta fallback.',
      error,
    );
  }
}

function addSterlingStation(
  root: Group,
  obstacles: CollisionObstacle[],
  marker: SterlingStationMarker,
  fleet: SterlingFleet,
): void {
  const fallback = createSterlingStationFallback(marker);
  // Stand on the pavement flags where there are any; East is on the car park.
  fallback.position.set(
    marker.x,
    pavementTopAt(PAVEMENTS, marker.x, marker.z) ?? CAR_PARK_SURFACE_TOP,
    marker.z,
  );
  fallback.rotation.y = marker.rotationY;
  root.add(fallback);
  void replaceSterlingStationFallback(root, fallback, marker, fleet);

  // Only the dock side posts are fixed. Each bike brings its own footprint
  // while it stands docked or parked, and none while it is being ridden.
  marker.occupancy.forEach((_, index) => {
    const offset = sterlingDockOffset(index, marker.occupancy.length);
    obstacles.push({
      ...rotatedObstacle(
        `${marker.name} dock ${index + 1} post`,
        marker.x,
        marker.z,
        marker.rotationY,
        STERLING_DOCK_POST.minX,
        STERLING_DOCK_POST.maxX,
        offset + STERLING_DOCK_POST.minZ,
        offset + STERLING_DOCK_POST.maxZ,
      ),
      height: STERLING_DOCK_POST.height,
      blocksCamera: false,
    });
  });
  addDevelopmentLabel(root, marker.name, marker.x, 1.8, marker.z);
}

function addUtilityBox(
  root: Group,
  obstacles: CollisionObstacle[],
  x: number,
  z: number,
  rotation = 0,
): void {
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
  obstacles.push(orientedBoxObstacle(box.name, x, z, 1.08, 0.48, rotation, 1.42));
}

function addShoppingTrolley(
  root: Group,
  obstacles: CollisionObstacle[],
  x: number,
  z: number,
  rotation = 0,
): void {
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
  // From the handle (local X -0.67) to the basket nose, across the 1.12 m frame.
  obstacles.push(orientedBoxObstacle(trolley.name, x, z, 1.3, 1.12, rotation, 1.3));
}

function addStreetDressing(root: Group, obstacles: CollisionObstacle[]): void {
  addHeroStreetEnvironmentKit(root, obstacles);
  addShoppingTrolley(root, obstacles, 31.9, 20.9, -0.74);
  addShoppingTrolley(root, obstacles, -7.1, -30.1, 0.22);
  addUtilityBox(root, obstacles, -34.7, -11.7, Math.PI / 2);
  addUtilityBox(root, obstacles, 34.5, 6.4, -Math.PI / 2);
  addUtilityBox(root, obstacles, 25.6, 31.2, Math.PI);
  addUtilityBox(root, obstacles, 8.15, -30.25, Math.PI);

  // Offsets were authored with Bus Stop A at (-9, 20.4); anchoring them to the
  // marker keeps the spill under the shelter when the stop moves.
  const busStopA = BUS_STOPS[0];
  addReflectionPatch(root, 'Bus shelter magenta spill', busStopA.x + 0.8, busStopA.z + 1.8, 1.1, 4.8, VISUAL_STYLE.lighting.magenta, 0.3, -0.12);
  addReflectionPatch(root, 'Bus shelter green spill', busStopA.x - 1.2, busStopA.z + 1.0, 0.8, 3.1, VISUAL_STYLE.lighting.fluorescent, 0.2, 0.15);
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
  addReflectionPatch(root, 'Advanced Photo fascia spill', 12.1, 62, 3.8, 0.7, VISUAL_STYLE.lighting.coldWhite, 0.16, -0.04);
}

function addStreetlightPool(
  root: Group,
  x: number,
  z: number,
  color: number = VISUAL_STYLE.lighting.sodium,
): void {
  // The fixture itself is a GLB (createStreetlights.ts). This is only its
  // light on the ground, centred under the lantern.
  const lamp = new Group();
  lamp.name = 'Public illumination pool';
  lamp.position.set(x, 0, z);
  const pool = new Mesh(
    getCircleGeometry(STREETLIGHT_POOL_RADIUS, 16),
    createAdditiveWorldMaterial('reflection-broken-overhaul', color, 0.23),
  );
  pool.name = 'Streetlight painted pool';
  pool.rotation.x = -Math.PI / 2;
  pool.position.y = 0.035;
  lamp.add(pool);

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

function addHeroLocalLights(localLights: LocalLightRegistry): void {
  type HeroLightDefinition = readonly [
    name: string,
    x: number,
    y: number,
    z: number,
    color: number,
    intensity: number,
    distance: number,
    activationRadius: number,
    priority?: number,
  ];

  // Dreams faces north, away from the moonlight, so this is its frontage's only
  // real light. Centre it on the plot, just proud of the fascia and signboard.
  const dreams = WORLD_LOCATIONS.find((location) => location.id === 'dreams');
  const dreamsFrontX = dreams?.x ?? -3;
  const dreamsFrontZ = dreams ? dreams.z - dreams.depth / 2 - 1.8 : 33.2;

  const definitions: HeroLightDefinition[] = [
    ['Bus Stop A hero light', BUS_STOPS[0].x, 2.35, BUS_STOPS[0].z, 0xb9ffe7, 8, 8, 18, 1.1],
    ['Dreams hero light', dreamsFrontX, 4.2, dreamsFrontZ, VISUAL_STYLE.lighting.coldWhite, 9, 13, 18, 1.05],
    ['Renee hero light', 17, 2.5, -30.8, VISUAL_STYLE.lighting.magenta, 7, 9, 15],
    ['Florist hero light', -16.9, 2.7, -27, VISUAL_STYLE.lighting.sodium, 7.5, 9, 15],
    ['Bus Stop B hero light', BUS_STOPS[1].x, 2.35, BUS_STOPS[1].z, 0xb9ffe7, 8, 8, 16, 1.1],
  ];

  for (const [name, x, y, z, color, intensity, distance, activationRadius, priority] of definitions) {
    localLights.register({
      name,
      lights: [
        createManagedPointLight(name, x, y, z, color, intensity, distance),
      ],
      priority,
      selectionMode: 'location-relevance',
      activationRadius,
    });
  }

  const cassArt = WORLD_LOCATIONS.find((location) => location.id === 'cass-art');
  if (cassArt) {
    const scale = cassArt.width / 18;
    const modelOriginZ = cassArt.z - cassArt.depth / 2;
    const cassLightAt = (
      name: string,
      localX: number,
      localDepth: number,
      localHeight: number,
      intensity: number,
      distance: number,
    ) => createManagedPointLight(
      name,
      cassArt.x - localX * scale,
      localHeight * scale,
      modelOriginZ + localDepth * scale,
      0xffcf91,
      intensity,
      distance,
    );

    // The model is rotated 180 degrees at runtime: authored +X becomes world
    // -X, while authored interior depth (+Y) extends south in world +Z.
    localLights.register({
      name: 'Cass Art window',
      lights: [cassLightAt('Cass Art window fill', 0, 0.65, 3.68, 7, 7)],
      priority: 1.1,
      selectionMode: 'location-relevance',
      activationRadius: 14,
    });
    localLights.register({
      name: 'Cass Art ceiling-track pair',
      lights: [
        cassLightAt('Cass Art interior track east', -2.1, 5.75, 4.02, 9, 8),
        cassLightAt('Cass Art interior track west', 1.9, 5.75, 4.02, 9, 8),
      ],
      selectionMode: 'location-relevance',
      activationRadius: 14,
    });
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
    const realCameraLightAt = (
      name: string,
      authoredX: number,
      authoredY: number,
      height: number,
      color: number,
      intensity: number,
      distance: number,
    ) => createManagedPointLight(
      name,
      worldX(authoredX),
      height,
      worldZ(authoredY),
      color,
      intensity,
      distance,
    );

    // Sodium wash on the hero shopfront, sitting proud of the facade so the
    // awning, hanging sign and stone piers catch it rather than one flat wall.
    localLights.register({
      name: 'Real Camera shopfront',
      lights: [realCameraLightAt('Real Camera shopfront', 0.05, -6.4, 3.7, VISUAL_STYLE.lighting.sodium, 7, 10)],
      priority: 1.1,
      selectionMode: 'location-relevance',
      activationRadius: 16,
    });
    // The two interior fluorescents remain paired so LOW never lights one side
    // of the display and leaves the other side accidentally black.
    localLights.register({
      name: 'Real Camera interior pair',
      lights: [
        realCameraLightAt('Real Camera interior west', -4.55, -1.55, 3.3, VISUAL_STYLE.lighting.fluorescent, 5, 7),
        realCameraLightAt('Real Camera interior east', -0.2, -1.55, 3.3, VISUAL_STYLE.lighting.fluorescent, 5, 7),
      ],
      selectionMode: 'location-relevance',
      activationRadius: 14,
    });
  }

  const advancedPhoto = WORLD_LOCATIONS.find(
    (location) => location.id === 'advanced-photo',
  );
  if (advancedPhoto) {
    // Authored points transformed by the 180-degree north-facing placement:
    // world X = plot X - Blender X, world Z = plot Z + Blender Y.
    localLights.register({
      name: 'Advanced Photo interior',
      lights: [
        createManagedPointLight(
          'Advanced Photo interior',
          advancedPhoto.x,
          2.45,
          advancedPhoto.z + 0.15,
          VISUAL_STYLE.lighting.fluorescent,
          5.4,
          7,
        ),
      ],
      // Spice Cabin faces this shop across South Road and its three lights fill
      // the MEDIUM budget alongside the arcade ring, which left the interior
      // unlit from the road. 1.3 wins over the gable wash only when looking at
      // Advanced Photo; from Spice Cabin's own pavement the selection is
      // unchanged.
      priority: 1.3,
      selectionMode: 'location-relevance',
      activationRadius: 13,
    });
    localLights.register({
      name: 'Advanced Photo arcade ring',
      lights: [
        createManagedPointLight(
          'Advanced Photo arcade ring',
          advancedPhoto.x - 0.55,
          3.35,
          advancedPhoto.z - 4.88,
          0xffd695,
          4.2,
          6,
        ),
      ],
      priority: 1.1,
      selectionMode: 'location-relevance',
      activationRadius: 11,
    });
  }
}

function addPublicIlluminationResponse(
  localLights: LocalLightRegistry,
): (playerPosition: Vector3) => void {
  const first = PUBLIC_LIGHTS[0];
  const light = createManagedPointLight(
    'Nearest public streetlight response',
    first.emitter.x,
    first.emitter.y,
    first.emitter.z,
    first.color,
    VISUAL_STYLE.lighting.streetLightIntensity,
    VISUAL_STYLE.lighting.streetLightDistance,
  );
  let proximityScale = 0;
  localLights.register({
    name: 'Public illumination pool',
    lights: [light],
    priority: 1.7,
    activationRadius: 5,
    intensityScale: () => proximityScale,
  });

  return (playerPosition: Vector3): void => {
    let nearest = first;
    let nearestDistanceSquared = Number.POSITIVE_INFINITY;
    for (const candidate of PUBLIC_LIGHTS) {
      const deltaX = candidate.emitter.x - playerPosition.x;
      const deltaZ = candidate.emitter.z - playerPosition.z;
      const distanceSquared = deltaX * deltaX + deltaZ * deltaZ;
      if (distanceSquared < nearestDistanceSquared) {
        nearest = candidate;
        nearestDistanceSquared = distanceSquared;
      }
    }

    // The proxy sits at the lantern's real emitter, eight metres up.
    light.position.set(nearest.emitter.x, nearest.emitter.y, nearest.emitter.z);
    light.color.setHex(nearest.color);

    // Full across the painted pool, then zero before the surrounding
    // darkness. The pool remains the compositional layer; this proxy merely
    // lets it affect real materials.
    const distance = Math.sqrt(nearestDistanceSquared);
    const fadeStart = STREETLIGHT_POOL_RADIUS + 0.1;
    const fadeEnd = STREETLIGHT_POOL_RADIUS + 1.6;
    const fade = Math.max(
      0,
      Math.min(1, (fadeEnd - distance) / (fadeEnd - fadeStart)),
    );
    proximityScale = fade * fade * (3 - 2 * fade);
  };
}

export function createWorld(scene: Scene, maximumActiveLocalLights: number): World {
  const atmosphere = createNightAtmosphere(scene);
  const root = new Group();
  root.name = 'Canonical city layout Map v0.3';
  scene.add(root);
  const localLights = new LocalLightRegistry(
    root,
    maximumActiveLocalLights,
  );
  addEnvironmentSurface(
    root,
    'World ground',
    0,
    -19,
    128,
    194,
    'concrete-cracked-overhaul',
    -0.12,
    5,
  );
  addRoadAndPavementLayout(root);
  const obstacles: CollisionObstacle[] = [];
  addCentralPark(root, obstacles);
  const updatePickup = addDevelopmentPickup(root);

  for (const location of WORLD_LOCATIONS) {
    if (location.kind === 'building') {
      addBuildingLocation(root, obstacles, location, localLights);
    } else if (location.kind === 'car-park') {
      addCarPark(root, location);
    }
  }

  addBusShelter(root, obstacles, BUS_STOPS[0], -Math.PI / 2);
  addBusShelter(root, obstacles, BUS_STOPS[1], -Math.PI / 2);
  for (const marker of FOOD_STANDS) {
    addGreekGyros(root, obstacles, marker, localLights);
  }
  for (const marker of PALLET_STACKS) {
    void addPalletStack(root, marker);
    addPalletStackCollision(obstacles, marker);
  }
  void addBougainvilleaFenceScene(root, palletGroundAt);
  addBougainvilleaFenceCollision(obstacles);
  addBougainvilleaSignLamp(localLights);
  for (const marker of SPECTER_GRAFFITI) {
    addSpecterGraffiti(root, marker);
  }
  addStreetDressing(root, obstacles);
  const sterlingFleet = new SterlingFleet(obstacles);
  for (const marker of STERLING_BIKE_DOCKS) {
    addSterlingStation(root, obstacles, marker, sterlingFleet);
  }
  for (const marker of FUTURE_EXITS) {
    addDevelopmentLabel(root, `${marker.name} →`, marker.x, 2.2, marker.z);
  }

  for (const light of PUBLIC_LIGHTS) {
    addStreetlightPool(root, light.emitter.x, light.emitter.z, light.color);
    obstacles.push(
      circleObstacle('Streetlight column', light.x, light.z, 0.11, STREETLIGHT_MODELS[light.model].height),
    );
  }
  void addStreetlightFixtures(root, PUBLIC_LIGHTS);

  if (import.meta.env.DEV) {
    root.add(createCollisionDebugOutlines(obstacles));
  }

  addHeroLocalLights(localLights);
  const updatePublicIllumination = addPublicIlluminationResponse(localLights);

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
    sterlingFleet,
    atmosphere,
    update: (deltaTime, playerPosition) => {
      atmosphere.update(deltaTime);
      updatePickup(deltaTime);
      updatePublicIllumination(playerPosition);
      localLights.update(deltaTime, playerPosition);
    },
    getLightingStats: () => ({
      ...localLights.getStats(),
      activeSpotLights: 0,
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
