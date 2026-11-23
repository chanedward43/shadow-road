"""? events: small story encounters on the map with choices. Pure Python (no pygame).

Each option's `do(run, rng)` changes the run and returns a result dict:
    text    - what happened (shown to the player)
    battle  - optional (enemy_id, kind): start this fight next; normal rewards follow
    choose  - optional list of item ids: let the player pick one for free
"""
from .data import ITEMS, TECHNIQUES, STAGES, max_level


def _hp(run, frac):
    return max(1, int(run.max_hp * frac))


def _heal(run, frac):
    amt = min(run.max_hp - run.hp, _hp(run, frac))
    run.hp += amt
    return amt


def _hurt(run, amount):
    run.hp = max(1, run.hp - amount)   # events never kill you outright
    return amount


# ---------------------------------------------------------------- event effects
def monk_bless(run, rng):
    run.gold -= 8
    choices = run.technique_choices(1)
    if not choices:
        return dict(text="The monk smiles. 'You have nothing left to learn from me.' He heals you instead.",
                    heal=_heal(run, 0.3))
    run.learn(choices[0])
    return dict(text=f"The monk teaches you {TECHNIQUES[choices[0]]['name']}: {TECHNIQUES[choices[0]]['desc']}")


def monk_heal(run, rng):
    return dict(text=f"The monk chants a sutra over your wounds. You recover {_heal(run, 0.25)} HP.")


def fox_feast(run, rng):
    dmg = _hurt(run, _hp(run, 0.12))
    return dict(text=f"The foxes' sake burns (-{dmg} HP), but the bride gifts you a treasure. Pick one.",
                choose=run.reward_choices("elite"))


def fox_bow(run, rng):
    run.max_hp += 6
    run.hp += 6
    return dict(text="The procession passes. The kami of the rain bless your patience: +6 Max HP.")


def smith_temper(run, rng):
    run.gold -= 10
    return dict(text="The smith wipes his brow. 'Which piece shall I temper?'", upgrade=1)


def smith_trade(run, rng):
    run.gold += 7
    return dict(text="You help at the forge all afternoon and earn 7 ryō.")


def bridge_fight(run, rng):
    eid = rng.choice(STAGES[run.stage]["elites"])
    return dict(text="You draw your weapon and step onto the bridge...", battle=(eid, "elite"))


def bridge_avoid(run, rng):
    dmg = _hurt(run, _hp(run, 0.12))
    return dict(text=f"You take the long mountain path. Rocks and cold cost you {dmg} HP.")


def tea_drink(run, rng):
    run.gold -= 5
    return dict(text=f"Warm sencha and quiet. You recover {_heal(run, 0.3)} HP.")


def tea_gamble(run, rng):
    if rng.random() < 0.5:
        run.gold += 15
        return dict(text="The dice roll in your favour: +15 ryō!")
    lost = min(run.gold, 8)
    run.gold -= lost
    return dict(text=f"The dealer smiles as you lose {lost} ryō.")


def shrine_take(run, rng):
    run.max_hp = max(10, run.max_hp - 10)
    run.hp = min(run.hp, run.max_hp)
    return dict(text="A chill runs through you (-10 Max HP), but power hums in the relic. Pick one.",
                choose=run.reward_choices("boss"))


def shrine_pray(run, rng):
    return dict(text=f"You pray quietly. Peace settles over you: +{_heal(run, 0.15)} HP.")


def sumo_fight(run, rng):
    return dict(text="You step into the ring. The crowd roars!", battle=("sumo", "elite"))


def field_search(run, rng):
    if rng.random() < 0.6:
        weapons = [i for i in ITEMS.values() if "weapon" in i["tags"] and not i["enemy"] and not i.get("loot")
                   and i["cls"] in (None, run.char_id) and i["rarity"] in ("rare", "epic")]
        iid = rng.choice(weapons)["id"]
        ok = run.add_item(iid)
        return dict(text=f"Among the broken spears you find a {ITEMS[iid]['name']}!"
                    + ("" if ok else " (No room to carry it.)"))
    return dict(text="Scavengers were waiting in the grass. Ambush!",
                battle=(rng.choice(run.fight_pool[run.stage]), "fight"))


