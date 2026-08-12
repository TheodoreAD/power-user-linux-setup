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
import tomllib
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from invoke import task

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


_ROOT = Path(__file__).parent.parent / "cli-allowlist"
_TOOLS_TOML = _ROOT / "tools.toml"
_HELP_CACHE_DIR = _ROOT / "help-cache"
_RULES_DIR = _ROOT / "rules"

_CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"
# Machine-local mutation-tracking state, not repo content — deliberately outside cli-allowlist/
# (which is portable, shared, tracked in git) since this records what `apply` last wrote into an
# out-of-repo file on *this* machine specifically, mirroring the ~/.config/pulse/ namespace
# util.py already uses for the same kind of machine-local state (identity.toml).
_APPLIED_MANIFEST = Path.home() / ".local" / "state" / "pulse" / "claude-settings-applied.json"

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


def _node_prefix(indent: str, label: str, classification: str, suffix: str = "") -> tuple[str, str]:
    """(plain, colored) prefix pair for a node/flag line: name in bold, classification in its
    tier color, everything else (indent, punctuation, source annotation) left in the terminal's
    default color so it doesn't compete for attention with the two things worth scanning for."""
    plain = f"{indent}{label}: {classification}{suffix} — "
    colored = (
        f"{indent}{_colorize(label, 'bold')}: {_colorize(classification, _CLASS_COLOR.get(classification))}{suffix} — "
    )
    return plain, colored


def _load_registry() -> dict:
    with _TOOLS_TOML.open("rb") as f:
        return tomllib.load(f)


def _load_rule(tool: str) -> dict | None:
    path = _RULES_DIR / f"{tool}.json"
    return json.loads(path.read_text()) if path.exists() else None


def _save_rule(tool: str, entry: dict) -> None:
    _RULES_DIR.mkdir(parents=True, exist_ok=True)
    (_RULES_DIR / f"{tool}.json").write_text(json.dumps(entry, indent=2, sort_keys=True) + "\n")


def _load_all_rules() -> dict[str, dict]:
    """Every reviewed-or-not rule, keyed by tool — one file per tool under cli-allowlist/rules/
    so a single tool's re-classification only touches that tool's diff, not one monolithic file."""
    if not _RULES_DIR.exists():
        return {}
    return {p.stem: json.loads(p.read_text()) for p in sorted(_RULES_DIR.glob("*.json"))}


def _load_cache(tool: str) -> dict | None:
    path = _HELP_CACHE_DIR / f"{tool}.json"
    return json.loads(path.read_text()) if path.exists() else None


def _save_cache(tool: str, data: dict) -> None:
    _HELP_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (_HELP_CACHE_DIR / f"{tool}.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def _run(cmd: list[str], timeout: int = _HELP_TIMEOUT) -> str:
    """Run a command, return combined stdout+stderr, "" on timeout/missing binary. Never raises
    on nonzero exit — --help conventionally exits nonzero on plenty of tools."""
    env = {**os.environ, **_DETERMINISTIC_ENV}
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env, stdin=subprocess.DEVNULL)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""
    return (result.stdout + result.stderr).strip()


def _invocation(tool: str, args: list[str], cfg: dict) -> list[str]:
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


def _tool_version(tool: str, version_flag: str, cfg: dict | None = None) -> str:
    """Return a stable per-version string for cache invalidation. Not always line 1: eza's
    --version prints its tagline first and the actual "v0.18.2 [+git]" on line 2 — a tagline
    never changes across upgrades, which would silently defeat staleness detection. Preferring
    the first line that contains a digit catches that case generally, not just for eza."""
    text = _run(_invocation(tool, version_flag.split(), cfg or {}))
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


def _dangerous_tokens_in(name_or_path: str) -> set[str]:
    """The specific _DANGEROUS_VERBS token(s) that matched, not just whether any did — reused by
    the needs_review backstop (which only needs the bool) and by `reconfirm` (which needs to tell
    the model exactly which word triggered suspicion, so it can judge whether that word's
    dangerous sense actually applies here)."""
    tokens = re.split(r"[\s\-_/]+", name_or_path.lower())
    return {t for t in tokens if t in _DANGEROUS_VERBS}


def _looks_dangerous(name_or_path: str) -> bool:
    return bool(_dangerous_tokens_in(name_or_path))


