---
status: landed
updated: 2026-09-18
---

# Where a consumer's PULSE checkout lives, and how they update it

## Context

`install.sh` clones into `~/projects/power-user-linux-setup` for everyone — the person developing
PULSE and the person who only wants a configured machine. `--dir` already overrides it, so the
option exists; what does not exist is a default that fits the second person, or a way for them to
update without knowing the path.

### The checkout is runtime state, not a development artifact

This is the fact the current default reads against. Three things resolve the checkout at run time
rather than copying it:

- `spowse`/`spouse` are `uv tool install --editable` against it, so a bare-path `.pth` in the tool
  venv holds that directory and `tasks/cli.py` reads `setup.toml` and `config/` out of it
  (`contributing/spowse-shim.md`).
- `inv deploy.all` deploys `config/` sources into `~`, and `inv deploy.status` reports drift by
  comparing the home directory against that tree.
- `inv setup` re-run after a `git pull` is the documented way to pick up a new package or a changed
  dotfile (`docs/updating.md`).

So the checkout is a permanent, user-wide data directory that happens to be a git working tree. A
consumer never opens it, never edits it, and must never move it — `install.sh` prints exactly that
warning, and `tests/unit/test_install_sh.py::test_the_checkout_is_permanent_and_the_script_says_so`
pins it.

### Three things in the repo already say `~/.local/share`

- **`AGENTS.md`'s own XDG rule**: "Multi-file runtimes (Go, nvm) install to `~/.local/share/<tool>`
  with a binary symlinked into `~/.local/bin/`." A PULSE checkout is precisely that shape, and it is
  the one such install this repo puts somewhere else.
- **`bootstrap-devcontainer.sh` already does it** —
  `CLONE_DIR="${HOME}/.local/share/pulse-devcontainer-src"`. The container path is the consumer path
  with nobody to ask, and it made this choice already.
- **PULSE owns two of the three XDG legs under its own name**: `~/.config/power-user-linux-setup`
  (`util.PULSE_CONFIG_DIR`) and `~/.local/state/power-user-linux-setup` (`util.PULSE_STATE_DIR`).
  `~/.local/share/power-user-linux-setup` is the free third leg and is what a reader would guess.

### `~/projects/` is a first-class PULSE concept for something else

`inv identity.init` defaults the projects root to `~/projects/` and `inv git.configure` writes
per-directory git identities under `~/projects/<dir>/.gitconfig`. Cloning PULSE there plants a repo
the consumer does not develop inside the workspace PULSE itself defines as "the repos you develop,
under your git identity". For the developer that is exactly right; for the consumer it is a category
error.

### The gap that exists today at either path: there is no update command

`docs/updating.md` says "pull and re-run `inv setup`", which requires knowing and typing the
checkout path. There is no `spowse`-reachable task that pulls the checkout it is anchored to —
`rg 'def update'` finds only `gnome.update` and `node.update-globals`. Moving the default to a
deeper path makes this worse, which is why it is a prerequisite rather than a follow-up: with an
update task the location stops mattering to the consumer at all, and that is what makes
`~/.local/share` safe rather than merely correct.

[PITFALL: **the update path itself works, and the obvious objection to it is wrong.** `install.sh`
clones `--branch stable --depth 1`, which leaves a detached HEAD and looks un-pullable. Probed
2026-09-18 against a local repo with a moved tag: the clone's only refspec is
`+refs/tags/stable:refs/tags/stable` — forced — so `git pull` updates the moved tag and
fast-forwards the detached HEAD onto it. The plain-`git fetch`-never-moves-a-tag rule in
`~/.agents/AGENTS.md` does not apply here, because that refspec is explicit and forced. Nothing
about the update mechanism needs changing; only its discoverability does.]

## Design

Four decisions were settled 2026-09-18; each is recorded at the subsection it shapes. The order
below is the implementation order, because item 1 is what makes item 2 safe.

**All of it landed 2026-09-18** — `b103ec7` (the task) and `16d6d4f` (the default flip, `--dev`, the
legacy adopt, and the docs). Item 3 was dropped the same day rather than built, on the user's answer
to the premise it rested on; the subsection records why and what was learned on the way past.

### 1. `tasks/selfupdate.py`, published as the `self` collection

One task, `update`, reachable as `spowse self.update` from anywhere and `inv self.update` inside the
checkout. Not marked `@util.dev_only` — it administers a machine's PULSE install, which is exactly
what the shim is for.

