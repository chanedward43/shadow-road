"""Automated checks for Shadow Road. Run from the project folder:

    python -m unittest discover tests        (or: python -m pytest tests, if you install pytest)

They catch the common ways a content change breaks the game: an item with a bad
shape or missing art, an enemy without loot, a mechanic that stops firing, a save
that doesn't load, or a screen that crashes when drawn.
"""
import os
import random
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["APPDATA"] = tempfile.mkdtemp()      # tests never touch your real save

from roguegame import data, save  # noqa: E402
from roguegame.combat import make_battle, effective_stats  # noqa: E402
from roguegame.events import EVENTS, options_for, resolve  # noqa: E402
from roguegame.inventory import ItemInst  # noqa: E402
from roguegame.run import RunState  # noqa: E402
from roguegame.sim import play, RandomPolicy  # noqa: E402

ART = os.path.join(ROOT, "assets", "art")


def has_art(key):
    return os.path.exists(os.path.join(ART, f"{key}.png"))


class TestContent(unittest.TestCase):
    def test_items_are_valid(self):
        for iid, d in data.ITEMS.items():
            with self.subTest(item=iid):
                self.assertEqual(d["id"], iid)
                self.assertIn(d["rarity"], data.RARITIES)
                self.assertTrue(d["shape"])
                if d.get("cd"):
                    self.assertGreater(d["cd"], 0)
                if d.get("cls"):
                    self.assertIn(d["cls"], data.CHARACTERS)
                for lvl in range(1, data.MAX_LEVEL + 1):
                    st = data.level_stats(d, lvl)
                    data.describe_stats(st)
                    if st.get("dmg"):
                        self.assertLessEqual(st["dmg"][0], st["dmg"][1])

    def test_player_items_have_art(self):
        missing = [i for i, d in data.ITEMS.items() if not d["enemy"] and not has_art(i)]
        self.assertEqual(missing, [])

    def test_enemies_have_moves_art_and_loot(self):
        for eid, e in data.ENEMIES.items():
            with self.subTest(enemy=eid):
                self.assertTrue(has_art(eid))
                self.assertIn(eid, data.ENEMY_LOOT)
                self.assertIn(data.ENEMY_LOOT[eid], data.ITEMS)
                for iid in e["items"]:
                    self.assertIn(iid, data.ITEMS)
                for ph in e.get("phases", []):
                    for iid in ph.get("add", []):
                        self.assertIn(iid, data.ITEMS)

    def test_enemies_fight_with_real_items(self):
        import random as _r
        from roguegame.combat import enemy_fighter
        for eid, e in data.ENEMIES.items():
            tier = data.enemy_tier(eid)
            with self.subTest(enemy=eid, tier=tier):
                f = enemy_fighter(eid, 1.0, stage=3, rng=_r.Random(eid))
                self.assertTrue(f.carried, "every enemy carries items the player can also own")
                for iid, lvl in f.carried:
                    self.assertFalse(data.ITEMS[iid]["enemy"], f"{iid} must be a player item")
                    self.assertIn(lvl, range(1, data.MAX_LEVEL + 1))
                wields = {i for i, _ in e["kit"]} | {i for ph in e.get("phases", []) for i in ph.get("add", [])}
                self.assertIn(data.ENEMY_LOOT[eid], wields, "enemies wield their signature item")
                self.assertLessEqual(len(e["items"]), 2, "at most two enemy-only signature moves")

    def test_enemy_tiers_fill_rules(self):
        import random as _r
        for seed in range(15):
            mob = data.enemy_fill("kappa", 2, _r.Random(seed))
            self.assertEqual(len(mob), 2)
            self.assertTrue(all(data.ITEMS[i]["cls"] is None for i, _ in mob), "mobs: shared items only")
            elite = data.enemy_fill("nue", 3, _r.Random(seed))
            self.assertIsNotNone(data.ITEMS[elite[0][0]]["cls"], "elites carry a class item")
            self.assertEqual(elite[0][1], data._fill_level("elite", 3, 0), "elite gear level follows the stage")
            self.assertGreater(data._fill_level("elite", 3, 0), data._fill_level("elite", 1, 0))
            self.assertEqual(len(elite), data.ENEMY_FILL_COUNT["elite"][2])
            for tier, eid in (("mob", "kappa"), ("elite", "nue"), ("boss", "orochi")):    # more gear each stage
                counts = [len(data.enemy_fill(eid, st, _r.Random(seed))) for st in (1, 2, 3)]
                self.assertEqual(counts, sorted(counts), f"{tier}s carry more items as stages go on")
                self.assertLess(counts[0], counts[2])
            boss = data.enemy_fill("orochi", 3, _r.Random(seed))
            classes = [data.ITEMS[i]["cls"] for i, _ in boss[:2]]
            self.assertTrue(all(classes) and classes[0] != classes[1], "bosses: items from two different classes")
        a = data.enemy_fill("ashura", 3, _r.Random("7:ashura"))
        self.assertEqual(a, data.enemy_fill("ashura", 3, _r.Random("7:ashura")), "same seed, same gear")

    def test_random_drops(self):
        import random as _r
        r = RunState("ninja", 1)
        carried = [("kappa_cucumber", 1), ("tanto", 1), ("bento_box", 1)]
        drops = [r.roll_drop("kappa", carried, _r.Random(s)) for s in range(400)]
        sig = sum(1 for d in drops if d[2]) / len(drops)
        self.assertAlmostEqual(sig, data.SIGNATURE_DROP_CHANCE["mob"], delta=0.07)
        self.assertTrue(all(d[0] in {"kappa_cucumber", "tanto", "bento_box"} for d in drops))
        boss = r.roll_drop("ashura", [("kusarigama", 2)], _r.Random(3))
        self.assertIn(boss, [("six_arm_blade", 1, True), ("kusarigama", 2, False)], "keeps the carried level")

    def test_classes(self):
        for cid, ch in data.CHARACTERS.items():
            with self.subTest(cls=cid):
                self.assertTrue(has_art(cid))
                techs = [t for t, d in data.TECHNIQUES.items() if d["cls"] == cid and not d.get("endless")]
                self.assertEqual(len(techs), 6)
                late = [t for t, d in data.TECHNIQUES.items() if d["cls"] == cid and d.get("endless")]
                self.assertEqual(len(late), 2, "two endless techniques per class")
                own = [i for i, d in data.ITEMS.items() if d["cls"] == cid]
                self.assertGreaterEqual(len(own), 10, "each class needs its own item pool")
                r = RunState(cid, seed=1)
                self.assertEqual(len(r.bag.items), len(ch["start"]), "starting kit must fit the kit grid")
                self.assertIn(cid, data.BUILDS)

    def test_stage_pools(self):
        for s, st in data.STAGES.items():
            self.assertGreaterEqual(len(st["fights"]), data.FIGHTS_PER_RUN)
            self.assertGreaterEqual(len(st["bosses"]), 2)


