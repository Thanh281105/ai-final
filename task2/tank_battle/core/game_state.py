"""GameState: the full, fully-observable state of the Tank Battle game plus its transition function.

The real game is simultaneous (both tanks act in the same cycle). `next_state(a1, a2)` applies the
joint action of one cycle. Search algorithms turn one cycle into two plies (MAX picks, then MIN picks)
and only call `next_state` once both actions are known.
"""

from .constants import (
    Action, BULLET_SPEED, BULLETS_CANCEL_EACH_OTHER, DAMAGE_PER_HIT, DC, DEFAULT_MAX_TURNS, DR, DRAW,
    MAX_BULLETS_PER_TANK, MOVE_DIRECTION,
)
from .entities import Bullet


class GameState:
    __slots__ = ("width", "height", "walls", "tanks", "bases", "bullets", "turn", "max_turns",
                 "_walls_owned", "record_trails", "trails")

    def __init__(self, width, height, walls, tanks, bases, bullets=None, turn=0,
                 max_turns=DEFAULT_MAX_TURNS):
        self.width = width
        self.height = height
        self.walls = walls            # dict (row, col) -> hp
        self.tanks = tanks            # [Tank P1, Tank P2]
        self.bases = bases            # [Base P1, Base P2]
        self.bullets = bullets if bullets is not None else []
        self.turn = turn
        self.max_turns = max_turns
        self._walls_owned = True      # copy-on-write flag for the walls dict
        # Display only (not part of the game state): when record_trails is set, apply_cycle stores
        # the cells every bullet crossed during the cycle, so the GUI can draw the shot even when
        # a bullet is fired and hits within the same cycle. Search never sets it.
        self.record_trails = False
        self.trails = []              # [{"owner", "cells": [(r, c), ...], "hit": bool}]

    # ------------------------------------------------------------------ copying
    def clone(self):
        """Cheap copy used by search. The walls dict is shared until one side modifies it."""
        s = GameState.__new__(GameState)
        s.width, s.height = self.width, self.height
        s.walls = self.walls
        s.tanks = [t.clone() for t in self.tanks]
        s.bases = [b.clone() for b in self.bases]
        s.bullets = [b.clone() for b in self.bullets]
        s.turn, s.max_turns = self.turn, self.max_turns
        s._walls_owned = False
        self._walls_owned = False
        s.record_trails = False
        s.trails = []
        return s

    def deep_copy(self):
        """Fully independent copy, handed to (untrusted) plugin agents."""
        s = self.clone()
        s.walls = dict(self.walls)
        s._walls_owned = True
        return s

    def __deepcopy__(self, memo):
        return self.deep_copy()

    def _own_walls(self):
        if not self._walls_owned:
            self.walls = dict(self.walls)
            self._walls_owned = True

    # ------------------------------------------------------------------ queries
    def in_bounds(self, r, c):
        return 0 <= r < self.height and 0 <= c < self.width

    def tank_at(self, r, c):
        for t in self.tanks:
            if t.hp > 0 and t.row == r and t.col == c:
                return t
        return None

    def base_at(self, r, c):
        for b in self.bases:
            if b.row == r and b.col == c:
                return b
        return None

    def is_free_for_tank(self, r, c):
        """A tank may enter a cell that is inside the map and holds no wall, base or tank."""
        return (self.in_bounds(r, c) and (r, c) not in self.walls
                and self.base_at(r, c) is None and self.tank_at(r, c) is None)

    def has_bullet(self, player):
        n = 0
        for b in self.bullets:
            if b.owner == player:
                n += 1
        return n >= MAX_BULLETS_PER_TANK

    def legal_actions(self, player):
        """All 6 actions are always allowed by the rules; here we drop actions whose effect is
        identical to STAY (blocked move while already facing that way, FIRE while a bullet is in
        flight). This removes duplicate subtrees without changing the minimax value."""
        tank = self.tanks[player]
        actions = []
        for action, d in MOVE_DIRECTION.items():
            if tank.direction != d or self.is_free_for_tank(tank.row + DR[d], tank.col + DC[d]):
                actions.append(action)
        if not self.has_bullet(player):
            actions.append(Action.FIRE)
        actions.append(Action.STAY)
        return actions

    # ------------------------------------------------------------------ terminal test / utility
    def lost(self, player):
        return self.tanks[player].hp <= 0 or self.bases[player].hp <= 0

    def is_terminal(self):
        return (self.turn >= self.max_turns or self.lost(0) or self.lost(1))

    def winner(self):
        """0 / 1 for the winning player, DRAW, or None if the game is not over."""
        lost0, lost1 = self.lost(0), self.lost(1)
        if lost0 and lost1:
            return DRAW
        if lost0:
            return 1
        if lost1:
            return 0
        if self.turn >= self.max_turns:
            return DRAW
        return None

    def utility(self, player):
        """Zero-sum utility: +1 win, -1 loss, 0 draw (scaled by the search agents)."""
        w = self.winner()
        if w is None or w == DRAW:
            return 0
        return 1 if w == player else -1

    # ------------------------------------------------------------------ transition model
    def next_state(self, action_p1, action_p2):
        """RESULT(s, (a1, a2)): returns a new state, `self` is not modified."""
        s = self.clone()
        s.apply_cycle(action_p1, action_p2)
        return s

    def apply_cycle(self, action_p1, action_p2):
        """Resolve one game cycle in place: 1) movement, 2) firing, 3) bullets fly 3 cells."""
        actions = (action_p1, action_p2)

        # 1) Movement. MOVE_x always turns the tank to x, then moves if the cell is free.
        #    Two tanks targeting the same cell both stay.
        targets = [None, None]
        for p in (0, 1):
            tank = self.tanks[p]
            d = MOVE_DIRECTION.get(actions[p])
            if d is not None:
                tank.direction = d
                nr, nc = tank.row + DR[d], tank.col + DC[d]
                if self.is_free_for_tank(nr, nc):
                    targets[p] = (nr, nc)
        if targets[0] is not None and targets[0] == targets[1]:
            targets = [None, None]
        for p in (0, 1):
            if targets[p] is not None:
                self.tanks[p].row, self.tanks[p].col = targets[p]

        # A tank that drives onto a bullet resting in its new cell is hit.
        if self.bullets:
            survivors = []
            for b in self.bullets:
                t = self.tank_at(b.row, b.col)
                if t is not None:
                    t.hp -= DAMAGE_PER_HIT
                else:
                    survivors.append(b)
            self.bullets = survivors

        # 2) Firing: the bullet starts in the tank's cell and flies in the facing direction.
        for p in (0, 1):
            if actions[p] == Action.FIRE and not self.has_bullet(p):
                t = self.tanks[p]
                self.bullets.append(Bullet(p, t.row, t.col, t.direction))

        # 3) Bullets move cell by cell, collision check after every cell.
        record = self.record_trails
        if record:
            trails = {id(b): {"owner": b.owner, "cells": [(b.row, b.col)], "hit": False} for b in self.bullets}
        for _ in range(BULLET_SPEED):
            if not self.bullets:
                break
            flying = self.bullets
            self._advance_bullets_one_cell()
            if record:
                alive = {id(b) for b in self.bullets}
                for b in flying:            # bullets move in place; a removed one stopped in this cell
                    trail = trails[id(b)]
                    trail["cells"].append((b.row, b.col))
                    trail["hit"] = id(b) not in alive and self.in_bounds(b.row, b.col)
        if record:
            self.trails = list(trails.values())

        self.turn += 1

    def _advance_bullets_one_cell(self):
        previous = [(b.row, b.col) for b in self.bullets] if BULLETS_CANCEL_EACH_OTHER else None
        for b in self.bullets:
            b.row += DR[b.direction]
            b.col += DC[b.direction]

        alive = [True] * len(self.bullets)
        # Optional house rule (off by default): bullets meeting in a cell or passing through each
        # other both disappear.
        for i in range(len(self.bullets) if BULLETS_CANCEL_EACH_OTHER else 0):
            for j in range(i + 1, len(self.bullets)):
                bi, bj = self.bullets[i], self.bullets[j]
                same_cell = bi.row == bj.row and bi.col == bj.col
                swapped = (bi.row, bi.col) == previous[j] and (bj.row, bj.col) == previous[i]
                if same_cell or swapped:
                    alive[i] = alive[j] = False

        for i, b in enumerate(self.bullets):
            if alive[i] and self._collide(b):
                alive[i] = False
        self.bullets = [b for i, b in enumerate(self.bullets) if alive[i]]

    def _collide(self, bullet):
        """Apply damage to whatever is in the bullet's cell. Returns True if the bullet stops."""
        r, c = bullet.row, bullet.col
        if not self.in_bounds(r, c):
            return True
        if (r, c) in self.walls:
            self._own_walls()
            hp = self.walls[(r, c)] - DAMAGE_PER_HIT
            if hp <= 0:
                del self.walls[(r, c)]
            else:
                self.walls[(r, c)] = hp
            return True
        tank = self.tank_at(r, c)
        if tank is not None:
            tank.hp -= DAMAGE_PER_HIT
            return True
        base = self.base_at(r, c)
        if base is not None:
            base.hp -= DAMAGE_PER_HIT
            return True
        return False

    # ------------------------------------------------------------------ misc
    def key(self):
        """Hashable description of the state (for transposition tables / tests)."""
        return (tuple(sorted(self.walls.items())),
                tuple(t.key() for t in self.tanks),
                tuple(b.hp for b in self.bases),
                tuple(sorted((b.owner, b.row, b.col, b.direction) for b in self.bullets)),
                self.turn)

    def to_dict(self):
        """Plain-Python observation for agents written by other groups (no dependency on our classes)."""
        return {
            "width": self.width,
            "height": self.height,
            "turn": self.turn,
            "max_turns": self.max_turns,
            "walls": [[r, c, hp] for (r, c), hp in sorted(self.walls.items())],
            "tanks": [t.to_dict() for t in self.tanks],
            "bases": [b.to_dict() for b in self.bases],
            "bullets": [b.to_dict() for b in self.bullets],
        }

    def render_text(self):
        grid = [["." for _ in range(self.width)] for _ in range(self.height)]
        for (r, c), hp in self.walls.items():
            grid[r][c] = "W"
        for b in self.bases:
            grid[b.row][b.col] = "AB"[b.player]
        for t in self.tanks:
            if t.hp > 0:
                grid[t.row][t.col] = "12"[t.player]
        for b in self.bullets:
            if self.in_bounds(b.row, b.col):
                grid[b.row][b.col] = "*"
        return "\n".join("".join(row) for row in grid)

