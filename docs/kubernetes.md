# Kubernetes

!!! WARNING

    Kubernetes may cause: headaches, fits of rage, binge eating, back pain and container orchestration.

All tools are declared in `setup.toml` and installed via invoke:

```shell
inv apt.repos   # kubectl, helm, tilt
inv apt.deb  # k9s, freelens
inv tools.install  # kind
```

Or all at once: `inv setup`

## kubectl

Kubernetes CLI — declared as `[packages.kubectl]` in `setup.toml`. The apt repo is version-specific (`v1.33`); update the repo URL in `setup.toml` when upgrading to a new minor version.

## helm

Package manager for Kubernetes charts. After install, add repos you need:

```shell
helm repo add <name> <url>
helm repo update
```

## kind

Kubernetes in Docker — for when you kinda want the banana but without the gorilla and the whole jungle.

Single-node cluster on your machine without the pain of kubeadm, kubelet & friends. Installed as a direct binary download to `~/.local/bin/kind`.

```shell
kind create cluster
kind delete cluster
```

## k9s

Terminal UI for Kubernetes — browse clusters, pods, logs, exec into containers, port-forward, all from the keyboard. Installed as a `.deb` from the latest GitHub release via `inv apt.deb`.

## Freelens

Open-source Kubernetes IDE (community fork of Lens). Installed as a `.deb` from the latest GitHub release via `inv apt.deb`.

## Tilt

Live-update dev loop for Kubernetes — watches files and hot-reloads workloads without manual `kubectl apply`.