[DECISION: **`self.update`, matching `uv self update` and `rustup self update`.** The repo's own
flag rule says to match the surrounding ecosystem's shape rather than invent one, and self-update is
a shape every consumer of a user-wide tool has already met. `pulse.update` was rejected on the same
grounds as the shim's name: `eee0cf6` (2026-08-13) deliberately renamed this repo's config and state
directories away from `pulse` to escape the PulseAudio collision, so reusing the word invites the
question again. `checkout.update` names the mechanism most literally and is the worst of the three
for the reader it is for — a consumer has never thought of their install as a checkout.]

**Module name.** `tasks/self.py` with `from . import self` is legal — probed 2026-09-18, it imports
and resolves fine, since `self` is a convention rather than a keyword. It is still not what to
write: it puts a name every Python reader parses as a parameter into `tasks/__init__.py`'s import
list. Publish under a different name instead, which this file already does twice — `testing` →
`test`, `dev_env` → `dev-env`:

```python
namespace.add_collection(Collection.from_module(selfupdate, name="self"))
```

`Collection.from_module`'s `name` parameter is verified present in the installed invoke.

**What the task does**, in order:

1. Resolve the checkout as `Path(__file__).parent.parent` — the same anchor
   `tasks/cli.py::_require_checkout` already validates, so a moved or gutted checkout has already
   failed with a sentence before this task runs.
2. **Refuse on a dirty tree** (`git status --porcelain` non-empty) and **refuse when the checkout is
   ahead of its upstream** (`git log @{u}..HEAD`). Report and stop; do not stash, do not rebase.
3. Pull, then report what moved — the ref before and after, and the changed paths.
4. **If `pyproject.toml` or `uv.lock` changed in that pull, say to re-run
   `inv python.install-tools`.** An editable install picks up new _code_ through its `.pth` with no
   reinstall, but the tool venv's resolved dependencies are fixed at install time, so a new
   dependency is silently absent otherwise.
5. On a TTY, offer to run `inv setup`. Never without asking.

[DECISION: **pull, report, then offer `inv setup` behind a confirmation — never run it unprompted.**
This mirrors `install.sh` exactly: do the safe part, ask before the irreversible one. `inv setup`
installs apt packages, changes the login shell and writes GNOME settings, which is why `install.sh`
asks before it. The prompt lives in the task's own Python guarded by `sys.stdin.isatty()`, the shape
`wsl.install` already uses, so it does not breach the repo's rule that nothing reached from inside a
`c.run(...)` may wait for typed input.]

[PITFALL: **the refusals in step 2 are not politeness, they are the machine this runs on.** Parallel
agent sessions on this machine share one working tree, so a task that pulls the checkout can move a
tree another session is mid-edit in — and for a developer running `inv self.update` in their own
checkout, a pull over local commits is a merge nobody asked for. A consumer's checkout is never
dirty and never ahead, so the refusals cost that reader nothing and are invisible to them.]

### 2. `install.sh`: default to `~/.local/share/power-user-linux-setup`, with `--dev`

- `CLONE_DIR` defaults to `${HOME}/.local/share/power-user-linux-setup`.
- `--dev` sets it to `${HOME}/projects/power-user-linux-setup`, the old default.
- `--dir` keeps covering everything else, and must record that it was passed explicitly — the
  legacy-adopt branch below has to not fire when the user named a path.
- The outro names the directory actually used and the flag that changes it, alongside the existing
  keep-it-there warning.

[DECISION: **a flag, not a prompt.** `install.sh` asks exactly one question today, immediately
before the least reversible thing this repo does, and a second question dilutes the one that matters
— it would also need a defined answer under `--yes` and under no-TTY, where the whole point of the
existing prompt is that it refuses rather than guessing. The developer, who is the minority case and
is about to clone a repo they intend to work on, is also the reader most likely to run `--help`.]

[PITFALL: **the flip can fork an existing machine into two clones, and the adopt-never-clobber logic
does not cover it.** `install.sh` tests `[ -e "${CLONE_DIR}" ]` against the one default. Somebody
who installed at `~/projects/power-user-linux-setup` and later re-pastes the one-liner — the most
likely thing anyone does — would get a _second_ clone at the new default and a `spowse` re-pointed
at it, leaving the first checkout on disk with nothing reading it and `deploy.status` now answering
about a tree they never updated. So: when neither `--dir` nor `--dev` was passed and the new default
does not exist, check the legacy path, adopt it if it is a valid checkout, and say which one was
adopted and why.]

