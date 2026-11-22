"""Effect keywords: their colour, and what they do (shown when you hover them). Pure Python."""
import re

# key -> (display name, colour, one-line definition)
KEYWORDS = {
    "block": ("Block", (110, 165, 240), "Absorbs damage before your HP. Poison ignores it."),
    "poison": ("Poison", (130, 210, 80), "Deals its stacks as damage every second. Ignores Block and never wears off."),
    "burn": ("Burn", (245, 145, 60), "Deals its stacks as damage every second, then drops by 1."),
    "regen": ("Regen", (100, 220, 140), "Heals its stacks every second."),
    "heal": ("Heal", (100, 220, 140), "Restores HP, up to your maximum."),
    "thorns": ("Thorns", (215, 125, 125), "Damages anyone whose attack hits you."),
    "stun": ("Stun", (240, 205, 90), "Freezes all of the target's items. After a stun, it can't be stunned again for 2s."),
    "dodge": ("Dodge", (190, 190, 255), "Each charge completely avoids the next attack."),
    "evasion": ("Evasion", (190, 190, 255), "A chance to completely avoid each attack (max 60%)."),
    "crit": ("Crit", (255, 120, 120), "A critical hit deals double damage."),
    "lifesteal": ("Lifesteal", (220, 90, 150), "Heals you for part of the damage dealt."),
    "curse": ("Curse", (175, 125, 225), "The cursed fighter deals 5% less damage per stack (max 50%)."),
    "hex": ("Hex", (195, 140, 235), "Deals damage for every Curse stack on the enemy. Ignores Block."),
    "ki": ("Ki", (255, 200, 120), "Sōhei: builds when hit. Powers counter-attacks and Ki Bursts."),
    "shikigami": ("Shikigami", (120, 210, 230), "An ally spirit that attacks on its own for the whole battle (max 5)."),
    "counter": ("Counter-attack", (255, 170, 90), "Strikes back whenever an enemy attack lands on you."),
    "grow": ("Grow", (255, 120, 90), "This weapon gains damage every time it hits, for the rest of the battle."),
    "steal": ("Steal", (150, 180, 255), "Takes the enemy's Block and adds it to yours."),
    "cleanse": ("Cleanse", (200, 255, 200), "Removes your own Poison and Burn."),
    "resolve": ("Resolve", (235, 195, 95), "Samurai: each stack adds +1 damage to every weapon hit."),
    "ambush": ("Ambush", (255, 230, 120), "Ninja: after an evade, the next weapon hit deals double damage."),
    "sunder": ("Armor break", (150, 180, 255), "Destroys part of the enemy's Block."),
    "speed": ("Speed", (160, 220, 255), "Makes adjacent items trigger more often."),
    "stamina": ("Stamina", (120, 230, 200), "Weapons spend it to swing (5 max, refills 1 per second). "
                                             "Without enough, a weapon waits."),
}

BASE_COLOURS = {k: v[1] for k, v in KEYWORDS.items()}   # ui.apply_palette swaps some for colour-blind mode

# words (lower case, punctuation stripped) that mean each keyword
ALIASES = {
    "block": "block", "poison": "poison", "burn": "burn", "regen": "regen", "heal": "heal", "heals": "heal",
    "thorns": "thorns", "stun": "stun", "stuns": "stun", "stunned": "stun", "dodge": "dodge",
    "evasion": "evasion", "evade": "evasion", "crit": "crit", "crits": "crit", "lifesteal": "lifesteal",
    "curse": "curse", "hex": "hex", "ki": "ki", "shikigami": "shikigami", "summon": "shikigami",
    "counter-attack": "counter", "counter": "counter", "grow": "grow", "steal": "steal", "cleanse": "cleanse",
    "resolve": "resolve", "ambush": "ambush", "destroy": "sunder", "speed": "speed", "stamina": "stamina",
}

_WORD = re.compile(r"[A-Za-zōŌū\-]+")


def keyword_of(word):
    m = _WORD.search(word)
    return ALIASES.get(m.group(0).lower().strip("-")) if m else None


def keywords_in(text):
    """Keyword keys mentioned in a text, in order of first appearance."""
    out = []
    for w in text.split():
        k = keyword_of(w)
        if k and k not in out:
            out.append(k)
    return out
