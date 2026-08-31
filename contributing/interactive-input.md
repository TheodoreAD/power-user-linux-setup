# Anything that waits for typed input, and why it can't go through invoke

The rule is in [`AGENTS.md`](../AGENTS.md) ("Nothing run through invoke may wait for typed input").
This page is the evidence behind it, the measurements, and the design that follows — read it before
"simplifying" `util.ensure_sudo()` back into a `c.run("sudo -v", pty=True)`, which is what it
replaced.

## What was reported

A first `inv wsl.install` on a second machine (corporate Windows laptop, WSL2) **hung after the sudo
password prompt**, and **the password appeared in plain text** as it was typed. Two symptoms, one
report, no stack trace.

Neither reproduces on the machine this repo is developed on, which is the whole problem: the
password path is exercised on a workstation whose sudo credential cache is nearly always warm, and
in dev containers whose user has a `NOPASSWD` rule. WSL is the environment where a real password
prompt actually happens.

## How it was reproduced

A container built for the purpose, because the difference that matters is the _user_, not the
distro: `ubuntu:22.04`, a `dev` user with an actual password in the `sudo` group, `WSL_DISTRO_NAME`
set so `util.is_wsl()` is true, no systemd, no display. Driven through a real pty by a small
harness, so prompts could be answered and the terminal's own echo state was faithful (a plain pipe
would have made both symptoms impossible to observe).

Two candidate causes turned up, and both are real.

### 1. invoke echoes stdin, and races sudo for it

`invoke/runners.py`:

```python
def should_echo_stdin(self, input_: IO, output: IO) -> bool:
    return (not self.using_pty) and isatty(input_)
```

For any non-pty `c.run` from a terminal, invoke puts the terminal in cbreak (ECHO off) and then
**prints every byte it reads back to stdout itself** — otherwise the user would see nothing as they
type. Demonstrated directly, with a task whose whole body is `c.run("head -n 1 > /dev/null")`:

```
[repro] START stdin_echo (type a secret + Enter)
SUPERSECRET
[repro] END stdin_echo
```

Meanwhile `sudo` does not read its password from stdin at all — it opens `/dev/tty`, the same
terminal invoke's mirror thread is reading. Two readers, one terminal, and the kernel hands each
byte to exactly one of them:

- sudo wins → nothing echoes, everything works. This is what happens on the development workstation,
  and in the container, every time it was run.
- invoke wins some or all of it → those characters are **printed in plain text** and sudo **never
  sees them**, so the attempt fails and it re-prompts. Three of those and it gives up.

That is precisely the report, and the raciness explains why it appears on one machine and not
another.

`pty=True` does not fix it: it moves the child's prompt into a second pty whose ECHO state sudo
controls, which is why the pre-auth looked fine here. Every _other_ sudo call in the repo — 46 of
them, all `f"{util.SUDO} …"` — is non-pty, so any one of them that prompts is the same bug again.

### 2. On Python 3.14, invoke cannot forward stdin at all

The pre-auth's own `c.run("sudo -v", pty=True)` **hung deterministically** in the container: the
prompt printed, the password was typed, and nothing happened. `docker top` showed `sudo -v` still
sleeping, and — the tell — a sudo timestamp file already existed, so nothing was wrong with the
credentials.

Bisecting by interpreter (same invoke 3.0.3 throughout, installed with `uv tool install --python`):

| Python | `c.run("head -n1 …")` — invoke must forward stdin  |
| ------ | -------------------------------------------------- |
| 3.10   | works, and echoes the typed text (cause 1)         |
| 3.11   | works, echoes                                      |
| 3.12   | works, echoes                                      |
| 3.13   | works, echoes                                      |
| 3.14   | **hangs — nothing is ever forwarded to the child** |

Reproducing invoke's read path with the standard library alone found it in one run:

```python
n = struct.unpack("h", fcntl.ioctl(sys.stdin, termios.FIONREAD, b"  "))[0]
```

```
SystemError: buffer overflow
```

