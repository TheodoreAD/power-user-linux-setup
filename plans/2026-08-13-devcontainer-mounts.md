---
status: landed
updated: 2026-08-13
---

# Dev container: mounting host directories (credentials, certs, config)

## Context

The dev-container pipeline (`plans/2026-08-08-devcontainer-pipeline.md`, landed) gets a fresh
container to a fully-provisioned shell, but every credential-shaped thing is either missing or
regenerated from scratch on every container: `inv identity.init` has to be re-run, `ssh.keys`
mints a brand-new keypair (which then needs re-adding to GitHub), and the corporate CA bundle
`certs.install` needs isn't present at all. This is real, unnecessary friction for repeated use of
the same container-based workflow.

This is greenfield — confirmed by exploration: no `.aws`/`.kube`/`.gnupg` awareness anywhere in the
repo, no existing volume/bind-mount or SSH-agent-forwarding logic, and `docs/dev-container.md` says
nothing about credentials today. The closest precedents are `tasks/identity.py`'s
interactive-wizard-over-a-small-fixed-list shape and `tasks/proxy.py`'s host-environment-discovery
pattern (network only) — reused below for the new discovery/prompt flow.

Scope decisions:

- **Docs + an interactive helper task** (not docs-only) — `inv devcontainer.mounts`, in the same
  `tasks/devcontainer.py` module, host-side (run before `devcontainer up`/opening in VS Code, not
  inside the container — mounts are fixed at container-creation time, `postCreateCommand` runs too
  late to add any).
- **SSH: agent forwarding by default**, with an explicit Linux-vs-WSL2 reality check (researched,
  not assumed — WSL2 + Docker Desktop's SSH-agent-forwarding-into-a-container path has multiple
  open, unresolved upstream issues, e.g. `microsoft/vscode-remote-release#3902`/`#8689`/`#2925`).
  The task probes what's actually forwardable on **this** host rather than always emitting the same
  JSON, and falls back to a direct `~/.ssh` mount (with a security caveat) when forwarding isn't
  detectable.
- **No "mount other project repos" auto-discovery.** Dev containers are repo-bounded by
  convention — the current repo is already auto-mounted as the workspace folder by the devcontainer
  spec itself, no config needed. "Code directories" doesn't need a feature; it needs one sentence
  in the docs saying this is automatic, plus a one-line manual-mount example for the rare case of
  genuinely needing a sibling repo too.

## Design

### 1. `inv devcontainer.mounts` (new task, `tasks/devcontainer.py`)

Host-side, read-only discovery + interactive selection + printed output — never mutates anything
(no file writes, unlike `render_docs`), so `util.DRY_RUN` doesn't apply; only `util.interactive()`
gates the per-item prompts (falls back to each candidate's default when non-interactive, same as
every other `confirm`/`prompt_text` call site).

**Candidate catalog** (a list of small dataclasses/namedtuples — id, label, default, discovery +
render logic), each only offered if actually discoverable on this host:

| id                      | host path                                                                                                                   | container target                                                              | default                                                                   | mode             |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------- | ---------------- |
| `ssh-agent`             | `$SSH_AUTH_SOCK` (socket)                                                                                                   | `/tmp/ssh-agent.sock` + `remoteEnv.SSH_AUTH_SOCK`                             | True if socket exists                                                     | agent forward    |
| `ssh-dir`               | `~/.ssh`                                                                                                                    | `<container-home>/.ssh`                                                       | True _only if_ `ssh-agent` wasn't offered/accepted                        | bind, read-write |
| `pulse-identity`        | `~/.config/pulse` (`util.PULSE_CONFIG_DIR`)                                                                                 | `<container-home>/.config/pulse`                                              | True if exists                                                            | bind, read-write |
| `corporate-cert-bundle` | resolved from `identity.toml`'s `[certs] bundle` (reuse the same resolution shape as `tasks/certs.py`'s `_resolve_paths()`) | **same absolute path** as host (not container-home-relative — see note below) | True if resolvable                                                        | bind, read-only  |
| `gitconfig`             | `~/.gitconfig`                                                                                                              | `<container-home>/.gitconfig`                                                 | True if exists                                                            | bind, read-only  |
| `gnupg`                 | `~/.gnupg`                                                                                                                  | `<container-home>/.gnupg`                                                     | False (GPG agent/pinentry forwarding is known-fiddly — noted, not solved) | bind, read-write |
| `aws`                   | `~/.aws`                                                                                                                    | `<container-home>/.aws`                                                       | False                                                                     | bind, read-only  |
| `kube`                  | `~/.kube`                                                                                                                   | `<container-home>/.kube`                                                      | False                                                                     | bind, read-only  |
| `gcloud-config`         | `~/.config/gcloud`                                                                                                          | `<container-home>/.config/gcloud`                                             | False                                                                     | bind, read-only  |
| `gh-config`             | `~/.config/gh`                                                                                                              | `<container-home>/.config/gh`                                                 | False                                                                     | bind, read-only  |

