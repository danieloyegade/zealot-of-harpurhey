import {
  BackSide,
  BufferAttribute,
  BufferGeometry,
  Color,
  Fog,
  Group,
  Mesh,
  Points,
  ShaderMaterial,
  SphereGeometry,
  type Scene,
} from 'three';
import { VISUAL_STYLE } from './visualStyle';

export interface NightAtmosphereParameters {
  skyZenithColor: number;
  skyUpperColor: number;
  skyLowerColor: number;
  skyHorizonColor: number;
  skyBrightness: number;
  skySaturation: number;
  horizonGlowColor: number;
  horizonGlowStrength: number;
  horizonGlowHeight: number;
  starCount: number;
  starBrightness: number;
  starSize: number;
  cloudNoiseStrength: number;
  cloudScale: number;
  cloudSpeed: number;
  fogColor: number;
  fogNear: number;
  fogFar: number;
}

export interface NightAtmosphere {
  readonly group: Group;
  readonly getParameters: () => Readonly<NightAtmosphereParameters>;
  readonly set: (parameters: Partial<NightAtmosphereParameters>) => void;
  readonly update: (deltaTime: number) => void;
}

const MAXIMUM_STAR_COUNT = 15;

function seededRandom(seed: number): () => number {
  let value = seed || 1;
  return () => {
    value = (value * 16807) % 2147483647;
    return (value - 1) / 2147483646;
  };
}

function createSparseStars(): Points<BufferGeometry, ShaderMaterial> {
  const positions = new Float32Array(MAXIMUM_STAR_COUNT * 3);
  const intensities = new Float32Array(MAXIMUM_STAR_COUNT);
  const indices = new Float32Array(MAXIMUM_STAR_COUNT);
  const random = seededRandom(19870917);

  for (let index = 0; index < MAXIMUM_STAR_COUNT; index += 1) {
    // Rejection sampling avoids the even latitude bands of the previous field.
    // All candidates stay above the polluted lower sky, where real urban stars
    // would disappear first.
    let x = 0;
    let y = 0;
    let z = 0;
    do {
      x = random() * 2 - 1;
      y = 0.18 + random() * 0.78;
      z = random() * 2 - 1;
    } while (x * x + y * y + z * z > 1 || x * x + y * y + z * z < 0.18);
    const length = Math.hypot(x, y, z);
    positions[index * 3] = (x / length) * 96;
    positions[index * 3 + 1] = (y / length) * 96;
    positions[index * 3 + 2] = (z / length) * 96;
    intensities[index] = 0.62 + random() * 0.38;
    indices[index] = index;
  }

  const geometry = new BufferGeometry();
  geometry.setAttribute('position', new BufferAttribute(positions, 3));
  geometry.setAttribute('starIntensity', new BufferAttribute(intensities, 1));
  geometry.setAttribute('starIndex', new BufferAttribute(indices, 1));

  const material = new ShaderMaterial({
    uniforms: {
      starColor: { value: new Color(VISUAL_STYLE.stars.color) },
      starCount: { value: VISUAL_STYLE.stars.count },
      starBrightness: { value: VISUAL_STYLE.stars.brightness },
      starSize: { value: VISUAL_STYLE.stars.size },
    },
    vertexShader: `
      uniform float starCount;
      uniform float starSize;
      attribute float starIntensity;
      attribute float starIndex;
      varying float vIntensity;
      varying float vVisible;

      void main() {
        vIntensity = starIntensity;
        vVisible = 1.0 - step(starCount, starIndex);
        vec4 viewPosition = mat4(mat3(viewMatrix)) * vec4(position, 1.0);
        vec4 clipPosition = projectionMatrix * viewPosition;
        gl_Position = vec4(clipPosition.xy, clipPosition.w, clipPosition.w);
        gl_PointSize = starSize * mix(0.78, 1.0, starIntensity) * vVisible;
      }
    `,
    fragmentShader: `
      uniform vec3 starColor;
      uniform float starBrightness;
      varying float vIntensity;
      varying float vVisible;

      void main() {
        if (vVisible < 0.5) discard;
        float radius = distance(gl_PointCoord, vec2(0.5));
        float coverage = 1.0 - smoothstep(0.18, 0.5, radius);
        if (coverage <= 0.0) discard;
        gl_FragColor = vec4(
          starColor * starBrightness * vIntensity,
          coverage * vIntensity
        );
      }
    `,
    transparent: true,
    depthWrite: false,
    fog: false,
    toneMapped: false,
  });

  const stars = new Points(geometry, material);
  stars.name = 'Threshold-visible urban stars';
  stars.frustumCulled = false;
  stars.renderOrder = -99;
  return stars;
}

