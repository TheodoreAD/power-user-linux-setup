---
status: idea
updated: 2026-09-08
---

# Making PULSE runnable from anywhere: what it costs, and whether it is worth it

## The finding that reframes the question

**PULSE's code is already location-independent.** Every repo-relative path in `tasks/` resolves from
`Path(__file__).parent.parent` — 24 sites across 11 modules, checked 2026-09-08, with not one
`Path.cwd()` or `os.getcwd()` anywhere in the package. And no `c.run` in the repo invokes a
repo-relative command: every shelled-out command is a system tool (`apt`, `gsettings`, `uv`,
`systemctl`, `docker`) or a path derived from that same `__file__` anchor. Nothing in PULSE's own
task set reads the process's working directory.

What binds PULSE to a directory is exactly one thing: **invoke's task discovery**, which walks up
from cwd looking for a `tasks/` package.

And that already has a flag. Verified live from a scratchpad directory, 2026-09-08:

| command                       | result                                                                       |
| ----------------------------- | ---------------------------------------------------------------------------- |
| `inv --list`                  | `Can't find any collection named 'tasks'!`, exit 1                           |
| `inv -r <repo> --list`        | the whole namespace — PULSE's 28 collections plus 8 borrowed                 |
| `inv -r <repo> deploy.status` | **executed correctly**, resolved every repo-side source, reported real drift |

So "PULSE needs to be run from a directory" is false as stated. The accurate version is narrower and
more annoying: **`inv` needs to be told where the tasks are, and `~/AGENTS.md` says there is no way
to tell it.**

[PITFALL: **the rule is wrong, and sessions have been paying for it for weeks.** `~/AGENTS.md`'s
"Running a command against a different repo" says: _"`inv` is the exception: invoke finds `tasks.py`
by walking up from cwd, **so no flag redirects it**"_. `-r`/`--search-root` redirects it, and has
since invoke 1.0. The rest of that clause is right, and is why the mistake is easy to make:
`inv -r <other repo> quality.precommit` loads the right tasks and then shells out to bare
`pytest`/`ruff`, which resolve from the **caller's** PATH — so the dev-loop half genuinely does need
`cd` plus a PATH prefix. The clause generalised a true statement about eight borrowed collections
into a false one about the mechanism. **Correcting it is a one-line edit to
`config/agents-md/bash.md` and is worth more than anything else in this plan, because it is free and
it is the thing that has actually been costing.**]

## The split that decides everything else

PULSE's namespace has two halves, and only one of them wants portability.

- **Machine administration — 28 collections, PULSE's own.** `deploy`, `ai`, `tools`, `apt`,
  `verify`, `gnome`, `certs`, `proxy`, `allowlist`, … These act on the machine, take their inputs
  from the repo through the `__file__` anchor, and shell out to system tools. **Already portable**;
  they only need discovery pointed at the checkout.
- **The dev loop — 8 collections borrowed from `repo-tasks`.** `quality`, `test`, `dev-env`, `docs`,
  `ci`, `deps`, `configs`, `agents`. These run `ruff .`, `pytest`, `dprint fmt` against the working
  directory and resolve their tools from PATH. **Not portable, and should not be** — running this
  repo's gate is work done in this repo, and `~/AGENTS.md` already routes substantial cross-repo
  work to its own session.

Everything below is about the first half only. Making the second half portable is not a goal that
survives being stated.

## What the need actually is, measured

Counted over the harness's ~30-day transcript window, 2026-09-08: every session in another repo that
reached for a PULSE task by `cd`-ing into the checkout.

**16 occurrences, 6 sessions, 3 repos** — `agent-skills` 12, `repo-tasks` 3, `olx-polite-mcp` 1.
Roughly two a week, and lopsided:

| what was typed          | count | note                                       |
| ----------------------- | ----: | ------------------------------------------ |
| `inv ai.install-skills` |    12 | the skill installer, after editing a skill |
| `inv ai.skills`         |     2 | **no such task**                           |
| `inv --list`            |     1 | looking for the name                       |
| `inv ai.init`           |     1 | **no such task**                           |

Two things fall out of that table, and the second is the more interesting.

**The need is one task.** Twelve of sixteen are `ai.install-skills`, and the shape is always the
same: a session edits a skill in `agent-skills`, pushes it, and has to re-install it from PULSE
because PULSE owns the installer. That is the `skill-authoring` sequence's last step crossing a repo
boundary by design.

**Four of sixteen were the session not knowing what to type.** Three named tasks that do not exist
(`ai.skills` twice, `ai.init` once) and one was a bare `inv --list` hunting for the name. From
outside the checkout there is no cheap way to ask what PULSE can do — which is a **discoverability**
failure wearing portability's clothes, and it is the half a wrapper actually fixes. A quarter
failure rate on a two-a-week operation is a better argument than the two-a-week is.

