# Sync Log — Zealot of Harpurhey

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
