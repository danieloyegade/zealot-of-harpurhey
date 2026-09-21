import { type Group, PointLight } from 'three';
import { applyBougainvilleaTexturePolicy } from './busShelterMaterials';
import { circleObstacle, type CollisionObstacle, orientedBoxObstacle } from './collision';
import { loadModel } from './loadModel';
import type { LocalLightRegistry } from './localLighting';
import { mergeStaticModelMeshes } from './mergeStaticModelMeshes';
import { BOUGAINVILLEA_FENCE_SCENE } from './worldLayout';

const VERSION = 'v=placed-20260921';
const { scale, rotationY, hero, extension, signpost, gap } = BOUGAINVILLEA_FENCE_SCENE;

// In authored metres, scaled at runtime with the models. The fence and the
// climber's densest growth stay within these depths of the fence line, so one
// strip covers them across the whole gap. Flowers reaching further out hang
// above head height or are too sparse to walk into.
const FENCE_BEHIND = 0.18;
const FENCE_IN_FRONT = 0.38;
const FENCE_HEIGHT = 2.0;
const SIGNPOST_RADIUS = 0.08;
const SIGNPOST_HEIGHT = 3.3;

// The sign lamp's housing sits on the column head (3.25 m) and overhangs the
// sign face by 0.125 m, authored. The light hangs just under its lens.
const LAMP_HEIGHT = 3.18;
const LAMP_OVERHANG = 0.125;
const LAMP_COLOUR = 0xffd6a0;
const LAMP_INTENSITY = 16;
const LAMP_DISTANCE = 10;

export function addBougainvilleaFenceCollision(obstacles: CollisionObstacle[]): void {
  const back = hero.x - FENCE_BEHIND * scale;
  const front = hero.x + FENCE_IN_FRONT * scale;
  obstacles.push(
    orientedBoxObstacle(
      'Bougainvillea fence and climber',
      (back + front) / 2,
      (gap.minZ + gap.maxZ) / 2,
      front - back,
      gap.maxZ - gap.minZ,
      0,
      FENCE_HEIGHT * scale,
    ),
    circleObstacle(
      'No Entry signpost',
      signpost.x,
      signpost.z,
      SIGNPOST_RADIUS * scale,
      SIGNPOST_HEIGHT * scale,
    ),
  );
}

/**
 * The sign lamp as a real light: a warm pool over the sign that reaches back
 * across the flowers. It is a location light, so it stays on while the fence
 * is in the nearby composition rather than only when the player stands under it.
 */
export function addBougainvilleaSignLamp(localLights: LocalLightRegistry): void {
  const light = new PointLight(LAMP_COLOUR, LAMP_INTENSITY, LAMP_DISTANCE, 2);
  light.name = 'Bougainvillea sign lamp';
  // The signpost's +Z faces east after its quarter turn.
  light.position.set(signpost.x + LAMP_OVERHANG * scale, LAMP_HEIGHT * scale, signpost.z);
  localLights.register({
    name: 'Bougainvillea sign lamp',
    lights: [light],
    priority: 1.1,
    selectionMode: 'location-relevance',
    activationRadius: 18,
  });
}

/** Loads the fence, its extension and the signpost into the Village Books–Coral gap. */
export async function addBougainvilleaFenceScene(
  root: Group,
  groundAt: (x: number, z: number) => number,
): Promise<void> {
  try {
    const models = await Promise.all([
      loadModel(`assets/models/bougainvillea/BGV_fence_bougainvillea.glb?${VERSION}`),
      loadModel(`assets/models/bougainvillea/BGV_fence_extension.glb?${VERSION}`),
      loadModel(`assets/models/bougainvillea/BGV_signpost_no_entry.glb?${VERSION}`),
    ]);
    const placements = [
      ['Bougainvillea fence hero section', hero],
      ['Bougainvillea fence extension section', extension],
      ['No Entry signpost with sign lamp', signpost],
    ] as const;
    models.forEach((model, index) => {
      const [name, { x, z }] = placements[index];
      applyBougainvilleaTexturePolicy(model);
      mergeStaticModelMeshes(model);
      model.name = name;
      model.scale.setScalar(scale);
      model.rotation.y = rotationY;
      model.position.set(x, groundAt(x, z), z);
      root.add(model);
    });
  } catch (error) {
    console.error('[World] Failed to load the bougainvillea fence scene. Only its collision remains.', error);
  }
}
