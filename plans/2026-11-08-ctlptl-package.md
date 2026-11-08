---
status: landed
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

[DECISION: `tags = ["k8s", "dev"]`, as kind and tilt carry. Neither tag gates anything — only the
seven named in AGENTS.md do — so this groups the entry with its stack and changes no install.]

## Recommended direction

Add `[packages.ctlptl]` with `method = "archive"`, modelled directly on `[packages.tilt]`: the asset
naming is the same scheme (`<tool>.{version}.linux.x86_64.tar.gz`), so `version_cmd` and
`download_url` copy over with the repo name changed. `check_cmd = "ctlptl"`; add
`zshrc = "source <(ctlptl completion zsh)"` if ctlptl ships completion like kind does.

[DECISION: the layout matches tilt's, checked 2026-11-08 against v0.9.6: `ctlptl`, `LICENSE` and
`README.md` at the archive root, so `bin_pick` + `bin_in_root` as for tilt, and the tarball's sha256
matches its line in `checksums.txt`. Two differences from tilt: no `--version` flag (the root
command sets no `Version`), so `verify_cmd = "ctlptl version"`; and cobra 1.10's default
`completion` command is there, so the zshrc line works.]

## Opting out of usage analytics

Merged in from `plans/2026-11-08-ctlptl-analytics-opt-out.md` (now deleted;
`plans.py archive --file` reads it back), filed from the `hekate` session
`5f84bc91-7291-42b4-9474-846d42d45b23.jsonl` at 2026-11-08T15:45:38Z, while answering whether a
Windows/WSL machine could join hekate's kind cluster. Its `source_plan` is
`github.com-personal/hekate/2026-11-08-hekate-tilt-kind-monorepo.md` in the plans store.

ctlptl's README says it "sends anonymized usage statistics, so we can improve it on every platform.
Opt out with `ctlptl analytics opt out`." The client is `tilt-dev/wmclient`'s remote analytics,
wired up in `pkg/cmd/analytics.go`. Read from a clone of `tilt-dev/ctlptl` at `main@9a9f7b1`, in the
research library, 2026-11-08. Per the home rule that a feature phoning home by default is a decision
rather than a default, the install should pin it off deliberately. The user chose "File the opt-out
(Recommended)" when asked whether the ctlptl package entry should also run
`ctlptl analytics opt out`.

[PITFALL: **the README is wrong about the code it ships, and Tilt is the one that reports.** Read
2026-11-08 from `tilt-dev/wmclient` at `1839d03`, the version both ctlptl and Tilt pin:
`NewRemoteAnalytics` sets `enabled` from `optedIn()`, which is true only for an `opt-in` choice, and
ctlptl passes no `WithEnabled`, so it sends nothing by default. Tilt passes `WithEnabled(true)` and
stops only on `opt-out` or an environment variable, so Tilt sends by default. Running
`ctlptl analytics opt out` at install time would have changed nothing.]

[DECISION: **the opt-out state is one file, and it is seeded rather than run.** wmclient keeps the
choice in `~/.tilt-dev/analytics/user/choice.txt` (`~/.windmill` if that exists, `TILT_DEV_DIR` over
both), outside the install, so an upgrade never resets it and one write is enough; a fresh home
directory needs it written again, which a `config_files` seed does at install. It sits on
`[packages.tilt]`, the tool that actually sends, and covers ctlptl because the file is shared. The
read-back the direction asked for is narrower than asked: `verify.all` fails when the file is
missing, but a seeded file changed afterwards is the user's by the `config_files` contract, so a
switch to `opt-in` passes. `tilt analytics` printed `opt-out` once it was written. Chosen by the
user 2026-11-08 over exporting `DO_NOT_TRACK`, which is now its own plan.]

[DECISION: **tilt had the gap**, and it is closed by the same file. What Tilt sends, and the limit
that a Tiltfile's `analytics_settings(True)` outranks the file, are in `docs/kubernetes.md` and
`plans/2026-11-08-do-not-track.md`.]

## Verification

The original repro was `which kind tilt kubectl ctlptl podman` printing `ctlptl not found`, in the
agent-skills session named above, on this machine. After `inv tools.install` on 2026-11-08:
`ctlptl version` prints `v0.9.6, built 2026-09-10`, the download's sha256 matched `checksums.txt`,
and `tilt analytics` prints `analytics status : opt-out`.

## Migrated to

- **The package**: `[packages.ctlptl]` in `setup.toml`, commit `7558b5d`. Its inline comments carry
  the archive layout and the missing `--version` flag.
- **The opt-out**: `[packages.tilt]`'s `config_files` and the comment above it, commit `90e769e`.
- **Usage docs**: `docs/kubernetes.md`, the Tilt and ctlptl sections — what Tilt sends, what
  outranks the choice file, and that ctlptl sends nothing unless opted in.
- **The open question it raised**: `plans/2026-11-08-do-not-track.md`, which keeps the full research
  on Tilt's reporting, the Tiltfile override and the `~/.windmill` fallback.

Deliberately not migrated: the `package_health.py` figures (release cadence, committers, bus
factor). They were the adoption judgement on 2026-11-08 and go stale; the command re-derives them.
