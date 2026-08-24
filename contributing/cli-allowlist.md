# CLI permission allowlist — design notes

Companion to [`docs/cli-allowlist.md`](../docs/cli-allowlist.md) (the published "what it is / how to
run it" page). This is the durable explanation of _why_ `cli-allowlist/` and `tasks/allowlist.py`
are built the way they are, including every gotcha the first implementation pass hit and how testing
(not code review) caught each one — read this before re-deriving the architecture from scratch or
"fixing" something that was already a deliberate tradeoff.

### `tools.toml` — the registry

`cli-allowlist/tools.toml` lists every tool `extract` probes, one `[tool]` section per binary. Most
CLIs are `<tool> <subcommand> --help` cobra/click/argparse programs and need no special handling,
but the registry has escape hatches for the ones that aren't, discovered by testing, not guessed:

- **`help_flag`** — override the default `--help`. `git` uses `-h` instead: see below.
- **`help_style = "prefix"`** — some tools put the flag _before_ the subcommand (`go help list`, not
  `go list --help` — the latter is just a one-line stub pointing at the former). Only `go` needs
  this so far.
- **`no_subcommands`** — flat tools (coreutils, `jq`, `curl`, `rsync`, `bash`, `zsh`...) where the
  risk lives in flags, not a subcommand tree. Classified as one unit.
- **`skip_interactive`** — TUI-only tools (`k9s`, `vim`) with no non-interactive surface to classify
  at all.
- **`shell_prefix`** — for tools that aren't binaries. `nvm` only exists as a shell function after
  sourcing `nvm.sh`; `which nvm` fails and a direct exec fails. Extraction instead runs
  `bash -c "<shell_prefix> && nvm <args>"`.
- **`version_flag`** — several tools don't use `--version`: `kubectl` needs `version --client`,
  `helm` needs `version --short`, `go` needs `version`, `tmux` needs `-V`, `ssh`/`unzip` need
  `-V`/`-v`. Guessed wrong for all of these on the first pass; caught by actually running each one
  and reading the output, not by assuming GNU-style conventions apply everywhere.

Coverage isn't limited to what `setup.toml` installs — it also includes the base system (coreutils,
util-linux, diffutils, procps, tar/gzip/bzip2/xz), audited via `dpkg -L coreutils` etc. rather than
from memory, since an agent reaches for `cat`/`cp`/`rm`/`dd` just as often as anything PULSE
explicitly installs.

Three more fields exist specifically for recursion:

