"""Game constants: actions, directions and entity parameters taken from the assignment."""

from enum import Enum

# Entity health / damage (assignment table)
TANK_HP = 6
BASE_HP = 9
WALL_HP = 3
DAMAGE_PER_HIT = 1

BULLET_SPEED = 3          # cells per game cycle
MAX_BULLETS_PER_TANK = 1  # one bullet in flight per tank (classic Battle City rule)
# The assignment lists only three things a bullet can collide with: a wall, a tank or a base.
# So two bullets do not stop each other. (Setting this to True makes two tanks that face each
# other cancel every shot and stand still until the turn limit.)
BULLETS_CANCEL_EACH_OTHER = False
DEFAULT_MAX_TURNS = 200   # safety limit -> draw, guarantees every game is finite

PLAYER_1 = 0
PLAYER_2 = 1
DRAW = -1
PLAYER_NAMES = ("P1 (Yellow)", "P2 (Green)")

# Directions are small ints so states stay cheap to copy.
UP, DOWN, LEFT, RIGHT = 0, 1, 2, 3
DIRECTION_NAMES = ("UP", "DOWN", "LEFT", "RIGHT")
DR = (-1, 1, 0, 0)
DC = (0, 0, -1, 1)


class Action(Enum):
    MOVE_UP = "MOVE_UP"
    MOVE_DOWN = "MOVE_DOWN"
    MOVE_LEFT = "MOVE_LEFT"
    MOVE_RIGHT = "MOVE_RIGHT"
    FIRE = "FIRE"
    STAY = "STAY"

    @classmethod
    def parse(cls, value):
        """Accept an Action, its name ("FIRE") or its value; used for plugin agents."""
        if isinstance(value, Action):
            return value
        if isinstance(value, str):
            key = value.strip().upper()
            if key in cls.__members__:
                return cls[key]
        raise ValueError("Unknown action: %r" % (value,))


ALL_ACTIONS = tuple(Action)

MOVE_DIRECTION = {
    Action.MOVE_UP: UP,
    Action.MOVE_DOWN: DOWN,
    Action.MOVE_LEFT: LEFT,
    Action.MOVE_RIGHT: RIGHT,
}
