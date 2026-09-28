---
status: idea
updated: 2026-09-28
source_repo: github.com-personal/scaffoldapy
source_session: 81492b4f-e6bc-4577-8d01-412b3ff4e7a9.jsonl
source_moment: 2026-09-28
source_plan: plans/2026-09-18-python-version-tier-rules.md (scaffoldapy; step 1 of its recommended direction)
---

# `zsh.configure`'s unset never reaches `UV_PYTHON`, the export that motivated it

## Context

`241b686` (2026-09-28 01:10) made `zsh.configure` unset, from the systemd user manager, any export
its dotfile rewrite drops. Its commit message names `UV_PYTHON=3.14` as the measured case: removed
from the dotfiles on 09-19, still in the manager, inherited by a fresh GNOME login.

**That variable is exactly the one the new code cannot catch.** `_unset_lingering` works on `gone`,
the names that disappear _during this run's_ rewrite (`tasks/zsh.py:147-156`). `UV_PYTHON` left the
dotfiles nine days before the logic existed, so no future `configure` sees it drop, and it survives
every deploy. `5065fea` records the narrowing as deliberate ("no machine-wide scan for variables
PULSE ..."), which is a fine rule for the steady state. The one pre-existing instance was left for
nobody.

Filed from scaffoldapy rather than fixed, since writing into another repo's tree is out. The machine
was deliberately left untouched: the user chose to file only.

## Evidence

Measured 2026-09-28 from a scaffoldapy session, read-only:

- `systemctl --user show-environment` lists `UV_PYTHON=3.14`.
- A fresh `env -i HOME=... zsh -l -i` has it **unset**, so the dotfiles are clean.
- No `~/.claude/shell-snapshots/*` carries it. The agent shell gets it from the process tree: the
  manager → the long-lived Claude daemon → every background job.
- `~/.config/uv/.python-version` holds `3.14`, so the replacement (`uv python pin --global`) is in.
  Only the removal is incomplete.
- `uv python find --show-version` in that agent shell: `3.14.5`, with the variable still outranking
  every declared floor. scaffoldapy's tier-rules plan names this as the precondition for everything
  else in it.

**Added on absorption, 2026-09-28: it was gone, and it came back.** A session in this repo checked
`systemctl --user show-environment | rg UV_PYTHON` at 01:48 local and got nothing. By 14:08 this
plan's own filing saw `UV_PYTHON=3.14`, and at absorption it was still there. Narrowed:

- The user manager (pid 2376) has run since 2026-08-28 and was never restarted, so nothing reset it.
- No login source defines it: `~/.zshenv`, `~/.zprofile`, `~/.zshrc`, `~/.profile`, `~/.bashrc`,
  `/etc/environment`, `/etc/profile.d`. `~/.config/environment.d` and `~/.pam_environment` don't
  exist.
- It was back in the manager by **12:49:17**. That is when `gnome-session-restart-dbus` restarted
  the session bus after GNOME Shell crashed (`signal 11`, 12:48:59), and the new `dbus-daemon` (pid
  2043271), which takes the manager's environment, carries it.
- The login at 14:01 then inherited it. `gdm-wayland-session` does **not** carry it, but
  `gnome-session-binary`, one step below, does, and so do `gnome-shell`, `wezterm-gui` and every
  shell under them.
- Nothing in this repo pushes environment into the manager. The only `systemctl --user` environment
  call in `tasks/` is `_clear_lingering_exports`'s unset. The user journal names no import between
  01:40 and 14:05.

So the re-importer ran between 01:48 and 12:49 and is **not identified**. The likeliest is a
long-lived process that still held the variable and re-exported its whole environment: the 00:04
login's GNOME session inherited it from the manager before the 01:10 unset. That is unconfirmed.
Either way it settles the question below: **a one-off `unset-environment` does not stick** while any
older process can re-export, so only a mechanism that runs at every `configure`, and ideally every
login, keeps it out.

It also bears on `tasks/claude_daemon.py`: stopping a stale daemon does not clear this variable,
because the next daemon starts from a shell of the new login, which inherits it from the manager.

## Open questions

[NEEDS CLARIFICATION: one-off or mechanism? A one-off:
`systemctl --user unset-environment UV_PYTHON` once, noted in the plan that retires this. A
mechanism: `configure` also unsets any name in a small declared list of "exports this repo used to
own" (a retired-exports table in `setup.toml` or `tasks/zsh.py`), which catches the historical cases
without the machine-wide scan `5065fea` ruled out. The list is cheap and stays empty most of the
time.]

## Recommended direction

Declare retired exports and have `configure` unset any the manager still carries, starting with
`UV_PYTHON`. That keeps `5065fea`'s rule (nothing unset that PULSE never exported) and closes the
gap for the case that prompted the fix. Whichever way it goes, the message should keep saying that
running processes, the Claude daemon's jobs included, keep their copy until
`claude daemon stop --any`.
