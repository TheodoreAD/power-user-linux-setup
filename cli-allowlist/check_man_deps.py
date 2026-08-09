"""Maintenance check, not part of the `inv allowlist.*` pipeline: does any registered tool's help
invocation secretly depend on a separately-installed man-pages package?

Text formatting alone can't answer this — gcloud's --help mimics a man page's NAME/SYNOPSIS/
DESCRIPTION layout with its own self-contained renderer, no `man` involved. The only reliable
signal is watching what actually execs during the call. Run after adding a tool to tools.toml, or
periodically to catch a tool that changed its help backend:

    python3 cli-allowlist/check_man_deps.py

Exit status is nonzero if anything invokes `man` — CI-friendly, though there's no CI here yet.
"""
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

_ROOT = Path(__file__).parent
_ENV_OVERRIDES = {"PAGER": "cat", "MANPAGER": "cat", "GIT_PAGER": "cat", "LESS": "FRX", "BROWSER": "true"}


def main() -> int:
    import os

    registry = tomllib.load(open(_ROOT / "tools.toml", "rb"))
    env = {**os.environ, **_ENV_OVERRIDES}
    offenders = []

    for name, cfg in sorted(registry.items()):
        if cfg.get("skip_interactive"):
            continue
        prefix = cfg.get("shell_prefix")
        if not prefix and subprocess.run(["which", name], capture_output=True).returncode != 0:
            continue

        help_flag = cfg.get("help_flag", "--help")
        args = help_flag.split()
        cmd = ["bash", "-c", f"{prefix} && {' '.join([name, *args])}"] if prefix else [name, *args]

        with tempfile.NamedTemporaryFile(prefix="strace-", suffix=".log") as log:
            try:
                subprocess.run(
                    ["strace", "-f", "-e", "trace=execve", "-o", log.name, *cmd],
                    capture_output=True, text=True, timeout=10, env=env, stdin=subprocess.DEVNULL,
                )
            except subprocess.TimeoutExpired:
                print(f"{name}: TIMEOUT (couldn't determine)")
                continue
            log_text = Path(log.name).read_text()

        if 'execve("/usr/bin/man"' in log_text or 'execve("/bin/man"' in log_text:
            offenders.append(name)
            print(f"{name}: invokes man — needs a fix (alternate flag, like git's -h) or a note")

    if not offenders:
        print(f"checked {len(registry)} registered tools — none invoke man")
        return 0
    print(f"\n{len(offenders)} tool(s) depend on man: {', '.join(offenders)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
