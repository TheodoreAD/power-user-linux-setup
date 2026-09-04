---
status: idea
updated: 2026-09-04
source_repo: github.com-personal/ingesta
source_session: c83364a4-8f1d-42f2-bb27-aba9b6feb970.jsonl
source_moment: 2026-09-04T11:20:43Z
---

# Adherence sample: a record view and a tail-ed gate

## Context

**A fourth `ingesta` row for [the sample corpus](2026-09-02-agents-md-adherence-sample-corpus.md),
not a plan of its own.** It is filed rather than appended because the corpus lives in this repo and
a session in another one may not write here; absorb it into that plan's tables and delete this file.

What makes it worth adding to a corpus that already has three rows from this repo: it is the first
one where the masked calls were checked all the way through to the claims they produced, and the
answer was that every claim held. The corpus so far can say how often exits are thrown away; it
cannot yet say how often that turns into a false statement, and one clean case is the beginning of
that column.

## Evidence

Transcript:
`~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-ingesta/c83364a4-8f1d-42f2-bb27-aba9b6feb970.jsonl`,
session opened 2026-09-04T11:20:43Z with _"Start from plans/2026-09-04-the-shape-of-the-interface.md
— its step 1, the usability run, is the only thing left blocking"_.

Measured at the harvest boundary `2026-09-04T15:07:41+03:00`, so the figures are the session's own
work and exclude the sweep:

| calls | shape                               | chain | head/tail | exit-masked | git -C own repo | cd own repo |
| ----- | ----------------------------------- | ----- | --------- | ----------- | --------------- | ----------- |
| 78    | code + plans + commits, three hours | 40%   | 35%       | 18%         | 0%              | 0%          |

Three things the row does not carry and that the corpus may want:

- **Every masked call that mattered was the same command.** Seven of the fourteen were
  `inv quality.precommit 2>&1 | tail -N`, run once per commit-worthy checkpoint. The remaining seven
  were `inv dev.seed`, `pytest` on one file, and two listings. The shape is not spread across the
  session's work; it is one habit applied to one command.
- **The three green claims all held.** `claims` counted three messages telling the user the gate was
  green — after 927, 947 and 958 tests — every one of them from a `| tail`-ed run. The unpiped
  re-run at harvest exits 0 with 958 passed, 1 skipped, so nothing said to the user was false. That
  is the outcome that makes the rule easy to dismiss, which is exactly why it is worth recording
  next to sample 2, where 28% masking sat beside a gate that was genuinely red.
- **The session held the rule in context the whole time.** `~/AGENTS.md`'s "Reading a command's
  result" and "Composing a Bash call" were loaded from the first turn, and the same session wrote
  five commits arguing carefully about honest bounds in a medical record. Knowing the rule and
  applying it to a command's output are evidently different things.

One separate slip from the same session, and it is the one the file names outright: a search was run
as `rg -rn "half-open" .` — `rg`'s `-r` is `--replace`, so the output printed the matched text
**rewritten**, showing lines like `Stretches are n, ...` where the file says `half-open`. Caught
because the mangled output was obviously wrong; the failure mode the rule warns about is the one
where it is not. Carried from `grep -r` habit inside a session that had already typed `rg` correctly
a dozen times.

## Open questions

[NEEDS CLARIFICATION: **Whether the corpus wants a "claims held / claims false" column.** This is
the first sample where the chain from a masked exit to a sentence the user read was followed to the
end, and one clean case is not a rate. If a second and third sample also come back clean, the honest
finding may be that the masking is a real hazard with a low realised cost — which is a different
argument for the rule than the one currently made, and worth knowing before the rule is reworded.]

## Recommended direction

Absorb into the corpus plan as sample 8, delete this file, and decide the column question there
rather than here.
