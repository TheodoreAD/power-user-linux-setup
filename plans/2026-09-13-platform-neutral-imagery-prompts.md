---
status: idea
updated: 2026-09-13
---

# Image-generator prompts that show what PULSE does, not what it runs on

Asked for 2026-09-13: graphics based on the nature of power-user-linux-setup, **not centred on
Linux**. Held in this repo's store mirror rather than its `plans/` because a parallel session was
writing to the repo at the time. `plans.py absorb` offers it to the next session working there.

**Read it together with the repo's `plans/2026-09-02-project-imagery-prompts.md`.** Same subject,
different brief: that one is sci-fi or high fantasy with a grid of installed-tool marks, Linux
first. This one is the project's behaviour, with no platform in the lead.

[DECISION: **this is a third direction, C, beside that plan's sci-fi (A) and high fantasy (B), not a
replacement.** Decided 2026-09-13. At absorption it merges into that plan as direction C. Only its
mark ordering changes, and only for C (see "The installed-tool marks in direction C").]

A first pass at this brief ran earlier the same day in a `/btw` aside and produced six prompts; the
session was lost and only two survived, truncated — "the manifest becomes the machine" (hero, 21:9)
and "one pasted line" (hero, 16:9). This plan starts over rather than rebuilding from the fragments.
Prompts 1 and 2 below descend from those two.

## Context

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

### Constraints carried over from the 2026-09-02 plan

These hold for direction C exactly as for A and B:

- **No legible text in a generated image.** Real type is set in HTML/CSS or SVG, over space the
  prompt reserves.
- **Real marks are composited from official SVGs, never generated.**
- **Not cutesy:** a serious subject rendered precisely, with one deliberate oddity. **Not
  steampunk**, excluded explicitly in every prompt.

### Palette, measured rather than described

The docs site is `scheme: slate`, `primary: blue`, `accent: orange` (`mkdocs.yml`), rendered by the
zensical theme. Values read 2026-09-13 from the installed theme in `.venv`:
`zensical/templates/assets/stylesheets/{classic,modern}/palette.*.min.css`, with `--md-hue: 225deg`
from `main.*.min.css`. Blue and orange are identical in both variants. The slate values come from
`classic`.

| role                    | source value       | hex       |
| ----------------------- | ------------------ | --------- |
| page background         | `hsl(225,15%,14%)` | `#1e2129` |
| code / panel background | `hsl(225,15%,18%)` | `#272b35` |
| deepest (footer)        | `hsl(225,15%,8%)`  | `#111317` |
| primary                 | blue               | `#2094f3` |
| accent                  | orange             | `#ff9100` |

The hex values in the first three rows are converted from the HSL. `config/wezterm.lua` sets no
colour scheme, so the terminal has no palette to pull, contrary to what the 2026-09-02 plan assumed.
`config/p10k.zsh` colours are not checked. `mkdocs.yml` sets no logo or favicon (both are commented
out), so the mark in prompt 6 has a real, empty surface to fill.

[DECISION: **the accent is called "amber" in every prompt, never "orange" alone.** `#ff9100` sits on
the amber side. Ubuntu's brand orange is redder, and a model told "orange accent" on a terminal and
desktop subject drifts toward it. That puts one distro back in the centre of the image.]

[DECISION: **the "power user" clichés are excluded explicitly**: hooded figures, green code rain,
neon cyberpunk, RGB gaming lighting. The 2026-09-02 plan excluded steampunk for the same reason.
Models reach for these on the words "power user" and "terminal" without being asked, and every image
then looks like stock art.]

[DECISION: **no frame shows a recognisable operating system.** No window decorations belonging to
any one OS (traffic-light buttons, a taskbar, a top bar), no distro colours, no penguin. Windows in
the images are frameless rectangles.]

## The shared clause

Every prompt below ends with this, verbatim. That keeps the set consistent and keeps the excluded
defaults out:

