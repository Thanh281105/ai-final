"""Draws a GameState with crisp Light Blue & White vector graphics (no external assets needed)."""

import pygame

from ..core.constants import BASE_HP, DC, DOWN, DR, LEFT, RIGHT, TANK_HP, UP, WALL_HP

# ----------------------------------------------------------------------
# Light Blue & White Palette (High Contrast & Accessibility Compliant)
# ----------------------------------------------------------------------
BG = (241, 245, 249)            # Slate 100 canvas (#F1F5F9)
PANEL = (255, 255, 255)         # Pure White cards (#FFFFFF)
PANEL_SOFT = (239, 246, 255)    # Soft Blue surface (#EFF6FF)
PANEL_BORDER = (203, 213, 225)  # Slate 300 border (#CBD5E1)
FIELD = (248, 250, 252)         # Bright arena floor (#F8FAFC)
FIELD_ALT = (241, 245, 249)     # Subtle checkerboard tint
GRID = (226, 232, 240)          # Slate 200 grid lines (#E2E8F0)
TEXT = (15, 23, 42)             # Slate 900 crisp ink (#0F172A)
MUTED = (71, 85, 105)           # Slate 600 muted ink (#475569)
RULE = (226, 232, 240)          # Subtle divider
ACCENT_BLUE = (37, 99, 235)     # Primary Blue (#2563EB)
ACCENT_DARK = (29, 78, 216)     # Dark Blue (#1D4ED8)
ACCENT_LIGHT = (219, 234, 254)  # Soft Blue highlight (#DBEAFE)

# Player Colors matched strictly to constants.PLAYER_NAMES: ("P1 (Blue)", "P2 (Red)")
PLAYER_COLORS = ((37, 99, 235), (220, 38, 38))     # P1 Royal Blue, P2 Crimson Red
PLAYER_DARK = ((29, 78, 216), (153, 27, 27))       # Deep Blue, Deep Red
PLAYER_LIGHT = ((147, 197, 253), (252, 165, 165))  # Sky highlight, Rose highlight

# Terracotta Masonry Walls (1 HP cracked -> 2 HP worn -> 3 HP intact)
BRICK = ((226, 135, 91), (204, 102, 58), (180, 74, 34))
MORTAR = (120, 96, 82)
SHADOW = (203, 213, 225)

BULLET_CORE = (254, 240, 138)
BULLET_RIM = (15, 23, 42)

HP_BG = (203, 213, 225)
HP_EMPTY = (226, 232, 240)
HP_HIGH = (22, 163, 74)         # Green 600
HP_MID = (217, 119, 6)          # Amber 600
HP_LOW = (220, 38, 38)          # Red 600
ALERT = (220, 38, 38)


def font(size, role="text", bold=False):
    """Clean modern sans-serif typography."""
    names = {"head": "segoeui,sfprodisplay,roboto,helveticaneue,arial,sans-serif",
             "text": "segoeui,sfprotext,roboto,helveticaneue,arial,sans-serif"}[role]
    return pygame.font.SysFont(names, size, bold=bold or (role == "head"))


