---
status: idea
updated: 2026-08-27
---

# Split inline code spans across this repo's markdown

## Context

Turned up incidentally on 2026-08-27 while harvesting an unrelated session in `ingesta`. The user
noticed markdown "broken into equal length rows, cutting off words" and asked for a check.

Roughly 68 inline code spans in this repo carry a **newline inside the backticks**:

```
generated from real `--help` output instead of hand-written guesses, and `inv
allowlist.apply` can
keep `~/.claude/settings.json` current from it automatically. `tasks/
allowlist.py` implements it as
```

Rendered, a newline inside a code span folds to a space, so a browser shows `inv allowlist.apply`
and nothing looks wrong. **Raw text is what suffers**, and raw text is what agents read: `AGENTS.md`
lines 151-154 are in this shape, and that file is loaded into every session in this repo. the
`python-conventions` skill's `SKILL.md` had one at line 112 (`` `python -O` ``) that arrived in a
live session's context split across two lines the moment the skill loaded. It has been repaired; the
rest have not.

### Scale

Measured with the detector below, excluding fenced blocks:

- **136 lines** with an unbalanced backtick count, across **29 files** — about 68 split spans.
  (`CLAUDE.md` symlinks `AGENTS.md`, so a couple of those files are the same content counted twice.)
- Spread across `docs/`, `plans/`, `contributing/`, `skills/`, `AGENTS.md` and `CONTRIBUTING.md` —
  not concentrated anywhere, which is what makes it look like an authoring habit rather than one bad
  edit.

That count is as of 2026-08-27 and includes the `skills/` tree, which has since moved to
`agent-skills` — so the repair work is now split across two repos, and the corpus to re-measure
against is the family rather than this repo. The scale finding is unaffected: the habit is the
author's, not any one repo's.

### It is not dprint, which was the obvious suspect

[PITFALL: dprint neither creates these nor repairs them, so "just run `dprint fmt`" does nothing and
the defect is permanent once written. Verified 2026-08-27 with two probes against this repo's own
config (`lineWidth` 100, `textWrap: "always"`):

- Given a code span straddling column 100, dprint treats the span as **atomic** and wraps _after_
  it, leaving a 99-character line and the span intact. It will not split one.
- Given an already-split span on two lines totalling 68 characters — trivially joinable — dprint
  leaves it exactly as-is, because a code span's contents are preserved verbatim.

So each of these was authored that way and then locked in: every subsequent `dprint fmt` and
`dprint check` passes on it forever.]

That points at the author hand-wrapping prose to ~100 columns and letting the break land between
backticks. Given how much of this repo's markdown is agent-written, and that pre-wrapping markdown
at ~100 columns is exactly what an LLM does, the likely author of most of them is an agent — which
also means the rate will keep climbing unless something checks for it.

## Recommended direction

Two separable pieces; the second matters more than the first.

1. **Repair the existing 68.** Mechanical: join each span onto one line and let `dprint fmt` rewrap
   the paragraph. Worth doing in one pass per directory rather than one giant commit, and worth
   eyeballing each — a few are inside tables or list items where the rewrap changes more than the
   one line.
2. **Add a check so it cannot recur.** The detection is a one-liner and needs no new dependency:

   ````shell
   awk 'FNR==1{f=0} /^ *```/{f=!f; next} !f{n=gsub(/`/,"`"); if(n%2) print FILENAME":"FNR}' <files>
   ````

   It toggles on fenced blocks and reports any line whose backtick count is odd. Spot-checked
   against six hits in four files on 2026-08-27, all six genuine; it has not been run against a
   corpus with deliberate edge cases (a literal backtick in prose, `double-backtick` spans).

Do the check first if only one gets done. Repairing without it just resets a counter that climbs
again.

## Open questions

[NEEDS CLARIFICATION: Where the check belongs. `repo-tasks`' quality tasks would give it to every
repo in the family at once, which is where the value is — `ingesta` had one too, in its own
`AGENTS.md`, found by the same scan. Against that: it is a markdown-prose rule, and `repo-tasks`'
quality gate is otherwise a thin wrapper over real tools rather than a home for bespoke `awk`. A
dprint plugin or an existing markdown linter may already cover it and would be the better answer if
so — check before writing anything custom.]

[NEEDS CLARIFICATION: Whether the detector's heuristic is good enough to gate CI on. An odd backtick
count is a proxy, not a parse. Before it fails anyone's build it should be run against every
markdown file in the family and every hit triaged, so the false-positive rate is a measured number
rather than an assumption.]

[NEEDS CLARIFICATION: Whether anything should also address the cause rather than the symptom — a
line in `~/AGENTS.md` telling agents not to break inside a code span when wrapping markdown. That is
the always-loaded file and it is already well over its own size guidance, so this may be exactly the
kind of cheap-and-recoverable rule that belongs in a check instead. See
`contributing/global-agents-md.md`'s admission criteria.]
