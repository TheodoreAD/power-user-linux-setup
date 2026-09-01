---
status: in-progress
updated: 2026-09-02
---

## Context

A full review of the published docs site (2026-08-27) — all 37 `docs/*.md` pages' structure, ~15
read in full, plus `mkdocs.yml`'s nav/theme, `docs/extra/extra.css`, and the built output under
`site/`. The question asked was user-friendliness from an _informational_ standpoint (is the right
material there, findable, and correctly framed), explicitly not graphic design.

Finding: content quality is high and the mechanics are sound; **discoverability and framing are the
weak parts.** The site reads like a well-kept engineer's notebook rather than a project's
documentation. A newcomer cannot tell what they get, what order to read in, or which pages apply to
their machine.

What already works, and should not be disturbed by any of the below:

- The nav is an explicit 7-tab tree in `mkdocs.yml`; all 37 pages are reachable and none are
  orphaned.
- `docs/index.md` does the right things: four use-case cards, quick start, env-var table, manual
  steps, maintenance. The cards genuinely render — `.grid.cards` rules are present in the built
  `site/assets/stylesheets/*/main.*.min.css`, and the `:material-*:`/`:octicons-*:` icons resolve (8
  twemoji hits in `site/index.html`).
- `docs/configuration.md` is the strongest page by a distance: mechanism → why → idempotency →
  tables → sample console transcript.
- The large pages already share a real template — quick start → how it works → genuine limitations →
  see also (`certs.md`, `corporate-proxy.md`, `wsl.md`, `dev-container.md`, `claude-code.md`).
- CI builds with `zensical build --strict`, which aborts on broken links and unresolved heading
  anchors, so link accuracy is already machine-guarded and needs no manual audit.

## Problems found, by impact

**1. No answer to "what do I actually get."** There is no package catalog anywhere on the site.
`docs/apt_packages.md` documents install _methods_, not contents. `setup.toml` is 90KB and is never
rendered. The curated tool list is the project's single most attractive asset and it is invisible to
anyone who does not open the repo.

**2. Three audiences interleaved with no signposting.** Repo documentation (`configuration`, `zsh`,
`terminal`, `fonts`) sits beside single-machine operational notes (`troubleshooting` — Gigabyte Z390
and RTX 3070 Ti; `input_devices` — one Kinesis Advantage 360; `keybindings` — a live dconf dump
dated 2026-08-08; `citrix`; `chrome`) and beside general landscape essays (`ai.md`, 226 lines of
which PULSE installs exactly one entry). Nothing tells a reader which kind of page they are on until
they are several screens in.

**3. Extreme page-quality variance, flattened by the nav.** `docs/shortcuts.md` is a bare
askubuntu.com URL followed by a 70-line unexplained gsettings script, with no prose, overlapping
both `screen_capture.md` and `keybindings.md`, carrying a `flamehost_output_path` typo, and nothing
in `setup.toml` runs it. `docs/github.md` is 18 lines. The sidebar presents both as peers of
`How it works` (399 lines).

**4. No reading path.** The index cards point at four environment profiles, then the tab bar goes
topic-by-topic. Nothing distinguishes day-one material from reference. The `Reference` tab in
particular is a junk drawer, and `apt_packages.md` — core mechanism — is filed inside it at the far
right of the tab bar.

**5. Pages dead-end.** Only `certs.md` and `corporate-proxy.md` carry a `## See also`. Every other
page ends and returns the reader to the sidebar.

**6. Zero visual aids.** `docs/` contains no image files at all — no screenshots of the terminal
layout, the p10k prompt, or the GNOME setup this repo produces. Mermaid is wired up and verified
working (`contributing/zensical.md`) and entirely unused. Four mechanisms are pure prose-and-table
today and are natural diagrams: the `inv setup` phase sequence, `deploy.all`'s five-state
classifier, the allowlist extract → classify → review → apply pipeline, and sentinel-block file
ownership.

**7. Search carries all cross-cutting navigation.** Zensical's native plugin allowlist has no `tags`
plugin (`contributing/zensical.md`), so there is no way to surface "everything WSL touches" other
than search — which means the nav tree has to do more work than it currently does.

## Accuracy findings

Two stale references, both in the same file, both cheap:

- `docs/configuration.md:233` cites "the `cleanup.*` umbrella tasks". No such namespace exists —
  `inv --list` shows `clean.all`, `clean.all-full`, `clean.caches`, `clean.caches-full`.
  `docs/index.md:122` already gets this right.
- `docs/configuration.md:318` annotates `inv ai.install-skills` with "see ai.md". `docs/ai.md` says
  nothing about skills; the material is in `docs/claude-code.md`.

Adjacent, outside `docs/`:

- ~~`CONTRIBUTING.md:10`'s "there is deliberately no integration tier" contradicts `inv --list`~~ —
  **checked 2026-08-28 and withdrawn.** Both are correct: the tier tasks ship from `repo-tasks` to
  every consumer and `tests/README.md:64` states they "no-op cleanly on the missing directory". The
  finding came from reading `inv --list` against a sentence without opening the file that explains
  the relationship. Left here rather than deleted so the same surface reading doesn't re-raise it.
