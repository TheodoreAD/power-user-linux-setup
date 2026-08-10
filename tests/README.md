# Tests

Most of `tasks/*.py` isn't realistically unit-testable: it shells out to `apt`/`systemctl`/`dpkg`/
`gsettings` and mutates a real system, which is why this repo has otherwise relied on
`PULSE_DRY_RUN=1` (see `docs/index.md`) plus manual runs instead of a test suite.

Three exceptions, all pure logic with no direct system calls: `tasks/phases.py` (pure
orchestration — calls whatever task functions it's given and branches on their captured output),
`tasks/proxy.py`'s parsing helpers (`_parse_proxy_authenticate`, `_parse_env_proxy`,
`_parse_etc_environment`, `_split_host_port` — string/env parsing with no subprocess/filesystem
calls of their own, unlike the rest of that module), and `tasks/certs.py`'s `_split_pem_certs`
(regex-splits a PEM blob into individual cert blocks, no subprocess/filesystem calls — everything
else in that module shells out to openssl/keytool or touches the trust store).

Run with:

```shell
uv run --with pytest --with invoke python -m pytest tests/
```

`--with invoke` is needed because importing `tasks.phases` imports the whole `tasks` package
(`tasks/__init__.py`), and every task module imports `invoke` for the `@task` decorator. `python -m
pytest` (not the bare `pytest` command) is what puts the repo root on `sys.path` so `import tasks`
resolves — run it from the repo root.
