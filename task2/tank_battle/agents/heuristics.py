"""Tactical heuristic evaluation EVAL(s, p) and move ordering for Tank Battle.

Every component is computed via `_side_score(state, p) - _side_score(state, 1 - p)`,
which strictly guarantees the zero-sum property EVAL(s, p) = -EVAL(s, 1 - p):

    f1  tank & base material advantage
    f2  imminent bullet danger & inescapable trajectory traps
    f3  clean-shot ambush potential, wall-pierce decay, and corridor pinning
    f4  obstacle-aware BFS distance to open firing lines (flanking around walls)
    f5  tactical cover & mobility (avoiding corners and dead ends)
"""

from collections import deque
from functools import lru_cache

from ..core.constants import (
    Action, BASE_HP, BULLET_SPEED, DC, DOWN, DR, LEFT, MOVE_DIRECTION, RIGHT, TANK_HP, UP,
)

DIRS = (UP, DOWN, LEFT, RIGHT)
INF_DIST = 999


def direction_towards(src_row, src_col, dst_row, dst_col):
    """Direction from src to dst if both are on the same row/column, otherwise None."""
    if src_row == dst_row and src_col != dst_col:
        return RIGHT if dst_col > src_col else LEFT
    if src_col == dst_col and src_row != dst_row:
        return DOWN if dst_row > src_row else UP
    return None


def alignment_distance(r1, c1, r2, c2):
    """Moves needed to reach the target's row or column (ignoring walls),
    plus a small term for the remaining Manhattan distance."""
    dr = r1 - r2 if r1 >= r2 else r2 - r1
    dc = c1 - c2 if c1 >= c2 else c2 - c1
    return (dr if dr < dc else dc) + 0.1 * (dr + dc)


@lru_cache(maxsize=512)
def _firing_line_bfs(walls_key, width, height, target_r, target_c):
    """Cached multi-source BFS distance map to any unobstructed firing lane of (target_r, target_c)."""
    walls = set(walls_key)
    dist = [INF_DIST] * (width * height)
    q = deque()

    # Seed distance=0 at every cell having an unobstructed orthogonal ray to target
    for d in DIRS:
        r, c = target_r + DR[d], target_c + DC[d]
        while 0 <= r < height and 0 <= c < width:
            if (r, c) in walls:
                break
            idx = r * width + c
            if dist[idx] == INF_DIST:
                dist[idx] = 0
                q.append((r, c))
            r += DR[d]
            c += DC[d]

    while q:
        r, c = q.popleft()
        nd = dist[r * width + c] + 1
        for d in DIRS:
            nr, nc = r + DR[d], c + DC[d]
            if 0 <= nr < height and 0 <= nc < width and (nr, nc) not in walls:
                idx = nr * width + nc
                if nd < dist[idx]:
                    dist[idx] = nd
                    q.append((nr, nc))

    return tuple(dist)


def _count_perp_escapes(state, row, col, shot_dir):
    """Number of free perpendicular adjacent cells a tank can step into to dodge along `shot_dir`."""
    perp = (LEFT, RIGHT) if shot_dir in (UP, DOWN) else (UP, DOWN)
    escapes = 0
    for d in perp:
        if state.is_free_for_tank(row + DR[d], col + DC[d]):
            escapes += 1
    return escapes


