# Contributing

Repo-development notes for anyone working on power-user-linux-setup itself — not needed just to
_use_ it (see the [docs site](https://theodoread.github.io/power-user-linux-setup/) for that).

## Dev environment & tests

See [tests/README.md](tests/README.md): `inv python.dev-venv` once after cloning (`uv sync` +
`direnv allow`), then plain `pytest tests/` — no `uv run` prefix, no manual activation.

## Code quality

This repo lints/formats Python with [ruff](https://docs.astral.sh/ruff/) and formats
JSON/TOML/Markdown/YAML/Dockerfile with [dprint](https://dprint.dev/), both declared in the `dev`
dependency group / `dprint.json` (see `[tool.ruff]` in `pyproject.toml`). `inv python.dev-venv`
creates `dprint.json` automatically on first run — idempotent; pass `--force` to recreate it and
re-pin plugin versions.

Don't call `ruff`/`dprint` directly — always go through the `inv quality.*` tasks below. They bake
in required flags (see the note below) and keep the tools' invocation in one place instead of
scattered across every contributor's/agent's memory of the right command line.

```shell
inv quality.fix     # apply, then check — the one command to run before considering a change done
```

That's `apply` (fix everything auto-fixable) followed by `check` (verify clean), each in turn a
`pre=`-chain of the individual `<category>_check` / `<category>_apply` tasks (`_check` never writes,
`_apply` fixes what's auto-fixable):

```shell
inv quality.check   # lint_check + format_check + test — CI-style gate, no changes written
inv quality.apply   # lint_apply + format_apply — fixes everything auto-fixable
```

Individually: `lint_check`, `lint_apply`, `format_check`, `format_apply`, `test`.

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

If you're about to write a "why this is built this way" section in `docs/`, it probably belongs in
`contributing/` instead — add a new per-topic file there and list it above. Exception: if the
writeup is documentation for a shipped skill (something under `skills/<name>/`), it belongs inside
that skill's own directory instead — e.g. `skills/<name>/references/*.md` — so it travels with every
`inv ai.skills` copy into every other repo. `contributing/` stays for rationale that's internal to
this repo and never leaves it (see `skills/plan-docs/references/design-rationale.md` vs.
`skills/mcp-skill-shipping/`'s and `skills/research-library/`'s external `contributing/<name>.md`
companions for both patterns side by side).

## Git workflow

Direct, focused commits straight to `master` are the normal way to land changes here. Open a PR
instead only when either (a) someone other than the owner is contributing, or (b) a batch of related
commits is worth bundling behind a PR description for reviewability.
