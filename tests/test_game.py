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
            self.assertEqual(elite[0][1], 2, "elite class item is level 2 in stage 3")
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
                techs = [t for t, d in data.TECHNIQUES.items() if d["cls"] == cid]
                self.assertEqual(len(techs), 6)
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
        r.auto_merge()                       # level 3 is the cap: nothing merges further
        self.assertEqual(sorted(i.level for i in r.all_items() if i.id == "katana"), [3, 3])
        st = data.level_stats(data.ITEMS["katana"], 3)
        self.assertGreater(st["dmg"][0], data.ITEMS["katana"]["dmg"][0])

    def test_summons_fight(self):
        b = self.fight(self.kit("onmyoji", ["fox_shikigami"]))
        self.assertGreater(self.kinds(b).get("summon", 0), 3)
        self.assertGreaterEqual(len(b.f[0].summons), 1)

    def test_curse_reduces_damage_and_hex_scales(self):
        r = self.kit("onmyoji", ["onmyo_compass", "hex_scroll"])
        b = make_battle(r, "kurogane", 1.0, seed=0)
        self.assertEqual(b.f[1].curse, 4)                 # 3 from the Compass + 1 from Shikigami Pact
        self.assertEqual(b._cursed(b.f[1], 100), 80)      # 4 stacks x 5% = 20% less damage
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
                   scenes.EventScene(g, EVENTS[0]), scenes.BattleScene(g, "ashura", "boss"), scenes.EndScene(g, True)]
        for sc in screens:
            with self.subTest(screen=type(sc).__name__):
                g.change(sc)
                for _ in range(30):
                    sc.update(1 / 30)
                sc.draw(g.screen)
        pygame.quit()


if __name__ == "__main__":
    unittest.main()
