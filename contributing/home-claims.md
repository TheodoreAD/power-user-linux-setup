# The home-directory claims registry — `tasks/home.py`

Design rationale behind `inv home.list-claims`, the read-only inventory of every path in `~` this
repo has a claim on. `contributing/deploy.md` covers the whole-file writer this builds on;
`docs/configuration.md` is the user-facing page.

## Why a second registry, and why not inside `deploy.py`

`deploy.py`'s own docstring scopes it precisely: "One way to write a file into the home directory."
That is an accurate description of what it owns, and the reason it cannot own this.
`deploy.status --path ~/.zshrc` had to grow a special case (`_has_pulse_block`) precisely because
the honest answer for a path `deploy.py` does not write is not "not deployed by PULSE" — that
sentence was already found "confidently wrong on the most-likely-asked path" once. Every writer
outside `deploy.py` has the same problem, and bolting each one into a module whose contract is
prove-what-you-wrote would make that contract mean two things.

So: `tasks/home.py` owns the registry of **claims**, `deploy.py` keeps owning the **whole-file
writer**, and the whole-file third of the registry is derived from `deploy.managed_paths()` rather
than restated. A test asserts that equality, because a second hand-maintained list of the same paths
is the failure this repo has already been bitten by elsewhere.

The task name follows the repo's conventions: `list-claims` is verb-first, and `<ns>.list-*` is one
of the shapes the machine's Claude Code allowlist auto-approves on the strength of the convention
that such a task inspects and never mutates. This one must therefore stay read-only forever — no
repair path, no prompt, no shelling out to `gsettings`.

## The registry is a list, not a path-keyed mapping

`deploy.managed_paths()` can be a `dict[Path, Managed]` because whole-file ownership is exclusive:
two packages deploying the same path would be a bug. That stops being true the moment blocks and key
surgery are in scope. `~/.zshrc` on this machine carries:

- one `PULSE::<package>` block per package declaring a `zshrc` snippet in `setup.toml`, each
  independently owned and independently rewritable;
- `zsh.configure-omz`'s regex replacement of `ZSH_THEME=` and `plugins=(...)`, which is **outside
  every marker** and is a different writer with a different notion of a conflict.

Collapsing those to one row per file would hide exactly the thing an inventory exists to show.

## Three axes, and why the tier axis reports rather than assigns

`Writer` says how the bytes get there and therefore what "drift" could even mean. `Authority` is
`deploy.py`'s existing `MANAGED`/`SEEDED` split generalized to four values. `Tier` is the new one.

**Tier reports where a claim's content lives today — it is not a recommendation**, and
`config/p10k.zsh` is the case that settled why. It is 1103 lines of one person's prompt, generated
by p10k's own wizard: the most personal-looking file in the repo, and the one
`plans/2026-08-29-dotfiles-repo-config-lifecycle.md` named first as a peculiarity that should not
ship publicly. Its owner then ruled it a deliberate public default (2026-08-30) — the vetted font,
icons and theme are the product, and leaving the prompt to a wizard was the odd manual step out.

An inventory that had inferred `personal` from the shape of the content would have been wrong,
confidently, about the single file the whole exercise was pointed at. So `personal` and `unassigned`
are part of the vocabulary and carry **zero** claims. That zero is the measurement: everything PULSE
writes is a public default, machine-bound, secret, or regenerable — nothing is
personal-but-homeless.

## The number this was built to produce

Re-measured on this machine, 2026-09-07 (the 2026-08-30 figures are in brackets):

| writer                  |    claims | what it is                                             |
| ----------------------- | --------: | ------------------------------------------------------ |
| `install`               |   42 (36) | trees and binaries an installer puts under `~`         |
| `block`                 |   25 (24) | `util.ensure_block` marker regions                     |
| `imperative`            |   23 (23) | `gsettings`/`dconf` — no file at any path              |
| `whole-file`            |   12 (11) | `deploy.py`, from a `setup.toml` declaration           |
| `mirror`                |     5 (—) | copies of a deployed file, at paths other tools read   |
| `whole-file-undeclared` |     4 (3) | `deploy.py`, destination decided at run time           |
| `key`                   |     3 (3) | regex surgery on one key of a file an application owns |
| `merge`                 |     3 (2) | structured merge into co-owned JSON                    |
| `external`              |     2 (1) | skills directories, written by the `skills` CLI        |
| `generated`             |     1 (1) | composed by a task, with no source to compare against  |
| `directory`             |     1 (—) | created by a task, filled by the user or another tool  |
| **total**               | 121 (109) |                                                        |

