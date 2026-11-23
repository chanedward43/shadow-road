"""The Balance Director: learns the game with reinforcement learning, then tunes difficulty.

    python tools/balance.py                    # train agents + write a balance report
    python tools/balance.py --autotune         # ...and adjust difficulty until it hits the target
    python tools/balance.py --episodes 3000 --eval 300 --target 0.20

Steps
 1. TRAIN   - one LearningAgent per class plays thousands of seeded runs and learns
              which paths, items, events and techniques lead to deeper runs (REINFORCE).
 2. MEASURE - the trained agents play fresh seeds they never saw. We record win rate,
              how far they got, what killed them, which items they took and how items
              correlate with winning (like Slay the Spire's pick-rate / win-rate data).
 3. TUNE    - (with --autotune) nudge the balance knobs and re-measure until:
                * skilled-agent win rate is near --target (default 20%: a hard game),
                * regular mobs + elites cause at least 30% of deaths (mobs must matter),
                * every class is within 3 points of the class average (so each class is ~20%).
              Then retrain the agents on the new difficulty and measure again.
 4. WRITE   - assets/balance.json (knobs the game loads at start), assets/ai/<class>.npz
              (trained agents), assets/balance_report.md and .json.
"""
import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from roguegame import data  # noqa: E402
from roguegame.ai import LearningAgent, describe_policy  # noqa: E402
from roguegame.sim import play  # noqa: E402

CLASSES = list(data.CHARACTERS)
ASSETS = os.path.join(ROOT, "assets")
TRAIN_SEED0, EVAL_SEED0 = 1_000_000, 9_000_000   # train and test on different seeds


def _set_balance(bal):
    data.BALANCE.clear()
    data.BALANCE.update(json.loads(json.dumps(bal)))
    data.BALANCE["stage_mult"] = {int(k): v for k, v in data.BALANCE["stage_mult"].items()}


def _train(args):
    cls, episodes, bal, warm = args
    _set_balance(bal)
    agent = LearningAgent(cls, seed=hash(cls) % 1000)
    path = os.path.join(ASSETS, "ai", f"{cls}.npz")
    if warm and os.path.exists(path):
        agent.load(path)
    agent.train(episodes, TRAIN_SEED0 + (episodes if warm else 0))
    agent.save(path)
    return cls


def _evaluate(args):
    cls, n, bal = args
    _set_balance(bal)
    agent = LearningAgent(cls).load(os.path.join(ASSETS, "ai", f"{cls}.npz"))
    agent.greedy = True
    return cls, [play(cls, EVAL_SEED0 + i, agent) for i in range(n)], describe_policy(agent)


def measure(n, bal, pool):
    results = pool.map(_evaluate, [(c, n, bal) for c in CLASSES])
    return {cls: (runs, pol) for cls, runs, pol in results}


def stats(runs):
    n = len(runs)
    wins = sum(r["win"] for r in runs)
    deaths = Counter(r["died_to"] for r in runs if r["died_to"])
    kind_of = {}
    enc, lost = Counter(), Counter()
    for r in runs:
        for eid, kind, won in r["encounters"]:
            kind_of[eid] = kind
            enc[eid] += 1
            lost[eid] += not won
    by_kind = Counter()
    for eid, c in deaths.items():
        by_kind["boss" if kind_of.get(eid) == "boss" else "mob"] += c
    stage = Counter(r["stage"] for r in runs if not r["win"])
    picks = Counter(p for r in runs for p in r["picks"])
    offered = Counter(o for r in runs for o in r["offered"])
    in_kit = defaultdict(lambda: [0, 0])
    for r in runs:
        for iid in {i for i, _ in r["final_kit"]}:
            in_kit[iid][0] += 1
            in_kit[iid][1] += r["win"]
    return dict(n=n, win_rate=wins / n, avg_battles=sum(r["battles"] for r in runs) / n,
                died_stage={s: stage.get(s, 0) / n for s in (1, 2, 3)},
                death_share_boss=by_kind["boss"] / max(1, n - wins),
                death_share_mobs=by_kind["mob"] / max(1, n - wins),
                top_killers=deaths.most_common(6),
                lethality={e: round(lost[e] / enc[e], 3) for e in enc if enc[e] >= 10},
                pick_rate={i: round(picks[i] / offered[i], 3) for i in offered if offered[i] >= 15},
                kit_win_rate={i: round(w / c, 3) for i, (c, w) in in_kit.items() if c >= 10})


