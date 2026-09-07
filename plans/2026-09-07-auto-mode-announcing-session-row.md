---
status: idea
updated: 2026-09-07
source_repo: github.com-personal/invoke-stubs
source_session: 6450239e-aad5-4861-acda-7eb9e97c15c6.jsonl
source_moment: 2026-09-06T08:49:31Z
---

# One announcing auto-mode session, with the first non-zero `cd-own-repo` in the corpus

## Context

A row for `plans/2026-08-28-auto-mode-contradicts-bash-rules.md`, not a new topic — file it there
rather than keeping it as a separate plan. It is an **announcing** session under the auto-mode note,
which that plan's open question about measuring announcing and non-announcing sessions separately
asks for directly.

The session was 26 hours of stub work in `invoke-stubs` on `claude-opus-5`. It took the note's
instruction, declined the file-tool half out loud once, and did not repeat it:

> Auto mode note asks for Bash-only file work; per `~/AGENTS.md` I'll keep Read/Edit/Write for files
> and use `rg` for search. Saying it once, not repeating.

## Evidence

`session-bash-audit`, `--until` the harvest boundary so the sweep's own 11 calls are excluded, and
`--compare` against `2026-09-06-zero-on-count.json`:

```
this session  n=306  chain=44%  chain5=6%  head/tail=27%  exit-masked=23% (49 gate, 20 listing)
              sed-n=2%(7)  cat-view=1%(2)  heredoc=5%  cd-own-repo=4%(11)
              git-C-own-repo=0%  git-mutating-in-chain=5%(16)  search|head=5%(15)
              echo-exit=1  rg-replace=1  rg-replace-bundle=1
10/13 expectations met; misses were echo-exit, cd-own-repo, rg-replace-bundle
```

**The row is the whole session, and a mid-session measurement of the same session was materially
different** — which is a finding about sampling rather than about this session. At n=211, two hours
before the end, it read `chain=36% head/tail=20% exit-masked=20% sed-n=0%(1)`. The last third —
converting a bespoke script to the family's pytest-and-tasks layout, so mostly reading sibling
repos' configs — moved every one of those the wrong way, `sed -n` worst at 1 call to 7. Any harvest
that reports adherence before the session ends is reporting a prefix, and a prefix of a session
whose phases differ is not a smaller version of the whole.

Four things in that row are worth the filing; the rest is another sample.

- **The file-read rows are near-zero — `sed -n` 1 call, `cat`-view 2 — which is the announcing
  behaviour working.** That plan's 2026-08-30 section concluded the note _removes_ `Grep`, so a
  session's Bash reads are partly forced rather than chosen. This row is the other half: refusing
  the note's file-tool half is cheap and holds for a whole long session, without re-announcing.
- **`cd-own-repo` = 11 is the first non-zero in that plan's table**, where the row at its line 105
  records 0%. It is not the flat violation it looks like, and that is the interesting part: cwd was
  reset out from under the session repeatedly by work in throwaway probe directories — the harness
  reported "Primary working directory ... (was ...)" seven times — and `~/AGENTS.md`'s own
  cross-repo clause _prescribes_ `cd <session repo> && …` as the next call after that. So most of
  the 11 are the rule being followed, and the audit cannot tell those from the banned habit. [NEEDS
  CLARIFICATION: should `cd-own-repo` discount a `cd` that follows a cwd change, or is the right fix
  a separate row? As counted today the number is unreadable for any session that works in a
  scratchpad, which is every session that builds a throwaway venv.]
- **`chain` at 44% is mid-corpus** (57% and 22% are the neighbours), and the plan's own point stands
  — the note says nothing about chaining, so this is an unopposed `~/AGENTS.md` rule broken in
  nearly half of all calls by a session that was otherwise following the file-tool rule
  deliberately.
- **`sed -n` at 7 calls is the row that contradicts this session's own headline**, and it is the
  reason the two-phase split above matters. The announcing behaviour held for editing all session —
  `cat`-view stayed at 2 — but every one of those seven `sed -n` calls is a _read_ of a sibling
  repo's config or of a stub's own lines, in the last third, where the work was comparing this repo
  against five others. Refusing the note protected the file tools it names; it did not protect a
  read the session reached for while thinking about something else.

`exit-masked` was 20%, **34 of them wrapping a gate**, which is the branch `session-harvest` added
on 2026-09-06 for exactly this case. `setopt` confirmed `pipefail` in force, so those exit codes
were real and no gate re-run was owed — but the count is the point: a session can be careful about
file tools and still route almost every check through a filter.

## Open questions

[NEEDS CLARIFICATION: `rg-replace-bundle` fired once — `rg -rln` typed for `rg -ln`, the exact trap
`~/AGENTS.md` documents at length with a six-row table. The rule did not prevent it. What did work
was the documented **detection signature**: the flag letters appeared where matched text belonged
(`ln` in place of every match), the session noticed within one call and re-ran correctly. That is
evidence the signature earns its place while the prohibition does not prevent the typo — which is a
different conclusion from "the wording needs work", and worth deciding before anyone rewords it.]

## Recommended direction

Merge into `2026-08-28-auto-mode-contradicts-bash-rules.md` as one more table row plus the two open
questions, and delete this file. Nothing here needs its own plan; it is filed separately only
because a session in `invoke-stubs` cannot write to this repo.
