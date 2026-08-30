---
status: in-progress
updated: 2026-08-30
---

# The good defaults are undocumented as features

## Context

Fallout from `plans/2026-08-29-dotfiles-repo-config-lifecycle.md`'s file-by-file audit of `config/`,
2026-08-30. That audit set out to find peculiarities to move into a private repo and found none —
every candidate was ruled a deliberate public default. The user's framing:

> the wezterm split is something that could be a default because it makes life much easier when you
> start it, it could be documented as a power user feature in the site docs (…) the font is most
> certainly there to stay, it's a feature of pulse, and we should mention it in the site docs (…)
> the statusline is definitely something we want to show case, it's very neat and there are a lot of
> claude users (…) the p10k config is also to keep public as a default, maybe let the user know they
> can customize it.

The gap this exposes: several of the repo's best defaults are documented as **mechanism** — which
file deploys where, by which task — and nowhere as **features** a reader would want. Someone
evaluating PULSE learns that `config/wezterm.lua` is deployed through `config_files`, not that their
terminal opens as a maximized 2×2 grid with `ALT+1..4` jumps.

## What each one needs, from reading the current docs

**The WezTerm startup layout.** [`docs/terminal.md`](../docs/terminal.md) already documents it
properly — "Startup layout", the custom bindings table, how to start un-maximized. The content is
there and is good. What is missing is that nothing points at it: `docs/index.md` never mentions it,
so it is only found by someone who already opened the terminal page. This is a surfacing problem,
not a writing one.

**The font.** [`docs/fonts.md`](../docs/fonts.md) covers install mechanics and the v2→v3 migration
in detail, and says which font is set where. It does not say why a Nerd Font is the point — the
prompt icons, the statusline glyphs and the editor ligatures all depend on it, and that dependency
chain is the feature. Making it changeable in one place landed 2026-08-30 (`docs/fonts.md`), so only
the "why a Nerd Font at all" half is still owed here — a feature nobody has documented is one nobody
changes.

**The Claude Code statusline.** [`docs/claude-code.md`](../docs/claude-code.md) mentions
`statusline` only as an installation side effect (which task writes it, which prompt defaults to
decline). Nothing describes what the line actually shows. From
[`config/statusline-command.sh`](../config/statusline-command.sh)'s own header, all of it deliberate
and some of it researched:

- model name coloured by weight — haiku gray, sonnet green, opus orange, fable red
- context window as tokens in K with a pie glyph (`○ ◔ ◑ ◕ ●`), coloured by **absolute** token count
  rather than percentage, because Anthropic's own usage page flags ">150k context" as more expensive
  regardless of window size — its own breakpoints, deliberately not the generic ones
- both rate-limit windows (5h and 7d), each coloured by its own used percentage
- session cost, rounded up to whole dollars, on the same muted palette
- icons taken from powerlevel10k's own nerdfont-complete table so the line matches the prompt

That is the most novel thing in `config/`, it is 285 lines, and it is invisible to anyone reading
the docs. It is also the item with the widest audience — every Claude Code user, whether or not they
run Linux.

**The p10k prompt.** [`docs/zsh.md`](../docs/zsh.md) currently says the wrong thing:

> **First run only** — configure the Powerlevel10k prompt interactively: `p10k configure`

PULSE ships a vetted `config/p10k.zsh` and `inv zsh.configure-p10k` seeds it, so the wizard is not a
first-run step — it is optional customization, and running it blind replaces a working prompt with
whatever the wizard's questions produce. `docs/index.md`'s own "Manual steps" table already has this
right ("use when the baseline doesn't suit you"), so the two pages disagree. Fix `docs/zsh.md`, and
say what the baseline gives you.

## Open questions