**There is no `symlink` row any more: this repo creates no symlinks under `~`.** It was 6 (5) until
2026-09-07, when the five instruction destinations became `mirror` copies and the sixth,
`~/.claude/skills`, turned out to be something the `skills` CLI writes per skill on its own — so it
became a second `external` claim. Neither change moved the total, which is the useful check that a
reclassification is a reclassification.

Every figure here is read from `inv home.list-claims --json` rather than adjusted by hand. The first
attempt at this edit put 6 in the `mirror` row from a `rg -c` that had also matched a line of prose,
and the row was wrong in a committed doc for one commit.

By tier: 75 `public`, 41 `derived`, 4 `machine`, 1 `secret`; zero `personal`. The `secret` count is
1 rather than 2 because this machine kept a real keyring — the plaintext credential store below is
claimed only where `--keyring-fallback` was chosen.

**A whole-file-only lifecycle would reach 16 of the 80 non-derived claims — 20%** (14 of 74, 18%, in
August). That is the number `plans/2026-08-29-dotfiles-repo-config-lifecycle.md` step 1 exists to
produce, and it is what the rest of that plan has to be sized against. (The first measurement,
before step 3 folded the ad-hoc writers in, was 15 of 74 with only 10 classifiable; the reach barely
moved because those files were already whole files — what changed is that all of them now carry a
manifest entry and a diff.)

The twelve claims added since August are what a re-measurement is for: eleven came from features
landing beside this registry rather than from a change to it, and the twelfth is the `directory`
writer below, which the audit found. A number in a doc that nothing re-derives goes stale silently,
which is the same failure this registry exists to prevent one directory up.

`derived` is excluded from that denominator deliberately: an installed Go toolchain or an `nvm`
directory can never be the subject of a config lifecycle, because its content is upstream's and
regenerating it is the repair. Including them would flatter every coverage number by a third.

## What the inventory found that nothing else had recorded

Building it turned up five claims nobody had written down, each a real ownership model the
`deploy.py` rework did not absorb:

- **Five whole files were written by a task of their own, outside `deploy.py`.** `~/.p10k.zsh`
  (skip-if-exists, no redeploy path at all), the two PyCharm font files (unconditional overwrite
  into a **glob-discovered** JetBrains directory), the systemd unit (content an f-string in
  `tasks/proxy.py`, so no repo-side source), and `identity.toml`. These are exactly the "too many
  ways to write into `~`" that `contributing/deploy.md` set out to unify — the unification landed
  for three writers and stopped. All five have since been resolved; see "Folding the ad-hoc writers
  in" below.
- **`key` is a distinct writer, not a variant of `merge`.** Merging into JSON parses the document
  and replaces a value; `zsh.configure-omz`, `screenshot.enable` and `chrome.fix-launchers` do regex
  substitution on text some other program owns. The failure modes differ: a merge can only lose the
  key it writes, a regex can rewrite the wrong line.
- **`mirror` is its own claim, and since 2026-09-07 it is the writer with real drift.** The
  instruction-file destinations were symlinks until then and are now byte-for-byte copies —
  `deploy.py`'s "Mirrored destinations" header carries the three reasons, the short version being
  that Claude Code ignores a symlinked `~/.claude/CLAUDE.md` in Cowork sessions and Windows has no
  admin-less way to link a file at all. A link could only be right or wrong; a copy can be _stale_,
  so `ensure_mirror` records every one in the deploy manifest and `verify` compares content rather
  than looking for a link. `deploy.lookup()` still resolves through a link, which now serves only a
  machine that has not re-deployed since the change.
