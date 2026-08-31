"""Unit tests for tasks/ai.py's skill-installation logic: the pure helpers
(_parse_frontmatter_description, _local_skill_plan, _remote_skill_label, _remote_skill_prompt),
plus the confirm/-y behavior of _install_local_skill/_install_remote_skill/_install_declared_skills
and the skills task itself — exercised with tmp_path fixtures and monkeypatched ui.ask/c.run/
util.load_config rather than any real system call, same shape as tests/unit/test_phases.py. See
tests/README.md.
"""

import json
import shutil
from pathlib import Path

import pytest
from invoke import Context, MockContext, Result
from typing_extensions import override  # typing.override is 3.12+; this repo's floor is 3.11

from tasks import ai, deploy, ui, util


@pytest.fixture(autouse=True)
def _reset_dry_run():
    saved = util.DRY_RUN
    util.DRY_RUN = False
    yield
    util.DRY_RUN = saved


@pytest.fixture(autouse=True)
def _isolated_deploy_manifest(tmp_path, monkeypatch):
    """_install_local_skill writes through tasks/deploy.py, which records into the deploy manifest
    — never the real one under ~/.local/state, and never with PULSE_ASSUME_YES leaking in from
    the environment the suite runs under."""
    monkeypatch.setattr(deploy, "_MANIFEST", tmp_path / "state" / "deployed.json")
    monkeypatch.setattr(util, "ASSUME_YES", False)


def _fail_if_asked(message):
    def fail_if_asked(*a, **k):
        raise AssertionError(message)

    return fail_if_asked


class _FakeContext(Context):
    """A Context that records the shell commands _install_remote_skill would have run, never
    executing anything. A real subclass (not a duck-typed stand-in) so it satisfies the
    `c: Context` annotation the helpers declare; invoke's own MockContext would raise on any
    command it wasn't pre-loaded with, and the commands are what these tests assert on."""

    def __init__(self) -> None:
        super().__init__()
        self.commands: list[str] = []

    @override
    def run(self, command: str, **kwargs: object) -> Result:
        self.commands.append(command)
        return Result()


# ---------------------------------------------------------------------------
# _parse_frontmatter_description — pure string parsing, no filesystem
# ---------------------------------------------------------------------------


def test_parse_frontmatter_description_extracts_value():
    text = '---\nname: foo\ndescription: "Use when doing X."\n---\nbody\n'
    assert ai._parse_frontmatter_description(text) == "Use when doing X."


def test_parse_frontmatter_description_unquoted_value():
    text = "---\ndescription: no quotes here\n---\n"
    assert ai._parse_frontmatter_description(text) == "no quotes here"


def test_parse_frontmatter_description_no_frontmatter():
    assert ai._parse_frontmatter_description("# just a heading\n") is None


def test_parse_frontmatter_description_no_description_key():
    assert ai._parse_frontmatter_description("---\nname: foo\n---\n") is None


def test_parse_frontmatter_description_empty_text():
    assert ai._parse_frontmatter_description("") is None


def test_parse_frontmatter_description_stops_at_closing_marker():
    # A `description:`-looking line in the body (after the closing ---) must not match.
    text = "---\nname: foo\n---\ndescription: not frontmatter\n"
    assert ai._parse_frontmatter_description(text) is None


def test_skill_frontmatter_description_reads_real_file(tmp_path):
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text('---\ndescription: "hello"\n---\n')
    assert ai._skill_frontmatter_description(skill_md) == "hello"


def test_skill_frontmatter_description_missing_file(tmp_path):
    assert ai._skill_frontmatter_description(tmp_path / "nope.md") is None


# ---------------------------------------------------------------------------
# _local_skill_plan — pure decision table
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("present", "ours", "state", "expected"),
    [
        (False, False, deploy.State.ABSENT, "install"),
        (True, False, deploy.State.UNKNOWN, "foreign"),
        (True, False, deploy.State.CLEAN, "foreign"),  # foreign wins even if a digest happened to match
        (True, True, deploy.State.STALE, "update"),
        (True, True, deploy.State.UNKNOWN, "update"),  # ours by marker, no manifest entry yet
        (True, True, deploy.State.DIRTY, "overwrite"),
        (True, True, deploy.State.CLEAN, "up_to_date"),
    ],
)
def test_local_skill_plan(present, ours, state, expected):
    assert ai._local_skill_plan(present=present, ours=ours, state=state) == expected


# ---------------------------------------------------------------------------
# _remote_skill_label / _remote_skill_prompt — pure string building
# ---------------------------------------------------------------------------


def test_remote_skill_label_with_names():
    assert ai._remote_skill_label(["a", "b"], "owner/repo") == "a, b from owner/repo"


def test_remote_skill_label_without_names():
    assert ai._remote_skill_label(None, "owner/repo") == "all skills from owner/repo"


def test_remote_skill_prompt_includes_description():
    assert ai._remote_skill_prompt("x from y", "does things") == "Install x from y?\ndoes things"


