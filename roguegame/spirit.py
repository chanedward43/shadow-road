"""Item spirits. Pure Python (no pygame).

SOUL FORGE (infusion): at a Kami Forge you sacrifice one item, and its *signature effect* is bound into
another item at half strength - a katana that poisons, armour that heals. One infusion per item, shown
as a gem. It survives merging and levelling.

TSUKUMOGAMI (awakening): in folklore, a tool used for long enough gains a soul. An item that has fought
in AWAKEN_BATTLES battles in your kit awakens, and HOW it was used decides what it becomes:
mostly damage -> Hundred Cuts (Grow), many crits -> Lightning (crits stun), lots of Block -> Unbreakable,
lots of healing -> Merciful, lots of Poison/Burn/Curse -> Vengeful, passive gear -> Guardian Spirit.
"""
from .data import ITEMS

AWAKEN_BATTLES = 8

# what can be passed on, most defining first (a poison weapon passes its Poison, not its damage)
ACTIVE_KEYS = ["poison", "burn", "curse", "hex", "stun", "heal", "regen", "block", "lifesteal", "steal_block",
               "cleanse", "dodge", "stamina_gain", "crit", "dmg"]
PASSIVE_KEYS = ["s_block", "s_hp", "s_regen", "s_thorns", "s_crit", "s_evade", "s_counter", "s_curse",
                "s_stamina", "s_stamina_regen"]
LABELS = {"poison": "Poison", "burn": "Burn", "curse": "Curse", "hex": "Hex", "stun": "Stun", "heal": "Heal",
          "regen": "Regen", "block": "Block", "lifesteal": "Lifesteal", "steal_block": "Steal Block",
          "cleanse": "Cleanse", "dodge": "Dodge", "stamina_gain": "Stamina", "crit": "crit", "dmg": "damage",
          "s_block": "starting Block", "s_hp": "Max HP", "s_regen": "starting Regen", "s_thorns": "Thorns",
          "s_crit": "crit", "s_evade": "evasion", "s_counter": "Counter", "s_curse": "starting Curse",
          "s_stamina": "max Stamina", "s_stamina_regen": "Stamina/s", "grow": "Grow", "crit_stun": "crit stun"}


