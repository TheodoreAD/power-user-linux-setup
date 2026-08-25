"""Unit tests for tasks/allowlist.py's pure helpers: Classification/Source enum interop with the
plain-string JSON that flows through cli-allowlist/rules/*.json and the LLM's JSON responses,
_resolve_flat_verdict/_classify_flag_result (pure data transforms, no subprocess/LLM calls of their
own), _merge_rule_sets/_coverage_gaps (render/apply's pure logic, given in-memory rules/cache
fixtures), and check_man_deps()'s _should_check_man_deps/_man_dependency (no strace/subprocess
calls of their own). See tests/README.md.
"""

import json
from pathlib import Path
from typing import cast

from tasks import allowlist

_REPO_ROOT = Path(__file__).parents[2]  # tests/unit/<this file> → repo root
_RULES_DIR = _REPO_ROOT / "cli-allowlist" / "rules"


# Complete, typed fixtures — every field allowlist.py's TypedDicts require, so a test only spells
# out the one or two it is actually about.


def _cache_node(
    content_hash: str = "x", *, likely_invalid: bool = False, children: list[str] | None = None
) -> allowlist.CacheNode:
    return {"help_text": "", "content_hash": content_hash, "children": children or [], "likely_invalid": likely_invalid}


def _cache_entry(
    nodes: dict[str, allowlist.CacheNode], *, version: str = "1.0.0", extracted_at: str = "new"
) -> allowlist.CacheEntry:
    return {"interactive": False, "version": version, "extracted_at": extracted_at, "nodes": nodes, "truncated": False}


def _rule_node(classification: str, *, content_hash: str = "x", source: str = "llm") -> allowlist.RuleNode:
    return {
        "classification": classification,
        "content_hash": content_hash,
        "rationale": "",
        "flags": {},
        "model": "haiku",
        "source": source,
    }


def _rule_entry(
    nodes: dict[str, allowlist.RuleNode], *, reviewed: bool = True, version: str = "1.0.0", extracted_at: str = "old"
) -> allowlist.RuleEntry:
    return {
        "version": version,
        "extracted_at": extracted_at,
        "classified_at": "old",
        "reviewed": reviewed,
        "reviewed_at": None,
        "truncated": False,
        "nodes": nodes,
    }


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
        entry = cast(allowlist.RuleEntry, json.loads(path.read_text()))
        for key, node in entry["nodes"].items():
            assert node["classification"] in known_classifications, f"{path.name}:{key}"
            assert node["source"] in known_sources, f"{path.name}:{key}"
            for flag_name, flag in node["flags"].items():
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
    assert result[allowlist._NO_SUBCOMMANDS_KEY].get("classification") == "dangerous"


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


def test_version_only_refresh_records_new_version_and_keeps_classification():
    existing = _rule_entry({"build": _rule_node("write")}, version="0.0.44", extracted_at="old")
    cached = _cache_entry({}, version="0.0.56", extracted_at="new")
    refreshed = allowlist._version_only_refresh(existing, cached)
    assert refreshed is not None
    assert refreshed["version"] == "0.0.56"
    assert refreshed["extracted_at"] == "new"
    # The whole point: an identical-help upgrade must not send an already-reviewed tool back
    # through the human gate, or reset when it was classified.
    assert refreshed["reviewed"] is True
    assert refreshed["classified_at"] == "old"
    assert refreshed["nodes"] == existing["nodes"]


def test_version_only_refresh_none_when_version_unchanged():
    existing = _rule_entry({}, version="1.0.0")
    assert allowlist._version_only_refresh(existing, _cache_entry({}, version="1.0.0")) is None


def test_version_only_refresh_none_when_no_existing_entry():
    assert allowlist._version_only_refresh(None, _cache_entry({}, version="1.0.0")) is None


def test_diff_nodes_carries_unchanged_node():
    cache_nodes = {"status": _cache_node("abc")}
    existing_nodes = {"status": _rule_node("read_only", content_hash="abc")}
    to_classify, carried, new_invalid = allowlist._diff_nodes(["status"], cache_nodes, existing_nodes, force=False)
    assert to_classify == {}
    assert carried == {"status": existing_nodes["status"]}
    assert new_invalid == {}


