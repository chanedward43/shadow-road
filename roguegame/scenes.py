"""All screens of the game."""
import copy
import math
import random

import pygame

from . import ui
from .ui import W, H, text, text_block, panel, Button
from .data import (ITEMS, CHARACTERS, STAGES, ENEMIES, TECHNIQUES, REST_HEAL, BUILDS, BALANCE, sell_value,
                   ENDLESS_STAGE_HP, ENDLESS_PASSIVES, BLOOD_MOON_STAGE, CONSUMABLES, MAX_CONSUMABLES,
                   ASCENSION, MAX_ASCENSION)
from . import save, history, arena, online, audio, progress, settings
from .version import VERSION
from .run import RunState, fresh_seed
from .combat import make_battle, make_pvp_battle, effective_stats
from .events import pick_event, options_for, resolve, omen_event, OMENS
from .inventory import Grid, ItemInst
from .sim import pack

CUR = "ryō"


class Scene:
    map_ok = False          # screens set this to show the Map button (and allow the M key)
    music = None            # music track while this screen is open (a method may pick one)

    def __init__(self, game):
        self.game = game
        self.buttons = []
        self._map_btn = Button((W - 118, 7, 104, 34), "Map (M)", self.open_map, 16)

    def open_map(self):
        if self.game.run is not None:
            self.game.change(MapScene(self.game, back=self))

    def show_map(self):
        run = self.game.run
        return self.map_ok and run is not None and not getattr(run, "arena", None)

    def handle(self, ev):
        if self.show_map():
            if self._map_btn.handle(ev):
                return True
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_m:
                self.open_map()
                return True
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
        if self.show_map():
            self._map_btn.draw(s)


def top_bar(s, run, title=""):
    pygame.draw.rect(s, ui.PANEL, (0, 0, W, 48))
    pygame.draw.line(s, ui.LINE, (0, 48), (W, 48), 2)
    ch = CHARACTERS[run.char_id]
    text(s, ch["name"], (16, 11), 20, ch["color"], True)
    text(s, f"HP {run.hp}/{run.max_hp}", (160, 11), 20, ui.RED, True)
    text(s, f"{run.gold} {CUR}", (330, 11), 20, ui.GOLD, True)
    a = getattr(run, "arena", None)
    if a:
        text(s, f"ARENA  Round {a['round']}   Wins {a['wins']}/{arena.MAX_WINS}", (460, 11), 20, ui.TEXT, True)
        draw_hearts(s, (800, 24), arena.hearts(run))
    else:
        st = STAGES[run.stage]
        label = f"Endless {run.stage}" if getattr(run, "mode", "story") == "endless" else f"Stage {run.stage}/3"
        col = (240, 90, 90) if run.blood_moon_now else ui.TEXT
        r = text(s, f"{label} - {st['name']}", (460, 11), 20, col, True)
        if run.asc:
            text(s, f"A{run.asc}", (r.right + 12, 11), 20, (200, 140, 255), True)
    if title:
        text(s, title, (W - 130, 11), 20, ui.DIM, True, right=True)


