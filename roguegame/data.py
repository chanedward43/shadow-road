"""All game content lives here: items, classes, techniques, enemies, stages.

SHADOW ROAD: a samurai, ninja or kunoichi travels the roads of old Japan, packing
their kit, growing stronger, and cutting down the villains of each region.

Tweak numbers here to balance the game. Nothing in this file imports pygame,
so the same data can later be used by an online server.
"""

# ---------------------------------------------------------------- shapes
S1 = [(0, 0)]
V2 = [(0, 0), (0, 1)]
H2 = [(0, 0), (1, 0)]
V3 = [(0, 0), (0, 1), (0, 2)]
H3 = [(0, 0), (1, 0), (2, 0)]
V4 = [(0, 0), (0, 1), (0, 2), (0, 3)]
SQ = [(0, 0), (1, 0), (0, 1), (1, 1)]
L3 = [(0, 0), (0, 1), (1, 1)]
L4 = [(0, 0), (0, 1), (0, 2), (1, 2)]
J4 = [(0, 0), (1, 0), (1, 1), (1, 2)]
T4 = [(0, 0), (1, 0), (2, 0), (1, 1)]
R23 = [(x, y) for x in range(2) for y in range(3)]
CROSS = [(1, 0), (0, 1), (1, 1), (2, 1), (1, 2)]

RARITIES = ["common", "rare", "epic", "legendary"]
DEFAULT_PRICE = {"common": 3, "rare": 6, "epic": 11, "legendary": 17}

# Tags: weapon, armor, food, poison, fire, charm, tool, scroll (+ enemy)
ITEMS = {}


def item(iid, name, shape, rarity, tags, cls=None, price=None, enemy=False, **stats):
    """Register an item.

    Active stats (need cd = cooldown in seconds):
        dmg=(lo, hi), hits (strikes per trigger), block, heal, poison, burn, regen,
        lifesteal (0-1), crit (0-1), stun (seconds the enemy's items freeze),
        dodge (charges: each one fully evades the next enemy hit),
        sunder (0-1: destroys that share of the enemy's Block)
    Passive start-of-battle stats:
        s_block, s_hp, s_regen, s_thorns, s_crit, s_evade (chance to evade hits)
    Aura (buffs ADJACENT items, only stats they already have):
        aura=dict(tags=("weapon",) or None for any, dmg, speed, block, poison, burn, heal, crit)
    """
    ITEMS[iid] = dict(
        id=iid, name=name, shape=shape, rarity=rarity, tags=tuple(tags), cls=cls,
        price=price if price is not None else DEFAULT_PRICE[rarity], enemy=enemy, **stats
    )


# ================================================================ shared gear
item("tanto", "Tantō", V2, "common", ["weapon"], cd=1.3, dmg=(2, 4))
item("bo_staff", "Bō Staff", V3, "common", ["weapon"], cd=2.2, dmg=(3, 5), stun=0.3, price=4)
item("onigiri", "Onigiri", S1, "common", ["food"], cd=4.5, heal=4)
item("kasa_hat", "Kasa Hat", H2, "common", ["armor"], s_block=8)
item("whetstone", "Whetstone", S1, "common", ["tool"], aura=dict(tags=("weapon",), dmg=1))
item("ofuda", "Ofuda Talisman", S1, "common", ["charm"], cd=3.5, block=4)

item("jitte", "Jitte", V2, "rare", ["weapon"], cd=1.8, dmg=(3, 5), stun=0.4)
item("yumi", "Yumi Bow", V3, "rare", ["weapon"], cd=2.6, dmg=(7, 10), price=7)
item("sake_gourd", "Sake Gourd", V2, "rare", ["food"], cd=5.0, heal=10)
item("omamori", "Omamori", S1, "rare", ["charm"], s_hp=12)
item("daruma", "Daruma Doll", S1, "rare", ["charm"], s_regen=1, price=7)
item("iron_fan", "Iron Fan", H2, "rare", ["weapon", "armor"], cd=2.5, dmg=(2, 3), block=4)
item("incense", "Temple Incense", S1, "rare", ["charm"], aura=dict(tags=None, speed=0.12), price=7)

item("kanabo", "Kanabō", V3, "epic", ["weapon"], cd=3.2, dmg=(12, 17), stun=0.6, price=12)
item("maneki", "Maneki-neko", S1, "epic", ["charm"], s_crit=0.08, s_hp=8)
item("oni_mask", "Oni Mask", S1, "epic", ["charm"], s_thorns=3, aura=dict(tags=("weapon",), dmg=1))

item("kusanagi", "Grass-Cutter Blade", V3, "legendary", ["weapon"], cd=1.9, dmg=(12, 16),
     lifesteal=0.2, price=18)
item("dragon_pearl", "Dragon Pearl", S1, "legendary", ["charm"], s_regen=2, s_block=15)

# ================================================================ SAMURAI - the blade & armor
item("katana", "Katana", V3, "common", ["weapon"], cls="samurai", cd=1.9, dmg=(4, 7), price=5)
item("do_armor", "Dō Armor", SQ, "common", ["armor"], cls="samurai", cd=4.0, block=6, price=4)
item("wakizashi", "Wakizashi", V2, "common", ["weapon"], cls="samurai", cd=1.4, dmg=(2, 4))
item("kabuto", "Kabuto Helm", H2, "rare", ["armor"], cls="samurai", s_block=12, s_thorns=1)
item("war_banner", "Sashimono Banner", V2, "rare", ["charm"], cls="samurai",
     aura=dict(tags=("weapon",), dmg=2), price=7)
item("naginata", "Naginata", L4, "rare", ["weapon"], cls="samurai", cd=2.4, dmg=(8, 11), stun=0.4, price=8)
item("nodachi", "Nōdachi", V4, "epic", ["weapon"], cls="samurai", cd=3.0, dmg=(16, 22), stun=0.7, price=13)
item("o_yoroi", "Ō-yoroi", R23, "epic", ["armor"], cls="samurai", cd=4.5, block=20, s_thorns=2, price=13)
item("bushido_scroll", "Bushidō Scroll", H2, "legendary", ["scroll"], cls="samurai",
     aura=dict(tags=("weapon",), dmg=3, speed=0.25), price=18)
item("masamune", "Masamune's Edge", V3, "legendary", ["weapon"], cls="samurai",
     cd=1.8, dmg=(9, 13), crit=0.15, lifesteal=0.15, price=20)

# ================================================================ NINJA - speed, evasion, many strikes
item("ninjato", "Ninjatō", V2, "common", ["weapon"], cls="ninja", cd=1.4, dmg=(4, 6), price=4)
item("shuriken", "Shuriken", S1, "common", ["weapon"], cls="ninja", cd=0.9, dmg=(2, 3))
item("smoke_bomb", "Smoke Bomb", S1, "common", ["tool"], cls="ninja", cd=4.0, dodge=1)
item("kunai", "Kunai", S1, "common", ["weapon"], cls="ninja", cd=1.0, dmg=(2, 3))
item("makibishi", "Makibishi", S1, "rare", ["tool"], cls="ninja", s_thorns=2, price=5)
item("fire_bomb", "Hōroku Fire Bomb", S1, "rare", ["fire"], cls="ninja", cd=3.5, dmg=(2, 3), burn=3, price=7)
item("tekko_kagi", "Tekkō-kagi Claws", V2, "rare", ["weapon"], cls="ninja", cd=1.0, dmg=(2, 4),
     lifesteal=0.4, price=7)
item("kaginawa", "Grappling Hook", H2, "rare", ["tool"], cls="ninja",
     aura=dict(tags=("weapon",), speed=0.2), price=7)
item("kusarigama", "Kusarigama", J4, "epic", ["weapon"], cls="ninja", cd=2.0, dmg=(7, 10), stun=0.5, price=13)
item("shadow_cloak", "Shadow Cloak", SQ, "epic", ["armor"], cls="ninja", cd=6.0, dodge=1, s_evade=0.12,
     price=12)
item("fuma_shuriken", "Fūma Shuriken", SQ, "legendary", ["weapon"], cls="ninja",
     cd=1.8, dmg=(4, 6), hits=3, price=19)

# ================================================================ KUNOICHI - poison, crits, control
item("kanzashi", "Kanzashi Hairpin", V2, "common", ["weapon"], cls="kunoichi", cd=1.3, dmg=(3, 5),
     crit=0.15, price=4)