- **`max_depth`** — how many levels deep to walk the subcommand tree (default `1`, today's original
  single-level behavior). `2` also probes each direct subcommand's own `--help` for a further
  command listing (`git remote add`, `docker network create`, `gh secret set`). Opt-in per tool —
  most tools' real risk lives at depth 1 and recursing needlessly just costs LLM calls for no new
  signal. Currently on for `git`, `gh`, `glab`, `kubectl`, `helm`, `docker`, `terraform`, `go`,
  `npm` — the tools where a bare subcommand name genuinely blends distinct risk levels
  (`docker network` alone can't tell you `ls` is read-only and `rm` is dangerous).
- **`max_nodes`** — total node budget for the whole tree, breadth-first (default `60`). Only matters
  once `max_depth > 1`. `docker` and `gh` needed `200` — their real trees measured ~160–175 nodes;
  `150` silently truncated the least-common branches (breadth-first truncation drops whatever hasn't
  been reached yet, not a random subset, so it's at least legible in `status`'s `truncated` flag,
  not a silent gap).
- **`cloud_cli`** — marks a tool whose real command surface is structurally too large to
  auto-discover (`gcloud`, `aws`: `<tool> <service> <resource> <verb>`, thousands of leaf commands,
  3 levels deep by construction). These intentionally stay at `max_depth = 1` with a hand-picked
  top-level `subcommands` list. This is a documented non-goal, not a gap `max_depth` will eventually
  close — recursing a provider CLI's full surface isn't worth the node/LLM-call budget for commands
  that will almost never be run.

### Recursive tree extraction — `_build_tree`, and what broke on the first pass

Depth isn't just "run `_discover_subcommands` again on the child's help text" — every one of the
following was found by actually running it against real tools, not by inspecting one tool's `--help`
and assuming the shape generalizes:

1. **Nested help text often doesn't look like the top level's.** `git`'s top-level `-h` has a
   `Commands:`-style heading; `git remote -h` / `git stash -h` / etc. render as docopt-style usage
   synopses instead (`usage: git remote add ...`, `or: git remote [-v] show ...`) with no heading at
   all. `_discover_subcommands` tries the heading-based regex first and falls back to a synopsis
   parser (`_discover_from_synopsis`) only when that finds nothing _and_ a tool+path context is
   available (i.e. only at nested levels, never at the top, where the heading style reliably
   applies). The fallback walks each `usage:`/`or:` line token by token, skips (possibly-nested)
   `[...]` bracket groups, and takes the next token _only if it's a bare lowercase identifier_ — a
   positional-arg placeholder right after the known path (`<pathspec>`, `<commit>...<commit>`, or
   docker's bare-ALL-CAPS convention `CONTAINER`) means this command takes arguments directly rather
   than nesting further, and is deliberately left unmatched rather than sanitized into a fake
   subcommand. It fails closed: a synopsis it can't parse confidently yields no verb from that line,
   not a wrong one. (An earlier version stripped punctuation before validating and fabricated nodes
   like `add pathspec`, `branch branch-name`, `diff commitcommit`, and merged git bisect's
   `(good|bad)` alternation into `bisect goodbad` — caught by inspecting the actual discovered tree,
   not by trusting the regex.)
2. **A cobra-style tool can format nested listings differently from its own top level.** `gh`'s
   nested help suffixes each name with a colon (`create:        Create a pull request`) where the
   top-level listing has no colon — `_SUBCOMMAND_LINE`'s trailing `:?` exists specifically for this;
   without it, `gh`'s entire depth-2 tree silently discovered zero children.
3. **A subcommand that no longer exists can silently echo its parent's help instead of erroring.**
   Confirmed at two different tree levels: `docker trust --help` (root-level, deprecated in this
   docker build, exits `0`, dumps `docker --help`) — recursing into that would treat the _entire_
   command surface as `trust`'s children and blow the node budget on a duplicate of the whole tree
   (this is what first exposed the bug: `docker`'s `truncated` node count didn't match reality, and
   `trust` had 40 "children" that were really just the rest of docker). `_build_tree` detects this
   by content hash — a node's help text byte-identical to its _immediate parent's_ (not just the
   tool's root; see point 4) — and suppresses further recursion into it.

   Whether duplicate content also means "not a real command" turned out to hinge on **how many
   siblings were discovered alongside it, not on where the name came from** — the first version of
   this check used "explicit `subcommands =` list vs auto-discovered" as the signal, which is wrong:
   `git submodule <verb> -h` returns the exact same combined usage block for 9 of its 10
   auto-discovered children (only `absorbgitdirs` differs), and all 9 are real, safety-distinct
   commands (`submodule deinit` is very different from `submodule sync`) that just happen to share
   undifferentiated help text — the same situation as `nvm`'s shell function, one level deeper. A
   _lone_ duplicate — the only child discovered for its parent at all — has nothing corroborating
   it; a duplicate inside a multi-member group discovered the same way as its non-duplicating
   siblings does. So: a node whose content matches its parent **and** was the only child found in
   its discovery batch gets marked `likely_invalid` at extract time and never even reaches the LLM
   (see point 4); everything else with duplicate content — `docker trust`, `nvm`'s whole list,
   `git submodule`'s 9 — keeps being classified normally, worst case producing a rule that never
   matches anything real (`docker trust`) rather than losing real coverage (`nvm`, `git submodule`).
4. **Some extraction weirdness doesn't show up as duplicate content at all**, and no deterministic
   heuristic was going to anticipate every shape it can take — so `classify`'s LLM call carries a
   4th classification tier, `invalid`, specifically for "this path isn't a genuine, distinct
   command" (rubric excerpt: matched a line from an example/sample-output table, a config snippet,
   or other incidental text; content doesn't describe what this specific path does). This is a
   deliberate second layer on top of point 3's deterministic check, not a duplicate of it — proven
   live on `helm`: the deterministic check caught `list maudlin-arachnid` (a sample-output table row
   — `maudlin-arachnid    Mon May 9 16:07:08 2016    alpine-0.1.0` — matched by the same
   heading-shaped regex that finds real subcommands, the lone-child case from point 3), while the
   LLM independently caught `diff` (a real, 18-member root-level entry — not a lone duplicate, so
   point 3's check doesn't touch it — but `helm diff` is a third-party plugin not installed here;
   `helm diff --help` silently dumps generic top-level Helm help, content that "looks like" a
   plausible response, not a duplicate signal, but doesn't actually describe a `diff` subcommand).
   Neither layer alone would have caught both. A third variety turned up later, at full-registry
   scale: `gh extension exec` and `direnv dump` both captured a literal CLI error message
   (`extension "--help" not found`) as their node's help text — not a duplicate of anything, not
   generic fallback content, just an error string — and the LLM correctly flagged both `invalid` on
   sight without any rubric change, which is really the point of having a judgment-based second
   layer at all: each new shape of extraction weirdness found so far has been a _different_ one, not
   a repeat, and a deterministic check can only ever cover the ones already seen. `invalid`-tier
   nodes are excluded from `render`/`apply` output automatically (the pattern-building code already
   only branches on `read_only`/`write`/`dangerous`) and shown in their own section in `review`,
   separate from the normal per-node dump, so they read as "not a command, ignore it" rather than a
   4th risk tier.

### Per-flag ratings — same call, no extra invocations

Flags don't get their own `--help`; they're already sitting in the help text `extract` captured for
a node. `_parse_flags` pulls `-f, --force  <description>`-style lines out of that text (best-effort,
not load-bearing the way subcommand discovery is — a missed flag is one fewer candidate offered to
the classifier, not a broken tree). Rating literally every flag on every node would be mostly noise
(`--verbose`, `--output`, `--color` never affect risk) for real token/cost overhead, so
`_candidate_flags` pre-filters by name against two heuristic token sets — one for flags that
plausibly _escalate_ risk (`force`, `recursive`, `all`, `yes`, `hard`, `global`, `cascade`, ...,
extending the same `_DANGEROUS_VERBS` set already used for the subcommand-name backstop) and one for
flags that plausibly _de-escalate_ it (`dry-run`, `check`, `plan-only`, `preview`, ...). Only the
matches get sent to the LLM as "candidate flags — rate ONLY these" for that node, in the same call
as the subcommand's own classification (no extra API calls).

Flags are rated on the same three-tier scale as subcommands, but as an **absolute resulting tier**
for command+flag together, not a delta from the base — `git push` is `write`, `git push --force` is
`dangerous`; `git clean` is `dangerous`, `git clean --dry-run` is `read_only`. This was a deliberate
framing choice: an absolute tier is directly comparable to the base classification and one the model
can reason about consistently, versus an abstract "escalates/mitigates" concept that would need its
own interpretation layer downstream. A flag missing from a node's `flags` map simply wasn't offered
as a candidate — treat it as "no signal that it changes the base tier," not "rated and found
neutral."

Flags get the same read_only-name-vs-dangerous-token backstop as subcommands
(`_looks_dangerous_flag`), and it caught a real false positive of its own: `--dry-run` tokenizes to
`{"dry", "run"}`, and `"run"` is in `_DANGEROUS_VERBS` (added for `nvm run` as a _subcommand_, which
does execute arbitrary code) — so the single most common safety-signaling flag in the entire
candidate set was getting downgraded to `needs_review` on sight, confirmed live on git's
`notes
prune --dry-run` / `remote prune --dry-run` (both correctly rated `read_only` by the model,
then immediately flipped). The fix isn't "remove `run` from the dangerous set" (it's a correct catch
for the subcommand case) — it's a whole-name check first: if a flag's full name (not its individual
tokens) matches something in the _safe_-flag hint set, that wins the tiebreak before tokenizing ever
loses the "dry-" context (`_flag_matches_hints`, shared by both the candidate-selection filter and
the backstop). A pure token-set comparison can't make this distinction on its own — `"dry-run"` as a
whole phrase and `"run"` as an isolated token need to be checked as genuinely different things.

**Important limitation, not a TODO**: this data doesn't drive `render`/`apply` yet, and structurally
can't with the current mechanism. Claude's Bash permission rules are literal-prefix globs
(`Bash(git push:*)`), and flags can appear in any order/position in a real invocation — there's no
clean prefix-based way to express "allow this subcommand except with `--force`". `write` and
`dangerous` still both render as `ask` either way (see below), so today a flag escalating from write
to dangerous doesn't even change the rendered rule. Per-flag data is analysis/review value right now
— exactly what motivated building it — and a foundation for a future consumer (e.g. a PreToolUse
hook, which unlike a prefix glob _can_ parse flags order-independently — deliberately not built yet,
see the `render`/`apply` section below) rather than something `render` acts on today.

### Deterministic extraction has more sharp edges than it looks like

Two real, empirically-confirmed problems, not hypothetical ones:

1. **A tool's `--help` can depend on a separately-installed package.** `git status --help` renders
   through the system `man` command, which needs the `git-man` package. It happened to be installed
   on the machine this was built on, which made the bug invisible until tested with a stripped
   environment. Fixed by using `git -h` instead — a self-contained synopsis with no package
   dependency. `inv allowlist.check-man-deps` (`tasks/allowlist.py` — deliberately not part of the
   extract/classify/review/apply pipeline itself, an occasional maintenance diagnostic instead) runs
   every registered tool's help invocation under `strace -f -e trace=execve` and checks for a child
   `exec` of `man`, `groff`, or `troff` — the only reliable way to tell "renders like a man page"
   (`gcloud`, which mimics man's NAME/SYNOPSIS/DESCRIPTION layout with its own self-contained
   renderer, nothing external involved) apart from "actually shells out to a formatter" (`git`
   depends on `man` itself; `aws` — added when the cloud-CLI recursion boundary was drawn — depends
   on `groff`/`troff`/`grotty` for `aws help`'s formatted output, same risk class, different
   package, caught the same way). Any tool in this category only extracts correctly because that
   package happens to be installed on this machine; there's no portable fix for `aws` the way `-h`
   was for `git` (no flag skips the groff pipeline), so it's accepted and documented in `tools.toml`
   rather than worked around. Re-run the check (`inv allowlist.check-man-deps`) after registering a
   new tool.
2. **Extraction must be portable, not just correct on the machine that wrote it.** `PAGER`,
   `MANPAGER`, `GIT_PAGER`, and `BROWSER` are neutralized (`cat`/`true`) for every extraction call —
   the actual defense here isn't "nothing tries to page or open a browser," it's that the captured
   text can't depend on this machine's interactive shell configuration.

### Classification via headless Claude

`classify` shells out to the `claude` CLI already installed on this machine (`-p`/`--print`,
`--model haiku`, `--output-format json`, `--json-schema` for enforced structure) rather than
standing up separate Anthropic API billing. This was the answer to "how do you automate the LLM
judgment call without new infrastructure": reuse what's already paid for and authenticated.

Things that weren't obvious until tested:

- **`--bare` cannot be used.** It restricts auth to `ANTHROPIC_API_KEY`/`apiKeyHelper` only — "OAuth
  and keychain are never read" per its own `--help` text — and this account is logged in via OAuth,
  so `--bare` calls fail outright with "Not logged in". Isolation from this repo's own `.claude/`
  instead rests on running with `cwd` pointed at a scratch directory outside the repo entirely, plus
  `--disallowedTools` covering every file/exec/subagent-spawning tool as a backstop.
- **`--json-schema` output lands in `structured_output` at the top level of the response envelope**,
  not nested inside `result` as text (that field is just the model's natural-language summary).
- **`claude -p` waits ~3s for stdin and prints a warning that breaks JSON parsing** unless stdin is
  explicitly closed (`stdin=subprocess.DEVNULL`).
- **A single flat "classify this whole tool as one thing" prompt is genuinely ambiguous.** The first
  attempt used a heading literally named `*` for `no_subcommands` tools; the model read that as
  "find distinct things to classify" and broke `nuitka --help` into per-flag verdicts (`--mode`,
  `--run`, ...) instead of one verdict for the tool. Fixed by asking explicitly for a single entry
  under a fixed key (`_default_`), with a conservative fallback (take the most cautious of whatever
  came back) if a future tool's help text confuses it the same way again.
- **Cost is dominated by fixed per-call overhead, not prompt size — up to a point.** A single
  trivial 2-item classification call cost ~$0.026 and ~12s at Haiku; a real tool with 15-25
  subcommands stayed in roughly the same ballpark. That stopped holding once per-flag ratings were
  added and trees got deeper: a 20-node batch (subcommand + candidate-flag ratings) measured
  ~$0.08 and ~92s — close enough to both `--max-budget-usd` and the process timeout that a tool with
  50+ new nodes in one call (routine once `max_depth > 1` is on) would blow past one or the other.
  `classify` batches `_CLASSIFY_CHUNK_SIZE` (15) nodes per call instead of the whole tool at once —
  still far fewer calls than one-per-node, just bounded per call. Classifying the ~70 tools not
  already covered by a community-sourced seed cost under $2 total the first time this pipeline
  existed; enabling recursion on 9 tools added a comparable one-time cost for their new nodes.
  Steady-state re-runs are close to free either way, because of the (now per-node) content-hash
  gate.
- **A deterministic safety backstop runs after every LLM call, at no extra cost**: any subcommand
  the model marks `read_only` gets re-checked against a small set of dangerous-sounding verb tokens
  in the subcommand _name itself_ (`delete`, `destroy`, `rm`, `force`, `run`, `exec`, ...) — a match
  downgrades it to `needs_review` regardless of what the model said. `run`/`exec` were added to this
  list after the model classified `nvm run`/`nvm exec` as `read_only`, which is wrong — they execute
  arbitrary commands. This does cause real false positives, though — the check has no understanding
  of context, it just matches words: `gh run` is a noun (GitHub Actions run history), not a verb,
  and `--all` on a listing command broadens what's _shown_, not what's destroyed. Left unresolved,
  `needs_review` entries stay excluded from both `allow` and `ask` forever (see "Review", below) —
  `inv allowlist.reconfirm` is the second pass that resolves them; see its own section further down.

Six tools (`git`\*, `gh`, `kubectl`, `helm`, `docker`, `terraform`, `gcloud`) were originally seeded
from a cloned community allowlist repo rather than classified fresh — `source: "community"` on that
node — on the theory that a well-covered, actively-maintained community list is a fine starting
point for stable, widely-used tools while this pipeline's own rubric was still new. (\* `git` was
reclassified via LLM early on anyway, after switching its `help_flag` to `-h` changed the extracted
text enough to invalidate the seed's hash.)

`source` lives on each _node_, not on the tool as a whole — originally because of recursion (five of
the six also gained `max_depth = 2`, so their depth-1 nodes stayed `source: "community"` while their
new depth-2 nodes, never covered by the seed at all, came back `source: "llm"`), but it also turned
out to matter for a second reason: **community data is now deliberately self-liquidating**.
`classify` sweeps every node with `source: "community"` back into reclassification on every run,
content hash notwithstanding — once the pipeline had matured (its own rubric, per-flag ratings, the
invalid-node backstop, chunked prompts), there was no remaining reason to trust an external seed
over a fresh judgment from the exact same model/rubric everything else here is classified with. A
few nodes get upgraded to real LLM output on each `classify` run at no cost to the nodes that are
already fresh, until nothing `community`-sourced is left. As of this writing, all six tools have
been fully swept — `source: "community"` shouldn't appear anywhere in `cli-allowlist/rules/`
anymore, though the sweep logic stays in place in case a future community-seed addition happens.

### Rules storage — one file per tool, not one monolithic `rules.json`

`cli-allowlist/rules/<tool>.json`, one file per tool (mirroring `help-cache/<tool>.json`), each
holding a path-keyed `nodes` map — replaced a single `rules.json` once trees got deep enough that
one tool's reclassification would otherwise rewrite (and diff-noise) every other tool's data in the
same file on every run. Each node carries its own `content_hash` (not a single hash for the whole
tool): `classify` diffs _per node_, so a new `docker network` child doesn't force reclassifying
`docker`'s other 160 unrelated nodes, and a routine re-run only ever pays for what actually changed.

### `reconfirm` — resolving `needs_review` with the specific concern in hand

The verb-token backstop (above) is deliberately dumb — a cheap, deterministic string match with no
context — which means it both catches real risks the first classify pass might have missed _and_
flags real false positives (`gh run`, `--all` on a listing command). Leaving those stuck at
`needs_review` forever (excluded from both `allow` and `ask`, so they'd always fall back to whatever
Claude's own default is) throws away commands that a closer look would clear.

`inv allowlist.reconfirm` is a second, targeted LLM pass over exactly the current `needs_review` set
(subcommands and flags both) — different from a normal `classify` re-run in two ways: it tells the
model precisely which word triggered suspicion (`_dangerous_path_tokens`/`_dangerous_flag_tokens`
report the matched token, not just a bool, specifically so this prompt can cite it), and it trusts
whatever the model comes back with directly — a reconfirmed `read_only` does **not** get run back
through the same backstop that flagged it in the first place, which would just recreate the original
problem. The rubric leans on the model instead: it's told this verdict is trusted unchecked, so if
the help text doesn't clearly settle whether the flagged word applies in its dangerous sense here,
it should answer `write`/`dangerous` rather than guess `read_only` — wrong in the cautious direction
just means one more prompt, wrong in the other direction is the actual failure mode.

Resolved nodes are stored with `source: "llm-reconfirmed"` (distinct from plain `"llm"`, so it's
visible in review/audit that this one took a second pass) and the tool is marked unreviewed again,
same as any other classification change — a human still signs off on the resolved verdict before it
renders into a rule. Idempotent by construction and needs no `--force`: once an item resolves to a
real classification it's no longer `needs_review`, so nothing is left for the next run to touch.

Verified it isn't just rubber-stamping everything `read_only`: `nvm exec`/`nvm run` — the exact case
the backstop's `run`/`exec` tokens were added to catch — correctly came back `write` with a
rationale distinguishing "the safe sense of execute-code" from "the shell builtin", not blindly
cleared because they were being reconfirmed at all.

### Three real bugs found running this at scale (community resweep + reconfirm)

Making `classify` always resweep `source: "community"` nodes (below) meant, for the first time,
sending every depth-1 node of five well-known, actively-maintained CLIs (`docker`, `gh`, `kubectl`,
`helm`, `terraform`) through this pipeline in one push. That surfaced three real bugs that smaller,
one-tool-at-a-time runs hadn't hit:

1. **A failed _or merely incomplete_ chunk silently dropped nodes from the ruleset, not just left
   them stale.** Community nodes are always routed into `to_classify` (never `carried`, by design —
   see below), so when a key never showed up in a chunk's result, it wasn't in `verdict` _or_
   `carried`, and the old `if result is None: continue` in the node-building loop meant it simply
   never made it into `new_nodes`. First confirmed losing 21 root-level `gh` nodes (`gh pr`,
   `gh
   issue`, `gh secret`, ...) from `rules/gh.json` entirely after one explicitly failed chunk
   — worse than the state before the resweep, which at least had the community data. But checking
   every recursive tool's `help-cache` keys against its `rules` keys (not just the one that printed
   a "chunk failed" message) turned up the same gap, silently, with **no error printed at all**, on
   `docker` (7 nodes), `gcloud` (4), `git` (2), and `aws` (1) — a chunk can report success while
   still covering only some of what it was asked for, which is exactly what point 2's scope-creep
   bug does when it burns output budget on unrequested items before finishing the requested ones. A
   clean-looking `classify` run was not sufficient evidence that nothing was lost. Fixed: on a
   missing result, fall back to whatever was in `existing_nodes` for that key (if anything) instead
   of dropping it — it's still not in `carried`, so it stays eligible for `to_classify` again next
   run, but nothing is lost in the meantime.
2. **The model doesn't reliably stay in scope for a tool it has extensive prior knowledge of.**
   Asked to classify 20 specific `gh` nodes, Haiku used its own training knowledge of the GitHub CLI
   and classified 134 — the entire tool's surface, most of it never requested. Confirmed by
   reproducing the exact call directly: 131s runtime and $0.12 versus 56s/$0.06 for the same 20
   nodes once fixed. This explains the intermittent chunk failures during the resweep: generating
   ~6x the necessary output routinely pushed calls right up against `_CLASSIFY_TIMEOUT`. Not a
   token-budget-only problem, since `--max-budget-usd` didn't reliably catch it either — fixed by
   making the rubric explicit that only the listed paths should be classified and that recognizing a
   well-known tool's other subcommands isn't an invitation to include them.
3. **A chunk can "succeed" while still returning nothing usable, via a subtle key mismatch.** After
   fix #2, `reconfirm` calls for `gcloud`/`gh`/`helm`/`kubectl` still came back with `resolved: 0`
   despite `_classify_via_claude` returning a non-empty, well-formed result — because the model
   prefixed every key with the tool name (`"gh run list"` instead of the requested `"run list"`),
   and a straight `verdict.get(key)` lookup by the original key silently found nothing for any of
   them. The rubric already asked for "the exact key strings given" — that instruction just isn't
   airtight either. Fixed defensively rather than by rubric-tuning alone: `_strip_tool_prefix`
   strips a leading `"<tool> "` from every returned key before it's used for lookup, in both
   `classify` and `reconfirm` — free when the model behaved, a real recovery when it didn't.

None of these were hypothetical hardening — each was caught by actually running the resweep across
six tools and checking `help-cache` node keys against `rules` node keys for gaps, not by reading the
code and assuming it was right.

### Two things tool upgrades break, neither of which announces itself

Found 2026-08-23 while committing a batch of regenerated artifacts after several tools had been
upgraded (`dprint` 0.54.0 → 0.56.1, `twine` 6.2.0 → 7.0.0, `zensical` 0.0.44 → 0.0.56, `nuitka`
4.1.2 → 4.1.3, `mkdocs` rebuilt against a new Python). Both are upgrade-triggered, so neither shows
up in the one-tool-at-a-time development loop.

1. **A `STALE` flag that doing exactly what it asks could never clear.** `status` calls a tool stale
   by comparing the installed version against the `version` field in its rule entry, but `classify`
   only wrote that entry when at least one node's help text had actually changed — the
   `not to_classify and not new_invalid` path returned before `_save_rule`. An upgrade whose
   `--help` is byte-identical (a patch release; or `mkdocs --version`, which merely names the Python
   path it was installed against) therefore left the tool flagged `STALE` permanently: re-extract
   and re-classify are what `STALE` asks for, both had been run, and neither could clear it.
   `mkdocs`, `nuitka` and `zensical` were all sitting in that state. The cost isn't the flag itself
   — it's that a flag which survives doing what it asks is one you learn to skip past, which defeats
   the only signal `status` has for "this tool actually needs attention". Fixed with
   `_version_only_refresh`: on that path, persist `version`/`extracted_at` and nothing else.
   `nodes`, `reviewed` and `classified_at` deliberately stay put — identical help text means the
   existing classification genuinely does describe the new version, so resetting `reviewed` would
   send a human to the gate to approve a diff that doesn't exist, which is how a gate stops being
   taken seriously. Split into its own helper rather than left inline so it's unit-testable like the
   rest of the module.
2. **Hand-pinned `subcommands` lists don't track upstream renames, and the extractor hides it.**
   `dprint` 0.56 renamed `output-file-paths` to `file-paths` (and `output-resolved-config` /
   `output-format-times` likewise, neither of which is tracked here). Nothing failed: the old name
   is still accepted as an alias, so `extract` re-fetched help under the pinned key and got back
   text whose usage line already read `Usage: dprint file-paths`. The rule therefore covered a
   deprecated spelling while the canonical name had no rule at all and would prompt. A version bump
   is not evidence the pinned list still matches reality — the help text itself is, and the mismatch
   is only visible by reading it. Worth re-reading pinned `subcommands` lists against the
   re-extracted `_top` help whenever a tool takes a minor-version bump, not just a major one.

### Review — the human gate

`inv allowlist.review` shows what's new or changed since the last reviewed snapshot — printed as an
indented tree (nested subcommands under their parent, candidate flags under their node) rather than
a flat list, since a 150+ node tool is unreadable any other way — and, on confirmation, marks a tool
`reviewed: true`. The nesting isn't stored structurally anywhere — `rules/<tool>.json` is a flat
dict keyed by full path — it's reconstructed at print time two ways at once: sorting paths
alphabetically naturally clusters every node under its parent already, since a path is literally
`"<parent> <child>"` and a child's string always sorts immediately after its parent and before the
parent's next sibling; and only the _trailing_ segment of each path is printed as the label; with
indentation carrying the depth (`path.count(" ")`), the result reads as an actual tree (`network`
then indented `create`/`rm`/`ls`) instead of the full path repeated at every line (`network`,
`network create`, `network rm`, ...), which is what an early version did and what prompted this — it
read as a flat, oddly-doubled list rather than a hierarchy, especially once a rationale routinely
ran past one line and, without a deliberate hanging indent (`_wrap`, using `textwrap.fill` with
`subsequent_indent`), wrapped back to column 0 instead of staying aligned under its entry.

**Nothing downstream trusts an unreviewed entry** — `render` and `apply` silently exclude any tool
that hasn't been through this. This is a per-_tool_ gate, not per-node: there's no mechanism to
individually override a single node's (or flag's) classification without re-running the LLM step
(`reconfirm` for `needs_review` specifically, a normal `classify --force` for anything else) — which
is why unresolved `needs_review` entries stay excluded even after their tool is marked reviewed.

`--only=dangerous,needs_review` (comma-separated classification tiers) narrows the per-node dump to
just those tiers — useful for triaging a large tree without reading past every `read_only` entry
first. Command/classification names print in color (tier-coded: green/yellow/red for
read_only/write/dangerous, magenta for needs_review, gray for invalid) when stdout is a real
terminal and `NO_COLOR` isn't set; rationale text is deliberately left in the default color so it
doesn't compete for attention, and every line wraps to the terminal width with a hanging indent
instead of running to the edge and wrapping back to column 0.

### `render` / `apply` — where the classified data goes

`render --target=claude|copilot` is pure, deterministic, output-only: turns the reviewed subset of
`rules/*.json` into Claude `Bash(...)` glob-prefix rules or Copilot
`chat.tools.terminal.autoApprove` regex rules — one rule per node, using its full path
(`Bash(docker network rm:*)` for a depth-2 node, same as `Bash(git status:*)` for a depth-1 one —
the pattern-building code doesn't need to know how deep a node is, a path is just a path). Per-flag
ratings aren't rendered here at all — see the "important limitation" note above. It never writes
anywhere by itself.

One deliberate exception to "one rule per node": **any** node that has children of its own (checked
against `help-cache/<tool>.json`'s `children` list, not `rules/`, since that's where tree structure
actually lives) is skipped entirely, regardless of its own classification tier — not just
`read_only` ones, as an earlier version of this logic had it. A `read_only` parent's bare-invocation
verdict (`docker network` with no further args just lists/describes, like any other read_only
command) was always pure noise once real usage goes through a child (`docker network rm`,
`docker
network create`), each already getting its own, independently-correct rule: Claude Code's
permission precedence is deny > ask > allow with **no specificity tiebreak** — confirmed against the
actual docs (<https://code.claude.com/docs/en/permissions.md>), not assumed — so a stricter rule for
a child always wins over a looser `allow` for its parent regardless of whether the parent's rule
exists at all. But for a `write`/`dangerous` parent, rendering its rule anyway wasn't just noise —
it was actively harmful: that same no-specificity-tiebreak precedence means the parent's `ask` rule
unconditionally _shadows_ a correctly-classified `read_only` child's `allow` rule. Caught live
(2026-08-23): `gh run` classified `dangerous` was shadowing `gh run view`/`gh run list`'s own
already-correct `read_only` `allow` rules, forcing a prompt every time despite the more specific
rule being exactly right — not gh-specific, the same shape hit `docker`, `git`, `go`, `glab`,
`helm`, and `kubectl`. Generalizing the skip to every tier fixed all of them at once. The one
behavior change from omitting a parent rule: a bare invocation with no subcommand at all (rare)
falls through to Claude's own default instead of being pre-approved/pre-gated — typically still a
prompt, not silent approval and not silent denial.

**Flip side of that generalization, and why `check-coverage` exists**: a `write`/`dangerous`
parent's own rule used to be a real (if imprecise) safety net for a child that fell through the
cracks — missing from `rules.json` entirely (the "chunk silently dropped nodes" bug documented
below), or stuck at `needs_review` forever (excluded from render/apply by design). Once the parent's
rule is _always_ skipped when it has children, that fallback is gone: an uncovered child now gets
zero rule at all, not just a looser one. `inv allowlist.check-coverage` walks every reviewed tool's
discovered tree and flags exactly that gap (missing-from-rules.json or stuck-needs_review children
of any node with children); `apply` calls the same check and refuses to write
`~/.claude/settings.json` if it finds anything, rather than silently shipping a coverage hole.
`render` prints the same warning but still completes, since it's output-only and someone may want to
see the (partial, gappy) result while debugging.

A second, unrelated exception: **`cloud_cli` tools never get an `allow` rule, full stop**, whatever
their own classification says. This one _is_ a real safety gap that was caught before it ever
reached `apply`, not a theoretical one — worth walking through, because it's the flip side of the
container-omission logic above and easy to miss. `gcloud`/`aws` never recurse (that's the entire
point of `cloud_cli`), so every one of their nodes is a bare top-level service-group command,
classified on what running _that_ with no arguments does — almost always "shows help/lists things,"
hence `read_only`. But unlike a recursed tool, there's no child node to correct for that:
`gcloud
storage`, `sql`, `secrets`, and `run` all came back `read_only` this way, and all four have
genuinely destructive real subcommands (`storage rm -r`, `sql instances delete`,
`secrets versions destroy`, `run services delete`) with no narrower rule anywhere to catch them — a
`Bash(gcloud storage:*)` allow rule is a plain prefix match, so it would have covered the
destructive form too. Caught by reading the `render --dry-run`-equivalent diff before running a real
`apply`, not by reasoning about it in the abstract. Fixed at `_compute_claude_rules`, not in the
rubric: any node belonging to a tool with `cloud_cli = true` in `tools.toml` is capped at `ask`
regardless of what its own classification says — the one place a node's classification is capped
rather than trusted outright.

`apply` (Claude only, so far) is what actually makes the rules take effect: it merges the
`allow`/`ask` output into **`~/.claude/settings.json`**, the global per-user config that applies to
every project on this machine. Two things make this safe to run repeatedly without either clobbering
your own settings or leaving stale rules behind:

1. **Only the `permissions` block is ever touched.** Every other key — `theme`, `effortLevel`,
   `cleanupPeriodDays`, anything else you or a future you adds — is read, kept, and written back
   unchanged.
2. **A local manifest tracks exactly which rule strings this pipeline wrote last time**
   (`~/.local/state/power-user-linux-setup/claude-settings-applied.json` — deliberately _not_ repo
   content, unlike everything under `cli-allowlist/`, since it's machine-local mutation-tracking
   state for an out-of-repo file, the same category as
   `~/.config/power-user-linux-setup/identity.toml`). On each run, only rule strings present in that
   manifest are eligible for removal; anything else already in your `permissions.allow`/`ask` — a
   rule you added by hand — is never touched, and a rule this pipeline generated before but no
   longer does (a tool's classification changed) gets cleanly removed instead of left orphaned. A
   `.json.bak` is written alongside the settings file before every real change.

Verified directly, not just by reading the code: idempotent re-run is a true no-op; a manually added
rule survives repeated `apply` runs untouched; a tool's classification changing tiers (tested by
flipping one back and forth) correctly moves its rule between `allow` and `ask` with an accurate
diff report. (The first version of the diff report was itself wrong — it compared the flattened
union of both arrays, so a rule moving from `allow` to `ask` printed as `+0 -0`. Caught by testing
the actual move, not by reading the diff logic and assuming it was right.)

Both tiers always still let you approve interactively — `write` and `dangerous` classifications
render as `ask` rules, never `deny`. This was a deliberate call, not an oversight: a PreToolUse hook
that intercepts and blocks specific patterns (the approach a couple of community repos take, and
what Anthropic's own docs suggest as the workaround for prefix-glob allowlisting's known fragility)
was considered and rejected — it changes the agent's control flow more invasively than a declarative
`ask` rule, for a benefit (catching a dangerous command _before_ Claude even proposes it, vs. after)
that didn't seem worth the added complexity of a custom interception script. What matters is that
dangerous-tier commands still surface a real, interactively-approvable prompt instead of running
silently — plain `ask` rules already get that.

### `mode_covered` and `global_option_prefixes` — shaping output without touching verdicts

Both are `tools.toml` registry fields read only by `_compute_claude_rules`; the classification on
disk is untouched, still reviewed, still reported by `status`. They exist because the machine's
default permission mode moved from `auto` to `acceptEdits` on 2026-08-24 (dogfooding; the design
comparison and the transcript audit behind the decision are in the `session-bash-audit` skill's
`references/research.md`), and two facts about that mode interact with prefix rules:

- **`mode_covered = true`** (`cp`, `mv`, `rm`, `rmdir`, `mkdir`, `touch`). `acceptEdits`
  auto-approves exactly these filesystem commands for paths inside the working directory or
  `additionalDirectories`, and prompts for paths outside — a path-aware gate no prefix rule can
  express. But an explicit `ask` rule beats a mode grant (same ask-over-allow, no-specificity
  precedence as everywhere else in this doc), so the pipeline's honest `write` verdict rendered as
  `Bash(mkdir:*)` `ask` re-prompted every in-scope `mkdir`. The field keeps the verdict and drops
  the rendered `ask`. Under `default`/manual mode nothing is silently opened up: an unmatched
  non-read-only command prompts anyway; the difference is only that the prompt comes from Claude
  Code's own default instead of an explicit rule. `apply`'s manifest diff removed the six old `ask`
  rules cleanly on the next run — no hand edit.
- **`global_option_prefixes = ["-C *", "-c *"]`** (`git`). Every rendered rule assumes the
  subcommand is the second word; `git -C <path> status` isn't, so it matched nothing and prompted —
  the most common unmatched git shape in the 4-day transcript audit (81 `git -C` calls). The field
  emits an extra `allow` per prefix for each read_only leaf: `Bash(git -C * status:*)`. Allow-only:
  an `ask` twin would be redundant (unmatched `git -C x push` already prompts in every mode that
  prompts), and Claude Code's mid-pattern `*` spans any number of arguments, so the allow side has a
  known hole — `git -C x commit -m status` also matches `Bash(git -C * status:*)`. Chosen with eyes
  open (2026-08-24) over accepting a prompt on every cross-repo read; revisit if the rule syntax
  ever gains a single-argument wildcard.

Under `auto` mode the picture differs: the classifier, not the prompt, catches an unmatched
`git -C x push`, and it approved all 81 of those calls in the audit window — one of the reasons the
mode was dropped. `plans/2026-08-22-compound-command-permission-audit.md` has the forensics.

### `allow_overrides` / `ask_overrides` — per-verb render overrides (2026-08-25)

The first day of `acceptEdits` answered the open question from the mode switch — what actually
prompts — and the answer was not the shapes anyone had guessed. A simulation of the harness's
matching over every Bash call since the switch (373 calls; the script and the numbers are in the
`session-bash-audit` skill's `references/research.md`) put **40% of calls at a prompt, and 67% of
those prompts on the git commit flow**: `git add` (35), `git commit` (26),
`git -C <other> add/commit` (18), `git push` (10), `git rm`/`restore --staged`/`reset -q` (10). The
cause was the interaction of two things each correct on its own: `~/AGENTS.md` mandates many small
single-concern commits, each staged right before it and `git fetch`ed before every push; and the
pipeline's honest `write` verdict on `add` ("reversible with reset") rendered as `ask`. Two to four
prompts per commit, multiplied by the commit count the instructions themselves drove up. `fetch`,
`rm`, `restore`, `switch`, `mv` weren't even registered in `tools.toml`'s `[git]` list, so they
prompted as unmatched.

`mode_covered` can't express this (per tool, not per verb) and reclassifying can't either — `add`
_is_ a write. The per-node knob the `review` docstring said didn't exist now does, on the render
side only: `allow_overrides = ["add", "rm", "reset", "restore --staged", "fetch"]` renders those as
`allow` (with the `global_option_prefixes` variants, so `git -C ../other add` stops prompting too),
suppressing the node's own generated `ask`; the verdict on disk is untouched. The line is "can this
lose uncommitted code": `commit` and `stash` stay `ask` (user decision, 2026-08-25 — commit is the
checkpoint, stash hides work), and every flag shape that can discard work gets a literal `ask` entry
in `ask_overrides` — `reset --hard/--merge/--keep`, `restore --staged --worktree`/`-W`, `rm -f`/
`--force`/`-rf` — each in two forms, `verb --flag` and `verb * --flag`, because the mid-pattern `*`
spans any number of arguments and so closes the flag-order hole (`git reset -q --hard` matches
`Bash(git reset * --hard:*)`). This is the first real consumer of "the per-flag data can't be
rendered as prefix rules": it still can't in general, but a hand-picked list of code-losing flags
per verb can, because `ask` beats `allow` with no specificity tiebreak. Residual, accepted:
single-letter clusters (`git rm -qf`), `-S` for `--staged`, `-W` written before `--staged` — every
one falls through to a prompt, never to an allow, so the hole is friction, not exposure.

`review` gained `--tool=<name>` at the same time. Re-registering verbs re-pends the whole `git`
tree, and `--apply-all` without a tool filter would have marked `sed` and `inv` reviewed too — the
exact near-miss the `sed` section below records — while from an agent's non-TTY Bash tool
`util.confirm` can only return its default, so there was no way to approve one tool and not the
others.

### End-to-end confirmed live

This isn't just tested in isolation — after `apply`, the actual rules were exercised in a live
Claude Code session: `allow`-tier commands (`git status`, `cat`, `jq --version`) ran without any
visible prompt; `ask`-tier commands (`rm --help`, `git add --help`, `npm install --help` — chosen so
they're harmless to execute either way) triggered real permission prompts. Confirmed by the user
watching the session, since a silent auto-approval and an instantly-approved prompt look identical
from the agent's own side.

## Retention policy note

While reviewing the global `~/.claude/settings.json` for this work, `cleanupPeriodDays` (governs how
long session transcripts, `tasks/`, `shell-snapshots/`, and `backups/` under `~/.claude/` are kept
before cleanup) was checked and deliberately left at **365** — the default is 30; other users in the
wild range from 60 to effectively-unlimited (99999). Not a disk problem at the time this was
reviewed (~52M total under `~/.claude/`, oldest transcript only a couple of days old on a
freshly-set-up install) — this was a preference call, not a fix.

## Known gaps / deliberately not built

- **`apply` only targets Claude's `settings.json`.** Copilot's `chat.tools.terminal.autoApprove`
  still needs manual copy-paste from `render --target=copilot`. The read_only-parent-with-children
  omission (see `render`/`apply` above) is Claude-specific for the same reason — it leans on a
  verified deny > ask > allow, no-specificity-tiebreak precedence that hasn't been confirmed for
  Copilot's own rule resolution, so `_render_copilot` doesn't apply the same skip.
- **No sandboxing integration** (`/sandbox`, OS-level filesystem/network isolation) — a stronger,
  orthogonal control considered out of scope for this pass.
- **No PreToolUse hook** — see the `render`/`apply` section above for why this was a deliberate
  rejection, not a TODO.
- **No node-level review override beyond `needs_review`.** `reconfirm` closes this gap specifically
  for the verb-backstop's `needs_review` tier; there's still no way to manually promote/demote an
  ordinary `read_only`/`write`/`dangerous` verdict without a full `classify --force` re-run for that
  tool.
- **Per-flag ratings aren't consumed by `render`/`apply`.** Deliberate, not an oversight — see the
  "Per-flag ratings" section above for why prefix-glob rules structurally can't express "allow this
  subcommand except with `--force`". The data exists for `review` and for a future consumer that can
  actually act on it order-independently.
- **Recursion stops at `max_depth = 2` for every opted-in tool so far**, and cloud-provider CLIs
  (`gcloud`, `aws`) don't recurse at all (`cloud_cli = true`, hand-curated top-level list instead).
  Both are a documented scope boundary — deep-diving `gcloud`'s or `aws`'s actual command surface,
  or going to depth 3 for e.g. `kubectl create <kind>`, would be a real node/cost/review-burden
  increase for command shapes that are almost never run unattended by an agent.
- **Truncated trees (`max_nodes` exceeded) are flagged but not resolved automatically.** `status`
  and `review` surface a `truncated` marker; raising `max_nodes` for that specific tool in
  `tools.toml` and re-extracting is a manual follow-up, not something the pipeline does on its own.

## `sed` — deliberately unreviewed, hand-maintained rules instead

`sed` is `no_subcommands` — one classification unit (`"*"` node), `write`, because of `-i`. Since
per-flag ratings don't drive `render`/`apply` (see above), that single `write` verdict became a
blanket `Bash(sed:*)` `ask` rule that gated every sed invocation, including plain `sed -n` reads —
confirmed as real friction (2026-08-23): every actual `sed` call Claude Code has ever issued on this
machine, across every project, is a `sed -n '<range>p' <file>` view (zero `-i` calls — the Edit tool
preference already works for mutation; the friction was entirely on the view side).

Fixed by taking `sed` out of the generated pipeline rather than trying to make `render` express
"allow this flag, not that one" (still structurally impossible, per the per-flag-ratings note
above): `cli-allowlist/rules/sed.json` has `"reviewed": false` set by hand, so `render`/`apply` skip
it entirely (same as any other never-reviewed tool) and the old blanket `Bash(sed:*)` `ask` rule was
cleanly removed by a normal `apply` run's manifest-based diff — no hand-editing of `settings.json`
needed for the removal itself. Three rules are then hand-maintained directly in
`~/.claude/settings.json`, outside the generated/reviewed flow:

- `Bash(sed -n *)` — `allow`. Covers the actual real-world usage shape. Deliberately requires `-n`
  as the leading token: `Bash(sed -n *)`'s trailing-wildcard word boundary means it does **not**
  match a combined `-ni`/`-in` invocation (mutates while filtering) — that falls through to no rule
  at all, i.e. still prompts, which is the safe default. Known, accepted residual gap: a prefix-glob
  rule can't see into the script argument's content, so a hostile `sed -n` script using GNU sed's
  `w` command or `e`/`s///e` extensions to write files or run shell commands would still match this
  allow rule — same class of gap the permissions doc's own `curl` example warns about. Accepted as a
  low-probability trade-off for real day-to-day friction, not an oversight.
- `Bash(sed -i*)` and `Bash(sed --in-place*)` — were `ask`, added explicitly so mutation stayed
  visibly gated rather than relying on Claude Code's default for an ungoverned `sed`. **Removed
  2026-08-24** with the move to `acceptEdits` (see the `mode_covered` section below): that mode
  auto-approves `sed` on in-scope paths and prompts outside them, and an explicit `ask` rule would
  have beaten the in-scope grant. Under a mode that doesn't grant `sed`, an unmatched `sed -i` still
  prompts — nothing became silently allowed. Re-add them by hand if the machine ever runs a mode
  where an ungoverned `sed -i` would run unprompted.

**Do not re-review `sed` via `inv allowlist.review` without deliberately deciding to** — marking it
reviewed again would let the next `apply` regenerate the blanket `Bash(sed:*)` `ask` rule (sed's
node classification itself hasn't changed, only whether the pipeline is allowed to act on it), which
would silently shadow the hand-maintained `Bash(sed -n *)` allow rule via the same no-specificity-
tiebreak precedence documented above.

**Near-miss confirmed 2026-08-23**: this prose warning alone wasn't enough — `sed` got re-approved
by habit in a later session (an agent triaging an unrelated batch of pending reviews, `sed` included
among them with no visible signal it was different from an ordinary new classification), caught only
because the approver double-checked before the next `apply` ran. Fixed by adding a `note` field
directly to `cli-allowlist/rules/sed.json` — `review()` already prints `entry["note"]` inline before
the confirm prompt (see the `review` section above), so the warning now surfaces at the moment of
the decision itself, not only in a doc someone has to already know to open.

## `inv` — deliberately unreviewed, same shape as `sed`

Structurally identical to `sed` above, and worth stating separately because the trigger looks
nothing alike. `inv` (invoke) is `no_subcommands` — one `"*"` node, classified `write`, which is a
_correct_ verdict: `inv <task>` runs whatever the current repo's `tasks.py` defines, which can
build, deploy, or delete. The problem isn't accuracy, it's that a machine-wide verdict for a task
runner can't be useful — the real command surface is per-repo and changes with whatever repo you
happen to be standing in, so there is nothing to recurse into and no child node that could ever
correct the parent.

Left reviewed, that single verdict renders a blanket `Bash(inv:*)` `ask` rule, which shadows the
hand-maintained `Bash(inv quality.*)` `allow` rule (added for `repo-tasks`' quality namespace) by
the same deny > ask > allow, no-specificity-tiebreak precedence documented above. Net effect: every
`inv quality.precommit` in every repo prompts, and the allow rule that exists specifically to
prevent that does nothing.

Caught 2026-08-23 by the reviewer asking the right question — "I marked `inv` as write, does that
mean the quality rule gets denied?" — _before_ the next `apply` ran, so the blanket rule never
reached `settings.json`. Worth noting the answer to the literal question was "no": `write` renders
as `ask`, never `deny` (see above), so nothing would have been blocked. It would just have prompted
forever, which is the failure mode that gets lived with rather than noticed.

Fixed the same way as `sed`: `cli-allowlist/rules/inv.json` carries `"reviewed": false` plus a
`note` that `review()` prints inline at the confirm prompt, so the next reviewer sees why before
deciding rather than re-approving by habit. Rules for `inv` stay hand-maintained in
`~/.claude/settings.json` — today just `Bash(inv quality.*)` as `allow`; a genuinely impactful
namespace worth gating gets its own explicit `ask` rule there, not a blanket one.

`pytest`, registered in the same batch, needs none of this: it classified `read_only`, renders
`Bash(pytest:*)` as `allow`, and shadows nothing.
