---
status: in-progress
updated: 2026-08-30
depends_on: [agent-skills]
---

# A config lifecycle layered over private dotfiles repos

## Context

PULSE is a **public** repo. Every config it deploys is therefore a public choice, offered to
everyone who clones it. But roughly half of what it currently deploys is not a public choice at all
— it is one person's preference (`config/p10k.zsh`, `config/terminator.conf`, `config/wezterm.lua`,
the `config/agents-md/` fragments), and shipping those as the repo's defaults forces every consumer
into peculiarities that may be useless to them. The user's framing, 2026-08-29:

> the point is to have a place to keep MY preferences separate from PUBLIC choices that are in
> pulse, otherwise i will force pulse users to embrace my peculiarities, which might not be at all
> useful for many.

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

| writer             | claims |
| ------------------ | -----: |
| `install`          |     36 |
| `block`            |     24 |
| `imperative`       |     23 |
| `whole-file`       |     10 |
| `whole-file-adhoc` |      5 |
| `symlink`          |      5 |
| `key`              |      3 |
| `merge`            |      2 |
| `external`         |      1 |

By tier: 69 `public`, 35 `derived`, 4 `machine`, 1 `secret`, **0 `personal`**.

**The number the rest of this plan has to be sized against: a whole-file-only lifecycle reaches 15
of the 74 non-derived claims — 20% — and only 10 of those (13%) can be classified at all.**
`derived` is excluded from the denominator because an installed Go toolchain or an `nvm` directory
can never be the subject of a config lifecycle; including them would flatter the number by a third.

Five findings that change the plan below rather than merely confirming it:

1. **Axis A needs ten values, not seven.** Three writers the table above did not name are real and
   each has a different notion of a conflict: `whole-file-adhoc` (a whole file written by a task of
   its own, outside `deploy.py` — five of them), `key` (regex surgery on one key of a file an
   application owns, which can rewrite the wrong line where a JSON merge can only lose its own key),
   and `symlink` (the claim is the link, not any bytes — five of them, invisible to
   `deploy.lookup()`, which resolves them onto their target's entry). `human` was dropped: a path
   nothing claims is by definition not in a registry of claims.
2. **`deploy.py`'s unification stopped three writers short.** `zsh.configure-p10k` writes
   `~/.p10k.zsh` skip-if-exists with **no redeploy path at all**; `ide.configure-pycharm`
   unconditionally overwrites two files in a **glob-discovered** JetBrains directory;
   `proxy.install` writes its systemd unit from a module constant rather than a `config/` file.
   These are exactly the "too many ways to write into `~`" `contributing/deploy.md` set out to
   remove. Folding them into `deploy.py` is a small, independently useful change and a prerequisite
   for step 5 — `dotfiles.capture` for whole files cannot capture a path with no manifest entry.
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

## The layering

```
PULSE  config/            public   — defaults for everyone, unchanged
  └─ dotfiles            private   — my preferences, all my machines
       └─ dotfiles-<machine>  private   — this box only
                                    ↓ first match wins (rcm's rule)
                              deploy.py → ~
                                    ↑ capture (review → tier → commit)
```

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

Which repos exist, and where they are cloned, is **machine-local configuration**
(`~/.config/power-user-linux-setup/`, beside `identity.toml` and `overrides.toml`) — never
`setup.toml`. A repo URL in the public tracked file would be the same category error as the
peculiarities this plan is removing.

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

[NEEDS CLARIFICATION: what actually moves out of `config/`, and does PULSE keep a default in its
place? `p10k.zsh`, `terminator.conf`, `wezterm.lua` and the `agents-md/` fragments are the
candidates, but "move it out" and "replace it with a neutral default" are different projects — a
consumer who clones PULSE and gets _no_ prompt config is worse off than one who gets someone else's.
Leaning: PULSE keeps a deliberately plain default for each, and the personal layer overrides it. The
`agents-md/` fragments are the hardest case — they are arguably this repo's most valuable public
output, not a peculiarity.]

[NEEDS CLARIFICATION: one machine repo per machine, or one repo with a `host-<hostname>/` directory
per machine (rcm's shape)? Per-repo keeps a decommissioned machine's data out of every clone and
matches "this box only" literally; one repo with host directories is far less GitHub bookkeeping and
lets a new machine start by copying a sibling's directory. Leaning: rcm's shape — one private repo,
host directories — because the number of repos is the thing that makes multi-machine setups rot.]

[NEEDS CLARIFICATION: does a machine layer holding a corporate proxy host, a work CA bundle path or
work-shaped hostnames belong on a remote **at all**? The `plan-docs` store on this machine answers
the analogous question with a hard no — its sensitive tier deliberately has no remote, and `doctor`
reports one as a problem. The ask here is explicitly a GitHub-stored repo, so this needs a
deliberate answer rather than an inherited one: private-with-a-remote, no-remote (local git only,
backup is the user's), or a third sensitive tier. Note a private GitHub repo is not a secret store.]

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
the evidence to revisit.]

[NEEDS CLARIFICATION: does any of this want an encryption story (`age`, as chezmoi and yadm both
use), or is "secrets are never in a layer, full stop" sufficient? The `secret` tier above asserts
the latter. `identity.toml` is the test case — emails and a proxy host, no keys.]

## Recommended direction

Sequenced so each step is independently useful and nothing is built before the thing it depends on:

1. ~~**The inventory, first and alone.**~~ **Landed 2026-08-30** — `inv home.list-claims`, 109
   claims, 20% whole-file coverage of the non-derived surface. See "Step 1 landed" above. It also
   discharges the `[DEFERRED:]` item `plans/2026-08-24-machine-local-setup-toml-overrides.md` held
   ("wants a registry entry per ownership model so 'is this path PULSE-managed?' has one answer for
   all three") — that tag can be retired from the overrides plan, since the registry now exists;
   what it does **not** discharge is the second half, designing drift classification for the block
   and merge writers, which stays open there.
2. **Answer the remote question for the machine tier** (open question 3). It decides whether this is
   one mechanism or two, and it is a policy question that no amount of building resolves. The
   inventory sharpened it: the machine tier is four real claims today, not a hypothesis.
3. **Fold the three `whole-file-adhoc` writers into `deploy.py`** — `~/.p10k.zsh`, the two PyCharm
   option files, the systemd unit. New, from finding 2 of the inventory. Independently useful (each
   gains a diff, a manifest entry and a redeploy path it does not have), it raises the classifiable
   share from 13% to 20% at no design cost, and step 6 depends on it: `capture` cannot capture a
   path with no record of what was written there. `~/.p10k.zsh` is the sharpest case — a
   skip-if-exists file with no redeploy path at all, and simultaneously the plan's own headline
   example of a peculiarity that should not ship from a public repo.
4. **Layer resolution in `deploy.py`** — first-match search across configured layers, falling back
   to `config/`. Small, and by itself it already lets personal content leave the public repo.
5. **The de-peculiarization pass** — move what the answer to open question 1 says should move, with
   a neutral default left behind for each.
6. **`dotfiles.capture` for `whole-file` paths only**, stating the limit. The manifest already knows
   what PULSE wrote, so the diff is free; the tier question is the only new judgment. The limit is
   now measurable rather than hand-waved: it covers 20% of the non-derived surface, and the footer
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
