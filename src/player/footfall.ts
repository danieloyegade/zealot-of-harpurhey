/**
 * A foot lands each time the walk cycle's thigh swing reaches an extreme, which
 * is every half turn of the stride phase starting at a quarter turn. Returns
 * true when the phase moving from `previous` to `current` crosses one.
 */
export function crossedFootfall(previousPhase: number, currentPhase: number): boolean {
  const beat = (phase: number): number => Math.floor((phase - Math.PI / 2) / Math.PI);
  return beat(currentPhase) !== beat(previousPhase);
}
