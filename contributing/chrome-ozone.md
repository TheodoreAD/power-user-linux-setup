# Forcing Chrome onto X11: the levers that don't exist

`[packages.google-chrome-x11]` exists because Google Chrome on native Wayland with the NVIDIA
proprietary driver plays protected video (Netflix and anything else DRM-backed) as sound over a
black picture, with a brief flash on play/pause. Still reproducible on driver 595.84 under GNOME
Wayland on 2026-08-26, so there is no "just drop the workaround" exit yet.

[`docs/chrome.md`](../docs/chrome.md) is the user-facing page: what `inv chrome.status` reports and
how the arrangement is supposed to look. This page is the part that stops the next session
re-deriving a dead end — every approach below was tried and measured, and each cost real time.

## The mechanism, stated once

The ozone platform is chosen **once, by the first Chrome process of the session**. Every window
opened afterwards joins that process and its own `--ozone-platform` is silently discarded. So a
correct launcher only helps if nothing unflagged can start Chrome before it — which at login is a
question about `~/.config/autostart/`, not about launchers at all.

This is why the bug recurs looking like a Netflix or driver problem: the fix is present on disk and
verified correct, and still does nothing.

## Levers that do not exist (verified 2026-08-24 — do not re-derive)

**Chrome does not read an `OZONE_PLATFORM` environment variable.** Two independent checks: an A/B
with throwaway `--user-data-dir` profiles (explicit `--ozone-platform=x11` → 9 child processes on
x11; `OZONE_PLATFORM=x11` with no flag → all children on `wayland`), and
`strings /opt/google/chrome/chrome | grep -x OZONE_PLATFORM` → no match at all. `OZONE_PLATFORM` is
an Electron convention, not a Chrome one. This kills the otherwise-attractive
`~/.config/environment.d/` route for this particular problem — see
`plans/2026-08-24-environment-d-session-env.md`, which wants that directory for unrelated reasons.

**There is no `#ozone-platform-hint` in Google Chrome stable 151.** The complete set of `ozone*`
switch names in the binary is `ozone`, `ozone-dump-file`, `ozone-override-screen-size`,
`ozone-platform`, `ozone-platform-state` — no `-hint`. A `chrome://flags` toggle persisted in
`Local State` (`browser.enabled_labs_experiments`, which does work — it currently holds
`vertical-tabs@1`) would have been launcher-independent and perfect. It is a Chromium/Electron flag.

**Per-window ozone platform is impossible.** All windows of one profile share one browser process,
so "x11 only for the Netflix tab" has nowhere to live. A second instance would need its own
`--user-data-dir`, i.e. a separate logged-out profile.

**Autostart filename ordering does not decide the race.** A `00-`-prefixed entry, chosen to sort
ahead of `chrome-*` and `google-chrome*`, was measured **losing**. On the 2026-08-25 login,
`gnome-session-binary` started all four Chrome-launching entries inside a 3ms window
(21:52:25.414–.417) and the fork order was not filename order — PIDs are the tell:
`google-chrome.desktop` got 1480257 and the WhatsApp PWA 1480272, while `00-google-chrome-x11`, the
entry that sorts first, got 1480305 and duly logged `Opening in existing browser session.` The PWA
won the singleton handshake and defined Wayland for the whole session. `X-GNOME-Autostart-Delay`
cannot rescue this either: the delay would have to go on _their_ entries, which Chrome regenerates.

**Vulkan is not the cause.** Chrome logs
`'--ozone-platform=wayland' is not compatible with Vulkan. Consider switching to '--ozone-platform=x11' or disabling Vulkan`
on every Wayland session, and has since at least 2026-08-13 — VS Code, which shares the ozone stack,
logs it too. It reads like the smoking gun and is not. Disabling Vulkan via
`chrome://flags/#enable-vulkan` was tested on 2026-08-25: the flag applied (`Local State` recorded
`enable-vulkan@2`, and the GPU process ran `--disable-features=EyeDropper,Vulkan` where it had
previously carried only `EyeDropper`), Chrome stayed on Wayland so the test was not confounded, and
Netflix was still black with sound. The same GPU process that carried the disable flag logged the
incompatibility one second later. The flag was set back to Default.

