import {
  CanvasTexture,
  CustomBlending,
  EquirectangularReflectionMapping,
  Mesh,
  MeshStandardMaterial,
  OneFactor,
  OneMinusSrcAlphaFactor,
  SRGBColorSpace,
  ShaderChunk,
  type Group,
  type Texture,
} from 'three';
import { VISUAL_STYLE, applyTextureProfile } from '../rendering/visualStyle';

type CompiledShader = Parameters<MeshStandardMaterial['onBeforeCompile']>[0];

const cssColor = (hex: number): string => `#${hex.toString(16).padStart(6, '0')}`;

// Runtime half of the bus-shelter texture pass
// (blender/scripts/createBusShelterTextured.py). The GLB carries baked
// weathering; this module supplies what glTF cannot describe: glass whose
// reflections are not dimmed by its transparency, a night street to reflect,
// and a wet-weather response that respects gravity and the roof.

const shelterWetness = { value: readRequestedWetness() };

function readRequestedWetness(): number {
  const requested = Number(new URLSearchParams(window.location.search).get('wet'));
  return Number.isFinite(requested) ? Math.min(Math.max(requested, 0), 1) : 0;
}

/** 0 = dry, 1 = fully rained on. Shared by every loaded shelter. */
export function setBusShelterWetness(value: number): void {
  shelterWetness.value = Math.min(Math.max(value, 0), 1);
}

let nightStreetEnvironment: Texture | undefined;

// A small painted equirectangular night street: cobalt sky, dark ground and
// the palette's practical lights along the horizon. The renderer converts it
// to a prefiltered environment on first use.
function getNightStreetEnvironment(): Texture {
  if (nightStreetEnvironment) {
    return nightStreetEnvironment;
  }
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 256;
  const context = canvas.getContext('2d');
  if (context) {
    const sky = context.createLinearGradient(0, 0, 0, canvas.height);
    sky.addColorStop(0, '#02071c');
    sky.addColorStop(0.46, '#0b1a45');
    sky.addColorStop(0.52, '#08101f');
    sky.addColorStop(1, '#030405');
    context.fillStyle = sky;
    context.fillRect(0, 0, canvas.width, canvas.height);
    const { sodium, magenta, fluorescent, coldWhite } = VISUAL_STYLE.lighting;
    const lights: readonly [number, number, number, number][] = [
      [40, 118, 26, sodium],
      [128, 110, 14, coldWhite],
      [205, 121, 34, sodium],
      [290, 116, 22, magenta],
      [360, 104, 12, coldWhite],
      [430, 120, 30, sodium],
      [480, 126, 16, fluorescent],
    ];
    for (const [x, y, radius, color] of lights) {
      const glow = context.createRadialGradient(x, y, 0, x, y, radius);
      glow.addColorStop(0, '#ffffff');
      glow.addColorStop(0.18, cssColor(color));
      glow.addColorStop(1, 'rgba(0, 0, 0, 0)');
      context.fillStyle = glow;
      context.fillRect(x - radius, y - radius, radius * 2, radius * 2);
    }
    context.fillStyle = 'rgba(255, 200, 140, 0.18)';
    for (let x = 0; x < canvas.width; x += 23) {
      context.fillRect(x, 96 + ((x * 7) % 13), 6, 4);
    }
  }
  const texture = new CanvasTexture(canvas);
  texture.mapping = EquirectangularReflectionMapping;
  texture.colorSpace = SRGBColorSpace;
  nightStreetEnvironment = texture;
  return texture;
}

const WORLD_VARYINGS = /* glsl */ `
varying vec3 vShelterWorldPosition;
varying vec3 vShelterWorldNormal;
`;

function addWorldVaryings(shader: CompiledShader): void {
  shader.uniforms.shelterWetness = shelterWetness;
  shader.vertexShader = shader.vertexShader
    .replace('#include <common>', `#include <common>\n${WORLD_VARYINGS}`)
    .replace(
      '#include <worldpos_vertex>',
      `#include <worldpos_vertex>
      vShelterWorldPosition = ( modelMatrix * vec4( transformed, 1.0 ) ).xyz;
      vShelterWorldNormal = normalize( mat3( modelMatrix ) * objectNormal );`,
    );
  shader.fragmentShader = shader.fragmentShader.replace(
    '#include <common>',
    `#include <common>
    ${WORLD_VARYINGS}
    uniform float shelterWetness;
    float shelterHash( vec2 p ) {
      return fract( sin( dot( p, vec2( 127.1, 311.7 ) ) ) * 43758.5453 );
    }
    float shelterNoise( vec2 p ) {
      vec2 i = floor( p );
      vec2 f = fract( p );
      f = f * f * ( 3.0 - 2.0 * f );
      return mix(
        mix( shelterHash( i ), shelterHash( i + vec2( 1.0, 0.0 ) ), f.x ),
        mix( shelterHash( i + vec2( 0.0, 1.0 ) ), shelterHash( i + vec2( 1.0, 1.0 ) ), f.x ),
        f.y
      );
    }`,
  );
}

