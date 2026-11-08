---
status: idea
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

[NEEDS CLARIFICATION: a drop-in file (`/etc/sysctl.d/<nn>-inotify.conf`, owned whole by this repo)
or a managed block in `/etc/sysctl.conf` following the `system.disable-ipv6` precedent. The drop-in
is the more conventional shape for a setting this repo owns outright; the precedent argues for
consistency.]

[NEEDS CLARIFICATION: whether this is its own `inv system.*` task or attaches to the kind/tilt
packages so it applies whenever they are installed.]

## Recommended direction

Set both keys to kind's recommended values, apply immediately with `sysctl --system` (or `-p` on the
file), and make the task idempotent and verifiable — the hekate repo's planned doctor task will
check the live values and point here for the fix.
