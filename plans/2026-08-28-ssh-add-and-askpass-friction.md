---
status: in-progress
updated: 2026-08-28
---

## What has landed

**Defect 1 is fixed** (`f7a714a`, docs `18b6384`). `[packages.ssh]` now declares a `zprofile`
snippet that probes before choosing an agent — `ssh-add -l` exits 0 with keys, 1 for a live but
empty agent, 2 when it cannot connect — falls back to the desktop sockets, and only starts keychain
when none of them holds keys. The hand-written `~/.zprofile` block is gone, and nothing sources
`~/.keychain/<host>-sh` any more.

Verified from a real login shell three ways, each landing on the keyring socket with all three keys,
with `git fetch` authenticating: starting with no agent at all, starting pinned to keychain's empty
agent, and starting on a dead socket path.

Two findings from doing it, both worth keeping:

[PITFALL: **`keychain --inherit any` does not adopt an existing agent when `--quick` is also set.**
The documented behaviour — "inherit when a sock is set in the environment" — reads like the fix, and
keychain 2.8.5 still returned its own agent when tested directly against `SSH_AUTH_SOCK` pointed at
gcr. `--quick` short-circuits on keychain's own live pidfile before inheritance is considered. The
default is `--inherit local-once`, which inherits only on a **pid**, and a socket-activated
gcr-ssh-agent exports no `SSH_AGENT_PID` — so the default could never have inherited it either.]

[DECISION: **Keychain stays installed and stays in the login path, guarded.** It is the only thing
providing an agent on a TTY login or a session without gnome-keyring, which is a real case even
though this machine's `openssh-server` is disabled. Removing it would have been simpler and would
have silently removed that fallback. The guard costs up to three `ssh-add -l` calls per login.]

This was also the **first package to declare a `zprofile` field.** `tasks/zsh.py` has supported it
since `_snippets` was written; nothing had used it, which is why the keychain block was hand-written
and therefore not reproducible on another machine.

Defects 2 and 3 below are untouched.

## Context

Found 2026-08-28 when a power cut rebooted the machine mid-session and pushing one commit stopped
working. Diagnosing it produced one real defect and two aggravating ones, and the first diagnosis
was wrong in a way worth recording.

### 1. Two ssh-agents, and a session can be pointed at the empty one

This machine runs **two** SSH agents at once:

| agent                   | socket                   | state after the reboot           |
| ----------------------- | ------------------------ | -------------------------------- |
| `ssh-agent` (keychain)  | `/tmp/ssh-*/agent.<pid>` | **empty**                        |
| `gcr-ssh-agent` (GNOME) | `/run/user/1000/gcr/ssh` | all three keys, already unlocked |

GNOME's keyring unlocks the keys at login without anyone typing a passphrase. Keychain's agent
starts empty and stays that way until something loads keys into it.

A Claude Code session replays a shell snapshot captured once at session start, and that snapshot's
`SSH_AUTH_SOCK` named keychain's agent. After the reboot the socket path happened to still resolve —
a fresh `ssh-agent` came up as pid 2498 with socket `agent.2497`, the same numbers the stale
`~/.keychain/TD-PORTABLE-SSD-T5-sh` file recorded at 19:17 on the previous boot — so nothing looked
broken. The session was simply talking to a live, empty agent while every key sat unlocked in the
other one.

Symptom order, which is what makes this expensive: `git push` fails `Permission denied (publickey)`,
which reads as "no key loaded", which leads to `ssh-add`, which prompts for a passphrase, which
fails. Every signal points at the passphrase. The passphrase was never involved.

The fix in the moment is one env var — `SSH_AUTH_SOCK=/run/user/1000/gcr/ssh git push` — and the
keys were there the whole time.

This also contradicts `~/AGENTS.md`'s SSH rule, which says `SSH_ASKPASS` pops a dialog "instead of
failing with `Permission denied (publickey)`". That holds when there is one agent. With two, a
session can land on the empty one and get the publickey failure the rule says it won't.

[PITFALL: **The first diagnosis was "the passphrase must be wrong", and it was stated to the user as
a conclusion.** The evidence for it was that the environment was healthy, the key file intact, and
three entry attempts failed. Every one of those observations was true and the conclusion was still
wrong, because no one had enumerated the other agents. The user's own objection — "this used to
work, we just used it today" — was the correct signal and should have outranked the reasoning.
Enumerate agents (`ps`, then `ssh-add -l` against each candidate socket) **before** prompting a
human for a secret.]