`FIONREAD` writes an `int` (4 bytes) into a 2-byte buffer. Every Python before 3.14 let that
overflow silently; 3.14 hardened `fcntl.ioctl` and raises. The exception kills invoke's stdin thread
on the very first keystroke, so nothing is ever written to the child — pty or not — and the child
waits forever. This is `terminals.bytes_to_read()`, upstream
[pyinvoke/invoke#1070](https://github.com/pyinvoke/invoke/issues/1070), with fixes open but
**unreleased as of invoke 3.0.3**.

`uv_python_default = "3.14"` in `setup.toml`, so `bootstrap.sh` installs invoke on exactly the
interpreter that has this bug. Every interactive prompt run through invoke on a current machine
hangs — including `ssh-keygen`, `ssh-copy-id` and `ssh-add`, which all used `pty=True` too.

## The design that follows

**One invariant: no command run through invoke may ever wait for something typed.** Not "use a pty",
which is a fix for one of the two causes and a coincidence for the other.

- **`util.run_interactive([...])`** runs an interactive child as a plain `subprocess` inheriting
  this process's stdin/stdout/stderr. The child owns the terminal exactly as if it had been typed at
  the shell: echo suppression is its business, and nothing races it. Verified working on 3.14, where
  the invoke version hangs.
- **`util.ensure_sudo()`** authenticates once, up front, through that helper — a GUI askpass where
  one can actually work, otherwise `sudo -v` on the terminal — and then **rebinds `util.SUDO` to
  `sudo -n`** for the rest of the process. That is the part that makes the invariant hold rather
  than merely being an intention: after it runs, no `c.run(f"{util.SUDO} …")` in the repo _can_
  prompt. A lapsed cache becomes an immediate, catchable failure instead of an invisible prompt
  inside a `hide=True` stream.
- **A keepalive thread** re-stamps the cache every 60 seconds, because sudo's own timeout is 15
  minutes and a full run on a slow corporate connection is much longer than that. Without it, `-n`
  would turn a mid-run lapse into a hard failure — the invariant would hold and the run would still
  break.
- **It refuses early** when there is no terminal, no usable askpass, no `NOPASSWD` rule and no root,
  naming the three ways out. The alternative is failing at whichever package happens to need root
  first, several minutes in.
- **As root, `util.SUDO` is empty.** A container built `FROM` a stock base image need not have sudo
  installed at all.

### The askpass helper needed a terminal fallback

`SUDO_ASKPASS`/`SSH_ASKPASS` are exported unconditionally by `~/.zshenv` (`zsh.configure`'s writer
ignores tags), so a headless WSL distro and every dev container get them too — pointing at a Zenity
dialog that cannot open. sudo's report of that is the unhelpful `sudo: no password was provided`.

`config/askpass-zenity.sh` now reads `/dev/tty` with echo off when no display is set, and exits
cleanly when there is no terminal either. It opens `/dev/tty` rather than testing for it: the device
node exists even with no controlling terminal, where opening it fails with `ENXIO`, so
`[ -e
/dev/tty ]` passes and the next line prints an error nobody can act on.

`[packages.zenity]` also moved to the `gui` tag — a headless distro was installing a GTK dependency
tree for a window it can never show.

## The other thing that waits for input: apt

`DEBIAN_FRONTEND` appeared **nowhere** in this repo, so every `apt install -y` ran with the
interactive frontend. `-y` answers apt's own "do you want to continue"; it does not answer a debconf
question (`tzdata`'s "Geographic area", `wireshark-common`'s dumpcap question,
`keyboard-configuration`) or dpkg's "a conffile you modified has a new version".

Confirmed by accident, and expensively: the `docker build` of _this investigation's own reproduction
container_ sat on tzdata's geographic-area prompt for 25 minutes before it was killed.
`docker build -q` prints nothing while that happens — the same "stuck with no output" shape as the
original report, from a different cause entirely.

`util.apt_command()` / `util.dpkg_command()` carry `DEBIAN_FRONTEND=noninteractive`,
`DEBIAN_PRIORITY=critical` and `--force-confold`/`--force-confdef`. The environment goes through
`env` rather than a `VAR=value sudo …` prefix (sudo's `env_reset` drops that) or a
`sudo VAR=value …` prefix (allowed only where sudoers grants `setenv`).

## What the container run then found

With the sudo path fixed, the same simulation got as far as writing `/etc/wsl.conf` and died on the
next line — `PermissionError: '/etc/wsl.conf'`, reading back the file it had just written.
`util.sudo_write()` wrote via `tempfile.NamedTemporaryFile` (mode 0600) plus `cp`, which preserves
the mode, so every system file this repo writes came out readable by root alone. It uses
`install -m 0644` now, as do the four hand-rolled variants of the same pattern in `wsl.py`,
`docker.py` and `certs.py`.

That bug had been there the whole time and no test could have found it: the file is only read back
by a non-root process on a machine where PULSE wrote it, which is a real WSL distro or this
container — never the development workstation, where `/etc/wsl.conf` doesn't exist.

## Testing

The pure state machine is unit-tested (`tests/unit/test_util.py`) with every sudo probe stubbed:
NOPASSWD vs a warm cache, authenticating through askpass vs the terminal, the root shortcut, the
refusal when nothing can ask, idempotence, and the apt command construction. What those tests
deliberately don't cover is the terminal behaviour itself — that is what the container is for, and
what the harness in this investigation exercised:

- `pty=True` and non-pty `c.run` against a password-protected sudo user, on five interpreters;
- `inv wsl.install` end to end, driven through a pty, answering the DNS/Proceed/password prompts;
- the askpass helper with and without a terminal.