def summary_line(res):
    parts = []
    for cls, (runs, _) in res.items():
        s = stats(runs)
        parts.append(f"{cls} {s['win_rate']*100:4.1f}%")
    return " | ".join(parts)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def save_balance(bal):
    with open(os.path.join(ASSETS, "balance.json"), "w", encoding="utf-8") as f:
        json.dump(bal, f, indent=2)


def autotune(bal, args, pool, log):
    """Measure -> adjust, up to args.rounds times. Saves balance.json after every round (a checkpoint you
    can stop at). Returns (bal, last_results, balanced) - last_results match bal when balanced is True."""
    res = None
    gain, last_sign = 1.0, 0       # damping: each time we overshoot the target, take smaller steps
    for rnd in range(args.rounds):
        res = measure(args.eval, bal, pool)
        st = {c: stats(r) for c, (r, _) in res.items()}
        w = sum(s["win_rate"] for s in st.values()) / len(st)
        mob_share = sum(s["death_share_mobs"] for s in st.values()) / len(st)
        log(f"  round {rnd + 1}: avg win {w*100:.1f}% (target {args.target*100:.0f}%), "
            f"mobs cause {mob_share*100:.0f}% of deaths  [{summary_line(res)}]")
        changed = False
        # Proportional steps: a big miss gets a big correction, a small miss a small one.
        if abs(w - args.target) > 0.03:
            sign = 1 if w > args.target else -1
            if last_sign and sign != last_sign:
                gain *= 0.5
            last_sign = sign
            f = clamp(((w + 0.02) / (args.target + 0.02)) ** (0.5 * gain), 0.75, 1.2)
            for k in bal["stage_mult"]:
                bal["stage_mult"][k] = round(bal["stage_mult"][k] * f, 3)
            log(f"    stages x{f:.2f}")
            changed = True
        if mob_share < 0.30:
            bal["fight_mult"] = round(bal["fight_mult"] * 1.08, 3)
            bal["elite_mult"] = round(bal["elite_mult"] * 1.04, 3)
            bal["boss_mult"] = round(bal["boss_mult"] * 0.97, 3)
            changed = True
        elif mob_share > 0.55:
            bal["fight_mult"] = round(bal["fight_mult"] * 0.95, 3)
            changed = True
        for c, s in st.items():
            if abs(s["win_rate"] - w) > 0.03:      # weaker class: more HP, stronger class: less
                f = clamp(((w + 0.03) / (s["win_rate"] + 0.03)) ** 0.35, 0.85, 1.2)
                bal["class_hp"][c] = round(bal["class_hp"].get(c, 1.0) * f, 3)
                log(f"    {c} HP x{f:.2f}")
                changed = True
        if not changed:
            log("  balanced: every target is inside its band.")
            return bal, res, True
        save_balance(bal)
        log("    checkpoint saved: assets/balance.json")
    return bal, res, False