item("poison_tea", "Poisoned Tea", S1, "common", ["poison"], cls="kunoichi", cd=2.5, poison=2, price=4)
item("silk_veil", "Silk Veil", H2, "common", ["charm"], cls="kunoichi", s_evade=0.06)
item("fukiya", "Fukiya Blowgun", V2, "common", ["weapon", "poison"], cls="kunoichi",
     cd=2.0, dmg=(1, 1), poison=1)
item("kaiken", "Kaiken Dagger", S1, "rare", ["weapon"], cls="kunoichi", cd=1.0, dmg=(2, 3), crit=0.2)
item("shamisen", "Shamisen", V3, "rare", ["charm"], cls="kunoichi", aura=dict(tags=None, speed=0.2), price=7)
item("sleep_powder", "Sleeping Powder", S1, "rare", ["tool"], cls="kunoichi", cd=5.0, stun=1.0, price=7)
item("torikabuto", "Torikabuto Root", S1, "rare", ["poison"], cls="kunoichi",
     aura=dict(tags=("poison",), poison=1), price=7)
item("noh_mask", "Noh Mask", S1, "epic", ["charm"], cls="kunoichi", s_crit=0.12, s_evade=0.05)
item("garrote", "Silk Garrote", H3, "epic", ["weapon", "poison"], cls="kunoichi",
     cd=2.2, dmg=(4, 6), poison=2, crit=0.1, price=12)
item("fugu", "Fugu Venom", SQ, "legendary", ["poison"], cls="kunoichi", cd=3.5, poison=5, stun=0.5, price=18)


# ================================================================ enemy moves
def eitem(iid, name, **stats):
    item(iid, name, S1, "common", ["enemy"], enemy=True, **stats)


# stage 1
eitem("e_rusty_katana", "Rusty Katana", cd=1.8, dmg=(3, 5))
eitem("e_dirty_trick", "Sand in the Eyes", cd=6.0, stun=0.5)
eitem("e_kappa_claw", "Webbed Claw", cd=1.4, dmg=(2, 4))
eitem("e_river_water", "Head-Dish Water", cd=5.0, heal=6)
eitem("e_leaf_blade", "Leaf Blade", cd=1.2, dmg=(2, 3))
eitem("e_illusion", "Illusion", cd=6.0, dodge=1)
eitem("e_yari", "Yari Thrust", cd=2.2, dmg=(5, 7))
eitem("e_jingasa", "Jingasa Hat", cd=5.0, block=6)
eitem("e_iai", "Iai Slash", cd=2.0, dmg=(6, 9))
eitem("e_parry", "Parry", cd=4.0, block=8)
eitem("e_quickdraw", "Lightning Draw", cd=7.0, dmg=(11, 14), stun=0.8, sunder=0.5)
eitem("e_wind_sickle", "Wind Sickle", cd=0.8, dmg=(2, 3))
eitem("e_gale", "Cutting Gale", cd=4.0, dmg=(4, 6), hits=2)
eitem("e_warlord_blade", "Warlord's Blade", cd=2.0, dmg=(8, 11))
eitem("e_war_cry", "War Cry", cd=6.0, block=8)
eitem("e_cheap_shot", "Cheap Shot", cd=5.0, dmg=(3, 4), stun=0.6)
eitem("e_second_blade", "Second Blade", cd=1.5, dmg=(4, 6))
# stage 2
eitem("e_foxfire", "Foxfire", cd=2.2, burn=2)
eitem("e_fox_bite", "Fox Bite", cd=1.4, dmg=(4, 6))
eitem("e_venom_fang", "Venom Fang", cd=2.0, dmg=(3, 5), poison=2)
eitem("e_web", "Silk Web", cd=6.0, stun=0.8)
eitem("e_branch", "Lashing Branch", cd=1.6, dmg=(4, 6))
eitem("e_root", "Root Wall", cd=4.0, block=10)
eitem("e_feather_blade", "Feather Blade", cd=1.0, dmg=(3, 5))
eitem("e_thunder", "Thunderclap", cd=4.0, dmg=(10, 14), stun=0.8)
eitem("e_nue_claws", "Tiger Claws", cd=1.3, dmg=(5, 7))
eitem("e_snake_tail", "Serpent Tail", cd=3.0, poison=3)
eitem("e_long_neck", "Coiling Neck", cd=1.8, dmg=(7, 9), lifesteal=0.5)
eitem("e_gaze", "Hypnotic Gaze", cd=5.0, stun=1.0)
eitem("e_bridal_fan", "Bridal Fan", cd=1.6, dmg=(5, 8))
eitem("e_jealousy", "Jealous Venom", cd=3.0, poison=3)
eitem("e_veil", "Wedding Veil", cd=5.0, block=10)
eitem("e_serpent_flames", "Serpent Flames", cd=2.0, burn=3)
eitem("e_coil", "Crushing Coil", cd=3.0, dmg=(10, 14), stun=0.6)
# stage 3
eitem("e_club", "Iron Club", cd=3.0, dmg=(16, 22), stun=0.6, sunder=0.5)
eitem("e_hide", "Oni Hide", cd=5.0, block=12)
eitem("e_bone_crush", "Bone Crush", cd=2.6, dmg=(12, 16))
eitem("e_grave_chill", "Grave Chill", cd=4.0, poison=4)
eitem("e_kunai_storm", "Kunai Storm", cd=0.8, dmg=(3, 5))
eitem("e_clan_smoke", "Clan Smoke", cd=5.0, dodge=1)
eitem("e_poison_kunai", "Poison Kunai", cd=3.0, poison=2)
eitem("e_cursed_katana", "Cursed Katana", cd=1.8, dmg=(9, 12), lifesteal=0.3)
eitem("e_cursed_armor", "Cursed Armor", cd=4.5, block=14)
eitem("e_tengu_fan", "Tengu War Fan", cd=3.0, dmg=(8, 10), stun=0.6)
eitem("e_tengu_gale", "Mountain Gale", cd=1.0, dmg=(4, 6))
eitem("e_feathers", "Feather Veil", cd=6.0, dodge=1)
eitem("e_hannya_blade", "Hannya Blade", cd=2.2, dmg=(12, 16))
eitem("e_rage", "Jealous Rage", cd=3.5, burn=4)
eitem("e_ashura_blade", "Shogun's Blade", cd=1.8, dmg=(12, 16))
eitem("e_shogun_armor", "Shogun's Armor", cd=5.0, block=18)
eitem("e_command", "Shatter Command", cd=6.0, stun=1.0, sunder=1.0)
eitem("e_oni_guard", "Oni Guard", cd=3.0, block=15)
eitem("e_six_arms", "Six Arms", cd=0.9, dmg=(6, 9), lifesteal=0.4)

# ================================================================ classes
CHARACTERS = {
    "samurai": dict(
        name="Samurai", color=(200, 60, 60), glyph="S", hp=60, portrait="samurai",
        style="Heavy blades / Armor / Ramping power",
        passive="Bushidō: start each battle with 6 Block. Every weapon hit builds 1 Resolve "
                "(max 5). Each Resolve adds +1 damage to every weapon hit.",
        lore="A masterless swordsman walking the road to restore his clan's honour.",
        start=["katana", "do_armor", "onigiri"],
    ),
    "ninja": dict(
        name="Ninja", color=(90, 110, 200), glyph="N", hp=60, portrait="ninja",
        style="Speed / Evasion / Many strikes",
        passive="Shinobi: 20% chance to evade enemy hits. Your weapons trigger 15% faster.",
        lore="A shadow of the Iga hills, sent to end the Demon Shogun before he wakes.",
        start=["ninjato", "shuriken", "smoke_bomb"],
    ),
    "kunoichi": dict(
        name="Kunoichi", color=(200, 90, 170), glyph="K", hp=70, portrait="kunoichi",
        style="Poison / Crits / Crowd control",
        passive="Deadly Grace: +5% crit. Your crits inflict 2 Poison. Poison you inflict "
                "ticks every 0.8s instead of every 1s.",
        lore="Entertainer by day, assassin by night. Every gift she gives is poisoned.",
        start=["kanzashi", "poison_tea", "fukiya", "silk_veil"],
    ),
}

