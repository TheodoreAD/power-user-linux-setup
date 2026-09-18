# Why there are two clone-and-install scripts, and not one

Design rationale for the relationship between `install.sh` and `bootstrap-devcontainer.sh` — the
options that were rejected while building the workstation one, which is the part neither script's
header can carry because a header explains what its own file does.

Everything about **what** each script does is in its own header, and they are thorough: the
never-pipe measurement is written up once in `bootstrap-devcontainer.sh` and pointed at from
`install.sh`, and the adopt-never-clobber, pinning and confirmation decisions are commented at the
lines that implement them. `AGENTS.md`'s "The one-line installer, and what gates the `stable` tag"
covers the release gating. This page is only the road not taken.

## Two scripts rather than one factored spine

The shape is identical — clone a pinned ref, run `bootstrap.sh`, re-export `PATH`, hand over to
`inv setup` — so extracting a shared spine is the obvious move. It was rejected on two counts, and
the second is the one that would not have been obvious later:

[PITFALL: **since 2026-09-18 both scripts clone under `~/.local/share`, which makes the first bullet
below read weaker than it is.** `install.sh`'s default moved off `~/projects` because the checkout
is permanent runtime state rather than a repo anyone opens — the same reasoning that put
`bootstrap-devcontainer.sh`'s there first. The two destinations are now siblings, so "the clone
destination differs" is easy to misread as settled. It is not: one is `rm -rf`'d on every build
because nothing in an image outlives it, and the other is adopted as it stands and refuses to be
deleted, and `install.sh` additionally has to recognise its own previous default. That is more
divergence than before, not less.]

- **All three decisions differ at every step.** The clone destination is disposable in a container
  and permanent on a workstation; the tag defaults are `CONTAINER_EXCLUDE_TAGS` plus
  `PULSE_ASSUME_YES=1` in one and the machine's own defaults in the other; and one runs `inv setup`
  to completion because an image build has nobody to ask, while the other asks. A spine
  parameterised on all three is not a spine.
- **`bootstrap-devcontainer.sh` is on a CI smoke test, and a refactor spends that.** Risking a
  working release gate to deduplicate a distribution entry point is the wrong trade in the wrong
  direction.

What is genuinely shared is the **expensive** part — the measurement that rules out `curl … | bash`
— and it is shared the cheap way: written up once in the container script's header and pointed at
from `install.sh`, rather than copied into both or hoisted into a third file nobody opens.

