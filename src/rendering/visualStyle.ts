import {
  ACESFilmicToneMapping,
  AgXToneMapping,
  LinearFilter,
  LinearMipmapLinearFilter,
  NeutralToneMapping,
  NoToneMapping,
  type Texture,
  type ToneMapping,
  type WebGLRenderer,
} from 'three';

export type TextureProfile = 'PHOTO_ENVIRONMENT' | 'RETRO_GRAPHIC';
export type QualityLevel = 'low' | 'medium' | 'high';
export type ToneMappingName = 'off' | 'agx' | 'neutral' | 'aces';

export interface ToneMappingProfile {
  readonly name: ToneMappingName;
  readonly curve: ToneMapping;
  readonly exposure: number;
}

export interface QualityProfile {
  readonly level: QualityLevel;
  readonly renderScale: number;
  readonly maximumDevicePixelRatio: number;
  readonly bloomEnabled: boolean;
  readonly bloomStrength: number;
  readonly maximumActiveLocalLights: number;
  // Post-process edge antialiasing (SMAA). The render-target chain that
  // EffectComposer draws into does not receive the canvas's own MSAA
  // (`antialias: true` on WebGLRenderer only affects the default backbuffer),
  // so thin geometry (railings, cables, kerbs) shimmers at the reduced
  // renderScale without this.
  readonly smaaEnabled: boolean;
}

export const QUALITY_PROFILES: Record<QualityLevel, QualityProfile> = {
  low: {
    level: 'low',
    renderScale: 0.65,
    maximumDevicePixelRatio: 1,
    bloomEnabled: false,
    bloomStrength: 0,
    maximumActiveLocalLights: 2,
    smaaEnabled: false,
  },
  medium: {
    level: 'medium',
    renderScale: 0.72,
    maximumDevicePixelRatio: 1.25,
    bloomEnabled: true,
    // Was 0.3. Trimmed alongside VISUAL_STYLE.bloom's tighter radius/higher
    // threshold (Stage 2) so a narrower halo doesn't also read brighter.
    bloomStrength: 0.24,
    maximumActiveLocalLights: 4,
    smaaEnabled: true,
  },
  high: {
    level: 'high',
    renderScale: 0.8,
    maximumDevicePixelRatio: 1.5,
    bloomEnabled: true,
    // Was 0.34; see the medium-profile comment above.
    bloomStrength: 0.26,
    maximumActiveLocalLights: 5,
    smaaEnabled: true,
  },
};

export const DEFAULT_QUALITY_LEVEL: QualityLevel = 'medium';

