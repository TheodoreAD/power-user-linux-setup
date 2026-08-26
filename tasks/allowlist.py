"""CLI command allowlist pipeline: extract -> classify -> review -> render -> apply.

Keeps `cli-allowlist/rules/<tool>.json` (read_only/write/dangerous per subcommand *and* per
risk-relevant flag, for every CLI tool this machine actually has installed) current without
hand-maintaining it, and merges the reviewed result into `~/.claude/settings.json`. Full design
rationale, every gotcha found while building this, and why several things here are deliberate
tradeoffs rather than TODOs: `contributing/cli-allowlist.md`.

    inv allowlist.extract    deterministic: capture --help text per tool, recursing into the
                              subcommand tree where a tool opts in (tools.toml's max_depth),
                              version-gated cache
    inv allowlist.classify   LLM (headless `claude -p`, Haiku): read_only/write/dangerous verdict
                              per subcommand node and per risk-relevant flag, incrementally —
                              only new/changed nodes (by content hash) are ever re-sent
    inv allowlist.review     human gate: shows what's new/changed, marks it reviewed
    inv allowlist.render     deterministic: reviewed rules -> Claude or Copilot rule syntax
    inv allowlist.apply      deterministic: merges reviewed Claude rules into ~/.claude/settings.json
    inv allowlist.status     quick table: installed/stale/unreviewed
    inv allowlist.check-coverage  every node-with-children's child has its own renderable rule —
                              apply already refuses to run when this finds anything

`render` only prints — `apply` is the only task that writes anywhere, and it only ever touches
`~/.claude/settings.json`'s `permissions` block (see its docstring for the merge safety design).
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from collections.abc import Mapping
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import NotRequired, TypedDict, cast

from invoke import Context, task

from . import util


class Classification(StrEnum):
    """A node's (or flag's) risk tier — see _RUBRIC for what each one means. Matches the
    "classification" enum values in _SCHEMA/_RECONFIRM_SCHEMA and the values stored in
    cli-allowlist/rules/*.json. needs_review and invalid aren't tiers the LLM assigns directly
    (read_only/write/dangerous/invalid are) — needs_review is applied locally by the
    dangerous-verb backstop."""

    READ_ONLY = "read_only"
    WRITE = "write"
    DANGEROUS = "dangerous"
    NEEDS_REVIEW = "needs_review"
    INVALID = "invalid"


class Source(StrEnum):
    """Where a node's classification came from — stored alongside it in cli-allowlist/rules/*.json."""

    COMMUNITY = "community"
    HEURISTIC = "heuristic"
    LLM = "llm"
    LLM_RECONFIRMED = "llm-reconfirmed"


# ---------------------------------------------------------------------------
# Shapes of the three files this pipeline reads and writes — tools.toml, help-cache/<tool>.json,
# rules/<tool>.json — plus the model's JSON answer. Required/optional split measured against the
# tracked files (2026-08-25), not guessed: `likely_invalid` is absent from caches written before
# it existed, `model` from the one heuristic-classified node, `note` from every non-interactive
# rule entry.
# ---------------------------------------------------------------------------


class ToolConfig(TypedDict, total=False):
    """One `[<tool>]` table in tools.toml — see its header comment for each knob."""

    shell_prefix: str
    skip_interactive: bool
    version_flag: str
    help_flag: str
    help_style: str
    max_depth: int
    max_nodes: int
    max_subcommands: int
    subcommands: list[str]
    no_subcommands: bool
    mode_covered: bool
    cloud_cli: bool
    global_option_prefixes: list[str]
    allow_overrides: list[str]
    ask_overrides: list[str]


Registry = dict[str, ToolConfig]


class CacheNode(TypedDict):
    """One node of a tool's extracted --help tree (help-cache/<tool>.json)."""

    help_text: str
    content_hash: str
    children: list[str]
    likely_invalid: NotRequired[bool]


class CacheEntry(TypedDict):
    interactive: bool
    version: str | None
    extracted_at: str
    nodes: dict[str, CacheNode]
    truncated: bool


class FlagRating(TypedDict):
    classification: str
    rationale: str


class RuleNode(TypedDict):
    """One classified node in rules/<tool>.json."""

    content_hash: str
    classification: str
    rationale: str
    source: str
    flags: dict[str, FlagRating]
    model: NotRequired[str]


class RuleEntry(TypedDict):
    version: str | None
    extracted_at: str | None
    classified_at: str
    reviewed: bool
    reviewed_at: str | None
    truncated: bool
    nodes: dict[str, RuleNode]
    note: NotRequired[str]


class FlagVerdict(TypedDict, total=False):
    classification: str
    rationale: str


class NodeVerdict(TypedDict, total=False):
    """What the model returns per path — every key optional, since a malformed answer is handled
    with `.get()` defaults rather than trusted."""

    classification: str
    rationale: str
    flags: dict[str, FlagVerdict]


Verdict = dict[str, NodeVerdict]


class _StructuredOutput(TypedDict):
    classifications: Verdict


class _ClaudeEnvelope(TypedDict):
    structured_output: _StructuredOutput


class _NodeProbe(TypedDict):
    """A CacheNode before its children are known — what _fetch_node hands _build_tree."""

    help_text: str
    content_hash: str
    likely_invalid: bool


class _ReconfirmCandidate(TypedDict):
    help_text: str
    tokens: set[str]
    path: str
    flag: str | None  # None for a subcommand node, the flag name for a flag-level rating


_ROOT = Path(__file__).parent.parent / "cli-allowlist"
_TOOLS_TOML = _ROOT / "tools.toml"
_HELP_CACHE_DIR = _ROOT / "help-cache"
_RULES_DIR = _ROOT / "rules"

# Machine-local mutation-tracking state, not repo content — deliberately outside cli-allowlist/
# (which is portable, shared, tracked in git) since this records what `apply` last wrote into an
# out-of-repo file on *this* machine specifically, using the same util.PULSE_STATE_DIR namespace
# util.py already uses for the same kind of machine-local state (identity.toml lives in its
# sibling PULSE_CONFIG_DIR).
_APPLIED_MANIFEST = util.PULSE_STATE_DIR / "claude-settings-applied.json"

_DEFAULT_MAX_SUBCOMMANDS = 40
_DEFAULT_MAX_NODES = 60  # total tree-node budget once max_depth > 1 (see tools.toml header)
_HELP_TIMEOUT = 10  # seconds — guards against a misbehaving or secretly-interactive tool hanging
_CLASSIFY_TIMEOUT = 150
# Per-call batch size cap. Measured empirically: 20 nodes (with per-flag candidate ratings, which
# is real added output over the old subcommand-only schema) took ~92s and ~$0.08 at Haiku — close
# enough to both the timeout and the --max-budget-usd ceiling below that a tool with 50+ new nodes
# (routine once recursion is enabled) would blow past one or the other. Chunking keeps each call
# comfortably inside both, at the cost of more fixed per-call overhead — still far cheaper than
# one call per node.
_CLASSIFY_CHUNK_SIZE = 15
_CLASSIFY_MAX_BUDGET_USD = "0.15"

# Extraction must give the same text on any machine, not whatever this machine's interactive
# shell happens to have configured. Without this, `git status --help` renders through `man`
# (needs the git-man package — silently absent on a minimal box) and a stray $PAGER/$BROWSER
# could theoretically block waiting for input despite stdin already being closed. None of this
# is hypothetical tightening: git's dependency on git-man was confirmed empirically here.
_DETERMINISTIC_ENV = {
    "PAGER": "cat",
    "MANPAGER": "cat",
    "GIT_PAGER": "cat",
    "LESS": "FRX",
    "BROWSER": "true",
    "NO_COLOR": "1",
    "CLICOLOR": "0",
}

# Verb-ish tokens that force a "needs_review" downgrade even if the LLM said read_only — checked
# against both a subcommand's full path (e.g. "network rm" -> tokens "network", "rm") and, since
# flags are verb-ish modifiers too, a candidate flag's own name (e.g. "--force" -> "force").
# Deliberately checked against the name/path itself, not the help text, to avoid false positives
# from a read-only command's help text merely mentioning "delete" while describing something else.
_DANGEROUS_VERBS = {
    "delete",
    "destroy",
    "drop",
    "rm",
    "rmi",
    "remove",
    "purge",
    "uninstall",
    "prune",
    "truncate",
    "kill",
    "drain",
    "cordon",
    "reset",
    "clean",
    "yank",
    "unpublish",
    "force",
    "wipe",
    "erase",
    "flush",
    "revoke",
    "down",
    "run",
    "exec",
    "eval",
    # flag-specific additions — not naturally subcommand-shaped, but just as dangerous as a modifier
    "recursive",
    "all",
    "yes",
    "hard",
    "global",
    "cascade",
    "overwrite",
}

# Flag-name tokens that make a flag worth asking the LLM to rate at all — most of a command's
# flags (--output, --verbose, --color) don't affect risk and would just be prompt noise rated
# "same as parent" for zero signal. This is a candidate *filter*, not a verdict — the LLM still
# decides the actual tier; a flag missing from both sets below simply isn't offered as a candidate.
_RISKY_FLAG_HINTS = _DANGEROUS_VERBS | {"no-verify", "skip-confirm", "unsafe", "delete"}
_SAFE_FLAG_HINTS = {"dry-run", "dry_run", "check", "plan-only", "plan_only", "preview", "list-only", "noop", "no-op"}

# Optional trailing ":" before the description gap — gh's cobra help nests subcommands as
# "  create:        Create a pull request" (colon right after the name), unlike git/docker's
# "  create        Create..." with no separator; confirmed empirically when gh's depth-2 discovery
# came back empty despite `gh pr --help` clearly listing create/edit/merge/etc.
_SUBCOMMAND_LINE = re.compile(r"^\s{1,4}([a-z][a-z0-9_-]{1,20})(?:,\s*[a-z][a-z0-9_-]{1,20})?:?\s{2,}\S")
_SKIP_WORDS = {"help", "completion", "version", "options", "flags", "usage"}

# GNU/POSIX-ish flag definition lines: "  -f, --force          Force the operation" or
# "      --hard              ..." or "  -n              Dry run". Heuristic, not load-bearing —
# unlike _SUBCOMMAND_LINE (which drives tree discovery), a missed or over-matched flag here just
# means a candidate isn't offered to the LLM, not a broken tree.
_FLAG_LINE = re.compile(r"^\s{1,6}(-{1,2}[A-Za-z][\w-]*(?:,\s*-{1,2}[A-Za-z][\w-]*)?)(?:[ =]\S+)?\s{2,}(\S.*)$")

_RUBRIC = """You are classifying CLI subcommands for a permission allowlist that decides which \
commands an AI coding agent may run unattended vs. which need a human to approve each time.

Categories:
- read_only: only inspects/reads/lists/describes/validates state. Cannot modify anything, local \
or remote, even indirectly.
- write: modifies state (files, cluster resources, cloud resources, packages, git history) but \
the effect is bounded, expected, and typically reversible.
- dangerous: irreversible, broad-blast-radius, bypasses a normal confirmation step, or deletes/\
destroys/force-overwrites something (force flags, deletion, destruction of infrastructure, \
publishing to a public registry, etc.)
- invalid: the path is NOT a genuine, distinct subcommand at all — its help text was extracted by \
a heuristic that can misfire, e.g. matched a line from an example/sample-output table, a config \
snippet, or other incidental text that merely *looked* like a command listing entry. Signs: the \
text under this heading doesn't describe what this specific path does, reads as data/output \
rather than documentation, or is unrelated to the path's own name. Use this rarely — only when the \
text genuinely doesn't describe a real command — not merely because a command is obscure or its \
purpose is unclear to you.

Worked example (git, already human-reviewed): status/log/diff/show/blame -> read_only. \
commit/add/checkout -> write. clean/reset --hard -> dangerous.

Each heading below is a full command path (e.g. "network rm" means `docker network rm`, a nested \
subcommand — classify it as its own command, not as a variant of "network"). Some headings are \
followed by a short "Candidate flags" list: options whose name suggests they might change the \
command's risk tier. For each one listed, rate the *absolute* resulting tier when that flag is \
used together with the base command — not a delta from the base tier. Example: `git push` is \
write; `git push --force` is dangerous. `git clean` is dangerous; `git clean --dry-run` is \
read_only. Only rate flags that are explicitly listed as candidates; do not invent others, and \
omit the "flags" key entirely for a node with no candidates listed.

Classify ONLY the exact paths given as "###" headings below — nothing else. For a well-known tool \
you may recognize many other subcommands from your own training that aren't listed here; do not \
add them. Only the paths explicitly headed below have actually been verified to exist on this \
machine's installed version — adding entries for ones you merely recognize by name wastes effort \
re-deriving output that's discarded (only the listed paths are ever read back) and risks running \
out of budget partway through the paths that were actually asked for.

Respond with a JSON object shaped {"classifications": {"<path>": {"classification": "...", \
"rationale": "<one short sentence>", "flags": {"<flag>": {"classification": "...", "rationale": \
"..."}}}}} covering every path listed below, using the exact path strings given as keys — and ONLY \
those paths, nothing more. Omit "flags" (or leave it empty) for paths with no candidate flags."""

_SCHEMA = json.dumps(
    {
        "type": "object",
        "properties": {
            "classifications": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "classification": {"type": "string", "enum": ["read_only", "write", "dangerous", "invalid"]},
                        "rationale": {"type": "string"},
                        "flags": {
                            "type": "object",
                            "additionalProperties": {
                                "type": "object",
                                "properties": {
                                    "classification": {"type": "string", "enum": ["read_only", "write", "dangerous"]},
                                    "rationale": {"type": "string"},
                                },
                                "required": ["classification", "rationale"],
                            },
                        },
                    },
                    "required": ["classification", "rationale"],
                },
            },
        },
        "required": ["classifications"],
    }
)

_RECONFIRM_RUBRIC = """You are re-examining CLI commands/flags that were tentatively classified \
read_only but overridden to "needs_review" by an automated safety check, purely because their \
name contains a word that often signals a dangerous action in OTHER contexts (delete, force, run, \
exec, all, reset, clean, ...). That check has no understanding of context — it just matches word \
tokens against a command's name — so it also catches real false positives: "gh run" is a noun (a \
GitHub Actions run), not the verb "execute"; "--all" on a listing/get command broadens what's \
*shown*, not what's destroyed, unlike "--all" on a prune/delete command which broadens what's \
*removed*.

Categories, same definitions as always:
- read_only: only inspects/reads/lists/describes/validates state, even indirectly.
- write: modifies state but boundedly, expectedly, reversibly.
- dangerous: irreversible, broad-blast-radius, bypasses confirmation, deletes/destroys/force-\
overwrites something.

Each item below shows the specific "Flagged word(s)" that triggered the automated check, plus its \
help text. Decide, from the actual help text, whether the flagged word is being used in its \
dangerous sense here or a different, safe one. This verdict is trusted directly and will NOT be \
re-checked by the same word-matching safety check that flagged it in the first place — so if the \
help text doesn't give you enough to be confident the flagged word is safe here, classify it write \
or dangerous instead of guessing read_only. Getting this wrong in the unsafe direction (calling \
something read_only that isn't) is the failure mode this whole check exists to prevent; getting it \
wrong in the safe direction (leaving something at write/dangerous that was actually fine) just \
means one more command still prompts for approval, which is the harmless default anyway.

Respond with a JSON object shaped {"classifications": {"<key>": {"classification": "...", \
"rationale": "<one short sentence, mention the flagged word>"}}} covering every key listed below, \
using the exact key strings given."""

_RECONFIRM_SCHEMA = json.dumps(
    {
        "type": "object",
        "properties": {
            "classifications": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "classification": {"type": "string", "enum": ["read_only", "write", "dangerous"]},
                        "rationale": {"type": "string"},
                    },
                    "required": ["classification", "rationale"],
                },
            },
        },
        "required": ["classifications"],
    }
)


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


_COLOR_ENABLED = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
_ANSI = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "red": "\033[31m",
    "magenta": "\033[35m",
    "gray": "\033[90m",
}
# read_only/write/dangerous mirror the rubric's own risk ordering (safe -> caution -> danger);
# needs_review and invalid aren't risk tiers at all (needs_review = ambiguous, unresolved by the
# verb backstop; invalid = not a real command) so they get their own non-risk colors instead of
# implying a place on the read_only-write-dangerous scale.
_CLASS_COLOR = {
    Classification.READ_ONLY: "green",
    Classification.WRITE: "yellow",
    Classification.DANGEROUS: "red",
    Classification.NEEDS_REVIEW: "magenta",
    Classification.INVALID: "gray",
}


def _colorize(text: str, color: str | None) -> str:
    if not color or not _COLOR_ENABLED:
        return text
    return f"{_ANSI[color]}{text}{_ANSI['reset']}"


def _wrap(prefix: str, text: str, colored_prefix: str | None = None) -> str:
    """Wrap `text` to the terminal width with a hanging indent under `prefix`, so a long
    rationale reads as one aligned block instead of running to the terminal edge and wrapping
    back to column 0 (the default behavior of a plain f-string print, which reads as a flat wall
    of text once trees got deep enough for rationales to routinely exceed one line).

    `prefix` must be the plain (uncolored) text — width/indent math needs the *visible* length,
    and ANSI escape codes aren't zero-width to textwrap, so coloring the string handed to
    initial_indent would miscalculate every wrap. Pass `colored_prefix` (same visible text, with
    escape codes) separately and it's swapped in after wrapping, only on the first line — the
    rationale itself is deliberately never colored, only the name/classification are."""
    width = max(shutil.get_terminal_size(fallback=(100, 24)).columns - 1, 40)
    wrapped = textwrap.fill(
        text,
        width=width,
        initial_indent=prefix,
        subsequent_indent=" " * len(prefix),
        break_long_words=False,
        break_on_hyphens=False,
    )
    if colored_prefix and _COLOR_ENABLED:
        wrapped = colored_prefix + wrapped[len(prefix) :]
    return wrapped


def _node_prefix(indent: str, label: str, classification: Classification, suffix: str = "") -> tuple[str, str]:
    """(plain, colored) prefix pair for a node/flag line: name in bold, classification in its
    tier color, everything else (indent, punctuation, source annotation) left in the terminal's
    default color so it doesn't compete for attention with the two things worth scanning for."""
    plain = f"{indent}{label}: {classification}{suffix} — "
    colored = (
        f"{indent}{_colorize(label, 'bold')}: {_colorize(classification, _CLASS_COLOR.get(classification))}{suffix} — "
    )
    return plain, colored


def _load_registry() -> Registry:
    return cast(Registry, util.load_toml(_TOOLS_TOML))


def _load_rule(tool: str) -> RuleEntry | None:
    path = _RULES_DIR / f"{tool}.json"
    return cast(RuleEntry, util.load_json(path)) if path.exists() else None


def _save_rule(tool: str, entry: RuleEntry) -> None:
    _RULES_DIR.mkdir(parents=True, exist_ok=True)
    (_RULES_DIR / f"{tool}.json").write_text(json.dumps(entry, indent=2, sort_keys=True) + "\n")


def _load_all_rules() -> dict[str, RuleEntry]:
    """Every reviewed-or-not rule, keyed by tool — one file per tool under cli-allowlist/rules/
    so a single tool's re-classification only touches that tool's diff, not one monolithic file."""
    if not _RULES_DIR.exists():
        return {}
    return {p.stem: cast(RuleEntry, util.load_json(p)) for p in sorted(_RULES_DIR.glob("*.json"))}


def _load_cache(tool: str) -> CacheEntry | None:
    path = _HELP_CACHE_DIR / f"{tool}.json"
    return cast(CacheEntry, util.load_json(path)) if path.exists() else None


def _help_text(cache_nodes: dict[str, CacheNode], path: str) -> str:
    """A node's cached --help text, "" when the cache has no such node."""
    node = cache_nodes.get(path)
    return node["help_text"] if node else ""


def _save_cache(tool: str, data: CacheEntry) -> None:
    _HELP_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (_HELP_CACHE_DIR / f"{tool}.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def _run_capture(cmd: list[str], timeout: int = _HELP_TIMEOUT) -> str:
    """Run a command, return combined stdout+stderr, "" on timeout/missing binary. Never raises
    on nonzero exit — --help conventionally exits nonzero on plenty of tools."""
    env = {**os.environ, **_DETERMINISTIC_ENV}
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, env=env, stdin=subprocess.DEVNULL, check=False
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""
    return (result.stdout + result.stderr).strip()


def _invocation(tool: str, args: list[str], cfg: ToolConfig) -> list[str]:
    """Build the argv for `tool args...`, honoring the shell_prefix escape hatch (nvm-style tools
    that only exist as a shell function, not a binary on PATH)."""
    prefix = cfg.get("shell_prefix")
    if not prefix:
        return [tool, *args]
    inner = " ".join([tool, *args])
    return ["bash", "-c", f"{prefix} && {inner}"]


def _sub_args(path: list[str] | None, help_flag: str, help_style: str) -> list[str]:
    """Build the --help-flag args for a given command path (None = tool's own top-level help).
    help_style="prefix" puts the flag before the path (go: `go help list`, since `go list --help`
    is just a stub pointing back at that); default "suffix" puts it after (`git status -h`,
    `docker network create --help`)."""
    flag_parts = help_flag.split()
    if path is None:
        return flag_parts
    return [*flag_parts, *path] if help_style == "prefix" else [*path, *flag_parts]


def _tool_version(tool: str, version_flag: str, cfg: ToolConfig | None = None) -> str:
    """Return a stable per-version string for cache invalidation. Not always line 1: eza's
    --version prints its tagline first and the actual "v0.18.2 [+git]" on line 2 — a tagline
    never changes across upgrades, which would silently defeat staleness detection. Preferring
    the first line that contains a digit catches that case generally, not just for eza."""
    text = _run_capture(_invocation(tool, version_flag.split(), cfg or {}))
    if not text:
        return ""
    for line in text.splitlines():
        if any(ch.isdigit() for ch in line):
            return line.strip()
    return text.splitlines()[0].strip()


def _discover_subcommands(
    help_text: str, max_n: int, tool: str | None = None, path: list[str] | None = None
) -> list[str]:
    """Primary discovery: a "Commands:"-style heading (`_SUBCOMMAND_LINE`), same as the top level.
    A nested command's own help text often doesn't have one — confirmed empirically on git, whose
    `git remote -h` / `git stash -h` / etc. render as docopt-style usage synopses ("or: git remote
    add ...") instead. When nothing matches and a tool+path is given (i.e. this is a nested-level
    probe, not the tool's top-level help), fall back to parsing verbs out of those synopsis lines."""
    seen: list[str] = []
    for line in help_text.splitlines():
        m = _SUBCOMMAND_LINE.match(line)
        if not m:
            continue
        word = m.group(1)
        if word in _SKIP_WORDS or word in seen:
            continue
        seen.append(word)
        if len(seen) >= max_n:
            break
    if seen or not (tool and path):
        return seen
    return _discover_from_synopsis(help_text, tool, path, max_n)


_SYNOPSIS_LINE = re.compile(r"^\s*(?:usage:|or:)\s+(.*)$", re.IGNORECASE)


def _discover_from_synopsis(help_text: str, tool: str, path: list[str], max_n: int) -> list[str]:
    """Fallback for docopt-style "usage: git remote add ..." / "or: git remote [-v] show ..."
    lines: confirm the synopsis starts with the known tool+path, skip over any bracketed flag
    groups that follow (possibly nested, e.g. "[push [-p | --patch] ...]"), and take the next
    token as a discovered verb *only if* it's a bare identifier. Fails closed, not open: a
    positional-arg placeholder token right after the prefix (`<pathspec>`, `<commit>...<commit>`)
    means this command takes arguments directly rather than a further subcommand — e.g. `git add`,
    `git branch <name>`, `git diff <commit>` — and a `(good|bad)`-style required-alternation group
    is skipped rather than expanded, since a missed child (bisect's `good`/`bad`) is a minor gap
    but misparsing `<pathspec>` as a verb named "pathspec" would fabricate a node that isn't real.
    Case-sensitive on purpose: docker's usage strings write positional-arg placeholders in bare
    ALL-CAPS (`docker diff CONTAINER`, no `<>`/`[]` at all) rather than git's `<angle-bracket>`
    style — a real subcommand verb is always lowercase in these synopses, so requiring literal
    lowercase rejects CONTAINER/IMAGE/NETWORK-style placeholders without needing a docker-specific
    special case."""
    prefix = [tool, *path]
    seen: list[str] = []
    bare_word = re.compile(r"^[a-z][a-z0-9-]*$")
    for line in help_text.splitlines():
        m = _SYNOPSIS_LINE.match(line)
        if not m:
            continue
        tokens = m.group(1).split()
        if tokens[: len(prefix)] != prefix:
            continue
        rest = tokens[len(prefix) :]
        i = 0
        while i < len(rest) and rest[i].startswith("["):
            depth = rest[i].count("[") - rest[i].count("]")
            i += 1
            while depth > 0 and i < len(rest):
                depth += rest[i].count("[") - rest[i].count("]")
                i += 1
        if i >= len(rest):
            continue
        wm = bare_word.match(rest[i])
        if not wm:
            continue
        word = wm.group(0).lower()
        if word in _SKIP_WORDS or word in seen:
            continue
        seen.append(word)
        if len(seen) >= max_n:
            break
    return seen


def _parse_flags(help_text: str) -> dict[str, str]:
    """Deterministic, best-effort: pull "-x, --flag  description" style lines out of help text
    already captured for a node (no extra invocation — flags don't have their own --help). Not
    load-bearing like _discover_subcommands: a missed flag just means one fewer candidate offered
    to the classifier, not a broken tree."""
    flags: dict[str, str] = {}
    for line in help_text.splitlines():
        m = _FLAG_LINE.match(line)
        if not m:
            continue
        names, desc = m.group(1), m.group(2).strip()
        primary = names.split(",")[-1].strip().split("=")[0]
        if primary not in flags:
            flags[primary] = desc[:200]
    return flags


def _flag_tokens(flag: str) -> set[str]:
    return set(re.split(r"[-_]+", flag.lstrip("-").lower()))


def _flag_matches_hints(flag: str, hints: set[str]) -> bool:
    """Whole-name match first, token match second. A hint set can contain multi-word phrases
    ("dry-run", "plan-only") specifically to be checked as a unit — splitting those into tokens
    the same way a flag is split would silently defeat them: "dry-run" -> {"dry", "run"}, and
    "run" alone is a legitimate single-word hint too (dangerous, in _DANGEROUS_VERBS), so a
    token-only comparison can't tell "the whole name is the safe phrase dry-run" apart from "one
    of its tokens happens to also be the dangerous word run". Checking the un-split name against
    the hint set first resolves that before tokenizing loses the distinction."""
    normalized = flag.lstrip("-").lower()
    if normalized in hints or normalized.replace("_", "-") in hints:
        return True
    return bool(_flag_tokens(flag) & hints)


def _candidate_flags(help_text: str) -> dict[str, str]:
    """Which of a node's flags are worth sending to the LLM for a rating — pre-filtered by name
    against risky/safe hints so a 30-flag command doesn't burn prompt budget rating
    --output/--verbose/--color, which never affect risk tier."""
    hints = _RISKY_FLAG_HINTS | _SAFE_FLAG_HINTS
    return {f: d for f, d in _parse_flags(help_text).items() if _flag_matches_hints(f, hints)}


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _dangerous_path_tokens(name_or_path: str) -> set[str]:
    """The specific _DANGEROUS_VERBS token(s) that matched, not just whether any did — reused by
    the needs_review backstop (which only needs the bool) and by `reconfirm` (which needs to tell
    the model exactly which word triggered suspicion, so it can judge whether that word's
    dangerous sense actually applies here)."""
    tokens = re.split(r"[\s\-_/]+", name_or_path.lower())
    return {t for t in tokens if t in _DANGEROUS_VERBS}


def _is_dangerous_path(name_or_path: str) -> bool:
    return bool(_dangerous_path_tokens(name_or_path))


def _dangerous_flag_tokens(flag: str) -> set[str]:
    """Flag counterpart of _dangerous_path_tokens — same safe-hint tiebreak as _looks_dangerous_flag
    (see its docstring: "--dry-run" token-matches "run" in _DANGEROUS_VERBS, added for `nvm run`
    as a subcommand, and needs the whole-name safe-hint check to not be wrongly flagged), just
    returning the matched token(s) instead of a bool."""
    if _flag_matches_hints(flag, _SAFE_FLAG_HINTS):
        return set()
    return _flag_tokens(flag) & _DANGEROUS_VERBS


def _looks_dangerous_flag(flag: str) -> bool:
    return bool(_dangerous_flag_tokens(flag))


def _fetch_node(
    name: str, cfg: ToolConfig, path: list[str], parent_hash: str, sibling_count: int, help_flag: str, help_style: str
) -> tuple[_NodeProbe, bool]:
    """Fetch one node's --help text and compute its hash/likely-invalid metadata. Returns
    (node_entry, duplicates_parent) — node_entry has everything `_build_tree` stores except
    `children` (only known after this node's own child-discovery, which happens in the caller);
    duplicates_parent isn't stored but the caller needs it to decide whether to recurse.

    A subcommand that doesn't actually exist can silently fall back to printing its parent's help
    instead of erroring — confirmed twice, at two different tree levels: `docker trust --help`
    (root-level, deprecated in this docker build) dumps the whole `docker --help`; `helm list
    maudlin-arachnid --help` (an auto-discovered depth-2 "child" that was never a real subcommand
    — `helm list --help`'s text includes a sample-output table row that happens to match the
    "Commands:"-heading line shape) dumps `helm list --help` verbatim. Recursing into either would
    treat the parent's full content as this node's children — for `trust` that would mean docker's
    entire command surface, blowing the node budget.

    Whether duplicate content also means "not a real command" turns out to hinge on group size,
    not on whether the name came from an explicit list vs auto-discovery — tried that distinction
    first and it was wrong: git's `submodule <verb> -h` returns the exact same combined usage
    block for 9 of its 10 auto-discovered children (only `absorbgitdirs` differs), and all 9 are
    real, safety-distinct commands (`submodule deinit` is very different from `submodule sync`)
    that just happen to share undifferentiated help text — the same situation as nvm's shell
    function, just one level deeper. What actually distinguishes that from `helm list
    maudlin-arachnid` is corroboration: submodule's verbs were discovered *together*, 10 in one
    batch, from a scoped signal (git's own usage synopsis literally lists each of them as an
    alternative). `maudlin-arachnid` was the *only* child found for `list` at all — `helm list`
    has no real subcommands, so nothing else in its help text matched, leaving one isolated,
    uncorroborated match that also happens to duplicate its parent. A lone duplicate has nothing
    backing it up; a duplicate inside a multi-member group discovered the same way as its
    non-duplicating siblings does."""
    text = _run_capture(_invocation(name, _sub_args(path, help_flag, help_style), cfg))
    node_hash = _hash_text(text)
    duplicates_parent = bool(text) and node_hash == parent_hash
    likely_invalid = duplicates_parent and sibling_count == 1
    node_entry: _NodeProbe = {"help_text": text, "content_hash": node_hash, "likely_invalid": likely_invalid}
    return node_entry, duplicates_parent


def _build_tree(
    name: str, cfg: ToolConfig, top_help: str, help_flag: str, help_style: str
) -> tuple[dict[str, CacheNode], bool]:
    """Breadth-first walk of the subcommand tree, up to tools.toml's max_depth/max_nodes for this
    tool (both default to today's single-level behavior — see tools.toml's header comment). Only
    the root level honors an explicit `subcommands =` override; deeper levels are always
    auto-discovered from each node's own --help text, since hand-listing e.g. every `docker
    network` child would just be re-deriving what --help already says.

    Returns (nodes, truncated) where nodes is path-string -> {help_text, content_hash, children,
    likely_invalid} and truncated is True if max_nodes cut the walk off before the tree was fully
    explored (breadth-first, so this means "deepest/least-common branches missing", not "random
    gaps")."""
    max_depth = cfg.get("max_depth", 1)
    max_nodes = cfg.get("max_nodes", _DEFAULT_MAX_NODES)
    breadth_cap = cfg.get("max_subcommands", _DEFAULT_MAX_SUBCOMMANDS)

    explicit = cfg.get("subcommands")
    roots = explicit if explicit is not None else _discover_subcommands(top_help, breadth_cap)

    nodes: dict[str, CacheNode] = {}
    truncated = False
    top_hash = _hash_text(top_help)
    # (path, depth, parent_hash, sibling_count) — parent_hash detects "doesn't really exist, help
    # fell back to the parent's text" (see _fetch_node); sibling_count is how many children were
    # discovered together in the same batch as this one, which is what actually distinguishes a
    # real-but-undifferentiated command from a discovery false positive (see _fetch_node — the
    # short version: a *lone* duplicate is suspicious, a duplicate within a larger corroborated
    # group isn't).
    queue: list[tuple[list[str], int, str, int]] = [([r], 1, top_hash, len(roots)) for r in roots]

    while queue:
        if len(nodes) >= max_nodes:
            truncated = True
            break
        path, depth, parent_hash, sibling_count = queue.pop(0)
        key = " ".join(path)
        node_entry, duplicates_parent = _fetch_node(name, cfg, path, parent_hash, sibling_count, help_flag, help_style)
        child_names = (
            _discover_subcommands(node_entry["help_text"], breadth_cap, tool=name, path=path)
            if depth < max_depth and not duplicates_parent
            else []
        )
        nodes[key] = {**node_entry, "children": [f"{key} {c}" for c in child_names]}
        queue.extend(([*path, c], depth + 1, node_entry["content_hash"], len(child_names)) for c in child_names)

    return nodes, truncated


def _extract_one(name: str, cfg: ToolConfig | None, force: bool) -> None:
    """Extract+cache one tool's --help tree, or mark it interactive-only/not-installed/unchanged
    as appropriate — the per-tool body of extract()'s loop."""
    if cfg is None:
        print(f"[allowlist] {name}: not in tools.toml — skipping")
        return
    # shell_prefix tools (nvm) are shell functions, not binaries — `which` can't see them,
    # so existence is judged by whether the extraction call actually produces output instead.
    if not cfg.get("shell_prefix") and not util.command_exists(name):
        print(f"[allowlist] {name}: not installed — skipping")
        return

    if cfg.get("skip_interactive"):
        _save_cache(
            name, {"interactive": True, "version": None, "extracted_at": _now(), "nodes": {}, "truncated": False}
        )
        print(f"[allowlist] {name}: interactive-only, no help captured")
        return

    version_flag = cfg.get("version_flag", "--version")
    version = _tool_version(name, version_flag, cfg)

    cached = _load_cache(name)
    if not force and version and cached is not None and cached["version"] == version:
        print(f"[allowlist] {name}: unchanged ({version}) — skipped")
        return

    help_flag = cfg.get("help_flag", "--help")
    help_style = cfg.get("help_style", "suffix")  # "prefix": <tool> <flag> <sub> (go); default: <tool> <sub> <flag>

    top_help = _run_capture(_invocation(name, _sub_args(None, help_flag, help_style), cfg))

    if not top_help and not cfg.get("shell_prefix"):
        print(f"[allowlist] {name}: no output from --help — skipping (installed but unresponsive?)")
        return

    truncated = False
    nodes: dict[str, CacheNode]
    if cfg.get("no_subcommands"):
        nodes = {
            _NO_SUBCOMMANDS_KEY: {
                "help_text": top_help,
                "content_hash": _hash_text(top_help),
                "children": [],
                "likely_invalid": False,
            }
        }
    else:
        nodes = {
            _TOP_HELP_KEY: {
                "help_text": top_help,
                "content_hash": _hash_text(top_help),
                "children": [],
                "likely_invalid": False,
            }
        }
        tree_nodes, truncated = _build_tree(name, cfg, top_help, help_flag, help_style)
        nodes.update(tree_nodes)

    if cfg.get("shell_prefix") and not any(n["help_text"] for n in nodes.values()):
        print(f"[allowlist] {name}: no output at all — likely not installed on this machine, skipping")
        return

    _save_cache(
        name,
        {
            "interactive": False,
            "version": version,
            "extracted_at": _now(),
            "nodes": nodes,
            "truncated": truncated,
        },
    )
    classifiable = len([k for k in nodes if k != _TOP_HELP_KEY])
    note = " [truncated at max_nodes — increase tools.toml's max_nodes for this tool if needed]" if truncated else ""
    print(f"[allowlist] {name}: extracted ({version or 'unknown version'}, {classifiable} node(s)){note}")


@task
def extract(c: Context, tool: str | None = None, force: bool = False):
    """Capture --help text per registered tool (tools.toml), recursing into the subcommand tree
    for any tool with max_depth > 1. Skips any tool whose --version output hasn't changed since
    the last successful extract, unless --force."""
    registry = _load_registry()
    names = [tool] if tool else sorted(registry)
    for name in names:
        _extract_one(name, registry.get(name), force)


_NO_SUBCOMMANDS_KEY = "*"  # nodes dict key for a flat, no-subcommand-tree tool's single verdict
_TOP_HELP_KEY = "_top"  # nodes dict key for the tool's own top-level --help text (not classifiable)
_FLAT_KEY = "_default_"


def _build_prompt(tool: str, nodes: dict[str, CacheNode], top_help: str) -> str:
    if list(nodes) == [_NO_SUBCOMMANDS_KEY]:
        # No subcommand tree — first attempt asked the model to classify a heading literally
        # named "*", which it read as "find distinct things to classify" and broke a flags-heavy
        # --help into individual flag verdicts instead of one verdict for the tool. Ask explicitly
        # for a single verdict under a fixed, unambiguous key instead.
        return (
            f"{_RUBRIC}\n\nTool: {tool}\n\n"
            f"This tool has no subcommands — it's invoked as a single flat command "
            f"(`{tool} [options] ...`), not `{tool} <subcommand> ...`. Its --help text is below. "
            f"Ignore informational flags like --help/--version — judge the tool's own primary "
            f'purpose when run normally. Respond with exactly one entry in "classifications", '
            f'keyed literally "{_FLAT_KEY}", covering the tool as a whole (omit "flags").\n\n'
            f"--help output:\n{nodes['*']['help_text'][:1500]}\n"
        )

    parts = [_RUBRIC, "", f"Tool: {tool}", ""]
    if top_help:
        parts.append(
            f"Top-level --help (context only — this is not itself something to classify):\n{top_help[:1000]}\n"
        )
    for path, node in nodes.items():
        parts.append(f"### {path}\n{node['help_text'][:800]}")
        candidates = _candidate_flags(node["help_text"])
        if candidates:
            flag_lines = "\n".join(f"  {f}: {d}" for f, d in candidates.items())
            parts.append(f'Candidate flags for "{path}" — rate ONLY these:\n{flag_lines}')
        parts.append("")
    return "\n".join(parts)


def _classify_via_claude(prompt: str, model: str, schema: str = _SCHEMA) -> Verdict | None:
    with tempfile.TemporaryDirectory(prefix="pulse-allowlist-") as scratch:
        try:
            result = subprocess.run(
                [
                    "claude",
                    "-p",
                    "--strict-mcp-config",
                    "--disallowedTools",
                    "Edit,Write,NotebookEdit,Bash,Agent",
                    "--model",
                    model,
                    "--output-format",
                    "json",
                    "--json-schema",
                    schema,
                    "--max-budget-usd",
                    _CLASSIFY_MAX_BUDGET_USD,
                    prompt,
                ],
                capture_output=True,
                text=True,
                timeout=_CLASSIFY_TIMEOUT,
                cwd=scratch,
                stdin=subprocess.DEVNULL,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return None
    if result.returncode != 0:
        return None
    try:
        envelope = cast(_ClaudeEnvelope, util.parse_json(result.stdout))
        return envelope["structured_output"]["classifications"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def _strip_tool_prefix(verdict: Verdict, tool: str) -> Verdict:
    """Defensive normalization: the model occasionally echoes the tool name back as part of a
    key ("gh run list" instead of the requested "run list") even though the rubric asks for the
    exact key strings given back unchanged — confirmed happening on a real `reconfirm` call for
    gh, where every one of 6 correctly-classified items was silently discarded because the lookup
    by the original (unprefixed) key came back empty. Stripping a leading "<tool> " prefix when
    present costs nothing when the model behaved, and recovers the result when it didn't."""
    prefix = f"{tool} "
    return {(k.removeprefix(prefix)): v for k, v in verdict.items()}


def _resolve_flat_verdict(verdict: Verdict) -> Verdict:
    """Map the model's single _FLAT_KEY answer back to "*". If it ignored the instruction and
    broke the tool into multiple entries anyway (observed once, on a flags-heavy --help text),
    fall back to the most cautious of whatever it returned rather than an arbitrary one —
    consistent with the verb backstop's "when in doubt, don't assume safe" stance."""
    if _FLAT_KEY in verdict:
        return {_NO_SUBCOMMANDS_KEY: verdict[_FLAT_KEY]}
    if not verdict:
        return verdict
    order: dict[str, int] = {Classification.READ_ONLY: 0, Classification.WRITE: 1, Classification.DANGEROUS: 2}
    worst = max(verdict.values(), key=lambda v: order.get(v.get("classification", ""), 1))
    return {
        _NO_SUBCOMMANDS_KEY: {
            "classification": worst.get("classification", Classification.WRITE),
            "rationale": f"inferred conservatively — model split this flat tool into "
            f"multiple parts instead of one verdict ({worst.get('rationale', '')})",
        }
    }


def _classify_flag_result(flag: str, result: FlagVerdict, base_classification: str) -> FlagRating:
    classification = result.get("classification", base_classification)
    if classification == Classification.READ_ONLY and _looks_dangerous_flag(flag):
        classification = Classification.NEEDS_REVIEW
    return {"classification": classification, "rationale": result.get("rationale", "")}


def _diff_nodes(
    classifiable_keys: list[str], cache_nodes: dict[str, CacheNode], existing_nodes: dict[str, RuleNode], force: bool
) -> tuple[dict[str, CacheNode], dict[str, RuleNode], dict[str, CacheNode]]:
    """Bucket each classifiable node into (to_classify, carried, new_invalid) by comparing this
    extraction's content hash against the last classification's.

    Nodes _build_tree already flagged as likely bogus (auto-discovered, byte-identical to their
    parent's help text) skip the LLM entirely — deterministic, free, and more reliable than asking
    a model to notice the same thing. They still go through the same unchanged-since-last-run
    check as everything else, just compared against "was this already recorded as invalid with
    this exact content" instead of a normal classification."""
    to_classify: dict[str, CacheNode] = {}
    carried: dict[str, RuleNode] = {}
    new_invalid: dict[str, CacheNode] = {}
    for key in classifiable_keys:
        node = cache_nodes[key]
        prior = existing_nodes.get(key)
        # Community-seeded nodes (source: "community" — see tools.toml's header) are always
        # swept back into to_classify, content hash notwithstanding: the seed was a reasonable
        # starting point before this pipeline had its own rubric, flag ratings, or backstops,
        # but it's external data with no ongoing reason to keep trusting over a fresh judgment
        # from the same model/rubric everything else here is classified with. This makes
        # community data self-liquidating — every classify() run upgrades whatever's left to
        # real LLM output, a few nodes at a time, at no cost to already-fresh nodes.
        is_community = prior is not None and prior.get("source") == Source.COMMUNITY
        unchanged = (
            not force and not is_community and prior is not None and prior.get("content_hash") == node["content_hash"]
        )
        if node.get("likely_invalid"):
            if unchanged and prior is not None and prior.get("classification") == Classification.INVALID:
                carried[key] = prior
            else:
                new_invalid[key] = node
        elif unchanged and prior is not None:
            carried[key] = prior
        else:
            to_classify[key] = node
    return to_classify, carried, new_invalid


def _run_classification(name: str, to_classify: dict[str, CacheNode], top_help: str, model: str) -> tuple[Verdict, int]:
    """Classify to_classify's nodes via chunked LLM calls. Returns (verdict, failed_chunks) —
    verdict only has entries for chunks that succeeded; failed_chunks counts how many didn't.

    Chunked, not one call for the whole tool: a call covering 50+ nodes (routine once recursion is
    on) risks both the timeout and --max-budget-usd ceiling — see _CLASSIFY_CHUNK_SIZE's comment
    for the measurement that drove this."""
    verdict: Verdict = {}
    failed_chunks = 0
    items = list(to_classify.items())
    for i in range(0, len(items), _CLASSIFY_CHUNK_SIZE):
        chunk = dict(items[i : i + _CLASSIFY_CHUNK_SIZE])
        chunk_verdict = _classify_via_claude(_build_prompt(name, chunk, top_help), model=model)
        if chunk_verdict is None:
            failed_chunks += 1
            continue
        if list(chunk) == [_NO_SUBCOMMANDS_KEY]:
            chunk_verdict = _resolve_flat_verdict(chunk_verdict)
        verdict.update(_strip_tool_prefix(chunk_verdict, name))
    return verdict, failed_chunks


def _assemble_new_nodes(
    carried: dict[str, RuleNode],
    new_invalid: dict[str, CacheNode],
    to_classify: dict[str, CacheNode],
    verdict: Verdict,
    existing_nodes: dict[str, RuleNode],
    model: str,
) -> dict[str, RuleNode]:
    """Merge carried-forward nodes, newly-flagged-invalid nodes, and this run's LLM verdicts into
    the final nodes dict to save."""
    new_nodes = dict(carried)
    for key, node in new_invalid.items():
        new_nodes[key] = {
            "content_hash": node["content_hash"],
            "classification": Classification.INVALID,
            "rationale": "Auto-discovered but duplicates its parent's help text verbatim — "
            "likely a false-positive match (e.g. example/sample output mistaken "
            "for a subcommand listing), not a real distinct command.",
            "source": Source.HEURISTIC,
            "flags": {},
        }
    for key, node in to_classify.items():
        result = verdict.get(key)
        if result is None:
            # A failed chunk (or the model dropping a key) must not silently lose this node's
            # existing coverage — confirmed as a real bug, not hypothetical: a single failed
            # gh chunk during the community-data resweep (community nodes are always forced
            # into to_classify, so they're never in `carried`) dropped 21 root-level nodes
            # from rules/gh.json entirely, with no fallback. Keep whatever was there before;
            # it's still not in `carried` so it stays eligible for to_classify next run too.
            if key in existing_nodes:
                new_nodes[key] = existing_nodes[key]
            continue
        classification = result.get("classification", Classification.WRITE)
        if classification == Classification.INVALID:
            new_nodes[key] = {
                "content_hash": node["content_hash"],
                "classification": Classification.INVALID,
                "rationale": result.get("rationale", ""),
                "source": Source.LLM,
                "model": model,
                "flags": {},
            }
            continue
        if classification == Classification.READ_ONLY and _is_dangerous_path(key):
            classification = Classification.NEEDS_REVIEW
        flags = {
            flag: _classify_flag_result(flag, fresult, classification)
            for flag, fresult in (result.get("flags") or {}).items()
        }
        new_nodes[key] = {
            "content_hash": node["content_hash"],
            "classification": classification,
            "rationale": result.get("rationale", ""),
            "source": Source.LLM,
            "model": model,
            "flags": flags,
        }
    return new_nodes


@task
def classify(c: Context, tool: str | None = None, force: bool = False, model: str = "haiku"):
    """Classify each tool's extracted nodes (subcommands, and nested subcommands for any tool
    with max_depth > 1) as read_only/write/dangerous via a headless `claude -p` call, isolated in
    a scratch cwd outside the repo with file/exec tools disallowed. Each node also gets its
    risk-relevant flags (--force, --dry-run, ...) rated in the same call. Diffing is per-node, by
    content hash: only new or changed nodes are ever re-sent to the model — unchanged nodes
    (the overwhelming majority on a routine re-run) are carried forward from the last
    classification untouched, which is what keeps repeat runs close to free even as trees grow."""
    if not util.command_exists("claude"):
        print("[allowlist] claude CLI not found — nothing to classify")
        return

    registry = _load_registry()
    names = [tool] if tool else sorted(registry)

    for name in names:
        cached = _load_cache(name)
        if cached is None:
            print(f"[allowlist] {name}: no extracted help — run `inv allowlist.extract --tool={name}` first")
            continue

        if cached.get("interactive"):
            _save_rule(
                name,
                {
                    "version": None,
                    "extracted_at": cached.get("extracted_at"),
                    "classified_at": _now(),
                    "reviewed": True,
                    "reviewed_at": _now(),
                    "note": "interactive-only TUI, no non-interactive command surface to classify",
                    "truncated": False,
                    "nodes": {},
                },
            )
            print(f"[allowlist] {name}: interactive-only — marked reviewed, nothing to classify")
            continue

        cache_nodes = cached["nodes"]
        classifiable_keys = [k for k in cache_nodes if k != _TOP_HELP_KEY]
        top_help = _help_text(cache_nodes, _TOP_HELP_KEY)

        existing = _load_rule(name)
        existing_nodes = existing["nodes"] if existing else {}

        to_classify, carried, new_invalid = _diff_nodes(classifiable_keys, cache_nodes, existing_nodes, force)

        if not to_classify and not new_invalid:
            refreshed = _version_only_refresh(existing, cached)
            if refreshed is not None:
                _save_rule(name, refreshed)
                print(
                    f"[allowlist] {name}: help unchanged, version now {cached.get('version')} — "
                    f"recorded, classification kept"
                )
                continue
            print(f"[allowlist] {name}: unchanged since last classification — skipped")
            continue

        verdict, failed_chunks = _run_classification(name, to_classify, top_help, model)

        if to_classify and not verdict:
            print(f"[allowlist] {name}: classification call failed — left as-is")
            continue
        if failed_chunks:
            missing = sum(1 for key in to_classify if key not in verdict)
            print(
                f"[allowlist] {name}: {failed_chunks} chunk(s) failed — {missing} node(s) left "
                f"unclassified, will retry on the next run"
            )

        new_nodes = _assemble_new_nodes(carried, new_invalid, to_classify, verdict, existing_nodes, model)

        _save_rule(
            name,
            {
                "version": cached.get("version"),
                "extracted_at": cached.get("extracted_at"),
                "classified_at": _now(),
                "reviewed": False,
                "reviewed_at": None,
                "truncated": cached.get("truncated", False),
                "nodes": new_nodes,
            },
        )
        flag_count = sum(len(n.get("flags", {})) for n in new_nodes.values())
        invalid_note = f", {len(new_invalid)} flagged invalid (no LLM call)" if new_invalid else ""
        print(
            f"[allowlist] {name}: classified {len(to_classify)} new/changed node(s) "
            f"({flag_count} flag rating(s) total), carried {len(carried)} unchanged{invalid_note} via {model}"
        )


def _version_only_refresh(existing: RuleEntry | None, cached: CacheEntry) -> RuleEntry | None:
    """The rule entry to save when a tool upgraded but its --help text didn't change, or None if
    there's nothing to record.

    `status` calls a tool stale by comparing the installed version against the version recorded in
    its rule entry, and `classify` only ever wrote that entry when at least one node's help text
    had actually changed. An upgrade whose help is byte-identical — a patch release, or mkdocs'
    --version merely naming a new Python path — therefore left the tool flagged STALE permanently:
    re-extract and re-classify are what STALE asks for, both had already been run, and neither
    could clear it. A flag that can't be cleared by doing what it asks is one you learn to ignore.

    Only `version`/`extracted_at` move. `nodes`, `reviewed` and `classified_at` stay put on
    purpose: the existing classification does describe this version's help (that's what identical
    text means), so resetting `reviewed` here would ask a human to re-approve a diff that doesn't
    exist — the opposite of the human gate being meaningful."""
    if not existing or existing["version"] == cached["version"]:
        return None
    return {**existing, "version": cached["version"], "extracted_at": cached["extracted_at"]}


def _build_reconfirm_prompt(tool: str, candidates: dict[str, _ReconfirmCandidate]) -> str:
    parts = [_RECONFIRM_RUBRIC, "", f"Tool: {tool}", ""]
    for key, meta in candidates.items():
        flagged = ", ".join(sorted(meta["tokens"])) or "(unknown)"
        parts.append(f"### {key}\nFlagged word(s): {flagged}\n{meta['help_text'][:800]}\n")
    return "\n".join(parts)


@task
def reconfirm(c: Context, tool: str | None = None, model: str = "haiku"):  # noqa: C901
    """Second-pass LLM reclassification for everything currently sitting at `needs_review`
    (subcommands and flags alike) — items where the model said read_only but the deterministic
    verb-token backstop (_DANGEROUS_VERBS) overrode it, because a name/flag merely *containing* a
    risky-sounding word isn't the same as it being used in its risky sense (`gh run` is a noun,
    `--all` on a listing command isn't the same `--all` as on a prune command). Unlike the first
    classify pass, this one tells the model exactly which word triggered suspicion and trusts a
    reconfirmed read_only verdict directly — the backstop doesn't re-fire on this pass's output, so
    the rubric leans on the model to be the one applying caution when the help text genuinely
    doesn't settle it (see _RECONFIRM_RUBRIC). Idempotent by construction: once an item resolves
    to write/dangerous/read_only it's no longer `needs_review`, so a re-run finds nothing left to
    do for it — no --force flag needed."""
    if not util.command_exists("claude"):
        print("[allowlist] claude CLI not found — nothing to reconfirm")
        return

    rules = _load_all_rules()
    names = [tool] if tool else sorted(rules)
    any_found = False

    for name in names:
        entry = rules.get(name)
        if entry is None:
            continue
        nodes = entry["nodes"]
        cache = _load_cache(name)
        cache_nodes = cache["nodes"] if cache else {}

        # Composite key "<path> <flag>" for flag-level items — unambiguous to parse back since a
        # real subcommand path segment never starts with "-", only a flag token does.
        candidates: dict[str, _ReconfirmCandidate] = {}
        for path, v in nodes.items():
            if v["classification"] == Classification.NEEDS_REVIEW:
                candidates[path] = {
                    "help_text": _help_text(cache_nodes, path),
                    "tokens": _dangerous_path_tokens(path),
                    "path": path,
                    "flag": None,
                }
            for flag, fv in v["flags"].items():
                if fv["classification"] == Classification.NEEDS_REVIEW:
                    candidates[f"{path} {flag}"] = {
                        "help_text": _help_text(cache_nodes, path),
                        "tokens": _dangerous_flag_tokens(flag),
                        "path": path,
                        "flag": flag,
                    }

        if not candidates:
            continue
        any_found = True

        verdict: Verdict = {}
        items = list(candidates.items())
        for i in range(0, len(items), _CLASSIFY_CHUNK_SIZE):
            chunk = dict(items[i : i + _CLASSIFY_CHUNK_SIZE])
            chunk_verdict = _classify_via_claude(
                _build_reconfirm_prompt(name, chunk),
                model=model,
                schema=_RECONFIRM_SCHEMA,
            )
            if chunk_verdict:
                verdict.update(_strip_tool_prefix(chunk_verdict, name))

        resolved = 0
        for key, meta in candidates.items():
            result = verdict.get(key)
            if result is None:
                continue
            classification = result.get("classification", Classification.NEEDS_REVIEW)
            rationale = result.get("rationale", "")
            node = nodes[meta["path"]]
            if meta["flag"] is None:
                node["classification"] = classification
                node["rationale"] = rationale
                node["source"] = Source.LLM_RECONFIRMED
            else:
                node["flags"][meta["flag"]] = {"classification": classification, "rationale": rationale}
            resolved += 1

        if resolved:
            entry["reviewed"] = False
            entry["reviewed_at"] = None
            _save_rule(name, entry)
            print(f"[allowlist] {name}: reconfirmed {resolved}/{len(candidates)} needs_review item(s)")
        else:
            print(f"[allowlist] {name}: {len(candidates)} needs_review item(s), reconfirm call failed — left as-is")

    if not any_found:
        print("[allowlist] no needs_review items found")


@task
def review(c: Context, apply_all: bool = False, only: str | None = None, tool: str | None = None):  # noqa: C901
    """Show tools with unreviewed classifications (new or changed since the last reviewed
    snapshot) and, on confirmation, mark them reviewed. Nothing in `render` trusts an unreviewed
    entry, so this is the human gate before anything downstream sees a tool's rules. Per-tool, not
    per-node: there's no mechanism to individually override one node's classification without
    reclassifying, which is why needs_review entries stay excluded even after their tool is
    marked reviewed (tools.toml's `allow_overrides`/`ask_overrides` shape what `render` emits for
    a verb, but never the verdict on disk).

    --only=dangerous,needs_review narrows the per-node list to just those classification tiers
    (comma-separated) — useful for triaging a large tree (docker/gh run 150+ nodes) without
    reading past every read_only entry first. Omit for the full list. `invalid` entries and the
    approval prompt are unaffected by the filter either way.

    --tool=git reviews just that one tool, same flag as extract/classify. Needed whenever another
    tool is *deliberately* pending (`sed`, `inv` — see contributing/cli-allowlist.md): `--apply-all`
    without it would mark those reviewed too, and from a non-TTY (an agent's Bash tool) the
    per-tool confirm can't be answered at all, so `--tool=<x> --apply-all` is the only way to
    approve one tool from there without approving everything."""
    rules = _load_all_rules()
    pending = {name: entry for name, entry in rules.items() if not entry["reviewed"]}
    only_set = {t.strip() for t in only.split(",") if t.strip()} if only else None

    if tool:
        if tool not in pending:
            print(f"[allowlist] {tool}: nothing pending review")
            return
        pending = {tool: pending[tool]}

    if not pending:
        print("[allowlist] nothing pending review")
        return

    for name, entry in sorted(pending.items()):
        nodes = entry["nodes"]
        invalid = [k for k, v in nodes.items() if v["classification"] == Classification.INVALID]
        invalid_note = f", {len(invalid)} excluded as invalid" if invalid else ""
        print(f"\n[allowlist] {name} ({len(nodes)} node(s){invalid_note})")
        if note := entry.get("note"):
            print(f"  note: {note}")
        if entry["truncated"]:
            print("  note: tree truncated at max_nodes — not the tool's full command surface")
        if invalid:
            # Not classified/rendered as a real command — a discovery false positive (see
            # tools.toml/docs for the "duplicates its parent" heuristic and the LLM backstop for
            # anything that slips past it). Shown separately, not mixed into the per-node dump
            # below, since printing "classification: invalid" inline reads like a 4th risk tier
            # rather than "this isn't a command, ignore it."
            print(f"  {_colorize('invalid', 'gray')} (excluded from rules, not a real command):")
            for path in sorted(invalid):
                plain = f"    {path} ({nodes[path]['source']}) — "
                colored = f"    {_colorize(path, 'bold')} ({nodes[path]['source']}) — "
                print(_wrap(plain, nodes[path]["rationale"], colored))
        # Full paths are sorted alphabetically, which — since a path is literally "<parent>
        # <child>" — naturally clusters every node under its parent already (a child's string
        # always sorts immediately after its parent and before the parent's next sibling). Only
        # the trailing segment is printed as the label, with indentation carrying the depth, so
        # the output reads as an actual nested tree ("network" then indented "create"/"rm"/"ls")
        # instead of repeating the full path at every line ("network", "network create", "network
        # rm", ...), which just looked like a flat list once paths got mixed with unrelated ones.
        for path in sorted(nodes):
            v = nodes[path]
            if v["classification"] == Classification.INVALID:
                continue
            if only_set and v["classification"] not in only_set:
                continue
            indent = "    " + "  " * path.count(" ")
            label = path.rsplit(" ", 1)[-1]
            source = f" ({v['source']})" if v["source"] == Source.COMMUNITY else ""
            plain, colored = _node_prefix(indent, label, Classification(v["classification"]), source)
            print(_wrap(plain, v["rationale"], colored))
            for flag, fv in sorted(v["flags"].items()):
                fplain, fcolored = _node_prefix(indent + "  ", flag, Classification(fv["classification"]))
                print(_wrap(fplain, fv["rationale"], fcolored))

        approve = apply_all or util.confirm(f"Mark {name} reviewed?", default=False)
        if approve:
            entry["reviewed"] = True
            entry["reviewed_at"] = _now()
            _save_rule(name, entry)
            print(f"  -> {name} marked reviewed")
        else:
            print(f"  -> {name} left unreviewed")


def _compute_claude_rules(rules: dict[str, RuleEntry]) -> tuple[list[str], list[str]]:
    """Reviewed rules -> (allow patterns, ask patterns). Shared by `render` (prints it) and
    `apply` (merges it into ~/.claude/settings.json) so the two can never drift apart. Per-flag
    ratings aren't rendered into rules here: Claude's Bash permission rules are literal-prefix
    globs, and flags can appear in any order/position in a real invocation, so there's no clean
    prefix-based way to carve out just "this subcommand, except with --force" — that data stays
    analysis/review-only until there's an actual consumer that can act on it (e.g. a future
    PreToolUse hook, deliberately not built yet — see contributing/cli-allowlist.md).

    Any node that has children of its own is skipped entirely, regardless of its own
    classification — deliberately, not an oversight. Its own verdict describes what happens when
    it's invoked *bare* (`docker network` with no further args just lists/describes, same as any
    other read_only command), but real usage always goes through a child (`docker network rm`,
    `docker network create`), each of which already gets its own independently-correct rule.
    Rendering a rule for the bare parent too is pure noise at best: Claude Code's permission
    precedence is deny > ask > allow with no specificity tiebreak (confirmed against the actual
    docs, not assumed), so a stricter rule for a child always wins over a looser allow for its
    parent regardless — the omitted allow rule was never doing anything a more specific one wasn't
    already doing more correctly. But for a `write`/`dangerous` parent it's actively harmful, not
    just noise: that same no-specificity-tiebreak precedence means the parent's `ask` rule
    unconditionally shadows a correctly-classified `read_only` child's `allow` rule (confirmed
    live: `gh run` classified `dangerous` was shadowing `gh run view`/`gh run list`'s own
    `read_only` `allow` rules, forcing a prompt every time despite the more specific rule being
    exactly right). Skipping every parent-with-children rule, not just read_only ones, fixes that
    for every recursed tool where a parent verb is riskier than one of its own children (also hit
    `docker`, `git`, `go`, `helm`, `kubectl` — not a gh-specific bug). The rare case of the bare
    parent actually being invoked with no subcommand falls through to Claude's own default behavior
    instead (typically still a prompt), not silent approval and not silent denial.

    Two per-tool registry knobs shape the output without touching the classification itself (the
    verdict stays on disk, reviewed, and reportable — only what `render`/`apply` do with it
    changes; see tools.toml's header and contributing/cli-allowlist.md "render / apply"):

    - `mode_covered` — the tool's write/dangerous verdict is *not* rendered as an `ask` rule,
      because the active permission mode already gates it more precisely than a prefix rule can.
      `acceptEdits` auto-approves `mkdir`/`cp`/`rm`/... on paths inside the working directory or
      `additionalDirectories` and still prompts outside them; an explicit `ask` rule beats that
      mode grant (ask > allow, no specificity tiebreak — the same precedence documented below), so
      rendering one would re-prompt for every in-scope `mkdir`. Read-only nodes of such a tool
      still render as `allow` normally.
    - `global_option_prefixes` — extra `allow` patterns for read_only subcommand nodes, one per
      prefix, so `git -C <path> status` matches `Bash(git -C * status:*)` instead of falling
      through to a prompt just because a global option sits between the tool and its verb.
      Deliberately allow-only: an `ask` variant would be redundant (an unmatched mutating
      subcommand prompts anyway in every mode that prompts), and a mid-pattern `*` spans any
      number of arguments, so the allow side is an accepted, documented hole (`git -C x commit -m
      status` also matches) taken in exchange for friction-free cross-repo reads.
    - `allow_overrides` / `ask_overrides` — hand-picked rule bodies (the tool name is implied:
      `"add"` renders `Bash(git add:*)`) emitted regardless of any node's verdict. An
      `allow_overrides` entry that names a node path replaces that node's own generated rule; any
      other entry (`"restore --staged"`, `"reset * --hard"`) is simply added. Allow entries also
      get the `global_option_prefixes` variants. This is the per-verb escape hatch `review`'s
      docstring says the classification side doesn't have: `git add` *is* a write, and stays one
      on disk, but a write that only touches the index and can't lose code is not worth a prompt
      per commit — while a flag that can (`reset --hard`) gets its own ask rule, which wins by the
      same ask > allow precedence. `ask_overrides` is where the flag-shaped carve-outs the per-flag
      ratings can't express go, as literal prefix patterns.
    """
    registry = _load_registry()
    allow: list[str] = []
    ask: list[str] = []
    for name, entry in sorted(rules.items()):
        if not entry["reviewed"]:
            continue
        tool_allow, tool_ask = _tool_claude_rules(name, entry, registry.get(name, {}))
        allow.extend(tool_allow)
        ask.extend(tool_ask)
    return allow, ask


def _tool_claude_rules(name: str, entry: RuleEntry, cfg: ToolConfig) -> tuple[list[str], list[str]]:
    """One reviewed tool's (allow, ask) patterns — the per-tool body of _compute_claude_rules,
    which documents every knob applied here."""
    allow: list[str] = []
    ask: list[str] = []
    mode_covered = bool(cfg.get("mode_covered"))
    global_prefixes: list[str] = cfg.get("global_option_prefixes", [])
    allow_overrides: list[str] = cfg.get("allow_overrides", [])
    ask_overrides: list[str] = cfg.get("ask_overrides", [])
    # cloud_cli tools (gcloud, aws) never recurse — every node is necessarily a bare
    # top-level service-group command, classified on what *that* does with no args (usually
    # "shows help/lists things"), never on what its real subcommands do. That's the wrong
    # signal to allow on: confirmed for real, not hypothetical — `gcloud storage`/`sql`/
    # `secrets`/`run` all classified read_only (bare invocation just lists), but `gcloud
    # storage rm -r`/`sql instances delete`/`secrets versions destroy`/`run services delete`
    # are genuinely destructive, and there's no narrower rule to correct for it the way a
    # recursed tool's `network rm` corrects for `network`'s own allow. So: never emit an
    # allow rule for a cloud_cli tool, full stop — every node renders as ask at most,
    # regardless of its own classification. This is the one place a node's classification is
    # capped rather than trusted outright.
    is_cloud_cli = bool(cfg.get("cloud_cli"))
    cache = _load_cache(name)
    cache_nodes = cache["nodes"] if cache else {}
    for path, v in sorted(entry["nodes"].items()):
        classification = v["classification"]
        if (cache_node := cache_nodes.get(path)) and cache_node["children"]:
            continue
        if path in allow_overrides:
            continue  # rendered from the override list below, whatever the verdict says
        pattern = f"Bash({name}:*)" if path == _NO_SUBCOMMANDS_KEY else f"Bash({name} {path}:*)"
        if classification == Classification.READ_ONLY and not is_cloud_cli:
            allow.append(pattern)
            if path != _NO_SUBCOMMANDS_KEY:
                allow.extend(f"Bash({name} {prefix} {path}:*)" for prefix in global_prefixes)
        elif classification in (Classification.WRITE, Classification.DANGEROUS) or (
            classification == Classification.READ_ONLY and is_cloud_cli
        ):
            if not mode_covered:
                ask.append(pattern)
    for body in allow_overrides:
        allow.append(f"Bash({name} {body}:*)")
        allow.extend(f"Bash({name} {prefix} {body}:*)" for prefix in global_prefixes)
    ask.extend(f"Bash({name} {body}:*)" for body in ask_overrides)
    return allow, ask


def _coverage_gaps(
    rules: dict[str, RuleEntry], caches: Mapping[str, CacheEntry | None]
) -> list[tuple[str, str, str, str]]:
    """For every *reviewed* tool, find children of a node that has children of its own — i.e. a
    node whose own rule `_compute_claude_rules` now always skips, regardless of its classification
    tier — that won't themselves render any rule at all.

    Before that skip was generalized to every tier (not just read_only), a write/dangerous
    parent's own rule was still a fallback for a child that fell through the cracks: missing from
    rules.json entirely (the "chunk silently dropped nodes" class of bug documented in
    contributing/cli-allowlist.md), or stuck at `needs_review` forever (excluded from render by
    design). Now that the parent's rule is *always* skipped once it has children, a child with no
    renderable rule of its own gets literally zero coverage from this pipeline — not just a looser
    rule, none at all. `invalid` children are not gaps: that classification means "not a real
    command" (a fabricated/duplicate/error-text node), so there's nothing real to cover.

    Returns (tool, parent_path, child_path, reason) tuples; empty means every discovered child of
    every node-with-children is covered by its own read_only/write/dangerous rule. Unreviewed
    tools are skipped entirely — nothing renders for them at all yet (parent or child alike), so
    there's no partial-coverage gap to report until they're reviewed."""
    gaps: list[tuple[str, str, str, str]] = []
    for tool, entry in sorted(rules.items()):
        if not entry["reviewed"]:
            continue
        nodes = entry["nodes"]
        cache = caches.get(tool)
        cache_nodes = cache["nodes"] if cache else {}
        for path, cache_node in sorted(cache_nodes.items()):
            for child in cache_node["children"]:
                child_entry = nodes.get(child)
                if child_entry is None:
                    gaps.append((tool, path, child, "missing from rules.json"))
                elif child_entry["classification"] == Classification.NEEDS_REVIEW:
                    gaps.append((tool, path, child, "needs_review (excluded from render)"))
    return gaps


def _print_coverage_gaps(gaps: list[tuple[str, str, str, str]]) -> None:
    for tool, parent, child, reason in gaps:
        print(f"[allowlist] COVERAGE GAP: {tool} {parent!r} has child {child!r} with no rule of its own ({reason})")


def _render_claude(rules: dict[str, RuleEntry]) -> str:
    allow, ask = _compute_claude_rules(rules)
    return json.dumps({"permissions": {"allow": allow, "ask": ask}}, indent=2)


def _render_copilot(rules: dict[str, RuleEntry]) -> str:
    auto_approve: dict[str, bool] = {}
    for name, entry in sorted(rules.items()):
        if not entry["reviewed"]:
            continue
        for path, v in sorted(entry["nodes"].items()):
            key = (
                f"/^{re.escape(name)}\\b.*/"
                if path == _NO_SUBCOMMANDS_KEY
                else f"/^{re.escape(name)} {re.escape(path)}\\b.*/"
            )
            auto_approve[key] = v["classification"] == Classification.READ_ONLY
    return json.dumps({"chat.tools.terminal.autoApprove": auto_approve}, indent=2)


