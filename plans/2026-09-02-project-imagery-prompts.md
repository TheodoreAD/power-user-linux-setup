---
status: idea
updated: 2026-09-13
---

# Image-generator prompts for this project

Asked for 2026-09-02, alongside
[the front-page recording](2026-09-02-front-page-install-recording.md) and filed separately because
they are different work: that one is a build with tooling and a regeneration task, this one is
content.

**The first brief, verbatim in its constraints:** technical, a little playful, **not cutesy**,
either **sci-fi or high fantasy**, and **no steampunk**. It produces directions A and B below.

**A second brief, asked for 2026-09-13:** graphics based on the nature of the project, **not centred
on Linux**. It produces direction C, whose subject is what the project does rather than what it runs
on.

[DECISION: **direction C is a third direction beside A and B, not a replacement.** Decided
2026-09-13. Only its ordering of the installed-tool marks differs from the shared set, and only for
C — see "The installed-tool marks in direction C". A and B are unchanged by it.]

Direction C was drafted as its own plan while a parallel session held this repo, filed into the
store mirror rather than into `plans/`, and merged in here at absorption on 2026-09-13. Its unmerged
original is `plans/2026-09-13-platform-neutral-imagery-prompts.md` — the name to give
`plans.py archive` to read it back as it stood.

## Context

`docs/` contains no image files at all — the docs review recorded that as finding 6, and the answer
so far has been mermaid diagrams, which are the house style for _mechanism_. That leaves everything
diagrams are bad at: the front-page hero, the social/OG card, the four use-case cards' currently
icon-only identity, and the repo's own avatar. Those want illustration, not schematics.

Two constraints neither brief states but the project imposes:

- **The palette already exists**, and as of 2026-09-13 it is measured rather than described — see
  "Palette, measured rather than described" below. This plan first assumed the values would come
  from the deployed WezTerm and p10k config, because the terminal, the Powerlevel10k prompt and the
  Claude Code statusline are a designed set. `config/wezterm.lua` sets no colour scheme at all, so
  the terminal has no palette to pull and the docs site's own theme is the real source.
- **Text in generated images is a liability.** Every current model still garbles small type, and
  this project's imagery would be full of plausible-looking command names. **Generate imagery with
  no legible text**, and set real type in HTML/CSS or SVG over it. Where a prompt below mentions
  glyphs, it asks for abstract or non-Latin marks for exactly this reason.

### Reading the first brief

"Technical, a little playful, but not cutesy" is a narrow band and the failure mode is predictable:
prompts drift to mascots, rounded shapes, big eyes, isometric toy-town. The lever that holds the
line is **subject seriousness with execution wit** — a real mechanism, rendered precisely, with one
deliberate oddity — rather than asking for "fun", which every model reads as "cute".

"Sci-fi or high fantasy" are given as alternatives, so they are two directions to try rather than a
blend to average. They are kept separate below; a hybrid reads as neither.

[DECISION: **no steampunk means excluding it explicitly in every prompt, not merely omitting it.**
"Brass", "gears", "Victorian", "clockwork" and "riveted copper" are strong attractors for anything
described as both technical and fantastical, and models reach for them unprompted on exactly this
brief. Each prompt below carries a negative clause. Also excluded for the same reason: circuit-board
traces and glowing-blue-hologram-UI, which are the sci-fi equivalent — not asked against, but they
are the generic default and will make every image look like stock art.]

### Palette, measured rather than described

Measured 2026-09-13, for every direction. The docs site is `scheme: slate`, `primary: blue`,
`accent: orange` (`mkdocs.yml`), rendered by the zensical theme. Values read from the installed
theme in `.venv`: `zensical/templates/assets/stylesheets/{classic,modern}/palette.*.min.css`, with
`--md-hue: 225deg` from `main.*.min.css`. Blue and orange are identical in both variants. The slate
values come from `classic`.

| role                    | source value       | hex       |
| ----------------------- | ------------------ | --------- |
| page background         | `hsl(225,15%,14%)` | `#1e2129` |
| code / panel background | `hsl(225,15%,18%)` | `#272b35` |
| deepest (footer)        | `hsl(225,15%,8%)`  | `#111317` |
| primary                 | blue               | `#2094f3` |
| accent                  | orange             | `#ff9100` |