### 3. No `/mnt/` guard — dropped, not deferred

[DECISION: **the guard was designed against a premise about how this machine is used, and the
premise is false.** Stated by the user 2026-09-18: this repo will not be developed on NTFS, and
`~/projects` will not be a symlink to a Windows location — the projects directory lives in the Linux
home. That is the whole of what the guard was protecting against, so there is nothing left to guard
and nothing to probe. Deleted rather than carried as an open item: an `[UNVERIFIED:]` tag on a
scenario that has been ruled out is a backlog entry nobody can ever close.]

Worth keeping, because it was checked rather than assumed and a future session should not re-derive
it. The claim was three things stacked, and measuring the repo dissolved most of it before the
question of a distro ever arose:

- **Case-insensitivity was never a risk here.** No two tracked paths in this repo differ only by
  case, so there is nothing for NTFS's case folding to collide.
- **A lost exec bit would not stop an install.** `install.sh` runs `bash ./bootstrap.sh`, naming the
  interpreter, so none of the five tracked `100755` files is invoked by path. (One of those five,
  `docs/extra/extra.css`, is executable by accident — a stylesheet with no reason to be.)
- **The sharp edge was somewhere else entirely, and was missed when this item was written.**
  `CLAUDE.md` is the repo's only tracked symlink, mode `120000` → `AGENTS.md`, and it is deliberate:
  `AGENTS.md` requires a plain symlink rather than a file carrying Claude Code's `@` import syntax.
  A filesystem that cannot create symlinks fails `git clone` at checkout, before anything else runs
  — a hard error rather than the slow-and-degraded shape this item was written about.

The last of those is the one that outlives the WSL question, since it is a property of the repo
rather than of any filesystem: **this repo cannot be checked out anywhere symlinks do not work.**
Nothing currently says so anywhere, and nothing needs to while every target is Linux.

The default flip does not lose anything by this. Its argument never rested on filesystems — the
checkout is runtime state, the XDG rule already covers that shape, `bootstrap-devcontainer.sh` got
there first, and `~/projects` is the git-identity workspace. What is gone is the _extra_
WSL-specific weight this item added: with Windows paths ruled out, a WSL distro is just Linux, and
`~/.local/share` is right there for exactly the same reasons it is right anywhere else.

### 4. What is deliberately not changed

- **This machine's own checkout stays where it is.** It is the development one, it is under a
  `~/projects` git identity, and `--dev` names that layout precisely. Nothing here is a migration
  instruction.
- **`bootstrap-devcontainer.sh` keeps its own `CLONE_DIR` and its `rm -rf`.** Both paths now sit
  under `~/.local/share`, which erodes one of the three differences
  `contributing/install-entry-points.md` cites for not factoring a shared spine — the destination is
  still disposable in one and permanent in the other, so the decision stands, but that page needs a
  sentence saying so rather than leaving a reader to notice the wording has gone stale.
- **`.github/workflows/install-smoke.yml` passes `--dir` explicitly** and is unaffected.
- **`deploy.prune` cannot reach a checkout under `~/.local/share`.** Verified by reading
  `tasks/deploy.py::prune`: it iterates the manifest of paths PULSE recorded writing, skips anything
  that is not a regular file, and refuses anything whose digest changed. A directory it never wrote
  is not reachable.
- **The editable anchor does not care about the path.** The `.pth` holds a bare directory string.

### 5. The alternative that would remove the checkout entirely

`uv tool install power-user-linux-setup@git+https://github.com/TheodoreAD/power-user-linux-setup`,
non-editable, with `setup.toml` and `config/` shipped as package data — no clone anywhere, and
`uv tool upgrade` as the update path. This is the shape "like every other user-wide tool, such as
uv" points at most literally, and it is strictly better for someone who never opens the tree.

[DECISION: **recorded, not built.** `contributing/spowse-shim.md` rejected it because
`deploy.status` would then compare the machine against a frozen copy nobody can `git pull`. That
argument is about the _developer_, who edits `config/`; for a consumer overriding through
`~/.config/power-user-linux-setup/overrides.toml`, comparing against the installed version is
arguably the correct semantics rather than a degradation — so the rejection answers a question asked
about a different user, and is worth re-reading rather than citing. It loses now on cost, not on
principle: two install shapes to maintain and test, `bootstrap.sh` and `tasks/netdoctor.py` still
need a tree to run from before uv exists so the one-liner would keep cloning something anyway, and
the consumer loses the ability to inspect or patch `config/` locally. Revisit if consumer installs
ever outnumber developer ones.]

