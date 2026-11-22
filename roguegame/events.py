"""? events: small story encounters on the map with choices. Pure Python (no pygame).

Each option's `do(run, rng)` changes the run and returns a result dict:
    text    - what happened (shown to the player)
    battle  - optional (enemy_id, kind): start this fight next; normal rewards follow
    choose  - optional list of item ids: let the player pick one for free
"""
from .data import ITEMS, TECHNIQUES, STAGES, MAX_LEVEL


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
    it = run.upgrade_random(rng)
    if not it:
        return dict(text="The smith shrugs. Everything you carry is already a masterwork.")
    return dict(text=f"Sparks fly. Your {ITEMS[it.id]['name']} is now level {it.level}!")


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
    it = run.upgrade_random(rng) if rng.random() < 0.5 else None
    if it:
        return dict(text=f"The well spirit accepts your coin. Your {ITEMS[it.id]['name']} glows: level {it.level}!")
    return dict(text="The coin sinks silently. Nothing happens.")


def leave(run, rng):
    return dict(text="You continue down the road.")


def _gold(n):
    return lambda run: run.gold >= n


def _upgradable(run):
    return any(i.level < MAX_LEVEL for i in run.all_items())


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
    pool = [e for e in EVENTS if e["id"] not in run.seen_events] or EVENTS
    ev = run.rng.choice(pool)
    run.seen_events.append(ev["id"])
    return ev


def options_for(run, ev):
    """[(index, option, available)] for an event."""
    return [(i, o, o.get("cond", lambda r: True)(run)) for i, o in enumerate(ev["options"])]


def resolve(run, ev, idx):
    return ev["options"][idx]["do"](run, run.rng)
