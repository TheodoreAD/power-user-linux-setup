"""Unit tests for tasks/tools.py's _install_wrapper_script — specifically its post-write
self-verification (re-read dest and compare against the content just written, rather than trusting
the write call succeeded). See tests/README.md.
"""

from pathlib import Path

import pytest

from tasks import tools, util


def test_install_wrapper_script_writes_matching_content(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(util, "DRY_RUN", False)
    (tmp_path / "config.sh").write_text("echo hi\n")
    dest = tmp_path / "deployed.sh"

    tools._install_wrapper_script(None, "test-tool", {"dest": str(dest), "content_file": "config.sh"})

    assert dest.read_text() == "echo hi\n"


def test_install_wrapper_script_raises_when_dest_doesnt_match_after_write(tmp_path, monkeypatch):
    # The exact gap this check exists to catch: the write call "succeeds" but what actually landed
    # on disk doesn't match — simulated here by racing a second writer in between our write and
    # our own re-read, rather than mocking Path.write_text (which would just prove the mock works).
    monkeypatch.setattr(tools, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(util, "DRY_RUN", False)
    (tmp_path / "config.sh").write_text("echo hi\n")
    dest = tmp_path / "deployed.sh"

    real_write_text = Path.write_text

    def racing_write_text(self, content, *args, **kwargs):
        real_write_text(self, content, *args, **kwargs)
        if self == dest:
            real_write_text(self, "clobbered by something else\n")
        return len(content)

    monkeypatch.setattr(Path, "write_text", racing_write_text)

    with pytest.raises(RuntimeError, match="doesn't match"):
        tools._install_wrapper_script(None, "test-tool", {"dest": str(dest), "content_file": "config.sh"})
