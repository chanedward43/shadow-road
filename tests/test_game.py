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
        self.assertEqual(b.f[1].curse, 3)
        self.assertEqual(b._cursed(b.f[1], 100), 88)
        b.run_to_end()
        self.assertGreater(self.kinds(b).get("hex", 0), 0)

    def test_sohei_ki_and_counter(self):
        b = self.fight(self.kit("sohei", ["temple_bell"]))
        k = self.kinds(b)
        self.assertGreater(k.get("counter", 0), 0)
        self.assertGreater(k.get("kiburst", 0), 0)

    def test_per_tag_scaling(self):
        r = self.kit("samurai", ["daisho", "wakizashi", "tanto"])
        st = effective_stats(r.bag, "samurai")
        daisho = next(s for s in st.values() if s["id"] == "daisho")
        base = data.ITEMS["daisho"]["dmg"]
        self.assertEqual(daisho["dmg"][0], base[0] + 3)   # katana + wakizashi + tanto

    def test_boss_phases_trigger(self):
        r = RunState("samurai", 1)
        r.max_hp = r.hp = 5000                          # survive long enough to see every phase
        b = self.fight(r, "orochi")
        self.assertEqual(self.kinds(b).get("phase", 0), 2)


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
