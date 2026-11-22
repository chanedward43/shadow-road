"""Grid / backpack logic. Pure Python (no pygame)."""
import itertools

from .data import ITEMS, level_stats

_uid = itertools.count(1)


def rotate_shape(shape, rot):
    cells = list(shape)
    for _ in range(rot % 4):
        cells = [(-y, x) for x, y in cells]
    minx = min(c[0] for c in cells)
    miny = min(c[1] for c in cells)
    return sorted((x - minx, y - miny) for x, y in cells)


class ItemInst:
    """One physical copy of an item."""

    def __init__(self, item_id, rot=0, level=1):
        self.uid = next(_uid)
        self.id = item_id
        self.rot = rot
        self.level = level
        self.x = 0
        self.y = 0
        self._cache = None

    @property
    def data(self):
        """Stats at this copy's level (level 1 = the base item)."""
        if self._cache is None or self._cache[0] != self.level:
            self._cache = (self.level, level_stats(ITEMS[self.id], self.level))
        return self._cache[1]

    @property
    def shape(self):
        return rotate_shape(ITEMS[self.id]["shape"], self.rot)

    def cells_at(self, x, y):
        return [(x + dx, y + dy) for dx, dy in self.shape]

    @property
    def cells(self):
        return self.cells_at(self.x, self.y)

    def to_dict(self):
        return dict(id=self.id, rot=self.rot, x=self.x, y=self.y, level=self.level)


class Grid:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.items = []

    def occupied(self, ignore=None):
        occ = {}
        for it in self.items:
            if it is ignore:
                continue
            for c in it.cells:
                occ[c] = it
        return occ

    def can_place(self, inst, x, y):
        occ = self.occupied(ignore=inst)
        for cx, cy in inst.cells_at(x, y):
            if not (0 <= cx < self.w and 0 <= cy < self.h) or (cx, cy) in occ:
                return False
        return True

    def place(self, inst, x, y):
        if not self.can_place(inst, x, y):
            return False
        inst.x, inst.y = x, y
        if inst not in self.items:
            self.items.append(inst)
        return True

    def remove(self, inst):
        if inst in self.items:
            self.items.remove(inst)

    def item_at(self, cx, cy):
        return self.occupied().get((cx, cy))

    def first_fit(self, inst):
        """Place the item anywhere it fits (trying rotations). Returns success."""
        for rot in range(4):
            inst.rot = (inst.rot + (1 if rot else 0)) % 4
            for y in range(self.h):
                for x in range(self.w):
                    if self.can_place(inst, x, y):
                        return self.place(inst, x, y)
        return False

    def neighbors(self, inst):
        occ = self.occupied()
        mine = set(inst.cells)
        out = set()
        for cx, cy in mine:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                other = occ.get((cx + dx, cy + dy))
                if other is not None and other is not inst:
                    out.add(other)
        return out

    def to_dict(self):
        return dict(w=self.w, h=self.h, items=[i.to_dict() for i in self.items])
