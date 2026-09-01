# Container harness: the two environments this repo can't dogfood

Everything under `tests/unit/` runs in-process against stubs. Two whole classes of behaviour can't
be tested that way, and both have produced real, user-visible bugs:

- **A terminal.** Whether a password is echoed, whether a prompt is answerable, and whether a run
  hangs waiting for input nobody can see are all properties of a real pty. A pipe makes every one of
  them impossible to observe — the failure looks like success.
- **A WSL-shaped machine.** A distro's default user has an actual sudo _password_, no systemd, no
  display, and a Windows host on the other side of the network. The development workstation has a
  warm sudo cache and a desktop session; every dev-container base image grants `NOPASSWD`. Neither
  exercises the path that broke.

These scripts are what found (and then verified the fixes for) the sudo hang, the plaintext
password, apt's debconf prompts, root-only file modes, and two broken container bake paths. See
[`contributing/interactive-input.md`](../../contributing/interactive-input.md) for what each of
those turned out to be.

Nothing here runs in CI or under `pytest` — they need docker and take minutes. Reach for them when
changing anything about sudo, prompts, bootstrap ordering, or the network diagnostic.

## `drive.py` — run a command under a real pty and answer its prompts

```shell
python3 tests/containers/drive.py --log /tmp/run.log --timeout 1800 \
  --on 'Proceed\?=y' --on 'password for dev=devpass' \
  -- docker run --rm -i -t <image> <command>
```

Each `--on REGEX=REPLY` fires once, when the regex first matches the accumulated output. Output is
streamed to `--log` as it arrives, so a hang is visible _while_ it hangs; the run gives up after
three minutes with no output and says so in the log.

## `Dockerfile.wsl` — a stand-in for a fresh WSL distro

A password-protected sudo user (`dev` / `devpass`), no systemd, no display. `WSL_DISTRO_NAME` is set
at run time rather than baked, so `util.is_wsl()` is true without touching `/proc/version`.

```shell
docker build -q --build-arg BASE=ubuntu:24.04 -f tests/containers/Dockerfile.wsl \
  -t pulse-wsl-sim tests/containers

python3 tests/containers/drive.py --log /tmp/wsl.log --timeout 2400 \
  --on 'Install repo-tasks=n' --on "Override WSL.s own DNS=" --on 'Proceed\?=y' \
  --on 'password for dev=devpass' --on 'Install all skills=n' \
  -- docker run --rm -i -t -e WSL_DISTRO_NAME=Ubuntu -e TERM=xterm \
     -v "$PWD:/src:ro" pulse-wsl-sim bash -lc \
     'cp -a /src /home/dev/pulse && rm -rf /home/dev/pulse/.venv /home/dev/pulse/.git && \
      cd /home/dev/pulse && bash bootstrap.sh --invoke-only && inv wsl.install'
```

What to look for: the sudo password is asked **once**, nothing echoes it, and the run reaches "next
steps" with exit 0.

`BASE` exists for checking an older release deliberately, not because one is supported: this repo
targets 24.04, and a run against `ubuntu:22.04` stops partway through at a package that release's
archives don't carry (`eza`). What _is_ worth running there is `tasks/netdoctor.py` on its own —
that module is the one thing that meets whatever python3 a distro happens to ship.

## Answering "what does a real WSL distro actually have?" without Windows

The simulation is a container with packages this repo chose to install, so it can't answer that.
Ubuntu publishes the real thing's package list, which can:

```shell
curl -fsSL https://cloud-images.ubuntu.com/wsl/noble/current/ubuntu-noble-wsl-amd64-wsl.manifest \
  | grep -E '^python3\s'
```

529 packages for noble, and that is how "a WSL distro ships python3 3.12.3" stopped being an
assumption. Swap `noble` for another release; `unpacked/` beside it has the rootfs itself if a
question needs more than the package list.

## `fakecorp.py` — the corporate network, on localhost

Serves the two shapes the network doctor has to recognise: a proxy answering every `CONNECT` with
`407` + `Proxy-Authenticate: Negotiate, NTLM` on `:3128`, and a TLS server on `:443` presenting a
self-signed **Corp Root Inspection CA** certificate. Point `/etc/hosts` at it with docker's
`--add-host` and run the doctor against it:

```shell
# PyPI blocked outright (connection refused), GitHub fine
docker run --rm -v "$PWD:/src:ro" --add-host pypi.org:127.0.0.1 pulse-wsl-sim \
  bash -lc 'python3 /src/tasks/netdoctor.py --quick --advisory'

# TLS interception
docker run --rm -v "$PWD:/src:ro" --add-host pypi.org:127.0.0.1 pulse-wsl-sim bash -lc \
  'python3 /src/tests/containers/fakecorp.py & sleep 3; python3 /src/tasks/netdoctor.py --quick --advisory'

# an authenticating proxy
docker run --rm -v "$PWD:/src:ro" pulse-wsl-sim bash -lc \
  'python3 /src/tests/containers/fakecorp.py & sleep 3;
   http_proxy=http://127.0.0.1:3128 https_proxy=http://127.0.0.1:3128 \
   python3 /src/tasks/netdoctor.py --quick --advisory'

# nothing at all
docker run --rm --network none -v "$PWD:/src:ro" pulse-wsl-sim \
  bash -lc 'python3 /src/tasks/netdoctor.py --quick --timeout 2 --advisory'
```

Each should produce exactly **one** finding naming the right cause. Two findings for one cause is
the regression to watch for: an early version reported a TLS-trust failure as a blocked package
index as well, and an all-DNS failure as eight separate problems.
