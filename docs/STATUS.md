# Status Log

This is the running stand-up for this repo. Claude and Codex each read the
top of this file before starting work, and append an entry before ending a
session. See `docs/AGENT_WORKFLOW.md` for the full protocol.

Newest entries go at the top. Do not edit or delete past entries — this is
an append-only log. When it gets long, older entries get archived (see
"Archiving" in AGENT_WORKFLOW.md), not deleted.

---

## 2026-09-12 — Claude — `claude/engineer-communication-workflow-uex7id`

**Status:** Done (review only — no gameplay code changed)

**Did:** Reviewed movement and camera mechanics for feel/playability
(`PlayerController`, `ThirdPersonCamera`, `InputController`,
`world/collision.ts`). Foundations are sound: fixed-step sim,
frame-rate-independent smoothing, correct diagonal normalisation,
`event.code` keying. Issues found, highest impact first:

1. Camera has no occlusion handling (`ThirdPersonCamera.ts:58`) — clips
   inside the perimeter buildings whenever the player faces a shopfront.
2. Camera orbit requires a held pointer drag; no pointer lock, and no
   keyboard turn at all, so mouseless players can never reorient.
3. No auto-follow — camera never settles behind the movement direction.
4. Look target is unsmoothed while camera position is smoothed
   (`ThirdPersonCamera.ts:69`), so framing swims under acceleration.
5. Movement acceleration is floaty (~125ms time constant,
   `PlayerController.ts:79`); no zero-snap on stop.
6. Walk-by-default over a 128x124m world means ~53s to cross; Space is
   bound to run, which should be freed.
7. Velocity isn't cancelled on collision (`PlayerController.ts:85`).
8. `moveCircleWithCollisions` has no depenetration — a player who ends up
   inside an obstacle can never escape.
   Plus smaller items: FOV 50 is narrow, pitch clamp 7-35deg is tight, no
   zoom, orbit sensitivity unnormalised for viewport, no gamepad/touch.

**State of the repo:** Working tree clean apart from this log entry. No
gameplay code touched — findings only. Nothing mid-refactor.

**Next up:** Awaiting Daniel's call on which fixes to take and in what
order. Recommended sequence: camera occlusion -> pointer lock + keyboard
turn -> auto-follow -> unified smoothed anchor -> movement tuning ->
collision depenetration -> polish. Unclaimed — if Codex picks this up,
say which items in your entry so we don't both touch
`ThirdPersonCamera.ts`.

**Blockers / questions for tech lead:** Two are design calls, not
engineering ones: (a) should running be the default with Shift to walk,
given world size? (b) is mobile/touch in scope? Right now touch devices
have no movement input whatsoever.

---

## 2026-09-11 — Claude — `claude/engineer-communication-workflow-uex7id`

**Status:** Done

**Did:** Set up the agent coordination workflow itself: this log
(`docs/STATUS.md`), the protocol doc (`docs/AGENT_WORKFLOW.md`), and
pointer files (`CLAUDE.md`, `AGENTS.md`) so both agents auto-load the
protocol at session start instead of relying on memory.

**State of the repo:** No other in-flight work found — `main` and this
branch are the only two branches, working tree was clean.

**Next up:** Nobody has a queued task. Codex: read `docs/AGENT_WORKFLOW.md`
once, then start logging entries here per the format.

**Blockers / questions for tech lead:** None.