def _dangerous_flag_tokens(flag: str) -> set[str]:
    """Flag counterpart of _dangerous_tokens_in — same safe-hint tiebreak as _looks_dangerous_flag
    (see its docstring: "--dry-run" token-matches "run" in _DANGEROUS_VERBS, added for `nvm run`
    as a subcommand, and needs the whole-name safe-hint check to not be wrongly flagged), just
    returning the matched token(s) instead of a bool."""
    if _flag_matches_hints(flag, _SAFE_FLAG_HINTS):
        return set()
    return _flag_tokens(flag) & _DANGEROUS_VERBS


def _looks_dangerous_flag(flag: str) -> bool:
    return bool(_dangerous_flag_tokens(flag))


def _fetch_node(
    name: str, cfg: dict, path: list[str], parent_hash: str, sibling_count: int, help_flag: str, help_style: str
) -> tuple[dict, bool]:
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
    text = _run(_invocation(name, _sub_args(path, help_flag, help_style), cfg))
    node_hash = _hash_text(text)
    duplicates_parent = bool(text) and node_hash == parent_hash
    likely_invalid = duplicates_parent and sibling_count == 1
    node_entry = {"help_text": text, "content_hash": node_hash, "likely_invalid": likely_invalid}
    return node_entry, duplicates_parent


def _build_tree(name: str, cfg: dict, top_help: str, help_flag: str, help_style: str) -> tuple[dict, bool]:
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

    nodes: dict[str, dict] = {}
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
        for c in child_names:
            queue.append(([*path, c], depth + 1, node_entry["content_hash"], len(child_names)))

    return nodes, truncated


def _extract_one(name: str, cfg: dict | None, force: bool) -> None:
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

    cached = _load_cache(name) or {}
    if not force and version and cached.get("version") == version:
        print(f"[allowlist] {name}: unchanged ({version}) — skipped")
        return

    help_flag = cfg.get("help_flag", "--help")
    help_style = cfg.get("help_style", "suffix")  # "prefix": <tool> <flag> <sub> (go); default: <tool> <sub> <flag>

    top_help = _run(_invocation(name, _sub_args(None, help_flag, help_style), cfg))

    if not top_help and not cfg.get("shell_prefix"):
        print(f"[allowlist] {name}: no output from --help — skipping (installed but unresponsive?)")
        return

    truncated = False
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
def extract(c, tool=None, force=False):
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


def _build_prompt(tool: str, nodes: dict[str, dict], top_help: str) -> str:
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