def test_diff_nodes_sends_changed_node_to_classify():
    cache_nodes = {"status": _cache_node("new-hash")}
    existing_nodes = {"status": _rule_node("read_only", content_hash="old-hash")}
    to_classify, carried, new_invalid = allowlist._diff_nodes(["status"], cache_nodes, existing_nodes, force=False)
    assert to_classify == {"status": cache_nodes["status"]}
    assert carried == {}
    assert new_invalid == {}


def test_diff_nodes_sends_new_node_to_classify():
    cache_nodes = {"status": _cache_node("abc")}
    to_classify, carried, new_invalid = allowlist._diff_nodes(["status"], cache_nodes, {}, force=False)
    assert to_classify == {"status": cache_nodes["status"]}
    assert carried == {}
    assert new_invalid == {}


def test_diff_nodes_force_resends_even_unchanged_nodes():
    cache_nodes = {"status": _cache_node("abc")}
    existing_nodes = {"status": _rule_node("read_only", content_hash="abc")}
    to_classify, carried, new_invalid = allowlist._diff_nodes(["status"], cache_nodes, existing_nodes, force=True)
    assert to_classify == {"status": cache_nodes["status"]}
    assert carried == {}
    assert new_invalid == {}


def test_diff_nodes_community_source_always_resent_despite_matching_hash():
    cache_nodes = {"status": _cache_node("abc")}
    existing_nodes = {"status": _rule_node("read_only", content_hash="abc", source="community")}
    to_classify, carried, new_invalid = allowlist._diff_nodes(["status"], cache_nodes, existing_nodes, force=False)
    assert to_classify == {"status": cache_nodes["status"]}
    assert carried == {}
    assert new_invalid == {}


def test_diff_nodes_likely_invalid_new_goes_to_new_invalid():
    cache_nodes = {"bogus": _cache_node("abc", likely_invalid=True)}
    to_classify, carried, new_invalid = allowlist._diff_nodes(["bogus"], cache_nodes, {}, force=False)
    assert new_invalid == {"bogus": cache_nodes["bogus"]}
    assert to_classify == {} and carried == {}


def test_diff_nodes_likely_invalid_unchanged_and_already_invalid_is_carried():
    cache_nodes = {"bogus": _cache_node("abc", likely_invalid=True)}
    existing_nodes = {"bogus": _rule_node("invalid", content_hash="abc", source="heuristic")}
    to_classify, carried, new_invalid = allowlist._diff_nodes(["bogus"], cache_nodes, existing_nodes, force=False)
    assert carried == {"bogus": existing_nodes["bogus"]}
    assert new_invalid == {} and to_classify == {}


def test_diff_nodes_likely_invalid_unchanged_but_previously_classified_normally_goes_to_new_invalid():
    # content hash matches, but the prior run hadn't yet flagged it invalid (e.g. _build_tree's
    # heuristic changed, or this is the first run after it started catching this node) — must be
    # re-recorded as invalid, not silently carried forward with its stale non-invalid verdict.
    cache_nodes = {"bogus": _cache_node("abc", likely_invalid=True)}
    existing_nodes = {"bogus": _rule_node("write", content_hash="abc")}
    to_classify, carried, new_invalid = allowlist._diff_nodes(["bogus"], cache_nodes, existing_nodes, force=False)
    assert new_invalid == {"bogus": cache_nodes["bogus"]}
    assert carried == {} and to_classify == {}


def test_assemble_new_nodes_keeps_carried_nodes_verbatim():
    carried = {"status": _rule_node("read_only", content_hash="abc")}
    result = allowlist._assemble_new_nodes(carried, {}, {}, {}, {}, "haiku")
    assert result == carried


def test_assemble_new_nodes_records_new_invalid_with_heuristic_source():
    new_invalid = {"bogus": _cache_node("abc")}
    result = allowlist._assemble_new_nodes({}, new_invalid, {}, {}, {}, "haiku")
    assert result["bogus"]["classification"] == allowlist.Classification.INVALID
    assert result["bogus"]["source"] == allowlist.Source.HEURISTIC
    assert result["bogus"]["flags"] == {}


def test_assemble_new_nodes_applies_verdict_to_classified_node():
    to_classify = {"rm": _cache_node("abc")}
    verdict: allowlist.Verdict = {"rm": {"classification": "dangerous", "rationale": "deletes things"}}
    result = allowlist._assemble_new_nodes({}, {}, to_classify, verdict, {}, "haiku")
    assert result["rm"]["classification"] == "dangerous"
    assert result["rm"]["source"] == allowlist.Source.LLM
    assert result["rm"].get("model") == "haiku"


