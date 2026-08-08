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
- `docs/index.md`, section "Tags, `enabled`, and which tasks actually respect either" — which
  tasks go through `util.packages_by_method()` (tag+enabled aware) vs which read a `[packages.*]`
  section directly and ignore tags (`node.install`, `docker.configure`, `fonts.*`) or ignore tags
  but not `enabled` (`zsh.configure`'s `zshrc`/`zshenv`/`zprofile` writer).

Only 5 tags actually gate anything: `gui`, `desktop`, `gnome`, `workstation`, `corporate`.
Everything else in the tag catalog is organizational only. Building an environment profile
(headless, dev container, WSL) by setting `PULSE_EXCLUDE_TAGS` alone is not sufficient — check
the docs/index.md table for what each task actually respects before assuming.

## WSL support

`tasks/wsl.py` (`inv wsl.check`) and `docs/wsl.md` already cover running this repo's setup under
WSL2 — distro/apt check, systemd, DNS, Docker Desktop-vs-native, WSLg, fonts. If asked about WSL
support again, extend that module rather than re-researching from scratch.