The hex values in the first three rows are converted from the HSL. `config/p10k.zsh` colours are not
checked. `mkdocs.yml` sets no logo or favicon (both are commented out), so the avatar and mark
prompts below (B4 and C6) have a real, empty surface to fill.

Models follow hex codes loosely. Treat them as a hint and grade each output to the palette
afterwards.

## The installed things have to be recognisable in the image

Asked for 2026-09-02, after the first draft: the imagery should carry the symbols of the popular
things this repo installs — Linux first, then Python, Claude Code, GNOME, Chrome, Rust, and the rest
of what has a well-known graphical representation.

That is the right instinct for the hero and the social card: "what do I actually get" is the front
page's weakest answer (finding 1 of the docs review), and a wall of recognisable marks answers it
before a word is read. The set, taken from `setup.toml` rather than from memory, in rough order of
recognisability: **Ubuntu/Linux, Python, Docker, Chrome, GNOME, Rust, Go, Node, Git, GitHub,
Kubernetes, Helm, Terraform, VS Code, JetBrains, Claude Code, tmux, zsh, WezTerm, gcloud.** Twenty
is already more than a composition can hold; twelve is a grid that reads.

Directions A and B keep that recognisability order. Direction C reorders the twelve for its own
grid, because leading with a distro mark is exactly what its brief rules out — see "The
installed-tool marks in direction C".

[DECISION: **the marks are composited from official SVGs, not drawn by the generator.** Two
independent reasons, and either alone settles it. **They come out wrong** — a model renders a known
logo the way it renders small type, at approximately the right shape with the proportions and the
wordmark mangled, which is the same failure the no-legible-text rule above already accounts for; a
nearly-right Python logo is more jarring than no logo. **And they are other people's marks** — Tux,
the Python logo, the GNOME foot, Chrome's circle, the Rust gear-ring, the Anthropic mark are each
governed by their owner's usage guidelines. Showing them to say "this is what gets installed" is
ordinary and expected; shipping a generated _approximation_ of someone's trademark is worse on every
axis than shipping the real file, which is downloadable, versioned and correct. So: generate the
scene with deliberate empty slots, composite the real SVGs in, and keep the attribution each licence
asks for (Tux and the Go gopher both carry one) in a credits line.]

This changes the prompts rather than replacing them: each direction below gets a **slot variant**
whose whole job is to produce a scene with a legible, evenly-lit grid of empty recesses at a known
position. A prompt that asks the model to draw the marks directly is given too, marked as such — not
because it is recommended, but because comparing the two is the fastest way to see the failure above
for yourself rather than taking it on trust.

## Direction A — sci-fi

The metaphor that fits the project: a machine being **provisioned from a manifest**. Declarative,
repeatable, one file deciding what exists.

**A1 — front-page hero.**

> A vast dim hangar interior, a single workstation deck at centre, seen from a low three-quarter
> angle. Above the deck, a machine is being assembled out of nothing by planes of light — flat
> geometric panels sliding into place along invisible rails, each one snapping to a grid. Half the
> machine is complete and solid; the other half is still wireframe, mid-materialisation. Cold
> instrument lighting, deep near-black background, one warm accent colour on the completed portion
> only. Precise hard-surface industrial design, matte machined surfaces, no ornament. Cinematic,
> restrained, wide aspect. No text, no lettering, no logos. Not steampunk, no brass, no gears, no
> exposed circuit-board traces, no glowing blue holographic UI panels, no lens flare.

**A2 — the manifest, as the thing that acts.**

> A single sheet of dark translucent material floating upright in a void, dense with faint engraved
> line-work in even columns — abstract marks, not readable letters. Beams project from the sheet
> downward and outward, and where each beam lands a small precise object has been built: a lamp, a
> tool, a folded terminal. Twelve objects, each different, arranged on an implied grid. The sheet is
> lit from within, the objects lit only by their beams. Cool monochrome with a single warm accent.
> Clean hard-surface rendering, high detail, shallow depth of field. No text, no legible symbols.
> Not steampunk, no gears, no parchment, no scrolls, no circuit traces.

**A3 — social / OG card, 1200×630.**

