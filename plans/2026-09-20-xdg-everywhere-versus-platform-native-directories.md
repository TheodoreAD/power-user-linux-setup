---
status: idea
updated: 2026-09-20
---

# `~/.local` on every platform, or platform-native defaults — and the answer is not one answer

## Context

Asked 2026-09-20:

> do we have a plan to explore using the linux-style .local convention across all platforms, like uv
> and some other software? I'm afraid we are complicating our software with the platform-specific
> stuff.

**No plan owned it**, and the nearest one assumed the opposite without arguing for it:
[`2026-09-07-agents-md-and-skills-on-native-windows.md`](2026-09-07-agents-md-and-skills-on-native-windows.md)
says `util.PULSE_CONFIG_DIR`/`PULSE_STATE_DIR` should copy the skills' destination table, which
branches to `%APPDATA%`/`%LOCALAPPDATA%` — "copy that, do not invent a second answer". That is
advice about _consistency_, not about which convention is right, and the question underneath it had
never been asked.

**Nothing in this repo branches today.** `util.py` hardcodes `~/.config/power-user-linux-setup` and
`~/.local/state/power-user-linux-setup`, and PULSE is Linux-only, so the complication the question
is about does not exist here yet. It arrives with the Windows port. That makes this the cheap moment
to decide it — before there is a second answer to keep in sync.

## Evidence

Surveyed 2026-09-20 across ~28 tools, from local clones in `$RESEARCH_HOME/repos/` with `file:line`
citations. Two page fetches, both closed-vendor docs with no public repo (Microsoft's
`Environment.SpecialFolder` and `KNOWNFOLDERID`), and maintainer quotes read through `gh api` rather
than rendered pages.

### The premise is half right, and the half that is wrong is the important one

**uv documents itself as platform-specific.** `docs/reference/storage.md:10`: _"The paths of storage
directories are platform-specific. uv follows the XDG conventions on Linux and macOS and the Known
Folder scheme on Windows."_

| what uv stores  | Unix                             | Windows                        |
| --------------- | -------------------------------- | ------------------------------ |
| cache           | `$XDG_CACHE_HOME/uv`             | `%LOCALAPPDATA%\uv\cache`      |
| data            | `$XDG_DATA_HOME/uv`              | `%APPDATA%\uv\data`            |
| config          | `$XDG_CONFIG_HOME/uv`            | `%APPDATA%\uv`                 |
| **executables** | `$XDG_BIN_HOME` → `~/.local/bin` | **`%USERPROFILE%\.local\bin`** |

So "uv uses `.local` everywhere" is true of exactly one directory out of four.

### The split is the finding, and it has a mechanical cause

**The executable directory converges on `~/.local/bin` on every platform, Windows included** — uv,
pipx (`src/pipx/paths.py:19-21`, hardcoded `Path.home()/".local/bin"` with no platform branch) and
goose all do it. The reason is not taste. uv's maintainer **zanieb**, astral-sh/uv#13307:

> There is no equivalent tool binary directory on Windows so we _are_ using the XDG location as done
> in `pipx`.

