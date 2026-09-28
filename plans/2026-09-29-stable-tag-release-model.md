---
status: idea
updated: 2026-09-29
---

# `stable` is three weeks behind, and the tag was never the problem

## Context

Asked 2026-09-29: revisit the `stable` tag decisions, and compare them with the rest of the repo
family and with what comparable tools do. What exists today, and where each part is written down:

- `install.sh` and `bootstrap-devcontainer.sh` both default to `REF="stable"` and shallow-clone
  `--branch stable --depth 1`. The one-line URL is `raw.githubusercontent.com/…/stable/install.sh`.
- `publish-stable` in `.github/workflows/devcontainer.yml` runs `git tag -f stable` and
  `git push origin stable --force`. It needs three jobs to pass first: `smoke-test`, `install-smoke`
  and `quality`.
- `devcontainer.yml` is `workflow_dispatch`-only on purpose. AGENTS.md says not to uncomment its
  `push` trigger without asking.
- `spowse self.update` (`tasks/selfupdate.py`) runs `git pull --ff-only` and follows whatever ref
  the checkout was cloned from.
- `contributing/install-entry-points.md` has the hand-move incident from 2026-09-08 and the finding
  that `git pull` works in a tag clone.

### What the published state actually is (measured 2026-09-29)

- `git ls-remote --tags origin` returns exactly one tag: `stable` at `2a2a152`, dated 2026-09-08.
  `origin/master` is **231 commits** ahead of it.
- `gh run list --workflow devcontainer.yml` shows the last dispatch was 2026-09-08. There have been
  four dispatches in total.
- `git show 2a2a152:install.sh` is the version the one-liner serves today. It is missing several
  things the current `README.md` and `docs/index.md` describe:
  - it still clones into `~/projects/power-user-linux-setup`;
  - it has no `--dev` flag and does not adopt a checkout at the old location;
  - there is no `tasks/selfupdate.py`, so `spowse self.update` does not exist on a fresh install.
- `ci.yml` runs `quality` and `install-smoke` on **every push to master**, and every recent run is
  green. So two of the three gates are already met on every commit. Only the devcontainer
  `smoke-test` is not, and only because nobody dispatches it.

[PITFALL: **the docs site is built from `master`, while the installer serves `stable`.** Anything
added to the installer is documented as soon as it merges, but fresh machines don't get it until the
next promotion. At 231 commits behind, the README's own install section describes behaviour the URL
it gives does not have. Nothing warns about this, because each half looks correct when checked on
its own.]

[PITFALL: **a `stable` nobody moves is the same failure as the 2026-09-08 incident, in the other
direction.** Then, a `stable` whose health nobody knew got published by hand. Now, a healthy
`master` is never published. Both come from the dispatch-only trigger.
`contributing/install-entry-points.md` already names the trigger as "the half that is not fixed".]

### Does `git pull` work in a tag clone? Re-verified, because two sources disagreed

The community research concluded that `git pull` fails in a `--branch stable --depth 1` clone
because HEAD is detached. `contributing/install-entry-points.md` says it works. A probe on
2026-09-29 settles it:

- make a bare-bones repo;
- clone it with `--branch stable --depth 1` over `file://`;
- move the tag upstream;
- run `git pull --ff-only`.

The clone's only refspec is `+refs/tags/stable:refs/tags/stable`, git printed `t [tag update]`, and
the pull fast-forwarded the detached HEAD with exit 0. The contributing doc is right.

