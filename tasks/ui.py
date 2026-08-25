"""Bordered terminal output for PULSE's own messages.

A single `inv setup`/`inv wsl.install` run interleaves our own status lines with raw apt/dpkg/
curl/gpg output scrolling past in the same terminal. Terse per-package lines (`[gh] repo:ok`) are
meant to blend in with that — they're deliberately styled like any other tool's status output.
This module is for the messages that aren't that: summaries, warnings, doc pointers, and prompts
that block for input — the ones worth visually pulling out of the noise so they can't be missed
mid-scroll.

Three kinds:

    ui.block(...)     a status/summary block — the general-purpose one
    ui.note(...)      a doc/reference pointer — visually softer, not an alert
    ui.warn(...)      something needs attention but isn't blocking for input
    ui.ask(question)  a yes/no prompt that blocks for input — the loudest style, since missing
                       it means the whole run just sits there waiting on you

All degrade to plain, uncolored text when stdout isn't a real terminal (piped, redirected, CI) —
never emits raw ANSI escapes into a log file. `ask()` also folds in util.interactive()'s gate:
non-interactive callers get `default` back with no box and no prompt at all.
"""

import shutil
import sys
import textwrap

from . import util

_MIN_WIDTH = 40
_MAX_WIDTH = 96

_RESET = "\033[0m"


def _width() -> int:
    cols = shutil.get_terminal_size(fallback=(80, 20)).columns
    return max(_MIN_WIDTH, min(_MAX_WIDTH, cols))


def _wrapped(lines: tuple[str, ...], width: int) -> list[str]:
    """Word-wrap each input line to the box width. A caller's own `\\n` still forces a break
    (e.g. to put a question on its own line after an explanation) — everything between those is
    free-flowing prose wrapped to fit, not something the caller needs to hand-wrap for a terminal
    width it can't know in advance.
    """
    out: list[str] = []
    for line in lines:
        for para in line.split("\n"):
            out.extend(textwrap.wrap(para, width) if para else [""])
    return out


def _color() -> bool:
    return sys.stdout.isatty()


def _paint(text: str, code: str) -> str:
    return f"\033[{code}m{text}{_RESET}" if _color() else text


def _rule(char: str, code: str, label: str | None = None) -> str:
    width = _width()
    if not label:
        return _paint(char * width, code)
    tag = f" {label} "
    side = char * 2
    fill = char * max(0, width - len(side) - len(tag))
    return _paint(f"{side}{tag}{fill}", code)


def _block(lines: tuple[str, ...], *, label: str, rule_char: str, code: str) -> None:
    width = _width()
    print()
    print(_rule(rule_char, code, label))
    for line in _wrapped(lines, width):
        print(line)
    print(_rule(rule_char, code))


def block(*lines: str, label: str = "pulse") -> None:
    """General-purpose bordered status/summary block."""
    _block(lines, label=label, rule_char="─", code="36")  # cyan


def note(*lines: str) -> None:
    """A doc/reference pointer — visually softer than block(), not an alert."""
    _block(lines, label="see also", rule_char="·", code="2")  # dim


def warn(*lines: str) -> None:
    """Something needs attention but isn't blocking for input."""
    _block(lines, label="warning", rule_char="─", code="33")  # yellow


def ask(question: str, default: bool = True) -> bool:
    """A yes/no prompt, boxed in the loudest style since missing it means the whole run just
    hangs waiting on you. No box and no prompt — straight to `default` — when not interactive
    (piped/scripted/CI/dry-run), same gate as util.interactive().
    """
    if not util.interactive():
        return default
    _block((question,), label="action needed", rule_char="═", code="33;1")  # bold yellow
    return util.confirm("→", default=default)
