---
status: in-progress
updated: 2026-09-28
source_repo: github.com-personal/invoke-stubs
source_session: 76d98521-8e7c-4524-bb4f-4caeb36e8cb0.jsonl
source_moment: 2026-09-28
source_plan:
---

# The Claude daemon outlives a re-login, so background sessions keep a stale environment and a dead SSH socket

**This reports a fact**, so `source_plan` is blank. It extends
`plans/2026-09-26-a-removed-export-lives-on-in-the-session-manager.md` rather than editing it: that
plan's recommended fix is "a re-login finishes the change", and this is the measurement showing that
for background agent sessions a re-login does not.

## Context

The user logged out and back in on 2026-09-28 around 00:04, and then asked why `git push` had
started failing. Every background agent session is a child of one `claude daemon run` process, which
was started 2026-09-26 11:49 from a Claude session inside a WezTerm window opened 2026-08-31. That
daemon was still running after the re-login, and so was the old login session (`loginctl`: sessions
`3` and `5690`, `Linger=no`). The daemon keeps that session alive, the environment it copied on
09-26 survives, and every background session it spawns afterwards inherits that copy.

## Evidence

From `/proc/<daemon pid>/environ`, read from a background session spawned 2026-09-28 00:07, after
the re-login:

- `SSH_AUTH_SOCK=/run/user/1000/wezterm/agent.2955010`. WezTerm publishes a per-GUI-process agent
  symlink pointing at the keyring agent. GUI 2955010 died at logout, so its symlink is gone, and
  `/run/user/1000/wezterm/` now holds only `agent.1034543` (the new GUI) and `agent.498484`. So
  **every ssh call from a background session fails with "Permission denied (publickey)"** while both
  real agents hold keys. `inv ssh.check` said so correctly: "this shell's agent has no keys but
  /run/user/1000/keyring/ssh does".
- `UV_PYTHON=3.14`, nine days after `240721b` removed it and after a re-login. The session had to
  run every uv-touching task as `env -u UV_PYTHON inv …` to hold a 3.11 `.python-version`.
- `PWD`, `VIRTUAL_ENV` and the front of `PATH` all name `ingesta/.venv`, from the repo the daemon
  happened to be started in. The per-call direnv hook in `~/.zshenv` corrects `PATH` for the
  session's own repo, but a tool that resolves Python by some other route still found the wrong
  environment: `basedpyright --verifytypes` in a scratch venv kept resolving the session repo's
  `.venv` until `PATH` was overridden explicitly.

`~/.zprofile`'s agent selection cannot help, because agent Bash calls run non-login shells that
source `~/.zshenv` only. So the inherited `SSH_AUTH_SOCK` is never re-chosen.

**It recurs on every re-login, not only after a dotfile change.** WezTerm's agent link is named
after its GUI process (`agent.<pid>`), so a daemon started from any WezTerm carries a link that dies
at the next logout, while the daemon itself survives. Also measured: the daemon keeps pre-started
spare workers (eight of them here, the oldest from 09-26) that were forked with the same
environment. A new background job claims one of those, so a job started after the re-login still
inherits the stale copy. That is how this session got it.

How the daemon can be stopped, from `claude daemon --help` on 2.1.283: `claude daemon stop --any`
shuts down a transient daemon and terminates its background sessions, and `--keep-workers` leaves
them running. The help also says service install is disabled and the daemon "runs on demand and
exits when the last client disconnects", so the next background job starts a fresh one with the
current environment.

## Design

Settled with the user 2026-09-28: two parts, and **nothing kills the daemon automatically**.

### 1. `~/.zshenv`: re-pick the SSH agent when the inherited one is dead

In the block agent shells already run, when the inherited `SSH_AUTH_SOCK` does not answer
`ssh-add -l`, run the same keyring/gcr selection loop `~/.zprofile` uses for login shells. A healthy
shell is untouched, since the loop runs only after that probe fails. This fixes pushes whatever the
daemon's age, including in the window between a re-login and whenever the old daemon is stopped.

**Landed 2026-09-28** as `[packages.ssh]`'s `zshenv`, beside the `zprofile` loop it mirrors rather
than inside `[packages.claude-code]`'s block, so the socket list stays in one package;
`tests/unit/test_ssh.py` pins all three copies and runs the snippet against real throwaway agents.
Verified live: a nested agent shell handed `/run/user/1000/wezterm/agent.2955010` came up on
`keyring/ssh` and `git ls-remote origin` succeeded.

