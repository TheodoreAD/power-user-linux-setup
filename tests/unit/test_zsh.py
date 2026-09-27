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
from typing import cast
from unittest.mock import Mock

import pytest
from invoke import MockContext, Result

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


def _ctx(session_env: str = "", *, exited: int = 0, unset: str | None = None) -> MockContext:
    """A context answering `systemctl --user show-environment` with `session_env` — the user
    manager's environment, one `NAME=value` per line — and, when given, accepting exactly the
    `unset-environment` call for `unset`. Any other command raises, so an unexpected unset fails."""
    run = {"systemctl --user show-environment": Result(stdout=session_env, exited=exited)}
    if unset:
        run[f"systemctl --user unset-environment {unset}"] = Result()
    return MockContext(run=run)


def _zshenv(tmp_path) -> str:
    path = tmp_path / ".zshenv"
    return path.read_text() if path.exists() else ""


def test_configure_writes_a_gui_block_when_no_tag_is_excluded(tmp_path, monkeypatch):
    _config(monkeypatch, {"askpass": _GUI, "editor": _HEADLESS})

    zsh.configure(_ctx())

    assert "ASKPASS" in _zshenv(tmp_path)
    assert "EDITOR" in _zshenv(tmp_path)


def test_configure_skips_a_gui_block_on_a_machine_that_excluded_gui(tmp_path, monkeypatch):
    """The regression: this export used to be written into every headless distro regardless."""
    _config(monkeypatch, {"askpass": _GUI, "editor": _HEADLESS}, exclude=["gui"])

    zsh.configure(_ctx())

    assert "ASKPASS" not in _zshenv(tmp_path)
    assert "EDITOR" in _zshenv(tmp_path)


def test_configure_removes_a_block_whose_package_stopped_applying(tmp_path, monkeypatch):
    """A machine that ran once without the exclusion has the block already; excluding the tag
    afterwards has to take it back out, because nothing else ever would."""
    _config(monkeypatch, {"askpass": _GUI, "editor": _HEADLESS})
    zsh.configure(_ctx())
    assert "ASKPASS" in _zshenv(tmp_path)

    _config(monkeypatch, {"askpass": _GUI, "editor": _HEADLESS}, exclude=["gui"])
    zsh.configure(_ctx())

    assert "ASKPASS" not in _zshenv(tmp_path)
    assert "EDITOR" in _zshenv(tmp_path)


def test_configure_leaves_hand_written_content_alone_when_it_removes_a_block(tmp_path, monkeypatch):
    (tmp_path / ".zshenv").write_text("# mine, not PULSE's\nexport MINE=1\n")
    _config(monkeypatch, {"askpass": _GUI})
    zsh.configure(_ctx())

    _config(monkeypatch, {"askpass": _GUI}, exclude=["gui"])
    zsh.configure(_ctx())

    assert _zshenv(tmp_path) == "# mine, not PULSE's\nexport MINE=1\n"


def test_configure_still_honours_enabled_false(tmp_path, monkeypatch):
    _config(monkeypatch, {"editor": _DISABLED})

    zsh.configure(_ctx())

    assert "EDITOR" not in _zshenv(tmp_path)


def test_configure_dry_run_reports_a_stale_block_as_work_to_do(tmp_path, monkeypatch, capsys):
    """phases.probe() greps its output for "MISSING" to decide whether a phase can be skipped, so a
    block that still needs removing has to produce that token or the phase offers to skip itself."""
    _config(monkeypatch, {"askpass": _GUI})
    zsh.configure(_ctx())

    _config(monkeypatch, {"askpass": _GUI}, exclude=["gui"])
    monkeypatch.setattr(util, "DRY_RUN", True)
    zsh.configure(_ctx())

    assert "MISSING" in capsys.readouterr().out
    assert "ASKPASS" in _zshenv(tmp_path), "a dry run must not write"


