"""excalikit — build clean Excalidraw scenes from Python.

Primitives: text, rect, ellipse, line, arrow, chip.
Generic components: node, group, connect, labelled_arrow, stat, edge_rect, timeline.
Small marks: step (numbered marker), dot (status dot + label), divider, callout (annotation with a leader line).
Flow and document components: card, out_chip, status_chip, badges, cartouche, legend, section_block, lane, hero_bar,
rows, questions_box.
Page: canvas() paints a full-bleed page colour behind everything (Excalidraw+ ignores viewBackgroundColor).
Theme: set_palette() recolours Palette and STATUS; every method reads the palette when it is called.

Usage (inside a generator script):

    import sys; sys.path.insert(0, "<skill>/scripts")
    from excalikit import Scene, Palette as P, text_size
    S = Scene()
    S.card(40, 200, 260, 180, "Triage", "PRODUCT OWNER", "sorts incoming requests", status="unchanged", out="ranked backlog")
    S.dump("diagram.excalidraw")

Only the Python standard library is used.

Geometry notes (why the components are layered the way they are):
- Rounded rectangles get an explicit corner radius (RADIUS). Excalidraw draws r = min(value, 0.25 * min(w, h)), so a
  radius can be lowered but never pushed past a quarter of the shortest side. corner_radius() returns the real value.
- Excalidraw has no clipping. A coloured edge or a header band that must follow rounded corners is built by layering
  shapes that share the same radius (see edge_rect, section_block, group), never by laying a square patch on a corner.
- Text widths come from per-glyph advance tables measured with Excalidraw's own text measurement (Nunito and
  Excalifont). Renderers draw the stored width as is (Excalidraw+ and the local renderer do not re-measure), so these
  estimates are what centres text, sizes chips and places badges: keep the tables accurate.
"""
import json
import random
import sys
import unicodedata

FONT_CLEAN = 6          # Nunito
FONT_HAND = 5           # Excalifont (hand-drawn variant)
LINE_HEIGHT = 1.25      # Excalidraw text box height = lines * size * LINE_HEIGHT

# spacing and shape tokens: use them instead of magic numbers so every component breathes the same way
PAD = 16                # inner padding of cards, tiles and rows (text and chips sit on this inset)
GAP = 8                 # gap between stacked items inside a component (lines, chip rows)
ARROW_GAP = 6           # gap between an arrow tip (or tail) and the border of the box it touches
LABEL_GAP = 8           # gap between a label and the line it annotates
RADIUS = 12             # corner radius of rounded rectangles; None = Excalidraw's adaptive default (up to 32)
CHIP_PX, CHIP_PY = 11, 4  # chip padding around its text
EDGE = 8                # width of the coloured left edge of stat tiles and rows
CANVAS_MARGIN = 64      # margin of the painted page around the drawing (canvas())


class Palette:
    INK, MID, GREY, LINE, PAPER, STONE, WHITE = "#212529", "#495057", "#868e96", "#dee2e6", "#f8f9fa", "#adb5bd", "#ffffff"
    ACCENT, ACCENT_BG, ACCENT_SOFT = "#5f3dc4", "#f3f0ff", "#d0bfff"        # what you propose
    TEAL, TEAL_BG, TEAL_SOFT = "#0c8599", "#e3fafc", "#99e9f2"
    BLUE, BLUE_BG, BLUE_SOFT = "#1971c2", "#e7f5ff", "#a5d8ff"
    GREEN, GREEN_BG, GREEN_SOFT = "#2b8a3e", "#ebfbee", "#b2f2bb"            # targets, improvement loops
    ORANGE, ORANGE_BG, ORANGE_SOFT = "#e8590c", "#fff4e6", "#ffd8a8"         # waiting time, in progress
    RED, RED_BG, RED_SOFT = "#e03131", "#fff5f5", "#ffc9c9"                  # problems, KO paths, what disappears
    YELLOW, YELLOW_BG, YELLOW_TXT = "#fab005", "#fff9db", "#8a6d00"          # open questions
    LANE = "#f1f3f5"
    ON_DARK = "#ced4da"                                                      # secondary text on INK
    CANVAS = "#ffffff"                                                       # page colour (dump, canvas)


P = Palette


def _c(value, attr):
    """Colour argument resolved at call time: None means the current Palette value."""
    return getattr(Palette, attr) if value is None else value


# Legacy average glyph widths (kept for scripts that import it; text_size now uses the per-glyph tables below).
CHAR_W = {11: 6.2, 12: 6.7, 13: 7.2, 13.5: 7.5, 14: 7.8, 15: 8.4, 16: 8.9, 17: 9.5, 18: 10.0, 19: 10.6, 20: 11.2,
          21: 11.8, 22: 12.3, 24: 13.4, 28: 15.6, 30: 16.8, 34: 19.0, 36: 20.0, 38: 21.2}
# Extra safety factor on estimated widths. The glyph tables cover both fonts, so hand_drawn() resets it to 1.0;
# raise it only to keep extra slack in overflow checks.
WIDEN = 1.0

# Advance widths in thousandths of an em, measured through Excalidraw's own text measurement.
_GLYPH_CHARS = (" !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~"
                "→←↑↓·×éèàçêâîôûù’‘“”–—…€°✓✗•")
