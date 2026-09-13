---
status: idea
updated: 2026-09-13
source_repo: github.com-personal/repo-tasks
source_session: 5de331c8-e7f0-4bcb-a86f-c242683a382d.jsonl
source_moment: 2026-09-13T00:00:00Z
source_plan: plans/2026-09-08-status-measures-the-running-interpreter-not-the-global-tool.md
---

# A third trap for the uv tool-install rule: which interpreter it lands on

## Context

`~/.agents/AGENTS.md`'s "Designing a uv tool-install or shared-dependency mechanism" carries two
traps today. A `repo-tasks` session measured a third one while settling whether its stamped
bootstrap script should pass `--python`, and it is the same kind of thing as the two already there:
something an agent cannot know, whose miss is silent.

Filed rather than applied because the rule's source is this repo's `config/agents-md/research.md`
and `~/.agents/AGENTS.md` is the deployed output — writing into another repo's tree is out, and
editing the deployed file would be overwritten by the next `inv deploy.all --name agents-md` anyway.

## Evidence

Session `5de331c8-e7f0-4bcb-a86f-c242683a382d.jsonl` under
`~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-repo-tasks/`, 2026-09-12/13. The
distinctive phrase is "Should the stamp template pin an interpreter".

Three probes on **uv 0.11.19**, each with isolated `UV_TOOL_DIR`/`UV_TOOL_BIN_DIR` so nothing on the
machine moved:

| probe                                                | uv reported, and chose                                           |
| ---------------------------------------------------- | ---------------------------------------------------------------- |
| a real git-URL target, `UV_PYTHON` unset             | `>=3.11` from `requires-python` metadata -> cpython 3.14.5       |
| a package declaring `>=3.9,<3.10`, `UV_PYTHON` unset | `>=3.9, <3.10` from `requires-python` metadata -> cpython 3.9.25 |
| the same package, `UV_PYTHON=3.14`                   | `3.14` from explicit request -> installed onto 3.14 regardless   |

The third row printed **no warning of any kind** — checked by grepping the full verbose log for
`warn`/`requires-python`/`incompatible`; the only warning in it was about the bin directory not
being on PATH.

Read from source as well as measured, in the research library's `github.com--astral-sh--uv` clone:

- `crates/uv/src/commands/tool/common.rs`, `ToolPython::from_request` — precedence is explicit
  request, then a version file discovered with `with_no_local(true)` and filtered to intersect
  `requires-python`, then a request derived from `requires-python` itself.
- `crates/uv-cli/src/lib.rs:5774` — `ToolInstallArgs::python` carries `env = EnvVars::UV_PYTHON`.
- `crates/uv-static/src/env_vars.rs:107` — "Equivalent to the `--python` command-line argument."
- `uv tool list --help` on 0.11.19 — `--show-paths`, `--show-version-specifiers`, `--show-with`,
  `--show-extras`, `--show-python`, `--outdated`, and no machine-readable mode. Relevant because the
  same investigation needed to read that listing programmatically.

## What to add

To `config/agents-md/research.md`, extending the existing section rather than adding a heading —
criterion 2 holds because "Designing a uv tool-install or shared-dependency mechanism" still names
the trigger exactly. Proposed wording, in that section's existing voice:

> And an explicit interpreter request **overrides** a package's `requires-python` instead of
> narrowing it. With no `--python` and no `UV_PYTHON`, `uv tool install` derives the request from
> the target's own `requires-python` — through a git URL too, since it fetches the static metadata
> before choosing — and takes the newest installed interpreter satisfying it. With either one set,
> uv installs against that version and says nothing when the package excludes it. So a version
> pinned into a shared installer is not a floor; it is a silent override of every consumer's own
> floor. A **local** `.python-version` is ignored for tool installs, a **global** one honoured where
> it intersects `requires-python`.

## Against the admission criteria

1. **Trigger in the heading** — unchanged, already stated.
2. **No duplication** — an extension, not a new rule, and the heading still names the trigger, so
   the extend-or-split clause resolves to extend.
3. **Evidence here, not inline** — the section above is meant to be moved into
   `contributing/global-agents-md.md` under a matching heading when this is applied, with only the
   quoted wording going into the fragment.
4. **Form** — this is the "the agent cannot know something" class the criterion explicitly exempts,
   the same class as that section's two existing traps and as the `uv run --with` rule the criterion
   names as an example. A plain statement of fact is the right form; there is no behaviour to shape.

## Recommended direction

1. Apply the wording above, move the evidence into `contributing/global-agents-md.md`, then
   `inv deploy.all --name agents-md` and delete this file.
2. Worth knowing while doing it: `[packages.uv-env]`'s `zshenv = 'export UV_PYTHON="3.14"'` is why
   every bare `uv tool install` on this machine already lands on 3.14. That makes the trap invisible
   locally and live on any machine without that variable — which is the ordinary case for a
   consumer's CI.
3. `repo-tasks` settled its own use of this as a won't-fix (no `--python` in its stamp template);
   `2026-09-12-stamp-python-item-answered-in-repo-tasks.md` in this same store carries that, and the
   two are best read together even though they belong to different files here.