def _classify_via_claude(prompt: str, model: str, schema: str = _SCHEMA) -> dict | None:
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
            )
        except subprocess.TimeoutExpired:
            return None
    if result.returncode != 0:
        return None
    try:
        envelope = json.loads(result.stdout)
        return envelope["structured_output"]["classifications"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def _strip_tool_prefix(verdict: dict, tool: str) -> dict:
    """Defensive normalization: the model occasionally echoes the tool name back as part of a
    key ("gh run list" instead of the requested "run list") even though the rubric asks for the
    exact key strings given back unchanged — confirmed happening on a real `reconfirm` call for
    gh, where every one of 6 correctly-classified items was silently discarded because the lookup
    by the original (unprefixed) key came back empty. Stripping a leading "<tool> " prefix when
    present costs nothing when the model behaved, and recovers the result when it didn't."""
    prefix = f"{tool} "
    return {(k[len(prefix) :] if k.startswith(prefix) else k): v for k, v in verdict.items()}


def _resolve_flat_verdict(verdict: dict) -> dict:
    """Map the model's single _FLAT_KEY answer back to "*". If it ignored the instruction and
    broke the tool into multiple entries anyway (observed once, on a flags-heavy --help text),
    fall back to the most cautious of whatever it returned rather than an arbitrary one —
    consistent with the verb backstop's "when in doubt, don't assume safe" stance."""
    if _FLAT_KEY in verdict:
        return {_NO_SUBCOMMANDS_KEY: verdict[_FLAT_KEY]}
    if not verdict:
        return verdict
    order = {Classification.READ_ONLY: 0, Classification.WRITE: 1, Classification.DANGEROUS: 2}
    worst = max(verdict.values(), key=lambda v: order.get(v.get("classification"), 1))
    return {
        _NO_SUBCOMMANDS_KEY: {
            "classification": worst.get("classification", Classification.WRITE),
            "rationale": f"inferred conservatively — model split this flat tool into "
            f"multiple parts instead of one verdict ({worst.get('rationale', '')})",
        }
    }


def _classify_flag_result(flag: str, result: dict, base_classification: str) -> dict:
    classification = result.get("classification", base_classification)
    if classification == Classification.READ_ONLY and _looks_dangerous_flag(flag):
        classification = Classification.NEEDS_REVIEW
    return {"classification": classification, "rationale": result.get("rationale", "")}


@task
def classify(c, tool=None, force=False, model="haiku"):
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

        cache_nodes = cached.get("nodes", {})
        classifiable_keys = [k for k in cache_nodes if k != _TOP_HELP_KEY]
        top_help = cache_nodes.get(_TOP_HELP_KEY, {}).get("help_text", "")

        existing = _load_rule(name)
        existing_nodes = (existing or {}).get("nodes", {})

        # Nodes _build_tree already flagged as likely bogus (auto-discovered, byte-identical to
        # their parent's help text) skip the LLM entirely — deterministic, free, and more reliable
        # than asking a model to notice the same thing. They still go through the same
        # unchanged-since-last-run check as everything else, just compared against "was this
        # already recorded as invalid with this exact content" instead of a normal classification.
        to_classify: dict[str, dict] = {}
        carried: dict[str, dict] = {}
        new_invalid: dict[str, dict] = {}
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
            is_community = bool(prior) and prior.get("source") == Source.COMMUNITY
            unchanged = (
                not force and not is_community and bool(prior) and prior.get("content_hash") == node["content_hash"]
            )
            if node.get("likely_invalid"):
                if unchanged and prior.get("classification") == Classification.INVALID:
                    carried[key] = prior
                else:
                    new_invalid[key] = node
            elif unchanged:
                carried[key] = prior
            else:
                to_classify[key] = node

        if not to_classify and not new_invalid:
            print(f"[allowlist] {name}: unchanged since last classification — skipped")
            continue

        # Chunked, not one call for the whole tool: a call covering 50+ nodes (routine once
        # recursion is on) risks both the timeout and --max-budget-usd ceiling — see
        # _CLASSIFY_CHUNK_SIZE's comment for the measurement that drove this.
        verdict: dict = {}
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

        if to_classify and not verdict:
            print(f"[allowlist] {name}: classification call failed — left as-is")
            continue
        if failed_chunks:
            missing = sum(1 for key in to_classify if key not in verdict)
            print(
                f"[allowlist] {name}: {failed_chunks} chunk(s) failed — {missing} node(s) left "
                f"unclassified, will retry on the next run"
            )

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
            if classification == Classification.READ_ONLY and _looks_dangerous(key):
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


def _build_reconfirm_prompt(tool: str, candidates: dict[str, dict]) -> str:
    parts = [_RECONFIRM_RUBRIC, "", f"Tool: {tool}", ""]
    for key, meta in candidates.items():
        flagged = ", ".join(sorted(meta["tokens"])) or "(unknown)"
        parts.append(f"### {key}\nFlagged word(s): {flagged}\n{meta['help_text'][:800]}\n")
    return "\n".join(parts)


@task
def reconfirm(c, tool=None, model="haiku"):
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
        nodes = entry.get("nodes", {})
        cache_nodes = (_load_cache(name) or {}).get("nodes", {})

        # Composite key "<path> <flag>" for flag-level items — unambiguous to parse back since a
        # real subcommand path segment never starts with "-", only a flag token does.
        candidates: dict[str, dict] = {}
        for path, v in nodes.items():
            if v.get("classification") == Classification.NEEDS_REVIEW:
                candidates[path] = {
                    "help_text": cache_nodes.get(path, {}).get("help_text", ""),
                    "tokens": _dangerous_tokens_in(path),
                    "kind": "node",
                    "path": path,
                }
            for flag, fv in v.get("flags", {}).items():
                if fv.get("classification") == Classification.NEEDS_REVIEW:
                    candidates[f"{path} {flag}"] = {
                        "help_text": cache_nodes.get(path, {}).get("help_text", ""),
                        "tokens": _dangerous_flag_tokens(flag),
                        "kind": "flag",
                        "path": path,
                        "flag": flag,
                    }

        if not candidates:
            continue
        any_found = True

        verdict: dict = {}
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
            if meta["kind"] == "node":
                nodes[meta["path"]]["classification"] = classification
                nodes[meta["path"]]["rationale"] = rationale
                nodes[meta["path"]]["source"] = Source.LLM_RECONFIRMED
            else:
                nodes[meta["path"]]["flags"][meta["flag"]] = {
                    "classification": classification,
                    "rationale": rationale,
                }
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
def review(c, apply_all=False, only=None):
    """Show tools with unreviewed classifications (new or changed since the last reviewed
    snapshot) and, on confirmation, mark them reviewed. Nothing in `render` trusts an unreviewed
    entry, so this is the human gate before anything downstream sees a tool's rules. Per-tool, not
    per-node: there's no mechanism to individually override one node's classification without
    reclassifying, which is why needs_review entries stay excluded even after their tool is
    marked reviewed.

    --only=dangerous,needs_review narrows the per-node list to just those classification tiers
    (comma-separated) — useful for triaging a large tree (docker/gh run 150+ nodes) without
    reading past every read_only entry first. Omit for the full list. `invalid` entries and the
    approval prompt are unaffected by the filter either way."""
    rules = _load_all_rules()
    pending = {name: entry for name, entry in rules.items() if not entry.get("reviewed")}
    only_set = {t.strip() for t in only.split(",") if t.strip()} if only else None

    if not pending:
        print("[allowlist] nothing pending review")
        return

    for name, entry in sorted(pending.items()):
        nodes = entry.get("nodes", {})
        invalid = [k for k, v in nodes.items() if v.get("classification") == Classification.INVALID]
        invalid_note = f", {len(invalid)} excluded as invalid" if invalid else ""
        print(f"\n[allowlist] {name} ({len(nodes)} node(s){invalid_note})")
        if entry.get("note"):
            print(f"  note: {entry['note']}")
        if entry.get("truncated"):
            print("  note: tree truncated at max_nodes — not the tool's full command surface")
        if invalid:
            # Not classified/rendered as a real command — a discovery false positive (see
            # tools.toml/docs for the "duplicates its parent" heuristic and the LLM backstop for
            # anything that slips past it). Shown separately, not mixed into the per-node dump
            # below, since printing "classification: invalid" inline reads like a 4th risk tier
            # rather than "this isn't a command, ignore it."
            print(f"  {_colorize('invalid', 'gray')} (excluded from rules, not a real command):")
            for path in sorted(invalid):
                plain = f"    {path} ({nodes[path].get('source')}) — "
                colored = f"    {_colorize(path, 'bold')} ({nodes[path].get('source')}) — "
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
            if v.get("classification") == Classification.INVALID:
                continue
            if only_set and v["classification"] not in only_set:
                continue
            indent = "    " + "  " * path.count(" ")
            label = path.rsplit(" ", 1)[-1]
            source = f" ({v['source']})" if v.get("source") == Source.COMMUNITY else ""
            plain, colored = _node_prefix(indent, label, v["classification"], source)
            print(_wrap(plain, v["rationale"], colored))
            for flag, fv in sorted(v.get("flags", {}).items()):
                fplain, fcolored = _node_prefix(indent + "  ", flag, fv["classification"])
                print(_wrap(fplain, fv["rationale"], fcolored))

        approve = apply_all or util.confirm(f"Mark {name} reviewed?", default=False)
        if approve:
            entry["reviewed"] = True
            entry["reviewed_at"] = _now()
            _save_rule(name, entry)
            print(f"  -> {name} marked reviewed")
        else:
            print(f"  -> {name} left unreviewed")


def _compute_claude_rules(rules: dict) -> tuple[list[str], list[str]]:
    """Reviewed rules -> (allow patterns, ask patterns). Shared by `render` (prints it) and
    `apply` (merges it into ~/.claude/settings.json) so the two can never drift apart. Per-flag
    ratings aren't rendered into rules here: Claude's Bash permission rules are literal-prefix
    globs, and flags can appear in any order/position in a real invocation, so there's no clean
    prefix-based way to carve out just "this subcommand, except with --force" — that data stays
    analysis/review-only until there's an actual consumer that can act on it (e.g. a future
    PreToolUse hook, deliberately not built yet — see contributing/cli-allowlist.md).

    A read_only node that has children of its own is skipped entirely — deliberately, not an
    oversight. Its read_only verdict describes what happens when it's invoked *bare* (`docker
    network` with no further args just lists/describes, same as any other read_only command), but
    real usage always goes through a child (`docker network rm`, `docker network create`), each of
    which already gets its own independently-correct rule. Rendering a rule for the bare parent
    too is pure noise: Claude Code's permission precedence is deny > ask > allow with no
    specificity tiebreak (confirmed against the actual docs, not assumed), so a stricter rule for
    a child always wins over a looser allow for its parent regardless — the omitted rule was never
    doing anything a more specific one wasn't already doing more correctly. The rare case of the
    bare parent actually being invoked with no subcommand falls through to Claude's own default
    behavior instead (typically still a prompt), not silent approval and not silent denial."""
    registry = _load_registry()
    allow, ask = [], []
    for name, entry in sorted(rules.items()):
        if not entry.get("reviewed"):
            continue
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
        is_cloud_cli = bool(registry.get(name, {}).get("cloud_cli"))
        cache_nodes = (_load_cache(name) or {}).get("nodes", {})
        for path, v in sorted(entry.get("nodes", {}).items()):
            classification = v["classification"]
            if classification == Classification.READ_ONLY and cache_nodes.get(path, {}).get("children"):
                continue
            pattern = f"Bash({name}:*)" if path == _NO_SUBCOMMANDS_KEY else f"Bash({name} {path}:*)"
            if classification == Classification.READ_ONLY and not is_cloud_cli:
                allow.append(pattern)
            elif classification in (Classification.WRITE, Classification.DANGEROUS) or (
                classification == Classification.READ_ONLY and is_cloud_cli
            ):
                ask.append(pattern)
    return allow, ask


def _render_claude(rules: dict) -> str:
    allow, ask = _compute_claude_rules(rules)
    return json.dumps({"permissions": {"allow": allow, "ask": ask}}, indent=2)


def _render_copilot(rules: dict) -> str:
    auto_approve = {}
    for name, entry in sorted(rules.items()):
        if not entry.get("reviewed"):
            continue
        for path, v in sorted(entry.get("nodes", {}).items()):
            key = (
                f"/^{re.escape(name)}\\b.*/"
                if path == _NO_SUBCOMMANDS_KEY
                else f"/^{re.escape(name)} {re.escape(path)}\\b.*/"
            )
            auto_approve[key] = v["classification"] == Classification.READ_ONLY
    return json.dumps({"chat.tools.terminal.autoApprove": auto_approve}, indent=2)


@task
def render(c, target="claude", out=None):
    """Print the reviewed subset of rules as Claude Bash(...) allow/ask rules or Copilot
    chat.tools.terminal.autoApprove regex rules. Output-only — never writes to any settings file
    (local or user-wide); that's a deliberate next step, not part of this task. `write` and
    `dangerous` entries always render as still-prompting (Claude `ask` / Copilot `false`), never
    as a hard deny — the point is a visible, still-approvable prompt, not a block."""
    rules = _load_all_rules()
    unreviewed = [name for name, entry in rules.items() if not entry.get("reviewed")]
    if unreviewed:
        joined = ", ".join(sorted(unreviewed))
        print(f"[allowlist] note: {len(unreviewed)} tool(s) not yet reviewed, excluded from output: {joined}")

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


@task
def apply(c):
    """Merge the reviewed Bash allow/ask rules into ~/.claude/settings.json's `permissions`
    block — the only thing this task ever touches there.

    Every other key in that file (theme, effortLevel, cleanupPeriodDays, any permission rule you
    added by hand, etc.) is left completely untouched, including on repeated runs. This works by
    tracking exactly which rule strings *we* wrote last time in a local manifest
    (~/.local/state/pulse/claude-settings-applied.json, not repo content — see its definition
    above): on each run, only rules present in that manifest are eligible to be removed, and only
    the freshly computed set is added back. A rule that was never in our manifest — something you
    added yourself — is never touched, and a rule we used to generate but no longer do (say a
    tool's classification changed) is cleanly removed rather than left orphaned. This is what
    "the bash allow rules could be overwritten every time" means in practice: our portion is fully
    regenerated each run, nothing else is.
    """
    rules = _load_all_rules()
    unreviewed = [name for name, entry in rules.items() if not entry.get("reviewed")]
    if unreviewed:
        print(
            f"[allowlist] note: {len(unreviewed)} tool(s) not yet reviewed, excluded: {', '.join(sorted(unreviewed))}"
        )

    allow, ask = _compute_claude_rules(rules)
    new_set = set(allow) | set(ask)
    previous = set(json.loads(_APPLIED_MANIFEST.read_text())) if _APPLIED_MANIFEST.exists() else set()

    settings = json.loads(_CLAUDE_SETTINGS.read_text()) if _CLAUDE_SETTINGS.exists() else {}
    perms = settings.setdefault("permissions", {})
    existing_allow = perms.get("allow", [])
    existing_ask = perms.get("ask", [])

    kept_allow = [r for r in existing_allow if r not in previous]
    kept_ask = [r for r in existing_ask if r not in previous]
    merged_allow = kept_allow + [r for r in allow if r not in kept_allow]
    merged_ask = kept_ask + [r for r in ask if r not in kept_ask]

    # Per-bucket diff, not just the flattened union — a rule moving from allow to ask (a tool's
    # classification changed) is a real, meaningful change even though the union of both arrays
    # contains that rule string either way. Reporting only the union would silently print "+0 -0"
    # for exactly the kind of change this task most needs to surface honestly.
    added_allow = set(merged_allow) - set(existing_allow)
    removed_allow = set(existing_allow) & previous - set(merged_allow)
    added_ask = set(merged_ask) - set(existing_ask)
    removed_ask = set(existing_ask) & previous - set(merged_ask)
    added = added_allow | added_ask
    removed = removed_allow | removed_ask
    unchanged = new_set & previous - added - removed

    if set(merged_allow) == set(existing_allow) and set(merged_ask) == set(existing_ask):
        print(f"[allowlist] {_CLAUDE_SETTINGS}: already up to date ({len(unchanged)} rule(s))")
        return

    print(f"[allowlist] {_CLAUDE_SETTINGS}: +{len(added)} -{len(removed)} rule(s) ({len(unchanged)} unchanged)")
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

    if _CLAUDE_SETTINGS.exists():
        _CLAUDE_SETTINGS.with_suffix(".json.bak").write_text(_CLAUDE_SETTINGS.read_text())
    _CLAUDE_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    _CLAUDE_SETTINGS.write_text(json.dumps(settings, indent=2) + "\n")

    _APPLIED_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    _APPLIED_MANIFEST.write_text(json.dumps(sorted(new_set), indent=2) + "\n")
    print(f"[allowlist] wrote {_CLAUDE_SETTINGS} (backup at {_CLAUDE_SETTINGS}.bak)")


@task
def status(c):
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
            print(f"[allowlist] {name}: interactive-only, reviewed={entry.get('reviewed')}")
            continue

        version_flag = cfg.get("version_flag", "--version")
        current_version = _tool_version(name, version_flag, cfg)
        stale = bool(current_version) and current_version != entry.get("version")
        nodes = entry.get("nodes", {})
        flags = []
        if stale:
            flags.append("STALE")
        if not entry.get("reviewed"):
            flags.append("unreviewed")
        if entry.get("truncated"):
            flags.append("truncated")
        if cfg.get("cloud_cli"):
            flags.append("cloud-cli (depth capped intentionally)")
        invalid_count = sum(1 for v in nodes.values() if v.get("classification") == Classification.INVALID)
        if invalid_count:
            flags.append(f"{invalid_count} invalid (excluded)")
        needs_review = sum(1 for v in nodes.values() if v.get("classification") == Classification.NEEDS_REVIEW)
        if needs_review:
            flags.append(f"{needs_review} needs_review")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        depth = cfg.get("max_depth", 1)
        print(f"[allowlist] {name}: {entry.get('version') or '?'} ({len(nodes)} node(s), depth={depth}){flag_str}")


# ---------------------------------------------------------------------------
# check-man-deps: not part of the extract/classify/review/apply pipeline above — a separate,
# occasional maintenance diagnostic (uses strace, slower than anything else here), run by hand
# after registering a new tool or periodically, not automatically by any other task.
# ---------------------------------------------------------------------------

_MAN_BINARIES = ["/usr/bin/man", "/bin/man", "/usr/bin/groff", "/usr/bin/troff"]


def _should_check_man_deps(name: str, cfg: dict) -> bool:
    """Skip tools explicitly opted out, and (for tools without a shell_prefix escape hatch) any
    not actually installed on this machine."""
    if cfg.get("skip_interactive"):
        return False
    return bool(cfg.get("shell_prefix")) or util.command_exists(name)


def _strace_execve_log(cmd: list[str], env: dict) -> str | None:
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
            )
        except subprocess.TimeoutExpired:
            return None
        return Path(log.name).read_text()


def _man_dependency(log_text: str) -> str | None:
    """Which (if any) of the man-rendering binaries the strace log shows an execve() for."""
    return next((b for b in _MAN_BINARIES if f'execve("{b}"' in log_text), None)


@task
def check_man_deps(c):
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
    offenders = []

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