### 6. Rejected outright

- **Symlink `~/projects/power-user-linux-setup` → `~/.local/share/...`.** Two paths naming one tree,
  and which one the editable `.pth` recorded decides what `Path(__file__).parent.parent` resolves
  to. A footgun bought for cosmetics.
- **A prompt asking where to clone.** Same objection as the developer prompt, and worse: the
  consumer, who is the majority case, would be asked about a case that does not apply to them.

## Files touched

| file                                   | change                                                                                     |
| -------------------------------------- | ------------------------------------------------------------------------------------------ |
| `tasks/selfupdate.py`                  | new — the `update` task                                                                    |
| `tasks/__init__.py`                    | import it, `add_collection(..., name="self")`                                              |
| `install.sh`                           | new default, `--dev`, explicit-`--dir` tracking, legacy adopt, header + outro              |
| `tests/unit/test_install_sh.py`        | new default, `--dev`, legacy adopt, `--dir` not overridden by legacy, non-checkout ignored |
| `tests/unit/test_cli.py`               | `self.update` in the pinned `spowse` namespace membership                                  |
| `tests/unit/test_selfupdate.py`        | new — dirty-tree and ahead-of-upstream refusals, the pyproject-changed message             |
| `docs/tasks.md`                        | regenerated by `inv catalog.render-tasks`; prose section on the two entry points           |
| `docs/updating.md`                     | "pull and re-run `inv setup`" becomes `spowse self.update`                                 |
| `docs/index.md`                        | Quick start clone path, and the step-by-step block                                         |
| `README.md`                            | the clone path line                                                                        |
| `AGENTS.md`                            | "The one-line installer" section: the new default and `self.update`                        |
| `contributing/install-entry-points.md` | a sentence on why two scripts still stand now both destinations are under `~/.local/share` |

Run the `invoke-task-conventions` skill before writing `tasks/selfupdate.py` — the name is settled,
the wiring traps it covers are not.

## Verification

What was actually run, 2026-09-18, rather than what was planned to be:

- `inv quality.precommit` clean on every commit — `pytest`, `basedpyright`, `shellcheck`/`shfmt`
  over `install.sh`, and the generated-docs guard that catches a stale `docs/tasks.md`.
- **`install.sh` driven end to end into `tmp_path`** by `tests/unit/test_install_sh.py`,
  `--repo-url` pointing at a real git repo built in the same directory: no flags (new default),
  `--dev`, a pre-existing legacy checkout adopted, a named `--dir` not overridden by one, and a
  non-checkout at the old default ignored rather than adopted.
- **Both new guards checked by disabling them and re-running**, since a passing test proves nothing
  on its own: the dirty-tree refusal and the legacy adopt each failed their own test with the branch
  short-circuited, and passed again with it restored.
- **`inv self.update` against this checkout while it was genuinely dirty** — refused, and ran no
  `git pull`.
- **`spowse --list` and `spowse deploy.status` from an unrelated directory**, proving the editable
  anchor still resolves from outside the checkout.
- This machine's own install was not migrated and is not part of any of the above.

- **The real `bootstrap.sh`, in CI**, which is where it belongs: locally it would install Python
  versions and run `uv tool install --force` over this machine's own `inv`/`repo-tasks`, mutating
  the developer machine for no extra coverage of the branches that changed. `install-smoke / smoke`
  runs it against the commit under test — `--repo-url` at the checkout, a branch cut at `HEAD` — and
  passed on `16d6d4f` as a job inside CI run `35341331495`.

[PITFALL: **the smoke job passes `--dir`, so no single run covers the new default together with the
real `bootstrap.sh`.** The two halves are each proven and the composition is sound — the default
only decides the value of `CLONE_DIR`, and `bootstrap.sh` is indifferent to where the checkout sits
— but the boundary is worth knowing before trusting a green CI about a future change to the default.
A break in default resolution that the unit tests miss would not be caught end to end. The same gap
covers `--dev` and the legacy adopt, for the same reason and with the same argument.]
