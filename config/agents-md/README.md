# `~/AGENTS.md` fragments

The assembled `~/AGENTS.md` is built from the fragments in this directory, in `order`:

| order | fragment         | owns                                                        |
| ----- | ---------------- | ----------------------------------------------------------- |
| 10    | `this-setup.md`  | this machine, this user's own repos, PULSE's own mechanisms |
| 20    | `claude-code.md` | behavior specific to the Claude Code harness                |
| 30    | `portable.md`    | conventions that hold on any machine, with any agent        |

Each fragment contributes whole `##` sections; the assembler never merges at the rule level, so no
cluster is split across two fragments. A rule may _mention_ another fragment's subject matter — the
Claude Code permission-mode rule points at PULSE's `cli-allowlist` pipeline, for instance — what it
may not do is live half in one fragment and half in another.

Design, rationale, and the rule-by-rule triage behind the split:
`plans/2026-08-26-agent-artifact-authoring-decoupling.md`, "Design — the assembled `~/AGENTS.md`".
Each rule's evidence and the admission criteria for a new one stay in
`contributing/global-agents-md.md`.

## Editing

Edit a fragment, then `inv deploy.all --name agents-md`. Never edit `~/AGENTS.md` directly: it is
regenerated in full from these fragments, so nothing at the destination is a source of truth.

A hand-edit there is caught rather than clobbered — `deploy.classify` compares the file against what
PULSE last wrote, and `deploy.deploy` prints the diff and asks, defaulting to keeping your version —
but the edit still only exists on that one machine until it is ported back into a fragment here.
That protection is the deploy manifest's, not the markers': unlike `~/.zshrc`, where
`util.ensure_block` writes one region into a file the user owns, this whole file is PULSE-owned and
rewritten end to end. The `<!-- PULSE::agents-md/<stem> -->` markers are provenance — they say which
fragment to go edit for a given section — not an ownership boundary.

## Still to do on the content itself

The split moved rules between clusters but deliberately did **not** rewrite their wording. About a
dozen rules in `portable.md` still name Claude-specific tools (`Read`/`Grep`/`Edit`,
`AskUserQuestion`, "plan mode") or this user's own setup (`inv quality.precommit`, "most of this
user's repos") in passing. They generalize with one-line rewrites, but each one is a rule whose
exact wording was tuned for adherence — rewrite them one at a time, not in a sweep, per
`contributing/global-agents-md.md`.
