#!/usr/bin/env python3
"""Audit recent Claude Code transcripts for Bash-tool habits that fight ~/AGENTS.md's Bash rules.

Reads every `~/.claude/projects/*/*.jsonl` (main sessions and their `subagents/` transcripts)
modified in the last N days, pulls out each Bash tool call with its result, tags it against the
PATTERNS table below, and prints per-model rates, per-session rates, samples per pattern, denied
calls, and truncation re-runs. Stdlib only; read-only; never touches the transcripts.

    python3 ~/.agents/skills/session-bash-audit/scripts/audit.py --days 4
    python3 .../audit.py --days 7 --project repo-tasks --samples 5 --json /tmp/x/calls.json

Extending: add a row to PATTERNS (name, regex or predicate, one-line why). Keep the row's "why"
honest — the table is also the checklist SKILL.md tells the agent to reason from, so a pattern with
no stated cost teaches nothing. Record what a new pattern found in references/research.md.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import time
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

PROJECTS_DIR = Path.home() / ".claude" / "projects"
HEREDOC_RE = re.compile(r"<<-?\s*['\"]?[A-Za-z_]+['\"]?")
SEPARATOR_RE = re.compile(r"&&|\|\||[;|\n]")


@dataclass
class Call:
    cmd: str
    model: str
    project: str
    session: str
    subagent: bool
    timestamp: str
    error: bool
    result: str
    tags: set[str] = field(default_factory=set)

    @property
    def denied(self) -> bool:
        low = self.result.lower()
        return self.error and ("denied" in low or "doesn't want to proceed" in low or "rejected" in low)


def strip_heredoc(cmd: str) -> str:
    """Drop heredoc bodies so their content can't look like chained commands."""
    m = HEREDOC_RE.search(cmd)
    return cmd[: m.start()] if m else cmd


def split_chain(cmd: str) -> list[str]:
    """Split on the separators Claude Code's permission engine recognizes (&&, ||, ;, |, newline),
    outside quotes. Crude on purpose — this is a habit audit, not a shell parser."""
    body = strip_heredoc(cmd)
    parts: list[str] = []
    buf = ""
    quote: str | None = None
    i = 0
    while i < len(body):
        c = body[i]
        if quote:
            buf += c
            if c == quote:
                quote = None
        elif c in "'\"":
            quote = c
            buf += c
        elif body.startswith(("&&", "||"), i):
            parts.append(buf)
            buf = ""
            i += 1
        elif c in ";|\n":
            parts.append(buf)
            buf = ""
        else:
            buf += c
        i += 1
    parts.append(buf)
    return [p.strip() for p in parts if p.strip()]


def _chain_tags(cmd: str) -> set[str]:
    parts = split_chain(cmd)
    if len(parts) < 2:
        return set()
    if len(parts) == 2 and parts[0].startswith("cd ") and "&&" in strip_heredoc(cmd):
        return {"cd-and-cmd"}  # the one chain shape ~/AGENTS.md permits (cross-repo only)
    return {f"chain{min(len(parts), 5)}"}


def _cd_tag(cmd: str, project: str) -> set[str]:
    m = re.search(r"(?:^|&&|;|\n)\s*cd\s+(\S+)", strip_heredoc(cmd))
    if not m:
        return set()
    target = m.group(1).replace("~", str(Path.home())).replace("$HOME", str(Path.home())).rstrip("/")
    # Claude Code names a project directory by its absolute path with / and . turned into -.
    return {"cd-own-repo"} if target.replace("/", "-").replace(".", "-") == project else {"cd-other"}


def short_project(project: str) -> str:
    """`-home-u-projects-github-com-personal-repo-tasks` -> `repo-tasks` (best effort)."""
    for marker in ("-github-com-personal-", "-projects-"):
        if marker in project:
            return project.split(marker, 1)[1]
    return project[-24:]


Predicate = Callable[[str], bool]


def _rx(pattern: str) -> Predicate:
    compiled = re.compile(pattern)
    return lambda cmd: bool(compiled.search(strip_heredoc(cmd)))