def test_assemble_new_nodes_downgrades_read_only_dangerous_verb_to_needs_review():
    to_classify = {"clean": _cache_node("abc")}
    verdict: allowlist.Verdict = {"clean": {"classification": "read_only", "rationale": "x"}}
    result = allowlist._assemble_new_nodes({}, {}, to_classify, verdict, {}, "haiku")
    assert result["clean"]["classification"] == allowlist.Classification.NEEDS_REVIEW


def test_assemble_new_nodes_verdict_invalid_short_circuits_before_flags():
    to_classify = {"weird": _cache_node("abc")}
    verdict: allowlist.Verdict = {"weird": {"classification": "invalid", "rationale": "not a real command"}}
    result = allowlist._assemble_new_nodes({}, {}, to_classify, verdict, {}, "haiku")
    assert result["weird"]["classification"] == allowlist.Classification.INVALID
    assert result["weird"]["flags"] == {}


def test_assemble_new_nodes_falls_back_to_existing_node_when_verdict_missing():
    # A failed chunk (or the model dropping a key) must not silently lose existing coverage.
    to_classify = {"push": _cache_node("new-hash")}
    existing_nodes = {"push": _rule_node("write", content_hash="old-hash")}
    result = allowlist._assemble_new_nodes({}, {}, to_classify, {}, existing_nodes, "haiku")
    assert result["push"] == existing_nodes["push"]


def test_assemble_new_nodes_drops_node_entirely_when_no_verdict_and_no_existing():
    to_classify = {"brand-new": _cache_node("abc")}
    result = allowlist._assemble_new_nodes({}, {}, to_classify, {}, {}, "haiku")
    assert "brand-new" not in result


def test_merge_rule_sets_no_change_when_rules_match_existing():
    merged_allow, merged_ask, added_allow, removed_allow, added_ask, removed_ask = allowlist._merge_rule_sets(
        ["Bash(git status:*)"], ["Bash(git push:*)"], ["Bash(git status:*)"], ["Bash(git push:*)"], set()
    )
    assert merged_allow == ["Bash(git status:*)"]
    assert merged_ask == ["Bash(git push:*)"]
    assert not added_allow and not removed_allow and not added_ask and not removed_ask


def test_merge_rule_sets_adds_new_rule():
    merged_allow, merged_ask, added_allow, removed_allow, added_ask, removed_ask = allowlist._merge_rule_sets(
        [], [], ["Bash(git status:*)"], [], set()
    )
    assert merged_allow == ["Bash(git status:*)"]
    assert merged_ask == []
    assert added_allow == {"Bash(git status:*)"}
    assert not removed_allow and not added_ask and not removed_ask


def test_merge_rule_sets_removes_stale_rule_we_previously_wrote():
    # "previous" is our own last-applied manifest — a rule in there but no longer in the fresh
    # allow/ask set is one we generated before and should now remove.
    merged_allow, merged_ask, added_allow, removed_allow, added_ask, removed_ask = allowlist._merge_rule_sets(
        ["Bash(git status:*)"], [], [], [], {"Bash(git status:*)"}
    )
    assert merged_allow == []
    assert merged_ask == []
    assert removed_allow == {"Bash(git status:*)"}
    assert not added_allow and not added_ask and not removed_ask


def test_merge_rule_sets_preserves_rule_user_added_by_hand():
    # Not in `previous` (our manifest) — this was never something we wrote, so even though it's
    # no longer in the fresh allow/ask set, it must survive the merge untouched.
    merged_allow, merged_ask, added_allow, removed_allow, added_ask, removed_ask = allowlist._merge_rule_sets(
        ["Bash(custom-tool:*)"], [], [], [], set()
    )
    assert merged_allow == ["Bash(custom-tool:*)"]
    assert merged_ask == []
    assert not added_allow and not removed_allow and not added_ask and not removed_ask