- **The `~/.claude/skills` symlink was ours, unnecessary, and hiding the evidence that it was.**
  PULSE made that directory a link to `~/.agents/skills` because Claude Code does not read the
  cross-tool path natively and a 2026-08-27 measurement said the `skills` CLI announced a per-agent
  symlink it did not create. The measurement was against CLI v1.5.10; the reading that mattered was
  wrong at any version. `claude-code` is **not** one of that CLI's universal agents — its
  `skillsDir` is `.claude/skills`, and `isUniversalAgent` tests for `.agents/skills` — so the early
  return that skips per-agent links never applied to it.

  The link was also self-concealing: the CLI resolves parent symlinks before deciding whether a
  skill is installed, so with the directory linked, `<link>/<name>` and `.agents/skills/<name>` are
  the same file and it correctly skipped. **The arrangement could not observe what the tool would do
  without it.** Removed and re-measured 2026-09-07 on CLI v1.5.24: 14 skills, 14 per-skill symlinks
  created at `~/.claude/skills/<name>` → `../../.agents/skills/<name>`, and this session's own skill
  listing unchanged. On Windows the same code path makes a junction, which needs no privilege, and
  falls back to copying.

  The general lesson is the one worth keeping: **a whole-directory link was our invention, and no
  vendor documents it** — Claude Code's docs say a `<skill-name>` _entry_ may be a symlink, never
  the directory. Being the outlier is what made Windows look hard, and the fix was to stop doing
  something rather than to port it.
- **Every skill on this machine is invisible to `deploy.py`, and since 2026-09-07 that is true by
  construction rather than by circumstance.** It used to hold only because this repo declared no
  `source = "local"` skill; `deploy._skill_entries` would have registered one if it had. Both that
  function and `Mechanism.SKILL` are now gone, because the `skills` CLI installs local skills too —
  and a registry entry for a path nothing writes is worse than no entry, since `deploy.status` would
  report it MISSING forever with no command able to fix it. The whole of `~/.agents/skills/` is
  declared in `setup.toml`, written by that CLI, and claimed here as `external`.
- **The machine tier already exists, at four claims.** The `certs` and `proxy` blocks in
  `~/.zshenv`, the `ssh` block in `~/.ssh/config`, and `overrides.toml`. All four are derived from
  `identity.toml` or hand-written, and all four are genuinely true of this box only — which is
  evidence for the layering the plan proposes, from before it is built.

## Folding the ad-hoc writers in

All five now go through `deploy.py`, so each has a manifest entry, a diff before it is overwritten,
and the never-destroy-what-we-can't-prove-we-wrote rule — or is correctly outside it:

- **`~/.p10k.zsh`** is declared `config_files` on `[packages.powerlevel10k]`. SEEDED is right: the
  prompt config is yours the moment p10k's own `configure` wizard rewrites it.
- **The systemd unit** is `config/pulse-proxy.service`, deployed by `inv proxy.fix`/`install`
  through a `Managed` built in `tasks/proxy.py`. The file could become static because systemd's own
  `%h` specifier expands the home directory, which is what the f-string was doing by hand.
- **The PyCharm font files** are deployed by `inv ide.configure-pycharm` through `Managed` objects
  resolved against whichever PyCharm is installed. With no PyCharm on the machine there are no
  claims, which beats two rows reporting a file absent that was never going to exist.
- **`identity.toml`** stays outside, and that is the right answer rather than a gap: it is composed
  by a wizard from answers, so there is no source to diff it against, and it is the one claim on the
  surface whose content must reach no repo at all. It gets its own writer value, `generated`.

**A sixth turned up on 2026-09-07, in the same feature as the systemd unit.**
`~/.config/power-user-linux-setup/proxy.env` — the file that pins the keyring backend for the daemon
— was a bare `write_text` of an f-string: no repo-side source, no manifest entry, no diff, no
redeploy path. Exactly the shape `_write_unit` had before this work and describes in its own
docstring, missed because one line of generated content does not look like a deployment. It is now
`config/pulse-proxy.env`, deployed through the one writer, and undeclared for the same reason the
unit beside it is. Its content could be static because the backend name never varied — and a unit
test now asserts the deployed file names the same backend `tasks/proxy.py` probes with, since a
drift there is silent in precisely the way the file-path drift already tested for is: px finds no
credential and answers 407 as though the password were wrong.

The lesson worth keeping is the detection one. Neither `deploy.status` nor this registry could have
found it — a path nothing claims is a path nothing looks for. It was found by asking what the
_feature_ writes into the home directory and comparing that list against the registry, which is a
question to ask of each new feature rather than of the registry.

