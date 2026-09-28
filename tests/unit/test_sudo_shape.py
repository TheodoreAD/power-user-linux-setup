"""No command in tasks/ may put a sudo inside a compound or piped shell command.

Without a terminal, sudo keys its credential cache on the parent PID. `util.ensure_sudo` stamps it
from a child of the `inv` process, so only a sudo that bash execs in place — a lone command — still
has `inv` as its parent and finds the stamp. `&&`, `||`, `;` or `|` makes bash fork, and that sudo's
`-n` fails with "a password is required". Measured 2026-09-28; the numbers are in
`util.sudo_write`'s docstring. A terminal keys the cache on the tty instead, so an interactive run
never shows it, and this scan is what does.

Read from the source rather than by running tasks: the shape is visible in an f-string, and running
every writer would need a machine to write to.
"""

import ast
import re
from collections.abc import Iterator
from pathlib import Path

import pytest

_TASKS = Path(__file__).resolve().parents[2] / "tasks"
_OPERATORS = ("&&", "||", ";", "|")
# A quoted argument is data, not shell syntax: screenshot.py's `sed 's|a|b|g'` has no pipeline.
_QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"")


def _is_sudo(node: ast.expr) -> bool:
    return (isinstance(node, ast.Name) and node.id == "SUDO") or (
        isinstance(node, ast.Attribute) and node.attr == "SUDO"
    )


def _compound_sudo_lines(source: str) -> Iterator[int]:
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.JoinedStr):
            continue
        if not any(isinstance(part, ast.FormattedValue) and _is_sudo(part.value) for part in node.values):
            continue
        literal = "".join(
            part.value for part in node.values if isinstance(part, ast.Constant) and isinstance(part.value, str)
        )
        if any(op in _QUOTED.sub("", literal) for op in _OPERATORS):
            yield node.lineno


_MODULES = sorted(_TASKS.glob("*.py"))


@pytest.mark.parametrize("module", _MODULES, ids=[path.name for path in _MODULES])
def test_no_sudo_command_is_compound(module: Path):
    lines = list(_compound_sudo_lines(module.read_text()))
    assert lines == [], (
        f"{module.name}: sudo inside a compound command at line(s) {lines} — split it into lone "
        "c.run calls, or use util.sudo_write (mkdir=True for the parent directory)"
    )


@pytest.mark.parametrize(
    "command",
    [
        'f"{util.SUDO} mkdir -p {d} && {util.SUDO} install -m 0644 {t} {p} && rm {t}"',
        'f"curl -fsSL {url} | {util.SUDO} gpg --dearmor -o {gpg}"',
        'f"{SUDO} install -m 0644 {tmp} {path} && rm {tmp}"',
    ],
    ids=["chained-install", "piped-gpg", "trailing-rm"],
)
def test_the_scan_catches_each_shape_this_repo_has_shipped(command: str):
    """Each of these was in tasks/ until 2026-09-28. A scan that passes the tree but misses them
    would be a scan of nothing."""
    assert list(_compound_sudo_lines(command)) == [1]


def test_the_scan_ignores_a_pipe_inside_a_quoted_argument():
    command = """f"{util.SUDO} sed -i 's|Exec=a|Exec=b|g' {path}\""""
    assert list(_compound_sudo_lines(command)) == []
