"""Content invariants for the `~/AGENTS.md` fragments and their evidence file.

`config/agents-md/*.md` holds the rules that get assembled into `~/AGENTS.md`;
`contributing/global-agents-md.md` holds each rule's evidence "under a heading matching the rule's
own, so rule and evidence stay findable from each other by name" (that file's own words). Nothing
enforced that correspondence, so it drifted both ways: a rule was renamed and its evidence section
kept the old trigger, and two rules had no section at all while carrying dated provenance inline —
the arrangement the fragment/evidence split exists to prevent. Found by hand 2026-08-30 during the
leanness pass (`plans/2026-08-26-agents-md-leanness-pass.md`); these tests are what keeps it found.

These read the real repo files rather than fixtures: the invariant is about this repo's actual
content, not about any function's behaviour. See tests/README.md.
"""

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parents[2]  # tests/unit/<this file> → repo root
_FRAGMENTS = _REPO_ROOT / "config" / "agents-md"
_EVIDENCE = _REPO_ROOT / "contributing" / "global-agents-md.md"

# Sections of the evidence file that document the file itself rather than any one rule.
_META_SECTIONS = frozenset(
    {
        "Admitting a new rule",
        "Why the deployed file is shaped this way",
        "Re-measuring the deployed file",
        "Contents",
        "Bash & the CLI allowlist (cluster intro)",
    }
)

# Rules that legitimately have no evidence: an exact instruction carrying its own worked example, or
# a stated user preference, which is not a finding and has nothing to confirm. Adding a name here is
# a claim that the rule rests on no measurement — if it rests on one, the measurement goes in the
# evidence file instead.
_EVIDENCE_FREE = frozenset(
    {
        "sudo",
        "Installing agent instructions and skills on this machine",
        "Pushing to a personal repo's default branch",
        "Setting up a repo's agent instructions and skills",
        "Designing a generator or multi-mode tool",
        "Invited to push back",
        "Caveman-style terse output",
        "Which sessions load this file",
    }
)


def _rule_headings() -> list[str]:
    return [
        m.group(1)
        for path in sorted(_FRAGMENTS.glob("*.md"))
        if path.name != "README.md"
        for m in re.finditer(r"^### (.+)$", path.read_text(), re.MULTILINE)
    ]


def _evidence_headings() -> list[str]:
    return re.findall(r"^## (.+)$", _EVIDENCE.read_text(), re.MULTILINE)


def test_every_rule_has_an_evidence_section_or_is_declared_evidence_free():
    missing = [r for r in _rule_headings() if r not in _evidence_headings() and r not in _EVIDENCE_FREE]
    assert not missing, (
        f"rules with no section in {_EVIDENCE.name}: {missing}. Either add one (criterion 3: dated "
        f"confirmations live there, not inline in the deployed file) or add the rule to _EVIDENCE_FREE."
    )


def test_every_evidence_section_still_matches_a_live_rule():
    rules = set(_rule_headings())
    orphans = [e for e in _evidence_headings() if e not in rules and e not in _META_SECTIONS]
    assert not orphans, (
        f"sections in {_EVIDENCE.name} matching no rule heading: {orphans}. A renamed rule leaves its "
        f"evidence behind under the old trigger — retitle the section to match, or fold it under the "
        f"rule that absorbed it."
    )


def test_declared_evidence_free_rules_still_exist():
    """_EVIDENCE_FREE is a list of exemptions, and an exemption for a deleted rule hides the next one."""
    stale = sorted(_EVIDENCE_FREE - set(_rule_headings()))
    assert not stale, f"_EVIDENCE_FREE names rules that no longer exist: {stale}"


def test_no_new_rule_carries_dated_provenance_inline():
    """A `Measured <date>` / `Confirmed <date>` sentence in a fragment belongs in the evidence file.

    Instructions compete for attention with inline narrative, which is why that file exists at all.
    The four grandfathered below are a different shape from the standalone incident paragraphs moved
    out on 2026-08-30: each is woven into the sentence that carries the instruction, and in at least
    the ssh case the incident is doing the deterring. Whether they move is a content decision, open
    on `plans/2026-08-26-agents-md-leanness-pass.md`; this test's job meanwhile is that the list
    does not grow.
    """
    grandfathered = {
        ("portable.md", "Measured 2026-08-28"),  # Reading a command's result — the gh poll loop
        ("this-setup.md", "Confirmed 2026-08-28"),  # git fetch/push — the three passphrase dialogs
        ("this-setup.md", "Confirmed 2026-08-29"),  # git fetch/push — export vs per-call prefix
        ("this-setup.md", "Measured 2026-08-26"),  # Installing a tool — the two PyPI wrappers
    }
    dated = re.compile(r"(?:Measured|Confirmed|Reaffirmed|Validated|Verified|Observed) 2026-\d\d-\d\d")
    found = {
        (path.name, m.group(0))
        for path in sorted(_FRAGMENTS.glob("*.md"))
        if path.name != "README.md"
        for m in dated.finditer(path.read_text())
    }
    assert not found - grandfathered, (
        f"new dated provenance inline in a fragment, move it to {_EVIDENCE.name}: {sorted(found - grandfathered)}"
    )
    assert not grandfathered - found, (
        f"grandfathered provenance no longer present — drop it from the list: {sorted(grandfathered - found)}"
    )
