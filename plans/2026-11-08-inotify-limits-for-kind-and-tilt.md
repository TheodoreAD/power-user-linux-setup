---
status: landed
updated: 2026-11-08
source_repo: github.com-personal/agent-skills
source_session: cfdd5789-b3d9-4818-a387-308047144830.jsonl
source_moment: 2026-11-08T15:07:06Z
source_plan: _unscoped/2026-11-08-hekate-tilt-kind-monorepo.md
---

# Raise inotify limits for kind and Tilt

## Context

The planned `hekate` monorepo (a Tilt + kind local-dev stack, plan in the store's `_unscoped/` area)
runs a kind cluster with Tilt watching files. Both lean on inotify: every kind node runs a kubelet
and its own watchers inside a container sharing the host's per-user limits, and Tilt watches the
whole source tree.

Measured on this machine 2026-11-08 with
`sysctl fs.inotify.max_user_watches
fs.inotify.max_user_instances`:

| key                             | current | kind's known-issues recommendation |
| ------------------------------- | ------- | ---------------------------------- |
| `fs.inotify.max_user_watches`   | 65536   | 524288                             |
| `fs.inotify.max_user_instances` | 128     | 512                                |

Below those values the failure is "too many open files" from kubelet or a pod, most often with
multi-node clusters or large repos, and it reads as a cluster bug rather than a host setting.

Nothing in this repo touches inotify today (checked 2026-11-08 outside `cli-allowlist/`). The
closest precedent is `inv system.disable-ipv6`, which manages keys in `/etc/sysctl.conf`
(`docs/configuration.md`).

## Evidence

Asked in agent-skills session `cfdd5789-b3d9-4818-a387-308047144830.jsonl`, around
2026-11-08T15:07Z. The user's words: "file the inotify and ctlptl plans for power-user-linux-setup,
and that the kind tilt stack needs a doctor task to check it has all the right things installed".
The limits were read earlier in that session, while assessing whether kind + Tilt is realistic on
this 6-core, 31 GiB machine.

## Open questions

[DECISION: **a drop-in, `/etc/sysctl.d/60-pulse-inotify.conf`.** `tasks/system.py`'s `_owned_dropin`
docstring already settled it — "a setting of one's own belongs in a drop-in of one's own" — after
`/etc/systemd/journald.conf.d/size.conf` carried a setting twice. 60 because Ubuntu's
`/usr/lib/sysctl.d/30-tracker.conf` is what pins 65536 on a GNOME desktop, so the drop-in must sort
after it, and before `99-sysctl.conf` so a value in `/etc/sysctl.conf` still wins. Confirmed with
`sysctl --system --dry-run`: 30-tracker sets 65536, then 60-pulse sets 524288.]

[DECISION: **its own task, `inv system.raise-inotify-limits`, in setup's system phase, a no-op
unless kind or tilt is enabled.** Chosen by the user 2026-11-08 over running on every machine and
over a standalone task setup never calls.]

[DECISION: **raise, never lower.** The kernel sizes `max_user_watches` from RAM when no file sets
it, which can exceed 524288, and a fixed value in the drop-in would cut it at the next boot. So each
key in the drop-in is the higher of the target and the live value, and only keys below target are
applied live with `sysctl -w`. Reasoned while writing the task, not hit.]

## Recommended direction

Set both keys to kind's recommended values, apply immediately with `sysctl --system` (or `-p` on the
file), and make the task idempotent and verifiable — the hekate repo's planned doctor task will
check the live values and point here for the fix.

## Verification

The original measurement was 65536/128 on this machine, read in the agent-skills session named
above. After `inv system.raise-inotify-limits` on 2026-11-08 the live values are 524288 and 512, the
task's dry run reports both the drop-in and the live limits `ok`, and `sysctl --system --dry-run`
applies `60-pulse-inotify.conf` after `30-tracker.conf`, so the value survives a reboot.

## Migrated to

- **The task**: `inv system.raise-inotify-limits` in `tasks/system.py`, commit `01696d6`. The
  drop-in's number, the raise-never-lower rule and the kind/tilt gate are commented there.
- **Usage docs**: `docs/kubernetes.md`, "File-watch limits", including where the 65536 comes from;
  `docs/configuration.md`'s managed-files table and system-phase list.

Deliberately not migrated: the hekate doctor's check of these values. It belongs to hekate and is in
its own plan.
