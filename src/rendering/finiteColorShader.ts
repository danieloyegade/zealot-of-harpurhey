/**
 * A single NaN in an HDR scene can contaminate every bloom mip and blank the
 * whole frame. Contain non-finite fragments before any spatial filtering.
 */
export const finiteColorShader = {
  uniforms: { tDiffuse: { value: null } },
  vertexShader: `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    uniform sampler2D tDiffuse;
    varying vec2 vUv;

    float finiteChannel(float value, float fallback) {
      return (isnan(value) || isinf(value)) ? fallback : value;
    }

    void main() {
      vec4 source = texture2D(tDiffuse, vUv);
      gl_FragColor = vec4(
        finiteChannel(source.r, 0.0),
        finiteChannel(source.g, 0.0),
        finiteChannel(source.b, 0.0),
        finiteChannel(source.a, 1.0)
      );
    }
  `,
};