_NUNITO_EM = (
    261, 233, 405, 600, 600, 933, 701, 226, 326, 326, 451, 600, 233, 427, 233, 290, 600, 600, 600, 600, 600, 600,
    600, 600, 600, 600, 233, 233, 600, 600, 600, 447, 947, 733, 679, 675, 747, 586, 551, 729, 764, 262, 331, 634,
    548, 858, 741, 771, 637, 771, 673, 618, 607, 731, 694, 1104, 655, 601, 593, 324, 290, 324, 600, 500, 361, 533,
    587, 465, 587, 534, 340, 590, 572, 237, 241, 508, 301, 861, 572, 560, 587, 587, 365, 483, 358, 565, 518, 844,
    530, 517, 466, 361, 270, 361, 600, 1000, 1000, 500, 500, 233, 600, 534, 534, 533, 465, 534, 533, 237, 560, 565,
    565, 233, 233, 405, 405, 500, 1000, 700, 600, 373, 600, 600, 524)
_EXCALIFONT_EM = (
    400, 314, 371, 783, 721, 928, 718, 218, 441, 402, 525, 550, 257, 411, 274, 561, 664, 427, 700, 608, 585, 618,
    640, 558, 636, 629, 264, 298, 550, 550, 550, 466, 829, 676, 761, 629, 780, 707, 661, 780, 573, 545, 569, 613,
    543, 766, 632, 767, 698, 768, 736, 622, 857, 730, 592, 786, 628, 564, 832, 472, 589, 497, 510, 670, 600, 576,
    555, 504, 605, 537, 497, 555, 567, 244, 328, 533, 225, 663, 526, 600, 537, 539, 412, 543, 553, 548, 525, 693,
    591, 530, 572, 504, 299, 544, 669, 1000, 1000, 500, 500, 200, 550, 551, 551, 542, 504, 551, 542, 244, 561, 508,
    508, 304, 267, 412, 428, 702, 935, 709, 713, 412, 600, 600, 522)
GLYPH_EM = {FONT_CLEAN: dict(zip(_GLYPH_CHARS, _NUNITO_EM)), FONT_HAND: dict(zip(_GLYPH_CHARS, _EXCALIFONT_EM))}
# vertical metrics (ascender, descender) in em, used to centre glyphs optically in their line box
FONT_METRICS = {FONT_CLEAN: (1.011, -0.353), FONT_HAND: (0.886, -0.374)}
_current_font = [FONT_CLEAN]

_STATUS_ROLES = {"done": ("GREEN_BG", "GREEN_SOFT", "GREEN"), "progress": ("ORANGE_BG", "ORANGE_SOFT", "ORANGE"),
                 "build": ("WHITE", "STONE", "INK"), "unchanged": ("PAPER", "LINE", "GREY")}
STATUS = {               # key: (label, fill, stroke, text) — neutral so the accent keeps one meaning
    "done": ("delivered", Palette.GREEN_BG, Palette.GREEN_SOFT, Palette.GREEN),
    "progress": ("in progress", Palette.ORANGE_BG, Palette.ORANGE_SOFT, Palette.ORANGE),
    "build": ("to build", Palette.WHITE, Palette.STONE, Palette.INK),
    "unchanged": ("unchanged", Palette.PAPER, Palette.LINE, Palette.GREY),
}

# semantic role names accepted by set_palette(), mapped onto the Palette attributes they drive
_ROLE_ATTR = {"bad": "RED", "good": "GREEN", "wait": "ORANGE", "open": "YELLOW", "cat1": "BLUE", "cat2": "TEAL"}


def set_palette(colours):
    """Recolour the kit in place. `colours` maps Palette attribute names (INK, ACCENT_BG, ...; any case) or role
    names (bad, good_bg, wait_soft, open_txt, cat1, cat2_bg, canvas, on_dark, ...) to colours. Unknown keys are
    ignored. STATUS colours follow. Methods read Palette when called, so call this before building the scene.
    Returns the list of attributes changed."""
    changed = []
    for key, val in colours.items():
        k = key.lower()
        base, _, suffix = k.partition("_")
        if base in _ROLE_ATTR:
            attr = _ROLE_ATTR[base] + ("_" + suffix.upper() if suffix else "")
        else:
            attr = k.upper()
        if hasattr(Palette, attr) and attr.isupper():
            setattr(Palette, attr, val)
            changed.append(attr)
    for k, roles in _STATUS_ROLES.items():
        if k in STATUS:
            STATUS[k] = (STATUS[k][0],) + tuple(getattr(Palette, r) for r in roles)
    return changed


def _glyph_em(c, table):
    if c in table:
        return table[c] / 1000
    if unicodedata.combining(c):
        return 0.0
    if unicodedata.east_asian_width(c) in ("W", "F"):
        return 1.0
    return 0.56


def text_size(text, size, font=None):
    """(width, height) of a text element as Excalidraw measures it. font defaults to the font of the scene being
    built (Nunito, or Excalifont after hand_drawn())."""
    table = GLYPH_EM.get(font or _current_font[0], GLYPH_EM[FONT_CLEAN])
    lines = text.split("\n")
    w = max(sum(_glyph_em(c, table) for c in l) for l in lines) * size * WIDEN
    return w, len(lines) * size * LINE_HEIGHT


def corner_radius(w, h, radius=None):
    """Corner radius Excalidraw actually draws for a rounded rectangle of this size (radius None = RADIUS)."""
    v = RADIUS if radius is None else radius
    m = min(w, h)
    if v is None:
        v = 32
    return m * 0.25 if m <= v * 4 else v


def warn(msg):
    print(msg, file=sys.stderr)


