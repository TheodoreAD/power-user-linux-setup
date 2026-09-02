---
status: idea
updated: 2026-09-02
---

# Image-generator prompts for this project

Asked for 2026-09-02, alongside
[the front-page recording](2026-09-02-front-page-install-recording.md) and filed separately because
they are different work: that one is a build with tooling and a regeneration task, this one is
content.

**The brief, verbatim in its constraints:** technical, a little playful, **not cutesy**, either
**sci-fi or high fantasy**, and **no steampunk**.

## Context

`docs/` contains no image files at all — the docs review recorded that as finding 6, and the answer
so far has been mermaid diagrams, which are the house style for _mechanism_. That leaves everything
diagrams are bad at: the front-page hero, the social/OG card, the four use-case cards' currently
icon-only identity, and the repo's own avatar. Those want illustration, not schematics.

Two constraints the brief does not state but the project imposes:

- **The palette already exists.** The terminal, the Powerlevel10k prompt and the Claude Code
  statusline are a designed set, and the docs site has its own theme in `docs/extra/extra.css`.
  Imagery that ignores it will look bolted on. Pull the actual hex values from the deployed WezTerm
  and p10k config before generating, rather than describing colours in words.
- **Text in generated images is a liability.** Every current model still garbles small type, and
  this project's imagery would be full of plausible-looking command names. **Generate imagery with
  no legible text**, and set real type in HTML/CSS or SVG over it. Where a prompt below mentions
  glyphs, it asks for abstract or non-Latin marks for exactly this reason.

### Reading the brief

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

## Open questions

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
edges.** The four prompts per direction cover hero, social card, cards and avatar — all framing.
Illustrating the _content_ pages is a different question, and the docs review's answer there was
mermaid, deliberately. Assume framing only unless asked otherwise.]

## Recommended direction

Generate four comparison images first, at the real palette: A1 and B1 for the look, A5 and B5 for
the slot grid. **Composite the twelve official SVGs into A5 and B5 before judging either** — an
empty grid and a filled one are different pictures, and the filled one is what ships. Run A6 once
alongside them, to see the direct-generation failure rather than to use it.

Then build both directions out, in order of payoff: social card (every link to the repo renders it),
hero, avatar, card set.

**Collect the twelve SVGs and their licence terms as a first step, not a last one.** The mark set is
what the grid geometry has to suit — twelve marks of wildly different aspect ratios do not sit in
one square grid — and at least two (Tux, the Go gopher) carry attribution conditions that need a
credits line somewhere before anything is published.

Keep the chosen prompts in this repo once they are settled — a prompt that produced a committed
image is the only way that image can be regenerated or varied consistently later, and it belongs
beside the image the same way a generator belongs beside its output.
