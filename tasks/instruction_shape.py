"""Measure the prose shape of an agent instruction file: how much of it instructs.

`plans/2026-09-12-imperative-vs-rationale-in-instruction-files.md` measured
`~/.agents/AGENTS.md` against 182 community `AGENTS.md`/`CLAUDE.md` files and found the gap is not
in how many imperatives it carries (39.6% of sentences against a 36.5% mean) but in how many words
each one is wrapped in — 1.7 directives per 100 words against 3.4, in 23-word sentences against
11.5. Those numbers only mean something re-run the same way, which is why this is a module rather
than the scratchpad script it started as.

Sentence-granularity and deliberately crude. Each sentence is scored *independently* for a directive
and for rationale/provenance, so a sentence carrying both is counted as mixed rather than being
forced into one bucket — the mixing is the thing under test, so it cannot be a classification
tie-break.

The lexicons are the measurement. Two notes on what is deliberately not in them:

- `rather than` and `instead of` are **not** rationale markers. They are the contrastive half of a
  directive ("translate rather than reach for the old spelling"), and counting them overstated the
  mixed rate by a third on the first pass.
- `since` only counts followed by a pronoun or article. Bare `since` is temporal far more often than
  causal in these files, and a date-adjacent `since 2026-09-04` is not a justification.
"""

from __future__ import annotations

import re
import statistics
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

# Base-form verbs that open a directive when they are the sentence's first word. Long by design: a
# short list silently reclassifies whole rules as description, and the failure is invisible because
# the count still looks plausible.
# Kept as whitespace-separated text rather than a list literal so the set stays readable and
# diffable at this length; a list would be reformatted onto one 2,000-character line.
_IMPERATIVE_VERB_TEXT = """
    add aim allow amend apply ask assert assume avoid base be branch build bump call catch change
    check checkout choose clean clone close commit compare configure confirm consider convert copy
    count create declare default define delete deploy describe design detect disable do document
    drop edit enable ensure escape expect explain export expose extend extract fetch file fill find
    finish fix focus follow format generate give go grep group handle have hold ignore implement
    import include increment inline insert inspect install invoke keep kill label launch leave let
    limit link list load lock log look maintain make mark match measure mention merge mind mount
    move name note notify open order pass pick pin place plan point prefer prepare preserve print
    prioritize proceed profile prompt propose prove provide prune publish pull push put quote raise
    read reach rebase recheck record refactor refer reference register reject release remember
    remove rename render repeat replace report request require reset resolve respect respond restore
    restrict return reuse revert review rewrite run save say scope search see select send separate
    set ship show simplify skip sort specify split stage start state stay stick stop store structure
    submit support sync tag take target tell test think throw tidy track translate treat trim trust
    try turn understand update upgrade use validate verify wait watch work wrap write
"""

IMPERATIVE_VERBS = frozenset(_IMPERATIVE_VERB_TEXT.split())

DEONTIC = re.compile(
    r"\b(?:"
    r"must(?:\s+not)?|shall(?:\s+not)?|should(?:n't|\s+not)?|"
    r"never|always|don'?t|do\s+not|cannot|can'?t|may\s+not|"
    r"has\s+to|have\s+to|needs?\s+to|ought\s+to|"
    r"required|mandatory|forbidden|prohibited|disallowed|"
    r"avoid|ensure|make\s+sure|be\s+sure"
    r")\b",
    re.IGNORECASE,
)

RATIONALE = re.compile(
    r"\b(?:"
    r"because|since\s+(?:the|it|that|this|they|we|you|a|an|its|their)|"
    r"the\s+reason|that\s+is\s+why|which\s+is\s+why|this\s+is\s+why|"
    r"rationale|so\s+that|in\s+order\s+to|otherwise|hence|therefore|thus|"
    r"as\s+a\s+result|the\s+point\s+is|the\s+goal\s+is|the\s+idea\s+is|"
    r"trade-?off|the\s+cost\s+is|the\s+risk\s+is|the\s+benefit\s+is|"
    r"chosen\s+over|was\s+rejected|were\s+rejected|"
    r"this\s+means|which\s+means|meaning\s+that|the\s+effect\s+is|"
    r"why\s+(?:this|that|it|we|the)"
    r")\b",
    re.IGNORECASE,
)

NARRATIVE = re.compile(
    r"(?:"
    r"\b(?:19|20)\d\d-\d\d-\d\d\b|"
    r"\bmeasured\b|\bobserved\b|\bcaught\b|\breproduced\b|\bconfirmed\b|"
    r"\ba\s+session\b|\bone\s+session\b|\bthe\s+session\b|"
    r"\bturned\s+out\b|\bwas\s+found\b|\bwe\s+found\b|\bwe\s+hit\b|"
    r"\bwe\s+ran\s+into\b|\bincident\b|\bpreviously\b|\bused\s+to\b|"
    r"\bhistorically\b|\bin\s+the\s+past\b|\bhappened\b|\bonce\s+(?:a|the|we|it)\b"
    r")",
    re.IGNORECASE,
)

