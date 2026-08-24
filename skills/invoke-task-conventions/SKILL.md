---
name: invoke-task-conventions
description: "Use when adding, renaming, or reviewing an invoke task in a tasks.py or tasks/ package — deciding what to call `inv <namespace>.<task>`, whether a name should be a verb or a noun, where a new task belongs, or whether an existing name is worth changing. Also covers what a rename actually costs (task names are cited in docs, CI, Dockerfiles and other repos, and the Python function name changes with the CLI name), and the invoke wiring traps that silently publish tasks nobody declared. Applies across the personal repo family — power-user-linux-setup, repo-tasks, scaffoldapy-generated projects, the *-polite-mcp repos."
---

# Naming and wiring invoke tasks

`inv <namespace>.<task>` should read as an imperative command. The namespace is the subject, the
task is the action: `inv apt.install-base` is "apt: install base", `inv zsh.fix-history` is "zsh:
fix history".

This is the mainstream CLI shape, not a local invention — `gh pr create`, `docker image prune`,
`kubectl config set-context` are all `<subject> <verb>`, and Azure CLI mandates it outright
("Commands must follow a `[noun] [noun] [verb]` pattern"). See
[`references/rationale.md`](references/rationale.md) for the prior art and the evidence behind each
rule below.

## The three rules

**1. Task names lead with a verb.** Name the action, not the thing produced — `apt.install-base`,
not `apt.base`; `ai.install-skills`, not `ai.skills`. Azure CLI states the same rule as "all command
names should contain a verb."

Multi-word task names put the verb first (`zsh.configure-omz`, `ide.configure-pycharm`), with one
exception: keep object-first when a pair reads as a family in `inv --list` and that adjacency is the
point — `format-check`/`format-apply`, `lint-check`/`lint-apply`. Judgment call per case, not a
second rule.

**2. Community conventions beat the rule.** Where a CLI convention already owns a name — `status`,
`list`, `version`, `check`, `diff` — keep it. `inv gnome.status` is what a reader's instinct reaches
for; `gnome.show-status` would be more consistent and worse. Same for a task that wraps a named
subcommand: `deps.tree` wraps `uv tree` and keeps its name.

**3. Some namespaces are themselves the action.** `setup`, `verify`, `clean`, `deploy`, `test`.
There the leaf names the scope or object instead: `verify.all`, `clean.caches`, `deploy.all`,
`test.unit`. This is the stated exception to rule 1, not a violation of it — a reader who sees rule
1 alone will flag `test.unit` as inverted, which has already happened once.

Prefer a subject namespace where one fits. Reach for an action namespace only when the tasks under
it genuinely differ by scope rather than by action.

## Be consistent about which verb

Pick one verb per meaning and reuse it across namespaces rather than alternating synonyms —
`install`, `configure`, `set`, `write`, `create`, `clean`, `fix`, `check`, `apply`, `print`,
`render`. Azure CLI's guidelines make the same point ("be consistent with the verbs you use across
different types of objects") and additionally warn off verbs that collide with a standard meaning.

When a task's docstring already starts with a verb, that verb is usually the name: a task whose
docstring began "Cap persistent journal size" belonged at `cap-journal-size`, and one beginning
"List a project's published versions" at `list-versions`. Several renames in this family were found
exactly that way.

## Renaming is a code change with a wide blast radius

Do not treat a rename as a string substitution:

- **The Python function name changes with the CLI name** (invoke derives one from the other), and
  phase lists or `pre=` chains reference the function object directly. A missed rename is an
  `AttributeError` at import — which is good: `inv --list` loading at all proves the code side is
  complete.
- **Task names are cited in prose far outside the module.** In one 24-task pass: 53 files, including
  every `docs/*.md`, the `setup.toml` header comment, a Dockerfile, CI workflows, bootstrap scripts,
  and other repos' documentation.
- **A mechanical pass cannot tell a CLI name from a Python identifier**, and both spellings of the
  same task appear in the same files. A rename script put `[ai.install_skills]` into user-facing
  output labels; no test caught it, because tests do not assert on label text. After any scripted
  rename, grep the snake spelling inside string literals, and run the task and read its output.
- **Check headings.** A task name in a Markdown heading changes that page's anchor, and a strict
  docs build fails on the dangling link. Grep for inbound `<page>.md#` links before editing.
- **Deployed copies need redeploying.** If a renamed task is cited in a file that gets installed
  somewhere (`~/AGENTS.md`, `~/.agents/skills/*`), editing the repo source is half the change.

Rename outright rather than keeping the old name alive via `@task(aliases=[...])`. An alias
permanently doubles the CLI surface and gives every task a second name in every future search; the
cost of a clean break is one session of mistyping.

## Wiring traps

**An imported task is a published task.** `Collection.from_module` adds every `Task` object it finds
in a module's namespace, and an imported one is indistinguishable from a defined one — so a task
pulled in for a `pre=` chain gets published a second time under the importing module's name. This
produced four tasks nobody had declared (`quality.unit` beside `test.unit`; `dev-env.create`,
`dev-env.allow` and `dev-env.claude-hook` beside the `venv`/`direnv`/`agents` tasks that own them),
and went unnoticed long enough that another repo documented one of them as the real name.

Any module that imports a task must declare an explicit module-level namespace, which `from_module`
prefers over its auto-scan:

```python
ns = Collection(setup)  # only what this module actually owns
```

**When citing another repo's task by name, check that repo's module source** — not that the command
happens to run. A command that works may be an accident of someone's import statement.

**A namespace only exists if it's wired.** A consumer repo that builds its own `Collection` from
selected upstream modules silently loses any task in a module it doesn't import. Run `inv --list`
after a dependency bump, not just the test suite.

## Auditing an existing repo

`inv --list | grep -oP '^  [a-z0-9.-]+'` gives the full surface. Read it against the module sources,
not from memory — that comparison is what surfaces both violations and tasks nobody declared. Then
sort each name into: verb-first already, community convention (rule 2), action namespace (rule 3),
or a real violation. Record the conforming-on-purpose cases somewhere durable, because the next
reader will otherwise "fix" them — `gitflow.feature-start` looks like a violation until you know it
mirrors `git flow feature start`.
