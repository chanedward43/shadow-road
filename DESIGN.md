# Shadow Road: Design Notes

> A samurai, ninja or kunoichi travels the roads of old Japan. Pack your kit, grow stronger, and cut down
> the villain who rules each region, ending with **Lord Ashura, the Demon Shogun**.
> *("Shadow Road" is a working title.)*

## How to run
```
pip install -r requirements.txt
python main.py
```

---

## Research: what makes good classes, items, enemies and difficulty

**Classes**
- Slay the Spire's characters are "as asymmetrical as StarCraft's races": each has its own card pool and its own way to win. ([PC Gamer](https://pcgamer.com/slay-the-spire-review))
- Draw players in with a *fantasy* first and the mechanics second. Archetypes are tied to flavour. ([Game Developer: Archetypes in deckbuilding](https://gamedeveloper.com/design/archetypes-in-deckbuilding-games))
- Restricting which items a class can find keeps classes distinct. ([Wikipedia: Roguelike deck-building](https://www.wikipedia.com/wiki/Roguelite_deck-building))
- In Backpack Battles, each class has its own starting items and class-only items that push it towards particular builds. ([Wikipedia: Backpack Battles](https://en.wikipedia.org/wiki/Backpack_Battles))

**Enemies and bosses**
- Slay the Spire's core design is **risk versus reward**. Elites cost you HP now in exchange for a reward later. ([Game Developer: Road to the IGF](https://www.gamedeveloper.com/disciplines/road-to-the-igf-mega-crit-games-i-slay-the-spire-i-), [design tensions](https://saschb2b.github.io/game-mechanics/games/slay-the-spire/design-tensions))
- Hard bosses must be **readable**: give players the chance to recognise patterns and plan counters. Slay the Spire shows enemy intents for this reason. ([Game Developer: readability](https://www.gamedeveloper.com/game-platforms/designing-for-difficulty-readability-in-arpgs))
- Higher difficulty should add **new mechanics**, not just bigger numbers. ([Game-Wisdom](https://game-wisdom.com/?p=24881))

**Difficulty and balance**
- Mega Crit tracked win rates and pick rates for every card and balanced from the data. ([GDC 2019](https://gdconf.com/news/learn-slay-spires-successful-metrics-driven-approach-game-balancing-gdc-2019))
- Balance from the first level upward, and expect spikes that take several attempts to beat. ([Game Developer: hard roguelikes](https://www.gamedeveloper.com/design/the-challenges-of-designing-a-hard-roguelike-game))

### How this shaped Shadow Road
1. **Three fully different classes**, each with a unique passive, its own item pool and its own techniques.
2. **Each villain tests something.** Every boss and elite punishes one kind of weak build:
   - Kiyohime's burn and poison go straight past armor stacking.
   - Ashura's Shatter Command destroys all of your Block.
   - The Gashadokuro's thorns punish builds that rely on many small hits.
   - Evasive enemies punish builds that rely on a few big hits.
3. **Readability:** you see the boss's name on the map, read rumours about it before the stage, and hover elites and bosses to read their mechanics. Phase changes show a banner.
4. **Data-driven tuning:** a headless bot plays hundreds of runs and reports win rates and which enemies kill it (see *Balance* below).

---

## The 3 classes
| | **Samurai** | **Ninja** | **Kunoichi** |
|---|---|---|---|
| Fantasy | Masterless swordsman restoring his clan's honour | Iga shadow sent to stop the Demon Shogun | Entertainer by day, assassin by night |
| Style | Heavy blades, armor, gets stronger as the fight goes on | Speed, evasion, many small strikes | Poison, crits, stuns |
| HP | 60 | 60 | 70 |
| Passive | **Bushidō:** start with 6 Block. Each weapon hit builds Resolve (max 5), and each point gives +1 damage to every weapon hit | **Shinobi:** 20% evasion, and weapons trigger 15% faster | **Deadly Grace:** +5% crit, crits inflict 2 Poison, and her Poison ticks every 0.8s. Starts with 4 items |
| Key items | Katana, Nōdachi (stun), Ō-yoroi, Bushidō Scroll, Masamune's Edge | Shuriken, Smoke Bomb (Dodge), Kusarigama, Shadow Cloak, Fūma Shuriken (hits 3 times) | Kanzashi, Poisoned Tea, Sleeping Powder (stun), Shamisen, Fugu Venom |
| Nemesis | **Kiyohime:** burn and poison go straight through armor | **Kiyohime** and the **Gashadokuro** (thorns) | **Kurogane** (early burst) and **Ashura** (purges poison) |

**Techniques** are how your character grows stronger on the journey. Each class has 6. Beat an **elite or a boss** to learn 1 of 3 offered (for example Iaijutsu, Kawarimi or Allure). They last for the whole run.

## The journey and its villains
| Stage | Region | Enemies | Elites | Villain (boss) |
|---|---|---|---|---|
| 1 | **The Old Highway** | Highway Bandit, Kappa, Tanuki Trickster, Deserter Ashigaru | Rōnin Duelist (armor-breaking draw), Kamaitachi (whirlwind cuts) | **Kurogane, the Bandit Warlord**: at 50% HP he draws a second blade |
| 2 | **The Mist-Veiled Forest** | Kitsune, Jorōgumo, Kodama Grove, Karasu Tengu | Nue (thunder stun + poison), Rokurokubi (life drain) | **Kiyohime, the Serpent Bride**: at 50% HP she transforms into a fire-breathing serpent and heals |
| 3 | **Castle of the Demon Shogun** | Oni Brute, Gashadokuro, Shadow Clan Assassins, Possessed Samurai | The Tengu Lord, Hannya | **Lord Ashura, the Demon Shogun**: 3 phases (Shogun → Oni Guard → six-armed demon form). Each transformation purges all Poison and Burn, and Shatter Command removes all your Block |

## Enemy intents
In the style of Slay the Spire, every battle shows an **Enemy Intent** panel: the enemy's next 4 moves, with countdowns and labels (ATTACK 8-11, DEFEND 8, STUN 0.6s, POISON, BURN, HEAL, BREAK ARMOR, EVADE, DRAIN).
- The soonest move is highlighted.
- When the enemy is stunned, the panel says its moves are delayed.
- Bosses show **PHASE** markers on their HP bar and "Transforms at X HP", so you can time your burst and see the transformation coming.

## New combat mechanics
- **Evasion:** a % chance to completely avoid a hit. Capped at 60%.
- **Dodge:** charges, each of which completely avoids the next hit.
- **Stun:** freezes all of the target's items. After a stun, the target can't be stunned again for 2 seconds, so stun can't lock an enemy down permanently.
- **Multi-hit:** some weapons strike several times per trigger.
- **Resolve:** the Samurai's ramping damage.
- **Sunder:** destroys some or all of the target's Block.
- **Boss phases:** at set HP thresholds a boss adds moves, speeds up, gains Block or thorns, heals, or purges Poison and Burn.
- **Thorns** trigger once per attacking item, not once per strike. Multi-hit weapons are still punished by fast attackers, but no longer wiped out.

## Why it's harder now
- No free healing after fights. Onsens heal 30%, and moving to the next stage heals 30%.
- Enemies get +6% stronger for every map row you go deeper.
- Stages 2 and 3 have overall multipliers (×1.3 and ×1.35).
- Fatigue starts at 25s instead of 30s.
- Less starting gold, smaller rewards, and legendary items are unique (no duplicates).

## Balance (headless bot, 150 runs per class)
The bot buys the most expensive items it can and packs them without planning adjacency, so a thoughtful player should do somewhat better.

| Class | Wins | Deaths in stage 1 / 2 / 3 | Top killers |
|---|---|---|---|
| Samurai | 12% | 24 / 61 / 47 | Kiyohime, Ashura |
| Ninja | 15% | 29 / 70 / 28 | Kiyohime, Kurogane, Gashadokuro |
| Kunoichi | 12% | 43 / 40 / 49 | Ashura, Kurogane |

All three classes now win about the same share of runs, deaths are spread across all three stages, and each class has a different nemesis.

## Code layout
| File | What it does |
|---|---|
| `roguegame/data.py` | **All content and balance numbers:** items, classes, techniques, enemies, stages, difficulty settings |
| `roguegame/combat.py` | Deterministic battle sim (no pygame), ready for a future online server |
| `roguegame/run.py` | Run state, map generation, loot, techniques |
| `roguegame/inventory.py` | Grid, shapes, rotation, adjacency |
| `roguegame/events.py` | The 12 `?` events and their choices |
| `roguegame/sim.py` | Headless game driver and auto-packer, used by the AI |
| `roguegame/ai.py` | Reinforcement-learning agent |
| `tools/balance.py` | The Balance Director: train, measure, auto-tune, report |
| `roguegame/scenes.py`, `ui.py` | Screens and drawing (pixel art from `assets/art/`) |

## Classes 4 and 5
| | **Onmyōji** | **Sōhei** |
|---|---|---|
| Fantasy | Court diviner who binds spirits to paper | Warrior monk of Mount Hiei |
| Style | Summons, curses, slow build-up | Counter-attacks, Ki, endurance |
| HP | 55 | 72 |
| Passive | **Shikigami Pact:** starts every battle with a Paper Crane shikigami, and shikigami attack 25% faster | **Iron Faith:** each enemy attack that lands gives 1 Ki (max 12), and he strikes back for 1 + half his Ki |
| New mechanic | **Shikigami:** allies that fight all battle (up to 5; at the cap, new summons empower the army instead). **Curse:** the enemy deals 4% less damage per stack, up to 60%. **Hex:** deals damage per Curse stack | **Ki:** builds when he is hit or uses Ki items. **Ki Burst:** spends all Ki in one blow, and stuns at 6+ Ki. **Counter:** strikes back every time he is hit |

## Build paths
Every class has two archetypes. Each one is made of a **setup** item, an **engine** that boosts it, and a **payoff** that cashes it in. Shared items are glue that fit more than one build. The class-select screen shows these paths.

| Class | Build | Core items | How it works |
|---|---|---|---|
| Samurai | **Daishō swarm** | Daishō Pair, Hata-jirushi Standard, Katana-kake Rack | Daishō gets +1 damage per other weapon, and the Standard and Rack speed up weapons, so every weapon you add makes the others stronger |
| Samurai | **Iron fortress** | Ō-yoroi, Lacquered Sode, Tachi of Honour, Unbroken Banner | The Tachi gains damage for every armor piece, and the Banner boosts adjacent armor |
| Ninja | **Throwing swarm** | Shuriken, Kunai Bandolier, Grappling Hook, Katana-kake Rack | Many fast hits; the Bandolier scales with weapon count |
| Ninja | **Fire arts** | Fire Bomb, Oil Bomb Pouch, Lamp Oil Flask, Dragon Flame Jutsu | The Oil Bomb and Oil Flask add +1 Burn to adjacent fire items |
| Kunoichi | **Venom** | Poisoned Tea, Torikabuto Root, Nightshade Perfume, Fugu Venom | Stacking Poison, plus Curse so you survive while it works |
| Kunoichi | **Crit control** | Kaiken, Fan of Whispers, Hidden Needle Bracelet, Whetted Saya | Crits poison (from her passive and the Bracelet), and the Fan stuns |
| Onmyōji | **Spirit army** | Paper and Fox Shikigami, Spirit Brush, Seimei's Star | The Brush and Star boost adjacent summon items' speed and shikigami damage |
| Onmyōji | **Curse and hex** | Ofuda of Binding, Onmyō Compass, Crow Shikigami, Hex of Five Elements | Stack Curse (the Crow curses on every hit), then Hex hits for 3 per stack |
| Sōhei | **Iron faith** | Kesa Robe, Iron Geta, Fudō Myōō Idol | Counter-attack items plus Block and HP: get hit, hit back harder |
| Sōhei | **Ki burst** | Hand Bell, Heart Sutra, Great Temple Bell, Benkei's Seven Weapons | Ki items build Ki (the Sutra gives +1 Ki to adjacent Ki items), then the Temple Bell releases it all |

**Shared glue items:**

| Item | Builds it helps |
|---|---|
| Katana-kake Rack | Any weapon build |
| Whetted Saya, Hawk-Eye Charm | Crit builds |
| Lamp Oil Flask, Paper Lantern | Burn builds |
| Bamboo Palisade, Spiked Kote | Armor and thorns builds |
| Bentō Box, Lacquer Chopsticks | Food and sustain builds |
| Toad Venom Jar | Poison builds |
| Hachimaki Headband | Anything |
| Yata no Kagami (legendary) | Defence and crit builds |

**New item mechanics:**
- `per_tag`: +damage for each other item with a given tag in your kit.
- `s_crit_block` and `s_crit_poison`: crits also give Block or inflict Poison.
- `summon`, `curse`, `hex`, `ki`, `ki_burst` and `s_counter`: the new class mechanics above.
- Aura keys `summon_dmg` and `ki`: buff adjacent summon or Ki items.

The AI agent understands all of these. It also gets a "synergy" signal: how many items in your kit share tags with the item it's looking at.

## Keeping it running smoothly
- **Save and continue:** the game autosaves whenever the map opens. **Continue** on the title screen resumes the run, and finishing a run deletes the save. Saves are kept in `%APPDATA%\ShadowRoad\run.json` and written atomically, so a crash mid-save can't corrupt them.
- **Automated tests:** `python -m unittest discover tests` runs 17 checks in about 2 seconds. They cover:
  - every item's shape, levels, tooltip and art,
  - every enemy's moves, art and loot,
  - every class's kit, techniques and item pool,
  - determinism, merging, summons, curse, hex, Ki and counters, per-tag scaling and boss phases,
  - seeds, every event option, 40 full simulated runs, the save round-trip, and drawing every screen.
- **Windows .exe:** `powershell -ExecutionPolicy Bypass -File build_exe.ps1` runs the tests and then builds `dist\ShadowRoad\ShadowRoad.exe` (about 30 MB). Zip that folder to share the game; no Python needed.
- **`.gitignore`:** already in place for when you set up git. It excludes build output and the 90 MB art pack.

## Item levels (merging)
Drop a copy of an item onto an identical item at the same level to merge them. The result is level 2, then level 3 (the maximum). Each level:
- adds +50% to the item's numbers (damage, Block, heal, Poison, Burn and so on),
- makes it trigger 8% faster,
- improves its aura and its crit or evasion bonus.

Levelled items show gold dots in their corner. Some `?` events (the Swordsmith, the Old Well) can also level up an item.

## Enemy drops
Every enemy, elite and boss carries its own **enemy-drop item**, 31 in total. These are never sold in shops. Examples:
- Kappa → Kappa's Cucumber
- Oni → Oni Club, which breaks armor
- Orochi → Orochi's Eight Fangs

**How you get them:**
- **Regular fights:** the drop is always one of your three reward choices, marked *ENEMY DROP*.
- **Elites and bosses:** the drop is added to your chest for free, and then you still pick a reward.

## `?` events (12)
| Event | What it offers |
|---|---|
| Wandering Monk | Learn a technique, or heal |
| Kitsune no Yomeiri | Lose HP for a rare treasure, or gain max HP |
| Swordsmith's Forge | Pay to level up an item, or earn ryō |
| Haunted Bridge | Fight an elite, or lose HP going around |
| Roadside Tea House | Heal, or gamble |
| Cursed Shrine | Lose max HP for a legendary-tier item |
| Wandering Yokozuna | A sumo bout for his belt |
| Abandoned Battlefield | Find a weapon, or get ambushed |
| A Rōnin's Challenge | Duel him for his blade |
| Snow Monkey Spring | Heal and gain max HP, or steal their food |
| Merchant Caravan | Buy a mystery epic item |
| The Old Well | Gamble on healing or an item upgrade |

## Seeded runs
Every run has a seed, shown on the map screen. The seed decides:
- the map layout,
- **which 4 of each stage's 6 regular enemies appear**,
- **which of the stage's 2 villains you face**,
- the order of the `?` events (no repeats within a run).

| Stage | Villain A | Villain B (new) | New mobs |
|---|---|---|---|
| 1 | Kurogane, the Bandit Warlord | **Gama, the Toad Sage**: drains life, then vanishes into smoke | Mountain Boar, Rogue Yamabushi |
| 2 | Kiyohime, the Serpent Bride | **Yuki-onna, the Snow Woman**: freezing stuns, then a blizzard | Chōchin-obake, Hitodama Swarm |
| 3 | Lord Ashura, the Demon Shogun | **Yamata no Orochi**: more heads wake as it weakens, and each awakening purges your poison and burn | Niō Guardian Statue, Katon Ninja |

## Harder mobs
Regular enemies now hit 35% harder and have 35% more HP. Elites get +15%. Bosses are unchanged. The Balance Director (below) re-tunes these numbers automatically.

## The Balance Director (reinforcement learning)
`python tools/balance.py --autotune` runs the full process:
1. **Train:** each class gets a learning agent (`roguegame/ai.py`) that plays thousands of seeded runs through a headless copy of the game (`roguegame/sim.py`). It learns which paths, items, events, onsen choices and techniques lead to deeper runs. It's a linear softmax policy trained with REINFORCE (policy gradient). An auto-packer arranges its kit, merges duplicates and places aura items where they buff the most.
2. **Measure:** the trained agents play fresh seeds they never trained on. The tool records:
   - win rate,
   - which stage they died in,
   - which enemies kill them,
   - item pick rates, and win rates when an item is in the final kit (the same kind of data Slay the Spire's developers used).
3. **Tune:** it adjusts the knobs in `assets/balance.json` until three targets are met:
   - skilled-agent win rate is about 20%,
   - regular mobs and elites cause at least 30% of deaths,
   - no class is more than 7 points from the class average.

   The knobs are stage multipliers, mob, elite and boss multipliers, and per-class HP. After tuning it retrains the agents on the new difficulty.
4. **Report:** results go to `assets/balance_report.md`, and the trained agents are saved in `assets/ai/`. They could later serve as AI opponents for the online mode.

## Next ideas
- **Difficulty levels** (an "Ascension" ladder), each adding a new rule.
- **Class-shaped kits:** the Samurai gets a wide armor rack, the Ninja a narrow belt.
- **Item merges:** e.g. Katana + Whetstone → Honed Katana.
- **More villains per stage,** with one picked at random each run.
- **Online mode:** 5 lives, 10 wins, asynchronous ghosts.
