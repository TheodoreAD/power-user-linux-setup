---
status: idea
updated: 2026-08-30
repo: git@github.com:TheodoreAD/power-user-linux-setup.git
---

# A credential file the session touched is a credential file the session reads

## Context

Measured 2026-08-30, in a session that was deliberately trying to keep a credential out of the
transcript. The user had said so explicitly, and the agent had agreed and designed around it.

The sequence, which looks careful at every step and fails anyway:

1. The user obtained an `api_id`/`api_hash` and stored them in a password manager.
2. To avoid the values appearing in a `!` command — where they would land in the transcript — the
   agent created a `.env` **placeholder** with the Write tool and launched `code .env` so the user
   could paste them in an editor instead.
3. The user pasted and saved.
4. **The harness immediately delivered the file's new contents to the model** as a file-change
   notification: "changed on disk since you last read it", followed by the lines, secrets included.

The mechanism is ordinary and useful — a session is told when a file it has read or written changes
underneath it, so it does not act on stale content. It is only a leak because the file's whole
purpose was to hold something the model was not supposed to see, and because _the agent itself_
created and opened that file, which is what enrolled it in the watch.

[PITFALL: Launching an editor on a credential file from inside a session is not a way of keeping the
credential out of the session. It is the opposite: the session now owns that path, and the next save
is quoted back into the context in full. The editor makes it feel out-of-band, which is exactly why
it is worth writing down — nothing about the interaction looks like a paste into the chat.]

[PITFALL: The values land in **two** places under `~/.claude`, not one — the session's own
`projects/<id>.jsonl`, and a `file-history/<id>/<hash>@vN` snapshot taken because the agent wrote
the file with the Write tool. A cleanup that only knows about the transcript leaves the second
copy.]

[PITFALL: Neither can be redacted from inside the session. Auto mode's classifier blocks Bash writes
to `~/.claude/**` outright — correctly, it is exactly the self-referential-file case it exists for —
and the Edit tool needs the whole multi-megabyte transcript read first, which would pull the secret
back into context to remove it from context. Cleanup is a command the user runs, and it is safest
after the session has ended, since the transcript is being appended to live.]

## Open questions

[NEEDS CLARIFICATION: Whether the rule should be "never let the session near the file" or "never
have the session create it". The weaker version — the user creates the file entirely outside, and
the session only ever references it indirectly (`set -a; . ./.env; set +a; <command>`, or
`$(grep KEY .env | cut -d= -f2)`) — is enough to prevent this specific failure, and it keeps the
convenience of the session running the command that consumes the credential. The stronger version
costs the user more and buys little, since a file the session never read is never quoted back.]

[NEEDS CLARIFICATION: Whether this belongs in `~/AGENTS.md`'s Claude Code section as a rule, or in a
skill. It is harness behaviour rather than a machine fact, and the Claude Code section already
carries the auto-mode classifier's edit rules, which is the closest neighbour and the one a session
in this situation would already have loaded.]

## Recommended direction

Write it as a short rule under the Claude Code section, next to the existing auto-mode guidance:

> **Never create, open, or read the file that will hold a credential.** A file the session has
> written or read is watched, and its next save is delivered back into the context in full — an
> editor launched from the session (`code .env`) makes that worse, not better, because it feels
> out-of-band. Name the path and the format for the user, let them create and fill it outside the
> session entirely, and consume it only by indirection.

And a second line for the cleanup, since the natural instinct is to fix it in place and the tooling
refuses: the copies are the session transcript and the `file-history` snapshot, both under
`~/.claude`, both unwritable from inside the session, and the redaction is a user-run command after
the session ends.
