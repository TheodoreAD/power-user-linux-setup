# Keyboard shortcuts PULSE changes

Which keys behave differently on a machine this repo set up, and which are left exactly as Ubuntu
shipped them. If a shortcut is not on this page, PULSE has not touched it — see
[keybindings.md](keybindings.md) for the full map of what GNOME and the installed extensions bind,
which is a much longer list and mostly not ours.

## Screenshots — opt-in, and only two keys

Nothing here happens during `inv setup`. Flameshot is installed, but the shortcuts are only rebound
when you ask for it:

```shell
inv screenshot.status     # what your session has right now, read-only
inv screenshot.enable     # take over the two keys below
inv screenshot.disable    # give them back to GNOME
```

<!-- PULSE::screenshot-shortcuts -->

| Shortcut           | Ubuntu default                              | After `inv screenshot.enable`                                                                                |
| ------------------ | ------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `Print`            | GNOME's own screenshot UI                   | Flameshot region select, with the annotation editor — saved and copied                                       |
| `Shift+Print`      | GNOME full-screen capture, saved and copied | Flameshot whole screen, no dialog — saved and copied                                                         |
| `Alt+Print`        | GNOME's own, unchanged                      | left alone — GNOME already saves it and copies it to the clipboard, and Flameshot has no window-capture mode |
| `Ctrl+Shift+Alt+R` | GNOME's own, unchanged                      | left alone — screen recording, which Flameshot cannot do at all — the built-in recorder stays the tool       |

<!-- /PULSE::screenshot-shortcuts -->

The table is generated from `tasks/screenshot.py`, so it says what the task actually does rather
than what someone once wrote down.

**Why only two.** There is more shadowing here than there looks: GNOME's built-in screenshot UI,
`gnome-screenshot`, and Flameshot all overlap, and none of them is a superset of the others.
Flameshot has no window-capture mode and no recording at all, so `Alt+Print` and the screencast
shortcut stay with GNOME — trading them for Flameshot would lose functionality, not add it. Nothing
about this stack is an obvious choice, which is why the two keys that do change are the two where
Flameshot's annotation editor is a clear win and nothing is lost.
[screen_capture.md](screen_capture.md) compares the tools properly.

**Recording is unchanged, deliberately.** `Ctrl+Shift+Alt+R` is still GNOME's own screen recorder.
Flameshot cannot record, and no replacement is installed.

## In the terminal

WezTerm's key bindings are PULSE's too — the startup split layout, `ALT+1..4` to jump between panes,
`CTRL+Tab` to cycle, `ALT+SHIFT+arrows` to resize. They are terminal-scoped, so they never collide
with the GNOME bindings above, and they are documented with the layout they belong to in
[terminal.md](terminal.md).

## Everything else

PULSE writes no other keyboard shortcuts. GNOME extensions installed by
[gnome_extensions.md](gnome_extensions.md) bring their own — Tiling Shell's `Super+Arrow`, the
Alt-Tab switcher's replacement of `Alt+Tab` — and those are the extension's defaults, not something
this repo configures. [keybindings.md](keybindings.md) has the live map, including which
`Super+<number>` bindings the extensions take over from the shell.

## See also

- [Keybindings](keybindings.md) — the full map of what GNOME and the extensions bind
- [Screen capture](screen_capture.md) — the tools behind the screenshot keys
- [Terminal](terminal.md) — WezTerm's own bindings
