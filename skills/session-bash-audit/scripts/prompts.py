#!/usr/bin/env python3
"""Estimate which recent Bash calls prompted under acceptEdits, and why — from the transcripts and
the live ~/.claude/settings.json rules.

Approved prompts leave no trace in a transcript, so the prompt rate can't be measured directly;
this replays Claude Code's matching over every call instead: split on the separators the
permission engine recognizes, strip the wrappers it strips, then per piece — an `ask` rule wins,
else an `allow` rule (not behind a leading VAR= assignment), else the built-in read-only set, else
acceptEdits' in-scope grant for mkdir/touch/rm/rmdir/mv/cp/sed, else it prompts. Reports the share
of calls that prompt per session and the first prompting reason per call, ranked, with samples —
the ranked list is the input to `inv allowlist.review`/`tools.toml`, not a ~/AGENTS.md sentence.

    python3 ~/.agents/skills/session-bash-audit/scripts/prompts.py --days 2
    python3 .../prompts.py --since 2026-08-24T19:13:00Z --project repo-tasks

Approximation, stated: `$VAR`/`~` redirect targets and `cd` + redirect are treated as prompting
(the docs say a ~/glob target needs approval; a variable target is unverified — probe it); the
built-in read-only git verbs are a short hand list; a `for`/`while` loop body isn't descended into.
Stdlib only; read-only.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from audit import Call, load_calls, short_project, split_chain

SETTINGS = Path.home() / ".claude" / "settings.json"
BUILTIN_RO = {"ls", "cat", "echo", "pwd", "head", "tail", "grep", "find", "wc", "which", "diff", "stat", "du", "cd"}
GIT_RO = {"status", "log", "diff", "show", "blame", "grep", "ls-files", "rev-parse"}
FS_MODE = {"mkdir", "touch", "rm", "rmdir", "mv", "cp", "sed"}
WRAPPERS = {"timeout", "time", "nice", "nohup", "stdbuf", "command", "builtin", "noglob"}
SHELL_WORDS = {"true", "false", "test", "[", "export", "set", "unset", "exit", "return", ":", "break", "continue"}
CONTROL_PREFIXES = ("for", "while", "if", "do", "done", "fi", "then", "else", "elif", "{", "}", "(", ")")
REDIRECT_RE = re.compile(r"(?<![<>&\d])>{1,2}\s*(\S+)")
ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=\S*\s+")


def _rule_regexes(rules: list[str]) -> list[tuple[str, re.Pattern[str]]]:
    out = []
    for rule in rules:
        m = re.fullmatch(r"Bash\((.*)\)", rule)
        if not m:
            continue
        body = m.group(1)
        if body.endswith(":*"):
            rx = "^" + re.escape(body[:-2]).replace(r"\*", ".*") + r"(\s.*)?$"
        else:
            rx = "^" + re.escape(body).replace(r"\*", ".*") + "$"
        out.append((rule, re.compile(rx, re.S)))
    return out


Rules = tuple[list[tuple[str, re.Pattern[str]]], list[tuple[str, re.Pattern[str]]], list[str]]


def load_rules() -> Rules:
    perms = json.loads(SETTINGS.read_text()).get("permissions", {})
    allow = _rule_regexes(perms.get("allow", []))
    ask = _rule_regexes(perms.get("ask", []))
    return allow, ask, perms.get("additionalDirectories", [])


def strip_wrappers(piece: str) -> tuple[str, bool]:
    env = False
    while True:
        m = ENV_ASSIGN_RE.match(piece)
        if m:
            piece, env = piece[m.end() :], True
            continue
        words = piece.split(None, 1)
        if words and words[0] in WRAPPERS:
            piece = re.sub(r"^(-\S+\s+|\d+\S*\s+)*", "", words[1] if len(words) > 1 else "")
            continue
        return piece, env


def in_scope(path: str, project: str, extra_dirs: list[str]) -> bool:
    if path.startswith(("~", "$")) or "*" in path:
        return False
    if not path.startswith("/"):
        return True
    # Claude Code names a project directory by its absolute path with / and . turned into -.
    encoded = path.replace("/", "-").replace(".", "-")
    return encoded.startswith(project) or any(path.startswith(d) for d in extra_dirs)


def _rule_match(piece: str, rules: list[tuple[str, re.Pattern[str]]]) -> str | None:
    return next((name for name, rx in rules if rx.match(piece)), None)


def _builtin_or_mode(piece: str, call: Call, has_cd: bool, has_git: bool, extra_dirs: list[str]) -> str | None:
    """What Claude Code does with a piece no rule matched: built-in read-only set, acceptEdits'
    in-scope filesystem grant, else a prompt."""
    words = piece.split()
    verb = words[0]
    if verb == "cd":
        return "cd+git" if has_git else None
    if verb in BUILTIN_RO:
        return None
    if verb == "git":
        sub = words[1] if len(words) > 1 else ""
        return None if sub in GIT_RO and not has_cd else f"unmatched:git {sub}"
    if verb in FS_MODE:
        # a quoted argument is a sed script or a pattern, not a path
        paths = [a for a in words[1:] if not a.startswith(("-", "'", '"'))]
        if not has_cd and all(in_scope(p, call.project, extra_dirs) for p in paths):
            return None
        return f"mode-outscope:{verb}"
    label = " ".join(words[:2]) if verb in {"inv", "uv", "gh", "python3", "python", "docker", "npm", "go"} else verb
    return f"unmatched:{label}"


def classify_piece(piece: str, call: Call, has_cd: bool, has_git: bool, rules: Rules) -> str | None:
    """None if the piece runs without a prompt, else a short reason label."""
    allow, ask, extra_dirs = rules
    piece, env = strip_wrappers(piece)
    if not piece:
        return None
    verb = piece.split()[0]
    if verb.startswith(CONTROL_PREFIXES) or verb in SHELL_WORDS:
        return None
    if asked := _rule_match(piece, ask):
        return f"ask:{asked}"
    if env:
        return f"env-prefix:{verb}"
    if _rule_match(piece, allow):
        return None
    m = REDIRECT_RE.search(piece)
    if m and m.group(1) != "/dev/null" and (has_cd or not in_scope(m.group(1), call.project, extra_dirs)):
        return f"redirect:{m.group(1)}"
    return _builtin_or_mode(piece, call, has_cd, has_git, extra_dirs)


def prompting_reasons(call: Call, rules: Rules) -> list[str]:
    pieces = split_chain(call.cmd)
    verbs = [p.split()[0] for p in pieces if p.split()]
    has_cd, has_git = "cd" in verbs, "git" in verbs
    return [r for p in pieces if (r := classify_piece(p, call, has_cd, has_git, rules))]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=float, default=2, help="look back this many days of transcript mtime (default 2)")
    ap.add_argument("--since", help="ISO timestamp; only calls at or after it (e.g. the moment a mode/rule changed)")
    ap.add_argument("--project", help="only projects whose slug contains this substring")
    ap.add_argument("--samples", type=int, default=2, help="sample commands per reason (default 2)")
    args = ap.parse_args()

    rules = load_rules()
    calls = [c for c in load_calls(args.days, args.project) if not c.subagent]
    if args.since:
        calls = [c for c in calls if c.timestamp >= args.since]
    if not calls:
        print("no calls in window")
        return

    per_session: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    reasons: Counter[str] = Counter()
    samples: dict[str, list[str]] = defaultdict(list)
    prompting = 0
    for c in calls:
        key = f"{short_project(c.project)}/{c.session[:8]} {c.model}"
        per_session[key][1] += 1
        found = prompting_reasons(c, rules)
        if not found:
            continue
        prompting += 1
        per_session[key][0] += 1
        reasons[found[0]] += 1  # the first prompt is the one the user sees
        if len(samples[found[0]]) < args.samples:
            samples[found[0]].append(c.cmd[:150].replace("\n", "\\n"))

    print(f"calls: {len(calls)}   estimated prompting: {prompting} ({100 * prompting / len(calls):.0f}%)\n")
    print("== per session (prompting/total) ==")
    for key, (p, n) in sorted(per_session.items(), key=lambda kv: -kv[1][1]):
        print(f"  {key:60s} {p:4d}/{n:4d}  {100 * p / n:3.0f}%")
    print("\n== first prompting reason per call ==")
    for reason, n in reasons.most_common():
        print(f"  {n:4d}  {reason}")
        for s in samples[reason]:
            print(f"          {s}")


if __name__ == "__main__":
    main()
