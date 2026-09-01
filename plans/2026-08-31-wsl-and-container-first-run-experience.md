---
status: in-progress
updated: 2026-09-01
---

# WSL and container first-run experience

## Context

A first `inv wsl.install` on a second machine (corporate Windows, WSL2) failed in two ways at once:
it **hung** after the sudo password prompt, and the **password was echoed in plain text** while
being typed. Separately, on the same corporate network, `pypi.org` was unreachable while "whatever
uv downloads from" was reachable — an asymmetry the setup has no way to report, so a run just fails
somewhere inside `uv tool install` with a network error and no diagnosis.

Both are first-run experience problems for the two environments PULSE cannot dogfood on the author's
own workstation: **WSL** (a password-protected sudo user, no display, a Windows host holding the
proxy and DNS configuration) and **containers** (no tty at all, no systemd, unattended).

Everything below was reproduced in a container built for the purpose (`ubuntu:22.04` + a
password-protected sudo user + `WSL_DISTRO_NAME` set), not reasoned about from the code.

### Finding 1 — invoke echoes stdin, and races sudo for it

`Runner.should_echo_stdin()` is `(not self.using_pty) and isatty(input_)` (`invoke/runners.py:918`).
For **every non-pty `c.run`** from a terminal, invoke's stdin mirror thread reads the user's
keystrokes and **writes them to stdout itself** — invoke has put the terminal in cbreak (ECHO off),
so without that echo the user would see nothing.

Demonstrated directly: a task running `c.run("head -n 1 > /dev/null")`, typing `SUPERSECRET`, prints
`SUPERSECRET` back.

`sudo` reads its password from `/dev/tty`, not from stdin — the same terminal invoke's mirror thread
is reading. So a sudo password prompt reached from inside any `c.run` is a **race between two
readers of one terminal**:

- sudo wins the read → nothing echoes, everything works (what happens on this workstation, and in
  the container repro, every time it was run).
- invoke wins some or all of it → those characters are printed in plain text **and** sudo never sees
  them, so it fails the attempt and re-prompts. Three of those and it gives up. That is exactly "it
  got stuck after asking for the password, which appeared in plain text".

The race is why this reproduces on one machine and not another, and why the same command can behave
differently twice in a row.

[PITFALL: `pty=True` does not fix this — it moves the prompt into a second pty whose ECHO state sudo
controls, which is why `wsl.install`'s existing pre-auth looks fine here. Every _other_ sudo call in
the repo (46 of them, all `f"{util.SUDO} …"`) is non-pty, so any one of them that prompts is the bug
again.]

The real invariant is not "use a pty": it is **no sudo call inside `c.run` may ever prompt**.

### Finding 1b — on Python 3.14 invoke cannot forward stdin at all

The hang half of the report is not the race; it is deterministic, and it is upstream.
`terminals.bytes_to_read()` calls `fcntl.ioctl(stdin, FIONREAD, b"  ")` — a 2-byte buffer for a
4-byte result. Every Python before 3.14 overflowed it silently; 3.14 hardened `fcntl.ioctl` and
raises `SystemError: buffer overflow`, which kills invoke's stdin thread on the first keystroke.
Nothing is ever written to the child, pty or not, and it waits forever.

Measured in the container, same invoke 3.0.3 throughout: 3.10/3.11/3.12/3.13 forward stdin (and echo
it — Finding 1); **3.14 hangs**. `uv_python_default = "3.14"`, so this is the default path on any
machine bootstrapped today. Upstream: pyinvoke/invoke#1070, fixes open, unreleased.

[PITFALL: `ssh-keygen`, `ssh-copy-id` and `ssh-add` all used `pty=True` too, so every SSH key
operation this repo automates hangs on 3.14 for the same reason. Found by grepping for `pty=True`
after the sudo cause was understood, not by anyone hitting it.]

### Finding 2 — the credential cache lapses mid-run