Key design points:

- **Why the corporate cert bundle mounts at an identical absolute path, not container-home-relative**:
  `identity.toml`'s `[certs] bundle` field is (and stays) an absolute host path, read verbatim by
  `tasks/certs.py` at runtime inside the container — no path-translation layer exists or should be
  invented for this. Mounting the bundle file at the exact same absolute path inside the container
  means the _also-mounted_ `identity.toml` keeps resolving correctly with zero changes to
  `certs.py`. Every other candidate is a conventional dotfile under `$HOME`, which normalizes fine
  across different host/container usernames.
- **`ssh-agent` detection**: `os.environ.get("SSH_AUTH_SOCK")` plus `Path(sock).exists()`. If
  `util.is_wsl()` is true, print an explicit caveat before offering it — WSL2 (especially through
  Docker Desktop's WSL integration, `util.is_docker_desktop_wsl_integration()`, already exists in
  `util.py`) is the specific combination with multiple open upstream forwarding bugs; the reliable
  fix (running `ssh-agent` natively _inside_ WSL2 rather than relying on a Windows-side agent) gets
  a one-line pointer, not new automation — out of scope to build/verify a Windows named-pipe bridge.
  If no socket is found at all, skip straight to offering `ssh-dir` instead, with its read-write
  caveat printed (private key bytes become visible inside the container).
- **Container home path**: prompted once (`util.prompt_text`, default `/home/vscode` — matches
  `.devcontainer/devcontainer.json`'s `mcr.microsoft.com/devcontainers/base:ubuntu-24.04` image's
  default `remoteUser`), used to render every non-identical-path target.
