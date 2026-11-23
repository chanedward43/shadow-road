"""Reinforcement-learning agent that learns to play Shadow Road (numpy, no pygame).

Method: a linear softmax policy for each decision type (map path, item picks/buys,
onsen, ? events, techniques), trained with REINFORCE (policy gradient) and a running
baseline. Each option is turned into a feature vector; the policy scores options with
learned weights and samples from softmax(scores). After a run ends, every decision in
that run is nudged towards (or away from) what it chose, in proportion to how much
better (or worse) the run went than average.

Packing items onto the grid is handled by sim.pack (a heuristic), so the agent focuses
on strategy: which path to walk, what to buy, which loot to take, when to heal.
"""
import numpy as np

from .data import ITEMS, RARITIES, CHARACTERS, TECHNIQUES, weapon_stamina_cost
from .events import EVENT_BY_ID, option_fx
from .sim import STOP, play

# Every feature list below is FIXED-SIZE and describes options by what they do, never by their name or
# position in a content list. New items, events (tag their options in events.FX) and techniques (made of
# existing modifiers) therefore don't change the shapes, and trained agents keep working - a quick
# `balance.py --skip-train --autotune` is enough. Only a brand-new KIND of effect needs a new feature.
KINDS = ["fight", "elite", "shop", "rest", "treasure", "event", "boss"]
KIND_ALIAS = {"omen": "event", "soul": "event", "forge": "treasure", "bounty": "treasure", "dojo": "rest"}
TAGS = ["weapon", "armor", "food", "poison", "fire", "charm", "tool", "scroll", "summon", "curse", "ki"]
EVENT_KEYS = ["gold", "hp", "max_hp", "item", "tech", "upgrade", "fight", "risk", "forge", "future"]
TECH_KEYS = {   # technique modifier -> typical size (features are value / size)
    "max_hp": 15, "weapon_dmg": 2, "crit": 0.1, "evade": 0.1, "s_block": 15, "dodge": 2, "weapon_speed": 0.15,
    "first_strike": 3, "resolve_max": 4, "item_burn": 2, "item_poison": 1, "poison_on_crit": 2,
    "enemy_slow": 0.12, "weapon_lifesteal": 0.15, "summon_dmg": 2, "extra_summon": 1, "item_curse": 1,
    "summon_curse": 1, "ki_max": 6, "counter": 2, "ki_start": 4, "ki_burst_bonus": 1}
# item stat keys the item features already understand; anything else counts in a catch-all "other" slot
KNOWN_ITEM_KEYS = {
    "id", "name", "shape", "rarity", "tags", "cls", "price", "enemy", "loot", "recipe", "cd", "dmg", "hits",
    "block", "heal", "poison", "burn", "stun", "dodge", "s_evade", "crit", "s_crit", "s_block", "s_hp",
    "lifesteal", "summon", "curse", "hex", "ki", "ki_burst", "s_counter", "s_curse", "per_tag", "s_crit_block",
    "s_crit_poison", "grow", "steal_block", "cleanse", "stamina_cost", "stamina_gain", "s_stamina",
    "s_stamina_regen", "gold_per_win", "interest", "gold_per_boss", "discount", "trigger", "n", "alone_dmg",
    "aura", "regen", "s_regen", "s_thorns", "speed", "level", "adj", "sunder"}


def _state(run):
    return [run.hp / max(1, run.max_hp), min(run.gold, 40) / 20.0, run.stage / 3.0]


