# Research library (`$RESEARCH_HOME`)

Design rationale for the shared, cross-project reference material store at `~/research/` —
vendor repo clones, PDFs/epubs, mirrored docs pages. What it _is_ and how to use it are covered
by `skills/research-library/SKILL.md` (the deployed skill) and `~/research/README.md` (the
portable copy that travels with the library itself, since this doc doesn't). This page is the
_why_, kept here because it's durable knowledge that belongs in a tracked, reviewable file, not
a local scratch note.

## Why it exists

Before this, reference material (vendor repo clones, PDFs) lived in this repo's own gitignored
`reference/`. Two problems with that:

1. **AI security exposure.** Gitignored ≠ unreadable. Anything operating with a repo as its cwd
   (an Explore agent, `grep -r`, "read the whole repo") walks straight into third-party cloned
   code/docs and treats their content as trusted project context — the vector prompt-injection-
   via-cloned-repo attacks use. Moving the content fully outside any repo directory takes it out
   of the _default_ blast radius of repo-scoped operations; it only enters an agent's context when
   a task explicitly names the external path — deliberate, not ambient.
2. **Not shareable.** Every repo that wanted the same reference material (GNOME internals, Claude
   Code allowlist research) re-cloned it into its own gitignored `reference/`, duplicating disk
   and staleness.

## Layout and naming

```
~/research/
  repos/<host>--<owner>--<repo>/   # shallow git clones, e.g. repos/github.com--zensical--zensical
  docs/<file>.pdf|.epub            # downloaded reference docs
  pages/<host>--<site>/            # mirrored/llms.txt-derived doc site snapshots
  README.md                        # human map + conventions (the portable copy)
```

Flat, not namespaced per project — namespacing was the initial idea but doesn't hold up: the
point of a shared library is that projects overlap in what they reference, and filing each clone
under whichever project pulled it in first just hides the duplication the library exists to
avoid.

**Naming is always `<host>--<owner>--<repo>`, no GitHub special case.** This caught a real
mistake during migration: two of the four repos being moved into the library turned out to be
hosted on `gitlab.gnome.org` (a self-hosted GitLab instance), not GitHub, despite looking like
they might be. A uniform rule forces checking the actual `origin` remote for every entry, every
time; special-casing "GitHub, no prefix" would have hidden that assumption. The prefix is the
full host, not a generic label like `gitlab` — that avoids ambiguity between `gitlab.com` and
self-hosted instances.

**Location: plain `~/research/`, not `~/.local/share/research/`.** The XDG-paths convention this
machine otherwise follows ("user tool installs go to `~/.local/share/<tool>`") is about _tool_
installs cluttering `$HOME`; this is human-facing content opened directly (PDFs, epubs) — more
like `~/Documents` than a tool's data dir.

## Provenance — `SOURCE.md`

Every entry gets a small `SOURCE.md` in its own directory (not a central manifest that can drift
out of sync):

```
url: <repo or docs URL actually fetched from>
kind: repo-clone | llms-txt-mirror | site-mirror
ref: <branch/tag/commit for a repo-clone, or fetch date for a mirror>
fetched: <date>
note: <only when non-obvious>
```

This isn't just for non-git items — a repo's default branch isn't guaranteed to match what's
actually published as "the docs" (docs sites are often built from a `stable`/release-tag branch,
or an entirely separate docs repo). `note:` is where that gets flagged.

**Gotcha found doing the first real migration, not anticipated up front:** the `gnome-shell`
clone had originally been created pinned to release tag `46.0`
(`remote.origin.fetch = +refs/tags/46.0:refs/tags/46.0`), not tracking a branch. The naive
refresh loop (`git fetch --depth 1 origin`) happily kept re-fetching that same 2024-03-16 tag
forever and reporting "up to date" — silently wrong, not an error. Fixed by reconfiguring the
fetch refspec to the actual default branch (found via `git ls-remote --symref origin HEAD`).
Worth checking `git config --get-all remote.origin.fetch` on any entry that looks suspiciously
stale.

## Reachability and update

- `RESEARCH_HOME=~/research` is provisioned via `[packages.research-library]` in `setup.toml`
  (a `zsh`-method `zshenv` field), so every project references `$RESEARCH_HOME/...` instead of a
  hardcoded path.
- **Deliberately no symlink from inside any repo into `~/research`.** That would reintroduce
  ambient exposure to repo-scoped agents — the entire reason the library lives outside every
  repo. Access is an explicit act: a project's `AGENTS.md` names the exact path relevant to a
  given task, read only when that task calls for it.
- `research-update` (deployed via the same package entry's `wrapper-script`/`content_file`, see
  `config/research-update.sh`) refreshes every clone under `repos/` to its default branch's
  latest commit — shallow fetch + hard reset via `FETCH_HEAD`, since these are disposable
  reference clones, not working copies with local commits to preserve.
- Adding an entry is just `git clone --depth 1 <url> $RESEARCH_HOME/repos/<host>--<owner>--<repo>`
  plus a hand-written `SOURCE.md`.

## Discoverability: two layers, not one

- **A global skill** (`skills/research-library/SKILL.md`, deployed to
  `~/.agents/skills/research-library`) teaches the _mechanism_ — where `$RESEARCH_HOME` is, the
  naming convention, how to add/update entries. Applies in every project automatically.
- **Each project's own `AGENTS.md` still needs a short, project-specific pointer** — e.g. "for
  GNOME Shell extension behavior, check `$RESEARCH_HOME/repos/gitlab.gnome.org--GNOME--gnome-
  shell` before reading anything online" — because _which_ library entries matter to a given
  project is knowledge the global skill can't have on its own. This is also what makes the
  convention visible to non-Claude `AGENTS.md` readers (Cursor, Copilot, Aider) with no
  equivalent global-skill discovery of their own.

The instruction that actually delivers "avoid reading lots of files off the internet" lives in
both: the skill says _how_ to check the library; each project's `AGENTS.md` says _prefer the
local copy over `WebFetch`_ as a standing rule, not a one-off suggestion.

## Docs sites (not just repos)

Researched rather than guessed, since mirroring whole websites is a bigger commitment than
cloning a repo:

- **`llms.txt` / `llms-full.txt`** is a real, growing convention — a plain-markdown index or full
  concatenated dump of a docs site, published specifically so an agent can fetch clean text
  instead of crawling rendered HTML. Not a formal standard (no public commitment from
  Anthropic/OpenAI/Google to read it automatically as of early 2026), but real adoption (Stripe,
  Clerk, Snowflake, others). Where a site has one, it's the best thing to cache.
- **Prefer the source repo over the built site when one's public** — most docs sites (mkdocs/
  docusaurus/sphinx/zensical) are generated from markdown/rst in a public repo, often the
  project's own. Cloning that gets clean source instead of scraped HTML and reuses the `repos/`
  bucket and update mechanism already built — no new tooling.
