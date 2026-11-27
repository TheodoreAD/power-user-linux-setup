"""Unit tests for tasks/herdr.py's install_mods — what it copies, what it leaves alone, and which
edits it makes to a fresh copy only.

The commands it runs (git clone, go run, git apply, herdr-app check) are recorded rather than run:
each needs the network or a Herdr install. A clone is simulated by laying out the folders the task
reads from, so the copying itself is real and happens under tmp_path, never in the home directory.
"""

import json
from pathlib import Path
from typing import cast, override

import pytest
from invoke import Context, Result
from invoke.exceptions import Exit

from tasks import deploy, herdr


class _Recorder(Context):
    """Records every command; `git clone` lays out the mod folders the task copies from."""

    def __init__(self, mods_dir: Path) -> None:
        super().__init__()
        self.commands: list[str] = []
        self.envs: list[dict[str, str]] = []
        self._mods_dir: Path = mods_dir

    @override
    def run(self, command: str, **kwargs: object) -> Result:
        self.commands.append(command)
        env = kwargs.get("env")
        self.envs.append(env if isinstance(env, dict) else {})
        words = command.split()
        if words[:2] == ["git", "clone"]:
            clone = Path(words[-1])
            source = next(s for s in herdr._SOURCES if s.repo == words[-2])
            for path in source.mods:
                (clone / path).mkdir(parents=True)
                (clone / path / "mod.json").write_text('{"title": "upstream"}\n', encoding="utf-8")
        if words[:2] == ["go", "-C"]:
            (self._mods_dir / "branch-pr").mkdir()
        return Result(command=command, exited=0)


@pytest.fixture
def app_home(tmp_path, monkeypatch) -> Path:
    home = tmp_path / "herdr-app"
    (home / "mods").mkdir(parents=True)
    monkeypatch.setattr(herdr, "APP_HOME", home)
    monkeypatch.setattr(herdr, "MODS_DIR", home / "mods")
    monkeypatch.setattr(deploy, "_MANIFEST", tmp_path / "state" / "deployed.json")
    return home


def test_install_mods_refuses_before_the_app_has_created_its_folder(tmp_path, monkeypatch):
    """The mods folder appears on Herdr's first start; installing into a folder the app has not
    made yet would put mods where a later first start may not expect them."""
    monkeypatch.setattr(herdr, "MODS_DIR", tmp_path / "missing" / "mods")

    with pytest.raises(Exit, match="start Herdr once"):
        herdr.install_mods(_Recorder(tmp_path))


def test_install_mods_copies_every_mod_and_seeds_the_layout(app_home):
    context = _Recorder(app_home / "mods")

    herdr.install_mods(context)

    assert sorted(p.name for p in (app_home / "mods").iterdir()) == sorted(herdr.mod_names())
    assert (app_home / "layouts" / "estro.json").is_file()
    assert (app_home / "layouts" / "estro-issues.svg").is_file()
    assert [c for c in context.commands if c.startswith("herdr-app check")] == [
        f"herdr-app check {app_home / 'mods' / name}" for name in herdr.mod_names()
    ]


def test_install_mods_clones_each_source_at_its_reviewed_commit(app_home):
    """A pin is what was security-reviewed; a branch head is code nobody has read."""
    context = _Recorder(app_home / "mods")

    herdr.install_mods(context)

    for source in herdr._SOURCES:
        assert any(c.startswith("git -C") and c.endswith(f"checkout --quiet {source.commit}") for c in context.commands)


def test_install_mods_leaves_an_existing_mod_and_its_edits_alone(app_home):
    """Never replace a mod that is there: it may carry the person's own settings or changes."""
    for name in ("better-tabs", "better-changes", "branch-pr"):
        (app_home / "mods" / name).mkdir()
        (app_home / "mods" / name / "mine").write_text("kept\n", encoding="utf-8")
    context = _Recorder(app_home / "mods")

    herdr.install_mods(context)

    for name in ("better-tabs", "better-changes", "branch-pr"):
        assert sorted(p.name for p in (app_home / "mods" / name).iterdir()) == ["mine"]
    assert not any(c.startswith("go -C") for c in context.commands)
    assert not any(" apply " in c for c in context.commands)


def test_install_mods_patches_and_limits_only_a_fresh_copy(app_home):
    context = _Recorder(app_home / "mods")

    herdr.install_mods(context)

    applies = [i for i, c in enumerate(context.commands) if " apply " in c]
    assert len(applies) == 1
    assert context.envs[applies[0]] == {"GIT_CEILING_DIRECTORIES": str(app_home / "mods")}
    manifest = cast(object, json.loads((app_home / "mods" / "better-changes" / "mod.json").read_text(encoding="utf-8")))
    assert manifest == {"title": "upstream", "settings": {"limits": {"files": 100}}}


def test_install_mods_builds_branch_pr_with_the_local_go_toolchain_only(app_home):
    """GOTOOLCHAIN=local keeps `go run` from downloading a toolchain nobody installed."""
    context = _Recorder(app_home / "mods")

    herdr.install_mods(context)

    builds = [i for i, c in enumerate(context.commands) if c.startswith("go -C")]
    assert len(builds) == 1
    assert context.commands[builds[0]].endswith("branch-pr/helper run ./install")
    assert context.envs[builds[0]] == {"GOTOOLCHAIN": "local"}


def test_the_patch_and_layout_sources_are_in_the_repo():
    assert (herdr._REPO_ROOT / herdr._PATCH).is_file()
    for managed in herdr.managed_files():
        assert managed.src.is_file()
