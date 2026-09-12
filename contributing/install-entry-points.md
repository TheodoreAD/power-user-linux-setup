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
