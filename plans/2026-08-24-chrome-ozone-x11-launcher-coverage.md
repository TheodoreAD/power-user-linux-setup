---
status: in-progress
updated: 2026-08-24
---

# Making the Chrome `--ozone-platform=x11` workaround actually stick

## Context

**Symptom.** Netflix (and any protected/DRM video) plays audio with a black picture, except a brief
flash on play/pause. NVIDIA proprietary driver + Chrome on native Wayland. Hit on 2026-08-10, worked
around, and hit again on 2026-08-24 — the second time is what this plan is about.

**The workaround already exists and is correct.** `[packages.google-chrome-x11]` deploys a
user-level `~/.local/share/applications/google-chrome.desktop` whose `Exec` lines carry
`--ozone-platform=x11`, taking XDG priority over `/usr/share/applications/google-chrome.desktop`.
That file was verified present and correct on disk during the 2026-08-24 recurrence.

**Why it stopped working.** Ozone platform is chosen once, by the **first** Chrome process to start,
and every later window joins that existing instance rather than spawning a new one. At login,
`~/.config/autostart/` starts Chrome before the user ever touches a launcher — and none of the three
autostart entries carries the flag:

| autostart entry                                                            | `Exec`                                          |
| -------------------------------------------------------------------------- | ----------------------------------------------- |
| `google-chrome.desktop`                                                    | `/usr/bin/google-chrome-stable %U`              |
| `chrome-hnpfjngllnobngcgfapefoaidbinmjnm-Profile_2.desktop` (WhatsApp Web) | `/opt/google/chrome/google-chrome … --app-id=…` |
| `chrome-fmgjjmmmlfnkbppncabfkddbjimcfncm-Profile_2.desktop` (Gmail)        | `/opt/google/chrome/google-chrome … --app-id=…` |

So the fixed launcher wins only if nothing has already started Chrome, which at login is never true.
Confirmed by `ps`: every child of the running instance carried `--ozone-platform=wayland`, and the
root process was the autostarted WhatsApp Web PWA. Quitting Chrome entirely and relaunching from the
app grid fixed it immediately — verified by the user the same evening.

The `~/.config/autostart/google-chrome.desktop` copy is Chrome's own "continue where you left off"
entry, written by Chrome, not by PULSE. The two PWA entries are likewise Chrome-generated and are
rewritten whenever the PWA is (re)installed — any hand-edit to them is temporary by construction.

### Levers that do NOT exist (verified 2026-08-24 — do not re-derive)

[PITFALL: Google Chrome does **not** read an `OZONE_PLATFORM` environment variable. Two independent
checks: an A/B with throwaway `--user-data-dir` profiles (explicit `--ozone-platform=x11` → 9 child
processes on x11; `OZONE_PLATFORM=x11` with no flag → all children on `wayland`), and
`strings /opt/google/chrome/chrome | grep -x OZONE_PLATFORM` → no match at all. `OZONE_PLATFORM` is
an Electron convention. This kills the otherwise-attractive `~/.config/environment.d/` route for
_this_ problem — see `plans/2026-08-24-environment-d-session-env.md`, which is about the same
directory for unrelated reasons.]

[PITFALL: There is no `#ozone-platform-hint` in Google Chrome stable 151. The complete set of
`ozone*` switch names in the binary is `ozone`, `ozone-dump-file`, `ozone-override-screen-size`,
`ozone-platform`, `ozone-platform-state` — no `-hint`. A `chrome://flags` toggle persisted in
`Local State` (`browser.enabled_labs_experiments`, which does work — it currently holds
`vertical-tabs@1`) would have been launcher-independent and perfect. It is a Chromium/Electron flag,
not a Chrome one.]

[PITFALL: Per-window ozone platform is impossible. All windows of one profile share one browser
process, so "x11 only for the Netflix tab" has nowhere to live. A second instance would need its own
`--user-data-dir`, i.e. a separate logged-out profile.]

Also still true on 2026-08-24 with driver **595.84** on GNOME Wayland: the bug is live, not
something newer explicit-sync work has already fixed. No "just delete the workaround" exit.

## Status: option B is built and deployed, awaiting one login

[DECISION: **Option B**, chosen by the user on 2026-08-24 with the rest kept as the fallback ladder
("do option B, i'll check it and get back to you. if that doesn't work we'll try the rest"). It is
the only option that writes exclusively files PULSE owns, which is the ownership rule
`plans/2026-08-22-deployed-config-drift-guard.md` is converging on.]

Landed:

- `config/google-chrome-x11-autostart.desktop` and `[packages.google-chrome-x11-autostart]`
  (`wrapper-script`, `enabled = false` — machine-specific, like its sibling), deploying to
  `~/.config/autostart/00-google-chrome-x11.desktop`.
- Enabled on this machine via `~/.config/power-user-linux-setup/overrides.toml`, the mechanism from
  `plans/2026-08-24-machine-local-setup-toml-overrides.md`, which had to be built first — there was
  otherwise no way to deploy a package `setup.toml` ships disabled, and hand-copying it is what this
  repo forbids.
- Verified deployed, and both halves now show `ok` in `inv deploy.status`.

[UNVERIFIED: The whole premise — that gnome-session processes `~/.config/autostart/` in filename
order, so `00-…` wins the race against `chrome-*` and `google-chrome.desktop`. This is what the next
login tests, and it is the only thing standing between option B and the fallback ladder. If Chrome
comes up on Wayland anyway, ordering is not filename-based and B is dead as designed.]

