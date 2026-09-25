# Stage 5b — baked lighting wired into the runtime

Captured 2026-09-25, Chromium/SwiftShader (software rasteriser — no
meaningful fps here, same caveat as every prior stage), `?quality=high`,
1280x720.

`dreams-target-lightmaps-on.png` vs `dreams-target-lightmaps-off.png`
(`?lightmaps=off`) is the direct A/B pair: with lightmaps on, the gable and
fascia show a softer, hazier gradient of light down the panel; off, they're
flatter/more evenly lit by the real-time "Dreams hero light" alone.

`park-to-dreams-lightmaps-on.png` shows the ground patch: a warm pink/rose
wash across the pavement, matching the Blender-side reference render
(`renders/realism-pass/05-baked-lighting/dreams-lightmap-ground.png` —
cool blue-white under the tubes, warming to pink/amber at the edges).
Debugged during this session: an initial version showed this as a flat,
garish, oversaturated block rather than a soft gradient — root cause was
`toneMapped: false` on the ground-patch material (copied from this world's
other, LDR-authored additive glow materials; wrong for genuine HDR bake
radiance, which needs the scene's normal AgX curve to compress the same way
everything else does). Confirmed fixed by comparing a debug-tinted render of
the patch alone against the Blender-side reference render before and after.

Compare `dreams-target-lightmaps-on.png` against
`renders/realism-pass/03-textures-materials/dreams-target.png` (Stage 3,
same view, pre-lightmap) and the reference in `renders/visual-gap-2026-09-24/`.
