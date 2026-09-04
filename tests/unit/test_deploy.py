"""Unit tests for tasks/deploy.py — the single writer for every path this repo deploys under ~.

The states are what matter here: a destination PULSE can prove it wrote is safe to overwrite
silently, and one it can't must never be destroyed unasked. See tests/README.md.
"""

import json
from pathlib import Path

import pytest
from invoke import Exit, MockContext

from tasks import deploy, util


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path, monkeypatch):
    """Point the repo root and the state manifest at tmp_path — no test may read or write the
    real ~/.local/state manifest, or resolve a source against the real repo."""
    monkeypatch.setattr(deploy, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(deploy, "_MANIFEST", tmp_path / "state" / "deployed.json")
    monkeypatch.setattr(util, "DRY_RUN", False)
    monkeypatch.setattr(util, "ASSUME_YES", False)


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
    assert "-hand-edited" in out
    assert "+new content" in out


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


def test_pulse_assume_yes_overwrites_a_dirty_destination_without_prompting(tmp_path, src, monkeypatch):
    # The env-var form of --yes, for `inv setup` and the other composite entry points that have no
    # flag to pass through — what bootstrap-devcontainer.sh sets.
    m = _managed(tmp_path, deploy.Mechanism.WRAPPER_SCRIPT)
    deploy.deploy(m)
    m.path.write_text("hand-edited\n")
    monkeypatch.setattr(util, "ASSUME_YES", True)
    monkeypatch.setattr(util, "confirm", lambda *a, **k: pytest.fail("PULSE_ASSUME_YES must not prompt"))

    assert deploy.deploy(m) == deploy.Action.UPDATED
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


def _stub_config(monkeypatch, packages: dict[str, util.PackageConfig]) -> None:
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
            "agents-md": {
                "method": "wrapper-script",
                "dest": str(tmp_path / "AGENTS.md"),
                "content_file": "config/statusline-command.sh",
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
            "agents-md": {
                "method": "wrapper-script",
                "dest": str(dest),
                "content_file": "config/statusline-command.sh",
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
# Context — .body is the plain underlying function, same pattern as tests/unit/test_ai.py. The
# body declares `c: Context` too, so it gets a MockContext (never consulted: status/all never run
# a shell command) rather than None.
_status = deploy.status.body


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

    _status(MockContext())

    assert not wrapper_pkg.exists()


def test_status_reports_a_clean_path_without_a_diff(wrapper_pkg, capsys):
    deploy.deploy(_entry(wrapper_pkg))
    capsys.readouterr()

    _status(MockContext())

    out = capsys.readouterr().out
    assert "ok" in out
    assert "+++" not in out


def test_status_shows_the_diff_and_warns_for_a_dirty_managed_path(wrapper_pkg, capsys):
    deploy.deploy(_entry(wrapper_pkg))
    wrapper_pkg.write_text("hand-edited\n")
    capsys.readouterr()

    _status(MockContext())

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

    _status(MockContext())

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

    _status(MockContext(), name="app")

    out = capsys.readouterr().out
    assert "app:" in out
    assert "other:" not in out


def test_status_name_for_a_package_that_deploys_nothing_raises(tmp_path, monkeypatch):
    _stub_config(monkeypatch, {})

    with pytest.raises(Exit, match="no enabled"):
        _status(MockContext(), name="nonexistent")


def test_status_path_reports_an_unmanaged_file_as_not_deployed(tmp_path, monkeypatch, capsys):
    _stub_config(monkeypatch, {})
    stray = tmp_path / "hand-written.conf"
    stray.write_text("mine\n")

    _status(MockContext(), path=str(stray))

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

    _status(MockContext(), path=str(zshrc))

    out = capsys.readouterr().out
    assert "PULSE-managed block" in out
    assert "not deployed by PULSE" not in out


def test_status_path_reports_a_managed_file_with_its_source(wrapper_pkg, capsys):
    deploy.deploy(_entry(wrapper_pkg))
    capsys.readouterr()

    _status(MockContext(), path=str(wrapper_pkg))

    out = capsys.readouterr().out
    assert "config/app.conf" in out
    assert "managed" in out


# ---------------------------------------------------------------------------
# inv deploy.all
# ---------------------------------------------------------------------------

_all = deploy.all_.body


def test_all_creates_a_missing_destination_and_records_it(wrapper_pkg, src, monkeypatch, capsys):
    monkeypatch.setattr(util, "confirm", lambda *a, **k: pytest.fail("create must not prompt"))

    _all(MockContext())

    assert wrapper_pkg.read_text() == src.read_text().strip() + "\n"
    assert deploy.classify(_entry(wrapper_pkg)) == deploy.State.CLEAN
    assert "1 path(s): 1 created" in capsys.readouterr().out


def test_all_shows_the_diff_and_keeps_a_dirty_destination_when_declined(wrapper_pkg, monkeypatch, capsys):
    _all(MockContext())
    wrapper_pkg.write_text("hand-edited\n")
    monkeypatch.setattr(util, "confirm", lambda *a, **k: False)

    _all(MockContext())

    out = capsys.readouterr().out
    assert wrapper_pkg.read_text() == "hand-edited\n"
    assert "-hand-edited" in out
    assert "1 left alone" in out


def test_all_yes_overwrites_a_dirty_destination_without_prompting(wrapper_pkg, src, monkeypatch):
    _all(MockContext())
    wrapper_pkg.write_text("hand-edited\n")
    monkeypatch.setattr(util, "confirm", lambda *a, **k: pytest.fail("--yes must not prompt"))

    _all(MockContext(), yes=True)

    assert wrapper_pkg.read_text() == src.read_text().strip() + "\n"


def test_all_name_scopes_to_one_package(tmp_path, src, monkeypatch):
    a = tmp_path / "home" / "a.conf"
    b = tmp_path / "home" / "b.conf"
    _stub_config(
        monkeypatch,
        {
            "a": {"method": "wrapper-script", "dest": str(a), "content_file": "config/app.conf"},
            "b": {"method": "wrapper-script", "dest": str(b), "content_file": "config/app.conf"},
        },
    )

    _all(MockContext(), name="a")

    assert a.exists()
    assert not b.exists()


def test_all_name_for_a_package_that_deploys_nothing_raises(tmp_path, monkeypatch):
    _stub_config(monkeypatch, {"nothing": {"method": "apt"}})
    with pytest.raises(Exit):
        _all(MockContext(), name="nothing")


# ---------------------------------------------------------------------------
# Assembled destinations (~/AGENTS.md)
# ---------------------------------------------------------------------------


@pytest.fixture
def agents_md_fragments(tmp_path):
    """Two repo-side fragments, as `config/agents-md/*.md`."""
    d = tmp_path / "config" / "agents-md"
    d.mkdir(parents=True)
    (d / "this-setup.md").write_text("# Title\n\n## This setup\n\nMachine facts.\n")
    (d / "portable.md").write_text("## Conventions\n\nPortable rules.\n")
    return d


def test_fragments_sort_by_order_then_package(monkeypatch):
    _stub_config(
        monkeypatch,
        {
            "zeta": {"method": "apt", "agents_md": [{"src": "c.md", "order": 10}]},
            "alpha": {"method": "apt", "agents_md": [{"src": "b.md", "order": 20}]},
            # Same order as alpha's — the package name is what breaks the tie, so the assembled
            # document is byte-identical across runs however setup.toml's keys iterate.
            "beta": {"method": "apt", "agents_md": [{"src": "d.md", "order": 20}]},
        },
    )

    assert deploy.fragments("agents_md") == ("c.md", "b.md", "d.md")


def test_a_fragment_with_no_order_lands_after_the_curated_ones(monkeypatch):
    _stub_config(
        monkeypatch,
        {
            "curated": {"method": "apt", "agents_md": [{"src": "a.md", "order": 30}]},
            "undeclared": {"method": "apt", "agents_md": [{"src": "z.md"}]},
        },
    )

    assert deploy.fragments("agents_md") == ("a.md", "z.md")


def test_a_fragment_missing_src_raises(monkeypatch):
    _stub_config(monkeypatch, {"broken": {"method": "apt", "agents_md": [{"order": 10}]}})
    with pytest.raises(RuntimeError, match="agents_md"):
        deploy.fragments("agents_md")


def test_assemble_wraps_each_fragment_in_its_own_block(agents_md_fragments):
    text = deploy.assemble(("config/agents-md/this-setup.md", "config/agents-md/portable.md"))

    assert text.startswith("<!-- PULSE::agents-md/this-setup -->")
    assert text.count("<!-- PULSE::") == 2
    assert "<!-- /PULSE::agents-md/portable -->" in text
    # Order is the argument's, and the fragments' own content survives verbatim.
    assert text.index("Machine facts.") < text.index("Portable rules.")


def test_assemble_is_a_pure_function_of_the_fragments(agents_md_fragments):
    """The digest comparison in classify() depends on this: assembling twice must give the same
    bytes, and nothing outside the repo may influence the result."""
    parts = ("config/agents-md/this-setup.md", "config/agents-md/portable.md")
    assert deploy.assemble(parts) == deploy.assemble(parts)


def test_the_registry_builds_an_assembled_entry_from_declared_fragments(tmp_path, agents_md_fragments, monkeypatch):
    dest = tmp_path / "home" / "AGENTS.md"
    _stub_config(
        monkeypatch,
        {
            "agents-md": {
                "method": "wrapper-script",
                "dest": str(dest),
                "assembled_from": "agents_md",
                "agents_md": [{"src": "config/agents-md/this-setup.md", "order": 10}],
            },
            # A second package contributing a fragment to the same destination — the any-section
            # half of the mechanism, and the reason `parts` isn't read off one package's list.
            "other": {"method": "apt", "agents_md": [{"src": "config/agents-md/portable.md", "order": 20}]},
        },
    )

    m = deploy.lookup(dest)

    assert m is not None
    assert m.mechanism == deploy.Mechanism.ASSEMBLED
    assert m.parts == ("config/agents-md/this-setup.md", "config/agents-md/portable.md")
    assert m.policy == deploy.Policy.MANAGED


def test_an_assembled_destination_deploys_and_then_classifies_clean(tmp_path, agents_md_fragments, monkeypatch):
    dest = tmp_path / "home" / "AGENTS.md"
    _stub_config(
        monkeypatch,
        {
            "agents-md": {
                "method": "wrapper-script",
                "dest": str(dest),
                "assembled_from": "agents_md",
                "agents_md": [
                    {"src": "config/agents-md/this-setup.md", "order": 10},
                    {"src": "config/agents-md/portable.md", "order": 20},
                ],
            }
        },
    )
    m = deploy.lookup(dest)
    assert m is not None

    assert deploy.deploy(m) == deploy.Action.CREATED
    assert dest.read_text().endswith("<!-- /PULSE::agents-md/portable -->\n")
    assert deploy.classify(m) == deploy.State.CLEAN


def test_editing_a_fragment_makes_the_deployed_file_stale(tmp_path, agents_md_fragments, monkeypatch):
    """STALE, not DIRTY: the destination still holds exactly what PULSE wrote, so the redeploy is
    safe and silent — the change came from the repo side."""
    dest = tmp_path / "home" / "AGENTS.md"
    _stub_config(
        monkeypatch,
        {
            "agents-md": {
                "method": "wrapper-script",
                "dest": str(dest),
                "assembled_from": "agents_md",
                "agents_md": [{"src": "config/agents-md/portable.md", "order": 10}],
            }
        },
    )
    m = deploy.lookup(dest)
    assert m is not None
    deploy.deploy(m)

    (agents_md_fragments / "portable.md").write_text("## Conventions\n\nRewritten.\n")

    assert deploy.classify(m) == deploy.State.STALE
    assert deploy.deploy(m) == deploy.Action.UPDATED
    assert "Rewritten." in dest.read_text()


def test_a_hand_edited_assembled_file_is_not_overwritten_unasked(tmp_path, agents_md_fragments, monkeypatch):
    """The markers give no partial ownership here — the file is regenerated whole — so this
    manifest-backed check is the only thing standing between a hand-edit and its loss."""
    dest = tmp_path / "home" / "AGENTS.md"
    _stub_config(
        monkeypatch,
        {
            "agents-md": {
                "method": "wrapper-script",
                "dest": str(dest),
                "assembled_from": "agents_md",
                "agents_md": [{"src": "config/agents-md/portable.md", "order": 10}],
            }
        },
    )
    m = deploy.lookup(dest)
    assert m is not None
    deploy.deploy(m)

    dest.write_text(dest.read_text() + "\nHand-written note.\n")

    assert deploy.classify(m) == deploy.State.DIRTY
    assert deploy.deploy(m) == deploy.Action.LEFT_ALONE
    assert "Hand-written note." in dest.read_text()


def test_assembled_from_naming_a_field_no_package_fills_raises(tmp_path, monkeypatch):
    """A destination declared with no fragments anywhere would deploy an empty ~/AGENTS.md —
    louder to fail than to silently wipe every rule on the machine."""
    _stub_config(
        monkeypatch,
        {
            "agents-md": {
                "method": "wrapper-script",
                "dest": str(tmp_path / "AGENTS.md"),
                "assembled_from": "agents_md",
            }
        },
    )
    with pytest.raises(RuntimeError, match="agents_md"):
        deploy.managed_paths()


# ---------------------------------------------------------------------------
# The install-time applier, and the MANAGED_FILE mechanism
# ---------------------------------------------------------------------------


def _mapped_cfg(tmp_path) -> util.PackageConfig:
    return {"config_files": [{"src": "config/app.conf", "dst": str(tmp_path / "home" / "app.conf")}]}


def _unit(tmp_path) -> deploy.Managed:
    """A MANAGED_FILE destination, as tasks/proxy.py builds one for the systemd --user unit."""
    return deploy.Managed(
        path=tmp_path / "home" / "app.conf",
        package="px-proxy",
        source="config/app.conf",
        mechanism=deploy.Mechanism.MANAGED_FILE,
    )


@pytest.fixture
def no_prompt(monkeypatch):
    """An install run must never prompt — it is reached from `inv setup`, where there is nobody to
    answer."""
    monkeypatch.setattr(util, "confirm", lambda *a, **k: pytest.fail("an install run must never prompt"))


def test_apply_seeds_a_missing_config_files_destination(tmp_path, src, no_prompt):
    deploy.apply_config_files("app", _mapped_cfg(tmp_path))

    dst = tmp_path / "home" / "app.conf"
    assert dst.read_text() == "new content\n"
    assert deploy.load_manifest()[str(dst)]["mechanism"] == "config-file"


def test_apply_reports_and_keeps_a_customized_config_files_destination(tmp_path, src, no_prompt, capsys):
    deploy.apply_config_files("app", _mapped_cfg(tmp_path))
    dst = tmp_path / "home" / "app.conf"
    dst.write_text("customized by the user\n")

    deploy.apply_config_files("app", _mapped_cfg(tmp_path))

    assert dst.read_text() == "customized by the user\n"
    assert "yours to own" in capsys.readouterr().out


def test_apply_keeps_a_pre_existing_config_files_destination_it_never_wrote(tmp_path, src, no_prompt, capsys):
    # A machine where the file already existed before PULSE ever ran: no manifest entry, content
    # differs. Seeded policy — it's the user's, leave it and say so.
    dst = tmp_path / "home" / "app.conf"
    dst.parent.mkdir()
    dst.write_text("was here first\n")

    deploy.apply_config_files("app", _mapped_cfg(tmp_path))

    assert dst.read_text() == "was here first\n"
    assert "yours to own" in capsys.readouterr().out


def test_apply_refreshes_an_untouched_destination_when_the_source_changes(tmp_path, src, no_prompt):
    deploy.apply_config_files("app", _mapped_cfg(tmp_path))
    src.write_text("new content v2\n")

    deploy.apply_config_files("app", _mapped_cfg(tmp_path))

    assert (tmp_path / "home" / "app.conf").read_text() == "new content v2\n"


def test_apply_with_no_mappings_is_a_no_op(tmp_path, src, no_prompt):
    deploy.apply_config_files("app", {"method": "apt"})

    assert not deploy._MANIFEST.exists()


def test_a_managed_file_destination_is_managed_not_seeded(tmp_path):
    assert _unit(tmp_path).policy == deploy.Policy.MANAGED


def test_a_managed_file_is_copied_verbatim_and_left_non_executable(tmp_path, src):
    """The whole reason this mechanism exists: `wrapper-script` was the only MANAGED whole-file
    shape and it chmods 0755, which is wrong for a systemd unit."""
    src.write_text("[Unit]\nDescription=x\n\n")

    deploy.deploy(_unit(tmp_path))

    dst = tmp_path / "home" / "app.conf"
    assert dst.read_bytes() == b"[Unit]\nDescription=x\n\n"
    assert not dst.stat().st_mode & 0o111


def test_an_edited_managed_file_is_reported_not_accepted(tmp_path, src, monkeypatch, capsys):
    monkeypatch.setattr(util, "confirm", lambda *a, **k: False)
    deploy.deploy(_unit(tmp_path))
    dst = tmp_path / "home" / "app.conf"
    dst.write_text("hand-edited\n")

    deploy.deploy(_unit(tmp_path))

    # Opposite of the config_files case above: the edit is drift, shown as a diff, not "yours".
    out = capsys.readouterr().out
    assert "edited since PULSE deployed it" in out
    assert "yours to own" not in out
    assert dst.read_text() == "hand-edited\n"


def test_yes_overwrites_a_customized_seeded_destination(tmp_path, src):
    """`--yes` is the documented way to take the repo's version back — all_()'s docstring says a
    customized config_files destination is "left alone unless --yes", and the message the SEEDED
    branch prints names that exact command. It returned before ever reading the flag, so the
    command it told you to run did nothing."""
    m = _managed(tmp_path)
    deploy.deploy(m)
    dest = tmp_path / "home" / "app.conf"
    dest.write_text("customized by the user\n")

    assert deploy.deploy(m, assume_yes=True) == deploy.Action.UPDATED
    assert dest.read_text() == "new content\n"


def test_a_customized_seeded_destination_is_still_left_alone_without_yes(tmp_path, src):
    m = _managed(tmp_path)
    deploy.deploy(m)
    dest = tmp_path / "home" / "app.conf"
    dest.write_text("customized by the user\n")

    assert deploy.deploy(m) == deploy.Action.LEFT_ALONE
    assert dest.read_text() == "customized by the user\n"


# ---------------------------------------------------------------------------
# symlink_dest, deployed by deploy.all rather than only by tools.install
# ---------------------------------------------------------------------------


def test_deploy_all_creates_a_packages_symlink_dests(tmp_path, monkeypatch, capsys):
    """`inv deploy.all` is the documented way to link a newly-installed agent in, and until
    2026-09-04 it wrote content and no links at all — the only writer was `tools.install`, which
    re-runs every installer for every package."""
    dest = tmp_path / "home" / ".agents" / "AGENTS.md"
    vendor = tmp_path / "home" / ".claude" / "CLAUDE.md"
    vendor.parent.mkdir(parents=True)
    (tmp_path / "config").mkdir(exist_ok=True)
    (tmp_path / "config" / "agents.md").write_text("rules\n")
    monkeypatch.setattr(deploy, "_REPO_ROOT", tmp_path)
    _stub_config(
        monkeypatch,
        {
            "agents-md": {
                "method": "wrapper-script",
                "dest": str(dest),
                "content_file": "config/agents.md",
                "symlink_dest": [str(vendor)],
            }
        },
    )

    deploy.all_(MockContext(), name="agents-md", yes=True)

    assert dest.read_text() == "rules\n"
    assert vendor.is_symlink()
    assert vendor.resolve() == dest.resolve()


def test_deploy_all_creates_an_always_link_whose_parent_is_missing(tmp_path, monkeypatch):
    """The `~/AGENTS.md` compatibility link: no vendor owns it, so its parent is created."""
    dest = tmp_path / "home" / ".agents" / "AGENTS.md"
    compat = tmp_path / "home" / "AGENTS.md"
    (tmp_path / "config").mkdir(exist_ok=True)
    (tmp_path / "config" / "agents.md").write_text("rules\n")
    monkeypatch.setattr(deploy, "_REPO_ROOT", tmp_path)
    _stub_config(
        monkeypatch,
        {
            "agents-md": {
                "method": "wrapper-script",
                "dest": str(dest),
                "content_file": "config/agents.md",
                "symlink_dest": [{"path": str(compat), "always": True}],
            }
        },
    )

    deploy.all_(MockContext(), name="agents-md", yes=True)

    assert compat.is_symlink()
    assert compat.resolve() == dest.resolve()


def test_deploy_all_writes_no_link_under_dry_run(tmp_path, monkeypatch, capsys):
    """`PULSE_DRY_RUN=1` reports without writing — the link half has to honour that too, and it
    has to *report*: returning early made a machine that would gain three links print
    `1 path(s): 1 created` and nothing else, which understates the real run in the one output
    someone reads before deciding to trust it."""
    dest = tmp_path / "home" / ".agents" / "AGENTS.md"
    compat = tmp_path / "home" / "AGENTS.md"
    (tmp_path / "config").mkdir(exist_ok=True)
    (tmp_path / "config" / "agents.md").write_text("rules\n")
    monkeypatch.setattr(deploy, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(util, "DRY_RUN", True)
    _stub_config(
        monkeypatch,
        {
            "agents-md": {
                "method": "wrapper-script",
                "dest": str(dest),
                "content_file": "config/agents.md",
                "symlink_dest": [{"path": str(compat), "always": True}],
            }
        },
    )

    deploy.all_(MockContext(), name="agents-md", yes=True)

    assert not compat.exists()
    assert not compat.is_symlink()
    assert f"{compat}: would symlink -> {dest}" in capsys.readouterr().out


def test_dry_run_names_the_agent_it_would_skip(tmp_path, monkeypatch, capsys):
    """The uninstalled-agent case is the one a reader most needs distinguished from a failure."""
    dest = tmp_path / "home" / ".agents" / "AGENTS.md"
    vendor = tmp_path / "home" / ".codex" / "AGENTS.md"
    (tmp_path / "config").mkdir(exist_ok=True)
    (tmp_path / "config" / "agents.md").write_text("rules\n")
    monkeypatch.setattr(deploy, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(util, "DRY_RUN", True)
    _stub_config(
        monkeypatch,
        {
            "agents-md": {
                "method": "wrapper-script",
                "dest": str(dest),
                "content_file": "config/agents.md",
                "symlink_dest": [str(vendor)],
            }
        },
    )

    deploy.all_(MockContext(), name="agents-md", yes=True)

    assert "would skip" in capsys.readouterr().out
    assert not vendor.parent.exists()
