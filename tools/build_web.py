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
    for name in ("balance.json", "online.json"):       # online.json: the Arena's server (optional)
        src = os.path.join(ROOT, "assets", name)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(STAGE, "assets"))
    # loading-screen / favicon image
    shutil.copy(os.path.join(ROOT, "assets", "art", "samurai.png"), os.path.join(STAGE, "favicon.png"))


def build(serve=False):
    stage()
    cmd = [sys.executable, "-m", "pygbag", "--title", "Shadow Road", "--icon", "favicon.png",
           "--app_name", "shadowroad"]
    if not serve:
        cmd.append("--build")
    cmd.append(STAGE)
    print(" ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)
    out = os.path.join(STAGE, "build", "web")
    print(f"Web build ready: {out}")
    return out


if __name__ == "__main__":
    build(serve="--serve" in sys.argv)
