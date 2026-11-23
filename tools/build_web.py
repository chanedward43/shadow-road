"""Build the browser version of Shadow Road with pygbag.

    python tools/build_web.py            -> web_build/build/web/ (index.html + game package)
    python tools/build_web.py --serve    -> also serves it at http://localhost:8000 to test

Only what the game needs is copied (code, pixel art, balance settings), so the
90 MB source art pack, the AI tools and build folders never end up in the web page.
GitHub Actions runs this same script to publish the game on GitHub Pages.
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGE = os.path.join(ROOT, "web_build")

GAME_CODE = ["main.py", "roguegame"]
SKIP_MODULES = {"ai.py"}                      # numpy-based AI: desktop/balance tool only


def stage():
    if os.path.exists(STAGE):
        shutil.rmtree(STAGE)
    os.makedirs(STAGE)
    shutil.copy(os.path.join(ROOT, "main.py"), STAGE)
    shutil.copytree(os.path.join(ROOT, "roguegame"), os.path.join(STAGE, "roguegame"),
                    ignore=lambda d, names: [n for n in names if n == "__pycache__" or n in SKIP_MODULES])
    os.makedirs(os.path.join(STAGE, "assets"))
    shutil.copytree(os.path.join(ROOT, "assets", "art"), os.path.join(STAGE, "assets", "art"))
    shutil.copy(os.path.join(ROOT, "assets", "icon.png"), os.path.join(STAGE, "assets"))
    sfx = os.path.join(ROOT, "assets", "audio", "sfx")       # sound effects go in the game bundle;
    if os.path.exists(sfx):                                   # music is downloaded on demand (see publish_music)
        shutil.copytree(sfx, os.path.join(STAGE, "assets", "audio", "sfx"))


def publish_music(out):
    """Music lives next to the page (not inside the game bundle), so the first load is small; the game
    fetches music/<track>.ogg the first time each track plays (roguegame/audio.py)."""
    src = os.path.join(ROOT, "assets", "audio", "music")
    if os.path.exists(src):
        dst = os.path.join(out, "music")
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    for name in ("balance.json", "online.json"):       # online.json: the Arena's server (optional)
        src = os.path.join(ROOT, "assets", name)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(STAGE, "assets"))
    # the game's icon (tools/make_icon.py) is the page's favicon
    shutil.copy(os.path.join(ROOT, "assets", "icon_256.png"), os.path.join(STAGE, "favicon.png"))


def build(serve=False):
    stage()
    # our own page template: a Shadow Road loading screen with a progress bar, and no "click to start" wait
    cmd = [sys.executable, "-m", "pygbag", "--title", "Shadow Road", "--icon", "favicon.png",
           "--app_name", "shadowroad", "--ume_block", "0",
           "--template", os.path.join(ROOT, "tools", "web_template.tmpl")]
    if not serve:
        cmd.append("--build")
    cmd.append(STAGE)
    print(" ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)
    out = os.path.join(STAGE, "build", "web")
    publish_music(out)
    print(f"Web build ready: {out}")
    return out


if __name__ == "__main__":
    build(serve="--serve" in sys.argv)