### Why two of those are _not_ declared in `setup.toml`

This is the constraint the fold-in ran into, and it is the reason the `whole-file-undeclared` writer
exists at all: **every declared destination is one `inv verify.all` requires to exist** — it runs at
the end of `inv setup`'s packages phase and fails on `ABSENT` for MANAGED and SEEDED alike. The
systemd unit is written only on a machine that configures a corporate proxy; the PyCharm files need
a destination discovered by glob, which a `[packages.*]` mapping's literal `dst` cannot express.
Declaring either would fail `inv setup` on every machine that legitimately lacks it.

`Mechanism.MANAGED_FILE` was added for both: `wrapper-script` was the only MANAGED whole-file shape
and it chmods 0755, which is wrong for a systemd unit and for an XML options file, so a PULSE-owned
**non-executable** file had no way to be expressed. A matching `managed_files` setup.toml field was
written and then removed — with both users undeclarable, it had no consumer, and a field nothing
declares is a second way to spell something.

### The latent bug this surfaced

`config_files` is documented as method-agnostic, and it was not: the applier was `apt.py`'s private
helper, called only from the apt and deb install paths. An `archive` or `git-clone` package's
declared config — `~/.config/wezterm/wezterm.lua`, and `~/.p10k.zsh` once declared — was therefore
never written during `inv setup` at all. It waited for an `inv deploy.all` a fresh machine has no
reason to run, while `verify.all` at the end of that same phase demanded it exist. The helper moved
to `deploy.apply_config_files` and `tools.install` now calls it after every installer, which is what
makes declaring `~/.p10k.zsh` safe.

## The eleventh writer: a directory PULSE creates and does not fill

Added 2026-09-07, by running the audit the section above describes rather than by extending the
registry for its own sake. Two paths came out of it, and neither fits any existing writer:

- `~/Pictures/Screenshots`, created by `inv screenshot.enable` beside the `flameshot.ini` savePath
  it already claims.
- `~/projects/<name>`, one per `[[git_profiles]]` entry, created by `inv git.configure` — the
  directories the user's own work lives in, and the most consequential thing this repo creates in a
  home directory.

`INSTALL` was the near miss, and taking it would have been wrong in a way that matters: its whole
note is _content is upstream's, so a divergence is not drift but a version_, and saying that about
somebody's projects directory is false. `DIRECTORY` says the true thing instead — **PULSE runs
`mkdir -p` and owns nothing inside**. Nothing can drift because nothing is written; the claim is the
existence of the container. Authority is `user` for both.

Tier reads the **path** here, because there is no content to place: the screenshots directory is a
constant in this public repo, and a projects directory is named in `identity.toml` and true of this
machine only, which is where every other identity-derived claim already sits. That keeps
`unassigned`'s zero intact, and its zero still means what "The number this was built to produce"
says it means — no _config_ is personal-but-homeless.

Two behaviours worth knowing, both of which have tests: a profile `directory` may be an absolute
path anywhere, so it gets the same `_under_home` test an install target does; and the git claims are
gated on `identity.toml` **existing** rather than on `load_identity()`, which raises. The machine
most likely to ask what PULSE would put in its home directory is the one that has not run
`inv identity.init` yet.

`~/.claude/settings.json.bak` came out of the same audit and is deliberately **not** a row. It is a
copy of the claim above it, written and overwritten by the same function, with no independent
content and no state of its own to report — so it is named in that claim's note instead, because a
backup nobody knows about is one nobody can use.

## The one credential file, and why it is claimed by a different writer

`~/.local/share/python_keyring/keyring_pass.cfg` holds a base64-encoded corporate proxy password in
a 0600 file, readable by anything running as this user. PULSE never writes it — the `keyring`
library does, inside Px's process and inside PULSE's one-shot credential writer — so its writer is
`external`, the same value the `skills` CLI's output carries, and its authority is `user` rather
than `pulse`. Its tier is `secret`, the only one besides `identity.toml`.

It is claimed **only when `proxy.env` exists**, which is the record that `--keyring-fallback` was
actually chosen. That follows the PyCharm rule above: a row for a file that was never going to exist
reads as something missing rather than as something not applicable, and on every machine that kept a
real keyring this file is the latter.

