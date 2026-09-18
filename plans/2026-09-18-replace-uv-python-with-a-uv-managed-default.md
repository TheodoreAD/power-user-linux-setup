---
status: in-progress
updated: 2026-09-19
source_repo: github.com-personal/repo-tasks
source_session: 14237e4b-3a66-4207-8a3a-882552c86680.jsonl
source_moment: 2026-09-18T09:40:00Z
source_plan: plans/2026-08-29-python-floor-in-the-shipped-configs.md
---

# The UV_PYTHON override defeats every library floor, and a uv-managed default replaces it

**Merged 2026-09-18 from `2026-09-13-uv-python-defeats-every-library-floor.md`**, which measured the
blast radius and asked four questions, and this file, which answered them. Both were written in the
same `repo-tasks` session (`source_moment` 2026-09-13 and 2026-09-18) and filed across, so neither
could be merged into the other by its author — the split was the cross-repo filing mechanism, not a
decision. That earlier name is recorded here because `plans.py archive --file` needs it to find the
merged-away file.

## Context

Two plans here already own halves of this and both have sat at `status: idea` since 2026-08-30:

- [`2026-08-30-uv-run-destroys-the-project-venv.md`](2026-08-30-uv-run-destroys-the-project-venv.md)
  — the mechanism, measured: `UV_PYTHON` outranks a project's `.python-version`.
- [`2026-08-29-python-floor-rule-in-the-global-agents-md.md`](2026-08-29-python-floor-rule-in-the-global-agents-md.md)
  — the rule's permanent home, blocked on which fragment owns it.

**This one adds what neither has: how far it has actually spread, and what to do about it.**

The rule, restated by the user 2026-09-13 in a `repo-tasks` session, unprompted and for at least the
second time:

> We need to make sure repo tasks stays at 3.11, since this is the minimum I use to work in some
> places. New apps on this machine and in my personal github.com account should be 3.14, but
> libraries and anything other projects might depend on in their venvs needs to stay 3.11.

That is the same rule recorded 2026-08-29 and quoted in both plans above. **A rule restated twice
with nothing enforcing it is the signal, not the statement.**

The principles the user gave 2026-09-18 while settling the family's Python version tiers, verbatim,
because each one decides something below. The tier rules themselves are
`scaffoldapy/plans/2026-09-18-python-version-tier-rules.md`.

> we would like to rely on the fewest requirements possible for consumers, since we don't have
> control there.

> for this machine I don't want special circumstances, so we can dogfood the experience.

> ideally we want the fewest possible system-level or user-level settings, and more per-script,
> per-repo or per-pyproject.

> setting the default python with uv is still a valid idea, since it's managed by uv and users don't
> need to do something extra.

> we must not rely on power user linux setup for our skills or mcps or libs to work.

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

### What the replacement measures

Measured 2026-09-18 on uv 0.11.19, all three paths uv resolves on:

| what is being resolved                                | `UV_PYTHON=3.14` | `uv python pin --global 3.14` |
| ----------------------------------------------------- | ---------------- | ----------------------------- |
| PEP 723 script, `requires-python = ">=3.9"`           | 3.14.5           | 3.14.5                        |
| PEP 723 script, `requires-python = "==3.11.*"`        | **3.14.5**       | 3.11.15                       |
| project, `requires-python = ">=3.11,<3.12"`           | 3.14.5           | 3.11.15                       |
| `uv tool install`, `requires-python = ">=3.11,<3.12"` | **3.14.5**       | 3.11.15                       |

The default is preserved in every unconstrained case and yielded in every declared one. That is the
whole of the change.

[PITFALL: **the variable is silent on the path where it does the most damage.** On the script path
uv at least prints
`warning: The requested interpreter resolved to Python 3.14.5, which is
incompatible with the script's Python requirement`
and proceeds. On the `uv tool install` path it prints nothing at all — the tool is simply built
against an interpreter it excluded, and fails later at import, somewhere with no connection to this
setting.]

