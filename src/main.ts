import {
  Mesh,
  PerspectiveCamera,
  Scene,
  SRGBColorSpace,
  Timer,
  Vector3,
  WebGLRenderer,
} from 'three';
import { AmbientAudio } from './audio/AmbientAudio';
import { ThirdPersonCamera } from './camera/ThirdPersonCamera';
import { FixedStepClock } from './core/FixedStepClock';
import { InputController } from './input/InputController';
import { PlayerController } from './player/PlayerController';
import { createPostProcessing } from './rendering/createPostProcessing';
import {
  applyInternalResolution,
  resolveQualityProfile,
  VISUAL_STYLE,
} from './rendering/visualStyle';
import { DebugOverlay } from './ui/DebugOverlay';
import { createWorld } from './world/createWorld';
import './style.css';

const app = document.querySelector<HTMLDivElement>('#app');

if (!app) {
  throw new Error('Application root element was not found.');
}

const scene = new Scene();
const renderer = new WebGLRenderer({ antialias: true });
const quality = resolveQualityProfile(window.location.search);
applyInternalResolution(renderer, window.innerWidth, window.innerHeight, quality);
renderer.outputColorSpace = SRGBColorSpace;
renderer.toneMappingExposure = VISUAL_STYLE.render.exposure;
renderer.info.autoReset = false;
app.appendChild(renderer.domElement);

const camera = new PerspectiveCamera(
  50,
  window.innerWidth / window.innerHeight,
  0.1,
  120,
);

const world = createWorld(scene, quality.maximumActiveLocalLights);
const input = new InputController(renderer.domElement);
new AmbientAudio();
const player = new PlayerController(world.collision);
scene.add(player.object);

const requestedView = import.meta.env.DEV
  ? new URLSearchParams(window.location.search).get('view')
  : null;

let requestedYaw = 0;
let requestedPitch = 0.31;
if (import.meta.env.DEV) {
  const developmentViews: Record<string, readonly [number, number, number?, number?]> = {
    'park-florist': [-13.9, -18],
    'greek-gyros': [14, -15.2, 0, 0.2],
    'come-through-lab': [-26, -15, Math.PI / 2, 0.2],
    'village-books': [-27, -3.5, Math.PI / 2, 0.16],
    'bus-shelter': [0, 27],
    'collision-dreams': [-3, 32.5, Math.PI],
    'dreams-target': [-3, 29.8, Math.PI],
    'dreams-angle': [-11, 29, 2.45, 0.18],
    'north-road': [-17, -25.2, -Math.PI / 2, 0.24],
    'park-to-dreams': [-3, 18, Math.PI, 0.2],
    'street-detail': [6.4, -27.2, 0.42, 0.16],
    'west-street': [-29.5, 25],
    'west-shops': [-29.5, 7],
    'east-shops': [29.5, 19],
    'south-shops': [0, 22],
    'south-road': [0, 53.5, Math.PI, 0.24],
    'real-camera': [-11.5, 58, Math.PI, 0.06],
    'real-camera-corner': [-26, 58.5, 2.3, 0.06],
    pickup: [5, 16.5],
  };
  const requestedPosition = requestedView
    ? developmentViews[requestedView]
    : undefined;
  if (requestedPosition) {
    player.position.set(requestedPosition[0], 0, requestedPosition[1]);
    player.recoverFromCollisionOverlap();
    requestedYaw = requestedPosition[2] ?? 0;
    requestedPitch = requestedPosition[3] ?? 0.31;
  }
}

const thirdPersonCamera = new ThirdPersonCamera(
  camera,
  requestedView === 'dreams-target' ? 2.9 : 1.05,
);
thirdPersonCamera.setOrbit(requestedYaw, requestedPitch);
thirdPersonCamera.snapTo(player.position);
const postProcessing = createPostProcessing(renderer, scene, camera, quality);

const debugOverlay = import.meta.env.DEV ? new DebugOverlay() : null;
const timer = new Timer();
timer.connect(document);
const simulationClock = new FixedStepClock();
const cameraForward = new Vector3();
let developmentOverlaysVisible = new URLSearchParams(window.location.search).get('overlays') !== 'off';
let elapsedSeconds = 0;
let sceneMaterialCount = 0;

world.setDevelopmentOverlaysVisible(developmentOverlaysVisible);
debugOverlay?.setVisible(developmentOverlaysVisible);

window.setTimeout(() => {
  const materials = new Set();
  scene.traverse((child) => {
    if (!(child instanceof Mesh)) return;
    const childMaterials = Array.isArray(child.material) ? child.material : [child.material];
    childMaterials.forEach((material) => materials.add(material));
  });
  sceneMaterialCount = materials.size;
}, 2000);

function resize(): void {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  applyInternalResolution(renderer, window.innerWidth, window.innerHeight, quality);
  postProcessing.resize(window.innerWidth, window.innerHeight);
}

window.addEventListener('resize', resize);
document.addEventListener('visibilitychange', () => {
  simulationClock.reset();
});

function frame(timestamp: number): void {
  requestAnimationFrame(frame);

  timer.update(timestamp);
  const rawDelta = timer.getDelta();

  input.update();
  if (input.consumeOverlayToggle()) {
    developmentOverlaysVisible = !developmentOverlaysVisible;
    world.setDevelopmentOverlaysVisible(developmentOverlaysVisible);
    debugOverlay?.setVisible(developmentOverlaysVisible);
  }
  thirdPersonCamera.getPlanarForward(cameraForward);
  const simulationResult = simulationClock.advance(rawDelta, (fixedDelta) => {
    player.update(fixedDelta, input, cameraForward);
    world.update(fixedDelta, player.position);
    elapsedSeconds += fixedDelta;
  });
  const cameraDelta = simulationResult.resetAfterExtremeGap ? 0 : rawDelta;
  thirdPersonCamera.update(cameraDelta, input, player.position);

  renderer.info.reset();
  postProcessing.render(elapsedSeconds);
  const lighting = world.getLightingStats();
  const diagnostics = {
    drawCalls: renderer.info.render.calls,
    triangles: renderer.info.render.triangles,
    activePointLights: lighting.activePointLights,
    activeSpotLights: lighting.activeSpotLights,
    drawingBufferWidth: renderer.domElement.width,
    drawingBufferHeight: renderer.domElement.height,
    pixelRatio: renderer.getPixelRatio(),
    renderScale: quality.renderScale,
    textures: renderer.info.memory.textures,
    geometries: renderer.info.memory.geometries,
    materials: sceneMaterialCount,
    programs: renderer.info.programs?.length ?? 0,
    qualityLevel: quality.level,
  };
  debugOverlay?.update(rawDelta, player.position, player.movementState, diagnostics);
}

requestAnimationFrame(frame);
