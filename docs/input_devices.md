# Input devices

## Kinesis Advantage 360

### Current layout (Profile 6 / `layout6.txt`)

This is the layout currently deployed to the keyboard. `[rwin]>[lwin]` under `<base>` fixes GNOME's
tap-to-open-overview gesture not firing on a tap of the right Super key — see "Tap-to-open
Activities" below for why. Confirmed working: the right Super key now works correctly everywhere
(both as a tap and as a modifier) with no OS-level (GNOME/X11/Wayland) remapping needed.

!!! WARNING
    `hk3` and `hk4` send `Super+Alt+KP0` and `Super+Shift+KP0` respectively — these were likely
    gTile window tiling shortcuts. gTile has been replaced by Tiling Shell / Tiling Assistant;
    verify these bindings are still useful or remap them before applying this layout.

```text
<base>
[rwin]>[lwin]
[hk1]>[prnt]
{hk2}>{-lshf}{prnt}{+lshf}
{hk3}>{x1}{keyt}{-rwin}{-lalt}{kp0}{+rwin}{+lalt}
{hk4}>{x1}{keyt}{-rwin}{-lshf}{kp0}{+rwin}{+lshf}

<keypad>

<function1>
[left]>[vol-]
[rght]>[vol+]
{up}>{-rwin}{pgup}{+rwin}
{down}>{-rwin}{pgdn}{+rwin}
{lshf}{up}>{-rwin}{-lshf}{pgup}{+rwin}{+lshf}
{lshf}{down}>{-rwin}{-lshf}{pgdn}{+rwin}{+lshf}

<function2>

<function3>
```

Annotated (documentation only — strip the `#` lines before pasting to the device):

```text
<base>
# right Windows/Super key sends left Windows/Super, so GNOME's Super_L-only
# tap-to-open-overview gesture fires no matter which physical Super key is tapped;
# single source of truth for this remap — confirmed <function1> falls through to
# this line, so it doesn't need repeating there (see "Tap-to-open Activities" below)
[rwin]>[lwin]
# Hotkey1 -> Print Screen
[hk1]>[prnt]
# Hotkey2 -> Shift+Print Screen
{hk2}>{-lshf}{prnt}{+lshf}
# Hotkey3 -> fire once, toggle keypad layer, then Super+Alt+Numpad0
# (likely a legacy gTile tiling shortcut — see WARNING above)
{hk3}>{x1}{keyt}{-rwin}{-lalt}{kp0}{+rwin}{+lalt}
# Hotkey4 -> fire once, toggle keypad layer, then Super+Shift+Numpad0
# (likely a legacy gTile tiling shortcut — see WARNING above)
{hk4}>{x1}{keyt}{-rwin}{-lshf}{kp0}{+rwin}{+lshf}

<keypad>

<function1>
# fn1 Left arrow -> Volume down
[left]>[vol-]
# fn1 Right arrow -> Volume up
[rght]>[vol+]
# fn1 Up   -> Super+PageUp (switch to workspace above, in GNOME's default bindings)
{up}>{-rwin}{pgup}{+rwin}
# fn1 Down -> Super+PageDown (switch to workspace below)
{down}>{-rwin}{pgdn}{+rwin}
# fn1 Shift+Up   -> Super+Shift+PageUp (move current window to workspace above)
{lshf}{up}>{-rwin}{-lshf}{pgup}{+rwin}{+lshf}
# fn1 Shift+Down -> Super+Shift+PageDown (move current window to workspace below)
{lshf}{down}>{-rwin}{-lshf}{pgdn}{+rwin}{+lshf}

<function2>

<function3>
```

### Applying a layout

- access the Direct Programming mode using the `SmartSet`+`V-Drive` keys
- place the custom configuration above in `layouts/layout6.txt` and save the file
- eject the drive and press the `SmartSet`+`V-Drive` keys
- if that fails and the keyboard isn't responsive, disconnect the keyboard cable and reconnect it

### Tap-to-open Activities does nothing (Super key swallowed)

