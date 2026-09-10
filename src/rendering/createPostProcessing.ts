import {
  ShaderMaterial,
  Vector2,
  type PerspectiveCamera,
  type Scene,
  type WebGLRenderer,
} from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { VISUAL_STYLE, type QualityProfile } from './visualStyle';

export interface PostProcessingPipeline {
  readonly render: (elapsedSeconds?: number) => void;
  readonly resize: (width: number, height: number) => void;
}

export function createPostProcessing(
  renderer: WebGLRenderer,
  scene: Scene,
  camera: PerspectiveCamera,
  quality: QualityProfile,
): PostProcessingPipeline {
  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));

  if (quality.bloomEnabled) {
    composer.addPass(
      new UnrealBloomPass(
        new Vector2(window.innerWidth, window.innerHeight),
        quality.bloomStrength,
        VISUAL_STYLE.bloom.radius,
        VISUAL_STYLE.bloom.threshold,
      ),
    );
  }

  composer.addPass(new OutputPass());

  const grade = new ShaderPass(
    new ShaderMaterial({
      uniforms: {
        tDiffuse: { value: null },
        exposure: { value: VISUAL_STYLE.render.exposure },
        saturation: { value: VISUAL_STYLE.render.saturation },
        contrast: { value: VISUAL_STYLE.render.contrast },
        quantizationLevels: {
          value: VISUAL_STYLE.render.colorQuantizationLevels,
        },
        ditherStrength: { value: VISUAL_STYLE.render.ditherStrength },
        grainStrength: { value: VISUAL_STYLE.render.grainStrength },
        vignetteStrength: { value: VISUAL_STYLE.render.vignetteStrength },
        vignetteSoftness: { value: VISUAL_STYLE.render.vignetteSoftness },
        elapsedSeconds: { value: 0 },
      },
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform sampler2D tDiffuse;
        uniform float exposure;
        uniform float saturation;
        uniform float contrast;
        uniform float quantizationLevels;
        uniform float ditherStrength;
        uniform float grainStrength;
        uniform float vignetteStrength;
        uniform float vignetteSoftness;
        uniform float elapsedSeconds;
        varying vec2 vUv;

        float orderedDither(vec2 pixel) {
          vec2 cell = mod(floor(pixel), 4.0);
          float index = cell.x + cell.y * 4.0;
          if (index < 1.0) return 0.0;
          if (index < 2.0) return 8.0;
          if (index < 3.0) return 2.0;
          if (index < 4.0) return 10.0;
          if (index < 5.0) return 12.0;
          if (index < 6.0) return 4.0;
          if (index < 7.0) return 14.0;
          if (index < 8.0) return 6.0;
          if (index < 9.0) return 3.0;
          if (index < 10.0) return 11.0;
          if (index < 11.0) return 1.0;
          if (index < 12.0) return 9.0;
          if (index < 13.0) return 15.0;
          if (index < 14.0) return 7.0;
          if (index < 15.0) return 13.0;
          return 5.0;
        }

        float hash(vec2 value) {
          return fract(sin(dot(value, vec2(12.9898, 78.233))) * 43758.5453);
        }

        void main() {
          vec4 source = texture2D(tDiffuse, vUv);
          vec3 exposed = source.rgb * exposure;
          float luminance = dot(exposed, vec3(0.299, 0.587, 0.114));
          vec3 color = mix(vec3(luminance), exposed, saturation);
          color = (color - 0.5) * contrast + 0.5;
          float shadowWeight = 0.4 + (1.0 - clamp(luminance, 0.0, 1.0)) * 0.6;
          float grain = hash(gl_FragCoord.xy + elapsedSeconds * vec2(17.0, 9.0)) - 0.5;
          color += grain * grainStrength * shadowWeight;
          float distanceFromCentre = distance(vUv, vec2(0.5));
          float vignette = smoothstep(
            0.48 - vignetteSoftness * 0.25,
            0.72 + vignetteSoftness * 0.25,
            distanceFromCentre
          );
          color *= 1.0 - vignette * vignetteStrength;
          float dither = (orderedDither(gl_FragCoord.xy) / 15.0 - 0.5)
            * ditherStrength;
          color = floor(clamp(color + dither, 0.0, 1.0)
            * quantizationLevels) / quantizationLevels;
          gl_FragColor = vec4(color, source.a);
        }
      `,
    }),
  );
  composer.addPass(grade);

  return {
    render: (elapsedSeconds = 0) => {
      grade.uniforms.elapsedSeconds.value = elapsedSeconds;
      composer.render();
    },
    resize: (width: number, height: number) => {
      composer.setPixelRatio(renderer.getPixelRatio());
      composer.setSize(width, height);
    },
  };
}