@task
def render(c: Context, target: str = "claude", out: str | None = None):
    """Print the reviewed subset of rules as Claude Bash(...) allow/ask rules or Copilot
    chat.tools.terminal.autoApprove regex rules. Output-only — never writes to any settings file
    (local or user-wide); that's a deliberate next step, not part of this task. `write` and
    `dangerous` entries always render as still-prompting (Claude `ask` / Copilot `false`), never
    as a hard deny — the point is a visible, still-approvable prompt, not a block."""
    rules = _load_all_rules()
    unreviewed = [name for name, entry in rules.items() if not entry["reviewed"]]
    if unreviewed:
        joined = ", ".join(sorted(unreviewed))
        print(f"[allowlist] note: {len(unreviewed)} tool(s) not yet reviewed, excluded from output: {joined}")

    gaps = _coverage_gaps(rules, {name: _load_cache(name) for name in rules})
    if gaps:
        _print_coverage_gaps(gaps)
        print(f"[allowlist] note: {len(gaps)} coverage gap(s) above — see `inv allowlist.check-coverage`")

    if target == "claude":
        text = _render_claude(rules)
    elif target == "copilot":
        text = _render_copilot(rules)
    else:
        print(f"[allowlist] unknown target {target!r} — use 'claude' or 'copilot'")
        return

    if out:
        Path(out).write_text(text + "\n")
        print(f"[allowlist] wrote {out}")
    else:
        print(text)


