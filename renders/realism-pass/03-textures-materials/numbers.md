# Stage 3 — after material settings (3b)

Captured 2026-09-24, Chromium/SwiftShader (software rasteriser — no
meaningful fps here, same caveat as Stages 1-2), `?quality=high`, 1280x720.

Changes visible in these shots:
- Dreams `mat-dreams-photographic-front` roughness 0.82 -> 0.45: a soft
  highlight band is now visible under the fascia tubes, where before the
  panel was evenly matte.
- Glass roughness clamped to <=0.05 (spice-cabin.png, bus-shelter.png):
  no visible artefacts; reflections themselves wait on Stage 4's
  environment map, so this is a quiet, forward-compatible change today.

No new texture content shipped in this stage (3c, the real 2K Dreams
texture set, needs Daniel + Blender + real photographic reference — see
docs/REALISM_PASS_PLAN.md Stage 3).

Compare against `renders/realism-pass/02-grade/dreams-target.png` (Stage 2,
same view) and the reference in `renders/visual-gap-2026-09-24/`.
