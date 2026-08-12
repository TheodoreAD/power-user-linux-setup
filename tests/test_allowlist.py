"""Unit tests for tasks/allowlist.py's pure helpers: Classification/Source enum interop with the
plain-string JSON that flows through cli-allowlist/rules/*.json and the LLM's JSON responses,
_resolve_flat_verdict/_classify_flag_result (pure data transforms, no subprocess/LLM calls of their
own), and check_man_deps()'s _should_check_man_deps/_man_dependency (no strace/subprocess calls of
their own). See tests/README.md.
"""

import json
from pathlib import Path

from tasks import allowlist

_RULES_DIR = Path(__file__).parent.parent / "cli-allowlist" / "rules"


def test_classification_values_match_rules_json_on_disk():
    # A typo in the enum's value must not silently diverge from what's already written into
    # cli-allowlist/rules/*.json — every rule file on disk uses these exact plain strings.
    assert {m.value for m in allowlist.Classification} == {
        "read_only",
        "write",
        "dangerous",
        "needs_review",
        "invalid",
    }


def test_source_values_match_rules_json_on_disk():
    assert {m.value for m in allowlist.Source} == {"community", "heuristic", "llm", "llm-reconfirmed"}


def test_every_rule_file_on_disk_uses_only_known_classification_and_source_values():
    rule_files = sorted(_RULES_DIR.glob("*.json"))
    assert rule_files, f"expected rule files under {_RULES_DIR}"
    known_classifications = {m.value for m in allowlist.Classification}
    known_sources = {m.value for m in allowlist.Source}
    for path in rule_files:
        entry = json.loads(path.read_text())
        for key, node in entry.get("nodes", {}).items():
            assert node["classification"] in known_classifications, f"{path.name}:{key}"
            if "source" in node:
                assert node["source"] in known_sources, f"{path.name}:{key}"
            for flag_name, flag in node.get("flags", {}).items():
                assert flag["classification"] in known_classifications, f"{path.name}:{key} flag {flag_name}"


def test_classification_formats_as_plain_value_not_enum_repr():
    # (str, Enum) members format as "Classification.DANGEROUS" in an f-string unless __str__ is
    # overridden — review()'s output and _save_rule's callers rely on the plain value.
    assert f"{allowlist.Classification.DANGEROUS}" == "dangerous"
    assert str(allowlist.Source.LLM_RECONFIRMED) == "llm-reconfirmed"


def test_classification_equals_and_hashes_like_plain_string():
    # Values loaded from disk via json.loads are always plain str, never Classification instances
    # — every comparison/dict-key site in allowlist.py depends on the two being interchangeable.
    assert allowlist.Classification.READ_ONLY == "read_only"
    assert hash(allowlist.Classification.READ_ONLY) == hash("read_only")
    assert {"read_only": 1}.get(allowlist.Classification.READ_ONLY) == 1


def test_classification_json_round_trips_as_plain_string():
    # _save_rule writes json.dumps(entry) where entry's "classification"/"source" values may be
    # Classification/Source members (set during classify()) — must serialize as plain strings.
    dumped = json.dumps({"classification": allowlist.Classification.DANGEROUS, "source": allowlist.Source.LLM})
    assert json.loads(dumped) == {"classification": "dangerous", "source": "llm"}


def test_resolve_flat_verdict_maps_flat_key_back_to_sentinel():
    result = allowlist._resolve_flat_verdict({allowlist._FLAT_KEY: {"classification": "dangerous", "rationale": "x"}})
    assert result == {allowlist._NO_SUBCOMMANDS_KEY: {"classification": "dangerous", "rationale": "x"}}


def test_resolve_flat_verdict_picks_worst_classification_when_model_splits_answer():
    result = allowlist._resolve_flat_verdict(
        {
            "foo": {"classification": "write", "rationale": "a"},
            "bar": {"classification": "dangerous", "rationale": "b"},
        }
    )
    assert result[allowlist._NO_SUBCOMMANDS_KEY]["classification"] == "dangerous"


def test_resolve_flat_verdict_empty_input():
    assert allowlist._resolve_flat_verdict({}) == {}


def test_classify_flag_result_downgrades_read_only_to_needs_review_for_dangerous_flag():
    result = allowlist._classify_flag_result("--force", {"classification": "read_only", "rationale": "x"}, "write")
    assert result["classification"] == allowlist.Classification.NEEDS_REVIEW


def test_classify_flag_result_leaves_safe_flag_alone():
    result = allowlist._classify_flag_result("--dry-run", {"classification": "read_only", "rationale": "x"}, "write")
    assert result["classification"] == "read_only"


def test_classify_flag_result_falls_back_to_base_classification():
    result = allowlist._classify_flag_result("--output", {}, "dangerous")
    assert result["classification"] == "dangerous"


def test_should_check_man_deps_skips_tools_marked_skip_interactive():
    assert allowlist._should_check_man_deps("vim", {"skip_interactive": True}) is False


def test_should_check_man_deps_allows_shell_prefix_tools_without_checking_install(monkeypatch):
    # A shell_prefix tool (e.g. nvm) only exists as a shell function, not a binary on PATH —
    # command_exists() would always report it missing, so it must be exempt from that check.
    monkeypatch.setattr(allowlist.util, "command_exists", lambda name: False)
    assert allowlist._should_check_man_deps("nvm", {"shell_prefix": ". ~/.nvm/nvm.sh"}) is True


def test_should_check_man_deps_requires_install_when_no_shell_prefix(monkeypatch):
    monkeypatch.setattr(allowlist.util, "command_exists", lambda name: False)
    assert allowlist._should_check_man_deps("some-tool", {}) is False

    monkeypatch.setattr(allowlist.util, "command_exists", lambda name: True)
    assert allowlist._should_check_man_deps("some-tool", {}) is True


def test_man_dependency_detects_man_binary():
    log = 'execve("/usr/bin/man", ["man", "git"], 0x7fff /* 40 vars */) = 0\n'
    assert allowlist._man_dependency(log) == "/usr/bin/man"


def test_man_dependency_detects_groff():
    log = 'execve("/usr/bin/groff", ["groff", "-m", "man"], 0x7fff) = 0\n'
    assert allowlist._man_dependency(log) == "/usr/bin/groff"


def test_man_dependency_none_when_no_match():
    log = 'execve("/usr/bin/git", ["git", "status", "--help"], 0x7fff) = 0\n'
    assert allowlist._man_dependency(log) is None