def _merge_rule_sets(
    existing_allow: list[str], existing_ask: list[str], allow: list[str], ask: list[str], previous: set[str]
) -> tuple[list[str], list[str], set[str], set[str], set[str], set[str]]:
    """Merge freshly-computed allow/ask rules into what's already in settings.json, keeping
    anything the user added by hand (not in `previous`, our own last-applied manifest) and
    replacing only what we wrote last time. Returns (merged_allow, merged_ask, added_allow,
    removed_allow, added_ask, removed_ask).

    Per-bucket diff, not just the flattened union — a rule moving from allow to ask (a tool's
    classification changed) is a real, meaningful change even though the union of both arrays
    contains that rule string either way. Reporting only the union would silently print "+0 -0"
    for exactly the kind of change this task most needs to surface honestly."""
    kept_allow = [r for r in existing_allow if r not in previous]
    kept_ask = [r for r in existing_ask if r not in previous]
    merged_allow = kept_allow + [r for r in allow if r not in kept_allow]
    merged_ask = kept_ask + [r for r in ask if r not in kept_ask]

    added_allow = set(merged_allow) - set(existing_allow)
    removed_allow = set(existing_allow) & previous - set(merged_allow)
    added_ask = set(merged_ask) - set(existing_ask)
    removed_ask = set(existing_ask) & previous - set(merged_ask)

    return merged_allow, merged_ask, added_allow, removed_allow, added_ask, removed_ask


