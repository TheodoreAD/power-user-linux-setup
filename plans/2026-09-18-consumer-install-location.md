---
status: idea
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

## Open questions

[NEEDS CLARIFICATION: **flag or prompt for the developer case?** `install.sh` is interactive and
already asks one question, before `inv setup` — the irreversible step. A second question ("are you
going to develop PULSE itself?") dilutes the one that matters and needs a defined answer under
`--yes` and under no-TTY. The alternative is a `--dev` flag meaning
`~/projects/power-user-linux-setup`, with `--dir` still covering everything else. Leaning flag; the
developer reading a README to clone a repo they intend to work on is the reader most likely to read
`--help`.]

[NEEDS CLARIFICATION: **what is the update task called?** `spowse self.update` reads well and has no
namespace today. `setup.update` collides in meaning with `inv setup`. `deploy.*` is taken and means
something else. Whatever it is, it is machine administration and therefore ships in `spowse` — not
`@util.dev_only`.]

[NEEDS CLARIFICATION: **does the update task re-run anything?** Pulling and stopping is honest and
cheap; pulling and offering `inv setup` matches what `docs/updating.md` tells people to do. Pulling
and re-running `inv setup` unprompted is out — that is the least reversible thing this repo does and
`install.sh` asks before it for exactly that reason.]

[NEEDS CLARIFICATION: **is the non-editable consumer install worth reopening?** See "The alternative
that would remove the checkout entirely" below. It is the shape that matches "like every other
user-wide tool, such as uv" most literally, and it has a real cost that was already weighed once.]

## Recommended direction

In order, because the second item is what makes the first safe.

### 1. Add the update task first

A task that `git pull`s the checkout `tasks/` was imported out of (`Path(__file__).parent.parent`,
the same anchor `tasks/cli.py::_require_checkout` already validates) and reports what moved. Once
that exists, a consumer never needs the path, and where the checkout sits becomes an implementation
detail rather than something they have to remember.

### 2. Flip `install.sh`'s default to `~/.local/share/power-user-linux-setup`

Keep `--dir` as the general escape hatch; add `--dev` as the documented spelling of the developer
case so it is a flag rather than a path to retype. Update the outro to name the directory that was
actually used and the flag that changes it.

[PITFALL: **the flip creates a double-clone hazard that the adopt-never-clobber logic does not
cover.** `install.sh` tests `[ -e "${CLONE_DIR}" ]` against the one default. A person who installed
at `~/projects/power-user-linux-setup` and later re-pastes the one-liner — the most likely thing
somebody does — would get a _second_ clone at the new default and a `spowse` re-pointed at it, with
the old checkout left behind still being compared against by nothing. The adopt check has to look at
both the new default and the legacy one before cloning, and say which it adopted.]

### 3. Refuse or warn on a clone directory under `/mnt/`

[UNVERIFIED: the WSL failure shape is reasoned from DrvFs behaviour, not measured on this machine. A
WSL user commonly symlinks or bind-mounts `~/projects` to `/mnt/c/Users/<name>/projects` so a
Windows editor can see it. A PULSE checkout landing there is a runtime dependency on a filesystem
with no reliable exec bits, case-insensitive paths, and a per-read cost — and nothing currently says
so. Worth a real probe inside a WSL distro before implementing the guard.]

Whichever way the probe goes, `~/.local/share` is always distro-native, which is a second
WSL-specific argument for the default flip: a WSL distro is nearly always a consumer install, and
`docs/wsl.md` sends people to the same Quick start as everyone else.

### 4. Docs and tests that follow

`README.md`, `docs/index.md`'s Quick start and its step-by-step block, `docs/tasks.md`'s "installed
`--editable`" paragraph, `docs/updating.md`'s "pull and re-run" line (which becomes the new task),
and `docs/wsl.md` if the `/mnt/` guard lands. `tests/unit/test_install_sh.py` gains a test for the
new default and one for adopting a legacy `~/projects` checkout.
`.github/workflows/install-smoke.yml` passes `--dir` explicitly and is unaffected.

### What is not at risk

- **`deploy.prune` cannot touch a checkout under `~/.local/share`.** Verified by reading
  `tasks/deploy.py::prune`: it iterates the manifest of paths PULSE recorded writing, skips anything
  that is not a regular file, and refuses anything whose digest has changed. A directory it never
  wrote is not reachable.
- **The editable anchor does not care about the path.** The `.pth` holds a bare directory string;
  `~/.local/share` is no different from `~/projects` to CPython's `site` machinery.
- **Existing machines are untouched.** Only new installs land at the new default, and step 2's
  legacy-adopt check is what keeps a re-run on an existing machine from forking.

### The alternative that would remove the checkout entirely

`uv tool install power-user-linux-setup@git+https://github.com/TheodoreAD/power-user-linux-setup`,
non-editable, with `setup.toml` and `config/` shipped as package data — no clone anywhere, and
`uv tool upgrade` as the update path. This is the shape the request's own analogy points at ("like
every other user-wide tool, such as uv"), and it is strictly better for someone who never opens the
tree.

It was rejected once, in `contributing/spowse-shim.md`, on the grounds that `deploy.status` would
then compare the machine against a frozen copy nobody can `git pull` and the drift model stops
meaning anything. That argument is about the **developer**, who edits `config/` and wants drift
reported against a tree they can change. For a consumer, who overrides through
`~/.config/power-user-linux-setup/overrides.toml` and never touches `config/`, comparing against the
installed version is arguably the correct semantics rather than a degradation.

The costs, stated so this is a decision rather than an omission: two install shapes to maintain and
test; `bootstrap.sh` and `tasks/netdoctor.py` still need a tree to run from before uv exists, so the
one-liner would keep cloning something; and the consumer loses the ability to inspect or patch
`config/` locally, which is a real escape hatch on a machine-setup tool.

Not recommended now. Recorded here because it is the right direction if consumer installs ever
outnumber developer ones, and because "we already decided against packaging the config" is an answer
to a question that was asked about a different user.

### Rejected outright

- **Symlink `~/projects/power-user-linux-setup` → `~/.local/share/...`.** Two paths naming one tree,
  and which one the editable `.pth` recorded decides what `Path(__file__).parent.parent` resolves
  to. A footgun bought for cosmetics.
- **A prompt asking where to clone.** Same objection as the developer prompt above, and worse: the
  consumer, who is the majority case, would be asked to answer a question about a case that does not
  apply to them.
