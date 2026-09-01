"""Unit tests for tasks/zsh.py's configure() — which packages get a shell block on this machine.

The bug being guarded is plans/2026-08-31-wsl-and-container-first-run-experience.md's deferred item:
the writer read every `[packages.*]` section and checked only `enabled`, so a `gui`-tagged package's
export was written into headless WSL distros and containers whatever PULSE_EXCLUDE_TAGS said. That
is how a GTK askpass ended up exported on machines with no display.

Real files under tmp_path with HOME redirected there, not a mocked writer: what these assert is the
content of the dotfile afterwards, which is the whole question. See tests/README.md.
"""

from collections.abc import Collection
from pathlib import Path

import pytest
from invoke import MockContext

from tasks import util, zsh

_GUI: util.PackageConfig = {"tags": ["gui"], "zshenv": "export ASKPASS=/usr/bin/zenity-thing"}
_HEADLESS: util.PackageConfig = {"zshenv": "export EDITOR=vim"}
_DISABLED: util.PackageConfig = {"zshenv": "export EDITOR=vim", "enabled": False}


@pytest.fixture(autouse=True)
def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(util, "DRY_RUN", False)
    monkeypatch.setattr(util, "load_overrides", dict)


def _config(monkeypatch, packages: dict[str, util.PackageConfig], *, exclude: Collection[str] = ()) -> None:
    monkeypatch.setattr(util, "load_config", lambda: {"packages": packages})
    monkeypatch.setattr(util, "_excluded_tags", lambda: set(exclude))


def _zshenv(tmp_path) -> str:
    path = tmp_path / ".zshenv"
    return path.read_text() if path.exists() else ""


def test_configure_writes_a_gui_block_when_no_tag_is_excluded(tmp_path, monkeypatch):
    _config(monkeypatch, {"askpass": _GUI, "editor": _HEADLESS})

    zsh.configure(MockContext())

    assert "ASKPASS" in _zshenv(tmp_path)
    assert "EDITOR" in _zshenv(tmp_path)


def test_configure_skips_a_gui_block_on_a_machine_that_excluded_gui(tmp_path, monkeypatch):
    """The regression: this export used to be written into every headless distro regardless."""
    _config(monkeypatch, {"askpass": _GUI, "editor": _HEADLESS}, exclude=["gui"])

    zsh.configure(MockContext())

    assert "ASKPASS" not in _zshenv(tmp_path)
    assert "EDITOR" in _zshenv(tmp_path)


def test_configure_removes_a_block_whose_package_stopped_applying(tmp_path, monkeypatch):
    """A machine that ran once without the exclusion has the block already; excluding the tag
    afterwards has to take it back out, because nothing else ever would."""
    _config(monkeypatch, {"askpass": _GUI, "editor": _HEADLESS})
    zsh.configure(MockContext())
    assert "ASKPASS" in _zshenv(tmp_path)

    _config(monkeypatch, {"askpass": _GUI, "editor": _HEADLESS}, exclude=["gui"])
    zsh.configure(MockContext())

    assert "ASKPASS" not in _zshenv(tmp_path)
    assert "EDITOR" in _zshenv(tmp_path)


def test_configure_leaves_hand_written_content_alone_when_it_removes_a_block(tmp_path, monkeypatch):
    (tmp_path / ".zshenv").write_text("# mine, not PULSE's\nexport MINE=1\n")
    _config(monkeypatch, {"askpass": _GUI})
    zsh.configure(MockContext())

    _config(monkeypatch, {"askpass": _GUI}, exclude=["gui"])
    zsh.configure(MockContext())

    assert _zshenv(tmp_path) == "# mine, not PULSE's\nexport MINE=1\n"


def test_configure_still_honours_enabled_false(tmp_path, monkeypatch):
    _config(monkeypatch, {"editor": _DISABLED})

    zsh.configure(MockContext())

    assert "EDITOR" not in _zshenv(tmp_path)


def test_configure_dry_run_reports_a_stale_block_as_work_to_do(tmp_path, monkeypatch, capsys):
    """phases.probe() greps its output for "MISSING" to decide whether a phase can be skipped, so a
    block that still needs removing has to produce that token or the phase offers to skip itself."""
    _config(monkeypatch, {"askpass": _GUI})
    zsh.configure(MockContext())

    _config(monkeypatch, {"askpass": _GUI}, exclude=["gui"])
    monkeypatch.setattr(util, "DRY_RUN", True)
    zsh.configure(MockContext())

    assert "MISSING" in capsys.readouterr().out
    assert "ASKPASS" in _zshenv(tmp_path), "a dry run must not write"
