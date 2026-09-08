---
status: in-progress
updated: 2026-09-08
---

# A `uv tool` shim for PULSE's production tasks, and what to call it

**The ask, stated 2026-09-08:** PULSE's main/production invoke tasks installed as a `uv tool` with a
shim, callable like any other tool from anywhere. Running it must expose **none** of `repo-tasks`
and none of PULSE's own development tasks. Open question carried with the ask: the name, because
`pulse` might clash with PulseAudio.

Everything below was measured or probed on 2026-09-08 rather than reasoned about.

## What is already true, and it is more than expected

**PULSE's code is already location-independent.** Every repo-relative path in `tasks/` resolves from
`Path(__file__).parent.parent` — 24 sites across 11 modules, with not one `Path.cwd()` or
`os.getcwd()` in the package. No `c.run` in the repo invokes a repo-relative command: every
shelled-out command is a system tool (`apt`, `gsettings`, `uv`, `systemctl`, `docker`) or a path
derived from that same anchor. **So no task needs the process to be standing in the repo.**

The only thing binding PULSE to a directory is invoke's task discovery, which walks up from cwd —
and even that redirects with `-r`. Verified from a scratchpad:

| command                       | result                                                                       |
| ----------------------------- | ---------------------------------------------------------------------------- |
| `inv --list`                  | `Can't find any collection named 'tasks'!`, exit 1                           |
| `inv -r <repo> --list`        | the whole namespace — PULSE's 28 collections plus 8 borrowed                 |
| `inv -r <repo> deploy.status` | **executed correctly**, resolved every repo-side source, reported real drift |

That does not satisfy the ask — `-r` is not "callable like a regular tool", and it exposes
everything rather than the production subset — but it means **the shim is a packaging and namespace
job, not a portability one.** No task has to be rewritten.

[PITFALL: **`~/AGENTS.md` said no flag redirects `inv`, which is false and had been costing.** Fixed
2026-09-08 in `199ed92` and deployed: the clause now picks by what the task needs — `inv -r <repo>`
for a task that drives the machine, `cd <repo> && PATH=… inv` for one that runs the target repo's
own toolchain, since bare `pytest`/`ruff` resolve from the caller's PATH whatever `inv` was
launched. Two traps went in with it, both of which look like the shortcut and neither of which
announces itself: `INVOKE_TASKS_SEARCH_ROOT` is read after the collection has loaded and fails
exactly as if unset, and `tasks.search_root` in `~/.invoke.yaml` replaces cwd for **every** repo on
the machine.]

## The install shape: editable, and this is not a preference

`uv tool install` supports both, and the difference is total. Probed with a throwaway package built
to mirror this repo exactly — a `ptasks/` package in the wheel, a `setup.toml` and a `config/`
beside it at the project root, and `Path(__file__).parent.parent` at runtime — installed into a
redirected `UV_TOOL_DIR`/`UV_TOOL_BIN_DIR` so nothing touched `~/.local/bin`, then run from an
unrelated cwd:

| install                        | anchor resolves to                           | `setup.toml` | `config/frag.md` |
| ------------------------------ | -------------------------------------------- | ------------ | ---------------- |
| `uv tool install --editable .` | **the checkout**                             | read         | read             |
| `uv tool install .`            | `…/tools/<pkg>/lib/python3.14/site-packages` | **MISSING**  | **MISSING**      |

**Editable is the only shape that works, and the non-editable failure is silent.** The program ran,
exited 0, and simply found nothing — which for PULSE means `deploy.all` with no sources to deploy
and `util._CONFIG_PATH` with no `setup.toml`, each failing wherever its own call site happens to
check.

The deeper reason not to "fix" that by packaging `config/` and `setup.toml` as package data: PULSE's
job is deploying files **from a checkout you `git pull`** and reporting drift against it. Freeze
those into a wheel and `deploy.status` starts comparing the machine against a copy nobody edits, so
the whole drift model stops meaning anything. **The tool must stay anchored to the checkout, and
`--editable` is what does that.**

## The production boundary does not fall where it looks like it falls

The obvious split is PULSE's own 28 collections against the 8 borrowed from `repo-tasks` (`quality`,
`test`, `dev-env`, `docs`, `ci`, `deps`, `configs`, `agents`). Those 8 are unambiguously out — and
they would fall out **by accident** anyway, since a tool venv resolves only `dependencies` and
`repo-tasks` is a dev-group entry, so `tasks/__init__.py`'s existing graceful-degradation branch
would simply skip them.

