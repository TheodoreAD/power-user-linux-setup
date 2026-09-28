#!/usr/bin/env python3
"""Notice a Claude Code daemon that outlived the login it was started in, and offer to stop it.

Deployed by `[packages.claude-daemon-notice]` as `~/.local/bin/claude-daemon-notice`, and run once
per graphical login by the autostart entry beside it:

    claude-daemon-notice            # print what it found, change nothing
    claude-daemon-notice --notify   # the same, as a desktop notification with a Stop button

Every background Claude session is a child of one `claude daemon run`, and that daemon survives a
logout: it keeps the old login session alive and hands the environment it copied at start to every
job it spawns afterwards, including jobs started from the new login. Measured 2026-09-28 in
`plans/2026-09-28-claude-daemon-outlives-relogin-with-a-dead-ssh-socket.md`: a daemon from 09-26 was
still serving jobs after a re-login, carrying a dead WezTerm SSH agent link and a `UV_PYTHON` the
dotfiles had dropped nine days earlier. The SSH half is repaired per call by `[packages.ssh]`'s
zshenv snippet; this is the other half, which only a fresh daemon fixes.

**It reports and never stops anything on its own.** The Stop button is the only thing that runs
`claude daemon stop --any`, and that ends the daemon's background jobs mid-command, so it is a
human's click, not a policy. Killing at login was rejected because it cannot tell work left running
on purpose from leftovers.

**"Older than this login" is judged against the graphical session's start, by timestamp.** Both
sides are epoch arithmetic, not parsed dates: the daemon's start from `/proc/<pid>/stat` plus the
boot time, and the session's from logind's `Timestamp` property in microseconds. Asking "does any
daemon exist" instead would flag the fresh one a new login starts within seconds. An SSH or console
login is also a login, which is why the session asked about is the caller's own (`session/auto`),
and the autostart entry is what makes the caller the desktop.

**Standard library only, and it must parse on the distro's own Python** — it runs from an autostart
entry on whatever `python3` the desktop session finds. `test_foreign_python_floor.py` holds the
syntax half. It imports nothing from `tasks/`.

`claude daemon`'s subcommands are Claude Code's own and version-specific. Written against
`WRITTEN_AGAINST` below. Before offering the button it checks that `claude daemon --help` still
lists `stop` and `--any`; if not, the notification only informs, rather than naming a command that
may no longer exist.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import cast

WRITTEN_AGAINST = "2.1.283"
PROC = Path("/proc")
APP_NAME = "Claude Code"


@dataclass(frozen=True)
class Proc:
    """One process, reduced to what the staleness check reads."""

    pid: int
    ppid: int
    argv: tuple[str, ...]
    started: float  # epoch seconds


def boot_time(proc: Path = PROC) -> float:
    """Wall-clock boot time from `/proc/stat`'s `btime` line."""
    for line in (proc / "stat").read_text().splitlines():
        if line.startswith("btime "):
            return float(line.split()[1])
    raise ValueError("no btime line in /proc/stat")


def read_proc(pid_dir: Path, btime: float, hz: int) -> Proc | None:
    """One `/proc/<pid>`, or None when it vanished or cannot be read.

    The command name in `stat` is parenthesised and may itself contain spaces or `)`, so the fields
    are counted from the **last** `)`. After it, the state is index 0, the parent pid index 1 and
    the start time, in clock ticks since boot, index 19.
    """
    try:
        stat = (pid_dir / "stat").read_text()
        raw_argv = (pid_dir / "cmdline").read_bytes()
    except OSError:
        return None
    fields = stat.rsplit(")", 1)[1].split()
    argv = tuple(part.decode(errors="replace") for part in raw_argv.split(b"\0") if part)
    return Proc(pid=int(pid_dir.name), ppid=int(fields[1]), argv=argv, started=btime + int(fields[19]) / hz)


def processes(proc: Path = PROC, uid: int | None = None) -> list[Proc]:
    """Every process owned by `uid` (this user by default)."""
    uid = os.getuid() if uid is None else uid
    btime = boot_time(proc)
    hz = os.sysconf("SC_CLK_TCK")
    found: list[Proc] = []
    for pid_dir in proc.iterdir():
        if not pid_dir.name.isdigit():
            continue
        try:
            if pid_dir.stat().st_uid != uid:
                continue
        except OSError:
            continue
        entry = read_proc(pid_dir, btime, hz)
        if entry is not None:
            found.append(entry)
    return found


def is_daemon(p: Proc) -> bool:
    """`<path>/claude daemon run …` — the supervisor, not a `claude daemon status` asking about it."""
    return len(p.argv) >= 3 and Path(p.argv[0]).name == "claude" and p.argv[1:3] == ("daemon", "run")


def job_session(p: Proc) -> str | None:
    """The session id a background job's pty host is running, or None for a pre-started spare.

    Spares carry `--bg-spare` and no session. A job claims a spare or gets a fresh host, and either
    way its host's argv names `--session-id <uuid>`. Match the `--bg-pty-host` **flag**, never the
    name: the host retitles itself, so its `argv[0]` reads `claude bg-pty-host` as one element, and
    a test for `bg-pty-host` as its own element found no job on a daemon that was running one.
    """
    if "--bg-pty-host" not in p.argv or "--session-id" not in p.argv:
        return None
    index = p.argv.index("--session-id")
    return p.argv[index + 1] if index + 1 < len(p.argv) else None


@dataclass(frozen=True)
class Stale:
    """A daemon started before this login, and the background jobs it is running."""

    daemon: Proc
    jobs: tuple[str, ...]