## Deliberately not claimed

- **`~/.local/state/power-user-linux-setup/windows-root-extras.pem`** — the Windows root export.
  Derived output, regenerated from the Windows certificate store on every
  `certs.check`/`install --from-windows`, inside a directory the registry already claims. Claiming
  it would be claiming a cache, and the same argument as "the contents of an installed tree"
  applies: the destination is the claim.
- **Skill-written config** — `~/.config/plan-docs/config.toml`,
  `~/.config/tasks-md/workspaces.json`, `~/.beads-planning`. This repo declares the _skill_; the
  skill's own config is `agent-skills`' business, and hard-coding another repo's paths here would
  rot silently the first time one of them moves. The footer says so rather than leaving the gap
  looking like an oversight.
- **The contents of an installed tree.** Only the destination is claimed. Enumerating what is inside
  `~/.local/share/go` would be a file listing, not a registry.
- **Paths outside `~`.** Nine `/etc` and `/usr/local` targets are written by this repo; a dotfiles
  lifecycle can never cover a root-owned file, so they are counted in the footer and excluded from
  every percentage.
- **Live `gsettings`/`dconf` values.** Reading one back means shelling out to a tool that needs a
  session bus, and this command must stay runnable in a container and over ssh. A dconf claim
  therefore reports its key and no value.

## Reading the `state` column

Only claims the deploy manifest covers get a real `deploy.State` (`clean`/`stale`/`dirty`/
`unknown`/`absent`). Everything else reports `present`/`absent`, and a claim with no filesystem
location reports `—`.

That is not a gap to fill in by inference. A registry entry does not imply a classifier: a block, a
merged JSON key and a dconf value each need their own notion of "dirty", and none has been designed.
Reporting presence and saying so is correct; borrowing the whole-file classifier and pretending
would produce confident wrong answers on two-thirds of the machine.

## Keeping it derived

Everything that can come from `setup.toml` does — block claims from the `zshrc`/`zshenv`/`zprofile`
fields, dconf claims from each extension's `dconf` table, install claims from `dest`/`install_dir`/
`bin_pick`/`symlinks`/`env`/`check_path` and the method. A package added tomorrow appears with
nobody remembering to add it.

The rest cannot be: a destination that is a literal inside the task that writes it has nothing to
derive from. Those claims reference **the writing module's own constant** (`ssh.SSH_CONFIG`,
`proxy.UNIT_PATH`, `screenshot.FLAMESHOT_INI`, `system.CURLRC`, ...) rather than repeating the path,
so the registry and the writer cannot disagree about where a file is.

Nine such constants were promoted from `_PRIVATE` to public as part of this, and that was the right
outcome rather than a concession to a checker: basedpyright's `reportPrivateUsage` fired on every
one, and it was correct to. A path the registry reads is no longer that module's private detail — it
is a cross-module contract, and naming it as one is what stops a later refactor renaming it without
noticing who else depends on it. The alternative considered and rejected was a per-line
`# pyright: ignore`, which would have suppressed exactly the warning that identified the coupling.

`single_binary` packages are the one place a `setup.toml` field needed interpreting rather than
reading: their `env` names an install _prefix_ (`DPRINT_INSTALL = "~/.local"`), so claiming it
verbatim put the entire XDG root in the registry on the strength of one binary. Claim
`~/.local/bin/<check_cmd>` instead.

## Pitfalls hit while building it

- **A coverage percentage over a filtered view is arithmetically true and meaningless.** The first
  version computed the headline number from whatever the `--writer`/`--tier` filter had selected, so
  `--writer install` reported "0% of the non-derived surface". The denominator is fixed now, and the
  filter only changes the per-selection counts.
- **A glob is not a location.** The PyCharm claims carry a `*` in their target, so presence cannot
  be answered for them; they hold no `path` and report `—` rather than reporting every JetBrains
  option file absent.
- **Moving the tests' idea of `~` takes two constants, not one.** `_LOCAL_BIN` is computed at import
  from the real home, so patching `_HOME` alone leaves every `~/.local/bin` claim pointing at the
  real machine — where `_under_home` then filters it out and the test passes for the wrong reason.