def monkeys_soak(run, rng):
    run.max_hp += 3
    run.hp += 3
    return dict(text=f"The snow monkeys make room. You soak: +{_heal(run, 0.2)} HP and +3 Max HP.")


def monkeys_steal(run, rng):
    dmg = _hurt(run, 5)
    food = [i for i in ITEMS.values() if "food" in i["tags"] and not i["enemy"] and i["cls"] in (None, run.char_id)]
    iid = rng.choice(food)["id"]
    ok = run.add_item(iid)
    return dict(text=f"You grab their {ITEMS[iid]['name']} and get bitten (-{dmg} HP)."
                + ("" if ok else " (No room to carry it.)"))


def caravan_box(run, rng):
    run.gold -= 12
    pool = [i for i in ITEMS.values() if not i["enemy"] and i["rarity"] == "epic"
            and i["cls"] in (None, run.char_id)]
    iid = rng.choice(pool)["id"]
    ok = run.add_item(iid)
    return dict(text=f"Inside the lacquered box: {ITEMS[iid]['name']}!" + ("" if ok else " (No room to carry it.)"))


def ronin_duel(run, rng):
    return dict(text="The rōnin bows and draws. Steel flashes.", battle=("ronin_duelist", "elite"))


def well_drink(run, rng):
    if rng.random() < 0.5:
        return dict(text=f"The water is pure. +{_heal(run, 0.35)} HP.")
    dmg = _hurt(run, _hp(run, 0.1))
    return dict(text=f"Something lives in the well. It bites (-{dmg} HP) and vanishes.")


def well_coin(run, rng):
    run.gold -= 3
    if rng.random() < 0.5:
        return dict(text="The well spirit accepts your coin. Choose an item for it to bless.", upgrade=1)
    return dict(text="The coin sinks silently. Nothing happens.")


def leave(run, rng):
    return dict(text="You continue down the road.")


def _gold(n):
    return lambda run: run.gold >= n


def _upgradable(run):
    return any(i.level < max_level(i.data) for i in run.all_items())