## The answers

[DECISION: **replace the exported variable with `uv python pin --global`.** The variable is
`setup.toml`'s `[packages.uv-env]`, `zshenv = 'export UV_PYTHON="3.14"'`, deployed to
`~/.zshenv:14`. `uv python pin --global 3.14` writes `~/.config/uv/.python-version` instead —
uv-managed, which is the form the user named as still valid, and one fewer shell-level setting,
which is the direction they asked for. The measurement above is what makes it a swap rather than a
removal.]

[DECISION: **there is no clash with what uv does on install, which was the user's explicit
question.** Exactly one behaviour changes: a tool declaring it _cannot_ run on 3.14 is today
installed onto 3.14 anyway, and afterwards gets an interpreter it supports. Broken to correct.
Everything else is unaffected — a tool with no upper bound still gets 3.14, because uv already
prefers the newest interpreter its declaration allows. Measured: with nothing set at all, a `>=3.11`
package installs onto 3.14.5 unaided.

`settings.uv_python_default = "3.14"` and `uv_python_extra` are untouched by this. `bootstrap.sh`
greps `uv_python_default` to _install_ 3.14, which is a different job from exporting an override and
is the half worth keeping — it is what makes 3.14 present on a fresh machine.]

[DECISION: **this repo is application tier, 3.14, and its own declaration is the half that is
wrong.** Resolved by the user 2026-09-18, and it answers the third reading of the measurement above.
It declares `requires-python = ">=3.11"` and pins `.python-version` to `3.14` — the one outright
contradiction the family audit found. Nothing resolves this repo into anyone's environment, so 3.14
is right and the declaration moves to match the pin, not the other way round.]

