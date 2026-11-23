"""Long-term progress on this device: first-time hints, achievements, lifetime stats, ascension unlocks.
Pure Python, kept with storage.py (browser localStorage on the website, so it survives updates)."""
import json
import time

from . import storage
from .data import MAX_ASCENSION, enemy_tier

KEY = "progress"
_data = None

ACHIEVEMENTS = [
    ("first_blood", "First Blood", "Win your first battle."),
    ("story_win", "Dawn Returns", "Defeat the stage-3 villain."),
    ("all_classes", "Five Paths", "Win a story run with every class."),
    ("minimalist", "Minimalist", "Win a story run with 6 or fewer items in your kit."),
    ("flawless_boss", "Untouchable", "Beat a boss without losing any HP."),
    ("rich", "Merchant Prince", "Hold 100 ryō at once."),
    ("master_smith", "Master Smith", "Finish a run with three level-3 items."),
    ("blood_moon", "Under the Blood Moon", "Reach endless stage 5."),
    ("endless7", "The Endless Night", "Reach endless stage 7."),
    ("enma", "Judge the Judge", "Defeat Enma, King of Yomi."),
    ("asc5", "Ascended", "Win on Ascension 5."),
    ("asc10", "Living Legend", "Win on Ascension 10."),
    ("arena_champ", "Arena Champion", "Win 10 Arena fights in one run."),
    ("arena_flawless", "Perfect Champion", "Become Arena champion without losing a heart."),
    ("slayer", "Demon Slayer", "Defeat 200 enemies in total."),
    ("omens", "Fate's Threads", "See a story thread through to its Omen."),
    ("tsukumogami", "A Hundred Years", "Awaken an item into a tsukumogami."),
    ("soul_forge", "Soul Smith", "Bind an item's spirit into another at a Kami Forge."),
]
ACH_BY_ID = {a[0]: a for a in ACHIEVEMENTS}


def data():
    global _data
    if _data is None:
        try:
            _data = json.loads(storage.read(KEY) or "{}")
        except (ValueError, TypeError):
            _data = {}
        _data.setdefault("hints", [])
        _data.setdefault("ach", {})
        _data.setdefault("kills", {})
        _data.setdefault("asc", {})            # class -> highest unlocked ascension level
        _data.setdefault("story_wins", {})     # class -> number of story wins
        _data.setdefault("deepest", 0)
        _data.setdefault("seen_items", [])
        _data.setdefault("seen_enemies", [])
    return _data


def save():
    storage.write(KEY, json.dumps(data(), separators=(",", ":")))


def reset_cache():
    global _data
    _data = None


# ---------------------------------------------------------------- hints
def hint_once(key):
    """True the first time a hint is asked for (and remembers it)."""
    from . import settings
    d = data()
    if not settings.get()["hints"] or key in d["hints"]:
        return False
    d["hints"].append(key)
    save()
    return True


# ---------------------------------------------------------------- achievements
def unlock(aid):
    """Unlock an achievement. Returns its (id, name, desc) the first time, else None."""
    d = data()
    if aid in d["ach"] or aid not in ACH_BY_ID:
        return None
    d["ach"][aid] = time.time()
    save()
    return ACH_BY_ID[aid]


def unlocked(aid):
    return aid in data()["ach"]


# ---------------------------------------------------------------- ascension
def asc_unlocked(cls):
    return int(data()["asc"].get(cls, 0))


# ---------------------------------------------------------------- hooks (return newly unlocked achievements)
def on_battle_won(run, enemy_id, kind, hp_before, hp_after):
    d = data()
    d["kills"][enemy_id] = d["kills"].get(enemy_id, 0) + 1
    new = [unlock("first_blood")]
    if kind == "boss" and hp_after >= hp_before:
        new.append(unlock("flawless_boss"))
    if enemy_id == "enma":
        new.append(unlock("enma"))
    if sum(d["kills"].values()) >= 200:
        new.append(unlock("slayer"))
    if run.gold >= 100:
        new.append(unlock("rich"))
    save()
    return [a for a in new if a]


def on_stage(run):
    new = []
    if run.stage >= 5:
        new.append(unlock("blood_moon"))
    if run.stage >= 7:
        new.append(unlock("endless7"))
    data()["deepest"] = max(data()["deepest"], run.stage)
    save()
    return [a for a in new if a]


def on_run_end(run, cleared):
    """cleared = beat the stage-3 villain (a story win, or an endless run that got past stage 3)."""
    d = data()
    new = []
    if any(run.flags.get(k + "_done") for k in ("tanuki", "ronin")):
        new.append(unlock("omens"))
    if sum(1 for i in run.all_items() if i.level >= 3) >= 3:
        new.append(unlock("master_smith"))
    if cleared:
        new.append(unlock("story_win"))
        d["story_wins"][run.char_id] = d["story_wins"].get(run.char_id, 0) + 1
        if len(run.bag.items) <= 6:
            new.append(unlock("minimalist"))
        if run.asc >= 5:
            new.append(unlock("asc5"))
        if run.asc >= 10:
            new.append(unlock("asc10"))
        from .data import CHARACTERS
        if all(d["story_wins"].get(c) for c in CHARACTERS):
            new.append(unlock("all_classes"))
        if run.asc >= asc_unlocked(run.char_id) and run.asc < MAX_ASCENSION:     # unlock the next level
            d["asc"][run.char_id] = run.asc + 1
            new.append(("asc_up", f"Ascension {run.asc + 1} unlocked",
                        f"{run.char_id}"))
    save()
    return [a for a in new if a]


def on_arena_end(run):
    a = run.arena
    new = []
    if a["wins"] >= 10:
        new.append(unlock("arena_champ"))
        if a["losses"] == 0:
            new.append(unlock("arena_flawless"))
    return [x for x in new if x]


# ---------------------------------------------------------------- stats screen
def lifetime_stats(history_runs, arena_runs):
    d = data()
    kills = d["kills"]
    total_kills = sum(kills.values())
    nemesis = {}
    items = {}
    for r in history_runs:
        if r.get("killed_by"):
            nemesis[r["killed_by"]] = nemesis.get(r["killed_by"], 0) + 1
        for it in r.get("kit", {}).get("items", []):
            items[it["id"]] = items.get(it["id"], 0) + 1
    return dict(
        runs=len(history_runs), wins=sum(1 for r in history_runs if r.get("won")),
        kills=total_kills, deepest=d["deepest"],
        most_killed=sorted(kills.items(), key=lambda kv: -kv[1])[:5],
        nemesis=sorted(nemesis.items(), key=lambda kv: -kv[1])[:3],
        favourite=sorted(items.items(), key=lambda kv: -kv[1])[:6],
        arena_runs=len(arena_runs), arena_best=max((r["wins"] for r in arena_runs), default=0),
        bosses=sum(v for k, v in kills.items() if enemy_tier(k) == "boss"),
    )


# ---------------------------------------------------------------- compendium (what you've discovered)
def discover_item(*iids):
    d = data()
    new = [i for i in dict.fromkeys(iids) if i and i not in d["seen_items"]]
    if new:
        d["seen_items"].extend(new)
        save()


def discover_enemy(eid):
    d = data()
    if eid and eid not in d["seen_enemies"]:
        d["seen_enemies"].append(eid)
        save()


def seen_item(iid):
    return iid in data()["seen_items"]


def seen_enemy(eid):
    return eid in data()["seen_enemies"]


def endless_unlocked():
    """Endless opens once you've beaten the story (all 3 stages) with any class."""
    return bool(data()["story_wins"]) or bool(data()["asc"])
