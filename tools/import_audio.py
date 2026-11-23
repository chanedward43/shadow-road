"""Copy the game's sounds and music from the Ninja Adventure pack (CC0) into assets/audio as small OGGs.

    python tools/import_audio.py

Needs ffmpeg on PATH. Everything becomes mono 44.1 kHz OGG with loudness normalisation (consistent volume).
Music is not bundled into the web page: the website downloads each track the first time it plays. Edit SFX / MUSIC below to swap a sound.
"""
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK = os.path.join(ROOT, "had", "Ninja Adventure - Asset Pack", "Audio")
OUT = os.path.join(ROOT, "assets", "audio")

SFX = {
    "click": "Sounds/Menu/Accept.wav", "back": "Sounds/Menu/Cancel.wav", "move": "Sounds/Menu/Move1.wav",
    "buy": "Sounds/Bonus/Coin.wav", "sell": "Sounds/Bonus/Coin2.wav", "gold": "Sounds/Bonus/Gold1.wav",
    "merge": "Sounds/Bonus/PowerUp1.wav", "event": "Sounds/Bonus/Bonus.wav",
    "hit": "Sounds/Hit & Impact/Hit1.wav", "hit2": "Sounds/Hit & Impact/Hit2.wav",
    "crit": "Sounds/Hit & Impact/Impact3.wav", "block": "Sounds/Hit & Impact/Impact.wav",
    "slash": "Sounds/Whoosh & Slash/Slash.wav", "evade": "Sounds/Whoosh & Slash/Whoosh.wav",
    "heal": "Sounds/Magic & Skill/Heal.wav", "poison": "Sounds/Elemental/Bubble.wav",
    "burn": "Sounds/Elemental/Fire.wav", "stun": "Sounds/Magic & Skill/Strange.wav",
    "summon": "Sounds/Magic & Skill/Spirit.wav", "curse": "Sounds/Magic & Skill/Magic3.wav",
    "phase": "Sounds/Alert/Alert2.wav", "explode": "Sounds/Elemental/Explosion.wav",
    "win": "Jingles/Success2.wav", "lose": "Jingles/GameOver2.wav", "levelup": "Jingles/LevelUp1.wav",
    "achievement": "Jingles/Secret1.wav",
}
MUSIC = {
    "title": "Musics/13 - Mystical.ogg", "map": "Musics/23 - Road.ogg", "battle": "Musics/17 - Fight.ogg",
    "boss": "Musics/28 - Tension.ogg", "bloodmoon": "Musics/14 - Curse.ogg", "arena": "Musics/10 - Dark Castle.ogg",
}


def peak_db(src):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", src, "-af", "volumedetect", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    for line in out.splitlines():
        if "max_volume" in line:
            return float(line.split("max_volume:")[1].split("dB")[0])
    return 0.0


def convert(src, dst, music):
    # 44.1 kHz (low sample rates sounded crackly once resampled).
    # Music: EBU R128 loudness normalisation to -20 LUFS, so every track is about as loud as the others.
    # Effects: peak-normalised to -6 dB. Short clips pushed to 0 dB clip (sounds like static) - and several
    # play at once in battle, so they need the headroom.
    norm = "loudnorm=I=-20:TP=-2:LRA=11" if music else f"volume={-6.0 - peak_db(src):.1f}dB"
    args = ["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-af", norm, "-ac", "1", "-ar", "44100",
            "-c:a", "libvorbis", "-q:a", "3" if music else "4", dst]
    subprocess.run(args, check=True)


def main():
    for sub in ("sfx", "music"):
        os.makedirs(os.path.join(OUT, sub), exist_ok=True)
    total = 0
    for group, table in (("sfx", SFX), ("music", MUSIC)):
        for name, rel in table.items():
            dst = os.path.join(OUT, group, f"{name}.ogg")
            convert(os.path.join(PACK, rel), dst, group == "music")
            total += os.path.getsize(dst)
            print(f"{group}/{name}.ogg  {os.path.getsize(dst) // 1024} KB  <- {rel}")
    print(f"total {total // 1024} KB")


if __name__ == "__main__":
    main()
