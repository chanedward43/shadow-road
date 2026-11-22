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

## Development
| Task | Command |
|---|---|
| Run the tests | `python -m unittest discover tests` |
| Build the browser version | `python tools/build_web.py` |
| Build a Windows .exe | `powershell -ExecutionPolicy Bypass -File build_exe.ps1` |
| Train the AI and re-balance | `pip install numpy` then `python tools/balance.py --autotune` |

Game design, research notes and balance details are in [DESIGN.md](DESIGN.md).

## Credits
Art: [Ninja Adventure Asset Pack](https://pixel-boy.itch.io/ninja-adventure-asset-pack) by Pixel-Boy and AAA (CC0).
