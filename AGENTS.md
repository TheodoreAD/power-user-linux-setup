# Agent instructions for power-user-linux-setup

Cross-tool instructions for AI coding agents working in this repo (Claude Code, and anything else
that reads `AGENTS.md`). Claude Code specifically loads this via a `@AGENTS.md` import in
`CLAUDE.md` — see that file's docs for why.

## Memory policy

Don't use Claude Code's cross-session memory system (`~/.claude/projects/.../memory/`) for durable
knowledge about this project. Put it here instead, or in a `docs/*.md` file with a pointer from
here. Reasons: this file is version-controlled, visible to every contributor and every agent tool
(not just Claude), and reviewable in diffs — the memory system is none of those.

## PULSE tag/method architecture

The `setup.toml` config/tag system is fully documented in the repo — don't re-derive it by reading
`tasks/*.py` from scratch:

- `setup.toml`'s header comment — field reference for every method (`apt`, `apt-repo`,
  `deb-github`, `deb-url`, `archive`, `uv-tool`, `nvm`, `script`, `binary`, `git-clone`,
  `wrapper-script`, `gnome-extension`, `apparmor-profile`, `zsh`), plus the tag catalog.
- `docs/configuration.md`, section "Tags, `enabled`, and which tasks actually respect either" —
  which tasks go through `util.packages_by_method()` (tag+enabled aware) vs which read a
  `[packages.*]` section directly and ignore tags (`node.install`, `docker.configure`, `fonts.*`)
  or ignore tags but not `enabled` (`zsh.configure`'s `zshrc`/`zshenv`/`zprofile` writer).

Only 7 tags actually gate anything: `gui`, `desktop`, `gnome`, `workstation`, `corporate`, `ide`,
`windows-native`. Everything else in the tag catalog is organizational only. Building an
environment profile (headless, dev container, WSL) by setting `PULSE_EXCLUDE_TAGS` alone is not
sufficient — check the docs/configuration.md table for what each task actually respects before
assuming.

## WSL support

`tasks/wsl.py` (`inv wsl.check` diagnostic, `inv wsl.fix` for the fixable subset —
`systemd`/`generateResolvConf` in `/etc/wsl.conf`) and `docs/wsl.md` already cover running this
repo's setup under WSL2 — distro/apt check, systemd, DNS, Docker Desktop-vs-native, WSLg, fonts.
`util.require_systemd()`/`util.require_apt()` (`tasks/util.py`) make the systemd- and apt-dependent
install tasks fail fast with an actionable message instead of partway through a raw error; these
are generic capability checks, not WSL-specific branching. If asked about WSL support again, extend
that module rather than re-researching from scratch.

## Git workflow

Direct, focused commits straight to `master` are the normal way to land changes here — the owner
has bypass permissions on the PR-required branch protection rule specifically for this. Open a PR
instead only when either (a) someone other than the owner is contributing, or (b) a batch of
related commits is worth bundling behind a PR description for reviewability. Don't default to
"always open a PR" — ask if unsure which case applies, don't assume the stricter workflow.
