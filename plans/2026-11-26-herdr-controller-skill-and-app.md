---
status: in-progress
updated: 2026-11-27
source_repo: github.com-personal/agent-skills
source_session: 65662eda-633f-45c8-b021-13e6247e9fc4.jsonl
source_moment: 2026-11-26
source_plan:
---

# Herdr controller: declare the herdr-remote skill and the Herdr desktop app

## Context

This Linux machine is being set up as the Herdr controller for a Windows PC and its WSL distro,
following the `herdr-remote` skill from `TheodoreAD/win-configs` (default branch `main`). Two things
that setup needs were missing from this machine and from `setup.toml`:

1. **The `herdr-remote` skill.** Not declared in `setup.toml`, so `inv ai.install-skills` can't
   install it. It was installed by hand on 2026-11-26 with
   `npx skills add TheodoreAD/win-configs --skill herdr-remote -a claude-code -g -y`. That command
   copies it straight into `~/.claude/skills/herdr-remote`, not into the `~/.agents/skills` hub, so
   the hand install doesn't follow the usual layout either.
2. **The Herdr desktop app** (`herdr-app`, plus `hc` and `herdr-core`). It isn't installed anywhere
   on PATH, /opt, /usr or ~/.local. `herdrdev/herdr-app` publishes no GitHub releases
   (`package_health.py github herdrdev/herdr-app`: 0 releases, tags only; Apache-2.0; bus factor 1;
   pushed daily). The skill says to install it from herdr.dev, so the delivery channel is herdr.dev
   rather than a GitHub release.

The rule in force is that every tool is a `[packages.<name>]` entry, never a one-off install, and
skills go through `setup.toml` so the next machine gets them.

## Evidence

- `fd -i herdr /opt /usr/bin /usr/local/bin ~/.local /usr/share/applications`: no hits.
  `command -v hc herdr-app herdr-core`: exit 1.
- `rg -i 'win-configs|herdr' setup.toml`: no hits.
- The doctor (`herdr-remote.py doctor --host <windows-host>`) reports `FAIL hc on PATH — not found`.
- The user chose "file a plan, carry on with the steps that don't need local hc".

Also of note for `[packages.ssh]`: the controller's `Host <windows-host>` block was **appended by
hand** to `~/.ssh/config`, outside the PULSE sentinel block. `identity.toml`'s `[[ssh_hosts]]` can't
express it: it names keys per email (`<email>__<node>_ed25519`, where herdr needs
`id_ed25519_<windows-host>`), and it has no `IdentitiesOnly`/`ForwardAgent no`/`ForwardX11 no` per
host. `ensure_block` leaves hand-written blocks alone, so nothing breaks, but a second machine won't
get the block. Whether that matters depends on whether a second Linux controller is planned.

## Landed 2026-11-27

- **The app**: `[packages.herdr-app]`, method `script`, from herdr.dev's installer. Both it and the
  herdr-core installer it chains were read first: no root, XDG paths, a sha256 from the release
  manifest. `inv tools.install` put Herdr 0.1.18 and hc 0.1.22 here. The question this plan asked, a
  pinned copy of the script or the tarball, came out as neither: the `script` method is the declared
  wrapper the repo already uses for the same shape (Claude Code, dprint, rustup).
- **Telemetry, pinned off at the user's request**: the app sends a daily usage report by default;
  `zshenv = "export HERDR_TELEMETRY=0"` on the package. herdr-core sends none. The reasoning, and
  why the app's own `settings.json` key is not written, is in the package's comment.
- **The skill**: `[packages.herdr-remote]`, `names = ["herdr-remote"]` from
  `TheodoreAD/win-configs`, installed through `inv ai.install-skills --skill=herdr-remote` as a hub
  copy plus a Claude link.

## Still open

- **Confirm telemetry is off on the first launch**: Settings → Privacy. The seeded `settings.json`
  (`config/herdr-app/settings.json`, win-configs' file minus `zoom`) was in place before the app
  ever started, so every launch reads `"telemetry": false`. A dock launch before the next login
  lacks `HERDR_TELEMETRY` but not the setting.
- **The Estro layout and the mods** in win-configs' `herdr/README.md` ("On Linux") are not deployed.
  That is third-party JavaScript at two pinned commits, security-reviewed for Windows on 2026-11-23,
  plus a Go build and a local patch, marked "Not tested on Linux yet". Better Files' open/reveal
  actions call macOS commands. Whether PULSE or win-configs owns it, and whether it becomes a task
  at all, is the README's own open point, waiting on the user.
- Should `[[ssh_hosts]]` grow per-host options and an explicit key path, so herdr controller entries
  can be declared too? Probably YAGNI while there's one controller.
- `[packages.herdr-app]` installs once and never updates the app, because the `script` method skips
  a package whose `check_cmd` exists. The app updates itself in the background, so this matters only
  if that updater is ever turned off.
