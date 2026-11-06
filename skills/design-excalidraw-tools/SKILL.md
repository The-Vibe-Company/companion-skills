---
name: design-excalidraw-tools
description: Design beautiful, readable Excalidraw diagrams of any kind — flows
  and processes, architectures, timelines and roadmaps, before/after
  comparisons, concept maps, layered stacks, posters with key figures,
  swimlanes, illustrated explainers — in six styles chosen from the request
  (corporate, editorial, hand-drawn sketch, playful pastel, dark,
  black-and-white), generated from a Python script, linted, rendered and looked
  at before delivery. Use this skill whenever someone asks for an Excalidraw
  diagram, a schéma, a canevas, a whiteboard-style drawing, a visual
  explanation, "make this diagram prettier / cleaner / less verbose", or any
  diagram they will show to someone, even if they never say "design" or
  "Excalidraw" but want a drawing in that style. Prefer it over hand-writing
  Excalidraw JSON. Not for slide decks, Mermaid in markdown, numeric charts, or
  UI mockups.
metadata: {}
---

<!-- skillpack:usage:start -->
## Skillpack runtime

Usage is observed locally by skillpack-runtime when installed through Skillpack. Package: f1567982-638a-46c1-9ab1-4379fa8eed44@0.3.0, origin: https://skillpack.app.
Do not send activation reports, run tracking commands, or install hooks during this skill's execution. Setup and updates belong to Skillpack. Continue the task when collection is unavailable. SKILLPACK_TELEMETRY=0 disables collection for this session.
<!-- skillpack:usage:end -->

# Design beautiful Excalidraw diagrams

A beautiful diagram is one people understand in thirty seconds and enjoy looking at: one clear message, a strong hierarchy, generous space, colour that means something, very few words, and nothing that fights for attention. Beauty here is mostly subtraction and alignment, not decoration.

Work in a short loop: **message → structure → generate → lint → render → look → refine.** Every diagram goes through a real render before you call it done, because text widths, overlaps and visual weight only show on the picture.

## 1. Find the message first

