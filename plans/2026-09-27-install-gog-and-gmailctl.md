---
status: idea
updated: 2026-09-27
source_repo: github.com-personal/agent-skills
source_session: a953b16f-c02c-45d9-99e8-21a7277c781d.jsonl
source_moment: 2026-09-27
source_plan: ~/plans/_unscoped/2026-09-26-google-api-access-foundation.md
---

# Install gog and gmailctl

## Context

The Google-stack assistant work, planned in the unscoped plans store under
`2026-09-26-google-stack-assistant-master.md` and branches, chose its access layer on 2026-09-27.
The user's decision, verbatim: "go with gog + gmailctl".

- **gog** (openclaw/gogcli, formerly steipete/gogcli, MIT) is the general CLI for Gmail, Calendar,
  Drive, Tasks and Contacts.
- **gmailctl** (mbrt/gmailctl, MIT) handles Gmail filters as code: Jsonnet, `diff`/`test`/`apply`.

The reasoning, and what each tool does and doesn't cover, live in the `source_plan`. Read it before
implementing, in case the decision moved after this was filed.

Neither tool is on PyPI or apt, and neither is installed on this machine (`which` finds neither on
2026-09-27). Both publish Linux release tarballs on GitHub, read through
`gh api .../releases/latest` on 2026-09-27:

| package  | latest              | asset                                   | size    | alongside                                                        |
| -------- | ------------------- | --------------------------------------- | ------- | ---------------------------------------------------------------- |
| gog      | v0.42.0, 2026-09-25 | `gogcli_{version}_linux_amd64.tar.gz`   | 14.8 MB | `checksums.txt`, `SIGNING-MANIFEST.json`, `ASSET-INVENTORY.json` |
| gmailctl | v0.12.0, 2026-05-19 | `gmailctl_{version}_linux_amd64.tar.gz` | 7.2 MB  | `checksums.txt`                                                  |

The existing `archive` method already fits this shape. `helm` and `tilt` use `version_cmd` over the
GitHub releases API, plus `download_url` with `{version}` and `bin_pick`.

## Evidence

- Transcript `a953b16f-c02c-45d9-99e8-21a7277c781d.jsonl` (the agent-skills project directory),
  2026-09-27. The user's words were "go with gog + gmailctl, figure out an
  as-much-as-possible-scripted way for the auth, ensuring we don't leave the json file in downloads,
  if that needs to happen, and file the setup.toml plan".
- Tool evaluation: clones at `$RESEARCH_HOME/repos/github.com--steipete--gogcli` and
  `github.com--mbrt--gmailctl`.

## Open questions

[NEEDS CLARIFICATION: checksum verification. `setup.toml` has no checksum field (no `sha256` or
`checksum` anywhere in it on 2026-09-27). Both tools publish `checksums.txt`, and gog also publishes
a signing manifest. Is verifying a published checksum worth adding to the `archive` method as an
optional `checksum_url`? It would benefit every GitHub-release package, not only these two. The
check has to be against a file fetched from the same release, and it defends against a corrupted
download rather than a compromised release.]

[NEEDS CLARIFICATION: the tarball layout. Confirm whether each binary sits at the archive root
(`bin_in_root = true`, like tilt) or under a directory (`bin_pick` alone, like helm). Download one
of each and list it before writing the entries.]

[NEEDS CLARIFICATION: the `go install` alternative. Go is installed through `[packages.go]`, and
`go install github.com/openclaw/gogcli/cmd/gog@latest` would work too. The archive route is
preferred because it needs no toolchain on a fresh machine and matches the published, checksummed
artifact. Confirm the preference.]

[NEEDS CLARIFICATION: shell completion. Check whether either tool offers `completion zsh`, like
`tilt` does in its `zshrc` line.]

## Recommended direction

1. Add `[packages.gog]` and `[packages.gmailctl]` with `method = "archive"`:
   - `version_cmd` reading `tag_name` from the releases API, the same shape as helm and tilt;
   - `download_url` pointing at the linux_amd64 tarball;
   - `bin_pick`, and `bin_in_root` if the layout calls for it;
   - `check_cmd`, and a `verify_cmd` that actually works for each binary.

   Tags should be something like `["google", "cli", "agents"]`. Enabled by default, or opt-in
   through overrides as `telegram-desktop` is, is the user's call: these are personal-account tools,
   but so is most of this machine.
2. Descriptions should say what each is for, and point at the auth bootstrap, which is not
   `setup.toml`'s job. The first run needs a Google Cloud project, a published consent screen and a
   Desktop OAuth client, with the steps and the script living in the Google-stack skill in
   `agent-skills`. Installing a binary should never start an OAuth flow.
3. Verify with `inv` for these two packages, then `gog --version` and `gmailctl version` from a
   fresh shell.
