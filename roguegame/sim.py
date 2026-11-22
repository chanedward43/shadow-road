"""Headless game driver: plays a full run with a pluggable decision policy. No pygame.

Used by the reinforcement-learning agent and the Balance Director (tools/balance.py).
It follows exactly the same rules as the real game screens.
"""
from .combat import make_battle, effective_stats
from .data import ITEMS, RARITIES
from .events import pick_event, options_for, resolve
from .run import RunState

STOP = "__stop__"


class RandomPolicy:
    def __init__(self, rng):
        self.rng = rng

    def choose(self, kind, options, run):
        return self.rng.randrange(len(options))


# ---------------------------------------------------------------- packing (placement heuristic)
def item_value(inst):
    d = inst.data
    v = RARITIES.index(d["rarity"]) * 10 + inst.level * 8 + d["price"]
    if d.get("cd"):
        v += 5
    return v


def _aura_score(run, inst):
    aura = inst.data.get("aura")
    if not aura:
        return 0
    score = 0
    for nb in run.bag.neighbors(inst):
        st = nb.data
        if st.get("cd") and (not aura.get("tags") or set(aura["tags"]) & set(st["tags"])):
            score += 1
    return score


def pack(run):
    """Merge duplicates, then fill the kit with the most valuable items; aura items go where they buff most."""
    run.auto_merge()
    items = run.all_items()
    run.bag.items, run.stash.items = [], []
    actives = sorted([i for i in items if not i.data.get("aura")], key=item_value, reverse=True)
    auras = sorted([i for i in items if i.data.get("aura")], key=item_value, reverse=True)
    for inst in actives:
        if not run.bag.first_fit(inst):
            run.stash.first_fit(inst)
    for inst in auras:
        best = None
        for rot in range(4):
            inst.rot = rot
            for y in range(run.bag.h):
                for x in range(run.bag.w):
                    if run.bag.can_place(inst, x, y):
                        run.bag.place(inst, x, y)
                        sc = _aura_score(run, inst)
                        run.bag.remove(inst)
                        if best is None or sc > best[0]:
                            best = (sc, rot, x, y)
        if best:
            inst.rot = best[1]
            run.bag.place(inst, best[2], best[3])
        elif not run.stash.first_fit(inst):
            pass   # no room anywhere: the item is dropped


# ---------------------------------------------------------------- one run
def play(char_id, seed, policy, log=None):
    """Play a full run. Returns a summary dict. `log` (list) receives (kind, options, choice) tuples."""
    run = RunState(char_id, seed)
    out = dict(char=char_id, seed=seed, win=False, stage=1, died_to=None, battles=0,
               encounters=[], picks=[], offered=[])

    def decide(kind, options):
        i = policy.choose(kind, options, run)
        if log is not None:
            log.append((kind, options, i))
        return i

    def pick_item(offers, kind):
        opts = list(offers) + [STOP]
        i = decide("item", opts)
        out["offered"].extend(offers)
        if opts[i] != STOP:
            out["picks"].append(opts[i])
            run.add_item(opts[i])
        return opts[i]

    def battle(eid, kind):
        b = make_battle(run, eid, run.enemy_scale(kind), seed=run.rng.randrange(1 << 30))
        b.run_to_end()
        run.hp = max(0, min(run.max_hp, b.f[0].hp))
        out["encounters"].append((eid, kind, b.winner == 0))
        if b.winner != 0:
            out["died_to"] = eid
            return False
        run.battles_won += 1
        run.kills.append(eid)
        run.gold_reward(kind)
        drop = run.loot_of(eid)
        if kind in ("elite", "boss"):
            if drop:
                run.add_item(drop)
            techs = run.technique_choices()
            if techs:
                run.learn(techs[decide("tech", techs)])
            pick_item(run.reward_choices(kind), "reward")
        else:
            offers = run.reward_choices(kind)
            if drop:
                offers = [drop] + offers[:2]
            pick_item(offers, "reward")
        return True

    while True:
        avail = run.available_nodes()
        kinds = [run.node(rc)["kind"] for rc in avail]
        node = run.visit(avail[decide("path", kinds)])
        kind = node["kind"]
        if kind in ("fight", "elite", "boss"):
            if not battle(run.pick_enemy(kind), kind):
                break
            if kind == "boss":
                if run.stage >= 3:
                    out["win"] = True
                    break
                run.next_stage()
        elif kind == "shop":
            offers = run.shop_offers()
            for _ in range(5):
                afford = [o for o in offers if ITEMS[o]["price"] <= run.gold]
                if not afford:
                    break
                opts = afford + [STOP]
                i = decide("item", opts)
                out["offered"].extend(afford)
                if opts[i] == STOP:
                    break
                run.gold -= ITEMS[opts[i]]["price"]
                run.add_item(opts[i])
                out["picks"].append(opts[i])
                offers.remove(opts[i])
        elif kind == "treasure":
            run.gold_reward("fight")
            pick_item(run.reward_choices("treasure"), "reward")
        elif kind == "rest":
            if decide("rest", ["heal", "train"]) == 0:
                run.rest()
            else:
                run.train()
        elif kind == "event":
            ev = pick_event(run)
            valid = [(i, o) for i, o, ok in options_for(run, ev) if ok]
            labels = [f"{ev['id']}:{i}" for i, _ in valid]
            choice = valid[decide("event", labels)][0]
            res = resolve(run, ev, choice)
            if res.get("battle"):
                if not battle(*res["battle"]):
                    break
            elif res.get("choose"):
                pick_item(res["choose"], "reward")
        pack(run)
    out["stage"] = run.stage
    out["battles"] = run.battles_won
    out["final_kit"] = [(i.id, i.level) for i in run.bag.items]
    out["techniques"] = list(run.techniques)
    return out
