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
import {
  DEFAULT_CAMERA_PITCH,
  ORBIT_PIVOT_HEIGHT,
  ThirdPersonCamera,
} from './camera/ThirdPersonCamera';
import { TitleCamera } from './camera/TitleCamera';
import { FixedStepClock } from './core/FixedStepClock';
import { DeliveryInteraction } from './delivery/DeliveryInteraction';
import { InputController } from './input/InputController';
import { BikeInteraction } from './interaction/BikeInteraction';
import { STERLING_ASSISTED_SPEED, STERLING_BOOST_SPEED } from './vehicles/SterlingBike';
import { PlayerController } from './player/PlayerController';
import { createPostProcessing } from './rendering/createPostProcessing';
import { prepareScene } from './rendering/prepareScene';
import {
  applyInternalResolution,
  resolveQualityProfile,
  resolveToneMapping,
  type QualityProfile,
} from './rendering/visualStyle';
import { DebugOverlay } from './ui/DebugOverlay';
import { DeliveryDocket } from './ui/DeliveryDocket';
import { InteractionPrompt } from './ui/InteractionPrompt';
import { IntroScreen } from './ui/IntroScreen';
import { createWorld } from './world/createWorld';
import './style.css';

// Title screen on/off. While false the game drops straight into the world once
// it has loaded, with no card, prompt or entry sequence.
const SHOW_TITLE_SCREEN = true;

// Behind the title card the city is drawn at a fraction of its resolution: the
// browser's upscale is the defocus, and it costs less than the game itself.
const TITLE_RENDER_SCALE = 0.14;
// How long the street takes to open up once the player enters.
const CITY_HEARD_SECONDS = 4.5;
// The canvas eases from the title's soft image into full sharpness.
const TITLE_FOCUS_PULL_MS = 2600;
const TITLE_FOCUS_BLUR_PX = 7;

const app = document.querySelector<HTMLDivElement>('#app');

if (!app) {
  throw new Error('Application root element was not found.');
}

if (import.meta.env.DEV && new URLSearchParams(window.location.search).has('identity')) {
  // Look development: the graphic identity's parts and compositions on one board.
  document.querySelector('[data-intro]')?.remove();
  void import('./ui/identity/specimen').then(({ mountIdentitySpecimen }) => mountIdentitySpecimen());
}

// Installed before createWorld() so it observes every model and texture load.
const intro = new IntroScreen({
  // Development screenshot views should land straight in the world once loaded.
  enterAutomatically:
    !SHOW_TITLE_SCREEN ||
    (import.meta.env.DEV && new URLSearchParams(window.location.search).has('view')),
});

const scene = new Scene();
const renderer = new WebGLRenderer({ antialias: true });
const quality = resolveQualityProfile(window.location.search);
const toneMapping = resolveToneMapping(window.location.search);
let renderQuality: QualityProfile = intro.holdsWorld
  ? { ...quality, renderScale: Math.min(quality.renderScale, TITLE_RENDER_SCALE) }
  : quality;
applyInternalResolution(renderer, window.innerWidth, window.innerHeight, renderQuality);
renderer.outputColorSpace = SRGBColorSpace;
renderer.toneMapping = toneMapping.curve;
renderer.toneMappingExposure = toneMapping.exposure;
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
// Current audio sources remain available for local development, but none has
// repository-level release clearance yet (config/asset-rights.json).
const ambientAudio = import.meta.env.DEV
  ? new AmbientAudio({ veiled: intro.holdsWorld })
  : null;
const player = new PlayerController(world.collision);
scene.add(player.object);
const bikeInteraction = new BikeInteraction(world.sterlingFleet, player, world.collision);
const deliveryInteraction = new DeliveryInteraction(
  undefined,
  import.meta.env.DEV
    && new URLSearchParams(window.location.search).get('delivery') === 'carrying'
    ? 'in-transit'
    : 'awaiting-pickup',
);
const deliveryDocket = new DeliveryDocket();
const interactionPrompt = new InteractionPrompt();
// A bike covers more street than walking; pull the chase camera back to match.
const RIDING_BOOM_LENGTH = 7;
// Extra lens width reached at full boost speed. The boom length stays fixed:
// tying it to speed made the camera zoom in and out with every change of pace.
const BOOST_EXTRA_FIELD_OF_VIEW = 5;

const requestedView = import.meta.env.DEV
  ? new URLSearchParams(window.location.search).get('view')
  : null;

