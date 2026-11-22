"""Save and continue a run. The game autosaves every time the map screen opens.

Saves go through storage.py: a JSON file in %APPDATA%/ShadowRoad on desktop, or the
browser's localStorage on the website (kept across new versions of the game).
"""
import json

from . import storage
from .inventory import Grid, ItemInst

SAVE_VERSION = 1


save_dir = storage.save_dir


def _grid_to(g):
    return g.to_dict()


def _grid_from(d):
    g = Grid(d["w"], d["h"])
    for it in d["items"]:
        inst = ItemInst(it["id"], rot=it["rot"], level=it.get("level", 1))
        g.place(inst, it["x"], it["y"])
    return g


def run_to_dict(run):
    state = run.rng.getstate()
    return dict(
        version=SAVE_VERSION, char_id=run.char_id, seed=run.seed,
        rng=[state[0], list(state[1]), state[2]],
        max_hp=run.max_hp, hp=run.hp, gold=run.gold, stage=run.stage,
        bag=_grid_to(run.bag), stash=_grid_to(run.stash),
        fight_pool={str(k): v for k, v in run.fight_pool.items()},
        boss_of={str(k): v for k, v in run.boss_of.items()},
        seen_events=run.seen_events, map=run.map, pos=list(run.pos) if run.pos else None,
        battles_won=run.battles_won, rerolls=run.rerolls, techniques=run.techniques, kills=run.kills,
        started=run.started, path=run.path, gold_earned=run.gold_earned, mode=run.mode,
        asc=run.asc, consumables=run.consumables, flags=run.flags,
    )


def run_from_dict(d):
    from .run import RunState
    run = RunState(d["char_id"], d["seed"], mode=d.get("mode", "story"), asc=d.get("asc", 0))
    run.consumables = d.get("consumables", [])
    run.flags = d.get("flags", {})
    st = d["rng"]
    run.rng.setstate((st[0], tuple(st[1]), st[2]))
    for k in ("max_hp", "hp", "gold", "stage", "seen_events", "map", "battles_won", "rerolls", "techniques",
              "kills"):
        setattr(run, k, d[k])
    run.pos = tuple(d["pos"]) if d["pos"] else None
    run.started = d.get("started", run.started)
    run.path = d.get("path", [])
    run.gold_earned = d.get("gold_earned", 0)
    run.bag = _grid_from(d["bag"])
    run.stash = _grid_from(d["stash"])
    run.fight_pool = {int(k): v for k, v in d["fight_pool"].items()}
    run.boss_of = {int(k): v for k, v in d["boss_of"].items()}
    return run


def save_run(run):
    """Autosave. Never lets a save problem (disk, browser storage) crash the game."""
    try:
        return storage.write("run", json.dumps(run_to_dict(run)))
    except Exception as e:   # noqa: BLE001
        print("autosave skipped:", repr(e))
        return False


def load_run():
    """Return the saved RunState, or None if there is no (valid) save."""
    try:
        text = storage.read("run")
        if not text:
            return None
        d = json.loads(text)
        if d.get("version") != SAVE_VERSION:
            return None
        return run_from_dict(d)
    except (OSError, ValueError, KeyError, TypeError):
        return None


def clear_run():
    storage.delete("run")
