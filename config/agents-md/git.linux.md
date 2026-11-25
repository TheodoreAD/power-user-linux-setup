### git fetch/push needing an SSH key [needs PULSE's zprofile]

**Run the plain `git` command — `git push`, `git fetch`, no prefix and no wrapper.** That is the
normal case and it is what to reach for every time. Keys live unlocked in the desktop keyring's
agent from login. `~/.zprofile` points each shell at whichever agent actually holds keys, so this
normally just works with no prompt. `SSH_ASKPASS` (same Zenity helper, `SSH_ASKPASS_REQUIRE=prefer`)
pops a GUI passphrase dialog for a key that genuinely needs one. It blocks on user input and times
out if nobody is at the machine. No HTTPS/token workaround needed.

Everything below fires **only after a command has actually failed.** None of it is setup to do
first.

**When it fails with "Permission denied (publickey)", run `inv ssh.check` before anything else.** Do
not reach for `ssh-add`. Never ask the user for a passphrase on the strength of that error. This
machine runs two agents, the keyring's and the keychain's, and a shell pinned to the empty one fails
exactly that way while every key sits unlocked in the other. A session that read the failure as a
missing key ran `ssh-add`, and had the user type a passphrase into three dialogs for a key that was
already loaded elsewhere and needed none. A session's own shell snapshot is captured once and
survives a reboot, so an agent session is the most likely thing to be holding a stale socket.
`ssh-add -l` exits 0 with keys, 1 for a live but empty agent, 2 for no agent. Those last two look
alike and mean opposite things.

**When `ssh.check` has told you to, apply its verdict as a per-call prefix, not as an `export`.**
`ssh.check` ends with `export SSH_AUTH_SOCK=/run/user/1000/keyring/ssh` for a human's interactive
shell. An agent's Bash calls each get a fresh shell, so the export evaporates and the next command
fails exactly as before — which reads as "the fix didn't work" and sends the session back toward
`ssh-add`. Prefix instead, on every ssh call **for the rest of that diagnosis**:
`SSH_AUTH_SOCK=/run/user/1000/keyring/ssh git push`. A session that pushed with the prefix then ran
a bare `git fetch` two turns later and got the same publickey error, while every key sat unlocked in
the keyring's agent. The prefix is the repair for a shell pinned to the empty agent. It is not the
house style for pushing, and a session that has not seen a publickey failure should never be typing
it. `gh` is not affected, since it authenticates with its own token, so a green `gh` command is not
evidence that the shell's ssh agent is the right one.

### Writing the commit command

The command has one shape:

```shell
git commit -m "subject line

Body: what changed, by name; then what it is for, what it beat, what it cost.
Real blank lines, inside this one argument.

Rejected: an approach weighed and dropped (the reason)
Verified: inv quality.precommit
Co-Authored-By: ..." -- path/one path/two
```

Its parts, in order, and each is load-bearing. **Its own call**, with nothing chained before or
after it. **One `-m`**, never a series: git paragraphs several correctly, and the approval prompt
runs them into one unbroken line. **One double-quoted argument** carrying the whole message. **The
pathspec last**, after `--`.

**The message is prose**, so name a command, flag or file in plain words rather than in backticks. A
backtick or a `$` makes the shell run or substitute something before git sees it, and a `"` ends the
argument, so the rest of your paragraph becomes shell words. Apostrophes are safe and single quotes
are not the escape — they end the argument on the first one, and 73% of messages here have one.

All of it serves one thing: the approval prompt shows the **command**, so the message is what the
user reads to decide. `-F <file>` hides it behind a path, which is why that is the escape hatch for
a message that genuinely must carry a backtick and nothing else.

When it goes wrong the error quotes **your own sentence** back at you. Run `git log -1` before
retrying, since whether anything was committed differs per case. Same shape, same reasons, for
`gh pr create --body` and `gh issue comment`.
