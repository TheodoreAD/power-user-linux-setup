---
status: in-progress
updated: 2026-08-30
repo: git@github.com:TheodoreAD/power-user-linux-setup.git
---

# Telegram Desktop, for exercising a bot against the test environment

## Context

A personal project is building a Telegram bot as its first surface, and the question that came up on
2026-08-30 was whether it can be exercised on this machine at all without picking up a phone. The
client landed; the "without a phone" half did not survive contact, and the two sections below the
install record why.

Telegram runs a **dedicated test environment** — separate data centres, separate accounts, a
separate BotFather — documented at
[core.telegram.org/bots/features](https://core.telegram.org/bots/features#dedicated-test-environment).
Accounts there use reserved test numbers rather than real ones, and nothing reachable from one can
touch a real chat. Desktop is the only client on this machine that can reach it.

That page also names Desktop as a way in and gives this gesture, which is where the rest of this
plan starts:

> **Telegram Desktop**: open ☰ Settings > Shift + Alt + Right click 'Add Account' and select 'Test
> Server'.

Both halves of that turned out to be wrong for a fresh install — the gesture has nothing to land on,
and Desktop cannot create the account it implies. Neither is documented anywhere upstream.

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

[PITFALL: Telegram Desktop answers no version flag. It does parse switches — see the list under
"Remaining" — but neither `--version` nor the `-version` that third-party docs mention is among
them, and an unrecognized argument is ignored rather than rejected, so the app just starts. Measured
2026-08-30 with `DISPLAY` and `WAYLAND_DISPLAY` stripped so nothing could surface a window:
`verify.all`'s 15s timeout fires (rc=124). It therefore carries a `verify_cmd` that resolves the
binary's shared libraries instead — same evidence a launch would give, without the launch. Being the
second instance of the `freelens` class is what prompted auditing the rest of it; that audit came
back clean and is written up in `contributing/verify.md`, along with why the same check would be
wrong for `freelens` itself.]

## The premise was wrong, and it was the package's justification

Settled the same day by a session that read the client's source (clone at `087b18b`, 2026-08-28, in
`$RESEARCH_HOME/repos/github.com--telegramdesktop--tdesktop`) and then tried it. The `[UNVERIFIED:]`
above — that a fresh account could be registered from Desktop with a reserved number — is answered,
and the answer is no.

[PITFALL: **Telegram Desktop cannot register a test-environment account. It can only log in to one
that already exists.** Five login attempts with correctly-formed reserved numbers, across two data
centres, every one returning `PHONE_CODE_INVALID` while the numbers themselves were accepted.
Telegram's bot documentation lists Desktop among the ways in and never mentions the limit; the
mini-apps documentation says a new test-environment account may only be created from a **mobile**
client, and `telegramdesktop/tdesktop#27824` is a queue of people hitting this and being told to
register on iOS or the Android beta and link Desktop afterwards.]

**Reaching the test environment is still true; "without a phone" is not** — not by this route alone.
That sentence was the argument for the entry existing, and it shipped in the
`[packages.telegram-desktop]` description on 2026-08-30 before this was known. Description corrected
the same day. The entry stays worth having on the narrower claim: once an account exists, Desktop is
where a human taps a real inline keyboard, which is the point of the exercise and what no library
substitutes for.

## The gesture in that description did nothing, either

[PITFALL: The Shift + Alt + right-click handler hangs off the **"Add Account" row of the accounts
list** — `AccountsList::setupAdd()` in `settings/sections/settings_information.cpp`, which checks
`IsAltShift(button->clickModifiers())` before offering "Production Server" / "Test Server". That
list only exists once a session does. **On a client that has never logged in there is no accounts
list, so the gesture has nothing to land on** — which cost twenty minutes of trying key combinations
against a fresh install. Ruled out on this machine rather than assumed: GNOME's
`mouse-button-modifier` is `<Super>` and input-switching is `<Super>space`, so nothing was
intercepting the combination.]

[PITFALL: The obvious-looking target is the wrong one. Settings' top-bar ⋮ menu has its own "Add
account" action (`settings/sections/settings_main.cpp`) which hard-codes `MTP::Environment{}` —
production — with no right-click path at all. And a `_DEBUG` build opens the environment menu on a
plain right-click with no modifiers, so every walkthrough written by someone running a debug build
describes a gesture the official binary does not have.]

**The route that works from a logged-out client is a secret code.** The login screen carries a
SETTINGS button (`intro/intro_widget.cpp`); with no session that opens `Settings::LayerWidget`,
whose `keyPressEvent` (`settings/settings_intro.cpp`) feeds every keystroke to `CodesFeedString`.
Typing `testmode` hits the handler in `settings/settings_codes.cpp`, which switches environment and
toasts "Switched to the test environment."

[PITFALL: Pressing "Add Account" first breaks that route permanently for the install. It creates a
second account slot, and the `testmode` handler guards on `accounts().size() == 1`, so the code
silently does nothing from then on. Switch the environment first, register second.]

## Remaining

[DECISION: The environment cannot be declared from outside the client. Which environment an account
belongs to lives in the encrypted `tdata` profile, and switching it is a UI action. Read from the
parser in `Telegram/SourceFiles/core/launcher.cpp`, the only trustworthy source: the accepted
switches are `-debug`, `-testagent`, `-key`, `-autostart`, `-fixprevious`, `-cleanup`, `-noupdate`,
`-tosettings`, `-startintray`, `-quit`, `-workdir`, `--`, `-scale`.]

[PITFALL: `-testmode` and `-many` appear all over third-party switch lists and neither is parsed by
the current client. An automation built on them silently starts an ordinary production instance —
the argument is not rejected, it is ignored. The Debian manpage and the project wiki each document a
subset and allude to "hidden options" without naming them.]

**What can be declared is the profile.** `-workdir <path>` gives an entirely independent profile in
a named directory, so a dedicated test profile logged into the test data centres once stays that way
and the login becomes once-per-profile rather than once-per-run. That is the remaining work here: a
fixed working directory under the user's data directory, a wrapper launching Desktop with `-workdir`
pointed at it, and a launcher entry named so it cannot be confused with the real client.

[UNVERIFIED: That two instances with different `-workdir` values run at the same time. The old
`-many` switch existed for exactly this and is gone from the parser, which suggests the
single-instance lock now lives inside the working directory — but that is inference from a removed
flag, not something anyone has run. It decides whether the test profile can sit beside a normal one
or has to replace it for the session.]

[NEEDS CLARIFICATION: Whether the test profile gets its own `.desktop` entry or a wrapper script on
`PATH`. A launcher entry is what makes it discoverable six months later, which is the whole point; a
script is what an agent or a task can invoke. Not exclusive — the entry can exec the script.]

[NEEDS CLARIFICATION: Whether this machine's setup should carry anything for the account-creation
step at all, or whether that belongs entirely to the project that needs it. An MTProto library
signing up on a test data centre unattended is the only genuinely no-phone path, and it is a Python
dependency of a project rather than a machine package — but the `api_id`/`api_hash` it needs are
per-person credentials from `my.telegram.org`, which is machine-adjacent in the same way an SSH key
is.]
