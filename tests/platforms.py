"""Platform skip marks shared by the test suite.

PULSE administers Linux machines, and only a slice of it runs on native Windows (deploying the
agent instructions and skills, see plans/2026-09-07-agents-md-and-skills-on-native-windows.md). A
test that exercises a Linux-only mechanism says so with one of these marks, and its reason names the
mechanism, so a Windows run reports what it skipped rather than failing on what cannot exist there.
"""

import sys

import pytest

IS_WINDOWS = sys.platform == "win32"


def posix_only(reason: str) -> pytest.MarkDecorator:
    """Skip on native Windows; `reason` names the POSIX mechanism the test needs."""
    return pytest.mark.skipif(IS_WINDOWS, reason=f"POSIX-only: {reason}")


def needs_symlinks() -> pytest.MarkDecorator:
    """Skip where this process cannot create a symlink (Windows without Developer Mode or admin)."""
    return pytest.mark.skipif(not _can_symlink(), reason="cannot create symlinks here")


def _can_symlink() -> bool:
    if not IS_WINDOWS:
        return True
    import tempfile  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

    with tempfile.TemporaryDirectory() as tmp:
        try:
            (Path(tmp) / "link").symlink_to(Path(tmp) / "target")
        except OSError:
            return False
    return True