def item_features(iid, run):
    if iid == STOP:
        f = np.zeros(ITEM_DIM)
        f[0] = 1.0
        f[1:4] = _state(run)
        return f
    d = ITEMS[iid]
    same = sum(1 for i in run.all_items() if i.id == iid and i.level == 1)
    dmg = (sum(d["dmg"]) / 2) * d.get("hits", 1) / d["cd"] if d.get("dmg") and d.get("cd") else 0.0
    per = lambda k: d.get(k, 0) / d["cd"] if d.get("cd") else 0.0
    f = [0.0, *_state(run), 1.0]
    f += [1.0 if d["rarity"] == r else 0.0 for r in RARITIES]
    f += [1.0 if d["cls"] else 0.0, float(same), 1.0 if d.get("loot") else 0.0,
          len(d["shape"]) / 6.0, d["price"] / 20.0]
    f += [1.0 if t in d["tags"] else 0.0 for t in TAGS]
    f += [1.0 if d.get("aura") else 0.0, dmg / 5.0, per("block") / 3.0, per("heal") / 2.0,
          per("poison") / 1.5, per("burn") / 1.5, d.get("stun", 0), per("dodge"),
          d.get("s_evade", 0) * 5, d.get("crit", 0) * 5 + d.get("s_crit", 0) * 5,
          (d.get("s_block", 0) + d.get("s_hp", 0)) / 20.0, d.get("lifesteal", 0) * 2]
    f += [run.hp / max(1, run.max_hp) * (per("heal") / 2.0)]   # healing matters more when hurt
    sm = d.get("summon")
    f += [((sum(sm["dmg"]) / 2) / sm["cd"]) / 3.0 if sm else 0.0, per("curse"), d.get("hex", 0) / 3.0,
          per("ki"), d.get("ki_burst", 0) / 3.0, (d.get("s_counter", 0) + d.get("s_curse", 0)) / 3.0,
          d["per_tag"][1] * _tag_count(run, d["per_tag"][0]) / 5.0 if d.get("per_tag") else 0.0,
          (d.get("s_crit_block", 0) + d.get("s_crit_poison", 0)) / 3.0,
          _synergy(iid, run),
          d.get("grow", 0) / 1.5 + d.get("steal_block", 0) / 5.0 + d.get("cleanse", 0) / 3.0 + d.get("sunder", 0),
          (weapon_stamina_cost(d) / d["cd"]) if d.get("cd") else 0.0,
          per("stamina_gain") + d.get("s_stamina", 0) / 3.0 + d.get("s_stamina_regen", 0)]
    f += [_economy(d), _trigger_power(d), d.get("alone_dmg", 0) / 5.0, _other(d)]
    return np.array(f)


def _other(d):
    """Catch-all for effects the features don't know yet: a new mechanic still registers as 'something'."""
    return sum(1 for k, v in d.items() if k not in KNOWN_ITEM_KEYS and v) / 2.0


def _economy(d):
    """Roughly: ryō per battle this item earns (or saves)."""
    return (d.get("gold_per_win", 0) + d.get("interest", 0) / 5.0 + d.get("gold_per_boss", 0) / 4.0
            + d.get("discount", 0) * 15) / 4.0


def _trigger_power(d):
    """Conditional items: how much one trigger does, divided by how rarely it fires."""
    if not d.get("trigger"):
        return 0.0
    one = (sum(d["dmg"]) / 2 if d.get("dmg") else 0) + d.get("block", 0) + d.get("heal", 0) * 2 \
        + d.get("curse", 0) * 3 + d.get("hex", 0) * 3
    every = d.get("n") or 3
    return one / every / 4.0


def _tag_count(run, tag):
    return sum(1 for i in run.bag.items if tag in i.data["tags"])


def _synergy(iid, run):
    """How many items you already own share a tag with this one (builds reward focus)."""
    tags = set(ITEMS[iid]["tags"]) - {"charm", "tool"}
    return sum(1 for i in run.bag.items if tags & set(i.data["tags"])) / 6.0


ITEM_DIM = 4 + 1 + 4 + 5 + len(TAGS) + 12 + 1 + 12 + 4


def path_features(kind, run):
    s = _state(run)
    one = np.zeros(len(KINDS) * 4)
    kind = KIND_ALIAS.get(kind, kind)
    k = KINDS.index(kind) if kind in KINDS else KINDS.index("event")    # unknown node kinds read as events
    one[k * 4:(k + 1) * 4] = [1.0, *s]
    return one


def rest_features(choice, run):
    f = np.zeros(4)
    f[choice * 2:(choice + 1) * 2] = [1.0, run.hp / max(1, run.max_hp)]
    return f


def event_features(label, run):
    """An event option described by its effects (events.FX), so any event - even a brand-new one - can be
    judged: gold, healing (worth more when hurt), max HP, items, techniques, fights (better when healthy)..."""
    ev = EVENT_BY_ID.get(label.rsplit(":", 1)[0])
    fx = option_fx(label, ev)
    hpr = run.hp / max(1, run.max_hp)
    g = fx.get("gold", 0)
    hp = fx.get("hp", 0)
    fight = fx.get("fight", 0) / 2.0
    return np.array([
        1.0, g / 20.0, (g / 20.0) * (1.0 if run.gold < 15 else 0.5),       # gold matters more when poor
        hp, max(hp, 0) * (1 - hpr), min(hp, 0) * (1 - hpr),                  # heals when hurt / losses when low
        fx.get("max_hp", 0) / 10.0, fx.get("item", 0) / 4.0, fx.get("tech", 0), fx.get("upgrade", 0),
        fight, fight * hpr, fx.get("risk", 0), fx.get("forge", 0), fx.get("future", 0),
        1.0 if not fx else 0.0, run.stage / 3.0])