**Relying on that accident is the trap.** It is invisible, it makes the tool's task list a property
of how it was installed rather than of what it declares, and one `uv tool install --with repo-tasks`
silently changes what the command means. The exclusion has to be declared.

And it does not stop at the repo-tasks line. Reading PULSE's own 28, the development tasks are
**inside** collections that are otherwise production:

| task                                                                | why it is development                                        |
| ------------------------------------------------------------------- | ------------------------------------------------------------ |
| `catalog.render-packages`, `catalog.render-tasks`                   | regenerate docs tables from `setup.toml`                     |
| `devcontainer.render-docs`                                          | regenerates a docs table                                     |
| `allowlist.extract/classify/review/render/check-man-deps/reconfirm` | authoring pipeline writing into `cli-allowlist/` in the repo |

`allowlist.apply`, `status` and `check-coverage` are the exceptions inside their own collection —
`apply` writes `~/.claude/settings.json`, which is machine configuration, and the other two are
read-only answers to "what would apply do" that need no checkout. `devcontainer.check`,
`print-exclude-tags` and `print-mounts` serve someone setting up a container, so they stay.
`home.list-claims` is a read-only diagnostic and stays.

So **a collection-level filter cannot express this**, which is the finding that shapes the
implementation.

## Implementation, and what each piece costs

1. **Mark the development tasks where they are defined**, and derive both namespaces from one
   source. **Built as a per-task marker rather than the per-module set this planned** —
   `@util.dev_only` applied directly under `@task`, which is one step better than a module-level
   list: there is no list to forget at all, the mark travels with the task through a rename or a
   move between modules, and `functools.update_wrapper` carries it onto the `Task` object for free.
   `inv` in the repo keeps showing everything; the shim shows everything minus the marked set.
   **Never two hand-maintained lists**: they drift, and the drift is silent in the same way the
   repo-tasks accident is.
2. **`tasks/cli.py`**, about fifteen lines: build the production `Collection`, hand it to
   `Program(namespace=…, version=…)`. Invoke supports this directly — `program.py:461` reads
   `if self.namespace is not None: self.collection = self.namespace`, skipping disk discovery
   entirely, so the shim never looks for a `tasks/` directory and never cares where it is run.
3. **`invoke` moves from the dev group to real `dependencies`.** A tool venv resolves only
   `dependencies`, and the entry point imports invoke, so without this the shim fails at import.
   Safe for everything else: `bootstrap.sh`'s zero-install path installs invoke as its own uv tool
   and never runs `uv sync`, and CI's `uv sync` already gets invoke from the dev group today.
4. **`setup.toml` needs a local-editable install method.** Existing `uv-tool` entries name a PyPI
   package; this one installs `--editable` from the checkout's own path. Either a field on `uv-tool`
   or a sibling method — the field is smaller and matches the ecosystem shape rule. The
   chicken-and-egg resolves itself: `bootstrap.sh` clones, `inv setup` runs, and the packages phase
   installs the shim from the repo it is already standing in.
5. **`verify.all` needs a check** for the new package — `<name> --list` is the natural one, and it
   is cheap and non-launching, unlike the GUI cases that plan documents.
6. **Allowlist**: a new `Bash(<name>:*)` family through `inv allowlist.review`. This is a saving
   rather than a cost — it replaces the `cd <repo> && inv …` chains that match no rule today.
7. **Docs**: `docs/tasks.md` and friends cite `inv <task>` 161 files deep. Nothing has to change,
   because `inv` in-repo keeps working — but the tool needs one page saying which entry point is
   which, or the two spellings become folklore.

## What landed, 2026-09-08

Built in five commits, in the order the costs fall:

| commit    | what                                                                           |
| --------- | ------------------------------------------------------------------------------ |
| `0b2d573` | `tasks/cli.py` and the production namespace, derived by subtraction            |
| `0b46fae` | `[project.scripts]`, `invoke` to a real dependency, `editable` in `setup.toml` |
| `94997c4` | the read-only permission grant on both shim names                              |
| `0002495` | `docs/tasks.md` and `AGENTS.md`                                                |
| `199ed92` | (earlier) the `~/AGENTS.md` `inv -r` correction                                |

