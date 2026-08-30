"""Content invariants for the `~/AGENTS.md` fragments and their evidence file.

`config/agents-md/*.md` holds the rules that get assembled into `~/AGENTS.md`;
`contributing/global-agents-md.md` holds each rule's evidence "under a heading matching the rule's
own, so rule and evidence stay findable from each other by name" (that file's own words). Nothing
enforced that correspondence, so it drifted both ways: a rule was renamed and its evidence section
kept the old trigger, and six rules carried dated provenance inline — the arrangement the
fragment/evidence split exists to prevent. Found by hand 2026-08-30 during the leanness pass
(`plans/2026-08-26-agents-md-leanness-pass.md`); these tests are what keeps it found.

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
        "What this setup provisions (cluster intro)",
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


# A trailing `[Claude Code]` / `[needs direnv]` is a dependency label, not part of the rule's name:
# it says what the rule assumes, and the evidence file keys on the name. Stripped everywhere a
# heading is compared, so relabelling a rule never looks like renaming one.
_LABEL = re.compile(r"\s*\[[^\]]+\]$")


def _rule_headings() -> list[str]:
    return [
        _LABEL.sub("", m.group(1))
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


def _labels() -> list[tuple[str, str]]:
    """(rule name, label) for every labelled rule."""
    return [
        (m.group(1), m.group(2))
        for path in sorted(_FRAGMENTS.glob("*.md"))
        if path.name != "README.md"
        for m in re.finditer(r"^### (.+?)\s*\[([^\]]+)\]$", path.read_text(), re.MULTILINE)
    ]


def test_every_dependency_label_is_from_the_known_vocabulary():
    """Two shapes only: `[Claude Code]`, or `[needs <thing>]`.

    An open vocabulary is how a label set stops meaning anything — a reader cannot tell whether
    `[Claude]` and `[Claude Code]` are the same claim, and neither can a grep.
    """
    bad = [(r, lb) for r, lb in _labels() if lb != "Claude Code" and not lb.startswith("needs ")]
    assert not bad, f"labels outside the vocabulary (`Claude Code` / `needs …`): {bad}"


def test_a_needs_label_naming_a_package_names_one_that_exists():
    """`[needs direnv]` is a checkable claim, and this is the check.

    Only bare identifiers are tested: a label may also name a file or a mechanism (`needs
    setup.toml`, `needs PULSE's zprofile`), which no `[packages.*]` entry corresponds to. The point
    is that a label naming a package cannot quietly outlive it — the rule it labels stops being true
    when the package goes, which is exactly when nobody is looking at the label.
    """
    declared = set(re.findall(r"^\[packages\.([\w.-]+)\]", (_REPO_ROOT / "setup.toml").read_text(), re.MULTILINE))
    missing = [
        (rule, label)
        for rule, label in _labels()
        if (dep := label.removeprefix("needs ")) != label and re.fullmatch(r"[\w-]+", dep) and dep not in declared
    ]
    assert not missing, f"labels naming a package that setup.toml does not declare: {missing}"


def test_no_rule_carries_a_dated_confirmation_inline():
    """A `Measured <date>` / `Confirmed <date>` attribution belongs in the evidence file, not a rule.

    Criterion 3's subject is the *date*, not the story. A rule may still narrate the failure it
    prevents — "a session read the failure as a missing key, and had the user type a passphrase into
    three dialogs" earns its place, because it names the wrong move the reader is about to make and
    nobody takes a reference hop before making it. What does not earn its place is the dated
    attribution, which is provenance: it settles who confirmed what and when, a question no session
    is asking mid-task, and instructions compete for attention with inline narrative.
    """
    # `\s+`, not a literal space: dprint reflows prose to 100 columns and will happily put the verb
    # at the end of one line and the date at the start of the next. A single-space pattern passed
    # clean on a fragment that had exactly that shape (2026-08-30) — the formatter, not the author,
    # decides where the line break falls, so any pattern spanning two words has to allow one.
    dated = re.compile(r"(?:Measured|Confirmed|Reaffirmed|Validated|Verified|Observed)\s+2026-\d\d-\d\d")
    offenders = [
        f"{path.name}: {' '.join(m.group(0).split())}"
        for path in sorted(_FRAGMENTS.glob("*.md"))
        if path.name != "README.md"
        for m in dated.finditer(path.read_text())
    ]
    assert not offenders, (
        f"dated confirmation inline in a fragment: {offenders}. Move the date and the fuller account "
        f"to {_EVIDENCE.name}; the narrative itself may stay if it names the failure being prevented."
    )


def test_no_rule_dates_itself_relative_to_another_rule():
    """ "Confirmed the same day" is only as good as the absolute date next to it.

    Which is precisely what the test above removes. One such phrase dangled the instant its
    paragraph's date moved to the evidence file (2026-08-30) — it had pointed two paragraphs up,
    survived the edit, and read as though it still meant something. A relative date in a fragment
    has nothing left to be relative to, so it belongs in the evidence file with the dates.
    """
    # Anchored to a provenance verb, because "the same session" has two meanings in these files and
    # only one of them is a date. "`Read`, `Edit` and `Write` all stay available in the same session"
    # is the claim itself — the scope over which the behaviour holds — and must not be flagged;
    # "verified in the same session" is provenance that outlived the date it pointed at.
    relative = re.compile(
        r"(?:[Cc]onfirmed|[Mm]easured|[Vv]erified|[Oo]bserved|[Rr]eproduced)[^.]{0,40}?"
        r"the (?:same (?:day|session|week)|day before)"
    )
    offenders = [
        f"{path.name}: {m.group(0)}"
        for path in sorted(_FRAGMENTS.glob("*.md"))
        if path.name != "README.md"
        for m in relative.finditer(path.read_text())
    ]
    assert not offenders, f"relative date in a fragment with no absolute date to anchor it: {offenders}"