## The options, and what each costs

### A — `inv -r <repo> <task>`. Zero code, works today.

Costs a 60-character path per call, and one thing that is not obvious: **the allowlist stops
matching.** `~/.claude/settings.json` carries 13 `Bash(inv …)` rules, matched on literal command
prefix, and a global option before the verb changes the prefix — the same trap `~/AGENTS.md`
documents for `git -C x push`. So every from-anywhere PULSE call prompts, every time, on a machine
whose whole allowlist pipeline exists to stop that.

Fixable by rendering `Bash(inv -r:*)`-shaped rules, which is one `inv allowlist.review` pass.
Nothing else changes; `inv <task>` in-repo keeps working unaltered.

### B — a `pulse` wrapper on PATH, deployed by `setup.toml`. Recommended.

Two lines of shell — `exec inv -r "${PULSE_ROOT}" "$@"` — shipped through the existing
`method = "wrapper-script"` mechanism (`dest = "~/.local/bin/pulse"`,
`content_file = "config/pulse.sh"`), which means `deploy.status` tracks it, `deploy.all` redeploys
it, and it is declared rather than hand-installed like everything else on this machine.

- **The repo path is the one real design question.** Hard-coding it is wrong — the clone's location
  is the user's choice and the repo is meant to work on a fresh machine. Read `PULSE_ROOT` from the
  environment, exported by the same `zshenv` field that already ships `SUDO_ASKPASS` for
  `[packages.askpass-zenity]`, with the installer writing the path it just cloned into.
- **It fixes the discoverability quarter**, which `-r` does not: `pulse --list` from anywhere is a
  one-word answer to the question three sessions guessed wrong.
- **Allowlist**: one new tool to classify and a `Bash(pulse:*)` family to render — exactly what
  `cli-allowlist/` is for, and cheaper than the `inv -r` prefix rules option A needs anyway.
- **The cost is a second name.** `inv <task>` in-repo, `pulse <task>` outside, for one task set. The
  family convention prefers one mandatory identical composite over a menu — though this is two
  situations rather than two choices, which is the case that convention exempts. Worth stating in
  the docs as "same tasks, two entry points, and which one you use is decided by where you are", not
  as two commands.

### C — a real console script, `pulse = "tasks.cli:program.run"`. Do not.

Invoke supports it directly and cleanly: `Program(namespace=namespace)` skips disk discovery
entirely (`invoke/program.py:461` —
`if self.namespace is not None: self.collection = self.namespace`). About fifteen lines and a
`[project.scripts]` entry. Installed with `uv tool install --editable <repo>`, the `__file__` anchor
still points at the checkout, so `config/`, `setup.toml` and `cli-allowlist/` resolve with **no
packaging work at all**.

It fails on something else:

[PITFALL: **the tool venv would silently publish a different task set under the same name.**
`dependencies = []` and `repo-tasks` is a dev-group dependency, so a `uv tool install` of this
project resolves without it — and `tasks/__init__.py` degrades gracefully by design, returning Nones
and skipping those collections rather than erroring. So `pulse --list` would show 28 collections
where `inv --list` shows 36, with nothing anywhere saying why, and `pulse quality.precommit` would
be "no idea what that is". Fixing it means moving `invoke` and `repo-tasks` into real
`dependencies`, which changes what `uv sync` installs and what CI resolves for a repo that currently
declares none. One command name meaning two things depending on how it was reached is worse than
either shape chosen whole.]

And the shape is wrong on its own terms: a console script is what a tool you **ship** looks like.
PULSE has one consumer and its entire value is that it is a checkout you `git pull` — option B's
wrapper delegates to that checkout, while C dresses it as a distributable it is not.

### D — a global `~/.invoke.yaml` with `tasks.search_root`. Never.

Written down so nobody re-derives it as the obvious answer. It **would** work — user config files
are loaded by `create_config()` before `parse_collection()`, unlike the shell environment — and that
is precisely what makes it dangerous. `search_root` **replaces** cwd as the discovery start
(`invoke/loader.py:114-121`), so every other repo on this machine — `repo-tasks`, `scaffoldapy`, the
`*-polite-mcp` family, `ingesta` — would load PULSE's tasks instead of its own. A machine-wide
setting that breaks every project except one.

[PITFALL: **`INVOKE_TASKS_SEARCH_ROOT` looks like the answer and silently does nothing.** Tested
2026-09-08 from outside the repo: same `Can't find any collection named 'tasks'!`, exit 1, no
warning that the variable was seen and ignored. The config key exists, the env var name is derived
correctly (`INVOKE_` + the nested path), and the value is read **too late to matter** —
`Program.run` calls `create_config()` and then `parse_collection()`, while `load_shell_env` is
documented in `invoke/config.py` as "intended for execution late in a `Config`'s lifecycle" and
lands after the collection is already loaded. An hour is available to anyone who assumes the env var
works because the key is real.]

