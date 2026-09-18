# `spowse`: the machine-administration entry point

Design rationale behind the `uv tool` shim that makes PULSE's production tasks callable from
anywhere. [`docs/tasks.md`](../docs/tasks.md) is the user-facing page — which entry point is which,
and what each one carries. `AGENTS.md`'s "Two entry points" section carries the rule a contributor
needs when adding a task. This page keeps what neither has room for: why the name, why `--editable`
is not a preference, and what was measured before any of it was built.

## The portability half was already done, and nobody knew

The ask was for PULSE's tasks to run from anywhere. Measured 2026-09-08 before anything was written:
**every repo-relative path in `tasks/` already resolves from `Path(__file__).parent.parent`** — 24
sites across 11 modules, with not one `Path.cwd()` or `os.getcwd()` in the package, and no `c.run`
invoking a repo-relative command. No task needs the process to be standing in the checkout.

The only thing binding PULSE to a directory was invoke's task discovery, which walks up from cwd —
and even that redirects with `inv -r <repo>`, verified to execute correctly and resolve every
repo-side source from an unrelated directory.

**So the shim was a packaging and namespace job, not a portability one**, and no task had to be
rewritten. Establishing that first is what kept the change to five commits; a session that had
assumed otherwise would have gone looking for cwd dependencies that were never there.

## `--editable` is load-bearing, and the failure is silent

Probed with a throwaway package built to mirror this repo exactly — a package in the wheel, a
`setup.toml` and a `config/` beside it at the project root, `Path(__file__).parent.parent` at
runtime — installed into a redirected `UV_TOOL_DIR`/`UV_TOOL_BIN_DIR` so nothing touched
`~/.local/bin`, then run from an unrelated cwd:

| install                        | anchor resolves to                           | `setup.toml` | `config/`   |
| ------------------------------ | -------------------------------------------- | ------------ | ----------- |
| `uv tool install --editable .` | **the checkout**                             | read         | read        |
| `uv tool install .`            | `…/tools/<pkg>/lib/python3.14/site-packages` | **missing**  | **missing** |

**The non-editable build ran, exited 0, and simply found nothing** — which for PULSE means
`deploy.all` with no sources to deploy and `util._CONFIG_PATH` with no `setup.toml`, each failing
wherever its own call site happens to check.

The obvious fix — package `config/` and `setup.toml` as package data — is the wrong one, and for a
reason specific to what this repo is. PULSE deploys files **from a checkout you `git pull`** and
reports drift against it. Freeze those into a wheel and `deploy.status` starts comparing the machine
against a copy nobody edits, so the drift model stops meaning anything. The tool has to stay
anchored to the checkout, and `--editable` is what does that.

[PITFALL: **that rejection answers a question about the developer, and it was later cited against a
different user.** Re-examined 2026-09-18 while moving the clone destination. The drift model matters
to somebody who _edits_ `config/`; a consumer overrides through
`~/.config/power-user-linux-setup/overrides.toml` and never touches it, and for them "compare
against the version I installed" is arguably the correct semantics rather than a degradation. So a
non-editable `uv tool install power-user-linux-setup@git+…` with the config as package data — no
clone at all, `uv tool upgrade` as the update path — is not refuted by the paragraph above, and it
is the shape that matches "like every other user-wide tool" most literally.

It still loses, on cost rather than on principle: two install shapes to maintain and test,
`bootstrap.sh` and `tasks/netdoctor.py` still need a tree to run from before uv exists so the
one-liner would keep cloning something anyway, and the consumer loses the ability to inspect or
patch `config/` locally on a machine-setup tool. Revisit if consumer installs ever outnumber
developer ones — but revisit it on those grounds, not by re-reading the paragraph above as though it
had already settled the question.]

### The anchor survives every upgrade path tried

Probed 2026-09-08 against the same mirror, every row run rather than reasoned about, including a
`setup.toml` edited **after** the install to prove the anchor was live rather than copied:

