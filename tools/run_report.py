"""Run Report: hundreds of AI runs per class -> one Excel workbook per patch, plus a picture of every
winning board. Made for balancing by CONTENT (which items, enemies, events are too strong or weak),
not just class HP.

    python tools/run_report.py                 # 200 runs per class with the trained agents
    python tools/run_report.py --runs 400      # more runs = more reliable numbers

Writes reports/v<VERSION>/:
    run_report_v<VERSION>.xlsx   Summary, Runs, Items, Enemies, Events, Techniques, Winning boards
    wins/<class>_<seed>.png      the final kit of every winning run

Needs: pip install numpy openpyxl pillow pygame-ce
How to read it is explained on the workbook's "Read me" sheet.
"""
import argparse
import collections
import datetime
import os
import statistics
import sys
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from roguegame.data import ITEMS, ENEMIES, CHARACTERS, TECHNIQUES, enemy_tier, STAGES  # noqa: E402
from roguegame.version import VERSION  # noqa: E402

SEED0 = 700_000           # report seeds: never used for training or the balance measurement


# ---------------------------------------------------------------- playing
def _play(args):
    cls, start, n = args
    from roguegame.ai import LearningAgent
    from roguegame.sim import play
    agent = LearningAgent(cls).load(os.path.join(ROOT, "assets", "ai", f"{cls}.npz"))
    agent.greedy = True
    return [play(cls, SEED0 + i, agent) for i in range(start, start + n)]


