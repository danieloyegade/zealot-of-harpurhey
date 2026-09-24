import assert from 'node:assert/strict';
import test from 'node:test';
import { BoxGeometry, Group, Mesh, MeshBasicMaterial, PerspectiveCamera, Scene, WebGLRenderTarget } from 'three';
import { prepareScene } from '../src/rendering/prepareScene.ts';

test('preparation uploads off-screen descendants in batches and restores state before yielding', async () => {
  const scene = new Scene();
  const camera = new PerspectiveCamera();
  camera.position.set(1, 2, 3);
  const meshes = Array.from({ length: 130 }, () => new Mesh(new BoxGeometry(), new MeshBasicMaterial()));
  // Children of meshes must upload even in a different batch from their parent.
  scene.add(meshes[0]);
  meshes.slice(1).forEach(mesh => { mesh.position.set(999, 999, 999); meshes[0].add(mesh); });
  const hidden = new Group();
  hidden.visible = false;
  const hiddenMesh = new Mesh(new BoxGeometry(), new MeshBasicMaterial());
  hidden.add(hiddenMesh);
  scene.add(hidden);
  const uploaded = new Set();
  const originalTarget = new WebGLRenderTarget(8, 8);
  let target = originalTarget;
  let renders = 0;
  let compiles = 0;
  const checkRestored = () => {
    assert.equal(target, originalTarget);
    assert.deepEqual(camera.position.toArray(), [1, 2, 3]);
    meshes.forEach(mesh => {
      assert.equal(mesh.layers.mask, 1);
      assert.equal(mesh.frustumCulled, true);
      assert.equal(mesh.visible, true);
    });
    assert.equal(hidden.visible, false);
  };
  const renderer = {
    getRenderTarget: () => target,
    setRenderTarget: value => { target = value; },
    compileAsync: async (_scene, preparationCamera) => {
      compiles++;
      assert.notEqual(preparationCamera, camera);
      await Promise.resolve();
      checkRestored();
    },
    render: (_scene, preparationCamera) => {
      renders++;
      let count = 0;
      scene.traverseVisible(object => {
        if (object.isMesh && object.layers.test(preparationCamera.layers)) {
          assert.equal(object.frustumCulled, false);
          uploaded.add(object);
          count++;
        }
      });
      assert.ok(count <= 64);
    },
  };
  const previousRAF = globalThis.requestAnimationFrame;
  globalThis.requestAnimationFrame = callback => { checkRestored(); queueMicrotask(callback); return 1; };
  try {
    await prepareScene(renderer, scene, camera);
    checkRestored();
    assert.equal(compiles, 1);
    assert.equal(renders, 3);
    assert.equal(uploaded.size, meshes.length);
    assert.equal(uploaded.has(hiddenMesh), false);
  } finally {
    globalThis.requestAnimationFrame = previousRAF;
    originalTarget.dispose();
  }
});

test('a failed GPU upload restores the render target and scene flags', async () => {
  const scene = new Scene();
  const mesh = new Mesh(new BoxGeometry(), new MeshBasicMaterial());
  mesh.layers.set(2);
  scene.add(mesh);
  const camera = new PerspectiveCamera();
  camera.layers.enable(2);
  let target = null;
  const renderer = {
    getRenderTarget: () => target,
    setRenderTarget: value => { target = value; },
    compileAsync: async () => {},
    render: () => { throw new Error('upload failed'); },
  };
  await assert.rejects(prepareScene(renderer, scene, camera), /upload failed/);
  assert.equal(target, null);
  assert.equal(mesh.layers.mask, 4);
  assert.equal(mesh.frustumCulled, true);
});
