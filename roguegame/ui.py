"""Drawing helpers and simple widgets."""
import math
import sys
import os

import pygame

from .data import ITEMS, CHARACTERS, describe_stats, sell_value, class_label, TAG_INFO, recipes_for, recipe_of

W, H = 1280, 720

BG = (16, 14, 22)
PANEL = (30, 27, 40)
PANEL2 = (42, 38, 56)
LINE = (70, 64, 90)
TEXT = (232, 226, 210)
DIM = (150, 144, 160)
GOLD = (226, 186, 92)
RED = (210, 70, 70)
GREEN = (90, 200, 110)
BLUE = (90, 150, 230)
POISON = (130, 200, 70)
BURN = (240, 140, 50)

_NORMAL = dict(RED=RED, GREEN=GREEN, POISON=POISON, BURN=BURN, BLUE=BLUE)
# colour-blind friendly (Okabe-Ito based): heal is sky blue, poison is purple, damage vermillion
_COLORBLIND = dict(RED=(213, 94, 0), GREEN=(86, 180, 233), POISON=(204, 121, 167), BURN=(240, 190, 40),
                   BLUE=(0, 114, 178))


def apply_palette(colorblind):
    """Swap the status colours (and the keyword colours) for the colour-blind palette, or back."""
    from . import keywords
    pal = _COLORBLIND if colorblind else _NORMAL
    globals().update(pal)
    swaps = {"poison": "POISON", "heal": "GREEN", "regen": "GREEN", "burn": "BURN", "block": "BLUE"}
    for k, name in swaps.items():
        n, _, desc = keywords.KEYWORDS[k]
        keywords.KEYWORDS[k] = (n, pal[name] if colorblind else keywords.BASE_COLOURS[k], desc)


RARITY_COL = {"common": (160, 160, 165), "rare": (80, 145, 235),
              "epic": (180, 95, 230), "legendary": (245, 165, 40)}
TAG_COL = {"weapon": (58, 44, 52), "armor": (34, 50, 80), "food": (92, 64, 38),
           "poison": (40, 72, 38), "fire": (110, 44, 22), "charm": (90, 34, 44),
           "tool": (52, 52, 60), "scroll": (96, 80, 46), "enemy": (90, 36, 40),
           "summon": (30, 70, 80), "curse": (64, 40, 84), "ki": (100, 72, 30)}
# bright chip colour for each tag (tooltips, compendium filters): the same colour everywhere a tag is shown
TAG_CHIP = {"weapon": (225, 225, 235), "armor": (120, 175, 250), "food": (240, 205, 150), "poison": (140, 215, 90),
            "fire": (250, 150, 70), "charm": (245, 140, 160), "tool": (180, 190, 205), "scroll": (230, 200, 130),
            "summon": (120, 210, 230), "curse": (185, 140, 235), "ki": (255, 200, 120), "enemy": (240, 120, 120)}
# bright line colour used for the item icon on top of the dark fill
LINE_COL = {"weapon": (215, 215, 230), "armor": (120, 180, 255), "food": (245, 235, 210),
            "poison": (150, 230, 100), "fire": (255, 160, 60), "charm": (255, 120, 120),
            "tool": (190, 200, 210), "scroll": (240, 210, 140), "enemy": (240, 120, 120)}
# glyph shape used per tag (see _glyph)
GLYPH = {"weapon": "weapon", "armor": "shield", "food": "food", "poison": "poison", "fire": "fire",
         "charm": "charm", "tool": "tool", "scroll": "scroll", "summon": "charm", "curse": "poison", "ki": "charm"}
LINE_COL.update(summon=(140, 230, 245), curse=(200, 150, 245), ki=(255, 210, 130))

_fonts = {}
TEXT_SCALE = 1.0          # "Larger text" setting


def set_text_scale(k):
    global TEXT_SCALE
    TEXT_SCALE = k
    _fonts.clear()

# ---------------------------------------------------------------- pixel art (Ninja Adventure pack, CC0)
ART_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "art")
_art_src = {}
_art_cache = {}


