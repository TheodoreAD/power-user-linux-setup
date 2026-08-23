"""Unit tests for tasks/ai.py's skill-installation logic: the pure helpers
(_parse_frontmatter_description, _local_skill_plan, _remote_skill_label, _remote_skill_prompt),
plus the confirm/-y behavior of _install_local_skill/_install_remote_skill/_install_declared_skills
and the skills task itself — exercised with tmp_path fixtures and monkeypatched ui.ask/c.run/
util.load_config rather than any real system call, same shape as tests/test_phases.py. See
tests/README.md.
"""

import shutil
from pathlib import Path

import pytest

from tasks import ai, ui, util


@pytest.fixture(autouse=True)
def _reset_dry_run():
    saved = util.DRY_RUN
    util.DRY_RUN = False
    yield
    util.DRY_RUN = saved


def _fail_if_asked(message):
    def fail_if_asked(*a, **k):
        raise AssertionError(message)

    return fail_if_asked


class _FakeContext:
    """Stand-in for invoke's Context — just records the shell commands _install_remote_skill
    would have run, never executes anything."""

    def __init__(self):
        self.commands = []

    def run(self, cmd):
        self.commands.append(cmd)


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
    "present,ours,up_to_date,expected",
    [
        (False, False, False, "install"),
        (True, False, False, "foreign"),
        (True, False, True, "foreign"),  # foreign wins even if a digest happened to match
        (True, True, False, "update"),
        (True, True, True, "up_to_date"),
    ],
)
def test_local_skill_plan(present, ours, up_to_date, expected):
    assert ai._local_skill_plan(present=present, ours=ours, up_to_date=up_to_date) == expected


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
    monkeypatch.setattr(ai, "_REPO_ROOT", repo_root)
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
    monkeypatch.setattr(ai, "_REPO_ROOT", repo_root)
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
    monkeypatch.setattr(ai, "_REPO_ROOT", repo_root)
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


