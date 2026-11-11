"""Draws a GameState with plain pygame shapes (no image assets needed)."""

import pygame

from ..core.constants import BASE_HP, DC, DR, DOWN, TANK_HP, UP, WALL_HP

# Palette: an arcade cabinet seen at night. Olive-black housing, black playfield, brick, two team colours.
BG = (22, 26, 22)
PANEL = (32, 38, 32)
FIELD = (8, 10, 8)
GRID = (26, 31, 26)
TEXT = (232, 230, 217)
MUTED = (136, 146, 134)
RULE = (58, 66, 58)
PLAYER_COLORS = ((242, 182, 50), (91, 200, 107))      # P1 yellow, P2 green
PLAYER_DARK = ((138, 98, 14), (32, 112, 50))
BRICK = ((140, 62, 36), (170, 80, 44), (196, 98, 54))   # index = hp - 1
MORTAR = (74, 36, 24)
BULLET = (255, 250, 235)
HP_BG = (58, 66, 58)
HP_LOW = (224, 80, 60)
ALERT = (224, 80, 60)


def font(size, role="text"):
    """role: "head" (condensed, for titles and numbers) or "text"."""
    names = {"head": "dincondensed,avenirnextcondensed,arialnarrow,impact,arial",
             "text": "avenir,helveticaneue,arial,dejavusans"}[role]
    return pygame.font.SysFont(names, size)


def draw_pips(surface, x, y, value, maximum, color, size=9, gap=3):
    """Health as one square per hit point (HP is a small integer, so every point is shown)."""
    for i in range(maximum):
        rect = pygame.Rect(x + i * (size + gap), y, size, size)
        if i < value:
            pygame.draw.rect(surface, color, rect)
        else:
            pygame.draw.rect(surface, HP_BG, rect, 1)
    return x + maximum * (size + gap)


