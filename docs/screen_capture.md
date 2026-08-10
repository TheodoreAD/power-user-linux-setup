# Screen capture

## Built-in GNOME tool (Ubuntu 24.04 default)

Since GNOME 42 the screenshot/screencast UI is baked directly into GNOME Shell — no separate app
is needed. It works on both Wayland (default in 24.04) and X11.

GNOME 46 keeps these bindings in `org.gnome.shell.keybindings`, not the older
`org.gnome.settings-daemon.plugins.media-keys` schema some older guides reference — that schema's
`screenshot`/`screenshot-clip`/`window-screenshot`/etc. keys don't exist on this GNOME version.

### Keyboard shortcuts

| Shortcut | gsettings key | Action |
|---|---|---|
| `PrtSc` | `show-screenshot-ui` | Interactive mode — choose area, window, or full screen |
| `Shift+PrtSc` | `screenshot` | Full screen, instant |
| `Alt+PrtSc` | `screenshot-window` | Active window, instant |
| `Ctrl+Shift+Alt+R` | `show-screen-recording-ui` | Screencast (interactive) |

**Every one of the 3 screenshot actions already saves to disk *and* copies to the clipboard —
there's no separate "clipboard-only" shortcut to look for.** This is confirmed straight from
`gnome-shell` 46.0 source (`js/ui/screenshot.js`, cloned into
`$RESEARCH_HOME/repos/gitlab.gnome.org--GNOME--gnome-shell` for reference — a shared,
cross-project clone outside this repo, see `docs/research-library.md`): `screenshot`
and `screenshot-window` both
call a shared `_storeScreenshot()`, whose docstring is literally *"Stores a PNG-encoded
screenshot into the clipboard and a file"*; the interactive picker's capture button
(`_onCaptureButtonClicked`) goes through the same function. So this is already the "always save +
clipboard, no dialog" behavior — no configuration needed.

Screenshots are saved to `~/Pictures/Screenshots/Screenshot from <timestamp>.png`
(`GLib.UserDirectory.DIRECTORY_PICTURES` + a literal `Screenshots` subfolder, auto-created).

Screencasts: `Ctrl+Shift+Alt+R` opens an interactive recording UI; output is `.webm` in
`~/Videos/`.

### Limitations

No annotation tools. For marking up screenshots (arrows, text, blur, crop) you need a third-party
tool.

---

## Flameshot

Flameshot is the recommended tool when annotation is needed — it provides a built-in editor that
launches immediately after capture. Everything below comes from reading the Flameshot source
directly (`flameshot-org/flameshot`, cloned into
`$RESEARCH_HOME/repos/github.com--flameshot-org--flameshot`), not its docs.

**Install:** via `[packages.flameshot]` in `setup.toml` (`inv apt.deb`) — **not** `apt install
flameshot`. Two real bugs were found and fixed getting this working on this machine
(2026-08-08), both worth knowing about if screen capture ever breaks again:

1. **Missing portal backend.** Flameshot captures via the standard
   `org.freedesktop.portal.Screenshot` D-Bus interface. `xdg-desktop-portal-gnome` — the backend
   that actually implements it for GNOME — wasn't installed on this machine (only the generic
   `xdg-desktop-portal-gtk` was). Without it, the request has no backend to answer it and hangs
   forever with *no error at all* (confirmed with `busctl --user monitor`). Now declared as its
   own `[packages.xdg-desktop-portal-gnome]` apt package — required for *any* portal-based
   screenshot/screencast tool, not just Flameshot.
