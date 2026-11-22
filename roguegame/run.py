"""State of a single-player run: hero, gold, kit, map. Pure Python (no pygame).

Every run has a seed. The seed decides the map layout, which regular enemies
appear in each stage, which villain rules each stage, and which ? events show up.
"""
import random

from .data import (ITEMS, CHARACTERS, STAGES, START_GOLD, BAG_SIZE, STASH_SIZE, GOLD_REWARD, RARITIES,
                   TECHNIQUES, ROW_SCALING, FIGHTS_PER_RUN, BALANCE, ENEMY_LOOT, MAX_LEVEL, REST_HEAL)
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


class RunState:
    def __init__(self, char_id, seed=None):
        self.seed = seed if seed is not None else random.randrange(1 << 30)
        self.rng = random.Random(self.seed)
        self.char_id = char_id
        ch = CHARACTERS[char_id]
        self.max_hp = int(round(ch["hp"] * BALANCE.get("class_hp", {}).get(char_id, 1.0)))
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

    # ---------------- techniques (permanent upgrades)
    def technique_choices(self, n=3):
        pool = [t for t, d in TECHNIQUES.items() if d["cls"] == self.char_id and t not in self.techniques]
        return self.rng.sample(pool, min(n, len(pool)))

    def learn(self, tid):
        self.techniques.append(tid)
        bonus = TECHNIQUES[tid].get("max_hp", 0)
        self.max_hp += bonus
        self.hp += bonus

    # ---------------- difficulty
    def enemy_scale(self, kind):
        """Stage multiplier x enemy-type multiplier x depth (+6% per map row for non-bosses)."""
        mult = BALANCE["stage_mult"].get(self.stage, 1.0)
        mult *= {"fight": BALANCE["fight_mult"], "elite": BALANCE["elite_mult"],
                 "boss": BALANCE["boss_mult"]}.get(kind, BALANCE["fight_mult"])
        if kind == "boss" or self.pos is None:
            return mult
        return mult * (1.0 + ROW_SCALING * self.pos[0])

    def boss_id(self, stage=None):
        return self.boss_of[stage or self.stage]

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
        return self.node(rc)

    def next_stage(self):
        self.stage += 1
        self.map = gen_map(self.rng, self.stage)
        self.pos = None
        self.hp = min(self.max_hp, self.hp + int(self.max_hp * 0.3))

    def rest(self):
        self.hp = min(self.max_hp, self.hp + int(self.max_hp * REST_HEAL))

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
                if not i["enemy"] and not i.get("loot") and i["rarity"] == rarity
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
        """The item this enemy drops (enemy-exclusive)."""
        return ENEMY_LOOT.get(enemy_id)

    def gold_reward(self, kind):
        lo, hi = GOLD_REWARD.get(kind, GOLD_REWARD["fight"])
        g = self.rng.randint(lo, hi)
        self.gold += g
        return g

    def pick_enemy(self, kind):
        st = STAGES[self.stage]
        if kind == "boss":
            return self.boss_id()
        if kind == "elite":
            return self.rng.choice(st["elites"])
        return self.rng.choice(self.fight_pool[self.stage])

    def add_item(self, iid, level=1):
        """Put a new item in the stash (or bag). Returns False if nowhere fits."""
        inst = ItemInst(iid, level=level)
        return self.stash.first_fit(inst) or self.bag.first_fit(inst)

    # ---------------- levelling (merge two identical items)
    @staticmethod
    def can_merge(a, b):
        return a is not b and a.id == b.id and a.level == b.level and a.level < MAX_LEVEL

    def merge(self, keep, consume):
        """Level up `keep` by merging `consume` (identical item, same level) into it."""
        if not self.can_merge(keep, consume):
            return False
        for g in (self.bag, self.stash):
            g.remove(consume)
        keep.level += 1
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
        cands = [i for i in self.bag.items if i.level < MAX_LEVEL] or \
                [i for i in self.all_items() if i.level < MAX_LEVEL]
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