def test_configure_removes_a_block_whose_field_was_dropped_from_setup_toml(tmp_path, monkeypatch):
    """The other way a block stops being wanted, and the one nothing used to take back: the package
    still applies here, it just no longer declares that dotfile. `[packages.uv-env]` dropped its
    `export UV_PYTHON` on 2026-09-18 and kept its zshrc completions — before this, the export
    stayed in ~/.zshenv on every machine that had already run, which would have left the swap it
    was part of inert.
    """
    both: util.PackageConfig = {"zshenv": "export UV_PYTHON=3.14", "zshrc": "eval completions"}
    _config(monkeypatch, {"uv-env": both})
    zsh.configure(_ctx())
    assert "UV_PYTHON" in _zshenv(tmp_path)

    _config(monkeypatch, {"uv-env": {"zshrc": "eval completions"}})
    zsh.configure(_ctx())

    assert "UV_PYTHON" not in _zshenv(tmp_path)
    assert "eval completions" in (tmp_path / ".zshrc").read_text(), "the surviving field stays"


_UV_ENV: util.PackageConfig = {"zshenv": "export UV_PYTHON=3.14", "zshrc": "eval completions"}
_UV_ENV_AFTER: util.PackageConfig = {"zshrc": "eval completions"}


def test_configure_unsets_a_removed_export_the_user_manager_still_carries(tmp_path, monkeypatch, capsys):
    """The UV_PYTHON case: the dotfile was fixed, but the systemd user manager kept the variable and
    handed it to the next GNOME login too — a re-login alone did not clear it. The deploy is the one
    moment the removal is known, so it unsets it there."""
    _config(monkeypatch, {"uv-env": _UV_ENV})
    zsh.configure(_ctx())
    capsys.readouterr()

    _config(monkeypatch, {"uv-env": _UV_ENV_AFTER})
    ctx = _ctx("HOME=/home/x\nUV_PYTHON=3.14\n", unset="UV_PYTHON")
    zsh.configure(ctx)

    # MockContext wraps run in a Mock at runtime; the stubs type it as the plain method.
    cast(Mock, ctx.run).assert_any_call("systemctl --user unset-environment UV_PYTHON", hide=True, warn=True)
    out = capsys.readouterr().out
    assert "UV_PYTHON is no longer exported" in out
    assert "already running keep their copy" in out


def test_configure_is_silent_when_the_session_no_longer_carries_the_export(tmp_path, monkeypatch, capsys):
    _config(monkeypatch, {"uv-env": _UV_ENV})
    zsh.configure(_ctx())

    _config(monkeypatch, {"uv-env": _UV_ENV_AFTER})
    zsh.configure(_ctx("HOME=/home/x\n"))

    assert "no longer exported" not in capsys.readouterr().out


def test_an_export_still_set_by_another_line_is_not_reported_as_removed(tmp_path, monkeypatch, capsys):
    """Removal is judged on the whole dotfile, not the block: a human's own `export UV_PYTHON` means
    the variable is still exported, whatever PULSE's block did."""
    (tmp_path / ".zshenv").write_text("export UV_PYTHON=3.13\n")
    _config(monkeypatch, {"uv-env": _UV_ENV})
    zsh.configure(_ctx())

    _config(monkeypatch, {"uv-env": _UV_ENV_AFTER})
    zsh.configure(_ctx("UV_PYTHON=3.14\n"))

    assert "no longer exported" not in capsys.readouterr().out


def test_no_systemd_user_manager_means_nothing_to_report(tmp_path, monkeypatch, capsys):
    """A container or a WSL distro without systemd has no login session for an export to outlive."""
    _config(monkeypatch, {"uv-env": _UV_ENV})
    zsh.configure(_ctx())

    _config(monkeypatch, {"uv-env": _UV_ENV_AFTER})
    zsh.configure(_ctx(exited=1))

    assert "no longer exported" not in capsys.readouterr().out


def test_path_is_marked_unique_before_anything_prepends_to_it():
    """~/.zshenv is read on every zsh invocation — the property the certs/proxy exports depend on —
    so an unguarded `PATH="x:$PATH"` grows the variable once per nested shell, without limit.
    Measured 2026-09-07 before the fix: four copies of ~/.local/bin in a login shell, five in a
    `zsh -c` started from it, and the duplicated value reaches every dock-launched application,
    because gnome-session imports this session's environment into the systemd user manager.

    Asserted against setup.toml rather than the deployed file: the declaration is the source, and
    the failure this guards is somebody rewriting the block without carrying the one line that
    makes every other PATH assignment in the file idempotent.
    """
    snippet = util.load_config()["packages"]["zsh-path"].get("zshenv", "")
    assert "typeset -U path PATH" in snippet
    assert snippet.index("typeset -U") < snippet.index("PATH="), "the flag has to be set before the value it dedupes"
