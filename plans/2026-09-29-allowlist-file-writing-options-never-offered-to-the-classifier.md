---
status: idea
updated: 2026-09-29
---

# Allowlist file writing options never offered to the classifier

## Context

Found classifying gog on 2026-09-28 (`58a3647`). Six gog commands came back `read_only`, and so
would have rendered as `allow`, although each writes a local file:

- `gmail attachment` always writes one, since `--out` defaults to gog's config directory.
- `--download` on `gmail thread get`, `thread attachments` and `drafts get` writes files.
- `-o`/`--out` on `contacts export` and `gmail settings filters export` writes to any path.

The classifier never saw those options as risky, for two reasons in `tasks/allowlist.py`:

- **They are never offered.** `_candidate_flags` sends a flag for rating only when its name matches
  `_RISKY_FLAG_HINTS | _SAFE_FLAG_HINTS`, and neither set has `out`, `output`, `download` or
  `out-dir`. Its docstring states the exclusion as a deliberate cost saving: `--output`/`--verbose`/
  `--color` "never affect risk tier". That holds for `--output json`, and not for `--output <path>`.
- **A rating would not render anyway.** Per-flag ratings are recorded and shown in `review`, but
  `render` emits only node-level rules plus the hand-written `allow_overrides`/`ask_overrides`
  (`contributing/cli-allowlist.md`, "allow_overrides"). A flag rated `write` on a `read_only` node
  changes no rule.

The gog fix was six hand-written `ask_overrides`, found by grepping every read-only leaf's help text
for `--out|--output|--download|--dir|--save|--write|--file|--dest` options. `--file` turned out to
be a file ID on the Drive commands, so it was dropped. Nothing does that sweep for the next tool,
and the miss is silent: the tool reviews clean, and an agent's `gog gmail attachment …` runs without
a prompt.

## Open questions

[NEEDS CLARIFICATION: **surface it, or render it?** Two shapes:

- **Surface at review.** List every `read_only` leaf whose help has a path-writing option, as its
  own section in `review` beside the `invalid` one, so the reviewer writes overrides knowingly.
  Small, and keeps the "a human writes every carve-out" design.
- **Render automatically.** Turn a flag rated `write`/`dangerous` on a `read_only` node into an ask
  carve-out, the way `ask_overrides` does. That needs the option offered for rating first, and the
  flag's value shape (`--out=x`, `--out x`, `-o x`, `-ox`), which ask patterns already express.
  Larger, and it changes what `render` trusts.]

[NEEDS CLARIFICATION: **how many already-reviewed tools have this today?** At least one. Checked
2026-09-29 in `cli-allowlist/rules/gh.json`: `gh run download`, `gh release download` and
`gh attestation download` are all `read_only`, so they are allowed now, and each writes files into
the working directory. Even a verb that names the write was read as a fetch. The same grep over
every cached tool's `read_only` leaves gives the full count, and `download`/`export`/`save` in a
leaf's own name belongs in that sweep alongside the option names.]

## Recommended direction

Measure first. Run the gog grep over every tool in `cli-allowlist/help-cache/`, restricted to
`read_only` leaves, and read the hits. If there are few, surface them at review and add overrides.
If there are many, rendering becomes worth its cost.
