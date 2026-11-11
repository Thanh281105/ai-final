"""PyGame application: a menu to pick agents/map and a game screen that runs the match in real time.

Agents think in a background thread so the window stays responsive while a search is running.
"""

import math
import threading
import time

import pygame

from ..agents import build_registry
from ..core.constants import Action, DRAW, PLAYER_NAMES
from ..core.map_loader import list_maps, load_map
from ..match import Match
from .renderer import (ALERT, BG, BoardRenderer, FIELD, MUTED, PANEL, PLAYER_COLORS, RULE, TEXT, draw_pips,
                       font)
from ..agents.search_agents import WIN_SCORE
from ..core.constants import BASE_HP, TANK_HP

WINDOW = (1000, 680)
BOARD_RECT = (20, 20, 640, 640)
PANEL_X = 680
PANEL_W = WINDOW[0] - PANEL_X - 20

P1_KEYS = {pygame.K_UP: Action.MOVE_UP, pygame.K_DOWN: Action.MOVE_DOWN, pygame.K_LEFT: Action.MOVE_LEFT,
           pygame.K_RIGHT: Action.MOVE_RIGHT, pygame.K_SPACE: Action.FIRE, pygame.K_RETURN: Action.STAY}
P2_KEYS = {pygame.K_w: Action.MOVE_UP, pygame.K_s: Action.MOVE_DOWN, pygame.K_a: Action.MOVE_LEFT,
           pygame.K_d: Action.MOVE_RIGHT, pygame.K_f: Action.FIRE, pygame.K_e: Action.STAY}

DELAYS = [0, 100, 250, 500, 1000]
TIME_LIMITS = [None, 1.0, 2.0, 5.0]


class Fonts:
    def __init__(self):
        self.title = font(76, "head")
        self.big = font(34, "head")
        self.head = font(26, "head")
        self.normal = font(17)
        self.small = font(14)


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


def describe_value(value):
    """Minimax value of the root as text. Utilities are +-WIN_SCORE, everything else is an EVAL."""
    if value is None:
        return "none"
    if value >= WIN_SCORE / 2:
        return "forced win"
    if value <= -WIN_SCORE / 2:
        return "forced loss"
    return "0" if abs(value) < 0.5 else "%+.0f" % value


