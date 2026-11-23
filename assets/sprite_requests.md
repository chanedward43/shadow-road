# Sprites needed

None right now: every item has its own sprite, and no two items share one
(`python tools/import_sprites.py --check` confirms it).

- Japanese gear (charms, armour, food, scrolls, tools, fans, kunai, needles...) is our own 16x16 pixel art:
  `tools/sprite_templates.py` holds the shapes, `tools/make_sprites.py` gives each item its colours (and an
  emblem for scrolls and ofuda). Run `python tools/make_sprites.py --sheet` to rebuild them and see a contact sheet.
- Katanas, daggers, polearms, staves, clubs and the hammer come from the CC0 "16x16 Weapon RPG Icons" sheets
  in `had/16x16_weapons_rpg_icons/`.

Adding an item: give it an entry in `CUSTOM` (a template + colours) or `SHEET` (a weapon-sheet cell) in
`tools/make_sprites.py`, then run it.