Before any coordinate, write two or three lines (in the generator's docstring is fine):

- **Who looks at it, where, and for how long** — a workshop wall, a link in Slack, a slide, a README.
- **The one thing they must remember.** Put it in the subtitle. Every element either supports it or goes.
- **The words to keep.** Use the user's own terms for steps, systems and roles. Do not rename them for clarity; explain an obscure term once in the legend instead.

If the user gave numbers, keep their unit and statistic attached (`2.1 working days, median`). Never invent figures to make a diagram look richer; an empty space is better than a made-up metric.

## 2. Pick the structure that fits the message

Read `references/recipes.md` and choose the diagram type whose shape matches the idea: a flow for "how things move", an architecture for "what talks to what", a timeline for "when", a comparison for "what changes", a hub for "what surrounds a concept", a stack for "what is built on what", a poster for "what we achieved", a dense process map for "how our whole delivery works, current or target" (workshop and steering material), an illustrated explainer for "how does it work?" told to a general audience (one drawing per step). Mixing types in one canvas is the most common reason a diagram feels messy; when two ideas compete, make two diagrams.

Read `references/design-principles.md` for the rules that make any of them look good: grid and spacing, hierarchy, typography, colour, arrows, density.

## 3. Choose a style

A style is the whole look: palette, clean or hand-drawn rendering, corner radius, and how colour is spent. The skill has six, defined in `assets/palettes.py` (`STYLES`) and described in `references/styles.md`. Pick one from the request and the audience, never mix two in one diagram, and remember that colour is not the default: most diagrams are better sober.

| Signal in the request or audience | Style |
|---|---|
| No signal; clients, management, slides, documentation | **corporate** (clean, cool greys, one violet accent) |
| Poster, report, article, one-page summary | **editorial** (grotesk type, square corners, hairline ink, cobalt accent) |
| Workshop, brainstorm, internal, "sketch", informal | **sketch** (hand-drawn on cream, pen lines, hachure, one terracotta accent) |
| General public, blog, onboarding, "friendly / fun / colourful" | **playful** (display titles, pastel per step or zone, yellow sticker, pictograms) |
| Dark slides, developer talk, dark mode | **night** (layered navy surfaces, monospace labels, cyan accent) |
| Print, black and white, "sober / minimal / no colour" | **mono** (ink and greys only, emphasis by weight and fill) |

When two fit, take the soberer one and offer the other in one line. When the user brings brand colours, keep the style and recolour its roles with `excalikit.set_palette`. Every example takes `--style <name>`; in your own generator call `palettes.setup(style="sketch")` before drawing and `S.header(title, message)` for the title block: the kit then applies the style's whole grammar (fonts, header, strokes, outlines, hachure, arched arrows, the loud element) to everything you draw. Use the spacing and type scales from `palettes.py` instead of ad-hoc numbers.

## 4. Generate with a script

Start from the closest example in `assets/` — `example_flow_tracks.py` (flow with tracks), `example_architecture.py`, `example_timeline.py`, `example_before_after.py`, `example_hub.py` (concept map), `example_stack.py` (layers), `example_poster.py` (key figures), `example_explainer.py` (illustrated), `example_process_map.py` (dense process map: lifecycle frame, two entrances, two tracks, a gate with its checklist, skill badges, inputs / outputs, tools per step, failure and improvement loops, who-does-what and open questions); each runs with `--out` and `--style` — and build with `scripts/excalikit.py`: primitives (text, rect, ellipse, line, arrow, chip) and components (node, group, card, labelled arrow, badge, stat tile, timeline, hero bar, rows, legend, cartouche, questions box). For explainers, `scripts/doodles.py` adds pictograms (bubble, page, magnifier, robot, person, database, cloud, answer with sources…), number badges, arched arrows and a hand underline: draw the thing each step talks about, it does more than any sentence. The kit estimates text widths and prints `OVERFLOW` warnings to stderr; fix each one. Keep every content change in the generator so the diagram can be regenerated after each round of feedback.

## 5. Lint, render, look

```bash
python scripts/lint_scene.py diagram.excalidraw
```

Lint catches text overflowing its box, overlapping texts, text crossing a box edge, shapes poking out of rounded corners, arrows landing in labels or across borders, low contrast, orphans, crowded boxes and colour sprawl; `--strict` adds near-misses, uneven rhythm and tight padding for the final pass. Then render locally with `node scripts/render_scene.mjs --in diagram.excalidraw --out diagram.png` (official Excalidraw export in headless Chromium, no account; `--crop x,y,w,h --scale 2` to zoom), or with Excalidraw+ through `scripts/excalidraw_plus.py` or the MCP `take_screenshot` (`references/excalidraw-plus.md`). `references/validation.md` gives the one-time setup, the order of checks and where to zoom.

Look at the render as a stranger would: where does the eye land first — is it the message? Is anything touching, cramped or floating? Is there an empty band or a corner nobody reads? Fix, regenerate, look again.

## 6. Refine with a cold eye when it matters

For a diagram that will be presented or published, ask one or two subagents for a cold critique (a 30-second reader and a demanding designer; add a fact-checker when there are numbers). Give them the render and a dump of the texts, not your opinion. Apply what converges, set aside with a reason what contradicts the user's choices or rewords their terms. Briefs are in `references/review-loop.md`.

When the diagram is for a client, a manager or a public audience, also read `references/audience-rules.md` (cartouche, provenance of numbers, tone, what to keep off the canvas).

## Output

Deliver the `.excalidraw` file, the generator script beside it, and the render (scene URL and/or PNG). Close with one or two sentences on what the diagram says and what you changed after looking at it.

## Protected invariants

- The render is checked before delivery; lint alone is not enough.
- One colour, one meaning, stated in a legend when colours carry meaning.
- The user's words for things are kept verbatim on the canvas.
- No invented numbers; every number carries its unit.
- Publishing goes to a new scene per version; deleting or sharing scenes only on explicit request (share links are public).

## References

- `references/styles.md` — the six styles, how to choose, colour moods (sober, pastel, mono).
- `references/design-principles.md` — grid, spacing, hierarchy, typography, colour, arrows, density, the beauty checklist.
- `references/recipes.md` — layouts for each diagram type and the kit calls that build them.
- `references/review-loop.md` — cold critique briefs and how to sort feedback.
- `references/validation.md` — order of checks, lint findings and fixes, local renderer setup, what to look at in thumbnail, at 100 % and zoomed.
- `references/audience-rules.md` — when the diagram leaves the team: cartouche, numbers, provenance, tone.
- `references/excalidraw-plus.md` — publishing, screenshots, HTTP fallback, pitfalls.
- `scripts/excalikit.py`, `scripts/doodles.py` (pictograms for explainers), `scripts/lint_scene.py`, `scripts/render_scene.mjs`, `scripts/excalidraw_plus.py`; `assets/palettes.py` (palettes, spacing and type scales); `assets/example_*.py` to copy.