def art(key, size, long_side=None):
    """Return the pixel-art sprite for `key` scaled (nearest-neighbour, crisp pixels) to fit
    a size x size box (or long_side along its long axis), or None if there is no art."""
    if key not in _art_src:
        p = os.path.join(ART_DIR, f"{key}.png")
        _art_src[key] = pygame.image.load(p).convert_alpha() if os.path.exists(p) else _placeholder(key)
    src = _art_src[key]
    if src is None or size <= 0:
        return None
    ck = (key, size, long_side)
    if ck not in _art_cache:
        w, h = src.get_size()
        box_w = box_h = size
        if long_side:
            if h >= w:
                box_h = long_side
            else:
                box_w = long_side
        k = min(box_w / w, box_h / h)
        if k >= 4:
            k = int(k)                  # big sizes: whole-number scaling keeps pixel art crisp
        # small sizes keep the in-between scale (nearest-neighbour): rounding down to 1x / 2x left sprites,
        # especially diagonal ones in long items (staves, katanas), small inside their tiles
        _art_cache[ck] = pygame.transform.scale(src, (max(1, int(w * k)), max(1, int(h * k))))
    return _art_cache[ck]


def _placeholder(key):
    """Stand-in icon for an item whose sprite hasn't been made yet (see assets/sprite_requests.md): its main
    tag's symbol on a tag-coloured tile, with the item's initials, so different items still look different."""
    d = ITEMS.get(key)
    if d is None or d["enemy"]:
        return None
    tag = d["tags"][0]
    img = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.rect(img, TAG_COL.get(tag, (60, 60, 60)), (1, 1, 30, 30), border_radius=6)
    pygame.draw.rect(img, TAG_CHIP.get(tag, TEXT), (1, 1, 30, 30), 1, border_radius=6)
    _glyph(img, GLYPH.get(tag, tag), (16, 13), 16, LINE_COL.get(tag, TEXT_CHIP_FALLBACK))
    initials = "".join(w[0] for w in d["name"].replace("-", " ").split()[:2]).upper()
    f = pygame.font.Font(None, 14)
    t = f.render(initials, True, (250, 245, 235))
    img.blit(t, t.get_rect(center=(16, 26)))
    return img


TEXT_CHIP_FALLBACK = (230, 230, 230)
WEB = sys.platform == "emscripten"


def font(size, bold=False, italic=False):
    key = (size, bold, italic)
    if key not in _fonts:
        size = int(round(size * TEXT_SCALE))
        if WEB:
            # browsers have no system fonts: use pygame's built-in font (scaled to match Segoe UI's size)
            f = pygame.font.Font(None, int(size * 1.3))
            f.set_bold(bold)
            f.set_italic(italic)
            _fonts[key] = f
        else:
            _fonts[key] = pygame.font.SysFont("segoeui,arial,helvetica", size, bold=bold, italic=italic)
    return _fonts[key]


def rich_text_block(surf, s, pos, width, size=16, col=TEXT, spacing=4, hits=None):
    """Like text_block, but effect keywords (Poison, Burn, Block...) are drawn in their own colour, in italics.
    hits: optional list that receives (rect, keyword) for every keyword drawn."""
    from .keywords import KEYWORDS, keyword_of
    x0, y = pos
    x = x0
    lh = font(size).get_height() + spacing
    space = font(size).size(" ")[0]
    for word in s.split(" "):
        if not word:
            x += space
            continue
        k = keyword_of(word)
        f = font(size, bold=bool(k), italic=bool(k))
        w = f.size(word)[0]
        if x > x0 and x + w > x0 + width:
            x, y = x0, y + lh
        surf.blit(f.render(word, True, KEYWORDS[k][1] if k else col), (x, y))
        if k and hits is not None:
            hits.append((pygame.Rect(x, y, w, lh - spacing), k))
        x += w + space
    return y + lh


def keyword_glossary(surf, keys, pos, width, size=13, limit=4):
    """'Poison: deals its stacks...' lines for the given keyword keys. Returns the y after the last line."""
    from .keywords import KEYWORDS
    x, y = pos
    for k in keys[:limit]:
        name, col, desc = KEYWORDS[k]
        label = font(size, True, True).render(name + ":", True, col)
        surf.blit(label, (x, y))
        y = text_block(surf, desc, (x + label.get_width() + 5, y), width - label.get_width() - 5, size, DIM)
    return y


