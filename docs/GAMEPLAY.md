# Gameplay systems

The game currently has one complete delivery loop and one reusable vehicle interaction. This document records implemented behaviour, not the wider narrative backlog.

## Contextual interaction

`InputController` owns a one-shot E queue. `DeliveryInteraction` gets first refusal only when the player is on foot and within reach of the active delivery address; otherwise the queued press remains available to `BikeInteraction`. The screen shows one `InteractionPrompt`, so overlapping systems cannot produce competing key prompts.

Future interaction domains should extend this priority deliberately rather than each adding its own key listener or UI.

## Delivery 001 — Flowers

The title card, runtime and tests all read `src/delivery/firstDelivery.ts`.

1. The player starts with a docket reading **COLLECT — Nice Things**.
2. At the florist's south shutter, E collects the flowers.
3. The docket changes to **DELIVER — Vinyl Exchange / Upper floor**.
4. At Vinyl Exchange's south frontage, E leaves the flowers.
5. The docket records **RECEIVED — £3.70**.

The state machine is intentionally only `awaiting-pickup → in-transit → complete`. There is no timer, rank, XP, route arrow, minimap or failure screen. Refreshing begins a new night; persistence is not yet implemented.

For focused development checks, `?view=delivery-pickup` opens at Nice Things and `?view=delivery-dropoff&delivery=carrying` opens at Vinyl Exchange with the flowers already collected. The phase override is development-only.

## Sterling bikes

On foot, E takes a nearby docked or parked Sterling bike. W pedals, Shift enables assist, Space boosts, A/D steer and S brakes or reverses. E returns a slow bike at an available dock, or requests a controlled dismount elsewhere. Camera targeting and player pose follow the active bike state.

## Next gameplay boundary

Add breadth only after this first loop has been playtested end to end. The next useful work is feedback and authored consequence—an NPC handoff, a small environmental change, or persistent delivery state—not a parallel quest framework.
