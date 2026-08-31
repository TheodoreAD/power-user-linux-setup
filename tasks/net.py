"""`inv net.*` — the invoke face of tasks/netdoctor.py.

All of the work is in that module, which is standard-library-only and Python-3.10-safe so it can
also run as `python3 tasks/netdoctor.py` before uv, invoke or this repo's venv exist (see its
docstring). This file adds nothing but the task wrapper: the same diagnosis has to be available
both to a fresh machine that has nothing installed and to someone already living in `inv`.
"""

import json
from pathlib import Path

from invoke import Context, task

from . import netdoctor, ui


@task
def check(c: Context, json_output: bool = False, quick: bool = False, full: bool = False, timeout: float = 4.0):
    """Diagnose this machine's network against what a PULSE run actually needs.

    Read-only: it resolves, connects and asks for headers, and never sends a credential —
    including when it asks a proxy what authentication it wants (a bare CONNECT, no
    Proxy-Authorization). Every finding it prints ends with the command that addresses it.

    Args:
        json_output: print the findings as JSON instead of the report.
        quick: only the endpoints that gate a bootstrap (skips npm/node/docker/microsoft).
        full: also probe every URL declared in setup.toml.
        timeout: seconds per probe (default 4).
    """
    scope = "quick" if quick else ("full" if full else "core")
    report = netdoctor.run(scope=scope, timeout=timeout, repo_root=Path(__file__).resolve().parent.parent)
    if json_output:
        print(json.dumps(report.as_dict(), indent=2))
        return
    print(netdoctor.render(report, colour=True))
    if report.verdict == netdoctor.BLOCKER:
        ui.warn(
            "At least one thing above will stop an install outright. Fix it before running "
            "`inv setup` / `inv wsl.install` — every step of those is a download."
        )
