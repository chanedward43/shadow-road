"""All screens of the game."""
import math
import random

import pygame

from . import ui
from .ui import W, H, text, text_block, panel, Button
from .data import ITEMS, CHARACTERS, STAGES, ENEMIES, TECHNIQUES, REST_HEAL, BUILDS, BALANCE
from . import save
from .run import RunState
from .combat import make_battle, effective_stats
from .events import pick_event, options_for, resolve

CUR = "ryō"


class Scene:
    def __init__(self, game):
        self.game = game
        self.buttons = []

    def handle(self, ev):
        for b in list(self.buttons):
            if b.handle(ev):
                return True
        return False

    def update(self, dt):
        pass

    def draw(self, s):
        pass

    def draw_buttons(self, s):
        for b in self.buttons:
            b.draw(s)


def top_bar(s, run, title=""):
    pygame.draw.rect(s, ui.PANEL, (0, 0, W, 48))
    pygame.draw.line(s, ui.LINE, (0, 48), (W, 48), 2)
    ch = CHARACTERS[run.char_id]
    text(s, ch["name"], (16, 11), 20, ch["color"], True)
    text(s, f"HP {run.hp}/{run.max_hp}", (160, 11), 20, ui.RED, True)
    text(s, f"{run.gold} {CUR}", (330, 11), 20, ui.GOLD, True)
    st = STAGES[run.stage]
    text(s, f"Stage {run.stage}/3 - {st['name']}", (460, 11), 20, ui.TEXT, True)
    if title:
        text(s, title, (W - 16, 11), 20, ui.DIM, True, right=True)


def draw_petals(s, t, n=45):
    for i in range(n):
        x = (i * 137 + t * (14 + i % 5) * 3) % W
        y = (i * 89 + t * (18 + i % 7) * 3) % H
        pygame.draw.ellipse(s, (230, 150, 180) if i % 3 else (190, 110, 140), (int(x), int(y), 6, 4))