class HeuristicEvaluator:
    def __init__(self, w_tank_hp=100.0, w_base_hp=70.0, w_bullet=1.0, w_fire_tank=62.0,
                 w_fire_base=44.0, w_distance=6.5, w_pin=26.0, w_cover=3.5):
        self.w_tank_hp = w_tank_hp
        self.w_base_hp = w_base_hp
        self.w_bullet = w_bullet
        self.w_fire_tank = w_fire_tank
        self.w_fire_base = w_fire_base
        self.w_distance = w_distance
        self.w_pin = w_pin
        self.w_cover = w_cover

    # ------------------------------------------------------------------ public API
    def evaluate(self, state, player):
        return self._side_score(state, player) - self._side_score(state, 1 - player)

    def _side_score(self, state, player):
        opp = 1 - player
        my_tank, op_tank = state.tanks[player], state.tanks[opp]
        my_base, op_base = state.bases[player], state.bases[opp]

        # f1: Material
        score = self.w_tank_hp * my_tank.hp + self.w_base_hp * my_base.hp

        # f2: Incoming enemy bullets threatening my tank or base
        for bullet in state.bullets:
            if bullet.owner != opp:
                continue
            hit = self.project_bullet_detail(state, bullet)
            if hit is None:
                continue
            kind, victim, dist = hit
            if victim != player:
                continue
            if kind == "base":
                # Base cannot move: imminent hits are near-certain damage
                urgency = 1.0 if dist <= BULLET_SPEED else (0.78 if dist <= 2 * BULLET_SPEED else 0.55)
                score -= self.w_bullet * self.w_base_hp * urgency
            else:
                escapes = _count_perp_escapes(state, my_tank.row, my_tank.col, bullet.direction)
                if dist <= BULLET_SPEED:
                    # Arrives next bullet step: 0 escapes = trapped, 1+ = must burn turn dodging
                    trap_factor = 0.92 if escapes == 0 else (0.48 if escapes == 1 else 0.25)
                elif dist <= 2 * BULLET_SPEED:
                    trap_factor = 0.65 if escapes == 0 else (0.30 if escapes == 1 else 0.14)
                else:
                    trap_factor = 0.18 if escapes == 0 else 0.08
                score -= self.w_bullet * self.w_tank_hp * trap_factor

        # f3: Offensive fire potential, corridor pinning, and low-HP finish urgency
        score += self.fire_potential(state, player)

        # f4: Obstacle-aware BFS positioning toward open firing lines on enemy base & tank
        base_dist = self._lane_distance(state, my_tank, op_base.row, op_base.col)
        tank_dist = self._lane_distance(state, my_tank, op_tank.row, op_tank.col)
        # Prioritize low-HP targets dynamically (symmetric across players)
        base_urgency = 1.0 + 0.35 * (BASE_HP - op_base.hp) / BASE_HP
        tank_urgency = 0.55 + 0.30 * (TANK_HP - op_tank.hp) / TANK_HP
        score -= self.w_distance * (base_urgency * base_dist + tank_urgency * tank_dist)

        # f5: Tactical cover & escape mobility (penalize corner dead-ends, reward brick shielding)
        free_dirs = sum(1 for d in DIRS if state.is_free_for_tank(my_tank.row + DR[d], my_tank.col + DC[d]))
        if free_dirs <= 1:
            score -= 10.0
        elif free_dirs >= 3:
            score += 2.5

        if self.shots_to_hit(state, op_tank, my_tank.row, my_tank.col) != 1:
            adj_walls = sum(
                1 for d in DIRS
                if (my_tank.row + DR[d], my_tank.col + DC[d]) in state.walls
            )
            score += self.w_cover * min(2, adj_walls)

        return score

    def fire_potential(self, state, player):
        tank = state.tanks[player]
        opp = 1 - player
        op_tank, op_base = state.tanks[opp], state.bases[opp]
        ready = 1.0 if not state.has_bullet(player) else 0.45
        value = 0.0

        # Attack on opponent tank
        shots = self.shots_to_hit(state, tank, op_tank.row, op_tank.col)
        if shots is not None:
            d = direction_towards(tank.row, tank.col, op_tank.row, op_tank.col)
            dir_factor = 1.0 if tank.direction == d else 0.52
            pierce_decay = 1.0 if shots == 1 else 1.0 / (shots * shots)
            kill_scale = 1.0 + 0.30 * (TANK_HP - op_tank.hp) / TANK_HP
            value += self.w_fire_tank * dir_factor * ready * pierce_decay * kill_scale
            if shots == 1:
                escapes = _count_perp_escapes(state, op_tank.row, op_tank.col, d)
                if escapes == 0:
                    value += self.w_pin * dir_factor * ready
                elif escapes == 1:
                    value += 0.45 * self.w_pin * dir_factor * ready

        # Attack on opponent base
        shots = self.shots_to_hit(state, tank, op_base.row, op_base.col)
        if shots is not None:
            d = direction_towards(tank.row, tank.col, op_base.row, op_base.col)
            dir_factor = 1.0 if tank.direction == d else 0.52
            pierce_decay = 1.0 if shots == 1 else 1.0 / (shots * shots)
            kill_scale = 1.0 + 0.35 * (BASE_HP - op_base.hp) / BASE_HP
            value += self.w_fire_base * dir_factor * ready * pierce_decay * kill_scale

        return value

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _lane_distance(state, tank, target_r, target_c):
        walls_key = frozenset(state.walls.keys())
        grid = _firing_line_bfs(walls_key, state.width, state.height, target_r, target_c)
        d = grid[tank.row * state.width + tank.col]
        if d < INF_DIST:
            return d + 0.05 * alignment_distance(tank.row, tank.col, target_r, target_c)
        # Fallback when target is completely boxed in by brick fortresses
        return alignment_distance(tank.row, tank.col, target_r, target_c) + 4.0

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
    def project_bullet_detail(state, bullet, horizon=3 * BULLET_SPEED):
        """Follow a bullet up to `horizon` cells and return ("tank"|"base", owner, step_dist) or None."""
        r, c = bullet.row, bullet.col
        for step in range(1, horizon + 1):
            r += DR[bullet.direction]
            c += DC[bullet.direction]
            if not state.in_bounds(r, c) or (r, c) in state.walls:
                return None
            t = state.tank_at(r, c)
            if t is not None:
                return ("tank", t.player, step)
            b = state.base_at(r, c)
            if b is not None:
                return ("base", b.player, step)
        return None

    @staticmethod
    def project_bullet(state, bullet, horizon=3 * BULLET_SPEED):
        """Follow a bullet for up to `horizon` cells and report ("tank"|"base", owner) it will hit."""
        hit = HeuristicEvaluator.project_bullet_detail(state, bullet, horizon)
        return None if hit is None else (hit[0], hit[1])

    # ------------------------------------------------------------------ move ordering
    def order_actions(self, state, player, actions):
        """Sort tactical moves first (clean shots, bullet dodging, wall-aware flanking)
        so Alpha-Beta prunes dramatically more branches without changing minimax values."""
        tank = state.tanks[player]
        opp = 1 - player
        op_tank, op_base = state.tanks[opp], state.bases[opp]
        walls_key = frozenset(state.walls.keys())
        base_bfs = _firing_line_bfs(walls_key, state.width, state.height, op_base.row, op_base.col)
        tank_bfs = _firing_line_bfs(walls_key, state.width, state.height, op_tank.row, op_tank.col)

        # Detect cells currently on an enemy bullet's upcoming 6-cell ray
        danger_cells = set()
        for b in state.bullets:
            if b.owner == opp:
                r, c = b.row, b.col
                for _ in range(2 * BULLET_SPEED):
                    r += DR[b.direction]
                    c += DC[b.direction]
                    if not state.in_bounds(r, c) or (r, c) in state.walls:
                        break
                    danger_cells.add((r, c))

        def cell_dist(r, c):
            bd = base_bfs[r * state.width + c]
            td = tank_bfs[r * state.width + c]
            best_bfs = bd if bd < td else td
            if best_bfs < INF_DIST:
                return best_bfs + 0.05 * min(
                    alignment_distance(r, c, op_base.row, op_base.col),
                    alignment_distance(r, c, op_tank.row, op_tank.col),
                )
            return min(
                alignment_distance(r, c, op_base.row, op_base.col),
                alignment_distance(r, c, op_tank.row, op_tank.col),
            )

        in_danger_now = (tank.row, tank.col) in danger_cells
        before = cell_dist(tank.row, tank.col)

        def score(action):
            if action == Action.FIRE:
                best_shot = None
                for target in (op_tank, op_base):
                    if direction_towards(tank.row, tank.col, target.row, target.col) == tank.direction:
                        shots = self.shots_to_hit(state, tank, target.row, target.col)
                        if shots is not None and (best_shot is None or shots < best_shot):
                            best_shot = shots
                if best_shot == 1:
                    return 2.5 if in_danger_now else 6.0
                if best_shot is not None:
                    return 3.0 / best_shot
                return 0.2
            if action == Action.STAY:
                return -3.0 if in_danger_now else 0.0

            d = MOVE_DIRECTION[action]
            nr, nc = tank.row + DR[d], tank.col + DC[d]
            if not state.is_free_for_tank(nr, nc):
                nr, nc = tank.row, tank.col
            step_score = 2.0 + (before - cell_dist(nr, nc))
            if (nr, nc) in danger_cells:
                step_score -= 4.0
            elif in_danger_now:
                step_score += 3.5     # Prioritize active dodging when caught in bullet path
            return step_score

        return sorted(actions, key=score, reverse=True)


# Upper bound of |EVAL| - terminal utilities are scaled far above it.
MAX_EVAL = 10 * (TANK_HP * 100 + BASE_HP * 100)
