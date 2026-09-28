---
status: landed
updated: 2026-09-29
---

# `deb-github`'s "latest release" lookup is an unauthenticated API call, and CI shares its quota

## Context

The first dispatch of the new weekly `stable` promotion (run 36489105752, 2026-09-29) failed in the
devcontainer `smoke-test`. `inv setup` inside the container ended with:

```text
[hyperfine] WARNING: could not fetch latest release — skipping
[dive] WARNING: could not fetch latest release — skipping
[apt.install-debs] 2 package(s) could not be installed — everything else was:
```

Both packages were already in `setup.toml` when the 2026-09-08 run passed, so this is not a
regression in them.

`apt._resolve_version` (`tasks/apt.py`) resolves an unpinned `deb-github` package with
`curl -fsSL https://api.github.com/repos/<repo>/releases/latest`. That is an **unauthenticated**
REST call, limited to 60 requests an hour per source IP. GitHub-hosted runners share their egress
IPs, so the quota is partly spent by strangers. So is a corporate NAT.

Rate limiting as the cause was inferred, never observed. `hide=True` swallowed curl's stderr, and
the re-run of the failed job passed with the same code on the same commit, which fits a transient
quota problem without proving it. It is deliberately left unproven: the fix below removes the API
from the path whatever the cause was, and the warning now prints curl's error, so a recurrence
explains itself.

Why it matters more now: the promotion job runs weekly and unattended, so an intermittent 403 in any
of the unpinned `deb-github` packages silently skips that week's promotion. Real installs can hit it
too: a fresh machine behind a shared IP skips the package and the run fails at the end.

## Decision

[DECISION: **read the tag off the `/releases/latest` redirect, and do not send a token to the API.**
User's choice, 2026-09-29, after a grep of the research-library clones. GitHub's own
`actions/runner-images` build scripts do this, with `--retry`, and so do the mergify, d2 and
rulesync installers. Mergify's comment states this exact failure: the API "403s on shared CI runner
IPs; the plain github.com redirect has no such limit." The token alternative fixes CI only, needs
the workflow token plumbed through `devcontainers/ci` into the container, and does nothing for a
real install behind a NAT.]

[PITFALL: **a repo with no releases is a 200, not an error.** `/releases/latest` then redirects to
`/releases`, so curl succeeds and the final URL has no `/tag/`. The parser requires that segment,
otherwise the whole URL would flow into the asset name. Mergify's installer guards the same case.]

## What landed

`535d821`: `apt._tag_from_release_url` and the rewritten `_resolve_version`, plus tests in
`tests/unit/test_apt.py`. They cover the tag shapes (`v`-prefixed, bare, URL-encoded), the
no-releases redirect, a curl failure whose stderr reaches the warning, and a command that never
names `api.github.com`. Checked live against `sharkdp/hyperfine` (resolves `1.20.0`), a repo with no
releases, and a missing repo (the warning shows curl's 404).

## Migrated to

- The rationale and the no-releases pitfall are in `_resolve_version`'s and
  `_tag_from_release_url`'s docstrings in `tasks/apt.py`, which is where anyone changing the lookup
  will read them.
- The incident itself is recorded in `2026-09-29-stable-tag-release-model.md`'s "Still open"
  section, as the first promotion's failed attempt.
- Not migrated: the survey of which installers use the API and which use the redirect. It is
  reproducible with one `rg 'url_effective|releases/latest'` over `$RESEARCH_HOME/repos`.