Windows does have `FOLDERID_UserProgramFiles` (`%LOCALAPPDATA%\Programs`), and it is what the
XDG-implementing libraries map `XDG_BIN_HOME` to —
`platformdirs/src/platformdirs/windows.py:166-168`, `adrg/xdg` README:100. What it is not is a
**single shared directory already on `PATH`**, which is the gap `~/.local/bin` fills. Neither is
`~/.local/bin` itself: pipx's `ensurepath` has to add it (`docs/how-to/install-pipx.rst:97-100`) and
uv has an open request to do the same (#12550).

**Everything else runs the other way on Windows.** The dominant pattern is XDG env vars honoured on
_every_ platform, with only the _default_ branching — which is what the Rust `etcetera` crate calls
the CLI convention (README:50-53, "`Windows` on Windows & `XDG` everywhere else"), and what uv, gh,
helm, pnpm, corepack and mise each do in some form. **Full XDG-everywhere-including-Windows-defaults
is a real but minority practice**: git (`path.c:1545-1570`, no platform branch at all), chezmoi and
opencode. Nobody in the sample puts data or cache under `%USERPROFILE%\.local\share` by default
except those two.

A third pattern is at least as common as either and worth naming so it is not mistaken for this one:
**a single non-XDG dotdir everywhere** — `~/.cargo`, `~/.rustup`, `~/.deno`, `~/.bun`, `~/go`,
`~/.docker`. So "uniform across platforms" is ordinary. "Uniform _and_ XDG-shaped" is the contested
part.

### The real migration is macOS, and it is one-directional

Three in uv alone, all toward XDG, and the legacy readers are still in the tree as migration debt:

- **v0.3.0 / PR #5806**, listed under _Breaking changes_ — "Migrate to XDG and Linux strategy for
  macOS directories" (`changelogs/0.3.x.md:32-33`). `crates/uv-cache/src/cli.rs:50-52`: _"If the
  user has an existing directory at (e.g.) `/Users/user/Library/Caches/uv`, respect it for backwards
  compatibility. Otherwise, prefer the XDG strategy, even on macOS."_
- **v0.5.0 / PR #8420** — installer moved off `~/.cargo/bin` to `$XDG_BIN_HOME` → `~/.local/bin`, on
  Windows too.
- **v0.5.0 / PR #8048** — swapped the `directories` crate for `etcetera`, i.e. from a native-dirs
  library to one whose CLI default is XDG-on-macOS.

And outside uv: **platformdirs 4.6.0 / PR #375**, "Honor XDG environment variables on macOS",
implemented as `XDGMixin` mixed into `MacOS` and `Unix` — and pointedly **not** into `Windows`
(`macos.py:214`, `unix.py:262`, `windows.py:20`). `gh` already defaults macOS to `~/.config/gh`.

[DECISION: **so the family's existing shape is already right on the axis that is actually moving,
and it got there by having no macOS branch at all.** Every argument found against XDG-everywhere is
Windows-specific; the macOS traffic runs entirely the other way, and the only documented macOS
problem is with the _native_ path — pipx reverted `~/Library/Application Support` because the space
in it breaks shebangs. Nothing to change here, which is worth recording so the next session does not
re-open it.]

### The Windows counter-evidence is specific, and it has drawn blood

- **Microsoft says not to.** `Environment.SpecialFolder`: `UserProfile` — _"Applications should not
  create files or folders at this level; they should put their data under the locations referred to
  by ApplicationData."_ And the roaming split is the documented intent: `%APPDATA%` is _"for the
  current **roaming** user… kept on a server on the network and loaded onto a system when the user
  logs on"_; `%LOCALAPPDATA%` is _"the current, **non-roaming** user."_
- **Roaming actually broke uv**, astral-sh/uv#7008: tool venvs in `%APPDATA%` (Roaming) with the
  cache in `%LOCALAPPDATA%` (Local) — _"you'll login into a new machine… the `AppData\Roaming` will
  be copied/mounted there, but there will be no corresponding `uv` cache."_ **zanieb** agreed it
  seems problematic. **It is still unfixed**: `storage.md:56` still says `%APPDATA%\uv\data`.
- **Steve Dower (CPython Windows maintainer)**, same thread, is the sharpest statement against
  dot-dirs on Windows: _"Recent versions of Windows have made it so dot-prefixed directories are no
  longer actively hostile, so the `.cargo` and `.local` are now just messy, rather than anti-user."_
- **Known Folder redirection is the reason the XDG libraries refuse to hardcode.** `adrg/xdg`
  README:48-50: appropriate locations are used _"for common folders which may have been
  redirected"_. Writing to `%USERPROFILE%\.local` bypasses that by construction.
- **`directories-rs` refuses to answer at all**, README: `executable_dir` _"returns `None` on macOS
  and Windows"_, because _"the confusion and unexpected failure modes of such an approach would be
  immense."_

[PITFALL: **the opposite choice has its own casualty list, so this is not a one-sided trade.** pipx
moved to platformdirs in 1.2.0, **reverted macOS and Windows in 1.5.0** — _"They were leading to a
lot of issues with Windows sandboxing and spaces in shebangs on MacOS"_
(`docs/changelog.rst:758-760`) — then restored it in 1.16.0. The maintainer's write-up
(pypa/pipx#1247) is specific: `AppData` is subject to MSIX path redirection, which made `--python`
incompatible with Store Python, _"basically not fixable"_ and _"impossible to replicate in an
automated test"_. platformdirs documents the same sandbox behaviour independently
(`docs/explanation.rst:420-433`). Through all of it `PIPX_BIN_DIR` never moved off `~/.local/bin` on
any platform — the one thing nobody reverted.]

### The XDG spec does not reach past Unix

Version 0.8, 2021-05-08: **no occurrence of "Windows" or "macOS" anywhere in the file.** Defaults
are Unix absolute paths, and the bin sentence scopes itself — _"Distributions should ensure this
directory shows up in the **UNIX** `$PATH`"_ (lines 163-168). The spec **never defines
`XDG_BIN_HOME` at all**; `adrg/xdg` calls it _"the non-standard `XDG_BIN_HOME`"_. So "follow the
spec on Windows" is not a thing the spec offers, and every tool doing it is extending a convention
rather than implementing a standard.

`platformdirs` has **no XDG-everywhere option** — selection is a `sys.platform` check at import with
no override (`__init__.py:24-29`) — and on Windows it invented `WIN_PD_OVERRIDE_*` variables
precisely because _"Windows has no built-in convention for overriding folder locations at the
application level"_ (`docs/explanation.rst:383-387`).

### What the family already does, measured

`skill-authoring`'s destination table and the resolvers in `audit.py`/`plans.py` honour `$XDG_*`
first **on every platform** and branch only the default — byte-for-byte the pattern uv, gh, helm,
pnpm and mise converged on. `audit.py:58` even states the reason in the same terms a maintainer
would: _"`$XDG_STATE_HOME` wins on every platform, including Windows: a user who sets it means it.
Only the default is per-platform."_

[DECISION: **the family's table is already better than uv's on the one axis uv has an open bug
about**, and this is the strongest argument against changing it. uv puts _data_ in `%APPDATA%`
(Roaming) and its cache in `%LOCALAPPDATA%` (Local), which is exactly the split that broke in #7008.
The family's table puts config in `%APPDATA%` and state, data and cache all in `%LOCALAPPDATA%` — so
the machine-specific half travels together and the roaming half holds only what should roam. That is
Microsoft's documented intent applied correctly, arrived at independently, and it is not something
to trade away for uniformity.]

## Open questions

[NEEDS CLARIFICATION: **does the family adopt `~/.local/bin` on every platform for executables?**
This is the one place the evidence points at uniformity rather than away from it, and the family has
no rule for it — PULSE's XDG section covers installs (`~/.local/share/<tool>` plus a symlink into
`~/.local/bin`) but says nothing about what Windows would do. The convergent answer is
`%USERPROFILE%\.local\bin`, honouring `XDG_BIN_HOME` first, because Windows has no shared per-user
`PATH` directory and `%LOCALAPPDATA%\Programs` is not one. The cost is that it is not on `PATH`
there either, so whatever installs into it owns saying so.]

[NEEDS CLARIFICATION: **is `%APPDATA%` for config the right call, given that nothing else of ours
roams?** The family's table roams config and keeps everything else local, which is correct by
Microsoft's intent. But a config file naming absolute machine paths is exactly what Dower warns
about — _"anything that is specific to the current machine (e.g. file paths) either shouldn't go in
there or should be safe for transfer"_ — and `plan-docs`' config is a map of this machine's clone
paths to routes, which its own skill already says is per-machine and not worth syncing. So the one
file we roam may be the one file that must not. Worth checking against each config we actually write
rather than deciding in general.]

[NEEDS CLARIFICATION: **does anything here bind before the Windows port exists?** The two decisions
above are free while PULSE is Linux-only and the skills already ship their resolvers. The question
is whether to write the rule now — into `~/.agents/AGENTS.md`'s XDG section or the skills' table —
or leave it until the port forces it. Writing it now costs a rule that cannot be tested on this
machine; leaving it risks the port inventing a third answer, which is the failure the Windows plan
was already worried about.]

## Recommended direction

1. **Change nothing about config/data/cache/state.** The current shape matches what every comparable
   tool converged on, is better than uv's on the roaming axis, and the concern that prompted this —
   platform-specific complication — costs about six lines per resolver, written once and already
   tested. Record that it was checked, so it is not re-opened.
2. **Settle the executable directory**, which is the genuine gap and the one place uniformity wins.
   One sentence in the XDG section of `~/.agents/AGENTS.md`, if the answer is yes.
3. **Correct the Windows plan's framing.** It says "copy that, do not invent a second answer", which
   is right, but it reads as though the table were arbitrary. Point it here instead so the port
   inherits the reasoning rather than just the paths.
4. **Do not reach for a directories library.** `platformdirs` would replace six lines with a
   dependency, has no XDG-everywhere mode, and disagrees with the family on the bin directory
   (`%LOCALAPPDATA%\Programs`) — the one case where the family would be following the convergent
   practice and the library would not.

[UNVERIFIED: that `%USERPROFILE%\.local` actually roams under a Roaming User Profile. Microsoft's
_Deploy roaming user profiles_ page does not enumerate what is excluded, so the documented intent of
`%APPDATA%` versus `%LOCALAPPDATA%` plus two maintainers' statements is as far as the evidence goes.
Treat "a cache in `~/.local` gets copied over the network at logon" as plausible and unproven. It
matters only if the family ever puts non-bin data there, which recommendation 1 says it should not.]

[UNVERIFIED: no primary source found for OneDrive Known Folder Move touching the profile root or
`.local` — KFM is documented for Desktop/Documents/Pictures only. The redirection argument rests on
`adrg/xdg`'s rationale and platformdirs' MSIX note, both of which are about `AppData` rather than
about `.local`. Nothing was found on backup semantics or antivirus behaviour specific to `.local`
either way.]

[UNVERIFIED: the `astral-sh/uv` clone this survey read was fetched 2026-08-30, three weeks before
the survey. The storage documentation and `uv-dirs` are unlikely to have moved, and uv's own open
issue #7008 suggests the Windows half has not — but a decision that turns on uv's current behaviour
should re-fetch rather than trust a three-week-old tree.]