### 2. `inv ssh.add` cannot load this machine's keys

It globbed for `~/.ssh/*TD-PORTABLE-SSD-T5_ed25519` and failed with a bare
`No such file or directory`. Every key here is `_rsa`:

```
<work-id-a>@<employer-a>__TD-PORTABLE-SSD-T5_rsa      <work-id-d>@<employer-d>__TD-PORTABLE-SSD-T5_rsa
<work-id-b>@<employer-b>__TD-PORTABLE-SSD-T5_rsa  teodor.dumitrescu@gmail.com__TD-PORTABLE-SSD-T5_rsa
teodor.dumitrescu@aws__TD-PORTABLE-SSD-T5_rsa   <work-id-c>@<employer-c>__TD-PORTABLE-SSD-T5_rsa
ec2-user__<EMPLOYER-D>_AWS_rsa
```

`inv ssh.create-keys` mints ed25519, so `ssh.add` assumes the keys it loads were minted by its
sibling task. These predate that convention. `~/.ssh/config` references them by absolute path and
works fine — only the loader is broken, and it breaks on **any** machine whose keys this repo did
not create, which is every machine adopting PULSE onto an existing home directory.

The message is the second half: a raw glob failure naming a path that was never supposed to exist,
with no statement of what it looked for or why. It reads like a missing file rather than an unmet
assumption.

### 3. The askpass dialog cannot be told apart from a sudo prompt

`config/askpass-zenity.sh` passes the caller's prompt through verbatim — correct, and its comment
says so — but hardcodes `--title="Authentication required"`. Sudo and SSH produce visually identical
windows, and the title is what a user registers on the third identical popup. Reported live: "you
asked me for a lot of sudo prompts, what's up?" They were SSH passphrase prompts, for a key that did
not need one.

Compounding it: `ssh-add` retries a passphrase three times before exiting 1, re-invoking
`SSH_ASKPASS` each time. One agent-issued command means three modal dialogs at a user who may not be
at the machine.

## Open questions

[NEEDS CLARIFICATION: should `ssh.add` glob both key types, or read `~/.ssh/config`? Globbing
`*_ed25519` **and** `*_rsa` is a one-line fix. Reading `IdentityFile` lines out of `~/.ssh/config`
is strictly more correct — that file is what `ssh` actually consults, `inv ssh.configure` writes it,
and it picks up a key of any algorithm at any path — but it makes the task parse a file it currently
only writes. Lean the config read, since the glob fix leaves the same class of bug waiting for the
next algorithm. Either way it should first check whether the keys are **already loaded in some
agent** and do nothing if so.]

[NEEDS CLARIFICATION: should an agent session run `ssh.add` at all? Three dialogs from one command,
at a user who may be away, is the same reasoning `AGENTS.md` already applies to GNOME
session-mutating tasks. The alternative is that the task detects a non-interactive caller and prints
the command for the human instead — which collides with `~/AGENTS.md`'s "never close with 'run X'"
rule, so it needs deciding rather than defaulting.]

## Recommended direction

Ordered by what actually cost time, not by size. Item 1 has landed; see "What has landed" above.

1. ~~**Make the agent situation deterministic.**~~ Done — `f7a714a`.
2. **Teach `verify.all` or `ssh.check` to report it.** There is no read-only task that answers "are
   my keys loaded, and in which agent" — which is why this took a live debugging session. A check
   that enumerates agent sockets and lists identities per socket would have shown the answer in one
   command. This is the highest-value item after (1) and is purely additive.
3. **Title the askpass dialog from its caller.** The script already receives a prompt beginning
   `[sudo] password for …` or `Enter passphrase for key …`; branch `--title` on that instead of
   hardcoding. Two lines, and it removes the misattribution entirely. Redeploy with
   `inv deploy.all --name <pkg>`, never by editing the deployed copy.
4. **Fix `ssh.add`'s key discovery and its error message**, per the second open question.

(2) is now the one that matters most. The failure is prevented, but nothing yet answers "which agent
am I on and does it have my keys" without a human running `ssh-add -l` against candidate sockets by
hand — which is exactly the step that was missing when this happened. A guard that works is not the
same as a guard you can confirm is working.