def _bounds(e):
    pts = e.get("points")
    if pts:
        xs = [e["x"] + p[0] for p in pts]
        ys = [e["y"] + p[1] for p in pts]
        return min(xs), min(ys), max(xs), max(ys)
    return e["x"], e["y"], e["x"] + e["width"], e["y"] + e["height"]


class Scene:
    def __init__(self, seed=7, font=FONT_CLEAN, roughness=0):
        self.els = []
        self._n = 0
        self.font = font
        self.roughness = roughness
        self.rng = random.Random(seed)
        self._canvas = None
        _current_font[0] = font

    # ------------------------------------------------------------ primitives
    def _id(self):
        self._n += 1
        return f"e{self._n:04d}"

    def _ts(self, s, size):
        return text_size(s, size, self.font)

    def _seed(self):
        return self.rng.randint(1, 2 ** 31)

    def _base(self, t, x, y, w, h, **kw):
        e = {"id": self._id(), "type": t, "x": x, "y": y, "width": w, "height": h, "angle": 0,
             "strokeColor": Palette.INK, "backgroundColor": "transparent", "fillStyle": "solid", "strokeWidth": 2,
             "strokeStyle": "solid", "roughness": 0 if t == "text" else self.roughness, "opacity": 100,
             "groupIds": [], "frameId": None, "roundness": None, "seed": self._seed(),
             "version": 1, "versionNonce": self._seed(), "isDeleted": False,
             "boundElements": None, "updated": 1, "link": None, "locked": False}
        e.update(kw)
        self.els.append(e)
        return e

    def _baseline(self, size):
        """Distance from the top of a text box to the baseline of its first line (Excalidraw centres the font's
        ascender + descender in the line box)."""
        asc, desc = FONT_METRICS.get(self.font, FONT_METRICS[FONT_CLEAN])
        return size * LINE_HEIGHT / 2 + (asc + desc) / 2 * size

    def _optical_dy(self, size):
        """Offset that moves a line box so that capitals and digits sit on its geometric centre."""
        cap = 0.7 if self.font == FONT_CLEAN else 0.62
        return size * LINE_HEIGHT / 2 - (self._baseline(size) - cap * size / 2)

    def text(self, x, y, s, size=14, color=None, align="left", width=None):
        color = _c(color, "MID")
        w, h = self._ts(s, size)
        w = width or w
        if align == "center":
            x -= w / 2
        elif align == "right":
            x -= w
        return self._base("text", x, y, w, h, text=s, originalText=s, fontSize=size, fontFamily=self.font,
                          textAlign=align, verticalAlign="top", containerId=None, lineHeight=LINE_HEIGHT,
                          strokeColor=color, autoResize=True, strokeWidth=1)

    def text_mid(self, x, cy, s, size=14, color=None, align="left"):
        """Text whose capitals are optically centred on the horizontal line cy (for chips, bars, badges)."""
        h = self._ts(s, size)[1]
        return self.text(x, cy - h / 2 + self._optical_dy(size), s, size, color, align)

    def rect(self, x, y, w, h, fill=None, stroke=None, sw=2, style="solid", rounded=True, radius=None, seed=None):
        """Rectangle; rounded ones use RADIUS (or `radius`), capped by Excalidraw at a quarter of the shortest side.
        fill / stroke default to PAPER / LINE."""
        v = RADIUS if radius is None else radius
        rnd = None if not rounded else ({"type": 3} if v is None else {"type": 3, "value": v})
        e = self._base("rectangle", x, y, w, h, backgroundColor=_c(fill, "PAPER"), strokeColor=_c(stroke, "LINE"),
                       strokeWidth=sw, strokeStyle=style, roundness=rnd)
        if seed is not None:
            e["seed"] = seed
        return e

    def ellipse(self, x, y, w, h, fill=None, stroke=None, sw=2):
        return self._base("ellipse", x, y, w, h, backgroundColor=_c(fill, "WHITE"), strokeColor=_c(stroke, "INK"),
                          strokeWidth=sw)

    def line(self, x, y, pts, color=None, sw=2, style="solid"):
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        return self._base("line", x, y, max(xs) - min(xs), max(ys) - min(ys), points=pts, strokeColor=_c(color, "MID"),
                          strokeWidth=sw, strokeStyle=style, startBinding=None, endBinding=None,
                          startArrowhead=None, endArrowhead=None, lastCommittedPoint=None)

    def arrow(self, x1, y1, x2, y2, color=None, sw=3, style="solid", via=None):
        """Straight or elbowed arrow (via = list of absolute (x, y) corners); elbows stay square. Callers leave
        ARROW_GAP between the tip and the box it points at (connect() does it for you)."""
        pts = [[0, 0]] + [[px - x1, py - y1] for px, py in (via or [])] + [[x2 - x1, y2 - y1]]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        return self._base("arrow", x1, y1, max(xs) - min(xs), max(ys) - min(ys), points=pts,
                          strokeColor=_c(color, "INK"), strokeWidth=sw, strokeStyle=style, startBinding=None,
                          endBinding=None, startArrowhead=None, endArrowhead="arrow", lastCommittedPoint=None,
                          elbowed=False, roundness=None)

    def chip(self, x, y, s, fill=None, stroke=None, color=None, size=12, style="solid"):
        """Pill with text (defaults PAPER / STONE / INK); returns its width. Its height is chip_height(size)."""
        w, h = self._ts(s, size)
        ch = h + 2 * CHIP_PY
        self.rect(x, y, w + 2 * CHIP_PX, ch, _c(fill, "PAPER"), _c(stroke, "STONE"), 1, style)
        self.text_mid(x + CHIP_PX, y + ch / 2, s, size, _c(color, "INK"))
        return w + 2 * CHIP_PX

    def chip_height(self, size=12):
        return self._ts("X", size)[1] + 2 * CHIP_PY

    # ------------------------------------------------------------ page
    def canvas(self, colour=None, margin=CANVAS_MARGIN):
        """Paint a full-bleed page colour (default Palette.CANVAS) behind everything, `margin` px around the
        drawing. Excalidraw+ screenshots ignore the file's viewBackgroundColor, so warm and ink palettes need this.
        The rectangle is computed and put underneath at dump() time; call canvas() anywhere."""
        self._canvas = (colour, margin)

    # ------------------------------------------------------------ layered shapes (rounded corners done right)
    def _rounded_outline(self, x, y, w, h, r, x_from, color, sw, style="solid"):
        """Open path tracing the top, right and bottom sides of a rounded rectangle, from x_from on the top edge
        round to x_from on the bottom edge. Corners follow Excalidraw's quadratic curves exactly."""
        def quad(p0, c, p2, n=16):
            return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p2[0],
                     (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p2[1])
                    for t in (i / n for i in range(1, n + 1))]
        pts = [(x_from, y), (x + w - r, y)]
        pts += quad((x + w - r, y), (x + w, y), (x + w, y + r))
        pts += [(x + w, y + h - r)]
        pts += quad((x + w, y + h - r), (x + w, y + h), (x + w - r, y + h))
        pts += [(x_from, y + h)]
        return self.line(x_from, y, [[px - x_from, py - y] for px, py in pts], color, sw, style)

    def edge_rect(self, x, y, w, h, color, edge=EDGE, fill=None, stroke=None, sw=2, radius=None):
        """Rounded box whose left edge is a coloured band that follows the rounded corners (like a CSS
        border-left). Three layers: the full box in the edge colour, the face (fill, default WHITE) inset by `edge`
        on the left with the same height and radius, then the border (stroke, default LINE) on the top, right and
        bottom sides only. Both boxes span the full height, so text inside always sits in the face box.
        Returns the box (x, y, w, h)."""
        fill, stroke = _c(fill, "WHITE"), _c(stroke, "LINE")
        r = corner_radius(w, h, radius)
        seed = self._seed()
        # fills stay crisp (also in the hand-drawn look) and carry no stroke, so nothing peeks out from under the
        # border, and no accent stroke sits under the grey corners where anti-aliasing could tint them
        sil = self.rect(x, y, w, h, color, "transparent", 1, radius=r, seed=seed)
        face = self.rect(x + edge, y, w - edge, h, fill, "transparent", 1, radius=r, seed=seed)
        sil["roughness"] = face["roughness"] = 0
        self._rounded_outline(x, y, w, h, r, x + edge + r, stroke, sw)
        return (x, y, w, h)

    def _banded(self, x, y, w, h, band_h, band, fill, stroke, sw, style="solid"):
        """Container with a coloured header band whose top corners match the container's exactly: the band has
        the container's radius, a square patch squares its bottom edge, and the border goes back on top when the
        band colour differs. In the hand-drawn look the fills stay crisp and a single rough border is drawn last,
        so the band never pokes past a wobbling outline."""
        r = corner_radius(w, h, min(RADIUS or 32, band_h / 4))
        if not self.roughness:
            seed = self._seed()
            self.rect(x, y, w, h, fill, stroke, sw, style, radius=r, seed=seed)
            self.rect(x, y, w, band_h, band, band, sw, radius=r)
            self.rect(x, y + band_h - r - 1, w, r + 1, band, band, sw, rounded=False)   # squares the band's bottom
            if band != stroke or style != "solid":
                self.rect(x, y, w, h, "transparent", stroke, sw, style, radius=r, seed=seed)  # border back on top
            return r
        for e in (self.rect(x, y, w, h, fill, "transparent", 1, radius=r),       # crisp fills, no stroke
                  self.rect(x, y, w, band_h, band, "transparent", 1, radius=r),
                  self.rect(x, y + band_h - r - 1, w, r + 1, band, "transparent", 1, rounded=False)):
            e["roughness"] = 0
        self.rect(x, y, w, h, "transparent", stroke, sw, style, radius=r)
        return r

    # ------------------------------------------------------------ components
    def status_chip(self, x_right, y, key):
        lab, bg, bd, tx = STATUS[key]
        w = self._ts(lab, 12)[0] + 2 * CHIP_PX
        self.chip(x_right - w, y, lab, bg, bd, tx, 12)
        return w

    def out_chip(self, x, y, s):
        """The piece a step produces (= input of the next step)."""
        return self.chip(x, y, "→ " + s, Palette.WHITE, Palette.STONE, Palette.MID, 12, "dashed")

    def badges(self, x_right, y, letters, proposed=()):
        """Letter badges straddling a card's top edge, clear of its rounded corner; letters in `proposed` use the
        accent colour. A white ring cuts the border cleanly where a badge sits on it."""
        d = 32                                  # > 30 px so linters treat the disc as the letter's container
        for i, l in enumerate(letters):
            cx = x_right - PAD - d / 2 - i * (d + GAP)
            col = Palette.ACCENT if l in proposed else Palette.INK
            self.ellipse(cx - d / 2, y - d / 2, d, d, col, Palette.WHITE, 2)
            self.text_mid(cx, y, l, 15, Palette.WHITE, align="center")

    def card(self, x, y, w, h, title, actor=None, body=None, *, status=None, out=None, out_high=False, note=None,
             skills="", proposed_skills=(), stroke=None, fill=None, sw=2, style="solid", tcolor=None, bcolor=None,
             tsize=19):
        """Title (+ actor line) + body; status bottom-right; output chip bottom-left (or one row higher with
        out_high when the status chip leaves no room); grey note above the bottom row; skill badges on the corner.
        Everything sits on the PAD inset, so chips align with the text column. Defaults: stroke LINE, fill WHITE,
        title INK, body MID."""
        self.rect(x, y, w, h, _c(fill, "WHITE"), _c(stroke, "LINE"), sw, style)
        self.text(x + PAD, y + PAD, title, tsize, _c(tcolor, "INK"))
        ty = y + PAD + self._ts(title, tsize)[1] + 6
        if actor:
            self.text(x + PAD, ty, actor, 12, Palette.MID)
            ty += 22
        if body:
            self.text(x + PAD, ty, body, 14, _c(bcolor, "MID"))
            ty += self._ts(body, 14)[1]
        ch = self.chip_height(12)
        row_y = y + h - PAD - ch
        floor = row_y - GAP if (status or (out and not out_high)) else y + h - 12
        if status:
            self.status_chip(x + w - PAD, row_y, status)
        if out:
            oy = row_y - (ch + GAP if out_high else 0)
            ow = self.out_chip(x + PAD, oy, out)
            if not out_high and status and ow + self._ts(STATUS[status][0], 12)[0] + 2 * CHIP_PX + 2 * PAD > w:
                warn(f"OUT CHIP TOO WIDE in '{title[:30]}': use out_high=True or a shorter output")
            floor = min(floor, oy - GAP)
        if note:
            nh = self._ts(note, 13)[1]
            self.text(x + PAD, floor - nh, note, 13, Palette.GREY)
            floor -= nh + GAP
        if ty > floor:
            warn(f"OVERFLOW in card '{title[:30]}': content ends at {ty - y:.0f}, room until {floor - y:.0f}")
        for line in ((title, tsize), (body or "", 14)):
            if line[0] and self._ts(line[0], line[1])[0] > w - 2 * PAD:
                warn(f"OVERFLOW (width) in card '{title[:30]}': '{line[0].splitlines()[0][:30]}…'")
        if skills:
            self.badges(x + w, y, skills, proposed_skills)
        return ty

    def cartouche(self, x, y, headline, subject, footnote, w=460):
        """Who presents to whom. Light, so it never outweighs the diagram."""
        self.rect(x, y, w, 96, Palette.PAPER, Palette.STONE, 2)
        self.text(x + 20, y + 14, headline, 17, Palette.INK)
        self.text(x + 20, y + 44, subject, 13, Palette.MID)
        self.text(x + 20, y + 66, footnote, 13, Palette.MID)

    def legend(self, x, y, items):
        """items: list of (kind, label, colour) with kind in 'box', 'fill', 'dashed', 'arrow', 'dot', 'text'."""
        cx = x
        for kind, label, col in items:
            if kind == "box":
                self.rect(cx, y, 22, 22, Palette.WHITE, col, 2)
            elif kind == "fill":
                self.rect(cx, y, 22, 22, col, col, 2)
            elif kind == "dashed":
                self.rect(cx, y, 22, 22, Palette.WHITE, col, 2, "dashed")
            elif kind == "arrow":
                self.arrow(cx, y + 11, cx + 24, y + 11, col, 2)
            elif kind == "dot":
                self.ellipse(cx + 6, y + 6, 10, 10, col, col, 1)
            off = 0 if kind == "text" else 32
            self.text_mid(cx + off, y + 11, label, 13, col if kind == "text" else Palette.INK)
            cx += off + self._ts(label, 13)[0] + 26

    def section_block(self, x, y, w, h, title, scope=None, sub=None):
        """White box with a black header bar: the part of the system the diagram is about. The bar's top corners
        follow the box's corners exactly."""
        band = 56
        self._banded(x, y, w, h, band, Palette.INK, Palette.WHITE, Palette.INK, 3)
        self.text_mid(x + 24, y + band / 2, title, 22, Palette.WHITE)
        if scope:                                  # on the title's baseline
            base = y + band / 2 - self._ts(title, 22)[1] / 2 + self._optical_dy(22) + self._baseline(22)
            self.text(x + w - 24, base - self._baseline(15), scope, 15, Palette.ON_DARK, align="right")
        if sub:
            self.text(x + 24, y + band + 10, sub, 13, Palette.GREY)
        return (x, y, w, h)

    def lane(self, x, y, w, h, label, fill=None, stroke=None, color=None, style="solid", sw=1):
        """Horizontal swimlane: tinted band (default LANE / LINE) with its label (default INK) in the top-left."""
        self.rect(x, y, w, h, _c(fill, "LANE"), _c(stroke, "LINE"), sw, style)
        self.text(x + PAD, y + 10, label, 13, _c(color, "INK"))
        return (x, y, w, h)

    def hero_bar(self, x, y, w, title, segments, caption=None, h=56):
        """segments: list of (value, label, kind) with kind in 'measured', 'measured_dark', 'wait', 'unmeasured'.
        Widths are proportional to value; unmeasured segments are dashed."""
        self.text(x, y, title, 24, Palette.INK)
        styles = {"measured": (Palette.PAPER, Palette.STONE, Palette.MID, "solid"),
                  "measured_dark": (Palette.INK, Palette.INK, Palette.WHITE, "solid"),
                  "wait": (Palette.ORANGE_SOFT, Palette.ORANGE, Palette.INK, "solid"),
                  "unmeasured": (Palette.PAPER, Palette.STONE, Palette.GREY, "dashed")}
        total = sum(s[0] for s in segments)
        bx = x
        for v, lab, kind in segments:
            bg, bd, tx, st = styles[kind]
            sw = w * v / total
            self.rect(bx, y + 50, sw, h, bg, bd, 2, st, rounded=False)
            self.text_mid(bx + 14, y + 50 + h / 2, lab, 16, tx)
            if self._ts(lab, 16)[0] > sw - 20:
                warn(f"OVERFLOW in hero segment '{lab[:30]}'")
            bx += sw
        if caption:
            self.text(x, y + 50 + h + 14, caption, 13, Palette.GREY)

    def rows(self, x, y, w, total_h, items, bar=None, fill=None, stroke=None, label_w=150):
        """Equal-height bars filling total_h, each with a coloured left edge (default INK) that follows its
        rounded corners. items: strings, or (label, text) pairs."""
        bar = _c(bar, "INK")
        gap = 10
        h = (total_h - gap * (len(items) - 1)) / len(items)
        for it in items:
            self.edge_rect(x, y, w, h, bar, EDGE, _c(fill, "WHITE"), _c(stroke, "LINE"), 2)
            if isinstance(it, tuple):
                self.text_mid(x + EDGE + PAD, y + h / 2, it[0], 17, Palette.INK)
                self.text_mid(x + label_w, y + h / 2, it[1], 16, Palette.INK)
                if self._ts(it[0], 17)[0] > label_w - EDGE - PAD - GAP:
                    warn(f"OVERFLOW in row label '{it[0][:30]}': raise label_w")
            else:
                self.text_mid(x + EDGE + PAD, y + h / 2, it, 16, Palette.INK)
            y += h + gap

    def questions_box(self, x, y, w, h, title, questions):
        self.text(x, y, title, 14, Palette.YELLOW_TXT)
        self.rect(x, y + 30, w, h, Palette.YELLOW_BG, Palette.YELLOW, 2, "dashed")
        body = "\n\n".join(f"{i + 1}. {q}" for i, q in enumerate(questions))
        self.text(x + 24, y + 50, body, 16, Palette.INK)
        if self._ts(body, 16)[1] > h - 30:
            warn(f"OVERFLOW in questions box '{title}'")

    # ------------------------------------------------------------ generic components (any diagram type)
    def node(self, x, y, w, h, label, sub=None, fill=None, stroke=None, strong=False, size=17):
        """A component, system or concept: centred label, optional small subtitle. strong = the one loud box.
        Defaults: fill WHITE, stroke INK."""
        fill, stroke = _c(fill, "WHITE"), _c(stroke, "INK")
        self.rect(x, y, w, h, Palette.INK if strong else fill, Palette.INK if strong else stroke, 3 if strong else 2)
        col = Palette.WHITE if strong else Palette.INK
        lh = self._ts(label, size)[1] + (self._ts(sub, 13)[1] + 4 if sub else 0)
        ty = y + (h - lh) / 2
        self.text(x + w / 2, ty, label, size, col, align="center")
        if sub:
            self.text(x + w / 2, ty + self._ts(label, size)[1] + 4, sub, 13, Palette.ON_DARK if strong else Palette.GREY,
                      align="center")
        if self._ts(label, size)[0] > w - 20 or (sub and self._ts(sub, 13)[0] > w - 20):
            warn(f"OVERFLOW in node '{label[:30]}'")
        return (x, y, w, h)

    def group(self, x, y, w, h, title, fill=None, stroke=None, header=None, header_text=None):
        """A tinted zone (default PAPER / LINE) holding related nodes; header = colour of an optional 44 px title
        band whose corners follow the zone's corners; header_text defaults to WHITE."""
        fill, stroke = _c(fill, "PAPER"), _c(stroke, "LINE")
        if header:
            self._banded(x, y, w, h, 44, header, fill, stroke, 2)
            self.text_mid(x + 18, y + 22, title, 17, _c(header_text, "WHITE"))
        else:
            self.rect(x, y, w, h, fill, stroke, 1)
            self.text(x + PAD, y + 10, title, 13, Palette.GREY)
        return (x, y, w, h)

    def _label_path(self, pts, label, color, size, sw):
        """Place a label beside a polyline: above its longest horizontal segment, else right of its longest
        vertical one, else above the midpoint. Never on the line."""
        w, h = self._ts(label, size)
        segs = list(zip(pts, pts[1:]))
        hor = [s for s in segs if abs(s[0][1] - s[1][1]) < 0.5]
        ver = [s for s in segs if abs(s[0][0] - s[1][0]) < 0.5]
        if hor:
            a, b = max(hor, key=lambda s: abs(s[1][0] - s[0][0]))
            return self.text((a[0] + b[0]) / 2, a[1] - sw / 2 - LABEL_GAP - h, label, size, color, align="center")
        if ver:
            a, b = max(ver, key=lambda s: abs(s[1][1] - s[0][1]))
            return self.text(a[0] + sw / 2 + LABEL_GAP + 2, (a[1] + b[1]) / 2 - h / 2, label, size, color)
        a, b = pts[0], pts[-1]
        return self.text((a[0] + b[0]) / 2, min(a[1], b[1]) - LABEL_GAP - h, label, size, color, align="center")

    def labelled_arrow(self, x1, y1, x2, y2, label, color=None, sw=3, size=13, via=None):
        """Arrow with a short label above its longest horizontal segment (beside it when the arrow is vertical),
        never on the line."""
        color = _c(color, "INK")
        self.arrow(x1, y1, x2, y2, color, sw, via=via)
        self._label_path([(x1, y1)] + list(via or []) + [(x2, y2)], label, color, size, sw)

    def connect(self, a, b, label=None, color=None, sw=2, style="solid", gap=ARROW_GAP, size=13):
        """Arrow between two boxes (x, y, w, h) — e.g. what node() returns — leaving `gap` at both ends. Straight
        when the boxes face each other, otherwise a square elbow from side to side."""
        color = _c(color, "INK")
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        acx, acy, bcx, bcy = ax + aw / 2, ay + ah / 2, bx + bw / 2, by + bh / 2
        horizontal = bx >= ax + aw or bx + bw <= ax
        vertical = by >= ay + ah or by + bh <= ay
        if horizontal and vertical:      # diagonal neighbours: go along the larger separation
            horizontal = abs(bcx - acx) >= abs(bcy - acy)
        via = None
        if horizontal:
            right = bx >= ax + aw
            x1, x2 = (ax + aw + gap, bx - gap) if right else (ax - gap, bx + bw + gap)
            lo, hi = max(ay, by), min(ay + ah, by + bh)
            if hi - lo >= 16:
                y1 = y2 = (lo + hi) / 2
            else:
                y1, y2 = acy, bcy
                mx = (x1 + x2) / 2
                via = [(mx, y1), (mx, y2)]
        else:
            down = by >= ay + ah
            y1, y2 = (ay + ah + gap, by - gap) if down else (ay - gap, by + bh + gap)
            lo, hi = max(ax, bx), min(ax + aw, bx + bw)
            if hi - lo >= 16:
                x1 = x2 = (lo + hi) / 2
            else:
                x1, x2 = acx, bcx
                my = (y1 + y2) / 2
                via = [(x1, my), (x2, my)]
        e = self.arrow(x1, y1, x2, y2, color, sw, style, via=via)
        if label:
            self._label_path([(x1, y1)] + list(via or []) + [(x2, y2)], label, color, size, sw)
        return e

    def stat(self, x, y, w, value, label, color=None, big=False, h=None, value_size=None):
        """A key-figure tile: coloured left edge (default INK) that follows the rounded corners, the figure, one or
        two lines of context. value_size sets the figure size (default 38 when big, else 28; ~56 for the one hero
        figure of a poster); the height grows to fit unless h is given. Returns the box (x, y, w, h)."""
        color = _c(color, "INK")
        vs = value_size or (38 if big else 28)
        vh, (lw, lh) = self._ts(value, vs)[1], self._ts(label, 13)
        need = PAD - 2 + vh + 10 + lh + PAD
        h = h or max(150 if big else 120, need)
        self.edge_rect(x, y, w, h, color, EDGE, Palette.WHITE, Palette.LINE, 2)
        tx = x + EDGE + PAD + 4
        self.text(tx, y + PAD - 2, value, vs, color)
        ly = y + PAD - 2 + vh + 10
        self.text(tx, ly, label, 13, Palette.MID)
        if ly + lh > y + h - 8:
            warn(f"OVERFLOW in stat '{value}': raise h")
        if max(self._ts(value, vs)[0], lw) > w - (tx - x) - PAD:
            warn(f"OVERFLOW (width) in stat '{value}'")
        return (x, y, w, h)

    def timeline(self, x, y, w, ticks, color=None, today=None, *, label_mode="tick", spans=None, today_color=None,
                 today_label="today", today_up=120, today_down=120):
        """Horizontal axis with evenly spaced ticks; returns the x of every tick mark.

        label_mode "tick": one label under each tick (len(ticks) marks). "span": the labels name the intervals
        (quarters, sprints): len(ticks) + 1 marks, each label centred between two marks.
        spans: list of (start, end, label) or (start, end, label, colour) in tick units (0 = first mark), drawn as
        a bracket with its label centred below the tick labels.
        today: position in tick units for a dashed marker (today_color defaults to INK, today_label to "today",
        today_up / today_down = length above / below the axis)."""
        color = _c(color, "INK")
        n = len(ticks) if label_mode == "span" else max(1, len(ticks) - 1)

        def at(i):
            return x + w * i / n

        self.line(x, y, [[0, 0], [w, 0]], color, 3)
        xs = [at(i) for i in range(n + 1)]
        for tx in xs:
            self.line(tx, y - 8, [[0, 0], [0, 16]], color, 3)
        for i, lab in enumerate(ticks):
            self.text(at(i + 0.5) if label_mode == "span" else at(i), y + 16, lab, 13, Palette.MID, align="center")
        by = y + 16 + self._ts("X", 13)[1] + 18
        for sp in spans or ():
            s, e, lab = sp[:3]
            col = sp[3] if len(sp) > 3 else Palette.STONE
            x1, x2 = at(s) + 2, at(e) - 2
            self.line(x1, by - 6, [[0, 0], [0, 6], [x2 - x1, 6], [x2 - x1, 0]], col, 2)
            self.text((x1 + x2) / 2, by + LABEL_GAP, lab, 13, col if len(sp) > 3 else Palette.MID, align="center")
        if today is not None:
            tc = _c(today_color, "INK")
            tx = at(today)
            gap_top, gap_bottom = y + 10, y + 16 + self._ts("X", 13)[1] + 4      # keep clear of the tick labels
            if y + today_down <= gap_top:
                self.line(tx, y - today_up, [[0, 0], [0, today_up + today_down]], tc, 2, "dashed")
            else:
                self.line(tx, y - today_up, [[0, 0], [0, gap_top - (y - today_up)]], tc, 2, "dashed")
                if y + today_down > gap_bottom:
                    self.line(tx, gap_bottom, [[0, 0], [0, y + today_down - gap_bottom]], tc, 2, "dashed")
            if today_label:
                self.text(tx + LABEL_GAP, y - today_up, today_label, 13, tc)
        return xs

    # ------------------------------------------------------------ small marks
    def step(self, x, y, n, color=None, size=28, outline=False):
        """Numbered step marker: a disc of diameter `size` with its top-left at (x, y), the number optically
        centred. outline=True draws a white disc with a coloured ring and number. Returns the diameter."""
        color = _c(color, "INK")
        fill, ring, txt = (Palette.WHITE, color, color) if outline else (color, color, Palette.WHITE)
        self.ellipse(x, y, size, size, fill, ring, 2 if outline else 1)
        fs = round(size * (0.5 if len(str(n)) < 2 else 0.43))
        self.text_mid(x + size / 2, y + size / 2, str(n), fs, txt, align="center")
        return size

    def dot(self, cx, cy, color, label=None, d=10, size=13, label_color=None):
        """Status or category dot centred on (cx, cy), with an optional label to its right. Returns the total width."""
        self.ellipse(cx - d / 2, cy - d / 2, d, d, color, color, 1)
        if not label:
            return d
        self.text_mid(cx + d / 2 + GAP, cy, label, size, _c(label_color, "INK"))
        return d + GAP + self._ts(label, size)[0]

    def divider(self, x, y, w, label=None, color=None, size=12, label_color=None, sw=1):
        """Horizontal hairline at y (default LINE); with a label (default GREY), the line breaks around it."""
        color = _c(color, "LINE")
        if not label:
            return self.line(x, y, [[0, 0], [w, 0]], color, sw)
        tw = self._ts(label, size)[0]
        cx = x + w / 2
        g = GAP + 4
        self.line(x, y, [[0, 0], [w / 2 - tw / 2 - g, 0]], color, sw)
        self.line(cx + tw / 2 + g, y, [[0, 0], [w / 2 - tw / 2 - g, 0]], color, sw)
        return self.text_mid(cx, y, label, size, _c(label_color, "GREY"), align="center")

    def callout(self, x, y, tx, ty, text, color=None, size=13, line_color=None):
        """Annotation: text (default MID) with its top-left at (x, y) and a thin leader line (default STONE) from
        the text's nearest side to the target point (tx, ty), which gets a small dot. The leader never touches
        the text (LABEL_GAP)."""
        line_color = _c(line_color, "STONE")
        self.text(x, y, text, size, _c(color, "MID"))
        w, h = self._ts(text, size)
        if tx < x - LABEL_GAP:
            sx, sy = x - LABEL_GAP, y + h / 2
        elif tx > x + w + LABEL_GAP:
            sx, sy = x + w + LABEL_GAP, y + h / 2
        elif ty < y:
            sx, sy = min(max(tx, x), x + w), y - LABEL_GAP / 2
        else:
            sx, sy = min(max(tx, x), x + w), y + h + LABEL_GAP / 2
        self.line(sx, sy, [[0, 0], [tx - sx, ty - sy]], line_color, 1)
        self.ellipse(tx - 3, ty - 3, 6, 6, line_color, line_color, 1)

    # ------------------------------------------------------------ output
    def dump(self, path, background=None, paint_background=False):
        """Write the scene. background defaults to Palette.CANVAS; paint_background=True (or an earlier canvas()
        call) also paints it as a full-bleed rectangle under everything, for renderers that ignore the file's
        background colour."""
        bg = _c(background, "CANVAS")
        els = self.els
        if (self._canvas or paint_background) and els:
            colour, margin = self._canvas or (None, CANVAS_MARGIN)
            colour = colour or bg
            b = [_bounds(e) for e in els]
            x0, y0 = min(v[0] for v in b) - margin, min(v[1] for v in b) - margin
            x1, y1 = max(v[2] for v in b) + margin, max(v[3] for v in b) + margin
            page = {"id": "page0000", "type": "rectangle", "x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0,
                    "angle": 0, "strokeColor": "transparent", "backgroundColor": colour, "fillStyle": "solid",
                    "strokeWidth": 1, "strokeStyle": "solid", "roughness": 0, "opacity": 100, "groupIds": [],
                    "frameId": None, "roundness": None, "seed": 1, "version": 1, "versionNonce": 1,
                    "isDeleted": False, "boundElements": None, "updated": 1, "link": None, "locked": False}
            els = [page] + els
        data = {"type": "excalidraw", "version": 2, "source": "https://excalidraw.com", "elements": els,
                "appState": {"gridSize": 20, "viewBackgroundColor": bg}, "files": {}}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        return path


def hand_drawn(scene):
    """Switch a scene to the hand-drawn look (Excalifont, roughness 1). Call right after Scene(), before building.
    Widths are measured per font, so this also resets WIDEN to 1.0 (older scripts set it to 1.16 first)."""
    global WIDEN
    scene.font = FONT_HAND
    scene.roughness = 1
    _current_font[0] = FONT_HAND
    WIDEN = 1.0
    return scene
