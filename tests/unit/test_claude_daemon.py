"""Unit tests for tasks/claude_daemon.py's pure halves: reading a fake `/proc`, telling the daemon,
its jobs and its spares apart, the staleness decision, and the notice text. The argv fixtures are
the real bytes read from a running 2.1.283 daemon and its children on 2026-09-28. Showing the
notification and stopping the daemon shell out and are not covered here. See tests/README.md.
"""

import ast
import os
import subprocess
import sys
import time
from pathlib import Path

from tasks import claude_daemon
from tasks.claude_daemon import (
    Proc,
    Stale,
    find_stale,
    is_daemon,
    job_session,
    notice,
    parse_busctl_timestamp,
    processes,
    read_proc,
    supports_stop,
)

_REPO_ROOT = Path(__file__).parent.parent.parent
_HZ = os.sysconf("SC_CLK_TCK")
_BTIME = 1_790_000_000


def _cmdline(*argv: str) -> bytes:
    """NUL-separated and NUL-terminated, as /proc stores it. Joined rather than written as one
    literal, because `b"\\0133"` is an octal escape and silently eats the digits after it."""
    return b"".join(arg.encode() + b"\x00" for arg in argv)


# Real cmdlines. The pty host retitles itself, so its first element is "claude bg-pty-host" with a
# space in it.
_VERSION = "/home/u/.local/share/claude/versions/2.1.283"
_DAEMON_ARGV = _cmdline(
    "/home/u/.local/bin/claude", "daemon", "run", "--json-path", "/home/u/.claude/daemon.json", "--origin", "transient"
)
_JOB_ARGV = _cmdline(
    "claude bg-pty-host",
    "--bg-pty-host",
    "/tmp/cc-daemon-1000/65b1707a/pty/76d98521.sock",
    "133",
    "35",
    "--",
    _VERSION,
    "--session-id",
    "76d98521-8e7c-4524-bb4f-4caeb36e8cb0",
    "--fork-session",
    "--resume",
    "/home/u/.claude/projects/p/e317394d.jsonl",
)
_SPARE_ARGV = _cmdline(
    "claude bg-pty-host",
    "--bg-pty-host",
    "/tmp/cc-daemon-1000/65b1707a/spare/459a120a.pty.sock",
    "200",
    "50",
    "--",
    _VERSION,
    "--bg-spare",
    "/tmp/cc-daemon-1000/65b1707a/spare/459a120a.claim.sock",
)


def _write_proc(root: Path, pid: int, ppid: int, start_ticks: int, argv: bytes, comm: str = "claude") -> None:
    pid_dir = root / str(pid)
    pid_dir.mkdir()
    # 20 fields after the comm: state, ppid, then filler up to starttime at index 19.
    after = ["S", str(ppid), *["0"] * 17, str(start_ticks)]
    (pid_dir / "stat").write_text(f"{pid} ({comm}) {' '.join(after)} 0 0\n")
    (pid_dir / "cmdline").write_bytes(argv)


def _fake_proc(tmp_path: Path) -> Path:
    (tmp_path / "stat").write_text(f"cpu  1 2 3\nbtime {_BTIME}\nprocesses 9\n")
    return tmp_path


def _at(seconds_after_boot: int) -> float:
    return _BTIME + seconds_after_boot


def test_read_proc_counts_fields_from_the_last_paren(tmp_path):
    # A comm can hold spaces and a closing paren, so splitting on the first ")" misreads every field.
    proc = _fake_proc(tmp_path)
    _write_proc(proc, 42, 7, start_ticks=100 * _HZ, argv=_DAEMON_ARGV, comm="odd) name")
    entry = read_proc(proc / "42", _BTIME, _HZ)
    assert entry is not None
    assert (entry.pid, entry.ppid, entry.started) == (42, 7, _at(100))
    assert entry.argv[:3] == ("/home/u/.local/bin/claude", "daemon", "run")


def test_read_proc_of_a_vanished_process_is_none(tmp_path):
    assert read_proc(tmp_path / "999", _BTIME, _HZ) is None


def test_processes_keeps_only_this_users(tmp_path):
    proc = _fake_proc(tmp_path)
    _write_proc(proc, 42, 1, start_ticks=_HZ, argv=_DAEMON_ARGV)
    (proc / "self").mkdir()  # non-numeric entries are skipped
    assert [p.pid for p in processes(proc)] == [42]
    assert processes(proc, uid=os.getuid() + 1) == []


def test_is_daemon_is_the_supervisor_and_not_a_status_query():
    assert is_daemon(Proc(1, 0, ("/x/claude", "daemon", "run", "--json-path", "j"), 0))
    assert not is_daemon(Proc(1, 0, ("/x/claude", "daemon", "status"), 0))
    assert not is_daemon(Proc(1, 0, ("/x/other", "daemon", "run"), 0))


