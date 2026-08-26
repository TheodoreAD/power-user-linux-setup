---
status: idea
updated: 2026-08-24
---

# Should session environment variables move to `~/.config/environment.d/`?

## Context

**Origin.** `~/.config/environment.d/` came up on 2026-08-24 as a candidate fix for the Chrome
Wayland/DRM problem. It turned out not to work for that (`contributing/chrome-ozone.md` — Chrome
reads no `OZONE_PLATFORM` env var), but investigating it surfaced a real, unrelated gap in how this
repo sets environment variables. This plan is about that gap, not about Chrome.

**Current mechanism.** `setup.toml` packages declare `zshenv` / `zprofile` / `zshrc` snippets, and
`inv zsh.configure` writes them as marker-delimited blocks into the matching dotfile. `~/.zshenv` on
this machine is 50 lines holding ~19 exports: `PATH` additions (`~/.local/bin`, Go, cargo),
`GOROOT`/`GOPATH`, `UV_PYTHON`, `NVM_DIR`, `RUSTUP_HOME`/`CARGO_HOME`, `RESEARCH_HOME`, the
`SUDO_ASKPASS`/`SSH_ASKPASS`/`SSH_ASKPASS_REQUIRE` trio, and the `FZF_*` family.

### The gap (verified 2026-08-24 — do not re-derive)

Modern GNOME launches desktop applications as **systemd user scopes**, not as children of
`gnome-shell`. Confirmed by cgroup:

```
code           → /user.slice/user-1000.slice/user@1000.service/app.slice/app-code-2008327.scope
claude-desktop → /user.slice/user-1000.slice/user@1000.service/app.slice/app-com.anthropic.Claude-….scope
gnome-shell    → /user.slice/user-1000.slice/user@1000.service/session.slice/org.gnome.Shell@wayland.service
```

`systemd --user` is started by `pam_systemd` at login — **before** any login shell runs — so its
environment never sees `~/.zshenv`. Everything it later spawns inherits that shell-free environment.
Measured directly:

- `code` and `claude-desktop`: **none** of `RESEARCH_HOME`, `UV_PYTHON`, `CARGO_HOME`, `GOPATH`,
  `NVM_DIR`, `SUDO_ASKPASS`, `SSH_ASKPASS` present in `/proc/<pid>/environ`.
- `gnome-shell`: **all** of them present — it is under `session.slice` and does get the login-shell
  environment.
- A zsh from the terminal: all present, obviously.

So the repo's environment variables are currently invisible to exactly the class of program that
cannot source a shell rc: GUI applications launched from the dock, the app grid, or autostart.

**How bad is that in practice?** Bounded, and worth being honest about. Any GUI app that opens a
terminal or runs a task through `$SHELL` gets the variables back, because zsh re-sources `~/.zshenv`
in the child. The exposure is limited to programs reading `getenv()` directly — an IDE run
configuration, an Electron app, a `.desktop` `Exec` line, a `systemctl --user` service. But
`SUDO_ASKPASS`/`SSH_ASKPASS` are precisely that shape, and the whole point of them is to work when
there is no TTY.

### What `~/.config/environment.d/` is

The systemd user manager's environment mechanism, `man 5 environment.d`. `systemd --user` runs
`systemd-environment-d-generator` at startup (present here at
`/usr/lib/systemd/user-environment-generators/30-systemd-environment-d-generator`), merging `*.conf`
files from four directories, lowest priority first:

```
/usr/lib/environment.d/    # 990-snapd.conf, 99-environment.conf -> /etc/environment
/run/environment.d/
/etc/environment.d/        # 90atk-adaptor.conf, 90qt-a11y.conf
~/.config/environment.d/   # does not exist on this machine
```

Format is plain `KEY=VALUE`, one per line — no shell, no conditionals, no command substitution.
Files merge in lexicographic order by filename _across_ directories; an identically-named file in a
higher-priority directory masks the lower one entirely. Variables land in the user manager's own
environment, so everything under `user@1000.service` inherits them, `app.slice` scopes included.
Applied at next login.

### Portability, and why the zsh blocks cannot simply be dropped

`environment.d` is upstream systemd (v233, 2017), not a distro feature — every systemd distro has it
identically, and the only per-distro variation is which files ship preloaded under the system-level
directories. There is no counterpart at all on the no-systemd targets this repo supports (containers
and WSL-without-systemd, where `util.has_systemd()` already gates whole phases; likewise
Alpine/OpenRC, Void/runit). That is a second, independent reason the `zshenv` blocks stay — not only
"they are what interactive shells read," but "on those targets nothing else exists."

### Why this repo never adopted it

Worth recording so the omission does not read as a considered rejection that someone later has to
re-litigate. `environment.d` is low-profile on Ubuntu rather than discouraged — there is no
community consensus against it. Three reasons it stayed invisible:

- The older advice kept working. A decade of Ask Ubuntu answers point at `~/.profile`,
  `/etc/environment`, and `~/.pam_environment`, and those still mostly function.
- It only became load-bearing when GNOME's session moved to systemd user units. Under X11, session
  environment came from `/etc/X11/Xsession.d/` and `~/.profile`, which _did_ reach GUI applications
  — the gap measured above did not exist in the same form, so nobody had a reason to go looking for
  a replacement mechanism.