[DECISION: **the update path is not a reason to switch from a tag to a branch.** "A moving tag
breaks `git pull`" is the usual argument against moving tags. It does not apply to this clone shape,
because git's own `write_refspec_config` forces the one refspec it writes.]

### The repo family

Surveyed across every repo under `github.com-personal`:

- **repo-tasks** is the only repo with versioned tags. It uses immutable annotated semver tags
  (`v0.2.0`…`v0.6.0`) and cuts GitHub Releases by hand-dispatch. Consumers pin `tag = "v0.6.0"`. The
  rationale is in its `contributing/consumer-sweep.md`, settled 2026-09-26. Its README deliberately
  leaves the day-to-day global install unpinned.
- **invoke-stubs, agent-skills, scaffoldapy and the `*-polite-mcp` repos** release by pushing to
  `main`. Consumers take the default branch, or a commit for copier. invoke-stubs bumps its
  `version` field but tags nothing, and its five consumers' lockfiles sit on three different
  commits.
- **Nothing else has a moving tag.** `stable` is unique to this repo.

That is not an inconsistency to fix. repo-tasks is a library resolved into other environments, and
semver means something to its consumers. This repo is an application installed onto a machine, with
no API for a version number to describe. The two models answer different questions.

### What comparable tools do

Details are in the research in this session. The tools cluster into five patterns:

| pattern                                      | examples                                                                        | fits a checkout-based setup repo?                                       |
| -------------------------------------------- | ------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| default branch HEAD                          | oh-my-zsh, yadm, chezmoi's dotfiles clone, ansible-pull                         | every merge ships; oh-my-zsh added an opt-in time cooldown to soften it |
| named ref that moves                         | **omakub's `stable` branch**, Actions `v1`, devcontainer `:1`                   | this repo; omakub is the closest analogue and moves its branch by hand  |
| immutable tags, "latest" resolved at install | Homebrew (a local `stable` branch computed from the newest tag), nvm, uv, zimfw | gives history and pinning; needs a release step                         |
| channel manifest                             | rustup, k3s `channel.yaml`, docker's repo components                            | overkill for one channel and one consumer class                         |
| consumer pins                                | dotbot as a submodule, SHA-pinned Actions                                       | this is `--ref`, already supported                                      |

Two mitigations cut across the patterns:

- **a deliberate lag:** oh-my-zsh's `cooldown`, and omarchy's stable mirror held a month behind;
- **stamping the commit into what runs:** `get.docker.com` prints the commit it was built from.

Git's own documentation (`git tag`, "On Re-tagging") calls moving a published tag "the insane
thing". That doesn't apply to this repo's installers, since the single-branch refspec is forced (see
above). It does apply to anyone with a full clone: a plain `git fetch` refuses to update a moved
tag. That is the same stale local `stable` that `install-entry-points.md` recorded on 2026-09-12.

## Open questions

[NEEDS CLARIFICATION: **What should move `stable`, now that only one of three gates is manual?**
There are three shapes, in order of how much the deliberate dispatch-only stance would change:

(a) Keep dispatch-only, and make staleness visible: CI reports "stable is N commits / D days
behind", or `inv` does.

(b) A scheduled promotion, weekly for example, that runs the devcontainer smoke test and promotes on
green. This is the lag pattern from oh-my-zsh and omarchy: it adds a cooldown for free and keeps the
heavy container build off every push.

(c) Re-enable the commented `push` trigger. AGENTS.md says to check with the user first, and the
reason it gives is that the pipeline is still being iterated on.]

[NEEDS CLARIFICATION: **Add an immutable tag per promotion?** For example, calver `v2026.09.29`
(with a `.N` suffix for a second promotion the same day), cut by `publish-stable` next to the move.
It would give:

- a history on the host of what was published and when, which the moving tag alone cannot give;
- a real "same bytes tomorrow": the comment in `install.sh` at `REF=` claims that today, and a
  moving ref cannot deliver it;
- a pin for a reproducible install via `--ref v2026.09.29`.

The cost is one more line in the job and a tag list that grows. Calver rather than semver, because
nothing here has an API for a major version to break. Optionally, a GitHub Release per promotion
carrying `git log --oneline <previous>..<new>` as its notes.]

[NEEDS CLARIFICATION: **Should the installers print the commit they cloned?** This is docker's
pattern: `install.sh` would name the resolved SHA, and the calver tag if (2) lands, on the line that
already says which source it is cloning. It costs nothing and turns "which version did I get" into
something visible on screen.]

[NEEDS CLARIFICATION: **What should the docs do about the gap between `master` and `stable`?** With
a regular cadence the gap shrinks to days and can simply be accepted. Otherwise there are two
options: the docs site builds from `stable`, or the install section says it describes `master`.
Building from `stable` would also hold back docs for things unrelated to installing, which is
probably worse.]

## Recommended direction

Keep `stable` as a tag. Switching to a branch (the omakub shape) would buy a git-native update path
this repo already has. It would also break every existing clone, whose one refspec names the tag, or
leave a branch and a tag both called `stable`, which makes the raw URL ambiguous.

What to fix is the cadence. Two of the three gates already pass on every push, so a **scheduled
promotion** (b) that runs the container smoke test and moves `stable` on green fixes the staleness.
It also adds a deliberate lag, and leaves the `push` trigger decision alone. Add the **calver tag
per promotion** and the **SHA line in the installers** in the same change: together they are about
five lines, and they make the comment in `install.sh` true. Then run one manual dispatch now to
publish the 231 commits, but only after the devcontainer smoke test passes on `ubuntu-24.04`. That
is the one gate `2026-09-28-ci-stops-testing-24-04-when-ubuntu-latest-moves.md` still lists as
unverified, so the same dispatch closes it.