@task
def apply(c: Context):
    """Merge the reviewed Bash allow/ask rules into ~/.claude/settings.json's `permissions`
    block — the only thing this task ever touches there.

    Every other key in that file (theme, effortLevel, cleanupPeriodDays, any permission rule you
    added by hand, etc.) is left completely untouched, including on repeated runs. This works by
    tracking exactly which rule strings *we* wrote last time in a local manifest
    (~/.local/state/power-user-linux-setup/claude-settings-applied.json, not repo content — see its definition
    above): on each run, only rules present in that manifest are eligible to be removed, and only
    the freshly computed set is added back. A rule that was never in our manifest — something you
    added yourself — is never touched, and a rule we used to generate but no longer do (say a
    tool's classification changed) is cleanly removed rather than left orphaned. This is what
    "the bash allow rules could be overwritten every time" means in practice: our portion is fully
    regenerated each run, nothing else is.
    """
    rules = _load_all_rules()
    unreviewed = [name for name, entry in rules.items() if not entry["reviewed"]]
    if unreviewed:
        print(
            f"[allowlist] note: {len(unreviewed)} tool(s) not yet reviewed, excluded: {', '.join(sorted(unreviewed))}"
        )

    gaps = _coverage_gaps(rules, {name: _load_cache(name) for name in rules})
    if gaps:
        _print_coverage_gaps(gaps)
        raise RuntimeError(
            f"{len(gaps)} coverage gap(s) found — refusing to apply. A node with children never renders "
            "its own rule (see _compute_claude_rules), so an uncovered child above would get zero rule at "
            "all, not just a looser one. Run `inv allowlist.check-coverage` for details, then reconfirm/"
            "classify the missing/needs_review child before re-running apply."
        )

    allow, ask = _compute_claude_rules(rules)
    new_set = set(allow) | set(ask)
    previous: set[str] = (
        set(cast(list[str], json.loads(_APPLIED_MANIFEST.read_text()))) if _APPLIED_MANIFEST.exists() else set()
    )

    settings = util.load_claude_settings()
    perms = settings.setdefault("permissions", {})
    existing_allow = perms.get("allow", [])
    existing_ask = perms.get("ask", [])

    merged_allow, merged_ask, added_allow, removed_allow, added_ask, removed_ask = _merge_rule_sets(
        existing_allow, existing_ask, allow, ask, previous
    )
    added = added_allow | added_ask
    removed = removed_allow | removed_ask
    unchanged = new_set & previous - added - removed

    if set(merged_allow) == set(existing_allow) and set(merged_ask) == set(existing_ask):
        print(f"[allowlist] {util.CLAUDE_SETTINGS}: already up to date ({len(unchanged)} rule(s))")
        return

    print(f"[allowlist] {util.CLAUDE_SETTINGS}: +{len(added)} -{len(removed)} rule(s) ({len(unchanged)} unchanged)")
    if util.DRY_RUN:
        for r in sorted(added_allow):
            print(f"  + {r} (allow)")
        for r in sorted(added_ask):
            print(f"  + {r} (ask)")
        for r in sorted(removed_allow):
            print(f"  - {r} (allow)")
        for r in sorted(removed_ask):
            print(f"  - {r} (ask)")
        return

    perms["allow"] = merged_allow
    perms["ask"] = merged_ask

    util.write_claude_settings(settings)

    _APPLIED_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    _APPLIED_MANIFEST.write_text(json.dumps(sorted(new_set), indent=2) + "\n")
    print(f"[allowlist] wrote {util.CLAUDE_SETTINGS} (backup at {util.CLAUDE_SETTINGS}.bak)")