def test_job_session_reads_a_retitled_pty_host(tmp_path):
    proc = _fake_proc(tmp_path)
    _write_proc(proc, 50, 42, start_ticks=_HZ, argv=_JOB_ARGV)
    _write_proc(proc, 51, 42, start_ticks=_HZ, argv=_SPARE_ARGV)
    job, spare = (read_proc(proc / pid, _BTIME, _HZ) for pid in ("50", "51"))
    assert job is not None
    assert spare is not None
    assert job_session(job) == "76d98521-8e7c-4524-bb4f-4caeb36e8cb0"
    assert job_session(spare) is None


def test_find_stale_counts_jobs_and_not_spares(tmp_path):
    proc = _fake_proc(tmp_path)
    _write_proc(proc, 42, 1, start_ticks=100 * _HZ, argv=_DAEMON_ARGV)
    _write_proc(proc, 50, 42, start_ticks=200 * _HZ, argv=_JOB_ARGV)
    _write_proc(proc, 51, 42, start_ticks=200 * _HZ, argv=_SPARE_ARGV)
    _write_proc(proc, 60, 99, start_ticks=200 * _HZ, argv=_JOB_ARGV)  # another daemon's job
    [stale] = find_stale(processes(proc), login_started=_at(150))
    assert stale.daemon.pid == 42
    assert stale.jobs == ("76d98521-8e7c-4524-bb4f-4caeb36e8cb0",)


def test_a_daemon_started_after_the_login_is_not_stale(tmp_path):
    # The fresh daemon a new login starts within seconds must never be flagged.
    proc = _fake_proc(tmp_path)
    _write_proc(proc, 42, 1, start_ticks=160 * _HZ, argv=_DAEMON_ARGV)
    assert find_stale(processes(proc), login_started=_at(150)) == []


def test_parse_busctl_timestamp():
    assert parse_busctl_timestamp("t 1790543046989562\n") == 1790543046.989562
    assert parse_busctl_timestamp("t 0") is None
    assert parse_busctl_timestamp('s "x"') is None
    assert parse_busctl_timestamp("") is None


def test_supports_stop_needs_both_the_subcommand_and_the_flag():
    help_text = "  stop    Shut down the supervisor\n            --any    also stop a transient (non-service) daemon"
    assert supports_stop(help_text)
    assert not supports_stop("  stop              Shut down the supervisor")


def _stale(jobs: tuple[str, ...]) -> Stale:
    started = time.mktime((2026, 9, 26, 11, 49, 0, 0, 0, -1))
    return Stale(daemon=Proc(42, 1, ("/x/claude", "daemon", "run"), started), jobs=jobs)


def test_notice_names_the_start_numerically_and_the_cost_of_stopping():
    summary, body = notice(_stale(("a",)))
    assert "previous login" in summary
    assert "2026-09-26 11:49" in body
    assert "1 background job." in body
    assert "ends that job" in body


def test_notice_with_only_spares_says_nothing_is_lost():
    _, body = notice(_stale(()))
    assert "no background jobs" in body
    assert "Nothing is lost" in body


def test_notice_pluralises():
    _, body = notice(_stale(("a", "b")))
    assert "2 background jobs." in body
    assert "ends those jobs" in body


class _FakeRun:
    """Stands in for subprocess.run: records every argv, answers --help and notify-send."""

    def __init__(self, action: str):
        self.action: str = action
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        self.calls.append(argv)
        if argv[1:] == ["daemon", "--help"]:
            return subprocess.CompletedProcess(argv, 0, "  stop  Shut down\n    --any  also transient", "")
        return subprocess.CompletedProcess(argv, 0, self.action if argv[0] == "notify-send" else "", "")


def test_the_offer_stays_on_screen_and_leave_it_stops_nothing(monkeypatch):
    fake = _FakeRun("keep")
    monkeypatch.setattr(subprocess, "run", fake)
    claude_daemon.offer_stop(_stale(("a",)), login=0)
    [offer] = [argv for argv in fake.calls if argv[0] == "notify-send"]
    assert offer[offer.index("-u") + 1] == "critical"
    assert "stop=Stop it (ends 1 job)" in offer
    assert not any("stop" in argv[1:3] for argv in fake.calls if argv[0] == "/x/claude")


def test_claude_daemon_imports_only_the_standard_library():
    """It runs from an autostart entry on the desktop's own `python3`, with no venv behind it."""
    tree = ast.parse((_REPO_ROOT / "tasks" / "claude_daemon.py").read_text())
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "a relative import would pull in tasks/__init__.py, and invoke with it"
            if node.module:
                imported.add(node.module.split(".")[0])
    assert imported <= set(sys.stdlib_module_names), sorted(imported - set(sys.stdlib_module_names))