# Techniques: permanent run upgrades. Earned by beating elites and bosses.
TECHNIQUES = {
    # samurai
    "iaijutsu": dict(cls="samurai", name="Iaijutsu", desc="The first strike of each weapon deals triple damage.",
                     first_strike=3.0),
    "unbreakable": dict(cls="samurai", name="Unbreakable Will", desc="+15 Max HP.", max_hp=15),
    "kenjutsu": dict(cls="samurai", name="Kenjutsu Mastery", desc="All weapons deal +2 damage.", weapon_dmg=2),
    "ironclad": dict(cls="samurai", name="Ironclad", desc="Start each battle with +15 Block.", s_block=15),
    "fighting_spirit": dict(cls="samurai", name="Fighting Spirit", desc="Max Resolve +4.", resolve_max=4),
    "zanshin": dict(cls="samurai", name="Zanshin", desc="+10% crit chance.", crit=0.10),
    # ninja
    "kawarimi": dict(cls="ninja", name="Kawarimi", desc="Start each battle with 2 Dodge charges.", dodge=2),
    "swift_hands": dict(cls="ninja", name="Swift Hands", desc="Weapons trigger 15% faster.", weapon_speed=0.15),
    "shadow_step": dict(cls="ninja", name="Shadow Step", desc="+10% evasion.", evade=0.10),
    "fire_arts": dict(cls="ninja", name="Katon Arts", desc="Items that Burn inflict +2 Burn.", item_burn=2),
    "lethal": dict(cls="ninja", name="Lethal Precision", desc="+12% crit chance.", crit=0.12),
    "endurance": dict(cls="ninja", name="Mountain Training", desc="+12 Max HP.", max_hp=12),
    # kunoichi
    "vipers_kiss": dict(cls="kunoichi", name="Viper's Kiss", desc="Your crits inflict +2 more Poison.",
                        poison_on_crit=2),
    "toxicology": dict(cls="kunoichi", name="Toxicology", desc="Items that Poison inflict +1 Poison.",
                       item_poison=1),
    "allure": dict(cls="kunoichi", name="Allure", desc="All enemy items are 12% slower.", enemy_slow=0.12),
    "blade_dance": dict(cls="kunoichi", name="Blade Dance", desc="+10% crit chance.", crit=0.10),
    "vanishing": dict(cls="kunoichi", name="Vanishing Veil", desc="+8% evasion.", evade=0.08),
    "blood_arts": dict(cls="kunoichi", name="Blood Arts", desc="Weapons gain 15% lifesteal.", weapon_lifesteal=0.15),
}

# ================================================================ enemies
# phases: when HP falls to `at` (fraction), the enemy transforms.
ENEMIES = {
    # ---- stage 1: The Old Highway
    "bandit": dict(name="Highway Bandit", hp=45, items=["e_rusty_katana", "e_dirty_trick"]),
    "kappa": dict(name="Kappa", hp=50, items=["e_kappa_claw", "e_river_water"]),
    "tanuki": dict(name="Tanuki Trickster", hp=40, evade=0.25, items=["e_leaf_blade", "e_illusion"]),
    "ashigaru": dict(name="Deserter Ashigaru", hp=55, items=["e_yari", "e_jingasa"]),
    "ronin_duelist": dict(name="Rōnin Duelist", hp=100, crit=0.2,
                          items=["e_iai", "e_parry", "e_quickdraw"],
                          desc="Hits hard and fast. His Lightning Draw breaks armor - kill him quickly."),
    "kamaitachi": dict(name="Kamaitachi", hp=85, evade=0.2, items=["e_wind_sickle", "e_gale"],
                       desc="A whirlwind weasel. Many small cuts: Block and thorns shine."),
    "kurogane": dict(name="Kurogane, the Bandit Warlord", hp=200,
                     items=["e_warlord_blade", "e_war_cry", "e_cheap_shot"],
                     desc="Ruler of the highway. At half health he draws a second blade.",
                     phases=[dict(at=0.5, msg="Kurogane draws his second blade!",
                                  add=["e_second_blade"], speed=1.15, block=10)]),
    # ---- stage 2: The Mist-Veiled Forest
    "kitsune": dict(name="Kitsune", hp=85, evade=0.2, items=["e_foxfire", "e_fox_bite"]),
    "jorogumo": dict(name="Jorōgumo", hp=95, items=["e_venom_fang", "e_web"]),
    "kodama": dict(name="Kodama Grove", hp=110, regen=2, items=["e_branch", "e_root"]),
    "karasu_tengu": dict(name="Karasu Tengu", hp=80, evade=0.25, items=["e_feather_blade"]),
    "nue": dict(name="Nue", hp=175, items=["e_thunder", "e_nue_claws", "e_snake_tail"],
                desc="Chimera of the storm. Its thunder stuns - and the poison never stops."),
    "rokurokubi": dict(name="Rokurokubi", hp=155, items=["e_long_neck", "e_gaze"],
                       desc="Drains your life with every bite. Burst it down."),
    "kiyohime": dict(name="Kiyohime, the Serpent Bride", hp=360,
                     items=["e_bridal_fan", "e_jealousy", "e_veil"],
                     desc="Spurned and furious. At half health she becomes a fire-breathing serpent.",
                     phases=[dict(at=0.5, msg="Kiyohime transforms into the Great Serpent!",
                                  add=["e_serpent_flames", "e_coil"], speed=1.1, heal=50)]),
    # ---- stage 3: Castle of the Demon Shogun
    "oni": dict(name="Oni Brute", hp=190, items=["e_club", "e_hide"]),
    "gashadokuro": dict(name="Gashadokuro", hp=210, thorns=2,
                        desc="A giant of bones. Its thorns punish rapid strikes.", items=["e_bone_crush", "e_grave_chill"]),
    "shadow_clan": dict(name="Shadow Clan Assassins", hp=150, evade=0.3,
                        items=["e_kunai_storm", "e_clan_smoke", "e_poison_kunai"]),
    "possessed": dict(name="Possessed Samurai", hp=180, items=["e_cursed_katana", "e_cursed_armor"]),
    "tengu_lord": dict(name="The Tengu Lord", hp=270, evade=0.25,
                       items=["e_tengu_fan", "e_tengu_gale", "e_feathers"],
                       desc="Master of the mountain wind. Hard to hit, harder to pin down."),
    "hannya": dict(name="Hannya", hp=290, items=["e_hannya_blade", "e_rage"],
                   desc="A demon of jealousy. Burns hotter the longer the fight goes."),
    "ashura": dict(name="Lord Ashura, the Demon Shogun", hp=760,
                   items=["e_ashura_blade", "e_shogun_armor", "e_command"],
                   desc="The final villain. His Command shatters ALL your Block. Three phases: the Shogun, his Oni Guard, and his true demon form. Each transformation purges all Poison and Burn.",
                   phases=[dict(at=0.66, msg="The Shogun summons his Oni Guard!",
                                add=["e_oni_guard"], block=30, cleanse=True),
                           dict(at=0.33, msg="Ashura reveals his six-armed demon form!",
                                add=["e_six_arms"], speed=1.25, cleanse=True)]),
}

STAGES = {
    1: dict(name="The Old Highway", subtitle="Bandits and river yokai haunt the mountain road",
            fights=["bandit", "kappa", "tanuki", "ashigaru"], elites=["ronin_duelist", "kamaitachi"],
            boss="kurogane", mult=1.0,
            rarity={"common": 70, "rare": 27, "epic": 3, "legendary": 0}),
    2: dict(name="The Mist-Veiled Forest", subtitle="Where foxes lie and spiders weave",
            fights=["kitsune", "jorogumo", "kodama", "karasu_tengu"], elites=["nue", "rokurokubi"],
            boss="kiyohime", mult=1.3,
            rarity={"common": 45, "rare": 40, "epic": 13, "legendary": 2}),
    3: dict(name="Castle of the Demon Shogun", subtitle="Every floor is guarded. Every guard is a demon.",
            fights=["oni", "gashadokuro", "shadow_clan", "possessed"], elites=["tengu_lord", "hannya"],
            boss="ashura", mult=1.35,
            rarity={"common": 30, "rare": 44, "epic": 22, "legendary": 4}),
}

