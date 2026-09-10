export interface FixedStepResult {
  readonly rawDelta: number;
  readonly simulatedDelta: number;
  readonly substeps: number;
  readonly interpolationAlpha: number;
  readonly resetAfterExtremeGap: boolean;
}

export class FixedStepClock {
  private accumulator = 0;

  constructor(
    readonly step = 1 / 60,
    readonly maximumSubsteps = 16,
    readonly extremeGapThreshold = 0.25,
  ) {}

  advance(rawDelta: number, update: (fixedDelta: number) => void): FixedStepResult {
    if (
      !Number.isFinite(rawDelta)
      || rawDelta < 0
      || rawDelta > this.extremeGapThreshold
    ) {
      this.reset();
      return {
        rawDelta,
        simulatedDelta: 0,
        substeps: 0,
        interpolationAlpha: 0,
        resetAfterExtremeGap: true,
      };
    }

    this.accumulator += rawDelta;
    let substeps = 0;

    while (this.accumulator >= this.step && substeps < this.maximumSubsteps) {
      update(this.step);
      this.accumulator -= this.step;
      substeps += 1;
    }

    return {
      rawDelta,
      simulatedDelta: substeps * this.step,
      substeps,
      interpolationAlpha: this.accumulator / this.step,
      resetAfterExtremeGap: false,
    };
  }

  reset(): void {
    this.accumulator = 0;
  }
}
