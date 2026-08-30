# `inv verify.all` — design notes

Companion to
[`docs/dev-container.md`'s "Automated functional verification"
section](../docs/dev-container.md#automated-functional-verification-inv-verifyall) (the published
"what it is / why it exists" explanation). This is the durable record of the gotchas the first
implementation pass hit and how testing — actually running the checks against a real machine and two
real container builds, not code review — caught each one. Read this before re-deriving
`tasks/verify.py`'s design from scratch or "simplifying" something that was already a deliberate
tradeoff.

### The core tension: convention vs. safety

The brief was "convention-based, not hand-written per package" — default to
`<check_cmd or
table-key> --version` and only override where that's wrong. In practice, auditing
that convention against every real package this repo installs surfaced two very different failure
shapes, and they need different fixes:

- **Wrong flag/binary name** — cheap to fix with a per-package `verify_cmd` override. Doesn't change
  the mechanism.
- **The command doesn't exit at all** — not something any override field alone can guard against,
  because the bug is "this specific invocation hangs," not "the guessed command was wrong." This is
  why `_TIMEOUT_SECS` (a hard `timeout 15s` wrapper around every invocation, applied uniformly, not
  opt-in) exists as a second, independent layer under the override mechanism.

### `nyancat --version` hung the machine running the audit

Not a hypothetical: auditing `inv verify.all` against this repo's own bare-metal dev machine
actually froze it. `nyancat` ignores unrecognized flags entirely and falls through to its default
behavior — the terminal animation — instead of erroring. `--version` isn't a flag it recognizes, so
it just ran forever. Confirmed by testing a _second_ time deliberately, after the timeout fix was in
place: overriding `nyancat`'s `verify_cmd` to a different unrecognized flag reproduced the exact
same hang class, but this time `timeout 15s` bounded it to a clean `exit 124` instead of hanging
anything. `px-proxy --version` turned out to have the identical bug shape — it started the proxy
daemon itself instead of printing a version and exiting. Both needed `--help` instead (which _is_ a
flag they recognize), and both stayed protected by the same timeout regardless.

**Lesson**: never assume an unrecognized-flag invocation is safe just because it "should" print an
error and exit. Some tools fall through to their default action instead. The timeout isn't optional
scaffolding around this task — it's load-bearing.

### `freelens --version` opened the GUI, and passed

Third instance of the same class, found 2026-08-28 by the user noticing two Freelens windows appear
after `inv verify.all` was run twice in one session. `/usr/bin/freelens` is a packaged Electron
binary; `--version` isn't something it answers, so it falls through to its default action and shows
the app.

**What makes this one different, and worse: the timeout does not catch it.** nyancat and px-proxy
hung, so `timeout 15s` bounded them to a visible `exit 124` failure. Freelens detaches and the
invoked process exits **0** — so verify reports `ok`, the run completes clean, and the only evidence
is a window on screen that nothing in the output mentions. A green `inv verify.all` is not proof
that nothing was launched.

Fixed with `verify_cmd = "test -x /usr/bin/freelens"` — an existence check, the same answer
`_path_only` already gives for methods where invoking the artifact would be unsafe. That reasoning
was previously scoped to `git-clone`/`apparmor-profile` by method; this is the first case where an
_invocable_ method needed it, decided per package rather than by widening the method rule.

**`test` is a real binary** (`/usr/bin/test`), which is why it works here. Checks run as
`timeout 15s <cmd>`, so `timeout` execs the command directly — a shell builtin like `command -v`
would not survive that wrapper.

**Re-running `inv verify.all` is not free**, which is how this was found: it invokes every installed
package, so a second run to re-read or filter the first run's output launches every GUI app again.
Redirect or grep the output you already have.

### Auditing the rest of the class, without launching anything

The open worry after `freelens` was that the whole GUI-tagged set might be doing this invisibly, and
that confirming it meant launching each one and watching the screen. It does not: run the check
against a **throwaway X display** instead of the user's session. A program that falls through to its
default action opens its window there and hangs or lingers; a program with a real CLI prints its
version and exits in milliseconds. Nothing reaches the real desktop either way.

```shell
Xvfb :99 -screen 0 1280x800x24 -nolisten tcp &
env -u WAYLAND_DISPLAY DISPLAY=:99 timeout 20s <the check>   # rc, elapsed, and output are the verdict
xlsclients -display :99                                      # did anything map a window?
```

Both `Xvfb` and `xlsclients` are already on this machine (`xvfb`, `x11-utils`). Stripping `DISPLAY`
and `WAYLAND_DISPLAY` entirely is the cheaper variant and was the first thing tried, but its
failures are ambiguous — a Qt app dying on a missing display looks the same whether or not it
recognized the flag. The virtual display removes that ambiguity, which is what makes this an audit
rather than a hint.

**Run `freelens` in the same batch as a positive control.** It is the known-bad case, so a batch
where it comes back clean is measuring nothing — that is how this procedure was validated rather
than assumed.

