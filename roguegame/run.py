"""State of a single-player run: hero, gold, kit, map. Pure Python (no pygame).

Every run has a seed. The seed decides the map layout, which regular enemies
appear in each stage, which villain rules each stage, and which ? events show up.
"""
import os
import random
import time

from .data import (ITEMS, CHARACTERS, STAGES, START_GOLD, BAG_SIZE, STASH_SIZE, GOLD_REWARD, RARITIES,
                   TECHNIQUES, FIGHTS_PER_RUN, BALANCE, ENEMY_LOOT, max_level, REST_HEAL,
                   SIGNATURE_DROP_CHANCE, enemy_tier, endless_mult, BLOOD_MOON_STAGE, CONSUMABLES,
                   MAX_CONSUMABLES)
from .inventory import Grid, ItemInst

MAP_ROWS = 6


def gen_map(rng, stage):
    rows = []
    for r in range(MAP_ROWS):
        n = 2 if r == 0 else rng.choice([2, 3, 3, 4])
        row = []
        for c in range(n):
            if r == 0:
                kind = "fight"
            elif r == MAP_ROWS - 1:
                kind = rng.choice(["rest", "shop", "rest", "event"])
            else:
                pool = ["fight"] * 8 + ["shop"] * 2 + ["treasure"] * 1 + ["event"] * 4
                if r >= 2:
                    pool += ["elite"] * 2 + ["rest"] * 2
                kind = rng.choice(pool)
            row.append(dict(row=r, col=c, kind=kind, x=(c + 0.5) / n, links=[]))
        rows.append(row)
    if not any(n["kind"] == "shop" for row in rows[1:4] for n in row):
        rng.choice(rows[2])["kind"] = "shop"
    if not any(n["kind"] == "elite" for row in rows[2:5] for n in row):
        rng.choice(rows[3])["kind"] = "elite"
    if sum(n["kind"] == "event" for row in rows for n in row) < 2:
        rng.choice(rows[1])["kind"] = "event"
        rng.choice(rows[4])["kind"] = "event"
    rows.append([dict(row=MAP_ROWS, col=0, kind="boss", x=0.5, links=[])])
    for r in range(len(rows) - 1):
        cur, nxt = rows[r], rows[r + 1]
        for node in cur:
            near = [j for j, m in enumerate(nxt) if abs(m["x"] - node["x"]) <= 0.34]
            if not near:
                near = [min(range(len(nxt)), key=lambda j: abs(nxt[j]["x"] - node["x"]))]
            node["links"] = near
        for j, m in enumerate(nxt):
            if not any(j in node["links"] for node in cur):
                closest = min(cur, key=lambda nd: abs(nd["x"] - m["x"]))
                closest["links"].append(j)
    return rows


def fresh_seed(extra=0):
    """A new random seed for every run. Mixes the clock (nanoseconds), a high-resolution timer, the OS's
    random source when there is one, and anything extra (the menu passes the mouse position), so two runs
    never start the same even in a browser, where Python's own random module can start identically."""
    mix = time.time_ns() ^ (time.perf_counter_ns() << 7) ^ (int(extra) * 2654435761)
    try:
        mix ^= int.from_bytes(os.urandom(8), "little")
    except (NotImplementedError, OSError):
        pass
    return random.Random(mix).randrange(1 << 30)


