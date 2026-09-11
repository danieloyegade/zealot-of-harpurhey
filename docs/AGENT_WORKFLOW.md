# Agent Workflow: Claude + Codex + Tech Lead

Two AI engineers (Claude, Codex) work on this repo alongside one human tech
lead (Daniel). Neither agent can see the other's chat history or working
memory — the only shared state between sessions is what's committed to this
repo. This doc is the protocol; `docs/STATUS.md` is the artifact it produces.

## The problem this solves

Without a shared log, two agents working the same repo on different
branches/sessions will:
- duplicate work neither knew the other started
- collide on the same files with no idea a conflict is coming
- leave the tech lead needing to ask "what's the state of things?" instead
  of just reading it
- lose context between sessions (an agent's own memory doesn't persist;
  a repo file does)

A stand-up works because it's frequent, short, and answers three
questions: what did you do, what's next, what's blocking you. That's the
model here — just asynchronous, since the two agents don't run
simultaneously in the same room.

## The two files

- **`docs/STATUS.md`** — the log itself. Append-only, newest entry on top,
  one entry per work session. This is the actual hand-off: reading it
  tells you what the other agent just did and what they expect to happen
  next.
- **`CLAUDE.md`** / **`AGENTS.md`** — one-line pointers at repo root, the
  files Claude Code and Codex respectively auto-load at session start.
  Their only job is to force this protocol into view before either agent
  does anything else. Keep them thin; the protocol itself lives here so
  there's one source of truth, not two copies to keep in sync.

## Session protocol

**At the start of every session:**
1. Read the most recent entries in `docs/STATUS.md` (at minimum, the top
   entry; more if it references branches/files you're about to touch).
2. Check `git branch -a` / `git status` against what STATUS.md claims —
   if they disagree (e.g. a branch STATUS.md calls "in progress" is
   missing, or has commits STATUS.md doesn't mention), trust the repo
   state and flag the discrepancy in your own entry rather than silently
   overwriting it.
3. If the top entry's "Next up" names you or a task you're about to
   duplicate, do that task (or explicitly say in your entry why you're
   doing something else instead).

**At the end of every session** (or before a long pause in a long one),
append an entry to `docs/STATUS.md` using the template below. "End of
session" means: you're about to stop responding, hand off, or you've hit a
stopping point significant enough that the other agent or the tech lead
would want to know about it before touching related code.

## Entry template

```markdown
## YYYY-MM-DD — <Claude|Codex> — `<branch-name>`

**Status:** In progress | Blocked | Done

**Did:** 1-3 sentences, concrete. Not "worked on physics" — "fixed the
player capsule tunneling through the bus shelter collider at high speed."

**State of the repo:** Anything the other agent needs to know before
touching related files — branches open, PRs open, files mid-refactor,
tests currently red, generated assets not yet committed.

**Next up:** What should happen next, and who you expect to do it (you,
the other agent, or the tech lead). If nobody's claimed it, say so
explicitly rather than leaving it implicit.

**Blockers / questions for tech lead:** Anything that needs Daniel's
decision before work can continue. Omit the section or write "None" if
there isn't one — don't leave it blank/ambiguous.
```

Keep entries short. This is a stand-up, not a design doc — link to a PR,
commit, or a doc under `docs/` for anything that needs depth.

## Avoiding collisions

- Before starting work that touches files another open branch also
  touches, say so in your entry ("touching `src/world/*`, same area as
  Codex's open branch X") rather than discovering the conflict at merge
  time.
- If you find the other agent mid-way through something (an open branch,
  an uncommitted stash, a STATUS.md entry marked "In progress" with no
  matching "Done" yet), don't restart or override it. Either continue it
  (say so in your entry) or work elsewhere and note why you left it.
- If you and the other agent's work collides anyway (same file, competing
  approaches), don't silently pick a winner — surface it as a blocker for
  the tech lead in your STATUS.md entry.

## Escalating to the tech lead vs. to the other agent

- Talk to the other agent (via STATUS.md) for: what's been done, what's
  next, what state the repo is in, non-blocking heads-up about shared
  files.
- Escalate to the tech lead for: architectural decisions, anything where
  the two agents would pick different approaches and need a tiebreaker,
  scope changes, or anything blocking that isn't resolvable by reading the
  log.

## Archiving

When `docs/STATUS.md` gets long (rule of thumb: past ~15-20 entries or
hard to scan), move everything except the most recent 5-10 entries into
`docs/STATUS_ARCHIVE.md` (create it if it doesn't exist, newest-on-top,
same order). Do this as its own small commit, not mixed into a feature
change, and say you did it in your next STATUS.md entry.
