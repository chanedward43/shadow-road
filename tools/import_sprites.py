"""Import item sprites from downloaded art packs into assets/art/.

    python tools/import_sprites.py                 # uses assets/sprite_import.json
    python tools/import_sprites.py --check         # just list items still missing / sharing a sprite

assets/sprite_import.json maps an item id to a source image (paths relative to the project folder):
    {"iron_tsuba": "had/Kyrise 16x16/icons/tsuba.png",
     "uchigatana": "had/Weapon icons/sheet.png#32,16,16,16"}      <- "#x,y,w,h" crops one icon from a sheet
Each sprite is trimmed to its visible pixels and saved as assets/art/<item id>.png (the game scales it, keeping
pixels crisp). assets/art_map.json records where every sprite came from; assets/sprite_requests.md lists what
is still needed.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    import pygame
    from roguegame.data import ITEMS
    art_dir = os.path.join(ROOT, "assets", "art")
    map_path = os.path.join(ROOT, "assets", "art_map.json")
    art_map = json.load(open(map_path, encoding="utf-8"))
    if a.check:
        missing = [i for i, d in ITEMS.items() if not d["enemy"] and not os.path.exists(os.path.join(art_dir, f"{i}.png"))]
        pygame.init()
        by_img = {}                                    # identical pixels = the same sprite
        for k, d in ITEMS.items():
            path = os.path.join(art_dir, f"{k}.png")
            if not d["enemy"] and os.path.exists(path):
                img = pygame.image.load(path)
                by_img.setdefault((img.get_size(), pygame.image.tobytes(img, "RGBA")), []).append(k)
        shared = [ks for ks in by_img.values() if len(ks) > 1]
        print(f"{len(missing)} items without a sprite, {len(shared)} identical sprites used by several items")
        for ks in shared:
            print("  shared:", ", ".join(ks))
        return
    req = json.load(open(os.path.join(ROOT, "assets", "sprite_import.json"), encoding="utf-8"))
    pygame.init()
    pygame.display.set_mode((1, 1))
    for iid, src in req.items():
        if iid not in ITEMS:
            print("unknown item", iid)
            continue
        path, _, crop = src.partition("#")
        img = pygame.image.load(os.path.join(ROOT, path)).convert_alpha()
        if crop:
            x, y, w, h = (int(v) for v in crop.split(","))
            img = img.subsurface((x, y, w, h)).copy()
        r = img.get_bounding_rect()
        pygame.image.save(img.subsurface(r).copy(), os.path.join(art_dir, f"{iid}.png"))
        art_map[iid] = src
        print(iid, "<-", src)
    json.dump(art_map, open(map_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
