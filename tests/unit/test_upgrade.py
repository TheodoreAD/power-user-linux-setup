"""Unit tests for tasks/upgrade.py — `inv upgrade`.

The one thing worth pinning is order: the `skills` CLI is upgraded before the skills it updates, so
the second step never runs on the CLI the first one was about to replace.
"""

import pytest
from invoke import Context

from tasks import ai, node, setup, upgrade


def test_the_cli_is_upgraded_before_the_skills_it_updates():
    assert (node.update_globals, ai.update_skills) == upgrade.UPGRADE_STEPS


def test_upgrade_runs_every_step_in_order(monkeypatch: pytest.MonkeyPatch):
    ran: list[str] = []
    monkeypatch.setattr(upgrade, "UPGRADE_STEPS", (lambda _c: ran.append("globals"), lambda _c: ran.append("skills")))

    upgrade.upgrade(Context())

    assert ran == ["globals", "skills"]


def test_setup_never_upgrades():
    """The whole reason the command exists separately: setup reproduces, upgrade takes upstream."""
    assert not set(upgrade.UPGRADE_STEPS) & set(setup.PACKAGES_PHASE)