def test_merge_rule_sets_detects_rule_moving_from_allow_to_ask():
    # Same rule string, different bucket — a real classification change, not a no-op.
    merged_allow, merged_ask, added_allow, removed_allow, added_ask, removed_ask = allowlist._merge_rule_sets(
        ["Bash(docker network:*)"], [], [], ["Bash(docker network:*)"], {"Bash(docker network:*)"}
    )
    assert merged_allow == []
    assert merged_ask == ["Bash(docker network:*)"]
    assert not added_allow
    assert removed_allow == {"Bash(docker network:*)"}
    assert added_ask == {"Bash(docker network:*)"}
    assert not removed_ask


def _stub_registry(monkeypatch, registry: allowlist.Registry, caches: dict[str, allowlist.CacheEntry] | None = None):
    monkeypatch.setattr(allowlist, "_load_registry", lambda: registry)
    monkeypatch.setattr(allowlist, "_load_cache", (caches or {}).get)


def test_compute_claude_rules_mode_covered_drops_ask_but_keeps_classification(monkeypatch):
    # acceptEdits already gates in-scope mkdir; an explicit ask rule would beat that grant and
    # re-prompt every time. The verdict on disk stays "write" — only the rendered output changes.
    _stub_registry(monkeypatch, {"mkdir": {"no_subcommands": True, "mode_covered": True}})
    rules = {"mkdir": _rule_entry({allowlist._NO_SUBCOMMANDS_KEY: _rule_node("write")})}
    allow, ask = allowlist._compute_claude_rules(rules)
    assert allow == []
    assert ask == []
    assert rules["mkdir"]["nodes"][allowlist._NO_SUBCOMMANDS_KEY]["classification"] == "write"


def test_compute_claude_rules_without_mode_covered_still_renders_ask(monkeypatch):
    _stub_registry(monkeypatch, {"mkdir": {"no_subcommands": True}})
    rules = {"mkdir": _rule_entry({allowlist._NO_SUBCOMMANDS_KEY: _rule_node("write")})}
    assert allowlist._compute_claude_rules(rules) == ([], ["Bash(mkdir:*)"])


def test_compute_claude_rules_mode_covered_keeps_read_only_allow(monkeypatch):
    # mode_covered only suppresses the ask side; a read_only node of the same tool is unaffected.
    _stub_registry(monkeypatch, {"tool": {"mode_covered": True}})
    rules = {"tool": _rule_entry({"list": _rule_node("read_only"), "wipe": _rule_node("dangerous")})}
    assert allowlist._compute_claude_rules(rules) == (["Bash(tool list:*)"], [])


def test_compute_claude_rules_global_option_prefixes_add_allow_variants_for_read_only_only(monkeypatch):
    _stub_registry(monkeypatch, {"git": {"global_option_prefixes": ["-C *", "-c *"]}})
    rules = {"git": _rule_entry({"status": _rule_node("read_only"), "push": _rule_node("dangerous")})}
    allow, ask = allowlist._compute_claude_rules(rules)
    assert allow == ["Bash(git status:*)", "Bash(git -C * status:*)", "Bash(git -c * status:*)"]
    # No ask variant: an unmatched `git -C x push` prompts anyway in every mode that prompts.
    assert ask == ["Bash(git push:*)"]


def test_compute_claude_rules_global_option_prefixes_ignored_for_no_subcommands_tool(monkeypatch):
    # `Bash(tool -x * *:*)` would be meaningless — the prefix shape only applies between a tool
    # and a real subcommand.
    _stub_registry(monkeypatch, {"flat": {"no_subcommands": True, "global_option_prefixes": ["-x *"]}})
    rules = {"flat": _rule_entry({allowlist._NO_SUBCOMMANDS_KEY: _rule_node("read_only")})}
    assert allowlist._compute_claude_rules(rules) == (["Bash(flat:*)"], [])


def test_compute_claude_rules_allow_override_replaces_node_ask_and_gets_prefix_variants(monkeypatch):
    # `git add` is honestly `write` on disk; the override only changes what render emits — an
    # allow instead of the ask, with the same -C/-c variants a read_only node would get.
    _stub_registry(monkeypatch, {"git": {"global_option_prefixes": ["-C *"], "allow_overrides": ["add"]}})
    rules = {"git": _rule_entry({"add": _rule_node("write"), "push": _rule_node("dangerous")})}
    allow, ask = allowlist._compute_claude_rules(rules)
    assert allow == ["Bash(git add:*)", "Bash(git -C * add:*)"]
    assert ask == ["Bash(git push:*)"]
    assert rules["git"]["nodes"]["add"]["classification"] == "write"