EVENTS = [
    dict(id="monk", title="The Wandering Monk", art="rogue_monk",
         text="An old yamabushi sits under a cedar tree. 'Every traveller carries a question,' he says.",
         options=[dict(label="Donate 8 ryō: learn a technique", cond=_gold(8), do=monk_bless),
                  dict(label="Ask him to tend your wounds (heal 25%)", do=monk_heal),
                  dict(label="Leave", do=leave)]),
    dict(id="fox_wedding", title="Kitsune no Yomeiri", art="kitsune",
         text="Rain falls from a clear sky. Lanterns float through the trees: a fox wedding procession.",
         options=[dict(label="Join the feast (lose 12% HP, pick a rare treasure)", do=fox_feast),
                  dict(label="Bow and let them pass (+6 Max HP)", do=fox_bow)]),
    dict(id="smith", title="The Swordsmith's Forge", art="nodachi",
         text="A swordsmith hammers a glowing blade. 'Bring me your steel, traveller.'",
         options=[dict(label="Pay 10 ryō: level up a random item", cond=lambda r: r.gold >= 10 and _upgradable(r),
                       do=smith_temper),
                  dict(label="Work the bellows (+7 ryō)", do=smith_trade),
                  dict(label="Leave", do=leave)]),
    dict(id="bridge", title="The Haunted Bridge", art="hannya",
         text="A shadow in a demon mask blocks the only bridge across the gorge.",
         options=[dict(label="Fight it (elite battle, elite rewards)", do=bridge_fight),
                  dict(label="Take the long way around (lose 12% HP)", do=bridge_avoid)]),
    dict(id="tea_house", title="Roadside Tea House", art="poison_tea",
         text="A tea house with paper lanterns. Gamblers laugh in the back room.",
         options=[dict(label="Pay 5 ryō for tea (heal 30%)", cond=_gold(5), do=tea_drink),
                  dict(label="Gamble at dice (50%: +15 ryō, or lose 8)", do=tea_gamble),
                  dict(label="Leave", do=leave)]),
    dict(id="cursed_shrine", title="The Cursed Shrine", art="map_shrine",
         text="Moss covers a forgotten shrine. On the altar, a relic glows with cold light.",
         options=[dict(label="Take the relic (-10 Max HP, pick a legendary-tier item)", do=shrine_take),
                  dict(label="Pray (heal 15%)", do=shrine_pray),
                  dict(label="Leave", do=leave)]),
    dict(id="sumo", title="The Wandering Yokozuna", art="sumo",
         text="A grand champion stamps the ground. 'Nobody passes without a bout!'",
         options=[dict(label="Accept the bout (elite fight, wins the Yokozuna Belt)", do=sumo_fight),
                  dict(label="Bow out", do=leave)]),
    dict(id="battlefield", title="Abandoned Battlefield", art="ashigaru",
         text="Torn banners and broken spears. Something useful must still be here.",
         options=[dict(label="Search the field (60% weapon, 40% ambush)", do=field_search),
                  dict(label="Leave", do=leave)]),
    dict(id="ronin", title="A Rōnin's Challenge", art="ronin_duelist",
         text="A masterless samurai blocks the road. 'Your blade or mine. Draw.'",
         options=[dict(label="Duel him (elite fight, wins his blade)", do=ronin_duel),
                  dict(label="Walk away", do=leave)]),
    dict(id="monkeys", title="Snow Monkey Spring", art="map_rest",
         text="Snow monkeys soak in a steaming spring. One is guarding a pile of food.",
         options=[dict(label="Share the spring (heal 20%, +3 Max HP)", do=monkeys_soak),
                  dict(label="Steal their food (-5 HP, gain a food item)", do=monkeys_steal)]),
    dict(id="caravan", title="The Merchant Caravan", art="map_shop",
         text="A caravan from the capital sells sealed lacquer boxes. 'Something special in each!'",
         options=[dict(label="Buy a mystery box (12 ryō, random epic item)", cond=_gold(12), do=caravan_box),
                  dict(label="Leave", do=leave)]),
    dict(id="well", title="The Old Well", art="kappa",
         text="An old stone well. Coins glint at the bottom, and something stirs in the dark water.",
         options=[dict(label="Drink (50%: heal 35%, 50%: get bitten)", do=well_drink),
                  dict(label="Toss in 3 ryō (50%: level up an item)", cond=_gold(3), do=well_coin),
                  dict(label="Leave", do=leave)]),
]
EVENT_BY_ID = {e["id"]: e for e in EVENTS}


def pick_event(run):
    """Seeded choice of an event this run hasn't seen yet."""
    fits = [e for e in EVENTS if run.stage in e.get("stages", (run.stage,))]
    pool = [e for e in fits if e["id"] not in run.seen_events] or fits
    ev = run.rng.choice(pool)
    run.seen_events.append(ev["id"])
    return ev


def options_for(run, ev):
    """[(index, option, available)] for an event."""
    return [(i, o, o.get("cond", lambda r: True)(run)) for i, o in enumerate(ev["options"])]


def resolve(run, ev, idx):
    return ev["options"][idx]["do"](run, run.rng)


# ================================================================ v8: RISK / REWARD and MULTI-STAGE events
def blood_pact(run, rng):
    loss = max(1, int(run.max_hp * 0.15))
    run.max_hp = max(10, run.max_hp - loss)
    run.hp = min(run.hp, run.max_hp)
    return dict(text=f"The oni carves its mark into your arm (-{loss} Max HP). Its hoard is yours: pick one.",
                choose=run.reward_choices("boss"))


