---
status: in-progress
updated: 2026-08-30
depends_on: [agent-skills]
---

# A config lifecycle layered over private dotfiles repos

## Context

PULSE is a **public** repo. Every config it deploys is therefore a public choice, offered to
everyone who clones it. The plan opened on the premise that roughly half of what it deploys is not a
public choice at all — one person's preference in `config/p10k.zsh`, `config/terminator.conf`,
`config/wezterm.lua` and the `config/agents-md/` fragments, forcing every consumer into
peculiarities. The user's framing, 2026-08-29:

> the point is to have a place to keep MY preferences separate from PUBLIC choices that are in
> pulse, otherwise i will force pulse users to embrace my peculiarities, which might not be at all
> useful for many.

**That premise did not survive the file-by-file audit** — see the DECISION under "Open questions",
2026-08-30. Every candidate turned out to be a defensible smart default, and nothing moves out of
`config/`. What survives is the plan's _other_ half, which was never about peculiarities: a config
PULSE writes into `~` still has no way home, the surface is still far wider than `config/`, and a
customization made here still dies with this disk. Read the rest of this document with that
correction in mind — the layering it designs is for content that does not exist in `config/` today
and for the machine-bound facts that do.

The second half of the problem is that a config PULSE writes into `~` today has **no way home**.
`contributing/deploy.md` closes the loop in one direction only — the writer can no longer silently
destroy a hand edit — and records the reverse as deliberately unbuilt:

> **Deliberately not built:** auto-porting a deployed edit back into the repo source. PULSE reports
> and asks; the human decides and commits.

That was right while the only destination was a public repo: a hand edit is usually personal, and
personal content had nowhere to go except a repo everyone reads. With a private destination the
calculus changes, and the missing return path becomes the whole point. Today a customization made on
this machine — a tuned terminator layout, a GNOME keybinding, a `~/.zshrc` addition — exists on
exactly one disk and dies with it.