## What actually works, and what it cost

Being the **only** thing that starts Chrome. On this machine that is
`[packages.google-chrome-x11-autostart]`'s entry plus "run on OS login" switched off for every PWA,
and Chrome's own `~/.config/autostart/google-chrome.desktop` renamed to `.disabled`.

Verified 2026-08-26: the 01:02:24 login came up on x11 and Netflix plays. `--ozone-platform=x11` on
26 Chrome processes and `wayland` on none; the browser root process was
`/opt/google/chrome/chrome --ozone-platform=x11` with no `--app-id`, i.e. the autostart entry's
plain launch rather than a PWA; the journal shows exactly one Chrome starter and no
`Opening in existing browser session` line.

Two options were considered and are still the fallback ladder if the PWA autostart entries ever come
back — `dpkg-divert` on `/opt/google/chrome/google-chrome` (the only approach Chrome cannot silently
undo, at the cost of an invisible diversion), and patching every Chrome-launching `.desktop` in
place (loses to Chrome's file generator over time, and writes files PULSE does not own, which
[`contributing/deploy.md`](deploy.md) forbids). Neither is built; the open choice between them is
tracked in `plans/`.

### That `google-chrome.desktop` was not a Chrome-managed file

It was dated feb 2020, mode 644, 8411 bytes — a verbatim copy of the system desktop file including
the full i18n `GenericName` block, carrying no `X-GNOME-Autostart-*` keys. A six-year-old leftover,
almost certainly added once through Startup Applications and forgotten. The autostart directory only
reads `*.desktop`, so renaming it to `.disabled` is inert and trivially reversible. An earlier
analysis assumed Chrome regenerated it and was wrong; that assumption is what made the problem look
unfixable without machinery.

### One cause wearing two hats

After a power loss or a logout with windows still open, the Gmail and WhatsApp PWAs came back
**doubled**. Same root cause, same fix. `Profile 2` has `session.restore_on_startup = 1`, so the
autostart `google-chrome.desktop` restored the PWA windows that were open at logout while the two
`chrome-*` entries opened the same two PWAs again. Closing the windows before logging out left
restore nothing to reopen, which is why the doubling only appeared after an unclean exit.

### The flag is deliberately absent from PWA launchers

Every copy of a PWA launcher carries the same `StartupWMClass=crx_<app-id>` — Chrome puts no profile
in the X11 WM_CLASS. Under X11 the shell therefore cannot tell a Work Gmail window from a Main Gmail
window, so an app installed in two or more profiles cannot be reliably pinned or grouped; under
Wayland, windows match per `.desktop` file and the ambiguity does not arise.

Adding `--ozone-platform=x11` to the PWA launchers would buy only the case where a PWA tile starts
the session's first Chrome process — which, with the autostart arrangement above, does not happen at
login — and would cost exactly the per-profile pinning that relabelling those launchers had just
restored. So it is off by default and `inv chrome.fix-launchers --ozone` is the explicit opt-in.
WhatsApp Web is immune to the collision either way because its app-id exists in exactly one profile,
which is why it was the only PWA that could be pinned before the relabelling — not evidence that the
rest would work under x11.

## Why this is reported and never repaired

Two of the three pieces that make the arrangement work are manual and PULSE cannot re-apply them:
the `.disabled` rename and the per-PWA "run on OS login" toggles, which live in Chrome's own
preferences. A fresh clone plus `inv setup` reproduces the autostart entry and none of the state
that makes it the _sole_ starter, so a rebuilt machine silently gets the race back.

`cleanup_paths` is not the mechanism for this — it only fires from `apt.uninstall`, on the section
being uninstalled. What is missing is an "ensure this foreign file stays absent" declaration, and
reporting is the honest ceiling: `inv chrome.status` lists every enabled autostart entry that can
start Chrome and whether each carries the flag, honouring both `Hidden=true` and
`X-GNOME-Autostart-enabled=false` as well as the XDG rule that a `~/.config/autostart` file masks a
`/etc/xdg/autostart` one of the same name. A `NO FLAG` line means another entry can claim Wayland
first, and Netflix goes back to playing sound over a black picture.
