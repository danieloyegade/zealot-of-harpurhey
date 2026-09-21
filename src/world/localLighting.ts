import { Group, PointLight, Vector3 } from 'three';

export interface LocalLightInstallationDefinition {
  /** Human-readable installation name used by the development diagnostics. */
  readonly name: string;
  /**
   * Lights that must switch together. Keeping pairs atomic prevents LOW from
   * selecting only the left or right half of a deliberately balanced setup.
   */
  readonly lights: readonly PointLight[];
  /** Higher values win close ranking decisions; ordinary locations use 1. */
  readonly priority?: number;
  /**
   * Location lights remain useful while their lit façade/threshold is in the
   * nearby composition. Public lights instead require direct player reach.
   */
  readonly selectionMode?: 'player-contribution' | 'location-relevance';
  /** Horizontal relevance radius, required by location-relevance selection. */
  readonly activationRadius?: number;
  /** Runtime multiplier for proximity-responsive installations. */
  readonly intensityScale?: () => number;
}

export interface LocalLightRegistryStats {
  readonly activePointLights: number;
  readonly registeredPointLights: number;
  readonly activePointLightNames: readonly string[];
  readonly activeLocalLightGroups: readonly string[];
  readonly maximumActiveLocalLights: number;
}

type RuntimeLight = {
  readonly light: PointLight;
  readonly baseIntensity: number;
};

type RuntimeInstallation = {
  readonly name: string;
  readonly lights: readonly RuntimeLight[];
  readonly priority: number;
  readonly selectionMode: 'player-contribution' | 'location-relevance';
  readonly activationRadius?: number;
  readonly intensityScale?: () => number;
  readonly stableOrder: number;
  desired: boolean;
  visible: boolean;
  fade: number;
  contributionRatio: number;
  horizontalDistance: number;
  selectionRatio: number;
};

const PLAYER_LIGHT_SAMPLE_HEIGHT = 1.1;
const ENTER_CONTRIBUTION_RATIO = 0.92;
const EXIT_CONTRIBUTION_RATIO = 1.08;
const STICKY_RANKING_MULTIPLIER = 0.9;
const FADE_IN_SECONDS = 0.25;
const FADE_OUT_SECONDS = 0.18;

/**
 * Owns every real-time local point light in the world.
 *
 * Registered lights are never rendered themselves. The scene holds a fixed
 * pool of `maximumActiveLocalLights` point lights that are always visible, and
 * each frame the pool copies the position, colour, range and faded intensity
 * of the installations currently switched on; spare slots sit at intensity 0.
 * Three.js keys every lit shader on the number of visible point lights, so
 * letting that number change recompiled every lit material in view — a
 * one-to-three-second freeze each time a new installation came on.
 *
 * The selector ranks atomic lighting installations by either real point-light
 * reach at the player's torso or authored location relevance for thresholds
 * and facades. It avoids filling the budget with the nearest objects when
 * their attenuation or composition role cannot help the current view.
 */
export class LocalLightRegistry {
  private readonly installations: RuntimeInstallation[] = [];
  private readonly registeredLights = new Set<PointLight>();
  private readonly slots: PointLight[] = [];
  private readonly slotOwners: (RuntimeLight | null)[] = [];

  constructor(
    private readonly root: Group,
    private readonly maximumActiveLocalLights: number,
  ) {
    for (let index = 0; index < Math.max(0, maximumActiveLocalLights); index += 1) {
      const slot = new PointLight(0xffffff, 0, 1, 2);
      slot.name = `Local light slot ${index + 1}`;
      root.add(slot);
      this.slots.push(slot);
      this.slotOwners.push(null);
    }
  }