The pre-auth warms sudo's cache (15 min default) and then a full `inv wsl.install` runs for much
longer than that on a slow/corporate connection. The next sudo call after the lapse prompts — see
Finding 1.

### Finding 3 — apt can prompt, and that hang is invisible

`DEBIAN_FRONTEND` appears **nowhere** in this repo, so every `sudo apt install -y …` runs with the
interactive frontend. A package with a debconf question (`tzdata`, `wireshark-common`'s dumpcap
question, `keyboard-configuration`) or a modified conffile stops and waits.

Confirmed the hard way while building the reproduction container for this plan: a plain
`apt-get install … tzdata` in a `docker build` sat on tzdata's "Geographic area" prompt for **25
minutes** before it was killed. `docker build -q` shows nothing while that happens — the same "stuck
with no output" shape the user reported, from a different cause.

### Finding 4 — WSL gets a GUI askpass with no GUI

`[packages.askpass-zenity]` writes `SUDO_ASKPASS`/`SSH_ASKPASS` into `~/.zshenv` unconditionally,
and `zsh.configure`'s zshenv writer ignored tags — as `docs/configuration.md` documented at the
time; both were fixed 2026-09-01 and that page now says the opposite, so read this paragraph as the
state at discovery. So on WSL without WSLg, and in any container:

- every new shell exports `SUDO_ASKPASS=~/.local/bin/askpass-zenity`,
- `util.SUDO` therefore becomes `sudo -A`,
- `wsl.install`'s pre-auth is **skipped** (its condition is "SUDO_ASKPASS is not set"),
- and `zenity` fails without a display.

Reproduced: `sudo -A -v` with a zenity-less askpass gives `sudo: no password was provided` /
`sudo: a password is required`, exit 1 — so the _second_ run of `inv wsl.install` on a fresh WSL
distro fails where the first one worked.

`[packages.zenity]` is tagged `shell, system`, not `gui`, so a headless WSL distro also installs
zenity's whole GTK dependency tree for a dialog it can never show.

### Finding 5 — nothing tells you which endpoint is blocked

`inv proxy.check` answers "is there a proxy and what auth does it want". The corporate failure that
actually happened is a different question: **which of the hosts this setup needs are reachable, and
by what route**. PyPI blocked while GitHub is fine is a completely ordinary corporate posture (an
internal Artifactory/Nexus mirror is the sanctioned path), and it is invisible until a download
fails deep inside `uv tool install`.

That diagnosis has to work **before** PULSE is installed — before `uv`, before `invoke`, before this
repo's own venv — so it cannot be an invoke task. Whatever python3 the distro ships is the only
interpreter available there, which for this repo's target (Ubuntu 24.04) is 3.12.

### Finding 6 — every system file this repo writes was mode 0600

Found by re-running the fixed flow in the container: `inv wsl.fix` wrote `/etc/wsl.conf` and the
next line, which reads it back to report what changed, died with `PermissionError`.
`util.sudo_write()` wrote through `tempfile.NamedTemporaryFile` (0600) and `cp`, which preserves the
mode. Unreachable from the development workstation — the file is only read back by a non-root
process on a machine where PULSE wrote it.

### Finding 7 — the documented container bake path was broken, twice

Running `docker build -f docker/Dockerfile` (the canonical bake, and the thing the dev-container
docs point at as an example) failed twice for reasons that have nothing to do with sudo:

1. **No git.** `bootstrap.sh` self-heals curl/gnupg/sudo/ca-certificates but not git, and
   `uv tool install 'repo-tasks @ git+https://…'` shells out to it — so the build died with uv's
   "Git executable not found" two minutes in, after downloading four Pythons.
2. **`skills` before the thing that installs it.** `ai.install_skills` ran _before_ `node.install`
   in both phase lists, and the `skills` CLI is a global npm package `node.install` provides. Exit
   127, ~90% of the way through an unattended build, with no message.

