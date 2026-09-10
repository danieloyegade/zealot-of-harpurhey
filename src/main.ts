import {
  PerspectiveCamera,
  Scene,
  SRGBColorSpace,
  Timer,
  Vector3,
  WebGLRenderer,
} from 'three';
import { ThirdPersonCamera } from './camera/ThirdPersonCamera';
import { InputController } from './input/InputController';
import { PlayerController } from './player/PlayerController';
import { createPostProcessing } from './rendering/createPostProcessing';
import {
  applyInternalResolution,
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
applyInternalResolution(renderer, window.innerWidth, window.innerHeight);
renderer.outputColorSpace = SRGBColorSpace;
renderer.toneMappingExposure = VISUAL_STYLE.render.exposure;
app.appendChild(renderer.domElement);

const camera = new PerspectiveCamera(
  50,
  window.innerWidth / window.innerHeight,
  0.1,
  120,
);

const world = createWorld(scene);
const input = new InputController(renderer.domElement);
const player = new PlayerController(world.collision);
scene.add(player.object);

const requestedView = import.meta.env.DEV
  ? new URLSearchParams(window.location.search).get('view')
  : null;

if (import.meta.env.DEV) {
  const developmentViews: Record<string, readonly [number, number]> = {
    'park-florist': [-13, -22],
    'bus-shelter': [-9, 27],
    'collision-dreams': [0, -31],
    'dreams-target': [0, -18.8],
    'west-street': [-29.5, 25],
    'west-shops': [-29.5, 7],
    'east-shops': [29.5, 19],
    'south-shops': [0, 22],
    pickup: [5, 16.5],
  };
  const requestedPosition = requestedView
    ? developmentViews[requestedView]
    : undefined;
  if (requestedPosition) {
    player.position.set(requestedPosition[0], 0, requestedPosition[1]);
  }
}

const thirdPersonCamera = new ThirdPersonCamera(
  camera,
  requestedView === 'dreams-target' ? 3.15 : 1.05,
);
thirdPersonCamera.snapTo(player.position);
const postProcessing = createPostProcessing(renderer, scene, camera);

const debugOverlay = import.meta.env.DEV ? new DebugOverlay() : null;
const timer = new Timer();
timer.connect(document);
const cameraForward = new Vector3();
let developmentOverlaysVisible = true;
let elapsedSeconds = 0;

function resize(): void {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  applyInternalResolution(renderer, window.innerWidth, window.innerHeight);
  postProcessing.resize(window.innerWidth, window.innerHeight);
}

window.addEventListener('resize', resize);

function frame(timestamp: number): void {
  requestAnimationFrame(frame);

  timer.update(timestamp);
  const deltaTime = Math.min(timer.getDelta(), 0.05);
  elapsedSeconds += deltaTime;

  input.update();
  if (input.consumeOverlayToggle()) {
    developmentOverlaysVisible = !developmentOverlaysVisible;
    world.setDevelopmentOverlaysVisible(developmentOverlaysVisible);
    debugOverlay?.setVisible(developmentOverlaysVisible);
  }
  thirdPersonCamera.getPlanarForward(cameraForward);
  player.update(deltaTime, input, cameraForward);
  world.update(deltaTime);
  thirdPersonCamera.update(deltaTime, input, player.position);
  debugOverlay?.update(deltaTime, player.position, player.movementState);
  postProcessing.render(elapsedSeconds);
}

requestAnimationFrame(frame);
