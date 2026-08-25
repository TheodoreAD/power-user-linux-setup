"""Unit tests for tasks/apt.py's _apply_config_files — the install-time seeding of `config_files`
mappings (wezterm, terminator, act). It delegates to tasks/deploy.py, so what's tested here is the
seeded-ownership contract at this call site: a missing destination is created, a customized one is
reported and left alone (it used to be skipped in silence), and nothing ever prompts on an install
run. See tests/README.md.
"""

import pytest

from tasks import apt, deploy, util


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(deploy, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(deploy, "_MANIFEST", tmp_path / "state" / "deployed.json")
    monkeypatch.setattr(util, "DRY_RUN", False)
    monkeypatch.setattr(util, "ASSUME_YES", False)
    monkeypatch.setattr(util, "confirm", lambda *a, **k: pytest.fail("an install run must never prompt"))
    (tmp_path / "config" / "app.conf").parent.mkdir()
    (tmp_path / "config" / "app.conf").write_text("seed\n")


def _cfg(tmp_path) -> dict:
    return {"config_files": [{"src": "config/app.conf", "dst": str(tmp_path / "home" / "app.conf")}]}


def test_apply_config_files_seeds_a_missing_destination(tmp_path):
    apt._apply_config_files("app", _cfg(tmp_path))

    assert (tmp_path / "home" / "app.conf").read_text() == "seed\n"
    assert deploy.load_manifest()[str(tmp_path / "home" / "app.conf")]["mechanism"] == "config-file"


def test_apply_config_files_reports_and_keeps_a_customized_destination(tmp_path, capsys):
    apt._apply_config_files("app", _cfg(tmp_path))
    dst = tmp_path / "home" / "app.conf"
    dst.write_text("customized by the user\n")

    apt._apply_config_files("app", _cfg(tmp_path))

    assert dst.read_text() == "customized by the user\n"
    assert "yours to own" in capsys.readouterr().out


def test_apply_config_files_keeps_a_pre_existing_destination_it_never_wrote(tmp_path, capsys):
    # A machine where the file already existed before PULSE ever ran: no manifest entry, content
    # differs. Seeded policy — it's the user's, leave it and say so.
    dst = tmp_path / "home" / "app.conf"
    dst.parent.mkdir()
    dst.write_text("was here first\n")

    apt._apply_config_files("app", _cfg(tmp_path))

    assert dst.read_text() == "was here first\n"
    assert "yours to own" in capsys.readouterr().out


def test_apply_config_files_refreshes_an_untouched_destination_when_the_source_changes(tmp_path):
    apt._apply_config_files("app", _cfg(tmp_path))
    (tmp_path / "config" / "app.conf").write_text("seed v2\n")

    apt._apply_config_files("app", _cfg(tmp_path))

    assert (tmp_path / "home" / "app.conf").read_text() == "seed v2\n"


def test_apply_config_files_with_no_mappings_is_a_no_op(tmp_path):
    apt._apply_config_files("app", {"method": "apt"})

    assert not deploy._MANIFEST.exists()
