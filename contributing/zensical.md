# Zensical (docs site engine)

This site is built with [zensical](https://zensical.org/) (`pyproject.toml`'s `docs` dependency
group pins `zensical==0.0.44`), not `mkdocs` + `mkdocs-material` anymore (migrated 2026-08-08).
`mkdocs`/`mkdocs-material` is still installed machine-wide as a `uv tool` (`setup.toml`, see
[docs/python.md](../docs/python.md#system-wide-tools)) for other projects that still use it — it's
just not what builds _this_ repo's docs anymore. Same author as Material for MkDocs, Rust core,
still early alpha. This page tracks what's actually been verified about how it behaves — as opposed
to what the docs say — so the next person (or session) checking whether a newer zensical version
changes any of this has a concrete list to re-test against, instead of re-discovering it all from
scratch.

Everything below was found by actually running `zensical build --strict`, grepping the real
installed package / the built output / the minified theme bundle for ground truth, and rendering
pages in headless Chrome — not by trusting the hosted docs at zensical.org, which turned out to be
incomplete for at least one case (see [Mermaid](#mermaid) below). If you're re-verifying this after
a version bump, that's the method: don't just read the changelog, build the real site and look at
the real output.

## Config format: staying on `mkdocs.yml`, not `zensical.toml`

Zensical supports two config formats: its own native `zensical.toml`, or drop-in `mkdocs.yml` compat
(`zensical build` auto-detects whichever is present, preferring `zensical.toml` if both exist). We
deliberately kept `mkdocs.yml` rather than migrating to `zensical.toml` — the native schema is
early-alpha and the compat path is the officially-supported, more stable one. Revisit this if
`zensical.toml` matures; there's no functional reason to migrate otherwise, since everything below
works fine through the compat layer.

Two things are handled transparently by the compat layer, confirmed by reading `zensical/config.py`
— no action needed when migrating an old Material config:

- `theme: material` (the name) is auto-mapped to zensical's own built-in theme.
- `materialx.emoji.*` and `material.extensions.*` python object references in YAML are
  regex-rewritten to `zensical.extensions.*` at load time, before the YAML tags resolve.

## `docs_dir` is walked, not gitignore-aware

Zensical's file discovery uses plain `walkdir` (confirmed in the Rust source, `Cargo.toml` has no
`ignore`-crate dependency) — it has no concept of `.gitignore`. Any non-content directory nested
inside `docs_dir` gets walked and built as if it were site content, warnings and all.

This bit us directly: `docs/reference/` (gitignored vendor-repo clones and PDFs — research material,
not site content) used to live inside `docs/`. It worked in CI only by accident — gitignored, so
absent from a clean checkout — but every _local_ `zensical build`/`serve` walked straight into
cloned repos like `gnome-shell` and either produced hundreds of broken-link warnings or hung
outright. Fixed by moving it to repo-root `reference/`, outside `docs_dir` entirely, 2026-08-08.
**Takeaway: never put anything under `docs_dir` that isn't meant to be a site page, even if it's
gitignored.** (That material has since moved again, out of this repo entirely, to a machine-wide
`$RESEARCH_HOME` shared across projects — see `contributing/research-library.md` — so this repo no
longer has a `reference/repos/` at all; the `docs_dir`-walking lesson still applies to anything
non-content placed under `docs/`.)

## `plugins:` — a small native allowlist, not the mkdocs plugin ecosystem

Zensical does not run arbitrary mkdocs plugins (no Python entry-point plugin lifecycle). It has
native, hardcoded support for exactly these plugin names (confirmed by reading
`_convert_plugins`/`_shim_*` in `config.py`): `search`, `offline`, `autorefs`, `mkdocstrings`,
`markdown-exec`, `glightbox`, `macros`. Anything else listed under `plugins:` is silently accepted
and does **nothing** — no error, no warning, just dead config. This is how we discovered `mermaid2`
(a leftover from the old `mkdocs-material` setup) had been inert since the zensical migration;
mermaid rendering was happening through an entirely different path (see below).

**Takeaway: if a plugin isn't in that list, don't bother adding it — check this list before assuming
a familiar mkdocs plugin will do anything under zensical.**

## `markdown_extensions:` replaces zensical's defaults, doesn't merge with them

Zensical ships a `DEFAULT_MARKDOWN_EXTENSIONS` dict with sensible defaults (`abbr`, `admonition`,
`md_in_html`, `pymdownx.betterem`, tabbed/tasklist with modern options, etc. — see
`zensical/config.py`), but only when a config **omits** `markdown_extensions:` entirely
(`config.get("markdown_extensions", DEFAULT_MARKDOWN_EXTENSIONS)` — plain dict `.get`, not a merge).
Since our `mkdocs.yml` declares the key explicitly, none of zensical's defaults apply for free;
everything wanted has to be listed. As of 2026-08-08 our file's extension list has been brought in
line with zensical's own default _values_ where they overlap (`pymdownx.tabbed` alternate style,
`pymdownx.tasklist` custom checkbox, `pymdownx.highlight` anchor/line-span options, added
`md_in_html` + `pymdownx.betterem`) — see git history on this file for the exact diff if checking
whether a newer zensical version's defaults have changed further.

## Mermaid

Zensical has genuine **native** mermaid support baked into the theme's JS bundle
(`assets/javascripts/bundle.*.min.js`): it lazy-loads a pinned `mermaid@11` from unpkg on demand
(only if a mermaid diagram is actually present on the page) and themes it via `--md-mermaid-*` CSS
custom properties that automatically track the site's light/dark palette. No plugin, no manual
`extra_javascript`, no manual `mermaid.initialize()` call needed — this part matches what
[zensical.org/docs/authoring/diagrams](https://zensical.org/docs/authoring/diagrams/) claims.

**What the hosted docs don't make obvious:** the auto-mount code only looks for
`<pre class="mermaid">` elements (confirmed by grepping the bundle for the literal selector string
`"pre.mermaid"`). It does **not** look for `<div class="mermaid">`. The old `mkdocs-material` +
`mermaid2`-plugin idiom (still floating around in a lot of copy-pasted `mkdocs.yml` files, including
ours until 2026-08-08) configures the fence as:

```yaml
pymdownx.superfences:
  custom_fences:
    - name: mermaid
      class: mermaid
      format: !!python/name:pymdownx.superfences.fence_div_format # <div> — wrong for zensical
```

which zensical's native mount point never finds. **The build succeeds with zero warnings either
way** — this fails completely silently. The only symptom is the diagram not rendering in a browser
(or, worse, rendering because a leftover manual `extra_javascript: unpkg.com/mermaid/...` script
happens to run mermaid's own legacy `startOnLoad` auto-scan — which is what was actually happening
here before the fix, and which used mermaid's _default light theme_, clashing visibly with our dark
site palette). The correct config for zensical:

```yaml
pymdownx.superfences:
  custom_fences:
    - name: mermaid
      class: mermaid
      format: !!python/name:pymdownx.superfences.fence_code_format # <pre> — what zensical mounts
```

This matches zensical's own `zensical new` bootstrap template. Verified end-to-end with headless
Chrome screenshots: broken (raw unrendered text) with the CDN script removed and no format fix,
wrong-theme (light-on-dark) with the old div-based config, correctly dark-themed with the fix.

**Takeaway: if you migrate an existing `mkdocs-material` + `mermaid2` config to zensical, you must
change `fence_div_format` → `fence_code_format`, or diagrams silently don't render and the build
gives no indication why.**

### Diagrams are mermaid, and nothing else

Decided 2026-09-02, when the docs-site usability pass added four diagrams to the one
`docs/python.md` already had: **no screenshots, no image files.** `docs/` contains none and that is
deliberate — an image goes stale silently while a mermaid block is text in the repo, reviewed and
diffed like everything else. The same answer closed the question of whether the statusline and the
prompt deserve a screenshot. The five diagrams as of that date are `cli-allowlist.md`'s pipeline,
`configuration.md`'s setup phase sequence, deploy classifier and shared-config-file walkthrough, and
`python.md`'s interpreter map; that last one is the house style for new ones.

### HTML in labels works, and stripping it was a mistake once

`<br/>`, `<b>` and `<small>` inside node and edge labels render under the theme's default
`securityLevel: "strict"`. A first pass believed strict mode escapes HTML and rewrote four diagrams
to plain single-line labels rather than check; the user pushed back and was right twice over:
`docs/python.md` had carried a published diagram using `<br/>` in both label kinds since 2026-08-24,
and the shipped bundle settles the mechanism — `sanitizeMore` runs `DOMPurify.sanitize` for
`strict`/`antiscript`/`sandbox`, which keeps those three tags, and even the escaping path
round-trips line breaks through a `#br#` placeholder precisely so `<br>` survives. The lesson is not
about mermaid: the safe-looking move was to avoid the uncertain construct, and it silently degraded
four diagrams on a belief one grep of the repo would have overturned.

### The CDN load is a view-time dependency the build never exercises

The theme bundle carries no mermaid; it fetches `https://unpkg.com/mermaid@11/dist/mermaid.min.js`
on finding a `pre.mermaid`. Two consequences. `zensical build --strict` passing says **nothing**
about whether a diagram renders — it can only tell you the fence was emitted. And a reader behind a
proxy that blocks unpkg — the corporate case this repo has a whole page about — sees the diagram
source as plain text. Not a defect of the diagrams, but the reason not to add a second such
dependency (an asciinema player from a CDN, say) and the reason the verification below exists.

### Verifying a diagram renders, without a human looking at the site

`google-chrome` is installed on this machine, so this needs no published site and no eyes:

- **In situ:** `inv docs.build`, then
  `google-chrome --headless=new --screenshot --virtual-time-budget=20000 file://…/site/<page>.html`.
  A real flowchart in the screenshot — nodes, edges, edge labels — proves the theme mounts
  `<pre class="mermaid">` for real, not merely that the element is present.
- **All blocks at once:** a throwaway harness page holding every `mermaid` fence extracted from
  `docs/*.md`, rendered with the same `mermaid@11` the theme loads. Every block should draw a
  diagram and none an error box. Keep a known-good diagram (`python.md`'s) in the set as the
  control: if the harness would hide a failure, the control cannot prove it would show one.

## No native math (MathJax/KaTeX) support

Unlike mermaid, there is no equivalent lazy-loader for `pymdownx.arithmatex` in the theme bundle —
grepped for `MathJax`/`katex`/`arithmatex`, zero hits. Even though `pymdownx.arithmatex` is part of
zensical's own `DEFAULT_MARKDOWN_EXTENSIONS`, using it still requires the site owner to manually
load MathJax or KaTeX via `extra_javascript`, exactly like the old mermaid2-era setup we just
removed. We have zero math content, so this wasn't added — re-evaluate if a future doc page needs
math notation, and expect to hand-roll the CDN script the same way mermaid used to be hand-rolled
pre-fix.

## `theme.features` — same key as Material, watch the typo

Standard Material-style `theme.features:` list (`content.code.copy`, `navigation.footer`, etc.)
works under zensical too, sourced from zensical's own bootstrap template. Historical footgun in this
repo specifically: the key was written as `feature:` (singular) inside a commented-out block for
years, across both the `mkdocs-material` era and the initial zensical migration — a silent no-op the
whole time, since neither engine recognizes a `feature:` key. Fixed 2026-08-08; current feature list
is in `mkdocs.yml`.

## `--strict` is aggressive, in a good way

`zensical build --strict` aborts on **any** warning — broken links, unresolved heading anchors,
unused link reference definitions. This is stricter than it sounds: it caught a genuinely dead link
in `docs/kubernetes.md` during the original mkdocs → zensical migration. Keep it in CI
(`.github/workflows/publish_on_push.yml` already does).

### Renaming a heading is an anchor change

The `unresolved heading anchor` half of that list is worth knowing about because a rename produces a
link that is wrong in a way nothing reads as wrong. `claude-code.md#some-heading` keeps a correct
path when the heading it points at is renamed — only the fragment goes stale — so `dprint` formats
the markdown without reading it as a document, `pytest` never renders a page, and a reviewer reads
the link as fine because it _is_ fine, at the path. The rename also lands in a different file from
the link, usually in a commit about something else.

It shipped a red deploy here twice, on `2a4de19` and `ae59318`: `docs/claude-code.md`'s
global-instructions heading was renamed in `e7b481e` while `docs/index.md` kept linking to the old
anchor, `CI` stayed green both times, and the published site quietly served the last good build.

**Two checks catch it now, and neither is a manual step any more.** Both run under
`inv quality.precommit`:

- **`inv docs.link-check` resolves the fragment**, not just the file, against the union of what
  python-markdown's `toc` extension and github.com would emit as a slug — the two sluggers a reader
  of this repo actually follows. It reports the nearest surviving anchor as a hint, and it walks
  **every tracked `.md`**, which is the coverage that matters: `--strict` only walks `docs_dir`
  (`mkdocs.yml` sets `docs_dir: docs`), so anchors written in `AGENTS.md`, `CONTRIBUTING.md`,
  `contributing/*.md` or `plans/*.md` are checked by this and by nothing else. Three such links
  existed when that was measured, all pointing into `docs/`, and all had to be verified by hand.
- **`zensical build --strict` is defence in depth behind it**, catching whatever a renderer objects
  to that a link checker cannot see. It sits in `quality.precommit`'s chain rather than
  `quality.check`'s, because `check` is the read-only half by construction and zensical offers no
  way to build without writing a site into the tree — `repo_tasks.quality.precommit`'s docstring
  carries that decision and the argument it beat.

Historical note for anyone reading an older session or plan: until 2026-09-04 `--strict` genuinely
was the only check that saw an anchor, and `docs.link-check` stripped the fragment by design. The
helper that does the resolving is `repo_tasks/docs.py`'s `_bad_link` — cited here only because it
was `_broken_link` in that same window, and a private helper's name is the least stable thing to
hang a citation on.

## Checklist for next time (re-verifying after a version bump)

**A bump is its own deliberate task, never something inherited.** The pin's job is that the gate, CI
and the deploy build with the _same_ version, which any single pin resolved from `uv.lock` gives —
`inv docs.build`, `ci.yml`'s `docs` job and `publish_on_push.yml` all read this one. **Which**
version it is, is separate. Zensical is early alpha and its versions demonstrably disagree about
what valid markdown is: a local 0.0.57 against CI's 0.0.44 disagreed about a `[certs]` table cell
being a link reference, and turned the deploy red on 2026-09-02. That is the whole reason there is a
pin. Versions also differ in speed by ~30%, so a bump moves gate latency too. It is much cheaper to
attempt than it was, because the docs build is in `quality.precommit` — a version that disagrees
about this repo's markdown now fails locally instead of failing the deploy — but it is still a
change to make on purpose and measure, not to drift into.

Re-run `zensical build --strict` at the repo root and re-check each of the above still holds,
particularly:

- [ ] Does `docs_dir` walking respect `.gitignore` yet? (would make the `reference/` move above
      obsolete, though there's no harm in leaving it as-is either way)
- [ ] Has the native plugin allowlist grown? (`_convert_plugins` / `_shim_*` in `config.py`)
- [ ] Does an explicit `markdown_extensions:` still fully replace the defaults instead of merging?
- [ ] Does the mermaid auto-mount still require `<pre class="mermaid">` specifically, or does it now
      also pick up `<div class="mermaid">`?
- [ ] Do the diagrams still render, and do HTML labels still survive? Re-run the headless-Chrome
      check above rather than trusting a green `--strict` build, which cannot see either.
- [ ] Has native math (MathJax/KaTeX) support been added to the bundle?
- [ ] Has `zensical.toml` stabilized enough to be worth migrating to from the `mkdocs.yml` compat
      path?
