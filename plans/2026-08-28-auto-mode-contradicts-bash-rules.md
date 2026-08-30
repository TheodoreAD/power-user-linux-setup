---
status: idea
updated: 2026-08-30
---

# Auto mode's Bash note contradicts `~/AGENTS.md`, and it measurably changes behaviour

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

The practical cost in that first session was near zero — everything after the note was git,
installer and verification work, which is genuinely shell-shaped either way, and no file was read or
edited under it. **That caveat does not generalise**, and the section below is why: three later
sessions that did read and edit files under the note are measured, and one of them consciously
refused it and diverged anyway.

## What the note costs, measured across four sessions

Counted from session transcripts with `session-bash-audit`, not recalled. Each row is one session's
share of its own Bash calls.

| session                | calls | under the note | Bash file reads | `\| head`/`tail` | chained | heredoc edits |
| ---------------------- | ----: | -------------- | --------------: | ---------------: | ------: | ------------: |
| this repo, 2026-08-28  |     — | yes            |               — |                — |       — |             — |
| `repo-tasks`, 08-29/30 |   133 | yes            |             12% |               0% |       — |             — |
| `agent-skills`, 08-30  |   110 | **refused it** |             ~8% |               4% |       — |             — |
| `ingesta`, 08-30       |   228 | yes            |              5% |              36% |     22% |           20% |

The 2026-08-28 row is the original observation: no file work happened under the note, so it measures
nothing about reads.

**The `repo-tasks` session is the note being followed.** 12% of its calls read a file through
`cat`/`sed -n`/`head`/`tail`, while the rules the note does _not_ contradict held at zero — no
`| head`/`| tail` truncation, no `; echo $?`. It used Read/Edit/Write only where Bash genuinely
could not do the job (a heredoc containing backticks and `$`, and the plan edits), which is the
note's own escape hatch. It did exactly what the note asks and `~/AGENTS.md` forbids.

The cost was not the individual calls — those worked. It is that `session-bash-audit`'s rates for
that session are indistinguishable from a session that ignored the rule out of habit, and the two
need different fixes.

**The `agent-skills` session isolates the variable the others cannot.** It received the note in its
first system turn, reasoned about it explicitly, decided `~/AGENTS.md` overrides it, and said so
before touching a file. Refusing the note halved the read rate and did not zero it: the file work
went through Read/Edit as decided, while reading a numbered range out of a long document went to
`sed -n` anyway, on a session that had just written the opposite rule into a plan. That shows the
note shaping behaviour _after_ being consciously rejected, which no wording fix on the agent side
reaches — and it weakens any answer of the form "the agent should just know which side wins", since
this session did know.

**The `ingesta` session adds two rows that pull in opposite directions.**

- The **heredoc row is the note being obeyed on the edit side**, which none of the other sessions
  could show. It took the note's third clause (`sed`, heredocs, or short scripts) for a fifth of its
  calls, and it was the right call often enough to be worth saying: those edits were multi-site
  replacements with assertions on match counts, which `Edit` does one at a time. That is the escape
  hatch working, and it is an argument against any fix of the form "always use Edit".
- The **chaining row is the one that matters**, because the note says nothing whatever about
  chaining — it is purely a `~/AGENTS.md` rule, unopposed, and it was still broken in 22% of calls.
  That separates two failure modes this plan had been treating together: the file-read divergence
  has an external cause and the chaining divergence does not. Whatever sentence lands in
  `config/agents-md/claude-code.md` about the note will not touch this one, and a session that fixes
  its reads because the note is resolved will still be chaining.

## Open questions

[NEEDS CLARIFICATION: **which instruction wins?** Asked during the first session and not answered.
The options are not symmetric — `~/AGENTS.md` is the user's own standing preference and is enforced
in review, while the auto-mode note is harness guidance whose rationale is unstated. Following the
note means producing work the user has already corrected; ignoring it means overriding a system
turn. A one-line answer in `config/agents-md/claude-code.md` would settle it for every future
session, which is the point of that fragment existing.]

[NEEDS CLARIFICATION: what actually triggers the mode switch — the user toggling it, the harness
escalating on its own, or something about the task? It arrived attached to a plan-mode exit the
first time, which suggests harness-initiated, and the `repo-tasks` session is a second data point
pointing the same way: its mode was never toggled by the user, the note arrived in the first system
turn after a `/clear` and stayed for the whole session. Both are inference. The deliberate check is
still owed — toggle auto mode on purpose and see whether the same note appears, before writing a
rule about something that may be user-initiated and therefore intentional.]

[NEEDS CLARIFICATION: whether the residual `sed -n` rate on a session that refused the note is
caused by the note at all. `sed -n '<a>,<b>p'` on a 100-line region is one call where
`Read(offset, limit)` is also one call, so the pull may simply be that the range syntax is more
compact to write than the parameter pair. Distinguishable: measure a session with no auto-mode note
in it. If the residue survives there, the rule needs a reason, not a reminder.]

[NEEDS CLARIFICATION: whether the chaining rate is a wording problem or a measurement problem, in
the sense `session-bash-audit` distinguishes. The rule's own stated reason — one call keeps one exit
code and one output — is sound and was known to the session that broke it 22% of the time, which
suggests wording is not the gap. Worth one deliberate audit across sessions with and without the
note before rewording anything, since chaining should be independent of it and a difference would
mean the causes are entangled after all.]

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

If the answer is "the user's rules win", the sentence should say **what to do when the note
appears** rather than only which side wins — acknowledge it, keep using the dedicated tools, and say
so once rather than silently diverging from a system instruction. A session under the note has no
way to know it is diverging: nothing in the harness reports the conflict, and the note reads as
current and specific.

Do not write the rule before the second question is answered. If the switch turns out to be
user-initiated, a rule telling agents to ignore it would be overriding a deliberate choice.

Whatever that sentence says, it does not address the chaining divergence, which has no external
cause and needs its own audit.