- Ubuntu ships files under the system-level directories but no installer, GUI, or doc points a user
  at the `~/.config/` counterpart.

**A third writer is still wired up on this machine (verified 2026-08-24).** `~/.pam_environment` was
deprecated in pam 1.5.0 and removed in 1.6.0, but this machine runs pam 1.5.3 and still carries
`user_readenv=1` in `/etc/pam.d/gdm-password` and `/etc/pam.d/sshd` — so the file would still be
read if it existed. It does not exist here, but nothing asserts that.

## Open questions

[NEEDS CLARIFICATION: should `inv verify.all` assert the _absence_ of `~/.pam_environment`? It is a
fourth possible origin for a variable, on a removal timer set by whenever pam 1.6 reaches an Ubuntu
release this repo targets — at which point anything relying on it fails silently rather than
loudly.]

[NEEDS CLARIFICATION: `environment.d` does not cover every entry point either, which sharpens the
replacement-vs-addition question below into "neither surface is complete." It reaches whatever
`systemd --user` spawns. [UNVERIFIED: a non-interactive `ssh host cmd` and a bare tty login are
believed not to pick it up, neither environment coming from the user manager — not tested.] For the
askpass trio the practical impact is near zero, since a GUI prompt is useless over a non-interactive
ssh anyway, but it means moving a variable to `environment.d` can never be a clean migration for one
that an ssh-invoked command also needs.]

[NEEDS CLARIFICATION: Is this a **replacement** for the `zshenv` blocks or an **addition** beside
them? Replacement is cleaner but impossible as stated — `environment.d` requires systemd, and this
repo explicitly targets containers and WSL-without-systemd, where `util.has_systemd()` already gates
whole phases. So zsh must remain the fallback path, and the real question is whether a variable gets
written to one place, the other, or both. Both means two writers for one fact and a new way for them
to drift.]

[NEEDS CLARIFICATION: `PATH` is the hard case and probably should not move at all. The `zshenv`
snippets prepend (`export PATH="${HOME}/.local/bin:${PATH}"`), and several are order-sensitive
relative to each other and to direnv. [UNVERIFIED: whether `environment.d` expands `$PATH` inherited
from PAM, or only variables set earlier within the merged `environment.d` set itself. The man page
documents `$VAR` expansion for previously-assigned variables; whether the inherited value
participates was not tested.] Getting this wrong breaks every login shell on the machine, so it
wants a real test, not a reading.]

[NEEDS CLARIFICATION: Which variables are actually worth moving? A first cut by whether a
non-shell-spawning GUI program would ever want them:

- **Clear yes:** `SUDO_ASKPASS`, `SSH_ASKPASS`, `SSH_ASKPASS_REQUIRE` — their entire purpose is
  no-TTY contexts, and they are currently absent from every `app.slice` process.
- **Probably yes:** `RESEARCH_HOME`, `UV_PYTHON`, `CARGO_HOME`, `RUSTUP_HOME`, `GOPATH`, `GOROOT`,
  `NVM_DIR` — an IDE launched from the dock is exactly the consumer that wants these, and is exactly
  what does not have them today.
- **Clear no:** the `FZF_*` family. They configure an interactive shell widget, their values
  reference other CLIs, and nothing outside a shell reads them.
- **Undecided:** `PATH`, per the question above.]

[DECISION: Writing into `~/.config/environment.d/` is a **new home-directory writer**, and the
drift-guard work that unified those has landed (`tasks/deploy.py`, rationale in
`contributing/deploy.md`). It goes through `deploy.deploy()` and appears in `deploy.status` — never
its own deploy path in `zsh.py`. Whether it is a `wrapper-script`-style `MANAGED` file or a
`config_files`-style `SEEDED` one is the only question left, and `MANAGED` is the obvious answer for
a file whose entire content PULSE generates.]

[NEEDS CLARIFICATION: Does the change need a re-login to be observable, and does that make it
awkward to verify in `inv verify.all`? A conventional post-install check can confirm the file's
_content_, but not that the running session picked it up — the two disagree for a whole session
after any change.]

## Recommended direction

1. **Do not frame this as "replace the zsh stuff."** The zsh blocks stay; they are the only
   mechanism that works on the no-systemd targets this repo supports, and they are what interactive
   shells actually read. The proposal is narrower: a second, systemd-only surface for the subset of
   variables that GUI-launched programs need.
2. **Start with the askpass trio only.** It is the sharpest case (no-TTY is their reason to exist),
   the smallest possible change, and it produces a testable claim: after a re-login, a dock-launched
   application's `/proc/<pid>/environ` contains `SUDO_ASKPASS`. If that works, widen to the
   tool-home variables; if it does not, nothing else was built on a wrong assumption.
3. **Leave `PATH` alone** until the expansion semantics are actually tested, and treat "we never
   move `PATH`" as an acceptable permanent outcome rather than a failure.
4. **Reuse the declaration shape already in `setup.toml`.** A per-package `environment_d` field
   alongside `zshenv`/`zshrc`/`zprofile` keeps the fact next to the package that owns it, which is
   the pattern the repo already uses and the reason `~/.zshenv` is coherent today. Route the write
   through the drift-guard plan's shared writer rather than adding a fourth one.