let requestedYaw = 0;
let requestedPitch = DEFAULT_CAMERA_PITCH;
if (import.meta.env.DEV) {
  const developmentViews: Record<string, readonly [number, number, number?, number?]> = {
    'park-florist': [-13.9, -18],
    'greek-gyros': [16, 10.8, -Math.PI / 2, 0.2],
    'come-through-lab': [-26, -15, Math.PI / 2, 0.2],
    'village-books': [-27, -3.5, Math.PI / 2, 0.16],
    'bus-shelter': [0, 27],
    'bus-stop-b': [-33.5, -53.6, -0.35, 0.1],
    'collision-dreams': [-3, 32.5, Math.PI],
    'dreams-target': [-3, 29.8, Math.PI],
    'dreams-angle': [-11, 29, 2.45, 0.18],
    // In the open gap south of Dreams, looking north at its rear wall.
    'dreams-rear': [4.6, 48.4, 0.32, 0.08],
    'north-road': [-17, -25.2, -Math.PI / 2, 0.24],
    'park-to-dreams': [-3, 18, Math.PI, 0.2],
    'street-detail': [6.4, -27.2, 0.42, 0.16],
    'public-light-pool': [-20, -18.2, 0, 0.18],
    'between-light-pools': [-14.8, -19.7, 0, 0.18],
    // A park north-edge sodium column seen from the park, head against the sky.
    'streetlights': [-17.5, -12.5, 0.36, -0.12],
    'west-street': [-29.5, 25],
    'west-shops': [-29.5, 7],
    'east-shops': [29.5, 19],
    // Renee's Thomas Street frontage from across the road (surface pass).
    'renee': [17, -25.5, 0, 0.04],
    // Gulliver's tiled Oldham Street frontage from across the road (surface pass).
    'gullivers': [27.9, -25.5, 0, 0.04],
    // The Hive's west frontage from across Lever Street (surface pass).
    'the-hive': [24, 24, -Math.PI / 2 - 0.2, -0.3],
    'south-shops': [0, 22],
    'cass-art': [-16.6, 27.5, Math.PI, 0.08],
    'south-road': [0, 53.5, Math.PI, 0.24],
    'vinyl-exchange': [-7, 58.2, 0, 0.08],
    'real-camera': [-11.5, 58, Math.PI, 0.06],
    'real-camera-corner': [-26, 58.5, 2.3, 0.06],
    'advanced-photo': [11.8, 59.4, Math.PI, 0.12],
    'spice-cabin': [12.35, 57.6, 0, 0.03],
    'spice-cabin-close': [11.0, 56.4, 0, 0.06],
    'spice-cabin-gable': [4.6, 57.2, -0.36, 0.1],
    // Beside the stack, not in front of it: the chase camera would put the player over it.
    'spice-cabin-pallets': [1.6, 56.4, -0.6, 0.2],
    'pallets-north': [-7.8, -31, 0.9, 0.2],
    'mcr1': [-29.5, -24.5, 0, 0.12],
    'mcr1-corner': [-39.5, -26.5, -0.7, 0.12],
    'pallets-west': [-43, 0, -2.35, 0.2],
    'pallets-east': [43, -7, -2.2, 0.2],
    'sterling-south': [-16.6, 19.6, Math.PI / 2 - 0.35, 0.16],
    'sterling-east': [42.6, -4.4, Math.PI / 2 + 0.35, 0.16],
    'delivery-pickup': [-16.9, -27.1, 0, 0.16],
    // Nice Things surface pass: the textured shopfront from the kerb.
    'nice-things': [-16.2, -28.8, 0, 0.02],
    'delivery-dropoff': [-7, 55.35, 0, 0.16],
    // ABC Building across the Outer North Road: street view, Clints doorway,
    // Side Street on Lower Byrom Street, and the tower seen from the park.
    'abc': [-4, -54.2, 0, 0.02],
    'abc-clints': [-2.8, -60.6, 0.25, 0.1],
    'abc-side-street': [25.4, -67.5, Math.PI / 2 - 0.35, 0.08],
    'abc-tower': [-4, -17.5, 0, -0.3],
    // From the moved Outer North Road, looking south at the backs of Renee and Gulliver's.
    'north-block-rear': [20, -54.2, Math.PI, 0.12],
    pickup: [5, 16.5],
  };
  const requestedPosition = requestedView
    ? developmentViews[requestedView]
    : undefined;
  if (requestedPosition) {
    player.position.set(requestedPosition[0], 0, requestedPosition[1]);
    player.recoverFromCollisionOverlap();
    requestedYaw = requestedPosition[2] ?? 0;
    requestedPitch = requestedPosition[3] ?? DEFAULT_CAMERA_PITCH;
  }
}

const thirdPersonCamera = new ThirdPersonCamera(
  camera,
  requestedView === 'dreams-target' ? 2.9 : ORBIT_PIVOT_HEIGHT,
  world.collision,
);
thirdPersonCamera.setOrbit(requestedYaw, requestedPitch);
thirdPersonCamera.snapTo(player.position);
const titleCamera = new TitleCamera(camera, intro.holdsWorld);
const postProcessing = createPostProcessing(
  renderer,
  scene,
  camera,
  quality,
  toneMapping,
);

const sceneReady = intro
  .waitForAssets()
  .then(() => prepareScene(renderer, scene, camera))
  .catch((error: unknown) => console.error('Scene preparation failed', error));
void sceneReady.then(() => intro.setReady());

void intro.whenEntering().then(() => ambientAudio?.unveil(CITY_HEARD_SECONDS));
void intro.whenRevealing().then(() => {
  titleCamera.release();
  if (renderQuality === quality) return;
  renderQuality = quality;
  resize();
  pullFocus(renderer.domElement);
});

