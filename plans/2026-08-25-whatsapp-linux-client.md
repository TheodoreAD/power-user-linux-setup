---
status: abandoned
updated: 2026-08-25
---

# Declaring a WhatsApp client in PULSE

Evaluated whether the hand-made Chrome PWA for `web.whatsapp.com` should be replaced by a real Linux
WhatsApp client declared in `setup.toml`. **Conclusion: no. Keep the PWA.** Recorded so the question
isn't re-litigated from scratch in six months.

## Why the PWA wins

Every desktop "client" on Linux is a wrapper around `web.whatsapp.com` — ZapZap (PyQt6/QtWebEngine),
Karere (GTK4 shell over CEF/Chromium 150), WhatsApp for Linux (WebKitGTK), Ferdium/Rambox
(Electron). None speaks a different protocol. So a wrapper can only win on the shell around the
page, and it necessarily loses on the page itself:

- **The PWA is real Chrome** — the newest engine on the machine, always current, full proprietary
  codecs, and it picks up WhatsApp Web features on the day they ship. Every wrapper is an older
  embedded Chromium or a WebKitGTK build that isn't Chromium at all.
- **Voice and video calling landed on WhatsApp Web on 2026-07-28** (with call transfer between
  phone/desktop/browser, and call-link waiting rooms). This was the one capability that used to
  justify looking past the browser, and the PWA gets it natively.
- The wrappers demonstrably lag on exactly this. ZapZap's open issues as of 2026-08-25 include the
  call button opening in the default browser instead of placing the call in-app (2026-08-19), plus
  video status, sent videos, and screenshare — the codec/WebRTC class of bug, because Ubuntu and
  Debian build QtWebEngine without proprietary codecs. Karere's entire v4.0 rewrite (WebKitGTK → CEF
  with H.264/AAC) existed to escape that same class.

What a wrapper actually offered over the PWA: a tray process independent of the browser session,
per-account isolated profiles, badge counts, custom CSS/JS injection. Real, but nowhere near worth a
worse rendering engine — let alone a new install mechanism to deliver it.

Also rejected along the way, each for its own reason:

- **ZapZap's `.deb`** — 356 KB, bundles nothing, `Depends: python3-pyqt6.qtwebengine`. On noble that
  resolves to `libqt6webenginecore6` **6.4.2**, a Chromium ~108 engine from late 2022. Adopting it
  would have moved the engine backwards from the PWA by four years.
- **Waydroid** — clears the technical bar on this machine (Wayland session, `binder_linux.ko` in the
  stock 6.8.0-137 kernel), but needs a GAPPS image, mic/camera passthrough work, and a manual Google
  device-ID registration that cannot be scripted — a non-reproducible step inside a repo whose whole
  premise is re-runnable installs. Its sole advantage was calls, which evaporated on 2026-07-28.
- **Matrix bridge** (`mautrix-whatsapp`, or Beeper) — a service to operate, not a package to
  declare, with an unofficial-client ban surface.

## Migrated to

- **`plans/2026-08-25-undeclared-snap-packages.md`** — the one live item this evaluation turned up,
  unrelated to WhatsApp: `duf-utility` and `mdless` are installed on this machine and declared
  nowhere in `setup.toml`. Note that the version of this item written here first claimed they need a
  new `snap` install method; that was checked afterwards and is wrong (duf ships a `.deb`, mdless's
  snap is a third-party repack of a Ruby gem), so the successor plan carries the corrected premise,
  not this one's.

Deliberately **not** migrated:

- The client survey and the reasoning above have no destination in `docs/` or `contributing/` —
  they're a machine-app choice, not a repo convention, and `contributing/` is organized around
  questions a contributor arrives with. This file's own git history is the record; that's why the
  conclusion was written down and committed before being deleted rather than simply dropped.
- The `snap`-vs-`flatpak` comparison and the `snap` method design notes. With zero packages that
  actually need such a method (see above), keeping them would be preserving a design for a mechanism
  nobody asked for. Recoverable from history if a genuinely snap-only tool ever appears.
- The dated engine facts (QtWebEngine 6.4.2 on noble, ZapZap's open issue list, Karere's v4.0
  rewrite). All are true as of 2026-08-25 and will rot; the durable conclusion — the PWA is real
  Chrome and therefore beats every embedded-engine wrapper — is what matters and is stated above.
