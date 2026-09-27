---
status: idea
updated: 2026-09-27
source_repo: github.com-personal/agent-skills
source_session: a953b16f-c02c-45d9-99e8-21a7277c781d.jsonl
source_moment: 2026-09-27
source_plan: plans/2026-09-27-package-health-release-files.md
---

# Install rule uses package health

## Context

The home instructions section "Installing a tool on this machine" lives in
`config/agents-md/research.md:131-147` and is deployed to `~/.agents/AGENTS.md` and
`~/.claude/CLAUDE.md`. It tells every session to judge a PyPI wrapper "from its own PyPI file list
(`curl -s https://pypi.org/pypi/<name>/json`)". It also says "maintained" means the wrapper tracks
upstream, "checked against the upstream changelog".

As of agent-skills `2d446af` (pushed 2026-09-27), `research-library`'s `package_health.py` answers
every part of that by command:

- **`pypi <name>`**: the latest stable release's files, meaning platform-tagged wheels versus
  sdist-only, sizes and release count, plus floors (requires-python, and the glibc floor from the
  manylinux tag) checked against this machine.
- **`--upstream <owner/repo>`**: whether the wrapper tracks upstream's latest stable release, and
  the lag in days.
- **`github <owner/repo>`**: a tool shipped only as release binaries. Maintenance, release cadence,
  and the Linux x86_64 assets with their checksum and signature files. This is the `archive` and
  `deb-github` route.
- **`npm <name>`**: resolves the platform packages and flags install-time scripts. This is the
  `nvm`/npm-global route.
- **`apt <name>`**: main versus universe, origin, lag behind upstream, and which Ubuntu and Debian
  releases carry which version. This is the `apt` and `apt-repo` route.

The rule is loaded in every session, while the skill only helps once something makes an agent open
it. So today the always-loaded text steers agents to the hand-rolled fetch the script replaced, and
it covers only the PyPI route of the install methods `setup.toml` actually uses.

## Evidence

- Transcript `a953b16f-c02c-45d9-99e8-21a7277c781d.jsonl` (agent-skills), 2026-09-27. A research
  subagent was briefed, following this rule, to `curl` PyPI JSON for wrapper file lists, and had to
  be redirected mid-run: "don't hand-roll PyPI fetches with curl. For any PyPI package, run …
  package_health.py". That redirection is what produced the agent-skills plan cited as
  `source_plan`.
- The user's decision on 2026-09-27, after the context was laid out, was "File it (Rec.)".

## Open questions

[NEEDS CLARIFICATION: how much of the per-source command list belongs in the rule, rather than
behind a pointer to the skill. A command per route keeps the rule actionable at the moment it fires.
A single "run `package_health.py <source> …`; see the research-library skill" line stays short and
can't drift from the script's CLI. The rule's own admission criteria are in
`contributing/global-agents-md.md`; check against them.]

## Recommended direction

1. Edit `config/agents-md/research.md` in place:
   - Replace the `curl -s https://pypi.org/pypi/<name>/json` parenthetical with
     `python3 ~/.agents/skills/research-library/scripts/package_health.py pypi <name> --upstream
     <owner/repo>`.
   - Replace "checked against the upstream changelog" with a reference to what `--upstream` reports.
   - Add one sentence naming `github`, `npm` and `apt` for tools that don't come through PyPI.
   - Keep the `hadolint-py` and `lychee-bin` cases: they are the evidence the rule survives on.
2. Add `[needs agent-skills]` to the section heading, since it now depends on the skill being
   installed, as other rules already do.
3. Run the repo gate, then `inv deploy.all --name agents-md`, then confirm the deployed
   `~/.agents/AGENTS.md` and `~/.claude/CLAUDE.md` carry the new text.

## Verification

- The deployed files contain `package_health.py pypi` and no `pypi.org/pypi` curl.
- In a fresh session, asking "should I install X via its PyPI wrapper?" leads to a
  `package_health.py` call, not a `curl`. That is the repro from the Evidence section, checked where
  it happened.
