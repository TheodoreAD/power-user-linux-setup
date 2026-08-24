---
status: landed
updated: 2026-08-24
depends_on: [repo-tasks]
---

# Uniform verb-first naming for invoke tasks

## Context

`inv --list` currently mixes two naming styles. Most tasks read as an action — `apt.uninstall`,
`fonts.install`, `git.configure`, `wsl.fix` — while a minority name the _thing_ instead of the
action: `apt.base`, `ai.skills`, `python.tools`, `system.dns`, `gnome.extensions`. Both styles are
defensible on their own (verbs, vs. make-like targets named for what they produce), but having both
means there is no instinct that reliably predicts a task's name.

The choice, made 2026-08-24: **verbs**, matching what the user names things in their other projects,
and matching how modern CLIs shape subcommands — `gh pr create`, `docker image prune`,
`kubectl config set-context` all read as `<subject> <verb>`, which is exactly this repo's
`<namespace>.<task>` shape.

[DECISION: "verbs" does not mean every task name must be a verb. Community conventions win over
formal consistency wherever one exists — `status`, `list`, `version` and friends stay as they are,
because a reader's instinct for `inv gnome.status` is worth more than a rule with no exceptions.
Stated by the user directly when the first draft of this plan proposed `gnome.show-status`: "of
course we keep all the community conventions, people should be able to use their instincts around
status, list, version, etc."]

[DECISION: multi-word task names lead with the verb (`zsh.fix-history`, `ide.configure-pycharm`),
matching community leaf compounds (`kubectl config set-context`, `gh repo set-default`,
`git remote
add`) — except where an object-first pair reads as a family in `inv --list` and that
adjacency is the point (`format-check`/`format-apply`, `lint-check`/`lint-apply`). Judgment call per
case, not a second rule.]

[DECISION: `quality.*`, `configs.*`, `docs.*` and `dev-env.*` come from `repo-tasks` and are out of
scope here, with a follow-up plan opened there so the family converges rather than splits. Per
`~/AGENTS.md`'s cross-repo rule the convention is mandatory family-wide, not optional per repo — the
split below is sequencing, not an exemption, and this plan is not `landed` until the follow-up
exists.]

### The rule

1. The namespace is the subject; the task is the action. `inv <namespace>.<task>` should read as an
   imperative command: "apt: install base", "zsh: fix history".
2. A task name leads with a verb — unless a community CLI convention already owns that name
   (`status`, `list`, `version`, `check`, `diff`), in which case the convention wins.
3. A handful of namespaces are themselves the action (`setup`, `verify`, `cleanup`, `deploy`,
   `test`). There the leaf names the scope or object being acted on — `verify.all`, `clean.caches`,
   `test.unit` — and the whole still reads as one imperative.

[DECISION: `test` joins rule 3's action-namespaces. `repo-tasks` introduced
`inv test.unit`/`test.integration`/`test.smoke`/`test.regression`/`test.all` on 2026-08-24, and a
reviewer reading rule 1 without rule 3 flagged them as inverted. They are not — `test.all` is the
same shape as `verify.all`. Rule 3 and `CONTRIBUTING.md`'s copy both name `test` explicitly now, so
the misreading does not recur.]

[DECISION: the follow-up this plan was blocked on exists —
`repo-tasks/plans/2026-08-24-verb-first-task-naming.md`, opened 2026-08-24. What remains before this
plan can land is that plan's `inv --list` audit of the shared namespaces, not its existence, so the
status line now names the audit instead.]

### Audit

103 tasks, of which 24 in this repo violate the rule, plus one namespace. Everything not listed in
the table below already complies.

## Design

### 1. Renames

| current                        | becomes                            | why                                         |
| ------------------------------ | ---------------------------------- | ------------------------------------------- |
| `ai.skills`                    | `ai.install-skills`                | noun; 42 references, the most-cited task    |
| `apt.base`                     | `apt.install-base`                 | noun                                        |
| `apt.deb`                      | `apt.install-debs`                 | noun                                        |
| `apt.repos`                    | `apt.install-repos`                | noun; sets up repos _and_ installs packages |
| `cleanup.all`                  | `clean.all`                        | namespace noun → verb                       |
| `cleanup.all-full`             | `clean.all-full`                   | ditto                                       |
| `cleanup.caches`               | `clean.caches`                     | ditto                                       |
| `cleanup.caches-full`          | `clean.caches-full`                | ditto                                       |
| `devcontainer.mounts`          | `devcontainer.print-mounts`        | noun; matches sibling `print-exclude-tags`  |
| `git.settings`                 | `git.apply-settings`               | noun; docstring already says "Apply"        |
| `gnome.extensions`             | `gnome.install-extensions`         | noun                                        |
| `ide.pycharm-configure`        | `ide.configure-pycharm`            | verb last                                   |
| `python.tools`                 | `python.install-tools`             | noun                                        |
| `ssh.keys`                     | `ssh.create-keys`                  | noun; docstring already says "Create"       |
| `system.apparmor-profiles`     | `system.install-apparmor-profiles` | noun                                        |
| `system.curlrc`                | `system.write-curlrc`              | noun; docstring already says "Write"        |
| `system.dns`                   | `system.configure-dns`             | noun                                        |
| `system.initramfs-compression` | `system.set-initramfs-compression` | noun                                        |
| `system.journal-size`          | `system.cap-journal-size`          | noun; docstring already says "Cap"          |
| `system.locale`                | `system.set-locale`                | noun                                        |
| `zsh.history-fix`              | `zsh.fix-history`                  | verb last                                   |
| `zsh.omz-configure`            | `zsh.configure-omz`                | verb last                                   |
| `zsh.p10k-configure`           | `zsh.configure-p10k`               | verb last                                   |

Each rename changes the Python function name too (`def base` → `def install_base`), since invoke
derives the CLI name from it — and `tasks/setup.py`/`tasks/wsl.py` reference those functions
directly in their phase lists, not by string.

`system.configs` is absent deliberately: it is being removed by
`plans/2026-08-22-deployed-config-drift-guard.md` step 3, not renamed.

### 2. The in-flight `deploy` namespace

That plan's step 3 was going to add `inv deploy.sync`. Under rule 3 that name is wrong — "deploy
sync" doesn't read as an imperative, and `deploy` is an action namespace like `verify`/`clean`.

[DECISION: `deploy.sync` becomes **`deploy.all`**, matching `verify.all` and `clean.all` — the leaf
names the scope, `--name` narrows it. `deploy.status` (already landed) stays exactly as it is under
rule 2. Caught before step 3 was written, so no rename is needed — just a corrected name in that
plan.]

### 3. What is deliberately not renamed

- **`status` tasks** — `gnome.status`, `allowlist.status`, `screenshot.status`, `deploy.status`.
  Rule 2.
- **`verify.all`, `setup`** — already read as imperatives under rule 3.
- **`apt.audit-keys`, `apt.refresh-keys`, `apt.upgrade-debs`, `allowlist.check-coverage`,
  `allowlist.check-man-deps`, `devcontainer.print-exclude-tags`, `devcontainer.render-docs`,
  `python.set-default`, `zsh.set-default-shell`, `system.disable-ipv6`, every `*.clean-cache*`** —
  already verb-first.
- **`repo-tasks`-owned namespaces** — §1's `[DECISION:]`.

[DEFERRED: `ssh.add` and `ssh.forward` both lead with a verb and so satisfy the rule, but neither
names its object — they add keys to the agent and copy public keys to remote hosts respectively.
`ssh.add-keys`/`ssh.forward-keys` would read better. Left out because that is a readability
improvement, not a convention fix, and folding it in would blur what this plan is for.]

### 4. No transitional aliases

[DECISION: rename outright rather than keeping the old names working via `@task(aliases=[...])`,
which invoke does support. This is a single-user repo whose every reference is updated in the same
commit series, so an alias would only serve the author's own muscle memory — at the cost of a
permanently doubled CLI surface and a second name for every task in every future search. The cost of
the clean break is one session of mistyping, and `inv --list` is right there. Reversible: adding
aliases later is a one-line decorator change per task if the break turns out to bite.]

### 5. Where the convention gets written down

`CONTRIBUTING.md` gains a short "Naming a task" section stating rules 1–3 with a worked example —
that file already owns how to work on this repo, and the rule needs a home that a future session
will actually read before adding a task. Not `AGENTS.md`: this is a contributor-facing convention,
not an operational instruction.

## Files touched

Renaming reaches further than `tasks/*.py`, because task names are cited in prose everywhere:

| area                                                        | what changes                                                             |
| ----------------------------------------------------------- | ------------------------------------------------------------------------ |
| `tasks/*.py`                                                | function names, the `cleanup`→`clean` module rename, `tasks/__init__.py` |
| `tasks/setup.py`, `wsl.py`                                  | phase lists reference the functions directly                             |
| `tasks/next_steps.py`                                       | prints suggested `inv ...` commands to the user                          |
| `tests/*`                                                   | every test importing a renamed function                                  |
| `setup.toml`                                                | header comment cites task names throughout                               |
| `docs/*.md` (20 files)                                      | prose, plus one heading anchor (`docs/claude-code.md`'s `inv ai.skills`) |
| `AGENTS.md`, `CONTRIBUTING.md`, `contributing/*.md`         | prose + §5's new section                                                 |
| `config/global-AGENTS.md`                                   | deployed to `~/AGENTS.md` — needs `inv tools.install` after              |
| `skills/*/SKILL.md` (3)                                     | deployed to `~/.agents/skills/` — needs `inv ai.install-skills` after    |
| `docker/Dockerfile`, `bootstrap*.sh`, `.github/workflows/*` | invoked task names                                                       |
| `plans/*.md`                                                | cited task names in open plans                                           |

[PITFALL: `docs/claude-code.md`'s `##`.agents/skills/`—`inv ai.skills`` is a _heading_, so renaming
it changes the generated anchor. The docs build runs a strict link check, and a stale internal
anchor is exactly the failure that broke the Pages deploy before (see
`plans/2026-08-23-git-hooks-for-quality-gate.md`'s context). Grep for inbound anchor links before
editing any heading that contains a task name.]

[PITFALL: `config/global-AGENTS.md` and the three `skills/*/SKILL.md` files are _deployed_ copies —
editing the repo source is only half the change. Both need their deploy task re-run afterwards, and
until then `inv deploy.status` will correctly report them stale. That is the mechanism working, not
a problem.]

## Verification

- `inv --list` shows no task whose name is a bare noun, `status`/`list`/`version` excepted.
- `rg 'inv [a-z-]+\.[a-z-]+' --glob '!plans/**'` finds no reference to a removed name.
- `inv quality.precommit` clean, full suite green.
- `inv setup --dry-run`-equivalent (`PULSE_DRY_RUN=1 inv setup`) still resolves every phase — the
  phase lists reference functions directly, so a missed rename is an `AttributeError` at import, not
  a silent no-op.
- `inv docs.build` (strict) passes — catches the heading-anchor pitfall.
- After landing: `inv tools.install` and `inv ai.install-skills` to redeploy the two edited deployed
  sources, then `inv deploy.status` reports everything clean again.

## Landed 2026-08-24 — all five steps

[DECISION: step 5 is done. `repo-tasks/plans/2026-08-24-verb-first-task-naming.md` audited its 67
tasks and landed three renames — `agents.claude-hook` → `agents.wire-claude-hook`, `dist.versions` →
`dist.list-versions`, `configs-promote` → `configs.promote` — plus a defect the audit exposed: four
tasks (`quality.unit`, `dev-env.allow`, `dev-env.create`, `dev-env.claude-hook`) were being
published as second names for tasks owned elsewhere, because `Collection.from_module` adds every
`Task` object it finds in a module, including ones imported for a `pre=` chain. The family no longer
splits, so this plan is `landed`.]

[PITFALL: this repo documented `inv dev-env.claude-hook` in `docs/claude-code.md` (a heading) and
`tests/README.md` — a command whose entire existence was an accident of an import statement in
`repo-tasks`' `dev_env.py`. Nothing declared it, no test asserted it, and it read like a deliberate
convenience alias. When citing another repo's task by name, the check is that repo's own module
source, not that the command happens to run.]

[DEFERRED: this repo's `uv.lock` pins `repo-tasks` at git SHA `83153ad`, which predates both the
`test.*` namespace and today's renames — so `inv agents.wire-claude-hook` does not work here yet,
and `inv dev-env.claude-hook` still does. The prose above describes the family's current state
deliberately; closing the gap needs `repo-tasks` pushed and this repo's pin bumped, which is a
deliberate standalone act (see `~/AGENTS.md`, "Regenerating a file from a canonical source"), not a
side effect of a naming pass.]

## Steps 1–4

All 24 renames plus the `cleanup`→`clean` namespace are in, across code, tests, `setup.toml`, the
Dockerfile, CI, 27 prose files, and the deployed sources (redeployed; `inv deploy.status` reports
every managed path ok). `CONTRIBUTING.md` carries the rule. Only step 5 — the `repo-tasks` follow-up
— is outstanding, which is what this plan is now blocked on.

What the execution turned up that the plan didn't predict:

[PITFALL: a mechanical rename cannot tell a CLI name from a Python identifier by context alone, and
both spellings of the same task appear in the same file. The pass put `[ai.install_skills]` into
`ai.py`'s user-facing output labels — a bare f-string prefix looks like neither code nor prose.
Caught by _running_ `inv ai.install-skills` and reading its output, not by the suite, which never
asserts on label text. Grep for the snake spelling inside string literals after any future rename.]

[PITFALL: the heading-anchor risk this plan flagged as its main danger was a non-issue —
`docs/claude-code.md`'s `## .agents/skills/ — inv ai.skills` is the only heading citing a renamed
task, and nothing links to its anchor. Two greps (`claude-code.md#`, then `^#+ .*<task>`) settled it
in seconds, and `inv docs.build` (`zensical --strict`) confirmed. Cheap to check, so check — but the
real cost was elsewhere.]

[PITFALL: three lines crossed ruff's 120-char limit purely because the new names are longer. Wrap
the line; never shorten a name to fit a formatter.]

## Sequencing

Renames are mechanical but wide, so the split is by blast radius, not by namespace:

1. **`tasks/*.py` + `tests/*`** — every rename, including the `cleanup`→`clean` module rename and
   `deploy.sync`→`deploy.all` in the not-yet-written step 3. Suite green at the end of this commit.
2. **`setup.toml` + the scripts that invoke tasks** (`docker/Dockerfile`, `bootstrap*.sh`, CI
   workflows) — the paths where a stale name is a runtime failure, not a doc typo.
3. **`docs/*.md` + `AGENTS.md` + `contributing/*.md`**, including §5's new CONTRIBUTING section and
   the heading-anchor check.
4. **`config/global-AGENTS.md` + `skills/*/SKILL.md`**, then redeploy both.
5. **Open the `repo-tasks` follow-up plan** for `quality.*`/`dev-env.*`, linked from here.

[DEFERRED: the `repo-tasks` half — `quality.format-check`/`lint-apply`/`type-check`/`shell-check`
(verb-second) and `dev-env.claude-hook` (noun) — plus whatever `scaffoldapy` templates and the
`*-polite-mcp` repos cite. Sequenced after this repo lands, but mandatory, not optional: see §1's
`[DECISION:]`. This plan cannot reach `landed` while it is outstanding.]