Third: the surface is much wider than `config/`. Skills from
[`agent-skills`](https://github.com/TheodoreAD/agent-skills) now write their own config into `~`
(`~/.config/plan-docs/config.toml`, `~/.config/tasks-md/workspaces.json`), applications rewrite
their own files underneath PULSE, and the desktop keeps its state in dconf where no file exists at
all. Nothing enumerates that surface, so nothing can preserve it.

### What this has to serve

Two user shapes, and the design fails if it only serves the second:

- **One development machine.** Should need zero new concepts. No repo, no layer, no new command —
  the machine behaves exactly as it does today, and the lifecycle only appears when asked for.
- **Several machines.** Wants personal preferences to follow them everywhere, and genuinely
  machine-bound facts (a GPU workaround, a monitor layout, a work-issued CA bundle path) to stay
  put. This is where layering earns its complexity.

### Grounding facts (verified 2026-08-29, do not re-derive)

- `inv deploy.status` reports **10** whole-file managed paths on this machine: `askpass-zenity`,
  `AGENTS.md`, `statusline-command.sh`, two `google-chrome-x11` desktop files, `pulse-proxy-start`,
  `research-update`, `actrc`, `terminator/config` (the one reported dirty), `wezterm.lua`.
- Only **3** of those are `config_files` (the `SEEDED` policy: PULSE seeds, the user owns it after).
  The rest are `MANAGED`.
- `util.ensure_block` writes marker-delimited regions into files the user owns — call sites in
  `zsh.py` (`~/.zshrc`, `~/.zshenv`, `~/.zprofile`), `ssh.py` (`~/.ssh/config`), `certs.py`,
  `proxy.py`, `system.py` (`~/.config/curlrc`, plus `/etc` targets).
- `util.write_claude_settings` merges into `~/.claude/settings.json` from **6** call sites in
  `ai.py` and `allowlist.py`; `fonts.py` merges into VS Code's `settings.json`.
- Neither of those two writers has any drift classification — recorded as `[DEFERRED:]` in
  `plans/2026-08-24-machine-local-setup-toml-overrides.md`, inherited from the retired drift-guard
  plan.
- Skills reference `~/.config/plan-docs/config.toml`, `~/.config/tasks-md/workspaces.json`,
  `~/.beads-planning`, `$RESEARCH_HOME`, `$PLANS_HOME`, `$PLANS_SENSITIVE_HOME`.
- No dotfiles repo exists on the account today. `win-configs` (public) is the Windows counterpart of
  PULSE; `pycharm-settings` (private) is a single-app precedent for private config in git.

## Prior art — what the community actually does

Researched 2026-08-29. This is search-and-docs depth, not hands-on: nothing below has been run.

**[chezmoi](https://www.chezmoi.io/)** is the current consensus pick, and its command vocabulary is
the closest thing to a specification for the round trip this plan wants: `apply` writes the target
state, `diff`/`status` compare, `update` is `git pull --autostash --rebase` then apply, and
**`re-add`** pulls a locally-modified managed file back into the source state — exactly the missing
verb. Its answer to machine differences is _templating_ (`{{ if eq .chezmoi.os … }}`) plus per-
machine data in `~/.config/chezmoi/chezmoi.toml`, and its answer to secrets is age/GPG encryption or
a password manager, which is what lets its users keep the repo public. What it does **not** have is
first-class layering of two source repos: one source directory per machine, with
`.chezmoiexternal.toml` or submodules as the workaround.

**[rcm](https://github.com/thoughtbot/rcm)** (thoughtbot) is the tool that does have it, and its
model maps onto the ask almost exactly: `DOTFILES_DIRS` takes several directories, **first match
wins** (`.dotfiles/vimrc` beats `marriage-dotfiles/vimrc`), and host-specific files live in a
`host-<hostname>/` directory that only installs on that host. Three layers, precedence, per-machine
overlay — as a shipped convention rather than a design to invent.

**[yadm](https://yadm.io/)** treats `~` itself as the work tree of a bare repo and disambiguates
with filename suffixes (`file.cfg##os.Linux`, `##hostname.…`), with an `encrypt` list for the secret
subset. Cheap to adopt, but the alternates syntax is widely reported as the part people leave it
over.

**GNU Stow / [dotbot](https://github.com/anishathalye/dotbot)** are the no-abstraction end: symlink
farms, plain files, no state and no templating. PULSE is deliberately copy-based, not symlink-based
(`contributing/deploy.md`: "Copies, not symlinks — a fixed constraint"), so Stow's model is excluded
by an existing decision rather than by preference.

**The hand-rolled classics** —
[mathiasbynens](https://github.com/mathiasbynens/dotfiles)/[holman](https://github.com/holman/dotfiles),
via [dotfiles.github.io](https://dotfiles.github.io/) — converged decades ago on the cheapest
possible version of this exact split: a public repo plus a sourced-if-present private file
(`~/.extra`, `~/.localrc`), sometimes with the private half cloned from its own repo into
`~/.dotfiles/private`. No tooling, no manifest, and it has outlasted most of the tools.

**[home-manager](https://nix-community.github.io/home-manager/)** solves it completely and takes the
whole package manager with it. Out of scope: PULSE _is_ the package layer here.

The reusable finding: **the layering is rcm's, the verbs are chezmoi's, and the graceful degradation
is mathiasbynens'.** None of the three needs to be adopted wholesale — PULSE already owns the
registry (`setup.toml`), the writer (`deploy.py`) and the state manifest, which is the expensive
two-thirds of what these tools are.

## The classification the inventory needs

One enum cannot express this — `enabled = false` is already being asked to mean both "PULSE does not
manage this here" and "PULSE manages this, but only on another machine"
(`plans/2026-08-24-machine-local-setup-toml-overrides.md`). Three independent axes instead, per
`~/AGENTS.md`'s "Designing a generator or multi-mode tool":

**Axis A — writer** (how the bytes get there; determines what "drift" even means):

| writer       | mechanism                                             | examples                                            |
| ------------ | ----------------------------------------------------- | --------------------------------------------------- |
| `whole-file` | `deploy.py` — wrapper-script, assembled, config_files | `~/AGENTS.md`, `~/.config/wezterm/wezterm.lua`      |
| `block`      | `util.ensure_block` marker regions                    | `~/.zshrc`, `~/.ssh/config`, `~/.config/curlrc`     |
| `merge`      | structured merge into co-owned JSON                   | `~/.claude/settings.json`, VS Code `settings.json`  |
| `imperative` | no file at a known path — gsettings/dconf, CLI        | GNOME keybindings, extension settings               |
| `skill`      | written by an `agent-skills` script                   | `~/.config/plan-docs/config.toml`                   |
| `app`        | the application rewrites it underneath                | `~/.config/terminator/config`, Chrome `Local State` |
| `human`      | hand-made, nothing declares it                        | whatever is in `~` that no rule claims              |

**Axis B — authority** (who wins a conflict): `pulse` · `user` · `co-owned` · `app`. This is the
existing `MANAGED`/`SEEDED` distinction, generalized — `SEEDED` is `pulse`-written but `user`- (or
`app`-) authoritative.

**Axis C — portability tier** (the new one, and the reason this plan exists):

| tier       | means                                                   | lives in                     |
| ---------- | ------------------------------------------------------- | ---------------------------- |
| `public`   | a good default for anyone cloning PULSE                 | PULSE `config/`, as today    |
| `personal` | my preference, wanted on every machine I own            | the private defaults repo    |
| `machine`  | true of this box only — GPU, monitors, work CA path     | the private per-machine repo |
| `secret`   | never in any repo without encryption                    | nowhere; keys stay keys      |
| `derived`  | state, caches, manifests — regenerable, never versioned | `PULSE_STATE_DIR`, untouched |

The three axes are orthogonal: `~/.zshrc` is `block`/`co-owned`, and _which_ block is which tier
varies line by line; `~/.p10k.zsh` is `whole-file`/`pulse`/**`personal`** — which is precisely the
mismatch that makes it wrong to ship from a public repo today.

**The first deliverable is the inventory itself, and it must be generated, not hand-written.**
`deploy.managed_paths()` already derives the `whole-file` third from `setup.toml` alone. The other
writers need the same treatment — a registry entry per ownership model, which is the exact
`[DEFERRED:]` item the overrides plan is holding. A dotfiles lifecycle covering only whole files
would cover about ten paths out of a home directory whose interesting content is mostly blocks,
merged JSON and dconf.

## Step 1 landed, and the number it produced (2026-08-30)

`inv home.list-claims` (`tasks/home.py`, read-only) is the inventory. Rationale, the full breakdown
and what is deliberately not claimed are in `contributing/home-claims.md`; the user-facing page is
`docs/configuration.md`. **109 claims on this machine**, against the 10 paths `deploy.status` could
see:

| writer                  | claims |
| ----------------------- | -----: |
| `install`               |     36 |
| `block`                 |     24 |
| `imperative`            |     23 |
| `whole-file`            |     11 |
| `symlink`               |      5 |
| `whole-file-undeclared` |      3 |
| `key`                   |      3 |
| `merge`                 |      2 |
| `generated`             |      1 |
| `external`              |      1 |

By tier: 69 `public`, 35 `derived`, 4 `machine`, 1 `secret`, **0 `personal`**.

**The number the rest of this plan has to be sized against: a whole-file-only lifecycle reaches 14
of the 74 non-derived claims — 18%.** `derived` is excluded from the denominator because an
installed Go toolchain or an `nvm` directory can never be the subject of a config lifecycle;
including them would flatter the number by a third. The first measurement, before step 3 folded the
ad-hoc writers in, was 15 of 74 with only 10 classifiable — the reach barely moved, because those
files were already whole files; what changed is that all 14 now carry a manifest entry and a diff.

Five findings that change the plan below rather than merely confirming it:

1. **Axis A needs ten values, not seven.** Four writers the table above did not name are real and
   each has a different notion of a conflict: `whole-file-undeclared` (deploy.py's writer, but a
   destination decided at run time rather than declared — see step 3 below for why that is a
   category and not an oversight), `key` (regex surgery on one key of a file an application owns,
   which can rewrite the wrong line where a JSON merge can only lose its own key), `symlink` (the
   claim is the link, not any bytes — five of them, invisible to `deploy.lookup()`, which resolves
   them onto their target's entry), and `generated` (composed by a task, with no source to compare
   against, so it can never be classified and that is correct). `human` was dropped: a path nothing
   claims is by definition not in a registry of claims.
2. **`deploy.py`'s unification stopped three writers short.** `zsh.configure-p10k` writes
   `~/.p10k.zsh` skip-if-exists with **no redeploy path at all**; `ide.configure-pycharm`
   unconditionally overwrites two files in a **glob-discovered** JetBrains directory;
   `proxy.install` writes its systemd unit from a module constant rather than a `config/` file.
   These are exactly the "too many ways to write into `~`" `contributing/deploy.md` set out to
   remove, and a prerequisite for step 6 — `dotfiles.capture` for whole files cannot capture a path
   with no manifest entry. Acted on the same day; see "Step 3 landed too" below.
3. **Every skill on this machine is invisible to `deploy.py`.** `deploy._skill_entries` registers
   only `source = "local"` skills and this repo deliberately declares none, so the whole of
   `~/.agents/skills/` is declared in `setup.toml` and absent from the registry.
4. **The machine tier already exists, at four claims**, before anything is built: the `certs` and
   `proxy` blocks in `~/.zshenv`, the `ssh` block in `~/.ssh/config`, and `overrides.toml`. All four
   are identity-derived or hand-written and genuinely true of this box only. That is real evidence
   for the layering, and it also means open question 3 (does the machine tier get a remote?) is
   about content that exists today, not a hypothetical.
5. **`personal` is empty, which is the plan's premise measured.** Every one of the 69 `public`
   claims is public because there is nowhere else for it to go — not because anyone judged it a good
   default for a stranger. The tier column deliberately reports where content lives _today_ rather
   than where it should; reclassifying is steps 2–4, and the inventory must not pre-empt it.

[DECISION: the inventory is a **new `home.*` namespace**, not an extension of `deploy.*`.
`deploy.py`'s docstring scopes it to "one way to write a file into the home directory", and that
contract is what makes its five-state classifier trustworthy; a registry of paths it does not write
would make the contract mean two things. `tasks/home.py` owns the claims, `deploy.py` keeps owning
the whole-file writer, and the whole-file third of the registry is **derived** from
`deploy.managed_paths()` with a test asserting the equality, so a second hand-maintained list of the
same paths cannot appear. The task name `list-claims` is verb-first per `invoke-task-conventions`
and matches the `<ns>.list-*` shape the machine's allowlist auto-approves as read-only — which binds
this command to stay read-only forever.]

[DECISION: **a registry entry does not imply a classifier**, and the inventory says so rather than
faking one. Only the deploy manifest records what was written, so only its claims get a real
`State`; everything else reports presence, and a claim with no filesystem location (a dconf key)
reports `—`. Designing a notion of "dirty" for a block, a merged JSON key and a dconf value is
separate work that this step deliberately does not start.]

[DEFERRED: skill-written config (`~/.config/plan-docs/config.toml`,
`~/.config/tasks-md/workspaces.json`, `~/.beads-planning`) is **not** claimed. This repo declares
the skill; the skill's own config belongs to `agent-skills`, and hard-coding another repo's paths
here would rot the first time one moves. The command's footer says so rather than leaving the gap
looking like an oversight. Open question 4 below is where this gets decided — and it has to be
decided in `agent-skills`, not here.]

## Step 3 landed too, and what it exposed (2026-08-30)

All five ad-hoc whole-file writers now go through `deploy.py`. `~/.p10k.zsh` is declared
`config_files` on `[packages.powerlevel10k]`; the systemd unit became `config/pulse-proxy.service`
(static, because systemd's own `%h` specifier does what the f-string was doing by hand) and the two
PyCharm font files are deployed from `Managed` objects resolved against whichever PyCharm is
installed; `identity.toml` stays outside, correctly, as its own `generated` writer — a wizard
composes it from answers, so there is nothing to diff it against.

[DECISION: **a destination declared in `setup.toml` is one `inv verify.all` requires to exist.** It
runs at the end of `inv setup`'s packages phase and fails on `ABSENT` for MANAGED and SEEDED alike.
So a file written only in some situations (the corporate-only systemd unit) or at a path discovered
on the machine (the glob-matched PyCharm directory) goes through the writer **without** being
declared — hence the `whole-file-undeclared` writer value. Declaring either would fail `inv setup`
on every machine that legitimately lacks it. This is the constraint that decides what can ever be
declared, and it was not visible before step 3 tried.]

[DECISION: `Mechanism.MANAGED_FILE` — a verbatim copy that PULSE owns and does **not** chmod 0755.
`wrapper-script` was the only MANAGED whole-file shape and it makes its destination executable,
which is wrong for a systemd unit and for an XML options file, so a PULSE-owned non-executable file
had no way to be expressed at all — which is exactly why the unit ended up as a module constant. A
matching `managed_files` setup.toml field was written and then removed: with both its users
undeclarable by the decision above, it had no consumer, and a field nothing declares is a second way
to spell something.]

[PITFALL: `config_files` is documented as method-agnostic and was not — the applier was `apt.py`'s
private helper, called only from the apt and deb install paths. An `archive` or `git-clone`
package's declared config (`~/.config/wezterm/wezterm.lua`, and `~/.p10k.zsh` once declared) was
therefore never written during `inv setup` at all: it waited for an `inv deploy.all` a fresh machine
has no reason to run, while `verify.all` at the end of that same phase demanded it exist. Found only
by trying to declare `~/.p10k.zsh` and asking what would happen on a fresh machine. Fixed —
`deploy.apply_config_files`, called by `tools.install` after every installer.]

## The layering

Two repositories, three resolution levels — settled 2026-08-30, see the DECISION under "Open
questions":

```
PULSE  config/                     public    — defaults for everyone, unchanged
  └─ <dotfiles>/base/             private   — my preferences, every machine I own
       └─ <dotfiles>/machines/<hostname>/   — this box only
                                    ↓ first match wins (rcm's rule)
                              deploy.py → ~
                                    ↑ capture (review → level → commit)
```

The shape the user asked for is helm/kustomize's: a base holding what is always the same, and a
directory per machine holding what differs. Two differences from kustomize worth stating before
anyone reaches for its vocabulary:

- **A machine directory replaces a file, it does not patch one.** kustomize patches structured YAML;
  here the layers hold `p10k.zsh`, `wezterm.lua`, `terminator.conf`, `.desktop` files — four formats
  with no common merge semantics, and a per-format merger is a second config language.
  First-match-wins on whole files is rcm's rule and is what keeps this cheap.
- **The one thing that already merges is the declaration, not the content.** `overrides.toml`
  patches `setup.toml` at the key level and predates this plan; it stays that way. So the split is
  clean: declarations merge, content files replace.

Directory names are a small choice, not a decision — `base/` and `machines/<hostname>/` read
clearly, keep every hostname under one parent, and leave `base/` free of any host-shaped name. rcm's
flat `host-<hostname>/` would work identically.

Three properties make this cheap rather than a second config language:

1. **PULSE keeps the registry; the layers keep only content.** A path exists because a
   `[packages.*]` entry (or the widened registry) declares it, exactly as today — the layers answer
   only "whose bytes go here", never "what may be installed". Every install stays declared in one
   reviewable place, which is the repo's founding principle.
2. **Layers are resolved at deploy time by first match**, so `deploy.py`'s five-state classifier,
   its manifest and its prompts are unchanged in shape — only `expected_bytes()` learns to search
   the layer list before falling back to `config/`.
3. **Absent layers are not an error.** With no layer repos configured, resolution finds only
   `config/` and the machine behaves precisely as it does today. That is the single-machine UX: the
   feature is invisible until `inv dotfiles.init` is run.

Which repo it is and where it is cloned is **machine-local configuration**
(`~/.config/power-user-linux-setup/`, beside `identity.toml` and `overrides.toml`) — never
`setup.toml`. A repo URL in the public tracked file would be the same category error as the
peculiarities this plan is removing. Only the URL and the clone path need recording: the machine
directory is found by hostname, so nothing has to name this box twice.

Note the chicken-and-egg that follows, and that `dotfiles.init` has to handle: `identity.toml` and
`overrides.toml` are themselves candidates for the machine directory, and they are also where the
layer's own location is recorded. Whatever lands there, the pointer to the repo stays a plain local
file that needs no repo to read.

[DECISION: this does **not** reopen the 2026-08-24 decision that "git is not for data on individual
hosts". That decision rejected _hostname-keyed sections inside PULSE's own tracked `setup.toml`_,
and stated that preserving a home directory is the user's own duty. A user's private repo is the
user discharging that duty; PULSE supplies the mechanism and holds none of the data. The distinction
to keep sharp: PULSE guarantees the stability of its **defaults**, and a layer repo is the user's
data at every point in its life.]

### The round trip

Verbs, borrowed from chezmoi and named for this repo's conventions (`invoke-task-conventions`):

- **forward** — unchanged: `inv deploy.status` classifies, `inv deploy.all` writes, showing the diff
  before it asks.
- **`inv dotfiles.capture <path>`** — chezmoi's `re-add`, plus the question chezmoi never has to ask
  because it has one source: _which tier?_ Shows the diff, asks `personal` or `machine`, writes into
  that layer's repo, updates the deploy manifest so the path classifies `CLEAN` again, and prints
  the exact `git -C … add <one path> && commit` line. Committing is the human's, as everywhere else
  in this family.
- **`inv dotfiles.sync`** — `git pull --autostash --rebase` in each layer, then `deploy.status`. Not
  an automatic apply: this repo's whole drift design is that a human sees a diff before a file in
  `~` is overwritten.
- **`inv dotfiles.init`** — the walkthrough: clone or create the layers, record them
  machine-locally, offer to capture what is already dirty.

Two shapes worth stealing verbatim from the store that `plan-docs` already runs on this machine: its
**two tiers with different remote policies**, and its **commit-immediately** rule (an uncommitted
file in a repo nobody browses is the same as no file at all).

## Open questions

[DECISION: **nothing moves out of `config/`. There is no de-peculiarization pass.** Settled by the
user 2026-08-30 after a file-by-file audit, and it reverses this plan's own opening premise rather
than merely answering the question:

> it looks like very few things are truly private now, the wezterm split is something that could be
> a default because it makes life much easier when you start it (…) the terminator color option is
> there to stay for everyone, the red is very annoying (…) the font is most certainly there to stay,
> it's a feature of pulse (…) the p10k config is also to keep public as a default (…) the point of
> pulse is awesome smart defaults, after all.

Every candidate was reclassified as a smart default rather than a peculiarity, which is a coherent
position and arguably the repo's whole thesis: a config nobody has to think about is the product.
Per file, with what the audit found:

- **`p10k.zsh`** (1103 lines, 57 KB) stays as the public default. The counter-argument considered
  and rejected: with no `~/.p10k.zsh`, p10k runs its own `configure` wizard on first shell, so
  shipping nothing is not "no prompt" but "p10k's own onboarding". Rejected because the wizard is
  precisely the leftover manual step everything else here exists to remove — the font, the icons and
  the theme are already vetted to work together, and making the user re-derive the prompt is the odd
  one out. Tell them they can customize it instead.
- **`wezterm.lua`'s 2×2 pane grid**, which the audit called the clearest peculiarity in the repo, is
  a **feature**: it makes the terminal useful the moment it opens. Document it as a power-user
  feature rather than hiding it.
- **`terminator.conf`'s `title_transmit_bg_color`** stays for everyone — Terminator's default red is
  the thing every user ends up changing by hand.
- **The font** stays, and is a PULSE feature to advertise. It is not taste in the sense this plan
  meant: PULSE installs the Nerd Font, so pointing its terminals at it is coherence, not preference.
- **`statusline-command.sh`** stays and should be showcased.
- **The `agents-md/` fragments** stay, all four. `this-setup.md` looked like the problem — it is
  literally "this machine" — but every rule in it is true of _any_ machine PULSE sets up, because
  PULSE is what creates that shape. A public consequence of a public repo.
- The remaining eight files were never candidates: `actrc`, `askpass-zenity.sh`,
  `pulse-proxy-start.sh`, `pulse-proxy.service`, `research-update.sh`, both
  `google-chrome-x11*.desktop` (already `enabled = false` by default) and the two `.example`
  templates are mechanism, not taste.

Measured while auditing, and worth keeping because both numbers are true and tell opposite stories:
genuinely-personal content was **2.5 files of 16, but ~64 KB of ~90 KB** — `p10k.zsh` alone is the
entire gap between the two counts, which is why "roughly half" felt right by weight and wrong by
count.]

[DEFERRED: two pieces of work this decision generated, each filed separately rather than absorbed
here — `plans/2026-08-30-font-as-one-config-value.md` (the font is hardcoded in `terminator.conf`,
`wezterm.lua` and both `pycharm/*.xml` while `[settings.fonts]` independently drives GNOME and VS
Code: five places, one font, two sources of truth) and
`plans/2026-08-30-showcase-the-defaults-in-the-docs.md` (the wezterm grid, the font, the statusline
and p10k customization all want documenting as features).]

[DECISION: **one private repo with a remote, laid out `base/` plus a directory per machine.**
Settled by the user 2026-08-30, resolving both the per-repo-vs-host-directories question and the
remote question at once:

> all config files can go in the private repo, even if they might have network topology inside, as
> long as there are no secrets or security risky things, or intellectual property. i want a single
> repo that could have a base directory, for the stuff that's always the same or default, and
> per-machine directories with overrides, sort of like a helm / kustomization / gitops structure.

So the layering is **three resolution levels across two repositories**, not three repositories — see
the diagram above, updated. rcm's leaning was right about host directories; what the earlier draft
got wrong was assuming the personal and machine tiers needed separate repos.]

[DECISION: **the admission rule for that repo is "no secrets, nothing security-risky, no
intellectual property" — network topology is explicitly fine.** Stated by the user in the same
message, and the earlier draft of this plan argued from a premise that does not hold. Measured
2026-08-30: `identity.toml` contains names, email addresses, ssh host aliases with their real
hostnames and login users, optionally a proxy host/port and `noproxy` CIDRs, and optionally a
filesystem _path_ to a CA bundle. It contains no credential by construction — the proxy password
goes to the OS keyring (`proxy._capture_credential` writes the entry directly, and the file's own
comment says so), ssh private keys stay in `~/.ssh/`, and a root CA certificate is a public artifact
referenced by path rather than inlined.

The `plan-docs` store's hard no-remote rule was cited as precedent here and **does not transfer**:
that tier holds clients' and employers' internal architecture, which is other people's confidential
material and not the user's to place anywhere. `identity.toml` is the user's own data about the
user's own machine, on an account with MFA and no shared access.

The one part that is not purely the user's own: work email addresses, an employer's proxy hostname
and internal `noproxy` CIDRs are that employer's network topology. Not a risk to this account, but
whether it may sit in a personal cloud repo is a per-employer policy question rather than a
technical one — worth a look before the first machine directory holding one is pushed.]

[NEEDS CLARIFICATION: does the machine tier absorb `~/.config/plan-docs/config.toml`? That skill
states its config is per-machine and **deliberately not version-controlled**, with a stated reason
(it maps this box's clones to routes and is wrong everywhere else). Either that reasoning stands and
the machine tier explicitly excludes skill configs of this kind, or it was a workaround for having
no machine tier and should be revisited — in `agent-skills`, not here. Same question for
`~/.config/tasks-md/workspaces.json` and `~/.beads-planning`.]

[NEEDS CLARIFICATION: how does `capture` work for the non-`whole-file` writers? A dirtied `~/.zshrc`
block, a hand-added key in `~/.claude/settings.json`, and a changed dconf value each need a
different notion of "the delta", and only the first is a diff of two files. Possible answer: v1
captures `whole-file` only and states the limit loudly; possible answer: dconf gets its own
`dconf dump`-based capture, since GNOME settings are among the things people most want to survive a
machine.]

[NEEDS CLARIFICATION: namespace — a new `dotfiles.*` namespace, or extend `deploy.*` with the
reverse direction? `deploy` is already the action namespace for writing into `~`, and layers are
just extra sources for it; but `capture`/`sync`/`init` are about the repos, not about deploying.
Leaning: layers stay invisible inside `deploy.*` (forward), and `dotfiles.*` owns repo lifecycle
(`init`, `capture`, `sync`).]

[NEEDS CLARIFICATION: templating, yes or no? Every surveyed tool has it and every one of them pays
for it with a second language in the config files. The layer model may make it unnecessary — a whole
file per machine instead of one file with conditionals. Cheapest position: no templating in v1, and
if the same file keeps being duplicated across host directories with a one-line difference, that is
the evidence to revisit. The `base/` + `machines/<hostname>/` shape settled above is exactly the
"whole file per machine" side of that trade, so the leaning is now structural rather than merely
cheap — but "no templating" is still a build-time decision to take deliberately when step 4 lands,
not one this structure forces.]

[DECISION: **no encryption story — secrets are never in a layer, full stop.** Settled 2026-08-30 by
the admission rule for the private repo: no secrets, nothing security-risky, no intellectual
property. `age`/GPG exists in chezmoi and yadm because those tools' users keep their dotfiles repo
**public**, so encryption is what lets a secret live there at all; this repo is private and the
boundary does the same job with no key management, no second tool and nothing to lose.
`identity.toml` was the test case and it passes: measured 2026-08-30, it carries names, addresses,
hostnames, ports, CIDRs and a filesystem path, and no credential — the proxy password is in the OS
keyring and the ssh private keys are in `~/.ssh/`, both by construction rather than by convention.
If something genuinely secret ever needs to follow the user between machines, the answer is a secret
manager, not a layer with encryption bolted on.]

## Recommended direction

Sequenced so each step is independently useful and nothing is built before the thing it depends on:

1. ~~**The inventory, first and alone.**~~ **Landed 2026-08-30** — `inv home.list-claims`, 109
   claims, 20% whole-file coverage of the non-derived surface. See "Step 1 landed" above. It also
   discharges the `[DEFERRED:]` item `plans/2026-08-24-machine-local-setup-toml-overrides.md` held
   ("wants a registry entry per ownership model so 'is this path PULSE-managed?' has one answer for
   all three") — that tag can be retired from the overrides plan, since the registry now exists;
   what it does **not** discharge is the second half, designing drift classification for the block
   and merge writers, which stays open there.
2. ~~**Answer the remote question for the machine tier.**~~ **Answered 2026-08-30** — one private
   repo with a remote, `base/` plus a directory per machine, admitting any config file that carries
   no secret, nothing security-risky and no intellectual property. That collapses what the plan
   assumed were two layer repos into one, and it settles the per-repo-vs-host-directories question
   with it. Both DECISIONs are under "Open questions"; the layering diagram is updated.
3. ~~**Fold the ad-hoc whole-file writers into `deploy.py`.**~~ **Landed 2026-08-30**, same session
   as step 1. All five now go through the one writer, so classifiable went 10 → 14 of 14 whole-file
   claims — which step 6 depends on, since `capture` cannot capture a path with no record of what
   was written there. What it took, and the two constraints it exposed, are below.
4. **Layer resolution in `deploy.py`** — first-match search across configured layers, falling back
   to `config/`. Small, and by itself it already lets personal content leave the public repo.
5. ~~**The de-peculiarization pass.**~~ **Cancelled 2026-08-30** — the audit found nothing to move.
   Every candidate is a smart default and stays public; see the DECISION under "Open questions". Two
   pieces of work it generated are filed as their own plans (the font as one config value, and
   documenting the defaults as features). This step's disappearance is the plan getting smaller in
   the right direction, not scope being dropped.
6. **`dotfiles.capture` for `whole-file` paths only**, stating the limit. The manifest already knows
   what PULSE wrote, so the diff is free; the level question is the only new judgment. The limit is
   now measurable rather than hand-waved: it covers 18% of the non-derived surface, and the footer
   of `inv home.list-claims` is where a reader sees what it misses.
7. **Everything else on evidence** — templating, non-whole-file capture, encryption — each revisited
   only when a real duplication or a real loss makes the case. `~/AGENTS.md`'s "Pilot before
   generalizing": this machine is the pilot, and it has exactly one dirty managed path today
   (`~/.config/terminator/config`), which is a thin evidence base for a large mechanism.

[PITFALL: a private GitHub repo is not an access-controlled secret store — it is a repo whose
history is as readable as its tip to anyone who ever gains access to the account. The tier boundary
is what keeps content out, exactly as in the `plan-docs` store; "it's private" is not a substitute
for that boundary.]

[PITFALL: layer resolution changes what `expected_bytes()` returns, which changes every digest in
the deploy manifest. Introducing layers will make previously-`CLEAN` paths classify `STALE` en masse
on first run unless the migration is thought through — and a mass prompt is exactly the "unattended
runs" regression `contributing/deploy.md` warns about.]

[DEFERRED: the Windows counterpart. `win-configs` is public and has the identical problem; whatever
tier vocabulary lands here should be reusable there rather than reinvented, but nothing about this
plan should wait for it.]
