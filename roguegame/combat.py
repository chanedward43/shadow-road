"""Deterministic auto-battle simulation. Pure Python (no pygame).

Same seed + same builds = same fight. That makes it usable later on a server
for asynchronous PvP (fight another player's saved build "ghost").
"""
import copy
import random

from .data import (ITEMS, CHARACTERS, ENEMIES, TECHNIQUES, level_stats, enemy_fill, weapon_stamina_cost,
                   STAMINA_MAX, STAMINA_REGEN, BLOOD_MOON_STAGE)

BLOOD_MOON_CRIT = 0.10
BLOOD_MOON_SPEED = 0.9      # enemy items recharge 10% faster

TICK = 0.05
FATIGUE_START = 25.0   # after this many seconds both sides take growing damage
HARD_CAP = 90.0
CRIT_MULT = 2.0
BASE_CRIT = 0.05
MAX_EVADE = 0.6
STUN_IMMUNITY = 2.0    # after a stun ends, the target can't be stunned again for this long
CURSE_PER_STACK = 0.05 # each Curse stack: enemy deals 5% less damage
CURSE_CAP = 0.5
SUMMON_CAP = 5
KI_MAX = 12


def tech_mods(techniques):
    """Sum every numeric modifier from a list of technique ids."""
    out = {}
    for tid in techniques:
        for k, v in TECHNIQUES[tid].items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out[k] = out.get(k, 0) + v
    return out


# ---------------------------------------------------------------- build -> stats
def effective_stats(grid, cls, techniques=()):
    """Return {uid: stats dict} with adjacency auras, class and technique bonuses applied."""
    mods = tech_mods(techniques)
    stats = {}
    for inst in grid.items:
        st = copy.deepcopy(inst.data)
        st["speed"] = 1.0
        stats[inst.uid] = st
    for inst in grid.items:
        aura = inst.data.get("aura")
        if not aura:
            continue
        for nb in grid.neighbors(inst):
            st = stats[nb.uid]
            if not st.get("cd"):
                continue
            tags = aura.get("tags")
            if tags and not set(tags) & set(st["tags"]):
                continue
            if aura.get("dmg") and st.get("dmg"):
                st["dmg"] = (st["dmg"][0] + aura["dmg"], st["dmg"][1] + aura["dmg"])
            for k in ("block", "poison", "burn", "heal"):
                if aura.get(k) and st.get(k):
                    st[k] += aura[k]
            if aura.get("crit") and st.get("dmg"):
                st["crit"] = st.get("crit", 0) + aura["crit"]
            if aura.get("summon_dmg") and st.get("summon"):
                sm = st["summon"]
                sm["dmg"] = (sm["dmg"][0] + aura["summon_dmg"], sm["dmg"][1] + aura["summon_dmg"])
            if aura.get("ki") and st.get("ki"):
                st["ki"] += aura["ki"]
            if aura.get("stamina_cost") and weapon_stamina_cost(st):
                st["stamina_cost"] = max(0.2, round(weapon_stamina_cost(st) + aura["stamina_cost"], 2))
            if aura.get("speed"):
                st["speed"] += aura["speed"]
    for inst in grid.items:                    # who is next to whom (for adjacent_crit / alone_dmg)
        st = stats[inst.uid]
        nbrs = grid.neighbors(inst)
        st["adj"] = [n.uid for n in nbrs]
        if st.get("alone_dmg") and st.get("dmg") and not nbrs:
            st["dmg"] = (st["dmg"][0] + st["alone_dmg"], st["dmg"][1] + st["alone_dmg"])
    tag_count = {}
    for inst in grid.items:
        for t in set(inst.data["tags"]):
            tag_count[t] = tag_count.get(t, 0) + 1
    for st in stats.values():
        if not st.get("cd"):
            continue
        if st.get("per_tag") and st.get("dmg"):
            tag, per = st["per_tag"]
            n = tag_count.get(tag, 0) - (1 if tag in st["tags"] else 0)
            st["dmg"] = (st["dmg"][0] + per * n, st["dmg"][1] + per * n)
        if st.get("curse") and mods.get("item_curse"):
            st["curse"] += mods["item_curse"]
        if st.get("summon") and mods.get("summon_dmg"):
            sm = st["summon"]
            sm["dmg"] = (sm["dmg"][0] + mods["summon_dmg"], sm["dmg"][1] + mods["summon_dmg"])
        if st.get("summon") and mods.get("summon_curse"):
            st["summon"]["curse"] = st["summon"].get("curse", 0) + mods["summon_curse"]
        is_weapon = "weapon" in st["tags"] and st.get("dmg")
        if is_weapon:
            if mods.get("weapon_dmg"):
                st["dmg"] = (st["dmg"][0] + mods["weapon_dmg"], st["dmg"][1] + mods["weapon_dmg"])
            st["speed"] += mods.get("weapon_speed", 0)
            if cls == "ninja":
                st["speed"] += 0.15
            if mods.get("weapon_lifesteal"):
                st["lifesteal"] = st.get("lifesteal", 0) + mods["weapon_lifesteal"]
        if st.get("burn") and mods.get("item_burn"):
            st["burn"] += mods["item_burn"]
        if st.get("poison") and mods.get("item_poison"):
            st["poison"] += mods["item_poison"]
        if not st.get("trigger"):
            st["cd"] = round(st["cd"] / st["speed"], 2)
    return stats


