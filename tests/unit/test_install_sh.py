"""Unit tests for install.sh — the one-line clone-and-install entry point.

Hermetic, per tests/README.md: no network and nothing outside `tmp_path`. That is possible because
every branch worth pinning here happens *before* anything is downloaded — the argument parsing, the
adopt-or-refuse decision, and the refusal to run `inv setup` with no terminal to ask on. The clone
is exercised against a real git repo built in `tmp_path`, which uses the `git` binary this repo
already requires but reaches no remote.

What is deliberately **not** here is the real `bootstrap.sh`: it downloads uv and a Python, which is
neither hermetic nor fast. Every checkout below ships a stub that only echoes, and CI's
`install-smoke` job is what runs the real one end to end.
"""

import subprocess
from pathlib import Path

import pytest

_INSTALL_SH = Path(__file__).parents[2] / "install.sh"

_STUB_BOOTSTRAP = "#!/usr/bin/env bash\necho '[stub bootstrap.sh ran]'\n"


def _write_checkout(root: Path) -> Path:
    """The three things install.sh looks for when deciding whether a directory is a checkout."""
    root.mkdir(parents=True, exist_ok=True)
    (root / ".git").mkdir(exist_ok=True)
    (root / "setup.toml").write_text("")
    (root / "bootstrap.sh").write_text(_STUB_BOOTSTRAP)
    return root


def _run(*args: str, home: Path, stdin: int = subprocess.DEVNULL) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(_INSTALL_SH), *args],
        capture_output=True,
        text=True,
        stdin=stdin,
        env={"HOME": str(home), "PATH": "/usr/bin:/bin:/usr/local/bin"},
        timeout=120,
        check=False,
    )


@pytest.fixture
def home(tmp_path: Path) -> Path:
    """A fake HOME. install.sh defaults its clone directory under it and exports a PATH from it, so
    a test that forgot `--dir` would otherwise write into the real home — see tests/README.md."""
    h = tmp_path / "home"
    h.mkdir()
    return h


def test_help_prints_the_options_and_exits_zero(home: Path):
    """The header comment is the help text, stripped of its `#`. A line-range `sed` would drift as
    the block grows; this asserts the awk that replaced it still finds the whole block."""
    result = _run("--help", home=home)
    assert result.returncode == 0
    for option in ("--dir", "--ref", "--repo-url", "--exclude-tags", "--bootstrap-only", "--yes"):
        assert option in result.stdout, option
    assert "Never `curl … | bash`" in result.stdout


def test_an_unknown_option_is_refused_rather_than_ignored(home: Path):
    result = _run("--nope", home=home)
    assert result.returncode == 1
    assert "--nope" in result.stderr


def test_a_directory_that_is_not_a_checkout_is_refused_untouched(home: Path, tmp_path: Path):
    """The container bootstrap `rm -rf`s its clone target. This one must not: the path is the user's
    to name, and a typo pointing at real work would otherwise delete it."""
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "important.txt").write_text("do not delete me")

    result = _run("--dir", str(occupied), home=home)

    assert result.returncode == 1
    assert "not a power-user-linux-setup checkout" in result.stderr
    assert (occupied / "important.txt").read_text() == "do not delete me"


def test_an_existing_checkout_is_adopted_exactly_as_it_stands(home: Path, tmp_path: Path):
    """Not fetched and not switched to the requested ref — a fetch-and-checkout over somebody's
    uncommitted work is a clobber wearing a git command."""
    checkout = _write_checkout(tmp_path / "existing")
    sentinel = checkout / "uncommitted.txt"
    sentinel.write_text("work in progress")

    result = _run("--dir", str(checkout), "--bootstrap-only", home=home)

    assert result.returncode == 0
    assert "Left exactly as it is" in result.stdout
    assert "[stub bootstrap.sh ran]" in result.stdout
    assert sentinel.read_text() == "work in progress"


def test_the_checkout_is_permanent_and_the_script_says_so(home: Path, tmp_path: Path):
    """This message is the only warning a user gets before moving the directory later breaks
    `spowse` with a bare `No module named 'tasks'`."""
    checkout = _write_checkout(tmp_path / "existing")
    result = _run("--dir", str(checkout), "--bootstrap-only", home=home)
    assert "Keep it there" in result.stdout
    assert str(checkout) in result.stdout


def test_exclude_tags_reaches_the_command_the_user_is_told_to_run(home: Path, tmp_path: Path):
    checkout = _write_checkout(tmp_path / "existing")
    result = _run("--dir", str(checkout), "--bootstrap-only", "--exclude-tags", "gui,gnome", home=home)
    assert "PULSE_EXCLUDE_TAGS=gui,gnome inv setup" in result.stdout


def test_no_terminal_and_no_yes_refuses_instead_of_running_setup(home: Path, tmp_path: Path):
    """The case a `curl … | bash` lands in. Running a full machine setup unattended *because* the
    question could not be shown is the silent default this script exists to avoid, so it exits 1."""
    checkout = _write_checkout(tmp_path / "existing")

    result = _run("--dir", str(checkout), home=home)

    assert result.returncode == 1
    assert "no terminal on stdin" in result.stderr
    assert "inv setup" in result.stderr  # the command to finish by hand


def _make_origin(root: Path) -> Path:
    """A real git repo in tmp_path, so the clone branch is covered without reaching a remote."""
    _write_checkout(root)
    git = ["git", "-c", "user.email=t@example.invalid", "-c", "user.name=Test", "-C", str(root)]
    subprocess.run([*git[:-2], "init", "-b", "trunk", str(root)], check=True, capture_output=True)
    subprocess.run([*git, "add", "-A"], check=True, capture_output=True)
    subprocess.run([*git, "commit", "-m", "stub"], check=True, capture_output=True)
    return root


def test_a_missing_directory_is_cloned_from_the_given_repo_url(home: Path, tmp_path: Path):
    """`--repo-url` is what lets CI install the commit under test rather than what is published;
    here it is what keeps the clone local."""
    origin = _make_origin(tmp_path / "origin")
    target = tmp_path / "nested" / "clone"

    result = _run(
        "--dir",
        str(target),
        "--repo-url",
        str(origin),
        "--ref",
        "trunk",
        "--bootstrap-only",
        home=home,
    )

    assert result.returncode == 0, result.stderr
    assert (target / "setup.toml").is_file()
    assert (target / ".git").is_dir()
    # The parent did not exist either — the script creates it rather than failing on `git clone`.
    assert "[stub bootstrap.sh ran]" in result.stdout


def test_running_it_twice_adopts_rather_than_failing(home: Path, tmp_path: Path):
    """Re-running a pasted line is the most likely thing a person does after it goes wrong once."""
    origin = _make_origin(tmp_path / "origin")
    target = tmp_path / "clone"
    args = ("--dir", str(target), "--repo-url", str(origin), "--ref", "trunk", "--bootstrap-only")

    first = _run(*args, home=home)
    second = _run(*args, home=home)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert "Cloning" in first.stdout
    assert "Left exactly as it is" in second.stdout