def test_remote_skill_prompt_no_description():
    assert ai._remote_skill_prompt("x from y", None) == "Install x from y?"


# ---------------------------------------------------------------------------
# _install_local_skill — confirm/-y behavior against a real tmp_path tree
# ---------------------------------------------------------------------------


def _make_src_skill(repo_root: Path, rel_path: str, *, description: str = "desc") -> Path:
    src = repo_root / rel_path
    src.mkdir(parents=True)
    (src / "SKILL.md").write_text(f'---\nname: {src.name}\ndescription: "{description}"\n---\nbody\n')
    return src


def test_install_local_skill_asks_before_first_install(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    _make_src_skill(repo_root, "skills/foo", description="Do the thing.")
    monkeypatch.setattr(deploy, "_REPO_ROOT", repo_root)
    base = tmp_path / "home"

    asked = {}

    def fake_ask(question, default=True):
        asked["question"] = question
        return True

    monkeypatch.setattr(ui, "ask", fake_ask)

    ai._install_local_skill(base, "skills/foo", label="test", yes=False)

    assert "Install skill 'foo'?" in asked["question"]
    assert "Do the thing." in asked["question"]
    assert (base / ".agents" / "skills" / "foo" / "SKILL.md").exists()


def test_install_local_skill_declining_prompt_skips_install(tmp_path, monkeypatch, capsys):
    repo_root = tmp_path / "repo"
    _make_src_skill(repo_root, "skills/foo")
    monkeypatch.setattr(deploy, "_REPO_ROOT", repo_root)
    base = tmp_path / "home"
    monkeypatch.setattr(ui, "ask", lambda *a, **k: False)

    ai._install_local_skill(base, "skills/foo", label="test", yes=False)

    assert not (base / ".agents" / "skills" / "foo").exists()
    assert "skipped (declined)" in capsys.readouterr().out


def test_install_local_skill_raises_when_copy_doesnt_match_source(tmp_path, monkeypatch):
    # The exact gap this check exists to catch: copytree "succeeds" (no exception) but what
    # actually landed on disk doesn't match the source — simulated via a real digest mismatch
    # (corrupting one file post-copy) rather than mocking _dir_digest, so the comparison itself is
    # exercised for real.
    repo_root = tmp_path / "repo"
    src = _make_src_skill(repo_root, "skills/foo")
    monkeypatch.setattr(deploy, "_REPO_ROOT", repo_root)
    monkeypatch.setattr(ui, "ask", lambda *a, **k: True)
    base = tmp_path / "home"

    real_copytree = shutil.copytree

    def corrupting_copytree(s, d, *args, **kwargs):
        result = real_copytree(s, d, *args, **kwargs)
        (Path(d) / "SKILL.md").write_text("corrupted during copy")
        return result

    monkeypatch.setattr(shutil, "copytree", corrupting_copytree)

    with pytest.raises(RuntimeError, match="doesn't match"):
        ai._install_local_skill(base, "skills/foo", label="test", yes=False)

    assert src.exists()  # source untouched by the corruption


def test_install_local_skill_records_the_copy_in_the_deploy_manifest(tmp_path, monkeypatch):
    # Without this, `inv deploy.status`/`deploy.all` reported every skill as "not deployed by
    # PULSE" — the marker said whose it was, but nothing said what PULSE had written.
    repo_root = tmp_path / "repo"
    src = _make_src_skill(repo_root, "skills/foo")
    monkeypatch.setattr(deploy, "_REPO_ROOT", repo_root)
    base = tmp_path / "home"

    ai._install_local_skill(base, "skills/foo", label="pkg", yes=True)

    entry = deploy.load_manifest()[str(base / ".agents" / "skills" / "foo")]
    assert entry["package"] == "pkg"
    assert entry["source"] == "skills/foo"
    assert entry["mechanism"] == "skill"
    assert entry["digest"] == deploy.dir_digest(src)


def test_install_local_skill_yes_skips_prompt(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    _make_src_skill(repo_root, "skills/foo")
    monkeypatch.setattr(deploy, "_REPO_ROOT", repo_root)
    base = tmp_path / "home"
    monkeypatch.setattr(ui, "ask", _fail_if_asked("yes=True must never prompt"))

    ai._install_local_skill(base, "skills/foo", label="test", yes=True)

    assert (base / ".agents" / "skills" / "foo" / "SKILL.md").exists()


def test_install_local_skill_update_uses_update_verb(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    _make_src_skill(repo_root, "skills/foo")
    monkeypatch.setattr(deploy, "_REPO_ROOT", repo_root)
    base = tmp_path / "home"
    monkeypatch.setattr(ui, "ask", lambda *a, **k: True)

    ai._install_local_skill(base, "skills/foo", label="test", yes=True)  # first install, quiet
    # change the source so the next run sees it as stale, not up to date
    (repo_root / "skills" / "foo" / "SKILL.md").write_text('---\nname: foo\ndescription: "changed"\n---\nbody\n')

    asked = {}

    def fake_ask(question, default=True):
        asked["question"] = question
        return True

    monkeypatch.setattr(ui, "ask", fake_ask)
    ai._install_local_skill(base, "skills/foo", label="test", yes=False)

    assert asked["question"].startswith("Update skill 'foo'?")


def test_install_local_skill_already_up_to_date_never_prompts(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    _make_src_skill(repo_root, "skills/foo")
    monkeypatch.setattr(deploy, "_REPO_ROOT", repo_root)
    base = tmp_path / "home"
    monkeypatch.setattr(ui, "ask", lambda *a, **k: True)
    ai._install_local_skill(base, "skills/foo", label="test", yes=True)  # first install

    monkeypatch.setattr(ui, "ask", _fail_if_asked("an unchanged, up-to-date skill must never prompt"))
    ai._install_local_skill(base, "skills/foo", label="test", yes=False)


def test_install_local_skill_edited_copy_asks_before_overwriting_and_defaults_to_no(tmp_path, monkeypatch):
    # A skill PULSE installed, then edited under ~/.agents/skills/ — the content exists only there.
    # The prompt has to say so and default to keeping it; declining leaves the edit in place.
    repo_root = tmp_path / "repo"
    _make_src_skill(repo_root, "skills/foo")
    monkeypatch.setattr(deploy, "_REPO_ROOT", repo_root)
    base = tmp_path / "home"
    ai._install_local_skill(base, "skills/foo", label="test", yes=True)
    deployed_md = base / ".agents" / "skills" / "foo" / "SKILL.md"
    deployed_md.write_text("edited at the destination\n")

    asked = {}

    def fake_ask(question, default=True):
        asked["question"], asked["default"] = question, default
        return default

    monkeypatch.setattr(ui, "ask", fake_ask)
    ai._install_local_skill(base, "skills/foo", label="test", yes=False)

    assert asked["question"].startswith("Overwrite skill 'foo'?")
    assert asked["default"] is False
    assert deployed_md.read_text() == "edited at the destination\n"


def test_install_local_skill_yes_overwrites_an_edited_copy_without_a_second_prompt(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    _make_src_skill(repo_root, "skills/foo")
    monkeypatch.setattr(deploy, "_REPO_ROOT", repo_root)
    base = tmp_path / "home"
    ai._install_local_skill(base, "skills/foo", label="test", yes=True)
    deployed_md = base / ".agents" / "skills" / "foo" / "SKILL.md"
    deployed_md.write_text("edited at the destination\n")
    monkeypatch.setattr(ui, "ask", _fail_if_asked("yes=True must never prompt"))
    monkeypatch.setattr(util, "confirm", _fail_if_asked("deploy() must not ask again after this task's own prompt"))

    ai._install_local_skill(base, "skills/foo", label="test", yes=True)

    assert "edited at the destination" not in deployed_md.read_text()


def test_install_local_skill_foreign_content_never_prompts_and_is_untouched(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    _make_src_skill(repo_root, "skills/foo")
    monkeypatch.setattr(deploy, "_REPO_ROOT", repo_root)
    base = tmp_path / "home"
    dest = base / ".agents" / "skills" / "foo"
    dest.mkdir(parents=True)
    (dest / "unrelated.txt").write_text("someone else's content")
    monkeypatch.setattr(ui, "ask", _fail_if_asked("foreign content must never prompt"))

    ai._install_local_skill(base, "skills/foo", label="test", yes=False)

    assert (dest / "unrelated.txt").read_text() == "someone else's content"


def test_install_local_skill_dry_run_never_prompts_or_writes(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    _make_src_skill(repo_root, "skills/foo")
    monkeypatch.setattr(deploy, "_REPO_ROOT", repo_root)
    base = tmp_path / "home"
    monkeypatch.setattr(ui, "ask", _fail_if_asked("dry run must never prompt"))
    util.DRY_RUN = True

    ai._install_local_skill(base, "skills/foo", label="test", yes=False)

    assert not (base / ".agents" / "skills" / "foo").exists()


# ---------------------------------------------------------------------------
# _install_remote_skill — confirm/-y behavior with a fake invoke Context
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _skills_cli_on_path(monkeypatch):
    """`skills` is a global npm package under nvm, so whether a bare call works depends on the
    machine running the tests — it does on the developer's, and doesn't in CI or a container.
    Pin it, so these tests assert on this module's behaviour rather than on the environment.
    The unpinned branches get their own tests below."""
    monkeypatch.setattr(ai.util, "command_exists", lambda name: name == "skills")


def test_install_remote_skill_reaches_the_cli_through_nvm_when_it_is_not_on_path(monkeypatch):
    """The ordinary first-run case: nvm has just installed `skills` globally, and nothing in this
    non-interactive process has sourced nvm.sh, so a bare call would exit 127."""
    c = _FakeContext()
    monkeypatch.setattr(ai.util, "command_exists", lambda name: False)
    monkeypatch.setattr(ai.node, "nvm_command", lambda command: f"bash -c 'nvm && {command}'")
    monkeypatch.setattr(ui, "ask", lambda *a, **k: True)

    ai._install_remote_skill(c, {"repo": "owner/repo"}, label="test", yes=True)

    assert c.commands == ["bash -c 'nvm && skills add owner/repo --global --yes --agent claude-code --skill '*''"]


def test_install_remote_skill_skips_when_the_cli_exists_nowhere(monkeypatch, capsys):
    """Not a crash: a bare `skills` call exited 127 and took a whole unattended container build
    down with it."""
    c = _FakeContext()
    monkeypatch.setattr(ai.util, "command_exists", lambda name: False)
    monkeypatch.setattr(ai.node, "nvm_command", lambda command: None)

    ai._install_remote_skill(c, {"repo": "owner/repo"}, label="test", yes=True)

    assert c.commands == []
    # ui.warn word-wraps, so match on words that survive a line break rather than a phrase.
    printed = capsys.readouterr().out
    assert "skipped" in printed
    assert "inv node.install" in printed


def test_install_remote_skill_asks_before_running_skills_add(monkeypatch):
    c = _FakeContext()
    entry: util.SkillEntry = {"repo": "owner/repo", "names": ["foo"], "description": "Does foo things."}
    asked = {}

    def fake_ask(question, default=True):
        asked["question"] = question
        return True

    monkeypatch.setattr(ui, "ask", fake_ask)

    ai._install_remote_skill(c, entry, label="test", yes=False)

    assert "Does foo things." in asked["question"]
    assert c.commands == ["skills add owner/repo --global --yes --agent claude-code --skill foo"]


def test_install_remote_skill_declining_prompt_skips_command(monkeypatch, capsys):
    c = _FakeContext()
    entry: util.SkillEntry = {"repo": "owner/repo"}
    monkeypatch.setattr(ui, "ask", lambda *a, **k: False)

    ai._install_remote_skill(c, entry, label="test", yes=False)

    assert c.commands == []
    assert "skipped (declined)" in capsys.readouterr().out


def test_install_remote_skill_yes_skips_prompt_and_runs(monkeypatch):
    c = _FakeContext()
    entry: util.SkillEntry = {"repo": "owner/repo"}
    monkeypatch.setattr(ui, "ask", _fail_if_asked("yes=True must never prompt"))

    ai._install_remote_skill(c, entry, label="test", yes=True)

    assert c.commands == ["skills add owner/repo --global --yes --agent claude-code --skill '*'"]


def test_install_remote_skill_dry_run_never_prompts_or_runs(monkeypatch):
    c = _FakeContext()
    entry: util.SkillEntry = {"repo": "owner/repo"}
    monkeypatch.setattr(ui, "ask", _fail_if_asked("dry run must never prompt"))
    util.DRY_RUN = True

    ai._install_remote_skill(c, entry, label="test", yes=False)

    assert c.commands == []


# ---------------------------------------------------------------------------
# --skill selection — pure filtering, no filesystem
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("plan-docs", {"plan-docs"}),
        ("a,b", {"a", "b"}),
        (" a , b ", {"a", "b"}),
        ("a,,b,", {"a", "b"}),
        ("", set()),
    ],
)
def test_selected_skill_names(value, expected):
    assert ai._selected_skill_names(value) == expected


def test_entry_skill_names_local_uses_directory_name():
    assert ai._entry_skill_names({"source": "local", "path": "skills/plan-docs"}) == ["plan-docs"]


def test_entry_skill_names_remote_uses_declared_names():
    assert ai._entry_skill_names({"source": "npx", "repo": "o/r", "names": ["a", "b"]}) == ["a", "b"]


def test_entry_skill_names_remote_without_names_is_unknowable():
    # No `names` means "every skill in that repo" — only the `skills` CLI can enumerate those.
    assert ai._entry_skill_names({"source": "npx", "repo": "o/r"}) is None


def test_select_entry_without_selection_passes_everything_through():
    entry: util.SkillEntry = {"source": "npx", "repo": "o/r"}
    assert ai._select_entry(entry, None) is entry


def test_select_entry_local_match_and_miss():
    entry: util.SkillEntry = {"source": "local", "path": "skills/plan-docs"}
    assert ai._select_entry(entry, {"plan-docs"}) is entry
    assert ai._select_entry(entry, {"something-else"}) is None


def test_select_entry_narrows_remote_names_to_the_requested_ones():
    entry: util.SkillEntry = {"source": "npx", "repo": "o/r", "names": ["a", "b"]}

    assert ai._select_entry(entry, {"a"}) == {"source": "npx", "repo": "o/r", "names": ["a"]}
    # the original entry is not mutated
    assert entry["names"] == ["a", "b"]


def test_select_entry_skips_remote_entry_whose_names_are_unknowable():
    # Installing it on the chance it might contain the named skill would defeat --skill's point.
    assert ai._select_entry({"source": "npx", "repo": "o/r"}, {"a"}) is None


# ---------------------------------------------------------------------------
# _install_declared_skills — dispatch by source, threading `yes` through
# ---------------------------------------------------------------------------


def test_install_declared_skills_dispatches_by_source_and_threads_yes(monkeypatch):
    calls = []
    monkeypatch.setattr(
        ai, "_install_local_skill", lambda base, path, *, label, yes: calls.append(("local", path, label, yes))
    )
    monkeypatch.setattr(
        ai, "_install_remote_skill", lambda c, entry, *, label, yes: calls.append(("npx", entry["repo"], label, yes))
    )
    monkeypatch.setattr(
        util,
        "load_config",
        lambda: {
            "packages": {
                "pkg-a": {"enabled": True, "skills": [{"source": "local", "path": "skills/a"}]},
                "pkg-b": {"enabled": True, "skills": [{"source": "npx", "repo": "o/r"}]},
                "pkg-disabled": {"enabled": False, "skills": [{"source": "local", "path": "skills/c"}]},
                "pkg-no-skills": {"enabled": True},
            }
        },
    )

    ai._install_declared_skills(MockContext(), Path("/base"), yes=True)

    assert calls == [("local", "skills/a", "pkg-a", True), ("npx", "o/r", "pkg-b", True)]


def _stub_two_skill_packages(monkeypatch, calls):
    monkeypatch.setattr(ai, "_install_local_skill", lambda base, path, *, label, yes: calls.append(("local", path)))
    monkeypatch.setattr(
        ai, "_install_remote_skill", lambda c, entry, *, label, yes: calls.append(("npx", entry.get("names")))
    )
    monkeypatch.setattr(
        util,
        "load_config",
        lambda: {
            "packages": {
                "pkg-a": {"enabled": True, "skills": [{"source": "local", "path": "skills/plan-docs"}]},
                "pkg-b": {"enabled": True, "skills": [{"source": "local", "path": "skills/db-defaults"}]},
                "pkg-c": {"enabled": True, "skills": [{"source": "npx", "repo": "o/r", "names": ["a", "b"]}]},
            }
        },
    )


def test_install_declared_skills_selection_installs_only_the_named_skill(monkeypatch):
    calls = []
    _stub_two_skill_packages(monkeypatch, calls)

    ai._install_declared_skills(MockContext(), Path("/base"), yes=True, selected={"plan-docs"})

    assert calls == [("local", "skills/plan-docs")]


def test_install_declared_skills_selection_narrows_a_remote_entrys_names(monkeypatch):
    calls = []
    _stub_two_skill_packages(monkeypatch, calls)

    ai._install_declared_skills(MockContext(), Path("/base"), yes=True, selected={"a"})

    assert calls == [("npx", ["a"])]


def test_install_declared_skills_no_selection_installs_everything(monkeypatch):
    calls = []
    _stub_two_skill_packages(monkeypatch, calls)

    ai._install_declared_skills(MockContext(), Path("/base"), yes=True)

    assert len(calls) == 3


def test_install_declared_skills_unmatched_selection_raises_and_lists_declared(monkeypatch):
    # A typo'd --skill that silently did no work would look exactly like a successful refresh.
    calls = []
    _stub_two_skill_packages(monkeypatch, calls)

    with pytest.raises(ValueError, match="matched no declared skill") as excinfo:
        ai._install_declared_skills(MockContext(), Path("/base"), yes=True, selected={"plan-doc"})

    assert "plan-docs" in str(excinfo.value)
    assert calls == []


def test_install_declared_skills_warns_on_unknown_source(monkeypatch, capsys):
    monkeypatch.setattr(ai, "_install_local_skill", _fail_if_asked("should not install"))
    monkeypatch.setattr(ai, "_install_remote_skill", _fail_if_asked("should not install"))
    monkeypatch.setattr(
        util,
        "load_config",
        lambda: {"packages": {"pkg": {"enabled": True, "skills": [{"source": "weird"}]}}},
    )

    ai._install_declared_skills(MockContext(), Path("/base"), yes=True)

    assert "unknown source" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# skills task — thin orchestration, same shape as tests/unit/test_phases.py
# ---------------------------------------------------------------------------


def _stub_skills_task_helpers(monkeypatch, calls):
    monkeypatch.setattr(ai, "_ensure_agents_skills", lambda base, *, label: calls.append(("ensure", base, label)))
    monkeypatch.setattr(
        ai,
        "_install_declared_skills",
        lambda c, base, *, yes, selected=None: calls.append(("install", base, yes, selected)),
    )
    monkeypatch.setattr(ai, "_apply_static_claude_permissions", lambda: calls.append(("perms",)))
    monkeypatch.setattr(ai, "_apply_additional_directories", lambda: calls.append(("dirs",)))
    monkeypatch.setattr(ai, "_apply_declared_default_mode", lambda: calls.append(("mode",)))
    monkeypatch.setattr(ai, "_apply_declared_statusline", lambda: calls.append(("statusline",)))
    monkeypatch.setattr(ai, "_note_copilot_permissions", lambda: calls.append(("copilot",)))


def test_skills_task_default_dir_applies_permissions_and_threads_yes(monkeypatch):
    # ai.install_skills is @task-wrapped, and invoke's Task.__call__ insists its first arg be a real
    # Context — .body is the plain underlying function, same pattern as calling any other
    # helper directly. MockContext() rather than None: the helpers declare `c: Context`, and a
    # None would be a type error even though every helper here is stubbed out.
    calls = []
    _stub_skills_task_helpers(monkeypatch, calls)

    ai.install_skills.body(MockContext(), yes=True)
    assert ("perms",) in calls
    assert ("dirs",) in calls
    assert ("mode",) in calls
    assert ("statusline",) in calls
    assert ("copilot",) in calls
    assert ("install", Path.home(), True, None) in calls


def test_skills_task_with_dir_skips_permissions_and_copilot(monkeypatch, tmp_path):
    calls = []
    _stub_skills_task_helpers(monkeypatch, calls)

    ai.install_skills.body(MockContext(), dir=str(tmp_path), yes=False)

    assert ("perms",) not in calls
    assert ("dirs",) not in calls
    assert ("mode",) not in calls
    assert ("statusline",) not in calls
    assert ("copilot",) not in calls
    assert ("install", tmp_path, False, None) in calls


def test_skills_task_with_skill_filters_and_skips_global_settings(monkeypatch):
    # Permissions/statusLine/Copilot are global — nothing to do with which skill was named.
    calls = []
    _stub_skills_task_helpers(monkeypatch, calls)

    ai.install_skills.body(MockContext(), yes=True, skill="plan-docs")

    assert ("perms",) not in calls
    assert ("statusline",) not in calls
    assert ("copilot",) not in calls
    assert ("install", Path.home(), True, {"plan-docs"}) in calls


# ---------------------------------------------------------------------------
# _apply_declared_statusline — no manifest, just absent/matches/conflicts
# ---------------------------------------------------------------------------

_DECLARED_STATUSLINE = {"type": "command", "command": "bash ~/.claude/statusline-command.sh"}


def _stub_declared_statusline_package(monkeypatch, value=_DECLARED_STATUSLINE):
    monkeypatch.setattr(
        util,
        "load_config",
        lambda: {"packages": {"claude-statusline": {"enabled": True, "claude_statusline": value}}},
    )


def test_apply_declared_statusline_writes_when_absent(monkeypatch, capsys):
    _stub_declared_statusline_package(monkeypatch)
    monkeypatch.setattr(util, "load_claude_settings", lambda: {})
    written = []
    monkeypatch.setattr(util, "write_claude_settings", written.append)
    monkeypatch.setattr(ui, "ask", _fail_if_asked("no existing value, must never prompt"))

    ai._apply_declared_statusline()

    assert written == [{"statusLine": _DECLARED_STATUSLINE}]
    assert "statusLine updated" in capsys.readouterr().out


def test_apply_declared_statusline_noop_when_already_correct(monkeypatch, capsys):
    _stub_declared_statusline_package(monkeypatch)
    monkeypatch.setattr(util, "load_claude_settings", lambda: {"statusLine": _DECLARED_STATUSLINE})
    monkeypatch.setattr(util, "write_claude_settings", _fail_if_asked("already correct, must never write"))
    monkeypatch.setattr(ui, "ask", _fail_if_asked("already correct, must never prompt"))

    ai._apply_declared_statusline()

    assert "already up to date" in capsys.readouterr().out


def test_apply_declared_statusline_declined_overwrite_leaves_existing(monkeypatch, capsys):
    _stub_declared_statusline_package(monkeypatch)
    existing = {"type": "command", "command": "some-other-script"}
    monkeypatch.setattr(util, "load_claude_settings", lambda: {"statusLine": existing})
    monkeypatch.setattr(util, "write_claude_settings", _fail_if_asked("declined, must never write"))
    monkeypatch.setattr(ui, "ask", lambda *a, **k: False)

    ai._apply_declared_statusline()

    assert "left existing custom value in place" in capsys.readouterr().out


def test_apply_declared_statusline_confirmed_overwrite_writes(monkeypatch, capsys):
    _stub_declared_statusline_package(monkeypatch)
    existing = {"type": "command", "command": "some-other-script"}
    monkeypatch.setattr(util, "load_claude_settings", lambda: {"statusLine": existing, "theme": "dark"})
    written = []
    monkeypatch.setattr(util, "write_claude_settings", written.append)
    monkeypatch.setattr(ui, "ask", lambda *a, **k: True)

    ai._apply_declared_statusline()

    assert written == [{"statusLine": _DECLARED_STATUSLINE, "theme": "dark"}]
    assert "statusLine updated" in capsys.readouterr().out


def test_apply_declared_statusline_dry_run_never_writes_or_prompts(monkeypatch, capsys):
    _stub_declared_statusline_package(monkeypatch)
    monkeypatch.setattr(util, "load_claude_settings", lambda: {"statusLine": {"type": "command", "command": "x"}})
    monkeypatch.setattr(util, "write_claude_settings", _fail_if_asked("dry run must never write"))
    monkeypatch.setattr(ui, "ask", _fail_if_asked("dry run must never prompt"))
    util.DRY_RUN = True

    ai._apply_declared_statusline()

    assert "statusLine" in capsys.readouterr().out


def test_apply_declared_statusline_noop_when_nothing_declared(monkeypatch):
    monkeypatch.setattr(util, "load_config", lambda: {"packages": {}})
    monkeypatch.setattr(util, "load_claude_settings", _fail_if_asked("nothing declared, must never read settings"))
    monkeypatch.setattr(util, "write_claude_settings", _fail_if_asked("nothing declared, must never write"))
    monkeypatch.setattr(ui, "ask", _fail_if_asked("nothing declared, must never prompt"))

    ai._apply_declared_statusline()


# ---------------------------------------------------------------------------
# _apply_additional_directories — manifest-tracked merge, same shape as static permissions
# ---------------------------------------------------------------------------


def _stub_declared_dirs(monkeypatch, tmp_path, dirs):
    monkeypatch.setattr(
        util,
        "load_config",
        lambda: {"packages": {"claude-code": {"enabled": True, "claude_additional_directories": dirs}}},
    )
    monkeypatch.setattr(ai, "_STATIC_DIRS_MANIFEST", tmp_path / "dirs-manifest.json")


def test_apply_additional_directories_writes_expanded_paths_and_manifest(monkeypatch, tmp_path, capsys):
    _stub_declared_dirs(monkeypatch, tmp_path, ["/tmp/claude-1000", "~/.claude/jobs"])
    monkeypatch.setattr(util, "load_claude_settings", lambda: {"permissions": {"allow": ["Bash(ls:*)"]}})
    written = []
    monkeypatch.setattr(util, "write_claude_settings", written.append)

    ai._apply_additional_directories()

    expected = sorted(["/tmp/claude-1000", str(Path.home() / ".claude" / "jobs")])
    assert written == [{"permissions": {"allow": ["Bash(ls:*)"], "additionalDirectories": expected}}]
    assert json.loads((tmp_path / "dirs-manifest.json").read_text()) == expected
    assert "additionalDirectories updated" in capsys.readouterr().out


def test_apply_additional_directories_keeps_hand_added_dir_and_removes_only_ours(monkeypatch, tmp_path):
    _stub_declared_dirs(monkeypatch, tmp_path, ["/tmp/claude-1000"])
    (tmp_path / "dirs-manifest.json").write_text(json.dumps(["/old/ours"]))
    monkeypatch.setattr(
        util,
        "load_claude_settings",
        lambda: {"permissions": {"additionalDirectories": ["/old/ours", "/theirs"]}},
    )
    written = []
    monkeypatch.setattr(util, "write_claude_settings", written.append)

    ai._apply_additional_directories()

    assert written[0]["permissions"]["additionalDirectories"] == ["/theirs", "/tmp/claude-1000"]


def test_apply_additional_directories_noop_when_up_to_date(monkeypatch, tmp_path, capsys):
    _stub_declared_dirs(monkeypatch, tmp_path, ["/tmp/claude-1000"])
    existing = {"permissions": {"additionalDirectories": ["/tmp/claude-1000"]}}
    monkeypatch.setattr(util, "load_claude_settings", lambda: existing)
    monkeypatch.setattr(util, "write_claude_settings", _fail_if_asked("up to date, must never write"))

    ai._apply_additional_directories()

    assert "already up to date" in capsys.readouterr().out


def test_apply_additional_directories_dry_run_never_writes(monkeypatch, tmp_path, capsys):
    _stub_declared_dirs(monkeypatch, tmp_path, ["/tmp/claude-1000"])
    monkeypatch.setattr(util, "load_claude_settings", lambda: {})
    monkeypatch.setattr(util, "write_claude_settings", _fail_if_asked("dry run must never write"))
    util.DRY_RUN = True

    ai._apply_additional_directories()

    assert "MISSING 1" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# _apply_declared_default_mode — scalar, statusline-shaped: absent/matches/conflicts
# ---------------------------------------------------------------------------


def _stub_declared_mode(monkeypatch, value="acceptEdits"):
    monkeypatch.setattr(
        util,
        "load_config",
        lambda: {"packages": {"claude-code": {"enabled": True, "claude_default_mode": value}}},
    )


def test_apply_declared_default_mode_sets_when_absent(monkeypatch, capsys):
    _stub_declared_mode(monkeypatch)
    monkeypatch.setattr(util, "load_claude_settings", lambda: {"permissions": {"allow": []}})
    written = []
    monkeypatch.setattr(util, "write_claude_settings", written.append)
    monkeypatch.setattr(ui, "ask", _fail_if_asked("no existing value, must never prompt"))

    ai._apply_declared_default_mode()

    assert written == [{"permissions": {"allow": [], "defaultMode": "acceptEdits"}}]
    assert "defaultMode set to 'acceptEdits'" in capsys.readouterr().out


def test_apply_declared_default_mode_noop_when_already_correct(monkeypatch, capsys):
    _stub_declared_mode(monkeypatch)
    monkeypatch.setattr(util, "load_claude_settings", lambda: {"permissions": {"defaultMode": "acceptEdits"}})
    monkeypatch.setattr(util, "write_claude_settings", _fail_if_asked("already correct, must never write"))
    monkeypatch.setattr(ui, "ask", _fail_if_asked("already correct, must never prompt"))

    ai._apply_declared_default_mode()

    assert "already up to date" in capsys.readouterr().out


def test_apply_declared_default_mode_declined_overwrite_leaves_existing(monkeypatch, capsys):
    _stub_declared_mode(monkeypatch)
    monkeypatch.setattr(util, "load_claude_settings", lambda: {"permissions": {"defaultMode": "auto"}})
    monkeypatch.setattr(util, "write_claude_settings", _fail_if_asked("declined, must never write"))
    monkeypatch.setattr(ui, "ask", lambda *a, **k: False)

    ai._apply_declared_default_mode()

    assert "left existing value in place" in capsys.readouterr().out


def test_apply_declared_default_mode_confirmed_overwrite_writes(monkeypatch):
    _stub_declared_mode(monkeypatch)
    monkeypatch.setattr(util, "load_claude_settings", lambda: {"permissions": {"defaultMode": "auto"}, "theme": "dark"})
    written = []
    monkeypatch.setattr(util, "write_claude_settings", written.append)
    monkeypatch.setattr(ui, "ask", lambda *a, **k: True)

    ai._apply_declared_default_mode()

    assert written == [{"permissions": {"defaultMode": "acceptEdits"}, "theme": "dark"}]


def test_apply_declared_default_mode_noop_when_nothing_declared(monkeypatch):
    monkeypatch.setattr(util, "load_config", lambda: {"packages": {"claude-code": {"enabled": True}}})
    monkeypatch.setattr(util, "load_claude_settings", _fail_if_asked("nothing declared, must never read settings"))

    ai._apply_declared_default_mode()


# --- ai.check-rule-prerequisites -------------------------------------------------------------
#
# A `[needs direnv]` label on a ~/AGENTS.md rule is a claim that direnv is there. These cover the
# decision itself (_stale_prerequisites is pure) plus the label parsing that feeds it.


def test_stale_prerequisites_is_quiet_when_every_dependency_is_enabled():
    rules = [("bash.md", "Invoking a venv tool", "needs direnv")]
    assert ai._stale_prerequisites(rules, {"direnv"}, {"direnv"}) == []


def test_stale_prerequisites_reports_a_package_that_is_declared_but_disabled():
    """The case the check exists for: someone switches direnv off and the rule keeps asserting it."""
    rules = [("bash.md", "Invoking a venv tool", "needs direnv")]
    (line,) = ai._stale_prerequisites(rules, {"direnv"}, set())
    assert "direnv" in line
    assert "disabled or tag-excluded" in line


def test_stale_prerequisites_reports_a_package_setup_toml_never_declared():
    rules = [("bash.md", "Some rule", "needs nonesuch")]
    (line,) = ai._stale_prerequisites(rules, set(), set())
    assert "does not declare" in line


def test_stale_prerequisites_ignores_labels_that_name_no_package():
    """`[Claude Code]` is a harness label, and `needs setup.toml` names a file — neither is a
    package, and reporting them would make the check cry wolf on every single run."""
    rules = [
        ("bash.md", "Viewing files", "Claude Code"),
        ("research.md", "Installing a tool", "needs setup.toml"),
        ("git.md", "Ssh", "needs PULSE's zprofile"),
    ]
    assert ai._stale_prerequisites(rules, set(), set()) == []


def test_labelled_rules_reads_headings_and_skips_the_readme(tmp_path, monkeypatch):
    frag = tmp_path / "agents-md"
    frag.mkdir()
    (frag / "bash.md").write_text(
        "## Bash & tool use\n\n### Plain rule\n\nBody.\n\n### Labelled rule  [needs direnv]\n\nBody.\n"
    )
    (frag / "README.md").write_text("### Not a rule  [needs direnv]\n")
    monkeypatch.setattr(ai, "_AGENTS_MD_FRAGMENTS", frag)

    assert ai._labelled_rules() == [("bash.md", "Labelled rule", "needs direnv")]
