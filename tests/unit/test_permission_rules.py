"""Unit tests for tasks/permission_rules.py: the pattern grammar, and what each harness renderer
emits for it. The Claude expectations encode behaviour measured against the real binary — see
contributing/cli-allowlist.md's "How each harness matches" — so a failing case here means the
renderer changed, not that Claude Code did; `inv allowlist.check-claude` is what notices the latter.
"""

import re

import pytest

from tasks.permission_rules import (
    Decision,
    Rule,
    RuleSyntaxError,
    claude_inner_wildcard,
    claude_patterns,
    copilot_key,
    parse,
    render_claude,
    render_copilot,
)


def _rule(
    body: str,
    decision: Decision = Decision.ALLOW,
    *,
    tool: str = "git",
    repo_dir_options: tuple[str, ...] = (),
    mode_covered: bool = False,
) -> Rule:
    return Rule(tool, decision, parse(body), repo_dir_options, mode_covered)


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        # A trailing ` *` alone already matches the bare command, so one pattern covers both.
        ("status ...", ["Bash(git status *)"]),
        ("...", ["Bash(git *)"]),
        ("status", ["Bash(git status)"]),
        # `*` never matches the empty string between two spaces: zero-or-more in the middle takes
        # two spellings, and a trailing `*` beside another wildcard no longer matches "nothing".
        (
            "reset ... --hard ...",
            ["Bash(git reset --hard *)", "Bash(git reset * --hard)", "Bash(git reset * --hard *)"],
        ),
        # A glob spans trailing text in Claude's syntax, so no ` *` sibling is emitted after it.
        ("quality.* ...", ["Bash(git quality.*)"]),
        ("*.status ...", ["Bash(git *.status)", "Bash(git *.status *)"]),
        ("... -c* ...", ["Bash(git -c*)", "Bash(git * -c*)"]),
    ],
    ids=["trailing", "bare-tool", "exact", "mid-args", "glob-then-args", "glob-verb", "guard"],
)
def test_claude_patterns(body: str, expected: list[str]):
    assert claude_patterns(_rule(body)) == expected


def test_claude_patterns_never_use_the_colon_star_suffix():
    # Mid-pattern `*` plus a trailing `:*` loads as a literal `*` and matches nothing (2.1.282+).
    for body in ["status ...", "reset ... --hard ...", "*.status ...", "..."]:
        assert not any(":*" in p for p in claude_patterns(_rule(body)))


def test_claude_patterns_enumerate_repo_dirs_instead_of_globbing_them():
    rule = _rule("status ...", repo_dir_options=("-C",))
    assert claude_patterns(rule, ["/p/a", "~/p/a"]) == [
        "Bash(git status *)",
        "Bash(git -C /p/a status *)",
        "Bash(git -C ~/p/a status *)",
    ]


@pytest.mark.parametrize(
    ("pattern", "warns"),
    [
        ("Bash(git -C * status *)", True),
        ("Bash(git * status)", True),
        ("Bash(git status *)", False),
        ("Bash(inv *.status *)", False),
        ("Bash(git -C /p/a status *)", False),
    ],
)
def test_claude_inner_wildcard(pattern: str, warns: bool):
    assert claude_inner_wildcard(pattern) is warns


def test_render_claude_splits_by_decision_and_dedupes():
    rules = [
        _rule("status ..."),
        _rule("status ..."),
        _rule("push ...", Decision.ASK),
    ]
    assert render_claude(rules) == (["Bash(git status *)"], ["Bash(git push *)"])


def test_render_claude_drops_mode_covered_ask_only():
    rules = [_rule("...", Decision.ASK, tool="mkdir", mode_covered=True), _rule("...", tool="ls", mode_covered=True)]
    assert render_claude(rules) == (["Bash(ls *)"], [])


def test_render_claude_refuses_an_allow_it_would_warn_about():
    with pytest.raises(RuleSyntaxError, match="wildcard before the last word"):
        render_claude([_rule("... status ...")])


def test_render_claude_accepts_the_same_shape_as_an_ask():
    # Ask rules only ever add a prompt, so Claude Code does not warn about them.
    assert render_claude([_rule("reset ... --hard ...", Decision.ASK)])[1][1] == "Bash(git reset * --hard)"


def _copilot_matches(key: str, command: str) -> bool:
    return re.search(key.removeprefix("/").removesuffix("/"), command) is not None


@pytest.mark.parametrize(
    ("body", "command", "matches"),
    [
        ("status ...", "git status", True),
        ("status ...", "git status --short", True),
        ("status ...", "git statusx", False),
        ("status ...", "git -C /p status", False),
        ("reset ... --hard ...", "git reset HEAD --hard", True),
        ("reset ... --hard ...", "git reset -q --hard HEAD", True),
        ("reset ... --hard ...", "git reset -q HEAD", False),
        # One argument means one: the glob can't swallow an inserted option the way Claude's `*` does.
        ("*.status ...", "git x.status", True),
        ("*.status ...", "git -c evil x.status", False),
    ],
)
def test_copilot_key_matching(body: str, command: str, matches: bool):
    assert _copilot_matches(copilot_key(_rule(body)), command) is matches


@pytest.mark.parametrize(
    ("command", "matches"),
    [
        ("git -C /any/path status", True),
        ("git -C a -C b status -s", True),
        ("git -C /p -c core.fsmonitor=x status", False),
        ("git -c x -C /p status", False),
    ],
)
def test_copilot_key_repo_dir_option_takes_exactly_one_argument(command: str, matches: bool):
    key = copilot_key(_rule("status ...", repo_dir_options=("-C",)))
    assert _copilot_matches(key, command) is matches


def test_render_copilot_ask_wins_a_shared_key():
    rules = [_rule("status ..."), _rule("status ...", Decision.ASK), _rule("log ...")]
    rendered = render_copilot(rules)
    assert rendered[copilot_key(rules[0])] is False
    assert rendered[copilot_key(rules[2])] is True


@pytest.mark.parametrize("body", ["reset --hard...", "a ... ... b"], ids=["glued", "doubled"])
def test_parse_rejects_ambiguous_any_args(body: str):
    with pytest.raises(RuleSyntaxError):
        parse(body)
