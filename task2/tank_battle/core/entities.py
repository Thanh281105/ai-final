"""Game entities. They use __slots__ because search copies them millions of times."""

from .constants import DIRECTION_NAMES


class Tank:
    __slots__ = ("player", "row", "col", "direction", "hp")

    def __init__(self, player, row, col, direction, hp):
        self.player = player
        self.row = row
        self.col = col
        self.direction = direction
        self.hp = hp

    @property
    def pos(self):
        return (self.row, self.col)

    @property
    def alive(self):
        return self.hp > 0

    def clone(self):
        return Tank(self.player, self.row, self.col, self.direction, self.hp)

    def to_dict(self):
        return {"player": self.player, "row": self.row, "col": self.col,
                "direction": DIRECTION_NAMES[self.direction], "hp": self.hp}

    def key(self):
        return (self.row, self.col, self.direction, self.hp)


class Base:
    __slots__ = ("player", "row", "col", "hp")

    def __init__(self, player, row, col, hp):
        self.player = player
        self.row = row
        self.col = col
        self.hp = hp

    @property
    def pos(self):
        return (self.row, self.col)

    @property
    def alive(self):
        return self.hp > 0

    def clone(self):
        return Base(self.player, self.row, self.col, self.hp)

    def to_dict(self):
        return {"player": self.player, "row": self.row, "col": self.col, "hp": self.hp}


class Bullet:
    __slots__ = ("owner", "row", "col", "direction")

    def __init__(self, owner, row, col, direction):
        self.owner = owner
        self.row = row
        self.col = col
        self.direction = direction

    @property
    def pos(self):
        return (self.row, self.col)

    def clone(self):
        return Bullet(self.owner, self.row, self.col, self.direction)

    def to_dict(self):
        return {"owner": self.owner, "row": self.row, "col": self.col,
                "direction": DIRECTION_NAMES[self.direction]}
