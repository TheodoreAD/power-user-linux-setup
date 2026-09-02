---
status: idea
updated: 2026-09-01
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
edited under it. **That caveat does not generalise**, and the section below is why: four later
sessions that did read and edit files under the note are measured, one of them consciously refused
it and diverged anyway, and one announced the resolution out loud and produced the worst rates in
the table.

## What the note costs, measured across five sessions

Counted from session transcripts with `session-bash-audit`, not recalled. Each row is one session's
share of its own Bash calls.

| session                | calls | under the note | Bash file reads | `\| head`/`tail` | chained | heredoc edits |
| ---------------------- | ----: | -------------- | --------------: | ---------------: | ------: | ------------: |
| this repo, 2026-08-28  |     — | yes            |               — |                — |       — |             — |
| `repo-tasks`, 08-29/30 |   133 | yes            |             12% |               0% |       — |             — |
| `agent-skills`, 08-30  |   110 | **refused it** |             ~8% |               4% |       — |             — |
| `ingesta`, 08-30       |   228 | yes            |              5% |              36% |     22% |           20% |
| `ingesta`, 08-31/09-01 |   306 | **announced**  |         **18%** |          **46%** | **57%** |       **30%** |

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
  has an external cause and the chaining divergence does not. Whatever sentence lands in `bash.md`
  about the note will not touch this one, and a session that fixes its reads because the note is
  resolved will still be chaining.

**The second `ingesta` row is why the "under the note" column needs a third value.** Merged in from
`plans/2026-09-01-bash-discipline-sample-ingesta-0901.md`, filed by that session because it could
not edit this repo. It did not passively sit under the note like the `repo-tasks` row, and it did
not reason its way to a refusal like the `agent-skills` row — it **stated the resolution of this
plan's central question in its own words, in its second message**:

> "Using Read/Edit/Write rather than Bash for files, per `~/AGENTS.md`; searching with `rg`."

It then produced the worst numbers in the table. Measured with `session-bash-audit`, not recalled:

```
this session  n=306  chain=57%  chain5=5%  head/tail=46%  exit-masked=28%
              redirect-then-filter=0%  sed-n=18%  cat-view=0%  heredoc=30%
              cd-own-repo=0%  git-C-own-repo=0%  git-mutating-in-chain=9%

vs 2026-08-24-auto-mode.json: 7/11 expectations met
head/tail 46%(+15pp,MISS)  sed-n 18%(+10pp,MISS)  heredoc 30%(+14pp,MISS)
git-mutating-in-chain 9%(+1pp,MISS)  chain 57%(-9pp,OK)
```

Transcript:
`~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-ingesta/f489b075-6f46-4814-a71b-57f5879ef27e.jsonl`,
session start `2026-08-31T18:41:11.778Z`, ~7 hours.

Two things sharpen it. The regression is **specific rather than general** — `cd-own-repo`,
`git-C-own-repo`, `cat-view` and `redirect-then-filter` were all 0%, so it is the output-filtering
and file-reading habits that moved, not the whole Bash cluster. And the same seven hours were spent
writing verification-discipline rationale into that repo's `contributing/` docs, including a pitfall
about a green check that was evidence for the wrong thing: the rule-authoring and the rule-breaking
are the same session.

That makes it the second recorded instance of the shape, after the session that authored the
`head`/`tail` rule and then produced it in a third of its calls.
`plans/2026-08-23-global-agents-md-adherence-watch.md`'s session 10 records a third from this repo
and cites this one — so the count across both plans is three.

## The note removes tools, and that settles half the question (2026-08-30)

A fifth session, in this repo, under the note from its first system turn. It read the note, decided
`~/AGENTS.md` wins, said so, and then hit the thing four sessions of counting had missed:

```
Error: No such tool available: Grep. Grep is not available in this session —
search file contents with `grep` via the Bash tool instead.
```

**Auto mode is not only advisory. It withdraws the dedicated search tools.** Measured over the
session's own transcript: 164 Bash calls, 17 `Read`, 35 `Edit`, 2 `Write` — so Read/Edit/Write
stayed available throughout and were used — against exactly one `Grep` call, which errored as above.
(`Glob` was never called, so it is unmeasured rather than confirmed present or absent.)

That splits this plan's central question into two halves with different answers, which is why four
sessions of rate-counting could not settle it:

- **Searching: there is no conflict, because there is no choice.** `~/AGENTS.md`'s "Grep/Glob over
  `grep`/`find`" is unfollowable while the note is active. A session obeying it is not diverging
  from the user's rule by preference; the rule has no referent. Every `grep`/`rg` call such a
  session makes is forced, and counting them as adherence failures — which the four-session table
  above implicitly does — measures the harness rather than the agent.
- **Reading and editing: the conflict is real and the user's rule can win.** Read, Edit and Write
  are all still there. This is the half a rule in `config/agents-md/bash.md` can actually direct,
  and it is where the earlier sessions' 5–12% Bash-read rates are genuine choices.

[PITFALL: the note's own wording hides this. It says to fall back to a dedicated tool "only when
Bash genuinely cannot do the job", which reads as a preference among available tools — so an agent
budgets its choices rather than discovering that one of them is gone. The removal surfaces only on
the call that fails, and only for a tool the session happens to reach for.]

## Open questions