[DECISION: **per-topic edits plus a short linked list on `docs/index.md`**, not a feature-tour page.
A tour page reads well for an evaluator and is the kind of page that rots first, because nothing
fails when it goes stale — whereas a fact kept next to its own mechanism is re-read by whoever
changes that mechanism. Confirmed by what the writing turned up: three of the four items needed
their _mechanism_ page corrected (a wrong instruction on `zsh.md`, a stale size on `fonts.md`, no
description at all on `claude-code.md`), which a separate tour page would have left untouched while
looking complete.]

[NEEDS CLARIFICATION: how much belongs in `README.md` rather than the docs site? The README is what
a stranger reads first and currently sells the repo on breadth (what it installs). The statusline in
particular is a better hook than any package list. Unclear how much of the site's content should be
duplicated there versus linked.]

[NEEDS CLARIFICATION: is a screenshot or an ANSI capture worth it for the statusline and the prompt?
Both are visual, and describing colour semantics in prose is exactly where a picture wins. Against:
an image in a docs site is a maintenance burden that goes stale silently, and this repo has none
today — adopting the first one is a decision beyond this plan.]

## What landed (2026-08-30)

All four, in the order the plan proposed:

1. **`docs/zsh.md`'s "first run only"** — replaced with a `## The prompt` section describing the
   baseline, verified against `config/p10k.zsh`'s own wizard-options header rather than paraphrased,
   plus how to change it and how to get back.
2. **`docs/index.md` gained a "What you get, out of the box" section** — five entries, one line and
   a link each. Deliberately not a feature tour page, per the leaning in the open question below.
3. **`docs/claude-code.md` gained `## The statusline`** — every segment, and why the thresholds are
   what they are.
4. **`docs/fonts.md` gained "Why this is load-bearing"** — the dependency chain, plus a table of
   where each application learns the font, stated as it is rather than as it should be.

Two things found while writing, both fixed in place: `docs/fonts.md`'s existing table gave the font
size as 13 where `setup.toml` says 12, and said "three places" over four rows.

[PITFALL: the first draft of the fonts section wrote "swap `[settings.fonts]` for any other
installed family", which is **not true today** — that setting reaches GNOME and VS Code only, while
Terminator, WezTerm and PyCharm each carry the font in their own file. Caught by re-reading against
the (now retired) font plan's own measurement before committing. Documenting the consolidated
behaviour a sibling plan is proposing is the exact failure mode this plan's own closing PITFALL
warns about, and it nearly happened in the same session that wrote the warning.

Since 2026-08-30 the consolidated claim **is** true — `[settings.fonts]` drives all seven consumers
and `inv fonts.check` verifies it — so this section can now say what the first draft wanted to.]

[PITFALL: the same draft duplicated the CaskaydiaCove/OFL rationale that `docs/fonts.md` already
carried further down under "Default font". Found by reading the whole page rather than the section
being edited. A second copy of a rationale is worse than none — both go stale, and neither is
obviously the authority.]

[UNVERIFIED: the anchors were checked with a throwaway reimplementation of
`markdown.extensions.toc`'s slugify, matched against an existing link in the repo
(`configuration.md#whole-file-configs-config_files`) to confirm the algorithm. Every cross-page and
in-page anchor in `docs/` resolves. The docs site has no link checker in the quality gate, so
nothing catches the next one — see the DEFERRED below.]

[PITFALL: this is documentation of _current behaviour_, and `~/AGENTS.md`'s "Don't stash future work
in prose docs" applies with full force — no "planned", no "coming soon", no dated status lines. If a
feature is not there yet it belongs in a plan, not on the site.]

[DEFERRED: no link checker runs on the docs. `lychee` was assessed for this repo before (its
`lychee-bin` PyPI wrapper is a 78 MB wheel with one release ever, which is why it was not adopted),
but an internal-anchor check needs no network and no such dependency — the throwaway script used
above is about fifteen lines. Worth adding to the gate the next time a dangling anchor is found,
rather than on the strength of this one.]

[DEFERRED: the two remaining open questions stay open — whether any of this belongs in `README.md`,
and whether the statusline and prompt deserve a screenshot. Neither blocked the writing, and both
are better answered by someone looking at the rendered site.]
