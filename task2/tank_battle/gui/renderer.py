"""Draws a GameState with polished, modern vector shapes (no image assets needed).
Follows high-craft design engineering and modern UI/UX principles (shadcn / Tailwind Slate palette).
"""

import math
import pygame

from ..core.constants import BASE_HP, DC, DR, DOWN, TANK_HP, UP, WALL_HP

# ----------------------------------------------------------------------
# Modern High-Contrast Palette (Tailwind Slate & Vibrant Accents)
# ----------------------------------------------------------------------
BG = (15, 23, 42)              # Slate 900
PANEL = (30, 41, 59)           # Slate 800
PANEL_BORDER = (51, 65, 85)    # Slate 700
FIELD = (10, 15, 26)           # Deep tactical black-navy
GRID = (23, 32, 48)            # Subtle grid lines
TEXT = (248, 250, 252)         # Slate 50 (pure crisp white)
MUTED = (148, 163, 184)        # Slate 400
RULE = (51, 65, 85)            # Slate 700
ACCENT_BLUE = (37, 99, 235)    # Primary Blue (#2563EB)
ACCENT_LIGHT = (96, 165, 250)  # Light Blue (#60A5FA)

# Player Colors: P1 Royal Blue vs P2 Radiant Amber (High Contrast & Accessible)
PLAYER_COLORS = ((59, 130, 246), (245, 158, 11))
PLAYER_DARK = ((29, 78, 216), (180, 83, 9))
PLAYER_LIGHT = ((147, 197, 253), (252, 211, 77))

# Tactile Brick Walls (1 HP -> 2 HP -> 3 HP)
BRICK = ((154, 52, 18), (194, 65, 12), (234, 88, 12))
MORTAR = (28, 20, 18)
BULLET = (255, 255, 255)
BULLET_GLOW = (254, 240, 138)

HP_BG = (51, 65, 85)
HP_HIGH = (34, 197, 94)        # Emerald 500
HP_MID = (234, 179, 8)         # Yellow 500
HP_LOW = (239, 68, 68)         # Red 500
ALERT = (239, 68, 68)


def font(size, role="text", bold=False):
    """Clean modern sans-serif typography (Segoe UI, SF Pro, Roboto, Arial)."""
    names = {"head": "segoeui,sfprodisplay,roboto,helveticaneue,arial,sans-serif",
             "text": "segoeui,sfprotext,roboto,helveticaneue,arial,sans-serif"}[role]
    return pygame.font.SysFont(names, size, bold=bold or (role == "head"))


