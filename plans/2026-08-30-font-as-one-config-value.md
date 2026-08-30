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

[DECISION: ~~**two variants, not three spellings**~~ — **reversed 2026-08-30, see below.** The
original reasoning, kept because the half about fontconfig is still correct: `family` and
`family_mono`, both written in full everywhere. The plan assumed three (`CaskaydiaCove Nerd Font`,
`… Nerd Font Mono`, `CaskaydiaCove NFM`) and a per-target naming rule to pick between them. Measured
2026-08-30 instead: Nerd Fonts v3 registers the short name as an alias of the long one, `fc-match`
resolves `CaskaydiaCove NFM` and `CaskaydiaCove Nerd Font Mono` to the same file, and
`wezterm ls-fonts` resolves the long form while printing `AKA: "CaskaydiaCove NFM"`. So the third
spelling was never a third thing. The long form is used everywhere so that a search for the family
name finds every occurrence — which is what made the original inconsistency hard to see.]

[PITFALL: the renderer raises when a substitution matches nothing, and that is the load-bearing
part. A regex that silently matches zero lines leaves the old font in a file the task has just
reported rewriting — and an upstream rename (PyCharm changing an option name) is exactly how that
would happen. Tested.]

## The one inference in this plan was wrong (2026-08-30)

The plan had this open:

> [UNVERIFIED: PyCharm accepting the long family name … the JVM takes its font list from the same
> fontconfig on Linux, so this is reasoning from one verified case to a very similar one rather than
> a measurement.]

Measured instead of restarting PyCharm, by asking the runtime PyCharm actually uses — its own
bundled JBR at `~/.local/share/JetBrains/Toolbox/apps/pycharm/jbr/bin/java`:

```
CaskaydiaCove Nerd Font Mono  ->  resolved family: Dialog
CaskaydiaCove NFM             ->  resolved family: CaskaydiaCove NFM
```

`getAvailableFontFamilyNames()` lists only the `NF`/`NFM`/`NFP` forms. `Dialog` is the AWT fallback.

[PITFALL: **the JVM does not use fontconfig for family lookup**, which is the assumption the
reversed decision rested on. It enumerates the family name embedded in the font file — the
abbreviated one — so the long form resolves to `Dialog` and PyCharm renders in a default sans font
while reporting nothing. `fc-match` and `wezterm ls-fonts` agreeing proved only that _fontconfig_
consumers accept either spelling, and every other target here is one. Generalising from them to the
JVM was the error, and the plan named it as an inference at the time.]

**The state this left on the machine, which is worse than the decision:** `editor-font.xml` had said
`CaskaydiaCove Nerd Font` all along — before this plan touched anything — so PyCharm's editor had
been falling back to `Dialog`, and `SECONDARY_FONT_FAMILY = JetBrains Mono` is probably why nobody
noticed. This plan's rewrite of `terminal-font.xml` from `CaskaydiaCove NFM` to the long form would
have broken the terminal the same way; it was never deployed, so the drift that
`plans/2026-08-30-font-as-one-config-value.md` was about is the only reason it did not land.

[DECISION: **four names, not two** — `family`, `family_mono`, `family_short`, `family_mono_short`.
Every fontconfig consumer (GNOME, GNOME Terminal, VS Code, Terminator, WezTerm) takes the long form;
the two PyCharm files take the short. The objection that beat three spellings originally — a grep
for the family name should find every occurrence — is satisfied differently and better: all four
live in one `[settings.fonts]` block, which is the "one place to change it" the plan actually
wanted. A derivation (`Nerd Font Mono` → `NFM`) was rejected as magic that would break on the next
family whose abbreviation is not mechanical.]

A test pins the asymmetry so it is not simplified back: the PyCharm rules must render a `*_short`
name and the terminator/wezterm rules must not.]

## The drift check, built (2026-08-30)

`inv fonts.check` — read-only. It reports every place on this machine that names a font and whether
it agrees with `[settings.fonts]`: the three settings `fonts.configure` applies, and the four files
`fonts.render-configs` writes, **read at their deployed paths** rather than in the repo.

[DECISION: its own read-only task, not a check inside `inv verify.all`. That task aborts on first
failure and is not read-only, and a `config_files` destination the user has customized differs by
design — failing `inv setup` on it would be crying wolf on exactly the mechanism that exists to let
people keep their own config. `wsl.check` and `devcontainer.check` are the shape this follows.]

[DECISION: it asks "does this file name the configured font", not "is this file identical to its
source". The second is `inv deploy.status`'s question and a different one — a seeded config may
legitimately differ everywhere except the font line, which is precisely why three months of
Terminator drift was invisible. Implemented by re-rendering the _deployed_ text with the same rules
`render-configs` uses: if the substitutions change nothing, the file already names the right font.
No second list of paths to keep in sync, and no parser per format.]

It earned itself on its first run, finding a second stale file nobody had looked for —
`terminal-font.xml` still on the pre-standardisation spelling — and then the reversal above.

## What this plan actually cost, on the live machine

Three of the seven consumers were wrong when the plan was written, and none reported it:

| consumer                      | was                           | now                               |
| ----------------------------- | ----------------------------- | --------------------------------- |
| `~/.config/terminator/config` | `JetBrainsMono Nerd Font 13`  | `CaskaydiaCove Nerd Font Mono 12` |
| PyCharm `editor-font.xml`     | long form → `Dialog` fallback | `CaskaydiaCove NF`                |
| PyCharm `terminal-font.xml`   | pre-standardisation spelling  | `CaskaydiaCove NFM`               |

`inv fonts.check` now reports all seven agreeing.

[PITFALL: a `config_files` destination PULSE has never deployed is indistinguishable, in
`deploy.status`, from one the user edited — both are `UNKNOWN`, whose wording is deliberately
non-committal because claiming either would be wrong half the time. The tell is the manifest: absent
from `~/.local/state/power-user-linux-setup/deployed.json` means never written here, and the
apparent "drift" may simply be a config that was never applied in the first place. Worth checking
before concluding a user customized something.]

## Migrated to

Landed and verified 2026-08-30. `inv fonts.check` reports all seven consumers agreeing.

- **The code** — `[settings.fonts]`'s four names in `setup.toml`, `tasks/fonts.py` (`_named`, the
  `_RENDERS` rules, `render-configs`, and the new `check`), `tasks/util.py`'s `FontsSettings`. The
  asymmetry that matters is pinned by
  `tests/unit/test_fonts.py::test_pycharm_takes_the_abbreviated_family_and_everything_else_the_long_one`,
  so a future simplification back to one spelling fails CI rather than silently sending PyCharm to
  `Dialog`.
- **Usage** — [`docs/fonts.md`](../docs/fonts.md), "Changing the font": the four names, the two
  tasks plus `inv ide.configure-pycharm`, `inv fonts.check`, and the fontconfig-vs-JVM warning with
  the measured `Dialog` output.
- **Design rationale** — the `setup.toml` comment above `[settings.fonts]` carries why there are
  four names rather than two, which is where someone about to "tidy" them will be standing.

**Not migrated:** the `deploy.status`-cannot-tell-never-deployed-from-edited pitfall. It is about
`deploy.py`'s classifier rather than about fonts, and it is already recorded where that mechanism is
documented — see `contributing/deploy.md` and `plans/2026-08-29-dotfiles-repo-config-lifecycle.md`,
which owns that surface.
