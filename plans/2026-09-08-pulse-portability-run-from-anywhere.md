---
status: idea
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
| `allowlist.extract/classify/review/render/check-*/reconfirm/status` | authoring pipeline writing into `cli-allowlist/` in the repo |

`allowlist.apply` is the exception inside its own collection — it writes `~/.claude/settings.json`,
which is machine configuration and belongs in the tool. `devcontainer.check`, `print-exclude-tags`
and `print-mounts` serve someone setting up a container, so they stay. `home.list-claims` is a
read-only diagnostic and stays.

So **a collection-level filter cannot express this**, which is the finding that shapes the
implementation.

## Implementation, and what each piece costs

1. **Mark the development tasks where they are defined**, and derive both namespaces from one
   source. A module-level set naming that module's dev-only tasks, read by the shim's namespace
   builder, keeps the declaration next to the task it describes — so adding a task and forgetting
   the list is a one-file mistake rather than a two-file one. `inv` in the repo keeps showing
   everything; the shim shows everything minus the marked set. **Never two hand-maintained lists**:
   they drift, and the drift is silent in the same way the repo-tasks accident is.
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

## The name

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

[NEEDS CLARIFICATION: **where exactly the production line falls inside `allowlist`.** `apply` writes
machine configuration and clearly belongs; the other eight write into `cli-allowlist/` in the repo
and clearly do not. But `status` and `check-coverage` are read-only and answer "what would apply
do", which is a question a machine administrator asks. Splitting one collection across the line is
the first time this repo would do that, and it is worth deciding deliberately rather than by
whichever list gets written first.]

[NEEDS CLARIFICATION: whether the shim should refuse to run when the checkout has moved or is
missing. An editable install whose source directory is gone fails at import with a traceback, which
is the worst available message for the most likely long-run failure — a repo that was moved or
renamed. One early check naming the expected path costs a few lines and turns it into a sentence.]

[UNVERIFIED: whether `uv tool install --editable` survives a `uv self update` or a Python bump on
the tool venv. The probe covered install and invocation, not the upgrade path, and a tool that
silently stops resolving its own checkout after an unrelated upgrade is exactly the failure this
repo exists to prevent. Probe before shipping.]

## Recommended direction

1. **Done** — the `~/AGENTS.md` `inv -r` correction (`199ed92`), deployed. Independent of the rest.
2. **Decide the name.** Evidence is above and complete; nothing else is blocked on it, but every
   file the work touches will carry it.
3. **Build it in the order the costs fall**: mark the dev tasks where they are defined, add
   `tasks/cli.py` with an explicit production `Collection`, move `invoke` into `dependencies`, then
   the `setup.toml` install method, the `verify` check, and the allowlist pass.
4. **Probe the upgrade path** before it ships, per the `UNVERIFIED` above.
5. **Not a self-contained wheel, and never the global invoke config.**