def text(surf, s, pos, size=18, col=TEXT, bold=False, center=False, right=False):
    img = font(size, bold).render(str(s), True, col)
    r = img.get_rect()
    if center:
        r.center = pos
    elif right:
        r.topright = pos
    else:
        r.topleft = pos
    surf.blit(img, r)
    return r


def wrap(s, size, width, bold=False):
    f = font(size, bold)
    words, lines, cur = s.split(" "), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if f.size(test)[0] <= width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def text_block(surf, s, pos, width, size=16, col=TEXT, spacing=4, bold=False):
    x, y = pos
    for line in wrap(s, size, width, bold):
        text(surf, line, (x, y), size, col, bold)
        y += font(size, bold).get_height() + spacing
    return y


def panel(surf, rect, col=PANEL, border=LINE, radius=8, width=2):
    pygame.draw.rect(surf, col, rect, border_radius=radius)
    if border:
        pygame.draw.rect(surf, border, rect, width, border_radius=radius)


class Button:
    def __init__(self, rect, label, cb, size=20, enabled=True, col=PANEL2):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.cb = cb
        self.size = size
        self.enabled = enabled
        self.col = col

    def draw(self, surf):
        hover = self.rect.collidepoint(pygame.mouse.get_pos()) and self.enabled
        col = tuple(min(255, c + 25) for c in self.col) if hover else self.col
        if not self.enabled:
            col = (35, 33, 42)
        panel(surf, self.rect, col, GOLD if hover else LINE)
        size = self.size                       # shrink the label until it fits the button
        while size > 11 and font(size, True).size(str(self.label))[0] > self.rect.width - 16:
            size -= 1
        text(surf, self.label, self.rect.center, size, TEXT if self.enabled else DIM, True, center=True)

    def handle(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.enabled \
                and self.rect.collidepoint(ev.pos):
            from . import audio
            audio.play("click", 0.6)
            self.cb()
            return True
        return False


def item_color(iid):
    tags = ITEMS[iid]["tags"]
    return TAG_COL.get(tags[0], (90, 90, 90))


def _glyph(surf, tag, center, size, col):
    """Very simple line-art 'tattoo' for each tag."""
    x, y = center
    s = size
    w = max(2, int(s / 9))
    if tag == "weapon":       # dagger
        pygame.draw.line(surf, col, (x - s * .5, y + s * .5), (x + s * .5, y - s * .5), w + 1)
        pygame.draw.line(surf, col, (x - s * .45, y + s * .05), (x - s * .05, y + s * .45), w)
    elif tag == "shield":
        pts = [(x - s * .45, y - s * .45), (x + s * .45, y - s * .45), (x + s * .4, y + s * .1),
               (x, y + s * .55), (x - s * .4, y + s * .1)]
        pygame.draw.polygon(surf, col, pts, w)
    elif tag == "heal":       # heart
        r = s * .26
        pygame.draw.circle(surf, col, (x - r * .9, y - r * .5), r, w)
        pygame.draw.circle(surf, col, (x + r * .9, y - r * .5), r, w)
        pygame.draw.lines(surf, col, False, [(x - r * 2, y - r * .2), (x, y + s * .5), (x + r * 2, y - r * .2)], w)
    elif tag == "poison":     # snake
        pts = [(x - s * .5 + i * s / 10, y + math.sin(i * 1.1) * s * .25) for i in range(11)]
        pygame.draw.lines(surf, col, False, pts, w + 1)
        pygame.draw.circle(surf, col, pts[-1], w + 2)
    elif tag == "fire":       # flame
        pts = [(x, y - s * .55), (x + s * .3, y - s * .05), (x + s * .25, y + s * .4), (x, y + s * .5),
               (x - s * .25, y + s * .4), (x - s * .3, y - s * .05), (x - s * .05, y - s * .2)]
        pygame.draw.polygon(surf, col, pts, w)
    elif tag == "charm":      # star
        pts = []
        for i in range(10):
            r = s * (.5 if i % 2 == 0 else .2)
            a = -math.pi / 2 + i * math.pi / 5
            pts.append((x + math.cos(a) * r, y + math.sin(a) * r))
        pygame.draw.polygon(surf, col, pts, w)
    elif tag == "food":       # onigiri: rice triangle with nori band
        pts = [(x, y - s * .45), (x + s * .45, y + s * .4), (x - s * .45, y + s * .4)]
        pygame.draw.polygon(surf, col, pts, w)
        pygame.draw.rect(surf, col, (x - s * .15, y + s * .1, s * .3, s * .3))
    elif tag == "tool":       # 4-point shuriken
        pts = []
        for i in range(8):
            r = s * (.5 if i % 2 == 0 else .14)
            a = i * math.pi / 4
            pts.append((x + math.cos(a) * r, y + math.sin(a) * r))
        pygame.draw.polygon(surf, col, pts, w)
    elif tag == "scroll":     # rolled scroll
        pygame.draw.rect(surf, col, (x - s * .35, y - s * .3, s * .7, s * .6), w)
        pygame.draw.line(surf, col, (x - s * .5, y - s * .35), (x - s * .5, y + s * .35), w + 1)
        pygame.draw.line(surf, col, (x + s * .5, y - s * .35), (x + s * .5, y + s * .35), w + 1)
        for k in (-.12, 0, .12):
            pygame.draw.line(surf, col, (x - s * .2, y + s * k), (x + s * .2, y + s * k), 1)
    else:
        pygame.draw.line(surf, col, (x - s * .4, y - s * .4), (x + s * .4, y + s * .4), w)
        pygame.draw.line(surf, col, (x + s * .4, y - s * .4), (x - s * .4, y + s * .4), w)


def draw_item(surf, iid, shape, ox, oy, cell, alpha=230, highlight=None, level=1, rot=0):
    """Draw a tattoo shape with its top-left cell at (ox, oy)."""
    d = ITEMS[iid]
    tag = d["tags"][0]
    fill = TAG_COL.get(tag, (50, 50, 50))
    rc = RARITY_COL[d["rarity"]]
    cells = set(shape)
    layer = pygame.Surface((cell * 4, cell * 4), pygame.SRCALPHA)
    for (cx, cy) in cells:
        r = pygame.Rect(cx * cell + 3, cy * cell + 3, cell - 6, cell - 6)
        if (cx + 1, cy) in cells:
            r.width += 6
        if (cx, cy + 1) in cells:
            r.height += 6
        pygame.draw.rect(layer, fill + (alpha,), r, border_radius=10)
    for (cx, cy) in cells:   # rarity-coloured outline on outer edges only
        x0, y0, x1, y1 = cx * cell + 3, cy * cell + 3, (cx + 1) * cell - 3, (cy + 1) * cell - 3
        if (cx, cy - 1) not in cells:
            pygame.draw.line(layer, rc, (x0, y0), (x1, y0), 2)
        if (cx, cy + 1) not in cells:
            pygame.draw.line(layer, rc, (x0, y1), (x1, y1), 2)
        if (cx - 1, cy) not in cells:
            pygame.draw.line(layer, rc, (x0, y0), (x0, y1), 2)
        if (cx + 1, cy) not in cells:
            pygame.draw.line(layer, rc, (x1, y0), (x1, y1), 2)
    if highlight:
        for (cx, cy) in cells:
            pygame.draw.rect(layer, highlight, (cx * cell + 2, cy * cell + 2, cell - 4, cell - 4), 3,
                             border_radius=10)
    xs = [c[0] for c in cells]
    ys = [c[1] for c in cells]
    bw = (max(xs) - min(xs) + 1) * cell
    bh = (max(ys) - min(ys) + 1) * cell
    # fit the art to the item's UNrotated footprint, then turn it with the item (90 degrees per turn)
    pic = art(iid, int(min(bw, bh) * 0.78), int(max(bw, bh) * 0.78) if bw != bh else None)
    if pic and rot % 4:
        pic = pygame.transform.rotate(pic, -90 * (rot % 4))
    if pic:
        layer.blit(pic, pic.get_rect(center=(bw / 2, bh / 2)))
        surf.blit(layer, (ox, oy))
        draw_level(surf, level, ox, oy, cell)
        return
    gsize = min(bw, bh) * 0.62
    _glyph(layer, GLYPH.get(tag, tag), (bw / 2, bh / 2), gsize, LINE_COL.get(tag, TEXT))
    surf.blit(layer, (ox, oy))
    if cell < 50 and bw <= cell:            # small cell: a short label (the tooltip has the full name)
        word = d["name"].split()[0][:7]
        text(surf, word, (ox + bw / 2 + 1, oy + bh - 9), 10, (0, 0, 0), True, center=True)
        text(surf, word, (ox + bw / 2, oy + bh - 10), 10, TEXT, True, center=True)
        draw_level(surf, level, ox, oy, cell)
        return
    # name, with a dark shadow so it reads on top of the line art
    cx = ox + bw / 2
    cy = oy + bh / 2
    size = 13 if cell >= 50 else 11
    lines = wrap(d["name"], size, max(bw - 6, cell - 6), True)
    lh = font(size, True).get_height()
    y = cy - lh * len(lines) / 2 + (bh * 0.18 if bh > cell else 0)
    for ln in lines:
        text(surf, ln, (cx + 1, y + lh / 2 + 1), size, (0, 0, 0), True, center=True)
        text(surf, ln, (cx, y + lh / 2), size, TEXT, True, center=True)
        y += lh
    draw_level(surf, level, ox, oy, cell)


def draw_level(surf, level, ox, oy, cell):
    """Gold pips in the top-left corner: one per level above 1."""
    for k in range(max(0, level - 1)):
        c = (ox + 9 + k * 11, oy + 9)
        pygame.draw.circle(surf, (40, 28, 10), c, 5)
        pygame.draw.circle(surf, GOLD, c, 4)


def tooltip_lines(iid, eff=None):
    d = ITEMS[iid]
    st = eff if eff is not None else d
    return describe_stats(st)


# ---------------------------------------------------------------- tooltips that can be pinned
# Every tooltip registers itself as "the tooltip on screen this frame". Alt + right-click pins it (main.py):
# it stays put while you move the mouse, and hovering a keyword in it (Poison, Block...) explains that keyword.
TIP = {"frame": None, "pinned": None, "drawing": False, "kw": [], "rect": None}


def _offer(fn, *a, **k):
    if not TIP["drawing"]:
        TIP["frame"] = (fn, a, k)


def draw_pinned(surf):
    p = TIP["pinned"]
    if not p:
        return
    fn, a, k = p
    TIP["drawing"], TIP["kw"], TIP["rect"] = True, [], None
    try:
        fn(surf, *a, **k)
    finally:
        TIP["drawing"] = False
    r = TIP["rect"]
    if r is None:
        return
    badge = pygame.Rect(r.right - 92, r.y - 12, 84, 20)       # "pinned" badge on the frame
    pygame.draw.rect(surf, GOLD, badge, border_radius=6)
    text(surf, "PINNED", badge.center, 12, (30, 22, 10), True, center=True)
    hint = "Alt + right-click to release"
    text(surf, hint, (r.centerx, r.bottom + 10), 12, DIM, True, center=True)
    mouse = pygame.mouse.get_pos()
    for rr, key in TIP["kw"]:
        if rr.collidepoint(mouse):
            pygame.draw.rect(surf, GOLD, rr.inflate(4, 2), 1, border_radius=3)
            draw_keyword_popup(surf, key, mouse)
            break


def draw_keyword_popup(surf, key, mouse):
    """A small box explaining one keyword (Poison, Block, Stun...)."""
    from .keywords import KEYWORDS
    name, col, desc = KEYWORDS[key]
    lines = wrap(desc, 14, 276)
    h = 42 + (font(14).get_height() + 3) * len(lines)
    r = pygame.Rect(min(mouse[0] + 16, W - 312), min(mouse[1] + 16, H - h - 4), 300, h)
    panel(surf, r, PANEL, col)
    surf.blit(font(17, True, True).render(name, True, col), (r.x + 12, r.y + 8))
    text_block(surf, desc, (r.x + 12, r.y + 34), 276, 14, TEXT, spacing=3)


def tag_chips(surf, tags, pos, size=12, max_w=None):
    """Coloured tag chips (Weapon, Poison, Ki...). Returns the y below them."""
    x0, y = pos
    x = x0
    h = font(size, True).get_height() + 4
    for t in tags:
        label = TAG_INFO.get(t, (t.title(),))[0]
        w = font(size, True).size(label)[0] + 12
        if max_w and x > x0 and x + w > x0 + max_w:
            x, y = x0, y + h + 4
        col = TAG_CHIP.get(t, TEXT)
        r = pygame.Rect(x, y, w, h)
        pygame.draw.rect(surf, tuple(c // 5 for c in col), r, border_radius=5)
        pygame.draw.rect(surf, col, r, 1, border_radius=5)
        text(surf, label, (r.x + 6, r.y + 2), size, col, True)
        x = r.right + 5
    return y + h


def recipe_lines(iid):
    """What this item fuses into (and with what), or what it is made from."""
    out = []
    for partner, res in recipes_for(iid):
        out.append(f"+ {ITEMS[partner]['name']}  ->  {ITEMS[res]['name']}")
    src = recipe_of(iid)
    if src:
        out.append("Made from " + " + ".join(ITEMS[i]["name"] for i in src))
    return out


def draw_tooltip(surf, iid, rect, eff=None, price=None, extra=None, fight_stats=None, fit=False):
    """Item tooltip. Effect keywords are coloured + italic and explained at the bottom.
    fight_stats: optional list of lines ("this battle" numbers). fit=True grows/moves the box to fit."""
    from .keywords import keywords_in
    _offer(draw_tooltip, iid, rect, eff=eff, price=price, extra=extra, fight_stats=fight_stats, fit=fit)
    d = ITEMS[iid]
    rect = pygame.Rect(rect)
    layer = pygame.Surface((rect.width, 1000), pygame.SRCALPHA)
    hits = []
    x, y, wdt = 18, 14, rect.width - 36
    name = eff.get("name", d["name"]) if eff else d["name"]
    lvl = eff.get("level", 1) if eff else 1
    title = name if lvl <= 1 else f"{d['name']}  (level {lvl})"
    y = text_block(layer, title, (x, y), wdt, 21, RARITY_COL[d["rarity"]], spacing=2, bold=True) + 2
    # rarity + class line: "Rare  -  Samurai only" (exclusive) or "Rare  -  Samurai" (favoured, anyone can use it)
    r1 = text(layer, d["rarity"].title(), (x, y), 14, RARITY_COL[d["rarity"]], True)
    who = class_label(d)
    if who:
        cid = d.get("cls") or d.get("affinity")
        text(layer, "-", (r1.right + 8, y), 14, DIM)
        text(layer, who, (r1.right + 20, y), 14, CHARACTERS[cid]["color"], True)
    y += 22
    if d.get("affinity") and not d.get("cls"):
        y = text_block(layer, f"Favoured by the {CHARACTERS[d['affinity']]['name']}: offered to them more often. "
                              f"Any class can use it.", (x, y), wdt, 12, DIM, spacing=2) + 2
    if d.get("boss_relic"):
        y = text_block(layer, "Villain's relic - dropped only by the boss who carries it", (x, y), wdt, 13, GOLD,
                       spacing=2) + 2
    elif d.get("loot"):
        y = text_block(layer, "Enemy drop - never sold in shops", (x, y), wdt, 13, GOLD, spacing=2) + 2
    elif d.get("recipe"):
        y = text_block(layer, "Recipe item - made by fusing two items", (x, y), wdt, 13, (190, 150, 255),
                       spacing=2) + 2
    if not d["enemy"]:
        y = tag_chips(layer, d["tags"], (x, y + 2), 12, wdt) + 8
    else:
        y += 4
    lines = tooltip_lines(iid, eff)
    for ln in lines:
        y = rich_text_block(layer, ln, (x, y), wdt, 16, spacing=5, hits=hits)
    if eff is not None and eff.get("speed", 1.0) != 1.0:
        y = text_block(layer, f"(speed boosted x{eff['speed']:.2f} by neighbours)", (x, y), wdt, 14, GREEN)
    recipes = [] if d["enemy"] else recipe_lines(iid)
    if recipes:
        y += 6
        text(layer, "Recipe", (x, y), 15, (190, 150, 255), True)
        y += 21
        for ln in recipes:
            y = text_block(layer, ln, (x + 8, y), wdt - 8, 14, (215, 195, 255), spacing=2)
        if recipes_for(iid):
            y = text_block(layer, "Place the two side by side in your kit: they fuse after your next battle.",
                           (x + 8, y + 2), wdt - 8, 12, DIM, spacing=2)
    if fight_stats:
        y += 6
        text(layer, "This battle:", (x, y), 15, GOLD, True)
        y += 20
        for ln in fight_stats:
            y = rich_text_block(layer, ln, (x + 8, y), wdt - 8, 15, hits=hits)
    if price is not None:
        y += 6
        text(layer, f"Price: {price} ryō", (x, y), 16, GOLD, True)
        y += 22
    if not d["enemy"]:
        if price is None:
            y += 6
        text(layer, f"Sells for: {sell_value(iid, lvl)} ryō", (x, y), 15, (200, 170, 110))
        y += 20
    if extra:
        y += 4
        y = rich_text_block(layer, extra, (x, y), wdt, 14, DIM, spacing=3, hits=hits)
    keys = keywords_in(" ".join(lines + (fight_stats or [])))
    if keys:
        y += 6
        pygame.draw.line(layer, LINE, (x, y), (rect.width - 14, y), 1)
        y = keyword_glossary(layer, keys, (x, y + 6), wdt)
    h = y + 12
    if fit:
        rect.height = h
        rect.y = max(4, min(rect.y, H - h - 4))
    else:
        h = max(h, rect.height)
        rect.height = h
    panel(surf, rect, PANEL, RARITY_COL[d["rarity"]])
    surf.blit(layer, rect.topleft, (0, 0, rect.width, h))
    if TIP["drawing"]:
        TIP["rect"] = rect
        TIP["kw"] = [(r.move(rect.topleft), k) for r, k in hits if r.bottom <= h]
    return rect.y + h


def draw_info_tip(surf, title, body, col, mouse, sub=None, width=330):
    """A generic hover box (techniques, passives, villains...). Pinnable like item tooltips."""
    _offer(draw_info_tip, title, body, col, mouse, sub=sub, width=width)
    hits = []
    inner = width - 28
    layer = pygame.Surface((width, 700), pygame.SRCALPHA)
    y = text_block(layer, title, (14, 10), inner, 18, col, spacing=2, bold=True) + 2
    if sub:
        y = text_block(layer, sub, (14, y), inner, 12, DIM, spacing=2) + 4
    y = rich_text_block(layer, body, (14, y + 2), inner, 15, TEXT, spacing=4, hits=hits) + 10
    r = pygame.Rect(min(mouse[0] + 16, W - width - 8), 0, width, y)
    r.y = max(4, min(mouse[1] + 16, H - y - 4))
    panel(surf, r, PANEL, col)
    surf.blit(layer, r.topleft, (0, 0, width, y))
    if TIP["drawing"]:
        TIP["rect"] = r
        TIP["kw"] = [(rr.move(r.topleft), k) for rr, k in hits]
    return r


def bar(surf, rect, frac, col, back=(50, 40, 50)):
    pygame.draw.rect(surf, back, rect, border_radius=4)
    r = pygame.Rect(rect)
    r.width = int(r.width * max(0.0, min(1.0, frac)))
    if r.width > 0:
        pygame.draw.rect(surf, col, r, border_radius=4)


def portrait(surf, center, radius, col, glyph, style="enemy", key=None):
    """Pixel-art faceset in a framed circle; falls back to simple shapes if no art."""
    x, y = center
    r = radius
    pic = art(key, int(r * 1.5)) if key else None
    if pic:
        pygame.draw.circle(surf, (col[0] // 4, col[1] // 4, col[2] // 4), center, r)
        surf.blit(pic, pic.get_rect(center=center))
        pygame.draw.circle(surf, col, center, r, 4)
        return
    skin = (232, 196, 160)
    pygame.draw.circle(surf, (col[0] // 4, col[1] // 4, col[2] // 4), center, r)
    pygame.draw.circle(surf, col, center, r, 4)
    # shoulders
    pygame.draw.ellipse(surf, col, (x - r * .6, y + r * .38, r * 1.2, r * .55))
    if style == "samurai":
        pygame.draw.circle(surf, skin, (x, y), r * .32)
        # kabuto helmet + golden crest (kuwagata)
        pygame.draw.ellipse(surf, (40, 36, 44), (x - r * .45, y - r * .52, r * .9, r * .5))
        pygame.draw.lines(surf, GOLD, False, [(x - r * .4, y - r * .85), (x, y - r * .45),
                                              (x + r * .4, y - r * .85)], 4)
        pygame.draw.line(surf, (30, 20, 20), (x - r * .14, y), (x - r * .05, y), 3)
        pygame.draw.line(surf, (30, 20, 20), (x + r * .05, y), (x + r * .14, y), 3)
    elif style == "ninja":
        pygame.draw.circle(surf, (28, 30, 44), (x, y), r * .36)
        pygame.draw.rect(surf, skin, (x - r * .26, y - r * .08, r * .52, r * .14))
        pygame.draw.circle(surf, (20, 20, 20), (x - r * .1, y - r * .01), max(2, r * .05))
        pygame.draw.circle(surf, (20, 20, 20), (x + r * .1, y - r * .01), max(2, r * .05))
        pygame.draw.line(surf, col, (x + r * .3, y - r * .1), (x + r * .6, y - r * .3), 4)  # headband tail
    elif style == "kunoichi":
        pygame.draw.circle(surf, (24, 18, 26), (x, y - r * .12), r * .42)   # hair
        pygame.draw.circle(surf, skin, (x, y + r * .02), r * .3)
        pygame.draw.circle(surf, (24, 18, 26), (x, y - r * .5), r * .18)    # bun
        pygame.draw.line(surf, GOLD, (x - r * .35, y - r * .65), (x + r * .3, y - r * .38), 3)  # kanzashi
        pygame.draw.circle(surf, col, (x + r * .3, y - r * .38), max(3, r * .07))
        pygame.draw.circle(surf, (40, 20, 30), (x - r * .1, y + r * .02), max(2, r * .04))
        pygame.draw.circle(surf, (40, 20, 30), (x + r * .1, y + r * .02), max(2, r * .04))
        pygame.draw.circle(surf, RED, (x, y + r * .17), max(2, r * .04))
    else:  # villain: horned demon face
        pygame.draw.circle(surf, (150, 40, 40), (x, y), r * .36)
        pygame.draw.polygon(surf, (235, 225, 200), [(x - r * .3, y - r * .2), (x - r * .45, y - r * .7),
                                                    (x - r * .14, y - r * .3)])
        pygame.draw.polygon(surf, (235, 225, 200), [(x + r * .3, y - r * .2), (x + r * .45, y - r * .7),
                                                    (x + r * .14, y - r * .3)])
        pygame.draw.circle(surf, (255, 220, 80), (x - r * .13, y - r * .03), max(2, r * .06))
        pygame.draw.circle(surf, (255, 220, 80), (x + r * .13, y - r * .03), max(2, r * .06))
        pygame.draw.line(surf, (40, 10, 10), (x - r * .15, y + r * .17), (x + r * .15, y + r * .17), 3)


def draw_spirit(surf, inst, ox, oy, cell):
    """Soul-bound items get a purple gem; awakened tsukumogami get a slowly pulsing spirit outline."""
    if inst is None or not (getattr(inst, "infusion", None) or getattr(inst, "awakened", None)):
        return
    cells = set(inst.shape)
    if inst.awakened:
        import time
        a = int(150 + 90 * math.sin(time.time() * 3))
        glow = pygame.Surface((cell * 4, cell * 4), pygame.SRCALPHA)
        for cx, cy in cells:
            pygame.draw.rect(glow, (190, 150, 255, a), (cx * cell + 1, cy * cell + 1, cell - 2, cell - 2), 3,
                             border_radius=10)
        surf.blit(glow, (ox, oy))
    if inst.infusion:
        cx, cy = max(cells, key=lambda c: (c[0], -c[1]))          # top-right cell of the item
        gx, gy = ox + (cx + 1) * cell - 9, oy + cy * cell + 9
        pygame.draw.polygon(surf, (40, 20, 60), [(gx, gy - 7), (gx + 7, gy), (gx, gy + 7), (gx - 7, gy)])
        pygame.draw.polygon(surf, (190, 150, 255), [(gx, gy - 5), (gx + 5, gy), (gx, gy + 5), (gx - 5, gy)])
