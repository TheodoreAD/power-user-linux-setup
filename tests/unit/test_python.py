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


def _seeding_context(monkeypatch: pytest.MonkeyPatch, packages: dict[str, util.PackageConfig]):
    """A context whose command log also records `apply_config_files` calls, so order is assertable."""
    monkeypatch.setattr(util, "packages_by_method", lambda _method: packages)
    monkeypatch.setattr(util, "load_config", lambda: {})
    context = _FakeContext()
    monkeypatch.setattr(
        python_tasks.deploy,
        "apply_config_files",
        lambda name, _cfg: context.commands.append(f"seed:{name}"),
    )
    python_tasks.install_tools(context)
    return context.commands


def test_a_uv_tool_packages_config_files_are_seeded_after_it_installs(monkeypatch: pytest.MonkeyPatch):
    """The gap that broke every dev container build from 2026-09-05: this was the one installer not
    calling `deploy.apply_config_files`, while `inv verify.all` — the last step of the same phase —
    requires every declared destination to exist. It stayed invisible because `act` was the only
    uv-tool package declaring one, and it is tagged `workstation`, so containers exclude it.

    Order is part of the assertion: seeding before the tool exists would write config for something
    that may then fail to install.
    """
    cfg: util.PackageConfig = {
        "package": "keyring",
        "config_files": [{"src": "config/uv.toml", "dst": "~/.config/uv/uv.toml"}],
    }
    assert _seeding_context(monkeypatch, {"python-keyring": cfg}) == [
        "uv tool install --upgrade keyring",
        "seed:python-keyring",
    ]


def test_seeding_is_unconditional_so_a_future_declaration_needs_no_edit_here(
    monkeypatch: pytest.MonkeyPatch,
):
    """Called for every package rather than only those declaring `config_files` — the empty case is
    a no-op inside `apply_config_files`. That is what stops the next uv-tool package to declare one
    from reintroducing this bug, which is exactly how it arrived."""
    assert _seeding_context(monkeypatch, {"glances": {"package": "glances"}}) == [
        "uv tool install --upgrade glances",
        "seed:glances",
    ]


def test_every_uv_tool_package_declaring_config_files_is_reachable_by_that_call():
    """A structural check on the real setup.toml rather than a fixture: if this list ever empties,
    the tests above are still green while guarding nothing, because no shipped package would
    exercise the path any more."""
    uv_tools = util.load_config()["packages"]
    declaring = [name for name, cfg in uv_tools.items() if cfg.get("method") == "uv-tool" and cfg.get("config_files")]
    assert "python-keyring" in declaring
