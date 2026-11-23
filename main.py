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
from roguegame import scenes
from roguegame.scenes import LoadingScene, TitleScene

WEB = sys.platform == "emscripten"
# screens where the run clock doesn't tick (menus, end screens)
IDLE_SCENES = {"TitleScene", "CharSelectScene", "MatchHistoryScene", "AchievementsScene", "SettingsScene",
               "CompendiumScene", "ArenaLobbyScene", "EndScene", "ArenaEndScene", "LoadingScene"}


class PauseMenu:
    """Esc or the top-right menu button: pauses the screen underneath (battles stop, the run clock stops)."""
    W_, H_ = 380, 430

    def __init__(self, game):
        self.game = game
        self.rect = pygame.Rect(ui.W // 2 - self.W_ // 2, ui.H // 2 - self.H_ // 2, self.W_, self.H_)
        x, w = self.rect.x + 40, self.W_ - 80
        y = self.rect.y + 92
        in_run = game.run is not None
        items = [("Resume  (Esc)", self.resume, True),
                 ("Settings", self.settings, True),
                 ("Compendium", self.compendium, True),
                 ("Recipe book", self.recipes, in_run),
                 ("Main menu", self.main_menu, True)]
        self.buttons = []
        for k, (label, cb, ok) in enumerate(items):
            self.buttons.append(ui.Button((x, y + k * 62, w, 50), label, cb, 20, enabled=ok))

    # each screen opened from here comes back to the paused screen, with the menu open again
    def _away(self, make):
        g, scene = self.game, self.game.scene

        def back():
            g.change(scene)
            g.open_pause()
            return scene
        g.paused = None
        g.change(make(back))

    def resume(self):
        self.game.paused = None

    def settings(self):
        self._away(lambda back: scenes.SettingsScene(self.game, back=back))

    def compendium(self):
        self._away(lambda back: scenes.CompendiumScene(self.game, back=back))

    def recipes(self):
        g, scene = self.game, self.game.scene
        g.paused = None
        g.change(scenes.RecipeBookScene(g, back=scene))

    def main_menu(self):
        g = self.game
        g.paused = None
        g.run = None                       # the run stays saved at its last map: Continue picks it up
        g.change(TitleScene(g))

    def handle(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self.resume()
            return
        for b in self.buttons:
            if b.handle(ev):
                return

    def draw(self, s):
        dim = pygame.Surface((ui.W, ui.H), pygame.SRCALPHA)
        dim.fill((8, 6, 12, 170))
        s.blit(dim, (0, 0))
        ui.panel(s, self.rect, (28, 25, 38), ui.GOLD, radius=12, width=3)
        ui.text(s, "PAUSED", (self.rect.centerx, self.rect.y + 38), 34, ui.GOLD, True, center=True)
        ui.text(s, "Battles and the run clock are stopped.", (self.rect.centerx, self.rect.y + 70), 14, ui.DIM,
                center=True)
        for b in self.buttons:
            b.draw(s)
        if self.game.run is not None:
            ui.text(s, "Main menu keeps your run: press Continue to pick it up at its last map.",
                    (self.rect.centerx, self.rect.bottom + 16), 13, ui.DIM, center=True)


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Shadow Road")
        self.set_window_icon()
        self.display = pygame.display.set_mode((ui.W, ui.H))
        self.screen = pygame.Surface((ui.W, ui.H))      # scenes draw here; shaken onto the display
        self.clock = pygame.time.Clock()
        self.run = None
        self.running = True
        self.shake_t = 0.0
        self.shake_amt = 0.0
        self.toasts = []                                 # (text, colour, seconds left)
        self.mute_rect = pygame.Rect(ui.W - 48, 7, 38, 34)   # top-right on every screen
        self.menu_rect = pygame.Rect(ui.W - 92, 7, 38, 34)   # pause menu, left of the speaker
        self.touch = False                               # set once a touch screen is used
        self.paused = None                               # PauseMenu while the game is paused
        self.last_tip = None                             # tooltip drawn last frame (alt+right-click pins it)
        ui.apply_palette(settings.get()["colorblind"])
        ui.set_text_scale(1.12 if settings.get()["large_text"] else 1.0)
        self.scene = None
        self.change(LoadingScene(self))

    @staticmethod
    def set_window_icon():
        """The game's icon (assets/icon.png, made by tools/make_icon.py) on the window and taskbar."""
        import os
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.png")
        if os.path.exists(path):
            try:
                pygame.display.set_icon(pygame.image.load(path))
            except pygame.error:
                pass

    def change(self, scene):
        if WEB:
            print("screen ->", type(scene).__name__)   # visible in the browser's terminal for debugging
        self.scene = scene
        ui.TIP["pinned"] = None                          # a pinned tooltip belongs to the screen it was on
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

    # ---------------------------------------------------------------- pause
    def can_pause(self):
        sc = self.scene
        return getattr(sc, "pausable", True) and not sc.wants_escape()

    def open_pause(self):
        if self.can_pause():
            self.paused = PauseMenu(self)
            audio.play("click", 0.6)

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

    # ---------------------------------------------------------------- one frame
    def frame(self):
        dt = min(self.clock.tick(60) / 1000.0, 0.1)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.mute_rect.collidepoint(ev.pos):
                audio.toggle_mute()
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 3 and pygame.key.get_mods() & pygame.KMOD_ALT:
                self.toggle_pin()                        # alt + right-click: pin / release a tooltip
            elif self.paused is not None:
                self.paused.handle(ev)
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.menu_rect.collidepoint(ev.pos) \
                    and self.can_pause():
                self.open_pause()
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE and self.can_pause():
                self.open_pause()
            else:
                if ev.type in (pygame.FINGERDOWN, pygame.FINGERMOTION):
                    self.touch = True
                self.scene.handle(ev)
        if self.paused is None:
            self.scene.update(dt)
            if self.run is not None and type(self.scene).__name__ not in IDLE_SCENES:
                self.run.play_time = getattr(self.run, "play_time", 0.0) + dt     # the run clock
        audio.update()
        ui.TIP["frame"] = None
        self.scene.draw(self.screen)
        self.last_tip = ui.TIP["frame"]
        ui.draw_pinned(self.screen)
        if self.paused is not None:
            self.paused.draw(self.screen)
        self.draw_corner_buttons()
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

    def toggle_pin(self):
        if ui.TIP["pinned"] is not None:
            ui.TIP["pinned"] = None
            audio.play("back", 0.5)
        elif self.last_tip is not None:
            ui.TIP["pinned"] = self.last_tip
            audio.play("click", 0.6)

    def draw_corner_buttons(self):
        """Top-right of every screen: the pause menu (in-game screens) and the speaker (mute / unmute)."""
        mouse = pygame.mouse.get_pos()
        if type(self.scene).__name__ != "LoadingScene":
            self.draw_speaker(mouse)
        if self.paused is None and self.can_pause() and type(self.scene).__name__ != "LoadingScene":
            r = self.menu_rect
            hover = r.collidepoint(mouse)
            ui.panel(self.screen, r, ui.PANEL2 if hover else ui.PANEL, ui.GOLD if hover else ui.LINE, radius=6)
            for k in (-7, 0, 7):                         # "hamburger" menu icon
                pygame.draw.line(self.screen, ui.TEXT, (r.centerx - 9, r.centery + k), (r.centerx + 9, r.centery + k), 3)
            if hover:
                ui.text(self.screen, "Menu (Esc)", (r.x - 6, r.bottom + 4), 13, ui.DIM, True, right=True)

    def draw_speaker(self, mouse):
        r = self.mute_rect
        hover = r.collidepoint(mouse)
        ui.panel(self.screen, r, ui.PANEL2 if hover else ui.PANEL, ui.GOLD if hover else ui.LINE, radius=6)
        col = ui.DIM if audio.muted() else ui.TEXT
        cx, cy = r.x + 13, r.centery
        pygame.draw.rect(self.screen, col, (cx - 6, cy - 4, 5, 8))
        pygame.draw.polygon(self.screen, col, [(cx - 1, cy - 4), (cx + 6, cy - 10), (cx + 6, cy + 10), (cx - 1, cy + 4)])
        if audio.muted():
            pygame.draw.line(self.screen, ui.RED, (cx + 11, cy - 6), (cx + 21, cy + 6), 3)
            pygame.draw.line(self.screen, ui.RED, (cx + 21, cy - 6), (cx + 11, cy + 6), 3)
        else:
            pygame.draw.arc(self.screen, col, (cx + 2, cy - 7, 12, 14), -1.1, 1.1, 2)
            pygame.draw.arc(self.screen, col, (cx + 2, cy - 11, 18, 22), -1.1, 1.1, 2)

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
