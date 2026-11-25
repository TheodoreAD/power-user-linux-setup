### Installing a tool on this machine [needs setup.toml]

Never as a one-off manual step: `curl | bash`, a release tarball into `~/.local/bin`,
`gh extension install`. Every tool is a `[packages.<name>]` entry in `power-user-linux-setup`'s
`setup.toml`, installed by its `inv` task, or the machine silently diverges from its own setup and
the next machine never gets it. Look for a maintained PyPI wrapper first (`shellcheck-py`,
`shfmt-py`, `actionlint-py`, `act-bin` — `method = "uv-tool"`) before any other method, so setup
stays one mechanism deep.

**Judge the candidate with `package_health.py`, never with a hand-rolled registry fetch or a search
summary:**

```shell
python3 ~/.agents/skills/research-library/scripts/package_health.py pypi <name> --upstream <owner/repo>
```

It lists what the latest release ships — platform-tagged wheels mean the binary is inside one, an
sdist alone means it fetches at install time, and the sizes and release count are the adoption cost
— and `--upstream` answers "maintained": whether the wrapper tracks upstream's latest release, and
by how many days. For a tool with no PyPI wrapper the same script takes `github <owner/repo>`
(release binaries, the `archive`/`deb-github` route), `npm <name>` or `apt <name>`. It goes wrong in
both directions. A summary claimed `hadolint-py` downloads at install and it was nearly rejected for
a false reason, since it ships real 12 MB wheels; `lychee-bin` turned out to be a 78 MB wheel with
exactly one release ever, which reversed a decision already made to adopt it. A tool a repo's
quality gate or test tasks run also goes in that repo's dependency group — the user-wide install is
for the human at the shell, the group is what CI and consumers resolve.
