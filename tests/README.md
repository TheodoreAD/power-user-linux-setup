# Tests

Most of `tasks/*.py` isn't realistically unit-testable: it shells out to `apt`/`systemctl`/`dpkg`/
`gsettings` and mutates a real system, which is why this repo has otherwise relied on
`PULSE_DRY_RUN=1` (see `docs/index.md`) plus manual runs instead of a test suite.

Pure logic with no direct system calls, growing as more of it gets pulled out of the
system-touching tasks around it: `tasks/phases.py` (pure orchestration — calls whatever task
functions it's given and branches on their captured output), `tasks/proxy.py`'s parsing helpers
(`_parse_proxy_authenticate`, `_parse_env_proxy`, `_parse_etc_environment`, `_split_host_port` —
string/env parsing with no subprocess/filesystem calls of their own, unlike the rest of that
module), `tasks/certs.py`'s `_split_pem_certs` (regex-splits a PEM blob into individual cert
blocks, no subprocess/filesystem calls — everything else in that module shells out to
openssl/keytool or touches the trust store), `tasks/wsl.py`'s `_dns_query_packet` (builds a raw DNS
query packet in memory — no socket I/O, unlike `_query_dns_server`/`_public_dns_reachable`, which
actually send it), `tasks/util.py`'s `ok_label`/`ensure_block_text`/`packages_by_method` (string
formatting and dict filtering — the sudo/file-write side of `ensure_block`/`sudo_write` isn't
covered), and `tasks/allowlist.py`'s `Classification`/`Source` enums plus `_resolve_flat_verdict`/
`_classify_flag_result` (pure data transforms — the LLM call and subprocess/strace probing around
them aren't).

Set up once after cloning:

```shell
inv python.dev-venv
```

This runs `uv sync` (creates `.venv/` from `pyproject.toml`'s `dev` dependency group —
`pytest`/`invoke` — and editable-installs `tasks` as a real package so `import tasks` just works,
no `sys.path` tricks needed) and `direnv allow`, so the repo's `.envrc` auto-exports
`VIRTUAL_ENV`/`PATH` whenever direnv's shell hook fires (`[packages.direnv]` in `setup.toml`). Then
just `cd` into the repo and run tests the plain way, same as any other Python project — no
`uv run` prefix, no manual activation:

```shell
pytest tests/
```

This also works unmodified from a Claude Code (or other agent) session in this repo, once
`.envrc`/`direnv allow` have been done at least once: Claude Code captures a shell snapshot once
per session and replays it for every Bash-tool command instead of re-sourcing dotfiles each time,
so a _new_ session's snapshot already has `.venv/bin` on `PATH` — no explicit activation needed.
A session whose snapshot predates `.envrc`/`direnv allow` existing won't see it retroactively
(the snapshot doesn't refresh mid-session); start a new session if that happens.
