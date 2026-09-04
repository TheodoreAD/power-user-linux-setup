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
that repo's own `inv configs.promote` (see
[`contributing/repo-family-architecture.md`](contributing/repo-family-architecture.md), and
[`contributing/quality-tooling.md`](contributing/quality-tooling.md) for why each tool is tuned the
way it is). `dprint.json` still lists its plugins in `[packages.dprint]` in `setup.toml` too — keep
the two in sync by hand, since `setup.toml` drives what actually gets installed on this machine
independent of `configs.pull`.

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
                     # workflow_check + dockerfile_check + link_check + deps_check +
                     # untested_modules + unit — CI-style gate, no changes written
inv quality.fix      # lint_apply + format_apply + shell_format_apply — fixes everything auto-fixable
```

Individually, in the `quality` namespace: `lint-check`, `lint-apply`, `format-check`,
`format-apply`, `type-check`, `verify-types`, `shell-check`, `shell-format-check`,
`shell-format-apply`, `workflow-check`, `dockerfile-check`. Four members of the `check` chain live
in other namespaces and are invocable there: `inv docs.link-check`, `inv test.untested-modules`,
`inv test.unit`, and `repo-tasks`' own `deps.check` — which this repo runs through the chain but
does not publish as a task of its own, since `tasks/__init__.py` adds no `deps` collection.

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
> is a lint error). Unrelated to `markdown.textWrap`, which is `"always"` — hard-wrap prose at the
> markdown `lineWidth` of 100. Don't change it to `"never"`, which does not mean "leave wrapping
> alone" but "never insert a line break", i.e. join every paragraph onto one line. See
> [`contributing/quality-tooling.md`](contributing/quality-tooling.md).

## Docs site

The published site is built from `docs/` and `mkdocs.yml` by [zensical](https://zensical.org/),
which `.github/workflows/publish_on_push.yml` runs as `zensical build --strict` on every push to
`master`. Locally:

```shell
inv docs.serve        # zensical serve — live reload while writing
inv docs.build        # zensical build --strict, the exact version and command CI runs
inv docs.clean        # remove the built site/
```

`zensical` is not a dependency of `repo-tasks`. It is pinned once, in this repo's `pyproject.toml` —
the `docs` dependency group, which `[tool.uv] default-groups` makes part of an ordinary `uv sync`,
so `inv dev-env.setup` installs it and direnv's `.venv/bin` puts it ahead of anything on `PATH`. The
Pages workflow resolves the same pin from `uv.lock`
(`uv run --only-group docs --frozen zensical build --strict`), so a green local build is a green
deploy.

> [!NOTE]
> Until 2026-09-04 the pin was declared twice — a `requirements-docs.txt` only CI read, against
> `[packages.zensical]` in `setup.toml` installing it unpinned machine-wide — and the two drifted.
> Measured 2026-09-02: a generated table cell containing `[certs]` — a bare bracket, which markdown
> reads as a link reference — passed locally on zensical 0.0.57 and failed CI's pinned 0.0.44 with
> `unresolved link reference`. `setup.toml`'s entry stays, for other repos and for the human at the
> shell; inside this repo the venv's copy wins, which is the point.

The built `site/` is gitignored.

> [!WARNING]
> `inv quality.precommit` does **not** build the site. `inv docs.link-check` runs in the gate, but
> it checks that a link's _file_ exists and stops at the fragment — so renaming a heading that
> another page links to (`configuration.md#some-heading`) passes every local check and fails the
> Pages deploy. After renaming a heading, grep for inbound links to it and run `inv docs.build`.

## Naming a task

`inv <namespace>.<task>` should read as an imperative command — the namespace is the subject, the
task is the action. `inv apt.install-base` is "apt: install base"; `inv zsh.fix-history` is "zsh:
fix history".

The full convention lives in the **`invoke-task-conventions` skill**, authored in
[`agent-skills`](https://github.com/TheodoreAD/agent-skills) and installed to `~/.agents/skills/` by
`inv ai.install-skills` so it reaches every repo in the family, not just this one. Read it before
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
- [`contributing/certs.md`](contributing/certs.md) — the corporate-CA-bundle feature's QA/fixture
  playbook (companion to [`docs/certs.md`](docs/certs.md)).
- [`contributing/repo-family-architecture.md`](contributing/repo-family-architecture.md) — what each
  of `power-user-linux-setup`/`repo-tasks`/`scaffoldapy` actually owns, the decision rule for where
  new shared work between them goes, and why the shared task runner is a global `uv tool` install.
- [`contributing/deploy.md`](contributing/deploy.md) — why every path this repo writes under `~`
  goes through `tasks/deploy.py`, the five-state classifier and its manifest, and the pitfalls hit
  building it (companion to the "Whole-file configs" section of
  [`docs/configuration.md`](docs/configuration.md)).
- [`contributing/verify.md`](contributing/verify.md) — every gotcha `inv verify.all`'s first
  implementation pass hit, and how testing (not review) caught each one.
- [`contributing/quality-tooling.md`](contributing/quality-tooling.md) — why each quality tool was
  picked and tuned the way it is (basedpyright, ruff, dprint, shellcheck/shfmt), and the traps that
  only showed up once the config met real code.
- [`contributing/chrome-ozone.md`](contributing/chrome-ozone.md) — every measured dead end in
  forcing Chrome onto X11, and why `inv chrome.status` reports rather than repairs (companion to
  [`docs/chrome.md`](docs/chrome.md)).

If you're about to write a "why this is built this way" section in `docs/`, it probably belongs in
`contributing/` instead — add a new per-topic file there and list it above. Exception: if the
writeup is documentation for a skill, it belongs inside that skill's own `references/` directory, so
it travels with the skill instead of staying behind in whichever repo happened to author it. That is
why most skills now live in [`agent-skills`](https://github.com/TheodoreAD/agent-skills) rather than
here; `contributing/` keeps only rationale about this repo's own mechanisms, which never leaves it.

**No skill is authored here any more** — there is no `skills/` directory. The last two moved
2026-08-28, and what stayed behind is the pattern to copy when a skill and a local mechanism are
entangled: `contributing/research-library.md` documents the `$RESEARCH_HOME` machinery this repo
deploys (the env var, the `research-update` script, the read grant), while the conventions for
_using_ a research library travel with the skill. Anything that would travel goes in the skill's
`references/`; anything that only makes sense on a machine running this repo stays here.

## Git workflow

Direct, focused commits straight to `master` are the normal way to land changes here. Open a PR
instead only when either (a) someone other than the owner is contributing, or (b) a batch of related
commits is worth bundling behind a PR description for reviewability.
