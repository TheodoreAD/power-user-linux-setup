---
status: idea
updated: 2026-08-30
repo: git@github.com:TheodoreAD/power-user-linux-setup.git
---

# A probe for "is this dependency absent" cannot run from an activated venv

## Context

From a `repo-tasks` session, 2026-08-29/30. The question was whether an ini key belonging to a
pytest plugin is harmless in a project that does not install that plugin — a question whose entire
content is "what happens when the package is _absent_".

The probe:

```shell
uv run --no-project --with pytest==9.1.1 pytest
```

run from a shell with the repo's own venv active. It reported
`plugins: anyio-4.14.2, socket-0.8.1, cov-7.1.0` and passed cleanly — the answer the session was
hoping for, and wrong. `--with` builds an ephemeral overlay **on top of** the active environment
rather than replacing it; `sys.prefix` inside that run was the repo's own `.venv`. So the probe
measured a machine that had the package all along.

The isolating form:

```shell
env -u VIRTUAL_ENV -u PYTHONPATH uv run --no-project --python 3.11 --with pytest==9.1.1 pytest
```

which produced the real answer immediately — a hard error and exit 4, the opposite conclusion.

Nothing here is a uv defect: `--with` does what it documents. The failure is reading a passing probe
as isolation.

## Why it is worth a rule

Two properties make it silent rather than merely wrong:

- **The contaminated run passes.** There is no error to notice, and the plugin list scrolls past in
  pytest's header where it reads as ordinary output.
- **A plugin can register itself.** AnyIO ships a `pytest11` entry point, so nothing in the project
  asks for it and nothing in the config names it — mere presence on the path is enough. A probe for
  absence is exactly the case where an auto-registering package is invisible.

The session caught it, but only after the wrong answer had been written into a plan and the user
questioned the stated cause.

## Recommended direction

Extend `~/AGENTS.md`'s **Verification** cluster rather than adding a heading — this is another
instance of the shape that cluster already carries (clean stdout vs exit code, a sample vs its
siblings, a green run vs the code actually imported): the convenient surface signal is not the
signal. Suggested addition, to sit alongside those:

> **Probing whether a dependency is absent.** `uv run --with …` layers an ephemeral overlay over the
> active environment, so from a directory with a venv active the probe measures a machine that has
> the package. Strip the environment —
> `env -u VIRTUAL_ENV -u PYTHONPATH uv run --no-project --python <ver> --with <pkg>` — and check
> `sys.prefix` if in doubt. A package that registers a plugin through an entry point (pytest's
> `pytest11`, for one) needs nothing in the project to name it, so absence probes are precisely
> where contamination hides.

One paragraph, no new rule count, per this repo's own admission criteria in
`contributing/global-agents-md.md`. Check the current rule/line totals before adding, as that
document requires.