def test_install_local_skill_yes_skips_prompt(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    _make_src_skill(repo_root, "skills/foo")
    monkeypatch.setattr(ai, "_REPO_ROOT", repo_root)
    base = tmp_path / "home"
    monkeypatch.setattr(ui, "ask", _fail_if_asked("yes=True must never prompt"))

    ai._install_local_skill(base, "skills/foo", label="test", yes=True)

    assert (base / ".agents" / "skills" / "foo" / "SKILL.md").exists()


def test_install_local_skill_update_uses_update_verb(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    _make_src_skill(repo_root, "skills/foo")
    monkeypatch.setattr(ai, "_REPO_ROOT", repo_root)
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
    monkeypatch.setattr(ai, "_REPO_ROOT", repo_root)
    base = tmp_path / "home"
    monkeypatch.setattr(ui, "ask", lambda *a, **k: True)
    ai._install_local_skill(base, "skills/foo", label="test", yes=True)  # first install

    monkeypatch.setattr(ui, "ask", _fail_if_asked("an unchanged, up-to-date skill must never prompt"))
    ai._install_local_skill(base, "skills/foo", label="test", yes=False)


def test_install_local_skill_foreign_content_never_prompts_and_is_untouched(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    _make_src_skill(repo_root, "skills/foo")
    monkeypatch.setattr(ai, "_REPO_ROOT", repo_root)
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
    monkeypatch.setattr(ai, "_REPO_ROOT", repo_root)
    base = tmp_path / "home"
    monkeypatch.setattr(ui, "ask", _fail_if_asked("dry run must never prompt"))
    util.DRY_RUN = True

    ai._install_local_skill(base, "skills/foo", label="test", yes=False)

    assert not (base / ".agents" / "skills" / "foo").exists()


# ---------------------------------------------------------------------------
# _install_remote_skill — confirm/-y behavior with a fake invoke Context
# ---------------------------------------------------------------------------


def test_install_remote_skill_asks_before_running_skills_add(monkeypatch):
    c = _FakeContext()
    entry = {"repo": "owner/repo", "names": ["foo"], "description": "Does foo things."}
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
    entry = {"repo": "owner/repo"}
    monkeypatch.setattr(ui, "ask", lambda *a, **k: False)

    ai._install_remote_skill(c, entry, label="test", yes=False)

    assert c.commands == []
    assert "skipped (declined)" in capsys.readouterr().out


def test_install_remote_skill_yes_skips_prompt_and_runs(monkeypatch):
    c = _FakeContext()
    entry = {"repo": "owner/repo"}
    monkeypatch.setattr(ui, "ask", _fail_if_asked("yes=True must never prompt"))

    ai._install_remote_skill(c, entry, label="test", yes=True)

    assert c.commands == ["skills add owner/repo --global --yes --agent claude-code --skill '*'"]


def test_install_remote_skill_dry_run_never_prompts_or_runs(monkeypatch):
    c = _FakeContext()
    entry = {"repo": "owner/repo"}
    monkeypatch.setattr(ui, "ask", _fail_if_asked("dry run must never prompt"))
    util.DRY_RUN = True

    ai._install_remote_skill(c, entry, label="test", yes=False)

    assert c.commands == []


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

    ai._install_declared_skills(None, Path("/base"), yes=True)

    assert calls == [("local", "skills/a", "pkg-a", True), ("npx", "o/r", "pkg-b", True)]


def test_install_declared_skills_warns_on_unknown_source(monkeypatch, capsys):
    monkeypatch.setattr(ai, "_install_local_skill", _fail_if_asked("should not install"))
    monkeypatch.setattr(ai, "_install_remote_skill", _fail_if_asked("should not install"))
    monkeypatch.setattr(
        util,
        "load_config",
        lambda: {"packages": {"pkg": {"enabled": True, "skills": [{"source": "weird"}]}}},
    )

    ai._install_declared_skills(None, Path("/base"), yes=True)

    assert "unknown source" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# skills task — thin orchestration, same shape as tests/test_phases.py
# ---------------------------------------------------------------------------


def _stub_skills_task_helpers(monkeypatch, calls):
    monkeypatch.setattr(ai, "_ensure_agents_skills", lambda base, *, label: calls.append(("ensure", base, label)))
    monkeypatch.setattr(ai, "_install_declared_skills", lambda c, base, *, yes: calls.append(("install", base, yes)))
    monkeypatch.setattr(ai, "_apply_static_claude_permissions", lambda: calls.append(("perms",)))
    monkeypatch.setattr(ai, "_apply_declared_statusline", lambda: calls.append(("statusline",)))
    monkeypatch.setattr(ai, "_note_copilot_permissions", lambda: calls.append(("copilot",)))


def test_skills_task_default_dir_applies_permissions_and_threads_yes(monkeypatch):
    # ai.skills is @task-wrapped, and invoke's Task.__call__ insists its first arg be a real
    # Context — .body is the plain underlying function, same pattern as calling any other
    # helper directly.
    calls = []
    _stub_skills_task_helpers(monkeypatch, calls)

    ai.skills.body(None, yes=True)  # pyright: ignore[reportAny, reportFunctionMemberAccess] — invoke's untyped Task.body

    assert ("perms",) in calls
    assert ("statusline",) in calls
    assert ("copilot",) in calls
    assert any(entry[0] == "install" and entry[2] is True for entry in calls)


def test_skills_task_with_dir_skips_permissions_and_copilot(monkeypatch, tmp_path):
    calls = []
    _stub_skills_task_helpers(monkeypatch, calls)

    ai.skills.body(  # pyright: ignore[reportAny, reportFunctionMemberAccess] — invoke's untyped Task.body
        None, dir=str(tmp_path), yes=False
    )

    assert ("perms",) not in calls
    assert ("statusline",) not in calls
    assert ("copilot",) not in calls
    assert ("install", tmp_path, False) in calls


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
