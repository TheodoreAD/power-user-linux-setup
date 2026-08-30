---
status: idea
updated: 2026-08-30
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

[NEEDS CLARIFICATION: which install method. Ubuntu noble ships `golang-docker-credential-helpers`
**0.6.4** (`apt-cache policy`, checked 2026-08-30) against upstream's 0.9.x line — years behind,
which `~/AGENTS.md`'s "judge from its own release cadence" rule says to weigh rather than wave
through. In its favour: a distro package with a security pocket, and `secretservice` is a thin shim
over libsecret whose surface barely moves. The alternative is an upstream release binary, which is
the one-off manual install that same rule forbids without a `setup.toml` entry.]

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

[NEEDS CLARIFICATION: what a headless or CI-like machine should do at step 5. Failing loudly is
right for this workstation and wrong for a machine with no Secret Service at all, where the honest
outcome is "credentials stay in a file, and you were told". Whether that is a separate profile, a
detected condition, or an explicit opt-out flag is undecided — but silently degrading is not an
option, because that is the state this plan exists to end.]

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

## Recommended direction

In dependency order, because the first item unblocks everything else.

1. **The helper package and the explicit `credsStore`**, plus the round-trip verification. This is
   the whole security change; the rest is configuration.
2. **`uv.toml` at user level.** Independent of the other two and the cheapest — it changes nothing
   until a URL carries a username, so it is safe to land first if convenient.
3. **The migration**, with the user.
4. **Then unblock `repo-tasks`' verification** —
   `plans/2026-08-30-registry-credentials-in-the-os-store.md` cannot prove its login tasks do
   anything secure until a helper exists, and its check is deliberately designed to run helm against
   a host that is _not_ an image registry, so the docker fallback cannot mask a helm-side failure.

CI is explicitly out of scope here and belongs to no machine: no keyring, no netrc, no credential
file on a runner. `repo-tasks`' `plans/2026-08-30-ci-secrets-for-non-oidc-registries.md` owns it.
