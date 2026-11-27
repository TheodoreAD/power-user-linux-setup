---
status: idea
updated: 2026-11-27
---

# Should this machine export DO_NOT_TRACK everywhere?

## Context

Asked for by the user 2026-11-08, while the ctlptl package landed: "leave a plan to think about
DO_NOT_TRACK", after the research below made Tilt's reporting look worrisome "especially if used in
an environment that works with corp code and ip".

What landed instead is narrower: `[packages.tilt]` seeds wmclient's choice file,
`~/.tilt-dev/analytics/user/choice.txt`, with `opt-out`. That covers Tilt and ctlptl in every
context — a GUI launch, a systemd unit, a non-zsh shell — which an environment variable does not.
`tilt analytics` reports `opt-out` on this machine. `inv ai.install-skills` already passes
`DO_NOT_TRACK=1` to the `skills` CLI, scoped to that one call (`tasks/ai.py`, `_SKILLS_ENV`).

What Tilt sends while it is on, read from a clone of `tilt-dev/tilt` at `master@1d760f6` and
`tilt-dev/wmclient` at `master@1839d03` (the version both Tilt and ctlptl pin), 2026-11-08:

- To `https://events.windmill.build/report`, overridable with `TILT_ANALYTICS_URL`.
- On every event: MD5 of `uname -a` as the user id (which includes the hostname), MD5 of the machine
  id, MD5 of the git `origin` URL, Tilt's version, the OS and the subcommand. The hashes are
  unsalted, so anyone able to guess a repository URL can confirm it was in use.
- `tiltfile.loaded`: a count of every Tiltfile builtin and argument used, whether the Tiltfile or
  any watched file changed, and the name of each loaded extension — an internal extension's name
  included.
- Build durations per kind, and a periodic `up.running` with resource counts, the cluster type
  (`kind`, `gke`, …), the container runtime and whether a local registry is configured.
- `tiltfile.custom.report`: whatever tags a Tiltfile passes to `experimental_analytics_report`.

[PITFALL: **the choice file does not win against a Tiltfile.** `EffectiveOpt` in
`internal/analytics/tilt_analytics.go` checks the environment first, then the Tiltfile, then the
user's file. A repository whose Tiltfile calls `analytics_settings(True)` turns reporting back on
for everyone running it, opt-out file or not, and can add `experimental_analytics_report` tags of
its own. Only `TILT_DISABLE_ANALYTICS`, `DO_NOT_TRACK` or `CI` (any non-empty value) beats that. So
on a machine running somebody else's Tiltfile — a client's or an employer's repository — the file is
not a guarantee, and an environment variable is the only one available.]

[PITFALL: **wmclient reads `~/.windmill` instead of `~/.tilt-dev` whenever `~/.windmill` exists**
(`pkg/dirs/dirs.go`, a legacy fallback). The seeded file would then be ignored without any error.
Neither directory existed here before 2026-11-08; `TILT_DEV_DIR` overrides both.]

ctlptl itself sends nothing unless the file says `opt-in`: its client is built without
`WithEnabled`, and wmclient's default is `optedIn()`. The upstream README's line that ctlptl "sends
anonymized usage statistics" describes behaviour the pinned code does not have.

## Open questions

[DECISION: **`TILT_DISABLE_ANALYTICS=1` landed 2026-11-08, asked for by the user**: "add
TILT_DISABLE_ANALYTICS to our setup". A `zshenv` field on `[packages.tilt]`, so it applies wherever
tilt is enabled, on every machine rather than only a corporate-tagged one — the Tiltfile override is
just as possible in a personal checkout of someone else's repo. It closes the Tiltfile override for
anything started from zsh; the choice file stays for every other launch. What remains open is the
broad variable.]

[NEEDS CLARIFICATION: export `DO_NOT_TRACK=1` machine-wide as well, or not? It changes what other
tools do — every CLI honouring the consoledonottrack convention goes quiet, which is the point, but
some tie unrelated behaviour to it — and like the Tilt variable it reaches only processes started
from zsh.]