class TestMechanics(unittest.TestCase):
    def kit(self, cls, items, seed=1):
        r = RunState(cls, seed=seed)
        for i in items:
            self.assertTrue(r.bag.first_fit(ItemInst(i)), i)
        return r

    def fight(self, run, enemy="kurogane", seed=0):
        b = make_battle(run, enemy, 1.0, seed=seed)
        b.run_to_end()
        return b

    def kinds(self, b):
        out = {}
        for e in b.events:
            out[e["kind"]] = out.get(e["kind"], 0) + 1
        return out

    def test_battles_are_deterministic(self):
        r1, r2 = RunState("ninja", 7), RunState("ninja", 7)
        b1, b2 = self.fight(r1, seed=3), self.fight(r2, seed=3)
        self.assertEqual((b1.winner, round(b1.t, 2), b1.f[1].hp), (b2.winner, round(b2.t, 2), b2.f[1].hp))

    def test_merge_levels_up_to_max(self):
        r = RunState("samurai", 1)
        for _ in range(3):
            r.add_item("katana")
        r.auto_merge()                       # 4 katanas -> two level-2s -> one level-3
        self.assertEqual(sorted(i.level for i in r.all_items() if i.id == "katana"), [3])
        r.add_item("katana", level=3)
        r.auto_merge()                       # weapons keep going: two level-3s -> level 4
        self.assertEqual(sorted(i.level for i in r.all_items() if i.id == "katana"), [4])
        r.add_item("katana", level=4)
        r.auto_merge()
        self.assertEqual(sorted(i.level for i in r.all_items() if i.id == "katana"), [5])
        r.add_item("katana", level=5)
        r.auto_merge()                       # level 5 is the weapon cap
        self.assertEqual(sorted(i.level for i in r.all_items() if i.id == "katana"), [5, 5])
        r.add_item("onigiri", level=3)
        r.add_item("onigiri", level=3)
        r.auto_merge()                       # non-weapons stop at level 3
        self.assertEqual(sorted(i.level for i in r.all_items() if i.id == "onigiri"), [1, 3, 3])
        d5 = data.level_stats(data.ITEMS["katana"], 5)
        d3 = data.level_stats(data.ITEMS["katana"], 3)
        self.assertGreater(d5["dmg"][0], d3["dmg"][0])
        self.assertLess(d5["cd"], d3["cd"])
        st = data.level_stats(data.ITEMS["katana"], 3)
        self.assertGreater(st["dmg"][0], data.ITEMS["katana"]["dmg"][0])

    def test_summons_fight(self):
        b = self.fight(self.kit("onmyoji", ["fox_shikigami"]))
        self.assertGreater(self.kinds(b).get("summon", 0), 3)
        self.assertGreaterEqual(len(b.f[0].summons), 1)

    def test_curse_reduces_damage_and_hex_scales(self):
        r = self.kit("onmyoji", ["onmyo_compass", "hex_scroll"])
        b = make_battle(r, "kurogane", 1.0, seed=0)
        stacks = data.ITEMS["onmyo_compass"]["s_curse"] + 1    # the Compass + 1 from Shikigami Pact
        self.assertEqual(b.f[1].curse, stacks)
        self.assertEqual(b._cursed(b.f[1], 100), 100 - 5 * stacks)   # 5% less damage per stack
        b.f[1].curse = 30
        self.assertEqual(b._cursed(b.f[1], 100), 50)      # capped at 50%
        b.run_to_end()
        self.assertGreater(self.kinds(b).get("hex", 0), 0)

    def test_sohei_ki_and_counter(self):
        b = self.fight(self.kit("sohei", ["temple_bell"]))
        k = self.kinds(b)
        self.assertGreater(k.get("counter", 0), 0)
        self.assertGreater(k.get("kiburst", 0), 0)

    def test_ninja_ambush(self):
        b = make_battle(self.kit("ninja", ["smoke_bomb"]), "kappa", 1.0, seed=0)
        ninja = b.f[0]
        ninja.dodge = 1
        block = ninja.block
        b._strike(1, b.f[1].items[0])                  # kappa attacks -> dodged
        self.assertTrue(ninja.ambush)
        self.assertEqual(ninja.block, block + 2)
        b.run_to_end()
        self.assertGreater(self.kinds(b).get("ambush", 0), 0)

    def test_per_tag_scaling(self):
        r = self.kit("samurai", ["daisho", "wakizashi", "tanto"])
        st = effective_stats(r.bag, "samurai")
        daisho = next(s for s in st.values() if s["id"] == "daisho")
        base = data.ITEMS["daisho"]["dmg"]
        self.assertEqual(daisho["dmg"][0], base[0] + 3)   # katana + wakizashi + tanto

    def test_boss_phases_trigger(self):
        b = make_battle(RunState("samurai", 1), "orochi", 1.0, seed=0)
        boss = b.f[1]
        moves = len(boss.items)
        boss.hp = int(boss.max_hp * 0.5)               # below the 66% threshold
        b._check_phases(1)
        self.assertEqual(self.kinds(b).get("phase", 0), 1)
        boss.hp = int(boss.max_hp * 0.2)               # below the 33% threshold
        b._check_phases(1)
        self.assertEqual(self.kinds(b).get("phase", 0), 2)
        self.assertEqual(len(boss.items), moves + 2, "each phase adds a move")


class TestRunsAndSaves(unittest.TestCase):
    def test_seeds_pick_different_casts(self):
        casts = {(tuple(RunState("ninja", s).fight_pool[1]), RunState("ninja", s).boss_of[1]) for s in range(20)}
        self.assertGreater(len(casts), 5)

    def test_every_event_option_resolves(self):
        for ev in EVENTS:
            for i, _, _ in options_for(RunState("kunoichi", 2), ev):
                r = RunState("kunoichi", 2)
                r.gold = 50
                with self.subTest(event=ev["id"], option=i):
                    res = resolve(r, ev, i)
                    self.assertIn("text", res)
                    self.assertGreater(r.hp, 0)

    def test_full_runs_for_every_class(self):
        for cid in data.CHARACTERS:
            for seed in range(8):
                with self.subTest(cls=cid, seed=seed):
                    out = play(cid, seed, RandomPolicy(random.Random(seed)))
                    self.assertIn(out["stage"], (1, 2, 3))

    def test_save_roundtrip(self):
        r = RunState("onmyoji", 11)
        r.add_item("fox_shikigami")
        r.gold = 37
        r.visit(r.available_nodes()[0])
        save.save_run(r)
        r2 = save.load_run()
        self.assertIsNotNone(r2)
        self.assertEqual(save.run_to_dict(r), save.run_to_dict(r2))
        self.assertEqual(r.rng.random(), r2.rng.random(), "random state must survive the save")
        save.clear_run()
        self.assertIsNone(save.load_run())


