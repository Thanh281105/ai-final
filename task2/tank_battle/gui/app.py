"""PyGame application: Light Blue & White arena menu and real-time telemetry dashboard."""

import math
import threading
import time

import pygame

from ..agents import CUTOFF_MINIMAX, build_registry
from ..agents.search_agents import WIN_SCORE
from ..core.constants import Action, BASE_HP, DRAW, PLAYER_NAMES, TANK_HP
from ..core.map_loader import list_maps, load_map
from ..match import Match
from .renderer import (
    ACCENT_BLUE, ACCENT_DARK, ACCENT_LIGHT, ALERT, BG, BoardRenderer, HP_HIGH, HP_MID, MUTED,
    PANEL, PANEL_BORDER, PANEL_SOFT, PLAYER_COLORS, RULE, SHADOW, TEXT, draw_pips, font,
)

WINDOW = (1120, 720)
BOARD_RECT = (20, 25, 670, 670)
PANEL_X = 710
PANEL_W = WINDOW[0] - PANEL_X - 20

P1_KEYS = {pygame.K_UP: Action.MOVE_UP, pygame.K_DOWN: Action.MOVE_DOWN, pygame.K_LEFT: Action.MOVE_LEFT,
           pygame.K_RIGHT: Action.MOVE_RIGHT, pygame.K_SPACE: Action.FIRE, pygame.K_RETURN: Action.STAY}
P2_KEYS = {pygame.K_w: Action.MOVE_UP, pygame.K_s: Action.MOVE_DOWN, pygame.K_a: Action.MOVE_LEFT,
           pygame.K_d: Action.MOVE_RIGHT, pygame.K_f: Action.FIRE, pygame.K_e: Action.STAY}

DELAYS = [0, 20, 50, 100, 250, 500]
TIME_LIMITS = [None, 0.5, 1.0, 2.0]


class Fonts:
    def __init__(self):
        self.title = font(36, "head", bold=True)
        self.big = font(24, "head", bold=True)
        self.head = font(18, "head", bold=True)
        self.head_small = font(14, "head", bold=True)     # long agent names in the player cards
        self.normal = font(15, "text")
        self.small = font(13, "text")
        self.mono = font(12, "text", bold=True)


def draw_text(surface, font_, text, pos, color=TEXT, center=False, right=False):
    image = font_.render(text, True, color)
    rect = image.get_rect()
    if center:
        rect.center = pos
    elif right:
        rect.topright = pos
    else:
        rect.topleft = pos
    surface.blit(image, rect)
    return rect


def draw_fit_text(surface, max_width, start_size, min_size, text, center_pos, color=TEXT):
    """Renders bold heading scaled down if needed so it never overflows horizontally."""
    for size in range(start_size, min_size - 1, -2):
        f_ = font(size, "head", bold=True)
        if f_.size(text)[0] <= max_width or size == min_size:
            return draw_text(surface, f_, text, center_pos, color, center=True)
    return pygame.Rect(0, 0, 0, 0)


def describe_value(value):
    """Minimax value of the root as formatted text."""
    if value is None:
        return "none"
    if value >= WIN_SCORE / 2:
        return "Win (+1M)"
    if value <= -WIN_SCORE / 2:
        return "Loss (-1M)"
    return "0.0" if abs(value) < 0.05 else "%+.1f" % value


