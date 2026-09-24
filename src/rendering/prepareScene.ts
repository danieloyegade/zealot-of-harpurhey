import {
  HalfFloatType,
  WebGLRenderTarget,
  type Camera,
  type Object3D,
  type Scene,
  type WebGLRenderer,
} from 'three';

const OBJECTS_PER_BATCH = 64;

/** Upload off-screen geometry and textures before handing control to the player. */
export async function prepareScene(
  renderer: WebGLRenderer,
  scene: Scene,
  camera: Camera,
): Promise<void> {
  // Match the composer's HDR target so compilation uses the same shader variants.
  // A private camera also keeps preparation from moving the live view.
  const target = new WebGLRenderTarget(1, 1, { type: HalfFloatType });
  const preparationCamera = camera.clone();
  const objects: { object: Object3D; mask: number; culled: boolean }[] = [];
  scene.traverseVisible((object) => {
    if ('geometry' in object && 'material' in object && object.layers.test(camera.layers)) {
      objects.push({ object, mask: object.layers.mask, culled: object.frustumCulled });
    }
  });

  try {
    const previousTarget = renderer.getRenderTarget();
    let compilation: Promise<unknown>;
    try {
      renderer.setRenderTarget(target);
      // compileAsync traverses the entire scene; rotating the camera adds nothing.
      compilation = renderer.compileAsync(scene, preparationCamera);
    } finally {
      renderer.setRenderTarget(previousTarget);
    }
    await compilation;

    for (let start = 0; start < objects.length; start += OBJECTS_PER_BATCH) {
      const previousTarget = renderer.getRenderTarget();
      try {
        for (let index = 0; index < objects.length; index += 1) {
          const entry = objects[index];
          // Layers skip this object's draw without hiding its descendants.
          entry.object.layers.mask = index >= start && index < start + OBJECTS_PER_BATCH
            ? entry.mask : 0;
          entry.object.frustumCulled = false;
        }
        renderer.setRenderTarget(target);
        renderer.render(scene, preparationCamera);
      } finally {
        for (const { object, mask, culled } of objects) {
          object.layers.mask = mask;
          object.frustumCulled = culled;
        }
        renderer.setRenderTarget(previousTarget);
      }
      // Restore all state before yielding so the regular frame stays intact.
      await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
    }
  } finally {
    target.dispose();
  }
}