def collect(runs_per_class, workers=5):
    jobs = []
    chunk = max(1, runs_per_class // 4)
    for cls in CHARACTERS:
        for start in range(0, runs_per_class, chunk):
            jobs.append((cls, start, min(chunk, runs_per_class - start)))
    with Pool(workers) as pool:
        parts = pool.map(_play, jobs)
    return [r for part in parts for r in part]


# ---------------------------------------------------------------- winning board pictures
def render_board(run, path):
    import pygame
    from roguegame import ui
    from roguegame.inventory import Grid, ItemInst
    if not pygame.get_init():
        pygame.init()
        pygame.display.set_mode((1, 1))
    kit = run["kit"]
    cell = 54
    w, h = 40 + kit["w"] * cell + 300, 96 + kit["h"] * cell + 24
    s = pygame.Surface((w, h))
    s.fill(ui.BG)
    ch = CHARACTERS[run["char"]]
    ui.portrait(s, (44, 44), 30, ch["color"], ch["glyph"], ch["portrait"], key=run["char"])
    ui.text(s, f"{ch['name']}  -  VICTORY", (86, 16), 24, ch["color"], True)
    ui.text(s, f"seed {run['seed']}   v{VERSION}   {run['battles']} battles   {run['max_hp']} max HP", (86, 48), 15,
            ui.DIM)
    ox, oy = 20, 92
    g = Grid(kit["w"], kit["h"])
    for it in kit["items"]:
        g.place(ItemInst.from_dict(it), it["x"], it["y"])
    for y in range(g.h):
        for x in range(g.w):
            pygame.draw.rect(s, (184, 170, 112) if (x + y) % 2 else (174, 160, 102),
                             (ox + x * cell, oy + y * cell, cell, cell))
            pygame.draw.rect(s, (120, 108, 64), (ox + x * cell, oy + y * cell, cell, cell), 1)
    for inst in g.items:
        px, py = ox + inst.x * cell, oy + inst.y * cell
        ui.draw_item(s, inst.id, inst.shape, px, py, cell, level=inst.level, rot=inst.rot)
        ui.draw_spirit(s, inst, px, py, cell)
    tx = ox + g.w * cell + 24
    ui.text(s, "TECHNIQUES", (tx, oy), 14, ui.GREEN, True)
    y = oy + 22
    for t in run["techniques"]:
        ui.text(s, TECHNIQUES[t]["name"], (tx, y), 14, ui.TEXT)
        y += 20
    y += 12
    ui.text(s, "TOP DAMAGE", (tx, y), 14, ui.GOLD, True)
    y += 22
    for iid, d in sorted(run["item_dmg"].items(), key=lambda kv: -kv[1])[:5]:
        ui.text(s, f"{ITEMS[iid]['name'][:20]}  {d}", (tx, y), 13, ui.TEXT)
        y += 19
    pygame.image.save(s, path)


# ---------------------------------------------------------------- analysis helpers
def name_of(iid):
    return ITEMS[iid]["name"] if iid in ITEMS else iid


def enemy_name(eid):
    return ENEMIES[eid]["name"].split(",")[0] if eid in ENEMIES else (eid or "")


def pct(a, b):
    return round(100.0 * a / b, 1) if b else None


def verdict_item(delta, n, pick_rate):
    if n >= 25 and delta is not None and delta >= 12:
        return "Too strong?"
    if n >= 25 and delta is not None and delta <= -12:
        return "Too weak?"
    if pick_rate is not None and pick_rate < 5:
        return "Rarely picked"
    return ""


def enemy_stage(eid):
    for s, st in STAGES.items():
        if eid in st["fights"] or eid in st["elites"] or eid in st.get("bosses", []):
            return s
    return 3


# ---------------------------------------------------------------- the workbook
def build_workbook(runs, out_xlsx, board_dir, embed_boards=True):
    from openpyxl import Workbook
    from openpyxl.drawing.image import Image as XLImage
    from openpyxl.formatting.rule import ColorScaleRule
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    head_fill = PatternFill("solid", fgColor="2A2638")
    head_font = Font(bold=True, color="F0E6C8")

    def sheet(title, headers, rows, widths=None, pct_cols=(), scale_cols=()):
        ws = wb.create_sheet(title)
        ws.append(headers)
        for c in ws[1]:
            c.fill, c.font = head_fill, head_font
            c.alignment = Alignment(wrap_text=True, vertical="center")
        for r in rows:
            ws.append(r)
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for i, w in enumerate(widths or [], start=1):
            ws.column_dimensions[get_column_letter(i)].width = w
        n = len(rows) + 1
        for col, (lo, hi) in scale_cols:       # red = bad for the player .. green = good, or reversed
            letter = get_column_letter(headers.index(col) + 1)
            ws.conditional_formatting.add(f"{letter}2:{letter}{n}", ColorScaleRule(
                start_type="min", start_color=lo, mid_type="percentile", mid_value=50, mid_color="FFF2CC",
                end_type="max", end_color=hi))
        return ws

    by_cls = collections.defaultdict(list)
    for r in runs:
        by_cls[r["char"]].append(r)
    base_wr = {c: pct(sum(r["win"] for r in rs), len(rs)) for c, rs in by_cls.items()}
    total_wins = sum(r["win"] for r in runs)

    # ---- Read me
    ws = wb.active
    ws.title = "Read me"
    lines = [
        f"Shadow Road run report - v{VERSION}",
        f"Made {datetime.datetime.now():%Y-%m-%d %H:%M}  -  {len(runs)} runs by the trained AI ({len(by_cls)} classes, "
        f"greedy play, seeds from {SEED0}). Overall success {pct(total_wins, len(runs))}%.",
        "",
        "Success = the stage-3 villain was defeated.",
        "Summary: win rate, how deep runs get and what ends them, per class.",
        "Runs: one row per run - where it ended (stage + floor), the final board, MVP item, techniques, events.",
        "Items: pick rate (picked / offered) and how often runs that FINISHED with the item won, compared with "
        "that class's normal win rate (Win-rate delta). Big + = maybe too strong, big - = maybe too weak.",
        "Enemies: how often each enemy beats the player, and how much HP it takes when the player wins. "
        "Bosses should be dangerous; a regular mob with a high kill rate may be over-tuned.",
        "Events: how often each option is picked and how runs that picked it ended.",
        "Techniques: how often each is learned and the win rate of runs that learned it.",
        "Winning boards: the final kit of every winning run (also saved as PNGs in the wins folder).",
        "",
        "Caveats: the AI is a decent but not perfect player. Treat small samples (n < 25) with care.",
        "Correlation is not causation: strong players buy strong items, so compare items within a class.",
    ]
    for ln in lines:
        ws.append([ln])
    ws.column_dimensions["A"].width = 140
    ws["A1"].font = Font(bold=True, size=16)

    # ---- Summary
    rows = []
    for cls, rs in by_cls.items():
        wins = [r for r in rs if r["win"]]
        losses = [r for r in rs if not r["win"]]
        killers = collections.Counter(r["died_to"] for r in losses if r["died_to"])
        mvps = collections.Counter(max(r["item_dmg"].items(), key=lambda kv: kv[1])[0] for r in wins if r["item_dmg"])
        died_stage = collections.Counter(r["stage"] for r in losses)
        rows.append([CHARACTERS[cls]["name"], len(rs), len(wins), base_wr[cls],
                     round(statistics.mean(r["stage"] for r in rs), 2),
                     round(statistics.mean(r["battles"] for r in rs), 1),
                     round(statistics.mean(r["gold_earned"] for r in rs), 1),
                     round(statistics.mean(r["max_hp"] for r in rs), 1),
                     died_stage.get(1, 0), died_stage.get(2, 0), died_stage.get(3, 0),
                     ", ".join(f"{enemy_name(e)} ({c})" for e, c in killers.most_common(3)),
                     ", ".join(f"{name_of(i)} ({c})" for i, c in mvps.most_common(3))])
    sheet("Summary", ["Class", "Runs", "Wins", "Win %", "Avg stage reached", "Avg battles won", "Avg ryō earned",
                      "Avg max HP", "Died in stage 1", "Died in stage 2", "Died in stage 3", "Top killers",
                      "Most common MVP item in wins"], rows,
          [14, 7, 7, 8, 10, 10, 10, 10, 9, 9, 9, 48, 52], scale_cols=[("Win %", ("F8696B", "63BE7B"))])

    # ---- Runs
    rows = []
    for r in runs:
        mvp = max(r["item_dmg"].items(), key=lambda kv: kv[1]) if r["item_dmg"] else (None, 0)
        kit = ", ".join(f"{name_of(i['id'])}{' L' + str(i['level']) if i['level'] > 1 else ''}"
                        for i in r["kit"]["items"])
        rows.append([CHARACTERS[r["char"]]["name"], r["seed"], "YES" if r["win"] else "no", r["stage"], r["floor"],
                     "" if r["win"] else enemy_name(r["died_to"]), r["death_kind"] or "", r["battles"],
                     sum(1 for f in r["fights"] if f["won"] and f["kind"] == "elite"),
                     sum(1 for f in r["fights"] if f["won"] and f["kind"] == "boss"),
                     r["gold_earned"], r["max_hp"], sum(r["item_dmg"].values()),
                     name_of(mvp[0]) if mvp[0] else "", mvp[1], kit,
                     ", ".join(TECHNIQUES[t]["name"] for t in r["techniques"]),
                     ", ".join(f"{name_of(i)}: {k}" for i, k in r["awakened"]),
                     ", ".join(f"{name_of(i)} <- {name_of(s)}" for i, s in r["infused"]),
                     ", ".join(name_of(x) for x in r["recipes"]), ", ".join(r["events"]), " > ".join(r["path"])])
    sheet("Runs", ["Class", "Seed", "Success", "Stage", "Floor", "Killed by", "Death node", "Battles won",
                   "Elites beaten", "Bosses beaten", "Ryō earned", "Max HP", "Damage dealt", "MVP item",
                   "MVP damage", "Final board", "Techniques", "Awakened (tsukumogami)", "Soul-bound",
                   "Recipes made", "Events chosen", "Path"], rows,
          [12, 9, 8, 6, 6, 20, 10, 8, 8, 8, 8, 7, 9, 22, 9, 80, 40, 30, 30, 24, 40, 60])

    # ---- Items
    offered = collections.Counter()
    picked = collections.Counter()
    held = collections.defaultdict(list)          # item -> [(class, win)]
    dmg = collections.defaultdict(list)
    for r in runs:
        offered.update(r["offered"])
        picked.update(r["picks"])
        for iid in {i["id"] for i in r["kit"]["items"]}:
            held[iid].append((r["char"], r["win"]))
        for iid, d in r["item_dmg"].items():
            dmg[iid].append(d)
    rows = []
    for iid, d in ITEMS.items():
        if d["enemy"]:
            continue
        h = held.get(iid, [])
        n = len(h)
        wr = pct(sum(w for _, w in h), n)
        expected = statistics.mean(base_wr[c] for c, _ in h) if h else None   # what these classes usually win
        delta = round(wr - expected, 1) if n and expected is not None else None
        pr = pct(picked[iid], offered[iid]) if offered[iid] else None
        rows.append([d["name"], CHARACTERS[d["cls"]]["name"] if d["cls"] else "shared", d["rarity"], d["price"],
                     "recipe" if d.get("recipe") else ("enemy drop" if d.get("loot") else "shop"),
                     offered[iid], picked[iid], pr, n, wr, delta,
                     round(statistics.mean(dmg[iid]), 1) if dmg[iid] else 0, verdict_item(delta, n, pr)])
    rows.sort(key=lambda r: (r[10] is None, -(r[10] or 0)))
    sheet("Items", ["Item", "Class", "Rarity", "Price", "Source", "Times offered", "Times picked", "Pick %",
                    "Runs ending with it", "Win % with it", "Win-rate delta vs class", "Avg damage per run",
                    "Verdict"], rows, [26, 12, 10, 7, 10, 9, 9, 8, 9, 9, 11, 11, 14],
          scale_cols=[("Win-rate delta vs class", ("F8696B", "63BE7B"))])

    # ---- Enemies
    fights = collections.defaultdict(list)
    for r in runs:
        for f in r["fights"]:
            fights[f["enemy"]].append(f)
    rows = []
    for eid, fs in fights.items():
        won = [f for f in fs if f["won"]]
        lost = len(fs) - len(won)
        hp_lost = [100.0 * (f["hp_before"] - f["hp_after"]) / max(1, f["max_hp"]) for f in won]
        tier = enemy_tier(eid)
        lr = pct(lost, len(fs))
        flag = ""
        if tier == "mob" and lr is not None and lr >= 12 and len(fs) >= 20:
            flag = "Mob kills a lot"
        elif tier == "elite" and lr is not None and lr >= 25 and len(fs) >= 20:
            flag = "Elite too deadly?"
        elif tier == "boss" and lr is not None and lr >= 55 and len(fs) >= 20:
            flag = "Boss too deadly?"
        elif tier == "boss" and lr is not None and lr <= 15 and len(fs) >= 20:
            flag = "Boss too easy?"
        rows.append([enemy_name(eid), tier, enemy_stage(eid), len(fs), lost, lr,
                     round(statistics.mean(hp_lost), 1) if hp_lost else None,
                     round(statistics.mean(f["time"] for f in fs), 1),
                     round(statistics.mean(f["enemy_hp"] for f in fs)), flag])
    rows.sort(key=lambda r: (r[2], ["mob", "elite", "boss"].index(r[1]), -(r[5] or 0)))
    sheet("Enemies", ["Enemy", "Tier", "Stage", "Fights", "Player losses", "Player loss %",
                      "Avg HP% lost when player wins", "Avg fight time (s)", "Avg enemy max HP", "Flag"], rows,
          [26, 7, 6, 7, 8, 9, 12, 10, 10, 18],
          scale_cols=[("Player loss %", ("63BE7B", "F8696B")), ("Avg HP% lost when player wins", ("63BE7B", "F8696B"))])

    # ---- Events
    from roguegame.events import EVENT_BY_ID
    picks = collections.defaultdict(list)
    for r in runs:
        for lab in r["events"]:
            picks[lab].append(r["win"])
    rows = []
    for lab, ws_ in sorted(picks.items()):
        eid, i = lab.rsplit(":", 1)
        ev = EVENT_BY_ID.get(eid)
        title = ev["title"] if ev else eid
        opt = ev["options"][int(i)]["label"] if ev and int(i) < len(ev["options"]) else lab
        rows.append([title, opt, len(ws_), pct(sum(ws_), len(ws_))])
    sheet("Events", ["Event", "Option", "Times chosen", "Win % of runs that chose it"], rows, [30, 70, 10, 12],
          scale_cols=[("Win % of runs that chose it", ("F8696B", "63BE7B"))])

    # ---- Techniques
    learned = collections.defaultdict(list)
    offered_t = collections.Counter()
    for r in runs:
        offered_t.update(r.get("techs_offered", []))
        for t in r["techniques"]:
            learned[t].append(r["win"])
    rows = []
    for t, d in TECHNIQUES.items():
        ws_ = learned.get(t, [])
        rows.append([d["name"], CHARACTERS[d["cls"]]["name"], "endless" if d.get("endless") else "story",
                     offered_t[t], len(ws_), pct(len(ws_), offered_t[t]) if offered_t[t] else None,
                     pct(sum(ws_), len(ws_)), d["desc"]])
    sheet("Techniques", ["Technique", "Class", "Type", "Times offered", "Times learned", "Pick %", "Win % when learned",
                         "Effect"], rows, [22, 12, 8, 9, 9, 8, 10, 60],
          scale_cols=[("Win % when learned", ("F8696B", "63BE7B"))])

    # ---- Winning boards
    ws = wb.create_sheet("Winning boards")
    ws.append(["Class", "Seed", "Battles", "Max HP", "Board"])
    for c in ws[1]:
        c.fill, c.font = head_fill, head_font
    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["E"].width = 100
    row = 2
    for r in runs:
        if not r["win"]:
            continue
        png = os.path.join(board_dir, f"{r['char']}_{r['seed']}.png")
        ws.cell(row=row, column=1, value=CHARACTERS[r["char"]]["name"])
        ws.cell(row=row, column=2, value=r["seed"])
        ws.cell(row=row, column=3, value=r["battles"])
        ws.cell(row=row, column=4, value=r["max_hp"])
        if embed_boards and os.path.exists(png):
            img = XLImage(png)
            img.width, img.height = img.width * 0.6, img.height * 0.6
            ws.add_image(img, f"E{row}")
            ws.row_dimensions[row].height = img.height * 0.78
        row += 1
    wb.save(out_xlsx)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=int, default=200, help="runs per class")
    ap.add_argument("--no-images", action="store_true", help="skip the winning-board pictures")
    a = ap.parse_args()
    out_dir = os.path.join(ROOT, "reports", f"v{VERSION}")
    board_dir = os.path.join(out_dir, "wins")
    os.makedirs(board_dir, exist_ok=True)
    print(f"Playing {a.runs} runs per class with the trained agents...", flush=True)
    runs = collect(a.runs)
    wins = [r for r in runs if r["win"]]
    print(f"{len(runs)} runs, {len(wins)} wins. Drawing winning boards...", flush=True)
    if not a.no_images:
        for r in wins:
            render_board(r, os.path.join(board_dir, f"{r['char']}_{r['seed']}.png"))
    out = os.path.join(out_dir, f"run_report_v{VERSION}.xlsx")
    build_workbook(runs, out, board_dir, embed_boards=not a.no_images)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
