"""Every script this repo runs on an interpreter it does not choose has to parse there.

Three of them: `tasks/netdoctor.py`, which runs on a fresh WSL distro or container *before* uv
exists, and the two helpers in `tests/containers/`, which run as a bare `python3` inside whatever
image a test spins up. Ubuntu 24.04 ships 3.12 and that is the floor for all three, against this
repo's own 3.14.

The test exists because that gap is not theoretical and is not caught by anything else. Raising
`requires-python` to `>=3.14` on 2026-09-18 moved ruff's target with it — ruff reads the floor from
that field — and **the formatter then rewrote four `except (A, B):` clauses across these files to
PEP 758's unparenthesized form, which is a SyntaxError on 3.12**. No lint rule fired, nothing in
the gate's output named the files, and the reformat arrives as part of `quality.fix` rather than as
a change anyone chose. `netdoctor.py` had a parse guard and failed loudly; `fakecorp.py` had none
and would have shipped broken to the next container run. Hence one guard covering all three.

Syntax only. A newer *API* under an old syntax is invisible to the parser, and CI's
`netdoctor-python-floor` job — a real 3.12 running the module — is the check that proves that half.
"""

import ast
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).parent.parent.parent

# The distro floor, not this repo's: Ubuntu 24.04 ships 3.12 and is what these run on.
_FLOOR = (3, 12)

_FOREIGN_SCRIPTS = (
    "tasks/netdoctor.py",
    "tests/containers/fakecorp.py",
    "tests/containers/drive.py",
)


@pytest.mark.parametrize("relative", _FOREIGN_SCRIPTS)
def test_script_parses_at_the_distro_floor(relative: str):
    """Fix a failure by restoring the syntax the formatter replaced and marking that line
    `# fmt: skip` — never by editing `_FLOOR`, and never by adding the file to a ruff exclude:
    `ruff.toml` is pulled byte-identical from repo-tasks and serves every consumer."""
    source = (_REPO_ROOT / relative).read_text()
    ast.parse(source, feature_version=_FLOOR)


def test_the_guarded_set_still_matches_what_the_repo_runs_this_way():
    """A structural check on the list above, which is the part that goes stale silently: a fourth
    script added to `tests/containers/` inherits the same exposure and none of the protection."""
    helpers = {f"tests/containers/{path.name}" for path in (_REPO_ROOT / "tests" / "containers").glob("*.py")}
    assert helpers <= set(_FOREIGN_SCRIPTS), sorted(helpers - set(_FOREIGN_SCRIPTS))


def test_the_zero_install_guardrail_job_pins_its_interpreter():
    """The cross-file invariant that `tasks/` is *not* in the set above — and it only holds because
    two files agree.

    `bootstrap.sh` installs invoke with `--python "${UV_PYTHON_DEFAULT}"`, so on a real machine
    `tasks/` is loaded at this repo's own floor. CI's `runtime-guardrail` job re-creates that path
    with bare `invoke` to prove the repo_tasks-absent case still works, and for as long as it
    installed unpinned it was quietly doing so on the runner's preinstalled 3.12. That cost nothing
    while the declared floor was 3.11 and killed the job on the commit that raised it to 3.14 — a
    SyntaxError on a PEP 758 `except` clause, from a file nothing else in the gate reads below the
    floor. Pin it there and `tasks/` never has to parse below its own declaration.
    """
    workflow = (_REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    install = [line for line in workflow.splitlines() if "uv tool install" in line and "invoke" in line]
    assert install, "runtime-guardrail no longer installs invoke — check this test still describes the job"
    assert all("--python" in line for line in install), install
