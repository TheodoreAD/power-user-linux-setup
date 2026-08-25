"""Unit tests for tasks/phases.py — the only part of tasks/*.py that's pure orchestration (no
direct system calls), so it's the only part worth an automated test. See tests/README.md.
"""

import sys
from dataclasses import dataclass, field

import pytest
from invoke import Context, MockContext

from tasks import phases, ui, util


@dataclass
class _StubTask:
    """A stub task callable matching the real convention: prints ok/MISSING depending on
    util.DRY_RUN, and records each call's DRY_RUN value at call time. A real class rather than a
    closure with a bolted-on attribute so `.calls` is a real, typed attribute instead of a
    dynamic addition to a plain function object.
    """

    missing: bool
    calls: list[bool] = field(default_factory=list)

    def __call__(self, c: object) -> None:
        self.calls.append(util.DRY_RUN)
        print(f"[x] {'MISSING' if self.missing else 'ok'}")


def _make_task(missing: bool) -> _StubTask:
    return _StubTask(missing)


@pytest.fixture(autouse=True)
def _reset_dry_run():
    """Every test starts from util.DRY_RUN == False and restores it afterward, regardless of
    what the test (or a bug in the code under test) leaves behind.
    """
    saved = util.DRY_RUN
    util.DRY_RUN = False
    yield
    util.DRY_RUN = saved


def test_probe_captures_output_and_restores_dry_run(capsys):
    ok = _make_task(missing=False)
    output = phases.probe(MockContext(), [ok])
    assert "ok" in output
    assert util.DRY_RUN is False
    assert ok.calls == [True]  # ran once, with DRY_RUN forced on during the probe
    capsys.readouterr()  # probe redirects stdout internally — nothing should leak to the real one


def test_probe_restores_dry_run_on_exception():
    def boom(c: Context) -> None:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        phases.probe(MockContext(), [boom])
    assert util.DRY_RUN is False


def test_run_skips_when_everything_already_ok(monkeypatch, capsys):
    ok = _make_task(missing=False)
    monkeypatch.setattr(ui, "ask", lambda *a, **k: True)  # simulate accepting the skip offer

    phases.run_phase(MockContext(), "shell", [ok])

    assert ok.calls == [True]  # only the probe call — no real (DRY_RUN=False) call followed
    assert "[shell] skipped" in capsys.readouterr().out


def _fail_if_asked(message):
    def fail_if_asked(*a, **k):
        raise AssertionError(message)

    return fail_if_asked


def test_run_does_not_offer_skip_when_something_is_missing(monkeypatch):
    missing = _make_task(missing=True)

    monkeypatch.setattr(ui, "ask", _fail_if_asked("should not ask to skip when a phase has outstanding work"))

    phases.run_phase(MockContext(), "packages", [missing])

    # probe call (DRY_RUN=True) + real call (DRY_RUN=False) — ran unconditionally, no prompt
    assert missing.calls == [True, False]


def test_run_bypasses_skip_logic_under_global_dry_run(monkeypatch):
    ok = _make_task(missing=False)

    monkeypatch.setattr(ui, "ask", _fail_if_asked("PULSE_DRY_RUN=1 must never be gated behind a skip prompt"))
    util.DRY_RUN = True  # simulates PULSE_DRY_RUN=1 inv setup

    phases.run_phase(MockContext(), "packages", [ok])

    # falls straight through to running funcs for real, once, still under DRY_RUN — the full
    # diagnostic report documented in docs/index.md, not a silently skipped phase.
    assert ok.calls == [True]
    assert util.DRY_RUN is True


def test_run_skips_silently_when_noninteractive(monkeypatch, capsys):
    ok = _make_task(missing=False)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)  # piped/scripted/CI

    phases.run_phase(MockContext(), "shell", [ok])

    out = capsys.readouterr().out
    assert ok.calls == [True]
    assert "[shell] skipped" in out
    assert "action needed" not in out  # ui.ask's box never renders outside a real terminal