  register(definition: LocalLightInstallationDefinition): void {
    if (definition.lights.length === 0) {
      return;
    }
    if (definition.priority !== undefined && definition.priority <= 0) {
      throw new Error(`Local-light priority must be positive: ${definition.name}`);
    }
    if (
      definition.activationRadius !== undefined &&
      definition.activationRadius <= 0
    ) {
      throw new Error(
        `Local-light activation radius must be positive: ${definition.name}`,
      );
    }
    if (
      definition.selectionMode === 'location-relevance' &&
      definition.activationRadius === undefined
    ) {
      throw new Error(
        `Location-relevance lights need an activation radius: ${definition.name}`,
      );
    }

    const lights = definition.lights.map((light) => {
      if (this.registeredLights.has(light)) {
        throw new Error(`Point light registered twice: ${light.name}`);
      }
      if (light.distance <= 0) {
        throw new Error(
          `Managed point lights need a finite range: ${light.name}`,
        );
      }
      this.registeredLights.add(light);
      const runtimeLight = {
        light,
        baseIntensity: light.intensity,
      };
      // A template for the pool, not a scene light: it stays hidden for good.
      light.intensity = 0;
      light.visible = false;
      this.root.add(light);
      return runtimeLight;
    });

    this.installations.push({
      name: definition.name,
      lights,
      priority: definition.priority ?? 1,
      selectionMode: definition.selectionMode ?? 'player-contribution',
      activationRadius: definition.activationRadius,
      intensityScale: definition.intensityScale,
      stableOrder: this.installations.length,
      desired: false,
      visible: false,
      fade: 0,
      contributionRatio: Number.POSITIVE_INFINITY,
      horizontalDistance: Number.POSITIVE_INFINITY,
      selectionRatio: Number.POSITIVE_INFINITY,
    });
  }

  update(deltaTime: number, playerPosition: Vector3): void {
    const ranked = this.installations
      .filter((installation) => {
        this.measureContribution(installation, playerPosition);
        const exitMultiplier = installation.desired
          ? EXIT_CONTRIBUTION_RATIO
          : ENTER_CONTRIBUTION_RATIO;
        installation.selectionRatio =
          installation.selectionMode === 'location-relevance'
            ? installation.horizontalDistance /
              (installation.activationRadius ?? 1)
            : installation.contributionRatio;
        const withinPrimaryRange =
          installation.selectionRatio <= exitMultiplier;
        const withinOptionalActivationCap =
          installation.selectionMode === 'location-relevance' ||
          installation.activationRadius === undefined ||
          installation.horizontalDistance <=
            installation.activationRadius * exitMultiplier;
        return withinPrimaryRange && withinOptionalActivationCap;
      })
      .map((installation) => ({
        installation,
        score:
          (installation.selectionRatio / installation.priority) *
          (installation.desired ? STICKY_RANKING_MULTIPLIER : 1),
      }))
      .sort(
        (a, b) =>
          a.score - b.score ||
          a.installation.stableOrder - b.installation.stableOrder,
      );

    const desired = new Set<RuntimeInstallation>();
    let remainingBudget = Math.max(0, this.maximumActiveLocalLights);
    for (const candidate of ranked) {
      const cost = candidate.installation.lights.length;
      if (cost > remainingBudget) {
        continue;
      }
      desired.add(candidate.installation);
      remainingBudget -= cost;
    }

    for (const installation of this.installations) {
      installation.desired = desired.has(installation);
    }

    const step = Math.max(0, deltaTime);
    for (const installation of this.installations) {
      if (!installation.visible) {
        continue;
      }
      installation.fade = installation.desired
        ? Math.min(1, installation.fade + step / FADE_IN_SECONDS)
        : Math.max(0, installation.fade - step / FADE_OUT_SECONDS);
      if (installation.fade === 0 && !installation.desired) {
        installation.visible = false;
      }
    }

    let visibleLightCount = this.countVisiblePointLights();
    for (const candidate of ranked) {
      const installation = candidate.installation;
      if (!installation.desired || installation.visible) {
        continue;
      }
      const cost = installation.lights.length;
      if (visibleLightCount + cost > this.maximumActiveLocalLights) {
        continue;
      }
      installation.visible = true;
      installation.fade = Math.min(1, step / FADE_IN_SECONDS);
      visibleLightCount += cost;
    }

    for (const installation of this.installations) {
      const runtimeScale = installation.intensityScale?.() ?? 1;
      const intensityScale = installation.fade * Math.max(0, runtimeScale);
      for (const runtimeLight of installation.lights) {
        runtimeLight.light.intensity =
          runtimeLight.baseIntensity * intensityScale;
      }
    }

    this.updateSlots();

    if (import.meta.env.DEV) {
      console.assert(
        this.countVisiblePointLights() <= this.maximumActiveLocalLights,
        'Local point-light budget exceeded.',
      );
    }
  }

