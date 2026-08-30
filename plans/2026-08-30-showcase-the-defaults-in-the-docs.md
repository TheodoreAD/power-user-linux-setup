---
status: idea
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
chain is the feature. Related: `plans/2026-08-30-font-as-one-config-value.md`, which is about making
it changeable in one place. Documenting it as a feature and making it changeable belong together — a
feature nobody has documented is one nobody changes.

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

[NEEDS CLARIFICATION: does this want a "what you get" page in `docs/`, or edits spread across the
existing per-topic pages? A single page reads like a feature tour and is what an evaluator wants;
per-topic edits keep each fact next to its mechanism and avoid a second place to keep current.
Leaning: per-topic edits plus a short linked list on `docs/index.md`, because a feature tour is the
kind of page that rots first — nothing fails when it goes stale.]

[NEEDS CLARIFICATION: how much belongs in `README.md` rather than the docs site? The README is what
a stranger reads first and currently sells the repo on breadth (what it installs). The statusline in
particular is a better hook than any package list. Unclear how much of the site's content should be
duplicated there versus linked.]

[NEEDS CLARIFICATION: is a screenshot or an ANSI capture worth it for the statusline and the prompt?
Both are visual, and describing colour semantics in prose is exactly where a picture wins. Against:
an image in a docs site is a maintenance burden that goes stale silently, and this repo has none
today — adopting the first one is a decision beyond this plan.]

## Recommended direction

Fix the wrong thing first, then surface, then write:

1. **`docs/zsh.md`'s "first run only"** is an inaccuracy, not a gap — it tells users to overwrite a
   good default. One paragraph, no new page.
2. **Point at what already exists.** `docs/index.md` gains a short "what you get" list linking to
   the terminal layout, the fonts page and the prompt. Cheap, and it fixes the wezterm case
   outright.
3. **Write the statusline up**, in `docs/claude-code.md` or its own page — it is the only one of the
   four with no feature-level documentation anywhere, and the only one whose audience is not
   Linux-specific.
4. **The font's dependency chain** — Nerd Font → prompt icons, statusline glyphs, editor ligatures —
   stated once on `docs/fonts.md`, and linked from the others rather than repeated.

Do this alongside `plans/2026-08-30-font-as-one-config-value.md` where they touch the same page.

[PITFALL: this is documentation of _current behaviour_, and `~/AGENTS.md`'s "Don't stash future work
in prose docs" applies with full force — no "planned", no "coming soon", no dated status lines. If a
feature is not there yet it belongs in a plan, not on the site.]