- `docs.build`, `docs.serve`, and `docs.clean` tasks exist and are documented nowhere — not on the
  site, not in `CONTRIBUTING.md`.

- `mkdocs.yml` opens with five unresolved `TODO:` comments, plus one in `docs/extra/extra.css`.
  Recounted 2026-09-02: **eleven** in `mkdocs.yml`, not five — the five at the top are the ones a
  reader meets first, which is how the count came out low.

### Step 7 landed 2026-09-02

- Both `docs/configuration.md` references fixed: the `cleanup.*` umbrella tasks are named `clean.*`
  (and are now listed rather than gestured at), and `inv ai.install-skills` points at
  `claude-code.md`, which is where the two skills sections actually are.
- `CONTRIBUTING.md` gained **`## Docs site`** — `docs.serve`/`build`/`clean`, that `docs.build` is
  the same `zensical build --strict` the Pages workflow runs, that zensical is pinned in
  `requirements-docs.txt` rather than in `pyproject.toml`, and a warning that the gate does not
  build the site.
- The same file's gate description was **wrong, not merely incomplete**: it listed `check` as five
  members ending in `test`, where the chain has eleven. `workflow_check`, `dockerfile_check`,
  `link_check`, `deps_check` and `untested_modules` had all joined without the page noticing.
- `mkdocs.yml`'s "figure out how CI works, implement, document" TODO and its dead
  `mkdocs-deploy-gh-pages` link were replaced by what CI actually does. The other ten TODOs are live
  intentions of the author's (theme tuning, extension research) and were left alone.
- Verified with `inv docs.build` — `No issues found`, strict.

[PITFALL: writing that list turned up a gap the docs were accurately describing: `deps_check` ran
inside `quality.check` while `inv deps.check` did not exist here — `tasks/__init__.py` published
`agents`, `configs`, `dev_env`, `docs`, `quality` and `testing`, and no `deps`. The gate ran a check
nobody could re-run on its own to see what it objected to. Fixed rather than documented, on the
user's call: the collection is published like every other repo-tasks namespace, bringing `lock`,
`audit`, `list`, `tree` and `export` with it. The find is the point — a stale docs sweep is a cheap
way to notice a real one, because writing down what a command does is when you check.]

[PITFALL: **`inv quality.precommit` does not build the docs, so a docs edit can pass the gate and
still break CI.** `inv docs.build` runs the same `zensical build --strict` the Pages workflow does,
and nothing calls it. Confirmed 2026-08-28: renaming a `docs/ssh.md` heading passed the full gate
twice and broke the Pages deploy both times, on an anchor cited from `docs/claude-code.md`. The
failure is invisible locally and only shows up as a red run someone else has to read — exactly the
shape `~/AGENTS.md`'s "About to commit" rule exists to prevent, except the gate genuinely does not
cover it. Two candidate fixes with different costs: add `docs.build` to the `check` chain (slower
gate, catches it before every commit) or leave it standalone and rely on the author remembering
after a docs edit (which is what just failed). Note the rename also violated `plan-docs`' own "grep
inbound references before renaming a section title" rule, so a strict build is the backstop for a
discipline that is already written down and was still missed.]

### The anchor half, half-closed 2026-09-02

`inv docs.link-check` now exists and runs inside `quality.check` — but it verifies only that a
link's _file_ exists. `repo_tasks/docs.py:59-64` strips the fragment by design, so `file.md#heading`
still passes after the heading is renamed. The gate therefore covers the link class that was never
the problem, and the `docs/ssh.md` failure above would happen again today.

The fix belongs in `repo-tasks`, which this repo may not edit, so it is filed there:
`github.com-personal/repo-tasks/2026-09-02-anchor-checking-in-link-check.md` in the plans store. It
carries the design — two sluggers, `markdown.extensions.toc` for the published site (this repo's
`mkdocs.yml` uses the stock one, checked) and GitHub's for everything read on github.com, plus
`attr_list` ids and inline HTML anchors — and the measurement below.

Measured here first, with a throwaway implementation, so the feature would not land blind: **79
fragment links in this repo (59 same-file, 20 cross-file), zero unresolved**; 29 in `agent-skills`,
9 in `repo-tasks`, 0 in `scaffoldapy` and `olx-polite-mcp`, all clean. Nothing in the family needs
cleaning up before such a check goes straight into the gate. It was also shown able to fail, on a
two-file fixture whose target heading was renamed — a measurement that can only print zero is not
evidence.

