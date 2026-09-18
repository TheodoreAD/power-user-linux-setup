"""Unit tests for tasks/selfupdate.py — `inv self.update` / `spowse self.update`.

Two things are worth pinning here and neither is the happy path. The **refusals** are invisible to
the reader the task is written for (a consumer's checkout is never dirty and never ahead) and are
the only thing standing between this command and a working tree another parallel session is holding
— so they are asserted by what the task did *not* run, not by what it printed. And the
**reinstall notice** covers a gap that is silent in the other direction: an editable install serves
pulled code immediately through its `.pth`, but its resolved dependency set was fixed when
`uv tool install` ran, so a newly declared dependency is simply absent with nothing to say so.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import override

import pytest
from invoke import Context, Result, UnexpectedExit

from tasks import selfupdate, ui, util


class _FakeContext(Context):
    """Answers git with canned stdout instead of running it, on invoke's own non-zero contract.

    A fragment mapping to a list is consumed one entry per call, which is how `rev-parse HEAD`
    returns a different commit before and after the pull; the last entry then repeats.
    """

    def __init__(self, outputs: Mapping[str, str | list[str]] | None = None, fail: Sequence[str] = ()) -> None:
        super().__init__()
        self.commands: list[str] = []
        self._outputs: dict[str, list[str]] = {
            key: list(value) if isinstance(value, list) else [value] for key, value in (outputs or {}).items()
        }
        self._fail: tuple[str, ...] = tuple(fail)

    @override
    def run(self, command: str, **kwargs: object) -> Result:
        self.commands.append(command)
        stdout = ""
        for fragment, values in self._outputs.items():
            if fragment in command:
                stdout = values.pop(0) if len(values) > 1 else values[0]
                break
        exited = 1 if any(fragment in command for fragment in self._fail) else 0
        result = Result(command=command, exited=exited, stdout=stdout)
        if exited and not kwargs.get("warn"):
            raise UnexpectedExit(result)
        return result

    def ran(self, fragment: str) -> bool:
        return any(fragment in command for command in self.commands)


@pytest.fixture
def checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A directory that passes the "is this a clone" check, standing in for the real one."""
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(selfupdate, "_REPO_ROOT", tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
def _live_and_unattended(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(util, "DRY_RUN", False)
    monkeypatch.setattr(util, "ASSUME_YES", False)
    # Nothing here may reach the real `inv setup`; each test that cares asserts on this list.
    monkeypatch.setattr(selfupdate.setup, "setup", lambda _c: _ran_setup.append(True))
    _ran_setup.clear()


_ran_setup: list[bool] = []


def _consumer_clone(before: str = "a" * 40, after: str = "b" * 40, changed: str = "") -> _FakeContext:
    """The shape `install.sh` produces: clean, detached at a tag, so no upstream to be ahead of."""
    return _FakeContext(
        {
            "status --porcelain": "",
            "rev-parse --abbrev-ref": "",
            "rev-parse HEAD": [before, after],
            "diff --name-only": changed,
        }
    )


def test_a_dirty_checkout_refuses_and_never_pulls(checkout: Path):
    context = _FakeContext({"status --porcelain": " M tasks/util.py"})
    selfupdate.update(context)
    assert not context.ran("pull")


def test_a_checkout_ahead_of_its_upstream_refuses_and_never_pulls(checkout: Path):
    context = _FakeContext({"rev-parse --abbrev-ref": "origin/master", "rev-list --count": "2"})
    selfupdate.update(context)
    assert not context.ran("pull")


def test_a_detached_checkout_has_no_upstream_and_is_not_blocked_by_that(checkout: Path):
    """install.sh clones --branch stable, so HEAD sits on a tag and `@{u}` fails. Nothing can be
    ahead of an upstream that does not exist, and reading that failure as a block would refuse to
    update every machine installed the documented way."""
    context = _consumer_clone()
    selfupdate.update(context)
    assert context.ran("pull --ff-only")


def test_a_checkout_level_with_its_upstream_is_not_blocked(checkout: Path):
    context = _FakeContext(
        {
            "rev-parse --abbrev-ref": "origin/master",
            "rev-list --count": "0",
            "rev-parse HEAD": ["a" * 40, "b" * 40],
        }
    )
    selfupdate.update(context)
    assert context.ran("pull --ff-only")


def test_a_directory_that_is_not_a_clone_is_refused_with_a_sentence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(selfupdate, "_REPO_ROOT", tmp_path)
    context = _FakeContext()
    with pytest.raises(SystemExit) as excinfo:
        selfupdate.update(context)
    assert "install.sh" in str(excinfo.value)
    assert context.commands == []


def test_a_non_fast_forward_stops_without_guessing_and_names_the_recovery(checkout: Path):
    """The local checks already proved there is nothing local to merge, so a refused fast-forward
    means the published ref moved somewhere this history does not lead — a decision, not a conflict
    to resolve on somebody's behalf."""
    context = _FakeContext({"status --porcelain": "", "rev-parse --abbrev-ref": ""}, fail=["pull --ff-only"])
    with pytest.raises(SystemExit) as excinfo:
        selfupdate.update(context)
    assert "fetch origin --tags --force" in str(excinfo.value)


def test_an_unchanged_head_reports_up_to_date_and_does_not_offer_setup(checkout: Path, capsys):
    context = _consumer_clone(before="a" * 40, after="a" * 40)
    selfupdate.update(context)
    assert "already up to date" in capsys.readouterr().out
    assert _ran_setup == []


def test_a_pulled_pyproject_change_names_the_reinstall_command(checkout: Path, capsys):
    context = _consumer_clone(changed="pyproject.toml\ntasks/util.py")
    selfupdate.update(context)
    assert "python.install-tools" in capsys.readouterr().out


def test_a_pulled_lock_change_names_it_too(checkout: Path, capsys):
    context = _consumer_clone(changed="uv.lock")
    selfupdate.update(context)
    assert "python.install-tools" in capsys.readouterr().out


def test_a_code_only_pull_does_not_name_the_reinstall_command(checkout: Path, capsys):
    """The editable install serves new code with no reinstall, so saying otherwise would train the
    reader to ignore the notice on the one pull where it matters."""
    context = _consumer_clone(changed="tasks/util.py\ndocs/index.md")
    selfupdate.update(context)
    assert "python.install-tools" not in capsys.readouterr().out


def test_setup_after_no_pulls_and_stops(checkout: Path):
    selfupdate.update(_consumer_clone(), setup_after="no")
    assert _ran_setup == []


def test_setup_after_yes_runs_setup_without_asking(checkout: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(ui, "ask", lambda *_args, **_kwargs: pytest.fail("should not have asked"))
    selfupdate.update(_consumer_clone(), setup_after="yes")
    assert _ran_setup == [True]


def test_a_declined_prompt_leaves_the_machine_alone(checkout: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(util, "interactive", lambda: True)
    monkeypatch.setattr(ui, "ask", lambda *_args, **_kwargs: False)
    selfupdate.update(_consumer_clone())
    assert _ran_setup == []


def test_an_accepted_prompt_runs_setup(checkout: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(util, "interactive", lambda: True)
    monkeypatch.setattr(ui, "ask", lambda *_args, **_kwargs: True)
    selfupdate.update(_consumer_clone())
    assert _ran_setup == [True]


def test_nothing_is_offered_where_there_is_nobody_to_ask(checkout: Path):
    """Piped, scripted, CI or a dry run: pull, say what to run next, and change nothing else."""
    selfupdate.update(_consumer_clone())
    assert _ran_setup == []


def test_a_dry_run_reports_without_pulling(checkout: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(util, "DRY_RUN", True)
    context = _consumer_clone()
    selfupdate.update(context)
    assert not context.ran("pull")


def test_an_unknown_setup_after_is_refused_rather_than_treated_as_no(checkout: Path):
    context = _FakeContext()
    with pytest.raises(SystemExit):
        selfupdate.update(context, setup_after="maybe")
    assert context.commands == []