class BoardRenderer:
    def __init__(self, rect):
        self.rect = pygame.Rect(rect)
        self.cell = 40
        self.origin = self.rect.topleft

    def fit(self, state):
        self.cell = min(self.rect.width // state.width, self.rect.height // state.height)
        w, h = self.cell * state.width, self.cell * state.height
        self.origin = (self.rect.x + (self.rect.width - w) // 2, self.rect.y + (self.rect.height - h) // 2)

    def cell_rect(self, r, c):
        return pygame.Rect(self.origin[0] + c * self.cell, self.origin[1] + r * self.cell, self.cell, self.cell)

    def draw(self, surface, state):
        self.fit(state)
        board = pygame.Rect(self.origin, (self.cell * state.width, self.cell * state.height))
        pygame.draw.rect(surface, FIELD, board)
        for r in range(1, state.height):
            y = self.origin[1] + r * self.cell
            pygame.draw.line(surface, GRID, (board.x, y), (board.right, y))
        for c in range(1, state.width):
            x = self.origin[0] + c * self.cell
            pygame.draw.line(surface, GRID, (x, board.y), (x, board.bottom))
        for (r, c), hp in state.walls.items():
            self.draw_wall(surface, self.cell_rect(r, c), hp)
        for base in state.bases:
            self.draw_base(surface, base)
        for tank in state.tanks:
            if tank.hp > 0:
                self.draw_tank(surface, tank)
        self.draw_trails(surface, state, board)
        for bullet in state.bullets:
            if state.in_bounds(bullet.row, bullet.col):
                self.draw_bullet(surface, bullet)
        pygame.draw.rect(surface, RULE, board, 2)

    def draw_wall(self, surface, rect, hp):
        pygame.draw.rect(surface, MORTAR, rect)
        color = BRICK[max(0, min(hp, WALL_HP) - 1)]
        rows, gap = 4, max(1, self.cell // 24)
        bh = rect.height / rows
        for i in range(rows):
            offset = 0 if i % 2 == 0 else rect.width / 4
            y = rect.y + i * bh
            for j in range(-1, 2):
                x = rect.x + offset + j * rect.width / 2
                brick = pygame.Rect(int(x) + gap, int(y) + gap, int(rect.width / 2) - gap, int(bh) - gap)
                brick = brick.clip(rect)
                if brick.width > 0:
                    pygame.draw.rect(surface, color, brick)
        if hp < WALL_HP:   # cracks show damage
            pygame.draw.line(surface, (20, 10, 5), rect.topleft, rect.center, 2)
            if hp == 1:
                pygame.draw.line(surface, (20, 10, 5), rect.bottomright, rect.center, 2)

    def draw_base(self, surface, base):
        rect = self.cell_rect(base.row, base.col).inflate(-self.cell // 8, -self.cell // 8)
        color = PLAYER_COLORS[base.player] if base.hp > 0 else (80, 80, 80)
        pygame.draw.rect(surface, PANEL, rect)
        pygame.draw.rect(surface, PLAYER_DARK[base.player] if base.hp > 0 else RULE, rect, 2)
        # Eagle-like emblem: a crown of three triangles over a body.
        cx, cy, s = rect.centerx, rect.centery, rect.width / 2
        body = [(cx - s * 0.6, cy - s * 0.1), (cx + s * 0.6, cy - s * 0.1), (cx + s * 0.35, cy + s * 0.6),
                (cx - s * 0.35, cy + s * 0.6)]
        pygame.draw.polygon(surface, color, body)
        for k in (-0.5, 0, 0.5):
            pygame.draw.polygon(surface, color, [(cx + (k - 0.2) * s, cy - s * 0.1), (cx + k * s, cy - s * 0.7),
                                                 (cx + (k + 0.2) * s, cy - s * 0.1)])
        self.draw_hp_bar(surface, rect, base.hp, BASE_HP)

    def draw_tank(self, surface, tank):
        rect = self.cell_rect(tank.row, tank.col).inflate(-self.cell // 6, -self.cell // 6)
        color, dark = PLAYER_COLORS[tank.player], PLAYER_DARK[tank.player]
        tread = max(3, rect.width // 5)
        if tank.direction in (UP, DOWN):
            treads = [pygame.Rect(rect.x, rect.y, tread, rect.height),
                      pygame.Rect(rect.right - tread, rect.y, tread, rect.height)]
        else:
            treads = [pygame.Rect(rect.x, rect.y, rect.width, tread),
                      pygame.Rect(rect.x, rect.bottom - tread, rect.width, tread)]
        body = rect.inflate(-tread, -tread)
        for t in treads:
            pygame.draw.rect(surface, dark, t, border_radius=2)
            step = max(4, tread)                     # tread links
            for k in range(step, max(t.width, t.height), step):
                a = (t.x + k, t.y) if t.width > t.height else (t.x, t.y + k)
                b = (t.x + k, t.bottom - 1) if t.width > t.height else (t.right - 1, t.y + k)
                pygame.draw.line(surface, FIELD, a, b)
        pygame.draw.rect(surface, color, body, border_radius=3)
        pygame.draw.circle(surface, dark, body.center, max(3, body.width // 3))
        end = (rect.centerx + DC[tank.direction] * rect.width * 0.62,
               rect.centery + DR[tank.direction] * rect.height * 0.62)
        pygame.draw.line(surface, dark, rect.center, end, max(3, self.cell // 9))
        self.draw_hp_bar(surface, rect, tank.hp, TANK_HP)

    def draw_trails(self, surface, state, board):
        """Path flown by every bullet during the last cycle, and a burst where it hit something.
        A bullet covers 3 cells per cycle, so at close range it is fired and lands within one cycle
        and would otherwise never be seen."""
        for trail in getattr(state, "trails", ()):
            cells = trail["cells"]
            if len(cells) < 2:
                continue
            color = PLAYER_COLORS[trail["owner"]]
            start = self.cell_rect(*cells[0]).center
            end = self.cell_rect(*cells[-1]).center
            previous = surface.get_clip()
            surface.set_clip(board)                   # a bullet may leave the map
            width = max(3, self.cell // 9)
            pygame.draw.line(surface, PLAYER_DARK[trail["owner"]], start, end, width + 2)
            pygame.draw.line(surface, color, start, end, max(1, width - 2))
            if trail["hit"]:
                self.draw_impact(surface, end, color)
            else:
                pygame.draw.circle(surface, BULLET, end, max(3, self.cell // 9))
            surface.set_clip(previous)

    def draw_impact(self, surface, center, color):
        cx, cy = center
        r = self.cell * 0.42
        for k in range(8):                            # eight rays
            dx, dy = pygame.math.Vector2(1, 0).rotate(45 * k + 22.5)
            inner, outer = r * 0.35, r if k % 2 == 0 else r * 0.7
            pygame.draw.line(surface, BULLET, (cx + dx * inner, cy + dy * inner),
                             (cx + dx * outer, cy + dy * outer), max(2, self.cell // 14))
        pygame.draw.circle(surface, color, center, max(3, int(r * 0.3)))
        pygame.draw.circle(surface, BULLET, center, max(2, int(r * 0.14)))

    def draw_bullet(self, surface, bullet):
        rect = self.cell_rect(bullet.row, bullet.col)
        cx, cy = rect.center
        tail = (cx - DC[bullet.direction] * self.cell * 0.45, cy - DR[bullet.direction] * self.cell * 0.45)
        pygame.draw.line(surface, PLAYER_COLORS[bullet.owner], tail, (cx, cy), max(2, self.cell // 12))
        pygame.draw.circle(surface, BULLET, (cx, cy), max(3, self.cell // 9))

    def draw_hp_bar(self, surface, rect, hp, max_hp):
        """Segmented bar above the entity: one segment per hit point."""
        hp = max(0, hp)
        color = (120, 214, 130) if hp / max_hp > 0.34 else HP_LOW
        seg = rect.width / max_hp
        for i in range(max_hp):
            part = pygame.Rect(int(rect.x + i * seg), rect.y - 6, max(1, int(seg) - 1), 4)
            pygame.draw.rect(surface, color if i < hp else HP_BG, part)

