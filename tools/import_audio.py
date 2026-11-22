"""Copy the game's sounds and music from the Ninja Adventure pack (CC0) into assets/audio as small OGGs.

    python tools/import_audio.py

Needs ffmpeg on PATH. Sound effects become mono 22 kHz; music mono ~48 kbps, so the whole set stays a
few MB for the website. Edit SFX / MUSIC below to swap a sound.
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


def convert(src, dst, music):
    args = ["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-ac", "1", "-ar", "22050" if not music else "32000",
            "-c:a", "libvorbis", "-q:a", "0" if music else "2", dst]
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