# Nuance/exemption clauses. `obra/superpowers`' writing-skills reports that appending one nuance
# clause to a directive that tested clean degraded it from consistent to noisy, so this is tracked
# separately from rationale even though both are "extra words around the imperative".
HEDGE = re.compile(
    r"\b(?:"
    r"unless|except\s+(?:when|where|for|in|that|a|the)|"
    r"only\s+(?:when|where|if|for|to|after|while)|but\s+only|"
    r"the\s+exception|one\s+exception|exempt|"
    r"does\s+not\s+apply|doesn'?t\s+apply|"
    r"is\s+fine|stays?\s+fine|are\s+fine|still\s+(?:fine|legitimate|ok|okay)|"
    r"almost\s+(?:always|never)|usually|normally|typically|generally|"
    r"in\s+most\s+cases"
    r")\b",
    re.IGNORECASE,
)

_FENCE = re.compile(r"^\s*(?:```|~~~)")
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s")
_BULLET = re.compile(r"^\s*(?:[-*+]\s|\d+[.)]\s)")
_TABLE = re.compile(r"^\s*\|")
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`]*`")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_EMPH = re.compile(r"[*_]{1,3}")
_FIRST_WORD = re.compile(r"^[^A-Za-z']*([A-Za-z']+)")

# Split on terminal punctuation only when the next character could open a sentence. A bare
# `(?<=[.!?])\s+` splits `inv quality.precommit` and every version number in the file.
_SENT_SPLIT = re.compile(r"(?<=[.!?:;])\s+(?=[A-Z(\[`*_\"'])")

# Below this, a sentence is a fragment (a table cell, a stray label) and scoring it adds noise.
_MIN_SENTENCE_WORDS = 3


def strip_markdown(text: str) -> str:
    """Reduce markup to the prose under it, replacing code spans with a neutral token.

    Inline code becomes ` CODE ` rather than being deleted, so a sentence's word count still
    reflects that something was said there — deleting it would make command-dense rules look
    artificially terse, which is the direction this measurement must not be biased in.
    """
    text = _HTML_COMMENT.sub(" ", text)
    text = _LINK.sub(r"\1", text)
    text = _INLINE_CODE.sub(" CODE ", text)
    return _EMPH.sub("", text)


@dataclass(frozen=True)
class Structure:
    """Line-level counts, kept apart from the sentence scoring because they answer a different
    question: whether the file is written as a list or as prose."""

    lines: int = 0
    headings: int = 0
    bullets: int = 0
    code_lines: int = 0
    table_lines: int = 0
    para_lines: int = 0
    bullet_words: int = 0

    @property
    def bullet_share(self) -> float:
        """Bullets as a share of content lines. The community median is 74%; prose-first files run
        near zero, which is a register choice rather than a defect on its own."""
        content = self.bullets + self.para_lines
        return round(self.bullets * 100 / content, 1) if content else 0.0

    @property
    def mean_bullet_words(self) -> float:
        return round(self.bullet_words / self.bullets, 1) if self.bullets else 0.0


def split_blocks(text: str) -> tuple[list[str], Structure]:
    """Split markdown into prose blocks, one per paragraph or list item, plus structural counts.

    Fenced code, headings and table rows are counted and dropped. Headings are dropped rather than
    scored because a trigger-named heading is a retrieval cue, not a sentence — scoring
    "About to commit" as a non-directive would penalise exactly the convention this repo wants.
    """
    blocks: list[str] = []
    lines = headings = bullets = code_lines = table_lines = para_lines = bullet_words = 0
    in_fence = False
    para: list[str] = []

    def flush() -> None:
        if para:
            blocks.append(" ".join(para))
            para.clear()

    for line in text.splitlines():
        lines += 1
        if _FENCE.match(line):
            in_fence = not in_fence
            code_lines += 1
            continue
        if in_fence:
            code_lines += 1
            continue
        if _HEADING.match(line):
            headings += 1
            flush()
            continue
        if _TABLE.match(line):
            table_lines += 1
            continue
        if not line.strip():
            flush()
            continue
        if _BULLET.match(line):
            flush()
            body = _BULLET.sub("", line, count=1)
            bullets += 1
            bullet_words += len(body.split())
            blocks.append(body)
            continue
        para_lines += 1
        para.append(line.strip())
    flush()

    return blocks, Structure(
        lines=lines,
        headings=headings,
        bullets=bullets,
        code_lines=code_lines,
        table_lines=table_lines,
        para_lines=para_lines,
        bullet_words=bullet_words,
    )


def split_sentences(block: str) -> list[str]:
    stripped = strip_markdown(block).strip()
    if not stripped:
        return []
    parts = (p.strip() for p in _SENT_SPLIT.split(stripped))
    return [p for p in parts if len(p.split()) >= _MIN_SENTENCE_WORDS]


