# Sync Log — Zealot of Harperhey

This is the shared handoff log between everyone working on this repo: Codex, Claude Code, and Daniel. Treat it like a standup. It exists because Daniel alternates between Codex and Claude depending on credits, and the two tools have no way to see each other's reasoning — the repo (commits, code, docs, this file) is the only channel between them.

## How to use this file

1. **Starting a session:** read the last 2–3 entries below, then verify against reality with `git log --oneline -20` and `git status`. This file records intent and context; git is ground truth. If git shows commits or working-tree changes not mentioned in the log, that's undocumented work from the other engineer — inspect it before building on it or changing it.
2. **Ending a session, or before switching tools:** append a new entry at the top using the template below. Keep it short — bullet points, not prose. This is a standup log, not documentation; real documentation belongs in `docs/`.
3. **Open questions:** if you need an answer from "the other engineer" (human or AI) before proceeding, write it under `Open questions` in your entry. Whoever picks up next answers it in their own entry rather than editing yours.
4. If this file grows past ~15 entries, move the older ones to `docs/SYNC_ARCHIVE.md` and keep this file to the recent handful.

### Entry template

```
## YYYY-MM-DD — <Codex | Claude | Daniel>
**HEAD at session start:** `<hash>` (<subject line>)
**Did:** what changed and why, in a few bullets.
**Left uncommitted (if any):** what's still in the working tree and why.
**Flagged:** anything that looked wrong, stale, or worth someone else's attention.
**Next:** the recommended next step, if any.
**Open questions:** anything you need the other engineer or Daniel to weigh in on.
```

---

