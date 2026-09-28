---
status: idea
updated: 2026-09-28
---

# Compound and piped sudo commands miss the credential cache in any run without a terminal

## Context

Without a terminal, sudo keys its credential cache on the **parent PID**. `util.ensure_sudo` stamps
it with `sudo -A -v` as a child of the `inv` process, then rebinds `util.SUDO` to `sudo -n`. A later
`c.run(f"{util.SUDO} …")` finds that stamp only if bash execs the sudo in place, so its parent is
still `inv`. A shell operator (`&&`, `||`, `;`, `|`) makes bash fork, the sudo's parent becomes that
bash, and `sudo -n` fails with `a password is required`. At a real terminal the cache is keyed on
the tty instead, so no interactive run has ever seen this.

Measured 2026-09-28 from an agent session, against one fresh stamp from the same Python process:

| Command                       | Exit |
| ----------------------------- | ---- |
| `sudo -n true` (direct)       | 0    |
| `bash -c 'sudo -n true'`      | 0    |
| `bash -c 'sudo -n true && :'` | 1    |

`util.sudo_write` was fixed in `260e6c8`: one lone sudo, and the tempfile removed from Python. Its
docstring carries the measurement. Found because the fix in `aacab99` could not repair four 0600
files from this session: every write failed until `sudo_write` stopped chaining its `rm`.

## Remaining call sites with the same shape

From `rg '(&&|\|\||;|\|)\s*\{(util\.)?SUDO\}' tasks` and its mirror, 2026-09-28:

- `tasks/wsl.py:155`: `rm -f` then `install` then `rm`, for `/etc/resolv.conf`.
- `tasks/wsl.py:378`: `mkdir -p`, `install`, `rm`, for `/etc/wsl.conf`.
- `tasks/docker.py:88`: the same, for `daemon.json`.
- `tasks/certs.py:42`: the same, in `certs`' private `_sudo_write`.
- `tasks/apt.py:162` and `:628`: `curl … | sudo gpg --dearmor -o …`, for a repo key.
- `tasks/apt.py:173`: `printf … | sudo tee …`, for a sources entry.

A multi-line command or a `sh -c` wrapper would not match those patterns, so the list is a floor.

**Also unverified, same area:** `ensure_sudo` returns early under `PULSE_DRY_RUN` without rebinding
`SUDO`, so a dry run's `sudo_read` runs `sudo -A cat …` (or plain `sudo cat …` with no askpass)
inside a hidden `c.run`. That can raise an askpass dialog per read, or at a terminal without askpass
reach the invisible in-invoke prompt the repo forbids. A dry run from this agent session reported
`MISSING` for all four 0600 files without any visible dialog, which fits every read failing
silently. Check that before trusting a dry run's report of a root-owned file.

**Leftover on this machine:** `/etc/systemd/journald.conf.d/size.conf` now carries the setting
twice, an unmarked copy from before PULSE's block markers and the marked block `cap-journal-size`
added on 2026-09-28. Identical values, so harmless. Removing the unmarked copy is a hand edit of a
system file, so it was left alone.

## Open questions

[NEEDS CLARIFICATION: **one helper or two.** The `mkdir`/`install`/`rm` sites all collapse into
`sudo_write` with a `mkdir -p` issued as its own lone `c.run` first. The pipeline sites need the
data handed to a lone sudo some other way: fetch the key in Python and pass it on stdin
(`c.run(f"{SUDO} gpg --dearmor -o {gpg}", in_stream=…)`), or write it to a tempfile and `install`
it. Whether stdin through invoke is safe here, given the Python 3.14 stdin-forwarding bug in
`contributing/interactive-input.md`, decides between them.]

## Recommended direction

Give `sudo_write` an optional `mkdir` and move the four compound writers onto it. Rework the three
pipelines to fetch in Python and install from a tempfile, avoiding stdin through invoke altogether.
Add a unit test that fails on any `c.run` whose command contains a shell operator and `SUDO`, so the
shape cannot come back, and fix the dry-run rebinding in the same pass.
