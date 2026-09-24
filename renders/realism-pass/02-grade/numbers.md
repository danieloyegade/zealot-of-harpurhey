# Stage 2 — after the grade retune

Captured 2026-09-24, Chromium/SwiftShader (software rasteriser — no
meaningful fps here, same caveat as Stage 1), `?quality=high`, 1280x720.

First-pass, not-yet-approved values (see docs/REALISM_PASS_PLAN.md Stage 2
for the "done when" gate this still owes):

- saturation 1.12 -> 1.0
- blackLift 0 -> 0.045
- splitTone: shadowTint #8fb4c9, highlightTint #dcb98c, strength 0.16,
  edges 0.12/0.72
- bloom radius 0.32 -> 0.22, threshold 0.88 -> 0.92,
  strength 0.3/0.34 -> 0.24/0.26 (medium/high)

Compare against `renders/realism-pass/01-retro-settings-off/` (Stage 1,
same views) and the reference in `renders/visual-gap-2026-09-24/`.
Tune live with `zealot.grade.set({...})` in the dev console and report
back the numbers that read best next to the reference.
