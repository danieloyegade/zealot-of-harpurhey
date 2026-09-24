# Stage 1 — after retro settings off

Captured 2026-09-24, Chromium/SwiftShader (software rasteriser — no meaningful
fps here, see caveat below), `?quality=high`, 1280×720.

| View | Draw calls (quality=medium, `H` overlay) |
| --- | ---: |
| dreams-target | 253 |

**Caveat:** this automation environment has no GPU, so all timing/fps numbers
from it are meaningless. Only draw-call count is renderer-agnostic and worth
recording. A real before/after fps comparison on Apple Silicon (the
documented target hardware) is still owed — see Stage 0.3/0.1 in
`docs/REALISM_PASS_PLAN.md`, and the Stage 1 entry's validation note.

Screenshots: `dreams-target.png`, `dreams-angle.png`, `park-to-dreams.png`,
compare against `renders/visual-gap-2026-09-24/01-current-dreams-target.png`
and `02-current-park-to-dreams.png` (the Stage 0 baseline, same views, same
capture method).
