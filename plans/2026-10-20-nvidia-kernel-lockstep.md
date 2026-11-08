---
status: idea
updated: 2026-10-20
source_repo: github.com-personal/agent-skills
source_session: 24d8b75b-4a2c-49eb-aaa0-da619810b928.jsonl
source_moment: 2026-10-20
source_plan:
---

# Nvidia kernel lockstep

## Context

Recurring failure: after an unattended kernel upgrade, the desktop boots at 640x480 because no
NVIDIA kernel module exists for the new kernel. GNOME falls back to `simpledrm` (EFI framebuffer),
`xrandr` shows a single `None-1` output, and `lspci -k` shows no `Kernel driver in use` for the RTX
3070 Ti. The user reports this has happened before ("again").

Mechanism, confirmed from logs on 2026-10-20:

- 2026-10-10 06:09 `unattended-upgrade` installed `linux-image-6.8.0-146-generic` and bumped
  `linux-generic`/`linux-image-generic`/`linux-headers-generic` from 142 to 146.
- In the same run it held back the entire NVIDIA set — `linux-modules-nvidia-595-open-generic`,
  `nvidia-driver-595-open`, every `libnvidia-*-595` — logging
  `kept back because a related package is kept back or due to local apt_preferences(5)` daily from
  10-10 onwards. No holds, no apt preferences in play.
- The NVIDIA side of that upgrade was not a plain upgrade: the driver moved 595.91.07 → 595.99.02,
  which needs a **new** package (`nvidia-firmware-595-595.99.02`) and **removes**
  `linux-modules-nvidia-595-open-6.8.0-142-generic`. unattended-upgrades refuses upgrades that
  remove packages, so the NVIDIA group stays put while the kernel metas, which need no removal, go
  through.
- Result: kernel N+1 is default in GRUB, module exists only for kernel N.

So the trigger is the coincidence of a kernel bump with an NVIDIA driver version bump, which is
frequent enough to recur.

Manual fix applied 2026-10-20 (from an agent-skills session, not via this repo):
`sudo -A apt-get update` then
`sudo -A apt-get install linux-modules-nvidia-595-open-6.8.0-146-generic linux-modules-nvidia-595-open-generic linux-generic`
— which also pulled kernel 147 with its matching module. `modinfo -k <kver> -F version nvidia`
returns 595.99.02 for both 146 and 147. The first install attempt 404'd on a stale index; the update
was required.

## Evidence

- `/var/log/apt/history.log`, Start-Date 2026-10-10 06:09:02: kernel 146 install with metas
  upgraded; no NVIDIA module package in that transaction.
- `/var/log/unattended-upgrades/unattended-upgrades.log` lines from 2026-10-10 06:10:18 onward:
  `Package linux-modules-nvidia-595-open-generic is kept back because a related package is kept back`.
- `apt-get -s install linux-modules-nvidia-595-open-generic` on 2026-10-20 showed the NEW firmware
  package plus the REMOVE of the 142 module — the shape u-u will not apply.
- Transcript: session `24d8b75b-4a2c-49eb-aaa0-da619810b928.jsonl` in agent-skills' project dir,
  user prompt "the graphics driver on this linux machine is again defaulting to 640x480 resolution".

## Open questions

- Blacklisting the kernel metas in unattended-upgrades also stops **security** kernel updates
  arriving automatically. Acceptable on a desktop that is rebooted rarely anyway, or should the
  mechanism instead be a scheduled task that does a full `apt-get dist-upgrade`, which does allow
  removals?
- Is there a u-u knob that permits the removal of superseded `linux-modules-nvidia-*-<old kver>`
  packages specifically? Check the unattended-upgrades source (clone into `$RESEARCH_HOME`) before
  concluding there is none.
- Should `inv verify.all` (or a login-time check) flag "default GRUB kernel has no nvidia module" so
  the failure is caught before a reboot rather than after?

## Recommended direction

User chose (2026-10-20) the unattended-upgrades blacklist route over switching to
`nvidia-dkms-595-open`:

- Declare `Unattended-Upgrade::Package-Blacklist` entries for `linux-generic`,
  `linux-image-generic`, `linux-headers-generic` (regex-anchored) in a PULSE-managed
  `/etc/apt/apt.conf.d/` drop-in, via `setup.toml`, so kernel and NVIDIA metas only move together on
  a manual `apt full-upgrade`.
- Pair it with a verify check: for the kernel `/boot/vmlinuz` points at, `modinfo -k <kver> nvidia`
  must succeed. Cheap, and catches every other path to the same break.
