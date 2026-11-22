"""Tiny key -> text storage that survives restarts AND new versions of the game.

Desktop / .exe: one file per key in %APPDATA%/ShadowRoad (or ~/.shadowroad).
Browser (pygbag): the page's localStorage. It belongs to the site address, so it is kept
when a new version is pushed to GitHub Pages; it is only lost if the player clears their
browser's site data.
"""
import os
import sys

WEB = sys.platform == "emscripten"
PREFIX = "shadowroad:"


def _local_storage():
    try:
        import platform as _p         # pygbag exposes the browser window here
        return _p.window.localStorage
    except Exception:                 # noqa: BLE001
        return None


def save_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "ShadowRoad" if os.environ.get("APPDATA") else ".shadowroad")
    os.makedirs(d, exist_ok=True)
    return d


def _path(key):
    return os.path.join(save_dir(), f"{key}.json")


def read(key):
    """The stored text for key, or None."""
    try:
        if WEB:
            ls = _local_storage()
            if ls is not None:
                v = ls.getItem(PREFIX + key)
                return None if v is None else str(v)
        with open(_path(key), encoding="utf-8") as f:
            return f.read()
    except Exception:                 # noqa: BLE001 - storage must never crash the game
        return None


def write(key, value):
    """Store text under key. Returns True on success."""
    try:
        if WEB:
            ls = _local_storage()
            if ls is not None:
                ls.setItem(PREFIX + key, value)
                return True
        tmp = _path(key) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(value)
        os.replace(tmp, _path(key))    # atomic: a crash mid-write never corrupts the file
        return True
    except Exception as e:            # noqa: BLE001
        print("storage write skipped:", repr(e))
        return False


def delete(key):
    try:
        if WEB:
            ls = _local_storage()
            if ls is not None:
                ls.removeItem(PREFIX + key)
                return
        os.remove(_path(key))
    except Exception:                 # noqa: BLE001
        pass
