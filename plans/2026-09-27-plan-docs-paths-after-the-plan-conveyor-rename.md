---
status: landed
updated: 2026-09-28
---

# The plan-docs paths this repo still names, after the plan-conveyor rename

## Context

`agent-skills` renamed eight skills on 2026-09-27 and pushed them. Two of this repo's own artifacts
still name the pre-rename paths, and neither is editable from a session in `agent-skills`, so they
were filed here rather than fixed there.

The rename: `plan-docs` → `plan-conveyor`, and seven skills took a personal author mark —
`python-conventions`, `python-testing-conventions`, `mcp-python-conventions`,
`invoke-task-conventions`, `polite-mcp-conventions`, `db-defaults` and `skill-authoring` all gained
`-taudelta`. The rule and the reasoning are in `agent-skills`' own `AGENTS.md` and
`skills/skill-authoring-taudelta/references/naming.md`.

`research-library` did **not** change, despite a 2026-09-12 plan that had settled on
`research-trove`. Worth knowing before touching anything here: the reversal is deliberate, and any
citation of `research-library` in this repo is still correct.

## What needs changing here

1. **`setup.toml`, around line 2080** — the plans-store install step runs
   `python3 ~/.agents/skills/plan-docs/scripts/plans.py install`. That path no longer exists; the
   installed skill is at `~/.agents/skills/plan-conveyor/scripts/plans.py`. This is executable, so
   it fails outright rather than reading wrong.
2. **The `config/agents-md/` fragment that deploys the home instructions** — it carries
   `python3 ~/.agents/skills/plan-docs/scripts/plans.py scan --mode staged` and `--mode history` in
   the confidentiality-check block, and names `~/.config/plan-docs/config.toml` as where
   `[private] extra` goes. Same dead path in the commands, and the config directory moved too (see
   below). Edit the fragment, never the deployed `~/.agents/AGENTS.md` or `~/.claude/CLAUDE.md`
   copies, then `inv deploy.all --name agents-md`.

Nothing else in this repo is affected: `setup.toml`'s skills declaration names the **repo**
(`{ source = "npx", repo = "TheodoreAD/agent-skills", … }`), not individual skills, so the eight
renames need no entry-level change.

## The config path moved too, and the fallback is temporary

`~/.config/plan-docs/` → `~/.config/plan-conveyor/`, and `$PLAN_DOCS_CONFIG` →
`$PLAN_CONVEYOR_CONFIG`. Both predecessors are still honoured one step lower, and this machine's
file has already been moved, so nothing is broken today.

[PITFALL: **the fallback exists because the writers skeletonise, not as politeness.** `plans.py`
lays down `CONFIG_SKELETON` whenever the config path is absent, so a rename without a fallback would
have answered with an empty config rather than an error — dropping `[private] extra`, whose terms
are the ones a public-repo scan cannot derive from directory names. The scan would then pass with a
shorter term list and say nothing. Verified on 2026-09-27: reading through the fallback still
derived 61 private terms, the pre-rename count, and 61 again after the file was moved.]

[DECISION: **the fallback comes out once this plan lands.** It is a migration shim for exactly the
window this plan closes — while the deployed instructions still tell a reader to edit
`~/.config/plan-docs/config.toml`, a reader who follows them would be writing to a file nothing
reads. Once the fragment names the new path, the shim in `plans.py` and the independent one in
`harvest.py` can both go, along with their four tests in `agent-skills`'
`tests/unit/test_locations.py`. Removing them is a change in `agent-skills`, so it is that repo's
commit, not this one's.]

## Order

The fragment edit first, then `inv deploy.all --name agents-md`, then `setup.toml`. Removing the
fallback is last and belongs to the other repo — leaving it in place costs nothing but a note on the
first run from an unmigrated machine.

## Migrated to

- **The fix**: `da6da06` (2026-09-28). The plan named two places; there were nine. The other seven
  were the `home.list-claims` footer, `contributing/home-claims.md`, the archive command in
  `contributing/ssh-agent-selection.md`, `docs/claude-code.md`, the generated `docs/packages.md`,
  and two more fragments (`bash.md`, `collaboration.md`, `agent-knowledge.md`). The commit body
  lists them. The `setup.toml` path was description text, not an executed command, so nothing was
  failing outright.
- **Removing the fallback**: filed for `agent-skills` as
  `2026-09-28-remove-the-plan-docs-config-fallback.md`, carrying the PITFALL above. The fallback
  guards `[private] extra`, so it has to be removed carefully.
- Deliberately not renamed: the dated history in `contributing/global-agents-md.md`, and
  `tests/unit/test_ai.py`'s fixture skill names. Neither refers to the live skill.
