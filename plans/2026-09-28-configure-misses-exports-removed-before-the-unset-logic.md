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

**Found, same day: `gnome-session` re-uploads its environment when it exits.** In 46.0,
`gnome-session/main.c` ends:

```c
        gsm_main ();

        gsm_util_export_user_environment (NULL);
```

`gsm_util_export_user_environment` sends the process's whole environment to the manager through
`UnsetAndSetEnvironment`, so the session manager restores at logout whatever it held at login. The
timeline fits every observation:

- 00:04. That login's `gnome-session-manager@ubuntu.service` started with `UV_PYTHON`, because the
  manager still had it.
- 01:13. The unset removed it from the manager, but not from the running session manager.
- 12:49:18. After the shell crash, the journal records
  `Stopped gnome-session-manager@ubuntu.service`. Its exit path re-exported `UV_PYTHON`, and the
  session bus restarted by `gnome-session-restart-dbus` in the same second carries it.
- 14:01. The next session manager inherited it from the manager. The current one,
  `gnome-session-binary --systemd-service` (pid 2058639), carries it now, so it will do the same at
  the next logout.

**This changes the design, not just the diagnosis.** An unset made during a session is undone at
that session's logout, so unsetting at every `configure` fails for the same reason the one-off did.
The unset has to run **before the session manager starts**, so that it never holds the variable and
has nothing to re-export. That means a user unit in `graphical-session-pre.target` (or ordered
`Before=gnome-session-manager@.service`) that unsets the declared retired exports. The alternative
is to unset after the manager exits, at `gnome-session-shutdown.target`, but that misses a crash
that skips an orderly stop. It also means the variable leaves only at the **second** login after the
fix is deployed, unless the user unsets it and then logs out from outside the graphical session.

The search that led here, and what it ruled out along the way: The premise holds: session `b73129dd`
ran `systemctl --user unset-environment UV_PYTHON` at 01:13, and its own `show-environment` read the
variable present at 01:08 and absent at 01:13. Ruled out for the 01:48–12:49:17 window:

- Agent sessions. No transcript modified in the last two days holds a tool call running
  `import-environment`, `set-environment`, `dbus-update-activation-environment`, `gnome-session`,
  `dbus-run-session`, `dbus-launch`, `startx`, `xinit`, `Xvfb`, `busctl --user call` or `gdbus call`
  in the window. The one environment call anywhere was the unset.
- Claude Code. The 2.1.283 binary contains none of those strings, and `~/.claude/daemon.log` has no
  systemd interaction.
- The manager itself. No re-exec, reload or apt upgrade appears in the system journal, which is
  readable for that window. The user manager logged nothing between 00:06 and the crash, which fits
  an idle overnight desktop.
- Units and scripts. No user unit, `/etc/xdg` entry or autostart imports the environment.
  `/etc/xdg/Xwayland-session.d` does not either. `/etc/X11/Xsession.d/95dbus_update-activation-env`
  (`--systemd --all`) runs only in X sessions. `gnome-session-ctl --restart-dbus`, which ran at
  12:49:18, only restarts the unit (46.0 source, `tools/gnome-session-ctl.c`).
- GNOME's own export. On this machine only `/usr/libexec/gnome-session-binary` references systemd's
  `SetEnvironment`. In 46.0 it uploads its whole environment through `UnsetAndSetEnvironment` once,
  at start (`gnome-session/main.c:639`, `gsm_util_export_user_environment`). The only gnome-session
  that started in the window was GDM's greeter at 12:49:20, which belongs to the `gdm` user's
  manager.

The journal could not settle it, because `SetEnvironment` calls are not logged. Reading the whole of
46.0's `main.c` did, and found the exit-time export above: the first read had stopped at the
start-time call. The source clone is `$RESEARCH_HOME/repos/gitlab.gnome.org--GNOME--gnome-session`
with the `46.0` tag fetched.

[UNVERIFIED: **the mechanism is read from source and fits the timeline, but has not been watched
happen.** To confirm it: unset `UV_PYTHON` while logged in, check that it stays absent for the rest
of the session, then log out and back in and check that it is present again. If it reappears before
the logout, something else is also exporting it.]

It also bears on `tasks/claude_daemon.py`: stopping a stale daemon does not clear this variable,
because the next daemon starts from a shell of the new login, which inherits it from the manager.

## Open questions

[DECISION: **a mechanism, not a one-off, and the one-off is refuted rather than merely weaker.** The
01:13 one-off was undone by the session manager's exit-time export at the next logout. A declared
list of retired exports, starting with `UV_PYTHON`, keeps `5065fea`'s rule: nothing is unset that
PULSE never exported.]

[NEEDS CLARIFICATION: **where the unset runs.** It must run before `gnome-session-manager@.service`
starts, or the session manager holds the variable and re-exports it at logout. Candidates:

- a user unit wanted by `graphical-session-pre.target`, deployed like other PULSE files;
- the same unset also left in `zsh.configure`, which does no harm but on its own does nothing
  lasting;
- `gnome-session-shutdown.target`, after the manager exits, which misses a crash that skips an
  orderly stop.

The first is the only one that holds by construction. Who owns the declared list, `setup.toml` or
`tasks/zsh.py`, is part of the same decision.]

## Recommended direction

Declare the retired exports, and unset them from a user unit that runs before the GNOME session
manager starts. A variable is then gone from the second login after deploy. `configure` can keep its
unset for the current session's new processes, but its message must stop implying that a re-login
finishes the job. Whatever else changes, the message should keep saying that running processes,
including the Claude daemon's jobs, keep their copy until restarted.
