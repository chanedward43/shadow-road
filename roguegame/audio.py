"""Sound effects and music. Silently does nothing when audio isn't available (tests, no sound card).

Files: assets/audio/sfx/<name>.ogg and assets/audio/music/<name>.ogg (made by tools/import_audio.py,
44.1 kHz, loudness-normalised). On the website the music is NOT inside the game bundle (that keeps the
first load small): each track is downloaded the first time it's needed, then cached for the session.
"""
import os
import sys
import time

import pygame

from . import settings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO = os.path.join(ROOT, "assets", "audio")
WEB = sys.platform == "emscripten"
SFX_GAIN = 0.8                 # effects overlap in battle: leave headroom so the mix never clips

_ok = None
_sounds = {}
_last = {}
_track = None                  # the track that should be playing
_playing = None                # the track actually playing
_web_files = {}                # track -> local path once downloaded (website)
_web_pending = set()

_JS = r"""
window.srMusic = window.srMusic || {};
window.srFetchMusic = function (name, url) {
  fetch(url).then(r => { if (!r.ok) throw new Error(r.status); return r.arrayBuffer(); })
    .then(buf => {
      let s = "", b = new Uint8Array(buf);
      for (let i = 0; i < b.length; i += 0x8000) s += String.fromCharCode.apply(null, b.subarray(i, i + 0x8000));
      window.srMusic[name] = btoa(s);
    })
    .catch(e => { window.srMusic[name] = "ERR"; });
  return "";
};
window.srTakeMusic = function (name) {
  const v = window.srMusic[name];
  if (v === undefined) return "";
  delete window.srMusic[name];
  return v;
};
"""
_js_ready = False


def ok():
    global _ok
    if _ok is None:
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(44100, -16, 2, 2048 if WEB else 1024)
            pygame.mixer.set_num_channels(16)
            _ok = True
        except Exception:            # noqa: BLE001 - no audio device: play nothing
            _ok = False
    return _ok


def muted():
    return bool(settings.get().get("muted"))


def toggle_mute():
    settings.set("muted", not muted())
    refresh_volume()


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
    if muted():
        return
    vol *= settings.get()["sfx"] * SFX_GAIN
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


def _music_path(track):
    local = os.path.join(AUDIO, "music", f"{track}.ogg")
    if os.path.exists(local):
        return local
    return _web_files.get(track)


def _web_fetch(track):
    """Start downloading a music track next to the web page (music/<track>.ogg)."""
    global _js_ready
    if track in _web_pending:
        return
    try:
        import platform as _p
        if not _js_ready:
            _p.window.eval(_JS)
            _js_ready = True
        _p.window.srFetchMusic(track, f"music/{track}.ogg")
        _web_pending.add(track)
    except Exception:                # noqa: BLE001
        pass


def update():
    """Called every frame: finishes web downloads and starts the wanted track once it's here."""
    if WEB and _web_pending:
        try:
            import base64
            import platform as _p
            for track in list(_web_pending):
                v = str(_p.window.srTakeMusic(track) or "")
                if not v:
                    continue
                _web_pending.discard(track)
                if v == "ERR":
                    continue
                path = f"/tmp/sr_{track}.ogg"
                with open(path, "wb") as f:
                    f.write(base64.b64decode(v))
                _web_files[track] = path
        except Exception:            # noqa: BLE001
            pass
    if _track != _playing:
        _start(_track)


def _start(track):
    global _playing
    if not ok():
        return
    try:
        if track is None:
            pygame.mixer.music.fadeout(600)
            _playing = None
            return
        path = _music_path(track)
        if path is None:
            if WEB:
                _web_fetch(track)
            return
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(0 if muted() else settings.get()["music"])
        pygame.mixer.music.play(-1, fade_ms=800)
        _playing = track
    except Exception:                # noqa: BLE001
        _playing = track             # don't retry a broken file every frame


def music(track):
    """Ask for a music track to loop (None = fade out). It starts as soon as it's available."""
    global _track
    _track = track
    update()


def refresh_volume():
    if ok():
        try:
            pygame.mixer.music.set_volume(0 if muted() else settings.get()["music"])
        except Exception:            # noqa: BLE001
            pass
