---
status: landed
updated: 2026-09-12
---

# A one-line clone-and-install for a fresh machine

**The ask, stated 2026-09-08:** an install script that works in one line, so a person can clone and
install in one go — a bootstrap, in the sense the word has outside this repo.

## Context

Today the README's quick start is six lines: `cd ~`, `mkdir -p projects`, `cd projects`,
`git clone …`, `cd power-user-linux-setup`, `./bootstrap.sh`, `inv setup`. Nothing is wrong with
them, but they are six chances to be somewhere unexpected on a machine that has nothing on it yet,
and the first thing a fresh Ubuntu install cannot do is remember which directory you meant.

**Most of the work already exists, and it is not `bootstrap.sh`.** `bootstrap.sh` has to be run from
inside a checkout — it reads `${SCRIPT_DIR}/setup.toml` for the Python versions and the
`install_repo_tasks` default — so it can never be the thing you curl. The script that already does
the whole job is **`bootstrap-devcontainer.sh`**: it clones a pinned ref, runs `bootstrap.sh`,
re-exports `PATH`, and runs `inv setup`. A workstation entry point is that script with three
decisions changed, not a new design.

## What the existing script already settled, and must not be re-litigated

[PITFALL: **`curl … | bash` is ruled out here by measurement, not by taste, and it is the exact
shape "one line" asks for.** A pipeline reports its last command's status, so a failed download
hands bash an empty stdin and the whole thing exits 0 — the install claims success having done
nothing. `bootstrap-devcontainer.sh`'s header records the measurement against a ref that did not
exist: `curl -f` exits 22, the pipeline exits 0, the download-to-a-file form exits 22. A proxy error
page or a network blip does the same thing. So the one-liner is
`curl -fsSL <url> -o /tmp/pulse-install.sh && bash /tmp/pulse-install.sh` — still one line to paste,
and the `&&` is what makes it honest.]

Two further consequences fall out of the same choice, and both of them are reasons a workstation
install needs it even more than a container does:

- **`bootstrap.sh` asks a question.** The repo-tasks prompt is guarded by `[ -t 0 ]`, so a piped
  stdin does not merely lose the prompt — it silently takes `setup.toml`'s default and the user
  never learns a choice existed. A downloaded script keeps the terminal on stdin.
- **`inv setup` needs root, and collects it outside invoke.** `util.ensure_sudo()` falls back to
  "`sudo -v` as a plain subprocess owning the real terminal" when no GUI askpass can work — and on a
  fresh machine there is no `~/.local/bin/askpass-zenity` yet, because PULSE is what installs it. A
  piped stdin is exactly the case that has no terminal to own.

## The three decisions that differ from the container script

1. **The clone destination is permanent and load-bearing.** The container script clones into
   `~/.local/share/pulse-devcontainer-src` and `rm -rf`s it first, because nothing there outlives
   the image. On a workstation the opposite is true in a way that is easy to miss: `spowse` is
   installed `--editable` against the checkout, and `deploy.status` compares the machine to it, so
   **the directory the installer picks is a permanent dependency of the machine.** Probed 2026-09-08
   (see the portability plan): move the checkout and `spowse` dies at import with
   `ModuleNotFoundError: No module named 'tasks'`, naming neither the path nor this repo. So the
   installer must never `rm -rf` a destination, must adopt an existing checkout rather than clobber
   it, and should say the path out loud when it finishes.
2. **The tag defaults are the machine's, not the container's.** No `CONTAINER_EXCLUDE_TAGS`, and no
   `PULSE_ASSUME_YES=1` — that flag exists because unattended provisioning must overwrite a base
   image's dotfiles, which is the wrong default for a person's home directory. Pass `--yes` through
   for someone who wants it.
3. **How far the one line should go.** The container script runs `inv setup` to completion because
   an image build has no user to ask. A workstation run has a terminal, and `inv setup` installs apt
   packages, changes the shell and writes GNOME settings — the least reversible thing this repo
   does. Recommended below.

## What landed, 2026-09-08

`install.sh` at the repo root, plus the quick start in `README.md` and `docs/index.md`. Verified in
a stock `ubuntu:24.04` container with no `git` on it: the script installed git, cloned, ran the real
`bootstrap.sh` and exited 0. The refuse, adopt, `--bootstrap-only`, `--exclude-tags` and no-terminal
branches were each exercised against a stub checkout rather than reasoned about.

[DECISION: **it runs `inv setup`, after asking.** Stopping at `bootstrap.sh` was the conservative
option and it loses the ask: "in one go" is the request, and a run started from a terminal has
somewhere to put the question. The prompt follows apt's shape — on by default, `--yes` to skip,
never an opt-in `--confirm` — and it names what is about to happen (apt packages, login shell, GNOME
settings) rather than asking an abstract "continue?". `--bootstrap-only` keeps the conservative path
available for anyone who wants it. **With no terminal and no `--yes` the script exits 1** rather
than proceeding, which is the same silent-default failure the never-pipe rule is about: a setup run
that happens because the question could not be shown is worse than one that does not happen.]

