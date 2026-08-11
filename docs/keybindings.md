# Keybindings

Reference for every binding that uses the Super (Windows) key on this setup, so it's clear what
to expect and where a given shortcut is defined. Pulled from live `gsettings`/`dconf` state on
2026-08-08 — re-verify with the commands shown if extensions or GNOME defaults change.

See [input_devices.md](input_devices.md) for why a bare Super _tap_ might not register at all
(Kinesis Super_L/Super_R issue).

## Tap-to-open overview

```shell
gsettings get org.gnome.mutter overlay-key   # 'Super_L'
```

Tapping (press+release with no other key) Super alone opens the Activities overview. This is a
separate mechanism from the `Super+<key>` combos below — it only recognizes the `Super_L` keysym,
not `Super_R`.

## GNOME defaults — `org.gnome.desktop.wm.keybindings`

| Binding                                         | Action                                    |
| ----------------------------------------------- | ----------------------------------------- |
| `Super+Tab`                                     | Switch applications                       |
| `Shift+Super+Tab`                               | Switch applications, backward             |
| `Super+Above_Tab`                               | Switch windows of current app             |
| `Shift+Super+Above_Tab`                         | Switch windows of current app, backward   |
| `Super+h`                                       | Minimize window                           |
| `Super+d`, `Primary+Super+d`                    | Show desktop                              |
| `Super+space`                                   | Switch input source (next)                |
| `Shift+Super+space`                             | Switch input source (previous)            |
| `Super+Home`                                    | Switch to workspace 1                     |
| `Super+End`                                     | Switch to last workspace                  |
| `Super+Page_Up` / `Super+Page_Down`             | Switch to workspace left / right          |
| `Shift+Super+Home`                              | Move window to workspace 1                |
| `Shift+Super+End`                               | Move window to last workspace             |
| `Shift+Super+Page_Up` / `Shift+Super+Page_Down` | Move window to workspace left / right     |
| `Shift+Super+Up/Down/Left/Right`                | Move window to monitor up/down/left/right |

## GNOME defaults — `org.gnome.shell.keybindings`

| Binding                           | Action                                            |
| --------------------------------- | ------------------------------------------------- |
| `Super+a`                         | Toggle application (app grid) view                |
| `Super+s`                         | Toggle Quick Settings                             |
| `Super+v`, `Super+m`              | Toggle message tray / notifications               |
| `Super+n`                         | Focus active notification                         |
| `Super+1`..`Super+9`              | Switch to application N (position in the taskbar) |
| `Super+Ctrl+1`..`Super+Ctrl+9`    | Open new window of application N                  |
| `Super+Alt+Up` / `Super+Alt+Down` | Shift overview up / down                          |

## GNOME defaults — `org.gnome.mutter.keybindings`

| Binding              | Action                          |
| -------------------- | ------------------------------- |
| `Super+p`            | Switch monitor / display layout |
| `Super+Shift+Escape` | Cancel input capture            |

## Tiling Shell (`tilingshell@ferrarodomenico.com`)

Tiling Shell records the native bindings it overrides in its own `overridden-settings` dconf key
(so it can restore them if disabled) and implements the actual Super+Arrow tiling itself:

```shell
dconf read /org/gnome/shell/extensions/tilingshell/overridden-settings
```

| Binding                      | Action                                                                                                         |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `Super+Left` / `Super+Right` | Tile window to a side / snap zone (replaces native `toggle-tiled-left/right`, which this extension blanks out) |
| `Super+Up`                   | Maximize                                                                                                       |
| `Super+Down`                 | Unmaximize (also `Alt+F5`)                                                                                     |
| drag near screen edge        | Edge tiling (`org.gnome.mutter edge-tiling` forced `true`)                                                     |

**Known conflict:** `tiling-assistant@ubuntu.com` (ships enabled by default on fresh Ubuntu 24.04)
writes to the same gsettings keys — `inv gnome.extensions` auto-disables it when Tiling Shell is
active. See [gnome_extensions.md](gnome_extensions.md).

## Dash to Panel (`dash-to-panel@jderose9.github.com`)

Doesn't bind Super itself — it visualizes the native `Super+1..9` shortcuts above by showing
number overlays on pinned/running app icons while Super is held:

```shell
dconf read /org/gnome/shell/extensions/dash-to-panel/hotkeys-overlay-combo   # 'TEMPORARILY'
```

## Advanced Alt-Tab Window Switcher (`advanced-alt-tab@G-dH.github.com`)

Replaces the handler behind `Super+Tab` / `Shift+Super+Tab` (still the same native keybinding
above) with a searchable, filterable switcher instead of GNOME's default. No separate dconf-level
binding of its own — check its extension preferences dialog for any custom shortcuts added there.

## Custom shortcuts

Ad-hoc `Ctrl`/`Alt`-based custom shortcuts (e.g. Flameshot) are managed separately — see
[shortcuts.md](shortcuts.md). None currently use Super.

## Re-checking this list

```shell
gsettings list-recursively org.gnome.desktop.wm.keybindings | grep -i super
gsettings list-recursively org.gnome.shell.keybindings | grep -i super
gsettings list-recursively org.gnome.mutter.keybindings | grep -i super
dconf dump /org/gnome/shell/extensions/ | grep -B5 -i super
```