## Is it worth it

**The free half, yes, immediately**: the `~/AGENTS.md` clause is wrong, one line fixes it, and it is
the only item here that has demonstrably been costing something.

**The wrapper, probably — but on the discoverability argument, not the frequency one.** Two calls a
week saved ten seconds each does not pay for a new entry point, a docs paragraph and an allowlist
pass. A quarter of those calls failing on a guessed task name is a different claim, and
`pulse
--list` answers it in a way `cd` never will. If the wrapper is built, that is the reason to
record for it.

**The cheapest option is not on the list above — and checking it turned up something better than a
cheap fix.** Twelve of sixteen reaches are one task from one repo, so the obvious move was to name
the command in `skill-authoring`'s last step and be done. Checked 2026-09-08: **that step names
`npx skills add <owner>/<repo> --global`, not `inv ai.install-skills`.** Nothing in the documented
sequence mentions PULSE at all.

So twelve sessions crossed a repo boundary to run a task their own loaded skill did not tell them
about, and three more guessed at its name. That is not a discoverability gap inside PULSE; it is
**two commands competing for one step**, and the sessions picked the one the skill does not name.
They may well have been right to: `ai.install-skills` also creates `~/.agents/skills/` and the
`.claude/skills` symlink, which is the gap this repo exists to cover because the `skills` CLI
announces it and does not create it. If that is the reason, the documented step is the one that is
wrong, and a `pulse` wrapper would be paving a path that should not be walked.

**That has to be settled before anything is built**, and it is not settleable here:
`skill-authoring` lives in `agent-skills`, and a session in this repo does not edit that one. File
it there.

## Open questions

[DECISION: **the "just name the command in the skill" fix is unavailable, and the reason is worth
more than the fix would have been.** `skill-authoring`'s step 6 names `npx skills add … --global`.
Twelve of the sixteen measured cross-repo reaches ran `inv ai.install-skills` instead, and three
guessed at its name — so the sessions were not failing to follow their instructions, they were
overriding them, consistently, in favour of a command that does one thing more. Whether that is
correct decides whether this plan has a problem to solve at all: if PULSE's task is the right step,
`skill-authoring` should say so and the from-anywhere need is real and recurring; if
`npx skills add` is the right step, twelve of the sixteen data points are sessions doing something
unnecessary and the measured need drops to four.]

[NEEDS CLARIFICATION: **which command is the canonical last step of the skill-authoring sequence?**
The case for `inv ai.install-skills` is the symlink gap — `~/AGENTS.md` and this repo's `AGENTS.md`
both record that the `skills` CLI announces a Claude Code symlink it does not create, and that PULSE
covers exactly that. The case for `npx skills add` is that it is one mechanism deep, needs no
checkout, and is what the skill already says. Belongs in `agent-skills` as the repo owning that
skill; this plan cannot answer it and must not edit it.]

[NEEDS CLARIFICATION: whether `PULSE_ROOT` should be exported by `zshenv` or discovered. Exporting
it is the mechanism this repo already uses and is honest about being machine state; discovering it
(a marker file, a well-known clone path) re-invents what the environment already knows. Leaning
exported — but the installer has to write it, which means the wrapper does not work until the next
shell, and that is a first-run wart worth deciding about rather than discovering.]

[UNVERIFIED: the 16-occurrence count is from a `cd <path> && inv` grep over ~30 days of transcripts,
so it misses any cross-repo reach spelled some other way, and misses everything the user did outside
an agent session. It is a floor. It is also skewed by the retention window rather than the habit —
the harness keeps 30 days, and PULSE is older than that.]

## Recommended direction

1. **Correct the `~/AGENTS.md` clause** — `config/agents-md/bash.md`, one line: `-r`/`--search-root`
   does redirect invoke's discovery, and the reason the `cd` form is still needed for another repo's
   gate is PATH resolution of `pytest`/`ruff`, not discovery. Free, independent of everything below,
   and it is the actual bug this plan found.
2. **File the canonical-step question in `agent-skills`**, where `skill-authoring` lives. It decides
   whether the measured need is sixteen reaches or four, and therefore whether steps 3 and 4 have
   anything to pay for.
3. **Then B, if 1 and 2 do not close it**: the `pulse` wrapper through `wrapper-script`, sold on
   discoverability rather than on two calls a week, with `PULSE_ROOT` from `zshenv` and one
   allowlist pass.
4. **Not C, and never D.**

Nothing here is worth doing in the order it was discovered: the portability question was the ask,
and the two things worth acting on are a wrong sentence in `~/AGENTS.md` and a contested step in
another repo's skill. The portability itself was already there behind a flag.