[NEEDS CLARIFICATION: which other installed tools phone home by default and honour `DO_NOT_TRACK`.
Worth an inventory across `setup.toml` before deciding, since the variable's value scales with how
many tools read it. Left open deliberately by the user 2026-11-08, once the Tilt variable landed:
"leave the DO_NOT_TRACK inventory an open question for now". Not scheduled.]

## The inventory, 2026-11-27

Asked for by the user ("DO_NOT_TRACK inventory") and run by a research subagent over every Linux
package in `setup.toml`, from cloned sources where there is one (now in `$RESEARCH_HOME/repos/`) and
vendor pages where not. A sweep of every binary in `~/.local/bin`, Go's and Cargo's bin directories
and `/usr/bin/gh` found the string `DO_NOT_TRACK` in only four: gh, tilt, claude and herdr-app.

**Send by default, and honour `DO_NOT_TRACK`:**

- **gh** (2.101.0) — `gh config get telemetry` is `enabled` here, 1% sampled: a device id, OS,
  version, the detected coding agent, CI flags and command events. `GH_TELEMETRY=0` outranks
  `DO_NOT_TRACK`, so it is the firmer pin (cli/cli `internal/telemetry/telemetry.go`).
- **Claude Code** (2.1.332) — nothing in `setup.toml` or `~/.claude/settings.json` turns any of it
  off. Usage analytics, crash upload, Sentry error reports and feature-flag fetches. `DO_NOT_TRACK`
  stops analytics and crash upload but **not Sentry**, which only `DISABLE_ERROR_REPORTING` or
  `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` stops. Read from the installed binary.
- **tilt, herdr-app, the `skills` CLI** — already pinned off, each by its own switch.

**Send by default, and ignore `DO_NOT_TRACK`, so each needs its own switch:**

- **terraform** — HashiCorp Checkpoint on every run: version, OS and a persistent random UUID in
  `~/.terraform.d/checkpoint_signature`. `CHECKPOINT_DISABLE=1` (go-checkpoint `check.go`).
- **VS Code** — `telemetry.telemetryLevel` defaults on, and extensions have their own settings.
- **Chrome and Edge** — both have `"reporting_enabled": true` in their `Local State` here. Chrome
  has a managed policy, `MetricsReportingEnabled`; Edge on Linux has only its in-app setting.
- **JetBrains IDEs** — error reports on; usage statistics off in release builds.
- **glab, gcloud** (both disabled here) — glab defaults on (`GLAB_SEND_TELEMETRY=0`); gcloud is
  opt-in and its installer already passes `--usage-reporting=false`.

**Send nothing:** docker CE, go (counters stay local unless `go telemetry on`), k9s, wezterm,
flameshot, dprint and atuin (update checks only), every uv tool, rust, npm, helm, kind, kubectl,
act, dive, and the apt utilities. Claude Desktop's own Sentry and the JetBrains Toolbox app are
unknown.

[PITFALL: **`DO_NOT_TRACK` changes what Claude Code does, not only what it sends.** It turns off
feature-flag evaluation, so staged features never arrive and Remote Control cannot take a session
started remotely, and it is forwarded into every spawned and background session. Whether it can also
make auto mode unavailable was not established; test `DO_NOT_TRACK=1 claude` in auto mode before any
machine-wide export.]

[DECISION 2026-11-27: **no further pins for now.** Offered gh and Terraform, Claude Code's error
reports and analytics, and VS Code and Chrome, the user answered: _"none of these are problematic"_.
So the tools above stay at their defaults by choice. The switches remain listed here for when that
changes, and a new tool that phones home is still judged when it is added, as Tilt and Herdr were.]

## Recommended direction

Keep pinning per tool. A machine-wide `DO_NOT_TRACK` would newly silence only gh and part of Claude
Code, would leave Claude Code's error reports on, and would cost Claude Code behaviour this machine
uses. The gaps, each a tool-specific switch: `GH_TELEMETRY=0`, `CHECKPOINT_DISABLE=1`, and
`DISABLE_ERROR_REPORTING=1` for Claude Code (plus `DISABLE_TELEMETRY` only if losing staged features
is acceptable); then VS Code's `telemetry.telemetryLevel`, Chrome's policy, and the JetBrains
checkbox, which no environment variable reaches.
