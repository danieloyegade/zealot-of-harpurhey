import {
  BoxGeometry,
  Color,
  DirectionalLight,
  HemisphereLight,
  Mesh,
  MeshStandardMaterial,
  PerspectiveCamera,
  PlaneGeometry,
  Scene,
  SRGBColorSpace,
  WebGLRenderer,
} from 'three';
import './style.css';

const app = document.querySelector<HTMLDivElement>('#app');

if (!app) {
  throw new Error('Application root element was not found.');
}

const scene = new Scene();
scene.background = new Color(0x050711);

const camera = new PerspectiveCamera(
  50,
  window.innerWidth / window.innerHeight,
  0.1,
  100,
);
camera.position.set(5, 4, 7);
camera.lookAt(0, 0.75, 0);

const renderer = new WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = SRGBColorSpace;
app.appendChild(renderer.domElement);

const ground = new Mesh(
  new PlaneGeometry(20, 20),
  new MeshStandardMaterial({ color: 0x151925, roughness: 1 }),
);
ground.rotation.x = -Math.PI / 2;
scene.add(ground);

const cube = new Mesh(
  new BoxGeometry(1.5, 1.5, 1.5),
  new MeshStandardMaterial({ color: 0xc49a32, roughness: 0.8 }),
);
cube.position.y = 0.75;
scene.add(cube);

scene.add(new HemisphereLight(0x68759d, 0x17120c, 1.5));

const streetLight = new DirectionalLight(0xffd99a, 2.5);
streetLight.position.set(3, 6, 4);
scene.add(streetLight);

function resize(): void {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(window.innerWidth, window.innerHeight);
}

window.addEventListener('resize', resize);

function render(): void {
  renderer.render(scene, camera);
  requestAnimationFrame(render);
}

render();