# name -> (predicate, why it matters). Chain and cd tags are computed separately above.
PATTERNS: dict[str, tuple[Predicate, str]] = {
    "head/tail": (
        _rx(r"\|\s*(head|tail)\b"),
        "truncates tool output the harness would have kept whole; forces re-runs and hides failures",
    ),
    "exit-masked": (
        _rx(r"2>&1\s*\|\s*(tail|head|grep|rg)\b"),
        "$? after a pipe is the filter's, not the command's — a failing gate reads as clean",
    ),
    "redirect-then-filter": (
        _rx(r">\s*\S+\s+2>&1\s*;.*\|\s*(rg|grep|head|tail)\b"),
        "capture-to-log is fine; filtering the log in the same call is not — Grep/Read the log as a second call",
    ),
    "echo-exit": (
        _rx(r";\s*echo\s+[\"']?(EXIT|exit)[=: ]"),
        "reflexive `; echo EXIT=$?` — the Bash tool already reports a non-zero exit",
    ),
    "search|head": (
        _rx(r"\b(rg|grep|fd|find)\b[^|]*\|\s*head\b"),
        "turns a completeness search into a sample without saying so (count first: rg -c / wc -l)",
    ),
    "sed-n": (_rx(r"\bsed\s+-n\b"), "file view via Bash; Read(offset/limit) does it with no Bash gate"),
    "cat-view": (
        lambda cmd: bool(re.fullmatch(r"\s*(cat|head -\d+|tail -\d+)\s+[^|;&<>]+", strip_heredoc(cmd))),
        "whole-file view via Bash; Read does it with no Bash gate",
    ),
    "grep/find": (_rx(r"(?:^|&&|;|\|)\s*(grep|rg|find|fd)\b"), "search via Bash; Grep/Glob have their own gate"),
    "env-prefix": (_rx(r"^\s*[A-Z_][A-Z0-9_]*=\S+\s+\S"), "leading VAR=x defeats allow-rule prefix matching"),
    "bash-c": (_rx(r"\b(bash|sh|zsh)\s+-l?c\b"), "outer bash is itself ask-gated; always prompts"),
    "heredoc": (lambda cmd: bool(HEREDOC_RE.search(cmd)), "file write via shell; Write/Edit have their own gate"),
    "sed-i": (_rx(r"\bsed\s+-i\b"), "in-place edit via shell; Edit has its own gate"),
    "python-c": (_rx(r"\bpython3?\s+-c\b"), "ad-hoc script instead of a test or a dedicated tool"),
    "label-echo": (_rx(r"echo\s+['\"]?(===|---)"), "batching several steps into one call for labelled output"),
    "git-mutating": (
        _rx(r"\bgit\s+(-C\s+\S+\s+|-c\s+\S+\s+)?(commit|push|add|reset|checkout|rebase|merge|stash|rm|mv)\b"),
        "ask-gated verb; inside a chain or behind -C/-c the prefix rule may not match",
    ),
    "git-C-mutating": (
        _rx(r"\bgit\s+(-C|-c|--git-dir\S*|--work-tree\S*)\s+\S+\s+(commit|push|add|reset|checkout|rebase|merge)\b"),
        "global option before the verb: Bash(git push:*) does not match `git -C x push`",
    ),
    "pgrep-f": (
        _rx(r"\b(pgrep|pkill)\s+(-\w*f\w*\s+)+"),
        "full-cmdline match hits the harness's own `zsh -c … eval '<cmd>'` wrapper: a false positive "
        "that reads as a real process, plus the env blob. Match the executable (pgrep -x, ps -C)",
    ),
    "shell-background": (
        _rx(r"\b(nohup|setsid|disown)\b|(?<![&|>])&\s*$"),
        "shell-level backgrounding can be killed before the command runs, and the next call then "
        "reads state as though it had: use the Bash tool's own run_in_background",
    ),
}


def classify(call: Call) -> None:
    call.tags |= _chain_tags(call.cmd)
    call.tags |= _cd_tag(call.cmd, call.project)
    for name, (pred, _) in PATTERNS.items():
        if pred(call.cmd):
            call.tags.add(name)
    if "git-mutating" in call.tags and any(t.startswith("chain") for t in call.tags):
        call.tags.add("git-mutating-in-chain")


