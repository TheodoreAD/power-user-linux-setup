---
status: idea
updated: 2026-11-27
---

# The basedpyright LSP plugin checks another repo's files against this session's project

## Context

`config/claude-plugins/basedpyright-lsp/.claude-plugin/plugin.json` starts the language server with
`uv run --no-sync --directory ${CLAUDE_PROJECT_DIR} --with basedpyright basedpyright-langserver`, so
one server runs in the session's project and resolves every file against that project's environment
and `pyrightconfig.json`.

Seen 2026-11-27 in a power-user-linux-setup session doing a cross-repo sweep: an edit to
scaffoldapy's `tests/unit/test_template.py` came back with `Import "copier" could not be resolved`
and `Import "tests.support" could not be resolved`, plus a cascade of `reportUnknown*` warnings.
scaffoldapy's own gate ran basedpyright on the same file with 0 errors, 0 warnings. A throwaway
script in the session's scratchpad got `reportAny` errors under this repo's strict settings, which
no scratch file is written to pass.

The cost is noise that reads as real: an agent that trusts the diagnostic block either "fixes"
imports that are fine or learns to ignore the block, which defeats the plugin in the repo where it
is right.

## Open questions

- Does Claude Code's plugin LSP support one server per workspace root, or a root derived from the
  edited file (nearest `pyproject.toml`)? If so, the plugin could start the server per repo.
- Failing that, is restricting `extensionToLanguage` impossible per path, so the remaining lever is
  documenting the limit in `docs/claude-code.md`?

## Recommended direction

Read the plugin LSP section of the Claude Code docs mirror in the research library for how a
server's root is chosen; if a per-file root exists, use it, and otherwise document that diagnostics
on files outside the session's project are not trustworthy, next to the plugin's description.