- **Interaction shape**: mirrors `tasks/identity.py`'s per-item loop
  (`[label for label in _HOST_LABELS if ui.ask(...)]`) — one `ui.ask`/`util.confirm` per
  _discovered_ candidate (nothing prompted for candidates that don't exist on this host at all),
  each defaulting per the table above.
- **Output**: prints (never writes) a ready-to-paste JSON fragment — a `"mounts": [...]` array plus
  a `"remoteEnv": {...}` block if `ssh-agent` was selected — for the user to merge into whichever
  `devcontainer.json` they're using. Printing rather than writing matches `print_exclude_tags`'s
  existing "machine/human-readable, caller decides what to do with it" shape, and specifically
  avoids ever auto-editing the **shared, committed, CI-smoke-tested** `.devcontainer/devcontainer.json`
  with one developer's personal host paths.

**Pure, testable helpers** (per this repo's testing convention — `tests/README.md`, mirrored by
`tests/test_wsl.py`'s split of pure helpers from the `@task` shell): extract
`_discover_candidates(home: Path, identity_toml: Path | None, ssh_auth_sock: str | None) -> list[...]`
and `_render_mounts_json(selected, container_home: str) -> str` as plain functions with no direct
I/O beyond what's passed in, so `tests/test_devcontainer.py` (new) can cover discovery-given-a-
`tmp_path`-fixture and JSON rendering without touching the real `$HOME`. The `@task`-decorated
`mounts()` itself (the interactive loop) stays untested by unit tests, same as `wsl.check`.

### 2. `docs/dev-container.md` — new `### Mounting host directories` subsection

Placed under `## Recommended: devcontainer.json + postCreateCommand` (mounts are a
`devcontainer.json`-authoring concern, specific to that path — not meaningful for the
`docker/Dockerfile` bake-time path), right after the existing "Constraint: apt-based images only"
paragraph, before `## Tags to exclude`. Matches the doc's existing dense, "verified by actually
testing X" tone — content:

- **Why**: avoids re-running `inv identity.init`/regenerating SSH keys/re-trusting a corporate CA
  bundle on every fresh container.
- **`inv devcontainer.mounts`**: what it does, that it runs on the _host_ before container creation
  (not `postCreateCommand` — explain the lifecycle-timing constraint explicitly, since nothing in
  the repo states it today and it's the reason this can't just be folded into
  `bootstrap-devcontainer.sh`), and that it prints a snippet rather than editing anything.
- **SSH**: agent-forwarding-first explanation, the WSL2/Docker-Desktop caveat with the concrete
  fix (run `ssh-agent` inside WSL2 itself), and the direct-mount fallback with its security note.
- **The corporate cert bundle same-path-mount note** (why target == source specifically for this
  one candidate).
- **"Code directories" clarification** (the corrected scope from Context above): the current repo
  is already the workspace folder, mounted automatically — nothing to configure. One short example
  for the rare sibling-repo case: a single extra `mounts` entry, by hand, not automated.
- **Security note**: mounted credentials are visible to anything that runs inside the container
  (any dependency, any installed tool) — this is why most candidates default to `readonly` and why
  low-value/high-sensitivity ones (`aws`, `kube`, `gcloud-config`, `gh-config`, `gnupg`) default to
  not-offered/opt-in rather than pre-selected.

## Files to create/edit

- **Edit `tasks/devcontainer.py`**: add the candidate catalog, `_discover_candidates`,
  `_render_mounts_json`, and the `mounts` task. Reuse `util.confirm`/`ui.ask`/`util.prompt_text`,
  `util.is_wsl`, `util.is_docker_desktop_wsl_integration`, `util.PULSE_CONFIG_DIR`,
  `util.IDENTITY_PATH`.
- **New `tests/test_devcontainer.py`**: unit tests for `_discover_candidates`/`_render_mounts_json`
  against a `tmp_path`-based fake `$HOME`, mirroring `tests/test_wsl.py`'s shape.
- **Edit `docs/dev-container.md`**: new `### Mounting host directories` subsection as designed
  above.

## Verification

- `inv quality.fix` — lint/format/tests clean, including the new `tests/test_devcontainer.py`.
- `pytest tests/test_devcontainer.py -v` — discovery logic behaves correctly given a fabricated
  `tmp_path` `$HOME` with various subsets of `.ssh`/`.gitconfig`/`.aws`/etc. present or absent, and
  with/without a fake `identity.toml` + `[certs] bundle`.
- `inv devcontainer.mounts` run for real on this machine (has a real `~/.ssh`, `~/.gitconfig`,
  `~/.config/pulse`) — confirm the interactive prompts only appear for candidates that actually
  exist here, confirm the printed JSON is well-formed (`json.loads()` the `mounts` array out of the
  printed output to check it parses), and confirm the corporate-cert-bundle candidate is
  offered/skipped correctly based on whether `identity.toml` actually has `[certs] bundle` set.
- End-to-end: take the printed snippet, paste it into a throwaway copy of
  `.devcontainer/devcontainer.json`, and confirm via
  `devcontainer up` + `devcontainer exec -- ls -la ~/.ssh ~/.config/pulse` (or equivalent for
  whichever candidates were selected) that the mounted paths are actually visible and correctly
  populated inside the container — not just that `docker create` accepted the config.

## Migrated to

- [`docs/dev-container.md`](../docs/dev-container.md)'s "Mounting host directories" subsection
  already carries this plan's design rationale in place (the candidate catalog's defaults, the
  same-absolute-path corporate-cert-bundle reasoning, the SSH-agent-forwarding-first choice and its
  WSL2/Docker Desktop caveat) — no separate `contributing/*.md` needed.
- `tasks/devcontainer.py` and `tests/test_devcontainer.py` are self-documenting for the pure-helper
  split; the end-to-end `@devcontainers/cli` verification result is already recorded in `AGENTS.md`.
- This file is deleted in the same change that fixes the one dangling reference to it
  (`AGENTS.md`).
