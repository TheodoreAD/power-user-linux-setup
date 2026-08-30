---
status: landed
updated: 2026-08-30
repo: git@github.com:TheodoreAD/power-user-linux-setup.git
---

# The ssh socket prefix gets applied when nothing has failed

## Context

Found by being the agent that got it wrong, in a `repo-tasks` session on 2026-08-29.

The session had fourteen commits to push. Before pushing it reasoned from `~/AGENTS.md`'s ssh
section and ran:

```
SSH_AUTH_SOCK=/run/user/1000/keyring/ssh git fetch --prune origin
SSH_AUTH_SOCK=/run/user/1000/keyring/ssh git push origin main
```

The fetch worked. The push was **denied by the user**, with: "you can do regular push, you don't
need the auth sock". A plain `git push origin main` then succeeded first try.

Nothing had failed beforehand. There was no `Permission denied (publickey)`, no `ssh.check` run, no
diagnosis — the prefix was applied prophylactically, as though it were the normal way to talk to the
remote on this machine.

**Second occurrence, same day**, in an `agent-skills` session that filed the other half of this plan
into the store. It ran the identical pair of commands with nothing having failed, no
`Permission denied (publickey)`, and no `inv ssh.check`. Different session, different repo, same
misread — which is the reproducibility evidence this plan wanted before spending words on a fix.

### What the rule actually says, and why it still read that way

The section is correct as written, and this is not a claim that it is wrong. It opens with the right
instruction — "Run the `git` command as normal" — and gates the diagnostic on a failure: "**When it
fails with `Permission denied (publickey)`, run `inv ssh.check` before anything else**".

The misread happens one paragraph later. That paragraph, added by `8a733d1`
(`agents-md: apply the ssh verdict as a prefix, not an export`), is the most emphatic text in the
section, and its own sentence is unconditional:

> Prefix instead, on every call that talks to the remote over ssh:
> `SSH_AUTH_SOCK=/run/user/1000/keyring/ssh git push`.

Read on its own — which is how an agent scanning for "what do I do about ssh here" reads it — "on
every call that talks to the remote over ssh" is a standing instruction, not the tail of a
conditional that started two paragraphs earlier. The scope word that would fix it ("its verdict") is
in the heading sentence, not in the imperative.

[PITFALL: the paragraph is emphatic _because_ the failure it fixes was expensive — a session that
exported instead of prefixing looked like the fix had not worked and went back toward `ssh-add`. The
emphasis is doing real work. So the fix here is not to soften it, which would reintroduce the
original problem; it is to bound it.]

[DECISION: **a plain `git push` is the normal way to talk to a remote on this machine, and the
`SSH_AUTH_SOCK` prefix is a remedy applied only after one has actually failed.** Stated by the user
2026-08-29: "only use the ssh auth sock thing if git push fails, we really want git push to be used
normally". That settles "is this worth a change at all" as yes, and it settles the direction: the
imperative is bounded, not softened. It also settles the second question this plan carried — bound
the imperative in place rather than restructuring a section two other sessions have recently worked
on.]

The cost of not fixing it is not only the denied call: a leading env assignment matches no allowlist
prefix, so the prophylactic form converts a silent operation into a recurring approval prompt.

## Design

1. **Bound the prefix imperative.** It currently reads as standing advice — "Prefix instead, on
   every call that talks to the remote over ssh" — with the conditional two paragraphs above it.
   Scope it to the diagnosis that produced it, so it cannot be read standalone as the normal way to
   push.
2. **State the default positively, where an agent scanning the section will hit it first.** The
   section already opens with "Run the `git` command as normal"; the failure mode is that the later
   emphatic paragraph outweighs it. Whatever shape is chosen has to leave "plain `git push`" as the
   more emphatic of the two.
3. **Keep the emphasis on the export-vs-prefix distinction.** That paragraph is emphatic because the
   failure it fixes was expensive — a session that exported instead of prefixing looked like the fix
   had not worked and went back toward `ssh-add`. Bounding its scope must not soften that.
4. **Audit the file for the same shape while it is open.** The pattern — a conditional stated once
   in a heading sentence, then an emphatic unconditional imperative below it that reads as standing
   advice — is a general authoring hazard for this file rather than an ssh-specific one, and it is
   cheap to look for now that there is a known instance. Record whatever it finds in
   `contributing/global-agents-md.md`.

Edit the fragment in `config/agents-md/`, never the deployed `~/AGENTS.md`, then
`inv deploy.all --name agents-md`.

Note for whoever picks this up: `plans/2026-08-28-ssh-add-and-askpass-friction.md` is `landed` and
already has a `## Migrated to` section, and it covers the _machine_ defects — the two agents,
`ssh.add` key discovery, the askpass dialog title. It does not cover when an agent should reach for
the prefix at all, so this is a new concern rather than an addition to that one.

## Files touched

- `config/agents-md/` — the fragment owning the "git fetch/push needing an SSH key" section.
- `contributing/global-agents-md.md` — the two occurrences, as evidence, under the matching heading.
- `~/AGENTS.md` / `~/.claude/CLAUDE.md` — regenerated by the deploy task, never edited directly.

## Verification

The check is behavioural, not textual: a later session with commits to push should reach for a plain
`git push` first. Until one does, the only evidence is the two occurrences above.

The wording was written and deployed 2026-08-30 — see "Migrated to" below. What stays unproven is
the behavioural check this plan set: that a later session with commits to push reaches for a plain
`git push` first. That is a question for the adherence watch, not for this plan.

[DEFERRED: the first session also never ran `inv ssh.check`, which is the step the rule actually
names. Whether the rule should say "and if you have not run `ssh.check`, you have no verdict to
apply" is a second, smaller clause with the same trade-off as the main change.]

## Migrated to

Landed 2026-08-30, deployed to `~/AGENTS.md`. `config/agents-md/this-setup.md`, "git fetch/push
needing an SSH key", rewritten per this plan's four design points: the default is stated first and
more emphatically ("run the plain `git` command — no prefix and no wrapper"), an explicit line says
everything below fires only after a command has actually failed, and the prefix paragraph is scoped
to "the rest of that diagnosis" while keeping its emphasis on export-vs-prefix intact.

Evidence, and the general authoring hazard the plan asked for — a conditional stated once in a
heading sentence followed by an emphatic imperative that reads as standing advice — are in
`contributing/global-agents-md.md` under "git fetch/push needing an SSH key".

**Deferred item resolved rather than carried:** the clause about having no verdict to apply without
running `ssh.check` is covered by the new wording, which opens the prefix paragraph on "When
`ssh.check` has told you to" and closes on "a session that has not seen a publickey failure should
never be typing it".
