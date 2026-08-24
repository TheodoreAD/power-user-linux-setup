# Contributing

Repo-development notes for anyone working on power-user-linux-setup itself — not needed just to
_use_ it (see the [docs site](https://theodoread.github.io/power-user-linux-setup/) for that).

## Dev environment & tests

See [tests/README.md](tests/README.md): `inv dev-env.setup` once after cloning (`uv sync` +
`direnv allow`), then plain `pytest` (or `inv test.unit`) — no `uv run` prefix, no manual
activation. Tests live in `tests/unit/`; there is deliberately no integration tier (see
`tests/README.md`).

## Code quality

This repo lints/formats Python with [ruff](https://docs.astral.sh/ruff/) and formats
JSON/TOML/Markdown/YAML/Dockerfile with [dprint](https://dprint.dev/), both declared in the `dev`
dependency group. `ruff.toml`/`pyrightconfig.json`/`dprint.json`/`pytest.ini`/`.editorconfig` are
all committed, but no longer hand-maintained here — they're pulled from
[`repo-tasks`](https://github.com/TheodoreAD/repo-tasks)'s canonical copies (`inv configs.pull`),
same as every other repo in the family. `inv configs.diff` checks for drift without writing
anything; a genuine local tuning here gets promoted back into `repo-tasks`' shipped baseline via
that repo's own `inv configs.promote` (see `plans/2026-08-14-python-repo-scaffolding.md` §D and
[`contributing/repo-family-architecture.md`](contributing/repo-family-architecture.md)).
`dprint.json` still lists its plugins in `[packages.dprint]` in `setup.toml` too — keep the two in
sync by hand, since `setup.toml` drives what actually gets installed on this machine independent of
`configs.pull`.

Don't call `ruff`/`dprint` directly — always go through the `inv quality.*` tasks below. They bake
in required flags (see the note below) and keep the tools' invocation in one place instead of
scattered across every contributor's/agent's memory of the right command line.

```shell
inv quality.precommit   # fix, then check — the one command to run before considering a change done
```

That's `fix` (fix everything auto-fixable) followed by `check` (verify clean), each in turn a
`pre=`-chain of the individual `<category>_check` / `<category>_apply` tasks (`_check` never writes,
`_apply` fixes what's auto-fixable):

```shell
inv quality.check   # lint_check + format_check + type_check + shell_check + shell_format_check +
                     # test — CI-style gate, no changes written
inv quality.fix      # lint_apply + format_apply + shell_format_apply — fixes everything auto-fixable
```

Individually: `lint_check`, `lint_apply`, `format_check`, `format_apply`, `type_check`,
`shell_check`, `shell_format_check`, `shell_format_apply`, `test`.

> [!NOTE]
> `dprint fmt`/`dprint check` need `--config-discovery=ignore-descendants` (already baked into the
> `inv quality.*` tasks) — without it, dprint's config-discovery walks into
> `cli-allowlist/rules/dprint.json` (the allowlist pipeline's classification-rules file for the
> `dprint` _tool_, an unrelated file that happens to share dprint's own config filename) and
> misreads it as a nested sub-project config.

> [!WARNING]
> When adding a new `!!! NOTE`/`!!! WARNING` mkdocs admonition to `docs/*.md`, put a **blank line**
> between the `!!! TYPE` marker and its indented body. Without one, dprint's markdown plugin parses
> the body as a lazy paragraph continuation and strips its indentation on format — silently breaking
> the admonition into a plain paragraph (mkdocs-material then renders the literal `!!!
> TYPE` text
> instead of a callout box, and `dprint check`/`ruff`/pytest all stay green since nothing about this
> is a lint error). `dprint.json`'s `markdown.textWrap` is `"maintain"` (dprint's own default)
> specifically so it doesn't also collapse ordinary hand-wrapped prose — don't change it to
> `"never"`, which means "never wrap," i.e. join every paragraph onto one line.

## Naming a task

`inv <namespace>.<task>` should read as an imperative command — the namespace is the subject, the
task is the action. `inv apt.install-base` is "apt: install base"; `inv zsh.fix-history` is "zsh:
fix history".

The full convention lives in the **`invoke-task-conventions` skill**
(`skills/invoke-task-conventions/SKILL.md`, deployed to `~/.agents/skills/` by
`inv ai.install-skills` so it reaches every repo in the family, not just this one). Read it before
adding or renaming a task. In short: task names lead with a verb; community conventions (`status`,
`list`, `version`, `check`, `diff`) beat the rule; and a namespace that is itself the action
(`setup`, `verify`, `clean`, `deploy`, `test`) takes a scope leaf instead — `verify.all`,
`deploy.all`, `test.unit`.

Renaming a task is a code change, not a string change: the Python function name changes with the CLI
name, and `tasks/setup.py`/`tasks/wsl.py` reference task functions directly in their phase lists.
The skill's rename checklist covers the rest of the blast radius.

## Design notes

`docs/*.md` is published to the public site (`docs_dir: docs` in `mkdocs.yml`) — it's for people
_using_ this tool, not developing it. Longer implementation/design write-ups that don't belong there
live in [`contributing/`](contributing/) instead, one file per topic, never published:

- [`contributing/cli-allowlist.md`](contributing/cli-allowlist.md) — the CLI permission allowlist
  pipeline's full design rationale (companion to the trimmed
  [`docs/cli-allowlist.md`](docs/cli-allowlist.md)).
- [`contributing/zensical.md`](contributing/zensical.md) — everything verified (as opposed to
  documented) about how the zensical docs-site engine actually behaves; read before a version bump.
- [`contributing/research-library.md`](contributing/research-library.md) — design rationale for the
  shared `$RESEARCH_HOME` cross-project reference store.
- [`contributing/mcp-skill-shipping.md`](contributing/mcp-skill-shipping.md) — design rationale for
  the personal MCP-server/skill dev + distribution workflow (companion to the deployed
  `skills/mcp-skill-shipping/SKILL.md`).
- [`contributing/certs.md`](contributing/certs.md) — the corporate-CA-bundle feature's QA/fixture
  playbook (companion to [`docs/certs.md`](docs/certs.md)).
- [`contributing/repo-family-architecture.md`](contributing/repo-family-architecture.md) — what each
  of `power-user-linux-setup`/`repo-tasks`/`scaffoldapy` actually owns, and the decision rule for
  where new shared work between them goes.

If you're about to write a "why this is built this way" section in `docs/`, it probably belongs in
`contributing/` instead — add a new per-topic file there and list it above. Exception: if the
writeup is documentation for a shipped skill (something under `skills/<name>/`), it belongs inside
that skill's own directory instead — e.g. `skills/<name>/references/*.md` — so it travels with every
`inv ai.install-skills` copy into every other repo. `contributing/` stays for rationale that's
internal to this repo and never leaves it (see `skills/plan-docs/references/design-rationale.md` vs.
`skills/mcp-skill-shipping/`'s and `skills/research-library/`'s external `contributing/<name>.md`
companions for both patterns side by side).

## Git workflow

Direct, focused commits straight to `master` are the normal way to land changes here. Open a PR
instead only when either (a) someone other than the owner is contributing, or (b) a batch of related
commits is worth bundling behind a PR description for reviewability.
