"""Harness-neutral command permission rules, and one renderer per agent harness.

`allowlist.py` decides *what* is allowed or asked about; this module decides how each harness has to
spell it. They are separate because the harnesses disagree about what a pattern can even say, and
the disagreement moves between releases — Claude Code 2.1.282 started loading, and 2.1.283 started
warning about, rules it had silently skipped for months. One source rendered many ways is what lets
a new harness, or a changed one, cost a renderer rather than a second hand-maintained rule list.

A rule's pattern is written in this module's own grammar, tokens after the tool name:

    status ...          `...` is zero or more whole arguments
    reset ... --hard    ...anywhere in the pattern, not only at the end
    *.status ...        a token containing `*` is exactly one argument matching that glob
    --list              anything else is a literal word

How each harness matches, and why each renderer is shaped the way it is, was measured rather than
read — see contributing/cli-allowlist.md's "How each harness matches".
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from itertools import pairwise

ANY_ARGS = "..."


class Decision(StrEnum):
    ALLOW = "allow"
    ASK = "ask"


class RuleSyntaxError(ValueError):
    """A pattern this module's grammar can't express, or one a harness would load but mis-read."""


def parse(body: str) -> tuple[str, ...]:
    """Split a pattern body into tokens, rejecting shapes whose meaning would be ambiguous."""
    tokens = tuple(body.split())
    for token in tokens:
        if ANY_ARGS in token and token != ANY_ARGS:
            raise RuleSyntaxError(f"{body!r}: `...` must be a token of its own, not part of {token!r}")
    for a, b in pairwise(tokens):
        if a == b == ANY_ARGS:
            raise RuleSyntaxError(f"{body!r}: two `...` in a row mean the same as one")
    return tokens


@dataclass(frozen=True)
class Rule:
    """One allow/ask decision about the commands a pattern matches.

    `repo_dir_options` names options that take a repository directory and may sit between the
    tool and its verb (git's `-C`); a renderer spells those its own way, or not at all where the
    harness can't say "one argument" safely. `mode_covered` marks an
    ask a harness's permission mode may already gate more precisely than a pattern can — Claude
    Code's `acceptEdits` does, for in-scope `mkdir`/`rm`/..., so its renderer drops it."""

    tool: str
    decision: Decision
    tokens: tuple[str, ...]
    repo_dir_options: tuple[str, ...] = ()
    mode_covered: bool = False

    def __post_init__(self) -> None:
        parse(" ".join(self.tokens))
        if not self.tool or any(ch.isspace() for ch in self.tool):
            raise RuleSyntaxError(f"tool name {self.tool!r} must be one non-empty word")


# ---------------------------------------------------------------------------
# Claude Code: `Bash(<pattern>)`, where `*` matches any text — spaces included, the empty string
# between two spaces excluded — and a trailing ` *` alone also matches the bare command.
# ---------------------------------------------------------------------------


def _claude_bodies(tokens: tuple[str, ...]) -> list[str]:
    """Every Claude spelling of a token sequence. `*` can't match "nothing" between two spaces, so
    zero-or-more arguments takes two spellings, with and without the `*`."""
    variants: list[list[str]] = [[]]
    for token in tokens:
        if token != ANY_ARGS:
            variants = [[*v, token] for v in variants]
            continue
        # A glob already spans any trailing text in Claude's syntax, so `x.* *` adds nothing.
        variants = [w for v in variants for w in ([v] if v and v[-1].endswith("*") else [v, [*v, "*"]])]
    bodies = [" ".join(v) for v in variants]
    # `X *` matches bare `X` as long as that trailing `*` is its only wildcard — drop the duplicate.
    return [b for b in bodies if not (f"{b} *".strip() in bodies and f"{b} *".count("*") == 1)]


def claude_inner_wildcard(pattern: str) -> bool:
    """True when a `Bash(...)` pattern has a standalone `*` before its last word — the shape
    Claude Code warns about at every startup on an allow rule, because the `*` absorbs options
    such as git's `-c` that run arbitrary programs."""
    words = pattern.removeprefix("Bash(").removesuffix(")").split()
    return "*" in words[:-1]


def claude_patterns(rule: Rule) -> list[str]:
    """A rule's `Bash(...)` patterns. `repo_dir_options` is not rendered: Claude's syntax has no
    "one argument", so `git -C * status` is the warned-about shape and lets `-c <program>` ride
    along, and one rule per repository hit the 2 MiB settings cap. Claude Code's Bash sandbox runs
    `git -C <repo> <read>` with no rule at all (measured 2026-09-26), so that is where it belongs."""
    return [f"Bash({rule.tool} {body})" if body else f"Bash({rule.tool})" for body in _claude_bodies(rule.tokens)]


def render_claude(rules: Iterable[Rule]) -> tuple[list[str], list[str]]:
    """(allow, ask) pattern lists for `~/.claude/settings.json`, de-duplicated in first-seen order.

    Raises on an allow pattern with an inner wildcard: it would print a warning on every session
    start, and a permanent warning is one nobody reads — which is how the next real one gets
    missed."""
    allow: dict[str, None] = {}
    ask: dict[str, None] = {}
    for rule in rules:
        if rule.decision is Decision.ASK and rule.mode_covered:
            continue
        for pattern in claude_patterns(rule):
            if rule.decision is Decision.ALLOW and claude_inner_wildcard(pattern):
                raise RuleSyntaxError(f"{pattern}: Claude Code warns about a wildcard before the last word")
            (allow if rule.decision is Decision.ALLOW else ask)[pattern] = None
    return list(allow), list(ask)


# ---------------------------------------------------------------------------
# VS Code Copilot: `chat.tools.terminal.autoApprove`, regex keys, `false` checked before `true`.
# Regex can say "exactly one argument", so no rule here needs enumerating.
# ---------------------------------------------------------------------------


def _copilot_token(token: str) -> str:
    if token == ANY_ARGS:
        return r"(?:\s+\S+)*"
    return r"\s+" + r"\S*".join(re.escape(part) for part in token.split("*"))


def copilot_key(rule: Rule) -> str:
    """A rule as an anchored `/regex/` key. VS Code anchors nothing itself."""
    regex = "^" + re.escape(rule.tool)
    if rule.repo_dir_options:
        options = "|".join(re.escape(opt) for opt in rule.repo_dir_options)
        regex += rf"(?:\s+(?:{options})\s+\S+)*"
    regex += "".join(_copilot_token(t) for t in rule.tokens) + "$"
    return f"/{regex}/"


def render_copilot(rules: Iterable[Rule]) -> dict[str, bool]:
    """`{key: approve}` for `chat.tools.terminal.autoApprove`. Two rules sharing a key resolve to
    `false`, the same way VS Code resolves two matching keys."""
    out: dict[str, bool] = {}
    for rule in rules:
        key = copilot_key(rule)
        out[key] = out.get(key, True) and rule.decision is Decision.ALLOW
    return out
