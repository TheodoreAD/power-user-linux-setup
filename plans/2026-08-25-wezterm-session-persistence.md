---
status: idea
updated: 2026-08-25
---

# Persisting WezTerm pane arrangement across a logout

## Context

Question raised 2026-08-25: can the arranged panes in WezTerm survive a logout, and what are the
alternatives? Nothing was implemented — this file exists so the research doesn't have to be redone
if the topic is picked up later.

Three distinct things get conflated under "persist my panes", and only the first is currently
solved:

1. **Layout** — already persists. `config/wezterm.lua`'s `gui-startup` hook builds the 2x2 grid
   declaratively on every launch, so it is rebuilt from config rather than restored from state. The
   `ALT+1..4` bindings depend on that split order.
2. **Per-pane cwd** — not persisted.
3. **Live processes surviving the logout** — not persisted.

Adding per-pane `cwd` to the `gui-startup` hook was considered and **explicitly declined**: fzf
shell history already makes getting back to a directory low-effort, so the config complexity buys
nothing. Don't re-propose it without a new reason.

## Option landscape

### A. Extend the declarative layout

Per-pane `cwd`/`args` in `gui-startup`. Zero dependencies, versioned in this repo, deploys via
`inv deploy.all --name wezterm`. Covers (2) for a fixed workspace only. **Declined — see above.**

### B. A session-manager plugin

Covers (2), and depending on the plugin either replays scrollback or re-launches processes. Does not
cover (3) — processes are re-started, not kept alive. See the plugin survey below.

### C. WezTerm unix multiplexer domain

```lua
config.unix_domains = { { name = "unix" } }
config.default_gui_startup_args = { "connect", "unix" }
```

The GUI becomes a client of `wezterm-mux-server`, which holds the panes. Genuinely covers (3).
Survives closing the GUI out of the box; surviving a _logout_ additionally needs a systemd user unit
plus lingering. Would require reworking the `gui-startup` hook, which fires per GUI connect rather
than per mux window.

### D. A multiplexer inside WezTerm

- **zellij** — built-in session resurrection, serializes layout plus the command per pane, optional
  viewport/scrollback. Not currently in `setup.toml`.
- **tmux** — already installed (`[packages.tmux]`, no config deployed). Needs `tmux-resurrect` +
  `tmux-continuum` to match zellij's built-in behavior.

Trade-off for both: the WezTerm panes collapse into one frame and the multiplexer's own keybindings
shadow `ALT+1..4` / `CTRL+Tab`.

## systemd lingering (needed by option C)

A logged-in user has two separate cgroup trees. `session-N.scope` holds everything forked from the
login and is governed by `KillUserProcesses=`. `user@1000.service` holds everything run by the user
manager — i.e. `systemctl --user` units — and is stopped when the last session ends unless lingering
is enabled. `man loginctl`: _"If enabled for a specific user, a user manager is spawned for the user
at boot and kept around after logouts."_

State is a zero-byte file at `/var/lib/systemd/linger/<username>`. Verified 2026-08-25 on this
machine (systemd 255): the directory is empty and `loginctl show-user tdumitrescu` reports
`Linger=no`.

[PITFALL: lingering is per-user, not per-unit — enabling it for one mux server means every
`systemctl --user` unit added afterwards also starts at boot and outlives logout.]

[PITFALL: a lingering unit started at boot has no graphical session — no
`DISPLAY`/`WAYLAND_DISPLAY`, no session D-Bus, no `keychain`-managed ssh-agent. This machine's
`askpass-zenity` helper cannot pop a dialog from a pre-login mux server, so a pane triggering
`sudo -A` or an SSH key prompt there hangs instead of prompting.]

[PITFALL: `KillUserProcesses` is unset in `/etc/systemd/logind.conf` (line 22 commented), so the
compiled default `no` applies — `man logind.conf` says the scope is "abandoned" rather than killed.
A mux server spawned by the GUI therefore sits in the session scope and may already survive logout
by accident. Don't build on that: nothing restarts it after a reboot or a crash, it is undeclared
machine state, and GNOME session teardown or `loginctl terminate-user` ends it anyway.]

Enabling it would be a `setup.toml` entry plus a task, not a one-off
`sudo -A loginctl enable-linger tdumitrescu`.

## `wezterm.plugin.require` mechanics (needed by option B)

At config-evaluation time WezTerm mangles the plugin URL into a directory name, clones the repo into
`<runtime_dir>/plugins/<mangled>` if absent, and requires `init.lua` from the repo root or a
`plugin/` subdirectory. Runtime dir here is `~/.local/share/wezterm/` (verified 2026-08-25 — holds
only `check_update`, no `plugins/` yet).

Mangling: `/` and `\` → `sZs`, `:` → `sCs`, `.` → `sDs`. So
`https://github.com/abidibo/wezterm-sessions` becomes
`~/.local/share/wezterm/plugins/httpssCssZssZsgithubsDscomsZsabidibosZswezterm-sessions`.

