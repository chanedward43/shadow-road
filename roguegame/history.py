"""Match history: one small record per finished run, kept with storage.py.

On the website this lives in the browser's localStorage, which belongs to the site
address - so pushing a new version of the game never wipes it. Pure Python (no pygame).
"""
import json
import time

from . import storage
from .data import enemy_tier, CHARACTERS

KEY = "history"
MAX_RUNS = 100           # oldest runs drop off after this
HISTORY_VERSION = 1


def record_from_run(run, won):
    tiers = [enemy_tier(e) for e in run.kills]
    last = run.path[-1] if run.path else None
    from .version import label
    return dict(
        v=HISTORY_VERSION,
        game=label(),
        mode=getattr(run, "mode", "story"),
        date=time.time(),
        char=run.char_id,
        won=bool(won),
        stage=run.stage,
        row=last["row"] + 1 if last else 0,
        floors=len(run.path),
        killed_by=None if won else getattr(run, "killed_by", None),
        battles=run.battles_won,
        elites=tiers.count("elite"),
        bosses=tiers.count("boss"),
        duration=max(0, int(time.time() - run.started)),
        seed=run.seed,
        max_hp=run.max_hp,
        gold=run.gold_earned,
        techniques=list(run.techniques),
        kit=run.bag.to_dict(),
        path=[dict(stage=p["stage"], row=p["row"], kind=p["kind"], hp=p["hp"], max_hp=p["max_hp"])
              for p in run.path],
    )


def load_history():
    """All recorded runs, newest first. Never raises."""
    try:
        runs = json.loads(storage.read(KEY) or "[]")
        return [r for r in runs if isinstance(r, dict) and r.get("char") in CHARACTERS]
    except (ValueError, TypeError):
        return []


def record_run(run, won):
    """Add a finished run to the history. Returns the record (or None if it couldn't be saved)."""
    try:
        rec = record_from_run(run, won)
    except Exception as e:          # noqa: BLE001 - never let history break the end of a run
        print("history skipped:", repr(e))
        return None
    runs = [rec] + load_history()
    storage.write(KEY, json.dumps(runs[:MAX_RUNS], separators=(",", ":")))
    return rec


def summary(runs):
    """Totals for the header: overall and per class."""
    out = dict(runs=len(runs), wins=sum(r["won"] for r in runs), per_class={}, best_stage=0, streak=0)
    for r in runs:
        pc = out["per_class"].setdefault(r["char"], dict(runs=0, wins=0, best=(0, 0)))
        pc["runs"] += 1
        pc["wins"] += r["won"]
        reach = (4, 0) if r["won"] else (r["stage"], r["row"])
        pc["best"] = max(pc["best"], reach)
    for r in runs:                   # current win streak (newest first)
        if not r["won"]:
            break
        out["streak"] += 1
    return out


# ---------------------------------------------------------------- Arena runs (their own list)
ARENA_KEY = "arena_history"


def arena_record(run):
    from .version import label
    a = run.arena
    return dict(v=HISTORY_VERSION, game=label(), date=time.time(), char=run.char_id, wins=a["wins"],
                losses=a["losses"], rounds=a["round"], champion=a["wins"] >= 10,
                duration=max(0, int(time.time() - run.started)), max_hp=run.max_hp,
                techniques=list(run.techniques), kit=run.bag.to_dict(),
                fights=[dict(f) for f in a["history"]])


def load_arena():
    try:
        runs = json.loads(storage.read(ARENA_KEY) or "[]")
        return [r for r in runs if isinstance(r, dict) and r.get("char") in CHARACTERS]
    except (ValueError, TypeError):
        return []


def record_arena(run):
    try:
        rec = arena_record(run)
    except Exception as e:          # noqa: BLE001
        print("arena history skipped:", repr(e))
        return None
    runs = [rec] + load_arena()
    storage.write(ARENA_KEY, json.dumps(runs[:MAX_RUNS], separators=(",", ":")))
    return rec


def arena_summary(runs):
    out = dict(runs=len(runs), champions=sum(r["champion"] for r in runs), per_class={},
               avg_wins=(sum(r["wins"] for r in runs) / len(runs)) if runs else 0.0)
    for r in runs:
        pc = out["per_class"].setdefault(r["char"], dict(runs=0, best=0, champions=0))
        pc["runs"] += 1
        pc["best"] = max(pc["best"], r["wins"])
        pc["champions"] += r["champion"]
    return out


def fmt_duration(sec):
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    return f"{h}h {m:02d}m" if h else f"{m}m {s:02d}s"


def fmt_date(ts):
    try:
        return time.strftime("%d %b %Y  %H:%M", time.localtime(ts))
    except (OverflowError, OSError, ValueError):
        return "?"
