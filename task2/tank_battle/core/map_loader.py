"""Loads text maps.

Symbols:  .  empty      W  brick wall (3 HP)
          1  P1 tank    2  P2 tank
          A  P1 base    B  P2 base
Lines starting with '#' are comments. A line "# max_turns N" overrides the turn limit.
"""

import os

from .constants import BASE_HP, DEFAULT_MAX_TURNS, DOWN, TANK_HP, UP, WALL_HP
from .entities import Base, Tank
from .game_state import GameState

MAPS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "maps")


def parse_map(text, max_turns=None):
    rows = []
    file_max_turns = DEFAULT_MAX_TURNS
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            parts = line[1:].split()
            if len(parts) == 2 and parts[0] == "max_turns":
                file_max_turns = int(parts[1])
            continue
        rows.append(line)

    height = len(rows)
    width = len(rows[0])
    if any(len(r) != width for r in rows):
        raise ValueError("All map rows must have the same length")

    walls, tanks, bases = {}, [None, None], [None, None]
    for r, line in enumerate(rows):
        for c, ch in enumerate(line):
            if ch == "W":
                walls[(r, c)] = WALL_HP
            elif ch in "12":
                p = int(ch) - 1
                # P1 starts at the bottom facing up, P2 at the top facing down.
                tanks[p] = Tank(p, r, c, UP if p == 0 else DOWN, TANK_HP)
            elif ch in "AB":
                p = "AB".index(ch)
                bases[p] = Base(p, r, c, BASE_HP)
            elif ch != ".":
                raise ValueError("Unknown map symbol %r at (%d, %d)" % (ch, r, c))
    if None in tanks or None in bases:
        raise ValueError("A map needs tanks '1', '2' and bases 'A', 'B'")

    return GameState(width, height, walls, tanks, bases,
                     max_turns=max_turns if max_turns is not None else file_max_turns)


def list_maps():
    return sorted(f[:-4] for f in os.listdir(MAPS_DIR) if f.endswith(".txt"))


def load_map(name_or_path, max_turns=None):
    path = name_or_path
    if not os.path.isfile(path):
        path = os.path.join(MAPS_DIR, name_or_path if name_or_path.endswith(".txt") else name_or_path + ".txt")
    with open(path, encoding="utf-8") as f:
        return parse_map(f.read(), max_turns)