START_GOLD = 6
BAG_SIZE = (7, 5)
STASH_SIZE = (6, 4)
GOLD_REWARD = {"fight": (4, 6), "elite": (9, 12), "boss": (18, 22)}
ROW_SCALING = 0.06      # enemies get +6% stats for every map row you go deeper
REST_HEAL = 0.30


def describe_stats(st):
    """Human readable lines for an item's (effective) stats."""
    out = []
    if st.get("cd"):
        out.append(f"Every {st['cd']:.1f}s:")
        if st.get("dmg"):
            hits = f" x{st['hits']}" if st.get("hits", 1) > 1 else ""
            out.append(f"  Deal {st['dmg'][0]}-{st['dmg'][1]} damage{hits}")
        if st.get("block"):
            out.append(f"  Gain {st['block']} Block")
        if st.get("heal"):
            out.append(f"  Heal {st['heal']}")
        if st.get("poison"):
            out.append(f"  Inflict {st['poison']} Poison")
        if st.get("burn"):
            out.append(f"  Inflict {st['burn']} Burn")
        if st.get("sunder"):
            out.append(f"  Destroy {int(st['sunder'] * 100)}% of enemy Block")
        if st.get("stun"):
            out.append(f"  Stun the enemy for {st['stun']:.1f}s")
        if st.get("summon"):
            sm = st["summon"]
            extra = (" + Burn" if sm.get("burn") else "") + (" + Curse" if sm.get("curse") else "")
            out.append(f"  Summon a {sm['name']} ({sm['dmg'][0]}-{sm['dmg'][1]} dmg every {sm['cd']:.1f}s{extra})")
        if st.get("curse"):
            out.append(f"  Curse {st['curse']} (enemy deals 5% less damage per Curse)")
        if st.get("hex"):
            out.append(f"  Hex: deal {st['hex']} damage per Curse on the enemy")
        if st.get("ki"):
            out.append(f"  Gain {st['ki']} Ki")
        if st.get("ki_burst"):
            out.append(f"  Ki Burst: spend all Ki, deal {st['ki_burst']} per Ki (6+ Ki stuns)")
        if st.get("per_tag"):
            out.append(f"  +{st['per_tag'][1]} damage per other {st['per_tag'][0]} in your kit")
        if st.get("grow"):
            out.append(f"  Grow: +{st['grow']} damage every hit (this battle)")
        if st.get("steal_block"):
            out.append(f"  Steal up to {st['steal_block']} Block from the enemy")
        if st.get("cleanse"):
            out.append(f"  Cleanse {st['cleanse']} Poison and Burn from yourself")
        if st.get("dodge"):
            out.append(f"  Gain {st['dodge']} Dodge (evade the next hit)")
        if st.get("regen"):
            out.append(f"  Gain {st['regen']} Regen")
        if st.get("lifesteal"):
            out.append(f"  Lifesteal {int(st['lifesteal'] * 100)}%")
        if st.get("crit"):
            out.append(f"  +{int(round(st['crit'] * 100))}% crit chance")
    starts = []
    if st.get("s_block"):
        starts.append(f"+{st['s_block']} Block")
    if st.get("s_hp"):
        starts.append(f"+{st['s_hp']} Max HP")
    if st.get("s_regen"):
        starts.append(f"+{st['s_regen']} Regen")
    if st.get("s_thorns"):
        starts.append(f"+{st['s_thorns']} Thorns")
    if st.get("s_crit"):
        starts.append(f"+{int(st['s_crit'] * 100)}% crit")
    if st.get("s_evade"):
        starts.append(f"+{int(st['s_evade'] * 100)}% evasion")
    if st.get("s_counter"):
        starts.append(f"Counter-attack +{st['s_counter']}")
    if st.get("s_curse"):
        starts.append(f"Curse the enemy {st['s_curse']}")
    if st.get("s_crit_block"):
        starts.append(f"+{st['s_crit_block']} Block on every crit")
    if st.get("s_crit_poison"):
        starts.append(f"+{st['s_crit_poison']} Poison on every crit")
    if starts:
        out.append("Battle start: " + ", ".join(starts))
    aura = st.get("aura")
    if aura:
        who = "items" if not aura.get("tags") else "/".join(aura["tags"]) + " items"
        parts = []
        for k, label in (("dmg", "dmg"), ("block", "Block"), ("poison", "Poison"),
                         ("burn", "Burn"), ("heal", "heal")):
            if aura.get(k):
                parts.append(f"+{aura[k]} {label}")
        if aura.get("speed"):
            parts.append(f"+{int(aura['speed'] * 100)}% speed")
        if aura.get("summon_dmg"):
            parts.append(f"+{aura['summon_dmg']} shikigami dmg")
        if aura.get("ki"):
            parts.append(f"+{aura['ki']} Ki")
        if aura.get("crit"):
            parts.append(f"+{int(aura['crit'] * 100)}% crit")
        out.append(f"Adjacent {who}: " + ", ".join(parts))
    return out


# ================================================================ ITEM LEVELS
# Drop a copy of an item onto an identical one (same level) to merge them: level 2, then level 3.
MAX_LEVEL = 3


