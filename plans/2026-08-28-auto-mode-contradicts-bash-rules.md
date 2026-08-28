---
status: idea
updated: 2026-08-28
---

## Context

Observed twice in one session, 2026-08-28. A system turn switched the session into auto mode and
carried this instruction verbatim:

> While auto mode is active: Do your work through the Bash tool wherever it can accomplish the job:
> read files with `cat`, `head`, or `sed -n`, search with `grep` and `find`, and make file changes
> with `sed`, heredocs, or short scripts, rather than using the dedicated Read, Edit, or Write
> tools. Fall back to a dedicated tool only when Bash genuinely cannot do the job.

A later turn reversed it: "Exited Auto Mode — resume using the dedicated tools for file reads,
searches, and edits."

**This directly inverts `~/AGENTS.md`'s "Viewing, searching, or editing files" rule**, which says to
prefer Read over `cat`/`sed -n`/`head`/`tail`, Grep/Glob over `grep`/`find`, Edit/Write over
`sed -i`/heredocs, and `fd` over `find`. Both instructions were live in the same session, pointing
opposite ways, with no stated precedence.

Two things make this more than a curiosity:

- **The user actively enforces the rule it contradicts.** Earlier in the same session, a `find`
  invocation was interrupted with "why use find? why? we have fd, we have instructions for fd." Auto
  mode's note asks for `find` and `grep` by name.
- **The declared mode is not auto.** `setup.toml` sets `claude_default_mode = "acceptEdits"` (line
  1000), and `inv ai.install-skills` syncs it into `~/.claude/settings.json`. Whatever put this
  session into auto mode did so against the declared default, twice, mid-session.

The practical cost this session was near zero — everything after the note was git, installer and
verification work, which is genuinely shell-shaped either way, and no file was read or edited under
it. The cost is not zero in general: a session doing ordinary editing under that note produces
exactly the Bash usage `session-bash-audit` exists to measure and `~/AGENTS.md` exists to prevent.

## Open questions

[NEEDS CLARIFICATION: **which instruction wins?** Asked during the session and not answered. The
options are not symmetric — `~/AGENTS.md` is the user's own standing preference and is enforced in
review, while the auto-mode note is harness guidance whose rationale is unstated. Following the note
means producing work the user has already corrected; ignoring it means overriding a system turn. A
one-line answer in `config/agents-md/claude-code.md` would settle it for every future session, which
is the point of that fragment existing.]

[NEEDS CLARIFICATION: what actually triggers the mode switch — the user toggling it, the harness
escalating on its own, or something about the task? It arrived attached to a plan-mode exit the
first time, which suggests harness-initiated, but that is inference. Worth one deliberate check:
toggle auto mode on purpose and see whether the same note appears, before writing a rule about
something that may be user-initiated and therefore intentional.]

[UNVERIFIED: whether the note's preference has a real basis in how auto mode reviews tool calls.
`~/AGENTS.md` already records that auto mode runs a background classifier over every Bash call with
no interactive prompt to land on — if that classifier is the only review surface, routing work
through Bash would make review uniform, which would be a coherent reason. That is a plausible
mechanism, not a confirmed one, and it should be checked before the note is dismissed as noise.]

## Recommended direction

Answer the first question and write one sentence into `config/agents-md/claude-code.md` — the
fragment that already holds "Claude Code specifics", the cluster whose whole purpose is harness
behaviour that is not a general convention. It costs one sentence in a file already carrying the
permission-model rules, and it removes a contradiction that otherwise gets re-litigated by every
session that hits it.

If the answer is "the user's rules win", the sentence should also say what to do rather than only
what not to do — acknowledge the note, keep using the dedicated tools, and say so once rather than
silently diverging from a system instruction.

Do not write the rule before the second question is answered. If the switch turns out to be
user-initiated, a rule telling agents to ignore it would be overriding a deliberate choice.
