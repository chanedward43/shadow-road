"""Headless game driver: plays a full run with a pluggable decision policy. No pygame.

Used by the reinforcement-learning agent and the Balance Director (tools/balance.py).
It follows exactly the same rules as the real game screens.
"""
from .combat import make_battle, effective_stats
from .data import ITEMS, RARITIES
from .events import pick_event, options_for, resolve, omen_event
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


def pack(run, merge=True):
    """Merge duplicates, then fill the kit with the most valuable items; aura items go where they buff most."""
    if merge:
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
def play(char_id, seed, policy, log=None, endless=False, max_stage=30):
    """Play a full run. Returns a summary dict. `log` (list) receives (kind, options, choice) tuples.
    endless=True keeps going after stage 3 (until death or max_stage)."""
    run = RunState(char_id, seed, mode="endless" if endless else "story")
    out = dict(char=char_id, seed=seed, win=False, stage=1, died_to=None, battles=0,
               encounters=[], picks=[], offered=[], fights=[], events=[], recipes=[], techs_offered=[])

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
        hp_before = run.hp
        b = make_battle(run, eid, run.enemy_scale(kind), seed=run.rng.randrange(1 << 30))
        b.run_to_end()
        run.hp = max(0, min(run.max_hp, b.f[0].hp))
        out["fights"].append(dict(enemy=eid, kind=kind, stage=run.stage, floor=(run.pos[0] + 1) if run.pos else 0,
                                  won=b.winner == 0, hp_before=hp_before, hp_after=run.hp, max_hp=run.max_hp,
                                  time=round(b.t, 1),
                                  dealt=sum(ci.stats.get("dmg", 0) for ci in b.f[0].items),
                                  enemy_hp=b.f[1].max_hp))
        run.after_battle(b.winner == 0, kind)
        run.record_battle(b.f[0].items)          # tsukumogami awaken in simulations too
        out["encounters"].append((eid, kind, b.winner == 0))
        if b.winner != 0:
            out["died_to"] = eid
            return False
        run.battles_won += 1
        run.kills.append(eid)
        run.gold_reward(kind)
        rolled = run.roll_drop(eid, b.f[1].carried)
        drop = rolled[0] if rolled else None
        if kind in ("elite", "boss"):
            if rolled:
                run.add_item(rolled[0], level=rolled[1])
            techs = run.technique_choices()
            if techs:
                out["techs_offered"].extend(techs)
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
                if (run.stage >= 3 and not endless) or run.stage >= max_stage:
                    break
                run.next_stage()
        elif kind == "shop":
            offers = run.shop_offers()
            for _ in range(5):
                afford = [o for o in offers if run.price(o) <= run.gold]
                if not afford:
                    break
                opts = afford + [STOP]
                i = decide("item", opts)
                out["offered"].extend(afford)
                if opts[i] == STOP:
                    break
                run.gold -= run.price(opts[i])
                run.add_item(opts[i])
                out["picks"].append(opts[i])
                offers.remove(opts[i])
        elif kind == "treasure":
            run.gold_reward("fight")
            pick_item(run.reward_choices("treasure"), "reward")
        elif kind == "rest":
            from .data import max_level
            opts = ["heal", "train"] + (["upgrade"] if any(i.level < max_level(i.data) for i in run.all_items())
                                        else [])
            choice = opts[decide("rest", opts)]
            if choice == "heal":
                run.rest()
            elif choice == "train":
                run.train()
            else:
                run.upgrade_random(run.rng)
        elif kind in ("event", "omen"):
            ev = omen_event(run, node["omen"]) if kind == "omen" else pick_event(run)
            valid = [(i, o) for i, o, ok in options_for(run, ev) if ok]
            labels = [f"{ev['id']}:{i}" for i, _ in valid]
            choice = valid[decide("event", labels)][0]
            out["events"].append(f"{ev['id']}:{choice}")
            res = resolve(run, ev, choice)
            if res.get("battle"):
                if not battle(*res["battle"]):
                    break
            elif res.get("choose"):
                pick_item(res["choose"], "reward")
            elif res.get("upgrade"):
                run.upgrade_random(run.rng)
            elif res.get("forge"):
                from .events import auto_infuse, pay_forge
                if auto_infuse(run, run.rng):
                    pay_forge(run, res["forge"])
        pack(run)
        made = run.combine_recipes()
        if made:
            out["recipes"].extend(res for _, _, res in made)
            pack(run)
    out["stage"] = run.stage
    out["floor"] = (run.pos[0] + 1) if run.pos else 0
    out["death_kind"] = out["fights"][-1]["kind"] if out["fights"] and not out["win"] else None
    out["gold_earned"] = run.gold_earned
    out["max_hp"] = run.max_hp
    out["kit"] = run.bag.to_dict()
    out["item_dmg"] = dict(run.stats.get("items", {}))
    out["awakened"] = [(i.id, i.awakened) for i in run.all_items() if i.awakened]
    out["infused"] = [(i.id, i.infusion["src"]) for i in run.all_items() if i.infusion]
    out["path"] = [p["kind"] for p in run.path]
    out["acquired"] = dict(run.acquired)
    out["battles"] = run.battles_won
    out["final_kit"] = [(i.id, i.level) for i in run.bag.items]
    out["techniques"] = list(run.techniques)
    return out