class MenuScreen:
    """Up/Down choose a row, Left/Right change it, Enter starts, F5 reloads plugins."""

    def __init__(self, app, settings=None):
        self.app = app
        self.registry, self.errors = build_registry()
        self.maps = list_maps()
        names = [e.name for e in self.registry]
        settings = settings or {}
        self.choice = {
            "p1": names.index(settings.get("p1", names[0])) if settings.get("p1") in names else 0,
            # Default opponent: plain Minimax, so the first match shows what the heuristic adds.
            "p2": names.index(settings["p2"]) if settings.get("p2") in names else
            (names.index("Minimax") if "Minimax" in names else 1),
            "map": self.maps.index(settings["map"]) if settings.get("map") in self.maps else
            (self.maps.index("classic") if "classic" in self.maps else 0),
            "delay": DELAYS.index(settings.get("delay", 250)) if settings.get("delay", 250) in DELAYS else 2,
            "limit": TIME_LIMITS.index(settings.get("limit", 2.0)) if settings.get("limit", 2.0) in TIME_LIMITS else 2,
        }
        self.rows = ["p1", "p2", "map", "delay", "limit", "start"]
        self.selected = 0
        self.row_rects = []
        self.preview = BoardRenderer((620, 184, 332, 332))
        self.preview_name, self.preview_state = None, None

    def option_text(self, row):
        if row in ("p1", "p2"):
            return self.registry[self.choice[row]].name
        if row == "map":
            return self.maps[self.choice["map"]]
        if row == "delay":
            return "%d ms" % DELAYS[self.choice["delay"]]
        if row == "limit":
            v = TIME_LIMITS[self.choice["limit"]]
            return "no limit" if v is None else "%.0f s" % v
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
        left = 48
        draw_text(surface, f.title, "Tank Battle", (left, 34))
        draw_text(surface, f.normal, "A turn-based duel played by adversarial search: Minimax, Alpha-Beta,",
                  (left, 112), MUTED)
        draw_text(surface, f.normal, "Heuristic Minimax and Heuristic Alpha-Beta.", (left, 134), MUTED)
        labels = {"p1": PLAYER_NAMES[0], "p2": PLAYER_NAMES[1], "map": "Map", "delay": "Pause between cycles",
                  "limit": "Time allowed per move", "start": ""}
        self.row_rects = []
        y = 184
        for i, row in enumerate(self.rows):
            rect = pygame.Rect(left, y, 520, 44 if row != "start" else 52)
            self.row_rects.append(rect)
            selected = i == self.selected
            if row == "start":
                rect.y += 10
                pygame.draw.rect(surface, PLAYER_COLORS[0] if selected else PANEL, rect)
                pygame.draw.rect(surface, PLAYER_COLORS[0], rect, 2)
                draw_text(surface, f.big, "Start the match", rect.center, FIELD if selected else PLAYER_COLORS[0],
                          center=True)
            else:
                if selected:
                    pygame.draw.rect(surface, PANEL, rect)
                    pygame.draw.rect(surface, TEXT, (rect.x, rect.y, 3, rect.h))
                pygame.draw.line(surface, RULE, (rect.x, rect.bottom), (rect.right, rect.bottom))
                color = PLAYER_COLORS[0] if row == "p1" else PLAYER_COLORS[1] if row == "p2" else MUTED
                draw_text(surface, f.normal, labels[row], (rect.x + 16, rect.y + 12), color)
                draw_text(surface, f.head, self.option_text(row), (rect.right - 40, rect.y + 9),
                          TEXT if selected else MUTED, right=True)
                if selected:
                    cy = rect.centery
                    for x, d in ((rect.right - 22, 1), (rect.right - 290, -1)):
                        pygame.draw.polygon(surface, TEXT, [(x - 4 * d, cy - 6), (x + 4 * d, cy), (x - 4 * d, cy + 6)])
            y += 46
        row = self.rows[self.selected]
        note_y = self.row_rects[-1].bottom + 18
        if row in ("p1", "p2"):
            entry = self.registry[self.choice[row]]
            draw_text(surface, f.small, entry.description, (left, note_y), TEXT)
            draw_text(surface, f.small, "Source: %s" % entry.source, (left, note_y + 20), MUTED)
        elif row == "limit":
            draw_text(surface, f.small, "An agent that takes longer plays STAY for that cycle.", (left, note_y), TEXT)
        help_lines = [
            "Up and Down choose a row. Left and Right change it. Enter starts. F5 reloads plugins.",
            "To add another group's agent, drop its .py file into the plugins folder.",
            "Human players: P1 arrows, Space fires, Enter stays. P2 WASD, F fires, E stays.",
        ]
        for k, line in enumerate(help_lines):
            draw_text(surface, f.small, line, (left, 592 + 22 * k), MUTED)
        for k, err in enumerate(self.errors[:2]):
            draw_text(surface, f.small, "Plugin could not be loaded: " + err[:90], (left, 548 + 18 * k), ALERT)

        # Preview of the chosen map, drawn by the same renderer as the game.
        name = self.maps[self.choice["map"]]
        if self.preview_name != name:
            self.preview_name, self.preview_state = name, load_map(name)
        self.preview.draw(surface, self.preview_state)
        st = self.preview_state
        draw_text(surface, f.small, "%s, %d by %d cells, draw after %d cycles" % (
            name, st.width, st.height, st.max_turns), (self.preview.rect.x, self.preview.rect.bottom + 10), MUTED)


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
        self.single_step = False
        self.worker = None
        self.decisions = None
        self.last_step_time = 0.0
        self.last_record = None
        self.log = []
        self.node_history = ([], [])     # nodes visited per move, for the effort chart

    # ------------------------------------------------------------------ input
    def handle(self, event):
        if event.type != pygame.KEYDOWN:
            return
        for player, keymap in ((0, P1_KEYS), (1, P2_KEYS)):
            agent = self.agents[player]
            if getattr(agent, "is_human", False) and event.key in keymap:
                agent.queue_action(keymap[event.key])
                return
        if event.key == pygame.K_ESCAPE:
            self.app.screen_obj = MenuScreen(self.app, self.settings)
        elif event.key == pygame.K_p:
            self.paused = not self.paused
        elif event.key == pygame.K_n:
            self.paused, self.single_step = True, True
        elif event.key == pygame.K_r:
            if self.worker is None:
                self.__init__(self.app, self.entries, self.map_name, self.delay * 1000,
                              self.match.move_time_limit, self.settings)
        elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self.delay = max(0.0, self.delay - 0.1)
        elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.delay = min(2.0, self.delay + 0.1)

    # ------------------------------------------------------------------ game loop
    def humans_ready(self):
        return all(a.has_action() for a in self.agents if getattr(a, "is_human", False))

    def _think(self):
        self.decisions = [self.match.decide(p) for p in (0, 1)]

    def update(self):
        if self.worker is not None:
            if self.worker.is_alive():
                return
            self.worker = None
            self.last_record = self.match.apply(self.decisions)
            self.last_step_time = time.perf_counter()
            self._log_record(self.last_record)
            for p in (0, 1):
                self.node_history[p].append(self.last_record.stats[p].get("nodes", 0))
            return
        if self.match.over or (self.paused and not self.single_step):
            return
        if time.perf_counter() - self.last_step_time < self.delay or not self.humans_ready():
            return
        self.single_step = False
        self.worker = threading.Thread(target=self._think, daemon=True)
        self.worker.start()

    def _log_record(self, record):
        self.log.append((record.turn + 1, record.actions[0].value, record.actions[1].value, ""))
        for p in (0, 1):
            if record.notes[p]:
                self.log.append((None, "", "", "P%d: %s" % (p + 1, record.notes[p])))
        self.log = self.log[-5:]

    # ------------------------------------------------------------------ drawing
    def draw(self, surface):
        f = self.app.fonts
        surface.fill(BG)
        state = self.match.state
        self.renderer.draw(surface, state)

        x, y, right = PANEL_X, 14, PANEL_X + PANEL_W
        draw_text(surface, f.big, self.map_name, (x, y))
        draw_text(surface, f.head, "cycle %d of %d" % (state.turn, state.max_turns), (right, y + 6), MUTED, right=True)
        y += 44
        bar = pygame.Rect(x, y, PANEL_W, 4)       # how close the game is to the turn limit (a draw)
        pygame.draw.rect(surface, RULE, bar)
        pygame.draw.rect(surface, TEXT, (bar.x, bar.y, int(bar.w * state.turn / max(1, state.max_turns)), bar.h))
        y += 16
        for p in (0, 1):
            y = self._draw_player_panel(surface, p, x, y)

        status, color = "", MUTED
        if self.match.over:
            status = "Game over"
        elif self.paused:
            status, color = "Paused. Press P to continue, N for one cycle", TEXT
        elif self.worker:
            status = "Searching"
        elif not self.humans_ready():
            status, color = "Waiting for a key from the human player", TEXT
        draw_text(surface, f.small, status, (x, y), color)
        y += 22
        for turn, a1, a2, note in self.log:
            if note:
                draw_text(surface, f.small, note[:44], (x + 34, y), ALERT)
            else:
                draw_text(surface, f.small, "%d" % turn, (x + 26, y), MUTED, right=True)
                draw_text(surface, f.small, a1, (x + 34, y), PLAYER_COLORS[0])
                draw_text(surface, f.small, a2, (x + 34 + (PANEL_W - 34) // 2, y), PLAYER_COLORS[1])
            y += 18
        help_y = WINDOW[1] - 42
        draw_text(surface, f.small, "P pause    N one cycle    R restart    Esc menu", (x, help_y), MUTED)
        draw_text(surface, f.small, "+ and - set the pause between cycles: %d ms" % int(self.delay * 1000),
                  (x, help_y + 18), MUTED)
        if self.match.over:
            self._draw_game_over(surface)

    def _draw_player_panel(self, surface, p, x, y):
        f = self.app.fonts
        state = self.match.state
        color = PLAYER_COLORS[p]
        card = pygame.Rect(x, y, PANEL_W, 208)
        pygame.draw.rect(surface, PANEL, card)
        pygame.draw.rect(surface, color, (card.x, card.y, 4, card.h))
        cx, cy, right = x + 16, y + 8, card.right - 12
        draw_text(surface, f.head, self.agents[p].name[:26], (cx, cy), color)
        cy += 34
        for label, hp, max_hp in (("Tank", state.tanks[p].hp, TANK_HP), ("Base", state.bases[p].hp, BASE_HP)):
            draw_text(surface, f.small, label, (cx, cy - 3), MUTED)
            end = draw_pips(surface, cx + 42, cy, max(0, hp), max_hp, color)
            draw_text(surface, f.small, "%d" % max(0, hp), (end + 4, cy - 3), TEXT)
            cy += 18
        cy += 6
        rec = self.last_record
        if rec is None:
            draw_text(surface, f.small, "No move yet", (cx, cy), MUTED)
            return card.bottom + 10
        stats = rec.stats[p]
        draw_text(surface, f.small, "Last action", (cx, cy), MUTED)
        draw_text(surface, f.small, "%s in %.1f ms" % (rec.actions[p].value, rec.times[p] * 1000), (right, cy),
                  TEXT, right=True)
        cy += 20
        if not stats.get("nodes"):
            draw_text(surface, f.small, "This agent does not search a game tree.", (cx, cy), MUTED)
            return card.bottom + 10
        depth = stats.get("depth") or 0
        reached = ("%d plies" % stats.get("max_ply", 0) if not depth else
                   "%d cycle%s, %d plies" % (depth, "" if depth == 1 else "s", depth * 2))
        rows = [("Nodes visited", "{:,}".format(stats["nodes"])),
                ("Alpha-beta cutoffs", "{:,}".format(stats["cutoffs"])),
                ("Search depth", reached + (" (timed out)" if stats.get("timed_out") else "")),
                ("Minimax value", describe_value(stats.get("value")))]
        for label, value in rows:
            draw_text(surface, f.small, label, (cx, cy), MUTED)
            draw_text(surface, f.small, value, (right, cy), TEXT, right=True)
            cy += 18
        self._draw_effort(surface, pygame.Rect(cx, cy + 4, card.right - 12 - cx, card.bottom - cy - 10), p)
        return card.bottom + 10

    def _draw_effort(self, surface, rect, p):
        """Nodes visited on each of the last moves, log scale: the cost of this agent's search over time."""
        history = self.node_history[p][-rect.w // 4:]
        pygame.draw.line(surface, RULE, rect.bottomleft, rect.bottomright)
        if not history:
            return
        top = math.log10(max(max(history), 10))
        for i, n in enumerate(history):
            h = int((rect.h - 1) * math.log10(n) / top) if n > 1 else 1
            pygame.draw.rect(surface, PLAYER_COLORS[p], (rect.x + i * 4, rect.bottom - h, 3, h))

    def _draw_game_over(self, surface):
        f = self.app.fonts
        w = self.match.winner
        text = "Draw" if w == DRAW else "%s wins" % PLAYER_NAMES[w]
        color = TEXT if w == DRAW else PLAYER_COLORS[w]
        box = pygame.Rect(0, 0, 460, 150)
        box.center = (BOARD_RECT[0] + BOARD_RECT[2] // 2, BOARD_RECT[1] + BOARD_RECT[3] // 2)
        overlay = pygame.Surface(box.size, pygame.SRCALPHA)
        overlay.fill((8, 10, 8, 225))
        surface.blit(overlay, box)
        pygame.draw.rect(surface, color, box, 2)
        draw_text(surface, f.title, text, (box.centerx, box.centery - 22), color, center=True)
        state = self.match.state
        if w == DRAW and state.turn >= state.max_turns:
            reason = "turn limit reached"
        elif w == DRAW:
            reason = "both sides destroyed in cycle %d" % state.turn
        else:
            reason = "after %d cycles" % state.turn
        draw_text(surface, f.small, "%s.  R plays again, Esc returns to the menu." % reason.capitalize(),
                  (box.centerx, box.centery + 46), MUTED, center=True)


class TankBattleApp:
    def __init__(self, settings=None, autostart=False):
        pygame.init()
        pygame.display.set_caption("Tank Battle - Adversarial Search")
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