interface GlassOptions {
  /** Environment reflection strength (the shelter's default is 2.6). */
  envMapIntensity?: number;
  /**
   * Extra reflection towards grazing angles plus a faint cool sheen, so a
   * darkened shopfront reads as glass rather than an open hatch. 0 is off.
   */
  grazingSheen?: number;
}

function configureGlass(material: MeshStandardMaterial, options: GlassOptions = {}): void {
  const sheen = options.grazingSheen ?? 0;
  material.transparent = true;
  material.depthWrite = false;
  material.opacity = 1;
  // Premultiplied output: the baked alpha dims only the glass's own film and
  // grime, while specular reflections add at full strength, as real glass does.
  material.blending = CustomBlending;
  material.blendSrc = OneFactor;
  material.blendDst = OneMinusSrcAlphaFactor;
  material.envMapIntensity = options.envMapIntensity ?? 2.6;
  material.onBeforeCompile = (shader) => {
    addWorldVaryings(shader);
    shader.fragmentShader = `#define GLASS_GRAZING_SHEEN ${sheen.toFixed(3)}\n${shader.fragmentShader}`;
    shader.fragmentShader = shader.fragmentShader
      .replace(
        '#include <roughnessmap_fragment>',
        `#include <roughnessmap_fragment>
        vec3 glassNormal = normalize( vShelterWorldNormal );
        float along = dot( vShelterWorldPosition.xz, vec2( -glassNormal.z, glassNormal.x ) );
        float rivulets = smoothstep( 0.62, 0.9, shelterNoise( vec2( along * 160.0, vShelterWorldPosition.y * 3.0 ) ) );
        float droplets = smoothstep( 0.86, 0.95, shelterNoise( vShelterWorldPosition.xy * 420.0 + along * 37.0 ) );
        float lowerGlass = smoothstep( 2.8, 0.3, vShelterWorldPosition.y );
        float glassWet = clamp( ( rivulets * 0.8 + droplets ) * ( 0.35 + 0.65 * lowerGlass ), 0.0, 1.0 ) * shelterWetness;
        roughnessFactor = mix( roughnessFactor, 0.015, glassWet );
        diffuseColor.a = clamp( diffuseColor.a + 0.05 * glassWet, 0.0, 1.0 );`,
      )
      .replace(
        '#include <opaque_fragment>',
        `float glassGrazing = pow( 1.0 - saturate( dot( geometryNormal, geometryViewDir ) ), 3.0 );
        vec3 glassSpecular = totalSpecular * ( 1.0 + GLASS_GRAZING_SHEEN * 4.0 * glassGrazing )
          + vec3( 0.030, 0.040, 0.062 ) * GLASS_GRAZING_SHEEN * ( 0.35 + glassGrazing );
        gl_FragColor = vec4( totalDiffuse * diffuseColor.a + glassSpecular + totalEmissiveRadiance, diffuseColor.a );`,
      )
      .replace(
        '#include <fog_fragment>',
        ShaderChunk.fog_fragment.replace('fogColor, fogFactor', 'fogColor * gl_FragColor.a, fogFactor'),
      );
  };
  material.customProgramCacheKey = () => `bus-shelter-glass-${sheen.toFixed(3)}`;
}

function configureWeatheredSurface(material: MeshStandardMaterial): void {
  // Opaque shelter materials store their rain exposure in the base-colour
  // alpha channel: roof-sheltered faces stay dry, upward and road-facing
  // faces take water, and porous (rough) surfaces darken the most.
  material.envMapIntensity = 1;
  material.onBeforeCompile = (shader) => {
    addWorldVaryings(shader);
    shader.fragmentShader = shader.fragmentShader.replace(
      '#include <roughnessmap_fragment>',
      `#include <roughnessmap_fragment>
      #ifdef USE_MAP
        // Alpha stores 0.2 + 0.8 * exposure so WebP keeps every texel's colour.
        float wetExposure = clamp( ( texture2D( map, vMapUv ).a - 0.2 ) / 0.8, 0.0, 1.0 ) * shelterWetness;
        float porosity = clamp( roughnessFactor * 1.3, 0.0, 1.0 );
        diffuseColor.rgb *= mix( 1.0, 0.55, wetExposure * porosity );
        roughnessFactor = mix( roughnessFactor, 0.07, wetExposure * 0.85 );
      #endif`,
    );
  };
  material.customProgramCacheKey = () => 'bus-shelter-weathered';
}

function configureGroundContact(material: MeshStandardMaterial, mesh: Mesh): void {
  material.transparent = true;
  material.depthWrite = false;
  material.polygonOffset = true;
  material.polygonOffsetFactor = -4;
  material.polygonOffsetUnits = -4;
  mesh.castShadow = false;
  mesh.renderOrder = 1;
}

