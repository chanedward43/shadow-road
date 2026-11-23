# Shadow Road

A pack-building roguelike set in old Japan. Choose a Samurai, Ninja, Kunoichi, Onmyōji or Sōhei,
arrange your kit on the tatami grid, and fight through three stages of yokai and villains in
automatic battles. Item placement matters: adjacent items buff each other, and duplicates merge
into stronger versions.

**Play in your browser:** see the GitHub Pages link in this repository's About section
(the game is rebuilt and published automatically on every push to `main`).

## Run it on your computer
```
pip install pygame-ce
python main.py
```

## Controls
- Click map nodes to travel. Click or drag items to move them in your kit.
- Right-click, **R** or the mouse wheel rotates the item you're holding.
- Drop an item on an identical one to merge it (up to level 3). Drop it on **PAWN** to sell.
  Every tooltip shows what an item sells for (half its price, times its level).
- **Map (M)** button on every screen (shop, rewards, events, battles): check the road ahead, then
  press M, Esc or Back to return where you were.
- In battle: 1x / 2x / 4x speed, or Skip. Both kits are shown as real grids: shaded items are still
  charging, flashes are activations, and xN counts uses. Hover an item for what it has done this battle,
  or a status (Block, Poison...) for what it means. The battle log lists every activation.
- After a battle: a breakdown of what every item did, and **Replay** to watch the same fight again.
- Effect words (Poison, Burn, Stun...) are coloured and italic in tooltips, with definitions underneath.
- **Stamina** (teal bar): every weapon swing costs Stamina (5 max, refills 1 per second). A weapon
  that is charged but can't pay glows teal and waits. Food, Matcha Tea, Ginseng, Waraji and the
  Breathing Scroll keep it flowing. The top of the battle shows **Fight time**: the battle's own clock,
  the same at any speed (fatigue starts at 25s). At 2x/4x it also shows how long you actually watched.
