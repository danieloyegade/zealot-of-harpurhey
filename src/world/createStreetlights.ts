import {
  Color,
  Group,
  LOD,
  type Material,
  Mesh,
  MeshStandardMaterial,
  type Object3D,
  type Texture,
  Vector3,
} from 'three';
import { applyTextureProfile } from '../rendering/visualStyle';
import { loadModel } from './loadModel';
import { mergeStaticModelMeshes } from './mergeStaticModelMeshes';

// The municipal streetlight family (blender/scripts/createStreetlights.py).
// The GLBs are the physical fixtures only. Each lamp's light is the game's
// business: the painted pool, the managed public-light proxy, and the
// emissive recolouring here. Only the emitter, the bowl, the reflector and a
// baked spill mask on the housing underside take the lamp's colour; the
// column and casing stay unlit metal.

export type StreetlightModel = 'warm-old' | 'led-modern' | 'curved' | 'weathered';

interface StreetlightModelInfo {
  readonly file: string;
  /**
   * `LightEmitter` in the model's own frame (overhang along +X, metres).
   * Mirrors the GLB so pools and the light proxy can be placed before the
   * model has loaded; a mismatch is reported once the GLB arrives.
   */
  readonly emitter: { readonly x: number; readonly y: number; readonly z: number };
  readonly height: number;
}

export const STREETLIGHT_MODELS: Readonly<Record<StreetlightModel, StreetlightModelInfo>> = {
  'warm-old': {
    file: 'assets/models/streetlight-warm-old-01.glb',
    emitter: { x: 1.015, y: 7.624, z: 0.005 },
    height: 7.8,
  },
  'led-modern': {
    file: 'assets/models/streetlight-led-modern-01.glb',
    emitter: { x: 0.997, y: 7.796, z: 0 },
    height: 7.8,
  },
  curved: {
    file: 'assets/models/streetlight-curved-01.glb',
    emitter: { x: 1.172, y: 6.586, z: -0.038 },
    height: 6.7,
  },
  weathered: {
    file: 'assets/models/streetlight-weathered-01.glb',
    emitter: { x: 1.406, y: 7.667, z: -0.019 },
    height: 7.7,
  },
};

// Council batches: close lamps use the full fixture, mid-distance ones lose
// bolts, welds and the lens array, far ones are a few hundred triangles.
const LOD_DISTANCES = [0, 26, 60] as const;

const EMITTER_INTENSITY = 3.2;
const GLASS_INTENSITY = 0.55;
const REFLECTOR_INTENSITY = 0.3;
const SPILL_INTENSITY = 0.85;

export interface StreetlightPlacement {
  readonly name: string;
  readonly x: number;
  readonly z: number;
  /** Rotation about Y; 0 points the lantern along world +X. */
  readonly yaw: number;
  readonly model: StreetlightModel;
  readonly color: number;
}

export interface StreetlightEmitterPoint {
  readonly x: number;
  readonly y: number;
  readonly z: number;
}

export function streetlightEmitterWorld(
  placement: Pick<StreetlightPlacement, 'x' | 'z' | 'yaw' | 'model'>,
): StreetlightEmitterPoint {
  const offset = STREETLIGHT_MODELS[placement.model].emitter;
  const cos = Math.cos(placement.yaw);
  const sin = Math.sin(placement.yaw);
  return {
    x: placement.x + offset.x * cos + offset.z * sin,
    y: offset.y,
    z: placement.z - offset.x * sin + offset.z * cos,
  };
}

interface Template {
  readonly levels: Object3D[];
  readonly emitterCheck: Object3D | undefined;
}

const templates = new Map<StreetlightModel, Promise<Template>>();
const variants = new Map<string, Promise<Group[]>>();
const recoloured = new Map<string, Material>();

