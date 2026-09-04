"""Unit tests for tasks/tools.py's _install_wrapper_script — the install-time writer for
`content_file` packages such as ~/AGENTS.md. Since it delegates the content write to
tasks/deploy.py, what's tested here is the contract at this call site: a fresh destination is
created, a hand-edited one is never silently overwritten (the exact loss this conversion exists to
close), and PULSE_ASSUME_YES restores the unattended overwrite. The symlink writer itself moved to
tasks/deploy.py on 2026-09-04; the tests exercising it through this installer stayed here, since
this call site is what has to keep wiring it correctly. See tests/README.md.

Also covers _install_archive's compression handling, which is the one part of that installer with
a format it cannot declare: the archive is fetched to a file and read with `tar -xf` so tar sniffs
gzip/xz/bzip2 itself. These run the real shell against real tarballs over file:// URLs — the bug
being guarded is a tar invocation, so mocking the run would test nothing.
"""

import subprocess
from pathlib import Path
from typing import override

import pytest
from invoke import Context, MockContext, Result

from tasks import deploy, tools, util


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    """Repo root and deploy manifest under tmp_path — never the real repo or ~/.local/state."""
    monkeypatch.setattr(deploy, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(deploy, "_MANIFEST", tmp_path / "state" / "deployed.json")
    monkeypatch.setattr(util, "DRY_RUN", False)
    monkeypatch.setattr(util, "ASSUME_YES", False)
    (tmp_path / "config.sh").write_text("echo hi\n")


def _cfg(tmp_path, *, symlink_dest: str | list[str | dict[str, str | bool]] | None = None) -> util.PackageConfig:
    cfg: util.PackageConfig = {"dest": str(tmp_path / "deployed.sh"), "content_file": "config.sh"}
    if symlink_dest is not None:
        cfg["symlink_dest"] = symlink_dest
    return cfg


def test_install_wrapper_script_writes_matching_content(tmp_path):
    tools._install_wrapper_script(MockContext(), "test-tool", _cfg(tmp_path))

    dest = tmp_path / "deployed.sh"
    assert dest.read_text() == "echo hi\n"
    assert dest.stat().st_mode & 0o111, "a wrapper script must be executable"


def test_install_wrapper_script_records_the_write_in_the_deploy_manifest(tmp_path):
    tools._install_wrapper_script(MockContext(), "test-tool", _cfg(tmp_path))

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
        tools._install_wrapper_script(MockContext(), "test-tool", _cfg(tmp_path))
    assert not deploy._MANIFEST.exists(), "a failed write must never be recorded as ours"


def test_install_wrapper_script_never_silently_overwrites_a_hand_edit(tmp_path, monkeypatch, capsys):
    # The regression this conversion exists to prevent: ~/AGENTS.md edited at the destination,
    # then `inv tools.install` — which used to overwrite unconditionally. Non-tty, no --yes: the
    # edit survives, and the run says so instead of looking like a successful install.
    tools._install_wrapper_script(MockContext(), "test-tool", _cfg(tmp_path))
    dest = tmp_path / "deployed.sh"
    dest.write_text("echo edited by hand\n")
    monkeypatch.setattr("sys.stdin", type("NoTTY", (), {"isatty": staticmethod(lambda: False)})())

    tools._install_wrapper_script(MockContext(), "test-tool", _cfg(tmp_path))

    assert dest.read_text() == "echo edited by hand\n"
    out = capsys.readouterr().out
    assert "-echo edited by hand" in out
    assert "+echo hi" in out
    assert "left alone" in out


def test_install_wrapper_script_overwrites_a_hand_edit_under_pulse_assume_yes(tmp_path, monkeypatch, capsys):
    # The unattended path (bootstrap-devcontainer.sh sets PULSE_ASSUME_YES=1): overwrite, and say so.
    tools._install_wrapper_script(MockContext(), "test-tool", _cfg(tmp_path))
    dest = tmp_path / "deployed.sh"
    dest.write_text("echo edited by hand\n")
    monkeypatch.setattr(util, "ASSUME_YES", True)
    monkeypatch.setattr(util, "confirm", lambda *a, **k: pytest.fail("PULSE_ASSUME_YES must not prompt"))

    tools._install_wrapper_script(MockContext(), "test-tool", _cfg(tmp_path))

    assert dest.read_text() == "echo hi\n"
    assert "overwrote" in capsys.readouterr().out


def test_install_wrapper_script_redeploys_a_changed_source_without_prompting(tmp_path, monkeypatch):
    # The destination still holds exactly what PULSE last wrote, so nothing can be lost.
    tools._install_wrapper_script(MockContext(), "test-tool", _cfg(tmp_path))
    (tmp_path / "config.sh").write_text("echo v2\n")
    monkeypatch.setattr(util, "confirm", lambda *a, **k: pytest.fail("a stale redeploy must not prompt"))

    tools._install_wrapper_script(MockContext(), "test-tool", _cfg(tmp_path))

    assert (tmp_path / "deployed.sh").read_text() == "echo v2\n"


def test_install_wrapper_script_dry_run_reports_ok_or_missing_without_writing(tmp_path, monkeypatch, capsys):
    # phases.py's "already looks complete" probe greps this output for MISSING — the label must
    # survive the conversion, and a dry run must never write or record anything.
    monkeypatch.setattr(util, "DRY_RUN", True)

    tools._install_wrapper_script(MockContext(), "test-tool", _cfg(tmp_path))

    assert "MISSING" in capsys.readouterr().out
    assert not (tmp_path / "deployed.sh").exists()
    assert not deploy._MANIFEST.exists()


def test_install_wrapper_script_creates_the_symlink_dest(tmp_path):
    link = tmp_path / "CLAUDE.md"

    tools._install_wrapper_script(MockContext(), "test-tool", _cfg(tmp_path, symlink_dest=str(link)))

    assert link.is_symlink()
    assert link.resolve() == (tmp_path / "deployed.sh").resolve()


def test_install_wrapper_script_leaves_a_non_symlink_at_symlink_dest_alone(tmp_path, capsys):
    link = tmp_path / "CLAUDE.md"
    link.write_text("a real file, not a symlink\n")

    tools._install_wrapper_script(MockContext(), "test-tool", _cfg(tmp_path, symlink_dest=str(link)))

    assert not link.is_symlink()
    assert link.read_text() == "a real file, not a symlink\n"
    assert "Leaving it alone" in capsys.readouterr().out


def test_install_wrapper_script_creates_every_symlink_in_a_list(tmp_path):
    """One real file, linked into several agents' own instruction paths."""
    claude = tmp_path / "dot-claude" / "CLAUDE.md"
    copilot = tmp_path / "dot-copilot" / "copilot-instructions.md"
    claude.parent.mkdir()
    copilot.parent.mkdir()

    tools._install_wrapper_script(MockContext(), "test-tool", _cfg(tmp_path, symlink_dest=[str(claude), str(copilot)]))

    assert claude.is_symlink()
    assert copilot.is_symlink()
    assert claude.resolve() == copilot.resolve() == (tmp_path / "deployed.sh")


def test_install_wrapper_script_skips_a_symlink_whose_parent_doesnt_exist(tmp_path, capsys):
    """A missing ~/.codex means Codex isn't installed — creating it to hold an instruction file
    would make an absent agent look present, so the link is reported and skipped instead."""
    absent = tmp_path / "dot-codex" / "AGENTS.md"

    tools._install_wrapper_script(MockContext(), "test-tool", _cfg(tmp_path, symlink_dest=[str(absent)]))

    assert not absent.parent.exists()
    assert "skipped" in capsys.readouterr().out


def test_install_wrapper_script_links_the_installed_agents_and_skips_the_rest(tmp_path):
    """One absent agent must not stop the others from being linked."""
    present = tmp_path / "dot-claude" / "CLAUDE.md"
    present.parent.mkdir()
    absent = tmp_path / "dot-codex" / "AGENTS.md"

    tools._install_wrapper_script(MockContext(), "test-tool", _cfg(tmp_path, symlink_dest=[str(absent), str(present)]))

    assert present.is_symlink()
    assert not absent.parent.exists()


def test_install_wrapper_script_creates_the_parent_of_an_always_symlink(tmp_path):
    """`always = true` is for a path no vendor owns, so a missing parent is not a verdict.

    `~/.agents/` is created by this repo, so asking "does it exist?" only ever answers a question
    about PULSE's own earlier run — the absent-agent rule has nothing to detect there.
    """
    link = tmp_path / "dot-agents" / "AGENTS.md"

    tools._install_wrapper_script(
        MockContext(), "test-tool", _cfg(tmp_path, symlink_dest=[{"path": str(link), "always": True}])
    )

    assert link.is_symlink()
    assert link.resolve() == (tmp_path / "deployed.sh").resolve()


def test_an_always_symlink_does_not_make_its_siblings_unconditional(tmp_path):
    """The flag is per-destination: a vendor path in the same list keeps the absent-agent rule."""
    always = tmp_path / "dot-agents" / "AGENTS.md"
    vendor = tmp_path / "dot-codex" / "AGENTS.md"

    tools._install_wrapper_script(
        MockContext(),
        "test-tool",
        _cfg(tmp_path, symlink_dest=[{"path": str(always), "always": True}, str(vendor)]),
    )

    assert always.is_symlink()
    assert not vendor.parent.exists()


def test_symlink_dests_defaults_always_to_false_for_a_bare_string(tmp_path):
    """A plain string must stay conditional — the flag is opt-in, never inferred."""
    dests = deploy.symlink_dests(_cfg(tmp_path, symlink_dest=[str(tmp_path / "a"), {"path": str(tmp_path / "b")}]))

    assert [d.always for d in dests] == [False, False]


def test_symlink_dests_rejects_a_table_without_a_path(tmp_path):
    """A typo'd key must fail loudly rather than silently declaring nothing."""
    with pytest.raises(TypeError, match="string `path`"):
        deploy.symlink_dests(_cfg(tmp_path, symlink_dest=[{"always": True}]))


def test_a_dest_change_converts_the_old_real_file_into_a_link(tmp_path, capsys):
    """Moving a package's `dest` must not leave two real files with the links on the old one.

    This is the `agents-md` move of 2026-09-04 in miniature: deploy to path A, repoint `dest` at
    path B, declare A as a link. A holds exactly what PULSE wrote, so converting it loses nothing —
    and refusing would strand every existing machine in the split-brain state.
    """
    old = tmp_path / "AGENTS.md"
    new = tmp_path / "dot-agents" / "AGENTS.md"
    tools._install_wrapper_script(MockContext(), "agents-md", {"dest": str(old), "content_file": "config.sh"})
    assert old.is_file()
    assert not old.is_symlink()

    moved: util.PackageConfig = {
        "dest": str(new),
        "content_file": "config.sh",
        "symlink_dest": [{"path": str(old), "always": True}],
    }
    tools._install_wrapper_script(MockContext(), "agents-md", moved)

    assert new.is_file()
    assert old.is_symlink()
    assert old.resolve() == new.resolve()
    assert "replaced a stale copy" in capsys.readouterr().out


def test_a_dest_change_repoints_a_link_that_aimed_at_the_old_dest(tmp_path, capsys):
    """A vendor link left pointing at the previous destination is stale, not a hand-edit.

    Without this the four `~/.claude`, `~/.codex`, ... links keep resolving to the old file after a
    move — the agent reads a copy that no longer gets updated, and nothing says so.
    """
    old = tmp_path / "AGENTS.md"
    new = tmp_path / "dot-agents" / "AGENTS.md"
    vendor = tmp_path / "dot-claude" / "CLAUDE.md"
    vendor.parent.mkdir()
    tools._install_wrapper_script(
        MockContext(), "agents-md", {"dest": str(old), "content_file": "config.sh", "symlink_dest": [str(vendor)]}
    )
    assert vendor.resolve() == old.resolve()

    moved: util.PackageConfig = {"dest": str(new), "content_file": "config.sh", "symlink_dest": [str(vendor)]}
    tools._install_wrapper_script(MockContext(), "agents-md", moved)

    assert vendor.resolve() == new.resolve()
    assert "replaced a stale link" in capsys.readouterr().out


def test_a_dest_change_still_refuses_to_replace_a_hand_edited_old_file(tmp_path, capsys):
    """The never-clobber promise outranks the migration: a DIRTY old file is still someone's work."""
    old = tmp_path / "AGENTS.md"
    new = tmp_path / "dot-agents" / "AGENTS.md"
    tools._install_wrapper_script(MockContext(), "agents-md", {"dest": str(old), "content_file": "config.sh"})
    old.write_text("edited by hand after the deploy\n")

    moved: util.PackageConfig = {
        "dest": str(new),
        "content_file": "config.sh",
        "symlink_dest": [{"path": str(old), "always": True}],
    }
    tools._install_wrapper_script(MockContext(), "agents-md", moved)

    assert old.read_text() == "edited by hand after the deploy\n"
    assert not old.is_symlink()
    assert "Leaving it alone" in capsys.readouterr().out


def test_a_hand_made_symlink_to_an_unmanaged_file_is_left_alone(tmp_path, capsys):
    """Only a link into something this repo deployed is replaceable — the manifest is the proof."""
    someone_elses = tmp_path / "notes.md"
    someone_elses.write_text("my own file\n")
    link = tmp_path / "CLAUDE.md"
    link.symlink_to(someone_elses)

    tools._install_wrapper_script(MockContext(), "test-tool", _cfg(tmp_path, symlink_dest=str(link)))

    assert link.resolve() == someone_elses.resolve()
    assert "Leaving it alone" in capsys.readouterr().out


def test_install_wrapper_script_dry_run_ignores_a_link_whose_parent_doesnt_exist(tmp_path, monkeypatch, capsys):
    """The dry run must apply the same absent-agent rule the writer does.

    It didn't, and reported `[agents-md] MISSING` on a machine where `deploy.status` said `ok` and
    the deployed file was correct — because `~/.codex/` and `~/.gemini/` don't exist here and the
    dry-run branch counted their unmade links as failures. A dry run that cries wolf on a healthy
    machine is how a report teaches people to ignore it.
    """
    cfg = _cfg(tmp_path, symlink_dest=[str(tmp_path / "dot-codex" / "AGENTS.md")])
    tools._install_wrapper_script(MockContext(), "test-tool", cfg)  # deploy the content for real
    capsys.readouterr()
    monkeypatch.setattr(util, "DRY_RUN", True)

    tools._install_wrapper_script(MockContext(), "test-tool", cfg)

    assert "MISSING" not in capsys.readouterr().out


class _ShellContext(Context):
    """Runs the command strings _install_archive builds, for real, via subprocess.

    Only the runner is substituted — the commands, and the tar that executes them, are the real
    ones, which is where the bug being guarded lives. Invoke's own Local runner can't be used here:
    it mirrors stdin (which pytest's capture refuses outright) and leaks the subprocess file
    objects, which pytest's unraisable-exception plugin then reports as a failure in whichever
    unrelated test happens to trigger the collection.
    """

    @override
    def run(self, command: str, **kwargs: object) -> Result:
        subprocess.run(command, shell=True, check=True)
        return Result(command=command, exited=0)


def _tarball(tmp_path: Path, name: str, flag: str) -> Path:
    """A real archive with one file one level down, so strip_components has something to strip."""
    src = tmp_path / "src" / "Telegram"
    src.mkdir(parents=True)
    (src / "binary").write_text("payload\n")
    archive = tmp_path / name
    subprocess.run(["tar", f"-c{flag}f", str(archive), "-C", str(tmp_path / "src"), "Telegram"], check=True)
    return archive


def _archive_cfg(install_dir: Path, archive: Path) -> util.PackageConfig:
    return {
        "download_url": archive.as_uri(),
        "extract_to": str(install_dir),
        "install_dir": str(install_dir),
        "strip_components": 1,
        "check_path": str(install_dir / "binary"),
    }


@pytest.mark.parametrize(("suffix", "flag"), [("tar.gz", "z"), ("tar.xz", "J"), ("tar.bz2", "j")])
def test_install_archive_extracts_every_compression_format(tmp_path, suffix, flag):
    """tar's -z was hardcoded, so anything but gzip failed outright with "Archive is compressed.
    Use -J option". Telegram Desktop ships only .tar.xz, and its download URL carries no extension
    to sniff, so the format has to be detected from the bytes."""
    install_dir = tmp_path / "installed"

    tools._install_archive(_ShellContext(), "t", _archive_cfg(install_dir, _tarball(tmp_path, f"a.{suffix}", flag)))

    assert (install_dir / "binary").read_text() == "payload\n"


def test_install_archive_leaves_no_download_behind(tmp_path):
    """The fetched archive is a temp file — extracting from one must not leave it in install_dir."""
    install_dir = tmp_path / "installed"

    tools._install_archive(_ShellContext(), "t", _archive_cfg(install_dir, _tarball(tmp_path, "a.tar.xz", "J")))

    assert sorted(p.name for p in install_dir.iterdir()) == ["binary"]
