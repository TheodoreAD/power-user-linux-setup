---
status: in-progress
updated: 2026-09-05
repo: git@github.com:TheodoreAD/power-user-linux-setup.git
---

# Nothing on this machine puts registry or index credentials in the OS secret store

## Context

Filed from a `repo-tasks` session, 2026-08-30, where the rule was stated:

> Everything that needs a password goes through the OS secret store, via whatever native integration
> the tool already has. `keyring` is expected to be on the command line already and is never
> installed into an application or library — it is the fallback for a tool with no native path.

And, on the machine's own responsibility:

> pulse needs to make sure all the stores are well integrated at install time, by default, so the
> users don't get a broken, hard to understand auth issue.

The mechanism is half in place and entirely unused. `[packages.python-keyring]` is declared and
`keyring` resolves to `~/.local/bin/keyring`. Every consumer of it is missing.

**This version supersedes the one filed earlier the same day**, which was written before reading the
tools' source and got helm wrong. The findings below are from source, not documentation: clones are
in `$RESEARCH_HOME/repos/` (`github.com--docker--cli`, `github.com--helm--helm`,
`github.com--oras-project--oras-go` at the `v2.6.2` tag helm pins, `github.com--astral-sh--uv`).

## Measured state, 2026-08-30

- `~/.docker/config.json` has **no `credsStore` and no `credHelpers`**, and holds one credential as
  a base64 `auth` entry. Base64 is encoding, not encryption.
- **No `docker-credential-*` helper is installed** anywhere on `PATH`, and neither is `pass`.
- **No uv keyring configuration exists**, so uv never consults keyring for an index or a publish.
- helm is 4.2.4, docker 29.7.2, uv 0.11.19.
- **`gh` is the exception, and already compliant.** `gh auth status` reports
  `Logged in to github.com account TheodoreAD (keyring)` — its token is in the OS secret store, not
  in `~/.config/gh/hosts.yml`. Nothing to do for it, and it is the fourth auth consumer on this
  machine rather than a fifth thing to fix.

That last one is worth more than a tick in a checklist: **it is live proof that the Secret Service
on this machine is present, unlocked and answering**, because `gh` is reading a token out of it
today. The failure this plan's round-trip verification exists to catch — helper installed, keyring
locked or absent, every push failing as though the credentials were wrong — is therefore unlikely
_here_, though the check stays because it is about the machine's state at install time rather than
about this machine on this day, and because a `docker-credential-*` helper talks to the same service
through a different client.

## The finding that decides the design

Docker and oras both auto-detect a credential helper, and both gate detection on the config file
having no authentication in it yet:

```go
// docker/cli, cli/config/config.go:173
if !configFile.ContainsAuth() {
    configFile.CredentialsStore = credentials.DetectDefaultStore(configFile.CredentialsStore)
}
```

`ContainsAuth()` is `credsStore != "" || len(credHelpers) > 0 || len(auths) > 0`. oras'
`IsAuthConfigured()` counts the same three.

[PITFALL: **the existing plaintext entry is what suppresses the secure default.** Not merely "that
one credential stays insecure" — its presence stops detection running at all, so installing the
helper changes nothing on any machine that has ever logged in. That is precisely this machine, and
it is why `credsStore` is written explicitly rather than left to detection: an explicit value is
consulted before the detected one and does not depend on what else the file contains.]

[PITFALL: docker checks the helper binary exists before selecting it
(`exec.LookPath("docker-credential-" + name)`) and degrades to plaintext when it does not. **oras
does not.** `getPlatformDefaultHelperSuffix` returns `"secretservice"` unconditionally when `pass`
is absent, and `getStore` returns `NewNativeStore(helper)` with no existence check and no fallback —
so on a machine with no helper and a fresh helm config, `helm registry login` picks a store that
fails when it execs. A half-finished install is worse than none, which is the whole reason the
verification below is a hard failure rather than a warning.]

## The three consumers

### 1. docker — a helper binary plus an explicit `credsStore`

`credsStore`'s value is the suffix of a `docker-credential-*` binary; `secretservice` is the Secret
Service one. With it set, `docker login` stores through the helper and every later docker command
reads back through it.

~~Which install method?~~ **Upstream's release binary, decided with the user 2026-09-05.** Noble is
still on `golang-docker-credential-helpers` 0.6.4 (`0.6.4+ds1-1ubuntu0.24.04.3`, re-checked the same
day) against an upstream `v0.9.9` that shipped 2026-08-26 — three minor versions and years apart,
which is too far to wave through for the one component `oras` fails hard on rather than degrading
from. No PyPI wrapper exists (checked directly: `docker-credential-helpers`,
`docker-credential-secretservice`, `dockercredentialhelpers` all 404), so the `uv-tool` route the
rule prefers was not available and `binary` is the next mechanism down.

It is a declared `[packages.docker-credential-secretservice]` entry, not a one-off install. The one
cost paid for it: the `binary` method only accepted a static `url`, and upstream names the version
in the asset filename, so a static URL would freeze at 0.9.9 forever — on a method that skips when
the command exists and would therefore never revisit it. `{version}` + `version_cmd` now works there
the way it already did for `archive` and `deb-url`.

### 2. helm — nothing to install, and one host-scoped caveat

helm resolves credentials through the same oras store, so a `credsStore` in its own registry config
works identically. It also **falls back to reading `~/.docker/config.json`**, keyed by registry
host, so `docker login <host>` already covers a chart registry on that same host. A chart registry
on a different host needs its own login; the lookup is per-host and nothing bridges two hosts.

So helm needs no package. What it needs is for its own config not to be in the suppressed state
described above — either absent, or carrying an explicit `credsStore`.

### 3. uv / PyPI — configuration only, and placement is load-bearing

