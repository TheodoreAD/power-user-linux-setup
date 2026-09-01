"""Unit tests for tasks/apt.py's failure handling — the part that decides whether one unavailable
package ends a whole setup run.

The context is plans/2026-08-31-wsl-and-container-first-run-experience.md's deferred item: a single
`apt-get install` returning non-zero used to abort install_base at that package, leaving every later
one uninstalled. The fix has two halves that pull against each other, and both are asserted here —
failures are *tolerated* per package so the run finishes, and then *fatal* in one summary so nothing
is silently swallowed.

The Context is faked rather than mocked loosely: _FakeContext raises UnexpectedExit for a non-zero
command that wasn't passed `warn=True`, exactly as invoke's real runner does. That is what makes a
missing `warn=True` fail these tests instead of passing them — it was a missing `warn=True` that
caused the abort in the first place. See tests/README.md.
"""

from collections.abc import Sequence
from typing import override

import pytest
from invoke import Context, Exit, Result, UnexpectedExit

from tasks import apt, deploy, util


class _FakeContext(Context):
    """Records commands instead of running them; fails any whose text contains a `fail` fragment.

    Mirrors invoke's own contract on the one point these tests turn on: a non-zero exit raises
    unless the caller passed warn=True.
    """

    def __init__(self, fail: Sequence[str] = ()) -> None:
        super().__init__()
        self.commands: list[str] = []
        self._fail: tuple[str, ...] = tuple(fail)

    @override
    def run(self, command: str, **kwargs: object) -> Result:
        self.commands.append(command)
        exited = 1 if any(fragment in command for fragment in self._fail) else 0
        result = Result(command=command, exited=exited)
        if exited and not kwargs.get("warn"):
            raise UnexpectedExit(result)
        return result

    def installs(self) -> list[str]:
        return [cmd for cmd in self.commands if "apt-get" in cmd and " install -y " in cmd]


@pytest.fixture(autouse=True)
def _live_mode(monkeypatch):
    monkeypatch.setattr(util, "DRY_RUN", False)


# ---------------------------------------------------------------------------
# _install_batch — one call normally, one call per package once that fails
# ---------------------------------------------------------------------------


def test_install_batch_makes_one_call_and_reports_nothing_when_it_works():
    c = _FakeContext()

    assert apt._install_batch(c, "pkg", ["a", "b", "c"]) == []
    assert len(c.installs()) == 1


def test_install_batch_retries_individually_and_blames_only_the_bad_package():
    # apt-get resolves the whole command line before installing anything, so the batch call
    # installs neither "a" nor "c" — without the retry they would be lost to "b"'s unavailability.
    c = _FakeContext(fail=["b"])

    assert apt._install_batch(c, "pkg", ["a", "b", "c"]) == ["b"]
    assert c.installs() == [
        util.apt_command("install -y a b c"),
        util.apt_command("install -y a"),
        util.apt_command("install -y b"),
        util.apt_command("install -y c"),
    ]


def test_install_batch_does_not_retry_a_single_package():
    """The retry exists to separate a bad package from its batch-mates; one package has none."""
    c = _FakeContext(fail=["only"])

    assert apt._install_batch(c, "pkg", ["only"]) == ["only"]
    assert len(c.installs()) == 1


def test_install_batch_reports_every_package_when_all_of_them_fail():
    c = _FakeContext(fail=["apt-get"])

    assert apt._install_batch(c, "pkg", ["a", "b"]) == ["a", "b"]


# ---------------------------------------------------------------------------
# _report_failures — quiet on success, fatal otherwise
# ---------------------------------------------------------------------------


def test_report_failures_returns_quietly_when_nothing_failed():
    assert apt._report_failures("apt.install-base", {}) is None


def test_report_failures_raises_once_naming_every_section_and_package():
    with pytest.raises(Exit) as excinfo:
        apt._report_failures("apt.install-base", {"two": ["c"], "one": ["a", "b"]})

    message = str(excinfo.value)
    assert "3 package(s)" in message
    # Sorted, so the summary reads the same way on every run rather than in dict order.
    assert message.index("[one] a, b") < message.index("[two] c")