> Colour palette: deep slate near-black background (#1e2129), panels slightly lighter (#272b35),
> cool blue structural lines (#2094f3), and a single warm amber accent (#ff9100) reserved for the
> one element that is changing. No text, no letters, no numbers, no logos, no trademarks. No
> penguin, no operating-system branding, no recognisable window decorations, no taskbars. No people,
> no hooded figures, no code rain, no neon cyberpunk, no RGB lighting. Not steampunk, no brass, no
> gears. No circuit-board traces, no glowing holographic interface, no lens flare, no cartoon
> mascots.

Models follow hex codes loosely. Treat them as a hint and grade each output to the palette
afterwards.

## The six prompts

Each prompt lists its surface and size, the concept it carries, and where real type goes. Each ends
with the shared clause above.

### 1. The manifest becomes the machine — docs hero, 21:9 (2520×1080)

Concept: one file decides what exists. Type: upper-left third.

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

### 1S. Slot variant of prompt 1 — the image the tool marks are composited into, 21:9

The 2026-09-02 plan's A5 and B5 exist for the same job. The composition is **straight-on rather than
isometric**, so flat official SVGs drop into the tiles without a perspective warp.

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

### 2. One line, and it asks first — alternative hero, 16:9 (1920×1080)

Concept: one pasted line starts everything, and nothing irreversible happens without a yes. Type:
upper right.

> Photorealistic close-up of a dark terminal filling a high-resolution display, shallow depth of
> field, camera slightly low and angled. Near the top, one short command line in sharp focus, its
> characters reduced to abstract glyph shapes rather than readable text, followed by a solid block
> cursor. Below it, a column of progress lines, each ending in a small blue tick, receding downward
> into soft bokeh. The last line in the column is different: it has stopped, and a single amber
> marker waits beside it for an answer. The screen is the only light source, spilling cool
> blue-white onto a matte dark desk and the edge of a low-profile keyboard, with one faint amber
> reflection from the waiting marker. The upper right of the frame falls away into darkness. _(+
> shared clause)_

### 3. Lose the machine, keep the setup — social preview, 2:1 (1280×640)

Concept: a hardware failure costs a machine, not a setup. This is the highest-payoff image, because
every link to the repo renders it. Type: left 45%. GitHub shows a custom preview with no text of its
own, so the repo name has to be composited in.

> Clean technical illustration, wide two-to-one frame, three-quarter view. In the right half, two
> different computers on one dark surface. Behind and to the left, an older laptop, powered off,
> rendered in dim desaturated slate, a hairline crack across its dark screen, on which the faint
> ghost of a layout of frameless panes is still visible. In front and to the right, a different,
> newer machine — a compact desktop with a monitor — powered on, its screen showing that exact same
> layout of panes, lit in cool blue. A single thin amber filament arcs from the dead laptop to the
> new screen and carries, at its midpoint, a small glowing document panel, the brightest object in
> the frame. The left 45 percent of the frame is empty dark slate with a very faint grid. Calm and
> precise rather than dramatic. _(+ shared clause)_

### 4. One manifest, four destinations — use-case card set, 4 × 1:1 (800×800 each)

Concept: the same manifest goes to every target, trimmed by tags. It replaces the Material icons on
the four front-page cards. Type: none, since the cards carry their titles in HTML. **Generate the
set as one sheet and slice it**, because four separate generations drift in angle, scale and
lighting.

> A single square image divided into a precise two-by-two grid of four equal tiles with thin gaps,
> the same isometric camera angle, lighting and scale in every tile. A thin blue filament enters
> each tile from its top edge and ends at one object; where it touches the object, the tip glows
> amber. Top left: a desk-scale workstation with two monitors, frameless panes on both screens. Top
> right: a bare rack-mounted server unit with no screen and one row of small status lights. Bottom
> left: a sealed geometric cube with a faint seam, the same workspace panes glowing through one
> translucent face. Bottom right: a large upright frameless window, inside which sits a smaller
> complete workspace — one machine hosted inside another. Matte flat surfaces, minimal, no
> background detail, generous margin in each tile. _(+ shared clause)_

### 5. Drift, shown and not overwritten — front-page image, 3:1 (2400×800)

Concept: `deploy.status` compares the home directory with the repo, shows what drifted, and asks
before overwriting. On the front page this stands for the promise that edits are never silently
overwritten. Type: none inside the image. It sits beside a sentence set in HTML.

> Precise technical illustration, wide three-to-one frame, slight isometric angle. Two layers of the
> same layout float one above the other, a small gap apart. The upper layer is a clean translucent
> blue blueprint of a workspace: panes, a small grid of settings tiles, a column of rows. The lower
> layer is the same layout built as solid slate objects. Every element lines up exactly through both
> layers except one small tile on the lower layer, which has shifted slightly off its outline and
> turned amber. A thin amber bracket links it to its outline above, pointing it out and waiting
> rather than pulling it back. Everything else is calm and aligned. Thin even line weights,
> vector-adjacent, subtle grid, generous margin on every side. _(+ shared clause)_

### 6. The mark — repo avatar and site favicon, 1:1, legible at 32px

Concept: a signal that builds something, without an "L" and without a heartbeat. Type: none.
**Generate this one only to explore ideas, then redraw the chosen mark as a hand-built SVG.** A
generated image will not be crisp at favicon size.

> A single bold emblem centred on a plain deep slate square. One thick horizontal line crosses the
> square; at its centre it rises into three small solid squares arranged as a precise ascending
> step, then drops back to the line. The line and the first two squares are cool blue, the top
> square amber. Flat vector, thick even strokes, no gradients, no outlines, no fine detail, generous
> margin, readable when reduced to thirty-two pixels. Not a heartbeat, not a medical symbol, no
> letters. _(+ shared clause)_

### Concepts not illustrated yet

Candidates if one of the six is dropped or a docs page asks for more: **installed means working** (a
grid of objects, each with a lit indicator, one mid-test), **the network preflight** (routes to
distant hosts checked before anything is fetched), and **a machine with rules for its agents**. The
last one is a front-page feature with no image at all, and it is the hardest to draw without falling
into robot clichés.

## The installed-tool marks in direction C

[DECISION: **the grid of official marks stays in direction C, reordered so cross-platform tools lead
and distro and desktop marks come last.** Decided 2026-09-13. The other option was dropping the grid
from C and keeping it only for the package catalog page. In a four-by-three grid read left to right,
the first row is **Python, Git, Docker, VS Code** and the second is **Claude Code, Rust, Go, Node**.
The platform marks (Ubuntu, GNOME) take the last positions of the third row. The exact twelve are
settled when the SVGs and their licence terms are collected, which the 2026-09-02 plan already puts
first. A and B keep their own ordering. The grid goes into prompt 1S.]

## Where prompt 5 goes

[DECISION: **prompt 5 goes on the front page, not on "How it works".** Decided 2026-09-13. On
`docs/configuration.md` it would repeat a diagram already there: the mermaid chart under "Install
never clobbers; redeploy is a separate, deliberate command" draws exactly the classification this
image shows. It would sit as a banner on a long reference page, pushing content down. That is the
mechanism-on-content-page case the 2026-09-02 plan left to mermaid. On the front page it is framing
for a promise the page currently makes only in prose and a "See also" link. Rejected: keeping it on
"How it works", swapping it for a candidate concept, and dropping it. The front page needs a
sentence beside it. The nearest existing one is Quick start's "`inv deploy.status` reports drift by
comparing your home directory to it"; a new bullet under "What you get, out of the box" is the
alternative. Choose between them when the image is placed.]

## Open questions

None open in this plan. Which generator to use, and whether its licence allows use on a public site,
is already an open question in the 2026-09-02 plan. It is not asked twice here, but it gates
publishing anything from this plan too.

## Recommended direction

1. **Absorb this plan into the repo and merge it into the 2026-09-02 plan as direction C** once the
   parallel session is out of the repo.
2. **Generate prompts 1 and 2 as a pair and keep one**, then 1S, with the marks composited in before
   judging it. The lost pass mixed isometric illustration with photoreal close-ups, and a set in two
   styles reads as two projects. Whichever hero survives sets the style for the other four images.
3. **Order by payoff**: social preview (3), then the hero (1 or 2), the card sheet (4), the mark (6)
   and the front-page drift image (5).
4. **Grade every output to the measured palette** before judging it against the others.
5. **Keep the settled prompts in the repo beside the images they produced**, as the 2026-09-02 plan
   already says. A prompt is the only way to regenerate or vary a committed image consistently.
