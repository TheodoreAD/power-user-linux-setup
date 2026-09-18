---
status: idea
updated: 2026-09-13
source_repo: github.com-personal/repo-tasks
source_session: 14237e4b-3a66-4207-8a3a-882552c86680.jsonl
source_moment: 2026-09-13T15:10:00Z
source_plan: plans/2026-08-29-python-floor-in-the-shipped-configs.md
---

# The library floor rule is defeated in 7 of 9 personal repos, by one line in setup.toml

## Context

Two plans here already own halves of this and both have sat at `status: idea` since 2026-08-30:

- [`2026-08-30-uv-run-destroys-the-project-venv.md`](2026-08-30-uv-run-destroys-the-project-venv.md)
  — the mechanism, measured: `UV_PYTHON` outranks a project's `.python-version`.
- [`2026-08-29-python-floor-rule-in-the-global-agents-md.md`](2026-08-29-python-floor-rule-in-the-global-agents-md.md)
  — the rule's permanent home, blocked on which fragment owns it.

**This file adds the one thing neither has: how far it has actually spread.** It is filed rather
than merged into either because it reports a measurement, and because the measurement is what turns
two ideas into a priority.

The rule, restated by the user 2026-09-13 in a `repo-tasks` session, unprompted and for at least the
second time:

> We need to make sure repo tasks stays at 3.11, since this is the minimum I use to work in some
> places. New apps on this machine and in my personal github.com account should be 3.14, but
> libraries and anything other projects might depend on in their venvs needs to stay 3.11.

That is the same rule recorded 2026-08-29 and quoted in both plans above. **A rule restated twice
with nothing enforcing it is the signal, not the statement.**

## Evidence

### The measurement

Read-only across `~/projects/github.com-personal`, 2026-09-13: each repo's `requires-python`, its
`.python-version` if it has one, and the version its existing `.venv` interpreter reports.

| repo                     | floor | pin  | venv    | packaged |
| ------------------------ | ----- | ---- | ------- | -------- |
| `agent-skills`           | 3.11  | —    | 3.14.5  | no       |
| `freshful-polite-mcp`    | 3.11  | —    | 3.14.5  | yes      |
| `ingesta`                | 3.14  | —    | 3.14.5  | yes      |
| `invoke-stubs`           | 3.11  | —    | 3.14.5  | yes      |
| `olx-polite-mcp`         | 3.11  | —    | 3.14.5  | yes      |
| `power-user-linux-setup` | 3.11  | 3.14 | 3.14.5  | yes      |
| `repo-tasks`             | 3.11  | 3.11 | 3.11.15 | yes      |
| `scaffoldapy`            | 3.11  | —    | 3.14.5  | no       |
| `temu-polite-mcp`        | 3.11  | —    | 3.14.5  | yes      |

`altex-polite-mcp`, `emag-polite-mcp` and `product-research-pipeline` carry no `pyproject.toml` and
no venv — nothing to measure, not an omission.

Three readings, in order of how much they cost:

1. **Seven of the nine develop above their own declared floor**, and `ingesta` is the only one
   entitled to, because it declares 3.14 and is therefore an application by the rule's own axis.
2. **`repo-tasks` is the only repo that matches, and only since today.** It was 3.14.5 an hour
   before this was written, despite pinning 3.11 in `9d4bd01`; `inv venv.recreate` fixed it in that
   session because `venv.recreate` passes `--python` explicitly, which is the one thing that
   outranks the variable.
3. **Two repos have a `.python-version` at all, and one of them contradicts itself** — this repo
   declares `requires-python = ">=3.11"` and pins its venv to **3.14**. Whichever tier it belongs
   to, those two lines cannot both be right, and it is the repo that sets the variable.

### The mechanism, already measured here

`setup.toml`'s `[packages.uv-env]` is `zshenv = 'export UV_PYTHON="3.14"'`, machine-wide, kept in
sync with `settings.uv_python_default` by `inv python.set-default`. uv treats an environment
variable as an **explicit interpreter request**, ranked above `.python-version`, so every `uv`
invocation that does not pass `--python` itself asks for 3.14 whatever the project declares.
`2026-08-30-uv-run-destroys-the-project-venv.md` has the isolated table, including the two rows that
matter: a 3.11-pinned venv destroyed and rebuilt at 3.14.5 with the variable set, and surviving
untouched with it unset.

[PITFALL: **the pin is not a weak defence, it is not a defence at all**, and it reads like one. A
repo with `.python-version` and a repo without are in exactly the same state here, which is why six
repos never bothered and the one that did (`repo-tasks`) still had a 3.14 venv two weeks later.
Anything that proposes "pin the floor per repo" as the fix is proposing what has already been tried
in the only repo that tried it.]

[PITFALL: **the failure is silent in the direction that matters.** Developing above the floor
produces no error at all — the suite passes, and the type checker agrees with it, because
`configs.pull` derives `pythonVersion` from `requires-python` and both then describe an interpreter
neither was asked to check. `repo-tasks` already has this recorded three times over, in
`plans/2026-08-25-consumer-transitions.md`: three consumers whose tests used `typing.override`
(3.12+) under a declared 3.11 floor, two of them in code shipped in the wheel. The floor is only
enforced where something actually runs at it.]

## Open questions

- **Does the variable need to be machine-wide at all?** Its stated purpose in `setup.toml` is
  "Default Python for all uv tool installs", and `uv tool install` has `--python`. A default that
  exists for tool installs is currently deciding every project venv on the machine, which is a much
  larger claim than the comment makes. Whether a narrower mechanism reaches the tool-install case
  without the project case is the question this plan exists to ask.
- **Which tier is this repo in?** It declares 3.11 and pins 3.14. If it is an application, the
  declaration is wrong; if it is a library, the pin is. Note it is also a `repo-tasks` consumer that
  pins `repo-tasks` in its own lock, so its venv is the one place the two floors meet.
- **Is `.python-version` worth having per repo once the variable is gone?** `repo-tasks` has
  `inv venv.pin` / `venv.check` / `venv.recreate` already, and those are the working parts — the
  file only becomes load-bearing when nothing outranks it.
- **Does the rule's permanent home block on any of this?** It should not:
  `2026-08-29-python-floor-rule-in-the-global-agents-md.md` is blocked on fragment ownership, which
  is an editorial question, and the rule is true whether or not the variable is fixed. Two weeks of
  both being open is itself the argument for unblocking the cheaper one first.

## Recommended direction

Nothing here is decided, and the ordering is the only real proposal:

1. **Give the rule its home**, since it is blocked on a filing decision rather than on evidence, and
   every session that has to re-derive it pays for its absence. Today's restatement is the second
   time a user has had to say it out loud.
2. **Then decide the variable**, with the table above as the blast radius rather than one repo's
   inconvenience.
3. **Then the per-repo venvs**, which are one `inv venv.recreate` each and are worth nothing until
   something stops them drifting back.

[UNVERIFIED: that `inv venv.recreate` in the six remaining repos would even pass their gates. It did
in `repo-tasks` — full gate green on 3.11.15, 691 tests — but that repo is the one that has been
type-checking at its floor since 2026-08-30. A repo that has never had anything run at 3.11 is
exactly where the `typing.override` class of finding lives, and finding some is the expected outcome
rather than a reason to stop.]