@task
def status(c: Context):  # noqa: C901
    """Quick table: which registered tools are installed, stale (version changed since last
    classify), or still unreviewed."""
    registry = _load_registry()
    rules = _load_all_rules()

    for name in sorted(registry):
        cfg = registry[name]
        if not cfg.get("shell_prefix") and not util.command_exists(name):
            print(f"[allowlist] {name}: not installed")
            continue

        entry = rules.get(name)
        if entry is None:
            print(f"[allowlist] {name}: not yet extracted/classified")
            continue

        if cfg.get("skip_interactive"):
            print(f"[allowlist] {name}: interactive-only, reviewed={entry['reviewed']}")
            continue

        version_flag = cfg.get("version_flag", "--version")
        current_version = _tool_version(name, version_flag, cfg)
        stale = bool(current_version) and current_version != entry["version"]
        nodes = entry["nodes"]
        flags: list[str] = []
        if stale:
            flags.append("STALE")
        if not entry["reviewed"]:
            flags.append("unreviewed")
        if entry["truncated"]:
            flags.append("truncated")
        if cfg.get("cloud_cli"):
            flags.append("cloud-cli (depth capped intentionally)")
        invalid_count = sum(1 for v in nodes.values() if v["classification"] == Classification.INVALID)
        if invalid_count:
            flags.append(f"{invalid_count} invalid (excluded)")
        needs_review = sum(1 for v in nodes.values() if v["classification"] == Classification.NEEDS_REVIEW)
        if needs_review:
            flags.append(f"{needs_review} needs_review")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        depth = cfg.get("max_depth", 1)
        print(f"[allowlist] {name}: {entry['version'] or '?'} ({len(nodes)} node(s), depth={depth}){flag_str}")