def blood_pact_hp(run, rng):
    dmg = _hurt(run, _hp(run, 0.3))
    return dict(text=f"You bleed for the oni (-{dmg} HP). It tosses you a heavy pouch: +25 ryō.", gold=_add_gold(run, 25))


def _add_gold(run, n):
    run.gold += n
    return n


def champion_fight(run, rng):
    eid = run.boss_of.get(max(1, run.stage - 1)) if run.stage > 1 else rng.choice(STAGES[1]["elites"])
    run.flags["champion_bounty"] = True
    return dict(text="The spirit of a fallen champion takes shape. Beat it and its legendary weapon is yours.",
                battle=(eid if eid else "ronin_duelist", "elite"), legendary=True)


def forget_technique(run, rng):
    if not run.techniques:
        return dict(text="'Your mind is already empty,' the monk laughs. 'I can buy nothing from you.'")
    tid = run.techniques.pop(rng.randrange(len(run.techniques)))
    bonus = TECHNIQUES[tid].get("max_hp", 0)
    run.max_hp -= bonus
    run.hp = min(run.hp, run.max_hp)
    run.gold += 40
    return dict(text=f"You let go of {TECHNIQUES[tid]['name']}. The monk presses 40 ryō into your hand.")


def dice_all_in(run, rng):
    bet = run.gold
    if rng.random() < 0.5:
        run.gold += bet
        return dict(text=f"Double! You walk out with {run.gold} ryō.")
    run.gold = 0
    return dict(text=f"The dice betray you. You lose all {bet} ryō.")


def merchant_gamble(run, rng):
    run.gold -= 15
    if rng.random() < 0.4:
        pool = [i for i in ITEMS.values() if not i["enemy"] and not i.get("loot") and i["rarity"] == "legendary"
                and i["cls"] in (None, run.char_id) and i["id"] not in run.owned_ids()]
        if pool:
            iid = rng.choice(pool)["id"]
            ok = run.add_item(iid)
            return dict(text=f"The cloth falls away: {ITEMS[iid]['name']}, a legendary!" +
                        ("" if ok else " (No room to carry it.)"))
    return dict(text="The cloth falls away: a painted rock. The merchant is already gone.")


# ---- multi-stage: the choice here changes what waits for you on the NEXT stage's map (an Omen node)
def tanuki_free(run, rng):
    dmg = _hurt(run, 4)
    run.flags["tanuki"] = "helped"
    return dict(text=f"You pry the trap open (-{dmg} HP). The tanuki looks back at you before it vanishes. "
                     "Something tells you you'll meet again...")


def tanuki_rob(run, rng):
    run.gold += 10
    run.flags["tanuki"] = "robbed"
    return dict(text="You take the gold coins tied to its tail (+10 ryō). It glares at you as you leave. "
                     "The forest will remember.")


def ronin_help(run, rng):
    run.gold -= 8
    run.flags["ronin"] = "saved"
    return dict(text="You pay a doctor to tend his wounds. 'I am Kagemaru,' he says. 'I will repay this debt.'")


def ronin_rob(run, rng):
    weapons = [i for i in ITEMS.values() if "weapon" in i["tags"] and not i["enemy"] and not i.get("loot")
               and i["cls"] in (None, run.char_id) and i["rarity"] == "epic"]
    iid = rng.choice(weapons)["id"]
    ok = run.add_item(iid)
    run.flags["ronin"] = "robbed"
    return dict(text=f"You take his {ITEMS[iid]['name']}. He curses your name as you walk away."
                + ("" if ok else " (No room to carry it.)"))


def leave_flag(key, value):
    def do(run, rng):
        run.flags[key] = value
        return dict(text="You continue down the road.")
    return do


