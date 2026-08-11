"""Group setup tasks into named, skippable phases for `inv setup` / `inv wsl.install`.

Every install task already has a side-effect-free `util.DRY_RUN` branch that prints `ok`/`MISSING`
per item (see apt.py, tools.py, node.py, python.py, zsh.py, system.py, docker.py, fonts.py) — that
existing convention is reused here as the "is this phase already done" probe, rather than inventing
a second detection mechanism.
"""

import io
from contextlib import redirect_stdout

from . import ui, util


def _probe(c, funcs) -> str:
    """Run funcs with util.DRY_RUN forced on, capturing their status output, then restore
    DRY_RUN regardless of outcome. Never touches the real system: every func's DRY_RUN branch is
    a local, read-only check.
    """
    buf = io.StringIO()
    saved = util.DRY_RUN
    util.DRY_RUN = True
    try:
        with redirect_stdout(buf):
            for f in funcs:
                f(c)
    finally:
        util.DRY_RUN = saved
    return buf.getvalue()


def run(c, label, funcs, note=None):
    """Run a named group of setup tasks as one phase, banner first for visibility. If a dry-run
    probe shows nothing missing, offers to skip (default: yes) instead of redoing possibly-slow
    work (apt update, tool/version checks) that would just no-op anyway.

    Skipped entirely when util.DRY_RUN is already true globally (PULSE_DRY_RUN=1 inv setup) — that
    mode is a full status report across every task (see docs/index.md), and must keep printing
    every phase's diagnostics rather than silently skipping phases that look done.
    """
    ui.block(note or label, label=f"phase: {label}")
    if (
        not util.DRY_RUN
        and "MISSING" not in _probe(c, funcs)
        and ui.ask("Already looks complete — skip this phase?", default=True)
    ):
        print(f"[{label}] skipped")
        return
    for f in funcs:
        f(c)
