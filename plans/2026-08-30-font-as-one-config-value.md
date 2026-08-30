---
status: idea
updated: 2026-08-30
---

# One font, five places, two sources of truth

## Context

Raised by the user 2026-08-30, while settling what moves out of `config/` in
`plans/2026-08-29-dotfiles-repo-config-lifecycle.md`:

> the font is most certainly there to stay, it's a feature of pulse (…) we can make the font
> something in a config, and perhaps make it an option that pulse can update the configs with the
> font where needed, but keeps the current one as the default.

The font is the same everywhere — CaskaydiaCove Nerd Font at 12pt, the family PULSE itself installs
from `[settings.fonts] families`. What differs is how each consumer of it learns the name.

**Driven from `setup.toml`'s `[settings.fonts]`, by `inv fonts.configure`:**

| target                         | key                                                 |
| ------------------------------ | --------------------------------------------------- |
| GNOME, all GTK apps            | `monospace` → `org.gnome.desktop.interface`         |
| GNOME Terminal default profile | `terminal` → the profile's `font`/`use-system-font` |
| VS Code `settings.json`        | `[settings.fonts.vscode]`, merged                   |

**Hard-coded in a repo-side file, learned by nobody:**

| file                               | how it names the font                                  |
| ---------------------------------- | ------------------------------------------------------ |
| `config/terminator.conf`           | `font = CaskaydiaCove Nerd Font Mono 12`               |
| `config/wezterm.lua`               | `wezterm.font "CaskaydiaCove NFM"`, `font_size = 12.0` |
| `config/pycharm/editor-font.xml`   | `FONT_FAMILY` = `CaskaydiaCove Nerd Font`, size 12     |
| `config/pycharm/terminal-font.xml` | `FONT_FAMILY` = `CaskaydiaCove NFM`, size 12           |

So changing the machine's font today means editing `[settings.fonts]` **and** four files, in four
formats, with the family spelled three different ways (`CaskaydiaCove Nerd Font`,
`CaskaydiaCove Nerd Font Mono`, `CaskaydiaCove NFM` — the last two are the same family, and `NFM` is
the Nerd Fonts abbreviation wezterm resolves). Miss one and the machine is subtly inconsistent in a
way nothing reports.

Confirmed 2026-08-30 by reading all five. Nothing is broken today; the values agree. The cost is
that they agree _by hand_.

## Open questions

[NEEDS CLARIFICATION: which direction — does `[settings.fonts]` become the source that rewrites the
four files, or do those files stop naming a font at all? Rewriting is what the user's phrasing
suggests ("pulse can update the configs with the font where needed"), and it keeps each file
readable and deployable on its own. Not naming a font would mean templating or per-format injection,
which the lifecycle plan is deliberately avoiding — that plan's whole layering design turns on
whole-file replacement rather than patching.]

[NEEDS CLARIFICATION: if PULSE rewrites them, what does it rewrite — the repo-side `config/` file,
or the deployed copy? Rewriting the repo source makes the change reviewable and commits it like any
other, which matches "Regenerating a file from a canonical source" in `~/AGENTS.md`. Rewriting only
the deployed copy would make every one of these paths permanently `DIRTY` against its source, which
is exactly the drift the deploy manifest exists to surface.]

[NEEDS CLARIFICATION: the three spellings. A single `family = "CaskaydiaCove Nerd Font"` cannot be
substituted verbatim into all four — terminator and GNOME want the `Mono` variant with a trailing
size, wezterm wants the `NFM` abbreviation, PyCharm wants the bare family in one file and `NFM` in
the other. Either the config carries the variants explicitly, or the writer knows a per-target
naming rule. The first is honest and slightly verbose; the second is the kind of implicit knowledge
that rots.]

[NEEDS CLARIFICATION: is this opt-in? The user said "an option that pulse can update the configs
with the font where needed". An option implies a flag or a setting; the alternative is that it is
simply what `inv fonts.configure` does. Note `fonts.configure` already mutates the live GNOME
session, so it is not a read-only task and this would not change its character.]

## Recommended direction

Establish one canonical font declaration in `[settings.fonts]`, carrying the variants explicitly
rather than deriving them, and have a task rewrite the four repo-side files from it — reviewed and
committed like any other regeneration, never auto-run as part of `fix`/`check`/`precommit`, per
`~/AGENTS.md`'s rule on regenerating from a canonical source. Keep the current values as the default
so nothing changes for anyone who does not ask.

Worth doing only alongside `plans/2026-08-30-showcase-the-defaults-in-the-docs.md`: the reason to
make the font one value is that the font is a PULSE feature people should be able to change in one
place, and a feature nobody has documented is one nobody changes.

[DEFERRED: `inv verify.all` has no check that the five agree. A drift check ("every place that names
a font names the same one") is cheap once there is a canonical value to compare against, and is what
would have caught this by machine rather than by reading four files. Not worth building before the
canonical value exists.]
