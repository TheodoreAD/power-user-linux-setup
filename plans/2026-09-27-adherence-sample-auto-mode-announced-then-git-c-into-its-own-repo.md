---
status: idea
updated: 2026-09-27
source_repo: github.com-personal/invoke-stubs
source_session: 65f8437a-a90e-41c6-9b1f-9b43d713ed9b.jsonl
source_moment: 2026-09-27T19:47:51Z
---

# Adherence sample: the session that announced the auto-mode carve-out and then broke the half it had announced

Belongs in `plans/2026-09-02-agents-md-adherence-sample-corpus.md` as a new numbered sample. Filed
rather than appended, because that plan lives in a repo this session is not working in.

## Context

An `invoke-stubs` session, 119 Bash calls, run under **auto mode**. It is worth a row for two
reasons that pull in opposite directions, which is what makes it more interesting than its score.

**It got the auto-mode rule right out loud, and then broke it.** The session's second message says,
verbatim:

> Note: auto mode asks for Bash over the file tools; per `~/AGENTS.md` I'll search with `rg` but
> keep Read/Edit/Write.

That is exactly what `2026-08-28-auto-mode-contradicts-bash-rules.md` asks for, stated unprompted
and before any file was touched. It then read files through `sed -n` seven times and `cat`/`head`
three more, while also using Read/Edit/Write throughout — so the announcement was not a lie told
once, it was a rule the session held and then leaked out of, on the specific tool it had just named.
Every one of the ten was a read of a file it could have opened with Read: invoke's own source in the
uv cache five times, its own plan twice, its own README once, its own conftest once.

**And `git -C` at its own repo, eight times, four of them mutating.** The corpus records only two
earlier non-zero rows on `git-C-own-repo` — sample 1 at 23%, and one later row its summary calls the
second — so this is a third instance of the pattern `~/.agents/AGENTS.md` singles out as six times
commoner than the `cd` it replaced. The shape is specific and worth recording: the session typed
`cd` into its own repo exactly **once**, and only to recover after a `cd` to the scratchpad had
stuck — the rule's own recovery case — while aiming `git -C <its own repo>` at `add`, `commit`,
`status` and `log`. Compliance with the `cd` half and breach of the `git -C` half, in one session,
is the pattern the rule's own wording predicts.

## Evidence

| row                     | this session | vs baseline    |
| ----------------------- | -----------: | -------------- |
| calls                   |          119 |                |
| `chain`                 |     22% (26) | −12pp, OK      |
| `head/tail`             |     13% (16) | −7pp, OK       |
| `exit-masked`           |     10% (12) | 8 gate, 4 list |
| `sed-n`                 |       6% (7) | **+3pp, MISS** |
| `cat-view`              |       3% (3) | **+1pp, MISS** |
| `heredoc`               |       1% (1) | −6pp, OK       |
| `cd-own-repo`           |       1% (1) | **MISS**       |
| `git-C-own-repo`        |       7% (8) | **MISS**       |
| `git-C-mutating`        |       3% (4) | **MISS**       |
| `git-mutating-in-chain` |       2% (2) | −1pp, OK       |
| `cut-message`           |         0/10 | OK             |

**12/17 expectations met.** Measured 2026-09-27 with `audit.py --session … --until <boundary>` from
the `agent-skills` checkout, against `~/.local/state/session-bash-audit/2026-09-12.json`. Two
caveats on the comparison: the baseline is a six-day corpus and this is one session, so only the
rates compare; and it predates the replay-dedupe fix, which the tool itself warns moves any row a
resumed session dominated.

**`exit-masked` resolved clean, and by the cheap route.** Eight of the twelve masked calls wrapped a
gate — mypy probes and one `pytest` run, all `2>&1 | tail -N` — and the session made four "gate
green" claims. `setopt | rg pipefail` answered `pipefail`, so those pipelines reported real exit
codes and no re-run was owed. Independently, every claim actually rested on an unpiped
`inv quality.precommit` or `inv test.integration`; the masked calls were probes whose success the
session read from mypy's own output text.

`head/tail` was 16 calls with **0 actually cut** — the truncation counter's answer, not an
inference.

## Open questions

[NEEDS CLARIFICATION: is the announcement itself worth anything? The corpus's existing auto-mode
rows are sessions that silently complied or silently did not. This one stated the carve-out
correctly, unprompted, and then produced the second-highest `sed-n` in the corpus anyway — which
either means the announcement is a costless ritual, or that it caught the _search_ half (`rg` at 0
misses, `grep-r-not-rg` and `find-not-fd` both zero) while the _viewing_ half has no such prompt.
The two halves scoring oppositely in one session is the evidence either reading has to explain.]

## Recommended direction

Add it as the next numbered sample. The two claims worth carrying into the corpus summary are the
split described above — search rules held, viewing rules leaked, in a session that had named both —
and the third non-zero `git-C-own-repo` row, alongside the detail that the same session used `cd`
into its own repo only as the documented recovery.
