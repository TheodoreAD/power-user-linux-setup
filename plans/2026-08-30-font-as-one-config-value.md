---
status: in-progress
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

## What landed (2026-08-30)

`[settings.fonts]` now declares `family`, `family_mono` and `size`, and nothing else names a font.

- `fonts.monospace_font()` and `fonts.vscode_settings()` derive what `inv fonts.configure` applies,
  replacing six hand-written strings (`monospace`, `terminal`, and four VS Code keys).
  `[settings.fonts.vscode]` survives as a passthrough for keys that are not the font — today just
  `editor.fontLigatures`.
- **`inv fonts.render-configs`** rewrites the four repo-side files that carry their own copy:
  `config/terminator.conf`, `config/wezterm.lua`, both `config/pycharm/*.xml`. A regex per line
  rather than a parser per format — four formats, four lines, and a Lua/XML/Qt-ini parser apiece
  would be far more machinery than they earn.
- A test asserts the committed files already match what the renderer would produce, so a
  `[settings.fonts]` change that skips the render step fails CI rather than leaving one application
  on the old font.

[DECISION: **`[settings.fonts]` rewrites the four files; the files keep naming a font.** The
alternative — files that name no font, filled in at deploy time — is templating, which the sibling
lifecycle plan is deliberately avoiding: its whole layering design turns on whole-file replacement,
and a per-format merge would be the second config language both plans exist to prevent. Each file
also stays readable and deployable on its own this way.]

[DECISION: **it rewrites the repo-side `config/` file, never the deployed copy**, and it is its own
deliberate command rather than part of `inv setup` or the quality gate — `~/AGENTS.md`,
"Regenerating a file from a canonical source". Rewriting only the deployed copy would leave every
one of those paths permanently `DIRTY` against its source, which is precisely the drift the deploy
manifest exists to surface. That standalone command _is_ the "option" the request asked for; a flag
on `fonts.configure` would have been a second way to spell the same thing.]

[DECISION: **two variants, not three spellings** — `family` and `family_mono`, both written in full
everywhere. The plan assumed three (`CaskaydiaCove Nerd Font`, `… Nerd Font Mono`,
`CaskaydiaCove NFM`) and a per-target naming rule to pick between them. Measured 2026-08-30 instead:
Nerd Fonts v3 registers the short name as an alias of the long one, `fc-match` resolves
`CaskaydiaCove NFM` and `CaskaydiaCove Nerd Font Mono` to the same file, and `wezterm ls-fonts`
resolves the long form while printing `AKA: "CaskaydiaCove NFM"`. So the third spelling was never a
third thing. The long form is used everywhere so that a search for the family name finds every
occurrence — which is what made the original inconsistency hard to see.]

[PITFALL: the renderer raises when a substitution matches nothing, and that is the load-bearing
part. A regex that silently matches zero lines leaves the old font in a file the task has just
reported rewriting — and an upstream rename (PyCharm changing an option name) is exactly how that
would happen. Tested.]

[UNVERIFIED: PyCharm accepting the long family name where the file previously said
`CaskaydiaCove NFM`. `fc-match` and WezTerm both confirm the alias resolves, and the JVM takes its
font list from the same fontconfig on Linux, so this is reasoning from one verified case to a very
similar one rather than a measurement. Confirming it needs a PyCharm restart and a look at the
editor — worth doing the next time it is open. The old and new strings name the same file, so the
worst case is cosmetic and one `git revert` away.]

[DEFERRED: `inv verify.all` has no check that the live machine agrees. A drift check ("every place
that names a font names the same one") is cheap once there is a canonical value to compare against,
and is what would have caught this by machine rather than by reading four files. Not worth building
before the canonical value exists.]
