---
status: landed
updated: 2026-08-28
---

## What has landed

All three defects are fixed, plus the diagnostic whose absence made the first one expensive.

| item                                | commit                    |
| ----------------------------------- | ------------------------- |
| 1. wrong agent — the zprofile guard | `f7a714a`, docs `18b6384` |
| the `ssh.check` diagnostic          | `fc63a5c`, docs `4632f22` |
| 2. `ssh.add` key discovery          | `fc63a5c`, docs `4632f22` |
| 3. askpass dialog title             | `23cdd50`                 |

**Defect 1** (`f7a714a`, docs `18b6384`). `[packages.ssh]` now declares a `zprofile` snippet that
probes before choosing an agent — `ssh-add -l` exits 0 with keys, 1 for a live but empty agent, 2
when it cannot connect — falls back to the desktop sockets, and only starts keychain when none of
them holds keys. The hand-written `~/.zprofile` block is gone, and nothing sources
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

**The diagnostic** (`fc63a5c`). `inv ssh.check` reports which socket this shell is on, what each
desktop socket holds, which declared keys are loaded, and a verdict naming the socket to export when
a better one exists. Read-only: it never starts an agent, loads a key, or prompts. Run against this
session's own broken shell it reproduces the original failure and prints the fix, which is the test
that mattered.

**Defect 2** (`fc63a5c`). `ssh.add` reads `IdentityFile` entries from `~/.ssh/config` — what `ssh`
itself consults — instead of globbing `*<node>_ed25519`. The glob survives as a fallback when no
config exists, now covering `rsa` too. It also skips keys the agent already holds, comparing
fingerprints rather than filenames since a loaded key has no path, so re-running costs no prompts. A
key with no `.pub` sibling can't be fingerprinted without its passphrase, so it stays pending and
says so instead of silently prompting every run.

**Defect 3** (`23cdd50`). The askpass dialog titles itself from the caller's prompt — "SSH key
passphrase", "sudo password", or the old generic string. Verified with a stubbed `zenity` on PATH
checking the `--title` argument for all three shapes.

Twelve tests cover the pure helpers: exit-code labels, socket ordering, `IdentityFile` parsing
(case-insensitivity, dedupe, `~` expansion, quotes, comments) and fingerprint extraction from both
`ssh-add -l` and `ssh-keygen -lf`.

## Migrated to

Nothing needs a separate home. The behaviour is in `tasks/ssh.py`, `config/askpass-zenity.sh` and
`[packages.ssh]`'s `zprofile` snippet, each carrying its reasoning in comments; the user-facing half
is `docs/ssh.md`'s "Which agent a shell talks to", which holds the two-agent table, the symptom
chain, the diagnosis and the dated incident.

The one thing worth keeping that has no natural code home is the `--inherit` finding below — it is a
rejected alternative, and the next person reading keychain's man page will reach the same wrong
conclusion. Left tagged here; it belongs in a `contributing/` page only if this file is ever deleted
rather than kept as the record of a landed change.

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

## Questions this raised, and how they were answered

[DECISION: **`ssh.add` reads `~/.ssh/config`, with the glob as a fallback.** The glob was the
one-line fix and would have left the same class of bug waiting for the next key algorithm;
`IdentityFile` is what `ssh` itself consults, so it is correct by construction and picks up a key of
any type at any path. The task now parses a file it previously only wrote, which is the cost. The
glob remains for a machine with no `~/.ssh/config` at all, widened to cover `rsa` as well as
`ed25519`. It also checks what the agent already holds and skips those keys, which was the other
half of the question.]

[DECISION: **Fingerprints, not filenames, decide whether a key is already loaded.** An agent knows
nothing about paths, so a name comparison would re-add a key it already holds under a different name
— and re-adding means a passphrase prompt, which is the cost this was meant to avoid. The
fingerprint comes from the `.pub` sibling, never the private key, which can prompt.]

[DEFERRED: **`ssh.add` still does not detect a non-interactive caller.** The sharp edge is blunted —
it is excluded from every composite task, and skipping already-loaded keys means the common re-run
now prompts zero times — but an agent session invoking it on a machine with genuinely unloaded keys
still fires a dialog per key, three times per key, at a user who may not be there. The alternative
is detecting a non-interactive caller and printing the command for the human instead, which collides
with `~/AGENTS.md`'s "never close with 'run X'" rule. Still wanted, still undecided; this is the
item that has to move to an open plan before this file can be deleted.]

## Recommended direction

All four items are done — see "What has landed" above. They were, in the order they mattered: make
the agent choice deterministic; give it a read-only check so the guard can be confirmed rather than
assumed; title the askpass dialog; fix `ssh.add`'s key discovery.

The ordering held up. The guard prevents the failure, but the check is what makes a future variant
of it self-diagnosing — and a guard that works is not the same as a guard you can confirm is
working.
