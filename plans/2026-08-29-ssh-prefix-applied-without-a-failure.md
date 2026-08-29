---
status: idea
updated: 2026-08-29
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

## Open questions

[NEEDS CLARIFICATION: is this worth a change at all? A careful reader gets it right from the text as
it stands, and the cost of the failure is one denied tool call and one user correction — cheap and
self-correcting, which is the profile of something that should _not_ earn words in an always-loaded
file. Against that: the prefix is not free, since a leading env assignment matches no allowlist
prefix and so prompts on every such call, and an agent applying it by default converts a silent
operation into a recurring approval. Worth pricing before writing anything.]

[NEEDS CLARIFICATION: if it is worth a change, is it one clause or a restructure? The minimal
version is bounding the imperative in place — "on every call that talks to the remote over ssh
_while that diagnosis stands_" — which costs no lines and no rule count. The alternative is moving
the prefix paragraph under the failure branch so it cannot be read standalone, which is a
restructure of a section another session has recently worked on twice.]

[NEEDS CLARIFICATION: does the same shape exist elsewhere in the file? The pattern is a conditional
stated once in a heading sentence, then an emphatic unconditional imperative below it that reads as
standing advice. That is a general authoring hazard for this file rather than an ssh-specific one,
and it is cheap to look for now that there is a known instance.]

## Recommended direction

Bound the imperative rather than softening it, if anything is done at all. The emphasis earns its
place; only its scope is loose.

Note for whoever picks this up: `plans/2026-08-28-ssh-add-and-askpass-friction.md` is `landed` and
already has a `## Migrated to` section, and it covers the _machine_ defects — the two agents,
`ssh.add` key discovery, the askpass dialog title. It does not cover when an agent should reach for
the prefix at all, so this is a new concern rather than an addition to that one.

[DEFERRED: the same session also never ran `inv ssh.check`, which is the step the rule actually
names. Whether the rule should say "and if you have not run `ssh.check`, you have no verdict to
apply" is a second, smaller clause with the same trade-off as the first question above.]
