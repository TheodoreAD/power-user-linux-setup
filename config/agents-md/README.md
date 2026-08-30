# `~/AGENTS.md` fragments

The assembled `~/AGENTS.md` is built from the fragments in this directory, in `order`. Each one owns
a single subject, and contributes exactly the `##` cluster named after it:

| order | fragment             | cluster                        |
| ----- | -------------------- | ------------------------------ |
| 5     | `preamble.md`        | (title, assembly note, legend) |
| 10    | `agent-knowledge.md` | Agent instructions & knowledge |
| 20    | `git.md`             | Git & commits                  |
| 30    | `bash.md`            | Bash & tool use                |
| 40    | `research.md`        | Research & design              |
| 50    | `verification.md`    | Verification                   |
| 60    | `collaboration.md`   | Collaboration & output         |

Each fragment contributes whole `##` sections; the assembler never merges at the rule level, so no
cluster is split across two fragments. With one cluster per fragment that holds by construction.

Design, rationale, and the rule-by-rule triage behind the split:
`plans/2026-08-26-agent-artifact-authoring-decoupling.md`, "Design — the assembled `~/AGENTS.md`".
Each rule's evidence and the admission criteria for a new one stay in
`contributing/global-agents-md.md`.

## Which fragment a rule belongs in

**What the rule is about** — the subject, not what it depends on. A rule about staging a commit goes
in `git.md` whether or not it names an `inv` task; a rule about choosing a Bash tool goes in
`bash.md` whether or not it names Claude Code's.

This is deliberate. Roughly ten of the rules are a portable principle wearing a local instantiation
("About to commit" is universal and names `inv quality.precommit`), and a rule may not live half in
one fragment and half in another — so filing by dependency would force each of those to a side and
misdescribe it. Dependency is a label instead, which a rule can carry without moving.

## Labels: what a rule assumes

A rule heading may end with a bracketed label. Two shapes, and no others:

- `[Claude Code]` — the rule describes one harness and does not transfer to another. These are
  deliberate and stay; the expectation is that a second harness gets its own rules alongside, not
  that these get generalised into vagueness.
- `[needs <thing>]` — the rule holds because PULSE installed that thing, and stops being true if it
  is removed. Where `<thing>` is a bare name it must be a `[packages.*]` entry in `setup.toml`, so
  the claim stays checkable; it may also name a file or a mechanism, as the sudo and ssh rules do.

No label means the rule assumes neither and holds anywhere. `tests/unit/test_agents_md.py` enforces
the vocabulary and that a package-shaped label names a package that exists.

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
