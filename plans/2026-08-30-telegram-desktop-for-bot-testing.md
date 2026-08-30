---
status: idea
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

## Open questions

[NEEDS CLARIFICATION: Which install method. Telegram Desktop ships as an official static tarball, a
Flatpak on Flathub, a Snap, and a distro package that lags. The repo's own rule is to look for a
maintained PyPI wrapper first, which does not exist for a Qt desktop application, so this falls to
the next mechanism — and which one that is depends on what `setup.toml` already uses for GUI
applications generally rather than on anything specific to this program.]

[NEEDS CLARIFICATION: Whether a GUI application used only for testing another project belongs in the
machine's setup at all, or whether that is scope creep into a per-project tool. The argument for
including it is the repo's own rule that a one-off manual install is how the machine silently
diverges from its own declaration; the argument against is that the next machine has no reason to
want a Telegram client. Leaning toward including it, since the rule is written without an exception
for "only needed occasionally".]

[UNVERIFIED: That a **fresh** account can be registered on the test server from Desktop using a
reserved test number. The number format `99966X YYYY` (X being the data-centre id) and the login
code of that id repeated five or six times are documented for the test DCs by both
[Pyrogram](https://docs.pyrogram.org/topics/test-servers) and
[Telethon](https://docs.telethon.dev/en/stable/developing/test-servers.html), and Desktop's Test
Server option targets those same DCs — but that is inference from two documented facts rather than
something anyone has done here. It is the first thing to try, and the whole route depends on it.]

## Recommended direction

Add Telegram Desktop as a `[packages.*]` entry in `setup.toml` with whatever method the file already
uses for GUI applications, then verify the test-server route end to end in one sitting: register a
test account, create a bot with the test environment's BotFather, and confirm the token answers on
`https://api.telegram.org/bot<token>/test/getMe` — the `/test/` segment being what distinguishes the
environment.

Record the outcome, particularly if the reserved-number signup does not work from Desktop, because
the fallback is materially worse: it means a production account and a second BotFather bot on the
real network, which is exactly the exposure the test environment exists to avoid.