class CItem:
    def __init__(self, st, uid=None):
        self.uid = uid
        self.name = st["name"]
        self.st = st
        self.cd = st["cd"]
        self.timer = 0.0
        self.flash = 0.0
        self.triggers = 0
        self.bonus = 0               # Grow: damage this item has gained during the battle
        self.cost = weapon_stamina_cost(st)   # Stamina per activation (weapons only)
        self.waiting = False         # charged, but waiting for Stamina
        self.stats = {}              # what this item did this battle: dmg, block, heal, poison, ...


class Fighter:
    def __init__(self, name, max_hp, hp, cls=None, color=(200, 200, 200), glyph="?", portrait="enemy"):
        self.name = name
        self.max_hp = max_hp
        self.hp = hp
        self.cls = cls
        self.color = color
        self.glyph = glyph
        self.portrait = portrait
        self.block = 0
        self.poison = 0
        self.burn = 0
        self.regen = 0
        self.thorns = 0
        self.crit = BASE_CRIT
        self.evade = 0.0
        self.dodge = 0
        self.stun_t = 0.0
        self.stun_immune = 0.0
        self.resolve = 0
        self.resolve_max = 0
        self.first_strike = 1.0
        self.poison_on_crit = 0
        self.armor_pierce = 0         # damage per hit that ignores Block
        self.poison_immune = False
        self.poison_interval = 1.0   # how fast poison THIS fighter inflicts ticks
        self.curse = 0               # stacks ON this fighter: it deals less damage
        self.start_curse = 0         # curse this fighter applies to the enemy at battle start
        self.summons = []            # shikigami fighting for this side
        self.summon_speed = 1.0
        self.ki = 0
        self.ki_max = 0
        self.counter = 0             # strike-back damage when an enemy attack lands
        self.ki_burst_bonus = 0
        self.crit_block = 0
        self.crit_poison = 0
        self.block_gains = 0         # for block_count triggers
        self.hits_taken = 0          # for hits_taken triggers
        self.heals = 0               # for heal_count triggers
        self.max_stamina = STAMINA_MAX
        self.stamina = STAMINA_MAX
        self.stamina_regen = STAMINA_REGEN
        self.ambush_on_evade = False # Ninja: evading primes an Ambush
        self.ambush = False          # next weapon hit deals double damage
        self.items = []
        self.activations = 0
        self.poison_t = 0.0
        self.status_t = 0.0
        self.phases = []
        self.phase_msg = ""
        self.carried = []            # enemies: real items carried (and droppable)

    def add_stats(self, st, uid=None):
        self.block += st.get("s_block", 0)
        self.max_hp += st.get("s_hp", 0)
        self.hp += st.get("s_hp", 0)
        self.regen += st.get("s_regen", 0)
        self.thorns += st.get("s_thorns", 0)
        self.crit += st.get("s_crit", 0)
        self.evade += st.get("s_evade", 0)
        self.counter += st.get("s_counter", 0)
        self.max_stamina += st.get("s_stamina", 0)
        self.stamina = self.max_stamina
        self.stamina_regen += st.get("s_stamina_regen", 0)
        self.start_curse += st.get("s_curse", 0)
        self.crit_block += st.get("s_crit_block", 0)
        self.crit_poison += st.get("s_crit_poison", 0)
        if st.get("cd"):
            self.items.append(CItem(st, uid))


