# Registry and index credentials in the OS secret store

The rule this implements, and it is a household rule rather than this repo's invention:

> Everything that needs a password goes through the OS secret store, via whatever native integration
> the tool already has. `keyring` is expected to be on the command line already and is never
> installed into an application or library — it is the fallback for a tool with no native path.

And, on this repo's own responsibility for it:

> pulse needs to make sure all the stores are well integrated at install time, by default, so the
> users don't get a broken, hard to understand auth issue.

That second half is why there is a task at all rather than a documentation page telling somebody to
run `docker login` differently. **Most of the reasoning lives with the code it explains** —
`tasks/docker.py`'s `configure_credential_store` and its three helpers carry the
explicit-`credsStore` design, the round-trip verification, the purge semantics and the `docker/cli`
source reads; `config/uv.toml`'s own comments carry the per-user-placement rule and the inertness
caveat. This page holds what has no such home: the survey those decisions were made from, the
consumer that turned out to need nothing, and two mistakes worth not repeating.

## The four auth consumers on this machine, as found 2026-08-30

Findings are from the tools' source, not their documentation — an earlier version of this survey was
written from docs and got helm wrong. The clones are in `$RESEARCH_HOME/repos/`
(`github.com--docker--cli`, `github.com--helm--helm`, `github.com--oras-project--oras-go` at the
`v2.6.2` tag helm pins, `github.com--astral-sh--uv`).

| consumer      | state when surveyed                                                         | what it needed                               |
| ------------- | --------------------------------------------------------------------------- | -------------------------------------------- |
| **docker**    | no `credsStore`, no `credHelpers`, one credential as a base64 `auth` entry  | a helper binary and an explicit `credsStore` |
| **helm**      | resolves through the same oras store                                        | **nothing to install** — see below           |
| **uv / PyPI** | no keyring configuration at all, so keyring never consulted                 | one per-user config file                     |
| **`gh`**      | already compliant — token in the secret store, not `~/.config/gh/hosts.yml` | nothing                                      |

Base64 is encoding, not encryption, so the one docker entry was plaintext in every sense that
matters. No `docker-credential-*` helper was installed anywhere on `PATH`, and neither was `pass`.

**`gh` being already compliant is worth more than a tick in a checklist.** It is live proof that the
Secret Service on this machine is present, unlocked and answering, because `gh` reads a token out of
it daily — which makes `gh auth status` reporting `(keyring)` a quick independent check when the
credential round trip fails, and that is exactly what the task's error message points at. It does
not make the round trip redundant: the check is about the machine's state at install time rather
than about this machine on this day, and a `docker-credential-*` helper reaches the same service
through a different client.

## helm needs no package, and the reason is a host-scoped fallback

helm resolves credentials through the same oras store, so a `credsStore` in its own registry config
works identically to docker's. It also **falls back to reading `~/.docker/config.json`**, keyed by
registry host — so `docker login <host>` already covers a chart registry on that same host, and that
is the common case here.

The caveat is that the lookup is per-host and nothing bridges two hosts: **a chart registry on a
different host from any image registry you have logged into needs its own `helm registry login`.**
What helm needs from this repo is therefore not a package but the absence of a broken state — its
own config either absent, or carrying an explicit `credsStore`.

## Why the helper is upstream's binary rather than the distro's

Decided with the user 2026-09-05. Noble ships `golang-docker-credential-helpers` 0.6.4
(`0.6.4+ds1-1ubuntu0.24.04.3`) against an upstream `v0.9.9` from 2026-08-26 — three minor versions
and years apart. That gap is too wide to wave through for the one component that **fails hard rather
than degrading**: docker checks the helper binary exists before selecting it
(`exec.LookPath("docker-credential-" + name)`) and falls back to plaintext, but oras does not —
`getPlatformDefaultHelperSuffix` returns `"secretservice"` unconditionally when `pass` is absent and
`getStore` returns a native store with no existence check and no fallback, so a stale or missing
helper is a `helm registry login` that dies when it execs.

No PyPI wrapper exists (`docker-credential-helpers`, `docker-credential-secretservice` and
`dockercredentialhelpers` all 404 on PyPI), so the `uv-tool` route `~/AGENTS.md` prefers was not
available and `binary` was the next mechanism down. It is a declared
`[packages.docker-credential-secretservice]` entry like anything else — the one cost paid for it was
teaching the `binary` method `{version}` + `version_cmd`, which `archive` and `deb-url` already had.
Upstream names the version in the asset filename, and `binary` skips when the command already
exists, so a static URL would have frozen at 0.9.9 forever with nothing ever revisiting it.

## Two mistakes worth not repeating

[PITFALL: **an existing plaintext entry is what suppresses the secure default, so "install the
helper" fixes nothing on a machine anyone has used.** Docker and oras both auto-detect a credential
helper and both gate detection on the config having no authentication in it yet — `ContainsAuth()`
is `credsStore != "" || len(credHelpers) > 0 || len(auths) > 0`, and oras' `IsAuthConfigured()`
counts the same three. So the single legacy `auths` entry stopped detection running at all. This is
the finding the whole design turns on: `credsStore` is written **explicitly** rather than left to
detection, because an explicit value is consulted first and does not depend on what else the file
contains.]

[PITFALL: **a justification that invokes the tool's own behaviour still has to be checked against
the tool.** The purge's first version kept the emptied `auths` entry, on the claim that
`{"<host>": {}}` is "what `docker logout` leaves under a `credsStore`". Read from `docker/cli`
afterwards, it is neither half of that: `nativeStore.Erase` erases from the helper and delegates to
`fileStore.Erase`, which is a `delete()` on the map — a logout **removes** the entry — while
`nativeStore.Store` is what produces a secretless entry, blanking the credential fields and keeping
the email, so such an entry means a live helper-backed **login**, the opposite state.

What makes it worth recording is that the reasoning read as careful. It appealed to docker's real
behaviour rather than inventing a rule, which is the right instinct, and the clone was in
`$RESEARCH_HOME` the whole time. The wrong claim reached a docstring, a test name, a commit message
and two plans before anything checked it, and only the user asking for the entry to go as well
prompted the two source reads that settled it.]

## Not covered here

**CI belongs to no machine** — no keyring, no netrc, no credential file on a runner — and is
`repo-tasks`' `plans/2026-08-30-ci-secrets-for-non-oidc-registries.md`. The uv side's own trap, that
a `keyring-provider` reaching a committed project file makes `uv publish` skip Trusted Publishing
entirely, is in `config/uv.toml`'s comments where anyone editing that file will meet it.
