"""Save and continue a run. The game autosaves every time the map screen opens.

Saves live in %APPDATA%/ShadowRoad on Windows (or ~/.shadowroad elsewhere), so they
also work from the packaged .exe. A save is plain JSON: easy to inspect or delete.
"""
import json
import os

from .inventory import Grid, ItemInst

SAVE_VERSION = 1


def save_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "ShadowRoad" if os.environ.get("APPDATA") else ".shadowroad")
    os.makedirs(d, exist_ok=True)
    return d


def save_path():
    return os.path.join(save_dir(), "run.json")


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
    )


def run_from_dict(d):
    from .run import RunState
    run = RunState(d["char_id"], d["seed"])
    st = d["rng"]
    run.rng.setstate((st[0], tuple(st[1]), st[2]))
    for k in ("max_hp", "hp", "gold", "stage", "seen_events", "map", "battles_won", "rerolls", "techniques",
              "kills"):
        setattr(run, k, d[k])
    run.pos = tuple(d["pos"]) if d["pos"] else None
    run.bag = _grid_from(d["bag"])
    run.stash = _grid_from(d["stash"])
    run.fight_pool = {int(k): v for k, v in d["fight_pool"].items()}
    run.boss_of = {int(k): v for k, v in d["boss_of"].items()}
    return run


def save_run(run):
    """Autosave. Never lets a save problem (disk, browser storage) crash the game."""
    try:
        tmp = save_path() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(run_to_dict(run), f)
        os.replace(tmp, save_path())   # atomic: a crash mid-write never corrupts the save
        return True
    except Exception as e:   # noqa: BLE001
        print("autosave skipped:", repr(e))
        return False


def load_run():
    """Return the saved RunState, or None if there is no (valid) save."""
    try:
        with open(save_path(), encoding="utf-8") as f:
            d = json.load(f)
        if d.get("version") != SAVE_VERSION:
            return None
        return run_from_dict(d)
    except (OSError, ValueError, KeyError, TypeError):
        return None


def clear_run():
    try:
        os.remove(save_path())
    except OSError:
        pass
