"""Sound effects and music. Silently does nothing when audio isn't available (tests, no sound card).

Files live in assets/audio/sfx/<name>.ogg and assets/audio/music/<name>.ogg (made by tools/import_audio.py).
"""
import os
import time

import pygame

from . import settings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO = os.path.join(ROOT, "assets", "audio")

_ok = None
_sounds = {}
_last = {}
_track = None


def ok():
    global _ok
    if _ok is None:
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 2, 512)
            pygame.mixer.set_num_channels(16)
            _ok = True
        except Exception:            # noqa: BLE001 - no audio device: play nothing
            _ok = False
    return _ok


def _sound(name):
    if name not in _sounds:
        p = os.path.join(AUDIO, "sfx", f"{name}.ogg")
        try:
            _sounds[name] = pygame.mixer.Sound(p) if os.path.exists(p) else None
        except Exception:            # noqa: BLE001
            _sounds[name] = None
    return _sounds[name]


def play(name, vol=1.0, gap=0.06):
    """Play a sound effect. The same sound won't stack more than once every `gap` seconds."""
    vol *= settings.get()["sfx"]
    if vol <= 0 or not ok():
        return
    now = time.time()
    if now - _last.get(name, 0) < gap:
        return
    _last[name] = now
    snd = _sound(name)
    if snd is not None:
        snd.set_volume(min(1.0, vol))
        snd.play()


def music(track):
    """Loop a music track (no-op if it's already playing). None = fade out."""
    global _track
    if track == _track or not ok():
        return
    _track = track
    try:
        if track is None:
            pygame.mixer.music.fadeout(600)
            return
        p = os.path.join(AUDIO, "music", f"{track}.ogg")
        if not os.path.exists(p):
            return
        pygame.mixer.music.load(p)
        pygame.mixer.music.set_volume(settings.get()["music"])
        pygame.mixer.music.play(-1, fade_ms=800)
    except Exception:                # noqa: BLE001
        pass


def refresh_volume():
    if ok():
        try:
            pygame.mixer.music.set_volume(settings.get()["music"])
        except Exception:            # noqa: BLE001
            pass
