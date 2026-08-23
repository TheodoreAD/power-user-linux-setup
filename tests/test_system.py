"""Unit tests for tasks/system.py's `configs` task — the deliberate redeploy path for setup.toml
`config_files` mappings, whose whole reason to exist is that it *does* overwrite where the
install-time path (apt._apply_config_files) deliberately doesn't. See tests/README.md.
"""

from pathlib import Path

import pytest
from invoke import Exit

from tasks import system, util


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A stand-in repo root with config/app.conf, plus a home-side destination path."""
    monkeypatch.setattr(system, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(util, "DRY_RUN", False)
    src = tmp_path / "config" / "app.conf"
    src.parent.mkdir()
    src.write_text("new content\n")
    return tmp_path


def _packages(dst: Path, *, name: str = "app") -> dict:
    return {name: {"config_files": [{"src": "config/app.conf", "dst": str(dst)}]}}


def _stub_packages(monkeypatch, packages: dict) -> None:
    monkeypatch.setattr(util, "enabled_packages", lambda: packages)


# system.configs is @task-wrapped and invoke's Task.__call__ insists its first arg be a real
# Context — .body is the plain underlying function, same pattern as tests/test_ai.py.
_run = system.configs.body  # pyright: ignore[reportAny, reportFunctionMemberAccess] — invoke's untyped Task.body


def test_creates_a_destination_that_doesnt_exist_yet(repo, monkeypatch, capsys):
    dst = repo / "home" / "app.conf"
    _stub_packages(monkeypatch, _packages(dst))
    # No prompt for a create — nothing is being destroyed, so confirm() must not even be reached.
    monkeypatch.setattr(util, "confirm", lambda *a, **k: pytest.fail("create must not prompt"))

    _run(None)

    assert dst.read_text() == "new content\n"
    assert "created" in capsys.readouterr().out


def test_leaves_an_already_matching_destination_alone(repo, monkeypatch, capsys):
    dst = repo / "app.conf"
    dst.write_text("new content\n")
    _stub_packages(monkeypatch, _packages(dst))
    monkeypatch.setattr(util, "confirm", lambda *a, **k: pytest.fail("no-op must not prompt"))

    _run(None)

    assert "already matches" in capsys.readouterr().out


def test_overwrites_a_drifted_destination_when_confirmed(repo, monkeypatch, capsys):
    dst = repo / "app.conf"
    dst.write_text("hand-edited\n")
    _stub_packages(monkeypatch, _packages(dst))
    monkeypatch.setattr(util, "confirm", lambda *a, **k: True)

    _run(None)

    assert dst.read_text() == "new content\n"
    out = capsys.readouterr().out
    assert "-hand-edited" in out and "+new content" in out


def test_keeps_a_drifted_destination_when_declined(repo, monkeypatch):
    dst = repo / "app.conf"
    dst.write_text("hand-edited\n")
    _stub_packages(monkeypatch, _packages(dst))
    monkeypatch.setattr(util, "confirm", lambda *a, **k: False)

    _run(None)

    assert dst.read_text() == "hand-edited\n"


def test_yes_overwrites_without_prompting(repo, monkeypatch):
    dst = repo / "app.conf"
    dst.write_text("hand-edited\n")
    _stub_packages(monkeypatch, _packages(dst))
    monkeypatch.setattr(util, "confirm", lambda *a, **k: pytest.fail("--yes must not prompt"))

    _run(None, yes=True)

    assert dst.read_text() == "new content\n"


def test_dry_run_reports_the_overwrite_without_writing(repo, monkeypatch, capsys):
    dst = repo / "app.conf"
    dst.write_text("hand-edited\n")
    _stub_packages(monkeypatch, _packages(dst))
    monkeypatch.setattr(util, "DRY_RUN", True)
    monkeypatch.setattr(util, "confirm", lambda *a, **k: pytest.fail("dry run must not prompt"))

    _run(None)

    assert dst.read_text() == "hand-edited\n"
    assert "would overwrite" in capsys.readouterr().out


def test_name_scopes_to_one_package(repo, monkeypatch):
    wanted = repo / "wanted.conf"
    other = repo / "other.conf"
    _stub_packages(monkeypatch, _packages(wanted, name="app") | _packages(other, name="elsewhere"))

    _run(None, name="app")

    assert wanted.exists()
    assert not other.exists()


def test_name_for_a_package_that_isnt_enabled_raises(repo, monkeypatch):
    _stub_packages(monkeypatch, _packages(repo / "app.conf"))

    with pytest.raises(Exit, match="no enabled"):
        _run(None, name="nonexistent")


def test_src_resolves_against_the_repo_root_not_the_cwd(repo, monkeypatch, tmp_path):
    # The install-time path had this bug: a relative src only resolved when invoked from the repo
    # root. Run from an unrelated cwd and the copy must still find config/app.conf.
    dst = repo / "app.conf"
    _stub_packages(monkeypatch, _packages(dst))
    elsewhere = tmp_path.parent / "elsewhere"
    elsewhere.mkdir(exist_ok=True)
    monkeypatch.chdir(elsewhere)

    _run(None, yes=True)

    assert dst.read_text() == "new content\n"
