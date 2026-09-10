import {
  LinearFilter,
  LinearMipmapLinearFilter,
  NearestFilter,
  NearestMipmapNearestFilter,
  type Texture,
  type WebGLRenderer,
} from 'three';

export type TextureProfile = 'PHOTO_ENVIRONMENT' | 'RETRO_GRAPHIC';

export const VISUAL_STYLE = {
  render: {
    internalScale: 0.72,
    maximumDevicePixelRatio: 2,
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
    enabled: true,
    strength: 0.34,
    radius: 0.32,
    threshold: 0.88,
  },
} as const;

export function applyInternalResolution(
  renderer: WebGLRenderer,
  width: number,
  height: number,
): void {
  const displayPixelRatio = Math.min(
    window.devicePixelRatio,
    VISUAL_STYLE.render.maximumDevicePixelRatio,
  );
  renderer.setPixelRatio(displayPixelRatio * VISUAL_STYLE.render.internalScale);
  renderer.setSize(width, height);
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
