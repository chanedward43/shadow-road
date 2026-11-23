"""Draw Shadow Road's icon (32x32 pixel art): a katana across a red rising sun over a dark mountain ridge,
with falling cherry petals, on a night-sky tile with a gold frame.

    python tools/make_icon.py

Writes assets/icon.png (32x32), assets/icon_256.png (8x, for the web page / stores) and assets/icon.ico
(16-256 px, for the Windows .exe).
"""
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

N = 32
OUTLINE = (22, 12, 20)
GOLD, GOLD_D = (232, 188, 64), (160, 112, 36)
SUN, SUN_L, SUN_D = (200, 50, 46), (232, 96, 70), (150, 32, 40)
STEEL, STEEL_L, STEEL_D = (196, 204, 214), (246, 248, 252), (112, 120, 136)
WRAP, WRAP_L = (170, 40, 46), (236, 204, 120)
PETAL, PETAL_D = (250, 180, 205), (220, 120, 160)
RIDGE, RIDGE_FAR = (26, 14, 26), (52, 26, 48)


def draw():
    import pygame
    px = [[None] * N for _ in range(N)]

    def put(x, y, c):
        if 0 <= x < N and 0 <= y < N:
            px[y][x] = c

    # night-sky tile with rounded corners
    for y in range(N):
        k = y / (N - 1)
        sky = (int(30 + 70 * k), int(20 + 22 * k), int(44 + 16 * k))
        for x in range(N):
            cx = min(x, N - 1 - x)
            cy = min(y, N - 1 - y)
            if cx + cy < 3:                                     # cut the corners
                continue
            px[y][x] = sky
    # rising sun
    sx, sy, r = 16, 14, 9.5
    for y in range(N):
        for x in range(N):
            d = math.hypot(x + 0.5 - sx, y + 0.5 - sy)
            if d <= r and px[y][x] is not None:
                px[y][x] = SUN_L if (x + 0.5 - sx) + (y + 0.5 - sy) < -6 else (SUN_D if d > r - 1.2 else SUN)
    # mountains: a far ridge, then a near one
    far = [24, 23, 22, 21, 21, 22, 23, 23, 22, 21, 20, 20, 21, 22, 23, 24, 24, 23, 22, 21, 21, 20, 19, 20,
           21, 22, 22, 23, 24, 24, 25, 25]
    near = [27, 27, 26, 26, 25, 25, 26, 27, 27, 26, 25, 24, 24, 25, 26, 27, 27, 28, 27, 26, 26, 25, 24, 24,
            25, 26, 27, 27, 28, 28, 28, 28]
    for x in range(N):
        for y in range(far[x], N):
            if px[y][x] is not None:
                px[y][x] = RIDGE_FAR
        for y in range(near[x], N):
            if px[y][x] is not None:
                px[y][x] = RIDGE
    # katana: blade from the guard up to the top-right, handle down to the bottom-left
    guard = (10, 21)
    for t in range(0, 17):                                      # blade, 2 px wide, slight curve
        x, y = guard[0] + 1 + t, guard[1] - 1 - t
        bend = 1 if 6 <= t <= 12 else 0
        put(x, y - bend, STEEL_L)
        put(x + 1, y - bend, STEEL)
        put(x + 1, y + 1 - bend, STEEL_D)
        put(x - 1, y - bend, OUTLINE)
        put(x, y - 1 - bend, OUTLINE)
        put(x + 2, y + 1 - bend, OUTLINE)
        put(x + 1, y + 2 - bend, OUTLINE)
    put(guard[0] + 18, guard[1] - 18, STEEL_L)                  # the tip
    put(guard[0] + 19, guard[1] - 19, OUTLINE)
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (0, 0), (-1, -1), (1, 1)):   # gold tsuba
        put(guard[0] + dx, guard[1] + dy, GOLD if (dx, dy) != (1, 1) else GOLD_D)
    for dx, dy in ((-2, 0), (0, -2), (2, 1), (1, 2), (-2, -1), (-1, -2), (2, 2)):
        put(guard[0] + dx, guard[1] + dy, OUTLINE)
    for t in range(1, 7):                                       # wrapped handle (tsuka)
        x, y = guard[0] - t, guard[1] + t
        put(x, y, WRAP_L if t % 2 else WRAP)
        put(x - 1, y, WRAP if t % 2 else WRAP_L)
        put(x - 2, y, OUTLINE)
        put(x, y + 1, OUTLINE)
        put(x + 1, y + 1, OUTLINE)
    put(guard[0] - 7, guard[1] + 7, GOLD)                       # pommel
    put(guard[0] - 8, guard[1] + 8, OUTLINE)
    # falling petals
    for x, y in ((5, 6), (24, 26), (27, 17), (7, 13), (20, 4)):
        put(x, y, PETAL)
        put(x + 1, y, PETAL_D)
    # gold frame along the rounded edge
    for y in range(N):
        for x in range(N):
            if px[y][x] is None:
                continue
            edge = any(not (0 <= x + dx < N and 0 <= y + dy < N) or px[y + dy][x + dx] is None
                       for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if edge:
                px[y][x] = GOLD_D
    img = pygame.Surface((N, N), pygame.SRCALPHA)
    for y in range(N):
        for x in range(N):
            if px[y][x] is not None:
                img.set_at((x, y), px[y][x])
    return img


def main():
    import pygame
    pygame.init()
    img = draw()
    art = os.path.join(ROOT, "assets")
    pygame.image.save(img, os.path.join(art, "icon.png"))
    big = pygame.transform.scale(img, (256, 256))
    pygame.image.save(big, os.path.join(art, "icon_256.png"))
    try:                                                         # Windows .ico (needs Pillow)
        from PIL import Image
        Image.open(os.path.join(art, "icon_256.png")).save(
            os.path.join(art, "icon.ico"), sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    except ImportError:
        print("Pillow not installed: skipped icon.ico")
    print("wrote assets/icon.png, assets/icon_256.png, assets/icon.ico")


if __name__ == "__main__":
    main()