NEW_EVENTS = [
    dict(id="blood_pact", title="The Oni's Bargain", art="oni", new=True,
         text="A grinning oni sits on a chest of plunder. 'Blood for gold, little warrior. Or blood for glory.'",
         options=[dict(label="Give your vigour (-15% Max HP, pick a legendary-tier item)", do=blood_pact),
                  dict(label="Bleed for it (-30% HP, +25 ryō)", do=blood_pact_hp),
                  dict(label="Leave", do=leave)]),
    dict(id="champion", title="The Champion's Grave", art="ronin_duelist", new=True,
         text="A sword stands in a burial mound. As you approach, a spectral warrior rises to guard it.",
         options=[dict(label="Fight the champion (hard elite fight, win a LEGENDARY)", do=champion_fight),
                  dict(label="Pay respects and leave", do=leave)]),
    dict(id="forgetful_monk", title="The Monk of Empty Mind", art="rogue_monk", new=True,
         text="'Knowledge is a heavy pack,' the monk says. 'I will buy what you carry in your head.'",
         options=[dict(label="Forget a random technique for 40 ryō", cond=lambda r: bool(r.techniques),
                       do=forget_technique),
                  dict(label="Leave", do=leave)]),
    dict(id="high_stakes", title="High-Stakes Dice", art="poison_tea", new=True,
         text="Yakuza gamblers wave you to their table. 'One throw. Double or nothing.'",
         options=[dict(label="Bet everything (50%: double your ryō, 50%: lose it all)",
                       cond=lambda r: r.gold >= 10, do=dice_all_in),
                  dict(label="Leave", do=leave)]),
    dict(id="veiled_merchant", title="The Veiled Merchant", art="map_shop", new=True,
         text="A merchant offers something under a silk cloth. 'Fifteen ryō. No refunds.'",
         options=[dict(label="Pay 15 ryō (40%: a legendary item, 60%: nothing)", cond=_gold(15),
                       do=merchant_gamble),
                  dict(label="Leave", do=leave)]),
    dict(id="tanuki_trap", title="A Tanuki in a Trap", art="tanuki", new=True, stages=(1,),
         text="A tanuki is caught in a hunter's trap. Gold coins are tied to its tail. It whimpers at you.",
         options=[dict(label="Free it (-4 HP). It may remember you...", do=tanuki_free),
                  dict(label="Take its coins (+10 ryō). It will remember you...", do=tanuki_rob),
                  dict(label="Leave it", do=leave_flag("tanuki", "ignored"))]),
    dict(id="wounded_ronin", title="The Wounded Rōnin", art="possessed", new=True, stages=(2,),
         text="A rōnin lies bleeding against a pine tree, his fine sword beside him.",
         options=[dict(label="Pay 8 ryō for a doctor. He may repay you...", cond=_gold(8), do=ronin_help),
                  dict(label="Take his sword (epic weapon now). He may come for you...", do=ronin_rob),
                  dict(label="Leave him", do=leave_flag("ronin", "ignored"))]),
]
for _e in NEW_EVENTS:
    EVENTS.append(_e)
EVENT_BY_ID.update({e["id"]: e for e in NEW_EVENTS})


# ---- Omens: the follow-ups, placed as a special node on the next stage's map
def omen_tanuki_gift(run, rng):
    run.gold += 12
    return dict(text="The tanuki you freed returns with its whole clan, bowing low. They give you 12 ryō and "
                     "a treasure from their hidden den. Pick one.", choose=run.reward_choices("boss"))


def omen_tanuki_revenge(run, rng):
    return dict(text="Leaves swirl into shapes... the tanuki you robbed has brought its clan. Ambush!",
                battle=("tanuki", "elite"))


def omen_ronin_gift(run, rng):
    lvl = 2
    run.add_item("ronin_blade", level=lvl)
    heal = _heal(run, 0.3)
    return dict(text=f"Kagemaru, the rōnin you saved, waits by the road. He hands you his last blade "
                     f"(level {lvl}) and treats your wounds (+{heal} HP). 'My debt is paid.'")


