"""Unit tests for tasks/python.py's uv-tool installer, specifically the `editable` branch that
installs this repo itself as the `spowse` shim.

Why this is worth pinning: a non-editable install of this project succeeds, exits 0, and leaves a
tool whose `Path(__file__).parent.parent` points at its own site-packages — where setup.toml and
config/ do not exist. Nothing errors; every repo-side read just comes back missing. Probed
2026-09-08 with a throwaway package of the same shape, and it is the reason `editable = true` is not
a preference. So the flag is asserted both at the command that gets built and at the setup.toml
declaration behind it.
"""

from collections.abc import Sequence
from pathlib import Path

import pytest
from invoke import Context, Result, UnexpectedExit
from typing_extensions import override  # typing.override is 3.12+; this repo's floor is 3.11

from tasks import python as python_tasks
from tasks import util


class _FakeContext(Context):
    """Records commands instead of running them, on invoke's own non-zero contract."""

    def __init__(self, fail: Sequence[str] = ()) -> None:
        super().__init__()
        self.commands: list[str] = []
        self._fail: tuple[str, ...] = tuple(fail)

    @override
    def run(self, command: str, **kwargs: object) -> Result:
        self.commands.append(command)
        exited = 1 if any(fragment in command for fragment in self._fail) else 0
        result = Result(command=command, exited=exited)
        if exited and not kwargs.get("warn"):
            raise UnexpectedExit(result)
        return result


@pytest.fixture(autouse=True)
def _live_mode(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(util, "DRY_RUN", False)
    monkeypatch.setattr(util, "command_exists", lambda _name: True)


def _run_with(monkeypatch: pytest.MonkeyPatch, packages: dict[str, util.PackageConfig]) -> list[str]:
    monkeypatch.setattr(util, "packages_by_method", lambda _method: packages)
    monkeypatch.setattr(util, "load_config", lambda: {})
    context = _FakeContext()
    python_tasks.install_tools(context)
    return context.commands


def test_an_editable_package_installs_from_an_absolute_repo_path(monkeypatch: pytest.MonkeyPatch):
    commands = _run_with(monkeypatch, {"spowse": {"package": ".", "editable": True}})
    repo_root = Path(python_tasks.__file__).parent.parent.resolve()
    assert commands == [f"uv tool install --upgrade --editable {repo_root}"]


def test_a_normal_package_is_untouched_by_the_editable_branch(monkeypatch: pytest.MonkeyPatch):
    """The flag has to be inert for the other thirteen uv-tool packages, which install by name."""
    commands = _run_with(monkeypatch, {"glances": {"package": "glances"}})
    assert commands == ["uv tool install --upgrade glances"]
    assert "--editable" not in commands[0]


def test_editable_composes_with_python_and_extras(monkeypatch: pytest.MonkeyPatch):
    cfg: util.PackageConfig = {"package": ".", "editable": True, "python": "3.14", "extras": ["rich"]}
    commands = _run_with(monkeypatch, {"spowse": cfg})
    assert "--python 3.14" in commands[0]
    assert "--with rich" in commands[0]
    assert "--editable" in commands[0]


def test_setup_toml_still_declares_the_shim_as_editable():
    """The regression this file exists for. Dropping `editable` from the section leaves an install
    that succeeds and a tool that silently reads nothing, so no runtime check would catch it."""
    package = util.load_config()["packages"]["spowse"]
    assert package.get("method") == "uv-tool"
    assert package.get("editable") is True
    assert package.get("package") == "."