[DEFERRED: **B2, a cosmetic refinement to try only if B works.** The entry currently launches Chrome
normally (`--ozone-platform=x11 %U`), so at login it does the session restore and Chrome's own
autostart entry may then open a second window. `--no-startup-window` exists in this Chrome build
(confirmed via `strings`) and would start the browser process without any window, purely to claim
the ozone platform. It was not used first because its failure mode is silent: with no windows and no
background apps, Chrome may simply exit, leaving the PWA entries to start a fresh Wayland instance
and making the test look like an ordering failure. Try it only once ordering itself is proven.]

## Open questions

[NEEDS CLARIFICATION: Which fallback if B's ordering assumption fails — C (`dpkg-divert`, the only
option Chrome cannot silently undo) or A (patch every `.desktop`, which loses to the file generator
over time). C is recommended below; the user's ladder says "we'll try the rest" without fixing an
order.]

### A. A task that patches every Chrome-launching `.desktop`

Scan `~/.local/share/applications/*.desktop` and `~/.config/autostart/*.desktop`, find `Exec` lines
invoking `google-chrome-stable` or `/opt/google/chrome/google-chrome`, inject the flag if absent.
The user's first suggestion.

- **For:** covers every launcher, whatever created it. Fits the repo's existing shape — a task that
  fixes a class of files. Pairs naturally with a read-only check in `deploy.status`/`verify.all` ("3
  Chrome launchers lack the flag").
- **Against:** must be re-run after any PWA install/update, forever, and nothing announces when that
  is needed. It edits Chrome-owned files, which is exactly the ownership model
  `plans/2026-08-22-deployed-config-drift-guard.md` is trying to make unambiguous — PULSE would be
  writing into files it did not create and does not control.

### B. One PULSE-owned autostart entry that starts Chrome first

Ship a single `~/.config/autostart/00-google-chrome-x11.desktop` with the flag, named to sort ahead
of `chrome-*` and `google-chrome*`. Whichever Chrome starts first sets the platform; the PWA
autostart entries then simply attach to the already-correct instance. The user's second suggestion.

- **For:** one file, PULSE-owned, never regenerated by Chrome. Nothing else is ever touched. If it
  works it is by far the smallest mechanism.
- **Against:** depends on autostart launch order being deterministic, which the XDG spec does not
  promise. [UNVERIFIED: whether gnome-session actually processes `~/.config/autostart/` in filename
  order. If it does not, `X-GNOME-Autostart-Delay` on our entry cannot help — the delay would have
  to go on _their_ entries, which reintroduces option A's regeneration problem. Testing this is a
  login cycle, not a command.]
- Robust variant if ordering turns out to be unreliable: a systemd user unit ordered inside
  `graphical-session.target` instead of a `.desktop` file, since units _can_ express ordering. Costs
  a mechanism this repo does not currently use for anything in `~`.

### C. `dpkg-divert` the Chrome wrapper

`/opt/google/chrome/google-chrome` is a plain bash wrapper that ends in
`exec -a "$0" "$HERE/chrome" "$@"`. Divert it and install a PULSE shim that appends the flag before
exec'ing the real binary.

- **For:** genuinely zero ongoing friction. Catches every launch path that will ever exist — desktop
  files, PWAs, `xdg-open`, a terminal invocation, a future launcher nobody has thought of — and
  survives Chrome package upgrades, because that is what diversions are for.
- **Against:** root-level machinery, and a diversion is invisible unless you go looking for it. A
  future session debugging Chrome flags would have no reason to suspect the binary is not the real
  one. Would need `deploy.status`/`verify.all` to surface it loudly.

### D. Stop autostarting Chrome

Turn off "run on OS login" for the two PWAs and Chrome's own session-restore autostart, so the first
Chrome of the day comes from the fixed app-grid launcher.

- **For:** no machinery at all. The bug's precondition just stops occurring.
- **Against:** a real behavior change the user did not ask for — WhatsApp and Gmail stop being there
  after login.

### E. Do nothing mechanical; document the recovery

Keep the launcher fix, and record "black Netflix → fully quit Chrome, relaunch from the app grid" in
`docs/`. It is a ~15-second fix on the rare occasions it bites.

- **For:** honest about how often this actually matters (twice in two weeks).
- **Against:** the recovery is only obvious once you know the first-process-wins mechanism; without
  it the symptom looks like a Netflix or driver problem.

Resolved: the `enabled = false` orphan problem (a disabled package is invisible to
`enabled_packages()` and so to `deploy.status`, while its file sits deployed in `~`) went away for
these two packages when `overrides.toml` turned them on here. The general case — a package deployed
and _later_ disabled — is still open, and is tracked in
`plans/2026-08-24-machine-local-setup-toml-overrides.md` rather than here.

## Recommended direction

**B first (done), C as the fallback, A only as a checker.**

B is the least friction _if_ autostart ordering holds, and the test is one login — cheap enough that
it should be settled before designing anything larger. It keeps PULSE writing only files PULSE owns,
which is the ownership rule the drift-guard plan is converging on.

If ordering proves unreliable, C is the honest answer to "least friction for the user," because it
is the only option that cannot be silently undone by Chrome regenerating a file. Its cost is
discoverability, and that is fixable with a loud entry in `deploy.status` — an invisible diversion
is bad, a registered and reported one is just a deployment.

A's scanning logic is worth building **as a read-only check regardless of which fix lands** — "does
any Chrome launcher on this machine lack the flag?" is the question that would have caught this on
2026-08-10 rather than on 2026-08-24. As a _writer_ it is the weakest option, because it fights a
file generator it cannot win against.

D and E are recorded for completeness; neither is proposed.
