---
status: in-progress
updated: 2026-08-25
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

[DECISION: **(a) — a plain machine-local file, with no export/import and no backup.** The pushback
above (that a file outside git weakens "every change is reproducible from a declared, re-runnable
command") was put to the user and rejected on principle, not on convenience:

> "each user has a duty to preserve his home if they want to. this is not a pulse responsibility.
> git is not for data on individual hosts. all the pulse behaviors are indeed stable, but around its
> defaults, it can't guarantee stability for each user's customizations."

That resolves the fork cleanly, and it is a sharper statement of the repo's scope than the original
framing: what PULSE guarantees is the stability of its **defaults**. A machine's divergence from
those defaults is that machine's own data, and backing up a home directory is the user's job. Option
(b) — hostname-keyed overrides in git — is dropped, not deferred; it would put per-host data in a
repo on the stated principle that repos are not for per-host data. The `export`/`import` round-trip
idea from (a) is dropped for the same reason: it exists only to smuggle the same data back into
somewhere shared.]

[NEEDS CLARIFICATION: File name and location — `~/.config/power-user-linux-setup/overrides.toml` as
its own file, versus new sections inside the existing `identity.toml`. Separate file is cleaner
(identity is secrets-adjacent and gets a wizard; this is not), but it adds a second thing to
remember. `local.toml`, `machine.toml`, `setup.local.toml` are the other candidate names.]

[NEEDS CLARIFICATION: What does `verify.all` do with an overridden package? Post-install
verification is convention-based and aborts on first failure; an override that enables a package on
one machine changes what "every package this run installed" means. Probably free (verification reads
the same `enabled_packages()`), but it should be checked rather than assumed.]

## What landed (2026-08-24)

The minimal version, built as a prerequisite for deploying
`plans/2026-08-24-chrome-ozone-x11-launcher-coverage.md`'s option B on this machine — there was no
way to deploy a package `setup.toml` ships disabled, and hand-copying the file is exactly what this
repo forbids.

- `util.OVERRIDES_PATH` = `~/.config/power-user-linux-setup/overrides.toml`, beside `identity.toml`
  in the existing machine-local namespace.
- `util.load_overrides()` — tolerant of a missing file (the common case), `@cache`d because
  `enabled_packages()` calls it many times per run, and it prints a warning for any package name the
  file mentions that `setup.toml` does not declare, since nothing else validates this file and a
  typo would otherwise be a silent no-op.
- `util.enabled_packages()` applies it: `setup.toml` → `overrides.toml` → `PULSE_EXCLUDE_TAGS`.
- Scope is **`enabled` only, on packages `setup.toml` already declares** — the v1 recommendation
  below, adopted as built. Every package _definition_ stays in git.
- `config/overrides.toml.example` and the rewritten `enabled` section of `docs/configuration.md`
  (which previously stated the opposite contract — "a permanent, environment-independent switch").
- Five tests in `tests/test_util.py`, including the precedence case where an excluded tag beats an
  override that asked for the package.

Both `google-chrome-x11` packages are enabled on this machine through it, and now appear in
`inv deploy.status` — which incidentally resolves the orphan described above _for enabled packages_.

## Remaining

[DEFERRED: `deploy.status` still cannot report a path for a package that is declared but disabled
here. The orphan case is narrower now (it needs a package that was deployed and later disabled) but
it has not gone away: `managed_paths()` still filters through `enabled_packages()`, so such a file
is invisible rather than reported as "declared, not managed here, but present on disk". Wants a
distinct status word rather than silent omission. Coordinate with
`plans/2026-08-22-deployed-config-drift-guard.md`, which owns that registry.]

[DEFERRED: Whether an override may carry anything beyond `enabled` — `tags` is the only other field
`enabled_packages()` consults. Not needed by any real use case yet; recorded so the question is not
re-derived. Widening is additive, so there is no cost to waiting.]

[DEFERRED: Whether an override may _define_ a package absent from `setup.toml`. Currently it cannot,
and `load_overrides()` warns on the attempt. The argument against allowing it stands — it would make
the home file a place where undeclared, unreviewed installs accumulate — but it was decided by
implementation rather than deliberately, so it is worth one look before it becomes load-bearing.]

[UNVERIFIED: What `verify.all` does with an overridden package. It reads the same
`enabled_packages()`, so it should be free, but this was reasoned rather than run — the next full
`inv setup` on this machine is what would actually prove it.]

## Inherited from the retired drift-guard plan (2026-08-25)

`plans/2026-08-22-deployed-config-drift-guard.md` landed and was retired into
`contributing/deploy.md`; the registry it built is what the orphan item above coordinates with, so
its two open items live here now.

[DEFERRED: `util.ensure_block` and `util.write_claude_settings` targets have no drift classification
of their own — a marker-delimited block and a merged JSON key each need their own notion of "dirty"
that the whole-file classifier doesn't model. `inv deploy.status --path` at least _detects_ a
block-owned file (any file containing a `PULSE::` marker) and says PULSE owns only the marked
regions; `write_claude_settings` targets remain entirely undetected. Wants a registry entry per
ownership model so "is this path PULSE-managed?" has one answer for all three, before any
classification is designed.]

[DEFERRED: the agent that dirties a deployed file still learns nothing _at edit time_ — only whoever
next runs a PULSE task does. Accepted deliberately (the actual harm, silent loss, is closed), with a
condition: if deployed-file drift keeps recurring now that the writer can't destroy it, revisit a
real-time `PostToolUse` hook _then_, with transcript evidence rather than on prediction. The hook
mechanics are recorded in `contributing/deploy.md` so nobody re-researches them.]
