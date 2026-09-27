---
status: idea
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

### 2. At login, report an old daemon and print how to stop it

Detect a `claude daemon run` process that started before the current graphical login, and print a
notice rather than acting. The notice names how many real jobs are running under it (`bg-pty-host`
children with `--session-id`, as opposed to the `--bg-spare` ones), and gives the command:

```
A Claude daemon from your previous login (started <date>) is still running <N> background job(s).
Its jobs carry that login's environment: an SSH agent link that no longer exists and any variables
your dotfiles have since dropped. Once those jobs finish, stop it with:
    claude daemon stop --any
The next background job starts a fresh one.
```

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

[NEEDS CLARIFICATION: where does the notice appear? A graphical login has no terminal. Candidates:
the first interactive shell of the login (once, with a marker under `$XDG_RUNTIME_DIR`, which is
cleared at logout), a desktop notification via `notify-send` from an autostart entry, or both. The
shell is where the command can be copied from, and the notification is what gets seen if no terminal
is opened for a while.]

[NEEDS CLARIFICATION: `claude daemon` is Claude Code's own and its subcommands are version-specific
(checked on 2.1.283). Part 2 should state the version it was written against, and fail quietly (no
notice) rather than print a stale command if `claude daemon --help` no longer lists `stop`.]

## Recommended direction

Part 1 first: it is small, and it fixes the user-visible failure. Part 2 after. Then, in the
2026-09-26 plan's fix, name the Claude daemon as one of the long-lived processes a re-login does
**not** replace, so "re-login finishes it" stops being advice that fails silently for agent
sessions.