export function createNightAtmosphere(scene: Scene): NightAtmosphere {
  const parameters: NightAtmosphereParameters = {
    skyZenithColor: VISUAL_STYLE.sky.zenithColor,
    skyUpperColor: VISUAL_STYLE.sky.upperColor,
    skyLowerColor: VISUAL_STYLE.sky.lowerColor,
    skyHorizonColor: VISUAL_STYLE.sky.horizonColor,
    skyBrightness: VISUAL_STYLE.sky.brightness,
    skySaturation: VISUAL_STYLE.sky.saturation,
    horizonGlowColor: VISUAL_STYLE.sky.horizonGlowColor,
    horizonGlowStrength: VISUAL_STYLE.sky.horizonGlowStrength,
    horizonGlowHeight: VISUAL_STYLE.sky.horizonGlowHeight,
    starCount: VISUAL_STYLE.stars.count,
    starBrightness: VISUAL_STYLE.stars.brightness,
    starSize: VISUAL_STYLE.stars.size,
    cloudNoiseStrength: VISUAL_STYLE.sky.cloudNoiseStrength,
    cloudScale: VISUAL_STYLE.sky.cloudScale,
    cloudSpeed: VISUAL_STYLE.sky.cloudSpeed,
    fogColor: VISUAL_STYLE.fog.color,
    fogNear: VISUAL_STYLE.fog.near,
    fogFar: VISUAL_STYLE.fog.far,
  };

  const group = new Group();
  group.name = 'Urban night atmosphere';

  const skyMaterial = new ShaderMaterial({
    uniforms: {
      zenithColor: { value: new Color(parameters.skyZenithColor) },
      upperColor: { value: new Color(parameters.skyUpperColor) },
      lowerColor: { value: new Color(parameters.skyLowerColor) },
      horizonColor: { value: new Color(parameters.skyHorizonColor) },
      horizonGlowColor: { value: new Color(parameters.horizonGlowColor) },
      skyBrightness: { value: parameters.skyBrightness },
      skySaturation: { value: parameters.skySaturation },
      horizonGlowStrength: { value: parameters.horizonGlowStrength },
      horizonGlowHeight: { value: parameters.horizonGlowHeight },
      cloudNoiseStrength: { value: parameters.cloudNoiseStrength },
      cloudScale: { value: parameters.cloudScale },
      cloudSpeed: { value: parameters.cloudSpeed },
      elapsedSeconds: { value: 0 },
    },
    vertexShader: `
      varying vec3 vSkyDirection;

      void main() {
        vSkyDirection = normalize(position);
        vec4 viewPosition = mat4(mat3(viewMatrix)) * vec4(position, 1.0);
        vec4 clipPosition = projectionMatrix * viewPosition;
        gl_Position = vec4(clipPosition.xy, clipPosition.w, clipPosition.w);
      }
    `,
    fragmentShader: `
      uniform vec3 zenithColor;
      uniform vec3 upperColor;
      uniform vec3 lowerColor;
      uniform vec3 horizonColor;
      uniform vec3 horizonGlowColor;
      uniform float skyBrightness;
      uniform float skySaturation;
      uniform float horizonGlowStrength;
      uniform float horizonGlowHeight;
      uniform float cloudNoiseStrength;
      uniform float cloudScale;
      uniform float cloudSpeed;
      uniform float elapsedSeconds;
      varying vec3 vSkyDirection;

      void main() {
        vec3 direction = normalize(vSkyDirection);
        float elevation = clamp(direction.y, 0.0, 1.0);

        vec3 color = mix(horizonColor, lowerColor, smoothstep(0.0, 0.22, elevation));
        color = mix(color, upperColor, smoothstep(0.16, 0.68, elevation));
        color = mix(color, zenithColor, smoothstep(0.58, 1.0, elevation));

        // Three broad, non-aligned waves produce continent-scale density
        // changes without a texture, cloud sprites or small readable clouds.
        float phase = elapsedSeconds * cloudSpeed;
        float broadNoise = (
          sin(dot(direction, vec3(1.73, 0.81, -1.19)) * cloudScale + phase) +
          sin(dot(direction, vec3(-0.62, 1.41, 1.27)) * cloudScale * 0.73 - phase * 0.61) +
          sin(dot(direction, vec3(1.11, -0.48, 0.67)) * cloudScale * 1.31 + phase * 0.37)
        ) / 3.0;
        float densityWeight = smoothstep(0.02, 0.48, elevation)
          * (1.0 - smoothstep(0.82, 1.0, elevation));
        color *= 1.0 + broadNoise * cloudNoiseStrength * densityWeight;

        float horizonBand = 1.0 - smoothstep(
          0.0,
          max(horizonGlowHeight, 0.001),
          elevation
        );
        horizonBand *= horizonBand;
        vec2 planarDirection = normalize(direction.xz + vec2(0.0001));
        float warmDistrict = pow(max(dot(planarDirection, normalize(vec2(-0.78, 0.62))), 0.0), 4.0);
        float coolDistrict = pow(max(dot(planarDirection, normalize(vec2(0.56, -0.83))), 0.0), 5.0);
        float unevenPollution = 0.54 + warmDistrict * 0.31 + coolDistrict * 0.15;
        color = mix(
          color,
          horizonGlowColor,
          horizonBand * horizonGlowStrength * unevenPollution
        );

        float luminance = dot(color, vec3(0.2126, 0.7152, 0.0722));
        color = mix(vec3(luminance), color, skySaturation) * skyBrightness;
        gl_FragColor = vec4(color, 1.0);
      }
    `,
    side: BackSide,
    depthWrite: false,
    fog: false,
    toneMapped: false,
  });

  const sky = new Group();
  sky.name = 'Blue-black polluted sky';
  const skyMesh = new Mesh(new SphereGeometry(96, 24, 12), skyMaterial);
  skyMesh.name = 'Atmospheric sky dome';
  skyMesh.frustumCulled = false;
  skyMesh.renderOrder = -100;
  sky.add(skyMesh);
  group.add(sky);

  const stars = createSparseStars();
  stars.visible = parameters.starCount > 0;
  group.add(stars);

  const backgroundColor = new Color(parameters.skyZenithColor);
  scene.background = backgroundColor;
  const fog = new Fog(parameters.fogColor, parameters.fogNear, parameters.fogFar);
  scene.fog = fog;
  scene.add(group);

  const set = (next: Partial<NightAtmosphereParameters>): void => {
    Object.assign(parameters, next);
    parameters.starCount = Math.max(
      0,
      Math.min(MAXIMUM_STAR_COUNT, Math.round(parameters.starCount)),
    );
    parameters.fogNear = Math.max(0, parameters.fogNear);
    parameters.fogFar = Math.max(parameters.fogNear + 1, parameters.fogFar);

    skyMaterial.uniforms.zenithColor.value.setHex(parameters.skyZenithColor);
    skyMaterial.uniforms.upperColor.value.setHex(parameters.skyUpperColor);
    skyMaterial.uniforms.lowerColor.value.setHex(parameters.skyLowerColor);
    skyMaterial.uniforms.horizonColor.value.setHex(parameters.skyHorizonColor);
    skyMaterial.uniforms.horizonGlowColor.value.setHex(parameters.horizonGlowColor);
    skyMaterial.uniforms.skyBrightness.value = parameters.skyBrightness;
    skyMaterial.uniforms.skySaturation.value = parameters.skySaturation;
    skyMaterial.uniforms.horizonGlowStrength.value = parameters.horizonGlowStrength;
    skyMaterial.uniforms.horizonGlowHeight.value = parameters.horizonGlowHeight;
    skyMaterial.uniforms.cloudNoiseStrength.value = parameters.cloudNoiseStrength;
    skyMaterial.uniforms.cloudScale.value = parameters.cloudScale;
    skyMaterial.uniforms.cloudSpeed.value = parameters.cloudSpeed;
    stars.material.uniforms.starCount.value = parameters.starCount;
    stars.material.uniforms.starBrightness.value = parameters.starBrightness;
    stars.material.uniforms.starSize.value = parameters.starSize;
    stars.visible = parameters.starCount > 0;
    fog.color.setHex(parameters.fogColor);
    fog.near = parameters.fogNear;
    fog.far = parameters.fogFar;
    backgroundColor.setHex(parameters.skyZenithColor);
  };

  return {
    group,
    getParameters: () => ({ ...parameters }),
    set,
    update: (deltaTime) => {
      skyMaterial.uniforms.elapsedSeconds.value += deltaTime;
    },
  };
}