[PITFALL: reordering the phases is necessary but not sufficient. A global npm package lives under a
version-specific nvm path that is only on `PATH` once `nvm.sh` has been sourced — a login shell does
that through Oh My Zsh's nvm plugin, an `inv` process never does. So a bare `skills` call works when
a human tries it by hand and exits 127 inside a `RUN` layer or any non-interactive run.
`[packages.node]`'s own `verify_cmd` already documented this gap for `node --version`; nothing had
generalised it. `node.nvm_command()` does now.]

[PITFALL: the existing tests for that code path passed only because `skills` happens to be on the
developer's `PATH`. A test asserting on a command string is asserting about the machine unless the
lookup is pinned.]

## Design

### 1. `tasks/netdoctor.py` — a stdlib-only diagnostic that runs on the system Python

```shell
python3 tasks/netdoctor.py            # nothing installed; runs on the distro's own python3
inv net.check                          # the same code, from the invoke side (tasks/net.py)
```

Hard constraints, each enforced by a unit test: **standard library only**, **no import from
`tasks/`**, and it must parse as Python 3.12 (24.04's system Python). The dependency runs one way —
`tasks/*.py` may import it, never the reverse; `wsl.py`'s raw DNS query moved there and is imported
back.

[DECISION: the floor is Ubuntu 24.04's Python 3.12, not 22.04's 3.10. The module was written against
3.10 first, on the reasoning that a corporate fleet lags and a WSL distro installed years ago is
never upgraded. Reconsidered and narrowed deliberately: this repo is distributed to a handful of
people directly, on the timescale where 22.04 will not be what any of them is running, and the
target everywhere else in the repo is already 24.04. The zero-install property — no uv, no invoke,
no venv — is unchanged and is the part that actually matters; only the version bound moved.]

[PITFALL: "the distro's python3" is only true of the _first_ bootstrap. `uv_python_set_default`
(true by default) puts `~/.local/bin/python3` — uv's managed interpreter — ahead of
`/usr/bin/python3`, which setup.toml documents, so every later run of the preflight is on uv's
Python rather than the system one. That satisfies the floor either way, but it means the floor is
set by one run only, and that wording was wrong in three files before it was checked.]

[PITFALL: neither container base image this repo targets ships a Python — not `ubuntu:24.04`, and
not `mcr.microsoft.com/devcontainers/base:ubuntu-24.04` either, which is the surprising one. What
provides `python3` in a container is `uv_python_set_default`'s symlink, and that is load-bearing
beyond the preflight: five `version_cmd` entries in setup.toml (atuin, glab, helm, tilt,
jetbrains-toolbox) pipe a release JSON through a bare `python3`, and none of those packages is
excluded by the container tag set. Verified in a Python-less image: helm's version_cmd fails before
`uv python install --default` and returns 4.2.4 after. So turning that setting off — documented as
"leave python/python3 fully system/apt-owned", which sounds harmless — breaks those five in a
container while changing nothing on a real Ubuntu. Recorded next to the setting itself.]

[PITFALL: the stock `ubuntu:24.04` _docker_ image has no Python at all — zero python packages, no
binary anywhere on the filesystem, and `python3` is not in `ubuntu-minimal`'s dependencies. A real
Ubuntu install always has one — and for WSL specifically that is now checked rather than assumed:
Ubuntu's published WSL image manifest for noble lists `python3 3.12.3-0ubuntu2` and
`python3-minimal` (`cloud-images.ubuntu.com/wsl/noble/current/ubuntu-noble-wsl-amd64-wsl.manifest`,
529 packages). So this is a container-only gap. Adding python3 to bootstrap.sh's apt prerequisites
to close it was proposed and rejected: it is a second system-wide Python on a machine where uv owns
them, installed from a shell script outside setup.toml, for the one environment where the diagnosis
matters least. The preflight says it is skipping instead.]

[DECISION: one self-contained module inside `tasks/`, not a new top-level `doctor/` package. A
top-level package would sit outside `pyrightconfig.json`'s `include` (`src*`/`tests*`/`tasks*`),
which is a file shared byte-identically across the repo family — so it would be neither type-checked
nor fixable without diverging that config. Running a _file_ (`python3 tasks/netdoctor.py`) rather
than importing a module is what keeps the zero-install entrypoint working: it never executes
`tasks/__init__.py`, which imports invoke.]

Sections within the module: the endpoint catalog (what breaks without each host); the probes (DNS,
TCP, TLS with and without verification, HTTP through an optional proxy); facts read off the machine
(proxy env, `/etc/environment`, apt proxy config, pip/uv/npm/git indexes, resolv.conf provenance,
extra CA roots); the Windows side under WSL (`reg.exe`, `netsh.exe`, the PAC file, `/etc/wsl.conf`,
`%USERPROFILE%\.wslconfig`); and `evaluate()`, which turns all of it into findings that each end in
the command that fixes them.

[DECISION: `evaluate()` takes every measurement as an argument, including whether public DNS
answered. That purity is what makes a corporate network a literal in a unit test — PyPI blocked
while GitHub answers, a 407, an untrusted issuer, a Windows-side proxy the distro doesn't know about
— none of which this repo can otherwise test against.]

[PITFALL: the certificate issuer is read by scanning the DER for the commonName OID rather than
parsing X.509. `ssl` only returns a parsed certificate dict for a chain it _validated_, and the
interesting case is precisely the one that failed validation. Verified against a real self-signed
certificate in a container, not only against a synthetic buffer.]

### 2. Sudo that cannot prompt from inside `c.run`

In `tasks/util.py`:

- `sudo_state()` — root? `sudo -n true` (passwordless)? cached? askpass usable (set, executable, and
  a display if it is the zenity one)? a tty?
- `ensure_sudo()` — idempotent, called once by `inv setup`/`inv wsl.install` and by each sudo-using
  task that can be run on its own. Authenticates **outside invoke**, with
  `subprocess.run(["sudo", "-v"])` inheriting the real terminal, so sudo owns `/dev/tty` alone and
  there is no second reader. Then sets `util.SUDO = "sudo -n"` so that **every** later call fails
  loudly instead of prompting invisibly, and starts a daemon keepalive thread refreshing
  `sudo -n -v` every 60s so the 15-minute cache cannot lapse mid-run (Finding 2).
- `SUDO` becomes `""` when already root, so the container path stops needing `sudo` installed at
  all.
- No tty, no askpass, not root, not passwordless → stop **before** the first install with the
  actionable message, rather than at some random package.

### 3. apt that cannot prompt

A single helper wraps every apt invocation with `DEBIAN_FRONTEND=noninteractive` and
`-o Dpkg::Options::=--force-confold -o Dpkg::Options::=--force-confdef`, so a debconf question or a
conffile conflict can never stop an unattended run (Finding 3).

### 4. askpass that degrades to the terminal

`config/askpass-zenity.sh` gets a no-display fallback: when neither `DISPLAY` nor `WAYLAND_DISPLAY`
is set, read the passphrase from `/dev/tty` with echo off instead of failing, and exit cleanly when
there is no terminal either. `[packages.zenity]` moves to the `gui` tag so a headless WSL distro
stops installing GTK for a window it can never show (Finding 4).

[DECISION: the helper degrades, rather than the `zshenv` export becoming conditional on a display.
The export is written once, at install time, while `DISPLAY` is a property of the _session_ and the
same machine has both kinds — so a helper that decides at call time is right in both. Restated
2026-09-01: the original wording gave the reason as "a writer that ignores tags", which stopped
being true when `zsh.configure` became tag-aware. The conclusion is unchanged and now rests on
something firmer than a bug: `[packages.askpass-zenity]` is tagged `shell, system`, not `gui`, so a
tag-honouring writer still writes that export on a headless distro — correctly, because the machine
may later have a display. Only `[packages.zenity]`, the dialog binary, moved to `gui`.]

## Still open

[DECISION: **`inv net.check` stays out of `inv verify.all`.** Settled 2026-09-01, converting what
was filed as a DEFERRED item — it was a reasoned rejection all along, not work put off, and leaving
it tagged as deferred kept a backlog entry nobody intended to act on. `verify.all` is a post-install
functional check of what was just installed, and a network probe there fails a run over a
reachability problem that no longer matters once everything _is_ installed. Two things sharpen it
since: `verify.all` aborts on the first failure by design, so a transient probe would take the whole
check down rather than report alongside it; and `bootstrap.sh` already runs the diagnostic as a
preflight, which is where reachability is actionable — before the downloads, not after. Revisit only
if a real failure argues for it.]

### Landed 2026-09-01

- **Per-package apt tolerance.** `install_base`'s apt call had no `warn=True`, so the first package
  the archive could not supply raised and left every later one uninstalled. Failures are collected
  per package and raised once at the end, so the run still fails but only after installing
  everything it could. The individual retry is what makes the batch survivable: `apt-get` resolves
  the whole command line before installing anything, so one bad name means none of its batch-mates
  were installed either. `install_repos` had the mirror-image bug — `_register_repo` returned the
  same `False` for "already registered" and "the key fetch failed", so an unregistered repo still
  went through phase 2. `tests/unit/test_apt.py` guards both; its fake Context raises on a non-zero
  command that was not passed `warn=True`, so deleting one fails five tests.
- **`zsh.configure` honours tags**, via `util.enabled_packages()`, and removes the block of a
  package that stopped applying — `util.remove_block_text`/`remove_block` are new for that. Removal
  was not optional: excluding a tag on a machine that already ran without the exclusion leaves the
  export sitting in the dotfile, and nothing else would ever take it out. `configure_omz` had the
  same blindness for `omz_plugin`. `tests/unit/test_zsh.py` guards it.

### Turned up while fixing those, not acted on

[DEFERRED: **`apt._install_deb_url` calls `input()`, which hangs an unattended run** — a container
bake or an `inv wsl.install` on a machine nobody is sitting at. It is reached by the three
`download_page` packages (`corporate`-tagged Citrix ones) that have no direct URL and ask for a
hand-downloaded `.deb` by path. This does not hit the invoke-stdin bug documented in
`contributing/interactive-input.md`, because the read is Python's rather than a child process's —
which is exactly why it slipped past that pass. The repo's stated invariant is that nothing run
through invoke may wait for typed input, and this waits. The fix is probably to skip with a message
when stdin is not a tty rather than to prompt, but that is a behaviour change for the interactive
case and wants its own decision.]

[DEFERRED: **`install_debs` still cannot fail.** Both deb installers report their failures and
return, so a run where every `deb-github` download 404'd exits 0. The apt paths got a failure
summary; this one did not, because the honest verdict is not available at the point of failure:
`dpkg -i` exits non-zero for a package whose dependencies aren't in place yet, and the closing
`apt-get install -f -y` is what repairs precisely that — so its exit code is not evidence, and
treating it as such would fail runs that are about to succeed (google-chrome-stable on a fresh
machine is the named case). The answerable form is a `check_cmd` existence sweep _after_ the `-f`
pass, which is what `verify.all` already does for these packages one phase later. Deciding whether
that duplication is worth it, and how it distinguishes a genuine failure from a package the user
deliberately skipped at the manual-download prompt, is the open part.]

[DEFERRED: **the tag-blindness fixed in `zsh.py` may not be the only instance.** `deploy.py:310`,
`home.py:571`, `ai.py:255`/`296`/`348` and `gnome.py:222` all read sections with a manual `enabled`
check rather than `util.enabled_packages()`. Some are certainly deliberate — `deploy.py`'s registry
has to cover everything declared so `deploy.status` can report drift on a package this profile
excludes — so this is an audit, not a sweep, and each one needs its own answer. The reason to do it
at all is that the zsh instance was found by its symptom on a real machine rather than by reading
the code, and the same symptom elsewhere would be just as quiet.]

## The consumer dev-container path was broken, and it failed silently

Found and fixed 2026-09-01 while running both distribution paths end to end. Unlike everything
above, this one is about the _recommended_ path a consumer copies, not about what happens once PULSE
is running.

**Resolved the same day, and verified as a consumer rather than as the author.** The devcontainer
workflow was dispatched for the first time in its existence: `smoke-test` passed in 3m0s and
`publish-stable` created the tag, so `stable` now resolves (`92d83ff`) and the documented URL
returns 200. Then the documented command itself was run in a stock
`mcr.microsoft.com/devcontainers/base:ubuntu-24.04` as the `vscode` user — not `--local`, not the
bake, the actual two-step curl a stranger would paste:

```
Cloning power-user-linux-setup@stable into /home/vscode/.local/share/pulse-devcontainer-src...
...
PULSE_EXCLUDE_TAGS=gui,workstation,corporate,ide,gnome
```

57 `verify.all` passes, zero failures, reached `next steps`, exit 0.

[PITFALL: `stable` moving is **not** automatic, and the docs now say so. The workflow stays
`workflow_dispatch`-only, so the tag advances only when someone dispatches it by hand — a reviewed
marker rather than a moving head, which can lag `master` indefinitely. That is a different promise
from the one "CI only force-moves it forward when the smoke test passes" implies on first reading.]

```
$ curl -fsSL https://raw.githubusercontent.com/TheodoreAD/power-user-linux-setup/stable/bootstrap-devcontainer.sh | bash
curl: (22) The requested URL returned error: 404
pipeline exit=0
```

Two independent defects, both confirmed:

[PITFALL: **`stable` does not exist.** `git ls-remote origin 'refs/tags/*'` returns nothing — the
remote has no tags at all. The only thing that creates the tag is `devcontainer.yml`'s
`publish-stable`, and `gh run list --workflow devcontainer.yml` returns `[]`: that workflow has
never executed. `docs/dev-container.md` hands consumers that exact URL in its headline snippet, and
the caveat explaining the situation sits 25 lines below it, under a "Why `stable`" aside a reader
copying the block never reaches. Nothing publishes an image either — the `smoke-test` job names
`ghcr.io/theodoread/power-user-linux-setup-devcontainer` but carries `push: never`, and that package
does not exist. **Delivery is pure git**: one script over `raw.githubusercontent.com` and a shallow
clone, both addressed by ref.]

[PITFALL: **`curl … | bash` converts the 404 into a success.** `curl -f` exits 22, `bash` reads an
empty stdin and exits 0, and a pipeline reports its _last_ command's status — so a
`postCreateCommand` written this way reports success while installing nothing, and the container
comes up bare. This is the repo's own "Reading a command's result" rule, in the one command handed
to strangers. It is not specific to the missing tag: a network blip, a corporate proxy's error page,
or any future ref problem produces the same silent no-op. The two-step form returns 22, verified:
`curl -fsSL <url> -o pulse.sh && bash pulse.sh`.]

### The smoke test asserted almost nothing

Noticed 2026-09-01 while reading the workflow for its stale plan pointer, and fixed the same day.
`devcontainers/ci`'s `runCmd` is handed to a single `sh -c`, which reports its **last** command's
status — so `inv --list` and two of the three `command -v` lines could each have failed without the
job noticing. The repo's own "clean output is not proof, the exit code is" rule, unenforced in the
one place this repo runs CI on itself. `set -eu` now heads the block.

What it asserts also moved. `inv verify.all` already runs during the build and invokes every package
it installed, so repeating that in `runCmd` adds nothing; the untested promise was
`docs/dev-container.md`'s "Which shell finds which tool" table, written 2026-09-01 and guarded by
nothing. The three blocks now mirror it: `/usr/bin` binaries in the bare context, everything
zshenv-reached under `zsh -c` (with `go` and `cargo` **executed** rather than located — go resolves
GOROOT through its symlink, which `[packages.go]`'s own `verify_cmd` cannot prove because it calls
the absolute path, and rustup's shims exit 1 without `RUSTUP_HOME`), and node plus `skills` under
`zsh -lic`, the route Finding 7's exit-127 bake failure came through.

[PITFALL: the assertions were run in `pulse-devcontainer-verify` — the `docker/Dockerfile` bake,
root on `ubuntu:24.04` with the image's own `ENV` — and all pass there, `zsh -lic` included. CI
builds `.devcontainer/` instead: `vscode` on the Microsoft base, no `ENV`, PATH coming only from
what PULSE wrote into that user's `~/.zshenv`. The same set was installed there in the consumer run
above (57 `verify.all` passes), but the shell assertions themselves have not run in that image;
dispatching the workflow is what confirms it.]

## Verification

Both distribution paths were re-run end to end 2026-09-01, against the working tree including that
day's apt and zsh changes:

- **WSL simulation, exit 0.** `bash bootstrap.sh --invoke-only && inv wsl.install` under the pty
  harness on `pulse-wsl-sim`. `verify.all` reported 57 packages `ok`, 6 config-only skipped, zero
  failures; the run reached `next steps`. The sudo password appears exactly once in the whole log,
  and that occurrence is `drive.py`'s own `<<< sent >>>` marker — so nothing echoed it.
- **The zsh tag fix, confirmed on a headless machine rather than in a unit test.** That run resolved
  `PULSE_EXCLUDE_TAGS=corporate,desktop,gnome,gui,workstation` and wrote 19 shell blocks;
  `[clipboard]` (tagged `cli, desktop, gui`) was **absent**, where the same task on the workstation
  lists it. `[askpass-zenity]` was written, correctly — it is tagged `shell, system`.
- **Dev container bake, exit 0.** `docker build -f docker/Dockerfile` with the local tree. The image
  smoke-tests clean: `inv --list`, and `rg fd fzf gh jq eza bat kubectl helm python3 uv dprint` all
  present.

Earlier, all of it in containers driven through a real pty (a pipe would make both original symptoms
impossible to observe):

- **The two causes, isolated.** invoke echoing a typed secret on 3.10–3.13; the deterministic hang
  on 3.14; the standard-library reproduction that named `FIONREAD`; `subprocess` working where both
  invoke forms fail.
- **`inv wsl.install` end to end** on a simulated WSL distro (`ubuntu:24.04`, password-protected
  sudo user, `WSL_DISTRO_NAME` set, no systemd, no display), from `bash bootstrap.sh` — including
  its new preflight — through the packages phase. The sudo password is asked once and nothing later
  stops for input. An earlier pass ran on `ubuntu:22.04` as well, which is how the module was
  exercised under a 3.10 interpreter before the floor was settled at 24.04's 3.12.
- **The doctor against simulated corporate networks**: no network at all, PyPI blocked while GitHub
  answers, a self-signed "Corp Root Inspection CA" presented on :443, and a proxy answering 407 with
  `Negotiate, NTLM`. Each produced the intended single finding after two rounds of tightening — a
  TLS-trust failure was initially also reported as a blocked index, and an all-DNS failure produced
  eight findings for one cause.
- **The askpass helper** with and without a terminal.
- **Unit tests**: the sudo state machine with every probe stubbed, the apt command construction,
  netdoctor's parsers, its whole `evaluate()` layer, and the three constraint tests (stdlib only, no
  `tasks/` import, 3.12 syntax).

[UNVERIFIED: none of this has run on a real WSL2 distro on real corporate infrastructure. The
Windows-side reads (`reg.exe`, `netsh.exe`, the PAC fetch, `.wslconfig` discovery) are exercised
only through their captured-output parsers in unit tests, since the development machine has no
Windows.]
