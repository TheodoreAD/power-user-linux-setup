---
status: idea
updated: 2026-11-26
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

## Open questions

- **Answered 2026-11-26** by win-configs `herdr/README.md` ("On Linux", commit 3b3ad60): the channel
  is `curl -fsSL https://releases.herdr.dev/app/install.sh | sh` (x86_64 and arm64, needs curl and
  tar, no root). It installs to `~/.local/share/herdr-app`, puts `herdr-app` in `~/.local/bin` plus
  a launcher entry, installs `herdr-core` and `hc` to `~/.local/bin` if they are missing, and
  updates the app when re-run. That is a `curl | sh`, which the house rule forbids as a one-off, so
  the question is which PULSE `method` can wrap it: a pinned, reviewed copy of the script, or the
  tarball the script downloads. Read the script before choosing.
- The same README section carries Herdr's settings, the Estro layout and the mods for Linux, marked
  "Not tested on Linux yet". It needs git, gh, Go, python3 and the Nerd Font from PULSE. Whether
  PULSE or win-configs should own that block is the README's own open point.
- The skill's install line changed in win-configs bfe6bf0 to `-a universal claude-code -g -y` (a hub
  copy in `~/.agents/skills` plus a link in `~/.claude/skills`). The `-a claude-code` form used on
  2026-11-26 predates it, which is why that install landed as a plain copy. **As of 2026-11-27 it
  sits in the hub**: `~/.agents/skills/herdr-remote` is a real copy and
  `~/.claude/skills/herdr-remote` links to it. It is still not in `setup.toml`
  (`rg -i 'herdr|win-configs' setup.toml`: no hits), so the next machine does not get it.
- Should `[[ssh_hosts]]` grow per-host options and an explicit key path, so herdr controller entries
  can be declared too? Probably YAGNI while there's one controller.

## Recommended direction

Add `herdr-remote` (source `TheodoreAD/win-configs`) to the skills `setup.toml` installs, then
re-run `inv ai.install-skills` and remove the hand-installed copy if the installer puts it in the
hub. Add a `[packages.herdr-app]` entry using whatever channel herdr.dev documents for Linux.
