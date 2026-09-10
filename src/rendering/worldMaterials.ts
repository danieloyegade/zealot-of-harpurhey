import {
  AdditiveBlending,
  ClampToEdgeWrapping,
  DoubleSide,
  MeshBasicMaterial,
  MeshStandardMaterial,
  RepeatWrapping,
  SRGBColorSpace,
  TextureLoader,
  type Material,
} from 'three';
import { applyTextureProfile, VISUAL_STYLE, type TextureProfile } from './visualStyle';

export type WorldTextureName =
  | 'asphalt-dark-temporary'
  | 'pavement-worn-temporary'
  | 'pavement-damp-temporary'
  | 'brick-red-temporary'
  | 'brick-brown-temporary'
  | 'masonry-alley-temporary'
  | 'concrete-stained-temporary'
  | 'painted-metal-temporary'
  | 'shop-shutter-temporary'
  | 'window-dark-temporary'
  | 'window-lit-temporary'
  | 'grass-cheap-temporary'
  | 'foliage-rough-temporary'
  | 'tree-bark-temporary'
  | 'asphalt-wet-overhaul'
  | 'pavement-weathered-overhaul'
  | 'pavement-wet-overhaul'
  | 'brick-soot-overhaul'
  | 'brick-painted-overhaul'
  | 'concrete-cracked-overhaul'
  | 'shutter-grimy-overhaul'
  | 'metal-oxidised-overhaul'
  | 'grass-damp-overhaul'
  | 'foliage-dark-overhaul'
  | 'reflection-broken-overhaul'
  | 'light-cone-noise-overhaul'
  | 'poster-wall-overhaul'
  | 'window-row-overhaul'
  | 'dreams-photo-overhaul'
  | 'coral-photo-overhaul';

const loader = new TextureLoader();
const materialCache = new Map<string, Material>();

export interface WorldMaterialOptions {
  readonly repeatX?: number;
  readonly repeatY?: number;
  readonly profile?: TextureProfile;
  readonly tint?: number;
  readonly emissive?: number;
  readonly emissiveIntensity?: number;
  readonly basic?: boolean;
  readonly roughness?: number;
  readonly metalness?: number;
  readonly opacity?: number;
  readonly transparent?: boolean;
  readonly clamp?: boolean;
}

function textureUrl(name: WorldTextureName): string {
  return `${import.meta.env.BASE_URL}assets/textures/world-prototype/${name}.png`;
}

export function createWorldMaterial(
  name: WorldTextureName,
  options: WorldMaterialOptions = {},
): Material {
  const {
    repeatX = 1,
    repeatY = 1,
    profile = 'PHOTO_ENVIRONMENT',
    tint = 0xffffff,
    emissive = 0x000000,
    emissiveIntensity = 0,
    basic = false,
    roughness = 0.96,
    metalness = 0,
    opacity = 1,
    transparent = opacity < 1,
    clamp = false,
  } = options;
  const key = [
    name,
    repeatX,
    repeatY,
    profile,
    tint,
    emissive,
    emissiveIntensity,
    basic,
    roughness,
    metalness,
    opacity,
    transparent,
    clamp,
  ].join(':');
  const existing = materialCache.get(key);
  if (existing) {
    return existing;
  }

  const texture = loader.load(textureUrl(name));
  texture.name = name;
  texture.colorSpace = SRGBColorSpace;
  texture.wrapS = clamp ? ClampToEdgeWrapping : RepeatWrapping;
  texture.wrapT = clamp ? ClampToEdgeWrapping : RepeatWrapping;
  texture.repeat.set(repeatX, repeatY);
  applyTextureProfile(texture, profile);

  const material = basic
    ? new MeshBasicMaterial({ map: texture, color: tint, opacity, transparent })
    : new MeshStandardMaterial({
        map: texture,
        color: tint,
        emissive,
        emissiveMap: emissiveIntensity > 0 ? texture : null,
        emissiveIntensity:
          emissiveIntensity * VISUAL_STYLE.lighting.emissiveMultiplier,
        flatShading: VISUAL_STYLE.geometry.facetedLighting,
        metalness,
        roughness,
        opacity,
        transparent,
      });
  material.name = `${name} material`;
  materialCache.set(key, material);
  return material;
}

export function createEmissiveWorldMaterial(
  name: WorldTextureName,
  tint: number,
  emissive: number,
  profile: TextureProfile = 'PHOTO_ENVIRONMENT',
): MeshStandardMaterial {
  const key = `${name}:emissive:${tint}:${emissive}:${profile}`;
  const existing = materialCache.get(key);
  if (existing instanceof MeshStandardMaterial) {
    return existing;
  }

  const source = createWorldMaterial(name, {
    profile,
    tint,
    emissive,
    emissiveIntensity: 1,
  });
  if (!(source instanceof MeshStandardMaterial)) {
    throw new Error(`Expected a standard material for ${name}.`);
  }
  const material = source.clone();
  material.name = `${name} emissive material`;
  materialCache.set(key, material);
  return material;
}

export function createHaloMaterial(color: number, opacity: number): MeshBasicMaterial {
  return new MeshBasicMaterial({
    color,
    transparent: true,
    opacity,
    depthWrite: false,
    side: DoubleSide,
    blending: AdditiveBlending,
  });
}

export function createAdditiveWorldMaterial(
  name: WorldTextureName,
  color: number,
  opacity: number,
  repeatX = 1,
  repeatY = 1,
): MeshBasicMaterial {
  const key = `${name}:additive:${color}:${opacity}:${repeatX}:${repeatY}`;
  const existing = materialCache.get(key);
  if (existing instanceof MeshBasicMaterial) {
    return existing;
  }

  const source = createWorldMaterial(name, {
    basic: true,
    tint: color,
    repeatX,
    repeatY,
  });
  if (!(source instanceof MeshBasicMaterial)) {
    throw new Error(`Expected a basic material for ${name}.`);
  }
  const material = source.clone();
  material.name = `${name} additive material`;
  material.blending = AdditiveBlending;
  material.transparent = true;
  material.opacity = opacity;
  material.depthWrite = false;
  material.side = DoubleSide;
  materialCache.set(key, material);
  return material;
}