# =================================================================== title
class TitleScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.t = 0
        self.buttons = [
            Button((W // 2 - 130, 400, 260, 56), "New Journey", lambda: game.change(CharSelectScene(game)), 24),
            Button((W // 2 - 130, 540, 260, 56), "Quit", game.quit, 24),
        ]
        self.saved = save.load_run()
        self.buttons.insert(1, Button((W // 2 - 130, 470, 260, 56), "Continue", self.resume, 24,
                                      enabled=self.saved is not None))

    def resume(self):
        self.game.run = self.saved
        self.game.change(MapScene(self.game))

    def update(self, dt):
        self.t += dt

    def draw(self, s):
        s.fill(ui.BG)
        draw_petals(s, self.t)
        pygame.draw.circle(s, (170, 40, 40), (W // 2, 205), 150)       # rising sun
        pygame.draw.circle(s, ui.BG, (W // 2, 205), 138)
        text(s, "SHADOW ROAD", (W // 2, 200), 84, ui.GOLD, True, center=True)
        text(s, "Pack your blade. Walk the road. Cut down the demons of old Japan.", (W // 2, 290), 22,
             ui.DIM, center=True)
        text(s, "Art: Ninja Adventure pack by Pixel-Boy & AAA (CC0)", (W // 2, 330), 16, ui.DIM, center=True)
        self.draw_buttons(s)


# =================================================================== character select
class CharSelectScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.ids = list(CHARACTERS)
        self.sel = None
        n = len(self.ids)
        cw = (W - 40 - (n - 1) * 10) // n
        self.cards = [pygame.Rect(20 + i * (cw + 10), 80, cw, 545) for i in range(n)]
        self.begin = Button((W // 2 - 140, 640, 280, 54), "Set Out", self.start, 24, enabled=False)
        self.buttons = [self.begin, Button((20, 650, 120, 44), "Back", lambda: game.change(TitleScene(game)))]

    def start(self):
        self.game.run = RunState(self.ids[self.sel])
        self.game.change(StageScene(self.game, first=True))

    def handle(self, ev):
        if super().handle(ev):
            return True
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for i, r in enumerate(self.cards):
                if r.collidepoint(ev.pos):
                    self.sel = i
                    self.begin.enabled = True
        return False

    def draw(self, s):
        s.fill(ui.BG)
        text(s, "Choose your path", (W // 2, 45), 34, ui.TEXT, True, center=True)
        for i, (cid, r) in enumerate(zip(self.ids, self.cards)):
            ch = CHARACTERS[cid]
            hover = r.collidepoint(pygame.mouse.get_pos())
            border = ui.GOLD if i == self.sel else (ch["color"] if hover else ui.LINE)
            panel(s, r, ui.PANEL, border, width=3 if i == self.sel else 2)
            ui.portrait(s, (r.centerx, r.y + 62), 50, ch["color"], ch["glyph"], ch["portrait"], key=cid)
            y = r.y + 122
            text(s, ch["name"], (r.centerx, y), 24, ch["color"], True, center=True)
            y += 24
            text(s, ch["style"], (r.centerx, y), 13, ui.DIM, center=True)
            y += 20
            hp = int(round(ch["hp"] * BALANCE.get("class_hp", {}).get(cid, 1.0)))
            text(s, f"HP {hp}", (r.centerx, y), 16, ui.RED, True, center=True)
            y += 20
            y = text_block(s, ch["passive"], (r.x + 12, y), r.width - 24, 13, ui.GOLD) + 6
            text(s, "Starting kit:", (r.x + 12, y), 13, ui.TEXT, True)
            y += 18
            for iid in ch["start"]:
                text(s, "- " + ITEMS[iid]["name"], (r.x + 18, y), 13, ui.TEXT)
                y += 17
            y += 6
            text(s, "Build paths:", (r.x + 12, y), 13, ui.TEXT, True)
            y += 18
            for b in BUILDS.get(cid, []):
                name, _, rest = b.partition(":")
                y = text_block(s, name, (r.x + 12, y), r.width - 24, 13, ui.GREEN, bold=True)
                y = text_block(s, rest.strip(), (r.x + 12, y), r.width - 24, 12, ui.DIM) + 4
        self.draw_buttons(s)


# =================================================================== map
NODE_STYLE = {
    "fight": ((150, 70, 70), "Fight"), "elite": ((200, 60, 160), "Elite"),
    "shop": ((220, 180, 80), "Merchant"), "rest": ((90, 170, 110), "Onsen"),
    "treasure": ((90, 160, 230), "Shrine"), "event": ((150, 100, 210), "?"),
    "boss": ((230, 50, 50), "BOSS"),
}


NODE_ART = {"fight": "map_fight", "elite": "map_elite", "boss": "map_boss", "event": "map_event",
            "shop": "map_shop", "rest": "map_rest", "treasure": "map_shrine"}


class MapScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.run = game.run
        self.t = 0
        save.save_run(self.run)
        self.buttons = [Button((W - 210, H - 70, 190, 50), "Your Kit", self.open_bag)]

    def open_bag(self):
        self.game.change(InventoryScene(self.game, "manage", on_done=lambda: MapScene(self.game)))

    def node_pos(self, r, node):
        return int(100 + r * 140), int(130 + node["x"] * 470)

    def node_at(self, pos, only_available=True):
        nodes = self.run.available_nodes() if only_available else \
            [(r, c) for r, row in enumerate(self.run.map) for c in range(len(row))]
        for rc in nodes:
            x, y = self.node_pos(rc[0], self.run.node(rc))
            if math.hypot(pos[0] - x, pos[1] - y) < 30:
                return rc
        return None

    def handle(self, ev):
        if super().handle(ev):
            return True
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            rc = self.node_at(ev.pos)
            if rc:
                self.enter(rc)
                return True
        return False

    def enter(self, rc):
        g, run = self.game, self.run
        node = run.visit(rc)
        kind = node["kind"]
        if kind in ("fight", "elite", "boss"):
            g.change(BattleScene(g, run.pick_enemy(kind), kind, run.enemy_scale(kind)))
        elif kind == "shop":
            g.change(InventoryScene(g, "shop", offers=run.shop_offers(),
                                    on_done=lambda: MapScene(g), title="Travelling Merchant"))
        elif kind == "treasure":
            gold = run.gold_reward("fight")
            g.change(InventoryScene(g, "reward", offers=run.reward_choices("treasure"),
                                    on_done=lambda: MapScene(g), title="Roadside Shrine",
                                    message=f"An offering of {gold} {CUR}. The kami grant one item."))
        elif kind == "rest":
            g.change(RestScene(g))
        elif kind == "event":
            g.change(EventScene(g, pick_event(run)))

    def update(self, dt):
        self.t += dt

    def draw(self, s):
        s.fill(ui.BG)
        run = self.run
        top_bar(s, run, "Choose your path")
        st = STAGES[run.stage]
        text(s, st["name"], (30, 58), 24, ui.GOLD, True)
        text(s, st["subtitle"], (30, 88), 15, ui.DIM)
        avail = set(run.available_nodes())
        for r, row in enumerate(run.map[:-1]):
            for node in row:
                a = self.node_pos(r, node)
                for j in node["links"]:
                    b = self.node_pos(r + 1, run.map[r + 1][j])
                    on_path = node.get("visited") and run.map[r + 1][j].get("visited")
                    pygame.draw.line(s, ui.GOLD if on_path else ui.LINE, a, b, 3 if on_path else 2)
        for r, row in enumerate(run.map):
            for c, node in enumerate(row):
                x, y = self.node_pos(r, node)
                col, label = NODE_STYLE[node["kind"]]
                rad = 36 if node["kind"] == "boss" else 27
                is_av = (r, c) in avail
                if is_av:
                    pulse = 4 + 3 * math.sin(self.t * 5)
                    pygame.draw.circle(s, ui.GOLD, (x, y), int(rad + pulse), 2)
                dim = not is_av and not node.get("visited")
                fill = tuple(v // 3 for v in col) if dim else col
                if node.get("visited"):
                    fill = (60, 56, 70)
                pygame.draw.circle(s, fill, (x, y), rad)
                pygame.draw.circle(s, ui.TEXT if is_av else ui.LINE, (x, y), rad, 2)
                pic = ui.art(NODE_ART.get(node["kind"], ""), int(rad * 1.25))
                if pic:
                    if dim:
                        pic = pic.copy()
                        pic.set_alpha(110)
                    s.blit(pic, pic.get_rect(center=(x, y)))
                    if is_av and node["kind"] != "boss":
                        text(s, label, (x, y + rad + 11), 12, ui.TEXT, True, center=True)
                else:
                    text(s, label, (x, y), 12 if len(label) > 6 else (18 if rad > 30 else 14), ui.TEXT, True,
                         center=True)
        # boss name under the boss node (readability: you always know what you're preparing for)
        boss = ENEMIES[run.boss_id()]
        bx, by = self.node_pos(len(run.map) - 1, run.map[-1][0])
        text(s, boss["name"].split(",")[0], (bx, by + 50), 15, ui.RED, True, center=True)

        # right column: legend + techniques + hovered node info
        lx, ly = W - 250, 62
        panel(s, (lx - 10, ly - 6, 240, 246))
        tips = {"fight": "Enemy", "elite": "Tough foe + technique", "shop": "Buy & sell",
                "rest": "Heal or train", "treasure": "Free item", "event": "Mystery event",
                "boss": "Stage villain"}
        for i, (k, (col, label)) in enumerate(NODE_STYLE.items()):
            yy = ly + 4 + i * 34
            pygame.draw.circle(s, col, (lx + 12, yy + 9), 10)
            text(s, f"{label}: {tips[k]}", (lx + 30, yy), 14, ui.DIM)
        y = ly + 254
        text(s, "Techniques", (lx, y), 18, ui.TEXT, True)
        y += 26
        if not run.techniques:
            y = text_block(s, "None yet. Defeat elites and bosses to learn them.", (lx, y), 225, 14, ui.DIM)
        for tid in run.techniques:
            text(s, "- " + TECHNIQUES[tid]["name"], (lx, y), 15, ui.GOLD)
            y += 20
        hov = self.node_at(pygame.mouse.get_pos(), only_available=False)
        if hov and self.run.node(hov)["kind"] in ("boss", "elite"):
            kind = self.run.node(hov)["kind"]
            names = [run.boss_id()] if kind == "boss" else st["elites"]
            y += 12
            for eid in names:
                e = ENEMIES[eid]
                text(s, e["name"], (lx, y), 15, ui.RED, True)
                y = text_block(s, e.get("desc", ""), (lx, y + 20), 225, 13, ui.DIM) + 6
        text(s, f"Battles won: {run.battles_won}    Seed {run.seed}", (30, H - 40), 16, ui.DIM)
        self.draw_buttons(s)


# =================================================================== inventory / shop / reward
CELL = 56


class InventoryScene(Scene):
    """mode: 'shop' (buy offers), 'reward' (take one offer free), 'manage' (just arrange)."""

    def __init__(self, game, mode, offers=None, on_done=None, title="", message="", drops=()):
        super().__init__(game)
        self.drops = set(drops)
        self.run = game.run
        self.mode = mode
        self.offers = list(offers or [])
        self.on_done = on_done
        self.title = title or {"manage": "Your kit", "shop": "Merchant", "reward": "Spoils"}[mode]
        self.message = message
        self.flash_msg = ""
        self.flash_t = 0
        self.held = None
        self.highlight = {}
        self.bag_o = (30, 300)
        self.stash_o = (470, 300)
        self.sell_rect = pygame.Rect(470, 540, 6 * CELL, 70)
        self.offer_rects = [pygame.Rect(30 + i * 162, 92, 152, 188) for i in range(len(self.offers))]
        label = {"manage": "Done", "shop": "Leave", "reward": "Continue"}[mode]
        self.buttons = [Button((W - 230, H - 70, 210, 52), label, self.done, 22)]
        if mode == "shop":
            self.reroll_btn = Button((850, 228, 180, 44), "", self.reroll, 18)
            self.buttons.append(self.reroll_btn)

    # ---------- actions
    def done(self):
        if self.held:
            self.return_held()
        self.game.change(self.on_done())

    def reroll_cost(self):
        return 1 + self.run.rerolls // 2

    def reroll(self):
        c = self.reroll_cost()
        if self.run.gold >= c:
            self.run.gold -= c
            self.run.rerolls += 1
            self.offers = self.run.shop_offers()
            self.offer_rects = [pygame.Rect(30 + i * 162, 92, 152, 188) for i in range(len(self.offers))]

    def say(self, msg):
        self.flash_msg, self.flash_t = msg, 2.5

    def click_offer(self, i):
        iid = self.offers[i]
        if iid is None:
            return
        price = ITEMS[iid]["price"]
        if self.mode == "shop":
            if self.run.gold < price:
                return self.say(f"Not enough {CUR}.")
            if not self.run.add_item(iid):
                return self.say("No room! Pawn something or rearrange.")
            self.run.gold -= price
            self.offers[i] = None
        elif self.mode == "reward":
            if not self.run.add_item(iid):
                return self.say("No room! Pawn something or rearrange.")
            self.offers = [None] * len(self.offers)
            self.say(f"Took {ITEMS[iid]['name']}.")

    def grid_at(self, pos):
        for grid, o in ((self.run.bag, self.bag_o), (self.run.stash, self.stash_o)):
            gx = (pos[0] - o[0]) // CELL
            gy = (pos[1] - o[1]) // CELL
            if 0 <= gx < grid.w and 0 <= gy < grid.h:
                return grid, o, int(gx), int(gy)
        return None

    def pick_up(self, pos):
        hit = self.grid_at(pos)
        if not hit:
            return
        grid, o, gx, gy = hit
        inst = grid.item_at(gx, gy)
        if not inst:
            return
        grid.remove(inst)
        off = (pos[0] - (o[0] + inst.x * CELL), pos[1] - (o[1] + inst.y * CELL))
        self.held = dict(inst=inst, grid=grid, x=inst.x, y=inst.y, rot=inst.rot, off=off)

    def held_topleft(self, pos):
        return pos[0] - self.held["off"][0], pos[1] - self.held["off"][1]

    def drop_target(self, pos):
        tlx, tly = self.held_topleft(pos)
        for grid, o in ((self.run.bag, self.bag_o), (self.run.stash, self.stash_o)):
            gx = round((tlx - o[0]) / CELL)
            gy = round((tly - o[1]) / CELL)
            r = pygame.Rect(o[0] - CELL, o[1] - CELL, (grid.w + 2) * CELL, (grid.h + 2) * CELL)
            if r.collidepoint(pos):
                return grid, o, gx, gy
        return None

    def drop(self, pos):
        inst = self.held["inst"]
        if self.sell_rect.collidepoint(pos):
            value = max(1, ITEMS[inst.id]["price"] // 2)
            self.run.gold += value
            self.say(f"Pawned {ITEMS[inst.id]['name']} for {value} {CUR}.")
            self.held = None
            return
        hit = self.grid_at(pos)
        other = hit[0].item_at(hit[2], hit[3]) if hit else None
        if other and self.run.can_merge(other, inst):
            other.level += 1
            self.held = None
            self.say(f"Merged! {ITEMS[other.id]['name']} is now level {other.level}.")
            return
        tgt = self.drop_target(pos)
        if tgt and tgt[0].place(inst, tgt[2], tgt[3]):
            self.held = None
            return
        if other and other.id == inst.id:
            self.say("Only items of the same level can merge (max level 3).")
        self.return_held()

    def return_held(self):
        h = self.held
        inst = h["inst"]
        inst.rot = h["rot"]
        if not h["grid"].place(inst, h["x"], h["y"]):
            if not h["grid"].first_fit(inst):
                self.run.stash.first_fit(inst) or self.run.bag.first_fit(inst)
        self.held = None

    def rotate_held(self):
        if self.held:
            self.held["inst"].rot = (self.held["inst"].rot + 1) % 4
            self.held["off"] = (CELL // 2, CELL // 2)

    def handle(self, ev):
        if self.held is None and super().handle(ev):
            return True
        if ev.type == pygame.MOUSEBUTTONDOWN:
            if ev.button == 1:
                if self.held:
                    self.drop(ev.pos)
                    return True
                for i, r in enumerate(self.offer_rects):
                    if r.collidepoint(ev.pos):
                        self.click_offer(i)
                        return True
                self.pick_up(ev.pos)
            elif ev.button == 3:
                self.rotate_held()
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1 and self.held:
            h = self.held
            o = self.bag_o if h["grid"] is self.run.bag else self.stash_o
            start = (o[0] + h["x"] * CELL + h["off"][0], o[1] + h["y"] * CELL + h["off"][1])
            if math.hypot(ev.pos[0] - start[0], ev.pos[1] - start[1]) > 12:
                self.drop(ev.pos)
        elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_r:
            self.rotate_held()
        elif ev.type == pygame.MOUSEWHEEL:
            self.rotate_held()
        return False

    def update(self, dt):
        self.flash_t = max(0, self.flash_t - dt)
        if self.mode == "shop":
            c = self.reroll_cost()
            self.reroll_btn.label = f"Reroll ({c})"
            self.reroll_btn.enabled = self.run.gold >= c

    # ---------- drawing
    def draw_grid(self, s, grid, o, label, active):
        text(s, label, (o[0], o[1] - 26), 17, ui.TEXT if active else ui.DIM, True)
        for y in range(grid.h):
            for x in range(grid.w):
                r = pygame.Rect(o[0] + x * CELL, o[1] + y * CELL, CELL, CELL)
                if active:   # tatami mat
                    shade = 10 if (x + y) % 2 else 0
                    pygame.draw.rect(s, (184 - shade, 170 - shade, 112 - shade), r)
                    pygame.draw.rect(s, (120, 108, 64), r, 1)
                else:        # wooden travel chest
                    pygame.draw.rect(s, (92, 66, 44), r)
                    pygame.draw.rect(s, (64, 44, 28), r, 1)
        for inst in grid.items:
            ui.draw_item(s, inst.id, inst.shape, o[0] + inst.x * CELL, o[1] + inst.y * CELL, CELL,
                         highlight=self.highlight.get(inst.uid), level=inst.level)

    def draw(self, s):
        s.fill(ui.BG)
        run = self.run
        top_bar(s, run, self.title)
        mouse = pygame.mouse.get_pos()
        eff = effective_stats(run.bag, run.char_id, run.techniques)
        hover_tip = None
        self.highlight = {}

        hit = None if self.held else self.grid_at(mouse)
        if hit:
            inst = hit[0].item_at(hit[2], hit[3])
            if inst:
                in_bag = hit[0] is run.bag
                hover_tip = (inst.id, eff.get(inst.uid) if in_bag else inst.data, None,
                             None if in_bag else "In travel chest: NOT used in battle.")
                if inst.level < 3:
                    hover_tip = hover_tip[:3] + ((hover_tip[3] + " " if hover_tip[3] else "")
                                                 + "Drop an identical copy on it to level it up.",)
                self.highlight[inst.uid] = ui.TEXT
                if in_bag and inst.data.get("aura"):
                    for nb in run.bag.neighbors(inst):
                        self.highlight[nb.uid] = ui.GREEN

        if self.offers:
            head = {"shop": "For sale - click to buy", "reward": "Choose ONE - click to take"}.get(self.mode, "")
            text(s, head, (30, 60), 18, ui.GOLD, True)
            if self.message:
                text(s, self.message, (300, 62), 16, ui.DIM)
        for i, (iid, r) in enumerate(zip(self.offers, self.offer_rects)):
            if iid is None:
                panel(s, r, (24, 22, 30), ui.LINE)
                text(s, "-", r.center, 30, ui.LINE, center=True)
                continue
            d = ITEMS[iid]
            hov = r.collidepoint(mouse) and not self.held
            panel(s, r, ui.PANEL2 if hov else ui.PANEL, ui.RARITY_COL[d["rarity"]])
            shp = d["shape"]
            cs = 36
            w = (max(c[0] for c in shp) + 1) * cs
            h = (max(c[1] for c in shp) + 1) * cs
            ui.draw_item(s, iid, shp, r.centerx - w // 2, r.y + 8 + (116 - h) // 2, cs)
            text(s, d["name"], (r.centerx, r.bottom - 52), 14, ui.TEXT, True, center=True)
            if self.mode == "shop":
                col = ui.GOLD if run.gold >= d["price"] else ui.RED
                text(s, f"{d['price']} {CUR}", (r.centerx, r.bottom - 26), 16, col, True, center=True)
            else:
                text(s, "ENEMY DROP" if iid in self.drops else "FREE", (r.centerx, r.bottom - 26), 16,
                     ui.GOLD if iid in self.drops else ui.GREEN, True, center=True)
            if hov:
                hover_tip = (iid, None, d["price"] if self.mode == "shop" else None, None)
        if not self.offers:
            text(s, "Arrange your kit. Only items on the TATAMI are equipped and fight for you.", (30, 70), 18,
                 ui.DIM)
            text(s, "Touching items can buff each other (hover one to see its neighbours).", (30, 96), 16,
                 ui.DIM)

        self.draw_grid(s, run.bag, self.bag_o, "KIT  (equipped - fights for you)", True)
        self.draw_grid(s, run.stash, self.stash_o, "TRAVEL CHEST  (not equipped)", False)

        hov_sell = self.sell_rect.collidepoint(mouse) and self.held
        panel(s, self.sell_rect, (70, 30, 30) if hov_sell else (40, 26, 30), ui.RED if hov_sell else ui.LINE)
        text(s, "PAWN: drop here to sell (half price)", self.sell_rect.center, 16, ui.TEXT, True, center=True)

        rp = pygame.Rect(850, 290, 410, 330)
        if self.held:
            hover_tip = (self.held["inst"].id, None, None, "Right-click / R / wheel to rotate.")
        if hover_tip:
            ui.draw_tooltip(s, hover_tip[0], rp, eff=hover_tip[1], price=hover_tip[2], extra=hover_tip[3])
        else:
            ch = CHARACTERS[run.char_id]
            panel(s, rp)
            y = rp.y + 12
            text(s, ch["name"], (rp.x + 14, y), 20, ch["color"], True)
            y += 30
            y = text_block(s, ch["passive"], (rp.x + 14, y), rp.width - 28, 15, ui.GOLD) + 8
            for tid in run.techniques:
                y = text_block(s, f"{TECHNIQUES[tid]['name']}: {TECHNIQUES[tid]['desc']}", (rp.x + 14, y),
                               rp.width - 28, 14, ui.GREEN)
            y += 6
            for ln in ["Click / drag to move. Right-click, R or wheel: rotate.",
                       "Drop on Pawn to sell. Hover anything for details."]:
                text(s, ln, (rp.x + 14, y), 14, ui.DIM)
                y += 20

        if self.held:
            inst = self.held["inst"]
            tgt = self.drop_target(mouse)
            if tgt:
                grid, o, gx, gy = tgt
                ok = grid.can_place(inst, gx, gy)
                for cx, cy in inst.cells_at(gx, gy):
                    if 0 <= cx < grid.w and 0 <= cy < grid.h:
                        r = pygame.Rect(o[0] + cx * CELL, o[1] + cy * CELL, CELL, CELL)
                        g = pygame.Surface(r.size, pygame.SRCALPHA)
                        g.fill((80, 220, 100, 70) if ok else (230, 60, 60, 80))
                        s.blit(g, r)
            tl = self.held_topleft(mouse)
            ui.draw_item(s, inst.id, inst.shape, tl[0], tl[1], CELL, alpha=200, level=inst.level)

        if self.flash_t > 0:
            text(s, self.flash_msg, (W // 2, H - 40), 20, ui.GOLD, True, center=True)
        if self.held is None:
            self.draw_buttons(s)


# =================================================================== techniques
class TechniqueScene(Scene):
    """Pick 1 of 3 permanent class upgrades (after elites and bosses)."""

    def __init__(self, game, then):
        super().__init__(game)
        self.run = game.run
        self.then = then
        self.choices = self.run.technique_choices()
        if not self.choices:
            self.choices = []
        n = len(self.choices)
        self.cards = [pygame.Rect(W // 2 - n * 190 + i * 380 + 10, 200, 360, 280) for i in range(n)]
        self.buttons = [Button((W // 2 - 100, 560, 200, 50), "Skip", lambda: game.change(then()))]

    def handle(self, ev):
        if super().handle(ev):
            return True
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for tid, r in zip(self.choices, self.cards):
                if r.collidepoint(ev.pos):
                    self.run.learn(tid)
                    self.game.change(self.then())
                    return True
        return False

    def draw(self, s):
        s.fill(ui.BG)
        top_bar(s, self.run, "Learn a technique")
        text(s, "Your skill grows. Learn a technique:", (W // 2, 130), 30, ui.GOLD, True, center=True)
        if not self.choices:
            text(s, "You have mastered every technique.", (W // 2, 300), 22, ui.DIM, center=True)
        for tid, r in zip(self.choices, self.cards):
            d = TECHNIQUES[tid]
            hov = r.collidepoint(pygame.mouse.get_pos())
            panel(s, r, ui.PANEL2 if hov else ui.PANEL, ui.GOLD if hov else ui.LINE, width=3 if hov else 2)
            text(s, d["name"], (r.centerx, r.y + 50), 26, ui.GOLD, True, center=True)
            text_block(s, d["desc"], (r.x + 24, r.y + 100), r.width - 48, 18)
        self.draw_buttons(s)


# =================================================================== battle
def intent_chips(st):
    chips = []
    if st.get("dmg"):
        hits = f" x{st['hits']}" if st.get("hits", 1) > 1 else ""
        chips.append((f"ATTACK {st['dmg'][0]}-{st['dmg'][1]}{hits}", (230, 90, 90)))
    if st.get("sunder"):
        chips.append(("BREAK ARMOR", (150, 180, 255)))
    if st.get("stun"):
        chips.append((f"STUN {st['stun']:.1f}s", ui.GOLD))
    if st.get("block"):
        chips.append((f"DEFEND {st['block']}", ui.BLUE))
    if st.get("poison"):
        chips.append((f"POISON {st['poison']}", ui.POISON))
    if st.get("burn"):
        chips.append((f"BURN {st['burn']}", ui.BURN))
    if st.get("heal"):
        chips.append((f"HEAL {st['heal']}", ui.GREEN))
    if st.get("dodge"):
        chips.append((f"EVADE x{st['dodge']}", (200, 200, 255)))
    if st.get("lifesteal"):
        chips.append(("DRAIN", (200, 90, 160)))
    return chips


class BattleScene(Scene):
    def __init__(self, game, enemy_id, kind, scale=1.0):
        super().__init__(game)
        self.run = run = game.run
        self.kind = kind
        self.enemy_id = enemy_id
        self.battle = make_battle(run, enemy_id, scale, seed=run.rng.randrange(1 << 30))
        self.pf, self.ef = self.battle.f
        self.speed = 1
        self.floats = []
        self.banner = ""
        self.banner_t = 0
        self.finished = False
        self.result_text = ""
        self.panels = [pygame.Rect(20, 60, 610, 560), pygame.Rect(650, 60, 610, 560)]
        self.speed_btns = []
        for i, sp in enumerate((1, 2, 4)):
            b = Button((20 + i * 90, 640, 80, 50), f"{sp}x", lambda sp=sp: self.set_speed(sp))
            self.speed_btns.append(b)
        self.skip_btn = Button((300, 640, 110, 50), "Skip", self.skip)
        self.cont_btn = Button((W - 230, 640, 210, 50), "Continue", self.cont, 22)
        self.buttons = self.speed_btns + [self.skip_btn]
        self.start_delay = 0.8

    def set_speed(self, sp):
        self.speed = sp

    def skip(self):
        self.battle.run_to_end()
        self.battle.events.clear()

    def cont(self):
        g, run = self.game, self.run
        run.hp = max(0, min(run.max_hp, self.pf.hp))
        if self.battle.winner != 0:
            g.change(EndScene(g, False))
            return
        run.battles_won += 1
        run.kills.append(self.enemy_id)
        gold = run.gold_reward(self.kind)
        drop = run.loot_of(self.enemy_id)
        if self.kind == "boss" and run.stage >= 3:
            g.change(EndScene(g, True))
            return

        def after_reward():
            if self.kind == "boss":
                run.next_stage()
                return StageScene(g)
            return MapScene(g)

        def reward():
            # regular enemies: their drop is one of the choices. Elites & bosses: drop is free, then pick one.
            msg = f"Victory! +{gold} {CUR}. Take one - the first is what the enemy dropped."
            offers = run.reward_choices(self.kind)
            if drop and self.kind == "fight":
                offers = [drop] + offers[:2]
            elif drop:
                got = run.add_item(drop)
                msg = (f"+{gold} {CUR}. It dropped {ITEMS[drop]['name']}"
                       + (" (in your chest)." if got else " but you had no room!") + " Now take one more.")
            return InventoryScene(g, "reward", offers=offers, on_done=after_reward, title="Spoils", message=msg,
                                  drops=[drop] if drop and self.kind == "fight" else [])

        if self.kind in ("elite", "boss"):
            g.change(TechniqueScene(g, then=reward))
        else:
            g.change(reward())

    def float_text(self, side, s, col, size=22):
        x = self.panels[side].x + 330 + random.randint(-110, 110)
        y = self.panels[side].y + 200 + random.randint(-15, 15)
        self.floats.append(dict(x=x, y=y, s=s, col=col, life=1.1, size=size))

    def update(self, dt):
        if self.start_delay > 0:
            self.start_delay -= dt
        elif not self.battle.done:
            self.battle.advance(dt * self.speed)
        for e in self.battle.events:
            k, side, a = e["kind"], e["side"], e["amount"]
            if k == "hit":
                self.float_text(side, f"{'CRIT ' if e['crit'] else ''}-{a}", ui.RED, 30 if e["crit"] else 22)
            elif k == "poison":
                self.float_text(side, f"-{a}", ui.POISON)
            elif k == "burn":
                self.float_text(side, f"-{a}", ui.BURN)
            elif k == "thorns":
                self.float_text(side, f"-{a} thorns", (200, 120, 120), 18)
            elif k == "fatigue":
                self.float_text(side, f"-{a} fatigue", (180, 120, 220), 18)
            elif k == "heal":
                self.float_text(side, f"+{a}", ui.GREEN)
            elif k == "block":
                self.float_text(side, f"+{a} block", ui.BLUE, 18)
            elif k == "evade":
                self.float_text(side, "EVADE", (200, 200, 255), 22)
            elif k == "sunder":
                self.float_text(side, e["text"], (150, 180, 255), 20)
            elif k == "stun":
                self.float_text(side, e["text"], ui.GOLD, 20)
            elif k == "summon" and e["text"]:
                self.float_text(side, e["text"], (120, 210, 230), 18)
            elif k == "summon":
                self.float_text(side, f"-{a}", (120, 210, 230), 18)
            elif k in ("hex", "kiburst", "counter"):
                label = {"hex": "HEX", "kiburst": "KI BURST", "counter": "COUNTER"}[k]
                self.float_text(side, f"{label} -{a}", (255, 170, 90) if k != "hex" else (170, 120, 220),
                                26 if k == "kiburst" else 20)
            elif k == "phase":
                self.banner, self.banner_t = e["text"], 3.0
        self.battle.events.clear()
        self.banner_t = max(0, self.banner_t - dt)
        for f in self.floats:
            f["life"] -= dt
            f["y"] -= 40 * dt
        self.floats = [f for f in self.floats if f["life"] > 0]
        if self.battle.done and not self.finished:
            self.finished = True
            self.result_text = "VICTORY" if self.battle.winner == 0 else "DEFEAT"
            self.buttons = [self.cont_btn]

    def draw_fighter(self, s, side, f, mouse):
        r = self.panels[side]
        panel(s, r, ui.PANEL, (120, 40, 40) if f.stun_t > 0 else ui.LINE, width=4 if f.stun_t > 0 else 2)
        ui.portrait(s, (r.x + 90, r.y + 100), 62, f.color, f.glyph, f.portrait,
                    key=self.run.char_id if side == 0 else self.enemy_id)
        x = r.x + 180
        text(s, f.name, (x, r.y + 20), 22 if len(f.name) < 24 else 17, ui.TEXT, True)
        ui.bar(s, (x, r.y + 60, 400, 26), f.hp / max(1, f.max_hp), ui.RED)
        if f.block:
            ui.bar(s, (x, r.y + 88, 400, 6), min(1, f.block / max(1, f.max_hp)), ui.BLUE)
        text(s, f"{max(0, f.hp)} / {f.max_hp}", (x + 200, r.y + 73), 17, ui.TEXT, True, center=True)
        sx = x
        for label, val, col in (("Block", f.block, ui.BLUE), ("Poison", f.poison, ui.POISON),
                                ("Burn", f.burn, ui.BURN), ("Regen", f.regen, ui.GREEN),
                                ("Thorns", f.thorns, (200, 120, 120)), ("Dodge", f.dodge, (200, 200, 255)),
                                ("Resolve", f.resolve, ui.GOLD), ("Ki", f.ki, (255, 200, 120)),
                                ("Counter", f.counter + f.ki // 2 if f.counter else 0, (255, 170, 90)),
                                ("Curse", f.curse, (170, 120, 220)), ("Shikigami", len(f.summons), (120, 210, 230))):
            if val:
                rr = text(s, f"{label} {val}", (sx, r.y + 102), 16, col, True)
                sx = rr.right + 14
        info = f"Crit {int(f.crit * 100)}%"
        if f.evade:
            info += f"   Evade {int(min(0.6, f.evade) * 100)}%"
        text(s, info, (x, r.y + 130), 15, ui.DIM)
        if f.stun_t > 0:
            text(s, "STUNNED", (x + 300, r.y + 130), 16, ui.GOLD, True)
        if side == 1:
            desc = ENEMIES[self.enemy_id].get("desc")
            if desc:
                text_block(s, desc, (r.x + 20, r.y + 172), r.width - 40, 14, (210, 150, 150))
        text(s, "Items", (r.x + 20, r.y + 220), 18, ui.DIM, True)
        tip = None
        for i, ci in enumerate(f.items):
            bx = r.x + 20 + (i % 4) * 146
            by = r.y + 248 + (i // 4) * 62
            box = pygame.Rect(bx, by, 138, 54)
            col = ui.item_color(ci.st["id"])
            if ci.flash > 0:
                col = tuple(min(255, c + 90) for c in col)
            panel(s, box, col, ui.RARITY_COL[ci.st["rarity"]], radius=6)
            pic = ui.art(ci.st["id"], 30)
            tx = bx + 8
            if pic:
                s.blit(pic, pic.get_rect(center=(bx + 20, by + 20)))
                tx = bx + 38
            text(s, ci.name, (tx, by + 5), 13, ui.TEXT, True)
            ui.bar(s, (bx + 8, by + 38, 122, 8), ci.timer / ci.cd, ui.GOLD, (30, 26, 34))
            text(s, f"{ci.cd:.1f}s", (bx + 130, by + 30), 11, ui.DIM, right=True)
            if box.collidepoint(mouse):
                tip = ci.st
        # phase markers on the HP bar
        for ph in f.phases:
            if not ph["done"]:
                px = x + int(400 * ph["at"])
                pygame.draw.line(s, ui.GOLD, (px, r.y + 56), (px, r.y + 90), 3)
                text(s, "PHASE", (px, r.y + 46), 11, ui.GOLD, True, center=True)
        if side == 1:
            self.draw_intents(s, f, pygame.Rect(r.x + 20, r.y + 390, r.width - 40, 155))
        return tip

    def draw_intents(self, s, f, area):
        """Slay-the-Spire style intents: what the enemy will do next, and when."""
        panel(s, area, (36, 24, 30), (120, 50, 50), radius=6)
        text(s, "ENEMY INTENT  -  next moves", (area.x + 12, area.y + 8), 15, (230, 150, 150), True)
        upcoming = []
        delay = max(0.0, f.stun_t)
        for ci in f.items:
            t_left = ci.cd - ci.timer + delay
            while t_left <= 8.0:
                upcoming.append((t_left, ci))
                t_left += ci.cd
        upcoming.sort(key=lambda u: u[0])
        y = area.y + 34
        for i, (t_left, ci) in enumerate(upcoming[:4]):
            chips = intent_chips(ci.st)
            col_bg = (70, 40, 46) if i == 0 else (48, 32, 38)
            row = pygame.Rect(area.x + 8, y, area.width - 16, 26)
            pygame.draw.rect(s, col_bg, row, border_radius=4)
            text(s, f"{t_left:4.1f}s", (row.x + 8, row.y + 4), 15, ui.GOLD if i == 0 else ui.DIM, True)
            text(s, ci.name, (row.x + 64, row.y + 4), 15, ui.TEXT, True)
            cx = row.x + 250
            for label, col in chips:
                w = ui.font(13, True).size(label)[0] + 12
                pygame.draw.rect(s, col, (cx, row.y + 3, w, 20), border_radius=4)
                text(s, label, (cx + 6, row.y + 5), 13, (15, 12, 16), True)
                cx += w + 6
            y += 29
        if f.stun_t > 0:
            text(s, "(stunned - all moves delayed)", (area.right - 12, area.y + 8), 13, ui.GOLD, True,
                 right=True)
        else:
            nxt = next((ph for ph in f.phases if not ph["done"]), None)
            if nxt:
                text(s, f"Transforms at {int(f.max_hp * nxt['at'])} HP", (area.right - 12, area.y + 8), 13,
                     ui.GOLD, True, right=True)


    def draw(self, s):
        s.fill(ui.BG)
        mouse = pygame.mouse.get_pos()
        head = {"fight": "Battle", "elite": "ELITE Battle", "boss": "BOSS BATTLE"}[self.kind]
        text(s, f"{head}  -  Stage {self.run.stage}  -  {self.battle.t:.1f}s", (W // 2, 28), 22,
             ui.GOLD, True, center=True)
        tip_a = self.draw_fighter(s, 0, self.pf, mouse)
        tip_b = self.draw_fighter(s, 1, self.ef, mouse)
        tip = tip_a or tip_b
        for f in self.floats:
            img = ui.font(f["size"], True).render(f["s"], True, f["col"])
            img.set_alpha(max(0, min(255, int(255 * f["life"]))))
            s.blit(img, img.get_rect(center=(f["x"], f["y"])))
        if self.battle.t >= 25 and not self.battle.done:
            text(s, "FATIGUE: both sides take growing damage!", (W // 2, 622), 16, (180, 120, 220), True,
                 center=True)
        if self.banner_t > 0:
            ov = pygame.Surface((W, 70), pygame.SRCALPHA)
            ov.fill((90, 0, 0, 190))
            s.blit(ov, (0, 470))
            text(s, self.banner, (W // 2, 505), 30, ui.GOLD, True, center=True)
        if tip:
            r = pygame.Rect(min(mouse[0] + 16, W - 330), min(mouse[1] + 16, H - 230), 310, 210)
            ui.draw_tooltip(s, tip["id"], r, eff=tip)
        for b in self.speed_btns:
            b.col = (80, 70, 40) if self.speed == int(b.label[0]) else ui.PANEL2
        if self.finished:
            ov = pygame.Surface((W, 140), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 170))
            s.blit(ov, (0, 290))
            text(s, self.result_text, (W // 2, 360), 72,
                 ui.GOLD if self.battle.winner == 0 else ui.RED, True, center=True)
        self.draw_buttons(s)


# =================================================================== rest
class RestScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.run = run = game.run
        heal = int(run.max_hp * REST_HEAL)
        self.buttons = [
            Button((W // 2 - 320, 400, 300, 70), f"Bathe: heal {heal} HP", self.rest, 20),
            Button((W // 2 + 20, 400, 300, 70), "Dojo training: +5 Max HP", self.train, 20),
        ]

    def rest(self):
        self.run.hp = min(self.run.max_hp, self.run.hp + int(self.run.max_hp * REST_HEAL))
        self.game.change(MapScene(self.game))

    def train(self):
        self.run.max_hp += 5
        self.run.hp += 5
        self.game.change(MapScene(self.game))

    def draw(self, s):
        s.fill(ui.BG)
        top_bar(s, self.run, "Mountain onsen")
        pygame.draw.ellipse(s, (60, 110, 140), (W // 2 - 160, 250, 320, 80))
        for i in range(6):  # steam
            x = W // 2 - 100 + i * 40
            pygame.draw.arc(s, (200, 200, 210), (x, 170 + (i % 2) * 15, 30, 70), 1.2, 4.5, 3)
        text(s, "Steam rises from a mountain hot spring. Rest, or train at the dojo nearby.", (W // 2, 360),
             20, ui.DIM, center=True)
        self.draw_buttons(s)


# =================================================================== stage intro / end
class StageScene(Scene):
    def __init__(self, game, first=False):
        super().__init__(game)
        self.run = game.run
        self.first = first
        self.t = 0
        self.buttons = [Button((W // 2 - 120, 520, 240, 56), "Continue",
                               lambda: game.change(MapScene(game)), 22)]

    def update(self, dt):
        self.t += dt

    def draw(self, s):
        s.fill(ui.BG)
        draw_petals(s, self.t, 25)
        st = STAGES[self.run.stage]
        boss = ENEMIES[self.run.boss_id()]
        text(s, f"STAGE {self.run.stage}", (W // 2, 200), 30, ui.DIM, True, center=True)
        text(s, st["name"], (W // 2, 265), 56, ui.GOLD, True, center=True)
        text(s, st["subtitle"], (W // 2, 325), 20, ui.DIM, center=True)
        text(s, f"Rumours speak of {boss['name']}.", (W // 2, 380), 20, ui.RED, True, center=True)
        text_block(s, boss.get("desc", ""), (W // 2 - 300, 412), 600, 16, ui.DIM)
        if not self.first:
            text(s, "You recovered 30% HP on the journey.", (W // 2, 480), 16, ui.GREEN, center=True)
        self.draw_buttons(s)


class EndScene(Scene):
    def __init__(self, game, won):
        super().__init__(game)
        save.clear_run()   # the run is over: no continuing a finished run
        self.run = game.run
        self.won = won
        self.buttons = [Button((W // 2 - 120, 500, 240, 56), "Main menu",
                               lambda: game.change(TitleScene(game)), 22)]

    def draw(self, s):
        s.fill(ui.BG)
        if self.won:
            text(s, "VICTORY", (W // 2, 230), 90, ui.GOLD, True, center=True)
            text(s, "Lord Ashura falls. Dawn returns to the land.", (W // 2, 320), 22, ui.TEXT, center=True)
        else:
            text(s, "FALLEN", (W // 2, 230), 90, ui.RED, True, center=True)
            text(s, "Your journey ends here. Another will take up the blade.", (W // 2, 320), 22, ui.DIM,
                 center=True)
        text(s, f"{CHARACTERS[self.run.char_id]['name']}  -  reached stage {self.run.stage}  -  "
                f"{self.run.battles_won} battles won", (W // 2, 380), 18, ui.DIM, center=True)
        self.draw_buttons(s)


# =================================================================== ? events
class EventScene(Scene):
    def __init__(self, game, ev):
        super().__init__(game)
        self.run = game.run
        self.ev = ev
        self.result = None
        self.make_option_buttons()

    def make_option_buttons(self):
        self.buttons = []
        for k, (i, opt, ok) in enumerate(options_for(self.run, self.ev)):
            b = Button((W // 2 - 330, 430 + k * 62, 660, 52), opt["label"], lambda i=i: self.choose(i), 18,
                       enabled=ok)
            self.buttons.append(b)

    def choose(self, i):
        g, run = self.game, self.run
        self.result = resolve(run, self.ev, i)
        res = self.result
        if res.get("battle"):
            eid, kind = res["battle"]
            nxt = lambda: g.change(BattleScene(g, eid, kind, run.enemy_scale(kind)))
            label = "Fight!"
        elif res.get("choose"):
            nxt = lambda: g.change(InventoryScene(g, "reward", offers=res["choose"],
                                                  on_done=lambda: MapScene(g), title=self.ev["title"],
                                                  message="Pick one."))
            label = "Choose your reward"
        else:
            nxt = lambda: g.change(MapScene(g))
            label = "Continue"
        self.buttons = [Button((W // 2 - 140, 560, 280, 56), label, nxt, 22)]

    def draw(self, s):
        s.fill(ui.BG)
        top_bar(s, self.run, "Mysterious encounter")
        panel(s, (W // 2 - 360, 80, 720, 330))
        pic = ui.art(self.ev.get("art", ""), 96)
        if pic:
            pygame.draw.circle(s, (40, 34, 52), (W // 2, 160), 62)
            s.blit(pic, pic.get_rect(center=(W // 2, 160)))
        text(s, self.ev["title"], (W // 2, 250), 32, ui.GOLD, True, center=True)
        body = self.result["text"] if self.result else self.ev["text"]
        text_block(s, body, (W // 2 - 320, 285), 640, 18, ui.TEXT if self.result else ui.DIM)
        self.draw_buttons(s)
