# Agent instructions for power-user-linux-setup

Cross-tool instructions for AI coding agents working in this repo (Claude Code, and anything else
that reads `AGENTS.md`). This repo's own `CLAUDE.md` is a plain symlink to `AGENTS.md` — not a file
containing Claude Code's `@AGENTS.md` import directive — so Claude Code and any other harness that
also happens to read a literal `CLAUDE.md` see byte-identical content, no special-case import
syntax required. See `tasks/ai.py` for why this replaced the import-line approach.

## Global conventions live in `~/AGENTS.md`

Anyone working in this repo already has `~/AGENTS.md` installed — this repo is literally what
deploys it (`[packages.claude-global-md]` in `setup.toml`, symlinked from `~/.claude/CLAUDE.md`
the same way this file symlinks from its own `CLAUDE.md`). It covers sudo/ssh askpass, the
`AGENTS.md`-over-`CLAUDE.md` convention itself, cross-session memory policy, and Bash/allowlist
discipline (don't `cd` out of a project, prefer several simple commands over one chained one).
Nothing universal is repeated below — only what's specific to this repo.

## AI agent tooling (`tasks/ai.py`)

`inv ai.skills` and `inv ai.init` scaffold the conventions this repo already follows — a minimal
`AGENTS.md`, a `CLAUDE.md` symlinked to it, and `.agents/skills/` with `.claude/skills` symlinked to
it (Claude Code doesn't read `.agents/skills/` natively, only the symlink target) — for _other_
projects on this machine, not just this one. Both tasks check for existing files/symlinks first and
never overwrite hand-written content. `init`'s `CLAUDE.md` symlink means nothing can be appended
below it the way the old `@AGENTS.md`-import form allowed — a genuinely Claude-specific addendum
now belongs in `AGENTS.md` itself (shared) or a separate `.claude/`-scoped file, not in `CLAUDE.md`.
The cross-session-memory policy (don't use Claude Code's auto-memory for durable repo knowledge —
use `AGENTS.md` instead) is documented once, globally, in `[packages.claude-global-md]` in
`setup.toml` rather than repeated per-repo — see `docs/claude-code.md`.

## PULSE tag/method architecture

The `setup.toml` config/tag system is fully documented in the repo — don't re-derive it by reading
`tasks/*.py` from scratch:

- `setup.toml`'s header comment — field reference for every method (`apt`, `apt-repo`,
  `deb-github`, `deb-url`, `archive`, `uv-tool`, `nvm`, `script`, `binary`, `git-clone`,
  `wrapper-script`, `gnome-extension`, `apparmor-profile`, `zsh`), plus the tag catalog.
- `docs/configuration.md`, section "Tags, `enabled`, and which tasks actually respect either" —
  which tasks go through `util.packages_by_method()` (tag+enabled aware) vs which read a
  `[packages.*]` section directly and ignore tags (`node.install`, `docker.configure`, `fonts.*`)
  or ignore tags but not `enabled` (`zsh.configure`'s `zshrc`/`zshenv`/`zprofile` writer).

Only 7 tags actually gate anything: `gui`, `desktop`, `gnome`, `workstation`, `corporate`, `ide`,
`windows-native`. Everything else in the tag catalog is organizational only. Building an
environment profile (headless, dev container, WSL) by setting `PULSE_EXCLUDE_TAGS` alone is not
sufficient — check the docs/configuration.md table for what each task actually respects before
assuming.

## WSL support

`tasks/wsl.py` (`inv wsl.check` diagnostic, `inv wsl.fix` for the fixable subset —
`systemd`/`generateResolvConf` in `/etc/wsl.conf`) and `docs/wsl.md` already cover running this
repo's setup under WSL2 — distro/apt check, systemd, DNS, Docker Desktop-vs-native, WSLg, fonts.
`util.require_systemd()`/`util.require_apt()` (`tasks/util.py`) make the systemd- and apt-dependent
install tasks fail fast with an actionable message instead of partway through a raw error; these
are generic capability checks, not WSL-specific branching. If asked about WSL support again, extend
that module rather than re-researching from scratch.

## CLI permission allowlist pipeline

`cli-allowlist/` (tracked, unlike the gitignored `reference/` research dump it grew out of) keeps a
read_only/write/dangerous classification for every CLI tool this machine has installed — base
system included, not just what `setup.toml` installs — so Claude Code / Copilot permission rules
can be generated from real `--help` output instead of hand-written guesses, and `inv
allowlist.apply` can keep `~/.claude/settings.json` current from it automatically. `tasks/
allowlist.py` implements it as `inv allowlist.{extract,classify,review,render,apply,status}`.

[`docs/cli-allowlist.md`](docs/cli-allowlist.md) is the published "what it is / how to run it"
page. **Full writeup, including every gotcha the first implementation pass hit and how testing
(not code review) caught each one, is [`contributing/cli-allowlist.md`](contributing/cli-allowlist.md)
— read that before re-deriving this architecture from scratch or "fixing" something that was
already a deliberate tradeoff** (why there's no PreToolUse hook, why dangerous/write tiers render
as `ask` rather than `deny`, why `--bare` isn't used for the classify step, why the `apply`
manifest lives outside the repo).

## Running the test suite

`tests/README.md` has the exact commands. Short version: `inv python.dev-venv` once after
cloning (`uv sync` + `direnv allow`), then plain `pytest`/`python` — not `uv run pytest`/
`uv run python`. `tasks` is editable-installed into `.venv` via `pyproject.toml`, and direnv
(`.envrc` + `[packages.direnv]` in `setup.toml`) puts `.venv/bin` on `PATH` automatically — no
`sys.path` trick or `uv run` wrapper needed for any command in this repo, including from an
agent's Bash tool. The one gotcha: Claude Code replays a shell snapshot captured once per session
instead of re-sourcing dotfiles per command, so a session started _before_ `.envrc`/`direnv allow`
existed won't pick this up retroactively — that's a stale-snapshot timing issue, not a reason to
add manual activation back in. If `pytest`/`python` aren't resolving from `.venv/bin` in an agent
session, the fix is a new session, not `source .venv/bin/activate` workarounds.

## Code quality

Before considering a change done, run:

```shell
inv quality.fix   # apply (ruff --fix, ruff format, dprint fmt), then check — must pass clean
```

**Never call `ruff` or `dprint` directly** — always go through `inv quality.*`. They bake in
required flags (e.g. `dprint`'s `--config-discovery=ignore-descendants`, needed because
`cli-allowlist/rules/dprint.json` — an unrelated per-tool classification file — would otherwise get
misread as a nested dprint sub-project config and abort the whole run) so the correct invocation
lives in one place instead of every contributor's/agent's memory. Same principle for anything else
in this repo an `inv` task already exists for — prefer the task over the bare command it wraps
(exception: the test suite, see below — `pytest`/`python` direct is the documented convention
there, not something this rule overrides).

Full details (rule selection, `dprint.json`, the individual `lint_check`/`lint_apply`/
`format_check`/`format_apply`/`test`/`apply`/`check` tasks) are in
[CONTRIBUTING.md](CONTRIBUTING.md) — read that rather than re-deriving the tasks/quality.py setup
from scratch.

## Git workflow

Direct, focused commits straight to `master` are the normal way to land changes here — the owner
has bypass permissions on the PR-required branch protection rule specifically for this. Open a PR
instead only when either (a) someone other than the owner is contributing, or (b) a batch of
related commits is worth bundling behind a PR description for reviewability. Don't default to
"always open a PR" — ask if unsure which case applies, don't assume the stricter workflow.