@task
def check_coverage(c: Context):
    """Does every child of a node-with-children actually have its own renderable rule?

    `_compute_claude_rules` never renders a rule for a node that has children — deliberately, and
    now for every classification tier, not just read_only (see its docstring: a write/dangerous
    parent's own rule was silently shadowing its correctly-classified read_only children's allow
    rules, e.g. `gh run` hiding `gh run view`). The flip side of that fix: a parent's rule is no
    longer there as a fallback for a child that's missing from rules.json entirely, or stuck at
    `needs_review` forever — that child now gets zero rule at all instead of at least the parent's
    (looser but present) one. This walks every reviewed tool's discovered tree and flags exactly
    that gap. `apply` already refuses to run when this finds anything; run this on its own after
    `classify`/`reconfirm` to catch it before `review` even signs off, or after registering/
    recursing a new tool.
    """
    rules = _load_all_rules()
    gaps = _coverage_gaps(rules, {name: _load_cache(name) for name in rules})
    if not gaps:
        reviewed = sum(1 for entry in rules.values() if entry["reviewed"])
        print(f"[allowlist] checked {reviewed} reviewed tool(s) — every parent-with-children's child is covered")
        return
    _print_coverage_gaps(gaps)
    raise RuntimeError(f"{len(gaps)} coverage gap(s) — see output above")


