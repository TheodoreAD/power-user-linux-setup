---
status: idea
updated: 2026-09-28
source_repo: github.com-personal/scaffoldapy
source_session: 81492b4f-e6bc-4577-8d01-412b3ff4e7a9.jsonl
source_moment: 2026-09-28
source_plan:
---

# Force plain output for anything a script parses: the harness exports `FORCE_COLOR=3`

## Context

A candidate extension of `config/agents-md/bash.md`, "Formatting a date or decimal in a shell
script", which already says to force the C locale for output a script parses. **Colour is the same
trap, and three repos hit it independently in one day.**

Claude Code exports `FORCE_COLOR=3` into every Bash call, and no dotfile sets it. uv honours it even
when stdout is a pipe, and gh does too. Any code that runs a tool and parses its output gets ANSI
escapes inside the text it matches, and the failure is silent: a regex misses, or a path gains an
escape prefix and becomes relative.

## Evidence

Three independent occurrences, 2026-09-28:

1. **scaffoldapy, this session.** Its e2e fixture read `uv cache dir` to pin the real cache. The
   path came back as `\e[36m/home/.../.cache/uv\e[39m`, which is relative, so every render built a
   cold uv cache inside the generated repo. That repo's `ruff check .` then linted the cache (31,442
   findings), and the gate spun in invoke's quadratic output capture for 10 minutes until pytest's
   timeout killed it, rather than failing. Fixed in scaffoldapy `ba23071` with `uv --color never`
   plus an absolute-path check.
2. **repo-tasks `deps.check-currency`** (v0.5.0): the colored `(latest: …)` clause broke its line
   regex, so exactly the entries that were behind vanished from the report, which exited 0. Fixed in
   v0.6.0.
3. **invoke-stubs**, a parallel session, hit (2) independently and filed it.

The search `env | rg -i color` in an agent shell shows `FORCE_COLOR=3`.

## Open questions

[NEEDS CLARIFICATION: extend the locale section or give it a sibling? The shape is identical
("ambient environment changes bytes you parse; the terminal looking fine proves nothing"), so the
leanness rule says extend. It needs one sentence and the fix: `--color never`/`NO_COLOR=1`, or
`env -u FORCE_COLOR`, on any tool whose output is parsed.]

[NEEDS CLARIFICATION: or unset `FORCE_COLOR` for agent shells in `[packages.claude-code]`'s zshenv
snippet, beside `PIPE_FAIL`? That fixes every script at once but hides colour from the human-facing
output the harness wanted it for, and it breaks the moment code runs somewhere the snippet is not
(CI, a container). The instruction is the portable half either way.]

## Recommended direction

Extend the existing section with one sentence naming `FORCE_COLOR` and the plain-output flags, and
keep the rule's closing line, "verify the actual bytes", which is the same test for both.
