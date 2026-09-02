# Choosing an SSH agent, and loading keys into it

Design rationale for `[packages.ssh]`'s `zprofile` snippet, `inv ssh.check` and `inv ssh.add`.
[`docs/ssh.md`](../docs/ssh.md)'s "Which agent a shell talks to" is the user-facing half — the
two-agent table, the symptom chain and what to run. This page holds the alternatives that were
rejected, which is the part a future reader will otherwise re-derive.

Migrated 2026-09-02 from the retired `plans/2026-08-28-ssh-add-and-askpass-friction.md`
(`python3 ~/.agents/skills/plan-docs/scripts/plans.py archive --search "keychain"` reads it back).

## Keychain stays installed, and stays in the login path

Removing `keychain` would have been the simpler fix and would have silently removed the only thing
providing an agent on a **TTY login, or any session without gnome-keyring** — a real case even on a
desktop machine, and the whole reason the package is declared. So the snippet guards it rather than
dropping it: it probes for an agent that actually holds keys, and starts keychain only when none
does. The guard costs up to three `ssh-add -l` calls per login, which is the price of not losing the
fallback.

Exit codes are the probe, and they are the part worth remembering: `ssh-add -l` exits **0** with
keys, **1** for a live but empty agent, and **2** when it cannot connect at all. The middle one is
the case that produced the incident — a live agent holding nothing looks identical to a working one
from every angle except this exit code.

## `keychain --inherit any` does not do what its documentation implies

The documented behaviour — "inherit when a sock is set in the environment" — reads exactly like the
fix for a shell pinned to the wrong agent, and it is not.

- **`--quick` short-circuits on keychain's own live pidfile before inheritance is considered.** With
  both flags set, keychain returns its own agent regardless of what `SSH_AUTH_SOCK` names. Tested
  directly against keychain 2.8.5 with `SSH_AUTH_SOCK` pointed at gcr's socket.
- **The default, `--inherit local-once`, inherits only on a PID** — and a socket-activated
  `gcr-ssh-agent` exports no `SSH_AGENT_PID` at all, so the default could never have inherited it
  either.

Both paths fail for different reasons, which is why reading the man page produces the wrong
conclusion twice. The snippet therefore chooses the socket itself rather than asking keychain to
adopt one.

## `ssh.add` reads `~/.ssh/config`, with the glob only as a fallback

The original implementation globbed `~/.ssh/*<node>_ed25519`, on the assumption that the keys it
loads were minted by its sibling `ssh.create-keys`. That breaks on **any machine whose keys this
repo did not create** — which is every machine adopting PULSE onto an existing home directory, and
was the case here: seven keys, every one `_rsa`, none matching the glob.

`IdentityFile` is what `ssh` itself consults, so parsing it is correct by construction and picks up
a key of any algorithm at any path. The cost is that the task now parses a file it previously only
wrote. The glob survives for a machine with no `~/.ssh/config` at all, widened to cover `rsa`.

The one-line fix — adding `rsa` to the glob — was rejected deliberately: it would have left the same
class of bug waiting for the next key algorithm.

## Fingerprints, not filenames, decide whether a key is already loaded

An agent knows nothing about paths, so comparing names would re-add a key the agent already holds
under a different name — and re-adding means a passphrase prompt, which is the cost the check exists
to avoid. The fingerprint comes from the `.pub` sibling, **never** the private key, which can prompt
on its own. A key with no `.pub` sibling therefore cannot be fingerprinted without its passphrase;
it stays pending and says so, rather than silently prompting on every run.

## What is deliberately not here

- **The behaviour itself** — it is in `tasks/ssh.py`, `config/askpass-zenity.sh` and
  `[packages.ssh]`'s `zprofile`, each carrying its reasoning in comments.
- **"Enumerate agents before asking a human for a secret."** That lesson — the first diagnosis in
  the incident was "the passphrase must be wrong", stated as a conclusion, on evidence that was
  entirely true and led nowhere — is a rule for agents rather than a note for this repo, and it
  lives in `~/AGENTS.md`'s ssh section as "run `inv ssh.check` before anything else". A second copy
  here would drift.
- **The remaining open item.** `ssh.add` still cannot tell whether a human is present:
  `plans/2026-09-02-ssh-add-prompts-a-user-who-is-not-there.md`.
