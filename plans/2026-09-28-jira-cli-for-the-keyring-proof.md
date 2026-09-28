---
status: idea
updated: 2026-09-28
source_repo: github.com-personal/agent-skills
source_session: 683fcc89-a606-4be2-b9e4-d3e7b357d169.jsonl
source_moment: 2026-09-28T11:40:00Z
source_plan: plans/2026-09-28-tracker-bound-epics-and-stories.md
---

# Install jira-cli so a keyring-auth proof can run

## Context

`agent-skills` is designing a skill that drafts Jira epics and stories as plans and exports them
through a CLI or an MCP server. Before choosing the transport, the user wants auth proven: a Jira
Cloud API token held in the OS keyring by Python `keyring`, which is already installed here as
`[packages.python-keyring]`, and read by `jira-cli` (`ankitpokhrel/jira-cli`). The machine does not
have `jira-cli`, and a tool is installed only through `setup.toml`, never by hand — so this is filed
here rather than done from `agent-skills`.

What the proof needs from this repo is one package entry. The proof itself runs from the
`agent-skills` session, and its steps are in that repo's plan named in `source_plan`.

## Evidence

In session `683fcc89-a606-4be2-b9e4-d3e7b357d169.jsonl`, the user answered "we need to try proving
keyring auth." Asked how `jira-cli` should get onto the machine, they chose the answer labelled
"File the plan" — add a `[packages.jira-cli]` entry here, installed by a session in this repo.

`package_health.py github ankitpokhrel/jira-cli`, run 2026-09-28:

- latest stable **v1.7.0, 2025-08-31**, 393 days ago; 15 stable releases, none in the last year;
  last push 2026-09-22; bus factor 1; 5,995 stars; MIT.
- Linux x86_64 asset: `jira_1.7.0_linux_x86_64.tar.gz`, 7.3 MB, with a `checksums.txt` and no
  signature.

## Open questions

[NEEDS CLARIFICATION: **`archive` or a pinned `tag`.** `[packages.atuin]` resolves the latest
release through `version_cmd` with a `download_url` template; `[packages.flameshot]` pins `tag` and
`asset`. With no release in 393 days, a pin costs nothing and makes the install reproducible. The
checksum is one line of a `checksums.txt` rather than a per-asset `.sha256`, so check which form the
`archive` method's `checksum_url` accepts before writing the entry.]

## Recommended direction

Add `[packages.jira-cli]` with `method = "archive"`, `bin_pick = "jira"`, the v1.7.0 Linux x86_64
tarball and its checksum, and `check_cmd = "jira"`. Nothing else: **no token, no `jira init`, no
config file.** The token goes into the keyring by the user's own hand during the proof, and
`jira init` writes a per-account config that belongs to that step, not to machine setup.

Verify with `jira version` after `inv` installs it.