class MenuScreen:
    """Up/Down choose option, Left/Right change, Enter starts, F5 reloads plugins."""

    def __init__(self, app, settings=None):
        self.app = app
        self.registry, self.errors = build_registry()
        self.maps = list_maps()
        names = [e.name for e in self.registry]
        settings = settings or {}

        p1_idx = names.index(settings.get("p1", names[0])) if settings.get("p1") in names else 0
        p2_default = CUTOFF_MINIMAX if CUTOFF_MINIMAX in names else (names[1] if len(names) > 1 else names[0])
        p2_idx = names.index(settings["p2"]) if settings.get("p2") in names else names.index(p2_default)

        self.choice = {
            "p1": p1_idx,
            "p2": p2_idx,
            "map": self.maps.index(settings["map"]) if settings.get("map") in self.maps else
            (self.maps.index("classic") if "classic" in self.maps else 0),
            "delay": DELAYS.index(settings.get("delay", 50)) if settings.get("delay", 50) in DELAYS else 2,
            "limit": TIME_LIMITS.index(settings.get("limit", 1.0)) if settings.get("limit", 1.0) in TIME_LIMITS else 2,
        }
        self.rows = ["p1", "p2", "map", "delay", "limit", "start"]
        self.selected = 0
        self.row_rects = []
        self.preview = BoardRenderer((720, 195, 360, 360))
        self.preview_name, self.preview_state = None, None

    def option_text(self, row):
        if row in ("p1", "p2"):
            return self.registry[self.choice[row]].name
        if row == "map":
            return self.maps[self.choice["map"]]
        if row == "delay":
            return "%d ms (real-time)" % DELAYS[self.choice["delay"]] if DELAYS[self.choice["delay"]] <= 50 else "%d ms" % DELAYS[self.choice["delay"]]
        if row == "limit":
            v = TIME_LIMITS[self.choice["limit"]]
            return "no limit" if v is None else "%.1f s" % v
        return ""

    def sizes(self):
        return {"p1": len(self.registry), "p2": len(self.registry), "map": len(self.maps),
                "delay": len(DELAYS), "limit": len(TIME_LIMITS)}

    def change(self, row, delta):
        if row in self.choice:
            self.choice[row] = (self.choice[row] + delta) % self.sizes()[row]

    def handle(self, event):
        if event.type == pygame.KEYDOWN:
            row = self.rows[self.selected]
            if event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(self.rows)
            elif event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(self.rows)
            elif event.key == pygame.K_LEFT:
                self.change(row, -1)
            elif event.key == pygame.K_RIGHT:
                self.change(row, 1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.start()
            elif event.key == pygame.K_F5:
                self.__init__(self.app, self.settings())
            elif event.key == pygame.K_ESCAPE:
                self.app.running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.row_rects):
                if rect.collidepoint(event.pos):
                    self.selected = i
                    if self.rows[i] == "start":
                        self.start()
                    else:
                        self.change(self.rows[i], -1 if event.pos[0] < rect.centerx else 1)

    def settings(self):
        return {"p1": self.registry[self.choice["p1"]].name, "p2": self.registry[self.choice["p2"]].name,
                "map": self.maps[self.choice["map"]], "delay": DELAYS[self.choice["delay"]],
                "limit": TIME_LIMITS[self.choice["limit"]]}

    def start(self):
        s = self.settings()
        entries = [self.registry[self.choice["p1"]], self.registry[self.choice["p2"]]]
        self.app.screen_obj = GameScreen(self.app, entries, s["map"], s["delay"], s["limit"], s)

    def update(self):
        pass

    def draw(self, surface):
        f = self.app.fonts
        surface.fill(BG)
        left = 40

        # Header Badge & Title
        badge_rect = pygame.Rect(left, 28, 186, 26)
        pygame.draw.rect(surface, PANEL_SOFT, badge_rect, border_radius=13)
        pygame.draw.rect(surface, ACCENT_LIGHT, badge_rect, 1, border_radius=13)
        draw_text(surface, f.mono, "AI ADVERSARIAL ARENA", badge_rect.center, ACCENT_DARK, center=True)

        draw_text(surface, f.title, "Tank Battle Simulation", (left, 62), TEXT)
        draw_text(surface, f.normal, "Adversarial search & tactical heuristics in a bright real-time arena.",
                  (left, 108), MUTED)

        labels = {
            "p1": "%s Agent" % PLAYER_NAMES[0],
            "p2": "%s Agent" % PLAYER_NAMES[1],
            "map": "Arena Map",
            "delay": "Turn Speed / Delay",
            "limit": "Time Budget / Move",
            "start": "",
        }
        self.row_rects = []
        y = 152

        for i, row in enumerate(self.rows):
            is_start = (row == "start")
            rect = pygame.Rect(left, y, 636, 52 if is_start else 48)
            self.row_rects.append(rect)
            selected = (i == self.selected)

            if is_start:
                rect.y += 12
                btn_color = ACCENT_DARK if selected else ACCENT_BLUE
                pygame.draw.rect(surface, SHADOW, rect.move(0, 2), border_radius=8)
                pygame.draw.rect(surface, btn_color, rect, border_radius=8)
                if selected:
                    pygame.draw.rect(surface, ACCENT_LIGHT, rect, 2, border_radius=8)
                draw_text(surface, f.big, "Start Match", rect.center, PANEL, center=True)
            else:
                card_bg = PANEL_SOFT if selected else PANEL
                pygame.draw.rect(surface, card_bg, rect, border_radius=8)
                pygame.draw.rect(surface, ACCENT_BLUE if selected else PANEL_BORDER, rect, 2 if selected else 1, border_radius=8)

                tag_color = PLAYER_COLORS[0] if row == "p1" else (PLAYER_COLORS[1] if row == "p2" else (ACCENT_BLUE if selected else PANEL_BORDER))
                pygame.draw.rect(surface, tag_color, (rect.x, rect.y + 6, 4, rect.h - 12), border_radius=2)

                draw_text(surface, f.normal, labels[row], (rect.x + 18, rect.y + 14), TEXT)
                val_x = rect.right - 36
                val_rect = draw_text(surface, f.head, self.option_text(row), (val_x, rect.y + 13),
                                     ACCENT_DARK if selected else TEXT, right=True)

                if selected:
                    cy = rect.centery
                    for ax, d in ((rect.right - 16, 1), (val_rect.left - 14, -1)):
                        pygame.draw.polygon(surface, ACCENT_BLUE, [(ax - 4 * d, cy - 5), (ax + 4 * d, cy), (ax - 4 * d, cy + 5)])

            y += 56

        # Description Card below
        row = self.rows[self.selected]
        note_box = pygame.Rect(left, y + 18, 636, 72)
        pygame.draw.rect(surface, PANEL, note_box, border_radius=8)
        pygame.draw.rect(surface, PANEL_BORDER, note_box, 1, border_radius=8)

        if row in ("p1", "p2"):
            entry = self.registry[self.choice[row]]
            draw_text(surface, f.normal, entry.description[:66], (note_box.x + 16, note_box.y + 14), TEXT)
            draw_text(surface, f.small, "Provider: %s" % entry.source, (note_box.x + 16, note_box.y + 40), MUTED)
        elif row == "limit":
            draw_text(surface, f.normal, "Max search duration per turn. Exceeding agents play STAY.",
                      (note_box.x + 16, note_box.y + 14), TEXT)
            draw_text(surface, f.small, "Guarantees anytime responsiveness and avoids UI freezes.",
                      (note_box.x + 16, note_box.y + 40), MUTED)
        else:
            draw_text(surface, f.normal, "Press Enter or Space to initiate duel simulation.",
                      (note_box.x + 16, note_box.y + 14), TEXT)
            draw_text(surface, f.small, "Arrow Keys navigate options  |  F5 reloads custom agents.",
                      (note_box.x + 16, note_box.y + 40), MUTED)

        # Map Preview Card
        preview_card = pygame.Rect(704, 152, 392, 438)
        pygame.draw.rect(surface, PANEL, preview_card, border_radius=10)
        pygame.draw.rect(surface, PANEL_BORDER, preview_card, 1, border_radius=10)
        draw_text(surface, f.mono, "ARENA PREVIEW", (720, 166), MUTED)

        name = self.maps[self.choice["map"]]
        if self.preview_name != name:
            self.preview_name, self.preview_state = name, load_map(name)
        self.preview.draw(surface, self.preview_state)
        st = self.preview_state
        draw_text(surface, f.small, "Map: %s (%dx%d grid)" % (name, st.width, st.height),
                  (720, 564), ACCENT_DARK)


