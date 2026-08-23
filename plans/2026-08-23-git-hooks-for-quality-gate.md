---
status: idea
updated: 2026-08-23
depends_on: [repo-tasks, scaffoldapy]
---

# Git hooks for the quality gate — considered, deliberately not adopted (for now)

## Context

CI-failure investigation across `power-user-linux-setup`/`repo-tasks`/`scaffoldapy` (2026-08-23)
found that after the one-off causes were fixed (missing quality tools in CI, exit 127; Pages-deploy
strict link-check on two broken anchors in `docs/dev-container.md`), every remaining recurring CI
failure had a single cause: **docs-only commits pushed without running the quality gate**, caught by
`dprint check` (exit 20). Always markdown — `plans/*.md`, `skills/plan-docs/SKILL.md`,
`config/global-AGENTS.md` — and always pure line-wrap reflows `dprint fmt` would auto-fix. Agent
sessions treat "just markdown" commits as exempt from `inv quality.precommit`, but dprint formats
markdown, so those are exactly the commits that fail. Concrete run tally at time of writing: 7
failed CI runs in this repo (11:47–13:47), 2 in repo-tasks (09:31–09:33), 2 in scaffoldapy (09:10,
12:13), all on 2026-08-23, all this failure shape.

A git-hook layer was researched as mechanical enforcement. Captured here so the research isn't lost;
the decision was to **not** adopt it now and handle the problem at skill level instead (see
"Decision context" below).

### Researched hook design (if ever adopted)

- Implementation lives in `repo-tasks` (a task writing the hook, e.g. wired into `dev_env.setup`'s
  pre-list), per the family convention: one mandatory identical composite, consumed unmodified by
  every consumer repo; `scaffoldapy` stamps it for new repos at generation time.
- Hook runs a **fast check subset** —
  `lint_check + format_check + shell_check +
  shell_format_check`, no pytest/basedpyright (~2s;
  full `quality.check` is too slow per commit/push — scaffoldapy's e2e tier alone is ~1min). That
  subset would have caught 100% of the observed failures. Likely wants a named composite in
  `repo_tasks.quality` (e.g. `quality.gate`) so hook and humans invoke the same task.
- **Check-only, never auto-fix**: fail with "run `inv quality.precommit`, retry" rather than
  mutating files mid-commit/push — auto-mutation conflicts with the deliberate-regeneration rule
  (`~/AGENTS.md`) and desyncs staged content from the worktree.
- **Degrade gracefully** when tools are absent (zero-install/bootstrap path): warn and pass, CI
  backstops — same contract as `shell_check`'s no-op on a shell-less repo.
- Git hook, not a Claude Code `PreToolUse` hook: tool-agnostic (covers every agent harness,
  concurrent sessions, and a human at a terminal), matching the `AGENTS.md`-over-`CLAUDE.md`
  cross-tool philosophy. A harness-level hook would be Claude-only and fires on every Bash call with
  the filtering pushed into the hook script.
- Rejected alternatives from the same research: CI auto-fix bot commit (violates
  deliberate-regeneration, adds noise commits, races frequent multi-session pushes); relaxing dprint
  markdown `textWrap` to `maintain` (turns off the formatter to avoid running it — wrapping
  consistency across agent-written docs is the point).

### Decision context — why not adopted now

User position (2026-08-23), the actual gate on this plan, not a detail:

- **Skills are being made the mainstay of directing agents.** The preference is that agents _know_
  what to run, not that things run without the agents' knowledge. Failing quality scripts in CI are
  a good thing — visible, attributable — versus enforcement that fires behind the agent's back.
- **Same standard for agents as for developers.** The user has always been against companies
  imposing git pre-commit hooks on developers, and sees no reason to treat an agent differently from
  a dev.
- On hook placement, if ever revisited: the user leans **pre-commit over pre-push** as the safer
  point, and would usually want tests run before committing too — with the caveat that a small
  change may not always warrant the full battery.

The skill-level handling that was adopted instead: `plan-docs` and `session-harvest` (this repo's
`skills/`) now instruct running the repo's quality gate before committing any file they produce,
closing the "docs are exempt" gap at the moment the failing commits actually happen.

## Open questions

- [NEEDS CLARIFICATION: revisit trigger — what observation would reopen this? e.g. dprint-shaped CI
  failures recurring at some rate after the skill-level fix has been deployed for a while, or a
  non-Claude agent harness (which never loads these skills) starting to commit in these repos.]
- [NEEDS CLARIFICATION: if revisited, pre-commit vs pre-push — user leans pre-commit as safer; the
  research above leaned pre-push (mirrors CI's per-push-tip granularity, runs once per push under
  the granular-commits practice). Also whether tests belong in the hook's gate: "usually run tests
  before committing, but a small change may not warrant everything" suggests a fast subset with an
  opt-in full tier, undesigned.]
- [NEEDS CLARIFICATION: even if hooks stay rejected as enforcement, is an _opt-in, self-installed_
  hook (a dev/agent choosing to install it for themselves, via a repo-tasks task that is never
  auto-wired into setup) compatible with the no-imposed-hooks philosophy, or not worth the
  machinery?]

## Recommended direction

Leave unadopted. Let the skill-level fix run for a while; check CI failure shape across the three
repos afterwards (`gh run list` per repo, filter non-success, look for dprint exit-20 runs). If the
docs-commit failure shape recurs despite skills, reopen this plan with the design above as the
starting point — pre-commit placement, check-only, fast subset, degrade-gracefully, implemented in
repo-tasks and stamped by scaffoldapy.
