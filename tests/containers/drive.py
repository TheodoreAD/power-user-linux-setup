#!/usr/bin/env python3
"""Drive a command under a real pty, streaming everything to a log as it happens (so a hang is
visible while it hangs, not after), and answering prompts by regex.

    python3 tests/containers/drive.py --log FILE [--timeout N] [--cols N] \
        [--on REGEX=REPLY ...] -- cmd ...

REPLY may be empty (just Enter). Each --on fires at most once, in any order, whenever its regex
first matches the accumulated output.

Why a pty and not a pipe: the behaviour under test *is* terminal behaviour — whether a password
echoes, whether a prompt can be answered at all, whether the run hangs waiting for input. Through a
pipe every one of those looks fine. See tests/containers/README.md.
"""

import argparse
import fcntl
import os
import pty
import re
import select
import struct
import subprocess
import sys
import termios
import time
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, cast


@dataclass
class Rule:
    """One `REGEX=REPLY` answer, and whether it has been used."""

    pattern: re.Pattern[str]
    reply: str
    fired: bool = False


def _rules(specs: list[str]) -> list[Rule]:
    return [Rule(re.compile(spec.partition("=")[0]), spec.partition("=")[2]) for spec in specs]


def _drive(
    master: int,
    proc: "subprocess.Popen[bytes]",
    log: BinaryIO,
    rules: list[Rule],
    timeout: float,
) -> None:
    """Pump the pty until the child exits, the output goes quiet, or the deadline passes."""
    buf = bytearray()
    deadline = time.monotonic() + timeout
    last_activity = time.monotonic()
    while time.monotonic() < deadline:
        if proc.poll() is not None and not select.select([master], [], [], 0.3)[0]:
            return
        ready, _, _ = select.select([master], [], [], 0.3)
        if ready:
            try:
                chunk = os.read(master, 4096)
            except OSError:
                return
            if not chunk:
                return
            buf += chunk
            log.write(chunk)
            last_activity = time.monotonic()
        text = buf.decode("utf-8", "replace")
        for rule in rules:
            if not rule.fired and rule.pattern.search(text):
                time.sleep(0.4)
                os.write(master, (rule.reply + "\n").encode())
                log.write(f"\n<<< sent {rule.reply!r} for /{rule.pattern.pattern}/ >>>\n".encode())
                rule.fired = True
        idle = time.monotonic() - last_activity
        if idle > 180:
            log.write(f"\n<<< no output for {idle:.0f}s — giving up >>>\n".encode())
            return


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--timeout", type=float, default=1800.0)
    ap.add_argument("--cols", type=int, default=100)
    ap.add_argument("--rows", type=int, default=40)
    ap.add_argument("--on", action="append", default=[])
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    args = ap.parse_args()
    # argparse's namespace is untyped; name each value once here so the rest stays checkable.
    cmd = [a for a in cast("list[str]", args.cmd) if a != "--"]
    rules = _rules(cast("list[str]", args.on))
    log_path = Path(cast(str, args.log))
    timeout = float(cast(float, args.timeout))

    master, slave = pty.openpty()
    rows, cols = int(cast(int, args.rows)), int(cast(int, args.cols))
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
    proc = subprocess.Popen(cmd, stdin=slave, stdout=slave, stderr=slave, close_fds=True)
    os.close(slave)

    with log_path.open("wb", buffering=0) as log:
        _drive(master, proc, log, rules, timeout)
        finished = proc.poll() is not None
        if not finished:
            proc.kill()
            proc.wait()
        os.close(master)
        log.write(f"\n<<< finished={finished} exit={proc.returncode} ".encode())
        log.write(f"unfired={[r.pattern.pattern for r in rules if not r.fired]} >>>\n".encode())
    print(f"finished={finished} exit={proc.returncode}")
    # Exit as the child did, so a caller can assert on this run instead of reading the log for a
    # verdict the harness already knew. Returning 0 unconditionally made every failure — a non-zero
    # `inv wsl.install`, a hang killed at the deadline, a container that never started — look
    # identical to a clean pass from the outside, in the one script whose entire purpose is
    # observing whether a run survives to exit 0. A killed child has returncode -SIGKILL, which is
    # negative and not a valid exit status, so a timeout reports 124 the way timeout(1) does.
    if not finished:
        return 124
    return proc.returncode if proc.returncode >= 0 else 128 - proc.returncode


if __name__ == "__main__":
    sys.exit(main())
