"""palettes — three curated colour systems for excalikit, plus the spacing and type scales.

    from palettes import use, SPACE, TYPE
    pal = use("warm")              # recolours excalikit.Palette (and the kit's colour defaults) in place
    S = Scene(); ...; S.dump(out, background=pal["canvas"])

Every palette fills the same roles, so a generator written for one works with the others:

    canvas   page background (Scene.dump background)
    white    card / node surface            paper  quiet zone, unchanged or out-of-scope box
    lane     lane / container tint          line   hairline borders of quiet boxes and zones
    stone    dashed outlines, chip borders  grey   captions, section labels, footers
    mid      body text, secondary arrows    ink    titles, main strokes, the one loud fill
    on_dark  secondary text on an ink fill
    accent   THE thing that matters (one per diagram), with accent_bg (tint) and accent_soft (border of tints)
    bad      problems, failure paths, what disappears        good  targets, improvements, what appears
    wait     waiting, in progress                            open  open questions (always dashed), open_txt for its text
    cat1     first category family (data, infra)             cat2  second category family (people, services)

Each colour role has a *_bg (pale tint for fills) and a *_soft (mid tint for borders of tinted boxes).
`use()` maps the roles onto the kit's names (ACCENT, RED, GREEN, ORANGE, YELLOW, BLUE, TEAL, INK...) and also swaps the
kit's default colour arguments, so calls that rely on defaults follow the palette.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import excalikit  # noqa: E402

# ---------------------------------------------------------------- scales (use these, not ad-hoc numbers)
SPACE = {"xs": 4, "s": 8, "m": 16, "l": 24, "xl": 32, "2xl": 48, "3xl": 64, "4xl": 96}
TYPE = {"display": 56, "title": 36, "subtitle": 20, "heading": 18, "label": 16, "body": 14, "caption": 13, "micro": 12}

# ---------------------------------------------------------------- palettes
PALETTES = {
    # Clean: cool neutrals on white, one violet accent. Slides, documentation, anything shared outside the team.
    "clean": {
        "canvas": "#ffffff", "white": "#ffffff", "paper": "#f8f9fa", "lane": "#f1f3f5", "line": "#dee2e6",
        "stone": "#adb5bd", "grey": "#646c74", "mid": "#495057", "ink": "#212529", "on_dark": "#ced4da",
        "accent": "#6741d9", "accent_bg": "#f3f0ff", "accent_soft": "#d0bfff",
        "bad": "#c92a2a", "bad_bg": "#fff5f5", "bad_soft": "#ffc9c9",
        "good": "#287d39", "good_bg": "#ebfbee", "good_soft": "#b2f2bb",
        "wait": "#b8470a", "wait_bg": "#fff4e6", "wait_soft": "#ffd8a8",
        "open": "#fab005", "open_bg": "#fff9db", "open_txt": "#806600",
        "cat1": "#1864ab", "cat1_bg": "#e7f5ff", "cat1_soft": "#a5d8ff",
        "cat2": "#087c59", "cat2_bg": "#e6fcf5", "cat2_soft": "#96f2d7",
    },
    # Warm: cream paper, warm greys, terracotta accent. Hand-drawn explainers, workshops, blog posts.
    "warm": {
        "canvas": "#fdf8f1", "white": "#fffdf9", "paper": "#f6efe5", "lane": "#f3ebdf", "line": "#e6dccd",
        "stone": "#c4b6a4", "grey": "#70675d", "mid": "#5c544b", "ink": "#2d2926", "on_dark": "#d8cfc3",
        "accent": "#bb3f0d", "accent_bg": "#fff1e6", "accent_soft": "#ffc9a3",
        "bad": "#a3213f", "bad_bg": "#fbeef1", "bad_soft": "#eab8c4",
        "good": "#3a7535", "good_bg": "#eff6ea", "good_soft": "#bfdcb3",
        "wait": "#8c6017", "wait_bg": "#faf1dc", "wait_soft": "#e7cf9c",
        "open": "#e0a800", "open_bg": "#fff8dc", "open_txt": "#7a5a00",
        "cat1": "#3c6c96", "cat1_bg": "#edf3f8", "cat1_soft": "#bcd2e6",
        "cat2": "#47725f", "cat2_bg": "#eef5f0", "cat2_soft": "#bfd8cb",
    },
    # Ink: deep navy ink on off-white paper, a single cobalt pen. Posters, editorial pieces, one-page summaries.
    "ink": {
        "canvas": "#f7f4ec", "white": "#fcfaf5", "paper": "#efebe0", "lane": "#ece7da", "line": "#dbd5c7",
        "stone": "#aaa69b", "grey": "#62666d", "mid": "#454b58", "ink": "#1b2030", "on_dark": "#c9cdd8",
        "accent": "#1d4ed8", "accent_bg": "#ebf0fd", "accent_soft": "#b3c5f5",
        "bad": "#b83729", "bad_bg": "#fbeeec", "bad_soft": "#efbdb6",
        "good": "#2b7349", "good_bg": "#ecf5ef", "good_soft": "#b5d8c2",
        "wait": "#955400", "wait_bg": "#fcf2e3", "wait_soft": "#f0cf9d",
        "open": "#d4a106", "open_bg": "#fbf4d9", "open_txt": "#6f5400",
        "cat1": "#4a5d82", "cat1_bg": "#eef0f6", "cat1_soft": "#c2c9db",
        "cat2": "#5c6b4f", "cat2_bg": "#f0f3ec", "cat2_soft": "#cbd5c0",
    },
    # Playful: cream paper, soft ink, bright pastels, orange pen. Illustrated explainers for a general audience,
    # blog posts, onboarding. Pair it with tints() for one pastel per step.
    "playful": {
        "canvas": "#fffcf5", "white": "#ffffff", "paper": "#f8f4ec", "lane": "#f5efe3", "line": "#e6ddcd",
        "stone": "#c6bba8", "grey": "#6a645d", "mid": "#55504a", "ink": "#343a40", "on_dark": "#e9ecef",
        "accent": "#c2410c", "accent_bg": "#fff4e6", "accent_soft": "#ffc078",
        "bad": "#c92a2a", "bad_bg": "#fff5f5", "bad_soft": "#ffc9c9",
        "good": "#2b8a3e", "good_bg": "#ebfbee", "good_soft": "#b2f2bb",
        "wait": "#c2410c", "wait_bg": "#fff4e6", "wait_soft": "#ffd8a8",
        "open": "#fab005", "open_bg": "#fff9db", "open_txt": "#806600",
        "cat1": "#1864ab", "cat1_bg": "#e7f5ff", "cat1_soft": "#a5d8ff",
        "cat2": "#0b7285", "cat2_bg": "#e3fafc", "cat2_soft": "#99e9f2",
    },
}

# role -> kit attribute names it drives
_KIT = {
    "ink": ["INK"], "mid": ["MID"], "grey": ["GREY"], "line": ["LINE"], "paper": ["PAPER"], "stone": ["STONE"],
    "white": ["WHITE"], "lane": ["LANE"], "on_dark": ["ON_DARK"],
    "accent": ["ACCENT"], "accent_bg": ["ACCENT_BG"], "accent_soft": ["ACCENT_SOFT"],
    "bad": ["RED"], "bad_bg": ["RED_BG"], "bad_soft": ["RED_SOFT"],
    "good": ["GREEN"], "good_bg": ["GREEN_BG"], "good_soft": ["GREEN_SOFT"],
    "wait": ["ORANGE"], "wait_bg": ["ORANGE_BG"], "wait_soft": ["ORANGE_SOFT"],
    "open": ["YELLOW"], "open_bg": ["YELLOW_BG"], "open_txt": ["YELLOW_TXT"],
    "cat1": ["BLUE"], "cat1_bg": ["BLUE_BG"], "cat1_soft": ["BLUE_SOFT"],
    "cat2": ["TEAL"], "cat2_bg": ["TEAL_BG"], "cat2_soft": ["TEAL_SOFT"],
}

_ORIGINAL = {a: getattr(excalikit.Palette, a) for names in _KIT.values() for a in names if hasattr(excalikit.Palette, a)}


def _swap(value, table):
    if isinstance(value, str):
        return table.get(value.lower(), value)
    if isinstance(value, tuple):
        return tuple(_swap(v, table) for v in value)
    return value


def use(name="clean"):
    """Recolour the kit with palette `name`; returns the palette dict (read 'canvas' for Scene.dump).
    Call once, before building the scene."""
    pal = PALETTES[name]
    current = {a: getattr(excalikit.Palette, a) for a in _ORIGINAL}
    table = {}
    for role, attrs in _KIT.items():
        for a in attrs:
            if a in current:
                table[current[a].lower()] = pal[role]
                setattr(excalikit.Palette, a, pal[role])
    for fn in vars(excalikit.Scene).values():          # colour defaults were bound at import time
        if callable(fn) and getattr(fn, "__defaults__", None):
            fn.__defaults__ = tuple(_swap(v, table) for v in fn.__defaults__)
        if callable(fn) and getattr(fn, "__kwdefaults__", None):
            fn.__kwdefaults__ = {k: _swap(v, table) for k, v in fn.__kwdefaults__.items()}
    if hasattr(excalikit, "STATUS"):
        for k, v in list(excalikit.STATUS.items()):
            excalikit.STATUS[k] = _swap(v, table)
    return pal


def setup(args_hand=False, palette=None):
    """Common preamble for the examples: pick the palette (warm for hand-drawn unless given), switch the font
    width estimate, return (Scene, palette dict)."""
    pal = use(palette or ("warm" if args_hand else "clean"))
    if args_hand:
        excalikit.WIDEN = 1.16
    S = excalikit.Scene()
    if args_hand:
        excalikit.hand_drawn(S)
    return S, pal


def example(default_out, doc=""):
    """Argument parsing shared by the examples: --out, --hand, --palette. Returns (args, Scene, palette dict)."""
    import argparse
    ap = argparse.ArgumentParser(description=doc)
    ap.add_argument("--out", default=default_out)
    ap.add_argument("--hand", action="store_true", help="hand-drawn look (Excalifont, roughness 1, warm palette)")
    ap.add_argument("--palette", choices=sorted(PALETTES), help="clean (default), warm (default with --hand), ink, playful")
    args = ap.parse_args()
    S, pal = setup(args.hand, args.palette)
    return args, S, pal


# ---------------------------------------------------------------- per-step tints (illustrated explainers)
# (card fill, badge fill) pairs. In an explainer each step may get its own pastel: colour paces the reading instead of
# coding a meaning, so no legend is needed. Keep the accent for the takeaway line. Badges carry ink numbers.
TINTS = {
    "playful": [("#fff3bf", "#ffd43b"), ("#ffe8cc", "#ffa94d"), ("#d3f9d8", "#69db7c"), ("#e5dbff", "#b197fc"),
                ("#ffdeeb", "#faa2c1"), ("#d0ebff", "#74c0fc"), ("#c3fae8", "#63e6be")],
    "warm": [("#faefd9", "#e9c46a"), ("#f9e3d3", "#e5986b"), ("#e6efdf", "#9cc18b"), ("#ebe4f1", "#b5a2cf"),
             ("#f6e1e3", "#d99aa3"), ("#e1ebf3", "#8fb3d3"), ("#e0f0ec", "#86c2b2")],
}


def tints(n, name="playful"):
    """n (card fill, badge fill) pairs, cycling if n exceeds the list. Unknown palettes get the playful set."""
    seq = TINTS.get(name, TINTS["playful"])
    return [seq[i % len(seq)] for i in range(n)]