def draw_pips(surface, x, y, value, maximum, color, size=11, gap=4):
    """Draws sleek segmented pill indicators with rounded corners."""
    for i in range(maximum):
        rect = pygame.Rect(x + i * (size + gap), y, size, size)
        if i < value:
            pygame.draw.rect(surface, color, rect, border_radius=2)
        else:
            pygame.draw.rect(surface, (40, 50, 68), rect, border_radius=2)
            pygame.draw.rect(surface, HP_BG, rect, 1, border_radius=2)
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
        # Tactical field background with rounded outer border
        pygame.draw.rect(surface, FIELD, board, border_radius=8)

        # Subtle grid
        for r in range(1, state.height):
            y = self.origin[1] + r * self.cell
            pygame.draw.line(surface, GRID, (board.x, y), (board.right, y), 1)
        for c in range(1, state.width):
            x = self.origin[0] + c * self.cell
            pygame.draw.line(surface, GRID, (x, board.y), (x, board.bottom), 1)

        # Entities
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

        # Outer bezel border
        pygame.draw.rect(surface, PANEL_BORDER, board, 2, border_radius=8)

    def draw_wall(self, surface, rect, hp):
        pygame.draw.rect(surface, MORTAR, rect, border_radius=3)
        color = BRICK[max(0, min(hp, WALL_HP) - 1)]
        rows, gap = 4, max(1, self.cell // 22)
        bh = rect.height / rows
        for i in range(rows):
            offset = 0 if i % 2 == 0 else rect.width / 4
            y = rect.y + i * bh
            for j in range(-1, 2):
                x = rect.x + offset + j * rect.width / 2
                brick = pygame.Rect(int(x) + gap, int(y) + gap, int(rect.width / 2) - gap, int(bh) - gap)
                brick = brick.clip(rect)
                if brick.width > 0:
                    pygame.draw.rect(surface, color, brick, border_radius=2)
                    # Subtle top highlight on each brick
                    pygame.draw.line(surface, (min(255, color[0] + 35), min(255, color[1] + 25), min(255, color[2] + 25)),
                                     (brick.x, brick.y), (brick.right, brick.y), 1)

        if hp < WALL_HP:   # Damage cracks
            pygame.draw.line(surface, (15, 10, 8), rect.topleft, rect.center, 2)
            if hp == 1:
                pygame.draw.line(surface, (15, 10, 8), rect.bottomright, rect.center, 2)

    def draw_base(self, surface, base):
        rect = self.cell_rect(base.row, base.col).inflate(-self.cell // 8, -self.cell // 8)
        is_alive = base.hp > 0
        color = PLAYER_COLORS[base.player] if is_alive else (80, 90, 110)
        dark = PLAYER_DARK[base.player] if is_alive else (40, 48, 60)

        # Fortress base plate
        pygame.draw.rect(surface, (20, 28, 42), rect, border_radius=6)
        pygame.draw.rect(surface, dark, rect, 2, border_radius=6)

        # Eagle-shield crest
        cx, cy, s = rect.centerx, rect.centery, rect.width / 2
        body = [(cx - s * 0.6, cy - s * 0.1), (cx + s * 0.6, cy - s * 0.1),
                (cx + s * 0.35, cy + s * 0.55), (cx - s * 0.35, cy + s * 0.55)]
        pygame.draw.polygon(surface, color, body)
        for k in (-0.5, 0, 0.5):
            pygame.draw.polygon(surface, color, [
                (cx + (k - 0.22) * s, cy - s * 0.1),
                (cx + k * s, cy - s * 0.68),
                (cx + (k + 0.22) * s, cy - s * 0.1)
            ])

        if is_alive:
            # Core energy gem
            pygame.draw.circle(surface, (255, 255, 255), (cx, cy + int(s * 0.18)), max(2, int(s * 0.16)))

        self.draw_hp_bar(surface, rect, base.hp, BASE_HP)

    def draw_tank(self, surface, tank):
        rect = self.cell_rect(tank.row, tank.col).inflate(-self.cell // 6, -self.cell // 6)
        color = PLAYER_COLORS[tank.player]
        dark = PLAYER_DARK[tank.player]
        light = PLAYER_LIGHT[tank.player]
        tread = max(4, rect.width // 5)

        # Treads on both sides
        if tank.direction in (UP, DOWN):
            treads = [pygame.Rect(rect.x, rect.y, tread, rect.height),
                      pygame.Rect(rect.right - tread, rect.y, tread, rect.height)]
        else:
            treads = [pygame.Rect(rect.x, rect.y, rect.width, tread),
                      pygame.Rect(rect.x, rect.bottom - tread, rect.width, tread)]

        body = rect.inflate(-tread + 1, -tread + 1)
        for t in treads:
            pygame.draw.rect(surface, (25, 34, 48), t, border_radius=3)
            pygame.draw.rect(surface, dark, t, 1, border_radius=3)
            step = max(5, tread)
            for k in range(step, max(t.width, t.height), step):
                a = (t.x + k, t.y + 1) if t.width > t.height else (t.x + 1, t.y + k)
                b = (t.x + k, t.bottom - 2) if t.width > t.height else (t.right - 2, t.y + k)
                pygame.draw.line(surface, (45, 58, 78), a, b, 1)

        # Armored Tank Chassis
        pygame.draw.rect(surface, color, body, border_radius=4)
        pygame.draw.rect(surface, dark, body, 1, border_radius=4)

        # Rotating Turret & Barrel
        turret_r = max(4, body.width // 3)
        pygame.draw.circle(surface, dark, body.center, turret_r)
        pygame.draw.circle(surface, light, body.center, max(2, turret_r // 2))

        # Barrel with muzzle tip
        barrel_w = max(3, self.cell // 9)
        end = (rect.centerx + DC[tank.direction] * rect.width * 0.65,
               rect.centery + DR[tank.direction] * rect.height * 0.65)
        pygame.draw.line(surface, dark, body.center, end, barrel_w + 2)
        pygame.draw.line(surface, (255, 255, 255), body.center, end, max(1, barrel_w - 2))

        # Overhead floating health bar
        self.draw_hp_bar(surface, rect, tank.hp, TANK_HP)

    def draw_trails(self, surface, state, board):
        """Draws glowing bullet laser trails and explosive impact bursts."""
        for trail in getattr(state, "trails", ()):
            cells = trail["cells"]
            if len(cells) < 2:
                continue
            color = PLAYER_COLORS[trail["owner"]]
            start = self.cell_rect(*cells[0]).center
            end = self.cell_rect(*cells[-1]).center
            previous = surface.get_clip()
            surface.set_clip(board)
            width = max(3, self.cell // 9)
            # Dual-layer glow trail
            pygame.draw.line(surface, PLAYER_DARK[trail["owner"]], start, end, width + 4)
            pygame.draw.line(surface, color, start, end, width)
            pygame.draw.line(surface, (255, 255, 255), start, end, max(1, width - 2))
            if trail["hit"]:
                self.draw_impact(surface, end, color)
            else:
                pygame.draw.circle(surface, BULLET, end, max(4, self.cell // 8))
            surface.set_clip(previous)

    def draw_impact(self, surface, center, color):
        cx, cy = center
        r = self.cell * 0.46
        # Dynamic energy burst
        for k in range(8):
            dx, dy = pygame.math.Vector2(1, 0).rotate(45 * k + 22.5)
            inner, outer = r * 0.3, r if k % 2 == 0 else r * 0.72
            pygame.draw.line(surface, (255, 255, 255), (cx + dx * inner, cy + dy * inner),
                             (cx + dx * outer, cy + dy * outer), max(2, self.cell // 12))
        pygame.draw.circle(surface, color, center, max(4, int(r * 0.35)))
        pygame.draw.circle(surface, (255, 255, 255), center, max(2, int(r * 0.18)))

    def draw_bullet(self, surface, bullet):
        rect = self.cell_rect(bullet.row, bullet.col)
        cx, cy = rect.center
        tail = (cx - DC[bullet.direction] * self.cell * 0.45, cy - DR[bullet.direction] * self.cell * 0.45)
        # Glowing projectile
        pygame.draw.line(surface, PLAYER_COLORS[bullet.owner], tail, (cx, cy), max(3, self.cell // 10))
        pygame.draw.circle(surface, BULLET_GLOW, (cx, cy), max(4, self.cell // 8))
        pygame.draw.circle(surface, BULLET, (cx, cy), max(2, self.cell // 12))

    def draw_hp_bar(self, surface, rect, hp, max_hp):
        """Clean capsule HP bar with dynamic health-based color indicator."""
        hp = max(0, hp)
        ratio = hp / max_hp
        if ratio > 0.5:
            color = HP_HIGH
        elif ratio > 0.25:
            color = HP_MID
        else:
            color = HP_LOW

        bar_w = rect.width
        bar_h = 5
        bar_rect = pygame.Rect(rect.x, rect.y - 8, bar_w, bar_h)
        # Background
        pygame.draw.rect(surface, (20, 28, 42), bar_rect, border_radius=2)
        # Fill
        fill_w = max(0, int(bar_w * ratio))
        if fill_w > 0:
            fill_rect = pygame.Rect(bar_rect.x, bar_rect.y, fill_w, bar_h)
            pygame.draw.rect(surface, color, fill_rect, border_radius=2)
        # Border
        pygame.draw.rect(surface, HP_BG, bar_rect, 1, border_radius=2)