class GameScreen:
    def __init__(self, app, entries, map_name, delay_ms, move_time_limit, settings):
        self.app = app
        self.settings = settings
        self.entries = entries
        self.map_name = map_name
        self.delay = delay_ms / 1000.0
        self.agents = [entries[p].create(p) for p in (0, 1)]
        self.match = Match(load_map(map_name), self.agents, move_time_limit)
        self.renderer = BoardRenderer(BOARD_RECT)
        self.paused = False
        self.step_once = False
        self.next_turn_at = time.monotonic() + 0.1
        self.last_record = None
        self.node_history = [[], []]
        self.log = []
        self.worker = None
        self.worker_result = None
        self.anim_tick = 0

    def is_human(self, player):
        return getattr(self.agents[player], "is_human", False)

    def humans_ready(self):
        return all((not self.is_human(p)) or self.agents[p].has_action() for p in (0, 1))

    def handle(self, event):
        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        if k == pygame.K_ESCAPE:
            self.app.screen_obj = MenuScreen(self.app, self.settings)
        elif k == pygame.K_r:
            self.app.screen_obj = GameScreen(
                self.app, self.entries, self.map_name, self.delay * 1000, self.match.move_time_limit, self.settings)
        elif k == pygame.K_p:
            self.paused = not self.paused
        elif k == pygame.K_n:
            self.paused = True
            self.step_once = True
        elif k in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
            self.delay = max(0.0, self.delay * 0.5)
        elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.delay = 0.05 if self.delay == 0 else min(2.0, self.delay * 2)
        if k in P1_KEYS and self.is_human(0):
            self.agents[0].queue_action(P1_KEYS[k])
        if k in P2_KEYS and self.is_human(1):
            self.agents[1].queue_action(P2_KEYS[k])

    def update(self):
        self.anim_tick += 1
        if self.match.over:
            return
        if self.worker is not None:
            if not self.worker.is_alive():
                self.worker = None
                self._commit(self.worker_result)
            return
        if self.paused and not self.step_once:
            return
        if not self.humans_ready():
            return
        if not self.step_once and time.monotonic() < self.next_turn_at:
            return

        self.step_once = False
        self.worker_result = None

        def run():
            self.worker_result = self.match.step()

        self.worker = threading.Thread(target=run, daemon=True)
        self.worker.start()

    def _commit(self, record):
        self.last_record = record
        for p in (0, 1):
            self.node_history[p].append(record.stats[p].get("nodes", 0))
            if record.notes[p]:
                self.log.append((record.turn, None, None, "t%d %s: %s" % (record.turn, PLAYER_NAMES[p], record.notes[p])))
        self.log.append((record.turn, record.actions[0].value, record.actions[1].value, None))
        self.log = self.log[-5:]
        self.next_turn_at = time.monotonic() + self.delay

    def draw(self, surface):
        f = self.app.fonts
        surface.fill(BG)
        state = self.match.state
        self.renderer.draw(surface, state)

        x, y, right = PANEL_X, 20, PANEL_X + PANEL_W

        # Header Title
        draw_text(surface, f.big, self.map_name.upper(), (x, y), TEXT)
        draw_text(surface, f.head, "Cycle %d / %d" % (state.turn, state.max_turns), (right, y + 4), MUTED, right=True)
        y += 34

        # Progress bar
        bar = pygame.Rect(x, y, PANEL_W, 6)
        pygame.draw.rect(surface, PANEL_BORDER, bar, border_radius=3)
        prog_w = int(bar.w * state.turn / max(1, state.max_turns))
        if prog_w > 0:
            pygame.draw.rect(surface, ACCENT_BLUE, (bar.x, bar.y, prog_w, bar.h), border_radius=3)
        y += 14

        # Player 1 and Player 2 Cards
        for p in (0, 1):
            y = self._draw_player_panel(surface, p, x, y)

        # Status Line
        status_box = pygame.Rect(x, y, PANEL_W, 30)
        pygame.draw.rect(surface, PANEL, status_box, border_radius=6)
        pygame.draw.rect(surface, PANEL_BORDER, status_box, 1, border_radius=6)

        if self.match.over:
            status, color = "Game Completed", ACCENT_DARK
        elif self.paused:
            status, color = "PAUSED (Press P to resume, N to step)", HP_MID
        elif self.worker:
            dots = "." * ((self.anim_tick // 15) % 4)
            status, color = "AI calculating move" + dots, ACCENT_BLUE
        elif not self.humans_ready():
            status, color = "Waiting for human input...", HP_MID
        else:
            status, color = "Real-time play active", HP_HIGH

        draw_text(surface, f.small, status, (status_box.x + 12, status_box.y + 7), color)
        y += 38

        # Action Log Feed
        log_box = pygame.Rect(x, y, PANEL_W, 98)
        pygame.draw.rect(surface, PANEL, log_box, border_radius=8)
        pygame.draw.rect(surface, PANEL_BORDER, log_box, 1, border_radius=8)
        draw_text(surface, f.mono, "TURN LOG", (log_box.x + 12, log_box.y + 7), MUTED)

        ly = log_box.y + 26
        col2_x = log_box.x + 196
        for turn, a1, a2, note in self.log[-4:]:
            if note:
                draw_text(surface, f.small, note[:44], (log_box.x + 12, ly), ALERT)
            else:
                draw_text(surface, f.mono, "#%02d" % turn, (log_box.x + 12, ly), MUTED)
                draw_text(surface, f.mono, a1, (log_box.x + 48, ly), PLAYER_COLORS[0])
                draw_text(surface, f.mono, a2, (col2_x, ly), PLAYER_COLORS[1])
            ly += 16

        # Footer Shortcuts
        help_y = WINDOW[1] - 32
        draw_text(surface, f.small, "[P] Pause  [N] Step  [R] Restart  [+/-] Speed  [Esc] Menu", (x, help_y), MUTED)

        if self.match.over:
            self._draw_game_over(surface)

    def _draw_player_panel(self, surface, p, x, y):
        f = self.app.fonts
        state = self.match.state
        color = PLAYER_COLORS[p]
        card = pygame.Rect(x, y, PANEL_W, 200)

        pygame.draw.rect(surface, PANEL, card, border_radius=8)
        pygame.draw.rect(surface, PANEL_BORDER, card, 1, border_radius=8)
        pygame.draw.rect(surface, color, (card.x, card.y + 6, 4, card.h - 12), border_radius=2)

        cx, cy, right = x + 16, y + 10, card.right - 14
        name = self.agents[p].name[:40]
        name_font = f.head if f.head.size(name)[0] <= PANEL_W - 110 else f.head_small
        draw_text(surface, name_font, name, (cx, cy + (0 if name_font is f.head else 3)), color)
        draw_text(surface, f.mono, PLAYER_NAMES[p], (right, cy + 3), color, right=True)
        cy += 28

        for label, hp, max_hp in (("Tank HP", state.tanks[p].hp, TANK_HP), ("Base HP", state.bases[p].hp, BASE_HP)):
            draw_text(surface, f.small, label, (cx, cy), MUTED)
            end = draw_pips(surface, cx + 62, cy + 2, max(0, hp), max_hp, color, size=10, gap=3)
            draw_text(surface, f.mono, "%d" % max(0, hp), (end + 6, cy + 1), TEXT)
            cy += 18
        cy += 4

        rec = self.last_record
        if rec is None:
            draw_text(surface, f.small, "Awaiting first move...", (cx, cy), MUTED)
            return card.bottom + 8

        stats = rec.stats[p]
        action_name = rec.actions[p].value
        latency_ms = rec.times[p] * 1000

        draw_text(surface, f.small, "Last Move", (cx, cy), MUTED)
        badge_text = "%s (%.1f ms)" % (action_name, latency_ms)
        draw_text(surface, f.mono, badge_text, (right, cy + 1), HP_HIGH if latency_ms < 30 else TEXT, right=True)
        cy += 20

        if not stats.get("nodes"):
            draw_text(surface, f.small, "Direct reflex / rule-based agent", (cx, cy), MUTED)
            return card.bottom + 8

        depth = stats.get("depth") or 0
        reached = ("%d plies" % stats.get("max_ply", 0) if not depth else
                   "%d cycles (%d plies)" % (depth, depth * 2))

        rows = [
            ("Nodes Visited", "{:,}".format(stats["nodes"])),
            ("Cutoffs (Pruned)", "{:,}".format(stats["cutoffs"])),
            ("Search Depth", reached + (" (timeout)" if stats.get("timed_out") else "")),
            ("Peak Mem / TT", "{:,} / {:,} nodes".format(stats.get("peak_memory", 0), stats.get("tt_entries", 0))),
            ("Minimax Value", describe_value(stats.get("value")))
        ]

        for label, val in rows:
            draw_text(surface, f.small, label, (cx, cy), MUTED)
            draw_text(surface, f.mono, val, (right, cy + 1), TEXT, right=True)
            cy += 16

        self._draw_effort(surface, pygame.Rect(cx, cy + 2, card.right - 14 - cx, card.bottom - cy - 8), p)
        return card.bottom + 8

    def _draw_effort(self, surface, rect, p):
        history = self.node_history[p][-rect.w // 5:]
        pygame.draw.line(surface, RULE, rect.bottomleft, rect.bottomright, 1)
        if not history:
            return
        top = math.log10(max(max(history), 10))
        for i, n in enumerate(history):
            h = int((rect.h - 1) * math.log10(n) / top) if n > 1 else 1
            pygame.draw.rect(surface, PLAYER_COLORS[p], (rect.x + i * 5, rect.bottom - h, 3, h), border_radius=1)

    def _draw_game_over(self, surface):
        f = self.app.fonts
        w = self.match.winner
        text = "DRAW MATCH" if w == DRAW else "%s VICTORIOUS" % PLAYER_NAMES[w].upper()
        color = TEXT if w == DRAW else PLAYER_COLORS[w]

        box = pygame.Rect(0, 0, 500, 176)
        box.center = (BOARD_RECT[0] + BOARD_RECT[2] // 2, BOARD_RECT[1] + BOARD_RECT[3] // 2)

        # Clean crisp bright modal with soft drop shadow
        pygame.draw.rect(surface, SHADOW, box.move(0, 6), border_radius=12)
        pygame.draw.rect(surface, PANEL, box, border_radius=12)
        pygame.draw.rect(surface, color, box, 2, border_radius=12)

        # Accent header bar inside modal
        badge_w = 136
        badge = pygame.Rect(box.centerx - badge_w // 2, box.y + 18, badge_w, 22)
        pygame.draw.rect(surface, PANEL_SOFT, badge, border_radius=11)
        draw_text(surface, f.mono, "MATCH RESULT", badge.center, ACCENT_DARK, center=True)

        # Auto-fit title inside box width (strictly prevents horizontal overflow!)
        draw_fit_text(surface, box.width - 40, 34, 18, text, (box.centerx, box.centery - 6), color)

        state = self.match.state
        if w == DRAW and state.turn >= state.max_turns:
            reason = "Turn limit reached (%d cycles)" % state.max_turns
        elif w == DRAW:
            reason = "Mutual destruction in cycle %d" % state.turn
        else:
            reason = "Victory secured in cycle %d" % state.turn

        draw_text(surface, f.normal, "%s." % reason, (box.centerx, box.centery + 32), TEXT, center=True)
        draw_text(surface, f.small, "Press [R] to replay, [Esc] to return to menu.", (box.centerx, box.centery + 58), MUTED, center=True)


class TankBattleApp:
    def __init__(self, settings=None, autostart=False):
        pygame.init()
        pygame.display.set_caption("Tank Battle - Adversarial Search Arena")
        self.surface = pygame.display.set_mode(WINDOW)
        self.clock = pygame.time.Clock()
        self.fonts = Fonts()
        self.running = True
        self.screen_obj = MenuScreen(self, settings)
        if autostart:
            self.screen_obj.start()

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                else:
                    self.screen_obj.handle(event)
            self.screen_obj.update()
            self.screen_obj.draw(self.surface)
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()