def is_directive(sentence: str) -> bool:
    """True when the sentence tells the reader to do or not do something.

    Two ways to qualify, and both are needed: a deontic modal anywhere ("never pipe …"), or a
    base-form verb in first position ("Run the repo's quality gate first"). Position-only misses
    every prohibition written as a clause; modal-only misses every plain imperative.
    """
    if DEONTIC.search(sentence):
        return True
    match = _FIRST_WORD.match(sentence)
    if not match:
        return False
    return match.group(1).lower().rstrip("'") in IMPERATIVE_VERBS


@dataclass(frozen=True)
class Shape:
    """One file's measurement. Percentages are rounded for display; keep the raw counts for any
    comparison, since rounding two files to one decimal and subtracting invents precision."""

    path: Path
    sentences: int
    words: int
    directives: int
    mixed: int
    hedged: int
    structure: Structure

    @property
    def directive_pct(self) -> float:
        return round(self.directives * 100 / self.sentences, 1) if self.sentences else 0.0

    @property
    def mixed_pct(self) -> float:
        return round(self.mixed * 100 / self.sentences, 1) if self.sentences else 0.0

    @property
    def hedged_pct(self) -> float:
        """Share of *directives* carrying a nuance clause — not of all sentences, since a hedge in a
        descriptive sentence costs nothing."""
        return round(self.hedged * 100 / self.directives, 1) if self.directives else 0.0

    @property
    def directives_per_100_words(self) -> float:
        return round(self.directives * 100 / self.words, 1) if self.words else 0.0

    @property
    def mean_sentence_words(self) -> float:
        return round(self.words / self.sentences, 1) if self.sentences else 0.0


def measure_text(text: str, path: Path) -> Shape | None:
    """Measure one file's text, or None when there is too little prose to say anything.

    The floor is deliberate: a stub `AGENTS.md` that only points at a README would otherwise land in
    an aggregate as a 100%-something outlier built on four sentences.
    """
    blocks, structure = split_blocks(text)
    sentences = [s for block in blocks for s in split_sentences(block)]
    words = sum(len(s.split()) for s in sentences)
    if not sentences or words < 60:
        return None

    directives = mixed = hedged = 0
    for sentence in sentences:
        if not is_directive(sentence):
            continue
        directives += 1
        if RATIONALE.search(sentence) or NARRATIVE.search(sentence):
            mixed += 1
        if HEDGE.search(sentence):
            hedged += 1

    return Shape(
        path=path,
        sentences=len(sentences),
        words=words,
        directives=directives,
        mixed=mixed,
        hedged=hedged,
        structure=structure,
    )


def measure_file(path: Path) -> Shape | None:
    return measure_text(path.read_text(encoding="utf-8", errors="replace"), path)


INSTRUCTION_FILENAMES = ("AGENTS.md", "CLAUDE.md", "GEMINI.md", "QWEN.md", "AGENT.md")


def measure_tree(root: Path) -> list[Shape]:
    """Every instruction file under `root`, measured. Sorted by path so two runs are diffable."""
    found = (p for p in sorted(root.rglob("*.md")) if p.name in INSTRUCTION_FILENAMES)
    return [shape for p in found if (shape := measure_file(p))]


HEADER = f"{'mix%':>5} {'hedg%':>6} {'dir%':>5} {'d/100w':>7} {'sentW':>6} {'bul%':>5} {'words':>6}  path"


def format_row(shape: Shape, *, label: str | None = None) -> str:
    return (
        f"{shape.mixed_pct:>5} {shape.hedged_pct:>6} {shape.directive_pct:>5} "
        f"{shape.directives_per_100_words:>7} {shape.mean_sentence_words:>6} "
        f"{shape.structure.bullet_share:>5} {shape.words:>6}  {label or shape.path}"
    )


def summarise(shapes: list[Shape]) -> list[str]:
    """Mean and median rows for a corpus.

    Both, because they disagree usefully here: the community mixed-rate mean is 1.0% against a
    median of 0.0%, which says most files never mix at all and a few do it a lot. A mean alone would
    read as "everyone mixes a little".
    """
    if not shapes:
        return []

    columns: dict[str, list[float]] = {
        "mixed_pct": [s.mixed_pct for s in shapes],
        "hedged_pct": [s.hedged_pct for s in shapes],
        "directive_pct": [s.directive_pct for s in shapes],
        "directives_per_100_words": [s.directives_per_100_words for s in shapes],
        "mean_sentence_words": [s.mean_sentence_words for s in shapes],
        "bullet_share": [s.structure.bullet_share for s in shapes],
        "words": [float(s.words) for s in shapes],
    }
    widths = (5, 6, 5, 7, 6, 5, 6)

    def line(name: str, central: Callable[[list[float]], float]) -> str:
        cells = (f"{round(central(values), 1):>{w}}" for values, w in zip(columns.values(), widths, strict=True))
        return f"{' '.join(cells)}  {name}"

    return [
        line(f"MEAN of {len(shapes)} files", statistics.mean),
        line("MEDIAN", statistics.median),
    ]
