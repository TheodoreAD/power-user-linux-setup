---
status: idea
updated: 2026-09-02
---

# `inv ssh.add` fires modal dialogs at a user who may not be at the machine

## Context

Carried out of `plans/2026-08-28-ssh-add-and-askpass-friction.md` at its retirement (2026-09-02),
which is where the reasoning below was worked out. That plan is deleted;
`plans.py archive --search
"non-interactive caller"` reads it back.

`ssh.add` cannot tell whether anything is watching. On a machine with genuinely unloaded keys it
invokes `SSH_ASKPASS` per key, and `ssh-add` retries a passphrase **three times** before exiting 1,
re-invoking the helper each time — so one agent-issued command can put three modal Zenity dialogs on
screen per key, at a user who may be away from the desk. Reported live during the incident that
produced the parent plan: _"you asked me for a lot of sudo prompts, what's up?"_ — they were SSH
passphrase prompts, for a key that did not need one.

**The sharp edge is already blunted, which is why this is an idea rather than a bug.** Three things
landed 2026-08-28 that make the common case cost nothing:

- `ssh.add` is excluded from every composite task, so no `inv setup` run reaches it.
- It skips keys the agent already holds, comparing fingerprints rather than filenames, so the
  ordinary re-run prompts zero times.
- `config/askpass-zenity.sh` now titles the dialog by which caller asked, so an SSH prompt is no
  longer indistinguishable from a sudo one.

What remains is the genuinely-unloaded case on a machine where nobody is present.

## Open questions

[NEEDS CLARIFICATION: what should a non-interactive caller get instead? The obvious answer — detect
no tty and print the command for the human to run — collides with `~/AGENTS.md`'s "never close with
'run X'" rule, which exists because this user works only through prompts and cannot type a shell
command. So "print it and stop" moves the dead end rather than removing it. Alternatives worth
weighing: skip with a clear message and a non-zero exit so the caller decides; or attempt only keys
whose `.pub` sibling proves they need no passphrase, and report the rest.]

[NEEDS CLARIFICATION: is `SSH_ASKPASS_REQUIRE=never` the mechanism rather than a tty probe? It would
make `ssh-add` fail immediately instead of popping anything, which is the desired behaviour for an
unattended caller and needs no detection at all. Unverified against this machine's helper.]

[NEEDS CLARIFICATION: does this generalise past `ssh.add`? Every task reaching a passphrase or
password through the Zenity helper has the same exposure, and `contributing/interactive-input.md`
already owns the rule that nothing run through invoke may wait for typed input. This may belong
there as a general constraint rather than as one task's fix.]

## Recommended direction

Decide the mechanism question first — if `SSH_ASKPASS_REQUIRE=never` does what it looks like it
does, there is no caller-detection to design and the change is one environment variable in the one
task that needs it. Only if that fails is a tty probe worth the collision with the "never close with
run X" rule, and that collision is then a real design question rather than a detail.
