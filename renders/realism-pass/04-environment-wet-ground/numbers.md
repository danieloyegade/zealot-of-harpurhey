# Stage 4 — environment map, puddle mask, light-streak reflections

Captured 2026-09-24, Chromium/SwiftShader (software rasteriser — no
meaningful fps here, same caveat as Stages 1-3), `?quality=high`, 1280x720.

- 4a: one-shot scene-captured environment map (PMREMGenerator.fromScene,
  no Blender/network dependency — see src/rendering/environment.ts for why),
  intensity 0.22.
- 4b: procedural puddle mask (scripts/generatePuddleMask.mjs), sampled by
  both road and pavement materials at 7 m world scale. Visible as darker,
  glossier patches on the ground in street-detail.png and
  public-light-pool.png.
- 4c: one InstancedMesh of puddle-masked light-streak reflections, one per
  streetlight plus Dreams' fascia tubes. public-light-pool.png shows a
  clear warm streak under MCR1's shop light.

Compare against `renders/realism-pass/03-textures-materials/` (Stage 3,
same dreams-target view) and the reference in `renders/visual-gap-2026-09-24/`.