type TexturePassRole = 'glass' | 'ground-contact' | 'emissive' | 'weathered' | 'plain';

/**
 * Shared runtime policy for Blender texture-pass GLBs: photographic filtering,
 * the painted night-street environment, and a role per material name.
 */
function applyTexturePassPolicy(
  model: Group,
  roleOf: (name: string, material: MeshStandardMaterial) => TexturePassRole,
  emissiveScale = 1,
  glass: GlassOptions = {},
): void {
  const environment = getNightStreetEnvironment();
  // Materials are shared between meshes; multiplying emissive strength is not
  // idempotent, so each material is configured once and meshes per visit.
  const configured = new Set<MeshStandardMaterial>();
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
      const role = roleOf(material.name.toLowerCase(), material);
      if (role === 'glass') {
        child.castShadow = false;
      } else if (role === 'ground-contact') {
        child.castShadow = false;
        child.renderOrder = 1;
      }
      if (configured.has(material)) {
        continue;
      }
      configured.add(material);
      for (const texture of [
        material.map,
        material.emissiveMap,
        material.roughnessMap,
        material.metalnessMap,
        material.aoMap,
        material.normalMap,
      ]) {
        if (texture) {
          applyTextureProfile(texture, 'PHOTO_ENVIRONMENT');
        }
      }
      material.envMap = environment;
      if (role === 'glass') {
        configureGlass(material, glass);
      } else if (role === 'ground-contact') {
        configureGroundContact(material, child);
      } else if (role === 'emissive') {
        material.emissiveIntensity *= VISUAL_STYLE.lighting.emissiveMultiplier * emissiveScale;
      } else if (role === 'weathered') {
        configureWeatheredSurface(material);
      }
      material.needsUpdate = true;
    }
  });
}

export function applyBusShelterTexturePolicy(model: Group): void {
  applyTexturePassPolicy(model, (name, material) => {
    if (name.includes('busstop_glass')) {
      return 'glass';
    }
    if (name.includes('busstop_groundcontact')) {
      return 'ground-contact';
    }
    if (name.includes('busstop_advert') || name.includes('busstop_light')) {
      return 'emissive';
    }
    return name.includes('busstop_') && material.map ? 'weathered' : 'plain';
  });
}

/**
 * Spice Cabin (docs/assets/spice-cabin.md). Its opaque base-colour alpha is 1,
 * not a rain-exposure mask, so no surface takes the shelter's wet treatment.
 * Its interior practicals (menu boxes, fridge, ceiling panels) share the LED
 * sign's emissive material and bloom out behind the glass at full strength, so
 * that material is held back to a restrained shop glow. The LED window sign and
 * the tube-light diffusers are exterior practicals and keep full strength on a
 * shared clone.
 */
const SPICE_CABIN_INTERIOR_EMISSIVE_SCALE = 0.25;
// Tinted shopfront glass: stronger street reflection, rising towards grazing
// angles, so the windows read as glazing from the pavement.
const SPICE_CABIN_GLASS: GlassOptions = { envMapIntensity: 4.2, grazingSheen: 1 };

export function applySpiceCabinTexturePolicy(model: Group): void {
  applyTexturePassPolicy(
    model,
    (name) => {
      if (name.includes('glass_shopfront')) {
        return 'glass';
      }
      if (name.includes('ground_contact')) {
        return 'ground-contact';
      }
      return name.includes('emissive_signage') ? 'emissive' : 'plain';
    },
    SPICE_CABIN_INTERIOR_EMISSIVE_SCALE,
    SPICE_CABIN_GLASS,
  );
  let practical: MeshStandardMaterial | undefined;
  model.traverse((child) => {
    if (
      !(child instanceof Mesh) ||
      !/LEDSign_Face|TubeDiffuser/.test(child.name) ||
      !(child.material instanceof MeshStandardMaterial)
    ) {
      return;
    }
    if (!practical) {
      practical = child.material.clone();
      practical.emissiveIntensity /= SPICE_CABIN_INTERIOR_EMISSIVE_SCALE;
    }
    child.material = practical;
  });
}

/**
 * Worn pallets (docs/assets/pallets.md): one opaque textured material each, with
 * base-colour alpha 1, so they take only the shared photographic filtering and
 * night-street environment.
 */
export function applyPalletTexturePolicy(model: Group): void {
  applyTexturePassPolicy(model, () => 'plain');
}

/**
 * Bougainvillea fence scene: everything plain except the sign lamp's lens,
 * which is pushed well past the other practicals so it reads as the source of
 * the pool of light that falls on the flowers.
 */
const BOUGAINVILLEA_LAMP_EMISSIVE_SCALE = 3;

export function applyBougainvilleaTexturePolicy(model: Group): void {
  applyTexturePassPolicy(
    model,
    (name) => (name.includes('lamp_lens') ? 'emissive' : 'plain'),
    BOUGAINVILLEA_LAMP_EMISSIVE_SCALE,
  );
}