def omen_ronin_revenge(run, rng):
    return dict(text="A familiar voice: 'You took my sword. Now I take your life.' The rōnin draws!",
                battle=("ronin_duelist", "elite"))


OMENS = {
    "tanuki": dict(stage=2, art="tanuki", outcomes={
        "helped": dict(title="The Tanuki's Gratitude", text="Paw prints lead to a pile of gifts...",
                       label="Accept their gifts", do=omen_tanuki_gift),
        "robbed": dict(title="The Tanuki's Revenge", text="The trees whisper with laughter. You are not alone.",
                       label="Face them (elite fight)", do=omen_tanuki_revenge)}),
    "ronin": dict(stage=3, art="possessed", outcomes={
        "saved": dict(title="Kagemaru's Debt", text="A rōnin stands waiting in the road. You know that face.",
                      label="Greet him", do=omen_ronin_gift),
        "robbed": dict(title="The Rōnin's Vengeance", text="A rōnin stands waiting in the road. You know that "
                                                           "face, and the hatred in it.",
                       label="Draw your weapon (elite fight)", do=omen_ronin_revenge)}),
}


def place_omens(run):
    """Called when a stage starts: turn one map node into an Omen for every pending story thread."""
    for key, om in OMENS.items():
        state = run.flags.get(key)
        if om["stage"] != run.stage or state not in om["outcomes"] or run.flags.get(key + "_done"):
            continue
        rows = [n for r in run.map[2:5] for n in r if n["kind"] not in ("boss", "omen")]
        if rows:
            node = run.rng.choice(rows)
            node["kind"] = "omen"
            node["omen"] = key


def omen_event(run, key):
    om = OMENS[key]
    out = om["outcomes"][run.flags[key]]
    run.flags[key + "_done"] = True
    return dict(id=f"omen_{key}_{run.flags[key]}", title=out["title"], art=om["art"], text=out["text"], new=True,
                options=[dict(label=out["label"], do=out["do"])])


# ================================================================ v10: THE KAMI FORGE (Soul Forge)
FORGE_GOLD = 12
FORGE_HP = 0.12


def _two_items(run):
    return len(run.all_items()) >= 2


def forge_gold(run, rng):
    return dict(text="The kami of the forge awakens. Choose an item to give up, then the item to receive its spirit.",
                forge=("gold", FORGE_GOLD))


def forge_blood(run, rng):
    return dict(text="You cut your palm over the anvil. The kami accepts blood. Choose the items.",
                forge=("hp", FORGE_HP))


KAMI_FORGE = dict(id="soul_forge", title="The Kami Forge", art="nodachi", new=True,
                  text="A smithy older than the road itself. Its kami can pour one item's spirit into another: "
                       "the first item is lost, the second gains its signature effect at half strength.",
                  options=[dict(label=f"Offer {FORGE_GOLD} ryō: bind a spirit",
                                cond=lambda r: r.gold >= FORGE_GOLD and _two_items(r), do=forge_gold),
                           dict(label=f"Offer blood (-{int(FORGE_HP * 100)}% Max HP): bind a spirit",
                                cond=_two_items, do=forge_blood),
                           dict(label="Leave", do=leave)])
EVENTS.append(KAMI_FORGE)
EVENT_BY_ID["soul_forge"] = KAMI_FORGE


def pay_forge(run, cost):
    """Charge the forge's price. cost = ("gold", n) | ("hp", fraction) | None (free)."""
    if not cost:
        return
    kind, v = cost
    if kind == "gold":
        run.gold -= v
    else:
        loss = max(1, int(run.max_hp * v))
        run.max_hp = max(10, run.max_hp - loss)
        run.hp = min(run.hp, run.max_hp)


