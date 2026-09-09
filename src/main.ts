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
import { DebugOverlay } from './ui/DebugOverlay';
import { createWorld } from './world/createWorld';
import './style.css';

const app = document.querySelector<HTMLDivElement>('#app');

if (!app) {
  throw new Error('Application root element was not found.');
}

const scene = new Scene();
const renderer = new WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = SRGBColorSpace;
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

const thirdPersonCamera = new ThirdPersonCamera(camera);
thirdPersonCamera.snapTo(player.position);

const debugOverlay = import.meta.env.DEV ? new DebugOverlay() : null;
const timer = new Timer();
timer.connect(document);
const cameraForward = new Vector3();

function resize(): void {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(window.innerWidth, window.innerHeight);
}

window.addEventListener('resize', resize);

function frame(timestamp: number): void {
  requestAnimationFrame(frame);

  timer.update(timestamp);
  const deltaTime = Math.min(timer.getDelta(), 0.05);

  input.update();
  thirdPersonCamera.getPlanarForward(cameraForward);
  player.update(deltaTime, input, cameraForward);
  thirdPersonCamera.update(deltaTime, input, player.position);
  debugOverlay?.update(deltaTime, player.position, player.movementState);
  renderer.render(scene, camera);
}

requestAnimationFrame(frame);
