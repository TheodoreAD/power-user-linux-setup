---
status: idea
updated: 2026-09-28
source_repo: github.com-personal/invoke-stubs
source_session: 76d98521-8e7c-4524-bb4f-4caeb36e8cb0.jsonl
source_moment: 2026-09-27T21:31:09Z
source_plan:
---

# Candidate rule: use the repo's `inv` task, not the raw tool it wraps

A candidate for `config/agents-md/`, as a variant of "Invoking a venv tool in the session's own
project". Filed rather than written because the fragment source lives in this repo.

## Evidence

In an invoke-stubs session, the user asked mid-turn, verbatim: _"why are we doing uv commands
instead of invoke commands?"_ The session had run `uv lock` directly three times: a five-package
`--upgrade-package` upgrade, a pin-only regeneration while splitting a commit, and a relock after a
version bump. `inv deps.lock` exists for all three, and its docstring says it is "the only task in
this package that ever runs `uv lock`". The lock came out identical either way. The cost was the
repo's single-writer invariant, and a reader who has to ask.

What made it easy to miss: `deps.lock --package` takes one name, so a multi-package upgrade looked
like it needed the raw tool, when five calls of the task was the answer. No rule in
`~/.agents/AGENTS.md` says to prefer a task over the tool it wraps. The nearest one, "Run the bare
command", is about `uv run` wrappers, not about bypassing tasks.

## Open questions

[NEEDS CLARIFICATION: always-loaded rule or skill? The miss is silent (identical output) but cheap
and recoverable (nothing broke), which by `contributing/global-agents-md.md`'s tier test points at a
skill, most likely `invoke-task-conventions-taudelta`. Against that: the trigger, about to run
`uv lock`/`uv sync`/`uv pip` in a repo with `inv` tasks, fires while doing something else, which is
the always-loaded file's case. A one-sentence extension of the existing section keeps the rule count
unchanged.]

## Recommended direction

One sentence appended to "Invoking a venv tool in the session's own project": where the repo has an
`inv` task wrapping a tool (`deps.lock`, `venv.sync`, `venv.recreate`), call the task, and call it
once per item when it takes one. Raw `uv` only where no task can exist yet: a CI bootstrap, or a
scratch environment outside the repo.
