---
status: in-progress
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

[DECISION: **`deploy` grew the notion, rather than the removal shipping a one-off `rm`.** A manual
deletion is a change nobody can re-run, which is the thing this repo exists to not have.
`inv
deploy.prune` deletes home files the manifest records but `setup.toml` no longer declares, and
only while the file still matches the digest recorded when PULSE wrote it — the same rule `deploy()`
follows before overwriting, so the command removes its own output and nothing else. It reuses the
manifest rather than adding config, which is what kept it small.]

[PITFALL: **the first dry run found two ways this would have destroyed something.** The manifest
still records the `~/.agents/skills/<name>` directories the copier wrote before 2026-09-07 — they
have been undeclared ever since, so every one reached prune, which called `read_bytes()` on a
directory. Crashing was the _good_ outcome: the `skills` CLI owns those now, so a version that had
handled directories would have deleted live installed skills. And `declared_paths()` has to union
the registry with the mirrors, because `lookup()` answers False for `~/.claude/CLAUDE.md` even while
`setup.toml` declares it — deciding ownership from the registry alone marks every agent's
instruction file an orphan. Both are pinned by tests.]

[NEEDS CLARIFICATION: **a second orphan, and it is not this plan's to delete.**
`~/.config/JetBrains/PyCharm2026.1/options/editor-font.xml` is recorded as deployed by `pycharm` and
is no longer declared. Its digest still matches, so prune would remove it — and removing it resets
an editor font that is currently set. Deleting someone's IDE config while retiring an unrelated path
is not tidying. Left alone deliberately; `inv deploy.prune --path <that file>` is the whole fix if
it is wanted.]

[DECISION: **the shorthand went too, in its own commit before anything was removed.** 95 mentions
across 34 files now name `~/.agents/AGENTS.md`, with `setup.toml` reverted from the sweep and edited
by hand — it is the one file that discusses both paths deliberately, and the blind pass had
rewritten the `also_deploy_to` entry to equal `dest`, which would have had deploy copy the file over
itself. Four other replacements were reverted in place: three sentences came out saying a file moved
from itself to itself, and one asserted that the canonical path's parent is the home directory,
which is false and was the premise the `always` flag rested on. `plans/` was excluded throughout.]

What forced that decision, recorded because it is the reusable half:
`contributing/global-agents-md.md` had deliberately chosen to keep calling it `~/AGENTS.md` "where
it means 'the global instructions file'". That reads fine while the file exists as a copy and
becomes a dangling instruction the moment it does not — the deployed rules themselves said "durable
cross-repo or personal preference → `~/AGENTS.md`", which is an instruction to write to it. Keeping
the file and keeping the shorthand were the same decision, and removing the file alone was the one
combination strictly worse than doing nothing.

## What landed, 2026-09-09

The sequence held: nothing was broken at any commit, because the rename went first while the copy
was still deployed.

1. **Rename** — 95 mentions across 34 files, `plans/` excluded, `setup.toml` by hand.
2. **Undeclare** — the `also_deploy_to` entry, and with it the `always` flag, `MirrorDest`, the
   table form of the field, and the `list[str | dict[...]]` type. `mirror_dests` returns
   `list[Path]` now and `deploy`, `tools`, `verify` and `home` all got simpler. The runtime
   `isinstance` guard stayed, suppressed precisely: TOML is untyped at run time and an older
   `setup.toml` may still carry a table.
3. **Prune** — `inv deploy.prune`, then `--path ~/AGENTS.md --yes` after a dry run. The file is
   gone; `~/.agents/AGENTS.md`, `~/.claude/CLAUDE.md` and `~/.copilot/copilot-instructions.md` are
   byte-identical and `inv verify.all` passes on all three.

One behaviour changed for a real reason rather than to follow the rename: the dry-run mirror plan
used to say "would write a copy" for the compat path regardless of its parent, and now correctly
says "would skip" when the parent is absent. Its test fixture moved to a vendor directory, which is
what this repo actually declares.

`plans/` was left alone throughout — those are dated records of what was true when written, and
rewriting their vocabulary is how a plan stops being evidence.