def sell_value(iid, level=1):
    """What the pawn shop pays: half the price, times the level (a merged item used up extra copies)."""
    return max(1, ITEMS[iid]["price"] * level // 2)


def level_stats(st, level):
    """Return a copy of an item's stats scaled to its level (+50% numbers per level, 8% faster)."""
    import copy as _copy
    out = _copy.deepcopy(st)
    out["level"] = level
    if level <= 1:
        return out
    mult = 1 + 0.5 * (level - 1)
    if out.get("dmg"):
        out["dmg"] = (round(out["dmg"][0] * mult), round(out["dmg"][1] * mult))
    for k in ("block", "heal", "poison", "burn", "regen", "s_block", "s_hp", "s_regen", "s_thorns", "dodge",
              "curse", "hex", "ki", "ki_burst", "s_counter", "s_curse", "s_crit_block", "s_crit_poison",
              "grow", "steal_block", "cleanse"):
        if out.get(k):
            out[k] = max(out[k] + 1, round(out[k] * mult))
    for k in ("s_crit", "s_evade", "crit", "lifesteal"):
        if out.get(k):
            out[k] = round(out[k] * (1 + 0.25 * (level - 1)), 3)
    if out.get("stun"):
        out["stun"] = round(out["stun"] * (1 + 0.25 * (level - 1)), 2)
    if out.get("summon"):
        sm = out["summon"]
        sm["dmg"] = (round(sm["dmg"][0] * mult), round(sm["dmg"][1] * mult))
    if out.get("per_tag"):
        out["per_tag"] = (out["per_tag"][0], out["per_tag"][1] + (level - 1))
    if out.get("cd"):
        out["cd"] = round(out["cd"] * (1 - 0.08 * (level - 1)), 2)
    if out.get("aura"):
        a = out["aura"]
        for k in ("dmg", "block", "poison", "burn", "heal"):
            if a.get(k):
                a[k] += level - 1
        for k in ("speed", "crit"):
            if a.get(k):
                a[k] = round(a[k] * mult, 3)
    out["name"] = f"{st['name']} +{level - 1}"
    return out


# ================================================================ LOOT DROPS (enemy-exclusive items)
# Never sold in shops: you only get them by beating the enemy that carries them.
def loot(iid, name, shape, rarity, tags, **stats):
    item(iid, name, shape, rarity, tags, loot=True, **stats)


loot("bandit_shiv", "Bandit's Shiv", S1, "rare", ["weapon"], cd=1.1, dmg=(2, 4), crit=0.1)
loot("kappa_cucumber", "Kappa's Cucumber", S1, "rare", ["food"], cd=4.0, heal=6, regen=1)
loot("tanuki_leaf", "Tanuki Leaf", S1, "rare", ["tool"], cd=5.0, dodge=1, s_evade=0.05)
loot("ashigaru_yari", "Ashigaru Yari", V3, "rare", ["weapon"], cd=2.0, dmg=(5, 8))
loot("boar_tusk", "Boar Tusk", S1, "rare", ["weapon"], cd=1.6, dmg=(3, 5), stun=0.2)
loot("prayer_beads", "Prayer Beads", S1, "rare", ["charm"], s_hp=10, s_regen=1)
loot("ronin_blade", "Rōnin's Last Blade", V3, "epic", ["weapon"], cd=1.7, dmg=(7, 10), crit=0.15)
loot("wind_sickle", "Wind Sickle", V2, "epic", ["weapon"], cd=0.8, dmg=(2, 3))
loot("warlord_blade", "Warlord's Second Blade", V3, "legendary", ["weapon"], cd=1.5, dmg=(8, 11), block=3)
loot("toad_scroll", "Toad Sage Scroll", H2, "legendary", ["scroll"], s_regen=1,
     aura=dict(tags=None, speed=0.2))
loot("foxfire_orb", "Foxfire Orb", S1, "rare", ["fire"], cd=2.5, burn=2)
loot("silk_spool", "Jorōgumo Silk", S1, "rare", ["tool"], cd=5.0, stun=0.6)
loot("kodama_sapling", "Kodama Sapling", S1, "rare", ["charm"], s_regen=2)
loot("tengu_feather_fan", "Tengu Feather Fan", H2, "rare", ["weapon"], cd=1.0, dmg=(3, 4), s_evade=0.05)
loot("chochin_lantern", "Chōchin Lantern", V2, "epic", ["fire"], cd=3.0, burn=3)
loot("hitodama_wisp", "Hitodama Wisp", S1, "rare", ["fire"], cd=2.0, burn=1, heal=1)
loot("thunder_drum", "Raijin's Drum", SQ, "epic", ["weapon"], cd=3.5, dmg=(8, 12), stun=0.8)
loot("long_neck_comb", "Rokurokubi's Comb", S1, "epic", ["weapon"], cd=1.8, dmg=(4, 6), lifesteal=0.5)
loot("serpent_fan", "Serpent Bride's Fan", H2, "legendary", ["fire", "weapon"], cd=2.0, dmg=(3, 5), burn=3)
loot("yuki_breath", "Yuki-onna's Breath", S1, "legendary", ["tool"], cd=4.0, stun=0.8, block=8)
loot("oni_club", "Oni Club", V3, "epic", ["weapon"], cd=2.8, dmg=(14, 19), stun=0.5, sunder=0.5)
loot("giant_rib", "Giant's Rib", V2, "epic", ["armor"], s_block=15, s_thorns=4)
loot("clan_kunai", "Clan Kunai Belt", H2, "epic", ["weapon", "poison"], cd=0.8, dmg=(2, 4), poison=1)
loot("cursed_katana", "Cursed Katana", V3, "epic", ["weapon"], cd=1.6, dmg=(10, 13), lifesteal=0.3)
loot("nio_fist", "Niō's Fist", SQ, "epic", ["weapon", "armor"], cd=2.2, dmg=(9, 13), block=6)
loot("fire_scroll", "Katon Scroll", H2, "epic", ["fire"], cd=3.0, burn=5)
loot("tengu_king_fan", "Tengu King's Fan", H2, "legendary", ["weapon", "armor"], cd=2.0, dmg=(6, 8),
     stun=0.4, s_evade=0.1)
loot("hannya_mask", "Hannya Mask", S1, "legendary", ["charm"], s_crit=0.15, s_thorns=3)
loot("six_arm_blade", "Six-Armed Blade", R23, "legendary", ["weapon"], cd=1.0, dmg=(8, 11), lifesteal=0.3)
loot("orochi_fangs", "Orochi's Eight Fangs", SQ, "legendary", ["poison", "weapon"], cd=2.0, dmg=(4, 6),
     poison=4)
loot("sumo_belt", "Yokozuna Belt", H2, "epic", ["armor"], s_hp=20, s_block=10)

# ================================================================ NEW ENEMIES, ELITES, BOSSES
eitem("e_tusk", "Tusk Gore", cd=2.0, dmg=(5, 7))
eitem("e_charge", "Wild Charge", cd=6.0, dmg=(9, 12), stun=0.4)
eitem("e_monk_staff", "Shakujō Staff", cd=1.6, dmg=(3, 5))
eitem("e_prayer", "Sutra", cd=5.0, heal=5, block=5)
eitem("e_tongue", "Long Tongue", cd=1.4, dmg=(4, 6), lifesteal=0.3)
eitem("e_toad_oil", "Toad Oil", cd=4.0, poison=2)
eitem("e_belly", "Belly Bounce", cd=6.0, block=10)
eitem("e_toad_smoke", "Toad Smoke", cd=5.0, dodge=2)
eitem("e_lantern_burn", "Lantern Flame", cd=2.0, burn=2)
eitem("e_tongue_lash", "Paper Tongue", cd=1.5, dmg=(4, 6))
eitem("e_wisp_fire", "Ghost Fire", cd=1.8, burn=2)
eitem("e_wisp_touch", "Cold Touch", cd=1.2, dmg=(3, 4))
eitem("e_ice_breath", "Freezing Breath", cd=3.0, dmg=(6, 9), stun=0.7)
eitem("e_snow_veil", "Snow Veil", cd=5.0, block=14)
eitem("e_frost", "Frost Needles", cd=1.6, dmg=(5, 7))
eitem("e_blizzard", "Blizzard", cd=1.0, dmg=(3, 5))
eitem("e_nio_fist", "Guardian Fist", cd=2.4, dmg=(12, 16))
eitem("e_temple_guard", "Temple Guard", cd=4.0, block=14)
eitem("e_fire_kunai", "Fire Kunai", cd=1.0, dmg=(4, 6))
eitem("e_fire_jutsu", "Katon Jutsu", cd=3.5, burn=4)
eitem("e_orochi_bite", "Serpent Bite", cd=1.6, dmg=(9, 12))
eitem("e_orochi_venom", "Eight-Fold Venom", cd=3.0, poison=4)
eitem("e_orochi_coil", "Mountain Coil", cd=5.0, block=16, stun=0.5)
eitem("e_orochi_head", "Fourth Head", cd=1.3, dmg=(7, 10))
eitem("e_orochi_all", "Eight Heads", cd=0.8, dmg=(5, 7))
eitem("e_sumo_slap", "Harite Slap", cd=1.4, dmg=(5, 7))
eitem("e_sumo_stomp", "Shiko Stomp", cd=5.0, block=12, stun=0.5)

ENEMIES.update({
    "wild_boar": dict(name="Mountain Boar", hp=55, items=["e_tusk", "e_charge"]),
    "rogue_monk": dict(name="Rogue Yamabushi", hp=50, items=["e_monk_staff", "e_prayer"]),
    "gama": dict(name="Gama, the Toad Sage", hp=230,
                 items=["e_tongue", "e_toad_oil", "e_belly"],
                 desc="A giant toad who drains life with his tongue. At half health he vanishes into smoke.",
                 phases=[dict(at=0.5, msg="Gama vanishes into a cloud of toad smoke!",
                              add=["e_toad_smoke"], speed=1.15, heal=30)]),
    "chochin": dict(name="Chōchin-obake", hp=85, evade=0.1, items=["e_lantern_burn", "e_tongue_lash"]),
    "hitodama": dict(name="Hitodama Swarm", hp=70, evade=0.3, items=["e_wisp_fire", "e_wisp_touch"]),
    "yuki_onna": dict(name="Yuki-onna, the Snow Woman", hp=360,
                      items=["e_ice_breath", "e_snow_veil", "e_frost"],
                      desc="Her breath freezes you solid. At half health she calls a blizzard.",
                      phases=[dict(at=0.5, msg="Yuki-onna calls down a blizzard!",
                                   add=["e_blizzard"], speed=1.15)]),
    "nio_guardian": dict(name="Niō Guardian Statue", hp=220, thorns=2, items=["e_nio_fist", "e_temple_guard"]),
    "fire_ninja": dict(name="Katon Ninja", hp=160, evade=0.25, items=["e_fire_kunai", "e_fire_jutsu"]),
    "orochi": dict(name="Yamata no Orochi", hp=620,
                   items=["e_orochi_bite", "e_orochi_venom", "e_orochi_coil"],
                   desc="The eight-headed serpent. More heads wake as it weakens, and each awakening purges "
                        "Poison and Burn.",
                   phases=[dict(at=0.66, msg="Orochi's fourth head awakens!", add=["e_orochi_head"],
                                cleanse=True),
                           dict(at=0.33, msg="All eight heads strike at once!", add=["e_orochi_all"],
                                speed=1.2, cleanse=True)]),
    "sumo": dict(name="Wandering Yokozuna", hp=140, items=["e_sumo_slap", "e_sumo_stomp"],
                 desc="A grand champion who never refuses a bout."),
})

ENEMY_LOOT = {
    "bandit": "bandit_shiv", "kappa": "kappa_cucumber", "tanuki": "tanuki_leaf", "ashigaru": "ashigaru_yari",
    "wild_boar": "boar_tusk", "rogue_monk": "prayer_beads", "ronin_duelist": "ronin_blade",
    "kamaitachi": "wind_sickle", "kurogane": "warlord_blade", "gama": "toad_scroll",
    "kitsune": "foxfire_orb", "jorogumo": "silk_spool", "kodama": "kodama_sapling",
    "karasu_tengu": "tengu_feather_fan", "chochin": "chochin_lantern", "hitodama": "hitodama_wisp",
    "nue": "thunder_drum", "rokurokubi": "long_neck_comb", "kiyohime": "serpent_fan", "yuki_onna": "yuki_breath",
    "oni": "oni_club", "gashadokuro": "giant_rib", "shadow_clan": "clan_kunai", "possessed": "cursed_katana",
    "nio_guardian": "nio_fist", "fire_ninja": "fire_scroll", "tengu_lord": "tengu_king_fan",
    "hannya": "hannya_mask", "ashura": "six_arm_blade", "orochi": "orochi_fangs", "sumo": "sumo_belt",
}

# Each run (seed) picks FIGHTS_PER_RUN regular enemies and one boss per stage from these pools.
STAGES[1]["fights"] = ["bandit", "kappa", "tanuki", "ashigaru", "wild_boar", "rogue_monk"]
STAGES[1]["bosses"] = ["kurogane", "gama"]
STAGES[2]["fights"] = ["kitsune", "jorogumo", "kodama", "karasu_tengu", "chochin", "hitodama"]
STAGES[2]["bosses"] = ["kiyohime", "yuki_onna"]
STAGES[3]["fights"] = ["oni", "gashadokuro", "shadow_clan", "possessed", "nio_guardian", "fire_ninja"]
STAGES[3]["bosses"] = ["ashura", "orochi"]
FIGHTS_PER_RUN = 4

# ================================================================ BALANCE KNOBS
# Tuned by tools/balance.py (the Balance Director). Values in assets/balance.json override these.
BALANCE = {
    "fight_mult": 1.35,     # regular mobs (they were too easy)
    "elite_mult": 1.15,
    "boss_mult": 1.0,
    "stage_mult": {1: 1.0, 2: 1.3, 3: 1.35},
    "class_hp": {},         # per-class starting-HP multiplier, e.g. {"ninja": 1.05}
}


def _load_balance_overrides():
    import json as _json
    import os as _os
    p = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "assets", "balance.json")
    if _os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            data = _json.load(f)
        for k, v in data.items():
            if k == "stage_mult":
                BALANCE["stage_mult"] = {int(s): m for s, m in v.items()}
            elif k in BALANCE:
                BALANCE[k] = v


