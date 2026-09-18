---
status: idea
updated: 2026-09-13
source_repo: github.com-personal/ingesta
source_session: 21c18768-649d-4753-9dca-e23e5b9555d3.jsonl
source_moment: 2026-09-13T18:42:02+03:00
source_plan: plans/2026-09-02-agents-md-adherence-sample-corpus.md
---

# An adherence sample that splits in two at a context compaction

## Context

A candidate row for `plans/2026-09-02-agents-md-adherence-sample-corpus.md`, measured by a harvest
of a long `ingesta` background job (2026-09-06 to 2026-09-13, one repo, code + browser tier + plans

- a consumer sweep). The whole-session row is ordinary. **What is not ordinary is that the session
  was compacted once, and its adherence is two different sessions either side of that instant.**

## Evidence

`audit.py --session 21c18768-649d-4753-9dca-e23e5b9555d3`, no `--compare`, so no score. The
compaction's continuation turn is at `2026-09-12T19:17:19Z` in the transcript. The session was
harvested twice; these are the figures at the **second** boundary, `2026-09-13T18:42:02+03:00`,
because a row taken at the first (`18:07:33`, 683 calls) was a prefix of the session.

| window                         | calls | chain | `head/tail` | `exit-masked` | heredoc | `sed-n` | `git-C-own-repo` |
| ------------------------------ | ----: | ----: | ----------: | ------------: | ------: | ------: | ---------------: |
| before the compaction          |   501 |   67% |         48% |           35% |     32% |     15% |               0% |
| after it, to the last harvest  |   220 |    1% |          0% |            0% |      0% |      4% |               0% |
| whole session, to that harvest |   721 |   47% |         33% |           24% |     22% |     12% |               0% |

The after-compaction row is the whole-session counts minus the `--until 2026-09-12T19:17:19Z`
counts: chain 339−336, `head/tail` 238−238, `exit-masked` 175−175, heredoc 159−159, `sed-n` 83−75.
It includes the first harvest's own inspection calls, which moved none of those counts. At the first
boundary the same row read 182 calls, 2% chain, 4% `sed-n`.

- `exit-masked` 175 = **105 wrapped a gate**, 70 a listing, every one before the compaction.
  `setopt` in the session's shell shows `pipefail`, so the nine green-gate messages stood on real
  exit codes and no re-run was owed.
- The heredoc row is almost entirely `python - <<'PY'` scripts doing string replacement on repo
  files — the Edit-tool rule, not followed 159 times, all before the compaction. After it, every
  edit went through Edit/Write.
- The compaction's continuation re-injected both instruction files in full (a system reminder
  carrying `~/.claude/CLAUDE.md` and the repo's `CLAUDE.md`).

## Open questions

Whether this is the instruction files being re-read or the conversation being shortened, since a
compaction does both at once and this sample cannot separate them. A session whose instruction files
are re-injected **without** a compaction, or compacted without re-injection, would.

## Recommended direction

Add it as a row, with the split recorded rather than only the whole-session figure — a whole-session
`33% head/tail` describes neither half. If a second long session shows the same step at its
compaction, the finding is that Bash-rule adherence decays with context length and is restored by
re-reading the rules, which is a different lever from rewording them.