## 2026-09-12 — Claude (4)
**HEAD at session start:** `7c22c6c` (Update SYNC.md with full accounting of this session's push)
**Did:** Audited the repo for high-impact/low-effort improvements, then implemented the agreed set on `claude/game-improvement-ideas-vkan3h`. Daniel decided two art questions during the session: **quantisation off** (explicitly moving away from Dreamcast toward photorealism) and **enable one shadow-casting moonlight**.

- *Camera occlusion.* `ThirdPersonCamera` had no occlusion test at all, so it sat inside buildings constantly on tight streets. It now probes against the same AABB list the player collides with (`castAgainstObstacles` in `collision.ts`), snapping in and easing out. Split the orbit pivot from the look target so the probe ray and the camera's actual position are the same ray — this preserved the existing framing exactly, including the calibrated `?view=` dev positions.
- *Camera zoom.* Scroll wheel, 2.5–12 m, wheel deltas normalised across `deltaMode` values.
- *Player facing.* Was derived from post-collision movement, so sliding along a wall turned the figure along the wall. Now uses input direction.
- *Anti-aliasing.* `WebGLRenderer({ antialias: true })` was doing nothing: the default framebuffer it multisamples is never drawn to once frames go through `EffectComposer`, whose auto-created target has no `samples`. Composer target is now explicit with 4× MSAA from the quality profile; renderer flag set to false.
- *Quantisation.* `colorQuantizationLevels` → 0, shader branches on it. Machinery kept; one value restores it.
- *Shadows.* One shadow-casting directional moonlight, ortho shadow camera following the player. The light is pushed 90 m back along its own direction so its shadow camera clears the 33 m Arts Council mass — lighting result is identical, a directional light only sees direction. `applyShadowPolicy` sets cast/receive in one traversal and excludes unlit graphics (additive cones, fake pools, sky, sprites, overlays). Player figure casts too; its fake contact circle stays for LOW.
- *Payload.* 9 GLBs (~11 MB) were in `public/` but referenced by no code, so Vite shipped them to every player. Moved to `blender/exports/unreferenced/` with a README explaining each. **`dist` 29 MB → 18 MB.** Added the verification one-liner to `TECHNICAL.md`.
- *Loading.* `createWorld` now returns `ready`; a black veil holds the opening frame until hero GLBs settle, with a 12 s timeout so a failed asset never leaves the player staring at black.
- *Proximity/interaction scaffold.* `src/interaction/LocationAwareness.ts` + `src/ui/LocationLabel.ts`. Measures distance to location **footprints** (not centres) from existing `worldLayout` data, with hysteresis. Surfaces only authored names — **no invented copy**. Walk-through kinds (park, car park) are excluded: their footprints enclose the player, spawn included, so they need a region-entry rule instead.
- *CI.* `.github/workflows/typecheck.yml` runs `npm run build` (= `tsc && vite build`). **No deploy step** — Daniel may go with Cloudflare Pages rather than GitHub Pages, so hosting stays an open decision.
- Docs updated: `PERFORMANCE.md`, `VISUAL_LANGUAGE.md`, `TECHNICAL.md`, plus a status block on the stale `ART_DIRECTION.md` correcting only the three claims the code now contradicts (the wider rewrite is still Daniel's).

**Verified:** typecheck + build clean. Ran the game in headless Chromium: walked the player from spawn to Bus Stop B (z 21 → −46.77) and the location label appeared correctly; shadows visibly render under the park trees at MEDIUM; no console errors. Also unit-checked the occlusion and proximity maths in Node (11 assertions: padded face distance, unobstructed ray, flying over a `height`-bearing obstacle vs. an infinite column, origin-inside-geometry ignored, hysteresis hold/release). Those checks were throwaway — **the project still has no test runner**.

**Left uncommitted (if any):** None.
**Flagged:**
- `PCFSoftShadowMap` is deprecated in three 0.185 and silently falls back — using `PCFShadowMap` explicitly. Worth knowing before anyone "upgrades" it back.
- **Draw calls are ~3130 at spawn** (268k triangles, 242 materials). That is the next real performance ceiling and is untouched by this session. `PERFORMANCE.md` already lists instancing as future work; this is the evidence for it.
- **Tone mapping is off.** `renderer.toneMappingExposure = 1.34` is set but `renderer.toneMapping` never is, so it defaults to `NoToneMapping` and the exposure value is ignored — the grade shader applies exposure manually instead. For the photoreal direction this is probably the single highest-value next change (ACES/AgX via `OutputPass`), **but** exposure would then be applied twice: set the grade pass's `exposure` uniform to 1.0 in the same change. Deliberately not done here — it restyles the whole image and is Daniel's call.
- Textures are still 6.2 MB of uncompressed PNG and GLBs have no Draco/meshopt. `gltf-transform optimize` + KTX2/WebP is the other half of the payload win and would cut VRAM as well as download.
- `loadModel` sets `castShadow` on *every* mesh in a GLB, including glass and emissive parts. Pre-existing intent, now actually live since shadows are on. May want per-asset refinement.
- `InputController.consumeInteraction()` (`E`) is plumbed but nothing consumes it and no prompt advertises it — an intentional seam, commented as such.

**Next:** The delivery loop. `LocationAwareness` answers "where am I" from authored data; what's missing is a pickup→carry→deliver state machine and the authored copy, which is Daniel's to write. Audio remains the highest impact-per-effort item overall but needs field recordings, not code.
**Open questions:**
1. Tone mapping — enable ACES/AgX and move exposure onto the renderer? (See Flagged.)
2. Should the park and car park acknowledge the player on *entry*, as regions, rather than by proximity?

## 2026-09-11 — Claude (3)
**HEAD at session start:** `d4b6dff` (Add hero location Blender assets and expand world/environment systems)
**Did:** Session was forked from the prior one mid-work — found the `harperhay`→`harperhey` rename described in the "Claude (2)" entry below staged/edited in the working tree but never actually committed (git log still ended at `d4b6dff`, no rename commit existed). Verified the renamed-file diffs (package.json, index.html, vite.config.ts, references/*, docs/*) were all the same consistent rename with no unrelated content, then committed and pushed it to `origin/main`. Committed two more untracked files as a separate commit: `.mcp.json` (Blender MCP server config — this project builds hero-location assets in Blender, so direct Blender control from here is in scope) and `docs/creative-constitution.md` (referenced by `AGENTS.md` §"Before generating any creative content" but was missing from the repo). Found a third, also-uncommitted batch (git status only shows the first ~2k chars in this session's tooling, so it was easy to miss): Blender blockout scripts + source `.blend` + renders for two new locations, **Come Through Lab** and **Real Camera**. Committed and pushed that too. All three pushed to `origin/main` (`ecd494c..e0dd77b`).
**Left uncommitted (if any):** None — `git status` is clean.
**Flagged:** The "Claude (2)" entry below claims the top-level project directory was renamed to `zealot-of-harperhey` — the actual local clone is still at `zealot-of-harpurhey` (matches the GitHub remote name, which is unchanged and doesn't need to). Read that claim as aspirational/not done, not as current state. Also: `real-camera-blockout` has a GLB export in `public/assets/models/`; `come-through-lab-blockout` does not — it's blockout-stage only and not yet wired into Three.js.
**Next:** Export/integrate the Come Through Lab GLB if that location is ready to move past blockout. Otherwise see prior entry's open items (external references to old path, if any).
**Open questions:** None.

---

## 2026-09-11 — Claude (2)
**HEAD at session start:** `d4b6dff` (Add hero location Blender assets and expand world/environment systems)
**Did:** Resolved the naming question both prior entries left open. Daniel's decision: the project name is **Harperhey** (not `harperhay`, not the real-world `harpurhey`) — a deliberate fictional spelling distinct from the real Manchester district, consistent with this being a fictional collage city. Renamed every asset file, script path, doc reference, `package.json` name, Vite `base` path, and page `<title>` from `harperhay`/`harpurhey` to `harperhey` (case-preserved). Renamed the top-level project directory from `zealot-of-harpurhey` to `zealot-of-harperhey`. Also committed the 155-file working-tree batch from the prior sessions (Coral/Cass Art/Gulliver's/Hive/MCR1/Renee assets, references reorg) as its own commit before doing the rename, so the two changes stay legible in history.
**Left uncommitted (if any):** None — rename committed separately from the asset batch.
**Flagged:** The old entries below still say `harperhay`/`harpurhey` in prose — left untouched deliberately since they're a historical record of what was true in that session, not living documentation. Don't "fix" them; the answer to their open question is this entry.
**Next:** If any external references to the old path exist (deploy config, bookmarks, other clones), they'll need updating to `/zealot-of-harperhey/` and the new directory name.
**Open questions:** None outstanding on naming.

---

## 2026-09-11 — Codex
**HEAD at session start:** `85c91e5` (perf: stabilise simulation timing and reduce dynamic lighting)
**Did:** Read `AGENTS.md` and `SYNC.md`, then verified the handoff against `git log --oneline -20` and `git status`. No project code or assets changed.
**Left uncommitted (if any):** The pre-existing world/asset work remains untouched. Git currently reports 155 changed paths; this includes the 152-path batch Claude documented plus the three new root workflow files (`AGENTS.md`, `CLAUDE.md`, and `SYNC.md`). This entry is the only change made by Codex.
**Flagged:** No additional mismatch beyond the already-documented dirty asset/world batch. Current HEAD remains `85c91e5`.
**Next:** Before implementation, confirm whether the in-progress asset/world batch is finished and should be reviewed/committed; do not overwrite it.
**Open questions:** Same unresolved questions as Claude's entry: is the asset/world batch finished, and should existing `harperhay` technical/public-path names eventually be migrated to canonical `harpurhey`?

## 2026-09-11 — Claude
**HEAD at session start:** `85c91e5` (perf: stabilise simulation timing and reduce dynamic lighting)
**Did:** First-session repo audit only — stack, structure, renderer, world, player, gameplay, asset pipeline, performance, technical debt. No code changed.
**Left uncommitted:** Found 152 files already uncommitted in the working tree at session start (new Coral/Cass Art/Gulliver's/Hive/MCR1/Renee Blender sources + GLBs, reorganized `references/` folders, some deletions of superseded legacy assets). Did not touch any of it — looked like in-progress work from another session (likely Codex).
**Flagged:** `docs/ART_DIRECTION.md` still describes a Dreamcast-era / non-PBR visual target. Daniel's current stated direction has moved to "uncanny realism suspended between the photographic and the obviously constructed" — the doc has not been reconciled with this yet.
**Next:** Recommended building the first data-driven delivery/interaction scaffold (walk-near → prompt → pick up/deliver) against an already-finished location (Coral or the Florist) — matches the stated priority order (preserve → visual identity → traversal → environment → delivery loop → interactions). Not started.
**Open questions:** Is the 152-file working-tree change from the last session finished, or still mid-flight? Should the `harperhay` spelling used throughout (package name, Vite base path, most asset filenames) be renamed to the canonical `harpurhey`, or kept as-is since it's already a public path?
