---
status: landed
updated: 2026-08-30
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

## A second confirmed instance, and a better check than `test -x` (2026-08-30)

`[packages.telegram-desktop]` was added and hit this immediately — it is the `hang` shape rather
than Freelens' `detach-and-exit-0`, so `timeout 15s` did catch it, but only because someone thought
to look. Both `--version` and the `-version` tdesktop's own docs mention are ignored and start the
app (rc=124). Two things worth carrying back here:

[DECISION: **Probe a suspect package with the display stripped.**
`env -u DISPLAY -u WAYLAND_DISPLAY
timeout 15s <check>` answers "does this flag exit?" without
risking a window on the user's desktop — a Qt/Electron app that tries to open one dies on the
missing display instead. It does not fully replace step 1's human-in-the-loop audit, since a clean
exit under no display is only strong evidence and a _failure_ there is ambiguous (it may be the
missing display, not the flag). But it turns the audit's dangerous half into something an agent can
run, and it is how the telegram case was settled without opening anything.]

[DECISION: **Resolving the binary's shared libraries is a middle option between `test -x` and
launching.** `telegram-desktop`'s check is
`sh -c '! ldd ~/.local/share/telegram-desktop/Telegram | grep -q "not found"'`. That is materially
more than `test -x`: it proves every dynamic dependency on this machine resolves, which is the most
common way a downloaded static build is present-but-broken, and it is exactly the class of failure a
launch would have surfaced. It bears directly on the open question below — the answer for at least
some packages is not "narrow the contract", it is "there is a real check available that isn't a
launch".]

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
narrowing the contract's wording rather than pretending the check is equivalent. Partly answered
2026-08-30: the `ldd` check above is a real functional test that isn't a launch, so the choice is
not the binary one this question assumed. What is still open is whether `freelens` and the rest
should be moved onto it — that depends on how each is packaged, and an Electron `.deb`'s libraries
resolving says less than a downloaded static build's do.]

## Migrated to

Settled 2026-08-30 by auditing the class rather than reasoning about it. Everything durable is in
[`contributing/verify.md`](../contributing/verify.md), which was already this task's rationale home:

- **"Auditing the rest of the class, without launching anything"** — the Xvfb procedure that
  replaces this plan's step 1, the positive-control rule, the environment-dependence caveat, and the
  full result table. Also carries the two corrections the audit forced: `jetbrains-toolbox` was not
  the prime suspect (12ms, real CLI), and the `vaapi` error was `freelens`'s, not `google-chrome`'s.
- **"Why `freelens` keeps the existence check rather than a stronger one"** — the answer to this
  plan's open question. There is a middle option between `test -x` and launching, it is in use on
  `telegram-desktop`, and it is measurably wrong for `freelens`.
- The `--version`-falls-through-to-default-action class, the timeout's load-bearing role, and the
  detach-and-exit-0 shape were already written up there and stay where they are.

`tasks/verify.py`'s docstring names the class and points at that section, so the constraint is
visible from the code as well as from the docs.

**Deliberately not migrated:**

- **The regression guard** (`DEFERRED`). Killed, not deferred again: the audit produced the ratio it
  was waiting on — 7 of 8 GUI-tagged packages have a perfectly good `--version` — so a lint
  demanding `verify_cmd` on all of them is noise. The reasoning is recorded in that section so it is
  not re-proposed from scratch.
- **The "not safely invocable" marker mechanism** (step 3). The class is two packages, each already
  fixed with a per-package `verify_cmd`, exactly as `nyancat`/`px-proxy` were. A mechanism was
  conditional on the set being large; it is not.
- **The per-package "probably fine" table.** Superseded by measurements; keeping the guesses beside
  the results would only invite trusting the wrong column.
