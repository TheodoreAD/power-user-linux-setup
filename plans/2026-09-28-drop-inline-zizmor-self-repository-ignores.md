---
status: idea
updated: 2026-09-28
source_repo: github.com-personal/repo-tasks
source_session: 44be2918-1669-4d16-9f77-56535cc6ddeb.jsonl
source_moment: 2026-09-27T22:20:00Z
source_plan: plans/2026-09-28-zizmor-self-repository-audit-conflicts-with-actionlint-and-act.md
---

# Drop the four inline zizmor self-repository ignores once repo-tasks' shipped config disables it

## Context

Sweeping to repo-tasks v0.5.0 took zizmor to 1.30.1, and its new `self-repository` audit flagged
four `uses: ./...` calls: `ci.yml:18`, `ci.yml:73`, `devcontainer.yml:78` and `devcontainer.yml:85`.
This repo declined them inline with `# zizmor: ignore[self-repository]`, with the reasoning beside
the first call in `ci.yml`. It did so because `zizmor.yml` is a pulled config and a local disable
would read as drift.

repo-tasks now ships the decision centrally. Its canonical `zizmor.yml` sets
`rules: self-repository: disable: true`, with the two blockers and the condition for lifting it:
actionlint and act both accepting `$/`. That is repo-tasks commit `069f3d6`, 2026-09-28, and it
reaches this repo at the first release after v0.5.0. From then on the four inline ignores suppress
an audit that is already off.

## Evidence

Decided in repo-tasks session `44be2918-1669-4d16-9f77-56535cc6ddeb`, by the user's answer to
"zizmor self-repository audit: how to handle it?" choosing "Disable in shipped zizmor.yml
(Recommended)". Verified there on repo-tasks' own `security.yml:36`: zizmor 1.30.1 fails without the
disable and passes with it, and zizmor 1.29.0 accepts the unknown audit id.

## Open questions

None. The decision is made upstream. This is cleanup timed to the sweep that brings it in.

## Recommended direction

At the sweep that takes the repo-tasks release containing `069f3d6`, run `inv configs.pull`, then
remove the four `# zizmor: ignore[self-repository]` comments and the reasoning block in `ci.yml`.
Then run `inv quality.workflow-check`: it should stay green, which proves the central disable
arrived. If it goes red, the pulled config predates the change.
