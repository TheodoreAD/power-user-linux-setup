---
status: idea
updated: 2026-08-25
---

# What PULSE could learn from developer-focused distros

## Context

Question raised 2026-08-25: "looking at everything PULSE does, how does it compare with
development-focused Linux distributions?", followed by an explicit framing for this file — **the
point is not to compete with them or converge on what they are, just to harvest what's worth
stealing.** Nothing here is a commitment; this exists so the survey doesn't have to be redone.

The category answer, stated once so it isn't re-litigated below: a dev distro ships a curated
_image_ (kernel, drivers, DE defaults, a package set someone else picked, QA'd as a unit); PULSE
ships a re-runnable _manifest_ that turns a stock Ubuntu 24.04 into one specific person's machine,
including everything under `~` that no distro ever touches after `/etc/skel` on install day.
Different layers. The correct pairing has always been "boring Ubuntu-family base **plus** PULSE",
never "PULSE instead of a distro" — so every candidate below is a feature to borrow, not a
positioning move.

### Grounding facts (verified 2026-08-25, do not re-derive)

What PULSE is, concretely: 103 `[packages.*]` sections in `setup.toml` across 15 install methods (40
`apt`, 22 `gnome-extension`, 14 `uv-tool`, 8 `skill`, 7 each `wrapper-script`/`apt-repo`, 6 each
`deb-url`/`deb-github`, 5 each `zsh`/`script`/`archive`, 3 `git-clone`, 1 each `nvm`/`binary`/
`apparmor-profile`), driven by ~110 invoke tasks in four phases (`tasks/setup.py:7-26`: system,
packages, shell, desktop).

Already present — several of these are exactly what the projects below get praised for, so the
survey must not "discover" them as gaps:

- **Dry run across every install task** — `PULSE_DRY_RUN=1` (ansible's `--check`).
- **Deployed-file drift detection with a state manifest** — `inv deploy.status` /`inv deploy.all`,
  backed by `PULSE_STATE_DIR/deployed.json` (`tasks/deploy.py:42`) plus an ownership marker that
  survives a wiped state dir (`tasks/deploy.py:47-48`). This is chezmoi's `verify`/`status`/`apply`
  triad for the subset of `~` that PULSE writes.
- **Post-install functional verification** — `inv verify.all`, run as the last step of the packages
  phase. No comparison project in this survey has an equivalent; keep it.
- **Convergence, in exactly one domain** — `inv gnome.clean` (`tasks/gnome.py:247`) removes user
  extensions not enabled in `setup.toml`. This is the NixOS "delete from config → it's gone"
  property, implemented once, for one method. See learning 2.
- **Environment profiles** — 7 gating tags + `PULSE_EXCLUDE_TAGS`, and machine-local
  `overrides.toml` (`tasks/util.py:525-540`, from
  `plans/2026-08-24-machine-local-setup-toml-overrides.md`).
- **Read-only diagnostics per domain** — `wsl.check`, `devcontainer.check`, `proxy.check`,
  `certs.check`, `gnome.status`, `allowlist.status`, `deploy.status`, `screenshot.status`.
- **Cache reclamation** — `inv clean.all` / `clean.all-full`.
- **A post-setup "what now"** — `tasks/next_steps.py`.

Absent, and relevant to what follows:

- No rollback, snapshot, or recovery boundary of any kind. Root fs on this machine is **ext4** on
  LVM (`/dev/mapper/vgubuntu-root`) — no btrfs snapshots available without a reinstall, which
  constrains learning 1.
- No package-level install ledger. `deployed.json` records deployed _files_ only; nothing records
  "PULSE installed this package", so nothing can answer "what's installed that the manifest no
  longer declares".
- No unified update path. `inv apt.upgrade-debs` and `inv gnome.update` exist; apt itself, uv tools,
  npm globals, cargo, `script`/`archive`/`binary` installers, and Oh My Zsh have none.
- No `setup.toml` schema validation. The 15-method field reference lives in a header comment;
  mistakes surface at runtime, and the one place a typo is caught at all is `overrides.toml`'s
  unknown-package warning (`tasks/util.py:533-535`, whose own comment notes the file is "unvalidated
  by anything else").
- No survivability story for `~/.config/power-user-linux-setup/identity.toml` — machine-local,
  out-of-repo, unencrypted, uncommitted anywhere. See learning 5.

## The comparison set

- **Universal Blue — Bluefin / Aurora / Bazzite** (Fedora Atomic + bootc). Image-based, atomic,
  rebase-and-rollback. `bluefin-dx` adds ~67 dev packages over the base (~160 total: Docker, Podman,
  Incus, QEMU/libvirt, VS Code with devcontainers, GPU compute), and its stated design principle is
  that **the OS and the dev environment are explicitly separated** — tooling is containerized, in a
  VM, or scoped to `$HOME`. `ujust` (a `just` wrapper over ~80 recipes in
  `/usr/share/ublue-os/just/`, with `ujust --choose` and a `ugum` TUI picker) is its whole
  system-management UX. As of April 2026, "DX Next" is folding DX into the base image instead of
  shipping a separate one.
- **Fedora Silverblue / bootc**. The underlying mechanism: build the system as an OCI image, deploy
  atomically, roll back to the pinned previous deployment.
- **NixOS + home-manager**. The only project that closes the convergence loop properly: the config
  is the whole truth, generations are atomic, rollback is instant, and drift is structurally
  impossible.
- **openSUSE Aeon / MicroOS** (`transactional-update`, Snapper + btrfs). Snapshot-per-transaction
  with a bootable rollback path — the same guarantee as bootc, delivered on a mutable-looking distro
  instead of an image.
- **Omakub** (DHH/Basecamp). The closest peer by far: pure Bash, one command, turns fresh Ubuntu
  24.04 LTS into an opinionated web-dev workstation. Same target OS, same "one command from fresh
  install", same reason for existing (LTS-frozen versions and post-install steps upstream doesn't
  do). Differs in being a curated _taste_ for other people, not a personal machine's reproduction.
- **chezmoi**. Dotfiles with `verify`/`status`/`apply`, externals, and encrypted secrets in the repo
  via age/gpg/rage (`chezmoi add --encrypt`, decrypted on `apply`).
- **Ansible desktop playbooks**. The same imperative-idempotent model PULSE uses, with `--check`/
  `--diff` and a module ecosystem instead of typed Python tasks.
- **topgrade**. Probes for 60+ package managers and update sources and runs them all in one command
  (apt, snap, flatpak, pip/pipx, cargo, npm, gem, nix, editor plugins, JetBrains, GNOME, tracked git
  repos). Rust, static binary, 15.x as of mid-2026.
- **devcontainer Features / BlueBuild recipes**. Versioned, OCI-distributed, schema-validated
  install units — the packaging shape PULSE's 15 private methods deliberately don't have.
- **toolbx / distrobox / mise / devbox**. Per-project or containerized toolchains instead of
  host-global ones.

## Candidate learnings

Ranked by value-per-unit-of-work, not by how impressive the source project is.

### 1. A recovery boundary around `inv setup`

**They do:** bootc/Silverblue/Aeon/NixOS all make "the last known-good system state" a first-class,
one-command-away thing. Ubuntu's equivalent is Snapper or Timeshift, optionally hooked to
`DPkg::Pre-Invoke` so every `apt install`/`upgrade` gets a snapshot, with `grub-btrfs` putting
snapshots in the boot menu.

**PULSE has:** nothing. `inv setup` mutates a live machine across 15 install methods, several of
which are vendor `.deb`s and `curl | sh` installers, with dpkg as the only ledger and no way back.

**The learning:** not immutability — a _recovery boundary_. One optional snapshot taken before the
packages phase, and a documented way back. This is the single largest structural gap between PULSE
and every image-based distro, and the only one where the distro's advantage is a real safety
property rather than a packaging preference.

**Cost/constraint:** root is ext4 on LVM here, so btrfs/Snapper is off the table without a
reinstall. Realistic options: Timeshift in rsync mode (works on ext4, slow, needs space), an LVM
snapshot (root is already on `vgubuntu` — cheap, but needs free extents in the VG and is a manual
restore), or the honest minimum: a documented pre-run backup checklist and nothing automated. Worth
noting the failure mode PULSE actually has is _partial_ breakage of one tool, not an unbootable
system, which argues for a cheap boundary rather than an elaborate one.

[NEEDS CLARIFICATION: is a snapshot/rollback story wanted at all on a machine whose realistic
failure mode is "one vendor `.deb` misbehaves", or is the honest answer that reinstall-and-re-run-
PULSE _is_ the rollback story, and the gap is only that this isn't written down anywhere?]

### 2. Convergence: what's installed but no longer declared

**They do:** NixOS deletes what left the config. `ujust`/BlueBuild get it for free by rebuilding the
image.

**PULSE has:** additive-only installs, plus two partial precedents — `inv gnome.clean` (real
convergence, one method) and `inv apt.uninstall <section>` (`tasks/apt.py:389`, explicit, one
section at a time, apt-owned packages plus declared `cleanup_paths`).

**The learning:** generalize the `gnome.clean` pattern into a read-only report first:
`inv
setup.orphans` (name TBD) listing things PULSE installed that the current manifest no longer
declares — a package whose section was deleted, one turned off in `overrides.toml`, one now excluded
by tags. Reporting is most of the value; removal can stay per-section and explicit.

**Cost/constraint:** this needs the install ledger PULSE doesn't have. The mechanism already exists
one level over — `deploy.py`'s manifest-plus-ownership-marker design (`tasks/deploy.py:41-53`) is
exactly the right shape, and its central insight ("the marker says _whose is this_ and survives a
wiped state dir, the manifest says _what did we write, when_") transfers directly. Without a ledger,
the only alternative is heuristics over dpkg/uv/npm state, which will produce false positives
against base-system packages and should not be attempted.

[NEEDS CLARIFICATION: does the ledger belong in `deployed.json` (one state file, two record kinds)
or its own `installed.json`? The former keeps one manifest version to migrate; the latter keeps
"files PULSE wrote" and "packages PULSE installed" from sharing a schema they don't really share.]

### 3. One update path

**They do:** topgrade probes and updates everything. Image distros collapse it further: one
`bootc
upgrade`/`rpm-ostree upgrade` covers the entire system.

**PULSE has:** `apt.upgrade-debs` and `gnome.update`, and nothing for the other ~6 update surfaces a
PULSE machine accumulates (apt itself, uv tools, npm globals, cargo, script/archive/binary
installers, Oh My Zsh + plugins).

**The learning:** `inv update.all`, walking `setup.toml` by method — with a real advantage over
topgrade worth stating: **topgrade probes, PULSE declares.** PULSE knows which surfaces it owns and
which it doesn't, can respect `enabled`/tags/`overrides.toml`, and can dry-run the whole thing.
Adopting topgrade itself is the alternative (one `setup.toml` entry, zero maintenance, but it
updates things PULSE never installed and knows nothing about the manifest).

[NEEDS CLARIFICATION: `inv update.all` versus declaring topgrade and pointing at it — the tradeoff
is manifest-awareness and dry-run parity versus ~0 maintenance. Also unresolved: whether an update
run should end in `verify.all` (it should, probably — an upgrade that breaks a tool is exactly what
`verify.all` was built to catch).]

### 4. One health command, and finding things among ~110 tasks

**They do:** `ujust --choose` + `ugum` make ~80 recipes discoverable without memorizing any of them;
Bluefin's MOTD surfaces system state and tips at every shell.

**PULSE has:** excellent per-domain diagnostics (listed above) and good docs, but `inv --list` is a
110-line wall and the diagnostics are only findable by already knowing they exist. `next_steps.py`
covers the immediately-post-setup moment only.

**The learning:** two separable pieces, and the first is the valuable one.

1. **`inv doctor`** — run every read-only check in one pass (`deploy.status`, `verify.all`,
   `proxy.check`, `certs.check`, `gnome.status`, `allowlist.status`, `wsl.check` when applicable)
   and print one health summary. Everything needed already exists; this is composition, not new
   capability. It is also the natural home for learning 2's orphan report.
2. **Discoverability UX** — an interactive picker over the task list. Cheap to build, but PULSE is
   agent-driven far more often than it is human-driven at a prompt, and an agent reads `--list` or
   the docs perfectly well. Low value here; noted so it isn't confused with (1).

### 5. Identity/secrets survivability

**They do:** chezmoi keeps secrets _in the config repo_, encrypted with age/gpg/rage, decrypted on
`apply` — so one clone plus one key reconstitutes the machine.

**PULSE has:** `identity.toml` (git identities, SSH host list, proxy, CA bundle path) living only at
`~/.config/power-user-linux-setup/identity.toml`, unencrypted, out-of-repo, and — per
`plans/2026-08-24-machine-local-setup-toml-overrides.md` — not present at all on this machine today.
`overrides.toml` is now in the same position.

**The learning:** this is the one place where the README's stated purpose ("minimize the impact of
hardware failure... reproduce your setup on a new machine, with the least amount of manual
reconfiguration") has an actual hole. After a disk failure, everything in `setup.toml` comes back
and every machine-local file does not — `inv identity.init`'s wizard has to be re-answered from
memory. Options, cheapest first: document that these files need backing up (and where); an
`inv identity.export`/`import` pair; age-encrypted copies committed to the repo, chezmoi-style.

[NEEDS CLARIFICATION: is committing an age-encrypted `identity.toml` to a **public** repo acceptable
here, or does the machine-local material stay out of git on principle, making this a documentation +
export-helper problem rather than an encryption one?]

### 6. Host-global toolchains, and the narrow slice worth taking

**They do:** Bluefin's stated principle is that the OS and the dev environment are separate —
toolchains live in toolbx/distrobox containers or in `$HOME`, and per-project version managers
(mise, devbox) handle the rest.

**PULSE has:** Go, Rust, Node (via `nvm`, the one `nvm`-method package), and Python tooling
installed host-global.

**The learning — and the limit:** wholesale adoption is a non-goal. PULSE's entire value is that the
_host_ is the tuned artifact; moving toolchains into containers would make the thing it reproduces
less useful, and the container path already exists for when isolation is what's wanted
(`docs/dev-container.md`). The genuinely interesting slice is much narrower: **`nvm` is the weakest
installer in the manifest** — shell-sourced, slow to initialize, awkward outside an interactive
shell — and `mise` would replace it with a single binary that also covers Go and Rust toolchain
versions, XDG-clean, with no shell hook. That's a self-contained swap, not an architecture change.

[NEEDS CLARIFICATION: is `nvm` → `mise` worth doing on its own merits (shell startup time, one tool
for three runtimes), or is the current setup fine and this is churn? Needs a look at what actually
depends on `nvm`-specific behavior first.]

### 7. Manifest validation

**They do:** BlueBuild recipes are YAML validated against a published JSON Schema; devcontainer
Features have a schema and a version.

**PULSE has:** a 15-method field reference in `setup.toml`'s header comment, no validation, and one
lonely typo check in `load_overrides()` whose own comment says the file is "unvalidated by anything
else".

**The learning:** a typed model over `setup.toml` (the repo is already fully typed and
basedpyright-strict, so the shape exists implicitly in `tasks/util.py`'s TypedDicts) with a
`inv config.validate` — catching a misspelled field or a method/field mismatch at parse time instead
of three phases into a real run. Modest value, low cost, and it directly serves the "one manifest is
the whole truth" property the rest of the repo already leans on.

### 8. Deliberately not taken

Stated so they don't get re-proposed as "improvements":

- **Immutability / image-based root.** Would break every `apt`, vendor `.deb`, and `curl | sh`
  installer in the manifest — that unrestricted access to ordinary Ubuntu mechanisms _is_ the trade
  PULSE makes on purpose. Learning 1 wants the recovery property without this.
- **A Nix rewrite.** Buys real convergence and rollback at the cost of repackaging every vendor tool
  (Citrix, Webex, JetBrains Toolbox, corporate CA/proxy paths) that currently works unmodified.
- **Distributing PULSE as an image, or as a curated taste for others** (the Omakub/Bluefin move).
  PULSE reproduces _this_ machine; the container path already covers the "give someone else a
  working environment" case.
- **A features/plugin ecosystem** for the 15 install methods. Packaging overhead for a
  single-consumer repo.

## Recommended direction

Take the two that are pure composition of what already exists, and treat the rest as optional:

1. **`inv doctor`** (learning 4.1) — no new capability, immediate value, and the place learnings 2
   and 3 later report into.
2. **`inv update.all`** (learning 3) — the most-used missing verb on a machine that's been running a
   while.
3. **Identity survivability** (learning 5) — at minimum a docs fix, because the gap contradicts the
   README's stated purpose.
4. **Install ledger + orphan report** (learning 2) — the most architecturally interesting, and the
   one with a proven in-repo pattern to copy; still the biggest build.
5. **Recovery boundary** (learning 1) — highest theoretical value, most constrained by ext4-on-LVM;
   resolve its open question before doing anything.

Learnings 6 and 7 are independent small items that don't need this plan to happen.

## Sources

- [Bluefin Developer Mode](https://docs.projectbluefin.io/bluefin-dx/) ·
  [DX Next PR](https://github.com/projectbluefin/common/pull/288) ·
  [ujust recipe system](https://deepwiki.com/ublue-os/bazzite/4-ujust-recipe-system)
- [home-manager](https://github.com/nix-community/home-manager)
- [chezmoi encryption](https://www.chezmoi.io/user-guide/encryption/age/) ·
  [`chezmoi verify`](https://mintlify.wiki/twpayne/chezmoi/commands/verify)
- [Omakub](https://omakub.org/) · [basecamp/omakub](https://github.com/basecamp/omakub)
- [topgrade](https://github.com/topgrade-rs/topgrade)
- [Timeshift/Snapper + `DPkg::Pre-Invoke` on Ubuntu](https://www.lorenzobettini.it/2022/10/timeshift-and-grub-btrfs-in-ubuntu/)
