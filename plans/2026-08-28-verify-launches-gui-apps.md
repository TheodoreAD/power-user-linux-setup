---
status: idea
updated: 2026-08-28
---

# `inv verify.all` can launch GUI applications and still report ok

## Context

Found 2026-08-28, not by a failing run: the user noticed two Freelens windows had appeared, and
`inv verify.all` had been run twice in the same session. `freelens` is `deb-github`, so it resolves
to the convention default `freelens --version`; `/usr/bin/freelens` is a packaged Electron binary
that doesn't answer `--version` and falls through to showing the app.

This is the third instance of the fall-through-to-default-action class already written up in
[`contributing/verify.md`](../contributing/verify.md) (`nyancat --version` ran its animation
forever, `px-proxy --version` started the proxy daemon), but it is the first one the existing
mitigation does not catch.

[PITFALL: **The 15s timeout is useless against the detach-and-exit-0 shape.** nyancat and px-proxy
hung, so `timeout 15s` turned them into a visible `exit 124`. Freelens detaches and the invoked
process exits **0**, so the check passes, the run completes clean, and nothing in the output
mentions that a window opened. "A green `inv verify.all`" is therefore not evidence that nothing was
launched — which is exactly why this survived the original audit pass that found the other two.]

`freelens` itself is fixed (`verify_cmd = "test -x /usr/bin/freelens"`, an existence check). What is
not fixed is the class.

## The unaudited set

Eight enabled packages carry a GUI-ish tag (`gui`/`desktop`/`ide`/`corporate`) on an invocable
method and still resolve to the default `<check_cmd> --version`:

| Package                | Method       | Assessment                                               |
| ---------------------- | ------------ | -------------------------------------------------------- |
| `jetbrains-toolbox`    | `archive`    | **Prime suspect** — also an Electron app                 |
| `google-chrome`        | `deb-url`    | Exits, but its `--version` initializes vaapi (see below) |
| `flameshot`            | `deb-github` | Has a real CLI; probably fine                            |
| `terminator`           | `apt`        | Has a real CLI; probably fine                            |
| `wezterm`              | `deb-github` | Has a real CLI; probably fine                            |
| `font-manager`         | `apt`        | Unassessed                                               |
| `gnome-extensions-cli` | `uv-tool`    | CLI by definition; fine                                  |

[UNVERIFIED: every "probably fine" above is inference from what kind of program it is, not a
measurement. The whole point of this plan is that the failure is invisible in the output, so the
only honest way to clear a package is to watch the screen while its check runs.]

`google-chrome --version` does exit, but it emitted
`ERROR:media/gpu/vaapi/vaapi_wrapper.cc:1631] vaInitialize failed` during a verify run — a version
check should not be initializing hardware video acceleration. Worth a look even though it isn't
opening a window.

## Recommended direction

Rough; the sequencing matters more than the mechanism.

1. **Audit before mechanising.** Run each of the eight checks individually, watching the screen, and
   record the result per package. This is a human-in-the-loop step by nature — an agent cannot
   observe a window appearing, the same limitation `session-bash-audit`'s **Probe** procedure works
   around by printing expected outcomes and asking. Copy that shape rather than inventing one.
2. **Then decide whether this needs a mechanism at all.** If the audit turns up only
   `jetbrains-toolbox`, two per-package `verify_cmd` overrides are the whole fix and nothing else
   should change — consistent with how `nyancat`/`px-proxy` were handled. A mechanism is only
   warranted if the set is large or keeps growing as GUI packages are added.
3. **If a mechanism is wanted**, the shape to consider is a declared "not safely invocable" marker
   that routes to the existence check `_path_only` already implements, rather than widening
   `_path_only`'s method rule — the problem is per-package (Electron vs. a real CLI), not
   per-method. A GUI tag is the wrong trigger: `flameshot` and `wezterm` are GUI apps with perfectly
   good `--version` support.

[DEFERRED: **A regression guard.** Nothing stops the next GUI package from being added with the
default check and nobody noticing, since the symptom is a window rather than a failure. A test can't
observe a window either, so the candidate is a lint-shaped check — "an invocable-method package
tagged `gui` must declare `verify_cmd` or `verify = false`" — which would be noise for `flameshot`
and `wezterm`. Decide after step 1, when the real ratio is known.]

## Open questions

[NEEDS CLARIFICATION: is the existence check enough for these, or does it hollow out what
`verify.all` promises? Its contract is "every package a run installed also actually _works_", and
`test -x` only proves a file is there and executable. For an app whose only interface is a GUI there
may be nothing better available without launching it — in which case the honest move might be
narrowing the contract's wording rather than pretending the check is equivalent.]
