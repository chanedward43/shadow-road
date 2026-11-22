"""SHADOW ROAD - a pack-building roguelike.

Desktop:  python main.py
Browser:  built with pygbag (see tools/build_web.py) - the async loop below lets the
          same code run in a web page, where the browser needs control back every frame.
"""
import asyncio
import random
import sys

import pygame

from roguegame import ui, settings, audio
from roguegame.scenes import TitleScene

WEB = sys.platform == "emscripten"


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Shadow Road")
        self.display = pygame.display.set_mode((ui.W, ui.H))
        self.screen = pygame.Surface((ui.W, ui.H))      # scenes draw here; shaken onto the display
        self.clock = pygame.time.Clock()
        self.run = None
        self.running = True
        self.shake_t = 0.0
        self.shake_amt = 0.0
        self.toasts = []                                 # (text, colour, seconds left)
        ui.apply_palette(settings.get()["colorblind"])
        self.scene = None
        self.change(TitleScene(self))

    def change(self, scene):
        if WEB:
            print("screen ->", type(scene).__name__)   # visible in the browser's terminal for debugging
        self.scene = scene
        track = getattr(scene, "music", None)
        if callable(track):
            track = track()
        if track:
            audio.music(track)

    def quit(self):
        if WEB:                      # a web page can't close itself: go back to the title instead
            self.change(TitleScene(self))
        else:
            self.running = False

    # ---------------------------------------------------------------- juice
    def shake(self, amount=6, secs=0.25):
        if settings.get()["shake"]:
            self.shake_amt = max(self.shake_amt, amount)
            self.shake_t = max(self.shake_t, secs)

    def toast(self, msg, col=(235, 200, 110), secs=3.5):
        self.toasts.append([msg, col, secs])

    def draw_toasts(self, dt):
        y = 58
        for t in self.toasts:
            t[2] -= dt
            img = ui.font(17, True).render(t[0], True, t[1])
            r = img.get_rect(midtop=(ui.W // 2, y)).inflate(28, 14)
            box = pygame.Surface(r.size, pygame.SRCALPHA)
            box.fill((20, 18, 26, 225))
            alpha = max(0, min(255, int(255 * t[2] / 0.4)))
            box.set_alpha(alpha)
            img.set_alpha(alpha)
            self.screen.blit(box, r)
            pygame.draw.rect(self.screen, t[1], r, 2, border_radius=6)
            self.screen.blit(img, img.get_rect(center=r.center))
            y = r.bottom + 6
        self.toasts = [t for t in self.toasts if t[2] > 0]

    def frame(self):
        dt = min(self.clock.tick(60) / 1000.0, 0.1)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False
            else:
                self.scene.handle(ev)
        self.scene.update(dt)
        self.scene.draw(self.screen)
        self.draw_toasts(dt)
        self.draw_version()
        ox = oy = 0
        if self.shake_t > 0:
            self.shake_t -= dt
            k = self.shake_amt * max(0.0, self.shake_t) / 0.25
            ox, oy = random.uniform(-k, k), random.uniform(-k, k)
            if self.shake_t <= 0:
                self.shake_amt = 0
        if ox or oy:
            self.display.fill((0, 0, 0))
        self.display.blit(self.screen, (int(ox), int(oy)))
        pygame.display.flip()

    def draw_version(self):
        from roguegame.version import label
        img = ui.font(13).render(label(), True, (120, 112, 100))
        img.set_alpha(170)
        self.screen.blit(img, (6, self.screen.get_height() - img.get_height() - 3))

    async def loop(self):
        while self.running:
            if WEB:
                try:
                    self.frame()
                except Exception:    # noqa: BLE001 - in a browser, report and keep the page alive
                    import traceback
                    msg = traceback.format_exc()
                    if msg != getattr(self, "_last_error", None):   # print each distinct error once
                        self._last_error = msg
                        print(msg)
            else:
                self.frame()
            await asyncio.sleep(0)   # hand control back to the browser (no-op on desktop)
        pygame.quit()


async def main():
    await Game().loop()


if __name__ == "__main__":
    asyncio.run(main())