EVENT_DIM = 17


def tech_features(tid, run):
    """A technique described by its modifiers (scaled to their typical size) + a catch-all for new ones."""
    d = TECHNIQUES.get(tid, {})
    f = [1.0] + [d.get(k, 0) / size for k, size in TECH_KEYS.items()]
    f.append(sum(1 for k, v in d.items() if k not in TECH_KEYS and isinstance(v, (int, float))
                 and not isinstance(v, bool)) / 2.0)
    return np.array(f)


TECH_DIM = 1 + len(TECH_KEYS) + 1


FEATURES = {
    "item": (item_features, ITEM_DIM),
    "path": (path_features, len(KINDS) * 4),
    "rest": (lambda o, r: rest_features(0 if o == "heal" else 1, r), 4),
    "event": (event_features, EVENT_DIM),
    "tech": (tech_features, TECH_DIM),
}


class LearningAgent:
    """Linear softmax policy per decision kind, trained with REINFORCE."""

    def __init__(self, char_id, seed=0, lr=0.03):
        self.char_id = char_id
        self.rng = np.random.default_rng(seed)
        self.lr = lr
        self.w = {k: np.zeros(dim) for k, (_, dim) in FEATURES.items()}
        self.baseline = 0.0
        self.greedy = False
        self.trace = []

    def choose(self, kind, options, run):
        fn, _ = FEATURES[kind]
        phi = np.array([fn(o, run) for o in options])
        scores = phi @ self.w[kind]
        p = np.exp(scores - scores.max())
        p /= p.sum()
        i = int(np.argmax(p)) if self.greedy else int(self.rng.choice(len(options), p=p))
        if not self.greedy:
            self.trace.append((kind, phi, p, i))
        return i

    @staticmethod
    def score(result):
        """Reward: how far the run got. Winning is worth the most."""
        return (result["stage"] - 1) * 1.0 + result["battles"] * 0.08 + (2.0 if result["win"] else 0.0)

    def learn(self, result):
        r = self.score(result)
        adv = r - self.baseline
        self.baseline += 0.02 * (r - self.baseline)
        for kind, phi, p, i in self.trace:
            grad = phi[i] - p @ phi                 # d log pi(i) / d w
            self.w[kind] += self.lr * adv * grad
        self.trace = []
        return r

    def train(self, episodes, seed0=0, progress=None):
        for ep in range(episodes):
            res = play(self.char_id, seed0 + ep, self)
            self.learn(res)
            if progress and (ep + 1) % progress[0] == 0:
                progress[1](ep + 1, self.baseline)
        return self

    def save(self, path):
        np.savez(path, baseline=self.baseline, **{k: v for k, v in self.w.items()})

    def load(self, path):
        z = np.load(path)
        for k in self.w:
            if k in z and z[k].shape == self.w[k].shape:
                self.w[k] = z[k]
        self.baseline = float(z["baseline"])
        return self


def describe_policy(agent, top=8):
    """Human-readable summary of what the agent learned (biggest item-feature weights)."""
    names = (["STOP", "hp_frac", "gold", "stage", "bias"] + [f"rarity:{r}" for r in RARITIES]
             + ["class_item", "duplicate(merge)", "enemy_drop", "size", "price"] + [f"tag:{t}" for t in TAGS]
             + ["aura", "dps", "block/s", "heal/s", "poison/s", "burn/s", "stun", "dodge/s", "evade", "crit",
                "start_block+hp", "lifesteal", "heal_when_hurt", "summon_dps", "curse/s", "hex", "ki/s",
                "ki_burst", "counter+start_curse", "per_tag_bonus", "on_crit", "synergy",
                "grow/steal/cleanse", "stamina_use/s", "stamina_gain", "economy", "trigger_power", "alone_dmg",
                "other_effects"])
    w = agent.w["item"]
    order = np.argsort(-np.abs(w))[:top]
    return [(names[i] if i < len(names) else str(i), round(float(w[i]), 2)) for i in order]