uv supports keyring in **subprocess mode**, which is exactly the "call the `keyring` CLI" shape the
rule asks for. Config resolution is user (`~/.config/uv/uv.toml`) → system → project (`uv.toml`
preferred over `pyproject.toml`'s `[tool.uv]`, walking up), so a per-machine default is a
first-class option rather than a workaround.

[PITFALL: **`keyring-provider` must go in the per-user file and nowhere else.** From uv's
`uv-publish/src/lib.rs:421`, with `trusted-publishing = "automatic"` a non-disabled keyring provider
makes `uv publish` **skip Trusted Publishing entirely** (`TrustedPublishResult::Skipped`); with
`"always"` it is a hard `MixedCredentials` error. So the same setting that secures a developer's
machine breaks OIDC publishing the moment it lands in a committed file, where CI reads it — and CI
has no keyring to fall back to. User-level placement keeps both correct at once.]

[PITFALL: uv consults keyring only when a username is available, and otherwise logs "Skipping
keyring fetch ... use `authenticate = always` to force". The lookup tries the full URL, then
`host:port`, then `scheme://host` for non-HTTPS. Without a username **and** without
`authenticate = "always"` on the index, the configuration is inert while appearing applied. For PyPI
the username is the literal `__token__`;
`uv publish --keyring-provider=subprocess
--username=__token__` is the working invocation, and
`--token` cannot be combined with it.]

## Install-time integration — the actual deliverable

The rule is "no broken, hard-to-understand auth issue by default", which means the install either
completes all of this or fails saying so:

1. `[packages.*]` entry for the docker credential helper, once the version question is settled.
2. Write `"credsStore": "secretservice"` into `~/.docker/config.json`, **preserving every other
   key** — it holds real auth entries and unrelated settings.
3. Same for helm's registry config, or leave it absent. An existing plaintext entry there suppresses
   detection exactly as docker's does.
4. `~/.config/uv/uv.toml` with `keyring-provider = "subprocess"`.
5. **Verify by round-trip, and fail loudly** — decided 2026-08-30. Store a throwaway credential
   through `docker-credential-secretservice`, read it back, delete it. A `which` check passes on
   exactly the machine where the confusing failure happens: helper installed, Secret Service locked
   or absent, every push failing as though the credentials were wrong.

~~What should a headless or CI-like machine do at step 5?~~ **Answered 2026-09-05, and it needed
neither a profile nor a flag.** The condition to detect is whether the helper is installed, and that
already follows the tag system: the package is `workstation`-tagged, so a headless or container
machine simply has none, and the task says "credentials stay in `~/.docker/config.json`" and
returns. Failing loudly is reserved for the case that actually warrants it — the helper is present
and the store does not answer, which is the confusing failure the round trip exists to catch. Silent
degradation happens in neither branch, which was the requirement.

## Migrating the credential that is already there

Deliberate, and to be done with the user present — it needs that registry's credentials to hand:

1. Install the helper and set `credsStore` (steps 1–2 above).
2. `docker login <that registry>` to re-store it through the helper.
3. **Delete the `auths` entry from `~/.docker/config.json`.** Setting `credsStore` does not migrate
   it: docker keeps reading the plaintext entry and it keeps working, which is the quiet failure.
4. Confirm the entry is gone and the credential still resolves.

[PITFALL: the registry in question is work infrastructure. Its hostname is not to be written into
this plan, a commit message, or any other file in a repo that is or may become public — the store's
`scan --mode staged` is the mechanical check, and this plan deliberately refers to it only by
shape.]

## Landed 2026-09-05: item 1, the whole security change

`docker-credential-secretservice` v0.9.9 installed through the declared package; `credsStore`
written explicitly into `~/.docker/config.json` with `HttpHeaders` and the existing `auths` entry
preserved and the file still `0600`; the round trip run first and hard-failing before anything is
written. `inv docker.configure-credential-store`, wired into `inv setup`'s packages phase after
`tools.install` — it has to be after, because `tools.install` is what puts the helper on `PATH`.

The round trip was proven against the live Secret Service by hand before the task existed (`store` →
`get` → `erase`, secret compared) and the task's own branches are unit-tested with the config
redirected under `tmp_path`: the merge keeps every other key, a new file is created `0600`, and a
store that answers with a _different_ secret is treated exactly like one that refuses — which is the
failure a `which` check cannot see.

The claim is registered in `inv home.list-claims` as a `merge`/`co-owned` writer on one key. Only
the key is claimed; the rest of the document is docker's, and holds real credentials.

## Recommended direction

In dependency order, because the first item unblocks everything else.

1. ~~**The helper package and the explicit `credsStore`**, plus the round-trip verification~~ —
   landed 2026-09-05, see above.
2. **`uv.toml` at user level.** Independent of the other two and the cheapest — it changes nothing
   until a URL carries a username, so it is safe to land first if convenient. **Still open**, and
   the `[PITFALL:]` above about per-user placement is the thing not to get wrong.
3. **The migration**, with the user. **Still open** — one plaintext `auths` entry remains, reported
   by the task on every run and deliberately never deleted by it.
4. ~~**Then unblock `repo-tasks`' verification**~~ — unblocked; filed there as
   `2026-09-05-credential-helper-installed-logins-verifiable.md`, which carries the machine state
   its check needs and the warning that the un-migrated host would measure the wrong path —
   `plans/2026-08-30-registry-credentials-in-the-os-store.md` cannot prove its login tasks do
   anything secure until a helper exists, and its check is deliberately designed to run helm against
   a host that is _not_ an image registry, so the docker fallback cannot mask a helm-side failure.

CI is explicitly out of scope here and belongs to no machine: no keyring, no netrc, no credential
file on a runner. `repo-tasks`' `plans/2026-08-30-ci-secrets-for-non-oidc-registries.md` owns it.