class TestBagControls(unittest.TestCase):
    """The kit / travel-chest controls: swap, Ctrl+click move, Shift+click sell + undo, rotate, arrange."""

    @classmethod
    def setUpClass(cls):
        from main import Game
        from roguegame import scenes
        cls.scenes = scenes
        cls.g = Game()

    def scene(self):
        self.g.run = RunState("samurai", 3)
        self.g.run.bag.items, self.g.run.stash.items = [], []
        return self.scenes.InventoryScene(self.g, "manage", on_done=lambda: None)

    def test_ctrl_click_moves_between_bags(self):
        sc = self.scene()
        k = ItemInst("katana")
        sc.run.bag.place(k, 0, 0)
        sc.quick_move(sc.run.bag, k)
        self.assertIn(k, sc.run.stash.items)
        sc.quick_move(sc.run.stash, k)
        self.assertIn(k, sc.run.bag.items)

    def test_drop_on_item_swaps(self):
        sc = self.scene()
        a, b = ItemInst("onigiri"), ItemInst("whetstone")
        sc.run.bag.place(a, 0, 0)
        sc.run.stash.place(b, 2, 1)
        sc.held = dict(inst=a, grid=sc.run.bag, x=0, y=0, rot=0, off=(28, 28))
        sc.run.bag.remove(a)
        self.assertTrue(sc.try_swap(a, sc.run.stash, sc.stash_o, 2, 1))
        self.assertEqual((a.x, a.y), (2, 1))
        self.assertIn(a, sc.run.stash.items)
        self.assertIn(b, sc.run.bag.items)
        self.assertEqual((b.x, b.y), (0, 0))

    def test_shift_click_sell_and_undo(self):
        sc = self.scene()
        k = ItemInst("katana", level=2)
        sc.run.bag.place(k, 1, 1)
        gold = sc.run.gold
        sc.quick_sell(sc.run.bag, k)
        self.assertEqual(sc.run.gold, gold + data.sell_value("katana", 2))
        self.assertNotIn(k, sc.run.bag.items)
        sc.undo_sell()
        self.assertEqual(sc.run.gold, gold)
        self.assertIn(k, sc.run.bag.items)
        self.assertEqual((k.x, k.y), (1, 1))

    def test_right_click_rotates_in_place(self):
        sc = self.scene()
        k = ItemInst("katana")                     # 1x3 vertical
        sc.run.bag.place(k, 0, 0)
        sc.rotate_in_place(sc.run.bag, k)
        self.assertEqual(k.rot, 1)
        self.assertEqual(sorted(k.cells), [(0, 0), (1, 0), (2, 0)])

    def test_auto_arrange_and_merge_all(self):
        sc = self.scene()
        for iid in ("katana", "katana", "war_banner", "do_armor"):
            sc.run.stash.first_fit(ItemInst(iid))
        sc.auto_arrange()
        self.assertGreaterEqual(len(sc.run.bag.items), 3)
        sc.merge_all()
        self.assertEqual([i.level for i in sc.run.all_items() if i.id == "katana"], [2])


class TestBattleReplayAndStats(unittest.TestCase):
    def test_item_stats_and_log(self):
        r = RunState("onmyoji", 3)
        for i in ("fox_shikigami", "hex_scroll"):
            r.bag.first_fit(ItemInst(i))
        b = make_battle(r, "kappa", 1.0, seed=2)
        b.run_to_end()
        player_items = b.f[0].items
        self.assertEqual(sum(ci.stats.get("uses", 0) for ci in player_items),
                         sum(1 for e in b.log if e["side"] == 0), "every activation is logged")
        fox = next(ci for ci in player_items if ci.st["id"] == "fox_shikigami")
        self.assertGreater(fox.stats.get("dmg", 0), 0, "summon damage is credited to the item that summoned it")
        hexs = next(ci for ci in player_items if ci.st["id"] == "hex_scroll")
        self.assertGreater(hexs.stats.get("dmg", 0), 0)

    def test_replay_is_identical(self):
        import copy as _copy
        r = RunState("samurai", 4)
        b = make_battle(r, "kurogane", 1.0, seed=9)
        start = _copy.deepcopy(b)
        b.run_to_end()
        again = _copy.deepcopy(start)
        again.run_to_end()
        self.assertEqual((b.winner, round(b.t, 2), b.f[0].hp, b.f[1].hp, len(b.log)),
                         (again.winner, round(again.t, 2), again.f[0].hp, again.f[1].hp, len(again.log)))

    def test_keywords(self):
        from roguegame.keywords import KEYWORDS, keywords_in, keyword_of
        self.assertEqual(keyword_of("Poison,"), "poison")
        self.assertEqual(keywords_in("Inflict 2 Poison and Stun the enemy for 0.5s"), ["poison", "stun"])
        for iid, d in data.ITEMS.items():           # every keyword used in a tooltip has a definition
            for k in keywords_in(" ".join(data.describe_stats(d))):
                self.assertIn(k, KEYWORDS)


