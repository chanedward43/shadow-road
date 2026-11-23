"""The game's version, shown bottom-left on every screen and saved with each match-history run.

How to bump it (edit VERSION below before you push):
  +0.01  hotfix / small change: a bug fix, or tweaked item or enemy numbers   (0.60 -> 0.61)
  +0.1   bigger update: new items, UI changes, reworked characters           (0.61 -> 0.70)
  +1     a new season                                                       (0.70 -> 1.00)
While BETA is True the game shows "Beta" in front of the version. When the game goes live, just set
BETA = False - the version number keeps counting from wherever it is.
"""
BETA = True
VERSION = "1.00"


def label():
    return f"{'Beta ' if BETA else ''}v{VERSION}"