| operation                                        | anchor | checkout-side files |
| ------------------------------------------------ | ------ | ------------------- |
| `uv tool upgrade <pkg>` (no `--editable` passed) | held   | read                |
| `uv tool upgrade --all`                          | held   | read                |
| `uv tool upgrade --reinstall <pkg>`              | held   | read                |
| `uv tool upgrade -p 3.13`, then back to 3.14     | held   | read                |
| a newer uv (0.12.10) upgrading a 0.11.19 env     | held   | read                |
| an older uv (0.11.19) taking over a 0.12.10 env  | held   | read                |

**Two mechanisms make it robust, and neither is uv at runtime.** The receipt records editability as
data rather than as a flag of the moment — `requirements = [{ name = "…", editable = "<path>" }]` —
so `uv tool upgrade` re-applies it with nothing on the command line. And the venv holds a
**bare-path `.pth`** containing the checkout path and nothing else, so resolution is CPython's own
`site` machinery with no import hook and no uv code in the path. A `uv self update` replaces a
binary that is not involved when the tool runs. A Python bump rebuilds the venv rather than patching
it, and `pyvenv.cfg`'s `home` points at uv's minor-version symlink, so a patch-level refresh does
not invalidate an existing tool venv at all.

[PITFALL: **the failure that was expected does not exist; the one that does is the checkout moving,
and it has the worst available message.** With the source directory renamed the tool does not
degrade — it dies at import with `ModuleNotFoundError: No module named 'tasks'` and a traceback
naming the console script, never the missing path and never this repo. `tasks` is generic enough
that it reads as a broken Python install. uv's own diagnosis is the good one and is on the wrong
command: `uv tool upgrade` refuses with `Distribution not found at: file:///…` and the full path —
but running the shim is what a person does, and running `uv tool upgrade` is not. `tasks/cli.py`'s
`_require_checkout` covers the half reachable from inside the package: a checkout that exists but no
longer holds `setup.toml`/`config/`. A checkout that is **gone** fails before any of our code runs
and is out of reach without a second artefact between the console script and the program, which was
judged not worth the drift.]

## The production boundary does not fall where it looks like it falls

The obvious split is PULSE's own collections against the eight borrowed from `repo-tasks`. Those
eight are unambiguously out — and they would fall out **by accident** anyway, since a tool venv
resolves only `dependencies` and `repo-tasks` is a dev-group entry, so `tasks/__init__.py`'s
existing graceful-degradation branch would skip them.

**Relying on that accident is the trap.** It is invisible, it makes the tool's task list a property
of how it was installed rather than of what it declares, and one `uv tool install --with repo-tasks`
would silently change what the command means. The exclusion has to be declared.

And it does not stop at the `repo-tasks` line: the development tasks are **inside** collections that
are otherwise production. `catalog.render-*` and `devcontainer.render-docs` regenerate docs tables;
six of the nine `allowlist` tasks write into `cli-allowlist/` in the checkout while `apply`,
`status` and `check-coverage` are machine administration. **A collection-level filter cannot express
that**, which is the finding that shaped the implementation — hence a per-task `@util.dev_only`
marker rather than a per-module list. There is no list to forget, and the mark travels with the task
through a rename or a move between modules.

[DECISION: **never two hand-maintained lists.** Both namespaces are derived from `tasks.namespace`
by subtraction, and each subtracted thing is recorded where it is created — borrowed collections by
the code that adds them, development tasks by the decorator on the task itself. A parallel list
would have been smaller to write and would drift silently, in the same invisible way the
`repo-tasks` accident does. Membership is pinned by `tests/unit/test_cli.py`.]

## The name

`spowse` — **S**ensible **POW**er-user **SE**tup — with `spouse` as a second console script at the
same entry point, because the homophone makes the misspelling guaranteed rather than hypothetical
and a second `[project.scripts]` line turns a recurring `command not found` into nothing at all.

