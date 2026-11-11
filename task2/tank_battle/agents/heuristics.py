"""Heuristic evaluation function EVAL(s, p) and move ordering used by the heuristic search agents.

EVAL is a weighted linear sum of features, always from the point of view of `player`
(zero-sum: EVAL(s, p) = -EVAL(s, 1 - p)):

    f1  tank HP difference
    f2  base HP difference
    f3  expected damage of bullets already in flight
    f4  fire potential: how easily each tank can hit the enemy tank / base from where it stands
    f5  mobility toward the enemy base (distance to a firing line)
"""

from ..core.constants import (
    Action, BASE_HP, BULLET_SPEED, DC, DOWN, DR, LEFT, MOVE_DIRECTION, RIGHT, TANK_HP, UP,
)


def direction_towards(src_row, src_col, dst_row, dst_col):
    """Direction from src to dst if both are on the same row/column, otherwise None."""
    if src_row == dst_row and src_col != dst_col:
        return RIGHT if dst_col > src_col else LEFT
    if src_col == dst_col and src_row != dst_row:
        return DOWN if dst_row > src_row else UP
    return None


def alignment_distance(r1, c1, r2, c2):
    """Moves needed to reach the target's row or column (where shooting is possible),
    plus a small term for the remaining Manhattan distance."""
    dr, dc = abs(r1 - r2), abs(c1 - c2)
    return min(dr, dc) + 0.1 * (dr + dc)


class HeuristicEvaluator:
    def __init__(self, w_tank_hp=100.0, w_base_hp=70.0, w_bullet=0.8, w_fire_tank=60.0,
                 w_fire_base=40.0, w_distance=6.0):
        self.w_tank_hp = w_tank_hp
        self.w_base_hp = w_base_hp
        self.w_bullet = w_bullet
        self.w_fire_tank = w_fire_tank
        self.w_fire_base = w_fire_base
        self.w_distance = w_distance

    # ------------------------------------------------------------------ public API
    def evaluate(self, state, player):
        opp = 1 - player
        my_tank, op_tank = state.tanks[player], state.tanks[opp]
        my_base, op_base = state.bases[player], state.bases[opp]

        # f1, f2: material
        score = self.w_tank_hp * (my_tank.hp - op_tank.hp)
        score += self.w_base_hp * (my_base.hp - op_base.hp)

        # f3: bullets in flight that are going to hit something important
        for bullet in state.bullets:
            hit = self.project_bullet(state, bullet)
            if hit is not None:
                kind, owner = hit
                value = self.w_tank_hp * 0.7 if kind == "tank" else self.w_base_hp
                score += self.w_bullet * (value if owner == opp else -value)

        # f4: fire potential (attack minus threat)
        score += self.fire_potential(state, player) - self.fire_potential(state, opp)

        # f5: approach the enemy base (and its tank) - smaller distance is better
        my_dist = (alignment_distance(my_tank.row, my_tank.col, op_base.row, op_base.col)
                   + 0.5 * alignment_distance(my_tank.row, my_tank.col, op_tank.row, op_tank.col))
        op_dist = (alignment_distance(op_tank.row, op_tank.col, my_base.row, my_base.col)
                   + 0.5 * alignment_distance(op_tank.row, op_tank.col, my_tank.row, my_tank.col))
        score += self.w_distance * (op_dist - my_dist)
        return score

    def fire_potential(self, state, player):
        tank = state.tanks[player]
        opp = 1 - player
        value = 0.0
        for target, weight in ((state.tanks[opp], self.w_fire_tank), (state.bases[opp], self.w_fire_base)):
            shots = self.shots_to_hit(state, tank, target.row, target.col)
            if shots is None:
                continue
            factor = 1.0 if tank.direction == direction_towards(tank.row, tank.col, target.row, target.col) else 0.5
            if state.has_bullet(player):
                factor *= 0.5
            value += weight * factor / shots
        return value

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def shots_to_hit(state, tank, target_row, target_col):
        """Number of shots needed to hit a target on the same line (walls in between absorb hits),
        or None if the target is not on a line or another tank/base blocks it."""
        d = direction_towards(tank.row, tank.col, target_row, target_col)
        if d is None:
            return None
        r, c = tank.row + DR[d], tank.col + DC[d]
        shots = 1
        while (r, c) != (target_row, target_col):
            wall_hp = state.walls.get((r, c))
            if wall_hp is not None:
                shots += wall_hp
            elif state.tank_at(r, c) is not None or state.base_at(r, c) is not None:
                return None
            r += DR[d]
            c += DC[d]
        return shots

    @staticmethod
    def project_bullet(state, bullet, horizon=3 * BULLET_SPEED):
        """Follow a bullet for up to `horizon` cells and report ("tank"|"base", owner) it will hit."""
        r, c = bullet.row, bullet.col
        for _ in range(horizon):
            r += DR[bullet.direction]
            c += DC[bullet.direction]
            if not state.in_bounds(r, c) or (r, c) in state.walls:
                return None
            t = state.tank_at(r, c)
            if t is not None:
                return ("tank", t.player)
            b = state.base_at(r, c)
            if b is not None:
                return ("base", b.player)
        return None

    # ------------------------------------------------------------------ move ordering
    def order_actions(self, state, player, actions):
        """Sort actions so that promising ones are searched first (improves alpha-beta pruning).
        Ordering never changes the minimax value, only how many nodes are pruned."""
        tank = state.tanks[player]
        opp = 1 - player
        targets = [(state.tanks[opp].row, state.tanks[opp].col), (state.bases[opp].row, state.bases[opp].col)]

        def score(action):
            if action == Action.FIRE:
                for tr, tc in targets:
                    if (direction_towards(tank.row, tank.col, tr, tc) == tank.direction
                            and self.shots_to_hit(state, tank, tr, tc) is not None):
                        return 4.0
                return 0.5
            if action == Action.STAY:
                return 0.0
            d = MOVE_DIRECTION[action]
            nr, nc = tank.row + DR[d], tank.col + DC[d]
            if not state.is_free_for_tank(nr, nc):
                nr, nc = tank.row, tank.col     # only turns
            before = min(alignment_distance(tank.row, tank.col, tr, tc) for tr, tc in targets)
            after = min(alignment_distance(nr, nc, tr, tc) for tr, tc in targets)
            return 2.0 + (before - after)

        return sorted(actions, key=score, reverse=True)


# Upper bound of |EVAL| - terminal utilities are scaled far above it.
MAX_EVAL = 10 * (TANK_HP * 100 + BASE_HP * 100)
