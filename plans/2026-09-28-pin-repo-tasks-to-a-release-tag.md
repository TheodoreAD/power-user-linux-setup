---
status: idea
updated: 2026-09-28
source_repo: github.com-personal/invoke-stubs
source_session: b418c54c-c032-4559-9cf3-6370d926625b.jsonl
source_moment: 2026-09-28T19:55:00Z
source_plan:
---

# Pin the repo-tasks dependency to a release tag

## Context

`pyproject.toml` declares `repo-tasks = { git = "https://github.com/TheodoreAD/repo-tasks" }` in
`[tool.uv.sources]`, with no `tag`. So `inv deps.lock --package repo-tasks` — the step repo-tasks'
`contributing/consumer-sweep.md` names as this repo's equivalent of `repo-tasks.stamp` — resolves
**`main`**, not the latest release.

That contradicts the family decision of 2026-09-26 (consumer-sweep.md, "pin, rather than keep
consumers' CI on `main`"): the global tool installs the latest tag, and every bootstrap script is
stamped to one. The two consumers that pin repo-tasks in their own `uv.lock` — this repo and
`invoke-stubs` — silently tracked `main` instead. The lock still pins an exact commit, so builds are
reproducible; what differs is which commit a bump lands on, and `main` can hold unreleased,
half-finished work.

`invoke-stubs` fixed its half in `9c5810b` (2026-09-28): the entry now names `@v0.6.0`, with a
comment saying a bump is that edit plus the re-lock.

## Evidence

Found during the `invoke-stubs` v0.6.0 sweep: `inv deps.lock --package repo-tasks` reported
`Updated repo-tasks v0.5.0 (023363c4) -> v0.6.0 (872dc55d)`, while v0.6.0's tag commit is `a2d9cf5`.
`872dc55` was four commits past it (plans and one docstring). The user asked "any reason we are not
using the tag?"; `invoke-stubs`' history recorded none — the bare URL predates the tag decision.

## Recommended direction

Add `tag = "v0.6.0"` (or whatever the current release is) to the `[tool.uv.sources]` entry, re-lock,
gate, and say in a comment beside it that a bump is that edit plus
`inv deps.lock --package repo-tasks`. Check whether anything here reads the source entry's shape —
e.g. a task or test that parses `[tool.uv.sources]` — before editing it.
