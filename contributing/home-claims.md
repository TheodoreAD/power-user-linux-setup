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

**Tier reports where a claim's content lives today — it is not a recommendation.** Deciding that
`config/p10k.zsh` belongs in a private personal layer rather than in this public repo is the
de-peculiarization pass, which `plans/2026-08-29-dotfiles-repo-config-lifecycle.md` deliberately
holds until this inventory's number exists. Encoding that judgement in the inventory would answer
the question the inventory was built to inform. So `personal` and `unassigned` are part of the
vocabulary and carry **zero** claims — and that zero is the measurement: there is no personal tier
today because there is nowhere for one to live.

## The number this was built to produce

Measured on this machine, 2026-08-30:

| writer             | claims | what it is                                                    |
| ------------------ | -----: | ------------------------------------------------------------- |
| `install`          |     36 | trees and binaries an installer puts under `~`                |
| `block`            |     24 | `util.ensure_block` marker regions                            |
| `imperative`       |     23 | `gsettings`/`dconf` — no file at any path                     |
| `whole-file`       |     10 | `deploy.py`'s registry                                        |
| `whole-file-adhoc` |      5 | whole files written by a task of its own, outside `deploy.py` |
| `symlink`          |      5 | links this repo creates                                       |
| `key`              |      3 | regex surgery on one key of a file an application owns        |
| `merge`            |      2 | structured merge into co-owned JSON                           |
| `external`         |      1 | `~/.agents/skills/`, installed by the `skills` CLI            |
| **total**          |    109 |                                                               |

By tier: 69 `public`, 35 `derived`, 4 `machine`, 1 `secret`; zero `personal`.

**A whole-file-only lifecycle would reach 15 of the 74 non-derived claims — 20% — and only 10 of
those (13%) can be classified at all.** That is the number
`plans/2026-08-29-dotfiles-repo-config-lifecycle.md` step 1 exists to produce, and it is what the
rest of that plan has to be sized against.

`derived` is excluded from that denominator deliberately: an installed Go toolchain or an `nvm`
directory can never be the subject of a config lifecycle, because its content is upstream's and
regenerating it is the repair. Including them would flatter every coverage number by a third.

## What the inventory found that nothing else had recorded

Building it turned up five claims nobody had written down, each a real ownership model the
`deploy.py` rework did not absorb:

- **`whole-file-adhoc` exists, and it is five paths.** `zsh.configure-p10k` (`~/.p10k.zsh`,
  skip-if-exists with no redeploy path at all), `ide.configure-pycharm` (two files, unconditional
  overwrite into a **glob-discovered** JetBrains directory), `proxy.install`
  (`~/.config/systemd/user/pulse-proxy.service`, content from a module constant rather than a
  `config/` file), and `identity.init`. These are exactly the "too many ways to write into `~`" that
  `contributing/deploy.md` set out to unify — the unification landed for three writers and stopped.
- **`key` is a distinct writer, not a variant of `merge`.** Merging into JSON parses the document
  and replaces a value; `zsh.configure-omz`, `screenshot.enable` and `chrome.fix-launchers` do regex
  substitution on text some other program owns. The failure modes differ: a merge can only lose the
  key it writes, a regex can rewrite the wrong line.
- **`symlink` is its own claim.** `deploy.lookup()` resolves `~/.claude/CLAUDE.md` onto
  `~/AGENTS.md`'s entry, which is right for "what content should be here" and means the link itself
  appears in no registry. There are five such links.
- **Every skill on this machine is invisible to `deploy.py`.** `deploy._skill_entries` registers
  only `source = "local"` skills, and this repo deliberately declares none — every skill is authored
  in `agent-skills` and fetched from its remote by the `skills` CLI. So the whole of
  `~/.agents/skills/` is declared in `setup.toml` and absent from the deploy registry.
- **The machine tier already exists, at four claims.** The `certs` and `proxy` blocks in
  `~/.zshenv`, the `ssh` block in `~/.ssh/config`, and `overrides.toml`. All four are derived from
  `identity.toml` or hand-written, and all four are genuinely true of this box only — which is
  evidence for the layering the plan proposes, from before it is built.

## Deliberately not claimed

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
