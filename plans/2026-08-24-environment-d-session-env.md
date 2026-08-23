---
status: idea
updated: 2026-08-24
---

# Should session environment variables move to `~/.config/environment.d/`?

## Context

**Origin.** `~/.config/environment.d/` came up on 2026-08-24 as a candidate fix for the Chrome
Wayland/DRM problem. It turned out not to work for that
(`plans/2026-08-24-chrome-ozone-x11-launcher-coverage.md` — Chrome reads no `OZONE_PLATFORM` env
var), but investigating it surfaced a real, unrelated gap in how this repo sets environment
variables. This plan is about that gap, not about Chrome.

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

## Open questions

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

[NEEDS CLARIFICATION: Writing into `~/.config/environment.d/` would be a **new home-directory
writer**, which `plans/2026-08-22-deployed-config-drift-guard.md` is explicitly trying to reduce the
number of. It should go through that plan's shared writer and appear in `deploy.status`, not grow
its own deploy path in `zsh.py`. That plan should probably land first.]

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