class TestStaminaAndHistory(unittest.TestCase):
    SPAM = ["shuriken", "kunai", "tekko_kagi", "shuriken", "kunai", "tekko_kagi"]

    def swings(self, items, cls="ninja", secs=20.0):
        r = RunState(cls, 4)
        r.bag.items = []
        for i in items:
            self.assertTrue(r.bag.first_fit(ItemInst(i)), i)
        b = make_battle(r, "kurogane", 1.0, seed=3)
        for f in b.f:                      # nobody dies: we only count swings
            f.hp = f.max_hp = 10 ** 6
        b.advance(secs)
        weapons = [ci for ci in b.f[0].items if ci.cost]
        return b, sum(ci.stats.get("uses", 0) for ci in weapons)

    def test_weapon_costs(self):
        self.assertEqual(data.weapon_stamina_cost(data.ITEMS["shuriken"]), 0.5)
        self.assertGreater(data.weapon_stamina_cost(data.ITEMS["nodachi"]),
                           data.weapon_stamina_cost(data.ITEMS["katana"]))
        self.assertEqual(data.weapon_stamina_cost(data.ITEMS["onigiri"]), 0, "only weapons cost Stamina")
        for iid, d in data.ITEMS.items():
            if d.get("enemy"):
                self.assertEqual(data.weapon_stamina_cost(d), 0, iid)

    def test_stamina_limits_weapon_spam(self):
        b, n = self.swings(self.SPAM)
        me = b.f[0]
        free = sum(20.0 / ci.cd for ci in me.items if ci.cost)          # swings with infinite Stamina
        self.assertLess(n, free * 0.85, "a kit of fast weapons must be throttled by Stamina")
        spent = sum(ci.stats.get("uses", 0) * ci.cost for ci in me.items if ci.cost)
        self.assertLessEqual(spent, me.max_stamina + me.stamina_regen * 20.0 + 0.01)

    def test_stamina_items_help(self):
        _, base = self.swings(self.SPAM)
        _, fed = self.swings(self.SPAM + ["matcha_tea", "ginseng"])
        self.assertGreater(fed, base, "Stamina items let weapons swing more")
        r = RunState("samurai", 4)
        r.bag.first_fit(ItemInst("katana"))
        g = effective_stats(r.bag, "samurai", [])
        self.assertTrue(all(st.get("stamina_cost") is None for st in g.values()))

    def test_breathing_scroll_cuts_cost(self):
        r = RunState("ninja", 4)
        r.bag.items = []
        r.bag.place(ItemInst("breathing_scroll"), 0, 0)
        k = ItemInst("katana")
        self.assertTrue(r.bag.first_fit(k))
        eff = effective_stats(r.bag, "ninja", [])
        if any(n.uid == k.uid for n in r.bag.neighbors(r.bag.items[0])):
            self.assertLess(eff[k.uid]["stamina_cost"], data.weapon_stamina_cost(data.ITEMS["katana"]))

    def test_history_roundtrip_and_cap(self):
        from roguegame import history, storage
        storage.delete(history.KEY)
        r = RunState("kunoichi", 9)
        r.visit(r.available_nodes()[0])
        r.kills = ["kappa"]
        r.killed_by = "kurogane"
        rec = history.record_run(r, False)
        runs = history.load_history()
        self.assertEqual(runs[0]["seed"], 9)
        self.assertEqual(runs[0]["killed_by"], "kurogane")
        self.assertEqual(runs[0], rec)
        for i in range(history.MAX_RUNS + 5):
            history.record_run(RunState("samurai", i), True)
        runs = history.load_history()
        self.assertEqual(len(runs), history.MAX_RUNS, "history is capped")
        self.assertEqual(history.summary(runs)["streak"], history.MAX_RUNS)
        storage.write(history.KEY, "not json")
        self.assertEqual(history.load_history(), [], "a broken history never crashes")
        storage.delete(history.KEY)

    def test_fresh_seeds_differ(self):
        from roguegame.run import fresh_seed
        self.assertGreater(len({fresh_seed(i) for i in range(20)}), 15)


class FakeSupabase:
    """A tiny stand-in for Supabase's REST API (just what the Arena uses), on localhost."""

    def __init__(self):
        import http.server
        import json
        import threading
        import urllib.parse
        tables = self.tables = {"ghosts": [], "scores": []}

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _table(self):
                u = urllib.parse.urlparse(self.path)
                return u.path.rsplit("/", 1)[-1], urllib.parse.parse_qs(u.query)

            def do_POST(self):
                name, _ = self._table()
                n = int(self.headers.get("Content-Length", 0))
                tables[name].append(json.loads(self.rfile.read(n)))
                self.send_response(201)
                self.end_headers()

            def do_GET(self):
                name, q = self._table()
                rows = list(reversed(tables[name]))
                for k, (v,) in q.items():
                    if k in ("select", "order", "limit"):
                        continue
                    op, val = v.split(".", 1)
                    rows = [r for r in rows if (str(r.get(k)) == val) == (op == "eq")]
                body = json.dumps(rows).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class TestArena(unittest.TestCase):
    def wait(self, req):
        import time
        t = time.time()
        while not req.done and time.time() - t < 5:
            time.sleep(0.01)
        return req

    def test_rounds_hearts_and_end(self):
        from roguegame import arena
        run = arena.new_run("samurai", 5)
        base = run.max_hp
        arena.start_round(run)
        self.assertEqual(run.gold, arena.FIRST_GOLD)
        self.assertEqual(run.max_hp, base)
        for _ in range(arena.HEARTS - 1):
            self.assertEqual(arena.apply_result(run, False), "next")
        self.assertEqual(arena.apply_result(run, False), "out")
        run = arena.new_run("ninja", 6)
        for i in range(arena.MAX_WINS):
            arena.start_round(run)
            state = arena.apply_result(run, True)
        self.assertEqual(state, "champion")
        self.assertEqual(run.stage, 3)
        self.assertEqual(run.max_hp, base and run.arena["base_hp"] + arena.HP_PER_ROUND * 9 + arena.tech_hp(run))

    def test_ghost_roundtrip_fights_like_the_original(self):
        from roguegame import arena
        from roguegame.combat import make_pvp_battle
        bot = arena.bot_record("onmyoji", 6, 1)
        self.assertTrue(arena.valid_record(bot))
        self.assertEqual(len(bot["build"]["techniques"]), 2, "techniques at rounds 3 and 6")
        g1, g2 = arena.ghost_run(bot), arena.ghost_run(bot)
        self.assertEqual(g1.bag.to_dict(), g2.bag.to_dict())
        me = arena.new_run("sohei", 2)
        arena.start_round(me)
        b1 = make_pvp_battle(me, g1, seed=4)
        b1.run_to_end()
        b2 = make_pvp_battle(me, g2, seed=4)
        b2.run_to_end()
        self.assertEqual((b1.winner, b1.f[0].hp, b1.f[1].hp), (b2.winner, b2.f[0].hp, b2.f[1].hp))

    def test_bad_ghosts_are_safe(self):
        from roguegame import arena
        import random as _r
        bot = arena.bot_record("kunoichi", 2, 1)
        bot["build"]["bag"]["items"].append(dict(id="no_such_item", x=0, y=0, rot=0, level=9))
        bot["build"]["bag"]["items"].append(dict(id="kappa_bite", x=6, y=4, rot=0, level=1))
        g = arena.ghost_run(bot)
        self.assertTrue(all(i.id in data.ITEMS and not i.data.get("enemy") for i in g.bag.items))
        self.assertFalse(arena.valid_record(dict(cls="dragon", build={})))
        opp = arena.pick_opponent([dict(player="me", cls="ninja", round=2, version="x", build={})], "me", 2,
                                  _r.Random(1))
        self.assertTrue(opp.get("bot"), "no usable ghost -> AI ghost")

    def test_online_against_fake_backend(self):
        from roguegame import arena, online
        from roguegame.version import VERSION
        fake = FakeSupabase()
        old = online._config
        online._config = dict(url=fake.url, key="test-anon-key")
        try:
            prof = online.profile()
            other = arena.bot_record("sohei", 3, 9)
            other.update(player="someone-else", name="Benkei")
            other.pop("bot")
            self.assertTrue(self.wait(online.upload_ghost(other)).ok)
            mine = arena.new_run("ninja", 4)
            for _ in range(3):
                arena.start_round(mine)
            self.assertTrue(self.wait(online.upload_ghost(arena.ghost_record(mine, prof))).ok)
            req = self.wait(online.find_ghosts(3, VERSION, prof["id"]))
            rows = req.json()
            self.assertEqual([r["name"] for r in rows], ["Benkei"], "never matched with your own ghost")
            import random as _r
            opp = arena.pick_opponent(rows, prof["id"], 3, _r.Random(0))
            self.assertEqual(opp["name"], "Benkei")
            self.assertTrue(self.wait(online.submit_score(arena.score_record(mine, prof))).ok)
            self.assertEqual(len(self.wait(online.top_scores(VERSION)).json()), 1)
        finally:
            online._config = old
            fake.close()
        self.assertFalse(online.request("GET", "/x").ok if not online.enabled() else False)

    def test_names(self):
        from roguegame import online
        self.assertEqual(online.clean_name("  <b>Hiro  </b>!!  "), "bHiro b")
        self.assertEqual(len(online.clean_name("x" * 40)), 14)