def _text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(str(b.get("text", "")) for b in content if isinstance(b, dict))
    return ""


def _blocks(path: Path):
    """Yield (message, block) for every content block in a transcript, skipping unparsable lines."""
    with path.open() as fh:
        for line in fh:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = obj.get("message") or {}
            content = msg.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if isinstance(block, dict):
                    yield obj, msg, block


def _parse_transcript(path: Path, project: str) -> list[Call]:
    subagent = "subagents" in path.parts
    pending: dict[str, Call] = {}
    results: dict[str, tuple[bool, str]] = {}
    for obj, msg, block in _blocks(path):
        if block.get("type") == "tool_use" and block.get("name") == "Bash":
            pending[block["id"]] = Call(
                cmd=block["input"].get("command", ""),
                model=msg.get("model") or "?",
                project=project,
                session=path.stem,
                subagent=subagent,
                timestamp=obj.get("timestamp") or "",
                error=False,
                result="",
            )
        elif block.get("type") == "tool_result":
            tid = block.get("tool_use_id", "")
            results[tid] = (bool(block.get("is_error")), _text(block.get("content"))[:300])
    for tid, call in pending.items():
        call.error, call.result = results.get(tid, (False, ""))
        classify(call)
    return list(pending.values())


def load_calls(days: float, project_filter: str | None) -> list[Call]:
    cutoff = time.time() - days * 86400
    calls: list[Call] = []
    for path in PROJECTS_DIR.rglob("*.jsonl"):
        if path.stat().st_mtime < cutoff:
            continue
        project = path.relative_to(PROJECTS_DIR).parts[0]
        if project_filter and project_filter not in project:
            continue
        calls.extend(_parse_transcript(path, project))
    return calls


RATE_COLUMNS = [
    "head/tail",
    "exit-masked",
    "redirect-then-filter",
    "sed-n",
    "cat-view",
    "heredoc",
    "cd-own-repo",
    "git-mutating-in-chain",
]

# What a re-measurement after the 2026-08-24 changes (acceptEdits default, rewritten ~/AGENTS.md
# Bash cluster) should show, per model, relative to the stored baseline. "down": lower share;
# "zero": at or near 0%. Anything else is reported but not judged.
EXPECTATIONS: dict[str, str] = {
    "chain": "down",
    "head/tail": "down",
    "redirect-then-filter": "zero",
    "echo-exit": "zero",
    "sed-n": "down",
    "cat-view": "down",
    "heredoc": "down",
    "cd-own-repo": "zero",
    "git-mutating-in-chain": "down",
    "git-C-mutating": "zero",
}


def rates(calls: list[Call]) -> dict[str, float]:
    """Share of `calls` carrying each tag, plus the aggregate chain rate."""
    n = len(calls)
    counts = Counter(t for c in calls for t in c.tags)
    out = {"chain": sum(counts[f"chain{i}"] for i in range(2, 6)) / n, "chain5": counts["chain5"] / n}
    for col in [*RATE_COLUMNS, "git-C-mutating", "echo-exit"]:
        out[col] = counts[col] / n
    return out


def rates_by_model(calls: list[Call]) -> dict[str, dict[str, float | int]]:
    groups = _group(calls, lambda c: f"{c.model}{' [sub]' if c.subagent else ''}")
    return {label: {"n": len(rs), **rates(rs)} for label, rs in groups.items()}


def _rate_row(label: str, calls: list[Call], columns: list[str]) -> str:
    r = rates(calls)
    cells = [f"chain={r['chain']:.0%}", f"chain5={r['chain5']:.0%}"]
    cells += [f"{col}={r[col]:.0%}" for col in columns]
    return f"{label:44} n={len(calls):5}  " + "  ".join(cells)


def save_baseline(calls: list[Call], path: Path, days: float, note: str) -> None:
    payload = {
        "saved": time.strftime("%Y-%m-%d", time.gmtime()),
        "days": days,
        "note": note,
        "models": rates_by_model(calls),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1) + "\n")
    print(f"\nbaseline written to {path}")


