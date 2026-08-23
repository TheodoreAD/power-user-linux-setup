---
status: idea
updated: 2026-08-24
---

# Machine-local overrides for `setup.toml`

## Context

**Origin.** A live NVIDIA+Wayland DRM bug on 2026-08-24 (Netflix plays audio, renders black — see
`plans/2026-08-24-chrome-ozone-x11-launcher-coverage.md`). The workaround already exists in the repo
as `[packages.google-chrome-x11]`, deliberately shipped `enabled = false` because it is specific to
this machine's GPU and session type, not something every consumer of this repo should get. The
user's framing: _"this is just for my machine, probably not a problem on everyone's machine, so the
default is off, but probably on in the toml in the home config dir."_

That mechanism does not exist. Today `enabled` has exactly one value per package, baked into a
git-tracked file shared by every machine that clones the repo.

### Grounding facts (verified 2026-08-24, do not re-derive)

- `util.load_config()` (`tasks/util.py:215`) reads **only** the repo's `setup.toml`. There is no
  overlay, no merge, no second source.
- `docs/configuration.md:158` states the current contract explicitly: `enabled = false` is "a
  permanent, environment-independent switch baked into `setup.toml`." Environment variation is
  `PULSE_EXCLUDE_TAGS`'s job, and only 7 tags gate anything.
- `~/.config/power-user-linux-setup/` (`util.PULSE_CONFIG_DIR`) is the existing machine-local,
  out-of-repo namespace, but everything in it is _identity_ or _generated manifest_:
  `identity.toml`, `ai.py`'s static-perms manifest, `allowlist.py`'s applied manifest. Nothing there
  influences which packages exist.
- On this machine the directory does not exist at all right now — `identity.toml` has never been
  created here.

### The second, sharper problem: `enabled = false` hides a deployed file

`deploy.managed_paths()` (`tasks/deploy.py:201`) builds the registry from `util.enabled_packages()`,
which filters on `enabled` **and** tags. So a disabled package contributes no managed path.

Confirmed live: `~/.local/share/applications/google-chrome.desktop` exists on disk with the x11
flag, is declared in `setup.toml` as `[packages.google-chrome-x11]`, and does **not** appear in
`inv deploy.status` output. It is an orphan — a file this repo describes but does not track, so
`deploy.status` cannot say whether it drifted, and the drift guard
(`plans/2026-08-22-deployed-config-drift-guard.md`) will never see it.

That is worse than a missing feature. It means "disabled" currently conflates two different things:

1. _PULSE does not manage this on this machine_ (correct for `glab`, `citrix-workspace`).
2. _PULSE manages this, but only somewhere else_ — while the file is sitting in `~` right now.

Whatever shape the override takes, it has to fix (2), not just make the package installable.

## Open questions

[NEEDS CLARIFICATION: What can an override change? The minimal version is `enabled` only — a
per-machine allow/deny list of package names, nothing more. The maximal version is a full deep-merge
of arbitrary `[packages.*]` keys, which turns the home file into a second config language and makes
`setup.toml` no longer readable as the truth. A middle option: `enabled` plus `tags`, since those
are the only two fields `enabled_packages()` consults.]

[NEEDS CLARIFICATION: Can an override _define_ a package that does not exist in `setup.toml` at all,
or only flip ones that do? Defining new ones makes the home file a place where undeclared,
unreviewed installs accumulate — the exact failure this repo exists to prevent. Flipping only
existing entries keeps every package definition in git, which seems clearly right, but should be
stated as a decision rather than assumed.]

[NEEDS CLARIFICATION: Precedence against `PULSE_EXCLUDE_TAGS`. If the home file enables
`google-chrome-x11` and the environment excludes `gui`, who wins? Proposed: the environment wins,
because tags describe _capability_ (no display server means the package genuinely cannot work) while
the override describes _intent_. Needs stating either way, since the container/WSL profiles depend
on tags being authoritative.]

[NEEDS CLARIFICATION: This cuts against the repo's founding principle — `CLAUDE.md`: "every change
this machine has is reproducible from a declared, re-runnable command." A file outside git is not
reproducible; restore this machine from a fresh clone and the override is gone, silently, with the
Netflix bug back. Two ways out, and they are genuinely different designs:

- **(a) Machine-local file, accept the gap.** Add `inv <something>.export` /`import` so the override
  set can be round-tripped, and have `deploy.status` / `verify.all` name every override in effect so
  it is at least _visible_ rather than reproducible.
- **(b) Keep it in git, key it on machine identity.** `[packages.google-chrome-x11] enabled = false`
  plus `enabled_on_hosts = ["<hostname>"]`, or a `[machines.<name>]` section listing overrides.
  Fully reproducible, reviewable, and diffable; costs a repo edit per machine and leaks hostnames
  into a public repo.

The user asked for (a). (b) is worth one round of pushback before (a) is built, because the whole
argument for this repo's design is the one (a) weakens.]

[NEEDS CLARIFICATION: File name and location — `~/.config/power-user-linux-setup/overrides.toml` as
its own file, versus new sections inside the existing `identity.toml`. Separate file is cleaner
(identity is secrets-adjacent and gets a wizard; this is not), but it adds a second thing to
remember. `local.toml`, `machine.toml`, `setup.local.toml` are the other candidate names.]

[NEEDS CLARIFICATION: What does `verify.all` do with an overridden package? Post-install
verification is convention-based and aborts on first failure; an override that enables a package on
one machine changes what "every package this run installed" means. Probably free (verification reads
the same `enabled_packages()`), but it should be checked rather than assumed.]

## Recommended direction

1. **Settle the git-vs-home question first** (the fourth clarification above). Everything else is
   downstream of it, and the answer changes what gets built, not just where a file lives.
2. **Scope the override to `enabled` only**, at least for v1. It is the entire motivating use case,
   it is the field `enabled_packages()` actually reads, and it keeps every package _definition_ in
   git where it can be reviewed. Widening later is additive; narrowing later is a break.
3. **Fix the orphan problem in the same pass**, independently of the override design.
   `deploy.status` should be able to report a path that PULSE declares but has disabled — as a
   distinct state ("declared, not managed here, but present on disk"), not by silently omitting it.
   This is a small change to `managed_paths()`'s filter plus a new status word, and it is worth
   doing even if the override layer is never built. Coordinate with
   `plans/2026-08-22-deployed-config-drift-guard.md`, which owns that registry.
4. Load order, once decided: `setup.toml` → machine-local overrides → `PULSE_EXCLUDE_TAGS`, with the
   environment last so capability always beats intent.
