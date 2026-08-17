# Fonts

Nerd Fonts patches popular programming fonts with thousands of extra glyphs (icons, powerline
symbols, devicons) required for a feature-rich terminal and editor experience.

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

`inv fonts.configure` sets it as the default in three places:

| Context                        | Font                            | Why                                                                               |
| ------------------------------ | ------------------------------- | --------------------------------------------------------------------------------- |
| System monospace (`gsettings`) | CaskaydiaCove Nerd Font Mono 13 | Used by GNOME Terminal, gedit, and all GTK apps that respect the system monospace |
| GNOME Terminal profile         | CaskaydiaCove Nerd Font Mono 13 | Explicit override; single-width icons fit the terminal cell grid                  |
| VS Code editor                 | CaskaydiaCove Nerd Font         | Default variant; double-width icons render correctly, ligatures enabled           |
| VS Code integrated terminal    | CaskaydiaCove Nerd Font Mono    | Mono for the terminal grid inside VS Code                                         |

For JetBrains IDEs: Settings → Editor → Font → set **CaskaydiaCove Nerd Font** (or Mono for the
embedded terminal under Tools → Terminal).

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
