# MCP/skill shipping workflow

Design rationale for `skills/mcp-skill-shipping/SKILL.md` — the workflow for taking a personal MCP
server or skill repo (`olx-polite-mcp`, `emag-polite-mcp`, `altex-polite-mcp`, `temu-polite-mcp`,
`product-research-pipeline`, and future repos in the same family) from a working checkout to
something Claude Code can actually load, on the dev machine and everywhere else. What it _is_ and
how to use it live in the skill itself; this page is the _why_.

## Why a skill, not a note in this repo's own docs

The workflow applies across several sibling repos, none of which is `power-user-linux-setup`
itself — it isn't project-specific knowledge that belongs in any one `AGENTS.md`, and it isn't a
one-off preference either, so per this machine's own cross-session-memory policy (see
`~/AGENTS.md`) it doesn't belong in chat history or Claude Code's auto-memory. It's durable,
cross-repo procedural knowledge — exactly what `skills/research-library/SKILL.md` already
established the pattern for: author it once in `power-user-linux-setup` (where the declarative
`setup.toml` + `inv ai.skills` machinery already lives), and `inv ai.skills` deploys a real copy to
`~/.agents/skills/<name>` so every project on the machine picks it up automatically, not just this
one.

## Why git+`uv` instead of PyPI

Each `*-polite-mcp` repo is a personal, non-commercial, single-user (maybe a friend or two) tool.
A PyPI release process — version bumps, `uv publish`, API tokens — is ceremony with no real
audience at this scale. `uv tool install` already resolves straight from a git remote and drops a
real `PATH` shim:

```shell
uv tool install git+https://github.com/TheodoreAD/olx-polite-mcp
```

so the GitHub repo itself is the artifact store. This needs nothing beyond a `[project.scripts]`
entry point in `pyproject.toml` and a reachable (public, or deploy-key-accessible private) repo —
no packaging step, no publish step. Pin `@<tag>`/`@<sha>` once a repo reaches a point worth
freezing; tracking the default branch is fine while still iterating. Revisit PyPI only if a repo
ever needs to be pip-installable as a transitive dependency of something else, which doesn't apply
to a standalone MCP server.

(An earlier draft of this skill used `uvx --from git+URL` / `uv run --directory <path>` directly in
`claude mcp add`'s command. Revised after cross-checking against `olx-polite-mcp/README.md` — the
first sibling repo to actually reach a real "Installation" section — which settled on
`uv tool install` instead: one stable `PATH` binary name that `claude mcp add` points at regardless
of source, versus a path/flag baked into the MCP registration itself that has to change by hand
when switching source. Recorded here as the reason the skill reads the way it does now, not the
way it first did.)

## Why `--scope user` for `claude mcp add`

Claude Code's MCP registration has three scopes: `local` (per-project, per-user, unshared —
the default), `project` (writes `.mcp.json` into the project, checked into git, shared with anyone
who clones it), and `user` (`~/.claude.json`, available in every project on the machine). These are
personal cross-project tools, not something a specific project's collaborators need pinned in its
own repo — `user` scope is the direct analogue of how skills already install globally via
`inv ai.skills`, so both mechanisms end up with the same reach. `project` scope would make sense
for a _consumer_ repo (e.g. `product-research-pipeline` wanting to pin exactly which site-MCP
versions it was built against) — not ruled out, just not the default case this skill covers.

## Same registered command, two install sources — why that matters

The whole point of adding a `[project.scripts]` entry before `server.py` even exists, plus
installing it via `uv tool install` rather than pointing `claude mcp add` at a `uv run`/`uvx`
invocation directly, is that switching between "I'm actively developing this" and "I just want to
use it" becomes `uv tool install -e <path>` vs. `uv tool install git+<url>` — the _registration_
itself (`claude mcp add --scope user <name> <name>`) never changes, since both installs land the
same binary name on `PATH`. Never two divergent MCP-registration setups to keep in sync, and never
a reason to publish a dev build somewhere just to test it end-to-end.

## Deferred: a declarative `mcp_servers` list in `tasks/ai.py`

`tasks/ai.py`'s `_install_declared_skills` already reads a `skills` list off any `setup.toml`
package and installs local-vs-npx sources idempotently (skipping work that's already done,
tracking provenance via `.pulse-source`). The natural extension once at least one of these MCP
servers has real code: a `mcp_servers` list read the same way, each entry declaring
`{name, repo, entry_point}`, driving `claude mcp add --scope user` calls (no-op if already
registered with the same command) — the same idempotent, declarative shape as skills and the
static-Claude-permissions merge in the same file.

Not built yet, deliberately: there's nothing to register until `olx-polite-mcp` (the
most implementation-ready of the three site MCPs, per `product-research-pipeline/ROADMAP.md`)
actually has a `server.py`. Building the declarative installer ahead of a real consumer risks
guessing at a shape that doesn't match what registering an actual server needs. Revisit once one
server is real.