One caveat the control itself exposed: **the failure shape is environment-dependent.** On the real
session `freelens` detached and exited 0 (which is why the timeout missed it); on the virtual
display it hung and was killed at 20s. Same defect, opposite symptom. So read a probe as "this check
is unsafe" or "this check is fine", never as a prediction of how it will fail in front of the user —
and do not conclude a check is safe because it merely exited 0, without also checking it was fast
and mapped no window.

Audited 2026-08-30, every GUI-tagged package resolving to the default `--version`:

| Package                | Result                      |
| ---------------------- | --------------------------- |
| `jetbrains-toolbox`    | `Toolbox 3.5.0.84344`, 12ms |
| `wezterm`              | version, 15ms               |
| `flameshot`            | version, 51ms               |
| `google-chrome`        | version, 62ms               |
| `font-manager`         | version, 141ms              |
| `terminator`           | version, 186ms              |
| `gnome-extensions-cli` | version, 273ms              |
| `freelens` (control)   | **hung**, killed at 20s     |

So the class was one package wide all along, and it was already fixed. Three corrections fall out of
that, each of which had been written down as an expectation:

- **`jetbrains-toolbox` was named the prime suspect on the reasoning that it is also an Electron
  app. It is the fastest check in the table.** "Same kind of program" turned out to predict nothing;
  what matters is whether the packager wired up a CLI, which is a per-package fact.
- **The `vaapi` error blamed on `google-chrome --version` was not Chrome's.**
  `google-chrome-stable
  --version` exits in 62ms with empty stderr, on both a virtual and the real
  display. `freelens` emits `vaInitialize failed` verbatim, and both run inside the same
  `inv verify.all` — the line was attributed to the wrong package by proximity in a shared log.
- **A regression guard requiring `verify_cmd` on every GUI-tagged package would be noise on 7 of 8
  entries.** Deliberately not built. The replacement is this procedure being written down: check a
  new GUI package once, when it is added, and record the answer in its section.

### Why `freelens` keeps the existence check rather than a stronger one

`telegram-desktop` (2026-08-30) is a second package whose only interface is a GUI — both `--version`
and the `-version` its upstream documents start the app — so it needed the same treatment. It got a
better check than `test -x`: resolving every shared library the binary needs.

```toml
verify_cmd = "sh -c '! ldd ~/.local/share/telegram-desktop/Telegram | grep -q \"not found\"'"
```

That is a real functional test — a downloaded static build that is present but unrunnable fails it,
which is the failure existence checking cannot see — and it launches nothing.

**It is not portable to `freelens`, and measuring that is the point.** `ldd /usr/bin/freelens`
reports `libffmpeg.so => not found` on an installation that works perfectly well: Electron ships
that library inside its own resources directory and resolves it at runtime, so the top-level
binary's link table is genuinely incomplete. Moving `freelens` onto the `ldd` check would fail
`inv setup` on a healthy machine.

The rule, then, is per packaging rather than per symptom: a self-contained downloaded build can be
checked by resolving its libraries; an app that loads bundled libraries at runtime cannot, and
existence is what is honestly available. That is a real narrowing of what `verify.all` promises for
GUI applications, and it is better stated than papered over.

### `git-clone`/`wrapper-script` were originally going to force a hard error, not a safe default

The first design had these methods (plus `apparmor-profile`, `gnome-extension`) in a "no verify
strategy — you must add `verify_cmd` or `verify = false`" bucket, on the theory that they don't
produce an invocable command by nature so there's no sensible default to guess. Auditing the actual
`wrapper-script` entries in `setup.toml` changed that: `[packages.askpass-zenity]`'s `dest` is a
script meant to be invoked _by_ `SUDO_ASKPASS`, popping a GUI password dialog — running it directly
as a "verification" would have actually popped that dialog during `inv setup`.
`[packages.pulse-proxy-start]`'s `dest` starts a background proxy daemon. Neither is safe to invoke
standalone just to check it "works."

The fix: `git-clone`/`wrapper-script`/`apparmor-profile` all default to an **existence check** on
the same path (`dest`/`dest`/`profile`) the install-time "already installed" check already uses —
never an invocation. This is strictly weaker evidence than actually running something, but it's the
only _safe_ default for methods whose installed artifact isn't meant to be run standalone.

**`wrapper-script` was later strengthened from existence to content comparison** (2026-08-23):
existence alone doesn't catch a deploy that landed stale or hand-edited content, only that
_something_ is at `dest`. Confirmed as a real gap, not theoretical, the same session it was fixed —
manually diffing `~/AGENTS.md` against `config/global-AGENTS.md` twice to confirm a redeploy
actually took (once after a fresh write, once again after `dprint` reflowed the source) is exactly
the kind of check an agent shouldn't need to do by hand. Every `wrapper-script` entry in
`setup.toml` declares `content_file` (no inline-`content` variant is actually in use), so
`_resolve_wrapper_script` (`tasks/verify.py`) compares `dest`'s actual bytes against `content_file`
run through the same `.strip() + "\n"` transform `_install_wrapper_script` applies before writing —
still safe, since reading a file's content and diffing it is not the same risk class as invoking it.
Falls back to the old existence-only check if a future entry ever omits `content_file`, rather than
erroring.

