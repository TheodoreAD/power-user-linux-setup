---
status: idea
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

[UNVERIFIED: **rate limiting is the cause.** It is inferred, not observed. `hide=True` swallows
curl's stderr, so the 403 body, if that is what came back, is not in the log. The re-run of the
failed job is the first evidence either way. Seeing the cause at all first needs the warning to say
what failed.]

Why it matters more now: the promotion job runs weekly and unattended, so an intermittent 403 in any
of the unpinned `deb-github` packages silently skips that week's promotion. Real installs can hit it
too: a fresh machine behind a shared IP skips the package and the run fails at the end.

## Open questions

[NEEDS CLARIFICATION: **Which fix, or both?**

(a) Resolve "latest" without the API. `https://github.com/<repo>/releases/latest` redirects to
`/releases/tag/<tag>`, and `curl -fsSLI -o /dev/null -w '%{url_effective}'` reads the tag from the
final URL. That is a web endpoint, not the REST API's 60-an-hour budget, and it needs no token
anywhere. Check how the research-library clones of other installers (mise, uv, zimfw) resolve
"latest" before settling on it.

(b) Send `Authorization: Bearer $GITHUB_TOKEN` (or `GH_TOKEN`) when one is set, and pass the
workflow token into the devcontainer build. That fixes CI only, and needs the token plumbed through
`devcontainers/ci` into the container environment.]

Either way, the warning should print curl's error, so a 403 reads as a rate limit rather than as
"could not fetch".

## Recommended direction

(a), plus the better warning. It fixes CI and real installs at once, and puts no token into the
container build.