def player_fighter(run):
    ch = CHARACTERS[run.char_id]
    f = Fighter(ch["name"], run.max_hp, run.hp, run.char_id, ch["color"], ch["glyph"], ch["portrait"])
    for uid, st in effective_stats(run.bag, run.char_id, run.techniques).items():
        f.add_stats(st, uid)
    mods = tech_mods(run.techniques)
    if run.char_id == "samurai":
        f.block += 6
        f.resolve_max = 5
    elif run.char_id == "ninja":
        f.evade += 0.20
        f.armor_pierce = 0
        f.ambush_on_evade = True
        f.max_stamina += 1
        f.stamina = f.max_stamina
        f.stamina_regen *= 1.25
    elif run.char_id == "kunoichi":
        f.crit += 0.05
        f.poison_on_crit = 2
        f.poison_interval = 0.8
    elif run.char_id == "onmyoji":
        f.summon_speed = 1.25
        f.start_curse += 1
        bonus = int(mods.get("summon_dmg", 0))
        for _ in range(1 + int(mods.get("extra_summon", 0))):
            f.summons.append(new_summon(dict(name="Paper Crane", dmg=(2 + bonus, 3 + bonus), cd=1.6,
                                             curse=mods.get("summon_curse", 0))))
    elif run.char_id == "sohei":
        f.ki_max = KI_MAX + int(mods.get("ki_max", 0))
        f.counter += 2 + int(mods.get("counter", 0))
        f.ki = 3 + int(mods.get("ki_start", 0))
        f.ki_burst_bonus = int(mods.get("ki_burst_bonus", 0))
    f.block += mods.get("s_block", 0)
    f.resolve_max += mods.get("resolve_max", 0)
    f.first_strike = mods.get("first_strike", 1.0)
    f.dodge += mods.get("dodge", 0)
    f.evade += mods.get("evade", 0)
    f.crit += mods.get("crit", 0)
    f.poison_on_crit += mods.get("poison_on_crit", 0)
    if run.stage >= 4:                        # endless class passives (ENDLESS_PASSIVES in data.py)
        depth = run.stage - 3
        if run.char_id == "samurai":          # Way of the Blade: weapons +2, then +1 more per endless stage
            for ci in f.items:
                if ci.st.get("dmg") and "weapon" in ci.st.get("tags", ()):
                    ci.st["dmg"] = (ci.st["dmg"][0] + depth + 2, ci.st["dmg"][1] + depth + 2)
        elif run.char_id == "sohei":          # Unshakable: counters +3 and +6 starting Block per endless stage
            f.counter += 3 * depth
            f.block += 6 * depth
    return f


def new_summon(sm):
    return dict(name=sm["name"], dmg=tuple(sm["dmg"]), cd=sm["cd"], burn=sm.get("burn", 0),
                curse=sm.get("curse", 0), timer=0.0, flash=0.0)


def _scale_stats(st, scale):
    st = copy.deepcopy(st)
    if st.get("dmg"):
        st["dmg"] = (max(1, round(st["dmg"][0] * scale)), max(1, round(st["dmg"][1] * scale)))
    for k in ("block", "heal", "poison", "burn"):
        if st.get(k):
            st[k] = max(1, round(st[k] * scale))
    return st


def enemy_fighter(enemy_id, scale=1.0, stage=1, rng=None):
    """Enemy = signature moves + fixed core items + (with an rng) a random fill of real items."""
    e = ENEMIES[enemy_id]
    hp = int(e["hp"] * scale)
    f = Fighter(e["name"], hp, hp, None, (170, 60, 60), e["name"][0], "enemy")
    f.regen = e.get("regen", 0)
    f.thorns = e.get("thorns", 0)
    f.evade = e.get("evade", 0)
    f.poison_immune = e.get("poison_immune", False)
    f.crit += e.get("crit", 0)
    for iid in e["items"]:                     # unique enemy-only moves
        f.add_stats(_scale_stats(ITEMS[iid], scale))
    gear = list(e.get("kit", [])) + (enemy_fill(enemy_id, stage, rng) if rng is not None else [])
    for iid, lvl in gear:                      # real items the player can also own
        f.add_stats(_scale_stats(level_stats(ITEMS[iid], lvl), scale))
    f.carried = gear                           # what it can drop when beaten
    f.phases = [dict(p, done=False, scale=scale) for p in e.get("phases", [])]
    return f