def test_compute_claude_rules_ask_overrides_render_verbatim_alongside_allow_override(monkeypatch):
    # An allow for the verb plus ask rules for its code-losing flag shapes: ask > allow with no
    # specificity tiebreak means `git reset --hard` prompts while `git reset -q` doesn't. The
    # `* --hard` form is what closes the flag-order hole (`git reset -q --hard`).
    cfg: allowlist.ToolConfig = {
        "allow_overrides": ["reset", "restore --staged"],
        "ask_overrides": ["reset --hard", "reset * --hard"],
    }
    _stub_registry(monkeypatch, {"git": cfg})
    rules = {"git": _rule_entry({"reset": _rule_node("write"), "restore": _rule_node("write")})}
    allow, ask = allowlist._compute_claude_rules(rules)
    assert allow == ["Bash(git reset:*)", "Bash(git restore --staged:*)"]
    # `restore` itself (bare form discards worktree changes) keeps its generated ask.
    assert ask == ["Bash(git restore:*)", "Bash(git reset --hard:*)", "Bash(git reset * --hard:*)"]


def test_compute_claude_rules_allow_override_on_read_only_node_does_not_duplicate(monkeypatch):
    _stub_registry(monkeypatch, {"git": {"allow_overrides": ["fetch"]}})
    rules = {"git": _rule_entry({"fetch": _rule_node("read_only")})}
    assert allowlist._compute_claude_rules(rules) == (["Bash(git fetch:*)"], [])


def test_compute_claude_rules_overrides_ignored_for_unreviewed_tool(monkeypatch):
    # The review gate stays the gate: overrides shape a reviewed tool's output, they don't bypass it.
    _stub_registry(monkeypatch, {"git": {"allow_overrides": ["add"]}})
    rules = {"git": _rule_entry({"add": _rule_node("write")}, reviewed=False)}
    assert allowlist._compute_claude_rules(rules) == ([], [])


def test_coverage_gaps_none_when_every_child_has_own_rule():
    rules = {
        "gh": _rule_entry(
            {
                "run": _rule_node("dangerous"),
                "run view": _rule_node("read_only"),
                "run cancel": _rule_node("write"),
            }
        )
    }
    caches = {"gh": _cache_entry({"run": _cache_node(children=["run view", "run cancel"])})}
    assert allowlist._coverage_gaps(rules, caches) == []


def test_coverage_gaps_flags_child_missing_from_rules_json():
    # The "chunk silently dropped a node" failure mode contributing/cli-allowlist.md documents —
    # the child was discovered by extraction but never made it into rules.json at all.
    rules = {"gh": _rule_entry({"run": _rule_node("dangerous")})}
    caches = {"gh": _cache_entry({"run": _cache_node(children=["run view"])})}
    gaps = allowlist._coverage_gaps(rules, caches)
    assert gaps == [("gh", "run", "run view", "missing from rules.json")]


def test_coverage_gaps_flags_child_stuck_needs_review():
    rules = {"gh": _rule_entry({"run": _rule_node("dangerous"), "run view": _rule_node("needs_review")})}
    caches = {"gh": _cache_entry({"run": _cache_node(children=["run view"])})}
    gaps = allowlist._coverage_gaps(rules, caches)
    assert gaps == [("gh", "run", "run view", "needs_review (excluded from render)")]


def test_coverage_gaps_invalid_child_is_not_a_gap():
    # invalid means "not a real command" (fabricated/duplicate/error-text) — nothing to cover.
    rules = {"helm": _rule_entry({"list": _rule_node("read_only"), "list maudlin-arachnid": _rule_node("invalid")})}
    caches = {"helm": _cache_entry({"list": _cache_node(children=["list maudlin-arachnid"])})}
    assert allowlist._coverage_gaps(rules, caches) == []


def test_coverage_gaps_skips_unreviewed_tools():
    # Nothing renders for an unreviewed tool at all yet (parent or child) — no partial-coverage
    # gap to report until it's reviewed.
    rules = {"sed": _rule_entry({"*": _rule_node("write")}, reviewed=False)}
    caches = {"sed": _cache_entry({"*": _cache_node(children=["*"])})}
    assert allowlist._coverage_gaps(rules, caches) == []


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
