---
status: landed
updated: 2026-08-08
---

# Dev container pipeline (no custom base image)

## Context

PULSE already documents a way to build a _custom Docker image_ from `setup.toml`
(`docs/dev-container.md`), but that forces every consumer onto one image and one set of
package choices baked at build time — the user explicitly doesn't want that (security
surface of a maintained image, and other people shouldn't be forced onto the same base
image as this machine). What's missing is a distribution path that layers PULSE's curated
CLI tooling onto _whatever_ base image a consumer already uses, expressed as plain
`devcontainer.json`, plus a pipeline that keeps that recipe correct as `setup.toml` and
`tasks/*.py` evolve.

Chosen distribution model (per user decision): a **live git reference**, not a published
OCI Feature. A consumer's `devcontainer.json` runs a `postCreateCommand` that clones this
repo at a pinned ref and runs the normal `inv` tasks with `PULSE_EXCLUDE_TAGS` — same
tasks, same `setup.toml`, no separate artifact to keep in sync, no registry to publish to.
"Up to date" is achieved by pinning to a **`stable` tag that CI only moves forward when a
build/smoke-test passes** — never an unpinned `master`/`HEAD` reference (that would be
running untested, possibly-broken instructions from strangers' `postCreateCommand`s).

**Prerequisite (landed):** `inv setup`/the granular task list this pipeline drives both used to
crash immediately in a plain, non-systemd container — `system.locale`/`system.dns` called
`util.require_systemd()` unconditionally, and plenty of devcontainer base images don't run
systemd. `tasks/setup.py` now detects this (`util.has_systemd()`) and skips the `system`/
`desktop` phases automatically instead of raising; see `tasks/util.py`'s `has_systemd()` and
`docs/dev-container.md`. `bootstrap-devcontainer.sh` below can call `inv setup` (or the
granular task list) without hitting that crash.

## Design

### 1. `bootstrap-devcontainer.sh` (new, repo root, alongside existing `bootstrap.sh`)

The distributable entrypoint. Consumers `curl` this file directly by pinned URL; this
repo's own `.devcontainer` calls it locally (`--local`, no clone).

Args: `--exclude-tags <tags>` (default = the constant from `tasks/devcontainer.py`,
below), `--ref <git-ref>` (default `stable`), `--local` (skip cloning; assume already
inside a checkout — used by this repo's own `.devcontainer/devcontainer.json`).

Behavior:

- If not `--local`: shallow `git clone --branch <ref> --depth 1` this repo into
  `~/.local/share/pulse-devcontainer-src` (matches the existing XDG-under-`~/.local/share`
  convention used everywhere else in this repo), `cd` there.
- Run the existing `./bootstrap.sh` (already does uv + invoke install — reused as-is, no
  duplication).
- Run `PULSE_EXCLUDE_TAGS=<tags> inv apt.repos apt.base apt.deb tools.install python.tools node.install zsh.omz-configure zsh.configure`
  — the same task list `docs/dev-container.md`'s existing Dockerfile outline already uses.

### 2. `tasks/devcontainer.py` (new invoke namespace)

Registered in `tasks/__init__.py`'s `Collection` list next to `wsl`, `docs`, etc.

- `CONTAINER_EXCLUDE_TAGS = ["gui", "workstation", "corporate", "ide", "gnome"]` — single
  source of truth for the recommended container tag exclusion, used by both the docs
  generator below and as `bootstrap-devcontainer.sh`'s default (today this list is
  hand-copied prose in `setup.toml`'s header comment, `docs/index.md`, `docs/wsl.md`, and
  `docs/dev-container.md` — this becomes the one place it's declared).
- `inv devcontainer.render-docs` — regenerates a sentinel-wrapped block (reusing
  `util.ensure_block`, the same mechanism `zsh.configure` etc. use for managed regions in
  shared files — see `docs/index.md`'s "Configuration management" section) inside
  `docs/dev-container.md`, containing the current tag table and the example
  `postCreateCommand` snippet with today's `CONTAINER_EXCLUDE_TAGS`. Running it after a
  `setup.toml`/tag change keeps the doc from silently drifting.
- `inv devcontainer.check` — local dry-run smoke test, same shape as `inv wsl.check`:
  `PULSE_DRY_RUN=1 PULSE_EXCLUDE_TAGS=<constant> inv apt.repos apt.base apt.deb tools.install`
  and report what would happen, read-only.

### 3. `.devcontainer/devcontainer.json` (new, repo root — VS Code's required path)

Dogfoods the setup for this repo itself and doubles as the exact artifact CI smoke-tests:

```json
{
  "name": "power-user-linux-setup",
  "image": "mcr.microsoft.com/devcontainers/base:ubuntu-24.04",
  "postCreateCommand": "bash bootstrap-devcontainer.sh --local --exclude-tags gui,workstation,corporate,ide,gnome"
}
```

### 4. `docs/dev-container.md` rewrite

- New primary section: "Recommended: devcontainer.json + postCreateCommand" — the
  consumer-facing snippet (any Debian/Ubuntu-family `image` of their choice +
  `postCreateCommand` curling `bootstrap-devcontainer.sh` pinned to `stable`). Explains the
  `stable`-tag pin/float tradeoff and states plainly that this only works on
  apt-based (Debian/Ubuntu-family) images — a real constraint, not a bug.
- Existing "custom Docker image" content stays, demoted to an "Alternative: baking a
  custom base image" section (still legitimate for e.g. CI runner images where a
  prebuilt image's startup-time win matters more than the flexibility tradeoff).
- The tag table + example become the generated block from `devcontainer.render-docs`
  (item 2), not hand-maintained prose.

### 5. `.github/workflows/devcontainer.yml` (new — repo has one existing workflow,

`publish_on_push.yml` for docs, to follow as a style reference)

- **Trigger**: push to `master` touching `setup.toml`, `tasks/**`, or
  `bootstrap-devcontainer.sh`/`bootstrap.sh`; plus `workflow_dispatch`.
- **Job `smoke-test`**: matrix over 2–3 reference base images (at minimum
  `mcr.microsoft.com/devcontainers/base:ubuntu-24.04` and plain `ubuntu:24.04`, to also
  catch assumptions about things devcontainers-base preinstalls, e.g. passwordless sudo).
  Uses the official `devcontainers/ci` GitHub Action to actually build/exec against this
  repo's real `.devcontainer/devcontainer.json` — validating the literal artifact
  consumers point their own `postCreateCommand` at, not a hand-rolled substitute. Follow-up
  `exec` step asserts a handful of representative installed binaries exist.
- **Job `publish-stable`** (`needs: smoke-test`, master only): force-moves the `stable` git
  tag to the current commit and pushes it. This is an intentionally _moving_ tag (git's
  equivalent of a `:latest` image tag) — flagging explicitly since it's a force-push to a
  ref other tooling/people may reference, done automatically by CI on every green build.
- **Job `docs`**: runs `inv devcontainer.render-docs`; if it produced a diff, commits it
  back to `master` directly (solo repo, no PR review step needed) via
  `stefanzweifel/git-auto-commit-action` or equivalent.

## Files touched

- New: `bootstrap-devcontainer.sh`, `tasks/devcontainer.py`, `.devcontainer/devcontainer.json`,
  `.github/workflows/devcontainer.yml`
- Edited: `tasks/__init__.py` (register namespace), `docs/dev-container.md` (rewrite +
  generated block), `setup.toml` header comment / `docs/index.md` / `docs/wsl.md` (point at
  `CONTAINER_EXCLUDE_TAGS` instead of repeating the tag list by hand, where they currently do)

## Verification

- Local: `npx @devcontainers/cli build --workspace-folder .` then
  `devcontainer up`/`exec -- inv --list` against this repo's own `.devcontainer` to confirm
  the postCreateCommand path works end-to-end.
- Local: `inv devcontainer.check` (dry run) and `inv devcontainer.render-docs` (confirm the
  generated block matches what's committed, i.e. no drift).
- Consumer path: point a throwaway repo's `devcontainer.json` at a branch-scoped `--ref`
  and open it in VS Code Dev Containers to confirm the curl+clone+`inv` flow works from
  outside this repo, not just self-hosted.
- CI: the `devcontainers/ci`-driven `smoke-test` job is the automated version of the first
  bullet, gating whether `stable` moves.

## Migrated to

- [`docs/dev-container.md`](../docs/dev-container.md) already carries this plan's design rationale
  in place (the devcontainer.json-vs-baked-image tradeoff, the `stable`-tag pin/float reasoning) —
  no separate `contributing/*.md` needed; nothing here wasn't already migrated.
- `.github/workflows/devcontainer.yml` and `tasks/devcontainer.py` are self-documenting for the CI
  job breakdown (each job's own comments/structure carry that record).
- This file is deleted in the same change that fixes the two dangling references to it
  (`docs/dev-container.md`, `AGENTS.md`).
