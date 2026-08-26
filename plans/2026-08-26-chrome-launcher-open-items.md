---
status: idea
updated: 2026-08-26
---

# Chrome launcher items left open when the ozone plan retired

## Context

`plans/2026-08-24-chrome-ozone-x11-launcher-coverage.md` landed on 2026-08-26 — Chrome comes up on
X11, Netflix plays, and the duplicate-PWA symptom went with it. Its design rationale and every
measured dead end moved to [`contributing/chrome-ozone.md`](../contributing/chrome-ozone.md), and
its user-facing half is [`docs/chrome.md`](../docs/chrome.md). Three things it carried were still
open and had nowhere else to go, so they live here rather than being lost in the retirement.

None is urgent. The arrangement works today; these are the ways it can stop working, plus one
refinement the user parked.

## Open questions

[NEEDS CLARIFICATION: **Which fallback if the PWA autostart entries ever come back.** The working
arrangement depends on `~/.config/autostart/` holding exactly one Chrome launcher. Re-enabling "run
on OS login" for Gmail or WhatsApp Web reintroduces the race, and the race cannot be won by ordering
— that was measured, see `contributing/chrome-ozone.md`. Two candidates remain: **C**, `dpkg-divert`
on `/opt/google/chrome/google-chrome` with a PULSE shim that appends the flag (the only approach
Chrome cannot silently undo; costs an invisible diversion that a future session debugging Chrome
flags would have no reason to suspect, so it would need `deploy.status`/`verify.all` to surface it
loudly), and **A**, patching every Chrome-launching `.desktop` in place (covers every launcher
whatever created it, but must be re-run after any PWA install/update forever, and writes files PULSE
does not own — the ownership rule `contributing/deploy.md` makes unambiguous). The retired plan
recommended C; the user's ladder said "we'll try the rest" without fixing an order. Nothing needs
deciding until the trigger actually fires.]

[NEEDS CLARIFICATION: **Should `config/google-chrome-x11.desktop` pin a profile?** Its `Exec` lines
carry no `--profile-directory`, so a launcher click — or a link handed to Chrome by another app —
lands on whatever profile Chrome restores from `last_active_profiles`. Adding
`--profile-directory="Profile 2"`, plus per-profile `[Desktop Action …]` entries for the others,
would make it deterministic, and unlike the Chrome-generated PWA files this one is PULSE-owned, so
the change survives. Offered 2026-08-25 and deferred by the user ("not yet"). The real question is
whether hardcoding a personal profile directory into a repo config file is acceptable: the package
is already `enabled = false` and machine-specific, turned on here through `overrides.toml`, so it is
consistent with its sibling — but a second machine's "Profile 2" is a different account. If the
answer is no, the alternative is deriving it from Chrome's own `Local State` at deploy time, which
`tasks/chrome.py` already knows how to read.]

[NEEDS CLARIFICATION: **Does a rebuilt machine ever learn to run `inv chrome.status`?** Two of the
three pieces that make the arrangement work are manual — the `google-chrome.desktop.disabled` rename
and the per-PWA "run on OS login" toggles — so a fresh clone plus `inv setup` silently gets the race
back. The reporting side is done: `chrome.status` lists every enabled Chrome-launching autostart
entry and whether it carries the flag, which is the honest ceiling given the PWA toggles live in
Chrome's own preferences. What is missing is a prompt to run it. `next_steps.print_next_steps` is
the wrong home — it is a strict one-item-at-a-time chain for the identity/git/ssh bootstrap and
returns after the first outstanding step. `inv verify.all` is also wrong: it aborts on first failure
and checks that packages work, not that machine state is arranged a particular way. So the honest
options are a line in the post-`inv setup` summary, or accepting that `docs/chrome.md` saying it is
enough.]

## Recommended direction

Leave all three parked. The first is trigger-driven and needs nothing until the trigger fires; the
second is the user's call on a personal-detail-in-repo tradeoff; the third is a one-line change once
someone decides where the line goes, and is only worth spending on if a machine actually gets
rebuilt.
