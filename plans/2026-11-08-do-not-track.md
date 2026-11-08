---
status: idea
updated: 2026-11-08
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
many tools read it.]

## Recommended direction

With the Tilt-specific minimum in place, inventory the other installed tools first and decide on
`DO_NOT_TRACK` with that list in hand.
