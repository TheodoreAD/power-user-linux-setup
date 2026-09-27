---
status: idea
updated: 2026-09-28
source_repo: github.com-personal/invoke-stubs
source_session: 76d98521-8e7c-4524-bb4f-4caeb36e8cb0.jsonl
source_moment: 2026-09-27T21:25:00Z
source_plan:
---

# Candidate rule: naming a gitignored directory does not make `rg`/`fd` search it

A candidate for `config/agents-md/`, as a variant of "Searching a tree, by name or by content",
whose "Name the directory, which needs no flag at all" is true for a **hidden** path and false for a
**gitignored** one. Filed rather than written because the fragment source lives in this repo.

## Evidence

In an invoke-stubs session, looking for a string in the installed `repo_tasks` package under the
repo's own gitignored `.venv`:

- `rg -n "not in this project's dev group" -B 30 <repo>/.venv/lib/python3.11/site-packages/repo_tasks`
  returned nothing, with exit 1 and no warning.
- `fd -t d repo_tasks <repo>/.venv/lib` returned nothing.
- `rg -n --no-ignore "dev group" <same path>` found it in `deps.py`.

Both tools apply the repository's `.gitignore` to an explicitly named path inside it, so a named
directory under `.venv/`, `node_modules/` or `build/` is searched as empty. The empty result reads
exactly like "the string is not there". It cost two calls, and the session nearly concluded the
package lacked the code it was about to read.

## Recommended direction

Extend the existing section by one bullet beside "Name the directory": naming works for a hidden
path, not a gitignored one. There, `rg --no-ignore` and `fd -I`, which is the one case where `-I`
earns its place (the section already says "only to find one file you know is ignored"). No new
heading, so the rule count is unchanged.
