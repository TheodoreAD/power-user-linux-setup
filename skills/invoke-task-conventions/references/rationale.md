# Why these rules, and where they came from

## Prior art (web pass, 2026-08-24)

Searched before writing anything, per `~/AGENTS.md`'s "About to author content, config, or a
workaround from scratch". **No existing skill or published style guide covers invoke task naming
specifically** — `pyinvoke`'s own docs cover argument/flag naming (underscores in Python become
dashes on the command line) but say nothing about what to call a task or a namespace. The rules here
are therefore this family's own, but they are not invented from nothing: the shape they settle on is
the mainstream CLI convention, independently arrived at by several published guides.

- **[Command Line Interface Guidelines (clig.dev)](https://clig.dev/)** — for software with many
  objects and operations, use two levels of subcommand, one noun and one verb, as in
  `docker container create`. Notes that either noun-verb or verb-noun ordering works but **noun-verb
  is more common**. That is exactly invoke's `<namespace>.<task>` shape, which is why rule 1 reads
  as it does.
- **[Azure CLI command guidelines](https://github.com/Azure/azure-cli/blob/dev/doc/command_guidelines.md)**
  — the strictest published version of the same idea, and the closest match to our rules:
  - "Commands must follow a `[noun] [noun] [verb]` pattern" — rule 1.
  - "All command names should contain a verb" — rule 1 again, stated as a hard requirement.
  - "Be consistent with the verbs you use across different types of objects" — the "be consistent
    about which verb" section.
  - A command with subcommands under it "should function as an area or grouping identifier rather
    than specify an action" — which is the _inverse_ framing of our rule 3, and worth knowing about:
    Azure would not allow `verify.all`, because `verify` is a grouping and so must be a noun.
  - Multi-word subgroups hyphenate (`foo-resource`), and a subgroup that would hold a single command
    gets hyphenated into its parent instead (`database list-sku-definitions`).
- **[fnproject's "CLI Proposal: verb noun structure"](https://github.com/fnproject/cli/wiki/CLI-Proposal:--verb--noun--structure)**
  — a real project arguing the opposite order. Recorded so nobody assumes noun-verb is universal.
- **[Nix CLI guideline](https://nix.dev/manual/nix/2.18/contributing/cli-guideline)** and
  **[.NET System.CommandLine design guidance](https://learn.microsoft.com/en-us/dotnet/standard/commandline/design-guidance)**
  — same two-level noun/verb family, less prescriptive.

### Where we deliberately diverge from Azure

Azure's standard verb vocabulary is `create`/`update`/`set`/`show`/`list`/`delete`/`wait`, and it
would name a state-reporting command `show`. This family uses **`status`** instead (`gnome.status`,
`deploy.status`, `allowlist.status`), because the instinct a reader actually brings comes from
`git status` and `systemctl status`, not from Azure. That is rule 2 doing its job: where a community
convention already owns a name, the convention wins over internal consistency. Rule 2 exists because
of a direct user correction while this convention was being drafted — an early draft proposed
`gnome.show-status` and the response was "of course we keep all the community conventions, people
should be able to use their instincts around status, list, version, etc."

Azure's "a command with subcommands is a grouping, so it must be a noun" is the one place we
knowingly disagree. `verify.all`, `clean.caches`, `deploy.all` and `test.unit` keep an action
namespace with a scope leaf, because the whole still reads as one imperative and the alternative
(`verification.run`, `cleanup.run-caches`) reads worse. Rule 3 is that exception, stated explicitly
rather than left to be rediscovered — a reviewer reading rule 1 without rule 3 flagged `test.unit`
as inverted once already, which is why `test` is named in the rule text.

## Evidence behind the non-naming sections

Everything in "Renaming is a code change with a wide blast radius" and "Wiring traps" comes from
executing this convention across two repos on 2026-08-24, not from theory:

- The 24-task rename in `power-user-linux-setup` touched 53 files. The heading-anchor risk was
  checked and turned out harmless there (nothing linked to the one affected anchor), but the check
  cost two greps and is worth keeping.
- The mechanical rename script wrote `[ai.install_skills]` into `ai.py`'s user-facing output labels.
  Found by running `inv ai.install-skills` and reading its output; the suite stayed green throughout
  because no test asserts on label text.
- Three lines crossed the 120-char lint limit purely because the new names were longer. Wrap the
  line; never shorten a name to fit a formatter.
- The `Collection.from_module` trap was found by reading `inv --list` against the module sources
  during `repo-tasks`' naming audit — four undeclared tasks, one of which (`dev-env.claude-hook`)
  `power-user-linux-setup` had documented as a heading in `docs/claude-code.md` and in
  `tests/README.md`. Its real name is `agents.wire-claude-hook`.
- Fixing that leak then _removed_ the command from `power-user-linux-setup`, because that repo wires
  only four upstream namespaces and `agents` was not one of them. Caught by running `inv --list`
  after the dependency bump — the test suite could not have caught it, since it asserts on the
  namespaces the repo does wire.

## Why a skill rather than `~/AGENTS.md`

The trigger is sharp and statable ("adding or renaming an invoke task"), which
`contributing/global-agents-md.md`'s admission criteria name as the marker of a rule that can live
in a skill rather than in always-loaded context. The content is also too long for `~/AGENTS.md`:
three rules plus a verb vocabulary, two documented exceptions, a rename checklist and two wiring
traps. And it needs to reach repos that do not exist yet — `inv ai.install-skills` deploys it to
`~/.agents/skills/`, so a freshly generated project gets it without anything being copied in.

The counter-argument, recorded honestly: a skill only fires if its description matches, whereas
`~/AGENTS.md` is always loaded. `plans/2026-08-22-skill-trigger-quality-review.md` covers that risk
for this family's skills generally — the description here deliberately uses request-side vocabulary
("what to call", "rename", "tasks.py") rather than the internal jargon of the convention.
