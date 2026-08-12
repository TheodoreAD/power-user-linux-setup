"""Unit tests for tasks/allowlist.py's pure helpers: Classification/Source enum interop with the
plain-string JSON that flows through cli-allowlist/rules/*.json and the LLM's JSON responses, plus
_resolve_flat_verdict and _classify_flag_result (pure data transforms, no subprocess/LLM calls of
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