Verified end to end from an unrelated directory, into a redirected `UV_TOOL_DIR` so the machine was
untouched: both shims report a version, `spowse --list` carries 26 collections plus `setup` with no
`quality`, `test` or `catalog`, and `spowse deploy.status` resolved all twelve deployed sources
against the checkout.

**The one design decision worth re-reading later**: both namespaces are derived from
`tasks.namespace` by subtraction, and each subtracted thing is recorded where it is created —
borrowed collections by the code that adds them, development tasks by `@util.dev_only` on the task
itself. A parallel list would have been smaller to write and would drift silently in the worse
direction. The membership is pinned by `tests/unit/test_cli.py`.

**Still open**: the machine install itself (`inv python.install-tools`, which upgrades every uv tool
on the machine, so it is the user's call) and the `agent-skills` question about `skill-authoring`'s
last step. The upgrade path was the third, and is answered below.

## The upgrade path survives everything, and the real failure is elsewhere

Probed 2026-09-08 against the same throwaway mirror — a `probepkg/` in the wheel, a `setup.toml` and
a `config/frag.md` beside it outside the wheel, `Path(__file__).parent.parent` at runtime — in a
redirected `UV_TOOL_DIR`/`UV_TOOL_BIN_DIR` so nothing on the machine moved. Every row was run, not
reasoned about; every one resolved the checkout and read both checkout-side files, including a
`setup.toml` edited **after** the install to prove the anchor was live rather than copied.

| operation                                           | anchor | checkout-side files |
| --------------------------------------------------- | ------ | ------------------- |
| `uv tool upgrade <pkg>` (no `--editable` passed)    | held   | read                |
| `uv tool upgrade --all`                             | held   | read                |
| `uv tool upgrade --reinstall <pkg>`                 | held   | read                |
| `uv tool upgrade -p 3.13` (Python bump down)        | held   | read                |
| `uv tool install --upgrade --python 3.14 …` (back)  | held   | read                |
| a **newer uv** (0.12.10) upgrading a 0.11.19 env    | held   | read                |
| a newer uv doing the Python bump on that env        | held   | read                |
| an **older uv** (0.11.19) taking over a 0.12.10 env | held   | read                |

**Two mechanisms make it robust, and neither one is uv at runtime.** The receipt records editability
as data rather than as a flag of the moment —
`requirements = [{ name = "…", editable = "/home/…/power-user-linux-setup" }]` — so
`uv tool upgrade` re-applies it with nothing passed on the command line. And what the venv actually
contains is a **bare-path `.pth`**: `_editable_impl_power_user_linux_setup.pth` holds the checkout
path and nothing else, so resolution is CPython's own `site` machinery, with no import hook and no
uv code in the path. A `uv self update` replaces a binary that is not involved when the tool runs.

The `uv self update` half is not hypothetical here: this machine is on **0.11.19** and the current
release is **0.12.10** (2026-09-04), so the pending update crosses a minor boundary. That is the
boundary the table above tests, in both directions and from a clean slate created by each version.

A Python bump rebuilds the venv rather than patching it — `pyvenv.cfg`'s `home` moves to the new
interpreter and the `.pth` is rewritten to the same checkout path. `home` also points at uv's
minor-version symlink (`cpython-3.14-linux-x86_64-gnu`), not the patch directory, so a 3.14.5 →
3.14.6 refresh does not invalidate an existing tool venv at all.

[PITFALL: **the failure this `UNVERIFIED` was guarding against does not exist; a different one does,
and it is the checkout moving.** With the source directory renamed, the tool does not degrade — it
dies at import with `ModuleNotFoundError: No module named 'tasks'` and a traceback naming the
console script, never the missing path and never this repo. `tasks` is generic enough that the
message reads as a broken Python install rather than as a moved directory. uv's own diagnosis is the
good one and is on the wrong command: `uv tool upgrade` refuses with
`Distribution not found at: file:///…/power-user-linux-setup`, exit 1 — the full path, but only for
someone who already suspected the cause. Running `spowse` is what a person does; running
`uv tool upgrade` is not.]

## The name

**Decided `spowse`, with `spouse` as a second console script at the same entry point.**

> **S**ensible **POW**er-user **SE**tup

Same construction as **P**ower **U**ser **L**inux **SE**tup, with no filler word — the `SE` comes
from `SEtup` in both. `spouse` is a homophone, so the misspelling is guaranteed rather than
hypothetical; a second `[project.scripts]` entry costs one line and turns a recurring
`command not found` into nothing at all. `spowse` is canonical in docs, `setup.toml` and the
allowlist.

The metaphor is the domain rather than decoration: this tool's job is `$HOME`, and a spouse keeps
the house in order and tells you what has drifted out of place, which is what `spowse deploy.status`
literally does.

[DECISION: **`pulse` was recommended and then withdrawn, and the reason is a collision this repo has
already been bitten by.** The first recommendation rested on a real finding — no package ships a
bare `pulse` binary, PulseAudio's own executables are `pulseaudio` and the `pa*` family, and this
machine runs PipeWire — so the _command_ namespace is genuinely free. What that missed is in
`tasks/util.py` beside `PULSE_CONFIG_DIR`: `~/.config/pulse` **is** PulseAudio's own config
directory, PULSE's state collided with it silently, and `eee0cf6` (2026-08-13) renamed this repo's
config and state dirs to the full repo name to escape it. Confirmed live — that directory holds a
card database, a cookie and default-sink files dating to 2020. The command namespace and the XDG
config namespace are different namespaces, so the original finding stands on its own terms; but a
repo that deliberately renamed away from `pulse` should not then name its binary `pulse`, and the
shim's own natural config path is the occupied one. Names screened after that: about sixty across
six themes, filtered on PATH, apt and PyPI. `fettle` (best meaning) lost to a live 2026 PyPI package
doing devcontainer scaffolding; `monty` (best pun — "the full monty" plus Monty Python) lost to an
active 129-release PyPI package; `pumas` (**P**ower **U**ser **MA**chine **S**etup) was a clean
backronym but a plural, adjacent to `puma` the app server, and not actually wordplay; `powerset`
lost to the pre-owned mathematical meaning. `spowse` was the user's, and it is the only candidate
that is a backronym **and** a joke.]

**The clash is nominal, not actual.** Checked on this machine and against the archive:

- **No package ships a bare `pulse` binary.** PulseAudio's own executables are `pulseaudio`,
  `pactl`, `pacmd`, `paplay`, `parec`; the apt names are `pulseaudio*`, `pulsemixer`, `pulseview`,
  `pulseeffects`. Nothing is called `pulse`.
- **PulseAudio is not even installed here.** This machine runs PipeWire (`pipewire`,
  `pipewire-pulse`), whose CLIs are `pw-*` and `wpctl`.
- **This repo already owns the `pulse` namespace on this machine**: it deploys
  `~/.local/bin/pulse-proxy-start`, ships `pulse-proxy.service`, and its own env vars are
  `PULSE_DRY_RUN` and `PULSE_EXCLUDE_TAGS`.

Against that, three real if minor risks: tab-completion and muscle memory sit next to `pulseaudio`
for anyone who has it installed; a future Debian package could take the name; and PyPI has a dormant
`pulse` project (0.1.2, a WSGI middleware), which cannot collide with a path install but would if
anyone ever typed `uv tool install pulse`.

**`pulse-setup` is specifically ruled out**, and by this machine's own naming rule, which uses this
exact alias as its worked example of what not to do: the full canonical name or a genuine short
form, never a compound that half-repeats the disambiguating word. The same rule permits a short form
"where the full name is genuinely unwieldy" — `power-user-linux-setup` as something you type daily
qualifies.

[NEEDS CLARIFICATION: **`pulse`, or a name with no overlap at all?** `pulse` is consistent with
every other artefact this repo already installs and collides with nothing that exists. A
zero-overlap alternative buys immunity from a package that does not exist yet and from confusion in
a `pulseaudio`-installed environment, at the cost of a name that matches nothing else in the repo.
The decision is the user's; the evidence above is all of it.]

## Alternatives considered, and why they lose to the shim

- **`inv -r <repo> <task>`** — works today, zero code, but it is not a tool: the path is typed every
  time, it exposes the whole namespace including `quality` and `test`, and the leading global option
  changes the command prefix so every call misses the 13 `Bash(inv …)` allowlist rules and prompts.
- **A shell wrapper** (`exec inv -r "$PULSE_ROOT" "$@"`) through the existing `wrapper-script`
  method — two lines, declared, tracked by `deploy.status`. Cheaper than the shim and it does fix
  discoverability, but it inherits the whole namespace, so it cannot satisfy the "no repo-tasks, no
  development tasks" half of the ask. It is the fallback if the namespace work is deferred.
- **A global `~/.invoke.yaml` with `tasks.search_root`** — never. It works, which is the danger:
  `search_root` replaces cwd as the discovery start for every repo on the machine, so `repo-tasks`,
  `scaffoldapy` and the `*-polite-mcp` family would all load PULSE's tasks instead of their own.

## What the shim is worth, measured

Counted over the harness's ~30-day transcript window: every session in another repo that reached for
a PULSE task by `cd`-ing into the checkout. **16 occurrences, 6 sessions, 3 repos** — `agent-skills`
12, `repo-tasks` 3, `olx-polite-mcp` 1.

| what was typed          | count | note                                       |
| ----------------------- | ----: | ------------------------------------------ |
| `inv ai.install-skills` |    12 | the skill installer, after editing a skill |
| `inv ai.skills`         |     2 | **no such task**                           |
| `inv --list`            |     1 | looking for the name                       |
| `inv ai.init`           |     1 | **no such task**                           |

Two a week is thin. **A quarter of the attempts failing on a guessed task name is not** — three
named tasks that do not exist and one was a bare `inv --list` hunting for the name, from outside the
checkout where that does not work. A tool on PATH answers that with `<name> --list`.

[DECISION: **chasing the cheap version of that fix found something else, and it is filed
elsewhere.** The obvious move was to name the command in `skill-authoring`'s last step. That step
already names a command — `npx skills add <owner>/<repo> --global` — and never mentions PULSE. So
twelve sessions overrode their own loaded skill in favour of a task that also creates the
`.claude/skills` symlink the `skills` CLI announces and does not create. Whether that is correct
decides whether the measured need is sixteen or four. It belongs to `agent-skills`, and is filed
there as `2026-09-08-skill-authoring-reinstall-step-is-contested.md`. **It does not block the shim**
— the ask is for a tool, not for a fix to that rate — but it should be answered before the rate is
ever cited as the shim's justification.]

## Open questions

[DECISION: **`allowlist` splits three to six — `apply`, `status` and `check-coverage` ship.**
`apply` writes `~/.claude/settings.json`, which is machine configuration; `status` and
`check-coverage` are read-only and answer "what would apply do", which is a machine-administration
question that needs no checkout. The other six write into `cli-allowlist/` in the repo. This is the
first collection this repo splits across the line, which is exactly why `AGENTS.md` names it as the
worked example — the boundary is per task, and reading the namespace name alone gets it wrong.]

[NEEDS CLARIFICATION: whether the shim should refuse to run when the checkout has moved or is
missing. This was speculative when written and the probe above has made it **the only failure mode
left** — every upgrade path holds the anchor, so a moved or renamed checkout is what actually breaks
`spowse`, and it breaks it with `ModuleNotFoundError: No module named 'tasks'`. The fix is small and
the placement is the question: a `try/except ImportError` in the console-script path cannot work
(the failure is the import of `tasks.cli` itself, before any of our code runs), so it has to be
either a check inside `tasks/cli.py:main` for the checkout-side files it needs — which catches a
partially-moved tree but not a missing one — or a generated wrapper that tests the path before
exec'ing. Worth deciding now that it is no longer one risk among several.]

## Recommended direction

1. ~~The `~/AGENTS.md` `inv -r` correction~~ — **done**, `199ed92`, deployed.
2. ~~Decide the name~~ — **done**, `spowse` with the `spouse` alias.
3. ~~Build it~~ — **done**, four commits, gate green throughout and verified from an unrelated
   directory. `verify.all` needed no override: the convention default is `<check_cmd> --version`,
   and invoke's `Program` answers that from `[project] version`.
4. **Install it on this machine.** `inv python.install-tools` is the declared path and it upgrades
   every other uv tool as it goes, so it is the user's call rather than a side effect of this work.
   `inv ai.install-skills` applies the permission grant in the same way.
5. ~~Probe the upgrade path~~ — **done**, and it is clean in every combination tried, including
   across the 0.11 → 0.12 uv boundary this machine has pending. What it turned up instead is that a
   **moved checkout** is the one real failure, with the worst available message; decide the guard.
6. **Answer the `agent-skills` question**, which decides whether the measured need was sixteen
   reaches or four. It does not change anything already built.
7. **Not a self-contained wheel, and never the global invoke config.**
