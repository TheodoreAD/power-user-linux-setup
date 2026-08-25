---
status: idea
updated: 2026-08-23
depends_on: [repo-tasks]
---

## Context

`bootstrap.sh` installs exactly one of two uv tools, chosen by `setup.toml`'s `install_repo_tasks`
default, the `--repo-tasks`/`--invoke-only` flags, or an interactive prompt when there's a TTY:

```shell
if [ "${INSTALL_REPO_TASKS}" = "true" ]; then
  uv tool install --python "${UV_PYTHON_DEFAULT}" --force --with-executables-from invoke \
    'repo-tasks @ git+https://github.com/TheodoreAD/repo-tasks'
else
  uv tool install --python "${UV_PYTHON_DEFAULT}" --force invoke --with python-dotenv
fi
```

Both branches provide the same two executables, `inv` and `invoke`. Neither branch removes the other
tool.

[PITFALL: two uv tools can both claim `inv`/`invoke`; whichever was `--force`-installed last owns
the `~/.local/bin` symlinks, silently, with no warning from uv and nothing in `uv tool list` marking
the loser as shadowed.]

The failure this produces is badly mislocalized. Every repo in the family has a `tasks.py` that is
just `from repo_tasks import ns`, resolved from whatever `inv` is on `PATH`. If bare `invoke` wins
the symlink, that import fails in _every_ repo at once, and the traceback points at the repo's own
`tasks.py` rather than at the machine's tool state — which is where the actual problem is.

**Sibling failure mode, same symptom, different mechanism.** The now-retired
`cross-directory-command-execution` plan (evidence preserved in `contributing/global-agents-md.md`,
"Running a command against a different repo than the session's project") found the other half of
this independently the same day: invoke resolves `tasks.py` by walking up from **cwd**, regardless
of which binary runs, so running `inv` against another repo silently collects the _calling_ repo's
tasks. The two compose — **cwd decides which `tasks.py` is found; the binary decides whether that
`tasks.py` can import `repo_tasks`** — and both fail silently, which is why either one alone is easy
to misdiagnose as the other. Relevant to this plan's `repo-tasks.doctor` idea below: a check that
reports only the shadowing case would still leave the cwd half undiagnosed, and the two are hard to
tell apart from the symptom.

Found live 2026-08-23, from the other direction: this machine had `invoke` v3.0.3 installed
standalone and **no `repo-tasks` tool at all**, despite `setup.toml`'s default preferring it. Every
family repo that appeared to work was working only because it carried `repo-tasks` in its own dev
dependency group — the exact posture `contributing/repo-family-architecture.md` says belongs only to
this repo and `repo-tasks` itself. It surfaced while taking `scaffoldapy` off that crutch: with the
dev dependency gone, `inv` in that repo resolved to bare invoke and could not import `repo_tasks`.

Resolved by hand for now — `uv tool uninstall invoke`, then `scaffoldapy`'s own committed
`bootstrap-repo-tasks.sh` — which leaves the machine correct but leaves the hole in `bootstrap.sh`
open: a later `bootstrap.sh --invoke-only` run puts it straight back, and so would reinstalling
`invoke` for any unrelated reason.

The same gap exists one level down, in `repo-tasks`' own installers: `selfinstall.update` (the
human-facing `inv repo-tasks.update`) and `_STAMP_TEMPLATE` (what every consumer's committed
`bootstrap-repo-tasks.sh` runs in CI) both `uv tool install --force` without checking for a
separately-installed `invoke` either. Fixing only `bootstrap.sh` would leave two other paths that
can recreate the split.

## Open questions

- **Where the guard actually lives.** `bootstrap.sh` is the machine-setup entrypoint and already has
  the prompt/unattended/flag machinery; `repo-tasks`' `selfinstall.py` owns the tool's own install
  lifecycle and is what CI and `inv repo-tasks.update` go through. Both need it, but only one should
  own the logic.

  [NEEDS CLARIFICATION: does `bootstrap.sh` implement the check itself, or does `repo-tasks` grow a
  task/flag that `bootstrap.sh` composes — the same relationship it already has with `repo-tasks`'
  own installer, per `contributing/repo-family-architecture.md`'s "Two installers, two scopes"? The
  second keeps the "never reach into repo-tasks' internals" rule intact, but the check has to run
  _before_ `repo-tasks` exists on the machine, which is exactly when a `repo-tasks` task can't be
  invoked.]

- **What the unattended default should do.** Stated preference: remove-by-default when there's no
  TTY, prompt when there is — matching apt/dnf's shape and `bootstrap.sh`'s existing `-t 0` branch.

  [NEEDS CLARIFICATION: is silently uninstalling another tool acceptable in the `--invoke-only`
  direction too? Removing `repo-tasks` to install bare `invoke` breaks every family repo's
  `tasks.py`, which is a much bigger blast radius than the reverse. It may want to warn and refuse
  rather than proceed unattended.]

- **CI.** The stamped `bootstrap-repo-tasks.sh` runs on a fresh runner where no conflicting `invoke`
  can plausibly exist.

  [NEEDS CLARIFICATION: is the guard worth the extra lines there at all, or should the stamp
  template stay minimal and the check live only in the two paths that run on a real machine?]

- **Detection mechanism.** `uv tool list` output parsing is the obvious approach, but it's a
  human-readable format with no stability guarantee.

  [NEEDS CLARIFICATION: does `uv tool list` have a machine-readable mode (or a stable-enough shape)
  as of the current uv version, or is checking `~/.local/share/uv/tools/invoke/` for existence the
  more honest test?]

## Recommended direction

Roughly five lines in each of the two real-machine paths, plus a decision on the third:

1. Before installing either tool, detect whether the _other_ one is present as a separate uv tool.
2. With a TTY, prompt (default yes to removing it, since leaving both is never what anyone wants).
   Without one, remove it and say so on stdout — never leave both installed silently.
3. Mirror the same check in `repo-tasks`' `selfinstall.update`, so the human-facing update path
   can't recreate the split either.

Worth doing in the same pass, since it's the same "the machine's tool state disagrees with what
every repo assumes" class of problem: `repo-tasks` grows an `inv repo-tasks.doctor` (or extends
`repo-tasks.status`, which already exists for stamped-vs-installed drift) that reports the shadowing
case explicitly. That turns the mislocalized `ImportError` above into one command with an answer.

[DEFERRED: `bootstrap-repo-tasks.sh` also stamps `uv tool install` without `--python`, while
`bootstrap.sh` passes `--python "${UV_PYTHON_DEFAULT}"`. Harmless on this machine today, where uv's
default already matches `setup.toml`'s 3.14, but the two installers can diverge on a machine where
it doesn't. Belongs to `repo-tasks`' stamp template, not here.]