def draw_hearts(s, pos, n, total=None, size=9):
    """Little pixel hearts (fonts on the web have no heart symbol)."""
    total = total or arena.HEARTS
    x, y = pos
    for i in range(total):
        col = (220, 60, 70) if i < n else (70, 50, 60)
        cx = x + i * (size * 2 + 8)
        pygame.draw.circle(s, col, (cx - size // 2, y - size // 3), size // 2 + 1)
        pygame.draw.circle(s, col, (cx + size // 2, y - size // 3), size // 2 + 1)
        pygame.draw.polygon(s, col, [(cx - size, y - size // 4), (cx + size, y - size // 4), (cx, y + size)])


def run_music(game):
    run = game.run
    if run is None:
        return "title"
    if getattr(run, "arena", None):
        return "arena"
    return "bloodmoon" if run.blood_moon_now else "map"


def announce(game, unlocked):
    """Toast newly unlocked achievements / ascension levels."""
    for a in unlocked:
        if a[0] == "asc_up":
            game.toast(f"{a[1]} for {CHARACTERS[a[2]]['name']}!", (200, 140, 255), 5)
            audio.play("levelup")
        else:
            game.toast(f"Achievement unlocked: {a[1]}", ui.GOLD, 5)
            audio.play("achievement")


def hint(game, key, msg):
    if progress.hint_once(key):
        game.toast(msg, (150, 210, 255), 8)


def draw_petals(s, t, n=45):
    for i in range(n):
        x = (i * 137 + t * (14 + i % 5) * 3) % W
        y = (i * 89 + t * (18 + i % 7) * 3) % H
        pygame.draw.ellipse(s, (230, 150, 180) if i % 3 else (190, 110, 140), (int(x), int(y), 6, 4))


# =================================================================== title
class TitleScene(Scene):
    music = "title"

    def __init__(self, game):
        super().__init__(game)
        self.t = 0
        self.saved = save.load_run()
        lx, rx, bw, bh = W // 2 - 290, W // 2 + 10, 280, 54
        self.buttons = [
            Button((lx, 390, bw, bh), "New Journey", lambda: game.change(CharSelectScene(game)), 24),
            Button((lx, 456, bw, bh), "Continue", self.resume, 24, enabled=self.saved is not None),
            Button((lx, 522, bw, bh), "Arena (online)", lambda: game.change(ArenaLobbyScene(game)), 24),
            Button((rx, 390, bw, bh), "Match History", lambda: game.change(MatchHistoryScene(game)), 24),
            Button((rx, 456, bw, bh), "Achievements", lambda: game.change(AchievementsScene(game)), 24),
            Button((rx, 522, bw, bh), "Settings", lambda: game.change(SettingsScene(game)), 24),
            Button((W // 2 - 110, 600, 220, 48), "Quit", game.quit, 20),
        ]

    def resume(self):
        self.game.run = self.saved
        self.game.change(MapScene(self.game))

    def update(self, dt):
        self.t += dt

    def draw(self, s):
        s.fill(ui.BG)
        draw_petals(s, self.t)
        pygame.draw.circle(s, (70, 22, 28), (W // 2, 190), 150)        # rising sun
        pygame.draw.circle(s, (120, 34, 40), (W // 2, 190), 150, 6)
        text(s, "SHADOW ROAD", (W // 2 + 3, 193), 84, (20, 12, 14), True, center=True)
        text(s, "SHADOW ROAD", (W // 2, 190), 84, ui.GOLD, True, center=True)
        text(s, "Pack your blade. Walk the road. Cut down the demons of old Japan.", (W // 2, 296), 22,
             ui.DIM, center=True)
        text(s, "Art & audio: Ninja Adventure pack by Pixel-Boy & AAA (CC0)", (W // 2, H - 24), 13, ui.DIM,
             center=True)
        self.draw_buttons(s)


# =================================================================== character select
class CharSelectScene(Scene):
    music = "title"

    def __init__(self, game, arena_mode=False):
        super().__init__(game)
        self.arena_mode = arena_mode
        self.ids = list(CHARACTERS)
        self.sel = None
        n = len(self.ids)
        cw = (W - 40 - (n - 1) * 10) // n
        self.cards = [pygame.Rect(20 + i * (cw + 10), 80, cw, 528) for i in range(n)]
        self.begin = Button((W // 2 - 140, 640, 280, 54), "Set Out", self.start, 24, enabled=False)
        back = (lambda: game.change(ArenaLobbyScene(game))) if arena_mode else (lambda: game.change(TitleScene(game)))
        self.buttons = [self.begin, Button((20, 650, 120, 44), "Back", back)]
        self.mode = "story"
        if not arena_mode:
            self.mode_btns = [Button((W - 340, 645, 150, 44), "Story", lambda: self.set_mode("story"), 18),
                              Button((W - 180, 645, 160, 44), "Endless", lambda: self.set_mode("endless"), 18)]
            self.asc = 0
            self.asc_btns = [Button((160, 645, 44, 44), "<", lambda: self.step_asc(-1), 20),
                             Button((380, 645, 44, 44), ">", lambda: self.step_asc(1), 20)]
            self.buttons += self.mode_btns + self.asc_btns

    def step_asc(self, d):
        if self.sel is None:
            return
        top = progress.asc_unlocked(self.ids[self.sel])
        self.asc = max(0, min(top, self.asc + d))

    def set_mode(self, mode):
        self.mode = mode

    def start(self):
        mx, my = pygame.mouse.get_pos()
        extra = mx * 7919 + my * 104729 + pygame.time.get_ticks()
        if self.arena_mode:
            self.game.run = arena.new_run(self.ids[self.sel], fresh_seed(extra))
            self.game.change(arena_next_round(self.game))
            return
        self.game.run = RunState(self.ids[self.sel], seed=fresh_seed(extra), mode=self.mode, asc=self.asc)
        self.game.change(StageScene(self.game, first=True))

    def handle(self, ev):
        if super().handle(ev):
            return True
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for i, r in enumerate(self.cards):
                if r.collidepoint(ev.pos):
                    self.sel = i
                    self.begin.enabled = True
                    if not self.arena_mode:
                        self.asc = progress.asc_unlocked(self.ids[i])
        return False

    def draw(self, s):
        s.fill(ui.BG)
        text(s, "Choose your Arena fighter" if self.arena_mode else "Choose your path", (W // 2, 45), 34,
             ui.TEXT, True, center=True)
        if not self.arena_mode:
            for b in self.mode_btns:
                b.col = (80, 70, 40) if b.label.lower() == self.mode else ui.PANEL2
            hint = ("3 stages, then the stage-3 villain." if self.mode == "story" else
                    "Beat stage 3, then keep going. Stage 5 brings the Blood Moon.")
            text(s, hint, (W - 20, 618), 13, ui.GOLD if self.mode == "endless" else ui.DIM, right=True)
            # ascension picker
            top = progress.asc_unlocked(self.ids[self.sel]) if self.sel is not None else 0
            for b in self.asc_btns:
                b.enabled = self.sel is not None and top > 0
            label = f"Ascension {self.asc}" if self.asc else ("Ascension: locked" if not top else "Ascension 0")
            text(s, label, (292, 667), 17, (200, 140, 255) if self.asc else ui.DIM, True, center=True)
            if self.asc:
                text(s, f"A{self.asc}: {ASCENSION[self.asc]}" + ("  (+ all lower levels)" if self.asc > 1 else ""),
                     (160, 618), 13, (200, 140, 255))
            elif self.sel is not None and not top:
                text(s, "Win a story run with this class to unlock Ascension 1.", (160, 618), 13, ui.DIM)
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
    "omen": ((240, 200, 80), "Omen"),
    "forge": ((210, 120, 60), "Forge"), "bounty": ((200, 160, 60), "Bounty"), "dojo": ((90, 170, 110), "Dojo"),
}


NODE_ART = {"fight": "map_fight", "elite": "map_elite", "boss": "map_boss", "event": "map_event",
            "shop": "map_shop", "rest": "map_rest", "treasure": "map_shrine", "forge": "nodachi",
            "bounty": "coin_purse", "dojo": "map_rest"}


class MapScene(Scene):
    def music(self):
        return run_music(self.game)

    def __init__(self, game, back=None):
        super().__init__(game)
        self.run = game.run
        self.t = 0
        if back is None:
            hint(game, "map", "Tip: click a glowing node to travel. Hover elites and the boss to read about them.")
            if any(n["kind"] == "omen" for row in self.run.map for n in row):
                hint(game, "omen", "An OMEN is on this map: a choice you made earlier is catching up with you.")
        self.back = back             # set when viewing the map from another screen
        self.arena = getattr(self.run, "arena", None)
        if back is None:
            if not self.arena:                       # arena runs are never saved over your adventure
                save.save_run(self.run)
            self.buttons = [Button((W - 210, H - 70, 190, 50), "Your Kit", self.open_bag)]
        else:
            self.buttons = [Button((W - 210, H - 70, 190, 50), "Back", self.go_back)]

    def go_back(self):
        self.game.change(self.back)

    def open_bag(self):
        self.game.change(InventoryScene(self.game, "manage", on_done=lambda: MapScene(self.game)))

    def node_pos(self, r, node):
        if self.arena:                              # a short floor: spread it across the screen
            return int(150 + r * 230), int(140 + node["x"] * 450)
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
        if self.back is not None:   # viewing only: M or Esc returns
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_m, pygame.K_ESCAPE):
                self.go_back()
                return True
            return False
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
        if self.arena:
            return self.enter_arena(node, kind)
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
        elif kind == "omen":
            g.change(EventScene(g, omen_event(run, node["omen"])))

    def enter_arena(self, node, kind):
        g, run = self.game, self.run
        back = lambda: MapScene(g)
        if kind == "boss":
            g.change(ArenaMatchScene(g))
        elif kind in ("fight", "elite"):
            g.change(BattleScene(g, run.pick_enemy(kind), kind, run.enemy_scale(kind)))
        elif kind == "shop":
            rnd = run.arena["round"]
            g.change(InventoryScene(g, "shop", offers=run.shop_offers(), on_done=back,
                                    title=f"Arena - Round {rnd}: Merchant",
                                    message="Buy, merge and arrange - your kit is what your ghost fights with."))
        elif kind == "treasure":
            g.change(InventoryScene(g, "reward", offers=run.reward_choices("treasure"), on_done=back,
                                    title="Shrine", message="The kami grant one item."))
        elif kind == "event":
            g.change(EventScene(g, arena.pick_floor_event(run), after=back))
        else:                                        # forge / bounty / dojo
            g.toast(arena.resolve_floor(run, kind), ui.GOLD, 4)
            audio.play("event")
            g.change(back())

    def update(self, dt):
        self.t += dt

    def draw(self, s):
        s.fill(ui.BG)
        run = self.run
        top_bar(s, run, "Choose your path" if self.back is None else "Map (viewing)")
        st = STAGES[run.stage]
        if self.arena:
            text(s, f"Arena floor - round {self.arena['round']}", (30, 58), 24, ui.GOLD, True)
            text(s, "Floor fights are practice: lose and you only miss the rewards. The ghost duel counts.",
                 (30, 88), 15, ui.DIM)
        else:
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
                key = OMENS[node["omen"]]["art"] if node["kind"] == "omen" else NODE_ART.get(node["kind"], "")
                pic = ui.art(key, int(rad * 1.25))
                if pic:
                    if dim:
                        pic = pic.copy()
                        pic.set_alpha(110)
                    s.blit(pic, pic.get_rect(center=(x, y)))
                    if (is_av and node["kind"] != "boss") or (node["kind"] == "omen" and not node.get("visited")):
                        text(s, label, (x, y + rad + 11), 12, (240, 200, 80) if node["kind"] == "omen" else ui.TEXT,
                             True, center=True)
                else:
                    text(s, label, (x, y), 12 if len(label) > 6 else (18 if rad > 30 else 14), ui.TEXT, True,
                         center=True)
        # boss name under the boss node (readability: you always know what you're preparing for)
        bx, by = self.node_pos(len(run.map) - 1, run.map[-1][0])
        if self.arena:
            text(s, "Ghost duel", (bx, by + 50), 15, ui.RED, True, center=True)
        else:
            boss = ENEMIES[run.boss_id()]
            text(s, boss["name"].split(",")[0], (bx, by + 50), 15, ui.RED, True, center=True)

        # right column: legend + techniques + hovered node info
        lx, ly = W - 250, 62
        tips = {"fight": "Enemy", "elite": "Tough foe + technique", "shop": "Buy & sell",
                "rest": "Heal or train", "treasure": "Free item", "event": "Mystery event",
                "boss": "Stage villain", "omen": "Your past returns", "forge": "Level up an item",
                "bounty": "Free ryō", "dojo": "+4 max HP"}
        if self.arena:
            tips.update(fight="Practice fight", elite="Hard practice", boss="Ghost duel (counts!)")
        present = {n["kind"] for row in run.map for n in row}
        legend = [(k, v) for k, v in NODE_STYLE.items() if k in present]   # only what's on this map
        panel(s, (lx - 10, ly - 6, 240, 14 + 31 * len(legend)))
        for i, (k, (col, label)) in enumerate(legend):
            yy = ly + 4 + i * 31
            pygame.draw.circle(s, col, (lx + 12, yy + 9), 10)
            text(s, f"{label}: {tips[k]}", (lx + 30, yy), 14, ui.DIM)
        y = ly + 30 + 31 * len(legend)
        text(s, "Techniques", (lx, y), 18, ui.TEXT, True)
        y += 26
        if not run.techniques:
            none = ("None yet. You learn one at rounds 3, 6 and 9." if self.arena else
                    "None yet. Defeat elites and bosses to learn them.")
            y = text_block(s, none, (lx, y), 225, 14, ui.DIM)
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
    map_ok = True

    def music(self):
        return run_music(self.game)

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
        self.offer_rects = [pygame.Rect(30 + i * 162, 92, 152, 172) for i in range(len(self.offers))]
        label = {"manage": "Done", "shop": "Leave", "reward": "Continue"}[mode]
        if getattr(self.run, "arena", None) and mode == "shop":
            label = "Back to the floor"
        self.buttons = [Button((W - 230, H - 70, 210, 52), label, self.done, 22)]
        if mode == "shop":
            self.reroll_btn = Button((850, 228, 180, 44), "", self.reroll, 18)
            self.buttons.append(self.reroll_btn)
        self.buttons += [Button((850, 92, 200, 40), "Auto-arrange", self.auto_arrange, 17),
                         Button((1060, 92, 200, 40), "Merge all", self.merge_all, 17)]
        self.undo = None                      # last Shift+click sale, undoable for a few seconds
        self.undo_btn = Button((470, 616, 200, 32), "Undo sell", self.undo_sell, 15)
        self.rotate_btn = Button((W - 230, H - 70, 210, 52), "Rotate (R)", self.rotate_held, 20)
        self.cons_offers = []
        if mode == "shop" and not getattr(self.run, "arena", None):
            self.cons_offers = self.run.shop_consumables()
        self.cons_rects = [pygame.Rect(850 + i * 210, 140, 200, 80) for i in range(len(self.cons_offers))]
        hint(game, "bag", "Tip: drag items onto the tatami to equip them. Drop an identical item on another to "
                          "merge it. Right-click or R rotates.")
        if self.cons_offers:
            hint(game, "consumable", "Consumables (top right) are used up in your NEXT battle. Hold up to 3.")

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
            self.offer_rects = [pygame.Rect(30 + i * 162, 92, 152, 172) for i in range(len(self.offers))]

    def say(self, msg):
        self.flash_msg, self.flash_t = msg, 2.5

    def other_grid(self, grid):
        return self.run.stash if grid is self.run.bag else self.run.bag

    def quick_move(self, grid, inst):
        """Ctrl+click: send an item to the other bag wherever it fits (trying every rotation)."""
        dest = self.other_grid(grid)
        x, y, rot = inst.x, inst.y, inst.rot
        grid.remove(inst)
        if dest.first_fit(inst):
            self.say(f"{ITEMS[inst.id]['name']} -> {'kit' if dest is self.run.bag else 'travel chest'}")
        else:
            inst.rot = rot
            grid.place(inst, x, y)
            self.say(f"No room in the {'kit' if dest is self.run.bag else 'travel chest'}.")

    def quick_sell(self, grid, inst):
        """Shift+click: sell instantly (with a few seconds to undo)."""
        value = sell_value(inst.id, inst.level)
        self.undo = dict(inst=inst, grid=grid, x=inst.x, y=inst.y, rot=inst.rot, value=value, t=5.0)
        grid.remove(inst)
        self.run.gold += value
        audio.play("sell")
        self.say(f"Sold {ITEMS[inst.id]['name']} for {value} {CUR}.")

    def undo_sell(self):
        u = self.undo
        if not u or self.run.gold < u["value"]:
            return
        inst = u["inst"]
        inst.rot = u["rot"]
        if not (u["grid"].place(inst, u["x"], u["y"]) or u["grid"].first_fit(inst)
                or self.other_grid(u["grid"]).first_fit(inst)):
            return self.say("No room to put it back.")
        self.run.gold -= u["value"]
        self.undo = None
        self.say(f"Got your {ITEMS[inst.id]['name']} back.")

    def rotate_in_place(self, grid, inst):
        """Right-click a placed item: turn it 90 degrees where it is, if it fits."""
        x, y, rot = inst.x, inst.y, inst.rot
        grid.remove(inst)
        inst.rot = (rot + 1) % 4
        if not grid.place(inst, x, y):
            inst.rot = rot
            grid.place(inst, x, y)
            self.say("No room to rotate it there - pick it up to rotate and move it.")

    def auto_arrange(self):
        pack(self.run, merge=False)
        self.say("Arranged: best items in your kit, aura items next to what they boost.")

    def merge_all(self):
        n = self.run.auto_merge()
        if n:
            audio.play("merge")
        self.say(f"Merged {n} pair{'s' if n != 1 else ''}." if n else "Nothing to merge.")

    def add_offer(self, iid, to_kit):
        if not to_kit:
            return self.run.add_item(iid)
        inst = ItemInst(iid)
        return self.run.bag.first_fit(inst) or self.run.stash.first_fit(inst)

    def click_consumable(self, i):
        cid = self.cons_offers[i]
        if cid is None:
            return
        price = self.run.price(cid)
        if self.run.gold < price:
            return self.say(f"Not enough {CUR}.")
        if not self.run.add_consumable(cid):
            return self.say(f"You can only carry {MAX_CONSUMABLES} consumables.")
        self.run.gold -= price
        self.cons_offers[i] = None
        audio.play("buy")
        self.say(f"Bought {CONSUMABLES[cid]['name']}: used in your next battle.")

    def click_offer(self, i, to_kit=False):
        iid = self.offers[i]
        if iid is None:
            return
        price = self.run.price(iid)
        if self.mode == "shop":
            if self.run.gold < price:
                audio.play("back")
                return self.say(f"Not enough {CUR}.")
            if not self.add_offer(iid, to_kit):
                return self.say("No room! Pawn something or rearrange.")
            self.run.gold -= price
            self.offers[i] = None
            audio.play("buy")
        elif self.mode == "reward":
            if not self.add_offer(iid, to_kit):
                return self.say("No room! Pawn something or rearrange.")
            self.offers = [None] * len(self.offers)
            audio.play("event")
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
            value = sell_value(inst.id, inst.level)
            self.run.gold += value
            audio.play("sell")
            self.say(f"Pawned {ITEMS[inst.id]['name']} for {value} {CUR}.")
            self.held = None
            return
        hit = self.grid_at(pos)
        other = hit[0].item_at(hit[2], hit[3]) if hit else None
        if other and self.run.can_merge(other, inst):
            other.level += 1
            self.held = None
            audio.play("merge")
            self.say(f"Merged! {ITEMS[other.id]['name']} is now level {other.level}.")
            return
        tgt = self.drop_target(pos)
        if tgt and tgt[0].place(inst, tgt[2], tgt[3]):
            self.held = None
            return
        if tgt and self.try_swap(inst, *tgt):
            return
        if other and other.id == inst.id:
            self.say("Only items of the same level can merge (max level 3).")
        self.return_held()

    def try_swap(self, inst, grid, o, gx, gy):
        """Dropped onto exactly one item: put the held item there and send that one where ours came from."""
        cells = inst.cells_at(gx, gy)
        if not all(0 <= cx < grid.w and 0 <= cy < grid.h for cx, cy in cells):
            return False
        occ = grid.occupied()
        hit = {occ[c] for c in cells if c in occ}
        if len(hit) != 1:
            return False
        other = hit.pop()
        ox, oy = other.x, other.y
        grid.remove(other)
        if not grid.place(inst, gx, gy):
            grid.place(other, ox, oy)
            return False
        h = self.held
        home = h["grid"]
        if home.place(other, h["x"], h["y"]) or home.first_fit(other) or self.other_grid(home).first_fit(other):
            self.held = None
            self.say(f"Swapped {ITEMS[inst.id]['name']} and {ITEMS[other.id]['name']}.")
            return True
        grid.remove(inst)                   # nowhere for the other item to go: undo
        grid.place(other, ox, oy)
        return False

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
                if self.held and self.rotate_btn.rect.collidepoint(ev.pos):
                    self.rotate_held()
                    return True
                if self.held:
                    self.drop(ev.pos)
                    return True
                for i, r in enumerate(self.cons_rects):
                    if r.collidepoint(ev.pos):
                        self.click_consumable(i)
                        return True
                mods = pygame.key.get_mods()
                ctrl, shift = mods & pygame.KMOD_CTRL, mods & pygame.KMOD_SHIFT
                if self.undo and self.undo_btn.handle(ev):
                    return True
                for i, r in enumerate(self.offer_rects):
                    if r.collidepoint(ev.pos):
                        self.click_offer(i, to_kit=bool(ctrl))
                        return True
                hit = self.grid_at(ev.pos)
                inst = hit[0].item_at(hit[2], hit[3]) if hit else None
                if inst and ctrl:
                    self.quick_move(hit[0], inst)
                    return True
                if inst and shift:
                    self.quick_sell(hit[0], inst)
                    return True
                self.pick_up(ev.pos)
            elif ev.button == 3:
                if self.held:
                    self.rotate_held()
                else:
                    hit = self.grid_at(ev.pos)
                    inst = hit[0].item_at(hit[2], hit[3]) if hit else None
                    if inst:
                        self.rotate_in_place(hit[0], inst)
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1 and self.held:
            h = self.held
            o = self.bag_o if h["grid"] is self.run.bag else self.stash_o
            start = (o[0] + h["x"] * CELL + h["off"][0], o[1] + h["y"] * CELL + h["off"][1])
            if math.hypot(ev.pos[0] - start[0], ev.pos[1] - start[1]) > 12 \
                    and not self.rotate_btn.rect.collidepoint(ev.pos):
                self.drop(ev.pos)
        elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_r:
            self.rotate_held()
        elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE and self.held:
            self.return_held()
        elif ev.type == pygame.MOUSEWHEEL:
            self.rotate_held()
        return False

    def update(self, dt):
        self.flash_t = max(0, self.flash_t - dt)
        if self.undo:
            self.undo["t"] -= dt
            if self.undo["t"] <= 0:
                self.undo = None
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
                         highlight=self.highlight.get(inst.uid), level=inst.level, rot=inst.rot)

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
            ui.draw_item(s, iid, shp, r.centerx - w // 2, r.y + 6 + (106 - h) // 2, cs)
            name = d["name"] if ui.font(14, True).size(d["name"])[0] <= r.width - 12 else d["name"][:17] + "."
            text(s, name, (r.centerx, r.bottom - 48), 14, ui.TEXT, True, center=True)
            if self.mode == "shop":
                price = run.price(iid)
                col = ui.GOLD if run.gold >= price else ui.RED
                text(s, f"{price} {CUR}", (r.centerx, r.bottom - 22), 16, col, True, center=True)
            else:
                text(s, "ENEMY DROP" if iid in self.drops else "FREE", (r.centerx, r.bottom - 22), 16,
                     ui.GOLD if iid in self.drops else ui.GREEN, True, center=True)
            if hov:
                hover_tip = (iid, None, run.price(iid) if self.mode == "shop" else None, None)
        cons_tip = None
        for cid, r in zip(self.cons_offers, self.cons_rects):
            if cid is None:
                panel(s, r, (24, 22, 30), ui.LINE)
                continue
            c = CONSUMABLES[cid]
            hov = r.collidepoint(mouse) and not self.held
            panel(s, r, ui.PANEL2 if hov else ui.PANEL, (120, 200, 170))
            pic = ui.art(c["art"], 34)
            if pic:
                s.blit(pic, pic.get_rect(center=(r.x + 26, r.centery)))
            text(s, c["name"], (r.x + 50, r.y + 10), 14, ui.TEXT, True)
            price = run.price(cid)
            text(s, f"{price} {CUR}", (r.x + 50, r.y + 30), 14, ui.GOLD if run.gold >= price else ui.RED, True)
            text(s, "consumable", (r.right - 8, r.y + 30), 11, (120, 200, 170), right=True)
            if hov:
                cons_tip = c
        if not self.offers:
            text(s, "Arrange your kit. Only items on the TATAMI are equipped and fight for you.", (30, 70), 18,
                 ui.DIM)
            text(s, "Touching items can buff each other (hover one to see its neighbours).", (30, 96), 16,
                 ui.DIM)

        self.draw_grid(s, run.bag, self.bag_o, "KIT  (equipped - fights for you)", True)
        self.draw_grid(s, run.stash, self.stash_o, "TRAVEL CHEST  (not equipped)", False)

        hov_sell = self.sell_rect.collidepoint(mouse) and self.held
        panel(s, self.sell_rect, (70, 30, 30) if hov_sell else (40, 26, 30), ui.RED if hov_sell else ui.LINE)
        pawn = (f"PAWN: drop to sell for {sell_value(self.held['inst'].id, self.held['inst'].level)} {CUR}"
                if self.held else "PAWN: drop here to sell (half price)")
        text(s, pawn, self.sell_rect.center, 16, ui.TEXT, True, center=True)

        # consumables you're carrying into the next battle
        text(s, "NEXT BATTLE:", (30, 600), 14, (120, 200, 170), True)
        for k in range(MAX_CONSUMABLES):
            r = pygame.Rect(150 + k * 50, 590, 42, 42)
            panel(s, r, (26, 34, 34), (70, 110, 100), radius=6)
            if k < len(run.consumables):
                c = CONSUMABLES[run.consumables[k]]
                pic = ui.art(c["art"], 30)
                if pic:
                    s.blit(pic, pic.get_rect(center=r.center))
                if r.collidepoint(mouse):
                    cons_tip = c
        rp = pygame.Rect(850, 290, 410, 330)
        if cons_tip:
            panel(s, rp, ui.PANEL, (120, 200, 170))
            text(s, cons_tip["name"], (rp.x + 14, rp.y + 12), 20, (150, 230, 200), True)
            y = ui.rich_text_block(s, cons_tip["desc"], (rp.x + 14, rp.y + 44), rp.width - 28, 16, ui.TEXT)
            text_block(s, "Consumable: used up in your next battle, win or lose.", (rp.x + 14, y + 10),
                       rp.width - 28, 14, ui.DIM)
        elif self.held:
            hover_tip = (self.held["inst"].id, None, None, "Right-click / R / wheel to rotate.")
        if hover_tip:
            ui.draw_tooltip(s, hover_tip[0], rp, eff=hover_tip[1], price=hover_tip[2], extra=hover_tip[3],
                            fit=True)
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
            for ln in ["Click or drag to move. Drop on another item to swap.",
                       "Right-click: rotate (in place, or while held). Esc: cancel.",
                       "Ctrl+click: send to the other bag / buy straight into kit.",
                       "Shift+click: sell instantly (Undo for 5s).",
                       "Drop on an identical item to merge. M: map."]:
                text(s, ln, (rp.x + 14, y), 13, ui.DIM)
                y += 18

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
            ui.draw_item(s, inst.id, inst.shape, tl[0], tl[1], CELL, alpha=200, level=inst.level, rot=inst.rot)

        if self.flash_t > 0:
            text(s, self.flash_msg, (W // 2, H - 40), 20, ui.GOLD, True, center=True)
        if self.held is not None:
            self.rotate_btn.draw(s)
        if self.held is None:
            self.draw_buttons(s)
            if self.undo:
                self.undo_btn.label = f"Undo sell ({int(self.undo['t']) + 1}s)"
                self.undo_btn.enabled = self.run.gold >= self.undo["value"]
                self.undo_btn.draw(s)


# =================================================================== techniques
class TechniqueScene(Scene):
    """Pick 1 of 3 permanent class upgrades (after elites and bosses)."""
    map_ok = True

    def music(self):
        return run_music(self.game)

    def __init__(self, game, then):
        super().__init__(game)
        self.run = game.run
        self.then = then
        self.choices = self.run.technique_choices()
        if not self.choices:
            self.choices = []
        n = len(self.choices)
        self.cards = [pygame.Rect(W // 2 - n * 190 + i * 380 + 10, 220, 360, 200) for i in range(n)]
        self.buttons = [Button((W // 2 - 100, 500, 200, 50), "Skip", lambda: game.change(then()))]

    def handle(self, ev):
        if super().handle(ev):
            return True
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for tid, r in zip(self.choices, self.cards):
                if r.collidepoint(ev.pos):
                    self.run.learn(tid)
                    audio.play("levelup")
                    self.game.change(self.then())
                    return True
        return False

    def draw(self, s):
        s.fill(ui.BG)
        top_bar(s, self.run, "Learn a technique")
        ch = CHARACTERS[self.run.char_id]
        text(s, "Your skill grows", (W // 2, 120), 34, ui.GOLD, True, center=True)
        text(s, f"Choose one {ch['name']} technique. It lasts for the rest of the run.", (W // 2, 162), 17,
             ui.DIM, center=True)
        if not self.choices:
            text(s, "You have mastered every technique.", (W // 2, 300), 22, ui.DIM, center=True)
        for tid, r in zip(self.choices, self.cards):
            d = TECHNIQUES[tid]
            hov = r.collidepoint(pygame.mouse.get_pos())
            panel(s, r, ui.PANEL2 if hov else ui.PANEL, ui.GOLD if hov else ch["color"], width=3 if hov else 2)
            pygame.draw.rect(s, ch["color"], (r.x + 2, r.y + 2, r.width - 4, 6), border_radius=4)
            text(s, d["name"], (r.centerx, r.y + 46), 26, ui.GOLD, True, center=True)
            if d.get("endless"):
                text(s, "ENDLESS TECHNIQUE", (r.centerx, r.y + 74), 12, (200, 140, 255), True, center=True)
            ui.rich_text_block(s, d["desc"], (r.x + 26, r.y + 98), r.width - 52, 18, ui.TEXT)
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


# =================================================================== battle helpers
KCELL = 40          # kit cell size in battle

STATUS_KEYS = {"Block": "block", "Poison": "poison", "Burn": "burn", "Regen": "regen", "Thorns": "thorns",
               "Dodge": "dodge", "Resolve": "resolve", "Ki": "ki", "Counter": "counter", "Curse": "curse",
               "Shikigami": "shikigami"}


def fight_stat_lines(st):
    """Readable 'this battle' numbers for one item."""
    out = []
    if st.get("uses"):
        out.append(f"Activated {st['uses']} time{'s' if st['uses'] != 1 else ''}")
    if st.get("dmg"):
        crit = f" ({st['crits']} crit{'s' if st.get('crits', 0) != 1 else ''})" if st.get("crits") else ""
        out.append(f"Dealt {st['dmg']} damage{crit}")
    for key, label in (("block", "Gained {} Block"), ("heal", "Heal: restored {} HP"), ("poison", "Applied {} Poison"),
                       ("burn", "Applied {} Burn"), ("curse", "Applied {} Curse"), ("steal", "Steal: took {} Block"),
                       ("ki", "Gained {} Ki"), ("dodge", "Gained {} Dodge"), ("regen", "Gained {} Regen"),
                       ("summons", "Summoned {} Shikigami")):
        if st.get(key):
            out.append(label.format(st[key]))
    if st.get("stun"):
        out.append(f"Stun: froze the enemy for {st['stun']:.1f}s")
    return out


def short_delta(delta):
    parts = []
    if "dmg" in delta:
        parts.append(f"{delta['dmg']} dmg" + (" CRIT" if delta.get("crits") else ""))
    for key, fmt in (("block", "+{} Block"), ("heal", "+{} heal"), ("poison", "+{} Poison"), ("burn", "+{} Burn"),
                     ("curse", "+{} Curse"), ("steal", "Steal {}"), ("ki", "+{} Ki"), ("dodge", "+{} Dodge"),
                     ("regen", "+{} Regen"), ("summons", "+Shikigami")):
        if key in delta:
            parts.append(fmt.format(delta[key]))
    if "stun" in delta:
        parts.append(f"Stun {delta['stun']:.1f}s")
    return ", ".join(parts) or "missed"


class BattleScene(Scene):
    map_ok = True

    def music(self):
        if self.ghost is not None:
            return "arena"
        if self.run.blood_moon_now:
            return "bloodmoon"
        return "boss" if self.kind == "boss" else "battle"

    def __init__(self, game, enemy_id, kind, scale=1.0, ghost=None, ghost_rec=None, on_result=None):
        super().__init__(game)
        self.run = run = game.run
        self.kind = kind
        self.enemy_id = enemy_id
        self.ghost, self.ghost_rec, self.on_result = ghost, ghost_rec, on_result
        if ghost is not None:
            self.battle = make_pvp_battle(run, ghost, seed=run.rng.randrange(1 << 30), name=ghost_rec["name"])
        else:
            self.battle = make_battle(run, enemy_id, scale, seed=run.rng.randrange(1 << 30))
        self.initial = copy.deepcopy(self.battle)        # replays restart from this exact moment
        self.pf, self.ef = self.battle.f
        self.build_enemy_layout()
        self.status_hits = []
        self.eff_stats = effective_stats(run.bag, run.char_id, run.techniques)
        self.show_summary = True
        self.replays = 0
        self.real_t = 0.0                  # wall-clock seconds watched (fight time / speed)
        self.speed = settings.get()["speed"]
        self.hp_before = run.hp
        hint(game, "battle", "Battles play themselves. Teal bar = Stamina: weapons wait when it runs out. "
                             "Hover anything for details.")
        if run.char_id == "onmyoji":
            hint(game, "curse", "Curse: each stack makes the enemy deal 5% less damage. Hex items hit harder "
                                "for every Curse.")
        if run.char_id == "sohei":
            hint(game, "ki", "Ki builds every time you're hit. It powers your counter-attacks and Ki Bursts.")
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
        self.replay_btn = Button((W - 450, 640, 200, 50), "Replay", self.replay, 22)
        self.summary_btn = Button((440, 640, 200, 50), "Hide summary", self.toggle_summary, 18)
        self.buttons = self.speed_btns + [self.skip_btn]
        self.start_delay = 0.8

    def set_speed(self, sp):
        self.speed = sp

    def build_enemy_layout(self):
        """Enemies have no grid of their own: lay their items out in a small kit so you can see it."""
        self.e_map = {}                  # id(CItem) -> ItemInst
        if self.ghost is not None:       # a ghost has a real kit: show it exactly as they packed it
            self.e_grid = self.ghost.bag
            by_uid = {inst.uid: inst for inst in self.e_grid.items}
            for ci in self.ef.items:
                if ci.uid in by_uid:
                    self.e_map[id(ci)] = by_uid[ci.uid]
            return
        self.e_grid = Grid(7, 3)
        for ci in self.ef.items:
            self.place_enemy_item(ci)
        for iid, lvl in self.ef.carried:  # passive items they carry (no cooldown)
            if not ITEMS[iid].get("cd"):
                self.e_grid.first_fit(ItemInst(iid, level=lvl))

    def place_enemy_item(self, ci):
        if self.ghost is not None:       # never rearrange a ghost's real kit
            self.e_map[id(ci)] = None
            return
        inst = ItemInst(ci.st["id"], level=ci.st.get("level", 1))
        if self.e_grid.first_fit(inst):
            self.e_map[id(ci)] = inst

    def replay(self):
        self.battle = copy.deepcopy(self.initial)
        self.pf, self.ef = self.battle.f
        self.build_enemy_layout()
        self.floats, self.banner, self.banner_t = [], "", 0
        self.finished = False
        self.start_delay = 0.5
        self.real_t = 0.0
        self.replays += 1
        self.buttons = self.speed_btns + [self.skip_btn]

    def toggle_summary(self):
        self.show_summary = not self.show_summary
        self.summary_btn.label = "Hide summary" if self.show_summary else "Show summary"

    def skip(self):
        self.battle.run_to_end()
        self.battle.events.clear()

    def cont(self):
        g, run = self.game, self.run
        if self.on_result is not None:
            self.on_result(self.battle.winner == 0)
            return
        if getattr(run, "arena", None):              # arena floor fight: practice, full heal after
            run.hp = run.max_hp
            run.after_battle(self.battle.winner == 0, self.kind)
            if self.battle.winner != 0:
                g.toast("Defeated - no rewards, but no heart lost.", (230, 130, 130), 4)
                g.change(MapScene(g))
                return
            gold = run.gold_reward(self.kind)
            g.change(InventoryScene(g, "reward", offers=run.reward_choices(self.kind),
                                    on_done=lambda: MapScene(g), title="Spoils",
                                    message=f"Victory! +{gold} {CUR}. Take one."))
            return
        run.hp = max(0, min(run.max_hp, self.pf.hp))
        for g_, why in run.after_battle(self.battle.winner == 0, self.kind):
            g.toast(f"{why}: +{g_} {CUR}", ui.GOLD, 3)
            audio.play("gold")
        if self.battle.winner == 0:
            announce(g, progress.on_battle_won(run, self.enemy_id, self.kind, self.hp_before, run.hp))
        if self.battle.winner != 0:
            run.killed_by = self.enemy_id
            run.killed_kind = self.kind
            g.change(EndScene(g, False))
            return
        run.battles_won += 1
        run.kills.append(self.enemy_id)
        gold = run.gold_reward(self.kind)
        rolled = run.roll_drop(self.enemy_id, self.ef.carried)
        drop, dlvl, signature = rolled if rolled else (None, 1, False)
        if self.kind == "boss" and run.stage >= 3 and run.mode != "endless":
            g.change(EndScene(g, True))
            return

        def after_reward():
            if self.kind == "boss":
                run.next_stage()
                return StageScene(g)
            return MapScene(g)

        def reward():
            # regular enemies: their drop is one of the choices. Elites & bosses: drop is free, then pick one.
            msg = f"Victory! +{gold} {CUR}. Take one - the first is what the enemy dropped" + (
                " (its signature item!)." if signature else ".")
            offers = run.reward_choices(self.kind)
            if run.flags.pop("champion_bounty", False):     # the Champion's Grave: a legendary
                offers = run.legendary_choices()
                msg = f"The champion falls. +{gold} {CUR}. Its legendary arsenal is yours: take one."
                return InventoryScene(g, "reward", offers=offers, on_done=after_reward, title="Legendary Spoils",
                                      message=msg)
            if drop and self.kind == "fight":
                offers = [drop] + offers[:2]
            elif drop:
                got = run.add_item(drop, level=dlvl)
                what = ITEMS[drop]["name"] + (f" (level {dlvl})" if dlvl > 1 else "")
                if signature:
                    what = "its signature " + what
                msg = (f"+{gold} {CUR}. It dropped {what}"
                       + (" (in your chest)." if got else " but you had no room!") + " Now take one more.")
            return InventoryScene(g, "reward", offers=offers, on_done=after_reward, title="Spoils", message=msg,
                                  drops=[drop] if drop and self.kind == "fight" else [])

        if self.kind in ("elite", "boss"):
            g.change(TechniqueScene(g, then=reward))
        else:
            g.change(reward())

    def sound(self, k, e, side):
        """Hit sounds and screen shake. Your side's hits are a little louder than the enemy's."""
        vol = 0.9 if side == 1 else 0.7
        if k == "hit":
            if e["crit"]:
                audio.play("crit", vol)
                self.game.shake(7, 0.22)
            else:
                audio.play("hit" if random.random() < 0.5 else "hit2", vol * 0.8, gap=0.05)
        elif k in ("ambush", "kiburst"):
            audio.play("explode", 0.8)
            self.game.shake(9, 0.3)
        elif k == "phase":
            audio.play("phase", 1.0)
            self.game.shake(12, 0.45)
        else:
            name = {"block": "block", "heal": "heal", "evade": "evade", "stun": "stun", "summon": "summon",
                    "poison": "poison", "burn": "burn", "hex": "curse", "counter": "hit2"}.get(k)
            if name:
                audio.play(name, 0.35 if k in ("poison", "burn") else 0.55, gap=0.25 if k in ("poison", "burn")
                           else 0.08)

    def float_text(self, side, s, col, size=22):
        x = self.panels[side].x + 330 + random.randint(-110, 110)
        y = self.panels[side].y + 200 + random.randint(-15, 15)
        self.floats.append(dict(x=x, y=y, s=s, col=col, life=1.1, size=size))

    def update(self, dt):
        if self.start_delay > 0:
            self.start_delay -= dt
        elif not self.battle.done:
            self.battle.advance(dt * self.speed)
            self.real_t += dt
        for e in self.battle.events:
            k, side, a = e["kind"], e["side"], e["amount"]
            if not a and not e["text"] and k in ("hit", "poison", "burn", "thorns", "fatigue", "counter", "hex",
                                                 "kiburst", "summon"):
                continue                                # fully absorbed by Block: no "-0" popups
            self.sound(k, e, side)
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
            elif k == "ambush":
                self.float_text(side, f"AMBUSH -{a}", (255, 230, 120), 26)
            elif k in ("grow", "steal", "cleanse"):
                col = {"grow": (255, 120, 90), "steal": (150, 180, 255), "cleanse": (200, 255, 200)}[k]
                self.float_text(side, e["text"], col, 18)
            elif k == "phase":
                self.banner, self.banner_t = e["text"], 3.0
        self.battle.events.clear()
        self.banner_t = max(0, self.banner_t - dt)
        for f in self.floats:
            f["life"] -= dt
            f["y"] -= 40 * dt
        self.floats = [f for f in self.floats if f["life"] > 0]
        if self.battle.done and not self.finished:
            audio.play("win" if self.battle.winner == 0 else "lose")
            self.finished = True
            self.result_text = "VICTORY" if self.battle.winner == 0 else "DEFEAT"
            self.show_summary = True
            self.summary_btn.label = "Hide summary"
            self.buttons = [self.summary_btn, self.replay_btn, self.cont_btn]

    def draw_fighter(self, s, side, f, mouse):
        r = self.panels[side]
        panel(s, r, ui.PANEL, (120, 40, 40) if f.stun_t > 0 else ui.LINE, width=4 if f.stun_t > 0 else 2)
        ui.portrait(s, (r.x + 90, r.y + 100), 62, f.color, f.glyph, f.portrait,
                    key=self.run.char_id if side == 0 else (self.ghost.char_id if self.ghost else self.enemy_id))
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
                self.status_hits.append((rr, STATUS_KEYS[label]))
                sx = rr.right + 14
        info = f"Crit {int(f.crit * 100)}%"
        if f.evade:
            info += f"   Evade {int(min(0.6, f.evade) * 100)}%"
        rr = text(s, info, (x, r.y + 130), 15, ui.DIM)
        self.status_hits.append((rr, "evasion" if f.evade else "crit"))
        if any(ci.cost for ci in f.items):
            sr = pygame.Rect(x + 165, r.y + 131, 110, 12)
            ui.bar(s, sr, f.stamina / max(0.1, f.max_stamina), (90, 210, 175))
            lab = text(s, f"Stamina {f.stamina:.1f}/{f.max_stamina:g}", (sr.right + 8, r.y + 129), 14,
                       (120, 230, 200), True)
            self.status_hits.append((sr.union(lab), "stamina"))
        if f.stun_t > 0:
            rr = text(s, "STUNNED", (x + 330, r.y + 112), 16, ui.GOLD, True)
            self.status_hits.append((rr, "stun"))
        if side == 1 and self.ghost is not None:
            g = self.ghost_rec
            who = "AI ghost" if g.get("bot") else "Player ghost"
            text_block(s, f"{who}  -  {CHARACTERS[g['cls']]['name']}  -  {g['wins']} wins, {g['losses']} losses "
                          f"when they reached round {g['round']}", (r.x + 20, r.y + 172), r.width - 40, 14,
                       (210, 150, 150))
        elif side == 1:
            desc = ENEMIES[self.enemy_id].get("desc")
            if desc:
                text_block(s, desc, (r.x + 20, r.y + 172), r.width - 40, 14, (210, 150, 150))
        tip = self.draw_kit(s, side, f, (r.x + 20, r.y + 228), mouse)
        if side == 0:
            self.draw_log(s, pygame.Rect(r.x + 318, r.y + 220, r.width - 338, 325))
        # phase markers on the HP bar
        for ph in f.phases:
            if not ph["done"]:
                px = x + int(400 * ph["at"])
                pygame.draw.line(s, ui.GOLD, (px, r.y + 56), (px, r.y + 90), 3)
                text(s, "PHASE", (px, r.y + 46), 11, ui.GOLD, True, center=True)
        if side == 1:
            self.draw_intents(s, f, pygame.Rect(r.x + 20, r.y + 390, r.width - 40, 155))
        return tip

    def draw_kit(self, s, side, f, origin, mouse):
        """The fighter's real kit: item art, a cooldown sweep, a flash on activation, and use counts."""
        ox, oy = origin
        if side == 0:
            grid = self.run.bag
            by_inst = {ci.uid: ci for ci in f.items}
            find = lambda inst: by_inst.get(inst.uid)
            label = "YOUR KIT"
        else:
            for ci in f.items:                      # weapons drawn mid-fight join the kit
                if id(ci) not in self.e_map:
                    self.place_enemy_item(ci)
            grid = self.e_grid
            rev = {self.e_map[id(ci)].uid: ci for ci in f.items if self.e_map.get(id(ci)) is not None}
            find = lambda inst: rev.get(inst.uid)
            label = "THEIR KIT"
        text(s, label, (ox, oy - 22), 15, ui.DIM, True)
        for y in range(grid.h):
            for x in range(grid.w):
                pygame.draw.rect(s, (40, 36, 30) if side == 0 else (44, 30, 34),
                                 (ox + x * KCELL, oy + y * KCELL, KCELL, KCELL))
                pygame.draw.rect(s, (66, 58, 48) if side == 0 else (74, 48, 54),
                                 (ox + x * KCELL, oy + y * KCELL, KCELL, KCELL), 1)
        tip = None
        for inst in grid.items:
            ci = find(inst)
            px, py = ox + inst.x * KCELL, oy + inst.y * KCELL
            ui.draw_item(s, inst.id, inst.shape, px, py, KCELL, level=inst.level, rot=inst.rot)
            xs = [c[0] for c in inst.shape]
            ys = [c[1] for c in inst.shape]
            box = pygame.Rect(px + min(xs) * KCELL + 3, py + min(ys) * KCELL + 3,
                              (max(xs) - min(xs) + 1) * KCELL - 6, (max(ys) - min(ys) + 1) * KCELL - 6)
            if ci is not None:
                left = 1 - min(1.0, ci.timer / ci.cd)               # cooldown still to go
                sh = pygame.Surface(box.size, pygame.SRCALPHA)
                sh.fill((0, 0, 0, 120 if f.stun_t <= 0 else 170))
                s.blit(sh, box.topleft, (0, 0, box.width, int(box.height * left)))
                if ci.waiting and ci.timer >= ci.cd and f.stamina < ci.cost:
                    wt = pygame.Surface(box.size, pygame.SRCALPHA)
                    wt.fill((40, 150, 130, 90))
                    s.blit(wt, box.topleft)
                    pygame.draw.rect(s, (120, 230, 200), box, 2, border_radius=3)
                    text(s, "...", (box.x + 3, box.y - 2), 16, (160, 255, 225), True)
                if ci.flash > 0:
                    fl = pygame.Surface(box.size, pygame.SRCALPHA)
                    fl.fill((255, 255, 220, int(160 * ci.flash / 0.25)))
                    s.blit(fl, box.topleft)
                uses = ci.stats.get("uses", 0)
                if uses:
                    text(s, f"x{uses}", (box.right - 2, box.bottom - 15), 12, ui.GOLD, True, right=True)
            if box.collidepoint(mouse):
                if ci is not None:
                    tip = (inst.id, ci.st, ci.stats)
                else:
                    tip = (inst.id, inst.data if side == 1 else self.eff_stats.get(inst.uid, inst.data), None)
        return tip

    def draw_log(self, s, area):
        """Activation-by-activation log for both sides (newest at the bottom)."""
        panel(s, area, (26, 24, 34), ui.LINE, radius=6)
        text(s, "BATTLE LOG", (area.x + 10, area.y + 6), 14, ui.DIM, True)
        lh = 17
        rows = (area.height - 30) // lh
        y = area.y + 28
        for e in self.battle.log[-rows:]:
            who = (150, 200, 255) if e["side"] == 0 else (240, 140, 140)
            text(s, f"{e['t']:5.1f}", (area.x + 8, y), 12, ui.DIM)
            name = e["name"] if len(e["name"]) <= 16 else e["name"][:15] + "."
            nr = text(s, name, (area.x + 46, y), 13, who, True)
            ui.rich_text_block(s, short_delta(e["delta"]), (nr.right + 6, y), area.right - nr.right - 12, 13,
                               ui.TEXT)
            y += lh

    def draw_keyword_tip(self, s, key, mouse):
        from .keywords import KEYWORDS
        name, col, desc = KEYWORDS[key]
        lines = ui.wrap(desc, 14, 280)
        h = 34 + 18 * len(lines)
        r = pygame.Rect(min(mouse[0] + 14, W - 310), min(mouse[1] + 14, H - h - 4), 300, h)
        panel(s, r, ui.PANEL, col)
        s.blit(ui.font(17, True, True).render(name, True, col), (r.x + 12, r.y + 7))
        ui.text_block(s, desc, (r.x + 12, r.y + 30), 276, 14, ui.TEXT)

    def draw_summary(self, s):
        """End-of-fight breakdown: what every item did."""
        r = pygame.Rect(W // 2 - 440, 120, 880, 470)
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 120))
        s.blit(ov, (0, 0))
        panel(s, r, (24, 22, 32), ui.GOLD if self.battle.winner == 0 else ui.RED, width=3)
        text(s, self.result_text, (r.centerx, r.y + 36), 52, ui.GOLD if self.battle.winner == 0 else ui.RED, True,
             center=True)
        text(s, f"Fight time {self.battle.t:.1f}s   -   {len(self.battle.log)} activations", (r.centerx, r.y + 76), 15,
             ui.DIM, center=True)
        for side, (f, title) in enumerate(((self.pf, "Your items"), (self.ef, self.ef.name))):
            cx = r.x + 24 + side * 430
            text(s, title, (cx, r.y + 100), 18, (150, 200, 255) if side == 0 else (240, 140, 140), True)
            items = sorted(f.items, key=lambda ci: (-ci.stats.get("dmg", 0), -sum(ci.stats.values())))
            y = r.y + 128
            for ci in items[:10]:
                pic = ui.art(ci.st["id"], 22)
                if pic:
                    s.blit(pic, pic.get_rect(center=(cx + 11, y + 10)))
                text(s, ci.name[:20], (cx + 28, y + 1), 14, ui.TEXT, True)
                text(s, f"x{ci.stats.get('uses', 0)}", (cx + 200, y + 1), 13, ui.GOLD, True)
                ui.rich_text_block(s, short_delta({k: v for k, v in ci.stats.items() if k != "uses"}),
                                   (cx + 238, y + 1), 170, 13, ui.TEXT)
                y += 26
            tot = {k: v for k, v in self.battle.totals[side].items() if k != "fatigue"}
            if tot:
                ui.rich_text_block(s, "Over time: " + ", ".join(f"{v} {k.title()}" for k, v in tot.items()) +
                                   " damage", (cx, r.bottom - 34), 400, 13, ui.DIM)


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
        if self.ghost is not None or getattr(self.run, "arena", None):
            a = self.run.arena
            what = "Ghost duel" if self.ghost is not None else "practice fight"
            text(s, f"ARENA  -  Round {a['round']} {what}  -  {a['wins']} wins", (W // 2, 18), 22, ui.GOLD,
                 True, center=True)
        else:
            head = {"fight": "Battle", "elite": "ELITE Battle", "boss": "BOSS BATTLE"}[self.kind]
            stage = self.run.stage
            where = f"Endless {stage}" if stage > 3 else f"Stage {stage}"
            moon = self.run.blood_moon_now
            text(s, f"{head}  -  {where}" + ("  -  BLOOD MOON" if moon else ""), (W // 2, 18), 22,
                 (240, 90, 90) if moon else ui.GOLD, True, center=True)
        # Fight time is the battle's own clock: the same number at any speed (fatigue starts at 25s).
        clock = f"Fight time {self.battle.t:.1f}s"
        if self.speed != 1:
            clock += f"   (x{self.speed} speed  -  {self.real_t:.1f}s real)"
        text(s, clock, (W // 2, 42), 15, ui.DIM, True, center=True)
        self.status_hits = []
        if self.replays:
            text(s, f"REPLAY {self.replays}", (20, 18), 18, (200, 160, 255), True)
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
            iid, eff, stats = tip
            r = pygame.Rect(min(mouse[0] + 16, W - 350), mouse[1] + 16, 330, 100)
            ui.draw_tooltip(s, iid, r, eff=eff, fight_stats=fight_stat_lines(stats) if stats else None, fit=True)
        else:
            for rr, key in self.status_hits:
                if rr.collidepoint(mouse):
                    self.draw_keyword_tip(s, key, mouse)
                    break
        if self.finished and self.show_summary:
            self.draw_summary(s)
        for b in self.speed_btns:
            b.col = (80, 70, 40) if self.speed == int(b.label[0]) else ui.PANEL2
        if self.finished and not self.show_summary:
            text(s, self.result_text, (W // 2, 28), 30, ui.GOLD if self.battle.winner == 0 else ui.RED, True,
                 center=True)
        self.draw_buttons(s)


# =================================================================== rest
class RestScene(Scene):
    map_ok = True

    def music(self):
        return run_music(self.game)

    def __init__(self, game):
        super().__init__(game)
        self.run = run = game.run
        heal = int(run.max_hp * (0.2 if run.asc >= 6 else REST_HEAL))
        self.buttons = [
            Button((W // 2 - 320, 400, 300, 70), f"Bathe: heal {heal} HP", self.rest, 20),
            Button((W // 2 + 20, 400, 300, 70), "Dojo training: +5 Max HP", self.train, 20),
        ]

    def rest(self):
        self.run.rest()
        audio.play("heal")
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
    map_ok = True

    def music(self):
        return run_music(self.game)

    def __init__(self, game, first=False):
        super().__init__(game)
        self.run = game.run
        announce(game, progress.on_stage(self.run))
        self.first = first
        self.t = 0
        self.buttons = [Button((W // 2 - 120, 560, 240, 56), "Continue",
                               lambda: game.change(MapScene(game)), 22)]

    def update(self, dt):
        self.t += dt

    def draw(self, s):
        s.fill(ui.BG)
        draw_petals(s, self.t, 25)
        run = self.run
        st = STAGES[run.stage]
        boss = ENEMIES[run.boss_id()]
        moon = run.blood_moon_now
        if run.asc:
            text(s, f"ASCENSION {run.asc}", (W // 2, 30), 18, (200, 140, 255), True, center=True)
        if moon:                                       # the Blood Moon
            pygame.draw.circle(s, (120, 20, 25), (W // 2, 100), 72)
            pygame.draw.circle(s, (170, 35, 40), (W // 2, 100), 60)
        if run.mode == "endless" and run.stage == 3:
            text(s, "ENDLESS - beat this villain and the road goes on", (W // 2, 160), 16, ui.GOLD, True,
                 center=True)
        label = f"ENDLESS STAGE {run.stage}" if run.stage > 3 else f"STAGE {run.stage}"
        text(s, label, (W // 2, 200), 30, (240, 110, 110) if moon else ui.DIM, True, center=True)
        text(s, st["name"], (W // 2, 265), 56, (240, 80, 80) if moon else ui.GOLD, True, center=True)
        text(s, st["subtitle"], (W // 2, 325), 20, ui.DIM, center=True)
        text(s, f"Rumours speak of {boss['name']}.", (W // 2, 380), 20, ui.RED, True, center=True)
        text_block(s, boss.get("desc", ""), (W // 2 - 300, 412), 600, 16, ui.DIM)
        y = 470
        if not self.first:
            msg = "You recovered 30% HP on the journey."
            if run.stage >= 4:
                msg += f"  Second Wind: +{ENDLESS_STAGE_HP.get(run.char_id, 8)} max HP."
            text(s, msg, (W // 2, y), 16, ui.GREEN, center=True)
            y += 22
        if run.stage == BLOOD_MOON_STAGE or (run.asc >= 10 and run.stage == 3):
            text(s, "THE BLOOD MOON RISES: enemies are much stronger, crit 10% more and act 10% faster.",
                 (W // 2, y), 16, (240, 90, 90), True, center=True)
            y += 22
        if run.stage >= 4 and run.char_id in ENDLESS_PASSIVES:
            text(s, ENDLESS_PASSIVES[run.char_id], (W // 2, y), 15, ui.GOLD, center=True)
        self.draw_buttons(s)


class EndScene(Scene):
    def __init__(self, game, won):
        super().__init__(game)
        save.clear_run()   # the run is over: no continuing a finished run
        self.run = game.run
        self.won = won
        self.record = history.record_run(self.run, won)
        audio.music(None)
        audio.play("win" if won else "lose")
        announce(game, progress.on_run_end(self.run, won or self.run.stage >= 4))
        self.buttons_extra = Button((W // 2 - 120, 570, 240, 50), "Match History",
                                    lambda: game.change(MatchHistoryScene(game)), 20)
        self.buttons = [Button((W // 2 - 120, 500, 240, 56), "Main menu",
                               lambda: game.change(TitleScene(game)), 22), self.buttons_extra]

    def draw(self, s):
        s.fill(ui.BG)
        if self.won:
            text(s, "VICTORY", (W // 2, 230), 90, ui.GOLD, True, center=True)
            text(s, "Lord Ashura falls. Dawn returns to the land.", (W // 2, 320), 22, ui.TEXT, center=True)
        elif self.run.mode == "endless":
            text(s, "THE ROAD ENDS", (W // 2, 230), 80, ui.RED, True, center=True)
            text(s, f"Endless: you reached stage {self.run.stage} - {STAGES[self.run.stage]['name']}.",
                 (W // 2, 320), 22, ui.GOLD if self.run.stage >= 4 else ui.DIM, center=True)
        else:
            text(s, "FALLEN", (W // 2, 230), 90, ui.RED, True, center=True)
            text(s, "Your journey ends here. Another will take up the blade.", (W // 2, 320), 22, ui.DIM,
                 center=True)
        text(s, f"{CHARACTERS[self.run.char_id]['name']}  -  reached stage {self.run.stage}  -  "
                f"{self.run.battles_won} battles won", (W // 2, 380), 18, ui.DIM, center=True)
        if not self.won and self.run.killed_by in ENEMIES:
            text(s, f"Slain by {ENEMIES[self.run.killed_by]['name']}", (W // 2, 410), 18, (230, 130, 130),
                 True, center=True)
        if self.record:
            text(s, f"{history.fmt_duration(self.record['duration'])}  -  {self.record['gold']} {CUR} earned  -  "
                    f"saved to your match history", (W // 2, 440), 15, ui.DIM, center=True)
        self.draw_buttons(s)


# =================================================================== ? events
class EventScene(Scene):
    map_ok = True

    def music(self):
        return run_music(self.game)

    def __init__(self, game, ev, after=None):
        super().__init__(game)
        self.run = game.run
        self.ev = ev
        self.after = after or (lambda: MapScene(game))       # the screen to go to when it's over
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
        audio.play("event")
        after = self.after
        if res.get("battle"):
            eid, kind = res["battle"]
            nxt = lambda: g.change(BattleScene(g, eid, kind, run.enemy_scale(kind)))
            label = "Fight!"
        elif res.get("choose"):
            nxt = lambda: g.change(InventoryScene(g, "reward", offers=res["choose"],
                                                  on_done=after, title=self.ev["title"],
                                                  message="Pick one."))
            label = "Choose your reward"
        else:
            nxt = lambda: g.change(after())
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


# =================================================================== match history
class MatchHistoryScene(Scene):
    """Past runs (kept in this browser / on this PC across game updates): a list on the left,
    the selected run's path, final kit and cause of death on the right."""
    ROW_H = 58
    LIST = pygame.Rect(20, 118, 430, 520)

    def __init__(self, game, tab="adventure"):
        super().__init__(game)
        self.tab_btns = [Button((W - 330, 14, 150, 38), "Adventure", lambda: self.set_tab("adventure"), 17),
                         Button((W - 172, 14, 150, 38), "Arena", lambda: self.set_tab("arena"), 17)]
        self.buttons = [Button((20, 650, 140, 48), "Back", lambda: game.change(TitleScene(game)), 20)] + \
            self.tab_btns
        self.seed_btn = Button((W - 250, 650, 230, 48), "Play this seed", self.play_seed, 20)
        self.class_chips = []            # (rect, class id or None)
        self.set_tab(tab)

    def set_tab(self, tab):
        self.tab = tab
        if tab == "arena":
            self.runs = history.load_arena()
            self.sum = history.arena_summary(self.runs)
        else:
            self.runs = history.load_history()
            self.sum = history.summary(self.runs)
        self.sel, self.scroll, self.filter = 0, 0, None
        self.kit_cache = {}
        for b in self.tab_btns:
            b.col = (80, 70, 40) if b.label.lower() == tab else ui.PANEL2

    def shown(self):
        return [r for r in self.runs if self.filter in (None, r["char"])]

    def current(self):
        rs = self.shown()
        return rs[self.sel] if 0 <= self.sel < len(rs) else None

    def play_seed(self):
        r = self.current()
        if r:
            self.game.run = RunState(r["char"], seed=r["seed"], mode=r.get("mode", "story"))
            self.game.change(StageScene(self.game, first=True))

    def handle(self, ev):
        if self.tab == "adventure" and self.current() and self.seed_btn.handle(ev):
            return True
        if super().handle(ev):
            return True
        rows = self.LIST.height // self.ROW_H
        n = len(self.shown())
        if ev.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(max(0, n - rows), self.scroll - ev.y))
        elif ev.type == pygame.KEYDOWN and ev.key in (pygame.K_UP, pygame.K_DOWN) and n:
            self.sel = max(0, min(n - 1, self.sel + (1 if ev.key == pygame.K_DOWN else -1)))
            self.scroll = max(min(self.scroll, self.sel), self.sel - rows + 1)
        elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self.game.change(TitleScene(self.game))
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for rect, cid in self.class_chips:
                if rect.collidepoint(ev.pos):
                    self.filter = None if self.filter == cid else cid
                    self.sel, self.scroll = 0, 0
                    return True
            if self.LIST.collidepoint(ev.pos):
                i = self.scroll + (ev.pos[1] - self.LIST.y) // self.ROW_H
                if i < n:
                    self.sel = i
                return True
        return False

    # ---------------------------------------------------------------- drawing
    def draw_header(self, s):
        text(s, "Match History", (20, 14), 34, ui.GOLD, True)
        sm = self.sum
        if self.tab == "arena":
            avg = f"{sm['avg_wins']:.1f}" if sm["runs"] else "-"
            text(s, f"{sm['runs']} Arena runs   -   {sm['champions']} champions   -   average {avg} wins",
                 (300, 24), 18, ui.TEXT, True)
            self.class_chips = []
            x = 20
            for cid, ch in CHARACTERS.items():
                pc = sm["per_class"].get(cid)
                label = f"{ch['name']}  best {pc['best']} wins" if pc else f"{ch['name']}  no runs"
                w = ui.font(14, True).size(label)[0] + 22
                r = pygame.Rect(x, 66, w, 32)
                on = self.filter == cid
                panel(s, r, (60, 52, 36) if on else ui.PANEL, ui.GOLD if on else ch["color"], radius=6)
                text(s, label, (r.x + 11, r.y + 8), 14, ch["color"] if pc else ui.DIM, True)
                self.class_chips.append((r, cid))
                x = r.right + 8
            return
        rate = f"{100 * sm['wins'] / sm['runs']:.0f}%" if sm["runs"] else "-"
        line = f"{sm['runs']} runs   -   {sm['wins']} wins ({rate})"
        if sm["streak"]:
            line += f"   -   win streak {sm['streak']}"
        text(s, line, (300, 24), 18, ui.TEXT, True)
        self.class_chips = []
        x = 20
        for cid, ch in CHARACTERS.items():
            pc = sm["per_class"].get(cid, dict(runs=0, wins=0, best=(0, 0)))
            best = "won" if pc["best"][0] == 4 else (f"best S{pc['best'][0]}" if pc["runs"] else "no runs")
            label = f"{ch['name']}  {pc['wins']}/{pc['runs']}  {best}"
            w = ui.font(14, True).size(label)[0] + 22
            r = pygame.Rect(x, 66, w, 32)
            on = self.filter == cid
            panel(s, r, (60, 52, 36) if on else ui.PANEL, ui.GOLD if on else ch["color"], radius=6)
            text(s, label, (r.x + 11, r.y + 8), 14, ch["color"] if pc["runs"] else ui.DIM, True)
            self.class_chips.append((r, cid))
            x = r.right + 8
        if self.filter:
            text(s, "(click again to show all)", (x + 4, 74), 13, ui.DIM)

    def draw_list(self, s):
        panel(s, self.LIST.inflate(8, 8), (26, 24, 34), ui.LINE)
        rows = self.shown()
        if not rows:
            text(s, ("No finished Arena runs yet." if self.tab == "arena" else "No finished runs yet.")
                 if not self.runs else "No runs with this class.",
                 (self.LIST.centerx, self.LIST.y + 40), 18, ui.DIM, center=True)
            return
        for k in range(self.LIST.height // self.ROW_H):
            i = self.scroll + k
            if i >= len(rows):
                break
            r = rows[i]
            ch = CHARACTERS[r["char"]]
            box = pygame.Rect(self.LIST.x, self.LIST.y + k * self.ROW_H, self.LIST.width, self.ROW_H - 4)
            pygame.draw.rect(s, (70, 60, 40) if i == self.sel else (38, 34, 44), box, border_radius=6)
            pygame.draw.rect(s, ui.GOLD if r.get("won") else (150, 60, 60), (box.x, box.y, 5, box.height),
                             border_radius=3)
            ui.portrait(s, (box.x + 32, box.centery), 21, ch["color"], ch["glyph"], ch["portrait"], key=r["char"])
            if self.tab == "arena":
                good = r["champion"]
                pygame.draw.rect(s, ui.GOLD if good else (150, 60, 60), (box.x, box.y, 5, box.height),
                                 border_radius=3)
                res = "CHAMPION - 10 wins" if good else f"{r['wins']} wins  -  {r['losses']} losses"
                text(s, res, (box.x + 62, box.y + 7), 17, ui.GOLD if good else (230, 170, 120), True)
                text(s, ch["name"], (box.right - 10, box.y + 8), 14, ch["color"], True, right=True)
                text(s, f"{history.fmt_date(r['date'])}   -   {r['rounds']} rounds   -   {r.get('game', '')}",
                     (box.x + 62, box.y + 31), 13, ui.DIM)
                continue
            endless = r.get("mode") == "endless"
            if r["won"]:
                res, col = "VICTORY", ui.GOLD
            elif endless:
                res = f"Endless  -  stage {r['stage']}, floor {r['row']}"
                col = ui.GOLD if r["stage"] >= 4 else (230, 130, 130)
                pygame.draw.rect(s, (200, 60, 200) if r["stage"] >= 4 else (150, 60, 60),
                                 (box.x, box.y, 5, box.height), border_radius=3)
            else:
                res, col = f"Stage {r['stage']}  -  floor {r['row']}", (230, 130, 130)
            text(s, res, (box.x + 62, box.y + 7), 17, col, True)
            text(s, ch["name"], (box.right - 10, box.y + 8), 14, ch["color"], True, right=True)
            sub = history.fmt_date(r["date"])
            if r.get("killed_by") in ENEMIES:
                sub += "   -   " + ENEMIES[r["killed_by"]]["name"].split(",")[0]
            text(s, sub, (box.x + 62, box.y + 31), 13, ui.DIM)
        if len(rows) > self.LIST.height // self.ROW_H:
            text(s, f"scroll for more ({len(rows)})", (self.LIST.right, self.LIST.bottom + 8), 12, ui.DIM,
                 right=True)

    def kit_grid(self, r):
        key = id(r)
        if key not in self.kit_cache:
            try:
                self.kit_cache[key] = save._grid_from(r["kit"])
            except Exception:            # noqa: BLE001 - an item removed in a later version
                g = Grid(r["kit"]["w"], r["kit"]["h"])
                for it in r["kit"]["items"]:
                    if it["id"] in ITEMS:
                        g.place(ItemInst(it["id"], rot=it["rot"], level=it.get("level", 1)), it["x"], it["y"])
                self.kit_cache[key] = g
        return self.kit_cache[key]

    def draw_path(self, s, r, area):
        text(s, "PATH", (area.x, area.y), 14, ui.DIM, True)
        y = area.y + 22
        last = len(r["path"]) - 1
        stages = sorted({p["stage"] for p in r["path"]})
        if len(stages) > 4:                  # long endless runs: only the last 4 stages fit
            text(s, f"(stages 1-{stages[-5]} hidden)", (area.x + 60, area.y), 12, ui.DIM)
            stages = stages[-4:]
        for stage in stages:
            nodes = [(i, p) for i, p in enumerate(r["path"]) if p["stage"] == stage]
            if not nodes:
                continue
            text(s, f"S{stage}", (area.x, y + 4), 14, (240, 90, 90) if stage >= BLOOD_MOON_STAGE else ui.TEXT,
                 True)
            x = area.x + 32
            for i, p in nodes:
                col = NODE_STYLE.get(p["kind"], ((120, 120, 120), ""))[0]
                died = i == last and not r["won"]
                pygame.draw.circle(s, col, (x, y + 11), 10)
                hpf = p["hp"] / max(1, p["max_hp"])           # HP when you arrived: a little bar under the dot
                pygame.draw.rect(s, (50, 40, 50), (x - 9, y + 24, 18, 3))
                pygame.draw.rect(s, ui.RED, (x - 9, y + 24, int(18 * hpf), 3))
                if died:
                    pygame.draw.line(s, (255, 255, 255), (x - 6, y + 5), (x + 6, y + 17), 3)
                    pygame.draw.line(s, (255, 255, 255), (x + 6, y + 5), (x - 6, y + 17), 3)
                if pygame.Rect(x - 11, y, 22, 28).collidepoint(pygame.mouse.get_pos()):
                    self.path_tip = f"{NODE_STYLE.get(p['kind'], (0, p['kind']))[1]}  -  arrived with " \
                                    f"{p['hp']}/{p['max_hp']} HP"
                x += 26
            y += 34
        return y

    def draw_detail(self, s):
        r = self.current()
        area = pygame.Rect(470, 114, W - 490, 528)
        panel(s, area, ui.PANEL, ui.LINE)
        if not r:
            text(s, "Finish a run and it will show up here - even after the game updates.",
                 (area.centerx, area.centery), 18, ui.DIM, center=True)
            return None
        if self.tab == "arena":
            return self.draw_arena_detail(s, r, area)
        ch = CHARACTERS[r["char"]]
        x0, y0 = area.x + 20, area.y + 16
        text(s, ch["name"] + ("  -  Endless" if r.get("mode") == "endless" else ""), (x0, y0), 26, ch["color"],
             True)
        if r["won"]:
            res = "VICTORY - Lord Ashura falls"
        elif r.get("mode") == "endless":
            res = f"Endless: fell on stage {r['stage']} ({STAGES[r['stage']]['name']}), floor {r['row']}"
        else:
            res = f"Fell on stage {r['stage']}, floor {r['row']}"
        text(s, res, (x0, y0 + 32), 18, ui.GOLD if r["won"] or r["stage"] >= 4 else (230, 130, 130), True)
        text(s, f"{history.fmt_date(r['date'])}   -   {history.fmt_duration(r['duration'])}   -   "
                f"seed {r['seed']}   -   {r.get('game', 'before versions')}", (x0, y0 + 56), 13, ui.DIM)
        stats = [("Battles won", r["battles"]), ("Elites", r["elites"]), ("Bosses", r["bosses"]),
                 ("Max HP", r["max_hp"]), (f"{CUR} earned", r["gold"])]
        sx = x0
        for label, val in stats:
            text(s, str(val), (sx, y0 + 80), 22, ui.TEXT, True)
            text(s, label, (sx, y0 + 106), 12, ui.DIM)
            sx += 112
        # killed by
        if not r["won"] and r.get("killed_by") in ENEMIES:
            kx = area.right - 200
            text(s, "Killed by", (kx, y0), 13, ui.DIM, True)
            ui.portrait(s, (kx + 30, y0 + 52), 28, (150, 60, 60), "?", "enemy", key=r["killed_by"])
            text_block(s, ENEMIES[r["killed_by"]]["name"], (kx + 66, y0 + 32), 130, 15, (240, 140, 140), bold=True)
        self.path_tip = None
        py = self.draw_path(s, r, pygame.Rect(x0, y0 + 132, 500, 120))
        return self.draw_kit_and_techniques(s, r, area, x0, max(py + 8, y0 + 250))

    def draw_kit_and_techniques(self, s, r, area, x0, ky):
        text(s, "FINAL KIT", (x0, ky), 14, ui.DIM, True)
        g = self.kit_grid(r)
        cell = min(42, (area.bottom - ky - 34) // max(1, g.h))
        tip = None
        mouse = pygame.mouse.get_pos()
        for yy in range(g.h):
            for xx in range(g.w):
                pygame.draw.rect(s, (40, 36, 30), (x0 + xx * cell, ky + 22 + yy * cell, cell, cell))
                pygame.draw.rect(s, (66, 58, 48), (x0 + xx * cell, ky + 22 + yy * cell, cell, cell), 1)
        for inst in g.items:
            px, py2 = x0 + inst.x * cell, ky + 22 + inst.y * cell
            ui.draw_item(s, inst.id, inst.shape, px, py2, cell, level=inst.level, rot=inst.rot)
            for cx, cy in inst.shape:
                if pygame.Rect(px + cx * cell, py2 + cy * cell, cell, cell).collidepoint(mouse):
                    tip = inst
        # techniques
        tx = x0 + g.w * cell + 30
        text(s, "TECHNIQUES", (tx, ky), 14, ui.DIM, True)
        ty = ky + 22
        if not r["techniques"]:
            text(s, "none", (tx, ty), 14, ui.DIM)
        for tid in r["techniques"]:
            t = TECHNIQUES.get(tid)
            if t:
                ty = text_block(s, t["name"], (tx, ty), area.right - tx - 16, 15, ui.GREEN, bold=True)
                ty = text_block(s, t["desc"], (tx, ty), area.right - tx - 16, 12, ui.DIM) + 6
        return tip

    def draw_arena_detail(self, s, r, area):
        ch = CHARACTERS[r["char"]]
        x0, y0 = area.x + 20, area.y + 16
        text(s, ch["name"] + "  -  Arena", (x0, y0), 26, ch["color"], True)
        res = "CHAMPION - 10 wins" if r["champion"] else f"Out of hearts after {r['wins']} wins"
        text(s, res, (x0, y0 + 32), 18, ui.GOLD if r["champion"] else (230, 130, 130), True)
        text(s, f"{history.fmt_date(r['date'])}   -   {history.fmt_duration(r['duration'])}   -   {r.get('game', '')}",
             (x0, y0 + 56), 13, ui.DIM)
        real = sum(1 for f in r["fights"] if not f.get("bot"))
        stats = [("Wins", r["wins"]), ("Losses", r["losses"]), ("Rounds", r["rounds"]), ("Max HP", r["max_hp"]),
                 ("vs players", real)]
        sx = x0
        for label, val in stats:
            text(s, str(val), (sx, y0 + 80), 22, ui.TEXT, True)
            text(s, label, (sx, y0 + 106), 12, ui.DIM)
            sx += 112
        text(s, "FIGHTS  (hover for the opponent)", (x0, y0 + 132), 14, ui.DIM, True)
        mouse = pygame.mouse.get_pos()
        self.path_tip = None
        for i, f in enumerate(r["fights"]):
            box = pygame.Rect(x0 + i * 38, y0 + 156, 32, 32)
            pygame.draw.rect(s, ui.GOLD if f["won"] else (150, 60, 60), box, border_radius=5)
            text(s, str(f["round"]), box.center, 14, (20, 16, 20), True, center=True)
            if f.get("vs_cls") in CHARACTERS:     # a small class-colour bar: who you fought
                pygame.draw.rect(s, CHARACTERS[f["vs_cls"]]["color"], (box.x + 3, box.bottom - 6, box.w - 6, 3))
            if box.collidepoint(mouse):
                who = f.get("vs") or "?"
                kind = "AI ghost" if f.get("bot") else "player"
                cls = CHARACTERS.get(f.get("vs_cls"), {}).get("name", "")
                rec = f", {f['vs_record']} at the time" if f.get("vs_record") else ""
                self.path_tip = (f"Round {f['round']}: {'beat' if f['won'] else 'lost to'} {who} "
                                 f"({cls} {kind}{rec})")
        return self.draw_kit_and_techniques(s, r, area, x0, y0 + 210)

    def draw(self, s):
        s.fill(ui.BG)
        self.draw_header(s)
        self.draw_list(s)
        tip = self.draw_detail(s)
        self.draw_buttons(s)
        if self.current() and self.tab == "adventure":
            self.seed_btn.draw(s)
            text(s, "Same map, shops and bosses", (W - 260, 672), 13, ui.DIM, right=True)
        mouse = pygame.mouse.get_pos()
        if tip is not None:
            rr = pygame.Rect(min(mouse[0] + 16, W - 350), mouse[1] + 16, 330, 100)
            ui.draw_tooltip(s, tip.id, rr, eff=tip.data, fit=True)
        elif getattr(self, "path_tip", None):
            w = ui.font(14, True).size(self.path_tip)[0] + 20
            rr = pygame.Rect(min(mouse[0] + 14, W - w - 4), mouse[1] + 16, w, 28)
            panel(s, rr, ui.PANEL2, ui.LINE, radius=5)
            text(s, self.path_tip, (rr.x + 10, rr.y + 6), 14, ui.TEXT, True)


# =================================================================== arena (online ghost PvP)
CLASS_NAMES = {cid: ch["name"] for cid, ch in CHARACTERS.items()}


def arena_next_round(game):
    """Start the next Arena round: technique pick (rounds 3/6/9), then the shop."""
    run = game.run
    rnd = arena.start_round(run)

    def shop():
        msg = (f"Round {rnd}: +{arena.income(rnd)} {CUR}. Buy, merge and arrange your kit, then Fight. "
               f"Your kit this round is uploaded as a ghost for other players.")
        return InventoryScene(game, "shop", offers=run.shop_offers(), on_done=lambda: MapScene(game),
                              title=f"Arena - Round {rnd}", message=msg)
    arena.gen_floor(run)                         # a fresh random floor: fights, nodes, merchant, ghost
    hint(game, "arena_floor", "Each Arena round is a small floor. Floor fights are practice: lose one and you "
                              "just get no rewards. The ghost duel at the end is what counts.")

    def floor():
        return MapScene(game)
    if arena.wants_technique(run):
        return TechniqueScene(game, then=floor)
    return floor()


class ArenaLobbyScene(Scene):
    """Rules, your name, your best run, and this version's leaderboard."""
    music = "arena"

    def __init__(self, game):
        super().__init__(game)
        game.run = None
        self.profile = online.profile()
        self.editing = False
        self.name_buf = ""
        self.board_req = online.top_scores(VERSION) if online.enabled() else None
        self.board = None
        self.buttons = [
            Button((W // 2 - 150, 600, 300, 60), "Enter the Arena",
                   lambda: game.change(CharSelectScene(game, arena_mode=True)), 26),
            Button((20, 650, 140, 48), "Back", lambda: game.change(TitleScene(game)), 20),
            Button((420, 236, 150, 36), "Change name", self.start_edit, 16),
        ]

    def start_edit(self):
        if self.editing:                 # the button doubles as "save"
            self.profile = online.set_name(self.name_buf)
            self.editing = False
            return
        self.editing = True
        self.name_buf = self.profile["name"]
        try:
            pygame.key.start_text_input()
        except pygame.error:
            pass

    def handle(self, ev):
        if self.editing and ev.type == pygame.TEXTINPUT:      # typed letters (desktop and browser)
            for ch in ev.text:
                if len(self.name_buf) < 14 and (ch == " " or online.clean_name("x" + ch) != "x"):
                    self.name_buf += ch
            return True
        if self.editing and ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.profile = online.set_name(self.name_buf)
                self.editing = False
            elif ev.key == pygame.K_ESCAPE:
                self.editing = False
            elif ev.key == pygame.K_BACKSPACE:
                self.name_buf = self.name_buf[:-1]
            return True
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self.game.change(TitleScene(self.game))
            return True
        return super().handle(ev)

    def update(self, dt):
        if self.board_req is not None and self.board is None and self.board_req.done:
            self.board = self.board_req.json([]) if self.board_req.ok else "error"

    def draw(self, s):
        s.fill(ui.BG)
        text(s, "THE ARENA", (W // 2, 34), 46, ui.GOLD, True, center=True)
        text(s, "Fight the ghosts of other players' kits", (W // 2, 82), 18, ui.DIM, center=True)
        left = pygame.Rect(30, 110, 560, 470)
        panel(s, left, ui.PANEL, ui.LINE)
        y = left.y + 16
        rules = [
            "Each round: get gold, shop, merge and arrange your kit.",
            "Then fight a ghost: another player's kit from the SAME round of the same version.",
            f"Win {arena.MAX_WINS} fights to become champion. Each loss costs a heart - lose all "
            f"{arena.HEARTS} and the run ends.",
            f"You fully heal before every fight, and gain +{arena.HP_PER_ROUND} max HP each round.",
            "Learn a technique at rounds 3, 6 and 9. Rarer items appear in later rounds.",
            "If nobody has played that round yet, you face an AI ghost instead.",
        ]
        for line in rules:
            y = text_block(s, "-  " + line, (left.x + 18, y), left.width - 36, 16, ui.TEXT) + 8
        y = max(y, left.y + 220)
        text(s, "Your name", (left.x + 18, y + 14), 15, ui.DIM, True)
        box = pygame.Rect(left.x + 110, y + 6, 260, 36)
        pygame.draw.rect(s, (30, 28, 36), box, border_radius=5)
        pygame.draw.rect(s, ui.GOLD if self.editing else ui.LINE, box, 2, border_radius=5)
        shown = self.name_buf + ("_" if (pygame.time.get_ticks() // 400) % 2 else "") if self.editing \
            else self.profile["name"]
        text(s, shown, (box.x + 10, box.y + 8), 19, ui.TEXT, True)
        self.buttons[2].rect.topleft = (box.right + 12, box.y)
        self.buttons[2].label = "Save name" if self.editing else "Change name"
        if self.editing:
            text(s, "Type a name, then Enter (Esc cancels)", (box.x, box.bottom + 4), 13, ui.DIM)
        y += 64
        b = online.best()
        if b:
            text(s, f"Your best: {b['wins']} wins, {b['hearts']} hearts left ({CLASS_NAMES.get(b['cls'], '?')}, "
                    f"v{b['version']})", (left.x + 18, y), 16, ui.GOLD, True)
        else:
            text(s, "Your best: no Arena runs yet", (left.x + 18, y), 16, ui.DIM, True)
        y += 34
        if online.enabled():
            text(s, "Online: your ghosts are shared with other players.", (left.x + 18, y), 15, ui.GREEN, True)
        else:
            text_block(s, "Offline: every opponent is an AI ghost and there is no leaderboard. "
                          "(The game's owner can switch online on - see the README.)",
                       (left.x + 18, y), left.width - 36, 14, (230, 170, 120))
        # leaderboard
        right = pygame.Rect(610, 110, W - 640, 470)
        panel(s, right, ui.PANEL, ui.LINE)
        text(s, f"LEADERBOARD  -  {VERSION}", (right.x + 18, right.y + 14), 18, ui.GOLD, True)
        if not online.enabled():
            text(s, "Offline", (right.centerx, right.centery), 20, ui.DIM, center=True)
        elif self.board is None:
            text(s, "Loading...", (right.centerx, right.centery), 20, ui.DIM, center=True)
        elif self.board == "error" or not isinstance(self.board, list):
            text(s, "Couldn't reach the server.", (right.centerx, right.centery), 18, (230, 130, 130),
                 center=True)
        elif not self.board:
            text(s, "No champions yet - be the first!", (right.centerx, right.centery), 18, ui.DIM, center=True)
        else:
            yy = right.y + 50
            for i, row in enumerate(self.board[:12]):
                ch = CHARACTERS.get(row.get("cls"), {})
                col = ui.GOLD if i == 0 else ui.TEXT
                text(s, f"{i + 1}.", (right.x + 18, yy), 17, ui.DIM, True)
                text(s, str(row.get("name", "?"))[:14], (right.x + 52, yy), 17, col, True)
                text(s, ch.get("name", "?"), (right.x + 230, yy), 15, ch.get("color", ui.DIM), True)
                text(s, f"{row.get('wins', 0)} wins", (right.x + 360, yy), 17, col, True)
                draw_hearts(s, (right.x + 470, yy + 9), int(row.get("hearts", 0)), size=6)
                yy += 33
        self.draw_buttons(s)


class ArenaMatchScene(Scene):
    """Upload your ghost, find an opponent from the same round, then fight."""
    WAIT = 6.0

    def __init__(self, game):
        super().__init__(game)
        self.run = run = game.run
        self.profile = online.profile()
        self.rnd = run.arena["round"]
        self.opp = None
        self.t = 0.0
        self.rng = random.Random(run.rng.randrange(1 << 30))
        if online.enabled():
            online.upload_ghost(arena.ghost_record(run, self.profile))     # fire and forget
            self.req = online.find_ghosts(self.rnd, VERSION, self.profile["id"])
        else:
            self.req = None
        self.fight_btn = Button((W // 2 - 140, 560, 280, 60), "Fight!", self.fight, 28)
        self.buttons = [Button((20, 650, 160, 48), "Edit kit", self.edit, 20)]

    def edit(self):
        g = self.game
        g.change(InventoryScene(g, "manage", on_done=lambda: ArenaMatchScene(g), title="Your kit",
                                message="Rearrange, then press Done to find an opponent."))

    def update(self, dt):
        self.t += dt
        if self.opp is not None:
            return
        if self.req is None or self.req.done or self.t > self.WAIT:
            found = self.req.json([]) if self.req is not None and self.req.ok else []
            self.opp = arena.pick_opponent(found if isinstance(found, list) else [], self.profile["id"], self.rnd,
                                           self.rng)
            self.opp_run = arena.ghost_run(self.opp)
            self.buttons.append(self.fight_btn)

    def fight(self):
        g, run, opp = self.game, self.run, self.opp

        def result(won):
            state = arena.apply_result(run, won, opp)
            g.change(ArenaResultScene(g, won, opp, state))
        g.change(BattleScene(g, None, "pvp", ghost=self.opp_run, ghost_rec=opp, on_result=result))

    def draw(self, s):
        s.fill(ui.BG)
        top_bar(s, self.run, "Matchmaking")
        if self.opp is None:
            dots = "." * (1 + int(self.t * 3) % 3)
            text(s, f"Looking for a round-{self.rnd} opponent{dots}", (W // 2, 300), 30, ui.TEXT, True,
                 center=True)
            return
        o = self.opp
        ch = CHARACTERS[o["cls"]]
        text(s, f"Round {self.rnd} opponent", (W // 2, 110), 22, ui.DIM, True, center=True)
        ui.portrait(s, (W // 2, 230), 70, ch["color"], ch["glyph"], ch["portrait"], key=o["cls"])
        text(s, o["name"], (W // 2, 330), 36, ch["color"], True, center=True)
        kind = "AI ghost" if o.get("bot") else "Player ghost"
        text(s, f"{kind}  -  {ch['name']}  -  {o['wins']} wins, {o['losses']} losses so far", (W // 2, 375), 18,
             ui.TEXT, center=True)
        n_items = len(self.opp_run.bag.items)
        text(s, f"{n_items} items, {self.opp_run.max_hp} HP" +
             (f", techniques: {', '.join(TECHNIQUES[t]['name'] for t in self.opp_run.techniques)}"
              if self.opp_run.techniques else ""), (W // 2, 405), 15, ui.DIM, center=True)
        text(s, f"You: {CHARACTERS[self.run.char_id]['name']}, {len(self.run.bag.items)} items, "
                f"{self.run.max_hp} HP", (W // 2, 470), 18, ui.TEXT, True, center=True)
        self.draw_buttons(s)


class ArenaResultScene(Scene):
    def __init__(self, game, won, opp, state):
        super().__init__(game)
        self.run = game.run
        self.won, self.opp, self.state = won, opp, state
        if state == "next":
            self.buttons = [Button((W // 2 - 140, 560, 280, 60), "Next round",
                                   lambda: game.change(arena_next_round(game)), 26)]
        else:
            self.buttons = [Button((W // 2 - 140, 560, 280, 60), "See results",
                                   lambda: game.change(ArenaEndScene(game)), 26)]

    def draw(self, s):
        s.fill(ui.BG)
        top_bar(s, self.run, "Arena")
        a = self.run.arena
        text(s, "VICTORY" if self.won else "DEFEAT", (W // 2, 200), 80, ui.GOLD if self.won else ui.RED, True,
             center=True)
        text(s, f"vs {self.opp['name']}", (W // 2, 270), 22, ui.DIM, center=True)
        text(s, f"{a['wins']} / {arena.MAX_WINS} wins", (W // 2, 340), 30, ui.TEXT, True, center=True)
        hs = arena.hearts(self.run)
        draw_hearts(s, (W // 2 - (arena.HEARTS - 1) * 13, 400), hs, size=11)
        if not self.won and self.state == "next":
            text(s, f"Lost a heart - {hs} left", (W // 2, 440), 18, (230, 130, 130), True, center=True)
        self.draw_buttons(s)


class ArenaEndScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.run = run = game.run
        self.profile = online.profile()
        self.rec = arena.score_record(run, self.profile)
        self.new_best = online.record_best(self.rec)
        history.record_arena(run)
        announce(game, progress.on_arena_end(run))
        self.req = online.submit_score(self.rec) if online.enabled() else None
        self.buttons = [Button((W // 2 - 420, 600, 260, 56), "Arena lobby",
                               lambda: game.change(ArenaLobbyScene(game)), 22),
                        Button((W // 2 - 130, 600, 260, 56), "Match History",
                               lambda: game.change(MatchHistoryScene(game, tab="arena")), 22),
                        Button((W // 2 + 160, 600, 260, 56), "Main menu",
                               lambda: game.change(TitleScene(game)), 22)]

    def draw(self, s):
        s.fill(ui.BG)
        a = self.run.arena
        champ = a["wins"] >= arena.MAX_WINS
        text(s, "CHAMPION" if champ else "ARENA RUN OVER", (W // 2, 150), 70 if champ else 56,
             ui.GOLD if champ else ui.RED, True, center=True)
        text(s, f"{CHARACTERS[self.run.char_id]['name']}  -  {a['wins']} wins  -  {a['round']} rounds",
             (W // 2, 230), 24, ui.TEXT, True, center=True)
        draw_hearts(s, (W // 2 - (arena.HEARTS - 1) * 13, 280), arena.hearts(self.run), size=11)
        if self.new_best:
            text(s, "New personal best!", (W // 2, 320), 20, ui.GOLD, True, center=True)
        if self.req is None:
            msg, col = "Offline - score kept on this device only.", ui.DIM
        elif not self.req.done:
            msg, col = "Posting your score...", ui.DIM
        elif self.req.ok:
            msg, col = "Score posted to the leaderboard.", ui.GREEN
        else:
            msg, col = "Couldn't post your score (no connection?).", (230, 130, 130)
        text(s, msg, (W // 2, 350), 16, col, True, center=True)
        y = 400
        text(s, "Your fights", (W // 2, y), 16, ui.DIM, True, center=True)
        x0 = W // 2 - len(a["history"]) * 17
        for i, h in enumerate(a["history"]):
            pygame.draw.rect(s, ui.GOLD if h["won"] else (150, 60, 60), (x0 + i * 34, y + 26, 28, 28),
                             border_radius=5)
            text(s, str(h["round"]), (x0 + i * 34 + 14, y + 32), 14, (20, 16, 20), True, center=True)
        self.draw_buttons(s)


# =================================================================== settings
class SettingsScene(Scene):
    music = "title"
    ROWS = [("music", "Music volume"), ("sfx", "Sound effects"), ("speed", "Default battle speed"),
            ("shake", "Screen shake"), ("colorblind", "Colour-blind palette"), ("hints", "First-time tips")]

    def __init__(self, game):
        super().__init__(game)
        self.buttons = [Button((W // 2 - 110, 620, 220, 54), "Back", lambda: game.change(TitleScene(game)), 22),
                        Button((W // 2 + 150, 548, 200, 40), "Show tips again", self.reset_hints, 16)]
        self.row_btns = []
        for i, (key, _) in enumerate(self.ROWS):
            y = 160 + i * 64
            if key in ("music", "sfx"):
                self.row_btns += [Button((W // 2 + 40, y, 50, 44), "-", lambda k=key: self.vol(k, -0.1), 22),
                                  Button((W // 2 + 240, y, 50, 44), "+", lambda k=key: self.vol(k, 0.1), 22)]
            elif key == "speed":
                for j, sp in enumerate((1, 2, 4)):
                    self.row_btns.append(Button((W // 2 + 40 + j * 86, y, 76, 44), f"{sp}x",
                                                lambda sp=sp: settings.set("speed", sp), 18))
            else:
                self.row_btns.append(Button((W // 2 + 40, y, 250, 44), "", lambda k=key: self.toggle(k), 18))
        self.buttons += self.row_btns

    def vol(self, key, d):
        settings.set(key, round(max(0.0, min(1.0, settings.get()[key] + d)), 2))
        audio.refresh_volume()
        audio.play("click")

    def toggle(self, key):
        settings.set(key, not settings.get()[key])
        if key == "colorblind":
            ui.apply_palette(settings.get()["colorblind"])

    def reset_hints(self):
        progress.data()["hints"] = []
        progress.save()
        self.game.toast("Tips will show again.", (150, 210, 255))

    def handle(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self.game.change(TitleScene(self.game))
            return True
        return super().handle(ev)

    def draw(self, s):
        s.fill(ui.BG)
        text(s, "Settings", (W // 2, 70), 44, ui.GOLD, True, center=True)
        st = settings.get()
        panel(s, pygame.Rect(W // 2 - 360, 136, 720, 6 * 64 + 20))
        for i, (key, label) in enumerate(self.ROWS):
            y = 160 + i * 64
            text(s, label, (W // 2 - 330, y + 10), 20, ui.TEXT, True)
            if key in ("music", "sfx"):
                ui.bar(s, (W // 2 + 100, y + 14, 130, 16), st[key], ui.GOLD)
                text(s, f"{int(st[key] * 100)}%", (W // 2 + 300, y + 10), 18, ui.DIM, True)
        for b in self.row_btns:
            if b.label.endswith("x"):
                b.col = (80, 70, 40) if st["speed"] == int(b.label[0]) else ui.PANEL2
        bi = 0
        for key, _ in self.ROWS:
            if key in ("music", "sfx"):
                bi += 2
            elif key == "speed":
                bi += 3
            else:
                b = self.row_btns[bi]
                b.label = "On" if st[key] else "Off"
                b.col = (50, 80, 50) if st[key] else ui.PANEL2
                bi += 1
        text(s, "Colour-blind palette: heals become blue, poison purple, damage vermillion.", (W // 2 - 330, 556),
             14, ui.DIM)
        self.draw_buttons(s)


# =================================================================== achievements & stats
class AchievementsScene(Scene):
    music = "title"

    def __init__(self, game):
        super().__init__(game)
        self.buttons = [Button((20, 650, 140, 48), "Back", lambda: game.change(TitleScene(game)), 20)]
        self.stats = progress.lifetime_stats(history.load_history(), history.load_arena())

    def handle(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self.game.change(TitleScene(self.game))
            return True
        return super().handle(ev)

    def draw(self, s):
        s.fill(ui.BG)
        n = sum(1 for a in progress.ACHIEVEMENTS if progress.unlocked(a[0]))
        text(s, "Achievements", (24, 16), 34, ui.GOLD, True)
        text(s, f"{n} / {len(progress.ACHIEVEMENTS)} unlocked", (290, 28), 18, ui.DIM, True)
        cw, chh = 380, 64
        for i, (aid, name, desc) in enumerate(progress.ACHIEVEMENTS):
            col, row = i % 2, i // 2
            r = pygame.Rect(24 + col * (cw + 12), 74 + row * (chh + 8), cw, chh)
            got = progress.unlocked(aid)
            panel(s, r, (52, 44, 28) if got else ui.PANEL, ui.GOLD if got else ui.LINE, radius=8)
            pygame.draw.circle(s, ui.GOLD if got else (60, 56, 70), (r.x + 30, r.centery), 18)
            text(s, "✓" if got and not ui.WEB else ("!" if got else "?"), (r.x + 30, r.centery), 18,
                 (30, 24, 20) if got else ui.DIM, True, center=True)
            text(s, name, (r.x + 60, r.y + 9), 17, ui.TEXT if got else ui.DIM, True)
            text_block(s, desc, (r.x + 60, r.y + 33), cw - 70, 13, ui.DIM)
        # lifetime stats
        st = self.stats
        sp = pygame.Rect(820, 74, W - 844, 568)
        panel(s, sp)
        x, y = sp.x + 18, sp.y + 14
        text(s, "LIFETIME STATS", (x, y), 16, ui.GOLD, True)
        y += 32
        rows = [("Runs", st["runs"]), ("Story wins", st["wins"]), ("Enemies defeated", st["kills"]),
                ("Bosses defeated", st["bosses"]), ("Deepest stage", st["deepest"] or "-"),
                ("Arena runs", st["arena_runs"]), ("Best Arena run", f"{st['arena_best']} wins")]
        for label, val in rows:
            text(s, label, (x, y), 15, ui.DIM)
            text(s, str(val), (sp.right - 18, y), 15, ui.TEXT, True, right=True)
            y += 24
        y += 10
        text(s, "Most defeated", (x, y), 15, ui.GOLD, True)
        y += 24
        for eid, c in st["most_killed"][:4] or [("-", 0)]:
            name = ENEMIES[eid]["name"].split(",")[0] if eid in ENEMIES else "-"
            text(s, name, (x, y), 14, ui.TEXT)
            text(s, f"x{c}" if c else "", (sp.right - 18, y), 14, ui.DIM, right=True)
            y += 21
        y += 8
        text(s, "Your nemesis", (x, y), 15, (230, 130, 130), True)
        y += 24
        for eid, c in st["nemesis"][:2] or [("-", 0)]:
            name = ENEMIES[eid]["name"].split(",")[0] if eid in ENEMIES else "-"
            text(s, name, (x, y), 14, ui.TEXT)
            text(s, f"killed you {c}x" if c else "", (sp.right - 18, y), 14, ui.DIM, right=True)
            y += 21
        y += 8
        text(s, "Favourite items", (x, y), 15, (150, 230, 200), True)
        y += 26
        for k, (iid, c) in enumerate(st["favourite"][:6]):
            pic = ui.art(iid, 30)
            px = x + k * 64
            if pic:
                s.blit(pic, pic.get_rect(center=(px + 20, y + 16)))
            text(s, f"x{c}", (px + 20, y + 36), 12, ui.DIM, center=True)
        if not st["favourite"]:
            text(s, "Finish a run to see them.", (x, y), 14, ui.DIM)
        self.draw_buttons(s)
