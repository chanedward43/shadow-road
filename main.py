"""SHADOW ROAD - a pack-building roguelike.

Desktop:  python main.py
Browser:  built with pygbag (see tools/build_web.py) - the async loop below lets the
          same code run in a web page, where the browser needs control back every frame.
"""
import asyncio
import sys

import pygame

from roguegame import ui
from roguegame.scenes import TitleScene

WEB = sys.platform == "emscripten"


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Shadow Road")
        self.screen = pygame.display.set_mode((ui.W, ui.H))
        self.clock = pygame.time.Clock()
        self.run = None
        self.running = True
        self.scene = TitleScene(self)

    def change(self, scene):
        if WEB:
            print("screen ->", type(scene).__name__)   # visible in the browser's terminal for debugging
        self.scene = scene

    def quit(self):
        if WEB:                      # a web page can't close itself: go back to the title instead
            self.change(TitleScene(self))
        else:
            self.running = False

    def frame(self):
        dt = min(self.clock.tick(60) / 1000.0, 0.1)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False
            else:
                self.scene.handle(ev)
        self.scene.update(dt)
        self.scene.draw(self.screen)
        self.draw_version()
        pygame.display.flip()

    def draw_version(self):
        from roguegame import ui
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
