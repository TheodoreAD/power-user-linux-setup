---
status: in-progress
updated: 2026-11-25
source_repo: github.com-personal/hekate
source_session: 5f84bc91-7291-42b4-9474-846d42d45b23.jsonl
source_moment: 2026-11-25T11:07:32Z
source_plan:
---

# The plans stores still commit with the private email address

## Context

GitHub's "block command line pushes that expose my email" protection is now on for the account, and
the machine's git identity was moved to the noreply address in another session. That fix lives in
`~/projects/github.com-personal/.gitconfig`, so it covers clones under that root only.

Both plans stores override it with their own `.git/config`, which still sets the private gmail
address:

```text
git -C ~/plans config --show-origin --get user.email            -> file:.git/config  (gmail)
git -C ~/plans-sensitive config --show-origin --get user.email  -> file:.git/config  (gmail)
```

plan-conveyor does not write that value. Its `install` only prints a reminder when a store has no
identity (`scripts/plans.py`, around line 7931), so the override was set by hand when the stores
were created.

Consequences:

- **`~/plans` has a GitHub remote (`TheodoreAD/plans`)**, so its next push will be refused with
  GH007. At filing time three unpushed commits carry the gmail address: `abad0d0`, `f5f16fc`,
  `c6eafcf`. They will need their author reset (`git commit --amend --no-edit --reset-author`
  through a rebase) once the identity is fixed, which is safe because they are unpublished.
- **Already-pushed history in `TheodoreAD/plans`** carries the gmail address on many commits. That
  repo is private. Rewriting published history is the user's call, as it was for hekate, where the
  user chose to leave the five affected commits as they are.
- `~/plans-sensitive` has no remote, so nothing is published from it, but it should match for
  consistency.

## Evidence

- The hekate session named in `source_session`, at `source_moment`: a hekate push was first refused
  with "GH007: Your push would publish a private email address", fixed there by resetting the author
  on three unpushed hekate commits. The user then chose "File a fix plan" for the stores.

## Open questions

[DECISION: the stores take the personal profile's identity from PULSE's global config, through
paths, not from their own `.git/config`. Asked "store-local config or a PULSE-managed profile", the
user answered "can't pulse add those to the global git config based on the paths?" (2026-11-25).
Landed in 4e5ac7f as `extra_directories` on a `[[git_profiles]]` entry: one
`includeIf.gitdir:<dir>/` per entry, pointing at the profile's existing `.gitconfig`, so nothing is
written into a store's tree. A separate profile per store was rejected because `inv git.configure`
writes `<directory>/.gitconfig`, which would land inside the store.]

[DECISION: re-author the unpushed store commits only once the hekate session committing into
`~/plans` has stopped (user's choice, 2026-11-25). At 15:45 that day 19 of the 21 unpushed commits
were hekate's, the last 4 minutes old; a rebase under a session committing every few minutes would
put its next commit on a detached HEAD.]

[DECISION: the already-pushed gmail commits in `TheodoreAD/plans` stay as they are (user's choice,
2026-11-25), as for hekate. The repo is private, and GH007 checks only the commits a push adds.]

## Remaining steps

Done 2026-11-25: this machine had no `~/.config/power-user-linux-setup/identity.toml`; its nine
global `includeIf` entries predated it. One was written whose `[[git_profiles]]` copy the nine
per-directory `.gitconfig` files unchanged, with `extra_directories` for both stores on the
`github.com-personal` profile. `inv git.configure` then warned about both stores' local
`user.email`, both were unset, and `git config --show-origin` in each store now resolves to the
personal profile's `.gitconfig` and the noreply address.

SSH followed the same day, at the user's request to make this machine "not special": the
hand-written `~/.ssh/config` (2020) held one live host, GitHub, and nine hosts of past employers and
clients reachable only on their old networks; its `Host *` block was already PULSE's `HOST_STAR`
word for word. The live key followed PULSE's naming but was RSA, so `key_path` learned to adopt an
existing key of any type (1d609e3). `identity.toml` now declares the GitHub host. The user ran the
archive step themselves, since agents' writes into `~/.ssh` are refused here: the old config and the
11 unused key files are in `~/.ssh/archive-2026-11-25/`, and `inv ssh.configure` wrote the config
fresh. Verified: `ssh -G github.com` resolves to the adopted key, `ssh -T git@github.com`
authenticates, `git ls-remote origin` answers.

1. Once hekate is idle: `git -C ~/plans log origin/master..HEAD`, confirm no commit there is still
   being amended by a live session (at 18:38 on 2026-11-25 there were 33 unpushed, the newest 6
   already on the noreply address, hekate's last one minute old), rebase with
   `--exec 'git commit --amend --no-edit --reset-author'` onto `origin/master`, then
   `plans.py push`.

## Recommended direction

- Reset the author on the unpushed store commits, then push through `plans.py push`.
- Consider proposing to agent-skills that plan-conveyor's `doctor` report a store whose identity is
  a private address while the store has a GitHub remote.