  getStats(): LocalLightRegistryStats {
    const activeInstallations = this.installations.filter(
      (installation) => installation.visible,
    );
    return {
      activePointLights: activeInstallations.reduce(
        (total, installation) => total + installation.lights.length,
        0,
      ),
      registeredPointLights: this.registeredLights.size,
      activePointLightNames: activeInstallations.flatMap((installation) =>
        installation.lights.map(({ light }) => light.name),
      ),
      activeLocalLightGroups: activeInstallations.map(
        (installation) => installation.name,
      ),
      maximumActiveLocalLights: this.maximumActiveLocalLights,
    };
  }

  private measureContribution(
    installation: RuntimeInstallation,
    playerPosition: Vector3,
  ): void {
    let contributionRatio = Number.POSITIVE_INFINITY;
    let horizontalDistanceSquared = Number.POSITIVE_INFINITY;
    const sampleY = playerPosition.y + PLAYER_LIGHT_SAMPLE_HEIGHT;

    for (const { light } of installation.lights) {
      const deltaX = light.position.x - playerPosition.x;
      const deltaY = light.position.y - sampleY;
      const deltaZ = light.position.z - playerPosition.z;
      const distance = Math.sqrt(
        deltaX * deltaX + deltaY * deltaY + deltaZ * deltaZ,
      );
      contributionRatio = Math.min(
        contributionRatio,
        distance / light.distance,
      );
      horizontalDistanceSquared = Math.min(
        horizontalDistanceSquared,
        deltaX * deltaX + deltaZ * deltaZ,
      );
    }

    installation.contributionRatio = contributionRatio;
    installation.horizontalDistance = Math.sqrt(horizontalDistanceSquared);
  }

  /**
   * Keeps each lit installation on the slots it already holds, so a light
   * never jumps between slots mid-fade, then hands free slots to newcomers.
   */
  private updateSlots(): void {
    const lit = new Set<RuntimeLight>();
    for (const installation of this.installations) {
      if (installation.visible) {
        installation.lights.forEach((runtimeLight) => lit.add(runtimeLight));
      }
    }

    for (let index = 0; index < this.slots.length; index += 1) {
      const owner = this.slotOwners[index];
      if (owner && lit.has(owner)) {
        lit.delete(owner);
      } else {
        this.slotOwners[index] = null;
      }
    }

    const newcomers = lit.values();
    for (let index = 0; index < this.slots.length; index += 1) {
      if (this.slotOwners[index] === null) {
        this.slotOwners[index] = newcomers.next().value ?? null;
      }
    }

    for (let index = 0; index < this.slots.length; index += 1) {
      const slot = this.slots[index];
      const owner = this.slotOwners[index];
      if (!owner) {
        slot.intensity = 0;
        continue;
      }
      const { light } = owner;
      slot.position.copy(light.position);
      slot.color.copy(light.color);
      slot.distance = light.distance;
      slot.decay = light.decay;
      slot.intensity = light.intensity;
    }
  }

  private countVisiblePointLights(): number {
    return this.installations.reduce(
      (total, installation) =>
        total + (installation.visible ? installation.lights.length : 0),
      0,
    );
  }
}