def _half(key, v):
    if key == "dmg":
        return (max(1, v[0] // 2), max(1, v[1] // 2))
    if isinstance(v, float) and v < 1:
        return round(v / 2, 3)
    return max(1, round(v / 2))


def signature(d):
    """The sacrificed item's defining effect at half strength: {key: value}, or {} if it has none."""
    for k in ACTIVE_KEYS:
        if d.get(k) and d.get("cd"):
            return {k: _half(k, d[k])}
    for k in PASSIVE_KEYS:
        if d.get(k):
            return {k: _half(k, d[k])}
    return {}


def is_active(stats):
    return any(k in ACTIVE_KEYS for k in stats)


def can_infuse(src, dst):
    """(ok, reason) for pouring src's spirit into dst."""
    if src is dst:
        return False, "Choose two different items."
    if dst.infusion:
        return False, "Already holds a spirit (one per item)."
    sig = signature(src.data)
    if not sig:
        return False, "Has no spirit to give."
    if is_active(sig) and not ITEMS[dst.id].get("cd"):
        return False, "Needs an item that acts (has a timer) to use this spirit."
    return True, ""


def infuse(src, dst):
    """Bind src's signature into dst. The caller removes src from the run."""
    dst.infusion = dict(src=src.id, stats=signature(src.data))
    dst.refresh()


def add_stats(st, extra):
    for k, v in extra.items():
        if k == "dmg":
            cur = st.get("dmg") or (0, 0)
            st["dmg"] = (cur[0] + v[0], cur[1] + v[1])
        else:
            st[k] = round(st.get(k, 0) + v, 3) if isinstance(v, float) else st.get(k, 0) + v
    return st


def fmt(stats):
    out = []
    for k, v in stats.items():
        if k == "dmg":
            out.append(f"+{v[0]}-{v[1]} damage")
        elif k in ("crit", "s_crit", "s_evade", "lifesteal", "crit_stun") and isinstance(v, float) and v < 1:
            out.append(f"+{int(round(v * 100))}% {LABELS.get(k, k)}" if k != "crit_stun" else f"crits stun {v:g}s")
        elif k == "stun":
            out.append(f"+{v:g}s Stun")
        else:
            out.append(f"+{v:g} {LABELS.get(k, k)}")
    return ", ".join(out)


# ---------------------------------------------------------------- tsukumogami
AWAKENINGS = {
    "blade": dict(title="{name} of the Hundred Cuts", stats={"grow": 1, "crit": 0.05},
                  desc="Grows +1 damage with every hit, +5% crit."),
    "storm": dict(title="Lightning {name}", stats={"crit_stun": 0.3, "crit": 0.05},
                  desc="Its crits stun for 0.3s, +5% crit."),
    "guard": dict(title="Unbreakable {name}", stats={"block": 3, "s_thorns": 3},
                  desc="+3 Block each time it acts, +3 Thorns."),
    "mercy": dict(title="Merciful {name}", stats={"heal": 2, "cleanse": 2},
                  desc="Also heals 2 and cleanses 2 Poison/Burn."),
    "venom": dict(title="Vengeful {name}", stats={},
                  desc="+1 to every Poison, Burn or Curse it inflicts."),
    "kami": dict(title="{name}, Guardian Spirit", stats={"s_hp": 8, "s_block": 4},
                 desc="+8 Max HP and +4 starting Block."),
}


def awaken_type(inst):
    """Decide what an item becomes from how it was actually used."""
    u = inst.usage
    if not ITEMS[inst.id].get("cd") or not u.get("uses"):
        return "kami"
    status = u.get("poison", 0) + u.get("burn", 0) + u.get("curse", 0)
    if u.get("crits", 0) >= max(6, 0.25 * u.get("uses", 0)):
        return "storm"
    scores = {"blade": u.get("dmg", 0), "guard": u.get("block", 0), "mercy": u.get("heal", 0) * 1.5,
              "venom": status * 3}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "kami"


def awakening_stats(inst):
    kind = inst.awakened
    if kind == "venom":
        d = level_base(inst)
        return {k: 1 for k in ("poison", "burn", "curse") if d.get(k)} or {"poison": 1}
    return dict(AWAKENINGS[kind]["stats"])


def level_base(inst):
    from .data import level_stats
    return level_stats(ITEMS[inst.id], inst.level)


def overlay(inst, st):
    """Apply infusion and awakening on top of an item's level stats (used by ItemInst.data)."""
    if inst.infusion:
        add_stats(st, inst.infusion["stats"])
    if inst.awakened:
        add_stats(st, awakening_stats(inst))
        st["name"] = AWAKENINGS[inst.awakened]["title"].format(name=st["name"])
    return st


def record(inst, ci_stats):
    """Count one battle for this item. ci_stats: what it did this battle (None for passive gear).
    Returns True if it just awakened."""
    inst.battles += 1
    for k, v in (ci_stats or {}).items():
        if isinstance(v, (int, float)):
            inst.usage[k] = inst.usage.get(k, 0) + v
    if not inst.awakened and inst.battles >= AWAKEN_BATTLES:
        inst.awakened = awaken_type(inst)
        inst.refresh()
        return True
    return False


def describe(inst):
    """Extra tooltip lines about an item's spirit."""
    out = []
    if inst.infusion:
        out.append(f"Soul-bound: {fmt(inst.infusion['stats'])} (spirit of {ITEMS[inst.infusion['src']]['name']}).")
    if inst.awakened:
        out.append(f"Tsukumogami - {AWAKENINGS[inst.awakened]['desc']}")
    else:
        out.append(f"Awakens after {AWAKEN_BATTLES - inst.battles} more battle"
                   f"{'s' if AWAKEN_BATTLES - inst.battles != 1 else ''} in your kit.")
    return " ".join(out)


def merge_into(keep, consume):
    """Merging two copies keeps the best of both spirits."""
    if not keep.infusion and consume.infusion:
        keep.infusion = consume.infusion
    if not keep.awakened and consume.awakened:
        keep.awakened = consume.awakened
    keep.battles = max(keep.battles, consume.battles)
    for k, v in consume.usage.items():
        keep.usage[k] = keep.usage.get(k, 0) + v
    keep.refresh()