def compare(calls: list[Call], baseline_path: Path) -> None:
    """Per model present in both runs: delta in percentage points against the baseline, with a
    verdict for every tag EXPECTATIONS names. A model with under 50 calls in either run is shown
    but not judged — the rates are too noisy to call."""
    baseline = json.loads(baseline_path.read_text())
    print(f"\n== vs baseline {baseline_path.name} ({baseline.get('saved')}, {baseline.get('note', '')}) ==")
    now = rates_by_model(calls)
    verdicts: list[bool] = []
    for label, cur in sorted(now.items(), key=lambda kv: -int(kv[1]["n"])):
        old = baseline["models"].get(label)
        if old is None:
            print(f"{label:44} n={cur['n']:5}  (not in baseline)")
            continue
        judge = min(int(cur["n"]), int(old["n"])) >= 50
        cells = []
        for tag, want in EXPECTATIONS.items():
            before, after = float(old.get(tag, 0.0)), float(cur.get(tag, 0.0))
            delta = (after - before) * 100
            ok = after <= 0.02 if want == "zero" else after < before
            mark = ("OK" if ok else "MISS") if judge else "?"
            if judge:
                verdicts.append(ok)
            cells.append(f"{tag}={after:.0%}({delta:+.0f}pp,{mark})")
        print(f"{label:44} n={cur['n']:5}  " + "  ".join(cells))
    if verdicts:
        print(f"\n{sum(verdicts)}/{len(verdicts)} expectations met (models with >=50 calls in both runs)")
    else:
        print("\nno model has >=50 calls in both runs — nothing judged yet; re-run with a wider --days")


PROBES = [
    (
        "mkdir -p <scratch>/probe-fs",
        "no prompt — <scratch> is in permissions.additionalDirectories and mkdir is a mode-granted fs command",
    ),
    (
        "mkdir -p ./.probe-fs && rmdir ./.probe-fs",
        "no prompt — inside the working directory; also proves the old Bash(mkdir:*) ask rule is gone",
    ),
    (
        "git -C <another personal repo> status",
        "no prompt — the Bash(git -C * status:*) allow rule from global_option_prefixes",
    ),
    (
        "git init -q --bare <scratch>/probe-remote.git",
        "PROMPT — not read-only, matches no rule; approve it (throwaway path)",
    ),
    (
        "git -C <scratch>/probe-remote.git push -q <scratch>/probe-remote.git HEAD:probe",
        "PROMPT — a mutating verb behind -C matches no ask rule and must fall through to the mode's prompt; "
        "under auto mode this is the call that ran unprompted. Fails harmlessly after approval "
        "(bare repo has no HEAD); the prompt is the data point",
    ),
    (
        "rm -rf <scratch>/probe-fs <scratch>/probe-remote.git",
        "no prompt — in-scope rm is mode-granted; the harness still hard-blocks rm on critical paths",
    ),
]


def print_probes() -> None:
    print(__doc__.split("\n\n")[0])
    print(
        "\nLive permission probes. Run each as its OWN Bash tool call (a subprocess would bypass the\n"
        "harness's permission check), in an acceptEdits session, with <scratch> = $CLAUDE_JOB_DIR/tmp\n"
        "or the session scratchpad. The agent cannot see prompts: after running them, tell the user\n"
        "which steps were expected to prompt and ask whether that is what they saw.\n"
    )
    for i, (cmd, expect) in enumerate(PROBES, 1):
        print(f"{i}. {cmd}\n   expect: {expect}")


def _print_rates(title: str, groups: dict[str, list[Call]], limit: int | None = None) -> None:
    print(f"\n== {title} ==")
    for label, rs in sorted(groups.items(), key=lambda kv: -len(kv[1]))[:limit]:
        print(_rate_row(label, rs, RATE_COLUMNS))


def _group(calls: list[Call], key: Callable[[Call], str]) -> dict[str, list[Call]]:
    groups: dict[str, list[Call]] = defaultdict(list)
    for c in calls:
        groups[key(c)].append(c)
    return groups