- **Match History** (title screen, and after every run): **Adventure** and **Arena** tabs. Adventure runs
  (story and endless) show the path, final kit, techniques and what killed you; Arena runs show every
  fight (hover a round for the opponent), wins, losses and your final kit. Click a class to filter, and **Play this seed** to retry the same
  map. On the website it is stored in your browser, so it survives game updates (but not clearing
  your browser's site data); on desktop it is in `%APPDATA%\ShadowRoad`.
- Every new run gets a random seed (from the clock and your mouse position).
- **Sound & music** (Ninja Adventure pack, CC0): hits, crits, blocks, heals, boss phases, plus music for the
  title, map, battles, bosses, the Blood Moon and the Arena. Crits and boss transformations shake the screen.
- **Settings** (title screen): music and sound volume, default battle speed, screen shake, a colour-blind
  palette (heals blue, poison purple, damage vermillion) and first-time tips.
- **Achievements** (title screen): 16 achievements plus lifetime stats (kills, nemesis, favourite items).
- **Ascension**: win a story run to unlock Ascension 1 for that class, then the next level each win, up to
  A10. Pick it with the < > arrows on the class select. Each level adds one rule on top of the last
  (stronger elites, pricier shops, stronger bosses, less HP, regenerating elites, weaker onsen, stronger
  mobs, a boss last-stand phase, less gold, and finally the Blood Moon over stage 3).
- **Conditional items**: some items trigger on events instead of a timer: when an adjacent item crits
  (Echo Blade, Ringing Tsuba), every N times you gain Block (Patient Tetsubō), every N hits you take
  (Wara Doll, Mask of Spite), every N heals (Inrō). The Lone Wolf Tantō hits harder with nothing next to it,
  and the Glutton's Hashi grows with every Food item.
- **Economy items** (only while in your kit): Maneki-neko (+ryō per win), Silk Coin Purse (interest),
  Merchant's Soroban (cheaper shops), Pirate's Treasure Map (+ryō per boss).
- **Consumables**: merchants also sell 2 consumables (top right of the shop). They are used up in your
  NEXT battle (hold up to 3, shown under your kit): tonic, iron skin elixir, smoke pellets, explosive tag,
  herbal salve, swift wind charm, antidote, fortune omikuji.
- **Story threads**: some choices come back later. Free (or rob) the trapped tanuki in stage 1, save (or rob)
  the wounded rōnin in stage 2 - an **Omen** node appears on the next stage's map with the payoff.
- **Risky events**: the Oni's Bargain, the Champion's Grave (a hard fight for a legendary), the Monk of Empty
  Mind (sell a technique), High-Stakes Dice and the Veiled Merchant.
- While holding an item, a **Rotate** button appears bottom-right (handy on touch screens). On a touch screen, a quick tap picks an item up; press and hold to read its tooltip.
- **Weapons merge up to level 5** (other items to 3). Levels 4 and 5 add a little less each.
- **Recipes**: put two ingredients next to each other in your kit; when you leave the bag/shop screen they fuse
  into a unique item (never sold in shops). Hover an ingredient to see its recipe; matching neighbours glow gold.
  Katana + Whetstone, Dō Armor + Kasa Hat, Shuriken + Kunai, Fire Bomb + Oil Flask, Iron Fan + Smoke Bomb,
  Poisoned Tea + Fukiya, Ofuda + Paper Shikigami, Temple Naginata + Kesa Robe, Onigiri + Sake Gourd,
  Bō Staff + Ofuda, Maneki-neko + Coin Purse.
- **Soul Forge** (the *Kami Forge* `?` event, for ryō or blood; a rare free node on Arena floors): sacrifice one
  item and pour its signature effect, at half strength, into another - a katana that Burns, armour that
  heals. One spirit per item (a purple gem); it survives merging and levelling.
- **Tsukumogami**: in folklore, a tool used long enough gains a soul. Every item that fights in 8 battles in
  your kit **awakens** (glowing outline, new name), shaped by how you used it: mostly damage -> *of the
  Hundred Cuts* (Grow +1, +5% crit); lots of crits -> *Lightning* (crits stun); lots of Block -> *Unbreakable*;
  lots of healing -> *Merciful*; Poison/Burn/Curse -> *Vengeful*; passive gear -> *Guardian Spirit*.
  Hover an item to see how many battles it still needs.
- **Compendium** (title screen): every item, enemy and recipe; undiscovered ones are dark silhouettes.
- **Battles** animate: items bounce when they fire, the attacker lunges, the target shakes, and coloured
  particles show hits, poison, burn, block and heals. Events are painted scenes with a typewriter reveal.
- **End screen**: MVP item, damage by item, the final kit, techniques and the run's numbers.
- **Hotkeys**: Space = skip / continue, 1 / 2 / 4 = battle speed.
- **Mute**: the speaker button in the top-right corner of every screen. **Settings** also has *Larger text*.
- **Endless** unlocks after you beat the story once. **Arena runs** are saved: refresh and pick *Resume run*
  (leaving during a ghost duel counts as a loss). On the website, music streams in when first played, so the
  game itself loads faster.

## Development
| Task | Command |
|---|---|
| Run the tests | `python -m unittest discover tests` |
| Build the browser version | `python tools/build_web.py` |
| Build a Windows .exe | `powershell -ExecutionPolicy Bypass -File build_exe.ps1` |
| Train the AI and re-balance | `pip install numpy` then `python tools/balance.py --autotune` |

Game design, research notes and balance details are in [DESIGN.md](DESIGN.md).

## Endless mode
Pick **Endless** (bottom-right of the class select). It plays like Story until Lord Ashura or Orochi falls,
then the road goes on: **stage 4 Yomi Pass**, **stage 5 Blood Moon over Kyō** (a big difficulty jump, and
every enemy is enraged: +10% crit, items 10% faster), then **The Endless Night** - harder every stage.
New yokai join the pools (Gaki, Nurikabe, Kasha, Onryō, Yamauba, Ittan-momen), plus the elites Ushi-oni
and Raijū and three new villains: **Shuten-dōji**, **Tamamo-no-Mae** and **Enma, King of Yomi**.
From stage 4 you gain *Second Wind* (max HP each stage), two new late-game techniques per class unlock, and
Samurai/Sōhei get endless passives (they scaled worst in testing). Match History shows how deep you got.
`python tools/endless_report.py` measures how far the trained AI gets per class.

## Arena (online ghost PvP)
**Arena (online)** on the title screen: shop and arrange your kit each round, then fight the
*ghost* of another player's kit from the same round of the same game version. Win 10 fights to be
champion; 5 losses and you're out. Each round is a random floor of 5 choices, like the adventure map: practice fights and elites (losing one costs nothing - you just get no rewards), shrines, events, a forge, a bounty and a dojo, then a merchant, and the round ends with the ghost duel instead of a boss. Your kit is uploaded as a ghost each round so others fight you.
When nobody has played a round yet (or you're offline) you face an AI ghost instead.

The website itself stays on GitHub Pages; ghosts and the leaderboard live in a free **Supabase**
database. Until it's set up the Arena simply runs offline against AI ghosts.

**Switch it on (one time, ~10 minutes):**
1. Create a free account and a new project at [supabase.com](https://supabase.com) (any name and region).
2. In the project: **SQL Editor -> New query**, paste all of [tools/supabase_setup.sql](tools/supabase_setup.sql),
   press **Run**. This makes the `ghosts` and `scores` tables and the rules: players can only
   *add* and *read* - never edit or delete.
3. **Project Settings -> API**: copy the **Project URL** and the **anon public** key.
4. Create `assets/online.json`:
   ```json
   {"url": "https://YOUR-PROJECT.supabase.co", "key": "YOUR-ANON-PUBLIC-KEY"}
   ```
   The anon key is designed to be public (it ships inside the web page); the rules from step 2
   protect the data. Never put the **service_role** key here.
5. Commit and push. The lobby should now say "Online" and show the leaderboard.

Notes: opponents only come from the same `VERSION`, so bumping the version starts a fresh ghost pool
and leaderboard (balance changes can't make old ghosts unfair). Clients are trusted, so a determined
cheater could upload a fake kit; Supabase lets you delete rows by hand in **Table Editor**.
The free tier pauses a project after a week with no visitors; open the dashboard to wake it.

## Versions
The version is shown bottom-left on every screen and saved with each run in Match History. Bump
`VERSION` in [roguegame/version.py](roguegame/version.py) before pushing:
**+0.01** hotfix or number tweaks, **+0.1** new items / UI / character changes, **+1** a new season.
While in beta it shows `Beta v1.xx`. When the game goes live, set `BETA = False`; the number keeps counting.

## Run the reinforcement learning yourself
The **Balance Director** (`tools/balance.py`) trains one AI agent per class, measures how often a
skilled agent wins, and tunes the difficulty knobs in `assets/balance.json`. It runs on the CPU
(numpy only, no GPU needed) and uses 5 worker processes.

**1. One-time setup** (in a terminal, in the project folder):
```
pip install pygame-ce numpy
```

**2. Pick a command:**

| What you want | Command | Time (roughly) |
|---|---|---|
| Just measure the current balance (reuse trained agents) | `python tools/balance.py --skip-train --eval 200` | 1-3 min |
| Re-tune difficulty with the existing agents | `python tools/balance.py --skip-train --autotune --eval 200 --checkpoint` | 3-10 min |
| Full retrain + tune | `python tools/balance.py --episodes 2000 --eval 200 --autotune --rounds 6 --checkpoint` | 15-30 min |

Flags: `--episodes` = training runs per class (more = smarter agents, slower), `--eval` = test runs
per class (more = more accurate %), `--target 0.20` = desired win rate for a skilled player,
`--rounds` = max tuning rounds, `--checkpoint` = stop at the first balanced point,
`--seed N` = repeat an earlier run exactly (by default every run picks fresh random seeds and prints
them, so the AI sees new maps, enemy casts and shops each time - like real players), `--fresh` = train
new agents from scratch instead of continuing from the saved ones. The balancer keeps every class within
3 points of the average win rate.

**Do I need to retrain?** Usually not. The agents describe every choice by *what it does* (damage,
Block, Poison, gold, healing, items, fights...), never by its name, so the trained agents already
understand new content built from existing effects:

| You changed... | Run |
|---|---|
| Numbers (damage, prices, HP, enemy stats) | `--skip-train --autotune` |
| New items using existing effects | `--skip-train --autotune` |
| New `?` events (tag each option in `events.FX`, e.g. `dict(gold=-10, item=3)`) | `--skip-train --autotune` |
| New techniques made of existing modifiers | `--skip-train --autotune` |
| A brand-new KIND of effect or rule (a new mechanic) | full retrain (it trains on top of the saved agents) |

A test (`TestAIFeaturesAreFutureProof`) fails if an event option is missing its tags or an item has an
effect the AI can't see, so you'll know when something needs a feature.

**Run report (Excel, one per patch):** `python tools/run_report.py --runs 200` (or add `--report 200` to any
`balance.py` command). The trained AI plays 200 runs per class and writes `reports/v<version>/`:
`run_report_v<version>.xlsx` with sheets for the summary per class, every run (where it ended - stage and
floor - what killed it, the final board, MVP item, techniques, events, recipes, spirits), every item (pick
rate and win-rate change when a run ends holding it), every enemy (how often it kills the player and how
much HP it costs), events and techniques - plus `wins/<class>_<seed>.png`, a picture of every winning
board (also embedded in the workbook). Only the newest patch's report is kept: writing a new one deletes the
older `reports/v*` folders (they stay in git history). Use it to tune items, enemies and events, not just class HP.

**3. Read the results:** the terminal prints each round's win rate per class. Afterwards look at
`assets/balance_report.md` (win rates, what killed runs, best/worst items) and `assets/balance.json`
(the knobs). Stop it any time with Ctrl+C; the last finished round is already saved.

**4. Ship it:** play a run with `python main.py` to sanity-check, run the tests, then commit and push
`assets/balance.json`, `assets/balance_report.*` and `assets/ai/`. GitHub Actions rebuilds the website
with the new balance automatically.
```
git add assets
git commit -m "Rebalance"
git push
```

You can also hand-edit `assets/balance.json` (e.g. lower `boss_mult` to make bosses weaker, or raise a
class's `class_hp`) and just restart the game - no training needed.

## Credits
Art, sound effects and music: [Ninja Adventure Asset Pack](https://pixel-boy.itch.io/ninja-adventure-asset-pack) by Pixel-Boy and AAA (CC0). `python tools/import_audio.py` re-imports the audio (needs ffmpeg).