const debugOverlay = import.meta.env.DEV ? new DebugOverlay() : null;
if (import.meta.env.DEV) {
  // Console access for look-development experiments (lighting, materials).
  (window as unknown as { zealot: unknown }).zealot = {
    scene,
    ready: sceneReady,
    renderer,
    camera,
    player,
    collision: world.collision,
    atmosphere: world.atmosphere,
    // Stage 2 of the realism pass: `zealot.grade.getParameters()` /
    // `zealot.grade.set({...})`, the same shape as `atmosphere` above.
    grade: {
      getParameters: postProcessing.getGradeParameters,
      set: postProcessing.setGradeParameters,
    },
    sterlingFleet: world.sterlingFleet,
    bikeInteraction,
    deliveryInteraction,
    input,
  };
}

const timer = new Timer();
timer.connect(document);
const simulationClock = new FixedStepClock();
const cameraForward = new Vector3();
// Hidden by default; H toggles them, and ?overlays=on starts with them shown.
let developmentOverlaysVisible = new URLSearchParams(window.location.search).get('overlays') === 'on';
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
  applyInternalResolution(renderer, window.innerWidth, window.innerHeight, renderQuality);
  postProcessing.resize(window.innerWidth, window.innerHeight);
}

// Hands the frame from the title's soft, low-resolution image to the game's
// full resolution without a visible jump in sharpness.
function pullFocus(canvas: HTMLCanvasElement): void {
  canvas.style.filter = `blur(${TITLE_FOCUS_BLUR_PX}px)`;
  void canvas.offsetWidth;
  canvas.style.transition = `filter ${TITLE_FOCUS_PULL_MS}ms cubic-bezier(0.2, 0.7, 0.2, 1)`;
  canvas.style.filter = 'blur(0px)';
  window.setTimeout(() => {
    canvas.style.removeProperty('filter');
    canvas.style.removeProperty('transition');
  }, TITLE_FOCUS_PULL_MS + 100);
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
    // The rider waits where the night begins while the title card holds the frame.
    if (!titleCamera.holdsPlayer) {
      // Delivery gets first refusal on E only at its active address; everywhere
      // else the same queued press remains available to the bike interaction.
      deliveryInteraction.update(input, player.position, bikeInteraction.isRiding);
      bikeInteraction.update(fixedDelta, input, cameraForward);
    } else {
      // An E pressed over the title card must not take a bike on entry.
      input.consumeInteract();
    }
    world.update(fixedDelta, player.position);
    elapsedSeconds += fixedDelta;
  });
  const cameraDelta = simulationResult.resetAfterExtremeGap ? 0 : rawDelta;
  const ridingSpeed = Math.abs(bikeInteraction.bike?.speed ?? 0);
  const boostFraction = Math.min(
    1,
    Math.max(0, (ridingSpeed - STERLING_ASSISTED_SPEED) / (STERLING_BOOST_SPEED - STERLING_ASSISTED_SPEED)),
  );
  thirdPersonCamera.setBoomLength(
    bikeInteraction.isRiding
      ? RIDING_BOOM_LENGTH
      : thirdPersonCamera.baseDistance,
  );
  thirdPersonCamera.setFieldOfView(
    thirdPersonCamera.fieldOfView + BOOST_EXTRA_FIELD_OF_VIEW * boostFraction,
  );
  thirdPersonCamera.update(cameraDelta, input, bikeInteraction.cameraTarget);
  interactionPrompt.update(
    rawDelta,
    titleCamera.holdsPlayer ? null : deliveryInteraction.prompt ?? bikeInteraction.prompt,
    bikeInteraction.isRiding,
  );
  deliveryDocket.update(deliveryInteraction.view, titleCamera.holdsPlayer);
  titleCamera.apply(cameraDelta);
  player.updateCameraVisibility(camera.position);

  renderer.info.reset();
  postProcessing.render(elapsedSeconds);
  const lighting = world.getLightingStats();
  const diagnostics = {
    drawCalls: renderer.info.render.calls,
    triangles: renderer.info.render.triangles,
    activePointLights: lighting.activePointLights,
    activeSpotLights: lighting.activeSpotLights,
    registeredPointLights: lighting.registeredPointLights,
    maximumActiveLocalLights: lighting.maximumActiveLocalLights,
    activeLocalLightGroups: lighting.activeLocalLightGroups,
    drawingBufferWidth: renderer.domElement.width,
    drawingBufferHeight: renderer.domElement.height,
    pixelRatio: renderer.getPixelRatio(),
    renderScale: renderQuality.renderScale,
    textures: renderer.info.memory.textures,
    geometries: renderer.info.memory.geometries,
    materials: sceneMaterialCount,
    programs: renderer.info.programs?.length ?? 0,
    qualityLevel: quality.level,
  };
  debugOverlay?.update(rawDelta, player.position, player.movementState, diagnostics);
}

requestAnimationFrame(frame);
