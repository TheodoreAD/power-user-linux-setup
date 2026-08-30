---
status: in-progress
updated: 2026-08-30
repo: git@github.com:TheodoreAD/power-user-linux-setup.git
---

# Telegram Desktop, for testing a bot without a phone

## Context

A personal project is building a Telegram bot as its first surface, and the question that came up on
2026-08-30 was whether it can be exercised on this machine at all without picking up a phone. It
can, and the route needs one GUI application this machine does not have.

Telegram runs a **dedicated test environment** — separate data centres, separate accounts, a
separate BotFather — documented at
[core.telegram.org/bots/features](https://core.telegram.org/bots/features#dedicated-test-environment).
An account there is registered with a reserved test number rather than a real one, so no SIM, no
phone and no production account is involved, and nothing reachable from it can touch a real chat.
Desktop is the only client on this machine that can reach it:

> **Telegram Desktop**: open ☰ Settings > Shift + Alt + Right click 'Add Account' and select 'Test
> Server'.

[DECISION: Desktop rather than a web client or an MTProto library. `web.telegram.org` offers no test
server switch, and driving the test DC from Telethon or Pyrogram tests the library rather than the
surface — the point of the exercise is a human tapping a real inline keyboard and finding out which
parts are awkward at 3am, which needs a real client.]

## What landed (2026-08-30)

`[packages.telegram-desktop]`, `method = "archive"`, `enabled = false`, enabled on this machine
through `~/.config/power-user-linux-setup/overrides.toml`. Installed to
`~/.local/share/telegram-desktop/` with `Telegram` symlinked into `~/.local/bin/telegram-desktop`,
per the XDG rule for multi-file installs.

[DECISION: The official static tarball, not apt, a PPA, a Flatpak or a Snap. Both open questions
about the method turned out to be settled by one measurement rather than by preference: **Ubuntu
24.04 ships no `telegram-desktop` in any component** — `apt-cache search --names-only telegram` on
this machine returns `telegram-cli` and `telegram-send` and nothing else, with universe and
multiverse both enabled. That removes the "distro package that lags" option entirely, and the repo
has no Flatpak or Snap method (and declined to grow one in
`plans/2026-08-25-undeclared-snap-packages.md`, on the grounds that it would serve zero packages
that actually need it). `archive` against upstream's own `telegram.org/dl/desktop/linux` endpoint is
what is left, and it is also the best of them: upstream, always current, no third-party repackager.]

[DECISION: Declared but shipped off, enabled per-machine. This is the shape the second open question
was reaching for — the repo's rule against one-off manual installs and the objection that the next
machine has no reason to want a Telegram client are both satisfiable at once, because
`overrides.toml` exists (`plans/2026-08-24-machine-local-setup-toml-overrides.md`). Nothing had to
be exempted from the rule.]

[PITFALL: The `archive` method was gzip-only — `tar -zx` hardcoded at all four call sites — and
Telegram ships `.tar.xz`, so this package could not have been installed by it as written. The fix
had to be download-then-extract rather than a wider set of tar flags: GNU tar auto-detects
compression only when it can **seek**, so `curl | tar -x` fails with "Archive is compressed. Use -J
option" no matter what, and sniffing the URL suffix is no good either because upstream's "latest"
endpoint carries no extension and only reveals the format through its redirect. Now fetched to a
temp file and read with `tar -xf`, which handles gzip, xz and bzip2 alike; three parametrised tests
over real tarballs guard it, and they were confirmed to fail against the old flag.]

[PITFALL: Telegram Desktop has no CLI whatsoever. Measured 2026-08-30 with `DISPLAY` and
`WAYLAND_DISPLAY` stripped so nothing could surface a window: both `--version` and the `-version`
that tdesktop's own docs mention are ignored, the app starts, and `verify.all`'s 15s timeout fires
(rc=124). It therefore carries a `verify_cmd` that resolves the binary's shared libraries instead —
same evidence a launch would give, without the launch. Being the second instance of the `freelens`
class is what prompted auditing the rest of it; that audit came back clean and is written up in
`contributing/verify.md`, along with why the same check would be wrong for `freelens` itself.]

## Remaining

[UNVERIFIED: That a **fresh** account can be registered on the test server from Desktop using a
reserved test number. The number format `99966X YYYY` (X being the data-centre id) and the login
code of that id repeated five or six times are documented for the test DCs by both
[Pyrogram](https://docs.pyrogram.org/topics/test-servers) and
[Telethon](https://docs.telethon.dev/en/stable/developing/test-servers.html), and Desktop's Test
Server option targets those same DCs — but that is inference from two documented facts rather than
something anyone has done here. The whole route depends on it, and the client is now installed, so
it is one sitting away: ☰ Settings > Shift + Alt + Right click 'Add Account' > Test Server,
register, create a bot with the test environment's BotFather, and confirm the token answers on
`https://api.telegram.org/bot<token>/test/getMe` — the `/test/` segment being what distinguishes the
environment.

Record the outcome, particularly if the reserved-number signup does not work from Desktop, because
the fallback is materially worse: it means a production account and a second BotFather bot on the
real network, which is exactly the exposure the test environment exists to avoid.]
