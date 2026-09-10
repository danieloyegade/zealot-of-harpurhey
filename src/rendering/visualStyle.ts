import {
  LinearFilter,
  LinearMipmapLinearFilter,
  NearestFilter,
  NearestMipmapNearestFilter,
  type Texture,
  type WebGLRenderer,
} from 'three';

export type TextureProfile = 'PHOTO_ENVIRONMENT' | 'RETRO_GRAPHIC';
export type QualityLevel = 'low' | 'medium' | 'high';

export interface QualityProfile {
  readonly level: QualityLevel;
  readonly renderScale: number;
  readonly maximumDevicePixelRatio: number;
  readonly bloomEnabled: boolean;
  readonly bloomStrength: number;
  readonly maximumActiveLocalLights: number;
}

export const QUALITY_PROFILES: Record<QualityLevel, QualityProfile> = {
  low: {
    level: 'low',
    renderScale: 0.65,
    maximumDevicePixelRatio: 1,
    bloomEnabled: false,
    bloomStrength: 0,
    maximumActiveLocalLights: 2,
  },
  medium: {
    level: 'medium',
    renderScale: 0.72,
    maximumDevicePixelRatio: 1.25,
    bloomEnabled: true,
    bloomStrength: 0.3,
    maximumActiveLocalLights: 4,
  },
  high: {
    level: 'high',
    renderScale: 0.8,
    maximumDevicePixelRatio: 1.5,
    bloomEnabled: true,
    bloomStrength: 0.34,
    maximumActiveLocalLights: 5,
  },
};

export const DEFAULT_QUALITY_LEVEL: QualityLevel = 'medium';

export const VISUAL_STYLE = {
  render: {
    exposure: 1.34,
    saturation: 1.12,
    contrast: 1.05,
    colorQuantizationLevels: 32,
    ditherStrength: 0.003,
    grainStrength: 0.042,
    vignetteStrength: 0.2,
    vignetteSoftness: 0.34,
  },
  texture: {
    photoAnisotropy: 2,
    graphicAnisotropy: 1,
  },
  sky: {
    color: 0x071c5a,
    horizonColor: 0x020817,
    starColor: 0xdce5ff,
    starCount: 320,
  },
  fog: {
    color: 0x07133b,
    near: 44,
    far: 108,
  },
  lighting: {
    ambientSky: 0x304e9b,
    ambientGround: 0x090b10,
    ambientIntensity: 0.72,
    moonColor: 0x8aa3d8,
    moonIntensity: 1.28,
    sodium: 0xffa326,
    fluorescent: 0x70ff9b,
    magenta: 0xff3a9c,
    coldWhite: 0xc4dcff,
    streetLightIntensity: 30,
    streetLightDistance: 14,
    emissiveMultiplier: 1.15,
  },
  geometry: {
    facetedLighting: true,
    shadowsEnabled: false,
    shadowMapSize: 512,
  },
  bloom: {
    radius: 0.32,
    threshold: 0.88,
  },
} as const;

export function applyInternalResolution(
  renderer: WebGLRenderer,
  width: number,
  height: number,
  quality: QualityProfile,
): void {
  const displayPixelRatio = Math.min(
    window.devicePixelRatio,
    quality.maximumDevicePixelRatio,
  );
  renderer.setPixelRatio(displayPixelRatio * quality.renderScale);
  renderer.setSize(width, height);
}

export function resolveQualityProfile(search: string): QualityProfile {
  const requested = new URLSearchParams(search).get('quality')?.toLowerCase();
  if (requested === 'low' || requested === 'medium' || requested === 'high') {
    return QUALITY_PROFILES[requested];
  }
  return QUALITY_PROFILES[DEFAULT_QUALITY_LEVEL];
}

export function applyTextureProfile(
  texture: Texture,
  profile: TextureProfile,
  renderer?: WebGLRenderer,
): Texture {
  if (profile === 'PHOTO_ENVIRONMENT') {
    texture.magFilter = LinearFilter;
    texture.minFilter = LinearMipmapLinearFilter;
    texture.anisotropy = renderer
      ? Math.min(
          VISUAL_STYLE.texture.photoAnisotropy,
          renderer.capabilities.getMaxAnisotropy(),
        )
      : VISUAL_STYLE.texture.photoAnisotropy;
  } else {
    texture.magFilter = NearestFilter;
    texture.minFilter = NearestMipmapNearestFilter;
    texture.anisotropy = VISUAL_STYLE.texture.graphicAnisotropy;
  }
  if (texture.image != null) {
    texture.needsUpdate = true;
  }
  return texture;
}
