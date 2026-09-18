# How this repo's environment reaches a process

Design rationale for the one assumption most of `setup.toml` rests on without saying so: that a
`zshenv` snippet reaches whatever needs it. Retired out of
`plans/2026-08-24-environment-d-session-env.md`, whose proposal — adopt `~/.config/environment.d/`
as a second surface — turned out to answer a problem that is not there. `docs/zsh.md` is the
user-facing page; this is why.

## The chain, end to end

`~/.zshenv` is read on **every** zsh invocation: login, interactive, non-interactive, `zsh -c`.
Nothing else in a shell's startup sequence has that property, and several things depend on it —
`[packages.claude-code]`'s `PIPE_FAIL` snippet applies to an agent's non-interactive Bash calls, and
`inv certs.install`/`inv proxy.install` write their exports there because an IDE server probes a
login shell at start.

Beyond the terminal the chain is longer than it looks, and it was mapped on 2026-09-07:

1. GDM starts the desktop session through the user's **login shell**, which is zsh because
   `inv zsh.set-default-shell` made it so. That shell reads `~/.zshenv` and `~/.zprofile`.
2. `gnome-session` imports that environment into the **systemd user manager**. The evidence is still
   visible in `systemctl --user show-environment`: `_=/usr/bin/gnome-session`, `SHLVL=0`,
   `SHELL=/usr/bin/zsh`, and a `PATH` containing `~/.local/share/JetBrains/Toolbox/scripts`, which
   only `~/.zprofile` adds and only a login shell reads.
3. Everything under `user@<uid>.service` inherits it — `systemctl --user` services directly, and
   dock-launched applications because `gnome-shell` forks them and registers each as an
   `app-<id>.scope`. A scope's process is the launcher's child; the scope is bookkeeping applied
   afterwards.

So a GUI application started from the dock does get `SSL_CERT_FILE`, `SUDO_ASKPASS` and the rest.
Measured three ways: the manager's own environment carries all of them, a transient service the
manager forks (`systemd-run --user --pipe --wait -- env`) has 8 of 8, and `claude-desktop`'s bash
launcher — dock-started, non-Chromium — has them too.

**None of this holds without zsh as the login shell**, which is why that is stated as a prerequisite
rather than left as a preference. See `docs/wsl.md`, "Assumptions this repo makes about WSL".

## A deployed `zshenv` snippet reaches a running agent session, with no restart

The consequence of the property above, stated because the opposite is the natural guess and it costs
a session: **an agent's next Bash call picks up a `zshenv` change immediately.** Each call is a
fresh `zsh -c`, and that reads `~/.zshenv` every time, so a session that stops and waits to be
restarted waits for nothing. Observed 2026-09-05 deploying `export REPO_TASKS_RUN_REPORT=1` with
`inv zsh.configure` and reading it back with `env` in the same session; a written report from that
same work had predicted that "existing agent sessions keep the old environment until they're
restarted", which is wrong in the expensive direction.

**The wrong intuition is easy to reach because it is right about a neighbouring case.** An `export`
typed _inside_ a Bash call dies with that call — which is why the global rules tell you to prefix
`SSH_AUTH_SOCK` per call rather than export it. Both facts come from the same mechanism, a fresh
shell per call, and they point in opposite directions: **what the shell sources every time persists;
what a call sets does not.**

### Which of the three files actually reaches a call

Measured 2026-09-11 with `ZDOTDIR` pointed at a scratch directory holding one marker per startup
file, so nothing real was touched:

| invocation                         | `.zshenv` | `.zshrc` | `.zprofile` |
| ---------------------------------- | --------- | -------- | ----------- |
| `zsh -c` — what the Bash tool runs | **yes**   | no       | no          |
| `zsh -l -c`                        | yes       | no       | **yes**     |
| `zsh -i -c`                        | yes       | **yes**  | no          |

So `zshenv` is the only one of the three with this property, and a snippet declared on the wrong
field silently never reaches a running session — a symptom identical to the mistaken prediction
above.

[PITFALL: **`setopt` reports `login` inside an agent's Bash call, and concluding from that that
`~/.zprofile` is re-read is wrong.** The harness invokes a bare `zsh -c` — no `-l`, no `-i` — that
first sources a per-session shell snapshot, and that snapshot ends with a literal `setopt login`
restoring the option state of the interactive shell it was captured from. So the flag is inherited
state, not evidence about this shell's startup. The same confusion runs one level deeper: variables
that only `~/.zshrc` sets (`ZSH`, `DIRENV_LOG_FORMAT`) and ones only `~/.zprofile` sets (the
JetBrains Toolbox `PATH` entry) _are_ visible in an agent's environment, because the snapshot
carries their values — while an **edit** to either file reaches nothing until a new session is
started. Read a present value as "captured once", never as "read every call"; only `zshenv` is the
second thing.]

## The first thing built to exploit the per-call property: direnv

`[packages.claude-code]`'s snippet runs `eval "$(DIRENV_LOG_FORMAT= direnv export zsh)"` on every
Bash call. It is here rather than in `~/.zshrc`, where direnv's own hook lives, for exactly the
reason the table above gives: `~/.zshrc` is read once per session from the snapshot, so direnv's
hook never re-runs and the environment an agent gets is frozen at capture time.

