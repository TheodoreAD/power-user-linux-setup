---
status: idea
updated: 2026-09-07
source_repo: github.com-personal/repo-tasks
source_session: 52905ee0-50ff-4376-bd19-5ab4d9ca0a24.jsonl
source_moment: 2026-09-07T16:40:00Z
---

# A rule for `research.md`: sibling distributions import installed, never by path

## Context

Stated by the user 2026-09-07, verbatim: "distinct python packages with their own pyproject toml in
the same repo should not import by path manipulation without a very good reason, like a special
framework contract, which is very rare. all projects should import from the installed wheels or
editable installations". Filed here because a session in `repo-tasks` does not edit this repo.

The `~/AGENTS.md` half is one new `###` block. The enforcement half already landed in `repo-tasks`
(`1c91c2e`) and is described below, because the rule reads better with its detector named.

## The block, as drafted

Belongs in `config/agents-md/research.md` — the cluster that already holds "Designing a uv
tool-install or shared-dependency mechanism", which is the same subject one step earlier. Not
`bash.md` (nothing to do with tool calls) and not `agent-knowledge.md` (not about instructions).

> ### Two distributions in one repo
>
> **They import each other through the installed distribution — an editable install, a wheel — and
> never by putting a sibling's source directory on the path at runtime.** No `sys.path.insert`, no
> `site.addsitedir`, no `PYTHONPATH` assignment, no `__path__` mutation, and no conftest doing it on
> the suite's behalf. A uv workspace already installs its members editable, so in the normal case
> there is nothing to arrange: declare the dependency and import it.
>
> The reason is that a path insert makes the import work while the dependency stays **undeclared**.
> It is absent from the lock, from `uv sync`, and from the built wheel — so the failure lands on
> whoever installs the artifact rather than on the machine that built it, which is the worst place
> for it and the furthest from the edit that caused it.
>
> The exception is a **framework doing it in its own code**, and it is rare enough to name the one
> that actually applies: pytest's default `prepend`/`append` import modes insert the rootdir into
> `sys.path` permanently (`_pytest/pathlib.py` says so in a comment beside the code). That is
> pytest's contract with itself. It is not licence for a conftest to add a sibling's `src/`.
>
> Detected rather than remembered, where the repo runs ruff: `TID251` with `"sys.path"` and
> `"site.addsitedir"` in `[lint.flake8-tidy-imports.banned-api]`. Measured against ruff 0.14 — it
> catches the attribute, the aliased module (`import sys as s`), and `from sys import path` at the
> import; `os.environ["PYTHONPATH"] = …` and `__path__` are not expressible there and stay a review
> matter.

## Evidence

The detector is in `repo-tasks`' shipped `ruff.toml` as of `1c91c2e`, so every consumer that runs
`configs.pull` inherits it. Coverage was probed rather than assumed, with a file per spelling and
real ruff:

| spelling                            | flagged            |
| ----------------------------------- | ------------------ |
| `sys.path.insert(0, …)`             | yes                |
| `import sys as s; s.path.append(…)` | yes                |
| `from sys import path`              | yes, at the import |
| `site.addsitedir(…)`                | yes                |
| `os.environ["PYTHONPATH"] = …`      | no                 |
| `__path__.append(…)`                | no                 |

`repo-tasks` itself already satisfied the rule before any of this: no `sys.path` anywhere, and its
one workspace member is reached through `importlib.metadata.version("sample-service")` — an
installed distribution, not a path.

## Open questions

[NEEDS CLARIFICATION: does the block belong in `~/AGENTS.md` at all, or only in
`python-conventions`? It is Python-specific, which argues for the skill; but it is also a rule about
**repo layout** that an agent should follow without loading a skill, and `~/AGENTS.md` already
carries the uv tool-install and dependency-group rules for the same reason. Filed as an
`~/AGENTS.md` block on that precedent; the skill would then point at it rather than restate it.]

## Recommended direction

Add the block to `config/agents-md/research.md`, deploy with `inv deploy.all --name agents-md`, and
say in the same commit that the enforcement half is already shipping from `repo-tasks`. Nothing else
in this repo needs to change: `power-user-linux-setup` has one `pyproject.toml`, so the rule is
inert here and lands for the repos that have several.
