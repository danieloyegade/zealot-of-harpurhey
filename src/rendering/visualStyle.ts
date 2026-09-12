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
  /**
   * Multisample count for the composer's render target. The renderer's own
   * `antialias` flag only affects the default framebuffer, which is never
   * drawn to once every frame goes through EffectComposer. Zero disables MSAA.
   */
  readonly msaaSamples: number;
  /**
   * Shadow map resolution for the single shadow-casting moonlight. Zero
   * disables shadow casting entirely for the profile.
   */
  readonly shadowMapSize: number;
}

export const QUALITY_PROFILES: Record<QualityLevel, QualityProfile> = {
  low: {
    level: 'low',
    renderScale: 0.65,
    maximumDevicePixelRatio: 1,
    bloomEnabled: false,
    bloomStrength: 0,
    maximumActiveLocalLights: 2,
    msaaSamples: 0,
    shadowMapSize: 0,
  },
  medium: {
    level: 'medium',
    renderScale: 0.72,
    maximumDevicePixelRatio: 1.25,
    bloomEnabled: true,
    bloomStrength: 0.3,
    maximumActiveLocalLights: 4,
    msaaSamples: 4,
    shadowMapSize: 1024,
  },
  high: {
    level: 'high',
    renderScale: 0.8,
    maximumDevicePixelRatio: 1.5,
    bloomEnabled: true,
    bloomStrength: 0.34,
    maximumActiveLocalLights: 5,
    msaaSamples: 4,
    shadowMapSize: 2048,
  },
};

export const DEFAULT_QUALITY_LEVEL: QualityLevel = 'medium';

export const VISUAL_STYLE = {
  render: {
    exposure: 1.34,
    saturation: 1.12,
    contrast: 1.05,
    // Zero disables quantisation. The 32-level banding was part of the
    // abandoned Dreamcast-era target; smooth gradients serve the current
    // "uncanny realism" direction. Dither and grain still carry the texture.
    colorQuantizationLevels: 0,
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
    shadowsEnabled: true,
  },
  /**
   * A single shadow-casting directional moonlight. Its orthographic camera
   * follows the player rather than spanning the whole 128 m world, so a modest
   * map size still resolves architectural edges.
   */
  shadow: {
    /**
     * Distance the light is pushed back along its own direction. The lighting
     * result is unchanged (a directional light only cares about direction) but
     * the shadow camera then sits above even the 33 m Arts Council mass
     * instead of clipping it against the near plane.
     */
    followDistance: 90,
    /** Half-extent of the orthographic shadow camera, in metres. */
    extent: 40,
    near: 1,
    far: 200,
    bias: -0.0012,
    normalBias: 0.05,
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