> Extreme close-up of a machined metal panel at a slight angle, filling the frame, with a single
> narrow channel cut across it. Inside the channel, a line of small indicator elements lights up in
> sequence from left to right, most already lit and a few still dark. Shallow angle, strong specular
> highlight along one edge, everything else falling into near-black. Industrial product-photography
> lighting, macro, very high detail. Composition leaves the left third empty and unlit for text to
> be placed later. No text, no numbers, no logos. Not steampunk, no brass, no rivets, no circuit
> board.

**A5 — slot variant of A1, the one to actually composite into.** The purpose of this prompt is a
clean grid of empty, evenly-lit recesses; the scene is secondary and must not compete.

> A vast dim hangar interior, low three-quarter angle, a dark machined bulkhead filling the centre
> of the frame. Set into the bulkhead, a precise grid of twelve identical square recesses, four
> across and three down, each one empty, each lit evenly from within by the same soft cold light,
> all at the same depth and the same scale. The grid is unobstructed and square to the camera.
> Around it the hangar falls away into deep near-black with one warm accent along a single
> structural edge. Matte machined surfaces, hard-surface industrial design, no ornament, no clutter
> in front of the grid. No text, no lettering, no symbols, no icons, no logos — the recesses must be
> completely empty. Not steampunk, no brass, no gears, no circuit traces, no glowing blue
> holographic UI, no lens flare.

**A6 — direct variant, for comparison only, not recommended.** Expect mangled marks; the value is
seeing how it fails.

> A dark machined bulkhead filling the frame, into which are set twelve softly backlit emblems in a
> four-by-three grid: a penguin, a two-coiled serpent, a whale carrying containers, a segmented
> colour wheel, a bare human footprint, a crab, a gopher, a hexagon, a ship's helm, a branching
> line, an angular monogram, a stylised terminal cursor. Each emblem is a flat single-colour inlay,
> evenly lit, none overlapping. Precise industrial hard-surface rendering, near-black surround, one
> warm accent. No text, no lettering, no wordmarks. Not steampunk, no gears, no circuit traces.

**A4 — the four use-case cards** (workstation / headless / container / WSL), as a consistent set.

> A set of four square icons in one consistent style: an isometric solid object on a plain
> near-black ground, each built from the same flat geometric panel language, each a different
> silhouette — a desk-scale terminal, a bare rack unit, a sealed cube, a cube nested inside a larger
> frame. Matte surfaces, one warm accent edge per object, no background detail, generous margin,
> identical lighting and camera angle across all four. Minimal, precise, no text, no
> icons-within-icons. Not steampunk, no gears, no glow effects.

## Direction B — high fantasy

The metaphor: a **workshop where the tools arrange themselves** — a bound compendium, and a room
that reads it. High fantasy read as craft and old precision, not as swords and dragons.

**B1 — front-page hero.**

> A stone workshop interior at night, tall and narrow, lit by one cold source high above. Along both
> walls, hundreds of tools and instruments hang in perfect ordered rows, each in its own outlined
> recess. In the centre, an open book rests on a plain lectern; from its pages a faint ordered light
> reaches out, and the recesses nearest it are filling — a tool forming in each, half-present. Deep
> shadow, one warm accent from the book, everything else cold grey stone. Painterly realism, muted
> palette, precise draughtsmanship, no clutter. No text, no readable writing on the pages. Not
> steampunk, no brass, no gears, no clockwork, no wizard, no robes, no dragons, no glowing runes as
> cliché neon.

**B2 — the compendium.**

> A heavy open book seen from directly above on a dark worn workbench, its two visible pages ruled
> into neat columns of small abstract marks. Laid across and around the book, arranged with obvious
> care, a set of real tools — calipers, a plane, a rule, a burin — each aligned to the grid of the
> page beneath it, as though the page had specified where each belongs. Single raking light from the
> left, deep shadows, aged paper, worn metal. Still-life realism, high detail, muted earth palette
> with one cold accent. No legible text, no letters, no numerals. Not steampunk, no gears, no
> goggles, no cogs, no magic sparkles.

**B5 — slot variant of B1, the one to actually composite into.** B1's tool-filled niches are the
scene; this one empties them so real marks can go in.

