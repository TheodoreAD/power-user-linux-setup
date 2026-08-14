---
name: mcp-skill-shipping
description: "Use when developing or distributing a personal MCP server or Agent Skill repo (e.g. the `*-polite-mcp` family, `product-research-pipeline`), or deciding how to register one with Claude Code — dev-loop setup, git-as-artifact-store distribution (no PyPI), local-vs-deployed registration, and how skills ship via the existing `inv ai.skills` mechanism."
---

# Shipping personal MCP servers and skills

Workflow for repos whose entire purpose is producing an MCP server or a skill for personal,
cross-project use (not a library other code imports) — e.g. `olx-polite-mcp`, `emag-polite-mcp`,
`altex-polite-mcp`, `temu-polite-mcp`, `product-research-pipeline`. Covers going from a working repo to "loadable by
Claude Code in any project," and how that differs between the dev machine and everywhere else.

## Per-repo dev loop

- `uv sync` + `direnv allow` — uv-managed `pyproject.toml`, dev dependency group (`pytest`, `ruff`).
- `pytest` runs against checked-in fixtures (saved HTML snapshots, etc.) — no live-network calls in
  tests.
- `ruff check` / `ruff format --check` before considering a change done.
- `inv ai.init --dir <path>` (from a `power-user-linux-setup` checkout) once per repo, for
  `AGENTS.md` + the `.claude/skills` symlink — never overwrites existing content.

## One entry point, `uv tool install` for a stable PATH binary

Add a `[project.scripts]` entry point to the MCP repo's `pyproject.toml`
(e.g. `olx-polite-mcp = "olx_polite_mcp.server:main"`) before writing `server.py`, not as a
retrofit. Then install it as a real tool via `uv tool` (validated end-to-end in
`olx-polite-mcp/README.md`) rather than pointing `claude mcp add` at a `uv run`/`uvx` invocation —
`uv tool install` builds an isolated env and drops a shim on `PATH` (`~/.local/bin/` by default),
so registration itself becomes a bare binary name with no path/flags to keep in sync:

Install against the **local working tree** while actively developing (editable — picks up local
edits without reinstalling, so the repo has to stay put at that path):

```shell
uv tool install -e ~/projects/github.com-personal/olx-polite-mcp
```

Install **from GitHub** once not actively iterating (pin `@<tag>`/`@<sha>` for reproducibility,
omit for the default branch):

```shell
uv tool install git+https://github.com/TheodoreAD/olx-polite-mcp
```

Either way, registration is the same one-liner, independent of which source was installed:

```shell
claude mcp add --scope user olx-polite-mcp olx-polite-mcp
```

Switching sources is `uv tool install` again with the other source (uv replaces the existing tool)
— no `claude mcp remove`/re-`add` needed, since the registered command name never changes.
`--scope user` (not `local`/`project`) matches how skills already install globally, so the server
is available in every project on this machine, not just one. Use `--scope project` instead only
for a _consumer_ repo that wants the server offered automatically to anyone who clones it (see
`olx-polite-mcp/README.md`'s project-scope example) — a different case than personal cross-project
use.

Editable and from-GitHub installs can't be combined (editable needs a real working directory uv
can point at; a git-sourced install doesn't expose one) — for "edit locally, sourced as if from
GitHub," `git clone` it yourself, then `uv tool install -e` that clone, which is just the
editable-from-disk case again.

Project- and user-scope servers need a one-time approval on `claude` startup before a _new_
session launches them (`claude mcp list` shows pending ones) — an already-running session that had
it approved keeps it live.

## Distribution: skip PyPI

At this scale (personal, non-commercial), `uv tool install` resolving straight from a git remote
(see above) makes the GitHub repo itself the artifact store — no version-bump/publish/credentials
ceremony. Pin `@<tag>`/`@<sha>` once a repo has a stable point worth freezing; no ref (tracks the
default branch) is fine while iterating.

## Skills ship via the existing mechanism — don't build a new one

A skill repo (like `product-research-pipeline`'s orchestrator skill) doesn't need any of the above.
`inv ai.skills` (`tasks/ai.py`) already installs a named skill from any public GitHub repo via the
`skills` CLI. Once the repo is public with a real skill directory, add to a `power-user-linux-setup`
`setup.toml` package:

```toml
skills = [{ source = "npx", repo = "TheodoreAD/product-research-pipeline" }]
```

then `inv ai.skills` makes it available globally, same as every other declared skill.

## Full rationale

See [`contributing/mcp-skill-shipping.md`](../../contributing/mcp-skill-shipping.md) in the
`power-user-linux-setup` repo for why git+`uv` was chosen over PyPI, why `--scope user`, and a
deferred idea for a declarative `mcp_servers` list in `tasks/ai.py`.