def make_battle(run, enemy_id, scale=1.0, seed=0):
    """Build both sides (incl. effects one side has on the other) and return a Battle."""
    p = player_fighter(run)
    e = enemy_fighter(enemy_id, scale, run.stage, random.Random(f"{seed}:{enemy_id}"))
    slow = tech_mods(run.techniques).get("enemy_slow", 0)
    if slow:
        for ci in e.items:
            ci.cd = round(ci.cd * (1 + slow), 2)
    from .data import CONSUMABLES, enemy_tier
    asc = getattr(run, "asc", 0)
    if asc >= 5 and enemy_tier(enemy_id) == "elite":
        e.regen += 2
    if asc >= 8 and enemy_tier(enemy_id) == "boss":
        e.phases.append(dict(at=0.25, msg=f"{e.name.split(',')[0]} makes a last stand!", speed=1.25, block=20,
                             done=False, scale=scale))
    for cid in getattr(run, "consumables", []):  # consumables bought for this battle
        c = CONSUMABLES[cid]
        p.block += c.get("block", 0)
        p.dodge += c.get("dodge", 0)
        p.regen += c.get("regen", 0)
        e.burn += c.get("enemy_burn", 0)
        if c.get("poison_immune"):
            p.poison_immune = True
        for ci in p.items:
            if c.get("speed") and not ci.st.get("trigger"):
                ci.cd = round(ci.cd / (1 + c["speed"]), 2)
            if c.get("weapon_dmg") and ci.st.get("dmg") and "weapon" in ci.st.get("tags", ()):
                ci.st["dmg"] = (ci.st["dmg"][0] + c["weapon_dmg"], ci.st["dmg"][1] + c["weapon_dmg"])
    if run.stage >= BLOOD_MOON_STAGE or (asc >= 10 and run.stage >= 3):   # Blood Moon: enemies enraged
        e.crit += BLOOD_MOON_CRIT
        for ci in e.items:
            ci.cd = round(ci.cd * BLOOD_MOON_SPEED, 2)
    e.curse += p.start_curse
    p.curse += e.start_curse
    return Battle(p, e, seed)


def make_pvp_battle(run, ghost, seed=0, name=None):
    """Arena: your kit against another player's ghost kit. Both sides are full player fighters."""
    run.hp = run.max_hp
    ghost.hp = ghost.max_hp
    p = player_fighter(run)
    g = player_fighter(ghost)
    if name:
        g.name = name
    for me, other, r in ((p, g, run), (g, p, ghost)):
        slow = tech_mods(r.techniques).get("enemy_slow", 0)
        if slow:
            for ci in other.items:
                ci.cd = round(ci.cd * (1 + slow), 2)
    g.curse += p.start_curse
    p.curse += g.start_curse
    return Battle(p, g, seed)