### 2. At login, report an old daemon and offer to stop it

Detect a `claude daemon run` process that started before the current graphical login, and report it
rather than acting. The report names how many real jobs are running under it (pty hosts with
`--session-id`, as opposed to the `--bg-spare` ones).

**Landed 2026-09-28** as `[packages.claude-daemon-notice]`: `tasks/claude_daemon.py`, stdlib-only
like `netdoctor`, deployed as a copy to `~/.local/bin/claude-daemon-notice`, and an autostart entry
that runs it with `--notify` 15 seconds into each graphical login. The notification offers **Stop it
(ends N jobs)** and **Leave it**. Only the click runs `claude daemon stop --any`, and it re-checks
first that the same daemon is still the only stale one. The design is in the module docstring.

Three things changed from the draft above while building it:

- **The notice no longer mentions the SSH agent**, since part 1 repairs that per call. What is left
  is the environment in general, and the fact that windows opened in the new login attach to the old
  daemon too. `claude daemon status` showed two `claude agents` clients started after the re-login
  that were holding the old daemon open.
- **A job's pty host retitles itself**, so its `argv[0]` is the single element `claude bg-pty-host`.
  The first version tested for `bg-pty-host` as its own element and reported "no background jobs"
  against a daemon that was running one. It now matches the `--bg-pty-host` flag. The tests use argv
  bytes read from the live processes.
- **The session start comes from logind in microseconds**
  (`busctl get-property … session/auto …
  Timestamp`), and the daemon's start from
  `/proc/<pid>/stat` plus `btime`. Neither involves parsing a date, so the locale cannot affect the
  comparison.

[UNVERIFIED: **the notification itself has not been seen.** Report mode ran live against the real
stale daemon (pid 3454123, started 2026-09-26 11:49, one job), both from the checkout and from the
deployed copy on PATH, and `desktop-file-validate` accepts the autostart entry. `--notify` was not
run, because clicking Stop would end another session's live job (`76d98521`). The first real test is
the next login, or `claude-daemon-notice --notify` run on purpose.]

[DECISION: report, never kill. Rejected killing at login because it ends background jobs mid-command
(a push, a commit, a venv rebuild cut off halfway), and "the daemon is from an older login" cannot
tell work you left running on purpose from leftovers. Also rejected: killing only when idle (spares
only). That is safer, but the user chose to keep a human in the loop entirely.]

[PITFALL: "before the current login" must be judged against the **graphical** session's start time,
compared by timestamp. An SSH or console login is also a login, and a check keyed on "any login"
would flag, or under an automatic design kill, the daemon serving the desktop's jobs. It also has to
compare start times rather than test whether any daemon exists, or it flags a fresh daemon started
seconds after login.]

## Open questions

[DECISION: **a desktop notification with a Stop button, chosen by the user 2026-09-28.** The
alternatives were the first interactive shell of the login (once, with a marker under
`$XDG_RUNTIME_DIR`), a text-only notification, or both. The shell lost because the user does not
type shell commands, so a copyable command in a terminal is a step they would not take. A button
keeps the human decision the "report, never kill" choice asked for and makes that decision one
click. `notify-send -A` (libnotify 0.8) blocks until the notification is answered or dismissed. A
dismissal stops nothing.]

[DECISION: **written against 2.1.283, and the button is gated on the help text.** Before offering
Stop, the script runs the daemon's own binary with `daemon --help` and requires both `stop` and
`--any`. If either is missing, the notification still informs but offers no button, and names the
version it was written for. The draft said to stay silent in that case. It was changed because the
stale environment is still worth knowing about when the command has moved. With two stale daemons it
also informs without a button, since `stop --any` names no pid.]

## Recommended direction

Part 1 first: it is small, and it fixes the user-visible failure. Part 2 after. Both have landed.
The third step, naming the Claude daemon where the 2026-09-26 plan's fix says a re-login finishes
the change, was already done when that plan retired: `tasks/zsh.py`'s `_clear_lingering_exports`
says a re-login cannot touch running processes, "including background agent sessions under an old
daemon". What is left is the `UNVERIFIED` notification above.