[NEEDS CLARIFICATION: **which instruction wins, for reads and edits?** Narrowed 2026-08-30 — the
search half is answered by the tool removal above, and only this half is still a question. Asked
during the first session and not answered. The options are not symmetric — `~/AGENTS.md` is the
user's own standing preference and is enforced in review, while the auto-mode note is harness
guidance whose rationale is unstated. Following the note means producing work the user has already
corrected; ignoring it means overriding a system turn. A one-line answer in
`config/agents-md/bash.md` would settle it for every future session, next to the permission-model
rule that already describes auto mode.]

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
in it. If the residue survives there, the rule needs a reason, not a reminder. Sharpened 2026-09-01
by the second `ingesta` row: 18% is the highest `sed -n` rate recorded here, +10pp over the
auto-mode baseline, on a session that had **said** it was using `Read`. So the residue survives an
explicit statement of the rule, which rules out "the session did not know" and leaves the
compactness hypothesis standing.]

[NEEDS CLARIFICATION: **is "the session said the right thing first" a variable worth its own column,
or noise?** Three occurrences now (the two named above plus the watch's session 10), and in all
three the announcing session scored at or below the baseline it was overriding. If it is real, it is
the most actionable finding either plan has: it would mean the announcement is a substitute for the
behaviour rather than a precursor to it, and every fix of the form "make the agent state which rule
wins" — including this plan's own recommended direction — is aimed at the wrong thing. Distinguish
it by measuring announcing and non-announcing sessions separately; `session-bash-audit` can detect
the announcement, since all three used a recognisable phrase in the first two messages.]

[NEEDS CLARIFICATION: **is `heredoc edits` at 30% the same failure as the others, or the rule being
wrong about a case it never considered?** The heredocs in that session were `python3 - <<'PY'`
blocks doing multi-site string replacement across a file — work `Edit` genuinely cannot do in one
call, and the same cause the watch's session 10 records for its own 26% (renaming a helper across
three modules, one line into fifteen task functions). Two sessions, same explanation, and the note's
own escape hatch ("only when Bash genuinely cannot do the job") arguably covers it. If it is a real
gap the rule needs a stated exception for mechanical multi-site rewrites and the metric needs to
stop counting them as misses; if it is not, both sessions are simply reaching for the cheaper call.
The split is measurable — a heredoc writing one file whole is not the same call as one rewriting a
pattern across several — and neither the audit script nor either plan separates them yet.]

[NEEDS CLARIFICATION: whether the chaining rate is a wording problem or a measurement problem, in
the sense `session-bash-audit` distinguishes. The rule's own stated reason — one call keeps one exit
code and one output — is sound and was known to the session that broke it 22% of the time, which
suggests wording is not the gap. Worth one deliberate audit across sessions with and without the
note before rewording anything, since chaining should be independent of it and a difference would
mean the causes are entangled after all. Sharpened 2026-08-30 by the fifth session: it chained in
**40%** of 162 calls — the same rate as session 5 and nearly three times session 6's 14% — while its
`head`/`tail` rate sat at 20%, at the good end of the range. So the two metrics moved independently
in one session, which is the strongest evidence yet that they are separate problems with separate
causes, and that fixing the note will not touch chaining.]

[UNVERIFIED: whether the note's preference has a real basis in how auto mode reviews tool calls.
`~/AGENTS.md` already records that auto mode runs a background classifier over every Bash call with
no interactive prompt to land on — if that classifier is the only review surface, routing work
through Bash would make review uniform, which would be a coherent reason. That is a plausible
mechanism, not a confirmed one, and it should be checked before the note is dismissed as noise.]

## Recommended direction

Answer the first question and write one sentence into `config/agents-md/bash.md`, next to "The
permission model in force" — which already describes what auto mode does to the toolset and carries
the `[Claude Code]` label this claim needs. (Written before the 2026-08-30 re-cut, this plan named
`claude-code.md`, the harness fragment; fragments are keyed to subject now and that file is gone, so
the destination is the Bash cluster rather than a harness one.) It costs one sentence in a rule
already carrying the permission model, and it removes a contradiction that otherwise gets
re-litigated by every session that hits it.

If the answer is "the user's rules win", the sentence should say **what to do when the note
appears** rather than only which side wins — acknowledge it, keep using the dedicated tools, and say
so once rather than silently diverging from a system instruction. A session under the note has no
way to know it is diverging: nothing in the harness reports the conflict, and the note reads as
current and specific.

[PITFALL: **that clause has since landed in `~/AGENTS.md`, and the three sessions that obeyed it
scored worse than the ones that did not.** "Say so once" was written to stop silent divergence, and
it does — the transcripts now read as compliant — but the second `ingesta` row, the `agent-skills`
refusal and the watch's session 10 all made the statement and then diverged anyway, at 46%, 4% and
40% `head`/`tail` respectively, two of them above the baseline they were overriding. The
announcement is verifiable and the behaviour is not, so the clause improved the thing that is easy
to check. Do not treat it as the fix; it is at best half of one. See the announcement question above
before writing any more of this shape.]

**And it has to cover the case where the tool is simply gone**, which the 2026-08-30 finding above
makes the more common one. "Keep using the dedicated tools" is not executable advice for search
under auto mode: `Grep` returns `No such tool available`. The sentence should say that reaching for
`Grep` and finding it absent is expected rather than a misconfiguration, that `rg` is then the
correct tool and `~/AGENTS.md`'s `rg`-over-`grep`/`fd`-over-`find` preferences still apply to how it
is called, and that Read/Edit/Write remain available and should still be preferred. Written the
other way round — as "the user's rules win" alone — it directs a session to keep trying a tool that
is not there.

Do not write the rule before the second question is answered. If the switch turns out to be
user-initiated, a rule telling agents to ignore it would be overriding a deliberate choice.

Whatever that sentence says, it does not address the chaining divergence, which has no external
cause and needs its own audit.
