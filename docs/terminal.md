# Terminal

[WezTerm](https://wezterm.org/) is the configured terminal ([`packages.wezterm`] in `setup.toml`,
installed from the project's nightly `.deb`). Its whole config is one Lua file,
[`config/wezterm.lua`](https://github.com/TheodoreAD/power-user-linux-setup/blob/master/config/wezterm.lua),
deployed to `~/.config/wezterm/wezterm.lua`.

[`packages.wezterm`]: configuration.md#whole-file-configs-config_files

WezTerm reloads its config automatically when the file changes — no restart needed for a keybinding
or font tweak. The `gui-startup` hook is the exception (see [Startup layout](#startup-layout)).

## Startup layout

The window opens maximized, split into a 2x2 grid of panes, with the top-left focused:

```text
2560 x 1440 maximized → 4 panes @ ~125 cols x 28 rows each

┌──────────────────┬──────────────────┐
│                  │                  │
│   pane 0         │   pane 1         │
│   ALT+1          │   ALT+2          │
│                  │                  │
├──────────────────┼──────────────────┤
│                  │                  │
│   pane 2         │   pane 3         │
│   ALT+3          │   ALT+4          │
│                  │                  │
└──────────────────┴──────────────────┘
```

Four panes on a 1440p display leaves each one fairly short (~28 rows). `CTRL+SHIFT+Z` is what makes
that workable — it zooms the focused pane to fill the whole tab, and the same key restores the grid.
Read a long agent transcript zoomed, drop back to the grid to see everything at once.

!!! note "The layout applies to the first window only"

    WezTerm's `gui-startup` event fires once, when the process starts. A new tab (`CTRL+SHIFT+T`) or
    a new window (`CTRL+SHIFT+N`) opens with a single pane — split it by hand with `CTRL+SHIFT+"`
    (horizontal) and `CTRL+SHIFT+%` (vertical).

The split order in the config is deliberate: it creates the row divider first, then splits each row.
Pane indices follow position in the split tree, so building it that way makes them read left-to-
right, top-to-bottom, which is what the `ALT+<n>` bindings assume. Check the live numbering with:

```shell
wezterm cli list
```

## Keybindings

Custom bindings from `config/wezterm.lua`:

| Binding             | Action                                                  |
| ------------------- | ------------------------------------------------------- |
| `CTRL+Tab`          | Next pane — cycles through all panes in order, wrapping |
| `CTRL+SHIFT+Tab`    | Previous pane                                           |
| `ALT+1` … `ALT+4`   | Jump straight to that pane of the grid                  |
| `ALT+SHIFT+<arrow>` | Resize the focused pane, 3 cells per press              |

The most useful WezTerm defaults, kept as-is:

| Binding                    | Action                                                           |
| -------------------------- | ---------------------------------------------------------------- |
| `CTRL+SHIFT+Z`             | Zoom focused pane to fill the tab / restore the grid             |
| `CTRL+SHIFT+P`             | Pane selector — overlays a letter on each pane, press it to jump |
| `CTRL+SHIFT+"`             | Split pane horizontally                                          |
| `CTRL+SHIFT+%`             | Split pane vertically                                            |
| `CTRL+SHIFT+W`             | Close focused pane                                               |
| `CTRL+PageUp` / `PageDown` | Previous / next **tab**                                          |
| `CTRL+SHIFT+T`             | New tab                                                          |
| `CTRL+SHIFT+<arrow>`       | Move to the pane in that direction (directional, not cyclic)     |
| `CTRL+SHIFT+ALT+<arrow>`   | Resize focused pane, 1 cell per press                            |

Print the complete, live list — defaults plus overrides, as WezTerm actually resolved them:

```shell
wezterm show-keys
```

### Why `CTRL+Tab` is free to use for panes

WezTerm's defaults bind tab-switching to `CTRL+Tab`/`CTRL+SHIFT+Tab` **and** to
`CTRL+PageUp`/`CTRL+PageDown` — two bindings for the same action. Reassigning the `Tab` pair to pane
cycling costs nothing; `CTRL+PageUp`/`PageDown` still switch tabs.

### Cyclic vs. directional pane navigation

`ActivatePaneDirection` is documented on the
[default keys page](https://wezterm.org/config/default-keys.html) only with
`"Left"`/`"Right"`/`"Up"`/`"Down"`, which needs a modifier-plus-arrow chord and requires you to know
where the target pane _is_. The same action also accepts `"Next"` and `"Prev"` — documented on
[its own page](https://wezterm.org/config/lua/keyassignment/ActivatePaneDirection.html), not the
default-keys one — which cycle by pane index and wrap around. That's the `CTRL+Tab` behaviour, and
it's what the config binds.

## Resizing the WezTerm window

Nothing in `config/wezterm.lua` prevents it: `window_decorations` is left at its default
`"TITLE|RESIZE"`. But the startup hook calls `window:gui_window():maximize()`, and on GNOME/Wayland
a **maximized window cannot be edge-dragged** until it's unmaximized — `Super+Down`, `Alt+F5`, or
double-click the titlebar. See [keybindings.md](keybindings.md).

If dragging still doesn't stick after unmaximizing, the cause is a GNOME extension, not WezTerm. Two
enabled ones actively manage window geometry:

- **Tiling Shell** (`tilingshell@ferrarodomenico.com`) — snap zones; re-snaps a window dropped near
  an edge. See [keybindings.md](keybindings.md#tiling-shell-tilingshellferrarodomenicocom).
- **Smart Auto Move** (`smart-auto-move@khimaros.com`) — remembers per-window geometry and restores
  it, which can revert a manual resize. See [gnome_extensions.md](gnome_extensions.md).

To start un-maximized instead, drop the `maximize()` line from `config/wezterm.lua` and redeploy.

## Changing the config

`config/wezterm.lua` is deployed via the `config_files` mechanism, which means the install tasks
write it **only if it doesn't already exist** — editing the repo copy does not update the deployed
one. Push a change out with:

```shell
inv deploy.all --name wezterm
```

It shows a diff and asks before overwriting. Full details, including the
edit-locally-vs-edit-in-repo workflows, are in
[configuration.md](configuration.md#whole-file-configs-config_files).

## See also

- [Zsh](zsh.md) — the shell and prompt inside it
- [Fonts](fonts.md) — where the terminal's font is set
- [Shortcuts](shortcuts.md) — what PULSE changes outside the terminal
