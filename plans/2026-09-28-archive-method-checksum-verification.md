---
status: landed
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

[DECISION: an optional `checksum_url`, not signatures. Every project signs differently, while nearly
all of them publish a sha256sum-format list. The check catches a corrupt or truncated download, and
the docstring says a compromised release is out of its reach.]

[DECISION: what a failure costs follows each method's existing stance. The archive method raises,
which aborts the phase (first-failure-aborts). `deb-github` reports `FAILED`, skips that package,
removes the file before `dpkg` sees it, and fails the run at the end, exactly as it treats a failed
download.]

[PITFALL: go.dev answers `<tarball>.sha256` with an HTML redirect page and a 200 status, which
`curl -f` accepts. The verifier refuses it ("lists no checksum"), so the result is safe, but Go's
entry points at `dl.google.com`, which serves the real file.]

## Migrated to

- **Mechanism**: `util.verify_sha256`, whose docstring carries both decisions, plus
  `tools._archive_urls` (one version lookup for both URLs) and the `apt._dpkg_install` wiring.
  Commits `63cdc0c` and `85839de`, with tests in `tests/unit/test_tools.py` and
  `tests/unit/test_apt.py`.
- **Field docs**: `setup.toml`'s header, under both the archive and deb-github sections.
- **Backfill**: `aaea47a` covers seven archive entries (atuin, helm, tilt, JetBrains Toolbox, Go,
  gog, gmailctl); `67ca7b5` covers five deb-github entries (k9s, Freelens, WezTerm, dive,
  Flameshot). Telegram Desktop and hyperfine publish none.
- **Verified live on 2026-09-28**: gog and gmailctl were reinstalled through it and printed
  `sha256 verified`. The other ten entries' checksum files were fetched and their format read by
  hand. Their packages are already installed, so the check first runs for them on a fresh install or
  `inv apt.upgrade-debs`.

## Recommended direction

Optional `checksum_url` on `archive` (and `deb-github`, same shape), read as the common
`<sha256>  <filename>` format, failing the package on a mismatch or a missing line. Backfill it on
every existing entry whose release publishes one, found with `package_health.py github`.
