"""Unit tests for tasks/verify.py's pure helpers: _resolve (which check each package method gets)
and _wrapper_script_up_to_date/_wrapper_script_expected (wrapper-script's content-match check,
exercised against real tmp_path files rather than mocked I/O — content comparison is the entire
point of the check). See tests/README.md.
"""

from tasks import verify


def test_resolve_wrapper_script_with_content_file_returns_content_kind():
    cfg = {"dest": "~/AGENTS.md", "content_file": "config/global-AGENTS.md"}
    kind, target = verify._resolve("claude-global-md", cfg, verify.util.PackageMethod.WRAPPER_SCRIPT)
    assert kind == "content"
    assert target == f"~/AGENTS.md{verify._CONTENT_SEP}config/global-AGENTS.md"


def test_resolve_wrapper_script_without_content_file_falls_back_to_path():
    cfg = {"dest": "~/.local/bin/some-tool"}
    kind, target = verify._resolve("some-tool", cfg, verify.util.PackageMethod.WRAPPER_SCRIPT)
    assert (kind, target) == ("path", "~/.local/bin/some-tool")


def test_resolve_still_honors_verify_false_and_verify_cmd_before_method_dispatch():
    assert verify._resolve("x", {"verify": False}, verify.util.PackageMethod.WRAPPER_SCRIPT)[0] == "skip"
    kind, target = verify._resolve("x", {"verify_cmd": "x --check"}, verify.util.PackageMethod.WRAPPER_SCRIPT)
    assert (kind, target) == ("cmd", "x --check")


def test_wrapper_script_up_to_date_true_when_dest_matches_content_file(tmp_path, monkeypatch):
    monkeypatch.setattr(verify, "_REPO_ROOT", tmp_path)
    (tmp_path / "config.txt").write_text("hello\n")
    dest = tmp_path / "deployed.txt"
    dest.write_text("hello\n")
    assert verify._wrapper_script_up_to_date(str(dest), "config.txt") is True


def test_wrapper_script_up_to_date_false_when_dest_is_stale(tmp_path, monkeypatch):
    # Exactly the gap this check exists to catch: dest exists, but its content no longer matches
    # the source it was last deployed from (a redeploy never ran, or landed hand-edited content).
    monkeypatch.setattr(verify, "_REPO_ROOT", tmp_path)
    (tmp_path / "config.txt").write_text("new content\n")
    dest = tmp_path / "deployed.txt"
    dest.write_text("old content\n")
    assert verify._wrapper_script_up_to_date(str(dest), "config.txt") is False


def test_wrapper_script_up_to_date_false_when_dest_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(verify, "_REPO_ROOT", tmp_path)
    (tmp_path / "config.txt").write_text("hello\n")
    assert verify._wrapper_script_up_to_date(str(tmp_path / "never-deployed.txt"), "config.txt") is False


def test_wrapper_script_expected_strips_and_adds_trailing_newline(tmp_path, monkeypatch):
    # Must match _install_wrapper_script's own .strip() + "\n" transform exactly, or every
    # deployed file would show as perpetually stale even right after a correct deploy.
    monkeypatch.setattr(verify, "_REPO_ROOT", tmp_path)
    (tmp_path / "config.txt").write_text("\n\n  content with padding  \n\n")
    assert verify._wrapper_script_expected("config.txt") == "content with padding\n"