> A tall stone workshop wall at night, seen square-on and filling the frame. Cut into the stone, a
> precise grid of twelve identical shallow niches, four across and three down, each one empty, each
> lit by the same soft warm light from a source above and outside the frame. The stonework is fine
> and deliberate, the niches perfectly regular and all at the same depth. Below and around the grid,
> a plain worn workbench edge and deep shadow, no other objects. Painterly realism, muted cold grey
> stone with one warm accent, precise draughtsmanship. No text, no carved letters, no runes, no
> symbols, no icons — the niches must be completely empty. Not steampunk, no brass, no gears, no
> clockwork, no glowing magic.

**B3 — social / OG card, 1200×630.**

> A dark stone wall filling the frame, into which a long horizontal row of small identical niches
> has been cut with great precision. Most niches hold a small tool, perfectly placed; a few at the
> right are still empty. Raking side light from the left, strong shadows inside each niche, the
> right third of the frame falling into darkness with no detail, reserved for text. Painterly
> realism, cold grey with one warm accent on the filled niches. No text, no carved letters, no
> runes. Not steampunk, no brass, no gears.

**B4 — repo avatar, square, legible at 64px.**

> A single simple emblem centred on a plain dark ground: a stylised open book whose two pages
> resolve, at a glance, into a bracket-and-bracket shape. Extremely bold and simple, one warm accent
> colour on near-black, no gradients, no fine detail, readable when reduced to a tiny square. Flat
> vector look, thick even strokes, generous margin. No text, no letters. Not steampunk, no gears, no
> filigree.

## Direction C — what the project does, not what it runs on

Asked for 2026-09-13. The metaphor is the project's own behaviour: one file decides what exists, and
nothing it does is irreversible without a yes.

A first pass at this brief ran earlier the same day in a `/btw` aside and produced six prompts; the
session was lost and only two survived, truncated — "the manifest becomes the machine" (hero, 21:9)
and "one pasted line" (hero, 16:9). This direction starts over rather than rebuilding from the
fragments. C1 and C2 descend from those two.

### Why not Linux-centred

The repo supports that choice, it is not only a style preference:

- **Three of the four front-page use cases are not a Linux desktop**: headless server, dev
  container, WSL2 on Windows. `setup.toml` also has a `windows-native` tag for GUI apps installed on
  the Windows side of a WSL machine.
- `README.md`: "The intent is to be distribution-agnostic eventually".
- **What sets the project apart is not the OS.** One manifest decides what exists. Runs are safe to
  repeat. A deploy never overwrites what it cannot prove it wrote. It shows the diff and asks.
  `verify.all` checks each installed thing actually runs. A network preflight runs before the first
  download. The machine arrives with instructions and permission rules for its AI agents.
- **Distro imagery ages worst.** A penguin or a distro-orange hero becomes wrong the day a second
  platform lands.

### What the images have to say

Each concept is traced to where the repo implements it. The prompts illustrate these, not "a cool
terminal":

| concept                                         | where it lives                                         |
| ----------------------------------------------- | ------------------------------------------------------ |
| one file decides what exists                    | `setup.toml`                                           |
| lose the machine, not the setup                 | `README.md`: "minimize the impact of hardware failure" |
| one line starts it, and it asks before acting   | `install.sh`, which asks before `inv setup`            |
| one manifest, many destinations, by subtraction | tags, `PULSE_EXCLUDE_TAGS`                             |
| drift is shown, never silently overwritten      | `inv deploy.status`, `inv deploy.all`                  |
| installed means working                         | `inv verify.all`                                       |
| the parts are designed as a set                 | font → prompt icons → statusline, `docs/index.md`      |
| the machine comes with rules for its agents     | `config/agents-md/`, `cli-allowlist/`                  |

The shared constraints above hold for C exactly as for A and B: no legible text in a generated
image, real marks composited from official SVGs, a serious subject rendered precisely with one
deliberate oddity, and steampunk excluded explicitly rather than merely omitted.

[DECISION: **the accent is called "amber" in every prompt in this direction, never "orange" alone.**
`#ff9100` sits on the amber side. Ubuntu's brand orange is redder, and a model told "orange accent"
on a terminal and desktop subject drifts toward it. That puts one distro back in the centre of the
image.]

