---
status: idea
updated: 2026-09-03
---

# Deployed artifacts should say they are generated

## Context

Stated by the user 2026-09-03, as a general boundary rather than a rule about one file:

> we do not touch live, deployed stuff directly. only source code. we build pipelines to redeploy
> and reconfigure via scripts code in general, deterministic, not via llm.

and the reason it matters here:

> regenerating from source is a big feature of pulse, and creating complex diffs after several
> actors modify a file is not fun.

**PULSE already has the enforcement half and is missing the announcement half.** `inv deploy.status`
reports drift, `inv deploy.all` converges, and the deploy manifest refuses to overwrite content it
cannot prove it wrote. What none of that does is tell a reader who has just opened a deployed file
that editing it is pointless.

## The gap, measured 2026-09-03

First six lines of every file this repo deploys under `~`, searched for any of `do not edit`,
`generated`, `managed by`, `PULSE`:

| deployed path                     | marker                                  |
| --------------------------------- | --------------------------------------- |
| `~/AGENTS.md`                     | yes — the assembly preamble says it     |
| `~/.p10k.zsh`                     | yes, but it is **p10k's own** header    |
| `~/.config/act/actrc`             | **none**                                |
| `~/.config/wezterm/wezterm.lua`   | **none**                                |
| `~/.local/bin/askpass-zenity`     | **none**                                |
| `~/.config/terminator/config`     | **none**                                |
| `~/.local/bin/research-update`    | **none**                                |
| `~/.claude/statusline-command.sh` | **none**                                |
| `~/.local/bin/pulse-proxy-start`  | incidental — the word appears in a path |

So exactly one deployed file states its own provenance, and it is the one whose provenance is
already the most discussed. Anyone opening `wezterm.lua` — a person or an agent — has nothing
telling them the edit will be reverted on the next deploy. `deploy.status` would catch it, whenever
somebody next runs it.

[PITFALL: **the drift machinery makes this feel solved when it is not.** Because a hand-edit is
detected and asked about rather than silently clobbered, the failure looks handled. What is actually
handled is the _overwrite_; the wasted edit is not, and neither is the reader's belief that the file
is theirs to change. Detection happens on PULSE's schedule and the mistake happens on the reader's.]

## Prior art — three traditions, the same two moves

Researched 2026-09-03. Each of these **marks the artifact** and **converges via a tool**, and all
three treat the marking as load-bearing rather than decorative:

- **Go**: `^// Code generated .* DO NOT EDIT\.$`, which "must appear before the first non-comment,
  non-blank text in the file". A fixed, machine-checkable form that tooling recognises — the part
  worth copying is that it is a _regex_, not a house style.
- **chezmoi**: an explicit source-state / target-state split with `diff` and `apply`. This is
  PULSE's `deploy.status` / `deploy.all` arrived at independently, which is reassurance that the
  model is right rather than a reason to change it.
- **Ansible / Puppet**: the `# managed by` header on every managed file, for exactly this reader.

## Design

1. **`deploy.py` emits a marker** into every deployable whose format supports a comment, in Go's
   shape — a fixed regex, first non-blank line, naming the source path and the task that rewrites
   it. One line.
2. **A test asserts every declared source carries one, or is listed as exempt.** The exemption list
   is the design's honest part: JSON has no comments, and some configs reject unknown leading lines.
   A test that cannot express the exceptions is a test nobody can ship.
3. **`~/AGENTS.md` gets one clause**, extending "Regenerating a file from a canonical source" rather
   than taking a heading — deployment is that rule one step further, and the rule count stays at 39.

[DECISION: **the marker is the primary mechanism and the instruction is the backstop, not the other
way round.** An agent reads the file it is about to edit; that is a more reliable trigger than an
always-loaded sentence it has to recall at the right moment. This is the same reasoning the leanness
pass reached from the other side — the always-loaded file is expensive and its rules are missed, so
where a mechanism can carry the rule, it should. Stated here because the instinct on being handed a
new convention is to write it into `~/AGENTS.md` first and build the mechanism later, which gets the
reliability backwards.]

## Open questions

[NEEDS CLARIFICATION: **does the marker live in the source file or get injected at deploy time?**
This is the design's real tension and it should be settled before any code. Injecting means the
deployed content no longer equals the source content, and `deploy.py`'s drift detection compares
exactly those two — so every comparison would need to strip the marker, and a stale marker becomes a
false drift. Putting it in the source means the _source_ file reads `DO NOT EDIT`, which is wrong on
its face: the source is precisely where editing is correct. A third option is a marker whose text
distinguishes them ("generated into `<dest>` from this file"), which reads correctly in both places
and keeps the byte comparison honest.]

[NEEDS CLARIFICATION: which deployables genuinely cannot take a comment? `actrc`, the shell scripts
and `wezterm.lua` all can. The exemption list should be derived by trying, not assumed — and the
answer decides whether the test is "all of them" with a short deny-list or something weaker.]

[NEEDS CLARIFICATION: how does this interact with the `PULSE::<dir>/<stem>` markers already inside
`~/AGENTS.md`? Those are provenance for _sections_, explicitly documented as "not partial
ownership". A whole-file marker is a different claim and the two should not be confused by a reader
or by a future regex. Possibly the assembled file's existing preamble already satisfies requirement
1 and needs nothing.]

[NEEDS CLARIFICATION: does this extend to the other nine ways this repo writes into `~`? The
registry is `inv home.list-claims` — `util.ensure_block` marker regions, merges into co-owned JSON,
regex surgery on one key of an app-owned file, `gsettings`/`dconf`, symlinks. A block marker already
announces itself; a `gsettings` key cannot carry a comment at all. The rule is clean for whole-file
deploys and needs a stated scope for the rest.]

## Recommended direction

Settle the source-versus-injected question first — everything else is downstream of it, and it is
the one choice that is expensive to reverse once files carry markers.

Then do the three steps in order: emit, test, clause. The clause last, deliberately: it should
describe a mechanism that already works rather than promise one, and if the mechanism turns out to
cover the case fully the clause may not be needed at all.

Related, and worth reading together: `plans/2026-08-29-dotfiles-repo-config-lifecycle.md` owns the
question of which config files PULSE should manage at all, and this plan assumes its answer rather
than reopening it.
