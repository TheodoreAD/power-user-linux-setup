---
status: idea
updated: 2026-11-27
source_repo: github.com-personal/hekate
source_session: 5f84bc91-7291-42b4-9474-846d42d45b23.jsonl
source_moment: 2026-11-27T18:36:00Z
source_plan:
---

# A split commit's gate, run in the working tree, verifies the final state, not the intermediate

## Context

`config/agents-md/git.md`, "When two concerns land in the same file", says to edit the file back
down to the first concern and "verify that state passes the gate". When the rest of the finished
work is still uncommitted around that file, the working tree is not that state. A gate run there
checks the cut-down file against every later change, so a split that does not decompose still
passes.

Kind of misuse: the rule is **followed and still produces the wrong outcome**. It is aimed at a
one-file split, and it breaks for a multi-commit split of a large change.

## Evidence

In hekate session `5f84bc91-7291-42b4-9474-846d42d45b23`, on 2026-11-27, the session split one
feature into four commits. `tests/unit/conftest.py`, `pyproject.toml`, `apicurio.py` and the
`Tiltfile` each needed a cut-down version in an earlier commit.

What worked:

- A scratch worktree at `HEAD`, from `git worktree add --detach <scratchpad>/wt HEAD`.
- Copying in only that commit's files.
- Running the main checkout's tools by absolute path, with `PYTHONPATH` set to the worktree's
  `packages/*/src`. The editable installs otherwise resolve imports to the main tree.
- Checking the import path with a `print(module.__file__)` probe first.

Each intermediate commit then passed `pytest tests/unit` on its own tree: 246, then 252, then 255
tests.

Three traps on the way, all from the harness rather than git:

- After `cd` into the worktree, Claude Code reported it as the new primary working directory. A
  later `cd <main> && git add …` reset back, so the next `git add` and `git commit` ran in the
  worktree, on a detached HEAD. This was harmless only because the worktree held identical content.
  The session then built every commit there and moved the branch with `git reset --soft <sha>` and
  `git reset` in the main checkout.
- The worktree has no venv, so the direnv hook gave it no tools. Bare `pytest` and `ruff` failed
  with `command not found`.
- After `git worktree remove`, the shell came back to the main checkout without its venv on `PATH`.
  `inv quality.precommit` failed with `ruff not found on PATH` until the call was prefixed with
  `PATH=<repo>/.venv/bin:$PATH`.

## Open questions

[NEEDS CLARIFICATION: is a scratch worktree the rule's answer for multi-commit splits, or should the
rule say to commit the intermediate first and let CI judge it? It must stay unpushed until the whole
series is ready, since a pushed intermediate is a published red commit if it fails.]

## Recommended direction

Extend the existing paragraph rather than adding a section. When other changes stay uncommitted
around the split, verify the intermediate in a scratch worktree at `HEAD` holding only that commit's
paths. Run the main venv's tools by absolute path there, with `PYTHONPATH` on the worktree's
sources. Then name the cwd trap. The direnv behaviour may belong to `[packages.claude-direnv-hook]`
instead.
