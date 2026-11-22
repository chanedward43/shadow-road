"""How far do the trained agents get in Endless mode? (run after tools/balance.py)

    python tools/endless_report.py            # 60 runs per class
    python tools/endless_report.py --runs 150

Prints, per class: % of runs reaching each stage, average deepest stage, and what killed them at
stage 4+. Use it to tune ENDLESS_GROWTH / BLOOD_MOON_JUMP in roguegame/data.py.
"""
import argparse
import collections
import os
import sys
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from roguegame.ai import LearningAgent  # noqa: E402
from roguegame.data import CHARACTERS, ENEMIES  # noqa: E402
from roguegame.sim import play  # noqa: E402

SEED0 = 900_000


def _run(args):
    cls, n = args
    agent = LearningAgent(cls).load(os.path.join(ROOT, "assets", "ai", f"{cls}.npz"))
    agent.greedy = True
    return cls, [play(cls, SEED0 + i, agent, endless=True, max_stage=12) for i in range(n)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=60)
    a = ap.parse_args()
    with Pool(5) as pool:
        results = pool.map(_run, [(c, a.runs) for c in CHARACTERS])
    print(f"{'class':10} " + " ".join(f"S{s}+".rjust(6) for s in range(2, 9)) + "   avg deepest")
    for cls, runs in results:
        n = len(runs)
        reach = [sum(r["stage"] >= s for r in runs) / n * 100 for s in range(2, 9)]
        avg = sum(r["stage"] for r in runs) / n
        print(f"{cls:10} " + " ".join(f"{p:5.0f}%" for p in reach) + f"   {avg:5.2f}")
    deaths = collections.Counter(r["died_to"] for _, runs in results for r in runs
                                 if r["stage"] >= 4 and r["died_to"])
    print("\nKilled at stage 4+:", ", ".join(f"{ENEMIES[e]['name'].split(',')[0]} {c}" for e, c in deaths.most_common(10)))


if __name__ == "__main__":
    main()
