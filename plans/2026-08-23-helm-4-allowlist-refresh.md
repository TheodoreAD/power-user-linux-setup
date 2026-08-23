---
status: idea
updated: 2026-08-23
---

# Helm 3→4 upgrade: cli-allowlist refresh

## Context

Helm jumped from v3.1.0 (stale manual install from Feb 2020, `/usr/local/bin`) to v4.2.4 (managed
`archive` install via `setup.toml`, `~/.local/bin`) on 2026-08-23, as the fix for a broken cached
zsh completion (`~/.oh-my-zsh/cache/completions/_helm` parse error — pre-3.2 helm emitted a
bash-emulation shim instead of native zsh completion).

`cli-allowlist/rules/helm.json` (39 nodes, depth 2, extracted/classified 2026-08-10) and whatever
`inv allowlist.apply` rendered into `~/.claude/settings.json` were all generated from **helm
3.1.0's** help output. `inv allowlist.status` already reports
`helm: v3.1.0 [STALE, 2 invalid
(excluded)]` — the version-hash staleness check caught the bump;
nothing has been refreshed yet.

Known ingredients that make this more than a routine re-extract:

- **Major-version jump across ~6 years.** Helm 4 (released late 2025) removed/changed subcommands
  and flags relative to 3.x, and 3.1.0 predates even most of helm 3's own additions. Expect the node
  tree to change shape substantially, not just re-hash.
- **Community-seeded depth-1 nodes.** helm is one of the six tools whose depth-1 nodes carry
  `source: "community"` (seeded from `UgurcanAkkok/claude-allow-list`, curated against helm 3
  semantics). `classify` deliberately re-sweeps community nodes into fresh LLM classification
  regardless of content hash, so this self-liquidates on the next classify run — but verify it
  actually happens for all of them.
- **Curated seed list in `tools.toml`.** `[helm]`'s `subcommands` list (15 entries: list, status,
  history, get, show, template, lint, diff, repo, search, plugin, env, install, upgrade, rollback,
  create, package, uninstall) was written against helm 3's command set. Any helm-4-removed entry
  extracts garbage or errors; any helm-4-new command is silently absent from the tree.
- **Previously-invalid nodes.** The 2 excluded nodes (`diff` — a plugin whose --help echoed generic
  output; `list maudlin-arachnid` — discovery-regex misfire, per `tools.toml`'s header) may resolve
  differently under helm 4's help output.

## Open questions

- [NEEDS CLARIFICATION: what did helm 4 actually add/remove/rename at the subcommand level vs 3.x?
  Needs a real pass over `helm --help` v4 output (and release notes / migration guide), not memory —
  drives whether `tools.toml`'s `subcommands` seed list needs edits before re-extracting.]
- [NEEDS CLARIFICATION: did any surviving subcommand change _risk tier_ between 3 and 4 (e.g. plugin
  system rework — helm 4 changed how plugins install/run)? Content-hash-triggered reclassification
  covers nodes whose help text changed, but a semantics change with near-identical help text would
  slip through; is a targeted review of write/dangerous-adjacent nodes warranted?]
- [NEEDS CLARIFICATION: should `setup.toml`'s `[packages.helm]` pin major version 3 instead of
  tracking latest? `version_cmd` grabs the latest GitHub release, which is now the 4.x line; helm
  3.x is still maintained. Depends on whether anything on this machine (charts, scripts, clusters)
  needs helm 3 behavior — if yes, this whole plan changes shape (refresh against 3.19.x instead).]
- [NEEDS CLARIFICATION: does the currently-applied `~/.claude/settings.json` contain any
  helm-3-derived rule that is now wrong-tier under helm 4 (allowing something that got more
  dangerous)? Worth checking the rendered helm rules specifically before waiting on a full pipeline
  run.]

## Recommended direction

Use the pipeline's own designed refresh path rather than anything bespoke — this is exactly the
scenario the staleness detection exists for:

1. Decide the version question first (pin 3 vs accept 4) — everything downstream depends on it.
2. If staying on 4: update `[helm]` in `cli-allowlist/tools.toml` against real helm 4 `--help`
   output (drop removed subcommands, add new ones worth tracking), then `inv allowlist.extract` →
   `classify` → `reconfirm` (for any needs_review) → `review` → `render` → `apply`.
3. Sanity-check the diff of `cli-allowlist/rules/helm.json` and the rendered settings rules by hand
   — a major-version jump is the case where skimming the review step is least safe.
4. Confirm the community-seeded depth-1 nodes all came back `source: "llm"` after the sweep.

Read `contributing/cli-allowlist.md` before executing — the review/render/reconfirm steps have
documented gotchas this plan doesn't repeat.
