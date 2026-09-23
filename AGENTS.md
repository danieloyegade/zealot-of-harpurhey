# AGENTS.md — Zealot of Harpurhey

This project is developed across **two AI coding tools — Codex and Claude Code — alternating on whichever still has credits**, plus Daniel working directly. You (whichever tool you are) do not share memory with the other tool. The repo — commits, code, `docs/`, and `SYNC.md` — is the only channel between you.

## Every session, before doing anything else

1. Read `SYNC.md` at the repo root — the running handoff log between engineers.
2. Run `git log --oneline -20` and `git status`. `SYNC.md` records intent; git is ground truth. If git shows commits or a working tree that doesn't match the last log entry, treat it as undocumented work from the other tool — inspect before building on it or overwriting it.

## Before ending a session or handing off

Append an entry to `SYNC.md` using the template at the top of that file: what you did, what's uncommitted, anything flagged, and open questions for whoever picks up next.

## What this project is

Zealot of Harpurhey (canonical spelling — reconciled 2026-09-23 across the package name, Vite base path, and all filenames/docs; see `SYNC.md`. An earlier session had deliberately renamed everything to a fictional "Harperhey" spelling, distinct from the real Manchester district — Daniel later confirmed that was a typo/error, not an intentional distinction, and the correct real-world spelling should be used everywhere) is a browser-based Three.js exploration game and artwork, not just "a Manchester delivery game." It is simultaneously a delivery game, an explorable fictional-collage Manchester, autobiographical fiction, a philosophical/surreal social-realist piece, and an extension of Daniel's photography/filmmaking practice — especially his parent project **The Spectres Are All Around Us (TSAU)**, whose visual grammar (planimetric composition, streetlight pools in darkness, deadpan museum-style labelling of mundane objects, municipal architecture, surveillance aesthetics) should shape the game's look throughout, not appear as easter eggs.

Visual direction has moved **away from the Dreamcast/PS2-era retro look** referenced early in development, toward "uncanny realism suspended between the photographic and the obviously constructed" — `docs/ART_DIRECTION.md`'s original "Core principles" and "Rendering restraint" sections still describe the old Dreamcast-era target and are stale until someone reconciles them. Its later sections (fashion, photographic apparatus and tableaux, transport and movement, added 2026-09-14) are current.

Philosophical references (Barthes, Baudrillard, Rilke, Don Quixote, etc.) should manifest environmentally — an unstable sign, a ridiculous ritual played sincerely — never as exposition-heavy dialogue. Avoid generic gamification (XP, skill trees, quest arrows, minimaps, health bars) unless it concretely serves the work.

**Before generating any creative content** — environments, characters, quests, events, dialogue, object descriptions, UI copy, asset names, lighting setups — read `docs/creative-constitution.md` in full. It's the conceptual framework behind the paragraph above (Barthes, Baudrillard, Derrida, Benjamin, TSAU, the gig economy as digital feudalism, etc.), including what to avoid (generic liminal-space/backrooms clichés, lore dumps, philosophy-NPC dialogue, over-explaining).

## How to work on this codebase

- **Preserve-first:** inspect → understand → preserve → improve → extend. Find the existing system (asset manager, interaction registry, quest data) and extend it — never build a parallel duplicate. Refactor only for a concrete, stated benefit. This is a fast-evolving artist-led project; continuity matters more than architectural purity.
- **Asset-first:** never invent a major visual asset directly in engine code. Sequence is: real photo reference → approved visual mockup (silhouette/material/mood) → build in Blender (reusable Python script under `blender/scripts/`) → export GLB → integrate in Three.js → iterate lighting/scale only after geometry is approved. Blender owns modelling/UVs/materials; Three.js owns world/game logic.
- **Priority order when unstated:** preserve working game → visual identity → player movement/traversal → authored environment → delivery loop → interactions → important interiors → asset quality → cinematic/surreal events → expansion.
- Technical specifics (renderer config, quality profiles, world layout, performance policy, naming conventions) are documented in `docs/TECHNICAL.md`, `docs/WORLD.md`, `docs/WORLD_LAYOUT.md`, `docs/PERFORMANCE.md`, and `docs/ART_DIRECTION.md` (caveat above). Read the relevant one before touching that area — don't assume this file is a substitute for them.

## Current state (verify against git before trusting)

As of 2026-09-11: world/environment building is well ahead of gameplay. Hero location GLBs exist in varying completion states; player movement/camera/collision and the render/quality-profile system are implemented and stable. No gameplay systems exist yet — `src/{delivery,interaction,npc,photography,audio,vehicles}` are empty stubs. See `SYNC.md` for the latest.