_load_balance_overrides()


# ================================================================ BUILD MECHANICS (v3)
# New stat keys (see combat.py):
#   summon=dict(name, dmg=(lo,hi), cd, burn?, curse?)  - spawn a shikigami that fights all battle (max 5)
#   curse=N      - enemy loses 4% damage per Curse stack (max 60%)
#   hex=N        - deal N damage per Curse stack on the enemy (ignores Block)
#   ki=N         - gain N Ki.   ki_burst=N - spend ALL Ki: deal N per Ki (6+ Ki also stuns)
#   per_tag=(tag, N) - +N damage for every OTHER item with that tag in your kit
#   s_counter=N  - strike back for N whenever an enemy attack lands on you
#   s_curse=N    - Curse the enemy at battle start
#   s_crit_block=N / s_crit_poison=N - gain Block / inflict Poison whenever you crit
#   aura keys: summon_dmg (+dmg to adjacent summon items), ki (+Ki to adjacent Ki items)

# ---------------------------------------------------------------- ONMYOJI: shikigami & curses
item("paper_shikigami", "Paper Shikigami", S1, "common", ["summon", "charm"], cls="onmyoji", cd=3.0,
     summon=dict(name="Paper Crane", dmg=(3, 4), cd=1.6), price=4)
item("binding_ofuda", "Ofuda of Binding", S1, "common", ["curse", "charm"], cls="onmyoji", cd=3.0, curse=2)
item("spirit_brush", "Spirit Brush", V2, "rare", ["tool"], cls="onmyoji",
     aura=dict(tags=("summon",), summon_dmg=1, speed=0.1), price=7)
item("fox_shikigami", "Fox Shikigami", SQ, "rare", ["summon", "fire"], cls="onmyoji", cd=5.0,
     summon=dict(name="Spirit Fox", dmg=(4, 5), cd=1.8, burn=1), price=8)
item("yin_yang_mirror", "Yin-Yang Mirror", S1, "rare", ["curse", "armor"], cls="onmyoji", cd=4.0, curse=2, block=4)
item("onmyo_compass", "Onmyō Compass", S1, "rare", ["curse", "tool"], cls="onmyoji", s_curse=3, price=6)
item("hex_scroll", "Hex of Five Elements", H2, "epic", ["scroll", "curse"], cls="onmyoji", cd=4.0, hex=4, price=12)
item("seimei_star", "Seimei's Star", S1, "epic", ["charm"], cls="onmyoji",
     aura=dict(tags=("summon",), speed=0.3, summon_dmg=1), price=12)
item("crow_shikigami", "Crow Shikigami", V2, "epic", ["summon", "curse"], cls="onmyoji", cd=4.5,
     summon=dict(name="Ink Crow", dmg=(2, 4), cd=1.2, curse=1), price=12)
item("twelve_generals", "Twelve Heavenly Generals", R23, "legendary", ["summon", "scroll"], cls="onmyoji",
     cd=6.0, summon=dict(name="Heavenly General", dmg=(7, 10), cd=2.0), curse=2, price=19)

# ---------------------------------------------------------------- SOHEI: Ki & counter-attacks
item("temple_naginata", "Temple Naginata", V3, "common", ["weapon", "ki"], cls="sohei", cd=2.3, dmg=(6, 9), ki=1,
     price=5)
item("kesa_robe", "Kesa Robe", SQ, "common", ["armor"], cls="sohei", s_block=10, s_counter=1, price=4)
item("prayer_bell", "Hand Bell", S1, "rare", ["charm", "ki"], cls="sohei", cd=5.0, ki=2, heal=3)
item("shakujo", "Shakujō", V3, "rare", ["weapon", "ki"], cls="sohei", cd=1.8, dmg=(3, 5), stun=0.2, ki=1, price=7)
item("iron_sandals", "Iron Geta", H2, "rare", ["armor"], cls="sohei", s_counter=2, s_hp=8)
item("sutra_scroll", "Heart Sutra", H2, "rare", ["scroll"], cls="sohei", aura=dict(tags=("ki",), ki=1, speed=0.15),
     price=7)
item("temple_bell", "Great Temple Bell", SQ, "epic", ["charm", "ki"], cls="sohei", cd=5.0, ki_burst=4, price=12)
item("fudo_statue", "Fudō Myōō Idol", SQ, "epic", ["charm", "armor"], cls="sohei", s_counter=3, s_thorns=2,
     s_block=10, price=12)
item("benkei_weapons", "Benkei's Seven Weapons", R23, "legendary", ["weapon", "ki"], cls="sohei", cd=2.0,
     dmg=(4, 6), per_tag=("weapon", 2), ki=1, price=19)

# ---------------------------------------------------------------- new SAMURAI items: Daisho swarm / Iron fortress
item("daisho", "Daishō Pair", H2, "rare", ["weapon"], cls="samurai", cd=1.6, dmg=(3, 5), per_tag=("weapon", 1),
     price=7)
item("battle_standard", "Hata-jirushi Standard", V2, "epic", ["charm"], cls="samurai",
     aura=dict(tags=("weapon",), dmg=1, speed=0.15), price=12)
item("lacquered_sode", "Lacquered Sode", H2, "common", ["armor"], cls="samurai", cd=3.0, block=6, s_thorns=1)
item("honour_tachi", "Tachi of Honour", V3, "rare", ["weapon"], cls="samurai", cd=2.2, dmg=(7, 10), crit=0.1,
     per_tag=("armor", 1), price=8)