[DECISION: **`install.sh`, not `bootstrap-remote.sh`.** The raw URL is the interface, and it is read
by people who have never seen this repo's file naming; `install.sh` is what uv's own one-liner uses
and what a person guesses. The `bootstrap-` prefix stays accurate for the two scripts that are
bootstraps in this repo's internal sense.]

[PITFALL: **the ref had to be `master`, and `stable` would have shipped a 404.** `stable` was the
recommendation and it is still where this belongs — it is what `bootstrap-devcontainer.sh` pins, and
pinning is what lets someone read the script today and run the same bytes tomorrow. But `stable` is
a **tag**, not a branch, currently on a commit from **2026-09-02**, six days behind and predating
`install.sh` entirely. Both the raw URL and a clone of that ref would resolve to a tree with no
installer in it, so the documented one-liner would have failed for every reader while looking
correct in review. Checked with `git ls-remote` rather than assumed — a local `origin/stable` would
not have told the truth about the tag. Moving the tag past this commit makes `master` → `stable` a
one-word change in four places, and the script's own comment names them.]

[DECISION: **two scripts, not one factored spine.** The clone-then-bootstrap-then-setup shape is
common, but all three decisions above differ at every step, and `bootstrap-devcontainer.sh` is on a
CI smoke test that a refactor would risk for the sake of a distributed entry point. What is shared
is the expensive part — the never-pipe measurement — and it stays written up once, in that script's
header, pointed at rather than copied.]

One thing was built more conservatively than planned. "Adopt, never clobber" was going to fetch and
check out the requested ref in an existing checkout; it now uses the checkout **exactly as it
stands**, no fetch and no ref change, and says so. A fetch-and-checkout on a directory that may hold
uncommitted work is a clobber wearing a git command, and this script's job is starting a machine,
not updating one that already started.

## What is left

1. ~~Move the `stable` tag past this commit and switch the four `master` spellings~~ — **done**, the
   same day. The tag was moved by hand, which is worth naming rather than leaving implicit: CI moves
   it "only on a green smoke test", and the workflow that would have run one
   (`.github/workflows/devcontainer.yml`) is deliberately `workflow_dispatch`-only while the
   container pipeline iterates. So the tag now points at a commit the smoke test has not seen, and
   `bootstrap-devcontainer.sh` pins the same ref. Item 2 below is what closes that gap for this
   script; the container path's own gap predates this plan.
2. ~~A CI smoke test for this script~~ — **done**, and it split into two tiers rather than the one
   this listed. `ci.yml`'s `install-smoke` job runs the real thing on every push and pull request:
   clone, `bootstrap.sh`, then `inv --list` in what it left behind. `tests/unit/test_install_sh.py`
   covers the nine branches that happen before any download, hermetically, so they run in
   `inv quality.precommit` rather than only on a runner — and it replaced the throwaway script those
   branches were first checked with.

   [DECISION: **the job installs the commit under test, which is what `--repo-url` was added for.**
   Cloning `stable` from GitHub was the obvious shape and it tests whatever was already released —
   confirming the past rather than gating the change, which is precisely the evidence that was not
   missing. So the job points `--repo-url` at the checkout and clones a branch made at `HEAD`.
   `git branch` rather than a SHA because `git clone --branch` takes a branch or tag and not an
   arbitrary commit, and creating one works from the detached `HEAD` a `pull_request` checkout
   leaves. `fetch-depth: 0` is load-bearing next to it: the clone is local, and
   `git clone --depth 1` from a shallow repository fails outright.]

   Two things it deliberately does not do. It stops at `--bootstrap-only`, because `inv setup` in
   full is what the devcontainer smoke test already covers and duplicating it would double the
   slowest job in the repo for no new information.

   [DECISION: **the `stable` tag waits for it too, through a `workflow_call` rather than a second
   copy.** `publish-stable` required only the container smoke test, which stopped covering what the
   tag promises the day `install.sh` started sharing that ref — `stable` could have moved onto a
   commit whose installer does not clone. `needs:` does not reach across workflows, so the job moved
   into `.github/workflows/install-smoke.yml` as a `workflow_call` and both workflows call it:
   `ci.yml`'s call is the per-commit coverage, `devcontainer.yml`'s is the release gate. Copying the
   job into the second workflow was the alternative and it is the one that drifts — the same
   argument the shim's namespace derivation makes about parallel lists. A `./` caller resolves the
   file at the caller's own commit, so neither call tests `master` by accident.]

   `quality` was wired the same way immediately after, so `publish-stable` now requires all three.
   `docs` is deliberately left out: a documentation-site build failure does not change what a
   consumer of this tag installs.

   [PITFALL: **dispatching the finished gate proved it worked by failing, and what it caught was
   three days old.** `publish-stable` was skipped because the container `smoke-test` died on
   `[verify] python-keyring: ~/.config/uv/uv.toml not found`. Cause: `tasks/python.py`'s
   `install_tools` was the only installer never calling `deploy.apply_config_files` — `apt.py` calls
   it twice, `tools.py` calls it, and that function's own docstring already claimed it was called
   from every install task. It stayed invisible because only two `uv-tool` packages declare
   `config_files`, and until 2026-09-05 the only one was `act`, tagged `workstation` and therefore
   excluded in containers; `python-keyring` declared one with no tags. Run history dates it exactly:
   last green container build 2026-09-01, nothing dispatched between the breakage and 2026-09-08 —
   the precise cost this workflow's own comment predicts about being `workflow_dispatch`-only.]

   [PITFALL: **moving the tag by hand had already published that breakage, which is the concrete
   version of the risk item 1 recorded as hypothetical.** `stable` went from `52cba6e` (2026-09-01,
   container-green, no `install.sh`) to `48f284a`, which carried the 09-05 regression — so
   `bootstrap-devcontainer.sh` consumers were broken by the move for as long as it stood, in
   exchange for the one-liner working. The two could only be fixed together: repair the installer,
   then let `publish-stable` move the tag itself. It now sits on `2a2a152` with all three gates
   green, and the raw `stable/install.sh` URL was re-fetched and byte-compared after the move rather
   than assumed.]
3. Not a `sudo bash`, ever. The script collects root the way `inv setup` already does, through
   `util.ensure_sudo()`, so nothing runs as root that does not need to. Worth restating here because
   "why not just tell people to sudo it" is the obvious simplification and it is wrong.

[DECISION: **this is a distribution entry point, so it is pinned and inspectable rather than
convenient.** A pasted line runs unreviewed code with access to sudo on a fresh machine, which is
the one place this repo's usual "it is only my machine" reasoning does not apply — the audience is
whoever reads the README. The download-to-a-file form is what makes inspection possible at all
(`less /tmp/pulse-install.sh` before `bash`), and pinning to `stable` is what makes what you
inspected yesterday the same as what you run today.]

## Verified 2026-09-12, and it all holds

Re-checked from the outside rather than read off the plan:

- `stable` on the **remote** is `2a2a152`, and all three gates are green on it — `CI`,
  `Dev container smoke test` and the docs deploy all `success`. The `devcontainer.yml` run history
  also confirms the sequence this plan describes: `52cba6e` green 2026-09-01, `90f47a0` **failed**
  2026-09-08 catching the regression, `2a2a152` green the same day.
- The published `stable/install.sh` is **byte-identical** to `git show stable:install.sh`, and
  `install.sh` on `master` has not drifted from either.
- All six published raw URLs across `README.md`, `docs/index.md`, `docs/dev-container.md`,
  `install.sh`, `bootstrap-devcontainer.sh` and one plan name `stable`; none still say `master`.
  `install.sh`'s own `REF` defaults to `stable`.
- `install-smoke` runs on every push and was green on today's `master`, so the installer is verified
  against current work, not only against the tag.

[PITFALL: **the local `stable` tag was stale, pointing at the commit this plan records as broken.**
`git rev-parse stable` gave `48f284a` — the hand-moved tag that carried the `verify.all` regression
— while the remote had `2a2a152`. A plain `git fetch` never updates a tag that moved, so the local
ref had been wrong since `publish-stable` corrected it on 2026-09-08, and anything reasoning from
`git show stable:<file>` on this machine would have read the broken tree while believing it was
reading the published one. Fixed with `git fetch origin --tags --force`. This is the tag-shaped
instance of the rule this corpus already states about remote-tracking refs: ask the host, not the
local ref.]

**Two decisions are left for the user rather than closed here**, and both are recorded in
`AGENTS.md` as things not to change unilaterally: whether `devcontainer.yml` keeps its
`workflow_dispatch`-only trigger, whose cost this plan measured at three silent days; and whether
`stable` should be moved forward, since it now sits well behind `master` and carries none of the
work done since 2026-09-08.

## Migrated to

- [`contributing/install-entry-points.md`](../contributing/install-entry-points.md), new — the
  options not taken, which is all that had no home: two scripts rather than one factored spine and
  the two counts that decided it, the `install.sh`-over-`bootstrap-remote.sh` naming, why
  `sudo bash` is refused, and the late conservatism in adopt-never-clobber. `AGENTS.md` points at it
  from the installer section.
- The stale-local-tag pitfall found while verifying this — carried into that page's neighbourhood by
  the commit message rather than the page, since it is a fact about `git fetch` and not about this
  installer.

Deliberately not migrated:

- **Everything either script's own header already argues**, which is most of this plan: the
  never-pipe measurement (written once in `bootstrap-devcontainer.sh`, pointed at from
  `install.sh`), the pinning rationale, adopt-never-clobber, and the apt-shaped confirmation. Each
  is commented at the lines that implement it, which is closer than a page.
- **The `stable` gating design** — three gates, `workflow_call` rather than a copied job, the
  `--repo-url`/`git branch`/`fetch-depth: 0` reasoning, and the hand-moved-tag pitfall. All already
  in `AGENTS.md`'s installer section, which is where someone about to touch the workflow will be.
- **The `deploy.apply_config_files` regression.** Fixed and pinned by three tests in
  `tests/unit/test_python.py`, each carrying its own reasoning — including the one asserting the
  call is unconditional so the next uv-tool package to declare `config_files` cannot reintroduce it.
- **The verification transcript above.** It is a dated re-check, not a design fact; the commit
  message carries it.