[PITFALL: a trailing slash changes the mangled directory name, producing two clones of the same
plugin (wezterm#5883).]

[PITFALL: the clone happens once and is never refreshed; updates come only from
`wezterm.plugin.update_all()`, which pulls every plugin at once. There is no tag/branch/commit
pinning and no lockfile.]

[PITFALL: config evaluation blocks on that git clone, so a failure — offline, DNS, GitHub down —
errors the whole `wezterm.lua`, losing the 2x2 grid and the keybindings along with the plugin. Wrap
the require in `pcall` if a plugin is ever adopted.]

[PITFALL: never call `update_all()` from the config — it turns every launch into a network fetch of
unreviewed upstream code, and is the recurring offline-breakage report upstream.]

A plugin fetched this way is also an undeclared install at an unpinned revision, which contradicts
this repo's core premise. The fix that fits: pre-seed the clone as a `[packages.*]` entry with
`method = "git-clone"` and the mangled path as `dest`, so WezTerm finds it already present and never
reaches the network.

[DEFERRED: `_install_git_clone` (`tasks/tools.py:66-80`) accepts only `repo`/`dest`/`depth` and
skips when `dest` exists, so such an entry would declare _what_ is installed but not _which commit_.
Real pinning needs a `ref` field added to the `git-clone` method.]

## Plugin survey (as of 2026-08-25)

Everything in this space descends from one of two roots, and both roots are unmaintained. State file
formats are not compatible across lineages, so switching later discards saved sessions.

**Lineage A** — `danielcopper/wezterm-session-manager` (145 stars, last push 2024-07-23) → rewritten
as `abidibo/wezterm-sessions`.

**Lineage B** — `MLFlexer/resurrect.wezterm` (317 stars) and its companion
`MLFlexer/smart_workspace_switcher.wezterm` (205 stars), **both archived 2026-05-24** when the
maintainer moved to a PhD. The archive notice names no successor: _"Please fork/use one of the forks
instead."_ Of 48 forks, only one has meaningful divergence. No maintained fork of
`smart_workspace_switcher` exists — all 8 of its forks sit at 0 stars, so that half of the ecosystem
is simply gone.

| Repo                                      | Stars | Last push  | License | Lineage |
| ----------------------------------------- | ----- | ---------- | ------- | ------- |
| `YedPool/Wezurrect`                       | 10    | 2026-08-17 | MIT     | B       |
| `abidibo/wezterm-sessions`                | 27    | 2026-05-25 | MIT     | A       |
| `neerajsingh0101/wezterm-session-restore` | 3     | 2026-07-11 | —       | B       |
| `Yuto729/tidy-sessions.wezterm`           | 1     | 2026-02-02 | —       | —       |

### `YedPool/Wezurrect`

Resurrect's feature set carried forward: restores workspaces, windows, tabs, panes, cwd, scrollback
text, active/zoom state, and remote domain reattachment (SSH/SSHMUX/WSL/Docker). Saves on pane/tab
change, periodically (default 5 min), and manually. Adds a startup instance selector with window/
pane counts and project names, tombstone + backup rotation fixing a restore-then-save data-loss bug,
7-day retention pruning, and optional `age`/`rage`/GnuPG encryption. Four commits since the upstream
archive, roughly fifteen since March 2026.

[PITFALL: state is plaintext JSON by default and the plugin captures scrollback, so anything echoed
into a pane — tokens, keys — lands on disk unless encryption is enabled.]

[PITFALL: Wezurrect ships Claude Code integration that configures a `SessionStart` hook and resumes
sessions via `--resume <session-id>`. `inv allowlist.apply` already owns `~/.claude/settings.json`
and rewrites it from `cli-allowlist/`. Two writers, one file, neither aware of the other — the
feature must be disabled explicitly if this plugin is ever adopted.]

### `abidibo/wezterm-sessions`

Different goal: re-launches processes rather than replaying their output. Restores workspaces
(matched by name), windows, tabs, panes, cwd, the foreground process, and the git branch per pane;
warns when a branch moved since the save. Also offers a session preview in the picker and a "fork
session" that duplicates the current layout into a new workspace. `auto_save_interval_s` defaults to
30.

[PITFALL: process restore reads `/proc/<pid>/cmdline`, is Linux/macOS only, and the README is candid
that not all processes can be restored successfully.]

[PITFALL: state files default into the plugin directory — i.e. inside the git clone — so an
`update_all()` pull can collide with saved sessions. `save_state_dir` must be set explicitly, e.g.
`~/.local/share/wezterm-sessions/state/`.]

Restore is manual (`ALT+l` / `ALT+r`); there is no auto-restore at startup, so the declarative
`gui-startup` grid builds first and a session is loaded over it.

### The other two

`neerajsingh0101/wezterm-session-restore` is another resurrect fork whose selling point is likewise
Claude Code auto-resume — same settings-file collision, less activity than Wezurrect.
`Yuto729/tidy-sessions.wezterm` shows no reason to be preferred over either.

## Recommended direction

Nothing to do now. The declarative grid already covers the layout, and per-pane cwd was declined.

[DEFERRED: if this is picked up again, first re-check `YedPool/Wezurrect` — whether it has actually
become the dominant successor to the archived `resurrect.wezterm` (star growth, issue traffic,
whether other forks defer to it, whether the ecosystem's plugin lists point at it), and how it has
fared as a maintained project. That verdict is the deciding input; the stated preference is to
revisit it specifically rather than re-survey the field from scratch.]

## Open questions

[NEEDS CLARIFICATION: which of the three persistence goals is actually wanted — layout only is
already solved, and only option C or D keeps processes alive through a logout. The answer picks the
option, and the options are not incremental steps toward one another.]

[NEEDS CLARIFICATION: whether a single-maintainer, sub-30-star plugin is an acceptable dependency
for this repo at all, given `wezterm.plugin.require` offers no version pinning and the whole
ecosystem's upstream is archived.]

[NEEDS CLARIFICATION: if option C or D is ever chosen, whether the per-user side effects of
lingering are acceptable on this machine — it changes what logging out means for every future
`systemctl --user` unit, not just the mux server.]
