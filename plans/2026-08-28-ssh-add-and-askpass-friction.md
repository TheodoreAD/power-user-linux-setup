---
status: idea
updated: 2026-08-28
---

## Context

Found 2026-08-28 after a power cut emptied the `keychain`-managed ssh-agent mid-session. Getting a
key loaded again to push one commit produced three defects in a row, none of which is the power cut.

**1. `inv ssh.add` cannot load this machine's keys.** It globbed for
`~/.ssh/*TD-PORTABLE-SSD-T5_ed25519` and failed with a bare `No such file or directory`. Every key
in `~/.ssh/` on this machine is `_rsa`:

```
<work-id-a>@<employer-a>__TD-PORTABLE-SSD-T5_rsa
<work-id-b>@<employer-b>__TD-PORTABLE-SSD-T5_rsa
teodor.dumitrescu@aws__TD-PORTABLE-SSD-T5_rsa
<work-id-c>@<employer-c>__TD-PORTABLE-SSD-T5_rsa
<work-id-d>@<employer-d>__TD-PORTABLE-SSD-T5_rsa
teodor.dumitrescu@gmail.com__TD-PORTABLE-SSD-T5_rsa
ec2-user__<EMPLOYER-D>_AWS_rsa
```

`inv ssh.create-keys` mints ed25519 (`ssh-keygen -t ed25519`, per `docs/ssh.md` and `index.md`'s
manual-steps table), so `ssh.add` assumes the keys it loads were minted by its sibling task. These
predate that convention. `~/.ssh/config` references them by absolute path and works fine — only the
loader is broken, and it breaks on **any** machine whose keys this repo did not create, which is
every machine adopting PULSE onto an existing home directory.

The error message is the second half of the problem: a raw glob failure names a path that was never
supposed to exist, with no statement of what it was looking for or why. It reads like a missing file
rather than an unmet assumption.

**2. The askpass dialog cannot be told apart from a sudo prompt.** `config/askpass-zenity.sh` passes
the caller's prompt through verbatim — correct, and its comment says so explicitly — but hardcodes
`--title="Authentication required"`. Sudo and SSH therefore produce visually identical windows, and
the title is what a user registers on the third identical popup. Reported live: "you asked me for a
lot of sudo prompts, what's up?" — they were SSH key passphrase prompts.

**3. One agent-issued `ssh-add` can produce three GUI dialogs.** `ssh-add` retries a passphrase up
to three times before exiting 1, re-invoking `SSH_ASKPASS` each time. From an agent session that is
three modal dialogs from one tool call, with no way for the agent to know whether the user is at the
machine. Combined with (2), the experience is three indistinguishable auth popups attributed to the
wrong subsystem.

Not a defect, recorded so it isn't re-investigated: the askpass path itself works. `DISPLAY=:1`,
`WAYLAND_DISPLAY=wayland-0` and `XDG_RUNTIME_DIR=/run/user/1000` were all live, the dialogs
appeared, and the key file is structurally intact (3479 bytes, correct OpenSSH header and footer).
The load failed because the passphrase entered did not match — a human problem, not a setup one.

## Open questions

[NEEDS CLARIFICATION: should `ssh.add` glob both key types, or read `~/.ssh/config`? Globbing
`*_ed25519` **and** `*_rsa` is a one-line fix and stays consistent with how the task already thinks.
Reading the `IdentityFile` lines out of `~/.ssh/config` is strictly more correct — that file is what
`ssh` actually consults, `inv ssh.configure` writes it, and it would pick up a key of any algorithm
at any path — but it makes the task depend on parsing a file it currently only writes. Lean the
config read, since the glob fix leaves the same class of bug waiting for the next algorithm.]

[NEEDS CLARIFICATION: does `ssh.add` warn about RSA at all? These keys work, but RSA with SHA-1
signatures is deprecated by GitHub and OpenSSH 8.8+ refuses `ssh-rsa` by default; these presumably
still work via `rsa-sha2-256/512`. A loader that silently loads deprecated keys forever is not
obviously right, but nagging on every load is worse. Possibly a one-time note from
`inv ssh.configure` rather than from `add`.]

[NEEDS CLARIFICATION: should an agent session run `ssh.add` at all? Point 3 means the answer may be
no — the same reasoning `AGENTS.md` already applies to GNOME session-mutating tasks: an agent
shouldn't fire modal dialogs at a user who may not be present. The alternative is that the task
detects a non-interactive caller and prints the command for the human to run instead. That is the
`~/AGENTS.md` "never close with 'run X'" tension in reverse, and worth deciding deliberately.]

## Recommended direction

Three fixes, independent, smallest first.

1. **Title the askpass dialog from its caller.** `askpass-zenity.sh` already receives a prompt that
   begins `[sudo] password for …` or `Enter passphrase for key …`; branch the `--title` on that
   rather than hardcoding one string. Two lines, no new dependency, and it removes the entire
   misattribution. Redeploy with `inv deploy.all --name <pkg>` per the repo's own rule against
   editing the deployed copy.
2. **Make `ssh.add` find the keys that exist.** Per the open question above, preferably by reading
   `IdentityFile` from `~/.ssh/config`. Whichever way it resolves, the failure message has to name
   the assumption — "no keys matching … ; `inv ssh.create-keys` mints ed25519, this machine may have
   keys it did not create" — not just echo a path that never existed.
3. **Decide the interactive-caller question** before either lands, since it changes what `ssh.add`
   should do when it succeeds at finding keys but cannot safely prompt.

Worth doing in that order because (1) is the one that already cost a real interruption, and it is
independent of the other two.
