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

[NEEDS CLARIFICATION: whether to rewrite the already-pushed gmail commits in `TheodoreAD/plans`.
Nothing requires it: GH007 checks only the commits a push adds.]

## Remaining steps

Done 2026-11-25: this machine had no `~/.config/power-user-linux-setup/identity.toml`; its nine
global `includeIf` entries predated it. One was written whose `[[git_profiles]]` copy the nine
per-directory `.gitconfig` files unchanged, with `extra_directories` for both stores on the
`github.com-personal` profile. `inv git.configure` then warned about both stores' local
`user.email`, both were unset, and `git config --show-origin` in each store now resolves to the
personal profile's `.gitconfig` and the noreply address.

1. **`[[ssh_hosts]]` in that `identity.toml` stays empty, and cannot be filled by copying.** A
   one-off script the user permitted read `~/.ssh/config` (agents' own reads there are denied by
   `Read(~/.ssh/**)`) and printed only what it derived: the file has no PULSE block, and none of its
   11 hosts uses a key named `<email>__<node>_ed25519`, the only path an `[[ssh_hosts]]` entry can
   resolve to (`tasks/ssh.py`, `key_path`). So listing them is a migration: `inv ssh.create-keys`
   would make new keys, which then need registering on every host. Whether to migrate, or leave SSH
   hand-managed here, is the user's call, and it is not this plan's subject. Until then
   `inv ssh.configure` must not run here: with an empty list it appends a block holding only PULSE's
   `Host *` defaults.
2. Once hekate is idle: `git -C ~/plans log origin/master..HEAD`, confirm no commit there is still
   being amended by a live session, rebase with
   `--exec 'git commit --amend --no-edit --reset-author'` onto `origin/master`, then
   `plans.py push`.

## Recommended direction

- Reset the author on the unpushed store commits, then push through `plans.py push`.
- Consider proposing to agent-skills that plan-conveyor's `doctor` report a store whose identity is
  a private address while the store has a GitHub remote.
