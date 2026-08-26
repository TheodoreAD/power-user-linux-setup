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

## Interim state — read this before editing

**`config/global-AGENTS.md` is still the deployed source.** The assembly mechanism (the `agents_md`
`setup.toml` field) does not exist yet, so these fragments are not wired to anything: they are the
content split, landed ahead of the mechanism so the two changes stay reviewable apart.

That means the content is duplicated right now. Until the mechanism lands:

- **A rule change goes in `config/global-AGENTS.md`** — that is what `inv deploy.all` actually
  deploys — **and then into the matching fragment here.** Editing only one side silently drops the
  change or resurrects an old one when the mechanism lands.
- Nothing here is deployed, so a mistake in a fragment cannot affect a live session yet.

Delete this section when the fragments become the source and `config/global-AGENTS.md` goes away.

## Still to do on the content itself

The split moved rules between clusters but deliberately did **not** rewrite their wording. About a
dozen rules in `portable.md` still name Claude-specific tools (`Read`/`Grep`/`Edit`,
`AskUserQuestion`, "plan mode") or this user's own setup (`inv quality.precommit`, "most of this
user's repos") in passing. They generalize with one-line rewrites, but each one is a rule whose
exact wording was tuned for adherence — rewrite them one at a time, not in a sweep, per
`contributing/global-agents-md.md`.