**Frozen is worse than absent, which is the finding that motivated it.** What is frozen is the
session's _origin_ repo's fully activated venv, so a bare `ruff` in a different repo succeeds and
returns the wrong repo's tool at that repo's pinned version. Measured 2026-09-18: a session in this
repo, standing in `olx-polite-mcp`, still resolved `ruff` to
`power-user-linux-setup/.venv/bin/ruff`. A session filed from a repo with no `.envrc` had reported
the failure as "direnv never fires", which is the same mechanism observed where the frozen
environment happened to be empty.

What the export does, all measured on direnv 2.32.1 at roughly 21 ms a call:

| cwd                                  | result                                                               |
| ------------------------------------ | -------------------------------------------------------------------- |
| a repo with an allowed `.envrc`      | loads it — `DIRENV_DIR`, `VIRTUAL_ENV` and `PATH` become that repo's |
| a directory with no `.envrc`         | **unloads** — emits `unset DIRENV_DIR` and restores the prior `PATH` |
| a repo whose `.envrc` is not allowed | unloads the previous env, silently                                   |

The unload row is half the value and is easy to miss: without it, moving to a directory with no
`.envrc` would keep the last repo's venv rather than dropping it.

**The gap, stated so nobody reads more into the fix than is there**: `cd <other repo> && <command>`
in a single call is unaffected, because `~/.zshenv` is sourced at shell startup, before the
command's own `cd`. `~/.agents/AGENTS.md`'s cross-repo section sanctions that shape and its advice
is unchanged; only its stated reason moved.

[PITFALL: **silencing direnv is deliberate and has a cost worth knowing before someone "fixes" it.**
`DIRENV_LOG_FORMAT=` suppresses direnv's own output entirely, including the error for an `.envrc`
that has not been allowed — the ordinary state of a fresh clone. An agent there gets
`command not
found` and no explanation. Unsilenced, the alternative is a red direnv error on
**every** Bash call in that repo, which is the noise that gets a mechanism switched off.
`inv dev-env.setup` runs `direnv allow` and is what `~/.agents/AGENTS.md` now names as the remedy.]

## Why `~/.config/environment.d/` is not used

Not an oversight, and not a rejection on taste. `man 5 environment.d` describes the systemd user
manager's own environment mechanism — plain `KEY=VALUE`, merged from four directories, applied at
next login, upstream systemd since v233 and identical on every systemd distro. It was proposed here
as a second surface for the variables a program reading `getenv()` needs.

Two reasons it stays unadopted, and the second only became clear once the first was measured:

- **The gap it would close is not there.** The chain above already delivers those variables to
  `app.slice`. Adding `environment.d` would put a second writer behind one fact, with a new way for
  the two to disagree, in exchange for nothing.
- **It cannot replace the zsh blocks anyway.** It requires systemd, and this repo explicitly targets
  containers and WSL-without-systemd, where `util.has_systemd()` already gates whole phases. So the
  zsh blocks would remain the mechanism on those targets whatever happened here.

`~/.pam_environment` is a third possible origin for a variable and is not used either; it was
deprecated in pam 1.5.0 and removed in 1.6.0, and whether its absence is worth asserting is open —
see `plans/2026-09-07-pam-environment-absence-assertion.md`.

## Measuring this: `/proc/<pid>/environ` lies about Chromium

The plan that proposed `environment.d` measured the gap by reading `/proc/<pid>/environ` for `code`
and `claude-desktop`, found none of the variables, and concluded the user manager never sees
`~/.zshenv`. **Both of those applications are Electron**, and that file is not a reliable read for a
Chromium-based process — Chromium rewrites the contiguous argv/envp region to set process titles.

The tell is a parent/child pair that cannot disagree: `/usr/bin/claude-desktop-unofficial` is a bash
script launched from the same dock entry, it has the variables, it sets nothing and unsets nothing
and runs no `env -i`, and the Electron binary it execs reports not having them. A child does not
lose inherited environment across a plain exec, so what changed is the reading.

The plan's one positive control, `gnome-shell`, was the only non-Electron process in its sample —
which is exactly the shape an artifact takes, and is worth knowing as a pattern rather than as one
fact about one file. **When every negative reading shares a process family and the positive does
not, suspect the instrument.**

What to do instead, when this question comes up again: read a non-Chromium child the app spawns, ask
the manager itself (`systemctl --user show-environment`), or run a transient service
(`systemd-run --user --pipe --wait -- env`) rather than a scope — `--scope` forks from the caller
and measures your own shell.

## Why the duplicated `PATH` was ours

The same investigation found `PATH` in the user manager carrying three copies of `~/.local/bin` and
of the go/JetBrains block. Not repeated imports: `~/.zshenv`'s prepend and `[packages.go]`'s append
were unguarded, and `~/.zshenv` is read on every invocation, so each nested shell added a copy —
four in a login shell, five in a `zsh -c` started from it, and whatever the session held at the
moment `gnome-session` imported it, for the life of that session.

`[packages.zsh-path]` now sets `typeset -U path PATH` ahead of the first prepend, which covers every
later assignment in the file and anything added by hand afterwards. The property that made the bug
inevitable — read on every invocation — is the same property the certs and proxy exports depend on,
so it was never going to be fixed by making the file quieter.

Worth keeping as a general shape: **an export that is idempotent in isolation is not idempotent in a
file that is sourced recursively.** `docs/zsh.md`'s PATH section carries the user-facing version.
