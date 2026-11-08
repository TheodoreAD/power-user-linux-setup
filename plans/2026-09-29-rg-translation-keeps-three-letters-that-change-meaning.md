---
status: idea
updated: 2026-09-29
source_repo: github.com-personal/agent-skills
source_session: c7d58945-4709-4fa6-9253-1140af86d9c0.jsonl
source_moment: 2026-09-28T21:52:54.798Z
source_plan: plans/2026-09-02-rg-replace-flag-used-twice-in-one-session.md
---

# "Delete the r, keep every other letter" is wrong for `-L`, `-h` and `-I`

Belongs with this repo's `plans/2026-09-02-rg-replace-flag-used-twice-in-one-session.md`, which owns
the rule and its DECISION. This is a new failure of that rule's wording, not another `-r` sample.

## Context

`config/agents-md/bash.md`, "Translating a `grep` invocation to `rg`", says: "One edit: delete the
`r`, keep every other letter." That holds for `-n`, `-i`, `-l`, `-c`, `-v`, `-w`. It is wrong for
three letters, where the same letter means something else in rg, and each fails silently:

| grep flag | grep means                | the same letter in rg | what you get                            |
| --------- | ------------------------- | --------------------- | --------------------------------------- |
| `-L`      | files **without** a match | `--follow` (symlinks) | the matching lines: the opposite set    |
| `-h`      | no filename prefix        | `--help`              | the help text, exit 0, no search at all |
| `-I`      | skip binary files         | `--no-filename`       | a search with filenames dropped         |

rg's equivalents: `--files-without-match` (no short form), `-I`/`--no-filename`, and binary files
are skipped by default.

## Evidence

Rule shape: **followed and still produced the wrong outcome.** The agent-skills session named above
wanted the snippets that name no dependency and translated `grep -rL "pip install" <dirs>` to
`rg -L "pip install" <dirs>` exactly as the rule says (moment above). It got the files that **do**
match, and noticed only because matched lines were printed where a file list was expected.
Reproduced on purpose at 2026-09-28T22:02:30.854Z; the same session verified that
`rg -h <pat> <file>` prints rg's help and searches nothing.

## Recommended direction

Keep the one-edit rule and add the three exceptions as a short table or one sentence: "except `-L`
(use `--files-without-match`), `-h` (use `-I`) and `-I` (drop it; rg skips binaries already)". The
detection signature fits the existing paragraph's shape: a `-L` search printing lines, or a `-h`
search printing help. agent-skills files a separate plan to have `session-bash-audit` measure how
often these occur, so the rule change can be weighed against a rate.