# ---------------------------------------------------------------------------
# install_base — the abort this whole section exists to prevent
# ---------------------------------------------------------------------------


@pytest.fixture
def _stub_apt(monkeypatch):
    """Nothing installed, no sudo, no apt requirement, no config_files deploys."""
    monkeypatch.setattr(util, "ensure_sudo", lambda: None)
    monkeypatch.setattr(util, "require_apt", lambda: None)
    monkeypatch.setattr(util, "apt_installed", lambda _pkg: False)
    monkeypatch.setattr(deploy, "apply_config_files", lambda _name, _cfg: None)


def _packages(monkeypatch, method: util.PackageMethod, pkgs: dict[str, util.PackageConfig]) -> None:
    monkeypatch.setattr(
        util,
        "packages_by_method",
        lambda m, _pkgs=pkgs, _method=method: dict(_pkgs) if m == _method else {},
    )


@pytest.mark.usefixtures("_stub_apt")
def test_install_base_installs_later_packages_after_an_earlier_one_fails(monkeypatch):
    """The regression itself: "gone" used to end the run, and "last" was never reached."""
    _packages(monkeypatch, util.PackageMethod.APT, {"first": {}, "gone": {}, "last": {}})
    c = _FakeContext(fail=["gone"])

    with pytest.raises(Exit):
        apt.install_base(c)

    assert util.apt_command("install -y first") in c.installs()
    assert util.apt_command("install -y last") in c.installs()


@pytest.mark.usefixtures("_stub_apt")
def test_install_base_still_fails_the_run_and_names_what_it_could_not_install(monkeypatch):
    """Tolerating the package is not the same as tolerating the outcome — `warn=True` everywhere
    would have made this run exit 0 with the failure buried in its output."""
    _packages(monkeypatch, util.PackageMethod.APT, {"first": {}, "gone": {}})

    with pytest.raises(Exit) as excinfo:
        apt.install_base(_FakeContext(fail=["gone"]))

    assert "[gone] gone" in str(excinfo.value)


@pytest.mark.usefixtures("_stub_apt")
def test_install_base_is_silent_when_every_package_installs(monkeypatch):
    _packages(monkeypatch, util.PackageMethod.APT, {"first": {}, "second": {}})

    apt.install_base(_FakeContext())  # no Exit raised


# ---------------------------------------------------------------------------
# _register_repo — "no apt update needed" and "registration failed" are different answers
# ---------------------------------------------------------------------------


def _repo_cfg(tmp_path) -> util.PackageConfig:
    return {
        "gpg_path": str(tmp_path / "key.gpg"),
        "gpg_url": "https://example.invalid/key.asc",
        "sources_path": str(tmp_path / "src.list"),
        "sources_entry": "deb [signed-by={gpg_path}] https://example.invalid {codename} main",
    }


def test_register_repo_reports_failure_when_the_key_cannot_be_fetched(tmp_path):
    needs_update, ok = apt._register_repo(_FakeContext(fail=["key.asc"]), "r", _repo_cfg(tmp_path), "noble")

    assert (needs_update, ok) == (False, False)


def test_register_repo_reports_success_and_an_update_when_it_writes_both(tmp_path):
    needs_update, ok = apt._register_repo(_FakeContext(), "r", _repo_cfg(tmp_path), "noble")

    assert (needs_update, ok) == (True, True)


@pytest.mark.usefixtures("_stub_apt")
def test_install_repos_skips_packages_of_a_repo_that_never_registered(monkeypatch, tmp_path):
    """Phase 2 would only ask apt for a package no source provides — and the old code, which read
    the same `False` as "already registered", did exactly that."""
    _packages(monkeypatch, util.PackageMethod.APT_REPO, {"broken": _repo_cfg(tmp_path)})
    monkeypatch.setattr(util, "command_exists", lambda _cmd: True)
    c = _FakeContext(fail=["key.asc"])

    with pytest.raises(Exit) as excinfo:
        apt.install_repos(c)

    assert c.installs() == []
    assert "[broken] broken" in str(excinfo.value)
