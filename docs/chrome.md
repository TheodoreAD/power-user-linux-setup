# Chrome PWA launchers

Google Chrome writes a `.desktop` launcher for every PWA you install, one per (app, Chrome profile)
pair, into `~/.local/share/applications/chrome-<app-id>-<Profile>.desktop`. With more than one
profile signed in, those generated files make the app grid worse rather than better:

- **Every copy has the same `Name`.** Gmail installed in three profiles gives three tiles all called
  "Gmail", indistinguishable in the grid and in the taskbar.
- **Some copies carry `NoDisplay=true`**, which hides them from the grid completely — so the apps
  belonging to the profile you actually use can be impossible to find or pin, while another
  profile's copies are the ones on offer.
- **None carry `--ozone-platform=x11`**, which `[packages.google-chrome-x11]` needs on every Chrome
  launch path to take effect.

```shell
inv chrome.status          # read-only: every launcher, its profile, and what has drifted
inv chrome.fix-launchers   # label by profile, unhide the primary profile's, add the ozone flag
```

`inv chrome.fix-launchers` takes `--yes` to skip the confirmation and `--profile "Profile 2"` to
treat a profile other than Chrome's `last_used` as the primary one. `PULSE_DRY_RUN=1` prints the
plan without writing.

## What it derives, and what it never touches

Nothing here is configured in `setup.toml`. Profile display names ("Main", "Work") come from
Chrome's own `Local State`, and the profile whose apps get unhidden defaults to the one Chrome
records as `last_used`. Whether the ozone flag is wanted comes from whether
`[packages.google-chrome-x11]` is enabled.

Two deliberate limits:

- **Filenames are never changed.** GNOME's `favorite-apps` pins launchers by filename, so renaming
  one would silently drop it from your dash.
- **`[Desktop Action …]` names are never relabelled.** Those are the right-click shortcut labels
  ("Search", "Shorts", "Subscriptions" on YouTube), not app names. Their `Exec` lines _do_ get the
  ozone flag, since each action is its own launch path.

Component extensions Chrome installs for itself (Chrome Web Store Payments) are hidden on purpose
and are left exactly as found.

## This is a repair, not a fix

Chrome owns these files and rewrites them whenever a PWA is installed or updated, discarding the
labels. `inv chrome.fix-launchers` is therefore re-runnable by design and is wired into no phase, no
`inv setup` step, and no hook — run it when `inv chrome.status` says it's needed.

That is also why this lives in its own namespace rather than under `deploy.*`. `inv deploy.all` only
ever writes paths PULSE created and can prove it wrote; these are another program's generated files,
and blurring that boundary would break the ownership model the deploy tasks depend on.

## Known limitation: profiles are indistinguishable under X11

Every copy of an app carries the same `StartupWMClass=crx_<app-id>` — Chrome puts no profile in the
X11 WM_CLASS. Under X11 the shell therefore cannot tell one profile's window from another's for the
same app, so an app installed in two or more profiles cannot be reliably pinned or grouped. Under
Wayland, windows are matched per `.desktop` file and the ambiguity does not arise.

This matters because `[packages.google-chrome-x11]` exists to force Chrome onto XWayland (an
NVIDIA + Wayland DRM-video bug). Taking that workaround costs per-profile pinning; an app installed
in exactly one profile is unaffected either way.
