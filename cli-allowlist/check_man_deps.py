"""Maintenance check, not part of the `inv allowlist.*` pipeline: does any registered tool's help
invocation secretly depend on a separately-installed man-page-rendering package?

Text formatting alone can't answer this — gcloud's --help mimics a man page's NAME/SYNOPSIS/
DESCRIPTION layout with its own self-contained renderer, no external process involved. The only
reliable signal is watching what actually execs during the call. Checks for `man` itself and for
`groff`/`troff` (confirmed via this same strace technique: `aws help` doesn't invoke `man`, but
pipes through `groff -m man -T ascii` -> `troff` -> `grotty` to produce its formatted output — the
same "only works because a package happens to be installed" risk as git's original git-man
dependency, just a different package). Run after adding a tool to tools.toml, or periodically to
catch a tool that changed its help backend:

    python3 cli-allowlist/check_man_deps.py

Exit status is nonzero if anything invokes one of these — CI-friendly, though there's no CI here yet.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

from tasks import util
from tasks.allowlist import _DETERMINISTIC_ENV, _invocation, _load_registry


def main() -> int:
    import os

    registry = _load_registry()
    env = {**os.environ, **_DETERMINISTIC_ENV}
    offenders = []

    for name, cfg in sorted(registry.items()):
        if cfg.get("skip_interactive"):
            continue
        prefix = cfg.get("shell_prefix")
        if not prefix and not util.command_exists(name):
            continue

        help_flag = cfg.get("help_flag", "--help")
        args = help_flag.split()
        cmd = _invocation(name, args, cfg)

        with tempfile.NamedTemporaryFile(prefix="strace-", suffix=".log") as log:
            try:
                subprocess.run(
                    ["strace", "-f", "-e", "trace=execve", "-o", log.name, *cmd],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    env=env,
                    stdin=subprocess.DEVNULL,
                )
            except subprocess.TimeoutExpired:
                print(f"{name}: TIMEOUT (couldn't determine)")
                continue
            log_text = Path(log.name).read_text()

        binaries = ["/usr/bin/man", "/bin/man", "/usr/bin/groff", "/usr/bin/troff"]
        hit = next((b for b in binaries if f'execve("{b}"' in log_text), None)
        if hit:
            offenders.append(name)
            print(f"{name}: invokes {hit} — needs a fix (alternate flag, like git's -h) or a note")

    if not offenders:
        print(f"checked {len(registry)} registered tools — none invoke man/groff/troff")
        return 0
    print(f"\n{len(offenders)} tool(s) depend on man: {', '.join(offenders)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