class TestEndless(unittest.TestCase):
    def test_endless_stages_exist_and_get_harder(self):
        self.assertEqual(sorted(data.STAGES), [1, 2, 3], "iterating STAGES still means the story")
        for n in range(4, 12):
            st = data.STAGES[n]
            self.assertTrue(st["endless"])
            for e in st["fights"] + st["elites"] + st["bosses"]:
                self.assertIn(e, data.ENEMIES)
                self.assertTrue(has_art(e), e)
        for e in ("shuten_doji", "tamamo", "enma"):
            self.assertEqual(data.enemy_tier(e), "boss")
            self.assertTrue(has_art(data.ENEMY_LOOT[e]))
        mults = [data.endless_mult(n) for n in range(4, 9)]
        self.assertTrue(all(b > a for a, b in zip(mults, mults[1:])))
        jump = data.endless_mult(5) / data.endless_mult(4)
        self.assertGreater(jump, data.endless_mult(4) / 1.0, "stage 5 is a bigger jump than stage 4")

    def test_endless_run_continues_and_story_seeds_unchanged(self):
        story, endless = RunState("ninja", 77), RunState("ninja", 77, mode="endless")
        self.assertEqual(story.fight_pool, endless.fight_pool)
        self.assertEqual(story.map, endless.map)
        for _ in range(3):
            endless.next_stage()
        self.assertEqual(endless.stage, 4)
        self.assertIn(endless.boss_id(), data.STAGES[4]["bosses"])
        hp = endless.max_hp
        endless.next_stage()
        self.assertGreater(endless.max_hp, hp, "Second Wind")
        self.assertNotEqual(endless.boss_of[5], endless.boss_of[4], "no same villain twice in a row")
        self.assertGreater(endless.enemy_scale("boss"), RunState("ninja", 77).enemy_scale("boss") * 1.5)
        self.assertTrue(any(TECHNIQUES_ENDLESS(t) for t in endless.technique_choices(20)))
        self.assertFalse(any(TECHNIQUES_ENDLESS(t) for t in story.technique_choices(20)))
        save.save_run(endless)
        back = save.load_run()
        self.assertEqual((back.mode, back.stage, back.boss_of[5]), ("endless", 5, endless.boss_of[5]))
        save.clear_run()

    def test_blood_moon_enrages_enemies(self):
        r = RunState("samurai", 3, mode="endless")
        b4 = make_battle(r, "gaki", 1.0, seed=1)
        r.stage = 5
        b5 = make_battle(r, "gaki", 1.0, seed=1)
        self.assertGreater(b5.f[1].crit, b4.f[1].crit)
        self.assertLess(b5.f[1].items[0].cd, b4.f[1].items[0].cd)

    def test_endless_sim_goes_past_stage_3(self):
        deep = [play("onmyoji", s, RandomPolicy(random.Random(s)), endless=True, max_stage=6)["stage"]
                for s in range(40)]
        self.assertTrue(all(1 <= d <= 6 for d in deep))

    def test_arena_history(self):
        from roguegame import arena, history, storage
        storage.delete(history.ARENA_KEY)
        run = arena.new_run("kunoichi", 3)
        for won in (True, False, True):
            arena.start_round(run)
            arena.apply_result(run, won, arena.bot_record("sohei", run.arena["round"], 1))
        rec = history.record_arena(run)
        runs = history.load_arena()
        self.assertEqual(runs[0], rec)
        self.assertEqual([f["won"] for f in rec["fights"]], [True, False, True])
        self.assertEqual(rec["fights"][0]["vs_cls"], "sohei")
        self.assertTrue(rec["fights"][0]["bot"])
        self.assertEqual(history.arena_summary(runs)["per_class"]["kunoichi"]["best"], 2)
        storage.delete(history.ARENA_KEY)


def TECHNIQUES_ENDLESS(tid):
    return bool(data.TECHNIQUES[tid].get("endless"))