- **Fallback tier, only when neither exists:** purpose-built mirror-to-markdown tools —
  [`llms-mirror`](https://pypi.org/project/llms-mirror/0.1.0/) (pulls via a site's `llms.txt`
  index) and [`site2md`](https://github.com/CamiloMartinezM/site2md) (wget-based mirror +
  HTML-to-Markdown cleanup). Both beat hand-rolled `wget --mirror` plus manual conversion.
- **Order: `llms.txt` → clone source repo → general site-to-markdown mirror.** Full site
  mirroring is the fallback of last resort — most staleness risk, plus a new tool dependency.
- **Bucket:** `pages/<host>--<site>/`, no version segment by default ("latest" is normally the
  goal; re-fetch in place rather than accumulate dated snapshots). Version actually fetched goes
  in that entry's `SOURCE.md`.
- Docs sites move faster than repos and have no pinned commit to anchor to — `research-update`
  should eventually re-fetch `pages/` entries on their own, shorter cadence, not `git pull`.

Sources: [Write LLM-friendly docs (Fern)](https://buildwithfern.com/post/how-to-write-llm-friendly-documentation),
[llms.txt guide (Fern)](https://buildwithfern.com/post/optimizing-api-docs-ai-agents-llms-txt-guide),
[Snowflake docs for AI agents](https://docs.snowflake.com/en/release-notes/2026/other/2026-04-15-agent-friendly-docs),
[llms.txt: Making Your Project Discoverable to AI Agents](https://www.agentpatterns.ai/standards/llms-txt/).

## RAG / embeddings — researched, not adding

**Reminder of the mechanics:** RAG means an external index, not the model's trained knowledge,
supplies facts at answer time — chunk source text, embed each chunk, store the vectors, embed
the query at search time, splice the nearest chunks into the prompt. It's how you search a corpus
too large to hand the model wholesale, and it matches on meaning rather than exact wording — at
the cost of a whole pipeline (chunker, embedding model, vector store, re-embed-on-update) to
build and keep in sync.

**2026 consensus:** the industry has moved _away_ from vector-DB RAG for code specifically —
multiple sources describe Anthropic/Claude Code itself moving off a vector-RAG pipeline toward
agentic search (grep, glob, file reads, symbol navigation), because code questions are usually
literal ("where is `X` defined") and exact-match search answers them better and cheaper. RAG
still earns its place for monorepos too large to grep from scratch each time, genuine concept
search, and large non-code corpora — usually hybrid, not embeddings alone.

**Applied here: doesn't clear the bar.** Curated entries, `AGENTS.md` naming the exact relevant
path, individually modest-sized repos/docs — that's already what makes agentic grep/Read
sufficient, the tool Claude Code already uses natively with zero added infrastructure.

**Revisit trigger, not a default:** a genuinely large, term-agnostic corpus (a huge PDF manual or
doc dump where the right search term isn't known and a full read-through isn't practical) is the
specific condition that would justify a lightweight local option (a local embedding model +
something like `sqlite-vec`, exposed via an MCP server) — added for that case, not built
preemptively.

**Checked against actual expected use, not just in the abstract:** the realistic workloads here
are a single novel at a time (themes/characters/style) or a handful of papers/books on one topic
— not hundreds of documents with repeated queries, the scenario where RAG's cost/recall numbers
actually apply. At that scale the corpus fits in a single context window outright (no retrieval
step needed), and for the novel case specifically, chunked retrieval would work _against_ the
task — themes and style are properties of the whole book, and top-k retrieval severs the
cross-chapter connections that kind of analysis depends on.

Sources: [RAG Is Not Always the Answer Anymore (DEV Community)](https://dev.to/nimay_04/rag-is-not-always-the-answer-anymore-how-ai-agents-search-code-in-2026-43m3),
[Why Claude Code Dropped Vector DB-Based RAG (SmartScope)](https://smartscope.blog/en/ai-development/practices/rag-debate-agentic-search-code-exploration/),
[Code Retrieval: Grep, RAG, or Both? (Medium)](https://medium.com/@jhanavibehl/code-retrieval-grep-rag-or-both-706cdefd0b70),
[grep vs. RAG (LlamaIndex)](https://www.llamaindex.ai/blog/is-grep-all-you-need-lexical-vs-sematic-search-for-agents).

## Packaging conventions as a skill — and a reversal worth remembering

The library's own conventions are packaged as a skill (`skills/research-library/SKILL.md`,
declared via `setup.toml`'s `skills = [{ source = "local", path = "..." }]` field, deployed as a
real copy — not a symlink — by `inv ai.skills`; full mechanism documented in
`docs/claude-code.md`). That `npx`-source path (installing a skill straight from a GitHub repo
via the `skills` CLI) was validated end-to-end against a real package,
[caveman](https://github.com/JuliusBrussee/caveman) — worth recording why it _isn't_ installed
that way today, since the reasoning generalizes:

Caveman ships terse-communication-style rules. Installed first as a skill, then also duplicated
into `~/AGENTS.md` for cross-tool, always-on reach — a skill only reaches Claude Code, and
loads conditionally, where AGENTS.md is unconditional and read by every agent tool on the
machine. Once both existed, the skill was mostly redundant for Claude Code specifically, and its
only remaining value (switchable intensity levels) was more complexity than wanted. Reversed:
skill uninstalled, only the AGENTS.md copy kept, trimmed down to one always-on mode with no
levels — the simplest version that still keeps the two things that matter (never drop negations,
carve out security/irreversible actions). **The lesson for future skill decisions:** if a skill's
behavior needs to apply unconditionally and across every agent tool, it belongs in `AGENTS.md`,
not as a skill — a skill is the right tool only for something genuinely conditional/on-demand or
Claude-Code-specific.
