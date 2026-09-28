---
status: idea
updated: 2026-09-28
source_repo: github.com-personal/repo-tasks
source_session: 44be2918-1669-4d16-9f77-56535cc6ddeb.jsonl
source_moment: 2026-09-28T11:15:00Z
source_plan:
---

# Sweep to repo-tasks v0.6.0

## Context

repo-tasks v0.6.0 was released 2026-09-28 (tag on `a2d9cf5`, CI/Security/Canary green), and this
machine's global tool is already at v0.6.0. What it carries for a consumer:

- **Shipped configs:** `pyrightconfig.json` drops `allowedUntypedLibraries: ["invoke"]`, redundant
  since invoke-stubs 0.2.0. A lock still resolving invoke-stubs older than 0.2.0 is the case
  expected to go red. `zizmor.yml` disables zizmor 1.30's `self-repository` audit family-wide,
  because actionlint and act both reject its `uses: $/` fix. zizmor 1.29 accepts the unknown audit
  id.
- **`deps.check-currency`:** it confirms a flagged entry with a dry-run lock upgrade, so a latest
  release that this repo's constraints exclude (`hadolint-py!=2.15.1.2`) reads as excluded, not
  BEHIND.
- **Colour:** uv and gh output is forced plain wherever repo-tasks parses it.
  `FORCE_COLOR`/`CLICOLOR_FORCE` no longer make check-currency drop behind entries, make
  `selfinstall` see no tools, or crash `ci.status`.
- **gitflow PR mode:** finalize deletes the finished branch locally and on origin, and the start
  tasks refuse a base that is behind origin. That matters only to a repo using `gitflow.*`.

The sequence is repo-tasks' `contributing/consumer-sweep.md`, "The sweep": the per-consumer loop,
ending with `inv repo-tasks.stamp`.

## This repo's drift

`inv consumers.diff` from repo-tasks, 2026-09-28: **config files behind: `pyrightconfig.json`,
`zizmor.yml`.** Nothing else was flagged.

## The four inline zizmor ignores this sweep retires

Merged in from `plans/2026-09-28-drop-inline-zizmor-self-repository-ignores.md` (filed from the same
repo-tasks session, `source_moment: 2026-09-27T22:20:00Z`), which was cleanup timed to exactly this
sweep.

Sweeping to repo-tasks v0.5.0 took zizmor to 1.30.1, and its new `self-repository` audit flagged
four `uses: ./...` calls: `ci.yml:18`, `ci.yml:73`, `devcontainer.yml:78` and `devcontainer.yml:85`.
This repo declined them inline with `# zizmor: ignore[self-repository]`, with the reasoning beside
the first call in `ci.yml`. It did so because `zizmor.yml` is a pulled config and a local disable
would read as drift.

repo-tasks now ships the decision centrally. Its canonical `zizmor.yml` sets
`rules: self-repository: disable: true`, with the two blockers and the condition for lifting it:
actionlint and act both accepting `$/`. That is repo-tasks commit `069f3d6`, 2026-09-28, first
released in v0.6.0. From then on the four inline ignores suppress an audit that is already off.

Decided in repo-tasks session `44be2918-1669-4d16-9f77-56535cc6ddeb`, by the user's answer to
"zizmor self-repository audit: how to handle it?" choosing "Disable in shipped zizmor.yml
(Recommended)". Verified there on repo-tasks' own `security.yml:36`: zizmor 1.30.1 fails without the
disable and passes with it, and zizmor 1.29.0 accepts the unknown audit id. No open question: the
decision is made upstream.

## Recommended direction

Run the sweep per the doc. After `inv configs.pull`, remove the four
`# zizmor: ignore[self-repository]` comments and the reasoning block in `ci.yml`, then run
`inv quality.workflow-check`. It should stay green, which proves the central disable arrived. If it
goes red, the pulled config predates the change.