# ---------------------------------------------------------------- simulation
class Battle:
    def __init__(self, a, b, seed=0):
        self.f = [a, b]
        self.rng = random.Random(seed)
        self.t = 0.0
        self.acc = 0.0
        self.events = []      # consumed by the UI
        self.done = False
        self.winner = None    # 0 = player / a, 1 = b
        self.fatigue = 0
        self.fatigue_t = 0.0
        self.log = []                # one entry per item activation: dict(t, side, name, id, delta)
        self.totals = [{}, {}]       # damage each side dealt through statuses (poison, burn, thorns...)
        self._pending = []           # triggered items waiting to fire: (side, CItem)
        self._cur = None             # the item currently activating (credited with its effects)
        self._cur_side = None

    # ---- helpers
    def _credit(self, key, amount, item=None):
        it = item or self._cur
        if it is not None and amount:
            it.stats[key] = it.stats.get(key, 0) + amount

    def _emit(self, kind, side, amount=0, crit=False, text=""):
        self.events.append(dict(kind=kind, side=side, amount=amount, crit=crit, text=text, t=self.t))

    def _damage(self, side, amount, kind, crit=False, pierce=False, pierce_amt=0):
        tgt = self.f[side]
        if amount <= 0:
            return 0
        if self._cur is not None and side != self._cur_side and kind in ("hit", "hex", "kiburst"):
            self._credit("dmg", amount)
        elif kind in ("poison", "burn", "thorns", "counter", "fatigue"):
            t = self.totals[1 - side]                  # credited to the other side
            t[kind] = t.get(kind, 0) + amount
        if not pierce and tgt.block > 0:
            absorbed = min(tgt.block, amount - min(pierce_amt, amount))
            tgt.block -= absorbed
            amount -= absorbed
        tgt.hp -= amount
        self._emit(kind, side, amount, crit)
        return amount

    def _heal(self, side, amount):
        f = self.f[side]
        amount = min(amount, f.max_hp - f.hp)
        if amount > 0:
            if self._cur is not None and side == self._cur_side:
                self._credit("heal", amount)
            f.hp += amount
            self._emit("heal", side, amount)
            f.heals += 1
            self._count_trigger(side, "heal_count", f.heals)

    def _strike(self, side, ci):
        me, foe = self.f[side], self.f[1 - side]
        st = ci.st
        if foe.dodge > 0:
            foe.dodge -= 1
            self._evaded(1 - side)
            return False
        if self.rng.random() < min(MAX_EVADE, foe.evade):
            self._evaded(1 - side)
            return False
        dmg = self.rng.randint(*st["dmg"]) + me.resolve + ci.bonus
        if ci.triggers == 1 and me.first_strike > 1:
            dmg = int(dmg * me.first_strike)
        crit = self.rng.random() < me.crit + st.get("crit", 0)
        if crit:
            dmg = int(dmg * CRIT_MULT)
            self._credit("crits", 1)
            for other in me.items:
                if other.st.get("trigger") == "adjacent_crit" and ci.uid is not None \
                        and ci.uid in other.st.get("adj", ()) and other is not ci:
                    self._pending.append((side, other))
            if (me.poison_on_crit or me.crit_poison) and not foe.poison_immune:
                foe.poison += me.poison_on_crit + me.crit_poison
                self._credit("poison", me.poison_on_crit + me.crit_poison)
            if me.crit_block:
                me.block += me.crit_block
        if me.ambush:
            me.ambush = False
            dmg *= 2
            self._emit("ambush", 1 - side, dmg, text="AMBUSH!")
        dmg = self._cursed(me, dmg)
        dealt = self._damage(1 - side, dmg, "hit", crit, pierce_amt=me.armor_pierce)
        self._on_hit_taken(1 - side)
        foe.hits_taken += 1
        self._count_trigger(1 - side, "hits_taken", foe.hits_taken)
        if me.resolve_max and me.resolve < me.resolve_max:
            me.resolve += 1
        if st.get("lifesteal") and dealt:
            self._heal(side, max(1, int(dealt * st["lifesteal"])))
        return True

    @staticmethod
    def _cursed(attacker, dmg):
        if attacker.curse:
            dmg = int(round(dmg * (1 - min(CURSE_CAP, attacker.curse * CURSE_PER_STACK))))
        return max(0, dmg)

    def _evaded(self, side):
        """`side` just evaded an attack. A Ninja turns that into an Ambush (+2 Block)."""
        f = self.f[side]
        self._emit("evade", side)
        if f.ambush_on_evade:
            f.ambush = True
            f.block += 2

    def _on_hit_taken(self, side):
        """Sohei: every landed enemy hit builds Ki."""
        f = self.f[side]
        if f.ki_max and f.ki < f.ki_max:
            f.ki += 1

    def _summons_act(self, side, dt):
        me, foe = self.f[side], self.f[1 - side]
        for sm in me.summons:
            sm["flash"] = max(0.0, sm["flash"] - dt)
            sm["timer"] += dt * me.summon_speed
            if sm["timer"] < sm["cd"]:
                continue
            sm["timer"] -= sm["cd"]
            sm["flash"] = 0.25
            if foe.dodge > 0:
                foe.dodge -= 1
                self._evaded(1 - side)
                continue
            if self.rng.random() < min(MAX_EVADE, foe.evade):
                self._evaded(1 - side)
                continue
            dmg = self._cursed(me, self.rng.randint(*sm["dmg"]))
            self._damage(1 - side, dmg, "summon")
            self._credit("dmg", dmg, item=sm.get("src"))
            if sm["burn"]:
                foe.burn += sm["burn"]
            if sm["curse"]:
                foe.curse += sm["curse"]

    def _activate(self, side, ci):
        before = dict(ci.stats)
        self._cur, self._cur_side = ci, side
        try:
            self._activate_inner(side, ci)
        finally:
            self._cur = self._cur_side = None
        ci.stats["uses"] = ci.stats.get("uses", 0) + 1
        delta = {k: v - before.get(k, 0) for k, v in ci.stats.items() if v != before.get(k, 0) and k != "uses"}
        self.log.append(dict(t=round(self.t, 2), side=side, name=ci.name, id=ci.st["id"], delta=delta))

    def _activate_inner(self, side, ci):
        me, foe = self.f[side], self.f[1 - side]
        st = ci.st
        ci.flash = 0.25
        ci.triggers += 1
        if st.get("dmg"):
            landed = False
            for _ in range(st.get("hits", 1)):
                landed = self._strike(side, ci) or landed
            if landed and foe.thorns:   # thorns fire once per attacking item, not per strike
                self._damage(side, foe.thorns, "thorns")
            if landed and foe.counter:  # counter-attacks: once per attacking item, grows with Ki
                self._damage(side, foe.counter + foe.ki // 2, "counter")
            if landed and st.get("grow"):
                ci.bonus += st["grow"]
                self._emit("grow", side, ci.bonus, text=f"{ci.name} +{ci.bonus}")
        if st.get("sunder") and foe.block > 0:
            lost = int(foe.block * st["sunder"])
            foe.block -= lost
            self._emit("sunder", 1 - side, lost, text=f"ARMOR BROKEN -{lost}")
        if st.get("steal_block") and foe.block > 0:
            taken = min(foe.block, st["steal_block"])
            foe.block -= taken
            me.block += taken
            self._credit("steal", taken)
            self._emit("steal", side, taken, text=f"STOLE {taken} BLOCK")
        if st.get("stamina_gain"):
            gain = min(st["stamina_gain"], me.max_stamina - me.stamina)
            me.stamina += gain
            self._credit("stamina", round(gain, 1))
        if st.get("cleanse") and (me.poison or me.burn):
            me.poison = max(0, me.poison - st["cleanse"])
            me.burn = max(0, me.burn - st["cleanse"])
            self._emit("cleanse", side, st["cleanse"], text="CLEANSED")
        if st.get("block"):
            me.block += st["block"]
            self._credit("block", st["block"])
            self._emit("block", side, st["block"])
            me.block_gains += 1
            self._count_trigger(side, "block_count", me.block_gains)
        if st.get("summon"):
            self._credit("summons", 1)
            if len(me.summons) < SUMMON_CAP:
                sm = new_summon(st["summon"])
                sm["src"] = ci
                me.summons.append(sm)
                self._emit("summon", side, text="+ " + st["summon"]["name"])
            else:   # army is full: empower it instead
                for sm in me.summons:
                    sm["dmg"] = (sm["dmg"][0] + 1, sm["dmg"][1] + 1)
                self._emit("summon", side, text="Shikigami empowered")
        if st.get("curse"):
            foe.curse += st["curse"]
            self._credit("curse", st["curse"])
        if st.get("hex") and foe.curse:
            self._damage(1 - side, st["hex"] * foe.curse, "hex", pierce=True)
        if st.get("ki") and me.ki_max:
            self._credit("ki", min(st["ki"], me.ki_max - me.ki))
            me.ki = min(me.ki_max, me.ki + st["ki"])
        if st.get("ki_burst") and me.ki:
            k = me.ki
            me.ki = 0
            self._damage(1 - side, (st["ki_burst"] + me.ki_burst_bonus) * k, "kiburst", crit=k >= 6)
            if k >= 6 and foe.stun_t <= 0 and foe.stun_immune <= 0:
                foe.stun_t = 0.8
                foe.stun_immune = 0.8 + STUN_IMMUNITY
                self._emit("stun", 1 - side, text="STUNNED 0.8s")
        if st.get("heal"):
            self._heal(side, st["heal"])
        if st.get("regen"):
            me.regen += st["regen"]
            self._credit("regen", st["regen"])
        if st.get("dodge"):
            me.dodge += st["dodge"]
            self._credit("dodge", st["dodge"])
        if st.get("poison") and not foe.poison_immune:
            foe.poison += st["poison"]
            self._credit("poison", st["poison"])
        if st.get("burn"):
            foe.burn += st["burn"]
            self._credit("burn", st["burn"])
        if st.get("stun") and foe.stun_t <= 0 and foe.stun_immune <= 0:
            self._credit("stun", st["stun"])
            foe.stun_t = st["stun"]
            foe.stun_immune = st["stun"] + STUN_IMMUNITY
            self._emit("stun", 1 - side, text=f"STUNNED {st['stun']:.1f}s")

    def _count_trigger(self, side, kind, count):
        for ci in self.f[side].items:
            st = ci.st
            if st.get("trigger") == kind and st.get("n") and count % st["n"] == 0:
                self._pending.append((side, ci))

    def _flush_triggers(self):
        """Fire triggered items. A trigger can cause another (chains), but never more than 8 in a row."""
        n = 0
        while self._pending and n < 8:
            side, ci = self._pending.pop(0)
            n += 1
            if self.f[side].hp > 0 and self.f[side].stun_t <= 0:
                self._activate(side, ci)
        self._pending.clear()

    def _status(self, side, dt):
        me, foe = self.f[side], self.f[1 - side]
        me.poison_t += dt
        if me.poison_t >= foe.poison_interval:
            me.poison_t -= foe.poison_interval
            if me.poison > 0:
                self._damage(side, me.poison, "poison", pierce=True)
        me.status_t += dt
        if me.status_t >= 1.0:
            me.status_t -= 1.0
            if me.burn > 0:
                self._damage(side, me.burn, "burn")
                me.burn -= 1
            if me.regen > 0:
                self._heal(side, me.regen)

    def _check_phases(self, side):
        f = self.f[side]
        for ph in f.phases:
            if not ph["done"] and f.hp > 0 and f.hp <= f.max_hp * ph["at"]:
                ph["done"] = True
                sc = ph["scale"]
                for iid in ph.get("add", []):
                    f.items.append(CItem(_scale_stats(ITEMS[iid], sc)))
                    if not ITEMS[iid]["enemy"]:
                        f.carried.append((iid, 1))   # a drawn weapon can be dropped too
                if ph.get("speed"):
                    for ci in f.items:
                        ci.cd = round(ci.cd / ph["speed"], 2)
                f.block += int(ph.get("block", 0) * sc)
                f.thorns += ph.get("thorns", 0)
                if ph.get("cleanse"):
                    f.poison = 0
                    f.burn = 0
                if ph.get("heal"):
                    self._heal(side, int(ph["heal"] * sc))
                f.phase_msg = ph["msg"]
                self._emit("phase", side, text=ph["msg"])

    def _tick(self):
        dt = TICK
        self.t += dt
        for side in (0, 1):
            f = self.f[side]
            f.stun_immune = max(0.0, f.stun_immune - dt)
            if f.stun_t > 0:
                f.stun_t -= dt
                for ci in f.items:
                    ci.flash = max(0.0, ci.flash - dt)
                continue
            f.stamina = min(f.max_stamina, f.stamina + f.stamina_regen * dt)
            for ci in f.items:
                ci.flash = max(0.0, ci.flash - dt)
                ci.timer += dt
                if ci.timer >= ci.cd:
                    if ci.cost and f.stamina < ci.cost:
                        ci.timer = ci.cd          # charged: swings as soon as there is Stamina
                        ci.waiting = True
                        continue
                    ci.waiting = False
                    f.stamina -= ci.cost
                    ci.timer -= ci.cd
                    self._activate(side, ci)
                    self._flush_triggers()
            if f.summons:
                self._summons_act(side, dt)
        for side in (0, 1):
            self._status(side, dt)
        self._flush_triggers()                 # e.g. a Regen heal completing a heal_count
        if self.t >= FATIGUE_START:
            self.fatigue_t += dt
            if self.fatigue_t >= 1.0:
                self.fatigue_t -= 1.0
                self.fatigue += 1
                for side in (0, 1):
                    self._damage(side, self.fatigue, "fatigue", pierce=True)
        for side in (0, 1):
            self._check_phases(side)
        a, b = self.f
        if a.hp <= 0 or b.hp <= 0 or self.t >= HARD_CAP:
            self.done = True
            if b.hp <= 0 and a.hp > 0:
                self.winner = 0
            elif a.hp <= 0:
                self.winner = 1
            else:
                self.winner = 0 if a.hp / a.max_hp >= b.hp / b.max_hp else 1

    def advance(self, seconds):
        self.acc += seconds
        while self.acc >= TICK and not self.done:
            self.acc -= TICK
            self._tick()

    def run_to_end(self):
        while not self.done:
            self._tick()
