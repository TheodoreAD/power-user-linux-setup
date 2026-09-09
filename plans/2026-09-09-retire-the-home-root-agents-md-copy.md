---
status: idea
updated: 2026-09-09
---

# Retire `~/AGENTS.md`, the copy no agent reads

**The ask, stated 2026-09-09:** research says `~/AGENTS.md` is not a canonical path — confirm that,
and get rid of it if it has not gone already.

## Confirmed, and this repo already knew

`setup.toml`'s own `[packages.agents-md]` comment records it, written when the file moved on
2026-09-04: the real file sits at `~/.agents/AGENTS.md` because that is the path four verified
agents read on their own (Goose, Warp, Cline, Kimi Code — sourced in `contributing/ai-tooling.md`),
and **"before that the real file was `~/AGENTS.md` and no agent read it directly — it worked only
because every link pointed there."**

The `also_deploy_to` list says the same thing a second way. Every other entry is a vendor path
(`~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, `~/.copilot/copilot-instructions.md`,
`~/.gemini/GEMINI.md`), each deployed only when that agent's config directory already exists — an
absent `~/.codex` means Codex is not installed and creating it would claim otherwise. `~/AGENTS.md`
cannot take that test, because its parent is the home directory and the test would pass vacuously.
It carries `{ always = true }` to opt out, and the comment beside it says why in as many words: **"a
path no vendor owns."**

So the file is a pure backwards-compatibility copy, kept in 2026-09-04 so that references to the old
location would not break. Nothing on this machine reads it.

## What removing it actually costs

[PITFALL: **it is the only `always = true` destination, so deleting the entry retires a config
feature.** `deploy.py` carries the flag end to end for this one path: a field on `MirrorDest`, a
branch in the table-vs-string parser, and two conditionals (`if not dest_entry.always`) that decide
whether a missing parent directory is created or treated as "that agent is not installed". With
`~/AGENTS.md` gone, every one of those is dead code, along with the tests that pin it —
`tests/unit/test_deploy.py`'s "The `~/AGENTS.md` compatibility copy: no vendor owns it, so its
parent is created". Removing the entry and leaving the mechanism is the worse outcome: a documented
config field no declaration uses, which reads as supported.]

**Roughly 100 references across 36 files**, and the split matters because it decides whether this is
mechanical:

- **Almost all of it is prose shorthand** — comments, docstrings and test docstrings citing the
  rules document by name ("per `~/AGENTS.md`'s rule that …", "`~/AGENTS.md` reserves an inverted
  flag shape for …"). Renaming those is find-and-replace, and the gate catches nothing because
  nothing breaks either way.
- **A handful are real path values**, and they are fixtures rather than constants:
  `tests/unit/test_verify.py` uses `dest = "~/AGENTS.md"` as an arbitrary destination,
  `tests/unit/test_home.py` uses it as a registry target. No module hardcodes the path — it is
  declared once, in `setup.toml`.

[NEEDS CLARIFICATION: **nothing deletes an orphaned destination.** `deploy.all` writes declared
paths; dropping a line from `also_deploy_to` stops it being rewritten but leaves the existing
`~/AGENTS.md` on disk, stale from that moment on and still the first thing a session's
tab-completion offers. `inv home.list-claims` would stop claiming it too, so it becomes exactly the
"not PULSE-managed" file that page warns is misleading. Either the removal ships with a one-off
deletion step, or `deploy` grows a notion of a retired destination — worth deciding, because this is
the first destination this repo has ever removed.]

[NEEDS CLARIFICATION: **does the shorthand go too, or only the file?**
`contributing/global-agents-md.md` took a deliberate decision that it "keeps calling it
`~/AGENTS.md` where it means 'the global instructions file', which is what the name has always meant
here." That reads fine while the file exists as a copy. Once it does not, every one of those ~100
mentions names a path that is not there — including inside the deployed rules themselves, where
"durable cross-repo or personal preference → `~/AGENTS.md`" is an instruction to write to it.
Keeping the file and keeping the shorthand are the same decision; removing the file without the
rename is the one combination that is strictly worse than today.]

## Recommended direction

1. **Rename first, delete second.** Sweep the ~100 references to `~/.agents/AGENTS.md`, gate, commit
   — with the repo still deploying the copy, so nothing is broken at any point in the sequence.
2. **Then drop the `also_deploy_to` entry**, and in the same commit remove the `always` flag,
   `MirrorDest.always`, both conditionals and their tests, since the flag has no other user.
3. **Then delete the file**, by whichever answer the orphan question above takes.
4. **Leave the plans/ mentions alone.** They are dated records of what was true when written, and
   rewriting history's vocabulary is how a plan stops being evidence.