def write_report(res, bal, path_md, path_json, train_info):
    st = {c: stats(r) for c, (r, _) in res.items()}
    pol = {c: p for c, (_, p) in res.items()}
    names = {k: v["name"] for k, v in data.ENEMIES.items()}
    L = ["# Balance Report", "",
         f"Generated by `tools/balance.py` - {time.strftime('%Y-%m-%d %H:%M')}. {train_info}", "",
         "Each class's reinforcement-learning agent played fresh seeds it never trained on, "
         "with greedy (best-move) play.", "",
         "## Win rates", "", "| Class | Win rate | Avg battles won | Died in stage 1 / 2 / 3 | Deaths to bosses | "
         "Deaths to mobs |", "|---|---|---|---|---|---|"]
    for c, s in st.items():
        d = s["died_stage"]
        L.append(f"| {c} | {s['win_rate']*100:.1f}% | {s['avg_battles']:.1f} | "
                 f"{d[1]*100:.0f}% / {d[2]*100:.0f}% / {d[3]*100:.0f}% | {s['death_share_boss']*100:.0f}% | "
                 f"{s['death_share_mobs']*100:.0f}% |")
    L += ["", "## Deadliest enemies (share of encounters the agent lost)", ""]
    leth = defaultdict(list)
    for s in st.values():
        for e, v in s["lethality"].items():
            leth[e].append(v)
    rows = sorted(((sum(v) / len(v), e) for e, v in leth.items()), reverse=True)
    L += ["| Enemy | Loss rate |", "|---|---|"] + [f"| {names.get(e, e)} | {v*100:.1f}% |" for v, e in rows[:15]]
    L += ["", "## Items: what the agents take and what wins", "",
          "Pick rate = taken when offered. Kit win rate = runs won when the item was in the final kit.", ""]
    for c, s in st.items():
        top = sorted(s["kit_win_rate"].items(), key=lambda kv: -kv[1])[:6]
        low = sorted(s["kit_win_rate"].items(), key=lambda kv: kv[1])[:4]
        picks = sorted(s["pick_rate"].items(), key=lambda kv: -kv[1])[:6]
        L.append(f"**{c}**")
        L.append("- Most picked: " + ", ".join(f"{data.ITEMS[i]['name']} ({v*100:.0f}%)" for i, v in picks))
        L.append("- Strongest in winning kits: " + ", ".join(f"{data.ITEMS[i]['name']} ({v*100:.0f}%)" for i, v in top))
        L.append("- Weakest: " + ", ".join(f"{data.ITEMS[i]['name']} ({v*100:.0f}%)" for i, v in low))
        L.append("- What the agent learned to value: " + ", ".join(f"{n} {w:+}" for n, w in pol[c]))
        L.append("")
    L += ["## Balance knobs in use (assets/balance.json)", "", "```json", json.dumps(bal, indent=2), "```"]
    open(path_md, "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump(dict(balance=bal, stats=st), open(path_json, "w", encoding="utf-8"), indent=1, default=str)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--episodes", type=int, default=4000, help="training runs per class")
    ap.add_argument("--eval", type=int, default=300, help="evaluation runs per class")
    ap.add_argument("--autotune", action="store_true")
    ap.add_argument("--target", type=float, default=0.20, help="target win rate for a skilled player")
    ap.add_argument("--rounds", type=int, default=6)
    ap.add_argument("--skip-train", action="store_true",
                    help="reuse the agents saved in assets/ai instead of training from scratch (faster re-tunes)")
    ap.add_argument("--checkpoint", action="store_true",
                    help="stop at the first balanced point: skip retraining and report that round's win rates")
    ap.add_argument("--report", type=int, default=0, metavar="RUNS",
                    help="afterwards, write the Excel run report (tools/run_report.py) with RUNS runs per class")
    args = ap.parse_args()

    def log(msg):
        print(msg, flush=True)

    bal = json.loads(json.dumps(data.BALANCE))
    bal["stage_mult"] = {str(k): v for k, v in bal["stage_mult"].items()}
    t0 = time.time()
    with Pool(len(CLASSES)) as pool:
        have_agents = all(os.path.exists(os.path.join(ASSETS, "ai", f"{c}.npz")) for c in CLASSES)
        if args.skip_train and have_agents:
            log("[1/4] Reusing the trained agents in assets/ai (--skip-train)")
        else:
            log(f"[1/4] Training {len(CLASSES)} agents x {args.episodes} runs...")
            pool.map(_train, [(c, args.episodes, bal, False) for c in CLASSES])
            log(f"      done in {time.time() - t0:.0f}s")
        res = None
        if args.autotune:
            log("[2/4] Tuning difficulty...")
            bal, last, balanced = autotune(bal, args, pool, log)
            if args.checkpoint:
                log("[3/4] Checkpoint mode: skipping retraining")
                if balanced:
                    res = last          # those measurements already match the saved settings
            else:
                log("[3/4] Retraining agents on the tuned difficulty...")
                pool.map(_train, [(c, args.episodes // 2, bal, True) for c in CLASSES])
        if res is None:
            log("[4/4] Final measurement...")
            res = measure(args.eval, bal, pool)
    log("      " + summary_line(res))
    save_balance(bal)
    write_report(res, bal, os.path.join(ASSETS, "balance_report.md"), os.path.join(ASSETS, "balance_report.json"),
                 f"{args.episodes} training runs per class, {args.eval} test runs per class, "
                 f"{time.time() - t0:.0f}s total.")
    log(f"Wrote assets/balance.json and assets/balance_report.md ({time.time() - t0:.0f}s)")
    if args.report:
        import subprocess
        subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_report.py"),
                        "--runs", str(args.report)], check=False)


if __name__ == "__main__":
    main()
