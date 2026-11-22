"""Player settings (volume, battle speed, colour-blind palette...), kept with storage.py."""
import json

from . import storage

DEFAULTS = dict(music=0.45, sfx=0.7, speed=1, colorblind=False, shake=True, hints=True)
_cur = None


def get():
    global _cur
    if _cur is None:
        _cur = dict(DEFAULTS)
        try:
            saved = json.loads(storage.read("settings") or "{}")
            _cur.update({k: v for k, v in saved.items() if k in DEFAULTS})
        except (ValueError, TypeError, AttributeError):
            pass
    return _cur


def set(key, value):           # noqa: A001 - settings.set reads naturally
    get()[key] = value
    storage.write("settings", json.dumps(_cur))
