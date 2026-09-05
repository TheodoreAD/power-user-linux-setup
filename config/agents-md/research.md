## Research & design

### About to author content, config, or a workaround from scratch

Check whether an actively-maintained external project already provides it — a `.gitignore`, a rule
set, a template, any reusable artifact — and search properly before concluding it doesn't: "the
first thing I checked didn't have it" and a single internal tool's "nothing relevant" are weak
signals, not conclusions. The same bar applies to designing a new skill or convention (a real
web/GitHub prior-art pass before finalizing). Within one tool, prefer its built-in feature over a
hand-rolled equivalent even when the built-in carries a documented trade-off — unless that trade-off
is _verified_ risky (grep/test for concrete breakage), not just theoretically possible.

**When the upstream tool falls short, verify its result rather than reimplement it.** The gap is
usually narrower than it looks and the reimplementation is permanent: the `skills` CLI announces a
Claude Code symlink it does not create, and PULSE covers exactly that gap instead of taking over
skill installation. Check what the tool actually did, fill what it missed, and let it keep owning
the rest.

### Choosing a tool or library

For a real selection decision with trade-offs, go deeper than a single-pass web-search summary
(actual CLI walkthroughs, real config examples) — or explicitly flag the research as search-summary
depth and offer to go deeper before the choice is treated as final.

Across a project's concerns, default to the best-fit tool per concern rather than consolidating onto
fewer technologies for its own sake (YAGNI still applies to speculative needs). Exception: when the
explicit goal is fewer options for an _agent_ pattern-matching off existing code, fewer routine
defaults wins over specialization.

### About to ask the user something factual [Claude Code]

Check whether it has a discoverable answer first — `AskUserQuestion` is for decisions genuinely the
user's to make (a real preference, a trade-off with no objectively better side), not for lookups a
web search resolves, however tempting the quick multiple-choice framing.

### Designing a generator or multi-mode tool

Default to independent, combinable axes/flags, each gating a small module, over one top-level enum
branching into near-duplicate trees — ask whether the "modes" are really orthogonal concerns
conflated into one axis. Design the user-facing interaction as a first-class concern: minimal
necessary prompts, skip what doesn't apply, concrete examples in helper text, and first-run output
that doesn't read as a diff against unchosen branches.

### Designing a uv tool-install or shared-dependency mechanism

Two traps: `uv tool install --with-executables-from <dep> <pkg>` only adds _extra_ console scripts
from `<dep>` — a package with zero `[project.scripts]` of its own still fails to install as a tool.
And `dependency-groups` (PEP 735) are per-project, never inherited through a regular dependency — a
shared package that wants consumers to pick up its tool list needs an explicit mechanism (a task
editing the consumer's own `pyproject.toml`, or an optional-dependencies extra).

### Adding a flag, or changing what a tool does by default

Match the surrounding ecosystem's shape (check the wrapped CLI's own flags too) rather than
inventing a bespoke one. For confirmation prompts that means apt/dnf's: prompt on by default,
`-y`/`--yes` to skip — never an opt-in `--confirm`; `rm -i`'s inverted shape is only for the
genuinely destructive-by-default. And don't add a bypass flag that overrides a marker/manifest the
tool uses to decide what it owns — that gives ownership two meanings, one with the flag and one
without; no hacks that complicate the mental model unless the alternative is utterly impractical.

Least surprise, in the form that bites beyond flag shape: **when you change what a tool already
does, the documented behaviour stays the default and the departure is opt-in** — most sharply when
the tool is a shared dependency, where "default" means every consumer's next upgrade. A change that
only some call sites get is worse than either choice made whole, because the tool then has two
behaviours and no rule saying which applies. If the departure has an audience that genuinely needs
it by default, reach that audience through their environment rather than by moving the default under
everyone else.

### Naming around a collision

Use the full, unambiguous canonical name (e.g. "power-user-linux-setup"), not a new compound short
alias (e.g. "pulse-setup") — an alias that half-repeats the disambiguating word reads as awkward,
not clean. Offer a short form only if asked, or where the full name is genuinely unwieldy (an env
var prefix).

### Installing a tool on this machine [needs setup.toml]

Never as a one-off manual step (`curl | bash`, a release tarball into `~/.local/bin`,
`gh extension install`) — every tool is a `[packages.<name>]` entry in `power-user-linux-setup`'s
`setup.toml`, installed by its `inv` task, or the machine silently diverges from its own setup and
the next machine never gets it. Look for a maintained PyPI wrapper first (`shellcheck-py`,
`shfmt-py`, `actionlint-py`, `act-bin` — `method = "uv-tool"`) before any other method, so setup
stays one mechanism deep; "maintained" means its version tracks the upstream release, checked
against the upstream changelog, not assumed. Judge the wrapper from its own PyPI file list
(`curl -s https://pypi.org/pypi/<name>/json`), never from a search summary: platform-tagged wheels
mean the binary ships inside one, an sdist alone means it fetches at install time, and the file
sizes and release count are the adoption cost. It goes wrong in both directions: a summary claimed
`hadolint-py` downloads at install and it was nearly rejected for a false reason (it ships real 12
MB wheels), while `lychee-bin` turned out to be a 78 MB wheel with exactly one release ever, which
reversed a decision already made to adopt it. A tool a repo's quality gate or test tasks run also
goes in that repo's dependency group — the user-wide install is for the human at the shell, the
group is what CI and consumers resolve.
