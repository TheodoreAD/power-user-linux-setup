---
status: idea
updated: 2026-09-28
---

# System files written before `sudo_write`'s 0644 fix stay root-only forever

## Context

`0a96f4e` (2026-09-01) made `util.sudo_write` use `install -m 0644` instead of `cp`, because a
`NamedTemporaryFile` is 0600 and `cp` carried that mode onto every root-owned file PULSE wrote. The
fix covers new writes only. Every caller compares **content** first and returns early on a match —
`apt.configure` ("already configured"), the apparmor loop in `system.py` ("already installed"), and
the journald/resolved writers the same way. So a file written before the fix, with the right content
and the wrong mode, is never rewritten, and no run of `inv setup` repairs it.

Surfaced 2026-09-28 while diagnosing an unrelated nvidia driver hold-back: every `apt-cache` and
`apt-get -s` run as the user warned `Unable to read /etc/apt/apt.conf.d/99-pulse`, with
`Permission denied`. Harmless to root's apt runs, but it is noise on every unprivileged apt query,
and it means the setting silently does not apply to them.

## Evidence

`find … -type f -perm 600` over every destination a `sudo_write` caller targets, 2026-09-28:

| Mode | mtime      | Path                                          | Writer                    |
| ---- | ---------- | --------------------------------------------- | ------------------------- |
| 600  | 2026-06-08 | `/etc/apt/apt.conf.d/99-pulse`                | `apt.configure`           |
| 600  | 2026-06-08 | `/etc/systemd/journald.conf.d/size.conf`      | `system.py` journald size |
| 600  | 2026-06-08 | `/etc/systemd/resolved.conf.d/pulse-dns.conf` | `system.py` resolved DNS  |
| 600  | 2026-06-09 | `/etc/apparmor.d/jbr-cef`                     | `system.py` apparmor loop |
| 600  | 2020-01-22 | `/etc/docker/key.json`                        | docker itself, not PULSE  |

All four PULSE files predate `0a96f4e`. `/etc/sysctl.conf` and `initramfs.conf` are not 0600,
presumably because they were edited in place of a distro file that already existed. `certs.py` has
its own `_sudo_write` (line 38), not checked here.

## Open questions

[NEEDS CLARIFICATION: **repair in each caller, or once in `util`.** Options:

- make "already configured" mean content **and** mode, so each caller's early return re-installs a
  file whose mode is wrong — one helper (`util.sudo_file_matches(path, text)`) used by every caller;
- a one-off repair task that `chmod 0644`s the known destinations, which fixes this machine and
  nothing that drifts later.

The first holds by construction and also catches a hand-`chmod`; the second is a one-off, which this
repo avoids.]

## Recommended direction

Add a content-and-mode check to `util`, switch every `sudo_write` caller's early return to it, and
add a unit test that a 0600 file with matching content is rewritten. Check `certs.py`'s private
`_sudo_write` in the same pass, and say in its docstring why it differs, if it still should.
