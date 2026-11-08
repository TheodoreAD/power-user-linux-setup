# Kubernetes

The Kubernetes CLIs this repo installs, and how each one is kept up to date.

!!! WARNING

    Kubernetes may cause: headaches, fits of rage, binge eating, back pain and container orchestration.

All tools are declared in `setup.toml` and installed via invoke:

```shell
inv apt.install-repos   # kubectl
inv apt.install-debs  # k9s, freelens
inv tools.install  # kind, helm, tilt, ctlptl
```

Or all at once: `inv setup`

## kubectl

Kubernetes CLI — declared as `[packages.kubectl]` in `setup.toml`. The apt repo is version-specific
(`v1.33`); update the repo URL in `setup.toml` when upgrading to a new minor version.

## helm

Package manager for Kubernetes charts. After install, add repos you need:

```shell
helm repo add <name> <url>
helm repo update
```

## kind

Kubernetes in Docker — for when you kinda want the banana but without the gorilla and the whole
jungle.

Single-node cluster on your machine without the pain of kubeadm, kubelet & friends. Installed as a
direct binary download to `~/.local/bin/kind`.

```shell
kind create cluster
kind delete cluster
```

## k9s

Terminal UI for Kubernetes — browse clusters, pods, logs, exec into containers, port-forward, all
from the keyboard. Installed as a `.deb` from the latest GitHub release via `inv apt.install-debs`.

## Freelens

Open-source Kubernetes IDE (community fork of Lens). Installed as a `.deb` from the latest GitHub
release via `inv apt.install-debs`.

## Tilt

Live-update dev loop for Kubernetes — watches files and hot-reloads workloads without manual
`kubectl apply`.

**Usage reporting is switched off.** Tilt reports usage to `events.windmill.build` by default, so
`[packages.tilt]` seeds `~/.tilt-dev/analytics/user/choice.txt` with `opt-out`; `tilt analytics`
prints `analytics status : opt-out`. A Tiltfile calling `analytics_settings(True)` outranks that
file, which matters on a repo you do not control, and only an environment variable
(`TILT_DISABLE_ANALYTICS`, `DO_NOT_TRACK` or `CI`) outranks the Tiltfile. So `[packages.tilt]` also
exports `TILT_DISABLE_ANALYTICS=1` in `~/.zshenv`, which closes that gap for anything started from
zsh; the file still covers a launch from outside a shell. While it is on, each event carries hashes
of `uname -a`, the machine id and the git `origin` URL, plus Tilt's version, the OS and the
subcommand. A loaded Tiltfile adds how often each Tiltfile builtin and argument was used and the
names of loaded extensions, builds add their durations, and a running `tilt up` adds resource counts
and the cluster type. No source code, file contents or resource names are sent, except whatever tags
a Tiltfile hands `experimental_analytics_report`. The hashes are unsalted MD5, so anyone who can
guess an `origin` URL can confirm it was the repo in use.

## File-watch limits

kind and Tilt both lean on inotify: every kind node runs a kubelet sharing the host's per-user
limits, and Tilt watches the whole source tree. Below kind's recommended limits the failure is "too
many open files" from kubelet or a pod, which reads as a cluster bug rather than a host setting.
`inv system.raise-inotify-limits`, part of `inv setup`'s system phase, raises them on any machine
where the kind or tilt package is enabled:

| key                             | on an Ubuntu 24.04 desktop | raised to |
| ------------------------------- | -------------------------- | --------- |
| `fs.inotify.max_user_watches`   | 65536                      | 524288    |
| `fs.inotify.max_user_instances` | 128                        | 512       |

The 65536 is not the kernel's own figure: Ubuntu's `tracker` package pins it in
`/usr/lib/sysctl.d/30-tracker.conf`. The task writes `/etc/sysctl.d/60-pulse-inotify.conf`, which
sorts after that file and so wins, and it never lowers a value already above these.

## ctlptl

Declares a kind cluster together with a local image registry, so Tilt pushes images rather than
copying each one in with `kind load`. It reads the same analytics choice file as Tilt, and sends
nothing unless that file says `opt-in`, so the opt-out above covers it too.

```shell
ctlptl create cluster kind --registry=ctlptl-registry
ctlptl delete cluster kind-kind
```

## See also

- [Docker](docker.md) — the runtime underneath
- [Package catalog](packages.md) — how each of these CLIs is installed
