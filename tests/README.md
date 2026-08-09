# Tests

Most of `tasks/*.py` isn't realistically unit-testable: it shells out to `apt`/`systemctl`/`dpkg`/
`gsettings` and mutates a real system, which is why this repo has otherwise relied on
`PULSE_DRY_RUN=1` (see `docs/index.md`) plus manual runs instead of a test suite.

`tasks/phases.py` is the exception — it's pure orchestration with no direct system calls of its
own, just calling whatever task functions it's given and branching on their captured output — so
it's the one thing covered here.

Run with:

```shell
uv run --with pytest --with invoke python -m pytest tests/
```

`--with invoke` is needed because importing `tasks.phases` imports the whole `tasks` package
(`tasks/__init__.py`), and every task module imports `invoke` for the `@task` decorator. `python -m
pytest` (not the bare `pytest` command) is what puts the repo root on `sys.path` so `import tasks`
resolves — run it from the repo root.
