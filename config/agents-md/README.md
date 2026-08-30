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

## Which fragment a rule belongs in

Audience, not subject matter. A rule goes in `portable.md` only if it holds on another machine, run
by another agent; anything true because of how this machine is set up goes in `this-setup.md`, and
anything describing one harness's behaviour in `claude-code.md`.

The boundary is not currently clean — `portable.md` inherited wording from before the split, and
several of its rules name Claude Code's tools or this machine's paths. That is tracked, with the
measurement, in `plans/2026-08-30-portable-fragment-names-one-harness.md`; it is not a licence to
sweep, because each rule's wording was tuned for adherence and some of it deliberately names the
harness this machine actually runs.