function loadTemplate(model: StreetlightModel): Promise<Template> {
  let template = templates.get(model);
  if (!template) {
    template = loadModel(STREETLIGHT_MODELS[model].file).then((scene) => {
      scene.updateMatrixWorld(true);
      const levels = LOD_DISTANCES.map((_, level) => {
        const node = scene.getObjectByName(`LOD${level}`);
        if (!node) {
          throw new Error(`${STREETLIGHT_MODELS[model].file} has no LOD${level}`);
        }
        return node;
      });
      const emitterCheck = scene.getObjectByName('LightEmitter');
      const expected = STREETLIGHT_MODELS[model].emitter;
      if (
        emitterCheck &&
        emitterCheck.position.distanceTo(new Vector3(expected.x, expected.y, expected.z)) > 0.05
      ) {
        console.warn(
          `Streetlight ${model}: LightEmitter is at ${emitterCheck.position.toArray().map((v) => v.toFixed(3))},` +
            ' STREETLIGHT_MODELS is out of date.',
        );
      }
      scene.traverse((child) => {
        if (!(child instanceof Mesh)) {
          return;
        }
        for (const material of Array.isArray(child.material) ? child.material : [child.material]) {
          if (material instanceof MeshStandardMaterial) {
            for (const texture of [material.map, material.normalMap, material.roughnessMap, material.emissiveMap]) {
              if (texture) {
                applyTextureProfile(texture as Texture, 'PHOTO_ENVIRONMENT');
              }
            }
          }
        }
      });
      return { levels, emitterCheck };
    });
    templates.set(model, template);
  }
  return template;
}

function lampMaterial(source: Material, color: number): Material {
  if (!(source instanceof MeshStandardMaterial)) {
    return source;
  }
  const name = source.name;
  let intensity = 0;
  if (name.startsWith('SL_Emitter')) {
    intensity = EMITTER_INTENSITY;
  } else if (name.startsWith('SL_Glass_Prismatic')) {
    intensity = GLASS_INTENSITY;
  } else if (name.startsWith('SL_Reflector')) {
    intensity = REFLECTOR_INTENSITY;
  } else if (name.includes('_Body') && source.emissiveMap) {
    intensity = SPILL_INTENSITY;
  } else {
    return source;
  }
  const key = `${source.uuid}:${color}`;
  let material = recoloured.get(key);
  if (!material) {
    const clone = source.clone();
    clone.emissive = new Color(color);
    clone.emissiveIntensity = intensity;
    if (name.startsWith('SL_Emitter')) {
      clone.color = new Color(color);
    }
    if (clone.transparent) {
      clone.depthWrite = false;
    }
    material = clone;
    recoloured.set(key, material);
  }
  return material;
}

function variantLevels(model: StreetlightModel, color: number): Promise<Group[]> {
  const key = `${model}:${color}`;
  let levels = variants.get(key);
  if (!levels) {
    levels = loadTemplate(model).then((template) =>
      template.levels.map((source, level) => {
        const group = new Group();
        group.name = `${model} streetlight LOD${level}`;
        // Copy the list: add() reparents, which shrinks the clone's children.
        for (const child of [...source.clone(true).children]) {
          group.add(child);
        }
        group.traverse((child) => {
          if (child instanceof Mesh) {
            child.material = Array.isArray(child.material)
              ? child.material.map((material) => lampMaterial(material, color))
              : lampMaterial(child.material, color);
          }
        });
        mergeStaticModelMeshes(group);
        return group;
      }),
    );
    variants.set(key, levels);
  }
  return levels;
}

export async function createStreetlightFixture(placement: StreetlightPlacement): Promise<LOD> {
  const levels = await variantLevels(placement.model, placement.color);
  const lod = new LOD();
  lod.name = placement.name;
  levels.forEach((level, index) => lod.addLevel(level.clone(), LOD_DISTANCES[index]));
  lod.position.set(placement.x, 0, placement.z);
  lod.rotation.y = placement.yaw;
  lod.updateMatrix();
  lod.matrixAutoUpdate = false;
  return lod;
}

export async function addStreetlightFixtures(
  root: Group,
  placements: readonly StreetlightPlacement[],
): Promise<void> {
  const fixtures = await Promise.allSettled(placements.map(createStreetlightFixture));
  for (const result of fixtures) {
    if (result.status === 'fulfilled') {
      root.add(result.value);
    } else {
      console.warn('Streetlight fixture failed to load', result.reason);
    }
  }
}