def find_stale(procs: list[Proc], login_started: float) -> list[Stale]:
    """Each daemon that started before `login_started`, with its jobs' session ids."""
    stale: list[Stale] = []
    for daemon in procs:
        if not is_daemon(daemon) or daemon.started >= login_started:
            continue
        jobs = tuple(sid for p in procs if p.ppid == daemon.pid and (sid := job_session(p)) is not None)
        stale.append(Stale(daemon=daemon, jobs=jobs))
    return stale


def parse_busctl_timestamp(output: str) -> float | None:
    """`t 1790543046989562` (microseconds) into epoch seconds; None for anything else, or zero."""
    parts = output.split()
    if len(parts) != 2 or parts[0] != "t" or not parts[1].isdigit() or int(parts[1]) == 0:
        return None
    return int(parts[1]) / 1_000_000


def login_started() -> float | None:
    """When the caller's own login session began, from logind — None when there is no session."""
    if shutil.which("busctl") is None:
        return None
    result = subprocess.run(
        [
            "busctl",
            "get-property",
            "org.freedesktop.login1",
            "/org/freedesktop/login1/session/auto",
            "org.freedesktop.login1.Session",
            "Timestamp",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return parse_busctl_timestamp(result.stdout) if result.returncode == 0 else None


def supports_stop(help_text: str) -> bool:
    """Whether this Claude Code still has the one command the button runs."""
    return "stop" in help_text and "--any" in help_text


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def notice(stale: Stale) -> tuple[str, str]:
    """The notification's summary and body. Dates are numeric, so the locale cannot change them."""
    started = time.strftime("%Y-%m-%d %H:%M", time.localtime(stale.daemon.started))
    summary = "A Claude daemon from your previous login is still running"
    if stale.jobs:
        running = f"It started {started} and is running {_plural(len(stale.jobs), 'background job')}."
        them = "that job" if len(stale.jobs) == 1 else "those jobs"
        consequence = f"Stopping it ends {them}, so wait for {them} to finish first."
    else:
        running = f"It started {started} and is running no background jobs, only idle spares."
        consequence = "Nothing is lost by stopping it."
    body = (
        f"{running} Every job it starts, including ones from windows opened since you logged in, "
        f"inherits that login's environment, with variables your dotfiles have since changed. "
        f"{consequence} The next background job starts a fresh daemon."
    )
    return summary, body


def _notify(*args: str) -> str:
    """Show a notification and return what it printed: an action name, or nothing."""
    result = subprocess.run(["notify-send", "-a", APP_NAME, *args], capture_output=True, text=True, check=False)
    return result.stdout.strip()


def _notice(*args: str) -> str:
    """The stale-daemon notice itself, at critical urgency so GNOME keeps it on screen until answered.

    At normal urgency the banner hides after a few seconds and waits in the notification list.
    Confirmed 2026-09-28 on the first live run: the user never saw a banner, found the notice later
    in the panel, and clicking its body dismissed it without showing the buttons. Fifteen seconds
    into a login is exactly when nobody is watching the top of the screen. It only fires when a
    stale daemon exists, so it stays rare. The follow-up results stay at normal urgency.
    """
    return _notify("-u", "critical", *args)


def _still_the_one(pid: int, login: float) -> bool:
    """The daemon we asked about is still the only stale one — checked again after the click."""
    stale = find_stale(processes(), login)
    return len(stale) == 1 and stale[0].daemon.pid == pid


def offer_stop(stale: Stale, login: float) -> None:
    """Notify, and stop the daemon only if the user clicks Stop on the notification."""
    summary, body = notice(stale)
    claude = stale.daemon.argv[0]
    help_run = subprocess.run([claude, "daemon", "--help"], capture_output=True, text=True, check=False)
    if not supports_stop(help_run.stdout + help_run.stderr):
        missing = f"This Claude Code no longer offers the stop command this was written for ({WRITTEN_AGAINST})."
        _notice(summary, f"{body} {missing}")
        return
    label = f"Stop it (ends {_plural(len(stale.jobs), 'job')})" if stale.jobs else "Stop it"
    if _notice("-A", f"stop={label}", "-A", "keep=Leave it", summary, body) != "stop":
        return
    if not _still_the_one(stale.daemon.pid, login):
        _notify("Claude daemon not stopped", "It changed since the notice appeared, so nothing was stopped.")
        return
    result = subprocess.run([claude, "daemon", "stop", "--any"], capture_output=True, text=True, check=False)
    if result.returncode == 0:
        _notify("Claude daemon stopped", "The next background job starts a fresh one.")
    else:
        detail = (result.stderr or result.stdout).strip() or f"exit {result.returncode}"
        _notify("Claude daemon stop failed", detail)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Notice a Claude Code daemon older than this login.")
    parser.add_argument("--notify", action="store_true", help="show a desktop notification with a Stop button")
    notify = bool(cast(object, parser.parse_args(argv).notify))

    login = login_started()
    if login is None:
        return 0
    stale = find_stale(processes(), login)
    for entry in stale:
        summary, body = notice(entry)
        print(f"{summary} (pid {entry.daemon.pid}). {body}")
    if not notify or not stale or shutil.which("notify-send") is None:
        return 0
    if len(stale) > 1:
        # `claude daemon stop --any` names no pid, so with two candidates a click could stop either.
        _notice(*notice(stale[0]))
        return 0
    offer_stop(stale[0], login)
    return 0


if __name__ == "__main__":
    sys.exit(main())
