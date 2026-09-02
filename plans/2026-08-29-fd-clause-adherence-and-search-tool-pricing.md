---
status: idea
updated: 2026-08-29
---

## Context

`~/AGENTS.md`'s "Viewing, searching, or editing files" rule ends with a tool- preference clause:
`rg` over `grep -r`, `fd` over `find`, with plain `grep`/`find` kept legitimate for non-recursive
lookups, `find -exec`/`-delete`, and portability. The user's standing impression, stated 2026-08-29,
is that agents do not respect it.

Measured over **15,171 Bash calls in 415 transcripts** under `~/.claude/projects/`:

| shape                                             | calls | share of that pair |
| ------------------------------------------------- | ----- | ------------------ |
| `rg`                                              | 2356  | —                  |
| `grep -r` / `grep -R`                             | 213   | **8%**             |
| `fd`                                              | 231   | —                  |
| `find`, plain lookup                              | 175   | **43%**            |
| `find` with `-exec`/`-delete`/`-mtime`/… (exempt) | 62    | —                  |

The impression is half right, and the two halves point opposite ways.

**`rg` adherence is good.** 92% of recursive text searches already use it. A rule holding at 92% is
not where effort belongs, and tightening its wording risks the "strengthen language rather than
lengthen explanation" trap in reverse — spending words on the half that works.

**`fd` adherence is bad.** 175 of 406 file-finding calls use `find` for a plain lookup. The samples
are not edge cases:

```
find . -name '*.py' -not -path './.venv/*' -not -path './.git/*' | sort
find . -iname "*plan*" -not -path "./.git/*"
find . -path ./.venv -prune -o -name '*.py' -print | sort
```

Each is `fd -e py` or `fd plan`, with the `.venv`/`.git` exclusions the author typed by hand
supplied free by `fd` being `.gitignore`-aware — which is the exact benefit the rule cites and the
exact work these calls are doing manually.

Two candidate causes, both in this repo's control:

1. **The clause buries `fd`.** It appears in a subordinate position inside a sentence about `rg`,
   after a long paragraph about the `rg -r`/`--replace` trap, and then hands out an exemption list
   ("`find -exec`/`-delete`, or portability") that 175 of 237 `find` calls do not qualify for. An
   exemption list adjacent to a preference reads as permission.
2. **There is no price difference.** `~/.claude/settings.json` allows all four equally —
   `Bash(fd:*)`, `Bash(grep:*)`, `Bash(rg:*)`, `Bash(find:*)`. Nothing in the permission layer
   distinguishes the preferred spelling from the discouraged one, so the rule is the only signal and
   it is competing with a 35 KB instruction file for attention.

## Open questions

[NEEDS CLARIFICATION: does the allowlist lever survive its own bluntness? Dropping `Bash(find:*)`
prices `find` and leaves `fd` free, which is a legitimate use of the permission model rather than a
mechanism firing behind the agent's back — a prompt is in front of the agent, and `~/AGENTS.md`'s
own rule on enforcement mechanisms objects to the covert kind, not to this. But rules match on
literal command prefix, so it cannot spare the 62 genuinely-exempt `-exec`/`-delete` calls: those
would prompt too. Roughly 237 prompts over two days of transcript, of which 62 are unfair. Is that
an acceptable price for retiring a 43% miss rate, or does it just teach sessions to route around
`find` in ways nobody predicted?]

[NEEDS CLARIFICATION: reword the clause, price it, or both — and in which order? Doing both at once
makes the re-measurement uninterpretable, since neither cause can be attributed. Doing the reword
first is cheaper and reversible; doing the pricing first is the stronger signal. There is a real
argument for reword-only, on the grounds that if teaching works, the allowlist change is not needed
at all — which is what `~/AGENTS.md` says to prefer.]

[NEEDS CLARIFICATION: should the exemption list stay at all? Its purpose is to stop the rule being
wrong about `find -exec`, which `fd` genuinely handles differently. But it is doing measurable
damage as a permission signal. Alternative shape: state the preference without exemptions and let
the rule be slightly over-broad, on the grounds that an agent reaching for `find -delete` will not
be stopped by a missing carve-out — it will just pay a prompt.]

## Recommended direction

Rough, and deliberately sequenced so the result is measurable.

1. **Nothing here is actionable without the audit change**, which belongs to `agent-skills`:
   `session-bash-audit`'s `PATTERNS` has one `grep/find` row covering all four commands, so it
   measures "shelled out instead of using Grep/Glob" and is blind to which CLI was used. Filed there
   2026-08-29 as `2026-08-29-bash-audit-cannot-see-grep-vs-rg.md`. The numbers above were taken by
   hand and are the baseline; the rows are what makes the next reading comparable rather than
   another hand-count.
2. **Reword the clause first, alone.** Give `fd` its own sentence rather than a subordinate one, and
   decide the exemption-list question above while doing it. Re-measure after a week of real
   sessions.
3. **Only then consider the allowlist**, if the miss rate has not moved. That order also matches
   `~/AGENTS.md`'s own preference for teaching over mechanism, and it keeps the two changes
   attributable.
4. **Leave `rg` alone.** At 92% it is evidence the rule shape works when the preference is stated
   plainly, which is itself the argument for step 2.

[DEFERRED: the general finding, which outlives this rule — a preference clause with an adjacent
exemption list adheres worse than one without. Two spellings of the same preference in one file, one
with carve-outs and one without, measured 92% and 57%. That is a single observation and not yet a
rule, but it is the kind of thing `contributing/global-agents-md.md` exists to accumulate, and it
would be worth a second instance before anything is written down.]
