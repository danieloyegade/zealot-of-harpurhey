export type DeliveryPhase = 'awaiting-pickup' | 'in-transit' | 'complete';

/** The intentionally small first-loop state machine, kept pure for testing. */
export function advanceDeliveryPhase(phase: DeliveryPhase): DeliveryPhase {
  switch (phase) {
    case 'awaiting-pickup':
      return 'in-transit';
    case 'in-transit':
      return 'complete';
    case 'complete':
      return 'complete';
  }
}