item("unbroken_banner", "Unbroken Banner", V2, "legendary", ["charm", "armor"], cls="samurai", s_block=20,
     aura=dict(tags=("armor",), block=3), price=17)

# ---------------------------------------------------------------- new NINJA items: throwing swarm / fire arts
item("kunai_bandolier", "Kunai Bandolier", H2, "rare", ["weapon"], cls="ninja", cd=1.4, dmg=(1, 2), hits=2,
     per_tag=("weapon", 1), price=7)
item("shinobi_garb", "Shinobi Shōzoku", SQ, "common", ["armor"], cls="ninja", s_evade=0.08, s_crit=0.05)
item("oil_bomb", "Oil Bomb Pouch", S1, "rare", ["fire", "tool"], cls="ninja", cd=4.0, burn=2,
     aura=dict(tags=("fire",), burn=1), price=7)
item("mizugumo", "Mizugumo Floats", H2, "rare", ["tool"], cls="ninja", cd=4.0, dodge=1, s_evade=0.05)
item("dragon_flame", "Dragon Flame Jutsu", H2, "legendary", ["fire", "scroll"], cls="ninja", cd=3.0, dmg=(4, 6),
     burn=6, price=18)

# ---------------------------------------------------------------- new KUNOICHI items: crit control / venom
item("whisper_fan", "Fan of Whispers", H2, "rare", ["weapon"], cls="kunoichi", cd=1.4, dmg=(2, 4), crit=0.15,
     stun=0.2, price=7)
item("needle_bracelet", "Hidden Needle Bracelet", S1, "rare", ["charm", "poison"], cls="kunoichi", s_crit=0.08,
     s_crit_poison=1)
item("nightshade_perfume", "Nightshade Perfume", V2, "epic", ["poison"], cls="kunoichi", cd=3.0, poison=3, curse=1,
     price=11)
item("tea_ceremony", "Tea Ceremony Set", SQ, "common", ["food", "poison"], cls="kunoichi", cd=5.0, heal=6, poison=1)
item("moonlit_dance", "Moonlit Dance", S1, "legendary", ["charm"], cls="kunoichi",
     aura=dict(tags=None, speed=0.2, crit=0.1), s_crit=0.05, price=17)

# ---------------------------------------------------------------- new SHARED items (glue between builds)
item("weapon_rack", "Katana-kake Rack", H3, "rare", ["tool"], aura=dict(tags=("weapon",), speed=0.12), price=7)
item("hawk_charm", "Hawk-Eye Charm", S1, "rare", ["charm"], s_crit=0.06, s_crit_block=3)
item("whetted_saya", "Whetted Saya", V2, "rare", ["tool"], aura=dict(tags=("weapon",), crit=0.12))
item("bento_box", "Bentō Box", SQ, "rare", ["food"], cd=5.0, heal=8, regen=1, price=7)
item("chopsticks", "Lacquer Chopsticks", S1, "common", ["tool"], aura=dict(tags=("food",), heal=2, speed=0.2))
item("oil_flask", "Lamp Oil Flask", S1, "common", ["fire", "tool"], aura=dict(tags=("fire",), burn=1))
item("paper_lantern", "Paper Lantern", V2, "common", ["fire"], cd=2.5, burn=2)
item("bamboo_palisade", "Bamboo Palisade", H3, "rare", ["armor"], cd=4.0, block=8, s_thorns=2, price=7)
item("spiked_kote", "Spiked Kote", S1, "rare", ["armor"], s_thorns=2, aura=dict(tags=("armor",), block=2))
item("toad_venom", "Toad Venom Jar", S1, "common", ["poison"], cd=3.0, poison=2)
item("hachimaki", "Hachimaki Headband", S1, "common", ["charm"], s_hp=5, aura=dict(tags=None, speed=0.08))
item("mirror_yata", "Yata no Kagami", S1, "legendary", ["charm", "armor"], s_block=15, s_thorns=4, s_crit_block=2,
     price=17)

# ---------------------------------------------------------------- the two new classes
CHARACTERS["onmyoji"] = dict(
    name="Onmyōji", color=(110, 200, 220), glyph="O", hp=60, portrait="onmyoji",
    style="Summons / Curses / Slow build",
    passive="Shikigami Pact: start every battle with a Paper Crane shikigami and Curse 2 on the enemy. "
            "Your shikigami attack 40% faster.",
    lore="A court diviner who reads the stars and binds spirits to paper. The Shogun's demons are a debt to collect.",
    start=["paper_shikigami", "binding_ofuda", "onigiri"],
)
CHARACTERS["sohei"] = dict(
    name="Sōhei", color=(230, 150, 60), glyph="H", hp=76, portrait="sohei",
    style="Counter-attacks / Ki / Endurance",
    passive="Iron Faith: start every battle with 3 Ki. When an enemy attack lands on you, gain 1 Ki (max 12) "
            "and strike back for 2 + half your Ki.",
    lore="A warrior monk of Mount Hiei. Every blow he takes is a prayer answered with a heavier one.",
    start=["temple_naginata", "kesa_robe", "onigiri"],
)

TECHNIQUES.update({
    # onmyoji
    "seimei_lineage": dict(cls="onmyoji", name="Seimei's Lineage", desc="Your shikigami deal +2 damage.",
                           summon_dmg=2),
    "twin_shikigami": dict(cls="onmyoji", name="Twin Shikigami", desc="Start every battle with a second Paper Crane.",
                           extra_summon=1),
    "deep_curse": dict(cls="onmyoji", name="Deep Curse", desc="Items that Curse inflict +1 Curse.", item_curse=1),
    "haunting": dict(cls="onmyoji", name="Haunting", desc="Your shikigami Curse on every hit.", summon_curse=1),
    "paper_wall": dict(cls="onmyoji", name="Paper Wall", desc="Start each battle with +14 Block.", s_block=14),
    "vital_talisman": dict(cls="onmyoji", name="Vital Talisman", desc="+14 Max HP.", max_hp=14),
    # sohei
    "iron_body": dict(cls="sohei", name="Iron Body", desc="Max Ki +6.", ki_max=6),
    "righteous_fury": dict(cls="sohei", name="Righteous Fury", desc="Your counter-attacks deal +2 damage.", counter=2),
    "zazen": dict(cls="sohei", name="Zazen", desc="Start every battle with 4 Ki.", ki_start=4),
    "thunder_bell": dict(cls="sohei", name="Thunder Bell", desc="Ki bursts deal +1 damage per Ki.",
                         ki_burst_bonus=1),
    "stone_skin": dict(cls="sohei", name="Stone Skin", desc="Start each battle with +12 Block.", s_block=12),
    "mountain_vow": dict(cls="sohei", name="Mountain Vow", desc="+15 Max HP.", max_hp=15),
})

# build guide shown on the class-select screen and in DESIGN.md
BUILDS = {
    "samurai": ["Daishō swarm: Daishō Pair, Battle Standard, Weapon Rack - more weapons, more damage each",
                "Iron fortress: Ō-yoroi, Lacquered Sode, Tachi of Honour, Unbroken Banner - armor that hits back"],
    "ninja": ["Throwing swarm: Shuriken, Kunai Bandolier, Grappling Hook, Weapon Rack - dozens of fast hits",
              "Fire arts: Fire Bomb, Oil Bomb Pouch, Lamp Oil Flask, Dragon Flame Jutsu - stacking Burn"],
    "kunoichi": ["Venom: Poisoned Tea, Torikabuto Root, Nightshade Perfume, Fugu Venom - Poison that never stops",
                 "Crit control: Kaiken, Fan of Whispers, Needle Bracelet, Whetted Saya - crits that poison and stun"],
    "onmyoji": ["Spirit army: Paper & Fox Shikigami, Spirit Brush, Seimei's Star - up to 5 shikigami",
                "Curse & hex: Ofuda of Binding, Onmyō Compass, Crow Shikigami, Hex of Five Elements"],
    "sohei": ["Iron faith: Kesa Robe, Iron Geta, Fudō Myōō Idol - take hits, gain Ki, strike back",
              "Ki burst: Hand Bell, Heart Sutra, Great Temple Bell - store Ki then release it in one blow"],
}

item("spring_gourd", "Mountain Spring Gourd", V2, "common", ["food", "ki"], cls="sohei", cd=5.0, heal=5, ki=1)