**Then replaced by the shared deploy classifier, and widened** (2026-08-25): the byte comparison
above was a second copy of the transform `tasks/tools.py` applied on write, kept in sync by hand.
Once `tasks/deploy.py` became the one writer for every path under `~` (`contributing/deploy.md`),
verify's `"deploy"` check became a read-only call into `deploy.classify()` — the same answer
`inv deploy.status` gives, including the stale-vs-edited distinction the old comparison couldn't
express. That also extended coverage to the two mechanisms the old check never saw: any method's
`config_files` mappings and every `skills` entry, both pulled from the deploy registry. The one
policy wrinkle: a `config_files` destination is _seeded_, not owned — the user's after first install
— so a customized copy is reported and passes; only its absence fails. Without that split,
`inv setup` would fail on every config the user has ever touched (this machine's terminator config,
rewritten by terminator itself, was the live example). `wrapper-script` paths still come from
`_resolve`, not the registry sweep, so `verify_cmd` / `verify = false` keep applying to them.

### `gnome-extension` needed a different fix entirely: always skip

Originally these defaulted to a read-only `gnome-extensions list | grep -qF <uuid>` check — safe (no
side effects), and it worked when tested by hand on a machine with extensions actually installed.
The bug wasn't unsafety, it was a false assumption: `gnome/gui` tags being present on an entry
doesn't mean `inv setup` (or anything else automated) ever actually installs it.
`inv gnome.install-extensions` is never called from `tasks/setup.py` or `tasks/wsl.py` — confirmed
by grepping for the call, not assumed — because this repo's own standing rule is to never touch a
live GNOME session programmatically (see `tasks/gnome.py`). On a normal desktop install (no
`gnome`/`gui` tag exclusion, the common case this repo is built for), every `gnome-extension` entry
is fully tag-eligible for `packages_by_method()` but was never actually installed by the run being
verified — checking it by default would fail `inv setup` for something it never promised to do.

Wiring `inv verify.all` into `packages_phase` (the step this bug would have made fatal, not just
noisy) is what surfaced it — it wasn't visible when the task only ran standalone on a machine that
happened to already have extensions installed by hand. **Lesson**: a check that's individually
correct can still be wrong to run _by default_ if the thing it's checking was never promised by the
surrounding pipeline. `gnome-extension` now always resolves to `skip`; the grep-based check is still
available, just only via an explicit per-package `verify_cmd`.

### Container-only PATH gaps: `go` and `node`

Both install fine — `go`'s `archive` extraction and `node`'s `nvm` install both succeed — but
neither binary lands on `PATH` for the process actually running `inv verify.all` inside a
Dockerfile's `RUN` layer. Both are only exposed via a `zshenv`/Oh-My-Zsh-plugin snippet, meant to be
sourced by an _interactive_ shell. That works fine on bare metal (any later terminal sources it) and
is invisible there — this repo's own dev machine has had that snippet sourced for ages, so a
bare-metal-only audit pass would never have caught it. It only surfaced once tested inside an actual
`docker build`, where the single non-interactive `RUN inv setup && inv verify.all` layer never
sources anything.

Fix: explicit `verify_cmd` pointing at the real, absolute install path
(`~/.local/share/go/bin/go
version`) or explicitly sourcing the nvm shim
(`bash -c 'source ~/.local/share/nvm/nvm.sh && node
--version'`) — not relying on the ambient `PATH`
at all. **Lesson**: "works when I test it interactively" and "works inside a Dockerfile `RUN`" are
genuinely different environments for anything whose exposure depends on shell startup files, and
only one of the two container base images tested (plain `ubuntu:24.04`) would have caught this — the
`devcontainers/base` image ships its own more thorough shell setup that happened not to expose the
same gap the same way.

### Table-key vs. real binary/flag, overlapping with `cli-allowlist/`'s own findings

Several entries' `[packages.<name>]` table key isn't the command it installs, or the tool doesn't
support `--version` at all — `[packages.edge]` installs `microsoft-edge`, `[packages.vscode]`
installs `code`, `[packages.ripgrep]` installs `rg`; `kubectl` needs `version --client`, `helm`
needs `version` (no `--short` required, unlike the allowlist's own finding), `go` needs `version`,
`k9s` needs `version`, `tmux`/`ssh` need `-V`, `unzip` needs `-v`. Several of these are the _exact
same tools_ `contributing/cli-allowlist.md`'s `version_flag` registry already documents having the
same quirk — found independently, for a different purpose, and landing on the same answer. Worth
checking that file first the next time a tool's default `--version` guess turns out wrong here;
there's a real chance it's already been diagnosed once.

### One genuinely stale machine, not a false positive

`[packages.pulse-proxy-start]` failed its existence check on this repo's own dev machine — not a bug
in the check, but a real gap: the entry was added to `setup.toml` after this machine's last full
`inv setup` run, so it had simply never been installed here. Running `inv tools.install` once fixed
it. Included here as a reminder of what `inv verify.all` is actually _for_: this is exactly the
class of drift it exists to catch, and a machine failing the check because it's genuinely behind is
a working feature, not something to explain away by loosening the check.
