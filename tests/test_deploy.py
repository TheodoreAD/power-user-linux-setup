"""Unit tests for tasks/deploy.py — the single writer for every path this repo deploys under ~.

The states are what matter here: a destination PULSE can prove it wrote is safe to overwrite
silently, and one it can't must never be destroyed unasked. See tests/README.md.
"""

import json
from pathlib import Path

import pytest
from invoke import Exit

from tasks import deploy, util


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path, monkeypatch):
    """Point the repo root and the state manifest at tmp_path — no test may read or write the
    real ~/.local/state manifest, or resolve a source against the real repo."""
    monkeypatch.setattr(deploy, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(deploy, "_MANIFEST", tmp_path / "state" / "deployed.json")
    monkeypatch.setattr(util, "DRY_RUN", False)


@pytest.fixture
def src(tmp_path):
    """A repo-side source file, as `config/app.conf`."""
    path = tmp_path / "config" / "app.conf"
    path.parent.mkdir(parents=True)
    path.write_text("new content\n")
    return path


def _managed(tmp_path, mechanism=deploy.Mechanism.CONFIG_FILE, *, name="app") -> deploy.Managed:
    return deploy.Managed(
        path=tmp_path / "home" / "app.conf",
        package=name,
        source="config/app.conf",
        mechanism=mechanism,
    )


def _skill(tmp_path, *, name="research-library") -> deploy.Managed:
    source = f"skills/{name}"
    src_dir = tmp_path / source
    src_dir.mkdir(parents=True)
    (src_dir / "SKILL.md").write_text("---\nname: x\n---\n")
    return deploy.Managed(
        path=tmp_path / "home" / ".agents" / "skills" / name,
        package="pkg",
        source=source,
        mechanism=deploy.Mechanism.SKILL,
    )


# ---------------------------------------------------------------------------
# classify
# ---------------------------------------------------------------------------


def test_absent_when_the_destination_doesnt_exist(tmp_path, src):
    assert deploy.classify(_managed(tmp_path)) == deploy.State.ABSENT


def test_clean_when_the_destination_matches_what_we_recorded(tmp_path, src):
    m = _managed(tmp_path)
    deploy.deploy(m)

    assert deploy.classify(m) == deploy.State.CLEAN


def test_stale_when_the_source_moved_on_but_the_destination_is_untouched(tmp_path, src):
    m = _managed(tmp_path)
    deploy.deploy(m)
    src.write_text("source moved on\n")

    assert deploy.classify(m) == deploy.State.STALE


def test_dirty_when_the_destination_was_edited_after_we_wrote_it(tmp_path, src):
    m = _managed(tmp_path)
    deploy.deploy(m)
    m.path.write_text("hand-edited\n")

    assert deploy.classify(m) == deploy.State.DIRTY


def test_unknown_when_a_differing_destination_has_no_manifest_entry(tmp_path, src):
    m = _managed(tmp_path)
    m.path.parent.mkdir(parents=True)
    m.path.write_text("someone else wrote this\n")

    assert deploy.classify(m) == deploy.State.UNKNOWN


def test_a_matching_destination_with_no_manifest_entry_is_clean_not_unknown(tmp_path, src):
    # The backfill case: every machine deployed before this manifest existed must classify clean
    # on the first run, or the whole mechanism lands as a prompt storm.
    m = _managed(tmp_path)
    m.path.parent.mkdir(parents=True)
    m.path.write_text("new content\n")

    assert deploy.classify(m) == deploy.State.CLEAN


def test_a_manifest_from_a_future_version_is_ignored_rather_than_trusted(tmp_path, src):
    m = _managed(tmp_path)
    deploy.deploy(m)
    m.path.write_text("hand-edited\n")
    deploy._MANIFEST.write_text(json.dumps({"version": 99, "entries": {}}) + "\n")

    # Unknown, not dirty — but crucially still not clean, so the edit is never overwritten unasked.
    assert deploy.classify(m) == deploy.State.UNKNOWN


def test_wrapper_script_content_is_stripped_and_newline_terminated(tmp_path, src):
    # tools.py has always deployed `content_file.strip() + "\n"`; a destination holding exactly
    # that must not read as drifted just because the source has trailing blank lines.
    src.write_text("\n\nnew content\n\n\n")
    m = _managed(tmp_path, deploy.Mechanism.WRAPPER_SCRIPT)
    deploy.deploy(m)

    assert m.path.read_text() == "new content\n"
    assert deploy.classify(m) == deploy.State.CLEAN


def test_a_skill_directory_classifies_by_content(tmp_path):
    m = _skill(tmp_path)
    assert deploy.classify(m) == deploy.State.ABSENT

    deploy.deploy(m)
    assert deploy.classify(m) == deploy.State.CLEAN

    (m.path / "SKILL.md").write_text("hand-edited\n")
    assert deploy.classify(m) == deploy.State.DIRTY


def test_the_skill_marker_is_written_and_ignored_by_the_digest(tmp_path):
    m = _skill(tmp_path)
    deploy.deploy(m)

    assert (m.path / deploy.SKILL_MARKER).read_text() == "skills/research-library\n"
    assert deploy.classify(m) == deploy.State.CLEAN


# ---------------------------------------------------------------------------
# deploy
# ---------------------------------------------------------------------------


def test_creating_a_missing_destination_never_prompts(tmp_path, src, monkeypatch):
    monkeypatch.setattr(util, "confirm", lambda *a, **k: pytest.fail("create must not prompt"))
    m = _managed(tmp_path)

    assert deploy.deploy(m) == deploy.Action.CREATED
    assert m.path.read_text() == "new content\n"


def test_a_stale_destination_is_overwritten_without_prompting(tmp_path, src, monkeypatch):
    # Nothing can be lost: the destination still holds exactly what PULSE last wrote there.
    m = _managed(tmp_path)
    deploy.deploy(m)
    src.write_text("source moved on\n")
    monkeypatch.setattr(util, "confirm", lambda *a, **k: pytest.fail("a redeploy must not prompt"))

    assert deploy.deploy(m) == deploy.Action.UPDATED
    assert m.path.read_text() == "source moved on\n"


def test_a_clean_destination_is_a_no_op(tmp_path, src, monkeypatch):
    m = _managed(tmp_path)
    deploy.deploy(m)
    monkeypatch.setattr(util, "confirm", lambda *a, **k: pytest.fail("a no-op must not prompt"))

    assert deploy.deploy(m) == deploy.Action.UNCHANGED


def test_a_dirty_managed_destination_is_kept_when_declined(tmp_path, src, monkeypatch, capsys):
    m = _managed(tmp_path, deploy.Mechanism.WRAPPER_SCRIPT)
    deploy.deploy(m)
    m.path.write_text("hand-edited\n")
    monkeypatch.setattr(util, "confirm", lambda *a, **k: False)

    assert deploy.deploy(m) == deploy.Action.LEFT_ALONE
    assert m.path.read_text() == "hand-edited\n"
    out = capsys.readouterr().out
    assert "-hand-edited" in out and "+new content" in out


def test_a_dirty_managed_destination_is_overwritten_when_confirmed(tmp_path, src, monkeypatch):
    m = _managed(tmp_path, deploy.Mechanism.WRAPPER_SCRIPT)
    deploy.deploy(m)
    m.path.write_text("hand-edited\n")
    monkeypatch.setattr(util, "confirm", lambda *a, **k: True)

    assert deploy.deploy(m) == deploy.Action.UPDATED
    assert m.path.read_text() == "new content\n"


def test_assume_yes_overwrites_a_dirty_destination_without_prompting(tmp_path, src, monkeypatch):
    m = _managed(tmp_path, deploy.Mechanism.WRAPPER_SCRIPT)
    deploy.deploy(m)
    m.path.write_text("hand-edited\n")
    monkeypatch.setattr(util, "confirm", lambda *a, **k: pytest.fail("--yes must not prompt"))

    assert deploy.deploy(m, assume_yes=True) == deploy.Action.UPDATED
    assert m.path.read_text() == "new content\n"


def test_a_non_tty_run_without_yes_leaves_a_dirty_destination_alone(tmp_path, src, monkeypatch, capsys):
    # The container/CI regression this design can cause: util.confirm() returns its default when
    # stdin isn't a terminal, and the default is False. The file must survive, and the run must
    # say so on stdout rather than looking like a successful deploy.
    m = _managed(tmp_path, deploy.Mechanism.WRAPPER_SCRIPT)
    deploy.deploy(m)
    m.path.write_text("hand-edited\n")
    monkeypatch.setattr("sys.stdin", type("NoTTY", (), {"isatty": staticmethod(lambda: False)})())

    assert deploy.deploy(m) == deploy.Action.LEFT_ALONE
    assert m.path.read_text() == "hand-edited\n"
    assert "left alone" in capsys.readouterr().out


def test_a_seeded_destination_that_differs_is_left_alone_without_prompting(tmp_path, src, monkeypatch, capsys):
    # config_files are the user's after first install — divergence is the expected steady state,
    # reported for information, never a prompt and never a warning.
    m = _managed(tmp_path, deploy.Mechanism.CONFIG_FILE)
    deploy.deploy(m)
    m.path.write_text("customized by the user\n")
    monkeypatch.setattr(util, "confirm", lambda *a, **k: pytest.fail("a seeded path must not prompt"))

    assert deploy.deploy(m) == deploy.Action.LEFT_ALONE
    assert m.path.read_text() == "customized by the user\n"
    assert "yours to own" in capsys.readouterr().out


def test_dry_run_reports_without_writing_or_prompting(tmp_path, src, monkeypatch, capsys):
    m = _managed(tmp_path, deploy.Mechanism.WRAPPER_SCRIPT)
    deploy.deploy(m)
    m.path.write_text("hand-edited\n")
    monkeypatch.setattr(util, "DRY_RUN", True)
    monkeypatch.setattr(util, "confirm", lambda *a, **k: pytest.fail("a dry run must not prompt"))

    deploy.deploy(m)

    assert m.path.read_text() == "hand-edited\n"
    assert "would overwrite" in capsys.readouterr().out


def test_dry_run_records_nothing(tmp_path, src, monkeypatch):
    monkeypatch.setattr(util, "DRY_RUN", True)

    deploy.deploy(_managed(tmp_path))

    assert not deploy._MANIFEST.exists()


def test_a_failed_write_is_never_recorded_as_ours(tmp_path, src, monkeypatch):
    m = _managed(tmp_path)
    # Simulate a partial/corrupt write landing something other than the source content.
    monkeypatch.setattr(deploy, "expected_bytes", lambda _: b"truncated")
    monkeypatch.setattr(deploy, "expected_digest", lambda _: "not-the-digest-that-landed")

    with pytest.raises(RuntimeError, match="doesn't match"):
        deploy.deploy(m)
    assert not deploy._MANIFEST.exists()


def test_the_source_resolves_against_the_repo_root_not_the_cwd(tmp_path, src, monkeypatch):
    elsewhere = tmp_path.parent / "elsewhere"
    elsewhere.mkdir(exist_ok=True)
    monkeypatch.chdir(elsewhere)

    deploy.deploy(_managed(tmp_path))

    assert (tmp_path / "home" / "app.conf").read_text() == "new content\n"


# ---------------------------------------------------------------------------
# manifest
# ---------------------------------------------------------------------------


def test_the_manifest_records_package_source_and_digest(tmp_path, src):
    m = _managed(tmp_path)
    deploy.deploy(m)

    entry = deploy.load_manifest()[str(m.path)]
    assert entry["package"] == "app"
    assert entry["source"] == "config/app.conf"
    assert entry["digest"] == deploy.expected_digest(m)
    assert entry["deployed_at"].endswith("+00:00")


def test_forget_drops_one_entry(tmp_path, src):
    m = _managed(tmp_path)
    deploy.deploy(m)

    deploy.forget(m.path)

    assert deploy.load_manifest() == {}


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------


def _stub_config(monkeypatch, packages: dict) -> None:
    monkeypatch.setattr(util, "load_config", lambda: {"packages": packages})
    monkeypatch.setattr(util, "enabled_packages", lambda: packages)
    monkeypatch.setattr(
        util,
        "packages_by_method",
        lambda method: {n: c for n, c in packages.items() if c.get("method") == method},
    )


def test_the_registry_covers_all_three_mechanisms(tmp_path, monkeypatch):
    _stub_config(
        monkeypatch,
        {
            "claude-global-md": {
                "method": "wrapper-script",
                "dest": str(tmp_path / "AGENTS.md"),
                "content_file": "config/global-AGENTS.md",
            },
            "wezterm": {
                "method": "archive",
                "config_files": [{"src": "config/wezterm.lua", "dst": str(tmp_path / "wezterm.lua")}],
            },
            "research-library": {
                "method": "skill",
                "skills": [{"source": "local", "path": "skills/research-library"}],
            },
        },
    )

    registry = deploy.managed_paths(tmp_path)

    assert registry[tmp_path / "AGENTS.md"].mechanism == deploy.Mechanism.WRAPPER_SCRIPT
    assert registry[tmp_path / "wezterm.lua"].mechanism == deploy.Mechanism.CONFIG_FILE
    skill = registry[tmp_path / ".agents" / "skills" / "research-library"]
    assert skill.mechanism == deploy.Mechanism.SKILL
    assert skill.policy == deploy.Policy.MANAGED


def test_a_config_files_destination_is_seeded_not_managed(tmp_path, monkeypatch):
    _stub_config(
        monkeypatch,
        {"wezterm": {"method": "archive", "config_files": [{"src": "config/w.lua", "dst": str(tmp_path / "w.lua")}]}},
    )

    assert deploy.managed_paths(tmp_path)[tmp_path / "w.lua"].policy == deploy.Policy.SEEDED


def test_a_wrapper_script_without_a_content_file_is_not_claimed(tmp_path, monkeypatch):
    _stub_config(monkeypatch, {"thing": {"method": "wrapper-script", "dest": str(tmp_path / "thing")}})

    assert deploy.managed_paths(tmp_path) == {}


def test_a_disabled_package_declares_no_skills(tmp_path, monkeypatch):
    _stub_config(
        monkeypatch,
        {"pkg": {"enabled": False, "skills": [{"source": "local", "path": "skills/x"}]}},
    )

    assert deploy.managed_paths(tmp_path) == {}


def test_an_npx_skill_is_not_claimed(tmp_path, monkeypatch):
    _stub_config(monkeypatch, {"pkg": {"skills": [{"source": "npx", "repo": "owner/repo"}]}})

    assert deploy.managed_paths(tmp_path) == {}


def test_lookup_matches_a_symlink_to_a_managed_destination(tmp_path, monkeypatch):
    dest = tmp_path / "AGENTS.md"
    dest.write_text("x\n")
    link = tmp_path / "CLAUDE.md"
    link.symlink_to(dest)
    _stub_config(
        monkeypatch,
        {
            "claude-global-md": {
                "method": "wrapper-script",
                "dest": str(dest),
                "content_file": "config/global-AGENTS.md",
                "symlink_dest": str(link),
            }
        },
    )

    hit = deploy.lookup(link, tmp_path)

    assert hit is not None
    assert hit.path == dest


def test_lookup_returns_none_for_a_path_this_repo_doesnt_deploy(tmp_path, monkeypatch):
    _stub_config(monkeypatch, {})

    assert deploy.lookup(tmp_path / "something-else", tmp_path) is None


def test_scan_classifies_every_registry_entry(tmp_path, monkeypatch, src):
    _stub_config(
        monkeypatch,
        {"app": {"method": "archive", "config_files": [{"src": "config/app.conf", "dst": str(tmp_path / "app.conf")}]}},
    )

    results = deploy.scan(tmp_path)

    assert [state for _, state in results] == [deploy.State.ABSENT]


def test_a_managed_path_is_absolute_even_when_setup_toml_uses_a_tilde(tmp_path, monkeypatch):
    _stub_config(
        monkeypatch,
        {"x": {"method": "wrapper-script", "dest": "~/.local/bin/x", "content_file": "config/x.sh"}},
    )

    (path,) = deploy.managed_paths(tmp_path)

    assert path == Path.home() / ".local" / "bin" / "x"


# ---------------------------------------------------------------------------
# inv deploy.status
# ---------------------------------------------------------------------------

# deploy.status is @task-wrapped and invoke's Task.__call__ insists its first arg be a real
# Context — .body is the plain underlying function, same pattern as tests/test_ai.py.
_status = deploy.status.body  # pyright: ignore[reportAny, reportFunctionMemberAccess] — invoke's untyped Task.body


@pytest.fixture
def wrapper_pkg(tmp_path, src, monkeypatch):
    """One wrapper-script package deploying config/app.conf, with the registry stubbed to it."""
    dest = tmp_path / "home" / "app.conf"
    _stub_config(
        monkeypatch,
        {"app": {"method": "wrapper-script", "dest": str(dest), "content_file": "config/app.conf"}},
    )
    return dest


def _entry(path) -> deploy.Managed:
    """The registry entry for `path`, asserted present — lookup() is Managed | None."""
    m = deploy.lookup(path)
    assert m is not None
    return m


def test_status_never_writes_or_prompts(wrapper_pkg, monkeypatch):
    monkeypatch.setattr(util, "confirm", lambda *a, **k: pytest.fail("status must not prompt"))
    monkeypatch.setattr(deploy, "_write", lambda _: pytest.fail("status must not write"))

    _status(None)

    assert not wrapper_pkg.exists()


def test_status_reports_a_clean_path_without_a_diff(wrapper_pkg, capsys):
    deploy.deploy(_entry(wrapper_pkg))
    capsys.readouterr()

    _status(None)

    out = capsys.readouterr().out
    assert "ok" in out
    assert "+++" not in out


def test_status_shows_the_diff_and_warns_for_a_dirty_managed_path(wrapper_pkg, capsys):
    deploy.deploy(_entry(wrapper_pkg))
    wrapper_pkg.write_text("hand-edited\n")
    capsys.readouterr()

    _status(None)

    out = capsys.readouterr().out
    assert "edited since PULSE deployed it" in out
    assert "-hand-edited" in out
    assert "no longer match their repo source" in out


def test_status_doesnt_warn_about_a_seeded_path_that_differs(tmp_path, src, monkeypatch, capsys):
    dst = tmp_path / "home" / "app.conf"
    dst.parent.mkdir(parents=True)
    dst.write_text("customized by the user\n")
    _stub_config(
        monkeypatch,
        {"app": {"method": "archive", "config_files": [{"src": "config/app.conf", "dst": str(dst)}]}},
    )

    _status(None)

    out = capsys.readouterr().out
    assert "either edited here, or the source moved on" in out
    assert "no longer match their repo source" not in out


def test_status_name_scopes_to_one_package(tmp_path, src, monkeypatch, capsys):
    _stub_config(
        monkeypatch,
        {
            "app": {"method": "wrapper-script", "dest": str(tmp_path / "a"), "content_file": "config/app.conf"},
            "other": {"method": "wrapper-script", "dest": str(tmp_path / "b"), "content_file": "config/app.conf"},
        },
    )

    _status(None, name="app")

    out = capsys.readouterr().out
    assert "app:" in out
    assert "other:" not in out


def test_status_name_for_a_package_that_deploys_nothing_raises(tmp_path, monkeypatch):
    _stub_config(monkeypatch, {})

    with pytest.raises(Exit, match="no enabled"):
        _status(None, name="nonexistent")


def test_status_path_reports_an_unmanaged_file_as_not_deployed(tmp_path, monkeypatch, capsys):
    _stub_config(monkeypatch, {})
    stray = tmp_path / "hand-written.conf"
    stray.write_text("mine\n")

    _status(None, path=str(stray))

    out = capsys.readouterr().out
    assert "not deployed by PULSE" in out
    assert "[packages.*]" in out


def test_status_path_distinguishes_a_block_owned_file_from_an_unmanaged_one(tmp_path, monkeypatch, capsys):
    # ~/.zshrc is not a deploy destination, but util.ensure_block writes marked regions into it —
    # calling that "not deployed by PULSE, an edit lives only on this machine" is wrong, and wrong
    # in exactly the message meant to teach.
    _stub_config(monkeypatch, {})
    zshrc = tmp_path / ".zshrc"
    zshrc.write_text(f"export FOO=1\n{util._marker('nvm', open_=True)}\nnvm stuff\n")

    _status(None, path=str(zshrc))

    out = capsys.readouterr().out
    assert "PULSE-managed block" in out
    assert "not deployed by PULSE" not in out


def test_status_path_reports_a_managed_file_with_its_source(wrapper_pkg, capsys):
    deploy.deploy(_entry(wrapper_pkg))
    capsys.readouterr()

    _status(None, path=str(wrapper_pkg))

    out = capsys.readouterr().out
    assert "config/app.conf" in out
    assert "managed" in out