# ================================================================ v4: GROW / STEAL BLOCK / CLEANSE items
#   grow=N        - this weapon gains +N damage every time it hits (for the rest of the battle)
#   steal_block=N - take up to N Block from the enemy and add it to yours
#   cleanse=N     - remove N Poison and N Burn from yourself
item("bokken", "Training Bokken", V2, "common", ["weapon"], cd=1.5, dmg=(1, 2), grow=1)
item("purifying_salt", "Purifying Salt", S1, "common", ["charm"], cd=4.0, cleanse=3, heal=2)
item("thieves_hook", "Thief's Grapnel", V2, "rare", ["weapon"], cd=2.0, dmg=(2, 4), steal_block=5)
item("sacred_sake", "Sacred Miki Sake", V2, "rare", ["food"], cd=6.0, heal=8, cleanse=4)
item("oni_gauntlet", "Oni Gauntlet", SQ, "epic", ["weapon"], cd=2.4, dmg=(5, 8), grow=2, price=12)
item("taiko_drum", "War Taiko", SQ, "epic", ["charm"], s_hp=10, aura=dict(tags=("weapon",), speed=0.2), price=12)
item("yoroi_doshi", "Yoroi-dōshi", V2, "rare", ["weapon"], cls="samurai", cd=1.7, dmg=(3, 5), sunder=0.3)
item("muramasa", "Muramasa's Grudge", V3, "legendary", ["weapon"], cls="samurai", cd=1.8, dmg=(6, 9), grow=2,
     lifesteal=0.1, price=19)
item("shadow_clone", "Shadow Clone Scroll", H2, "epic", ["scroll", "summon"], cls="ninja", cd=6.0,
     summon=dict(name="Shadow Clone", dmg=(3, 5), cd=1.0), price=12)
item("smoke_fan", "Smoke Fan", S1, "rare", ["tool"], cls="kunoichi", cd=4.0, dodge=1, cleanse=2)
item("serpent_hairpin", "Serpent Hairpin", V2, "epic", ["weapon"], cls="kunoichi", cd=1.3, dmg=(3, 5), crit=0.2,
     grow=1, price=12)
item("purify_ofuda", "Purification Ofuda", S1, "rare", ["charm", "curse"], cls="onmyoji", cd=4.0, cleanse=3, curse=1)
item("prayer_wheel", "Prayer Wheel", S1, "rare", ["charm", "ki"], cls="sohei", cd=3.0, ki=1, block=3)
item("begging_bowl", "Iron Begging Bowl", S1, "rare", ["armor"], cls="sohei", cd=3.5, steal_block=6)

# ---------------------------------------------------------------- boss-only signature moves
eitem("e_toad_tongue", "Toad Sage's Tongue", cd=1.4, dmg=(4, 6), lifesteal=0.3, steal_block=4)
eitem("e_bandit_rally", "Bandit King's Rally", cd=6.0, block=10, cleanse=3)
eitem("e_grudge_flame", "Bell of Dōjō-ji", cd=4.0, burn=3, stun=0.4)
eitem("e_snow_shroud", "Snow Shroud", cd=5.0, block=14, cleanse=4)
eitem("e_eight_venoms", "Eight Venoms", cd=3.0, poison=3, steal_block=6)

# ================================================================ ENEMIES FIGHT WITH REAL ITEMS
# kit = [(item_id, level)]: items the player can also own. Every enemy wields its own drop,
# so beating it hands you the weapon you just watched it use. "items" keeps the few moves
# that are unique to that enemy (mostly bosses' signature abilities).
ENEMY_KITS = {
    # ---- stage 1
    "bandit": (["e_dirty_trick"], [("bandit_shiv", 1), ("kasa_hat", 1)]),
    "kappa": (["e_kappa_claw"], [("kappa_cucumber", 1)]),
    "tanuki": ([], [("tanuki_leaf", 1), ("tanto", 1)]),
    "ashigaru": ([], [("ashigaru_yari", 1), ("kasa_hat", 1)]),
    "wild_boar": (["e_charge"], [("boar_tusk", 1)]),
    "rogue_monk": ([], [("bo_staff", 1), ("prayer_beads", 1), ("ofuda", 1)]),
    "ronin_duelist": (["e_quickdraw"], [("ronin_blade", 1), ("iron_fan", 1)]),
    "kamaitachi": (["e_gale"], [("wind_sickle", 1)]),
    "kurogane": (["e_cheap_shot", "e_bandit_rally"], [("katana", 2), ("do_armor", 1)]),
    "gama": (["e_toad_tongue", "e_belly"], [("toad_venom", 1)]),
    # ---- stage 2
    "kitsune": ([], [("foxfire_orb", 1), ("whisper_fan", 1)]),
    "jorogumo": (["e_venom_fang"], [("silk_spool", 1), ("fukiya", 2)]),
    "kodama": ([], [("kodama_sapling", 1), ("bo_staff", 2), ("bamboo_palisade", 1)]),
    "karasu_tengu": ([], [("tengu_feather_fan", 1), ("shuriken", 1)]),
    "chochin": (["e_tongue_lash"], [("chochin_lantern", 1), ("paper_lantern", 1)]),
    "hitodama": (["e_wisp_touch"], [("hitodama_wisp", 1)]),
    "nue": ([], [("thunder_drum", 1), ("tekko_kagi", 2), ("toad_venom", 1)]),
    "rokurokubi": ([], [("long_neck_comb", 1), ("sleep_powder", 1)]),
    "kiyohime": (["e_grudge_flame"], [("iron_fan", 2), ("nightshade_perfume", 1)]),
    "yuki_onna": (["e_frost", "e_snow_shroud"], [("yuki_breath", 1), ("kaiken", 2)]),
    # ---- stage 3
    "oni": ([], [("oni_club", 1), ("do_armor", 2), ("oni_gauntlet", 1)]),
    "gashadokuro": ([], [("giant_rib", 1), ("kanabo", 1), ("toad_venom", 2)]),
    "shadow_clan": ([], [("clan_kunai", 1), ("smoke_bomb", 1), ("shuriken", 2)]),
    "possessed": ([], [("cursed_katana", 1), ("o_yoroi", 1)]),
    "nio_guardian": ([], [("nio_fist", 1), ("fudo_statue", 1), ("bamboo_palisade", 1)]),
    "fire_ninja": ([], [("fire_scroll", 1), ("fire_bomb", 2), ("kunai", 2)]),
    "tengu_lord": (["e_feathers"], [("tengu_king_fan", 1), ("yumi", 2)]),
    "hannya": (["e_rage"], [("hannya_mask", 1), ("oni_gauntlet", 1)]),
    "ashura": (["e_command"], [("masamune", 1), ("o_yoroi", 2)]),
    "orochi": (["e_orochi_coil", "e_eight_venoms"], [("orochi_fangs", 1), ("fugu", 1)]),
    "sumo": (["e_sumo_slap"], [("sumo_belt", 1), ("iron_fan", 2)]),
}
for _eid, (_unique, _kit) in ENEMY_KITS.items():
    ENEMIES[_eid]["items"] = _unique
    ENEMIES[_eid]["kit"] = _kit

# Bosses draw their signature weapon when they transform.
ENEMIES["kurogane"]["phases"][0]["add"] = ["warlord_blade"]
ENEMIES["kiyohime"]["phases"][0]["add"] = ["serpent_fan", "e_coil"]
ENEMIES["ashura"]["phases"][1]["add"] = ["six_arm_blade"]
ENEMIES["ronin_duelist"]["crit"] = 0.1         # was 0.2: lost 63% of encounters - too punishing for stage 1
ENEMIES["gashadokuro"]["thorns"] = 0           # its Giant's Rib already gives thorns

# outlier fixes after the kit rework (checked with the before/after strength comparison)
ENEMIES["nio_guardian"]["thorns"] = 0
ENEMIES["nio_guardian"]["kit"] = [("nio_fist", 1), ("fudo_statue", 1)]
ENEMIES["gashadokuro"]["kit"] = [("giant_rib", 1), ("kanabo", 1), ("toad_venom", 1)]
ENEMIES["yuki_onna"]["kit"] = [("yuki_breath", 1), ("kaiken", 1)]
ENEMIES["gama"]["kit"] = [("toad_venom", 1), ("toad_scroll", 1)]   # wields its drop (passive Regen)
