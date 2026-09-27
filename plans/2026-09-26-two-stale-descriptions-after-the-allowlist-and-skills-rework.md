---
status: landed
updated: 2026-09-28
source_repo: github.com-personal/agent-skills
source_session: 8db05b10-386d-41aa-884b-890e81fdada7.jsonl
source_moment: 2026-09-26T19:14:00Z
source_plan:
---

# Two descriptions here contradict the code beside them

## Context

Found read-only from an agent-skills session that was updating its own citations of this repo's
allowlist. Nothing was written to this tree.

## Evidence

1. **`tasks/ai.py`, `install_skills`'s docstring** opens "Ensure .agents/skills exists with
   .claude/skills symlinked to it". The function called just above it, `_ensure_agents_skills`, says
   in its own docstring that it deliberately stopped linking `.claude/skills` on 2026-09-07 and
   leaves per-skill links to the `skills` CLI. `inv ai.install-skills --help` prints the stale
   sentence, which is where a reader meets it.
2. **`contributing/cli-allowlist.md`, section "`inv` — deliberately unreviewed, same shape as
   `sed`"** ends: "Rules for `inv` stay hand-maintained in `~/.claude/settings.json` — today just
   `Bash(inv quality.*)` as `allow`". `cli-allowlist/tools.toml`'s `[inv]` entry now says those
   rules moved there from `setup.toml` on 2026-09-26 as `overrides_only` / `allow_overrides`,
   covering `quality.*`, `test.*`, `--list` and the read-only-by-name globs.

## Recommended direction

Reword both to match the code. Each is one or two sentences.

## Migrated to

- `install_skills`' docstring: `ec0f79f`, which also corrects "local repo paths symlinked in" (every
  source goes through the `skills` CLI) and regenerates `docs/tasks.md`.
- The `inv` section of `contributing/cli-allowlist.md`: `268877b`, now pointing at
  `cli-allowlist/tools.toml`'s `[inv]` entry.