def draw_pips(surface, x, y, value, maximum, color, size=11, gap=4):
    """Draws sleek segmented pill indicators."""
    for i in range(maximum):
        rect = pygame.Rect(x + i * (size + gap), y, size, size)
        if i < value:
            pygame.draw.rect(surface, color, rect, border_radius=2)
        else:
            pygame.draw.rect(surface, HP_EMPTY, rect, border_radius=2)
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

        # Outer card drop shadow + clean bright floor
        pygame.draw.rect(surface, SHADOW, board.move(2, 3), border_radius=8)
        pygame.draw.rect(surface, FIELD, board, border_radius=8)

        # Subtle checkerboard floor tint for clear distance reading
        for r in range(state.height):
            for c in range((r + 1) % 2, state.width, 2):
                cr = self.cell_rect(r, c)
                pygame.draw.rect(surface, FIELD_ALT, cr)

        # Clean tactical grid
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

        pygame.draw.rect(surface, PANEL_BORDER, board, 2, border_radius=8)

    def draw_wall(self, surface, rect, hp):
        inner = rect.inflate(-2, -2)
        pygame.draw.rect(surface, MORTAR, inner, border_radius=3)
        color = BRICK[max(0, min(hp, WALL_HP) - 1)]
        rows, gap = 4, max(1, self.cell // 24)
        bh = inner.height / rows
        for i in range(rows):
            offset = 0 if i % 2 == 0 else inner.width / 4
            y = inner.y + i * bh
            for j in range(-1, 2):
                x = inner.x + offset + j * inner.width / 2
                brick = pygame.Rect(int(x) + gap, int(y) + gap, int(inner.width / 2) - gap, int(bh) - gap)
                brick = brick.clip(inner)
                if brick.width > 1 and brick.height > 1:
                    pygame.draw.rect(surface, color, brick, border_radius=1)
                    highlight = (min(255, color[0] + 28), min(255, color[1] + 22), min(255, color[2] + 18))
                    pygame.draw.line(surface, highlight, (brick.x, brick.y), (brick.right - 1, brick.y), 1)

        if hp < WALL_HP:
            pygame.draw.line(surface, (45, 32, 26), inner.topleft, inner.center, 2)
            if hp == 1:
                pygame.draw.line(surface, (45, 32, 26), inner.bottomright, inner.center, 2)

    def draw_base(self, surface, base):
        rect = self.cell_rect(base.row, base.col).inflate(-self.cell // 8, -self.cell // 8)
        is_alive = base.hp > 0
        color = PLAYER_COLORS[base.player] if is_alive else (148, 163, 184)
        dark = PLAYER_DARK[base.player] if is_alive else (100, 116, 139)
        plate_bg = (239, 246, 255) if (is_alive and base.player == 0) else ((254, 242, 242) if is_alive else (226, 232, 240))

        # Grounded shadow + bastion plate
        pygame.draw.rect(surface, SHADOW, rect.move(1, 2), border_radius=6)
        pygame.draw.rect(surface, plate_bg, rect, border_radius=6)
        pygame.draw.rect(surface, dark, rect, 2, border_radius=6)

        # Fortress crown-shield emblem
        cx, cy, s = rect.centerx, rect.centery, rect.width / 2
        body = [(cx - s * 0.58, cy - s * 0.08), (cx + s * 0.58, cy - s * 0.08),
                (cx + s * 0.34, cy + s * 0.54), (cx - s * 0.34, cy + s * 0.54)]
        pygame.draw.polygon(surface, color, body)
        for k in (-0.48, 0, 0.48):
            pygame.draw.polygon(surface, color, [
                (cx + (k - 0.21) * s, cy - s * 0.08),
                (cx + k * s, cy - s * 0.64),
                (cx + (k + 0.21) * s, cy - s * 0.08)
            ])

        if is_alive:
            pygame.draw.circle(surface, (255, 255, 255), (cx, cy + int(s * 0.18)), max(2, int(s * 0.15)))

        self.draw_hp_bar(surface, rect, base.hp, BASE_HP)

    def draw_tank(self, surface, tank):
        """Draws a realistic top-down armored tank with tracks, sloped hull, optics, cupola, and muzzle brake."""
        cell = self.cell_rect(tank.row, tank.col)
        pad = max(3, self.cell // 9)
        outer = cell.inflate(-pad * 2, -pad * 2)
        color = PLAYER_COLORS[tank.player]
        dark = PLAYER_DARK[tank.player]
        light = PLAYER_LIGHT[tank.player]
        dx, dy = DC[tank.direction], DR[tank.direction]
        vertical = tank.direction in (UP, DOWN)

        tread_w = max(5, outer.width // 4)
        # Drop shadow beneath tank
        pygame.draw.rect(surface, SHADOW, outer.move(2, 3), border_radius=5)

        # Protruding armored caterpillar treads
        if vertical:
            treads = [
                pygame.Rect(outer.x, outer.y - 1, tread_w, outer.height + 2),
                pygame.Rect(outer.right - tread_w, outer.y - 1, tread_w, outer.height + 2),
            ]
            hull = pygame.Rect(outer.x + tread_w - 2, outer.y + 2, outer.width - 2 * tread_w + 4, outer.height - 4)
        else:
            treads = [
                pygame.Rect(outer.x - 1, outer.y, outer.width + 2, tread_w),
                pygame.Rect(outer.x - 1, outer.bottom - tread_w, outer.width + 2, tread_w),
            ]
            hull = pygame.Rect(outer.x + 2, outer.y + tread_w - 2, outer.width - 4, outer.height - 2 * tread_w + 4)

        for t in treads:
            pygame.draw.rect(surface, (30, 41, 59), t, border_radius=3)
            pygame.draw.rect(surface, (15, 23, 42), t, 1, border_radius=3)
            step = max(4, tread_w - 1)
            if vertical:
                for ky in range(t.y + 3, t.bottom - 2, step):
                    pygame.draw.line(surface, (71, 85, 105), (t.x + 1, ky), (t.right - 2, ky), 1)
            else:
                for kx in range(t.x + 3, t.right - 2, step):
                    pygame.draw.line(surface, (71, 85, 105), (kx, t.y + 1), (kx, t.bottom - 2), 1)

        # Sloped armored hull
        pygame.draw.rect(surface, color, hull, border_radius=4)
        pygame.draw.rect(surface, dark, hull, 2, border_radius=4)

        # Front glacis highlight & headlights + Rear engine deck louvres
        cx, cy = hull.center
        if vertical:
            front_y = hull.y + 3 if dy < 0 else hull.bottom - 6
            rear_y = hull.bottom - 7 if dy < 0 else hull.y + 3
            glacis = pygame.Rect(hull.x + 3, front_y, hull.width - 6, 3)
            pygame.draw.rect(surface, light, glacis, border_radius=1)
            # Twin headlights
            pygame.draw.circle(surface, (254, 249, 195), (hull.x + 4, front_y + 1), 2)
            pygame.draw.circle(surface, (254, 249, 195), (hull.right - 5, front_y + 1), 2)
            # Rear engine grilles
            for k in range(3):
                gx = hull.x + 5 + k * max(3, (hull.width - 10) // 2)
                pygame.draw.line(surface, dark, (gx, rear_y), (gx, rear_y + 4), 2)
        else:
            front_x = hull.x + 3 if dx < 0 else hull.right - 6
            rear_x = hull.right - 7 if dx < 0 else hull.x + 3
            glacis = pygame.Rect(front_x, hull.y + 3, 3, hull.height - 6)
            pygame.draw.rect(surface, light, glacis, border_radius=1)
            pygame.draw.circle(surface, (254, 249, 195), (front_x + 1, hull.y + 4), 2)
            pygame.draw.circle(surface, (254, 249, 195), (front_x + 1, hull.bottom - 5), 2)
            for k in range(3):
                gy = hull.y + 5 + k * max(3, (hull.height - 10) // 2)
                pygame.draw.line(surface, dark, (rear_x, gy), (rear_x + 4, gy), 2)

        # Heavy Cannon Barrel + Turret Mantlet + Muzzle Brake (drawn under turret dome rim cleanly)
        barrel_len = max(14, int(self.cell * 0.48))
        barrel_w = max(4, self.cell // 8)
        ex, ey = int(cx + dx * barrel_len), int(cy + dy * barrel_len)
        # Mantlet collar
        mx, my = int(cx + dx * (outer.width * 0.28)), int(cy + dy * (outer.height * 0.28))
        pygame.draw.line(surface, dark, (cx, cy), (mx, my), barrel_w + 4)
        # Main barrel tube + inner metallic highlight
        pygame.draw.line(surface, (15, 23, 42), (cx, cy), (ex, ey), barrel_w + 2)
        pygame.draw.line(surface, light, (cx, cy), (ex, ey), max(2, barrel_w - 2))
        # Muzzle brake tip perpendicular to barrel
        px, py = -dy, dx
        tip_w = max(3, barrel_w // 2 + 1)
        pygame.draw.line(surface, dark, (ex - px * tip_w, ey - py * tip_w), (ex + px * tip_w, ey + py * tip_w), 4)

        # Rotating Armored Turret Dome + Commander Cupola Hatch
        turret_r = max(6, min(hull.width, hull.height) // 2 - 1)
        pygame.draw.circle(surface, dark, (cx + 1, cy + 1), turret_r)
        pygame.draw.circle(surface, color, (cx, cy), turret_r)
        pygame.draw.circle(surface, dark, (cx, cy), turret_r, 2)
        pygame.draw.circle(surface, light, (cx - dx * 1, cy - dy * 1), max(2, turret_r - 3), 1)
        # Off-center commander hatch
        hx, hy = int(cx - dy * max(2, turret_r // 3)), int(cy + dx * max(2, turret_r // 3))
        pygame.draw.circle(surface, dark, (hx, hy), max(2, turret_r // 3))
        pygame.draw.circle(surface, light, (hx, hy), max(1, turret_r // 4))

        # Overhead floating health bar
        self.draw_hp_bar(surface, outer, tank.hp, TANK_HP)

    def draw_trails(self, surface, state, board):
        """Draws crisp high-contrast projectile trails and impact bursts on light ground."""
        for trail in getattr(state, "trails", ()):
            cells = trail["cells"]
            if len(cells) < 2:
                continue
            color = PLAYER_COLORS[trail["owner"]]
            dark = PLAYER_DARK[trail["owner"]]
            start = self.cell_rect(*cells[0]).center
            end = self.cell_rect(*cells[-1]).center
            previous = surface.get_clip()
            surface.set_clip(board)
            width = max(3, self.cell // 10)
            pygame.draw.line(surface, PLAYER_LIGHT[trail["owner"]], start, end, width + 4)
            pygame.draw.line(surface, color, start, end, width)
            pygame.draw.line(surface, dark, start, end, max(1, width - 2))
            if trail["hit"]:
                self.draw_impact(surface, end, color)
            else:
                pygame.draw.circle(surface, dark, end, max(4, self.cell // 9))
            surface.set_clip(previous)

    def draw_impact(self, surface, center, color):
        cx, cy = center
        r = self.cell * 0.44
        for k in range(8):
            dx, dy = pygame.math.Vector2(1, 0).rotate(45 * k + 22.5)
            inner, outer = r * 0.28, r if k % 2 == 0 else r * 0.72
            pygame.draw.line(surface, color, (cx + dx * inner, cy + dy * inner),
                             (cx + dx * outer, cy + dy * outer), max(2, self.cell // 12))
        pygame.draw.circle(surface, color, center, max(4, int(r * 0.34)))
        pygame.draw.circle(surface, (254, 240, 138), center, max(2, int(r * 0.18)))

    def draw_bullet(self, surface, bullet):
        rect = self.cell_rect(bullet.row, bullet.col)
        cx, cy = rect.center
        tail = (cx - DC[bullet.direction] * self.cell * 0.45, cy - DR[bullet.direction] * self.cell * 0.45)
        pygame.draw.line(surface, PLAYER_COLORS[bullet.owner], tail, (cx, cy), max(3, self.cell // 9))
        pygame.draw.circle(surface, BULLET_RIM, (cx, cy), max(5, self.cell // 7))
        pygame.draw.circle(surface, PLAYER_COLORS[bullet.owner], (cx, cy), max(4, self.cell // 9))
        pygame.draw.circle(surface, BULLET_CORE, (cx, cy), max(2, self.cell // 13))

    def draw_hp_bar(self, surface, rect, hp, max_hp):
        """Clean capsule HP bar."""
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
        bar_y = max(self.origin[1] + 2, rect.y - 8)
        bar_rect = pygame.Rect(rect.x, bar_y, bar_w, bar_h)
        pygame.draw.rect(surface, PANEL, bar_rect, border_radius=2)
        fill_w = max(0, int(bar_w * ratio))
        if fill_w > 0:
            pygame.draw.rect(surface, color, pygame.Rect(bar_rect.x, bar_rect.y, fill_w, bar_h), border_radius=2)
        pygame.draw.rect(surface, (148, 163, 184), bar_rect, 1, border_radius=2)