def report(calls: list[Call], samples: int) -> None:
    random.seed(1)
    print(f"Bash calls: {len(calls)}  (subagent: {sum(c.subagent for c in calls)})")

    _print_rates("per model", _group(calls, lambda c: f"{c.model}{' [sub]' if c.subagent else ''}"))
    main_calls = [c for c in calls if not c.subagent]
    by_session = _group(main_calls, lambda c: f"{short_project(c.project)}/{c.session[:8]} {c.model}")
    _print_rates("per session (main, largest first)", by_session, limit=25)

    print("\n== pattern totals ==")
    totals = Counter(t for c in calls for t in c.tags)
    for name, (_, why) in PATTERNS.items():
        print(f"{name:24} {totals[name]:5}   {why}")
    for name in CHAIN_TAGS:
        print(f"{name:24} {totals[name]:5}")

    reruns = _truncation_reruns(calls)
    print(f"\n== re-runs after a head/tail-truncated first run: {len(reruns)} ==")
    for base in reruns[:samples]:
        print("  " + base[:140].replace("\n", "\\n"))

    if samples:
        _print_samples(calls, samples)

    denied = [c for c in calls if c.denied]
    print(f"\n== denied ({len(denied)}) ==")
    for c in denied:
        print(f"[{c.model[:12]}] {c.cmd[:160]!r}\n    -> {c.result[:120]!r}")


CHAIN_TAGS = ("chain2", "chain3", "chain4", "chain5", "cd-and-cmd", "cd-own-repo", "cd-other", "git-mutating-in-chain")
SAMPLE_TAGS = (
    "git-C-mutating",
    "git-mutating-in-chain",
    "chain5",
    "head/tail",
    "exit-masked",
    "cd-own-repo",
    "sed-n",
    "cat-view",
)


def _print_samples(calls: list[Call], samples: int) -> None:
    for name in SAMPLE_TAGS:
        rs = [c for c in calls if name in c.tags]
        print(f"\n== {name} ({len(rs)}) samples ==")
        for c in random.sample(rs, min(samples, len(rs))):
            who = f"{c.model[:12]}|{'sub' if c.subagent else 'main'}|{short_project(c.project)[:18]}"
            print(f"[{who}] {c.cmd[:220].replace(chr(10), chr(92) + 'n')}")


def _truncation_reruns(calls: list[Call]) -> list[str]:
    """Same command issued again after a `| head/tail -N` run — the truncation lost something."""
    seen: dict[str, int] = {}
    reruns: list[str] = []
    for c in sorted(calls, key=lambda c: c.timestamp):
        m = re.match(r"(.*?)\|\s*(?:head|tail)\s+-(\d+)\s*$", c.cmd.strip(), re.DOTALL)
        base = m.group(1).strip() if m else c.cmd.strip()
        limit = int(m.group(2)) if m else 10**9
        if base in seen and seen[base] < limit:
            reruns.append(base)
        seen[base] = limit
    return reruns


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=float, default=4, help="look back this many days of transcript mtime (default 4)")
    ap.add_argument("--project", help="only projects whose slug contains this substring")
    ap.add_argument("--samples", type=int, default=8, help="samples to print per pattern (0 = none)")
    ap.add_argument("--json", type=Path, help="also dump every call with its tags to this JSON file")
    ap.add_argument("--compare", type=Path, help="baseline JSON to diff the per-model rates against, with verdicts")
    ap.add_argument("--save-baseline", type=Path, help="write this run's per-model rates as a new baseline JSON")
    ap.add_argument("--note", default="", help="free-text label stored in the baseline (mode in force, why)")
    ap.add_argument("--probe", action="store_true", help="print the live permission probes and exit")
    args = ap.parse_args()

    if args.probe:
        print_probes()
        return

    calls = load_calls(args.days, args.project)
    if not calls:
        print("no Bash calls found — check --days / --project")
        return
    report(calls, args.samples)
    if args.compare:
        compare(calls, args.compare)
    if args.save_baseline:
        save_baseline(calls, args.save_baseline, args.days, args.note)
    if args.json:
        args.json.write_text(json.dumps([{**c.__dict__, "tags": sorted(c.tags)} for c in calls], indent=1, default=str))
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
