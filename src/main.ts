import {
  Cache,
  Mesh,
  PCFShadowMap,
  PerspectiveCamera,
  Scene,
  SRGBColorSpace,
  Timer,
  Vector3,
  WebGLRenderer,
} from 'three';
import { ThirdPersonCamera } from './camera/ThirdPersonCamera';
import { FixedStepClock } from './core/FixedStepClock';
import { InputController } from './input/InputController';
import { LocationAwareness } from './interaction/LocationAwareness';
import { PlayerController } from './player/PlayerController';
import { createPostProcessing } from './rendering/createPostProcessing';
import {
  applyInternalResolution,
  resolveQualityProfile,
  resolveToneMapping,
  VISUAL_STYLE,
} from './rendering/visualStyle';
import { DebugOverlay } from './ui/DebugOverlay';
import { LoadingVeil } from './ui/LoadingVeil';
import { LocationLabel } from './ui/LocationLabel';
import { createWorld } from './world/createWorld';
import './style.css';

// Shares decoded images between the many material variants that reuse one
// texture file, instead of decoding the same PNG once per variant.
Cache.enabled = true;

const app = document.querySelector<HTMLDivElement>('#app');

if (!app) {
  throw new Error('Application root element was not found.');
}

const scene = new Scene();
// Anti-aliasing is configured on the composer's render target instead: the
// default framebuffer this flag would multisample is never drawn to.
const renderer = new WebGLRenderer({ antialias: false });
const quality = resolveQualityProfile(window.location.search);
const toneMapping = resolveToneMapping(window.location.search);
applyInternalResolution(renderer, window.innerWidth, window.innerHeight, quality);
renderer.outputColorSpace = SRGBColorSpace;
renderer.toneMapping = toneMapping;
renderer.toneMappingExposure = VISUAL_STYLE.render.exposure;
renderer.info.autoReset = false;

if (VISUAL_STYLE.geometry.shadowsEnabled && quality.shadowMapSize > 0) {
  renderer.shadowMap.enabled = true;
  // PCFSoftShadowMap is deprecated in three 0.185 and silently falls back to
  // PCFShadowMap, so ask for it directly.
  renderer.shadowMap.type = PCFShadowMap;
}

app.appendChild(renderer.domElement);

const camera = new PerspectiveCamera(
  50,
  window.innerWidth / window.innerHeight,
  0.1,
  120,
);

const world = createWorld(scene, quality);
const input = new InputController(renderer.domElement);
const player = new PlayerController(world.collision);
scene.add(player.object);

const loadingVeil = new LoadingVeil();
const locationLabel = new LocationLabel();
const locationAwareness = new LocationAwareness();

const requestedView = import.meta.env.DEV
  ? new URLSearchParams(window.location.search).get('view')
  : null;

let requestedYaw = 0;
let requestedPitch = 0.31;
if (import.meta.env.DEV) {
  const developmentViews: Record<string, readonly [number, number, number?, number?]> = {
    'park-florist': [-13, -22],
    'bus-shelter': [-9, 27],
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
    pickup: [5, 16.5],
  };
  const requestedPosition = requestedView
    ? developmentViews[requestedView]
    : undefined;
  if (requestedPosition) {
    player.position.set(requestedPosition[0], 0, requestedPosition[1]);
    requestedYaw = requestedPosition[2] ?? 0;
    requestedPitch = requestedPosition[3] ?? 0.31;
  }
}

const thirdPersonCamera = new ThirdPersonCamera(
  camera,
  world.collision,
  requestedView === 'dreams-target' ? 2.9 : 1.05,
);
thirdPersonCamera.setOrbit(requestedYaw, requestedPitch);
thirdPersonCamera.snapTo(player.position);
const postProcessing = createPostProcessing(
  renderer,
  scene,
  camera,
  quality,
  toneMapping,
);

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

/**
 * Hold the opening frame until the hero models resolve, but never indefinitely:
 * a stalled or failed asset must not leave the player staring at black.
 */
const LOADING_VEIL_TIMEOUT_MS = 12000;
void Promise.race([
  world.ready,
  new Promise((resolve) => window.setTimeout(resolve, LOADING_VEIL_TIMEOUT_MS)),
]).then(() => {
  loadingVeil.dismiss();
});

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
    if (locationAwareness.update(player.position)) {
      locationLabel.render(locationAwareness.activeTarget);
    }
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
  debugOverlay?.update(
    rawDelta,
    player.position,
    player.movementState,
    diagnostics,
    locationAwareness.activeTarget?.name ?? null,
  );
}

requestAnimationFrame(frame);