export const VISUAL_STYLE = {
  render: {
    toneMapping: 'agx',
    // Curves receive exposure in linear HDR through OutputPass. `off` keeps the
    // pre-tone-mapping look: a display-referred gain applied by the grade pass.
    // Curve values were calibrated so their interquartile display luminance
    // matches `off` across the dreams-angle, west-shops, park-to-dreams and
    // bus-shelter views, so switching compares highlight rolloff and colour
    // rather than overall brightness.
    exposure: {
      off: 1.34,
      agx: 1.7,
      neutral: 3.3,
      aces: 3.2,
    },
    // Was 1.12. The split-tone push below now carries some of what a flat
    // saturation boost used to do, so the global figure comes down closer to
    // neutral; the reference's colour comes from the sodium/fluorescent
    // practicals and the shadow/highlight tint, not a blanket vibrance lift.
    saturation: 1.0,
    contrast: 1.05,
    // Stage 2: a lift, not a brightness change. Raises only the darkest
    // pixels (display luminance floor, roughly this fraction) so true
    // shadow stays a dark blue-grey like the reference instead of crushing
    // to flat black; midtones and highlights are essentially untouched.
    // `LIGHTING_AUDIT.md` is right that the darkness between light pools is
    // the identity — this does not raise overall exposure or ambient light,
    // only the display floor of the grade.
    blackLift: 0.045,
    // Split-tone: a gentle, luminance-weighted colour push rather than a
    // uniform tint — shadows lean slightly toward `shadowTint`, highlights
    // slightly toward `highlightTint`, blended by (post-lift) luminance
    // between shadowEdge and highlightEdge. `strength` is how much of that
    // tint mixes in; keep it subtle, this is a push not a colour cast.
    splitTone: {
      shadowTint: 0x8fb4c9,
      highlightTint: 0xdcb98c,
      strength: 0.16,
      shadowEdge: 0.12,
      highlightEdge: 0.72,
    },
    // 255 (one 8-bit step) makes the grade's quantise step a no-op: the
    // output is already 8-bit, so this stops short of visibly posterising
    // dark gradients (the night sky, light pools) the way the old 32-level
    // retro-console step did. ditherStrength stays at roughly one 8-bit step
    // purely to break up banding, not to add a visible dither pattern.
    colorQuantizationLevels: 255,
    ditherStrength: 1 / 255,
    grainStrength: 0.042,
    vignetteStrength: 0.2,
    vignetteSoftness: 0.34,
  },
  texture: {
    photoAnisotropy: 2,
    graphicAnisotropy: 1,
  },
  sky: {
    zenithColor: 0x01040b,
    upperColor: 0x03091a,
    lowerColor: 0x09152a,
    horizonColor: 0x151722,
    brightness: 0.82,
    saturation: 0.76,
    horizonGlowColor: 0x2a2023,
    horizonGlowStrength: 0.17,
    horizonGlowHeight: 0.2,
    cloudNoiseStrength: 0.045,
    cloudScale: 1.35,
    cloudSpeed: 0.003,
  },
  stars: {
    color: 0x8792a4,
    // Begin with the urban sky empty. The atmosphere controller supports up
    // to fifteen threshold-visible points if later compositions need them.
    count: 0,
    brightness: 0.24,
    size: 1.15,
  },
  fog: {
    color: 0x081327,
    near: 46,
    far: 106,
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
    // One budgeted proxy follows the nearest painted public-light pool. These
    // values are deliberately local: they should select a figure, not wash an
    // entire street or revive the old one-real-light-per-lamp system.
    // The proxy sits at the lantern, about 7.8 m up, so it needs roughly four
    // times the old 3.85 m value to put the same light on the ground.
    streetLightIntensity: 95,
    streetLightDistance: 12,
    emissiveMultiplier: 1.15,
  },
  geometry: {
    // Flat (per-facet) shading was the strongest single "low-poly toy" signal
    // in the old retro-console pass. Off means every world material now lights
    // per-vertex/per-pixel off smooth normals. GLBs exported with hard/flat
    // shading in Blender should be re-exported with Shade Smooth plus a
    // Weighted Normal modifier (or Auto Smooth) if they read lumpy after this.
    facetedLighting: false,
    shadowsEnabled: false,
    shadowMapSize: 512,
  },
  bloom: {
    // Stage 2: a tighter halo around genuinely bright emissive sources
    // (tubes, signs) rather than a general haze over midtones. Radius down
    // from 0.32 (narrower blur spread), threshold up from 0.88 (more
    // selective about what counts as "bright enough to glow"). Provisional
    // first-pass numbers — tune live via `window.zealot.grade.set({...})`
    // (dev only) against the Dreams reference and bake the agreed values in.
    radius: 0.22,
    threshold: 0.92,
  },
  environment: {
    // Stage 4 of the realism pass (docs/REALISM_PASS_PLAN.md): with no
    // scene.environment, PBR materials have nothing to reflect and every
    // metal/glass surface reads flat regardless of its metalness/roughness.
    // Kept low: this should read as a soft ambient tint and the faint
    // reflections the reference shows, not a visible mirror — the darkness
    // between light pools stays the identity, this is not a new light
    // source (`LIGHTING_AUDIT.md`).
    intensity: 0.22,
    // PMREM cube-face resolution. 256 is PMREMGenerator's own default and
    // plenty for a soft ambient source — this never needs to be sharp.
    captureSize: 256,
    // Pre-blur radius in radians before prefiltering, so the one-shot
    // capture reads as soft ambient light rather than a sharp, aliased
    // mirror of nearby geometry. PMREMGenerator caps its discrete blur at
    // 20 samples; at captureSize 256 that's sigma <= ~0.039 before it clips
    // and logs a console warning (measured directly — its own internals
    // aren't public), so this stays safely under that.
    captureSigma: 0.03,
    captureNear: 0.5,
    captureFar: 90,
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

const TONE_MAPPING_CURVES: Record<ToneMappingName, ToneMapping> = {
  off: NoToneMapping,
  agx: AgXToneMapping,
  neutral: NeutralToneMapping,
  aces: ACESFilmicToneMapping,
};

export function resolveToneMapping(search: string): ToneMappingProfile {
  const requested = new URLSearchParams(search).get('tonemap')?.toLowerCase();
  const name =
    requested !== undefined && requested in TONE_MAPPING_CURVES
      ? (requested as ToneMappingName)
      : VISUAL_STYLE.render.toneMapping;
  return {
    name,
    curve: TONE_MAPPING_CURVES[name],
    exposure: VISUAL_STYLE.render.exposure[name],
  };
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
    // RETRO_GRAPHIC used nearest/nearest-mip filtering (hard, pixellated
    // edges) as part of the old retro-console rendering pass. These are
    // canvas-drawn signs, graffiti and road text, not pixel art, so they now
    // get the same smooth, mipmapped filtering as photographic surfaces;
    // only the (lower) anisotropy stays distinct.
    texture.magFilter = LinearFilter;
    texture.minFilter = LinearMipmapLinearFilter;
    texture.anisotropy = VISUAL_STYLE.texture.graphicAnisotropy;
  }
  if (texture.image != null) {
    texture.needsUpdate = true;
  }
  return texture;
}