[DECISION: **the "power user" clichés are excluded explicitly**: hooded figures, green code rain,
neon cyberpunk, RGB gaming lighting. The first brief excluded steampunk for the same reason. Models
reach for these on the words "power user" and "terminal" without being asked, and every image then
looks like stock art.]

[DECISION: **no frame shows a recognisable operating system.** No window decorations belonging to
any one OS (traffic-light buttons, a taskbar, a top bar), no distro colours, no penguin. Windows in
the images are frameless rectangles.]

### The shared clause

Every C prompt ends with this, verbatim. That keeps the set consistent and keeps the excluded
defaults out:

> Colour palette: deep slate near-black background (#1e2129), panels slightly lighter (#272b35),
> cool blue structural lines (#2094f3), and a single warm amber accent (#ff9100) reserved for the
> one element that is changing. No text, no letters, no numbers, no logos, no trademarks. No
> penguin, no operating-system branding, no recognisable window decorations, no taskbars. No people,
> no hooded figures, no code rain, no neon cyberpunk, no RGB lighting. Not steampunk, no brass, no
> gears. No circuit-board traces, no glowing holographic interface, no lens flare, no cartoon
> mascots.

### The six C prompts

Each lists its surface and size, the concept it carries, and where real type goes. Each ends with
the shared clause above.

**C1 — the manifest becomes the machine; docs hero, 21:9 (2520×1080).** Concept: one file decides
what exists. Type: upper-left third.

> Precise isometric technical illustration, wide cinematic frame. In the lower left, a single
> upright document panel, softly edge-lit, its surface ruled with faint even rows of abstract marks
> that suggest structured configuration without being readable. From its right edge, many thin
> luminous filaments leave in orderly parallel bundles, split cleanly at small junction nodes, and
> resolve across the right two thirds of the frame into a complete workspace assembling itself:
> several frameless rectangular panes — a terminal, an editor, a browser, a file view — each sliding
> into place on an invisible grid. Most panes are already seated and calm in blue; the last one
> arriving glows amber at its edges. The filaments never cross or tangle. Subtle background grid,
> faint volumetric haze, thin consistent line weights, vector-adjacent rendering, generous empty
> space across the upper left third. _(+ shared clause)_

**C1S — slot variant of C1, the image the tool marks are composited into, 21:9.** A5 and B5 exist
for the same job in their own directions. The composition is **straight-on rather than isometric**,
so flat official SVGs drop into the tiles without a perspective warp.

> Precise technical illustration, wide cinematic frame, straight-on orthographic view with no
> perspective. In the lower left, a single upright document panel, softly edge-lit, ruled with faint
> even rows of abstract marks that suggest structured configuration without being readable. From its
> right edge, thin luminous blue filaments leave in orderly parallel bundles, split cleanly at small
> junction nodes, and each one ends at one of twelve identical square tiles arranged in a precise
> grid, four across and three down, filling the right half of the frame. Every tile is empty, the
> same size, evenly lit from within by the same soft light, with a thin blue border. The filament
> reaching the last tile, bottom right, glows amber. The grid is unobstructed and square to the
> frame. Subtle background grid, thin consistent line weights, vector-adjacent rendering, generous
> empty space across the upper left third. The tiles must be completely empty: no symbols, no icons.
> _(+ shared clause)_

**C2 — one line, and it asks first; alternative hero, 16:9 (1920×1080).** Concept: one pasted line
starts everything, and nothing irreversible happens without a yes. Type: upper right.

> Photorealistic close-up of a dark terminal filling a high-resolution display, shallow depth of
> field, camera slightly low and angled. Near the top, one short command line in sharp focus, its
> characters reduced to abstract glyph shapes rather than readable text, followed by a solid block
> cursor. Below it, a column of progress lines, each ending in a small blue tick, receding downward
> into soft bokeh. The last line in the column is different: it has stopped, and a single amber
> marker waits beside it for an answer. The screen is the only light source, spilling cool
> blue-white onto a matte dark desk and the edge of a low-profile keyboard, with one faint amber
> reflection from the waiting marker. The upper right of the frame falls away into darkness. _(+
> shared clause)_

**C3 — lose the machine, keep the setup; social preview, 2:1 (1280×640).** Concept: a hardware
failure costs a machine, not a setup. This is the highest-payoff image, because every link to the
repo renders it. Type: left 45%. GitHub shows a custom preview with no text of its own, so the repo
name has to be composited in.

> Clean technical illustration, wide two-to-one frame, three-quarter view. In the right half, two
> different computers on one dark surface. Behind and to the left, an older laptop, powered off,
> rendered in dim desaturated slate, a hairline crack across its dark screen, on which the faint
> ghost of a layout of frameless panes is still visible. In front and to the right, a different,
> newer machine — a compact desktop with a monitor — powered on, its screen showing that exact same
> layout of panes, lit in cool blue. A single thin amber filament arcs from the dead laptop to the
> new screen and carries, at its midpoint, a small glowing document panel, the brightest object in
> the frame. The left 45 percent of the frame is empty dark slate with a very faint grid. Calm and
> precise rather than dramatic. _(+ shared clause)_

**C4 — one manifest, four destinations; use-case card set, 4 × 1:1 (800×800 each).** Concept: the
same manifest goes to every target, trimmed by tags. It replaces the Material icons on the four
front-page cards, the same job A4 does for its own direction. Type: none, since the cards carry
their titles in HTML. **Generate the set as one sheet and slice it**, because four separate
generations drift in angle, scale and lighting.

> A single square image divided into a precise two-by-two grid of four equal tiles with thin gaps,
> the same isometric camera angle, lighting and scale in every tile. A thin blue filament enters
> each tile from its top edge and ends at one object; where it touches the object, the tip glows
> amber. Top left: a desk-scale workstation with two monitors, frameless panes on both screens. Top
> right: a bare rack-mounted server unit with no screen and one row of small status lights. Bottom
> left: a sealed geometric cube with a faint seam, the same workspace panes glowing through one
> translucent face. Bottom right: a large upright frameless window, inside which sits a smaller
> complete workspace — one machine hosted inside another. Matte flat surfaces, minimal, no
> background detail, generous margin in each tile. _(+ shared clause)_

**C5 — drift, shown and not overwritten; front-page image, 3:1 (2400×800).** Concept:
`deploy.status` compares the home directory with the repo, shows what drifted, and asks before
overwriting. On the front page this stands for the promise that edits are never silently
overwritten. Type: none inside the image. It sits beside a sentence set in HTML.

> Precise technical illustration, wide three-to-one frame, slight isometric angle. Two layers of the
> same layout float one above the other, a small gap apart. The upper layer is a clean translucent
> blue blueprint of a workspace: panes, a small grid of settings tiles, a column of rows. The lower
> layer is the same layout built as solid slate objects. Every element lines up exactly through both
> layers except one small tile on the lower layer, which has shifted slightly off its outline and
> turned amber. A thin amber bracket links it to its outline above, pointing it out and waiting
> rather than pulling it back. Everything else is calm and aligned. Thin even line weights,
> vector-adjacent, subtle grid, generous margin on every side. _(+ shared clause)_

**C6 — the mark; repo avatar and site favicon, 1:1, legible at 32px.** Concept: a signal that builds
something, without an "L" and without a heartbeat. Type: none. **Generate this one only to explore
ideas, then redraw the chosen mark as a hand-built SVG.** A generated image will not be crisp at
favicon size.

> A single bold emblem centred on a plain deep slate square. One thick horizontal line crosses the
> square; at its centre it rises into three small solid squares arranged as a precise ascending
> step, then drops back to the line. The line and the first two squares are cool blue, the top
> square amber. Flat vector, thick even strokes, no gradients, no outlines, no fine detail, generous
> margin, readable when reduced to thirty-two pixels. Not a heartbeat, not a medical symbol, no
> letters. _(+ shared clause)_

### The installed-tool marks in direction C

[DECISION: **the grid of official marks stays in direction C, reordered so cross-platform tools lead
and distro and desktop marks come last.** Decided 2026-09-13. The other option was dropping the grid
from C and keeping it only for the package catalog page. In a four-by-three grid read left to right,
the first row is **Python, Git, Docker, VS Code** and the second is **Claude Code, Rust, Go, Node**.
The platform marks (Ubuntu, GNOME) take the last positions of the third row. The exact twelve are
settled when the SVGs and their licence terms are collected, which is already the first step in
"Recommended direction" below. A and B keep the recognisability order. The grid goes into C1S.]

### Where C5 goes

[DECISION: **C5 goes on the front page, not on "How it works".** Decided 2026-09-13. On
`docs/configuration.md` it would repeat a diagram already there: the mermaid chart under "Install
never clobbers; redeploy is a separate, deliberate command" draws exactly the classification this
image shows. It would sit as a banner on a long reference page, pushing content down. That is the
mechanism-on-content-page case this plan otherwise leaves to mermaid. On the front page it is
framing for a promise the page currently makes only in prose and a "See also" link. Rejected:
keeping it on "How it works", swapping it for a candidate concept, and dropping it. The front page
needs a sentence beside it. The nearest existing one is Quick start's "`inv deploy.status` reports
drift by comparing your home directory to it"; a new bullet under "What you get, out of the box" is
the alternative. Choose between them when the image is placed.]

### Concepts C does not illustrate yet

Candidates if one of the six is dropped or a docs page asks for more: **installed means working** (a
grid of objects, each with a lit indicator, one mid-test), **the network preflight** (routes to
distant hosts checked before anything is fetched), and **a machine with rules for its agents**. The
last one is a front-page feature with no image at all, and it is the hardest to draw without falling
into robot clichés.

## Open questions

Both questions below gate every direction. Direction C added none of its own — it deliberately did
not re-ask the licence question, and it is gated by it exactly as A and B are.

[NEEDS CLARIFICATION: **whether the comparison set is now six images rather than four.** The
2026-09-02 decision below settled a four-image comparison — A1 and B1 for the look, A5 and B5 for
the slot grid — when there were two directions. C arrived with its own hero pair and its own slot
variant, and nothing has said whether all three directions get built out, or whether the three
heroes are compared and one wins. Raised by the 2026-09-13 merge, not by either brief.]

[DECISION: **generate both directions, decided 2026-09-02.** The proposal was to run one hero from
each and pick before building either out; the answer was to do both. So the comparison set is four
images rather than two — A1 and B1 for the look, A5 and B5 for the slot grid that actually ships —
and the choice is made with the compositing already visible rather than from the scene alone, which
is the better comparison anyway since the grid is the part the front page depends on.]

[NEEDS CLARIFICATION: **which model, and whether its licence permits this use.** The prompts are
written model-agnostically, but wording that works well differs between them, and — more importantly
— the output's licence and any attribution requirement have to be checked before an image goes into
a public repo. Not a formality: this is imagery for a published site.]

[NEEDS CLARIFICATION: **whether generated imagery is wanted on the docs pages at all, or only at the
edges.** The prompts in every direction cover hero, social card, cards and avatar — all framing.
Illustrating the _content_ pages is a different question, and the docs review's answer there was
mermaid, deliberately. Assume framing only unless asked otherwise.]

## Recommended direction

**Collect the twelve SVGs and their licence terms as a first step, not a last one.** The mark set is
what the grid geometry has to suit — twelve marks of wildly different aspect ratios do not sit in
one square grid — and at least two (Tux, the Go gopher) carry attribution conditions that need a
credits line somewhere before anything is published.

**Grade every output to the measured palette** before judging it against the others. That applies to
all three directions now the palette is a measurement rather than a description.

**A and B.** Generate four comparison images first, at the real palette: A1 and B1 for the look, A5
and B5 for the slot grid. **Composite the twelve official SVGs into A5 and B5 before judging
either** — an empty grid and a filled one are different pictures, and the filled one is what ships.
Run A6 once alongside them, to see the direct-generation failure rather than to use it. Then build
both directions out, in order of payoff: social card (every link to the repo renders it), hero,
avatar, card set.

**C.** Generate C1 and C2 as a pair and keep one, then C1S, with the marks composited in before
judging it. The lost first pass mixed isometric illustration with photoreal close-ups, and a set in
two styles reads as two projects. Whichever hero survives sets the style for the other four images.
Then order by payoff: social preview (C3), the hero (C1 or C2), the card sheet (C4), the mark (C6)
and the front-page drift image (C5).

Keep the chosen prompts in this repo once they are settled — a prompt that produced a committed
image is the only way that image can be regenerated or varied consistently later, and it belongs
beside the image the same way a generator belongs beside its output.
