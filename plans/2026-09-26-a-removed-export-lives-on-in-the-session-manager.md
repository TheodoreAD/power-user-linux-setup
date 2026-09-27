---
status: landed
updated: 2026-09-28
source_repo: github.com-personal/agent-skills
source_session: background job 1767aa06 (session id prefix 1767aa06-adb)
source_moment: 2026-09-26T14:30:00+03:00
source_plan:
---

# A removed export lives on in the session manager until re-login

**This reports a fact rather than proposing a design owned elsewhere**, so `source_plan` is blank.

## Context

`240721b` (2026-09-19) deleted the machine-wide `UV_PYTHON="3.14"` export and replaced it with a uv
global pin, precisely because the variable outranks every project's `.python-version` and
`requires-python`. The dotfile change was correct and complete. **The running desktop session never
heard about it.**

## Evidence

Measured 2026-09-26 from an agent-skills session that found `UV_PYTHON=3.14` in its own environment
a week after the removal:

- No file sets it: `~/.zshenv`, `~/.zshrc`, `~/.zprofile`, `~/.profile`, `~/.bashrc`,
  `/etc/environment` and `/etc/profile.d` all clean; `~/.config/environment.d` does not exist.
- `systemctl --user show-environment` lists `UV_PYTHON=3.14`.
- Walking `/proc/*/environ` for the topmost carrier of each chain: `gnome-session-binary`, started
  **2026-08-31 23:00**, before the removal. GNOME imported the login shell's environment into the
  systemd user manager at login, and everything since inherits it: terminals, and the Claude Code
  daemon (started 2026-09-26 11:49, from a session that inherited it), so every background agent
  session it spawns.
- Consequence observed the same day: `inv venv.recreate` and `uv add` in agent-skills would have
  rebuilt its venv at 3.14 over the new 3.11 `.python-version`, silently. Every call that builds a
  venv had to be run as `env -u UV_PYTHON …`. The plan that announced the removal already carried a
  pitfall for "a shell started before 2026-09-19"; the scale was larger than a shell — it was the
  whole login, for a week.

[PITFALL: **deleting an export from a dotfile is not deleting it from the machine.** The value stays
in the systemd user manager (and D-Bus activation environment) of the current login, and in every
long-lived process started from it, until logout. A deploy whose point is removing a variable
therefore finishes only on the next login, and nothing says so.]

## Open questions

[DECISION: unset and report, the user's choice on 2026-09-28. This reverses a "report only" choice
made an hour earlier on a false premise: that a re-login finishes the job.]

[PITFALL: **a re-login does not reset the systemd user manager, and the next login inherits from
it.** The manager is per-user and runs until every session has ended. Measured 2026-09-28: the
manager had run since 08-28, the previous session was still `closing` in `loginctl` (a Claude daemon
held it), and the `gnome-session`, `gnome-shell` and WezTerm of a login made at 00:04 that day all
carried `UV_PYTHON=3.14`. So `unset-environment` is the fix that reaches the next login, and
re-login alone is advice that fails silently. Running processes still keep their copy.]

## Recommended direction

When a PULSE deploy removes an exported variable, have it print one line saying the running login
still carries it and that a re-login finishes the change — optionally running the
`systemctl --user unset-environment` half. A generic form: compare
`systemctl --user
show-environment` against the variables PULSE declares, and report ones PULSE used
to set and no longer does.

Filed from an agent-skills session, which does not edit this repo.

## Migrated to

- **The behaviour, with both pitfalls and the decision**: `tasks/zsh.py`,
  `_clear_lingering_exports`'s docstring, `241b686`. `configure` diffs each dotfile's exported names
  before and after its rewrite, then unsets any the user manager still carries, and reports what
  keeps its copy. Four tests are in `tests/unit/test_zsh.py`.
- **Deliberately narrower than the "generic form" above**: no machine-wide scan for variables PULSE
  used to set. The removal is only knowable at the moment `configure` performs it. `UV_PYTHON`
  itself predates the code, so it was cleared by hand with the user's approval on 2026-09-28
  (`systemctl --user unset-environment UV_PYTHON`, confirmed gone).
- **The Claude daemon side**, meaning background sessions that keep the stale copy and a dead SSH
  socket: the store plan `2026-09-28-claude-daemon-outlives-relogin-with-a-dead-ssh-socket.md`,
  filed for this repo by another session. It is not absorbed here.
