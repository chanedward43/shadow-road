"""Make item sprites: our own hand-drawn 16x16 pixel art (tools/sprite_templates.py) for Japanese gear, and
weapons cut from the CC0 "16x16 Weapon RPG Icons" sheets in had/.

    python tools/make_sprites.py            # writes assets/art/<item>.png for every item listed below
    python tools/make_sprites.py --sheet    # also writes a contact sheet to check them side by side

Each custom item = a template (its shape) + its own colours A, B, C (a, b, c are darker shades), so two
items of the same kind (two bells, two gourds) still look different, and different things get different shapes.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from sprite_templates import T  # noqa: E402

FIXED = {"k": (26, 18, 24), "w": (255, 248, 230), "p": (238, 228, 198), "y": (232, 188, 64),
         "N": (96, 60, 36), "s": (200, 206, 214), "S": (110, 116, 130)}

# colours
RED, CRIMSON, VERMIL, ORANGE = (200, 52, 48), (150, 28, 40), (226, 84, 44), (236, 130, 40)
GOLD, YELLOW, CREAM, WHITE = (226, 182, 60), (240, 214, 80), (236, 222, 186), (232, 232, 236)
GREEN, JADE, MOSS, LIME = (78, 150, 70), (60, 170, 130), (104, 124, 56), (150, 200, 70)
TEAL, SKY, BLUE, INDIGO = (60, 150, 160), (120, 186, 230), (64, 104, 190), (52, 60, 120)
PURPLE, VIOLET, PINK, SAKURA = (120, 70, 160), (170, 110, 210), (220, 110, 160), (244, 170, 196)
BROWN, WOOD, TAN, STRAW = (120, 76, 44), (156, 104, 60), (196, 156, 104), (214, 186, 110)
BLACK, CHARCOAL, GREY, SILVER = (40, 36, 44), (66, 62, 74), (128, 128, 136), (186, 190, 200)
IRON, BRONZE, ICE, BONE = (96, 100, 112), (176, 118, 60), (186, 226, 240), (226, 214, 180)
FLAME, EMBER = (250, 150, 40), (240, 90, 30)

# item id -> (template, A, B, C, extra pixels [(x, y, colour)])
CUSTOM = {
    # ---- food
    "alms_rice": ("bowl", BROWN, BLACK, WHITE),
    "bitter_tea": ("cup", TAN, BROWN, (110, 80, 50)),
    "matcha_tea": ("cup", CREAM, GREEN, LIME),
    "gama_oil": ("jar", MOSS, BROWN, YELLOW),
    "hag_cauldron": ("cauldron", CHARCOAL, IRON, LIME),
    "kami_offering": ("offering", WHITE, WOOD, RED),
    "orochi_sake": ("tokkuri", WHITE, BLUE, INDIGO, [(7, 10, INDIGO), (8, 11, INDIGO)]),
    "pilgrim_gourd": ("gourd", TAN, WOOD, RED),
    "spring_gourd": ("gourd", SKY, WOOD, BLUE),
    "shuten_gourd": ("gourd", CRIMSON, BLACK, GOLD),
    "sake_cask": ("cask", WOOD, BLACK, RED),
    # ---- charms
    "ashura_drum": ("drum", RED, GOLD, BLACK),
    "ashura_mask": ("mask", RED, BLACK, GOLD),
    "bandit_crown": ("crown", BRONZE, RED, GREEN),
    "judgement_crown": ("crown", GOLD, PURPLE, RED),
    "divining_sticks": ("sticks", TAN, (140, 40, 40), RED),
    "dojo_nobori": ("banner", WHITE, INDIGO, BLACK),
    "hachiman_banner": ("banner", RED, GOLD, WHITE),
    "dragon_bell": ("bell", JADE, GOLD, (40, 110, 90)),
    "hiei_bell": ("bell", BRONZE, CHARCOAL, (120, 80, 40)),
    "omen_bell": ("handbell", PURPLE, BLACK, RED),
    "faceless_mask": ("egg", WHITE, WHITE, WHITE, [(6, 7, (210, 210, 214)), (9, 7, (210, 210, 214))]),
    "fox_bride_mirror": ("mirror", (250, 230, 170), GOLD, RED),
    "moon_mirror": ("moon_mirror", SILVER, INDIGO, SILVER),
    "yinyang_mirror": ("yinyang", WHITE, BLACK, BLACK),
    "hatamoto_seal": ("seal", RED, GOLD, RED),
    "kenshi_oath": ("seal", INDIGO, WOOD, CRIMSON),
    "hawk_charm": ("omamori", BROWN, GOLD, YELLOW),
    "kagero_charm": ("omamori", ORANGE, SKY, (250, 200, 120)),
    "inugami_talisman": ("omamori", WHITE, TAN, RED),
    "kekkai_ward": ("omamori", BLUE, SKY, WHITE),
    "iron_mala": ("beads", IRON, IRON, BLACK),
    "juzu_beads": ("beads", WOOD, WOOD, VIOLET),
    "needle_bracelet": ("beads", SILVER, SILVER, (150, 220, 90)),
    "kiai_shout": ("headband", WHITE, WHITE, RED),
    "maneki_neko": ("maneki", WHITE, WHITE, RED),
    "mokugyo": ("fish_drum", RED, RED, GOLD),
    "onryo_hair": ("hair", BLACK, BLACK, WHITE),
    "purify_ofuda": ("ofuda", WHITE, WHITE, RED),
    "raijin_talisman": ("ofuda", YELLOW, YELLOW, BLUE),
    "seimei_talisman": ("ofuda", INDIGO, INDIGO, BLUE),
    "katon_seal": ("ofuda", EMBER, EMBER, EMBER),
    "seimei_fan": ("fan", WHITE, BLACK, INDIGO),
    "spider_sash": ("sash", WHITE, SILVER, PURPLE),
    "spirit_lantern": ("lantern", (150, 220, 230), BLACK, BLUE),
    "tamamo_tail": ("tail", (250, 210, 120), WHITE, WHITE),
    "tortoise_comb": ("comb", (176, 110, 50), BROWN, (90, 50, 30)),
    "yuki_comb": ("comb", ICE, WHITE, BLUE),
    "umibozu_pearl": ("pearl", (130, 210, 200), (60, 90, 120), BLUE),
    "wisteria_incense": ("incense", VIOLET, BRONZE, (200, 180, 230)),
    # ---- armor
    "assassin_obi": ("sash", BLACK, CRIMSON, RED),
    "bakezori_sandals": ("sandal", STRAW, STRAW, RED, [(7, 6, WHITE), (8, 6, BLACK)]),
    "waraji": ("sandal", STRAW, STRAW, BROWN),
    "bamboo_shield": ("shield", (150, 190, 90), BROWN, BROWN),
    "frost_mirror": ("mirror", ICE, SILVER, SKY),
    "gaki_bowl": ("cracked_bowl", (90, 70, 60), BLACK, BLACK),
    "jika_tabi": ("tabi", CHARCOAL, BLACK, GREY),
    "silent_tabi": ("tabi", INDIGO, BLACK, PURPLE),
    "jinbaori": ("robe", CRIMSON, GOLD, GOLD),
    "kesa_robe": ("robe", ORANGE, BROWN, GOLD),
    "serpent_robe": ("robe", JADE, MOSS, (40, 100, 70)),
    "shinobi_garb": ("robe", CHARCOAL, BLACK, BLACK),
    "kabuto_set": ("kabuto", RED, BLACK, GOLD),
    "tetsu_kabuto": ("kabuto", IRON, CHARCOAL, SILVER),
    "kote_bracers": ("bracer", BLACK, RED, GOLD),
    "nio_bracers": ("bracer", BRONZE, (120, 70, 30), RED),
    "spiked_kote": ("spiked_bracer", IRON, CHARCOAL, BLACK),
    "lacquered_sode": ("sode", RED, BLACK, GOLD),
    "menpo": ("menpo", IRON, BLACK, WHITE),
    "mino_cloak": ("cloak", STRAW, STRAW, BROWN),
    "nurikabe_brick": ("brick", GREY, GREY, GREY),
    "o_yoroi": ("do", CRIMSON, BLACK, GOLD),
    "tatami_do": ("do", WOOD, BROWN, INDIGO),
    "parasol": ("parasol", SAKURA, PINK, RED),
    "stone_lantern": ("stone_lantern", GREY, GREY, FLAME),
    "war_hakama": ("hakama", INDIGO, INDIGO, WHITE),
    # ---- poison
    "black_lotus": ("lotus", (70, 40, 90), BLACK, BLACK),
    "hemlock_vial": ("vial", WHITE, WHITE, LIME),
    "toad_venom": ("vial", (200, 170, 120), WHITE, ORANGE),
    "killing_stone": ("stone", (110, 70, 130), PURPLE, LIME),
    "queen_of_poisons": ("jar", PURPLE, GOLD, LIME),
    "venom_censer": ("cauldron", BRONZE, (110, 70, 30), LIME),
    # ---- scrolls & books
    "breathing_scroll": ("scroll", CREAM, GREEN, GREEN),
    "iaido_scroll": ("scroll", CREAM, INDIGO, BLACK),
    "kage_scroll": ("scroll", (90, 80, 110), BLACK, VIOLET),
    "patience_scroll": ("scroll", CREAM, WOOD, BROWN),
    "thunder_sutra": ("scroll", YELLOW, BLUE, BLUE),
    "phoenix_scroll": ("scroll", (250, 200, 140), RED, EMBER),
    "dragon_flame": ("scroll", (250, 220, 170), GOLD, RED),
    "star_chart": ("scroll", INDIGO, BLACK, YELLOW),
    "shikigami_contract": ("scroll", WHITE, BLACK, RED),
    "diamond_sutra": ("book", SKY, WHITE, BLUE),
    "sutra_scroll": ("book", GOLD, BROWN, BLACK),
    "enma_ledger": ("book", CRIMSON, BLACK, RED),
    "treasure_map": ("scroll", TAN, BROWN, RED),
    # ---- tools
    "climbing_rope": ("rope", TAN, TAN, BROWN),
    "silk_spool": ("rope", WHITE, WHITE, PURPLE),
    "gama_pipe": ("pipe", BRONZE, BROWN, BROWN),
    "kiseru": ("pipe", SILVER, GREEN, GREEN),
    "herb_satchel": ("pouch", GREEN, BROWN, TAN),
    "tetsubishi": ("pouch", GREY, BLACK, IRON),
    "shadow_bandolier": ("bandolier", GREY, PURPLE, SILVER),
    "kunai_bandolier": ("bandolier", BROWN, BROWN, SILVER),
    "ink_stone": ("inkstone", CHARCOAL, BLACK, BLACK),
    "inro": ("inro", RED, GOLD, GOLD),
    "iron_tsuba": ("tsuba", IRON, IRON, GOLD),
    "ittan_cloth": ("cloth", WHITE, WHITE, WHITE),
    "mizugumo": ("float", WOOD, WOOD, BLUE),
    "tanuki_leaf": ("leaf", GREEN, GREEN, BROWN),
    "torinoko": ("egg", CHARCOAL, CHARCOAL, GREY),
    # ---- curse
    "curse_nail": ("nail", IRON, IRON, RED),
    "ox_hour_nails": ("nails_doll", IRON, STRAW, WHITE),
    "five_element_wheel": ("wheel", WOOD, GOLD, RED),
    "yomi_mirror": ("mirror", (70, 40, 70), BLACK, CRIMSON),
    # ---- fire
    "dojoji_bell": ("bell", CRIMSON, EMBER, ORANGE),
    "fire_quiver": ("quiver", BROWN, BLACK, FLAME),
    "fire_rat": ("bomb", (150, 90, 60), RED, FLAME),
    "uzumaki_bomb": ("bomb", BLACK, RED, FLAME),
    "horoku_hiya": ("rocket", RED, GOLD, FLAME),
    "katon_brazier": ("cauldron", BLACK, EMBER, FLAME),
    "serpent_fan": ("fan", EMBER, BLACK, GOLD),
    "kasha_wheel": ("wheel", BLACK, EMBER, FLAME),
    # ---- summons
    "hitogata": ("doll", WHITE, WHITE, RED),
    "tengu_shikigami": ("doll", RED, RED, BLACK),
    "serpent_shikigami": ("doll", (180, 220, 160), GREEN, GREEN),
    # ---- custom weapons
    "bo_shuriken": ("needles", SILVER, SILVER, BLACK),
    "senbon": ("needles", WHITE, WHITE, RED),
    "thousand_needles": ("needles", GOLD, GOLD, BLACK),
    "widow_needle": ("needles", VIOLET, VIOLET, BLACK),
    "chain_of_stars": ("shuriken", SILVER, SILVER, BLACK),
    "star_storm": ("shuriken", GOLD, GOLD, RED),
    "glutton_hashi": ("hashi", RED, RED, GOLD),
    "jade_fan": ("fan", JADE, BLACK, GOLD),
    "kurogane_fan": ("fan", BLACK, GOLD, GOLD),
    "whisper_fan": ("fan", VIOLET, BLACK, WHITE),
    "tengu_feather_fan": ("feather_fan", WHITE, BROWN, BLACK),
    "tengu_king_fan": ("feather_fan", CRIMSON, GOLD, BLACK),
    "war_tessen": ("closed_fan", IRON, BLACK, RED),
    "long_neck_comb": ("comb", BLACK, BLACK, RED),
    "mirror_hairpin": ("hairpin", SILVER, SKY, WHITE),
    "serpent_hairpin": ("hairpin", GOLD, LIME, GREEN),
    "red_scissors": ("scissors", SILVER, RED, BLACK),
    "oni_king_horn": ("horn", BONE, RED, BLACK),
    "raiju_fang": ("fang", BONE, BONE, YELLOW),
    "ember_kunai": ("kunai", (230, 150, 110), FLAME, EMBER),
    "sakura_kunai": ("kunai", SAKURA, PINK, PINK),
}

# scrolls and ofuda of different kinds carry their own emblem, not just their own colours
EMBLEM_OF = {"breathing_scroll": "wave", "iaido_scroll": "slash", "kage_scroll": "eye", "patience_scroll": "circle",
             "thunder_sutra": "bolt", "phoenix_scroll": "flame", "dragon_flame": "swirl", "star_chart": "star",
             "shikigami_contract": "kanji", "treasure_map": "xmark",
             "purify_ofuda": "circle", "seimei_talisman": "star", "katon_seal": "flame", "raijin_talisman": "bolt"}

# weapons from the CC0 sheets: item id -> (material sheet, column, row) on the 16x16 grid
SHEET_DIR = os.path.join("had", "16x16_weapons_rpg_icons", "16x16 Weapons RPG Icons")
SHEET = {
    "uchigatana": ("steel", 10, 0), "honed_katana": ("steel", 11, 2), "cursed_katana": ("iron", 11, 7),
    "masamune": ("gold", 10, 1), "muramasa": ("iron", 13, 2), "ronin_blade": ("bronze", 10, 3),
    "ryumon_katana": ("gold", 11, 5), "ninjato": ("iron", 9, 1), "honour_tachi": ("steel", 12, 1),
    "kiri_oroshi": ("steel", 12, 6), "echo_blade": ("iron", 12, 9), "kurikara_sword": ("gold", 6, 4),
    "orochi_shard": ("bronze", 7, 2), "warlord_blade": ("iron", 8, 1), "daisho": ("steel", 11, 8),
    "soryu_blades": ("gold", 12, 3),
    "bandit_shiv": ("iron", 6, 10), "kaiken": ("steel", 6, 12), "kogatana": ("steel", 7, 10),
    "lone_tanto": ("iron", 6, 16), "silk_tanto": ("gold", 6, 14), "yoroi_doshi": ("steel", 7, 18),
    "temple_naginata": ("steel", 17, 2), "warrior_monk": ("gold", 17, 4), "sode_garami": ("iron", 22, 2),
    "temple_bo": ("bronze", 18, 0), "vajra_staff": ("gold", 19, 5), "kongo_staff": ("iron", 19, 7),
    "bokken": ("bronze", 9, 0), "wanyudo_spoke": ("bronze", 18, 6),
    "drunken_kanabo": ("iron", 3, 14), "tetsubo": ("steel", 3, 16), "enma_gavel": ("gold", 22, 12),
    "thieves_hook": ("iron", 16, 11), "wind_sickle": ("steel", 13, 12),
}


EMBLEMS = {
    "flame": ["..x..", ".xx..", ".xxx.", "xxxxx", ".xxx."],
    "bolt": ["..xx.", ".xx..", "xxxx.", "..xx.", ".xx.."],
    "star": ["..x..", ".xxx.", "xxxxx", ".x.x.", "x...x"],
    "wave": [".....", ".x.x.", "x.x.x", ".....", "xxxxx"],
    "eye": [".xxx.", "x.x.x", "xxxxx", ".xxx.", "....."],
    "swirl": ["xxxx.", "...x.", ".x.x.", ".xxx.", "....."],
    "kanji": ["..x..", "xxxxx", "..x..", ".x.x.", "x...x"],
    "circle": [".xxx.", "x...x", "x...x", "x...x", ".xxx."],
    "slash": ["....x", "...x.", "..x..", ".x...", "x...."],
    "xmark": ["x...x", ".x.x.", "..x..", ".x.x.", "x...x"],
}
# where an emblem goes on each template: (clear rect x, y, w, h), emblem top-left
EMBLEM_AT = {"scroll": ((5, 4, 7, 7), (6, 5)), "ofuda": ((5, 4, 6, 8), (5, 5))}


def emblem(template, name, col, bg):
    (cx, cy, cw, ch), (ex, ey) = EMBLEM_AT[template]
    px = [(x, y, bg) for x in range(cx, cx + cw) for y in range(cy, cy + ch)]
    for dy, row in enumerate(EMBLEMS[name]):
        px += [(ex + dx, ey + dy, col) for dx, v in enumerate(row) if v == "x"]
    return px


def shade(c, k=0.68):
    return tuple(int(v * k) for v in c)


def render(name, a, b, c, extra=()):
    import pygame
    rows = [r for r in T[name].strip("\n").split("\n")]
    assert len(rows) == 16, (name, len(rows))
    pal = dict(FIXED, A=a, a=shade(a), B=b, b=shade(b), C=c, c=shade(c))
    img = pygame.Surface((16, 16), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        assert len(row) == 16, (name, y, row)
        for x, ch in enumerate(row):
            if ch != ".":
                img.set_at((x, y), pal[ch])
    for x, y, col in extra:
        img.set_at((x, y), col)
    return img


def cut(material, col, row):
    import pygame
    sheet = pygame.image.load(os.path.join(ROOT, SHEET_DIR, f"{material}-weapons.png")).convert_alpha()
    return sheet.subsurface((col * 16, row * 16, 16, 16)).copy()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sheet", nargs="?", const="sprites_contact.png", default=None, help="contact sheet path")
    args = ap.parse_args()
    import pygame
    pygame.init()
    pygame.display.set_mode((1, 1))
    art_dir = os.path.join(ROOT, "assets", "art")
    map_path = os.path.join(ROOT, "assets", "art_map.json")
    art_map = json.load(open(map_path, encoding="utf-8"))
    made = {}
    for iid, spec in CUSTOM.items():
        name, a, b, c = spec[:4]
        extra = list(spec[4]) if len(spec) > 4 else []
        if iid in EMBLEM_OF:
            paper = FIXED["p"] if name == "ofuda" else a
            extra = emblem(name, EMBLEM_OF[iid], c, paper) + extra
        made[iid] = (render(name, a, b, c, extra), f"custom:{name} ({iid} colours)")
    for iid, (mat, col, row) in SHEET.items():
        made[iid] = (cut(mat, col, row), f"{SHEET_DIR}/{mat}-weapons.png#{col * 16},{row * 16},16,16")
    for iid, (img, src) in made.items():
        r = img.get_bounding_rect()
        pygame.image.save(img.subsurface(r).copy(), os.path.join(art_dir, f"{iid}.png"))
        art_map[iid] = src
    json.dump(art_map, open(map_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"wrote {len(made)} sprites ({len(CUSTOM)} hand-drawn, {len(SHEET)} from the weapon sheets)")
    if args.sheet is not None:
        from roguegame.data import ITEMS
        f = pygame.font.Font(None, 15)
        ids = sorted(made, key=lambda i: (ITEMS[i]["tags"][0], i))
        cols, cw, ch = 12, 104, 86
        s = pygame.Surface((cols * cw, ((len(ids) + cols - 1) // cols) * ch))
        s.fill((44, 40, 54))
        for k, iid in enumerate(ids):
            x, y = (k % cols) * cw, (k // cols) * ch
            img = made[iid][0]
            s.blit(pygame.transform.scale(img, (64, 64)), (x + 20, y + 2))
            s.blit(f.render(iid[:15], True, (240, 230, 200)), (x + 4, y + 70))
        out = sys.argv[sys.argv.index("--sheet") + 1] if len(sys.argv) > sys.argv.index("--sheet") + 1 \
            else os.path.join(ROOT, "sprites_contact.png")
        pygame.image.save(s, out)
        print("contact sheet:", out)


if __name__ == "__main__":
    main()
