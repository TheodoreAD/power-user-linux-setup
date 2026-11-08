---
status: idea
updated: 2026-11-08
source_repo: github.com-personal/agent-skills
source_session: cfdd5789-b3d9-4818-a387-308047144830.jsonl
source_moment: 2026-11-08T15:07:06Z
source_plan: _unscoped/2026-11-08-hekate-tilt-kind-monorepo.md
---

# ctlptl as a setup.toml package

## Context

The planned `hekate` monorepo (a lightweight Tilt + kind local-dev stack, plan in the store's
`_unscoped/` area) creates its kind cluster with `ctlptl`, Tilt's own tool for declaring a kind
cluster together with a local image registry. Without the registry every image has to be copied in
with `kind load`, which is the slow path on this 6-core machine. `kind`, `tilt` and `kubectl` are
already `[packages.*]` entries in `setup.toml`; `ctlptl` is not, and nothing in this repo mentions
it (checked 2026-11-08 outside `cli-allowlist/`).

Judged 2026-11-08 with `package_health.py`:

- **No PyPI wrapper** (`pypi ctlptl` returns 404), so the uv-tool route is unavailable.
- **`github tilt-dev/ctlptl`**: 83 stable releases, 8 in the last year, median gap 41 days, latest
  v0.9.6 on 2026-09-10; Apache-2.0; 5 human committers in 365 days, bus factor 1. Ships
  `ctlptl.<version>.linux.x86_64.tar.gz` (17.0 MB) with a `checksums.txt`, no signature.

## Evidence

Asked in agent-skills session `cfdd5789-b3d9-4818-a387-308047144830.jsonl`, around
2026-11-08T15:07Z. The user's words: "file the inotify and ctlptl plans for power-user-linux-setup,
and that the kind tilt stack needs a doctor task to check it has all the right things installed".
The gap itself was found earlier in that session: `which kind tilt kubectl ctlptl podman` printed
`ctlptl not found`.

## Open questions

[NEEDS CLARIFICATION: which `tags` the entry carries — `["k8s", "dev"]` like kind and tilt is the
obvious answer; confirm against how tags select installs.]

## Recommended direction

Add `[packages.ctlptl]` with `method = "archive"`, modelled directly on `[packages.tilt]`: the asset
naming is the same scheme (`<tool>.{version}.linux.x86_64.tar.gz`), so `version_cmd` and
`download_url` copy over with the repo name changed. `check_cmd = "ctlptl"`; add
`zshrc = "source <(ctlptl completion zsh)"` if ctlptl ships completion like kind does.

[UNVERIFIED: that ctlptl's archive lays the binary out the same way tilt's does, so the archive
method extracts it without extra config. Check the tarball's contents before relying on it.]