GNOME's tap-to-open-overview gesture (`gsettings get org.gnome.mutter overlay-key`) is hardcoded
to the `Super_L` keysym only — it does not also listen for `Super_R`. If the Kinesis's thumb-cluster
key(s) that act as "Windows/Super" are mapped to the right-hand keysym, tapping them does nothing
in GNOME even though the same physical key works fine as a modifier (e.g. in `Super+Tab`, which
GNOME binds to both `Super_L` and `Super_R`).

Fix: remap `rwin` to `lwin` under `<base>` only (see the layout above). A layout file stores only
the *diffs* from the factory defaults (§4.0 of the guide), and a key left unmapped on
`<function1>`/`<function2>`/`<function3>` falls through to whatever `<base>` says for that key —
so one line under `<base>` covers every layer, with nothing to keep in sync elsewhere.

**Confirmed working**: a single `<base>` line is enough — unmapped keys on the Fn layers do fall
through to `<base>`, so the right Super key now works correctly everywhere (tap-to-open-overview
and modifier use) with no duplicate line needed on Fn1, and no OS-level (GNOME/X11/Wayland)
remapping required on top of it.

Verify with `gsettings get org.gnome.mutter overlay-key` (should stay `'Super_L'`) and a bare tap
of the key. See [keybindings.md](keybindings.md) for the full set of Super-based bindings this
affects.

### SmartSet direct-programming syntax reference

Reference PDFs (large, not checked in — see `reference/kinesis/`, which is gitignored;
re-download from https://kinesis-ergo.com/support/kb360/ if missing):

- `adv360-smartset-direct-programming-guide-v12-2-22.pdf` — syntax rules, section 4
- `adv360-smartset-action-tokens-v3-31-23.pdf` — full list of position/action tokens

Each of the 9 profiles is a plain-text `layout<N>.txt` file on the keyboard's onboard "v-Drive".
A file is split into layer sections; write a line under the layer it should apply to:

```text
<base>
<keypad>
<function1>
<function2>
<function3>
```

**Remaps** — one physical key always sends one action. Square brackets, exactly one action token,
no control over press/release timing:

```text
[position]>[action]
```

Example: `[esc]>[caps]` makes the Escape key send Caps Lock.

**Macros** — a trigger (optionally combined with a co-trigger modifier held first) plays back a
sequence of actions. Curly braces on both sides:

```text
{trigger}>{action1}{action2}...
```

Action-sequence tokens:

- `{-tok}` / `{+tok}` — press-and-hold / release `tok` (needed for modifiers, since a plain
  `{tok}` is a full tap). Shifted characters therefore require a macro, not a remap:
  `{tab}>{-lshf}{h}{+lshf}{i}` makes the Tab key type "Hi".
- `{s1}`-`{s9}` prefix (right after the `>`) — sets this macro's own playback speed.
- `{x1}`-`{x9}` prefix — Multiplay: fire the macro exactly that many times instead of the default
  "repeat continuously while the trigger is held".
- `{d001}`-`{d999}` / `{dran}` — a fixed (ms) or random delay, e.g. between clicks of a
  double-click macro.
- Tap-and-Hold uses remap syntax with two extra tokens:
  `[key]>[tap-action][t&hNNN][hold-action]` — different behavior for a tap vs. holding past
  `NNN` ms (Kinesis recommends 250ms; not recommended for alphanumeric keys).

**No comment syntax exists**, inline or line-level. The only documented "inert line" mechanism is
a leading `*`, which *disables* an otherwise-valid code line — it doesn't let you attach free text,
and the guide warns that bad syntax "could cause temporary problems with even basic keyboard
operation." So actual layout files are kept comment-free; explanations live in this doc instead,
as annotated copies placed next to the pasteable block above.

### References

- https://kinesis-ergo.com/support/kb360/
- https://kinesis-ergo.com/wp-content/uploads/Advantage360-SmartSet-KB360-Users-Manual-v10-12-22.pdf
- https://kinesis-ergo.com/wp-content/uploads/Adv360-SmartSet-Direct-Programming-Guide-v12-2-22.pdf
- https://kinesis-ergo.com/wp-content/uploads/Adv360-SmartSet-Direct-Programming-Action-Tokens-v3-31-23.pdf