[DECISION: **nothing this repo configures may be load-bearing for a skill, an MCP server or a
library.** The user's words: "we must not rely on power user linux setup for our skills or mcps or
libs to work." That is a scope rule rather than a task, and it is the general form of the bug this
plan fixes — a machine-level setting here was silently deciding what interpreter every published
artifact in the family was built against. Worth carrying into `contributing/` as a test applied when
adding any new machine-wide environment variable: if removing it would change how an artifact
behaves on a stranger's machine, it is in the wrong place.]

## What landed, 2026-09-19

Steps 2 and 3 of the direction below, in this repo, plus the writer bug that had to be fixed first.

- **`zsh.configure` could not take back a dropped field.** It visited only the dotfiles a package
  still declared, so deleting `uv-env`'s `zshenv` would have left `export UV_PYTHON` in `~/.zshenv`
  on every machine that had already run, with nothing left to remove it — the swap would have been
  inert where it mattered most. Now keyed on the declaration as well as on the machine, with the
  case under test.
- **`[packages.uv-env]` stops exporting the variable**; `inv python.pin-default` writes
  `~/.config/uv/.python-version` from `settings.uv_python_default` and runs in the packages phase,
  ahead of `install-tools`. `set_default` re-applies it instead of rewriting a second copy of the
  version into the file. Registered in `inv home.list-claims` as an EXTERNAL claim, the same class
  as a `skills`-CLI install: uv writes it, on this repo's instruction and with this repo's value.
- **`requires-python` is `>=3.14`**, matching the pin and the tier.

Applied to this machine and re-measured here, not only in the source session — `uv run` on a PEP 723
script declaring `==3.11.*` resolved **3.11.15** with the variable stripped and **3.14.5** with it
still set, while an unconstrained script stayed on 3.14.5 either way. Both halves of the claim, on
one machine, minutes apart.

[PITFALL: **a session started before the swap still carries the old value, and the shell files are
not where it comes from.** `~/.zshenv` loses the export the moment `inv zsh.configure` runs, and
this session's Bash calls still reported `UV_PYTHON=3.14` afterwards — the value was inherited from
the environment of the terminal Claude Code was launched in, which no dotfile edit reaches. So a
probe run from an existing session measures the state before the change unless it strips the
variable (`env -u UV_PYTHON …`), and a session that skipped that step would conclude the swap had
not worked. Same shape as the launch-directory `PATH` inheritance recorded in
`2026-09-18-direnv-never-fires-in-an-agent-bash-call.md`.]

Step 3 cost more than a one-line edit, which the now-retired addendum plan
`2026-09-18-raising-the-floor-goes-red-on-ruff-before-the-type-check.md` predicted and still
undershot. Its content is in `contributing/quality-tooling.md`, "Raising `requires-python` is a ruff
change before it is anything else" — the short version being that the floor raise reconfigures ruff
in the same commit, the type checker follows only on `inv configs.pull`, and the formatter silently
rewrites files whose own floor is lower.

## Still open

Two of the merged plan's four questions are answered above — whether the variable needs to be
machine-wide (no, a uv-managed pin replaces it) and which tier this repo is in (application, 3.14).
A third answered itself: the rule's permanent home does **not** block on any of this, since
`2026-08-29-python-floor-rule-in-the-global-agents-md.md` is blocked on an editorial question about
fragment ownership and the rule is true either way. One remains.

[NEEDS CLARIFICATION: **is a per-repo `.python-version` worth having once the variable is gone?**
`repo-tasks` has `inv venv.pin` / `venv.check` / `venv.recreate` already, and those are the working
parts — the file only becomes load-bearing when nothing outranks it, which is exactly the state this
plan creates. Answering it decides whether step 3 below is "recreate seven venvs" or "recreate seven
venvs and pin them", and the second is only worth it if something re-checks the pin later.]

## Recommended direction

1. **Give the rule its home**, since it is blocked on a filing decision rather than on evidence, and
   every session that has to re-derive it pays for its absence. The user has now had to state it
   twice out loud. Cheapest of the four and blocks nothing. **Still open** — it is the one step here
   that is an editorial decision rather than a defect, and
   `2026-08-29-python-floor-rule-in-the-global-agents-md.md` carries five open questions about the
   rule's wording, not just about which fragment owns it.
2. ~~**Swap the mechanism.**~~ **Done 2026-09-19** — see "What landed" above.
3. ~~**Fix this repo's own declaration** to `requires-python = ">=3.14"`.~~ **Done 2026-09-19**, at
   a cost the addendum plan only half predicted.
4. **Then the per-repo venvs**, which are one `inv venv.recreate` each and were worth nothing until
   step 2 landed. **The family can now be told it is safe to proceed**: six repos have plans filed
   carrying the same caveat, that their pin does not hold until this lands — `agent-skills`,
   `invoke-stubs`, the three `*-polite-mcp` servers and `ingesta`. `repo-tasks` is already correct
   and had to be fixed with an explicit `--python` to get there, which is the measurement that
   started this. **Each is another repo's session**, per the rule against writing into a tree this
   one does not own, so what is owed from here is telling them rather than doing it.

[UNVERIFIED: that `inv venv.recreate` in the six remaining repos would even pass their gates. It did
in `repo-tasks` — full gate green on 3.11.15, 691 tests — but that repo is the one that has been
type-checking at its floor since 2026-08-30. A repo that has never had anything run at 3.11 is
exactly where the `typing.override` class of finding lives, and finding some is the expected outcome
rather than a reason to stop.]

**Verified 2026-09-19, and the answer was yes with one correction.** The sweep — every shell startup
file, `/etc/environment`, `~/.config`, `~/.local/bin`, `.github/` and `docker/` — found exactly one
setter, `~/.zshenv:14`, and `inv zsh.configure` removed it cleanly once the writer bug above was
fixed (dry run: one line of work, the rest `ok`). The correction is that removing it from the file
does not remove it from a running session, per the pitfall above. `~/.agents/AGENTS.md`'s remaining
hits are documentation of uv's behaviour, which stays true and is now more relevant rather than
less.
