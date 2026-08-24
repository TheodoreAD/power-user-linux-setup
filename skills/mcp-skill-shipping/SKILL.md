---
name: mcp-skill-shipping
description: "Use when developing or distributing a personal MCP server or Agent Skill repo (e.g. the `*-polite-mcp` family, `product-research-pipeline`), or deciding how to register one with Claude Code — dev-loop setup, git-as-artifact-store distribution (no PyPI), local-vs-deployed registration, and how skills ship via the existing `inv ai.install-skills` mechanism."
---

# Shipping personal MCP servers and skills

Workflow for repos whose entire purpose is producing an MCP server or a skill for personal,
cross-project use (not a library other code imports) — e.g. `olx-polite-mcp`, `emag-polite-mcp`,
`altex-polite-mcp`, `temu-polite-mcp`, `product-research-pipeline`. Covers going from a working repo
to "loadable by Claude Code in any project," and how that differs between the dev machine and
everywhere else.

## Per-repo dev loop

Every repo in this family takes [`repo-tasks`](https://github.com/TheodoreAD/repo-tasks) as a dev
dependency (git-as-artifact-store, no PyPI —
`uv add --dev git+https://github.com/TheodoreAD/repo-tasks`) instead of hand-rolled `tasks.py`
logic; the repo's own `tasks.py` is then just `from repo_tasks
import ns`. See that repo's own
README for the full task catalog (one invoke module per facility — `quality`, `venv`, `deps`,
`direnv`, `agents`, `docs`, ...) — the two that matter for day-to-day work here:

- `inv dev-env.setup` once after cloning — syncs `.venv` from `uv.lock` (fails loudly on a missing
  or stale lockfile rather than silently rewriting it), `direnv allow`s it, and wires Claude Code's
  Bash tool to auto-activate the same venv (a no-op if the repo has no `.envrc`).
- `inv quality.precommit` before considering a change done — fixes everything auto-fixable
  (`ruff`/`dprint`/`shfmt`), then runs the full CI-style gate (lint/format/type-check/shell-check/
  test). `pytest` runs against checked-in fixtures (saved HTML snapshots, etc.) — no live-network
  calls in tests.
- `AGENTS.md` + `CLAUDE.md` symlink + `.agents/skills`/`.claude/skills` scaffold comes from
  [`scaffoldapy`](https://github.com/TheodoreAD/scaffoldapy) automatically at generation time —
  nothing to run for it.

`invoke` is a per-project venv dependency (pulled in transitively via `repo-tasks`), never assumed
to be a machine-wide tool — unlike `power-user-linux-setup`'s own `inv`, which `bootstrap.sh`
installs as a global `uv tool` for real end users. Anything invoking `inv` from outside an
already-activated shell (a CI step, a `copier.yml` `_tasks` hook, any automation) needs
`uv run inv <task>`, not bare `inv` — nothing guarantees the latter resolves. `scaffoldapy`'s
`copier.yml` (`_tasks: [uv sync, uv run inv configure]`) and every generated repo's own
`.github/workflows/ci.yml` (`uv run inv quality.check`) both already follow this; keep new
automation consistent with it rather than assuming a global `inv`.

## One entry point, `uv tool install` for a stable PATH binary

Add a `[project.scripts]` entry point to the MCP repo's `pyproject.toml` (e.g.
`olx-polite-mcp = "olx_polite_mcp.server:main"`) before writing `server.py`, not as a retrofit. Then
install it as a real tool via `uv tool` (validated end-to-end in `olx-polite-mcp/README.md`) rather
than pointing `claude mcp add` at a `uv run`/`uvx` invocation — `uv tool install` builds an isolated
env and drops a shim on `PATH` (`~/.local/bin/` by default), so registration itself becomes a bare
binary name with no path/flags to keep in sync:

Install against the **local working tree** while actively developing (editable — picks up local
edits without reinstalling, so the repo has to stay put at that path):

```shell
uv tool install -e ~/projects/github.com-personal/olx-polite-mcp
```

Install **from GitHub** once not actively iterating (pin `@<tag>`/`@<sha>` for reproducibility, omit
for the default branch):

```shell
uv tool install git+https://github.com/TheodoreAD/olx-polite-mcp
```

Either way, registration is the same one-liner, independent of which source was installed:

```shell
claude mcp add --scope user olx-polite-mcp olx-polite-mcp
```

Switching sources is `uv tool install` again with the other source (uv replaces the existing tool) —
no `claude mcp remove`/re-`add` needed, since the registered command name never changes.
`--scope user` (not `local`/`project`) matches how skills already install globally, so the server is
available in every project on this machine, not just one. Use `--scope project` instead only for a
_consumer_ repo that wants the server offered automatically to anyone who clones it (see
`olx-polite-mcp/README.md`'s project-scope example) — a different case than personal cross-project
use.

Editable and from-GitHub installs can't be combined (editable needs a real working directory uv can
point at; a git-sourced install doesn't expose one) — for "edit locally, sourced as if from GitHub,"
`git clone` it yourself, then `uv tool install -e` that clone, which is just the editable-from-disk
case again.

Project- and user-scope servers need a one-time approval on `claude` startup before a _new_ session
launches them (`claude mcp list` shows pending ones) — an already-running session that had it
approved keeps it live.

## Distribution: skip PyPI

At this scale (personal, non-commercial), `uv tool install` resolving straight from a git remote
(see above) makes the GitHub repo itself the artifact store — no version-bump/publish/credentials
ceremony. Pin `@<tag>`/`@<sha>` once a repo has a stable point worth freezing; no ref (tracks the
default branch) is fine while iterating.

## Skills ship via the existing mechanism — don't build a new one

A skill repo (like `product-research-pipeline`'s orchestrator skill) doesn't need any of the above.
`inv ai.install-skills` (`tasks/ai.py`) already installs a named skill from any public GitHub repo
via the `skills` CLI. Once the repo is public with a real skill directory, add to a
`power-user-linux-setup` `setup.toml` package:

```toml
skills = [{ source = "npx", repo = "TheodoreAD/product-research-pipeline" }]
```

then `inv ai.install-skills` makes it available globally, same as every other declared skill.

## Convention skills should self-update on friction

A skill that encodes a convention (not a one-shot task) should build in a way to improve itself from
real usage, not just get read and followed. Default pattern for any new convention skill: when using
it produces a genuinely ambiguous call the skill's own rules don't resolve, or the user corrects a
decision it made, escalate to the user with `AskUserQuestion` rather than guessing — then fold the
resolution back into the skill's own source as a small, additive edit (never the installed
`~/.agents/skills/<name>` copy, which is a plain file copy clobbered by the next
`inv ai.install-skills` run) and re-run `inv ai.install-skills` so the fix reaches every project.
`skills/session-harvest/SKILL.md` is the worked example — its own "On friction, ask" + "Self-update
mechanics" sections are the pattern to copy when authoring the next one.

## A skill's follow-up checks are procedures it runs, not chores it hands back

When a skill's own research ends in "re-measure after a week", "verify X live", "compare against the
baseline", that list is the skill's job, not the user's: encode each item as something the skill
executes on the next invocation — a script flag with pass/fail output (`--compare <baseline>` with
per-expectation verdicts), a stored baseline file the skill diffs against, a printed probe plan with
expected outcomes the agent runs step by step. What genuinely can't be automated (a human watching
for a permission prompt) is reduced to one yes/no question, not left as a numbered to-do. Stated by
the user 2026-08-24 on `session-bash-audit`'s first version, which closed with a manual "open / to
re-measure" list: "i don't want to do this manually, the skill should do this for me." That skill's
Measure / Compare / Probe split is the pattern to copy.

## Full rationale

See [`contributing/mcp-skill-shipping.md`](../../contributing/mcp-skill-shipping.md) in the
`power-user-linux-setup` repo for why git+`uv` was chosen over PyPI, why `--scope user`, and a
deferred idea for a declarative `mcp_servers` list in `tasks/ai.py`.