# ---------------------------------------------------------------------------
# check-man-deps: not part of the extract/classify/review/apply pipeline above — a separate,
# occasional maintenance diagnostic (uses strace, slower than anything else here), run by hand
# after registering a new tool or periodically, not automatically by any other task.
# ---------------------------------------------------------------------------

_MAN_BINARIES = ["/usr/bin/man", "/bin/man", "/usr/bin/groff", "/usr/bin/troff"]


def _should_check_man_deps(name: str, cfg: ToolConfig) -> bool:
    """Skip tools explicitly opted out, and (for tools without a shell_prefix escape hatch) any
    not actually installed on this machine."""
    if cfg.get("skip_interactive"):
        return False
    return bool(cfg.get("shell_prefix")) or util.command_exists(name)


def _strace_execve_log(cmd: list[str], env: dict[str, str]) -> str | None:
    """Run cmd under strace tracing execve calls; return the log text, or None on timeout."""
    with tempfile.NamedTemporaryFile(prefix="strace-", suffix=".log") as log:
        try:
            subprocess.run(
                ["strace", "-f", "-e", "trace=execve", "-o", log.name, *cmd],
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
                stdin=subprocess.DEVNULL,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return None
        return Path(log.name).read_text()


def _man_dependency(log_text: str) -> str | None:
    """Which (if any) of the man-rendering binaries the strace log shows an execve() for."""
    return next((b for b in _MAN_BINARIES if f'execve("{b}"' in log_text), None)


@task
def check_man_deps(c: Context):
    """Does any registered tool's --help invocation secretly depend on a separately-installed
    man-page-rendering package?

    Text formatting alone can't answer this — gcloud's --help mimics a man page's NAME/SYNOPSIS/
    DESCRIPTION layout with its own self-contained renderer, no external process involved. The
    only reliable signal is watching what actually execs during the call. Checks for `man` itself
    and for `groff`/`troff` (confirmed via this same strace technique: `aws help` doesn't invoke
    `man`, but pipes through `groff -m man -T ascii` -> `troff` -> `grotty` to produce its
    formatted output — the same "only works because a package happens to be installed" risk as
    git's original git-man dependency, just a different package).

    Run after adding a tool to tools.toml, or periodically to catch a tool that changed its help
    backend. Raises (nonzero exit) if anything invokes one of these — CI-friendly, though there's
    no CI here yet.
    """
    registry = _load_registry()
    env = {**os.environ, **_DETERMINISTIC_ENV}
    offenders: list[str] = []

    for name, cfg in sorted(registry.items()):
        if not _should_check_man_deps(name, cfg):
            continue

        help_flag = cfg.get("help_flag", "--help")
        args = help_flag.split()
        cmd = _invocation(name, args, cfg)

        log_text = _strace_execve_log(cmd, env)
        if log_text is None:
            print(f"{name}: TIMEOUT (couldn't determine)")
            continue

        hit = _man_dependency(log_text)
        if hit:
            offenders.append(name)
            print(f"{name}: invokes {hit} — needs a fix (alternate flag, like git's -h) or a note")

    if not offenders:
        print(f"checked {len(registry)} registered tools — none invoke man/groff/troff")
        return
    print(f"\n{len(offenders)} tool(s) depend on man: {', '.join(offenders)}")
    raise RuntimeError(f"{len(offenders)} tool(s) depend on man/groff/troff: {', '.join(offenders)}")