def auto_infuse(run, rng):
    """For bots / simulations: sacrifice the least valuable spare item into the best weapon."""
    from .spirit import can_infuse, infuse, signature
    items = run.all_items()
    value = lambda i: (["common", "rare", "epic", "legendary"].index(i.data["rarity"]), i.level)
    targets = sorted([i for i in run.bag.items if i.data.get("dmg") and not i.infusion], key=value, reverse=True)
    sources = sorted([i for i in items if signature(i.data)], key=value)
    for dst in targets[:1]:
        for src in sources:
            if can_infuse(src, dst)[0]:
                infuse(src, dst)
                for g in (run.bag, run.stash):
                    g.remove(src)
                return src, dst
    return None


# ================================================================ what each option DOES (for the AI)
# The learning agent judges event options by these effect tags, not by name, so new events don't
# require retraining - just tag their options here (or with fx=dict(...) on the option itself).
#   gold   - expected ryō change          hp      - HP change as a fraction of max (+heal / -loss)
#   max_hp - max HP change (absolute)     item    - item gained: 1 common .. 4 legendary (expected)
#   tech   - +1 learn / -1 forget a technique         upgrade - chance an item levels up
#   fight  - 1 mob, 2 elite, 2.5 very hard            risk    - chance it goes badly
#   forge  - opens the Soul Forge         future  - +1 a good omen later / -1 a bad one
FX = {
    "monk:0": dict(gold=-8, tech=1), "monk:1": dict(hp=0.25),
    "fox_wedding:0": dict(hp=-0.12, item=2), "fox_wedding:1": dict(max_hp=6),
    "smith:0": dict(gold=-10, upgrade=1), "smith:1": dict(gold=7),
    "bridge:0": dict(fight=2), "bridge:1": dict(hp=-0.12),
    "tea_house:0": dict(gold=-5, hp=0.3), "tea_house:1": dict(gold=3.5, risk=0.5),
    "cursed_shrine:0": dict(max_hp=-10, item=3.5), "cursed_shrine:1": dict(hp=0.15),
    "sumo:0": dict(fight=2, item=3),
    "battlefield:0": dict(item=1.5, fight=0.4, risk=0.4),
    "ronin:0": dict(fight=2, item=3),
    "monkeys:0": dict(hp=0.2, max_hp=3), "monkeys:1": dict(hp=-0.06, item=1),
    "caravan:0": dict(gold=-12, item=3),
    "well:0": dict(hp=0.07, risk=0.5), "well:1": dict(gold=-3, upgrade=0.5),
    "blood_pact:0": dict(max_hp=-10, item=3.5), "blood_pact:1": dict(hp=-0.3, gold=25),
    "champion:0": dict(fight=2.5, item=4),
    "forgetful_monk:0": dict(tech=-1, gold=40),
    "high_stakes:0": dict(risk=1.0),
    "veiled_merchant:0": dict(gold=-15, item=1.6, risk=0.6),
    "tanuki_trap:0": dict(hp=-0.05, future=1), "tanuki_trap:1": dict(gold=10, future=-1),
    "wounded_ronin:0": dict(gold=-8, future=1), "wounded_ronin:1": dict(item=3, future=-1),
    "soul_forge:0": dict(gold=-12, forge=1), "soul_forge:1": dict(max_hp=-8, forge=1),
    "omen_tanuki_helped:0": dict(gold=12, item=3.5), "omen_tanuki_robbed:0": dict(fight=2),
    "omen_ronin_saved:0": dict(item=3, hp=0.3), "omen_ronin_robbed:0": dict(fight=2),
}


def option_fx(label, ev=None):
    """Effect tags for an option label 'event_id:index' ({} = nothing happens, e.g. Leave)."""
    if ev is not None:
        i = int(label.rsplit(":", 1)[1])
        if ev["options"][i].get("fx") is not None:
            return ev["options"][i]["fx"]
    return FX.get(label, {})