[DECISION: **`install.sh`, not `bootstrap-remote.sh`.** The raw URL _is_ the interface, and it is
read by people who have never seen this repo's file naming — `install.sh` is what uv's own one-liner
uses and what a person guesses. The `bootstrap-` prefix stays accurate for the two scripts that are
bootstraps in this repo's internal sense, which is a narrower meaning than the word has outside it.]

## Where the clone lands, and why it is not `~/projects`

Moved to `~/.local/share/power-user-linux-setup` on 2026-09-18, with `--dev` as the opt-out. The
reasoning is at the `CLONE_DIR` assignment in `install.sh` and does not need repeating; what a
header cannot carry is what the move beat.

[DECISION: **a flag, not a prompt, for the developer case.** The obvious alternative was to ask —
`install.sh` is interactive already. It loses for a reason specific to this script: it asks exactly
one question, immediately before the least reversible thing this repo does, and that question's
weight is the whole point of the two-step download-then-run shape. A second question dilutes it. It
would also need a defined answer under `--yes` and under no-TTY, where the existing prompt's design
is to _refuse_ rather than guess — and "refuse because we could not ask where to clone" is a worse
failure than any it prevents. The developer is the minority case and is about to clone a repo they
intend to work on, which makes them the reader most likely to run `--help`.]

[PITFALL: **a person who installed before the move, re-pasting the one-liner, is the case the
adopt-never-clobber logic did not cover.** That logic tests one path. With the default moved, a
re-run would clone a _second_ checkout at the new default and re-point `spowse` at it with
`uv tool install --editable`, leaving the first on disk with nothing reading it while
`inv deploy.status` quietly starts answering about a tree its owner never updates. Nothing errors
and both checkouts look fine. Hence the legacy-adopt branch — and hence its guard: it fires only
when no path was named, because a `--dir` is an instruction rather than a guess to second-guess.]

[PITFALL: **`git pull` works in the shallow tag clone, and the reasoning that says it cannot is
wrong.** `install.sh` clones `--branch stable --depth 1`, which leaves a detached HEAD, and this
machine's own `~/.agents/AGENTS.md` warns that a plain `git fetch` never updates a moved tag — so
"consumers cannot update by pulling" looks sound and is false. Probed 2026-09-18 against a local
repo with a moved tag: such a clone's only refspec is `+refs/tags/stable:refs/tags/stable`,
**forced**, so a pull updates the tag and fast-forwards the detached HEAD onto it. The AGENTS.md
rule is about a clone whose refspec does not name the tag. Nothing about the update mechanism needed
changing — only its discoverability, which is what `spowse self.update` is for.]

### The `/mnt` guard that was designed and then deleted

A refusal for clone destinations under `/mnt/` was planned, on the theory that a WSL user points
`~/projects` at `/mnt/c/...` so a Windows editor can see it, and that a checkout there loses exec
bits and case sensitivity. It was dropped 2026-09-18 without being built: the user ruled the premise
out — this repo is not developed on NTFS and the projects directory stays in the Linux home.
Recorded because the checking was done and should not be redone, and because one third of it
survives the premise:

- **Case-insensitivity was never a risk.** No two tracked paths in this repo differ only by case.
- **A lost exec bit would not stop an install.** `install.sh` runs `bash ./bootstrap.sh`, naming the
  interpreter, so none of the tracked `100755` files is invoked by path.
- **`CLAUDE.md` is the repo's only tracked symlink** (mode `120000` → `AGENTS.md`), and deliberately
  so — `AGENTS.md` requires a real symlink rather than a file carrying Claude Code's `@` import
  syntax. **So this repo cannot be checked out anywhere symlinks do not work**, and that fails at
  `git clone` rather than degrading. That is a property of the repo, not of any filesystem, and it
  outlives the WSL question entirely.

[DECISION: **deleted rather than carried as an open item.** An `[UNVERIFIED:]` tag describing a
scenario that has been ruled out is a backlog entry nobody can ever close, and it would have been
re-read as real work by every later session. The default flip loses nothing by the deletion: its
argument never rested on filesystems, and what is gone is only the extra WSL-specific weight — with
Windows paths ruled out, a WSL distro is just Linux and `~/.local/share` is right there for the same
reasons it is right anywhere.]

Two alternatives were rejected outright and are worth naming so they are not re-proposed.
**Symlinking `~/projects/power-user-linux-setup` at the new location** gives one tree two paths, and
which one the editable `.pth` recorded then decides what `Path(__file__).parent.parent` resolves to
— a footgun bought for cosmetics. **Prompting for the destination** is the developer-prompt
objection one step worse: it asks the majority case about a situation that does not apply to them.

## Never `sudo bash`, and it is worth stating because the simplification is obvious

"Why not just tell people to `sudo bash install.sh`" is the first thing anyone proposes, and it is
wrong. The script collects root the way `inv setup` already does, through `util.ensure_sudo()`, so
nothing runs as root that does not need to. Running the whole installer as root would also put a
root-owned checkout in the user's home directory and a root-owned `~/.local`, which is a machine
nobody can then use without `sudo`.

The same reasoning is why the one-liner is a download **then** a run rather than a pipe, and the two
arguments reinforce each other: a pasted line runs unreviewed code with access to sudo on a fresh
machine. That is the one place this repo's usual "it is only my machine" reasoning does not apply,
because the audience is whoever reads the README. `less /tmp/pulse-install.sh` before `bash` is only
possible in the two-step form, and pinning to `stable` is what makes what you inspected yesterday
the same bytes you run today.

## The conservatism that was added late

"Adopt, never clobber" was going to fetch and check out the requested ref in an existing checkout.
It ships using the checkout **exactly as it stands** — no fetch, no ref change — and says so on the
way past. A fetch-and-checkout against a directory that may hold uncommitted work is a clobber
wearing a git command, and this script's job is starting a machine rather than updating one that
already started. Anything at the destination that is not a PULSE checkout is a refusal naming
`--dir`, never a delete.

## Never move `stable` by hand

`publish-stable` in `.github/workflows/devcontainer.yml` is the only thing that should move the tag,
and it is gated on three jobs. Moving it by hand publishes whatever is broken at that commit, to
both consumers at once, because `install.sh` and `bootstrap-devcontainer.sh` pin the same ref.

Done once, 2026-09-08, to get `install.sh` reachable before the gate existed. It carried a
three-day-old `verify.all` regression to every `bootstrap-devcontainer.sh` consumer — `stable` went
from a container-green commit with no installer on it to one that had the installer and the
regression, so the one-liner started working and the container path broke in the same move. The two
could only be fixed together: repair the installer, then let `publish-stable` move the tag itself.

[PITFALL: **the breakage was three days old and nothing said so, which is the cost of a
`workflow_dispatch`-only trigger rather than a cost of the hand-move.** The container build had been
failing since 2026-09-05 and nobody dispatched it in between, so the hand-move was made against a
`stable` whose health was simply unknown. The hand-move published it; the missing trigger is what
made it invisible. Both halves are worth keeping separate, because only one of them is fixed.]

[PITFALL: **the local tag can disagree with the remote indefinitely.** A plain `git fetch` never
updates a tag that moved, so after `publish-stable` corrected `stable`, this machine's local ref
still pointed at the hand-moved commit — confirmed 2026-09-12, four days later. Anything reading
`git show stable:<file>` locally would have read the broken tree while looking authoritative. Ask
the host (`git ls-remote --tags origin stable`) or force it (`git fetch origin --tags --force`)
before trusting a local tag about what is published.]
