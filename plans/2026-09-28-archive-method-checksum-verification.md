---
status: idea
updated: 2026-09-28
---

# Verify a published checksum in the archive method

## Context

`setup.toml`'s `archive` method (`tasks/tools.py`) downloads a GitHub release tarball and extracts
it with no integrity check; no package entry carries a checksum field. Most of the projects it
installs from publish one beside the tarball — `gog` and `gmailctl` (added 2026-09-28) both ship
`checksums.txt`, and gog also a `SIGNING-MANIFEST.json`. `package_health.py github <owner/repo>`
already lists a release's checksum and signature files, so the data is easy to find.

Raised by the now-retired `2026-09-27-install-gog-and-gmailctl.md` and deliberately kept out of it:
it changes every archive package, not two.

## Open questions

[NEEDS CLARIFICATION: an optional `checksum_url` (with `{version}`), verified against the downloaded
file's line in it, or something stronger? A checksum fetched from the same release defends against a
corrupted or truncated download, not a compromised release. Signature verification (cosign,
minisign, gog's manifest) is the stronger form and differs per project.]

[NEEDS CLARIFICATION: what a mismatch does — abort the package, or abort the whole run, matching
`inv verify.all`'s first-failure-aborts stance?]

## Recommended direction

Optional `checksum_url` on `archive` (and `deb-github`, same shape), read as the common
`<sha256>  <filename>` format, failing the package on a mismatch or a missing line. Backfill it on
every existing entry whose release publishes one, found with `package_health.py github`.