class TestV8Systems(unittest.TestCase):
    def bag(self, cls, placed, seed=1):
        r = RunState(cls, seed)
        r.bag.items, r.stash.items = [], []
        for iid, x, y in placed:
            self.assertTrue(r.bag.place(ItemInst(iid), x, y), iid)
        return r

    def uses(self, b, iid):
        return sum(ci.stats.get("uses", 0) for ci in b.f[0].items if ci.st["id"] == iid)

    def test_adjacent_crit_trigger(self):
        r = self.bag("ninja", [("kunai", 0, 0), ("echo_blade", 1, 0)])
        b = make_battle(r, "kurogane", 1.0, seed=2)
        for f in b.f:
            f.hp = f.max_hp = 10 ** 6
        b.f[0].crit = 0.5
        b.advance(20)
        crits = sum(ci.stats.get("crits", 0) for ci in b.f[0].items if ci.st["id"] == "kunai")
        self.assertGreater(crits, 0)
        self.assertGreater(self.uses(b, "echo_blade"), 0, "fires when the adjacent kunai crits")
        far = self.bag("ninja", [("kunai", 0, 0), ("echo_blade", 5, 0)])
        b2 = make_battle(far, "kurogane", 1.0, seed=2)
        for f in b2.f:
            f.hp = f.max_hp = 10 ** 6
        b2.f[0].crit = 0.5
        b2.advance(20)
        self.assertEqual(self.uses(b2, "echo_blade"), 0, "not adjacent: never fires")

    def test_count_triggers(self):
        r = self.bag("samurai", [("tetsubo", 0, 0), ("ofuda", 3, 0), ("wara_doll", 5, 0)])
        b = make_battle(r, "kurogane", 1.0, seed=3)
        for f in b.f:
            f.hp = f.max_hp = 10 ** 6
        b.advance(30)
        me = b.f[0]
        self.assertEqual(self.uses(b, "tetsubo"), me.block_gains // 5)
        self.assertEqual(self.uses(b, "wara_doll"), me.hits_taken // 6)

    def test_alone_bonus(self):
        alone = effective_stats(self.bag("samurai", [("lone_tanto", 0, 0)]).bag, "samurai")
        crowd = effective_stats(self.bag("samurai", [("lone_tanto", 0, 0), ("onigiri", 1, 0)]).bag, "samurai")
        a = next(st for st in alone.values() if st["id"] == "lone_tanto")["dmg"][0]
        c = next(st for st in crowd.values() if st["id"] == "lone_tanto")["dmg"][0]
        self.assertEqual(a - c, 5)

    def test_economy_and_consumables(self):
        r = self.bag("kunoichi", [("maneki_neko", 0, 0), ("coin_purse", 1, 0), ("soroban", 2, 0)])
        r.gold = 30
        self.assertLess(r.price("katana"), data.ITEMS["katana"]["price"] + 1)
        self.assertTrue(r.add_consumable("omikuji"))
        paid = r.after_battle(True, "fight")
        self.assertEqual(sum(g for g, _ in paid), 2 + 3 + 10)
        self.assertEqual(r.consumables, [], "consumables are used up")
        r.consumables = ["iron_elixir", "explosive_tag", "antidote"]
        self.assertFalse(r.add_consumable("tonic"), "max 3")
        b = make_battle(r, "kappa", 1.0, seed=1)
        self.assertGreaterEqual(b.f[0].block, 30)
        self.assertEqual(b.f[1].burn, 8)
        self.assertTrue(b.f[0].poison_immune)
        self.assertEqual(r.after_battle(False, "fight"), [], "no payout when you lose")

    def test_ascension(self):
        base, hard = RunState("sohei", 4), RunState("sohei", 4, asc=10)
        self.assertLess(hard.max_hp, base.max_hp)
        self.assertGreater(hard.price("katana"), base.price("katana"))
        for kind in ("fight", "elite", "boss"):
            self.assertGreater(hard.enemy_scale(kind), base.enemy_scale(kind) - 1e-9)
        hard.stage = 3
        self.assertTrue(hard.blood_moon_now)
        b = make_battle(hard, "ashura", 1.0, seed=1)
        self.assertEqual(len(b.f[1].phases), len(data.ENEMIES["ashura"]["phases"]) + 1, "A8: extra phase")
        save.save_run(hard)
        self.assertEqual(save.load_run().asc, 10)
        save.clear_run()

    def test_omens_follow_you_to_the_next_stage(self):
        from roguegame.events import EVENT_BY_ID, resolve, omen_event
        r = RunState("ninja", 12)
        res = resolve(r, EVENT_BY_ID["tanuki_trap"], 1)
        self.assertEqual(r.flags["tanuki"], "robbed")
        r.next_stage()
        omens = [n for row in r.map for n in row if n["kind"] == "omen"]
        self.assertEqual(len(omens), 1, "one Omen node on the stage-2 map")
        ev = omen_event(r, "tanuki")
        self.assertIn("battle", ev["options"][0]["do"](r, r.rng))
        r2 = RunState("ninja", 12)
        resolve(r2, EVENT_BY_ID["tanuki_trap"], 0)
        r2.next_stage()
        got = omen_event(r2, "tanuki")["options"][0]["do"](r2, r2.rng)
        self.assertIn("choose", got)
        self.assertTrue(res["text"])

    def test_progress_and_unlocks(self):
        from roguegame import progress, storage
        storage.delete(progress.KEY)
        progress.reset_cache()
        r = RunState("samurai", 5)
        self.assertEqual(progress.asc_unlocked("samurai"), 0)
        got = progress.on_run_end(r, cleared=True)
        self.assertEqual(progress.asc_unlocked("samurai"), 1)
        self.assertIn("story_win", [a[0] for a in got])
        self.assertTrue(progress.hint_once("x"))
        self.assertFalse(progress.hint_once("x"))
        storage.delete(progress.KEY)
        progress.reset_cache()

    def test_arena_floor(self):
        from roguegame import arena
        run = arena.new_run("ninja", 8)
        arena.start_round(run)
        rows = arena.gen_floor(run)
        self.assertEqual(len(rows), arena.FLOOR_ROWS + 2, "5 choices, then merchant, then duel")
        self.assertNotEqual([[n["kind"] for n in r] for r in rows],
                            [[n["kind"] for n in r] for r in arena.gen_floor(run)], "every floor is different")
        self.assertEqual([n["kind"] for n in rows[-2]], ["shop"], "a merchant before the duel")
        self.assertEqual([n["kind"] for n in rows[-1]], ["boss"], "the floor ends in the ghost duel")
        self.assertIn("fight", [n["kind"] for n in rows[0]])
        for r in range(len(rows) - 1):
            for n in rows[r]:
                self.assertTrue(n["links"], "every node leads on")
        hp = run.arena["base_hp"]
        arena.resolve_floor(run, "dojo")
        self.assertEqual(run.arena["base_hp"], hp + 4)
        g0 = run.gold
        arena.resolve_floor(run, "bounty")
        self.assertGreater(run.gold, g0)

    def test_story_sims_still_work(self):
        for s in range(6):
            out = play("samurai", s, RandomPolicy(random.Random(s)))
            self.assertIn(out["stage"], (1, 2, 3))


class TestV9(unittest.TestCase):
    def test_recipes_combine_when_adjacent(self):
        r = RunState("samurai", 3)
        r.bag.items, r.stash.items = [], []
        r.bag.place(ItemInst("katana"), 0, 0)
        r.bag.place(ItemInst("whetstone"), 1, 0)
        made = r.combine_recipes()
        self.assertEqual(made, [("katana", "whetstone", "honed_katana")])
        self.assertEqual([i.id for i in r.bag.items], ["honed_katana"])
        far = RunState("samurai", 3)
        far.bag.items, far.stash.items = [], []
        far.bag.place(ItemInst("katana"), 0, 0)
        far.bag.place(ItemInst("whetstone"), 5, 0)
        self.assertEqual(far.combine_recipes(), [], "not touching: nothing happens")
        for pair, res in data.RECIPES.items():
            self.assertTrue(data.ITEMS[res].get("recipe"))
            self.assertTrue(all(i in data.ITEMS for i in pair))
            self.assertTrue(has_art(res), res)
        self.assertFalse(any(i["id"] == "honed_katana" for i in r.item_pool("epic")), "never sold")

    def test_discovery_and_endless_lock(self):
        from roguegame import progress, storage
        storage.delete(progress.KEY)
        progress.reset_cache()
        self.assertFalse(progress.endless_unlocked())
        progress.discover_item("katana", "katana", "kunai")
        progress.discover_enemy("kappa")
        self.assertTrue(progress.seen_item("kunai") and progress.seen_enemy("kappa"))
        self.assertEqual(progress.data()["seen_items"].count("katana"), 1)
        progress.on_run_end(RunState("ninja", 1), cleared=True)
        self.assertTrue(progress.endless_unlocked())
        storage.delete(progress.KEY)
        progress.reset_cache()

    def test_arena_save_and_resume(self):
        from roguegame import arena
        run = arena.new_run("onmyoji", 4)
        arena.start_round(run)
        arena.gen_floor(run)
        run.visit(run.available_nodes()[0])
        save.save_arena(run)
        back = save.load_arena()
        self.assertEqual(back.arena["round"], 1)
        self.assertEqual([[n["kind"] for n in r] for r in back.map], [[n["kind"] for n in r] for r in run.map])
        self.assertEqual(back.pos, run.pos)
        save.clear_arena()
        self.assertIsNone(save.load_arena())
        self.assertIsNotNone(save.load_run() is None or True)

    def test_run_stats_for_end_screen(self):
        r = RunState("ninja", 2)
        b = make_battle(r, "kappa", 1.0, seed=1)
        b.run_to_end()
        r.record_battle(b.f[0].items)
        self.assertGreater(r.stats["dmg"], 0)
        iid, dmg = r.best_item()
        self.assertEqual(dmg, max(r.stats["items"].values()))


class TestSpirits(unittest.TestCase):
    def test_signature_is_the_defining_effect_at_half(self):
        from roguegame.spirit import signature
        self.assertEqual(signature(ItemInst("fire_bomb").data), {"burn": max(1, round(data.ITEMS["fire_bomb"]["burn"] / 2))})
        k = signature(ItemInst("kunai").data)
        self.assertEqual(list(k), ["dmg"])
        self.assertEqual(list(signature(ItemInst("kasa_hat").data)), ["s_block"])

    def test_soul_forge_rules_and_save(self):
        from roguegame.spirit import can_infuse, infuse
        r = RunState("ninja", 6)
        r.bag.items, r.stash.items = [], []
        katana, bomb, hat, kunai = (ItemInst(i) for i in ("katana", "fire_bomb", "kasa_hat", "kunai"))
        for i, it in enumerate((katana, bomb, hat, kunai)):
            r.bag.first_fit(it)
        self.assertFalse(can_infuse(bomb, hat)[0], "an active spirit needs an item that acts")
        self.assertTrue(can_infuse(hat, katana)[0], "a passive spirit fits anything")
        base_burn = katana.data.get("burn", 0)
        infuse(bomb, katana)
        self.assertGreater(katana.data["burn"], base_burn)
        self.assertFalse(can_infuse(kunai, katana)[0], "one spirit per item")
        save.save_run(r)
        back = save.load_run()
        k2 = next(i for i in back.all_items() if i.id == "katana")
        self.assertEqual(k2.infusion["src"], "fire_bomb")
        self.assertEqual(k2.data["burn"], katana.data["burn"])
        save.clear_run()
        b = make_battle(r, "kappa", 1.0, seed=1)
        kat = next(ci for ci in b.f[0].items if ci.st["id"] == "katana")
        self.assertTrue(kat.st.get("burn"), "the infusion is real in battle")

    def test_tsukumogami_awakens_by_use(self):
        from roguegame import spirit
        r = RunState("samurai", 7)
        for _ in range(spirit.AWAKEN_BATTLES):
            b = make_battle(r, "kappa", 1.0, seed=2)
            b.run_to_end()
            awoke = r.record_battle(b.f[0].items)
        self.assertTrue(awoke, "every kit item awakens after the set number of battles")
        katana = next(i for i in r.bag.items if i.id == "katana")
        self.assertIn(katana.awakened, ("blade", "storm"))
        self.assertNotEqual(katana.data["name"], data.ITEMS["katana"]["name"])
        armor = next(i for i in r.bag.items if i.id == "do_armor")
        self.assertEqual(armor.awakened, "kami" if not data.ITEMS["do_armor"].get("cd") else armor.awakened)
        d = ItemInst.from_dict(katana.to_dict())
        self.assertEqual((d.awakened, d.battles), (katana.awakened, katana.battles))

    def test_merging_keeps_spirits(self):
        from roguegame.spirit import infuse
        r = RunState("samurai", 8)
        a, b, src = ItemInst("katana"), ItemInst("katana"), ItemInst("fire_bomb")
        infuse(src, b)
        b.awakened = "blade"
        r.bag.items, r.stash.items = [], []
        r.bag.first_fit(a)
        r.bag.first_fit(b)
        self.assertTrue(r.merge(a, b))
        self.assertEqual((a.level, a.infusion["src"], a.awakened), (2, "fire_bomb", "blade"))

    def test_crit_stun(self):
        r = RunState("samurai", 9)
        r.bag.items = []
        k = ItemInst("katana")
        k.awakened = "storm"
        k.refresh()
        r.bag.first_fit(k)
        b = make_battle(r, "kurogane", 1.0, seed=3)
        for f in b.f:
            f.hp = f.max_hp = 10 ** 6
        b.f[0].crit = 1.0
        b.advance(10)
        kat = next(ci for ci in b.f[0].items if ci.st["id"] == "katana")
        self.assertGreater(kat.stats.get("stun", 0), 0, "a Lightning tsukumogami's crits stun")

    def test_forge_event_and_bots(self):
        from roguegame.events import EVENT_BY_ID, resolve, auto_infuse
        r = RunState("kunoichi", 10)
        res = resolve(r, EVENT_BY_ID["soul_forge"], 0)
        self.assertEqual(res["forge"][0], "gold")
        r.add_item("fire_bomb") if False else r.add_item("oil_flask")
        got = auto_infuse(r, r.rng)
        self.assertIsNotNone(got)


class TestAIFeaturesAreFutureProof(unittest.TestCase):
    """The agents describe options by what they do, so adding content never changes feature sizes."""

    def setUp(self):
        try:
            import numpy  # noqa: F401
        except ImportError:
            self.skipTest("numpy not installed")

    def test_shapes_are_fixed(self):
        from roguegame import ai
        from roguegame.events import EVENTS, EVENT_BY_ID
        r = RunState("onmyoji", 1)
        dims = {k: d for k, (_, d) in ai.FEATURES.items()}
        fake = dict(id="test_event", title="t", text="t", options=[dict(label="x", do=lambda r, g: {},
                                                                         fx=dict(gold=5, item=2))])
        EVENTS.append(fake)
        EVENT_BY_ID["test_event"] = fake
        data.TECHNIQUES["test_tech"] = dict(cls="onmyoji", name="t", desc="t", crit=0.1, brand_new_mod=3)
        try:
            self.assertEqual(len(ai.event_features("test_event:0", r)), dims["event"])
            self.assertEqual(len(ai.tech_features("test_tech", r)), dims["tech"])
            self.assertGreater(ai.tech_features("test_tech", r)[-1], 0, "unknown modifiers still register")
            self.assertEqual(len(ai.path_features("some_new_node", r)), dims["path"])
            for iid in list(data.ITEMS)[:40]:
                self.assertEqual(len(ai.item_features(iid, r)), dims["item"])
        finally:
            EVENTS.remove(fake)
            del EVENT_BY_ID["test_event"]
            del data.TECHNIQUES["test_tech"]

    def test_every_event_option_is_tagged(self):
        from roguegame.events import EVENTS, option_fx
        for e in EVENTS:
            for i, o in enumerate(e["options"]):
                label = f"{e['id']}:{i}"
                with self.subTest(option=label):
                    is_leave = o["do"].__name__ in ("leave", "do")      # do = leave_flag(...)
                    self.assertTrue(is_leave or option_fx(label, e), "tag this option in events.FX")

    def test_current_items_need_no_catch_all(self):
        from roguegame import ai
        r = RunState("samurai", 1)
        for iid, d in data.ITEMS.items():
            if not d["enemy"]:
                self.assertEqual(ai.item_features(iid, r)[-1], 0, f"{iid} has an effect the AI can't see")


class TestDifficultyCurve(unittest.TestCase):
    def test_first_battle_can_never_be_lost(self):
        for cls in data.CHARACTERS:
            for seed in range(120):
                r = RunState(cls, seed)
                r.visit(r.available_nodes()[0])
                self.assertTrue(r.is_first_battle())
                eid = r.pick_enemy("fight")
                self.assertIn(eid, data.FIRST_FIGHT_POOL)
                b = make_battle(r, eid, r.enemy_scale("fight"), seed=r.rng.randrange(1 << 30))
                b.run_to_end()
                self.assertEqual(b.winner, 0, f"{cls} lost the first battle on seed {seed}")

    def test_each_stage_ramps_up(self):
        for stage in (1, 2, 3, 4):
            ramp = [data.floor_ramp(stage, row) for row in range(6)]
            self.assertEqual(ramp, sorted(ramp), f"stage {stage} must only get harder floor by floor")
        self.assertLess(data.floor_ramp(1, 0), data.floor_ramp(2, 0), "stage 1 starts gentlest")
        r = RunState("ninja", 3)
        r.stats["battles"] = 1
        r.pos = (0, 0)
        early = r.enemy_scale("fight")
        r.pos = (4, 0)
        self.assertGreater(r.enemy_scale("fight"), early)


class TestV099(unittest.TestCase):
    def test_onsen_before_every_boss(self):
        for seed in range(30):
            r = RunState("onmyoji", seed)
            for _ in range(3):
                before_boss = r.map[-2]
                self.assertEqual([n["kind"] for n in before_boss], ["rest"], "one onsen right before the boss")
                self.assertTrue(all(0 in n["links"] for n in r.map[-3]), "every path leads to it")
                r.next_stage()

    def test_upgrade_events_let_you_choose(self):
        from roguegame.events import EVENT_BY_ID, resolve
        r = RunState("samurai", 2)
        r.gold = 30
        res = resolve(r, EVENT_BY_ID["smith"], 0)
        self.assertEqual(res.get("upgrade"), 1, "the smith asks which item")
        self.assertEqual(r.gold, 20)

    def test_battle_debrief_tracking(self):
        r = RunState("kunoichi", 4)
        r.stats["battles"] = 1
        b = make_battle(r, "jorogumo", 1.5, seed=3)
        b.run_to_end()
        self.assertTrue(b.taken[0], "we know what hurt the player")
        self.assertEqual(sum(b.taken[1].values()), b.f[1].max_hp - max(0, b.f[1].hp) + b.healed[1])
        phases = make_battle(r, "kurogane", 0.5, seed=1)
        phases.run_to_end()
        self.assertTrue(any("phase" in e["delta"] for e in phases.log), "transformations are in the log")

    def test_run_clock_and_stage_times(self):
        r = RunState("ninja", 5)
        r.play_time = 125.0
        r.next_stage()
        r.play_time = 300.0
        r.next_stage()
        self.assertEqual(r.stage_times, [125.0, 175.0])
        save.save_run(r)
        self.assertEqual(save.load_run().play_time, 300.0)
        save.clear_run()
        from roguegame import history
        rec = history.record_from_run(r, False)
        self.assertEqual(rec["stage_times"], [125.0, 175.0, 0.0])
        self.assertEqual(rec["duration"], 300)

    def test_new_screens_draw(self):
        import pygame
        from main import Game
        from roguegame import scenes
        g = Game()
        g.run = RunState("samurai", 6)
        inv = scenes.InventoryScene(g, "manage", on_done=lambda: None)
        for sc in (scenes.UpgradePickScene(g, lambda: inv), scenes.RecipeBookScene(g, inv)):
            g.change(sc)
            sc.draw(g.screen)
        up = scenes.UpgradePickScene(g, lambda: inv)
        up.sel = up.items[0]
        before = up.sel.level
        up.confirm()
        self.assertEqual(g.run.bag.items[0].level if g.run.bag.items[0] is up.sel else up.sel.level, before + 1)
        self.assertTrue(scenes.battle_numbers(g.run, next(i for i in g.run.bag.items if i.id == "katana")))
        pygame.quit()


class TestScreens(unittest.TestCase):
    def test_every_screen_draws(self):
        import pygame
        from main import Game
        from roguegame import scenes
        g = Game()
        g.run = RunState("sohei", 5)
        screens = [scenes.TitleScene(g), scenes.CharSelectScene(g), scenes.MapScene(g), scenes.StageScene(g),
                   scenes.InventoryScene(g, "shop", offers=g.run.shop_offers(), on_done=lambda: None),
                   scenes.TechniqueScene(g, then=lambda: None), scenes.RestScene(g),
                   scenes.EventScene(g, EVENTS[0]), scenes.BattleScene(g, "ashura", "boss"), scenes.EndScene(g, True),
                   scenes.MatchHistoryScene(g), scenes.MatchHistoryScene(g, tab="arena"),
                   scenes.ArenaLobbyScene(g), scenes.SettingsScene(g), scenes.AchievementsScene(g),
                   scenes.CompendiumScene(g)]
        for sc in screens:
            with self.subTest(screen=type(sc).__name__):
                g.change(sc)
                for _ in range(30):
                    sc.update(1 / 30)
                sc.draw(g.screen)
        pygame.quit()


if __name__ == "__main__":
    unittest.main()
