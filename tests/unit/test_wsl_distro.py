"""Unit tests for tasks/wsl_distro.py's pure parts and its refusals. Nothing here calls wsl.exe: the
installer itself was exercised against a real throwaway distro on Windows (see the module docstring).
See tests/README.md.
"""

import sys

import pytest
from invoke import Exit, MockContext

from tasks import wsl_distro


@pytest.mark.parametrize(
    ("text", "expected"),
    [("500GB", 500 * 1024**3), ("1TB", 1024**4), ("300G", 300 * 1024**3), (" 40gb ", 40 * 1024**3)],
)
def test_size_strings_are_binary_units(text, expected):
    assert wsl_distro.size_bytes(text) == expected


def test_a_size_without_a_unit_is_refused_by_name():
    with pytest.raises(Exit, match="--vhd-size"):
        wsl_distro.size_bytes("500")


def test_installing_the_default_image_needs_no_name():
    assert wsl_distro.install_command("Ubuntu-24.04", "Ubuntu-24.04", "500GB") == [
        "--install",
        "Ubuntu-24.04",
        "--no-launch",
        "--vhd-size",
        "500GB",
    ]


def test_a_side_by_side_distro_is_installed_under_its_own_name():
    # The point of --name: a throwaway copy of the same image beside the one holding real work.
    assert wsl_distro.install_command("Ubuntu-24.04", "pulse-test", "40GB") == [
        "--install",
        "Ubuntu-24.04",
        "--name",
        "pulse-test",
        "--no-launch",
        "--vhd-size",
        "40GB",
    ]


@pytest.mark.parametrize("task", [wsl_distro.install, wsl_distro.check])
def test_every_task_refuses_off_windows(monkeypatch, task):
    monkeypatch.setattr(sys, "platform", "linux")
    with pytest.raises(Exit, match="Windows host"):
        task(MockContext())


def test_remove_refuses_the_default_distro_without_force(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(wsl_distro, "registered", lambda: ["Ubuntu-24.04"])
    monkeypatch.setattr(
        wsl_distro,
        "_registration",
        lambda _name: wsl_distro._Registration(key="k", default_uid=1000, run_oobe=0, base_path=None, is_default=True),
    )
    monkeypatch.setattr(wsl_distro, "_wsl", lambda *a, **k: pytest.fail(f"ran wsl {a}"))

    with pytest.raises(Exit, match="--force"):
        wsl_distro.remove(MockContext(), name="Ubuntu-24.04", yes=True)


def test_remove_of_an_absent_distro_does_nothing(monkeypatch, capsys):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(wsl_distro, "registered", lambda: [])
    monkeypatch.setattr(wsl_distro, "_wsl", lambda *a, **k: pytest.fail(f"ran wsl {a}"))

    wsl_distro.remove(MockContext(), name="pulse-test", yes=True)

    assert "nothing to remove" in capsys.readouterr().out