2. **Flameshot v12.1.0 (Ubuntu's apt package) itself hangs on capture.** Even after fixing (1),
   `flameshot full`/`gui` still hung indefinitely. `gdb` + `busctl monitor` together showed GNOME
   *does* send back a correct, successful `Response` with the capture — Flameshot's own Qt6/D-Bus
   signal handling in v12.1.0 just never processes it. This matches a long history of similar
   hang/freeze reports across Flameshot versions and distros with no single clean fix. Upgrading
   to **v14.0.0** (installed from GitHub releases, since Ubuntu noble-updates only ships 12.1.0)
   resolved it completely — capture-and-save now completes instantly and reliably. `setup.toml`
   pins the exact release rather than tracking latest, since the release's zip-asset filename
   embeds a git-describe string, not the version — bump `tag`/`asset` by hand to try a newer
   release.

### Design: same keys, same directory, same "always save + clipboard" behavior

Flameshot only takes over the 2 shortcuts it can actually replace. `Alt+PrtSc` (active window) is
left on GNOME's own `screenshot-window` action — it already saves + copies to clipboard by
default (see above), and Flameshot has no window-capture mode to offer instead
(`flameshot --help` only has `full`/`gui`/`screen`/`config`/`launcher` — no "grab the focused
window" primitive anywhere in the source). The screencast shortcut is untouched too — Flameshot
has no recording/video code path at all, confirmed by grepping the whole source tree.

Flameshot's `-p/--path` and `-c/--clipboard` flags are independent and combine in one invocation
(verified in `src/main.cpp`'s `gui`/`full` handlers): passing both always does *both* — saves to
the given directory and copies to the clipboard, no save dialog, matching the built-in tool's
behavior exactly.

| Shortcut | Command |
|---|---|
| `PrtSc` | `flameshot gui -p ~/Pictures/Screenshots -c` — interactive area/window/full + annotate → save & clipboard |
| `Shift+PrtSc` | `flameshot full -p ~/Pictures/Screenshots -c` — all monitors, instant → save & clipboard |
| `Alt+PrtSc` | *(untouched — GNOME's `screenshot-window`, already save + clipboard)* |
| `Ctrl+Shift+Alt+R` | *(untouched — GNOME screencast; Flameshot has no video capability)* |

**Wayland note:** older Flameshot builds (Qt5, e.g. the apt-shipped v12.1.0) default to XWayland
and can't communicate with the Wayland screenshot portal ("Unable to capture screen"); the fix is
`QT_QPA_PLATFORM=wayland` in both the `.desktop` file and keybinding commands. v14.0.0 (Qt6) works
correctly with no override needed — tested both with and without it. `inv screenshot.enable` still
applies the override when the session is Wayland, since it's a harmless no-op on a version that
doesn't need it and protects against a future downgrade.

### Managing it

```shell
inv screenshot.enable    # sets Flameshot's savePath, applies the Wayland fix if needed,
                          # disables GNOME's show-screenshot-ui/screenshot keys, binds PrtSc/Shift+PrtSc
inv screenshot.disable   # removes the 2 custom bindings, restores GNOME's shipped defaults exactly
                          # (gsettings reset, not hardcoded values)
inv screenshot.status    # diagnostic: shows GNOME key state, custom binding state, savePath
```

These are GNOME-session tasks (`gsettings`/`dconf`), like `inv gnome.*` — not wired into `inv
setup`; run them yourself from a logged-in terminal. `inv screenshot.disable` is the reinstatement
path if Flameshot is ever removed: it doesn't guess at default values, it resets the actual keys,
so whatever GNOME 46 (or a future version) ships as default comes back exactly.

**Status:** installed (v14.0.0) and enabled in `setup.toml`. Confirmed working live end-to-end
2026-08-08: `PrtSc`/`Shift+PrtSc` capture-and-save, clipboard copy (pasted a live capture directly
into another app), and `Alt+PrtSc` (GNOME's untouched native window capture) all work as designed.
The earlier scripted `flameshot full -c` + immediate `wl-paste --list-types` check that showed no
`image/png` was a false alarm from the non-interactive repro, not a real clipboard problem. The
annotation editor (arrows/text/blur/crop) also confirmed working on a `PrtSc` capture.

---

## Other options

- **Shutter** — heavier GUI editor, pixel-level tools; overkill for most use cases
- **Kazam** — screenshots + screen recording in one app; no annotation
- **`gnome-screenshot` CLI** — the older screenshot tool, still installed on this machine
  alongside the newer Shell UI. Scriptable (`-w`/`-a`/`-c`/`-f` for window/area/clipboard/file, and
  `-c` + `-f` together do both), and it still works fine under Wayland since it captures via the
  same `org.gnome.Shell.Screenshot` D-Bus service the Shell UI itself uses — but the built-in
  `Alt+PrtSc` already covers everything it'd be used for here.
