# Agent instructions for power-user-linux-setup

Cross-tool instructions for AI coding agents working in this repo (Claude Code, and anything else
that reads `AGENTS.md`). This repo's own `CLAUDE.md` is a plain symlink to `AGENTS.md` — not a file
containing Claude Code's `@AGENTS.md` import directive — so Claude Code and any other harness that
also happens to read a literal `CLAUDE.md` see byte-identical content, no special-case import syntax
required (see `~/AGENTS.md`'s "Project conventions" for the full rationale).

## Global conventions live in `~/AGENTS.md`

Anyone working in this repo already has `~/AGENTS.md` installed — this repo is literally what
deploys it (`[packages.agents-md]` in `setup.toml`, symlinked from `~/.claude/CLAUDE.md` the same
way this file symlinks from its own `CLAUDE.md`). It covers sudo/ssh askpass, the
`AGENTS.md`-over-`CLAUDE.md` convention itself, cross-session memory policy, and Bash/allowlist
discipline (don't `cd` out of a project, prefer several simple commands over one chained one).
Nothing universal is repeated below — only what's specific to this repo.

## AI agent tooling (`tasks/ai.py`)

`inv ai.install-skills` ensures `.agents/skills/` exists with `.claude/skills` symlinked to it
(Claude Code doesn't read `.agents/skills/` natively, only the symlink target) and installs every
skill declared via a `skills` field anywhere in `setup.toml` — home-directory-scoped (`~`), never
overwrites hand-written content.

**Skills are not authored here.** There is no `skills/` directory; every skill lives in
[`agent-skills`](https://github.com/TheodoreAD/agent-skills) and is installed from there by
`[packages.agent-skills]`. To change a skill, edit it in that repo and follow its `skill-authoring`
skill (edit → gate → commit → **push** → re-install → verify) — the installer clones from the
remote, so an unpushed edit reaches nothing. Editing the installed copy under `~/.agents/skills/` is
always wrong: it is overwritten by the next install and never leaves this machine. The
`source = "local"` mechanism still exists as an escape hatch for a skill that genuinely cannot be
published, and is deliberately unused.

Project-scoped scaffolding (a new Python project's own `AGENTS.md`/`CLAUDE.md`/`.agents/skills`
setup) isn't this repo's job anymore — see
[`scaffoldapy`](https://github.com/TheodoreAD/scaffoldapy), which stamps that at generation time
instead (`contributing/repo-family-architecture.md`). The cross-session-memory policy (don't use
Claude Code's auto-memory for durable repo knowledge — use `AGENTS.md` instead) is documented once,
globally, in `[packages.agents-md]` in `setup.toml` rather than repeated per-repo — see
`docs/claude-code.md`.

## Deployed dotfiles are generated — never edit `~/<file>` directly

Before editing any file under `~/` that this repo might have deployed (a dotfile, a shell config,
`~/AGENTS.md`, anything that looks hand-editable), grep `setup.toml` for a `[packages.*]` entry that
targets the path. **Grep the path itself, not a field name** — two different fields point at a
deployed file: `dest` (the `wrapper-script` method) and `dst` (inside a `config_files` mapping,
which any method may declare). A grep for `dest` alone silently misses every `config_files` package.

If an entry exists, the real place to edit is its repo-side source (`content_file`, or a
`config_files` mapping's `src` — e.g. `config/<file>`), not the deployed path. A direct edit to the
deployed path exists only on this machine: it never reaches the repo or the next machine, and every
PULSE writer (`inv tools.install`, `inv deploy.all`, `inv ai.install-skills`) now shows it as a diff
and asks before overwriting it — until 2026-08-25 `inv tools.install` wiped it silently, caught live
once only because the user asked "would this actually be installed?", not because anything failed
loudly. `~/AGENTS.md` specifically is `[packages.agents-md]`, **assembled** from the fragments in
`config/agents-md/` rather than copied from one file — edit the fragment that owns the rule (see
that directory's `README.md`), never the deployed file.

**Re-deploy by running a task, not by hand-replicating its write logic — and not by calling a task's
private writer from `python -c` either.** One command covers every mechanism:

```shell
inv deploy.status                       # what's drifted, read-only
inv deploy.all --name <pkg> [--yes]     # redeploy one package's paths (content_file, config_files, skills)
inv deploy.all                          # everything this repo deploys under ~
```

`inv deploy.all` shows the diff before it asks, never overwrites content it can't prove it wrote,
and records what it deployed so the next `deploy.status` can tell drift from a repo-side change.
Confirmed live twice: 2026-08-23, `config/wezterm.lua` had no redeploy path at all (the install-time
writer skips any destination that already exists) and a one-off `cp` was rejected with "there should
be a pulse invoke task that deploys the wezterm config"; 2026-08-24, redeploying `~/AGENTS.md` by
calling `tools._install_wrapper_script` from `python -c` — to avoid `inv tools.install` re-running
every installer — was rejected the same way, and `deploy.all` is the result. The whole point of the
repo is that every change this machine has is reproducible from a declared, re-runnable command; a
manual copy or an ad-hoc Python call is a change nobody can re-run.

**`deploy.status` covers only the whole files declared in `setup.toml` — 18% of the surface a config
lifecycle could ever touch, and not even all of what `deploy.py` writes.** Before concluding that a
path is "not PULSE-managed", run `inv home.list-claims` (read-only): it is the registry of all ten
ways this repo writes into the home directory — declared whole-file deploys, undeclared ones whose
destination is decided at run time, `util.ensure_block` marker regions, merges into co-owned JSON,
regex surgery on one key of an app-owned file, `gsettings`/`dconf`, symlinks, installed trees,
generated files, and skills fetched by the `skills` CLI — each classified by writer, authority and
portability tier. `deploy.status`'s "not deployed by PULSE" is true of its own registry and
misleading about the repo.

**A destination declared in `setup.toml` is one `inv verify.all` requires to exist** at the end of
`inv setup`'s packages phase. A file written only in some situations (a corporate-only systemd unit)
or at a path discovered on the machine (a glob-matched IDE config directory) therefore goes through
`deploy.py` without being declared — construct a `deploy.Managed` in the writing module and call
`deploy.deploy()`. Declaring it instead fails `inv setup` on every machine that legitimately lacks
it. Design rationale, the measured breakdown, and what is deliberately **not** claimed
(skill-written config, `/etc` targets, the contents of installed trees) are in
[`contributing/home-claims.md`](contributing/home-claims.md) — read that before extending the
registry or adding a tenth writer.

## PULSE tag/method architecture

The `setup.toml` config/tag system is fully documented in the repo — don't re-derive it by reading
`tasks/*.py` from scratch:

- `setup.toml`'s header comment — field reference for every method (`apt`, `apt-repo`, `deb-github`,
  `deb-url`, `archive`, `uv-tool`, `nvm`, `script`, `binary`, `git-clone`, `wrapper-script`,
  `gnome-extension`, `apparmor-profile`, `zsh`), plus the tag catalog.
- `docs/configuration.md`, section "Tags, `enabled`, and which tasks actually respect either" —
  which tasks go through `util.packages_by_method()` (tag+enabled aware) vs which read a
  `[packages.*]` section directly and ignore tags (`node.install`, `docker.configure`, `fonts.*`) or
  ignore tags but not `enabled` (`zsh.configure`'s `zshrc`/`zshenv`/`zprofile` writer).

Only 7 tags actually gate anything: `gui`, `desktop`, `gnome`, `workstation`, `corporate`, `ide`,
`windows-native`. Everything else in the tag catalog is organizational only. Building an environment
profile (headless, dev container, WSL) by setting `PULSE_EXCLUDE_TAGS` alone is not sufficient —
check the docs/configuration.md table for what each task actually respects before assuming.

**Installing a new tool for this repo's own use (not the machine's) still goes through this pipeline
— never a manual `apt install`/`sudo apt install`/`uv tool install`/`pip install`.** Add a
`[packages.<name>]` entry to `setup.toml` (matching an existing entry's `method` for the same kind
of tool — e.g. `uv-tool` for a PyPI-distributed CLI, see `gnome-extensions-cli`/`nox`/`glances` for
the shape) and run the corresponding install task (`inv python.install-tools` for every `uv-tool`
package, `inv apt.install-base` for `apt`, etc.) instead. This is not a style preference — running
the install by hand outside `setup.toml` defeats the entire point of the repo, which is that every
install this machine has is declared in one reproducible, re-runnable place. Caught live during the
`python-conventions` pilot (`contributing/quality-tooling.md`): `shellcheck`/`shfmt` were first
installed via a direct `uv tool install`, then corrected on the spot to go through `setup.toml` and
`inv python.install-tools` instead.

## Post-install verification (`inv verify.all`)

`tasks/verify.py` runs as the last step of `inv setup`'s (and `inv wsl.install`'s) `packages` phase
— a hard, convention-based check that every package a run installed also actually _works_, not just
that it's present. No fallback chain: first failure aborts immediately, the deliberate opposite of
`apt.py`'s `warn=True`-and-continue pattern.

**It is not a read-only command — don't re-run it to re-read or filter its own output.** It invokes
every installed package, and some of those open windows on the user's desktop: `freelens --version`
launched the Freelens GUI and still exited 0, so the check passed silently while a window appeared
(2026-08-28, caught by the user seeing two of them after two runs). Redirect the first run's output
and grep that instead. To test one package's check, run that command on its own rather than the
whole task.

The rest of the GUI-tagged set was audited on 2026-08-30 and is clean — the class is `freelens` and
`telegram-desktop`, both fixed with a per-package `verify_cmd`. **Before adding a new GUI package,
probe its check against a throwaway `Xvfb` display rather than the live session**;
`contributing/verify.md`'s "Auditing the rest of the class, without launching anything" has the
three commands and the result table.

[`docs/dev-container.md`'s "Automated functional verification"
section](docs/dev-container.md#automated-functional-verification-inv-verifyall) is the published
"what it is / why it exists" page. **Full writeup, including every gotcha the first implementation
pass hit (a real machine freeze from an unrecognized-flag hang, why `gnome-extension` always skips,
container-only `PATH` gaps for `go`/`node`, why `git-clone`/`wrapper-script` default to an existence
check instead of invocation) and how testing — not code review — caught each one, is
[`contributing/verify.md`](contributing/verify.md)** — read that before re-deriving this task's
design from scratch or "simplifying" something that was already a deliberate tradeoff.

## WSL support

`tasks/wsl.py` (`inv wsl.check` diagnostic, `inv wsl.fix` for the fixable subset —
`systemd`/`generateResolvConf` in `/etc/wsl.conf`) and `docs/wsl.md` already cover running this
repo's setup under WSL2 — distro/apt check, systemd, DNS, Docker Desktop-vs-native, WSLg, fonts.
`util.require_systemd()`/`util.require_apt()` (`tasks/util.py`) make the systemd- and apt-dependent
install tasks fail fast with an actionable message instead of partway through a raw error; these are
generic capability checks, not WSL-specific branching. If asked about WSL support again, extend that
module rather than re-researching from scratch.

## Nothing run through invoke may wait for typed input

**A password prompt, a passphrase prompt, a debconf question — none of them may be reached from
inside a `c.run(...)`, with or without `pty=True`.** Two independent reasons, both reproduced in a
container rather than reasoned about (full write-up:
[`contributing/interactive-input.md`](contributing/interactive-input.md)):

- invoke echoes stdin itself for any non-pty run from a terminal (`should_echo_stdin` is
  `(not using_pty) and isatty(stdin)`), while sudo reads the _same_ terminal through `/dev/tty` —
  two readers racing, printing the password in plain text whenever invoke wins the read.
- on **Python 3.14** invoke can't forward stdin at all: `terminals.bytes_to_read()` hands a 2-byte
  buffer to a `FIONREAD` ioctl that writes 4, which 3.14 made a `SystemError`. The stdin thread dies
  on the first keystroke and the child waits forever. Upstream pyinvoke/invoke#1070, unreleased —
  and `uv_python_default = "3.14"`, so it is the default path here.

So:

- **Interactive child → `util.run_interactive([...])`** (a plain `subprocess` inheriting the real
  terminal). `ssh-keygen`, `ssh-copy-id`, `ssh-add` and the sudo pre-auth all go through it.
- **Anything needing root → call `util.ensure_sudo()` first**, then keep using `f"{util.SUDO} …"`.
  It authenticates once outside invoke, rebinds `util.SUDO` to `sudo -n` so no later call _can_
  prompt, and keeps the credential cache warm for the whole run. Never add a new `sudo -v`/`sudo -A`
  call of your own.
- **apt/dpkg → `util.apt_command(...)` / `util.dpkg_command(...)`**, never a hand-written
  `f"{util.SUDO} apt …"`. They carry `DEBIAN_FRONTEND=noninteractive` and
  `--force-confold`/`--force-confdef`; `-y` covers apt's own question, not debconf's or dpkg's, and
  a conffile prompt in a hidden stream is indistinguishable from a hang.
- **Writing a root-owned file → `util.sudo_write()`**, which uses `install -m 0644`. A tempfile is
  0600 and `cp` preserves that, which left `/etc/wsl.conf` unreadable by the user who had just
  written it.

## Network diagnosis before anything is installed (`tasks/netdoctor.py`)

`python3 tasks/netdoctor.py` (or `inv net.check`) reports which of the hosts a run needs are
reachable, by what route, and the command that fixes each failure — including the Windows side of a
WSL distro. `bootstrap.sh` runs it as an advisory preflight. Published page:
[`docs/net-doctor.md`](docs/net-doctor.md).

**It is standard-library-only, Python 3.10 syntax, and imports nothing from `tasks/`** — it has to
run on a fresh Ubuntu 22.04 WSL distro before uv, invoke or this repo's venv exist. Unit tests
enforce each of those three, so a `from . import util` or a `tomllib` added here fails the gate
rather than the next fresh machine. The dependency direction is one-way: `tasks/*.py` may import
`netdoctor` (`wsl.py` does, for the raw DNS query), never the reverse.

## Dev container distribution pipeline

Two paths for running PULSE inside a dev container, both landed: a `devcontainer.json` +
`postCreateCommand` flow (`bootstrap-devcontainer.sh`, the recommended path — layers PULSE onto
_any_ consumer's base image without forcing a shared maintained image on them) and a build-time bake
via `docker/Dockerfile` (canonical example, local-WIP-testing vehicle, and hand-roll template —
reuses `bootstrap-devcontainer.sh --local`, not a separate script). `tasks/devcontainer.py` is the
supporting invoke namespace: `CONTAINER_EXCLUDE_TAGS` (single source of truth for the recommended
tag exclusion), `print-exclude-tags` (machine-readable, consumed by the bash script), `render-docs`
(regenerates the tag table in `docs/dev-container.md` via `util.ensure_block` with
`util.MarkerStyle.HTML` — a `#`-prefixed marker would render as a heading in Markdown), `check`
(read-only dry run, same shape as `inv wsl.check`), and `mounts` (host-side interactive helper —
discovers credential-shaped directories/sockets on the host and prints a devcontainer.json
`mounts`/`remoteEnv` fragment; never writes/edits a file itself — verified end-to-end via
`@devcontainers/cli up`/`exec`, including a live `ssh-add -l` against a forwarded agent socket).

[`docs/dev-container.md`](docs/dev-container.md) is the published page — read that before extending
this rather than re-deriving the design. **`.github/workflows/devcontainer.yml` is intentionally
`workflow_dispatch`-only right now** (the `push` trigger is written in but commented out, with a
re-enable note) — this is deliberate, not an oversight, while the pipeline is still under active
iteration; don't "fix" it by uncommenting the trigger without checking with the user first.

## CLI permission allowlist pipeline

`cli-allowlist/` (tracked, unlike the research dump it grew out of) keeps a
read_only/write/dangerous classification for every CLI tool this machine has installed — base system
included, not just what `setup.toml` installs — so Claude Code / Copilot permission rules can be
generated from real `--help` output instead of hand-written guesses, and `inv
allowlist.apply` can
keep `~/.claude/settings.json` current from it automatically. `tasks/
allowlist.py` implements it as
`inv allowlist.{extract,classify,review,render,apply,status}`.

[`docs/cli-allowlist.md`](docs/cli-allowlist.md) is the published "what it is / how to run it" page.
**Full writeup, including every gotcha the first implementation pass hit and how testing (not code
review) caught each one, is [`contributing/cli-allowlist.md`](contributing/cli-allowlist.md) — read
that before re-deriving this architecture from scratch or "fixing" something that was already a
deliberate tradeoff** (why there's no PreToolUse hook, why dangerous/write tiers render as `ask`
rather than `deny`, why `--bare` isn't used for the classify step, why the `apply` manifest lives
outside the repo).

## Running the test suite

`tests/README.md` has the exact commands. Short version: `inv dev-env.setup` once after cloning
(`uv sync` + `direnv allow`), then plain `pytest`/`python` — not `uv run pytest`/ `uv run python`.
`tasks` is editable-installed into `.venv` via `pyproject.toml`, and direnv (`.envrc` +
`[packages.direnv]` in `setup.toml`) puts `.venv/bin` on `PATH` automatically — no `sys.path` trick
or `uv run` wrapper needed for any command in this repo, including from an agent's Bash tool. The
one gotcha: Claude Code replays a shell snapshot captured once per session instead of re-sourcing
dotfiles per command, so a session started _before_ `.envrc`/`direnv allow` existed won't pick this
up retroactively — that's a stale-snapshot timing issue, not a reason to add manual activation back
in. If `pytest`/`python` aren't resolving from `.venv/bin` in an agent session, the fix is a new
session, not `source .venv/bin/activate` workarounds.

## Code quality

Before considering a change done, run:

```shell
inv quality.precommit   # fix (ruff --fix, ruff format, dprint fmt), then check — must pass clean
```

**Never call `ruff` or `dprint` directly** — always go through `inv quality.*`. They bake in
required flags (e.g. `dprint`'s `--config-discovery=ignore-descendants`, needed because
`cli-allowlist/rules/dprint.json` — an unrelated per-tool classification file — would otherwise get
misread as a nested dprint sub-project config and abort the whole run) so the correct invocation
lives in one place instead of every contributor's/agent's memory. Same principle for anything else
in this repo an `inv` task already exists for — prefer the task over the bare command it wraps
(exception: the test suite, see below — `pytest`/`python` direct is the documented convention there,
not something this rule overrides).

Full details (rule selection, `dprint.json`, the individual `lint_check`/`lint_apply`/
`format_check`/`format_apply`/`test`/`fix`/`check` tasks) are in [CONTRIBUTING.md](CONTRIBUTING.md)
— read that rather than re-deriving the setup from scratch. The tasks themselves live in
[github.com/TheodoreAD/repo-tasks](https://github.com/TheodoreAD/repo-tasks)'s `quality.py`, a git
dev dependency (`tasks/__init__.py` imports it lazily — see the comment there — so bootstrap.sh's
zero-install path, which never runs `uv sync`, still works without it).

## Never run GNOME session-mutating tasks yourself

Don't execute `inv gnome.install-extensions`, `inv gnome.configure`, `inv gnome.status`'s mutating
siblings, `inv screenshot.enable`/`inv screenshot.disable`, or any other invoke task that writes to
the live GNOME session (gsettings/dconf/`gnome-extensions` CLI) via the Bash tool — treat this as
the default for any future task that mutates GNOME keybindings/settings too. These require a live
Wayland/X11 session; running the mutating ones via the Bash tool can interact unexpectedly with the
running desktop. Read-only tasks in the same modules (`inv screenshot.status`, dry-run via
`PULSE_DRY_RUN=1`) are fine to run directly — the boundary is mutation of the live session, not the
module. After making changes to `setup.toml`/a `tasks/*.py` module that touches gsettings/dconf,
tell the user what to run and why, but don't run the mutating command yourself.

## XDG Base Directory Specification for all user-scoped installs

No tool installation should create its own dotdir directly in `~` (e.g. `~/.dprint`, `~/.nvm`) —
home root is for dotfiles (config), not program installations. Multi-file runtimes (Go, nvm) install
to `~/.local/share/<tool>` with a binary symlinked into `~/.local/bin/`; single-binary tools set
`single_binary = true` and point the installer's env var at `~/.local` so the binary lands directly
in `~/.local/bin/`, no symlink needed. In `setup.toml`, use a `[packages.<name>.env]` subtable for
installer env vars (`~` paths expand automatically). `symlink_from` is only for multi-file installs
where the binary needs linking into `~/.local/bin`.

## Cross-repo family conventions: strict and mandatory, no per-repo allowances

When a design task is about _convergence_ across the `repo-tasks`/`*-polite-mcp`/`scaffoldapy`
family specifically (shared tooling, shared config conventions, shared invoke tasks) — as opposed to
a single repo's own internal architecture, where normal per-project judgment and "best tool per
concern" still apply (see `~/AGENTS.md`) — default to one mandatory, identical composite every
consumer repo uses unmodified, not a menu of leaf pieces each repo composes differently, even when
real current repos already diverge. The fact that repos diverge is the problem needing fixed, not
evidence flexibility should be preserved. If a naive mandatory version would break on some repos
(missing config, missing file types), the fix is making the shared logic degrade gracefully (e.g.
`shell_check` no-ops cleanly on a repo with zero `.sh` files), not exempting those repos from the
shared composite. Don't propose "each repo picks what it needs" as the design without being asked
for it.

## Git workflow

Direct, focused commits straight to `master` are the normal way to land changes here — the owner has
bypass permissions on the PR-required branch protection rule specifically for this. Open a PR
instead only when either (a) someone other than the owner is contributing, or (b) a batch of related
commits is worth bundling behind a PR description for reviewability. Don't default to "always open a
PR" — ask if unsure which case applies, don't assume the stricter workflow.