[PITFALL: the first run reported two unresolved links and **both were the measuring script's bugs**
— `docs/terminal.md`'s link to `configuration.md#whole-file-configs-config_files`, and
`contributing/global-agents-md.md`'s own contents entry. Treating `_` as emphasis mangles
`config_files` into `configfiles`, and collapsing runs of spaces loses GitHub's double hyphen in
`bash--the-cli-allowlist-cluster-intro` (from a heading containing an ampersand). Both links are
correct in both renderers. A checker of this kind fails toward false positives, and a false positive
in a family-wide gate is worse than the dangling anchor it was meant to catch — which is the
argument for measuring across every repo before shipping it rather than after.]

`zensical build --strict` in the gate stays a separate question: anchor checking removes the failure
that motivated it, not every strict-build failure — an unresolved nav entry, say.

`docs/ai.md` is a separate accuracy class: it carries dated market claims ("Cursor … $2B ARR",
Copilot "~42% market share", "top open-weight coding model as of mid-2026") about tools this repo
does not install. Nothing will prompt anyone to refresh them, and they are the first thing a visitor
to the `AI` tab reads.

## Missing pages a visitor will feel

- Package catalog — what is actually installed. Mechanically derivable from `setup.toml`.
- An `inv` task index. `inv --list` is currently the only source of truth for ~110 tasks.
- Updating/upgrading, currently scattered across `index.md` (`apt.upgrade-debs`), `rust.md`
  (`rustup update`), `scala.md` (`cs update`), and `gnome_extensions.md` (`gnome.update`).
- Uninstall/rollback. `inv apt.uninstall` exists; only `rust.md` and `gcloud.md` mention removal at
  all.
- A contributing entry point — `CONTRIBUTING.md` is linked from no docs page, only from the repo
  header link.

## Open questions

[NEEDS CLARIFICATION: is a generated package catalog page the right first move, and generated how?
`inv devcontainer.render-docs` already establishes the pattern — `util.ensure_block` with
`util.MarkerStyle.HTML` writing a table into a committed `docs/*.md` — and `~/AGENTS.md`'s
"Regenerating a file from a canonical source" rule says the output is committed and regeneration is
its own deliberate standalone command, never wired into `fix`/`check`/`precommit`. Open: what the
catalog is grouped by (tag, method, or nav-topic), whether disabled entries appear at all, and
whether `description` fields in `setup.toml` are currently good enough to publish verbatim — they
were written as inline comments for a maintainer, not as catalog copy.]

[NEEDS CLARIFICATION: how should single-machine pages be framed? Two options with different costs.
(a) A nav group named for what they are — "This machine" — keeping them public but honestly scoped;
cheap, and fixes the framing problem without moving content. (b) Move the genuinely
hardware-specific ones out of `docs/` entirely, since a Gigabyte Z390 ELD workaround and a Kinesis
layout dump are not documentation of this repo. (b) collides with the fact that they are real,
useful, hard-won notes with no other home — `contributing/` is explicitly for _this repo's_ design
rationale, not machine ops.]

[NEEDS CLARIFICATION: what happens to `docs/ai.md`? It is a 226-line survey of the AI tooling market
of which PULSE installs one entry (`claude-code`). Trimming it to what this repo installs and
linking out would shrink the `AI` tab to `claude-code.md` + `cli-allowlist.md`, which is arguably
the honest shape. Deleting research the user deliberately gathered is a different call from
reframing it, so this needs a decision rather than an assumption.]

[NEEDS CLARIFICATION: `docs/shortcuts.md` — fold the flameshot binding into `screen_capture.md` and
delete, or keep? The script is unreferenced by `setup.toml`, duplicates `screen_capture.md`, and
carries a typo. Nothing in the repo executes it, so it is either a manual recipe worth one section
elsewhere or dead weight on the public nav.]

## Recommended direction

Rough, and deliberately ordered by information gained per unit of effort rather than by section
order above.

1. **Package catalog generated from `setup.toml`.** The single biggest gap and the most mechanical
   to close. Answer the grouping question first, then reuse the `devcontainer.render-docs` shape.
2. **Re-cut the nav into a path rather than a topic list.** Roughly: Start here (index,
   configuration, apt_packages) → Daily use → Environments → This machine → Reference. Moving
   `apt_packages.md` out of `Reference` and naming the machine-specific group fixes problems 2 and 4
   together, with no content rewritten.
3. **Four mermaid diagrams** — setup phases, the deploy classifier, the allowlist pipeline,
   sentinel-block ownership. Already supported and verified end-to-end; nothing to build first.
4. **A one-line "what this page is for" opener and a `## See also` footer on every page.**
   `certs.md` and `corporate-proxy.md` already model both; this is a sweep, not a design.
5. **Resolve `shortcuts.md` and reframe `ai.md`,** per the open questions above.
6. **Add the task index and an updating/uninstalling page.**
7. **Fix the two stale references in `configuration.md`,** plus the `CONTRIBUTING.md` test-tier line
   and the undocumented `docs.*` tasks. Small enough to land independently of everything above, and
   worth doing first precisely because it does not depend on any open question being answered.

Steps 1–2 are the ones that change how the site reads. Steps 3–4 are what make it attractive
informationally. Nothing here requires touching the theme, the palette, or `extra.css`.
