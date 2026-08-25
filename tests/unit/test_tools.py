"""Unit tests for tasks/tools.py's _install_wrapper_script — the install-time writer for
`content_file` packages such as ~/AGENTS.md. Since it delegates the content write to
tasks/deploy.py, what's tested here is the contract at this call site: a fresh destination is
created, a hand-edited one is never silently overwritten (the exact loss this conversion exists to
close), PULSE_ASSUME_YES restores the unattended overwrite, and the symlink handling that stays in
tools.py still works. See tests/README.md.
"""

from pathlib import Path

import pytest

from tasks import deploy, tools, util


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    """Repo root and deploy manifest under tmp_path — never the real repo or ~/.local/state."""
    monkeypatch.setattr(deploy, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(deploy, "_MANIFEST", tmp_path / "state" / "deployed.json")
    monkeypatch.setattr(util, "DRY_RUN", False)
    monkeypatch.setattr(util, "ASSUME_YES", False)
    (tmp_path / "config.sh").write_text("echo hi\n")


def _cfg(tmp_path, **extra) -> dict:
    return {"dest": str(tmp_path / "deployed.sh"), "content_file": "config.sh", **extra}


def test_install_wrapper_script_writes_matching_content(tmp_path):
    tools._install_wrapper_script(None, "test-tool", _cfg(tmp_path))

    dest = tmp_path / "deployed.sh"
    assert dest.read_text() == "echo hi\n"
    assert dest.stat().st_mode & 0o111, "a wrapper script must be executable"


def test_install_wrapper_script_records_the_write_in_the_deploy_manifest(tmp_path):
    tools._install_wrapper_script(None, "test-tool", _cfg(tmp_path))

    entry = deploy.load_manifest()[str(tmp_path / "deployed.sh")]
    assert entry["package"] == "test-tool"
    assert entry["source"] == "config.sh"


def test_install_wrapper_script_raises_when_dest_doesnt_match_after_write(tmp_path, monkeypatch):
    # The exact gap this check exists to catch: the write call "succeeds" but what actually landed
    # on disk doesn't match — simulated here by racing a second writer in between our write and
    # our own re-read, rather than mocking the write (which would just prove the mock works).
    dest = tmp_path / "deployed.sh"
    real_write_bytes = Path.write_bytes

    def racing_write_bytes(self, data, *args, **kwargs):
        n = real_write_bytes(self, data, *args, **kwargs)
        if self == dest:
            real_write_bytes(self, b"clobbered by something else\n")
        return n

    monkeypatch.setattr(Path, "write_bytes", racing_write_bytes)

    with pytest.raises(RuntimeError, match="doesn't match"):
        tools._install_wrapper_script(None, "test-tool", _cfg(tmp_path))
    assert not deploy._MANIFEST.exists(), "a failed write must never be recorded as ours"


def test_install_wrapper_script_never_silently_overwrites_a_hand_edit(tmp_path, monkeypatch, capsys):
    # The regression this conversion exists to prevent: ~/AGENTS.md edited at the destination,
    # then `inv tools.install` — which used to overwrite unconditionally. Non-tty, no --yes: the
    # edit survives, and the run says so instead of looking like a successful install.
    tools._install_wrapper_script(None, "test-tool", _cfg(tmp_path))
    dest = tmp_path / "deployed.sh"
    dest.write_text("echo edited by hand\n")
    monkeypatch.setattr("sys.stdin", type("NoTTY", (), {"isatty": staticmethod(lambda: False)})())

    tools._install_wrapper_script(None, "test-tool", _cfg(tmp_path))

    assert dest.read_text() == "echo edited by hand\n"
    out = capsys.readouterr().out
    assert "-echo edited by hand" in out and "+echo hi" in out
    assert "left alone" in out


def test_install_wrapper_script_overwrites_a_hand_edit_under_pulse_assume_yes(tmp_path, monkeypatch, capsys):
    # The unattended path (bootstrap-devcontainer.sh sets PULSE_ASSUME_YES=1): overwrite, and say so.
    tools._install_wrapper_script(None, "test-tool", _cfg(tmp_path))
    dest = tmp_path / "deployed.sh"
    dest.write_text("echo edited by hand\n")
    monkeypatch.setattr(util, "ASSUME_YES", True)
    monkeypatch.setattr(util, "confirm", lambda *a, **k: pytest.fail("PULSE_ASSUME_YES must not prompt"))

    tools._install_wrapper_script(None, "test-tool", _cfg(tmp_path))

    assert dest.read_text() == "echo hi\n"
    assert "overwrote" in capsys.readouterr().out


def test_install_wrapper_script_redeploys_a_changed_source_without_prompting(tmp_path, monkeypatch):
    # The destination still holds exactly what PULSE last wrote, so nothing can be lost.
    tools._install_wrapper_script(None, "test-tool", _cfg(tmp_path))
    (tmp_path / "config.sh").write_text("echo v2\n")
    monkeypatch.setattr(util, "confirm", lambda *a, **k: pytest.fail("a stale redeploy must not prompt"))

    tools._install_wrapper_script(None, "test-tool", _cfg(tmp_path))

    assert (tmp_path / "deployed.sh").read_text() == "echo v2\n"


def test_install_wrapper_script_dry_run_reports_ok_or_missing_without_writing(tmp_path, monkeypatch, capsys):
    # phases.py's "already looks complete" probe greps this output for MISSING — the label must
    # survive the conversion, and a dry run must never write or record anything.
    monkeypatch.setattr(util, "DRY_RUN", True)

    tools._install_wrapper_script(None, "test-tool", _cfg(tmp_path))

    assert "MISSING" in capsys.readouterr().out
    assert not (tmp_path / "deployed.sh").exists()
    assert not deploy._MANIFEST.exists()


def test_install_wrapper_script_creates_the_symlink_dest(tmp_path):
    link = tmp_path / "CLAUDE.md"

    tools._install_wrapper_script(None, "test-tool", _cfg(tmp_path, symlink_dest=str(link)))

    assert link.is_symlink()
    assert link.resolve() == (tmp_path / "deployed.sh").resolve()


def test_install_wrapper_script_leaves_a_non_symlink_at_symlink_dest_alone(tmp_path, capsys):
    link = tmp_path / "CLAUDE.md"
    link.write_text("a real file, not a symlink\n")

    tools._install_wrapper_script(None, "test-tool", _cfg(tmp_path, symlink_dest=str(link)))

    assert not link.is_symlink()
    assert link.read_text() == "a real file, not a symlink\n"
    assert "Leaving it alone" in capsys.readouterr().out
