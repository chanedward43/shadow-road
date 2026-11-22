"""Arena: asynchronous "ghost" PvP, Backpack Battles style. Pure Python (no pygame).

A run is a series of rounds. Each round you get gold, shop and arrange your kit, then fight the
ghost of another player's kit *from the same round of the same game version*. 10 wins ends the
run; so does losing all 5 hearts. Your own kit is uploaded as a ghost every round, so other
players fight you later. Battles are deterministic, so each player's game simulates the fight
itself - no live connection is needed.

When no real ghost is available (offline, or nobody has played that round yet) an AI ghost is
built on the spot by the same shopping rules a player has.
"""
import random

from .data import ITEMS, RARITIES, TECHNIQUES, CHARACTERS
from .inventory import Grid, ItemInst
from .run import RunState
from .sim import pack
from .version import VERSION

MAX_WINS = 10
HEARTS = 5
TECH_ROUNDS = (3, 6, 9)          # pick a technique at the start of these rounds
HP_PER_ROUND = 6
FIRST_GOLD = 10


def stage_for(rnd):
    """Rounds 1-3 sell stage-1 items, 4-6 stage-2, 7+ stage-3 (rarer items appear later)."""
    return min(3, 1 + (rnd - 1) // 3)


def income(rnd):
    return FIRST_GOLD if rnd == 1 else 5 + rnd


def new_run(char_id, seed):
    run = RunState(char_id, seed)
    run.gold = 0
    run.arena = dict(round=0, wins=0, losses=0, base_hp=run.max_hp, history=[])
    return run


def tech_hp(run):
    return sum(TECHNIQUES[t].get("max_hp", 0) for t in run.techniques)


def start_round(run):
    a = run.arena
    a["round"] += 1
    run.stage = stage_for(a["round"])
    run.max_hp = a["base_hp"] + HP_PER_ROUND * (a["round"] - 1) + tech_hp(run)
    run.hp = run.max_hp
    run.gold += income(a["round"])
    run.rerolls = 0
    return a["round"]


def wants_technique(run):
    return run.arena["round"] in TECH_ROUNDS and bool(run.technique_choices())


def hearts(run):
    return HEARTS - run.arena["losses"]


def apply_result(run, won, opponent=None):
    """Record a fight. Returns 'champion', 'out' or 'next'."""
    a = run.arena
    if won:
        a["wins"] += 1
    else:
        a["losses"] += 1
    if isinstance(opponent, dict):          # a ghost record: keep who it was
        a["history"].append(dict(round=a["round"], won=bool(won), vs=opponent.get("name"),
                                 vs_cls=opponent.get("cls"), bot=bool(opponent.get("bot")),
                                 vs_record=f"{opponent.get('wins', 0)}-{opponent.get('losses', 0)}"))
    else:
        a["history"].append(dict(round=a["round"], won=bool(won), vs=opponent))
    if a["wins"] >= MAX_WINS:
        return "champion"
    if a["losses"] >= HEARTS:
        return "out"
    return "next"


def finished(run):
    return run.arena["wins"] >= MAX_WINS or run.arena["losses"] >= HEARTS


# ---------------------------------------------------------------- ghosts
def ghost_record(run, profile):
    """What gets uploaded: who you are, how you're doing, and your kit for this round."""
    a = run.arena
    return dict(player=profile["id"], name=profile["name"], cls=run.char_id, round=a["round"], wins=a["wins"],
                losses=a["losses"], version=VERSION,
                build=dict(max_hp=run.max_hp, techniques=list(run.techniques), bag=run.bag.to_dict()))


def valid_record(rec):
    try:
        b = rec["build"]
        return (rec["cls"] in CHARACTERS and isinstance(b["bag"]["items"], list)
                and 1 <= int(b["max_hp"]) <= 999 and len(b["bag"]["items"]) <= 40)
    except (KeyError, TypeError, ValueError):
        return False


def ghost_run(rec):
    """Rebuild a ghost's RunState so it fights exactly like a player's kit. Unknown items are skipped."""
    b = rec["build"]
    run = RunState(rec["cls"], seed=1)
    run.max_hp = run.hp = int(b["max_hp"])
    run.techniques = [t for t in b.get("techniques", []) if t in TECHNIQUES
                      and TECHNIQUES[t]["cls"] == rec["cls"]]
    run.stage = stage_for(int(rec.get("round", 1)))
    g = Grid(b["bag"]["w"], b["bag"]["h"])
    for it in b["bag"]["items"]:
        d = ITEMS.get(it.get("id"))
        if d is None or d.get("enemy"):
            continue
        inst = ItemInst(it["id"], rot=int(it.get("rot", 0)) % 4, level=max(1, min(3, int(it.get("level", 1)))))
        if g.can_place(inst, int(it["x"]), int(it["y"])):
            g.place(inst, int(it["x"]), int(it["y"]))
    run.bag = g
    run.stash = Grid(1, 1)
    return run


def _bot_score(run, iid, rng):
    d = ITEMS[iid]
    return RARITIES.index(d["rarity"]) * 10 + (6 if d["cls"] == run.char_id else 0) + d["price"] + rng.random() * 8


def bot_record(char_id, rnd, seed):
    """An AI ghost for round `rnd`: it shops every round the way a sensible player would."""
    rng = random.Random(f"bot:{char_id}:{rnd}:{seed}")
    run = new_run(char_id, rng.randrange(1 << 30))
    for _ in range(rnd):
        start_round(run)
        if wants_technique(run):
            run.learn(rng.choice(run.technique_choices()))
        for shop in range(2):                        # look at the shop, maybe reroll once
            offers = run.shop_offers()
            while True:
                afford = [o for o in offers if ITEMS[o]["price"] <= run.gold]
                if not afford:
                    break
                pick = max(afford, key=lambda o: _bot_score(run, o, rng))
                run.gold -= ITEMS[pick]["price"]
                run.add_item(pick)
                offers.remove(pick)
            if run.gold < 2:
                break
            run.gold -= 1 + run.rerolls // 2
            run.rerolls += 1
        pack(run)
    wins = rng.randint(max(0, rnd - 1 - (HEARTS - 1)), rnd - 1)
    names = {"samurai": "Wandering Rōnin", "ninja": "Shadow of the Mist", "kunoichi": "Veiled Kunoichi",
             "onmyoji": "Hermit Onmyōji", "sohei": "Mountain Sōhei"}
    rec = ghost_record(run, dict(id="bot", name=names.get(char_id, "Ghost")))
    rec.update(wins=wins, losses=rnd - 1 - wins, bot=True)
    return rec


def pick_opponent(records, my_id, rnd, rng):
    """A real ghost from the server if there is one (never yourself), else an AI ghost."""
    pool = [r for r in records or [] if r.get("player") != my_id and valid_record(r)
            and int(r.get("round", 0)) == rnd and r.get("version") == VERSION]
    if pool:
        return rng.choice(pool)
    return bot_record(rng.choice(list(CHARACTERS)), rnd, rng.randrange(1 << 30))


def score_record(run, profile):
    a = run.arena
    return dict(player=profile["id"], name=profile["name"], cls=run.char_id, wins=a["wins"],
                hearts=HEARTS - a["losses"], rounds=a["round"], version=VERSION)