[DECISION: **`pulse` was recommended, then withdrawn over a collision this repo has already been
bitten by.** The recommendation rested on a real finding, and it still stands on its own terms: no
package ships a bare `pulse` binary (PulseAudio's executables are `pulseaudio` and the `pa*`
family), this machine runs PipeWire, and the _command_ namespace is genuinely free. What it missed
sits in `tasks/util.py` beside `PULSE_CONFIG_DIR`: `~/.config/pulse` **is** PulseAudio's own config
directory, PULSE's state collided with it silently, and `eee0cf6` (2026-08-13) renamed this repo's
config and state directories to the full repo name to escape it. The command namespace and the XDG
config namespace are different namespaces — but a repo that deliberately renamed away from `pulse`
should not then name its binary `pulse`, and the shim's own natural config path is the occupied
one.]

[DECISION: **the same collision argument later named a task, not just the binary.**
`spowse
self.update` (2026-09-18) pulls the checkout the shim is anchored to. `pulse.update` was the
obvious spelling and lost to the reasoning directly above — a repo that renamed its config and state
directories away from `pulse` should not reintroduce the word as a namespace. `self.update` wins on
the rule this repo applies to flags: match the surrounding ecosystem rather than invent a spelling,
and `uv self update` / `rustup self update` is a shape every consumer of a user-wide tool has
already met. `checkout.update` names the mechanism most literally and is the worst of the three for
the reader it exists for, who has never thought of their install as a checkout.

Its module is `tasks/selfupdate.py`, published under the shorter name. `tasks/self.py` with
`from . import self` was probed and imports perfectly well — `self` is a convention, not a keyword —
but it puts a name every Python reader parses as a parameter into `tasks/__init__.py`'s import list,
for nothing. Renaming on publication is what that file already does for `testing` → `test`.]

About sixty candidates were screened across six themes, filtered against PATH, apt and PyPI.
`fettle` lost to a live PyPI package doing devcontainer scaffolding; `monty` lost to an active
129-release package; `pumas` was a clean backronym but a plural adjacent to `puma` the app server;
`powerset` lost to the pre-owned mathematical meaning. **`pulse-setup` is ruled out by this
machine's own naming rule**, which uses that exact alias as its worked example of what not to do:
the full canonical name or a genuine short form, never a compound that half-repeats the
disambiguating word.

## Alternatives, and why they lose

- **`inv -r <repo> <task>`** — works today, zero code, and is not a tool: the path is typed every
  time, it exposes the whole namespace, and the leading global option changes the command prefix so
  every call misses the `Bash(inv …)` allowlist rules and prompts.
- **A shell wrapper** through the existing `wrapper-script` method — two lines, declared, tracked by
  `deploy.status`, and it does fix discoverability. It inherits the whole namespace, so it cannot
  satisfy the "no repo-tasks, no development tasks" half of the ask. The fallback if the namespace
  work is ever deferred.
- **A global `~/.invoke.yaml` with `tasks.search_root`** — never. It works, which is the danger:
  `search_root` replaces cwd as the discovery start for **every** repo on the machine, so
  `repo-tasks`, `scaffoldapy` and the `*-polite-mcp` family would all load PULSE's tasks instead of
  their own.

## What it is worth, measured

Counted over the harness's ~30-day transcript window: every session in another repo that reached for
a PULSE task by `cd`-ing into the checkout. **16 occurrences, 6 sessions, 3 repos.** Twelve were
`inv ai.install-skills` after editing a skill; the rest were `inv ai.skills`, `inv ai.init` and a
bare `inv --list` — **three guessed task names that do not exist, and one hunt for the name from
outside the checkout where that does not work.**

Two reaches a week is thin justification. A quarter of them failing on a guessed name is not, and
`<name> --list` from anywhere is the answer to that specific failure.

[DECISION: **chasing the cheap version of that fix found something else, and it is owned
elsewhere.** The obvious move was to name the command in the `skill-authoring` skill's last step —
which already names `npx skills add …` and never mentions PULSE. So twelve sessions overrode their
own loaded skill in favour of a task that also creates the `.claude/skills` symlink the `skills` CLI
announces and does not create. Whether that is correct decides whether the measured need was sixteen
reaches or four. It belongs to `agent-skills` and is filed there; it does not block anything here,
but the rate above should not be cited as this tool's justification until it is answered.]