class RunState:
    def __init__(self, char_id, seed=None, mode="story", asc=0):
        self.mode = mode         # "story" (3 stages) or "endless" (keeps going after stage 3)
        self.asc = asc           # ascension level (0 = normal), see ASCENSION in data.py
        self.consumables = []    # used up in the next battle
        self.flags = {}          # multi-stage event state, e.g. {"tanuki": "helped"}
        self.stats = dict(dmg=0, items={}, battles=0)   # for the end-of-run screen
        self.acquired = {}       # item id -> stage it was first gained (run reports; starting kit = 1)
        self.seed = seed if seed is not None else fresh_seed()
        self.rng = random.Random(self.seed)
        self.char_id = char_id
        ch = CHARACTERS[char_id]
        self.max_hp = int(round(ch["hp"] * BALANCE.get("class_hp", {}).get(char_id, 1.0)))
        if asc >= 4:                                     # A4: weary traveller
            self.max_hp = int(self.max_hp * 0.9)
        self.hp = self.max_hp
        self.gold = START_GOLD
        self.bag = Grid(*BAG_SIZE)
        self.stash = Grid(*STASH_SIZE)
        for iid in ch["start"]:
            inst = ItemInst(iid)
            if not self.bag.first_fit(inst):
                self.stash.first_fit(inst)
        # the seed picks this run's cast of enemies and villains
        self.fight_pool = {s: self.rng.sample(STAGES[s]["fights"], FIGHTS_PER_RUN) for s in STAGES}
        self.boss_of = {s: self.rng.choice(STAGES[s].get("bosses", [STAGES[s]["boss"]])) for s in STAGES}
        self.seen_events = []
        self.stage = 1
        self.map = gen_map(self.rng, 1)
        self.pos = None          # (row, col) of last visited node
        self.battles_won = 0
        self.rerolls = 0
        self.techniques = []
        self.kills = []          # enemy ids defeated (for stats / the balance tool)
        # match-history tracking
        self.started = time.time()
        self.path = []           # every node visited: dict(stage, row, kind, hp, max_hp)
        self.gold_earned = 0
        self.killed_by = None

    # ---------------- techniques (permanent upgrades)
    def technique_choices(self, n=3):
        late = self.stage >= 4                       # endless techniques only from endless stage 4 on
        pool = [t for t, d in TECHNIQUES.items() if d["cls"] == self.char_id and t not in self.techniques
                and (late or not d.get("endless"))]
        return self.rng.sample(pool, min(n, len(pool)))

    def learn(self, tid):
        self.techniques.append(tid)
        bonus = TECHNIQUES[tid].get("max_hp", 0)
        self.max_hp += bonus
        self.hp += bonus

    # ---------------- difficulty
    def enemy_scale(self, kind):
        """Stage multiplier x enemy-type multiplier x the stage's floor ramp (non-bosses; see FLOOR_RAMP).
        The first battle of a run is extra gentle (FIRST_FIGHT_SCALE)."""
        if self.stage > 3:
            mult = BALANCE["stage_mult"].get(3, 1.0) * endless_mult(self.stage)
        else:
            mult = BALANCE["stage_mult"].get(self.stage, 1.0)
        mult *= {"fight": BALANCE["fight_mult"], "elite": BALANCE["elite_mult"],
                 "boss": BALANCE["boss_mult"]}.get(kind, BALANCE["fight_mult"])
        if self.asc >= 1 and kind == "elite":
            mult *= 1.15
        if self.asc >= 3 and kind == "boss":
            mult *= 1.15
        if self.asc >= 7 and kind == "fight":
            mult *= 1.10
        if kind == "boss" or self.pos is None:
            return mult
        from .data import floor_ramp, FIRST_FIGHT_SCALE
        mult *= floor_ramp(self.stage, self.pos[0])
        if self.is_first_battle():
            mult *= FIRST_FIGHT_SCALE
        return mult

    def is_first_battle(self):
        """True until the run's first battle has been fought."""
        return self.stage == 1 and not self.stats.get("battles") and not self.battles_won

    def boss_id(self, stage=None):
        self.ensure_stage(stage or self.stage)
        return self.boss_of[stage or self.stage]

    @property
    def endless(self):
        return self.mode == "endless"

    @property
    def blood_moon(self):
        return self.stage >= BLOOD_MOON_STAGE

    def ensure_stage(self, n):
        """Endless stages pick their cast when you get there (own rng: story seeds stay identical).
        The villain is never the same one as the stage before."""
        if n in self.fight_pool:
            return
        rng = random.Random(f"{self.seed}:endless:{n}")
        st = STAGES[n]
        self.fight_pool[n] = rng.sample(st["fights"], min(FIGHTS_PER_RUN, len(st["fights"])))
        prev = self.boss_of.get(n - 1)
        self.boss_of[n] = rng.choice([b for b in st["bosses"] if b != prev] or st["bosses"])

    # ---------------- map
    def available_nodes(self):
        if self.pos is None:
            return [(0, c) for c in range(len(self.map[0]))]
        r, c = self.pos
        if r + 1 >= len(self.map):
            return []
        return [(r + 1, j) for j in self.map[r][c]["links"]]

    def node(self, rc):
        return self.map[rc[0]][rc[1]]

    def visit(self, rc):
        self.pos = rc
        self.node(rc)["visited"] = True
        self.path.append(dict(stage=self.stage, row=rc[0], kind=self.node(rc)["kind"], hp=self.hp,
                              max_hp=self.max_hp))
        return self.node(rc)

    def next_stage(self):
        self.stage += 1
        self.ensure_stage(self.stage)
        if self.stage >= 4:                              # Second Wind (endless)
            from .data import ENDLESS_STAGE_HP
            gain = ENDLESS_STAGE_HP.get(self.char_id, 8)
            self.max_hp += gain
            self.hp += gain
        self.map = gen_map(self.rng, self.stage)
        self.pos = None
        from .events import place_omens
        place_omens(self)                                # earlier choices come back as Omen nodes
        self.hp = min(self.max_hp, self.hp + int(self.max_hp * 0.3))

    def rest(self):
        frac = 0.2 if self.asc >= 6 else REST_HEAL
        self.hp = min(self.max_hp, self.hp + int(self.max_hp * frac))

    def train(self):
        self.max_hp += 5
        self.hp += 5

    # ---------------- items
    def all_items(self):
        return self.bag.items + self.stash.items

    def owned_ids(self):
        return {i.id for i in self.all_items()}

    def item_pool(self, rarity):
        owned = self.owned_ids() if rarity == "legendary" else set()   # legendaries are unique
        return [i for i in ITEMS.values()
                if not i["enemy"] and not i.get("loot") and not i.get("recipe") and i["rarity"] == rarity
                and i["cls"] in (None, self.char_id) and i["id"] not in owned]

    def roll_item(self, bias=0):
        weights = STAGES[self.stage]["rarity"]
        rar = self.rng.choices(RARITIES, weights=[weights[r] for r in RARITIES])[0]
        idx = min(3, RARITIES.index(rar) + bias)
        pool = []
        while not pool and idx >= 0:
            pool = self.item_pool(RARITIES[idx])
            idx -= 1
        weighted = [i for i in pool for _ in range(2 if i["cls"] else 1)]   # class items twice as likely
        return self.rng.choice(weighted)["id"]

    def shop_offers(self, n=5):
        return [self.roll_item() for _ in range(n)]

    def reward_choices(self, kind, n=3):
        bias = {"fight": 0, "treasure": 1, "event": 1, "elite": 1, "boss": 2}[kind]
        out, tries = [], 0
        while len(out) < n:
            iid = self.roll_item(bias)
            tries += 1
            if iid not in out or tries > 30:
                out.append(iid)
        return out

    def loot_of(self, enemy_id):
        """The enemy's signature (enemy-exclusive) item."""
        return ENEMY_LOOT.get(enemy_id)

    def roll_drop(self, enemy_id, carried, rng=None):
        """What a beaten enemy drops: its signature item (chance by tier) or one of the other items
        it was carrying, at the level it had. Returns (item_id, level, is_signature) or None."""
        rng = rng or self.rng
        signature = ENEMY_LOOT.get(enemy_id)
        others = [(i, lvl) for i, lvl in carried if i != signature]
        if signature and (not others or rng.random() < SIGNATURE_DROP_CHANCE[enemy_tier(enemy_id)]):
            return signature, 1, True
        if others:
            iid, lvl = rng.choice(others)
            return iid, lvl, False
        return None

    def gold_reward(self, kind):
        lo, hi = GOLD_REWARD.get(kind, GOLD_REWARD["fight"])
        g = self.rng.randint(lo, hi)
        if self.asc >= 9:
            g = int(g * 0.75)
        self.gold += g
        self.gold_earned += g
        return g

    def pick_enemy(self, kind):
        st = STAGES[self.stage]
        if kind == "boss":
            return self.boss_id()
        if kind == "elite":
            return self.rng.choice(st["elites"])
        self.ensure_stage(self.stage)
        if self.is_first_battle():                      # warm-up: one of the gentlest mobs
            from .data import FIRST_FIGHT_POOL
            return self.rng.choice(FIRST_FIGHT_POOL)
        return self.rng.choice(self.fight_pool[self.stage])

    def add_item(self, iid, level=1):
        """Put a new item in the stash (or bag). Returns False if nowhere fits."""
        inst = ItemInst(iid, level=level)
        self.acquired.setdefault(iid, self.stage)
        return self.stash.first_fit(inst) or self.bag.first_fit(inst)

    # ---------------- levelling (merge two identical items)
    @staticmethod
    def can_merge(a, b):
        return a is not b and a.id == b.id and a.level == b.level and a.level < max_level(a.data)

    def merge(self, keep, consume):
        """Level up `keep` by merging `consume` (identical item, same level) into it."""
        if not self.can_merge(keep, consume):
            return False
        for g in (self.bag, self.stash):
            g.remove(consume)
        keep.level += 1
        from .spirit import merge_into
        merge_into(keep, consume)               # infusions / awakenings carry over
        return True

    def auto_merge(self):
        """Merge every identical pair (used by bots and the 'merge all' button). Returns merges done."""
        merges = 0
        changed = True
        while changed:
            changed = False
            items = sorted(self.all_items(), key=lambda i: (i.id, i.level, i not in self.bag.items))
            for a in items:
                for b in items:
                    if self.can_merge(a, b):
                        self.merge(a, b)
                        merges += 1
                        changed = True
                        break
                if changed:
                    break
        return merges

    def upgrade_random(self, rng=None):
        """Level up a random upgradable item (blacksmith events). Returns the item or None."""
        rng = rng or self.rng
        cands = [i for i in self.bag.items if i.level < max_level(i.data)] or \
                [i for i in self.all_items() if i.level < max_level(i.data)]
        if not cands:
            return None
        it = rng.choice(cands)
        it.level += 1
        # a bigger level never changes the shape, so it still fits where it is
        return it

    def snapshot_build(self):
        """Serializable build - the future 'ghost' uploaded for async PvP."""
        return dict(char=self.char_id, max_hp=self.max_hp, stage=self.stage, seed=self.seed,
                    techniques=list(self.techniques), bag=self.bag.to_dict())

    # ---------------- shop prices, economy items, consumables
    def discount(self):
        return min(0.3, sum(i.data.get("discount", 0) for i in self.bag.items))

    def price(self, iid):
        p = ITEMS[iid]["price"] if iid in ITEMS else CONSUMABLES[iid]["price"]
        mult = (1.2 if self.asc >= 2 else 1.0) * (1 - self.discount())
        return max(1, int(round(p * mult)))

    @property
    def blood_moon_now(self):
        return self.stage >= BLOOD_MOON_STAGE or (self.asc >= 10 and self.stage >= 3)

    def legendary_choices(self, n=3):
        pool = [i["id"] for i in self.item_pool("legendary")]
        return self.rng.sample(pool, min(n, len(pool))) if pool else self.reward_choices("boss")

    def shop_consumables(self, n=2):
        return self.rng.sample(sorted(CONSUMABLES), n)

    def add_consumable(self, cid):
        if len(self.consumables) >= MAX_CONSUMABLES:
            return False
        self.consumables.append(cid)
        return True

    def after_battle(self, won, kind):
        """Called once after every battle: economy items pay out, consumables are used up.
        Returns a list of (ryō, reason) for what paid out."""
        paid = []
        if won:
            for inst in self.bag.items:
                d = inst.data
                if d.get("gold_per_win"):
                    paid.append((d["gold_per_win"], d["name"]))
                if d.get("interest"):
                    g = min(5, self.gold * d["interest"] // 100)
                    if g:
                        paid.append((g, d["name"]))
                if d.get("gold_per_boss") and kind == "boss":
                    paid.append((d["gold_per_boss"], d["name"]))
            for cid in self.consumables:
                if CONSUMABLES[cid].get("win_gold"):
                    paid.append((CONSUMABLES[cid]["win_gold"], CONSUMABLES[cid]["name"]))
        for g, _ in paid:
            self.gold += g
            self.gold_earned += g
        self.consumables = []
        return paid

    # ---------------- recipes
    def combine_recipes(self):
        """Fuse every pair of recipe ingredients that touch in the kit. Returns [(a, b, result)]."""
        from .data import RECIPES
        made = []
        changed = True
        while changed:
            changed = False
            for a in list(self.bag.items):
                for b in self.bag.neighbors(a):
                    res = RECIPES.get(frozenset((a.id, b.id)))
                    if not res or a.id == b.id:
                        continue
                    spots = [(a.x, a.y), (b.x, b.y)]
                    self.bag.remove(a)
                    self.bag.remove(b)
                    inst = ItemInst(res, level=min(a.level, b.level))
                    self.acquired.setdefault(res, self.stage)
                    if not any(self.bag.place(inst, x, y) for x, y in spots):
                        self.bag.first_fit(inst) or self.stash.first_fit(inst)
                    made.append((a.id, b.id, res))
                    changed = True
                    break
                if changed:
                    break
        return made

    def record_battle(self, items):
        """Add one battle's per-item stats (CItem.stats) to the run totals, and count the battle for every
        item in the kit (tsukumogami). Returns the items that just awakened."""
        from .spirit import record
        by_uid = {ci.uid: ci for ci in items if ci.uid is not None}
        awoke = [inst for inst in self.bag.items
                 if record(inst, by_uid[inst.uid].stats if inst.uid in by_uid else None)]
        self.stats["battles"] += 1
        for ci in items:
            d = ci.stats.get("dmg", 0)
            if d:
                self.stats["dmg"] += d
                iid = ci.st["id"]
                self.stats["items"][iid] = self.stats["items"].get(iid, 0) + d
        return awoke

    def best_item(self):
        items = self.stats.get("items") or {}
        return max(items.items(), key=lambda kv: kv[1]) if items else None
