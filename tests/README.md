# Tests

Most of `tasks/*.py` isn't realistically unit-testable: it shells out to `apt`/`systemctl`/`dpkg`/
`gsettings` and mutates a real system, which is why this repo has otherwise relied on
`PULSE_DRY_RUN=1` (see `docs/index.md`) plus manual runs instead of a test suite.

Pure logic with no direct system calls, growing as more of it gets pulled out of the system-touching
tasks around it: `tasks/phases.py` (pure orchestration — calls whatever task functions it's given
and branches on their captured output), `tasks/proxy.py`'s parsing helpers
(`_parse_proxy_authenticate`, `_parse_env_proxy`, `_parse_etc_environment`, `_split_host_port` —
string/env parsing with no subprocess/filesystem calls of their own, unlike the rest of that
module), `tasks/certs.py`'s `_split_pem_certs` (regex-splits a PEM blob into individual cert blocks,
no subprocess/filesystem calls — everything else in that module shells out to openssl/keytool or
touches the trust store), `tasks/wsl.py`'s `_dns_query_packet` (builds a raw DNS query packet in
memory — no socket I/O, unlike `_query_dns_server`/`_public_dns_reachable`, which actually send it),
`tasks/util.py`'s `ok_label`/`ensure_block_text`/`packages_by_method` (string formatting and dict
filtering — the file-write side of `ensure_block`/`sudo_write` isn't covered) plus its **sudo state
machine** (`sudo_state`/`ensure_sudo`/`apt_command`, with every `sudo` probe and the interactive
runner stubbed: NOPASSWD vs a warm cache, askpass vs terminal, the root shortcut, the refusal when
nothing can ask — the terminal behaviour itself is exercised in a container instead, see
`contributing/interactive-input.md`), `tasks/netdoctor.py`'s parsers and its whole `evaluate()`
judgement layer (every measurement is an argument, so a corporate network — PyPI blocked while
GitHub answers, a 407, an untrusted certificate issuer, a Windows-side proxy — is a literal in the
test rather than infrastructure nobody has; the socket-touching half is exercised against simulated
networks in containers), plus three tests that hold that module's constraints in place: standard
library only, no import from `tasks/`, Python 3.10 syntax, `tasks/allowlist.py`'s
`Classification`/`Source` enums plus `_resolve_flat_verdict`/ `_classify_flag_result` (pure data
transforms — the LLM call and subprocess/strace probing around them aren't), `tasks/git.py`'s
`resolve_project_dir` (relative-vs-absolute `directory` resolution — no subprocess/filesystem calls,
unlike `configure()`/`settings()` around it, which shell out to git), `tasks/identity.py`'s
`_render`/`_toml_string` (TOML string-building for the generated identity.toml — no
filesystem/prompting, unlike `init()` around them), and `tasks/ai.py`'s skill install/confirm logic:
`_parse_frontmatter_description`/`_local_skill_plan`/`_remote_skill_label`/ `_remote_skill_prompt`
(pure), plus `_install_local_skill`/`_install_remote_skill`/ `_install_declared_skills`/the `skills`
task itself exercised against `tmp_path` with `ui.ask`/`c.run`/`util.load_config` monkeypatched out
— same "stub the collaborators, assert on calls" shape as `tasks/phases.py`'s tests, since none of
it needs a real `~/.agents/skills` or a real `skills` CLI invocation to verify the
-y/prompt/up-to-date-skip behavior.

Set up once after cloning:

```shell
inv dev-env.setup
```

This runs `uv sync` (creates `.venv/` from `pyproject.toml`'s `dev` dependency group —
`pytest`/`invoke` — and editable-installs `tasks` as a real package so `import tasks` just works, no
`sys.path` tricks needed) and `direnv allow`, so the repo's `.envrc` auto-exports
`VIRTUAL_ENV`/`PATH` whenever direnv's shell hook fires (`[packages.direnv]` in `setup.toml`), plus
wires Claude Code's Bash tool to pick up the same environment (`agents.wire-claude-hook` — see
docs/claude-code.md). Then just `cd` into the repo and run tests the plain way, same as any other
Python project — no `uv run` prefix, no manual activation:

```shell
pytest            # or: inv test.unit — what quality.check/precommit run
```

This also works unmodified from a Claude Code (or other agent) session in this repo, once
`.envrc`/`direnv allow` have been done at least once: Claude Code captures a shell snapshot once per
session and replays it for every Bash-tool command instead of re-sourcing dotfiles each time, so a
_new_ session's snapshot already has `.venv/bin` on `PATH` — no explicit activation needed. A
session whose snapshot predates `.envrc`/`direnv allow` existing won't see it retroactively (the
snapshot doesn't refresh mid-session); start a new session if that happens.

## Layout: `tests/unit/` only, no integration tier — on purpose

The suite lives in `tests/unit/`, matching the two-tier layout `repo-tasks` ships to every consumer
(`pytest.ini`'s `testpaths = tests/unit`, the `inv test.{unit,integration,smoke,regression,all}`
namespace — rationale in `repo-tasks/contributing/test-tiers.md`). This repo has **no**
`tests/integration/` and that is deliberate, not an omission: every test here is hermetic (the
collaborators that would shell out are monkeypatched, nothing needs a network, a Docker daemon, or
anything outside `tmp_path`) and the whole suite runs in well under a second — there is nothing to
put in a slower tier. `inv test.integration`/`smoke`/`regression` no-op cleanly on the missing
directory. Add the directory only when a test genuinely needs a real external service; a test that
merely stubs its collaborators belongs in `tests/unit/`.

The directory matters even with the tier empty: the shared `pytest.ini` names `tests/unit`, and when
`testpaths` misses, pytest only _warns_
(`No files were found in testpaths ... Searching recursively from the current directory instead`)
and falls back to searching the whole working tree — broader than `tests/`, and not
`.gitignore`-aware — so any non-test directory at the repo root would join the default run. "The
suite keeps passing" is the benign case: in `scaffoldapy` the same config pull, made before the
directory existed, broke collection outright (exit 2) because that repo has a second `tests/` tree
under `template/`, and the fallback reached `template/tests/conftest.py`, which shadowed the real
one (`ImportError: cannot import name 'BASE_ANSWERS' from 'conftest'`). Adopt the structure first,
then pull the config (`~/AGENTS.md`, "Regenerating a file from a canonical source").

If this repo ever does grow a `tests/integration/` with its own `conftest.py`: an import from
`conftest` then resolves to a _different file per tier_ — the root one from the unit tier, the
tier-local one from the integration tier, where it raises `ImportError`, silently and
direction-dependently. Shared constants that feed `@pytest.mark.parametrize` cannot be fixtures, so
they need a distinctly-named module (`tests/support.py`, as `scaffoldapy` did), never `conftest.py`.
