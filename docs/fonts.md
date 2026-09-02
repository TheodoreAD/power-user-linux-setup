# Fonts

Nerd Fonts patches popular programming fonts with thousands of extra glyphs (icons, powerline
symbols, devicons) required for a feature-rich terminal and editor experience.

## Why this is load-bearing

The font is not a cosmetic preference here — three other things PULSE configures are drawn from its
glyph set, and all three degrade to boxes without it:

- the [shell prompt](zsh.md#the-prompt)'s directory, branch and status icons
  (`POWERLEVEL9K_MODE=nerdfont-complete`);
- the [Claude Code statusline](claude-code.md#the-statusline)'s clock, calendar and context-fill
  glyphs, taken from powerlevel10k's own icon table so the two lines match;
- editor ligatures in VS Code and PyCharm.

So the same family is set everywhere rather than left to each application's default.

## Changing the font

It is named in exactly one place — `[settings.fonts]` in `setup.toml`:

```toml
[settings.fonts]
family = "CaskaydiaCove Nerd Font" # editors: icons at full width, ligatures
family_mono = "CaskaydiaCove Nerd Font Mono" # terminals: icons forced to one cell
family_short = "CaskaydiaCove NF" # the same two, as the JVM enumerates them
family_mono_short = "CaskaydiaCove NFM"
size = 12
```

Two variants, because a terminal needs every glyph to occupy exactly one cell and an editor does not
— and each in two spellings, because PyCharm will only accept one of them (see the warning below).
Everything else derives from these values, through two tasks:

```shell
inv fonts.configure       # GNOME, GNOME Terminal, VS Code — settings on the live machine
inv fonts.render-configs  # rewrites config/terminator.conf, config/wezterm.lua, config/pycharm/*.xml
inv deploy.all            # pushes those rewritten files to ~
inv ide.configure-pycharm # ...and the PyCharm pair, whose destination is discovered at run time
```

`inv fonts.check` is the read-only counterpart: it reports every place on this machine that names a
font — the three settings and the four files, read at their deployed paths — and whether each agrees
with `[settings.fonts]`. Run it if a single application looks wrong.

The split is what each application will accept: GNOME and VS Code take a setting, while Terminator,
WezTerm and PyCharm read a config file, so their copy of the font lives in this repo and has to be
rewritten rather than set. `render-configs` is a separate deliberate command whose output is
committed and reviewed like any other change — it is not run by `inv setup`, and a test fails if the
committed files stop matching `[settings.fonts]`, so a font change that skips it is caught in CI
rather than leaving one application on the old font.

!!! warning "PyCharm needs the short name — the long one silently falls back"

    Nerd Fonts v3 registers an abbreviation for every family — `NFM` for `Nerd Font Mono`, `NF` for
    `Nerd Font` — and both name the same file. Every **fontconfig** consumer resolves either:
    `fc-match` and `wezterm ls-fonts` agree, and WezTerm even prints the alias. So GNOME, GNOME
    Terminal, VS Code, Terminator and WezTerm all get the long form, which is what a search for the
    family name finds.

    **The JVM does not go through fontconfig for family lookup.** It enumerates the family name
    embedded in the font file, which is the abbreviation. Measured 2026-08-30 with PyCharm's own
    bundled JBR:

    ```
    CaskaydiaCove Nerd Font Mono  ->  resolved family: Dialog
    CaskaydiaCove NFM             ->  resolved family: CaskaydiaCove NFM
    ```

    `Dialog` is the fallback. PyCharm given the long name renders in a default sans font and reports
    nothing — which is why the two PyCharm files take `family_short`/`family_mono_short`, and why
    `inv fonts.check` exists.

Which family, and why that one: [Default font](#default-font-caskaydiacove-nerd-font) below.

## Install

```shell
inv fonts.install    # downloads all families to ~/.local/share/fonts, rebuilds font cache
inv fonts.configure  # sets CaskaydiaCove Nerd Font Mono as system monospace, GNOME Terminal, and VS Code
```

Both run as part of `inv setup`. Re-running is safe:

- If v3 files are present (compact filenames like `JetBrainsMonoNerdFont-Regular.ttf`), the family
  is skipped.
- If only v2 files are present (spaced filenames like
  `JetBrains Mono Regular Nerd Font Complete.ttf`), they are removed and v3 is downloaded
  automatically.
- If nothing is present, v3 is downloaded fresh.

!!! hint "Troubleshooting"

    Font files go to `~/.local/share/fonts/`. Ubuntu rebuilds the font cache automatically within a few seconds; close any open application before changing its font.

    If fonts are missing from listings, check permissions: files should be `644`, the directory `755`.

## Dry run

Check which families are already installed without downloading anything:

```shell
PULSE_DRY_RUN=1 inv fonts.install
```

Check current font configuration versus what `inv fonts.configure` would set:

```shell
PULSE_DRY_RUN=1 inv fonts.configure
```

Sample output:

```
[fonts] CascadiaCode: ok
[fonts] JetBrainsMono: ok (v2 — will upgrade)
[fonts] SourceCodePro: MISSING
...
[fonts] system monospace: ok
[fonts] GNOME Terminal: MISSING  (current: 'Monospace 12')
[fonts] VS Code: ok
```

`ok (v2 — will upgrade)` means the family is installed but as v2 — the next live run will remove the
old files and install v3.

## Default font — CaskaydiaCove Nerd Font

CaskaydiaCove Nerd Font is the Nerd Fonts project's patched version of Microsoft's
[Cascadia Code](https://github.com/microsoft/cascadia-code). The name change is required by the OFL
(Open Font License) **Reserved Font Name** clause in Cascadia Code's license — any modified version
must be distributed under a different name.

`inv fonts.configure` sets it as the default in these places:

| Context                        | Font                            | Why                                                                               |
| ------------------------------ | ------------------------------- | --------------------------------------------------------------------------------- |
| System monospace (`gsettings`) | CaskaydiaCove Nerd Font Mono 12 | Used by GNOME Terminal, gedit, and all GTK apps that respect the system monospace |
| GNOME Terminal profile         | CaskaydiaCove Nerd Font Mono 12 | Explicit override; single-width icons fit the terminal cell grid                  |
| VS Code editor                 | CaskaydiaCove Nerd Font         | Default variant; double-width icons render correctly, ligatures enabled           |
| VS Code integrated terminal    | CaskaydiaCove Nerd Font Mono    | Mono for the terminal grid inside VS Code                                         |

Terminator, WezTerm and PyCharm get the same font from their own config files — see
[Changing the font](#changing-the-font). For JetBrains IDEs that is `inv ide.configure-pycharm`,
which writes the editor and terminal font options directly; setting them by hand under Settings →
Editor → Font works too, but PyCharm rewrites those files itself, so the task is what puts them
back.

## Font variants (Nerd Fonts v3)

Each family ships three variants per weight:

| Variant | Filename suffix | Best for                                                        |
| ------- | --------------- | --------------------------------------------------------------- |
| Default | `NerdFont`      | Editors — icons use full visual width, ligatures work correctly |
| Mono    | `NerdFontMono`  | Terminals — icons forced to exactly one cell width              |
| Propo   | `NerdFontPropo` | Proportional contexts (rare)                                    |

`inv fonts.install` installs all three variants for every family so you can switch freely without
re-running the installer.

## CascadiaCode NF vs CaskaydiaCove NF — naming explained

Two distributions of the same upstream font exist:

| Name                        | Source                                  | Notes                                                                               |
| --------------------------- | --------------------------------------- | ----------------------------------------------------------------------------------- |
| **CaskaydiaCove Nerd Font** | Nerd Fonts project (`CascadiaCode.zip`) | Renamed due to OFL RFN; bundled with all other Nerd Font families                   |
| **Cascadia Code NF**        | Microsoft (official, since April 2024)  | Microsoft's own first-party Nerd Font variant; not subject to RFN since they own it |

This setup uses CaskaydiaCove because it ships in the same zip as all other families and is updated
in sync with them. The Microsoft variant is equally valid — to use it instead, replace the
`CascadiaCode` entry in `setup.toml` with the Microsoft release URL and an appropriate `check` glob.

## Installed families

Families are declared in `setup.toml` under `[[settings.fonts.families]]`. Each entry has:

| Field    | Purpose                                                                                                                                                            |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `zip`    | Release asset stem — downloaded from `/releases/latest/download/<zip>.zip`                                                                                         |
| `family` | Substring matched against `fc-list` output (case-insensitive); used for dry-run status. Works for both v2 and v3. Can be a list for families with OFL RFN renames. |
| `check`  | Glob matched against `~/.local/share/fonts/`; detects v3 files specifically (v2 filenames don't match). If no match, legacy cleanup + download runs.               |
| `legacy` | List of globs for v2 files to remove before installing v3. Safe to run when empty (nothing to remove).                                                             |

| `zip`           | Installed as            | Notes                                                  |
| --------------- | ----------------------- | ------------------------------------------------------ |
| `CascadiaCode`  | CaskaydiaCove Nerd Font | **Default everywhere** — ligatures, all three variants |
| `JetBrainsMono` | JetBrainsMono Nerd Font | Clean, no ligatures by default                         |
| `SourceCodePro` | SauceCodePro Nerd Font  | Adobe → renamed via OFL RFN                            |
| `Meslo`         | MesloLG Nerd Font       | Popular for Powerlevel10k                              |
| `RobotoMono`    | RobotoMono Nerd Font    | —                                                      |
| `FiraCode`      | FiraCode Nerd Font      | Strong ligature set                                    |
| `FiraMono`      | FiraMono Nerd Font      | FiraCode without ligatures; v3 ships `.otf` not `.ttf` |
| `Ubuntu`        | Ubuntu Nerd Font        | Ubuntu system font, patched                            |
| `UbuntuMono`    | UbuntuMono Nerd Font    | —                                                      |

To add a family, append a `[[settings.fonts.families]]` entry to `setup.toml`.

The default font and VS Code settings are also in `setup.toml` under `[settings.fonts]` — edit
`monospace`, `terminal`, and `[settings.fonts.vscode]` to change the configured font without
touching any Python.

## See also

- [Terminal](terminal.md) — one of the applications that reads this font setting
- [Zsh](zsh.md) — the prompt whose glyphs need it
- [Claude Code](claude-code.md) — the statusline that draws with the same glyph set
