"""Per-repo commit-message stats for the last N days: body presence (trailers excluded) and size."""

import json
import re
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path.home() / "projects" / "github.com-personal"
DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 30
TRAILER = re.compile(r"^[A-Za-z-]+: .+$")
SEP = "\x1e"


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False).stdout


def body_of(raw: str) -> str:
    lines = [ln for ln in raw.strip().splitlines() if not TRAILER.match(ln.strip())]
    return "\n".join(lines).strip()


rows = []
samples = {}
for repo in sorted(p for p in ROOT.iterdir() if (p / ".git").exists()):
    if not git(repo, "remote").strip():
        continue
    out = git(repo, "log", "HEAD", f"--since={DAYS}.days", "--no-merges", f"--format=%h%x1f%s%x1f%b{SEP}")
    commits = [c.split("\x1f") for c in out.split(SEP) if c.strip()]
    if not commits:
        continue
    bodies = [(h.strip(), s, body_of(b)) for h, s, b in commits]
    sizes = [len(b) for _, _, b in bodies]
    bare = [(h, s) for h, s, b in bodies if not b]
    short = [(h, s, len(b)) for h, s, b in bodies if 0 < len(b) < 120]
    rows.append(
        {
            "repo": repo.name,
            "commits": len(bodies),
            "no_body": len(bare),
            "body_lt_120": len(short),
            "median_body": int(statistics.median(sizes)),
        }
    )
    samples[repo.name] = {"no_body": bare[:8], "short": short[:5]}

print(json.dumps({"days": DAYS, "rows": rows, "samples": samples}, indent=1))
